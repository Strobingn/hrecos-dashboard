"""Build a detector from config. ML models plug in through an entrypoint."""

from __future__ import annotations

import importlib
from typing import Any

from hydrophone_node.detect.band_energy import BandEnergyDetector
from hydrophone_node.detect.base import Detector


def load_entrypoint(entrypoint: str) -> Detector:
    """Load ``package.module:attribute`` and return a Detector.

    The attribute may be a Detector instance, a zero-arg factory, or a class.
    """
    module_name, separator, attribute = entrypoint.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError(
            "detector entrypoint must look like 'package.module:build_detector'"
        )
    module = importlib.import_module(module_name)
    obj: Any = module
    for part in attribute.split("."):
        obj = getattr(obj, part)
    detector = obj() if isinstance(obj, type) else obj() if callable(obj) else obj
    if not hasattr(detector, "detect"):
        raise TypeError(f"{entrypoint} did not produce a detector")
    return detector


def build_detector(name: str, entrypoint: str | None = None) -> Detector:
    if name in ("band_energy", "", None):
        return BandEnergyDetector()
    if name == "ml":
        if not entrypoint:
            raise ValueError("detector.name is 'ml' but detector.entrypoint is empty")
        return load_entrypoint(entrypoint)
    raise ValueError(
        f"unknown detector '{name}'. Use 'band_energy' or 'ml' with an entrypoint."
    )
