"""Publication validation for the Surfing v1 location pilot."""
from __future__ import annotations

import json
from pathlib import Path

from activities.registry import ACTIVITIES


def _read_snapshot(public_root: Path, slug: str) -> dict | None:
    path = public_root / "data" / "conditions" / f"{slug}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _wave_coverage(rows: list[dict]) -> tuple[int, int]:
    sample = rows[:24]
    usable = 0
    for row in sample:
        height = row.get("wave_height_ft")
        period = row.get("wave_period_s")
        if height is None or period is None:
            continue
        try:
            if float(height) >= 0 and float(period) > 0:
                usable += 1
        except (TypeError, ValueError):
            continue
    return usable, len(sample)


def validate_surfing_pilot(locations: dict, public_root: Path) -> list[str]:
    """Require reliable shared marine data for every configured Surfing pilot location."""
    surfing = ACTIVITIES["surfing"]
    pilot = list(surfing.get("location_allowlist") or ())
    failures: list[str] = []

    if len(pilot) != 10:
        failures.append(f"pilot configuration: expected 10 locations, found {len(pilot)}")

    for slug in pilot:
        if slug not in locations:
            failures.append(f"{slug}: unknown configured location")
            continue
        snapshot = _read_snapshot(public_root, slug)
        if snapshot is None:
            failures.append(f"{slug}: missing snapshot")
            continue

        providers = snapshot.get("providers") or {}
        marine = providers.get("marine") or {}
        alerts = providers.get("alerts") or {}
        if marine.get("status") != "ok":
            failures.append(f"{slug}: marine provider is not ok")
        if alerts.get("status") == "error":
            failures.append(f"{slug}: alerts provider is error")

        rows = snapshot.get("hourly")
        if not isinstance(rows, list):
            failures.append(f"{slug}: hourly data is missing")
            continue
        usable, sampled = _wave_coverage(rows)
        if sampled < 12 or usable < 12:
            failures.append(f"{slug}: wave coverage {usable}/{sampled}, need at least 12 usable rows")

    if failures:
        raise ValueError("Surfing pilot validation failed: " + " | ".join(failures))
    return pilot
