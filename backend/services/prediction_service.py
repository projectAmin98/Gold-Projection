from __future__ import annotations

from datetime import datetime
from math import sqrt
from statistics import mean
from typing import Any


class PredictionService:
    def calculate_current_value(self, latest_price_per_gram: float, grams: float) -> float:
        return latest_price_per_gram * grams

    def calculate_profit(self, current_value: float, initial_value: float) -> float:
        return current_value - initial_value

    def forecast_prices(
        self,
        historical_series: list[dict[str, Any]],
        latest_price: float,
        grams: float,
        initial_investment: float,
        forecast_horizons: list[int],
    ) -> dict[str, Any]:
        if len(historical_series) < 30:
            raise ValueError("At least 30 data points are required for forecasting.")

        prices = [point["price_per_gram"] for point in historical_series]
        ma_30 = self._moving_average(prices, 30)
        ma_90 = self._moving_average(prices, 90)
        slope, intercept = self._linear_regression(prices)
        cagr = self._calculate_cagr(prices)
        volatility = self._annualized_volatility(prices)

        latest_date = datetime.strptime(historical_series[-1]["date"], "%Y-%m-%d")
        projection_table = []

        scenario_ranges = {
            "conservative": (-0.05, 0.05),
            "moderate": (0.05, 0.15),
            "aggressive": (0.15, 0.30),
        }
        scenario_summary = {}

        for horizon in forecast_horizons:
            projected_price = self._blended_projection(
                latest_price=latest_price,
                ma_30=ma_30,
                ma_90=ma_90,
                slope=slope,
                intercept=intercept,
                history_length=len(prices),
                years_ahead=horizon,
                cagr=cagr,
                volatility=volatility,
            )
            total_value = projected_price * grams
            profit = self.calculate_profit(total_value, initial_investment)
            projection_table.append(
                {
                    "year": latest_date.year + horizon,
                    "horizon_years": horizon,
                    "price_per_gram": round(projected_price, 2),
                    "total_value": round(total_value, 2),
                    "profit": round(profit, 2),
                }
            )

        for scenario_name, yearly_range in scenario_ranges.items():
            scenario_summary[scenario_name] = self._build_scenario_band(
                latest_price=latest_price,
                grams=grams,
                initial_investment=initial_investment,
                forecast_horizons=forecast_horizons,
                yearly_range=yearly_range,
                latest_year=latest_date.year,
            )

        return {
            "projection_table": projection_table,
            "scenario_summary": scenario_summary,
            "meta": {
                "moving_average_30": round(ma_30, 2),
                "moving_average_90": round(ma_90, 2),
                "cagr": round(cagr * 100, 2),
                "annualized_volatility": round(volatility * 100, 2),
                "model": "Blended moving-average + linear-regression + CAGR projection",
            },
        }

    def _moving_average(self, prices: list[float], window: int) -> float:
        slice_window = prices[-min(window, len(prices)) :]
        return mean(slice_window)

    def _linear_regression(self, prices: list[float]) -> tuple[float, float]:
        x_values = list(range(len(prices)))
        x_mean = mean(x_values)
        y_mean = mean(prices)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, prices))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        slope = numerator / denominator if denominator else 0.0
        intercept = y_mean - (slope * x_mean)
        return slope, intercept

    def _calculate_cagr(self, prices: list[float]) -> float:
        periods = max((len(prices) - 1) / 252, 1 / 252)
        start_price = max(prices[0], 0.0001)
        end_price = max(prices[-1], 0.0001)
        return (end_price / start_price) ** (1 / periods) - 1

    def _annualized_volatility(self, prices: list[float]) -> float:
        returns = []
        for previous, current in zip(prices, prices[1:]):
            if previous <= 0:
                continue
            returns.append((current - previous) / previous)
        if len(returns) < 2:
            return 0.0

        avg_return = mean(returns)
        variance = sum((value - avg_return) ** 2 for value in returns) / (len(returns) - 1)
        return sqrt(variance) * sqrt(252)

    def _blended_projection(
        self,
        latest_price: float,
        ma_30: float,
        ma_90: float,
        slope: float,
        intercept: float,
        history_length: int,
        years_ahead: int,
        cagr: float,
        volatility: float,
    ) -> float:
        days_forward = years_ahead * 252
        regression_price = (slope * (history_length + days_forward)) + intercept
        regression_price = max(regression_price, latest_price * 0.65)
        cagr_price = latest_price * ((1 + cagr) ** years_ahead)
        ma_anchor = (ma_30 * 0.55) + (ma_90 * 0.45)

        uncertainty_dampener = max(0.78, 1 - (volatility * 0.2))
        blended = (
            (latest_price * 0.25)
            + (ma_anchor * 0.20)
            + (regression_price * 0.30)
            + (cagr_price * 0.25)
        ) * uncertainty_dampener

        return max(blended, latest_price * 0.75)

    def _build_scenario_band(
        self,
        latest_price: float,
        grams: float,
        initial_investment: float,
        forecast_horizons: list[int],
        yearly_range: tuple[float, float],
        latest_year: int,
    ) -> list[dict[str, Any]]:
        lower_rate, upper_rate = yearly_range
        rows = []
        for horizon in forecast_horizons:
            low_price = latest_price * ((1 + lower_rate) ** horizon)
            high_price = latest_price * ((1 + upper_rate) ** horizon)
            rows.append(
                {
                    "year": latest_year + horizon,
                    "low_price_per_gram": round(low_price, 2),
                    "high_price_per_gram": round(high_price, 2),
                    "low_total_value": round(low_price * grams, 2),
                    "high_total_value": round(high_price * grams, 2),
                    "low_profit": round((low_price * grams) - initial_investment, 2),
                    "high_profit": round((high_price * grams) - initial_investment, 2),
                }
            )
        return rows
