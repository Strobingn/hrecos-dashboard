"""Synthetic sonar tracks.

Truth lengths stay inside the envelopes in contract.LENGTH_CM. The length on
the track is that truth plus noise, which is what a classifier is allowed to
see. Behavior is the stand-in for a track summary (a surface cluster, a
school, a single fish). This module does not invent tailbeat frequencies or
ARIS pixels.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from sonar_node.contract import LENGTH_CM, SPECIES_IDS
from sonar_node.seasons import bass_spawning, expected_per_hour

LENGTH_NOISE_SD_CM = 5.0
SURFACE_DEPTH_M = 1.5

_LENGTH_MEAN_SD = {
    "striped_bass": (70.0, 18.0),
    "river_herring": (27.0, 3.0),
    "american_shad": (54.0, 4.0),
    "atlantic_sturgeon": (170.0, 35.0),
}


@dataclass(frozen=True)
class SimulatedTrack:
    """One fish. `length_cm` is the noisy observation. `truth_length_cm` is not a sonar product."""

    id: str
    node_id: str
    start: datetime
    end: datetime
    direction: str
    length_cm: float
    depth_m: float
    range_m: float
    speed_mps: float
    behavior: str
    cluster_size: int
    near_surface: bool
    cluster_id: str | None
    truth_species: str
    truth_length_cm: float

    @property
    def features(self) -> dict:
        return {
            "synthetic": True,
            "behavior": self.behavior,
            "cluster_size": self.cluster_size,
            "near_surface": self.near_surface,
            "cluster_id": self.cluster_id,
        }


def generate_tracks(
    start: datetime,
    end: datetime,
    node_id: str,
    seed: int = 1,
    rate: float = 1.0,
) -> list[SimulatedTrack]:
    """Tracks with start times in [start, end). Hours are stepped in UTC."""
    if rate < 0:
        raise ValueError("rate must be >= 0")
    start = _utc(start)
    end = _utc(end)
    if end < start:
        raise ValueError("end before start")
    rng = np.random.default_rng(seed)
    tracks: list[SimulatedTrack] = []
    cursor = start
    while cursor < end:
        hour_end = min(end, cursor + timedelta(hours=1))
        for species in SPECIES_IDS:
            lam = expected_per_hour(species, cursor) * rate
            n_groups = int(rng.poisson(lam)) if lam > 0 else 0
            tracks.extend(
                _groups(species, n_groups, cursor, hour_end, node_id, rng)
            )
        cursor = hour_end
    tracks.sort(key=lambda item: (item.start, item.id))
    return tracks


def _groups(species, n_groups, hour_start, hour_end, node_id, rng):
    """Each draw is one group. About 12% of spawners and schooling fish are
    alone in the beam so length overlap stays visible to the classifier.
    """
    tracks = []
    spawning = species == "striped_bass" and bass_spawning(hour_start)
    schooling = species in ("river_herring", "american_shad")
    for _group_index in range(n_groups):
        alone = (spawning or schooling) and rng.random() < 0.12
        if spawning and not alone:
            size = int(rng.integers(4, 13))
            behavior = "surface_cluster"
        elif schooling and not alone:
            size = int(rng.integers(6, 16))
            behavior = "school"
        else:
            size = 1
            behavior = "solitary"
        cluster_id = str(uuid.UUID(bytes=rng.bytes(16)))
        direction = _direction(species, hour_start, behavior, rng)
        anchor = _time_in(hour_start, hour_end, rng)
        depth0 = _depth(species, behavior, rng)
        range0 = float(rng.uniform(3.0, 18.0))
        speed0 = _speed(behavior, rng)
        for _ in range(size):
            truth_length = _length(species, rng)
            observed = float(np.clip(truth_length + rng.normal(0.0, LENGTH_NOISE_SD_CM), 1.0, 400.0))
            depth = float(np.clip(depth0 + rng.normal(0.0, 0.15), 0.05, 20.0))
            if behavior == "surface_cluster":
                depth = float(np.clip(depth, 0.1, 1.4))
            start = anchor + timedelta(seconds=float(rng.uniform(0.0, 20.0)))
            if start >= hour_end:
                start = hour_end - timedelta(seconds=1)
            duration = timedelta(seconds=float(rng.uniform(3.0, 18.0)))
            shown_behavior = behavior
            shown_size = size
            shown_cluster = cluster_id
            # A fraction of tracks lose the grouping cue, the way a tracker
            # drops an association. Depth is still observed.
            if rng.random() < 0.08:
                shown_behavior = "unknown"
                shown_size = 1
                shown_cluster = None
            tracks.append(
                SimulatedTrack(
                    id=str(uuid.UUID(bytes=rng.bytes(16))),
                    node_id=node_id,
                    start=start,
                    end=start + duration,
                    direction=direction,
                    length_cm=round(observed, 1),
                    depth_m=round(depth, 2),
                    range_m=round(float(np.clip(range0 + rng.normal(0.0, 0.4), 0.5, 35.0)), 2),
                    speed_mps=round(float(np.clip(speed0 + rng.normal(0.0, 0.05), 0.0, 3.0)), 3),
                    behavior=shown_behavior,
                    cluster_size=shown_size,
                    near_surface=depth < SURFACE_DEPTH_M,
                    cluster_id=shown_cluster,
                    truth_species=species,
                    truth_length_cm=round(truth_length, 1),
                )
            )
    return tracks


def _direction(species: str, moment: datetime, behavior: str, rng) -> str:
    if behavior == "surface_cluster":
        return str(rng.choice(["milling", "milling", "milling", "upstream", "downstream"]))
    month_day = (moment.month, moment.day)
    if species == "river_herring":
        upstream_bias = month_day <= (5, 1)
    elif species == "american_shad":
        upstream_bias = month_day <= (5, 10)
    elif species == "atlantic_sturgeon":
        upstream_bias = month_day <= (6, 10)
    else:
        upstream_bias = month_day <= (5, 20)
    if upstream_bias:
        return str(rng.choice(["upstream", "upstream", "upstream", "upstream", "downstream"]))
    return str(rng.choice(["downstream", "downstream", "downstream", "downstream", "upstream"]))


def _depth(species: str, behavior: str, rng) -> float:
    if behavior == "surface_cluster":
        return float(rng.uniform(0.2, 1.2))
    if species == "atlantic_sturgeon":
        return float(rng.uniform(4.0, 12.0))
    if behavior == "school":
        return float(rng.uniform(1.8, 5.5))
    return float(rng.uniform(2.0, 8.0))


def _speed(behavior: str, rng) -> float:
    if behavior == "surface_cluster":
        return float(rng.uniform(0.05, 0.35))
    return float(rng.uniform(0.35, 1.1))


def _length(species: str, rng) -> float:
    low, high = LENGTH_CM[species]
    mean, sd = _LENGTH_MEAN_SD[species]
    for _ in range(1000):
        draw = float(rng.normal(mean, sd))
        if low <= draw <= high:
            return draw
    return float(np.clip(mean, low, high))


def _time_in(start: datetime, end: datetime, rng) -> datetime:
    span = (end - start).total_seconds()
    if span <= 1:
        return start
    return start + timedelta(seconds=float(rng.uniform(0.0, span - 1.0)))


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)
