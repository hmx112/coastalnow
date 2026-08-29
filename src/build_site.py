"""Build directory pages and normalize search indexing metadata."""

from pathlib import Path

from locations import LOCATIONS
from seo import build_robots_txt, build_sitemap, normalize_location_html
from site_generator import build_directory_pages

ROOT = Path(__file__).resolve().parents[1] / "public"


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
        output.write_text(normalized, encoding="utf-8")
        print(f"Normalized SEO {output}")

    sitemap = ROOT / "sitemap.xml"
    sitemap.write_text(build_sitemap(LOCATIONS), encoding="utf-8")
    print(f"Rendered {sitemap}")

    robots = ROOT / "robots.txt"
    robots.write_text(build_robots_txt(), encoding="utf-8")
    print(f"Rendered {robots}")


if __name__ == "__main__":
    main()
