import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from locations import LOCATIONS
from site_generator import build_directory_pages, location_status


class DirectoryGenerationTests(unittest.TestCase):
    def test_locations_expose_all_fifty_prototype_links(self):
        self.assertEqual(len(LOCATIONS), 51)
        self.assertEqual(len({item["page_path"] for item in LOCATIONS.values()}), 51)

    def test_live_status_is_limited_to_noaa_ready_locations(self):
        live_locations = [
            location for location in LOCATIONS.values() if location["status"] == "Live NOAA"
        ]
        preview_locations = [
            location for location in LOCATIONS.values() if location["status"] == "Preview"
        ]
        self.assertTrue(live_locations)
        self.assertTrue(preview_locations)
        self.assertTrue(all(location_status(location) == "Live NOAA" for location in live_locations))
        self.assertTrue(all(location_status(location) == "Preview" for location in preview_locations))

    def test_home_page_contains_every_location_and_state_directory(self):
        pages = build_directory_pages()
        home = pages["index.html"]
        for location in LOCATIONS.values():
            self.assertIn(location["page_path"], home)
        self.assertEqual(home.count('class="info-card state-card"'), len({x["state_slug"] for x in LOCATIONS.values()}))

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

    def test_status_badges_have_distinct_visual_classes(self):
        pages = build_directory_pages()
        home = pages["index.html"]
        self.assertIn('badge-live', home)
        self.assertIn('badge-preview', home)

    def test_directory_pages_do_not_render_global_data_status_banners(self):
        for path, html in build_directory_pages().items():
            self.assertNotIn('class="preview-note"', html, path)
            self.assertNotIn('<strong>Data status:</strong>', html, path)


if __name__ == "__main__":
    unittest.main()
