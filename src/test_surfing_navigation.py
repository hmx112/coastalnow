import tempfile
import unittest
from pathlib import Path

from activities.rendering.location_page import render_fishing_location
from activities.rendering.surfing_page import render_surfing_location
from generate_tides import render_location
from locations import LOCATIONS


SNAPSHOT = {
    "alerts": {"status": "ok", "items": []},
    "hourly": [],
    "tide": {"hilo": []},
}


def _result(activity):
    day = {
        "status": "Limited",
        "score": None,
        "rating": None,
        "confidence": "Limited",
        "best_window": None,
        "ranking_eligible": False,
        "reasons": [],
    }
    return {
        "activity": activity,
        "today": day,
        "tomorrow": day,
        "hourly": {"today": [], "tomorrow": []},
        "safety_disclaimer": f"{activity.title()} score is a planning metric, not a safety guarantee.",
    }


class SurfingNavigationTests(unittest.TestCase):
    def test_raw_san_diego_tide_renderer_links_fishing_and_surfing_before_tides(self):
        location = LOCATIONS["san-diego"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, None, output, mode="error", error_message="test")
            html = output.read_text(encoding="utf-8")
        fishing = "/tides/california/san-diego/fishing/"
        surfing = "/tides/california/san-diego/surfing/"
        self.assertIn(f'href="{fishing}"', html)
        self.assertIn(f'href="{surfing}"', html)
        self.assertLess(html.index(surfing), html.index("Your next tides"))
        primary = html.split("ACTIVITY_PRIMARY_START", 1)[1].split("ACTIVITY_PRIMARY_END", 1)[0]
        self.assertEqual(primary.count(fishing), 1)
        self.assertEqual(primary.count(surfing), 1)

    def test_raw_nonpilot_tide_renderer_has_no_surfing_link(self):
        location = LOCATIONS["key-west"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, None, output, mode="error", error_message="test")
            html = output.read_text(encoding="utf-8")
        self.assertIn('/tides/florida/key-west/fishing/', html)
        self.assertNotIn('/tides/florida/key-west/surfing/', html)

    def test_fishing_and_surfing_pages_cross_link_for_pilot(self):
        location = LOCATIONS["san-diego"]
        fishing = render_fishing_location(location, _result("fishing"), SNAPSHOT)
        surfing = render_surfing_location(location, _result("surfing"), SNAPSHOT)
        self.assertIn('/tides/california/san-diego/', fishing)
        self.assertIn('/tides/california/san-diego/surfing/', fishing)
        self.assertIn('/tides/california/san-diego/', surfing)
        self.assertIn('/tides/california/san-diego/fishing/', surfing)

    def test_nonpilot_fishing_page_has_no_dead_surfing_link(self):
        location = LOCATIONS["key-west"]
        fishing = render_fishing_location(location, _result("fishing"), SNAPSHOT)
        self.assertNotIn('/tides/florida/key-west/surfing/', fishing)

    def test_mobile_tide_activity_links_are_not_hidden(self):
        location = LOCATIONS["san-diego"]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "index.html"
            render_location(location, None, output, mode="error", error_message="test")
            html = output.read_text(encoding="utf-8")
        self.assertNotIn(".activity-primary-section{display:none}", html.replace(" ", ""))
        if ".nav>a{display:none}" in html:
            self.fail("generic mobile nav rule would hide Activity links")


if __name__ == "__main__":
    unittest.main()
