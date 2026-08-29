import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.conditions.collect import collect_location_conditions


class ActivityCollectionTests(unittest.TestCase):
    def test_collection_uses_separate_shore_and_marine_points_and_reuses_common_snapshot(self):
        calls = []
        now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
        location = {
            "slug": "example",
            "timezone": "America/Los_Angeles",
            "station": "9410170",
            "data_path": "data/example.json",
            "activity": {
                "shore_point": {"latitude": 32.75, "longitude": -117.25},
                "marine_point": {"latitude": 32.75, "longitude": -117.30},
                "coast_bearing": 270,
            },
        }

        def point_lookup(lat, lon, cache=None):
            calls.append(("point", lat, lon))
            suffix = "shore" if lon == -117.25 else "marine"
            return {
                "forecast_hourly": f"https://example/{suffix}/hourly",
                "forecast_grid_data": f"https://example/{suffix}/grid",
                "forecast_zone": "CAZ043",
                "county_zone": "CAC073",
                "time_zone": "America/Los_Angeles",
                "grid_id": "SGX",
                "grid_x": 1,
                "grid_y": 2,
            }

        def hourly_fetch(url, cache=None):
            calls.append(("hourly", url))
            return [{
                "time": "2026-08-30T05:00:00-07:00",
                "wind_mph": 8.0,
                "gust_mph": None,
                "wind_direction_deg": 270.0,
                "precip_probability_pct": 10.0,
                "air_temperature_f": 68.0,
                "wave_height_ft": None,
                "wave_period_s": None,
                "water_temperature_f": None,
                "condition_text": "Partly Sunny",
            }]

        def grid_fetch(url, cache=None):
            calls.append(("grid", url))
            return [{
                "time": "2026-08-30T12:00:00+00:00",
                "gust_mph": 15.0,
                "wave_height_ft": 2.5,
                "wave_period_s": 9.0,
            }]

        def alerts_fetch(lat, lon, cache=None):
            calls.append(("alerts", lat, lon))
            return [{
                "id": "same-alert",
                "event": "Coastal Flood Advisory",
                "severity": "Minor",
                "certainty": "Likely",
                "urgency": "Expected",
                "effective": None,
                "onset": None,
                "expires": None,
                "ends": None,
                "headline": "Test",
                "description": "Test",
                "instruction": "Test",
                "sender_name": "NWS",
            }]

        def water_fetch(station):
            calls.append(("water", station))
            return 68.5

        def tide_loader(loc, public_root):
            calls.append(("tide", loc["slug"]))
            return {
                "generated_at_utc": "2026-08-30T11:00:00+00:00",
                "hilo": [{"t": "2026-08-30 06:00", "v": 2.0, "type": "H"}],
                "curve": [{"t": "2026-08-30 05:00", "v": 1.5}],
            }

        snapshot = collect_location_conditions(
            location,
            public_root=Path("/tmp/not-used"),
            now=now,
            point_lookup=point_lookup,
            hourly_fetch=hourly_fetch,
            grid_fetch=grid_fetch,
            alerts_fetch=alerts_fetch,
            water_fetch=water_fetch,
            tide_loader=tide_loader,
        )

        self.assertIn(("point", 32.75, -117.25), calls)
        self.assertIn(("point", 32.75, -117.30), calls)
        self.assertEqual(snapshot["hourly"][0]["wave_height_ft"], 2.5)
        self.assertEqual(snapshot["hourly"][0]["water_temperature_f"], 68.5)
        self.assertEqual(len(snapshot["alerts"]["items"]), 1)
        self.assertEqual(snapshot["tide"]["hilo"][0]["type"], "H")
        self.assertIn("today", snapshot["astronomy"])
        self.assertEqual(snapshot["providers"]["alerts"]["status"], "ok")
        self.assertEqual(snapshot["providers"]["forecast"]["status"], "ok")
        self.assertEqual(snapshot["provenance"]["wave_height_ft"], "NWS marine forecastGridData")


if __name__ == "__main__":
    unittest.main()
