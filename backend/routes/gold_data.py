from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.services.gold_api_service import GoldApiService


router = APIRouter(tags=["gold-data"])
gold_api_service = GoldApiService()


@router.get("/get-gold-price")
def get_gold_price(
    currency: Literal["USD", "MYR"] = Query(default="USD"),
    range_value: Optional[str] = Query(default="5y", alias="range"),
    interval: str = Query(default="1d"),
):
    try:
        return gold_api_service.get_gold_market_snapshot(
            currency=currency,
            range_value=range_value,
            interval=interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime safety
        raise HTTPException(status_code=502, detail=f"Unable to fetch gold data: {exc}") from exc


@router.get("/malaysia-live-price")
def malaysia_live_price():
    try:
        return gold_api_service.get_malaysia_local_prices()
    except Exception as exc:  # pragma: no cover - runtime safety
        raise HTTPException(status_code=502, detail=f"Unable to fetch Malaysia gold prices: {exc}") from exc
