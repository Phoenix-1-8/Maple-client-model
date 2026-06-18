"""
Maple Store adapter — the client's OWN store (maplestore.in).

maplestore.in is a Shopify storefront, so the full catalogue is available as
clean, structured JSON at ``/products.json`` (paginated, no bot-blocking). That
makes the client's real data the most reliable source in the whole pilot — we
read it directly rather than driving a browser.

Each Shopify product is a single certified pre-owned unit whose TITLE encodes
everything we need, e.g.::

    iPhone 15 - 128GB - Blue - IW (20-Dec-26) - Pre-owned
    iPhone 16 Pro Max - 256GB - Natural Titanium - Pre-owned
    iPhone 15 - 128GB - Pink - ACS - Demo-unit

We parse (model -> series/variant), storage, colour, warranty (IW/AC+/ACS) and
condition (Pre-owned / Demo-unit), map to the catalog SKU, and emit canonical
listing dicts. ``variant.price`` is Maple's sell price; ``compare_at_price`` is
kept as a market reference.

Role is ``own`` — these listings are tracked but EXCLUDED from the competitor
benchmark (see ``MapleConfig.competitor_platforms``); they're what the
"Maple vs Market" tab justifies.
"""
from __future__ import annotations

import json
import re
from datetime import date

from ..catalog import Device, device_by_sku
from ..util import as_of_date
from .base import BaseScraper, ScrapeBlocked

PRODUCTS_URL = "https://maplestore.in/products.json"
KNOWN_SERIES = {13, 14, 15, 16, 17}

_STORAGE_RE = re.compile(r"(\d+)\s*(GB|TB)", re.I)
_WARRANTY_RE = re.compile(r"\b(IW|AC\+|ACS)\b\s*(\(([^)]+)\))?", re.I)
_SERIES_RE = re.compile(r"iphone\s+(\d{1,2})", re.I)

# Title condition vocabulary -> display string (normalize_grade maps it to a
# Maple grade downstream via config.DEFAULT_GRADE_MAP).
_CONDITIONS = {
    "pre-owned": "Pre-owned",
    "preowned": "Pre-owned",
    "demo-unit": "Demo-unit",
    "demo unit": "Demo-unit",
    "refurbished": "Refurbished",
    "open box": "Open Box",
}


def parse_title(title: str) -> dict | None:
    """Parse a maplestore.in product title into structured fields.

    Returns None if it isn't a recognizable iPhone title. Storage/condition may
    be None if absent; the caller decides whether to keep the record.
    """
    # Real titles use ' - ' (spaces) as the delimiter; the hyphen inside
    # 'Pre-owned'/'Demo-unit' has no surrounding spaces, so split on '\s+-\s+'.
    parts = [p.strip() for p in re.split(r"\s+-\s+", title) if p.strip()]
    if len(parts) == 1:  # fallback for the rare space-less variant
        parts = [p.strip() for p in title.split("-") if p.strip()]
    if not parts:
        return None

    sm = _SERIES_RE.search(parts[0])
    if not sm:
        return None
    series = int(sm.group(1))

    low = parts[0].lower()
    if "pro max" in low:
        variant = "Pro Max"
    elif " pro" in low:
        variant = "Pro"
    elif "plus" in low:
        variant = "Plus"
    elif "mini" in low:
        variant = "Mini"
    else:
        variant = "Base"

    storage = None
    for p in parts[1:]:
        m = _STORAGE_RE.search(p)
        if m:
            storage = m.group(1).upper() + m.group(2).upper()
            break

    condition = next(
        (_CONDITIONS[p.lower()] for p in reversed(parts) if p.lower() in _CONDITIONS),
        None,
    )

    warranty = "No warranty"
    wm = _WARRANTY_RE.search(title)
    if wm:
        tag = wm.group(1).upper()
        dt = wm.group(3)
        label = {"IW": "In warranty", "AC+": "AppleCare+", "ACS": "AppleCare service"}[tag]
        warranty = f"{label} · until {dt}" if dt and tag != "ACS" else label

    color = next(
        (
            p
            for p in parts[1:]
            if not _STORAGE_RE.search(p)
            and p.lower() not in _CONDITIONS
            and not _WARRANTY_RE.search(p)
        ),
        "",
    )

    return {
        "series": series,
        "variant": variant,
        "storage": storage,
        "color": color,
        "raw_condition": condition,
        "warranty": warranty,
    }


def _to_int_price(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class MapleStoreScraper(BaseScraper):
    platform_key = "maple_store"
    platform_name = "Maple Store"
    region = "IN"
    base_url = "https://maplestore.in"

    def fetch_raw(self, devices: list | None = None) -> list[dict]:
        """Page the Shopify products feed and emit canonical listing dicts.

        Uses scrapling's fast HTTP Fetcher (bundles a CA store, sets a referer)
        so this works without a browser. Any failure raises so the resilience
        contract falls back to the certified mock generator.
        """
        try:
            from scrapling.fetchers import Fetcher
        except Exception as exc:  # scrapling not installed
            raise ScrapeBlocked(f"{self.platform_key}: scrapling unavailable: {exc}")

        as_of = as_of_date()
        out: list[dict] = []
        for page in range(1, 12):  # generous cap; the catalogue is ~5 pages
            resp = Fetcher.get(
                PRODUCTS_URL,
                params={"limit": 250, "page": page},
                headers={"User-Agent": "Mozilla/5.0 (MapleAI market monitor)"},
            )
            if getattr(resp, "status", None) != 200:
                raise ScrapeBlocked(f"{self.platform_key}: HTTP {getattr(resp, 'status', '?')}")
            products = json.loads(resp.body).get("products", [])
            if not products:
                break
            for prod in products:
                if (prod.get("product_type") or "").strip().lower() != "iphone":
                    continue
                rec = self._record(prod, as_of)
                if rec is not None:
                    out.append(rec)
        if not out:
            raise ScrapeBlocked(f"{self.platform_key}: no iPhone products parsed")
        return out

    def _record(self, prod: dict, as_of: date) -> dict | None:
        title = prod.get("title") or ""
        parsed = parse_title(title)
        if not parsed or not parsed["storage"] or parsed["series"] not in KNOWN_SERIES:
            return None  # out-of-catalogue (iPhone Air / SE) or unparseable

        device = Device(parsed["series"], parsed["variant"], parsed["storage"])
        if device_by_sku(device.sku) is None:
            return None  # variant/storage combo not in the 13–17 catalogue

        variants = prod.get("variants") or [{}]
        v0 = variants[0]
        price = _to_int_price(v0.get("price"))
        if not price:
            return None

        handle = prod.get("handle") or device.sku
        return {
            "platform": self.platform_key,
            "region": self.region,
            "sku": device.sku,
            "series": device.series,
            "model": device.model,
            "variant": device.variant,
            "storage": device.storage,
            "battery_health": 100,  # certified; site does not publish per-unit %
            # condition is normalized to a Maple grade by _postprocess()
            "raw_condition": parsed["raw_condition"] or "Pre-owned",
            "city": "Delhi",  # online-national store; anchor to the reference city
            "asking_price": float(price),
            "asking_price_native": float(price),
            "currency": "INR",
            "seller_type": "maple_store",
            "color": parsed["color"],
            "listing_title": title,
            "seller_name": "Maple Store",
            "seller_rating": 4.8,
            "seller_reviews": 0,
            "warranty": parsed["warranty"],
            "accessories": "Box & cable",
            "lock_status": "Factory Unlocked",
            "verified": True,
            "negotiable": False,
            "views": 0,
            "listing_date": as_of,
            "url": f"https://maplestore.in/products/{handle}",
        }

    def _mock_listings(self, as_of: date) -> list[dict]:
        """Mock fallback uses Maple's CERTIFIED generator (not the generic one)."""
        from ..mock_data import build_maple_rng, generate_maple_listings

        return generate_maple_listings(self.cfg, as_of, build_maple_rng(self.cfg))
