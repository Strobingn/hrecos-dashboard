"""Build the dicts the migration accepts. Key order matches contract.NODE_COLUMNS."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sonar_node.classify.base import Classification
from sonar_node.config import AppConfig
from sonar_node.contract import REVIEW_STATUS_DEFAULT, TRACK_COLUMNS
from sonar_node.simulate import SimulatedTrack


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def node_row(config: AppConfig, heartbeat: datetime) -> dict:
    node = config.node
    return {
        "id": node.id,
        "name": node.name,
        "lat": node.lat,
        "lon": node.lon,
        "river_mile": node.river_mile,
        "hardware": node.hardware,
        "status": node.status,
        "last_heartbeat": _iso(heartbeat),
    }


def clip_path_for(track: SimulatedTrack) -> str:
    stamp = track.start.astimezone(timezone.utc)
    return (
        f"{track.node_id}/tracks/{stamp:%Y/%m/%d}/{track.id}.json"
    )


def track_row(track: SimulatedTrack, classification: Classification) -> dict:
    row = {
        "id": track.id,
        "node_id": track.node_id,
        "start_time": _iso(track.start),
        "end_time": _iso(track.end),
        "direction": track.direction,
        "length_cm": track.length_cm,
        "depth_m": track.depth_m,
        "range_m": track.range_m,
        "speed_mps": track.speed_mps,
        "species_id": classification.species_id,
        "species_confidence": classification.confidence,
        "model_name": classification.model_name,
        "model_version": classification.model_version,
        "review_status": REVIEW_STATUS_DEFAULT,
        "clip_path": clip_path_for(track),
        "features": track.features,
    }
    if tuple(row) != TRACK_COLUMNS:
        raise RuntimeError("track row drifted from TRACK_COLUMNS")
    return row


def clip_bytes(track: SimulatedTrack, classification: Classification) -> bytes:
    """JSON sidecar. Not an ARIS frame and not the hidden truth species."""
    body = {
        "synthetic": True,
        "note": "Feature sidecar for a simulated track. Not an ARIS or DIDSON frame.",
        "track_id": track.id,
        "node_id": track.node_id,
        "start_time": _iso(track.start),
        "end_time": _iso(track.end),
        "direction": track.direction,
        "length_cm": track.length_cm,
        "depth_m": track.depth_m,
        "range_m": track.range_m,
        "speed_mps": track.speed_mps,
        "features": track.features,
        "species_id": classification.species_id,
        "species_confidence": classification.confidence,
        "model_name": classification.model_name,
        "model_version": classification.model_version,
    }
    return json.dumps(body, sort_keys=True).encode("utf-8")


def truth_row(track: SimulatedTrack) -> dict:
    return {
        "id": track.id,
        "truth_species": track.truth_species,
        "truth_length_cm": track.truth_length_cm,
    }
