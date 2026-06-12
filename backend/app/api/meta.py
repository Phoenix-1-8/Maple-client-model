"""Meta / config / catalog / scrape-control endpoints."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..catalog import all_devices
from ..config import MAPLE_GRADES, get_config
from ..db import get_session
from ..normalization import explain_mapping
from ..scrapers import get_scrapers
from ..seed import refresh_market, seed_all

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "maple-ai-department"}


@router.get("/config")
def config() -> dict:
    cfg = get_config()
    return {
        "pricing": asdict(cfg.pricing),
        "baselines": asdict(cfg.baselines),
        "condition_multipliers": cfg.condition_multipliers,
        "condition_confidence": cfg.condition_confidence,
        "maple_grades": MAPLE_GRADES,
        "aed_to_inr": cfg.aed_to_inr,
        "platforms": [asdict(p) for p in cfg.platforms],
        "city_multipliers": cfg.city_multipliers,
    }


@router.get("/normalization/grades")
def grades() -> dict:
    return {"maple_grades": MAPLE_GRADES, "mapping": explain_mapping()}


@router.get("/catalog")
def catalog() -> dict:
    devices = [
        {
            "sku": d.sku,
            "model": d.model,
            "series": d.series,
            "variant": d.variant,
            "storage": d.storage,
            "msrp": d.msrp,
            "launch_date": d.launch_date.isoformat(),
        }
        for d in all_devices()
    ]
    return {"count": len(devices), "devices": devices}


@router.get("/scrape/sources")
def scrape_sources() -> dict:
    out = []
    for s in get_scrapers():
        out.append(
            {
                "platform": s.platform_key,
                "platform_name": s.platform_name,
                "region": s.region,
                "base_url": s.base_url,
                "brightdata_enabled": s.brightdata_enabled,
            }
        )
    return {"count": len(out), "sources": out}


@router.post("/scrape/refresh")
def scrape_refresh(db: Session = Depends(get_session)) -> dict:
    return refresh_market(db)


@router.post("/seed")
def reseed(force: bool = Query(True), db: Session = Depends(get_session)) -> dict:
    return seed_all(db, force=force)
