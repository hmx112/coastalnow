import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_site import inject_activity_links
from locations import LOCATIONS


def fishing_result():
    return {
        "activity": "fishing",
        "location": "san-diego",
        "today": {
            "confidence": "High",
            "status": "normal",
            "score": 88,
            "rating": "Good",
        },
    }


class TideMobileActivityNavTests(unittest.TestCase):
    def test_legacy_generated_tide_css_keeps_injected_activity_link_visible_on_mobile(self):
        html = '''<html><head><style>@media(max-width:800px){.nav>a{display:none}}</style></head><body>
<header><nav class="nav"><a href="#forecast">7-Day forecast</a><span class="search-pill">Search</span></nav></header>
<main>Content</main></body></html>'''
        updated = inject_activity_links(
            html,
            LOCATIONS["san-diego"],
            {"fishing": fishing_result()},
        )
        self.assertIn('.nav>a:not(.activity-nav-link){display:none}', updated)
        self.assertNotIn('.nav>a{display:none}', updated)
        self.assertIn(
            '<a class="activity-nav-link" href="/tides/california/san-diego/fishing/">Fishing</a>',
            updated,
        )


if __name__ == "__main__":
    unittest.main()
