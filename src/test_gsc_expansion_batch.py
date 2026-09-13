import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS
from promote_location import validate_activity_geography
from seo import build_sitemap, canonical_url, robots_directive
from site_generator import build_directory_pages


PUBLIC = Path(__file__).resolve().parents[1] / "public"
EXPECTED_NEW = {
    "long-beach",
    "ventura",
    "santa-barbara",
    "redondo-beach",
    "dana-point",
    "seal-beach",
    "key-biscayne",
    "west-palm-beach",
    "fort-myers-beach",
    "pompano-beach",
    "marco-island",
    "sarasota",
}


class GscExpansionBatchTests(unittest.TestCase):
    def test_gsc_expansion_batch_exists_in_catalog(self):
        self.assertTrue(EXPECTED_NEW <= set(LOCATIONS), sorted(EXPECTED_NEW - set(LOCATIONS)))

    def test_gsc_expansion_locations_have_explicit_geography(self):
        for slug in EXPECTED_NEW:
            item = LOCATIONS[slug]
            self.assertIsInstance(item.get("latitude"), (int, float), slug)
            self.assertIsInstance(item.get("longitude"), (int, float), slug)
            validate_activity_geography(item)

    def test_gsc_expansion_batch_is_live_after_validation(self):
        for slug in EXPECTED_NEW:
            item = LOCATIONS[slug]
            self.assertEqual(item["status"], "Live NOAA", slug)
            self.assertTrue(item.get("station"), slug)

    def test_expansion_batch_appears_in_home_and_state_directories(self):
        pages = build_directory_pages()
        home = pages["index.html"]
        california = pages["tides/california/index.html"]
        florida = pages["tides/florida/index.html"]
        for slug in EXPECTED_NEW:
            item = LOCATIONS[slug]
            self.assertIn(item["page_path"], home, slug)
            state_html = california if item["state_slug"] == "california" else florida
            self.assertIn(f'{slug}/index.html', state_html, slug)

    def test_expansion_batch_is_in_sitemap_with_self_canonical_policy(self):
        xml = build_sitemap(LOCATIONS)
        for slug in EXPECTED_NEW:
            item = LOCATIONS[slug]
            self.assertIn(canonical_url(item["page_path"]), xml, slug)
            self.assertEqual(robots_directive(item), "index,follow", slug)

    def test_expansion_batch_size_is_exactly_twelve(self):
        self.assertEqual(len(EXPECTED_NEW), 12)

    def test_expansion_batch_has_fresh_generated_tide_pages(self):
        for slug in EXPECTED_NEW:
            item = LOCATIONS[slug]
            page = PUBLIC / item["page_path"]
            data = PUBLIC / item["data_path"]
            self.assertTrue(page.exists(), slug)
            self.assertTrue(data.exists(), slug)
            html = page.read_text(encoding="utf-8")
            self.assertIn("NEXT TIDE", html, slug)
            self.assertIn("Today’s Tide Chart", html, slug)
            self.assertIn("7-Day Tide Schedule", html, slug)
            self.assertIn("NOAA", html, slug)
            self.assertIn(canonical_url(item["page_path"]), html, slug)

    def test_nearby_noaa_expansion_pages_disclose_station_and_distance(self):
        for slug in ("dana-point", "seal-beach", "key-biscayne", "west-palm-beach", "pompano-beach"):
            item = LOCATIONS[slug]
            self.assertEqual(item["coverage_mode"], "nearby-noaa", slug)
            html = (PUBLIC / item["page_path"]).read_text(encoding="utf-8")
            self.assertIn("Nearby NOAA station:", html, slug)
            self.assertIn(item["station_name"], html, slug)
            distance = float(item["coverage_distance_miles"])
            distance_text = str(int(distance)) if distance.is_integer() else f"{distance:g}"
            self.assertIn(f"about {distance_text} miles away", html, slug)


if __name__ == "__main__":
    unittest.main()
