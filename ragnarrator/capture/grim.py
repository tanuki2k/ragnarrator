"""Screenshot capture via grim (the wlr-screencopy CLI)."""
from __future__ import annotations

import subprocess
from io import BytesIO

from PIL import Image


class GrimError(RuntimeError):
    pass


def capture_region(geometry: str) -> Image.Image:
    """Capture a screen region as a PIL Image.

    `geometry` is a grim-style "X,Y WxH" string, e.g. "100,200 640x180",
    as produced by `select_region()`.
    """
    try:
        proc = subprocess.run(
            ["grim", "-g", geometry, "-t", "png", "-"],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        raise GrimError("grim is not installed (pacman -S grim)") from exc
    except subprocess.CalledProcessError as exc:
        raise GrimError(f"grim failed: {exc.stderr.decode(errors='replace')}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GrimError("grim timed out") from exc

    return Image.open(BytesIO(proc.stdout)).convert("RGB")
