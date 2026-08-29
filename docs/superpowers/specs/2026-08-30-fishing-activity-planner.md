# CoastalNow Fishing Activity Planner — Design Specification

Date: 2026-08-30
Status: Approved design pending implementation plan
Scope: Phase 1 Fishing only, with shared foundations for future Surfing, Beach, and Swimming

## 1. Product direction

CoastalNow will expand from a tide-only site into a **Coastal Conditions & Activity Planner** for U.S. coastal locations. The site must answer two distinct search and navigation intents:

1. **Location-first:** “Is fishing good in San Diego today?”
2. **Activity-first:** “Where in the U.S. has the best fishing conditions today?”

The existing tide site remains intact. Phase 1 adds Fishing as a new activity layer without moving, renaming, redirecting, or otherwise changing any existing indexed location URL.

Phase 1 Fishing is explicitly defined as **shore / pier / nearshore recreational fishing conditions**. Offshore or boat-fishing conditions are out of scope because their weather, sea-state, and safety thresholds differ materially and should become a separate future activity if needed.

The Fishing Score is a planning and comparison metric, not a safety guarantee. Official warnings, local closures, signs, lifeguards, harbor authorities, and emergency guidance always take priority over CoastalNow scores.

## 2. Non-negotiable URL and SEO constraints

The current location hierarchy is preserved exactly. Existing URLs such as:

- `/tides/california/san-diego/`

remain unchanged.

Fishing adds only new URLs:

- National Fishing hub: `/fishing/`
- Location Fishing page: `/tides/california/san-diego/fishing/`

Future activities will follow the same pattern:

- `/surfing/` and `/tides/.../surfing/`
- `/beach/` and `/tides/.../beach/`
- `/swimming/` and `/tides/.../swimming/`

No existing page relocation, directory reorganization, or redirect is part of this project.

New indexable pages receive canonical URLs, BreadcrumbList structured data, internal links, and sitemap entries. Existing sitemap entries remain untouched. Activity pages with insufficient critical data are generated for continuity but remain `noindex,follow` until they meet the data-quality threshold.

## 3. Location catalog is the source of truth

The existing location catalog remains the single source of truth for site geography. No separate list of Fishing locations will be maintained.

The core invariant is:

> **Adding one CoastalNow location automatically expands every enabled activity.**

Conceptually:

```text
LOCATIONS
  ├── Tide
  ├── Fishing
  ├── Surfing     (future)
  ├── Beach       (future)
  └── Swimming    (future)
```

A future location such as Galveston is added once to the location catalog. The build and update pipelines then automatically:

1. create or refresh its tide output,
2. collect common coastal-condition data,
3. run every enabled activity scorer,
4. create `/tides/texas/galveston/fishing/`,
5. add it to `/fishing/` when ranking eligibility is satisfied,
6. add appropriate internal links,
7. add indexable activity URLs to the sitemap.

No later “create Galveston Fishing” action is required.

Any hard-coded references to “51 locations” in user-facing generated content must be replaced by values derived from `len(LOCATIONS)` or the corresponding eligible activity count.

## 4. Location metadata for activities

Existing NOAA tide-station coordinates must not be assumed to represent the coastal location itself. This matters especially for locations using a nearby NOAA tide station.

The location catalog will therefore be extended with activity-specific geographic metadata without changing existing tide metadata:

```json
{
  "activity": {
    "shore_point": {"latitude": 0.0, "longitude": 0.0},
    "marine_point": {"latitude": 0.0, "longitude": 0.0},
    "coast_bearing": 270
  }
}
```

Meaning:

- `shore_point`: representative shoreline / pier area used for weather and shore alerts.
- `marine_point`: representative nearshore point used for marine forecasts and marine alerts.
- `coast_bearing`: optional shoreline-facing bearing used only when a scorer needs wind-direction exposure. Missing bearing must not be fabricated; direction-based adjustments are skipped and confidence may be reduced if the activity depends on them.

The existing NOAA station ID and station coordinates remain Tide-specific.

For future location promotion, activity coordinates become part of location validation. The user should not need a second activity-registration workflow after a location is added.

## 5. Activity Registry

Activities are registered once in a common registry. Fishing is the only enabled activity in Phase 1.

Conceptual structure:

```python
ACTIVITIES = {
    "fishing": {
        "enabled": True,
        "scorer": FishingScorer,
        "slug": "fishing",
        "requires": {...},
    },
    "surfing": {"enabled": False, ...},
    "beach": {"enabled": False, ...},
    "swimming": {"enabled": False, ...},
}
```

Generation loops over the location catalog and enabled activities rather than maintaining page lists manually:

```text
for each location in LOCATIONS
    for each enabled activity in ACTIVITIES
        normalize inputs
        score activity
        render activity page
```

Enabling a future activity therefore produces that activity for all catalog locations from the same pipeline, subject to data availability and indexability rules.

## 6. Separation of data collection, scoring, and rendering

The activity architecture has three independent layers:

### 6.1 Condition providers

Provider adapters obtain source data and normalize it into a provider-independent schema.

Phase 1 data policy:

- **Tides:** existing NOAA CO-OPS prediction cache.
- **Weather / wind / precipitation:** U.S. National Weather Service (NWS) official API.
- **Weather and coastal alerts:** NWS official active-alert API, queried for both shore and marine points where appropriate.
- **Marine conditions:** NWS marine grid / point forecast where structured marine values are available.
- **Water temperature:** NOAA CO-OPS observations when the relevant official station supports it; missing water temperature remains unknown.
- **Solar / lunar timing:** deterministic local calculation with tested astronomical functions; no AI API.

A third-party marine provider may be added only after its commercial-use and redistribution terms are explicitly verified. No unverified free API is part of Phase 1 production scoring.

### 6.2 Common Condition Snapshot

Providers write one normalized condition snapshot per location. This is shared by all activity scorers to avoid repeated API calls as additional activities are enabled.

Target storage:

`public/data/conditions/<location-slug>.json`

The snapshot contains source timestamps and provenance for every field. Missing data is represented as missing/unknown, never invented.

### 6.3 Activity scoring output

Each activity writes its own deterministic result:

`public/data/activities/fishing/<location-slug>.json`

The Fishing output contains:

- activity and location identifiers,
- input snapshot timestamp,
- scorer version,
- Today and Tomorrow scores,
- hourly component scores,
- best valid three-hour window,
- rating,
- confidence,
- safety state,
- active safety caps / hard stops,
- rule-based explanation reasons,
- data provenance references.

Keeping common raw conditions separate from activity results prevents duplicated weather/marine payloads when Surfing, Beach, and Swimming are later added.

## 7. Fishing Quality Score

Fishing is scored hourly before a daily score is selected. The quality model represents **general shore / pier / nearshore recreational fishing suitability**, not species-specific fishing.

Initial weights:

| Factor | Weight |
| --- | ---: |
| Tide movement / phase | 30% |
| Wind | 20% |
| Wave / nearshore sea state | 15% |
| Weather / precipitation | 15% |
| Time of day / light | 10% |
| Moon / Solunar | 5% |
| Water temperature | 5% |

Weights are configuration, not scattered constants. Future tuning changes the Fishing rules module, not the shared engine.

### 7.1 Tide factor

The Tide factor uses the existing NOAA high/low events and curve. It must not claim that tide-height change equals measured current velocity.

The generic Phase 1 model favors moving water and reduces the score near slack water. For each interval between adjacent official turning points, phase progress is calculated from 0 to 1 and a smooth movement potential is derived from the middle of the cycle, for example:

```text
movement_potential = sin(pi × phase_progress)
```

The component is then mapped into a bounded score. Rising and falling tides are treated symmetrically in Phase 1 because a nationwide species-agnostic engine does not have evidence to prefer one direction everywhere.

### 7.2 Wind factor

Wind scoring favors light to moderate conditions and declines nonlinearly as sustained wind and gusts increase. A starting rule table is:

| Sustained wind | Base quality |
| --- | ---: |
| 4–12 mph | 100 |
| 0–3 mph | 85 |
| 13–18 mph | 80 |
| 19–24 mph | 55 |
| 25–30 mph | 25 |
| >30 mph | 0 |

Gusts apply additional quality penalties and may activate Safety Gate caps independently of this quality score.

### 7.3 Wave factor

The Fishing quality factor favors manageable nearshore conditions. The starting generic band is intentionally conservative:

| Significant wave height | Base quality |
| --- | ---: |
| 1–3 ft | 100 |
| <1 ft | 85 |
| 3–5 ft | 75 |
| 5–7 ft | 45 |
| 7–9 ft | 20 |
| >9 ft | 0 |

Wave period modifies this factor and is also evaluated separately by the Safety Gate. This score is a generic shoreline planning heuristic, not a physical safety limit.

### 7.4 Weather factor

Cloud cover by itself should not materially penalize fishing. Precipitation likelihood and intensity reduce quality; thunder/lightning is handled by the Safety Gate rather than being allowed to average against favorable factors.

Starting precipitation-probability mapping:

| Probability | Base quality |
| --- | ---: |
| 0–20% | 100 |
| 21–40% | 75 |
| 41–60% | 50 |
| >60% | 30 |

Heavy rainfall can reduce this further.

### 7.5 Time-of-day factor

Dawn and dusk receive a modest general boost without making night or daytime fishing invalid:

- dawn/dusk window: highest score,
- normal daylight: good,
- twilight: good to very good,
- full night: reduced but not zero.

The exact window is derived from local solar times rather than a fixed clock time.

### 7.6 Moon / Solunar factor

Moon/Solunar remains a low-weight secondary factor. It must never dominate Tide, Wind, Wave, Weather, or Safety.

Phase 1 constrains its effect to a narrow range so uncertain biological assumptions cannot create large score swings. The public explanation describes it as a secondary timing factor, not a guarantee of fish activity.

### 7.7 Water-temperature factor

Water temperature has only 5% weight because ideal temperature varies by target species. Phase 1 uses it mainly to detect broad extremes rather than claiming one nationwide optimum.

If water temperature is unavailable, it is not guessed. The component receives a neutral-unknown treatment and confidence is lowered; its weight is not redistributed to other factors.

## 8. Missing-data behavior

Missing data must never make a location look artificially better.

Rules:

- Safety-critical data is never replaced with optimistic defaults.
- Missing optional quality data is not reweighted into the remaining factors.
- A missing optional factor uses an explicit neutral-unknown component and lowers confidence.
- Missing wave/marine safety information lowers the page to `Limited` unless an equivalent verified official field is available.
- Failure to retrieve active alert state is `Unavailable`, not “no alerts.”

This prevents a page with unknown sea state from receiving a top national rank simply because its remaining factors are favorable.

## 9. Safety Gate

The Safety Gate is separate from the Fishing Quality Score and always runs after quality scoring.

```text
Quality Score
    ↓
Safety penalties
    ↓
Safety score cap
    ↓
Hard-stop override
    ↓
Final Hourly Score / Status
```

General formula when no hard stop is active:

```text
final = min(quality - safety_penalties, safety_cap_if_any)
```

When a hard-stop condition applies:

```text
status = NOT RECOMMENDED
```

A raw quality score may still be stored internally for diagnostics, but the public page must never display it as the recommendation while a hard stop is active.

### 9.1 Safety precedence

1. Hard stop
2. Lowest active safety cap
3. Cumulative safety penalties
4. Quality score

Multiple hazards cannot cancel one another or be averaged away.

### 9.2 Official-alert hard stops

The initial hard-stop event map includes severe hazards relevant to shoreline access or immediate outdoor exposure, such as:

- Tornado Warning
- Hurricane Warning
- Tropical Storm Warning
- Storm Surge Warning
- Tsunami Warning
- Extreme Wind Warning
- Severe Thunderstorm Warning
- High Surf Warning
- Special Marine Warning when it covers the relevant nearshore point
- other NWS event names explicitly added to the tested hard-stop configuration

Coastal Flood Warning and Flash Flood Warning are treated conservatively when they affect the shore point or access area. Event handling is configuration-driven so wording and regional NWS products can be maintained without changing the engine.

A Rip Current Statement or equivalent explicit high-rip-current hazard receives a strong cap or hard stop according to the NWS product severity and text. Because Phase 1 combines shore and pier fishing into one general score, the public output remains conservative and explains the shoreline hazard rather than implying pier fishing is automatically safe.

### 9.3 Wind safety thresholds

The starting rule-based wind safety tiers are deliberately more conservative than the quality bands:

- sustained 25–29 mph or gust 35–39 mph: cap at 59,
- sustained 30–39 mph or gust 40–49 mph: cap at 39,
- sustained >=40 mph or gust >=50 mph: hard stop unless a stricter official warning already applies.

These are CoastalNow planning heuristics, not official boating criteria, and are documented as such.

### 9.4 Wave-exposure heuristic

Wave height is not evaluated alone. A configurable **exposure heuristic** combines significant wave height and period. It is intentionally not labeled “physical wave energy.”

Starting form:

```text
exposure_index = height_ft × sqrt(period_seconds / 8)
```

Initial tiers:

- <3.5: normal quality evaluation,
- 3.5–5.5: caution,
- 5.5–7.5: maximum 69,
- 7.5–9.5: maximum 39,
- >=9.5: hard stop / Not Recommended.

When coast bearing is known, strong onshore gusts can move the exposure one severity tier higher. If coast bearing is unavailable, no direction adjustment is invented.

All thresholds live in configuration and require fixture tests at each boundary before production changes.

### 9.5 Thunder / lightning

Active thunderstorm warnings are hard stops. When structured NWS hourly thunder probability is available, elevated thunder risk can cap the affected hours even before a warning exists. If that structured field is unavailable, the engine relies on official alerts and forecast condition text rather than inventing a probability.

### 9.6 Other hazards

Small Craft Advisories, dense fog, heavy rain, excessive heat/cold, coastal flooding, and similar products do not all produce the same result. They are mapped by relevance to shore/pier fishing into:

- information only,
- penalty,
- score cap,
- hard stop.

The mapping is explicit, versioned, and unit-tested.

## 10. Fishing ratings

Normal quality ratings use:

- 90–100: Excellent
- 75–89: Good
- 60–74: Fair
- 40–59: Poor
- 0–39: Unfavorable

`NOT RECOMMENDED` is reserved for Safety Gate hard stops and is not simply another quality band.

## 11. Hourly scoring and the daily score

The engine scores each usable hour independently for Today and Tomorrow.

The user-facing daily score represents the best **safe, continuous three-hour fishing window**, not a simple 24-hour average.

For each candidate three-hour window:

- all three hours must have valid safety state,
- no hour may be hard-stopped or unavailable,
- a window confidence is derived from its three hourly confidences,
- score continuity is favored using:

```text
window_score = 0.70 × mean(hourly_final_scores)
             + 0.30 × min(hourly_final_scores)
```

This prevents one excellent hour from hiding a poor hour inside the recommended window.

The highest valid three-hour window becomes:

- Today’s Fishing Score,
- Today’s rating,
- Best Fishing Time.

Tomorrow is calculated independently with the same rules.

If no valid three-hour window exists, the day is shown as unavailable or Not Recommended depending on the cause.

## 12. Confidence model

Confidence describes input completeness, not certainty about catching fish.

### High

All critical inputs for the selected window are fresh and available:

- tide,
- wind,
- weather,
- wave/marine conditions,
- active alerts.

### Medium

All safety-critical inputs are available, but one secondary input such as water temperature or moon detail is missing or degraded.

### Limited

A major quality/safety context field such as structured marine wave data is missing, but enough information remains to render an informational page. Limited pages are excluded from top national rankings and are `noindex,follow` until sufficient data becomes available.

### Unavailable

A critical safety input is unavailable, including active-alert retrieval, or core tide/weather/wind data cannot be validated. No normal Fishing Score is published and the page is excluded from ranking and indexing.

## 13. Rule-based explanations

No AI API is used for score generation or explanation text.

Explanations are composed from deterministic rules tied to component scores and changes through the day, for example:

- favorable tide movement,
- light wind,
- manageable wave conditions,
- worsening afternoon gusts,
- active coastal hazard,
- missing marine observations.

The explanation layer receives structured reason codes from the scorer and maps them to approved sentence fragments. The same inputs therefore produce the same score and the same explanation.

## 14. National Fishing hub

URL: `/fishing/`

Purpose: answer activity-first discovery intent rather than act as a flat directory.

Required sections:

1. Hero: `Best Fishing Conditions in the U.S. Today`
2. Scope note: shore / pier / nearshore recreational fishing
3. Today / Tomorrow switch
4. Top Locations Today
5. #1 location explanation
6. Excellent / Good / Fair groups
7. Poor / Unfavorable group
8. Not Recommended safety group
9. Limited / Unavailable data group
10. Methodology / safety disclaimer

Ranking cards show:

- location and state,
- Fishing Score,
- rating,
- Best Fishing Time,
- one or two top reason codes rendered as short text,
- Confidence.

Only High and Medium confidence locations are eligible for the primary numerical ranking. Limited and Unavailable locations remain visible in separate status groups but cannot rank above fully evaluated locations.

Every ranked location links to its location Fishing page.

`This Weekend` is intentionally excluded from Phase 1 UI. The data contracts should not prevent adding it later.

## 15. Location Fishing page

URL pattern:

`/tides/<state-slug>/<location-slug>/fishing/`

Example:

`/tides/california/san-diego/fishing/`

Title pattern:

`San Diego Fishing Conditions Today | CoastalNow`

H1 pattern:

`San Diego Fishing Conditions Today`

Breadcrumb:

`Home → California → San Diego → Fishing`

Required page hierarchy:

1. Safety alert strip, when applicable, above recommendation content.
2. Fishing Score and rating.
3. Best Fishing Time.
4. Confidence.
5. Hour-by-hour Fishing Score timeline.
6. `Why this score?` factor breakdown.
7. Today / Tomorrow outlook.
8. Fishing-relevant tide summary.
9. Wind / wave / weather summary.
10. Rule-based reasons and expected deterioration/improvement.
11. Link to detailed parent tide page.
12. Link back to national Fishing hub.
13. Future sibling activity links when those activities become enabled.
14. Clear safety and methodology disclaimer.

The Fishing page must not duplicate the full tide page. Detailed tide tables and charts remain on the parent Tide page; Fishing uses only the tide information needed for the activity decision.

## 16. Bidirectional navigation

The internal-link graph must support both discovery directions:

```text
/fishing/
  ↓
/tides/california/san-diego/fishing/
  ↓
/tides/california/san-diego/
  ↓
future sibling activities
  ↓
future /surfing/, /beach/, /swimming/
```

The existing location Tide page receives a generated Activities section. In Phase 1 it contains Fishing and its current score/status.

The main homepage receives `Explore by activity` alongside the existing state-based discovery. In Phase 1 this contains Fishing. Future activity cards are generated from the Activity Registry.

## 17. SEO and indexability

Existing indexed URL behavior is preserved.

Fishing adds:

- `/fishing/`, and
- one generated Fishing URL per catalog location.

A Fishing location page is `index,follow` only when the latest output is High or Medium confidence and contains a real computed Today result. Limited or Unavailable pages use `noindex,follow`.

The sitemap includes:

- all existing indexable URLs,
- `/fishing/`,
- only indexable location Fishing pages.

As a result, page count can grow automatically with location count without exposing thin or unverified activity pages to search engines.

Canonical URLs always use `https://coastalnowtides.com`.

## 18. Refresh and caching strategy

Tide predictions remain on the existing NOAA refresh cycle. Activity conditions run on a separate **three-hour schedule** because wind, weather, alerts, and marine conditions change more rapidly.

Activity refresh sequence:

1. load current location catalog,
2. load verified tide caches,
3. fetch NWS shore weather/grid data,
4. fetch NWS marine conditions,
5. fetch active alerts for shore and marine points,
6. fetch optional NOAA water temperature where supported,
7. calculate solar/lunar fields,
8. write normalized condition snapshots,
9. run all enabled activity scorers,
10. write activity result JSON,
11. render all activity location pages,
12. render all activity hubs,
13. update homepage activity links and parent-location activity links,
14. rebuild sitemap and robots artifacts,
15. run regression tests,
16. commit generated output only if validation passes.

### Cache policy

- Fresh validated provider response: use it.
- Temporary provider failure with recent validated cache: use cache, mark stale source age, and lower confidence when appropriate.
- Cache too old for a safe decision: do not calculate a normal score.
- Alert API failure: never use a previous “no alert” result as proof that the location is currently safe. The safety state becomes Unavailable unless a recent alert cache is explicitly within a conservative freshness threshold.

Freshness thresholds are configuration and must be tested.

## 19. Automatic location-promotion integration

The existing promotion workflow remains the location-entry point. It will be extended rather than replaced.

After a location is validated and its Tide page is generated, the workflow must:

1. validate `activity.shore_point` and `activity.marine_point`,
2. collect an initial common condition snapshot,
3. run all enabled activity scorers,
4. render all activity pages for the promoted location,
5. rebuild activity hubs,
6. rebuild homepage/state/location links,
7. rebuild sitemap,
8. run activity and existing Tide/SEO regressions,
9. include generated activity output in the same promotion PR.

The important invariant is tested explicitly:

> A promoted location automatically appears in every enabled activity pipeline without a separate activity request.

If an activity cannot produce an indexable score due to provider coverage, the page is still generated with an explicit Limited/Unavailable state and `noindex,follow`; the Tide promotion itself does not silently fabricate activity data.

## 20. Proposed module boundaries

The target structure is intentionally modular:

```text
src/
  activities/
    registry.py

    conditions/
      providers/
        nws.py
        noaa.py
      astronomy.py
      snapshot.py
      validation.py

    scoring/
      engine.py
      safety.py
      fishing.py

    rendering/
      location_page.py
      hub_page.py
      links.py

  templates/
    activity-location.html
    activity-hub.html
```

Responsibilities:

- `registry.py`: enabled activities and requirements.
- provider adapters: HTTP/source-specific parsing only.
- `snapshot.py`: normalized provider-independent condition model.
- `engine.py`: generic weighted scoring and best-window mechanics.
- `safety.py`: generic cap/hard-stop framework and hazard precedence.
- `fishing.py`: Fishing weights, quality functions, and Fishing-specific hazard mapping.
- renderers: HTML only; no scoring logic.

The existing Tide generator should not accumulate Fishing-specific code.

## 21. Testing requirements

Implementation follows test-driven development. At minimum, Phase 1 requires tests for:

### Scoring

- every component boundary,
- weights sum correctly,
- missing optional fields do not increase the score,
- missing critical fields cannot produce a normal score,
- window score uses 70% mean + 30% minimum,
- best window excludes unsafe hours,
- Today and Tomorrow are independent.

### Safety

- each hard-stop alert event,
- score-cap precedence,
- multiple hazards choose the strictest cap,
- wind boundary values,
- wave-exposure boundary values,
- alert API failure is never interpreted as no alert,
- hard-stop output cannot render `Excellent`, `Good`, or another normal recommendation.

### Data

- provider payload validation,
- stale-cache behavior,
- provenance timestamps,
- NOAA/NWS error handling,
- no fabricated values.

### Rendering and SEO

- `/fishing/` exists,
- every eligible catalog location has a Fishing URL,
- parent Tide page links to Fishing,
- Fishing page links to parent Tide page and national hub,
- breadcrumb and canonical are correct,
- High/Medium pages are indexable,
- Limited/Unavailable pages are noindex,
- sitemap contains only indexable activity URLs,
- existing 51 location URLs remain byte-for-byte path-compatible.

### Automatic expansion invariant

A synthetic new location added to the test catalog must automatically produce:

- its existing-style Tide path,
- its Fishing path,
- its Fishing hub entry/status,
- bidirectional internal links,
- sitemap inclusion when indexable.

The test must not contain the number 51 as an expected permanent site size.

When a second activity is enabled in a fixture, the same synthetic location must automatically receive both activities. This proves the architecture is truly registry-driven rather than Fishing-specific.

## 22. Deployment strategy

Fishing should be introduced as an additive change on a feature branch and merged only after:

1. all existing Tide and SEO regressions still pass,
2. all Fishing scorer/safety tests pass,
3. all 51 current locations have validated activity geographic metadata,
4. activity data generation has been exercised against all current locations,
5. generated pages have no broken internal links,
6. sitemap changes contain only additive intended URLs,
7. no existing location path has changed,
8. Cloudflare preview deployment is checked before production merge.

The initial release may have fewer than 51 indexable Fishing pages if official marine/safety data is insufficient at some locations. This is preferable to publishing thin or falsely confident pages.

## 23. Future activities

The shared architecture must allow future activity modules to define their own:

- factor weights,
- component scoring functions,
- critical data requirements,
- hazard penalties,
- score caps,
- hard-stop rules,
- rating labels,
- explanation fragments.

Expected future emphasis:

- Surfing: wave height/period/direction, wind direction, tide, water temperature.
- Beach: air/water temperature, rain, wind, wave height, UV.
- Swimming: water temperature, wave height, wind, weather, and a substantially stricter safety policy.

No future activity should require a second geographic catalog or manual per-location page list.

## 24. Success criteria for Phase 1

Phase 1 is complete when:

- existing CoastalNow Tide URLs and indexing behavior remain intact,
- `/fishing/` is a real comparison/discovery page,
- every catalog location automatically receives a Fishing page/status,
- eligible locations can be ranked Today and Tomorrow,
- Fishing results are deterministic and reproducible without AI APIs,
- Safety Gate overrides favorable conditions when required,
- missing safety data fails conservatively,
- a newly promoted location automatically flows into Fishing without separate manual setup,
- the architecture can add Surfing/Beach/Swimming by registering new scorers rather than rewriting the site.
