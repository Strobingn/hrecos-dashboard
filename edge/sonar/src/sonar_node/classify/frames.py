"""Shape check for a future ARIS frame model. No weights, no predictions."""

from __future__ import annotations

import numpy as np


def require_frame_stack(frames: np.ndarray) -> None:
    """Acoustic frames are (n_frames, height, width), floating point, n >= 1."""
    array = np.asarray(frames)
    if array.ndim != 3:
        raise ValueError(
            "ARIS frames must have shape (n_frames, height, width); "
            f"got ndim {array.ndim}"
        )
    if array.shape[0] < 1 or array.shape[1] < 2 or array.shape[2] < 2:
        raise ValueError(f"ARIS frame stack is too small: {array.shape}")
    if not np.issubdtype(array.dtype, np.floating):
        raise ValueError("ARIS frames must be a floating-point array, not an encoded image")
