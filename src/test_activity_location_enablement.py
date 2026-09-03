import unittest

from activities.paths import activity_page_paths_for_location
from activities.registry import ACTIVITIES, activity_enabled_for_location, enabled_activities_for_location
from locations import LOCATIONS


PILOT = {
    "san-diego",
    "la-jolla",
    "huntington-beach",
    "santa-cruz",
    "malibu",
    "half-moon-bay",
    "cocoa-beach",
    "daytona-beach",
    "wrightsville-beach",
    "nags-head",
}


class ActivityLocationEnablementTests(unittest.TestCase):
    def test_surfing_enabled_only_for_pilot_locations(self):
        surfing = ACTIVITIES["surfing"]
        self.assertTrue(surfing["enabled"])
        self.assertEqual(set(surfing["location_allowlist"]), PILOT)
        for slug in LOCATIONS:
            with self.subTest(slug=slug):
                self.assertEqual(activity_enabled_for_location(surfing, slug), slug in PILOT)

    def test_fishing_remains_enabled_for_all_locations(self):
        for slug, location in LOCATIONS.items():
            with self.subTest(slug=slug):
                enabled = {item["slug"] for item in enabled_activities_for_location(location)}
                self.assertIn("fishing", enabled)
                self.assertEqual("surfing" in enabled, slug in PILOT)

    def test_paths_follow_location_enablement(self):
        self.assertEqual(
            set(activity_page_paths_for_location(LOCATIONS["san-diego"])),
            {"fishing", "surfing"},
        )
        self.assertEqual(
            set(activity_page_paths_for_location(LOCATIONS["key-west"])),
            {"fishing"},
        )


if __name__ == "__main__":
    unittest.main()
