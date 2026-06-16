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
    family: str = "iPhone"

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


@dataclass(frozen=True)
class ExtraDevice:
    """Non-iPhone device with explicit fields (not computed)."""
    family: str
    series: int
    variant: str
    storage: str
    model: str
    msrp: float
    launch_date: date
    sku: str


def iphone_devices() -> list[Device]:
    """Return EXACTLY what all_devices() currently returns (the iPhone loop)."""
    devices: list[Device] = []
    for series, variants in SERIES_VARIANTS.items():
        for variant in variants:
            for storage in storages_for(variant):
                devices.append(Device(series, variant, storage))
    return devices


def _build_extra_devices() -> list[ExtraDevice]:
    """Build list of non-iPhone devices from family rules."""
    devices: list[ExtraDevice] = []

    # iPad (series 30)
    devices.extend(_make_extra_family("iPad", 30, "iPad (A16)", "ipad", date(2025, 3, 12),
                                       {"A16": 1.0}, {"128GB": 1.0, "256GB": 1.18, "512GB": 1.45}, 34900))
    # iPad mini (series 31)
    devices.extend(_make_extra_family("iPad", 31, "iPad mini (A17 Pro)", "ipadmini", date(2024, 10, 23),
                                       {"A17 Pro": 1.0}, {"128GB": 1.0, "256GB": 1.2, "512GB": 1.5}, 49900))
    # iPad Air 11" (series 32)
    devices.extend(_make_extra_family("iPad", 32, 'iPad Air 11" (M3)', "ipadair11", date(2025, 3, 12),
                                       {"M3": 1.0}, {"128GB": 1.0, "256GB": 1.18, "512GB": 1.45, "1TB": 1.8}, 59900))
    # iPad Air 13" (series 33)
    devices.extend(_make_extra_family("iPad", 33, 'iPad Air 13" (M3)', "ipadair13", date(2025, 3, 12),
                                       {"M3": 1.0}, {"128GB": 1.0, "256GB": 1.18, "512GB": 1.45, "1TB": 1.8}, 74900))
    # iPad Pro 11" (series 34)
    devices.extend(_make_extra_family("iPad", 34, 'iPad Pro 11" (M4)', "ipadpro11", date(2024, 5, 15),
                                       {"M4": 1.0}, {"256GB": 1.0, "512GB": 1.25, "1TB": 1.6, "2TB": 2.0}, 99900))
    # iPad Pro 13" (series 35)
    devices.extend(_make_extra_family("iPad", 35, 'iPad Pro 13" (M4)', "ipadpro13", date(2024, 5, 15),
                                       {"M4": 1.0}, {"256GB": 1.0, "512GB": 1.25, "1TB": 1.6, "2TB": 2.0}, 129900))
    # MacBook Air 13" (series 40)
    devices.extend(_make_extra_family("Mac", 40, 'MacBook Air 13" (M4)', "mba13", date(2025, 3, 12),
                                       {"M4": 1.0}, {"256GB": 1.0, "512GB": 1.18, "1TB": 1.45}, 99900))
    # MacBook Air 15" (series 41)
    devices.extend(_make_extra_family("Mac", 41, 'MacBook Air 15" (M4)', "mba15", date(2025, 3, 12),
                                       {"M4": 1.0}, {"256GB": 1.0, "512GB": 1.18, "1TB": 1.45}, 124900))
    # MacBook Pro 14" (series 42)
    devices.extend(_make_extra_family_variant("Mac", 42, "MacBook Pro 14", "mbp14", date(2024, 11, 8),
                                               {"M4": 1.0, "M4 Pro": 1.3, "M4 Max": 1.8},
                                               {"512GB": 1.0, "1TB": 1.2, "2TB": 1.5}, 169900))
    # MacBook Pro 16" (series 43)
    devices.extend(_make_extra_family_variant("Mac", 43, "MacBook Pro 16", "mbp16", date(2024, 11, 8),
                                               {"M4 Pro": 1.0, "M4 Max": 1.45},
                                               {"512GB": 1.0, "1TB": 1.2, "2TB": 1.5}, 249900))
    # Mac mini (series 44)
    devices.extend(_make_extra_family_variant("Mac", 44, "Mac mini", "macmini", date(2024, 11, 8),
                                               {"M4": 1.0, "M4 Pro": 1.6},
                                               {"256GB": 1.0, "512GB": 1.2, "1TB": 1.45}, 59900))
    # iMac 24" (series 45)
    devices.extend(_make_extra_family("Mac", 45, 'iMac 24" (M4)', "imac24", date(2024, 11, 8),
                                       {"M4": 1.0}, {"256GB": 1.0, "512GB": 1.2, "1TB": 1.45}, 134900))
    # Apple Watch SE (series 50)
    devices.extend(_make_extra_family("Watch", 50, "Apple Watch SE", "watch-se", date(2022, 9, 16),
                                       {"40mm": 1.0, "44mm": 1.08}, {"32GB": 1.0}, 29900))
    # Apple Watch Series 10 (series 51)
    devices.extend(_make_extra_family("Watch", 51, "Apple Watch Series 10", "watch-s10", date(2024, 9, 20),
                                       {"42mm": 1.0, "46mm": 1.09}, {"32GB": 1.0}, 46900))
    # Apple Watch Ultra 2 (series 52)
    devices.extend(_make_extra_family("Watch", 52, "Apple Watch Ultra 2", "watch-ultra2", date(2024, 9, 20),
                                       {"49mm": 1.0}, {"64GB": 1.0}, 89900))
    # AirPods 4 (series 60)
    devices.extend(_make_extra_family("AirPods", 60, "AirPods 4 (ANC)", "airpods4", date(2024, 9, 20),
                                       {"ANC": 1.0}, {"-": 1.0}, 17900))
    # AirPods Pro 2 (series 61)
    devices.extend(_make_extra_family("AirPods", 61, "AirPods Pro 2", "airpodspro2", date(2023, 9, 22),
                                       {"USB-C": 1.0}, {"-": 1.0}, 24900))
    # AirPods Max (series 62)
    devices.extend(_make_extra_family("AirPods", 62, "AirPods Max", "airpodsmax", date(2024, 9, 20),
                                       {"USB-C": 1.0}, {"-": 1.0}, 59900))
    return devices


def _make_extra_family(family: str, series: int, model_base: str, sku_prefix: str, launch_date: date,
                       variants: dict[str, float], storages: dict[str, float], base_msrp: float) -> list[ExtraDevice]:
    """Helper: expand single-variant family."""
    devices: list[ExtraDevice] = []
    for variant, v_mult in variants.items():
        for storage, s_mult in storages.items():
            msrp = round(base_msrp * v_mult * s_mult, -2)
            if len(variants) == 1 and len(storages) == 1:
                sku = sku_prefix
            elif len(variants) == 1:
                sku = f"{sku_prefix}-{storage.lower()}"
            elif len(storages) == 1:
                sku = f"{sku_prefix}-{_sku_token(variant)}"
            else:
                sku = f"{sku_prefix}-{_sku_token(variant)}-{storage.lower()}"
            devices.append(ExtraDevice(
                family=family,
                series=series,
                variant=variant,
                storage=storage,
                model=model_base,
                msrp=msrp,
                launch_date=launch_date,
                sku=sku,
            ))
    return devices


def _make_extra_family_variant(family: str, series: int, model_base: str, sku_prefix: str, launch_date: date,
                                variants: dict[str, float], storages: dict[str, float], base_msrp: float) -> list[ExtraDevice]:
    """Helper: expand multi-variant family where variant appears in model name."""
    devices: list[ExtraDevice] = []
    for variant, v_mult in variants.items():
        model = f"{model_base} ({variant})"
        for storage, s_mult in storages.items():
            msrp = round(base_msrp * v_mult * s_mult, -2)
            sku = f"{sku_prefix}-{_sku_token(variant)}-{storage.lower()}"
            devices.append(ExtraDevice(
                family=family,
                series=series,
                variant=variant,
                storage=storage,
                model=model,
                msrp=msrp,
                launch_date=launch_date,
                sku=sku,
            ))
    return devices


def _sku_token(s: str) -> str:
    """Convert variant name to lowercase SKU token."""
    return s.lower().replace(" ", "")


EXTRA_DEVICES: list[ExtraDevice] = _build_extra_devices()


def all_devices() -> list[Device | ExtraDevice]:
    """Return iPhones + extra devices."""
    return iphone_devices() + EXTRA_DEVICES


_SKU_INDEX: dict[str, Device | ExtraDevice] = {d.sku: d for d in all_devices()}


def device_by_sku(sku: str) -> Device | ExtraDevice | None:
    return _SKU_INDEX.get(sku)


def device_age_months(d: Device | ExtraDevice, as_of: date) -> float:
    delta_days = (as_of - d.launch_date).days
    return max(0.0, delta_days / 30.44)
