"""SQLAlchemy ORM models. Generic types only (SQLite + Postgres compatible)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Listing(Base):
    """A single normalized market listing (scraped or mock)."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    platform: Mapped[str] = mapped_column(String(40), index=True)
    region: Mapped[str] = mapped_column(String(4), default="IN", index=True)

    # Device identity
    sku: Mapped[str] = mapped_column(String(40), index=True)
    series: Mapped[int] = mapped_column(Integer, index=True)
    model: Mapped[str] = mapped_column(String(40), index=True)
    variant: Mapped[str] = mapped_column(String(16))
    storage: Mapped[str] = mapped_column(String(8))

    # Condition
    battery_health: Mapped[int] = mapped_column(Integer, default=100)
    condition: Mapped[str] = mapped_column(String(16), index=True)      # Maple grade
    raw_condition: Mapped[str] = mapped_column(String(40), default="")   # competitor grade

    # Location & price
    city: Mapped[str] = mapped_column(String(40), index=True)
    asking_price: Mapped[float] = mapped_column(Float)          # always INR
    asking_price_native: Mapped[float] = mapped_column(Float)   # original currency
    currency: Mapped[str] = mapped_column(String(4), default="INR")

    seller_type: Mapped[str] = mapped_column(String(40), default="individual")
    listing_date: Mapped[date] = mapped_column(Date, index=True)
    url: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_listings_sku_platform", "sku", "platform"),
        Index("ix_listings_sku_city", "sku", "city"),
    )


class MarketDaily(Base):
    """One row per day: the Maple Used-iPhone Market Index."""

    __tablename__ = "market_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    index_value: Mapped[float] = mapped_column(Float)
    prev_index_value: Mapped[float] = mapped_column(Float, default=0.0)
    movement_pct: Mapped[float] = mapped_column(Float, default=0.0)
    total_active_listings: Mapped[int] = mapped_column(Integer, default=0)


class DeviceDaily(Base):
    """Per-device daily fair value (condition-normalized to 'Superb')."""

    __tablename__ = "device_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    sku: Mapped[str] = mapped_column(String(40), index=True)
    series: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(40))
    variant: Mapped[str] = mapped_column(String(16))
    storage: Mapped[str] = mapped_column(String(8))
    fair_value: Mapped[float] = mapped_column(Float)
    listing_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (Index("ix_device_daily_sku_day", "sku", "day"),)
