"""load_corpus: shared corpus loader. Includes apath + tmeval ONLY when flagged."""
from __future__ import annotations

import pathlib

from apd_gauntlet.synthesis.loader import load_corpus

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def test_default_excludes_attack_path_findings():
    findings, caps = load_corpus(EXAMPLE)
    # apath-* live in 40-synthesis/attack-path.findings.yaml — excluded by default.
    assert not any(fid.startswith("apath-") for fid in findings)
    assert caps  # capabilities still load


def test_include_attack_path_pulls_apath_and_tmeval():
    findings, caps = load_corpus(EXAMPLE, include_attack_path=True)
    assert any(fid.startswith("apath-") for fid in findings), "apath-* must be included"
    assert any(fid.startswith("tmeval-") for fid in findings), "tmeval-* must be included"


def test_skips_deduped_outputs_so_corpus_is_specialist_records():
    # The loader reads the *source* tier files, never 40-synthesis deduped outputs
    # (whose filenames do not match the per-tier glob). No merged-* leaks in.
    findings, _caps = load_corpus(EXAMPLE, include_attack_path=True)
    assert not any(fid.startswith("merged-") for fid in findings)
