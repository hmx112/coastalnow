import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.hub_page import render_fishing_hub
from activities.rendering.location_page import render_fishing_location
from site_generator import build_directory_pages


class ActivityAttributionTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "name": "San Diego",
            "state": "California",
            "state_code": "CA",
            "state_slug": "california",
            "slug": "san-diego",
            "page_path": "tides/california/san-diego/index.html",
            "timezone": "America/Los_Angeles",
            "station": "9410170",
            "station_name": "San Diego, San Diego Bay",
            "coverage_mode": "local",
        }
        day = {
            "status": "normal",
            "score": 82.0,
            "rating": "Good",
            "confidence": "High",
            "best_window": None,
            "ranking_eligible": True,
            "reasons": ["light-wind"],
        }
        self.result = {
            "activity": "fishing",
            "today": day,
            "tomorrow": dict(day),
            "hourly": {"today": [], "tomorrow": []},
            "safety_disclaimer": "Fishing Score is a planning metric, not a safety guarantee.",
        }
        self.snapshot = {
            "hourly": [],
            "alerts": {"status": "ok", "items": []},
            "tide": {"hilo": []},
            "providers": {
                "alerts": {"source": "NWS", "status": "ok", "fetched_at_utc": "2026-08-30T12:00:00+00:00"},
                "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": "2026-08-30T12:00:00+00:00"},
                "marine": {"source": "NWS forecastGridData", "status": "ok", "fetched_at_utc": "2026-08-30T12:00:00+00:00"},
                "tide": {"source": "NOAA/NOS/CO-OPS", "status": "ok", "fetched_at_utc": "2026-08-30T09:00:00+00:00"},
                "water_temperature": {"source": "NOAA/NOS/CO-OPS", "status": "ok", "fetched_at_utc": "2026-08-30T12:00:00+00:00"},
            },
        }

    def test_location_page_distinguishes_government_sources_from_coastalnow_calculations(self):
        html = render_fishing_location(self.location, self.result, self.snapshot)
        self.assertIn("Data sources & methodology", html)
        self.assertIn("NOAA/NOS/CO-OPS", html)
        self.assertIn("National Weather Service", html)
        self.assertIn("San Diego, San Diego Bay", html)
        self.assertIn("9410170", html)
        self.assertIn("Fishing Score &amp; Best Fishing Time", html)
        self.assertIn("calculated by CoastalNow", html)
        self.assertIn("not an official NOAA/NWS product", html)
        self.assertIn('href="/methodology/"', html)

    def test_hub_links_to_methodology_and_identifies_score_as_coastalnow_metric(self):
        html = render_fishing_hub({"san-diego": self.location}, {"san-diego": self.result})
        self.assertIn("Data sources & methodology", html)
        self.assertIn("NOAA", html)
        self.assertIn("National Weather Service", html)
        self.assertIn("CoastalNow", html)
        self.assertIn('href="/methodology/"', html)

    def test_methodology_page_is_indexable_and_explains_source_boundaries(self):
        pages = build_directory_pages()
        self.assertIn("methodology/index.html", pages)
        html = pages["methodology/index.html"]
        self.assertIn("Data Sources &amp; Methodology", html)
        self.assertIn("NOAA/NOS/CO-OPS", html)
        self.assertIn("National Weather Service", html)
        self.assertIn("api.tidesandcurrents.noaa.gov", html)
        self.assertIn("weather.gov/documentation/services-web-api", html)
        self.assertIn("Nearby NOAA", html)
        self.assertIn("not an official NOAA or National Weather Service product", html)
        self.assertIn("does not predict whether you will catch fish", html)
        self.assertIn('<meta name="robots" content="index,follow">', html)
        self.assertIn('https://coastalnowtides.com/methodology/', html)


if __name__ == "__main__":
    unittest.main()
