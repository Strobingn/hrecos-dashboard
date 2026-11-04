"""Upload tracks through the Supabase REST API (supabase-py).

Uses the service role key. That key bypasses RLS, so it stays on the node
and never goes in a dry-run file.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SupabasePublisher:
    def __init__(self, url: str, service_role_key: str, sonar_bucket: str = "sonar"):
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
        self.sonar_bucket = sonar_bucket

    def close(self) -> None:
        return None

    def heartbeat(self, row: dict) -> None:
        self.client.table("sonar_nodes").upsert(row).execute()
        logger.info("heartbeat %s status=%s", row.get("id"), row.get("status"))

    def upload_clip(self, storage_path: str, payload: bytes) -> None:
        bucket = self.client.storage.from_(self.sonar_bucket)
        options = {"content-type": "application/json", "upsert": "true"}
        try:
            bucket.upload(storage_path, payload, file_options=options)
        except Exception as exc:
            text = str(exc).lower()
            if "already exists" in text or "duplicate" in text or "409" in text:
                bucket.update(
                    storage_path,
                    payload,
                    file_options={"content-type": "application/json"},
                )
            else:
                raise

    def insert_track(self, row: dict) -> None:
        self.client.table("sonar_tracks").insert(row).execute()
        logger.info(
            "track %s species=%s confidence=%s",
            row["id"],
            row["species_id"],
            row["species_confidence"],
        )

    def insert_truth(self, row: dict) -> None:
        # Truth species is not a column. Uploads do not store it.
        return None
