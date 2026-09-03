import unittest

from activities.rendering.surfing_page import render_surfing_hub, render_surfing_location
from locations import LOCATIONS


LOCATION = LOCATIONS["san-diego"]
SNAPSHOT = {
    "alerts": {"status": "ok", "items": []},
    "hourly": [
        {
            "time": "2026-09-03T10:00:00-07:00",
            "wave_height_ft": 3.0,
            "wave_period_s": 11.0,
            "wind_mph": 6.0,
            "gust_mph": 8.0,
            "precip_probability_pct": 10.0,
        }
    ],
    "tide": {"hilo": [{"t": "2026-09-03 11:00", "type": "H", "v": "4.2"}]},
}


def _row():
    return {
        "time": "2026-09-03T10:00:00-07:00",
        "components": {
            "wave_height": 100,
            "wave_period": 100,
            "wind": 90,
            "weather": 100,
            "daylight": 100,
        },
        "final_score": 97.5,
        "hard_stop": False,
        "confidence": "High",
        "available": True,
        "ranking_eligible": True,
        "reasons": ["moderate-wave-height", "organized-wave-period"],
    }


def _result(status="normal", confidence="High", score=91.0):
    row = _row()
    if status == "NOT RECOMMENDED":
        row.update({"final_score": None, "hard_stop": True, "ranking_eligible": False})
    elif confidence in {"Limited", "Unavailable"}:
        row.update({"final_score": None, "ranking_eligible": False, "available": confidence != "Unavailable", "confidence": confidence})
    day = {
        "status": status,
        "score": score,
        "rating": "Excellent" if score is not None else None,
        "confidence": confidence,
        "best_window": {"start": row["time"], "end": "2026-09-03T13:00:00-07:00"} if score is not None else None,
        "ranking_eligible": status == "normal" and confidence in {"High", "Medium"},
        "reasons": row["reasons"],
    }
    if status != "normal" or confidence in {"Limited", "Unavailable"}:
        day["score"] = None
        day["rating"] = None
        day["best_window"] = None
        day["ranking_eligible"] = False
    return {
        "today": day,
        "tomorrow": day,
        "hourly": {"today": [row], "tomorrow": []},
        "safety_disclaimer": "Surf Conditions Score is a planning metric, not a safety guarantee or a break-specific forecast.",
    }


class SurfingRenderingTests(unittest.TestCase):
    def test_location_page_separates_normalized_scores_from_raw_context(self):
        html = render_surfing_location(LOCATION, _result(), SNAPSHOT)
        self.assertIn("San Diego Surf Conditions", html)
        self.assertIn("0–100 composite planning score", html)
        self.assertIn("not a safety guarantee", html)
        self.assertIn("not break-specific", html)
        for label in (
            "Wave height score",
            "Wave period score",
            "Wind score",
            "Weather score",
            "Daylight score",
        ):
            self.assertIn(label, html)
        self.assertIn("Wave height", html)
        self.assertIn("3.0 ft", html)
        self.assertIn("Wave period", html)
        self.assertIn("11.0 sec", html)
        self.assertIn("Wind", html)
        self.assertIn("6.0 mph", html)
        self.assertIn("TIDE CONTEXT", html)
        self.assertIn('/tides/california/san-diego/', html)
        self.assertIn('/tides/california/san-diego/fishing/', html)
        self.assertNotIn("NOAA logo", html)
        self.assertNotIn("NWS logo", html)

    def test_limited_and_unavailable_suppress_headline_numeric_score(self):
        for confidence in ("Limited", "Unavailable"):
            with self.subTest(confidence=confidence):
                html = render_surfing_location(LOCATION, _result(status=confidence, confidence=confidence, score=None), SNAPSHOT)
                self.assertIn(f">{confidence}<", html)
                self.assertNotIn('class="activity-score-value">91', html)

    def test_not_recommended_has_priority_over_limited_numeric_presentation(self):
        html = render_surfing_location(
            LOCATION,
            _result(status="NOT RECOMMENDED", confidence="Limited", score=None),
            SNAPSHOT,
        )
        self.assertIn("NOT RECOMMENDED", html)
        self.assertIn("Safety condition takes priority", html)
        self.assertNotIn('class="activity-score-value">91', html)

    def test_hub_uses_only_supplied_results_and_hides_limited_numbers(self):
        locations = {
            "san-diego": LOCATIONS["san-diego"],
            "la-jolla": LOCATIONS["la-jolla"],
            "key-west": LOCATIONS["key-west"],
        }
        results = {
            "san-diego": _result(),
            "la-jolla": _result(status="Limited", confidence="Limited", score=None),
        }
        html = render_surfing_hub(locations, results)
        self.assertIn("San Diego", html)
        self.assertIn("La Jolla", html)
        self.assertNotIn("Key West", html)
        self.assertIn("Limited", html)
        self.assertNotIn("La Jolla</h3><p>CA</p><strong>91", html)
        self.assertIn("planning scores", html)
        self.assertIn("not a safety guarantee", html)


if __name__ == "__main__":
    unittest.main()
