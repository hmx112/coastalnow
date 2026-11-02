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
        index = item["release_index"]
        published = config.get("legacy_location_count", len(catalog))
        if index < published:
            release_date = release_date_for_index(start, index, config["locations_per_day"])
        else:
            backfill = date.fromisoformat(config["new_location_start_date"])
            release_date = release_date_for_index(backfill, index - published, config["locations_per_day"])
        if release_date <= as_of:
            released.append({**item, "release_date": release_date})
    return released


def released_surfing_locations(catalog: list[dict], config: dict, as_of: date) -> list[dict]:
    """Return Surfing pilot locations due on their independent one-location-per-day schedule."""
    if not config.get("enabled"):
        return []
    start = date.fromisoformat(config["surfing_start_date"])
    by_slug = {item["slug"]: item for item in catalog}
    released = []
    for index, slug in enumerate(config["surfing_launch_order"]):
        item = by_slug[slug]
        if not item.get("surfing_enabled"):
            raise ValueError(f"Pinterest Surfing schedule contains disabled location: {slug}")
        published = config.get("legacy_surfing_count", len(config["surfing_launch_order"]))
        if index < published:
            release_date = release_date_for_index(start, index, config["locations_per_day"])
        else:
            next_start = date.fromisoformat(config["new_surfing_start_date"])
            release_date = release_date_for_index(next_start, index - published, config["locations_per_day"])
        if release_date <= as_of:
            released.append({**item, "release_date": release_date})
    return released


def released_creative_v2_pilots(catalog: list[dict], config: dict, as_of: date) -> list[dict]:
    """Release v2 test designs in the configured batch or daily cadence."""
    if not config.get("enabled"):
        return []
    start_text = config.get("creative_v2_start_date")
    if not start_text:
        return []
    start = date.fromisoformat(start_text)
    batch_release = config.get("creative_v2_batch_release", False)
    if not isinstance(batch_release, bool):
        raise ValueError("Pinterest creative_v2_batch_release must be a boolean")
    by_slug = {item["slug"]: item for item in catalog}
    pilots = config.get("creative_v2_pilots") or []
    seen = set()
    output = []
    for index, candidate in enumerate(pilots):
        kind, slug = candidate["kind"], candidate["slug"]
        if kind not in {"tides", "fishing", "surfing"}:
            raise ValueError(f"Invalid Pinterest v2 pilot kind: {kind}")
        if slug not in by_slug:
            raise ValueError(f"Unknown Pinterest v2 pilot slug: {slug}")
        if (kind, slug) in seen:
            raise ValueError(f"Duplicate Pinterest v2 creative: {kind}/{slug}")
        seen.add((kind, slug))
        item = by_slug[slug]
        if kind in {"fishing", "surfing"} and not item.get(f"{kind}_enabled"):
            raise ValueError(f"Disabled Pinterest v2 activity: {kind}/{slug}")
        # Six alternative pilot creatives are intentionally released together;
        # ordinary location and Surfing backfill remain daily.
        release_date = start if batch_release else release_date_for_index(start, index, config["locations_per_day"])
        if release_date <= as_of:
            output.append({**item, "creative_version": "v2", "kind": kind, "release_date": release_date})
    return output
