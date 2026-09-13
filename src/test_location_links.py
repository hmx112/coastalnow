import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from location_links import nearest_same_state_locations


class LocationLinksTests(unittest.TestCase):
    def test_nearby_links_use_nearest_live_locations_in_same_state(self):
        locations = {
            "origin": {
                "slug": "origin",
                "name": "Origin",
                "state_slug": "california",
                "status": "Live NOAA",
                "latitude": 33.0,
                "longitude": -117.0,
            },
            "near": {
                "slug": "near",
                "name": "Near",
                "state_slug": "california",
                "status": "Live NOAA",
                "latitude": 33.1,
                "longitude": -117.0,
            },
            "far": {
                "slug": "far",
                "name": "Far",
                "state_slug": "california",
                "status": "Live NOAA",
                "latitude": 35.0,
                "longitude": -117.0,
            },
            "preview": {
                "slug": "preview",
                "name": "Preview",
                "state_slug": "california",
                "status": "Preview",
                "latitude": 33.05,
                "longitude": -117.0,
            },
            "other": {
                "slug": "other",
                "name": "Other",
                "state_slug": "florida",
                "status": "Live NOAA",
                "latitude": 33.01,
                "longitude": -117.0,
            },
        }
        result = nearest_same_state_locations(locations["origin"], locations, limit=4)
        self.assertEqual([item["slug"] for item in result], ["near", "far"])

    def test_nearby_links_break_equal_distance_ties_by_name(self):
        locations = {
            "origin": {
                "slug": "origin",
                "name": "Origin",
                "state_slug": "florida",
                "status": "Live NOAA",
                "latitude": 27.0,
                "longitude": -82.0,
            },
            "beta": {
                "slug": "beta",
                "name": "Beta Beach",
                "state_slug": "florida",
                "status": "Live NOAA",
                "latitude": 27.1,
                "longitude": -82.0,
            },
            "alpha": {
                "slug": "alpha",
                "name": "Alpha Beach",
                "state_slug": "florida",
                "status": "Live NOAA",
                "latitude": 26.9,
                "longitude": -82.0,
            },
        }
        result = nearest_same_state_locations(locations["origin"], locations, limit=2)
        self.assertEqual([item["slug"] for item in result], ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
