"""Orchestrates capture -> settle -> OCR -> dedupe -> TTS -> playback,
driven by the active per-game profile. UI-agnostic: the UI and the IPC
control socket both just call methods on an Engine instance.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Callable

from .capture import niri_ipc
from .capture.grim import GrimError, capture_region
from .capture.settle import SettleDetector
from .dedupe import Deduper
from .ocr.easyocr_engine import EasyOCREngine
from .profiles.profile import Profile
from .tts.kokoro_engine import KokoroEngine
from .tts.playback import AudioQueue


class Engine:
    def __init__(
        self,
        on_log: Callable[[str], None] | None = None,
        on_profile_change: Callable[[str], None] | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        self._on_log = on_log or (lambda msg: None)
        self._on_profile_change = on_profile_change or (lambda app_id: None)
        self._on_state_change = on_state_change or (lambda state: None)

        self._paused = threading.Event()
        self._paused.set()  # start paused until a region/profile is ready
        self._stopped = threading.Event()

        self._ocr = EasyOCREngine()
        self._tts = KokoroEngine()
        self._audio = AudioQueue()
        self._settle = SettleDetector()
        self._deduper = Deduper()

        self._profile: Profile | None = None
        self._last_focused_app_id: str | None = None
        # The last non-Ragnarrator window niri reported as focused. Used by
        # the "Select Region" UI action: at the moment that button is
        # clicked, the *focused* window is always Ragnarrator itself, so the
        # game to save the profile under has to come from here instead.
        self._last_seen_app_id: str | None = None
        self._own_pid = os.getpid()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # --- control -----------------------------------------------------
    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stopped.set()
        self._audio.close()

    def pause(self) -> None:
        self._paused.set()
        self._on_log("paused")
        self._on_state_change("paused")

    def resume(self) -> None:
        if self._profile is None:
            self._on_log("no profile/region selected yet - select a region first")
            return
        self._paused.clear()
        self._on_log("resumed")
        self._on_state_change("running")

    def toggle(self) -> None:
        if self._paused.is_set():
            self.resume()
        else:
            self.pause()

    def skip(self) -> None:
        self._audio.clear()

    def set_profile(self, profile: Profile) -> None:
        self._profile = profile
        self._settle = SettleDetector(settle_frames=profile.settle_frames)
        self._deduper = Deduper(similarity_threshold=profile.similarity_threshold)
        self._tts.voice = profile.voice
        self._tts.speed = profile.speed

    def set_voice(self, voice: str) -> None:
        self._tts.voice = voice

    def set_speed(self, speed: float) -> None:
        self._tts.speed = speed

    def get_last_seen_app_id(self) -> str | None:
        return self._last_seen_app_id

    # --- main loop -----------------------------------------------------
    def _run(self) -> None:
        while not self._stopped.is_set():
            self._maybe_switch_profile()

            if self._paused.is_set() or self._profile is None:
                time.sleep(0.3)
                continue

            try:
                frame = capture_region(self._profile.region)
            except GrimError as exc:
                self._on_log(f"capture error: {exc}")
                time.sleep(1.0)
                continue

            if self._settle.observe(frame):
                text = self._ocr.read_text(frame)
                if self._deduper.should_speak(text):
                    self._on_log(f"speaking: {text!r}")
                    self._deduper.mark_spoken(text)
                    audio, sample_rate = self._tts.synthesize(text)
                    self._audio.enqueue(audio, sample_rate)

            time.sleep(self._profile.poll_interval_s)

    def _maybe_switch_profile(self) -> None:
        try:
            focused = niri_ipc.get_focused_window()
        except niri_ipc.NiriIPCError:
            return
        if focused is None or focused.app_id is None:
            return
        if focused.pid == self._own_pid:
            # Ragnarrator's own control window. Ignore entirely - by
            # definition it's focused whenever the user clicks a button in
            # it, so it must never be treated as "the game" regardless of
            # whether a (stale/accidental) profile happens to exist for it.
            return

        self._last_seen_app_id = focused.app_id

        if focused.app_id == self._last_focused_app_id:
            return

        profile = Profile.load(focused.app_id)
        if profile is None:
            # Focus moved to a window with no saved profile - Steam's
            # launcher/overlay, a browser, etc. Don't touch playback state;
            # only react when a *recognized* game gets focus. Deliberately
            # not updating _last_focused_app_id: if a genuinely new,
            # unconfigured game gets focus, this keeps re-checking it (cheap -
            # a JSON-file existence check) so a saved profile added while it's
            # still focused gets picked up without needing an extra alt-tab.
            return

        self._last_focused_app_id = focused.app_id
        self.set_profile(profile)
        self._on_profile_change(focused.app_id)
        self._on_log(f"loaded profile for {focused.app_id}")
