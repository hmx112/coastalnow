"""Geographic internal-link helpers for CoastalNow tide locations."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt


def _coordinates(location: dict) -> tuple[float, float] | None:
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        return float(latitude), float(longitude)

    activity = location.get("activity") or {}
    shore_point = activity.get("shore_point") or {}
    latitude = shore_point.get("latitude")
    longitude = shore_point.get("longitude")
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        return float(latitude), float(longitude)
    return None


def distance_miles(a: dict, b: dict) -> float:
    coords_a = _coordinates(a)
    coords_b = _coordinates(b)
    if coords_a is None or coords_b is None:
        raise ValueError("Both locations require usable coordinates")
    lat1, lon1 = map(radians, coords_a)
    lat2, lon2 = map(radians, coords_b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3958.7613 * 2 * asin(sqrt(h))


def nearest_same_state_locations(
    location: dict,
    locations: dict[str, dict],
    limit: int = 4,
) -> list[dict]:
    if limit <= 0 or _coordinates(location) is None:
        return []
    candidates = []
    for item in locations.values():
        if item.get("slug") == location.get("slug"):
            continue
        if item.get("state_slug") != location.get("state_slug"):
            continue
        if item.get("status") != "Live NOAA":
            continue
        if _coordinates(item) is None:
            continue
        candidates.append(item)
    candidates.sort(key=lambda item: (distance_miles(location, item), item.get("name", "")))
    return candidates[:limit]
