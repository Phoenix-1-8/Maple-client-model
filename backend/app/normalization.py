"""
Condition normalization.

Competitor platforms grade devices on wildly different scales ("Mint",
"Excellent", "Superb", "A+", "Average", ...).  Maple uses a single 4-grade
system: Almost New > Superb > Good > Fair.

This module maps any competitor grade into a Maple grade, with a battery-health
fallback when a platform reports no usable grade.  The mapping is configurable
(see config.DEFAULT_GRADE_MAP).
"""
from __future__ import annotations

import re

from .config import MAPLE_GRADES, get_config


def normalize_grade(raw: str | None, battery_health: int | None = None) -> str:
    """Return a canonical Maple grade for a competitor grade string.

    Resolution order:
      1. Exact / fuzzy match against the configurable grade map.
      2. Battery-health heuristic fallback.
      3. Default to 'Good' (safe middle grade).
    """
    cfg = get_config()
    if raw:
        key = _clean(raw)
        if key in cfg.grade_map:
            return cfg.grade_map[key]
        # token / substring fallback (e.g. "superb (a grade)" -> "superb")
        for token, grade in cfg.grade_map.items():
            if token and token in key:
                return grade

    if battery_health is not None:
        return grade_from_battery(battery_health)

    return "Good"


def grade_from_battery(battery_health: int) -> str:
    """Heuristic Maple grade purely from battery health %."""
    if battery_health >= 95:
        return "Almost New"
    if battery_health >= 88:
        return "Superb"
    if battery_health >= 82:
        return "Good"
    return "Fair"


def is_valid_grade(grade: str) -> bool:
    return grade in MAPLE_GRADES


def _clean(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"[._/]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def explain_mapping() -> list[dict]:
    """Return the active competitor->Maple grade map for the config/docs API."""
    cfg = get_config()
    out: list[dict] = []
    for competitor_grade, maple_grade in sorted(cfg.grade_map.items(), key=lambda x: (MAPLE_GRADES.index(x[1]), x[0])):
        out.append({"competitor_grade": competitor_grade, "maple_grade": maple_grade})
    return out
