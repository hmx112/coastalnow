"""Site-specific official fishing/access context for the four new locations.

These editorial notes are not catch forecasts and cannot replace active alerts.
Only current NOAA/NWS forecast inputs feed CoastalNow numerical Fishing Scores.
"""
from __future__ import annotations

from html import escape


NEW_FISHING_GUIDES = {
    "jacksonville-beach": {
        "place": "Jacksonville Beach Fishing Pier and Atlantic beach access",
        "summary": (
            "Jacksonville Beach has a public oceanfront fishing pier and beach access "
            "points. The tide data shown by CoastalNow are predictions from the nearby "
            "Mayport (Bar Pilots Dock) NOAA station, not a sensor on the pier. "
            "The St. Johns River entrance and oceanfront may differ in tide height "
            "and exact turning-point time."
        ),
        "caution": (
            "Use official city access notices, current pier rules and lifeguard "
            "information. A favorable Fishing Score is not a catch prediction or "
            "evidence that wave, rip-current or pier conditions are safe."
        ),
        "source": "City of Jacksonville Beach – Beach Rules",
        "url": "https://www.jacksonvillebeach.org/202/Beach-Rules",
    },
    "sebastian-inlet": {
        "place": "Sebastian Inlet State Park north and south jetties",
        "summary": (
            "Florida State Parks identifies the inlet's two fishing jetties as "
            "shore-fishing destinations. NOAA 8722004 is the Sebastian Inlet bridge "
            "high/low tide station; its predicted water heights are not a "
            "measurement of current speed between the jetties or in the Atlantic surf."
        ),
        "caution": (
            "The inlet can have strong flowing water, surf and slippery rocks. "
            "Check official park advisories and NWS marine and safety alerts before "
            "visiting. The curve displayed between NOAA high/low events is a "
            "derived visualization, not a separate NOAA interval forecast."
        ),
        "source": "Florida State Parks – Beach at Sebastian Inlet",
        "url": "https://www.floridastateparks.org/learn/beach-sebastian-inlet",
    },
    "galveston": {
        "place": "Galveston Gulf shore and Galveston Island State Park fishing",
        "summary": (
            "Texas Parks and Wildlife describes both Gulf beach-side and bay-side "
            "fishing at Galveston Island State Park. CoastalNow uses NOAA Galveston "
            "Pleasure Pier station 8771510 on the Gulf side; predictions at this "
            "station should not be taken as identical at every park bay shoreline."
        ),
        "caution": (
            "Check current park rules, fishing license requirements where applicable "
            "and official marine alerts. Wind, waves and tidal currents can change "
            "conditions separately from the NOAA high/low heights. "
            "The Fishing Score does not predict fish catches or safe wading."
        ),
        "source": "Texas Parks and Wildlife – Galveston Island State Park",
        "url": "https://tpwd.texas.gov/state-parks/galveston-island",
    },
    "port-aransas": {
        "place": "Port Aransas Gulf-side jetty",
        "summary": (
            "Port Aransas has Gulf-facing jetties and shore-fishing access. NOAA "
            "station 8775237 supplies its high/low tide predictions. "
            "Predicted heights at the station are not observed jetty currents, "
            "water depths or wave measurements beside the rocks."
        ),
        "caution": (
            "Rock jetties can be hazardous in surf or strong currents. Verify local "
            "public-access restrictions, current NWS warnings and Texas fishing "
            "regulations. CoastalNow's general score is neither a real-time "
            "fishing report nor a safety guarantee."
        ),
        "source": "Texas Parks and Wildlife – Coastal Jetties",
        "url": "https://tpwd.texas.gov/fishing/sea-center-texas/flora-fauna-guide/jetties",
    },
}


def fishing_location_guide_html(location: dict) -> str:
    """Return attributable local utility on new Fishing pages only."""
    guide = NEW_FISHING_GUIDES.get(location.get("slug"))
    if guide is None:
        return ""
    return (
        '<section class="section activity-panel fishing-local-guide" aria-label="Local fishing context">'
        '<div class="section-head"><div><p class="eyebrow">LOCAL FISHING CONTEXT</p>'
        f'<h2>Fishing locations near {escape(location["name"])}</h2></div></div>'
        f'<h3>{escape(guide["place"])}</h3>'
        f'<p>{escape(guide["summary"])}</p>'
        f'<p>{escape(guide["caution"])}</p>'
        '<p><strong>Planning data:</strong> NOAA tide predictions and NWS forecast and '
        'alert information. The numerical Fishing Score is a CoastalNow '
        'rule-based indicator, not a fish-bite forecast and not a safety guarantee.</p>'
        '<p><strong>Local access reference:</strong> '
        f'<a href="{escape(guide["url"], quote=True)}" target="_blank" '
        'rel="noopener noreferrer">'
        f'{escape(guide["source"])}</a> (external official information; '
        'not used as the numerical scoring data source).</p></section>'
    )


def fishing_meta_description(location: dict) -> str:
    guide = NEW_FISHING_GUIDES.get(location.get("slug"))
    if not guide:
        return (
            f'Fishing conditions today for {location["name"]}, {location["state"]}, '
            'including tide, wind, waves, best fishing time and safety context.'
        )
    return (
        f'{location["name"]}, {location["state"]} fishing conditions, NOAA tide '
        f'predictions, NWS wind/wave alerts and local access context.'
    )
