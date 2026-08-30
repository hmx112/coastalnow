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
        "enabled": False,
        "scorer_version": "surfing-future",
        "requires": ("tide", "wind", "marine"),
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


def enabled_activities(registry: dict | None = None) -> list[dict]:
    """Return enabled activity configs in registry insertion order."""
    source = ACTIVITIES if registry is None else registry
    return [dict(item) for item in source.values() if item.get("enabled")]
