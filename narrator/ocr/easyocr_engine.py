"""EasyOCR-backed OCR engine, CUDA-accelerated when available."""
from __future__ import annotations

import numpy as np
from PIL import Image


class EasyOCREngine:
    def __init__(self, languages: list[str] | None = None, gpu: bool = True) -> None:
        import easyocr  # deferred: heavy import, loads model weights on first use

        self._reader = easyocr.Reader(languages or ["en"], gpu=gpu)

    def read_text(self, image: Image.Image) -> str:
        lines = self._reader.readtext(np.array(image), detail=0, paragraph=True)
        return "\n".join(line.strip() for line in lines if line.strip())
