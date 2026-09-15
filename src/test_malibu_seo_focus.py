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
