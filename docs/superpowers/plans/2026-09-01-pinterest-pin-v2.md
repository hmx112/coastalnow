# Pinterest Pin v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CoastalNow’s decorative Pinterest images with deterministic information-first Tide and Fishing pin templates that match the live site branding and preserve the current RSS/release behavior.

**Architecture:** Keep `src/generate_pinterest.py`, RSS generation, GUIDs, destinations, and scheduling unchanged. Replace only the Pillow renderer in `src/pinterest/render.py`, using shared drawing helpers for the canonical CoastalNow brand, typography, feature cards, icons, CTA, and footer. Extend renderer tests so they assert exact copy, evergreen constraints, logo structure, dimensions, and absence of the old decorative wave-layer implementation.

**Tech Stack:** Python 3.12, Pillow 11.3.0, `unittest`, GitHub Actions, Cloudflare Pages.

**Spec:** `docs/pinterest-pin-v2-spec.md`

## Global Constraints

- Output must remain exactly `1000 × 1500` PNG.
- Rendering must remain deterministic and offline; no network access and no AI image generation in production.
- Use the CoastalNow site logo visual: teal rounded-square mark with three white horizontal waves plus `CoastalNow` navy wordmark.
- Do not commit font files; use available system fonts with fallbacks.
- Do not use NOAA/NWS logos.
- Do not put volatile values in pin images: no current score values, wind speed, wave height, tide height/time, temperature, dates, or alerts.
- The generic phrase `Live 0–100 Fishing Score` is allowed because it describes the scale, not a current value.
- Existing RSS feed paths, GUIDs, landing URLs, launch order, and `locations_per_day: 1` remain unchanged.
- Do not republish already-released Pinterest items by changing GUIDs or destination URLs.

---

### Task 1: Lock v2 copy and brand contract in tests

**Files:**
- Modify: `src/test_pinterest_render.py`
- Test: `src/test_pinterest_render.py`

**Interfaces:**
- Consumes: existing `pin_text(item: dict, kind: str) -> dict[str, str]`, `render_pin(item: dict, kind: str, output: Path) -> Path`
- Produces: test expectations for v2 text payload keys `subtitle`, `cta`, `features`, and `footer`, plus stable renderer constants/helpers used by later tasks.

- [ ] **Step 1: Extend the evergreen text test with exact v2 copy**

Add assertions equivalent to:

```python
tide = pin_text(self.item, "tides")
self.assertEqual(tide["subtitle"], "Fast local tide info for planning by the water.")
self.assertEqual(tide["cta"], "See today’s tide times →")
self.assertEqual(
    tide["features"],
    (
        ("High & Low Tide Times", "Know when tides rise and fall."),
        ("7-Day Tide Forecast", "Plan ahead with a weekly outlook."),
        ("Live NOAA Tide Data", "Reliable local prediction data."),
        ("Today’s Tide Chart", "See the tide pattern at a glance."),
    ),
)

fishing = pin_text(self.item, "fishing")
self.assertEqual(fishing["subtitle"], "For shore, pier and nearshore fishing.")
self.assertEqual(fishing["cta"], "See today’s fishing conditions →")
self.assertEqual(
    fishing["features"],
    (
        ("Live 0–100 Fishing Score", "See how conditions rate for fishing."),
        ("Tide", "Tide movement and timing"),
        ("Wind", "Wind speed and direction"),
        ("Waves", "Wave height and period"),
        ("Weather", "Sky, rain chance and more"),
        ("Best 3-hour fishing window", "Top window based on today’s conditions"),
    ),
)
```

- [ ] **Step 2: Add a renderer-source regression that rejects the old decorative wave-layer approach**

Read `src/pinterest/render.py` and assert the old helper `_wave_polygon` and the four large layered `draw.polygon(_wave_polygon(...))` calls are absent after implementation. Do not reject small wave icons used for the CoastalNow logo.

- [ ] **Step 3: Add a logo helper contract test**

Import `_draw_coastalnow_brand` and assert it is callable. Render a pin and inspect representative pixels or helper constants only if stable; avoid brittle screenshot-hash tests. The test should primarily guarantee that both pin kinds use the same brand helper and that the mark is a rounded-square/wave logo rather than the prior ellipse/arc mark.

- [ ] **Step 4: Run the focused test and verify RED**

Run:

```bash
python src/test_pinterest_render.py
```

Expected: FAIL because v2 payload keys/helper do not exist and old decorative renderer is still present.

- [ ] **Step 5: Commit the RED test**

```bash
git add src/test_pinterest_render.py
git commit -m "test: define Pinterest pin v2 renderer contract"
```

---

### Task 2: Implement shared CoastalNow brand and layout primitives

**Files:**
- Modify: `src/pinterest/render.py`
- Test: `src/test_pinterest_render.py`

**Interfaces:**
- Consumes: Pillow `Image`, `ImageDraw`, `ImageFont`; existing `WIDTH`, `HEIGHT`, brand palette.
- Produces: `_draw_coastalnow_brand(draw, x, y)`, `_draw_wrapped_text(...)`, `_draw_feature_card(...)`, `_draw_icon(...)`, and updated `pin_text(...)` payloads.

- [ ] **Step 1: Replace the old brand header implementation**

Implement one shared helper that draws:
- teal rounded rectangle approximately 78×78;
- three white horizontal sinusoidal/wave strokes inside the mark;
- `CoastalNow` navy wordmark to the right;
- no circular teal mark, no arc/sun mark, no separate fishing logo.

Suggested signature:

```python
def _draw_coastalnow_brand(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    ...
```

- [ ] **Step 2: Add reusable text wrapping/fitting helper**

Provide a deterministic helper used for subtitles, feature-card titles/descriptions, and CTA text. It must fit long labels such as `Best 3-hour fishing window` without clipping.

Suggested signature:

```python
def _draw_wrapped_text(draw, text, box, font_path, max_size, min_size, fill, spacing=8, align="left") -> None:
    ...
```

- [ ] **Step 3: Add simple vector icon renderer**

Support only these semantic icon names:
- `score`
- `tide`
- `wind`
- `waves`
- `weather`
- `window`
- `calendar`
- `data`
- `chart`

Icons must be simple line/vector drawings. `data` may use a database/check symbol but must not reproduce the NOAA logo.

- [ ] **Step 4: Expand `pin_text()` to return all v2 copy**

Return at minimum:

```python
{
    "brand": "CoastalNow",
    "location": item["name"].upper(),
    "state": item["state"].upper(),
    "category": ...,
    "subtitle": ...,
    "features": tuple(...),
    "cta": ...,
    "footer": ...,
}
```

- [ ] **Step 5: Run focused tests and verify the text/helper contract is GREEN**

Run:

```bash
python src/test_pinterest_render.py
```

Expected: remaining failures should be only layout/source assertions not yet implemented, or full PASS if layout implementation is already complete.

- [ ] **Step 6: Commit primitives**

```bash
git add src/pinterest/render.py src/test_pinterest_render.py
git commit -m "feat: add Pinterest v2 brand and layout primitives"
```

---

### Task 3: Implement Tide and Fishing information-first templates

**Files:**
- Modify: `src/pinterest/render.py`
- Test: `src/test_pinterest_render.py`

**Interfaces:**
- Consumes: helpers from Task 2 and `pin_text()` payload.
- Produces: deterministic `render_pin()` output for `tides` and `fishing`.

- [ ] **Step 1: Replace the old decorative composition in `render_pin()`**

Remove:
- dark full-width 210px brand banner as the dominant header;
- large sun/horizon motif used only as decoration;
- four layered lower-half wave polygons that resemble a chart;
- fishing-hook-only visual cue as the main content.

Use an off-white/pale-aqua base with clean card hierarchy.

- [ ] **Step 2: Implement common header/location hierarchy**

Approximate vertical zones:
- y 55–155: canonical CoastalNow brand;
- y 200–370: city and state;
- y 390–560: category headline and subtitle.

City must be the largest location text. Category must remain readable at feed thumbnail size.

- [ ] **Step 3: Implement Fishing 3×2 feature-card grid**

Draw six rounded cards between approximately y 610–1190.

Card order must be:
1. `Live 0–100 Fishing Score`
2. `Tide`
3. `Wind`
4. `Waves`
5. `Weather`
6. `Best 3-hour fishing window`

Each card has one icon, title, and concise description. No live values.

- [ ] **Step 4: Implement Tide 2×2 feature-card grid plus benefit row**

Draw four rounded cards between approximately y 630–1080:
1. `High & Low Tide Times`
2. `7-Day Tide Forecast`
3. `Live NOAA Tide Data`
4. `Today’s Tide Chart`

Below, draw a compact value strip with:
- `Local Focus`
- `Accurate NOAA Data`
- `Real-time Updates`
- `Clean & Clear`

Use text `NOAA` only; never draw the NOAA emblem.

- [ ] **Step 5: Draw template-specific CTA and footer**

Fishing:
- CTA: `See today’s fishing conditions →`
- footer: `Live tide, wind & wave context`

Tide:
- CTA: `See today’s tide times →`
- footer: `Your go-to source for coastal conditions.`

CTA must be a high-contrast rounded teal button, not an externally baked Pinterest UI button.

- [ ] **Step 6: Verify exact output size and focused tests**

Run:

```bash
python src/test_pinterest_render.py
```

Expected: PASS.

- [ ] **Step 7: Commit templates**

```bash
git add src/pinterest/render.py src/test_pinterest_render.py
git commit -m "feat: render information-first Pinterest pin templates"
```

---

### Task 4: Regenerate San Diego samples without changing RSS identity

**Files:**
- Modify generated assets only as needed: `public/pinterest/images/san-diego-tides.png`, `public/pinterest/images/san-diego-fishing.png`
- Do not intentionally modify: `public/pinterest/rss/tides.xml`, `public/pinterest/rss/fishing.xml`

**Interfaces:**
- Consumes: `src/generate_pinterest.py`, current enabled schedule, v2 renderer.
- Produces: v2 San Diego image files while preserving existing feed GUIDs and destinations.

- [ ] **Step 1: Regenerate with the existing release date**

Run:

```bash
python src/generate_pinterest.py --date 2026-08-31
```

This should regenerate San Diego images using v2 without introducing a new RSS item identity.

- [ ] **Step 2: Confirm RSS identity is unchanged**

Run:

```bash
git diff -- public/pinterest/rss/tides.xml public/pinterest/rss/fishing.xml
```

Expected: no semantic changes to GUIDs, destinations, titles, or descriptions. Ideally no RSS diff at all.

- [ ] **Step 3: Inspect generated PNG metadata**

Open both images and confirm:
- 1000×1500;
- PNG;
- readable text hierarchy;
- no clipping;
- same site-style logo;
- no fake graph-like wave background;
- no volatile values.

- [ ] **Step 4: Commit regenerated San Diego v2 images**

```bash
git add public/pinterest/images/san-diego-tides.png public/pinterest/images/san-diego-fishing.png
git commit -m "chore: regenerate San Diego Pinterest v2 samples"
```

---

### Task 5: Full regression, workflow compatibility, and merge

**Files:**
- Verify: `.github/workflows/update-pinterest.yml`
- Verify: `src/generate_pinterest.py`
- Verify: `src/pinterest/rss.py`
- Verify: `src/pinterest/schedule.py`
- Verify: `src/data/pinterest.json`

**Interfaces:**
- Consumes: completed v2 renderer.
- Produces: merge-ready feature branch with unchanged release cadence and RSS behavior.

- [ ] **Step 1: Install pinned image dependency**

Run:

```bash
pip install -r requirements-pinterest.txt
```

- [ ] **Step 2: Run Pinterest-focused suite**

Run the existing Pinterest tests, including renderer, generator, RSS, schedule/catalog, and workflow tests.

Expected: all PASS.

- [ ] **Step 3: Run complete repository regression suite**

Run:

```bash
python -m unittest discover -s src -p "test_*.py"
```

Expected: all PASS.

- [ ] **Step 4: Verify schedule and RSS files are unchanged**

Confirm:
- `src/data/pinterest.json` still has `locations_per_day: 1`;
- no GUID version bump;
- no destination URL changes;
- `.github/workflows/update-pinterest.yml` schedule remains unchanged;
- no already-published item duplication mechanism was introduced.

- [ ] **Step 5: Review final diff**

Expected product diff:
- `src/pinterest/render.py`
- `src/test_pinterest_render.py`
- `public/pinterest/images/san-diego-tides.png`
- `public/pinterest/images/san-diego-fishing.png`
- this implementation plan

No unrelated site/data files.

- [ ] **Step 6: Create PR and wait for Cloudflare Preview**

PR title:

```text
Redesign Pinterest pins with information-first templates
```

PR body must summarize the v2 design, evergreen constraints, unchanged RSS/schedule identity, and test results.

- [ ] **Step 7: Squash merge only after tests and Preview succeed**

After merge, verify the production branch deploy succeeds. Future daily Pinterest runs should use v2 automatically for newly released locations.
