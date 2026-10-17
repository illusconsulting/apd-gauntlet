"""Pass-3 tests: cross-file ID and artifact resolution."""
from __future__ import annotations

import pathlib
import shutil

import pytest
import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_capability_id, compute_id, compute_improvement_id
from apd_gauntlet.validate import run_cross_file_pass
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"
VALID_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "valid"
INVALID_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "invalid"


def _copy_clean_run(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_unknown_artifact_caught(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Change artifact reference to one not in the intake brief.
    text = text.replace("artifact: tech_plan.md", "artifact: unknown_file.md")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "not in intake brief" in result.output.lower()


def test_analyzer_derived_artifacts_accepted(tmp_path):
    """Issue #86: tier-4 analyzers may cite their own derived synthesis outputs.

    A finding whose evidence cites 40-synthesis/asset-graph.yaml and
    40-synthesis/deduped-findings.yaml must NOT be flagged as "not in intake
    brief", even though those paths are absent from the context-brief artifacts.
    """
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Repoint the single tech_plan.md evidence entry at an analyzer-derived
    # synthesis output, and append a second analyzer-derived citation.
    assert "artifact: tech_plan.md" in text  # guard against a no-op replace
    text = text.replace(
        "    - artifact: tech_plan.md\n",
        "    - artifact: 40-synthesis/asset-graph.yaml\n"
        '      locator: "conf-7aa376c5"\n'
        '      excerpt: "deduped finding record"\n'
        "    - artifact: 40-synthesis/deduped-findings.yaml\n",
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert "not in intake brief" not in result.output.lower(), result.output


def test_unknown_artifact_still_caught_alongside_analyzer_derived(tmp_path):
    """Issue #86 guard: the carve-out is narrow — a genuinely-unknown artifact
    cited in evidence STILL fails, even when analyzer-derived paths are allowed.
    """
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace("artifact: tech_plan.md", "artifact: 40-synthesis/not-a-real-file.yaml")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "not in intake brief" in result.output.lower()
    assert "not-a-real-file.yaml" in result.output


def test_dangling_cross_reference_caught(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    # Append a cross_reference pointing nowhere.
    text = text.replace("evidence:", "cross_references:\n    - conf-deadbeef\n  evidence:")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "cross_reference" in result.output.lower()
    assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# FW-3: 00-context generated artifacts + post-synthesis merged cross-refs
# ---------------------------------------------------------------------------


def test_context_derived_artifacts_accepted(tmp_path):
    """FW-3: specialists (esp. the tier-4 threat-model evaluator, which MUST
    cite the normalized threat model) may cite 00-context generated artifacts as
    evidence — in both ``00-context/``-prefixed and bare form — without being
    flagged 'not in intake brief'."""
    dst = _copy_clean_run(tmp_path)
    # The carve-out is existence-gated: the cited 00-context artifacts must
    # actually be present (mirrors the code-evidence-index guard).
    ctx = dst / "00-context"
    (ctx / "threat-model-normalized.yaml").write_text(
        "schema_version: 1\nentries: []\n", encoding="utf-8"
    )
    (ctx / "asset-inventory.yaml").write_text(
        "schema_version: 1\ngenerated_by: intake\n"
        "assets: []\nidentities: []\ntrust_boundaries: []\n",
        encoding="utf-8",
    )
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    assert "artifact: tech_plan.md" in text  # guard against a no-op replace
    text = text.replace(
        "    - artifact: tech_plan.md\n",
        "    - artifact: 00-context/threat-model-normalized.yaml\n"
        '      locator: "entries[entry_id=tm-0001]"\n'
        '      excerpt: "normalized threat model entry"\n'
        "    - artifact: asset-inventory.yaml\n",
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert "not in intake brief" not in result.output.lower(), result.output


def test_context_derived_carveout_is_existence_gated(tmp_path):
    """FW-3 guard: a 00-context artifact that does NOT exist on disk is still
    flagged — the carve-out never grants an implicit pass to an absent file."""
    dst = _copy_clean_run(tmp_path)  # 00-context has only context-brief.md
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace(
        "artifact: tech_plan.md", "artifact: 00-context/threat-model-normalized.yaml"
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "not in intake brief" in result.output.lower()


def test_context_derived_carveout_still_narrow(tmp_path):
    """FW-3 guard: the 00-context carve-out does NOT whitelist context-brief.md
    (cite the underlying artifact, not the brief) nor arbitrary 00-context files."""
    dst = _copy_clean_run(tmp_path)
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace("artifact: tech_plan.md", "artifact: 00-context/context-brief.md")
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "not in intake brief" in result.output.lower()


def test_merged_cross_reference_resolved_from_deduped(tmp_path):
    """FW-3: tier-4 findings legitimately cross-reference MERGED ids that live
    only in 40-synthesis/deduped-findings.yaml — whose hyphenated filename is not
    matched by the ``*.findings.yaml`` record glob. When that corpus is present,
    those ids must resolve (not be flagged 'not found')."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / "deduped-findings.yaml").write_text(
        "finding:\n- id: merged-abcd1234\n", encoding="utf-8"
    )
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace(
        "evidence:", "cross_references:\n    - merged-abcd1234\n  evidence:", 1
    )
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert "merged-abcd1234" not in result.output, result.output
    assert "not found" not in result.output.lower(), result.output
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Kind-aware resolution: a record's cross_references and merged_from name ids of
# its OWN kind (capability.schema.json: capability ids; finding.schema.json:
# finding ids), so each must resolve against that kind's id set only.
# ---------------------------------------------------------------------------

# The clean-run fixture's two records (10-trustworthiness/confidentiality.*).
CLEAN_FINDING_ID = "conf-7aa376c5"
CLEAN_CAPABILITY_ID = "conf-cap-53b6f810"

# Record field -> the label the cross-file pass uses in its "not found" message.
REF_FIELDS = {"cross_references": "cross_reference", "merged_from": "merged_from"}


def _write_integrity_capability(dst, field, refs):
    """Write a second, schema-valid capability file (integrity lens) whose
    ``field`` lists ``refs``; return the new record's id."""
    title = "Signed claim-event payloads verified by consumers"
    locator = "§4.2 paragraph 5"
    rid = compute_capability_id("intg", title, locator)
    doc = {"capability": {
        "schema_version": 1,
        "id": rid,
        "agent": "integrity",
        "apd_tier": "trustworthiness",
        "apd_goal": "integrity",
        "title": title,
        "description": "Consumers verify an HMAC over each claim-event payload.",
        "maturity": "designed",
        "scope": "Confirmed for: claim-events topic consumers.",
        "evidence": [{
            "artifact": "tech_plan.md",
            "locator": locator,
            "excerpt": "Consumers verify the payload HMAC before processing",
        }],
        "control_mappings": {"nist_800_53r5": ["SI-7"]},
        field: list(refs),
    }}
    path = dst / "10-trustworthiness" / "integrity.capabilities.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return rid


def _write_integrity_finding(dst, field, refs):
    """Write a second, schema-valid finding file (integrity lens) whose
    ``field`` lists ``refs``; return the new record's id."""
    title = "Claim-event consumers do not verify payload integrity"
    locator = "§4.2 paragraph 4"
    rid = compute_id("intg", title, locator)
    doc = {"finding": {
        "schema_version": 1,
        "id": rid,
        "agent": "integrity",
        "apd_tier": "trustworthiness",
        "apd_goal": "integrity",
        "disposition": "gap",
        "severity": "medium",
        "confidence": "high",
        "title": title,
        "summary": "Consumers trust claim-event payloads without an integrity check.",
        "detail": "A tampered event would be processed as authentic.",
        "evidence": [{
            "artifact": "tech_plan.md",
            "locator": locator,
            "excerpt": "Consumers deserialize claim events directly",
        }],
        "control_mappings": {"nist_800_53r5": ["SI-7"]},
        "recommendation": {
            "posture": "required",
            "summary": "Verify a payload MAC before processing.",
            "detail": "Add an HMAC over each event payload and verify it in every consumer.",
        },
        field: list(refs),
    }}
    path = dst / "10-trustworthiness" / "integrity.findings.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return rid


@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_capability_ref_to_capability_in_other_file_resolves(tmp_path, field):
    """A capability naming an existing capability id from another file (the only
    form capability.schema.json allows) must not be reported 'not found'."""
    dst = _copy_clean_run(tmp_path)
    _write_integrity_capability(dst, field, [CLEAN_CAPABILITY_ID])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert f"{REF_FIELDS[field]} {CLEAN_CAPABILITY_ID} not found" not in result.output, (
        result.output
    )
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_capability_ref_to_missing_capability_caught(tmp_path, field):
    """A capability naming a capability id that exists nowhere is still reported."""
    dst = _copy_clean_run(tmp_path)
    _write_integrity_capability(dst, field, ["dist-cap-deadbeef"])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert f"{REF_FIELDS[field]} dist-cap-deadbeef not found" in result.output, result.output


@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_capability_ref_to_finding_id_caught(tmp_path, field):
    """Resolution is per kind, not over the union: a capability naming an
    existing FINDING id does not resolve (it is not a capability id)."""
    dst = _copy_clean_run(tmp_path)
    _write_integrity_capability(dst, field, [CLEAN_FINDING_ID])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert f"{REF_FIELDS[field]} {CLEAN_FINDING_ID} not found" in result.output, result.output


@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_finding_ref_to_finding_in_other_file_resolves(tmp_path, field):
    """Unchanged behaviour: a finding naming an existing finding id resolves."""
    dst = _copy_clean_run(tmp_path)
    _write_integrity_finding(dst, field, [CLEAN_FINDING_ID])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert "not found" not in result.output.lower(), result.output
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_finding_ref_to_missing_finding_caught(tmp_path, field):
    """Unchanged behaviour: a finding naming a finding id that exists nowhere is
    reported."""
    dst = _copy_clean_run(tmp_path)
    _write_integrity_finding(dst, field, ["conf-deadbeef"])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert f"{REF_FIELDS[field]} conf-deadbeef not found" in result.output, result.output


@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_finding_ref_to_capability_id_caught(tmp_path, field):
    """Unchanged behaviour: a finding naming an existing CAPABILITY id does not
    resolve (it is not a finding id)."""
    dst = _copy_clean_run(tmp_path)
    _write_integrity_finding(dst, field, [CLEAN_CAPABILITY_ID])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert f"{REF_FIELDS[field]} {CLEAN_CAPABILITY_ID} not found" in result.output, (
        result.output
    )


# Well-formed 40-synthesis/deduped-capabilities.yaml shapes that hold the merged
# id. apply.py writes the first; the synthesizer-fallback agent may write any of
# them, and the shared extract_records rule accepts all three.
DEDUPED_CAPABILITY_DOCS = {
    "singular-list": "capability:\n- id: cap-merged-abcd1234\n",
    "plural-list": "capabilities:\n- id: cap-merged-abcd1234\n",
    "single-record": "capability:\n  id: cap-merged-abcd1234\n",
}


@pytest.mark.parametrize("doc", list(DEDUPED_CAPABILITY_DOCS))
@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_merged_capability_ref_resolved_from_deduped(tmp_path, field, doc):
    """Mirror of FW-3 for capabilities: a cap-merged-* id that exists only in
    40-synthesis/deduped-capabilities.yaml (hyphenated, so not matched by the
    ``*.capabilities.yaml`` record glob) resolves once that corpus is present."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / "deduped-capabilities.yaml").write_text(
        DEDUPED_CAPABILITY_DOCS[doc], encoding="utf-8"
    )
    _write_integrity_capability(dst, field, ["cap-merged-abcd1234"])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert "cap-merged-abcd1234" not in result.output, result.output
    assert "not found" not in result.output.lower(), result.output
    assert result.exit_code == 0, result.output


# Malformed deduped corpora (written by an LLM on the synthesizer-fallback path):
# a top-level list, a top-level scalar, a root key whose value is a scalar, a YAML
# syntax error, and a record whose id is not a string (a list, so unhashable).
MALFORMED_DEDUPED_BODIES = {
    "top-level-list": "- id: {id}\n",
    "top-level-scalar": "5\n",
    "scalar-root-value": "{root}: 5\n",
    "invalid-yaml": "{root}: [\n",
    "non-string-id": "{root}:\n- id: [{id}]\n",
}


@pytest.mark.parametrize("body", list(MALFORMED_DEDUPED_BODIES))
@pytest.mark.parametrize("field", list(REF_FIELDS))
def test_malformed_deduped_capabilities_reports_not_found(tmp_path, field, body):
    """A malformed deduped-capabilities.yaml contributes no ids. validate must
    report the unresolved cap-merged-* ref as a normal error, not crash."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / "deduped-capabilities.yaml").write_text(
        MALFORMED_DEDUPED_BODIES[body].format(id="cap-merged-abcd1234", root="capability"),
        encoding="utf-8",
    )
    _write_integrity_capability(dst, field, ["cap-merged-abcd1234"])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert isinstance(result.exception, SystemExit), result.exception
    assert result.exit_code == 1, result.output
    assert f"{REF_FIELDS[field]} cap-merged-abcd1234 not found" in result.output, (
        result.output
    )


@pytest.mark.parametrize("body", list(MALFORMED_DEDUPED_BODIES))
def test_malformed_deduped_findings_reports_not_found(tmp_path, body):
    """FW-3 guard: a malformed deduped-findings.yaml contributes no ids. validate
    must report the unresolved merged-* ref as a normal error, not crash."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / "deduped-findings.yaml").write_text(
        MALFORMED_DEDUPED_BODIES[body].format(id="merged-abcd1234", root="finding"),
        encoding="utf-8",
    )
    _write_integrity_finding(dst, "cross_references", ["merged-abcd1234"])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert isinstance(result.exception, SystemExit), result.exception
    assert result.exit_code == 1, result.output
    assert "cross_reference merged-abcd1234 not found" in result.output, result.output


# Deduped files that cannot be read as UTF-8 text: bytes that are not UTF-8, and
# a directory where the file should be.
UNREADABLE_DEDUPED = ("non-utf8-bytes", "directory")
DEDUPED_REF = {
    "capability": ("deduped-capabilities.yaml", "cap-merged-abcd1234", _write_integrity_capability),
    "finding": ("deduped-findings.yaml", "merged-abcd1234", _write_integrity_finding),
}


@pytest.mark.parametrize("shape", UNREADABLE_DEDUPED)
@pytest.mark.parametrize("kind", list(DEDUPED_REF))
def test_unreadable_deduped_file_reports_not_found(tmp_path, kind, shape):
    """An unreadable deduped file contributes no ids. validate must report the
    unresolved merged ref as a normal error, not crash."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    filename, ref, write_record = DEDUPED_REF[kind]
    if shape == "directory":
        (synth / filename).mkdir()
    else:
        (synth / filename).write_bytes(b"\xff\xfe\x00bad")
    write_record(dst, "cross_references", [ref])
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert isinstance(result.exception, SystemExit), result.exception
    assert result.exit_code == 1, result.output
    assert f"cross_reference {ref} not found" in result.output, result.output


# The report-data.yaml check reads both deduped files. Per kind: the deduped
# file, the report-data section and the error a dangling merged id gets there.
REPORT_DATA_DEDUPED = {
    "finding": (
        "deduped-findings.yaml", "headline_findings", "merged-abcd1234",
        "headline_findings references unknown finding 'merged-abcd1234'",
    ),
    "capability": (
        "deduped-capabilities.yaml", "strengths", "cap-merged-abcd1234",
        "strengths references unknown capability 'cap-merged-abcd1234'",
    ),
}


@pytest.mark.parametrize("body", list(MALFORMED_DEDUPED_BODIES))
@pytest.mark.parametrize("kind", list(REPORT_DATA_DEDUPED))
def test_malformed_deduped_with_report_data_reports_unknown(tmp_path, kind, body):
    """The report-data.yaml check reads a malformed deduped file as holding no
    ids. validate must report the merged id it headlines as unknown, not crash."""
    fname, section, rid, message = REPORT_DATA_DEDUPED[kind]
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / fname).write_text(
        MALFORMED_DEDUPED_BODIES[body].format(id=rid, root=kind), encoding="utf-8"
    )
    (synth / "report-data.yaml").write_text(
        yaml.safe_dump({section: [{"id": rid}]}), encoding="utf-8"
    )
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert isinstance(result.exception, SystemExit), result.exception
    assert result.exit_code == 1, result.output
    assert message in result.output, result.output


@pytest.mark.parametrize("doc", list(DEDUPED_CAPABILITY_DOCS))
def test_report_data_strength_resolves_merged_capability(tmp_path, doc):
    """The report-data.yaml check reads deduped-capabilities.yaml with the shared
    extract_records rule, so a cap-merged-* strength resolves in every
    well-formed shape (singular or plural root key, single record)."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / "deduped-capabilities.yaml").write_text(
        DEDUPED_CAPABILITY_DOCS[doc], encoding="utf-8"
    )
    (synth / "report-data.yaml").write_text(
        yaml.safe_dump({"strengths": [{"id": "cap-merged-abcd1234"}]}), encoding="utf-8"
    )
    report = run_cross_file_pass(dst)
    assert report.is_clean, report.render()


@pytest.mark.parametrize("body", list(MALFORMED_DEDUPED_BODIES))
def test_malformed_deduped_findings_with_domain_improvements_reports_not_found(
    tmp_path, body
):
    """The domain-improvements.yaml check reads a malformed deduped-findings.yaml
    as holding no ids. validate must report the merged-* evidence ref as not
    found, not crash."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    synth.mkdir(exist_ok=True)
    (synth / "deduped-findings.yaml").write_text(
        MALFORMED_DEDUPED_BODIES[body].format(id="merged-abcd1234", root="finding"),
        encoding="utf-8",
    )
    itype, pack, tfile = "missing_severity_clause", "pbm", "severity-rubric.md"
    improvements = {
        "schema_version": 1,
        "generated_by": "domain-auditor",
        "examined_domains": [pack],
        "improvements": [{
            "id": compute_improvement_id(itype, pack, tfile, "merged-abcd1234"),
            "improvement_type": itype,
            "target_pack": pack,
            "target_file": tfile,
            "source": "deterministic",
            "priority": "high",
            "evidence": [{"kind": "finding", "ref": "merged-abcd1234"}],
            "rationale": "The run raised a finding no selected pack's rubric covers.",
            "suggested_action": "add the missing severity clause to the pack",
            "draft_snippet": "- clause: grounded in the merged finding\n",
        }],
    }
    (synth / "domain-improvements.yaml").write_text(
        yaml.safe_dump(improvements, sort_keys=False), encoding="utf-8"
    )
    result = CliRunner().invoke(main, ["validate", str(dst)])
    assert isinstance(result.exception, SystemExit), result.exception
    assert result.exit_code == 1, result.output
    assert (
        "evidence[0].ref 'merged-abcd1234' (kind: finding) not found in run corpus"
        in result.output
    ), result.output


# ---------------------------------------------------------------------------
# C-21: Phase C artifact pickup
# ---------------------------------------------------------------------------


def test_validate_picks_up_asset_inventory(tmp_path):
    """Phase C context-rollup: asset-inventory.yaml is schema-validated when present."""
    dst = _copy_clean_run(tmp_path)
    shutil.copy2(
        VALID_FIXTURES / "asset-inventory-valid.yaml",
        dst / "00-context" / "asset-inventory.yaml",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    # The new rollup must be counted in files_seen (was 2 before, must be >= 3 now).
    assert "Files scanned:" in result.output
    # Should still report Clean — the valid fixture passes schema validation.
    assert "Clean." in result.output


def test_validate_rejects_malformed_asset_inventory(tmp_path):
    """Phase C context-rollup: asset-inventory.yaml is actually schema-validated.

    Drop schema-required fields so an empty document still violates the schema.
    """
    dst = _copy_clean_run(tmp_path)
    (dst / "00-context" / "asset-inventory.yaml").write_text("schema_version: 1\n")
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "asset-inventory" in result.output.lower()


def test_validate_picks_up_phase_c_synthesis_artifacts(tmp_path):
    """Phase C synthesis rollups: asset-graph, attack-paths, defense-graph schema-validated."""
    dst = _copy_clean_run(tmp_path)
    synth = dst / "40-synthesis"
    # Use the valid fixtures as canonical clean inputs.
    shutil.copy2(VALID_FIXTURES / "asset-graph-valid.yaml",   synth / "asset-graph.yaml")
    shutil.copy2(VALID_FIXTURES / "attack-paths-valid.yaml",  synth / "attack-paths.yaml")
    shutil.copy2(VALID_FIXTURES / "defense-graph-valid.yaml", synth / "defense-graph.yaml")
    # The asset-graph-valid fixture references a foreign auth-9e8d7c6b finding and
    # auth-cap-12345678 capability. To exercise cross-file edge-integrity in the
    # positive case without hitting those orphan refs, strip the two ID-bearing
    # edges from the asset-graph for this rollup test. (The dedicated
    # orphan-edge test below exercises the unhappy path.)
    import yaml  # local import keeps top-of-file imports tidy
    ag_path = synth / "asset-graph.yaml"
    ag = yaml.safe_load(ag_path.read_text())
    ag["edges"] = [
        e for e in ag["edges"]
        if e["edge_type"] not in {"compromisable_via_finding", "mitigated_by_capability"}
    ]
    ag_path.write_text(yaml.safe_dump(ag, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
    assert "Clean." in result.output


def test_validate_rejects_malformed_asset_graph(tmp_path):
    """Cross-file integrity: asset-graph edge endpoints must reference real nodes."""
    dst = _copy_clean_run(tmp_path)
    shutil.copy2(
        INVALID_FIXTURES / "asset-graph-with-orphan-edge.yaml",
        dst / "40-synthesis" / "asset-graph.yaml",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    # The error should name the orphan endpoint and the offending edge field.
    assert "asset-ffffffff" in result.output
    assert "not in nodes list" in result.output.lower()


def test_validate_rejects_asset_graph_with_unknown_finding_id(tmp_path):
    """Cross-file integrity: compromisable_via_finding edges must reference real findings."""
    dst = _copy_clean_run(tmp_path)
    # Build a graph whose finding edge points at an id that is NOT in the run.
    import yaml
    graph = {
        "schema_version": 1,
        "generated_by": "attack_path_analyzer",
        "nodes": [
            {
                "node_id": "asset-11111111",
                "node_type": "asset",
                "name": "service-a",
                "asset_type": "service",
                "provenance": {"source": "artifact"},
                "confidence": "high",
            },
            {
                "node_id": "asset-22222222",
                "node_type": "asset",
                "name": "service-b",
                "asset_type": "service",
                "provenance": {"source": "artifact"},
                "confidence": "high",
            },
        ],
        "edges": [
            {
                "edge_id": "edge-00000001",
                "edge_type": "compromisable_via_finding",
                "from": "asset-11111111",
                "to":   "asset-22222222",
                "finding_id": "conf-deadbeef",  # NOT in the clean-run findings
                "provenance": {"source": "artifact"},
                "confidence": "high",
                "traversal_cost": 1,
            }
        ],
    }
    (dst / "40-synthesis" / "asset-graph.yaml").write_text(yaml.safe_dump(graph, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "conf-deadbeef" in result.output
    assert "not found" in result.output.lower()


def test_validate_rejects_asset_graph_with_unknown_capability_id(tmp_path):
    """Cross-file integrity: mitigated_by_capability edges must reference real capabilities."""
    dst = _copy_clean_run(tmp_path)
    import yaml
    graph = {
        "schema_version": 1,
        "generated_by": "attack_path_analyzer",
        "nodes": [
            {
                "node_id": "asset-11111111",
                "node_type": "asset",
                "name": "service-a",
                "asset_type": "service",
                "provenance": {"source": "artifact"},
                "confidence": "high",
            },
            {
                "node_id": "asset-22222222",
                "node_type": "asset",
                "name": "service-b",
                "asset_type": "service",
                "provenance": {"source": "artifact"},
                "confidence": "high",
            },
        ],
        "edges": [
            {
                "edge_id": "edge-00000002",
                "edge_type": "mitigated_by_capability",
                "from": "asset-11111111",
                "to":   "asset-22222222",
                "capability_id": "conf-cap-deadbeef",  # NOT in the clean-run capabilities
                "provenance": {"source": "artifact"},
                "confidence": "high",
                "traversal_cost": 1,
            }
        ],
    }
    (dst / "40-synthesis" / "asset-graph.yaml").write_text(yaml.safe_dump(graph, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "conf-cap-deadbeef" in result.output
    assert "not found" in result.output.lower()


def test_validate_picks_up_attack_path_findings(tmp_path):
    """Regression: an apath-* record in attack-path.findings.yaml is schema-validated.

    Post-C-20 the file naturally matches the ``*.findings.yaml`` glob, so this is
    covered transitively by _iter_records. The assertion is that a bad apath-*
    record produces an error (i.e., not silently skipped).
    """
    dst = _copy_clean_run(tmp_path)
    # Write a finding with a wrong-shape id prefix (apath- expected but with
    # bogus 4-char suffix instead of 8-hex). The finding schema's id pattern
    # must reject it.
    bad_finding = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: apath-xx\n"               # invalid: 'xx' not 8-hex
        "    agent: attack_path_analyzer\n"
        "    apd_tier: trustworthiness\n"
        "    apd_goal: confidentiality\n"
        "    disposition: risk\n"
        "    severity: high\n"
        "    confidence: high\n"
        "    title: 'malformed apath finding'\n"
        "    summary: 'should fail schema validation'\n"
        "    detail: 'short'\n"
        "    evidence:\n"
        "      - artifact: tech_plan.md\n"
        "        locator: 'x'\n"
        "        excerpt: 'y'\n"
        "    recommendation:\n"
        "      posture: required\n"
        "      summary: 's'\n"
        "      detail: 'd'\n"
    )
    (dst / "40-synthesis" / "attack-path.findings.yaml").write_text(bad_finding)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    # The record should have been seen and rejected by the finding schema.
    assert "apath-xx" in result.output or "pattern" in result.output.lower()


@pytest.mark.parametrize(
    "name, body",
    [
        ("asset-graph.yaml", "bogus_key: 1\n"),
        ("attack-paths.yaml", "bogus_key: 1\n"),
        ("defense-graph.yaml", "bogus_key: 1\n"),
        ("attack-path.findings.yaml", "finding:\n  - agent: attack_path_analyzer\n"),
    ],
)
def test_validate_schema_checks_each_attack_path_artifact(tmp_path, name, body):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / name).write_text(body)
    result = CliRunner().invoke(main, ["validate", "--schema-only", "--errors-only", str(dst)])
    assert result.exit_code == 1 and name in result.output
