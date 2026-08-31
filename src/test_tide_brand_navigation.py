import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_site import inject_activity_links
from generate_tides import build_preview, render_location
from locations import LOCATIONS
from site_generator import LOGO


def fishing_result():
    return {
        "activity": "fishing",
        "location": "san-diego",
        "today": {
            "confidence": "High",
            "status": "normal",
            "score": 88,
            "rating": "Good",
        },
    }


class TideBrandNavigationTests(unittest.TestCase):
    # These regressions cover the user-visible Tide header before dynamic public pages are regenerated.
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

    def test_site_build_adds_mobile_visible_enabled_fishing_navigation_link_to_tide_header(self):
        location = LOCATIONS["san-diego"]
        html = self.render_san_diego_tide()
        results = {"fishing": fishing_result()}
        updated = inject_activity_links(html, location, results)
        expected = '<a class="activity-nav-link" href="/tides/california/san-diego/fishing/">Fishing</a>'
        header = updated.split("</header>", 1)[0]
        self.assertIn(expected, header)
        self.assertIn("Plan coastal activities", updated)
        self.assertIn(".nav>a:not(.activity-nav-link){display:none}", updated)
        self.assertNotIn(".nav>a{display:none}", updated)

        twice = inject_activity_links(updated, location, results)
        self.assertEqual(twice.count("ACTIVITY_NAV_START"), 1)
        self.assertEqual(twice.count(expected), 1)


if __name__ == "__main__":
    unittest.main()
