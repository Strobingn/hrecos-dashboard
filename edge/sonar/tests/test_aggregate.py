from datetime import datetime, timezone
from pathlib import Path

from sonar_node.aggregate import fish_passage_hourly, striped_bass_fusion


def test_passage_counts_tracks_and_drops_rejects_and_unknowns():
    hour = datetime(2026, 5, 15, 12, 30, tzinfo=timezone.utc)
    tracks = [
        _row("striped_bass", "milling", 80, "unreviewed"),
        _row("striped_bass", "milling", 60, "unreviewed"),
        _row("striped_bass", "upstream", 90, "unreviewed"),
        _row("striped_bass", "milling", 70, "rejected"),
        _row(None, "upstream", 40, "unreviewed"),
    ]
    for row in tracks:
        row["start_time"] = hour
    grouped = fish_passage_hourly(tracks)
    by_direction = {row["direction"]: row for row in grouped}
    assert by_direction["milling"]["fish_count"] == 2
    assert by_direction["milling"]["mean_length_cm"] == 70
    assert by_direction["upstream"]["fish_count"] == 1
    assert set(by_direction) == {"milling", "upstream"}


def test_fusion_repeats_splash_counts_and_keeps_hydrophone_only_hours():
    hour = datetime(2026, 5, 15, 12, tzinfo=timezone.utc)
    later = datetime(2026, 5, 15, 13, tzinfo=timezone.utc)
    passage = [
        {
            "node_id": "westpoint-cornwall",
            "species_id": "striped_bass",
            "direction": "milling",
            "hour": hour,
            "fish_count": 6,
            "mean_length_cm": 70.0,
        },
        {
            "node_id": "westpoint-cornwall",
            "species_id": "striped_bass",
            "direction": "upstream",
            "hour": hour,
            "fish_count": 1,
            "mean_length_cm": 95.0,
        },
        {
            "node_id": "westpoint-cornwall",
            "species_id": "american_shad",
            "direction": "upstream",
            "hour": hour,
            "fish_count": 4,
            "mean_length_cm": 52.0,
        },
    ]
    detections = [
        {
            "node_id": "westpoint-cornwall",
            "species_id": "striped_bass",
            "label": "bass_spawning_splash",
            "hour": hour,
            "detections": 3,
        },
        {
            "node_id": "westpoint-cornwall",
            "species_id": "striped_bass",
            "label": "bass_spawning_splash",
            "hour": later,
            "detections": 1,
        },
    ]
    fused = striped_bass_fusion(passage, detections)
    same_hour = [row for row in fused if row["hour"] == hour]
    assert len(same_hour) == 2
    assert {row["splash_detections"] for row in same_hour} == {3}
    assert {row["striped_bass_detections"] for row in same_hour} == {3}
    # Summing the repeated hour total would count the three splashes twice.
    assert sum(row["splash_detections"] for row in same_hour) == 6
    assert sum(row["fish_count"] for row in same_hour) == 7
    hydro_only = [row for row in fused if row["hour"] == later]
    assert len(hydro_only) == 1
    assert hydro_only[0]["direction"] is None
    assert hydro_only[0]["fish_count"] is None
    assert hydro_only[0]["splash_detections"] == 1
    assert all(row["species_id"] != "american_shad" for row in fused if "species_id" in row)


def test_migration_defines_the_passage_contract():
    root = Path(__file__).resolve().parents[3]
    sql = (root / "supabase/migrations/20261103160000_sonar_fish_passage.sql").read_text()
    assert "create table public.sonar_nodes" in sql
    assert "create table public.sonar_tracks" in sql
    assert "create view public.fish_passage_hourly" in sql
    assert "create view public.striped_bass_passage_and_calls_hourly" in sql
    assert "bass_spawning_splash" in sql
    assert "review_status <> 'rejected'" in sql
    assert "westpoint-cornwall" in sql
    assert "poughkeepsie" not in sql
    seed = (root / "supabase/seed.sql").read_text()
    assert seed.count("westpoint-cornwall") >= 2


def _row(species, direction, length, review):
    return {
        "node_id": "westpoint-cornwall",
        "species_id": species,
        "direction": direction,
        "length_cm": length,
        "review_status": review,
    }
