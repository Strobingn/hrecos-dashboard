"""Import a Lowrance .sl2 or .sl3 into sonar_tracks.

    python -m sonar.import_lowrance file.sl2 --node westpoint-cornwall --dry-run

Species stays null. A striped-bass-sized mark is a candidate in ``features``,
not a species_id. A stationary down-looking beam counts fish that pass under
the boat. That count is an index, not a full-river passage count, and
``fish_passage_hourly`` omits these rows until a species is assigned.
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sonar.detect import DETECTOR_NAME, DETECTOR_VERSION, detect, size_class
from sonar.slx import LogInfo, read_log
from sonar.stations import choose_node, find_stations_file, load_stations
from sonar_node.contract import REVIEW_STATUS_DEFAULT, TRACK_COLUMNS

logger = logging.getLogger(__name__)

SOURCE = "lowrance_log"
COUNT_NOTE = (
    "A down-looking or side-looking beam counts targets that passed through "
    "the water under or beside the boat. It is an index at that spot, not a "
    "count of the river cross-section, and it has no along-river direction."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read a Lowrance .sl2 or .sl3 log and write sonar_tracks rows. "
            "Species is left unknown. Bass-sized marks are candidates only."
        )
    )
    parser.add_argument("path", type=Path, help="Path to a .sl2 or .sl3 file")
    parser.add_argument(
        "--node",
        default=None,
        help="sonar_nodes id. Overrides the nearest station in data/stations.json.",
    )
    parser.add_argument(
        "--stations",
        type=Path,
        default=None,
        help="Station registry. Defaults to data/stations.json from the repo root.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write JSONL and do not open a network connection.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out"),
        help="Directory for sonar_tracks.jsonl in a dry run.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not args.path.is_file():
        raise SystemExit(f"log not found: {args.path}")
    info = read_log(args.path)
    if not info.pings:
        raise SystemExit(f"{args.path} has a Lowrance header and no complete frames")
    try:
        rows = tracks_from_log(info, args.path, args.node, args.stations)
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc
    logger.info(
        "%s %s pings=%s tracks=%s",
        info.kind,
        args.path.name,
        len(info.pings),
        len(rows),
    )
    if args.dry_run:
        _write_dry_run(args.output_dir, rows)
        return 0
    _upload(rows)
    return 0


def tracks_from_log(
    info: LogInfo,
    path: Path,
    node_override: str | None,
    stations_path: Path | None,
) -> list[dict]:
    detections = detect(info.pings)
    if not detections:
        return []
    fixes = [
        (ping.latitude, ping.longitude)
        for ping in info.pings
        if ping.latitude is not None and ping.longitude is not None
    ]
    if not fixes and node_override is None:
        raise ValueError(f"{path} has no GPS fix. Pass --node.")
    if not fixes and not detections:
        return []
    latitude = statistics.fmean(lat for lat, _lon in fixes) if fixes else None
    longitude = statistics.fmean(lon for _lat, lon in fixes) if fixes else None
    choice = None
    if latitude is not None and longitude is not None:
        stations = load_stations(find_stations_file(stations_path, path.parent))
        choice = choose_node(latitude, longitude, stations, node_override)
    elif node_override is None:
        raise ValueError(f"{path} has no GPS fix. Pass --node.")
    node_id = choice.node_id if choice is not None else node_override
    rows = []
    for detection in detections:
        label, bass, notes = size_class(detection.length_cm)
        if detection.size_method == "along_track":
            size_note = (
                "Length is boat speed times the time the mark stayed in the beam. "
                "That includes the beam footprint. It is not a measured fork length."
            )
        else:
            size_note = (
                "The boat was stopped or drifting under 0.4 m/s, so along-track "
                "length is not available. length_cm is the height of the bright "
                "mark in the water column, not a fork length."
            )
        features = {
            "detector": DETECTOR_NAME,
            "detector_version": DETECTOR_VERSION,
            "detection_confidence": detection.detection_confidence,
            "channel": detection.channel_name,
            "frequency": detection.frequency,
            "size_class": label,
            "bass_candidate": bass,
            "size_method": detection.size_method,
            "size_note": size_note,
            "overlap_notes": notes,
            "peak_intensity": detection.peak_intensity,
            "target_strength_note": (
                "peak_intensity is the uncalibrated 0-255 sample at the mark. "
                "It is not target strength in dB."
            ),
            "n_pings": detection.n_pings,
            "arch": detection.arch,
            "boat_speed_mps": round(detection.boat_speed_mps, 3),
            "station_key": choice.station.key if choice else None,
            "station_name": choice.station.name if choice else None,
            "station_distance_m": round(choice.station.distance_m, 1) if choice else None,
            "species_note": (
                "Species is unknown. size_class is a length bin. "
                "bass_candidate means the estimate sits in the 30–120 cm striped "
                "bass envelope, including lengths that also fit herring, shad, or "
                "a small sturgeon. A later model can set species_id."
            ),
            "count_note": COUNT_NOTE,
            "file_name": path.name,
            "priority": ["striped_bass", "atlantic_sturgeon", "river_herring"],
        }
        row = {
            "id": str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{path.resolve()}|{detection.channel_name}|{detection.start.isoformat()}|{detection.n_pings}",
                )
            ),
            "node_id": node_id,
            "start_time": _iso(detection.start),
            "end_time": _iso(detection.end),
            "direction": "unknown",
            "length_cm": round(detection.length_cm, 1),
            "depth_m": round(detection.depth_m, 3),
            "range_m": round(detection.range_m, 3),
            "speed_mps": None,
            "species_id": None,
            "species_confidence": None,
            "model_name": None,
            "model_version": None,
            "review_status": REVIEW_STATUS_DEFAULT,
            "clip_path": None,
            "features": features,
            "source": SOURCE,
        }
        if tuple(row) != TRACK_COLUMNS:
            raise RuntimeError("lowrance track row drifted from TRACK_COLUMNS")
        rows.append(row)
    return rows


def _write_dry_run(output_dir: Path, rows: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "sonar_tracks.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=False) + "\n")
    logger.info("dry-run wrote %s tracks to %s", len(rows), path)


def _upload(rows: list[dict]) -> None:
    import os

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required. "
            "Use --dry-run to write JSONL without a network."
        )
    from sonar_node.publish.supabase import SupabasePublisher

    publisher = SupabasePublisher(url, key)
    for row in rows:
        publisher.insert_track(row)
    publisher.close()


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    sys.exit(main())
