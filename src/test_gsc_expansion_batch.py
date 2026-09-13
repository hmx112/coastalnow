import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS
from promote_location import validate_activity_geography


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


if __name__ == "__main__":
    unittest.main()
