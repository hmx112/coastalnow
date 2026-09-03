import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class PinterestRssTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "slug": "san-diego",
            "name": "San Diego",
            "state": "California",
            "state_slug": "california",
            "release_date": date(2026, 8, 31),
            "fishing_enabled": True,
            "surfing_enabled": True,
        }

    def test_tide_and_fishing_records_use_claimed_domain_and_evergreen_copy(self):
        from pinterest.rss import pin_record

        tide = pin_record(self.location, "tides")
        fishing = pin_record(self.location, "fishing")
        self.assertEqual(tide["link"], "https://coastalnowtides.com/tides/california/san-diego/")
        self.assertEqual(fishing["link"], "https://coastalnowtides.com/tides/california/san-diego/fishing/")
        for record in (tide, fishing):
            self.assertTrue(record["image_url"].startswith("https://coastalnowtides.com/pinterest/images/"))
            combined = (record["title"] + " " + record["description"]).lower()
            for forbidden in ("88", " mph", " ft", "°f", "today's score", "catch probability"):
                self.assertNotIn(forbidden, combined)

    def test_feed_is_rss_2_and_each_item_has_exactly_one_media_content(self):
        from pinterest.rss import build_rss

        xml = build_rss("tides", [self.location])
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.attrib["version"], "2.0")
        item = root.find("./channel/item")
        self.assertIsNotNone(item)
        media = [child for child in item if child.tag.endswith("content")]
        self.assertEqual(len(media), 1)
        self.assertEqual(media[0].attrib["type"], "image/png")
        self.assertEqual(media[0].attrib["width"], "1000")
        self.assertEqual(media[0].attrib["height"], "1500")
        self.assertEqual(item.findtext("link"), "https://coastalnowtides.com/tides/california/san-diego/")

    def test_fishing_feed_skips_locations_when_fishing_is_not_enabled(self):
        from pinterest.rss import build_rss

        item = {**self.location, "fishing_enabled": False}
        xml = build_rss("fishing", [item])
        root = ET.fromstring(xml)
        self.assertEqual(root.findall("./channel/item"), [])

    def test_unknown_feed_kind_fails(self):
        from pinterest.rss import build_rss

        with self.assertRaises(ValueError):
            build_rss("swimming", [self.location])


if __name__ == "__main__":
    unittest.main()
