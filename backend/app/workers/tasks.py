"""Job handlers run by the worker (or inline in the synchronous fallback)."""
from __future__ import annotations

from typing import Any

from ..db import SessionLocal
from ..seed import refresh_market, seed_all


def task_refresh_market(payload: dict[str, Any]) -> dict:
    with SessionLocal() as db:
        return refresh_market(db)


def task_reseed(payload: dict[str, Any]) -> dict:
    with SessionLocal() as db:
        return seed_all(db, force=bool(payload.get("force", True)))


HANDLERS = {
    "refresh_market": task_refresh_market,
    "reseed": task_reseed,
}


def dispatch(job: str, payload: dict[str, Any]) -> dict:
    handler = HANDLERS.get(job)
    if not handler:
        return {"error": f"unknown job '{job}'"}
    return handler(payload)
