from __future__ import annotations

import sys

from yt_dlp.cookies import SUPPORTED_BROWSERS

from super_dl.core.cookies import (
    NO_BROWSER,
    available_browsers,
    display_name,
    normalize_browser,
)


def test_available_browsers_are_all_supported_by_ytdlp():
    assert set(available_browsers()) <= set(SUPPORTED_BROWSERS)


def test_common_browsers_are_offered_first():
    browsers = available_browsers()
    assert browsers[:3] == ("firefox", "chrome", "edge")


def test_safari_only_on_macos():
    assert ("safari" in available_browsers()) == (sys.platform == "darwin")


def test_normalize_accepts_known_browser():
    assert normalize_browser("firefox") == "firefox"


def test_normalize_is_case_and_space_insensitive():
    assert normalize_browser("  Firefox ") == "firefox"


def test_normalize_rejects_unknown_browser():
    assert normalize_browser("netscape") == NO_BROWSER


def test_normalize_rejects_platform_unavailable_browser():
    if sys.platform == "darwin":
        assert normalize_browser("safari") == "safari"
    else:
        assert normalize_browser("safari") == NO_BROWSER


def test_normalize_empty_is_no_browser():
    assert normalize_browser("") == NO_BROWSER


def test_every_available_browser_has_a_display_name():
    for browser in available_browsers():
        assert display_name(browser)[0].isupper()
