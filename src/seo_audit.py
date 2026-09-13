"""Audit generated CoastalNow Tide pages against reusable SEO/content checks."""
from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path

from seo import canonical_url, robots_directive


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta\s+name=["\']description["\'][^>]*content=["\'](.*?)["\'][^>]*>',
    re.IGNORECASE | re.DOTALL,
)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

SEARCH_INTENT_TERMS = (
    "tide times",
    "high tide",
    "low tide",
    "tide chart",
    "tide schedule",
    "today’s tides",
)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return unescape(TAG_RE.sub(" ", value)).strip()


def _first(pattern: re.Pattern[str], html: str) -> str | None:
    match = pattern.search(html)
    return _clean_text(match.group(1)) if match else None


def _empty_result(location: dict) -> dict[str, object]:
    return {
        "slug": location.get("slug"),
        "page_exists": False,
        "title": None,
        "meta_description": None,
        "h1": None,
        "canonical": False,
        "robots": False,
        "breadcrumb_json_ld": False,
        "state_link": False,
        "nearby_link_count": 0,
        "today_tide_events": False,
        "seven_day_forecast": False,
        "noaa_source": False,
        "search_intent_terms": [],
    }


def audit_location_page(public_root: Path, location: dict) -> dict[str, object]:
    """Return deterministic structural/content signals for one generated Tide page."""
    result = _empty_result(location)
    page = Path(public_root) / location["page_path"]
    if not page.exists():
        return result

    html = page.read_text(encoding="utf-8")
    lower = unescape(html).lower()
    expected_canonical = canonical_url(location["page_path"])
    expected_robots = robots_directive(location)

    result.update(
        {
            "page_exists": True,
            "title": _first(TITLE_RE, html),
            "meta_description": _first(DESCRIPTION_RE, html),
            "h1": _first(H1_RE, html),
            "canonical": bool(
                re.search(
                    rf'<link\s+rel=["\']canonical["\'][^>]*href=["\']{re.escape(expected_canonical)}["\']',
                    html,
                    flags=re.IGNORECASE,
                )
            ),
            "robots": bool(
                re.search(
                    rf'<meta\s+name=["\']robots["\'][^>]*content=["\']{re.escape(expected_robots)}["\']',
                    html,
                    flags=re.IGNORECASE,
                )
            ),
            "breadcrumb_json_ld": "BreadcrumbList" in html,
            "state_link": bool(re.search(r'href=["\']\.\./index\.html["\']', html)),
            "nearby_link_count": len(re.findall(r'class=["\']place["\']', html)),
            "today_tide_events": (
                'class="tide-list"' in html
                and bool(re.search(r'class=["\']event["\']', html))
            ),
            "seven_day_forecast": (
                'id="forecast"' in html
                and ("7-day tide schedule" in lower or "7-day tide forecast" in lower)
            ),
            "noaa_source": "noaa" in lower,
            "search_intent_terms": [
                term for term in SEARCH_INTENT_TERMS if term in lower
            ],
        }
    )
    return result


def compare_location_pages(public_root: Path, locations: dict[str, dict], slugs: list[str]) -> list[dict]:
    rows = []
    for slug in slugs:
        location = locations.get(slug)
        if location is None:
            rows.append({**_empty_result({"slug": slug}), "catalog_exists": False})
            continue
        row = audit_location_page(public_root, location)
        row["catalog_exists"] = True
        rows.append(row)
    return rows


def audit_passes(row: dict) -> bool:
    """Return whether a generated Live Tide page satisfies deployment-critical audit checks."""
    return all(
        (
            row.get("page_exists"),
            row.get("title"),
            row.get("meta_description"),
            row.get("h1"),
            row.get("canonical"),
            row.get("robots"),
            row.get("breadcrumb_json_ld"),
            row.get("state_link"),
            int(row.get("nearby_link_count") or 0) >= 1,
            row.get("today_tide_events"),
            row.get("seven_day_forecast"),
            row.get("noaa_source"),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit generated CoastalNow Tide location pages")
    parser.add_argument("--slugs", nargs="+", required=True)
    parser.add_argument("--public-root", default=str(Path(__file__).resolve().parents[1] / "public"))
    args = parser.parse_args(argv)

    from locations import LOCATIONS

    rows = compare_location_pages(Path(args.public_root), LOCATIONS, args.slugs)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0 if all(row.get("catalog_exists") and audit_passes(row) for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
