"""Render Surfing v1 location pages and the Surfing pilot hub."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from activities.rendering.links import activity_hub_url, activity_location_url, tide_parent_url
from site_generator import LOGO

ROOT = Path(__file__).resolve().parents[2]
LOCATION_TEMPLATE = ROOT / "templates" / "activity-location.html"
HUB_TEMPLATE = ROOT / "templates" / "activity-hub.html"

_FACTOR_LABELS = {
    "wave_height": "Wave height score",
    "wave_period": "Wave period score",
    "wind": "Wind score",
    "weather": "Weather score",
    "daylight": "Daylight score",
}

_REASON_COPY = {
    "moderate-wave-height": "Moderate wave height supports the composite planning score.",
    "organized-wave-period": "Wave period is in the stronger v1 planning range.",
    "lighter-wind": "Lighter wind supports the composite planning score.",
    "stronger-wind": "Stronger wind is reducing the planning score.",
    "wet-weather": "Wetter weather is reducing the planning score.",
}


def _fill(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    if "{{" in out or "}}" in out:
        raise ValueError("Unresolved Surfing template token")
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
    confidence = day.get("confidence") or "Unavailable"
    return status in {"Limited", "Unavailable"} or confidence in {"Limited", "Unavailable"}


def _data_state_label(day: dict) -> str:
    status = day.get("status") or "Unavailable"
    confidence = day.get("confidence") or "Unavailable"
    if "Limited" in {status, confidence}:
        return "Limited"
    return "Unavailable"


def _score_card(day: dict) -> str:
    status = day.get("status") or "Unavailable"
    confidence = day.get("confidence") or "Unavailable"
    score = day.get("score")
    if status == "NOT RECOMMENDED":
        return (
            '<section class="activity-score-card danger">'
            '<span class="activity-score-label">Surf Conditions Score</span>'
            '<strong class="activity-score-state">NOT RECOMMENDED</strong>'
            '<small>Safety condition takes priority</small>'
            f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
            '</section>'
        )
    if score is None or _limited_or_unavailable(day):
        label = _data_state_label(day)
        return (
            f'<section class="activity-score-card data-state {escape(label.lower())}">'
            '<span class="activity-score-label">Surf Conditions Score</span>'
            '<strong class="activity-score-value">—</strong>'
            f'<small>{escape(label)}</small>'
            f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
            '</section>'
        )
    return (
        '<section class="activity-score-card">'
        '<span class="activity-score-label">Surf Conditions Score</span>'
        f'<strong class="activity-score-value">{float(score):g}</strong>'
        f'<small>{escape(str(day.get("rating") or ""))}</small>'
        '<div class="activity-score-definition">0–100 composite planning score · not a raw environmental measurement</div>'
        f'<div class="activity-best-time"><span>Best Surf Planning Window</span><b>{escape(_fmt_window(day))}</b></div>'
        f'<div class="activity-confidence">Confidence: {escape(confidence)}</div>'
        '</section>'
    )


def _safety_strip(result: dict, snapshot: dict) -> str:
    day = result.get("today") or {}
    if day.get("status") == "NOT RECOMMENDED":
        return '<div class="activity-safety-strip danger"><strong>Safety condition takes priority.</strong> Check current official warnings, closures and local guidance before approaching or entering the water.</div>'
    alerts = snapshot.get("alerts") or {}
    if alerts.get("status") != "ok":
        return '<div class="activity-safety-strip unknown"><strong>Safety alert status unavailable.</strong> CoastalNow is not treating this as a no-alert condition.</div>'
    count = len(alerts.get("items") or [])
    if count:
        return f'<div class="activity-safety-strip caution"><strong>{count} active NWS alert(s) detected.</strong> Review official alert details before making plans.</div>'
    return '<div class="activity-safety-strip normal"><strong>Latest NWS alert check completed.</strong> This is not a safety clearance; local signs, closures and official guidance take priority.</div>'


def _day_cards(result: dict) -> str:
    cards = []
    for key, label in (("today", "Today"), ("tomorrow", "Tomorrow")):
        day = result.get(key) or {}
        status = day.get("status") or "Unavailable"
        score = day.get("score")
        if status == "NOT RECOMMENDED":
            score_text, detail = "—", "NOT RECOMMENDED"
        elif _limited_or_unavailable(day):
            score_text, detail = "—", _data_state_label(day)
        else:
            score_text = "—" if score is None else f"{float(score):g}"
            detail = status if score is None else day.get("rating")
        cards.append(
            f'<article class="activity-day-card" data-day="{key}"><span>{label}</span>'
            f'<strong>{escape(score_text)}</strong><small>{escape(str(detail or "Unavailable"))}</small>'
            f'<p>{escape(_fmt_window(day))}</p></article>'
        )
    return '<section class="activity-day-switch">' + "".join(cards) + "</section>"


def _hourly_section(result: dict) -> str:
    day = result.get("today") or {}
    status = day.get("status") or "Unavailable"
    rows = (result.get("hourly") or {}).get("today") or []
    if status == "NOT RECOMMENDED":
        body = '<div class="activity-empty">Safety condition takes priority — hourly numerical planning score is not shown.</div>'
    elif _limited_or_unavailable(day):
        label = _data_state_label(day)
        body = f'<div class="activity-empty">{escape(label)} data — hourly numerical planning score is not shown because critical coastal context is incomplete.</div>'
    elif not rows:
        body = '<div class="activity-empty">Hourly Surf Conditions Score is unavailable for today.</div>'
    else:
        items = []
        for row in rows:
            confidence = row.get("confidence") or "Unavailable"
            score = row.get("final_score")
            if row.get("hard_stop"):
                score_text, width = "STOP", 0
            elif confidence in {"Limited", "Unavailable"}:
                score_text, width = confidence, 0
            elif score is None:
                score_text, width = "—", 0
            else:
                score_text, width = f"{float(score):g}", max(0, min(100, float(score)))
            items.append(
                '<div class="activity-hour-row">'
                f'<span>{escape(_fmt_time(row["time"]))}</span>'
                f'<div class="activity-hour-track"><i style="width:{width:g}%"></i></div>'
                f'<strong>{escape(score_text)}</strong><small>{escape(confidence)}</small></div>'
            )
        body = '<div class="activity-hourly-list">' + "".join(items) + '</div>'
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">BY HOUR</p><h2>Hourly Surf Conditions Score</h2></div><p>0–100 score · Local time</p></div>' + body + '</section>'


def _factor_section(result: dict) -> str:
    rows = (result.get("hourly") or {}).get("today") or []
    window = (result.get("today") or {}).get("best_window")
    chosen = next((row for row in rows if window and row.get("time") == window.get("start")), None)
    chosen = chosen or (rows[0] if rows else None)
    components = (chosen or {}).get("components") or {}
    items = []
    for key, label in _FACTOR_LABELS.items():
        value = components.get(key)
        items.append(
            '<div class="activity-factor-row">'
            f'<span>{escape(label)}</span><strong>{"—" if value is None else f"{float(value):g}"}</strong></div>'
        )
    note = '<p class="activity-score-note">Factor scores are normalized from 0–100. They are scoring inputs, not raw weather or ocean measurements.</p>'
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">BREAKDOWN</p><h2>Why this score?</h2></div></div>' + note + '<div class="activity-factor-list">' + "".join(items) + '</div></section>'


def _condition_row(snapshot: dict, result: dict) -> dict:
    rows = snapshot.get("hourly") or []
    window = (result.get("today") or {}).get("best_window")
    if window:
        chosen = next((row for row in rows if row.get("time") == window.get("start")), None)
        if chosen:
            return chosen
    return rows[0] if rows else {}


def _condition_section(snapshot: dict, result: dict) -> str:
    row = _condition_row(snapshot, result)
    metrics = [
        ("Wave height", "—" if row.get("wave_height_ft") is None else f'{float(row["wave_height_ft"]):.1f} ft'),
        ("Wave period", "—" if row.get("wave_period_s") is None else f'{float(row["wave_period_s"]):.1f} sec'),
        ("Wind", "—" if row.get("wind_mph") is None else f'{float(row["wind_mph"]):.1f} mph'),
        ("Gust", "—" if row.get("gust_mph") is None else f'{float(row["gust_mph"]):.1f} mph'),
        ("Rain chance", "—" if row.get("precip_probability_pct") is None else f'{float(row["precip_probability_pct"]):.0f}%'),
    ]
    cards = "".join(
        f'<div class="activity-condition-stat"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in metrics
    )
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">COASTAL CONDITIONS</p><h2>Wave, wind and weather context</h2></div></div><div class="activity-condition-grid">' + cards + '</div></section>'


def _tide_section(snapshot: dict) -> str:
    events = ((snapshot.get("tide") or {}).get("hilo") or [])[:4]
    if not events:
        body = '<div class="activity-empty">Tide context is unavailable. Tide is not part of the Surf Conditions Score.</div>'
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
    return '<section class="section activity-panel"><div class="section-head"><div><p class="eyebrow">TIDE CONTEXT</p><h2>Today’s tide turning points</h2></div><p>Tide is shown as context and is not included in the v1 composite score.</p></div>' + body + '</section>'


def _why_section(result: dict) -> str:
    reasons = (result.get("today") or {}).get("reasons") or []
    messages = [_REASON_COPY[reason] for reason in reasons if reason in _REASON_COPY]
    if not messages:
        messages = ["The current result combines wave height, wave period, wind, weather and daylight scoring inputs with the Safety Gate."]
    return '<section class="section activity-panel activity-why"><div class="section-head"><div><p class="eyebrow">EXPLANATION</p><h2>What is driving today’s result?</h2></div></div><p>' + escape(" ".join(messages)) + '</p></section>'


def render_surfing_location(location: dict, result: dict, snapshot: dict, *, head_extra: str = "") -> str:
    template = LOCATION_TEMPLATE.read_text(encoding="utf-8")
    template = template.replace("COASTAL FISHING PLANNER", "COASTAL SURF PLANNER")
    template = template.replace(
        "Shore, pier and nearshore recreational fishing conditions.",
        "General coastal surf planning context. Conditions are not break-specific.",
    )
    breadcrumbs = (
        '<div class="breadcrumbs"><a href="/">Home</a><span>/</span>'
        f'<a href="/tides/{escape(location["state_slug"])}/">{escape(location["state"])}</a><span>/</span>'
        f'<a href="{escape(tide_parent_url(location))}">{escape(location["name"])}</a><span>/</span>Surfing</div>'
    )
    links = (
        f'<a href="{escape(tide_parent_url(location))}"><span>Detailed {escape(location["name"])} tide forecast</span><b>View tide page →</b></a>'
        f'<a href="{escape(activity_location_url(location, "fishing"))}"><span>{escape(location["name"])} fishing conditions</span><b>View fishing conditions →</b></a>'
        f'<a href="{escape(activity_hub_url("surfing"))}"><span>Compare Surfing pilot locations</span><b>Surfing hub →</b></a>'
    )
    disclaimer = result.get("safety_disclaimer") or (
        "Surf Conditions Score is a planning metric, not a safety guarantee or a break-specific forecast. "
        "Official warnings and local guidance always take priority."
    )
    if "not break-specific" not in disclaimer.lower():
        disclaimer += " Conditions are not break-specific."
    return _fill(template, {
        "TITLE": escape(f'{location["name"]} Surf Conditions & Best Times | CoastalNow'),
        "DESCRIPTION": escape(f'Surf conditions planning for {location["name"]}, {location["state"]}, with wave, wind, weather and tide context.', quote=True),
        "HEAD_EXTRA": head_extra,
        "LOGO": LOGO,
        "BREADCRUMBS": breadcrumbs,
        "SAFETY_STRIP": _safety_strip(result, snapshot),
        "H1": escape(f'{location["name"]} Surf Conditions'),
        "SCORE_CARD": _score_card(result.get("today") or {}),
        "TODAY_TOMORROW": _day_cards(result),
        "HOURLY_SECTION": _hourly_section(result),
        "FACTOR_SECTION": _factor_section(result),
        "CONDITION_SECTION": _condition_section(snapshot, result),
        "TIDE_SECTION": _tide_section(snapshot),
        "WHY_SECTION": _why_section(result),
        "LINKS": links,
        "DISCLAIMER": escape(disclaimer),
    })


def _ranking(locations: dict[str, dict], results: dict[str, dict], day_key: str) -> list[tuple[dict, dict]]:
    rows = []
    for slug, result in results.items():
        location = locations.get(slug)
        if not location:
            continue
        day = result.get(day_key) or {}
        if day.get("ranking_eligible") and day.get("confidence") in {"High", "Medium"} and day.get("score") is not None and day.get("status") != "NOT RECOMMENDED":
            rows.append((location, day))
    return sorted(rows, key=lambda item: (-float(item[1]["score"]), item[0]["name"].casefold()))


def _hub_top_cards(rows: list[tuple[dict, dict]]) -> str:
    if not rows:
        return '<div class="activity-empty">No pilot locations currently meet the ranking requirements.</div>'
    items = []
    for index, (location, day) in enumerate(rows[:10], 1):
        items.append(
            f'<a class="activity-rank-card" href="{escape(activity_location_url(location, "surfing"))}">'
            f'<span class="rank-number">#{index}</span><div><h3>{escape(location["name"])}</h3>'
            f'<p>{escape(location["state_code"])} · {escape(_fmt_window(day))} · {escape(day.get("confidence") or "")}</p></div>'
            f'<strong>{float(day["score"]):g}</strong><small>{escape(day.get("rating") or "")}</small></a>'
        )
    return '<div class="activity-ranking-list">' + "".join(items) + '</div>'


def _hub_number_one(rows: list[tuple[dict, dict]]) -> str:
    if not rows:
        return '<div class="activity-panel"><h2>Why #1 today</h2><p>No pilot location currently qualifies for the primary numerical ranking.</p></div>'
    location, _ = rows[0]
    return (
        '<div class="activity-number-one-card"><p class="eyebrow">WHY #1 TODAY</p><h2>Why #1 today</h2>'
        f'<h3>{escape(location["name"])}, {escape(location["state_code"])}</h3>'
        '<p>This location has the highest qualifying Surf Conditions Score among the current pilot locations.</p>'
        f'<a href="{escape(activity_location_url(location, "surfing"))}">See full surf conditions →</a></div>'
    )


def _hub_group_card(location: dict, day: dict) -> str:
    status = day.get("status") or "Unavailable"
    confidence = day.get("confidence") or "Unavailable"
    score = day.get("score")
    if status == "NOT RECOMMENDED":
        display = "NOT RECOMMENDED"
    elif status in {"Limited", "Unavailable"} or confidence in {"Limited", "Unavailable"}:
        display = "Limited" if "Limited" in {status, confidence} else "Unavailable"
    elif score is None:
        display = status
    else:
        display = f'{float(score):g} {day.get("rating") or ""}'.strip()
    return (
        f'<a class="activity-group-card" href="{escape(activity_location_url(location, "surfing"))}">'
        f'<h3>{escape(location["name"])}</h3><p>{escape(location["state_code"])}</p><strong>{escape(display)}</strong></a>'
    )


def _hub_groups(locations: dict[str, dict], results: dict[str, dict], day_key: str) -> str:
    buckets = {
        "Excellent": [], "Good": [], "Fair": [], "Poor / Unfavorable": [],
        "Not Recommended": [], "Limited / Unavailable": [],
    }
    for slug, result in results.items():
        location = locations.get(slug)
        if not location:
            continue
        day = result.get(day_key) or {}
        status = day.get("status") or "Unavailable"
        confidence = day.get("confidence") or "Unavailable"
        if status == "NOT RECOMMENDED":
            key = "Not Recommended"
        elif status in {"Limited", "Unavailable"} or confidence in {"Limited", "Unavailable"}:
            key = "Limited / Unavailable"
        elif day.get("rating") in {"Excellent", "Good", "Fair"}:
            key = day["rating"]
        else:
            key = "Poor / Unfavorable"
        buckets[key].append((location, day))
    sections = []
    for label, rows in buckets.items():
        if not rows:
            continue
        rows.sort(key=lambda item: (999 if item[1].get("score") is None else -float(item[1]["score"]), item[0]["name"].casefold()))
        sections.append(
            f'<section class="activity-status-group"><div class="section-head"><h3>{escape(label)}</h3><p>{len(rows)} location(s)</p></div>'
            '<div class="activity-group-grid">' + "".join(_hub_group_card(location, day) for location, day in rows) + '</div></section>'
        )
    return "".join(sections) or '<div class="activity-empty">No Surfing pilot results are available.</div>'


def render_surfing_hub(locations: dict[str, dict], results: dict[str, dict], *, day_key: str = "today", head_extra: str = "") -> str:
    if day_key not in {"today", "tomorrow"}:
        raise ValueError("day_key must be today or tomorrow")
    template = HUB_TEMPLATE.read_text(encoding="utf-8")
    template = template.replace("<span>/</span>Fishing", "<span>/</span>Surfing")
    template = template.replace("Best Fishing Conditions in the U.S. Today", "Surf Conditions Across U.S. Pilot Locations")
    template = template.replace(
        "Compare shore, pier and nearshore recreational fishing conditions across CoastalNow locations.",
        "Compare general coastal surf planning conditions across the current CoastalNow pilot locations. Conditions are not break-specific.",
    )
    template = template.replace("Best Fishing Windows", "Surf Planning Windows")
    template = template.replace(
        "Fishing Scores are 0–100 composite planning scores, not measured environmental values such as water temperature, wave height, or wind speed. Scores compare planning conditions, not personal safety or the chance of catching fish. Official warnings, closures, signs and local guidance always take priority.",
        "Surf Conditions Scores are 0–100 composite planning scores, not measured environmental values. They are not a safety guarantee and are not break-specific forecasts. Official warnings, closures, signs and local guidance always take priority.",
    )
    ranked = _ranking(locations, results, day_key)
    day_switch = (
        '<div class="activity-hub-day-switch" role="group" aria-label="Surfing outlook day">'
        f'<span class="{"active" if day_key == "today" else ""}">Today</span>'
        f'<span class="{"active" if day_key == "tomorrow" else ""}">Tomorrow</span></div>'
    )
    return _fill(template, {
        "TITLE": "Surf Conditions Across U.S. Pilot Locations | CoastalNow",
        "DESCRIPTION": "Compare Surf Conditions Scores and wave, wind, weather and tide context across CoastalNow Surfing pilot locations.",
        "HEAD_EXTRA": head_extra,
        "LOGO": LOGO,
        "RANKED_COUNT": str(len(ranked)),
        "DAY_SWITCH": day_switch,
        "TOP_LOCATIONS": _hub_top_cards(ranked),
        "NUMBER_ONE": _hub_number_one(ranked),
        "GROUPS": _hub_groups(locations, results, day_key),
    })
