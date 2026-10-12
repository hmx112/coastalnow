"""State landing-page metadata for search-focused tide directories."""
from __future__ import annotations


STATE_LANDING = {
    "california": {
        "featured_title": "Featured California tide locations",
        "featured": [
            "oceanside",
            "huntington-beach",
            "malibu",
            "long-beach",
            "dana-point",
            "los-angeles",
            "san-diego",
        ],
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
                    "dana-point",
                    "laguna-beach",
                    "newport-beach",
                    "huntington-beach",
                    "seal-beach",
                    "long-beach",
                    "redondo-beach",
                    "los-angeles",
                    "santa-monica",
                    "malibu",
                    "ventura",
                    "santa-barbara",
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
        "featured": [
            "miami-beach",
            "clearwater-beach",
            "key-biscayne",
            "west-palm-beach",
            "fort-lauderdale",
            "key-west",
        ],
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
                "slugs": [
                    "miami-beach",
                    "key-biscayne",
                    "fort-lauderdale",
                    "pompano-beach",
                    "west-palm-beach",
                ],
            },
            {
                "key": "gulf-coast",
                "title": "Gulf Coast Tides",
                "slugs": [
                    "clearwater-beach",
                    "st-pete-beach",
                    "tampa-bay",
                    "sarasota",
                    "fort-myers-beach",
                    "sanibel-island",
                    "naples",
                    "marco-island",
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
    "north-carolina": {
        "featured_title": "Featured North Carolina tide locations",
        "featured": ["nags-head", "cape-hatteras", "wrightsville-beach", "emerald-isle"],
        "guide_title": "North Carolina tides: Outer Banks and southern beaches",
        "intro": (
            "Find today's high and low tides on North Carolina's Outer Banks and "
            "southern beaches. Tidal timing and height differ from place to place, "
            "especially across inlets and ocean-facing shorelines. Open a location "
            "for the seven-day NOAA prediction, its reference station and any "
            "nearby-station limitations before planning a coastal visit."
        ),
        "meta_description": (
            "Compare North Carolina tide times, high and low tides and 7-day "
            "charts for Outer Banks, Crystal Coast and southern beach locations."
        ),
        "regions": [
            {
                "key": "outer-banks",
                "title": "Outer Banks Tide Times",
                "slugs": ["corolla", "kitty-hawk", "kill-devil-hills", "nags-head",
                          "cape-hatteras", "ocracoke"],
            },
            {
                "key": "southern-north-carolina",
                "title": "Crystal Coast and Southern North Carolina Tides",
                "slugs": ["emerald-isle", "topsail-beach", "wrightsville-beach",
                          "carolina-beach", "holden-beach"],
            },
        ],
    },
    "south-carolina": {
        "featured_title": "Featured South Carolina tide locations",
        "featured": ["myrtle-beach", "hilton-head", "folly-beach", "isle-of-palms"],
        "guide_title": "South Carolina tides: Grand Strand and Lowcountry",
        "intro": (
            "Compare South Carolina tide times from the Grand Strand near Myrtle "
            "Beach to the Lowcountry islands. Each local Tide page shows the next "
            "high and low tide, a seven-day schedule, and the exact NOAA station "
            "used. Check the source details when comparing communities, because "
            "predictions at one station do not represent every nearby waterway."
        ),
        "meta_description": (
            "Explore South Carolina tide times and NOAA charts for Myrtle Beach, "
            "Hilton Head, Folly Beach and nearby Grand Strand and Lowcountry shores."
        ),
        "regions": [
            {
                "key": "grand-strand",
                "title": "Grand Strand Tide Times",
                "slugs": ["north-myrtle-beach", "myrtle-beach", "pawleys-island"],
            },
            {
                "key": "lowcountry",
                "title": "Charleston Area and Lowcountry Tides",
                "slugs": ["isle-of-palms", "folly-beach", "kiawah-island",
                          "edisto-beach", "hilton-head"],
            },
        ],
    },
    "oregon": {
        "featured_title": "Featured Oregon tide locations",
        "featured": ["cannon-beach", "seaside", "lincoln-city"],
        "guide_title": "Oregon Coast tides and local NOAA source coverage",
        "intro": (
            "Find predicted high and low tides for Cannon Beach, Seaside and "
            "Lincoln City on the Oregon Coast. Compare their seven-day schedules "
            "and read the NOAA source details for each location. Some coastal "
            "pages use a nearby reference station rather than a station at the "
            "beach itself; those limits are disclosed on the Tide page."
        ),
        "meta_description": (
            "See Oregon Coast tide times and seven-day NOAA-based forecasts for "
            "Cannon Beach, Seaside and Lincoln City, with station source details."
        ),
        "regions": [
            {
                "key": "northern-oregon",
                "title": "Northern Oregon Coast Tides",
                "slugs": ["cannon-beach", "seaside"],
            },
            {
                "key": "central-oregon",
                "title": "Central Oregon Coast Tides",
                "slugs": ["lincoln-city"],
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
