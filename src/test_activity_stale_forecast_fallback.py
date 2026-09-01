import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_activities import generate_location, read_json
from test_activity_generation import snapshot

UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class ActivityStaleForecastFallbackTests(unittest.TestCase):
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

    def _write_cached_snapshot(self, root: Path, forecast_age: timedelta) -> Path:
        cached = snapshot(self.location["slug"])
        cached["providers"]["forecast"]["fetched_at_utc"] = (NOW - forecast_age).isoformat(timespec="seconds")
        path = root / "data" / "conditions" / "galveston.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cached), encoding="utf-8")
        return path

    def test_alert_only_promotes_to_full_refresh_when_forecast_reaches_four_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            condition_path = self._write_cached_snapshot(root, timedelta(hours=4))
            calls = {"collector": 0, "alerts": 0}

            def collector(location, *, public_root, now):
                calls["collector"] += 1
                fresh = snapshot(location["slug"])
                fresh["generated_at_utc"] = now.isoformat(timespec="seconds")
                for provider in fresh["providers"].values():
                    provider["fetched_at_utc"] = now.isoformat(timespec="seconds")
                return fresh

            def alerts_fetch(*args, **kwargs):
                calls["alerts"] += 1
                return []

            result = generate_location(
                self.location,
                public_root=root,
                now=NOW,
                collector=collector,
                alerts_only=True,
                alerts_fetch=alerts_fetch,
                scorers={"fishing": lambda common, **kwargs: {"activity": "fishing"}},
            )

            refreshed = read_json(condition_path)
            self.assertEqual(calls["collector"], 1)
            self.assertEqual(calls["alerts"], 0)
            self.assertEqual(result["condition_source"], "alerts-only-full-refresh")
            self.assertEqual(refreshed["refresh_state"], "alerts-only-full-refresh")
            self.assertEqual(refreshed["providers"]["forecast"]["fetched_at_utc"], NOW.isoformat(timespec="seconds"))

    def test_alert_only_keeps_lightweight_path_before_four_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            condition_path = self._write_cached_snapshot(root, timedelta(hours=3, minutes=59))
            calls = {"collector": 0, "alerts": 0}

            def collector(*args, **kwargs):
                calls["collector"] += 1
                raise AssertionError("full collector must not run before fallback threshold")

            def alerts_fetch(*args, **kwargs):
                calls["alerts"] += 1
                return []

            result = generate_location(
                self.location,
                public_root=root,
                now=NOW,
                collector=collector,
                alerts_only=True,
                alerts_fetch=alerts_fetch,
                scorers={"fishing": lambda common, **kwargs: {"activity": "fishing"}},
            )

            refreshed = read_json(condition_path)
            self.assertEqual(calls["collector"], 0)
            self.assertEqual(calls["alerts"], 2)
            self.assertEqual(result["condition_source"], "alerts-only")
            self.assertEqual(refreshed["refresh_state"], "alerts-only")


if __name__ == "__main__":
    unittest.main()
