import unittest
from pathlib import Path

from locations import LOCATIONS
from seo import build_sitemap, canonical_url
from site_generator import build_directory_pages
from state_landing import state_landing_config

ROOT = Path(__file__).resolve().parents[1] / "public"
PRIORITY_LOCATIONS = (
    "oceanside",
    "huntington-beach",
    "miami-beach",
    "clearwater-beach",
    "long-beach",
    "dana-point",
    "key-biscayne",
    "west-palm-beach",
)


class AdsenseSeoReadinessTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_trust_pages_are_production_ready(self):
        blocked_markers = (
            "Prototype static coastal-information directory",
            "Replace this prototype page",
            "Add a real contact method before production launch",
            "https://example.com/",
        )
        for slug in ("about", "privacy", "contact"):
            with self.subTest(page=slug):
                html = self._read(f"{slug}/index.html")
                for marker in blocked_markers:
                    self.assertNotIn(marker, html)
                self.assertIn(f'<link rel="canonical" href="{canonical_url(f"{slug}/index.html")}">', html)
                self.assertIn('<meta name="robots" content="index,follow">', html)

    def test_about_page_explains_service_and_sources(self):
        html = self._read("about/index.html")
        self.assertIn("NOAA", html)
        self.assertIn("tide", html.lower())
        self.assertIn("methodology", html.lower())
        self.assertGreaterEqual(html.count("<p>"), 3)

    def test_privacy_page_discloses_google_advertising_cookies(self):
        html = self._read("privacy/index.html")
        self.assertIn("Google", html)
        self.assertIn("cookies", html.lower())
        self.assertIn("Ads Settings", html)
        self.assertIn("https://adssettings.google.com/", html)
        self.assertIn("personalized advertising", html.lower())

    def test_contact_page_has_working_public_contact_route(self):
        html = self._read("contact/index.html")
        self.assertIn("https://github.com/hmx112/coastalnow/issues", html)
        self.assertIn("data correction", html.lower())
        self.assertIn("privacy", html.lower())

    def test_sitemap_includes_trust_pages(self):
        xml = build_sitemap(LOCATIONS, {})
        for slug in ("about", "privacy", "contact"):
            self.assertIn(f"<loc>{canonical_url(f'{slug}/index.html')}</loc>", xml)

    def test_directory_footer_exposes_methodology_and_trust_pages(self):
        pages = build_directory_pages()
        for relative, html in pages.items():
            with self.subTest(page=relative):
                self.assertIn("methodology/index.html", html)
                self.assertIn("about/index.html", html)
                self.assertIn("privacy/index.html", html)
                self.assertIn("contact/index.html", html)

    def test_priority_locations_have_unique_search_context(self):
        bodies = []
        for slug in PRIORITY_LOCATIONS:
            with self.subTest(location=slug):
                context = LOCATIONS[slug].get("search_context")
                self.assertIsInstance(context, dict)
                self.assertTrue(context.get("title"))
                paragraphs = context.get("paragraphs") or []
                self.assertGreaterEqual(len(paragraphs), 2)
                body = " ".join(paragraphs)
                self.assertIn(LOCATIONS[slug]["name"], body)
                bodies.append(body)
        self.assertEqual(len(bodies), len(set(bodies)))

    def test_priority_tide_pages_render_search_context(self):
        for slug in PRIORITY_LOCATIONS:
            location = LOCATIONS[slug]
            with self.subTest(location=slug):
                html = self._read(location["page_path"])
                self.assertIn("LOCAL TIDE CONTEXT", html)
                self.assertIn(location["search_context"]["title"], html)
                self.assertIn(location["search_context"]["paragraphs"][0], html)

    def test_california_and_florida_featured_lists_match_search_priorities(self):
        california = state_landing_config("california")["featured"]
        florida = state_landing_config("florida")["featured"]
        for slug in ("oceanside", "huntington-beach", "long-beach", "dana-point"):
            self.assertIn(slug, california)
        for slug in ("miami-beach", "clearwater-beach", "key-biscayne", "west-palm-beach"):
            self.assertIn(slug, florida)


if __name__ == "__main__":
    unittest.main()
