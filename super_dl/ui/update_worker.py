from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from super_dl.core.updater import UpdateCheckError, check_for_update


class UpdateWorker(QObject):
    finished = Signal(object)  # UpdateInfo
    failed = Signal(str)

    def __init__(self, current_version: str) -> None:
        super().__init__()
        self._current = current_version

    @Slot()
    def run(self) -> None:
        try:
            info = check_for_update(self._current)
        except UpdateCheckError as e:
            self.failed.emit(str(e))
            return
        self.finished.emit(info)
