"""Offline tests for delayed, station-scoped NOAA retries.

NOAA predictions can intermittently return 'No Predictions data was found'
for a valid station/datum. Successful locations must never be unnecessarily
refetched; a genuinely unavailable location must still fail the workflow.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_tides


A = {"slug": "san-diego"}
B = {"slug": "cocoa-beach"}
C = {"slug": "dana-point"}


class DelayedNOAARetryTests(unittest.TestCase):
    def test_all_successful_stations_never_retry_or_sleep(self):
        with patch.object(generate_tides, "generate_one", return_value=0) as generate, \
             patch.object(generate_tides.time, "sleep") as sleep:
            self.assertEqual(generate_tides.generate_locations_with_retry([A, B, C]), 0)
            self.assertEqual([call.args[0]["slug"] for call in generate.call_args_list],
                             ["san-diego", "cocoa-beach", "dana-point"])
            sleep.assert_not_called()

    def test_only_failed_station_retried_after_first_pass(self):
        responses = {
            "san-diego": [0],
            "cocoa-beach": [2, 0],
            "dana-point": [0],
        }
        called = []

        def mock_generate(location, preview=False):
            called.append(location["slug"])
            return responses[location["slug"]].pop(0)

        with patch.object(generate_tides, "generate_one", side_effect=mock_generate), \
             patch.object(generate_tides.time, "sleep") as sleep:
            self.assertEqual(generate_tides.generate_locations_with_retry([A, B, C]), 0)
            self.assertEqual(called, ["san-diego", "cocoa-beach",
                                      "dana-point", "cocoa-beach"])
            sleep.assert_called_once_with(8)

    def test_persistent_failure_is_not_silenced_and_successes_remain_untouched(self):
        called = []

        def mock_generate(location, preview=False):
            called.append(location["slug"])
            return 2 if location["slug"] == "dana-point" else 0

        with patch.object(generate_tides, "generate_one", side_effect=mock_generate), \
             patch.object(generate_tides.time, "sleep") as sleep:
            self.assertEqual(generate_tides.generate_locations_with_retry([A, B, C]), 2)
            self.assertEqual(called, ["san-diego", "cocoa-beach",
                                      "dana-point", "dana-point"])
            sleep.assert_called_once_with(8)

    def test_preview_mode_does_not_retry_or_wait(self):
        with patch.object(generate_tides, "generate_one", return_value=2) as generate, \
             patch.object(generate_tides.time, "sleep") as sleep:
            self.assertEqual(
                generate_tides.generate_locations_with_retry([A], preview=True), 2)
            self.assertEqual(generate.call_count, 1)
            self.assertTrue(generate.call_args.kwargs["preview"])
            sleep.assert_not_called()

    def test_multiple_failures_retry_once_each_and_keep_error_when_one_persists(self):
        attempts = {"san-diego": [2, 0], "cocoa-beach": [2, 2],
                    "dana-point": [0]}
        called = []

        def mock_generate(location, preview=False):
            called.append(location["slug"])
            return attempts[location["slug"]].pop(0)

        with patch.object(generate_tides, "generate_one", side_effect=mock_generate), \
             patch.object(generate_tides.time, "sleep") as sleep:
            self.assertEqual(generate_tides.generate_locations_with_retry([A, B, C]), 2)
            self.assertEqual(called, ["san-diego", "cocoa-beach",
                                      "dana-point", "san-diego", "cocoa-beach"])
            sleep.assert_called_once_with(8)


if __name__ == "__main__":
    unittest.main()
