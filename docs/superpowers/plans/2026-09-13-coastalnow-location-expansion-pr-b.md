# CoastalNow Controlled Location Expansion PR B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add exactly 12 genuinely new CoastalNow tide locations—six Southern California and six Florida—only after NOAA compatibility validation, then verify directory, sitemap, canonical, indexability, and generated output end to end.

**Architecture:** Extend the existing `locations.json` catalog first, then validate/promote each candidate through the existing `live_noaa.json` and NOAA compatibility path. Keep Live/Preview gating, static rendering, sitemap generation, canonical policy, and Activity geography validation unchanged; PR B supplies new data and permanent expansion-specific regression coverage rather than creating a new publishing system.

**Tech Stack:** Python 3.12 standard library, NOAA CO-OPS prediction API, static HTML/CSS, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-coastalnow-gsc-cluster-expansion-design.md`

## Global Constraints

- Add only genuinely new location URLs; do not duplicate existing California or Florida inventory.
- Target batch size is exactly 12 unless a candidate fails NOAA validation and is replaced by a documented same-cluster substitute.
- Southern California candidates: Long Beach, Ventura, Santa Barbara, Redondo Beach, Dana Point, Seal Beach.
- Florida candidates: Key Biscayne, West Palm Beach, Fort Myers Beach, Pompano Beach, Marco Island, Sarasota.
- Each new catalog entry requires explicit latitude/longitude and Activity shore/marine points.
- A page is indexable only after its slug exists in `live_noaa.json` and NOAA validation passes.
- Nearby NOAA coverage must use `coverage_mode="nearby-noaa"` plus station name and `coverage_distance_miles`.
- Existing URL pattern remains `/tides/{state_slug}/{location_slug}/`.
- NOAA remains the tide source.
- Do not change Fishing/Surfing scoring policy as part of this PR.

---

## File Structure

- Modify: `src/data/locations.json` — add the 12 new catalog locations with explicit coordinates and Activity geography.
- Modify: `src/data/live_noaa.json` — add only candidates that pass network validation.
- Create: `src/test_gsc_expansion_batch.py` — exact batch, duplicate-slug, geography, status, directory, sitemap, canonical regressions.
- Modify: `src/test_location_promotion.py` — add promotion validation assertions where needed.
- Modify: `.github/workflows/update-san-diego.yml` — run the expansion regression permanently.
- Generated: `public/data/{slug}.json` — NOAA Tide data for each promoted location.
- Generated: `public/tides/{state}/{slug}/index.html` — new public tide pages.
- Generated: `public/tides/california/index.html`, `public/tides/florida/index.html`, `public/index.html`, `public/sitemap.xml`.

---

### Task 1: Add the 12 new locations to the catalog as non-promoted entries

**Files:**
- Modify: `src/data/locations.json`
- Create: `src/test_gsc_expansion_batch.py`

**Interfaces:**
- Consumes: existing `locations.py` loader and `validate_activity_geography()`.
- Produces: 12 new slugs available in `LOCATIONS` before Live promotion.

- [ ] **Step 1: Write the failing exact-batch test**

```python
EXPECTED_NEW = {
    "long-beach",
    "ventura",
    "santa-barbara",
    "redondo-beach",
    "dana-point",
    "seal-beach",
    "key-biscayne",
    "west-palm-beach",
    "fort-myers-beach",
    "pompano-beach",
    "marco-island",
    "sarasota",
}


def test_gsc_expansion_batch_exists_in_catalog():
    assert EXPECTED_NEW <= set(LOCATIONS)
```

- [ ] **Step 2: Add a failing coordinate/geography test**

```python
def test_gsc_expansion_locations_have_explicit_geography():
    for slug in EXPECTED_NEW:
        item = LOCATIONS[slug]
        assert isinstance(item.get("latitude"), (int, float)), slug
        assert isinstance(item.get("longitude"), (int, float)), slug
        validate_activity_geography(item)
```

- [ ] **Step 3: Run and verify RED**

Run: `python src/test_gsc_expansion_batch.py`
Expected: FAIL because the 12 slugs are not yet in `locations.json`.

- [ ] **Step 4: Add the six Southern California catalog entries**

Each entry must include:

```json
{
  "state": "California",
  "state_code": "CA",
  "state_slug": "california",
  "name": "Long Beach",
  "slug": "long-beach",
  "priority": "B",
  "latitude": 0.0,
  "longitude": 0.0,
  "timezone": "America/Los_Angeles",
  "datum": "MLLW",
  "units": "english",
  "source": "NOAA/NOS/CO-OPS",
  "activity": {
    "shore_point": {"latitude": 0.0, "longitude": 0.0},
    "marine_point": {"latitude": 0.0, "longitude": 0.0},
    "coast_bearing": 0
  }
}
```

Replace every `0.0` with verified real coordinates before committing. Do not infer coordinates from a NOAA station if the station is not local to the named place; location coordinates represent the place/activity geography, not the tide station.

- [ ] **Step 5: Add the six Florida catalog entries**

Use `America/New_York` for Atlantic/South Florida candidates and the appropriate local timezone for Gulf candidates. If Sarasota or Fort Myers Beach require Eastern time, state it explicitly rather than relying on the default.

- [ ] **Step 6: Run catalog/geography tests**

Run: `python src/test_gsc_expansion_batch.py && python src/test_activity_geography.py && python src/test_location_promotion.py`
Expected: catalog/geography tests PASS while Live-status assertions are not added yet.

- [ ] **Step 7: Commit catalog additions**

```bash
git add src/data/locations.json src/test_gsc_expansion_batch.py
git commit -m "Add controlled California and Florida expansion catalog"
```

---

### Task 2: Validate NOAA stations for every candidate before promotion

**Files:**
- Modify: `src/data/live_noaa.json`
- Modify: `src/test_gsc_expansion_batch.py`
- Modify: `src/test_location_promotion.py` if additional coverage-mode cases are needed.

**Interfaces:**
- Consumes: `validate_noaa_compatibility(location, station_id, prediction_mode)` from `src/promote_location.py`.
- Produces: one validated Live NOAA config entry per accepted candidate.

- [ ] **Step 1: Prepare a validation table outside production config**

For each slug record:

```text
slug
candidate station_id
station_name
prediction_mode (harmonic | hilo-derived)
coverage_mode (local | nearby-noaa)
coverage_distance_miles if nearby
validation result
```

Do not edit `live_noaa.json` until network validation succeeds.

- [ ] **Step 2: Validate high/low and interval support using the existing production validator**

Run a short Python command per candidate or a temporary validation script that calls:

```python
validate_noaa_compatibility(
    LOCATIONS[slug],
    station_id,
    prediction_mode,
)
```

Expected:

- Both `H` and `L` predictions exist.
- Harmonic mode has at least 70 valid 30-minute points across the validator window.
- `hilo-derived` is used only for an official NOAA subordinate station that lacks sufficient interval data.

- [ ] **Step 3: Replace failures within the same cluster**

If a candidate cannot be represented honestly by an available NOAA source, do not ship it as Live. Choose a substitute from the same cluster, add it to `locations.json`, remove the failed candidate from the exact-batch set, and document the replacement in the PR body and test constant.

- [ ] **Step 4: Add validated configs to `live_noaa.json`**

Example local config:

```json
"long-beach": {
  "station_id": "9410680",
  "station_name": "Long Beach, Inner Harbor, CA",
  "prediction_mode": "harmonic"
}
```

Example nearby config:

```json
"example-beach": {
  "station_id": "1234567",
  "station_name": "Nearby NOAA Station",
  "prediction_mode": "harmonic",
  "coverage_mode": "nearby-noaa",
  "coverage_distance_miles": 8.5
}
```

Use only station IDs/names verified during Step 2.

- [ ] **Step 5: Add Live-status regression**

```python
def test_gsc_expansion_batch_is_live_after_validation():
    for slug in EXPECTED_NEW:
        assert LOCATIONS[slug]["status"] == "Live NOAA", slug
        assert LOCATIONS[slug]["station"], slug
```

- [ ] **Step 6: Run config validation**

Run:

```bash
python src/promote_location.py --validate-config
python src/test_location_promotion.py
python src/test_gsc_expansion_batch.py
```

Expected: PASS.

- [ ] **Step 7: Commit validated promotion config**

```bash
git add src/data/live_noaa.json src/test_gsc_expansion_batch.py src/test_location_promotion.py
git commit -m "Promote validated expansion locations to Live NOAA"
```

---

### Task 3: Verify state landing metadata and nearby clusters include the new locations

**Files:**
- Modify: `src/state_landing.py`
- Modify: `src/test_state_landing.py`
- Modify: `src/test_location_links.py`

**Interfaces:**
- Consumes: PR A `STATE_LANDING` and geographic nearby-link helpers.
- Produces: the new locations appear under correct explicit California/Florida regions and naturally enter nearest-location links.

- [ ] **Step 1: Write failing region-membership tests**

```python
def test_southern_california_region_contains_expansion_locations():
    slugs = set(region_slugs("california", "Southern California Tides"))
    assert {"long-beach", "ventura", "santa-barbara", "redondo-beach", "dana-point", "seal-beach"} <= slugs


def test_florida_regions_contain_expansion_locations():
    all_region_slugs = set().union(*[set(items) for _, items in STATE_LANDING["florida"]["regions"]])
    assert {"key-biscayne", "west-palm-beach", "fort-myers-beach", "pompano-beach", "marco-island", "sarasota"} <= all_region_slugs
```

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_state_landing.py`
Expected: FAIL because PR A region lists intentionally predate these new slugs.

- [ ] **Step 3: Add explicit region memberships**

California:

- Long Beach, Redondo Beach, Dana Point, Seal Beach → Southern California.
- Ventura, Santa Barbara → Southern California for this CoastalNow cluster release; do not auto-reclassify from latitude.

Florida recommended grouping:

- Key Biscayne, West Palm Beach, Pompano Beach → South Florida / Atlantic Coast as defined in the State config.
- Fort Myers Beach, Marco Island, Sarasota → Gulf Coast.

Avoid duplicate cards inside one state page unless a deliberate Featured block references the same location separately.

- [ ] **Step 4: Verify nearby links become geographically sensible**

Add assertions such as:

```python
def test_los_angeles_nearby_cluster_gains_long_beach_and_redondo_beach():
    slugs = [item["slug"] for item in LOCATIONS["los-angeles"]["nearby"]]
    assert "long-beach" in slugs or "redondo-beach" in slugs
```

Use distance-based expectations only where stable; do not over-specify all four slots if several locations have very similar distances.

- [ ] **Step 5: Run tests and commit**

Run: `python src/test_state_landing.py && python src/test_location_links.py`
Expected: PASS.

```bash
git add src/state_landing.py src/test_state_landing.py src/test_location_links.py
git commit -m "Add expansion locations to coastal state clusters"
```

---

### Task 4: Prove new URLs, canonical policy, directories, and sitemap generation before network rendering

**Files:**
- Modify: `src/test_gsc_expansion_batch.py`
- Modify: `src/test_directory_generation.py`
- Modify: `src/test_seo_generation.py`

**Interfaces:**
- Consumes: Live `LOCATIONS`, `build_directory_pages()`, `build_sitemap()`, `canonical_url()`.
- Produces: static-site generation guarantees for all new pages.

- [ ] **Step 1: Add failing directory/sitemap assertions**

```python
def test_expansion_batch_appears_in_state_and_home_directories():
    pages = build_directory_pages()
    home = pages["index.html"]
    california = pages["tides/california/index.html"]
    florida = pages["tides/florida/index.html"]
    for slug in EXPECTED_NEW:
        path = LOCATIONS[slug]["page_path"]
        assert path in home
        target = california if LOCATIONS[slug]["state_slug"] == "california" else florida
        assert f'{slug}/index.html' in target


def test_expansion_batch_is_in_sitemap_with_self_canonical_policy():
    xml = build_sitemap(LOCATIONS)
    for slug in EXPECTED_NEW:
        assert canonical_url(LOCATIONS[slug]["page_path"]) in xml
        assert robots_directive(LOCATIONS[slug]) == "index,follow"
```

- [ ] **Step 2: Run and verify behavior**

Run: `python src/test_gsc_expansion_batch.py`
Expected: PASS after Tasks 1–3; if not, fix the data/config rather than special-casing sitemap generation.

- [ ] **Step 3: Add exact batch-size protection**

Assert that all expected new slugs are present and no accidental extras from the branch are introduced. Compare branch catalog to a recorded pre-expansion count or explicit new-slug set rather than hard-coding total global location count forever.

- [ ] **Step 4: Run SEO/directory suites**

Run:

```bash
python src/test_gsc_expansion_batch.py
python src/test_directory_generation.py
python src/test_seo_generation.py
python src/test_activity_geography.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/test_gsc_expansion_batch.py src/test_directory_generation.py src/test_seo_generation.py
git commit -m "Protect controlled location expansion outputs"
```

---

### Task 5: Generate all 12 Live pages with real NOAA data and verify Production rendering

**Files:**
- Generated: `public/data/{slug}.json`
- Generated: `public/tides/{state}/{slug}/index.html`
- Generated: California/Florida state pages, home directory, sitemap, robots.

**Interfaces:**
- Consumes: validated catalog/live config and the normal production generation pipeline.
- Produces: live generated pages with NOAA timestamps and seven-day forecasts.

- [ ] **Step 1: Run full Live NOAA generation**

Run:

```bash
python src/promote_location.py --validate-config
python src/generate_tides.py
python src/build_site.py
```

Expected: exit 0, or explicit stale-cache handling only for already-established locations. Every new slug must produce a fresh data file during this verification run; a new location must not rely on stale cache because none should exist before promotion.

- [ ] **Step 2: Validate generated files programmatically**

Add or use test code that checks for every new slug:

```python
page = PUBLIC / LOCATIONS[slug]["page_path"]
data = PUBLIC / LOCATIONS[slug]["data_path"]
assert page.exists()
assert data.exists()
html = page.read_text(encoding="utf-8")
assert "NEXT TIDE" in html
assert "Today’s Tide Chart" in html
assert "7-Day Tide Schedule" in html
assert "NOAA" in html
assert canonical_url(LOCATIONS[slug]["page_path"]) in html
```

- [ ] **Step 3: Inspect nearby-station disclosure where applicable**

For each config using `nearby-noaa`, verify the generated page includes station name and distance disclosure. A nearby station must never look like a local station.

- [ ] **Step 4: Run full focused regressions**

Run:

```bash
python src/test_gsc_expansion_batch.py
python src/test_location_promotion.py
python src/test_generate_tides.py
python src/test_directory_generation.py
python src/test_seo_generation.py
python src/test_location_links.py
python src/test_state_landing.py
python src/test_location_seo_template.py
python src/test_integrated_render.py
python src/test_san_diego_fixture.py
python src/test_activity_network_validation.py
```

Expected: all PASS.

- [ ] **Step 5: Commit generated source-controlled output if that matches current repository policy**

Use the existing Tide writer behavior and stage only the same generated paths it normally stages. Do not invent a second output policy.

---

### Task 6: Add permanent expansion regression to the production workflow and deploy

**Files:**
- Modify: `.github/workflows/update-san-diego.yml`
- Modify: `src/test_activity_workflows.py` if needed.

**Interfaces:**
- Consumes: `src/test_gsc_expansion_batch.py`.
- Produces: CI protection for the 12-location release.

- [ ] **Step 1: Add failing workflow assertion**

Require `python src/test_gsc_expansion_batch.py` in the Tide refresh offline regression step.

- [ ] **Step 2: Run and verify RED**

Run: `python src/test_activity_workflows.py`
Expected: FAIL until the workflow includes the new regression.

- [ ] **Step 3: Add the expansion test to `update-san-diego.yml`**

Do not change cron, shared concurrency, fetch/rebase/push behavior, or NOAA error reporting.

- [ ] **Step 4: Run the final full suite**

Run the PR A focused suite plus:

```bash
python src/test_gsc_expansion_batch.py
python src/test_location_promotion.py
python src/test_activity_network_validation.py
python src/test_activity_workflows.py
```

Expected: all PASS.

- [ ] **Step 5: Open PR B**

PR title: `Add controlled California and Florida tide expansion`

PR body must include:

- final 12 slugs;
- any substitutions and why;
- NOAA station ID/name per slug;
- local vs nearby coverage disclosure;
- validation results;
- sitemap/directory/canonical evidence;
- generated-page test evidence.

- [ ] **Step 6: Merge only after fresh verification**

Use squash merge after the final branch test run and mergeability check.

- [ ] **Step 7: Observe the Production Tide workflow**

Confirm the merge-triggered `Update live NOAA tide data` run completes successfully through NOAA generation, site build, offline regressions, generated-output commit, and final push.

- [ ] **Step 8: Verify public source on representative new pages**

At minimum inspect:

- Long Beach
- Santa Barbara
- Key Biscayne
- Fort Myers Beach

Confirm title/meta/H1, `NEXT TIDE`, tide chart, 7-day schedule, nearby links, state link, NOAA attribution, canonical, and state-directory inclusion.

---

### Task 7: Record the post-expansion Search Console baseline for future cluster comparison

**Files:**
- Output only: normalized snapshot file outside generated site content or under a designated analytics folder if the project chooses to version it.

**Interfaces:**
- Consumes: PR A `src/tools/gsc_report.py`.
- Produces: baseline against which California, Florida, and North Carolina can be compared after impressions accrue.

- [ ] **Step 1: Normalize the current/pre-expansion Pages export**

Example:

```bash
python -m src.tools.gsc_report snapshot \
  --pages path/to/Pages.csv \
  --date 2026-09-13 \
  --output reports/gsc/2026-09-13-pages.csv
```

- [ ] **Step 2: Preserve the baseline date and first-impression values**

Do not mark new locations as indexed or impression-positive until Search Console actually reports those facts.

- [ ] **Step 3: After the next export, generate a comparison**

```bash
python -m src.tools.gsc_report compare \
  --previous reports/gsc/2026-09-13-pages.csv \
  --current reports/gsc/YYYY-MM-DD-pages.csv \
  --output reports/gsc/YYYY-MM-DD-vs-2026-09-13.csv
```

- [ ] **Step 4: Choose the next expansion cluster from evidence**

Compare aggregate impressions/clicks and location-level first impressions for California, Florida, and North Carolina. Do not start the next large batch until this comparison is available.
