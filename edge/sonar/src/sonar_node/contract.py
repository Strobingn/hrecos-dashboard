"""Column names shared with the sonar migration and contracts/."""

from __future__ import annotations

SONAR_BUCKET = "sonar"

NODE_STATUSES = ("online", "offline", "simulated")

SEEDED_NODE_IDS = ("westpoint-cornwall",)

LATER_NODE_IDS = ("poughkeepsie", "tappan-zee")

DIRECTIONS = ("upstream", "downstream", "milling")

BEHAVIORS = ("surface_cluster", "school", "solitary", "unknown")

SPECIES_IDS = (
    "atlantic_sturgeon",
    "striped_bass",
    "river_herring",
    "american_shad",
)

REVIEW_STATUS_DEFAULT = "unreviewed"

# Length envelopes the simulator draws from. They are not the biological
# maximum. Atlantic sturgeon on the Hudson can be larger than 250 cm, and
# juveniles are smaller. See docs/sonar-track.md.
LENGTH_CM = {
    "striped_bass": (30.0, 120.0),
    "river_herring": (20.0, 35.0),
    "american_shad": (40.0, 60.0),
    "atlantic_sturgeon": (100.0, 250.0),
}

# Same coordinates as supabase/seed.sql hydrophone rows.
NODE_PRESETS = {
    "westpoint-cornwall": {
        "name": "West Point / Cornwall",
        "lat": 41.4150,
        "lon": -73.9600,
        "river_mile": 54.0,
    },
    "poughkeepsie": {
        "name": "Poughkeepsie",
        "lat": 41.7210,
        "lon": -73.9390,
        "river_mile": 75.0,
    },
    "tappan-zee": {
        "name": "Tappan Zee / Piermont",
        "lat": 41.0630,
        "lon": -73.8900,
        "river_mile": 26.0,
    },
}

DEFAULT_HARDWARE = (
    "Simulated ARIS Explorer-class imaging sonar (no instrument connected)"
)

NODE_COLUMNS = (
    "id",
    "name",
    "lat",
    "lon",
    "river_mile",
    "hardware",
    "status",
    "last_heartbeat",
)

TRACK_COLUMNS = (
    "id",
    "node_id",
    "start_time",
    "end_time",
    "direction",
    "length_cm",
    "depth_m",
    "range_m",
    "speed_mps",
    "species_id",
    "species_confidence",
    "model_name",
    "model_version",
    "review_status",
    "clip_path",
    "features",
)

SPLASH_LABEL = "bass_spawning_splash"
STRIPED_BASS_ID = "striped_bass"
