"""Maple vs Market — the comparison angle (own price vs market, premium justification)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..agents.maple_compare import MapleComparisonAgent
from ..db import get_session

router = APIRouter()


@router.get("/maple/comparison")
def maple_comparison(
    region: str = Query("IN"),
    series: int | None = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    result = MapleComparisonAgent().run(db, region=region)
    if series is not None:
        result["devices"] = [d for d in result["devices"] if d["series"] == series]
        result["device_count"] = len(result["devices"])
    return result


@router.get("/maple/comparison/{sku}")
def maple_comparison_one(
    sku: str, region: str = Query("IN"), db: Session = Depends(get_session)
) -> dict:
    result = MapleComparisonAgent().breakdown(db, sku, region=region)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No Maple comparison for sku '{sku}'")
    return result
