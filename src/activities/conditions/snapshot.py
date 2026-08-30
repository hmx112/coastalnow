"""Build provider-independent Condition Snapshot dictionaries."""
from __future__ import annotations

from copy import deepcopy


def build_snapshot(
    location: dict,
    *,
    generated_at_utc: str,
    hourly: list[dict],
    providers: dict,
    alerts: dict,
    provenance: dict,
) -> dict:
    """Return a serializable snapshot without inventing or reordering source values."""
    return {
        "schema_version": 1,
        "location": location["slug"],
        "timezone": location["timezone"],
        "generated_at_utc": generated_at_utc,
        "providers": deepcopy(providers),
        "hourly": deepcopy(hourly),
        "alerts": deepcopy(alerts),
        "provenance": deepcopy(provenance),
    }
