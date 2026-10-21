"""Tests for downloader internals — no network calls."""
from __future__ import annotations

import os
import urllib.error
from pathlib import Path

import pytest

from super_dl.core.downloader import (
    DownloadRequest,
    ErrorKind,
    WorkerState,
    YtDlpWorker,
    _classify,
    prune_unresolvable_path_entries,
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


def test_download_request_defaults_to_no_cookies(tmp_path: Path):
    req = DownloadRequest(
        urls=("https://example.com",),
        format_spec=FormatSpec("b"),
        output_dir=tmp_path,
    )
    assert req.cookies_from_browser == ""


def test_download_request_carries_cookie_browser(tmp_path: Path):
    req = DownloadRequest(
        urls=("https://example.com",),
        format_spec=FormatSpec("b"),
        output_dir=tmp_path,
        cookies_from_browser="firefox",
    )
    assert req.cookies_from_browser == "firefox"


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


class _FakeMergingYoutubeDL:
    """Replays the hook order yt-dlp uses for a bv+ba download that gets merged."""

    def __init__(self, opts: dict) -> None:
        self._opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def download(self, urls: list[str]) -> None:
        out = Path(self._opts["outtmpl"]).parent
        for hook in self._opts["progress_hooks"]:
            hook({"status": "finished", "filename": str(out / "clip.f251.webm")})
        for hook in self._opts["post_hooks"]:
            hook(str(out / "clip.webm"))


def test_worker_reports_merged_output_not_intermediate(qtbot, tmp_path: Path, monkeypatch):
    import yt_dlp

    monkeypatch.setattr(yt_dlp, "YoutubeDL", _FakeMergingYoutubeDL)
    w = YtDlpWorker()
    req = DownloadRequest(
        urls=("https://example.com/v",),
        format_spec=FormatSpec("bv*+ba/b"),
        output_dir=tmp_path,
    )
    with qtbot.waitSignal(w.finished) as blocker:
        w.start(req)
    assert blocker.args == [[tmp_path / "clip.webm"]]


def test_classify_extractor_error():
    from yt_dlp.utils import ExtractorError

    assert _classify(ExtractorError("no extractor")) == ErrorKind.EXTRACTOR


def test_classify_urllib_error_is_network():
    assert _classify(urllib.error.URLError("connection refused")) == ErrorKind.NETWORK


def test_classify_plain_oserror_is_filesystem():
    assert _classify(OSError("disk full")) == ErrorKind.FILESYSTEM


def test_classify_unknown_falls_through():
    assert _classify(ValueError("nope")) == ErrorKind.UNKNOWN


def test_classify_cookie_load_error():
    from yt_dlp.cookies import CookieLoadError

    assert _classify(CookieLoadError("failed to load cookies")) == ErrorKind.COOKIES


def test_classify_cookie_error_wins_over_wrapped_oserror():
    from yt_dlp.cookies import CookieLoadError

    try:
        try:
            raise PermissionError("cookie db locked")
        except PermissionError:
            raise CookieLoadError("failed to load cookies") from None
    except CookieLoadError as e:
        assert _classify(e) == ErrorKind.COOKIES
    else:
        pytest.fail("expected CookieLoadError")


def test_classify_cookie_message_fallback():
    assert _classify(RuntimeError("failed to load cookies")) == ErrorKind.COOKIES


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


def test_prune_drops_unresolvable_path_entries(monkeypatch, tmp_path: Path):
    good = tmp_path / "good"
    untrusted = tmp_path / "untrusted"
    monkeypatch.setenv("PATH", os.pathsep.join([str(good), str(untrusted)]))
    real_resolve = Path.resolve

    def fake_resolve(self, strict=False):
        if self == untrusted:
            raise OSError("The path cannot be traversed (WinError 448)")
        return real_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", fake_resolve)
    prune_unresolvable_path_entries()
    assert os.environ["PATH"] == str(good)


def test_prune_leaves_resolvable_path_untouched(monkeypatch, tmp_path: Path):
    original = os.pathsep.join([str(tmp_path / "a"), "", str(tmp_path / "b")])
    monkeypatch.setenv("PATH", original)
    prune_unresolvable_path_entries()
    assert os.environ["PATH"] == original
