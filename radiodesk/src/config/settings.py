import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    base_dir: Path = field(default_factory=lambda: Path.home() / ".radiodesk")
    db_path: Path = field(default=None)
    media_path: Path = field(default=None)
    session_timeout_minutes: int = 30
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        self.base_dir = Path(os.environ.get("RADIODESK_HOME", str(self.base_dir)))
        self.db_path = self.db_path or self.base_dir / "radiodesk.db"
        self.media_path = self.media_path or self.base_dir / "media"
        self.session_timeout_minutes = int(os.environ.get("SESSION_TIMEOUT", self.session_timeout_minutes))
        self.log_level = os.environ.get("LOG_LEVEL", self.log_level)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.media_path.mkdir(parents=True, exist_ok=True)
