"""ML pricing layer — fair value, effects, depreciation curve and forecast."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..agents.ml_pricing import MLPricingAgent
from ..db import get_session

router = APIRouter()


@router.get("/ml/pricing")
def ml_pricing(
    region: str = Query("IN"),
    series: int | None = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    result = MLPricingAgent().overview(db, region=region)
    if result.get("available") and series is not None:
        result["devices"] = [d for d in result["devices"] if d["series"] == series]
        result["device_count"] = len(result["devices"])
    return result


@router.get("/ml/pricing/{sku}")
def ml_pricing_one(
    sku: str, region: str = Query("IN"), db: Session = Depends(get_session)
) -> dict:
    result = MLPricingAgent().price_one(db, sku, region=region)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No ML pricing for sku '{sku}'")
    return result


@router.get("/ml/forecast")
def ml_forecast(region: str = Query("IN"), db: Session = Depends(get_session)) -> dict:
    return MLPricingAgent().forecast_all(db, region=region)
