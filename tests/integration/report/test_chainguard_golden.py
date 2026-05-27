# tests/integration/report/test_legacy_example_golden.py
"""Golden-output test: build_report against the legacy_example fixture must
produce byte-identical data.js to the checked-in fixture.

Update protocol: when a transform changes intentionally, run
`python -m apd_gauntlet build-report runs/apd-legacy-example-run
--out /tmp/golden && cp /tmp/golden/data.js tests/fixtures/report-html/
legacy_example-golden-data.js` and commit alongside the transform change.
"""
from __future__ import annotations

import difflib
import pathlib

import pytest
from apd_gauntlet.report.build import build_report

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURE_RUN = REPO / "runs" / "apd-legacy-example-run"
GOLDEN = REPO / "tests" / "fixtures" / "report-html" / "legacy_example-golden-data.js"

pytestmark = pytest.mark.skipif(
    not (REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "index.html").exists(),
    reason="precompiled bundle not present",
)


def test_data_js_matches_golden(tmp_path: pathlib.Path) -> None:
    out = build_report(FIXTURE_RUN, out_dir=tmp_path)
    actual = (out / "data.js").read_text()
    expected = GOLDEN.read_text()
    if actual != expected:
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), actual.splitlines(),
            fromfile="golden", tofile="actual", n=3, lineterm="",
        ))
        pytest.fail(
            "data.js differs from golden — if intentional, update "
            f"{GOLDEN.relative_to(REPO)} and commit. Diff:\n{diff[:4000]}"
        )


def test_all_expected_files_present(tmp_path: pathlib.Path) -> None:
    out = build_report(FIXTURE_RUN, out_dir=tmp_path)
    expected = {
        "index.html", "app.js", "data.js", "styles.css", "screens.css",
        "mermaid.min.js", "vendor-licenses.txt", "build-manifest.txt",
    }
    actual = {p.name for p in out.iterdir() if p.is_file()}
    missing = expected - actual
    assert not missing, f"missing files in bundle output: {missing}"
