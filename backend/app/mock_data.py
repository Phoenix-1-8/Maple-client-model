"""
Synthetic but internally-consistent market generator.

When live scraping is blocked, the whole system still has to *work* and the
agents have to surface *real* signal.  We achieve that by generating listings
from a hidden ground-truth value model:

    true_superb_value(device, day)
        = MSRP * depreciation(age) * variant_retention

and then projecting each listing through the SAME multipliers the pricing
engine inverts:

    asking_price = true_value * condition_mult * city_mult * platform_index * noise

Because the multipliers are shared with config, the Market Pricing Agent
recovers the hidden value, the Arbitrage Agent finds the city spreads we baked
in, and the Dubai Agent finds the AED gap — i.e. the demo tells a true story.
"""
from __future__ import annotations

import math
import random
import zlib
from datetime import date, timedelta

from .catalog import Device, all_devices, device_age_months
from .config import (
    DUBAI_CITIES,
    INDIA_CITIES,
    MapleConfig,
    get_config,
)

# Competitor grade vocabularies — every phrase normalizes back to the Maple
# grade it is listed under (see normalization.DEFAULT_GRADE_MAP), but platforms
# use different words, which is exactly what the normalizer has to handle.
GRADE_SYNONYMS: dict[str, list[str]] = {
    "Almost New": ["Mint", "Like New", "Pristine", "Open Box"],
    "Superb": ["Excellent", "Superb", "Very Good"],
    "Good": ["Good", "Fine"],
    "Fair": ["Fair", "Average", "Acceptable"],
}

# Relative trading liquidity, used to size listing counts (creates supply gaps).
_SERIES_LIQUIDITY = {13: 0.70, 14: 0.90, 15: 1.10, 16: 1.00, 17: 0.60}
_VARIANT_POP = {"Base": 1.0, "Plus": 0.55, "Pro": 1.0, "Pro Max": 1.25, "Mini": 0.5}
_STORAGE_POP = {"128GB": 1.0, "256GB": 1.1, "512GB": 0.6, "1TB": 0.35}
_PLATFORM_VOLUME = {
    "cashify": 1.0,
    "controlz": 0.7,
    "olx": 1.4,
    "quikr": 1.0,
    "facebook": 1.1,
    "apple_tradein": 0.5,
    "dubai_resale": 0.8,
}
_PLATFORM_SELLER = {
    "cashify": "certified_refurbisher",
    "controlz": "certified_refurbisher",
    "olx": "individual",
    "quikr": "individual",
    "facebook": "individual",
    "apple_tradein": "oem_program",
    "dubai_resale": "individual",
}


def depreciation(age_months: float) -> float:
    """Fraction of MSRP retained by a 'Superb' used unit at a given age."""
    return 0.30 + 0.62 * math.exp(-0.030 * age_months)


def _variant_retention(variant: str) -> float:
    if variant in ("Pro", "Pro Max"):
        return 1.04
    if variant == "Mini":
        return 0.97
    return 1.0


def true_superb_value(device: Device, as_of: date) -> float:
    """Hidden ground-truth fair value (Superb grade, Delhi, retail reference)."""
    age = device_age_months(device, as_of)
    return device.msrp * depreciation(age) * _variant_retention(device.variant)


def _sentiment_series(days: int, rng: random.Random) -> list[float]:
    """Smooth market-sentiment multiplier per day, normalized so today == 1.0."""
    vals: list[float] = []
    drift = 0.0
    for t in range(days):
        cyclical = 0.012 * math.sin(2 * math.pi * t / 31.0)
        drift += rng.gauss(-0.0003, 0.0016)  # slow downward used-market drift
        drift = max(-0.05, min(0.05, drift))
        vals.append(1.0 + cyclical + drift)
    # Normalize so the most recent day is exactly 1.0 (anchors current listings).
    last = vals[-1]
    return [v / last for v in vals]


def _weighted_choice(rng: random.Random, options: list[str], weights: list[float]) -> str:
    return rng.choices(options, weights=weights, k=1)[0]


def _condition_for(age_months: float, rng: random.Random) -> str:
    newness = max(0.0, min(1.0, 1.0 - age_months / 60.0))
    weights = {
        "Almost New": 0.08 + 0.27 * newness,
        "Superb": 0.30 + 0.04 * newness,
        "Good": 0.37 - 0.12 * newness,
        "Fair": 0.25 - 0.19 * newness,
    }
    grades = list(weights.keys())
    return _weighted_choice(rng, grades, [max(0.02, weights[g]) for g in grades])


def _battery_for(condition: str, age_months: float, rng: random.Random) -> int:
    base = {"Almost New": 98, "Superb": 93, "Good": 88, "Fair": 82}[condition]
    base -= int(age_months * 0.12)
    val = base + rng.randint(-2, 2)
    return max(76, min(100, val))


def _listing_count(device: Device, platform_key: str, rng: random.Random) -> int:
    base = 4.0
    expected = (
        base
        * _SERIES_LIQUIDITY[device.series]
        * _VARIANT_POP[device.variant]
        * _STORAGE_POP[device.storage]
        * _PLATFORM_VOLUME.get(platform_key, 0.8)
    )
    # Poisson-ish via rounding with jitter; can legitimately be 0 (coverage gap).
    jitter = rng.uniform(0.7, 1.3)
    return max(0, int(round(expected * jitter)))


def _pick_city(region: str, rng: random.Random, platform_key: str) -> str:
    if platform_key == "apple_tradein":
        return "Delhi"  # OEM program quotes are national; anchor to Delhi (mult 1.0)
    if region == "AE":
        return _weighted_choice(rng, DUBAI_CITIES, [0.6, 0.2, 0.2])
    # India: bias toward metros
    weights = [1.4, 1.3, 1.3, 1.0, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
    return _weighted_choice(rng, INDIA_CITIES, weights)


def _noise(rng: random.Random) -> float:
    n = math.exp(rng.gauss(0.0, 0.05))
    if rng.random() < 0.05:  # occasional outlier (scam / typo / desperate seller)
        n *= rng.choice([0.78, 1.22])
    return n


def generate_platform_listings(
    cfg: MapleConfig, platform_key: str, as_of: date, rng: random.Random
) -> list[dict]:
    """Generate mock listings for a single platform (used as scraper fallback)."""
    platform = cfg.platform(platform_key)
    if platform is None:
        return []
    listings: list[dict] = []
    for device in all_devices():
        # Dubai resale skews to newer flagships; skip oldest series there.
        if platform.key == "dubai_resale" and device.series <= 13:
            continue
        true_val = true_superb_value(device, as_of)
        count = _listing_count(device, platform.key, rng)
        for _ in range(count):
            listings.append(
                _make_listing(cfg, device, platform, true_val, as_of, rng)
            )
    return listings


def _make_listing(cfg, device, platform, true_val, as_of, rng) -> dict:
    condition = _condition_for(device_age_months(device, as_of), rng)
    city = _pick_city(platform.region, rng, platform.key)
    cond_mult = cfg.condition_multipliers[condition]
    city_mult = cfg.city_multipliers.get(city, 1.0)
    inr_price = true_val * cond_mult * city_mult * platform.index * _noise(rng)
    inr_price = round(inr_price / 50) * 50  # round to ₹50

    if platform.currency == "AED":
        native = round(inr_price / cfg.aed_to_inr / 5) * 5
        inr_for_storage = round(native * cfg.aed_to_inr)
    else:
        native = inr_price
        inr_for_storage = inr_price

    battery = _battery_for(condition, device_age_months(device, as_of), rng)
    # Stable per-platform pick (crc32, not hash(): str hash is randomized per
    # process and would break demo reproducibility). Also leaves the rng stream
    # untouched so seeded numbers stay identical.
    raw_grade = GRADE_SYNONYMS[condition][
        (zlib.crc32(platform.key.encode()) >> 3) % len(GRADE_SYNONYMS[condition])
    ]
    age_days = int(rng.triangular(0, 45, 6))  # recency-skewed
    listing_date = as_of - timedelta(days=age_days)

    return {
        "platform": platform.key,
        "region": platform.region,
        "sku": device.sku,
        "series": device.series,
        "model": device.model,
        "variant": device.variant,
        "storage": device.storage,
        "battery_health": battery,
        "condition": condition,
        "raw_condition": raw_grade,
        "city": city,
        "asking_price": float(inr_for_storage),
        "asking_price_native": float(native),
        "currency": platform.currency,
        "seller_type": _PLATFORM_SELLER.get(platform.key, "individual"),
        "listing_date": listing_date,
        "url": f"https://demo.maple.local/{platform.key}/{device.sku}/{rng.randint(10000, 99999)}",
    }


def generate_listings(cfg: MapleConfig, as_of: date, rng: random.Random) -> list[dict]:
    """Generate the full mock market across every configured platform."""
    listings: list[dict] = []
    for platform in cfg.platforms:
        listings.extend(generate_platform_listings(cfg, platform.key, as_of, rng))
    return listings


def generate_history(
    cfg: MapleConfig, as_of: date, rng: random.Random
) -> tuple[list[dict], list[dict]]:
    """Return (market_daily_rows, device_daily_rows)."""
    days = max(1, cfg.infra.history_days)
    sentiment = _sentiment_series(days, rng)
    start = as_of - timedelta(days=days - 1)
    devices = all_devices()

    device_daily: list[dict] = []
    basket_by_day: list[float] = []

    for i in range(days):
        d = start + timedelta(days=i)
        s = sentiment[i]
        basket = 0.0
        for device in devices:
            fv = true_superb_value(device, d) * s
            # light idiosyncratic wiggle per device-day
            fv *= math.exp(rng.gauss(0.0, 0.006))
            fv = round(fv, 0)
            device_daily.append(
                {
                    "day": d,
                    "sku": device.sku,
                    "series": device.series,
                    "model": device.model,
                    "variant": device.variant,
                    "storage": device.storage,
                    "fair_value": fv,
                    "listing_count": 0,  # filled by seed from live listings for today
                }
            )
            basket += fv
        basket_by_day.append(basket)

    base = basket_by_day[0] or 1.0
    market_daily: list[dict] = []
    prev_index = 0.0
    for i in range(days):
        d = start + timedelta(days=i)
        index_value = round(100.0 * basket_by_day[i] / base, 2)
        movement = round((index_value - prev_index) / prev_index * 100, 2) if prev_index else 0.0
        market_daily.append(
            {
                "day": d,
                "index_value": index_value,
                "prev_index_value": round(prev_index, 2),
                "movement_pct": movement,
                "total_active_listings": 0,  # filled by seed
            }
        )
        prev_index = index_value
    return market_daily, device_daily


def build_rng(cfg: MapleConfig | None = None) -> random.Random:
    cfg = cfg or get_config()
    return random.Random(cfg.infra.mock_seed)
