# Full Live Rollout Spec

## Goal
Promote the remaining 39 Preview locations to production-quality Live NOAA pages as quickly as possible without sacrificing station accuracy.

## Rollout policy
- Use NOAA CO-OPS tide-prediction stations only.
- Prefer an exact-name station when one exists.
- Otherwise prefer a station physically inside the named municipality, beach, inlet, harbor, or immediately adjacent coastal waterbody.
- Prefer a defensible local subordinate station over a farther harmonic station when the subordinate station better represents the user-facing location.
- Never assign a merely nearby station just to reach 51/51 Live.
- `type=R` NOAA prediction stations use the existing harmonic/interval mode.
- `type=S` NOAA prediction stations use the existing `hilo-derived` mode, preserving official NOAA High/Low and deriving only the display curve.
- A batch is atomic: if any location in the batch cannot be validated, the batch must not silently promote that location.
- Preview locations remain `noindex,follow` and stay out of the sitemap until successfully promoted.
- Successful promotion automatically switches the location to `index,follow` and adds it to the sitemap via the existing SEO build.

## Promotion waves
1. California: Santa Cruz, Newport Beach, Huntington Beach, Half Moon Bay, Santa Monica, Malibu, San Francisco, Oceanside, Laguna Beach.
2. North Carolina: Nags Head, Kitty Hawk, Kill Devil Hills, Cape Hatteras, Ocracoke, Wrightsville Beach, Carolina Beach, Topsail Beach, Emerald Isle, Corolla.
3. South Carolina: Folly Beach, Isle of Palms, Kiawah Island, Edisto Beach, Pawleys Island.
4. Florida: Key West, Clearwater Beach, St. Pete Beach, Naples, Miami Beach, Fort Lauderdale, Daytona Beach, Cocoa Beach, Destin, Panama City Beach.
5. Oregon: Cannon Beach, Seaside.
6. Mid-Atlantic: Ocean City (MD), Virginia Beach (VA), Cape May (NJ).

## Known high-confidence NOAA examples already confirmed
- Santa Cruz: 9413745, subordinate, reference 9413450.
- Half Moon Bay: 9414131 Pillar Point Harbor, reference station.
- Santa Monica: 9410840 Santa Monica Municipal Pier, reference station.
- San Francisco: 9414290 San Francisco (Golden Gate), reference station.
- Nags Head: 8652226 Jennettes Pier, subordinate, reference 8651370.
- Kitty Hawk: 8651605 Kitty Hawk (ocean), subordinate, reference 8651370.
- Cape Hatteras: 8654400 Cape Hatteras Fishing Pier or 8654467 Hatteras (ocean), both reference stations; choose the page-representative coastal station during batch review.
- Ocracoke: 8654769 Ocracoke, Pamlico Sound, reference station.
- Wrightsville Beach: 8658163 Wrightsville Beach, reference station.
- Isle of Palms: 8665494 Isle of Palms Pier, subordinate, reference 8665530.
- Edisto Beach: 8667630 Edisto Beach, Edisto Island, subordinate.
- Pawleys Island: 8662006 Pawleys Island Pier (ocean), reference station, with local alternatives also available.
- Key West: 8724580 Key West, reference station.
- Clearwater Beach: 8726724 Clearwater Beach, reference station.
- Naples: 8725114 Naples, Naples Bay north end, reference station.
- Fort Lauderdale: 8722937 Fort Lauderdale Andrews Ave Bridge and 8722899 Lauderdale-by-the-Sea Anglin Fishing Pier are reference stations; select the coastal representation during review.
- Daytona Beach: 8721120 Daytona Beach Shores Sunglow Pier, subordinate.
- Cocoa Beach: 8721649 Cocoa Beach, reference station.
- Destin: 8729511 East Pass (Destin), subordinate.
- Panama City Beach: 8729210 Panama City Beach, reference station.
- Ocean City: 8570280 Ocean City Fishing Pier and 8570283 Ocean City Inlet are reference stations; prefer the ocean-facing user intent.
- Virginia Beach: 8639168 Virginia Beach, subordinate.
- Cape May: 8535962 Cape May Atlantic Ocean is subordinate; 8536110 Cape May ferry terminal is reference. Prefer the Atlantic Ocean station for the beach-intent page unless validation reveals a reason not to.

## Launch gate
The site is ready for custom-domain cutover only when:
- every promoted station passes live NOAA validation,
- all generated pages pass regression tests,
- every Live location is in the sitemap and `index,follow`,
- every remaining unresolved location (if any) stays Preview/noindex and is explicitly listed,
- Cloudflare Production deployment succeeds from `main`.
