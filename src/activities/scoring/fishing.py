"""Fishing-specific quality, confidence and shoreline Safety Gate rules."""
from __future__ import annotations

import math
from datetime import datetime

from activities.scoring.engine import weighted_score
from activities.scoring.safety import SafetyDecision

FISHING_WEIGHTS = {
    "tide": 0.30,
    "wind": 0.20,
    "wave": 0.15,
    "weather": 0.15,
    "time_of_day": 0.10,
    "solunar": 0.05,
    "water_temperature": 0.05,
}

FISHING_HARD_STOP_EVENTS = {
    "Tornado Warning",
    "Hurricane Warning",
    "Tropical Storm Warning",
    "Storm Surge Warning",
    "Tsunami Warning",
    "Extreme Wind Warning",
    "Severe Thunderstorm Warning",
    "High Surf Warning",
    "Special Marine Warning",
    "Coastal Flood Warning",
    "Flash Flood Warning",
}


def tide_quality(phase_progress: float | None) -> float | None:
    if phase_progress is None:
        return None
    phase = float(phase_progress)
    if not 0 <= phase <= 1:
        raise ValueError("tide phase_progress must be between 0 and 1")
    return round(100.0 * math.sin(math.pi * phase), 1)


def wind_quality(speed_mph: float | None) -> float | None:
    if speed_mph is None:
        return None
    speed = float(speed_mph)
    if speed < 0:
        raise ValueError("wind speed cannot be negative")
    if speed <= 3:
        return 85
    if speed <= 12:
        return 100
    if speed <= 18:
        return 80
    if speed <= 24:
        return 55
    if speed <= 30:
        return 25
    return 0


def wave_quality(height_ft: float | None, period_s: float | None) -> float | None:
    if height_ft is None:
        return None
    height = float(height_ft)
    if height < 0:
        raise ValueError("wave height cannot be negative")
    if height < 1:
        base = 85
    elif height <= 3:
        base = 100
    elif height <= 5:
        base = 75
    elif height <= 7:
        base = 45
    elif height <= 9:
        base = 20
    else:
        base = 0

    if period_s is None:
        return base
    period = float(period_s)
    if period <= 0:
        raise ValueError("wave period must be positive")
    modifier = 0
    if period < 5:
        modifier = -10
    elif period > 13:
        modifier = -15
    return max(0, base + modifier)


def weather_quality(precip_probability_pct: float | None, condition_text: str = "") -> float | None:
    if precip_probability_pct is None:
        return None
    probability = float(precip_probability_pct)
    if not 0 <= probability <= 100:
        raise ValueError("precipitation probability must be between 0 and 100")
    if probability <= 20:
        score = 100
    elif probability <= 40:
        score = 75
    elif probability <= 60:
        score = 50
    else:
        score = 30
    text = (condition_text or "").lower()
    if "heavy rain" in text or "torrential rain" in text:
        score = max(0, score - 20)
    return score


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("solar/hourly timestamps must be offset-aware")
    return parsed


def time_of_day_quality(timestamp: str, solar: dict) -> float | None:
    required = ("civil_dawn", "sunrise", "sunset", "civil_dusk")
    if any(not solar.get(name) for name in required):
        return None
    current = _aware(timestamp)
    dawn = _aware(solar["civil_dawn"])
    sunrise = _aware(solar["sunrise"])
    sunset = _aware(solar["sunset"])
    dusk = _aware(solar["civil_dusk"])
    ninety_minutes = 90 * 60
    if abs((current - sunrise).total_seconds()) <= ninety_minutes:
        return 100
    if abs((current - sunset).total_seconds()) <= ninety_minutes:
        return 100
    if dawn <= current < sunrise or sunset < current <= dusk:
        return 90
    if sunrise <= current <= sunset:
        return 85
    return 60


def solunar_quality(moon_phase_fraction: float | None) -> float | None:
    if moon_phase_fraction is None:
        return None
    phase = float(moon_phase_fraction)
    if not 0 <= phase <= 1:
        raise ValueError("moon phase fraction must be between 0 and 1")
    # Keep this intentionally narrow: 50 at quarter moons, 70 at new/full.
    return round(50 + 20 * abs(math.cos(2 * math.pi * phase)), 1)


def water_temperature_quality(temp_f: float | None) -> float | None:
    if temp_f is None:
        return None
    temp = float(temp_f)
    # Species-agnostic, broad-extreme heuristic only. Weight is just 5%.
    if temp < 45:
        return 35
    if temp < 55:
        return 55
    if temp <= 75:
        return 75
    if temp <= 85:
        return 70
    return 50


def wave_exposure_index(height_ft: float | None, period_s: float | None) -> float | None:
    if height_ft is None or period_s is None:
        return None
    height = float(height_ft)
    period = float(period_s)
    if height < 0 or period <= 0:
        raise ValueError("wave exposure requires nonnegative height and positive period")
    return height * math.sqrt(period / 8.0)


def _angular_difference(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _onshore_gust_escalates(hour: dict, coast_bearing: float | None) -> bool:
    if coast_bearing is None:
        return False
    direction = hour.get("wind_direction_deg")
    gust = hour.get("gust_mph")
    if direction is None or gust is None or float(gust) < 25:
        return False
    return _angular_difference(float(direction) % 360, float(coast_bearing) % 360) <= 45


def _apply_exposure_tier(decision: SafetyDecision, tier: int) -> None:
    if tier <= 0:
        return
    if tier == 1:
        decision.add_penalty(8, "wave-exposure-caution")
    elif tier == 2:
        decision.add_cap(69, "wave-exposure-cap-69")
    elif tier == 3:
        decision.add_cap(39, "wave-exposure-cap-39")
    else:
        decision.add_hard_stop("wave-exposure-hard-stop")


def fishing_safety_decision(hour: dict, alerts: list[dict], *, coast_bearing: float | None) -> SafetyDecision:
    decision = SafetyDecision()

    for item in alerts:
        event = str(item.get("event") or "").strip()
        if event in FISHING_HARD_STOP_EVENTS:
            decision.add_hard_stop(event.lower().replace(" ", "-"))
            continue
        if event == "Rip Current Statement":
            text = " ".join(str(item.get(name) or "") for name in ("headline", "description")).lower()
            if "high rip current risk" in text:
                decision.add_hard_stop("high-rip-current-risk")
            else:
                decision.add_cap(39, "rip-current-statement")
        elif event == "Small Craft Advisory":
            decision.add_cap(69, "small-craft-advisory")
        elif event == "Dense Fog Advisory":
            decision.add_penalty(15, "dense-fog-advisory")
        elif event == "Coastal Flood Advisory":
            decision.add_cap(59, "coastal-flood-advisory")
        elif event == "Heat Advisory":
            decision.add_penalty(10, "heat-advisory")
        elif event == "Excessive Heat Warning":
            decision.add_cap(59, "excessive-heat-warning")

    sustained = hour.get("wind_mph")
    gust = hour.get("gust_mph")
    sustained = None if sustained is None else float(sustained)
    gust = None if gust is None else float(gust)
    if (sustained is not None and sustained >= 40) or (gust is not None and gust >= 50):
        decision.add_hard_stop("wind-hard-stop")
    elif (sustained is not None and sustained >= 30) or (gust is not None and gust >= 40):
        decision.add_cap(39, "wind-cap-39")
    elif (sustained is not None and sustained >= 25) or (gust is not None and gust >= 35):
        decision.add_cap(59, "wind-cap-59")

    exposure = wave_exposure_index(hour.get("wave_height_ft"), hour.get("wave_period_s"))
    if exposure is not None:
        if exposure < 3.5:
            tier = 0
        elif exposure < 5.5:
            tier = 1
        elif exposure < 7.5:
            tier = 2
        elif exposure < 9.5:
            tier = 3
        else:
            tier = 4
        if tier and _onshore_gust_escalates(hour, coast_bearing):
            tier = min(4, tier + 1)
        _apply_exposure_tier(decision, tier)

    if "thunderstorm" in str(hour.get("condition_text") or "").lower():
        decision.add_cap(39, "forecast-thunder-cap")
    return decision


def fishing_confidence(
    hour: dict,
    freshness: dict,
    *,
    tide_available: bool,
    solunar_available: bool,
) -> str:
    if not freshness.get("normal_safety_state_allowed") or freshness.get("alerts") != "fresh":
        return "Unavailable"
    if not tide_available:
        return "Unavailable"
    if hour.get("wind_mph") is None or hour.get("precip_probability_pct") is None:
        return "Unavailable"
    if hour.get("wave_height_ft") is None or hour.get("wave_period_s") is None:
        return "Limited"
    if freshness.get("forecast") != "fresh" or not freshness.get("high_medium_eligible"):
        return "Limited"
    if hour.get("water_temperature_f") is None or not solunar_available:
        return "Medium"
    return "High"


def fishing_components(
    hour: dict,
    *,
    tide_phase_progress: float | None,
    solar: dict,
    moon_phase_fraction: float | None,
) -> dict[str, float | None]:
    return {
        "tide": tide_quality(tide_phase_progress),
        "wind": wind_quality(hour.get("wind_mph")),
        "wave": wave_quality(hour.get("wave_height_ft"), hour.get("wave_period_s")),
        "weather": weather_quality(hour.get("precip_probability_pct"), hour.get("condition_text", "")),
        "time_of_day": time_of_day_quality(hour["time"], solar),
        "solunar": solunar_quality(moon_phase_fraction),
        "water_temperature": water_temperature_quality(hour.get("water_temperature_f")),
    }


def score_fishing_hour(
    hour: dict,
    *,
    tide_phase_progress: float | None,
    solar: dict,
    moon_phase_fraction: float | None,
    alerts: list[dict],
    freshness: dict,
    tide_available: bool,
    coast_bearing: float | None,
) -> dict:
    components = fishing_components(
        hour,
        tide_phase_progress=tide_phase_progress,
        solar=solar,
        moon_phase_fraction=moon_phase_fraction,
    )
    quality = weighted_score(components, FISHING_WEIGHTS)
    confidence = fishing_confidence(
        hour,
        freshness,
        tide_available=tide_available,
        solunar_available=moon_phase_fraction is not None,
    )
    safety = fishing_safety_decision(hour, alerts, coast_bearing=coast_bearing).apply(quality)

    reasons = []
    if components["tide"] is not None and components["tide"] >= 80:
        reasons.append("favorable-tide-movement")
    if components["wind"] is not None and components["wind"] >= 80:
        reasons.append("light-wind")
    if components["wave"] is not None and components["wave"] >= 75:
        reasons.append("manageable-sea-state")
    if components["wind"] is not None and components["wind"] <= 55:
        reasons.append("worsening-wind")
    if components["weather"] is not None and components["weather"] <= 50:
        reasons.append("wet-weather")
    if hour.get("wave_period_s") is not None and float(hour["wave_period_s"]) > 13:
        reasons.append("long-period-swell")
    reasons.extend(safety["reasons"])

    return {
        "time": hour["time"],
        "components": components,
        "raw_quality_score": quality,
        "final_score": safety["final_score"],
        "hard_stop": safety["hard_stop"],
        "safety_status": safety["status"],
        "safety_cap": safety["cap"],
        "safety_penalty": safety["penalty"],
        "confidence": confidence,
        "available": confidence != "Unavailable",
        "ranking_eligible": confidence in {"High", "Medium"} and not safety["hard_stop"] and safety["final_score"] is not None,
        "reasons": reasons,
    }
