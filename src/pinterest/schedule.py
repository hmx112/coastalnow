"""Deterministic Pinterest release scheduling."""
from __future__ import annotations

from datetime import date, timedelta


def release_date_for_index(start_date: date, index: int, locations_per_day: int) -> date:
    if locations_per_day != 1:
        raise ValueError("Pinterest v1 supports exactly one location per day")
    return start_date + timedelta(days=index)


def released_locations(catalog: list[dict], config: dict, as_of: date) -> list[dict]:
    if not config.get("enabled"):
        return []
    start = date.fromisoformat(config["start_date"])
    released = []
    for item in catalog:
        release_date = release_date_for_index(start, item["release_index"], config["locations_per_day"])
        if release_date <= as_of:
            released.append({**item, "release_date": release_date})
    return released
