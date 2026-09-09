"""Render a location-first Fishing conditions page."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from activities.explanations import summarize_fishing_result
from activities.registry import enabled_activities_for_location
from activities.rendering.links import activity_hub_url, activity_location_url, tide_parent_url
from activities.rendering.surfing_alert_details import build_nws_alert_details
from activities.rendering.surfing_explanation import _alert_relation, _fmt_window as _fmt_alert_window
from site_generator import LOGO

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "activity-location.html"

_FACTOR_LABELS = {
    "tide": "Tide movement score",
    "wind": "Wind score",
    "wave": "Wave / sea state score",
    "weather": "Weather score",
    "time_of_day": "Time of day score",
    "solunar": "Moon / Solunar score",
    "water_temperature": "Water temperature score",
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


def _limited_or_unavailable(day: dict) -> bool:
    status = day.get("status") or "Unavailable"
    return day.get("confidence") in {"Limited", "Unavailable"} or status in {"Limited", "Unavailable"}


def _data_state_label(day: dict) -> str:
    status = day.get("status") or "Unavailable"
    confidence = day.get("confidence") or "Unavailable"
    if "Limited" in {status, confidence}:
        return "Limited"
    if "Unavailable" in {status, confidence}:
        return "Unavailable"
    return status


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
    if score is None or _limited_or_unavailable(day):
        label = _data_state_label(day)
        return (
            f'<section class="activity-score-card data-state {escape(label.lower().replace(" ", "-"))}">'
            '<span class="activity-score-label">Fishing Score</span>'
            '<strong class="activity-score-value">—</strong>'
            f'<small>{escape(label)}</small>'
            f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
            '</section>'
        )
    return (
        '<section class="activity-score-card">'
        '<span class="activity-score-label">Fishing Score</span>'
        f'<strong class="activity-score-value">{score:g}</strong>'
        f'<small>{escape(str(day.get("rating") or ""))}</small>'
        '<div class="activity-score-definition">0–100 composite planning score · not a raw environmental measurement</div>'
        f'<div class="activity-best-time"><span>Best Fishing Time</span><b>{escape(_fmt_window(day))}</b></div>'
        f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
        '</section>'
    )


def _alert_detail_markup(snapshot: dict) -> str:
    blocks = []
    for detail in build_nws_alert_details(snapshot):
        summary = detail.get("summary") or ""
        summary_html = f'<p>{escape(summary)}</p>' if summary else ""
        blocks.append(
            '<div class="activity-alert-detail">'
            f'<strong>{escape(detail["event"])}</strong>'
            f'<span>{escape(detail["period"])}</span>'
            f'{summary_html}'
            '</div>'
        )
    return "".join(blocks)


def _safety_strip(result: dict, snapshot: dict) -> str:
    day = result.get("today") or {}
    alerts = snapshot.get("alerts") or {}
    if alerts.get("status") != "ok":
        if day.get("status") == "NOT RECOMMENDED":
            return '<div class="activity-safety-strip danger"><strong>Safety condition takes priority.</strong> NWS alert status is unavailable; check current official warnings and local guidance before approaching the shore.</div>'
        return '<div class="activity-safety-strip unknown"><strong>Safety alert status unavailable.</strong> CoastalNow is not treating this as a no-alert condition.</div>'

    details = build_nws_alert_details(snapshot)
    if details:
        css_class = "danger" if day.get("status") == "NOT RECOMMENDED" else "caution"
        priority = "Safety condition takes priority. " if day.get("status") == "NOT RECOMMENDED" else ""
        return (
            f'<div class="activity-safety-strip {css_class}">'
            f'<div><strong>{priority}{len(details)} active NWS alert(s) detected.</strong> Official alert details take priority over the numerical Fishing Score.</div>'
            f'{_alert_detail_markup(snapshot)}'
            '</div>'
        )

    if day.get("status") == "NOT RECOMMENDED":
        return '<div class="activity-safety-strip danger"><strong>Safety condition takes priority.</strong> Check current official warnings and local guidance before approaching the shore.</div>'
    return '<div class="activity-safety-strip normal"><strong>Latest NWS alert check completed.</strong> Conditions can still change; local signs and official guidance take priority.</div>'


def _day_cards(result: dict) -> str:
    cards = []
    for key, label in (("today", "Today"), ("tomorrow", "Tomorrow")):
        day = result.get(key) or {}
        status = day.get("status") or "Unavailable"
        score = day.get("score")
        if status == "NOT RECOMMENDED":
            score_text = "—"
            detail = "NOT RECOMMENDED"
        elif _limited_or_unavailable(day):
            score_text = "—"
            detail = _data_state_label(day)
        else:
            score_text = "—" if score is None else f"{score:g}"
            detail = status if score is None else day.get("rating")
        cards.append(
            f'<article class="activity-day-card" data-day="{key}"><span>{label}</span>'
            f'<strong>{escape(score_text)}</strong><small>{escape(str(detail or "Unavailable"))}</small>'
            f'<p>{escape(_fmt_window(day))}</p></article>'
        )
    return '<section class="activity-day-switch">' + "".join(cards) + "</section>"


def _hourly_section(result: dict) -> str:
    hourly = result.get("hourly") or {}
    rows = list(hourly.get("today") or []) + list(hourly.get("tomorrow") or [])
    rows = sorted(rows, key=lambda row: row.get("time") or "")[:24]

    if not rows:
        body = '<div class="activity-empty">24-hour Fishing Conditions Forecast is unavailable.</div>'
    else:
        items = []
        for row in rows:
            score = row.get("final_score")
            confidence = row.get("confidence") or "Unavailable"
            if row.get("hard_stop"):
                score_text, width, detail = "NOT RECOMMENDED", 0, "Alert active"
            elif confidence in {"Limited", "Unavailable"}:
                score_text, width, detail = confidence, 0, confidence
            elif score is None:
                score_text, width, detail = "—", 0, confidence
            else:
                score_text = f"{score:g}"
                width = max(0, min(100, float(score)))
                detail = confidence
            items.append(
                '<div class="activity-hour-row">'
                f'<span>{escape(_fmt_time(row["time"]))}</span>'
                f'<div class="activity-hour-track"><i style="width:{width:g}%"></i></div>'
                f'<strong>{escape(score_text)}</strong><small>{escape(detail)}</small>'
                '</div>'
            )
        body = '<div class="activity-hourly-list">' + "".join(items) + "</div>"
    return (
        '<section class="section activity-panel"><div class="section-head"><div>'
        '<p class="eyebrow">NEXT 24 HOURS</p><h2>24-Hour Fishing Conditions Forecast</h2></div>'
        '<p>0–100 score · Local time · Safety hard-stop hours show NOT RECOMMENDED</p></div>'
        + body + '</section>'
    )


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
    note = '<p class="activity-score-note">Factor scores are normalized from 0–100. They are scoring inputs, not raw weather or ocean measurements.</p>'
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">BREAKDOWN</p><h2>Why this score?</h2></div></div>' + note + '<div class="activity-factor-list">' + "".join(factor_rows) + '</div></section>'


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


def _fishing_alert_explanation(result: dict, snapshot: dict) -> list[str]:
    details = build_nws_alert_details(snapshot)
    if not details:
        return []

    joined = "; ".join(f'{detail["event"]} ({detail["period"]})' for detail in details)
    sentences = [f"NWS alert details: {joined}."]
    first_summary = details[0].get("summary") or ""
    if first_summary:
        sentences.append(first_summary)

    items = ((snapshot.get("alerts") or {}).get("items") or [])
    if items:
        item = items[0]
        event = str(item.get("event") or "weather alert").strip()
        window = (result.get("today") or {}).get("best_window")
        relation = _alert_relation(item, window)
        window_text = _fmt_alert_window(window)
        if relation == "after":
            sentences.append(
                f"The {event} begins after the {window_text} fishing window, so it may not directly reduce that window's numerical score; the official alert still takes priority once its stated period begins."
            )
        elif relation == "before":
            sentences.append(
                f"The {event} ends before the {window_text} fishing window, so it does not directly reduce that window's numerical score; the official alert should still be reviewed first."
            )
        elif relation == "overlap":
            sentences.append(
                f"The {event} overlaps the {window_text} fishing window; the official alert should be reviewed first even when it is not a direct Fishing Score adjustment."
            )
        else:
            sentences.append(
                f"The timing of the {event} cannot be matched confidently to the fishing window, so the official alert should be reviewed first."
            )
    return sentences


def _why_section(result: dict, snapshot: dict | None = None) -> str:
    day = result.get("today") or {}
    score_text = summarize_fishing_result(day)
    paragraphs = []
    if snapshot is not None:
        paragraphs.extend(_fishing_alert_explanation(result, snapshot))
    paragraphs.append(score_text)
    body = "".join(f'<p>{escape(text)}</p>' for text in paragraphs if text)
    return '<section class="section activity-panel activity-why"><div class="section-head"><div><p class="eyebrow">EXPLANATION</p><h2>What is driving today’s result?</h2></div></div>' + body + '</section>'


def render_fishing_location(location: dict, result: dict, snapshot: dict, *, head_extra: str = "") -> str:
    """Render one Fishing child page without changing the parent Tide URL."""
    template = TEMPLATE.read_text(encoding="utf-8")
    breadcrumbs = (
        '<div class="breadcrumbs"><a href="/">Home</a><span>/</span>'
        f'<a href="/tides/{escape(location["state_slug"])}/">{escape(location["state"])}</a><span>/</span>'
        f'<a href="{escape(tide_parent_url(location))}">{escape(location["name"])}</a><span>/</span>Fishing</div>'
    )
    sibling_links = []
    for activity in enabled_activities_for_location(location):
        if activity["slug"] == "fishing":
            continue
        sibling_links.append(
            f'<a href="{escape(activity_location_url(location, activity["slug"]))}">'
            f'<span>{escape(location["name"])} {escape(activity["label"].lower())} conditions</span>'
            f'<b>View {escape(activity["label"].lower())} conditions →</b></a>'
        )
    links = (
        f'<a href="{escape(tide_parent_url(location))}"><span>Detailed {escape(location["name"])} tide forecast</span><b>View tide page →</b></a>'
        + "".join(sibling_links)
        + f'<a href="{escape(activity_hub_url("fishing"))}"><span>Compare fishing conditions nationwide</span><b>Fishing hub →</b></a>'
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
        "WHY_SECTION": _why_section(result, snapshot),
        "LINKS": links,
        "DISCLAIMER": escape(result.get("safety_disclaimer") or "Fishing Score is a planning metric, not a safety guarantee. Official warnings and local guidance always take priority."),
    })
