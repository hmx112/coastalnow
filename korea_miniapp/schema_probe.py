"""Print ONLY public KHOA response field names, never API keys or row values.

Use after an integration run fails due to a missing predicted height field.
The two API endpoints are always tested independently for one station/day.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime

from pipeline import KST, STATIONS, TideDataError, _fetch


def _keys(value: object) -> str:
    if not isinstance(value, dict):
        return "(not a JSON object)"
    # Names only. No values, tokens, URLs or full responses are logged.
    return ", ".join(sorted(map(str, value.keys()))) or "(empty object)"


def _rows(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise TideDataError("API response was not a JSON object")
    root = payload.get("response", payload)
    if not isinstance(root, dict):
        raise TideDataError("Invalid response wrapper")
    body = root.get("body")
    if not isinstance(body, dict):
        raise TideDataError("No JSON body returned")
    items = body.get("items")
    if isinstance(items, dict):
        item = items.get("item")
    else:
        item = items
    if isinstance(item, dict):
        return [item]
    if isinstance(item, list) and all(isinstance(r, dict) for r in item):
        return item
    raise TideDataError("No recognizable item rows")


def describe(kind: str, payload: object) -> str:
    """Sanitized diagnostics safe to share, including zero raw record values."""
    if isinstance(payload, dict):
        root = payload.get("response", payload)
    else:
        root = None
    parts = [f"[{kind}]", f"root fields: {_keys(root)}"]
    body = root.get("body") if isinstance(root, dict) else None
    parts.append(f"body fields: {_keys(body)}")
    items = body.get("items") if isinstance(body, dict) else None
    parts.append(f"items fields: {_keys(items)}" if isinstance(items, dict) else
                 f"items structure: {type(items).__name__}")
    try:
        rows = _rows(payload)
    except TideDataError as exc:
        parts.append(f"row inspection: {exc}")
        return "\n".join(parts)
    parts.append(f"row count: {len(rows)}")
    if not rows:
        return "\n".join(parts + ["no data rows"])
    parts.append(f"first row fields: {_keys(rows[0])}")
    for expected in (("predcDt", "predcTdlvVl", "extrSe") if kind == "high_low"
                     else ("predcDt", "tdlvHgt")):
        parts.append(f"  {expected}: {'present' if expected in rows[0] else 'MISSING'}")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect only API field names; no sensitive values")
    parser.add_argument("--station", choices=tuple(STATIONS), default="incheon")
    parser.add_argument("--date", default=datetime.now(KST).date().isoformat())
    args = parser.parse_args()
    day = date.fromisoformat(args.date)
    station = STATIONS[args.station]
    keys = {
        "high_low": os.getenv("KHOA_HIGH_LOW_KEY") or os.getenv("KHOA_SERVICE_KEY", ""),
        "series": os.getenv("KHOA_SERIES_KEY") or os.getenv("KHOA_HIGH_LOW_KEY") or
                  os.getenv("KHOA_SERVICE_KEY", ""),
    }
    print(f"Schema inspection only: {station['name']} {day.isoformat()} (no API values shown)")
    errors = 0
    for kind in ("high_low", "series"):
        try:
            payload = _fetch(kind, station["id"], day, keys[kind])
            print(describe(kind, payload))
        except TideDataError as exc:
            print(f"[{kind}] request could not be inspected: {exc}")
            errors += 1
    print("Probe finished. Share the lines above; never share API keys or response JSON files.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
