"""Write contract rows locally. Does not open a socket."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DryRunPublisher:
    def __init__(self, output_dir: str):
        self.root = Path(output_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._nodes = (self.root / "sonar_nodes.jsonl").open("w", encoding="utf-8")
        self._tracks = (self.root / "sonar_tracks.jsonl").open("w", encoding="utf-8")
        self._truth = (self.root / "truth.jsonl").open("w", encoding="utf-8")
        self.clips = self.root / "clips"
        self.clips.mkdir(exist_ok=True)

    def close(self) -> None:
        for handle in (self._nodes, self._tracks, self._truth):
            handle.close()

    def heartbeat(self, row: dict) -> None:
        self._write(self._nodes, row)
        logger.info("heartbeat %s status=%s", row.get("id"), row.get("status"))

    def upload_clip(self, storage_path: str, payload: bytes) -> None:
        # Flatten the object key so the dry run stays inside output_dir.
        name = storage_path.replace("/", "__")
        (self.clips / name).write_bytes(payload)

    def insert_track(self, row: dict) -> None:
        self._write(self._tracks, row)
        logger.info(
            "track %s species=%s direction=%s length_cm=%s",
            row["id"],
            row["species_id"],
            row["direction"],
            row["length_cm"],
        )

    def insert_truth(self, row: dict) -> None:
        self._write(self._truth, row)

    @staticmethod
    def _write(handle, row: dict) -> None:
        handle.write(json.dumps(row, sort_keys=False) + "\n")
        handle.flush()
