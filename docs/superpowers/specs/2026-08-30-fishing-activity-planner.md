# CoastalNow Fishing Activity Planner — Design Specification

Date: 2026-08-30
Status: Conversation design approved; written specification pending final user review
Scope: Phase 1 Fishing only, with shared foundations for future Surfing, Beach, and Swimming

## 1. Product direction

CoastalNow will expand from a tide-only site into a **Coastal Conditions & Activity Planner** for U.S. coastal locations. The site must answer two distinct search and navigation intents:

1. **Location-first:** “Is fishing good in San Diego today?”
2. **Activity-first:** “Where in the U.S. has the best fishing conditions today?”

The existing tide site remains intact. Phase 1 adds Fishing as a new activity layer without moving, renaming, redirecting, or otherwise changing any existing indexed location URL.

Phase 1 Fishing is explicitly **shore / pier / nearshore recreational fishing conditions**. Offshore or boat-fishing is out of scope because its weather, sea-state, and safety thresholds differ materially.

The Fishing Score is a planning and comparison metric, not a safety guarantee. Official warnings, closures, signs, lifeguards, harbor authorities, and emergency guidance always take priority.

## 2. URL and SEO constraints

Existing URLs remain exactly as they are, for example:

- `/tides/california/san-diego/`

Fishing adds only:

- national hub: `/fishing/`
- location Fishing page: `/tides/california/san-diego/fishing/`

Future activities follow the same additive pattern:

- `/surfing/` and `/tides/.../surfing/`
- `/beach/` and `/tides/.../beach/`
- `/swimming/` and `/tides/.../swimming/`

No existing page relocation, directory reorganization, or redirect is part of this project.

New indexable pages receive canonical URLs, BreadcrumbList structured data, internal links, and sitemap entries. Activity pages with insufficient critical data are generated for continuity but remain `noindex,follow` until they meet the data-quality threshold.

## 3. Location catalog is the source of truth

The existing location catalog remains the single source of truth for site geography. No separate list of Fishing locations is maintained.

The core invariant is:

> **Adding one CoastalNow location automatically expands every enabled activity.**

```text
LOCATIONS
  ├── Tide
  ├── Fishing
  ├── Surfing     (future)
  ├── Beach       (future)
  └── Swimming    (future)
```

A future location such as Galveston is added once. The pipelines then automatically:

1. create or refresh Tide output,
2. collect common coastal-condition data,
3. run every enabled activity scorer,
4. create `/tides/texas/galveston/fishing/`,
5. add the location to `/fishing/` when ranking eligibility is satisfied,
6. create bidirectional internal links,
7. add indexable activity URLs to the sitemap.

No later “create Galveston Fishing” action is required.

Hard-coded references to “51 locations” in generated UI must be replaced with catalog-derived counts.

## 4. Activity geographic metadata

NOAA tide-station coordinates must not be treated as the location itself, especially for Nearby NOAA locations. The location catalog is extended with activity-specific geography without changing existing Tide metadata:

```json
{
  "activity": {
    "shore_point": {"latitude": 0.0, "longitude": 0.0},
    "marine_point": {"latitude": 0.0, "longitude": 0.0},
    "coast_bearing": 270
  }
}
```

Definitions:

- `shore_point`: representative shoreline / pier point for local weather and shore alerts.
- `marine_point`: representative nearshore point for marine forecasts and marine alerts.
- `coast_bearing`: optional **seaward-facing bearing in degrees clockwise from true north**. It is used only for directional exposure rules such as onshore wind. It is never guessed when missing.

Existing NOAA station identifiers and station coordinates remain Tide-specific.

Future location promotion validates activity coordinates as part of adding the location, so the user never needs a separate activity-registration workflow.

## 5. Activity Registry

Activities are registered once in a common registry. Fishing is the only enabled activity in Phase 1.

```python
ACTIVITIES = {
    "fishing": {
        "enabled": True,
        "slug": "fishing",
        "scorer": FishingScorer,
        "requires": {...},
    },
    "surfing": {"enabled": False, ...},
    "beach": {"enabled": False, ...},
    "swimming": {"enabled": False, ...},
}
```

Generation is registry-driven:

```text
for location in LOCATIONS
    for activity in ENABLED_ACTIVITIES
        obtain normalized conditions
        score activity
        render activity page
```

Enabling a future activity therefore expands that activity to all catalog locations without maintaining a second geographic list.

## 6. Data architecture

### 6.1 Provider adapters

Provider-specific HTTP and parsing code is isolated from scoring.

Phase 1 sources:

- **Tides:** existing NOAA CO-OPS prediction cache.
- **Weather / wind / precipitation:** U.S. National Weather Service (NWS) official API.
- **Alerts:** NWS official active alerts for relevant shore and marine zones/points.
- **Marine conditions:** NWS marine grid / point forecast where structured values are available.
- **Water temperature:** NOAA CO-OPS observation where a relevant official station supports it.
- **Solar / lunar timing:** deterministic local calculation with tested astronomical functions; no AI API.

A third-party marine provider may be added only after commercial-use and redistribution rights are explicitly verified. No unverified free API is part of Phase 1 production scoring.

Provider code should cache and deduplicate NWS metadata, forecast-grid, and alert-zone requests so location growth does not cause unnecessary repeated calls. Alert retrieval should prefer reusable NWS zone/grid identifiers where that preserves correct geographic matching.

### 6.2 Common Condition Snapshot

One normalized snapshot is written per location:

`public/data/conditions/<location-slug>.json`

It contains local-time hourly values plus source timestamps and provenance. Missing data is `unknown`; it is never invented.

### 6.3 Activity result

Fishing writes:

`public/data/activities/fishing/<location-slug>.json`

The result includes:

- location/activity IDs,
- input snapshot timestamp,
- scorer version,
- Today and Tomorrow result,
- hourly component scores,
- best three-hour window,
- rating and confidence,
- Safety Gate state,
- caps / hard stops,
- rule-based reason codes,
- source provenance references.

Common raw conditions remain separate so later activities reuse the same provider calls.

## 7. Fishing Quality Score

Scoring happens in each location’s **local timezone**. “Today” and “Tomorrow” always mean local calendar days for that location.

Initial hourly quality weights:

| Factor | Weight |
| --- | ---: |
| Tide movement / phase | 30% |
| Wind | 20% |
| Wave / nearshore sea state | 15% |
| Weather / precipitation | 15% |
| Time of day / light | 10% |
| Moon / Solunar | 5% |
| Water temperature | 5% |

Weights and thresholds live in Fishing configuration, not the shared engine.

### 7.1 Tide

Use existing NOAA high/low events and tide curve. Do not describe tide-height change as measured current velocity.

Between adjacent official turning points, compute phase progress from 0 to 1 and favor moving water using a smooth function such as:

```text
movement_potential = sin(pi × phase_progress)
```

Rising and falling tides are treated symmetrically in Phase 1 because the score is species-agnostic and nationwide.

### 7.2 Wind quality

Starting sustained-wind quality bands:

| Wind | Quality |
| --- | ---: |
| 4–12 mph | 100 |
| 0–3 mph | 85 |
| 13–18 mph | 80 |
| 19–24 mph | 55 |
| 25–30 mph | 25 |
| >30 mph | 0 |

Gusts can reduce quality and independently activate Safety Gate caps.

### 7.3 Wave quality

Starting significant-wave-height quality bands:

| Height | Quality |
| --- | ---: |
| 1–3 ft | 100 |
| <1 ft | 85 |
| 3–5 ft | 75 |
| 5–7 ft | 45 |
| 7–9 ft | 20 |
| >9 ft | 0 |

Wave period modifies quality and is evaluated again by the Safety Gate. These are CoastalNow generic planning heuristics, not official safety limits.

### 7.4 Weather quality

Cloud cover alone is not a major penalty. Starting precipitation-probability mapping:

| Probability | Quality |
| --- | ---: |
| 0–20% | 100 |
| 21–40% | 75 |
| 41–60% | 50 |
| >60% | 30 |

Heavy rain can reduce it further. Thunder/lightning is handled by Safety Gate, not averaged against favorable quality factors.

### 7.5 Time of day

Local dawn/dusk receive a modest boost; normal daylight remains good; full night is reduced but not zero. Solar times are calculated per location rather than using fixed clock windows.

### 7.6 Moon / Solunar

This remains a low-weight secondary factor. Its effect is intentionally narrow so uncertain biological assumptions cannot dominate weather, waves, tides, or safety.

### 7.7 Water temperature

Water temperature has only 5% weight because useful ranges vary by target species. It detects broad extremes rather than claiming a nationwide optimum.

## 8. Missing data

Missing data must never improve a location artificially.

Rules:

- safety-critical data never receives optimistic defaults,
- weights are never redistributed because an input is missing,
- an optional unknown quality factor uses a fixed **neutral-unknown score of 50** and lowers confidence,
- missing marine/wave safety context lowers the page to `Limited` unless an equivalent verified official source is available,
- alert retrieval failure is `Unavailable`, never “no alerts.”

Water temperature and detailed Solunar data are optional. Tide, wind, weather, active alert state, and sufficient marine context for shoreline risk are critical to normal ranking eligibility.

## 9. Safety Gate

Safety is evaluated separately after Fishing Quality Score:

```text
Quality Score
    ↓
Safety penalties
    ↓
Safety cap
    ↓
Hard-stop override
    ↓
Final Hourly Score / Status
```

When no hard stop is active:

```text
final = min(quality - penalties, active_safety_cap)
```

If no cap exists, the cap is effectively 100.

When a hard stop applies:

```text
status = NOT RECOMMENDED
```

The raw quality score may remain in diagnostic JSON but must not be presented as the public recommendation during a hard stop.

Safety precedence:

1. hard stop,
2. lowest active cap,
3. cumulative penalties,
4. quality score.

Hazards never average one another away.

### 9.1 Official-alert hard stops

The initial configuration includes severe shoreline/outdoor hazards such as:

- Tornado Warning,
- Hurricane Warning,
- Tropical Storm Warning,
- Storm Surge Warning,
- Tsunami Warning,
- Extreme Wind Warning,
- Severe Thunderstorm Warning,
- High Surf Warning,
- Special Marine Warning when it affects the relevant nearshore area.

Coastal Flood Warning and Flash Flood Warning are handled conservatively when they affect the shore/access area.

A Rip Current Statement or equivalent explicit high-rip-current hazard receives a strong cap or hard stop according to the official product severity/text. Because the Phase 1 score combines shore and pier use, public messaging stays conservative and does not imply pier fishing is automatically safe.

The event mapping is configuration-driven and unit-tested so changing NWS terminology does not require rewriting the engine.

### 9.2 Wind safety

Starting heuristic tiers:

- sustained 25–29 mph or gust 35–39 mph → cap 59,
- sustained 30–39 mph or gust 40–49 mph → cap 39,
- sustained >=40 mph or gust >=50 mph → hard stop unless an even stricter official warning already controls the state.

These are CoastalNow planning thresholds, not official boating criteria.

### 9.3 Wave-exposure safety

Height is not evaluated alone. Use a configurable **exposure heuristic** that is explicitly not described as physical wave energy:

```text
exposure_index = height_ft × sqrt(period_seconds / 8)
```

Starting tiers:

- <3.5 → normal evaluation,
- 3.5–5.5 → caution,
- 5.5–7.5 → cap 69,
- 7.5–9.5 → cap 39,
- >=9.5 → hard stop / Not Recommended.

When `coast_bearing` exists, sufficiently strong onshore gusts can increase exposure by one severity tier. Missing bearing never triggers a guessed directional adjustment.

Every threshold is configuration and receives boundary fixtures.

### 9.4 Thunder / lightning

Active severe-thunderstorm warnings are hard stops. When structured NWS hourly thunder probability is available, elevated risk can cap affected hours before a warning exists. If that field is unavailable, the engine may use official alert state and explicit forecast-condition text but must not invent a thunder probability.

### 9.5 Other hazards

Small Craft Advisories, dense fog, heavy rain, excessive temperature, coastal flooding, and similar products are explicitly mapped to one of:

- information only,
- penalty,
- score cap,
- hard stop.

No generic “all advisories subtract N points” rule is allowed.

## 10. Ratings

Normal quality ratings:

- 90–100: Excellent
- 75–89: Good
- 60–74: Fair
- 40–59: Poor
- 0–39: Unfavorable

`NOT RECOMMENDED` is reserved for Safety Gate hard stops.

## 11. Hourly and daily score

The engine evaluates hourly conditions for Today and Tomorrow.

The daily user-facing score is the best **safe continuous three-hour window**, not a 24-hour average.

A candidate window is valid only when all three hours have usable safety state and none is hard-stopped or unavailable.

```text
window_score = 0.70 × mean(hourly final scores)
             + 0.30 × minimum(hourly final scores)
```

The minimum component penalizes a weak hour inside an otherwise good window.

The highest valid window becomes:

- Fishing Score,
- rating,
- Best Fishing Time.

Tomorrow is calculated independently. If no valid three-hour window exists, the day is shown as Unavailable or Not Recommended depending on cause.

## 12. Confidence

Confidence measures **input completeness**, not the probability of catching fish.

### High

Fresh Tide, Wind, Weather, Wave/Marine, and Alert inputs are all available for the chosen window, with optional supporting inputs also available.

### Medium

All safety-critical inputs are available, but one or more secondary inputs such as water temperature or detailed moon data are missing/degraded.

### Limited

Important marine/wave context is insufficient for normal national comparison, but enough data exists to render an informational page. Limited pages are excluded from primary ranking and use `noindex,follow`.

### Unavailable

Alert state or another critical safety/core input cannot be validated. No normal Fishing Score is published; the page is excluded from ranking and indexing.

## 13. Rule-based explanations

No AI API is used for scoring or explanation text.

Scorers emit structured reason codes, for example:

- favorable tide movement,
- light wind,
- manageable sea state,
- worsening afternoon gusts,
- active coastal hazard,
- unavailable marine context.

A deterministic explanation layer maps these codes to approved sentence fragments. Same inputs produce the same score and explanation.

## 14. National Fishing hub

URL: `/fishing/`

Purpose: answer “where is fishing good today?” rather than provide a flat list.

Required sections:

1. `Best Fishing Conditions in the U.S. Today`
2. shore / pier / nearshore scope note
3. Today / Tomorrow control
4. Top Locations Today
5. explanation for the #1 location
6. Excellent / Good / Fair groups
7. Poor / Unfavorable group
8. Not Recommended safety group
9. Limited / Unavailable data group
10. methodology and safety disclaimer

Ranking cards show location/state, score, rating, Best Fishing Time, short reasons, and Confidence.

Only High and Medium confidence locations can enter the primary numerical ranking. Limited/Unavailable locations remain visible in separate status groups.

`This Weekend` is intentionally out of Phase 1 UI, while data contracts remain extensible.

## 15. Location Fishing page

Pattern:

`/tides/<state>/<location>/fishing/`

Example:

`/tides/california/san-diego/fishing/`

Title: `San Diego Fishing Conditions Today | CoastalNow`

H1: `San Diego Fishing Conditions Today`

Breadcrumb: `Home → California → San Diego → Fishing`

Required hierarchy:

1. safety alert strip when applicable,
2. Fishing Score / rating,
3. Best Fishing Time,
4. Confidence,
5. hourly Fishing Score timeline,
6. `Why this score?` factor breakdown,
7. Today / Tomorrow outlook,
8. fishing-relevant Tide summary,
9. Wind / Wave / Weather summary,
10. deterministic reasons,
11. link to parent Tide page,
12. link to `/fishing/`,
13. future sibling activity links when enabled,
14. safety/methodology disclaimer.

The Fishing page must not duplicate the full Tide forecast. Detailed Tide tables/charts remain on the parent page.

## 16. Bidirectional navigation

```text
/fishing/
  ↓
/tides/california/san-diego/fishing/
  ↓
/tides/california/san-diego/
  ↓
future sibling activity pages
  ↓
future activity hubs
```

Existing location pages gain a generated Activities section. Phase 1 shows Fishing and its current score/status.

The homepage gains `Explore by activity` alongside state discovery. Cards are generated from Activity Registry so future activities appear automatically.

## 17. SEO and indexability

Existing URL/indexing behavior is preserved.

Fishing adds `/fishing/` plus one generated Fishing URL per catalog location.

A location Fishing page is `index,follow` only when it has a real Today result with High or Medium confidence. Limited and Unavailable pages use `noindex,follow`.

The sitemap includes existing indexable URLs, `/fishing/`, and only indexable location Fishing URLs. Canonicals always use `https://coastalnowtides.com`.

## 18. Refresh and fail-safe policy

Tide predictions keep their current NOAA refresh cycle.

### Full condition refresh

Weather, wind, marine conditions, optional water temperature, solar/lunar fields, scoring, hubs, and pages refresh every **3 hours**.

### Safety alert refresh

Active NWS safety alerts refresh **hourly**, independently of the full three-hour condition cycle. A newly detected hard stop or safety cap must be able to update the affected activity page/hub without waiting for the next full forecast refresh.

At scale, the alert adapter should group/collapse requests by reusable NWS zone or grid identifiers when correct, rather than blindly issuing two independent alert queries per location forever.

### Full refresh sequence

1. load catalog,
2. load verified Tide caches,
3. fetch NWS shore weather/grid data,
4. fetch NWS marine conditions,
5. obtain current active alerts,
6. fetch optional NOAA water temperature,
7. calculate solar/lunar fields,
8. write Condition Snapshots,
9. run all enabled activity scorers,
10. write activity results,
11. render location activity pages and hubs,
12. rebuild homepage/location activity links,
13. rebuild sitemap/robots,
14. run regressions,
15. commit only validated output.

### Cache rules

- fresh validated data → use,
- temporary provider failure with sufficiently recent verified cache → use cache and downgrade confidence if appropriate,
- data older than configured safe freshness → no normal score,
- Alert API failure → never infer “no alert.”

The initial alert-cache maximum age for publishing a normal safety state is **2 hours**. Beyond that, alert state becomes Unavailable until a fresh check succeeds. Full weather/marine forecast freshness for High/Medium eligibility is **6 hours**; older validated forecasts may render stale informational content but cannot remain High/Medium.

These freshness values are configuration and receive boundary tests.

## 19. Automatic location-promotion integration

The existing location promotion workflow is extended, not replaced.

After Tide validation/generation it must:

1. validate shore/marine activity points,
2. collect initial common conditions,
3. run every enabled activity scorer,
4. render every enabled activity page for the new location,
5. rebuild activity hubs,
6. rebuild homepage/location links,
7. rebuild sitemap,
8. run existing and activity regressions,
9. include generated activity output in the same promotion PR.

Invariant:

> A promoted location automatically enters every enabled activity pipeline without a separate activity request.

If an activity cannot produce a normal result because provider coverage is insufficient, its page is still generated as Limited/Unavailable with `noindex,follow`. Tide promotion never fabricates activity data.

## 20. Module boundaries

Target structure:

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

- registry → enabled activities/requirements,
- provider adapters → source HTTP/parsing only,
- snapshot → normalized provider-independent condition schema,
- engine → generic weighted scoring and best-window mechanics,
- safety → generic cap/hard-stop framework and precedence,
- fishing → Fishing weights, quality functions, hazard mapping,
- renderers → HTML only, no scoring logic.

Existing Tide generator must not accumulate Fishing-specific scoring code.

## 21. Tests

Implementation uses TDD.

Required test classes include:

### Scoring

- every component threshold boundary,
- weight correctness,
- missing optional data cannot raise score,
- critical missing data cannot publish a normal score,
- neutral-unknown optional score is 50,
- best-window formula is 70% mean + 30% minimum,
- unsafe hours are excluded,
- Today/Tomorrow use each location’s local date.

### Safety

- every hard-stop event,
- strictest cap wins,
- multiple hazards never offset,
- wind boundaries,
- wave-exposure boundaries,
- alert failure never means “no alerts,”
- alert freshness >2 hours prevents normal safety state,
- hard stop cannot render Excellent/Good/Fair/Poor/Unfavorable as recommendation.

### Data/cache

- provider validation,
- provenance/timestamps,
- no fabricated values,
- stale cache handling,
- >6-hour full forecast cannot remain High/Medium.

### Rendering/SEO

- `/fishing/` exists,
- every catalog location receives an activity page/status,
- parent Tide ↔ Fishing links are bidirectional,
- hub links to location Fishing pages,
- canonical/breadcrumb are correct,
- High/Medium → indexable,
- Limited/Unavailable → noindex,
- sitemap contains only indexable activity URLs,
- existing location paths are unchanged.

### Automatic expansion invariant

A synthetic new location added to a fixture must automatically produce:

- its standard Tide path,
- its Fishing path,
- hub entry/status,
- bidirectional links,
- sitemap entry when indexable.

The test must not assume permanent site size 51.

When a second activity is enabled in a fixture, the same synthetic location must automatically receive both activity paths. This proves registry-driven expansion rather than Fishing-specific page lists.

## 22. Deployment strategy

Fishing is additive and ships only after:

1. existing Tide/SEO regressions pass,
2. Fishing scorer/safety tests pass,
3. all current locations have validated activity geography,
4. all current locations have been exercised through data generation,
5. generated internal links are valid,
6. sitemap changes are only the intended additions,
7. no existing location path changes,
8. Cloudflare preview is checked before production merge.

The initial release may contain fewer than all catalog locations in Google’s index if some official marine/safety data is insufficient. That is preferable to thin or falsely confident pages.

## 23. Future activities

Each future activity supplies its own:

- weights,
- component functions,
- critical input requirements,
- penalties,
- caps,
- hard stops,
- ratings,
- explanation fragments.

Expected emphasis:

- Surfing → wave height/period/direction, wind direction, Tide, water temperature.
- Beach → air/water temperature, rain, wind, wave height, UV.
- Swimming → water temperature, wave height, wind, weather, with a substantially stricter Safety Gate.

No future activity gets a second location catalog or manual per-location page list.

## 24. Phase 1 success criteria

Phase 1 is complete when:

- existing Tide URLs/indexing remain intact,
- `/fishing/` is a real comparison/discovery page,
- every catalog location automatically receives Fishing output/status,
- eligible locations can be ranked for Today and Tomorrow,
- scoring is deterministic and reproducible without AI APIs,
- Safety Gate can override otherwise excellent conditions,
- missing safety data fails conservatively,
- a new promoted location automatically enters Fishing with no separate setup,
- the architecture can add Surfing/Beach/Swimming by registering new scorers instead of rewriting geography or page generation.
