"""Tests for scripts/bump_ytdlp.py — run against copies of the real release files."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

from super_dl import __version__

ROOT = Path(__file__).resolve().parent.parent
RELEASE_FILES = ("pyproject.toml", "super_dl/__init__.py", "installer/super-dl.iss")

_spec = importlib.util.spec_from_file_location("bump_ytdlp", ROOT / "scripts" / "bump_ytdlp.py")
bump_ytdlp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bump_ytdlp)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel in RELEASE_FILES:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dst)
    return tmp_path


def _snapshot(root: Path) -> dict[str, bytes]:
    return {rel: (root / rel).read_bytes() for rel in RELEASE_FILES}


def _floor(root: Path) -> str:
    return bump_ytdlp.read_value(root / "pyproject.toml", bump_ytdlp.FLOOR_RE)


def test_next_patch():
    assert bump_ytdlp.next_patch("0.4.1") == "0.4.2"
    assert bump_ytdlp.next_patch("1.2.9") == "1.2.10"


def test_version_key_ignores_zero_padding():
    assert bump_ytdlp.version_key("2026.08.19") == bump_ytdlp.version_key("2026.8.19")
    assert bump_ytdlp.version_key("2026.10.2") > bump_ytdlp.version_key("2026.9.30")


def test_no_bump_when_latest_equals_floor(repo: Path):
    before = _snapshot(repo)
    assert bump_ytdlp.bump(repo, _floor(repo)) is None
    assert _snapshot(repo) == before


def test_no_bump_when_latest_is_older(repo: Path):
    assert bump_ytdlp.bump(repo, "2000.1.1") is None


def test_bump_updates_floor_and_every_version_file(repo: Path):
    expected = bump_ytdlp.next_patch(__version__)
    assert bump_ytdlp.bump(repo, "2999.1.1") == expected
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert '"yt-dlp[default]>=2999.1.1"' in pyproject
    assert f'version = "{expected}"' in pyproject
    assert f'__version__ = "{expected}"' in (repo / "super_dl/__init__.py").read_text()
    assert f'#define AppVersion "{expected}"' in (repo / "installer/super-dl.iss").read_text()


def test_dry_run_reports_without_writing(repo: Path):
    before = _snapshot(repo)
    assert bump_ytdlp.bump(repo, "2999.1.1", write=False) == bump_ytdlp.next_patch(__version__)
    assert _snapshot(repo) == before


def test_disagreeing_versions_abort(repo: Path):
    iss = repo / "installer/super-dl.iss"
    iss.write_text(iss.read_text().replace(__version__, "9.9.9"))
    with pytest.raises(SystemExit, match="disagree"):
        bump_ytdlp.bump(repo, "2999.1.1")
