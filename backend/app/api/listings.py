"""Raw listing access + facets (powers the competitor heatmap & drill-downs)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Listing

router = APIRouter()


def _serialize(l: Listing) -> dict:
    return {
        "id": l.id,
        "platform": l.platform,
        "region": l.region,
        "sku": l.sku,
        "model": l.model,
        "variant": l.variant,
        "storage": l.storage,
        "battery_health": l.battery_health,
        "condition": l.condition,
        "raw_condition": l.raw_condition,
        "city": l.city,
        "asking_price": l.asking_price,
        "asking_price_native": l.asking_price_native,
        "currency": l.currency,
        "seller_type": l.seller_type,
        "color": l.color,
        "listing_title": l.listing_title,
        "seller_name": l.seller_name,
        "seller_rating": l.seller_rating,
        "seller_reviews": l.seller_reviews,
        "warranty": l.warranty,
        "accessories": l.accessories,
        "lock_status": l.lock_status,
        "verified": l.verified,
        "negotiable": l.negotiable,
        "views": l.views,
        "listing_date": l.listing_date.isoformat(),
        "url": l.url,
    }


@router.get("/listings")
def listings(
    platform: str | None = None,
    sku: str | None = None,
    series: int | None = None,
    city: str | None = None,
    condition: str | None = None,
    region: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
) -> dict:
    stmt = select(Listing)
    if platform:
        stmt = stmt.where(Listing.platform == platform)
    if sku:
        stmt = stmt.where(Listing.sku == sku)
    if series is not None:
        stmt = stmt.where(Listing.series == series)
    if city:
        stmt = stmt.where(Listing.city == city)
    if condition:
        stmt = stmt.where(Listing.condition == condition)
    if region:
        stmt = stmt.where(Listing.region == region)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(stmt.order_by(Listing.listing_date.desc()).offset(offset).limit(limit))
    )
    return {"total": int(total), "count": len(rows), "items": [_serialize(r) for r in rows]}


@router.get("/listings/facets")
def facets(db: Session = Depends(get_session)) -> dict:
    def grouped(col):
        return {
            k: int(v)
            for k, v in db.execute(
                select(col, func.count()).group_by(col).order_by(func.count().desc())
            ).all()
        }

    return {
        "total": int(db.scalar(select(func.count()).select_from(Listing)) or 0),
        "by_platform": grouped(Listing.platform),
        "by_city": grouped(Listing.city),
        "by_condition": grouped(Listing.condition),
        "by_region": grouped(Listing.region),
        "by_series": grouped(Listing.series),
    }
