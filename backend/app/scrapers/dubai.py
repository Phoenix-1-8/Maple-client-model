"""Dubai resale adapter (Dubizzle / UAE marketplaces — AED, export arbitrage)."""
from __future__ import annotations

from .base import BaseScraper


class DubaiResaleScraper(BaseScraper):
    platform_key = "dubai_resale"
    platform_name = "Dubai Resale (Dubizzle)"
    region = "AE"
    base_url = "https://uae.dubizzle.com/mobile-phones-tablets-accessories-numbers/mobile-phones/apple/"
    selectors = {
        "card": "li[aria-label='Listing']",
        "price": "div[aria-label='Price']",
        "title": "h2[aria-label='Title']",
        "city": "span[aria-label='Location']",
    }
    # Prices on this platform are in AED; the base scraper / mock layer attaches
    # currency='AED' and an INR-converted asking_price for cross-market compare.
