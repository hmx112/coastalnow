"""Single location catalog used by NOAA pages and directory generation."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE_NOAA_FILE = ROOT / "data" / "live_noaa.json"

def _load_live_noaa_config():
    if not LIVE_NOAA_FILE.exists():
        return {}
    raw = json.loads(LIVE_NOAA_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("live_noaa.json must contain a JSON object keyed by location slug")
    return raw

LIVE_NOAA_CONFIG = _load_live_noaa_config()
LIVE_NOAA = set(LIVE_NOAA_CONFIG)

TIMEZONE_BY_STATE = {
    "CA": "America/Los_Angeles",
    "OR": "America/Los_Angeles",
    "WA": "America/Los_Angeles",
}


def _timezone_for(item):
    return item.get("timezone") or TIMEZONE_BY_STATE.get(item.get("state_code"), "America/New_York")


def _time_label_for(timezone):
    if timezone == "America/Los_Angeles":
        return "Pacific time"
    if timezone == "America/New_York":
        return "Eastern time"
    return "Local time"


def _load_locations():
    raw = json.loads((ROOT / "data" / "locations.json").read_text(encoding="utf-8"))
    locations = {}
    for item in raw:
        slug = item["slug"]
        live_config = LIVE_NOAA_CONFIG.get(slug, {})
        station_id = live_config.get("station_id", item.get("station_id"))
        station_name = live_config.get("station_name") or item.get("station_name") or f'{item["name"]}, {item["state_code"]}'
        prediction_mode = live_config.get("prediction_mode", "harmonic")
        timezone = _timezone_for(item)
        locations[slug] = {
            **item,
            "station_id": station_id,
            "station": station_id,
            "prediction_mode": prediction_mode,
            "timezone": timezone,
            "page_path": f'tides/{item["state_slug"]}/{slug}/index.html',
            "data_path": f"data/{slug}.json",
            "page_title": f'{item["name"]} Tide Times Today | CoastalNow',
            "meta_description": f'{item["name"]} tide times and tide outlook for {item["name"]}, {item["state"]}.',
            "hero_copy": "Today’s tide times and a quick coastal outlook.",
            "local_guide": f'{item["name"]} coastal conditions can change throughout the day. Check tide time and height before shoreline walks, fishing, boating and other coastal activities.',
            "nearby": [],
            "time_label": _time_label_for(timezone),
            "units_label": "Feet",
            "station_name": station_name,
            "status": "Live NOAA" if slug in LIVE_NOAA else "Preview",
        }
    if "los-angeles" not in locations:
        locations["los-angeles"] = {
            "state": "California", "state_code": "CA", "state_slug": "california",
            "name": "Los Angeles", "slug": "los-angeles", "priority": "A",
            "station_id": "9410660", "station": "9410660", "station_name": "Los Angeles, CA",
            "latitude": 33.72, "longitude": -118.272, "timezone": "America/Los_Angeles",
            "datum": "MLLW", "units": "english", "source": "NOAA/NOS/CO-OPS",
            "prediction_mode": "harmonic",
            "page_path": "tides/california/los-angeles/index.html", "data_path": "data/los-angeles.json",
            "page_title": "Los Angeles Tide Times Today | CoastalNow",
            "meta_description": "Los Angeles tide times and tide outlook for Los Angeles, California.",
            "hero_copy": "Today’s tide times and a quick coastal outlook.", "time_label": "Pacific time",
            "local_guide": "Los Angeles coastal conditions can change throughout the day. Check tide time and height before shoreline walks, fishing, boating and other coastal activities.", "nearby": [],
            "units_label": "Feet", "status": "Live NOAA",
        }
    return locations


LOCATIONS = _load_locations()
