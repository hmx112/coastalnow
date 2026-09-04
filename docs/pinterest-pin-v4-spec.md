# CoastalNow Pinterest Pin v4 — Final Photographic Template

## Status

Approved final design for new Pinterest releases from September 4, 2026 onward.

## Core visual rule

Pinterest pins are visual-first posters, not website information cards.

- 1000x1500 PNG (2:3)
- photoreal coastal background
- cinematic / golden-hour coastal mood when available
- large category heading
- very large location name
- state name beneath location
- one short descriptive line near the bottom
- one large CTA button

## Category copy

### Surfing

- heading: `SURF CONDITIONS`
- subtitle: `Surf Conditions & Best Times`
- CTA: `View Surf Conditions`
- photographic theme: active surfer / ocean wave

### Fishing

- heading: `FISHING CONDITIONS`
- subtitle: `Fishing Conditions & Best Times`
- CTA: `View Fishing Conditions`
- photographic theme: angler / pier / coastal sunset

### Tide

- heading: `TIDE TIMES`
- subtitle: `Tide Times & Tide Chart`
- CTA: `View Tide Times`
- photographic theme: scenic shoreline / ocean / golden hour

## Explicitly excluded

- Best Window text on the pin
- score chips or metric chips
- multiple information cards
- vector/stick-figure people
- hand-drawn character scenes
- current scores or current measurements
- alert state or date-dependent copy

Current data stays on the destination page so Pinterest pins remain evergreen.

## Background strategy

The renderer uses fixed category-specific free-to-use Unsplash photographs. The image is cover-cropped to 1000x1500. If the image CDN cannot be reached, generation falls back to a clean category-specific gradient rather than the old vector-character artwork.

Already-published Pinterest PNGs remain immutable. Renderer changes only affect new assets that do not yet exist.

## Typography hierarchy

1. CoastalNow brand
2. category heading in warm gold
3. location name in large white type
4. state name in smaller serif italic
5. short subtitle
6. gold CTA button

Top and bottom readability gradients are applied over the photograph so typography remains legible without turning the pin into a card layout.
