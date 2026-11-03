"""Suppress splash labels that sit inside a long boat sequence.

Perch scores one 5 s window. A slice of wake can look like splashes in that
window. Dirk's field distinction is temporal: boat wake is constant, or it
stops and starts over tens of seconds, often with engine tonals around it.
Spawning splashes are short impulsive bursts. This layer looks across about
30–90 s of envelope and relabels ``bass_spawning_splash`` to ``boat`` when
the context is a sustained wash or a stop-start pair of long washes.

Buffers shorter than 30 s are left alone. There is not enough context.
"""

from __future__ import annotations

import numpy as np

from hrecos_ml.labels import SPECIES, TARGET_SR

# A wash has to last about this long before it counts as boat, not a splash.
LONG_BLOCK_S = 8.0
# One sustained block, or two of them (stop-start), inside this span.
CONTEXT_S = 90.0
MIN_CONTEXT_S = 30.0


def _bursts(audio: np.ndarray, sample_rate: int) -> list[tuple[float, float]]:
    x = np.asarray(audio, dtype=np.float32)
    if x.size < sample_rate:
        return []
    frame = max(int(0.02 * sample_rate), 1)
    hop = max(frame // 2, 1)
    n = 1 + max(0, (x.size - frame) // hop)
    env = np.empty(n, dtype=np.float32)
    for i in range(n):
        a = i * hop
        env[i] = float(np.mean(np.abs(x[a : a + frame])))
    low = float(np.percentile(env, 50))
    high = float(np.percentile(env, 90))
    if high <= low * 1.05:
        return []
    threshold = low + 0.45 * (high - low)
    on = env >= threshold
    spans: list[tuple[int, int]] = []
    i = 0
    while i < on.size:
        if not on[i]:
            i += 1
            continue
        j = i + 1
        while j < on.size and on[j]:
            j += 1
        spans.append((i, j))
        i = j
    # Merge hits separated by less than 0.15 s so one splash is one burst.
    gap_frames = max(int(0.15 * sample_rate / hop), 1)
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start - merged[-1][1] <= gap_frames:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    out = []
    for start, end in merged:
        t0 = start * hop / sample_rate
        t1 = min(x.size / sample_rate, (end * hop + frame) / sample_rate)
        if t1 > t0:
            out.append((float(t0), float(t1)))
    return out


def gate_splash_labels(
    events: list[dict],
    audio: np.ndarray,
    sample_rate: int = TARGET_SR,
) -> list[dict]:
    """Return a copy of ``events`` with boat-context splashes relabeled."""
    duration = float(len(audio)) / float(sample_rate) if len(audio) else 0.0
    if duration < MIN_CONTEXT_S or not events:
        return [dict(event) for event in events]
    bursts = _bursts(audio, sample_rate)
    gated = []
    for event in events:
        row = dict(event)
        if row.get("label") == "bass_spawning_splash" and _in_boat_context(
            bursts, float(row["start_time"]), float(row["end_time"]), duration
        ):
            row["label"] = "boat"
            row["species_id"] = SPECIES["boat"]["species_id"]
        gated.append(row)
    return gated


def drop_boat_outside_wash(
    events: list[dict],
    audio: np.ndarray,
    sample_rate: int = TARGET_SR,
) -> list[dict]:
    """Drop boat labels that are not inside a sustained or stop-start wash.

    Splash bouts are short bursts. The 5 s probe still calls some of those
    windows ``boat``. A real wake keeps its boat labels, because they sit on
    an elevated block of at least 8 s or between two such blocks. Buffers
    shorter than 30 s are left alone.
    """
    duration = float(len(audio)) / float(sample_rate) if len(audio) else 0.0
    if duration < MIN_CONTEXT_S or not events:
        return [dict(event) for event in events]
    bursts = _bursts(audio, sample_rate)
    kept = []
    for event in events:
        row = dict(event)
        if row.get("label") == "boat" and not _in_boat_context(
            bursts, float(row["start_time"]), float(row["end_time"]), duration
        ):
            continue
        kept.append(row)
    return kept


def _in_boat_context(
    bursts: list[tuple[float, float]],
    start_s: float,
    end_s: float,
    duration: float,
) -> bool:
    """True when this splash sits inside a sustained or stop-start wash.

    Three measurements over the ~90 s context:

    * burst duration — a block of elevated envelope lasting at least 8 s
    * duty cycle — fraction of the context that envelope stays elevated
    * inter-burst interval — gaps between those blocks

    A single long block, or a high duty cycle with short gaps, is a
    sustained wake. Two or more long blocks make a stop-start sequence,
    and a splash anywhere between the first and last of those blocks is
    suppressed, including the quiet gap.
    """
    mid = 0.5 * (start_s + end_s)
    c0 = max(0.0, mid - CONTEXT_S / 2.0)
    c1 = min(duration, c0 + CONTEXT_S)
    c0 = max(0.0, c1 - CONTEXT_S)
    if c1 - c0 < MIN_CONTEXT_S:
        return False
    inside = [(max(a, c0), min(b, c1)) for a, b in bursts if b > c0 and a < c1]
    if not inside:
        return False
    covered = sum(b - a for a, b in inside)
    duty = covered / (c1 - c0)
    ordered = sorted(inside)
    gaps = [a2 - b1 for (_, b1), (a2, _) in zip(ordered, ordered[1:])]
    long = [(a, b) for a, b in ordered if (b - a) >= LONG_BLOCK_S]
    overlaps_long = any(a <= end_s and b >= start_s for a, b in long)
    overlaps_energy = any(a <= end_s and b >= start_s for a, b in ordered)
    near_long = any(a - 2.0 <= end_s and b + 2.0 >= start_s for a, b in long)
    if overlaps_long or near_long:
        return True
    if len(long) >= 2:
        seq0 = min(a for a, _ in long)
        seq1 = max(b for _, b in long)
        if end_s > seq0 and start_s < seq1:
            return True
    # Wash that the envelope picker split into pieces: still high duty,
    # short gaps, and at least one long-block's worth of energy.
    if duty >= 0.55 and covered >= LONG_BLOCK_S and overlaps_energy:
        median_gap = float(np.median(gaps)) if gaps else 0.0
        if median_gap <= 1.0:
            return True
    return False
