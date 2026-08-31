import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS


class PinterestCatalogScheduleTests(unittest.TestCase):
    def config_path(self):
        return Path(__file__).resolve().parent / "data" / "pinterest.json"

    def test_config_launch_order_is_complete_unique_and_starts_with_san_diego(self):
        from pinterest.catalog import load_pinterest_config

        config = load_pinterest_config(self.config_path())
        self.assertTrue(config["enabled"])
        self.assertEqual(config["start_date"], "2026-08-31")
        self.assertEqual(config["locations_per_day"], 1)
        self.assertEqual(config["launch_order"][0], "san-diego")
        self.assertEqual(len(config["launch_order"]), len(set(config["launch_order"])))
        self.assertEqual(set(config["launch_order"]), set(LOCATIONS))

    def test_unknown_or_duplicate_launch_slug_fails(self):
        from pinterest.catalog import validate_launch_order

        with self.assertRaises(ValueError):
            validate_launch_order(["san-diego", "san-diego"], LOCATIONS)
        with self.assertRaises(ValueError):
            validate_launch_order(["not-a-location"], LOCATIONS)

    def test_day_one_releases_only_san_diego_and_day_two_adds_next_location(self):
        from pinterest.catalog import build_catalog, load_pinterest_config
        from pinterest.schedule import released_locations

        config = load_pinterest_config(self.config_path())
        catalog = build_catalog(LOCATIONS, config)
        self.assertEqual(
            [item["slug"] for item in released_locations(catalog, config, date(2026, 8, 31))],
            ["san-diego"],
        )
        released_day_two = released_locations(catalog, config, date(2026, 9, 1))
        self.assertEqual(len(released_day_two), 2)
        self.assertEqual(released_day_two[0]["slug"], "san-diego")
        self.assertEqual(released_day_two[1]["slug"], config["launch_order"][1])

    def test_disabled_config_releases_nothing(self):
        from pinterest.schedule import released_locations

        catalog = [{"slug": "san-diego", "release_index": 0}]
        config = {"enabled": False, "start_date": "2026-08-31", "locations_per_day": 1}
        self.assertEqual(released_locations(catalog, config, date(2026, 9, 5)), [])


if __name__ == "__main__":
    unittest.main()
