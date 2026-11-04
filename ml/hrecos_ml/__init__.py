"""Offline Hudson River fish-sound baseline.

The edge-facing entry point is :func:`hrecos_ml.detect`.
"""

from hrecos_ml.infer import detect, to_detection_rows

__all__ = ["detect", "to_detection_rows"]
