"""Build day-specific Surfing score explanations from raw conditions and Safety Gate output."""
from __future__ import annotations

from datetime import datetime

from activities.scoring.surfing_policy import SURFING_WEIGHTS

_ALERT_REASONS = {
    "Rip Current Statement": {"rip-current-statement", "high-rip-current-risk"},
    "Small Craft Advisory": {"small-craft-advisory"},
    "Dense Fog Advisory": {"dense-fog-advisory"},
    "Coastal Flood Advisory": {"coastal-flood-advisory"},
}


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


def _fmt_number(value: object, *, one_decimal: bool = False) -> str:
    number = float(value)
    if one_decimal:
        return f"{number:.1f}"
    return f"{number:g}"


def _chosen_scored_row(result: dict) -> dict:
    rows = (result.get("hourly") or {}).get("today") or []
    day = result.get("today") or {}
    window = day.get("best_window") or {}
    start = window.get("start")
    if start:
        match = next((row for row in rows if row.get("time") == start), None)
        if match:
            return match
    if day.get("status") == "NOT RECOMMENDED":
        match = next((row for row in rows if row.get("hard_stop")), None)
        if match:
            return match
    return rows[0] if rows else {}


def _chosen_raw_row(snapshot: dict, scored: dict, result: dict) -> dict:
    rows = snapshot.get("hourly") or []
    target = scored.get("time")
    if target:
        match = next((row for row in rows if row.get("time") == target), None)
        if match:
            return match
    window = (result.get("today") or {}).get("best_window") or {}
    start = window.get("start")
    if start:
        match = next((row for row in rows if row.get("time") == start), None)
        if match:
            return match
    return rows[0] if rows else {}


def _alert_reason_keys(event: str) -> set[str]:
    keys = set(_ALERT_REASONS.get(event, set()))
    if event:
        keys.add(event.lower().replace(" ", "-"))
    return keys


def _alert_relation(item: dict, window: dict | None) -> str:
    if not window:
        return "unknown"
    window_start = _aware(window.get("start"))
    window_end = _aware(window.get("end"))
    alert_start = _aware(item.get("onset") or item.get("effective"))
    alert_end = _aware(item.get("ends") or item.get("expires"))
    if not window_start or not window_end:
        return "unknown"
    if alert_start and alert_start >= window_end:
        return "after"
    if alert_end and alert_end <= window_start:
        return "before"
    return "overlap"


def _fmt_window(window: dict | None) -> str:
    if not window:
        return "today's relevant period"
    start = _aware(window.get("start"))
    end = _aware(window.get("end"))
    if not start or not end:
        return "today's planning window"
    start_text = start.strftime("%I:%M %p").lstrip("0")
    end_text = end.strftime("%I:%M %p").lstrip("0")
    return f"{start_text}–{end_text}"


def _alert_sentence(result: dict, snapshot: dict, scored: dict) -> str | None:
    alerts = snapshot.get("alerts") or {}
    if alerts.get("status") != "ok":
        return (
            "NWS alert status is unavailable, so CoastalNow is not treating today as a no-alert day; "
            "the safety status takes priority over any numerical planning score."
        )

    items = alerts.get("items") or []
    if not items:
        return None

    day = result.get("today") or {}
    window = day.get("best_window")
    reasons = set(scored.get("reasons") or [])
    applied = [
        item for item in items
        if reasons.intersection(_alert_reason_keys(str(item.get("event") or "").strip()))
    ]
    item = applied[0] if applied else items[0]
    event = str(item.get("event") or "weather alert").strip()
    relation = _alert_relation(item, window)

    if applied:
        if scored.get("hard_stop") or day.get("status") == "NOT RECOMMENDED":
            return (
                f"NWS {event} is the primary reason today is NOT RECOMMENDED; "
                "this safety condition takes priority over otherwise favorable wave, wind, or weather inputs."
            )
        cap = scored.get("safety_cap")
        if cap is not None and float(cap) < 100:
            return (
                f"NWS {event} is active during the best planning window and caps the Surf Conditions Score at "
                f"{_fmt_number(cap)}, even if the underlying wave, wind, and weather inputs would score higher."
            )
        penalty = scored.get("safety_penalty")
        if penalty is not None and float(penalty) > 0:
            return (
                f"NWS {event} is active during the best planning window and applies a "
                f"{_fmt_number(penalty)}-point Safety Gate penalty to the composite score."
            )
        return (
            f"NWS {event} is active during the relevant period and is treated as the first planning consideration."
        )

    if relation == "after":
        return (
            f"NWS {event} is in effect today but begins after the {_fmt_window(window)} planning window, "
            "so it does not directly reduce that window's numerical score; the official alert still takes priority for later plans."
        )
    if relation == "before":
        return (
            f"NWS {event} is listed for today but ends before the {_fmt_window(window)} planning window, "
            "so it does not directly reduce that window's numerical score."
        )
    if relation == "overlap":
        return (
            f"NWS {event} overlaps the {_fmt_window(window)} planning window. It is not a direct v1 Surf Conditions Score "
            "adjustment, but the official alert should be reviewed before relying on the numerical score."
        )
    return (
        f"NWS {event} is active today. Its timing cannot be matched confidently to the planning window, "
        "so the official alert should be reviewed first."
    )


def _safety_gate_sentence(result: dict, scored: dict, raw: dict) -> str | None:
    reasons = set(scored.get("reasons") or [])
    day = result.get("today") or {}
    status = day.get("status") or "Unavailable"
    cap = scored.get("safety_cap")
    penalty = scored.get("safety_penalty")

    wind = raw.get("wind_mph")
    gust = raw.get("gust_mph")
    height = raw.get("wave_height_ft")
    period = raw.get("wave_period_s")
    condition = str(raw.get("condition_text") or "")

    if "wind-hard-stop" in reasons:
        detail = []
        if wind is not None:
            detail.append(f"{_fmt_number(wind)} mph sustained wind")
        if gust is not None:
            detail.append(f"{_fmt_number(gust)} mph gusts")
        measured = _join_phrases(detail) or "the forecast wind"
        return (
            f"{measured.capitalize()} triggers the Surfing Safety Gate, making today NOT RECOMMENDED "
            "regardless of otherwise favorable score inputs."
        )

    if "wave-exposure-hard-stop" in reasons:
        if height is not None and period is not None:
            measured = f"{_fmt_number(height, one_decimal=True)} ft waves at {_fmt_number(period)} sec"
        else:
            measured = "The combined wave height and period"
        return (
            f"{measured} triggers the Surfing Safety Gate, making today NOT RECOMMENDED "
            "regardless of otherwise favorable score inputs."
        )

    if "forecast-thunder-cap" in reasons:
        label = condition if condition else "Thunderstorms"
        return (
            f"{label} during the planning window triggers the Surfing Safety Gate and caps the numerical score at "
            f"{_fmt_number(cap if cap is not None else 39)}."
        )

    if reasons.intersection({"wind-cap-39", "wind-cap-59"}):
        detail = []
        if wind is not None:
            detail.append(f"{_fmt_number(wind)} mph sustained wind")
        if gust is not None:
            detail.append(f"{_fmt_number(gust)} mph gusts")
        measured = _join_phrases(detail) or "Stronger wind"
        return (
            f"{measured.capitalize()} triggers a Safety Gate cap of "
            f"{_fmt_number(cap)} on the Surf Conditions Score."
        )

    if reasons.intersection({"wave-exposure-cap-39", "wave-exposure-cap-69"}):
        if height is not None and period is not None:
            measured = f"{_fmt_number(height, one_decimal=True)} ft waves at {_fmt_number(period)} sec"
        else:
            measured = "The combined wave height and period"
        return (
            f"{measured} triggers a Safety Gate cap of {_fmt_number(cap)} on the Surf Conditions Score."
        )

    if "wave-exposure-caution" in reasons and penalty is not None and float(penalty) > 0:
        if height is not None and period is not None:
            measured = f"{_fmt_number(height, one_decimal=True)} ft waves at {_fmt_number(period)} sec"
        else:
            measured = "The combined wave height and period"
        return (
            f"{measured} subtracts {_fmt_number(penalty)} points from the composite score through the Safety Gate."
        )

    if status == "NOT RECOMMENDED" and scored.get("hard_stop"):
        return (
            "A Surfing Safety Gate hard stop is active, making today NOT RECOMMENDED before normal score inputs are considered."
        )
    return None


def _support_phrase(key: str, raw: dict) -> str:
    if key == "wave_height" and raw.get("wave_height_ft") is not None:
        return f"{_fmt_number(raw['wave_height_ft'], one_decimal=True)} ft wave height"
    if key == "wave_period" and raw.get("wave_period_s") is not None:
        return f"{_fmt_number(raw['wave_period_s'])} sec wave period"
    if key == "wind" and raw.get("wind_mph") is not None:
        return f"{_fmt_number(raw['wind_mph'])} mph winds"
    if key == "weather" and raw.get("precip_probability_pct") is not None:
        return f"{_fmt_number(raw['precip_probability_pct'])}% rain chance"
    if key == "daylight":
        return "daylight during the planning window"
    return key.replace("_", " ")


def _drag_phrase(key: str, raw: dict) -> str:
    if key == "wave_height" and raw.get("wave_height_ft") is not None:
        height = float(raw["wave_height_ft"])
        prefix = "low" if height < 2 else "higher" if height > 4 else ""
        value = f"{_fmt_number(height, one_decimal=True)} ft wave height"
        return f"{prefix} {value}".strip()
    if key == "wave_period" and raw.get("wave_period_s") is not None:
        period = float(raw["wave_period_s"])
        prefix = "short" if period < 7 else ""
        return f"{prefix} {_fmt_number(period)} sec wave period".strip()
    if key == "wind" and raw.get("wind_mph") is not None:
        return f"{_fmt_number(raw['wind_mph'])} mph winds"
    if key == "weather" and raw.get("precip_probability_pct") is not None:
        return f"{_fmt_number(raw['precip_probability_pct'])}% rain chance"
    if key == "daylight":
        return "limited daylight"
    return key.replace("_", " ")


def _join_phrases(items: list[str]) -> str:
    items = [item for item in items if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _score_sentences(result: dict, scored: dict, raw: dict) -> list[str]:
    day = result.get("today") or {}
    status = day.get("status") or "Unavailable"
    score = day.get("score")
    components = scored.get("components") or {}

    if status == "NOT RECOMMENDED":
        context = [
            _support_phrase(key, raw)
            for key in ("wave_height", "wave_period", "wind")
            if components.get(key) is not None and float(components[key]) >= 70
        ][:2]
        if context:
            return [f"Outside that safety stop, {_join_phrases(context)} would otherwise support the planning inputs."]
        return []

    if score is None:
        missing = []
        if raw.get("wave_height_ft") is None:
            missing.append("wave height")
        if raw.get("wave_period_s") is None:
            missing.append("wave period")
        if raw.get("wind_mph") is None:
            missing.append("wind")
        if raw.get("precip_probability_pct") is None:
            missing.append("weather")
        if missing:
            return [
                f"No numerical Surf Conditions Score is shown because {_join_phrases(missing)} data is incomplete or unavailable."
            ]
        return ["No numerical Surf Conditions Score is shown because the current data confidence does not meet the publication threshold."]

    score_value = float(score)
    available = {
        key: float(value)
        for key, value in components.items()
        if key in SURFING_WEIGHTS and value is not None
    }
    supports = sorted(
        (key for key, value in available.items() if value >= 85),
        key=lambda key: -(SURFING_WEIGHTS[key] * available[key]),
    )
    drags = sorted(
        (key for key, value in available.items() if value < 85),
        key=lambda key: -(SURFING_WEIGHTS[key] * (100 - available[key])),
    )

    support_text = _join_phrases([_support_phrase(key, raw) for key in supports[:3]])
    drag_text = _join_phrases([_drag_phrase(key, raw) for key in drags[:2]])

    if score_value >= 75:
        first = f"Today's {score_value:g} score"
        if support_text:
            first += f" is mainly supported by {support_text}."
        else:
            first += " reflects broadly favorable inputs during the best planning window."
        sentences = [first]
        if drags:
            sentences.append(f"The {drag_text} is the main factor keeping the score below the top range.")
        return sentences

    if score_value < 60:
        sentences = []
        if drag_text:
            sentences.append(f"Today's {score_value:g} score is being held down mainly by {drag_text}.")
        else:
            sentences.append(f"Today's {score_value:g} score reflects weaker combined planning inputs.")
        if supports:
            sentences.append(f"{_support_phrase(supports[0], raw).capitalize()} still provides some support.")
        return sentences

    if support_text and drag_text:
        return [f"Today's {score_value:g} score is mixed: {support_text} supports it, while {drag_text} pulls it down."]
    if support_text:
        return [f"Today's {score_value:g} score is supported mainly by {support_text}."]
    if drag_text:
        return [f"Today's {score_value:g} score is limited mainly by {drag_text}."]
    return [f"Today's {score_value:g} score reflects the combined wave, wind, weather, and daylight inputs."]


def build_surfing_explanation(result: dict, snapshot: dict) -> str:
    scored = _chosen_scored_row(result)
    raw = _chosen_raw_row(snapshot, scored, result)
    sentences = []
    alert = _alert_sentence(result, snapshot, scored)
    if alert:
        sentences.append(alert)

    alerts = (snapshot.get("alerts") or {}).get("items") or []
    reasons = set(scored.get("reasons") or [])
    alert_applied = any(
        reasons.intersection(_alert_reason_keys(str(item.get("event") or "").strip()))
        for item in alerts
    )
    safety = None if alert_applied else _safety_gate_sentence(result, scored, raw)
    if safety:
        sentences.append(safety)

    sentences.extend(_score_sentences(result, scored, raw))
    return " ".join(sentences[:3])
