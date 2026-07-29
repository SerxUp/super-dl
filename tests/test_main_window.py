"""UI wiring tests — no network: update checks are disabled in the config."""
from __future__ import annotations

import pytest

from super_dl.core.config import AppConfig
from super_dl.core.cookies import NO_BROWSER, available_browsers
from super_dl.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    w = MainWindow(AppConfig(output_dir=str(tmp_path), check_updates_on_startup=False))
    qtbot.addWidget(w)
    yield w
    w.close()


def test_cookie_combo_defaults_to_no_cookies(window):
    assert window.cookie_combo.currentData() == NO_BROWSER


def test_cookie_combo_lists_every_available_browser(window):
    values = [window.cookie_combo.itemData(i) for i in range(window.cookie_combo.count())]
    assert values == [NO_BROWSER, *available_browsers()]


def test_cookie_combo_has_tooltip(window):
    assert "cookies" in window.cookie_combo.toolTip().lower()


def test_saved_cookie_browser_is_restored(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    cfg = AppConfig(
        output_dir=str(tmp_path),
        check_updates_on_startup=False,
        cookies_from_browser="firefox",
    )
    w = MainWindow(cfg)
    qtbot.addWidget(w)
    try:
        assert w.cookie_combo.currentData() == "firefox"
    finally:
        w.close()


def test_unavailable_cookie_browser_falls_back_to_none(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr("super_dl.core.config.config_dir", lambda: tmp_path)
    cfg = AppConfig(
        output_dir=str(tmp_path),
        check_updates_on_startup=False,
        cookies_from_browser="netscape",
    )
    w = MainWindow(cfg)
    qtbot.addWidget(w)
    try:
        assert w.cookie_combo.currentData() == NO_BROWSER
    finally:
        w.close()
