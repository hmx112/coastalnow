import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.fishing import (
    FISHING_HARD_STOP_EVENTS,
    fishing_confidence,
    fishing_safety_decision,
    wave_exposure_index,
)


def alert(event, *, headline="", description="", severity="Severe"):
    return {
        "id": event.lower().replace(" ", "-"),
        "event": event,
        "headline": headline,
        "description": description,
        "severity": severity,
        "certainty": "Likely",
        "urgency": "Immediate",
    }


class FishingSafetyTests(unittest.TestCase):
    def test_every_initial_official_hard_stop_event_blocks_normal_recommendation(self):
        expected = {
            "Tornado Warning",
            "Hurricane Warning",
            "Tropical Storm Warning",
            "Storm Surge Warning",
            "Tsunami Warning",
            "Extreme Wind Warning",
            "Severe Thunderstorm Warning",
            "High Surf Warning",
            "Special Marine Warning",
            "Coastal Flood Warning",
            "Flash Flood Warning",
        }
        self.assertEqual(FISHING_HARD_STOP_EVENTS, expected)
        for event in sorted(expected):
            decision = fishing_safety_decision(
                {"wind_mph": 5, "gust_mph": 8, "wave_height_ft": 1, "wave_period_s": 8, "condition_text": "Clear"},
                [alert(event)],
                coast_bearing=None,
            )
            result = decision.apply(96)
            self.assertTrue(result["hard_stop"], event)
            self.assertEqual(result["status"], "NOT RECOMMENDED", event)
            self.assertIsNone(result["final_score"], event)

    def test_high_rip_current_risk_is_hard_stop_other_statement_is_strong_cap(self):
        high = fishing_safety_decision(
            {"wind_mph": 8, "gust_mph": 10, "wave_height_ft": 2, "wave_period_s": 8, "condition_text": "Clear"},
            [alert("Rip Current Statement", headline="HIGH RIP CURRENT RISK")],
            coast_bearing=270,
        ).apply(95)
        self.assertTrue(high["hard_stop"])

        statement = fishing_safety_decision(
            {"wind_mph": 8, "gust_mph": 10, "wave_height_ft": 2, "wave_period_s": 8, "condition_text": "Clear"},
            [alert("Rip Current Statement", headline="Rip currents possible")],
            coast_bearing=270,
        ).apply(95)
        self.assertFalse(statement["hard_stop"])
        self.assertEqual(statement["cap"], 39)
        self.assertEqual(statement["final_score"], 39)

    def test_wind_safety_boundaries_apply_caps_then_hard_stop(self):
        cases = [
            ({"wind_mph": 24.9, "gust_mph": 34.9}, 100, False),
            ({"wind_mph": 25, "gust_mph": 10}, 59, False),
            ({"wind_mph": 10, "gust_mph": 35}, 59, False),
            ({"wind_mph": 30, "gust_mph": 10}, 39, False),
            ({"wind_mph": 10, "gust_mph": 40}, 39, False),
            ({"wind_mph": 40, "gust_mph": 10}, 100, True),
            ({"wind_mph": 10, "gust_mph": 50}, 100, True),
        ]
        for fields, cap, hard_stop in cases:
            hour = {**fields, "wave_height_ft": 1, "wave_period_s": 8, "condition_text": "Clear"}
            result = fishing_safety_decision(hour, [], coast_bearing=None).apply(95)
            self.assertEqual(result["hard_stop"], hard_stop, fields)
            self.assertEqual(result["cap"], cap, fields)

    def test_wave_exposure_boundaries_and_onshore_gust_escalation(self):
        self.assertAlmostEqual(wave_exposure_index(4, 8), 4.0)

        normal = fishing_safety_decision(
            {"wind_mph": 5, "gust_mph": 10, "wind_direction_deg": 270, "wave_height_ft": 3.4, "wave_period_s": 8, "condition_text": "Clear"},
            [], coast_bearing=270,
        ).apply(95)
        self.assertEqual(normal["cap"], 100)

        caution = fishing_safety_decision(
            {"wind_mph": 5, "gust_mph": 10, "wind_direction_deg": 270, "wave_height_ft": 3.5, "wave_period_s": 8, "condition_text": "Clear"},
            [], coast_bearing=270,
        ).apply(95)
        self.assertGreater(caution["penalty"], 0)

        cap69 = fishing_safety_decision(
            {"wind_mph": 5, "gust_mph": 10, "wind_direction_deg": 270, "wave_height_ft": 5.5, "wave_period_s": 8, "condition_text": "Clear"},
            [], coast_bearing=270,
        ).apply(95)
        self.assertEqual(cap69["cap"], 69)

        cap39 = fishing_safety_decision(
            {"wind_mph": 5, "gust_mph": 10, "wind_direction_deg": 270, "wave_height_ft": 7.5, "wave_period_s": 8, "condition_text": "Clear"},
            [], coast_bearing=270,
        ).apply(95)
        self.assertEqual(cap39["cap"], 39)

        hard = fishing_safety_decision(
            {"wind_mph": 5, "gust_mph": 10, "wind_direction_deg": 270, "wave_height_ft": 9.5, "wave_period_s": 8, "condition_text": "Clear"},
            [], coast_bearing=270,
        ).apply(95)
        self.assertTrue(hard["hard_stop"])

        # Strong wind coming from the seaward-facing bearing raises exposure one tier.
        escalated = fishing_safety_decision(
            {"wind_mph": 15, "gust_mph": 30, "wind_direction_deg": 270, "wave_height_ft": 5.0, "wave_period_s": 8, "condition_text": "Clear"},
            [], coast_bearing=270,
        ).apply(95)
        self.assertEqual(escalated["cap"], 69)

    def test_forecast_thunder_text_caps_even_without_warning(self):
        result = fishing_safety_decision(
            {"wind_mph": 5, "gust_mph": 8, "wave_height_ft": 1, "wave_period_s": 8, "condition_text": "Thunderstorms likely"},
            [], coast_bearing=None,
        ).apply(95)
        self.assertEqual(result["cap"], 39)

    def test_confidence_is_about_data_completeness_not_fishing_success(self):
        fresh = {"alerts": "fresh", "forecast": "fresh", "normal_safety_state_allowed": True, "high_medium_eligible": True}
        complete = {
            "wind_mph": 8, "precip_probability_pct": 10, "wave_height_ft": 2, "wave_period_s": 8,
            "water_temperature_f": 65,
        }
        self.assertEqual(fishing_confidence(complete, fresh, tide_available=True, solunar_available=True), "High")

        no_optional = dict(complete)
        no_optional["water_temperature_f"] = None
        self.assertEqual(fishing_confidence(no_optional, fresh, tide_available=True, solunar_available=False), "Medium")

        no_wave = dict(complete)
        no_wave["wave_height_ft"] = None
        self.assertEqual(fishing_confidence(no_wave, fresh, tide_available=True, solunar_available=True), "Limited")

        stale_alert = {**fresh, "alerts": "stale", "normal_safety_state_allowed": False, "high_medium_eligible": False}
        self.assertEqual(fishing_confidence(complete, stale_alert, tide_available=True, solunar_available=True), "Unavailable")
        self.assertEqual(fishing_confidence(complete, fresh, tide_available=False, solunar_available=True), "Unavailable")

    def test_raw_excellent_score_cannot_remain_rankable_under_hard_stop(self):
        result = fishing_safety_decision(
            {"wind_mph": 6, "gust_mph": 8, "wave_height_ft": 1.5, "wave_period_s": 8, "condition_text": "Clear"},
            [alert("High Surf Warning")],
            coast_bearing=None,
        ).apply(97)
        self.assertEqual(result["raw_quality_score"], 97)
        self.assertEqual(result["status"], "NOT RECOMMENDED")
        self.assertIsNone(result["final_score"])


if __name__ == "__main__":
    unittest.main()
