# CoastalNow Live Location Automation

After this automation is merged, converting an existing Preview location to Live NOAA no longer requires editing Python or workflow files.

## Normal promotion flow

1. Research the best NOAA prediction station for the location.
2. In GitHub, open **Actions -> Promote tide location -> Run workflow**.
3. Enter:
   - `slug` - existing CoastalNow slug, such as `monterey`
   - `station_id` - seven-digit NOAA prediction station ID
   - `station_name` - NOAA station name shown to users
4. The workflow:
   - validates the slug and station configuration,
   - calls NOAA for both high/low and 30-minute predictions,
   - refuses incompatible/subordinate stations that cannot power the current curve,
   - updates `src/data/live_noaa.json`,
   - generates the location page and JSON data,
   - rebuilds home/state directories,
   - runs regression tests,
   - pushes a preview branch,
   - attempts to open a pull request.
5. Review the Cloudflare Preview deployment and merge the PR.

## Single source of truth

`src/data/live_noaa.json` contains only the station mapping required to promote existing catalog locations. Paths, titles, status, timezone labels and directory membership continue to be derived automatically from the location catalog and existing generators.

## Adding an entirely new location

This automation promotes locations that already exist in `src/data/locations.json`. Adding a brand-new catalog location is a separate operation and should first add that location to the catalog.
