from __future__ import annotations

from PySide6.QtWidgets import QApplication

from super_dl.core.config import AppConfig
from super_dl.core.logging_setup import setup_logging
from super_dl.ui.main_window import MainWindow


def run(argv: list[str]) -> int:
    setup_logging()
    config = AppConfig.load()

    app = QApplication(argv)
    app.setApplicationName("super-dl")
    app.setOrganizationName("super-dl")

    window = MainWindow(config)
    window.show()

    exit_code = app.exec()
    config.save()
    return exit_code
