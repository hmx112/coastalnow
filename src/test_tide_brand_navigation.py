import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_tides import build_preview, render_location
from locations import LOCATIONS
from site_generator import LOGO


class TideBrandNavigationTests(unittest.TestCase):
    def render_san_diego_tide(self) -> str:
        location = LOCATIONS["san-diego"]
        data, preview_now = build_preview(location)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, data, output, mode="preview", now=preview_now)
            return output.read_text(encoding="utf-8")

    def test_direct_tide_render_uses_same_shared_logo_as_directory_pages(self):
        html = self.render_san_diego_tide()
        self.assertIn(LOGO, html)
        self.assertNotIn("M3 13c3.5-4 6.8-4 10.1 0", html)

    def test_direct_tide_render_has_visible_enabled_fishing_navigation_link(self):
        html = self.render_san_diego_tide()
        expected = '<a href="/tides/california/san-diego/fishing/">Fishing</a>'
        self.assertIn(expected, html)
        header = html.split("</header>", 1)[0]
        self.assertIn(expected, header)


if __name__ == "__main__":
    unittest.main()
