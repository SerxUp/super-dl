"""Tests for downloader internals — no network calls."""
from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

from super_dl.core.downloader import (
    DownloadRequest,
    ErrorKind,
    WorkerState,
    YtDlpWorker,
    _classify,
)


def test_download_request_holds_values(tmp_path: Path):
    req = DownloadRequest(url="https://example.com", format_selector="ba/b", output_dir=tmp_path)
    assert req.url == "https://example.com"
    assert req.format_selector == "ba/b"
    assert req.output_dir == tmp_path


def test_worker_state_values_are_unique():
    seen = set()
    for s in WorkerState:
        assert s.value not in seen
        seen.add(s.value)


def test_cancel_sets_event(qtbot):  # qtbot provides a QApplication
    w = YtDlpWorker()
    assert not w._cancel_event.is_set()
    w.cancel()
    assert w._cancel_event.is_set()


def test_classify_extractor_error():
    from yt_dlp.utils import ExtractorError

    assert _classify(ExtractorError("no extractor")) == ErrorKind.EXTRACTOR


def test_classify_urllib_error_is_network():
    assert _classify(urllib.error.URLError("connection refused")) == ErrorKind.NETWORK


def test_classify_plain_oserror_is_filesystem():
    assert _classify(OSError("disk full")) == ErrorKind.FILESYSTEM


def test_classify_unknown_falls_through():
    assert _classify(ValueError("nope")) == ErrorKind.UNKNOWN


def test_classify_walks_cause_chain():
    from yt_dlp.utils import ExtractorError

    try:
        try:
            raise ExtractorError("upstream")
        except ExtractorError as inner:
            raise RuntimeError("wrapped") from inner
    except RuntimeError as wrapped:
        assert _classify(wrapped) == ErrorKind.EXTRACTOR
    else:
        pytest.fail("expected RuntimeError")
