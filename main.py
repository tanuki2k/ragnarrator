#!/usr/bin/env python3
"""Entry point: wires the UI, IPC control socket, and the capture/OCR/TTS
engine together.

Run inside the project venv (see README.md for setup):

    ./venv/bin/python main.py
"""
from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtWidgets import QApplication

from narrator.engine import Engine
from narrator.ui.bridge import Bridge
from narrator.ui.ipc_server import IPCServer
from narrator.ui.window import MainWindow


def _dispatch(engine: Engine) -> Callable[[str], None]:
    commands = {
        "toggle": engine.toggle,
        "pause": engine.pause,
        "resume": engine.resume,
        "skip": engine.skip,
    }

    def handler(command: str) -> None:
        action = commands.get(command)
        if action is not None:
            action()

    return handler


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    bridge = Bridge()
    engine = Engine(
        on_log=bridge.log_message.emit,
        on_profile_change=bridge.profile_changed.emit,
        on_state_change=bridge.state_changed.emit,
    )

    window = MainWindow(engine=engine, bridge=bridge)
    window.show()

    ipc = IPCServer(on_command=_dispatch(engine))
    ipc.start()

    engine.start()

    exit_code = app.exec()
    engine.stop()
    ipc.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
