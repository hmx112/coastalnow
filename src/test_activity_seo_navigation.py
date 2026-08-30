import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.links import activity_location_url
from build_site import inject_activity_links, load_activity_inventory, render_activity_outputs
from locations import LOCATIONS
from seo import (
    activity_breadcrumbs,
    activity_robots_directive,
    activity_seo_tags,
    build_sitemap,
    canonical_url,
)
from site_generator import build_directory_pages

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "src" / "fixtures" / "tide-page-paths-v1.json"


def result(confidence="High", status="normal", score=88, eligible=True):
    return {
        "activity": "fishing",
        "location": "san-diego",
        "today": {
            "confidence": confidence,
            "status": status,
            "score": score,
            "rating": "Good" if score is not None else None,
            "ranking_eligible": eligible,
            "best_window": None,
            "reasons": [],
        },
        "tomorrow": {
            "confidence": confidence,
            "status": status,
            "score": score,
            "rating": "Good" if score is not None else None,
            "ranking_eligible": eligible,
            "best_window": None,
            "reasons": [],
        },
        "hourly": {"today": [], "tomorrow": []},
        "safety_disclaimer": "Fishing Score is a planning metric, not a safety guarantee.",
    }


class ActivitySeoNavigationTests(unittest.TestCase):
    def test_existing_tide_url_set_is_frozen(self):
        expected = set(json.loads(BASELINE.read_text(encoding="utf-8")))
        actual = {location["page_path"] for location in LOCATIONS.values()}
        self.assertEqual(len(expected), 51)
        self.assertEqual(actual, expected)

    def test_homepage_has_registry_driven_explore_by_activity_link(self):
        home = build_directory_pages()["index.html"]
        self.assertIn("Explore by activity", home)
        self.assertIn("Fishing", home)
        self.assertIn('href="fishing/index.html"', home)

    def test_activity_indexability_depends_on_real_data_confidence(self):
        self.assertEqual(activity_robots_directive(result("High")), "index,follow")
        self.assertEqual(activity_robots_directive(result("Medium")), "index,follow")
        self.assertEqual(activity_robots_directive(result("Limited", "Limited", None, False)), "noindex,follow")
        self.assertEqual(activity_robots_directive(result("Unavailable", "Unavailable", None, False)), "noindex,follow")
        # A high-confidence hard stop is useful real data and remains indexable, while still not rankable.
        self.assertEqual(activity_robots_directive(result("High", "NOT RECOMMENDED", None, False)), "index,follow")

    def test_activity_page_gets_self_canonical_and_four_level_breadcrumb(self):
        location = LOCATIONS["san-diego"]
        tags = activity_seo_tags(location, "fishing", result("High"))
        expected = "https://coastalnowtides.com/tides/california/san-diego/fishing/"
        self.assertIn(f'<link rel="canonical" href="{expected}">', tags)
        self.assertIn('<meta name="robots" content="index,follow">', tags)
        crumbs = activity_breadcrumbs(location, "fishing", "Fishing")
        self.assertEqual(len(crumbs), 4)
        self.assertEqual(crumbs[-1][1], "tides/california/san-diego/fishing/index.html")
        self.assertIn("BreadcrumbList", tags)

    def test_sitemap_keeps_existing_urls_and_adds_hub_and_only_indexable_activity_pages(self):
        high = result("High")
        limited = result("Limited", "Limited", None, False)
        high["location"] = "san-diego"
        limited["location"] = "monterey"
        inventory = {"fishing": {"san-diego": high, "monterey": limited}}
        xml = build_sitemap(LOCATIONS, inventory)
        for location in LOCATIONS.values():
            self.assertIn(f'<loc>{canonical_url(location["page_path"])}</loc>', xml)
        self.assertIn("<loc>https://coastalnowtides.com/fishing/</loc>", xml)
        self.assertIn("<loc>https://coastalnowtides.com/tides/california/san-diego/fishing/</loc>", xml)
        self.assertNotIn("<loc>https://coastalnowtides.com/tides/california/monterey/fishing/</loc>", xml)

    def test_parent_tide_page_gets_fishing_link_without_changing_parent_url(self):
        location = LOCATIONS["san-diego"]
        html = '<html><body><main><h1>San Diego Tide</h1></main><footer>Footer</footer></body></html>'
        updated = inject_activity_links(html, location, {"fishing": result("High")})
        self.assertIn("Plan coastal activities", updated)
        self.assertIn(activity_location_url(location, "fishing"), updated)
        self.assertIn("88", updated)
        self.assertIn("Good", updated)
        # Idempotent rebuilds must replace the same block rather than duplicate it.
        twice = inject_activity_links(updated, location, {"fishing": result("High")})
        self.assertEqual(twice.count("ACTIVITY_LINKS_START"), 1)

    def test_build_renders_fishing_hub_and_location_pages_from_existing_json(self):
        location = {**LOCATIONS["san-diego"]}
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            (public / "data/activities/fishing").mkdir(parents=True)
            (public / "data/conditions").mkdir(parents=True)
            (public / "data/activities/fishing/san-diego.json").write_text(json.dumps(result("High")), encoding="utf-8")
            snapshot = {
                "hourly": [],
                "alerts": {"status": "ok", "items": []},
                "tide": {"hilo": []},
            }
            (public / "data/conditions/san-diego.json").write_text(json.dumps(snapshot), encoding="utf-8")
            inventory = load_activity_inventory(public, locations={"san-diego": location})
            rendered = render_activity_outputs(public, {"san-diego": location}, inventory)
            self.assertIn("fishing/index.html", rendered)
            self.assertIn("tides/california/san-diego/fishing/index.html", rendered)
            child = (public / "tides/california/san-diego/fishing/index.html").read_text(encoding="utf-8")
            self.assertIn("https://coastalnowtides.com/tides/california/san-diego/fishing/", child)
            self.assertIn('<meta name="robots" content="index,follow">', child)
            hub = (public / "fishing/index.html").read_text(encoding="utf-8")
            self.assertIn("https://coastalnowtides.com/fishing/", hub)
            self.assertIn('<meta name="robots" content="index,follow">', hub)


if __name__ == "__main__":
    unittest.main()
