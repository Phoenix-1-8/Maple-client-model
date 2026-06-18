"""
Maple vs Market Agent — the "comparison" angle.

Answers the question the client wants on a slide: *how does Maple's own price
compare to the market, and is the premium justified?*

For each SKU Maple stocks we:
  1. Restate Maple's own listings to the Superb/Delhi reference, KEEPING the
     platform level (pricing.restate_price with condition+city only) — this is
     Maple's true price level, premium and all.
  2. Compare it to the market fair value (the competitor-only weighted central
     estimate from the shared pricing engine) and the competitor median.
  3. Decompose the premium: Maple's Pricing Formula says the justified premium
     is brand + warranty + trust (from PricingConfig). We surface how much of
     Maple's observed premium that explains.
  4. Buy-side: Maple's implied buy target (recommend_prices) vs the market low.

Maple's own listings are loaded with include_own=True; competitor valuations use
the default (own-excluded) path, so the benchmark is never contaminated.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy.orm import Session

from ..config import MAPLE_OWN_KEY
from ..pricing import recommend_prices, restate_price
from .base import Agent


class MapleComparisonAgent(Agent):
    name = "maple_comparison"
    title = "Maple vs Market Agent"

    def _own_key(self) -> str:
        own = self.cfg.own_platform()
        return own.key if own else MAPLE_OWN_KEY

    def run(self, db: Session, region: str = "IN") -> dict:
        own_key = self._own_key()

        # Market fair values (competitor-only; own excluded by default).
        valuations = self.valuations(db, region=region)

        # Maple's own listings, grouped by SKU.
        own_listings = [
            l for l in self.load_listings(db, region=region, include_own=True)
            if l.platform == own_key
        ]
        own_by_sku: dict[str, list] = defaultdict(list)
        for l in own_listings:
            own_by_sku[l.sku].append(l)

        # Competitor listings (for a simple competitor-median display).
        comp_by_sku: dict[str, list[float]] = defaultdict(list)
        for l in self.load_listings(db, region=region):
            comp_by_sku[l.sku].append(
                restate_price(l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg)
            )

        # Justified premium from the Pricing Formula (brand + warranty + trust).
        p = self.cfg.pricing
        justified_pct = round(
            (p.brand_premium_pct + p.warranty_premium_pct + p.maple_trust_premium_pct) * 100, 2
        )

        devices = []
        for sku, listings in own_by_sku.items():
            val = valuations.get(sku)
            if val is None:
                continue
            fair = val.fair.fair_value
            if not fair:
                continue

            # Maple's price restated to Superb/Delhi, keeping the platform level.
            maple_norm = [
                restate_price(l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg)
                for l in listings
            ]
            maple_level = statistics.median(maple_norm)
            maple_raw_median = statistics.median([l.asking_price for l in listings])

            comp_prices = comp_by_sku.get(sku, [])
            comp_median = statistics.median(comp_prices) if comp_prices else None

            premium_vs_fair = round((maple_level / fair - 1) * 100, 1)
            premium_vs_comp = (
                round((maple_level / comp_median - 1) * 100, 1) if comp_median else None
            )
            # How much of the observed premium the formula explains.
            explained = round(min(premium_vs_fair, justified_pct), 1) if premium_vs_fair > 0 else 0.0
            unexplained = round(max(0.0, premium_vs_fair - justified_pct), 1)

            buy_rec = recommend_prices(fair, "Superb", self.cfg).recommended_buy

            devices.append({
                "sku": sku,
                "model": val.device.model,
                "variant": val.device.variant,
                "storage": val.device.storage,
                "series": getattr(val.device, "series", None),
                "maple_price": round(maple_raw_median),
                "maple_price_normalized": round(maple_level),
                "market_fair_value": round(fair),
                "competitor_median": round(comp_median) if comp_median else None,
                "premium_vs_fair_pct": premium_vs_fair,
                "premium_vs_competitor_pct": premium_vs_comp,
                "justified_premium_pct": justified_pct,
                "premium_explained_pct": explained,
                "premium_unexplained_pct": unexplained,
                "verdict": self._verdict(premium_vs_fair, justified_pct),
                "maple_buy_target": round(buy_rec),
                "maple_units": len(listings),
                # Market-side reliability so the UI can flag thin comparisons.
                "market_sample_size": val.fair.sample_size,
                "market_confidence": val.fair.confidence,
            })

        devices.sort(key=lambda d: d["premium_vs_fair_pct"], reverse=True)
        return {
            "agent": self.title,
            "own_platform": own_key,
            "device_count": len(devices),
            "justified_premium_pct": justified_pct,
            "headline": self._headline(devices, justified_pct),
            "devices": devices,
            "premium_justification": {
                "brand_pct": round(p.brand_premium_pct * 100, 2),
                "warranty_pct": round(p.warranty_premium_pct * 100, 2),
                "trust_pct": round(p.maple_trust_premium_pct * 100, 2),
                "note": (
                    "Maple's certified, warrantied, trusted-reseller proposition "
                    "supports a structural premium over raw market value."
                ),
            },
        }

    def _verdict(self, premium: float, justified: float) -> str:
        if premium <= 0:
            return "At or below market"
        if premium <= justified + 1.0:
            return "Premium justified"
        if premium <= justified + 5.0:
            return "Slight premium over justified"
        return "Above justified premium"

    def _headline(self, devices: list[dict], justified: float) -> dict:
        if not devices:
            return {}
        weights = [d["maple_units"] for d in devices]
        wsum = sum(weights) or 1
        avg_premium = round(
            sum(d["premium_vs_fair_pct"] * w for d, w in zip(devices, weights)) / wsum, 1
        )
        above = sum(1 for d in devices if d["premium_vs_fair_pct"] > justified + 1.0)
        return {
            "avg_premium_vs_fair_pct": avg_premium,
            "justified_premium_pct": justified,
            "skus_above_justified": above,
            "skus_compared": len(devices),
            "summary": (
                f"Maple prices ~{avg_premium}% above market fair value; "
                f"~{justified}% is justified by certification, warranty and trust."
            ),
        }

    def breakdown(self, db: Session, sku: str, region: str = "IN") -> dict | None:
        """Per-SKU detail for the comparison drill-down."""
        full = self.run(db, region=region)
        for d in full["devices"]:
            if d["sku"] == sku:
                return {**d, "premium_justification": full["premium_justification"]}
        return None
