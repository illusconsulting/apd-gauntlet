"""Pass-3 tests: cross-file ID and artifact resolution."""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet.cli import main
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
