import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.registry import ACTIVITIES
from locations import LOCATIONS


class PinterestIdentityAndSurfingTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "slug": "san-diego",
            "name": "San Diego",
            "state": "California",
            "state_slug": "california",
            "release_date": date(2026, 9, 4),
            "fishing_enabled": True,
            "surfing_enabled": True,
        }

    def test_same_feed_rejects_duplicate_guid_link_or_image_identity(self):
        from pinterest.rss import build_rss

        with self.assertRaises(ValueError):
            build_rss("tides", [self.location, dict(self.location)])

    def test_surfing_record_uses_canonical_page_and_stable_identity(self):
        from pinterest.rss import pin_record

        record = pin_record(self.location, "surfing")
        self.assertEqual(
            record["link"],
            "https://coastalnowtides.com/tides/california/san-diego/surfing/",
        )
        self.assertEqual(
            record["image_url"],
            "https://coastalnowtides.com/pinterest/images/san-diego-surfing.png",
        )
        self.assertEqual(record["guid"], "coastalnow:pinterest:surfing:san-diego:v1")
        combined = (record["title"] + " " + record["description"]).lower()
        for forbidden in ("today's score", " mph", " ft", "safe", "alert"):
            self.assertNotIn(forbidden, combined)

    def test_surfing_feed_only_contains_enabled_pilot_locations(self):
        from pinterest.rss import build_rss

        disabled = {
            **self.location,
            "slug": "miami-beach",
            "name": "Miami Beach",
            "state": "Florida",
            "state_slug": "florida",
            "surfing_enabled": False,
        }
        root = ET.fromstring(build_rss("surfing", [self.location, disabled]))
        items = root.findall("./channel/item")
        self.assertEqual(len(items), 1)
        self.assertIn("San Diego", items[0].findtext("title"))
        self.assertIn("/san-diego/surfing/", items[0].findtext("link"))

    def test_catalog_marks_only_surfing_allowlist_locations_enabled(self):
        from pinterest.catalog import build_catalog

        config = {
            "launch_order": list(LOCATIONS),
        }
        # build_catalog validates launch_order against all locations, so use the real
        # configured ordering when available rather than relying on dict order.
        config_path = Path(__file__).resolve().parent / "data" / "pinterest.json"
        import json
        config = json.loads(config_path.read_text(encoding="utf-8"))
        catalog = build_catalog(LOCATIONS, config)
        enabled = {item["slug"] for item in catalog if item.get("surfing_enabled")}
        self.assertEqual(enabled, set(ACTIVITIES["surfing"]["location_allowlist"]))

    def test_surfing_has_independent_one_per_day_pilot_release_schedule(self):
        from pinterest.catalog import build_catalog, load_pinterest_config
        from pinterest.schedule import released_surfing_locations

        config_path = Path(__file__).resolve().parent / "data" / "pinterest.json"
        config = load_pinterest_config(config_path)
        catalog = build_catalog(LOCATIONS, config)

        day_one = released_surfing_locations(catalog, config, date.fromisoformat(config["surfing_start_date"]))
        self.assertEqual(len(day_one), 1)
        self.assertEqual(day_one[0]["slug"], config["surfing_launch_order"][0])
        self.assertTrue(day_one[0]["surfing_enabled"])

        day_two = released_surfing_locations(
            catalog,
            config,
            date.fromisoformat(config["surfing_start_date"]).fromordinal(
                date.fromisoformat(config["surfing_start_date"]).toordinal() + 1
            ),
        )
        self.assertEqual(
            [item["slug"] for item in day_two],
            config["surfing_launch_order"][:2],
        )


if __name__ == "__main__":
    unittest.main()
