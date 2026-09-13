# CoastalNow GSC Cluster Expansion Design

Date: 2026-09-13

## Goal

Use the first meaningful Google Search Console signals to improve CoastalNow without broad nationwide expansion. The next release should strengthen existing indexed pages, turn California and Florida state directories into search landing pages, add one controlled 12-location expansion batch, improve local internal linking, and create a repeatable Search Console comparison workflow.

The long-term hierarchy remains `Country → State → Location`. This release does not change existing public URL paths or canonical URLs.

## Current signals driving the work

Today’s Search Console summary supplied by the user shows:

- 15 valid indexed pages.
- 11 location pages with actual search impressions.
- California state directory is currently the strongest page with 27 impressions and 2 clicks.
- Oceanside: 15 impressions, average position 9.87.
- Miami Beach: 8 impressions, average position 4.62.
- Clearwater Beach: 10 impressions.
- Topsail Beach: 8 impressions.
- Ocean City, MD: 6 impressions.
- Los Angeles: average position 30.75.
- Huntington Beach has a small sample but has recorded position 1.
- Query patterns are beginning to include location + `tide`, `high tide`, `tide chart`, and `tide schedule`.

Existing repository state also matters:

- Many of the initially suggested California and Florida candidates are already Live NOAA locations.
- California currently has 13 generated locations and Florida has 12.
- State pages are still simple location-list directories.
- Location metadata is generic and nearby links are currently initialized as an empty list.
- Huntington Beach alone has the answer-first `NEXT TIDE` pilot.
- Sitemap policy already includes state pages and Live NOAA location pages while excluding Preview location pages.

## Delivery strategy

The implementation should be split into two production PRs after this design is approved.

### PR A — Existing-page audit and SEO foundation

This PR changes no location count. It establishes the structure that the expansion will use.

Scope:

1. Audit existing indexed-but-no-impression pages.
2. Strengthen California and Florida state pages.
3. Improve the reusable location SEO template.
4. Expand answer-first tide presentation from the Huntington pilot to Live NOAA location pages.
5. Generate nearby-location links automatically.
6. Add Search Console snapshot/report tooling.
7. Add regression coverage for all new SEO rules.

### PR B — Controlled 12-location expansion

This PR adds 12 genuinely new location URLs after NOAA station validation.

Southern California:

1. Long Beach
2. Ventura
3. Santa Barbara
4. Redondo Beach
5. Dana Point
6. Seal Beach

Florida:

1. Key Biscayne
2. West Palm Beach
3. Fort Myers Beach
4. Pompano Beach
5. Marco Island
6. Sarasota

A candidate is promoted to Live NOAA only if its configured NOAA source returns valid seven-day high/low data through the existing production generation path. If a local station is unavailable and a nearby station is used, the existing `nearby-noaa` disclosure model must be used with an explicit station name and distance. If a candidate cannot pass production validation, it is replaced by another location in the same cluster rather than shipped as a broken or misleading Live page.

## 1. Existing-page audit

The first implementation step is a deterministic comparison of these no-impression indexed pages:

- San Diego
- Cape Hatteras
- Kill Devil Hills
- Myrtle Beach

against pages already showing search demand, especially:

- Oceanside
- Huntington Beach
- Miami Beach
- Clearwater Beach

The audit must verify, per page:

- HTTP-output file exists.
- Title.
- Meta description.
- H1.
- Canonical.
- Robots directive.
- Breadcrumb JSON-LD.
- State backlink.
- Nearby internal-link count.
- Tide data presence.
- High/low events rendered.
- Seven-day forecast rendered.
- NOAA source disclosure.
- Body text coverage of tide-search intent.

The audit should be implemented as a test/report helper, not a one-off manual checklist, so the same checks can run against new locations.

### San Diego interpretation

San Diego should not receive a special keyword-stuffed page merely because it has no impressions yet. The repository shows that it already has a valid Live NOAA page, canonical structure, and generated tide data. The notable structural differences from Huntington are the lack of answer-first `NEXT TIDE` treatment, generic search copy, and currently empty nearby-link structure.

The common template improvements should therefore be applied first. San Diego-specific copy should be added only if later Search Console data supports it.

## 2. State landing pages

### California

`/tides/california/` should become a search landing page rather than only a directory.

Required sections:

1. Hero: `California Tide Times`.
2. Short explanatory copy describing today’s tide times, high and low tides, tide charts, and schedules across California coastal locations.
3. Featured locations driven by current Search Console response, initially prioritizing:
   - Oceanside
   - Huntington Beach
   - Los Angeles
   - San Diego
4. `Southern California Tides` section.
5. `Northern California Tides` section.
6. Full California location directory.
7. Clear links into individual today/7-day tide pages.

Natural-language coverage should include the concepts behind:

- California tide times
- California tides
- California tide schedule
- Southern California tide tables
- SoCal tides

These phrases should appear in readable explanatory sentences, not as a keyword list.

### Florida

`/tides/florida/` receives the same landing-page model with state-specific grouping:

- Featured locations: Miami Beach and Clearwater Beach first.
- South Florida.
- Gulf Coast.
- Atlantic Coast / Keys.
- Full Florida location directory.

The implementation should use structured state metadata rather than hard-coding large HTML fragments directly in `site_generator.py`. A small state configuration map is acceptable and keeps future Country → State expansion possible.

### Ordering

State pages should no longer be purely alphabetical at the top. Featured GSC-response locations appear first in a dedicated block, while the complete location list remains deterministic and discoverable.

## 3. Location-page SEO template

All Live NOAA location pages should naturally cover these search intents:

- Tide Times
- High Tide
- Low Tide
- Tide Chart
- Tide Schedule
- Today’s Tides

### Title

Use a concise format such as:

`{Location} Tide Times, High & Low Tides Today | CoastalNow`

The exact wording may be shortened where necessary, but should retain location + tide times + today intent.

### Meta description

Use readable location-specific copy that mentions today’s high and low tide times, the tide chart/schedule, and seven-day outlook without repeating the same phrase mechanically.

### H1

Keep the established human-readable pattern:

`{Location} Tide Times Today`

### H2/body structure

Existing real data sections should carry the additional intent rather than adding filler text. Recommended headings/copy include:

- `Today’s High and Low Tides`
- `Today’s Tide Chart`
- `7-Day Tide Schedule`

The existing chronological seven-day forecast remains the authoritative schedule presentation.

### Answer-first

The Huntington Beach `NEXT TIDE` answer-first block should become the default for Live NOAA pages, not remain a one-location pilot. It should show:

- Next tide type.
- Local time.
- Height.
- Countdown.
- Next high.
- Next low.
- Today’s tide range.

This directly serves the dominant query intent without changing canonical or URL structure.

## 4. Internal linking

### Location → State

Every location page already has a breadcrumb State link. The improved local guide/navigation area should also retain an obvious State-directory route.

### Location → nearby locations

Nearby links should be generated from coordinates rather than manually maintained lists.

Rules:

- Consider only locations in the same state.
- Prefer Live NOAA locations.
- Compute geographic distance from location coordinates.
- Return the nearest 4 locations by default.
- Never link the page to itself.
- Keep deterministic ordering by distance and then name.
- If fewer than 4 valid same-state locations exist, show the available set.

This produces geographically useful links such as Southern California clusters without maintaining dozens of hand-written relationships.

### State → locations

State pages keep a full location directory, plus featured/region blocks above it.

## 5. New location validation and data model

New entries must use the existing `locations.json` + `live_noaa.json` separation.

For each new location:

`locations.json` must contain:

- state
- state_code
- state_slug
- name
- slug
- priority
- latitude/longitude where applicable
- timezone
- datum/units/source where applicable
- activity shore point
- activity marine point
- coast bearing

`live_noaa.json` must contain:

- station_id
- station_name
- prediction_mode
- coverage_mode when a nearby station is used
- coverage_distance_miles when a nearby station is used

No page becomes indexable merely because it exists in `locations.json`; the existing Live NOAA status and sitemap policy remain the gate.

## 6. Sitemap, canonical, and indexability

Existing policy is retained:

- State pages are indexable and included in sitemap.
- Live NOAA location pages are `index,follow` and included in sitemap.
- Preview location pages remain `noindex,follow` and are excluded from sitemap.
- Canonical remains the existing `/tides/{state}/{location}/` URL.
- `robots.txt` remains crawl-allowing and points to the sitemap.

Regression tests must prove that all 12 promoted Live locations appear in:

- generated state directory
- main directory
- sitemap

and have:

- self canonical
- `index,follow`
- breadcrumb structured data
- successful NOAA output

## 7. Search Console comparison reporting

Add a lightweight reporting utility under `tools/` or `src/tools/` that accepts Search Console CSV exports and writes a normalized snapshot.

### Supported page metrics

For each location/state URL:

- indexed flag when supplied separately from coverage export
- impressions
- clicks
- CTR
- average position
- first impression date when historical snapshots exist

### Snapshot format

Use a simple CSV or JSON file keyed by canonical URL and snapshot date. It must be easy to diff without a database.

Suggested fields:

- snapshot_date
- url
- page_type (`state`, `location`, `activity`, `other`)
- state_slug
- location_slug
- impressions
- clicks
- ctr
- avg_position
- indexed
- first_impression_date

### Weekly comparison output

Given a current and previous snapshot, produce:

- impressions delta
- clicks delta
- CTR delta
- position delta
- new first-impression locations
- fastest-growing states by aggregate impressions/clicks

This should make California vs Florida vs North Carolina easy to compare after the expansion batch.

### Query limitation

Standard separate `Pages.csv` and `Queries.csv` exports do not provide a reliable Page × Query join. The report must not falsely attribute site-level query rows to individual locations. Until Search Console API or page-filtered exports are used, store:

- page-level metrics by URL
- site-level query mix separately

If page-filtered query exports are later provided, the schema can add explicit location query rows.

## 8. Testing strategy

Implementation uses TDD for each behavior group.

### PR A tests

- Existing-page audit catches missing canonical, robots, H1, state link, nearby links, or NOAA output.
- California page contains featured, Southern California, Northern California, and full directory sections.
- Florida page contains featured and regional sections.
- State pages remain self-canonical and indexable.
- Location metadata covers high/low/tide chart/schedule intent without meta-keywords.
- All Live NOAA pages render the answer-first block.
- Nearby links return nearest same-state Live locations in deterministic order.
- Existing URLs are unchanged.
- Search Console snapshot parser and delta report are deterministic.

### PR B tests

- Exactly 12 intended new slugs are added unless a documented NOAA-validation replacement is required.
- No duplicate slugs or page paths.
- Each new location passes activity geography validation.
- Each Live NOAA source returns valid high and low tide predictions through the production fetch/validation path.
- New pages are generated.
- State and home directories include them.
- Sitemap includes them.
- Canonical and robots directives are correct.
- Full existing tide/activity/SEO regression suites remain green.

## 9. Deployment and observation

After PR A:

- Deploy and verify generated California/Florida state pages plus San Diego/Oceanside/Huntington pages.
- Do not manually request broad reindexing beyond the normal sitemap/search-console workflow unless needed.

After PR B:

- Deploy the 12 new locations.
- Verify generated public files and NOAA timestamps.
- Verify sitemap and directory output.
- Record a Search Console baseline snapshot.

Then hold large-scale expansion. Do not add dozens or hundreds more locations until the next Search Console comparison identifies which cluster is growing fastest among California, Florida, and North Carolina.

## Non-goals

This release does not:

- Change existing public location URLs.
- Replace NOAA as the tide source.
- Expand nationwide by dozens or hundreds of cities.
- Add a database.
- Create a fake Page × Query mapping from unrelated Search Console CSV exports.
- Redesign Fishing/Surfing scoring logic.
- Change the long-term Country → State → Location hierarchy.
