# CoastalNow Surfing v1 Design

## Goal

Add a Surfing activity to CoastalNow as a 10-location pilot without changing existing Tide or Fishing URLs, without adding a paid external surf API, and without weakening the existing safety, freshness, or deployment guarantees.

Surfing v1 reuses the existing shared Condition Snapshot pipeline and introduces a Surf Conditions Score, Surfing hub, location pages, Activity links, and automatic refresh integration. The pilot is intentionally limited so data quality and user behavior can be observed before expanding Surfing to all CoastalNow locations.

## Scope

### In scope

- Add Surfing as an enabled Activity with a location allowlist.
- Start with 10 pilot locations, subject to pre-release wave-data validation.
- Add a rule-based Surf Conditions Score on a 0–100 normalized planning scale.
- Reuse existing NOAA/NOS/CO-OPS and NOAA NWS inputs.
- Add Surfing hub and location pages.
- Add Tide ↔ Fishing ↔ Surfing internal navigation for locations where Surfing is available.
- Integrate Surfing into existing Activity refresh and safety-alert refresh flows.
- Add sitemap/SEO/IndexNow coverage through existing site-build mechanisms.
- Preserve current Health & Safety language discipline: no safety guarantees, no skill-based advice, no medical/health advice.

### Out of scope

- Paid surf APIs.
- Break-specific surf forecasts.
- Swell direction scoring unless the existing NWS data source proves stable and explicit during implementation.
- Board/skill-level recommendations.
- Pinterest Surfing RSS in v1.
- Surfing on all 51 locations before pilot validation.
- Swimming or Beach implementation.

## Existing Architecture to Reuse

The existing Activity Registry already reserves a Surfing entry but keeps it disabled. The shared Activity generator collects one Condition Snapshot per location and then scores every enabled Activity. Fishing currently uses this model successfully.

Surfing will reuse:

- `src/activities/registry.py`
- `src/generate_activities.py`
- `src/activities/conditions/**`
- `src/activities/scoring/engine.py`
- `src/activities/scoring/safety.py`
- `src/activities/rendering/**`
- `src/build_site.py`
- existing Activity refresh workflows and shared concurrency lock
- existing sitemap and IndexNow behavior

No new external provider is required for v1.

## Pilot Location Model

Activity enablement must support a per-Activity location allowlist. Fishing remains enabled for all supported locations. Surfing is enabled only for validated pilot locations.

Recommended initial candidates:

1. San Diego, CA
2. La Jolla, CA
3. Huntington Beach, CA
4. Santa Cruz, CA
5. Malibu, CA
6. Half Moon Bay, CA
7. Cocoa Beach, FL
8. Daytona Beach, FL
9. Wrightsville Beach, NC
10. Virginia Beach, VA

Before publication, each candidate must be checked against the current shared Condition Snapshot pipeline to confirm that NWS marine data supplies usable wave height and wave period frequently enough for Surfing v1. If a candidate fails that validation, it may be replaced by another existing CoastalNow location without requiring a new design approval. The final public pilot must contain 10 validated locations.

The Registry should expose a helper equivalent to “activity enabled for this location” so generation, rendering, navigation, and SEO all use one source of truth rather than repeating allowlist logic.

## Surf Conditions Score

### Meaning

The Surf Conditions Score is a 0–100 normalized planning metric. It is not:

- a measured ocean value,
- a safety score,
- a prediction of surf quality at a specific break,
- a recommendation for a user’s skill level,
- a guarantee that conditions are suitable for entering the water.

Pages must state this clearly.

### v1 weights

- Wave height: 30%
- Wave period: 25%
- Wind: 25%
- Weather: 10%
- Daylight/time of day: 10%

Tide is shown as context but is not included in the v1 composite score because ideal tide varies substantially by surf break. This avoids false precision.

### Component principles

All component values are normalized 0–100 scoring inputs, not raw measurements.

Wave height and period heuristics should favor moderate, organized surf and avoid implying that larger surf is inherently better. Wind should favor lighter winds and penalize strong winds. If coast bearing is reliable, it may be used only for broad onshore-wind penalties, not for break-specific offshore claims. Weather scoring should be limited to operational context such as precipitation/thunderstorm conditions. Daylight should favor daylight periods and avoid presenting darkness as unsafe by itself.

The implementation plan may tune exact thresholds after testing against representative fixtures, but it must preserve these weights and semantic constraints unless a new design approval is requested.

## Safety Gate

Safety Gate always overrides quality score.

### Hard-stop candidates

At minimum, Surfing must treat the following as hard-stop or equivalent NOT RECOMMENDED conditions when active and relevant:

- Tsunami Warning
- Hurricane Warning
- Tropical Storm Warning
- Storm Surge Warning
- Extreme Wind Warning
- Severe Thunderstorm Warning
- High Surf Warning
- Special Marine Warning
- Coastal Flood Warning where shoreline access/exposure is directly implicated
- extreme sustained wind/gust thresholds defined by policy
- extreme wave-exposure threshold defined by policy

### Caps / penalties

Examples include:

- Rip Current Statement: cap or hard stop depending on explicit high-risk wording
- Small Craft Advisory: cap
- Dense Fog Advisory: penalty
- Coastal Flood Advisory: cap
- strong wind: graduated cap
- elevated wave exposure: graduated penalty/cap
- forecast thunderstorm wording: strong cap

The implementation must be conservative where data is incomplete.

## Missing Data and Confidence

Fishing exposed important failure modes that Surfing must avoid from the start.

Rules:

- Alert lookup failure is unknown, never “no alerts”.
- Missing tide does not automatically block Surfing score because Tide is contextual in v1, but the page must mark tide context unavailable.
- Missing wave height or wave period means Surfing is `Limited` and no diagnostic headline score should be shown.
- Missing wind or core forecast data means `Unavailable`.
- Stale/failed safety state cannot produce a normal recommendation.
- `NOT RECOMMENDED` remains higher priority than `Limited`.
- `Limited` and `Unavailable` cards suppress misleading numeric recommendation scores.
- Confidence uses the existing High / Medium / Limited / Unavailable vocabulary where practical.

## Page and URL Structure

Existing URLs remain unchanged.

- Tide: `/tides/{state}/{location}/`
- Fishing: `/tides/{state}/{location}/fishing/`
- Surfing: `/tides/{state}/{location}/surfing/`
- Surfing hub: `/surfing/`

No redirects or URL migrations are required.

### Surfing location page

The Surfing page should follow the established CoastalNow visual system and Fishing information hierarchy, while using Surf-specific labels.

Required sections:

- CoastalNow header and search
- breadcrumbs
- Surf Conditions hero
- normalized score explanation
- status / confidence / data-state messaging
- best available planning window when ranking is eligible
- hourly context
- normalized factor breakdown
- raw context values for wave height, period, wind, weather and tide where available
- source / freshness / methodology disclosure
- links back to Tide and Fishing

No NOAA/NWS logos.

### Hub

`/surfing/` lists only pilot locations. Limited/Unavailable locations must not show misleading diagnostic scores. The hub must explain that the score is a planning metric, not a measured value or safety guarantee.

## Internal Navigation

The Activity Registry must be the source of truth for navigation.

For a pilot Surfing location:

- Tide page exposes Fishing and Surfing.
- Fishing page exposes Tide and Surfing.
- Surfing page exposes Tide and Fishing.

For a non-pilot location:

- Tide and Fishing must not render dead Surfing links.

Fishing CTA bugs showed that post-processing alone is insufficient. Any Tide-to-Activity primary navigation that must survive regeneration must be rendered at the Tide generator/template level or through a generation path that is guaranteed to run whenever Tide HTML is rebuilt. `build_site.py` may remain a secondary normalization/safety layer but must not be the sole owner of critical links.

Mobile tests must verify visible navigation structure, not merely string presence.

## Rendering and Registry Changes

The current Activity dispatcher special-cases Fishing rendering. Surfing should be added through an explicit Surfing renderer while keeping the dispatcher understandable. Avoid large unrelated refactors.

Recommended boundaries:

- `activities/scoring/surfing_policy.py` — Surfing scoring, confidence and Safety Gate policy
- Surfing-specific rendering functions/modules under `activities/rendering/`
- Registry location-allowlist helper
- shared link/path helpers reused unchanged where possible

The implementation should not copy all Fishing code wholesale if a small shared helper clearly removes duplication, but broad refactoring is out of scope.

## Data Flow

For each scheduled Activity refresh:

1. Collect one shared Condition Snapshot per location.
2. Determine which Activities are enabled for that location.
3. Score Fishing everywhere it is enabled.
4. Score Surfing only for pilot locations.
5. Persist Activity JSON separately by Activity.
6. Build Activity hub/location HTML.
7. Normalize Tide page Activity navigation using the same Registry decisions.
8. Build sitemap and robots output.
9. Commit generated public outputs under the existing workflow behavior.
10. Existing IndexNow detects changed HTML and submits affected URLs.

The hourly safety-alert refresh follows the same location-aware Activity selection and must not require a separate Surfing workflow.

## Automation

Do not add a separate Surfing data workflow.

Surfing must run under the existing:

- 3-hour Activity refresh
- 1-hour safety-alert refresh
- shared `coastalnow-site-writes` concurrency discipline

This keeps official-data fetches shared and avoids duplicate API load and push races.

## SEO and Metadata

Surfing pages must use unique titles/descriptions appropriate to surf-condition planning. Suggested pattern:

- `{City} Surf Conditions & Best Times | CoastalNow`

Avoid promises such as “best waves guaranteed”, “safe to surf”, or claims of exact break-level quality.

Only public pilot Surfing pages belong in the sitemap. Non-pilot Surfing URLs must not be generated or linked.

## Rollout and Publication Gate

Implementation may be built and tested for all fixture scenarios, but Production publication requires all of the following:

1. 10 pilot locations pass wave-height / wave-period availability validation.
2. Score-component unit tests pass.
3. Missing-wave state produces Limited and suppresses headline numeric score.
4. Missing/failed alerts cannot produce normal safety state.
5. Safety Gate priority tests pass.
6. Pilot Surfing URLs and metadata are correct.
7. No Surfing URLs or links exist for non-pilot locations.
8. Tide ↔ Fishing ↔ Surfing navigation is correct for pilot locations.
9. Mobile navigation/CTA regression tests pass.
10. Surfing hub handles normal, Limited, Unavailable and NOT RECOMMENDED states correctly.
11. Sitemap contains only public Surfing URLs.
12. Existing Tide/Fishing tests remain green.
13. Full repository regression suite passes.
14. Cloudflare branch Preview succeeds.
15. Final PR diff is reviewed for unintended generated-data churn.
16. Production deploy succeeds after merge.

## Post-launch Validation

After Production rollout:

- Verify at least San Diego and one East Coast Surfing page on mobile.
- Verify Tide/Fishing/Surfing bidirectional links in production.
- Verify scheduled Activity and hourly safety workflows complete normally after Surfing is enabled.
- Observe Cloudflare Web Analytics and Search Console for several days before expanding beyond 10 locations.

Expansion from 10 to all validated existing CoastalNow locations can be treated as a follow-up bounded rollout if it does not change scoring or safety semantics.

## Pinterest

Do not add Surfing to Pinterest RSS during this v1 implementation. After Surfing pages have remained stable and shown meaningful search/analytics activity, add Surfing RSS/board distribution as a separate bounded change.

## Success Criteria

Surfing v1 is successful when CoastalNow can publish and automatically maintain 10 reliable Surfing planning pages using the existing official-data pipeline, without regressing Tide/Fishing, without dead or disappearing internal links, without misleading scores under missing/safety-constrained data, and without adding a new paid provider or duplicated refresh workflow.
