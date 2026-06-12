"""Unit tests for the structural canonicalizer (C1)."""
from __future__ import annotations

import hashlib
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


def test_canonicalize_skips_unparseable_file_and_reports_it(tmp_path):
    """A single unparseable YAML file must NOT abort the whole pass.

    The malformed file is skipped (left untouched on disk) and surfaced in
    ``result.parse_errors``; every valid file is still canonicalized.
    """
    run = tmp_path / "run"
    # Valid in-scope findings file.
    valid_path = run / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(valid_path, {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    # Malformed YAML findings file (unquoted colon-bearing scalar makes the
    # value a mapping where a list/value is expected -> yaml.YAMLError on load).
    bad_path = run / "10-trustworthiness" / "integrity.findings.yaml"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text(
        "finding:\n  - title: broken: unquoted colon: scalar\n    agent: integrity\n",
        encoding="utf-8",
    )
    bad_before = bad_path.read_bytes()

    # Must NOT raise.
    result = canonicalize_run(run)

    # Valid file IS canonicalized (id recomputed deterministically).
    rec = yaml.safe_load(valid_path.read_text())["finding"][0]
    assert rec["id"] == compute_id("conf", "PHI in topic", "§4.2")

    # Malformed file left untouched on disk (not rewritten).
    assert bad_path.read_bytes() == bad_before

    # Malformed file surfaced in parse_errors; valid file is not.
    assert len(result.parse_errors) == 1
    err_path, err_msg = result.parse_errors[0]
    assert err_path == str(bad_path)
    assert err_msg  # non-empty message


def test_canonicalize_parse_errors_empty_when_all_parse(tmp_path):
    """When every file parses cleanly, parse_errors is empty (no behavior change)."""
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    result = canonicalize_run(run)
    assert result.parse_errors == []


def test_canonicalize_injects_id_and_schema_version_when_absent(tmp_path):
    rec = _finding("confidentiality", "PHI in logs", "§2.1")
    rec.pop("id", None)
    rec.pop("schema_version", None)
    run_dir = tmp_path
    path = run_dir / "10-trustworthiness" / "confidentiality.findings.yaml"
    _write(path, {"finding": [rec]})

    canonicalize_run(run_dir)

    out = yaml.safe_load(path.read_text(encoding="utf-8"))["finding"][0]
    assert out["schema_version"] == 1
    assert out["id"].startswith("conf-") and len(out["id"]) == len("conf-") + 8


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


def test_canonicalize_mints_tmeval_id_from_key(tmp_path):
    tmeval_key = {"flavor": "coverage_gap", "surface": "ingest-api", "goal": "confidentiality"}
    rec = {
        "agent": "threat_model_evaluator",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality",
        "disposition": "gap", "severity": "medium", "confidence": "medium",
        "title": "Threat model omits Confidentiality analysis for ingest-api",
        "summary": "s", "detail": "d",
        "tmeval_key": tmeval_key,
        "evidence": [{"artifact": "00-context/threat-model-normalized.yaml",
                      "locator": "entries[asset=ingest-api]", "excerpt": "x"}],
        "control_mappings": {"nist_800_53r5": ["SC-7"]},
        "recommendation": {"posture": "recommended", "summary": "s", "detail": "d"},
    }
    d = tmp_path / "40-threat-model"
    d.mkdir(parents=True)
    p = d / "threat-model.findings.yaml"
    p.write_text(yaml.safe_dump({"finding": [rec]}, sort_keys=False), encoding="utf-8")

    canonicalize_run(tmp_path)

    out = yaml.safe_load(p.read_text(encoding="utf-8"))["finding"][0]
    digest = hashlib.sha256(b"coverage_gap|ingest-api|confidentiality").hexdigest()[:8]
    want = f"tmeval-{digest}"
    assert out["id"] == want
    assert out["schema_version"] == 1


def test_canonicalize_skips_tmeval_record_without_key(tmp_path):
    """A threat_model_evaluator record lacking tmeval_key is silently skipped:
    no id is minted (the prefix path also can't mint one — agent is out-of-prefix)."""
    rec = {
        "agent": "threat_model_evaluator",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality",
        "disposition": "gap", "severity": "medium", "confidence": "medium",
        "title": "Threat model omits Confidentiality analysis for ingest-api",
        "summary": "s", "detail": "d",
        "evidence": [{"artifact": "00-context/threat-model-normalized.yaml",
                      "locator": "entries[asset=ingest-api]", "excerpt": "x"}],
        "control_mappings": {"nist_800_53r5": ["SC-7"]},
        "recommendation": {"posture": "recommended", "summary": "s", "detail": "d"},
    }
    d = tmp_path / "40-threat-model"
    d.mkdir(parents=True)
    p = d / "threat-model.findings.yaml"
    p.write_text(yaml.safe_dump({"finding": [rec]}, sort_keys=False), encoding="utf-8")

    canonicalize_run(tmp_path)

    out = yaml.safe_load(p.read_text(encoding="utf-8"))["finding"][0]
    assert "id" not in out


def test_canonicalize_mints_dimpr_id(tmp_path):
    from apd_gauntlet.canonicalize import canonicalize_run
    from apd_gauntlet.linters import compute_improvement_id
    rec = {
        "improvement_type": "missing_consequential_action",
        "target_pack": "agentic-ai",
        "target_file": "domain.yaml",
        "source": "deterministic",
        "priority": "medium",
        "rationale": "Tool-call audit action missing from the pack's consequential-action surface.",
        "suggested_action": "Add a tool_invocation consequential action.",
        "draft_snippet": "consequential_actions:\n  - tool_invocation",
        "evidence": [{"kind": "finding", "ref": "conf-12345678"}],
    }
    doc = {
        "schema_version": 1, "generated_by": "domain-auditor",
        "examined_domains": ["agentic-ai"], "improvements": [rec],
    }
    d = tmp_path / "40-synthesis"
    d.mkdir(parents=True)
    p = d / "domain-improvements.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")

    canonicalize_run(tmp_path)

    out = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert out["improvements"][0]["id"] == compute_improvement_id(
        "missing_consequential_action", "agentic-ai", "domain.yaml", "conf-12345678")
    # envelope preserved
    assert out["generated_by"] == "domain-auditor"
    assert out["examined_domains"] == ["agentic-ai"]
