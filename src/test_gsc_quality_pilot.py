"""Search Console 28-day pilot: uniquely helpful NOAA-grounded location context.

These regression tests run after production-equivalent generation/build, so
content must survive every scheduled tide regeneration, not just source config.
"""
from html import escape
import unittest
from pathlib import Path

from locations import LOCATIONS
from seo import canonical_url

ROOT = Path(__file__).resolve().parents[1] / "public"

PILOT = {
    "corolla": ("8651370", "Duck", "Kitty Hawk tides"),
    "half-moon-bay": ("9414131", "Pillar Point Harbor", "Santa Cruz tides"),
    "fort-lauderdale": ("8722899", "Anglin Fishing Pier", "Pompano Beach tides"),
    "holden-beach": ("8659665", "Shallotte Inlet", "Wrightsville Beach tides"),
    "los-angeles": ("9410660", "Los Angeles", "Santa Monica tides"),
}
ADAPTED = ("oceanside", "huntington-beach")


class GscQualityPilotTests(unittest.TestCase):
    def test_new_local_guides_are_specific_and_dont_make_safety_promises(self):
        bodies = []
        for slug, (station, identifier, link_text) in PILOT.items():
            with self.subTest(slug=slug):
                location = LOCATIONS[slug]
                context = location["search_context"]
                self.assertEqual(location["station"], station)
                self.assertGreaterEqual(len(context["paragraphs"]), 3)
                combined = " ".join(context["paragraphs"])
                self.assertIn(identifier, combined)
                self.assertIn(location["name"], context["title"])
                self.assertIn("not", combined.lower())
                self.assertIn(link_text, [x["label"] for x in context["related_links"]])
                self.assertTrue(context["meta_description"])
                bodies.append(combined)
        self.assertEqual(len(bodies), len(set(bodies)))

    def test_source_sharing_is_honestly_disclosed(self):
        oceanside = " ".join(LOCATIONS["oceanside"]["search_context"]["paragraphs"])
        huntington = " ".join(LOCATIONS["huntington-beach"]["search_context"]["paragraphs"])
        self.assertIn("24 miles", oceanside)
        self.assertIn("La Jolla", oceanside)
        self.assertIn("may match", oceanside)
        self.assertIn("Dana Point", huntington)
        self.assertIn("same NOAA source", huntington)
        self.assertIn("8 miles", huntington)

    def test_long_titles_shortened_only_on_two_explicit_pages(self):
        self.assertLessEqual(len(LOCATIONS["half-moon-bay"]["page_title"]), 60)
        self.assertLessEqual(len(LOCATIONS["fort-lauderdale"]["page_title"]), 60)
        self.assertIn("High & Low Tide Times", LOCATIONS["half-moon-bay"]["page_title"])
        self.assertIn("High & Low Tide Times", LOCATIONS["fort-lauderdale"]["page_title"])
        self.assertEqual(
            LOCATIONS["malibu"]["page_title"],
            "Malibu Tide Times, High & Low Tides Today | CoastalNow",
        )

    def test_pilot_pages_keep_canonicals_adsense_and_rendered_local_value(self):
        for slug in (*PILOT.keys(), *ADAPTED):
            with self.subTest(slug=slug):
                location = LOCATIONS[slug]
                html = (ROOT / location["page_path"]).read_text(encoding="utf-8")
                context = location["search_context"]
                self.assertEqual(html.count("<!-- SEARCH_CONTEXT_START -->"), 1)
                self.assertIn(escape(context["title"]), html)
                self.assertIn(escape(context["paragraphs"][0]), html)
                self.assertIn('<meta name="robots" content="index,follow">', html)
                self.assertIn(
                    f'<link rel="canonical" href="{canonical_url(location["page_path"])}">',
                    html,
                )
                self.assertIn('name="google-adsense-account"', html)
                self.assertIn("Daily high-to-low tide differences", html)
                if slug in PILOT:
                    for link in context["related_links"]:
                        self.assertIn(f'href="{link["href"]}"', html)
                if slug in ("half-moon-bay", "fort-lauderdale"):
                    self.assertIn(location["page_title"].replace("&", "&amp;"), html)

    def test_tide_pages_retain_a_single_hero_c2_and_weekly_comparison(self):
        for slug in PILOT:
            loc = LOCATIONS[slug]
            html = (ROOT / loc["page_path"]).read_text(encoding="utf-8")
            self.assertEqual(html.count('data-coastalnow-design="tide-c2"'), 1)
            self.assertEqual(html.count("<!-- WEEKLY_TIDE_COMPARE_START -->"), 1)
            self.assertNotIn("AdSense placement", html)


if __name__ == "__main__":
    unittest.main()
