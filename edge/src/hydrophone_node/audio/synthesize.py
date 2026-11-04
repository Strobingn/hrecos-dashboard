"""Synthetic fish calls mixed into estuary background.

Templates follow the monitoring contract:

- Atlantic sturgeon spawning "thunder": ~1.9 s of percussive beats,
  energy in 10-100 Hz, spectral peak near 44 Hz.
- Freshwater drum knock train: ~25 knocks near 400 Hz across ~0.8 s.
- Oyster toadfish boatwhistle: short tonal call with harmonics.
- Striped bass spawning "rock fight": a short bout of sharp broadband
  surface splashes. Distinct from rain, and from boat wake, which is
  sustained or stop-start over tens of seconds and usually follows engine rumble.

Background is broadband noise plus low-frequency boat rumble and 60 Hz hum,
which both show up constantly on a Pi sitting next to mains power and a river
full of traffic. Rain is optional and off unless asked for.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

STURGEON_DURATION_S = 1.9
STURGEON_PEAK_HZ = 44.0
DRUM_KNOCKS = 25
DRUM_DURATION_S = 0.8
DRUM_FREQ_HZ = 400.0
TOADFISH_DURATION_S = 0.45
TOADFISH_F0_HZ = 200.0
BOAT_PASS_DURATION_S = 5.0
BASS_BOUT_DURATION_S = 2.6
BASS_BURSTS = 7


@dataclass(frozen=True)
class SynthEvent:
    kind: str
    start_s: float
    duration_s: float


def _damped_sine(
    sample_rate: float, freq_hz: float, duration_s: float, decay_s: float
) -> np.ndarray:
    n = max(1, int(round(sample_rate * duration_s)))
    t = np.arange(n, dtype=np.float64) / sample_rate
    return np.sin(2.0 * np.pi * freq_hz * t) * np.exp(-t / decay_s)


def render_sturgeon_thunder(
    sample_rate: float, peak_hz: float = STURGEON_PEAK_HZ
) -> np.ndarray:
    """Eight low-frequency beats spread across ~1.9 s, peaked near 44 Hz.

    Each beat is a damped sinusoid at the peak frequency. The short decay
    spreads energy across 10-100 Hz while the spectrum still peaks near 44 Hz.
    """
    duration = STURGEON_DURATION_S
    n = int(round(sample_rate * duration))
    y = np.zeros(n, dtype=np.float64)
    beat_times = np.linspace(0.05, duration - 0.25, 8)
    for index, beat_time in enumerate(beat_times):
        # A hertz or two of variation keeps the train from being a pure tone.
        freq = peak_hz + (-1.5 if index % 2 else 1.5)
        pulse = _damped_sine(sample_rate, freq, 0.18, 0.04)
        start = int(round(float(beat_time) * sample_rate))
        end = min(n, start + pulse.size)
        y[start:end] += pulse[: end - start]
    peak = np.max(np.abs(y)) + 1e-12
    return y / peak * 0.85


def render_drum_knocks(sample_rate: float, freq_hz: float = DRUM_FREQ_HZ) -> np.ndarray:
    """25 short knocks at ~400 Hz spread across ~0.8 s."""
    duration = DRUM_DURATION_S
    n = int(round(sample_rate * duration))
    y = np.zeros(n, dtype=np.float64)
    pulse = _damped_sine(sample_rate, freq_hz, 0.012, 0.003)
    times = np.linspace(0.0, duration, DRUM_KNOCKS, endpoint=False)
    for knock_time in times:
        start = int(round(float(knock_time) * sample_rate))
        end = min(n, start + pulse.size)
        if start >= n:
            break
        y[start:end] += pulse[: end - start]
    peak = np.max(np.abs(y)) + 1e-12
    return y / peak * 0.85


def render_toadfish_boatwhistle(
    sample_rate: float, f0_hz: float = TOADFISH_F0_HZ
) -> np.ndarray:
    """Tonal boatwhistle: fundamental plus second and third harmonics."""
    duration = TOADFISH_DURATION_S
    n = int(round(sample_rate * duration))
    t = np.arange(n, dtype=np.float64) / sample_rate
    tone = (
        np.sin(2.0 * np.pi * f0_hz * t)
        + 0.55 * np.sin(2.0 * np.pi * 2.0 * f0_hz * t)
        + 0.28 * np.sin(2.0 * np.pi * 3.0 * f0_hz * t)
    )
    envelope = np.ones(n, dtype=np.float64)
    attack = max(1, int(round(0.03 * sample_rate)))
    release = max(1, int(round(0.06 * sample_rate)))
    envelope[:attack] = np.linspace(0.0, 1.0, attack)
    envelope[-release:] = np.linspace(1.0, 0.0, release)
    y = tone * envelope
    # Brief onset grunt, the front of a classic boatwhistle.
    grunt_n = min(n, int(round(0.025 * sample_rate)))
    grunt_t = np.arange(grunt_n, dtype=np.float64) / sample_rate
    grunt = np.sin(2.0 * np.pi * 140.0 * grunt_t) * np.linspace(1.0, 0.0, grunt_n)
    y[:grunt_n] += 0.35 * grunt
    peak = np.max(np.abs(y)) + 1e-12
    return y / peak * 0.75


def render_boat_pass(
    sample_rate: float,
    duration_s: float,
    rng: np.random.Generator,
    amplitude: float = 0.22,
) -> np.ndarray:
    """Close boat pass: loud, smooth, low-frequency broadband noise."""
    n = max(1, int(round(sample_rate * duration_s)))
    white = rng.normal(0.0, 1.0, n)
    cutoff = min(220.0, sample_rate * 0.45)
    sos = butter(4, cutoff / (sample_rate / 2.0), btype="low", output="sos")
    shaped = sosfiltfilt(sos, white)
    # Scale by RMS, not the peak, so one loud sample cannot bury the pass.
    y = shaped / (np.std(shaped) + 1e-12) * amplitude
    fade = min(n // 3, int(round(0.4 * sample_rate)))
    if fade > 1:
        ramp = np.linspace(0.0, 1.0, fade)
        y[:fade] *= ramp
        y[-fade:] *= ramp[::-1]
    return y


def _shaped_noise(
    sample_rate: float,
    duration_s: float,
    rng: np.random.Generator,
    low_hz: float,
    high_hz: float,
    attack_s: float,
    decay_s: float,
) -> np.ndarray:
    """Broadband burst. attack_s is the onset; decay_s is the fall after that."""
    n = max(8, int(round(sample_rate * duration_s)))
    noise = rng.normal(0.0, 1.0, n)
    nyquist = sample_rate / 2.0
    lo = max(low_hz / nyquist, 1e-3)
    hi = min(high_hz / nyquist, 0.95)
    if hi > lo + 0.02 and n >= 24:
        sos = butter(2, [lo, hi], btype="band", output="sos")
        noise = sosfilt(sos, noise)
    time = np.arange(n, dtype=np.float64) / sample_rate
    envelope = np.ones(n, dtype=np.float64)
    attack_n = min(n, max(1, int(round(attack_s * sample_rate))))
    envelope[:attack_n] = np.linspace(0.0, 1.0, attack_n)
    envelope *= np.exp(-np.maximum(0.0, time - attack_s) / max(decay_s, 1e-4))
    shaped = noise * envelope
    peak = np.max(np.abs(shaped)) + 1e-12
    return shaped / peak


def render_bass_spawning_splash(
    sample_rate: float,
    rng: np.random.Generator,
    duration_s: float = BASS_BOUT_DURATION_S,
) -> np.ndarray:
    """One rock-fight bout: a handful of sharp surface splashes.

    Each splash lasts a few tens of milliseconds, the onset is a couple of
    milliseconds, and the gaps inside the bout are a few tenths of a second.
    The envelope returns to the floor between splashes. There is no engine
    tonal and the bout itself is only a few seconds long.
    """
    n = int(round(sample_rate * duration_s))
    y = np.zeros(n, dtype=np.float64)
    gaps = rng.uniform(0.22, 0.38, BASS_BURSTS)
    times = np.cumsum(gaps)
    span = float(times[-1] - times[0])
    usable = max(0.2, duration_s - 0.35)
    if span > 0:
        times = 0.08 + (times - times[0]) / span * usable
    high_hz = min(2200.0, sample_rate * 0.45)
    for splash_time in times:
        pulse = _shaped_noise(
            sample_rate,
            duration_s=float(rng.uniform(0.045, 0.07)),
            rng=rng,
            low_hz=300.0,
            high_hz=high_hz,
            attack_s=0.002,
            decay_s=0.02,
        )
        pulse = pulse * float(rng.uniform(0.75, 1.0))
        _mix(y, pulse, 0.0, float(splash_time), sample_rate)
    peak = np.max(np.abs(y)) + 1e-12
    return y / peak * 0.8


def render_rain(
    sample_rate: float,
    duration_s: float,
    rng: np.random.Generator,
    rate_hz: float = 16.0,
    amplitude: float = 0.045,
) -> np.ndarray:
    """Rain on the surface: small, similar drops spread across the whole interval.

    Drops are shorter and much more evenly distributed than a spawning bout,
    so the envelope never gathers into one short cluster and then goes quiet.
    """
    n = max(1, int(round(sample_rate * duration_s)))
    y = np.zeros(n, dtype=np.float64)
    n_drops = max(1, int(round(duration_s * rate_hz)))
    times = np.sort(rng.uniform(0.0, max(duration_s - 0.01, 0.0), n_drops))
    high_hz = min(3200.0, sample_rate * 0.48)
    for drop_time in times:
        pulse = _shaped_noise(
            sample_rate,
            duration_s=float(rng.uniform(0.004, 0.008)),
            rng=rng,
            low_hz=700.0,
            high_hz=high_hz,
            attack_s=0.001,
            decay_s=0.002,
        )
        _mix(y, pulse * amplitude, 0.0, float(drop_time), sample_rate)
    return y


def _render_engine(
    sample_rate: float,
    duration_s: float,
    rng: np.random.Generator,
    fundamental_hz: float,
) -> np.ndarray:
    """Low-frequency engine tonal plus rumble, sustained for many seconds."""
    n = max(1, int(round(sample_rate * duration_s)))
    time = np.arange(n, dtype=np.float64) / sample_rate
    tonal = (
        np.sin(2.0 * np.pi * fundamental_hz * time)
        + 0.55 * np.sin(2.0 * np.pi * 2.0 * fundamental_hz * time)
        + 0.30 * np.sin(2.0 * np.pi * 3.0 * fundamental_hz * time)
    )
    tonal = tonal / (np.max(np.abs(tonal)) + 1e-12) * 0.16
    white = rng.normal(0.0, 1.0, n)
    cutoff = min(160.0, sample_rate * 0.4)
    sos = butter(3, cutoff / (sample_rate / 2.0), btype="low", output="sos")
    rumble = sosfiltfilt(sos, white)
    rumble = rumble / (np.std(rumble) + 1e-12) * 0.06
    swell = np.linspace(0.35, 1.0, n)
    return (tonal + rumble) * swell


def _render_wake_wash(
    sample_rate: float, duration_s: float, rng: np.random.Generator
) -> np.ndarray:
    """Sustained wake wash with a few slow slaps, not isolated sharp splashes.

    The wash stays up for seconds. Each slap takes tens of milliseconds to
    rise and lasts a few tenths of a second, and it sits on top of energy
    that does not fall back to the noise floor between slaps.
    """
    n = max(1, int(round(sample_rate * duration_s)))
    white = rng.normal(0.0, 1.0, n)
    high_hz = min(1400.0, sample_rate * 0.45)
    sos = butter(
        3,
        [40.0 / (sample_rate / 2.0), high_hz / (sample_rate / 2.0)],
        btype="band",
        output="sos",
    )
    wash = sosfiltfilt(sos, white)
    wash = wash / (np.std(wash) + 1e-12) * 0.1
    fade = min(n // 4, int(round(0.25 * sample_rate)))
    if fade > 1:
        ramp = np.linspace(0.0, 1.0, fade)
        wash[:fade] *= ramp
        wash[-fade:] *= ramp[::-1]
    y = wash
    slap_times = np.arange(0.45, duration_s - 0.3, 0.55)
    for slap_time in slap_times:
        slap = _shaped_noise(
            sample_rate,
            duration_s=0.32,
            rng=rng,
            low_hz=80.0,
            high_hz=high_hz,
            attack_s=0.05,
            decay_s=0.1,
        )
        _mix(y, slap * 0.55, 0.0, float(slap_time), sample_rate)
    return y


def render_stop_start_wake(
    sample_rate: float,
    duration_s: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Boat wake that stops and starts over tens of seconds.

    Each on-period is engine rumble for several seconds, then a wake wash.
    The quiet gaps between on-periods are also several seconds. That is the
    opposite of a spawning bout, whose splashes are short and whose quiet
    gaps inside the bout are fractions of a second.
    """
    n = max(1, int(round(sample_rate * duration_s)))
    y = np.zeros(n, dtype=np.float64)
    cursor = 0.5
    fundamental = float(rng.uniform(48.0, 85.0))
    while cursor + 14.0 < duration_s:
        engine_s = 8.0
        wake_s = 4.5
        gap_s = 6.0
        engine = _render_engine(sample_rate, engine_s, rng, fundamental)
        _mix(y, engine, 0.0, cursor, sample_rate)
        wake = _render_wake_wash(sample_rate, wake_s, rng)
        # The slap arrives while the engine is still running.
        _mix(y, wake, 0.0, cursor + engine_s - 1.0, sample_rate)
        cursor += engine_s + wake_s + gap_s
    return y.astype(np.float32)


def background(
    n: int,
    sample_rate: float,
    rng: np.random.Generator,
    t_origin: float,
    hum: bool = True,
    ambient_boat: bool = True,
    rain: bool = False,
) -> np.ndarray:
    """Quiet river bed: pink-ish noise, distant boat rumble, mains hum."""
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    white = rng.normal(0.0, 1.0, n)
    # Leaky integration approximates a red/pink slope without a huge FFT.
    integrated = np.cumsum(white)
    integrated = integrated - np.mean(integrated)
    integrated = integrated / (np.std(integrated) + 1e-12) * 0.012
    white = white / (np.std(white) + 1e-12) * 0.006
    y = integrated + white
    if ambient_boat and n > int(sample_rate * 0.05):
        cutoff = min(180.0, sample_rate * 0.4)
        sos = butter(3, cutoff / (sample_rate / 2.0), btype="low", output="sos")
        rumble = sosfiltfilt(sos, rng.normal(0.0, 1.0, n))
        rumble = rumble / (np.std(rumble) + 1e-12) * 0.02
        t = t_origin + np.arange(n, dtype=np.float64) / sample_rate
        rumble = rumble * (0.75 + 0.25 * np.sin(2.0 * np.pi * 0.07 * t))
        y = y + rumble
    if hum:
        t = t_origin + np.arange(n, dtype=np.float64) / sample_rate
        y = y + 0.015 * np.sin(2.0 * np.pi * 60.0 * t)
        y = y + 0.005 * np.sin(2.0 * np.pi * 120.0 * t)
    if rain and n > 0:
        y = y + render_rain(sample_rate, n / sample_rate, rng)
    return y


def render_call(
    kind: str,
    sample_rate: float,
    rng: np.random.Generator,
    duration_s: float | None = None,
) -> np.ndarray:
    if kind == "sturgeon_thunder":
        return render_sturgeon_thunder(sample_rate)
    if kind == "drum_knock":
        return render_drum_knocks(sample_rate)
    if kind == "toadfish_boatwhistle":
        return render_toadfish_boatwhistle(sample_rate)
    if kind == "boat":
        return render_boat_pass(sample_rate, duration_s or BOAT_PASS_DURATION_S, rng)
    if kind == "bass_spawning_splash":
        return render_bass_spawning_splash(
            sample_rate, rng, duration_s or BASS_BOUT_DURATION_S
        )
    if kind == "rain":
        return render_rain(sample_rate, duration_s or 10.0, rng)
    if kind == "stop_start_wake":
        return render_stop_start_wake(sample_rate, duration_s or 48.0, rng)
    raise ValueError(f"unknown call kind: {kind}")


def pattern_events(segment_seconds: float) -> list[SynthEvent]:
    """Place one of each template inside a segment, scaled if it is short."""
    scale = segment_seconds / 60.0
    events = [
        SynthEvent("sturgeon_thunder", 8.0 * scale, STURGEON_DURATION_S),
        SynthEvent("drum_knock", 20.0 * scale, DRUM_DURATION_S),
        SynthEvent("bass_spawning_splash", 26.0 * scale, BASS_BOUT_DURATION_S),
        SynthEvent("toadfish_boatwhistle", 35.0 * scale, TOADFISH_DURATION_S),
        SynthEvent("boat", 45.0 * scale, BOAT_PASS_DURATION_S),
    ]
    kept: list[SynthEvent] = []
    for event in events:
        if event.start_s + 0.2 < segment_seconds and event.start_s >= 0:
            kept.append(event)
    return kept


def events_overlapping(
    t0: float, t1: float, segment_seconds: float
) -> list[SynthEvent]:
    if segment_seconds <= 0:
        return []
    first = int(np.floor(t0 / segment_seconds))
    last = int(np.floor(max(t0, t1 - 1e-9) / segment_seconds))
    found: list[SynthEvent] = []
    for index in range(first, last + 1):
        base = index * segment_seconds
        for event in pattern_events(segment_seconds):
            start = base + event.start_s
            end = start + event.duration_s
            if end > t0 and start < t1:
                found.append(SynthEvent(event.kind, start, event.duration_s))
    return found


def _mix(
    destination: np.ndarray,
    signal: np.ndarray,
    dest_t0: float,
    signal_t0: float,
    sample_rate: float,
) -> None:
    if signal.size == 0 or destination.size == 0:
        return
    dest_t1 = dest_t0 + destination.size / sample_rate
    signal_t1 = signal_t0 + signal.size / sample_rate
    left = max(dest_t0, signal_t0)
    right = min(dest_t1, signal_t1)
    if right <= left:
        return
    n = int(round((right - left) * sample_rate))
    if n <= 0:
        return
    dest_at = int(round((left - dest_t0) * sample_rate))
    src_at = int(round((left - signal_t0) * sample_rate))
    dest_at = min(max(dest_at, 0), destination.size)
    src_at = min(max(src_at, 0), signal.size)
    n = min(n, destination.size - dest_at, signal.size - src_at)
    if n <= 0:
        return
    destination[dest_at : dest_at + n] += signal[src_at : src_at + n]


def render_interval(
    t0: float,
    t1: float,
    sample_rate: float,
    segment_seconds: float,
    seed: int,
    hum: bool = True,
    ambient_boat: bool = True,
    calls: bool = True,
    rain: bool = False,
) -> np.ndarray:
    """Render [t0, t1) seconds of the synthetic soundscape."""
    n = int(round((t1 - t0) * sample_rate))
    rng = np.random.default_rng(
        [int(seed) & 0xFFFFFFFF, int(round(t0 * 1000.0)) & 0xFFFFFFFF]
    )
    y = background(
        n,
        sample_rate,
        rng,
        t_origin=t0,
        hum=hum,
        ambient_boat=ambient_boat,
        rain=rain,
    )
    if not calls:
        return y.astype(np.float32, copy=False)
    for event in events_overlapping(t0, t1, segment_seconds):
        signal = render_call(event.kind, sample_rate, rng, event.duration_s)
        _mix(y, signal, t0, event.start_s, sample_rate)
    return y.astype(np.float32)


def render_scene(
    sample_rate: float,
    duration_s: float,
    events: list[SynthEvent],
    seed: int = 1,
    hum: bool = True,
    ambient_boat: bool = True,
    rain: bool = False,
) -> np.ndarray:
    """Render an explicit list of calls. Used by detector tests."""
    n = int(round(duration_s * sample_rate))
    rng = np.random.default_rng(seed)
    y = background(
        n,
        sample_rate,
        rng,
        t_origin=0.0,
        hum=hum,
        ambient_boat=ambient_boat,
        rain=rain,
    )
    for event in events:
        signal = render_call(event.kind, sample_rate, rng, event.duration_s)
        _mix(y, signal, 0.0, event.start_s, sample_rate)
    return y.astype(np.float32)
