# Ragnarrator

An accessibility tool that watches a region of the screen while you play a
game (via Proton on Linux/niri), detects new dialogue text, and reads it
aloud with a local, GPU-accelerated TTS voice - useful for RPGs with lots of
unvoiced text.

Named after Ragn Hemlin, the cleric protagonist of *Esoteric Ebb*, the RPG
this was first built and tested against.

Pipeline: `grim screenshot -> settle detector -> OCR -> fuzzy dedupe -> Kokoro TTS -> audio queue`

## Setup

### 1. System packages

```sh
sudo pacman -S python311 grim slurp espeak-ng
```

- `grim`/`slurp` - Wayland screen capture and region selection (works with
  niri and other wlroots-protocol-compatible compositors; **not** GNOME/KDE).
- `python311` - the ML dependency chain (specifically Kokoro's `misaki` ->
  `spacy` -> `thinc` -> `blis` chain) doesn't yet build on very new Python
  releases. 3.11 is a safe, well-supported target. This does not touch or
  replace your system's default Python.
- `espeak-ng` - fallback grapheme-to-phoneme backend Kokoro/misaki uses for
  out-of-vocabulary words.

### 2. Python environment

```sh
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Confirm GPU acceleration is available:

```sh
./venv/bin/python -c "import torch; print(torch.cuda.is_available())"
```

### 3. Run

```sh
./venv/bin/python main.py
```

This opens the control window and puts an icon in the system tray. The app
starts paused.

### 4. Set up a game

1. Launch your game through Steam/Proton and focus its window.
2. Click **Select Region...** and drag a box around the dialogue area.
   This saves a profile keyed to the game window's niri `app_id`, along with
   the currently selected voice/speed.
3. Click **Resume** (or use the tray menu) to start narrating.

The app polls niri's focused window every loop iteration; switching to a
different game window with its own saved profile auto-loads that profile.
Switching to a window with no saved profile auto-pauses and prompts you to
select a region for it.

**Note:** capture regions are stored as absolute screen coordinates, not
window-relative. If a game window moves (e.g. you drag it or change niri's
layout), re-run **Select Region...** for that game.

## Keybind control (optional)

Since Wayland compositors don't let regular applications register global
hotkeys, control the running app from niri's own keybinds instead, via the
included `ragnarrator_ctl.py` client and a small Unix-socket IPC server the
app exposes at `$XDG_RUNTIME_DIR/ragnarrator.sock`:

```kdl
// ~/.config/niri/config.kdl
binds {
    Mod+N { spawn "/path/to/venv/bin/python" "/path/to/ragnarrator_ctl.py" "toggle"; }
    Mod+Shift+N { spawn "/path/to/venv/bin/python" "/path/to/ragnarrator_ctl.py" "skip"; }
}
```

Commands: `toggle`, `pause`, `resume`, `skip` (drops the currently-playing
and queued audio - handy if you've advanced past what's being read).

## Tuning per game

If a game's font trips up EasyOCR, or the typewriter effect is unusually
slow/fast, edit the saved profile at
`~/.config/ragnarrator/profiles/<app_id>.json`:

- `settle_frames` - how many consecutive identical frames (~poll_interval_s
  apart) before text is considered "done animating". Raise this if dialogue
  gets narrated mid-typewriter-effect.
- `poll_interval_s` - how often the region is screenshotted.
- `similarity_threshold` - fuzzy-match cutoff (0-100) for treating new OCR
  output as a repeat of what was just spoken, rather than new dialogue.
- `ocr_engine` - `"easyocr"` (default) or `"paddleocr"` (requires installing
  `paddlepaddle-gpu paddleocr` separately - often more accurate on heavily
  stylized fantasy fonts, at the cost of being a second, heavier ML stack).

## Project layout

```
ragnarrator/
  capture/    grim/slurp wrappers, niri IPC, settle detection
  ocr/        OCREngine interface + EasyOCR (default) and PaddleOCR (optional)
  tts/        Kokoro wrapper, audio queue/playback
  profiles/   per-game JSON profile load/save
  ui/         PySide6 control window + tray icon, IPC socket server
  dedupe.py   fuzzy text-stabilization logic
  engine.py   orchestration loop tying it all together
main.py             app entry point
ragnarrator_ctl.py  CLI client for the control socket (bind to niri keybinds)
```
