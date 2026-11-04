import numpy as np

from hydrophone_node.audio.features import band_levels
from hydrophone_node.audio.synthesize import (
    BASS_BOUT_DURATION_S,
    DRUM_DURATION_S,
    DRUM_KNOCKS,
    STURGEON_DURATION_S,
    SynthEvent,
    render_bass_spawning_splash,
    render_drum_knocks,
    render_rain,
    render_scene,
    render_stop_start_wake,
    render_sturgeon_thunder,
    render_toadfish_boatwhistle,
)


def _peak_hz(samples, sample_rate, low, high):
    spec = np.abs(np.fft.rfft(samples * np.hanning(samples.size)))
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / sample_rate)
    mask = (freqs >= low) & (freqs <= high)
    return float(freqs[mask][np.argmax(spec[mask])])


def test_sturgeon_template_peaks_near_44_hz():
    sample_rate = 8000
    call = render_sturgeon_thunder(sample_rate)
    assert abs(call.size / sample_rate - STURGEON_DURATION_S) < 0.02
    assert 35 <= _peak_hz(call, sample_rate, 10, 100) <= 55
    levels = band_levels(call, sample_rate)
    assert levels["10-100"] > levels["100-500"]


def test_drum_template_is_a_400_hz_knock_train():
    sample_rate = 8000
    call = render_drum_knocks(sample_rate)
    assert abs(call.size / sample_rate - DRUM_DURATION_S) < 0.02
    assert 370 <= _peak_hz(call, sample_rate, 200, 800) <= 430
    # 25 knocks show up as 25 envelope peaks.
    envelope = np.convolve(np.abs(call), np.ones(8) / 8, mode="same")
    from scipy.signal import find_peaks

    peaks, _ = find_peaks(
        envelope, height=np.max(envelope) * 0.2, distance=int(0.02 * sample_rate)
    )
    assert abs(len(peaks) - DRUM_KNOCKS) <= 2


def test_toadfish_template_peaks_at_the_fundamental():
    sample_rate = 8000
    call = render_toadfish_boatwhistle(sample_rate)
    assert 170 <= _peak_hz(call, sample_rate, 80, 800) <= 230


def test_bass_bout_is_a_short_broadband_cluster():
    sample_rate = 8000
    rng = np.random.default_rng(1)
    call = render_bass_spawning_splash(sample_rate, rng)
    assert abs(call.size / sample_rate - BASS_BOUT_DURATION_S) < 0.05
    levels = band_levels(call, sample_rate)
    # Surface splashes are not a low-frequency rumble.
    assert levels["500-2000"] > levels["10-100"] - 6
    envelope = np.convolve(np.abs(call), np.ones(16) / 16, mode="same")
    from scipy.signal import find_peaks

    peaks, _ = find_peaks(
        envelope, height=np.max(envelope) * 0.25, distance=int(0.1 * sample_rate)
    )
    assert 5 <= len(peaks) <= 10
    # Gaps inside the bout are fractions of a second, and the bout is short.
    gaps = np.diff(peaks) / sample_rate
    assert np.median(gaps) < 0.6
    assert peaks[-1] / sample_rate < BASS_BOUT_DURATION_S


def test_rain_drops_are_smaller_and_more_spread_than_a_bout():
    sample_rate = 8000
    rng = np.random.default_rng(2)
    rain = render_rain(sample_rate, 10.0, rng)
    bass = render_bass_spawning_splash(sample_rate, rng)
    assert np.max(np.abs(rain)) < np.max(np.abs(bass)) * 0.5


def test_stop_start_wake_has_long_on_periods():
    sample_rate = 8000
    wake = render_stop_start_wake(sample_rate, 48.0, np.random.default_rng(3))
    assert abs(wake.size / sample_rate - 48.0) < 0.05
    frame = int(0.5 * sample_rate)
    hops = range(0, wake.size - frame, frame)
    loud = []
    for start in hops:
        loud.append(float(np.sqrt(np.mean(wake[start : start + frame] ** 2))) > 0.04)
    # At least one run of elevated energy lasts many seconds, not a 2 s bout.
    longest = 0
    run = 0
    for flag in loud:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    assert longest >= 6


def test_scene_mixes_calls_into_hum_and_boat_noise():
    sample_rate = 8000
    scene = render_scene(
        sample_rate,
        10.0,
        [SynthEvent("sturgeon_thunder", 2.0, 1.9)],
        seed=4,
    )
    quiet = render_scene(sample_rate, 10.0, [], seed=4)
    assert scene.shape == quiet.shape
    # The call makes the scene louder than hum and rumble alone.
    assert np.sqrt(np.mean(scene**2)) > np.sqrt(np.mean(quiet**2)) * 1.5
    # 60 Hz hum is in the background even with no calls.
    spec = np.abs(np.fft.rfft(quiet))
    freqs = np.fft.rfftfreq(quiet.size, d=1.0 / sample_rate)
    hum_bin = np.argmin(np.abs(freqs - 60))
    neighbors = np.median(spec[max(0, hum_bin - 20) : hum_bin + 20])
    assert spec[hum_bin] > neighbors * 5
