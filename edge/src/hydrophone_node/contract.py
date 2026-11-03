"""Column names shared with the Supabase migrations.

Another agent owns the migrations. These strings are the on-the-wire contract
for hydrophone_nodes, audio_segments, and detections, plus the Storage bucket
that holds WAV segments and clips.
"""

AUDIO_BUCKET = "audio"

NODE_STATUSES = ("online", "offline", "simulated")

SIMULATED_NODE_IDS = ("westpoint-cornwall", "poughkeepsie", "tappan-zee")

BAND_LEVEL_KEYS = ("10-100", "100-500", "500-2000")

DETECTION_LABELS = (
    "sturgeon_thunder",
    "drum_knock",
    "toadfish_boatwhistle",
    "boat",
    "unknown",
)

SPECIES_IDS = (
    "atlantic_sturgeon",
    "freshwater_drum",
    "oyster_toadfish",
)

LABEL_SPECIES = {
    "sturgeon_thunder": "atlantic_sturgeon",
    "drum_knock": "freshwater_drum",
    "toadfish_boatwhistle": "oyster_toadfish",
    "boat": None,
    "unknown": None,
}

REVIEW_STATUS_DEFAULT = "unreviewed"

NODE_COLUMNS = (
    "id",
    "name",
    "lat",
    "lon",
    "river_mile",
    "hardware",
    "sample_rate_hz",
    "status",
    "last_heartbeat",
)

SEGMENT_COLUMNS = (
    "id",
    "node_id",
    "start_time",
    "end_time",
    "storage_path",
    "rms_db",
    "band_levels",
)

DETECTION_COLUMNS = (
    "id",
    "node_id",
    "segment_id",
    "start_time",
    "end_time",
    "label",
    "species_id",
    "confidence",
    "model_name",
    "model_version",
    "freq_low_hz",
    "freq_high_hz",
    "clip_path",
    "review_status",
)

# Approximate channel positions, river miles counted from The Battery.
NODE_PRESETS = {
    "westpoint-cornwall": {
        "name": "West Point-Cornwall",
        "lat": 41.3865,
        "lon": -73.9550,
        "river_mile": 52.5,
    },
    "poughkeepsie": {
        "name": "Poughkeepsie",
        "lat": 41.7066,
        "lon": -73.9380,
        "river_mile": 75.6,
    },
    "tappan-zee": {
        "name": "Tappan Zee",
        "lat": 41.0715,
        "lon": -73.8905,
        "river_mile": 27.4,
    },
}

DEFAULT_HARDWARE = "Aquarian H2a hydrophone + Raspberry Pi (simulated)"
