"""Main control window: region selection, start/pause, voice/speed, log."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..capture.region import SlurpError, select_region
from ..profiles.profile import Profile

# A modest curated set of built-in Kokoro voices; see the kokoro package's
# own voice list for the full set if you want more options.
VOICES = [
    "af_heart", "af_bella", "af_sarah", "af_nicole",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella", "bm_george", "bm_lewis",
]


def _make_icon(color: str) -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, engine, bridge) -> None:
        super().__init__()
        self._engine = engine
        self._bridge = bridge

        self.setWindowTitle("Ragnarrator")
        self.resize(560, 420)

        self._select_region_btn = QPushButton("Select Region…")
        self._select_region_btn.clicked.connect(self._on_select_region)

        self._toggle_btn = QPushButton("Resume")
        self._toggle_btn.clicked.connect(self._on_toggle)

        self._profile_label = QLabel("No window focused")

        self._voice_combo = QComboBox()
        self._voice_combo.addItems(VOICES)
        self._voice_combo.currentTextChanged.connect(self._engine.set_voice)

        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(0.5, 2.0)
        self._speed_spin.setSingleStep(0.1)
        self._speed_spin.setValue(1.0)
        self._speed_spin.valueChanged.connect(self._engine.set_speed)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)

        top_row = QHBoxLayout()
        top_row.addWidget(self._select_region_btn)
        top_row.addWidget(self._toggle_btn)
        top_row.addWidget(self._profile_label, 1)

        settings_row = QHBoxLayout()
        settings_row.addWidget(QLabel("Voice:"))
        settings_row.addWidget(self._voice_combo)
        settings_row.addWidget(QLabel("Speed:"))
        settings_row.addWidget(self._speed_spin)
        settings_row.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addLayout(settings_row)
        layout.addWidget(self._log)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._bridge.log_message.connect(self._append_log)
        self._bridge.profile_changed.connect(self._on_profile_changed)
        self._bridge.state_changed.connect(self._on_state_changed)

        self._tray = self._make_tray()

    # --- tray -----------------------------------------------------
    def _make_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(_make_icon("#89B4FA"), self)
        tray.setToolTip("Ragnarrator")

        menu = QMenu()
        show_action = QAction("Show window", self)
        show_action.triggered.connect(self._show_and_raise)
        toggle_action = QAction("Toggle narration", self)
        toggle_action.triggered.connect(self._on_toggle)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_quit)

        menu.addAction(show_action)
        menu.addAction(toggle_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        return tray

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_and_raise()

    def _show_and_raise(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_quit(self) -> None:
        QApplication.instance().quit()

    # --- actions -----------------------------------------------------
    def _on_select_region(self) -> None:
        # Not get_focused_window(): at the instant this button is clicked,
        # the focused window is always Ragnarrator itself. The engine tracks
        # the last *other* window niri reported as focused instead.
        app_id = self._engine.get_last_seen_app_id()
        if app_id is None:
            QMessageBox.warning(
                self, "Ragnarrator",
                "Haven't seen a game window focused yet. Switch to your game for "
                "a moment, then come back and try again.",
            )
            return

        self.showMinimized()
        try:
            geometry = select_region()
        except SlurpError as exc:
            self.showNormal()
            QMessageBox.warning(self, "Ragnarrator", str(exc))
            return
        self.showNormal()

        profile = Profile.load(app_id) or Profile(app_id=app_id, region=geometry)
        profile.region = geometry
        profile.voice = self._voice_combo.currentText()
        profile.speed = self._speed_spin.value()
        profile.save()

        self._engine.set_profile(profile)
        self._profile_label.setText(f"Profile: {app_id}")
        self._append_log(f"saved region for {app_id}: {geometry}")

    def _on_toggle(self) -> None:
        self._engine.toggle()

    # --- bridge slots -----------------------------------------------------
    def _append_log(self, message: str) -> None:
        self._log.appendPlainText(message)

    def _on_profile_changed(self, app_id: str) -> None:
        self._profile_label.setText(f"Profile: {app_id}")

    def _on_state_changed(self, state: str) -> None:
        self._toggle_btn.setText("Pause" if state == "running" else "Resume")

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
