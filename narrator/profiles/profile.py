"""Per-game profile: capture region + OCR/voice/timing settings, persisted
as JSON keyed by the game window's niri app_id."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

PROFILES_DIR = Path.home() / ".config" / "narrator" / "profiles"


@dataclass
class Profile:
    app_id: str
    region: str  # grim geometry string, "X,Y WxH"
    ocr_engine: str = "easyocr"
    voice: str = "af_heart"
    speed: float = 1.0
    settle_frames: int = 3
    poll_interval_s: float = 0.2
    similarity_threshold: float = 92.0

    def path(self) -> Path:
        return PROFILES_DIR / f"{_slug(self.app_id)}.json"

    def save(self) -> None:
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self.path().write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, app_id: str) -> "Profile | None":
        path = PROFILES_DIR / f"{_slug(app_id)}.json"
        if not path.exists():
            return None
        return cls(**json.loads(path.read_text()))

    @classmethod
    def list_all(cls) -> list["Profile"]:
        if not PROFILES_DIR.exists():
            return []
        return [cls(**json.loads(p.read_text())) for p in sorted(PROFILES_DIR.glob("*.json"))]


def _slug(app_id: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_id).strip("_")
    return cleaned or "default"
