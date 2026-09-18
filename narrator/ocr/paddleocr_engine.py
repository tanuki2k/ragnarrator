"""PaddleOCR-backed OCR engine.

Optional alternative to EasyOCR - try this for a game whose stylized font
EasyOCR reads poorly. Not installed by default; `pip install paddlepaddle-gpu
paddleocr` to use it (see README).
"""
from __future__ import annotations

import numpy as np
from PIL import Image


class PaddleOCREngine:
    def __init__(self, lang: str = "en", use_gpu: bool = True) -> None:
        from paddleocr import PaddleOCR  # deferred: optional dependency

        self._ocr = PaddleOCR(lang=lang, use_angle_cls=False, show_log=False)

    def read_text(self, image: Image.Image) -> str:
        result = self._ocr.ocr(np.array(image), cls=False)
        if not result or not result[0]:
            return ""
        lines = [line[1][0] for line in result[0]]
        return "\n".join(line.strip() for line in lines if line.strip())
