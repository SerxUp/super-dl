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
from super_dl.core.formats import FormatSpec


def test_download_request_holds_values(tmp_path: Path):
    spec = FormatSpec("ba/b")
    req = DownloadRequest(
        urls=("https://example.com/a", "https://example.com/b"),
        format_spec=spec,
        output_dir=tmp_path,
    )
    assert req.urls == ("https://example.com/a", "https://example.com/b")
    assert req.format_spec is spec
    assert req.output_dir == tmp_path


def test_download_request_accepts_single_url_tuple(tmp_path: Path):
    req = DownloadRequest(
        urls=("https://example.com",),
        format_spec=FormatSpec("bv*+ba/b"),
        output_dir=tmp_path,
    )
    assert len(req.urls) == 1


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
