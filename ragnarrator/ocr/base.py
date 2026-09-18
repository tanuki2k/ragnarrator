"""OCR engine interface."""
from __future__ import annotations

from typing import Protocol

from PIL import Image


class OCREngine(Protocol):
    def read_text(self, image: Image.Image) -> str:
        """Return the text detected in `image`, reading order preserved,
        lines joined with '\\n'. Return "" if nothing is detected."""
        ...
