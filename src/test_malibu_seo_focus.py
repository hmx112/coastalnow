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

    def test_malibu_c2_design_pilot_is_scoped_and_preserves_seo(self):
        html = (ROOT / MALIBU["page_path"]).read_text(encoding="utf-8")
        self.assertIn('class="c2-malibu"', html)
        self.assertEqual(html.count('data-coastalnow-design="malibu-c2"'), 1)
        self.assertIn('href="/assets/malibu-c2.css?v=20260923-mobile-1"', html)
        self.assertIn('class="c2-section-tabs"', html)
        self.assertIn('id="overview"', html)
        self.assertIn('id="tide-chart"', html)
        self.assertIn(
            '<link rel="canonical" href="https://coastalnowtides.com/tides/california/malibu/">',
            html,
        )
        self.assertIn('<meta name="robots" content="index,follow">', html)
        self.assertIn("<title>Malibu Tide Times, High &amp; Low Tides Today | CoastalNow</title>", html)

        css = ROOT / "assets" / "malibu-c2.css"
        hero = ROOT / "assets" / "malibu-c2-hero.svg"
        self.assertTrue(css.exists())
        self.assertTrue(hero.exists())
        css_text = css.read_text(encoding="utf-8")
        self.assertIn(".c2-malibu #overview", css_text)
        self.assertIn("/assets/malibu-c2-hero.svg", css_text)
        self.assertIn("overflow-x:visible;", css_text)
        self.assertIn("flex:1 1 20%;", css_text)
        self.assertIn("padding-inline:5px;", css_text)
        self.assertIn(".c2-malibu .chart .point-label{font-size:22px;", css_text)
        self.assertIn(".c2-malibu .chart .axis-label{font-size:18px;", css_text)

        santa_monica = (ROOT / LOCATIONS["santa-monica"]["page_path"]).read_text(encoding="utf-8")
        self.assertNotIn("c2-malibu", santa_monica)
        self.assertNotIn("malibu-c2.css", santa_monica)

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
