"""State landing-page metadata for search-focused tide directories."""
from __future__ import annotations


STATE_LANDING = {
    "california": {
        "featured_title": "Featured California tide locations",
        "featured": ["oceanside", "huntington-beach", "los-angeles", "san-diego"],
        "guide_title": "California tides and tide schedules",
        "intro": (
            "California tide times vary along a long coastline. Use these California tides pages "
            "to check today’s high and low tides, compare a California tide schedule, and open "
            "local tide charts. Southern California tide tables and SoCal tides links are grouped "
            "below for faster planning."
        ),
        "meta_description": (
            "Check California tide times, high and low tides, local tide charts and tide schedules "
            "for Southern and Northern California coastal locations."
        ),
        "regions": [
            {
                "key": "southern-california",
                "title": "Southern California Tides",
                "slugs": [
                    "san-diego",
                    "la-jolla",
                    "oceanside",
                    "laguna-beach",
                    "newport-beach",
                    "huntington-beach",
                    "los-angeles",
                    "santa-monica",
                    "malibu",
                ],
            },
            {
                "key": "northern-california",
                "title": "Northern California Tides",
                "slugs": ["half-moon-bay", "san-francisco", "santa-cruz", "monterey"],
            },
        ],
    },
    "florida": {
        "featured_title": "Featured Florida tide locations",
        "featured": ["miami-beach", "clearwater-beach"],
        "guide_title": "Florida tides and tide schedules",
        "intro": (
            "Florida tide times differ between the Atlantic coast, Gulf Coast and Keys. Use these "
            "Florida tides pages to check today’s high and low tides, open local tide charts, and "
            "compare a Florida tide schedule before viewing a detailed coastal forecast."
        ),
        "meta_description": (
            "Check Florida tide times, high and low tides, local tide charts and tide schedules "
            "across South Florida, the Gulf Coast, Atlantic coast and Keys."
        ),
        "regions": [
            {
                "key": "south-florida",
                "title": "South Florida Tides",
                "slugs": ["miami-beach", "fort-lauderdale"],
            },
            {
                "key": "gulf-coast",
                "title": "Gulf Coast Tides",
                "slugs": [
                    "clearwater-beach",
                    "st-pete-beach",
                    "tampa-bay",
                    "naples",
                    "sanibel-island",
                    "destin",
                    "panama-city-beach",
                ],
            },
            {
                "key": "atlantic-keys",
                "title": "Atlantic Coast & Keys Tides",
                "slugs": ["key-west", "cocoa-beach", "daytona-beach"],
            },
        ],
    },
}


def state_landing_config(state_slug: str) -> dict | None:
    return STATE_LANDING.get(state_slug)


def items_for_slugs(items: list[dict], slugs: list[str]) -> list[dict]:
    by_slug = {item["slug"]: item for item in items}
    return [by_slug[slug] for slug in slugs if slug in by_slug]


def state_region_items(state_slug: str, region_key: str, items: list[dict]) -> list[dict]:
    config = state_landing_config(state_slug)
    if not config:
        return []
    for region in config.get("regions", []):
        if region.get("key") == region_key:
            return items_for_slugs(items, region.get("slugs", []))
    return []
