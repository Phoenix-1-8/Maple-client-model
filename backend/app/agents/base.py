"""
Shared machinery for the AI agents.

Agents are deterministic analytical workers that read the listings table and the
market history, then emit structured insight.  They share:

  * a config handle
  * a way to load + group listings
  * the canonical fair-value computation (so every agent agrees on "value")
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..catalog import Device, device_by_sku
from ..config import MapleConfig, get_config
from ..models import Listing
from ..pricing import FairValue, Observation, build_observation, fair_market_value
from ..util import as_of_date


@dataclass
class DeviceValuation:
    sku: str
    device: Device
    fair: FairValue
    listing_count: int
    region: str


class Agent:
    name: str = "agent"
    title: str = "Agent"

    def __init__(self, cfg: MapleConfig | None = None):
        self.cfg = cfg or get_config()
        self.as_of: date = as_of_date()

    # ---- data access ---------------------------------------------------- #
    def load_listings(
        self, db: Session, region: str | None = None, sku: str | None = None
    ) -> list[Listing]:
        stmt = select(Listing)
        if region:
            stmt = stmt.where(Listing.region == region)
        if sku:
            stmt = stmt.where(Listing.sku == sku)
        return list(db.scalars(stmt))

    def group_by_sku(self, listings: list[Listing]) -> dict[str, list[Listing]]:
        groups: dict[str, list[Listing]] = defaultdict(list)
        for l in listings:
            groups[l.sku].append(l)
        return groups

    def observations(self, listings: list[Listing]) -> list[Observation]:
        obs: list[Observation] = []
        for l in listings:
            obs.append(
                build_observation(
                    asking_price=l.asking_price,
                    platform=l.platform,
                    city=l.city,
                    condition=l.condition,
                    listing_date=l.listing_date,
                    as_of=self.as_of,
                    cfg=self.cfg,
                )
            )
        return obs

    def valuations(
        self, db: Session, region: str = "IN"
    ) -> dict[str, DeviceValuation]:
        """Condition-normalized fair value per SKU for a region."""
        groups = self.group_by_sku(self.load_listings(db, region=region))
        out: dict[str, DeviceValuation] = {}
        for sku, listings in groups.items():
            device = device_by_sku(sku)
            if not device:
                continue
            fv = fair_market_value(self.observations(listings), self.cfg)
            if not fv:
                continue
            out[sku] = DeviceValuation(
                sku=sku,
                device=device,
                fair=fv,
                listing_count=len(listings),
                region=region,
            )
        return out

    # ---- to override ---------------------------------------------------- #
    def run(self, db: Session) -> dict:  # pragma: no cover - interface
        raise NotImplementedError
