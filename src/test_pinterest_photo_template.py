import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class PinterestPhotoTemplateTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "slug": "san-diego",
            "name": "San Diego",
            "state": "California",
            "state_slug": "california",
            "fishing_enabled": True,
            "surfing_enabled": True,
        }

    def test_category_labels_match_final_large_heading_copy(self):
        from pinterest.render import pin_text

        self.assertEqual(pin_text(self.item, "surfing")["category"], "SURF CONDITIONS")
        self.assertEqual(pin_text(self.item, "fishing")["category"], "FISHING CONDITIONS")
        self.assertEqual(pin_text(self.item, "tides")["category"], "TIDE TIMES")

    def test_final_copy_has_no_best_window_or_information_chip_copy(self):
        from pinterest.render import pin_text

        for kind in ("surfing", "fishing", "tides"):
            payload = pin_text(self.item, kind)
            combined = " ".join(str(value) for value in payload.values()).upper()
            self.assertNotIn("BEST WINDOW", combined)
            self.assertNotIn("7-DAY VIEW", combined)
            self.assertNotIn("FISHING SCORE", combined)
            self.assertNotIn("WAVE + SWELL", combined)

    def test_renderer_uses_photographic_backgrounds_and_no_vector_people(self):
        import pinterest.render as render

        source = inspect.getsource(render)
        self.assertIn("PHOTO_BACKGROUNDS", source)
        self.assertIn("images.unsplash.com", source)
        self.assertIn("ImageOps.fit", source)
        self.assertNotIn("_draw_surfing_scene", source)
        self.assertNotIn("_draw_fishing_scene", source)
        self.assertNotIn("_draw_tide_scene", source)
        self.assertNotIn("chip_width", source)

    def test_pinterest_brand_matches_site_header_logo_spec(self):
        import pinterest.render as render

        self.assertEqual(render.WEBSITE_LOGO_GRADIENT_HEX, ("#0b8190", "#65c4c6"))
        self.assertEqual(
            render.WEBSITE_LOGO_WAVE_PATH,
            "M3 8c3.5-4 6.5 4 10 0s6.5 4 8 0M3 13c3.5-4 6.5 4 10 0s6.5 4 8 0M3 18c3.5-4 6.5 4 10 0s6.5 4 8 0",
        )
        helper = inspect.getsource(render._draw_coastalnow_brand)
        self.assertIn("_draw_website_logo_mark", helper)
        self.assertIn("BOLD_FONT", helper)
        self.assertNotIn("SERIF_FONT", helper)


if __name__ == "__main__":
    unittest.main()
