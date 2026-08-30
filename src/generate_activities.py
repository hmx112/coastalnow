#!/usr/bin/env python3
"""Generate shared coastal-condition snapshots and enabled Activity results."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from activities.conditions.collect import collect_location_conditions
from activities.conditions.providers.nws import active_alerts, dedupe_alerts
from activities.paths import activity_data_path
from activities.registry import ACTIVITIES, enabled_activities
from activities.scoring.fishing_policy import score_fishing_activity
from locations import LOCATIONS

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DEFAULT_SCORERS = {"fishing": score_fishing_activity}


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def condition_path(public_root: Path, location: dict) -> Path:
    return public_root / "data" / "conditions" / f'{location["slug"]}.json'


def _unavailable_snapshot(location: dict, now: datetime, reason: str) -> dict:
    timestamp = now.isoformat(timespec="seconds")
    return {
        "schema_version": 1,
        "location": location["slug"],
        "timezone": location["timezone"],
        "generated_at_utc": timestamp,
        "refresh_state": "unavailable",
        "refresh_error": reason,
        "providers": {
            "alerts": {"source": "NWS", "status": "error", "fetched_at_utc": timestamp},
            "forecast": {"source": "NWS", "status": "unavailable", "fetched_at_utc": timestamp},
            "marine": {"source": "NWS forecastGridData", "status": "unavailable", "fetched_at_utc": timestamp},
            "tide": {"source": "NOAA/NOS/CO-OPS", "status": "unavailable", "fetched_at_utc": timestamp},
        },
        "hourly": [],
        "alerts": {"status": "error", "items": []},
        "provenance": {"failure": reason},
        "tide": None,
        "astronomy": {},
    }


def _cached_or_unavailable(location: dict, public_root: Path, now: datetime, error: Exception) -> tuple[dict, str]:
    cached = read_json(condition_path(public_root, location))
    if cached:
        cached = deepcopy(cached)
        cached["refresh_state"] = "cache-fallback"
        cached["refresh_attempted_at_utc"] = now.isoformat(timespec="seconds")
        cached["refresh_error"] = str(error)
        return cached, "cache-fallback"
    return _unavailable_snapshot(location, now, str(error)), "unavailable"


def _refresh_alerts_only(
    location: dict,
    public_root: Path,
    now: datetime,
    *,
    alerts_fetch,
) -> tuple[dict, str]:
    snapshot = read_json(condition_path(public_root, location))
    if not snapshot:
        snapshot = _unavailable_snapshot(location, now, "alert-only refresh has no condition cache")
    else:
        snapshot = deepcopy(snapshot)

    timestamp = now.isoformat(timespec="seconds")
    activity = location["activity"]
    shore = activity["shore_point"]
    marine = activity["marine_point"]
    request_cache = {}
    try:
        shore_alerts = alerts_fetch(shore["latitude"], shore["longitude"], cache=request_cache)
        marine_alerts = alerts_fetch(marine["latitude"], marine["longitude"], cache=request_cache)
        items = dedupe_alerts(shore_alerts, marine_alerts)
        alert_status = "ok"
    except Exception as exc:
        items = []
        alert_status = "error"
        snapshot["alert_refresh_error"] = str(exc)

    snapshot.setdefault("providers", {})["alerts"] = {
        "source": "NWS",
        "status": alert_status,
        "fetched_at_utc": timestamp,
    }
    snapshot["alerts"] = {"status": alert_status, "items": items}
    snapshot["generated_at_utc"] = timestamp
    snapshot["refresh_state"] = "alerts-only"
    return snapshot, "alerts-only"


def generate_location(
    location: dict,
    *,
    public_root: Path = PUBLIC,
    now: datetime | None = None,
    collector=collect_location_conditions,
    registry: dict | None = None,
    scorers: dict | None = None,
    alerts_only: bool = False,
    alerts_fetch=active_alerts,
) -> dict:
    """Collect once, score every enabled Activity, and atomically persist outputs."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    registry = ACTIVITIES if registry is None else registry
    scorers = DEFAULT_SCORERS if scorers is None else scorers

    if alerts_only:
        snapshot, source = _refresh_alerts_only(
            location,
            public_root,
            now,
            alerts_fetch=alerts_fetch,
        )
    else:
        try:
            snapshot = collector(location, public_root=public_root, now=now)
            snapshot["refresh_state"] = "live"
            source = "live"
        except Exception as exc:
            snapshot, source = _cached_or_unavailable(location, public_root, now, exc)

    atomic_write_json(condition_path(public_root, location), snapshot)

    outputs = {}
    for activity in enabled_activities(registry):
        slug = activity["slug"]
        scorer = scorers.get(slug)
        if scorer is None:
            raise ValueError(f"No scorer registered for enabled activity: {slug}")
        result = scorer(snapshot, location=location, now=now)
        result.setdefault("activity", slug)
        result.setdefault("location", location["slug"])
        output = public_root / activity_data_path(location, slug)
        atomic_write_json(output, result)
        outputs[slug] = result

    return {
        "location": location["slug"],
        "condition_source": source,
        "activities": outputs,
    }


def _selected_locations(slug: str | None) -> list[dict]:
    if slug is None:
        return list(LOCATIONS.values())
    if slug not in LOCATIONS:
        raise ValueError(f"Unknown location: {slug}")
    return [LOCATIONS[slug]]


def _activity_registry(activity_slug: str | None) -> dict:
    if activity_slug is None:
        return ACTIVITIES
    if activity_slug not in ACTIVITIES:
        raise ValueError(f"Unknown activity: {activity_slug}")
    selected = deepcopy(ACTIVITIES)
    for slug, config in selected.items():
        config["enabled"] = slug == activity_slug
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--location")
    parser.add_argument("--activity")
    parser.add_argument("--alerts-only", action="store_true")
    parser.add_argument("--public-root", type=Path, default=PUBLIC)
    args = parser.parse_args()

    registry = _activity_registry(args.activity)
    failures = []
    for location in _selected_locations(args.location):
        try:
            result = generate_location(
                location,
                public_root=args.public_root,
                registry=registry,
                alerts_only=args.alerts_only,
            )
            print(f'{location["slug"]}: {result["condition_source"]}')
        except Exception as exc:
            failures.append(f'{location["slug"]}: {exc}')
            print(f'{location["slug"]}: FAILED: {exc}')
    if failures:
        print("Activity generation failures: " + " | ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
