"""Unit tests for the structural canonicalizer (C1)."""
from __future__ import annotations

import pathlib

import pytest
import yaml
from apd_gauntlet.canonicalize import (
    CanonicalizeCollision,
    canonicalize_run,
)
from apd_gauntlet.linters import compute_capability_id, compute_id
from apd_gauntlet.validate import extract_records


def test_extract_records_handles_singular_plural_and_wrapped():
    # singular root, list of bare records
    assert extract_records({"finding": [{"id": "a"}, {"id": "b"}]}, "finding") == [
        {"id": "a"}, {"id": "b"},
    ]
    # singular root, single bare record
    assert extract_records({"finding": {"id": "a"}}, "finding") == [{"id": "a"}]
    # legacy plural root
    assert extract_records({"findings": [{"id": "a"}]}, "finding") == [{"id": "a"}]
    # per-record wrapper is unwrapped
    assert extract_records(
        {"finding": [{"finding": {"id": "a"}}, {"finding": {"id": "b"}}]}, "finding"
    ) == [{"id": "a"}, {"id": "b"}]
    # empty / absent
    assert extract_records({}, "finding") == []


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _finding(agent, title, locator, fid="fabricated-00000000", **extra):
    rec = {
        "id": fid,
        "agent": agent,
        "title": title,
        "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "q"}],
    }
    rec.update(extra)
    return rec


def test_canonicalize_normalizes_plural_root_and_unwraps(tmp_path):
    run = tmp_path / "run"
    # plural root key + per-record wrapper + fabricated id
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    canonicalize_run(run)
    doc = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )
    # singular root key, bare record, schema_version injected
    assert set(doc.keys()) == {"finding"}
    assert isinstance(doc["finding"], list)
    rec = doc["finding"][0]
    assert rec["schema_version"] == 1
    assert "finding" not in rec  # unwrapped
    # id recomputed deterministically (tooling-authoritative)
    assert rec["id"] == compute_id("conf", "PHI in topic", "§4.2")


def test_canonicalize_rewrites_cross_references(tmp_path):
    run = tmp_path / "run"
    a = _finding("confidentiality", "A", "§1")
    b = _finding("integrity", "B", "§2", fid="fab-b",
                 cross_references=["fabricated-00000000"])
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {"finding": [a]})
    _write(run / "10-trustworthiness" / "integrity.findings.yaml", {"finding": [b]})
    canonicalize_run(run)
    b_doc = yaml.safe_load(
        (run / "10-trustworthiness" / "integrity.findings.yaml").read_text()
    )
    expected_a_id = compute_id("conf", "A", "§1")
    assert b_doc["finding"][0]["cross_references"] == [expected_a_id]


def test_canonicalize_is_idempotent(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    canonicalize_run(run)
    first = (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_bytes()
    canonicalize_run(run)
    second = (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_bytes()
    assert first == second  # second run is a byte-for-byte no-op


def test_canonicalize_is_structural_only(tmp_path):
    run = tmp_path / "run"
    long_title = "X" * 250  # over the 200-char limit validate enforces
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [_finding("confidentiality", long_title, "§1",
                             evidence=[{"artifact": "tech_plan.md", "locator": "§1",
                                        "excerpt": "word " * 40}])],
    })
    canonicalize_run(run)
    rec = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )["finding"][0]
    assert rec["title"] == long_title  # NOT trimmed — validate flags content, not canonicalize
    assert rec["evidence"][0]["excerpt"] == "word " * 40  # untouched


def test_canonicalize_collision_raises(tmp_path):
    run = tmp_path / "run"
    # Two distinct records with the SAME title + locator under the same agent
    # -> identical computed id -> collision.
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [
            _finding("confidentiality", "dup", "§1", fid="fab-1"),
            _finding("confidentiality", "dup", "§1", fid="fab-2"),
        ],
    })
    with pytest.raises(CanonicalizeCollision):
        canonicalize_run(run)


def test_canonicalize_leaves_out_of_scope_records_untouched(tmp_path):
    run = tmp_path / "run"
    synth = run / "40-synthesis"
    # attack-path file: agent not in _PREFIX_BY_AGENT -> file untouched
    apath = {"finding": [{"schema_version": 1, "id": "apath-deadbeef",
                          "agent": "attack_path_analyzer", "title": "t",
                          "evidence": [{"artifact": ".apd-run.yaml", "locator": "x",
                                        "excerpt": "y"}]}]}
    _write(synth / "attack-path.findings.yaml", apath)
    before = (synth / "attack-path.findings.yaml").read_bytes()
    # deduped file: filename does not match the *.findings.yaml glob at all
    _write(synth / "deduped-findings.yaml", {"finding": [{"id": "merged-abcd1234"}]})
    ded_before = (synth / "deduped-findings.yaml").read_bytes()
    canonicalize_run(run)
    assert (synth / "attack-path.findings.yaml").read_bytes() == before
    assert (synth / "deduped-findings.yaml").read_bytes() == ded_before


def test_canonicalize_count_is_zero_on_idempotent_rerun(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    first = canonicalize_run(run)
    assert first.records_canonicalized >= 1
    second = canonicalize_run(run)
    assert second.records_canonicalized == 0
    assert second.cross_refs_rewritten == 0


def test_canonicalize_leaves_id_untouched_when_no_locator(tmp_path):
    """An in-scope record with no evidence locator cannot yield a deterministic
    id, so canonicalize leaves its id untouched (by-design; mirrors the linters'
    early-return).

    When the file has ONLY locator-less records, in_scope stays 0 and the file
    is not written back at all.  When a file also contains a record with a valid
    locator (making in_scope >= 1), the file IS written back — but the
    locator-less record's id is still left as-is.
    """
    run = tmp_path / "run"

    # Case A: file contains ONLY a locator-less in-scope record → file untouched.
    only_nolocator = {
        "finding": [
            {
                "id": "fabricated-only-no-locator",
                "agent": "confidentiality",
                "title": "No locator finding",
                "evidence": [],
            }
        ]
    }
    path_a = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path_a, only_nolocator)
    before_a = path_a.read_bytes()
    canonicalize_run(run)
    assert path_a.read_bytes() == before_a  # file not rewritten

    # Case B: file contains one locator-less + one normal record → file IS
    # rewritten (in_scope >= 1), but the locator-less record's id is still
    # left untouched.
    run2 = tmp_path / "run2"
    mixed = {
        "finding": [
            {
                "id": "fabricated-no-locator",
                "agent": "confidentiality",
                "title": "PHI exposure with no evidence locator",
                "evidence": [],
            },
            _finding("confidentiality", "PHI in logs", "§3.1", fid="fabricated-has-locator"),
        ]
    }
    path_b = run2 / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path_b, mixed)
    canonicalize_run(run2)
    out = yaml.safe_load(path_b.read_text())
    # The normal record gets its id recomputed deterministically.
    assert out["finding"][1]["id"] == compute_id("conf", "PHI in logs", "§3.1")
    # The locator-less record's id is left as-is.
    assert out["finding"][0]["id"] == "fabricated-no-locator"


def test_canonicalize_normalizes_plural_capabilities_root(tmp_path):
    """A genuine 'capabilities:' plural root key is now correctly normalized."""
    run = tmp_path / "run"
    title = "Field encryption capability"
    locator = "§1"
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml", {
        "capabilities": [{
            "id": "fabricated-00000000",
            "agent": "confidentiality",
            "title": title,
            "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "q"}],
        }],
    })
    canonicalize_run(run)
    doc = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.capabilities.yaml").read_text()
    )
    assert set(doc.keys()) == {"capability"}  # normalized to singular root
    rec = doc["capability"][0]
    assert rec["id"] == compute_capability_id("conf", title, locator)
