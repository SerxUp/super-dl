from __future__ import annotations

from super_dl.core.formats import FormatPreset, resolve_format


def test_best_video_audio_preset():
    assert resolve_format(FormatPreset.BEST_VIDEO_AUDIO.value) == "bv*+ba/b"


def test_best_audio_preset():
    assert resolve_format(FormatPreset.BEST_AUDIO.value) == "ba/b"


def test_custom_returns_user_string_verbatim():
    assert (
        resolve_format(FormatPreset.CUSTOM.value, "bv[height<=720]+ba")
        == "bv[height<=720]+ba"
    )


def test_custom_strips_whitespace():
    assert resolve_format(FormatPreset.CUSTOM.value, "  ba  ") == "ba"


def test_custom_empty_falls_back_to_default():
    assert resolve_format(FormatPreset.CUSTOM.value, "  ") == "bv*+ba/b"


def test_unknown_preset_falls_back_to_default():
    assert resolve_format("not_a_real_preset") == "bv*+ba/b"
