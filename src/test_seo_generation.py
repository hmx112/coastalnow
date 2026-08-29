import json
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
