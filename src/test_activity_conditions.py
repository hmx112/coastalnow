import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.conditions.snapshot import build_snapshot
from activities.conditions.validation import (
    ALERT_MAX_AGE_HOURS,
    FORECAST_MAX_AGE_HOURS,
    assess_snapshot_freshness,
    validate_snapshot,
)

UTC = timezone.utc


def iso(dt):
    return dt.isoformat(timespec="seconds")


class ActivityConditionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
        self.location = {"slug": "example", "timezone": "America/New_York"}
        self.hourly = [
            {
                "time": "2026-08-30T08:00:00-04:00",
                "wind_mph": 8.0,
                "gust_mph": 12.0,
                "wind_direction_deg": 90.0,
                "precip_probability_pct": 20.0,
                "air_temperature_f": 78.0,
                "wave_height_ft": 2.5,
                "wave_period_s": 9.0,
                "water_temperature_f": None,
                "condition_text": "Partly Sunny",
            },
            {
                "time": "2026-08-30T09:00:00-04:00",
                "wind_mph": 9.0,
                "gust_mph": 14.0,
                "wind_direction_deg": 95.0,
                "precip_probability_pct": 25.0,
                "air_temperature_f": 79.0,
                "wave_height_ft": 2.7,
                "wave_period_s": 9.0,
                "water_temperature_f": None,
                "condition_text": "Partly Sunny",
            },
        ]

    def snapshot(self, alert_age=1, forecast_age=1, alert_status="ok", forecast_status="ok"):
        return build_snapshot(
            self.location,
            generated_at_utc=iso(self.now),
            hourly=self.hourly,
            providers={
                "alerts": {
                    "source": "NWS",
                    "status": alert_status,
                    "fetched_at_utc": iso(self.now - timedelta(hours=alert_age)),
                },
                "forecast": {
                    "source": "NWS",
                    "status": forecast_status,
                    "fetched_at_utc": iso(self.now - timedelta(hours=forecast_age)),
                },
                "tide": {
                    "source": "NOAA/NOS/CO-OPS",
                    "status": "ok",
                    "fetched_at_utc": iso(self.now - timedelta(hours=1)),
                },
            },
            alerts={"status": alert_status, "items": []},
            provenance={
                "wind_mph": "NWS forecast",
                "wave_height_ft": "NWS marine forecast",
                "alerts": "NWS active alerts",
                "tide": "NOAA/NOS/CO-OPS",
            },
        )

    def test_snapshot_schema_preserves_local_hourly_values_and_provenance(self):
        snapshot = self.snapshot()
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["location"], "example")
        self.assertEqual(snapshot["timezone"], "America/New_York")
        self.assertEqual(snapshot["hourly"][0]["time"], "2026-08-30T08:00:00-04:00")
        self.assertEqual(snapshot["provenance"]["wave_height_ft"], "NWS marine forecast")
        self.assertIsNone(snapshot["hourly"][0]["water_temperature_f"])

    def test_validation_rejects_out_of_order_hours_and_invalid_ranges(self):
        snapshot = self.snapshot()
        snapshot["hourly"] = list(reversed(snapshot["hourly"]))
        with self.assertRaisesRegex(ValueError, "hourly timestamps"):
            validate_snapshot(snapshot)

        snapshot = self.snapshot()
        snapshot["hourly"][0]["precip_probability_pct"] = 120
        with self.assertRaisesRegex(ValueError, "precip_probability_pct"):
            validate_snapshot(snapshot)

        snapshot = self.snapshot()
        snapshot["hourly"][0]["wave_height_ft"] = -1
        with self.assertRaisesRegex(ValueError, "wave_height_ft"):
            validate_snapshot(snapshot)

    def test_alert_freshness_boundary_is_two_hours(self):
        self.assertEqual(ALERT_MAX_AGE_HOURS, 2)
        fresh = assess_snapshot_freshness(self.snapshot(alert_age=2), self.now)
        stale = assess_snapshot_freshness(self.snapshot(alert_age=2.01), self.now)
        self.assertEqual(fresh["alerts"], "fresh")
        self.assertEqual(stale["alerts"], "stale")
        self.assertTrue(fresh["normal_safety_state_allowed"])
        self.assertFalse(stale["normal_safety_state_allowed"])

    def test_forecast_freshness_boundary_is_six_hours(self):
        self.assertEqual(FORECAST_MAX_AGE_HOURS, 6)
        fresh = assess_snapshot_freshness(self.snapshot(forecast_age=6), self.now)
        stale = assess_snapshot_freshness(self.snapshot(forecast_age=6.01), self.now)
        self.assertEqual(fresh["forecast"], "fresh")
        self.assertEqual(stale["forecast"], "stale")
        self.assertTrue(fresh["high_medium_eligible"])
        self.assertFalse(stale["high_medium_eligible"])

    def test_alert_failure_is_unavailable_not_no_alerts(self):
        snapshot = self.snapshot(alert_status="error")
        snapshot["alerts"] = {"status": "error", "items": []}
        freshness = assess_snapshot_freshness(snapshot, self.now)
        self.assertEqual(freshness["alerts"], "unavailable")
        self.assertFalse(freshness["normal_safety_state_allowed"])
        self.assertFalse(freshness["high_medium_eligible"])

    def test_missing_values_remain_unknown(self):
        snapshot = self.snapshot()
        snapshot["hourly"][0]["wave_height_ft"] = None
        snapshot["hourly"][0]["wave_period_s"] = None
        validate_snapshot(snapshot)
        self.assertIsNone(snapshot["hourly"][0]["wave_height_ft"])
        self.assertIsNone(snapshot["hourly"][0]["wave_period_s"])


if __name__ == "__main__":
    unittest.main()
