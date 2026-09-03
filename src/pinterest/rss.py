"""Evergreen Pinterest pin metadata and RSS 2.0 serialization."""
from __future__ import annotations

from datetime import datetime, time, timezone
from email.utils import format_datetime
import xml.etree.ElementTree as ET

BASE_URL = "https://coastalnowtides.com"
MEDIA_NS = "http://search.yahoo.com/mrss/"
ET.register_namespace("media", MEDIA_NS)


def _validate_kind(kind: str) -> None:
    if kind not in {"tides", "fishing", "surfing"}:
        raise ValueError(f"Unsupported Pinterest feed kind: {kind}")


def pin_record(item: dict, kind: str) -> dict:
    _validate_kind(kind)
    slug = item["slug"]
    state_slug = item["state_slug"]
    name = item["name"]
    state = item["state"]

    if kind == "tides":
        title = f"{name}, {state} Tide Times & Tide Chart"
        description = (
            f"Check current tide times and coastal planning information for {name}, {state}. "
            "CoastalNow keeps the destination page updated with the latest available tide data."
        )
        link = f"{BASE_URL}/tides/{state_slug}/{slug}/"
        image_url = f"{BASE_URL}/pinterest/images/{slug}-tides.png"
    elif kind == "fishing":
        title = f"{name}, {state} Fishing Conditions & Best Times"
        description = (
            f"Plan shore, pier and nearshore fishing with current tide, wind, wave and weather context for {name}, {state}. "
            "CoastalNow Fishing Score is a 0–100 planning metric, not a safety guarantee."
        )
        link = f"{BASE_URL}/tides/{state_slug}/{slug}/fishing/"
        image_url = f"{BASE_URL}/pinterest/images/{slug}-fishing.png"
    else:
        title = f"{name}, {state} Surf Conditions & Best Times"
        description = (
            f"Plan coastal surf sessions with current wave, wind and weather context for {name}, {state}. "
            "CoastalNow Surf Conditions Score is a planning metric, not a safety guarantee or break-specific forecast."
        )
        link = f"{BASE_URL}/tides/{state_slug}/{slug}/surfing/"
        image_url = f"{BASE_URL}/pinterest/images/{slug}-surfing.png"

    return {
        "kind": kind,
        "title": title,
        "description": description,
        "link": link,
        "image_url": image_url,
        "guid": f"coastalnow:pinterest:{kind}:{slug}:v1",
        "release_date": item["release_date"],
    }


def _pub_date(value) -> str:
    stamp = datetime.combine(value, time(hour=12), tzinfo=timezone.utc)
    return format_datetime(stamp)


def _channel_copy(kind: str) -> tuple[str, str]:
    if kind == "tides":
        return (
            "CoastalNow Tide Times & Tide Charts",
            "Evergreen U.S. coastal tide planning pins from CoastalNow.",
        )
    if kind == "fishing":
        return (
            "CoastalNow Fishing Conditions & Best Times",
            "Evergreen U.S. shore, pier and nearshore fishing planning pins from CoastalNow.",
        )
    return (
        "CoastalNow Surf Conditions & Best Times",
        "Evergreen U.S. coastal surf planning pins from CoastalNow.",
    )


def _enabled_for_kind(location: dict, kind: str) -> bool:
    if kind == "fishing":
        return bool(location.get("fishing_enabled"))
    if kind == "surfing":
        return bool(location.get("surfing_enabled"))
    return True


def build_rss(kind: str, released: list[dict]) -> str:
    _validate_kind(kind)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    title, description = _channel_copy(kind)
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "link").text = BASE_URL + "/"

    seen_guids: set[str] = set()
    seen_links: set[str] = set()
    seen_images: set[str] = set()

    for location in released:
        if not _enabled_for_kind(location, kind):
            continue
        record = pin_record(location, kind)
        identities = (
            ("GUID", record["guid"], seen_guids),
            ("link", record["link"], seen_links),
            ("image URL", record["image_url"], seen_images),
        )
        for label, value, seen in identities:
            if value in seen:
                raise ValueError(f"Duplicate Pinterest {kind} RSS {label}: {value}")
            seen.add(value)

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = record["title"]
        ET.SubElement(item, "description").text = record["description"]
        ET.SubElement(item, "link").text = record["link"]
        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = record["guid"]
        ET.SubElement(item, "pubDate").text = _pub_date(record["release_date"])
        ET.SubElement(
            item,
            f"{{{MEDIA_NS}}}content",
            {
                "url": record["image_url"],
                "medium": "image",
                "type": "image/png",
                "width": "1000",
                "height": "1500",
            },
        )

    return ET.tostring(rss, encoding="utf-8", xml_declaration=True).decode("utf-8")
