import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from promote_location import load_catalog, promote, validate_config, validate_station_id


class PromotionTests(unittest.TestCase):
    def test_station_id_requires_seven_digits(self):
        self.assertEqual(validate_station_id("9413450"), "9413450")
        with self.assertRaises(ValueError):
            validate_station_id("abc")
        with self.assertRaises(ValueError):
            validate_station_id("123456")

    def test_config_rejects_unknown_slug(self):
        catalog = load_catalog()
        with self.assertRaises(ValueError):
            validate_config({
                "not-a-real-place": {
                    "station_id": "9413450",
                    "station_name": "Example"
                }
            }, catalog)

    def test_promote_updates_only_requested_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live_noaa.json"
            path.write_text(json.dumps({
                "san-diego": {
                    "station_id": "9410170",
                    "station_name": "San Diego, CA"
                }
            }), encoding="utf-8")

            result = promote(
                "monterey",
                "9413450",
                "Monterey, CA",
                config_path=path,
                validate_network=False,
            )

            self.assertEqual(result["san-diego"]["station_id"], "9410170")
            self.assertEqual(result["monterey"]["station_id"], "9413450")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["monterey"]["station_name"], "Monterey, CA")


if __name__ == "__main__":
    unittest.main()
