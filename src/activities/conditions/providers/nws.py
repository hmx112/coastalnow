"""NWS API request/parsing helpers for coastal Activity conditions."""
from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
from copy import deepcopy
from datetime import datetime, timedelta

NWS_API = "https://api.weather.gov"
USER_AGENT = "CoastalNow/1.0 (https://coastalnowtides.com/)"

_CARDINAL_DEGREES = {
    "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
    "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
    "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
    "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5,
}


def request_json(url: str, *, retries: int = 3, timeout: int = 25, cache: dict | None = None) -> dict:
    """Fetch NWS JSON with retries and optional in-process URL deduplication."""
    if cache is not None and url in cache:
        return deepcopy(cache[url])
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"},
    )
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if cache is not None:
                cache[url] = deepcopy(payload)
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"NWS request failed after {retries} attempts for {url}: {last_error}")


def _zone_id(value: str | None) -> str | None:
    return value.rstrip("/").rsplit("/", 1)[-1] if value else None


def parse_point_metadata(payload: dict) -> dict:
    properties = payload.get("properties") or {}
    hourly = properties.get("forecastHourly")
    grid = properties.get("forecastGridData")
    if not hourly or not grid:
        raise ValueError("NWS point metadata lacks forecastHourly or forecastGridData")
    return {
        "forecast_hourly": hourly,
        "forecast_grid_data": grid,
        "forecast_zone": _zone_id(properties.get("forecastZone")),
        "county_zone": _zone_id(properties.get("county")),
        "time_zone": properties.get("timeZone"),
        "grid_id": properties.get("gridId"),
        "grid_x": properties.get("gridX"),
        "grid_y": properties.get("gridY"),
    }


def point_metadata(latitude: float, longitude: float, *, cache: dict | None = None) -> dict:
    url = f"{NWS_API}/points/{latitude:.4f},{longitude:.4f}"
    return parse_point_metadata(request_json(url, cache=cache))


def _temperature_f(value, unit: str | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if (unit or "F").upper() == "C":
        number = number * 9 / 5 + 32
    return round(number, 2)


def _wind_mph(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).lower()
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None
    speed = max(numbers)
    if "kt" in text or "knot" in text:
        speed *= 1.150779448
    elif "km" in text:
        speed *= 0.621371192
    return round(speed, 2)


def _direction_degrees(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) % 360
    return _CARDINAL_DEGREES.get(str(value).strip().upper())


def parse_hourly_forecast(payload: dict) -> list[dict]:
    rows = []
    for period in (payload.get("properties") or {}).get("periods", []):
        start = period.get("startTime")
        if not start:
            continue
        parsed = datetime.fromisoformat(start)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("NWS hourly forecast startTime must be offset-aware")
        precip = (period.get("probabilityOfPrecipitation") or {}).get("value")
        rows.append({
            "time": parsed.isoformat(),
            "wind_mph": _wind_mph(period.get("windSpeed")),
            "gust_mph": None,
            "wind_direction_deg": _direction_degrees(period.get("windDirection")),
            "precip_probability_pct": None if precip is None else float(precip),
            "air_temperature_f": _temperature_f(period.get("temperature"), period.get("temperatureUnit")),
            "wave_height_ft": None,
            "wave_period_s": None,
            "water_temperature_f": None,
            "condition_text": period.get("shortForecast") or "",
        })
    return rows


def _parse_duration(value: str) -> timedelta:
    """Parse the day/hour/minute ISO-8601 durations emitted by NWS validTime."""
    match = re.fullmatch(
        r"P(?:(\d+(?:\.\d+)?)D)?(?:T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?)?",
        value,
    )
    if not match:
        raise ValueError(f"Unsupported NWS validTime duration: {value}")
    days = float(match.group(1) or 0)
    hours = float(match.group(2) or 0)
    minutes = float(match.group(3) or 0)
    duration = timedelta(days=days, hours=hours, minutes=minutes)
    if duration.total_seconds() <= 0:
        raise ValueError(f"NWS validTime duration must be positive: {value}")
    return duration


def _unit_value(field: str, value: float | None, uom: str | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    unit = uom or ""
    if field in {"wind_mph", "gust_mph"}:
        if "km_h-1" in unit:
            number *= 0.621371192
        elif "m_s-1" in unit:
            number *= 2.236936292
        elif "kt" in unit:
            number *= 1.150779448
    elif field == "wave_height_ft":
        if unit.endswith(":m") or unit == "m" or "wmoUnit:m" == unit:
            number *= 3.280839895
    elif field == "wave_period_s":
        if number <= 0:
            return None
    elif field == "air_temperature_f":
        if "degC" in unit:
            number = number * 9 / 5 + 32
    return round(number, 3)


def _expand_grid_property(prop: dict | None, output_field: str) -> dict[datetime, float | None]:
    if not prop:
        return {}
    uom = prop.get("uom")
    expanded = {}
    for item in prop.get("values", []):
        valid = item.get("validTime")
        if not valid or "/" not in valid:
            continue
        start_text, duration_text = valid.split("/", 1)
        start = datetime.fromisoformat(start_text)
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("NWS grid validTime must be offset-aware")
        duration = _parse_duration(duration_text)
        count = max(1, int(math.ceil(duration.total_seconds() / 3600)))
        normalized = _unit_value(output_field, item.get("value"), uom)
        for offset in range(count):
            expanded[start + timedelta(hours=offset)] = normalized
    return expanded


def parse_grid_data(payload: dict) -> list[dict]:
    properties = payload.get("properties") or {}
    sources = {
        "gust_mph": _expand_grid_property(properties.get("windGust"), "gust_mph"),
        "wave_height_ft": _expand_grid_property(properties.get("waveHeight"), "wave_height_ft"),
        "wave_period_s": _expand_grid_property(properties.get("wavePeriod"), "wave_period_s"),
    }
    times = sorted({stamp for values in sources.values() for stamp in values})
    return [
        {
            "time": stamp.isoformat(),
            **{field: values.get(stamp) for field, values in sources.items()},
        }
        for stamp in times
    ]


def merge_hourly_conditions(hourly: list[dict], grid: list[dict]) -> list[dict]:
    """Merge grid/marine fields by absolute forecast hour."""
    grid_by_time = {datetime.fromisoformat(item["time"]): item for item in grid}
    out = []
    for row in hourly:
        merged = dict(row)
        stamp = datetime.fromisoformat(row["time"])
        grid_row = next((item for key, item in grid_by_time.items() if key == stamp), None)
        if grid_row:
            for field in ("gust_mph", "wave_height_ft", "wave_period_s"):
                if grid_row.get(field) is not None:
                    merged[field] = grid_row[field]
        out.append(merged)
    return out


def parse_alerts(payload: dict) -> list[dict]:
    alerts = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        alert_id = feature.get("id") or properties.get("id")
        if not alert_id:
            continue
        alerts.append({
            "id": alert_id,
            "event": properties.get("event") or "",
            "severity": properties.get("severity") or "Unknown",
            "certainty": properties.get("certainty") or "Unknown",
            "urgency": properties.get("urgency") or "Unknown",
            "effective": properties.get("effective"),
            "onset": properties.get("onset"),
            "expires": properties.get("expires"),
            "ends": properties.get("ends"),
            "headline": properties.get("headline") or "",
            "description": properties.get("description") or "",
            "instruction": properties.get("instruction") or "",
            "sender_name": properties.get("senderName") or "",
        })
    return alerts


def active_alerts(latitude: float, longitude: float, *, cache: dict | None = None) -> list[dict]:
    query = urllib.parse.urlencode({"point": f"{latitude:.4f},{longitude:.4f}"})
    return parse_alerts(request_json(f"{NWS_API}/alerts/active?{query}", cache=cache))


def dedupe_alerts(*groups: list[dict]) -> list[dict]:
    by_id = {}
    for group in groups:
        for alert in group:
            by_id.setdefault(alert["id"], alert)
    return list(by_id.values())
