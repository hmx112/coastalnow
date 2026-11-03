# CoastalNow Pinterest — Information-First V4 Pins (Nov 2026)

## User-approved creative direction

Replace the visually polished but hard-to-understand magazine-cover layout **for new designs only** with clear, useful information-first pins at 1000×1500 (2:3). The three real design previews in the conversation establish the layout: large semantic title → location → large photo → practical visual explanation → clear CTA and original CoastalNow wave logo.

| Topic | Main image title | Visual information | CTA | Palette |
| --- | --- | --- | --- | --- |
| Tides | TIDE TIMES & CHART | Illustrative high/low tide curve plus a seven-day NOAA prompt | VIEW LOCAL TIDE CHART | deep teal, bright aqua, cream |
| Fishing | SHORE FISHING CONDITIONS | Three icon rows for tides, wind and waves, marine alerts | CHECK LOCAL CONDITIONS | deep navy, orange |
| Surfing | SURF FORECAST | Three pictograms: wave height, swell period, wind | EXPLORE THE SURF OUTLOOK | ocean blue, aqua |

Only name and state code are dynamic in these images. The category images use the existing reusable, attributed Unsplash photo library configured in `src/pinterest/render.py`; **these are illustrative category photos, not location-specific photos**. Each HTML document inlines the chosen photo, CSS, system fonts and original logo; Chrome screenshots make no network requests. All forecast data is fetched afresh when someone visits the actual landing page.

**No live tide values, catch probability, surf safety guarantees, hourly forecasts or fabricated data appear on any evergreen pin.** The tide curve is specifically labeled an illustration.

## Publication / immutable identities

- The earlier V1, V2, V3 images and RSS identity histories stay immutable. V3 is still held with `creative_v3_publish_enabled=false`.
- V4 enables exactly six named pilots simultaneously on **2026-11-03 UTC** through `creative_v4_publish_enabled=true`; the six match the previous design test destinations.
- Each new file uses `-v4.png`, a dedicated `:v4` GUID and `utm_campaign=coastalnow_info_v4`. No existing files are overwritten and older version identities are never reused.
- Existing RSS URLs remain `/pinterest/rss/{tides,fishing,surfing}.xml`. Before Nov 11 expect **17 Tide, 17 Fishing, 14 Surfing** entries, of which two per feed are V4 and zero are V3.
- All other new-location HTML rollout is **still paused** with `html_cutover_enabled=false`. The previously configured November 11 one-new-location/day schedule is unchanged.
- The Pinterest RSS importer decides when or whether to ingest new items. Successful GitHub deployment is NOT proof that the Pinterest account published six new pins or generated clicks.
- When evaluating Pinterest analytics, compare impressions, saves, outbound clicks and attributed sessions for `coastalnow_info_v4` versus the earlier campaigns.

## Deployment and rollback

The existing PR SEO Pilot Test and Pinterest publishing Action both execute `src/test_pinterest_info_v4.py`, which validates semantic topics, browser render bounding boxes, 1000×1500 screenshots, unique GUIDs, no V3 release, and no mutation of existing images.

For a reversible hold, set **only** `creative_v4_publish_enabled=false` and regenerate the RSS. This removes V4 items from future feeds but cannot retract anything Pinterest may have cached or already posted. Do not delete PNG assets or change historical GUIDs.

The Pinterest campaign is a distribution experiment. Site SEO pages, NOAA/NWS generation, AdSense settings, robots, sitemap, landing URLs and existing cron schedules are out of scope.
