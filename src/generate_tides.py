#!/usr/bin/env python3
"""Generate CoastalNow tide pages from shared code and location configuration.

Production (all configured locations):
    python3 src/generate_tides.py

One location:
    python3 src/generate_tides.py --location san-diego

Offline layout preview:
    python3 src/generate_tides.py --location san-diego --preview

The production path never invents NOAA high/low values. Harmonic stations use
NOAA interval predictions directly. Subordinate stations derive a smooth curve
between official NOAA high/low predictions and label that curve as estimated.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from html import escape
from activities.registry import enabled_activities
from activities.rendering.links import activity_location_url
from locations import LOCATIONS

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PUBLIC = ROOT / "public"
TEMPLATE = SRC / "templates" / "tide-page.html"
PREVIEW_DIR = ROOT / "preview"
API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def location_tz(location: dict) -> ZoneInfo:
    return ZoneInfo(location["timezone"])


def page_file(location: dict) -> Path:
    return PUBLIC / location["page_path"]


def data_file(location: dict) -> Path:
    return PUBLIC / location["data_path"]


def preview_file(location: dict) -> Path:
    return PREVIEW_DIR / f'{location["slug"]}-integrated-preview.html'


def api_get(location: dict, params: dict, retries: int = 3) -> dict:
    query = dict(params)
    query.setdefault("station", location["station"])
    query.setdefault("datum", location.get("datum", "MLLW"))
    query.setdefault("time_zone", "lst_ldt")
    query.setdefault("units", location.get("units", "english"))
    query.setdefault("application", "CoastalNow")
    query.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": "CoastalNow/0.3 tide renderer"})
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if "error" in payload:
                raise RuntimeError(f"NOAA API error: {payload['error']}")
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"NOAA request failed after {retries} attempts: {last_error}")


def parse_noaa_dt(value: str, tz: ZoneInfo) -> datetime:
    # NOAA lst_ldt timestamps are station-local wall-clock time.
    return datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=tz)


def data_tz(data: dict) -> ZoneInfo:
    return ZoneInfo(data["station"]["timezone"])


def validate_hilo(items: list[dict], start: date, end: date, tz: ZoneInfo) -> list[dict]:
    if not items:
        raise ValueError("NOAA high/low prediction response was empty")
    out = []
    for raw in items:
        if raw.get("type") not in {"H", "L"}:
            raise ValueError(f"Unexpected tide event type: {raw!r}")
        dt = parse_noaa_dt(raw["t"], tz)
        value = float(raw["v"])
        if not math.isfinite(value) or not -20 <= value <= 30:
            raise ValueError(f"Implausible tide value: {raw!r}")
        if not start <= dt.date() <= end:
            raise ValueError(f"Tide event outside requested range: {raw!r}")
        out.append({"t": raw["t"], "v": round(value, 3), "type": raw["type"]})
    if {e["type"] for e in out} != {"H", "L"}:
        raise ValueError("Prediction range did not contain both high and low tides")
    return sorted(out, key=lambda x: x["t"])


def validate_curve(items: list[dict], start: date, end: date, tz: ZoneInfo) -> list[dict]:
    if not items:
        raise ValueError("NOAA interval prediction response was empty")
    out = []
    for raw in items:
        dt = parse_noaa_dt(raw["t"], tz)
        if not start <= dt.date() <= end:
            continue
        value = float(raw["v"])
        if math.isfinite(value) and -20 <= value <= 30:
            out.append({"t": raw["t"], "v": round(value, 3)})
    # 30-minute data should have roughly 48 points/day. Leave room for DST days.
    if len(out) < 70:
        raise ValueError(f"Too few valid interval predictions: {len(out)}")
    return sorted(out, key=lambda x: x["t"])


def derive_curve_from_hilo(
    hilo: list[dict],
    start: date,
    end: date,
    tz: ZoneInfo,
    interval_minutes: int = 30,
) -> list[dict]:
    """Build a smooth half-cosine curve between official NOAA high/low events.

    The input must include a turning point before the requested window and one
    after it so every output point is bracketed by official high/low events.
    No high/low time or height is changed; only the values between events are
    estimated for display and tide-direction calculations.
    """
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")
    control = []
    for event in hilo:
        if event.get("type") not in {"H", "L"}:
            continue
        dt = parse_noaa_dt(event["t"], tz)
        value = float(event["v"])
        if math.isfinite(value):
            control.append((dt, value))
    control.sort(key=lambda item: item[0])
    if len(control) < 2:
        raise ValueError("At least two high/low events are required to derive a curve")

    window_start = datetime.combine(start, datetime.min.time(), tzinfo=tz)
    window_end = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    if control[0][0] > window_start or control[-1][0] < window_end:
        raise ValueError("High/low context does not bracket the requested curve window")

    curve = []
    index = 0
    t = window_start
    while t < window_end:
        while index + 1 < len(control) and control[index + 1][0] < t:
            index += 1
        if index + 1 >= len(control):
            raise ValueError("High/low context ended before the requested curve window")
        t0, v0 = control[index]
        t1, v1 = control[index + 1]
        if not (t0 <= t <= t1):
            raise ValueError("High/low context contains a gap around the requested curve point")
        span = (t1 - t0).total_seconds()
        if span <= 0:
            raise ValueError("High/low events must be strictly increasing")
        frac = (t - t0).total_seconds() / span
        smooth = (1 - math.cos(math.pi * frac)) / 2
        value = v0 + (v1 - v0) * smooth
        curve.append({"t": t.strftime("%Y-%m-%d %H:%M"), "v": round(value, 3)})
        t += timedelta(minutes=interval_minutes)
    return curve


def fetch_live(location: dict) -> dict:
    tz = location_tz(location)
    now = datetime.now(tz)
    start = now.date()
    display_end = start + timedelta(days=6)
    context_end = start + timedelta(days=7)
    curve_end = start + timedelta(days=1)
    prediction_mode = location.get("prediction_mode", "harmonic")
    hilo_start = start - timedelta(days=1) if prediction_mode == "hilo-derived" else start

    hilo_payload = api_get(location, {
        "begin_date": hilo_start.strftime("%Y%m%d"),
        "end_date": context_end.strftime("%Y%m%d"),
        "product": "predictions",
        "interval": "hilo",
    })
    hilo = validate_hilo(hilo_payload.get("predictions", []), hilo_start, context_end, tz)

    if prediction_mode == "hilo-derived":
        curve = derive_curve_from_hilo(hilo, start, curve_end, tz)
        curve_source = "derived_from_noaa_hilo"
    else:
        curve_payload = api_get(location, {
            "begin_date": start.strftime("%Y%m%d"),
            "end_date": curve_end.strftime("%Y%m%d"),
            "product": "predictions",
            "interval": "30",
        })
        curve = validate_curve(curve_payload.get("predictions", []), start, curve_end, tz)
        curve_source = "noaa_interval"

    return {
        "schema_version": 3,
        "mode": "live",
        "source": "NOAA/NOS/CO-OPS",
        "station": {
            "id": location["station"],
            "name": location["station_name"],
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "timezone": location["timezone"],
        },
        "datum": location.get("datum", "MLLW"),
        "units": "feet" if location.get("units", "english") == "english" else "metric",
        "time_zone_mode": "LST/LDT",
        "prediction_mode": prediction_mode,
        "curve_source": curve_source,
        "range": {"start": start.isoformat(), "end": display_end.isoformat()},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_at_local": now.isoformat(timespec="seconds"),
        "hilo": hilo,
        "curve": curve,
    }


def atomic_json_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_cache(location: dict) -> dict | None:
    path = data_file(location)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def cache_is_usable(cache: dict | None, today: date, tz: ZoneInfo) -> bool:
    if not cache or cache.get("mode") != "live":
        return False
    try:
        start = date.fromisoformat(cache["range"]["start"])
        end = date.fromisoformat(cache["range"]["end"])
        generated = datetime.fromisoformat(cache["generated_at_local"])
        age = datetime.now(tz) - generated
        return start <= today <= end and age.total_seconds() <= 30 * 3600
    except Exception:
        return False


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def fmt_height(value: float) -> str:
    s = f"{abs(value):.1f} ft"
    return ("−" + s) if value < 0 else s


def countdown(target: datetime, now: datetime, kind: str) -> str:
    seconds = max(0, int((target - now).total_seconds()))
    minutes = seconds // 60
    days, rem = divmod(minutes, 1440)
    hours, mins = divmod(rem, 60)
    if days:
        span = f"{days}d {hours}h"
    elif hours:
        span = f"{hours}h {mins}m"
    else:
        span = f"{mins}m"
    return f"{kind} tide in {span}"


def grouped_hilo(data: dict) -> dict:
    tz = data_tz(data)
    grouped = defaultdict(lambda: {"H": [], "L": [], "all": []})
    for event in data.get("hilo", []):
        dt = parse_noaa_dt(event["t"], tz)
        grouped[dt.date()][event["type"]].append(event)
        grouped[dt.date()]["all"].append(event)
    for day in grouped:
        grouped[day]["all"].sort(key=lambda x: x["t"])
    return grouped


def next_event(data: dict, tide_type: str, now: datetime):
    tz = data_tz(data)
    events = []
    for event in data.get("hilo", []):
        if event["type"] != tide_type:
            continue
        dt = parse_noaa_dt(event["t"], tz)
        if dt >= now:
            events.append((dt, event))
    return min(events, key=lambda x: x[0]) if events else None


def tide_direction(data: dict, now: datetime) -> str | None:
    tz = data_tz(data)
    points = [(parse_noaa_dt(x["t"], tz), float(x["v"])) for x in data.get("curve", [])]
    if len(points) < 2:
        return None
    before = None
    after = None
    for point in points:
        if point[0] <= now:
            before = point
        if point[0] > now:
            after = point
            break
    if not before or not after:
        return None
    delta = after[1] - before[1]
    if delta > 0.01:
        return "Tide is rising now ↑"
    if delta < -0.01:
        return "Tide is falling now ↓"
    return "Tide is near a turning point ↔"


def render_tide_cards(data: dict, now: datetime) -> str:
    high = next_event(data, "H", now)
    low = next_event(data, "L", now)

    def card(event, kind: str, arrow: str, css: str) -> str:
        if not event:
            return f'''<article class="tide-card {css}"><div class="label"><span class="arrow-icon">{arrow}</span>Next {kind.lower()} tide</div><div class="tide-time">—</div><div class="tide-height">Unavailable</div></article>'''
        dt, raw = event
        return f'''<article class="tide-card {css}">
        <div class="label"><span class="arrow-icon">{arrow}</span>Next {kind.lower()} tide</div>
        <div class="tide-time">{fmt_time(dt)}</div>
        <div class="tide-height">{fmt_height(float(raw['v']))}</div>
        <div class="tide-meta">{countdown(dt, now, kind)}</div>
        <svg class="card-wave" viewBox="0 0 250 95" aria-hidden="true"><path d="M0 55 C40 20 72 80 116 48 S195 23 250 58"/><path d="M0 72 C40 38 72 94 116 67 S195 42 250 75" opacity=".55"/></svg>
      </article>'''

    return '<div class="tide-grid">' + card(high, "High", "↑", "high") + card(low, "Low", "↓", "low") + '</div>'


def render_status(data: dict, now: datetime) -> str:
    status = tide_direction(data, now)
    if not status:
        return '<div class="status-strip"><span class="status-dot"></span><strong>Current tide direction unavailable</strong></div>'
    return f'<div class="status-strip"><span class="status-dot"></span><strong>{status}</strong></div>'


def today_curve(data: dict, today: date) -> list[dict]:
    tz = data_tz(data)
    return [x for x in data.get("curve", []) if parse_noaa_dt(x["t"], tz).date() == today]


def render_chart_and_events(location: dict, data: dict, today: date) -> str:
    tz = data_tz(data)
    curve = today_curve(data, today)
    grouped = grouped_hilo(data)
    events = grouped[today]["all"]
    if len(curve) < 2:
        return '<div class="unavailable-card">Today’s NOAA prediction curve is unavailable.</div>'

    values = [float(x["v"]) for x in curve]
    lo, hi = min(values), max(values)
    padding = max((hi - lo) * 0.12, 0.2)
    ymin, ymax = lo - padding, hi + padding
    span = max(ymax - ymin, 0.1)
    left, right, top, bottom = 55, 878, 42, 270

    def xy(dt: datetime, value: float):
        minutes = dt.hour * 60 + dt.minute
        x = left + (right - left) * minutes / 1440
        y = bottom - (value - ymin) / span * (bottom - top)
        return x, y

    points = []
    for item in curve:
        dt = parse_noaa_dt(item["t"], tz)
        points.append(xy(dt, float(item["v"])))
    line_path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))
    area_path = line_path + f" L{points[-1][0]:.1f},{bottom} L{points[0][0]:.1f},{bottom} Z"

    marker_html = []
    for event in events:
        dt = parse_noaa_dt(event["t"], tz)
        value = float(event["v"])
        x, y = xy(dt, value)
        css = "dot-high" if event["type"] == "H" else "dot-low"
        kind = "High" if event["type"] == "H" else "Low"
        label_y = y - 15 if event["type"] == "H" else min(y + 28, 300)
        label_x = max(60, min(x - 42, 805))
        marker_html.append(f'<circle class="{css}" cx="{x:.1f}" cy="{y:.1f}" r="8"/><text class="point-label" x="{label_x:.1f}" y="{label_y:.1f}">{fmt_time(dt)} · {kind}</text>')

    grid = ''.join([
        f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>',
        f'<line class="axis" x1="{left}" y1="194" x2="{right}" y2="194"/>',
        f'<line class="axis" x1="{left}" y1="118" x2="{right}" y2="118"/>',
    ])
    svg = f'''<svg class="chart" viewBox="0 0 920 330" role="img" aria-label="Tide curve for {location['name']} today">
      <defs><linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#65c1c7" stop-opacity=".32"/><stop offset="100%" stop-color="#65c1c7" stop-opacity=".03"/></linearGradient></defs>
      {grid}<path class="area" d="{area_path}"/><path class="line" d="{line_path}"/>{''.join(marker_html)}
      <text class="axis-label" x="55" y="315">12 AM</text><text class="axis-label" x="256" y="315">6 AM</text><text class="axis-label" x="453" y="315">12 PM</text><text class="axis-label" x="653" y="315">6 PM</text><text class="axis-label" x="842" y="315">12 AM</text>
    </svg>'''

    event_cards = []
    for event in events:
        dt = parse_noaa_dt(event["t"], tz)
        kind = "High" if event["type"] == "H" else "Low"
        event_cards.append(f'<div class="event"><span>{kind}</span><strong>{fmt_time(dt)}</strong><small>{fmt_height(float(event["v"]))}</small></div>')
    note = ""
    if data.get("curve_source") == "derived_from_noaa_hilo":
        note = '<p style="margin:12px 4px 0;color:#73878f;font-size:.78rem">Tide curve is estimated between official NOAA high and low predictions.</p>'
    return svg + '<div class="tide-list">' + ''.join(event_cards) + '</div>' + note


def next_same_type_event(data: dict, day: date, tide_type: str):
    tz = data_tz(data)
    candidates = []
    for event in data.get("hilo", []):
        if event["type"] != tide_type:
            continue
        dt = parse_noaa_dt(event["t"], tz)
        if dt.date() > day:
            candidates.append((dt, event))
    return min(candidates, key=lambda x: x[0]) if candidates else None


def next_tide_note(data: dict, day: date, tide_type: str) -> str:
    grouped = grouped_hilo(data)
    if len(grouped[day][tide_type]) != 1:
        return ""
    nxt = next_same_type_event(data, day, tide_type)
    if not nxt:
        return ""
    dt, _ = nxt
    arrow = "↑" if tide_type == "H" else "↓"
    return f'<span class="next-tide-note">Next {arrow} {fmt_time(dt)} {dt.strftime("%a")}</span>'


def desktop_forecast_rows(data: dict, start: date) -> str:
    tz = data_tz(data)
    grouped = grouped_hilo(data)
    rows = []
    for i in range(7):
        day = start + timedelta(days=i)
        day_label = day.strftime("%a %d")
        sub = "Today" if i == 0 else ("Tomorrow" if i == 1 else day.strftime("%A"))
        highs = ''.join(f'<span class="pill-event">↑ {fmt_time(parse_noaa_dt(e["t"], tz))} · {fmt_height(float(e["v"]))}</span>' for e in grouped[day]["H"]) or '—'
        lows = ''.join(f'<span class="pill-event low">↓ {fmt_time(parse_noaa_dt(e["t"], tz))} · {fmt_height(float(e["v"]))}</span>' for e in grouped[day]["L"]) or '—'
        highs += next_tide_note(data, day, "H")
        lows += next_tide_note(data, day, "L")
        rows.append(f'<tr><td class="day"><strong>{day_label}</strong><span>{sub}</span></td><td>{highs}</td><td>{lows}</td></tr>')
    return ''.join(rows)


def mobile_day(data: dict, day: date, events: list[dict], label: str) -> str:
    tz = data_tz(data)
    cells = []
    for event in events:
        kind = "High" if event["type"] == "H" else "Low"
        arrow = "↑" if event["type"] == "H" else "↓"
        cells.append(f'<div class="mobile-event">{arrow} {kind} · {fmt_time(parse_noaa_dt(event["t"], tz))} · {fmt_height(float(event["v"]))}</div>')
    grouped = grouped_hilo(data)
    for tide_type, kind in (("H", "High"), ("L", "Low")):
        if len(grouped[day][tide_type]) == 1:
            nxt = next_same_type_event(data, day, tide_type)
            if nxt:
                dt, _ = nxt
                cells.append(f'<div class="mobile-event next-note">Next {kind} · {fmt_time(dt)} {dt.strftime("%a")}</div>')
    if not cells:
        cells.append('<div class="mobile-event">No tide events available</div>')
    day_text = day.strftime("%a, %b") + f" {day.day}"
    return f'<article class="mobile-day"><div class="mobile-day-head"><strong>{day_text}</strong><span>{label}</span></div><div class="mobile-events">{"".join(cells)}</div></article>'


def mobile_forecast(data: dict, start: date) -> str:
    grouped = grouped_hilo(data)
    days = []
    for i in range(7):
        day = start + timedelta(days=i)
        label = "Today" if i == 0 else ("Tomorrow" if i == 1 else day.strftime("%A"))
        days.append(mobile_day(data, day, grouped[day]["all"], label))
    return f'<div class="mobile-days">{"".join(days[:3])}<div id="moreForecast" class="more-forecast" hidden>{"".join(days[3:])}</div><button class="forecast-toggle" id="forecastToggle" type="button" aria-expanded="false" aria-controls="moreForecast">Show all 7 days</button></div>'


def data_notice(mode: str, message: str = "") -> str:
    if mode == "live":
        return ""
    if mode == "preview":
        return '<div class="wrap"><div class="data-notice stale"><strong>Technical preview:</strong> mock values are used only to test the live-data layout.</div></div>'
    if mode == "stale":
        return '<div class="wrap"><div class="data-notice stale"><strong>Latest refresh delayed.</strong> Showing the most recent same-day verified NOAA cache.</div></div>'
    return f'<div class="wrap"><div class="data-notice error"><strong>NOAA data temporarily unavailable.</strong> {message}</div></div>'


def unavailable_fragments(now: datetime, message: str) -> dict:
    return {
        "DATA_NOTICE": data_notice("error", message),
        "HERO_DATE": now.strftime("%A, %B %d").replace(" 0", " "),
        "UPDATED_TEXT": "Live NOAA refresh pending",
        "TIDE_CARDS": '<div class="tide-grid"><div class="unavailable-card">Next high tide unavailable.</div><div class="unavailable-card">Next low tide unavailable.</div></div>',
        "STATUS_STRIP": '<div class="status-strip"><span class="status-dot"></span><strong>Current tide direction unavailable</strong></div>',
        "CHART_AND_EVENTS": '<div class="unavailable-card">Today’s NOAA tide curve is temporarily unavailable.</div>',
        "DESKTOP_FORECAST_ROWS": '<tr><td colspan="3">7-day NOAA forecast temporarily unavailable.</td></tr>',
        "MOBILE_FORECAST": '<div class="mobile-days"><div class="unavailable-card">7-day NOAA forecast temporarily unavailable.</div></div>',
    }


def nearby_links(location: dict) -> str:
    return ''.join(
        f'<a class="place" href="../{item["slug"]}/index.html">{item["name"]}</a>'
        for item in location.get("nearby", [])
    )


def primary_activity_cta(location: dict) -> str:
    configured = {item["slug"]: item for item in enabled_activities()}
    if "fishing" not in configured:
        return ""
    href = escape(activity_location_url(location, "fishing"))
    location_name = escape(location["name"])
    return (
        '<!-- ACTIVITY_PRIMARY_START -->'
        '<section class="section activity-primary-section">'
        f'<a class="activity-primary-cta" href="{href}"><div class="info-card">'
        '<p class="eyebrow">FISHING</p>'
        f'<h2>Fishing conditions for {location_name}</h2>'
        '<p>See tide, wind, wave and weather context for shore, pier and nearshore fishing.</p>'
        '<p><strong>View fishing conditions →</strong></p>'
        '</div></a></section>'
        '<!-- ACTIVITY_PRIMARY_END -->'
    )


def static_replacements(location: dict) -> dict:
    return {
        "PAGE_TITLE": location["page_title"],
        "META_DESCRIPTION": location["meta_description"],
        "STATE_NAME": location["state"],
        "STATE_UPPER": location["state"].upper(),
        "LOCATION_NAME": location["name"],
        "LOCATION_UPPER": location["name"].upper(),
        "HERO_COPY": location["hero_copy"],
        "ACTIVITY_PRIMARY_CTA": primary_activity_cta(location),
        "TIME_LABEL": location["time_label"],
        "LOCAL_GUIDE": location["local_guide"],
        "NEARBY_LINKS": nearby_links(location),
        "STATION_ID": location["station"],
        "DATUM": location.get("datum", "MLLW"),
        "UNITS_LABEL": location.get("units_label", "Feet"),
    }


def render_location(location: dict, data: dict | None, output: Path, mode: str, now: datetime | None = None, error_message: str = "") -> None:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    tz = location_tz(location)
    now = now or datetime.now(tz)
    replacements = static_replacements(location)
    if data is None:
        replacements.update(unavailable_fragments(now, error_message))
    else:
        start = date.fromisoformat(data["range"]["start"])
        generated = datetime.fromisoformat(data["generated_at_local"])
        replacements.update({
            "DATA_NOTICE": data_notice(mode),
            "HERO_DATE": start.strftime("%A, %B %d").replace(" 0", " "),
            "UPDATED_TEXT": f"Updated {fmt_time(generated)} {generated.tzname() or 'local time'}",
            "TIDE_CARDS": render_tide_cards(data, now),
            "STATUS_STRIP": render_status(data, now),
            "CHART_AND_EVENTS": render_chart_and_events(location, data, start),
            "DESKTOP_FORECAST_ROWS": desktop_forecast_rows(data, start),
            "MOBILE_FORECAST": mobile_forecast(data, start),
        })
    for key, value in replacements.items():
        tpl = tpl.replace("{{" + key + "}}", value)
    if "{{" in tpl or "}}" in tpl:
        raise RuntimeError("Unreplaced template token remains in tide-page.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(tpl, encoding="utf-8")


def build_preview(location: dict, start: date | None = None) -> tuple[dict, datetime]:
    tz = location_tz(location)
    start = start or date(2026, 8, 26)
    preview_now = datetime.combine(start, datetime.min.time(), tzinfo=tz).replace(hour=6, minute=55)
    daily = [
        [(2,53,-1.1,'L'),(9,13,3.9,'H'),(13,52,2.0,'L'),(20,18,7.2,'H')],
        [(3,20,-0.8,'L'),(9,42,4.1,'H'),(14,31,1.8,'L'),(20,44,6.9,'H')],
        [(3,48,-0.5,'L'),(10,10,4.3,'H'),(15,10,1.7,'L'),(21,9,6.5,'H')],
        [(4,16,-0.1,'L'),(10,40,4.4,'H'),(15,51,1.5,'L'),(21,35,6.1,'H')],
        [(4,46,0.3,'L'),(11,12,4.5,'H'),(16,35,1.4,'L'),(22,3,5.7,'H')],
        [(5,18,0.7,'L'),(11,46,4.6,'H'),(17,23,1.3,'L'),(22,34,5.3,'H')],
        [(5,53,1.0,'L'),(12,23,4.7,'H'),(18,17,1.2,'L')],
        [(0,59,3.8,'H'),(6,2,2.0,'L'),(12,52,5.8,'H'),(20,21,1.1,'L')],
    ]
    hilo = []
    for i, events in enumerate(daily):
        day = start + timedelta(days=i)
        for hour, minute, value, typ in events:
            hilo.append({"t": f"{day.isoformat()} {hour:02d}:{minute:02d}", "v": value, "type": typ})

    control = [(datetime.combine(start, datetime.min.time(), tzinfo=tz), 0.0)]
    for event in hilo:
        dt = parse_noaa_dt(event["t"], tz)
        if dt.date() <= start + timedelta(days=1):
            control.append((dt, float(event["v"])))
    control.append((datetime.combine(start + timedelta(days=2), datetime.min.time(), tzinfo=tz), 1.0))
    control.sort()
    curve = []
    t = datetime.combine(start, datetime.min.time(), tzinfo=tz)
    end = datetime.combine(start + timedelta(days=1), datetime.min.time(), tzinfo=tz).replace(hour=23, minute=30)
    while t <= end:
        value = control[-1][1]
        for j in range(len(control) - 1):
            t0, v0 = control[j]
            t1, v1 = control[j + 1]
            if t0 <= t <= t1:
                frac = (t - t0).total_seconds() / max((t1 - t0).total_seconds(), 1)
                smooth = (1 - math.cos(math.pi * frac)) / 2
                value = v0 + (v1 - v0) * smooth
                break
        curve.append({"t": t.strftime("%Y-%m-%d %H:%M"), "v": round(value, 3)})
        t += timedelta(minutes=30)

    return ({
        "schema_version": 3,
        "mode": "preview",
        "source": "SYNTHETIC PREVIEW",
        "station": {
            "id": location["station"],
            "name": location["station_name"],
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "timezone": location["timezone"],
        },
        "datum": location.get("datum", "MLLW"),
        "units": "feet",
        "time_zone_mode": "LST/LDT",
        "range": {"start": start.isoformat(), "end": (start + timedelta(days=6)).isoformat()},
        "generated_at_local": preview_now.isoformat(timespec="seconds"),
        "generated_at_utc": preview_now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "hilo": hilo,
        "curve": curve,
    }, preview_now)


def generate_one(location: dict, preview: bool = False) -> int:
    tz = location_tz(location)
    if preview:
        data, preview_now = build_preview(location)
        output = preview_file(location)
        render_location(location, data, output, mode="preview", now=preview_now)
        print(f"Preview rendered: {output}")
        return 0

    now = datetime.now(tz)
    cache = load_cache(location)
    try:
        live = fetch_live(location)
        atomic_json_write(data_file(location), live)
        render_location(location, live, page_file(location), mode="live", now=now)
        print(f"[{location['slug']}] NOAA cache updated: {data_file(location)}")
        print(f"[{location['slug']}] Production page rendered: {page_file(location)}")
        return 0
    except Exception as exc:
        print(f"WARNING [{location['slug']}]: NOAA refresh failed: {exc}", file=sys.stderr)
        if cache_is_usable(cache, now.date(), tz):
            render_location(location, cache, page_file(location), mode="stale", now=now)
            print(f"[{location['slug']}] Rendered same-day verified cache.")
        else:
            render_location(
                location,
                None,
                page_file(location),
                mode="error",
                now=now,
                error_message="No current verified cache is available; tide values are intentionally withheld.",
            )
            print(f"[{location['slug']}] Rendered explicit unavailable state; no tide values were invented.")
        return 2


def selected_locations(slug: str | None) -> list[dict]:
    if slug:
        if slug not in LOCATIONS:
            raise KeyError(f"Unknown location: {slug}")
        return [LOCATIONS[slug]]
    return [location for location in LOCATIONS.values() if location.get("status") == "Live NOAA"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="render offline mock-data integration previews")
    parser.add_argument("--location", choices=sorted(LOCATIONS), help="generate only one configured location")
    args = parser.parse_args()

    exit_code = 0
    for location in selected_locations(args.location):
        exit_code = max(exit_code, generate_one(location, preview=args.preview))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
