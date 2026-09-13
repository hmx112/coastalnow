# CoastalNow SEO Foundation PR A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen existing CoastalNow tide pages and California/Florida state landing pages before adding new locations, while adding deterministic nearby links, answer-first tide presentation, SEO audits, and repeatable Search Console comparison tooling.

**Architecture:** Keep the existing static-site pipeline and public URL scheme. Add small focused helpers for state landing metadata, geographic nearby-link generation, SEO auditing, and Search Console snapshot comparison; wire those helpers into the existing `locations.py`, `site_generator.py`, `generate_tides.py`, and regression workflow without changing NOAA as the data source.

**Tech Stack:** Python 3.12 standard library, static HTML/CSS, NOAA CO-OPS JSON feeds, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-coastalnow-gsc-cluster-expansion-design.md`

## Global Constraints

- Existing public location URL pattern remains `/tides/{state_slug}/{location_slug}/`.
- Long-term hierarchy remains `Country → State → Location`.
- NOAA remains the tide source.
- No large nationwide expansion in PR A.
- California and Florida state pages become search landing pages without keyword stuffing.
- All Live NOAA pages cover Tide Times, High Tide, Low Tide, Tide Chart, Tide Schedule, and Today’s Tides naturally.
- Preview pages remain `noindex,follow` and excluded from the sitemap.
- Standard `Pages.csv` and `Queries.csv` exports must not be falsely joined into Page × Query attribution.
- Use TDD for each behavior change.

---

## File Structure

- Create: `src/state_landing.py` — state-specific landing metadata and region membership helpers.
- Create: `src/location_links.py` — haversine distance and nearest same-state Live NOAA links.
- Create: `src/seo_audit.py` — reusable generated-page audit and CLI report for existing/no-impression pages.
- Create: `src/tools/__init__.py` — tools package marker.
- Create: `src/tools/gsc_report.py` — Search Console Pages CSV normalization and snapshot comparison.
- Create: `src/test_state_landing.py` — state landing structure tests.
- Create: `src/test_location_links.py` — nearby-link tests.
- Create: `src/test_location_seo_template.py` — location search-intent and answer-first tests.
- Create: `src/test_seo_audit.py` — audit tests.
- Create: `src/test_gsc_report.py` — GSC parser/comparison tests.
- Modify: `src/locations.py` — richer title/description copy and attach generated nearby links.
- Modify: `src/site_generator.py` — render California/Florida landing sections from state metadata.
- Modify: `src/generate_tides.py` — make answer-first tide block standard for Live pages, move Activity CTA after core tide answer, expose explicit state-directory link replacement.
- Modify: `src/templates/tide-page.html` — Tide Chart / Tide Schedule headings and state/nearby navigation copy.
- Modify: `src/test_directory_generation.py` — permanent state-page and directory regressions.
- Modify: `src/test_seo_generation.py` — location metadata/search-intent regressions.
- Modify: `.github/workflows/update-san-diego.yml` — run new offline SEO regressions.

---

### Task 1: Add deterministic nearby-location generation

**Files:**
- Create: `src/location_links.py`
- Create: `src/test_location_links.py`
- Modify: `src/locations.py`

**Interfaces:**
- Produces: `distance_miles(a: dict, b: dict) -> float`
- Produces: `nearest_same_state_locations(location: dict, locations: dict[str, dict], limit: int = 4) -> list[dict]`
- Consumes: location dictionaries with `latitude`, `longitude`, `state_slug`, `status`, `slug`, and `name`.

- [ ] **Step 1: Write failing nearby-link tests**

```python
from location_links import nearest_same_state_locations


def test_nearby_links_use_nearest_live_locations_in_same_state():
    locations = {
        "origin": {"slug": "origin", "name": "Origin", "state_slug": "california", "status": "Live NOAA", "latitude": 33.0, "longitude": -117.0},
        "near": {"slug": "near", "name": "Near", "state_slug": "california", "status": "Live NOAA", "latitude": 33.1, "longitude": -117.0},
        "far": {"slug": "far", "name": "Far", "state_slug": "california", "status": "Live NOAA", "latitude": 35.0, "longitude": -117.0},
        "preview": {"slug": "preview", "name": "Preview", "state_slug": "california", "status": "Preview", "latitude": 33.05, "longitude": -117.0},
        "other": {"slug": "other", "name": "Other", "state_slug": "florida", "status": "Live NOAA", "latitude": 33.01, "longitude": -117.0},
    }
    result = nearest_same_state_locations(locations["origin"], locations, limit=4)
    assert [item["slug"] for item in result] == ["near", "far"]
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python src/test_location_links.py`
Expected: FAIL because `location_links` or the target functions do not exist.

- [ ] **Step 3: Implement haversine distance and deterministic filtering**

```python
from math import asin, cos, radians, sin, sqrt


def distance_miles(a, b):
    lat1, lon1 = radians(a["latitude"]), radians(a["longitude"])
    lat2, lon2 = radians(b["latitude"]), radians(b["longitude"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3958.7613 * 2 * asin(sqrt(h))


def nearest_same_state_locations(location, locations, limit=4):
    candidates = [
        item for item in locations.values()
        if item["slug"] != location["slug"]
        and item["state_slug"] == location["state_slug"]
        and item.get("status") == "Live NOAA"
        and item.get("latitude") is not None
        and item.get("longitude") is not None
    ]
    return sorted(candidates, key=lambda item: (distance_miles(location, item), item["name"]))[:limit]
```

- [ ] **Step 4: Attach nearby links after the catalog is fully loaded**

In `locations.py`, load all base locations first, then assign:

```python
for location in locations.values():
    location["nearby"] = nearest_same_state_locations(location, locations, limit=4)
```

Do not compute nearby links inside the per-item construction loop because the full catalog is not available yet.

- [ ] **Step 5: Run tests**

Run: `python src/test_location_links.py && python src/test_directory_generation.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/location_links.py src/test_location_links.py src/locations.py
git commit -m "Add geographic nearby tide links"
```

---

### Task 2: Convert California and Florida state pages into search landing pages

**Files:**
- Create: `src/state_landing.py`
- Create: `src/test_state_landing.py`
- Modify: `src/site_generator.py`
- Modify: `src/test_directory_generation.py`

**Interfaces:**
- Produces: `state_landing_config(state_slug: str) -> dict | None`
- Produces: `state_region_items(state_slug: str, region_key: str, items: list[dict]) -> list[dict]`
- Consumes: current `LOCATIONS` entries and explicit region membership slugs.

- [ ] **Step 1: Write failing state landing tests**

```python
from site_generator import build_directory_pages


def test_california_state_page_is_a_search_landing_page():
    html = build_directory_pages()["tides/california/index.html"]
    assert "California Tide Times" in html
    assert "Featured California tide locations" in html
    assert "Southern California Tides" in html
    assert "Northern California Tides" in html
    assert "California tide schedule" in html
    assert "SoCal tides" in html


def test_florida_state_page_has_featured_and_regional_sections():
    html = build_directory_pages()["tides/florida/index.html"]
    assert "Featured Florida tide locations" in html
    assert "South Florida Tides" in html
    assert "Gulf Coast Tides" in html
    assert "Atlantic Coast & Keys Tides" in html
```

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_state_landing.py`
Expected: FAIL because state pages currently render only a generic hero plus full location grid.

- [ ] **Step 3: Add explicit state landing configuration**

Use a Python constant rather than geographic auto-classification:

```python
STATE_LANDING = {
    "california": {
        "featured": ["oceanside", "huntington-beach", "los-angeles", "san-diego"],
        "intro": "California tide times vary along a long coastline...",
        "regions": [
            ("Southern California Tides", ["san-diego", "la-jolla", "oceanside", "laguna-beach", "newport-beach", "huntington-beach", "los-angeles", "santa-monica", "malibu"]),
            ("Northern California Tides", ["half-moon-bay", "san-francisco", "santa-cruz", "monterey"]),
        ],
    },
    "florida": {
        "featured": ["miami-beach", "clearwater-beach"],
        "intro": "Florida tide times differ between the Atlantic coast, Gulf Coast, and Keys...",
        "regions": [
            ("South Florida Tides", ["miami-beach", "fort-lauderdale"]),
            ("Gulf Coast Tides", ["clearwater-beach", "st-pete-beach", "tampa-bay", "naples", "sanibel-island", "destin", "panama-city-beach"]),
            ("Atlantic Coast & Keys Tides", ["key-west", "cocoa-beach", "daytona-beach"]),
        ],
    },
}
```

The helper must silently skip slugs that are not in the current catalog so PR A can land before PR B.

- [ ] **Step 4: Render featured, regional, and full-directory sections in `_state_page`**

Keep the canonical and breadcrumb behavior unchanged. Use existing `.directory-grid` and `.info-card location-card` markup so no new layout framework is required.

- [ ] **Step 5: Add natural state search copy**

California copy must contain readable sentences that naturally include the concepts `California tide times`, `California tides`, `California tide schedule`, `Southern California tide tables`, and `SoCal tides`. Florida copy should mirror the same intent without repeating phrases mechanically.

- [ ] **Step 6: Run state and SEO tests**

Run: `python src/test_state_landing.py && python src/test_directory_generation.py && python src/test_seo_generation.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/state_landing.py src/test_state_landing.py src/site_generator.py src/test_directory_generation.py
git commit -m "Strengthen California and Florida tide landing pages"
```

---

### Task 3: Strengthen the reusable Live location SEO template and answer-first layout

**Files:**
- Create: `src/test_location_seo_template.py`
- Modify: `src/locations.py`
- Modify: `src/generate_tides.py`
- Modify: `src/templates/tide-page.html`
- Modify: `src/test_seo_generation.py`

**Interfaces:**
- Consumes: `location["page_title"]`, `location["meta_description"]`, `render_tide_answer()`, `static_replacements()`.
- Produces: all Live NOAA pages render the answer-first block before Activity CTAs.

- [ ] **Step 1: Write failing template tests**

```python
from locations import LOCATIONS
from generate_tides import build_preview, render_location


def test_live_location_metadata_covers_core_tide_search_intent():
    location = LOCATIONS["san-diego"]
    assert "Tide Times" in location["page_title"]
    assert "High" in location["page_title"]
    assert "Low" in location["page_title"]
    desc = location["meta_description"]
    for phrase in ("high tide", "low tide", "tide chart", "7-day"):
        assert phrase.lower() in desc.lower()


def test_answer_first_block_is_not_huntington_only(tmp_path):
    location = LOCATIONS["san-diego"]
    data, now = build_preview(location)
    output = tmp_path / "index.html"
    render_location(location, data, output, mode="preview", now=now)
    html = output.read_text(encoding="utf-8")
    assert "NEXT TIDE" in html
    assert html.index("NEXT TIDE") < html.index("FISHING")
```

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_location_seo_template.py`
Expected: FAIL because San Diego does not currently get the Huntington-only `NEXT TIDE` block and metadata is generic.

- [ ] **Step 3: Update generated location metadata**

In `locations.py`, generate:

```python
"page_title": f'{name} Tide Times, High & Low Tides Today | CoastalNow',
"meta_description": (
    f"See today’s high and low tide times for {name}, {state}, with a tide chart, "
    "7-day tide schedule, and NOAA source details."
),
```

Keep descriptions human-readable and one sentence.

- [ ] **Step 4: Make `render_tide_answer` generic for Live pages**

Remove the `HUNTINGTON_SEO_PILOT` slug gate. The function should render whenever tide data is present; Preview fixtures may also render it so tests remain deterministic.

- [ ] **Step 5: Move the Activity primary CTA after core tide answer for all locations**

Change `static_replacements()` from the Huntington-only placement split to:

```python
"ACTIVITY_PRIMARY_PRE_TIDES": "",
"ACTIVITY_PRIMARY_POST_TIDES": activity_cta,
```

This preserves Fishing/Surfing links while keeping the tide answer first.

- [ ] **Step 6: Rename data-backed H2s in the tide template**

Use:

- `Today’s High and Low Tides`
- `Today’s Tide Chart`
- `7-Day Tide Schedule`

Do not add a keyword block or meta keywords.

- [ ] **Step 7: Add explicit state-directory route near local guide links**

Add a template replacement such as:

```html
<a class="place" href="../index.html">More {{STATE_NAME}} tide locations</a>
```

or generate `STATE_DIRECTORY_LINK` in `static_replacements()`. Keep nearby links next to it.

- [ ] **Step 8: Run regressions**

Run: `python src/test_location_seo_template.py && python src/test_seo_generation.py && python src/test_integrated_render.py && python src/test_san_diego_fixture.py && python src/test_tide_forecast_chronology.py`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/locations.py src/generate_tides.py src/templates/tide-page.html src/test_location_seo_template.py src/test_seo_generation.py
git commit -m "Strengthen tide location search intent"
```

---

### Task 4: Add a reusable existing-page SEO audit

**Files:**
- Create: `src/seo_audit.py`
- Create: `src/test_seo_audit.py`

**Interfaces:**
- Produces: `audit_location_page(public_root: Path, location: dict) -> dict[str, object]`
- Produces: `compare_location_pages(public_root: Path, slugs: list[str]) -> list[dict]`
- CLI: `python src/seo_audit.py --slugs san-diego cape-hatteras kill-devil-hills myrtle-beach oceanside huntington-beach miami-beach clearwater-beach`

- [ ] **Step 1: Write failing audit tests**

```python
def test_audit_reports_required_location_signals(tmp_path):
    page = tmp_path / "tides/california/example/index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<html><head><title>Example Tide Times</title></head><body><h1>Example</h1></body></html>", encoding="utf-8")
    result = audit_location_page(tmp_path, example_location)
    assert result["page_exists"] is True
    assert result["canonical"] is False
    assert result["robots"] is False
    assert result["breadcrumb_json_ld"] is False
```

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_seo_audit.py`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement exact checks**

The returned dict must include:

```python
{
    "slug": slug,
    "page_exists": bool,
    "title": str | None,
    "meta_description": str | None,
    "h1": str | None,
    "canonical": bool,
    "robots": bool,
    "breadcrumb_json_ld": bool,
    "state_link": bool,
    "nearby_link_count": int,
    "today_tide_events": bool,
    "seven_day_forecast": bool,
    "noaa_source": bool,
    "search_intent_terms": list[str],
}
```

Use only stdlib `re`, `html.parser`, and `json` if needed; do not add BeautifulSoup.

- [ ] **Step 4: Verify target pages**

Run the CLI against the four no-impression and four response pages listed above. The command must exit 0 when structural requirements are present and print a compact comparison table/JSON.

- [ ] **Step 5: Commit**

```bash
git add src/seo_audit.py src/test_seo_audit.py
git commit -m "Add repeatable tide page SEO audit"
```

---

### Task 5: Add Search Console snapshot and week-over-week comparison tooling

**Files:**
- Create: `src/tools/__init__.py`
- Create: `src/tools/gsc_report.py`
- Create: `src/test_gsc_report.py`

**Interfaces:**
- Produces: `parse_pages_csv(path: Path, snapshot_date: date) -> list[dict]`
- Produces: `classify_url(url: str) -> dict`
- Produces: `compare_snapshots(previous: list[dict], current: list[dict]) -> dict`
- CLI supports `snapshot` and `compare` subcommands.

- [ ] **Step 1: Write failing parser and delta tests**

```python
def test_pages_csv_maps_location_urls_and_metrics(tmp_path):
    csv_path = tmp_path / "Pages.csv"
    csv_path.write_text(
        "Top pages,Clicks,Impressions,CTR,Position\n"
        "https://coastalnowtides.com/tides/california/oceanside/,1,15,6.67%,9.87\n",
        encoding="utf-8",
    )
    rows = parse_pages_csv(csv_path, date(2026, 9, 13))
    assert rows[0]["page_type"] == "location"
    assert rows[0]["state_slug"] == "california"
    assert rows[0]["location_slug"] == "oceanside"
    assert rows[0]["impressions"] == 15


def test_compare_reports_growth_and_position_improvement():
    report = compare_snapshots(previous, current)
    row = report["pages"]["https://coastalnowtides.com/tides/california/oceanside/"]
    assert row["impressions_delta"] == 5
    assert row["position_delta"] == -2.0
```

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_gsc_report.py`
Expected: FAIL because the tooling does not exist.

- [ ] **Step 3: Implement flexible Search Console headers**

Accept at minimum:

- Page: `Top pages`, `Page`, `상위 페이지`, `페이지`
- Clicks: `Clicks`, `클릭수`, `클릭`
- Impressions: `Impressions`, `노출수`, `노출`
- CTR: `CTR`
- Position: `Position`, `Average position`, `게재순위`, `평균 게재순위`

Require `--date YYYY-MM-DD` for snapshots so dates are never guessed.

- [ ] **Step 4: Implement URL classification**

Rules:

```text
/tides/{state}/                     -> state
/tides/{state}/{location}/          -> location
/tides/{state}/{location}/fishing/  -> activity
/tides/{state}/{location}/surfing/  -> activity
otherwise                           -> other
```

- [ ] **Step 5: Persist normalized snapshot CSV**

Fields:

```text
snapshot_date,url,page_type,state_slug,location_slug,impressions,clicks,ctr,avg_position,indexed,first_impression_date
```

When no coverage/index file is supplied, leave `indexed` blank rather than inventing a value.

- [ ] **Step 6: Implement comparison output**

Aggregate state impressions/clicks and emit page deltas plus fastest-growing states. Preserve `first_impression_date` from the previous snapshot when already known; set it to current date only when prior impressions were zero/missing and current impressions are greater than zero.

- [ ] **Step 7: Keep query exports separate**

If a `Queries.csv` path is supplied, normalize it to a separate site-level query file. Never assign a query row to a location unless the input itself contains a page dimension.

- [ ] **Step 8: Run tests**

Run: `python src/test_gsc_report.py`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/tools/__init__.py src/tools/gsc_report.py src/test_gsc_report.py
git commit -m "Add Search Console snapshot comparison tool"
```

---

### Task 6: Wire permanent regressions into the Tide production workflow

**Files:**
- Modify: `.github/workflows/update-san-diego.yml`
- Modify: `src/test_activity_workflows.py` if workflow assertions require new test names.

**Interfaces:**
- Consumes all tests created in Tasks 1–5.
- Produces CI protection against future state-page, nearby-link, SEO-template, and audit regressions.

- [ ] **Step 1: Add a failing workflow assertion**

Extend the workflow regression to require these commands:

```text
python src/test_location_links.py
python src/test_state_landing.py
python src/test_location_seo_template.py
python src/test_seo_audit.py
python src/test_gsc_report.py
```

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_activity_workflows.py`
Expected: FAIL because the production Tide workflow does not yet run all new tests.

- [ ] **Step 3: Add the five tests to `update-san-diego.yml` offline regression block**

Do not change scheduling, concurrency group, NOAA fetch behavior, or site-writer rebase logic.

- [ ] **Step 4: Run the focused full suite**

Run:

```bash
python src/test_location_links.py
python src/test_state_landing.py
python src/test_location_seo_template.py
python src/test_seo_audit.py
python src/test_gsc_report.py
python src/test_directory_generation.py
python src/test_seo_generation.py
python src/test_integrated_render.py
python src/test_san_diego_fixture.py
python src/test_tide_forecast_chronology.py
python src/test_activity_workflows.py
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/update-san-diego.yml src/test_activity_workflows.py
git commit -m "Protect CoastalNow SEO foundation regressions"
```

---

### Task 7: Rebuild static outputs and verify representative Production HTML before PR

**Files:**
- Generated: `public/index.html`
- Generated: `public/tides/california/index.html`
- Generated: `public/tides/florida/index.html`
- Generated: representative location pages under `public/tides/**`
- Generated: `public/sitemap.xml`, `public/robots.txt`

**Interfaces:**
- Consumes the completed PR A source changes.
- Produces reviewable static output and evidence that existing URLs remain stable.

- [ ] **Step 1: Generate/refresh Tide pages and site artifacts**

In a network-capable environment run the normal production commands used by `update-san-diego.yml`:

```bash
python src/promote_location.py --validate-config
python src/generate_tides.py
python src/build_site.py
```

- [ ] **Step 2: Run the SEO audit target comparison**

```bash
python src/seo_audit.py --slugs san-diego cape-hatteras kill-devil-hills myrtle-beach oceanside huntington-beach miami-beach clearwater-beach
```

Expected: all target pages exist and satisfy canonical/robots/H1/state-link/nearby/NOAA/forecast checks.

- [ ] **Step 3: Inspect representative generated HTML**

Verify in generated files:

- California has Featured + Southern + Northern + full directory.
- Florida has Featured + South Florida + Gulf + Atlantic/Keys + full directory.
- San Diego and Oceanside render `NEXT TIDE` before Fishing/Surfing CTA cards.
- Nearby links are geographically sensible and count 3–4 where inventory allows.
- Existing canonical URLs are unchanged.

- [ ] **Step 4: Verify sitemap/robots remain policy-correct**

Run: `python src/test_seo_generation.py`
Expected: PASS and generated files exactly match `build_sitemap()` / `build_robots_txt()`.

- [ ] **Step 5: Open PR A**

PR title: `Strengthen CoastalNow tide SEO foundation`

PR body must summarize GSC motivation, no URL changes, California/Florida landing changes, answer-first expansion, nearby links, audit tooling, GSC snapshot tooling, and test evidence.
