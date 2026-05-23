from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from super_dl.core.paths import config_dir, default_download_dir

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
CONFIG_VERSION = 1


@dataclass
class AppConfig:
    version: int = CONFIG_VERSION
    output_dir: str = field(default_factory=lambda: str(default_download_dir()))
    format_preset: str = "best_video_audio"  # best_video_audio | best_audio | custom
    custom_format: str = ""
    subfolder_per_url: bool = False
    window_width: int = 720
    window_height: int = 480
    check_updates_on_startup: bool = True
    skip_version: str | None = None
    last_update_check_iso: str | None = None
    ui_language: str = ""

    @classmethod
    def path(cls) -> Path:
        return config_dir() / CONFIG_FILE

    @classmethod
    def load(cls) -> AppConfig:
        p = cls.path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to read config (%s); using defaults", e)
            return cls()
        known = set(cls.__dataclass_fields__)
        clean = {k: v for k, v in data.items() if k in known}
        return cls(**clean)

    def save(self) -> None:
        p = self.path()
        try:
            p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except OSError as e:
            logger.error("Failed to save config: %s", e)
