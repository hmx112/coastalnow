#!/usr/bin/env python3
"""Promote existing CoastalNow catalog locations to Live NOAA safely."""
from __future__ import annotations

import argparse
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from locations import LOCATIONS

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "data" / "locations.json"
LIVE_CONFIG = ROOT / "data" / "live_noaa.json"
API = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
PREDICTION_MODES = {"harmonic", "hilo-derived"}


def load_catalog(path: Path = CATALOG) -> dict[str, dict]:
    return {slug: dict(location) for slug, location in LOCATIONS.items()}


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


def validate_prediction_mode(prediction_mode: str) -> str:
    prediction_mode = prediction_mode.strip()
    if prediction_mode not in PREDICTION_MODES:
        raise ValueError(
            "prediction_mode must be one of: " + ", ".join(sorted(PREDICTION_MODES))
        )
    return prediction_mode


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
        validate_prediction_mode(str(entry.get("prediction_mode", "harmonic")))


def normalize_request_payload(payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        raise ValueError("promotion request must be a JSON object")
    raw_items = payload.get("locations") if "locations" in payload else [payload]
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("promotion request must contain at least one location")
    items = []
    seen = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("each promotion location must be an object")
        missing = [key for key in ("slug", "station_id", "station_name") if key not in raw]
        if missing:
            raise ValueError("Promotion request missing fields: " + ", ".join(missing))
        slug = str(raw["slug"]).strip()
        if slug in seen:
            raise ValueError(f"duplicate promotion slug: {slug}")
        seen.add(slug)
        station_name = str(raw["station_name"]).strip()
        if not station_name:
            raise ValueError("station_name is required")
        items.append({
            "slug": slug,
            "station_id": validate_station_id(str(raw["station_id"])),
            "station_name": station_name,
            "prediction_mode": validate_prediction_mode(str(raw.get("prediction_mode", "harmonic"))),
        })
    return items


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


def validate_noaa_compatibility(location: dict, station_id: str, prediction_mode: str = "harmonic") -> None:
    prediction_mode = validate_prediction_mode(prediction_mode)
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
    if prediction_mode == "hilo-derived":
        return
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
            "Use prediction_mode=hilo-derived only for an official NOAA subordinate station."
        )


def promote_batch(
    items: list[dict],
    *,
    config_path: Path = LIVE_CONFIG,
    validate_network: bool = False,
) -> dict[str, dict]:
    catalog = load_catalog()
    normalized = normalize_request_payload({"locations": items})
    for item in normalized:
        slug = item["slug"]
        if slug not in catalog:
            raise ValueError(f"Unknown location slug: {slug}")
        if validate_network:
            validate_noaa_compatibility(
                catalog[slug], item["station_id"], item["prediction_mode"]
            )

    config = load_live_config(config_path)
    updated = dict(config)
    for item in normalized:
        updated[item["slug"]] = {
            "station_id": item["station_id"],
            "station_name": item["station_name"],
            "prediction_mode": item["prediction_mode"],
        }
    validate_config(updated, catalog)
    config_path.write_text(
        json.dumps(dict(sorted(updated.items())), indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def promote(
    slug: str,
    station_id: str,
    station_name: str,
    *,
    prediction_mode: str = "harmonic",
    config_path: Path = LIVE_CONFIG,
    validate_network: bool = False,
) -> dict[str, dict]:
    return promote_batch(
        [{
            "slug": slug,
            "station_id": station_id,
            "station_name": station_name,
            "prediction_mode": prediction_mode,
        }],
        config_path=config_path,
        validate_network=validate_network,
    )


def load_request(path: Path) -> dict:
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise ValueError("promotion request must be a JSON object")
    normalize_request_payload(request)
    return request


def promote_request(
    request_path: Path,
    *,
    config_path: Path = LIVE_CONFIG,
    validate_network: bool = True,
) -> dict[str, dict]:
    request = load_request(request_path)
    return promote_batch(
        normalize_request_payload(request),
        config_path=config_path,
        validate_network=validate_network,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--slug")
    parser.add_argument("--station-id")
    parser.add_argument("--station-name")
    parser.add_argument("--prediction-mode", choices=sorted(PREDICTION_MODES), default="harmonic")
    parser.add_argument("--validate-network", action="store_true")
    parser.add_argument("--validate-config", action="store_true")
    args = parser.parse_args()

    if args.validate_config:
        validate_config(load_live_config(), load_catalog())
        print("Live NOAA config is valid.")
        return 0

    if args.request:
        request = load_request(args.request)
        items = normalize_request_payload(request)
        promote_batch(items, validate_network=True)
        print("Promoted to Live NOAA: " + ", ".join(item["slug"] for item in items))
        return 0

    if not (args.slug and args.station_id and args.station_name):
        parser.error("--slug, --station-id and --station-name are required for promotion")

    promote(
        args.slug,
        args.station_id,
        args.station_name,
        prediction_mode=args.prediction_mode,
        validate_network=args.validate_network,
    )
    print(f"Promoted {args.slug} to Live NOAA using station {args.station_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
