"""Pluggable detectors. The baseline is rule-based band energy."""

from hydrophone_node.detect.base import DetectionEvent, Detector
from hydrophone_node.detect.registry import build_detector

__all__ = ["DetectionEvent", "Detector", "build_detector"]
