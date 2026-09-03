"""URL/output paths derived from the location catalog and Activity Registry."""
from __future__ import annotations

from activities.registry import enabled_activities_for_location


def activity_page_path(location: dict, activity_slug: str) -> str:
    return f'tides/{location["state_slug"]}/{location["slug"]}/{activity_slug}/index.html'


def activity_data_path(location: dict, activity_slug: str) -> str:
    return f'data/activities/{activity_slug}/{location["slug"]}.json'


def activity_hub_path(activity_slug: str) -> str:
    return f"{activity_slug}/index.html"


def activity_page_paths_for_location(location: dict, registry: dict | None = None) -> dict[str, str]:
    return {
        activity["slug"]: activity_page_path(location, activity["slug"])
        for activity in enabled_activities_for_location(location, registry)
    }
