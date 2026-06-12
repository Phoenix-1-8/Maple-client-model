"""
Inventory Agent.

Identifies:
  * high-demand models      (liquid + fast-moving + recent series)
  * underpriced models      (cheapest live offer far below fair value -> buy)
  * oversupplied models     (supply well above the catalogue norm -> hold price)
  * inventory gaps           (too few listings to source reliably)

Also emits per-model pricing recommendations (Superb grade) and inventory KPIs.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy.orm import Session

from ..catalog import all_devices
from ..pricing import recommend_prices
from .base import Agent


class InventoryAgent(Agent):
    name = "inventory"
    title = "Inventory Agent"

    def run(self, db: Session, region: str = "IN") -> dict:
        listings = self.load_listings(db, region=region)
        obs = self.observations(listings)

        norm_by_sku: dict[str, list[float]] = defaultdict(list)
        age_by_sku: dict[str, list[int]] = defaultdict(list)
        for l, o in zip(listings, obs):
            norm_by_sku[l.sku].append(o.normalized_price)
            age_by_sku[l.sku].append(o.age_days)

        vals = self.valuations(db, region=region)
        counts = {sku: len(p) for sku, p in norm_by_sku.items()}
        median_count = statistics.median(counts.values()) if counts else 0

        rows = []
        for sku, v in vals.items():
            prices = norm_by_sku[sku]
            count = counts[sku]
            avg_age = statistics.mean(age_by_sku[sku])
            best_buy = min(prices)
            fair = v.fair.fair_value
            underpricing_pct = (fair - best_buy) / fair if fair else 0.0
            # freshness: fresher listings churn => demand proxy
            freshness = 1.0 / (1.0 + avg_age / 14.0)
            series_recency = max(0.2, (v.device.series - 12) / 5.0)
            demand_score = round(
                100
                * min(1.0, (count / (median_count * 2 or 1)))
                * (0.5 + 0.5 * freshness)
                * (0.6 + 0.4 * series_recency),
                1,
            )
            reco = recommend_prices(fair, "Superb", self.cfg)
            rows.append(
                {
                    "sku": sku,
                    "model": v.device.model,
                    "series": v.device.series,
                    "variant": v.device.variant,
                    "storage": v.device.storage,
                    "listings": count,
                    "avg_listing_age_days": round(avg_age, 1),
                    "fair_value": fair,
                    "best_available_buy": round(best_buy),
                    "underpricing_pct": round(underpricing_pct * 100, 1),
                    "demand_score": demand_score,
                    "supply_ratio": round(count / median_count, 2) if median_count else 0.0,
                    "recommended_buy": reco.recommended_buy,
                    "recommended_sell": reco.recommended_sell,
                    "confidence": v.fair.confidence,
                }
            )

        high_demand = sorted(rows, key=lambda r: r["demand_score"], reverse=True)[:10]
        underpriced = sorted(rows, key=lambda r: r["underpricing_pct"], reverse=True)[:10]
        oversupplied = sorted(
            [r for r in rows if r["supply_ratio"] >= 1.6],
            key=lambda r: r["supply_ratio"],
            reverse=True,
        )[:10]

        # Inventory / coverage gaps: catalogue devices with too-thin listings.
        gaps = []
        for d in all_devices():
            c = counts.get(d.sku, 0)
            if c < max(2, median_count * 0.35):
                gaps.append(
                    {
                        "sku": d.sku,
                        "model": d.model,
                        "variant": d.variant,
                        "storage": d.storage,
                        "listings": c,
                    }
                )
        gaps.sort(key=lambda g: g["listings"])

        return {
            "agent": self.title,
            "region": region,
            "kpis": {
                "models_tracked": len(rows),
                "catalogue_size": len(all_devices()),
                "median_listings_per_model": round(median_count, 1),
                "avg_confidence": round(
                    statistics.mean([r["confidence"] for r in rows]), 2
                ) if rows else 0.0,
                "coverage_gaps": len(gaps),
            },
            "high_demand": high_demand,
            "underpriced": underpriced,
            "oversupplied": oversupplied,
            "inventory_gaps": gaps[:15],
        }
