"""Detailed NWS alert presentation for Surfing pages."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from activities.rendering.surfing_explanation import (
    _alert_reason_keys,
    _alert_relation,
    _chosen_raw_row,
    _chosen_scored_row,
    _fmt_number,
    _fmt_window,
    _safety_gate_sentence,
    _score_sentences,
    build_surfing_explanation as _base_explanation,
)


def _aware(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _localize(value: str | None, timezone_name: str | None) -> datetime | None:
    parsed = _aware(value)
    if parsed is None:
        return None
    if not timezone_name:
        return parsed
    try:
        return parsed.astimezone(ZoneInfo(timezone_name))
    except (KeyError, ValueError):
        return parsed


def _month_day_time(value: datetime) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.strftime('%I:%M %p').lstrip('0')}"


def _time_only(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _alert_period(item: dict, timezone_name: str | None) -> str:
    start = _localize(item.get("onset") or item.get("effective"), timezone_name)
    end = _localize(item.get("ends") or item.get("expires"), timezone_name)
    zone = (end or start).tzname() if (end or start) else None
    zone_suffix = f" {zone}" if zone else ""

    if start and end:
        if start.date() == end.date():
            return f"{_month_day_time(start)}–{_time_only(end)}{zone_suffix}"
        return f"{_month_day_time(start)} – {_month_day_time(end)}{zone_suffix}"
    if start:
        return f"Starts {_month_day_time(start)}{zone_suffix}"
    if end:
        return f"Until {_month_day_time(end)}{zone_suffix}"
    return "Timing unavailable"


def _hazard_summary(description: object) -> str:
    text = str(description or "").strip()
    if not text:
        return ""
    match = re.search(r"\*\s*WHAT\.\.\.(.*?)(?=\n\s*\n|\n\*\s*[A-Z]+|$)", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1)
    else:
        text = text.split("\n\n", 1)[0]
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= 320:
        return text
    shortened = text[:320].rsplit(" ", 1)[0].rstrip(" ,;:")
    return shortened + "…"


def build_nws_alert_details(snapshot: dict) -> list[dict[str, str]]:
    alerts = snapshot.get("alerts") or {}
    if alerts.get("status") != "ok":
        return []
    timezone_name = snapshot.get("timezone")
    details: list[dict[str, str]] = []
    for item in alerts.get("items") or []:
        event = str(item.get("event") or "NWS weather alert").strip()
        details.append(
            {
                "event": event,
                "period": _alert_period(item, timezone_name),
                "summary": _hazard_summary(item.get("description")),
            }
        )
    return details


def _details_sentence(snapshot: dict) -> str | None:
    details = build_nws_alert_details(snapshot)
    if not details:
        return None
    joined = "; ".join(f'{detail["event"]} ({detail["period"]})' for detail in details)
    return f"NWS alert details: {joined}."


def _effect_sentence(result: dict, snapshot: dict, scored: dict) -> str | None:
    items = ((snapshot.get("alerts") or {}).get("items") or [])
    if not items:
        return None

    day = result.get("today") or {}
    window = day.get("best_window")
    reasons = set(scored.get("reasons") or [])
    applied = [
        item
        for item in items
        if reasons.intersection(_alert_reason_keys(str(item.get("event") or "").strip()))
    ]
    item = applied[0] if applied else items[0]
    event = str(item.get("event") or "weather alert").strip()
    relation = _alert_relation(item, window)

    if applied:
        if scored.get("hard_stop") or day.get("status") == "NOT RECOMMENDED":
            return (
                f"The {event} is the primary reason today is NOT RECOMMENDED; "
                "this safety condition takes priority over otherwise favorable wave, wind, or weather inputs."
            )
        cap = scored.get("safety_cap")
        if cap is not None and float(cap) < 100:
            return (
                f"The {event} is active during the best planning window and caps the Surf Conditions Score at "
                f"{_fmt_number(cap)}, even if the underlying wave, wind, and weather inputs would score higher."
            )
        penalty = scored.get("safety_penalty")
        if penalty is not None and float(penalty) > 0:
            return (
                f"The {event} is active during the best planning window and applies a "
                f"{_fmt_number(penalty)}-point Safety Gate penalty to the composite score."
            )
        return f"The {event} is active during the relevant period and should be treated as the first planning consideration."

    if relation == "after":
        return (
            f"The {event} begins after the {_fmt_window(window)} planning window, so it does not directly reduce "
            "that window's numerical score; the official alert still takes priority once its stated period begins."
        )
    if relation == "before":
        return (
            f"The {event} ends before the {_fmt_window(window)} planning window, so it does not directly reduce "
            "that window's numerical score."
        )
    if relation == "overlap":
        return (
            f"The {event} overlaps the {_fmt_window(window)} planning window. It is not a direct v1 Surf Conditions Score "
            "adjustment unless the Safety Gate maps that alert, but the official alert should be reviewed first."
        )
    return f"The timing of the {event} cannot be matched confidently to the planning window, so the official alert should be reviewed first."


def build_detailed_surfing_explanation(result: dict, snapshot: dict) -> str:
    alerts = snapshot.get("alerts") or {}
    if alerts.get("status") != "ok" or not (alerts.get("items") or []):
        return _base_explanation(result, snapshot)

    scored = _chosen_scored_row(result)
    raw = _chosen_raw_row(snapshot, scored, result)
    sentences: list[str] = []

    details = _details_sentence(snapshot)
    if details:
        sentences.append(details)
    effect = _effect_sentence(result, snapshot, scored)
    if effect:
        sentences.append(effect)

    reasons = set(scored.get("reasons") or [])
    alert_applied = any(
        reasons.intersection(_alert_reason_keys(str(item.get("event") or "").strip()))
        for item in alerts.get("items") or []
    )
    safety = None if alert_applied else _safety_gate_sentence(result, scored, raw)
    if safety:
        sentences.append(safety)

    sentences.extend(_score_sentences(result, scored, raw))
    return " ".join(sentences[:3])
