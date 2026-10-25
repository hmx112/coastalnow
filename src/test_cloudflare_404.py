"""Production contract for Cloudflare Pages' static 404 routing.

The presence of public/404.html disables Pages' implicit SPA index.html
fallback for arbitrary missing URLs. Cloudflare Pages, not this file, supplies
the HTTP 404 status. Guard against accidental removal and SEO regressions.
"""
from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path

from locations import LOCATIONS
from seo import build_sitemap, canonical_url

PUBLIC = Path(__file__).resolve().parents[1] / "public"
FOUR_OH_FOUR = PUBLIC / "404.html"
ADSENSE = '<meta name="google-adsense-account" content="ca-pub-1296444525711781">'


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []
        self.links: list[dict[str, str]] = []
        self.metas: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.hrefs.append(attrs.get("href", ""))
        elif tag == "link":
            self.links.append(attrs)
        elif tag == "meta":
            self.metas.append(attrs)


class Cloudflare404Tests(unittest.TestCase):
    def test_root_404_file_exists_and_is_a_real_page_not_home_copy(self):
        self.assertTrue(FOUR_OH_FOUR.is_file())
        html = FOUR_OH_FOUR.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("<html lang=\"en\">", html)
        self.assertIn("Page Not Found (404) | CoastalNow", html)
        self.assertIn("PAGE NOT FOUND", html)
        self.assertIn("We couldn’t find that coastal page.", html)
        self.assertNotIn("COASTAL TIDE DIRECTORY", html)
        self.assertNotIn('http-equiv="refresh"', html.lower())
        self.assertNotIn("window.location", html)
        self.assertNotIn("<script", html.lower())

    def test_missing_routes_are_not_indexed_or_canonicalized_to_the_homepage(self):
        html = FOUR_OH_FOUR.read_text(encoding="utf-8")
        parser = _Links()
        parser.feed(html)
        directives = [
            meta.get("content", "")
            for meta in parser.metas
            if meta.get("name", "").lower() == "robots"
        ]
        self.assertEqual(directives, ["noindex,follow"])
        self.assertFalse(any(link.get("rel") == "canonical" for link in parser.links))
        self.assertEqual(html.count(ADSENSE), 1)
        self.assertIn('href="/assets/site.css"', html)

    def test_all_404_navigation_uses_root_relative_known_links(self):
        parser = _Links()
        parser.feed(FOUR_OH_FOUR.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(parser.hrefs), 7)
        self.assertTrue(all(href.startswith("/") and not href.startswith("//")
                            for href in parser.hrefs))
        for route in ("/", "/fishing/", "/surfing/", "/methodology/", "/contact/"):
            with self.subTest(route=route):
                self.assertIn(route, parser.hrefs)
                output = PUBLIC / route.lstrip("/") / "index.html"
                if route == "/":
                    output = PUBLIC / "index.html"
                self.assertTrue(output.exists(), route)

    def test_404_is_not_an_indexable_sitemap_entry(self):
        xml = build_sitemap(LOCATIONS)
        self.assertNotIn("/404", xml)
        published = (PUBLIC / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("/404", published)
        for slug in ("san-diego", "malibu", "nags-head"):
            loc = LOCATIONS[slug]
            self.assertIn(canonical_url(loc["page_path"]), published)
            html = (PUBLIC / loc["page_path"]).read_text(encoding="utf-8")
            self.assertIn(
                f'<link rel="canonical" href="{canonical_url(loc["page_path"])}">',
                html,
            )
            self.assertIn('<meta name="robots" content="index,follow">', html)


if __name__ == "__main__":
    unittest.main()
