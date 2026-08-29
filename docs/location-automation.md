# CoastalNow Live Location Automation

Live NOAA promotion is started by pushing one request file to a dedicated `promotion/*` branch. The user does not need to open GitHub Actions or Codespaces for normal location promotion.

## Promotion request

Create a branch from current `main` using the prefix `promotion/`, for example:

`promotion/monterey-20260829`

Add one file under `promotion-request/`, for example `promotion-request/monterey.json`:

```json
{
  "slug": "monterey",
  "station_id": "9413450",
  "station_name": "Monterey, CA"
}
```

The workflow then:

1. Resolves the request added by the triggering commit.
2. Uses the normalized `LOCATIONS` catalog, including derived timezone data.
3. Validates NOAA high/low and 30-minute prediction support.
4. Updates `src/data/live_noaa.json`.
5. Generates the Live NOAA data and location page.
6. Rebuilds home and state directory pages.
7. Runs regression tests.
8. Removes the request file before committing, preventing a merge from retriggering promotion.
9. Pushes the generated result back to the same `promotion/*` branch.
10. Opens a pull request to `main`.

Cloudflare can use that branch as the Preview deployment. After review, the PR can be squash-merged.

## Single source of truth

`src/data/live_noaa.json` contains the NOAA station mapping for Live locations. Paths, titles, timezone labels, status and directory membership are derived from the catalog and generators.

## Adding a brand-new catalog location

This promotion flow only promotes a location that already exists in `src/data/locations.json`. Adding a completely new catalog location remains a separate catalog change.
