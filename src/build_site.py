"""Build the home and state directory pages from locations.py."""

from pathlib import Path

from site_generator import build_directory_pages

ROOT = Path(__file__).resolve().parents[1] / "public"


def main():
    for relative_path, html in build_directory_pages().items():
        output = ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Rendered {output}")


if __name__ == "__main__":
    main()
