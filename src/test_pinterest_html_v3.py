"""HTML/CSS Pinterest V3 rollout and Chrome screenshot safety checks."""
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
from pinterest.capture_pin import render_pin_html
from pinterest.render_html import render_html_document
from pinterest.rss import MEDIA_NS, pin_record
from pinterest.schedule import released_creative_v3_pilots, released_locations

CONFIG_PATH = Path(__file__).resolve().parent / "data" / "pinterest.json"
PUBLIC = Path(__file__).resolve().parents[1] / "public"
EXPECTED = {
    ("tides", "huntington-beach"), ("tides", "san-diego"),
    ("fishing", "cape-hatteras"), ("fishing", "miami-beach"),
    ("surfing", "malibu"), ("surfing", "nags-head"),
}


def _config():
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return cfg, build_catalog(LOCATIONS, cfg)


def _mock_image(item, kind, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"mock-pin")
    return path


class HtmlPinterestV3Tests(unittest.TestCase):
    def test_six_v3_pilots_remain_held_until_explicitly_enabled(self):
        config, catalog = _config()
        self.assertEqual(config["creative_v3_start_date"], "2026-11-03")
        self.assertTrue(config["creative_v3_batch_release"])
        self.assertFalse(config["creative_v3_publish_enabled"])
        self.assertFalse(config["html_cutover_enabled"])
        self.assertEqual(config["html_cutover_start_date"], "2026-11-11")
        self.assertEqual(released_creative_v3_pilots(catalog, config, date(2026, 11, 3)), [])
        approved = {**config, "creative_v3_publish_enabled": True}
        self.assertEqual(released_creative_v3_pilots(catalog, approved, date(2026, 11, 2)), [])
        pilots = released_creative_v3_pilots(catalog, approved, date(2026, 11, 3))
        self.assertEqual(len(pilots), 6)
        self.assertEqual({(x["kind"], x["slug"]) for x in pilots}, EXPECTED)
        self.assertTrue(all(x["creative_version"] == "v3" for x in pilots))
        self.assertTrue(all(x["release_date"] == date(2026, 11, 3) for x in pilots))
        self.assertEqual(len(released_locations(catalog, config, date(2026, 11, 3))), 13)

    def test_html_templates_are_self_contained_and_do_not_claim_live_conditions(self):
        with patch("pinterest.render_html._load_photo_background",
                   return_value=Image.new("RGB", (1000, 1500), "#42677b")):
            for kind, name, state in (
                ("tides", "Huntington Beach", "California"),
                ("fishing", "Cape Hatteras", "North Carolina"),
                ("surfing", "Malibu", "California"),
            ):
                with self.subTest(kind=kind):
                    html = render_html_document({"name": name, "state": state}, kind)
                    self.assertIn('width=1000,initial-scale=1', html)
                    self.assertIn(f'class="pin {kind}"', html)
                    self.assertIn(name.upper(), html)
                    self.assertIn(state.upper(), html)
                    self.assertIn("CoastalNow", html)
                    self.assertIn("data:image/jpeg;base64,", html)
                    self.assertNotIn("{{", html)
                    self.assertNotIn("<script", html.lower())
                    self.assertNotIn("http://", html)
                    self.assertNotIn("https://", html)
                    for phrase in ("WAVE HEIGHT: 5", "BEST WINDOW:", "TODAY'S SCORE"):
                        self.assertNotIn(phrase, html)

    def test_dynamic_city_names_are_escaped_for_safe_html(self):
        demo = {"name": "Beach <script>alert(1)</script>", "state": "California & Nevada"}
        with patch("pinterest.render_html._load_photo_background",
                   return_value=Image.new("RGB", (1000, 1500))):
            doc = render_html_document(demo, "tides")
        self.assertNotIn("<script>", doc)
        self.assertIn("&lt;SCRIPT&gt;", doc)
        self.assertIn("CALIFORNIA &amp; NEVADA", doc)

    def test_real_chrome_capture_produces_three_distinct_unclipped_pngs(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "pinterest.render_html._load_photo_background",
            side_effect=lambda kind: Image.new("RGB", (1000, 1500), {
                "tides": "#24778e", "fishing": "#536677", "surfing": "#0c8188",
            }[kind]),
        ):
            output = Path(tmp)
            produced = {}
            for kind in ("tides", "fishing", "surfing"):
                item = {"name": "Huntington Beach", "state": "California",
                        "slug": "huntington-beach"}
                path = output / f"{kind}.png"
                self.assertEqual(render_pin_html(item, kind, path), path)
                self.assertTrue(path.is_file())
                with Image.open(path) as im:
                    self.assertEqual(im.format, "PNG")
                    self.assertEqual(im.size, (1000, 1500))
                    self.assertGreater(im.getpixel((700, 1400))[:3].__len__(), 2)
                produced[kind] = path.read_bytes()
            self.assertEqual(len(set(produced.values())), 3)
            # Never modify a published PNG even if rendering is re-requested.
            sentinel = output / "tides.png"
            sentinel.write_bytes(b"already published")
            render_pin_html(item, "tides", sentinel)
            self.assertEqual(sentinel.read_bytes(), b"already published")

    def test_v3_feed_is_paused_but_can_be_explicitly_approved_without_touching_v1_v2(self):
        cfg, _ = _config()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "generate_pinterest.render_pin_v2", side_effect=_mock_image
        ), patch("generate_pinterest.render_pin_html", side_effect=_mock_image):
            root = Path(tmp)
            prior = root / "pinterest" / "images" / "san-diego-tides.png"
            prior.parent.mkdir(parents=True)
            prior.write_bytes(b"old published image")
            held = generate(date(2026, 11, 3), root, CONFIG_PATH)
            self.assertEqual(held["creative_v3_pilots_released"], [])
            self.assertEqual(len(held["released_slugs"]), 13)
            self.assertEqual(len(held["surfing_released_slugs"]), 10)
            self.assertEqual(prior.read_bytes(), b"old published image")
            for kind, slug in EXPECTED:
                self.assertFalse((root / "pinterest" / "images" / f"{slug}-{kind}-v3.png").exists())
            for kind, expected in (("tides", 15), ("fishing", 15), ("surfing", 12)):
                rss = ET.parse(root / "pinterest" / "rss" / (kind + ".xml"))
                items = rss.findall("./channel/item")
                self.assertEqual(len(items), expected)
                guids = [i.findtext("guid") for i in items]
                self.assertEqual(len(guids), len(set(guids)))
                self.assertEqual(sum(g.endswith(":v3") for g in guids), 0)
                self.assertEqual(sum(g.endswith(":v2") for g in guids), 2)
                self.assertTrue(all(g.endswith(":v2") for g in guids[:2]))

            approved_config = root / "approved.json"
            approved_config.write_text(json.dumps({
                **cfg, "creative_v3_publish_enabled": True,
            }), encoding="utf-8")
            approved = generate(date(2026, 11, 3), root, approved_config)
            self.assertEqual(len(approved["creative_v3_pilots_released"]), 6)
            self.assertEqual(prior.read_bytes(), b"old published image")
            for kind, slug in EXPECTED:
                self.assertTrue((root / "pinterest" / "images" / f"{slug}-{kind}-v3.png").exists())
            for kind, expected in (("tides", 17), ("fishing", 17), ("surfing", 14)):
                rss = ET.parse(root / "pinterest" / "rss" / (kind + ".xml"))
                items = rss.findall("./channel/item")
                self.assertEqual(len(items), expected)
                guids = [i.findtext("guid") for i in items]
                self.assertEqual(len(guids), len(set(guids)))
                self.assertEqual(sum(g.endswith(":v3") for g in guids), 2)
                self.assertEqual(sum(g.endswith(":v2") for g in guids), 2)
                self.assertEqual(sum(g.endswith(":v1") for g in guids),
                                 13 if kind != "surfing" else 10)
                for entry in items[:2]:
                    self.assertTrue(entry.findtext("guid").endswith(":v3"))
                    self.assertEqual(len(entry.findall("{" + MEDIA_NS + "}content")), 1)

    def test_v3_links_and_identity_dont_mutate_prior_published_pins(self):
        cfg, catalog = _config()
        pilot = released_creative_v3_pilots(catalog, {**cfg, "creative_v3_publish_enabled": True}, date(2026, 11, 3))[0]
        v3 = pin_record(pilot, pilot["kind"])
        v2 = pin_record({**pilot, "creative_version": "v2"}, pilot["kind"])
        self.assertEqual(v3["guid"], v2["guid"].replace(":v2", ":v3"))
        self.assertNotEqual(v3["image_url"], v2["image_url"])
        self.assertTrue(v3["image_url"].endswith("-v3.png"))
        self.assertIn("utm_campaign=coastalnow_html_v3", v3["link"])
        self.assertEqual(v3["link"].split("?")[0], v2["link"].split("?")[0])

    def test_future_pin_requires_explicit_html_cutover_approval(self):
        cfg, _ = _config()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "generate_pinterest.render_pin_v2", side_effect=_mock_image
        ) as legacy, patch("generate_pinterest.render_pin_html",
                           side_effect=_mock_image) as html_renderer:
            root = Path(tmp)
            generate(date(2026, 11, 11), root, CONFIG_PATH)
            self.assertFalse(html_renderer.called)
            self.assertTrue(any(call.args[0].get("slug") == "galveston"
                                for call in legacy.call_args_list))
            self.assertTrue(any(call.args[0].get("slug") == "oceanside"
                                and call.args[1] == "surfing"
                                for call in legacy.call_args_list))
            approved_config = root / "approved.json"
            approved_config.write_text(json.dumps({
                **cfg, "html_cutover_enabled": True,
            }), encoding="utf-8")
            with tempfile.TemporaryDirectory() as approved_tmp:
                generate(date(2026, 11, 11), Path(approved_tmp), approved_config)
            self.assertTrue(any(call.args[0].get("slug") == "galveston"
                                for call in html_renderer.call_args_list))
            self.assertTrue(any(call.args[0].get("slug") == "oceanside"
                                and call.args[1] == "surfing"
                                for call in html_renderer.call_args_list))


if __name__ == "__main__":
    unittest.main()
