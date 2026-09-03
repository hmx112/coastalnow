"""Reusable data-source and methodology attribution for Activity pages."""
from __future__ import annotations

import re
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

ATTRIBUTION_PATTERN = re.compile(
    r"<!-- ACTIVITY_ATTRIBUTION_START -->.*?<!-- ACTIVITY_ATTRIBUTION_END -->",
    re.DOTALL,
)

NOAA_COOPS_URL = "https://tidesandcurrents.noaa.gov/"
NOAA_COOPS_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/"
NWS_API_URL = "https://www.weather.gov/documentation/services-web-api"
METHODOLOGY_URL = "/methodology/"


def _provider_local_time(snapshot: dict, provider_name: str, timezone_name: str) -> str | None:
    provider = (snapshot.get("providers") or {}).get(provider_name) or {}
    value = provider.get("fetched_at_utc")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        local = parsed.astimezone(ZoneInfo(timezone_name))
        return local.strftime("%b %d, %Y %-I:%M %p %Z")
    except Exception:
        return None


def _tide_source_text(location: dict) -> str:
    station_name = str(location.get("station_name") or "NOAA station")
    station_id = str(location.get("station") or "").strip()
    station = station_name + (f" ({station_id})" if station_id else "")
    if location.get("coverage_mode") == "nearby-noaa":
        distance = location.get("coverage_distance_miles")
        distance_text = f", about {float(distance):g} miles away" if distance is not None else ""
        return f"Nearby NOAA station: {station}{distance_text}."
    return f"NOAA station: {station}."


def location_attribution_html(location: dict, snapshot: dict, activity_slug: str = "fishing") -> str:
    timezone_name = location.get("timezone") or "UTC"
    forecast_update = _provider_local_time(snapshot, "forecast", timezone_name)
    alert_update = _provider_local_time(snapshot, "alerts", timezone_name)
    tide_update = _provider_local_time(snapshot, "tide", timezone_name)
    updates = []
    if forecast_update:
        updates.append(f"Forecast: {forecast_update}")
    if alert_update:
        updates.append(f"Safety alerts: {alert_update}")
    if tide_update:
        updates.append(f"Tides: {tide_update}")
    update_html = " · ".join(escape(item) for item in updates) or "Source update times unavailable."

    if activity_slug == "surfing":
        score_line = '<p><strong>Surf Conditions Score &amp; Surf Planning Window:</strong> calculated by CoastalNow from the source data above using published rule-based methodology.</p>'
        context_line = '<p><strong>Daylight context:</strong> calculated locally by CoastalNow and used as a low-weight planning input.</p>'
        product_note = 'Surf Conditions Score is a CoastalNow planning metric and is not an official NOAA/NWS product or safety determination. CoastalNow is not affiliated with or endorsed by NOAA or the National Weather Service.'
    else:
        score_line = '<p><strong>Fishing Score &amp; Best Fishing Time:</strong> calculated by CoastalNow from the source data above using published rule-based methodology.</p>'
        context_line = '<p><strong>Solar &amp; lunar context:</strong> calculated locally by CoastalNow; lunar influence has low weight and is not presented as a catch guarantee.</p>'
        product_note = 'Fishing Score is a CoastalNow planning metric and is not an official NOAA/NWS product or safety determination. CoastalNow is not affiliated with or endorsed by NOAA or the National Weather Service.'

    return (
        '<!-- ACTIVITY_ATTRIBUTION_START -->'
        '<section class="section activity-panel activity-sources">'
        '<div class="section-head"><div><p class="eyebrow">TRANSPARENCY</p>'
        '<h2>Data sources &amp; methodology</h2></div></div>'
        '<div class="activity-source-list">'
        f'<p><strong>Tides &amp; water observations:</strong> <a href="{NOAA_COOPS_URL}" rel="noopener">NOAA/NOS/CO-OPS</a>. '
        f'{escape(_tide_source_text(location))}</p>'
        f'<p><strong>Weather, wind, waves &amp; alerts:</strong> <a href="{NWS_API_URL}" rel="noopener">NOAA National Weather Service</a>.</p>'
        + score_line
        + context_line
        + '</div>'
        + f'<p class="meta">{update_html}</p>'
        + f'<p class="meta">{escape(product_note)}</p>'
        + f'<a class="card-arrow" href="{METHODOLOGY_URL}">Full Data Sources &amp; Methodology →</a>'
        + '</section>'
        + '<!-- ACTIVITY_ATTRIBUTION_END -->'
    )

def hub_attribution_html(activity_slug: str = "fishing") -> str:
    if activity_slug == "surfing":
        product_note = 'Surf Conditions Scores and planning windows are calculated by CoastalNow. They are not official NOAA/NWS products, safety determinations, or break-specific forecasts.'
    else:
        product_note = 'Fishing Scores and best-time windows are calculated by CoastalNow. They are not official NOAA/NWS products, safety determinations, or catch predictions.'
    return (
        '<!-- ACTIVITY_ATTRIBUTION_START -->'
        '<section class="section activity-panel activity-sources">'
        '<div class="section-head"><div><p class="eyebrow">TRANSPARENCY</p>'
        '<h2>Data sources &amp; methodology</h2></div></div>'
        f'<p>Tide inputs come from <a href="{NOAA_COOPS_URL}" rel="noopener">NOAA/NOS/CO-OPS</a>; weather, wind, wave context and alerts come from the <a href="{NWS_API_URL}" rel="noopener">NOAA National Weather Service</a>.</p>'
        + f'<p>{escape(product_note)}</p>'
        + f'<a class="card-arrow" href="{METHODOLOGY_URL}">Full Data Sources &amp; Methodology →</a>'
        + '</section>'
        + '<!-- ACTIVITY_ATTRIBUTION_END -->'
    )

def inject_attribution(html: str, block: str) -> str:
    """Insert or replace a source block idempotently before the methodology note."""
    if ATTRIBUTION_PATTERN.search(html):
        return ATTRIBUTION_PATTERN.sub(block, html, count=1)
    marker = '<section class="activity-method-note">'
    if marker in html:
        return html.replace(marker, block + marker, 1)
    if "</main>" in html:
        return html.replace("</main>", block + "</main>", 1)
    raise ValueError("Could not find Activity attribution insertion point")
