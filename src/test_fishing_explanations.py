import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class FishingExplanationTests(unittest.TestCase):
    def summarize(self, **overrides):
        from activities.explanations import summarize_fishing_result

        day = {
            "status": "normal",
            "score": 72,
            "rating": "Good",
            "confidence": "High",
            "reasons": [],
        }
        day.update(overrides)
        return summarize_fishing_result(day)

    def test_thunderstorm_constraint_leads_and_positive_factors_are_subordinate(self):
        text = self.summarize(
            score=39,
            rating="Poor",
            reasons=[
                "favorable-tide-movement",
                "light-wind",
                "manageable-sea-state",
                "forecast-thunder-cap",
            ],
        )
        self.assertTrue(text.startswith("Thunderstorm conditions"), text)
        self.assertIn("main reason", text)
        self.assertIn("otherwise favorable", text)
        self.assertIn("do not outweigh", text)
        self.assertLessEqual(text.count("."), 2)

    def test_not_recommended_prioritizes_hard_stop_over_positive_factors(self):
        text = self.summarize(
            status="NOT RECOMMENDED",
            score=None,
            rating=None,
            reasons=[
                "favorable-tide-movement",
                "manageable-sea-state",
                "high-rip-current-risk",
            ],
        )
        self.assertTrue(text.startswith("A high rip-current risk"), text)
        self.assertIn("not recommended", text.lower())
        self.assertIn("do not override", text)

    def test_low_score_without_explicit_safety_constraint_does_not_sound_positive(self):
        text = self.summarize(
            score=34,
            rating="Poor",
            reasons=["favorable-tide-movement", "light-wind"],
        )
        self.assertTrue(text.startswith("Today's overall Fishing Score is low"), text)
        self.assertIn("not enough", text)

    def test_high_score_can_lead_with_supportive_conditions(self):
        text = self.summarize(
            score=82,
            rating="Very Good",
            reasons=["favorable-tide-movement", "light-wind", "manageable-sea-state"],
        )
        self.assertTrue(text.startswith("Conditions are generally supportive"), text)
        self.assertIn("main positives", text)

    def test_limited_data_explains_data_state_instead_of_weather(self):
        text = self.summarize(
            status="Limited",
            score=None,
            rating=None,
            confidence="Limited",
            reasons=["favorable-tide-movement", "light-wind"],
        )
        self.assertIn("data is incomplete", text)
        self.assertNotIn("favorable", text.lower())
        self.assertNotIn("light", text.lower())

    def test_unavailable_data_does_not_infer_conditions(self):
        text = self.summarize(
            status="Unavailable",
            score=None,
            rating=None,
            confidence="Unavailable",
            reasons=["manageable-sea-state"],
        )
        self.assertIn("data is unavailable", text)
        self.assertNotIn("manageable", text.lower())

    def test_end_of_day_state_is_explained_as_timing_not_safety(self):
        text = self.summarize(
            status="No 3-hour window remaining",
            score=None,
            rating=None,
            confidence="High",
            reasons=[],
        )
        self.assertIn("three hours", text.lower())
        self.assertIn("timing state", text.lower())
        self.assertIn("not a statement that coastal conditions are unsafe", text.lower())


if __name__ == "__main__":
    unittest.main()
