"""
Competitor Intelligence Agent.

Tracks, per platform:
  * lowest price        (cheapest condition-normalized offer)
  * median price        (typical condition-normalized offer)
  * premium sellers      (platforms structurally above market)
  * price movement       (market index 1d / 7d / 30d)

It restates every listing to the 'Superb / Delhi' reference so platforms are
compared apples-to-apples regardless of grade vocabulary or city mix.

Scope is the iPhone 13–17 universe (the pilot's market). Maple's OWN store is
NOT part of the competitor benchmark — the market median, lowest and the
per-series heatmap baseline are competitor-only. But because the sales team
wants to *see* where Maple sits, we append Maple as a flagged ``is_own`` row to
the rankings and the heatmap, measured against that competitor benchmark.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..catalog import SERIES_LAUNCH
from ..config import MAPLE_OWN_KEY
from ..models import MarketDaily
from ..pricing import restate_price
from .base import Agent

# The pilot's market: iPhone 13–17. Everything else (iPad/Mac/Watch/AirPods,
# series 30+) is out of scope for competitor intelligence.
IPHONE_SERIES = set(SERIES_LAUNCH)


class CompetitorIntelligenceAgent(Agent):
    name = "competitor_intelligence"
    title = "Competitor Intelligence Agent"

    def _iphone(self, listings):
        return [l for l in listings if l.series in IPHONE_SERIES]

    def _own_key(self) -> str:
        own = self.cfg.own_platform()
        return own.key if own else MAPLE_OWN_KEY

    def run(self, db: Session) -> dict:
        listings = self._iphone(self.load_listings(db, region="IN"))

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

        # market reference = median of all comparable COMPETITOR prices (own excluded)
        market_median = statistics.median(all_norm) if all_norm else 0.0
        market_lowest = min(all_norm) if all_norm else 0.0

        rankings = []
        for p in self.cfg.competitor_platforms(region="IN"):
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
                    "is_own": False,
                    "listings": len(prices),
                    "lowest_price": round(min(prices)),
                    "median_price": round(med),
                    "price_index": round(price_index, 3),
                    "position": self._position(price_index),
                    "avg_listing_age_days": round(statistics.mean(age_by_platform[p.key]), 1),
                }
            )

        # Maple's own store as a flagged row, measured against the competitor median.
        own_row = self._own_ranking(db, market_median)
        if own_row:
            rankings.append(own_row)
        rankings.sort(key=lambda r: r["price_index"])

        premium_sellers = [r for r in rankings if not r["is_own"] and r["price_index"] >= 1.02]
        value_sellers = [r for r in rankings if not r["is_own"] and r["price_index"] <= 0.95]

        return {
            "agent": self.title,
            "market_lowest": round(market_lowest),
            "market_median": round(market_median),
            "competitor_rankings": rankings,
            "premium_sellers": premium_sellers,
            "value_sellers": value_sellers,
            "price_movement": self._movement(db),
            "platforms_tracked": sum(1 for r in rankings if not r["is_own"]),
            "price_heatmap": self._heatmap(listings, db),
        }

    # ------------------------------------------------------------------ #
    # Maple own-store overlay
    # ------------------------------------------------------------------ #
    def _own_listings(self, db: Session, region: str = "IN"):
        own_key = self._own_key()
        return own_key, self._iphone(
            [
                l
                for l in self.load_listings(db, region=region, include_own=True)
                if l.platform == own_key
            ]
        )

    def _own_ranking(self, db: Session, market_median: float) -> dict | None:
        own_key, own_rows = self._own_listings(db)
        if not own_rows:
            return None
        norm = [
            restate_price(l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg)
            for l in own_rows
        ]
        ages = [o.age_days for o in self.observations(own_rows)]
        med = statistics.median(norm)
        idx = med / market_median if market_median else 1.0
        own_cfg = self.cfg.own_platform()
        return {
            "platform": own_key,
            "platform_name": own_cfg.name if own_cfg else "Maple Store",
            "role": "own",
            "is_own": True,
            "listings": len(norm),
            "lowest_price": round(min(norm)),
            "median_price": round(med),
            "price_index": round(idx, 3),
            "position": "Your store",
            "avg_listing_age_days": round(statistics.mean(ages), 1) if ages else 0.0,
        }

    def _heatmap(self, listings, db: Session) -> dict:
        """Platform x series price-index matrix (1.0 == that series' competitor median).

        Series axis is iPhone 13–17 only. Maple's own store is appended as a
        flagged row, indexed to the SAME competitor series median.
        """
        series_list = sorted({l.series for l in listings} & IPHONE_SERIES)
        # comparable price per (platform, series) and per series overall (competitors)
        cell: dict[tuple[str, int], list[float]] = defaultdict(list)
        per_series: dict[int, list[float]] = defaultdict(list)
        for l in listings:
            comp = restate_price(
                l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg
            )
            cell[(l.platform, l.series)].append(comp)
            per_series[l.series].append(comp)
        series_med = {s: statistics.median(v) for s, v in per_series.items() if v}

        def cells_for(by_series_or_cell, key_fn) -> list[dict]:
            out = []
            for s in series_list:
                vals = key_fn(s)
                if vals and series_med.get(s):
                    med = statistics.median(vals)
                    out.append(
                        {"series": s, "index": round(med / series_med[s], 3),
                         "median_price": round(med), "n": len(vals)}
                    )
                else:
                    out.append({"series": s, "index": None, "median_price": None, "n": 0})
            return out

        rows = []
        for p in self.cfg.competitor_platforms(region="IN"):
            rows.append({
                "platform": p.key,
                "platform_name": p.name,
                "is_own": False,
                "cells": cells_for(cell, lambda s, k=p.key: cell.get((k, s), [])),
            })

        # Maple own row (indexed to the competitor series median).
        own_key, own_rows = self._own_listings(db)
        if own_rows:
            own_cell: dict[int, list[float]] = defaultdict(list)
            for l in own_rows:
                own_cell[l.series].append(
                    restate_price(l.asking_price, condition=l.condition, city=l.city, cfg=self.cfg)
                )
            own_cfg = self.cfg.own_platform()
            rows.insert(0, {
                "platform": own_key,
                "platform_name": own_cfg.name if own_cfg else "Maple Store",
                "is_own": True,
                "cells": cells_for(own_cell, lambda s: own_cell.get(s, [])),
            })

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
