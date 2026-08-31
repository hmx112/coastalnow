# CoastalNow Pinterest RSS Automation Design

## Goal

Create a low-maintenance Pinterest distribution channel for CoastalNow that publishes evergreen Tide and Activity pins from the claimed domain without requiring Pinterest API Standard Access.

Pinterest v1 uses Pinterest Business RSS auto-publish. CoastalNow generates pin images and RSS 2.0 feeds as static public assets; Pinterest reads those feeds after the user connects them to the two existing boards.

## Pinterest account

- Display name: `CoastalNow | Coastal Conditions`
- Business country/region: `South Korea`
- Website: `https://coastalnowtides.com`
- Website claim: completed
- Content language: English
- Primary audience: U.S. coastal users
- Automated v1 board 1: `Tide Times & Tide Charts`
- Automated v1 board 2: `Fishing Conditions & Best Fishing Times`

The account name intentionally avoids locking the brand to Fishing because CoastalNow is expected to add Surfing, Swimming, Beach and other coastal Activities later.

## Distribution architecture

The existing site pipeline remains independent:

`NOAA/NWS -> CoastalNow data -> static pages -> Cloudflare -> IndexNow`

Pinterest adds a separate output pipeline:

`LOCATIONS + Activity Registry -> Pinterest catalog -> daily release schedule -> 1000x1500 PNGs + RSS 2.0 -> Cloudflare -> Pinterest RSS Auto-publish`

Pinterest generation does not modify Tide/Fishing scores, data collection, safety gates, canonical URLs, sitemap policy, or existing Activity refresh workflows.

## Release cadence

The catalog has a fixed marketing `launch_order` separate from `locations.json`. The first location is San Diego.

- `enabled: true`
- `start_date: 2026-08-31`
- `locations_per_day: 1`

Day N releases launch-order location N. Each released location produces at most two items:

1. Tide pin
2. Fishing pin, while Fishing is enabled in the Activity Registry

The deterministic schedule has no mutable posted-state database. Stable GUIDs and stable image paths make regeneration idempotent. If a daily job is missed, the next run catches up all locations whose release dates have passed.

## Evergreen content rules

Pinterest pins can remain discoverable long after creation, so the image and RSS metadata must not contain values that become stale.

Never include:

- current Fishing Score
- catch probability
- exact tide height/time
- current wind/wave/water-temperature values
- alert state
- dates
- `safe` or equivalent safety guarantee wording

The destination CoastalNow page remains the source for current conditions.

## Metadata templates

### Tide

Title:

`{City}, {State} Tide Times & Tide Chart`

Description:

`Check current tide times and coastal planning information for {City}, {State}. CoastalNow keeps the destination page updated with the latest available tide data.`

Destination:

`https://coastalnowtides.com/tides/{state_slug}/{location_slug}/`

### Fishing

Title:

`{City}, {State} Fishing Conditions & Best Times`

Description:

`Plan shore, pier and nearshore fishing with current tide, wind, wave and weather context for {City}, {State}. CoastalNow Fishing Score is a 0–100 planning metric, not a safety guarantee.`

Destination:

`https://coastalnowtides.com/tides/{state_slug}/{location_slug}/fishing/`

## Image design

Every pin is a deterministic 1000x1500 PNG rendered by Pillow in GitHub Actions.

V1 uses a graphic CoastalNow design rather than stock photography:

- no image licensing dependency
- no photo API dependency
- deterministic output
- consistent CoastalNow teal / seafoam / navy / off-white language
- no NOAA/NWS logos

Tide image copy:

- `CoastalNow`
- city/state
- `TIDE TIMES & TIDE CHART`
- abstract wave/horizon visual
- `Live coastal data on CoastalNow`

Fishing image copy:

- `CoastalNow`
- city/state
- `FISHING CONDITIONS & BEST TIMES`
- shoreline/wave visual
- `Live tide, wind & wave context`

No font files are committed. GitHub Ubuntu's DejaVu Sans family is used when available, with Pillow default font fallback.

## RSS design

Public feeds:

- `https://coastalnowtides.com/pinterest/rss/tides.xml`
- `https://coastalnowtides.com/pinterest/rss/fishing.xml`

RSS is version 2.0 XML. Pinterest officially reads each item's `<title>`, `<description>`, claimed-domain `<link>`, and supported image tags. To avoid the risk of Pinterest interpreting repeated image tags as multiple images, each item contains exactly one `media:content` image element.

Each item includes:

- stable non-permalink GUID: `coastalnow:pinterest:{kind}:{slug}:v1`
- title
- description
- claimed-domain destination link
- deterministic release `pubDate`
- one 1000x1500 PNG `media:content` URL on the claimed domain

Released items remain in the feed. At 51 locations, feed size is small enough that v1 needs no pagination or truncation.

## Repository components

- `src/data/pinterest.json` — enabled flag, start date, cadence, fixed launch order
- `src/pinterest/__init__.py`
- `src/pinterest/catalog.py` — validate config and project existing locations into Pinterest catalog entries
- `src/pinterest/schedule.py` — deterministic release dates
- `src/pinterest/render.py` — 1000x1500 PNG renderer
- `src/pinterest/rss.py` — evergreen metadata and RSS 2.0 serialization
- `src/generate_pinterest.py` — generator/CLI
- `requirements-pinterest.txt` — pinned Pillow dependency only
- `.github/workflows/update-pinterest.yml` — daily/manual generation workflow
- `src/test_pinterest_*.py` — Pinterest-specific regressions
- `public/pinterest/images/*.png` — released pin images only
- `public/pinterest/rss/*.xml` — live feeds

## GitHub workflow

`Update Pinterest distribution assets` runs daily at `15:17 UTC` and supports `workflow_dispatch`.

It uses the shared `coastalnow-site-writes` concurrency group.

Steps:

1. checkout main
2. Python 3.12
3. install pinned Pinterest requirements
4. generate all due Pinterest assets for current UTC date
5. run Pinterest regressions
6. commit only `public/pinterest/**` if changed
7. push

There is no `push:` trigger, preventing self-trigger loops.

Existing IndexNow may observe the push, but IndexNow only submits changed public HTML URLs, so PNG/XML-only Pinterest releases result in no IndexNow URL submission.

## Error handling

Generation fails before commit when:

- Pinterest config is malformed
- launch order contains unknown, duplicate, or missing location slugs
- required canonical destination cannot be constructed
- image rendering fails
- RSS cannot be parsed
- an RSS image URL does not map to an existing generated PNG

Pinterest outages cannot corrupt CoastalNow because the v1 workflow does not call Pinterest directly. Pinterest fetches the static feeds independently.

## Acceptance criteria

1. fixed launch order contains every current CoastalNow location exactly once
2. San Diego is first
3. day 1 releases only San Diego
4. day N deterministically includes all locations released through day N
5. disabled config releases zero items
6. Tide and Fishing destination URLs use existing canonical structures
7. each PNG is exactly 1000x1500
8. image and RSS copy contain no volatile condition values
9. RSS is valid RSS 2.0 XML
10. each item contains exactly one `media:content` image
11. every item link and image URL uses the claimed domain
12. generator is idempotent for the same date/config
13. workflow is schedule/manual only and uses `coastalnow-site-writes`
14. complete existing repository regression suite remains green
15. first production release exposes San Diego Tide and Fishing PNGs plus both feeds

## User handoff after deployment

On desktop Pinterest:

`Settings -> Create Pins in bulk -> Auto-publish -> Connect RSS feed`

Connect:

- `https://coastalnowtides.com/pinterest/rss/tides.xml` -> `Tide Times & Tide Charts`
- `https://coastalnowtides.com/pinterest/rss/fishing.xml` -> `Fishing Conditions & Best Fishing Times`

Pinterest can create Pins from feed updates within 24 hours and processes older feed content first.

## Out of scope for v1

- Pinterest API Standard Access / direct Create Pin
- paid schedulers
- automatic duplication into regional/state boards
- multiple creative variants per location
- dynamic daily-score pins
- AI-generated photography
- Pinterest analytics ingestion

After roughly 30 days of impressions/clicks, expand the highest-performing regions, keyword variants, visual variants, and newly enabled Activities.