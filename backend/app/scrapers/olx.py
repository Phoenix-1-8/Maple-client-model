"""OLX adapter (C2C marketplace, asking prices)."""
from __future__ import annotations

from .base import BaseScraper


class OLXScraper(BaseScraper):
    platform_key = "olx"
    platform_name = "OLX"
    region = "IN"
    base_url = "https://www.olx.in/items/q-iphone"
    selectors = {
        "card": "li[data-aut-id='itemBox']",
        "price": "span[data-aut-id='itemPrice']",
        "title": "span[data-aut-id='itemTitle']",
        "city": "span[data-aut-id='item-location']",
    }
