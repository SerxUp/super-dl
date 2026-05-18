from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FormatPreset(str, Enum):
    BEST_VIDEO_AUDIO = "best_video_audio"
    BEST_AUDIO = "best_audio"
    MP4_720P = "mp4_720p"
    MP4_1080P = "mp4_1080p"
    MP3_AUDIO = "mp3_audio"
    CUSTOM = "custom"


@dataclass(frozen=True)
class FormatSpec:
    selector: str
    postprocessors: tuple[dict, ...] = field(default_factory=tuple)
    merge_output_format: str | None = None


# Format-selector reference: https://github.com/yt-dlp/yt-dlp#format-selection
_DEFAULT_SELECTOR = "bv*+ba/b"

_MP3_POSTPROCESSORS: tuple[dict, ...] = (
    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
)


def _mp4_capped(max_height: int) -> str:
    return (
        f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/"
        f"bv*[height<={max_height}]+ba/"
        f"b[height<={max_height}]"
    )


_PRESETS: dict[str, FormatSpec] = {
    FormatPreset.BEST_VIDEO_AUDIO.value: FormatSpec(_DEFAULT_SELECTOR),
    FormatPreset.BEST_AUDIO.value: FormatSpec("ba/b"),
    FormatPreset.MP4_720P.value: FormatSpec(_mp4_capped(720), merge_output_format="mp4"),
    FormatPreset.MP4_1080P.value: FormatSpec(_mp4_capped(1080), merge_output_format="mp4"),
    FormatPreset.MP3_AUDIO.value: FormatSpec("ba/b", postprocessors=_MP3_POSTPROCESSORS),
}

_DEFAULT = _PRESETS[FormatPreset.BEST_VIDEO_AUDIO.value]


def resolve_format(preset: str, custom: str = "") -> FormatSpec:
    if preset == FormatPreset.CUSTOM.value:
        selector = custom.strip() or _DEFAULT_SELECTOR
        return FormatSpec(selector)
    return _PRESETS.get(preset, _DEFAULT)
