from __future__ import annotations

import logging
from importlib.resources import as_file, files

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

SUPPORTED_LANGS: tuple[str, ...] = ("en", "es", "fr")

LANG_DISPLAY: dict[str, str] = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
}


def resolve_language(config_value: str) -> str:
    if config_value in SUPPORTED_LANGS:
        return config_value
    sys_lang = QLocale.system().name()[:2].lower()
    if sys_lang in SUPPORTED_LANGS:
        return sys_lang
    return "en"


def install_translators(app: QApplication, lang: str) -> list[QTranslator]:
    translators: list[QTranslator] = []

    qt_base = QTranslator(app)
    qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_base.load(QLocale(lang), "qtbase", "_", qt_dir):
        app.installTranslator(qt_base)
        translators.append(qt_base)
    else:
        logger.debug("No qtbase translation for %s in %s", lang, qt_dir)

    if lang != "en":
        app_tr = QTranslator(app)
        res = files("super_dl.resources.i18n").joinpath(f"super_dl_{lang}.qm")
        with as_file(res) as qm_path:
            if qm_path.exists() and app_tr.load(str(qm_path)):
                app.installTranslator(app_tr)
                translators.append(app_tr)
            else:
                logger.warning("Failed to load app translation: %s", qm_path)

    return translators
