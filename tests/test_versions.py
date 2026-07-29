from __future__ import annotations

import re

from super_dl.core import versions

VERSION_RE = re.compile(r"^\d+")


def test_dependency_versions_covers_every_runtime_dependency():
    assert set(versions.dependency_versions()) == {
        "yt-dlp",
        "PySide6",
        "imageio-ffmpeg",
        "platformdirs",
    }


def test_dependency_versions_are_resolved():
    for name, value in versions.dependency_versions().items():
        assert value != versions.UNKNOWN, name
        assert VERSION_RE.match(value), (name, value)


def test_missing_distribution_falls_back_to_module_attribute():
    assert versions.package_version("not-a-real-dist", "platformdirs") == versions.package_version(
        "platformdirs"
    )


def test_missing_distribution_and_module_reports_unknown():
    assert versions.package_version("not-a-real-dist", "not_a_real_module") == versions.UNKNOWN
    assert versions.package_version("not-a-real-dist") == versions.UNKNOWN


def test_python_and_qt_versions_are_dotted_numbers():
    assert VERSION_RE.match(versions.python_version())
    assert VERSION_RE.match(versions.qt_version())
