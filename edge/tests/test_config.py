from hydrophone_node.config import load_config
from hydrophone_node.contract import NODE_PRESETS


def test_preset_fills_coordinates_for_a_known_node(tmp_path, monkeypatch):
    monkeypatch.delenv("NODE_ID", raising=False)
    monkeypatch.delenv("SAMPLE_RATE_HZ", raising=False)
    monkeypatch.delenv("REPLAY_SPEED", raising=False)
    path = tmp_path / "node.yaml"
    path.write_text("node:\n  id: tappan-zee\n", encoding="utf-8")
    config = load_config(path)
    preset = NODE_PRESETS["tappan-zee"]
    assert config.node.name == preset["name"]
    assert config.node.lat == preset["lat"]
    assert config.node.river_mile == preset["river_mile"]
    assert config.node.status == "simulated"
    assert config.segment_seconds == 60
    assert config.sample_rate_hz == 48000


def test_env_overrides_yaml(tmp_path, monkeypatch):
    path = tmp_path / "node.yaml"
    path.write_text(
        "node:\n  id: poughkeepsie\n  sample_rate_hz: 48000\n"
        "source:\n  kind: synth\n"
        "replay_speed: 1\n"
        "supabase:\n  url: ${SUPABASE_URL}\n  service_role_key: ${SUPABASE_SERVICE_ROLE_KEY}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NODE_ID", "westpoint-cornwall")
    monkeypatch.setenv("SAMPLE_RATE_HZ", "16000")
    monkeypatch.setenv("HYDROPHONE_SOURCE", "folder")
    monkeypatch.setenv("HYDROPHONE_SOURCE_PATH", "/data/wavs")
    monkeypatch.setenv("REPLAY_SPEED", "0")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test")
    config = load_config(path)
    assert config.node.id == "westpoint-cornwall"
    assert config.node.lat == NODE_PRESETS["westpoint-cornwall"]["lat"]
    assert config.sample_rate_hz == 16000
    assert config.source.kind == "folder"
    assert config.source.path == "/data/wavs"
    assert config.replay_speed == 0
    assert config.supabase.url == "https://example.supabase.co"
    assert config.supabase.service_role_key == "service-role-test"


def test_bad_status_is_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("NODE_ID", raising=False)
    path = tmp_path / "node.yaml"
    path.write_text("node:\n  id: poughkeepsie\n  status: napping\n", encoding="utf-8")
    try:
        load_config(path)
    except ValueError as exc:
        assert "status" in str(exc)
    else:
        raise AssertionError("expected ValueError")
