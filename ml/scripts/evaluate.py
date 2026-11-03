#!/usr/bin/env python3
"""Evaluate the committed probe on synthetic events and on downloaded recordings.

Prints per-class precision/recall and writes ``metrics.json`` next to the
artifact. Numbers in ``ml/README.md`` are copied from that file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hrecos_ml.audio import load_audio  # noqa: E402
from hrecos_ml.dataset import read_manifest  # noqa: E402
from hrecos_ml.infer import clear_detector_cache, detect  # noqa: E402
from hrecos_ml.labels import (  # noqa: E402
    INFERENCE_LABEL,
    MODEL_NAME,
    MODEL_VERSION,
    TARGET_SR,
    TRAIN_LABELS,
)
from hrecos_ml.probe import fit_probe  # noqa: E402
from hrecos_ml.synthesize import (  # noqa: E402
    render_background,
    render_clip,
    render_splash_bout,
    render_stop_start_wake,
)

ARTIFACT = ROOT / "artifacts" / MODEL_NAME / MODEL_VERSION


def _top(probe, features: np.ndarray) -> tuple[str, float]:
    probs = probe.predict_proba(features)
    winner = int(np.argmax(probs))
    return probe.classes[winner], float(probs[0, winner])


def _rel(path: str) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return Path(path).name


FEATURE_SETS = {
    "perch_v2_backbone": ("perch_v2_backbone",),
    "lowband_v1": ("lowband_v1",),
    "perch_v2_backbone+lowband_v1": ("perch_v2_backbone", "lowband_v1"),
}


def _matrix(cache: dict, columns: tuple[str, ...]) -> np.ndarray:
    parts = [cache[name] for name in columns]
    return parts[0] if len(parts) == 1 else np.concatenate(parts, axis=1)


def _external_transfer(probe, cache: dict, columns: tuple[str, ...]) -> list[dict]:
    if any(name not in cache for name in columns) or cache["labels"].size == 0:
        return []
    x = _matrix(cache, columns)
    rows = []
    for i in range(x.shape[0]):
        label, confidence = _top(probe, x[i : i + 1])
        rows.append(
            {
                "path": _rel(str(cache["paths"][i])),
                "source": str(cache["sources"][i]),
                "reference_label": str(cache["labels"][i]),
                "predicted_train_label": label,
                "confidence": confidence,
            }
        )
    return rows


def _leave_one_file_out(synthetic: dict, external: dict, columns: tuple[str, ...]) -> list[dict]:
    """Fit a fresh probe for each held-out real fish clip. Not saved."""
    if any(name not in external for name in columns) or external["labels"].size == 0:
        return []
    syn_x = _matrix(synthetic, columns)
    ext_x = _matrix(external, columns)
    syn_y = np.asarray([str(v) for v in synthetic["labels"]])
    syn_split = np.asarray([str(v) for v in synthetic["splits"]])
    train_x = syn_x[syn_split == "train"]
    train_y = syn_y[syn_split == "train"]
    ext_y = np.asarray([str(v) for v in external["labels"]])
    results = []
    for i in range(ext_x.shape[0]):
        reference = ext_y[i]
        if reference not in TRAIN_LABELS or reference == "background":
            continue
        keep = np.ones(ext_x.shape[0], dtype=bool)
        keep[i] = False
        usable = keep & np.array([label in TRAIN_LABELS and label != "unscored" for label in ext_y])
        # Other real clips join the synthetic train set. The held-out file does not.
        extra_y = ext_y[usable]
        extra_y = np.array([label if label in TRAIN_LABELS else "background" for label in extra_y])
        x = np.concatenate([train_x, ext_x[usable]], axis=0) if np.any(usable) else train_x
        y = np.concatenate([train_y, extra_y]) if np.any(usable) else train_y
        probe = fit_probe(x, y, seed=i)
        pred, confidence = _top(probe, ext_x[i : i + 1])
        results.append(
            {
                "path": _rel(str(external["paths"][i])),
                "source": str(external["sources"][i]),
                "reference_label": reference,
                "predicted_train_label": pred,
                "confidence": confidence,
                "correct": pred == reference,
            }
        )
    return results


def _event_timing(n_scenes: int = 8, seed: int = 7) -> dict:
    """Drop a synthetic clip into a longer background buffer at a known offset."""
    rng = np.random.default_rng(seed)
    clear_detector_cache()
    per_class = []
    for label in (
        "sturgeon_thunder",
        "drum_knock",
        "toadfish_boatwhistle",
        "bass_spawning_splash",
        "boat",
        "train",
        "hum_60hz",
        "rain",
        "wave_slap",
    ):
        hits = 0
        start_errors = []
        for _ in range(n_scenes):
            duration_s = 15.0
            n = int(duration_s * TARGET_SR)
            buffer = render_background(n, rng) * 0.15
            clip = render_clip(label, 5 * TARGET_SR, rng)
            offset_s = float(rng.uniform(1.0, 8.0))
            offset = int(offset_s * TARGET_SR)
            buffer[offset : offset + clip.size] += clip
            peak = float(np.max(np.abs(buffer)) + 1e-9)
            buffer = (buffer * (0.98 / peak)).astype(np.float32)
            found = detect(buffer, TARGET_SR, hop_s=1.0)
            matched = [
                event
                for event in found
                if event["label"] == _expected_detection_label(label)
                and event["end_time"] >= offset_s
                and event["start_time"] <= offset_s + 5.0
            ]
            if matched:
                hits += 1
                start_errors.append(abs(matched[0]["start_time"] - offset_s))
        per_class.append(
            {
                "label": label,
                "detection_label": _expected_detection_label(label),
                "scenes": n_scenes,
                "hits": hits,
                "hit_rate": hits / n_scenes,
                "median_abs_start_error_s": float(np.median(start_errors)) if start_errors else None,
            }
        )
    false_positives = 0
    false_positive_labels: list[str] = []
    empty = 6
    for _ in range(empty):
        n = 15 * TARGET_SR
        buffer = (render_background(n, rng) * 0.2).astype(np.float32)
        found = detect(buffer, TARGET_SR, hop_s=1.0)
        if found:
            false_positives += 1
            false_positive_labels.extend(sorted({event["label"] for event in found}))
    return {
        "note": (
            "A 5 s synthetic clip is added to 15 s of background at a known offset. "
            "A hit is a detection of the mapped label whose interval overlaps that 5 s span. "
            "Start error is coarse because the model sees 5 s windows on a 1 s hop. "
            "These scenes are 15 s, under the 30 s minimum for the splash gate."
        ),
        "per_class": per_class,
        "background_only_scenes": empty,
        "background_only_scenes_with_a_detection": false_positives,
        "background_only_labels": false_positive_labels,
    }


def _expected_detection_label(train_label: str) -> str:
    return INFERENCE_LABEL[train_label]


def _labels_present(events: list[dict], label: str) -> bool:
    return any(event["label"] == label for event in events)


def _sequence_gate(n_files: int = 8, seed: int = 11) -> dict:
    """Long synthetic wakes versus splash bouts, with and without the gate.

    Windows are 5 s. The gate only sees files of 90 s, which is inside the
    30–120 s context it was written for. These clips are not in the training
    manifest; ``render_boat`` sometimes crops the same wake family, so the
    window classifier is not blind to wash, and this check can still be
    optimistic.
    """
    rng = np.random.default_rng(seed)
    clear_detector_cache()
    duration_s = 90.0

    def _run(render) -> dict:
        splash_off = 0
        splash_on = 0
        boat_off = 0
        boat_on = 0
        for _ in range(n_files):
            audio = render(duration_s, rng)
            off = detect(audio, TARGET_SR, hop_s=1.0, temporal_gate=False)
            on = detect(audio, TARGET_SR, hop_s=1.0, temporal_gate=True)
            splash_off += int(_labels_present(off, "bass_spawning_splash"))
            splash_on += int(_labels_present(on, "bass_spawning_splash"))
            boat_off += int(_labels_present(off, "boat"))
            boat_on += int(_labels_present(on, "boat"))
        return {
            "files": n_files,
            "duration_s": duration_s,
            "files_with_bass_spawning_splash_without_gate": splash_off,
            "files_with_bass_spawning_splash_with_gate": splash_on,
            "files_with_boat_without_gate": boat_off,
            "files_with_boat_with_gate": boat_on,
        }

    wake = _run(render_stop_start_wake)
    bout = _run(render_splash_bout)
    return {
        "note": (
            "Each file is 90 s. A file counts if detect() emits that label "
            "anywhere in it. temporal_gate=False is the 5 s probe alone. "
            "temporal_gate=True relabels bass_spawning_splash to boat when "
            "the envelope shows a sustained wash or a stop-start pair of "
            "long washes. There is no real striped-bass splash recording "
            "in this check."
        ),
        "stop_start_wake": wake,
        "splash_bout": bout,
    }


def _full_file_detections(manifest: Path) -> list[dict]:
    if not manifest.is_file():
        return []
    rows = []
    for row in read_manifest(manifest):
        audio, sr = load_audio(row["path"])
        events = detect(audio, sr, hop_s=1.0)
        rows.append(
            {
                "path": _rel(row["path"]),
                "source": row.get("source"),
                "reference_label": row.get("label"),
                "note": row.get("note"),
                "n_detections": len(events),
                "labels": sorted({event["label"] for event in events}),
                "detections": events,
            }
        )
    return rows


def main() -> int:
    synthetic_path = ROOT / "artifacts" / "cache" / "synthetic.npz"
    external_path = ROOT / "artifacts" / "cache" / "external.npz"
    manifest = ROOT / "data" / "external_manifest.jsonl"
    if not (ARTIFACT / "probe.npz").is_file():
        raise SystemExit("missing trained probe; run scripts/train.py")
    with np.load(synthetic_path, allow_pickle=False) as data:
        synthetic = {key: data[key] for key in data.files}
    external = {}
    if external_path.is_file():
        with np.load(external_path, allow_pickle=False) as data:
            external = {key: data[key] for key in data.files}

    from hrecos_ml.probe import LinearProbe

    metadata = json.loads((ARTIFACT / "metadata.json").read_text())
    embedder_name = metadata["embedder"]
    columns = FEATURE_SETS[embedder_name]
    probe = LinearProbe.load(ARTIFACT / "probe.npz")
    transfer = _external_transfer(probe, external, columns) if external else []
    by_probe = {}
    if external:
        for name, cols in FEATURE_SETS.items():
            slug = "probe.npz" if name == embedder_name else f"probe_{name.replace('+', '_')}.npz"
            probe_path = ARTIFACT / slug
            if not probe_path.is_file():
                continue
            by_probe[name] = _external_transfer(LinearProbe.load(probe_path), external, cols)
    loo = _leave_one_file_out(synthetic, external, columns) if external else []
    print("running synthetic event-timing check...")
    timing = _event_timing()
    print("running long wake vs splash-bout gate check...")
    sequences = _sequence_gate()
    print("running full-file detect() on downloaded audio...")
    files = _full_file_detections(manifest)
    synthetic_metrics = json.loads((ARTIFACT / "metrics_synthetic.json").read_text())
    payload = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "synthetic_test": synthetic_metrics,
        "deployed_embedder": embedder_name,
        "external_center_window_transfer": transfer,
        "external_center_window_by_probe": by_probe,
        "external_leave_one_file_out": loo,
        "synthetic_event_timing": timing,
        "synthetic_sequence_gate": sequences,
        "external_full_file_detections": files,
    }
    out = ARTIFACT / "metrics.json"
    out.write_text(json.dumps(payload, indent=2))
    scored = [row for row in loo if "correct" in row]
    n_correct = sum(1 for row in scored if row["correct"])
    print(f"leave-one-file-out correct {n_correct}/{len(scored)}")
    for row in timing["per_class"]:
        print(f"event {row['label']}: hit_rate={row['hit_rate']:.2f} median_start_err={row['median_abs_start_error_s']}")
    print(
        "background-only scenes with a detection: "
        f"{timing['background_only_scenes_with_a_detection']}/{timing['background_only_scenes']}"
    )
    wake = sequences["stop_start_wake"]
    bout = sequences["splash_bout"]
    print(
        "stop-start wake files with bass_spawning_splash: "
        f"without gate {wake['files_with_bass_spawning_splash_without_gate']}/{wake['files']}, "
        f"with gate {wake['files_with_bass_spawning_splash_with_gate']}/{wake['files']}"
    )
    print(
        "splash-bout files with bass_spawning_splash: "
        f"without gate {bout['files_with_bass_spawning_splash_without_gate']}/{bout['files']}, "
        f"with gate {bout['files_with_bass_spawning_splash_with_gate']}/{bout['files']}"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
