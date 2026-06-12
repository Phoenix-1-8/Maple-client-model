"""Facebook Marketplace adapter (C2C, asking prices).

FB Marketplace is login-walled and heavily bot-protected; in production this
adapter routes through a BrightData authenticated session + residential proxy.
"""
from __future__ import annotations

from .base import BaseScraper


class FacebookScraper(BaseScraper):
    platform_key = "facebook"
    platform_name = "Facebook Marketplace"
    region = "IN"
    base_url = "https://www.facebook.com/marketplace/category/search/?query=iphone"
    selectors = {
        "card": "div[role='article']",
        "price": "span[dir='auto'] > span",
        "title": "span.x1lliihq",
        "city": "span.x1i10hfl",
    }
