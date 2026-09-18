"""Kokoro-82M local TTS wrapper. Local, open-weight (Apache-2.0), fast
enough for near-real-time use, GPU-accelerated via the user's CUDA device.
"""
from __future__ import annotations

import numpy as np


class KokoroEngine:
    def __init__(self, voice: str = "af_heart", speed: float = 1.0, lang_code: str = "a") -> None:
        from kokoro import KPipeline  # deferred: heavy import, loads model weights

        self.voice = voice
        self.speed = speed
        self._pipeline = KPipeline(lang_code=lang_code)

    def synthesize(self, text: str) -> tuple[np.ndarray, int]:
        """Returns (audio_samples, sample_rate)."""
        chunks = [audio for _, _, audio in self._pipeline(text, voice=self.voice, speed=self.speed)]
        if not chunks:
            return np.zeros(0, dtype=np.float32), 24000
        return np.concatenate(chunks), 24000
