import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.safety import SafetyDecision


class ActivitySafetyTests(unittest.TestCase):
    def test_penalties_accumulate_before_cap(self):
        decision = SafetyDecision()
        decision.add_penalty(10, "fog")
        decision.add_penalty(5, "heavy-rain")
        result = decision.apply(82)
        self.assertEqual(result["penalty"], 15.0)
        self.assertEqual(result["cap"], 100.0)
        self.assertEqual(result["final_score"], 67.0)
        self.assertFalse(result["hard_stop"])
        self.assertEqual(result["status"], "normal")

    def test_strictest_active_cap_wins(self):
        decision = SafetyDecision()
        decision.add_cap(69, "moderate-exposure")
        decision.add_cap(39, "strong-wind")
        decision.add_penalty(5, "rain")
        result = decision.apply(95)
        self.assertEqual(result["cap"], 39.0)
        self.assertEqual(result["final_score"], 39.0)
        self.assertEqual(result["reasons"], ["moderate-exposure", "strong-wind", "rain"])

    def test_penalty_cannot_push_normal_score_below_zero(self):
        decision = SafetyDecision()
        decision.add_penalty(80, "poor-visibility")
        result = decision.apply(30)
        self.assertEqual(result["final_score"], 0.0)

    def test_hard_stop_overrides_quality_penalties_and_caps(self):
        decision = SafetyDecision()
        decision.add_penalty(10, "rain")
        decision.add_cap(69, "exposure")
        decision.add_hard_stop("severe-thunderstorm-warning")
        result = decision.apply(98)
        self.assertTrue(result["hard_stop"])
        self.assertEqual(result["status"], "NOT RECOMMENDED")
        self.assertIsNone(result["final_score"])
        self.assertEqual(result["raw_quality_score"], 98.0)
        self.assertIn("severe-thunderstorm-warning", result["reasons"])

    def test_invalid_penalty_and_cap_values_are_rejected(self):
        decision = SafetyDecision()
        for value in (0, -1, 101):
            with self.assertRaises(ValueError):
                decision.add_penalty(value, "bad")
        for value in (-1, 101):
            with self.assertRaises(ValueError):
                decision.add_cap(value, "bad")
        with self.assertRaises(ValueError):
            decision.apply(101)


if __name__ == "__main__":
    unittest.main()
