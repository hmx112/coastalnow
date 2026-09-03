import hashlib
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class PinterestGenerationTests(unittest.TestCase):
    def config_path(self):
        return Path(__file__).resolve().parent / "data" / "pinterest.json"

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_day_one_generates_only_san_diego_tide_fishing_and_three_valid_feeds(self):
        from generate_pinterest import generate

        with tempfile.TemporaryDirectory() as tmp:
            public_root = Path(tmp)
            result = generate(date(2026, 8, 31), public_root, self.config_path())
            image_names = sorted(path.name for path in (public_root / "pinterest" / "images").glob("*.png"))
            self.assertEqual(image_names, ["san-diego-fishing.png", "san-diego-tides.png"])
            self.assertEqual(result["released_slugs"], ["san-diego"])
            self.assertEqual(result["surfing_released_slugs"], [])
            for feed_name in ("tides.xml", "fishing.xml", "surfing.xml"):
                feed_path = public_root / "pinterest" / "rss" / feed_name
                self.assertTrue(feed_path.exists())
                root = ET.fromstring(feed_path.read_text(encoding="utf-8"))
                expected_items = 0 if feed_name == "surfing.xml" else 1
                self.assertEqual(len(root.findall("./channel/item")), expected_items)
                for item in root.findall("./channel/item"):
                    media = [child for child in item if child.tag.endswith("content")]
                    self.assertEqual(len(media), 1)
                    image_url = media[0].attrib["url"]
                    relative = image_url.removeprefix("https://coastalnowtides.com/")
                    self.assertTrue((public_root / relative).exists(), image_url)

    def test_same_date_regeneration_is_byte_identical(self):
        from generate_pinterest import generate

        with tempfile.TemporaryDirectory() as tmp:
            public_root = Path(tmp)
            generate(date(2026, 8, 31), public_root, self.config_path())
            files = sorted(path for path in (public_root / "pinterest").rglob("*") if path.is_file())
            before = {path.relative_to(public_root): self.digest(path) for path in files}
            generate(date(2026, 8, 31), public_root, self.config_path())
            files = sorted(path for path in (public_root / "pinterest").rglob("*") if path.is_file())
            after = {path.relative_to(public_root): self.digest(path) for path in files}
            self.assertEqual(before, after)

    def test_existing_published_image_is_never_rewritten(self):
        from generate_pinterest import generate

        with tempfile.TemporaryDirectory() as tmp:
            public_root = Path(tmp)
            generate(date(2026, 8, 31), public_root, self.config_path())
            image = public_root / "pinterest" / "images" / "san-diego-tides.png"
            marker = b"already-published-immutable-pin"
            image.write_bytes(marker)

            generate(date(2026, 8, 31), public_root, self.config_path())
            self.assertEqual(image.read_bytes(), marker)

    def test_day_two_retains_san_diego_and_adds_only_second_location(self):
        from generate_pinterest import generate
        from pinterest.catalog import load_pinterest_config

        with tempfile.TemporaryDirectory() as tmp:
            public_root = Path(tmp)
            config = load_pinterest_config(self.config_path())
            second_slug = config["launch_order"][1]
            generate(date(2026, 8, 31), public_root, self.config_path())
            result = generate(date(2026, 9, 1), public_root, self.config_path())
            self.assertEqual(result["released_slugs"], ["san-diego", second_slug])
            image_names = sorted(path.name for path in (public_root / "pinterest" / "images").glob("*.png"))
            self.assertEqual(
                image_names,
                sorted([
                    "san-diego-tides.png",
                    "san-diego-fishing.png",
                    f"{second_slug}-tides.png",
                    f"{second_slug}-fishing.png",
                ]),
            )
            for feed_name in ("tides.xml", "fishing.xml"):
                root = ET.fromstring((public_root / "pinterest" / "rss" / feed_name).read_text(encoding="utf-8"))
                self.assertEqual(len(root.findall("./channel/item")), 2)

    def test_surfing_start_day_adds_only_first_pilot_surfing_pin(self):
        from generate_pinterest import generate
        from pinterest.catalog import load_pinterest_config

        with tempfile.TemporaryDirectory() as tmp:
            public_root = Path(tmp)
            config = load_pinterest_config(self.config_path())
            result = generate(date.fromisoformat(config["surfing_start_date"]), public_root, self.config_path())
            first = config["surfing_launch_order"][0]
            self.assertEqual(result["surfing_released_slugs"], [first])
            self.assertTrue((public_root / "pinterest" / "images" / f"{first}-surfing.png").exists())
            root = ET.fromstring((public_root / "pinterest" / "rss" / "surfing.xml").read_text(encoding="utf-8"))
            items = root.findall("./channel/item")
            self.assertEqual(len(items), 1)
            self.assertIn(f"/{first}/surfing/", items[0].findtext("link"))


if __name__ == "__main__":
    unittest.main()
