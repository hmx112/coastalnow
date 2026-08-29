import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from locations import LOCATIONS


class LocationTimezoneTests(unittest.TestCase):
    def test_florida_panhandle_locations_use_central_time(self):
        self.assertEqual(LOCATIONS["destin"]["timezone"], "America/Chicago")
        self.assertEqual(LOCATIONS["panama-city-beach"]["timezone"], "America/Chicago")
        self.assertEqual(LOCATIONS["destin"]["time_label"], "Central time")
        self.assertEqual(LOCATIONS["panama-city-beach"]["time_label"], "Central time")


if __name__ == "__main__":
    unittest.main()
