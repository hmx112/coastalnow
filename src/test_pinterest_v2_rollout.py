"""Pinterest 2026-11 recovery and design v2: no bulk reposts or stale data."""
from __future__ import annotations

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from generate_pinterest import generate
from locations import LOCATIONS
from pinterest.catalog import build_catalog
from pinterest.creative_v2 import PALETTES, render_pin_v2
from pinterest.rss import MEDIA_NS, pin_record
from pinterest.schedule import (
    released_locations, released_surfing_locations, released_creative_v2_pilots,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "data" / "pinterest.json"
PUBLIC = ROOT / "public"
OLD_CITIES = (
    "san-diego", "miami-beach", "myrtle-beach", "key-west", "san-francisco",
    "virginia-beach", "clearwater-beach", "huntington-beach",
    "cape-hatteras", "destin", "santa-monica", "hilton-head", "daytona-beach",
)


def config_and_catalog():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return config, build_catalog(LOCATIONS, config)


def fake_render(item, kind, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"mock image for feed metadata test")
    return path


class PinterestCreativeRolloutTests(unittest.TestCase):
    def test_catalog_exactly_matches_published_locations_without_rewriting_history(self):
        config, catalog = config_and_catalog()
        self.assertEqual(len(LOCATIONS), 67)
        self.assertEqual(len(config["launch_order"]), 67)
        self.assertEqual(len(set(config["launch_order"])), 67)
        self.assertEqual(config["launch_order"][:13], list(OLD_CITIES))
        self.assertEqual(config["legacy_location_count"], 13)
        self.assertEqual(config["legacy_surfing_count"], 10)
        self.assertEqual(len(config["surfing_launch_order"]), 16)
        self.assertEqual(len(set(config["surfing_launch_order"])), 16)
        self.assertEqual(len(catalog), 67)
        for slug in OLD_CITIES:
            for kind in ("tides", "fishing"):
                self.assertTrue((PUBLIC / "pinterest" / "images" / f"{slug}-{kind}.png").exists())
        for slug in config["surfing_launch_order"][:10]:
            self.assertTrue((PUBLIC / "pinterest" / "images" / f"{slug}-surfing.png").exists())

    def test_backfill_is_one_new_coastal_location_per_day_not_a_bulk_dump(self):
        config, catalog = config_and_catalog()
        before = released_locations(catalog, config, date(2026, 11, 10))
        day1 = released_locations(catalog, config, date(2026, 11, 11))
        day2 = released_locations(catalog, config, date(2026, 11, 12))
        self.assertEqual(len(before), 13)
        self.assertEqual(len(day1), 14)
        self.assertEqual(len(day2), 15)
        self.assertEqual(day1[-1]["slug"], "galveston")
        self.assertEqual(day2[-1]["slug"], "jacksonville-beach")
        self.assertEqual(before[0]["release_date"], date(2026, 8, 31))
        self.assertEqual(before[-1]["release_date"], date(2026, 9, 12))
        surf_before = released_surfing_locations(catalog, config, date(2026, 11, 10))
        surf_day1 = released_surfing_locations(catalog, config, date(2026, 11, 11))
        self.assertEqual(len(surf_before), 10)
        self.assertEqual(len(surf_day1), 11)
        self.assertEqual(surf_day1[-1]["slug"], "oceanside")
        self.assertEqual(surf_before[0]["release_date"], date(2026, 9, 3))

    def test_six_v2_pilots_are_evergreen_staggered_and_on_previously_published_destinations(self):
        config, catalog = config_and_catalog()
        p0 = released_creative_v2_pilots(catalog, config, date(2026, 11, 3))
        p1 = released_creative_v2_pilots(catalog, config, date(2026, 11, 4))
        p6 = released_creative_v2_pilots(catalog, config, date(2026, 11, 9))
        self.assertEqual(p0, [])
        self.assertEqual(len(p1), 1)
        self.assertEqual(len(p6), 6)
        self.assertEqual(len({(p["kind"], p["slug"]) for p in p6}), 6)
        for pilot in p6:
            slug, kind = pilot["slug"], pilot["kind"]
            path = PUBLIC / "pinterest" / "images" / f"{slug}-{kind}.png"
            self.assertTrue(path.exists(), str(path))
            self.assertEqual(pilot["creative_version"], "v2")
        self.assertEqual({p["kind"] for p in p6}, set(PALETTES))

    def test_v2_metadata_is_new_identified_image_with_utm_not_a_rewritten_legacy_guid(self):
        config, catalog = config_and_catalog()
        pilot = released_creative_v2_pilots(catalog, config, date(2026, 11, 4))[0]
        new = pin_record(pilot, "tides")
        legacy = pin_record({**pilot, "creative_version": "v1"}, "tides")
        self.assertEqual(legacy["guid"], "coastalnow:pinterest:tides:huntington-beach:v1")
        self.assertTrue(legacy["image_url"].endswith("huntington-beach-tides.png"))
        self.assertEqual(new["guid"], "coastalnow:pinterest:tides:huntington-beach:v2")
        self.assertTrue(new["image_url"].endswith("huntington-beach-tides-v2.png"))
        self.assertEqual(new["link"].split("?")[0], legacy["link"])
        self.assertIn("utm_source=pinterest", new["link"])
        self.assertIn("utm_campaign=coastalnow_creative_v2", new["link"])
        self.assertIn("utm_content=tides_huntington-beach", new["link"])
        self.assertIn("Low Tide Guide", new["title"])
        self.assertNotIn("2026", new["description"])
        self.assertNotIn("ft", new["description"])

    def test_first_v2_pin_is_one_new_image_and_preserves_old_files_and_feeds(self):
        config, _ = config_and_catalog()
        with tempfile.TemporaryDirectory() as tmp, patch("generate_pinterest.render_pin_v2", side_effect=fake_render):
            root = Path(tmp)
            existing = root / "pinterest" / "images" / "huntington-beach-tides.png"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"published-immutable-original")
            result = generate(date(2026, 11, 4), root, CONFIG)
            self.assertEqual(len(result["released_slugs"]), 13)
            self.assertEqual(len(result["surfing_released_slugs"]), 10)
            self.assertEqual(result["creative_v2_pilots_released"], ["tides:huntington-beach"])
            self.assertEqual(existing.read_bytes(), b"published-immutable-original")
            self.assertTrue((root / "pinterest" / "images" / "huntington-beach-tides-v2.png").is_file())
            self.assertFalse((root / "pinterest" / "images" / "galveston-tides.png").exists())
            for kind, expected in (("tides", 14), ("fishing", 13), ("surfing", 10)):
                feed = root / "pinterest" / "rss" / f"{kind}.xml"
                xml = ET.parse(feed)
                items = xml.findall("./channel/item")
                self.assertEqual(len(items), expected)
                identities = [item.findtext("guid") for item in items]
                self.assertEqual(len(identities), len(set(identities)))
                self.assertTrue(all(len(item.findall(f"{{{MEDIA_NS}}}content")) == 1 for item in items))
            tide_items = ET.parse(root / "pinterest" / "rss" / "tides.xml").findall("./channel/item")
            self.assertEqual(tide_items[0].findtext("guid"), "coastalnow:pinterest:tides:huntington-beach:v2")
            self.assertIn("2026", tide_items[0].findtext("pubDate") or "")

    def test_v2_photo_first_creatives_are_1000x1500_and_three_formats_are_distinct(self):
        from pinterest import creative_v2
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            creative_v2, "_load_photo_background", side_effect=lambda kind: Image.new("RGB", (1000, 1500), (44, 94, 118))
        ):
            root = Path(tmp)
            hashes = set()
            for kind in ("tides", "fishing", "surfing"):
                item = {"name": "Half Moon Bay", "state": "California", "slug": "half-moon-bay"}
                output = root / (kind + ".png")
                self.assertEqual(render_pin_v2(item, kind, output), output)
                with Image.open(output) as image:
                    self.assertEqual(image.size, (1000, 1500))
                    self.assertEqual(image.format, "PNG")
                    self.assertNotEqual(image.getpixel((100, 1040)), image.getpixel((100, 500)))
                hashes.add(output.read_bytes()[:512])
            self.assertEqual(len(hashes), 3)


if __name__ == "__main__":
    unittest.main()
