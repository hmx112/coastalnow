"""Build seven consecutive Korean tidal forecast days per station.

Uses the already verified per-day KHOA adapter; no fake or interpolated tides.
This is a local development collector, NOT a deployed scheduler. Publishing and
Cloudflare cache wiring must be tested separately before production deployment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline import KST, STATIONS, TideDataError, fetch_one_day

DEFAULT_DAYS = 7
MAX_DAYS = 7


def build_week(station_slug: str, first_date: date, high_low_key: str,
               series_key: str, *, days: int = DEFAULT_DAYS) -> dict:
    """Fetch and validate all days before yielding a publishable station bundle."""
    if station_slug not in STATIONS:
        raise ValueError(f"Unknown station: {station_slug}")
    if not (1 <= days <= MAX_DAYS):
        raise ValueError("days must be 1..7")
    if not high_low_key.strip() or not series_key.strip():
        raise TideDataError("Both KHOA service keys are required")
    station = STATIONS[station_slug]
    forecasts = []
    for index in range(days):
        day = first_date + timedelta(days=index)
        data = fetch_one_day(station_slug, day, high_low_key, series_key)
        if data.get("date") != day.isoformat() or data.get("station", {}).get("id") != station["id"]:
            raise TideDataError("Station/date mismatch in daily API result")
        if data.get("units") != "cm" or not data.get("hilo") or not data.get("curve"):
            raise TideDataError("Incomplete daily API result")
        forecasts.append({
            "date": day.isoformat(),
            "hilo": data["hilo"],
            "curve": data["curve"],
        })
    if len(forecasts) != days or len({item["date"] for item in forecasts}) != days:
        raise TideDataError("Invalid forecast coverage")
    return {
        "schema_version": 1,
        "mode": "live",
        "source": "KHOA / public data portal",
        "attribution": "국립해양조사원 조석예보 (공공누리 제1유형: 출처표시)",
        "station": {"id": station["id"], "name": station["name"], "timezone": "Asia/Seoul"},
        "units": "cm",
        "datum": "unverified; do not interpret values as water depth",
        "date_range": {"start": first_date.isoformat(), "end": (first_date + timedelta(days=days-1)).isoformat()},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": forecasts,
    }


def atomic_write_json(path: Path, payload: dict) -> None:
    """Never replace an earlier verified bundle until the new bundle is complete."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".pending-", suffix=".json", delete=False) as file:
            tmp_name = file.name
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(tmp_name, path)
    finally:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect verified KHOA 7-day forecasts")
    parser.add_argument("--station", choices=("all", *STATIONS), default="all")
    parser.add_argument("--start-date", default=datetime.now(KST).date().isoformat())
    parser.add_argument("--output-dir", default=str(Path(__file__).parent / "output" / "weekly"))
    parser.add_argument("--dry-run", action="store_true", help="Print planned request counts, no network")
    args = parser.parse_args()
    try:
        start = date.fromisoformat(args.start_date)
        slugs = tuple(STATIONS) if args.station == "all" else (args.station,)
        expected = len(slugs) * DEFAULT_DAYS * 2
        if args.dry_run:
            print(f"DRY-RUN: stations={','.join(slugs)} days={DEFAULT_DAYS} total_provider_requests={expected} (not sent)")
            return 0
        high_low_key = os.getenv("KHOA_HIGH_LOW_KEY") or os.getenv("KHOA_SERVICE_KEY", "")
        series_key = os.getenv("KHOA_SERIES_KEY") or high_low_key
        if not high_low_key.strip() or not series_key.strip():
            raise TideDataError("KHOA API keys missing from local environment")
        failures = 0
        for slug in slugs:
            try:
                result = build_week(slug, start, high_low_key, series_key)
                output = Path(args.output_dir) / f"{slug}.json"
                atomic_write_json(output, result)
                print(f"PASS {slug}: {len(result['days'])} days; "
                      f"high/low={sum(len(d['hilo']) for d in result['days'])}; "
                      f"series={sum(len(d['curve']) for d in result['days'])}; "
                      f"last={result['date_range']['end']}")
            except (TideDataError, ValueError, OSError) as exc:
                print(f"FAILED {slug}: {exc} (existing cache not replaced)", file=sys.stderr)
                failures += 1
        print(f"WEEK SUMMARY: {len(slugs)-failures}/{len(slugs)} stations complete; "
              f"expected provider requests <= {expected}")
        return 1 if failures else 0
    except (ValueError, TideDataError) as exc:
        print(f"KHOA weekly validation incomplete: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
