"""Generate due CoastalNow Pinterest pin images and RSS feeds."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

from locations import LOCATIONS
from pinterest.catalog import build_catalog, load_pinterest_config
from pinterest.creative_v2 import render_pin_v2
from pinterest.capture_pin import render_pin_html
from pinterest.rss import BASE_URL, build_rss
from pinterest.schedule import released_locations, released_surfing_locations, released_creative_v2_pilots, released_creative_v3_pilots, released_creative_v4_pilots

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_ROOT = REPO_ROOT / "public"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "data" / "pinterest.json"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.fromstring(text)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _validate_feed_images(feed_path: Path, public_root: Path) -> None:
    root = ET.fromstring(feed_path.read_text(encoding="utf-8"))
    base_prefix = BASE_URL + "/"
    seen_guids: set[str] = set()
    seen_links: set[str] = set()
    seen_images: set[str] = set()
    for item in root.findall("./channel/item"):
        guid = item.findtext("guid") or ""
        link = item.findtext("link") or ""
        media = [child for child in item if child.tag.endswith("content")]
        if len(media) != 1:
            raise ValueError(f"{feed_path}: each RSS item must contain exactly one media:content image")
        image_url = media[0].attrib.get("url", "")
        for label, value, seen in (
            ("GUID", guid, seen_guids),
            ("link", link, seen_links),
            ("image URL", image_url, seen_images),
        ):
            if not value:
                raise ValueError(f"{feed_path}: RSS item has empty {label}")
            if value in seen:
                raise ValueError(f"{feed_path}: duplicate RSS item {label}: {value}")
            seen.add(value)
        if not image_url.startswith(base_prefix):
            raise ValueError(f"{feed_path}: image URL must use claimed CoastalNow domain: {image_url}")
        relative = image_url[len(base_prefix):]
        if not relative.startswith("pinterest/images/"):
            raise ValueError(f"{feed_path}: image URL is outside Pinterest image output: {image_url}")
        local_path = public_root / relative
        if not local_path.exists():
            raise FileNotFoundError(f"{feed_path}: referenced Pinterest image does not exist: {local_path}")


def _render_once(item: dict, kind: str, path: Path, *, html_cutover_enabled: bool = True, html_cutover_date: date = date(2026, 11, 11)) -> bool:
    if path.exists():
        return False
    version = item.get("creative_version", "v1")
    release_date = item.get("release_date")
    # Retain all already published PNG assets (early-return above).
    # Use the new HTML renderer for v3, then for all *new* backfill pins.
    if version in {"v3", "v4"} or (html_cutover_enabled and version == "v1" and release_date is not None and release_date >= html_cutover_date):
        render_pin_html(item, kind, path)
    else:
        render_pin_v2(item, kind, path)
    return True


def generate(as_of: date, public_root: Path = DEFAULT_PUBLIC_ROOT, config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    public_root = Path(public_root)
    config_path = Path(config_path)
    config = load_pinterest_config(config_path)
    catalog = build_catalog(LOCATIONS, config)
    released = released_locations(catalog, config, as_of)
    surfing_released = released_surfing_locations(catalog, config, as_of)
    v2_pilots = released_creative_v2_pilots(catalog, config, as_of)
    v3_pilots = released_creative_v3_pilots(catalog, config, as_of)
    v4_pilots = released_creative_v4_pilots(catalog, config, as_of)
    html_renderer_options = {
        "html_cutover_enabled": config.get("html_cutover_enabled", True),
        "html_cutover_date": date.fromisoformat(config.get("html_cutover_start_date", "2026-11-11")),
    }

    image_root = public_root / "pinterest" / "images"
    rss_root = public_root / "pinterest" / "rss"
    image_root.mkdir(parents=True, exist_ok=True)
    rss_root.mkdir(parents=True, exist_ok=True)

    images: list[Path] = []
    new_images: list[Path] = []
    for item in released:
        tide_path = image_root / f'{item["slug"]}-tides.png'
        if _render_once(item, "tides", tide_path, **html_renderer_options):
            new_images.append(tide_path)
        images.append(tide_path)
        if item.get("fishing_enabled"):
            fishing_path = image_root / f'{item["slug"]}-fishing.png'
            if _render_once(item, "fishing", fishing_path, **html_renderer_options):
                new_images.append(fishing_path)
            images.append(fishing_path)

    for item in surfing_released:
        surfing_path = image_root / f'{item["slug"]}-surfing.png'
        if _render_once(item, "surfing", surfing_path, **html_renderer_options):
            new_images.append(surfing_path)
        images.append(surfing_path)

    for pilot in v2_pilots + v3_pilots + v4_pilots:
        version = pilot["creative_version"]
        image = image_root / f'{pilot["slug"]}-{pilot["kind"]}-{version}.png'
        if _render_once(pilot, pilot["kind"], image, **html_renderer_options):
            new_images.append(image)
        images.append(image)

    feeds = [
        rss_root / "tides.xml",
        rss_root / "fishing.xml",
        rss_root / "surfing.xml",
    ]
    # Existing RSS feed paths/GUIDs stay unchanged. A new pin version has
    # its own image, GUID, release date and analytics-attributed destination.
    creative_pilots = v2_pilots + v3_pilots + v4_pilots
    _atomic_write_text(feeds[0], build_rss("tides", released + [x for x in creative_pilots if x["kind"] == "tides"]))
    _atomic_write_text(feeds[1], build_rss("fishing", released + [x for x in creative_pilots if x["kind"] == "fishing"]))
    _atomic_write_text(feeds[2], build_rss("surfing", surfing_released + [x for x in creative_pilots if x["kind"] == "surfing"]))
    for feed in feeds:
        _validate_feed_images(feed, public_root)

    return {
        "released_slugs": [item["slug"] for item in released],
        "surfing_released_slugs": [item["slug"] for item in surfing_released],
        "creative_v2_pilots_released": [f'{item["kind"]}:{item["slug"]}' for item in v2_pilots],
        "creative_v3_pilots_released": [f'{item["kind"]}:{item["slug"]}' for item in v3_pilots],
        "creative_v4_pilots_released": [f'{item["kind"]}:{item["slug"]}' for item in v4_pilots],
        "images": images,
        "new_images": new_images,
        "feeds": feeds,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate CoastalNow Pinterest RSS distribution assets")
    parser.add_argument("--date", help="UTC release date in YYYY-MM-DD format; defaults to current UTC date")
    args = parser.parse_args(argv)
    as_of = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    result = generate(as_of)
    print(
        "Pinterest: generated "
        f'{len(result["new_images"])} new image(s), 3 feed(s); '
        f'released={result["released_slugs"]}; '
        f'surfing_released={result["surfing_released_slugs"]}'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
