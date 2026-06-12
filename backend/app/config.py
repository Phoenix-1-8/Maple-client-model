"""
Central configuration for the Maple Store AI Department.

Everything the business team would want to tune lives here:
  * pricing premiums & cost structure (the Pricing Recommendation Formula)
  * condition weighting & normalization
  * platform trust / weighting
  * city price multipliers (the basis for arbitrage)
  * competitor grade -> Maple grade mapping

Values can be overridden in three layers (lowest -> highest priority):
  1. The defaults in this file.
  2. A JSON file at  $MAPLE_CONFIG_FILE  (default: ./maple_config.json if present).
  3. Environment variables (for infra-level settings only).

This keeps the pilot "investor demo ready" out of the box while remaining
fully reconfigurable for production.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

# Load backend/.env (if present) before any os.getenv() default is evaluated.
# Real environment variables (docker-compose, Makefile) still win (override=False).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:  # python-dotenv optional; ignore if absent
    pass


# --------------------------------------------------------------------------- #
# Infrastructure settings (env driven)
# --------------------------------------------------------------------------- #
@dataclass
class InfraSettings:
    # Default to SQLite so the backend runs on a laptop with zero services.
    # docker-compose overrides this to point at Postgres.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./maple.db")
    redis_url: str = os.getenv("REDIS_URL", "")  # empty => synchronous fallback
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
    )
    seed_on_startup: bool = os.getenv("SEED_ON_STARTUP", "true").lower() == "true"
    mock_seed: int = int(os.getenv("MAPLE_MOCK_SEED", "42"))
    # How many days of synthetic market history to generate for trend charts.
    history_days: int = int(os.getenv("MAPLE_HISTORY_DAYS", "60"))


# --------------------------------------------------------------------------- #
# Maple Condition System & competitor grade normalization
# --------------------------------------------------------------------------- #
# Canonical Maple grades, best -> worst.
MAPLE_GRADES = ["Almost New", "Superb", "Good", "Fair"]

# Condition weighting: how a device's grade scales fair-market value relative to
# the reference grade ("Superb" == 1.00). Used by the Market Pricing Agent for
# condition normalization and by the pricing formula.
DEFAULT_CONDITION_MULTIPLIERS: dict[str, float] = {
    "Almost New": 1.06,
    "Superb": 1.00,
    "Good": 0.90,
    "Fair": 0.78,
}

# Confidence we place in each grade when computing the weighted central value.
# Lower grades are noisier (more subjective), so they get slightly less weight.
DEFAULT_CONDITION_CONFIDENCE: dict[str, float] = {
    "Almost New": 1.00,
    "Superb": 1.00,
    "Good": 0.90,
    "Fair": 0.80,
}

# Configurable mapping of competitor grades -> Maple grades.
# Keys are lower-cased competitor grade strings. Extend freely.
DEFAULT_GRADE_MAP: dict[str, str] = {
    # Almost New
    "mint": "Almost New",
    "like new": "Almost New",
    "as good as new": "Almost New",
    "open box": "Almost New",
    "pristine": "Almost New",
    "a+": "Almost New",
    "grade a+": "Almost New",
    "almost new": "Almost New",
    "flawless": "Almost New",
    # Superb
    "excellent": "Superb",
    "superb": "Superb",
    "very good": "Superb",
    "a": "Superb",
    "grade a": "Superb",
    "superb condition": "Superb",
    "lightly used": "Superb",
    # Good
    "good": "Good",
    "b": "Good",
    "grade b": "Good",
    "fine": "Good",
    "used - good": "Good",
    # Fair
    "fair": "Fair",
    "average": "Fair",
    "ok": "Fair",
    "okay": "Fair",
    "acceptable": "Fair",
    "c": "Fair",
    "grade c": "Fair",
    "poor": "Fair",
    "heavily used": "Fair",
    "partially functional": "Fair",
}


# --------------------------------------------------------------------------- #
# Platform configuration
# --------------------------------------------------------------------------- #
# role:
#   recommerce  -> refurbished retail (with warranty), sell-side reference
#   marketplace -> C2C asking prices (optimistic, negotiable)
#   tradein     -> buy-back / trade-in quotes (low, buy-side)
# weight: trust placed in the source when computing fair-market value.
# index : structural price level of the platform vs the market reference.
# region: "IN" or "AE".
@dataclass
class PlatformConfig:
    key: str
    name: str
    role: str
    region: str
    weight: float
    index: float
    currency: str = "INR"


DEFAULT_PLATFORMS: list[PlatformConfig] = [
    PlatformConfig("cashify", "Cashify", "recommerce", "IN", 1.00, 0.98),
    PlatformConfig("controlz", "ControlZ", "recommerce", "IN", 0.95, 1.02),
    PlatformConfig("olx", "OLX", "marketplace", "IN", 0.80, 0.92),
    PlatformConfig("quikr", "Quikr", "marketplace", "IN", 0.70, 0.90),
    PlatformConfig("facebook", "Facebook Marketplace", "marketplace", "IN", 0.65, 0.88),
    PlatformConfig("apple_tradein", "Apple Trade-In", "tradein", "IN", 0.90, 0.60),
    PlatformConfig("dubai_resale", "Dubai Resale (Dubizzle)", "marketplace", "AE", 0.85, 0.83, "AED"),
]

# AED -> INR conversion used to compare Dubai listings against India.
DEFAULT_AED_TO_INR: float = 23.0


# --------------------------------------------------------------------------- #
# City configuration (drives arbitrage spreads)
# --------------------------------------------------------------------------- #
DEFAULT_CITY_MULTIPLIERS: dict[str, float] = {
    # India
    "Mumbai": 1.04,
    "Delhi": 1.00,
    "Bengaluru": 1.05,
    "Hyderabad": 0.99,
    "Chennai": 0.98,
    "Pune": 1.01,
    "Kolkata": 0.97,
    "Ahmedabad": 0.96,
    "Jaipur": 0.95,
    "Lucknow": 0.93,
    # UAE
    "Dubai": 1.00,
    "Sharjah": 0.97,
    "Abu Dhabi": 1.01,
}

INDIA_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
]
DUBAI_CITIES = ["Dubai", "Sharjah", "Abu Dhabi"]


# --------------------------------------------------------------------------- #
# Pricing Recommendation Formula
# --------------------------------------------------------------------------- #
# Recommended Selling Price =
#     Market Median
#   + Brand Premium
#   + Warranty Premium
#   + Maple Trust Premium
#
# Recommended Buying Price =
#     Recommended Selling Price
#   - Target Margin
#   - Refurbishment Cost
#   - Logistics Cost
#   - Warranty Reserve
#
# Premiums are expressed as a fraction of the condition-adjusted market median.
# Costs are flat INR amounts (defensible, tier-able) so they read clearly on a
# demo slide.  All are overridable.
@dataclass
class PricingConfig:
    brand_premium_pct: float = 0.015        # Apple brand strength
    warranty_premium_pct: float = 0.035     # Maple bundles a warranty
    maple_trust_premium_pct: float = 0.030  # certified / trusted reseller premium

    target_margin_pct: float = 0.14         # gross margin Maple wants to lock in
    refurbishment_cost: float = 1200.0      # avg parts + labour to certify
    logistics_cost: float = 450.0           # inbound + outbound + handling
    warranty_reserve: float = 800.0         # provision for warranty claims

    # Recency weighting: a listing's weight decays with age.
    # weight_recency = 0.5 ** (age_days / recency_half_life_days)
    recency_half_life_days: float = 21.0

    # Outlier trimming when computing the weighted central value (fraction each side).
    trim_fraction: float = 0.10

    # Cross-border (Dubai <-> India) economics used by the Dubai Expansion Agent.
    import_duty_pct: float = 0.18          # customs + GST on imported handset value
    cross_border_logistics: float = 1500.0  # freight + clearing + last-mile per unit

    # Arbitrage thresholds.
    min_arbitrage_spread_pct: float = 0.06  # ignore inter-city spreads below this
    min_city_samples: int = 2               # need this many listings per city to trust it


# --------------------------------------------------------------------------- #
# Metric baselines (so KPIs read against a credible "before AI" baseline)
# --------------------------------------------------------------------------- #
@dataclass
class MetricBaselines:
    baseline_gross_margin_pct: float = 0.11      # margin before the AI Dept
    baseline_inventory_turns_per_year: float = 6.0
    target_inventory_turns_per_year: float = 8.4
    baseline_purchase_accuracy: float = 0.74     # % buys within target band before
    baseline_pricing_accuracy: float = 0.79      # % sells within fair band before
    target_platform_count: int = 14              # competitors Maple wants covered
    # Assumed monthly units to convert per-unit gains into rupee value.
    assumed_monthly_units: int = 900


# --------------------------------------------------------------------------- #
# Aggregate config object
# --------------------------------------------------------------------------- #
@dataclass
class MapleConfig:
    infra: InfraSettings = field(default_factory=InfraSettings)
    pricing: PricingConfig = field(default_factory=PricingConfig)
    baselines: MetricBaselines = field(default_factory=MetricBaselines)
    condition_multipliers: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CONDITION_MULTIPLIERS)
    )
    condition_confidence: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CONDITION_CONFIDENCE)
    )
    grade_map: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_GRADE_MAP))
    city_multipliers: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_CITY_MULTIPLIERS)
    )
    platforms: list[PlatformConfig] = field(
        default_factory=lambda: list(DEFAULT_PLATFORMS)
    )
    aed_to_inr: float = DEFAULT_AED_TO_INR

    # ---- convenience lookups -------------------------------------------- #
    def platform(self, key: str) -> PlatformConfig | None:
        return next((p for p in self.platforms if p.key == key), None)

    def platform_keys(self, region: str | None = None) -> list[str]:
        return [p.key for p in self.platforms if region is None or p.region == region]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    # ---- JSON override loader ------------------------------------------- #
    def apply_overrides(self, data: dict[str, Any]) -> None:
        if not data:
            return
        for section in ("pricing", "baselines"):
            if section in data and isinstance(data[section], dict):
                target = getattr(self, section)
                for k, v in data[section].items():
                    if hasattr(target, k):
                        setattr(target, k, v)
        for mapping in ("condition_multipliers", "condition_confidence",
                        "grade_map", "city_multipliers"):
            if mapping in data and isinstance(data[mapping], dict):
                getattr(self, mapping).update(data[mapping])
        if "aed_to_inr" in data:
            self.aed_to_inr = float(data["aed_to_inr"])
        if "platforms" in data and isinstance(data["platforms"], list):
            self.platforms = [PlatformConfig(**p) for p in data["platforms"]]


@lru_cache(maxsize=1)
def get_config() -> MapleConfig:
    cfg = MapleConfig()
    path = os.getenv("MAPLE_CONFIG_FILE", "maple_config.json")
    p = Path(path)
    if p.exists():
        try:
            cfg.apply_overrides(json.loads(p.read_text()))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[config] Failed to load {p}: {exc}")
    return cfg


def reset_config_cache() -> None:
    get_config.cache_clear()
