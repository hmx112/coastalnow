"""Regression checks for the optional NOAA low-tide finder (five locations)."""
from __future__ import annotations

import math
import unittest
from pathlib import Path

from locations import LOCATIONS
from low_tide_finder import PILOT_LOCATIONS, render_low_tide_finder
from seo import _enrich_location_body, canonical_url

PUBLIC = Path(__file__).resolve().parents[1] / "public"


def fixture():
    loc = LOCATIONS["malibu"]
    return {
        "mode": "live",
        "source": "NOAA/NOS/CO-OPS",
        "datum": "MLLW",
        "units": "feet",
        "time_zone_mode": "LST/LDT",
        "station": {"id": loc["station"], "timezone": loc["timezone"]},
        "range": {"start": "2026-10-12", "end": "2026-10-18"},
        "hilo": [
            {"t": "2026-10-12 05:45", "type": "L", "v": 0.7},
            {"t": "2026-10-12 10:15", "type": "H", "v": 5.0},
            {"t": "2026-10-12 14:10", "type": "L", "v": -0.2},
            {"t": "2026-10-13 10:05", "type": "L", "v": 0.1},
            {"t": "2026-10-13 16:00", "type": "H", "v": 3.0},
            {"t": "2026-10-13 21:30", "type": "L", "v": -0.6},
            {"t": "2026-10-19 02:00", "type": "L", "v": -99.0},
            {"t": "2026-10-12 23:00", "type": "L", "v": float("nan")},
        ],
    }


class LowTideFinderTests(unittest.TestCase):
    def test_verified_events_are_sorted_by_level_and_grouped_by_time_of_day(self):
        html = render_low_tide_finder(fixture(), LOCATIONS["malibu"])
        self.assertEqual(html.count('class="c2-low-finder-row"'), 4)
        values = [html.index(text) for text in ("-0.6 ft", "-0.2 ft", "0.1 ft", "0.7 ft")]
        self.assertEqual(values, sorted(values))
        self.assertIn('data-time-band="morning"', html)
        self.assertIn('data-time-band="afternoon"', html)
        self.assertIn('data-time-band="evening"', html)
        self.assertIn('data-time-band="overnight"', html)
        self.assertIn("Times shown in Pacific time", html)
        self.assertNotIn("-99.0 ft", html)
        self.assertNotIn("nan ft", html.lower())
        self.assertIn("not beach water depth", html)
        self.assertIn("does not establish safe access", html)
        self.assertIn("Earlier events in the current day may already have passed", html)

    def test_no_fake_results_for_missing_or_misattributed_noaa_data(self):
        malibu = LOCATIONS["malibu"]
        self.assertEqual(render_low_tide_finder(None, malibu), "")
        for key, value in (
            ("mode", "preview"),
            ("source", "SYNTHETIC PREVIEW"),
            ("units", "meters"),
            ("datum", "MHW"),
            ("time_zone_mode", "GMT"),
        ):
            with self.subTest(key=key):
                d = fixture()
                d[key] = value
                self.assertEqual(render_low_tide_finder(d, malibu), "")
        for key, value in (("id", "9999999"), ("timezone", "America/New_York")):
            d = fixture()
            d["station"][key] = value
            self.assertEqual(render_low_tide_finder(d, malibu), "")
        d = fixture()
        d["range"]["end"] = "2026-11-19"
        self.assertEqual(render_low_tide_finder(d, malibu), "")
        d = fixture()
        d["hilo"] = d["hilo"][:2]
        self.assertEqual(render_low_tide_finder(d, malibu), "")
        preview_location = dict(malibu, status="Preview")
        self.assertEqual(render_low_tide_finder(fixture(), preview_location), "")

    def test_feature_is_limited_to_pilot_and_respects_seo_normalization(self):
        self.assertEqual(len(PILOT_LOCATIONS), 5)
        self.assertEqual(render_low_tide_finder(fixture(), LOCATIONS["san-diego"]), "")
        html = '<main><section class="section lower-grid"></section></main>'
        a = _enrich_location_body(html, LOCATIONS["malibu"], fixture())
        b = _enrich_location_body(a, LOCATIONS["malibu"], fixture())
        self.assertEqual(a, b)
        self.assertEqual(b.count("<!-- LOW_TIDE_FINDER_START -->"), 1)
        self.assertEqual(b.count("<!-- LOW_TIDE_FINDER_END -->"), 1)
        self.assertLess(b.index("<!-- LOW_TIDE_FINDER_START -->"),
                        b.index("<!-- WEEKLY_TIDE_COMPARE_START -->"))
        erased = _enrich_location_body(b, LOCATIONS["malibu"], None)
        self.assertNotIn("<!-- LOW_TIDE_FINDER_START -->", erased)

    def test_generated_pilot_pages_keep_unique_urls_and_noaa_source(self):
        for slug in sorted(PILOT_LOCATIONS):
            loc = LOCATIONS[slug]
            html = (PUBLIC / loc["page_path"]).read_text(encoding="utf-8")
            with self.subTest(slug=slug):
                self.assertEqual(html.count("<!-- LOW_TIDE_FINDER_START -->"), 1)
                self.assertIn('class="c2-low-finder-daypart"', html)
                self.assertIn('class="c2-low-finder-row"', html)
                self.assertIn('src="/assets/low-tide-finder.js?v=20261013-pilot-1"', html)
                self.assertIn('href="/assets/malibu-c2.css?v=20261012-value-1"', html)
                self.assertIn('href="/assets/low-tide-finder.css?v=20261013-pilot-1"', html)
                self.assertEqual(html.count("<!-- WEEKLY_TIDE_COMPARE_START -->"), 1)
                self.assertIn(f'<link rel="canonical" href="{canonical_url(loc["page_path"])}">', html)
                self.assertIn('<meta name="robots" content="index,follow">', html)
                self.assertEqual(html.count('name="google-adsense-account"'), 1)
                self.assertIn(str(loc["station"]), html)

        normal = LOCATIONS["san-diego"]
        unmodified = (PUBLIC / normal["page_path"]).read_text(encoding="utf-8")
        self.assertNotIn("<!-- LOW_TIDE_FINDER_START -->", unmodified)
        self.assertNotIn('src="/assets/low-tide-finder.js', unmodified)
        self.assertNotIn('href="/assets/low-tide-finder.css', unmodified)

    def test_browser_filter_assets_have_fallback_and_accessibility(self):
        css = (PUBLIC / "assets" / "low-tide-finder.css").read_text(encoding="utf-8")
        script = (PUBLIC / "assets" / "low-tide-finder.js").read_text(encoding="utf-8")
        self.assertIn(".c2-low-finder-row[hidden]{display:none!important}", css)
        self.assertIn('picker.addEventListener("change", update)', script)
        self.assertIn("row.hidden = !visible", script)
        self.assertIn('role="status"', render_low_tide_finder(fixture(), LOCATIONS["malibu"]))
        self.assertIn("aria-live", render_low_tide_finder(fixture(), LOCATIONS["malibu"]))


if __name__ == "__main__":
    unittest.main()
