from __future__ import annotations

from super_dl.core.formats import FormatPreset, FormatSpec, resolve_format


def test_best_video_audio_preset():
    spec = resolve_format(FormatPreset.BEST_VIDEO_AUDIO.value)
    assert spec.selector == "bv*+ba/b"
    assert spec.postprocessors == ()
    assert spec.merge_output_format is None


def test_best_audio_preset():
    spec = resolve_format(FormatPreset.BEST_AUDIO.value)
    assert spec.selector == "ba/b"
    assert spec.postprocessors == ()


def test_mp4_720p_preset_caps_height_and_merges_mp4():
    spec = resolve_format(FormatPreset.MP4_720P.value)
    assert "height<=720" in spec.selector
    assert spec.merge_output_format == "mp4"
    assert spec.postprocessors == ()


def test_mp4_1080p_preset_caps_height_and_merges_mp4():
    spec = resolve_format(FormatPreset.MP4_1080P.value)
    assert "height<=1080" in spec.selector
    assert spec.merge_output_format == "mp4"


def test_mp3_audio_preset_wires_extract_audio_postprocessor():
    spec = resolve_format(FormatPreset.MP3_AUDIO.value)
    assert spec.selector == "ba/b"
    assert len(spec.postprocessors) == 1
    pp = spec.postprocessors[0]
    assert pp["key"] == "FFmpegExtractAudio"
    assert pp["preferredcodec"] == "mp3"


def test_custom_returns_user_string_verbatim():
    spec = resolve_format(FormatPreset.CUSTOM.value, "bv[height<=720]+ba")
    assert spec.selector == "bv[height<=720]+ba"
    assert spec.postprocessors == ()
    assert spec.merge_output_format is None


def test_custom_strips_whitespace():
    assert resolve_format(FormatPreset.CUSTOM.value, "  ba  ").selector == "ba"


def test_custom_empty_falls_back_to_default():
    assert resolve_format(FormatPreset.CUSTOM.value, "  ").selector == "bv*+ba/b"


def test_unknown_preset_falls_back_to_default():
    spec = resolve_format("not_a_real_preset")
    assert isinstance(spec, FormatSpec)
    assert spec.selector == "bv*+ba/b"
