"""Unix-socket control channel so external tools - e.g. a niri keybind
running `ragnarrator_ctl.py toggle` - can control a running Ragnarrator
instance without relying on global hotkeys, which Wayland compositors don't
expose to regular applications."""
from __future__ import annotations

import os
import socket
import threading
from pathlib import Path
from typing import Callable

SOCKET_PATH = Path(f"/run/user/{os.getuid()}/ragnarrator.sock")


class IPCServer:
    def __init__(self, on_command: Callable[[str], None]) -> None:
        self._on_command = on_command
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(SOCKET_PATH))
        self._sock.listen(4)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        assert self._sock is not None
        while True:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            with conn:
                data = conn.recv(256).decode().strip()
                if data:
                    self._on_command(data)

    def stop(self) -> None:
        if self._sock is not None:
            self._sock.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
