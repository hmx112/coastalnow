import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_generator import build_directory_pages


class StateLandingTests(unittest.TestCase):
    def test_california_state_page_is_a_search_landing_page(self):
        html = build_directory_pages()["tides/california/index.html"]
        self.assertIn("California Tide Times", html)
        self.assertIn("Featured California tide locations", html)
        self.assertIn("Southern California Tides", html)
        self.assertIn("Northern California Tides", html)
        self.assertIn("California tide schedule", html)
        self.assertIn("Southern California tide tables", html)
        self.assertIn("SoCal tides", html)

    def test_california_featured_locations_match_current_gsc_signals(self):
        html = build_directory_pages()["tides/california/index.html"]
        featured = html.split("Featured California tide locations", 1)[1].split("Southern California Tides", 1)[0]
        positions = [featured.index(name) for name in ("Oceanside", "Huntington Beach", "Los Angeles", "San Diego")]
        self.assertEqual(positions, sorted(positions))

    def test_florida_state_page_has_featured_and_regional_sections(self):
        html = build_directory_pages()["tides/florida/index.html"]
        self.assertIn("Featured Florida tide locations", html)
        self.assertIn("Miami Beach", html)
        self.assertIn("Clearwater Beach", html)
        self.assertIn("South Florida Tides", html)
        self.assertIn("Gulf Coast Tides", html)
        self.assertIn("Atlantic Coast &amp; Keys Tides", html)

    def test_state_landing_pages_keep_full_location_directory(self):
        pages = build_directory_pages()
        for state_slug in ("california", "florida"):
            html = pages[f"tides/{state_slug}/index.html"]
            self.assertIn("All tide locations", html)


if __name__ == "__main__":
    unittest.main()
