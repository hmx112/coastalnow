import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.hub_page import render_fishing_hub


class FishingHubDataStateTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "name": "Bar Harbor",
            "state": "Maine",
            "state_code": "ME",
            "state_slug": "maine",
            "slug": "bar-harbor",
            "page_path": "tides/maine/bar-harbor/index.html",
        }

    def result(self, *, status, confidence, score=None, rating=None):
        day = {
            "status": status,
            "confidence": confidence,
            "score": score,
            "rating": rating,
            "ranking_eligible": confidence in {"High", "Medium"} and score is not None,
            "best_window": None,
            "reasons": [],
        }
        return {"activity": "fishing", "today": day, "tomorrow": dict(day)}

    def test_limited_group_hides_numeric_recommendation_even_if_diagnostic_score_exists(self):
        results = {
            "bar-harbor": self.result(
                status="Limited",
                confidence="Limited",
                score=88.4,
                rating="Good",
            )
        }
        html = render_fishing_hub({"bar-harbor": self.location}, results)
        limited = html.split("<h3>Limited / Unavailable</h3>", 1)[1]
        self.assertIn("Bar Harbor", limited)
        self.assertIn("Limited", limited)
        self.assertNotIn("88.4 Good", limited)

    def test_end_of_day_locations_have_their_own_group_not_poor_unfavorable(self):
        results = {
            "bar-harbor": self.result(
                status="No 3-hour window remaining",
                confidence="High",
            )
        }
        html = render_fishing_hub({"bar-harbor": self.location}, results)
        self.assertIn("<h3>Today’s Window Closed</h3>", html)
        closed = html.split("<h3>Today’s Window Closed</h3>", 1)[1]
        self.assertIn("Bar Harbor", closed)
        if "<h3>Poor / Unfavorable</h3>" in html:
            poor = html.split("<h3>Poor / Unfavorable</h3>", 1)[1].split("</section>", 1)[0]
            self.assertNotIn("Bar Harbor", poor)


if __name__ == "__main__":
    unittest.main()
