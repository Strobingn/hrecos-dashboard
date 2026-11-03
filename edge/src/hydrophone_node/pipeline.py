"""Heartbeat, segment, detect, publish."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from hydrophone_node.audio.segment import iter_segments
from hydrophone_node.audio.sources import open_source
from hydrophone_node.config import AppConfig
from hydrophone_node.detect.base import Detector
from hydrophone_node.publish.rows import build_segment_product, node_row

logger = logging.getLogger(__name__)


def run(
    config: AppConfig,
    publisher,
    detector: Detector,
    max_segments: int | None = None,
    sleep=time.sleep,
    now=None,
) -> int:
    """Process the source until it ends or max_segments is reached.

    Returns the number of segments published. replay_speed 0 does not sleep.
    Live device input is already real-time, so it never sleeps.
    """
    source = open_source(config)
    publisher.heartbeat(node_row(config, when=now() if now else None))
    last_heartbeat = time.monotonic()
    produced = 0
    try:
        segments = iter_segments(
            iter(source),
            config.sample_rate_hz,
            config.segment_seconds,
            config.stream_origin(now() if now else None),
        )
        for segment in segments:
            if time.monotonic() - last_heartbeat >= config.heartbeat_interval_s:
                publisher.heartbeat(node_row(config))
                last_heartbeat = time.monotonic()
            product = build_segment_product(segment, config, detector)
            publisher.upload_wav(product["segment"]["storage_path"], product["wav"])
            publisher.insert_segment(product["segment"])
            for detection in product["detections"]:
                publisher.upload_wav(detection["row"]["clip_path"], detection["wav"])
                publisher.insert_detection(detection["row"])
            produced += 1
            labels = [item["row"]["label"] for item in product["detections"]]
            logger.info(
                "segment %s rms_db=%.1f detections=%s",
                product["segment"]["id"],
                product["segment"]["rms_db"],
                labels,
            )
            if max_segments is not None and produced >= max_segments:
                break
            if not source.realtime and config.replay_speed > 0:
                sleep(config.segment_seconds / config.replay_speed)
    finally:
        publisher.close()
    return produced


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
