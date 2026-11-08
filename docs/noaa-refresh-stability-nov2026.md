# NOAA Tide refresh audit — 2026-11-08

## Observed facts

- 2026-11-05 19:57 UTC: scheduled NOAA update run #42098879508 failed because **Dana Point** returned NOAA `No Predictions data was found. Please make sure the Datum input is valid.` after three retries. The remaining **66 of 67** live locations refreshed; Dana Point retained verified same-day NOAA cache and published a visible stale state.
- 2026-11-07 05:59 UTC: scheduled NOAA update run #42345016711 failed with the same intermittent error for **Cocoa Beach**. The remaining **66 of 67** succeeded and Cocoa Beach showed the verified same-day cache.
- Later runs on both Nov 7 and Nov 8 succeeded for all 67 locations. This confirms the two stations and their existing NOAA datum are usable; do not change their station or datum based on a transient error.
- Latest complete run #42453174391 finished Nov 8 06:06 UTC with 67 location caches refreshed. On Nov 8 10:52 UTC, Pacific Coast pages still displayed *Saturday Nov 7* as `Today` because the 06:00 UTC-generation run happened before Pacific local midnight. Eastern U.S. pages correctly displayed Nov 8.

## Small, bounded mitigation

1. Preserve the existing per-request three attempts; **after all live locations**, retry only those still failing, once, with an eight-second quiet interval. Do not refetch successful stations.
2. Do not substitute an unverified station, datum or forecast, and do not hide persistent errors. A persistent failure still exits nonzero, retains a same-day cache if verified, otherwise shows an unavailable notice.
3. Adjust the **existing four daily** UTC Tide schedule slots from `00:17, 06:17, 12:17, 18:17` to `05:17, 08:17, 14:17, 20:17` UTC. The first two slots target just after Eastern and Pacific local midnight in standard time, roughly one hour after in daylight time. This improves same-day freshness and retains four runs/day. GitHub Actions schedule timing can drift and is not guaranteed to execute exactly.
4. Preserve NOAA/NWS datum, data validation, cache freshness rules, GitHub shared writer concurrency, Cloudflare build behavior, canonical URLs, site structure, SEO/AdSense and all activity schedules.
5. Offline tests cover recovered and persistent failure paths and the schedule invariants, running before and during deployment. This is a best-effort reduction of transient failure notifications, not a guarantee that NOAA will never fail.

## Verification

After CI and merge, confirm one completed `Update live NOAA tide data` run, check 67 `NOAA cache updated` log lines and the California/East Coast public data generated timestamps. Inspect the user-facing `Today` heading in live California pages to validate the day rollover at the next Pacific midnight. The original failure emails are legitimate alerts, not false reports of the entire site being down.
