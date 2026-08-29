import sys
import unittest
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

import generate_tides
from generate_tides import selected_locations
from locations import LOCATIONS


class GenerationTargetTests(unittest.TestCase):
    def test_default_generation_targets_only_live_noaa_locations(self):
        selected = selected_locations(None)
        expected = [
            location["slug"]
            for location in LOCATIONS.values()
            if location["status"] == "Live NOAA"
        ]
        self.assertEqual([location["slug"] for location in selected], expected)
        self.assertTrue(all(location["status"] == "Live NOAA" for location in selected))

    def test_explicit_location_selection_allows_any_catalog_location(self):
        preview_slugs = [
            slug for slug, location in LOCATIONS.items() if location["status"] == "Preview"
        ]
        slug = preview_slugs[0] if preview_slugs else next(iter(LOCATIONS))
        selected = selected_locations(slug)
        self.assertEqual([location["slug"] for location in selected], [slug])
        self.assertEqual(selected[0]["status"], LOCATIONS[slug]["status"])

    def test_subordinate_hilo_can_generate_half_cosine_curve(self):
        self.assertTrue(
            hasattr(generate_tides, "derive_curve_from_hilo"),
            "generate_tides must provide derive_curve_from_hilo for subordinate stations",
        )
        hilo = [
            {"t": "2026-08-28 22:00", "v": 0.0, "type": "L"},
            {"t": "2026-08-29 04:00", "v": 4.0, "type": "H"},
            {"t": "2026-08-29 10:00", "v": 0.0, "type": "L"},
            {"t": "2026-08-29 16:00", "v": 4.0, "type": "H"},
            {"t": "2026-08-29 22:00", "v": 0.0, "type": "L"},
            {"t": "2026-08-30 04:00", "v": 4.0, "type": "H"},
        ]
        curve = generate_tides.derive_curve_from_hilo(
            hilo,
            date(2026, 8, 29),
            date(2026, 8, 29),
            ZoneInfo("America/New_York"),
        )
        by_time = {item["t"]: item["v"] for item in curve}
        self.assertEqual(len(curve), 48)
        self.assertAlmostEqual(by_time["2026-08-29 04:00"], 4.0, places=3)
        self.assertAlmostEqual(by_time["2026-08-29 07:00"], 2.0, places=3)
        self.assertAlmostEqual(by_time["2026-08-29 10:00"], 0.0, places=3)


if __name__ == "__main__":
    unittest.main()

def test_live_pacific_locations_use_pacific_time_label():
    from locations import LOCATIONS
    assert LOCATIONS["san-diego"]["time_label"] == "Pacific time"
    assert LOCATIONS["los-angeles"]["time_label"] == "Pacific time"