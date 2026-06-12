"""Small shared helpers."""
from __future__ import annotations

import os
from datetime import date, datetime


def as_of_date() -> date:
    """The 'current' date the pilot reasons about.

    Defaults to today, but can be pinned via MAPLE_AS_OF=YYYY-MM-DD for fully
    reproducible investor demos.
    """
    raw = os.getenv("MAPLE_AS_OF", "").strip()
    if raw:
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def inr(amount: float) -> str:
    """Format a number as Indian-grouped rupees, e.g. 4,82,500."""
    n = int(round(amount))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return f"{sign}₹{s}"
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return f"{sign}₹{','.join(parts)},{tail}"
