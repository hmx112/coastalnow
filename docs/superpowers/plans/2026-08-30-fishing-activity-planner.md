# CoastalNow Fishing Activity Planner — Implementation Plan

> **Execution:** implement task-by-task with TDD on an isolated feature branch. Do not change any existing `/tides/<state>/<location>/` URL. Do not use `[skip ci]` in any commit message.

**Goal:** Ship Phase 1 Fishing as a rules-based, safety-first activity layer with a national `/fishing/` discovery hub and automatically generated `/tides/<state>/<location>/fishing/` pages for every catalog location, while creating reusable foundations for Surfing, Beach, and Swimming.

**Architecture:** Keep `src/data/locations.json` as the single geography catalog. Add a registry-driven Activity subsystem that collects one common Condition Snapshot per location, applies a generic scoring/safety framework plus Fishing-specific rules, writes deterministic activity JSON, renders location/hub pages, and extends SEO/workflows without changing existing Tide behavior. New locations automatically flow through all enabled activities.

**Tech stack:** Python 3.12 standard library, NOAA CO-OPS, NWS API, static HTML/CSS, GitHub Actions, Cloudflare Pages.

**Spec:** `docs/superpowers/specs/2026-08-30-fishing-activity-planner.md`

## Global constraints

- Existing 51 location URLs remain byte-for-byte path compatible; no moves, redirects, or alternate geography hierarchy.
- Fishing URL pattern is `/tides/<state>/<location>/fishing/`; root hub is `/fishing/`.
- `locations.json` remains the only location list. No Fishing-specific list.
- Safety-critical missing data must fail conservatively.
- Scoring and explanations are deterministic; no AI API.
- Phase 1 Fishing means shore / pier / nearshore recreational fishing, not offshore/boat fishing.
- Third-party marine APIs are excluded unless commercial-use and redistribution rights are explicitly verified.
- Generated activity pages may exist as `noindex,follow` when data is Limited/Unavailable.
- All public counts must derive from the catalog/eligibility, never hard-code `51`.

---

## Task 1 — Make the location catalog Activity-ready and remove fixed-size assumptions

**Files:**
- Modify: `src/data/locations.json`
- Modify: `src/locations.py`
- Modify: `src/site_generator.py`
- Modify: `src/test_directory_generation.py`
- Create: `src/test_activity_geography.py`

**Interfaces:**
- Every catalog item exposes `activity.shore_point`, `activity.marine_point`, and optional `activity.coast_bearing`.
- `LOCATIONS[slug]["activity"]` is preserved by `locations.py`.
- Homepage location count is derived from `len(LOCATIONS)`.

- [ ] **Step 1: Write failing tests** asserting that every catalog location has finite shore/marine latitude/longitude within legal geographic bounds, `coast_bearing` is absent/null or `0 <= bearing < 360`, Activity coordinates are independent of Nearby NOAA station metadata, and homepage search copy uses `len(LOCATIONS)` rather than literal `51`.
- [ ] **Step 2: Run the tests and verify RED** because most current locations have no Activity geography and homepage copy is fixed at 51.
- [ ] **Step 3: Curate Activity geography for all current locations.** Use representative public shoreline/pier points, not Nearby NOAA station coordinates. Store explicit shore and nearshore points. For exposed ocean beaches, store a seaward-facing bearing where it can be established confidently; omit direction rather than guess.
- [ ] **Step 4: Add validation helpers** in `locations.py` or a focused Activity geography helper so malformed coordinates fail at load/build time with the location slug in the error.
- [ ] **Step 5: Replace fixed UI counts** in `site_generator.py` with catalog-derived counts and rename the old test that assumes exactly 51 locations so it tests uniqueness/non-empty inventory instead of permanent size.
- [ ] **Step 6: Run `python src/test_activity_geography.py` and `python src/test_directory_generation.py`** until green.
- [ ] **Step 7: Commit** catalog geography + dynamic counts.

## Task 2 — Add Activity Registry, paths, and automatic-expansion invariants

**Files:**
- Create: `src/activities/__init__.py`
- Create: `src/activities/registry.py`
- Create: `src/activities/paths.py`
- Create: `src/test_activity_registry.py`

**Interfaces:**
- `enabled_activities()` returns registry entries with `slug`, `label`, `scorer_version`, and requirements.
- `activity_page_path(location, activity_slug)` returns `tides/<state>/<location>/<activity>/index.html`.
- `activity_data_path(location, activity_slug)` returns `data/activities/<activity>/<location>.json`.
- `activity_hub_path(activity_slug)` returns `<activity>/index.html`.

- [ ] **Step 1: Write failing tests** for Fishing registry enablement, exact Fishing paths, absence of a separate geography list, and a synthetic new location automatically producing paths for every enabled Activity.
- [ ] **Step 2: Add a test-only second Activity registry fixture** and prove that the same synthetic location receives both Activity paths without changing location data.
- [ ] **Step 3: Run tests and verify RED** because the Activity package does not exist.
- [ ] **Step 4: Implement the minimal registry/path helpers** with Fishing enabled and future activities represented only as disabled registry metadata if useful; do not implement their scorers.
- [ ] **Step 5: Run `python src/test_activity_registry.py`** and verify green.
- [ ] **Step 6: Commit** the registry/path foundation.

## Task 3 — Define provider-independent Condition Snapshot and cache/freshness rules

**Files:**
- Create: `src/activities/conditions/__init__.py`
- Create: `src/activities/conditions/snapshot.py`
- Create: `src/activities/conditions/validation.py`
- Create: `src/test_activity_conditions.py`
- Create fixtures under: `src/fixtures/activity/`

**Interfaces:**
- Snapshot schema has location slug, timezone, generated timestamps, provider provenance, hourly local-time values, alerts state, and explicit missing fields.
- Freshness policy constants: alerts normal-state max age 2h; full forecast High/Medium max age 6h.
- Unknown values remain `None`/missing, never substituted with optimistic numbers.

- [ ] **Step 1: Write fixture-driven failing tests** for schema validation, source timestamps/provenance, legal unit-normalized ranges, local-time hourly ordering, stale alert state, stale forecast state, and the rule that alert failure is `Unavailable` rather than an empty alert list.
- [ ] **Step 2: Run and verify RED** because snapshot/validation modules do not exist.
- [ ] **Step 3: Implement dataless normalization/validation code first.** Keep provider HTTP outside this module.
- [ ] **Step 4: Implement freshness classification** with explicit `fresh / stale / unavailable` results and boundary tests at exactly 2h and 6h.
- [ ] **Step 5: Run `python src/test_activity_conditions.py`** until green.
- [ ] **Step 6: Commit** snapshot contracts and fixtures.

## Task 4 — Implement official NWS/NOAA condition providers and astronomy

**Files:**
- Create: `src/activities/conditions/providers/__init__.py`
- Create: `src/activities/conditions/providers/nws.py`
- Create: `src/activities/conditions/providers/noaa.py`
- Create: `src/activities/conditions/astronomy.py`
- Create: `src/activities/conditions/collect.py`
- Extend: `src/test_activity_conditions.py`
- Add fixtures under: `src/fixtures/activity/`

**Provider behavior:**
- NWS point metadata from `api.weather.gov/points/{lat},{lon}`.
- NWS hourly/grid data normalized to mph, °F, feet, seconds, and percentages as appropriate.
- NWS active alerts queried for the relevant shore/marine geography; preserve event/severity/effective/expiry/source text needed by Safety Gate.
- Marine structured fields such as wave height/period are used only when actually returned; absence stays unknown.
- NOAA optional water temperature is queried only where supported; failure does not fabricate a value.
- Tide input is loaded from existing verified `public/data/<slug>.json` cache rather than duplicating Tide fetch logic.
- Solar/lunar values are deterministic local calculations and covered by fixtures.

- [ ] **Step 1: Add failing parser tests** using saved NWS/NOAA fixtures for unit conversion, hourly time alignment, missing marine fields, alert parsing, and optional water-temperature failure.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement HTTP request wrappers** with descriptive User-Agent, retries/backoff, timeouts, and clear provider exceptions. Do not let parser code make network calls in unit tests.
- [ ] **Step 4: Implement NWS point/hourly/grid/alerts parsers** and request deduplication cache keyed by URL/zone/grid where safe.
- [ ] **Step 5: Implement NOAA optional water-temperature adapter** and existing Tide-cache loader.
- [ ] **Step 6: Implement tested solar/lunar calculation helpers** sufficient for dawn/dusk and the low-weight moon timing factor.
- [ ] **Step 7: Implement `collect_location_conditions(location)`** that merges sources into the common snapshot and records per-field provenance/freshness.
- [ ] **Step 8: Run provider/condition tests** until green.
- [ ] **Step 9: Commit** provider collection code.

## Task 5 — Implement generic scoring engine and Safety Gate before Fishing rules

**Files:**
- Create: `src/activities/scoring/__init__.py`
- Create: `src/activities/scoring/engine.py`
- Create: `src/activities/scoring/safety.py`
- Create: `src/test_activity_scoring_engine.py`
- Create: `src/test_activity_safety.py`

**Interfaces:**
- Generic weighted score consumes named component scores + configured weights; weights are never redistributed for missing inputs.
- Optional unknown component is fixed at 50.
- Safety result has penalties, cap, hard-stop flag, reason codes, and precedence.
- Best 3-hour window uses `0.70 * mean + 0.30 * minimum` and excludes unsafe/unavailable hours.

- [ ] **Step 1: Write failing tests** for weighted arithmetic, neutral unknown = 50, no weight redistribution, rating boundaries, 3-hour window formula, local Today/Tomorrow grouping, and exclusion of unsafe hours.
- [ ] **Step 2: Write failing Safety tests** for strictest-cap wins, cumulative penalties, hard-stop precedence, and public state never showing a normal recommendation when hard-stopped.
- [ ] **Step 3: Verify RED.**
- [ ] **Step 4: Implement generic engine primitives** with no Fishing thresholds in `engine.py`.
- [ ] **Step 5: Implement generic Safety Gate primitives** in `safety.py`: `SafetyDecision`, penalty accumulation, minimum cap, hard-stop override.
- [ ] **Step 6: Run both test files** until green.
- [ ] **Step 7: Commit** generic scoring/safety framework.

## Task 6 — Implement Fishing-specific quality, hazard map, confidence, and explanations

**Files:**
- Create: `src/activities/scoring/fishing.py`
- Create: `src/activities/explanations.py`
- Create: `src/test_fishing_scoring.py`
- Create: `src/test_fishing_safety.py`

**Fishing configuration:**
- Tide 30%, Wind 20%, Wave 15%, Weather 15%, Time-of-day 10%, Moon/Solunar 5%, Water temp 5%.
- Quality and Safety thresholds are exactly those in the approved spec, represented as named configuration constants/tables.
- Safety event mapping is explicit and versioned.

- [ ] **Step 1: Write failing boundary tests** for every Wind/Wave/Weather quality band, Tide phase midpoint vs turning point, time-of-day behavior, water-temp/solunar optional treatment, and rating boundaries.
- [ ] **Step 2: Write failing Safety tests** for every initial official hard-stop event, wind safety boundaries, wave exposure boundaries, strongest active cap, and alert/marine missing-data confidence degradation.
- [ ] **Step 3: Include tests proving a raw 90+ quality score becomes `NOT RECOMMENDED` under a hard stop** and cannot appear in national ranking.
- [ ] **Step 4: Verify RED.**
- [ ] **Step 5: Implement Fishing component functions and scorer** on top of the generic engine.
- [ ] **Step 6: Implement Fishing hazard mapping** on top of generic Safety Gate; no generic “all advisories -N” fallback.
- [ ] **Step 7: Implement deterministic reason codes and approved sentence fragments**; output explains favorable and limiting factors without claiming safety or catch guarantees.
- [ ] **Step 8: Implement confidence classification** High/Medium/Limited/Unavailable from freshness/completeness.
- [ ] **Step 9: Run Fishing scoring/safety tests** until green.
- [ ] **Step 10: Commit** Fishing rules.

## Task 7 — Build Activity data pipeline and fail-safe refresh behavior

**Files:**
- Create: `src/generate_activities.py`
- Create: `src/test_activity_generation.py`
- Modify: `src/build_site.py`

**Interfaces:**
- Full mode: collect common snapshot → score all enabled activities → atomically write condition/activity JSON.
- Alert-only mode: refresh alert state, recompute affected Safety Gate/results/pages without re-fetching all forecast data.
- Cache fallback preserves provenance and downgrades confidence; stale beyond policy cannot remain High/Medium.

- [ ] **Step 1: Write failing generation tests** with temporary directories for all catalog locations, synthetic new location, atomic writes, stale cache fallback, provider failure, and alert-only refresh.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement command-line targets** (`--location`, `--activity`, `--alerts-only`, fixture/offline test mode) without hard-coded location count.
- [ ] **Step 4: Implement atomic condition/activity JSON writes** under `public/data/conditions/` and `public/data/activities/fishing/`.
- [ ] **Step 5: Ensure one common snapshot is reused by all enabled scorers.** Add a test with two fake enabled activities proving provider collection runs once per location.
- [ ] **Step 6: Integrate Activity output discovery into `build_site.py`** without changing Tide generation semantics.
- [ ] **Step 7: Run generation tests** until green.
- [ ] **Step 8: Commit** Activity pipeline.

## Task 8 — Render Fishing location pages and national hub

**Files:**
- Create: `src/templates/activity-location.html`
- Create: `src/templates/activity-hub.html`
- Create: `src/activities/rendering/__init__.py`
- Create: `src/activities/rendering/location_page.py`
- Create: `src/activities/rendering/hub_page.py`
- Create: `src/activities/rendering/links.py`
- Create: `src/test_activity_rendering.py`
- Modify: `public/assets/site.css`

**Required location page content:** safety strip, score/rating, best 3-hour time, confidence, hourly timeline, factor breakdown, Today/Tomorrow, compact Tide summary, Wind/Wave/Weather, reasons, Tide parent link, Fishing hub link, disclaimers.

**Required hub content:** Today/Tomorrow, Top Locations, #1 explanation, rating groups, Not Recommended group, Limited/Unavailable group, methodology/safety note.

- [ ] **Step 1: Write failing renderer tests** using fixed High, Limited, Unavailable, and hard-stop fixtures. Assert exact URL hierarchy, no unresolved template tokens, hard-stop presentation, ranking sort order, and exclusion of Limited/Unavailable from numeric ranking.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement shared visual shell** consistent with current CoastalNow branding, reusing the canonical three-wave logo but not duplicating Tide-specific tables.
- [ ] **Step 4: Implement location renderer** with deterministic content and clear “planning metric, not safety guarantee” language.
- [ ] **Step 5: Implement national hub renderer** with stable tie-break (`score desc`, then location name) and Today/Tomorrow data attributes or static sections that work without external JS dependencies.
- [ ] **Step 6: Add responsive CSS** to existing site stylesheet; avoid redesigning unrelated Tide UI.
- [ ] **Step 7: Run renderer tests** until green.
- [ ] **Step 8: Commit** renderers/templates/styles.

## Task 9 — Add bidirectional navigation, Activity discovery, and SEO/indexability

**Files:**
- Modify: `src/site_generator.py`
- Modify: `src/templates/tide-page.html`
- Modify: `src/generate_tides.py` only for a generic Activity-links replacement hook, not Fishing scoring
- Modify: `src/seo.py`
- Modify: `src/build_site.py`
- Modify: `src/test_directory_generation.py`
- Modify: `src/test_seo_generation.py`
- Extend: `src/test_activity_rendering.py`

**Interfaces:**
- Homepage `Explore by activity` generated from Activity Registry.
- Parent Tide pages render an Activities section from current Activity outputs.
- Fishing pages link back to parent Tide and `/fishing/`.
- `/fishing/` is always indexable when generated.
- Location Fishing is `index,follow` only for real Today High/Medium confidence; Limited/Unavailable is `noindex,follow`.
- Sitemap keeps all existing URLs and adds only indexable Activity URLs.

- [ ] **Step 1: Write failing integration tests** for homepage Activity card, parent↔Fishing links, canonical, four-level breadcrumb, robots directive, sitemap inclusion/exclusion, and unchanged existing Tide paths.
- [ ] **Step 2: Add a regression snapshot/set of the current 51 `page_path` values** and assert the Activity change does not alter them.
- [ ] **Step 3: Verify RED.**
- [ ] **Step 4: Add registry-driven Activity discovery** to homepage and generic Activity-links HTML generation for location Tide pages.
- [ ] **Step 5: Extend SEO helpers** to accept Activity result/indexability without weakening existing Live NOAA rules.
- [ ] **Step 6: Extend sitemap builder** to accept generated Activity inventory and include `/fishing/` + High/Medium location Fishing URLs only.
- [ ] **Step 7: Rebuild static outputs and run directory/SEO/render tests** until green.
- [ ] **Step 8: Commit** navigation + SEO.

## Task 10 — Integrate automatic location promotion and scheduled refreshes

**Files:**
- Modify: `src/promote_location.py`
- Modify: `src/test_location_promotion.py`
- Modify: `.github/workflows/promote-location.yml`
- Modify: `.github/workflows/update-san-diego.yml`
- Create: `.github/workflows/update-activities.yml` or replace with a clearly named general Activity workflow if cleaner
- Create: `src/test_activity_workflows.py`

**Promotion contract:** a promotion request includes/validates Activity geography for any newly added catalog location; after Tide generation the same PR generates every enabled Activity output automatically.

**Schedules:**
- Existing Tide refresh remains every 6h.
- Full Activity refresh every 3h.
- Alert-only Safety refresh hourly.

- [ ] **Step 1: Write failing tests** that inspect workflow/promotion code for Activity validation, Activity generation, full regressions, generated-output staging, 3h full schedule, 1h alert schedule, and no recursive promotion trigger.
- [ ] **Step 2: Write a promotion test with a synthetic catalog fixture** proving the new location enters every enabled Activity with no separate Activity request.
- [ ] **Step 3: Verify RED.**
- [ ] **Step 4: Extend promotion normalization/validation** to require or resolve the Activity geography contract for new catalog additions while preserving legacy behavior for already-existing catalog locations.
- [ ] **Step 5: Update promotion workflow**: Tide generation → Activity collection/scoring/rendering → directories/SEO → full regressions → stage Activity JSON/pages/hub/sitemap in the same PR.
- [ ] **Step 6: Add scheduled Activity workflow** with separate full and alert-only jobs/cadences. Use concurrency guards to prevent overlapping writers.
- [ ] **Step 7: Ensure generated commit messages contain no CI-skip markers.**
- [ ] **Step 8: Run workflow/promotion tests** until green.
- [ ] **Step 9: Commit** automation integration.

## Task 11 — Validate all current locations, generate production outputs, and ship safely

**Files:**
- Generated: `public/data/conditions/*.json`
- Generated: `public/data/activities/fishing/*.json`
- Generated: `public/tides/*/*/fishing/index.html`
- Generated: `public/fishing/index.html`
- Generated/modified: `public/index.html`, parent Tide pages, `public/sitemap.xml`, `public/robots.txt`
- Temporary branch-only workflow may be added for validation and must be removed from final diff.

- [ ] **Step 1: Add a temporary feature-branch validation workflow** if needed to execute network-backed NWS/NOAA generation and the full offline regression suite without touching `main`.
- [ ] **Step 2: Run full Activity collection across every current catalog location.** Record which locations are High/Medium, Limited, or Unavailable; do not force a score for missing marine/safety data.
- [ ] **Step 3: Validate every Activity point through NWS point metadata and inspect failures.** Correct bad geography only with defensible representative shore/marine coordinates; never substitute the NOAA Tide station merely to make the API work.
- [ ] **Step 4: Re-run until each current location either has validated production data or a legitimate Limited/Unavailable result.**
- [ ] **Step 5: Generate `/fishing/`, all location Fishing pages/status pages, bidirectional links, and sitemap.** Confirm original Tide URL set is unchanged.
- [ ] **Step 6: Run complete regression suite**, including all existing tests plus new Activity tests.
- [ ] **Step 7: Run explicit safety fixtures** proving severe alert → NOT RECOMMENDED, alert failure → Unavailable, stale alerts >2h → no normal safety state, and stale full forecast >6h → no High/Medium.
- [ ] **Step 8: Compare branch vs base** and inspect for accidental deletes/moves, URL changes, `example.com`, hard-coded `51`, unresolved template tokens, or `[skip ci]`.
- [ ] **Step 9: Remove temporary validation workflow from the final diff.**
- [ ] **Step 10: Create PR** summarizing data sources, score scope, Safety Gate, indexability, automatic location expansion, and generated URL additions.
- [ ] **Step 11: Verify PR mergeability/checks and Cloudflare preview.** Spot-check `/`, `/fishing/`, one normal Fishing page, one Limited/Unavailable page if present, and parent Tide page links.
- [ ] **Step 12: Squash merge with a clean commit title/body containing no CI-skip marker.**
- [ ] **Step 13: Verify final Cloudflare Production deployment succeeds on the merge SHA.**

## Required regression command set

At minimum, the final feature-branch verification runs:

```bash
python src/test_alphanumeric_stations.py
python src/test_nearby_noaa.py
python src/test_timezones.py
python src/test_location_promotion.py
python src/test_generate_tides.py
python src/test_directory_generation.py
python src/test_seo_generation.py
python src/test_integrated_render.py
python src/test_san_diego_fixture.py
python src/test_activity_geography.py
python src/test_activity_registry.py
python src/test_activity_conditions.py
python src/test_activity_scoring_engine.py
python src/test_activity_safety.py
python src/test_fishing_scoring.py
python src/test_fishing_safety.py
python src/test_activity_generation.py
python src/test_activity_rendering.py
python src/test_activity_workflows.py
```

## Completion criteria

Implementation is complete only when:

- the existing Tide URL set is unchanged,
- `/fishing/` works as a national comparison page,
- every catalog location automatically has Fishing output/status,
- High/Medium pages are indexable and rankable while Limited/Unavailable pages fail conservatively,
- the Safety Gate overrides favorable conditions when necessary,
- no missing alert/marine data is interpreted as safe,
- adding one synthetic new location automatically expands every enabled Activity,
- enabling a second test Activity requires no geography duplication or manual location page list,
- scheduled Activity refresh and promotion workflows are automated,
- all old and new regressions pass,
- Cloudflare preview and final Production deployment succeed.