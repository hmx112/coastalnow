"""Surf spot context for the six new, NWS-backed Surfing location pages.

Published wave/wind scores describe broad nearby coastal conditions, not
observations at the named break. Surf spot references are background, not
live forecast inputs or endorsements.
"""
from __future__ import annotations

from html import escape


EXPANSION_SURF_SPOTS = {
    "oceanside": {
        "spot": "Oceanside Harbor and Oceanside Pier",
        "summary": (
            "Oceanside has distinct breaks around the harbor jetties and both sides of "
            "its pier. Sandbars and exposure differ across those breaks, so a citywide "
            "wave/wind outlook cannot say which individual peak is surfable."
        ),
        "caution": (
            "Check the surf at your intended break, along with beach rules and official "
            "alerts. Nearby harbor structures, a pier and changing sandbars matter "
            "more locally than the regional score can capture."
        ),
        "source": "Surfline Oceanside Surf Guide",
        "url": "https://www.surfline.com/travel/zones/san-diego/surf-guide/oceanside/5842041f4e65fad6a7708835",
    },
    "newport-beach": {
        "spot": "Blackies near Newport Pier",
        "summary": (
            "Blackies is a recognized Newport Beach surf break near the pier and "
            "28th Street jetty, with a sandbar shape influenced by these structures. "
            "This page represents nearby coastal forecast conditions, not a "
            "Blackies-specific wave camera or surf-height measurement."
        ),
        "caution": (
            "Crowds, pier supports, rocks and changing sandbars can affect conditions. "
            "Check on-site rules and current official safety notices before entering."
        ),
        "source": "Surfline Blackies Surf Guide",
        "url": "https://www.surfline.com/surf-report/blackies/584204204e65fad6a7709115/spot-guide",
    },
    "ventura": {
        "spot": "Ventura Point / California Street",
        "summary": (
            "Ventura Point, also called California Street or C Street, contains "
            "several surfing sections near the county fairgrounds. Sand and "
            "cobblestone conditions vary; the area-wide wave forecast does not "
            "resolve the shape or surfability of each section."
        ),
        "caution": (
            "Account for rocks and changing currents, and verify beach access, "
            "official warnings and surf conditions on site."
        ),
        "source": "Surfline Ventura Point Surf Guide",
        "url": "https://www.surfline.com/surf-report/ventura-point/584204204e65fad6a77096b1/spot-guide",
    },
    "virginia-beach": {
        "spot": "1st Street Jetty",
        "summary": (
            "1st Street Jetty is a well-known Virginia Beach surf location close "
            "to Rudee Inlet. Local sandbanks and the jetty affect how waves break; "
            "a broader National Weather Service forecast is not an on-site "
            "measurement at this particular break."
        ),
        "caution": (
            "Crowds, jetty structures, coastal currents and local restrictions "
            "require independent attention. Follow posted beach rules and alerts."
        ),
        "source": "Surfline 1st Street Jetty Surf Guide",
        "url": "https://www.surfline.com/surf-report/1st-street-jetty/584204214e65fad6a7709ce7/spot-guide",
    },
    "folly-beach": {
        "spot": "The Washout",
        "summary": (
            "The Washout is a recognized Folly Beach surfing area along a stretch "
            "of beach breaks shaped by nearby jetties. Local break behavior can "
            "differ from the regional wave, wind and marine forecasts used here."
        ),
        "caution": (
            "Jetty rocks, underwater obstructions and stronger currents during "
            "large swells are not captured by the numerical planning score. "
            "Check official alerts and on-site conditions before surfing."
        ),
        "source": "Surfline Washout Surf Guide",
        "url": "https://www.surfline.com/surf-report/washout/5842041f4e65fad6a7708a85/spot-guide",
    },
    "ocean-city": {
        "spot": "Ocean City, Maryland designated surf beaches",
        "summary": (
            "Ocean City, Maryland operates rotating designated surfing areas "
            "and a separate surfing zone at the Inlet. Permitted locations "
            "and hours can change, so the citywide forecast here does not "
            "identify where surfing is permitted today."
        ),
        "caution": (
            "Check the town Beach Patrol's current official surf-beach schedule, "
            "seasonal surfing restrictions and safety notices. Do not confuse "
            "Ocean City, Maryland with Ocean City, New Jersey."
        ),
        "source": "Ocean City, MD Beach Patrol – Surf Beaches",
        "url": "https://oceancitymd.gov/oc/departments/emergency-services/beach-patrol/surf-beaches/",
    },
}


def surf_spot_guide_html(location: dict) -> str:
    """Produce factual, attributable, location-specific context (never a score)."""
    guide = EXPANSION_SURF_SPOTS.get(location.get("slug"))
    if not guide:
        return ""
    return (
        '<section class="section activity-panel surf-local-guide" aria-label="Local surfing context">'
        '<div class="section-head"><div><p class="eyebrow">LOCAL SURF CONTEXT</p>'
        f'<h2>Surf locations near {escape(location["name"])}</h2></div></div>'
        f'<h3>{escape(guide["spot"])}</h3>'
        f'<p>{escape(guide["summary"])}</p>'
        f'<p>{escape(guide["caution"])}</p>'
        '<p><strong>Coverage:</strong> CoastalNow uses NOAA/NWS area forecasts '
        'and rule-based scores, not real-time measurements at this surf break. '
        'No wave direction, board suitability or guaranteed safe surf is inferred.</p>'
        '<p><strong>Spot reference:</strong> '
        f'<a href="{escape(guide["url"], quote=True)}" rel="noopener noreferrer" target="_blank">'
        f'{escape(guide["source"])}</a> (external, descriptive guide; '
        'not a CoastalNow data provider).</p></section>'
    )


def surfing_meta_description(location: dict) -> str:
    guide = EXPANSION_SURF_SPOTS.get(location.get("slug"))
    if not guide:
        return (
            f'Surf conditions planning for {location["name"]}, {location["state"]}, '
            'with wave, wind, weather and tide context.'
        )
    return (
        f'{location["name"]}, {location["state"]} surf planning: NWS wave and wind '
        f'context, safety alerts and a local guide to {guide["spot"]}.'
    )
