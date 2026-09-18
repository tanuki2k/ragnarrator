"""Frame-change and text-settle detection.

Screenshotting is cheap; OCR is not. This module hashes each captured frame
and only signals "ready for OCR" once the frame has stopped changing for a
short window. That's what prevents narrating dialogue mid-typewriter-effect,
and what avoids running OCR on every single frame.
"""
from __future__ import annotations

import hashlib
from collections import deque
from dataclasses import dataclass, field

from PIL import Image


def _frame_hash(image: Image.Image) -> str:
    # Downscale + grayscale before hashing so the hash tolerates the kind of
    # single-pixel encoding noise that can differ between two screenshots of
    # an otherwise-unchanged frame, while staying sensitive to real text changes.
    small = image.resize((64, 24)).convert("L")
    return hashlib.blake2b(small.tobytes(), digest_size=16).hexdigest()


@dataclass
class SettleDetector:
    """Tracks recent frame hashes and reports when the region has stabilized."""

    settle_frames: int = 3
    _recent: deque[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._recent: deque[str] = deque(maxlen=self.settle_frames)

    def observe(self, image: Image.Image) -> bool:
        """Feed a new frame. Returns True exactly once per settle event: when
        the last `settle_frames` frames are identical and this is the first
        observation of that stable state (not a repeat report)."""
        was_settled = self._is_settled()
        self._recent.append(_frame_hash(image))
        is_settled = self._is_settled()
        return is_settled and not was_settled

    def _is_settled(self) -> bool:
        return len(self._recent) == self._recent.maxlen and len(set(self._recent)) == 1

    def reset(self) -> None:
        self._recent.clear()
