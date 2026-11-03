import json
from pathlib import Path

import numpy as np
import pytest

from hydrophone_node.audio.wavio import write_wav_bytes
from hydrophone_node.cli import main
from hydrophone_node.config import load_config
from hydrophone_node.contract import DETECTION_COLUMNS, NODE_COLUMNS, SEGMENT_COLUMNS
from hydrophone_node.detect.registry import build_detector
from hydrophone_node.pipeline import run
from hydrophone_node.publish.dry_run import DryRunPublisher


def _write_synth_config(path: Path, sample_rate: int = 8000) -> None:
    path.write_text(
        f"""
node:
  id: poughkeepsie
  sample_rate_hz: {sample_rate}
  status: simulated
source:
  kind: synth
  seed: 1
  duration_s: 60
  calls: true
segment_seconds: 60
replay_speed: 0
heartbeat_interval_s: 3600
stream_start: "2026-06-01T12:00:00Z"
detector:
  name: band_energy
supabase:
  url: https://should-not-be-called.example
  service_role_key: should-not-be-sent
""",
        encoding="utf-8",
    )


def test_dry_run_writes_contract_rows_and_does_not_use_the_network(
    tmp_path, monkeypatch
):
    def explode(*_args, **_kwargs):
        raise AssertionError("dry-run tried to use the network")

    monkeypatch.setattr("requests.sessions.Session.request", explode)
    config_path = tmp_path / "node.yaml"
    _write_synth_config(config_path)
    output = tmp_path / "out"
    code = main(
        [
            "--config",
            str(config_path),
            "--dry-run",
            "--replay-speed",
            "0",
            "--max-segments",
            "1",
            "--output-dir",
            str(output),
        ]
    )
    assert code == 0
    heartbeats = [
        json.loads(line)
        for line in (output / "heartbeats.jsonl").read_text().splitlines()
    ]
    segments = [
        json.loads(line)
        for line in (output / "audio_segments.jsonl").read_text().splitlines()
    ]
    detections = [
        json.loads(line)
        for line in (output / "detections.jsonl").read_text().splitlines()
    ]
    assert len(heartbeats) == 1
    assert len(segments) == 1
    assert tuple(heartbeats[0]) == NODE_COLUMNS
    assert heartbeats[0]["id"] == "poughkeepsie"
    assert heartbeats[0]["status"] == "simulated"
    assert tuple(segments[0]) == SEGMENT_COLUMNS
    assert set(segments[0]["band_levels"]) == {"10-100", "100-500", "500-2000"}
    assert segments[0]["node_id"] == "poughkeepsie"
    assert segments[0]["start_time"] == "2026-06-01T12:00:00Z"
    assert segments[0]["end_time"] == "2026-06-01T12:01:00Z"
    wav_path = output / "audio" / segments[0]["storage_path"]
    assert wav_path.is_file()
    labels = set()
    for row in detections:
        assert tuple(row) == DETECTION_COLUMNS
        assert row["segment_id"] == segments[0]["id"]
        assert row["review_status"] == "unreviewed"
        assert row["model_name"] == "band_energy"
        assert 0.0 <= row["confidence"] <= 1.0
        assert (output / "audio" / row["clip_path"]).is_file()
        labels.add(row["label"])
        if row["label"] == "boat":
            assert row["species_id"] is None
    assert {"sturgeon_thunder", "drum_knock", "toadfish_boatwhistle", "boat"} <= labels


def test_folder_replay_publishes_one_segment(tmp_path):
    sample_rate = 8000
    tone = (
        0.2 * np.sin(2 * np.pi * 100 * np.arange(sample_rate * 2) / sample_rate)
    ).astype(np.float32)
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "clip.wav").write_bytes(write_wav_bytes(tone, sample_rate))
    config_path = tmp_path / "node.yaml"
    config_path.write_text(
        f"""
node:
  id: westpoint-cornwall
  sample_rate_hz: {sample_rate}
source:
  kind: folder
  path: {audio_dir}
  max_files: 5
segment_seconds: 1
replay_speed: 0
stream_start: "2026-01-01T00:00:00Z"
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    publisher = DryRunPublisher(tmp_path / "out", echo=False)
    produced = run(
        config,
        publisher,
        build_detector("band_energy"),
        max_segments=5,
        sleep=lambda _seconds: None,
    )
    assert produced == 2
    rows = [
        json.loads(line)
        for line in (tmp_path / "out" / "audio_segments.jsonl").read_text().splitlines()
    ]
    assert rows[0]["node_id"] == "westpoint-cornwall"
    assert rows[0]["rms_db"] < 0


def test_live_publish_without_keys_fails_before_any_audio(tmp_path):
    config_path = tmp_path / "node.yaml"
    config_path.write_text(
        "node:\n  id: poughkeepsie\nsource:\n  kind: synth\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        main(["--config", str(config_path), "--max-segments", "1"])
