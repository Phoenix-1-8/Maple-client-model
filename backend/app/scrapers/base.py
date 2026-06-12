"""
Scraper base class — modular, BrightData-compatible architecture.

Each adapter declares WHERE and HOW to scrape a platform (search URL template,
DOM selectors, pagination) and implements ``fetch_raw()`` using Playwright,
optionally routed through a BrightData "Web Unlocker" / proxy.

Reality of the pre-owned market: most of these sites aggressively block bots.
So every adapter is wrapped in a resilience contract:

    scrape() -> fetch_raw()         # real listings, normalized
              -> on ANY failure     # blocked, captcha, layout change, no network
              -> mock fallback       # synthetic-but-consistent listings

This is exactly what keeps the pilot "always functional" for a live demo.

Output of every scraper is a list of normalized listing dicts:
    {
        platform, model, variant, storage, battery_health, condition,
        city, asking_price, listing_date, url,
        # plus enrichment used downstream:
        region, sku, series, raw_condition, asking_price_native, currency, seller_type
    }
"""
from __future__ import annotations

import os
import random
import zlib
from datetime import date

from ..config import MapleConfig, get_config
from ..mock_data import generate_platform_listings
from ..normalization import normalize_grade
from ..util import as_of_date


class ScrapeBlocked(RuntimeError):
    """Raised by fetch_raw() when the platform blocks the scrape."""


class BaseScraper:
    platform_key: str = ""
    platform_name: str = ""
    region: str = "IN"
    base_url: str = ""
    # Per-platform selector map — illustrative, the real values live here.
    selectors: dict[str, str] = {}

    def __init__(self, cfg: MapleConfig | None = None):
        self.cfg = cfg or get_config()

    # --- BrightData / Playwright wiring ---------------------------------- #
    @property
    def brightdata_enabled(self) -> bool:
        return bool(os.getenv("BRIGHTDATA_API_KEY")) or bool(os.getenv("BRIGHTDATA_WSS"))

    @property
    def proxy_endpoint(self) -> str | None:
        # e.g. wss://brd-customer-XXX:pass@brd.superproxy.io:9222 (CDP) for Playwright
        return os.getenv("BRIGHTDATA_WSS") or None

    def fetch_raw(self, devices: list | None = None) -> list[dict]:
        """Real scrape. Override in adapters.

        Default raises ScrapeBlocked so the resilience contract kicks in and the
        pilot stays functional even with zero network / no Playwright install.
        """
        raise ScrapeBlocked(
            f"{self.platform_key}: live scraping not available in this environment"
        )

    # --- public entrypoint ----------------------------------------------- #
    def scrape(self, as_of: date | None = None) -> tuple[list[dict], str]:
        """Return (listings, source) where source in {'live','mock'}."""
        as_of = as_of or as_of_date()
        try:
            raw = self.fetch_raw()
            if raw:
                return [self._postprocess(r) for r in raw], "live"
            raise ScrapeBlocked(f"{self.platform_key}: empty result")
        except Exception as exc:  # noqa: BLE001 - resilience by design
            # Seed derived from platform so each scraper's mock stream is stable
            # yet distinct (crc32: str hash() is randomized per process).
            seed = self.cfg.infra.mock_seed + (zlib.crc32(self.platform_key.encode()) % 9973)
            rng = random.Random(seed)
            listings = generate_platform_listings(self.cfg, self.platform_key, as_of, rng)
            return listings, "mock"

    def _postprocess(self, raw: dict) -> dict:
        """Normalize a raw scraped record into the canonical schema.

        Maps the platform's grade vocabulary into the Maple Condition System.
        """
        raw = dict(raw)
        raw.setdefault("platform", self.platform_key)
        raw.setdefault("region", self.region)
        raw["condition"] = normalize_grade(
            raw.get("raw_condition") or raw.get("condition"),
            raw.get("battery_health"),
        )
        return raw
