import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS
from site_generator import build_directory_pages

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "data" / "locations.json"
SITE_GENERATOR = ROOT / "site_generator.py"


class ActivityGeographyTests(unittest.TestCase):
    def test_locations_json_is_the_only_geography_catalog(self):
        raw = json.loads(CATALOG.read_text(encoding="utf-8"))
        raw_slugs = {item["slug"] for item in raw}
        self.assertEqual(raw_slugs, set(LOCATIONS))
        self.assertEqual(len(raw), len(LOCATIONS))

    def test_every_location_has_valid_activity_points(self):
        raw = json.loads(CATALOG.read_text(encoding="utf-8"))
        for item in raw:
            activity = item.get("activity")
            self.assertIsInstance(activity, dict, item["slug"])
            for field in ("shore_point", "marine_point"):
                point = activity.get(field) if activity else None
                self.assertIsInstance(point, dict, f'{item["slug"]}:{field}')
                lat = point.get("latitude") if point else None
                lon = point.get("longitude") if point else None
                self.assertIsInstance(lat, (int, float), f'{item["slug"]}:{field}:latitude')
                self.assertIsInstance(lon, (int, float), f'{item["slug"]}:{field}:longitude')
                self.assertTrue(math.isfinite(lat), f'{item["slug"]}:{field}:latitude')
                self.assertTrue(math.isfinite(lon), f'{item["slug"]}:{field}:longitude')
                self.assertGreaterEqual(lat, -90, item["slug"])
                self.assertLessEqual(lat, 90, item["slug"])
                self.assertGreaterEqual(lon, -180, item["slug"])
                self.assertLessEqual(lon, 180, item["slug"])
            bearing = activity.get("coast_bearing") if activity else None
            if bearing is not None:
                self.assertIsInstance(bearing, (int, float), item["slug"])
                self.assertTrue(math.isfinite(bearing), item["slug"])
                self.assertGreaterEqual(bearing, 0, item["slug"])
                self.assertLess(bearing, 360, item["slug"])

    def test_loaded_locations_preserve_activity_metadata(self):
        for slug, location in LOCATIONS.items():
            self.assertIn("activity", location, slug)
            self.assertIn("shore_point", location["activity"], slug)
            self.assertIn("marine_point", location["activity"], slug)

    def test_homepage_location_count_is_catalog_derived(self):
        source = SITE_GENERATOR.read_text(encoding="utf-8")
        self.assertNotIn("Search 51 coastal locations", source)
        home = build_directory_pages()["index.html"]
        self.assertIn(f"Search {len(LOCATIONS)} coastal locations", home)


if __name__ == "__main__":
    unittest.main()
