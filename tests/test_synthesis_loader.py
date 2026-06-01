"""load_corpus: shared corpus loader. Includes apath + tmeval ONLY when flagged."""
from __future__ import annotations

import pathlib

import yaml
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


# C3 / F3: load_corpus skips id-less capability records instead of crashing.


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_load_corpus_skips_capability_missing_id(tmp_path, capsys):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml", {
        "capability": [
            {"id": "conf-cap-00000000", "agent": "confidentiality", "title": "ok"},
            {"agent": "confidentiality", "title": "missing id"},  # no id
        ],
    })
    _findings, capabilities = load_corpus(run)
    ids = [c.get("id") for c in capabilities]
    assert "conf-cap-00000000" in ids
    assert all(c.get("id") for c in capabilities)  # the id-less one was skipped
    err = capsys.readouterr().err
    assert "missing 'id'; skipping" in err
