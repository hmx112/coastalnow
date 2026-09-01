"""Deterministic, non-AI explanation prose for Activity results."""
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
    "heat-advisory": "Heat adds a modest planning penalty.",
    "excessive-heat-warning": "Excessive heat limits the recommendation.",
}

END_OF_DAY_STATUS = "No 3-hour window remaining"

# Ordered from the strongest / most decision-driving constraint to weaker ones.
# The order is independent of the order in which the scorer happened to append reasons.
_PRIMARY_CONSTRAINTS = (
    ("high-rip-current-risk", "A high rip-current risk", "is"),
    ("tornado-warning", "An active Tornado Warning", "is"),
    ("hurricane-warning", "An active Hurricane Warning", "is"),
    ("tropical-storm-warning", "An active Tropical Storm Warning", "is"),
    ("storm-surge-warning", "An active Storm Surge Warning", "is"),
    ("tsunami-warning", "An active Tsunami Warning", "is"),
    ("extreme-wind-warning", "An active Extreme Wind Warning", "is"),
    ("severe-thunderstorm-warning", "An active Severe Thunderstorm Warning", "is"),
    ("high-surf-warning", "An active High Surf Warning", "is"),
    ("special-marine-warning", "An active Special Marine Warning", "is"),
    ("coastal-flood-warning", "An active Coastal Flood Warning", "is"),
    ("flash-flood-warning", "An active Flash Flood Warning", "is"),
    ("wave-exposure-hard-stop", "Extreme nearshore wave exposure", "is"),
    ("wind-hard-stop", "Extreme winds", "are"),
    ("forecast-thunder-cap", "Thunderstorm conditions", "are"),
    ("rip-current-statement", "An active rip-current statement", "is"),
    ("wave-exposure-cap-39", "Strong nearshore wave exposure", "is"),
    ("wind-cap-39", "Very strong winds", "are"),
    ("coastal-flood-advisory", "Coastal flooding", "is"),
    ("excessive-heat-warning", "Excessive heat", "is"),
    ("wind-cap-59", "Strong winds", "are"),
    ("wave-exposure-cap-69", "Elevated nearshore wave exposure", "is"),
    ("small-craft-advisory", "An active Small Craft Advisory", "is"),
    ("wave-exposure-caution", "Nearshore wave exposure", "is"),
    ("long-period-swell", "Long-period swell", "is"),
    ("worsening-wind", "Stronger winds", "are"),
    ("wet-weather", "Rain chances", "are"),
    ("dense-fog-advisory", "Dense fog", "is"),
    ("heat-advisory", "Heat", "is"),
)

_POSITIVE_SUBJECTS = {
    "favorable-tide-movement": "tide movement",
    "light-wind": "winds",
    "manageable-sea-state": "nearshore waves",
}

_POSITIVE_NOUNS = {
    "favorable-tide-movement": "favorable tide movement",
    "light-wind": "light-to-moderate winds",
    "manageable-sea-state": "manageable nearshore waves",
}


def _unique(reason_codes: list[str]) -> list[str]:
    seen = set()
    result = []
    for code in reason_codes:
        if code not in seen:
            seen.add(code)
            result.append(code)
    return result


def _join_english(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _primary_constraint(reason_codes: list[str]) -> tuple[str, str] | None:
    reasons = set(reason_codes)
    for code, subject, verb in _PRIMARY_CONSTRAINTS:
        if code in reasons:
            return subject, verb
    return None


def _positive_subject_summary(reason_codes: list[str]) -> tuple[str, str] | None:
    subjects = [_POSITIVE_SUBJECTS[code] for code in reason_codes if code in _POSITIVE_SUBJECTS]
    if not subjects:
        return None
    return _capitalize_first(_join_english(subjects)), ("is" if len(subjects) == 1 else "are")


def _positive_noun_summary(reason_codes: list[str]) -> str:
    items = [_POSITIVE_NOUNS[code] for code in reason_codes if code in _POSITIVE_NOUNS]
    return _join_english(items)


def explain_reasons(reason_codes: list[str]) -> str:
    """Legacy fragment joiner retained for callers outside Fishing result summaries."""
    sentences = []
    for code in _unique(reason_codes):
        text = _REASON_TEXT.get(code)
        if text:
            sentences.append(text)
    return " ".join(sentences)


def summarize_fishing_result(day: dict) -> str:
    """Return a coherent, score-aware summary of the day's Fishing result.

    Safety/hard-stop/cap reasons lead the explanation. Favorable factors are only
    supporting context and never read as if they override a low score or safety
    constraint. Data-state and end-of-day states are explained independently of
    environmental quality so the prose cannot imply conditions that were not scored.
    """
    status = str(day.get("status") or "Unavailable")
    confidence = str(day.get("confidence") or "Unavailable")
    reasons = _unique(list(day.get("reasons") or []))

    if status == END_OF_DAY_STATUS:
        return (
            "Fewer than three hours remain in the local day, so a new 3-hour Fishing window is not shown. "
            "This is a timing state, not a statement that coastal conditions are unsafe."
        )

    if status == "Unavailable" or confidence == "Unavailable":
        return (
            "Critical coastal-condition data is unavailable, so CoastalNow cannot produce a normal Fishing recommendation for today. "
            "No favorable or unfavorable condition is inferred from missing data."
        )

    if status == "Limited" or confidence == "Limited":
        return (
            "Some critical coastal-condition data is incomplete, so today's Fishing recommendation is limited. "
            "Available factors are not treated as a full-condition assessment."
        )

    primary = _primary_constraint(reasons)
    positive_subjects = _positive_subject_summary(reasons)
    positive_nouns = _positive_noun_summary(reasons)

    if status == "NOT RECOMMENDED":
        if primary:
            subject, verb = primary
            first = f"{subject} {verb} the main reason this period is not recommended."
        else:
            first = "A safety constraint is the main reason this period is not recommended."
        if positive_subjects:
            subjects, verb = positive_subjects
            if verb == "is":
                second = f"{subjects} is otherwise favorable, but that positive factor does not override the safety constraint."
            else:
                second = f"{subjects} are otherwise favorable, but those positive factors do not override the safety constraint."
            return first + " " + second
        return first

    score = day.get("score")
    try:
        numeric_score = None if score is None else float(score)
    except (TypeError, ValueError):
        numeric_score = None

    if primary:
        subject, verb = primary
        if numeric_score is not None and numeric_score >= 70:
            first = f"{subject} {verb} the main factor keeping today's Fishing Score from being stronger."
        else:
            first = f"{subject} {verb} the main reason today's Fishing Score is limited."
        if positive_subjects:
            subjects, positive_verb = positive_subjects
            if positive_verb == "is":
                second = f"{subjects} is otherwise favorable, but that positive factor does not outweigh that constraint."
            else:
                second = f"{subjects} are otherwise favorable, but those positives do not outweigh that constraint."
            return first + " " + second
        return first

    if numeric_score is not None and numeric_score < 40:
        first = "Today's overall Fishing Score is low because the combined conditions are not supportive enough."
        if positive_nouns:
            return first + f" { _capitalize_first(positive_nouns) } help, but they are not enough to lift the overall result."
        return first

    if numeric_score is not None and numeric_score < 70:
        first = "Today's Fishing Score reflects mixed conditions rather than one dominant constraint."
        if positive_nouns:
            return first + f" { _capitalize_first(positive_nouns) } help, while the remaining factors keep the overall result moderate."
        return first

    if numeric_score is not None and numeric_score >= 70:
        first = "Conditions are generally supportive for today's best fishing window."
        if positive_nouns:
            return first + f" The main positives are {positive_nouns}."
        return first + " The overall score reflects the combined tide, wind, waves, weather and timing factors."

    return "The result reflects the combined tide movement, wind, waves, weather and time-of-day conditions."
