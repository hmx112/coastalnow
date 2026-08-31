# CoastalNow Pinterest RSS Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and release evergreen CoastalNow Pinterest pin images and RSS 2.0 feeds automatically, starting with one U.S. coastal location per day and publishing Tide + Fishing pins to two claimed-domain Pinterest boards.

**Architecture:** A Pinterest-only generator reads the existing `LOCATIONS` catalog and Activity registry, applies a fixed marketing launch order from `src/data/pinterest.json`, renders deterministic 1000×1500 PNGs with Pillow, and serializes two static RSS 2.0 feeds under `public/pinterest/rss/`. A daily GitHub Actions workflow uses the existing `coastalnow-site-writes` concurrency lock, generates only newly due assets, runs regressions, and commits only `public/pinterest/**`. Pinterest then reads the public feeds asynchronously; no Pinterest API token is required in v1.

**Tech Stack:** Python 3.12, Pillow 11.3.0, Python stdlib `xml.etree.ElementTree`, GitHub Actions, Cloudflare Pages, Pinterest RSS Auto-publish.

**Spec:** `docs/superpowers/specs/2026-08-31-pinterest-rss-automation.md`

## Global Constraints

- Pinterest profile display name: `CoastalNow | Coastal Conditions`.
- Pinterest business country/region: `South Korea`.
- Pinterest content language and audience: English / U.S. coastal audience.
- Claimed domain: `https://coastalnowtides.com`.
- Automated v1 boards: `Tide Times & Tide Charts` and `Fishing Conditions & Best Fishing Times` only.
- Release cadence: one location per UTC date, producing at most one Tide item and one Fishing item per day.
- First release location: `san-diego`.
- Pin images are exactly 1000×1500 PNGs and contain only evergreen copy.
- Do not put live Fishing Score, catch probability, tide height, wind speed, water temperature, alert state, dates, or any other volatile measurement into image copy or RSS title/description.
- Do not use NOAA/NWS logos or imply NOAA/NWS sponsorship.
- RSS must be RSS 2.0 XML. Each item contains exactly one Pinterest-consumable image tag (`media:content`) to avoid duplicate-image ingestion.
- Every RSS item link and image URL must use the claimed `coastalnowtides.com` domain.
- Existing Tide URLs, Fishing URLs, scoring, safety gates, NOAA/NWS collection, sitemap policy, and IndexNow behavior must remain unchanged.
- Pinterest generation uses the existing `coastalnow-site-writes` concurrency group.

---

### Task 1: Pinterest configuration, catalog and deterministic release schedule

**Files:**
- Create: `src/data/pinterest.json`
- Create: `src/pinterest/__init__.py`
- Create: `src/pinterest/catalog.py`
- Create: `src/pinterest/schedule.py`
- Create: `src/test_pinterest_catalog_schedule.py`

**Interfaces:**
- Consumes: `locations.LOCATIONS`, `activities.registry.enabled_activities()`.
- Produces: `load_pinterest_config(path: Path) -> dict`, `build_catalog(locations: dict, config: dict) -> list[dict]`, `released_locations(catalog: list[dict], config: dict, as_of: date) -> list[dict]`, `release_date_for_index(start_date: date, index: int, locations_per_day: int) -> date`.

- [ ] **Step 1: Write failing config/catalog/schedule tests**

Create `src/test_pinterest_catalog_schedule.py` with tests that assert:

```python
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from locations import LOCATIONS


class PinterestCatalogScheduleTests(unittest.TestCase):
    def test_config_launch_order_is_complete_unique_and_starts_with_san_diego(self):
        from pinterest.catalog import load_pinterest_config
        config = load_pinterest_config(Path(__file__).parent / "data" / "pinterest.json")
        self.assertTrue(config["enabled"])
        self.assertEqual(config["start_date"], "2026-08-31")
        self.assertEqual(config["locations_per_day"], 1)
        self.assertEqual(config["launch_order"][0], "san-diego")
        self.assertEqual(len(config["launch_order"]), len(set(config["launch_order"])))
        self.assertEqual(set(config["launch_order"]), set(LOCATIONS))

    def test_unknown_or_duplicate_launch_slug_fails(self):
        from pinterest.catalog import validate_launch_order
        with self.assertRaises(ValueError):
            validate_launch_order(["san-diego", "san-diego"], LOCATIONS)
        with self.assertRaises(ValueError):
            validate_launch_order(["not-a-location"], LOCATIONS)

    def test_day_one_releases_only_san_diego_and_day_two_adds_next_location(self):
        from pinterest.catalog import build_catalog, load_pinterest_config
        from pinterest.schedule import released_locations
        config = load_pinterest_config(Path(__file__).parent / "data" / "pinterest.json")
        catalog = build_catalog(LOCATIONS, config)
        self.assertEqual([x["slug"] for x in released_locations(catalog, config, date(2026, 8, 31))], ["san-diego"])
        self.assertEqual(len(released_locations(catalog, config, date(2026, 9, 1))), 2)

    def test_disabled_config_releases_nothing(self):
        from pinterest.schedule import released_locations
        catalog = [{"slug": "san-diego", "release_index": 0}]
        config = {"enabled": False, "start_date": "2026-08-31", "locations_per_day": 1}
        self.assertEqual(released_locations(catalog, config, date(2026, 9, 5)), [])
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python src/test_pinterest_catalog_schedule.py
```

Expected: import/file failures because `src/pinterest/` and `src/data/pinterest.json` do not yet exist.

- [ ] **Step 3: Add fixed launch-order configuration**

Create `src/data/pinterest.json` with:

```json
{
  "enabled": true,
  "start_date": "2026-08-31",
  "locations_per_day": 1,
  "launch_order": [
    "san-diego", "miami-beach", "myrtle-beach", "key-west", "san-francisco",
    "virginia-beach", "clearwater-beach", "huntington-beach", "cape-hatteras", "destin",
    "santa-monica", "hilton-head", "daytona-beach", "la-jolla", "ocean-city",
    "newport-beach", "panama-city-beach", "monterey", "cocoa-beach", "nags-head",
    "malibu", "tampa-bay", "carolina-beach", "fort-lauderdale", "santa-cruz",
    "naples", "wrightsville-beach", "laguna-beach", "st-pete-beach", "cape-may",
    "oceanside", "sanibel-island", "holden-beach", "half-moon-bay", "north-myrtle-beach",
    "kitty-hawk", "folly-beach", "bar-harbor", "corolla", "cannon-beach",
    "kill-devil-hills", "emerald-isle", "lincoln-city", "isle-of-palms", "ocracoke",
    "seaside", "topsail-beach", "kiawah-island", "edisto-beach", "pawleys-island",
    "los-angeles"
  ]
}
```

- [ ] **Step 4: Implement config validation and catalog projection**

Create `src/pinterest/catalog.py` with exact behavior:

```python
from __future__ import annotations

import json
from pathlib import Path

from activities.registry import enabled_activities


def load_pinterest_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("pinterest.json must contain an object")
    if config.get("locations_per_day") != 1:
        raise ValueError("Pinterest v1 requires locations_per_day=1")
    if config.get("enabled") and not config.get("start_date"):
        raise ValueError("Enabled Pinterest config requires start_date")
    if not isinstance(config.get("launch_order"), list):
        raise ValueError("Pinterest launch_order must be a list")
    return config


def validate_launch_order(launch_order: list[str], locations: dict) -> None:
    if len(launch_order) != len(set(launch_order)):
        raise ValueError("Pinterest launch_order contains duplicate slugs")
    unknown = [slug for slug in launch_order if slug not in locations]
    if unknown:
        raise ValueError(f"Pinterest launch_order contains unknown slugs: {unknown}")
    missing = [slug for slug in locations if slug not in launch_order]
    if missing:
        raise ValueError(f"Pinterest launch_order is missing slugs: {missing}")


def build_catalog(locations: dict, config: dict) -> list[dict]:
    order = config["launch_order"]
    validate_launch_order(order, locations)
    fishing_enabled = any(item["slug"] == "fishing" for item in enabled_activities())
    catalog = []
    for index, slug in enumerate(order):
        location = locations[slug]
        catalog.append({
            "slug": slug,
            "name": location["name"],
            "state": location["state"],
            "state_slug": location["state_slug"],
            "release_index": index,
            "tide_page_path": location["page_path"],
            "fishing_enabled": fishing_enabled,
        })
    return catalog
```

- [ ] **Step 5: Implement deterministic release schedule**

Create `src/pinterest/schedule.py`:

```python
from __future__ import annotations

from datetime import date, timedelta


def release_date_for_index(start_date: date, index: int, locations_per_day: int) -> date:
    if locations_per_day != 1:
        raise ValueError("Pinterest v1 supports exactly one location per day")
    return start_date + timedelta(days=index)


def released_locations(catalog: list[dict], config: dict, as_of: date) -> list[dict]:
    if not config.get("enabled"):
        return []
    start = date.fromisoformat(config["start_date"])
    released = []
    for item in catalog:
        release_date = release_date_for_index(start, item["release_index"], config["locations_per_day"])
        if release_date <= as_of:
            released.append({**item, "release_date": release_date})
    return released
```

- [ ] **Step 6: Run Task 1 tests and full regression**

Run:

```bash
python src/test_pinterest_catalog_schedule.py
python -m unittest discover -s src -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 7: Commit Task 1**

```bash
git add src/data/pinterest.json src/pinterest src/test_pinterest_catalog_schedule.py
git commit -m "Add Pinterest release catalog and schedule"
```

---

### Task 2: Evergreen pin metadata and RSS 2.0 serialization

**Files:**
- Create: `src/pinterest/rss.py`
- Create: `src/test_pinterest_rss.py`

**Interfaces:**
- Consumes catalog entries with `release_date`, `state_slug`, `slug`, `name`, `state`.
- Produces: `pin_record(item: dict, kind: str) -> dict`, `build_rss(kind: str, released: list[dict]) -> str`.

- [ ] **Step 1: Write failing RSS tests**

Create `src/test_pinterest_rss.py` to assert:

```python
import unittest
import xml.etree.ElementTree as ET
from datetime import date


class PinterestRssTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "slug": "san-diego",
            "name": "San Diego",
            "state": "California",
            "state_slug": "california",
            "release_date": date(2026, 8, 31),
            "fishing_enabled": True,
        }

    def test_tide_and_fishing_records_use_claimed_domain_and_evergreen_copy(self):
        from pinterest.rss import pin_record
        tide = pin_record(self.location, "tides")
        fishing = pin_record(self.location, "fishing")
        self.assertEqual(tide["link"], "https://coastalnowtides.com/tides/california/san-diego/")
        self.assertEqual(fishing["link"], "https://coastalnowtides.com/tides/california/san-diego/fishing/")
        for record in (tide, fishing):
            self.assertTrue(record["image_url"].startswith("https://coastalnowtides.com/pinterest/images/"))
            for forbidden in ("88", "mph", "ft", "°F", "today's score", "catch probability"):
                self.assertNotIn(forbidden.lower(), (record["title"] + " " + record["description"]).lower())

    def test_feed_is_rss_2_and_each_item_has_exactly_one_media_content(self):
        from pinterest.rss import build_rss
        xml = build_rss("tides", [self.location])
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.attrib["version"], "2.0")
        item = root.find("./channel/item")
        self.assertIsNotNone(item)
        media = [child for child in item if child.tag.endswith("content")]
        self.assertEqual(len(media), 1)
        self.assertEqual(media[0].attrib["type"], "image/png")

    def test_fishing_feed_skips_locations_when_fishing_is_not_enabled(self):
        from pinterest.rss import build_rss
        item = {**self.location, "fishing_enabled": False}
        xml = build_rss("fishing", [item])
        root = ET.fromstring(xml)
        self.assertEqual(root.findall("./channel/item"), [])
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python src/test_pinterest_rss.py
```

Expected: import failure for `pinterest.rss`.

- [ ] **Step 3: Implement evergreen record templates**

Create `src/pinterest/rss.py` with constants:

```python
BASE_URL = "https://coastalnowtides.com"
MEDIA_NS = "http://search.yahoo.com/mrss/"
```

Implement `pin_record()` so Tide records use:

```text
Title: {City}, {State} Tide Times & Tide Chart
Description: Check current tide times and coastal planning information for {City}, {State}. CoastalNow keeps the destination page updated with the latest available tide data.
Image: /pinterest/images/{slug}-tides.png
GUID: coastalnow:pinterest:tides:{slug}:v1
```

and Fishing records use:

```text
Title: {City}, {State} Fishing Conditions & Best Times
Description: Plan shore, pier and nearshore fishing with current tide, wind, wave and weather context for {City}, {State}. CoastalNow Fishing Score is a 0–100 planning metric, not a safety guarantee.
Image: /pinterest/images/{slug}-fishing.png
GUID: coastalnow:pinterest:fishing:{slug}:v1
```

- [ ] **Step 4: Implement RSS 2.0 serializer with one image tag per item**

Use `xml.etree.ElementTree`, register the Media RSS namespace, create `<rss version="2.0">`, `<channel>`, channel title/link/description, and for each released record add `<title>`, `<description>`, `<link>`, `<guid isPermaLink="false">`, `<pubDate>` at `12:00:00 +0000` on the release date, and exactly one `<media:content url="..." medium="image" type="image/png" width="1000" height="1500"/>`.

- [ ] **Step 5: Run RSS tests and full regression**

```bash
python src/test_pinterest_rss.py
python -m unittest discover -s src -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 6: Commit Task 2**

```bash
git add src/pinterest/rss.py src/test_pinterest_rss.py
git commit -m "Add Pinterest RSS feed generation"
```

---

### Task 3: Deterministic 1000×1500 Pinterest image renderer

**Files:**
- Create: `requirements-pinterest.txt`
- Create: `src/pinterest/render.py`
- Create: `src/test_pinterest_render.py`

**Interfaces:**
- Consumes: catalog item + `kind` (`tides` or `fishing`) + output `Path`.
- Produces: `render_pin(item: dict, kind: str, output: Path) -> Path`.

- [ ] **Step 1: Pin Pillow dependency**

Create:

```text
Pillow==11.3.0
```

- [ ] **Step 2: Write failing image tests**

Create `src/test_pinterest_render.py` that uses a temporary directory and asserts both kinds render, both output images are PNG RGB/RGBA at exactly `(1000, 1500)`, and the renderer exposes copy through `pin_text(item, kind)` so the test can assert the strings contain `SAN DIEGO`, `CALIFORNIA`, `TIDE TIMES & TIDE CHART` or `FISHING CONDITIONS & BEST TIMES`, and do not contain volatile units such as `mph`, `ft`, `°F`, `%`, or a date.

- [ ] **Step 3: Run renderer test and verify RED**

```bash
python src/test_pinterest_render.py
```

Expected: import failure for `pinterest.render`.

- [ ] **Step 4: Implement graphic renderer**

Create `src/pinterest/render.py` using Pillow only. Required layout:

```text
Canvas: 1000×1500 RGB
Background: off-white/very light seafoam
Top brand: CoastalNow
Dominant location: CITY (large) + STATE (smaller)
Category: TIDE TIMES & TIDE CHART or FISHING CONDITIONS & BEST TIMES
Graphic: layered teal/navy wave bands and a simple sun/horizon circle
Footer: tides -> Live coastal data on CoastalNow
        fishing -> Live tide, wind & wave context
```

Use `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` and `DejaVuSans.ttf` when present; fall back to `ImageFont.load_default()` only if unavailable. Do not commit fonts.

- [ ] **Step 5: Run renderer tests and full regression**

```bash
python src/test_pinterest_render.py
python -m unittest discover -s src -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 6: Commit Task 3**

```bash
git add requirements-pinterest.txt src/pinterest/render.py src/test_pinterest_render.py
git commit -m "Add CoastalNow Pinterest pin renderer"
```

---

### Task 4: Pinterest generation CLI and static outputs

**Files:**
- Create: `src/generate_pinterest.py`
- Create: `src/test_pinterest_generation.py`
- Generate: `public/pinterest/images/*.png`
- Generate: `public/pinterest/rss/tides.xml`
- Generate: `public/pinterest/rss/fishing.xml`

**Interfaces:**
- Consumes Task 1 catalog/schedule, Task 2 RSS, Task 3 renderer.
- Produces: `generate(as_of: date, public_root: Path, config_path: Path) -> dict[str, list[Path] | Path]` and CLI `python src/generate_pinterest.py [--date YYYY-MM-DD]`.

- [ ] **Step 1: Write failing orchestration tests**

Create tests that run in a temporary public root and assert:

```python
result = generate(date(2026, 8, 31), public_root, config_path)
```

creates exactly:

```text
pinterest/images/san-diego-tides.png
pinterest/images/san-diego-fishing.png
pinterest/rss/tides.xml
pinterest/rss/fishing.xml
```

and that each RSS item references an image file that exists beneath the temp public root. A second run for the same date must produce byte-identical RSS and image files. A run for `2026-09-01` must retain San Diego and add only the second location's two images/items.

- [ ] **Step 2: Run tests and verify RED**

```bash
python src/test_pinterest_generation.py
```

Expected: import failure for `generate_pinterest`.

- [ ] **Step 3: Implement generator and CLI**

`generate()` must:

1. load config
2. build/validate catalog
3. calculate released locations as of date
4. render missing/due Tide images
5. render Fishing images only when Fishing is enabled
6. write both RSS feeds atomically using temporary files + `Path.replace()`
7. parse each generated feed once before returning
8. verify every feed image URL maps to an existing `public/pinterest/images/*.png`

CLI rules:

```text
--date omitted -> datetime.now(timezone.utc).date()
--date YYYY-MM-DD -> deterministic test/manual date
```

- [ ] **Step 4: Run generator tests and full regression**

```bash
python src/test_pinterest_generation.py
python -m unittest discover -s src -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 5: Generate the first real San Diego outputs on the feature branch**

```bash
python src/generate_pinterest.py --date 2026-08-31
```

Verify only San Diego's two PNGs and the two feeds exist.

- [ ] **Step 6: Commit Task 4**

```bash
git add src/generate_pinterest.py src/test_pinterest_generation.py public/pinterest
git commit -m "Generate first CoastalNow Pinterest feeds"
```

---

### Task 5: Daily GitHub Actions release workflow

**Files:**
- Create: `.github/workflows/update-pinterest.yml`
- Create: `src/test_pinterest_workflow.py`

**Interfaces:**
- Runs `python src/generate_pinterest.py` once daily and manually.
- Commits only `public/pinterest/**`.

- [ ] **Step 1: Write failing workflow contract test**

Create `src/test_pinterest_workflow.py` that loads the workflow text and asserts it contains:

```text
workflow_dispatch:
cron: "17 15 * * *"
group: coastalnow-site-writes
cancel-in-progress: false
python-version: "3.12"
pip install -r requirements-pinterest.txt
python src/generate_pinterest.py
python src/test_pinterest_catalog_schedule.py
python src/test_pinterest_rss.py
python src/test_pinterest_render.py
python src/test_pinterest_generation.py
git add public/pinterest
```

and does not contain a `push:` trigger.

- [ ] **Step 2: Run workflow test and verify RED**

```bash
python src/test_pinterest_workflow.py
```

Expected: file-not-found failure.

- [ ] **Step 3: Create daily workflow**

Create `.github/workflows/update-pinterest.yml`:

```yaml
name: Update Pinterest distribution assets

on:
  workflow_dispatch:
  schedule:
    - cron: "17 15 * * *"

permissions:
  contents: write

concurrency:
  group: coastalnow-site-writes
  cancel-in-progress: false

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-pinterest.txt
      - name: Generate due Pinterest assets and feeds
        run: python src/generate_pinterest.py
      - name: Run Pinterest regressions
        run: |
          python src/test_pinterest_catalog_schedule.py
          python src/test_pinterest_rss.py
          python src/test_pinterest_render.py
          python src/test_pinterest_generation.py
          python src/test_pinterest_workflow.py
      - name: Commit Pinterest release
        shell: bash
        run: |
          git config user.name "coastalnow-bot"
          git config user.email "coastalnow-bot@users.noreply.github.com"
          git add public/pinterest
          git diff --cached --quiet || git commit -m "Update Pinterest distribution assets"
          git push
```

- [ ] **Step 4: Run workflow contract and full repository regression**

```bash
python src/test_pinterest_workflow.py
python -m unittest discover -s src -p "test_*.py"
```

Expected: all pass.

- [ ] **Step 5: Commit Task 5**

```bash
git add .github/workflows/update-pinterest.yml src/test_pinterest_workflow.py
git commit -m "Automate daily Pinterest feed releases"
```

---

### Task 6: End-to-end branch verification, PR and production handoff

**Files:**
- Temporary during branch verification only: `.github/workflows/test-pinterest-rss.yml` (must be removed before PR)
- No production files beyond Tasks 1–5.

**Interfaces:**
- Verifies the exact feature branch in GitHub Actions because Pillow/image generation must be exercised on the same Ubuntu environment used by the production workflow.

- [ ] **Step 1: Add temporary feature-branch verification workflow**

It must checkout `feat/pinterest-rss-automation`, install `requirements-pinterest.txt`, run all Pinterest tests, run the complete repository regression suite, and run `python src/generate_pinterest.py --date 2026-08-31` followed by a clean-diff check for committed Pinterest outputs.

- [ ] **Step 2: Verify RED/GREEN history and final GitHub Actions run**

Confirm the final feature-branch run has:

```text
Pinterest catalog/schedule: pass
Pinterest RSS: pass
Pinterest renderer: pass
Pinterest generator: pass
Pinterest workflow contract: pass
Full unittest discovery: pass
Clean Pinterest regeneration: pass
```

- [ ] **Step 3: Remove the temporary workflow**

Delete `.github/workflows/test-pinterest-rss.yml`, then rerun the previously safe branch-only job so it checks out the final branch head and reconfirms all tests without leaving the temporary workflow in the PR diff.

- [ ] **Step 4: Review final diff**

Final diff must contain only:

```text
.github/workflows/update-pinterest.yml
docs/superpowers/specs/2026-08-31-pinterest-rss-automation.md
docs/superpowers/plans/2026-08-31-pinterest-rss-automation.md
requirements-pinterest.txt
src/data/pinterest.json
src/pinterest/**
src/generate_pinterest.py
src/test_pinterest_*.py
public/pinterest/**
```

No existing Tide/Fishing content, scoring, safety, URLs, or current data files may change.

- [ ] **Step 5: Verify Cloudflare branch preview**

Confirm the final feature head has a successful Cloudflare Pages preview and that the preview exposes both RSS XML files and both San Diego PNGs.

- [ ] **Step 6: Create PR and squash merge**

PR title:

```text
Add automated Pinterest RSS distribution
```

Merge only after `mergeable=true`, successful final preview, and full regression evidence.

- [ ] **Step 7: Verify production**

After merge, confirm the merge SHA is current `main`, Cloudflare Pages is successful, and these production assets return successfully:

```text
https://coastalnowtides.com/pinterest/rss/tides.xml
https://coastalnowtides.com/pinterest/rss/fishing.xml
https://coastalnowtides.com/pinterest/images/san-diego-tides.png
https://coastalnowtides.com/pinterest/images/san-diego-fishing.png
```

- [ ] **Step 8: User Pinterest RSS connection**

Once the two production feeds are reachable, instruct the user on desktop Pinterest:

```text
Settings -> Create Pins in bulk -> Auto-publish -> Connect RSS feed
```

Connect:

```text
/pinterest/rss/tides.xml -> Tide Times & Tide Charts
/pinterest/rss/fishing.xml -> Fishing Conditions & Best Fishing Times
```

Pinterest may create Pins within 24 hours after feed updates; it processes older feed content first and supports RSS 2.x feeds with `<title>`, `<description>`, claimed-domain `<link>`, and image tags under each `<item>`.
