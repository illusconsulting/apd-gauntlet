"""apply-clusters: merge/link/separate application + merged-id rule + reproducibility."""
from __future__ import annotations

import hashlib
import json
import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.apply import AdjudicationMissing, apply_clusters
from apd_gauntlet.validate import run_cross_file_pass
from click.testing import CliRunner
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
FIXTURES = REPO / "tests" / "fixtures"


def _scaffold_two_finding_run(tmp_path):
    """A minimal run: two reciprocal findings + a hand-built merge decision."""
    run = tmp_path / "run"
    (run / "10-trustworthiness").mkdir(parents=True)
    (run / "30-auditability").mkdir(parents=True)
    (run / "40-synthesis").mkdir()
    (run / ".apd-run.yaml").write_text("run_id: t\ndomain: pbm\n")
    nonrep = {
        "schema_version": 1, "id": "nonrep-62124087", "agent": "non_repudiation",
        "apd_tier": "auditability", "apd_goal": "non_repudiation", "disposition": "gap",
        "severity": "high", "confidence": "high",
        "title": "Audit log unsigned no HMAC protection present",
        "summary": "Unsigned audit entries cannot prove non-tampering of records.",
        "detail": "Without HMAC there is no cryptographic proof entries are unmodified.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§5.2",
                       "excerpt": "no WORM enforcement"}],
        "control_mappings": {"nist_800_53r5": ["AU-9", "AU-10"]},
        "recommendation": {
            "posture": "required",
            "summary": "Sign every audit entry with HMAC.",
            "detail": "Sign each audit entry with a KMS-derived HMAC at write time.",
        },
        "related_concerns": ["immutability"],
    }
    immut = {
        "schema_version": 1, "id": "immut-e09e4945", "agent": "immutability",
        "apd_tier": "auditability", "apd_goal": "immutability", "disposition": "gap",
        "severity": "high", "confidence": "high",
        "title": "Audit log mutable table no WORM enforcement present",
        "summary": "No storage-layer write-once protection prevents record deletion.",
        "detail": "Application-level append-only discipline can be bypassed by any DBA.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§5.2",
                       "excerpt": "no WORM enforcement"}],
        "control_mappings": {"nist_800_53r5": ["AU-9(2)", "AU-9(3)"]},
        "recommendation": {
            "posture": "required",
            "summary": "Migrate to WORM-protected storage.",
            "detail": "Migrate audit log storage to S3 with Object Lock in Compliance mode.",
        },
        "related_concerns": ["non_repudiation"],
    }
    # A real capability + finding the contradiction (C5) + stale downgrade (I4)
    # reference; both ids must resolve in validate.run_cross_file_pass.
    conf_cap = {
        "schema_version": 1, "id": "conf-cap-89e19793", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality",
        "maturity": "tested", "confidence": "high",
        "title": "Field-level envelope encryption on PHI columns",
        "description": "Envelope encryption is applied to PHI columns in the RDS tables at rest.",
        "scope": "member_demographics and claims tables at rest",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§5.1",
                       "excerpt": "field-level encryption"}],
        "control_mappings": {"nist_800_53r5": ["SC-28"]},
    }
    conf_finding = {
        "schema_version": 1, "id": "conf-7aa376c5", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "high", "confidence": "high",
        "title": "Kafka claim-events topic carries plaintext PHI payloads",
        "summary": "PHI fields in the Kafka topic are protected only at the broker level.",
        "detail": "Payload-level PHI is plaintext; only broker-level encryption applies today.",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2",
                       "excerpt": "broker encryption only"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {
            "posture": "required",
            "summary": "Encrypt PHI payloads field-level.",
            "detail": "Apply envelope encryption to PHI fields before publishing to Kafka.",
        },
    }
    (run / "30-auditability" / "non_repudiation.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [nonrep]}, sort_keys=False))
    (run / "30-auditability" / "immutability.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [immut]}, sort_keys=False))
    (run / "10-trustworthiness" / "confidentiality.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [conf_finding]}, sort_keys=False))
    (run / "10-trustworthiness" / "confidentiality.capabilities.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "capability": [conf_cap]}, sort_keys=False))
    decisions = {
        "schema_version": 1, "generated_by": "apd-cluster-adjudicator",
        "decisions": [{
            "group_id": "cluster-cand-0001", "disposition": "merge",
            "merged_title": "Audit log is unsigned and stored in a mutable table",
            "merged_summary": "The audit_log lacks both signing and storage-layer immutability.",
            "merged_detail": "Both lenses identified this risk from complementary angles together.",
            "merged_recommendation": {
                "posture": "required",
                "summary": "Implement HMAC signing and migrate to WORM storage.",
                "detail": "Sign entries and migrate to S3 Object Lock compliance mode.",
            },
            "lens_perspectives": {
                "non_repudiation": {
                    "summary": "Unsigned entries cannot prove non-tampering.",
                    "detail": "No cryptographic proof a record was not modified.",
                },
                "immutability": {
                    "summary": "No write-once protection prevents deletion.",
                    "detail": "Append-only discipline can be bypassed by a DBA.",
                },
            },
            "chosen_severity": "critical",
            "severity_rationale": (
                "Combination triggers HIPAA breach-notification exposure beyond either lens."
            ),
        }],
        "contradictions": [{
            "finding_id": "conf-7aa376c5",
            "capability_id": "conf-cap-89e19793",
            "classification": "stale",
            "finding_assertion": (
                "PHI payloads in the Kafka topic are plaintext at the payload level."
            ),
            "capability_assertion": (
                "Field-level envelope encryption is applied to PHI columns at rest."
            ),
            "evidence_comparison": (
                "The capability covers RDS storage; the finding covers Kafka topics"
                " — different storage layers, different postures."
            ),
            "recommended_resolution": (
                "Confirm the encryption capability scope explicitly excludes Kafka"
                " payloads and update its scope statement."
            ),
        }],
        "_members": {"cluster-cand-0001": ["nonrep-62124087", "immut-e09e4945"]},
    }
    (run / "40-synthesis" / "cluster-decisions.yaml").write_text(
        yaml.safe_dump(decisions, sort_keys=False))
    return run


def test_merge_builds_merged_record_with_sha8_id(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    result = apply_clusters(run)
    merged = [f for f in result.findings if f["agent"] == "synthesizer"]
    assert len(merged) == 1
    m = merged[0]
    title = "Audit log is unsigned and stored in a mutable table"
    first_locator = "§5.2"
    expect = "merged-" + hashlib.sha256(f"{title}|{first_locator}".encode()).hexdigest()[:8]
    assert m["id"] == expect
    assert m["merged_from"] == ["immut-e09e4945", "nonrep-62124087"]  # sorted
    assert m["severity"] == "critical"  # honors adjudicator chosen_severity
    # sorted union
    assert m["control_mappings"]["nist_800_53r5"] == ["AU-10", "AU-9", "AU-9(2)", "AU-9(3)"]
    assert set(m["lens_perspectives"].keys()) == {"non_repudiation", "immutability"}
    # source records no longer appear as top-level findings
    assert not any(f["id"] in ("nonrep-62124087", "immut-e09e4945") for f in result.findings)


def test_merge_emits_severity_disagreement(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    apply_clusters(run)
    sevdis = yaml.safe_load((run / "40-synthesis" / "severity-disagreements.yaml").read_text())
    rows = sevdis["severity_disagreements"]
    assert len(rows) == 1
    assert rows[0]["chosen_severity"] == "critical"
    assert rows[0]["agent_severities"] == {"non_repudiation": "high", "immutability": "high"}


def test_outputs_are_schema_valid_and_reproducible(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    result1 = apply_clusters(run)
    deduped1 = (run / "40-synthesis" / "deduped-findings.yaml").read_text()
    apply_clusters(run)  # idempotent / reproducible
    deduped2 = (run / "40-synthesis" / "deduped-findings.yaml").read_text()
    assert deduped1 == deduped2, "apply-clusters output must be reproducible (no generated_at)"
    assert "generated_at" not in deduped1
    finding_schema = json.loads((SCHEMA_DIR / "finding.schema.json").read_text())
    from referencing import Registry, Resource
    resources = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            resources.append((s["$id"], Resource.from_contents(s)))
    registry = Registry().with_resources(resources)
    v = Draft202012Validator(finding_schema, registry=registry)
    for f in result1.findings:
        assert list(v.iter_errors(f)) == [], f.get("id")


def test_contradictions_written_and_pass_cross_ref_validation(tmp_path):
    # C5/I3: apply-clusters is the producer of contradictions.yaml. The emitted
    # file must (a) have the per-row shape (id contra-<sha8> + the 6 prose
    # fields, NO classification), (b) reference real ids so the EXISTING
    # validate.run_cross_file_pass contradiction cross-ref passes.
    run = _scaffold_two_finding_run(tmp_path)
    result = apply_clusters(run)
    assert len(result.contradictions) == 1
    row = result.contradictions[0]
    assert row["id"].startswith("contra-") and len(row["id"]) == len("contra-") + 8
    assert "classification" not in row  # adjudicator-only; stripped on disk
    contra = yaml.safe_load((run / "40-synthesis" / "contradictions.yaml").read_text())
    # Validate per-row against the EXISTING contradiction schema.
    from referencing import Registry, Resource
    resources = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            resources.append((s["$id"], Resource.from_contents(s)))
    registry = Registry().with_resources(resources)
    cschema = json.loads((SCHEMA_DIR / "contradiction.schema.json").read_text())
    v = Draft202012Validator(cschema, registry=registry)
    for r in contra["contradictions"]:
        assert list(v.iter_errors(r)) == [], r
    # Cross-file pass: contradictions.yaml references must resolve to real
    # finding/capability ids written into the run.
    report = run_cross_file_pass(run)
    dangling = [e for e in report.errors if "contradictions.yaml" in str(e.file)]
    assert dangling == [], [e.render() for e in dangling]


def test_stale_contradiction_downgrades_capability_and_logs_rejected(tmp_path):
    # I4: a 'stale' contradiction downgrades the named capability one maturity
    # notch (tested -> implemented) and logs a stale_capability_downgrade row.
    run = _scaffold_two_finding_run(tmp_path)
    result = apply_clusters(run)
    cap = next(c for c in result.capabilities if c["id"] == "conf-cap-89e19793")
    assert cap["maturity"] == "implemented"  # was "tested", down one notch
    downgrades = [r for r in result.rejected if r["category"] == "stale_capability_downgrade"]
    assert len(downgrades) == 1
    assert downgrades[0]["from_maturity"] == "tested"
    assert downgrades[0]["to_maturity"] == "implemented"
    # rejected-records.yaml validates against its schema (category + maturities).
    rej = yaml.safe_load((run / "40-synthesis" / "rejected-records.yaml").read_text())
    schema = json.loads((SCHEMA_DIR / "rejected-records.schema.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(rej)) == []


def test_missing_decisions_raises_adjudication_missing(tmp_path):
    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    (run / ".apd-run.yaml").write_text("run_id: t\n")
    try:
        apply_clusters(run)
        raise AssertionError("expected AdjudicationMissing")
    except AdjudicationMissing:
        pass


def test_cli_apply_clusters_smoke(tmp_path):
    run = _scaffold_two_finding_run(tmp_path)
    result = CliRunner().invoke(main, ["apply-clusters", str(run)])
    assert result.exit_code == 0, result.output
    assert (run / "40-synthesis" / "deduped-findings.yaml").exists()
    assert (run / "40-synthesis" / "deduped-capabilities.yaml").exists()
    assert (run / "40-synthesis" / "rejected-records.yaml").exists()
    assert (run / "40-synthesis" / "contradictions.yaml").exists()
    assert (run / "40-synthesis" / "severity-disagreements.yaml").exists()


def test_merge_confidence_takes_highest_of_sources(tmp_path):
    """Merged confidence = HIGHEST of sources (deliberate; no golden impact)."""
    run = _scaffold_two_finding_run(tmp_path)
    # Patch one source to low confidence so the two sources differ.
    nonrep_path = run / "30-auditability" / "non_repudiation.findings.yaml"
    doc = yaml.safe_load(nonrep_path.read_text())
    doc["finding"][0]["confidence"] = "low"  # nonrep-62124087 → low
    # immut-e09e4945 remains "high"
    nonrep_path.write_text(yaml.safe_dump(doc, sort_keys=False))
    result = apply_clusters(run)
    merged = next(f for f in result.findings if f.get("agent") == "synthesizer")
    assert merged["confidence"] == "high"  # highest of ["low", "high"] wins


def test_link_adds_reciprocal_cross_references(tmp_path):
    """A 'link' decision adds reciprocal cross_references to both records."""
    run = tmp_path / "run"
    (run / "10-trustworthiness").mkdir(parents=True)
    (run / "40-synthesis").mkdir()
    (run / ".apd-run.yaml").write_text("run_id: t\ndomain: pbm\n")
    # Two findings with ids that match the cross_references pattern.
    f_a = {
        "schema_version": 1, "id": "conf-aaaaaaaa", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "medium", "confidence": "medium",
        "title": "Finding A for link test",
        "summary": "Summary A.", "detail": "Detail A.",
        "evidence": [{"artifact": "a.md", "locator": "§1", "excerpt": "A excerpt"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {"posture": "required", "summary": "Fix A.", "detail": "Detail fix A."},
    }
    f_b = {
        "schema_version": 1, "id": "conf-bbbbbbbb", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "medium", "confidence": "medium",
        "title": "Finding B for link test",
        "summary": "Summary B.", "detail": "Detail B.",
        "evidence": [{"artifact": "b.md", "locator": "§2", "excerpt": "B excerpt"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {"posture": "required", "summary": "Fix B.", "detail": "Detail fix B."},
    }
    (run / "10-trustworthiness" / "confidentiality.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [f_a, f_b]}, sort_keys=False))
    decisions = {
        "schema_version": 1, "generated_by": "apd-cluster-adjudicator",
        "decisions": [{
            "group_id": "cluster-link-0001", "disposition": "link",
            "links": [{"from": "conf-aaaaaaaa", "to": "conf-bbbbbbbb"}],
        }],
        "contradictions": [],
        "_members": {},
    }
    (run / "40-synthesis" / "cluster-decisions.yaml").write_text(
        yaml.safe_dump(decisions, sort_keys=False))
    result = apply_clusters(run)
    by_id = {f["id"]: f for f in result.findings}
    assert "conf-aaaaaaaa" in by_id and "conf-bbbbbbbb" in by_id
    assert "conf-bbbbbbbb" in by_id["conf-aaaaaaaa"]["cross_references"]
    assert "conf-aaaaaaaa" in by_id["conf-bbbbbbbb"]["cross_references"]


def test_separate_copies_both_unchanged(tmp_path):
    """A 'separate' decision passes both records through unchanged (no merge, no cross_refs)."""
    run = tmp_path / "run"
    (run / "10-trustworthiness").mkdir(parents=True)
    (run / "40-synthesis").mkdir()
    (run / ".apd-run.yaml").write_text("run_id: t\ndomain: pbm\n")
    f_a = {
        "schema_version": 1, "id": "conf-cccccccc", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "low", "confidence": "low",
        "title": "Finding C for separate test",
        "summary": "Summary C.", "detail": "Detail C.",
        "evidence": [{"artifact": "c.md", "locator": "§3", "excerpt": "C excerpt"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {"posture": "required", "summary": "Fix C.", "detail": "Detail fix C."},
    }
    f_b = {
        "schema_version": 1, "id": "conf-dddddddd", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "low", "confidence": "low",
        "title": "Finding D for separate test",
        "summary": "Summary D.", "detail": "Detail D.",
        "evidence": [{"artifact": "d.md", "locator": "§4", "excerpt": "D excerpt"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {"posture": "required", "summary": "Fix D.", "detail": "Detail fix D."},
    }
    (run / "10-trustworthiness" / "confidentiality.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [f_a, f_b]}, sort_keys=False))
    decisions = {
        "schema_version": 1, "generated_by": "apd-cluster-adjudicator",
        "decisions": [{
            "group_id": "cluster-sep-0001", "disposition": "separate",
            "_members": ["conf-cccccccc", "conf-dddddddd"],
        }],
        "contradictions": [],
        "_members": {},
    }
    (run / "40-synthesis" / "cluster-decisions.yaml").write_text(
        yaml.safe_dump(decisions, sort_keys=False))
    result = apply_clusters(run)
    by_id = {f["id"]: f for f in result.findings}
    assert "conf-cccccccc" in by_id and "conf-dddddddd" in by_id
    # No cross_references added and no merged record.
    assert "cross_references" not in by_id["conf-cccccccc"]
    assert "cross_references" not in by_id["conf-dddddddd"]
    assert not any(f.get("agent") == "synthesizer" for f in result.findings)


def test_apply_excludes_preexisting_apath_from_deduped(tmp_path):
    """F4: apply-clusters runs BEFORE attack-path analysis, so it must not pull
    apath-* into deduped-findings.yaml even when a stale attack-path.findings.yaml
    is already present (a corruption-recovery re-run). apath is unioned downstream
    by the rollup + the report; if apply also emitted it, findings_array would
    render the apath finding twice.
    """
    run = tmp_path / "run"
    (run / "10-trustworthiness").mkdir(parents=True)
    (run / "40-synthesis").mkdir()
    (run / ".apd-run.yaml").write_text("run_id: t\ndomain: pbm\n")
    conf = {
        "schema_version": 1, "id": "conf-12121212", "agent": "confidentiality",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "gap",
        "severity": "medium", "confidence": "medium",
        "title": "Lens finding present before apath",
        "summary": "A specialist-lens finding in the corpus.",
        "detail": "This finding must survive apply-clusters unchanged.",
        "evidence": [{"artifact": "a.md", "locator": "§1", "excerpt": "x"}],
        "control_mappings": {"nist_800_53r5": ["SC-8"]},
        "recommendation": {"posture": "required", "summary": "Fix it.",
                           "detail": "Detailed remediation for the lens finding."},
    }
    apath = {
        "schema_version": 1, "id": "apath-99999999", "agent": "attack_path_analyzer",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality", "disposition": "risk",
        "severity": "high", "confidence": "high",
        "title": "Bottleneck edge to the crown jewel",
        "summary": "Stale attack-path finding from a prior partial run.",
        "detail": "Present on disk before apply re-runs in a recovery scenario.",
        "evidence": [{"artifact": "40-synthesis/attack-paths.yaml", "locator": "paths[0]",
                       "excerpt": "edge appears in 6 paths"}],
        "control_mappings": {"nist_800_53r5": ["SC-7"]},
        "recommendation": {"posture": "required", "summary": "Harden the edge.",
                           "detail": "Apply egress filtering on the bottleneck edge."},
    }
    (run / "10-trustworthiness" / "confidentiality.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [conf]}, sort_keys=False))
    # Stale apath file already on disk (the recovery scenario).
    (run / "40-synthesis" / "attack-path.findings.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "finding": [apath]}, sort_keys=False))
    (run / "40-synthesis" / "cluster-decisions.yaml").write_text(yaml.safe_dump(
        {"schema_version": 1, "generated_by": "apd-cluster-adjudicator",
         "decisions": [], "contradictions": [], "_members": {}}, sort_keys=False))
    result = apply_clusters(run)
    ids = {f["id"] for f in result.findings}
    assert "conf-12121212" in ids
    assert "apath-99999999" not in ids, "apath must not be folded into deduped by apply-clusters"
    deduped = yaml.safe_load((run / "40-synthesis" / "deduped-findings.yaml").read_text())
    assert "apath-99999999" not in {f["id"] for f in deduped["finding"]}


def test_cli_apply_clusters_exits_2_without_decisions(tmp_path):
    """apply-clusters exits with code 2 when cluster-decisions.yaml is absent."""
    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    (run / ".apd-run.yaml").write_text("run_id: t\ndomain: pbm\n")
    # No cluster-decisions.yaml written.
    result = CliRunner().invoke(main, ["apply-clusters", str(run)])
    assert result.exit_code == 2
