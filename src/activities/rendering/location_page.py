"""Render a location-first Fishing conditions page."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from activities.explanations import explain_reasons
from activities.rendering.links import activity_hub_url, tide_parent_url
from site_generator import LOGO

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "activity-location.html"

_FACTOR_LABELS = {
    "tide": "Tide movement",
    "wind": "Wind",
    "wave": "Wave / sea state",
    "weather": "Weather",
    "time_of_day": "Time of day",
    "solunar": "Moon / Solunar",
    "water_temperature": "Water temperature",
}


def _fill(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    if "{{" in out or "}}" in out:
        raise ValueError("Unresolved Activity template token")
    return out


def _fmt_time(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%I:%M %p").lstrip("0")


def _fmt_window(day: dict) -> str:
    window = day.get("best_window")
    if not window:
        return "—"
    return f'{_fmt_time(window["start"])}–{_fmt_time(window["end"])}'


def _score_card(day: dict) -> str:
    status = day.get("status") or "Unavailable"
    score = day.get("score")
    confidence = day.get("confidence") or "Unavailable"
    if status == "NOT RECOMMENDED":
        return (
            '<section class="activity-score-card danger">'
            '<span class="activity-score-label">Fishing Score</span>'
            '<strong class="activity-score-state">NOT RECOMMENDED</strong>'
            '<small>Safety condition takes priority</small>'
            f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
            '</section>'
        )
    if score is None:
        return (
            f'<section class="activity-score-card data-state {escape(status.lower().replace(" ", "-"))}">'
            '<span class="activity-score-label">Fishing Score</span>'
            '<strong class="activity-score-value">—</strong>'
            f'<small>{escape(status)}</small>'
            f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
            '</section>'
        )
    return (
        '<section class="activity-score-card">'
        '<span class="activity-score-label">Fishing Score</span>'
        f'<strong class="activity-score-value">{score:g}</strong>'
        f'<small>{escape(str(day.get("rating") or ""))}</small>'
        f'<div class="activity-best-time"><span>Best Fishing Time</span><b>{escape(_fmt_window(day))}</b></div>'
        f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
        '</section>'
    )


def _safety_strip(result: dict, snapshot: dict) -> str:
    day = result.get("today") or {}
    if day.get("status") == "NOT RECOMMENDED":
        return '<div class="activity-safety-strip danger"><strong>Safety condition takes priority.</strong> Check current official warnings and local guidance before approaching the shore.</div>'
    alerts = snapshot.get("alerts") or {}
    if alerts.get("status") != "ok":
        return '<div class="activity-safety-strip unknown"><strong>Safety alert status unavailable.</strong> CoastalNow is not treating this as a no-alert condition.</div>'
    count = len(alerts.get("items") or [])
    if count:
        return f'<div class="activity-safety-strip caution"><strong>{count} active NWS alert(s) detected.</strong> Review official alert details before making plans.</div>'
    return '<div class="activity-safety-strip normal"><strong>Latest NWS alert check completed.</strong> Conditions can still change; local signs and official guidance take priority.</div>'


def _day_cards(result: dict) -> str:
    cards = []
    for key, label in (("today", "Today"), ("tomorrow", "Tomorrow")):
        day = result.get(key) or {}
        score = day.get("score")
        score_text = "—" if score is None else f"{score:g}"
        detail = day.get("status") if score is None else day.get("rating")
        cards.append(
            f'<article class="activity-day-card" data-day="{key}"><span>{label}</span>'
            f'<strong>{escape(score_text)}</strong><small>{escape(str(detail or "Unavailable"))}</small>'
            f'<p>{escape(_fmt_window(day))}</p></article>'
        )
    return '<section class="activity-day-switch">' + "".join(cards) + "</section>"


def _hourly_section(result: dict) -> str:
    rows = (result.get("hourly") or {}).get("today") or []
    if not rows:
        body = '<div class="activity-empty">Hourly score is unavailable for today.</div>'
    else:
        items = []
        for row in rows:
            score = row.get("final_score")
            if row.get("hard_stop"):
                score_text = "STOP"
            elif score is None:
                score_text = "—"
            else:
                score_text = f"{score:g}"
            items.append(
                '<div class="activity-hour-row">'
                f'<span>{escape(_fmt_time(row["time"]))}</span>'
                f'<div class="activity-hour-track"><i style="width:{0 if score is None else max(0, min(100, float(score))):g}%"></i></div>'
                f'<strong>{escape(score_text)}</strong>'
                f'<small>{escape(str(row.get("confidence") or ""))}</small>'
                '</div>'
            )
        body = '<div class="activity-hourly-list">' + "".join(items) + "</div>"
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">BY HOUR</p><h2>Hourly Fishing Score</h2></div><p>Local time</p></div>' + body + '</section>'


def _factor_section(result: dict) -> str:
    rows = (result.get("hourly") or {}).get("today") or []
    chosen = None
    window = (result.get("today") or {}).get("best_window")
    if window:
        chosen = next((row for row in rows if row.get("time") == window.get("start")), None)
    chosen = chosen or (rows[0] if rows else None)
    components = (chosen or {}).get("components") or {}
    factor_rows = []
    for key, label in _FACTOR_LABELS.items():
        value = components.get(key)
        factor_rows.append(
            '<div class="activity-factor-row">'
            f'<span>{escape(label)}</span>'
            f'<strong>{"—" if value is None else f"{float(value):g}"}</strong>'
            '</div>'
        )
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">BREAKDOWN</p><h2>Why this score?</h2></div></div><div class="activity-factor-list">' + "".join(factor_rows) + '</div></section>'


def _condition_row(snapshot: dict, result: dict) -> dict:
    rows = snapshot.get("hourly") or []
    window = (result.get("today") or {}).get("best_window")
    if window:
        found = next((row for row in rows if row.get("time") == window.get("start")), None)
        if found:
            return found
    return rows[0] if rows else {}


def _condition_section(snapshot: dict, result: dict) -> str:
    row = _condition_row(snapshot, result)
    metrics = [
        ("Wind", "—" if row.get("wind_mph") is None else f'{float(row["wind_mph"]):.1f} mph'),
        ("Gust", "—" if row.get("gust_mph") is None else f'{float(row["gust_mph"]):.1f} mph'),
        ("Wave height", "—" if row.get("wave_height_ft") is None else f'{float(row["wave_height_ft"]):.1f} ft'),
        ("Wave period", "—" if row.get("wave_period_s") is None else f'{float(row["wave_period_s"]):.1f} sec'),
        ("Rain chance", "—" if row.get("precip_probability_pct") is None else f'{float(row["precip_probability_pct"]):.0f}%'),
        ("Water temp", "—" if row.get("water_temperature_f") is None else f'{float(row["water_temperature_f"]):.1f}°F'),
    ]
    cards = "".join(f'<div class="activity-condition-stat"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>' for label, value in metrics)
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">COASTAL CONDITIONS</p><h2>Wind, waves and weather</h2></div></div><div class="activity-condition-grid">' + cards + '</div></section>'


def _tide_section(snapshot: dict) -> str:
    events = ((snapshot.get("tide") or {}).get("hilo") or [])[:4]
    if not events:
        body = '<div class="activity-empty">Tide timing is unavailable.</div>'
    else:
        rows = []
        for event in events:
            kind = "High" if event.get("type") == "H" else "Low"
            try:
                time_text = datetime.strptime(event["t"], "%Y-%m-%d %H:%M").strftime("%I:%M %p").lstrip("0")
            except Exception:
                time_text = str(event.get("t") or "—")
            height = "—" if event.get("v") is None else f'{float(event["v"]):.1f} ft'
            rows.append(f'<div class="activity-tide-event"><span>{kind}</span><strong>{escape(time_text)}</strong><small>{escape(height)}</small></div>')
        body = '<div class="activity-tide-events">' + "".join(rows) + '</div>'
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">TIDE CONTEXT</p><h2>Today’s tide turning points</h2></div><p>For detailed tide charts, use the Tide page.</p></div>' + body + '</section>'


def _why_section(result: dict) -> str:
    reasons = (result.get("today") or {}).get("reasons") or []
    text = explain_reasons(reasons)
    if not text:
        status = (result.get("today") or {}).get("status")
        if status == "NOT RECOMMENDED":
            text = "Current safety conditions prevent a normal Fishing recommendation."
        elif status in {"Limited", "Unavailable"}:
            text = "Some critical coastal-condition data is not complete enough for a normal recommendation."
        else:
            text = "The score combines tide movement, wind, waves, weather and time-of-day conditions."
    return '<section class="section activity-panel activity-why"><div class="section-head"><div><p class="eyebrow">EXPLANATION</p><h2>What is driving today’s result?</h2></div></div><p>' + escape(text) + '</p></section>'


def render_fishing_location(location: dict, result: dict, snapshot: dict, *, head_extra: str = "") -> str:
    """Render one Fishing child page without changing the parent Tide URL."""
    template = TEMPLATE.read_text(encoding="utf-8")
    breadcrumbs = (
        '<div class="breadcrumbs"><a href="/">Home</a><span>/</span>'
        f'<a href="/tides/{escape(location["state_slug"])}/">{escape(location["state"])}</a><span>/</span>'
        f'<a href="{escape(tide_parent_url(location))}">{escape(location["name"])}</a><span>/</span>Fishing</div>'
    )
    links = (
        f'<a href="{escape(tide_parent_url(location))}"><span>Detailed {escape(location["name"])} tide forecast</span><b>View tide page →</b></a>'
        f'<a href="{escape(activity_hub_url("fishing"))}"><span>Compare fishing conditions nationwide</span><b>Fishing hub →</b></a>'
    )
    return _fill(template, {
        "TITLE": escape(f'{location["name"]} Fishing Conditions Today | CoastalNow'),
        "DESCRIPTION": escape(f'Fishing conditions today for {location["name"]}, {location["state"]}, including tide, wind, waves, best fishing time and safety context.', quote=True),
        "HEAD_EXTRA": head_extra,
        "LOGO": LOGO,
        "BREADCRUMBS": breadcrumbs,
        "SAFETY_STRIP": _safety_strip(result, snapshot),
        "H1": escape(f'{location["name"]} Fishing Conditions Today'),
        "SCORE_CARD": _score_card(result.get("today") or {}),
        "TODAY_TOMORROW": _day_cards(result),
        "HOURLY_SECTION": _hourly_section(result),
        "FACTOR_SECTION": _factor_section(result),
        "CONDITION_SECTION": _condition_section(snapshot, result),
        "TIDE_SECTION": _tide_section(snapshot),
        "WHY_SECTION": _why_section(result),
        "LINKS": links,
        "DISCLAIMER": escape(result.get("safety_disclaimer") or "Fishing Score is a planning metric, not a safety guarantee. Official warnings and local guidance always take priority."),
    })
