# tests/integration/report/test_example_golden.py
"""Golden-output test: build_report against the canonical example fixture must
produce byte-identical data.js to the checked-in fixture.

Update protocol: when a transform changes intentionally, run
`python -m apd_gauntlet build-report examples/apd-20260601-claim-event-bus/expected
--out /tmp/golden && cp /tmp/golden/data.js tests/fixtures/report-html/
claim-event-bus-golden-data.js` and commit alongside the transform change.
"""
from __future__ import annotations

import difflib
import pathlib
import re

import pytest
from apd_gauntlet.report.build import build_report
from apd_gauntlet.report.taxonomy import invalidate_all

REPO = pathlib.Path(__file__).resolve().parents[3]
CLAIM_RUN = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
HA_RUN = REPO / "examples" / "apd-20260612-home-assistant" / "expected"
# (fixture_run, golden_data_js) pairs. The claim-event-bus golden is a small,
# standalone fixture. The Home Assistant report's data.js is ~4 MB; rather than
# duplicate it as a second fixture, its golden IS the committed in-tree report
# data.js — regenerate the report (`apd-gauntlet build-report <run>`) and
# re-commit when a transform intentionally changes the output.
GOLDEN_CASES = [
    pytest.param(
        CLAIM_RUN,
        REPO / "tests" / "fixtures" / "report-html" / "claim-event-bus-golden-data.js",
        id="claim-event-bus",
    ),
    pytest.param(
        HA_RUN,
        HA_RUN / "40-synthesis" / "report-html" / "data.js",
        id="home-assistant",
    ),
]


@pytest.fixture(autouse=True)
def _fresh_taxonomy_cache():
    """The golden is a byte-exact comparison that includes resolved NIST/ATT&CK
    titles, so the build must use the real shipped catalog. Clear the taxonomy
    LRU caches first so a result primed/faked by an earlier test cannot make this
    comparison order-dependent."""
    invalidate_all()
    yield

# The report's "date" field falls back to the wall-clock build date when the run
# declares none (loader.py date fallback chain), so a frozen golden would drift
# every calendar day. Normalize it before the byte-comparison.
_DATE_RE = re.compile(r'("date":\s*)"\d{4}-\d{2}-\d{2}"')


def _normalize(text: str) -> str:
    return _DATE_RE.sub(r'\1"<DATE>"', text)

pytestmark = pytest.mark.skipif(
    not (REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "index.html").exists(),
    reason="precompiled bundle not present",
)


@pytest.mark.parametrize("fixture_run, golden", GOLDEN_CASES)
def test_data_js_matches_golden(
    tmp_path: pathlib.Path, fixture_run: pathlib.Path, golden: pathlib.Path
) -> None:
    out, _ = build_report(fixture_run, out_dir=tmp_path)
    actual = _normalize((out / "data.js").read_text())
    expected = _normalize(golden.read_text())
    if actual != expected:
        diff = "\n".join(difflib.unified_diff(
            expected.splitlines(), actual.splitlines(),
            fromfile="golden", tofile="actual", n=3, lineterm="",
        ))
        pytest.fail(
            "data.js differs from golden — if intentional, update "
            f"{golden.relative_to(REPO)} and commit. Diff:\n{diff[:4000]}"
        )


@pytest.mark.parametrize(
    "fixture_run", [CLAIM_RUN, HA_RUN], ids=["claim-event-bus", "home-assistant"]
)
def test_all_expected_files_present(tmp_path: pathlib.Path, fixture_run: pathlib.Path) -> None:
    out, _ = build_report(fixture_run, out_dir=tmp_path)
    expected = {
        "index.html", "app.js", "data.js", "styles.css", "screens.css",
        "vendor-licenses.txt", "build-manifest.txt",
    }
    actual = {p.name for p in out.iterdir() if p.is_file()}
    missing = expected - actual
    assert not missing, f"missing files in bundle output: {missing}"
