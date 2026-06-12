"""
Dubai Expansion Agent.

Compares India vs Dubai prices for the same device/grade and computes the
cross-border opportunity:

    spread        = India market value - Dubai acquisition cost
    landed cost   = Dubai cost * (1 + import duty) + cross-border logistics
    margin        = Maple India sell price - landed cost - domestic costs
    export score  = 0..100 blend of margin% and two-sided liquidity

Prices are condition-adjusted to 'Superb' but keep the real regional price gap
(that gap is the whole opportunity).
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy.orm import Session

from ..catalog import device_by_sku
from ..pricing import recommend_prices, restate_price
from .base import Agent


class DubaiExpansionAgent(Agent):
    name = "dubai_expansion"
    title = "Dubai Expansion Agent"

    def run(self, db: Session, top_n: int = 20) -> dict:
        india = self._region_prices(db, "IN")
        dubai = self._region_prices(db, "AE")

        p = self.cfg.pricing
        skus = sorted(set(india) & set(dubai))
        opportunities = []
        for sku in skus:
            in_prices = india[sku]
            ae_prices = dubai[sku]
            if len(in_prices) < 2 or len(ae_prices) < 2:
                continue
            india_value = statistics.median(in_prices)
            dubai_cost = statistics.median(ae_prices)
            spread = india_value - dubai_cost
            spread_pct = spread / dubai_cost if dubai_cost else 0.0

            landed = dubai_cost * (1 + p.import_duty_pct) + p.cross_border_logistics
            sell = recommend_prices(india_value, "Superb", self.cfg).recommended_sell
            net_margin = sell - landed - p.refurbishment_cost - p.logistics_cost - p.warranty_reserve
            margin_pct = net_margin / sell if sell else 0.0

            liquidity = min(len(in_prices), len(ae_prices))
            score = max(
                0.0,
                min(100.0, margin_pct * 320 * min(1.0, liquidity / 4.0)),
            )
            device = device_by_sku(sku)
            opportunities.append(
                {
                    "sku": sku,
                    "model": device.model if device else sku,
                    "variant": device.variant if device else "",
                    "storage": device.storage if device else "",
                    "india_value": round(india_value),
                    "dubai_cost": round(dubai_cost),
                    "dubai_cost_aed": round(dubai_cost / self.cfg.aed_to_inr),
                    "spread": round(spread),
                    "spread_pct": round(spread_pct * 100, 1),
                    "landed_cost": round(landed),
                    "maple_sell": round(sell),
                    "net_margin": round(net_margin),
                    "margin_pct": round(margin_pct * 100, 1),
                    "export_opportunity_score": round(score, 1),
                    "direction": "Source in Dubai → sell in India"
                    if spread > 0
                    else "Source in India → sell in Dubai",
                    "units_observed": liquidity,
                }
            )

        opportunities.sort(key=lambda o: o["export_opportunity_score"], reverse=True)
        positive = [o for o in opportunities if o["net_margin"] > 0]
        # Crude monthly basis: per-unit margin x observed liquidity (mirrors the
        # Arbitrage Agent's spread x units convention so the two are comparable).
        total_margin_potential = sum(o["net_margin"] * o["units_observed"] for o in positive)
        return {
            "agent": self.title,
            "aed_to_inr": self.cfg.aed_to_inr,
            "import_duty_pct": round(p.import_duty_pct * 100, 1),
            "cross_border_logistics": round(p.cross_border_logistics),
            "domestic_costs": {
                "refurbishment": round(p.refurbishment_cost),
                "logistics": round(p.logistics_cost),
                "warranty_reserve": round(p.warranty_reserve),
            },
            "devices_compared": len(opportunities),
            "viable_opportunities": len(positive),
            "total_margin_potential": total_margin_potential,
            "avg_spread_pct": round(
                statistics.mean([o["spread_pct"] for o in opportunities]), 1
            ) if opportunities else 0.0,
            "opportunities": opportunities[:top_n],
        }

    def _region_prices(self, db: Session, region: str) -> dict[str, list[float]]:
        """sku -> condition-adjusted (Superb) prices for a region."""
        listings = self.load_listings(db, region=region)
        out: dict[str, list[float]] = defaultdict(list)
        for l in listings:
            out[l.sku].append(
                restate_price(l.asking_price, condition=l.condition, cfg=self.cfg)
            )
        return out
