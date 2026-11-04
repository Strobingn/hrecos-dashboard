from datetime import datetime, timezone

from sonar_node.contract import LENGTH_CM
from sonar_node.seasons import expected_per_hour
from sonar_node.simulate import generate_tracks


def _utc(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_truth_lengths_stay_inside_the_envelopes():
    tracks = generate_tracks(
        _utc(2026, 6, 1),
        _utc(2026, 6, 3),
        node_id="westpoint-cornwall",
        seed=1,
        rate=1.0,
    )
    assert tracks
    for track in tracks:
        low, high = LENGTH_CM[track.truth_species]
        assert low <= track.truth_length_cm <= high
        assert track.length_cm > 0
        assert track.features["synthetic"] is True
        assert "truth" not in track.features


def test_january_has_no_migrants_and_june_has_surface_bass():
    winter = generate_tracks(
        _utc(2026, 1, 10),
        _utc(2026, 1, 12),
        node_id="westpoint-cornwall",
        seed=1,
    )
    species = {track.truth_species for track in winter}
    assert species <= {"striped_bass"}
    assert all(track.behavior != "surface_cluster" for track in winter)

    june = generate_tracks(
        _utc(2026, 6, 1),
        _utc(2026, 6, 3),
        node_id="westpoint-cornwall",
        seed=1,
    )
    bass = [track for track in june if track.truth_species == "striped_bass"]
    assert any(track.behavior == "surface_cluster" for track in bass)
    assert any(track.near_surface and track.depth_m < 1.5 for track in bass)
    assert any(track.direction == "milling" for track in bass)
    assert {track.truth_species for track in june} >= {
        "striped_bass",
        "river_herring",
        "american_shad",
        "atlantic_sturgeon",
    }


def test_spawn_rate_exceeds_the_winter_bass_background():
    may = expected_per_hour("striped_bass", _utc(2026, 5, 15, 12))
    january = expected_per_hour("striped_bass", _utc(2026, 1, 15, 12))
    assert may > 1.0
    assert january < 0.2
    assert expected_per_hour("river_herring", _utc(2026, 1, 15)) == 0.0
    assert expected_per_hour("american_shad", _utc(2026, 7, 1)) == 0.0
    assert expected_per_hour("atlantic_sturgeon", _utc(2026, 6, 10)) > 0.0


def test_same_seed_is_repeatable():
    kwargs = dict(
        start=_utc(2026, 5, 15),
        end=_utc(2026, 5, 15, 6),
        node_id="westpoint-cornwall",
        seed=7,
        rate=1.0,
    )
    first = generate_tracks(**kwargs)
    second = generate_tracks(**kwargs)
    assert [track.id for track in first] == [track.id for track in second]
    assert [track.truth_species for track in first] == [track.truth_species for track in second]
