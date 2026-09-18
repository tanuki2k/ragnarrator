"""Query niri's window/focus state via `niri msg -j windows`.

Used to identify which game window is focused so the right per-game profile
(capture region, voice, etc.) can be loaded automatically.

Note: this deliberately does not attempt to derive absolute screen geometry
from niri's window layout, since niri is a scrollable-tiling compositor and a
window's on-screen position can change as the user scrolls. Capture regions
are stored as absolute screen coordinates (see profiles/profile.py) and
should be re-selected if a game window moves.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


class NiriIPCError(RuntimeError):
    pass


@dataclass(frozen=True)
class NiriWindow:
    id: int
    app_id: str | None
    title: str | None
    is_focused: bool


def _run(*args: str) -> object:
    try:
        proc = subprocess.run(
            ["niri", "msg", "-j", *args],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        raise NiriIPCError("niri is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise NiriIPCError(f"niri msg failed: {exc.stderr.decode(errors='replace')}") from exc
    except subprocess.TimeoutExpired as exc:
        raise NiriIPCError("niri msg timed out") from exc

    return json.loads(proc.stdout)


def list_windows() -> list[NiriWindow]:
    data = _run("windows")
    return [
        NiriWindow(
            id=w["id"],
            app_id=w.get("app_id"),
            title=w.get("title"),
            is_focused=bool(w.get("is_focused")),
        )
        for w in data
    ]


def get_focused_window() -> NiriWindow | None:
    for w in list_windows():
        if w.is_focused:
            return w
    return None
