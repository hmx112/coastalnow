"""Root-relative links between Tide parents and Activity pages."""
from __future__ import annotations


def tide_parent_url(location: dict) -> str:
    return f'/tides/{location["state_slug"]}/{location["slug"]}/'


def activity_location_url(location: dict, activity_slug: str) -> str:
    return f'/tides/{location["state_slug"]}/{location["slug"]}/{activity_slug}/'


def activity_hub_url(activity_slug: str) -> str:
    return f'/{activity_slug}/'
