"""
Database seeding.

On startup we materialize a full, internally-consistent mock market:
  * listings      — current cross-platform listings (India + Dubai)
  * market_daily  — the Maple Used-iPhone Index history
  * device_daily  — per-device fair-value history (trend charts)

By default the data is loaded from a committed fixture
(app/fixtures/seed_market.json) so the demo is identical on every machine and
does not depend on the generator running at startup. If the fixture is absent
(or MAPLE_SEED_SOURCE=generate), we fall back to generating it on the fly.
Rebuild the fixture with:  python -m scripts.build_seed_fixture

refresh_market() re-runs the scraper layer (which falls back to mock) and
replaces the live listings — this is what the "Refresh market" demo button and
the Redis worker call.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from .config import get_config
from .db import SessionLocal, init_db
from .models import DeviceDaily, Listing, MarketDaily
from .mock_data import build_rng, build_extra_rng, generate_history, generate_listings, generate_extended_listings
from .scrapers import run_all_scrapers
from .util import as_of_date

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "seed_market.json"

# Columns stored as dates in the fixture, by table key, that must be parsed back
# into date objects before bulk insert.
_DATE_FIELDS = {
    "listings": ("listing_date",),
    "market_daily": ("day",),
    "device_daily": ("day",),
}


def _use_fixture() -> bool:
    """Prefer the committed fixture unless explicitly told to generate."""
    if os.getenv("MAPLE_SEED_SOURCE", "").strip().lower() == "generate":
        return False
    return FIXTURE_PATH.exists()


def _parse_dates(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    for r in rows:
        for f in fields:
            v = r.get(f)
            if isinstance(v, str):
                r[f] = datetime.strptime(v, "%Y-%m-%d").date()
    return rows


def load_fixture(db: Session) -> dict:
    """Load the pre-built market fixture into the (already wiped) database."""
    data = json.loads(FIXTURE_PATH.read_text())
    listings = _parse_dates(list(data["listings"]), _DATE_FIELDS["listings"])
    market = _parse_dates(list(data["market_daily"]), _DATE_FIELDS["market_daily"])
    devices = _parse_dates(list(data["device_daily"]), _DATE_FIELDS["device_daily"])

    db.bulk_insert_mappings(Listing, listings)
    db.bulk_insert_mappings(MarketDaily, market)
    db.bulk_insert_mappings(DeviceDaily, devices)
    db.commit()
    return {
        "seeded": True,
        "source": "fixture",
        "listings": len(listings),
        "market_days": len(market),
        "device_days": len(devices),
    }


def _insert_listings(db: Session, rows: list[dict]) -> None:
    db.bulk_insert_mappings(Listing, rows)


def _update_today_counts(db: Session, as_of: date) -> None:
    """Fill today's listing counts on market_daily / device_daily from listings."""
    today_row = db.scalar(select(MarketDaily).where(MarketDaily.day == as_of))
    listing_total = db.scalar(select(func.count()).select_from(Listing)) or 0
    if today_row is not None:
        today_row.total_active_listings = int(listing_total)

    counts = Counter(
        r[0] for r in db.execute(select(Listing.sku)).all()
    )
    for sku, c in counts.items():
        db.execute(
            update(DeviceDaily)
            .where(DeviceDaily.day == as_of, DeviceDaily.sku == sku)
            .values(listing_count=int(c))
        )


def seed_all(db: Session, force: bool = False, ignore_fixture: bool = False) -> dict:
    cfg = get_config()
    as_of = as_of_date()

    existing = db.scalar(select(MarketDaily).limit(1))
    if existing is not None and not force:
        n = db.scalar(select(func.count()).select_from(Listing))
        return {"seeded": False, "listings": int(n or 0)}

    # wipe
    db.execute(delete(Listing))
    db.execute(delete(MarketDaily))
    db.execute(delete(DeviceDaily))
    db.commit()

    # Preferred path: load the committed pre-built fixture (deterministic, no
    # runtime generation). The fixture already includes the filled-in listing
    # counts, so there's no _update_today_counts step.
    if not ignore_fixture and _use_fixture():
        return load_fixture(db)

    rng = build_rng(cfg)
    listings = generate_listings(cfg, as_of, rng)
    listings += generate_extended_listings(cfg, as_of, build_extra_rng(cfg))
    market_daily, device_daily = generate_history(cfg, as_of, rng)

    _insert_listings(db, listings)
    db.bulk_insert_mappings(MarketDaily, market_daily)
    db.bulk_insert_mappings(DeviceDaily, device_daily)
    db.commit()

    _update_today_counts(db, as_of)
    db.commit()

    return {"seeded": True, "source": "generated", "listings": len(listings),
            "market_days": len(market_daily), "device_days": len(device_daily)}


def refresh_market(db: Session) -> dict:
    """Re-scrape (mock fallback) and replace current listings."""
    as_of = as_of_date()
    listings, report = run_all_scrapers(as_of)
    listings += generate_extended_listings(get_config(), as_of, build_extra_rng(get_config()))

    db.execute(delete(Listing))
    db.commit()
    _insert_listings(db, listings)
    db.commit()

    _update_today_counts(db, as_of)
    db.commit()

    live = sum(r["count"] for r in report if r["source"] == "live")
    mock = sum(r["count"] for r in report if r["source"] == "mock")
    return {
        "refreshed": True,
        "total_listings": len(listings),
        "live_listings": live,
        "mock_listings": mock,
        "platforms": report,
    }


def seed_on_startup() -> dict:
    init_db()
    cfg = get_config()
    if not cfg.infra.seed_on_startup:
        return {"seeded": False, "reason": "SEED_ON_STARTUP=false"}
    with SessionLocal() as db:
        return seed_all(db, force=False)
