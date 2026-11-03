"""Evergreen Pinterest pin metadata and RSS 2.0 serialization."""
from __future__ import annotations

from datetime import datetime, time, timezone
from email.utils import format_datetime
from urllib.parse import urlencode
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

    version = item.get("creative_version", "v1")
    if version == "v2":
        # Alternative creative, same useful canonical destination. Analytics
        # attribution makes the pilot's outbound clicks distinguishable.
        theme = {
            "tides": ("Low Tide Guide", "Plan a beach visit with NOAA high/low tide timing and a local seven-day chart."),
            "fishing": ("Shore Fishing Planner", "Check NOAA tides and NWS wind, wave and alert context before a shore or pier visit."),
            "surfing": ("Surf Conditions Guide", "Compare forecast wave height, period, wind and official marine alerts before visiting."),
        }[kind]
        title = f"{name}, {state} | {theme[0]}"
        description = f"{theme[1]} Open CoastalNow for the updated forecast and source limitations."
        image_url = f"{BASE_URL}/pinterest/images/{slug}-{kind}-v2.png"
        link += "?" + urlencode({
            "utm_source": "pinterest",
            "utm_medium": "organic",
            "utm_campaign": "coastalnow_creative_v2",
            "utm_content": f"{kind}_{slug}",
        })
    elif version == "v3":
        copy = {
            "tides": (
                "Low Tide Beach Guide",
                "Find the local high and low tide times, NOAA station details and a seven-day chart for coastal planning.",
            ),
            "fishing": (
                "Shore Fishing Field Notes",
                "Before you cast, check NOAA tide timing and NWS wind, wave and marine alert context for the coast.",
            ),
            "surfing": (
                "Read the Waves",
                "Use regional wave height, period and wind data to plan your visit. Check official marine alerts and local conditions.",
            ),
        }[kind]
        title = f"{name}, {state} | {copy[0]}"
        description = f"{copy[1]} Visit CoastalNow for up-to-date sources and limitations."
        image_url = f"{BASE_URL}/pinterest/images/{slug}-{kind}-v3.png"
        link += "?" + urlencode({
            "utm_source": "pinterest",
            "utm_medium": "organic",
            "utm_campaign": "coastalnow_html_v3",
            "utm_content": f"{kind}_{slug}",
        })
    elif version == "v4":
        copy = {
            "tides": (
                "Tide Times & Chart | 7-Day NOAA Guide",
                "Understand high and low tides with an illustrative chart, then check updated NOAA tide times and the seven-day local outlook on CoastalNow.",
            ),
            "fishing": (
                "Shore Fishing Conditions | Tide, Wind & Alerts",
                "Before shore fishing, review NOAA tides, NWS wind and waves, and official marine alerts. See current local planning information on CoastalNow.",
            ),
            "surfing": (
                "Surf Forecast | Height, Period & Wind",
                "Explore regional wave height, swell period and wind forecasts, with official marine alerts and limitations. Not a break-specific safety forecast.",
            ),
        }[kind]
        title = f"{name}, {state} | {copy[0]}"
        description = copy[1]
        image_url = f"{BASE_URL}/pinterest/images/{slug}-{kind}-v4.png"
        link += "?" + urlencode({
            "utm_source": "pinterest",
            "utm_medium": "organic",
            "utm_campaign": "coastalnow_info_v4",
            "utm_content": f"{kind}_{slug}",
        })
    elif version != "v1":
        raise ValueError(f"Unknown Pinterest creative version: {version}")

    return {
        "kind": kind,
        "title": title,
        "description": description,
        "link": link,
        "image_url": image_url,
        "guid": f"coastalnow:pinterest:{kind}:{slug}:{version}",
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

    # Feed readers often inspect the newest items first. Preserve existing
    # item GUIDs/URLs; only change the ordering in the RSS document.
    for location in sorted(released, key=lambda x: (x["release_date"], x["slug"], x.get("creative_version", "v1")), reverse=True):
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
