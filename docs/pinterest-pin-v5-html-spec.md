# CoastalNow Pinterest V5 — HTML/CSS editorial covers

## Design intent

Supersedes the V2 checklist card and earlier V4 all-purpose photo poster **for newly released assets only**. Preserve all existing published PNG, RSS GUID, URL and original publication dates. This is a visual-first, informative magazine-cover system designed around a single visitor task.

All three are **1000 × 1500 px** (2:3) PNGs rendered by Playwright + installed Chrome. Images include the CoastalNow wave mark and a practical, evergreen link prompt; they intentionally contain **no** live NOAA/NWS measurements, dates, fishing-catch predictions, surf-break-specific scores, or safety guarantees.

## The three designs

| Template | Graphic character | On-image copy | Destination |
| --- | --- | --- | --- |
| `pin_tides.html` | Teal coastal editorial + pale-mint footer; serif lead line and prominent city | `Find your low tide.` / `High & low tide times. Seven-day NOAA outlook.` / `EXPLORE THE TIDE CHART` | Existing Tide city page |
| `pin_fishing.html` | Deep-navy shore-fishing field journal + amber headline + cream bottom strip | `READ THE WATER.` / `NOAA tide timing`, `Wind & waves`, `Marine alerts` / `CHECK FISHING CONDITIONS` | Existing Fishing city page |
| `pin_surfing.html` | High-contrast surf-journal cover + lime accent & oversize dynamic title | `READ THE WAVES` / `HEIGHT · PERIOD · WIND` / `SEE THE SURF OUTLOOK` | Existing Surfing city page |

Text uses system fonts. Only location and state are substituted, HTML-escaped, and classified into short/long title styles. No scraped images, web fonts, external JS, API calls or telemetry inside the browser. The existing verified category photo configuration in `pinterest/render.py` supplies one reusable photo per category (with offline gradient fallback); photos are *illustrative* and do not claim to depict the target location.

## Implementation and file contracts

- `src/pinterest/templates/pin.css` — shared typography and three **different** visual compositions.
- `src/pinterest/templates/pin_{tides,fishing,surfing}.html` — category-specific semantic HTML.
- `src/pinterest/render_html.py` — safe location text and local photographic JPEG embedded as a data URI, so Chromium never makes network requests.
- `src/pinterest/capture_pin.py` — captures exact 1000×1500 PNG via GitHub-hosted Chrome and Playwright. Requires `Pillow` and `playwright` as pinned in `requirements-pinterest.txt`. No Playwright browser download is needed on GitHub's Ubuntu runner.
- `src/generate_pinterest.py` — existing immutable-image policy remains intact. V3 pilots and new locations first published on/after Nov 11 use HTML capture; already released V1/V2 remain unchanged.
- `src/pinterest/rss.py` — V3 uses dedicated `-v3.png`, `coastalnow:pinterest:{kind}:{slug}:v3` GUID, `utm_campaign=coastalnow_html_v3`. Existing V1/V2 records remain unchanged.
- `src/pinterest/schedule.py` — six V3 pilot pins simultaneously on Nov 3, 2026 (UTC), **independent** of the regional backfill that remains one new city/day starting Nov 11.
- `src/test_pinterest_html_v3.py` — true Chrome screenshot tests, 3 category styles, new V3 RSS identities, old pin protection, date gates and future HTML routing.

### Six V3 pilot Pins

| Topic | Destination |
| --- | --- |
| Tides | Huntington Beach, California; San Diego, California |
| Fishing | Cape Hatteras, North Carolina; Miami Beach, Florida |
| Surfing | Malibu, California; Nags Head, North Carolina |

The six tests deliberately reference destinations with earlier V1/V2 pins so distribution outcomes can be compared using Pinterest impressions/saves/outbound clicks and UTM-tagged visits.

## Deployment safety / verification

1. All file changes land in a single feature branch and PR; existing `SEO Pilot Test` runs Pinterest screenshot tests *before* expensive NOAA collection.
2. Merge only if the full PR CI is green.
3. The existing `Update Pinterest distribution assets` workflow renders and commits exactly six extra V3 PNGs to `public/pinterest/images` and updates the **same three** RSS feeds.
4. Verify on GitHub and production that all six V3 PNG and RSS entries exist (Tide 17, Fishing 17, Surfing 14 before Nov 11), with no legacy GUID/image replacement.
5. The Pinterest *account* publishing is managed by Pinterest's connected RSS importer. GitHub output success does **not** prove that Pinterest has ingested or published the Pins; inspect account analytics separately.
6. If a V3 design later underperforms, stop adding new versioned Pins; never delete already published images or rewrite legacy feed GUIDs. Recover from a new generator version without changing site URL, title, robots, canonical, NOAA or AdSense metadata.

## Costs and failure modes

GitHub's hosted Chrome removes the need for a daily Chromium download. PIL loads the already-configured Unsplash photos once by category, with an offline gradient fallback if CDN access fails. A browser launch and screenshot per **new** Pin is the only added computation; unchanged PNGs are skipped entirely. The 404 fallback and NOAA/safety update pipelines are untouched.

Actual Pinterest distribution metrics must be collected from the Pinterest business account; successful RSS/PNG delivery alone does not prove reach or increased traffic.
