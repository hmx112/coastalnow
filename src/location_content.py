"""Editorial search context for priority CoastalNow Tide landing pages.

Keep these notes factual and traceable to CoastalNow's configured page structure
and NOAA station metadata. They are not intended to replace live tide data.
"""

LOCATION_SEARCH_CONTEXT = {
    "oceanside": {
        "title": "Oceanside tide timing and nearby NOAA coverage",
        "paragraphs": [
            "Use the Oceanside seven-day tide table to compare the predicted time of each low tide across possible visit dates. For beach access or an exposed shoreline visit, the height at a reference station is planning context, not a guarantee of dry or safe ground.",
            "Oceanside uses NOAA station 9410230 at La Jolla, about 24 miles away, rather than an Oceanside-specific gauge. Because the La Jolla tide page also uses that reference, their displayed station predictions may match; neither should be mistaken for an independent on-site measurement at Oceanside.",
        ],
    },
    "huntington-beach": {
        "title": "Huntington Beach tide timing and Newport Beach source",
        "paragraphs": [
            "For a Huntington Beach outing, compare the next predicted low tide with the later lows in the seven-day table, rather than treating a single low-tide time as a fixed daily schedule. Actual shoreline exposure depends on conditions not measured by a tide prediction alone.",
            "Huntington Beach uses Newport Beach, Newport Bay Entrance NOAA station 9410580, roughly 8 miles away. Dana Point also references this station, so identical forecasts across those pages represent the same NOAA source, not two separate local measurements. The ocean beach and the station entrance may differ.",
        ],
    },
    "malibu": {
        "title": "Malibu tides today and nearby Santa Monica NOAA coverage",
        "paragraphs": [
            "The Malibu tide page pairs today’s high and low tide timing with the tide chart and 7-day Malibu tide schedule so search visitors can move from today’s answer to the weekly pattern without changing pages.",
            "Malibu uses NOAA’s Santa Monica station as nearby coverage, about 10 miles away. CoastalNow keeps that source relationship visible because local tide timing and height around Malibu may differ from the reference station.",
        ],
        "today_summary": True,
        "meta_description": "Check Malibu tides today, including high and low tide times, today’s tide chart, a 7-day Malibu tide schedule, and nearby NOAA Santa Monica source details.",
        "related_links": [
            {"label": "Santa Monica tides", "href": "/tides/california/santa-monica/"},
            {"label": "Los Angeles tides", "href": "/tides/california/los-angeles/"},
        ],
    },
    "miami-beach": {
        "title": "Miami Beach tides and the Government Cut NOAA source",
        "paragraphs": [
            "For Miami Beach, the next tide answer, today’s high and low events and the 7-day schedule are shown together so search visitors can get the immediate answer without losing the weekly context.",
            "Miami Beach is configured to use NOAA’s Government Cut, Miami Harbor Entrance station. CoastalNow keeps the NOAA source and station details on the page so the prediction can be traced to its data source.",
        ],
    },
    "clearwater-beach": {
        "title": "Clearwater Beach tide timing on Florida’s Gulf Coast",
        "paragraphs": [
            "The Clearwater Beach tide page prioritizes the next high or low tide, then shows today’s tide chart and the 7-day schedule for a quick view of how the day fits into the week.",
            "Clearwater Beach uses the configured NOAA Clearwater Beach station for its tide predictions, with station and source details shown alongside the forecast information.",
        ],
    },
    "long-beach": {
        "title": "Long Beach tides and the Fire Boat Pier NOAA station",
        "paragraphs": [
            "Long Beach tide searchers can see the next tide first, followed by today’s high and low events, a tide chart and the 7-day schedule in one page.",
            "Long Beach uses NOAA’s Long Beach Fire Boat Pier station. The station, datum and NOAA source details remain visible so the published tide times can be traced back to the configured source.",
        ],
    },
    "dana-point": {
        "title": "Dana Point tides with nearby Newport Beach NOAA coverage",
        "paragraphs": [
            "The Dana Point page combines the next tide, today’s high and low events, the tide chart and the 7-day schedule so the immediate answer and weekly pattern are available together.",
            "Dana Point uses NOAA’s Newport Beach, Newport Bay Entrance station as nearby coverage, about 14.5 miles away. CoastalNow flags that relationship because local Dana Point tide timing and height may differ from the reference station.",
        ],
    },
    "key-biscayne": {
        "title": "Key Biscayne tides with nearby Virginia Key coverage",
        "paragraphs": [
            "For Key Biscayne, CoastalNow leads with the next tide and then provides today’s events, tide chart and 7-day schedule so the page answers both “what is next?” and “what comes later?”",
            "Key Biscayne uses NOAA’s Virginia Key station as nearby coverage, about 2.7 miles away. The nearby-station disclosure stays visible so users know where the prediction originates.",
        ],
    },
    "west-palm-beach": {
        "title": "West Palm Beach tides with Lake Worth Pier coverage",
        "paragraphs": [
            "The West Palm Beach tide page puts the next high or low tide before the full chart and 7-day schedule so the immediate tide answer is easy to find while keeping the longer forecast available.",
            "West Palm Beach uses NOAA’s Lake Worth Pier, Atlantic Ocean station as nearby coverage, about 7.2 miles away. CoastalNow identifies that source because local tide timing and height may differ from the reference point.",
        ],
    },
    "corolla": {
        "title": "Corolla tide times and the nearby Duck NOAA station",
        "paragraphs": [
            "Corolla's high and low tide predictions on this page come from NOAA station 8651370 at Duck, North Carolina. This is nearby reference coverage, not a water-level reading taken on Corolla's beach. Check the station name and datum before using the figures for a specific access point.",
            "For a Corolla low-tide visit, compare the local-time lows in the seven-day schedule and note how their predicted heights differ. The lowest predicted event at Duck is not a promise that a particular ocean access, sound-side shoreline or inlet crossing will be passable or safe.",
            "Nearby Outer Banks communities have separate Tide pages so visitors can compare station provenance and the timings shown there instead of assuming one prediction applies identically across the whole coast.",
        ],
        "meta_description": "Corolla, NC tide times today, 7-day high and low tide chart, and nearby NOAA Duck station source details for Outer Banks planning.",
        "related_links": [
            {"label": "Kitty Hawk tides", "href": "/tides/north-carolina/kitty-hawk/"},
            {"label": "Nags Head tides", "href": "/tides/north-carolina/nags-head/"},
        ],
    },
    "half-moon-bay": {
        "title": "Half Moon Bay low tides and Pillar Point Harbor predictions",
        "paragraphs": [
            "The Half Moon Bay tide table is sourced from NOAA station 9414131 at Pillar Point Harbor. It gives predicted high and low tide times in local Pacific time, with heights referenced to the station's tidal datum; those heights are not a measurement of water depth on every beach.",
            "If you are comparing possible dates for observing the shoreline or tide pools, find the predicted low events in the seven-day schedule and compare their times and heights. A lower predicted tide can help with timing, but it does not establish safe tide-pool access: breaking waves, swell, closures and the return of rising water require separate checks.",
            "The seven-day high-to-low comparison summarizes how much the station's predicted levels vary on each date. It does not identify which particular tide pool or walking route is accessible.",
        ],
        "page_title": "Half Moon Bay High & Low Tide Times | CoastalNow",
        "meta_description": "Half Moon Bay tide times, 7-day high and low tide chart, and NOAA Pillar Point Harbor data for planning shoreline and tide-pool visits.",
        "related_links": [
            {"label": "Santa Cruz tides", "href": "/tides/california/santa-cruz/"},
            {"label": "San Francisco tides", "href": "/tides/california/san-francisco/"},
        ],
    },
    "fort-lauderdale": {
        "title": "Fort Lauderdale tides and Anglin Fishing Pier station coverage",
        "paragraphs": [
            "Fort Lauderdale tide predictions here use NOAA station 8722899 at Anglin Fishing Pier in Lauderdale-by-the-Sea. The station name is important when comparing a predicted high or low with conditions elsewhere along the Fort Lauderdale coastline or near an inlet.",
            "For beach or shore-fishing plans, read the next high or low tide first, then check the seven-day sequence for a later window. These are astronomical predictions for the NOAA reference site; wind, waves and current conditions must be considered separately and may change the actual water level.",
            "The daily high-to-low differences on this page compare predicted heights within each date at that station. They do not indicate surf safety, rip-current risk or whether an inlet is suitable for boating.",
        ],
        "page_title": "Fort Lauderdale High & Low Tide Times | CoastalNow",
        "meta_description": "Fort Lauderdale high and low tide times, 7-day NOAA chart, and Anglin Fishing Pier station details for local coastal planning.",
        "related_links": [
            {"label": "Pompano Beach tides", "href": "/tides/florida/pompano-beach/"},
            {"label": "Miami Beach tides", "href": "/tides/florida/miami-beach/"},
        ],
    },
    "holden-beach": {
        "title": "Holden Beach tides and the Shallotte Inlet NOAA reference",
        "paragraphs": [
            "Holden Beach tide events shown here are predicted for NOAA station 8659665 at Bowen Point, Shallotte Inlet. Because this is an inlet station, its published times and heights should not be treated as simultaneous observed water levels along every stretch of Holden Beach.",
            "For a planned low-tide walk or shore visit, compare multiple low-tide events over the next seven days and read their local-time labels. Conditions along a beach, waterway or inlet can differ from the reference prediction, and a predicted low does not establish that an access route is safe.",
            "The tide curve and daily high-to-low comparison help describe the timing and relative predicted range at the source station; they are not a live water-depth or current-speed measurement.",
        ],
        "meta_description": "Holden Beach, NC tide times, high and low tides, 7-day chart, and NOAA Bowen Point at Shallotte Inlet reference details.",
        "related_links": [
            {"label": "Carolina Beach tides", "href": "/tides/north-carolina/carolina-beach/"},
            {"label": "Wrightsville Beach tides", "href": "/tides/north-carolina/wrightsville-beach/"},
        ],
    },
    "los-angeles": {
        "title": "Los Angeles tides: using the NOAA station's 7-day predictions",
        "paragraphs": [
            "The Los Angeles Tide page uses NOAA station 9410660. Its high and low water levels are tied to that station's tidal datum, not to a universal depth or a measurement at every nearby beach, harbor or inlet.",
            "To compare a morning coastal outing with an afternoon one, read the ordered high/low events in the current day's chart, then check the next few days: tide times move rather than staying fixed at the same hour every day.",
            "For the adjacent Santa Monica and Long Beach coastlines, compare their Tide pages and NOAA station labels rather than assuming the Los Angeles station prediction is exact for those locations.",
        ],
        "meta_description": "Los Angeles tide times today, high and low tides, 7-day tide chart, and NOAA station 9410660 source details.",
        "related_links": [
            {"label": "Santa Monica tides", "href": "/tides/california/santa-monica/"},
            {"label": "Long Beach tides", "href": "/tides/california/long-beach/"},
        ],
    },

}
