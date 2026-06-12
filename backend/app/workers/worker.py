"""
Worker entrypoint:  python -m app.workers.worker

Consumes jobs from the Redis queue and runs them.  Also performs an initial
seed and an immediate market refresh so a fresh stack is populated.
"""
from __future__ import annotations

import json
import time

from ..config import get_config
from ..db import init_db
from ..seed import seed_on_startup
from .queue import JOB_QUEUE_KEY, _redis
from .tasks import dispatch


def main() -> None:
    init_db()
    print("[worker] starting; seeding if needed...")
    print("[worker] seed:", seed_on_startup())

    r = _redis()
    if r is None:
        print("[worker] REDIS_URL not set — nothing to consume. Exiting.")
        return

    cfg = get_config()
    # The backend service seeds the full market on startup, so the worker just
    # consumes queued refresh jobs (avoids racing the startup seed on `listings`).
    print(f"[worker] connected to {cfg.infra.redis_url}; waiting for jobs on {JOB_QUEUE_KEY}")

    while True:
        try:
            item = r.blpop(JOB_QUEUE_KEY, timeout=5)
            if not item:
                continue
            _, raw = item
            msg = json.loads(raw)
            print(f"[worker] running {msg['job']}")
            result = dispatch(msg["job"], msg.get("payload", {}))
            print(f"[worker] done {msg['job']}: {result}")
        except KeyboardInterrupt:
            print("[worker] shutting down")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] error: {exc}")
            time.sleep(2)


if __name__ == "__main__":
    main()
