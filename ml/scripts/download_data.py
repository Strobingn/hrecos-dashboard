#!/usr/bin/env python3
"""Download public reference audio and the Perch 2.0 ONNX backbone.

Large files land in ``ml/data/``, which is gitignored. Failures are recorded
and do not abort the other sources. Re-running skips files that already exist.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hrecos_ml.dataset import write_manifest  # noqa: E402

DATA = ROOT / "data"
PERCH_URL = "https://huggingface.co/biodiversica/Perch-onnx-backbone/resolve/main/perch_v2_backbone.onnx"
TFLITE_URL = "https://huggingface.co/biodiversica/Perch-onnx-backbone/resolve/main/perch_v2_backbone.tflite"
SURFPERCH_URL = "https://zenodo.org/api/records/11060189/files/SurfPerch_v1.0.zip/content"

FISHSOUNDS_ATTR = (
    "Looby, A. et al. (2021). FishSounds Website Data Repository. "
    "https://doi.org/10.5683/SP2/TACOUX, Borealis, V10. CC BY-NC 4.0. "
    "Non-commercial. Do not redistribute the recordings with this repository."
)

# file id, manifest label, note
FISHSOUNDS = [
    (200686, "drum_knock", "Aplodinotus grunniens drum call 1, Rountree 2017"),
    (200719, "drum_knock", "Aplodinotus grunniens drum call 2, Rountree 2017"),
    (200764, "drum_knock", "Aplodinotus grunniens drum call 3, Rountree 2017"),
    (200676, "drum_knock", "Aplodinotus grunniens drum chorus, Rountree 2017"),
    (843171, "toadfish_boatwhistle", "Opsanus beta complex call, Looby 2022. Gulf toadfish, not oyster toadfish."),
    (843165, "unscored", "Opsanus beta grunt, Looby 2022. Not a boatwhistle; scored only as a qualitative check."),
    (
        200588,
        "toadfish_boatwhistle",
        "Halobatrachus didactylus boatwhistle, Amorim 2008. Lusitanian toadfish, not Opsanus tau.",
    ),
]

STURGEON = [
    (
        "https://www.int-res.com/articles/suppl/n058p001_AS1.mp3",
        "n058p001_AS1.mp3",
        "sturgeon_thunder",
        "Cohen et al. 2025 ESR doi:10.3354/esr01429 supplementary audio S1, wild Atlantic sturgeon thunder.",
    ),
    (
        "https://www.int-res.com/articles/suppl/n058p001_AS2.mp3",
        "n058p001_AS2.mp3",
        "sturgeon_thunder",
        "Cohen et al. 2025 ESR doi:10.3354/esr01429 supplementary audio S2, captive Atlantic sturgeon thunder.",
    ),
]

# Public NOAA NCEI objects. These FLACs are hundreds of MB, so only a header
# byte range is fetched and decoded. They are unlabeled ambient audio.
NOAA_OBJECTS = [
    "cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_02/audio/144488Hudson_024K_AS02_ST300-5683_20210424_090503Zm0400.flac",
    "cornell/audio/noaa_nerrs/as/noaa-nerrs_hudsonriver_2023-2024_as_05/audio/",
]


def _get(
    url: str,
    dest: Path,
    headers: dict | None = None,
    timeout: int = 120,
    max_bytes: int | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "hrecos-ml/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response, dest.open("wb") as handle:
        written = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            if max_bytes is not None and written + len(chunk) > max_bytes:
                chunk = chunk[: max_bytes - written]
            handle.write(chunk)
            written += len(chunk)
            if max_bytes is not None and written >= max_bytes:
                break


def _record(log: dict, name: str, ok: bool, detail: str, path: str | None = None) -> None:
    log["sources"].append({"name": name, "ok": ok, "detail": detail, "path": path})
    print(f"[{'ok' if ok else 'FAIL'}] {name}: {detail}")


def download_perch(log: dict, fetch_tflite: bool) -> Path | None:
    dest = DATA / "models" / "perch_v2_backbone.onnx"
    cached = Path("/tmp/perch_v2_backbone.onnx")
    try:
        if dest.is_file() and dest.stat().st_size > 1_000_000:
            _record(log, "perch_v2_backbone.onnx", True, f"already present ({dest.stat().st_size} bytes)", str(dest))
        elif cached.is_file() and cached.stat().st_size > 1_000_000:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(cached.read_bytes())
            _record(log, "perch_v2_backbone.onnx", True, f"copied cached download ({dest.stat().st_size} bytes)", str(dest))
        else:
            _get(PERCH_URL, dest, timeout=300)
            _record(log, "perch_v2_backbone.onnx", True, f"downloaded ({dest.stat().st_size} bytes)", str(dest))
    except Exception as exc:  # noqa: BLE001
        _record(log, "perch_v2_backbone.onnx", False, str(exc))
        return None
    if fetch_tflite:
        tflite = DATA / "models" / "perch_v2_backbone.tflite"
        try:
            if not tflite.is_file():
                _get(TFLITE_URL, tflite, timeout=300)
            _record(log, "perch_v2_backbone.tflite", True, f"{tflite.stat().st_size} bytes", str(tflite))
        except Exception as exc:  # noqa: BLE001
            _record(log, "perch_v2_backbone.tflite", False, str(exc))
    return dest


def download_fishsounds(log: dict) -> list[dict]:
    rows = []
    out_dir = DATA / "external" / "fishsounds"
    for file_id, label, note in FISHSOUNDS:
        dest = out_dir / f"{file_id}.wav"
        url = f"https://borealisdata.ca/api/access/datafile/{file_id}?format=original"
        try:
            if not dest.is_file() or dest.stat().st_size < 1000:
                _get(url, dest, timeout=180)
            if dest.stat().st_size < 1000:
                raise RuntimeError(f"file too small ({dest.stat().st_size} bytes)")
            rows.append(
                {
                    "path": str(dest),
                    "label": label,
                    "split": "external",
                    "source": "fishsounds",
                    "file_id": file_id,
                    "license": "CC BY-NC 4.0",
                    "attribution": FISHSOUNDS_ATTR,
                    "note": note,
                }
            )
            _record(log, f"fishsounds:{file_id}", True, f"{dest.stat().st_size} bytes; {note}", str(dest))
        except Exception as exc:  # noqa: BLE001
            _record(log, f"fishsounds:{file_id}", False, str(exc))
    return rows


def download_sturgeon(log: dict) -> list[dict]:
    rows = []
    out_dir = DATA / "external" / "esr01429"
    for url, name, label, note in STURGEON:
        dest = out_dir / name
        try:
            if not dest.is_file() or dest.stat().st_size < 500:
                _get(url, dest, timeout=60)
            rows.append(
                {
                    "path": str(dest),
                    "label": label,
                    "split": "external",
                    "source": "esr01429",
                    "license": "journal supplementary audio; not redistributed",
                    "attribution": note,
                    "note": note,
                }
            )
            _record(log, name, True, f"{dest.stat().st_size} bytes", str(dest))
        except Exception as exc:  # noqa: BLE001
            _record(log, name, False, str(exc))
    return rows


def _first_audio_object(prefix: str) -> str | None:
    if not prefix.endswith("/"):
        return prefix
    api = "https://storage.googleapis.com/storage/v1/b/noaa-passive-bioacoustic/o?maxResults=5&prefix=" + urllib.request.quote(
        prefix, safe=""
    )
    with urllib.request.urlopen(api, timeout=60) as response:
        payload = json.load(response)
    for item in payload.get("items") or []:
        name = item["name"]
        if name.endswith((".flac", ".wav", ".mp3")):
            return name
    return None


def download_noaa_excerpts(log: dict, range_bytes: int = 12_000_000) -> list[dict]:
    """Decode a few seconds from the start of two Hudson River FLACs.

    Object names are not call-annotated, so every excerpt is labeled background.
    """
    rows = []
    out_dir = DATA / "external" / "noaa_hudson"
    out_dir.mkdir(parents=True, exist_ok=True)
    for spec in NOAA_OBJECTS:
        try:
            object_name = _first_audio_object(spec)
            if not object_name:
                raise RuntimeError(f"no audio object under {spec}")
            partial = out_dir / (Path(object_name).name + ".partial")
            url = "https://storage.googleapis.com/" + "noaa-passive-bioacoustic/" + urllib.request.quote(object_name)
            if not partial.is_file() or partial.stat().st_size < 100_000:
                _get(
                    url,
                    partial,
                    headers={"User-Agent": "hrecos-ml/0.1", "Range": f"bytes=0-{range_bytes - 1}"},
                    max_bytes=range_bytes,
                    timeout=180,
                )
            wav = out_dir / (Path(object_name).stem + "_excerpt.wav")
            proc = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", str(partial), "-t", "20", "-ac", "1", str(wav)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0 or not wav.is_file():
                raise RuntimeError(proc.stderr[-400:] or "ffmpeg failed")
            rows.append(
                {
                    "path": str(wav),
                    "label": "background",
                    "split": "external",
                    "source": "noaa_ncei",
                    "license": "US government work, NOAA NCEI passive acoustic archive",
                    "attribution": (
                        "gs://noaa-passive-bioacoustic/"
                        + object_name
                        + " (first 20 s decoded from a partial download). Unlabeled ambient audio, "
                        "project NOAA-NERRS Hudson River 2023-2024."
                    ),
                    "note": "Unlabeled. Used only as an external background check, not as a fish label.",
                    "gcs_object": object_name,
                }
            )
            _record(log, "noaa:" + Path(object_name).name, True, f"excerpt {wav.stat().st_size} bytes", str(wav))
        except Exception as exc:  # noqa: BLE001
            _record(log, "noaa:" + spec[-40:], False, str(exc))
    return rows


def download_surfperch(log: dict) -> None:
    dest = DATA / "models" / "SurfPerch_v1.0.zip"
    try:
        if not dest.is_file():
            _get(SURFPERCH_URL, dest, timeout=300)
        _record(log, "SurfPerch_v1.0.zip", True, f"{dest.stat().st_size} bytes", str(dest))
    except Exception as exc:  # noqa: BLE001
        _record(log, "SurfPerch_v1.0.zip", False, str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tflite", action="store_true", help="also download the TFLite backbone (~43 MB)")
    parser.add_argument("--surfperch", action="store_true", help="also download the Zenodo SurfPerch zip (~128 MB)")
    parser.add_argument("--skip-audio", action="store_true", help="only fetch the embedding model")
    args = parser.parse_args()

    log: dict = {"sources": []}
    download_perch(log, fetch_tflite=args.tflite)
    rows: list[dict] = []
    if not args.skip_audio:
        rows.extend(download_fishsounds(log))
        rows.extend(download_sturgeon(log))
        rows.extend(download_noaa_excerpts(log))
    if args.surfperch:
        download_surfperch(log)
    manifest = DATA / "external_manifest.jsonl"
    if rows:
        write_manifest(manifest, rows)
    log_path = DATA / "download_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2))
    # A copy under artifacts is safe to commit: it has no audio, only status lines.
    artifact_log = ROOT / "artifacts" / "data_access.json"
    artifact_log.parent.mkdir(parents=True, exist_ok=True)
    public = {
        "sources": [
            {"name": item["name"], "ok": item["ok"], "detail": item["detail"]}
            for item in log["sources"]
        ]
    }
    artifact_log.write_text(json.dumps(public, indent=2))
    failed = [item for item in log["sources"] if not item["ok"]]
    print(f"wrote {manifest if rows else '(no manifest)'} ; failures={len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
