import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_activity_network import validate_location_network


class ActivityNetworkValidationTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "slug": "example",
            "activity": {
                "shore_point": {"latitude": 32.7, "longitude": -117.2},
                "marine_point": {"latitude": 32.68, "longitude": -117.25},
            },
        }

    def test_ready_when_points_and_wave_context_are_available(self):
        report = validate_location_network(
            self.location,
            point_lookup=lambda lat, lon, cache=None: {"forecast_hourly": "hourly", "forecast_grid_data": "grid"},
            hourly_fetch=lambda url, cache=None: [{"time": "x"}] * 24,
            grid_fetch=lambda url, cache=None: [{"time": "x", "wave_height_ft": 2.0, "wave_period_s": 9.0}],
            alerts_fetch=lambda lat, lon, cache=None: [],
        )
        self.assertTrue(report["points_valid"])
        self.assertTrue(report["wave_context"])
        self.assertEqual(report["status"], "ready")

    def test_missing_wave_context_is_limited_not_bad_geography(self):
        report = validate_location_network(
            self.location,
            point_lookup=lambda lat, lon, cache=None: {"forecast_hourly": "hourly", "forecast_grid_data": "grid"},
            hourly_fetch=lambda url, cache=None: [{"time": "x"}] * 24,
            grid_fetch=lambda url, cache=None: [{"time": "x", "wave_height_ft": None, "wave_period_s": None}],
            alerts_fetch=lambda lat, lon, cache=None: [],
        )
        self.assertTrue(report["points_valid"])
        self.assertFalse(report["wave_context"])
        self.assertEqual(report["status"], "limited-marine-context")

    def test_invalid_marine_point_is_invalid_geography(self):
        calls = {"count": 0}
        def point_lookup(lat, lon, cache=None):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("outside forecast area")
            return {"forecast_hourly": "hourly", "forecast_grid_data": "grid"}
        report = validate_location_network(
            self.location,
            point_lookup=point_lookup,
            hourly_fetch=lambda url, cache=None: [],
            grid_fetch=lambda url, cache=None: [],
            alerts_fetch=lambda lat, lon, cache=None: [],
        )
        self.assertFalse(report["points_valid"])
        self.assertEqual(report["status"], "invalid-geography")

    def test_alert_failure_is_separate_from_geography(self):
        def alerts_fail(lat, lon, cache=None):
            raise RuntimeError("temporary alert outage")
        report = validate_location_network(
            self.location,
            point_lookup=lambda lat, lon, cache=None: {"forecast_hourly": "hourly", "forecast_grid_data": "grid"},
            hourly_fetch=lambda url, cache=None: [{"time": "x"}] * 24,
            grid_fetch=lambda url, cache=None: [{"time": "x", "wave_height_ft": 1.5, "wave_period_s": 8.0}],
            alerts_fetch=alerts_fail,
        )
        self.assertTrue(report["points_valid"])
        self.assertFalse(report["alerts_available"])
        self.assertEqual(report["status"], "alert-check-unavailable")


if __name__ == "__main__":
    unittest.main()
