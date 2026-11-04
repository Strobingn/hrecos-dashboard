"""Rule-based detector on band energy, pulse rate, and tonal peaks.

This is the stand-in for an ML model. It looks for the call templates the
synthesizer produces, plus a close boat pass:

- sturgeon thunder: several impulsive peaks in 15-90 Hz whose spectrum
  peaks near 44 Hz and lasts on the order of 1.9 s
- drum knocks: ~25 impulses near 400 Hz inside ~0.8 s
- toadfish boatwhistle: a harmonic tone with fundamental near 200 Hz
- striped bass rock fight: a short bout of sharp broadband splashes.
  Burst duration, onset, inter-burst gap, and duty cycle separate it from
  rain and from boat wake (sustained, or stop-start over tens of seconds,
  usually with an engine tonal before the slap)
- boat: several seconds of loud, spectrally flat energy below ~250 Hz
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

from hydrophone_node.contract import LABEL_SPECIES
from hydrophone_node.detect.base import DetectionEvent


def _bandpass(
    samples: np.ndarray, sample_rate: float, low_hz: float, high_hz: float
) -> np.ndarray:
    nyquist = sample_rate / 2.0
    lo = max(low_hz / nyquist, 1e-4)
    hi = min(high_hz / nyquist, 0.99)
    if hi <= lo + 1e-3:
        return np.zeros_like(samples)
    sos = butter(4, [lo, hi], btype="band", output="sos")
    return sosfiltfilt(sos, samples)


def _moving_mean(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, int(window))
    kernel = np.ones(window, dtype=np.float64) / window
    return np.convolve(np.abs(values), kernel, mode="same")


def _confidence(ratio: float, low: float = 2.0, high: float = 12.0) -> float:
    scaled = (ratio - low) / (high - low)
    return float(np.clip(0.55 + 0.4 * scaled, 0.55, 0.97))


def _merge_intervals(
    intervals: list[tuple[float, float]], gap_s: float
) -> list[tuple[float, float]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + gap_s:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _spectrum(samples: np.ndarray, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    window = np.hanning(samples.size)
    spec = np.abs(np.fft.rfft(samples * window))
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / sample_rate)
    return freqs, spec


def _band_energy(
    freqs: np.ndarray, spec: np.ndarray, low_hz: float, high_hz: float
) -> float:
    mask = (freqs >= low_hz) & (freqs < high_hz)
    if not np.any(mask):
        return 0.0
    return float(np.sum(np.square(spec[mask])))


class BandEnergyDetector:
    """Baseline detector. Swap it for an ML model via detector.entrypoint."""

    model_name = "band_energy"
    model_version = "1.0.0"

    def detect(
        self,
        samples: np.ndarray,
        sample_rate: float,
        segment_start: datetime | None = None,
    ) -> list[DetectionEvent]:
        del segment_start  # offsets are converted to timestamps by the pipeline
        x = np.asarray(samples, dtype=np.float64).reshape(-1)
        if x.size < int(sample_rate):
            return []
        x = x - np.mean(x)
        events: list[DetectionEvent] = []
        events.extend(self._sturgeon(x, sample_rate))
        events.extend(self._drum(x, sample_rate))
        events.extend(self._toadfish(x, sample_rate))
        events.extend(self._bass(x, sample_rate))
        events.extend(self._boat(x, sample_rate, events))
        events.sort(key=lambda event: event.start_offset_s)
        return events

    def _event(
        self,
        start_s: float,
        end_s: float,
        label: str,
        confidence: float,
        freq_low_hz: float,
        freq_high_hz: float,
    ) -> DetectionEvent:
        return DetectionEvent(
            start_offset_s=max(0.0, start_s),
            end_offset_s=max(start_s, end_s),
            label=label,
            species_id=LABEL_SPECIES[label],
            confidence=float(confidence),
            freq_low_hz=freq_low_hz,
            freq_high_hz=freq_high_hz,
            model_name=self.model_name,
            model_version=self.model_version,
        )

    def _sturgeon(
        self, samples: np.ndarray, sample_rate: float
    ) -> list[DetectionEvent]:
        band = _bandpass(samples, sample_rate, 15.0, 90.0)
        envelope = _moving_mean(band, int(0.03 * sample_rate))
        floor = float(np.median(envelope)) + 1e-12
        threshold = floor * 8.0
        peaks, _ = find_peaks(
            envelope,
            height=threshold,
            distance=int(0.12 * sample_rate),
            prominence=threshold * 0.4,
        )
        if peaks.size == 0:
            return []
        groups: list[list[int]] = [[int(peaks[0])]]
        max_gap = int(0.45 * sample_rate)
        for peak in peaks[1:]:
            if int(peak) - groups[-1][-1] <= max_gap:
                groups[-1].append(int(peak))
            else:
                groups.append([int(peak)])
        found: list[DetectionEvent] = []
        for group in groups:
            if not 6 <= len(group) <= 12:
                continue
            start = group[0] / sample_rate
            end = group[-1] / sample_rate
            if not 1.2 <= (end - start) <= 2.5:
                continue
            # Include the decay of the last beat.
            slice_end = min(samples.size, group[-1] + int(0.25 * sample_rate))
            segment = samples[group[0] : slice_end]
            freqs, spec = _spectrum(segment, sample_rate)
            in_band = (freqs >= 10.0) & (freqs <= 100.0)
            if not np.any(in_band):
                continue
            peak_hz = float(freqs[in_band][np.argmax(spec[in_band])])
            if not 32.0 <= peak_hz <= 58.0:
                continue
            narrow = _band_energy(freqs, spec, 32.0, 58.0)
            wide = _band_energy(freqs, spec, 10.0, 100.0) + 1e-12
            ratio = narrow / wide
            if ratio < 0.35:
                continue
            pad_start = max(0.0, start - 0.05)
            found.append(
                self._event(
                    pad_start,
                    end + 0.2,
                    "sturgeon_thunder",
                    _confidence(ratio / 0.35 * 4),
                    10.0,
                    100.0,
                )
            )
        return found

    def _drum(self, samples: np.ndarray, sample_rate: float) -> list[DetectionEvent]:
        band = _bandpass(samples, sample_rate, 330.0, 480.0)
        envelope = _moving_mean(band, max(1, int(0.003 * sample_rate)))
        floor = float(np.median(envelope)) + 1e-12
        threshold = floor * 7.0
        peaks, _ = find_peaks(
            envelope,
            height=threshold,
            distance=int(0.02 * sample_rate),
            prominence=threshold * 0.35,
        )
        if peaks.size < 15:
            return []
        times = peaks.astype(np.float64) / sample_rate
        hits: list[tuple[float, float]] = []
        for start in times:
            window = times[(times >= start) & (times < start + 0.9)]
            if window.size < 18:
                continue
            intervals = np.diff(window)
            median_interval = float(np.median(intervals))
            if not 0.024 <= median_interval <= 0.045:
                continue
            hits.append((float(window[0]), float(window[-1] + median_interval)))
        merged = _merge_intervals(hits, 0.15)
        events: list[DetectionEvent] = []
        for start, end in merged:
            if end - start < 0.5 or end - start > 1.6:
                continue
            events.append(
                self._event(start, end, "drum_knock", _confidence(8.0), 350.0, 450.0)
            )
        return events

    def _toadfish(
        self, samples: np.ndarray, sample_rate: float
    ) -> list[DetectionEvent]:
        window = int(0.36 * sample_rate)
        hop = int(0.08 * sample_rate)
        if samples.size < window:
            return []
        rms_values = []
        for start in range(0, samples.size - window + 1, hop):
            frame = samples[start : start + window]
            rms_values.append(float(np.sqrt(np.mean(np.square(frame)))))
        if not rms_values:
            return []
        noise_floor = float(np.percentile(rms_values, 20)) + 1e-12
        hits: list[tuple[float, float, float]] = []
        frame_index = 0
        for start in range(0, samples.size - window + 1, hop):
            frame_rms = rms_values[frame_index]
            frame_index += 1
            if frame_rms < noise_floor * 4.0:
                continue
            frame = samples[start : start + window]
            freqs, spec = _spectrum(frame, sample_rate)
            search = (freqs >= 100.0) & (freqs <= 900.0)
            if not np.any(search):
                continue
            search_freqs = freqs[search]
            search_spec = spec[search]
            peak_index = int(np.argmax(search_spec))
            peak_hz = float(search_freqs[peak_index])
            if not 165.0 <= peak_hz <= 245.0:
                continue
            median_mag = float(np.median(search_spec)) + 1e-12
            prominence = float(search_spec[peak_index]) / median_mag
            if prominence < 18.0:
                continue
            harmonic_bin = np.argmin(np.abs(freqs - 2.0 * peak_hz))
            harmonic_ratio = float(spec[harmonic_bin]) / (
                float(search_spec[peak_index]) + 1e-12
            )
            if harmonic_ratio < 0.18:
                continue
            # Drum energy lives near 400 Hz and would not peak at the fundamental.
            if (
                _band_energy(freqs, spec, 330.0, 480.0)
                > _band_energy(freqs, spec, 160.0, 250.0) * 1.4
            ):
                continue
            t0 = start / sample_rate
            hits.append((t0, t0 + window / sample_rate, prominence))
        merged = _merge_intervals([(start, end) for start, end, _ in hits], 0.12)
        events: list[DetectionEvent] = []
        for start, end in merged:
            if not 0.28 <= (end - start) <= 1.3:
                continue
            events.append(
                self._event(
                    start, end, "toadfish_boatwhistle", _confidence(10.0), 150.0, 700.0
                )
            )
        return events

    def _bass(self, samples: np.ndarray, sample_rate: float) -> list[DetectionEvent]:
        """Broadband impulsive bursts clustered into a short bout.

        A spawning splash is a sharp onset, a few tens of milliseconds long,
        and the next splash follows within a few tenths of a second. The
        envelope then drops. Over a 30–120 s window the duty cycle stays low.

        Boat wake fails that shape. It is constant, or it stops and starts
        over tens of seconds, and an engine tonal / low-frequency rumble is
        usually already present when the slap arrives. Rain fails it by
        staying spread out, with drops too short and too evenly spaced to
        form one isolated bout.
        """
        high_hz = min(2000.0, sample_rate * 0.45)
        if high_hz <= 400.0:
            return []
        band = _bandpass(samples, sample_rate, 350.0, high_hz)
        envelope = _moving_mean(band, max(1, int(0.002 * sample_rate)))
        floor = float(np.median(envelope)) + 1e-12
        threshold = floor * 10.0
        peaks, _ = find_peaks(
            envelope,
            height=threshold,
            distance=int(0.08 * sample_rate),
            prominence=threshold * 0.5,
        )
        qualified: list[tuple[float, float, float]] = []
        for peak in peaks:
            shape = _burst_shape(envelope, int(peak), sample_rate)
            if shape is None:
                continue
            duration_s, onset_s = shape
            # Longer than a rain drop, shorter than a wake slap.
            if not 0.008 <= duration_s <= 0.09:
                continue
            if onset_s > 0.015:
                continue
            local = _local_median(envelope, int(peak), int(0.25 * sample_rate))
            if envelope[int(peak)] < local * 6.0:
                continue
            qualified.append((float(peak) / sample_rate, duration_s, onset_s))
        if len(qualified) < 4:
            return []

        bouts: list[list[tuple[float, float, float]]] = [[qualified[0]]]
        for burst in qualified[1:]:
            gap = burst[0] - bouts[-1][-1][0]
            if 0.08 <= gap <= 0.9:
                bouts[-1].append(burst)
            else:
                bouts.append([burst])

        duration = samples.size / sample_rate
        low_frames, low_times = _low_band_frames(samples, sample_rate)
        events: list[DetectionEvent] = []
        for bout in bouts:
            if not 4 <= len(bout) <= 14:
                continue
            start = bout[0][0]
            end = bout[-1][0] + bout[-1][1]
            span = end - start
            if not 0.7 <= span <= 5.5:
                continue
            intervals = np.diff([item[0] for item in bout])
            median_interval = float(np.median(intervals))
            if not 0.12 <= median_interval <= 0.7:
                continue
            outside = sum(
                1 for item in qualified if item[0] < start - 0.5 or item[0] > end + 0.5
            )
            # A few stray impulses (a drum knock, one short splash) can sit
            # outside the bout. Rain puts impulses across the whole window.
            if outside > 4:
                continue
            # Inside the bout the envelope has to fall between splashes.
            # A wake wash stays up, so its duty cycle inside the "bout" is high.
            if (
                _between_burst_quiet(
                    envelope, sample_rate, [item[0] for item in bout], threshold
                )
                < 0.45
            ):
                continue
            window_start, window_end = _duty_window(start, end, duration)
            # Over 30–120 s (or the whole clip when it is shorter) splashes
            # occupy little of the window. Sustained wake does not.
            if (
                _envelope_duty(
                    envelope, sample_rate, window_start, window_end, threshold
                )
                > 0.4
            ):
                continue
            if _sustained_low(low_frames, low_times, start - 8.0, end, min_run_s=3.0):
                continue
            if _engine_tonal(samples, sample_rate, max(0.0, start - 8.0), start):
                continue
            events.append(
                self._event(
                    max(0.0, start - 0.05),
                    end + 0.05,
                    "bass_spawning_splash",
                    _confidence(float(len(bout))),
                    200.0,
                    2000.0,
                )
            )
        return events

    def _boat(
        self,
        samples: np.ndarray,
        sample_rate: float,
        fish: list[DetectionEvent],
    ) -> list[DetectionEvent]:
        window = int(0.5 * sample_rate)
        hop = int(0.25 * sample_rate)
        if samples.size < window:
            return []
        band = _bandpass(samples, sample_rate, 20.0, 250.0)
        frame_rms = []
        frame_times = []
        for start in range(0, band.size - window + 1, hop):
            frame = band[start : start + window]
            frame_rms.append(float(np.sqrt(np.mean(np.square(frame)))))
            frame_times.append(start / sample_rate)
        if not frame_rms:
            return []
        levels = np.asarray(frame_rms)
        floor = float(np.percentile(levels, 25)) + 1e-12
        loud = levels > max(floor * 4.0, 0.04)
        active = _fill_short_gaps(loud, gap_frames=2)
        intervals: list[tuple[float, float]] = []
        run_start: int | None = None
        for index, flag in enumerate(active):
            if flag and run_start is None:
                run_start = index
            elif not flag and run_start is not None:
                intervals.append((frame_times[run_start], frame_times[index - 1] + 0.5))
                run_start = None
        if run_start is not None:
            intervals.append((frame_times[run_start], frame_times[-1] + 0.5))
        events: list[DetectionEvent] = []
        duration = samples.size / sample_rate
        for start, end in intervals:
            start = max(0.0, start)
            end = min(duration, end)
            if end - start < 2.0:
                continue
            if _overlap_fraction(start, end, fish) > 0.5:
                continue
            a = int(start * sample_rate)
            b = min(samples.size, int(end * sample_rate))
            region = samples[a:b]
            if region.size < window:
                continue
            freqs, spec = _spectrum(region, sample_rate)
            band_mask = (freqs >= 20.0) & (freqs <= 250.0)
            power = np.square(spec[band_mask])
            power = power[power > 0]
            if power.size < 8:
                continue
            geometric = float(np.exp(np.mean(np.log(power + 1e-20))))
            arithmetic = float(np.mean(power)) + 1e-20
            flatness = geometric / arithmetic
            # Tones (hum, boatwhistle, thunder) are peaky. A boat pass is not.
            if flatness < 0.12:
                continue
            ratio = float(np.median(levels[active])) / floor if np.any(active) else 1.0
            events.append(
                self._event(start, end, "boat", _confidence(ratio), 10.0, 500.0)
            )
        return events


def _burst_shape(
    envelope: np.ndarray, peak: int, sample_rate: float
) -> tuple[float, float] | None:
    """Return (duration_s, onset_s) for one impulsive peak.

    Duration is the time the envelope stays above a quarter of the peak.
    Onset is the rise from 20% to 80% of the peak. A spawning splash is short
    and steep. A wake slap is longer and takes longer to arrive.
    """
    peak_val = float(envelope[peak])
    if peak_val <= 0:
        return None
    left_limit = max(0, peak - int(0.1 * sample_rate))
    left = peak
    while left > left_limit and envelope[left] > 0.25 * peak_val:
        left -= 1
    right_limit = min(envelope.size - 1, peak + int(0.15 * sample_rate))
    right = peak
    while right < right_limit and envelope[right] > 0.25 * peak_val:
        right += 1
    duration_s = (right - left) / sample_rate
    climb = envelope[left : peak + 1]
    if climb.size < 2:
        return None
    above_20 = np.flatnonzero(climb >= 0.2 * peak_val)
    above_80 = np.flatnonzero(climb >= 0.8 * peak_val)
    if above_20.size == 0 or above_80.size == 0:
        return None
    onset_s = (int(above_80[0]) - int(above_20[0])) / sample_rate
    return duration_s, max(0.0, onset_s)


def _local_median(envelope: np.ndarray, peak: int, radius: int) -> float:
    start = max(0, peak - radius)
    stop = min(envelope.size, peak + radius)
    return float(np.median(envelope[start:stop])) + 1e-12


def _duty_window(
    bout_start: float, bout_end: float, duration: float
) -> tuple[float, float]:
    """Window of 30–120 s around a bout, or the whole clip when it is shorter."""
    if duration <= 120.0:
        return 0.0, duration
    span = 60.0
    start = max(0.0, bout_start - 20.0)
    end = min(duration, start + span)
    start = max(0.0, end - span)
    return start, end


def _between_burst_quiet(
    envelope: np.ndarray,
    sample_rate: float,
    burst_times: list[float],
    threshold: float,
) -> float:
    """Fraction of the gaps between bursts that have already fallen quiet."""
    quiet = []
    for left, right in zip(burst_times, burst_times[1:]):
        start = int(left * sample_rate)
        stop = int(right * sample_rate)
        if stop <= start:
            continue
        quiet.append(float(np.mean(envelope[start:stop] < threshold)))
    if not quiet:
        return 0.0
    return float(np.median(quiet))


def _envelope_duty(
    envelope: np.ndarray,
    sample_rate: float,
    start_s: float,
    end_s: float,
    threshold: float,
) -> float:
    start = max(0, int(start_s * sample_rate))
    stop = min(envelope.size, int(end_s * sample_rate))
    if stop <= start:
        return 0.0
    return float(np.mean(envelope[start:stop] > threshold))


def _low_band_frames(
    samples: np.ndarray, sample_rate: float
) -> tuple[np.ndarray, np.ndarray]:
    window = int(0.5 * sample_rate)
    hop = int(0.25 * sample_rate)
    if samples.size < window:
        return np.zeros(0), np.zeros(0)
    low = _bandpass(samples, sample_rate, 20.0, 180.0)
    levels = []
    times = []
    for start in range(0, low.size - window + 1, hop):
        frame = low[start : start + window]
        levels.append(float(np.sqrt(np.mean(np.square(frame)))))
        times.append(start / sample_rate)
    return np.asarray(levels), np.asarray(times)


def _sustained_low(
    levels: np.ndarray,
    times: np.ndarray,
    start_s: float,
    end_s: float,
    min_run_s: float,
) -> bool:
    """True when low-frequency energy stays up for several seconds.

    That is engine rumble or a wake wash, not the gaps inside a splash bout.
    """
    if levels.size == 0:
        return False
    floor = float(np.percentile(levels, 25)) + 1e-12
    loud = levels > max(floor * 4.0, 0.03)
    run_start = None
    for index, flag in enumerate(loud):
        if flag and run_start is None:
            run_start = index
        elif not flag and run_start is not None:
            run_end = times[index - 1] + 0.5
            run_begin = times[run_start]
            if (
                run_end - run_begin >= min_run_s
                and run_end > start_s
                and run_begin < end_s
            ):
                return True
            run_start = None
    if run_start is not None:
        run_begin = times[run_start]
        run_end = times[-1] + 0.5
        if run_end - run_begin >= min_run_s and run_end > start_s and run_begin < end_s:
            return True
    return False


def _engine_tonal(
    samples: np.ndarray, sample_rate: float, start_s: float, end_s: float
) -> bool:
    """Loud low-frequency tonal, the kind an engine leaves before a wake slap.

    Quiet 60 Hz hum does not count: the band has to be loud in absolute level
    and the peak has to stand well above the rest of 25–160 Hz.
    """
    start = max(0, int(start_s * sample_rate))
    stop = min(samples.size, int(end_s * sample_rate))
    if stop - start < int(0.5 * sample_rate):
        return False
    clip = samples[start:stop]
    low = _bandpass(clip, sample_rate, 20.0, 180.0)
    low_rms = float(np.sqrt(np.mean(np.square(low))))
    if low_rms < 0.035:
        return False
    freqs, spec = _spectrum(clip, sample_rate)
    band = (freqs >= 25.0) & (freqs <= 160.0)
    if not np.any(band):
        return False
    band_spec = spec[band]
    band_freqs = freqs[band]
    peak_index = int(np.argmax(band_spec))
    prominence = float(band_spec[peak_index]) / (float(np.median(band_spec)) + 1e-12)
    if prominence < 8.0:
        return False
    peak_hz = float(band_freqs[peak_index])
    # Mains hum alone is not an engine. An engine here is louder and harmonic.
    if abs(peak_hz - 60.0) < 4.0 and low_rms < 0.06:
        return False
    return True


def _fill_short_gaps(mask: np.ndarray, gap_frames: int) -> np.ndarray:
    """Treat a few quiet frames inside a loud run as still loud."""
    filled = np.asarray(mask, dtype=bool).copy()
    on = np.flatnonzero(filled)
    if on.size < 2:
        return filled
    for left, right in zip(on[:-1], on[1:]):
        if 1 < (right - left) <= gap_frames + 1:
            filled[left : right + 1] = True
    return filled


def _overlap_fraction(start: float, end: float, events: list[DetectionEvent]) -> float:
    span = max(end - start, 1e-6)
    overlap = 0.0
    for event in events:
        left = max(start, event.start_offset_s)
        right = min(end, event.end_offset_s)
        if right > left:
            overlap += right - left
    return overlap / span
