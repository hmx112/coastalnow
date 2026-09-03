import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIDE_REFRESH = ROOT / ".github" / "workflows" / "update-san-diego.yml"


class TideRefreshOnMainMergeTests(unittest.TestCase):
    def test_main_source_merges_trigger_tide_refresh(self):
        text = TIDE_REFRESH.read_text(encoding="utf-8")
        expected = '''  push:\n    branches:\n      - main\n    paths:\n      - "src/**"\n      - ".github/workflows/update-san-diego.yml"\n'''
        self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
