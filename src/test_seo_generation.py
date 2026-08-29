import json
import sys
import unittest
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locations import LOCATIONS
from seo import (
    SITE_ORIGIN,
    breadcrumb_json_ld,
    build_robots_txt,
    build_sitemap,
    canonical_url,
    normalize_preview_html,
    robots_directive,
)
from site_generator import build_directory_pages

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
TIDE_TEMPLATE = ROOT / "src" / "templates" / "tide-page.html"


class SeoGenerationTests(unittest.TestCase):
    def test_site_origin_and_canonical_url(self):
        self.assertEqual(SITE_ORIGIN, "https://coastalnowtides.com")
        self.assertEqual(canonical_url(""), "https://coastalnowtides.com/")
        self.assertEqual(
            canonical_url("tides/california/san-diego/index.html"),
            "https://coastalnowtides.com/tides/california/san-diego/",
        )

    def test_indexing_policy_supports_live_and_preview_states(self):
        live = next(x for x in LOCATIONS.values() if x["status"] == "Live NOAA")
        self.assertEqual(robots_directive(live), "index,follow")
        self.assertEqual(robots_directive({"status": "Preview"}), "noindex,follow")

    def test_sitemap_includes_directories_and_only_live_detail_pages(self):
        xml = build_sitemap(LOCATIONS)
        self.assertIn("https://coastalnowtides.com/</loc>", xml)
        states = {x["state_slug"] for x in LOCATIONS.values()}
        for state in states:
            self.assertIn(
                f"https://coastalnowtides.com/tides/{state}/</loc>", xml
            )
        for location in LOCATIONS.values():
            url = canonical_url(location["page_path"])
            if location["status"] == "Live NOAA":
                self.assertIn(f"{url}</loc>", xml, location["slug"])
            else:
                self.assertNotIn(f"{url}</loc>", xml, location["slug"])

    def test_robots_txt_allows_crawling_and_points_to_sitemap(self):
        robots = build_robots_txt()
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertIn(
            "Sitemap: https://coastalnowtides.com/sitemap.xml", robots
        )

    def test_breadcrumb_json_ld_is_valid_schema_markup(self):
        markup = breadcrumb_json_ld(
            [
                ("Home", ""),
                ("California", "tides/california/index.html"),
                ("San Diego", "tides/california/san-diego/index.html"),
            ]
        )
        self.assertIn('type="application/ld+json"', markup)
        payload = markup.split(">", 1)[1].rsplit("<", 1)[0]
        data = json.loads(payload)
        self.assertEqual(data["@type"], "BreadcrumbList")
        self.assertEqual(len(data["itemListElement"]), 3)
        self.assertEqual(
            data["itemListElement"][-1]["item"],
            "https://coastalnowtides.com/tides/california/san-diego/",
        )

    def test_preview_html_gets_noindex_and_real_canonical(self):
        location = dict(next(iter(LOCATIONS.values())))
        location["status"] = "Preview"
        html = (
            '<!doctype html><html><head><title>Preview</title>'
            '<meta name="description" content="Old preview description">'
            '<link rel="canonical" href="https://example.com/tides/example/">'
            '</head><body>demo</body></html>'
        )
        updated = normalize_preview_html(html, location)
        self.assertIn('<meta name="robots" content="noindex,follow">', updated)
        self.assertIn(
            f'<link rel="canonical" href="{canonical_url(location["page_path"])}">',
            updated,
        )
        self.assertIn(f'<title>{escape(location["page_title"])}</title>', updated)
        self.assertIn(
            f'<meta name="description" content="{escape(location["meta_description"], quote=True)}">',
            updated,
        )
        self.assertNotIn("example.com", updated)
        self.assertIn('type="application/ld+json"', updated)

    def test_directory_pages_are_indexable_self_canonical_and_structured(self):
        for path, html in build_directory_pages().items():
            canonical_path = "" if path == "index.html" else path
            self.assertIn('<meta name="robots" content="index,follow">', html, path)
            self.assertIn(
                f'<link rel="canonical" href="{canonical_url(canonical_path)}">',
                html,
                path,
            )
            self.assertIn('type="application/ld+json"', html, path)
            self.assertNotIn('name="keywords"', html.lower(), path)

    def test_tide_template_does_not_use_meta_keywords(self):
        template = TIDE_TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn('name="keywords"', template.lower())

    def test_rebuilt_location_pages_have_current_indexing_policy(self):
        for location in LOCATIONS.values():
            page = PUBLIC / location["page_path"]
            self.assertTrue(page.exists(), location["slug"])
            html = page.read_text(encoding="utf-8")
            self.assertNotIn("https://example.com", html, location["slug"])
            self.assertIn(
                f'<title>{escape(location["page_title"])}</title>',
                html,
                location["slug"],
            )
            self.assertIn(
                f'<meta name="description" content="{escape(location["meta_description"], quote=True)}">',
                html,
                location["slug"],
            )
            self.assertIn(
                f'<link rel="canonical" href="{canonical_url(location["page_path"])}">',
                html,
                location["slug"],
            )
            self.assertIn(
                f'<meta name="robots" content="{robots_directive(location)}">',
                html,
                location["slug"],
            )
            self.assertIn("BreadcrumbList", html, location["slug"])

    def test_generated_seo_artifacts_match_policy(self):
        sitemap = PUBLIC / "sitemap.xml"
        robots = PUBLIC / "robots.txt"
        self.assertTrue(sitemap.exists())
        self.assertTrue(robots.exists())
        self.assertEqual(sitemap.read_text(encoding="utf-8"), build_sitemap(LOCATIONS))
        self.assertEqual(robots.read_text(encoding="utf-8"), build_robots_txt())


if __name__ == "__main__":
    unittest.main()
