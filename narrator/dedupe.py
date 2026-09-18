"""Fuzzy text-stabilization: decide whether newly OCR'd text is worth
speaking, filtering out OCR noise and near-duplicates of what was just said.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz


@dataclass
class Deduper:
    similarity_threshold: float = 92.0
    min_chars: int = 2
    _last_spoken: str = field(default="", init=False, repr=False)

    def should_speak(self, text: str) -> bool:
        text = text.strip()
        if len(text) < self.min_chars:
            return False
        if not self._last_spoken:
            return True
        return fuzz.ratio(text, self._last_spoken) < self.similarity_threshold

    def mark_spoken(self, text: str) -> None:
        self._last_spoken = text.strip()
