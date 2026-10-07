import json
import re
import unittest
from datetime import datetime
from pathlib import Path

from locations import LOCATIONS
from state_landing import state_landing_config

ROOT = Path(__file__).resolve().parents[1] / "public"
MALIBU = LOCATIONS["malibu"]


def _fmt_time(raw: str) -> str:
    value = datetime.strptime(raw, "%Y-%m-%d %H:%M").strftime("%I:%M %p")
    return value[1:] if value.startswith("0") else value


def _fmt_height(value) -> str:
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


class MalibuSeoFocusTests(unittest.TestCase):
    def test_malibu_has_search_focused_editorial_config(self):
        context = MALIBU.get("search_context")
        self.assertIsInstance(context, dict)
        self.assertTrue(context.get("today_summary"))
        self.assertIn("Malibu", context.get("title", ""))
        body = " ".join(context.get("paragraphs") or [])
        self.assertIn("Santa Monica", body)
        self.assertIn("10 miles", body)
        self.assertEqual(
            context.get("related_links"),
            [
                {"label": "Santa Monica tides", "href": "/tides/california/santa-monica/"},
                {"label": "Los Angeles tides", "href": "/tides/california/los-angeles/"},
            ],
        )
        self.assertTrue(MALIBU["meta_description"].startswith("Check Malibu tides today"))

    def test_malibu_is_featured_on_california_landing(self):
        featured = state_landing_config("california")["featured"]
        self.assertIn("malibu", featured[:4])

    def test_c2_design_is_applied_to_every_tide_location_and_preserves_seo(self):
        region_by_slug = {
            "sanibel-island": "florida-gulf",
            "tampa-bay": "florida-gulf",
            "key-west": "florida-keys",
            "clearwater-beach": "florida-gulf",
            "st-pete-beach": "florida-gulf",
            "naples": "florida-gulf",
            "miami-beach": "florida-atlantic",
            "fort-lauderdale": "florida-atlantic",
            "daytona-beach": "florida-atlantic",
            "cocoa-beach": "florida-atlantic",
            "destin": "florida-gulf",
            "panama-city-beach": "florida-gulf",
            "key-biscayne": "florida-atlantic",
            "west-palm-beach": "florida-atlantic",
            "fort-myers-beach": "florida-gulf",
            "pompano-beach": "florida-atlantic",
            "marco-island": "florida-gulf",
            "sarasota": "florida-gulf",
            "nags-head": "outer-banks",
            "kitty-hawk": "outer-banks",
            "kill-devil-hills": "outer-banks",
            "cape-hatteras": "outer-banks",
            "ocracoke": "outer-banks",
            "corolla": "outer-banks",
        }
        for slug, location in LOCATIONS.items():
            if location["state_slug"] == "california":
                region = "california"
            elif location["state_slug"] == "florida":
                region = region_by_slug[slug]
            elif location["state_slug"] == "north-carolina":
                region = region_by_slug.get(slug, "carolinas")
            elif location["state_slug"] == "south-carolina":
                region = "carolinas"
            elif location["state_slug"] == "oregon":
                region = "oregon"
            else:
                region = "northeast"

            html = (ROOT / location["page_path"]).read_text(encoding="utf-8")
            self.assertIn(
                f'class="c2-tide c2-region-{region} c2-{slug}"',
                html,
                slug,
            )
            self.assertEqual(html.count('data-coastalnow-design="tide-c2"'), 1, slug)
            self.assertIn('href="/assets/malibu-c2.css?v=20261008-rollout-2"', html, slug)
            self.assertIn('class="c2-section-tabs"', html, slug)
            self.assertIn('id="overview"', html, slug)
            self.assertIn('id="tide-chart"', html, slug)
            self.assertIn(
                f'<link rel="canonical" href="https://coastalnowtides.com/tides/{location["state_slug"]}/{slug}/">',
                html,
                slug,
            )
            self.assertIn('<meta name="robots" content="index,follow">', html, slug)

        css = ROOT / "assets" / "malibu-c2.css"
        self.assertTrue(css.exists())
        regional_fallbacks = {
            "california": "hero-los-angeles.avif",
            "florida-atlantic": "hero-miami-beach.avif",
            "florida-gulf": "hero-miami-beach.avif",
            "florida-keys": "hero-miami-beach.avif",
            "outer-banks": "hero-oceanside.avif",
            "carolinas": "hero-oceanside.avif",
            "oregon": "hero-malibu.avif",
            "northeast": "hero-malibu.avif",
        }
        specific_assets = {
            "malibu": "hero-malibu.avif",
            "los-angeles": "hero-los-angeles.avif",
            "oceanside": "hero-oceanside.avif",
            "miami-beach": "hero-miami-beach.avif",
        }
        for filename in specific_assets.values():
            asset = ROOT / "assets" / filename
            self.assertTrue(asset.exists(), filename)
            self.assertGreater(asset.stat().st_size, 3000, filename)
            self.assertEqual(asset.read_bytes()[4:12], b"ftypavif", filename)

        css_text = css.read_text(encoding="utf-8")
        self.assertIn(".c2-tide #overview", css_text)
        self.assertNotIn("hero-regions-sprite.avif", css_text)
        for region, filename in regional_fallbacks.items():
            self.assertIn(
                f'.c2-region-{region}{{--c2-hero-image:url(\"/assets/{filename}?v=20261008-rollout-2\");--c2-hero-position:center 48%;--c2-hero-size:cover}}',
                css_text,
            )
        for slug, filename in specific_assets.items():
            self.assertIn(
                f'.c2-{slug}{{--c2-hero-image:url(\"/assets/{filename}?v=20261008-rollout-2\");--c2-hero-position:center 48%;--c2-hero-size:cover}}',
                css_text,
            )
        self.assertIn("overflow-x:visible;", css_text)
        self.assertIn("flex:1 1 20%;", css_text)
        self.assertIn("padding-inline:5px;", css_text)
        self.assertIn(".c2-tide .chart .point-label{font-size:22px;", css_text)
        self.assertIn(".c2-tide .chart .axis-label{font-size:18px;", css_text)

    def test_malibu_local_context_renders_dynamic_today_summary_and_links(self):
        html = (ROOT / MALIBU["page_path"]).read_text(encoding="utf-8")
        match = re.search(
            r"<!-- SEARCH_CONTEXT_START -->(.*?)<!-- SEARCH_CONTEXT_END -->",
            html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        block = match.group(1)

        data = json.loads((ROOT / MALIBU["data_path"]).read_text(encoding="utf-8"))
        local_day = data["generated_at_local"][:10]
        events = [item for item in data["hilo"] if item["t"].startswith(local_day)]
        highs = [item for item in events if item["type"] == "H"]
        lows = [item for item in events if item["type"] == "L"]
        self.assertTrue(highs)
        self.assertTrue(lows)
        high = max(highs, key=lambda item: float(item["v"]))
        low = min(lows, key=lambda item: float(item["v"]))
        expected = (
            f"Malibu tides today reach a predicted high of {_fmt_height(high['v'])} ft at {_fmt_time(high['t'])} "
            f"and a predicted low of {_fmt_height(low['v'])} ft at {_fmt_time(low['t'])}, Pacific time."
        )
        self.assertIn(expected, block)
        self.assertIn('href="/tides/california/santa-monica/"', block)
        self.assertIn('href="/tides/california/los-angeles/"', block)
        self.assertIn("7-day Malibu tide schedule", block)


if __name__ == "__main__":
    unittest.main()
