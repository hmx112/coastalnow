import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_tides import static_replacements
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
        self.assertEqual(SITE_ORIGIN, "https://coastalnow.pages.dev")
        self.assertEqual(canonical_url(""), "https://coastalnow.pages.dev/")
        self.assertEqual(
            canonical_url("tides/california/san-diego/index.html"),
            "https://coastalnow.pages.dev/tides/california/san-diego/",
        )

    def test_live_pages_index_and_preview_pages_noindex(self):
        live = next(x for x in LOCATIONS.values() if x["status"] == "Live NOAA")
        preview = next(x for x in LOCATIONS.values() if x["status"] == "Preview")
        self.assertEqual(robots_directive(live), "index,follow")
        self.assertEqual(robots_directive(preview), "noindex,follow")

    def test_sitemap_includes_directories_and_only_live_detail_pages(self):
        xml = build_sitemap(LOCATIONS)
        self.assertIn("https://coastalnow.pages.dev/</loc>", xml)
        states = {x["state_slug"] for x in LOCATIONS.values()}
        for state in states:
            self.assertIn(
                f"https://coastalnow.pages.dev/tides/{state}/</loc>", xml
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
            "Sitemap: https://coastalnow.pages.dev/sitemap.xml", robots
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
            "https://coastalnow.pages.dev/tides/california/san-diego/",
        )

    def test_preview_html_gets_noindex_and_real_canonical(self):
        location = next(x for x in LOCATIONS.values() if x["status"] == "Preview")
        html = (
            '<!doctype html><html><head><title>Preview</title>'
            '<link rel="canonical" href="https://example.com/tides/example/">'
            '</head><body>demo</body></html>'
        )
        updated = normalize_preview_html(html, location)
        self.assertIn('<meta name="robots" content="noindex,follow">', updated)
        self.assertIn(
            f'<link rel="canonical" href="{canonical_url(location["page_path"])}">',
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

    def test_tide_template_and_replacements_apply_status_based_indexing(self):
        template = TIDE_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("{{ROBOTS_META}}", template)
        self.assertIn("{{CANONICAL_URL}}", template)
        self.assertIn("{{BREADCRUMB_JSON_LD}}", template)
        self.assertNotIn('name="keywords"', template.lower())

        live = next(x for x in LOCATIONS.values() if x["status"] == "Live NOAA")
        preview = next(x for x in LOCATIONS.values() if x["status"] == "Preview")
        live_meta = static_replacements(live)
        preview_meta = static_replacements(preview)
        self.assertEqual(live_meta["ROBOTS_META"], "index,follow")
        self.assertEqual(preview_meta["ROBOTS_META"], "noindex,follow")
        self.assertEqual(live_meta["CANONICAL_URL"], canonical_url(live["page_path"]))
        self.assertEqual(
            preview_meta["CANONICAL_URL"], canonical_url(preview["page_path"])
        )
        self.assertIn("BreadcrumbList", live_meta["BREADCRUMB_JSON_LD"])

    def test_committed_location_pages_have_current_indexing_policy(self):
        for location in LOCATIONS.values():
            page = PUBLIC / location["page_path"]
            self.assertTrue(page.exists(), location["slug"])
            html = page.read_text(encoding="utf-8")
            self.assertNotIn("https://example.com", html, location["slug"])
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

    def test_generated_seo_artifacts_are_committed(self):
        sitemap = PUBLIC / "sitemap.xml"
        robots = PUBLIC / "robots.txt"
        self.assertTrue(sitemap.exists())
        self.assertTrue(robots.exists())
        self.assertEqual(sitemap.read_text(encoding="utf-8"), build_sitemap(LOCATIONS))
        self.assertEqual(robots.read_text(encoding="utf-8"), build_robots_txt())


if __name__ == "__main__":
    unittest.main()
