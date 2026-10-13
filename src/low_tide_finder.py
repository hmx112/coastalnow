"""Five-location low-tide finder using already verified NOAA prediction events.

This module only reorders and groups the NOAA high/low series already shown on
the Tide page. It does not estimate water depth, safety, currents or new tides.
"""
from __future__ import annotations

from datetime import date, datetime
from html import escape
import math


PILOT_LOCATIONS = frozenset({
    "malibu",
    "oceanside",
    "half-moon-bay",
    "corolla",
    "nags-head",
})
ASSET_VERSION = "20261013-pilot-1"


def _local_date(raw: datetime) -> str:
    return raw.strftime("%a, %b ") + str(raw.day)


def _local_time(raw: datetime) -> str:
    return raw.strftime("%I:%M %p").lstrip("0")


def _time_band(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "overnight"


def _valid_window(data: dict, location: dict) -> tuple[date, date] | None:
    if data.get("mode") != "live" or data.get("source") != "NOAA/NOS/CO-OPS":
        return None
    if data.get("units") != "feet" or data.get("time_zone_mode") != "LST/LDT":
        return None
    station = data.get("station")
    if not isinstance(station, dict):
        return None
    if str(station.get("id", "")) != str(location.get("station", "")):
        return None
    if station.get("timezone") != location.get("timezone"):
        return None
    window = data.get("range")
    if not isinstance(window, dict):
        return None
    try:
        start = date.fromisoformat(window["start"])
        end = date.fromisoformat(window["end"])
    except (KeyError, ValueError, TypeError):
        return None
    if not 0 <= (end - start).days <= 6:
        return None
    return start, end


def render_low_tide_finder(data: dict | None, location: dict) -> str:
    """Generate a collapsed, accessible, searchable-by-daypart list of lows.

    No invented values: empty, stale-structure or misattributed predictions
    render no feature at all. All listed heights remain relative to NOAA MLLW.
    """
    if location.get("slug") not in PILOT_LOCATIONS or not isinstance(data, dict):
        return ""
    window = _valid_window(data, location)
    if window is None:
        return ""
    start, end = window
    events = []
    for event in data.get("hilo") or []:
        if not isinstance(event, dict) or event.get("type") != "L":
            continue
        try:
            stamp = datetime.strptime(event["t"], "%Y-%m-%d %H:%M")
            height = float(event["v"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not (start <= stamp.date() <= end) or not math.isfinite(height):
            continue
        events.append((height, stamp))
    if len(events) < 3:
        return ""
    events.sort(key=lambda item: (item[0], item[1]))
    rows = []
    for height, stamp in events:
        band = _time_band(stamp.hour)
        rows.append(
            f'<li class="c2-low-finder-row" data-time-band="{band}">'
            f'<span>{escape(_local_date(stamp))}</span>'
            f'<span>{escape(_local_time(stamp))}</span>'
            f'<strong>{height:.1f} ft</strong></li>'
        )
    timezone_label = escape(location.get("time_label") or "local time")
    return (
        '<!-- LOW_TIDE_FINDER_START -->'
        '<section class="section c2-low-finder" aria-label="Low tide finder">'
        '<details class="c2-low-finder-details">'
        '<summary>Find lower predicted tides in the next 7-day schedule'
        '<span class="c2-low-finder-summary-note">Compare NOAA low-tide events by local time</span>'
        '</summary>'
        '<div class="info-card c2-low-finder-card">'
        '<p>These are NOAA low-tide predictions sorted by lowest water level first, '
        'not by date. Compare dates and times before choosing when to visit. '
        'Earlier events in the current day may already have passed.</p>'
        '<label for="c2-low-finder-daypart">Show low tides by time of day</label>'
        '<select id="c2-low-finder-daypart" class="c2-low-finder-daypart">'
        '<option value="all">Any time</option>'
        '<option value="morning">Morning (6 AM–noon)</option>'
        '<option value="afternoon">Afternoon (noon–6 PM)</option>'
        '<option value="evening">Evening (6–10 PM)</option>'
        '<option value="overnight">Overnight (10 PM–6 AM)</option>'
        '</select>'
        f'<p class="c2-low-finder-zone">Times shown in {timezone_label}</p>'
        '<div class="c2-low-finder-head" aria-hidden="true">'
        '<span>Date</span><span>Low tide time</span><span>Level</span></div>'
        f'<ol class="c2-low-finder-rows">{"".join(rows)}</ol>'
        '<p class="c2-low-finder-status" role="status" aria-live="polite"></p>'
        '<p class="c2-low-finder-warning">Levels are predicted heights relative to '
        'the NOAA station datum (MLLW), not beach water depth. '
        'A low predicted tide does not establish safe access, current speed, '
        'wave conditions, or tide-pool safety. '
        '<a href="/methodology/#reading-tides">Understand tide predictions</a>.</p>'
        '</div></details></section>'
        f'<script defer src="/assets/low-tide-finder.js?v={ASSET_VERSION}"></script>'
        '<!-- LOW_TIDE_FINDER_END -->'
    )
