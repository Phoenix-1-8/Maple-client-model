"""Per-device price breakdown — every device, broken down by site & condition."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..agents.device_pricing import DevicePricingAgent
from ..db import get_session

router = APIRouter()


@router.get("/devices")
def devices(
    region: str = Query("IN"),
    series: int | None = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    result = DevicePricingAgent().overview(db, region=region)
    if series is not None:
        result["devices"] = [d for d in result["devices"] if d["series"] == series]
        result["device_count"] = len(result["devices"])
    return result


@router.get("/devices/{sku}")
def device_breakdown(
    sku: str, region: str = Query("IN"), db: Session = Depends(get_session)
) -> dict:
    result = DevicePricingAgent().breakdown(db, sku, region=region)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No listings for sku '{sku}'")
    return result
