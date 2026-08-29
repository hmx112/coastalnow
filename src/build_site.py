"""Build directory pages and normalize search indexing metadata."""

import re
from pathlib import Path

from locations import LOCATIONS
from seo import build_robots_txt, build_sitemap, normalize_location_html
from site_generator import LOGO, build_directory_pages

ROOT = Path(__file__).resolve().parents[1] / "public"
LOGO_PATTERN = re.compile(
    r'<span class="logo-mark">\s*<svg viewBox="0 0 24 24" aria-hidden="true">.*?</svg>\s*</span>',
    re.DOTALL,
)


def normalize_brand_logo(html: str) -> str:
    normalized, count = LOGO_PATTERN.subn(LOGO, html, count=1)
    if count != 1:
        raise ValueError("Location page logo markup was not found exactly once")
    return normalized


def main():
    for relative_path, html in build_directory_pages().items():
        output = ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Rendered {output}")

    for location in LOCATIONS.values():
        output = ROOT / location["page_path"]
        if not output.exists():
            raise FileNotFoundError(f"Missing location page: {output}")
        html = output.read_text(encoding="utf-8")
        normalized = normalize_location_html(html, location)
        normalized = normalize_brand_logo(normalized)
        output.write_text(normalized, encoding="utf-8")
        print(f"Normalized SEO and branding {output}")

    sitemap = ROOT / "sitemap.xml"
    sitemap.write_text(build_sitemap(LOCATIONS), encoding="utf-8")
    print(f"Rendered {sitemap}")

    robots = ROOT / "robots.txt"
    robots.write_text(build_robots_txt(), encoding="utf-8")
    print(f"Rendered {robots}")


if __name__ == "__main__":
    main()
