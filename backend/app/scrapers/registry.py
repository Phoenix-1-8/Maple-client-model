"""Scraper registry — discover, instantiate and run all adapters."""
from __future__ import annotations

from datetime import date

from ..config import get_config
from .apple_tradein import AppleTradeInScraper
from .base import BaseScraper
from .cashify import CashifyScraper
from .controlz import ControlZScraper
from .dubai import DubaiResaleScraper
from .facebook import FacebookScraper
from .olx import OLXScraper
from .quikr import QuikrScraper

SCRAPER_CLASSES: list[type[BaseScraper]] = [
    CashifyScraper,
    ControlZScraper,
    OLXScraper,
    QuikrScraper,
    FacebookScraper,
    AppleTradeInScraper,
    DubaiResaleScraper,
]


def get_scrapers() -> list[BaseScraper]:
    cfg = get_config()
    return [cls(cfg) for cls in SCRAPER_CLASSES]


def run_all_scrapers(as_of: date | None = None) -> tuple[list[dict], list[dict]]:
    """Run every adapter. Returns (all_listings, per_platform_report)."""
    all_listings: list[dict] = []
    report: list[dict] = []
    for scraper in get_scrapers():
        listings, source = scraper.scrape(as_of)
        all_listings.extend(listings)
        report.append(
            {
                "platform": scraper.platform_key,
                "platform_name": scraper.platform_name,
                "region": scraper.region,
                "source": source,          # 'live' or 'mock'
                "count": len(listings),
            }
        )
    return all_listings, report
