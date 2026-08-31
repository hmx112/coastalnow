"""Pinterest marketing catalog projected from CoastalNow's location source of truth."""
from __future__ import annotations

import json
from pathlib import Path

from activities.registry import enabled_activities


def load_pinterest_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("pinterest.json must contain an object")
    if not isinstance(config.get("enabled"), bool):
        raise ValueError("Pinterest enabled must be a boolean")
    if config.get("locations_per_day") != 1:
        raise ValueError("Pinterest v1 requires locations_per_day=1")
    if config.get("enabled") and not config.get("start_date"):
        raise ValueError("Enabled Pinterest config requires start_date")
    if not isinstance(config.get("launch_order"), list):
        raise ValueError("Pinterest launch_order must be a list")
    return config


def validate_launch_order(launch_order: list[str], locations: dict) -> None:
    if len(launch_order) != len(set(launch_order)):
        raise ValueError("Pinterest launch_order contains duplicate slugs")
    unknown = [slug for slug in launch_order if slug not in locations]
    if unknown:
        raise ValueError(f"Pinterest launch_order contains unknown slugs: {unknown}")
    missing = [slug for slug in locations if slug not in launch_order]
    if missing:
        raise ValueError(f"Pinterest launch_order is missing slugs: {missing}")


def build_catalog(locations: dict, config: dict) -> list[dict]:
    order = config["launch_order"]
    validate_launch_order(order, locations)
    fishing_enabled = any(item["slug"] == "fishing" for item in enabled_activities())
    catalog = []
    for index, slug in enumerate(order):
        location = locations[slug]
        catalog.append(
            {
                "slug": slug,
                "name": location["name"],
                "state": location["state"],
                "state_slug": location["state_slug"],
                "release_index": index,
                "tide_page_path": location["page_path"],
                "fishing_enabled": fishing_enabled,
            }
        )
    return catalog
