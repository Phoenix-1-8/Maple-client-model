"""ControlZ adapter (recommerce / refurbished retail)."""
from __future__ import annotations

from .base import BaseScraper


class ControlZScraper(BaseScraper):
    platform_key = "controlz"
    platform_name = "ControlZ"
    region = "IN"
    base_url = "https://control-z.in/collections/apple-iphone"
    selectors = {
        "card": "li.grid__item",
        "title": "a.full-unstyled-link",
        "price": "span.price-item--sale",
        "condition": "span.badge--condition",
    }
