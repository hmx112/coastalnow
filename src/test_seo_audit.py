import tempfile
import unittest
from pathlib import Path

from seo_audit import audit_location_page


EXAMPLE_LOCATION = {
    "slug": "example-beach",
    "name": "Example Beach",
    "state": "California",
    "state_slug": "california",
    "page_path": "tides/california/example-beach/index.html",
    "status": "Live NOAA",
}


class SeoAuditTests(unittest.TestCase):
    def test_audit_reports_missing_structural_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / EXAMPLE_LOCATION["page_path"]
            page.parent.mkdir(parents=True)
            page.write_text(
                "<html><head><title>Example Tide Times</title></head>"
                "<body><h1>Example Beach Tide Times Today</h1></body></html>",
                encoding="utf-8",
            )
            result = audit_location_page(root, EXAMPLE_LOCATION)

        self.assertTrue(result["page_exists"])
        self.assertEqual(result["title"], "Example Tide Times")
        self.assertFalse(result["canonical"])
        self.assertFalse(result["robots"])
        self.assertFalse(result["breadcrumb_json_ld"])
        self.assertFalse(result["state_link"])
        self.assertEqual(result["nearby_link_count"], 0)
        self.assertFalse(result["today_tide_events"])
        self.assertFalse(result["seven_day_forecast"])
        self.assertFalse(result["noaa_source"])

    def test_audit_detects_complete_tide_page_signals(self):
        canonical = "https://coastalnowtides.com/tides/california/example-beach/"
        html = f'''<!doctype html><html><head>
        <title>Example Beach Tide Times, High &amp; Low Tides Today | CoastalNow</title>
        <meta name="description" content="See today’s high tide and low tide times with a tide chart and 7-day tide schedule.">
        <meta name="robots" content="index,follow">
        <link rel="canonical" href="{canonical}">
        <script type="application/ld+json">{{"@type":"BreadcrumbList"}}</script>
        </head><body>
        <a href="../index.html">California</a>
        <h1>Example Beach Tide Times Today</h1>
        <h2>Today’s High and Low Tides</h2>
        <div class="tide-list"><div class="event"><span>High</span></div></div>
        <h2>Today’s Tide Chart</h2>
        <section id="forecast"><h2>7-Day Tide Schedule</h2></section>
        <a class="place state-directory-link" href="../index.html">More California tide locations</a>
        <a class="place" href="../neighbor-one/index.html">Neighbor One</a>
        <a class="place" href="../neighbor-two/index.html">Neighbor Two</a>
        <div>NOAA CO-OPS</div>
        </body></html>'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / EXAMPLE_LOCATION["page_path"]
            page.parent.mkdir(parents=True)
            page.write_text(html, encoding="utf-8")
            result = audit_location_page(root, EXAMPLE_LOCATION)

        self.assertTrue(result["canonical"])
        self.assertTrue(result["robots"])
        self.assertTrue(result["breadcrumb_json_ld"])
        self.assertTrue(result["state_link"])
        self.assertEqual(result["nearby_link_count"], 2)
        self.assertTrue(result["today_tide_events"])
        self.assertTrue(result["seven_day_forecast"])
        self.assertTrue(result["noaa_source"])
        for term in ("tide times", "high tide", "low tide", "tide chart", "tide schedule"):
            self.assertIn(term, result["search_intent_terms"])

    def test_missing_page_returns_safe_empty_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = audit_location_page(Path(tmp), EXAMPLE_LOCATION)
        self.assertFalse(result["page_exists"])
        self.assertIsNone(result["title"])
        self.assertIsNone(result["h1"])
        self.assertEqual(result["nearby_link_count"], 0)


if __name__ == "__main__":
    unittest.main()
