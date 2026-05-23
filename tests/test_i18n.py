from __future__ import annotations

import pytest

from super_dl.core.i18n import (
    SUPPORTED_LANGS,
    install_translators,
    resolve_language,
)


def test_resolve_empty_returns_supported():
    assert resolve_language("") in SUPPORTED_LANGS


def test_resolve_unsupported_falls_back_to_english():
    assert resolve_language("de") == "en"


def test_resolve_explicit_supported():
    assert resolve_language("es") == "es"
    assert resolve_language("fr") == "fr"


@pytest.mark.parametrize("lang", SUPPORTED_LANGS)
def test_install_translators_no_error(qtbot, lang):
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    translators = install_translators(app, lang)
    assert isinstance(translators, list)
    # English is the source language: the app translator is intentionally skipped.
    if lang != "en":
        assert translators, f"expected at least one translator for {lang}"
