#!/usr/bin/env python3
"""Promote an existing CoastalNow catalog location to Live NOAA safely."""
from __future__ import annotations

import argparse
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "data" / "locations.json"
LIVE_CONFIG = ROOT / "data" / "live_noaa.json"
API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def load_catalog(path: Path = CATALOG) -> dict[str, dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = {item["slug"]: item for item in raw}
    items.setdefault("los-angeles", {
        "slug": "los-angeles",
        "name": "Los Angeles",
        "state": "California",
        "state_code": "CA",
        "state_slug": "california",
        "timezone": "America/Los_Angeles",
    })
    return items


def load_live_config(path: Path = LIVE_CONFIG) -> dict[str, dict]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("live_noaa.json must be a JSON object")
    return raw


def validate_station_id(station_id: str) -> str:
    station_id = station_id.strip()
    if not station_id.isdigit() or len(station_id) != 7:
        raise ValueError("NOAA station_id must be a 7-digit numeric string")
    return station_id


def validate_config(config: dict[str, dict], catalog: dict[str, dict]) -> None:
    unknown = sorted(set(config) - set(catalog))
    if unknown:
        raise ValueError("Live NOAA config contains unknown catalog slugs: " + ", ".join(unknown))
    for slug, entry in config.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{slug}: config must be an object")
        validate_station_id(str(entry.get("station_id", "")))
        if not str(entry.get("station_name", "")).strip():
            raise ValueError(f"{slug}: station_name is required")


def _request(station_id: str, params: dict) -> dict:
    query = {
        "station": station_id,
        "datum": "MLLW",
        "time_zone": "lst_ldt",
        "units": "english",
        "application": "CoastalNow",
        "format": "json",
        **params,
    }
    url = API + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"User-Agent": "CoastalNow station validator"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(f"NOAA API error: {payload['error']}")
    return payload


def validate_noaa_compatibility(location: dict, station_id: str) -> None:
    """Require both hilo and 30-minute predictions used by the current page renderer."""
    tz = ZoneInfo(location["timezone"])
    start = datetime.now(tz).date()
    end = start + timedelta(days=1)
    dates = {
        "begin_date": start.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
        "product": "predictions",
    }

    hilo = _request(station_id, {**dates, "interval": "hilo"}).get("predictions", [])
    types = {item.get("type") for item in hilo}
    if not hilo or not {"H", "L"} <= types:
        raise RuntimeError("Station does not provide usable NOAA high/low predictions")

    curve = _request(station_id, {**dates, "interval": "30"}).get("predictions", [])
    valid_curve = []
    for item in curve:
        try:
            value = float(item["v"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value):
            valid_curve.append(item)
    if len(valid_curve) < 70:
        raise RuntimeError(
            "Station does not provide enough 30-minute prediction points. "
            "It may be a subordinate station; keep it Preview until subordinate support is added."
        )


def promote(
    slug: str,
    station_id: str,
    station_name: str,
    *,
    config_path: Path = LIVE_CONFIG,
    validate_network: bool = False,
) -> dict[str, dict]:
    catalog = load_catalog()
    if slug not in catalog:
        raise ValueError(f"Unknown location slug: {slug}")
    station_id = validate_station_id(station_id)
    station_name = station_name.strip()
    if not station_name:
        raise ValueError("station_name is required")

    if validate_network:
        validate_noaa_compatibility(catalog[slug], station_id)

    config = load_live_config(config_path)
    config[slug] = {"station_id": station_id, "station_name": station_name}
    validate_config(config, catalog)
    config_path.write_text(
        json.dumps(dict(sorted(config.items())), indent=2) + "\n",
        encoding="utf-8",
    )
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug")
    parser.add_argument("--station-id")
    parser.add_argument("--station-name")
    parser.add_argument("--validate-network", action="store_true")
    parser.add_argument("--validate-config", action="store_true")
    args = parser.parse_args()

    if args.validate_config:
        validate_config(load_live_config(), load_catalog())
        print("Live NOAA config is valid.")
        return 0

    if not (args.slug and args.station_id and args.station_name):
        parser.error("--slug, --station-id and --station-name are required for promotion")

    promote(
        args.slug,
        args.station_id,
        args.station_name,
        validate_network=args.validate_network,
    )
    print(f"Promoted {args.slug} to Live NOAA using station {args.station_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
