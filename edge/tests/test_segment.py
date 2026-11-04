from datetime import datetime, timezone

import numpy as np

from hydrophone_node.audio.segment import iter_segments


def test_segments_are_contiguous_and_drop_the_tail():
    sample_rate = 10
    chunks = [np.ones(25, dtype=np.float32), np.arange(12, dtype=np.float32)]
    origin = datetime(2026, 6, 1, tzinfo=timezone.utc)
    segments = list(iter_segments(iter(chunks), sample_rate, 3.0, origin))
    # 37 samples, segment length 30, one segment, 7 dropped.
    assert len(segments) == 1
    assert segments[0].samples.size == 30
    assert segments[0].start_time == origin
    assert (segments[0].end_time - segments[0].start_time).total_seconds() == 3
    assert segments[0].samples[25] == 0


def test_second_segment_continues_the_clock():
    sample_rate = 1000
    chunk = np.zeros(2500, dtype=np.float32)
    origin = datetime(2026, 6, 1, tzinfo=timezone.utc)
    segments = list(iter_segments(iter([chunk]), sample_rate, 1.0, origin))
    assert len(segments) == 2
    assert segments[1].start_time == segments[0].end_time
    assert (segments[1].start_time - origin).total_seconds() == 1
