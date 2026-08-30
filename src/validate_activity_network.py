#!/usr/bin/env python3
"""Validate Activity geography against live NWS services and report data coverage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from activities.conditions.providers.nws import (
    active_alerts,
    parse_grid_data,
    parse_hourly_forecast,
    point_metadata,
    request_json,
)
from locations import LOCATIONS

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


def _default_hourly_fetch(url: str, *, cache=None) -> list[dict]:
    return parse_hourly_forecast(request_json(url, cache=cache))


def _default_grid_fetch(url: str, *, cache=None) -> list[dict]:
    return parse_grid_data(request_json(url, cache=cache))


def validate_location_network(
    location: dict,
    *,
    point_lookup=point_metadata,
    hourly_fetch=_default_hourly_fetch,
    grid_fetch=_default_grid_fetch,
    alerts_fetch=active_alerts,
) -> dict:
    """Check real provider geography without treating missing wave fields as bad coordinates."""
    slug = location["slug"]
    activity = location["activity"]
    shore = activity["shore_point"]
    marine = activity["marine_point"]
    cache = {}
    report = {
        "location": slug,
        "points_valid": False,
        "wave_context": False,
        "alerts_available": False,
        "hourly_count": 0,
        "marine_count": 0,
        "status": "invalid-geography",
        "errors": [],
    }

    try:
        shore_meta = point_lookup(shore["latitude"], shore["longitude"], cache=cache)
        marine_meta = point_lookup(marine["latitude"], marine["longitude"], cache=cache)
        hourly_url = shore_meta.get("forecast_hourly")
        grid_url = marine_meta.get("forecast_grid_data")
        if not hourly_url or not grid_url:
            raise RuntimeError("NWS point metadata is missing hourly or grid forecast URLs")
        report["points_valid"] = True
    except Exception as exc:
        report["errors"].append(f"point lookup: {exc}")
        return report

    try:
        hourly = hourly_fetch(hourly_url, cache=cache)
        grid = grid_fetch(grid_url, cache=cache)
        report["hourly_count"] = len(hourly)
        report["marine_count"] = len(grid)
        report["wave_context"] = any(
            row.get("wave_height_ft") is not None and row.get("wave_period_s") is not None
            for row in grid
        )
    except Exception as exc:
        report["errors"].append(f"forecast check: {exc}")
        report["status"] = "forecast-check-unavailable"
        return report

    try:
        alerts_fetch(shore["latitude"], shore["longitude"], cache=cache)
        alerts_fetch(marine["latitude"], marine["longitude"], cache=cache)
        report["alerts_available"] = True
    except Exception as exc:
        report["errors"].append(f"alert check: {exc}")
        report["status"] = "alert-check-unavailable"
        return report

    report["status"] = "ready" if report["wave_context"] else "limited-marine-context"
    return report


def _activity_result_summary(public_root: Path, slug: str) -> str:
    path = public_root / "data" / "activities" / "fishing" / f"{slug}.json"
    if not path.exists():
        return "missing-output"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "invalid-output"
    today = result.get("today") or {}
    confidence = today.get("confidence") or "Unknown"
    status = today.get("status") or today.get("rating") or "Unknown"
    return f"{confidence}/{status}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--location")
    parser.add_argument("--public-root", type=Path, default=PUBLIC)
    args = parser.parse_args()

    if args.location:
        if args.location not in LOCATIONS:
            raise SystemExit(f"Unknown location: {args.location}")
        locations = [LOCATIONS[args.location]]
    else:
        locations = list(LOCATIONS.values())

    reports = []
    for location in locations:
        report = validate_location_network(location)
        report["fishing_result"] = _activity_result_summary(args.public_root, location["slug"])
        reports.append(report)
        print(
            f'{location["slug"]}: {report["status"]}; '
            f'wave_context={report["wave_context"]}; alerts={report["alerts_available"]}; '
            f'fishing={report["fishing_result"]}'
        )
        for error in report["errors"]:
            print(f'  warning: {error}')

    counts = {}
    for report in reports:
        counts[report["status"]] = counts.get(report["status"], 0) + 1
    print("NETWORK SUMMARY " + json.dumps(dict(sorted(counts.items())), sort_keys=True))

    invalid = [report for report in reports if report["status"] == "invalid-geography"]
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
