"""Offline synthetic tests. They do NOT establish live KHOA API compatibility."""
import unittest
from unittest.mock import patch
from datetime import date, datetime, timedelta, timezone

from pipeline import TideDataError, _items, normalize_day, fetch_one_day, STATIONS

DAY = date(2026, 11, 17)


def envelope(rows, code="00"):
    return {"header": {"resultCode": code}, "body": {"items": {"item": rows}}}


class TestKhoaAdapter(unittest.TestCase):
    def test_20_station_inventory(self):
        self.assertEqual(len(STATIONS), 20)
        self.assertEqual(len({item["id"] for item in STATIONS.values()}), 20)
        self.assertEqual({r["region"] for r in STATIONS.values()}, {"서해", "남해", "동해", "제주"})


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
        start = datetime(2026, 11, 17, tzinfo=timezone(timedelta(hours=9)))
        data = envelope([
            {"predcDt": (start + timedelta(minutes=30*i)).strftime("%Y-%m-%d %H:%M"),
             "tdlvHgt": str(400 + i)} for i in range(48)
        ])
        rows = normalize_day(data, DAY, "series")
        self.assertEqual(len(rows), 48)
        self.assertEqual(rows[-1]["t"], "2026-11-17 23:30")

    def test_distinct_keys_are_routed_to_the_correct_services(self):
        seen = []

        def fake_fetch(kind, station_id, day, key):
            seen.append((kind, station_id, key))
            if kind == "high_low":
                return envelope([
                    {"predcDt": "2026-11-17 03:00", "predcTdlvVl": "700", "extrSe": "1"},
                    {"predcDt": "2026-11-17 09:00", "predcTdlvVl": "100", "extrSe": "2"},
                ])
            start = datetime(2026, 11, 17, tzinfo=timezone(timedelta(hours=9)))
            return envelope([
                {"predcDt": (start + timedelta(minutes=30 * i)).strftime("%Y-%m-%d %H:%M"),
                 "tdlvHgt": str(300 + i)}
                for i in range(48)
            ])

        with patch("pipeline._fetch", side_effect=fake_fetch):
            result = fetch_one_day("incheon", DAY, "KEY_HIGH_LOW", "KEY_TIME_SERIES")
        self.assertEqual(
            seen,
            [("high_low", "DT_0001", "KEY_HIGH_LOW"), ("series", "DT_0001", "KEY_TIME_SERIES")],
        )
        self.assertEqual(len(result["hilo"]), 2)
        self.assertEqual(len(result["curve"]), 48)

    def test_official_guides_use_different_height_fields(self):
        # 2026-11-06 KHOA API manuals: high/low = predcTdlvVl, series = tdlvHgt.
        hilo = envelope([
            {"predcDt": "2026-11-17 03:00", "predcTdlvVl": "812", "extrSe": 1},
            {"predcDt": "2026-11-17 09:00", "predcTdlvVl": "96", "extrSe": 2},
        ])
        self.assertEqual(normalize_day(hilo, DAY, "high_low")[0]["v"], 812.0)
        start = datetime(2026, 11, 17, tzinfo=timezone(timedelta(hours=9)))
        curve = envelope([{
            "predcDt": (start + timedelta(minutes=30 * i)).strftime("%Y-%m-%d %H:%M"),
            "tdlvHgt": str(202.23 + i),
        } for i in range(48)])
        self.assertEqual(normalize_day(curve, DAY, "series")[0]["v"], 202.23)

    def test_wrong_field_for_each_service_is_rejected(self):
        wrong_hilo = envelope([
            {"predcDt": "2026-11-17 03:00", "tdlvHgt": "812", "extrSe": 1},
            {"predcDt": "2026-11-17 09:00", "tdlvHgt": "96", "extrSe": 2},
        ])
        with self.assertRaisesRegex(TideDataError, "predcTdlvVl"):
            normalize_day(wrong_hilo, DAY, "high_low")
        start = datetime(2026, 11, 17, tzinfo=timezone(timedelta(hours=9)))
        wrong_series = envelope([{
            "predcDt": (start + timedelta(minutes=30 * i)).strftime("%Y-%m-%d %H:%M"),
            "predcTdlvVl": str(i + 100),
        } for i in range(48)])
        with self.assertRaisesRegex(TideDataError, "tdlvHgt"):
            normalize_day(wrong_series, DAY, "series")

    def test_truncated_daily_series_is_rejected(self):
        start = datetime(2026, 11, 17, tzinfo=timezone(timedelta(hours=9)))
        payload = envelope([
            {"predcDt": (start + timedelta(minutes=30 * i)).strftime("%Y-%m-%d %H:%M"),
             "tdlvHgt": "100"}
            for i in range(32)  # 16 hours only
        ])
        with self.assertRaises(TideDataError):
            normalize_day(payload, DAY, "series")

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
            normalize_day(envelope([{"predcDt": "2026-11-17 00:00", "tdlvHgt": "100"}]), DAY, "series")


if __name__ == "__main__":
    unittest.main()
