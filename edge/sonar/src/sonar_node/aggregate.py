"""Python mirror of the passage views.

The SQL in supabase/migrations/20261103160000_sonar_fish_passage.sql is the
contract. These functions exist so a dry run can print the same grouping
without a database, and so tests can check the grouping rules.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sonar_node.contract import SPLASH_LABEL, STRIPED_BASS_ID


def hour_start(moment: datetime) -> datetime:
    moment = moment.astimezone(timezone.utc)
    return moment.replace(minute=0, second=0, microsecond=0)


def fish_passage_hourly(tracks: list[dict]) -> list[dict]:
    """Group classified track rows the way fish_passage_hourly does.

    Each dict needs node_id, species_id, direction, start_time (datetime),
    length_cm, review_status.
    """
    buckets: dict[tuple, list] = defaultdict(list)
    for row in tracks:
        if row.get("review_status") == "rejected":
            continue
        if not row.get("species_id"):
            continue
        key = (
            row["node_id"],
            row["species_id"],
            row["direction"],
            hour_start(row["start_time"]),
        )
        buckets[key].append(row["length_cm"])
    out = []
    for (node_id, species_id, direction, hour), lengths in sorted(
        buckets.items(), key=lambda item: (item[0][3], item[0][0], item[0][1], item[0][2])
    ):
        present = [value for value in lengths if value is not None]
        mean = sum(present) / len(present) if present else None
        out.append(
            {
                "node_id": node_id,
                "species_id": species_id,
                "direction": direction,
                "hour": hour,
                "fish_count": len(lengths),
                "mean_length_cm": mean,
            }
        )
    return out


def striped_bass_fusion(passage: list[dict], detections: list[dict]) -> list[dict]:
    """Mirror striped_bass_passage_and_calls_hourly.

    `detections` are hourly calling rows: node_id, species_id, label, hour, detections.
    Splash and striped-bass detection totals are hour-level. They are copied
    onto every direction row and must not be summed across directions.
    """
    calls: dict[tuple, dict] = defaultdict(
        lambda: {"splash_detections": 0, "striped_bass_detections": 0}
    )
    for row in detections:
        splash = row.get("label") == SPLASH_LABEL
        bass = row.get("species_id") == STRIPED_BASS_ID
        if not splash and not bass:
            continue
        slot = calls[(row["node_id"], row["hour"])]
        count = int(row["detections"])
        if splash:
            slot["splash_detections"] += count
        if bass:
            slot["striped_bass_detections"] += count

    bass_passage = [row for row in passage if row["species_id"] == STRIPED_BASS_ID]
    seen = set()
    out = []
    for row in bass_passage:
        key = (row["node_id"], row["hour"])
        seen.add(key)
        slot = calls.get(key, {"splash_detections": 0, "striped_bass_detections": 0})
        out.append(
            {
                "node_id": row["node_id"],
                "hour": row["hour"],
                "direction": row["direction"],
                "fish_count": row["fish_count"],
                "mean_length_cm": row["mean_length_cm"],
                "splash_detections": slot["splash_detections"],
                "striped_bass_detections": slot["striped_bass_detections"],
            }
        )
    for key, slot in sorted(calls.items(), key=lambda item: (item[0][1], item[0][0])):
        if key in seen:
            continue
        if slot["splash_detections"] == 0 and slot["striped_bass_detections"] == 0:
            continue
        out.append(
            {
                "node_id": key[0],
                "hour": key[1],
                "direction": None,
                "fish_count": None,
                "mean_length_cm": None,
                "splash_detections": slot["splash_detections"],
                "striped_bass_detections": slot["striped_bass_detections"],
            }
        )
    return out
