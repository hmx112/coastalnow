import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from promote_location import validate_station_id


class AlphanumericStationTests(unittest.TestCase):
    def test_official_seven_character_station_ids_are_supported(self):
        self.assertEqual(validate_station_id("TEC2837"), "TEC2837")
        self.assertEqual(validate_station_id("twc0427"), "TWC0427")
        self.assertEqual(validate_station_id("9410170"), "9410170")

    def test_station_ids_must_be_exactly_seven_alphanumeric_characters(self):
        for value in ("ABC", "123456", "ABCDEFGH", "ABC-123"):
            with self.assertRaises(ValueError, msg=value):
                validate_station_id(value)


if __name__ == "__main__":
    unittest.main()
