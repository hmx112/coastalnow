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

TIMEZONE_BY_SLUG = {
    "destin": "America/Chicago",
    "panama-city-beach": "America/Chicago",
}

TIMEZONE_BY_STATE = {
    "CA": "America/Los_Angeles",
    "OR": "America/Los_Angeles",
    "WA": "America/Los_Angeles",
}


def _timezone_for(item):
    return (
        item.get("timezone")
        or TIMEZONE_BY_SLUG.get(item.get("slug"))
        or TIMEZONE_BY_STATE.get(item.get("state_code"), "America/New_York")
    )


def _time_label_for(timezone):
    if timezone == "America/Los_Angeles":
        return "Pacific time"
    if timezone == "America/Chicago":
        return "Central time"
    if timezone == "America/New_York":
        return "Eastern time"
    return "Local time"


def _format_distance_miles(value) -> str:
    distance = float(value)
    return str(int(distance)) if distance.is_integer() else f"{distance:g}"


def coverage_disclosure(location: dict) -> str:
    """Explain when a page uses a nearby/regional NOAA station instead of a local one."""
    if location.get("coverage_mode", "local") != "nearby-noaa":
        return ""
    name = location.get("name", "This location")
    station_name = location.get("station_name", "the configured NOAA station")
    distance = location.get("coverage_distance_miles")
    distance_text = ""
    if distance is not None:
        distance_text = f", about {_format_distance_miles(distance)} miles away"
    return (
        f"Nearby NOAA station: Tide predictions for {name} use NOAA station "
        f"{station_name}{distance_text}. Local tide timing and height may differ."
    )


def _load_locations():
    raw = json.loads((ROOT / "data" / "locations.json").read_text(encoding="utf-8"))
    locations = {}
    for item in raw:
        slug = item["slug"]
        live_config = LIVE_NOAA_CONFIG.get(slug, {})
        station_id = live_config.get("station_id", item.get("station_id"))
        station_name = live_config.get("station_name") or item.get("station_name") or f'{item["name"]}, {item["state_code"]}'
        prediction_mode = live_config.get("prediction_mode", "harmonic")
        coverage_mode = live_config.get("coverage_mode", "local")
        coverage_distance_miles = live_config.get("coverage_distance_miles")
        timezone = _timezone_for(item)
        coverage = coverage_disclosure({
            "name": item["name"],
            "station_name": station_name,
            "coverage_mode": coverage_mode,
            "coverage_distance_miles": coverage_distance_miles,
        })
        base_guide = f'{item["name"]} coastal conditions can change throughout the day. Check tide time and height before shoreline walks, fishing, boating and other coastal activities.'
        locations[slug] = {
            **item,
            "station_id": station_id,
            "station": station_id,
            "prediction_mode": prediction_mode,
            "coverage_mode": coverage_mode,
            "coverage_distance_miles": coverage_distance_miles,
            "timezone": timezone,
            "page_path": f'tides/{item["state_slug"]}/{slug}/index.html',
            "data_path": f"data/{slug}.json",
            "page_title": f'{item["name"]} Tide Times Today | CoastalNow',
            "meta_description": f'{item["name"]} tide times and tide outlook for {item["name"]}, {item["state"]}.',
            "hero_copy": coverage or "Today’s tide times and a quick coastal outlook.",
            "local_guide": base_guide + ((" " + coverage) if coverage else ""),
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
            "prediction_mode": "harmonic", "coverage_mode": "local", "coverage_distance_miles": None,
            "page_path": "tides/california/los-angeles/index.html", "data_path": "data/los-angeles.json",
            "page_title": "Los Angeles Tide Times Today | CoastalNow",
            "meta_description": "Los Angeles tide times and tide outlook for Los Angeles, California.",
            "hero_copy": "Today’s tide times and a quick coastal outlook.", "time_label": "Pacific time",
            "local_guide": "Los Angeles coastal conditions can change throughout the day. Check tide time and height before shoreline walks, fishing, boating and other coastal activities.", "nearby": [],
            "units_label": "Feet", "status": "Live NOAA",
        }
    return locations


LOCATIONS = _load_locations()
