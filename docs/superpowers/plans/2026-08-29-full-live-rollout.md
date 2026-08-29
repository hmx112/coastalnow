# Full Live Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the remaining 39 Preview locations to validated Live NOAA pages in six regional waves, leaving any location Preview only when no defensible NOAA mapping can be verified.

**Architecture:** Keep the existing NOAA rendering, `hilo-derived`, SEO, and Cloudflare deployment systems. Extend the push-promotion request format so one regional request can contain multiple locations, validate the entire batch atomically, render only the new locations, rebuild directories/SEO once, run the full regression suite, and create one PR per regional wave.

**Tech Stack:** Python 3.12, NOAA CO-OPS MDAPI and Data API, GitHub Actions, static HTML, Cloudflare Pages.

**Spec:** `docs/superpowers/specs/2026-08-29-full-live-rollout.md`

## Global Constraints

- Use NOAA CO-OPS tide-prediction stations only.
- Do not substitute a merely nearby station for an exact/local station just to reach 51/51 Live.
- NOAA `type=R` stations use harmonic/interval predictions.
- NOAA `type=S` stations use `prediction_mode: "hilo-derived"`.
- Batch promotion must be atomic: config changes are written only after every requested location validates.
- Existing single-location promotion requests remain backward compatible.
- Preview pages remain `noindex,follow` and absent from `sitemap.xml` until promotion succeeds.
- Never use `[skip ci]` in commits that may reach `main`.
- Every regional PR must pass the complete existing regression suite plus new batch-promotion tests before merge.

---

### Task 1: Add batch promotion request support

**Files:**
- Modify: `src/promote_location.py`
- Modify: `src/test_location_promotion.py`

**Interfaces:**
- Consumes: legacy request object `{slug, station_id, station_name, prediction_mode?}`.
- Produces: normalized `list[dict]` from either the legacy object or `{ "locations": [...] }` batch request.
- Produces: atomic `src/data/live_noaa.json` update only after all entries validate.

- [ ] **Step 1: Write failing normalization tests**

Add tests equivalent to:

```python
class BatchPromotionTests(unittest.TestCase):
    def test_batch_request_normalizes_multiple_locations(self):
        payload = {
            "locations": [
                {"slug": "santa-cruz", "station_id": "9413745", "station_name": "Santa Cruz, Monterey Bay, CA", "prediction_mode": "hilo-derived"},
                {"slug": "half-moon-bay", "station_id": "9414131", "station_name": "Pillar Point Harbor, Half Moon Bay, CA"},
            ]
        }
        items = normalize_request_payload(payload)
        self.assertEqual([x["slug"] for x in items], ["santa-cruz", "half-moon-bay"])

    def test_legacy_request_still_normalizes_to_one_item(self):
        payload = {"slug": "santa-cruz", "station_id": "9413745", "station_name": "Santa Cruz, Monterey Bay, CA", "prediction_mode": "hilo-derived"}
        self.assertEqual(len(normalize_request_payload(payload)), 1)

    def test_unknown_mode_is_rejected_before_config_write(self):
        payload = {"locations": [{"slug": "santa-cruz", "station_id": "9413745", "station_name": "Santa Cruz, Monterey Bay, CA", "prediction_mode": "wrong"}]}
        with self.assertRaises(ValueError):
            normalize_request_payload(payload)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python src/test_location_promotion.py
```

Expected: FAIL because `normalize_request_payload` does not yet support batch requests.

- [ ] **Step 3: Implement request normalization**

Implement one function with this behavior:

```python
def normalize_request_payload(payload: dict) -> list[dict]:
    raw_items = payload.get("locations") if "locations" in payload else [payload]
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("promotion request must contain at least one location")
    items = []
    seen = set()
    for raw in raw_items:
        slug = raw["slug"]
        if slug in seen:
            raise ValueError(f"duplicate promotion slug: {slug}")
        seen.add(slug)
        mode = raw.get("prediction_mode", "harmonic")
        if mode not in {"harmonic", "hilo-derived"}:
            raise ValueError(f"unsupported prediction_mode: {mode}")
        items.append({
            "slug": slug,
            "station_id": str(raw["station_id"]),
            "station_name": raw["station_name"],
            "prediction_mode": mode,
        })
    return items
```

Refactor the existing promotion path to validate every normalized item first, accumulate config mutations in memory, and write `live_noaa.json` once only after all validations pass.

- [ ] **Step 4: Add atomicity test**

Use a temporary config and mocked validation where item 1 succeeds and item 2 raises. Assert the persisted config remains byte-for-byte unchanged.

- [ ] **Step 5: Run tests to verify GREEN**

```bash
python src/test_location_promotion.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/promote_location.py src/test_location_promotion.py
git commit -m "Support atomic batch location promotion"
```

---

### Task 2: Make the push-trigger workflow batch-aware

**Files:**
- Modify: `.github/workflows/promote-location.yml`

**Interfaces:**
- Consumes: one changed `promotion-request/*.json` file.
- Produces: newline-safe list of promoted slugs, generation for each slug, one regional PR.

- [ ] **Step 1: Change request resolution output**

Replace the single `slug` extraction with a Python expression that reads either request form and emits a comma-separated slug list:

```bash
slugs=$(python -c 'import json,sys; p=json.load(open(sys.argv[1])); xs=p.get("locations", [p]); print(",".join(x["slug"] for x in xs))' "$request")
echo "slugs=$slugs" >> "$GITHUB_OUTPUT"
```

- [ ] **Step 2: Generate every newly promoted location**

Replace the single generation command with:

```bash
IFS=',' read -ra SLUGS <<< "${{ steps.request.outputs.slugs }}"
for slug in "${SLUGS[@]}"; do
  python src/generate_tides.py --location "$slug"
done
```

- [ ] **Step 3: Include SEO regression**

The regression step must include:

```bash
python src/test_location_promotion.py
python src/test_generate_tides.py
python src/test_directory_generation.py
python src/test_seo_generation.py
python src/test_integrated_render.py
python src/test_san_diego_fixture.py
```

- [ ] **Step 4: Commit all generated SEO artifacts**

The generated promotion commit must stage:

```bash
git add src/data/live_noaa.json public/data public/tides public/index.html public/sitemap.xml public/robots.txt
```

Use commit message `Promote regional batch to Live NOAA` with no CI-skip tokens.

- [ ] **Step 5: Create one PR per regional request**

Use a PR title derived from the request filename, for example `Promote California wave to Live NOAA`, and include the promoted slug list in the body.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/promote-location.yml
git commit -m "Make promotion workflow batch-aware"
```

---

### Task 3: Complete the NOAA station audit for all 39 Preview locations

**Files:**
- Create: `docs/superpowers/research/2026-08-29-noaa-station-audit.md`

**Interfaces:**
- Consumes: NOAA MDAPI `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions` plus individual tide-prediction pages and offsets endpoints.
- Produces: one accepted mapping or an explicit `UNRESOLVED` decision per Preview slug.

- [ ] **Step 1: Audit California**

Cover exactly: `santa-cruz`, `newport-beach`, `huntington-beach`, `half-moon-bay`, `santa-monica`, `malibu`, `san-francisco`, `oceanside`, `laguna-beach`.

Record columns: slug, NOAA ID, NOAA station name, NOAA type (`R`/`S`), reference ID, geographic rationale, resulting prediction mode, confidence.

Use already confirmed anchors: Santa Cruz `9413745 S`, Half Moon Bay `9414131 R`, Santa Monica `9410840 R`, San Francisco `9414290 R`. For names with no exact MDAPI match, inspect neighboring NOAA stations by coastal geography before accepting anything.

- [ ] **Step 2: Audit North Carolina**

Cover exactly: `nags-head`, `kitty-hawk`, `kill-devil-hills`, `cape-hatteras`, `ocracoke`, `wrightsville-beach`, `carolina-beach`, `topsail-beach`, `emerald-isle`, `corolla`.

Use confirmed anchors: Nags Head `8652226 S`, Kitty Hawk `8651605 S`, Cape Hatteras `8654400 R` / `8654467 R`, Ocracoke `8654769 R`, Wrightsville Beach `8658163 R`.

- [ ] **Step 3: Audit South Carolina**

Cover exactly: `folly-beach`, `isle-of-palms`, `kiawah-island`, `edisto-beach`, `pawleys-island`.

Use confirmed anchors: Isle of Palms `8665494 S`, Edisto Beach `8667630 S`, Pawleys Island ocean pier `8662006 R`.

- [ ] **Step 4: Audit Florida**

Cover exactly: `key-west`, `clearwater-beach`, `st-pete-beach`, `naples`, `miami-beach`, `fort-lauderdale`, `daytona-beach`, `cocoa-beach`, `destin`, `panama-city-beach`.

Use confirmed anchors: Key West `8724580 R`, Clearwater Beach `8726724 R`, Naples `8725114 R`, Daytona Beach `8721120 S`, Cocoa Beach `8721649 R`, Destin `8729511 S`, Panama City Beach `8729210 R`. For Fort Lauderdale compare the inland `8722937 R` with coastal `8722899 R` and choose the station that best represents the beach-intent page.

- [ ] **Step 5: Audit Oregon and Mid-Atlantic**

Cover exactly: `cannon-beach`, `seaside`, `ocean-city`, `virginia-beach`, `cape-may`.

Use confirmed anchors: Ocean City `8570280 R` / `8570283 R`, Virginia Beach `8639168 S`, Cape May Atlantic Ocean `8535962 S` versus ferry terminal `8536110 R`.

- [ ] **Step 6: Apply the no-forced-mapping gate**

Any location without a defensible station is written as `UNRESOLVED` with candidate stations and the reason for rejection. Do not promote it in later waves.

- [ ] **Step 7: Commit the audit**

```bash
git add docs/superpowers/research/2026-08-29-noaa-station-audit.md
git commit -m "Document NOAA station mappings for remaining locations"
```

---

### Task 4: Promote the California and North Carolina waves

**Files:**
- Create from audit: `promotion-request/california-wave.json`
- Create from audit: `promotion-request/north-carolina-wave.json`
- Generated/modified by workflow: `src/data/live_noaa.json`, `public/data/*`, `public/tides/*`, `public/index.html`, `public/sitemap.xml`, `public/robots.txt`

**Interfaces:**
- Consumes: accepted rows from the station audit.
- Produces: two independent, mergeable regional PRs.

- [ ] **Step 1: Create California batch request on `promotion/california-wave`**

Serialize every accepted California audit row into:

```json
{
  "locations": [
    {
      "slug": "santa-cruz",
      "station_id": "9413745",
      "station_name": "Santa Cruz, Monterey Bay, CA",
      "prediction_mode": "hilo-derived"
    },
    {
      "slug": "half-moon-bay",
      "station_id": "9414131",
      "station_name": "Pillar Point Harbor, Half Moon Bay, CA"
    },
    {
      "slug": "santa-monica",
      "station_id": "9410840",
      "station_name": "Santa Monica, Municipal Pier, CA"
    },
    {
      "slug": "san-francisco",
      "station_id": "9414290",
      "station_name": "San Francisco (Golden Gate), CA"
    }
  ]
}
```

Before committing, append the remaining accepted California rows from the audit to the same `locations` array; omit only rows explicitly marked `UNRESOLVED`.

- [ ] **Step 2: Push and verify California workflow**

Verify NOAA validation, per-location generation, directory/SEO rebuild, all six regression test scripts, generated commit, and auto-created PR.

- [ ] **Step 3: Inspect California PR**

Confirm every promoted page has current tide data, correct source station name, correct `index,follow`, self-canonical URL, and sitemap inclusion. Confirm unresolved pages remain Preview/noindex.

- [ ] **Step 4: Squash merge California PR**

Use a clean merge title such as `Promote California locations to Live NOAA`; do not allow intermediate commit bodies with CI-skip markers into the final message.

- [ ] **Step 5: Repeat for North Carolina**

Create `promotion/north-carolina-wave` from the updated `main`, serialize all accepted NC audit rows, run the same checks, and merge only after the PR is mergeable and tests pass.

---

### Task 5: Promote the South Carolina and Florida waves

**Files:**
- Create: `promotion-request/south-carolina-wave.json`
- Create: `promotion-request/florida-wave.json`

- [ ] **Step 1: Create and push South Carolina wave**

Use accepted audit rows only. Ensure subordinate stations such as Isle of Palms and Edisto Beach explicitly carry `"prediction_mode": "hilo-derived"`.

- [ ] **Step 2: Verify and merge South Carolina PR**

Check tide data, curve disclosure on subordinate pages, SEO state, sitemap, full regression results, and Cloudflare Production after merge.

- [ ] **Step 3: Create and push Florida wave from fresh main**

Use accepted audit rows only. Verify Eastern/Central timezone assignments remain correct for each Florida location; Destin and Panama City Beach must render Central local time.

- [ ] **Step 4: Verify and merge Florida PR**

Use the same launch checks and a clean squash commit message.

---

### Task 6: Promote Oregon and Mid-Atlantic waves

**Files:**
- Create: `promotion-request/oregon-wave.json`
- Create: `promotion-request/mid-atlantic-wave.json`

- [ ] **Step 1: Promote Oregon**

Use accepted Cannon Beach and Seaside mappings from the audit. If either is unresolved, keep that slug Preview and promote the accepted one only.

- [ ] **Step 2: Promote Mid-Atlantic**

Use the accepted Ocean City, Virginia Beach, and Cape May mappings. For beach-intent pages prefer ocean-facing stations when the NOAA mapping is defensible.

- [ ] **Step 3: Merge each PR sequentially from fresh main**

Do not open a later batch from a stale base after an earlier batch modifies `live_noaa.json` and sitemap output.

---

### Task 7: Verify the final 51-location production state

**Files:**
- Read: `src/data/live_noaa.json`
- Read: `public/sitemap.xml`
- Read: generated `public/tides/**/index.html`

- [ ] **Step 1: Count status**

Run a Python check equivalent to:

```python
from locations import LOCATIONS
live = [x for x in LOCATIONS.values() if x["status"] == "Live NOAA"]
preview = [x for x in LOCATIONS.values() if x["status"] == "Preview"]
print("live", len(live))
print("preview", len(preview))
print([x["slug"] for x in preview])
```

Expected ideal result: `live 51`, `preview 0`. Any nonzero Preview list must match the audit's explicit unresolved list.

- [ ] **Step 2: Validate all Live config**

```bash
python src/promote_location.py --validate-config
```

Expected: PASS.

- [ ] **Step 3: Regenerate and run all regressions**

```bash
python src/generate_tides.py
python src/build_site.py
python src/test_location_promotion.py
python src/test_generate_tides.py
python src/test_directory_generation.py
python src/test_seo_generation.py
python src/test_integrated_render.py
python src/test_san_diego_fixture.py
```

Expected: all PASS.

- [ ] **Step 4: Verify search outputs**

Assert every Live page appears in `sitemap.xml`, every Preview page is absent, no page contains `https://example.com`, and no page uses meta keywords.

- [ ] **Step 5: Verify Cloudflare Production**

Confirm the final `main` SHA has a Cloudflare Pages check with `conclusion=success` and that the public site shows the latest state.

- [ ] **Step 6: Produce final rollout report**

Report: total Live count, any unresolved slugs, reference vs subordinate counts, final `main` SHA, Cloudflare deployment status, and readiness for custom-domain cutover.

---

### Task 8: Hand off to custom-domain launch

**Files:**
- No domain code change until the final domain is chosen.

- [ ] **Step 1: Stop after the Live rollout report**

Do not change `SITE_ORIGIN` away from `https://coastalnow.pages.dev` until the user supplies the purchased production domain.

- [ ] **Step 2: After the domain is supplied, create a separate domain-cutover plan**

That follow-up plan must cover Cloudflare custom-domain attachment, `SITE_ORIGIN` replacement, canonical/sitemap/robots regeneration, production deploy verification, and Google Search Console domain-property verification plus sitemap submission.
