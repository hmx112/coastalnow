"""Normalize and compare Google Search Console exports for CoastalNow.

Pages and Queries exports stay separate unless a future input explicitly contains
both page and query dimensions. This tool never invents Page × Query attribution.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PAGE_HEADERS = ("Top pages", "Page", "상위 페이지", "페이지")
CLICK_HEADERS = ("Clicks", "클릭수", "클릭")
IMPRESSION_HEADERS = ("Impressions", "노출수", "노출")
CTR_HEADERS = ("CTR",)
POSITION_HEADERS = ("Position", "Average position", "게재순위", "평균 게재순위")
QUERY_HEADERS = ("Top queries", "Query", "상위 검색어", "검색어", "쿼리")

SNAPSHOT_FIELDS = (
    "snapshot_date",
    "url",
    "page_type",
    "state_slug",
    "location_slug",
    "impressions",
    "clicks",
    "ctr",
    "avg_position",
    "indexed",
    "first_impression_date",
)


def _header(fieldnames: list[str] | None, aliases: tuple[str, ...], label: str) -> str:
    available = {str(name).strip().casefold(): name for name in (fieldnames or [])}
    for alias in aliases:
        match = available.get(alias.casefold())
        if match is not None:
            return match
    raise ValueError(f"Search Console CSV is missing {label} column; found {fieldnames or []}")


def _int_value(value: str | None) -> int:
    text = (value or "").strip().replace(",", "")
    if not text:
        return 0
    return int(round(float(text)))


def _float_value(value: str | None) -> float:
    text = (value or "").strip().replace(",", "")
    if not text:
        return 0.0
    return float(text)


def _ctr_value(value: str | None) -> float:
    text = (value or "").strip()
    if not text:
        return 0.0
    if text.endswith("%"):
        text = text[:-1]
    return _float_value(text)


def classify_url(url: str) -> dict[str, str]:
    """Classify a CoastalNow canonical/public URL without requiring the catalog."""
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) == 2 and parts[0] == "tides":
        return {"page_type": "state", "state_slug": parts[1], "location_slug": ""}
    if len(parts) == 3 and parts[0] == "tides":
        return {"page_type": "location", "state_slug": parts[1], "location_slug": parts[2]}
    if len(parts) >= 4 and parts[0] == "tides" and parts[3] in {"fishing", "surfing"}:
        return {"page_type": "activity", "state_slug": parts[1], "location_slug": parts[2]}
    return {"page_type": "other", "state_slug": "", "location_slug": ""}


def parse_pages_csv(path: Path, snapshot_date: date) -> list[dict]:
    """Parse a standard GSC Pages export into stable CoastalNow snapshot rows."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        page_col = _header(reader.fieldnames, PAGE_HEADERS, "page")
        clicks_col = _header(reader.fieldnames, CLICK_HEADERS, "clicks")
        impressions_col = _header(reader.fieldnames, IMPRESSION_HEADERS, "impressions")
        ctr_col = _header(reader.fieldnames, CTR_HEADERS, "CTR")
        position_col = _header(reader.fieldnames, POSITION_HEADERS, "position")
        rows = []
        for raw in reader:
            url = (raw.get(page_col) or "").strip()
            if not url:
                continue
            classification = classify_url(url)
            impressions = _int_value(raw.get(impressions_col))
            rows.append(
                {
                    "snapshot_date": snapshot_date.isoformat(),
                    "url": url,
                    **classification,
                    "impressions": impressions,
                    "clicks": _int_value(raw.get(clicks_col)),
                    "ctr": _ctr_value(raw.get(ctr_col)),
                    "avg_position": _float_value(raw.get(position_col)),
                    "indexed": "",
                    "first_impression_date": snapshot_date.isoformat() if impressions > 0 else "",
                }
            )
    return rows


def parse_queries_csv(path: Path, snapshot_date: date) -> list[dict]:
    """Normalize site-level query rows without assigning them to location pages."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        query_col = _header(reader.fieldnames, QUERY_HEADERS, "query")
        clicks_col = _header(reader.fieldnames, CLICK_HEADERS, "clicks")
        impressions_col = _header(reader.fieldnames, IMPRESSION_HEADERS, "impressions")
        ctr_col = _header(reader.fieldnames, CTR_HEADERS, "CTR")
        position_col = _header(reader.fieldnames, POSITION_HEADERS, "position")
        return [
            {
                "snapshot_date": snapshot_date.isoformat(),
                "query": (raw.get(query_col) or "").strip(),
                "impressions": _int_value(raw.get(impressions_col)),
                "clicks": _int_value(raw.get(clicks_col)),
                "ctr": _ctr_value(raw.get(ctr_col)),
                "avg_position": _float_value(raw.get(position_col)),
            }
            for raw in reader
            if (raw.get(query_col) or "").strip()
        ]


def _number(row: dict | None, key: str, default=0):
    if not row:
        return default
    value = row.get(key, default)
    if value in {None, ""}:
        return default
    return float(value) if key in {"ctr", "avg_position"} else int(float(value))


def compare_snapshots(previous: list[dict], current: list[dict]) -> dict:
    """Compare normalized page snapshots and aggregate cluster growth by state."""
    previous_by_url = {row["url"]: row for row in previous}
    current_by_url = {row["url"]: row for row in current}
    pages = {}
    new_first_impressions = []

    for url in sorted(set(previous_by_url) | set(current_by_url)):
        before = previous_by_url.get(url)
        after = current_by_url.get(url)
        reference = after or before or {}
        previous_impressions = _number(before, "impressions")
        current_impressions = _number(after, "impressions")
        previous_clicks = _number(before, "clicks")
        current_clicks = _number(after, "clicks")
        previous_ctr = _number(before, "ctr", 0.0)
        current_ctr = _number(after, "ctr", 0.0)
        previous_position = _number(before, "avg_position", 0.0)
        current_position = _number(after, "avg_position", 0.0)

        first_date = (before or {}).get("first_impression_date") or ""
        if not first_date and previous_impressions > 0:
            first_date = (before or {}).get("snapshot_date", "")
        is_new_first = previous_impressions <= 0 and current_impressions > 0
        if is_new_first:
            first_date = (after or {}).get("first_impression_date") or (after or {}).get("snapshot_date", "")
            new_first_impressions.append(url)

        position_delta = None
        if before and after and previous_position > 0 and current_position > 0:
            position_delta = round(current_position - previous_position, 4)

        pages[url] = {
            "url": url,
            "page_type": reference.get("page_type", "other"),
            "state_slug": reference.get("state_slug", ""),
            "location_slug": reference.get("location_slug", ""),
            "previous_impressions": previous_impressions,
            "current_impressions": current_impressions,
            "impressions_delta": current_impressions - previous_impressions,
            "previous_clicks": previous_clicks,
            "current_clicks": current_clicks,
            "clicks_delta": current_clicks - previous_clicks,
            "previous_ctr": previous_ctr,
            "current_ctr": current_ctr,
            "ctr_delta": round(current_ctr - previous_ctr, 4),
            "previous_position": previous_position or None,
            "current_position": current_position or None,
            "position_delta": position_delta,
            "indexed": (after or before or {}).get("indexed", ""),
            "first_impression_date": first_date,
        }

    state_totals = defaultdict(lambda: {
        "previous_impressions": 0,
        "current_impressions": 0,
        "previous_clicks": 0,
        "current_clicks": 0,
    })
    for page in pages.values():
        state = page.get("state_slug")
        if not state:
            continue
        totals = state_totals[state]
        for key in ("previous_impressions", "current_impressions", "previous_clicks", "current_clicks"):
            totals[key] += int(page[key])

    states = {}
    for state, totals in state_totals.items():
        states[state] = {
            **totals,
            "impressions_delta": totals["current_impressions"] - totals["previous_impressions"],
            "clicks_delta": totals["current_clicks"] - totals["previous_clicks"],
        }
    fastest = [
        {"state_slug": state, **values}
        for state, values in states.items()
    ]
    fastest.sort(key=lambda row: (-row["impressions_delta"], -row["clicks_delta"], row["state_slug"]))

    return {
        "pages": pages,
        "states": states,
        "fastest_growing_states": fastest,
        "new_first_impressions": new_first_impressions,
    }


def write_snapshot(rows: list[dict], output: Path) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in SNAPSHOT_FIELDS} for row in rows)


def read_snapshot(path: Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_queries(rows: list[dict], output: Path) -> None:
    fields = ("snapshot_date", "query", "impressions", "clicks", "ctr", "avg_position")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_comparison(report: dict, output: Path) -> None:
    """Write page deltas to CSV and state-growth summary to a sibling JSON file."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    page_rows = list(report["pages"].values())
    fields = (
        "url", "page_type", "state_slug", "location_slug",
        "previous_impressions", "current_impressions", "impressions_delta",
        "previous_clicks", "current_clicks", "clicks_delta",
        "previous_ctr", "current_ctr", "ctr_delta",
        "previous_position", "current_position", "position_delta",
        "indexed", "first_impression_date",
    )
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in page_rows)
    summary = output.with_name(output.stem + "-states.json")
    summary.write_text(
        json.dumps(
            {
                "states": report["states"],
                "fastest_growing_states": report["fastest_growing_states"],
                "new_first_impressions": report["new_first_impressions"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize and compare CoastalNow Search Console exports")
    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot", help="Normalize a Search Console Pages export")
    snapshot.add_argument("--pages", required=True)
    snapshot.add_argument("--date", required=True, type=_parse_date)
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--queries")
    snapshot.add_argument("--queries-output")

    compare = sub.add_parser("compare", help="Compare two normalized page snapshots")
    compare.add_argument("--previous", required=True)
    compare.add_argument("--current", required=True)
    compare.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    if args.command == "snapshot":
        rows = parse_pages_csv(Path(args.pages), args.date)
        write_snapshot(rows, Path(args.output))
        if args.queries:
            query_output = Path(args.queries_output) if args.queries_output else Path(args.output).with_name(Path(args.output).stem + "-queries.csv")
            write_queries(parse_queries_csv(Path(args.queries), args.date), query_output)
        return 0

    report = compare_snapshots(read_snapshot(Path(args.previous)), read_snapshot(Path(args.current)))
    write_comparison(report, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
