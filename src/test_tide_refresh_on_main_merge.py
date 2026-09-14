import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIDE_REFRESH = ROOT / ".github" / "workflows" / "update-san-diego.yml"


class TideRefreshOnMainMergeTests(unittest.TestCase):
    def test_main_source_merges_trigger_tide_refresh(self):
        text = TIDE_REFRESH.read_text(encoding="utf-8")
        expected = '''  push:\n    branches:\n      - main\n    paths:\n      - "src/**"\n      - ".github/workflows/update-san-diego.yml"\n'''
        self.assertIn(expected, text)

    def test_tide_refresh_generates_activity_data_before_site_build(self):
        text = TIDE_REFRESH.read_text(encoding="utf-8")
        activity_generation = "python src/generate_activities.py"
        site_build = "python src/build_site.py"
        self.assertIn(activity_generation, text)
        self.assertIn(site_build, text)
        self.assertLess(text.index(activity_generation), text.index(site_build))

    def test_tide_refresh_checks_primary_activity_cta(self):
        text = TIDE_REFRESH.read_text(encoding="utf-8")
        self.assertIn("python src/test_tide_body_activity_cta.py", text)


if __name__ == "__main__":
    unittest.main()
