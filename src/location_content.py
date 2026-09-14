"""Editorial search context for priority CoastalNow Tide landing pages.

Keep these notes factual and traceable to CoastalNow's configured page structure
and NOAA station metadata. They are not intended to replace live tide data.
"""

LOCATION_SEARCH_CONTEXT = {
    "oceanside": {
        "title": "Oceanside tide timing and nearby NOAA coverage",
        "paragraphs": [
            "For Oceanside, CoastalNow puts today’s next high and low tides ahead of the 7-day schedule so visitors can compare the immediate tide window with the rest of the week before planning time near the water.",
            "Oceanside uses NOAA’s La Jolla station as nearby coverage, about 24 miles away. Treat the prediction as a regional reference and allow for local differences in tide timing and height around Oceanside.",
        ],
    },
    "huntington-beach": {
        "title": "Huntington Beach tide timing and Newport Beach source",
        "paragraphs": [
            "The Huntington Beach page brings today’s next high and low tides, tide chart and 7-day schedule together so the current tide window is easy to compare with later events.",
            "Huntington Beach uses NOAA’s Newport Beach, Newport Bay Entrance station as nearby coverage, about 8 miles away. The page keeps that source visible because local tide timing and height can differ from the reference station.",
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
}
