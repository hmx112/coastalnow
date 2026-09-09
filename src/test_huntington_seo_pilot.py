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


class HuntingtonSeoPilotTests(unittest.TestCase):
    def _render(self, slug: str) -> str:
        location = LOCATIONS[slug]
        data = json.loads((ROOT / "public" / location["data_path"]).read_text(encoding="utf-8"))
        now = datetime.fromisoformat(data["generated_at_local"])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, data, output, mode="live", now=now)
            return output.read_text(encoding="utf-8")

    def test_huntington_answer_first_block_precedes_activity_cards(self):
        html = self._render("huntington-beach")
        self.assertIn('class="tide-answer"', html)
        self.assertIn("NEXT TIDE", html)
        self.assertIn("Today's range", html)
        self.assertLess(html.index('class="tide-answer"'), html.index("ACTIVITY_PRIMARY_START"))
        self.assertLess(html.index("Your next tides"), html.index("ACTIVITY_PRIMARY_START"))

    def test_huntington_keeps_existing_title_and_meta_description(self):
        html = self._render("huntington-beach")
        self.assertIn("<title>Huntington Beach Tide Times Today | CoastalNow</title>", html)
        self.assertIn(
            '<meta name="description" content="Huntington Beach tide times and tide outlook for Huntington Beach, California.">',
            html,
        )

    def test_non_pilot_location_keeps_existing_activity_first_layout(self):
        html = self._render("san-diego")
        self.assertNotIn('class="tide-answer"', html)
        self.assertLess(html.index("ACTIVITY_PRIMARY_START"), html.index("Your next tides"))


if __name__ == "__main__":
    unittest.main()
