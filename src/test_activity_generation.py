import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_activities import generate_location, read_json

UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def snapshot(slug="galveston"):
    hourly = []
    for hour in range(7, 13):
        hourly.append({
            "time": f"2026-08-30T{hour:02d}:00:00-05:00",
            "wind_mph": 8.0,
            "gust_mph": 12.0,
            "wind_direction_deg": 120.0,
            "precip_probability_pct": 10.0,
            "air_temperature_f": 82.0,
            "wave_height_ft": 2.0,
            "wave_period_s": 8.0,
            "water_temperature_f": 78.0,
            "condition_text": "Mostly Sunny",
        })
    return {
        "schema_version": 1,
        "location": slug,
        "timezone": "America/Chicago",
        "generated_at_utc": NOW.isoformat(timespec="seconds"),
        "providers": {
            "alerts": {"source": "NWS", "status": "ok", "fetched_at_utc": NOW.isoformat(timespec="seconds")},
            "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": NOW.isoformat(timespec="seconds")},
            "marine": {"source": "NWS forecastGridData", "status": "ok", "fetched_at_utc": NOW.isoformat(timespec="seconds")},
            "tide": {"source": "NOAA/NOS/CO-OPS", "status": "ok", "fetched_at_utc": NOW.isoformat(timespec="seconds")},
            "water_temperature": {"source": "NOAA/NOS/CO-OPS", "status": "ok", "fetched_at_utc": NOW.isoformat(timespec="seconds")},
        },
        "hourly": hourly,
        "alerts": {"status": "ok", "items": []},
        "provenance": {"wind_mph": "NWS", "wave_height_ft": "NWS", "alerts": "NWS", "tide": "NOAA"},
        "tide": {
            "generated_at_utc": NOW.isoformat(timespec="seconds"),
            "hilo": [
                {"t": "2026-08-30 04:00", "v": 0.0, "type": "L"},
                {"t": "2026-08-30 10:00", "v": 4.0, "type": "H"},
                {"t": "2026-08-30 16:00", "v": 0.0, "type": "L"},
                {"t": "2026-08-30 22:00", "v": 4.0, "type": "H"},
            ],
        },
        "astronomy": {
            "today": {
                "civil_dawn": "2026-08-30T06:00:00-05:00",
                "sunrise": "2026-08-30T06:30:00-05:00",
                "sunset": "2026-08-30T19:30:00-05:00",
                "civil_dusk": "2026-08-30T20:00:00-05:00",
                "moon_phase_fraction": 0.5,
            },
            "tomorrow": {
                "civil_dawn": "2026-08-31T06:01:00-05:00",
                "sunrise": "2026-08-31T06:31:00-05:00",
                "sunset": "2026-08-31T19:29:00-05:00",
                "civil_dusk": "2026-08-31T19:59:00-05:00",
                "moon_phase_fraction": 0.53,
            },
        },
    }


class ActivityGenerationTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "slug": "galveston",
            "state_slug": "texas",
            "timezone": "America/Chicago",
            "activity": {
                "shore_point": {"latitude": 29.285, "longitude": -94.789},
                "marine_point": {"latitude": 29.23, "longitude": -94.72},
                "coast_bearing": 150,
            },
        }

    def test_one_common_snapshot_feeds_every_enabled_activity(self):
        registry = {
            "fishing": {"slug": "fishing", "enabled": True},
            "surfing": {"slug": "surfing", "enabled": True},
        }
        calls = {"collector": 0, "fishing": 0, "surfing": 0}

        def collector(location, *, public_root, now):
            calls["collector"] += 1
            return snapshot(location["slug"])

        def fake_scorer(name):
            def score(common, *, location, now):
                calls[name] += 1
                self.assertIs(common, common_snapshot_holder[0])
                return {"activity": name, "location": location["slug"], "today": {"status": "normal"}}
            return score

        common_snapshot_holder = []

        def capturing_collector(location, *, public_root, now):
            calls["collector"] += 1
            value = snapshot(location["slug"])
            common_snapshot_holder.append(value)
            return value

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = generate_location(
                self.location,
                public_root=root,
                now=NOW,
                collector=capturing_collector,
                registry=registry,
                scorers={"fishing": fake_scorer("fishing"), "surfing": fake_scorer("surfing")},
            )
            self.assertEqual(calls, {"collector": 1, "fishing": 1, "surfing": 1})
            self.assertEqual(set(result["activities"]), {"fishing", "surfing"})
            self.assertTrue((root / "data/conditions/galveston.json").exists())
            self.assertTrue((root / "data/activities/fishing/galveston.json").exists())
            self.assertTrue((root / "data/activities/surfing/galveston.json").exists())
            self.assertFalse(list(root.rglob("*.tmp")))

    def test_new_location_needs_no_separate_activity_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate_location(
                self.location,
                public_root=root,
                now=NOW,
                collector=lambda location, **kwargs: snapshot(location["slug"]),
                scorers={"fishing": lambda common, **kwargs: {"activity": "fishing", "location": common["location"]}},
            )
            saved = read_json(root / "data/activities/fishing/galveston.json")
            self.assertEqual(saved["location"], "galveston")

    def test_collection_failure_uses_existing_cache_without_erasing_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            condition_path = root / "data/conditions/galveston.json"
            condition_path.parent.mkdir(parents=True)
            cached = snapshot()
            cached["provenance"]["special"] = "preserve-me"
            condition_path.write_text(json.dumps(cached), encoding="utf-8")

            def fail(*args, **kwargs):
                raise RuntimeError("NWS temporary failure")

            result = generate_location(
                self.location,
                public_root=root,
                now=NOW,
                collector=fail,
                scorers={"fishing": lambda common, **kwargs: {"activity": "fishing", "refresh_state": common["refresh_state"]}},
            )
            rewritten = read_json(condition_path)
            self.assertEqual(rewritten["refresh_state"], "cache-fallback")
            self.assertEqual(rewritten["provenance"]["special"], "preserve-me")
            self.assertEqual(result["condition_source"], "cache-fallback")

    def test_alert_only_refresh_does_not_call_full_collector(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            condition_path = root / "data/conditions/galveston.json"
            condition_path.parent.mkdir(parents=True)
            condition_path.write_text(json.dumps(snapshot()), encoding="utf-8")
            calls = {"collector": 0, "alerts": 0}

            def collector(*args, **kwargs):
                calls["collector"] += 1
                raise AssertionError("full collector must not run")

            def alerts_fetch(lat, lon, *, cache=None):
                calls["alerts"] += 1
                return [{"id": f"alert-{calls['alerts']}", "event": "Dense Fog Advisory"}]

            generate_location(
                self.location,
                public_root=root,
                now=NOW,
                collector=collector,
                alerts_only=True,
                alerts_fetch=alerts_fetch,
                scorers={"fishing": lambda common, **kwargs: {"activity": "fishing", "alert_count": len(common["alerts"]["items"])}},
            )
            refreshed = read_json(condition_path)
            self.assertEqual(calls["collector"], 0)
            self.assertEqual(calls["alerts"], 2)
            self.assertEqual(refreshed["alerts"]["status"], "ok")
            self.assertEqual(len(refreshed["alerts"]["items"]), 2)
            self.assertEqual(refreshed["refresh_state"], "alerts-only")

    def test_alert_only_failure_becomes_unknown_not_no_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            condition_path = root / "data/conditions/galveston.json"
            condition_path.parent.mkdir(parents=True)
            condition_path.write_text(json.dumps(snapshot()), encoding="utf-8")

            def fail_alerts(*args, **kwargs):
                raise RuntimeError("alert API failed")

            generate_location(
                self.location,
                public_root=root,
                now=NOW,
                alerts_only=True,
                alerts_fetch=fail_alerts,
                scorers={"fishing": lambda common, **kwargs: {"activity": "fishing", "alert_status": common["alerts"]["status"]}},
            )
            refreshed = read_json(condition_path)
            self.assertEqual(refreshed["alerts"]["status"], "error")
            self.assertEqual(refreshed["providers"]["alerts"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
