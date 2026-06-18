"""
Feature engineering for the ML pricing model.

We turn raw market listings into a tabular frame the model can learn from. The
features are deliberately the same economic drivers the deterministic engine
uses (so the learned model is interpretable and comparable):

    numeric:      series, msrp, age_months, storage_mult, battery_health
    categorical:  variant, condition, city, platform

Target: the listing's asking price in INR (the model learns price in log-space
for stability, handled in model.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..catalog import STORAGE_MULTIPLIER, device_age_months, device_by_sku

NUMERIC = ["series", "msrp", "age_months", "storage_mult", "battery_health"]
CATEGORICAL = ["variant", "condition", "city", "platform"]
FEATURES = NUMERIC + CATEGORICAL


@dataclass
class FeatureRow:
    series: int
    msrp: float
    age_months: float
    storage_mult: float
    battery_health: int
    variant: str
    condition: str
    city: str
    platform: str

    def as_dict(self) -> dict:
        return {f: getattr(self, f) for f in FEATURES}


def row_for(
    *,
    sku: str,
    condition: str,
    city: str,
    platform: str,
    as_of: date,
    battery_health: int = 93,
) -> FeatureRow | None:
    """Build a single feature row for a hypothetical listing of ``sku``."""
    device = device_by_sku(sku)
    if device is None:
        return None
    return FeatureRow(
        series=int(getattr(device, "series", 0)),
        msrp=float(device.msrp),
        age_months=round(device_age_months(device, as_of), 2),
        storage_mult=float(STORAGE_MULTIPLIER.get(device.storage, 1.0)),
        battery_health=int(battery_health),
        variant=str(getattr(device, "variant", "Base")),
        condition=condition,
        city=city,
        platform=platform,
    )


def build_frame(listings, as_of: date) -> pd.DataFrame:
    """Build the training frame from listing objects/dicts.

    Accepts SQLAlchemy ``Listing`` rows or plain dicts. Rows whose SKU is not in
    the catalogue (or with a non-positive price) are dropped.
    """
    records: list[dict] = []
    for l in listings:
        get = (lambda k, d=None: l.get(k, d)) if isinstance(l, dict) else (lambda k, d=None: getattr(l, k, d))
        sku = get("sku")
        device = device_by_sku(sku) if sku else None
        price = get("asking_price")
        if device is None or not price or price <= 0:
            continue
        records.append(
            {
                "series": int(get("series") or getattr(device, "series", 0)),
                "msrp": float(device.msrp),
                "age_months": round(device_age_months(device, as_of), 2),
                "storage_mult": float(STORAGE_MULTIPLIER.get(get("storage"), 1.0)),
                "battery_health": int(get("battery_health") or 93),
                "variant": str(get("variant") or getattr(device, "variant", "Base")),
                "condition": str(get("condition") or "Superb"),
                "city": str(get("city") or "Delhi"),
                "platform": str(get("platform") or "unknown"),
                "asking_price": float(price),
            }
        )
    return pd.DataFrame.from_records(records)
