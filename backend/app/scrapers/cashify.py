"""
Cashify adapter (recommerce / refurbished retail).

Cashify's catalogue page is a client-rendered React app (no usable SSR JSON on
the *category* page), but every individual product page ships a clean
``application/ld+json`` **ProductGroup** with one entry per
(condition × storage × colour) variant, each carrying an ``offers.price`` and
stock status. That structured data is far more reliable than scraping rendered
card markup, so we drive a real (stealth) browser via scrapling's
``StealthyFetcher`` to render each product page, then read the JSON-LD.

We iterate Maple's own catalogue (iPhone 13–17), map each (series, variant) to
Cashify's product slug (``renewed-apple-iphone-13-pro``), fetch it, and emit one
canonical listing per in-stock (storage, condition) at its lowest price.

This is BEST-EFFORT: third-party sites change markup and fight scrapers. To
protect demo quality, ``fetch_raw`` applies a sanity gate — if it can't extract
enough plausible listings it raises ``ScrapeBlocked`` and the resilience
contract falls back to the synthetic generator (clean mock beats garbage rows).
"""
from __future__ import annotations

import json
import re

from ..catalog import Device, device_by_sku, iphone_devices
from ..util import as_of_date
from .base import BaseScraper, ScrapeBlocked

# (series, variant) -> Cashify product-slug suffix.
_VARIANT_SLUG = {
    "Base": "",
    "Plus": "-plus",
    "Pro": "-pro",
    "Pro Max": "-pro-max",
    "Mini": "-mini",
}
_PRODUCT_URL = (
    "https://www.cashify.in/buy-refurbished-mobile-phones/renewed-apple-iphone-{slug}"
)

# Plausible used-iPhone price band (INR) — reject anything outside it.
_MIN_PRICE, _MAX_PRICE = 8_000, 250_000
_MIN_LISTINGS = 8  # need at least this many plausible rows to trust the scrape

# Variant name looks like:
#   "Apple iPhone 13 - Refurbished, Cashify Warranty, Superb, 4 GB / 256 GB, Blue"
_COND_RE = re.compile(r"Warranty,\s*([A-Za-z ]+?)\s*,", re.I)
_STORAGE_RE = re.compile(r"/\s*(\d+)\s*GB", re.I)  # the value AFTER the RAM "/"
# Nominal battery health by Maple-mapped grade (Cashify doesn't publish per-unit).
_BATTERY_BY_COND = {"Almost New": 97, "Superb": 92, "Good": 87, "Fair": 83}


class CashifyScraper(BaseScraper):
    platform_key = "cashify"
    platform_name = "Cashify"
    region = "IN"
    base_url = "https://www.cashify.in/buy-refurbished-mobile-phones/apple"

    # --- URL planning ---------------------------------------------------- #
    def _model_urls(self) -> dict[tuple[int, str], str]:
        """Distinct catalogue (series, variant) -> Cashify product URL."""
        urls: dict[tuple[int, str], str] = {}
        for d in iphone_devices():
            key = (d.series, d.variant)
            if key in urls:
                continue
            suffix = _VARIANT_SLUG.get(d.variant)
            if suffix is None:
                continue
            urls[key] = _PRODUCT_URL.format(slug=f"{d.series}{suffix}")
        return urls

    # --- live scrape ----------------------------------------------------- #
    def fetch_raw(self, devices: list | None = None) -> list[dict]:
        try:
            from scrapling.fetchers import StealthyFetcher
        except Exception as exc:
            raise ScrapeBlocked(f"{self.platform_key}: scrapling unavailable: {exc}")

        as_of = as_of_date()
        out: list[dict] = []
        for (series, variant), url in self._model_urls().items():
            try:
                page = StealthyFetcher.fetch(url, network_idle=True, timeout=60000)
            except Exception:
                continue  # one model failing must not sink the whole scrape
            html = self._html(page)
            if not html:
                continue
            for storage, raw_cond, price in self._parse_product(html):
                if not (_MIN_PRICE <= price <= _MAX_PRICE):
                    continue
                device = Device(series, variant, storage)
                if device_by_sku(device.sku) is None:
                    continue
                out.append(self._record(device, raw_cond, price, url, as_of))

        if len(out) < _MIN_LISTINGS:
            raise ScrapeBlocked(
                f"{self.platform_key}: only {len(out)} plausible listings (< {_MIN_LISTINGS})"
            )
        return out

    # --- parsing --------------------------------------------------------- #
    @staticmethod
    def _html(page) -> str:
        for attr in ("html_content", "body", "get_all_text"):
            val = getattr(page, attr, None)
            val = val() if callable(val) else val
            if val:
                return val.decode("utf-8", "ignore") if isinstance(val, bytes) else str(val)
        return ""

    @staticmethod
    def _parse_product(html: str) -> list[tuple[str, str, int]]:
        """Read the ProductGroup JSON-LD -> [(storage, raw_condition, price)].

        One row per in-stock (storage, condition) at its lowest observed price
        (colours are collapsed — they share a price and don't matter for value).
        """
        best: dict[tuple[str, str], int] = {}
        for block in re.findall(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S
        ):
            try:
                data = json.loads(block)
            except Exception:
                continue
            for obj in data if isinstance(data, list) else [data]:
                if not isinstance(obj, dict):
                    continue
                for v in obj.get("hasVariant") or []:
                    name = v.get("name", "")
                    offers = v.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    try:
                        price = int(float(offers.get("price")))
                    except (TypeError, ValueError):
                        continue
                    in_stock = "InStock" in str(offers.get("availability", ""))
                    cm, sm = _COND_RE.search(name), _STORAGE_RE.search(name)
                    if not (in_stock and cm and sm):
                        continue
                    storage = sm.group(1).upper() + "GB"
                    raw_cond = cm.group(1).strip()
                    key = (storage, raw_cond)
                    if key not in best or price < best[key]:
                        best[key] = price
        return [(st, cn, pr) for (st, cn), pr in best.items()]

    def _record(self, device: Device, raw_cond: str, price: float, url: str, as_of) -> dict:
        from ..normalization import normalize_grade

        graded = normalize_grade(raw_cond, None)
        return {
            "platform": self.platform_key,
            "region": self.region,
            "sku": device.sku,
            "series": device.series,
            "model": device.model,
            "variant": device.variant,
            "storage": device.storage,
            "battery_health": _BATTERY_BY_COND.get(graded, 90),
            "raw_condition": raw_cond,  # normalized to a Maple grade by _postprocess()
            "city": "Delhi",  # Cashify is a national online refurbisher; anchor to ref city
            "asking_price": float(price),
            "asking_price_native": float(price),
            "currency": "INR",
            "seller_type": "certified_refurbisher",
            "color": "",
            "listing_title": f"Refurbished {device.model} {device.storage} — {raw_cond}",
            "seller_name": "Cashify Certified",
            "seller_rating": 4.5,
            "warranty": "6-month Cashify warranty",
            "accessories": "Box & cable",
            "verified": True,
            "listing_date": as_of,
            "url": url,
        }
