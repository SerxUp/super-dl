from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from super_dl.core.config import AppConfig
from super_dl.core.downloader import (
    DownloadRequest,
    ErrorKind,
    WorkerState,
    YtDlpWorker,
)
from super_dl.core.formats import FormatPreset, resolve_format

_PRESET_LABELS: list[tuple[str, str]] = [
    ("Best video + audio", FormatPreset.BEST_VIDEO_AUDIO.value),
    ("Best audio only", FormatPreset.BEST_AUDIO.value),
    ("Custom format string", FormatPreset.CUSTOM.value),
]

_BUSY_STATES = {WorkerState.EXTRACTING, WorkerState.DOWNLOADING, WorkerState.POSTPROCESSING}


def _fmt_bytes(n: float | None) -> str:
    if n is None:
        return "?"
    f = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if f < 1024:
            return f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} PB"


def _fmt_speed(s: float | None) -> str:
    return f"{_fmt_bytes(s)}/s" if s else "—"


def _fmt_eta(eta: int | None) -> str:
    if eta is None:
        return "—"
    m, s = divmod(int(eta), 60)
    return f"{m}:{s:02d}"


class MainWindow(QMainWindow):
    request_download = Signal(object)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._state = WorkerState.IDLE

        self.setWindowTitle("super-dl")
        self.resize(config.window_width, config.window_height)

        self._build_ui()
        self._apply_config()
        self._setup_worker()
        self._apply_state(WorkerState.IDLE)

    # --- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://...")
        url_row.addWidget(self.url_edit, 1)
        root.addLayout(url_row)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        for label, value in _PRESET_LABELS:
            self.format_combo.addItem(label, value)
        self.format_combo.currentIndexChanged.connect(self._on_preset_changed)
        fmt_row.addWidget(self.format_combo)
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("e.g. bv[height<=720]+ba")
        fmt_row.addWidget(self.custom_edit, 1)
        root.addLayout(fmt_row)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output:"))
        self.output_edit = QLineEdit()
        out_row.addWidget(self.output_edit, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._on_browse)
        out_row.addWidget(browse)
        root.addLayout(out_row)

        action_row = QHBoxLayout()
        self.action_btn = QPushButton("Download")
        self.action_btn.clicked.connect(self._on_action)
        action_row.addWidget(self.action_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.status_label)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        root.addWidget(self.log_view, 1)

        self.setCentralWidget(central)

    def _apply_config(self) -> None:
        self.output_edit.setText(self._config.output_dir)
        idx = self.format_combo.findData(self._config.format_preset)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        self.custom_edit.setText(self._config.custom_format)
        self._on_preset_changed()

    def _setup_worker(self) -> None:
        self._thread = QThread(self)
        self._worker = YtDlpWorker()
        self._worker.moveToThread(self._thread)

        self.request_download.connect(self._worker.start)
        self._worker.state_changed.connect(self._apply_state)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)

        self._thread.start()

    # --- Slots --------------------------------------------------------------

    def _on_preset_changed(self) -> None:
        is_custom = self.format_combo.currentData() == FormatPreset.CUSTOM.value
        self.custom_edit.setEnabled(is_custom)

    def _on_browse(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Choose output directory", self.output_edit.text()
        )
        if d:
            self.output_edit.setText(d)

    def _on_action(self) -> None:
        if self._state in _BUSY_STATES:
            self._worker.cancel()
            self.status_label.setText("Cancelling…")
            self.action_btn.setEnabled(False)
        else:
            self._start_download()

    def _start_download(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "super-dl", "Please enter a URL.")
            return

        out = Path(self.output_edit.text()).expanduser()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "super-dl", f"Cannot create output directory:\n{e}")
            return

        preset = self.format_combo.currentData()
        custom = self.custom_edit.text()
        selector = resolve_format(preset, custom)

        self._config.output_dir = str(out)
        self._config.format_preset = preset
        self._config.custom_format = custom

        self.log_view.clear()
        self.request_download.emit(
            DownloadRequest(url=url, format_selector=selector, output_dir=out)
        )

    # --- Worker signal handlers --------------------------------------------

    def _apply_state(self, state: WorkerState) -> None:
        self._state = state
        if state == WorkerState.IDLE:
            self.action_btn.setText("Download")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("")
        elif state == WorkerState.EXTRACTING:
            self.action_btn.setText("Cancel")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Fetching metadata…")
        elif state == WorkerState.DOWNLOADING:
            self.action_btn.setText("Cancel")
            self.action_btn.setEnabled(True)
            self.status_label.setText("Downloading…")
        elif state == WorkerState.POSTPROCESSING:
            self.action_btn.setText("Cancel")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Post-processing…")
        elif state == WorkerState.DONE:
            self.action_btn.setText("Download")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.status_label.setText("Done.")
        elif state == WorkerState.ERROR:
            self.action_btn.setText("Download")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            # status text is set by _on_failed
        elif state == WorkerState.CANCELLED:
            self.action_btn.setText("Download")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("Cancelled.")

    def _on_progress(
        self,
        downloaded: int,
        total: int | None,
        speed: float | None,
        eta: int | None,
    ) -> None:
        if total:
            if self.progress_bar.maximum() != 100:
                self.progress_bar.setRange(0, 100)
            pct = max(0, min(100, int(downloaded * 100 / total)))
            self.progress_bar.setValue(pct)
            self.status_label.setText(
                f"{_fmt_bytes(downloaded)} / {_fmt_bytes(total)}   "
                f"{_fmt_speed(speed)}   ETA {_fmt_eta(eta)}"
            )
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText(f"{_fmt_bytes(downloaded)}   {_fmt_speed(speed)}")

    def _on_log(self, level: int, message: str) -> None:
        prefix = logging.getLevelName(level).lower()
        self.log_view.append(f"[{prefix}] {message}")

    def _on_finished(self, output_path: Path | None) -> None:
        if output_path:
            self.log_view.append(f"[info] saved: {output_path}")

    def _on_failed(self, kind: ErrorKind, message: str, traceback_str: str) -> None:
        self.status_label.setText(f"Error: {message}")
        self.log_view.append(f"[error] {message}")
        hint = ""
        if kind == ErrorKind.EXTRACTOR:
            hint = (
                "\n\nThis often means yt-dlp needs an update — the site's "
                "format may have changed."
            )
        QMessageBox.critical(self, "super-dl", message + hint)

    # --- Lifecycle ----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        if self._thread.isRunning():
            self._worker.cancel()
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
