"""A useful, source-grounded seven-day tide comparison for live Tide pages.

This is an interpretation of existing NOAA high/low predictions, not another
forecast source and not a safety or current-speed assessment.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from html import escape
import math


def _time_label(raw: str) -> str:
    local_time = datetime.strptime(raw, "%Y-%m-%d %H:%M")
    return local_time.strftime("%I:%M %p").lstrip("0")


def _date_label(raw: str) -> str:
    local_date = date.fromisoformat(raw)
    return local_date.strftime("%a, %b ") + str(local_date.day)


def render_weekly_tide_comparison(data: dict | None) -> str:
    """Render only verified NOAA live predictions with at least two usable days."""
    if not isinstance(data, dict):
        return ""
    if data.get("mode") != "live" or data.get("source") != "NOAA/NOS/CO-OPS":
        return ""
    if data.get("units") != "feet":
        return ""
    window = data.get("range")
    if not isinstance(window, dict):
        return ""
    try:
        start = date.fromisoformat(window["start"])
        end = date.fromisoformat(window["end"])
    except (KeyError, TypeError, ValueError):
        return ""
    if end < start or (end - start).days > 6:
        return ""

    events_by_day: dict[str, dict[str, list[tuple[float, str]]]] = defaultdict(
        lambda: {"H": [], "L": []}
    )
    for event in data.get("hilo") or []:
        if not isinstance(event, dict) or event.get("type") not in {"H", "L"}:
            continue
        stamp = event.get("t")
        try:
            if not isinstance(stamp, str):
                continue
            parsed = datetime.strptime(stamp, "%Y-%m-%d %H:%M")
            if not start <= parsed.date() <= end:
                continue
            height = float(event["v"])
            if not math.isfinite(height):
                continue
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        events_by_day[parsed.date().isoformat()][event["type"]].append((height, stamp))

    days = []
    for day in sorted(events_by_day):
        events = events_by_day[day]
        if not events["H"] or not events["L"]:
            continue
        high = max(events["H"], key=lambda item: item[0])
        low = min(events["L"], key=lambda item: item[0])
        spread = high[0] - low[0]
        if spread < 0:
            continue
        days.append({"date": day, "high": high, "low": low, "spread": spread})
    if len(days) < 2:
        return ""

    widest = max(days, key=lambda row: row["spread"])
    narrowest = min(days, key=lambda row: row["spread"])
    scale = max(row["spread"] for row in days)
    bars = []
    for row in days:
        day_label = escape(_date_label(row["date"]))
        width = 100.0 * row["spread"] / scale if scale > 0 else 0.0
        bars.append(
            '<li class="c2-weekly-row">'
            f'<span class="c2-weekly-day">{day_label}</span>'
            '<span class="c2-weekly-track" aria-hidden="true">'
            f'<span class="c2-weekly-fill" style="width:{width:.1f}%"></span></span>'
            f'<strong class="c2-weekly-value">{row["spread"]:.1f} ft</strong>'
            '</li>'
        )

    peak_summary = (
        f'The largest predicted daily high-to-low difference is '
        f'<strong>{widest["spread"]:.1f} ft on {escape(_date_label(widest["date"]))}</strong>: '
        f'a high of {widest["high"][0]:.1f} ft at {_time_label(widest["high"][1])} '
        f'and a low of {widest["low"][0]:.1f} ft at {_time_label(widest["low"][1])}.'
    )
    contrast = (
        f'The smallest daily difference is {narrowest["spread"]:.1f} ft '
        f'on {escape(_date_label(narrowest["date"]))}.'
    )
    return (
        '<!-- WEEKLY_TIDE_COMPARE_START -->'
        '<section class="section c2-weekly-compare" aria-labelledby="weekly-tide-compare-title">'
        '<div class="section-head"><div><p class="eyebrow">COMPARE THE WEEK</p>'
        '<h2 id="weekly-tide-compare-title">Daily high-to-low tide differences</h2></div>'
        '<p>Compare the predicted spread for each local date</p></div>'
        '<div class="info-card c2-weekly-card">'
        f'<p class="c2-weekly-lead">{peak_summary} {contrast}</p>'
        f'<ol class="c2-weekly-bars" aria-label="Predicted daily high-to-low differences">{"".join(bars)}</ol>'
        '<p class="c2-weekly-note">Calculated from the highest predicted high and lowest '
        'predicted low on each date in the NOAA CO-OPS seven-day tide data. Those '
        'events may not be consecutive. Differences do not indicate current '
        'speed, surf conditions, flooding risk, or safe access. Predictions are '
        'not observations and local conditions may differ.</p>'
        '</div></section>'
        '<!-- WEEKLY_TIDE_COMPARE_END -->'
    )
