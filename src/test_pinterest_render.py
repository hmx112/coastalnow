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
        }

    def test_pin_text_is_evergreen_and_activity_specific(self):
        from pinterest.render import pin_text

        tide = pin_text(self.item, "tides")
        fishing = pin_text(self.item, "fishing")

        self.assertEqual(tide["location"], "SAN DIEGO")
        self.assertEqual(tide["state"], "CALIFORNIA")
        self.assertEqual(tide["category"], "TIDE TIMES & TIDE CHART")
        self.assertEqual(tide["subtitle"], "Fast local tide info for planning by the water.")
        self.assertEqual(tide["cta"], "See today’s tide times →")
        self.assertEqual(tide["footer"], "Your go-to source for coastal conditions.")
        self.assertEqual(
            tide["features"],
            (
                ("High & Low Tide Times", "Know when tides rise and fall."),
                ("7-Day Tide Forecast", "Plan ahead with a weekly outlook."),
                ("Live NOAA Tide Data", "Reliable local prediction data."),
                ("Today’s Tide Chart", "See the tide pattern at a glance."),
            ),
        )

        self.assertEqual(fishing["category"], "FISHING CONDITIONS & BEST TIMES")
        self.assertEqual(fishing["subtitle"], "For shore, pier and nearshore fishing.")
        self.assertEqual(fishing["cta"], "See today’s fishing conditions →")
        self.assertEqual(fishing["footer"], "Live tide, wind & wave context")
        self.assertEqual(
            fishing["features"],
            (
                ("Live 0–100 Fishing Score", "See how conditions rate for fishing."),
                ("Tide", "Tide movement and timing"),
                ("Wind", "Wind speed and direction"),
                ("Waves", "Wave height and period"),
                ("Weather", "Sky, rain chance and more"),
                ("Best 3-hour fishing window", "Top window based on today’s conditions"),
            ),
        )

        for payload in (tide, fishing):
            text_values = []
            for value in payload.values():
                if isinstance(value, str):
                    text_values.append(value)
                elif isinstance(value, tuple):
                    for item in value:
                        if isinstance(item, tuple):
                            text_values.extend(item)
            combined = " ".join(text_values).lower()
            for forbidden in (
                "mph",
                "°f",
                "2026-",
                "fishing score 88",
                "tide height 5",
                "wave height 3",
            ):
                self.assertNotIn(forbidden, combined)

    def test_renderer_uses_shared_site_style_brand_helper_and_removes_old_wave_layers(self):
        import pinterest.render as render

        self.assertTrue(callable(render._draw_coastalnow_brand))
        source = inspect.getsource(render)
        self.assertNotIn("def _wave_polygon", source)
        self.assertNotIn("draw.polygon(_wave_polygon", source)
        self.assertNotIn("draw.ellipse((72, 60, 172, 160), fill=TEAL)", source)
        heading_source = inspect.getsource(render._draw_common_heading)
        self.assertIn("_draw_coastalnow_brand", heading_source)

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
