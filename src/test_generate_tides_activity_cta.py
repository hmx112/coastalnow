import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.links import activity_location_url
from generate_tides import render_location
from locations import LOCATIONS


class GenerateTidesActivityCtaTests(unittest.TestCase):
    def test_raw_tide_renderer_includes_primary_fishing_cta_before_tide_summary(self):
        location = LOCATIONS["san-diego"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, None, output, mode="error", error_message="test")
            html = output.read_text(encoding="utf-8")

        href = activity_location_url(location, "fishing")
        self.assertEqual(html.count("ACTIVITY_PRIMARY_START"), 1)
        self.assertIn(f'href="{href}"', html)
        self.assertIn("Fishing conditions for San Diego", html)
        self.assertLess(html.index("ACTIVITY_PRIMARY_START"), html.index("Your next tides"))
        self.assertGreater(html.index("ACTIVITY_PRIMARY_START"), html.index("</section>"))

    def test_raw_tide_renderer_includes_one_correct_primary_fishing_cta_for_every_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug, location in LOCATIONS.items():
                with self.subTest(location=slug):
                    output = root / slug / "index.html"
                    render_location(location, None, output, mode="error", error_message="test")
                    html = output.read_text(encoding="utf-8")
                    href = activity_location_url(location, "fishing")
                    self.assertEqual(html.count("ACTIVITY_PRIMARY_START"), 1)
                    self.assertIn(f'href="{href}"', html)
                    self.assertIn(f"Fishing conditions for {location['name']}", html)


if __name__ == "__main__":
    unittest.main()
