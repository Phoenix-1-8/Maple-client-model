"""
Market Pricing Agent.

For every device it computes a condition-normalized fair market value (weighted
average + recency weighting + condition weighting + outlier trimming) and then
applies Maple's Pricing Recommendation Formula to produce recommended SELL and
BUY prices for each Maple grade.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..pricing import recommend_all_conditions
from .base import Agent


class MarketPricingAgent(Agent):
    name = "market_pricing"
    title = "Market Pricing Agent"

    def run(self, db: Session, region: str = "IN") -> dict:
        vals = self.valuations(db, region=region)
        devices = []
        for sku, v in vals.items():
            recos = recommend_all_conditions(v.fair.fair_value, self.cfg)
            devices.append(
                {
                    "sku": sku,
                    "model": v.device.model,
                    "series": v.device.series,
                    "variant": v.device.variant,
                    "storage": v.device.storage,
                    "msrp": v.device.msrp,
                    "fair_value": v.fair.fair_value,
                    "fair_value_p25": v.fair.p25,
                    "fair_value_p75": v.fair.p75,
                    "confidence": v.fair.confidence,
                    "sample_size": v.fair.sample_size,
                    "recommendations": {c: r.to_dict() for c, r in recos.items()},
                }
            )
        devices.sort(key=lambda d: (d["series"], d["model"], d["storage"]))
        return {
            "agent": self.title,
            "region": region,
            "device_count": len(devices),
            "devices": devices,
        }

    def price_one(self, db: Session, sku: str, region: str = "IN") -> dict | None:
        vals = self.valuations(db, region=region)
        v = vals.get(sku)
        if not v:
            return None
        recos = recommend_all_conditions(v.fair.fair_value, self.cfg)
        return {
            "sku": sku,
            "model": v.device.model,
            "variant": v.device.variant,
            "storage": v.device.storage,
            "msrp": v.device.msrp,
            "fair_value": v.fair.__dict__,
            "recommendations": {c: r.to_dict() for c, r in recos.items()},
        }
