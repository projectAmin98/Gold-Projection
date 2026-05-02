from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import time
from typing import Any

import requests


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
HARGA_EMAS_URL = "https://hargaemas.com.my/harga-emas-terkini-di-malaysia/"
RAZAK_STORE_URL = "https://razak.com.my/store/"
RAZAK_GPO_ENDPOINT = "https://razak.com.my/wp-json/gpo/v1/price"
GRAMS_PER_TROY_OUNCE = 31.1034768


@dataclass(slots=True)
class YahooChartParams:
    symbol: str
    range_value: str
    interval: str


class GoldApiService:
    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0 Safari/537.36"
                )
            }
        )

    def get_gold_market_snapshot(
        self,
        currency: str = "USD",
        range_value: str = "5y",
        interval: str = "1d",
    ) -> dict[str, Any]:
        currency = currency.upper()
        if currency not in {"USD", "MYR"}:
            raise ValueError("Supported currencies are USD and MYR.")

        gold_chart = self._fetch_chart(YahooChartParams("GC=F", range_value, interval))
        gold_series = self._extract_series(gold_chart)
        if not gold_series:
            raise ValueError("No gold market data received from provider.")

        fx_rate = 1.0
        if currency == "MYR":
            fx_chart = self._fetch_chart(YahooChartParams("MYR=X", "1mo", "1d"))
            fx_series = self._extract_series(fx_chart)
            if not fx_series:
                raise ValueError("No USD/MYR FX data received from provider.")
            # Yahoo's MYR=X feed returns MYR per USD, which matches our
            # need to convert USD-denominated gold prices into MYR.
            fx_rate = fx_series[-1]["close"] or 1.0

        historical_series = [
            {
                "date": point["date"],
                "price_per_gram": round((point["close"] / GRAMS_PER_TROY_OUNCE) * fx_rate, 4),
            }
            for point in gold_series
        ]

        latest_price_per_gram = historical_series[-1]["price_per_gram"]
        return {
            "provider": "Yahoo Finance",
            "symbol": "GC=F",
            "currency": currency,
            "fx_rate": round(fx_rate, 6),
            "updated_at": historical_series[-1]["date"],
            "latest_price_per_gram": round(latest_price_per_gram, 4),
            "historical_points": len(historical_series),
            "historical_series": historical_series,
        }

    def get_malaysia_local_prices(self) -> dict[str, Any]:
        spot_market = self._fetch_hargaemas_spot_market()
        dealer_market = self._fetch_razak_buyback_market()

        return {
            "market": "Malaysia",
            "currency": "MYR",
            "updated_at": spot_market["updated_at"],
            "analytics_price_per_gram": spot_market["spot_sell_999_per_gram"],
            "realistic_sell_price_per_gram": dealer_market["dealer_buy_999_per_gram"],
            "analytics_source": {
                "name": "HargaEmas.com.my",
                "url": HARGA_EMAS_URL,
                "label": "999 spot/raw-material price for analytics",
                "updated_at": spot_market["updated_at"],
            },
            "realistic_sell_source": {
                "name": "Abdul Razak Gold House",
                "url": RAZAK_STORE_URL,
                "label": "999 dealer buyback price for realistic selling value",
                "updated_at": dealer_market["updated_at"],
            },
            "spot_market": spot_market,
            "dealer_market": dealer_market,
            "provider_note": "System uses 999 spot price for analytics/modeling and dealer buyback price for realistic Malaysia selling value. Jewellery prices are excluded.",
        }

    def _fetch_chart(self, params: YahooChartParams) -> dict[str, Any]:
        response = self.session.get(
            YAHOO_CHART_URL.format(symbol=params.symbol),
            params={"range": params.range_value, "interval": params.interval},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        result = payload.get("chart", {}).get("result", [])
        if not result:
            error = payload.get("chart", {}).get("error")
            raise ValueError(error or f"Empty chart result for {params.symbol}.")
        return result[0]

    def _extract_series(self, chart_payload: dict[str, Any]) -> list[dict[str, Any]]:
        timestamps = chart_payload.get("timestamp") or []
        indicators = chart_payload.get("indicators", {}).get("quote", [{}])[0]
        closes = indicators.get("close") or []

        series: list[dict[str, Any]] = []
        for timestamp, close in zip(timestamps, closes):
            if close is None:
                continue
            series.append(
                {
                    "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "close": float(close),
                }
            )
        return series

    def _fetch_hargaemas_spot_market(self) -> dict[str, Any]:
        response = self._get_with_retries(HARGA_EMAS_URL)
        response.raise_for_status()
        html = response.text

        updated_at_match = re.search(
            r"Dikemaskini:\s*([^<]+)",
            html,
            flags=re.IGNORECASE,
        )
        sell_match = re.search(
            r"Harga Jual 999</small>\s*<strong[^>]*>\s*RM\s*([\d,]+(?:\.\d+)?)",
            html,
            flags=re.IGNORECASE,
        )
        buy_match = re.search(
            r"Harga Beli 999</small>\s*<strong[^>]*>\s*RM\s*([\d,]+(?:\.\d+)?)",
            html,
            flags=re.IGNORECASE,
        )
        if not sell_match or not buy_match:
            raise ValueError("Unable to parse HargaEmas 999 spot prices.")

        return {
            "product": "999 spot gold",
            "spot_sell_999_per_gram": round(float(sell_match.group(1).replace(",", "")), 3),
            "spot_buy_999_per_gram": round(float(buy_match.group(1).replace(",", "")), 3),
            "updated_at": updated_at_match.group(1).strip() if updated_at_match else None,
        }

    def _fetch_razak_buyback_market(self) -> dict[str, Any]:
        response = self._get_with_retries(RAZAK_STORE_URL)
        response.raise_for_status()
        html = response.text

        nonce_match = re.search(r'const NONCE="([^"]+)"', html)
        if not nonce_match:
            raise ValueError("Unable to parse Razak live price nonce.")

        payload = {
            "elements": [
                {
                    "id": "buy_back_gold999",
                    "type": "gold",
                    "weight": "1",
                    "addon": "-2.30",
                }
            ],
            "nonce": nonce_match.group(1),
        }
        api_response = self._post_with_retries(RAZAK_GPO_ENDPOINT, json=payload)
        api_response.raise_for_status()
        result = api_response.json()
        if not result.get("success"):
            raise ValueError("Razak buyback endpoint returned an unsuccessful response.")

        price = result.get("data", {}).get("prices", {}).get("buy_back_gold999")
        if price is None:
            raise ValueError("Unable to parse Razak 999 buyback price.")

        updated_at_match = re.search(
            r'"dateModified":"([^"]+)"',
            html,
            flags=re.IGNORECASE,
        )
        return {
            "product": "999 dealer buyback",
            "dealer_buy_999_per_gram": round(float(price), 2),
            "updated_at": updated_at_match.group(1) if updated_at_match else None,
        }

    def _get_with_retries(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self.session.get(url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(0.6 * (attempt + 1))
        raise last_error or ValueError(f"Unable to fetch URL: {url}")

    def _post_with_retries(self, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self.session.post(url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(0.6 * (attempt + 1))
        raise last_error or ValueError(f"Unable to post to URL: {url}")
