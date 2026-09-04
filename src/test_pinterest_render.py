import inspect
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
            "surfing_enabled": True,
        }

    def test_pin_text_is_evergreen_and_matches_final_poster_copy(self):
        from pinterest.render import pin_text

        tide = pin_text(self.item, "tides")
        fishing = pin_text(self.item, "fishing")
        surfing = pin_text(self.item, "surfing")

        self.assertEqual(tide["location"], "SAN DIEGO")
        self.assertEqual(tide["state"], "California")
        self.assertEqual(tide["category"], "TIDE TIMES")
        self.assertEqual(tide["subtitle"], "Tide Times & Tide Chart")
        self.assertEqual(tide["cta"], "View Tide Times")

        self.assertEqual(fishing["category"], "FISHING CONDITIONS")
        self.assertEqual(fishing["subtitle"], "Fishing Conditions & Best Times")
        self.assertEqual(fishing["cta"], "View Fishing Conditions")

        self.assertEqual(surfing["category"], "SURF CONDITIONS")
        self.assertEqual(surfing["subtitle"], "Surf Conditions & Best Times")
        self.assertEqual(surfing["cta"], "View Surf Conditions")

        for payload in (tide, fishing, surfing):
            combined = " ".join(str(value) for value in payload.values()).lower()
            for forbidden in (
                "mph",
                "°f",
                "2026-",
                "fishing score",
                "tide height",
                "wave height",
                "best window",
            ):
                self.assertNotIn(forbidden, combined)

    def test_renderer_uses_photo_backgrounds_and_final_minimal_layout(self):
        import pinterest.render as render

        self.assertTrue(callable(render._draw_coastalnow_brand))
        self.assertTrue(callable(render._load_photo_background))
        source = inspect.getsource(render)
        self.assertIn("PHOTO_BACKGROUNDS", source)
        self.assertIn("images.unsplash.com", source)
        self.assertIn("ImageOps.fit", source)
        self.assertNotIn("_draw_tide_scene", source)
        self.assertNotIn("_draw_fishing_scene", source)
        self.assertNotIn("_draw_surfing_scene", source)
        self.assertNotIn("chip_width", source)

    def test_rendered_pins_are_exactly_1000_by_1500_png_and_visually_distinct(self):
        from pinterest.render import render_pin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = {}
            for kind in ("tides", "fishing", "surfing"):
                output = root / f"san-diego-{kind}.png"
                rendered = render_pin(self.item, kind, output)
                self.assertEqual(rendered, output)
                self.assertTrue(output.exists())
                payloads[kind] = output.read_bytes()
                with Image.open(output) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, (1000, 1500))
                    self.assertIn(image.mode, {"RGB", "RGBA"})
            self.assertEqual(len({payloads[kind] for kind in payloads}), 3)

    def test_unknown_pin_kind_fails(self):
        from pinterest.render import pin_text

        with self.assertRaises(ValueError):
            pin_text(self.item, "swimming")


if __name__ == "__main__":
    unittest.main()
