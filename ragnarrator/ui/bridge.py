"""Qt signal bridge so the background pipeline thread (Engine) can safely
push updates to widgets living on the GUI thread. Qt auto-marshals a signal
emitted from a non-GUI thread to a receiver on the GUI thread."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class Bridge(QObject):
    log_message = Signal(str)
    profile_changed = Signal(str)
    state_changed = Signal(str)  # "running" | "paused"
