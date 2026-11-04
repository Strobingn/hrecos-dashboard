"""Write node rows to local JSONL and WAV files. No network."""

from __future__ import annotations

import json
from pathlib import Path


class DryRunPublisher:
    def __init__(self, output_dir: str | Path, echo: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "audio").mkdir(exist_ok=True)
        self.echo = echo
        self._handles = {
            "heartbeat": (self.output_dir / "heartbeats.jsonl").open(
                "a", encoding="utf-8"
            ),
            "segment": (self.output_dir / "audio_segments.jsonl").open(
                "a", encoding="utf-8"
            ),
            "detection": (self.output_dir / "detections.jsonl").open(
                "a", encoding="utf-8"
            ),
        }
        self.counts = {"heartbeat": 0, "segment": 0, "detection": 0}

    def close(self) -> None:
        for handle in self._handles.values():
            if not handle.closed:
                handle.close()

    def _emit(self, kind: str, row: dict) -> None:
        line = json.dumps(row, separators=(",", ":"), sort_keys=False)
        self._handles[kind].write(line + "\n")
        self._handles[kind].flush()
        self.counts[kind] += 1
        if self.echo:
            print(line, flush=True)

    def heartbeat(self, row: dict) -> None:
        self._emit("heartbeat", row)

    def upload_wav(self, storage_path: str, wav_bytes: bytes) -> None:
        dest = self.output_dir / "audio" / storage_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(wav_bytes)

    def insert_segment(self, row: dict) -> None:
        self._emit("segment", row)

    def insert_detection(self, row: dict) -> None:
        self._emit("detection", row)
