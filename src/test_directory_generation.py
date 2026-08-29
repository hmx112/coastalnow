import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locations import LOCATIONS
from site_generator import build_directory_pages, location_status

TIDE_TEMPLATE = Path(__file__).parent / "templates" / "tide-page.html"
MAIN_LOGO_WAVE = "M3 8c3.5-4 6.5 4 10 0s6.5 4 8 0M3 13c3.5-4 6.5 4 10 0s6.5 4 8 0M3 18c3.5-4 6.5 4 10 0s6.5 4 8 0"


class DirectoryGenerationTests(unittest.TestCase):
    def test_locations_expose_all_fifty_prototype_links(self):
        self.assertEqual(len(LOCATIONS), 51)
        self.assertEqual(len({item["page_path"] for item in LOCATIONS.values()}), 51)

    def test_catalog_statuses_are_rendered_consistently(self):
        live_locations = [
            location for location in LOCATIONS.values() if location["status"] == "Live NOAA"
        ]
        preview_locations = [
            location for location in LOCATIONS.values() if location["status"] == "Preview"
        ]
        self.assertTrue(live_locations)
        self.assertTrue(all(location_status(location) == "Live NOAA" for location in live_locations))
        self.assertTrue(all(location_status(location) == "Preview" for location in preview_locations))

    def test_home_page_contains_every_location_and_state_directory(self):
        pages = build_directory_pages()
        home = pages["index.html"]
        for location in LOCATIONS.values():
            self.assertIn(location["page_path"], home)
        self.assertEqual(home.count('class="info-card state-card"'), len({x["state_slug"] for x in LOCATIONS.values()}))

    def test_all_coastal_locations_are_sorted_by_location_name(self):
        home = build_directory_pages()["index.html"]
        section = home.split("<h2>All coastal locations</h2>", 1)[1].split("</section>", 1)[0]
        rendered_names = re.findall(r'<h3>([^<]+)</h3>', section)
        expected_names = sorted(location["name"] for location in LOCATIONS.values())
        self.assertEqual(rendered_names, expected_names)

    def test_state_pages_use_detail_style_and_preserve_location_links(self):
        pages = build_directory_pages()
        states = {x["state_slug"] for x in LOCATIONS.values()}
        self.assertEqual({path.split("/")[1] for path in pages if path.startswith("tides/") and path.count("/") == 2}, states)
        for state in states:
            page = pages[f"tides/{state}/index.html"]
            members = [x for x in LOCATIONS.values() if x["state_slug"] == state]
            self.assertIn("class=\"info-card location-card\"", page)
            for location in members:
                self.assertIn(f'{location["slug"]}/index.html', page)

    def test_generated_directory_pages_have_no_template_tokens(self):
        for path, html in build_directory_pages().items():
            self.assertNotIn("{{", html, path)
            self.assertNotIn("}}", html, path)

    def test_directory_pages_use_san_diego_detail_visual_structure(self):
        pages = build_directory_pages()
        for path, html in pages.items():
            self.assertIn('class="site-header"', html, path)
            self.assertIn('header-inner', html, path)
            self.assertIn('class="logo-mark"', html, path)
            self.assertIn('class="hero-inner"', html, path)
            self.assertIn('class="hero-wave"', html, path)
            self.assertIn('class="hero-bubble b1"', html, path)
            self.assertIn('info-card', html, path)

    def test_location_template_uses_same_logo_wave_as_directory_pages(self):
        template = TIDE_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn(MAIN_LOGO_WAVE, template)

    def test_status_badges_match_current_catalog_inventory(self):
        pages = build_directory_pages()
        home = pages["index.html"]
        self.assertIn('class="status-badge badge-live">Live NOAA</span>', home)
        if any(x["status"] == "Preview" for x in LOCATIONS.values()):
            self.assertIn('class="status-badge badge-preview">Preview</span>', home)
        else:
            self.assertNotIn('class="status-badge badge-preview">Preview</span>', home)

    def test_directory_pages_do_not_render_global_data_status_banners(self):
        for path, html in build_directory_pages().items():
            self.assertNotIn('class="preview-note"', html, path)
            self.assertNotIn('<strong>Data status:</strong>', html, path)


if __name__ == "__main__":
    unittest.main()
