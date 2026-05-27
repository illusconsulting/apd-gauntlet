# tests/unit/report/test_emit.py
from __future__ import annotations

import json
import pathlib
import re

import pytest

from apd_gauntlet.report.emit import (
    BundleMissingError,
    write_data_js,
    copy_bundle,
    write_manifest,
)


def test_write_data_js_round_trips_dict(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "data.js"
    write_data_js({"meta": {"run_id": "test-run"}, "summary": {}}, out)
    text = out.read_text()
    assert text.startswith("window.APD_DATA = ")
    # Strip the wrapper, parse the JSON body.
    body = re.sub(r"^window\.APD_DATA = ", "", text)
    body = body.rstrip(";\n")
    parsed = json.loads(body)
    assert parsed["meta"]["run_id"] == "test-run"


def test_write_data_js_preserves_unicode(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "data.js"
    write_data_js({"x": "ñ é · ◆"}, out)
    body = out.read_text()
    assert "ñ" in body  # not escaped


def test_copy_bundle_copies_every_file(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.html").write_text("<!doctype html>")
    (src / "app.js").write_text("// app")
    (src / "fonts").mkdir()
    (src / "fonts" / "a.woff2").write_bytes(b"\x00")
    dst = tmp_path / "dst"
    copy_bundle(src, dst)
    assert (dst / "index.html").exists()
    assert (dst / "app.js").exists()
    assert (dst / "fonts" / "a.woff2").exists()


def test_copy_bundle_missing_source_raises(tmp_path: pathlib.Path) -> None:
    with pytest.raises(BundleMissingError):
        copy_bundle(tmp_path / "does-not-exist", tmp_path / "dst")


def test_write_manifest_includes_hashes(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "build-manifest.txt"
    write_manifest(
        out,
        framework_version="1.5.0",
        source_hashes={"deduped-findings.yaml": "abc", "report-data.yaml": "def"},
        bundle_hash="bundle123",
    )
    text = out.read_text()
    assert "framework_version=1.5.0" in text
    assert "deduped-findings.yaml=abc" in text
    assert "bundle_hash=bundle123" in text
