"""Generate, classify, and publish one window of synthetic tracks."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone

from sonar_node.classify.base import SonarClassifier
from sonar_node.config import AppConfig
from sonar_node.publish.rows import clip_bytes, node_row, track_row, truth_row
from sonar_node.simulate import generate_tracks

logger = logging.getLogger(__name__)


def run(config: AppConfig, publisher, classifier: SonarClassifier, max_tracks: int | None = None) -> int:
    start, end = config.window()
    now = datetime.now(timezone.utc)
    try:
        publisher.heartbeat(node_row(config, now))
        tracks = generate_tracks(
            start,
            end,
            node_id=config.node.id,
            seed=config.source.seed,
            rate=config.source.rate,
        )
        if max_tracks is not None:
            tracks = tracks[: max(0, max_tracks)]
        counts: Counter[str] = Counter()
        for track in tracks:
            classification = classifier.classify(track)
            row = track_row(track, classification)
            publisher.upload_clip(row["clip_path"], clip_bytes(track, classification))
            publisher.insert_track(row)
            publisher.insert_truth(truth_row(track))
            counts[classification.species_id or "unclassified"] += 1
        logger.info("classified %s", dict(counts))
        if config.replay_speed > 0:
            logger.info(
                "replay_speed=%s is not applied; synthetic tracks are written as a batch",
                config.replay_speed,
            )
        return len(tracks)
    finally:
        publisher.close()
