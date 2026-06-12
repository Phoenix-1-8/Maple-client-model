"""SQLAlchemy engine / session setup.

Portable between SQLite (zero-config laptop demo) and PostgreSQL (docker-compose).
We deliberately use only generic column types so the same models run on both.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_config

_cfg = get_config()

# SQLite needs check_same_thread=False for FastAPI's threadpool.
_connect_args = (
    {"check_same_thread": False}
    if _cfg.infra.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    _cfg.infra.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Import models so they register on the metadata before create_all.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
