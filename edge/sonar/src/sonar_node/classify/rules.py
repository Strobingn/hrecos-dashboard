"""Length and behavior rules.

Scores are ranks in [0, 1], not calibrated probabilities. The cuts sit on the
same envelopes the simulator draws, so a high score on synthetic data is the
generator recognizing its own rules wherever the envelopes do not overlap.
Overlap cases (large bass versus small sturgeon, shad versus bass, herring
versus small bass) are left uncertain on purpose.
"""

from __future__ import annotations

from sonar_node.classify.base import Classification
from sonar_node.simulate import SimulatedTrack

MODEL_NAME = "length_behavior_rules"
MODEL_VERSION = "0.1.0"


class RulesClassifier:
    model_name = MODEL_NAME
    model_version = MODEL_VERSION

    def classify(self, track: SimulatedTrack) -> Classification:
        species, confidence = decide(
            length_cm=track.length_cm,
            depth_m=track.depth_m,
            behavior=track.behavior,
            cluster_size=track.cluster_size,
            near_surface=track.near_surface,
        )
        return Classification(
            species_id=species,
            confidence=confidence,
            model_name=self.model_name,
            model_version=self.model_version,
        )

    def classify_frames(self, frames) -> Classification:
        raise NotImplementedError(
            "length_behavior_rules does not read ARIS frames. "
            "Plug in a FrameClassifier through detector name 'ml' when a "
            "model trained on real frames exists. Expected shape is "
            "(n_frames, height, width)."
        )


def decide(
    length_cm: float,
    depth_m: float,
    behavior: str,
    cluster_size: int,
    near_surface: bool,
) -> tuple[str | None, float]:
    surface_group = behavior == "surface_cluster" or (
        near_surface and cluster_size >= 3 and behavior != "school"
    )
    school = behavior == "school" and cluster_size >= 4
    deep = depth_m >= 2.5 and not surface_group

    if surface_group and 35.0 <= length_cm <= 130.0:
        confidence = 0.72 if length_cm >= 45.0 else 0.45
        return "striped_bass", confidence
    if length_cm >= 150.0 and not surface_group:
        return "atlantic_sturgeon", 0.84
    if length_cm >= 100.0 and deep and not school:
        # 100–140 cm is where a large bass and a small Atlantic sturgeon overlap,
        # and where shortnose sturgeon also sits. Keep the score modest.
        return "atlantic_sturgeon", 0.58 if length_cm < 140.0 else 0.78
    if school and 40.0 <= length_cm <= 65.0:
        return "american_shad", 0.62
    if school and 18.0 <= length_cm <= 38.0:
        return "river_herring", 0.66
    if 45.0 <= length_cm <= 120.0 and not school:
        return "striped_bass", 0.4
    if 18.0 <= length_cm < 40.0:
        return "river_herring", 0.34
    return None, 0.0
