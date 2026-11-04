"""Seasonal rate knobs for the synthetic sonar.

The windows follow the Hudson timing in docs/sonar-track.md. `expected_per_hour`
is the mean number of groups in that clock hour, not a census and not a catch
rate. A group is one herring or shad school, one striped bass surface cluster
during the spawn, or one solitary fish (sturgeon, resident bass, or a fish
whose schoolmates missed the beam).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

# (month, day) inclusive window, peak month/day, width in days, peak fish/hour.
_WINDOWS = {
    # Alewife from mid-March, blueback into early June. One combined peak.
    "river_herring": ((3, 15), (6, 15), (4, 25), 18.0, 10.0),
    # Late March through the first week of June, peak mid-May.
    "american_shad": ((3, 25), (6, 7), (5, 15), 14.0, 7.0),
    # Early May through June, peak mid-May, inside the historical egg reach.
    "striped_bass": ((5, 1), (6, 30), (5, 15), 12.0, 6.0),
    # Gill nets mid-May through June near Hyde Park; thunder recorded into July.
    # West Point is downstream of that reach, so this is passage, not spawning.
    "atlantic_sturgeon": ((5, 1), (7, 15), (6, 10), 18.0, 0.35),
}

# Year-round striped bass outside the spawn window. The Hudson has resident
# fish; this rate is only a way to keep the winter beam from being empty.
RESIDENT_BASS_PER_HOUR = 0.12


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _on_or_after(moment: datetime, month: int, day: int) -> bool:
    return (moment.month, moment.day) >= (month, day)


def _on_or_before(moment: datetime, month: int, day: int) -> bool:
    return (moment.month, moment.day) <= (month, day)


def in_window(species: str, moment: datetime) -> bool:
    start, end, _peak, _width, _rate = _WINDOWS[species]
    moment = _as_utc(moment)
    return _on_or_after(moment, *start) and _on_or_before(moment, *end)


def expected_per_hour(species: str, moment: datetime) -> float:
    """Mean of the Poisson draw for one species in this clock hour."""
    moment = _as_utc(moment)
    start, end, peak, width, rate = _WINDOWS[species]
    if not in_window(species, moment):
        if species == "striped_bass":
            return RESIDENT_BASS_PER_HOUR
        return 0.0
    peak_dt = moment.replace(
        month=peak[0], day=peak[1], hour=0, minute=0, second=0, microsecond=0
    )
    days = abs((moment - peak_dt).total_seconds()) / 86400.0
    return rate * math.exp(-0.5 * (days / width) ** 2)


def bass_spawning(moment: datetime) -> bool:
    return in_window("striped_bass", moment)
