"""Bump the yt-dlp floor and the app's patch version when PyPI has a newer yt-dlp.

Run weekly by ``.github/workflows/yt-dlp-release.yml``. Stdlib-only so it can
run before the project's dependencies are installed.

Usage:
    python scripts/bump_ytdlp.py [--dry-run] [--latest VERSION]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"

PYPROJECT = Path("pyproject.toml")
FLOOR_RE = re.compile(r'"yt-dlp\[default\]>=(?P<v>[^"]+)"')
VERSION_FILES = (
    (PYPROJECT, re.compile(r'^version = "(?P<v>[^"]+)"', re.M)),
    (Path("super_dl/__init__.py"), re.compile(r'^__version__ = "(?P<v>[^"]+)"', re.M)),
    (Path("installer/super-dl.iss"), re.compile(r'#define AppVersion "(?P<v>[^"]+)"')),
)


def _match(path: Path, pattern: re.Pattern[str]) -> tuple[str, re.Match[str]]:
    # Exactly one match, or fail loudly: an unattended release must never
    # silently skip a file because someone reformatted it.
    text = path.read_text(encoding="utf-8", newline="")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"{path}: expected 1 match for {pattern.pattern!r}, got {len(matches)}")
    return text, matches[0]


def read_value(path: Path, pattern: re.Pattern[str]) -> str:
    return _match(path, pattern)[1].group("v")


def _replace_value(path: Path, pattern: re.Pattern[str], new: str) -> None:
    text, m = _match(path, pattern)
    path.write_text(text[: m.start("v")] + new + text[m.end("v") :], encoding="utf-8", newline="")


def version_key(version: str) -> tuple[int, ...]:
    # PyPI reports yt-dlp as e.g. 2026.8.19, upstream tags as 2026.08.19.
    return tuple(int(part) for part in re.findall(r"\d+", version))


def next_patch(version: str) -> str:
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


def bump(root: Path, latest: str, *, write: bool = True) -> str | None:
    """Return the new app version if `latest` is newer than the yt-dlp floor, else None."""
    if version_key(latest) <= version_key(read_value(root / PYPROJECT, FLOOR_RE)):
        return None

    versions = {str(rel): read_value(root / rel, pattern) for rel, pattern in VERSION_FILES}
    if len(set(versions.values())) != 1:
        raise SystemExit(f"app versions disagree: {versions}")
    new_version = next_patch(versions[str(PYPROJECT)])

    if write:
        _replace_value(root / PYPROJECT, FLOOR_RE, latest)
        for rel, pattern in VERSION_FILES:
            _replace_value(root / rel, pattern, new_version)
    return new_version


def latest_ytdlp() -> str:
    with urllib.request.urlopen(PYPI_URL, timeout=30) as resp:
        return json.load(resp)["info"]["version"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report without editing files")
    parser.add_argument("--latest", help="yt-dlp version to bump to (default: latest on PyPI)")
    args = parser.parse_args()

    latest = args.latest or latest_ytdlp()
    new_version = bump(ROOT, latest, write=not args.dry_run)
    if new_version is None:
        print(f"yt-dlp {latest} is not newer than the pyproject floor; nothing to do")
    else:
        print(f"yt-dlp -> {latest}, super-dl -> {new_version}")

    if gh_output := os.environ.get("GITHUB_OUTPUT"):
        with Path(gh_output).open("a", encoding="utf-8") as f:
            f.write(f"bumped={'true' if new_version else 'false'}\n")
            f.write(f"version={new_version or ''}\n")
            f.write(f"ytdlp={latest}\n")


if __name__ == "__main__":
    main()
