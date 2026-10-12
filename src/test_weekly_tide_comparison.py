"""Regression checks for NOAA-based, safe, idempotent Tide comparison content."""
import unittest

from locations import LOCATIONS
from seo import _enrich_location_body
from weekly_tide_comparison import render_weekly_tide_comparison


def fixture():
    return {
        "mode": "live",
        "source": "NOAA/NOS/CO-OPS",
        "units": "feet",
        "range": {"start": "2026-10-12", "end": "2026-10-18"},
        "hilo": [
            {"t": "2026-10-12 06:00", "type": "L", "v": -0.2},
            {"t": "2026-10-12 12:00", "type": "H", "v": 9.8},
            {"t": "2026-10-12 18:00", "type": "L", "v": 0.1},
            {"t": "2026-10-13 06:15", "type": "L", "v": 1.0},
            {"t": "2026-10-13 12:15", "type": "H", "v": 5.0},
            {"t": "2026-10-14 06:30", "type": "L", "v": 1.0},
            {"t": "2026-10-14 12:30", "type": "H", "v": 8.0},
            {"t": "2026-10-20 12:30", "type": "H", "v": 99.0},
        ],
    }


class WeeklyTideComparisonTests(unittest.TestCase):
    def test_derived_differences_match_noaa_predictions_without_extra_events(self):
        html = render_weekly_tide_comparison(fixture())
        self.assertIn("Daily high-to-low tide differences", html)
        self.assertIn("10.0 ft on Mon, Oct 12", html)
        self.assertIn("smallest daily difference is 4.0 ft on Tue, Oct 13", html)
        self.assertIn("a high of 9.8 ft at 12:00 PM", html)
        self.assertIn("a low of -0.2 ft at 6:00 AM", html)
        self.assertEqual(html.count('class="c2-weekly-row"'), 3)
        self.assertNotIn("99.0 ft", html)
        self.assertIn("not indicate current speed", html)
        self.assertIn("Predictions are not observations", html)

    def test_no_fabricated_comparison_when_live_data_is_missing_or_unverified(self):
        self.assertEqual(render_weekly_tide_comparison(None), "")
        missing = fixture()
        missing["hilo"] = []
        self.assertEqual(render_weekly_tide_comparison(missing), "")
        preview = fixture()
        preview["mode"] = "preview"
        self.assertEqual(render_weekly_tide_comparison(preview), "")
        unverified = fixture()
        unverified["source"] = "SYNTHETIC PREVIEW"
        self.assertEqual(render_weekly_tide_comparison(unverified), "")
        wrong_units = fixture()
        wrong_units["units"] = "metric"
        self.assertEqual(render_weekly_tide_comparison(wrong_units), "")
        only_one_day = fixture()
        only_one_day["hilo"] = fixture()["hilo"][:2]
        self.assertEqual(render_weekly_tide_comparison(only_one_day), "")

    def test_no_nan_or_unbounded_date_windows(self):
        invalid = fixture()
        invalid["hilo"][1]["v"] = "nan"
        html = render_weekly_tide_comparison(invalid)
        self.assertNotIn("nan ft", html.lower())
        wide = fixture()
        wide["range"]["end"] = "2026-11-18"
        self.assertEqual(render_weekly_tide_comparison(wide), "")

    def test_comparison_links_to_a_public_explanation(self):
        from activities.rendering.methodology_page import render_methodology_page
        comparison = render_weekly_tide_comparison(fixture())
        self.assertIn('href="/methodology/#reading-tides"', comparison)
        guide = render_methodology_page()
        self.assertIn('id="reading-tides"', guide)
        self.assertIn("Mean Lower Low Water", guide)
        self.assertIn("5.2 ft daily high-to-low difference", guide)

    def test_repeated_normalization_replaces_one_block(self):
        html = '<main><section class="section lower-grid"></section></main>'
        location = LOCATIONS["bar-harbor"]
        first = _enrich_location_body(html, location, fixture())
        second = _enrich_location_body(first, location, fixture())
        self.assertEqual(first, second)
        self.assertEqual(second.count("<!-- WEEKLY_TIDE_COMPARE_START -->"), 1)
        empty = _enrich_location_body(second, location, None)
        self.assertNotIn("<!-- WEEKLY_TIDE_COMPARE_START -->", empty)


if __name__ == "__main__":
    unittest.main()
