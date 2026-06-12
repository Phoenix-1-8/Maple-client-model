"""Market index, pricing recommendations, executive snapshot & KPIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.market_pricing import MarketPricingAgent
from ..agents.orchestrator import executive_snapshot
from ..db import get_session
from ..metrics import compute_metrics
from ..models import MarketDaily

router = APIRouter()


@router.get("/market/index")
def market_index(db: Session = Depends(get_session)) -> dict:
    rows = list(db.scalars(select(MarketDaily).order_by(MarketDaily.day.asc())))
    history = [
        {
            "day": r.day.isoformat(),
            "index": r.index_value,
            "movement_pct": r.movement_pct,
            "active_listings": r.total_active_listings,
        }
        for r in rows
    ]
    latest = history[-1] if history else None
    return {"latest": latest, "history": history}


@router.get("/market/snapshot")
def snapshot(db: Session = Depends(get_session)) -> dict:
    return executive_snapshot(db)


@router.get("/market/metrics")
def metrics(db: Session = Depends(get_session)) -> dict:
    return compute_metrics(db)


@router.get("/market/pricing")
def pricing(
    region: str = Query("IN"),
    series: int | None = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    result = MarketPricingAgent().run(db, region=region)
    if series is not None:
        result["devices"] = [d for d in result["devices"] if d["series"] == series]
        result["device_count"] = len(result["devices"])
    return result


@router.get("/market/pricing/{sku}")
def pricing_one(
    sku: str, region: str = Query("IN"), db: Session = Depends(get_session)
) -> dict:
    result = MarketPricingAgent().price_one(db, sku, region=region)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No pricing data for sku '{sku}'")
    return result
