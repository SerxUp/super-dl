from __future__ import annotations

from pathlib import Path

from super_dl.core import paths


def test_config_dir_exists():
    p = paths.config_dir()
    assert isinstance(p, Path)
    assert p.exists()
    assert p.is_dir()


def test_log_dir_exists():
    p = paths.log_dir()
    assert p.exists()
    assert p.is_dir()


def test_default_download_dir_under_home():
    assert paths.default_download_dir() == Path.home() / "Downloads"


def test_bundle_root_in_dev_contains_core_package():
    # In dev (not frozen), bundle_root() = super_dl/ package dir
    assert (paths.bundle_root() / "core").is_dir()
