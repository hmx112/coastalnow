import struct
import unittest
from pathlib import Path

from site_generator import build_directory_pages

ROOT = Path(__file__).resolve().parents[1]


class FaviconTests(unittest.TestCase):
    def test_homepage_declares_search_favicon(self):
        html = build_directory_pages()["index.html"]
        self.assertIn('<link rel="icon" type="image/png" sizes="192x192" href="/favicon.png">', html)
        self.assertIn('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">', html)

    def test_favicon_png_is_192_square(self):
        path = ROOT / "public" / "favicon.png"
        data = path.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (192, 192))


if __name__ == "__main__":
    unittest.main()
