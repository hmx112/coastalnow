import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS
from promote_location import validate_activity_geography

ROOT = Path(__file__).resolve().parents[1]
PROMOTION = ROOT / ".github" / "workflows" / "promote-location.yml"
TIDE_REFRESH = ROOT / ".github" / "workflows" / "update-san-diego.yml"
ACTIVITY_REFRESH = ROOT / ".github" / "workflows" / "update-activities.yml"
ALERT_REFRESH = ROOT / ".github" / "workflows" / "update-activity-alerts.yml"


class ActivityWorkflowTests(unittest.TestCase):
    def test_every_current_catalog_location_passes_activity_geography_validation(self):
        for slug, location in LOCATIONS.items():
            validate_activity_geography(location)

    def test_activity_geography_validation_rejects_missing_or_invalid_points(self):
        base = {
            "slug": "galveston",
            "activity": {
                "shore_point": {"latitude": 29.30, "longitude": -94.79},
                "marine_point": {"latitude": 29.25, "longitude": -94.75},
                "coast_bearing": 135,
            },
        }
        validate_activity_geography(base)
        missing = {"slug": "bad", "activity": {"shore_point": base["activity"]["shore_point"]}}
        with self.assertRaises(ValueError):
            validate_activity_geography(missing)
        invalid = {
            "slug": "bad",
            "activity": {
                "shore_point": {"latitude": 95, "longitude": 0},
                "marine_point": {"latitude": 0, "longitude": -190},
            },
        }
        with self.assertRaises(ValueError):
            validate_activity_geography(invalid)

    def test_promotion_generates_activity_outputs_before_site_build_and_stages_them(self):
        text = PROMOTION.read_text(encoding="utf-8")
        self.assertIn('python src/generate_activities.py --location "$slug"', text)
        self.assertLess(text.index('python src/generate_activities.py --location "$slug"'), text.index("python src/build_site.py"))
        self.assertIn("src/test_activity_generation.py", text)
        self.assertIn("src/test_activity_rendering.py", text)
        self.assertIn("src/test_activity_seo_navigation.py", text)
        self.assertIn("public/fishing", text)
        self.assertNotIn("[skip ci]", text.lower())
        self.assertIn('"promotion/**"', text)
        self.assertIn('git rm "$request"', text)

    def test_full_activity_refresh_runs_every_three_hours_with_shared_concurrency_group(self):
        text = ACTIVITY_REFRESH.read_text(encoding="utf-8")
        self.assertIn('cron: "23 */3 * * *"', text)
        self.assertIn("group: coastalnow-activity-writes", text)
        self.assertIn("python src/generate_activities.py", text)
        self.assertNotIn("--alerts-only", text)
        self.assertIn("python src/build_site.py", text)
        self.assertIn("public/data/conditions", text)
        self.assertIn("public/data/activities", text)
        self.assertIn("public/fishing", text)
        self.assertNotIn("[skip ci]", text.lower())

    def test_alert_refresh_runs_hourly_and_reuses_the_same_write_lock(self):
        text = ALERT_REFRESH.read_text(encoding="utf-8")
        self.assertIn('cron: "41 * * * *"', text)
        self.assertIn("group: coastalnow-activity-writes", text)
        self.assertIn("python src/generate_activities.py --alerts-only", text)
        self.assertIn("python src/build_site.py", text)
        self.assertNotIn("[skip ci]", text.lower())

    def test_tide_refresh_remains_six_hourly_and_does_not_gain_ci_skip_markers(self):
        text = TIDE_REFRESH.read_text(encoding="utf-8")
        self.assertIn('cron: "17 */6 * * *"', text)
        self.assertNotIn("[skip ci]", text.lower())


if __name__ == "__main__":
    unittest.main()
