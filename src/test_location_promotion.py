import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from promote_location import load_catalog, load_request, promote, promote_request, validate_config, validate_station_id


class PromotionTests(unittest.TestCase):

    def test_catalog_supplies_timezone_for_preview_location(self):
        catalog = load_catalog()
        self.assertEqual(catalog["monterey"]["timezone"], "America/Los_Angeles")

    def test_request_file_promotes_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "live_noaa.json"
            config_path.write_text(json.dumps({
                "san-diego": {
                    "station_id": "9410170",
                    "station_name": "San Diego, CA"
                }
            }), encoding="utf-8")
            request_path = tmp_path / "monterey.json"
            request_path.write_text(json.dumps({
                "slug": "monterey",
                "station_id": "9413450",
                "station_name": "Monterey, CA"
            }), encoding="utf-8")

            request = load_request(request_path)
            self.assertEqual(request["slug"], "monterey")
            result = promote_request(
                request_path,
                config_path=config_path,
                validate_network=False,
            )

            self.assertEqual(result["monterey"]["station_id"], "9413450")

    def test_push_workflow_is_non_recursive(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "promote-location.yml").read_text(encoding="utf-8")
        self.assertIn('"promotion/**"', workflow)
        self.assertIn('git rm "$request"', workflow)
        self.assertIn('--head "$BRANCH"', workflow)
        self.assertNotIn('branch="preview/', workflow)

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
