import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image


class PinterestRenderTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "slug": "san-diego",
            "name": "San Diego",
            "state": "California",
            "state_slug": "california",
            "fishing_enabled": True,
        }

    def test_pin_text_is_evergreen_and_activity_specific(self):
        from pinterest.render import pin_text

        tide = pin_text(self.item, "tides")
        fishing = pin_text(self.item, "fishing")
        self.assertEqual(tide["location"], "SAN DIEGO")
        self.assertEqual(tide["state"], "CALIFORNIA")
        self.assertEqual(tide["category"], "TIDE TIMES & TIDE CHART")
        self.assertEqual(fishing["category"], "FISHING CONDITIONS & BEST TIMES")
        for payload in (tide, fishing):
            combined = " ".join(payload.values()).lower()
            for forbidden in ("mph", "°f", "%", "2026-", "fishing score 88", "tide height"):
                self.assertNotIn(forbidden, combined)

    def test_rendered_pins_are_exactly_1000_by_1500_png(self):
        from pinterest.render import render_pin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for kind in ("tides", "fishing"):
                output = root / f"san-diego-{kind}.png"
                rendered = render_pin(self.item, kind, output)
                self.assertEqual(rendered, output)
                self.assertTrue(output.exists())
                with Image.open(output) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, (1000, 1500))
                    self.assertIn(image.mode, {"RGB", "RGBA"})

    def test_unknown_pin_kind_fails(self):
        from pinterest.render import pin_text

        with self.assertRaises(ValueError):
            pin_text(self.item, "surfing")


if __name__ == "__main__":
    unittest.main()
