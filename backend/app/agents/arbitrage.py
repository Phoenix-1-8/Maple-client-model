"""
Arbitrage Agent.

Finds Buy-Low -> Sell-High opportunities across Indian cities.

    Delhi market   = ₹42,000
    Mumbai market  = ₹48,000
    => flag a ₹6,000 (14%) spread.

Prices are condition-normalized to the 'Superb' reference so a cheap Fair unit
in one city is not mistaken for a genuine geographic spread.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from sqlalchemy.orm import Session

from ..pricing import restate_price
from .base import Agent


class ArbitrageAgent(Agent):
    name = "arbitrage"
    title = "Arbitrage Agent"

    def run(self, db: Session, top_n: int = 20) -> dict:
        listings = self.load_listings(db, region="IN")

        # Arbitrage only makes sense on C2C marketplaces where Maple can actually
        # buy a physical unit in one city and resell in another.
        marketplace_keys = {
            p.key for p in self.cfg.platforms if p.role == "marketplace"
        }
        listings = [l for l in listings if l.platform in marketplace_keys]

        # (sku, city) -> condition-adjusted prices (KEEP the geographic spread)
        cells: dict[tuple[str, str], list[float]] = defaultdict(list)
        for l in listings:
            price = restate_price(l.asking_price, condition=l.condition, cfg=self.cfg)
            cells[(l.sku, l.city)].append(price)

        # sku -> {city: median_price}
        by_sku: dict[str, dict[str, float]] = defaultdict(dict)
        counts: dict[str, dict[str, int]] = defaultdict(dict)
        from ..catalog import device_by_sku

        min_samples = self.cfg.pricing.min_city_samples
        for (sku, city), prices in cells.items():
            if len(prices) < min_samples:
                continue
            by_sku[sku][city] = statistics.median(prices)
            counts[sku][city] = len(prices)

        opportunities = []
        threshold = self.cfg.pricing.min_arbitrage_spread_pct
        for sku, city_prices in by_sku.items():
            if len(city_prices) < 2:
                continue
            buy_city = min(city_prices, key=city_prices.get)
            sell_city = max(city_prices, key=city_prices.get)
            buy_price = city_prices[buy_city]
            sell_price = city_prices[sell_city]
            spread = sell_price - buy_price
            spread_pct = spread / buy_price if buy_price else 0.0
            if spread_pct < threshold:
                continue
            device = device_by_sku(sku)
            liquidity = min(counts[sku][buy_city], counts[sku][sell_city])
            # crude expected monthly capture value
            opp_value = round(spread * liquidity)
            opportunities.append(
                {
                    "sku": sku,
                    "model": device.model if device else sku,
                    "variant": device.variant if device else "",
                    "storage": device.storage if device else "",
                    "buy_city": buy_city,
                    "sell_city": sell_city,
                    "buy_price": round(buy_price),
                    "sell_price": round(sell_price),
                    "spread": round(spread),
                    "spread_pct": round(spread_pct * 100, 1),
                    "units_observed": liquidity,
                    "opportunity_value": opp_value,
                    "city_prices": {c: round(v) for c, v in sorted(city_prices.items(), key=lambda x: x[1])},
                }
            )

        opportunities.sort(key=lambda x: x["opportunity_value"], reverse=True)
        total_value = sum(o["opportunity_value"] for o in opportunities)
        return {
            "agent": self.title,
            "opportunities_found": len(opportunities),
            "total_opportunity_value": total_value,
            "avg_spread_pct": round(
                statistics.mean([o["spread_pct"] for o in opportunities]), 1
            ) if opportunities else 0.0,
            "opportunities": opportunities[:top_n],
        }
