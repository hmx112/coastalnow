"""Location configuration for CoastalNow tide pages.

Adding a location should normally require only a new entry here. The renderer in
``generate_tides.py`` supplies the NOAA data and the shared template supplies the
page layout.
"""

LOCATIONS = {
    "san-diego": {
        "slug": "san-diego",
        "name": "San Diego",
        "state": "California",
        "state_slug": "california",
        "station": "9410170",
        "station_name": "San Diego, CA",
        "latitude": 32.71419,
        "longitude": -117.17358,
        "timezone": "America/Los_Angeles",
        "time_label": "Pacific time",
        "datum": "MLLW",
        "units": "english",
        "units_label": "Feet",
        "page_path": "tides/california/san-diego/index.html",
        "data_path": "data/san-diego.json",
        "page_title": "San Diego Tide Times Today | CoastalNow",
        "meta_description": (
            "San Diego high and low tide times today, tide curve and 7-day NOAA "
            "tide outlook for San Diego, California."
        ),
        "hero_copy": (
            "Today’s high and low tide times, tide curve and 7-day outlook in one quick view."
        ),
        "local_guide": (
            "San Diego’s coastline experiences mixed tides, with two high tides and two low tides "
            "on many days. Checking both tide time and height is useful before shoreline walks, "
            "fishing, boating and other coastal activities."
        ),
        "nearby": [
            {"name": "La Jolla", "slug": "la-jolla"},
            {"name": "Oceanside", "slug": "oceanside"},
            {"name": "Newport Beach", "slug": "newport-beach"},
            {"name": "Laguna Beach", "slug": "laguna-beach"},
            {"name": "Santa Monica", "slug": "santa-monica"},
        ],
    },
    "los-angeles": {
        "slug": "los-angeles",
        "name": "Los Angeles",
        "state": "California",
        "state_slug": "california",
        "station": "9410660",
        "station_name": "Los Angeles, CA",
        "latitude": 33.72,
        "longitude": -118.272,
        "timezone": "America/Los_Angeles",
        "time_label": "Pacific time",
        "datum": "MLLW",
        "units": "english",
        "units_label": "Feet",
        "page_path": "tides/california/los-angeles/index.html",
        "data_path": "data/los-angeles.json",
        "page_title": "Los Angeles Tide Times Today | CoastalNow",
        "meta_description": (
            "Los Angeles high and low tide times today, tide curve and 7-day NOAA "
            "tide outlook for Los Angeles, California."
        ),
        "hero_copy": (
            "Today’s high and low tide times, tide curve and 7-day outlook in one quick view."
        ),
        "local_guide": (
            "Los Angeles coastal waters commonly experience two high tides and two low tides of "
            "unequal height each day. Checking tide time and height is useful before beach walks, "
            "fishing, boating and other coastal activities."
        ),
        "nearby": [
            {"name": "Long Beach", "slug": "long-beach"},
            {"name": "Santa Monica", "slug": "santa-monica"},
            {"name": "Redondo Beach", "slug": "redondo-beach"},
            {"name": "Newport Beach", "slug": "newport-beach"},
            {"name": "Malibu", "slug": "malibu"},
        ],
    },
}
