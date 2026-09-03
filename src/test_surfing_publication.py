import json
import tempfile
import unittest
from pathlib import Path

from activities.paths import activity_data_path
from build_site import load_activity_inventory
from locations import LOCATIONS
from seo import build_robots_txt, build_sitemap
from site_generator import _groups, _home


PILOT = {
    "san-diego", "la-jolla", "huntington-beach", "santa-cruz", "malibu",
    "half-moon-bay", "cocoa-beach", "daytona-beach", "wrightsville-beach",
    "nags-head",
}


def usable_result(slug: str) -> dict:
    day = {
        "status": "normal",
        "score": 72.0,
        "rating": "Fair",
        "confidence": "High",
        "best_window": None,
        "ranking_eligible": True,
        "reasons": [],
    }
    return {
        "activity": "surfing",
        "location": slug,
        "today": dict(day),
        "tomorrow": dict(day),
    }


class SurfingPublicationTests(unittest.TestCase):
    def test_homepage_discovers_surfing_from_registry(self):
        html = _home(_groups())
        self.assertIn("Explore surfing", html)
        self.assertIn('href="surfing/index.html"', html)

    def test_inventory_ignores_non_pilot_surfing_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug in ("san-diego", "key-west"):
                location = LOCATIONS[slug]
                path = root / activity_data_path(location, "surfing")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(usable_result(slug)), encoding="utf-8")

            inventory = load_activity_inventory(root, locations=LOCATIONS)
            self.assertIn("san-diego", inventory["surfing"])
            self.assertNotIn("key-west", inventory["surfing"])

    def test_sitemap_defensively_excludes_non_pilot_surfing_result(self):
        results = {slug: usable_result(slug) for slug in PILOT}
        results["key-west"] = usable_result("key-west")
        xml = build_sitemap(LOCATIONS, {"surfing": results})
        surfing_urls = [line for line in xml.splitlines() if "/surfing/" in line]
        self.assertEqual(len(surfing_urls), 11)
        self.assertIn("https://coastalnowtides.com/surfing/", xml)
        self.assertNotIn("https://coastalnowtides.com/tides/florida/key-west/surfing/", xml)

    def test_robots_output_remains_valid(self):
        robots = build_robots_txt()
        self.assertIn("User-agent: *", robots)
        self.assertIn("Sitemap: https://coastalnowtides.com/sitemap.xml", robots)

    def test_no_standalone_surfing_refresh_workflow_exists(self):
        workflows = Path(".github/workflows")
        names = {path.name for path in workflows.glob("*.yml")}
        self.assertNotIn("update-surfing.yml", names)
        self.assertNotIn("surfing-refresh.yml", names)


if __name__ == "__main__":
    unittest.main()
