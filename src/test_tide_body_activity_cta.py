import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.paths import activity_location_url
from build_site import inject_activity_links
from locations import LOCATIONS

ROOT = Path(__file__).resolve().parents[1] / "public"


def fishing_result(location_slug: str):
    return {
        "activity": "fishing",
        "location": location_slug,
        "today": {
            "confidence": "High",
            "status": "normal",
            "score": 82,
            "rating": "Good",
        },
    }


class TideBodyActivityCtaTests(unittest.TestCase):
    def test_injection_places_fishing_cta_after_hero_before_tide_summary(self):
        location = LOCATIONS["san-diego"]
        html = '''<html><body><main>
<section class="hero"><div>Hero</div></section>
<section class="section" id="tide-summary"><h2>Your next tides</h2></section>
</main></body></html>'''
        updated = inject_activity_links(html, location, {"fishing": fishing_result("san-diego")})
        href = activity_location_url(location, "fishing")
        cta = f'href="{href}"'
        self.assertEqual(updated.count("ACTIVITY_PRIMARY_START"), 1)
        self.assertEqual(updated.count(cta), 2)  # primary CTA + existing lower Activity card
        self.assertIn("Fishing conditions for San Diego", updated)
        self.assertLess(updated.index("ACTIVITY_PRIMARY_START"), updated.index("Your next tides"))
        self.assertGreater(updated.index("ACTIVITY_PRIMARY_START"), updated.index('</section>'))

    def test_all_generated_tide_pages_have_exactly_one_primary_fishing_cta(self):
        for slug, location in LOCATIONS.items():
            with self.subTest(location=slug):
                html = (ROOT / location["page_path"]).read_text(encoding="utf-8")
                href = activity_location_url(location, "fishing")
                self.assertEqual(html.count("ACTIVITY_PRIMARY_START"), 1)
                primary = html.split("<!-- ACTIVITY_PRIMARY_START -->", 1)[1].split("<!-- ACTIVITY_PRIMARY_END -->", 1)[0]
                self.assertIn(f'href="{href}"', primary)
                self.assertIn(f"Fishing conditions for {location['city']}", primary)


if __name__ == "__main__":
    unittest.main()
