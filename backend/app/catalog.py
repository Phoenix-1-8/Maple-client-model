"""
Device catalog for the Maple pilot: iPhone 13 -> 17 series.

Defines the (model, variant, storage) universe, launch dates and a launch MSRP
model.  These drive the depreciation-based "true value" used to synthesize a
realistic, internally-consistent mock market.

MSRP model:
    msrp = base_msrp[series] * variant_multiplier * storage_multiplier

Indian launch MSRPs are approximate but plausible for a demo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Launch month per series (used to compute device age -> depreciation).
SERIES_LAUNCH: dict[int, date] = {
    13: date(2021, 9, 24),
    14: date(2022, 9, 16),
    15: date(2023, 9, 22),
    16: date(2024, 9, 20),
    17: date(2025, 9, 19),
}

# Base (128GB, base variant) launch MSRP in INR per series.
SERIES_BASE_MSRP: dict[int, float] = {
    13: 79900.0,
    14: 79900.0,
    15: 79900.0,
    16: 79900.0,
    17: 82900.0,
}

# Variants. "mini" only exists for the 13 series in this catalog.
VARIANT_MULTIPLIER: dict[str, float] = {
    "Mini": 0.90,
    "Base": 1.00,
    "Plus": 1.18,
    "Pro": 1.50,
    "Pro Max": 1.68,
}

STORAGE_MULTIPLIER: dict[str, float] = {
    "128GB": 1.00,
    "256GB": 1.12,
    "512GB": 1.32,
    "1TB": 1.55,
}

# Which variants each series ships.
SERIES_VARIANTS: dict[int, list[str]] = {
    13: ["Mini", "Base", "Pro", "Pro Max"],
    14: ["Base", "Plus", "Pro", "Pro Max"],
    15: ["Base", "Plus", "Pro", "Pro Max"],
    16: ["Base", "Plus", "Pro", "Pro Max"],
    17: ["Base", "Plus", "Pro", "Pro Max"],
}

# Storage options by variant tier.
STANDARD_STORAGE = ["128GB", "256GB", "512GB"]
PRO_STORAGE = ["128GB", "256GB", "512GB", "1TB"]


def storages_for(variant: str) -> list[str]:
    return PRO_STORAGE if variant in ("Pro", "Pro Max") else STANDARD_STORAGE


def model_name(series: int, variant: str) -> str:
    """Human label, e.g. 'iPhone 13 mini', 'iPhone 15 Pro Max'."""
    if variant == "Base":
        return f"iPhone {series}"
    if variant == "Mini":
        return f"iPhone {series} mini"
    return f"iPhone {series} {variant}"


@dataclass(frozen=True)
class Device:
    series: int
    variant: str
    storage: str

    @property
    def model(self) -> str:
        return model_name(self.series, self.variant)

    @property
    def launch_date(self) -> date:
        return SERIES_LAUNCH[self.series]

    @property
    def msrp(self) -> float:
        base = SERIES_BASE_MSRP[self.series]
        return round(
            base
            * VARIANT_MULTIPLIER[self.variant]
            * STORAGE_MULTIPLIER[self.storage],
            -2,  # round to nearest 100
        )

    @property
    def sku(self) -> str:
        v = self.variant.lower().replace(" ", "")
        return f"ip{self.series}-{v}-{self.storage.lower()}"


def all_devices() -> list[Device]:
    devices: list[Device] = []
    for series, variants in SERIES_VARIANTS.items():
        for variant in variants:
            for storage in storages_for(variant):
                devices.append(Device(series, variant, storage))
    return devices


_SKU_INDEX: dict[str, Device] = {d.sku: d for d in all_devices()}


def device_by_sku(sku: str) -> Device | None:
    return _SKU_INDEX.get(sku)


def device_age_months(d: Device, as_of: date) -> float:
    delta_days = (as_of - d.launch_date).days
    return max(0.0, delta_days / 30.44)
