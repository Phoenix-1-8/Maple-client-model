"""
Tiny Redis-backed job queue.

If REDIS_URL is configured we push jobs onto a Redis list; a separate worker
process (worker.py) consumes them.  If Redis is NOT configured we fall back to
running the job inline (synchronous), so the pilot works with zero infra.
"""
from __future__ import annotations

import json
from typing import Any

from ..config import get_config

JOB_QUEUE_KEY = "maple:jobs"


def _redis():
    cfg = get_config()
    if not cfg.infra.redis_url:
        return None
    try:
        import redis  # type: ignore

        return redis.Redis.from_url(cfg.infra.redis_url, decode_responses=True)
    except Exception:
        return None


def enqueue(job: str, payload: dict[str, Any] | None = None) -> dict:
    """Enqueue a job. Returns dict describing how it was handled."""
    message = json.dumps({"job": job, "payload": payload or {}})
    r = _redis()
    if r is None:
        # Synchronous fallback — run immediately.
        from .tasks import dispatch

        result = dispatch(job, payload or {})
        return {"mode": "sync", "job": job, "result": result}
    r.rpush(JOB_QUEUE_KEY, message)
    return {"mode": "queued", "job": job, "queue": JOB_QUEUE_KEY}


def is_async_enabled() -> bool:
    return _redis() is not None
