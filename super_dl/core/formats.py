from __future__ import annotations

from enum import Enum


class FormatPreset(str, Enum):
    BEST_VIDEO_AUDIO = "best_video_audio"
    BEST_AUDIO = "best_audio"
    CUSTOM = "custom"


# Format-selector reference: https://github.com/yt-dlp/yt-dlp#format-selection
_PRESETS: dict[str, str] = {
    FormatPreset.BEST_VIDEO_AUDIO.value: "bv*+ba/b",
    FormatPreset.BEST_AUDIO.value: "ba/b",
}

_DEFAULT = _PRESETS[FormatPreset.BEST_VIDEO_AUDIO.value]


def resolve_format(preset: str, custom: str = "") -> str:
    if preset == FormatPreset.CUSTOM.value:
        return custom.strip() or _DEFAULT
    return _PRESETS.get(preset, _DEFAULT)
