"""Enabled coastal activities and their shared generation requirements."""
from __future__ import annotations

ACTIVITIES = {
    "fishing": {
        "slug": "fishing",
        "label": "Fishing",
        "enabled": True,
        "scorer_version": "fishing-v1",
        "requires": ("tide", "wind", "weather", "alerts", "marine"),
    },
    "surfing": {
        "slug": "surfing",
        "label": "Surfing",
        "enabled": True,
        "scorer_version": "surfing-v1",
        "requires": ("wind", "weather", "alerts", "marine"),
        "location_allowlist": (
            "san-diego",
            "la-jolla",
            "huntington-beach",
            "santa-cruz",
            "malibu",
            "half-moon-bay",
            "cocoa-beach",
            "daytona-beach",
            "wrightsville-beach",
            "virginia-beach",
        ),
    },
    "beach": {
        "slug": "beach",
        "label": "Beach",
        "enabled": False,
        "scorer_version": "beach-future",
        "requires": ("weather", "wind", "marine", "alerts"),
    },
    "swimming": {
        "slug": "swimming",
        "label": "Swimming",
        "enabled": False,
        "scorer_version": "swimming-future",
        "requires": ("weather", "wind", "marine", "alerts"),
    },
}


def activity_enabled_for_location(activity: dict, location_slug: str) -> bool:
    """Return whether one Activity is public/enabled for a location slug."""
    if not activity.get("enabled"):
        return False
    allowlist = activity.get("location_allowlist")
    return allowlist is None or location_slug in allowlist


def enabled_activities(registry: dict | None = None) -> list[dict]:
    """Return globally enabled activity configs in registry insertion order."""
    source = ACTIVITIES if registry is None else registry
    return [dict(item) for item in source.values() if item.get("enabled")]


def enabled_activities_for_location(location: dict, registry: dict | None = None) -> list[dict]:
    """Return enabled Activity configs that are public for one location."""
    source = ACTIVITIES if registry is None else registry
    return [
        dict(item)
        for item in source.values()
        if activity_enabled_for_location(item, location["slug"])
    ]
