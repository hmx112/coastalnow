"""Regression gates for the four NOAA-validated Florida / Texas Fishing pages.

Require official data and useful local context *before* allowing search-indexed
new pages to be published. Existing canonical and safety behavior is unchanged.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from activities.paths import activity_page_path
from activities.registry import ACTIVITIES, activity_enabled_for_location
from activities.rendering.fishing_local_guides import (
    NEW_FISHING_GUIDES,
    fishing_location_guide_html,
)
from locations import LOCATIONS
from promote_location import validate_activity_geography
from seo import canonical_url, robots_directive, build_sitemap
from site_generator import build_directory_pages
from state_landing import STATE_LANDING

PUBLIC = Path(__file__).resolve().parents[1] / "public"

NEW = {
    "jacksonville-beach": ("FL", "8720218", "harmonic"),
    "sebastian-inlet": ("FL", "8722004", "hilo-derived"),
    "galveston": ("TX", "8771510", "harmonic"),
    "port-aransas": ("TX", "8775237", "harmonic"),
}


class FishingFloridaTexasExpansionTests(unittest.TestCase):
    def test_exactly_four_new_distinct_noaa_locations(self):
        self.assertEqual(set(NEW), set(NEW_FISHING_GUIDES))
        self.assertEqual(len(NEW), 4)
        for slug, (state, station, mode) in NEW.items():
            with self.subTest(slug=slug):
                loc = LOCATIONS[slug]
                self.assertEqual(loc["state_code"], state)
                self.assertEqual(loc["status"], "Live NOAA")
                self.assertEqual(loc["station"], station)
                self.assertEqual(loc["prediction_mode"], mode)
                validate_activity_geography(loc)
                self.assertEqual(loc["datum"], "MLLW")
                self.assertEqual(loc["units"], "english")
                self.assertTrue(activity_enabled_for_location(ACTIVITIES["fishing"], slug))
                self.assertFalse(activity_enabled_for_location(ACTIVITIES["surfing"], slug))

    def test_nearby_mayport_is_disclosed_not_represented_as_a_jax_pier_station(self):
        jax = LOCATIONS["jacksonville-beach"]
        self.assertEqual(jax["coverage_mode"], "nearby-noaa")
        self.assertEqual(jax["coverage_distance_miles"], 8.1)
        self.assertIn("Mayport", jax["hero_copy"])
        self.assertIn("about 8.1 miles away", jax["hero_copy"])
        self.assertIn("Local tide timing and height may differ", jax["hero_copy"])

    def test_subordinate_sebastian_uses_only_official_hilo_and_no_fake_intervals(self):
        seb = LOCATIONS["sebastian-inlet"]
        self.assertEqual(seb["prediction_mode"], "hilo-derived")
        combined = " ".join(seb["search_context"]["paragraphs"])
        self.assertIn("not NOAA 30-minute interval predictions", combined)
        self.assertIn("derived visual estimate", combined)

    def test_all_four_fishing_guides_offer_unique_official_source_and_limits(self):
        seen = set()
        for slug in NEW:
            with self.subTest(slug=slug):
                loc = LOCATIONS[slug]
                guide = NEW_FISHING_GUIDES[slug]
                html = fishing_location_guide_html(loc)
                self.assertIn('LOCAL FISHING CONTEXT', html)
                self.assertIn('rel="noopener noreferrer"', html)
                self.assertIn(guide["source"], html)
                self.assertIn(guide["url"], html)
                self.assertIn("not a fish-bite forecast", html)
                self.assertIn("not a safety guarantee", html)
                self.assertGreater(len(guide["summary"]), 110)
                self.assertGreater(len(guide["caution"]), 90)
                self.assertNotIn(guide["summary"], seen)
                seen.add(guide["summary"])
                context = loc["search_context"]
                self.assertGreaterEqual(len(context["paragraphs"]), 3)
                self.assertTrue(context["meta_description"])
        self.assertEqual(fishing_location_guide_html(LOCATIONS["malibu"]), "")

    def test_florida_and_texas_directories_have_accurate_regional_links(self):
        fl = STATE_LANDING["florida"]
        texas = STATE_LANDING["texas"]
        for state, config, expected in (
            ("florida", fl, {"jacksonville-beach", "sebastian-inlet"}),
            ("texas", texas, {"galveston", "port-aransas"}),
        ):
            with self.subTest(state=state):
                pages = build_directory_pages()
                html = pages[f"tides/{state}/index.html"]
                grouped = [slug for region in config["regions"] for slug in region["slugs"]]
                self.assertEqual(len(grouped), len(set(grouped)))
                self.assertTrue(expected <= set(grouped))
                for slug in expected:
                    self.assertIn(slug + "/index.html", html)
                    self.assertIn(LOCATIONS[slug]["name"], html)
                self.assertIn("All tide locations", html)
                self.assertIn(f'<link rel="canonical" href="{canonical_url(f"tides/{state}/index.html")}">', html)
                self.assertIn('<meta name="robots" content="index,follow">', html)

    def test_source_generated_tides_and_activity_pages_must_be_live_and_indexable(self):
        xml = (PUBLIC / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://coastalnowtides.com/tides/texas/</loc>", xml)
        for slug, (state, station, mode) in NEW.items():
            with self.subTest(slug=slug):
                loc = LOCATIONS[slug]
                tide_path = PUBLIC / loc["page_path"]
                data_path = PUBLIC / loc["data_path"]
                fish_path = PUBLIC / activity_page_path(loc, "fishing")
                result_path = PUBLIC / "data" / "activities" / "fishing" / (slug + ".json")
                for path in (tide_path, data_path, fish_path, result_path):
                    self.assertTrue(path.is_file(), str(path))
                tide_data = json.loads(data_path.read_text(encoding="utf-8"))
                self.assertEqual(tide_data.get("mode"), "live")
                self.assertEqual(tide_data.get("source"), "NOAA/NOS/CO-OPS")
                self.assertEqual(tide_data.get("station", {}).get("id"), station)
                self.assertEqual(tide_data.get("prediction_mode"), mode)
                types = {item.get("type") for item in tide_data.get("hilo") or []}
                self.assertTrue({"H", "L"} <= types)
                curve_origin = tide_data.get("curve_source")
                if mode == "harmonic":
                    self.assertEqual(curve_origin, "noaa_interval")
                else:
                    self.assertEqual(curve_origin, "derived_from_noaa_hilo")

                tide_html = tide_path.read_text(encoding="utf-8")
                fish_html = fish_path.read_text(encoding="utf-8")
                self.assertIn("7-Day Tide Schedule", tide_html)
                self.assertIn("NOAA", tide_html)
                self.assertIn(loc["search_context"]["title"], tide_html)
                self.assertIn(
                    f'<link rel="canonical" href="{canonical_url(loc["page_path"])}">',
                    tide_html,
                )
                self.assertIn(f'/tides/{loc["state_slug"]}/{slug}/fishing/', tide_html)
                self.assertIn(
                    f'<link rel="canonical" href="{canonical_url(activity_page_path(loc, "fishing"))}">',
                    fish_html,
                )
                self.assertIn("LOCAL FISHING CONTEXT", fish_html)
                self.assertEqual(fish_html.count('class="section activity-panel fishing-local-guide"'), 1)
                self.assertIn('name="google-adsense-account"', tide_html)
                self.assertIn('name="google-adsense-account"', fish_html)
                self.assertIn('<meta name="robots" content="index,follow">', tide_html)
                self.assertEqual(robots_directive(loc), "index,follow")
                self.assertIn(canonical_url(loc["page_path"]), xml)
                self.assertIn(canonical_url(activity_page_path(loc, "fishing")), xml)

    def test_unintended_surfing_pages_do_not_appear(self):
        for slug in NEW:
            loc = LOCATIONS[slug]
            path = PUBLIC / activity_page_path(loc, "surfing")
            self.assertFalse(path.exists(), str(path))
        self.assertIn("malibu", LOCATIONS)
        self.assertEqual(LOCATIONS["malibu"]["station"], "9410840")


if __name__ == "__main__":
    unittest.main()
