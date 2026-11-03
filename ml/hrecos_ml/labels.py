"""Class names, species identifiers, and literature frequency bounds.

Detection labels are the values stored on a detections row. Training also uses
``train``, ``hum_60hz``, ``rain``, ``wave_slap``, and ``background``. Those
collapse to ``unknown`` at inference time, except plain background, which is
not emitted. ``bass_spawning_splash`` is kept and stored as species
``striped_bass``.
"""

from __future__ import annotations

DETECTION_LABELS = (
    "sturgeon_thunder",
    "drum_knock",
    "toadfish_boatwhistle",
    "bass_spawning_splash",
    "boat",
    "unknown",
)

TRAIN_LABELS = (
    "sturgeon_thunder",
    "drum_knock",
    "toadfish_boatwhistle",
    "bass_spawning_splash",
    "boat",
    "train",
    "hum_60hz",
    "rain",
    "wave_slap",
    "background",
)

# Train-time label -> detections.label
INFERENCE_LABEL = {
    "sturgeon_thunder": "sturgeon_thunder",
    "drum_knock": "drum_knock",
    "toadfish_boatwhistle": "toadfish_boatwhistle",
    "bass_spawning_splash": "bass_spawning_splash",
    "boat": "boat",
    "train": "unknown",
    "hum_60hz": "unknown",
    "rain": "unknown",
    "wave_slap": "unknown",
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
    "bass_spawning_splash": {
        "species_id": "striped_bass",
        "scientific_name": "Morone saxatilis",
        "common_name": "striped bass",
        "freq_low_hz": 100.0,
        "freq_high_hz": 8000.0,
        "peak_hz": None,
        "citation": (
            "Surface spawning behavior: Setzler et al. 1980, NOAA Tech. Rep. NMFS Circ. 433. "
            "No published spectrum of the Hudson splash itself; shape follows Franz 1959, JASA 31:1080."
        ),
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
    "rain": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "rain",
        "freq_low_hz": 1000.0,
        "freq_high_hz": 16000.0,
        "peak_hz": 15000.0,
        "citation": "Nystuen 1986, JASA 79:972; Medwin et al. 1992, JASA 92:1613.",
    },
    "wave_slap": {
        "species_id": None,
        "scientific_name": None,
        "common_name": "wave slap",
        "freq_low_hz": 40.0,
        "freq_high_hz": 800.0,
        "peak_hz": None,
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
MODEL_VERSION = "0.2.0"

TARGET_SR = 32_000
WINDOW_S = 5.0
WINDOW_SAMPLES = TARGET_SR * 5  # 160_000, Perch / SurfPerch contract
DEFAULT_HOP_S = 1.0
DEFAULT_THRESHOLD = 0.5
