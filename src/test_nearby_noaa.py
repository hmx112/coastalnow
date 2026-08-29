import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import coverage_disclosure
from promote_location import normalize_request_payload, promote_batch


class NearbyNoaaCoverageTests(unittest.TestCase):
    def test_nearby_request_preserves_coverage_metadata(self):
        items = normalize_request_payload({
            "slug": "huntington-beach",
            "station_id": "9410580",
            "station_name": "Newport Beach, Newport Bay Entrance, CA",
            "coverage_mode": "nearby-noaa",
            "coverage_distance_miles": 8,
        })
        self.assertEqual(items[0]["coverage_mode"], "nearby-noaa")
        self.assertEqual(items[0]["coverage_distance_miles"], 8.0)

    def test_local_request_defaults_to_local_coverage(self):
        items = normalize_request_payload({
            "slug": "huntington-beach",
            "station_id": "9410580",
            "station_name": "Newport Beach, Newport Bay Entrance, CA",
        })
        self.assertEqual(items[0]["coverage_mode"], "local")
        self.assertIsNone(items[0]["coverage_distance_miles"])

    def test_invalid_coverage_mode_and_distance_are_rejected(self):
        base = {
            "slug": "huntington-beach",
            "station_id": "9410580",
            "station_name": "Newport Beach, Newport Bay Entrance, CA",
        }
        with self.assertRaises(ValueError):
            normalize_request_payload({**base, "coverage_mode": "satellite"})
        with self.assertRaises(ValueError):
            normalize_request_payload({**base, "coverage_mode": "nearby-noaa", "coverage_distance_miles": 0})

    def test_promote_batch_persists_nearby_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live_noaa.json"
            path.write_text("{}", encoding="utf-8")
            result = promote_batch([{
                "slug": "huntington-beach",
                "station_id": "9410580",
                "station_name": "Newport Beach, Newport Bay Entrance, CA",
                "prediction_mode": "harmonic",
                "coverage_mode": "nearby-noaa",
                "coverage_distance_miles": 8,
            }], config_path=path, validate_network=False)
            self.assertEqual(result["huntington-beach"]["coverage_mode"], "nearby-noaa")
            self.assertEqual(result["huntington-beach"]["coverage_distance_miles"], 8.0)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["huntington-beach"]["coverage_mode"], "nearby-noaa")

    def test_nearby_disclosure_is_explicit(self):
        text = coverage_disclosure({
            "name": "Huntington Beach",
            "station_name": "Newport Beach, Newport Bay Entrance, CA",
            "coverage_mode": "nearby-noaa",
            "coverage_distance_miles": 8,
        })
        self.assertIn("Nearby NOAA station", text)
        self.assertIn("Huntington Beach", text)
        self.assertIn("Newport Beach, Newport Bay Entrance, CA", text)
        self.assertIn("8 miles away", text)
        self.assertIn("Local tide timing and height may differ", text)

    def test_local_coverage_has_no_extra_disclosure(self):
        self.assertEqual(coverage_disclosure({"coverage_mode": "local"}), "")


if __name__ == "__main__":
    unittest.main()
