from __future__ import annotations

import json

from super_dl.core.config import AppConfig


def test_load_returns_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    cfg = AppConfig.load()
    assert cfg.version == 1
    assert cfg.format_preset == "best_video_audio"


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    cfg = AppConfig(format_preset="best_audio", window_width=1000)
    cfg.save()

    loaded = AppConfig.load()
    assert loaded.format_preset == "best_audio"
    assert loaded.window_width == 1000


def test_ui_language_defaults_to_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    assert AppConfig.load().ui_language == ""


def test_ui_language_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    AppConfig(ui_language="fr").save()
    assert AppConfig.load().ui_language == "fr"


def test_unknown_keys_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps({"format_preset": "best_audio", "future_field": "wat"}),
        encoding="utf-8",
    )
    cfg = AppConfig.load()
    assert cfg.format_preset == "best_audio"


def test_corrupt_file_falls_back_to_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text("not valid json{", encoding="utf-8")
    cfg = AppConfig.load()
    assert cfg.format_preset == "best_video_audio"
