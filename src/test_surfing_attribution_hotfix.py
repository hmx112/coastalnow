import json
import tempfile
import unittest
from pathlib import Path

from activities.paths import activity_page_path
from build_site import render_activity_outputs
from locations import LOCATIONS


class SurfingAttributionHotfixTests(unittest.TestCase):
    def _snapshot(self):
        return {
            "schema_version": 1,
            "location": "san-diego",
            "timezone": "America/Los_Angeles",
            "providers": {
                "forecast": {"status": "ok", "fetched_at_utc": "2026-09-03T12:00:00+00:00"},
                "alerts": {"status": "ok", "fetched_at_utc": "2026-09-03T12:00:00+00:00"},
                "tide": {"status": "ok", "fetched_at_utc": "2026-09-03T12:00:00+00:00"},
            },
            "alerts": {"status": "ok", "items": []},
            "hourly": [],
            "tide": {"hilo": []},
        }

    def _surfing_result(self):
        limited = {
            "status": "Limited",
            "score": None,
            "rating": None,
            "confidence": "Limited",
            "best_window": None,
            "ranking_eligible": False,
            "reasons": [],
        }
        return {
            "activity": "surfing",
            "location": "san-diego",
            "today": dict(limited),
            "tomorrow": dict(limited),
            "hourly": {"today": [], "tomorrow": []},
            "safety_disclaimer": "Surf Conditions Score is a planning metric, not a safety guarantee or a break-specific forecast.",
        }

    def test_surfing_location_and_hub_use_surfing_specific_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot_path = root / "data" / "conditions" / "san-diego.json"
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(json.dumps(self._snapshot()), encoding="utf-8")

            render_activity_outputs(
                root,
                {"san-diego": LOCATIONS["san-diego"]},
                {"surfing": {"san-diego": self._surfing_result()}},
            )

            location_html = (root / activity_page_path(LOCATIONS["san-diego"], "surfing")).read_text(encoding="utf-8")
            hub_html = (root / "surfing" / "index.html").read_text(encoding="utf-8")

            for html in (location_html, hub_html):
                self.assertIn("Surf Conditions Score", html)
                self.assertNotIn("Fishing Score &amp; Best Fishing Time", html)
                self.assertNotIn("Fishing Score is", html)
                self.assertNotIn("catch guarantee", html)
                self.assertNotIn("lunar influence", html)

            self.assertIn("Daylight context", location_html)


if __name__ == "__main__":
    unittest.main()
