import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from promote_location import (
    load_catalog,
    load_request,
    normalize_request_payload,
    promote,
    promote_batch,
    promote_request,
    validate_config,
    validate_station_id,
)


class PromotionTests(unittest.TestCase):

    def test_catalog_supplies_timezone_for_preview_location(self):
        catalog = load_catalog()
        self.assertEqual(catalog["monterey"]["timezone"], "America/Los_Angeles")

    def test_batch_request_normalizes_multiple_locations(self):
        payload = {
            "locations": [
                {
                    "slug": "santa-cruz",
                    "station_id": "9413745",
                    "station_name": "Santa Cruz, Monterey Bay, CA",
                    "prediction_mode": "hilo-derived",
                },
                {
                    "slug": "half-moon-bay",
                    "station_id": "9414131",
                    "station_name": "Pillar Point Harbor, Half Moon Bay, CA",
                },
            ]
        }
        items = normalize_request_payload(payload)
        self.assertEqual([x["slug"] for x in items], ["santa-cruz", "half-moon-bay"])
        self.assertEqual(items[0]["prediction_mode"], "hilo-derived")
        self.assertEqual(items[1]["prediction_mode"], "harmonic")

    def test_legacy_request_still_normalizes_to_one_item(self):
        payload = {
            "slug": "santa-cruz",
            "station_id": "9413745",
            "station_name": "Santa Cruz, Monterey Bay, CA",
            "prediction_mode": "hilo-derived",
        }
        items = normalize_request_payload(payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["slug"], "santa-cruz")

    def test_unknown_mode_is_rejected_before_config_write(self):
        payload = {
            "locations": [
                {
                    "slug": "santa-cruz",
                    "station_id": "9413745",
                    "station_name": "Santa Cruz, Monterey Bay, CA",
                    "prediction_mode": "wrong",
                }
            ]
        }
        with self.assertRaises(ValueError):
            normalize_request_payload(payload)

    def test_duplicate_slug_is_rejected(self):
        payload = {
            "locations": [
                {
                    "slug": "santa-cruz",
                    "station_id": "9413745",
                    "station_name": "Santa Cruz, Monterey Bay, CA",
                    "prediction_mode": "hilo-derived",
                },
                {
                    "slug": "santa-cruz",
                    "station_id": "9413745",
                    "station_name": "Santa Cruz, Monterey Bay, CA",
                    "prediction_mode": "hilo-derived",
                },
            ]
        }
        with self.assertRaises(ValueError):
            normalize_request_payload(payload)

    def test_batch_is_atomic_when_later_network_validation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live_noaa.json"
            original = json.dumps(
                {
                    "san-diego": {
                        "station_id": "9410170",
                        "station_name": "San Diego, CA",
                    }
                },
                indent=2,
            ) + "\n"
            path.write_text(original, encoding="utf-8")
            items = normalize_request_payload(
                {
                    "locations": [
                        {
                            "slug": "santa-cruz",
                            "station_id": "9413745",
                            "station_name": "Santa Cruz, Monterey Bay, CA",
                            "prediction_mode": "hilo-derived",
                        },
                        {
                            "slug": "half-moon-bay",
                            "station_id": "9414131",
                            "station_name": "Pillar Point Harbor, Half Moon Bay, CA",
                        },
                    ]
                }
            )
            with patch(
                "promote_location.validate_noaa_compatibility",
                side_effect=[None, RuntimeError("second station failed")],
            ):
                with self.assertRaises(RuntimeError):
                    promote_batch(items, config_path=path, validate_network=True)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

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

    def test_subordinate_request_preserves_prediction_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "live_noaa.json"
            config_path.write_text("{}", encoding="utf-8")
            request_path = tmp_path / "north-myrtle-beach.json"
            request_path.write_text(json.dumps({
                "slug": "north-myrtle-beach",
                "station_id": "8660642",
                "station_name": "North Myrtle Beach, ICWW, SC",
                "prediction_mode": "hilo-derived"
            }), encoding="utf-8")

            result = promote_request(
                request_path,
                config_path=config_path,
                validate_network=False,
            )

            self.assertEqual(result["north-myrtle-beach"]["prediction_mode"], "hilo-derived")

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

    def test_config_rejects_unknown_prediction_mode(self):
        catalog = load_catalog()
        with self.assertRaises(ValueError):
            validate_config({
                "north-myrtle-beach": {
                    "station_id": "8660642",
                    "station_name": "North Myrtle Beach, ICWW, SC",
                    "prediction_mode": "made-up-mode"
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
