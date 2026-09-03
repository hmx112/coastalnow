# CoastalNow Pinterest Pin v3

## Why this revision exists

Pinterest v1/v2 proved the RSS auto-publish pipeline, but the information-card visual language looked too similar across Tide and Fishing and did not use Pinterest's visual-first format strongly enough. A user review also found Miami Beach and Myrtle Beach appearing duplicated in Pinterest.

Repository history did not show the same RSS item being regenerated with a changed GUID, link, publication date, or media URL. Miami Beach remained byte-identical in the next day's RSS update, while Myrtle Beach was appended as the next scheduled location. CoastalNow therefore does not claim a proven same-feed duplication bug.

v3 hardens the feed anyway and makes categories visually unmistakable.

## Distribution safety

- Each feed rejects duplicate GUIDs, destination links, or media URLs before publication.
- Stable identity remains `coastalnow:pinterest:{kind}:{slug}:v1`.
- Once a public Pinterest PNG exists, the daily generator does not overwrite it. Published media assets are immutable.
- Existing Tide/Fishing images therefore stay unchanged after this rollout; newly released locations use the v3 design.
- The Pinterest workflow may run after Pinterest source merges, but `public/pinterest/**` is not a push trigger, preventing bot self-loops.

## Feeds and boards

- `/pinterest/rss/tides.xml` -> `Tide Times & Tide Charts`
- `/pinterest/rss/fishing.xml` -> `Fishing Conditions & Best Fishing Times`
- `/pinterest/rss/surfing.xml` -> `Surfing Conditions`

The Surfing board/feed connection is a one-time Pinterest account action and is not performed by the repository workflow.

## Surfing pilot release

Surfing Pinterest distribution is independent from the 51-location Tide/Fishing marketing order.

- start: `2026-09-03`
- cadence: one Surfing pilot location per day
- scope: exactly the current 10-location Surfing allowlist
- order: San Diego, La Jolla, Huntington Beach, Santa Cruz, Malibu, Half Moon Bay, Cocoa Beach, Daytona Beach, Wrightsville Beach, Nags Head

This allows the 10 public Surfing pages to be distributed without enabling Surfing for non-pilot Tide locations.

## v3 visual system

The automated renderer remains deterministic and license-independent: no stock-photo API, image hotlink, or AI image service is required at runtime.

Instead of white information cards, each 1000x1500 pin is a full-bleed coastal poster with a category-specific scenic focal image:

- Tide: sunrise disc, layered ocean, shoreline/headland, tide contour motif
- Fishing: warm sunset, pier silhouette, angler and rod, coastal water layers
- Surfing: large curling wave, foam, surfer silhouette, ocean sunset

Shared hierarchy:

1. CoastalNow brand
2. category pill
3. city/state
4. large category headline
5. three short benefit chips
6. one strong CTA

No current score, current alert, exact wave/tide measurement, or dated value is baked into the evergreen Pinterest image or RSS metadata. Current conditions remain on the destination page.

## Verification

Pinterest regressions cover:

- unique feed identity
- Surfing canonical links and stable GUIDs
- Surfing allowlist-only publication
- independent one-location-per-day Surfing schedule
- immutable existing public images
- three RSS feeds
- 1000x1500 PNG output for Tide/Fishing/Surfing
- visually distinct image bytes across the three categories
- source-merge refresh without `public/pinterest/**` self-triggering
