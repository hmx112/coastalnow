import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_tides import render_location
from locations import LOCATIONS

ROOT = Path(__file__).resolve().parents[1]


class AnswerFirstTideSeoTests(unittest.TestCase):
    def _render(self, slug: str) -> str:
        location = LOCATIONS[slug]
        data = json.loads((ROOT / "public" / location["data_path"]).read_text(encoding="utf-8"))
        now = datetime.fromisoformat(data["generated_at_local"])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, data, output, mode="live", now=now)
            return output.read_text(encoding="utf-8")

    def _assert_answer_first(self, html: str) -> None:
        self.assertIn('class="tide-answer"', html)
        self.assertIn("NEXT TIDE", html)
        self.assertIn("Next high", html)
        self.assertIn("Next low", html)
        self.assertIn("Today's range", html)
        self.assertIn("Today’s High and Low Tides", html)
        self.assertEqual(html.count("ACTIVITY_PRIMARY_START"), 1)
        self.assertLess(html.index('class="tide-answer"'), html.index("ACTIVITY_PRIMARY_START"))
        self.assertLess(html.index("Today’s High and Low Tides"), html.index("ACTIVITY_PRIMARY_START"))

    def test_huntington_keeps_answer_first_layout(self):
        self._assert_answer_first(self._render("huntington-beach"))

    def test_huntington_uses_strengthened_tide_title_and_meta_description(self):
        html = self._render("huntington-beach")
        self.assertIn(
            "<title>Huntington Beach Tide Times, High & Low Tides Today | CoastalNow</title>",
            html,
        )
        self.assertIn(
            '<meta name="description" content="See today’s high tide and low tide times for Huntington Beach, California, with a tide chart, 7-day tide schedule, and NOAA source details.">',
            html,
        )

    def test_non_pilot_location_now_uses_same_answer_first_layout(self):
        self._assert_answer_first(self._render("san-diego"))


if __name__ == "__main__":
    unittest.main()
