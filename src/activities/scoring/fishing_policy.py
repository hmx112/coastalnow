"""Fishing result policy applied after the raw hourly/day scoring pass."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from activities.scoring.fishing import score_fishing_snapshot

_CONFIDENCE_RANK = {"High": 0, "Medium": 1, "Limited": 2, "Unavailable": 3}
END_OF_DAY_STATUS = "No 3-hour window remaining"


def _worst_confidence(rows: list[dict], fallback: str = "Unavailable") -> str:
    labels = [row.get("confidence", "Unavailable") for row in rows]
    if not labels:
        return fallback
    return max(labels, key=lambda label: _CONFIDENCE_RANK.get(label, 3))


def _less_than_three_hours_to_midnight(now: datetime, timezone_name: str) -> bool:
    timezone = ZoneInfo(timezone_name)
    local_now = now.astimezone(timezone)
    next_day = local_now.date() + timedelta(days=1)
    midnight = datetime.combine(next_day, time.min, tzinfo=timezone)
    return timedelta(0) <= midnight - local_now < timedelta(hours=3)


def apply_end_of_day_policy(result: dict, *, location: dict, now: datetime) -> dict:
    """Distinguish a closing local day from genuine data unavailability.

    A full Fishing recommendation requires a consecutive three-hour window. When
    fewer than three hours remain before local midnight, lack of such a window is
    a clock/calendar state rather than a provider failure. Any remaining hard-stop
    condition still takes priority over this presentation state.
    """
    today = result.get("today") or {}
    rows = (result.get("hourly") or {}).get("today") or []
    if today.get("status") != "Unavailable":
        return result
    if not _less_than_three_hours_to_midnight(now, location["timezone"]):
        return result

    hard_stop_rows = [row for row in rows if row.get("hard_stop")]
    if hard_stop_rows:
        today.update({
            "status": "NOT RECOMMENDED",
            "score": None,
            "rating": None,
            "confidence": _worst_confidence(hard_stop_rows),
            "best_window": None,
            "ranking_eligible": False,
        })
        return result

    fallback = (result.get("tomorrow") or {}).get("confidence", "Unavailable")
    today.update({
        "status": END_OF_DAY_STATUS,
        "score": None,
        "rating": None,
        "confidence": _worst_confidence(rows, fallback=fallback),
        "best_window": None,
        "ranking_eligible": False,
    })
    return result


def score_fishing_activity(snapshot: dict, *, location: dict, now: datetime) -> dict:
    result = score_fishing_snapshot(snapshot, location=location, now=now)
    return apply_end_of_day_policy(result, location=location, now=now)
