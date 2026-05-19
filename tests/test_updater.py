from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from super_dl.core.updater import (
    UpdateCheckError,
    _compare,
    check_for_update,
)


def _fake_response(payload: dict) -> io.BytesIO:
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def test_compare_basic():
    assert _compare("0.1.0", "0.2.0") is True
    assert _compare("0.2.0", "0.2.0") is False
    assert _compare("0.2.1", "0.2.0") is False
    assert _compare("0.2.0", "0.10.0") is True


def test_compare_with_v_prefix_stripped_by_caller():
    # caller strips "v" prefix via _normalize before passing here
    assert _compare("1.0.0", "1.0.1") is True


def test_check_for_update_returns_newer():
    payload = {
        "tag_name": "v0.3.0",
        "html_url": "https://github.com/x/y/releases/tag/v0.3.0",
        "body": "Bugfixes",
    }
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)) as m:
        info = check_for_update("0.2.0")
    assert m.called
    assert info.current == "0.2.0"
    assert info.latest == "0.3.0"
    assert info.is_newer is True
    assert info.url.endswith("v0.3.0")
    assert info.notes == "Bugfixes"


def test_check_for_update_returns_same_version():
    payload = {"tag_name": "0.2.0", "html_url": "u", "body": ""}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        info = check_for_update("0.2.0")
    assert info.is_newer is False


def test_check_for_update_strips_v_prefix():
    payload = {"tag_name": "v1.2.3", "html_url": "u", "body": ""}
    with patch("urllib.request.urlopen", return_value=_fake_response(payload)):
        info = check_for_update("1.2.2")
    assert info.latest == "1.2.3"
    assert info.is_newer is True


def test_check_for_update_network_error_raises():
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("boom"),
    ), pytest.raises(UpdateCheckError):
        check_for_update("0.1.0")


def test_check_for_update_bad_json_raises():
    with patch(
        "urllib.request.urlopen",
        return_value=io.BytesIO(b"not json"),
    ), pytest.raises(UpdateCheckError):
        check_for_update("0.1.0")


def test_check_for_update_missing_tag_raises():
    with patch(
        "urllib.request.urlopen",
        return_value=_fake_response({"html_url": "u"}),
    ), pytest.raises(UpdateCheckError):
        check_for_update("0.1.0")
