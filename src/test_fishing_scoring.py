import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.explanations import explain_reasons
from activities.scoring.engine import weighted_score
from activities.scoring.fishing import (
    FISHING_WEIGHTS,
    solunar_quality,
    tide_quality,
    time_of_day_quality,
    water_temperature_quality,
    wave_quality,
    weather_quality,
    wind_quality,
)


class FishingQualityTests(unittest.TestCase):
    def test_weights_match_approved_fishing_design(self):
        self.assertEqual(FISHING_WEIGHTS, {
            "tide": 0.30,
            "wind": 0.20,
            "wave": 0.15,
            "weather": 0.15,
            "time_of_day": 0.10,
            "solunar": 0.05,
            "water_temperature": 0.05,
        })
        self.assertAlmostEqual(sum(FISHING_WEIGHTS.values()), 1.0)

    def test_tide_mid_phase_is_best_and_turning_points_are_low(self):
        self.assertEqual(tide_quality(0.0), 0.0)
        self.assertEqual(tide_quality(0.5), 100.0)
        self.assertEqual(tide_quality(1.0), 0.0)
        self.assertAlmostEqual(tide_quality(0.25), tide_quality(0.75), places=1)
        with self.assertRaises(ValueError):
            tide_quality(1.1)

    def test_wind_quality_boundaries(self):
        expected = {
            0: 85, 3: 85,
            4: 100, 12: 100,
            13: 80, 18: 80,
            19: 55, 24: 55,
            25: 25, 30: 25,
            31: 0,
        }
        for speed, score in expected.items():
            self.assertEqual(wind_quality(speed), score, speed)
        self.assertIsNone(wind_quality(None))

    def test_wave_quality_height_bands_and_long_period_modifier(self):
        self.assertEqual(wave_quality(0.5, 8), 85)
        self.assertEqual(wave_quality(1, 8), 100)
        self.assertEqual(wave_quality(3, 8), 100)
        self.assertEqual(wave_quality(3.1, 8), 75)
        self.assertEqual(wave_quality(5.1, 8), 45)
        self.assertEqual(wave_quality(7.1, 8), 20)
        self.assertEqual(wave_quality(9.1, 8), 0)
        self.assertLess(wave_quality(2, 15), wave_quality(2, 8))
        self.assertIsNone(wave_quality(None, 8))

    def test_weather_precipitation_quality_boundaries(self):
        expected = {0: 100, 20: 100, 21: 75, 40: 75, 41: 50, 60: 50, 61: 30, 100: 30}
        for probability, score in expected.items():
            self.assertEqual(weather_quality(probability, "Partly Cloudy"), score, probability)
        self.assertEqual(weather_quality(20, "Heavy Rain"), 80)
        self.assertIsNone(weather_quality(None, "Unknown"))

    def test_time_of_day_favors_dawn_and_dusk_without_zeroing_night(self):
        solar = {
            "civil_dawn": "2026-08-30T05:30:00-07:00",
            "sunrise": "2026-08-30T06:00:00-07:00",
            "sunset": "2026-08-30T19:00:00-07:00",
            "civil_dusk": "2026-08-30T19:30:00-07:00",
        }
        self.assertEqual(time_of_day_quality("2026-08-30T06:15:00-07:00", solar), 100)
        self.assertEqual(time_of_day_quality("2026-08-30T13:00:00-07:00", solar), 85)
        self.assertEqual(time_of_day_quality("2026-08-30T19:15:00-07:00", solar), 100)
        self.assertEqual(time_of_day_quality("2026-08-30T23:00:00-07:00", solar), 60)

    def test_optional_solunar_and_water_temperature_do_not_get_reweighted(self):
        self.assertIsNone(solunar_quality(None))
        self.assertIsNone(water_temperature_quality(None))
        components = {
            "tide": 100, "wind": 100, "wave": 100, "weather": 100,
            "time_of_day": 100, "solunar": None, "water_temperature": None,
        }
        # Two unknown 5% factors remain neutral 50 rather than being discarded.
        self.assertEqual(weighted_score(components, FISHING_WEIGHTS), 95.0)
        self.assertGreaterEqual(solunar_quality(0.0), 50)
        self.assertLessEqual(solunar_quality(0.25), solunar_quality(0.0))

    def test_reason_explanations_are_deterministic_and_non_guaranteeing(self):
        text = explain_reasons(["favorable-tide-movement", "light-wind", "manageable-sea-state"])
        self.assertEqual(
            text,
            "Moving tide supports the fishing window. Winds are light to moderate. Nearshore wave conditions are manageable.",
        )
        self.assertNotIn("safe", text.lower())
        self.assertNotIn("catch", text.lower())


if __name__ == "__main__":
    unittest.main()
