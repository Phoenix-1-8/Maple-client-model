"""
Device Pricing Agent.

Where the Market Pricing Agent answers "what is each device worth?", this agent
answers the client's operational question: **"show me every device, broken down
by site, with every detail we can publicly scrape."**

For one device (SKU) it assembles:
  * device identity + economics (MSRP, age, depreciation, fair value, confidence)
  * Maple's recommended BUY / SELL for every grade
  * a per-platform ("per site") price breakdown — lowest / median / highest,
    comparable (condition-normalized) median, spread vs fair value, seller trust
  * a per-condition breakdown
  * the full, de-normalized listing feed with all scrapable attributes
    (colour, battery, warranty, accessories, seller rating, lock status, …)

and an `overview()` that powers the device picker / catalogue table.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy.orm import Session

from ..catalog import device_age_months, device_by_sku
from ..mock_data import depreciation
from ..pricing import recommend_all_conditions, recommend_prices, restate_price
from .base import Agent

# Listing attributes surfaced in the per-device feed (the "scrapable detail").
_LISTING_KEYS = (
    "platform", "region", "city", "condition", "raw_condition", "battery_health",
    "color", "storage", "seller_type", "seller_name", "seller_rating",
    "seller_reviews", "warranty", "accessories", "lock_status", "verified",
    "negotiable", "views", "asking_price", "asking_price_native", "currency",
    "listing_title", "url",
)


class DevicePricingAgent(Agent):
    name = "device_pricing"
    title = "Device Pricing Agent"

    # The dashboard tab's default view is the catalogue overview.
    def run(self, db: Session, region: str = "IN") -> dict:
        return self.overview(db, region=region)

    # ---- catalogue overview (device picker / table) --------------------- #
    def overview(self, db: Session, region: str = "IN") -> dict:
        listings = self.load_listings(db, region=region)
        by_sku = self.group_by_sku(listings)
        vals = self.valuations(db, region=region)

        devices = []
        for sku, v in vals.items():
            rows = by_sku.get(sku, [])
            asks = [l.asking_price for l in rows]
            superb = recommend_prices(v.fair.fair_value, "Superb", self.cfg)
            devices.append(
                {
                    "sku": sku,
                    "model": v.device.model,
                    "family": getattr(v.device, "family", "iPhone"),
                    "series": v.device.series,
                    "variant": v.device.variant,
                    "storage": v.device.storage,
                    "msrp": v.device.msrp,
                    "listings": len(rows),
                    "platforms": len({l.platform for l in rows}),
                    "lowest_price": round(min(asks)) if asks else None,
                    "median_price": round(statistics.median(asks)) if asks else None,
                    "fair_value": v.fair.fair_value,
                    "confidence": v.fair.confidence,
                    "recommended_buy": superb.recommended_buy,
                    "recommended_sell": superb.recommended_sell,
                }
            )
        devices.sort(key=lambda d: (d["series"], d["model"], d["storage"]))
        return {
            "agent": self.title,
            "region": region,
            "device_count": len(devices),
            "devices": devices,
        }

    # ---- one device, full per-site breakdown ---------------------------- #
    def breakdown(self, db: Session, sku: str, region: str = "IN") -> dict | None:
        device = device_by_sku(sku)
        if device is None:
            return None
        listings = self.load_listings(db, region=region, sku=sku)
        if not listings:
            return None

        # Fair value stays COMPETITOR-ONLY (own excluded) so the benchmark Maple
        # is measured against is never contaminated by Maple's own prices.
        fv = self.valuations(db, region=region).get(sku)
        fair_value = fv.fair.fair_value if fv else 0.0
        recos = recommend_all_conditions(fair_value, self.cfg)

        # …but the per-site table, the by-condition view and the listing feed DO
        # include Maple's own store (flagged is_own) so it shows alongside the market.
        listings = self.load_listings(db, region=region, sku=sku, include_own=True)

        asks = [l.asking_price for l in listings]
        cheapest = min(listings, key=lambda l: l.asking_price)

        age_m = device_age_months(device, self.as_of)

        return {
            "agent": self.title,
            "region": region,
            "device": {
                "sku": sku,
                "model": device.model,
                "family": getattr(device, "family", "iPhone"),
                "series": device.series,
                "variant": device.variant,
                "storage": device.storage,
                "msrp": device.msrp,
                "launch_date": device.launch_date.isoformat(),
                "age_months": round(age_m, 1),
                "depreciation_pct": round((1 - depreciation(age_m)) * 100, 1),
                "colors_seen": sorted({l.color for l in listings if l.color}),
            },
            "valuation": fv.fair.__dict__ if fv else None,
            "fair_value": fair_value,
            "recommendations": {c: r.to_dict() for c, r in recos.items()},
            "summary": {
                "total_listings": len(listings),
                "platforms": len({l.platform for l in listings}),
                "cities": len({l.city for l in listings}),
                "lowest_price": round(min(asks)),
                "median_price": round(statistics.median(asks)),
                "highest_price": round(max(asks)),
                "cheapest_platform": cheapest.platform,
                "cheapest_url": cheapest.url,
            },
            "by_platform": self._by_platform(listings, fair_value),
            "by_condition": self._by_condition(listings, fair_value),
            "listings": self._listing_feed(listings),
        }

    # ---- breakdown helpers ---------------------------------------------- #
    def _by_platform(self, listings, fair_value: float) -> list[dict]:
        groups: dict[str, list] = defaultdict(list)
        for l in listings:
            groups[l.platform].append(l)

        rows = []
        for key, rows_in in groups.items():
            pc = self.cfg.platform(key)
            asks = [l.asking_price for l in rows_in]
            # comparable = restate condition + city to the Superb/Delhi reference,
            # keeping the platform's own price level (apples-to-apples per site).
            comparable = [
                restate_price(l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg)
                for l in rows_in
            ]
            med = statistics.median(asks)
            ratings = [l.seller_rating for l in rows_in if l.seller_rating]
            natives = [l.asking_price_native for l in rows_in]
            rows.append(
                {
                    "platform": key,
                    "platform_name": pc.name if pc else key,
                    "role": pc.role if pc else "marketplace",
                    "is_own": bool(pc and pc.role == "own"),
                    "currency": pc.currency if pc else "INR",
                    "listings": len(rows_in),
                    "lowest_price": round(min(asks)),
                    "median_price": round(med),
                    "highest_price": round(max(asks)),
                    "median_native": round(statistics.median(natives)),
                    "comparable_median": round(statistics.median(comparable)),
                    "vs_fair_value_pct": round((med / fair_value - 1) * 100, 1) if fair_value else 0.0,
                    "avg_seller_rating": round(statistics.mean(ratings), 1) if ratings else None,
                    "verified_share_pct": round(
                        100 * sum(1 for l in rows_in if l.verified) / len(rows_in)
                    ),
                }
            )
        rows.sort(key=lambda r: r["median_price"])
        return rows

    def _by_condition(self, listings, fair_value: float) -> list[dict]:
        order = {g: i for i, g in enumerate(self.cfg.condition_multipliers)}
        groups: dict[str, list] = defaultdict(list)
        for l in listings:
            groups[l.condition].append(l)

        rows = []
        for cond, rows_in in groups.items():
            asks = [l.asking_price for l in rows_in]
            reco = recommend_prices(fair_value, cond, self.cfg)
            rows.append(
                {
                    "condition": cond,
                    "listings": len(rows_in),
                    "lowest_price": round(min(asks)),
                    "median_price": round(statistics.median(asks)),
                    "avg_battery_health": round(statistics.mean(l.battery_health for l in rows_in)),
                    "recommended_buy": reco.recommended_buy,
                    "recommended_sell": reco.recommended_sell,
                }
            )
        rows.sort(key=lambda r: order.get(r["condition"], 99))
        return rows

    def _listing_feed(self, listings) -> list[dict]:
        own_keys = {p.key for p in self.cfg.platforms if p.role == "own"}
        feed = []
        for l in sorted(listings, key=lambda x: x.asking_price):
            item = {k: getattr(l, k) for k in _LISTING_KEYS}
            item["listing_date"] = l.listing_date.isoformat()
            item["is_own"] = l.platform in own_keys
            feed.append(item)
        return feed
