"""Class names, species identifiers, and literature frequency bounds.

Detection labels are the values stored on a detections row. Training uses two
extra noise classes (``train``, ``hum_60hz``) plus ``background``. Those three
collapse to ``unknown`` at inference time, and plain background is not emitted.
"""

from __future__ import annotations

DETECTION_LABELS = (
    "sturgeon_thunder",
    "drum_knock",
    "toadfish_boatwhistle",
    "boat",
    "unknown",
)

TRAIN_LABELS = (
    "sturgeon_thunder",
    "drum_knock",
    "toadfish_boatwhistle",
    "boat",
    "train",
    "hum_60hz",
    "background",
)

# Train-time label -> detections.label
INFERENCE_LABEL = {
    "sturgeon_thunder": "sturgeon_thunder",
    "drum_knock": "drum_knock",
    "toadfish_boatwhistle": "toadfish_boatwhistle",
    "boat": "boat",
    "train": "unknown",
    "hum_60hz": "unknown",
    "background": "unknown",
}

# Background is the negative class. It is not written as a detection.
EMITTED_TRAIN_LABELS = tuple(label for label in TRAIN_LABELS if label != "background")

# species_id is public.species.id from supabase/seed.sql, not an ITIS number.
SPECIES = {
    "sturgeon_thunder": {
        "species_id": "atlantic_sturgeon",
        "scientific_name": "Acipenser oxyrinchus",
        "common_name": "Atlantic sturgeon",
        "freq_low_hz": 10.0,
        "freq_high_hz": 100.0,
        "peak_hz": 44.0,
        "citation": "Cohen et al. 2025, Endang. Species Res., doi:10.3354/esr01429",
    },
    "drum_knock": {
        "species_id": "freshwater_drum",
        "scientific_name": "Aplodinotus grunniens",
        "common_name": "freshwater drum",
        "freq_low_hz": 150.0,
        "freq_high_hz": 800.0,
        "peak_hz": 400.0,
        "citation": "Knock trains centered near 400 Hz; Rountree recordings in FishSounds (doi:10.5683/SP2/TACOUX).",
    },
    "toadfish_boatwhistle": {
        "species_id": "oyster_toadfish",
        "scientific_name": "Opsanus tau",
        "common_name": "oyster toadfish",
        "freq_low_hz": 80.0,
        "freq_high_hz": 800.0,
        "peak_hz": 200.0,
        "citation": "Tonal boatwhistle; fundamental typically well below 300 Hz with harmonics.",
    },
    "boat": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "vessel",
        "freq_low_hz": 20.0,
        "freq_high_hz": 2000.0,
        "peak_hz": None,
        "citation": None,
    },
    "train": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "train",
        "freq_low_hz": 20.0,
        "freq_high_hz": 2000.0,
        "peak_hz": None,
        "citation": None,
    },
    "hum_60hz": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "electrical hum",
        "freq_low_hz": 50.0,
        "freq_high_hz": 360.0,
        "peak_hz": 60.0,
        "citation": None,
    },
    "background": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "background",
        "freq_low_hz": None,
        "freq_high_hz": None,
        "peak_hz": None,
        "citation": None,
    },
    "unknown": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "unknown",
        "freq_low_hz": None,
        "freq_high_hz": None,
        "peak_hz": None,
        "citation": None,
    },
}

MODEL_NAME = "hrecos-fish-probe"
MODEL_VERSION = "0.1.0"

TARGET_SR = 32_000
WINDOW_S = 5.0
WINDOW_SAMPLES = TARGET_SR * 5  # 160_000, Perch / SurfPerch contract
DEFAULT_HOP_S = 1.0
DEFAULT_THRESHOLD = 0.5
