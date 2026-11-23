"""Offline tests for weekly KHOA bundle collection (no real credentials or network)."""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from build_week import atomic_write_json, build_week
from pipeline import TideDataError

DAY = date(2026, 11, 18)


def daily_fixture(slug, day, *_):
    return {
        "date": day.isoformat(),
        "station": {"id": "DT_0001", "name": "인천"},
        "units": "cm",
        "hilo": [{"t": f"{day} 03:00", "v": 500.0, "type": "H"},
                 {"t": f"{day} 09:00", "v": 100.0, "type": "L"}],
        "curve": [{"t": f"{day} 00:00", "v": 300.0}],
    }


class WeeklyBuildTests(unittest.TestCase):
    def test_seven_day_window_and_query_budget(self):
        with patch("build_week.fetch_one_day", side_effect=daily_fixture) as mocked:
            result = build_week("incheon", DAY, "key-one", "key-two")
        self.assertEqual(mocked.call_count, 7)  # 2 provider requests each inside adapter
        self.assertEqual(result["date_range"]["start"], "2026-11-18")
        self.assertEqual(result["date_range"]["end"], "2026-11-24")
        self.assertEqual(len(result["days"]), 7)
        dates = [x["date"] for x in result["days"]]
        self.assertEqual(dates, [(DAY + timedelta(days=i)).isoformat() for i in range(7)])
        self.assertEqual(result["units"], "cm")

    def test_partial_failure_never_replaces_previous_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "incheon.json"
            atomic_write_json(path, {"version": "previous"})

            def fail_on_fourth(slug, day, *keys):
                if day == DAY + timedelta(days=3):
                    raise TideDataError("sample provider outage")
                return daily_fixture(slug, day)

            with patch("build_week.fetch_one_day", side_effect=fail_on_fourth):
                with self.assertRaises(TideDataError):
                    result = build_week("incheon", DAY, "key-one", "key-two")
                    atomic_write_json(path, result)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"version": "previous"})

    def test_station_and_date_mismatch_rejected(self):
        def bad_station(slug, day, *keys):
            f = daily_fixture(slug, day)
            f["station"]["id"] = "DT_0005"
            return f
        with patch("build_week.fetch_one_day", side_effect=bad_station):
            with self.assertRaisesRegex(TideDataError, "Station/date mismatch"):
                build_week("incheon", DAY, "key-one", "key-two")
        def bad_date(slug, day, *keys):
            f = daily_fixture(slug, day)
            f["date"] = "2000-01-01"
            return f
        with patch("build_week.fetch_one_day", side_effect=bad_date):
            with self.assertRaisesRegex(TideDataError, "Station/date mismatch"):
                build_week("incheon", DAY, "key-one", "key-two")

    def test_missing_key_and_invalid_days(self):
        with self.assertRaisesRegex(TideDataError, "required"):
            build_week("incheon", DAY, "", "series")
        with self.assertRaises(ValueError):
            build_week("incheon", DAY, "hi", "lo", days=8)

    def test_atomic_file_is_valid_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "weekly.json"
            atomic_write_json(path, {"name": "부산", "days": []})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["name"], "부산")


if __name__ == "__main__":
    unittest.main()
