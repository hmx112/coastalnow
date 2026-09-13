import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS
from promote_location import validate_activity_geography
from seo import build_sitemap, canonical_url, robots_directive
from site_generator import build_directory_pages


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


if __name__ == "__main__":
    unittest.main()
