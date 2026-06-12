"""
The pricing brain.

Two responsibilities:

1. fair_market_value(...) — turn a noisy bag of listings (different conditions,
   cities, platforms, ages) into ONE condition-normalized fair value, using:
       * condition weighting   (normalize price to the 'Superb' reference grade)
       * recency weighting      (recent listings count more)
       * source weighting       (trusted platforms count more)
       * outlier trimming        (drop the cheapest/priciest tails)

2. recommend_prices(...) — apply Maple's Pricing Recommendation Formula:

       Recommended Selling Price =
           Market Median + Brand Premium + Warranty Premium + Maple Trust Premium

       Recommended Buying Price =
           Recommended Selling Price
           - Target Margin - Refurbishment Cost - Logistics Cost - Warranty Reserve

All knobs come from config (fully configurable).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date

from .config import MapleConfig, get_config


# --------------------------------------------------------------------------- #
# Observation normalization
# --------------------------------------------------------------------------- #
@dataclass
class Observation:
    normalized_price: float   # price restated to Superb / Delhi / retail reference
    weight: float
    raw_price: float
    platform: str
    city: str
    condition: str
    age_days: int


def recency_weight(age_days: float, half_life: float) -> float:
    if half_life <= 0:
        return 1.0
    return 0.5 ** (max(0.0, age_days) / half_life)


def restate_price(
    asking_price: float,
    *,
    condition: str | None = None,
    city: str | None = None,
    platform: str | None = None,
    cfg: MapleConfig | None = None,
) -> float:
    """Restate an observed price by dividing out ONLY the chosen structural effects.

    This is the key difference between *valuation* and *arbitrage*:
      * Fair value divides out condition + city + platform (estimate the value).
      * Competitor compare divides out condition + city, KEEPS platform
        (so platform price levels are comparable).
      * Arbitrage divides out condition only, KEEPS city + platform
        (so the geographic spread survives — that IS the opportunity).
    """
    cfg = cfg or get_config()
    p = asking_price
    if condition is not None:
        p /= cfg.condition_multipliers.get(condition, 1.0)
    if city is not None:
        p /= cfg.city_multipliers.get(city, 1.0)
    if platform is not None:
        pc = cfg.platform(platform)
        p /= pc.index if pc else 1.0
    return p


def _city_mult(cfg: MapleConfig, city: str) -> float:
    return cfg.city_multipliers.get(city, 1.0)


def _platform_index(cfg: MapleConfig, platform: str) -> float:
    p = cfg.platform(platform)
    return p.index if p else 1.0


def _platform_weight(cfg: MapleConfig, platform: str) -> float:
    p = cfg.platform(platform)
    return p.weight if p else 0.5


def build_observation(
    *,
    asking_price: float,
    platform: str,
    city: str,
    condition: str,
    listing_date: date,
    as_of: date,
    cfg: MapleConfig | None = None,
) -> Observation:
    cfg = cfg or get_config()
    cond_mult = cfg.condition_multipliers.get(condition, 1.0)
    cond_conf = cfg.condition_confidence.get(condition, 0.85)
    city_mult = _city_mult(cfg, city)
    plat_index = _platform_index(cfg, platform)

    # Restate the observed price to the reference: Superb grade, Delhi, retail level.
    normalized = asking_price / (cond_mult * city_mult * plat_index)

    age_days = max(0, (as_of - listing_date).days)
    w = (
        _platform_weight(cfg, platform)
        * recency_weight(age_days, cfg.pricing.recency_half_life_days)
        * cond_conf
    )
    return Observation(
        normalized_price=round(normalized, 2),
        weight=round(w, 4),
        raw_price=asking_price,
        platform=platform,
        city=city,
        condition=condition,
        age_days=age_days,
    )


# --------------------------------------------------------------------------- #
# Fair market value
# --------------------------------------------------------------------------- #
@dataclass
class FairValue:
    fair_value: float          # the condition-normalized central estimate (Superb)
    weighted_mean: float
    weighted_median: float
    p25: float
    p75: float
    low: float
    high: float
    sample_size: int
    confidence: float          # 0..1 — based on sample size & weight concentration


def _weighted_percentile(pairs: list[tuple[float, float]], q: float) -> float:
    """pairs = [(value, weight)] sorted by value. q in [0,1]."""
    if not pairs:
        return 0.0
    total = sum(w for _, w in pairs)
    if total <= 0:
        vals = [v for v, _ in pairs]
        idx = min(len(vals) - 1, int(q * len(vals)))
        return vals[idx]
    cum = 0.0
    target = q * total
    for v, w in pairs:
        cum += w
        if cum >= target:
            return v
    return pairs[-1][0]


def fair_market_value(
    observations: list[Observation], cfg: MapleConfig | None = None
) -> FairValue | None:
    cfg = cfg or get_config()
    obs = [o for o in observations if o.normalized_price > 0 and o.weight > 0]
    if not obs:
        return None

    obs.sort(key=lambda o: o.normalized_price)

    # Trim tails by count to kill scams / typos / overpriced flippers.
    n = len(obs)
    trim = cfg.pricing.trim_fraction
    cut = int(n * trim)
    trimmed = obs[cut: n - cut] if n - 2 * cut >= 3 else obs

    pairs = [(o.normalized_price, o.weight) for o in trimmed]
    wsum = sum(w for _, w in pairs) or 1.0

    weighted_mean = sum(v * w for v, w in pairs) / wsum
    weighted_median = _weighted_percentile(pairs, 0.50)
    p25 = _weighted_percentile(pairs, 0.25)
    p75 = _weighted_percentile(pairs, 0.75)

    # Primary fair value: blend robust median with weighted mean (60/40).
    fair = 0.6 * weighted_median + 0.4 * weighted_mean

    # Confidence: more samples + tighter spread => higher.
    spread = (p75 - p25) / fair if fair else 1.0
    size_factor = min(1.0, n / 12.0)
    confidence = max(0.05, min(0.99, size_factor * (1.0 - min(spread, 0.6))))

    return FairValue(
        fair_value=round(fair, 0),
        weighted_mean=round(weighted_mean, 0),
        weighted_median=round(weighted_median, 0),
        p25=round(p25, 0),
        p75=round(p75, 0),
        low=round(obs[0].normalized_price, 0),
        high=round(obs[-1].normalized_price, 0),
        sample_size=n,
        confidence=round(confidence, 2),
    )


# --------------------------------------------------------------------------- #
# Pricing Recommendation Formula
# --------------------------------------------------------------------------- #
@dataclass
class PriceRecommendation:
    condition: str
    market_median: float          # condition-adjusted market median (the base)
    brand_premium: float
    warranty_premium: float
    maple_trust_premium: float
    recommended_sell: float
    target_margin: float
    refurbishment_cost: float
    logistics_cost: float
    warranty_reserve: float
    recommended_buy: float
    expected_gross_margin: float       # INR
    expected_gross_margin_pct: float   # fraction of sell

    def to_dict(self) -> dict:
        return asdict(self)


def recommend_prices(
    fair_value_superb: float,
    condition: str,
    cfg: MapleConfig | None = None,
) -> PriceRecommendation:
    """Apply the configurable pricing formula for a given condition."""
    cfg = cfg or get_config()
    p = cfg.pricing
    cond_mult = cfg.condition_multipliers.get(condition, 1.0)

    # Condition-adjusted market median (the "Market Median" in the formula).
    market_median = fair_value_superb * cond_mult

    brand = market_median * p.brand_premium_pct
    warranty = market_median * p.warranty_premium_pct
    trust = market_median * p.maple_trust_premium_pct

    sell = market_median + brand + warranty + trust

    target_margin = sell * p.target_margin_pct
    buy = sell - target_margin - p.refurbishment_cost - p.logistics_cost - p.warranty_reserve

    # What Maple actually nets if it buys at `buy` and sells at `sell`.
    total_cost = buy + p.refurbishment_cost + p.logistics_cost + p.warranty_reserve
    gm = sell - total_cost
    gm_pct = gm / sell if sell else 0.0

    return PriceRecommendation(
        condition=condition,
        market_median=round(market_median, 0),
        brand_premium=round(brand, 0),
        warranty_premium=round(warranty, 0),
        maple_trust_premium=round(trust, 0),
        recommended_sell=round(sell, 0),
        target_margin=round(target_margin, 0),
        refurbishment_cost=round(p.refurbishment_cost, 0),
        logistics_cost=round(p.logistics_cost, 0),
        warranty_reserve=round(p.warranty_reserve, 0),
        recommended_buy=round(buy, 0),
        expected_gross_margin=round(gm, 0),
        expected_gross_margin_pct=round(gm_pct, 4),
    )


def recommend_all_conditions(
    fair_value_superb: float, cfg: MapleConfig | None = None
) -> dict[str, PriceRecommendation]:
    cfg = cfg or get_config()
    return {
        cond: recommend_prices(fair_value_superb, cond, cfg)
        for cond in cfg.condition_multipliers
    }
