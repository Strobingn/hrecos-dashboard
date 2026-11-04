"""Upload metadata and clips through the Supabase REST API (supabase-py).

Uses the service role key from the environment. That key bypasses RLS, so it
stays on the node and never goes in an image, a log line, or a dry-run file.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SupabasePublisher:
    def __init__(self, url: str, service_role_key: str, audio_bucket: str = "audio"):
        if not url or not service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required. "
                "Use --dry-run to exercise the node without a network."
            )
        try:
            from supabase import create_client
        except ImportError as exc:
            raise RuntimeError(
                "supabase-py is not installed (pip install supabase)"
            ) from exc
        self.client = create_client(url, service_role_key)
        self.audio_bucket = audio_bucket

    def close(self) -> None:
        return None

    def heartbeat(self, row: dict) -> None:
        self.client.table("hydrophone_nodes").upsert(row).execute()
        logger.info("heartbeat %s status=%s", row.get("id"), row.get("status"))

    def upload_wav(self, storage_path: str, wav_bytes: bytes) -> None:
        bucket = self.client.storage.from_(self.audio_bucket)
        options = {"content-type": "audio/wav", "upsert": "true"}
        try:
            bucket.upload(storage_path, wav_bytes, file_options=options)
        except Exception as exc:
            text = str(exc).lower()
            if "already exists" in text or "duplicate" in text or "409" in text:
                bucket.update(
                    storage_path, wav_bytes, file_options={"content-type": "audio/wav"}
                )
            else:
                raise

    def insert_segment(self, row: dict) -> None:
        self.client.table("audio_segments").insert(row).execute()
        logger.info("segment %s rms_db=%.1f", row["id"], row["rms_db"])

    def insert_detection(self, row: dict) -> None:
        self.client.table("detections").insert(row).execute()
        logger.info(
            "detection %s label=%s confidence=%.2f",
            row["id"],
            row["label"],
            row["confidence"],
        )
