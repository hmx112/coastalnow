import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_tides import selected_locations


class GenerationTargetTests(unittest.TestCase):
    def test_default_generation_targets_only_live_noaa_locations(self):
        selected = selected_locations(None)
        self.assertEqual([location["slug"] for location in selected], ["san-diego", "los-angeles"])
        self.assertTrue(all(location["status"] == "Live NOAA" for location in selected))

    def test_explicit_location_selection_still_allows_preview_mode(self):
        selected = selected_locations("monterey")
        self.assertEqual([location["slug"] for location in selected], ["monterey"])
        self.assertEqual(selected[0]["status"], "Preview")


if __name__ == "__main__":
    unittest.main()

def test_live_pacific_locations_use_pacific_time_label():
    from locations import LOCATIONS
    assert LOCATIONS["san-diego"]["time_label"] == "Pacific time"
    assert LOCATIONS["los-angeles"]["time_label"] == "Pacific time"
