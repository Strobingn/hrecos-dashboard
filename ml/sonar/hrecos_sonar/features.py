"""Features a track classifier may see. Truth species is not one of them."""

from __future__ import annotations

import math

import numpy as np

from sonar_node.simulate import SimulatedTrack

FEATURE_NAMES = (
    "length_m",
    "depth_m_scaled",
    "speed_mps",
    "near_surface",
    "surface_cluster",
    "school",
    "log_cluster_size",
    "doy_sin",
    "doy_cos",
)


def featurize(track: SimulatedTrack) -> np.ndarray:
    doy = track.start.timetuple().tm_yday
    angle = 2.0 * math.pi * doy / 365.0
    return np.array(
        [
            track.length_cm / 100.0,
            track.depth_m / 10.0,
            track.speed_mps,
            1.0 if track.near_surface else 0.0,
            1.0 if track.behavior == "surface_cluster" else 0.0,
            1.0 if track.behavior == "school" else 0.0,
            math.log1p(track.cluster_size),
            math.sin(angle),
            math.cos(angle),
        ],
        dtype=np.float64,
    )


def design_matrix(tracks: list[SimulatedTrack]) -> np.ndarray:
    return np.stack([featurize(track) for track in tracks])
