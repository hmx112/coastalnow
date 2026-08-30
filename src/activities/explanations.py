"""Deterministic, non-AI explanation fragments for Activity results."""
from __future__ import annotations

_REASON_TEXT = {
    "favorable-tide-movement": "Moving tide supports the fishing window.",
    "light-wind": "Winds are light to moderate.",
    "manageable-sea-state": "Nearshore wave conditions are manageable.",
    "worsening-wind": "Stronger winds reduce the quality of this window.",
    "wet-weather": "Rain chances reduce the quality of this window.",
    "long-period-swell": "Long-period swell increases shoreline exposure.",
    "wave-exposure-caution": "Nearshore wave exposure warrants extra caution.",
    "wave-exposure-cap-69": "Elevated wave exposure limits the recommendation.",
    "wave-exposure-cap-39": "Strong wave exposure sharply limits the recommendation.",
    "wave-exposure-hard-stop": "Extreme wave exposure makes this period not recommended.",
    "wind-cap-59": "Strong winds limit the recommendation.",
    "wind-cap-39": "Very strong winds sharply limit the recommendation.",
    "wind-hard-stop": "Extreme winds make this period not recommended.",
    "forecast-thunder-cap": "Thunderstorm conditions sharply limit the recommendation.",
    "high-rip-current-risk": "A high rip-current risk makes shoreline fishing not recommended.",
    "rip-current-statement": "An active rip-current statement sharply limits the recommendation.",
    "small-craft-advisory": "An active Small Craft Advisory indicates rougher nearshore conditions.",
    "dense-fog-advisory": "Dense fog reduces visibility near the shore.",
    "coastal-flood-advisory": "Coastal flooding may affect shoreline access.",
}


def explain_reasons(reason_codes: list[str]) -> str:
    """Return stable prose for known reason codes, preserving first-seen order."""
    seen = set()
    sentences = []
    for code in reason_codes:
        if code in seen:
            continue
        seen.add(code)
        text = _REASON_TEXT.get(code)
        if text:
            sentences.append(text)
    return " ".join(sentences)
