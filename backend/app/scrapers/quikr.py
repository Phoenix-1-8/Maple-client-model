"""Quikr adapter (C2C marketplace, asking prices)."""
from __future__ import annotations

from .base import BaseScraper


class QuikrScraper(BaseScraper):
    platform_key = "quikr"
    platform_name = "Quikr"
    region = "IN"
    base_url = "https://www.quikr.com/mobiles-tablets/mobile-phones/apple+iphone"
    selectors = {
        "card": "div.card",
        "price": "span.price",
        "title": "a.ad-title",
        "city": "span.locality",
    }
