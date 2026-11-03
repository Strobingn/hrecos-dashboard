import numpy as np

from hydrophone_node.audio.features import band_levels
from hydrophone_node.audio.synthesize import (
    DRUM_DURATION_S,
    DRUM_KNOCKS,
    STURGEON_DURATION_S,
    SynthEvent,
    render_drum_knocks,
    render_scene,
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
