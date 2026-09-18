"""FIFO audio queue + playback, so consecutive dialogue lines are spoken in
order rather than overlapping/garbling."""
from __future__ import annotations

import queue
import threading
import time

import numpy as np
import sounddevice as sd


class AudioQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[np.ndarray, int] | None] = queue.Queue()
        self._skip_requested = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def enqueue(self, audio: np.ndarray, sample_rate: int) -> None:
        self._queue.put((audio, sample_rate))

    def skip_current(self) -> None:
        """Stop whatever is currently playing; the rest of the queue continues."""
        self._skip_requested.set()

    def clear(self) -> None:
        """Drop everything queued, including the currently-playing line."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self.skip_current()

    def close(self) -> None:
        self.clear()
        self._queue.put(None)

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            audio, sample_rate = item
            self._skip_requested.clear()
            sd.play(audio, sample_rate)
            stream = sd.get_stream()
            while stream is not None and stream.active:
                if self._skip_requested.is_set():
                    sd.stop()
                    break
                time.sleep(0.05)
