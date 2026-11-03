"""Rule-based detector on band energy, pulse rate, and tonal peaks.

This is the stand-in for an ML model. It looks for the same three call
templates the synthesizer produces, plus a close boat pass:

- sturgeon thunder: several impulsive peaks in 15-90 Hz whose spectrum
  peaks near 44 Hz and lasts on the order of 1.9 s
- drum knocks: ~25 impulses near 400 Hz inside ~0.8 s
- toadfish boatwhistle: a harmonic tone with fundamental near 200 Hz
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
