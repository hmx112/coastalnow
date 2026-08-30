"""Provider- and activity-independent scoring primitives."""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo

NEUTRAL_UNKNOWN_SCORE = 50.0
_CONFIDENCE_RANK = {
    "High": 0,
    "Medium": 1,
    "Limited": 2,
    "Unavailable": 3,
}


def _validate_score(value: float) -> float:
    number = float(value)
    if not 0 <= number <= 100:
        raise ValueError("component scores must be between 0 and 100")
    return number


def weighted_score(components: dict[str, float | None], weights: dict[str, float]) -> float:
    """Return a 0-100 weighted score without redistributing unknown weights.

    Missing/None component values receive the fixed neutral-unknown score of 50.
    Every configured weight must be positive and weights must sum to one.
    """
    if not weights:
        raise ValueError("weights are required")
    normalized_weights = {}
    for name, value in weights.items():
        weight = float(value)
        if weight <= 0:
            raise ValueError("weights must be positive")
        normalized_weights[name] = weight
    if abs(sum(normalized_weights.values()) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1")

    total = 0.0
    for name, weight in normalized_weights.items():
        raw = components.get(name)
        component = NEUTRAL_UNKNOWN_SCORE if raw is None else _validate_score(raw)
        total += component * weight
    return round(total, 1)


def rating_for_score(score: float) -> str:
    value = _validate_score(score)
    if value >= 90:
        return "Excellent"
    if value >= 75:
        return "Good"
    if value >= 60:
        return "Fair"
    if value >= 40:
        return "Poor"
    return "Unfavorable"


def group_local_days(hourly: list[dict], timezone_name: str, now: datetime) -> dict[str, list[dict]]:
    """Split hourly rows into the location's local Today and Tomorrow calendars."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    timezone = ZoneInfo(timezone_name)
    local_today = now.astimezone(timezone).date()
    local_tomorrow = local_today + timedelta(days=1)
    grouped = {"today": [], "tomorrow": []}
    for row in hourly:
        stamp = datetime.fromisoformat(row["time"])
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("hourly times must be offset-aware")
        local_date = stamp.astimezone(timezone).date()
        if local_date == local_today:
            grouped["today"].append(row)
        elif local_date == local_tomorrow:
            grouped["tomorrow"].append(row)
    return grouped


def _window_is_consecutive(rows: list[dict]) -> bool:
    stamps = [datetime.fromisoformat(row["time"]) for row in rows]
    if any(stamp.tzinfo is None or stamp.utcoffset() is None for stamp in stamps):
        raise ValueError("hourly times must be offset-aware")
    return all(later - earlier == timedelta(hours=1) for earlier, later in zip(stamps, stamps[1:]))


def _window_confidence(rows: list[dict]) -> str:
    labels = [row.get("confidence", "Unavailable") for row in rows]
    try:
        return max(labels, key=lambda label: _CONFIDENCE_RANK[label])
    except KeyError as exc:
        raise ValueError(f"unknown confidence label: {exc.args[0]}") from exc


def best_continuous_window(hourly: list[dict], *, hours: int = 3) -> dict | None:
    """Pick the highest safe consecutive window using 70% mean + 30% minimum."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    if len(hourly) < hours:
        return None

    candidates = []
    for index in range(len(hourly) - hours + 1):
        rows = hourly[index:index + hours]
        if not _window_is_consecutive(rows):
            continue
        if any(not row.get("available", False) or row.get("hard_stop", False) for row in rows):
            continue
        scores = [_validate_score(row["final_score"]) for row in rows]
        window_score = round(0.70 * mean(scores) + 0.30 * min(scores), 1)
        start = datetime.fromisoformat(rows[0]["time"])
        end = start + timedelta(hours=hours)
        candidates.append({
            "score": window_score,
            "rating": rating_for_score(window_score),
            "start": rows[0]["time"],
            "end": end.isoformat(),
            "confidence": _window_confidence(rows),
            "hours": rows,
        })

    if not candidates:
        return None
    return max(candidates, key=lambda item: (item["score"], -_CONFIDENCE_RANK[item["confidence"]]))
