"""SQLAlchemy engine / session setup.

Portable between SQLite (zero-config laptop demo) and PostgreSQL (docker-compose).
We deliberately use only generic column types so the same models run on both.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, inspect
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

    # Self-heal schema drift. All tables here are derived from the committed
    # fixture and re-seeded on startup, so if a persistent DB (e.g. the Docker
    # Postgres volume) was created with an older model and is now missing
    # columns, we drop & recreate rather than fail every query. This keeps the
    # pilot runnable across model changes without a migration tool.
    inspector = inspect(engine)
    drift = False
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        expected = {c.name for c in table.columns}
        if not expected.issubset(existing):
            missing = sorted(expected - existing)
            print(
                f"[init_db] schema drift on '{table_name}' (missing {missing}); "
                "recreating tables — data will be re-seeded from the fixture."
            )
            drift = True
            break

    if drift:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
