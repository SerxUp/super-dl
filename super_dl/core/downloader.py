from __future__ import annotations

import contextlib
import logging
import threading
import traceback
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import yt_dlp
from PySide6.QtCore import QObject, Signal, Slot
from yt_dlp.utils import DownloadCancelled, DownloadError, ExtractorError
from yt_dlp.utils import Popen as _YdlPopen

from super_dl.core.formats import FormatSpec
from super_dl.core.paths import ffmpeg_path

logger = logging.getLogger(__name__)


class WorkerState(Enum):
    IDLE = auto()
    EXTRACTING = auto()
    DOWNLOADING = auto()
    POSTPROCESSING = auto()
    DONE = auto()
    ERROR = auto()
    CANCELLED = auto()


class ErrorKind(Enum):
    EXTRACTOR = auto()   # site/extractor broke — yt-dlp likely needs an update
    NETWORK = auto()
    FILESYSTEM = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class DownloadRequest:
    urls: tuple[str, ...]
    format_spec: FormatSpec
    output_dir: Path
    subfolder_per_url: bool = False


_SUBFOLDER_TEMPLATE = "%(playlist_title,channel,uploader,title)s"


def _classify(exc: BaseException) -> ErrorKind:
    cur: BaseException | None = exc
    seen: set[int] = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, ExtractorError):
            return ErrorKind.EXTRACTOR
        if isinstance(cur, urllib.error.URLError):
            return ErrorKind.NETWORK
        if isinstance(cur, OSError):
            return ErrorKind.FILESYSTEM
        cur = cur.__cause__ or cur.__context__
    msg = str(exc).lower()
    if "http error" in msg or "unable to download" in msg or "name or service" in msg:
        return ErrorKind.NETWORK
    return ErrorKind.UNKNOWN


class _YdlLogAdapter:
    """Bridge yt-dlp's logger protocol to a Python logger + a Qt signal callback."""

    def __init__(self, emit: Callable[[int, str], None]) -> None:
        self._emit = emit
        self._py = logging.getLogger("yt_dlp")

    def debug(self, msg: str) -> None:
        # yt-dlp routes info-level messages through debug() unless prefixed.
        if msg.startswith("[debug] "):
            self._py.debug(msg)
        else:
            self._py.info(msg)
            self._emit(logging.INFO, msg)

    def info(self, msg: str) -> None:
        self._py.info(msg)
        self._emit(logging.INFO, msg)

    def warning(self, msg: str) -> None:
        self._py.warning(msg)
        self._emit(logging.WARNING, msg)

    def error(self, msg: str) -> None:
        self._py.error(msg)
        self._emit(logging.ERROR, msg)


class YtDlpWorker(QObject):
    state_changed = Signal(object)                # WorkerState
    progress = Signal(int, object, object, object)  # downloaded, total|None, speed|None, eta|None
    log_line = Signal(int, str)                   # logging level, message
    item_started = Signal(int, int, str)          # index (1-based), total, url
    item_finished = Signal(int, object)           # index (1-based), output_path | None
    finished = Signal(object)                     # list[Path] of completed item outputs
    failed = Signal(object, str, str)             # ErrorKind, message, traceback

    def __init__(self) -> None:
        super().__init__()
        self._cancel_event = threading.Event()
        self._state = WorkerState.IDLE
        # Subprocesses (ffmpeg, etc.) spawned by yt-dlp during the active item.
        # Populated via a scoped Popen patch in start(); read by cancel() to
        # terminate in-flight post-processing without waiting for hook ticks.
        self._active_procs: set[_YdlPopen] = set()
        self._procs_lock = threading.Lock()

    def cancel(self) -> None:
        # Thread-safe: sets an Event for hook-driven aborts, and terminates any
        # tracked subprocesses so ffmpeg post-processing cancels immediately.
        self._cancel_event.set()
        with self._procs_lock:
            procs = list(self._active_procs)
        for p in procs:
            with contextlib.suppress(Exception):
                p.terminate()

    @Slot(object)
    def start(self, request: DownloadRequest) -> None:
        self._cancel_event.clear()
        completed: list[Path] = []
        total_items = len(request.urls)

        for idx, url in enumerate(request.urls, start=1):
            if self._cancel_event.is_set():
                self._set_state(WorkerState.CANCELLED)
                self.finished.emit(completed)
                return

            self.item_started.emit(idx, total_items, url)
            self._set_state(WorkerState.EXTRACTING)
            captured: list[Path | None] = [None]

            def progress_hook(d: dict, _captured: list = captured) -> None:
                if self._cancel_event.is_set():
                    raise DownloadCancelled
                status = d.get("status")
                if status == "downloading":
                    if self._state != WorkerState.DOWNLOADING:
                        self._set_state(WorkerState.DOWNLOADING)
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    self.progress.emit(
                        int(d.get("downloaded_bytes") or 0),
                        int(total) if total else None,
                        d.get("speed"),
                        d.get("eta"),
                    )
                elif status == "finished":
                    fp = d.get("filename")
                    if fp:
                        _captured[0] = Path(fp)

            def postprocessor_hook(d: dict) -> None:
                if self._cancel_event.is_set():
                    raise DownloadCancelled
                if d.get("status") == "started":
                    self._set_state(WorkerState.POSTPROCESSING)

            outtmpl_path = (
                request.output_dir / _SUBFOLDER_TEMPLATE / "%(title)s.%(ext)s"
                if request.subfolder_per_url
                else request.output_dir / "%(title)s.%(ext)s"
            )
            ydl_opts: dict = {
                "format": request.format_spec.selector,
                "outtmpl": str(outtmpl_path),
                "ffmpeg_location": ffmpeg_path(),
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "logger": _YdlLogAdapter(self.log_line.emit),
                "noprogress": True,
                "quiet": True,
                # Bound the extraction-phase worst case so cancel and failure
                # paths regain control quickly when the network stalls.
                "socket_timeout": 15,
                "retries": 2,
                "fragment_retries": 2,
                "extractor_retries": 2,
            }
            if request.format_spec.merge_output_format:
                ydl_opts["merge_output_format"] = request.format_spec.merge_output_format
            if request.format_spec.postprocessors:
                ydl_opts["postprocessors"] = list(request.format_spec.postprocessors)

            try:
                with self._track_subprocesses(), yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except DownloadCancelled:
                self._set_state(WorkerState.CANCELLED)
                self.item_finished.emit(idx, None)
                self.finished.emit(completed)
                return
            except Exception as e:  # noqa: BLE001 — consolidated catch-all
                if self._cancel_event.is_set():
                    self._set_state(WorkerState.CANCELLED)
                    self.item_finished.emit(idx, None)
                    self.finished.emit(completed)
                    return
                self.item_finished.emit(idx, None)
                if isinstance(e, (DownloadError, ExtractorError, OSError)):
                    self._fail(_classify(e), str(e))
                else:
                    self._fail(ErrorKind.UNKNOWN, str(e) or type(e).__name__)
                return

            item_path = captured[0]
            if item_path is not None:
                completed.append(item_path)
            self.item_finished.emit(idx, item_path)

        self._set_state(WorkerState.DONE)
        self.finished.emit(completed)

    @contextlib.contextmanager
    def _track_subprocesses(self):
        """Patch yt_dlp.utils.Popen for the lifetime of one ydl.download() call
        so that ffmpeg (and any other subprocess yt-dlp launches via its Popen
        subclass) is registered in `self._active_procs` and can be terminated
        synchronously by `cancel()`."""
        orig_init = _YdlPopen.__init__
        active = self._active_procs
        lock = self._procs_lock

        def tracked_init(proc_self, *args, **kwargs):
            orig_init(proc_self, *args, **kwargs)
            with lock:
                active.add(proc_self)

        _YdlPopen.__init__ = tracked_init
        try:
            yield
        finally:
            _YdlPopen.__init__ = orig_init
            with lock:
                active.clear()

    def _set_state(self, new: WorkerState) -> None:
        self._state = new
        self.state_changed.emit(new)

    def _fail(self, kind: ErrorKind, message: str) -> None:
        tb = traceback.format_exc()
        logger.error("Download failed (%s): %s\n%s", kind.name, message, tb)
        self._set_state(WorkerState.ERROR)
        self.failed.emit(kind, message, tb)
