#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fixture = json.loads((ROOT/"src"/"fixtures"/"noaa-9410170-2026-07-10-hilo.json").read_text())

assert fixture["station"] == "9410170"
assert len(fixture["predictions"]) == 4
assert {x["type"] for x in fixture["predictions"]} == {"H","L"}
for x in fixture["predictions"]:
    datetime.strptime(x["t"], "%Y-%m-%d %H:%M")
    float(x["v"])

print("PASS: San Diego NOAA fixture parses correctly.")
for x in fixture["predictions"]:
    print(f'  {x["type"]} {x["t"]} {x["v"]} ft')
