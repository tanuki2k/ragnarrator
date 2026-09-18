"""Interactive screen-region selection via slurp."""
from __future__ import annotations

import subprocess


class SlurpError(RuntimeError):
    pass


def select_region() -> str:
    """Run slurp so the user can drag-select a screen region.

    Returns a grim-compatible geometry string ("X,Y WxH").
    """
    try:
        proc = subprocess.run(["slurp"], capture_output=True, check=True, timeout=60)
    except FileNotFoundError as exc:
        raise SlurpError("slurp is not installed (pacman -S slurp)") from exc
    except subprocess.CalledProcessError as exc:
        # slurp exits non-zero if the user cancels (Esc)
        raise SlurpError("region selection cancelled") from exc
    except subprocess.TimeoutExpired as exc:
        raise SlurpError("region selection timed out") from exc

    return proc.stdout.decode().strip()
