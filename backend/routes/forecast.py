from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.services.gold_api_service import GoldApiService
from backend.services.prediction_service import PredictionService


router = APIRouter(tags=["forecast"])
gold_api_service = GoldApiService()
prediction_service = PredictionService()


class ForecastRequest(BaseModel):
    price_per_gram: float = Field(gt=0)
    grams: float = Field(gt=0)
    purchase_date: Optional[str] = None
    future_price_per_gram: Optional[float] = Field(default=None, gt=0)
    projection_years: list[int] = Field(default_factory=lambda: [1, 3, 5])
    display_currency: Literal["USD", "MYR"] = "USD"
    use_ai_projection: bool = True

    @field_validator("purchase_date")
    @classmethod
    def normalize_date(cls, value: Optional[str]) -> Optional[str]:
        return value or None

    @field_validator("projection_years")
    @classmethod
    def validate_projection_years(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("Projection years cannot be empty.")
        normalized = sorted(set(value))
        if any(year <= 0 for year in normalized):
            raise ValueError("Projection years must be positive whole numbers.")
        if any(year > 50 for year in normalized):
            raise ValueError("Projection years must be 50 or less.")
        return normalized


@router.post("/forecast")
def forecast(payload: ForecastRequest):
    try:
        market = gold_api_service.get_gold_market_snapshot(
            currency=payload.display_currency,
            range_value="5y",
            interval="1d",
        )
        malaysia_reference = (
            gold_api_service.get_malaysia_local_prices()
            if payload.display_currency == "MYR"
            else None
        )
        analytics_price = (
            malaysia_reference["analytics_price_per_gram"]
            if malaysia_reference
            else market["latest_price_per_gram"]
        )
        realistic_sell_price = (
            malaysia_reference["realistic_sell_price_per_gram"]
            if malaysia_reference
            else market["latest_price_per_gram"]
        )
        initial_investment = payload.price_per_gram * payload.grams
        current_value = prediction_service.calculate_current_value(realistic_sell_price, payload.grams)
        current_profit = prediction_service.calculate_profit(current_value, initial_investment)

        response = {
            "inputs": payload.model_dump(),
            "market": {
                "currency": payload.display_currency,
                "latest_price_per_gram": analytics_price,
                "analytics_price_per_gram": analytics_price,
                "realistic_sell_price_per_gram": realistic_sell_price,
                "updated_at": market["updated_at"],
                "historical_points": market["historical_points"],
                "fx_rate": market["fx_rate"],
                "pricing_reference": malaysia_reference,
            },
            "summary": {
                "initial_investment": round(initial_investment, 2),
                "current_value": round(current_value, 2),
                "profit_loss": round(current_profit, 2),
            },
            "historical_series": market["historical_series"],
            "manual_future_value": None,
            "projection_table": [],
            "scenario_summary": {},
            "forecast_meta": {},
            "warning": "Projection is estimation, not financial advice.",
        }

        if payload.future_price_per_gram is not None and not payload.use_ai_projection:
            future_value = payload.future_price_per_gram * payload.grams
            future_profit = prediction_service.calculate_profit(future_value, initial_investment)
            response["manual_future_value"] = {
                "future_price_per_gram": round(payload.future_price_per_gram, 2),
                "total_value": round(future_value, 2),
                "profit": round(future_profit, 2),
            }
            return response

        forecast_result = prediction_service.forecast_prices(
            historical_series=market["historical_series"],
            latest_price=analytics_price,
            grams=payload.grams,
            initial_investment=initial_investment,
            forecast_horizons=payload.projection_years,
        )
        response["projection_table"] = forecast_result["projection_table"]
        response["scenario_summary"] = forecast_result["scenario_summary"]
        response["forecast_meta"] = forecast_result["meta"]
        return response
    except Exception as exc:  # pragma: no cover - runtime safety
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {exc}") from exc
