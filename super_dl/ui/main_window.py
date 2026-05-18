from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from super_dl.core.config import AppConfig


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config

        self.setWindowTitle("super-dl")
        self.resize(config.window_width, config.window_height)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("super-dl — UI scaffold (no downloads yet)"))
        self.setCentralWidget(central)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        super().closeEvent(event)
