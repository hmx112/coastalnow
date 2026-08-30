"""Collect one common official-data Condition Snapshot per CoastalNow location."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from activities.conditions.astronomy import moon_phase_fraction, solar_events
from activities.conditions.providers.noaa import fetch_latest_water_temperature, load_tide_cache
from activities.conditions.providers.nws import (
    active_alerts,
    dedupe_alerts,
    merge_hourly_conditions,
    parse_grid_data,
    parse_hourly_forecast,
    point_metadata,
    request_json,
)
from activities.conditions.snapshot import build_snapshot
from activities.conditions.validation import validate_snapshot


def _default_hourly_fetch(url: str, *, cache=None) -> list[dict]:
    return parse_hourly_forecast(request_json(url, cache=cache))


def _default_grid_fetch(url: str, *, cache=None) -> list[dict]:
    return parse_grid_data(request_json(url, cache=cache))


def _serialize_solar(events: dict) -> dict:
    return {name: value.isoformat() if value is not None else None for name, value in events.items()}


def collect_location_conditions(
    location: dict,
    *,
    public_root: Path,
    now: datetime | None = None,
    point_lookup=point_metadata,
    hourly_fetch=_default_hourly_fetch,
    grid_fetch=_default_grid_fetch,
    alerts_fetch=active_alerts,
    water_fetch=fetch_latest_water_temperature,
    tide_loader=load_tide_cache,
) -> dict:
    """Collect shared Tide/NWS/astronomy inputs without any Activity-specific scoring."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    activity = location["activity"]
    shore = activity["shore_point"]
    marine = activity["marine_point"]
    request_cache = {}

    shore_meta = point_lookup(shore["latitude"], shore["longitude"], cache=request_cache)
    marine_meta = point_lookup(marine["latitude"], marine["longitude"], cache=request_cache)
    hourly_url = shore_meta.get("forecast_hourly")
    marine_grid_url = marine_meta.get("forecast_grid_data")
    if not hourly_url:
        raise RuntimeError(f'{location["slug"]}: NWS shore point has no hourly forecast URL')
    if not marine_grid_url:
        raise RuntimeError(f'{location["slug"]}: NWS marine point has no grid forecast URL')

    hourly = hourly_fetch(hourly_url, cache=request_cache)
    marine_grid = grid_fetch(marine_grid_url, cache=request_cache)
    merged = merge_hourly_conditions(hourly, marine_grid)

    water_temperature = water_fetch(location["station"]) if location.get("station") else None
    if water_temperature is not None:
        for row in merged:
            row["water_temperature_f"] = water_temperature

    alert_status = "ok"
    try:
        shore_alerts = alerts_fetch(shore["latitude"], shore["longitude"], cache=request_cache)
        marine_alerts = alerts_fetch(marine["latitude"], marine["longitude"], cache=request_cache)
        alerts = dedupe_alerts(shore_alerts, marine_alerts)
    except Exception:
        # Safety policy: a failed alert check is unknown, never equivalent to no alerts.
        alert_status = "error"
        alerts = []

    tide = tide_loader(location, public_root)
    tide_status = "ok" if tide else "unavailable"
    tide_timestamp = (tide or {}).get("generated_at_utc") or now.isoformat(timespec="seconds")

    local_tz = ZoneInfo(location["timezone"])
    local_today = now.astimezone(local_tz).date()
    astronomy = {}
    for label, day in (("today", local_today), ("tomorrow", local_today + timedelta(days=1))):
        astronomy[label] = {
            **_serialize_solar(solar_events(day, shore["latitude"], shore["longitude"], local_tz)),
            "moon_phase_fraction": moon_phase_fraction(day),
        }

    fetched = now.isoformat(timespec="seconds")
    snapshot = build_snapshot(
        location,
        generated_at_utc=fetched,
        hourly=merged,
        providers={
            "alerts": {"source": "NWS", "status": alert_status, "fetched_at_utc": fetched},
            "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
            "marine": {
                "source": "NWS forecastGridData",
                "status": "ok" if marine_grid else "unavailable",
                "fetched_at_utc": fetched,
            },
            "tide": {"source": "NOAA/NOS/CO-OPS", "status": tide_status, "fetched_at_utc": tide_timestamp},
            "water_temperature": {
                "source": "NOAA/NOS/CO-OPS",
                "status": "ok" if water_temperature is not None else "unavailable",
                "fetched_at_utc": fetched,
            },
        },
        alerts={"status": alert_status, "items": alerts},
        provenance={
            "wind_mph": "NWS hourly forecast",
            "gust_mph": "NWS marine forecastGridData",
            "air_temperature_f": "NWS hourly forecast",
            "precip_probability_pct": "NWS hourly forecast",
            "wave_height_ft": "NWS marine forecastGridData",
            "wave_period_s": "NWS marine forecastGridData",
            "water_temperature_f": "NOAA/NOS/CO-OPS observation" if water_temperature is not None else "unavailable",
            "alerts": "NWS active alerts",
            "tide": "NOAA/NOS/CO-OPS cached predictions",
            "astronomy": "deterministic local calculation",
        },
    )
    snapshot["tide"] = tide
    snapshot["astronomy"] = astronomy
    snapshot["points"] = {
        "shore": dict(shore),
        "marine": dict(marine),
        "shore_nws": shore_meta,
        "marine_nws": marine_meta,
    }
    validate_snapshot(snapshot)
    return snapshot
