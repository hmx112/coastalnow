import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from site_generator import build_directory_pages
from state_landing import STATE_LANDING


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

    def test_southern_california_region_contains_expansion_locations(self):
        region = next(item for item in STATE_LANDING["california"]["regions"] if item["key"] == "southern-california")
        self.assertTrue({"long-beach", "ventura", "santa-barbara", "redondo-beach", "dana-point", "seal-beach"} <= set(region["slugs"]))

    def test_florida_regions_contain_expansion_locations(self):
        slugs = set()
        for region in STATE_LANDING["florida"]["regions"]:
            slugs.update(region["slugs"])
        self.assertTrue({"key-biscayne", "west-palm-beach", "fort-myers-beach", "pompano-beach", "marco-island", "sarasota"} <= slugs)


    def test_north_carolina_directory_groups_outer_banks_and_southern_shores(self):
        html = build_directory_pages()["tides/north-carolina/index.html"]
        self.assertIn("Outer Banks Tide Times", html)
        self.assertIn("Crystal Coast and Southern North Carolina Tides", html)
        self.assertIn("Cape Hatteras", html)
        self.assertIn("Wrightsville Beach", html)
        self.assertIn("All tide locations", html)

    def test_south_carolina_and_oregon_have_useful_directory_guides(self):
        pages = build_directory_pages()
        self.assertIn("Grand Strand Tide Times", pages["tides/south-carolina/index.html"])
        self.assertIn("Charleston Area and Lowcountry Tides", pages["tides/south-carolina/index.html"])
        self.assertIn("Northern Oregon Coast Tides", pages["tides/oregon/index.html"])
        self.assertIn("Central Oregon Coast Tides", pages["tides/oregon/index.html"])
        for state in ("south-carolina", "oregon"):
            self.assertIn("All tide locations", pages[f"tides/{state}/index.html"])

    def test_new_state_regions_cover_each_live_location_once(self):
        from locations import LOCATIONS
        for state in ("north-carolina", "south-carolina", "oregon"):
            config = STATE_LANDING[state]
            grouped = [slug for region in config["regions"] for slug in region["slugs"]]
            expected = {
                loc["slug"] for loc in LOCATIONS.values()
                if loc["state_slug"] == state and loc["status"] == "Live NOAA"
            }
            self.assertEqual(set(grouped), expected, state)
            self.assertEqual(len(grouped), len(set(grouped)), state)



if __name__ == "__main__":
    unittest.main()
