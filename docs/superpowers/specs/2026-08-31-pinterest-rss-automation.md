# CoastalNow Pinterest RSS Automation Design

## Goal

Create a low-maintenance Pinterest distribution channel for CoastalNow that can publish evergreen Tide and Fishing pins without waiting for Pinterest API Standard Access.

Pinterest v1 will use Pinterest Business RSS auto-publish. CoastalNow will generate the pin images and RSS feeds as static public assets. Pinterest will consume those feeds and create the public pins after the user claims `coastalnowtides.com` and connects each feed to its board.

The system must not publish time-sensitive values such as today's Fishing Score, exact tide heights, current wind, dates, or alert state into the pin image or metadata. A Pinterest pin may remain discoverable long after those values have changed; the pin should instead send the visitor to the live CoastalNow page.

## Account and board structure

The Pinterest account is a separate CoastalNow Business account.

Recommended profile:

- Display name: `CoastalNow | Tides & Fishing`
- Preferred username: `coastalnowtides`
- Website: `https://coastalnowtides.com`
- Primary market/language: United States / English
- Bio: `Tide times, fishing conditions, wind, waves and coastal planning for U.S. coastlines. Live data and local fishing windows, updated automatically.`

Initial boards:

1. `Tide Times & Tide Charts`
2. `Fishing Conditions & Best Fishing Times`
3. `California Tides & Fishing`
4. `Florida Tides & Fishing`
5. `East Coast Tides & Fishing`
6. `Pacific Coast Tides & Fishing`

Only boards 1 and 2 are automated in v1. Regional boards are intentionally left for later curation so the same URL is not automatically duplicated across several boards.

RSS mapping after website claim:

- `https://coastalnowtides.com/pinterest/rss/tides.xml` -> `Tide Times & Tide Charts`
- `https://coastalnowtides.com/pinterest/rss/fishing.xml` -> `Fishing Conditions & Best Fishing Times`

## Activation safety

Pinterest generation ships disabled.

The repository will contain a Pinterest config with:

- `enabled: false`
- `start_date: null`
- one explicit marketing launch order of CoastalNow location slugs
- `locations_per_day: 1`

While disabled, the generator may create valid empty RSS endpoints, but it exposes no publishable items. This prevents Pinterest from ingesting the full 51-location catalog while the Business account and website claim are still being configured.

After the website is claimed, activation is one small config change:

- set `enabled: true`
- set `start_date` to the activation date

The first release is San Diego. Each release day unlocks one location, producing up to two items: one Tide pin and one Fishing pin. At the current 51-location catalog this gives roughly 51 days of daily original content.

The schedule is deterministic rather than stored as mutable "already posted" state. Day N releases launch-order location N. Stable RSS GUIDs prevent duplicate items when feeds are regenerated.

If a scheduled GitHub run is missed, the next run catches up items whose release dates have passed. Existing items remain in the feed with the same GUID, URL and publication date.

## Source of truth and catalog

`src/locations.py` / existing location data remains the source of truth for location names, states, slugs and canonical Tide URLs.

Pinterest has a separate explicit `launch_order` because marketing priority is not geographic source-of-truth data. Adding or promoting a location must not silently rearrange already scheduled Pinterest releases.

Tide candidates exist for every CoastalNow location with a public Tide page.

Fishing candidates exist where the Fishing activity/page is enabled. The pin is evergreen and may link to a page whose current data state is Ready, Limited, Not Recommended, or otherwise dynamic; the pin itself never claims that current conditions are favorable.

## Pin metadata

### Tide

Title template:

`{City}, {State} Tide Times & Tide Chart`

Description template:

`Check current tide times and coastal planning information for {City}, {State}. CoastalNow updates the live page with the latest available tide data.`

Destination:

`/tides/{state_slug}/{location_slug}/`

### Fishing

Title template:

`{City}, {State} Fishing Conditions & Best Times`

Description template:

`Plan shore, pier and nearshore fishing with current tide, wind, wave and weather conditions for {City}, {State}. CoastalNow Fishing Score is a 0–100 planning metric, not a safety guarantee.`

Destination:

`/tides/{state_slug}/{location_slug}/fishing/`

Titles, descriptions and images must not contain today's score, catch probability, exact weather/ocean observations, or wording that implies safety.

## Image system

Every pin image is a deterministic 1000 x 1500 PNG.

V1 uses a graphic CoastalNow visual system rather than stock photography. Reasons:

- no external image licensing or attribution dependency
- no API needed to source photos
- deterministic rendering in GitHub Actions
- consistent CoastalNow identity across 51 locations
- small files and easy regeneration

Two templates are required.

### Tide template

- CoastalNow brand mark/name
- city + state as the dominant text
- `TIDE TIMES & TIDE CHART`
- abstract wave/tide geometry
- small evergreen footer such as `Live coastal data on CoastalNow`

### Fishing template

- CoastalNow brand mark/name
- city + state as the dominant text
- `FISHING CONDITIONS & BEST TIMES`
- simple shoreline/wave/fishing visual motif
- small evergreen footer such as `Live tide, wind & wave context`

The design uses the existing CoastalNow teal/off-white visual language. It does not use NOAA or NWS logos and does not imply agency sponsorship.

Rendering uses Pillow in a dedicated Pinterest generation workflow. The workflow installs a pinned Pillow dependency. It uses the standard DejaVu Sans family available on GitHub's Ubuntu runner, with a safe Pillow default-font fallback for tests/development. No font files are committed to the repository.

Images are generated only for locations that have become due for release rather than committing all 102 PNGs on day one.

Output pattern:

- `public/pinterest/images/{slug}-tides.png`
- `public/pinterest/images/{slug}-fishing.png`

## RSS feeds

Feeds are RSS 2.0 and remain static files served by Cloudflare Pages.

Outputs:

- `public/pinterest/rss/tides.xml`
- `public/pinterest/rss/fishing.xml`

Each item contains:

- stable GUID (`coastalnow:pinterest:{type}:{slug}:v1`)
- keyword-focused title
- evergreen description
- canonical CoastalNow destination URL
- deterministic publication date from the release schedule
- public PNG image using RSS enclosure and compatible media metadata

The feed keeps the released catalog rather than only the newest day. Because the entire v1 catalog is small (about 51 items per feed), there is no need for pagination or feed truncation in v1.

## Repository components

Planned structure:

- `src/data/pinterest.json` — enabled flag, start date, cadence and fixed launch order
- `src/pinterest/__init__.py`
- `src/pinterest/catalog.py` — build Tide/Fishing candidates from CoastalNow locations
- `src/pinterest/schedule.py` — deterministic release-date calculation
- `src/pinterest/render.py` — 1000x1500 PNG renderer
- `src/pinterest/rss.py` — RSS 2.0 serialization
- `src/generate_pinterest.py` — CLI/orchestrator
- `requirements-pinterest.txt` — pinned image dependency only
- `.github/workflows/update-pinterest.yml` — daily generation workflow
- Pinterest-specific regression tests under `src/test_pinterest_*.py`

Pinterest generation is isolated from Tide, Fishing, NOAA/NWS, promotion and IndexNow workflows. It consumes existing location/page configuration but does not alter scoring, tide data, Fishing data, canonical URLs, sitemap indexing policy or activity safety behavior.

## Daily workflow

`Update Pinterest distribution assets` runs once daily plus `workflow_dispatch`.

Recommended schedule: approximately U.S. morning (`13:17 UTC`). Exact Pinterest publication time is intentionally not promised because RSS auto-publish is asynchronous.

Steps:

1. checkout `main`
2. set up Python 3.12
3. install pinned Pinterest image dependency
4. validate Pinterest config and catalog
5. generate any newly due PNGs and both RSS feeds
6. run Pinterest-specific regressions
7. commit only `public/pinterest/**` when changed
8. push the generated release

The workflow has the same shared site-write concurrency group used by generated site content, preventing competing repository pushes.

The resulting `public/pinterest/**` push can trigger the existing IndexNow workflow, but IndexNow already filters to public HTML URLs, so Pinterest PNG/XML changes produce no IndexNow URL submission.

## Error handling

The Pinterest workflow fails before commit when:

- config is invalid
- launch order contains an unknown or duplicate location slug
- a required destination page cannot be resolved
- image rendering fails
- generated RSS is malformed
- an RSS item references an image that does not exist

Pinterest account/API outages cannot corrupt CoastalNow because v1 does not call Pinterest directly. Pinterest periodically reads the public feeds independently.

The generator must be idempotent: rerunning the same date/config produces the same item GUIDs, filenames, publication dates and logical feed contents.

## Tests and acceptance criteria

Automated tests must prove:

1. disabled config publishes zero RSS items
2. day 1 releases only launch-order location 1
3. each subsequent day deterministically expands the released catalog
4. no duplicate GUIDs or destination URLs within a feed
5. Tide and Fishing destinations use the existing canonical URL structure
6. generated PNGs are exactly 1000x1500
7. pin title/image copy contains no live Fishing Score, tide height, wind speed, date or other volatile measurement
8. generated feed XML parses successfully and references existing images
9. missing/invalid location config fails rather than silently dropping a scheduled item
10. the Pinterest workflow is schedule/manual only and cannot create a push loop
11. existing repository regression tests remain green

## User-side setup sequence

While code is being built, the user creates the separate CoastalNow Pinterest Business account and the two primary boards.

Then:

1. claim `coastalnowtides.com` in Pinterest
2. send the Pinterest HTML tag or verification file if repository/site changes are needed
3. CoastalNow enables `src/data/pinterest.json` and sets the launch date
4. the generator deploys the first San Diego Tide and Fishing images plus non-empty RSS feeds
5. user connects `tides.xml` and `fishing.xml` to their matching Pinterest boards
6. verify the first two public pins and destination links
7. leave daily release automated

## Out of scope for v1

- Pinterest API Standard Access/direct Create Pin calls
- paid schedulers such as Tailwind
- automatic duplication into state/regional boards
- multiple creative variants per location
- dynamic scores or daily-condition pins
- AI-generated photographs
- automatic Pinterest analytics ingestion

After roughly 30 days of Pinterest impressions/clicks, use performance data to choose which regions, keyword variants and visual variants deserve expansion. Direct Pinterest API publishing can replace or complement RSS later if Standard Access is approved.