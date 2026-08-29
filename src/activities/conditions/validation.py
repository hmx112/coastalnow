"""Validation and freshness policy for common Activity condition snapshots."""
from __future__ import annotations

import math
from datetime import datetime

ALERT_MAX_AGE_HOURS = 2
FORECAST_MAX_AGE_HOURS = 6


def _parse_aware_iso(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"{label} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include timezone information")
    return parsed


def _validate_optional_number(item: dict, field: str, low: float, high: float, *, low_inclusive: bool = True) -> None:
    value = item.get(field)
    if value is None:
        return
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number or null")
    lower_ok = value >= low if low_inclusive else value > low
    if not lower_ok or value > high:
        comparator = ">=" if low_inclusive else ">"
        raise ValueError(f"{field} must be {comparator} {low} and <= {high}")


def validate_snapshot(snapshot: dict) -> dict:
    if snapshot.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if not snapshot.get("location"):
        raise ValueError("location is required")
    if not snapshot.get("timezone"):
        raise ValueError("timezone is required")
    _parse_aware_iso(snapshot.get("generated_at_utc", ""), "generated_at_utc")

    providers = snapshot.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("providers must be an object")
    for name, provider in providers.items():
        if not isinstance(provider, dict):
            raise ValueError(f"provider {name} must be an object")
        if not provider.get("source"):
            raise ValueError(f"provider {name} source is required")
        if provider.get("status") not in {"ok", "stale", "error", "unavailable"}:
            raise ValueError(f"provider {name} has invalid status")
        _parse_aware_iso(provider.get("fetched_at_utc", ""), f"provider {name} fetched_at_utc")

    hourly = snapshot.get("hourly")
    if not isinstance(hourly, list):
        raise ValueError("hourly must be a list")
    previous = None
    for item in hourly:
        if not isinstance(item, dict):
            raise ValueError("hourly entries must be objects")
        current = _parse_aware_iso(item.get("time", ""), "hourly time")
        if previous is not None and current <= previous:
            raise ValueError("hourly timestamps must be strictly increasing")
        previous = current
        _validate_optional_number(item, "wind_mph", 0, 250)
        _validate_optional_number(item, "gust_mph", 0, 300)
        _validate_optional_number(item, "wind_direction_deg", 0, 360)
        _validate_optional_number(item, "precip_probability_pct", 0, 100)
        _validate_optional_number(item, "air_temperature_f", -150, 160)
        _validate_optional_number(item, "wave_height_ft", 0, 100)
        _validate_optional_number(item, "wave_period_s", 0, 60, low_inclusive=False)
        _validate_optional_number(item, "water_temperature_f", -10, 120)

    alerts = snapshot.get("alerts")
    if not isinstance(alerts, dict) or alerts.get("status") not in {"ok", "stale", "error", "unavailable"}:
        raise ValueError("alerts must include a valid status")
    if not isinstance(alerts.get("items", []), list):
        raise ValueError("alerts items must be a list")
    if not isinstance(snapshot.get("provenance"), dict):
        raise ValueError("provenance must be an object")
    return snapshot


def _provider_freshness(provider: dict | None, now: datetime, max_age_hours: float) -> str:
    if not provider or provider.get("status") != "ok":
        return "unavailable"
    try:
        fetched = _parse_aware_iso(provider["fetched_at_utc"], "provider fetched_at_utc")
    except (KeyError, ValueError):
        return "unavailable"
    age_hours = (now - fetched).total_seconds() / 3600
    if age_hours < 0:
        return "unavailable"
    return "fresh" if age_hours <= max_age_hours else "stale"


def assess_snapshot_freshness(snapshot: dict, now: datetime) -> dict:
    """Apply the conservative publication freshness policy to critical providers."""
    providers = snapshot.get("providers") or {}
    alert_state = _provider_freshness(providers.get("alerts"), now, ALERT_MAX_AGE_HOURS)
    forecast_state = _provider_freshness(providers.get("forecast"), now, FORECAST_MAX_AGE_HOURS)
    alert_payload_status = (snapshot.get("alerts") or {}).get("status")
    if alert_payload_status != "ok":
        alert_state = "unavailable"
    normal_safety = alert_state == "fresh"
    high_medium = normal_safety and forecast_state == "fresh"
    return {
        "alerts": alert_state,
        "forecast": forecast_state,
        "normal_safety_state_allowed": normal_safety,
        "high_medium_eligible": high_medium,
    }
