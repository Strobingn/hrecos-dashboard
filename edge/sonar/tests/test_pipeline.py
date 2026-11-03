import json
from pathlib import Path

from sonar_node.cli import main
from sonar_node.contract import NODE_COLUMNS, TRACK_COLUMNS


def test_dry_run_writes_contract_rows_and_does_not_use_the_network(tmp_path, monkeypatch):
    def explode(*_args, **_kwargs):
        raise AssertionError("dry-run tried to use the network")

    monkeypatch.setattr("requests.sessions.Session.request", explode)
    config = tmp_path / "node.yaml"
    config.write_text(
        """
node:
  id: westpoint-cornwall
  status: simulated
source:
  kind: synth
  seed: 3
  start: "2026-05-15T12:00:00Z"
  hours: 2
  rate: 1
classifier:
  name: rules
supabase:
  url: https://should-not-be-called.example
  service_role_key: should-not-be-sent
""",
        encoding="utf-8",
    )
    output = tmp_path / "out"
    code = main(
        [
            "--config",
            str(config),
            "--dry-run",
            "--max-tracks",
            "12",
            "--output-dir",
            str(output),
        ]
    )
    assert code == 0
    nodes = [json.loads(line) for line in (output / "sonar_nodes.jsonl").read_text().splitlines()]
    tracks = [json.loads(line) for line in (output / "sonar_tracks.jsonl").read_text().splitlines()]
    truth = [json.loads(line) for line in (output / "truth.jsonl").read_text().splitlines()]
    assert len(nodes) == 1
    assert tuple(nodes[0]) == NODE_COLUMNS
    assert nodes[0]["id"] == "westpoint-cornwall"
    assert nodes[0]["status"] == "simulated"
    assert len(tracks) == 12
    assert len(truth) == 12
    assert tuple(tracks[0]) == TRACK_COLUMNS
    assert tracks[0]["source"] == "synthetic"
    assert tracks[0]["features"]["synthetic"] is True
    clip_name = tracks[0]["clip_path"].replace("/", "__")
    clip = json.loads((output / "clips" / clip_name).read_text())
    assert clip["synthetic"] is True
    assert "truth_species" not in clip
    assert "Not an ARIS" in clip["note"]
    uploaded_ids = {row["id"] for row in tracks}
    assert {row["id"] for row in truth} == uploaded_ids


def test_upload_without_keys_fails_before_any_work(tmp_path):
    config = tmp_path / "node.yaml"
    config.write_text(
        """
node:
  id: westpoint-cornwall
source:
  kind: synth
  hours: 1
classifier:
  name: rules
""",
        encoding="utf-8",
    )
    try:
        main(["--config", str(config), "--max-tracks", "1"])
    except RuntimeError as exc:
        assert "SUPABASE_URL" in str(exc)
    else:
        raise AssertionError("expected a missing-key error")
