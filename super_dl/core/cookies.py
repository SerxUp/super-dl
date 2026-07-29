"""Browser choices for yt-dlp's `cookiesfrombrowser` option.

The option value itself is passed straight through to `YoutubeDL`; this module
only holds the picker data (which browsers exist on this platform, how to label
them) so the UI has something to offer and bad values can't reach yt-dlp.
"""
from __future__ import annotations

import sys

from yt_dlp.cookies import SUPPORTED_BROWSERS

NO_BROWSER = ""

# Most commonly used first; browsers yt-dlp adds later still appear, appended
# alphabetically, so the picker doesn't need a code change to stay complete.
_PREFERRED_ORDER: tuple[str, ...] = (
    "firefox",
    "chrome",
    "edge",
    "brave",
    "chromium",
    "opera",
    "vivaldi",
    "safari",
    "whale",
)

BROWSER_DISPLAY: dict[str, str] = {
    "brave": "Brave",
    "chrome": "Google Chrome",
    "chromium": "Chromium",
    "edge": "Microsoft Edge",
    "firefox": "Mozilla Firefox",
    "opera": "Opera",
    "safari": "Safari",
    "vivaldi": "Vivaldi",
    "whale": "Naver Whale",
}


def available_browsers() -> tuple[str, ...]:
    supported = set(SUPPORTED_BROWSERS)
    if sys.platform != "darwin":
        supported.discard("safari")
    ordered = [b for b in _PREFERRED_ORDER if b in supported]
    ordered += sorted(supported.difference(ordered))
    return tuple(ordered)


def display_name(browser: str) -> str:
    return BROWSER_DISPLAY.get(browser, browser.capitalize())


def normalize_browser(value: str) -> str:
    """Coerce a stored/user value to a browser usable here, else `NO_BROWSER`."""
    candidate = (value or "").strip().lower()
    return candidate if candidate in available_browsers() else NO_BROWSER
