# CoastalNow — San Diego integrated v1

This package combines the approved San Diego v3 design with the NOAA tide-data pipeline.

## Production flow

1. NOAA CO-OPS station `9410170` (San Diego, CA)
2. Fetch 7 days of high/low predictions (`interval=hilo`)
3. Fetch today + tomorrow at 30-minute intervals (`interval=30`)
4. Validate timestamps, event types and numeric ranges
5. Save normalized JSON to `public/data/san-diego.json`
6. Calculate next high/low countdowns and current rising/falling direction
7. Generate the SVG tide curve and complete 7-day forecast
8. Render the static HTML page
9. GitHub Actions can repeat this every 6 hours

## Design behavior

- Next High / Next Low cards show exact time, height and countdown.
- The status strip shows only current tide direction: rising / falling / turning point.
- Desktop shows all 7 forecast days immediately.
- Mobile shows the first 3 days, then expands the remaining 4 with `Show all 7 days`.
- Mobile day cards include every high/low event returned by NOAA; events are not discarded for brevity.

## Failure behavior

Production never generates fake tide values.

- NOAA success: new verified cache + page render.
- NOAA failure + same-day verified cache: render that cache with a delayed-refresh notice.
- NOAA failure + no usable cache: show an explicit data-unavailable state.

## Commands

```bash
# Offline visual/integration test using explicitly synthetic preview values
python src/update_san_diego.py --preview

# Automated integration checks
python src/test_integrated_render.py

# Production NOAA fetch + render (requires internet)
python src/update_san_diego.py
```

## Files to inspect

- `src/templates/san-diego-v3.html` — approved design converted to a data template
- `src/update_san_diego.py` — live fetch/calculation/render logic
- `preview/san-diego-integrated-preview.html` — offline integrated design preview
- `public/tides/california/san-diego/index.html` — production output path
- `.github/workflows/update-san-diego.yml` — six-hour update schedule example

The current packaged production output shows an unavailable state because the build environment used to assemble this package cannot reach the NOAA API. The preview page is clearly labeled and uses mock values only for layout testing.
