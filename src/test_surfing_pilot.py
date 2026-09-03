import json
import tempfile
import unittest
from pathlib import Path

from activities.registry import ACTIVITIES
from activities.surfing_pilot import validate_surfing_pilot


PILOT = tuple(ACTIVITIES["surfing"]["location_allowlist"])


def _locations():
    return {slug: {"slug": slug} for slug in (*PILOT, "key-west")}


def _snapshot(*, marine_status="ok", alerts_status="ok", with_period=True):
    rows = []
    for hour in range(24):
        rows.append(
            {
                "time": f"2026-09-03T{hour:02d}:00:00+00:00",
                "wave_height_ft": 3.0,
                "wave_period_s": 10.0 if with_period else None,
            }
        )
    return {
        "providers": {
            "marine": {"status": marine_status},
            "alerts": {"status": alerts_status},
        },
        "hourly": rows,
    }


def _write(root: Path, slug: str, snapshot: dict):
    path = root / "data" / "conditions" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot), encoding="utf-8")


class SurfingPilotValidationTests(unittest.TestCase):
    def test_ten_configured_pilot_locations_pass_with_wave_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in PILOT:
                _write(root, slug, _snapshot())
            self.assertEqual(validate_surfing_pilot(_locations(), root), list(PILOT))

    def test_missing_period_fails_and_names_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in PILOT:
                _write(root, slug, _snapshot(with_period=slug != "san-diego"))
            with self.assertRaisesRegex(ValueError, "san-diego.*wave coverage"):
                validate_surfing_pilot(_locations(), root)

    def test_non_pilot_snapshot_does_not_substitute_for_failed_pilot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in PILOT:
                if slug != "san-diego":
                    _write(root, slug, _snapshot())
            _write(root, "key-west", _snapshot())
            with self.assertRaisesRegex(ValueError, "san-diego.*missing snapshot"):
                validate_surfing_pilot(_locations(), root)

    def test_unavailable_marine_provider_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in PILOT:
                _write(root, slug, _snapshot(marine_status="unavailable" if slug == "la-jolla" else "ok"))
            with self.assertRaisesRegex(ValueError, "la-jolla.*marine provider"):
                validate_surfing_pilot(_locations(), root)

    def test_alert_provider_error_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in PILOT:
                _write(root, slug, _snapshot(alerts_status="error" if slug == "malibu" else "ok"))
            with self.assertRaisesRegex(ValueError, "malibu.*alerts provider"):
                validate_surfing_pilot(_locations(), root)


if __name__ == "__main__":
    unittest.main()
