"""Apple Trade-In adapter (OEM buy-back quotes — buy-side reference)."""
from __future__ import annotations

from .base import BaseScraper


class AppleTradeInScraper(BaseScraper):
    platform_key = "apple_tradein"
    platform_name = "Apple Trade-In"
    region = "IN"
    base_url = "https://www.apple.com/in/shop/trade-in"
    selectors = {
        # Apple's estimator is an interactive form, not a listing grid.
        "device_select": "select#device",
        "quote": "span.rc-tradein-value",
    }
