import json
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.conditions.astronomy import moon_phase_fraction, solar_events
from activities.conditions.providers.noaa import parse_water_temperature
from activities.conditions.providers.nws import (
    merge_hourly_conditions,
    parse_alerts,
    parse_grid_data,
    parse_hourly_forecast,
    parse_point_metadata,
)
from activities.conditions.snapshot import build_snapshot
from activities.conditions.validation import (
    ALERT_MAX_AGE_HOURS,
    FORECAST_MAX_AGE_HOURS,
    assess_snapshot_freshness,
    validate_snapshot,
)

UTC = timezone.utc
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "activity"


def iso(dt):
    return dt.isoformat(timespec="seconds")


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


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

    def test_nws_point_metadata_follows_linked_forecast_urls(self):
        parsed = parse_point_metadata(fixture("nws-points.json"))
        self.assertEqual(parsed["grid_id"], "SGX")
        self.assertEqual(parsed["forecast_hourly"], "https://api.weather.gov/gridpoints/SGX/54,20/forecast/hourly")
        self.assertEqual(parsed["forecast_grid_data"], "https://api.weather.gov/gridpoints/SGX/54,20")
        self.assertEqual(parsed["forecast_zone"], "CAZ043")
        self.assertEqual(parsed["county_zone"], "CAC073")

    def test_nws_hourly_parser_normalizes_weather_fields(self):
        rows = parse_hourly_forecast(fixture("nws-hourly.json"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["time"], "2026-08-30T05:00:00-07:00")
        self.assertEqual(rows[0]["air_temperature_f"], 68.0)
        self.assertEqual(rows[0]["wind_mph"], 8.0)
        self.assertEqual(rows[0]["wind_direction_deg"], 270.0)
        self.assertEqual(rows[0]["precip_probability_pct"], 10.0)
        self.assertEqual(rows[0]["condition_text"], "Partly Sunny")
        self.assertEqual(rows[1]["wind_mph"], 14.0)
        self.assertEqual(rows[1]["wind_direction_deg"], 247.5)

    def test_nws_marine_grid_expands_valid_time_and_converts_units(self):
        grid = parse_grid_data(fixture("nws-grid.json"))
        self.assertEqual(len(grid), 2)
        self.assertAlmostEqual(grid[0]["gust_mph"], 15.0, places=1)
        self.assertAlmostEqual(grid[0]["wave_height_ft"], 2.62, places=1)
        self.assertEqual(grid[0]["wave_period_s"], 9.0)
        hourly = parse_hourly_forecast(fixture("nws-hourly.json"))
        merged = merge_hourly_conditions(hourly, grid)
        self.assertAlmostEqual(merged[0]["wave_height_ft"], 2.62, places=1)
        self.assertAlmostEqual(merged[1]["gust_mph"], 15.0, places=1)

    def test_nws_alert_parser_keeps_fields_needed_by_safety_gate(self):
        alerts = parse_alerts(fixture("nws-alerts.json"))
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["id"], "urn:oid:alert-1")
        self.assertEqual(alert["event"], "High Surf Warning")
        self.assertEqual(alert["severity"], "Severe")
        self.assertIn("Dangerous surf", alert["description"])
        self.assertEqual(alert["sender_name"], "NWS San Diego CA")

    def test_noaa_water_temperature_is_optional_and_never_fabricated(self):
        self.assertEqual(parse_water_temperature(fixture("noaa-water-temperature.json")), 68.5)
        self.assertIsNone(parse_water_temperature({"error": {"message": "No data"}}))
        self.assertIsNone(parse_water_temperature({"data": []}))

    def test_solar_and_moon_calculations_are_local_and_deterministic(self):
        tz = ZoneInfo("America/Los_Angeles")
        events = solar_events(date(2026, 6, 21), 32.7507, -117.2534, tz)
        self.assertEqual(events["sunrise"].tzinfo, tz)
        self.assertEqual(events["sunset"].tzinfo, tz)
        self.assertGreaterEqual(events["sunrise"].hour, 4)
        self.assertLessEqual(events["sunrise"].hour, 7)
        self.assertGreaterEqual(events["sunset"].hour, 18)
        self.assertLessEqual(events["sunset"].hour, 21)
        phase = moon_phase_fraction(date(2026, 8, 30))
        self.assertGreaterEqual(phase, 0.0)
        self.assertLess(phase, 1.0)
        self.assertEqual(phase, moon_phase_fraction(date(2026, 8, 30)))


if __name__ == "__main__":
    unittest.main()
