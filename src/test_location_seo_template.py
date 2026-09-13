import tempfile
import unittest
from pathlib import Path

from generate_tides import build_preview, render_location
from locations import LOCATIONS


class LocationSeoTemplateTests(unittest.TestCase):
    def test_live_location_metadata_covers_core_tide_search_intent(self):
        location = LOCATIONS["san-diego"]
        title = location["page_title"]
        description = location["meta_description"].lower()
        self.assertIn("Tide Times", title)
        self.assertIn("High", title)
        self.assertIn("Low", title)
        for phrase in ("high tide", "low tide", "tide chart", "7-day tide schedule"):
            self.assertIn(phrase, description)

    def test_answer_first_block_is_standard_for_live_location_pages(self):
        location = LOCATIONS["san-diego"]
        data, now = build_preview(location)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, data, output, mode="preview", now=now)
            html = output.read_text(encoding="utf-8")
        self.assertIn("NEXT TIDE", html)
        self.assertIn("FISHING", html)
        self.assertLess(html.index("NEXT TIDE"), html.index("FISHING"))

    def test_location_page_headings_cover_today_chart_and_schedule_intent(self):
        location = LOCATIONS["san-diego"]
        data, now = build_preview(location)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, data, output, mode="preview", now=now)
            html = output.read_text(encoding="utf-8")
        self.assertIn("Today’s High and Low Tides", html)
        self.assertIn("Today’s Tide Chart", html)
        self.assertIn("7-Day Tide Schedule", html)

    def test_location_page_has_visible_state_directory_route_and_nearby_links(self):
        location = LOCATIONS["san-diego"]
        data, now = build_preview(location)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, data, output, mode="preview", now=now)
            html = output.read_text(encoding="utf-8")
        self.assertIn("More California tide locations", html)
        self.assertGreaterEqual(html.count('class="place"'), 2)


if __name__ == "__main__":
    unittest.main()
