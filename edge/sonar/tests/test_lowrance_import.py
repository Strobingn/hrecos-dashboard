"""Lowrance .sl2/.sl3 import.

The public fixtures are the first frames of sonarlight's example logs (MIT).
The synthetic logs are built in the test so a water-column arch, a DownScan
mark, a SideScan mark, and surface/bottom clutter are known exactly.
"""

import json
from pathlib import Path

import pytest

from sonar.detect import size_class
from sonar.import_lowrance import main, tracks_from_log
from sonar.slx import FEET_TO_M, KNOTS_TO_MPS, Frame, read_log, write_log
from sonar_node.contract import TRACK_COLUMNS

FIXTURES = Path(__file__).parent / "fixtures"
WEST_POINT = (41.38607, -73.95496)


def test_public_sl2_and_sl3_headers_match_the_example_files():
    sl2 = read_log(FIXTURES / "example_sl2_head.sl2")
    assert sl2.kind == "sl2"
    assert sl2.format == 2
    primary = sl2.pings[0]
    assert primary.channel_name == "primary"
    assert primary.depth_m == pytest.approx(10.5066 * FEET_TO_M, abs=0.02)
    assert primary.latitude == pytest.approx(55.773, abs=0.01)
    assert primary.longitude == pytest.approx(12.345, abs=0.01)
    assert primary.time is not None and primary.time.year == 2023
    assert len(primary.samples) == 3072

    sl3 = read_log(FIXTURES / "example_sl3_head.sl3")
    assert sl3.kind == "sl3"
    down = sl3.pings[0]
    assert down.channel_name == "downscan"
    assert down.depth_m == pytest.approx(13.481 * FEET_TO_M, abs=0.02)
    assert down.latitude == pytest.approx(55.773, abs=0.01)
    assert down.time is not None and down.time.year == 2023
    assert len(down.samples) == 1400


def test_size_class_follows_bass_then_sturgeon_then_herring():
    label, bass, notes = size_class(50)
    assert label == "striped_bass_candidate"
    assert bass is True
    assert any("shad" in note for note in notes)

    label, bass, notes = size_class(25)
    assert label == "herring_sized"
    assert bass is False
    assert notes == []

    label, bass, _notes = size_class(180)
    assert label == "sturgeon_sized"
    assert bass is False

    label, bass, notes = size_class(110)
    assert label == "striped_bass_candidate"
    assert bass is True
    assert any("sturgeon" in note for note in notes)

    label, bass, notes = size_class(32)
    assert bass is True
    assert any("herring" in note for note in notes)


def test_synthetic_log_rejects_surface_and_bottom_and_flags_bass(tmp_path):
    path = tmp_path / "spot.sl2"
    write_log(path, _anchor_frames(), kind="sl2")
    info = read_log(path)
    assert info.pings[0].channel_name == "primary"
    assert info.pings[0].latitude == pytest.approx(WEST_POINT[0], abs=1e-4)
    rows = tracks_from_log(info, path, node_override=None, stations_path=None)
    by_channel = {}
    for row in rows:
        by_channel.setdefault(row["features"]["channel"], []).append(row)

    assert set(by_channel) == {"primary", "downscan"}
    bass = by_channel["primary"][0]
    assert tuple(bass) == TRACK_COLUMNS
    assert bass["source"] == "lowrance_log"
    assert bass["node_id"] == "westpoint-cornwall"
    assert bass["direction"] == "unknown"
    assert bass["species_id"] is None
    assert bass["species_confidence"] is None
    assert bass["model_name"] is None
    assert bass["speed_mps"] is None
    assert bass["features"]["size_method"] == "vertical_extent"
    assert bass["features"]["arch"] is True
    assert bass["features"]["bass_candidate"] is True
    assert bass["features"]["size_class"] == "striped_bass_candidate"
    assert bass["features"]["station_key"] == "west_point"
    assert any("shad" in note for note in bass["features"]["overlap_notes"])
    assert "not a count of the river" in bass["features"]["count_note"]
    assert 40 < bass["length_cm"] < 60

    herring = by_channel["downscan"][0]
    assert herring["features"]["bass_candidate"] is False
    assert herring["features"]["size_class"] == "herring_sized"
    assert herring["features"]["arch"] is False
    assert 20 <= herring["length_cm"] < 30


def test_sidescan_mark_can_be_sturgeon_sized_without_a_species(tmp_path):
    path = tmp_path / "side.sl3"
    frames = []
    for index, ms in enumerate((0, 200, 400)):
        frames.append(
            Frame(
                channel=3,
                samples=_sidescan(fish=True),
                upper_ft=0,
                lower_ft=80,
                depth_ft=20,
                time_ms=ms,
                frame_index=index,
                latitude=WEST_POINT[0],
                longitude=WEST_POINT[1],
            )
        )
    write_log(path, frames, kind="sl3")
    rows = tracks_from_log(read_log(path), path, None, None)
    assert len(rows) == 1
    row = rows[0]
    assert row["features"]["channel"] == "left_sidescan"
    assert row["features"]["size_class"] == "sturgeon_sized"
    assert row["features"]["bass_candidate"] is False
    assert row["species_id"] is None
    assert row["length_cm"] == pytest.approx(182.9, abs=1)


def test_moving_boat_uses_along_track_length(tmp_path):
    path = tmp_path / "drift.sl2"
    centers = (22, 18, 14, 18, 22)
    frames = []
    for index, (center, ms) in enumerate(zip(centers, (0, 250, 500, 750, 1000))):
        frames.append(
            Frame(
                channel=0,
                samples=_down_looking(64, fish_center=center, fish_width=3, bottom_at=48),
                upper_ft=0,
                lower_ft=32,
                depth_ft=20,
                speed_knots=0.5 / KNOTS_TO_MPS,
                time_ms=ms,
                frame_index=index,
            )
        )
    write_log(path, frames, kind="sl2")
    rows = tracks_from_log(read_log(path), path, "westpoint-cornwall", None)
    assert len(rows) == 1
    assert rows[0]["features"]["size_method"] == "along_track"
    assert rows[0]["length_cm"] == pytest.approx(50.0, abs=0.5)
    assert rows[0]["node_id"] == "westpoint-cornwall"


def test_cli_dry_run_does_not_use_the_network(tmp_path, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("dry-run tried to use the network")

    monkeypatch.setattr("requests.sessions.Session.request", explode)
    path = tmp_path / "spot.sl2"
    write_log(path, _anchor_frames(), kind="sl2")
    output = tmp_path / "out"
    code = main(
        [
            str(path),
            "--node",
            "westpoint-cornwall",
            "--dry-run",
            "--output-dir",
            str(output),
        ]
    )
    assert code == 0
    lines = (output / "sonar_tracks.jsonl").read_text().splitlines()
    rows = [json.loads(line) for line in lines]
    assert len(rows) == 2
    assert {row["source"] for row in rows} == {"lowrance_log"}
    assert {row["node_id"] for row in rows} == {"westpoint-cornwall"}


def test_log_far_from_the_hudson_requires_a_node(tmp_path):
    path = tmp_path / "denmark.sl2"
    frames = []
    centers = (22, 18, 14, 18, 22)
    for index, center in enumerate(centers):
        frames.append(
            Frame(
                channel=0,
                samples=_down_looking(64, fish_center=center, fish_width=3, bottom_at=48),
                latitude=55.773,
                longitude=12.345,
                time_ms=index * 200,
                frame_index=index,
            )
        )
    write_log(path, frames, kind="sl2")
    with pytest.raises(SystemExit, match="Pass --node"):
        main([str(path), "--dry-run", "--output-dir", str(tmp_path / "out")])


def _anchor_frames() -> list[Frame]:
    frames: list[Frame] = []
    primary_centers = {1: 22, 2: 18, 3: 14, 4: 18, 5: 22}
    for index in range(8):
        frames.append(
            Frame(
                channel=0,
                samples=_down_looking(
                    64,
                    fish_center=primary_centers.get(index),
                    fish_width=3,
                    bottom_at=48,
                ),
                upper_ft=0,
                lower_ft=32,
                depth_ft=20,
                time_ms=index * 200,
                frame_index=index,
            )
        )
        if index < 3:
            frames.append(
                Frame(
                    channel=2,
                    samples=_down_looking(64, fish_center=10, fish_width=2, bottom_at=52),
                    upper_ft=0,
                    lower_ft=26.246,
                    depth_ft=20,
                    time_ms=index * 200,
                    frame_index=index,
                )
            )
        frames.append(
            Frame(
                channel=1,
                samples=_down_looking(64, fish_center=None, fish_width=0, bottom_at=48),
                upper_ft=0,
                lower_ft=32,
                depth_ft=20,
                time_ms=index * 200,
                frame_index=index,
            )
        )
    # One bright primary ping that never repeats, so it is not an arch.
    frames.append(
        Frame(
            channel=0,
            samples=_down_looking(64, fish_center=30, fish_width=3, bottom_at=48),
            upper_ft=0,
            lower_ft=32,
            depth_ft=20,
            time_ms=5000,
            frame_index=8,
        )
    )
    return frames


def _down_looking(count: int, fish_center: int | None, fish_width: int, bottom_at: int) -> bytes:
    samples = bytearray([12]) * count
    for index in range(min(3, count)):
        samples[index] = 250
    for index in range(bottom_at, min(count, bottom_at + 8)):
        samples[index] = 230
    if fish_center is not None and fish_width > 0:
        start = fish_center - fish_width // 2
        for index in range(start, start + fish_width):
            if 0 <= index < bottom_at:
                samples[index] = 240
    return bytes(samples)


def _sidescan(fish: bool) -> bytes:
    samples = bytearray([12]) * 80
    samples[0] = 255
    samples[1] = 255
    for index in range(50, 70):
        samples[index] = 250
    if fish:
        for index in range(10, 16):
            samples[index] = 240
    return bytes(samples)
