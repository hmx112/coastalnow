"""Guard the 10 -> 16 Surfing expansion and independently sourced spot context.

No Tide, Fishing or Activity safety-policy changes are authorized by this
pilot. A generated page must remain indexable ONLY when its official data
state meets the pre-existing Activity robots policy.
"""
import json
import unittest
from pathlib import Path

from activities.registry import ACTIVITIES, activity_enabled_for_location
from activities.paths import activity_page_path
from activities.rendering.surf_spot_guides import EXPANSION_SURF_SPOTS, surf_spot_guide_html
from activities.rendering.surfing_page import render_surfing_location
from locations import LOCATIONS
from seo import activity_robots_directive, canonical_url

PUBLIC = Path(__file__).resolve().parents[1] / "public"
NEW = ("oceanside", "newport-beach", "ventura", "virginia-beach", "folly-beach", "ocean-city")
OLD = ("san-diego", "la-jolla", "huntington-beach", "santa-cruz", "malibu",
       "half-moon-bay", "cocoa-beach", "daytona-beach", "wrightsville-beach", "nags-head")


class SurfingSixLocationExpansionTests(unittest.TestCase):
    def test_exactly_six_additions_without_unintended_locations(self):
        enabled = tuple(ACTIVITIES["surfing"]["location_allowlist"])
        self.assertEqual(len(enabled), 16)
        self.assertEqual(len(set(enabled)), 16)
        self.assertEqual(set(enabled), set(OLD) | set(NEW))
        self.assertEqual(set(EXPANSION_SURF_SPOTS), set(NEW))
        self.assertFalse(activity_enabled_for_location(ACTIVITIES["surfing"], "key-west"))
        for slug in NEW:
            self.assertIn(slug, LOCATIONS)
            self.assertEqual(LOCATIONS[slug]["status"], "Live NOAA")
            self.assertTrue(activity_enabled_for_location(ACTIVITIES["surfing"], slug))

    def test_every_new_guide_is_unique_attributed_and_not_a_break_specific_forecast(self):
        bodies = []
        for slug in NEW:
            with self.subTest(slug=slug):
                g = EXPANSION_SURF_SPOTS[slug]
                html = surf_spot_guide_html(LOCATIONS[slug])
                self.assertIn(LOCATIONS[slug]["name"], html)
                self.assertIn(g["spot"], html)
                self.assertIn(g["url"].replace("&", "&amp;"), html)
                self.assertIn('rel="noopener noreferrer"', html)
                self.assertIn("not real-time measurements", html)
                self.assertIn("not a CoastalNow data provider", html)
                self.assertGreater(len(g["summary"]), 100)
                self.assertGreater(len(g["caution"]), 70)
                bodies.append(g["summary"])
        self.assertEqual(len(set(bodies)), 6)
        self.assertEqual(surf_spot_guide_html(LOCATIONS["malibu"]), "")
        self.assertEqual(surf_spot_guide_html(LOCATIONS["key-west"]), "")

    def test_ocean_city_is_maryland_not_new_jersey_and_discloses_access_rules(self):
        location = LOCATIONS["ocean-city"]
        self.assertEqual(location["state_slug"], "maryland")
        guide = surf_spot_guide_html(location)
        self.assertIn("rotating designated surfing areas", guide)
        self.assertIn("Maryland with Ocean City, New Jersey", guide)
        self.assertIn("oceancitymd.gov", guide)

    def test_new_snapshots_have_official_provenance_and_24h_wave_coverage(self):
        for slug in NEW:
            with self.subTest(slug=slug):
                snap = json.loads((PUBLIC / "data" / "conditions" / (slug + ".json")).read_text(encoding="utf-8"))
                providers = snap.get("providers") or {}
                self.assertEqual((providers.get("marine") or {}).get("status"), "ok")
                self.assertNotEqual((providers.get("alerts") or {}).get("status"), "error")
                hours = (snap.get("hourly") or [])[:24]
                self.assertGreaterEqual(len(hours), 12)
                good = sum(
                    1 for row in hours
                    if row.get("wave_height_ft") is not None and
                    row.get("wave_period_s") is not None and
                    float(row["wave_height_ft"]) >= 0 and
                    float(row["wave_period_s"]) > 0
                )
                self.assertGreaterEqual(good, 12)

    def test_generated_surfing_pages_and_seo_are_consistent(self):
        for slug in NEW:
            with self.subTest(slug=slug):
                loc = LOCATIONS[slug]
                path = PUBLIC / activity_page_path(loc, "surfing")
                result_path = PUBLIC / "data" / "activities" / "surfing" / (slug + ".json")
                self.assertTrue(path.is_file(), slug)
                self.assertTrue(result_path.is_file(), slug)
                result = json.loads(result_path.read_text(encoding="utf-8"))
                self.assertEqual(result["activity"], "surfing")
                self.assertEqual(result["location"], slug)
                html = path.read_text(encoding="utf-8")
                self.assertEqual(html.count('class="section activity-panel surf-local-guide"'), 1)
                self.assertIn('COASTAL SURF PLANNER', html)
                self.assertIn("Conditions are not break-specific.", html)
                self.assertIn(f'<link rel="canonical" href="{canonical_url(activity_page_path(loc, "surfing"))}">', html)
                expected = activity_robots_directive(result)
                self.assertIn(f'<meta name="robots" content="{expected}">', html)
                self.assertIn('name="google-adsense-account"', html)
                self.assertIn(f'/tides/{loc["state_slug"]}/{slug}/', html)
                tide_html = (PUBLIC / loc["page_path"]).read_text(encoding="utf-8")
                self.assertIn(f'/tides/{loc["state_slug"]}/{slug}/surfing/', tide_html)
                self.assertIn(f'<link rel="canonical" href="{canonical_url(loc["page_path"])}">', tide_html)

    def test_existing_surfing_and_nonpilot_pages_are_untouched_by_spot_guides(self):
        for slug in OLD:
            with self.subTest(slug=slug):
                loc = LOCATIONS[slug]
                html = (PUBLIC / activity_page_path(loc, "surfing")).read_text(encoding="utf-8")
                self.assertNotIn('class="section activity-panel surf-local-guide"', html)
        self.assertFalse((PUBLIC / "tides" / "florida" / "key-west" / "surfing" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
