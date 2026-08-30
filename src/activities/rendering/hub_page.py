"""Render the national Fishing discovery/ranking hub."""
from __future__ import annotations

from html import escape
from pathlib import Path

from activities.explanations import explain_reasons
from activities.rendering.links import activity_location_url
from site_generator import LOGO

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "activity-hub.html"


def _fill(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    if "{{" in out or "}}" in out:
        raise ValueError("Unresolved Activity hub template token")
    return out


def _fmt_window(day: dict) -> str:
    from datetime import datetime
    window = day.get("best_window")
    if not window:
        return "—"
    start = datetime.fromisoformat(window["start"]).strftime("%I:%M %p").lstrip("0")
    end = datetime.fromisoformat(window["end"]).strftime("%I:%M %p").lstrip("0")
    return f"{start}–{end}"


def _ranking(locations: dict[str, dict], results: dict[str, dict], day_key: str) -> list[tuple[dict, dict]]:
    rows = []
    for slug, result in results.items():
        location = locations.get(slug)
        if not location:
            continue
        day = result.get(day_key) or {}
        if (
            day.get("ranking_eligible")
            and day.get("confidence") in {"High", "Medium"}
            and day.get("score") is not None
            and day.get("status") != "NOT RECOMMENDED"
        ):
            rows.append((location, day))
    return sorted(rows, key=lambda item: (-float(item[1]["score"]), item[0]["name"].casefold()))


def _top_cards(rows: list[tuple[dict, dict]]) -> str:
    if not rows:
        return '<div class="activity-empty">No locations currently meet the national ranking requirements.</div>'
    cards = []
    for index, (location, day) in enumerate(rows[:10], 1):
        cards.append(
            f'<a class="activity-rank-card" href="{escape(activity_location_url(location, "fishing"))}">'
            f'<span class="rank-number">#{index}</span><div><h3>{escape(location["name"])}</h3>'
            f'<p>{escape(location["state_code"])} · {_fmt_window(day)} · {escape(day.get("confidence") or "")}</p></div>'
            f'<strong>{float(day["score"]):g}</strong><small>{escape(day.get("rating") or "")}</small></a>'
        )
    return '<div class="activity-ranking-list">' + "".join(cards) + '</div>'


def _number_one(rows: list[tuple[dict, dict]], day_key: str) -> str:
    if not rows:
        return '<div class="activity-panel"><h2>Why #1 today</h2><p>No location currently qualifies for the primary numerical ranking.</p></div>'
    location, day = rows[0]
    why = explain_reasons(day.get("reasons") or []) or "This location has the highest qualifying Fishing Score for the selected day."
    return (
        '<div class="activity-number-one-card"><p class="eyebrow">WHY #1 TODAY</p><h2>Why #1 today</h2>'
        f'<h3>{escape(location["name"])}, {escape(location["state_code"])}</h3><p>{escape(why)}</p>'
        f'<a href="{escape(activity_location_url(location, "fishing"))}">See full fishing conditions →</a></div>'
    )


def _group_card(location: dict, day: dict) -> str:
    score = day.get("score")
    status = day.get("status") or "Unavailable"
    display = status if score is None else f'{float(score):g} {day.get("rating") or ""}'
    return (
        f'<a class="activity-group-card" href="{escape(activity_location_url(location, "fishing"))}">'
        f'<h3>{escape(location["name"])}</h3><p>{escape(location["state_code"])}</p><strong>{escape(display)}</strong></a>'
    )


def _groups(locations: dict[str, dict], results: dict[str, dict], day_key: str) -> str:
    buckets = {
        "Excellent": [],
        "Good": [],
        "Fair": [],
        "Poor / Unfavorable": [],
        "Not Recommended": [],
        "Limited / Unavailable": [],
    }
    for slug, result in results.items():
        location = locations.get(slug)
        if not location:
            continue
        day = result.get(day_key) or {}
        status = day.get("status") or "Unavailable"
        if status == "NOT RECOMMENDED":
            key = "Not Recommended"
        elif day.get("confidence") in {"Limited", "Unavailable"} or status in {"Limited", "Unavailable"}:
            key = "Limited / Unavailable"
        elif day.get("rating") == "Excellent":
            key = "Excellent"
        elif day.get("rating") == "Good":
            key = "Good"
        elif day.get("rating") == "Fair":
            key = "Fair"
        else:
            key = "Poor / Unfavorable"
        buckets[key].append((location, day))

    sections = []
    for label, rows in buckets.items():
        if not rows:
            continue
        rows.sort(key=lambda item: (
            999 if item[1].get("score") is None else -float(item[1]["score"]),
            item[0]["name"].casefold(),
        ))
        sections.append(
            f'<section class="activity-status-group"><div class="section-head"><h3>{escape(label)}</h3><p>{len(rows)} location(s)</p></div>'
            '<div class="activity-group-grid">' + "".join(_group_card(location, day) for location, day in rows) + '</div></section>'
        )
    return "".join(sections) or '<div class="activity-empty">No activity results are available.</div>'


def render_fishing_hub(
    locations: dict[str, dict],
    results: dict[str, dict],
    *,
    day_key: str = "today",
    head_extra: str = "",
) -> str:
    if day_key not in {"today", "tomorrow"}:
        raise ValueError("day_key must be today or tomorrow")
    ranked = _ranking(locations, results, day_key)
    template = TEMPLATE.read_text(encoding="utf-8")
    day_switch = (
        '<div class="activity-hub-day-switch" role="group" aria-label="Fishing outlook day">'
        f'<span class="{"active" if day_key == "today" else ""}">Today</span>'
        f'<span class="{"active" if day_key == "tomorrow" else ""}">Tomorrow</span></div>'
    )
    return _fill(template, {
        "TITLE": "Best Fishing Conditions in the U.S. Today | CoastalNow",
        "DESCRIPTION": "Compare shore, pier and nearshore fishing conditions across U.S. CoastalNow locations using tide, wind, waves, weather and safety context.",
        "HEAD_EXTRA": head_extra,
        "LOGO": LOGO,
        "RANKED_COUNT": str(len(ranked)),
        "DAY_SWITCH": day_switch,
        "TOP_LOCATIONS": _top_cards(ranked),
        "NUMBER_ONE": _number_one(ranked, day_key),
        "GROUPS": _groups(locations, results, day_key),
    })
