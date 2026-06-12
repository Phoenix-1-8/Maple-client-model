"""Cashify adapter (recommerce / refurbished retail)."""
from __future__ import annotations

from .base import BaseScraper


class CashifyScraper(BaseScraper):
    platform_key = "cashify"
    platform_name = "Cashify"
    region = "IN"
    base_url = "https://www.cashify.in/buy-refurbished-mobile-phones/apple"
    selectors = {
        "card": "div[data-testid='product-card']",
        "title": "h3.product-title",
        "price": "span.price",
        "condition": "span.grade-tag",
        "storage": "span.variant-storage",
    }

    # Real implementation (sketch):
    #
    # def fetch_raw(self, devices=None):
    #     from playwright.sync_api import sync_playwright
    #     out = []
    #     with sync_playwright() as p:
    #         browser = (p.chromium.connect_over_cdp(self.proxy_endpoint)
    #                    if self.brightdata_enabled else p.chromium.launch())
    #         page = browser.new_page()
    #         page.goto(self.base_url, wait_until="networkidle")
    #         for card in page.query_selector_all(self.selectors["card"]):
    #             out.append({
    #                 "model": ..., "variant": ..., "storage": ...,
    #                 "raw_condition": card.query_selector(self.selectors["condition"]).inner_text(),
    #                 "asking_price": parse_price(...),
    #                 "city": "Delhi", "battery_health": None,
    #                 "listing_date": today(), "url": ...,
    #             })
    #         browser.close()
    #     return out
