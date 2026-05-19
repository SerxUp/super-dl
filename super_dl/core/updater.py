from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from super_dl import GITHUB_REPO

logger = logging.getLogger(__name__)

RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
DEFAULT_TIMEOUT_SECONDS = 5.0


class UpdateCheckError(Exception):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    url: str
    notes: str
    is_newer: bool


def _normalize(tag: str) -> str:
    return tag.lstrip("vV").strip()


def _compare(current: str, latest: str) -> bool:
    """Return True if latest > current. Uses packaging.version when available,
    falls back to tuple comparison of numeric components."""
    try:
        from packaging.version import InvalidVersion, Version

        try:
            return Version(latest) > Version(current)
        except InvalidVersion:
            pass
    except ImportError:
        pass

    def parts(v: str) -> tuple[int, ...]:
        out: list[int] = []
        for chunk in v.split("."):
            num = ""
            for ch in chunk:
                if ch.isdigit():
                    num += ch
                else:
                    break
            out.append(int(num) if num else 0)
        return tuple(out)

    return parts(latest) > parts(current)


def check_for_update(
    current_version: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    url: str = RELEASES_API_URL,
) -> UpdateInfo:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"super-dl/{current_version}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        raise UpdateCheckError(str(e)) from e

    tag = payload.get("tag_name")
    if not tag:
        raise UpdateCheckError("Release payload missing tag_name")

    latest = _normalize(tag)
    return UpdateInfo(
        current=current_version,
        latest=latest,
        url=payload.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"),
        notes=payload.get("body", "") or "",
        is_newer=_compare(current_version, latest),
    )
