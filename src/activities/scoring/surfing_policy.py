"""Surfing-specific planning score, confidence, and conservative Safety Gate."""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from activities.conditions.validation import assess_snapshot_freshness
from activities.scoring.engine import best_continuous_window, group_local_days, weighted_score
from activities.scoring.safety import SafetyDecision

SURFING_WEIGHTS = {
    "wave_height": 0.30,
    "wave_period": 0.25,
    "wind": 0.25,
    "weather": 0.10,
    "daylight": 0.10,
}

SURFING_HARD_STOP_EVENTS = {
    "Tsunami Warning",
    "Hurricane Warning",
    "Tropical Storm Warning",
    "Storm Surge Warning",
    "Extreme Wind Warning",
    "Severe Thunderstorm Warning",
    "High Surf Warning",
    "Special Marine Warning",
    "Coastal Flood Warning",
}


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must be offset-aware")
    return parsed


def wave_height_quality(height_ft: float | None) -> float | None:
    if height_ft is None:
        return None
    height = float(height_ft)
    if height < 0:
        raise ValueError("wave height cannot be negative")
    if height < 1:
        return 35
    if height < 2:
        return 70
    if height <= 4:
        return 100
    if height <= 6:
        return 85
    if height <= 8:
        return 55
    if height <= 10:
        return 25
    return 0


def wave_period_quality(period_s: float | None) -> float | None:
    if period_s is None:
        return None
    period = float(period_s)
    if period <= 0:
        raise ValueError("wave period must be positive")
    if period < 5:
        return 25
    if period < 7:
        return 55
    if period < 9:
        return 75
    if period <= 13:
        return 100
    if period <= 16:
        return 85
    return 65


def wind_quality(speed_mph: float | None) -> float | None:
    if speed_mph is None:
        return None
    speed = float(speed_mph)
    if speed < 0:
        raise ValueError("wind speed cannot be negative")
    if speed <= 3:
        return 100
    if speed <= 8:
        return 90
    if speed <= 12:
        return 70
    if speed <= 18:
        return 45
    if speed <= 25:
        return 20
    return 0


def weather_quality(precip_probability_pct: float | None, condition_text: str = "") -> float | None:
    if precip_probability_pct is None:
        return None
    probability = float(precip_probability_pct)
    if not 0 <= probability <= 100:
        raise ValueError("precipitation probability must be between 0 and 100")
    if probability <= 20:
        score = 100
    elif probability <= 40:
        score = 80
    elif probability <= 60:
        score = 55
    else:
        score = 30
    text = str(condition_text or "").lower()
    if "heavy rain" in text or "torrential rain" in text:
        score = max(0, score - 25)
    return score


def daylight_quality(timestamp: str, solar: dict) -> float | None:
    dawn_raw = solar.get("civil_dawn") or solar.get("dawn")
    dusk_raw = solar.get("civil_dusk") or solar.get("dusk")
    if not dawn_raw or not dusk_raw:
        return None
    current = _aware(timestamp)
    dawn = _aware(dawn_raw)
    dusk = _aware(dusk_raw)
    if dawn <= current <= dusk:
        return 100
    if dawn - timedelta(hours=1) <= current < dawn:
        return 60
    if dusk < current <= dusk + timedelta(hours=1):
        return 60
    return 35


def wave_exposure_index(height_ft: float | None, period_s: float | None) -> float | None:
    if height_ft is None or period_s is None:
        return None
    height = float(height_ft)
    period = float(period_s)
    if height < 0 or period <= 0:
        raise ValueError("wave exposure requires nonnegative height and positive period")
    return height * math.sqrt(period / 8.0)


def surfing_safety_decision(hour: dict, alerts: list[dict], *, coast_bearing: float | None) -> SafetyDecision:
    """Apply broad coastal safety gates without claiming break-specific suitability."""
    decision = SafetyDecision()

    for item in alerts:
        event = str(item.get("event") or "").strip()
        if event in SURFING_HARD_STOP_EVENTS:
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
        if exposure >= 13.5:
            decision.add_hard_stop("wave-exposure-hard-stop")
        elif exposure >= 10.5:
            decision.add_cap(39, "wave-exposure-cap-39")
        elif exposure >= 7.5:
            decision.add_cap(69, "wave-exposure-cap-69")
        elif exposure >= 5:
            decision.add_penalty(8, "wave-exposure-caution")

    if "thunderstorm" in str(hour.get("condition_text") or "").lower():
        decision.add_cap(39, "forecast-thunder-cap")
    return decision


def _marine_freshness(snapshot: dict, now: datetime) -> str:
    provider = (snapshot.get("providers") or {}).get("marine") or {}
    if provider.get("status") != "ok":
        return "unavailable"
    try:
        fetched = _aware(provider["fetched_at_utc"])
    except (KeyError, TypeError, ValueError):
        return "unavailable"
    age_hours = (now - fetched).total_seconds() / 3600
    if age_hours < 0:
        return "unavailable"
    return "fresh" if age_hours <= 6 else "stale"


def surfing_confidence(hour: dict, freshness: dict) -> str:
    if not freshness.get("normal_safety_state_allowed") or freshness.get("alerts") != "fresh":
        return "Unavailable"
    if hour.get("wind_mph") is None or hour.get("precip_probability_pct") is None:
        return "Unavailable"
    if hour.get("wave_height_ft") is None or hour.get("wave_period_s") is None:
        return "Limited"
    if freshness.get("forecast") != "fresh" or freshness.get("marine") != "fresh":
        return "Limited"
    if not freshness.get("high_medium_eligible"):
        return "Limited"
    return "High"


def surfing_components(hour: dict, *, solar: dict) -> dict[str, float | None]:
    return {
        "wave_height": wave_height_quality(hour.get("wave_height_ft")),
        "wave_period": wave_period_quality(hour.get("wave_period_s")),
        "wind": wind_quality(hour.get("wind_mph")),
        "weather": weather_quality(hour.get("precip_probability_pct"), hour.get("condition_text", "")),
        "daylight": daylight_quality(hour["time"], solar),
    }


def score_surfing_hour(
    hour: dict,
    *,
    solar: dict,
    alerts: list[dict],
    freshness: dict,
    coast_bearing: float | None,
) -> dict:
    components = surfing_components(hour, solar=solar)
    quality = weighted_score(components, SURFING_WEIGHTS)
    confidence = surfing_confidence(hour, freshness)
    safety = surfing_safety_decision(hour, alerts, coast_bearing=coast_bearing).apply(quality)

    reasons: list[str] = []
    if components["wave_height"] is not None and components["wave_height"] >= 85:
        reasons.append("moderate-wave-height")
    if components["wave_period"] is not None and components["wave_period"] >= 85:
        reasons.append("organized-wave-period")
    if components["wind"] is not None and components["wind"] >= 70:
        reasons.append("lighter-wind")
    if components["wind"] is not None and components["wind"] <= 45:
        reasons.append("stronger-wind")
    if components["weather"] is not None and components["weather"] <= 55:
        reasons.append("wet-weather")
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
        "ranking_eligible": (
            confidence in {"High", "Medium"}
            and not safety["hard_stop"]
            and safety["final_score"] is not None
        ),
        "reasons": reasons,
    }


def _alert_active_at(item: dict, timestamp: str) -> bool:
    target = _aware(timestamp)
    start = item.get("onset") or item.get("effective")
    end = item.get("ends") or item.get("expires")
    try:
        if start and target < _aware(start):
            return False
        if end and target > _aware(end):
            return False
    except ValueError:
        return True
    return True


def _unique_reasons(rows: list[dict]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for row in rows:
        for reason in row.get("reasons", []):
            if reason not in seen:
                seen.add(reason)
                output.append(reason)
    return output


def _summarize_day(rows: list[dict]) -> dict:
    best = best_continuous_window(rows, hours=3)
    if best is not None:
        return {
            "status": "normal",
            "score": best["score"],
            "rating": best["rating"],
            "confidence": best["confidence"],
            "best_window": {"start": best["start"], "end": best["end"]},
            "ranking_eligible": True,
            "reasons": _unique_reasons(best["hours"]),
        }

    hard_stop_rows = [row for row in rows if row.get("hard_stop")]
    if hard_stop_rows:
        return {
            "status": "NOT RECOMMENDED",
            "score": None,
            "rating": None,
            "confidence": max(
                (row.get("confidence", "Unavailable") for row in hard_stop_rows),
                key=lambda value: {"High": 0, "Medium": 1, "Limited": 2, "Unavailable": 3}.get(value, 3),
                default="Unavailable",
            ),
            "best_window": None,
            "ranking_eligible": False,
            "reasons": _unique_reasons(hard_stop_rows),
        }

    limited_rows = [row for row in rows if row.get("confidence") == "Limited"]
    if limited_rows:
        return {
            "status": "Limited",
            "score": None,
            "rating": None,
            "confidence": "Limited",
            "best_window": None,
            "ranking_eligible": False,
            "reasons": _unique_reasons(limited_rows),
        }

    return {
        "status": "Unavailable",
        "score": None,
        "rating": None,
        "confidence": "Unavailable",
        "best_window": None,
        "ranking_eligible": False,
        "reasons": _unique_reasons(rows),
    }


def score_surfing_activity(snapshot: dict, *, location: dict, now: datetime) -> dict:
    """Score Today/Tomorrow from one shared Condition Snapshot."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    freshness = assess_snapshot_freshness(snapshot, now)
    freshness["marine"] = _marine_freshness(snapshot, now)
    grouped = group_local_days(snapshot.get("hourly", []), location["timezone"], now)
    astronomy = snapshot.get("astronomy") or {}
    coast_bearing = (location.get("activity") or {}).get("coast_bearing")
    all_alerts = (snapshot.get("alerts") or {}).get("items", [])
    scored_days: dict[str, list[dict]] = {}

    for label in ("today", "tomorrow"):
        solar = astronomy.get(label) or {}
        rows: list[dict] = []
        for hour in grouped[label]:
            active = [item for item in all_alerts if _alert_active_at(item, hour["time"])]
            rows.append(
                score_surfing_hour(
                    hour,
                    solar=solar,
                    alerts=active,
                    freshness=freshness,
                    coast_bearing=coast_bearing,
                )
            )
        scored_days[label] = rows

    return {
        "schema_version": 1,
        "activity": "surfing",
        "location": location["slug"],
        "scorer_version": "surfing-v1",
        "generated_at_utc": now.isoformat(timespec="seconds"),
        "input_snapshot_generated_at_utc": snapshot.get("generated_at_utc"),
        "freshness": freshness,
        "today": _summarize_day(scored_days["today"]),
        "tomorrow": _summarize_day(scored_days["tomorrow"]),
        "hourly": scored_days,
        "scope": "general coastal surf planning; not break-specific",
        "safety_disclaimer": (
            "Surf Conditions Score is a planning metric, not a safety guarantee or a break-specific forecast. "
            "Official warnings and local guidance always take priority."
        ),
    }
