"""Pinterest V4 information-first pin renderer, identity, and RSS safety tests."""
from __future__ import annotations

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from generate_pinterest import generate
from locations import LOCATIONS
from pinterest.catalog import build_catalog
from pinterest.capture_pin import _launch_chromium, render_pin_html
from pinterest.render_html import render_html_document
from pinterest.rss import MEDIA_NS, pin_record
from pinterest.schedule import released_creative_v4_pilots

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "data" / "pinterest.json"
PILOTS = {
    ("tides", "huntington-beach"), ("tides", "san-diego"),
    ("fishing", "cape-hatteras"), ("fishing", "miami-beach"),
    ("surfing", "malibu"), ("surfing", "nags-head"),
}
TITLE_AND_PANEL = {
    "tides": ("TIDE TIMES", "CHART", "HIGH TIDE", "LOW TIDE", "VIEW LOCAL TIDE CHART"),
    "fishing": ("SHORE FISHING", "CONDITIONS", "TIDES", "MARINE ALERTS", "CHECK LOCAL CONDITIONS"),
    "surfing": ("SURF", "FORECAST", "WAVE", "SWELL", "EXPLORE THE SURF OUTLOOK"),
}


def fake_render(item, kind, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"mock-png")
    return path


class PinterestInformationV4Tests(unittest.TestCase):
    def test_v4_releases_exactly_six_and_leaves_v3_and_bulk_cutover_held(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        catalog = build_catalog(LOCATIONS, cfg)
        self.assertTrue(cfg["creative_v4_publish_enabled"])
        self.assertFalse(cfg["creative_v3_publish_enabled"])
        self.assertFalse(cfg["html_cutover_enabled"])
        self.assertEqual(cfg["creative_v4_start_date"], "2026-11-03")
        self.assertEqual(released_creative_v4_pilots(catalog, cfg, date(2026, 11, 2)), [])
        due = released_creative_v4_pilots(catalog, cfg, date(2026, 11, 3))
        self.assertEqual(len(due), 6)
        self.assertEqual({(i["kind"], i["slug"]) for i in due}, PILOTS)
        self.assertTrue(all(i["creative_version"] == "v4" for i in due))
        off = {**cfg, "creative_v4_publish_enabled": False}
        self.assertEqual(released_creative_v4_pilots(catalog, off, date(2026, 11, 3)), [])

    def test_every_information_template_has_clear_topic_and_evergreen_explanatory_graphics(self):
        for kind, city, state, state_code in (
            ("tides", "San Diego", "California", "CA"),
            ("fishing", "Cape Hatteras", "North Carolina", "NC"),
            ("surfing", "Malibu", "California", "CA"),
        ):
            with self.subTest(kind=kind):
                doc = render_html_document({"name": city, "state": state}, kind,
                                           background=Image.new("RGB", (1000, 1500), "#42818f"))
                self.assertIn(city.upper(), doc)
                self.assertIn(state.upper(), doc)  # Full name remains in accessibility label.
                self.assertIn(f', {state_code}</span>', doc)
                self.assertIn("CoastalNow", doc)
                self.assertIn("data:image/jpeg;base64,", doc)
                self.assertNotIn("{{", doc)
                self.assertNotIn("<script", doc.lower())
                self.assertNotIn("https://", doc)
                for term in TITLE_AND_PANEL[kind]:
                    self.assertIn(term, doc)
                for unsafe in ("BEST WINDOW:", "TODAY'S SCORE", "5 FT", "100% SAFE"):
                    self.assertNotIn(unsafe, doc)
        malicious = render_html_document({
            "name": "Beach <script>alert(1)</script>",
            "state": "California & Nevada",
        }, "tides", background=Image.new("RGB", (1000, 1500)))
        self.assertNotIn("<script>", malicious)
        self.assertIn("&lt;SCRIPT&gt;", malicious)
        self.assertIn("CALIFORNIA &amp; NEVADA", malicious)

    def test_html_screenshot_shows_content_in_nonoverlapping_bounds(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as driver:
            browser = _launch_chromium(driver)
            try:
                for kind in TITLE_AND_PANEL:
                    with self.subTest(kind=kind):
                        html = render_html_document({
                            "name": "North Myrtle Beach", "state": "South Carolina",
                        }, kind, background=Image.new("RGB", (1000, 1500), "#327e8d"))
                        page = browser.new_page(viewport={"width": 1000, "height": 1500},
                                                device_scale_factor=1)
                        page.set_content(html, wait_until="load")
                        headline = page.locator(".headline").bounding_box()
                        location = page.locator(".location").bounding_box()
                        info = page.locator(
                            {"tides": ".chart-panel", "fishing": ".check-panel",
                             "surfing": ".metric-panel"}[kind]).bounding_box()
                        cta = page.locator(".cta").bounding_box()
                        self.assertGreater(location["y"], headline["y"] + headline["height"] - 5)
                        self.assertGreater(info["y"], location["y"] + location["height"] + 50)
                        self.assertGreater(cta["y"], info["y"] + info["height"])
                        self.assertLessEqual(cta["y"] + cta["height"], 1500)
                        self.assertLessEqual(location["x"] + location["width"], 999)
                        self.assertGreaterEqual(location["x"], 0)
                        if kind != "tides":
                            logo = page.locator(".brand.bottom").bounding_box()
                            note = page.locator(".source-note").bounding_box()
                            self.assertGreaterEqual(logo["y"], cta["y"] + cta["height"] - 1)
                            self.assertGreater(note["y"], logo["y"] + logo["height"])
                        page.close()
            finally:
                browser.close()

    def test_actual_1000_by_1500_render_and_immutable_output(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "pinterest.render_html._load_photo_background",
            return_value=Image.new("RGB", (1000, 1500), "#276f80"),
        ):
            file_path = Path(tmp) / "trial-v4.png"
            item = {"name": "San Diego", "state": "California", "slug": "san-diego"}
            render_pin_html(item, "tides", file_path)
            with Image.open(file_path) as im:
                self.assertEqual(im.size, (1000, 1500))
                self.assertEqual(im.format, "PNG")
            before = file_path.read_bytes()
            render_pin_html(item, "tides", file_path)
            self.assertEqual(before, file_path.read_bytes())

    def test_v4_rss_six_new_images_does_not_republish_old_v3_or_edit_v1_v2(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "generate_pinterest.render_pin_v2", side_effect=fake_render
        ), patch("generate_pinterest.render_pin_html", side_effect=fake_render):
            root = Path(tmp)
            saved = root / "pinterest" / "images" / "san-diego-tides-v3.png"
            saved.parent.mkdir(parents=True)
            saved.write_bytes(b"keep-old-v3-image")
            legacy = root / "pinterest" / "images" / "san-diego-tides.png"
            legacy.write_bytes(b"keep-old-v1-image")
            result = generate(date(2026, 11, 3), root, CONFIG)
            self.assertEqual(result["creative_v3_pilots_released"], [])
            self.assertEqual(len(result["creative_v4_pilots_released"]), 6)
            self.assertEqual(saved.read_bytes(), b"keep-old-v3-image")
            self.assertEqual(legacy.read_bytes(), b"keep-old-v1-image")
            for kind, slug in PILOTS:
                self.assertTrue((root / "pinterest" / "images"
                                 / f"{slug}-{kind}-v4.png").exists())
            for kind, count in (("tides", 17), ("fishing", 17), ("surfing", 14)):
                entries = ET.parse(root / "pinterest" / "rss" / f"{kind}.xml")
                items = entries.findall("./channel/item")
                self.assertEqual(len(items), count)
                guids = [item.findtext("guid") for item in items]
                self.assertEqual(len(set(guids)), count)
                self.assertEqual(sum(g.endswith(":v1") for g in guids),
                                 13 if kind != "surfing" else 10)
                self.assertEqual(sum(g.endswith(":v2") for g in guids), 2)
                self.assertEqual(sum(g.endswith(":v3") for g in guids), 0)
                self.assertEqual(sum(g.endswith(":v4") for g in guids), 2)
                for entry in [i for i in items if i.findtext("guid").endswith(":v4")]:
                    media = entry.findall("{" + MEDIA_NS + "}content")
                    self.assertEqual(len(media), 1)
                    self.assertTrue(media[0].attrib["url"].endswith("-v4.png"))
                    self.assertIn("coastalnow_info_v4", entry.findtext("link"))
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
            cfg["creative_v4_publish_enabled"] = False
            disabled = root / "paused.json"
            disabled.write_text(json.dumps(cfg), encoding="utf-8")
            held = generate(date(2026, 11, 3), root, disabled)
            self.assertEqual(held["creative_v4_pilots_released"], [])
            self.assertEqual(legacy.read_bytes(), b"keep-old-v1-image")

    def test_v4_uses_new_rss_id_and_campaign(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        catalog = build_catalog(LOCATIONS, cfg)
        pilot = released_creative_v4_pilots(catalog, cfg, date(2026, 11, 3))[0]
        v4 = pin_record(pilot, pilot["kind"])
        v3 = pin_record({**pilot, "creative_version": "v3"}, pilot["kind"])
        self.assertTrue(v4["guid"].endswith(":v4"))
        self.assertTrue(v4["image_url"].endswith("-v4.png"))
        self.assertIn("utm_campaign=coastalnow_info_v4", v4["link"])
        self.assertNotEqual(v4["guid"], v3["guid"])
        self.assertNotEqual(v4["image_url"], v3["image_url"])
        self.assertEqual(v4["link"].split("?")[0], v3["link"].split("?")[0])


if __name__ == "__main__":
    unittest.main()
