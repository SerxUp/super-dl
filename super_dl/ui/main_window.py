from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from super_dl import APP_NAME, __version__
from super_dl.core.config import AppConfig
from super_dl.core.downloader import (
    DownloadRequest,
    ErrorKind,
    WorkerState,
    YtDlpWorker,
)
from super_dl.core.formats import FormatPreset, resolve_format
from super_dl.core.updater import UpdateInfo
from super_dl.ui.about_dialog import AboutDialog
from super_dl.ui.update_worker import UpdateWorker

_UPDATE_CHECK_INTERVAL = timedelta(hours=24)

_PRESET_LABELS: list[tuple[str, str]] = [
    ("Best video + audio", FormatPreset.BEST_VIDEO_AUDIO.value),
    ("MP4 up to 720p", FormatPreset.MP4_720P.value),
    ("MP4 up to 1080p", FormatPreset.MP4_1080P.value),
    ("Best audio only", FormatPreset.BEST_AUDIO.value),
    ("MP3 (audio extract)", FormatPreset.MP3_AUDIO.value),
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

        self.setWindowTitle(APP_NAME)
        self.resize(config.window_width, config.window_height)

        self._mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self._update_thread: QThread | None = None
        self._update_worker: UpdateWorker | None = None
        self._update_check_manual = False
        self._build_ui()
        self._build_menu()
        self._apply_config()
        self._setup_worker()
        self._apply_state(WorkerState.IDLE)
        self._maybe_check_updates_on_startup()

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

    def _build_menu(self) -> None:
        menubar = self.menuBar()
        options_menu = menubar.addMenu("&Options")

        check_updates_action = QAction("Check for &updates…", self)
        check_updates_action.triggered.connect(self._on_check_updates)
        options_menu.addAction(check_updates_action)

        self._auto_check_action = QAction("Check for updates on startup", self)
        self._auto_check_action.setCheckable(True)
        self._auto_check_action.setChecked(self._config.check_updates_on_startup)
        self._auto_check_action.toggled.connect(self._on_toggle_auto_check)
        options_menu.addAction(self._auto_check_action)

        options_menu.addSeparator()

        about_action = QAction(f"&About {APP_NAME}", self)
        about_action.triggered.connect(self._on_about)
        options_menu.addAction(about_action)

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
        self._worker.item_started.connect(self._on_item_started)
        self._worker.item_finished.connect(self._on_item_finished)
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

        self._config.output_dir = str(out)
        self._config.format_preset = preset
        self._config.custom_format = custom

        self.log_view.clear()
        self.overall_label.setText("")
        self.request_download.emit(DownloadRequest(urls=urls, format_spec=spec, output_dir=out))

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
            self.status_label.setText("<b>SUCCESS!</b>")
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
            self.status_label.setText("<b>Cancelled.</b>")

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

    def _on_item_started(self, index: int, total: int, url: str) -> None:
        self.overall_label.setText(f"Item {index} / {total}")
        self.log_view.append(f"[info] starting ({index}/{total}): {url}")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(0)

    def _on_item_finished(self, _index: int, output_path: Path | None) -> None:
        if output_path:
            self.log_view.append(f"[info] saved: {output_path}")

    def _on_finished(self, output_paths: list[Path]) -> None:
        if output_paths:
            self.log_view.append(f"[info] queue done — {len(output_paths)} file(s) saved")

    def _on_failed(self, kind: ErrorKind, message: str, traceback_str: str) -> None:
        self.status_label.setText(f"<b>Error:</b> {message}")
        self.log_view.append(f"[error] {message}")
        hint = ""
        if kind == ErrorKind.EXTRACTOR:
            hint = (
                "\n\nThis often means yt-dlp needs an update — the site's format may have changed."
            )
        QMessageBox.critical(self, APP_NAME, message + hint)

    # --- Update check -------------------------------------------------------

    def _maybe_check_updates_on_startup(self) -> None:
        if not self._config.check_updates_on_startup:
            return
        last = self._config.last_update_check_iso
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
            except ValueError:
                last_dt = None
            if last_dt and datetime.now(timezone.utc) - last_dt < _UPDATE_CHECK_INTERVAL:
                return
        self._start_update_check(manual=False)

    def _on_check_updates(self) -> None:
        self._start_update_check(manual=True)

    def _on_toggle_auto_check(self, checked: bool) -> None:
        self._config.check_updates_on_startup = checked

    def _start_update_check(self, *, manual: bool) -> None:
        if self._update_thread is not None:
            if manual:
                QMessageBox.information(self, APP_NAME, "An update check is already in progress.")
            return

        self._update_check_manual = manual
        self._update_thread = QThread(self)
        self._update_worker = UpdateWorker(__version__)
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._on_update_finished)
        self._update_worker.failed.connect(self._on_update_failed)
        self._update_thread.start()

    def _cleanup_update_thread(self) -> None:
        if self._update_thread is not None:
            self._update_thread.quit()
            self._update_thread.wait(2000)
            self._update_thread = None
            self._update_worker = None

    def _on_update_finished(self, info: UpdateInfo) -> None:
        manual = self._update_check_manual
        self._config.last_update_check_iso = datetime.now(timezone.utc).isoformat()
        self._cleanup_update_thread()

        if not info.is_newer:
            if manual:
                QMessageBox.information(
                    self,
                    APP_NAME,
                    f"You're up to date.\n\nCurrent version: {info.current}",
                )
            return

        if not manual and info.latest == self._config.skip_version:
            return

        self._prompt_update(info, manual=manual)

    def _on_update_failed(self, message: str) -> None:
        manual = self._update_check_manual
        self._cleanup_update_thread()
        if manual:
            QMessageBox.warning(self, APP_NAME, f"Could not check for updates:\n{message}")

    def _prompt_update(self, info: UpdateInfo, *, manual: bool) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(APP_NAME)
        box.setIcon(QMessageBox.Icon.Information)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(
            f"<b>A new version is available.</b><br><br>"
            f"Current: {info.current}<br>"
            f"Latest: <b>{info.latest}</b>"
        )
        notes = info.notes.strip()
        if notes:
            box.setInformativeText(notes[:600] + ("…" if len(notes) > 600 else ""))
        view_btn = box.addButton("View release", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        skip_btn = None
        if not manual:
            skip_btn = box.addButton("Skip this version", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(view_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked is view_btn:
            QDesktopServices.openUrl(info.url)  # type: ignore[arg-type]
        elif skip_btn is not None and clicked is skip_btn:
            self._config.skip_version = info.latest
        # later_btn: do nothing

    def _on_about(self) -> None:
        AboutDialog(self).exec()

    # --- Lifecycle ----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        self._config.window_width = self.width()
        self._config.window_height = self.height()
        if self._thread.isRunning():
            self._worker.cancel()
            self._thread.quit()
            self._thread.wait(2000)
        self._cleanup_update_thread()
        super().closeEvent(event)
