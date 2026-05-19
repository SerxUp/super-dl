from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from super_dl import APP_NAME
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
    ("MP4 up to 720p", FormatPreset.MP4_720P.value),
    ("MP4 up to 1080p", FormatPreset.MP4_1080P.value),
    ("Best audio only", FormatPreset.BEST_AUDIO.value),
    ("MP3 (audio extract)", FormatPreset.MP3_AUDIO.value),
    ("Custom format string", FormatPreset.CUSTOM.value),
]

_BUSY_STATES = {WorkerState.EXTRACTING, WorkerState.DOWNLOADING, WorkerState.POSTPROCESSING}

_COLOR_SUCCESS = "#1aa64b"
_COLOR_ERROR = "#c92a2a"
_COLOR_CANCEL = "#d97706"


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


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class MainWindow(QMainWindow):
    request_download = Signal(object)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._state = WorkerState.IDLE

        # Queue progress tracking
        self._queue_total = 0
        self._queue_completed = 0
        self._queue_start: float | None = None
        self._current_item_fraction = 0.0

        self.setWindowTitle(APP_NAME)
        self.resize(config.window_width, config.window_height)

        self._mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self._build_ui()
        self._apply_config()
        self._setup_worker()
        self._setup_tray()

        self._queue_timer = QTimer(self)
        self._queue_timer.setInterval(1000)
        self._queue_timer.timeout.connect(self._refresh_queue_label)

        self._apply_state(WorkerState.IDLE)

    # --- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        url_row = QHBoxLayout()
        url_label = QLabel("URLs:")
        url_label.setAlignment(Qt.AlignTop)
        url_row.addWidget(url_label)
        self.url_edit = QPlainTextEdit()
        self.url_edit.setFont(self._mono_font)
        self.url_edit.setPlaceholderText("One URL per line\nhttps://...")
        fm = self.url_edit.fontMetrics()
        self.url_edit.setFixedHeight(fm.lineSpacing() * 4 + 12)
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
        self.custom_edit.setFont(self._mono_font)
        self.custom_edit.setPlaceholderText("e.g. bv[height<=720]+ba")
        fmt_row.addWidget(self.custom_edit, 1)
        root.addLayout(fmt_row)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output:"))
        self.output_edit = QLineEdit()
        self.output_edit.setFont(self._mono_font)
        out_row.addWidget(self.output_edit, 1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._on_browse)
        out_row.addWidget(browse)
        root.addLayout(out_row)

        opt_row = QHBoxLayout()
        opt_row.addSpacing(self.fontMetrics().horizontalAdvance("Output: "))
        self.subfolder_check = QCheckBox("Create subfolder per URL (playlist / channel / title)")
        opt_row.addWidget(self.subfolder_check)
        opt_row.addStretch(1)
        root.addLayout(opt_row)

        action_row = QHBoxLayout()
        self.action_btn = QPushButton("Download")
        self.action_btn.clicked.connect(self._on_action)
        action_row.addStretch(1)
        action_row.addWidget(self.action_btn)
        action_row.addStretch(1)
        action_row.setContentsMargins(0, 8, 0, 0)
        f = self.action_btn.font()
        f.setPointSize(12)
        self.action_btn.setFont(f)

        root.addLayout(action_row)

        self.overall_label = QLabel("")
        self.overall_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.overall_label)

        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)
        self.overall_bar.setTextVisible(True)
        self.overall_bar.setFormat("Queue %v / %m")
        self.overall_bar.setVisible(False)
        root.addWidget(self.overall_bar)

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
        self.subfolder_check.setChecked(self._config.subfolder_per_url)
        self._on_preset_changed()

    def _setup_worker(self) -> None:
        self._thread = QThread(self)
        self._worker = YtDlpWorker()
        self._worker.moveToThread(self._thread)

        self.request_download.connect(self._worker.start)
        self._worker.state_changed.connect(self._apply_state)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._on_log)
        self._worker.item_started.connect(self._on_item_started)
        self._worker.item_finished.connect(self._on_item_finished)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)

        self._thread.start()

    def _setup_tray(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray: QSystemTrayIcon | None = QSystemTrayIcon(self.windowIcon(), self)
            self._tray.setToolTip(APP_NAME)
            self._tray.show()
        else:
            self._tray = None

    def _notify(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        if self._tray is None or not self._tray.supportsMessages():
            return
        self._tray.showMessage(title, message, icon, 5000)

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
        urls = tuple(
            line.strip() for line in self.url_edit.toPlainText().splitlines() if line.strip()
        )
        if not urls:
            QMessageBox.warning(self, APP_NAME, "Please enter at least one URL.")
            return

        out = Path(self.output_edit.text()).expanduser()
        try:
            out.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, APP_NAME, f"Cannot create output directory:\n{e}")
            return

        preset = self.format_combo.currentData()
        custom = self.custom_edit.text()
        spec = resolve_format(preset, custom)
        subfolder = self.subfolder_check.isChecked()

        self._config.output_dir = str(out)
        self._config.format_preset = preset
        self._config.custom_format = custom
        self._config.subfolder_per_url = subfolder

        self._queue_total = len(urls)
        self._queue_completed = 0
        self._queue_start = time.monotonic()
        self._current_item_fraction = 0.0

        self.overall_bar.setRange(0, self._queue_total)
        self.overall_bar.setValue(0)
        self.overall_bar.setVisible(self._queue_total > 1)

        self.log_view.clear()
        self.overall_label.setText("")
        self._queue_timer.start()
        self.request_download.emit(
            DownloadRequest(
                urls=urls,
                format_spec=spec,
                output_dir=out,
                subfolder_per_url=subfolder,
            )
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
            self.overall_bar.setValue(self.overall_bar.maximum())
            self.status_label.setText(
                f"<span style='color:{_COLOR_SUCCESS};font-weight:bold;'>SUCCESS!</span>"
            )
            self._queue_timer.stop()
        elif state == WorkerState.ERROR:
            self.action_btn.setText("Download")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            self._queue_timer.stop()
            # status text set by _on_failed
        elif state == WorkerState.CANCELLED:
            self.action_btn.setText("Download")
            self.action_btn.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText(
                f"<span style='color:{_COLOR_CANCEL};font-weight:bold;'>Cancelled.</span>"
            )
            self._queue_timer.stop()

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
            self._current_item_fraction = max(0.0, min(1.0, downloaded / total))
            self.status_label.setText(
                f"{_fmt_bytes(downloaded)} / {_fmt_bytes(total)}   "
                f"{_fmt_speed(speed)}   item ETA {_fmt_duration(eta)}"
            )
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText(f"{_fmt_bytes(downloaded)}   {_fmt_speed(speed)}")
        self._refresh_queue_label()

    def _on_log(self, level: int, message: str) -> None:
        prefix = logging.getLevelName(level).lower()
        self.log_view.append(f"[{prefix}] {message}")

    def _on_item_started(self, index: int, total: int, url: str) -> None:
        self._current_item_fraction = 0.0
        if self._queue_total != total:
            self._queue_total = total
            self.overall_bar.setRange(0, total)
            self.overall_bar.setVisible(total > 1)
        self.overall_bar.setValue(index - 1)
        self.log_view.append(f"[info] starting ({index}/{total}): {url}")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)
        self._refresh_queue_label()

    def _on_item_finished(self, _index: int, output_path: Path | None) -> None:
        if output_path:
            self._queue_completed += 1
            self.log_view.append(f"[info] saved: {output_path}")
        self._current_item_fraction = 0.0
        self.overall_bar.setValue(self._queue_completed)
        self._refresh_queue_label()

    def _on_finished(self, output_paths: list[Path]) -> None:
        self._queue_timer.stop()
        n = len(output_paths)
        if n:
            self.log_view.append(f"[info] queue done — {n} file(s) saved")
        if self._state == WorkerState.CANCELLED:
            if n:
                self._notify(
                    "Downloads cancelled",
                    f"Partial: {n} file(s) saved before cancel.",
                    QSystemTrayIcon.MessageIcon.Warning,
                )
            return
        if n:
            self._notify(
                "Downloads complete",
                f"{n} file(s) saved to {self.output_edit.text()}",
            )

    def _on_failed(self, kind: ErrorKind, message: str, traceback_str: str) -> None:
        self._queue_timer.stop()
        self.status_label.setText(
            f"<span style='color:{_COLOR_ERROR};font-weight:bold;'>Error:</span> {message}"
        )
        self.log_view.append(f"[error] {message}")
        hint = ""
        if kind == ErrorKind.EXTRACTOR:
            hint = (
                "\n\nThis often means yt-dlp needs an update — the site's format may have changed."
            )
        self._notify(
            "Download failed",
            message,
            QSystemTrayIcon.MessageIcon.Critical,
        )
        QMessageBox.critical(self, APP_NAME, message + hint)

    def _refresh_queue_label(self) -> None:
        if self._queue_total == 0 or self._queue_start is None:
            self.overall_label.setText("")
            return
        elapsed = time.monotonic() - self._queue_start
        effective = self._queue_completed + self._current_item_fraction
        if 0.05 < effective < self._queue_total:
            eta = elapsed / effective * (self._queue_total - effective)
            eta_txt = _fmt_duration(int(eta))
        else:
            eta_txt = "—"
        self.overall_label.setText(
            f"<b>Queue:</b> {self._queue_completed} / {self._queue_total}"
            f" &nbsp;·&nbsp; elapsed {_fmt_duration(int(elapsed))}"
            f" &nbsp;·&nbsp; ETA {eta_txt}"
        )

    # --- Lifecycle ----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        if self._tray is not None:
            self._tray.hide()
        if self._thread.isRunning():
            self._worker.cancel()
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
