"""Deterministic solar/lunar helpers for Activity timing factors."""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone


def _sun_utc_hours(day: date, latitude: float, longitude: float, *, sunrise: bool, zenith: float) -> float | None:
    """Approximate UTC solar event using the standard NOAA/USNO sunrise equation."""
    n = day.timetuple().tm_yday
    lng_hour = longitude / 15.0
    t = n + ((6 - lng_hour) / 24.0 if sunrise else (18 - lng_hour) / 24.0)
    m = (0.9856 * t) - 3.289
    l = m + 1.916 * math.sin(math.radians(m)) + 0.020 * math.sin(math.radians(2 * m)) + 282.634
    l %= 360
    ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(l)))) % 360
    l_quadrant = math.floor(l / 90) * 90
    ra_quadrant = math.floor(ra / 90) * 90
    ra = (ra + l_quadrant - ra_quadrant) / 15.0
    sin_dec = 0.39782 * math.sin(math.radians(l))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (
        math.cos(math.radians(zenith)) - sin_dec * math.sin(math.radians(latitude))
    ) / (cos_dec * math.cos(math.radians(latitude)))
    if cos_h > 1 or cos_h < -1:
        return None
    h = 360 - math.degrees(math.acos(cos_h)) if sunrise else math.degrees(math.acos(cos_h))
    h /= 15.0
    local_mean = h + ra - (0.06571 * t) - 6.622
    return (local_mean - lng_hour) % 24


def _local_event(day: date, latitude: float, longitude: float, tz, *, sunrise: bool, zenith: float):
    utc_hours = _sun_utc_hours(day, latitude, longitude, sunrise=sunrise, zenith=zenith)
    if utc_hours is None:
        return None
    midnight = datetime.combine(day, time.min, tzinfo=timezone.utc)
    local = (midnight + timedelta(hours=utc_hours)).astimezone(tz)
    # _sun_utc_hours is normalized to 0..24 and therefore loses the UTC
    # day rollover for western longitudes. The function contract is a
    # solar event for the requested *local* day, so restore that day here.
    day_delta = (day - local.date()).days
    return local + timedelta(days=day_delta)

def solar_events(day: date, latitude: float, longitude: float, tz) -> dict:
    dawn = _local_event(day, latitude, longitude, tz, sunrise=True, zenith=96.0)
    sunrise = _local_event(day, latitude, longitude, tz, sunrise=True, zenith=90.833)
    sunset = _local_event(day, latitude, longitude, tz, sunrise=False, zenith=90.833)
    dusk = _local_event(day, latitude, longitude, tz, sunrise=False, zenith=96.0)
    return {
        "dawn": dawn,
        "civil_dawn": dawn,
        "sunrise": sunrise,
        "sunset": sunset,
        "dusk": dusk,
        "civil_dusk": dusk,
    }

def moon_phase_fraction(day: date) -> float:
    """Return deterministic synodic phase fraction: 0=new, ~0.5=full."""
    reference = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    target = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)
    synodic_days = 29.53058867
    elapsed_days = (target - reference).total_seconds() / 86400
    return round((elapsed_days % synodic_days) / synodic_days, 6)
