#!/usr/bin/env python3
"""Tiny client for controlling a running Ragnarrator instance, meant to be
bound to a niri keybind, e.g. in ~/.config/niri/config.kdl:

    Mod+N { spawn "/path/to/venv/bin/python" "/path/to/ragnarrator_ctl.py" "toggle"; }

Usage: ragnarrator_ctl.py <toggle|pause|resume|skip>
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

SOCKET_PATH = Path(f"/run/user/{os.getuid()}/ragnarrator.sock")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"toggle", "pause", "resume", "skip"}:
        print(__doc__)
        return 1

    if not SOCKET_PATH.exists():
        print("Ragnarrator is not running (socket not found)", file=sys.stderr)
        return 1

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(SOCKET_PATH))
        sock.sendall(sys.argv[1].encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
