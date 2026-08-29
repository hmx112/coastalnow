import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.paths import (
    activity_data_path,
    activity_hub_path,
    activity_page_path,
    activity_page_paths_for_location,
)
from activities.registry import ACTIVITIES, enabled_activities


class ActivityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "state_slug": "texas",
            "slug": "galveston",
            "name": "Galveston",
        }

    def test_fishing_is_the_only_enabled_phase_one_activity(self):
        enabled = enabled_activities()
        self.assertEqual([item["slug"] for item in enabled], ["fishing"])
        fishing = ACTIVITIES["fishing"]
        self.assertEqual(fishing["label"], "Fishing")
        self.assertTrue(fishing["enabled"])
        self.assertTrue(fishing["scorer_version"])
        self.assertTrue(fishing["requires"])

    def test_activity_paths_follow_the_existing_tide_hierarchy(self):
        self.assertEqual(
            activity_page_path(self.location, "fishing"),
            "tides/texas/galveston/fishing/index.html",
        )
        self.assertEqual(
            activity_data_path(self.location, "fishing"),
            "data/activities/fishing/galveston.json",
        )
        self.assertEqual(activity_hub_path("fishing"), "fishing/index.html")

    def test_new_location_expands_to_every_enabled_activity(self):
        fake_registry = {
            "fishing": {
                "slug": "fishing",
                "label": "Fishing",
                "enabled": True,
                "scorer_version": "fishing-v1",
                "requires": ("tide",),
            },
            "surfing": {
                "slug": "surfing",
                "label": "Surfing",
                "enabled": True,
                "scorer_version": "surfing-test-v1",
                "requires": ("waves",),
            },
            "beach": {
                "slug": "beach",
                "label": "Beach",
                "enabled": False,
                "scorer_version": "beach-test-v1",
                "requires": ("weather",),
            },
        }
        enabled = enabled_activities(fake_registry)
        self.assertEqual([item["slug"] for item in enabled], ["fishing", "surfing"])
        paths = activity_page_paths_for_location(self.location, fake_registry)
        self.assertEqual(
            paths,
            {
                "fishing": "tides/texas/galveston/fishing/index.html",
                "surfing": "tides/texas/galveston/surfing/index.html",
            },
        )

    def test_registry_does_not_contain_a_location_inventory(self):
        for item in ACTIVITIES.values():
            self.assertNotIn("locations", item)
            self.assertNotIn("location_slugs", item)


if __name__ == "__main__":
    unittest.main()
