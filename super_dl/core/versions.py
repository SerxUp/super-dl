from __future__ import annotations

import importlib
import platform
from importlib.metadata import PackageNotFoundError, version

UNKNOWN = "unknown"

# (distribution name, module exposing __version__). PyInstaller builds only ship
# dist-info for packages listed in copy_metadata(), so the module attribute is
# the fallback that keeps frozen builds from showing "unknown" everywhere.
_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("yt-dlp", "yt_dlp.version"),
    ("PySide6", "PySide6"),
    ("imageio-ffmpeg", "imageio_ffmpeg"),
    ("platformdirs", "platformdirs"),
)


def _module_version(module_name: str) -> str | None:
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    value = getattr(module, "__version__", None)
    return str(value) if value else None


def package_version(dist_name: str, module_name: str | None = None) -> str:
    try:
        return version(dist_name)
    except PackageNotFoundError:
        pass
    if module_name:
        return _module_version(module_name) or UNKNOWN
    return UNKNOWN


def dependency_versions() -> dict[str, str]:
    return {dist: package_version(dist, module) for dist, module in _DEPENDENCIES}


def python_version() -> str:
    return platform.python_version()


def qt_version() -> str:
    from PySide6.QtCore import qVersion

    return qVersion()
