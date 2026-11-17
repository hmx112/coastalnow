"""Offline synthetic tests. They do NOT establish live KHOA API compatibility."""
import unittest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from pipeline import TideDataError, _items, normalize_day

DAY = date(2026, 11, 17)


def envelope(rows, code="00"):
    return {"header": {"resultCode": code}, "body": {"items": {"item": rows}}}


class TestKhoaAdapter(unittest.TestCase):
    def test_hilo_maps_event_types_and_cm_without_unit_conversion(self):
        data = envelope([
            {"predcDt": "2026-11-17 12:12", "predcTdlvVl": "750.6", "extrSe": "3"},
            {"predcDt": "2026-11-17 06:00", "predcTdlvVl": "-2.5", "extrSe": "2"},
            {"predcDt": "2026-11-17 18:30", "predcTdlvVl": "15", "extrSe": "4"},
            {"predcDt": "2026-11-17 00:12", "predcTdlvVl": "702", "extrSe": "1"},
        ])
        rows = normalize_day(data, DAY, "high_low")
        self.assertEqual([r["type"] for r in rows], ["H", "L", "H", "L"])
        self.assertEqual([r["t"][-5:] for r in rows], ["00:12", "06:00", "12:12", "18:30"])
        self.assertEqual(rows[1]["v"], -2.5)
        self.assertEqual(rows[2]["v"], 750.6)

    def test_time_series_daily_count(self):
        start = datetime(2026, 11, 17, tzinfo=ZoneInfo("Asia/Seoul"))
        data = envelope([
            {"predcDt": (start + timedelta(minutes=30*i)).strftime("%Y-%m-%d %H:%M"),
             "predcTdlvVl": str(400 + i)} for i in range(48)
        ])
        rows = normalize_day(data, DAY, "series")
        self.assertEqual(len(rows), 48)
        self.assertEqual(rows[-1]["t"], "2026-11-17 23:30")

    def test_provider_failure_is_not_faked(self):
        with self.assertRaises(TideDataError):
            _items(envelope([], "20"))
        with self.assertRaises(TideDataError):
            _items({"header": {"resultCode": "00"}, "body": {"items": {"item": []}}})

    def test_bad_fields_and_dates_fail_closed(self):
        invalid = envelope([
            {"predcDt": "2026-11-18 00:00", "predcTdlvVl": "100", "extrSe": "1"},
            {"predcDt": "2026-11-17 10:00", "predcTdlvVl": "200", "extrSe": "2"},
        ])
        with self.assertRaises(TideDataError):
            normalize_day(invalid, DAY, "high_low")
        with self.assertRaises(TideDataError):
            normalize_day(envelope([{"predcDt": "2026-11-17 00:00", "predcTdlvVl": "nan", "extrSe": "1"}]), DAY, "high_low")

    def test_missing_type_or_short_series_fails(self):
        with self.assertRaises(TideDataError):
            normalize_day(envelope([{"predcDt": "2026-11-17 00:00", "predcTdlvVl": "100", "extrSe": "7"}]), DAY, "high_low")
        with self.assertRaises(TideDataError):
            normalize_day(envelope([{"predcDt": "2026-11-17 00:00", "predcTdlvVl": "100"}]), DAY, "series")


if __name__ == "__main__":
    unittest.main()
