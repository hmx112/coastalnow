import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.engine import best_continuous_window, rating_for_score, weighted_score


class ActivityScoringEngineTests(unittest.TestCase):
    def test_weighted_score_uses_neutral_unknown_without_redistributing_weight(self):
        weights = {"tide": 0.5, "wind": 0.3, "water": 0.2}
        self.assertEqual(weighted_score({"tide": 100, "wind": 80, "water": 50}, weights), 84.0)
        self.assertEqual(weighted_score({"tide": 100, "wind": 80, "water": None}, weights), 84.0)
        # If water were incorrectly discarded/reweighted this would be 95; it must stay 84.
        self.assertNotEqual(weighted_score({"tide": 100, "wind": 80, "water": None}, weights), 95.0)

    def test_weighted_score_rejects_bad_weights_and_component_ranges(self):
        with self.assertRaises(ValueError):
            weighted_score({"a": 50}, {"a": 0})
        with self.assertRaises(ValueError):
            weighted_score({"a": 101}, {"a": 1})
        with self.assertRaises(ValueError):
            weighted_score({"a": 50}, {"a": 0.8, "b": 0.3})

    def test_rating_boundaries_are_deterministic(self):
        expected = {
            100: "Excellent", 90: "Excellent",
            89: "Good", 75: "Good",
            74: "Fair", 60: "Fair",
            59: "Poor", 40: "Poor",
            39: "Unfavorable", 0: "Unfavorable",
        }
        for score, label in expected.items():
            self.assertEqual(rating_for_score(score), label)

    def test_best_three_hour_window_uses_mean_and_minimum_and_excludes_unsafe_hours(self):
        hourly = [
            {"time": "2026-08-30T05:00:00-07:00", "final_score": 80, "available": True, "hard_stop": False, "confidence": "High"},
            {"time": "2026-08-30T06:00:00-07:00", "final_score": 90, "available": True, "hard_stop": False, "confidence": "High"},
            {"time": "2026-08-30T07:00:00-07:00", "final_score": 100, "available": True, "hard_stop": False, "confidence": "Medium"},
            {"time": "2026-08-30T08:00:00-07:00", "final_score": 99, "available": True, "hard_stop": True, "confidence": "High"},
            {"time": "2026-08-30T09:00:00-07:00", "final_score": 95, "available": True, "hard_stop": False, "confidence": "High"},
        ]
        best = best_continuous_window(hourly, hours=3)
        # First three: mean=90, minimum=80 => 0.7*90 + 0.3*80 = 87.
        self.assertEqual(best["score"], 87.0)
        self.assertEqual(best["start"], "2026-08-30T05:00:00-07:00")
        self.assertEqual(best["end"], "2026-08-30T08:00:00-07:00")
        self.assertEqual(best["confidence"], "Medium")

    def test_window_requires_consecutive_clock_hours(self):
        hourly = [
            {"time": "2026-08-30T05:00:00-07:00", "final_score": 90, "available": True, "hard_stop": False, "confidence": "High"},
            {"time": "2026-08-30T07:00:00-07:00", "final_score": 90, "available": True, "hard_stop": False, "confidence": "High"},
            {"time": "2026-08-30T08:00:00-07:00", "final_score": 90, "available": True, "hard_stop": False, "confidence": "High"},
        ]
        self.assertIsNone(best_continuous_window(hourly, hours=3))


if __name__ == "__main__":
    unittest.main()
