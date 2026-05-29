# tests/unit/report/test_tier2_atomicity.py
"""Regression tests for the atomic-write contract in emit.py."""
from __future__ import annotations

import json
import re

import pytest
from apd_gauntlet.report.emit import (
    _atomic_write_text,
    write_data_js,
    write_manifest,
)


def test_atomic_write_text_creates_target(tmp_path):
    target = tmp_path / "out.txt"
    _atomic_write_text(target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"
    # No leftover .tmp file.
    assert not (tmp_path / "out.txt.tmp").exists()


def test_atomic_write_text_overwrites_existing(tmp_path):
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    _atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"
    assert not (tmp_path / "out.txt.tmp").exists()


def test_atomic_write_text_cleans_up_tmp_on_failure(tmp_path, monkeypatch):
    """Simulate os.replace failing after the tmp file is written.
    The target must not exist; the tmp must be cleaned up."""
    target = tmp_path / "out.txt"

    def boom(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("apd_gauntlet.report.emit.os.replace", boom)
    with pytest.raises(OSError):
        _atomic_write_text(target, "x" * 1000)
    assert not target.exists()
    assert not (tmp_path / "out.txt.tmp").exists()


def test_write_data_js_atomic_payload(tmp_path):
    target = tmp_path / "data.js"
    write_data_js({"foo": "bar", "n": 42}, target)
    body = target.read_text(encoding="utf-8")
    assert body.startswith("window.APD_DATA = ")
    assert body.rstrip().endswith(";")
    json_body = re.sub(r"^window\.APD_DATA = ", "", body).rstrip(";\n")
    payload = json.loads(json_body)
    assert payload == {"foo": "bar", "n": 42}
    # No leftover tmp.
    assert not (tmp_path / "data.js.tmp").exists()


def test_write_manifest_atomic(tmp_path):
    target = tmp_path / "build-manifest.txt"
    write_manifest(
        target,
        framework_version="1.5.0",
        source_hashes={"deduped-findings.yaml": "abc"},
        bundle_hash="bundle123",
    )
    text = target.read_text(encoding="utf-8")
    assert "framework_version=1.5.0" in text
    assert "bundle_hash=bundle123" in text
    assert "deduped-findings.yaml=abc" in text
    assert not (tmp_path / "build-manifest.txt.tmp").exists()
