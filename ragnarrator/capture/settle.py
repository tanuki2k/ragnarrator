"""Frame-change and text-settle detection.

Screenshotting is cheap; OCR is not. This module compares each captured
frame to the previous one and only signals "ready for OCR" once the region
has stopped changing for a short window. That's what prevents narrating
dialogue mid-typewriter-effect, and what avoids running OCR on every frame.

Frames are compared by mean absolute pixel difference on a downsampled
grayscale copy, not exact equality: some games render with a per-frame
dithering/grain effect, so two screenshots of visually-identical content can
still differ at the byte level. An exact hash would never match in that
case and OCR would never trigger; a small tolerance absorbs that noise while
staying sensitive to real text changes (see git history for the measured
noise floor this default was calibrated against).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image


def _downsample(image: Image.Image) -> np.ndarray:
    small = image.resize((64, 24)).convert("L")
    return np.asarray(small, dtype=np.int16)


@dataclass
class SettleDetector:
    """Tracks recent frames and reports when the region has stabilized."""

    settle_frames: int = 3
    diff_threshold: float = 2.0  # mean abs pixel diff (0-255 scale) treated as "unchanged"
    _prev: np.ndarray | None = field(default=None, init=False, repr=False)
    _stable_count: int = field(default=0, init=False, repr=False)
    _reported: bool = field(default=False, init=False, repr=False)

    def observe(self, image: Image.Image) -> bool:
        """Feed a new frame. Returns True exactly once per settle event: when
        `settle_frames` consecutive frames have been within `diff_threshold`
        of each other and this is the first observation of that stable run
        (not a repeat report)."""
        current = _downsample(image)

        if self._prev is None:
            self._stable_count = 0
        else:
            diff = float(np.abs(current.astype(np.int32) - self._prev.astype(np.int32)).mean())
            if diff <= self.diff_threshold:
                self._stable_count += 1
            else:
                self._stable_count = 0
                self._reported = False

        self._prev = current

        if self._stable_count >= self.settle_frames and not self._reported:
            self._reported = True
            return True
        return False

    def reset(self) -> None:
        self._prev = None
        self._stable_count = 0
        self._reported = False
