"""KHOA tide API adapter experiment for a possible Apps-in-Toss mini app.

This module is NOT wired into CoastalNow production. It fetches one day's
high/low events and time-series predictions, validates them, and writes a
normalized JSON document. The API key is read only from an environment variable.
No simulated or stale data is silently substituted for a failed live request.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

API_ROOT = "https://apis.data.go.kr/1192136"
OPERATIONS = {
    "high_low": "tideFcstHghLw/GetTideFcstHghLwApiService",
    "series": "tideFcstTime/GetTideFcstTimeApiService",
}
# KHOA observation codes. Confirmed in public station inventories; the service
# must validate the response's station identity before expanding this roster.
STATIONS = {
    "incheon": {"id": "DT_0001", "name": "인천"},
    "busan": {"id": "DT_0005", "name": "부산"},
    "jeju": {"id": "DT_0004", "name": "제주"},
}
KST = ZoneInfo("Asia/Seoul")
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
    "%Y%m%d%H%M%S", "%Y%m%d%H%M",
)


class TideDataError(ValueError):
    """A provider error, invalid response, or unsafe prediction data."""


def _parse_kst(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TideDataError("Missing prediction timestamp (predcDt)")
    raw = value.strip()
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=KST)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TideDataError("Unrecognized prediction timestamp format") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def _value_cm(item: dict) -> float:
    if "predcTdlvVl" not in item:
        raise TideDataError("Missing predicted tide height (predcTdlvVl)")
    try:
        value = float(item["predcTdlvVl"])
    except (ValueError, TypeError) as exc:
        raise TideDataError("Invalid predicted tide height") from exc
    # This is a validation guard, not a claim about a particular sea level datum.
    if not math.isfinite(value) or not -500 <= value <= 2000:
        raise TideDataError("Prediction height outside conservative cm sanity range")
    return round(value, 3)


def _items(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise TideDataError("Provider response must be a JSON object")
    root = payload.get("response", payload)
    if not isinstance(root, dict):
        raise TideDataError("Invalid provider response envelope")
    header = root.get("header")
    if isinstance(header, dict):
        code = header.get("resultCode")
        if code is not None and str(code).strip() not in {"00", "0", "200"}:
            raise TideDataError(f"KHOA API rejected request (resultCode={code})")
    body = root.get("body")
    if not isinstance(body, dict):
        raise TideDataError("Missing KHOA response body; check authentication and API status")
    items = body.get("items")
    if isinstance(items, dict):
        raw = items.get("item")
    else:
        raw = items  # Some data.go.kr APIs return `items` as an array.
    if isinstance(raw, dict):
        rows = [raw]
    elif isinstance(raw, list):
        rows = raw
    else:
        raise TideDataError("Missing body.items.item; live API shape must be checked")
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise TideDataError("No valid tide prediction rows")
    return rows


def normalize_day(payload: object, day: date, kind: str) -> list[dict]:
    """Normalize provider rows without fabricating missing values.

    Field names follow KHOA's published API / publicly documented integration
    examples. Their live behavior must be confirmed with an authorized API key.
    """
    if kind not in OPERATIONS:
        raise ValueError(f"Unsupported prediction kind: {kind}")
    result: list[dict] = []
    for item in _items(payload):
        when = _parse_kst(item.get("predcDt"))
        if when.date() != day:
            raise TideDataError("KHOA prediction outside requested KST date")
        row = {"t": when.strftime("%Y-%m-%d %H:%M"), "v": _value_cm(item)}
        if kind == "high_low":
            try:
                extreme = int(item["extrSe"])
            except (KeyError, ValueError, TypeError) as exc:
                raise TideDataError("Missing or unknown high/low identifier (extrSe)") from exc
            if extreme not in (1, 2, 3, 4):
                raise TideDataError("Unknown high/low identifier (extrSe)")
            row["type"] = "H" if extreme in (1, 3) else "L"
        result.append(row)
    result.sort(key=lambda x: x["t"])
    if len({r["t"] for r in result}) != len(result):
        raise TideDataError("Duplicate KHOA prediction timestamps")
    if kind == "high_low" and not {"H", "L"}.issubset({r["type"] for r in result}):
        raise TideDataError("High/low response missing at least one tide extreme")
    if kind == "series" and len(result) < 30:
        raise TideDataError("Too few hourly/30-minute values for a daily tide graph")
    return result


def _fetch(kind: str, station_id: str, day: date, key: str) -> object:
    if kind not in OPERATIONS:
        raise ValueError("Unsupported API operation")
    if not re.fullmatch(r"DT_\d{4}", station_id):
        raise ValueError("Invalid KHOA station code")
    if not key.strip():
        raise TideDataError("KHOA_SERVICE_KEY is not set")
    params = {
        "serviceKey": key.strip(),
        "obsCode": station_id,
        "reqDate": day.strftime("%Y%m%d"),
        "type": "json",
        "numOfRows": "300",
    }
    if kind == "series":
        params["min"] = "30"
    query = urllib.parse.urlencode(params)
    url = f"{API_ROOT}/{OPERATIONS[kind]}?{query}"
    # Never expose `url` or raw exception text: the URL embeds the API key.
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "CoastalNow-Korea-Tide-Experiment/0.1"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        raise TideDataError(f"KHOA HTTP {exc.code}; check API key and approved access") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TideDataError(f"KHOA network error ({type(exc).__name__})") from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TideDataError("KHOA did not return valid JSON; check type=json and API status") from None


def fetch_one_day(station_slug: str, day: date, key: str) -> dict:
    """Make exactly two requests and return validated, provider-originated data."""
    if station_slug not in STATIONS:
        raise ValueError("Station must be one of: incheon, busan, jeju")
    station = STATIONS[station_slug]
    hilo = normalize_day(_fetch("high_low", station["id"], day, key), day, "high_low")
    curve = normalize_day(_fetch("series", station["id"], day, key), day, "series")
    return {
        "schema_version": 1,
        "mode": "live",
        "source": "KHOA / public data portal",
        "source_url": "https://www.data.go.kr/data/15156018/openapi.do",
        "station": {"id": station["id"], "name": station["name"], "timezone": "Asia/Seoul"},
        "units": "cm",
        "datum": "provider reference; confirm official vertical datum before public display",
        "date": day.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hilo": hilo,
        "curve": curve,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate KHOA tide API responses in isolation")
    parser.add_argument("--station", choices=tuple(STATIONS), default="incheon")
    parser.add_argument("--date", default=datetime.now(KST).date().isoformat(), help="YYYY-MM-DD in KST")
    parser.add_argument("--output", help="JSON output path (not inside production public/data)")
    parser.add_argument("--dry-run", action="store_true", help="No network; prints nonsecret request metadata")
    args = parser.parse_args()
    try:
        day = date.fromisoformat(args.date)
        if args.dry_run:
            print(json.dumps({
                "station": STATIONS[args.station], "date": day.isoformat(),
                "operations": list(OPERATIONS.values()),
                "credentials_present": bool(os.getenv("KHOA_SERVICE_KEY")),
                "network_called": False,
            }, ensure_ascii=False, indent=2))
            return 0
        result = fetch_one_day(args.station, day, os.getenv("KHOA_SERVICE_KEY", ""))
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(serialized + "\n", encoding="utf-8")
            print(f"Validated one KHOA station/day: {result['station']['name']} {result['date']}; wrote {target}")
        else:
            print(serialized)
        return 0
    except (TideDataError, ValueError) as exc:
        print(f"KHOA verification incomplete: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
