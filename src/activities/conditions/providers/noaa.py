"""NOAA CO-OPS helpers used by Activity snapshots."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COOPS_API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USER_AGENT = "CoastalNow/1.0 (https://coastalnowtides.com/)"


def parse_water_temperature(payload: dict) -> float | None:
    if payload.get("error"):
        return None
    rows = payload.get("data") or []
    if not rows:
        return None
    try:
        return round(float(rows[-1]["v"]), 2)
    except (KeyError, TypeError, ValueError):
        return None


def fetch_latest_water_temperature(station_id: str, *, retries: int = 3, timeout: int = 20) -> float | None:
    query = urllib.parse.urlencode({
        "product": "water_temperature",
        "date": "latest",
        "station": station_id,
        "time_zone": "gmt",
        "units": "english",
        "application": "CoastalNow",
        "format": "json",
    })
    request = urllib.request.Request(
        COOPS_API + "?" + query,
        headers={"User-Agent": USER_AGENT},
    )
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return parse_water_temperature(payload)
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    # Water temperature is optional. Provider failure stays unknown rather than blocking Tide.
    return None


def load_tide_cache(location: dict, public_root: Path) -> dict | None:
    path = public_root / location["data_path"]
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None
