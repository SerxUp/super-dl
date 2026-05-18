from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs("super-dl", "super-dl", roaming=False)


def config_dir() -> Path:
    p = Path(_dirs.user_config_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_dir() -> Path:
    p = Path(_dirs.user_log_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_download_dir() -> Path:
    p = Path.home() / "Downloads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_root() -> Path:
    # In a PyInstaller --onefile build, resources unpack to sys._MEIPASS.
    # In dev, the package directory itself is the bundle root.
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def ffmpeg_path() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()
