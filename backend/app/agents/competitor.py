"""
Competitor Intelligence Agent.

Tracks, per platform:
  * lowest price        (cheapest condition-normalized offer)
  * median price        (typical condition-normalized offer)
  * premium sellers      (platforms structurally above market)
  * price movement       (market index 1d / 7d / 30d)

It restates every listing to the 'Superb / Delhi' reference so platforms are
compared apples-to-apples regardless of grade vocabulary or city mix.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import MarketDaily
from ..pricing import restate_price
from .base import Agent


class CompetitorIntelligenceAgent(Agent):
    name = "competitor_intelligence"
    title = "Competitor Intelligence Agent"

    def run(self, db: Session) -> dict:
        listings = self.load_listings(db, region="IN")

        # Restate to 'Superb / Delhi' but KEEP each platform's own price level,
        # so we can rank platforms from aggressive-discount to premium.
        by_platform: dict[str, list[float]] = defaultdict(list)
        age_by_platform: dict[str, list[int]] = defaultdict(list)
        all_norm: list[float] = []
        for l, o in zip(listings, self.observations(listings)):
            comp = restate_price(
                l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg
            )
            by_platform[l.platform].append(comp)
            age_by_platform[l.platform].append(o.age_days)
            all_norm.append(comp)

        # market reference = median of all comparable prices
        market_median = statistics.median(all_norm) if all_norm else 0.0
        market_lowest = min(all_norm) if all_norm else 0.0

        rankings = []
        for p in self.cfg.platforms:
            if p.region != "IN":
                continue
            prices = by_platform.get(p.key, [])
            if not prices:
                continue
            med = statistics.median(prices)
            price_index = med / market_median if market_median else 1.0
            rankings.append(
                {
                    "platform": p.key,
                    "platform_name": p.name,
                    "role": p.role,
                    "listings": len(prices),
                    "lowest_price": round(min(prices)),
                    "median_price": round(med),
                    "price_index": round(price_index, 3),
                    "position": self._position(price_index),
                    "avg_listing_age_days": round(statistics.mean(age_by_platform[p.key]), 1),
                }
            )
        rankings.sort(key=lambda r: r["price_index"])

        premium_sellers = [r for r in rankings if r["price_index"] >= 1.02]
        value_sellers = [r for r in rankings if r["price_index"] <= 0.95]

        return {
            "agent": self.title,
            "market_lowest": round(market_lowest),
            "market_median": round(market_median),
            "competitor_rankings": rankings,
            "premium_sellers": premium_sellers,
            "value_sellers": value_sellers,
            "price_movement": self._movement(db),
            "platforms_tracked": len(rankings),
            "price_heatmap": self._heatmap(listings),
        }

    def _heatmap(self, listings) -> dict:
        """Platform x series price-index matrix (1.0 == that series' market median)."""
        series_list = sorted({l.series for l in listings})
        # comparable price per (platform, series) and per series overall
        cell: dict[tuple[str, int], list[float]] = defaultdict(list)
        per_series: dict[int, list[float]] = defaultdict(list)
        for l in listings:
            comp = restate_price(
                l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg
            )
            cell[(l.platform, l.series)].append(comp)
            per_series[l.series].append(comp)
        series_med = {s: statistics.median(v) for s, v in per_series.items() if v}

        rows = []
        for p in self.cfg.platforms:
            if p.region != "IN":
                continue
            cells = []
            for s in series_list:
                vals = cell.get((p.key, s), [])
                if vals and series_med.get(s):
                    med = statistics.median(vals)
                    cells.append(
                        {
                            "series": s,
                            "index": round(med / series_med[s], 3),
                            "median_price": round(med),
                            "n": len(vals),
                        }
                    )
                else:
                    cells.append({"series": s, "index": None, "median_price": None, "n": 0})
            rows.append({"platform": p.key, "platform_name": p.name, "cells": cells})
        return {"series": series_list, "rows": rows}

    def _position(self, idx: float) -> str:
        if idx >= 1.04:
            return "Premium"
        if idx >= 1.0:
            return "Above market"
        if idx >= 0.93:
            return "Value"
        return "Aggressive discount"

    def _movement(self, db: Session) -> dict:
        rows = list(
            db.scalars(select(MarketDaily).order_by(MarketDaily.day.asc()))
        )
        if not rows:
            return {"index": 0.0, "change_1d_pct": 0.0, "change_7d_pct": 0.0, "change_30d_pct": 0.0}

        def pct(curr: float, prev: float) -> float:
            return round((curr - prev) / prev * 100, 2) if prev else 0.0

        latest = rows[-1].index_value
        d1 = rows[-2].index_value if len(rows) >= 2 else latest
        d7 = rows[-8].index_value if len(rows) >= 8 else rows[0].index_value
        d30 = rows[-31].index_value if len(rows) >= 31 else rows[0].index_value
        return {
            "index": round(latest, 2),
            "change_1d_pct": pct(latest, d1),
            "change_7d_pct": pct(latest, d7),
            "change_30d_pct": pct(latest, d30),
        }
