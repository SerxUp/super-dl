from __future__ import annotations

from importlib.resources import as_file, files

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from super_dl.core.config import AppConfig
from super_dl.core.logging_setup import setup_logging
from super_dl.ui.main_window import MainWindow


def _load_app_icon() -> QIcon:
    res = files("super_dl.resources").joinpath("icon.ico")
    with as_file(res) as path:
        return QIcon(str(path))


def run(argv: list[str]) -> int:
    setup_logging()
    config = AppConfig.load()

    app = QApplication(argv)
    app.setApplicationName("super-dl")
    app.setOrganizationName("super-dl")
    app.setWindowIcon(_load_app_icon())

    window = MainWindow(config)
    window.show()

    exit_code = app.exec()
    config.save()
    return exit_code
