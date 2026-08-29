"""Single location catalog used by NOAA pages and directory generation."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE_NOAA = {"san-diego", "los-angeles"}


def _load_locations():
    raw = json.loads((ROOT / "data" / "locations.json").read_text(encoding="utf-8"))
    locations = {}
    for item in raw:
        slug = item["slug"]
        locations[slug] = {
            **item,
            "station": item.get("station_id"),
            "page_path": f'tides/{item["state_slug"]}/{slug}/index.html',
            "data_path": f"data/{slug}.json",
            "page_title": f'{item["name"]} Tide Times Today | CoastalNow',
            "meta_description": f'{item["name"]} tide times and tide outlook for {item["name"]}, {item["state"]}.',
            "hero_copy": "Today’s tide times and a quick coastal outlook.",
            "local_guide": f'{item["name"]} coastal conditions can change throughout the day. Check tide time and height before shoreline walks, fishing, boating and other coastal activities.',
            "nearby": [],
            "time_label": "Local time",
            "units_label": "Feet",
            "station_name": item.get("station_name") or f'{item["name"]}, {item["state_code"]}',
            "status": "Live NOAA" if slug in LIVE_NOAA else "Preview",
        }
    if "los-angeles" not in locations:
        locations["los-angeles"] = {
            "state": "California", "state_code": "CA", "state_slug": "california",
            "name": "Los Angeles", "slug": "los-angeles", "priority": "A",
            "station_id": "9410660", "station": "9410660", "station_name": "Los Angeles, CA",
            "latitude": 33.72, "longitude": -118.272, "timezone": "America/Los_Angeles",
            "datum": "MLLW", "units": "english", "source": "NOAA/NOS/CO-OPS",
            "page_path": "tides/california/los-angeles/index.html", "data_path": "data/los-angeles.json",
            "page_title": "Los Angeles Tide Times Today | CoastalNow",
            "meta_description": "Los Angeles tide times and tide outlook for Los Angeles, California.",
            "hero_copy": "Today’s tide times and a quick coastal outlook.", "time_label": "Local time",
            "local_guide": "Los Angeles coastal conditions can change throughout the day. Check tide time and height before shoreline walks, fishing, boating and other coastal activities.", "nearby": [],
            "units_label": "Feet", "status": "Live NOAA",
        }
    return locations


LOCATIONS = _load_locations()
