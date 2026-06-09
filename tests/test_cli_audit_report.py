"""audit-report: structural data.js<->YAML cross-check; exit 1 on FAIL."""
from __future__ import annotations

import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.audit import audit_report, parse_data_js
from click.testing import CliRunner

REPO = pathlib.Path(__file__).parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _copy_example(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    return dst


def test_parse_data_js_roundtrips_window_assignment(tmp_path):
    data_js = EXAMPLE / "40-synthesis" / "report-html" / "data.js"
    d = parse_data_js(data_js)
    assert "findings" in d and "meta" in d
    # 15 deduped + 1 apath (bounded: worst-per-pair + aggregate; PR4) + 3 tmeval =
    # 19 findings in the rendered data (F1: tmeval-* are first-class report findings;
    # PR4 bounded the per-path apath emitter so the long uncertainty tail collapses
    # into one aggregate finding).
    assert len(d["findings"]) == 19


def test_audit_passes_on_committed_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    assert result.status == "pass", [c for c in result.checks if c["status"] == "fail"]
    assert any(c["name"] == "id_coverage_findings" for c in result.checks)


def test_audit_writes_compact_report_audit_yaml(tmp_path):
    dst = _copy_example(tmp_path)
    audit_report(dst)
    out = dst / "40-synthesis" / "report-audit.yaml"
    doc = yaml.safe_load(out.read_text())
    assert doc["generated_by"] == "apd-gauntlet"
    assert doc["status"] in ("pass", "fail")
    # Compact: never embeds the full data.js (no 'findings' array).
    assert "findings" not in doc


def test_audit_fails_on_stale_data_js(tmp_path):
    dst = _copy_example(tmp_path)
    # Corrupt data.js so the recompute<->parsed diff and id-coverage fail.
    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    text = data_js.read_text().replace('"conf-7aa376c5"', '"conf-DELETED0"', 1)
    data_js.write_text(text)
    result = audit_report(dst)
    assert result.status == "fail"


def test_cli_audit_report_exit_code(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert result.exit_code == 0, result.output
    # Now break it: stale data.js -> exit 1.
    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    data_js.write_text(data_js.read_text().replace('"conf-7aa376c5"', '"conf-DELETED0"', 1))
    result2 = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert result2.exit_code == 1, result2.output


def test_audit_fails_gracefully_on_unparseable_data_js(tmp_path):
    dst = _copy_example(tmp_path)
    # Overwrite data.js with unparseable body — must not raise, must record FAIL check.
    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    data_js.write_text("window.APD_DATA = {not json,,,};", encoding="utf-8")
    result = audit_report(dst)
    assert result.status == "fail", "expected fail on unparseable data.js"
    failing = [c for c in result.checks if c["status"] == "fail"]
    assert any(c["name"] == "data_js_parse" for c in failing), \
        f"no data_js_parse check found; checks={result.checks}"
    out = dst / "40-synthesis" / "report-audit.yaml"
    assert out.is_file(), "report-audit.yaml must be written even on parse failure"
    # CLI must exit 1 on this run.
    cli_result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert cli_result.exit_code == 1, cli_result.output


def test_nist_rollup_parity_passes_on_committed_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    parity = [c for c in result.checks if c["name"] == "nist_rollup_parity"]
    assert parity, "nist_rollup_parity check must be emitted"
    assert parity[0]["status"] == "pass", parity[0]["detail"]


def test_nist_rollup_parity_fails_when_data_js_diverges(tmp_path):
    dst = _copy_example(tmp_path)
    # Diverge a data.js nist_rollup family count from the recompute. The committed
    # data.js is pretty-printed (json.dumps indent=2), so a single-line text
    # needle like '"family": "IA", "title"' has ZERO matches and cannot be used.
    # Instead: parse the dict, mutate one family's "covered", then re-serialize
    # the SAME way emit.write_data_js does (window.APD_DATA = json.dumps(indent=2,
    # ensure_ascii=False, sort_keys=False, allow_nan=False) + the '</' -> '<\\/'
    # escaping + ';\\n'). Calling write_data_js directly is the canonical mirror.
    from apd_gauntlet.report.emit import write_data_js

    data_js = dst / "40-synthesis" / "report-html" / "data.js"
    parsed = parse_data_js(data_js)
    assert parsed.get("nist_rollup"), "example data.js must carry nist_rollup rows"
    parsed["nist_rollup"][0]["covered"] = int(parsed["nist_rollup"][0].get("covered", 0)) + 9999
    write_data_js(parsed, data_js)
    # Round-trip sanity: the mutation persisted and re-parses cleanly.
    assert parse_data_js(data_js)["nist_rollup"][0]["covered"] >= 9999
    result = audit_report(dst)
    parity = [c for c in result.checks if c["name"] == "nist_rollup_parity"]
    assert parity and parity[0]["status"] == "fail", parity
    assert result.status == "fail"
    # CLI exits 1.
    cli_result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert cli_result.exit_code == 1, cli_result.output


def test_every_check_carries_a_valid_klass(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    assert result.checks, "expected at least one check"
    for c in result.checks:
        assert c["klass"] in ("structural", "editorial"), c
    # Pre-existing checks are all structural.
    sec = [c for c in result.checks if c["name"] == "section_errors_empty"]
    assert sec and sec[0]["klass"] == "structural"


def test_nist_rollup_parity_soft_on_transform_exception(tmp_path, monkeypatch):
    dst = _copy_example(tmp_path)
    # Force the recompute to raise; the parity check must record a NON-blocking soft entry.
    import apd_gauntlet.synthesis.audit as audit_mod

    def _boom(*a, **k):
        raise RuntimeError("synthetic transform failure")

    # Patch the rollup recompute path used by the new parity check.
    monkeypatch.setattr(audit_mod, "_recompute_nist_rollup", _boom, raising=True)
    result = audit_report(dst)
    parity = [c for c in result.checks if c["name"] == "nist_rollup_parity"]
    assert parity, "parity check must still be emitted on transform failure"
    # Soft: the parity check itself reports pass (non-blocking) and notes the exception.
    assert parity[0]["status"] == "pass"
    assert "exception" in parity[0]["detail"].lower() or "skipped" in parity[0]["detail"].lower()


def _mutate_data_js(dst, fn):
    """Parse the example data.js, apply fn(dict), re-emit it canonically."""
    from apd_gauntlet.report.emit import write_data_js
    p = dst / "40-synthesis" / "report-html" / "data.js"
    d = parse_data_js(p)
    fn(d)
    write_data_js(d, p)


def test_exec_summary_present_passes_on_enriched_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "exec_summary_present"]
    assert c and c[0]["status"] == "pass", c
    assert c[0]["klass"] == "editorial"


def test_exec_summary_present_fails_on_placeholder(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__(
        "exec_summary", ["Run summary not provided by synthesizer."]))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "exec_summary_present"]
    assert c and c[0]["status"] == "fail", c
    assert result.status == "fail"


def test_exec_summary_present_exempt_when_empty_run(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: (
        d["meta"].__setitem__("is_empty_run", True),
        d.__setitem__("exec_summary", ["Run summary not provided by synthesizer."]),
    ))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "exec_summary_present"]
    assert c and c[0]["status"] == "pass", "empty run is exempt"


def test_editorial_sections_present_fails_when_report_data_absent(tmp_path):
    dst = _copy_example(tmp_path)
    (dst / "40-synthesis" / "report-data.yaml").unlink()
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "editorial_sections_present"]
    assert c and c[0]["status"] == "fail", c
    assert c[0]["klass"] == "editorial"


def test_editorial_sections_fails_gracefully_on_malformed_report_data(tmp_path):
    dst = _copy_example(tmp_path)
    (dst / "40-synthesis" / "report-data.yaml").write_text("key: [unclosed\n", encoding="utf-8")
    result = audit_report(dst)  # must NOT raise
    c = [x for x in result.checks if x["name"] == "editorial_sections_present"]
    assert c and c[0]["status"] == "fail", c
    audit_artifact = dst / "40-synthesis" / "report-audit.yaml"
    assert audit_artifact.is_file(), "audit must still write its artifact"


def test_attack_paths_present_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "pass", c
    assert c[0]["klass"] == "structural"


def test_attack_paths_present_fails_when_section_null_but_graph_exists(tmp_path):
    dst = _copy_example(tmp_path)  # has asset-graph.yaml
    _mutate_data_js(dst, lambda d: d.__setitem__("attack_paths", None))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "fail", c


def test_attack_paths_present_exempt_when_not_activated(tmp_path):
    dst = _copy_example(tmp_path)
    (dst / "40-synthesis" / "asset-graph.yaml").unlink()
    _mutate_data_js(dst, lambda d: d.__setitem__("attack_paths", None))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "pass", "no asset-graph.yaml -> exempt"


def test_attack_paths_present_handles_nondict_section(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__("attack_paths", []))
    result = audit_report(dst)  # must NOT raise
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "fail", c
    audit_artifact = dst / "40-synthesis" / "report-audit.yaml"
    assert audit_artifact.is_file(), "audit must still write its artifact"


def _overlay(edge_id="e1"):
    return {
        "edge_id": edge_id, "paths_traversing": 3,
        "exposed_attack_techniques": ["T1078"],
        "candidate_d3fend": [
            {"d3fend_id": "D3-MFA", "counters": ["T1078"],
             "rationale": "multi-factor auth counters valid-accounts abuse here"}
        ],
        "existing_capability_backing": [], "net_new_d3fend": ["D3-MFA"],
    }


def test_d3fend_overlay_exempt_when_no_overlays(tmp_path):
    dst = _copy_example(tmp_path)  # defense-graph.yaml has 0 overlays
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "pass", c


def test_d3fend_overlay_fails_when_defense_graph_overlays_dropped(tmp_path):
    dst = _copy_example(tmp_path)
    dg = dst / "40-synthesis" / "defense-graph.yaml"
    doc = yaml.safe_load(dg.read_text()) or {}
    doc["bottleneck_overlays"] = [_overlay()]
    dg.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    _mutate_data_js(dst, lambda d: d["attack_paths"].__setitem__("bottleneck_overlays", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "fail", c


def test_d3fend_overlay_passes_when_counts_match(tmp_path):
    dst = _copy_example(tmp_path)
    dg = dst / "40-synthesis" / "defense-graph.yaml"
    doc = yaml.safe_load(dg.read_text()) or {}
    doc["bottleneck_overlays"] = [_overlay()]
    dg.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    _mutate_data_js(
        dst,
        lambda d: d["attack_paths"].__setitem__("bottleneck_overlays", [_overlay()]),
    )
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "pass", c


def test_d3fend_overlay_exempt_when_defense_graph_missing(tmp_path):
    dst = _copy_example(tmp_path)
    (dst / "40-synthesis" / "defense-graph.yaml").unlink()
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "pass", c


def test_d3fend_overlay_handles_nonlist_bottleneck_overlays(tmp_path):
    dst = _copy_example(tmp_path)
    dg = dst / "40-synthesis" / "defense-graph.yaml"
    doc = yaml.safe_load(dg.read_text()) or {}
    doc["bottleneck_overlays"] = [_overlay()]
    dg.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    _mutate_data_js(dst, lambda d: d["attack_paths"].__setitem__("bottleneck_overlays", 42))
    result = audit_report(dst)  # must NOT raise
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "fail", c
    assert (dst / "40-synthesis" / "report-audit.yaml").is_file()


def test_apd_matrix_nonempty_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "apd_matrix_nonempty"]
    assert c and c[0]["status"] == "pass", c


def test_apd_matrix_nonempty_fails_when_rows_empty_but_findings_exist(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d["apd_matrix"].__setitem__("rows", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "apd_matrix_nonempty"]
    assert c and c[0]["status"] == "fail", c


def test_apd_matrix_nonempty_handles_nondict_matrix(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__("apd_matrix", []))
    result = audit_report(dst)  # must NOT raise
    c = [x for x in result.checks if x["name"] == "apd_matrix_nonempty"]
    assert c and c[0]["status"] == "fail", c
    assert (dst / "40-synthesis" / "report-audit.yaml").is_file()


def test_coverage_rollups_nonempty_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"]
    assert c and c[0]["status"] == "pass", c


def test_coverage_rollups_fail_when_nist_rollup_dropped(tmp_path):
    dst = _copy_example(tmp_path)  # nist-coverage.yaml has controls
    _mutate_data_js(dst, lambda d: d.__setitem__("nist_rollup", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"]
    assert c and c[0]["status"] == "fail", c


def test_coverage_rollups_fail_when_attack_exposure_dropped(tmp_path):
    dst = _copy_example(tmp_path)  # attack-exposure.yaml has techniques
    _mutate_data_js(dst, lambda d: d.__setitem__("attack_exposure", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"]
    assert c and c[0]["status"] == "fail", c


def test_taxonomy_titles_resolve_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "taxonomy_titles_resolve"]
    assert c and c[0]["status"] == "pass", c


def test_taxonomy_titles_resolve_fails_on_bare_id(tmp_path):
    dst = _copy_example(tmp_path)
    def _bare(d):
        # Force one taxonomy entry's title to equal its id (a bare-ID tooltip).
        k = next(iter(d["taxonomy"]))
        d["taxonomy"][k]["title"] = k
    _mutate_data_js(dst, _bare)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "taxonomy_titles_resolve"]
    assert c and c[0]["status"] == "fail", c


def test_taxonomy_titles_resolve_handles_nondict_taxonomy(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__("taxonomy", []))
    result = audit_report(dst)  # must NOT raise
    c = [x for x in result.checks if x["name"] == "taxonomy_titles_resolve"]
    assert c and c[0]["status"] == "pass", "empty/absent taxonomy has no bare ids -> pass"
    assert (dst / "40-synthesis" / "report-audit.yaml").is_file()


def test_cli_audit_report_prints_per_class_counts(tmp_path):
    dst = _copy_example(tmp_path)
    # Break one editorial check (placeholder exec summary).
    _mutate_data_js(dst, lambda d: d.__setitem__(
        "exec_summary", ["Run summary not provided by synthesizer."]))
    result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert result.exit_code == 1, result.output
    assert "editorial_failed=1" in result.output
    assert "structural_failed=0" in result.output


def test_completeness_gate_passes_after_build_on_canonical_example(tmp_path):
    """Build the report fresh from the committed YAMLs, then audit — exercises the
    full build -> audit path on the one shipped (synthetic) example run."""
    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed


def test_completeness_gate_passes_on_enriched_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed
    names = {c["name"] for c in result.checks}
    for expected in (
        "exec_summary_present", "editorial_sections_present", "attack_paths_present",
        "d3fend_overlay_present", "apd_matrix_nonempty", "coverage_rollups_nonempty",
        "taxonomy_titles_resolve", "section_errors_empty",
    ):
        assert expected in names, f"missing check {expected}"


def test_audit_handles_nondict_taxonomy_scalar(tmp_path):
    # A non-container taxonomy (int) must not crash id_coverage_nist or check #7.
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__("taxonomy", 42))
    result = audit_report(dst)  # must NOT raise
    assert (dst / "40-synthesis" / "report-audit.yaml").is_file()
    tax_check = [c for c in result.checks if c["name"] == "taxonomy_titles_resolve"]
    assert tax_check and tax_check[0]["status"] == "pass"  # no entries -> no bare ids


def test_threat_model_scene_coherent_passes_on_example(tmp_path):
    # Build the report fresh from the committed YAMLs so data.js carries the
    # populated threat_model block (the shipped data.js is regenerated in a later
    # task; building here exercises the present-and-coherent path explicitly).
    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "threat_model_scene_coherent"]
    assert c and c[0]["status"] == "pass"
    assert c[0]["klass"] == "structural"


def test_threat_model_scene_coherent_exempt_when_absent(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__("threat_model", {"present": False}))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "threat_model_scene_coherent"]
    assert c and c[0]["status"] == "pass"   # absent → exempt


def test_threat_model_scene_coherent_fails_when_present_but_empty(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__(
        "threat_model", {"present": True, "entries": [], "stride_matrix": {"rows": []}}))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "threat_model_scene_coherent"]
    assert c and c[0]["status"] == "fail"
    assert result.status == "fail"


def test_attack_paths_present_checks_structured_graph(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"][0]
    assert c["status"] == "pass"
    assert "graph_nodes=" in c["detail"]   # detail now reports structured graph size


# ---------------------------------------------------------------------------
# count_parity passthrough + internal-consistency (Task 6)
# ---------------------------------------------------------------------------

def test_count_parity_passes_on_faithful_build(tmp_path):
    """After a fresh build, data.js.summary must faithfully carry metrics.yaml —
    both parity checks and the new internal-consistency check must pass."""
    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    sev = [c for c in result.checks if c["name"] == "count_parity_severity"][0]
    tot = [c for c in result.checks if c["name"] == "count_parity_totals"][0]
    con = [c for c in result.checks if c["name"] == "metrics_internal_consistency"][0]
    assert sev["status"] == "pass", sev["detail"]
    assert tot["status"] == "pass", tot["detail"]
    assert con["status"] == "pass", con["detail"]


def test_count_parity_fails_when_data_js_diverges_from_metrics(tmp_path):
    """Perturbing metrics.yaml AFTER the build (so data.js no longer matches)
    must trip count_parity_severity."""
    import yaml as _yaml

    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    mpath = dst / "40-synthesis" / "metrics.yaml"
    doc = _yaml.safe_load(mpath.read_text())
    doc["bySeverity"]["critical"] = doc["bySeverity"]["critical"] + 5
    doc["findings_total"] = doc["findings_total"] + 5
    mpath.write_text(_yaml.safe_dump(doc, sort_keys=False))
    result = audit_report(dst)
    sev = [c for c in result.checks if c["name"] == "count_parity_severity"][0]
    assert sev["status"] == "fail", sev["detail"]


def test_metrics_internal_consistency_fails_on_broken_invariant(tmp_path):
    """Breaking sum(bySeverity) == findings_total (while keeping data.js in sync
    so parity stays OK) must trip metrics_internal_consistency."""
    import yaml as _yaml
    from apd_gauntlet.report.build import build_report as _build_report

    dst = _copy_example(tmp_path)
    mpath = dst / "40-synthesis" / "metrics.yaml"
    doc = _yaml.safe_load(mpath.read_text())
    doc["findings_total"] = doc["findings_total"] + 7  # break sum(bySeverity)==total
    mpath.write_text(_yaml.safe_dump(doc, sort_keys=False))
    # Rebuild data.js so it faithfully carries the corrupted total (parity stays OK).
    _build_report(dst, out_dir=dst / "40-synthesis" / "report-html")
    result = audit_report(dst)
    con = [c for c in result.checks if c["name"] == "metrics_internal_consistency"][0]
    assert con["status"] == "fail", con["detail"]


def test_metrics_present_fails_when_metrics_yaml_absent(tmp_path):
    """Deleting metrics.yaml after the build must trip the metrics_present check."""
    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    (dst / "40-synthesis" / "metrics.yaml").unlink()
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "metrics_present"][0]
    assert c["status"] == "fail"
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# id_coverage_masvs / id_coverage_maswe (OWASP MAS — subset of taxonomy keys)
# ---------------------------------------------------------------------------

def test_id_coverage_mas_exempt_when_no_mas_findings(tmp_path):
    """The shipped example cites no MAS ids, so both checks pass vacuously."""
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    names = {c["name"] for c in result.checks}
    assert "id_coverage_masvs" in names
    assert "id_coverage_maswe" in names
    masvs = [c for c in result.checks if c["name"] == "id_coverage_masvs"][0]
    maswe = [c for c in result.checks if c["name"] == "id_coverage_maswe"][0]
    assert masvs["status"] == "pass" and masvs["klass"] == "structural", masvs
    assert maswe["status"] == "pass" and maswe["klass"] == "structural", maswe


def test_id_coverage_masvs_fails_on_cited_id_missing_from_taxonomy(tmp_path):
    """A finding citing a MASVS id with no matching taxonomy entry FAILS."""
    dst = _copy_example(tmp_path)

    def _add(d):
        d["findings"][0].setdefault("mappings", {})["masvs"] = ["MASVS-STORAGE-1"]
        # Deliberately do NOT add MASVS-STORAGE-1 to d["taxonomy"].
    _mutate_data_js(dst, _add)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "id_coverage_masvs"][0]
    assert c["status"] == "fail", c
    assert "MASVS-STORAGE-1" in c["detail"]
    assert result.status == "fail"


def test_id_coverage_maswe_fails_on_cited_id_missing_from_taxonomy(tmp_path):
    """A finding citing a MASWE id with no matching taxonomy entry FAILS."""
    dst = _copy_example(tmp_path)

    def _add(d):
        d["findings"][0].setdefault("mappings", {})["maswe"] = ["MASWE-0001"]
    _mutate_data_js(dst, _add)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "id_coverage_maswe"][0]
    assert c["status"] == "fail", c
    assert "MASWE-0001" in c["detail"]


def test_id_coverage_masvs_passes_when_cited_id_present_in_taxonomy(tmp_path):
    """Citing a MASVS id that IS a taxonomy key keeps the check green."""
    dst = _copy_example(tmp_path)

    def _add(d):
        d["findings"][0].setdefault("mappings", {})["masvs"] = ["MASVS-STORAGE-1"]
        d["taxonomy"]["MASVS-STORAGE-1"] = {
            "family": "OWASP MASVS", "title": "The app securely stores sensitive data."}
    _mutate_data_js(dst, _add)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "id_coverage_masvs"][0]
    assert c["status"] == "pass", c


# ---------------------------------------------------------------------------
# coverage_rollups_nonempty — MAS extension (active + cited => rows required)
# ---------------------------------------------------------------------------

def test_coverage_rollups_mas_exempt_when_inactive(tmp_path):
    """No 'masvs'/'maswe' in meta.active_taxonomies => MAS does not gate the check."""
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "pass", c


def test_coverage_rollups_mas_exempt_when_active_but_no_findings(tmp_path):
    """MASVS active but ZERO findings cite a MASVS id => exempt (no empty-rows penalty)."""
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d["meta"].__setitem__("active_taxonomies", ["masvs", "maswe"]))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "pass", c


def test_coverage_rollups_fail_when_masvs_active_cited_but_rows_empty(tmp_path):
    """MASVS active + a finding cites a MASVS id, but masvs_coverage rows are empty => FAIL."""
    dst = _copy_example(tmp_path)

    def _mut(d):
        d["meta"]["active_taxonomies"] = ["masvs", "maswe"]
        d["findings"][0].setdefault("mappings", {})["masvs"] = ["MASVS-STORAGE-1"]
        d["taxonomy"]["MASVS-STORAGE-1"] = {"family": "OWASP MASVS", "title": "Secure storage."}
        d["masvs_coverage"] = []  # rendered rollup dropped
    _mutate_data_js(dst, _mut)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "fail", c
    assert "masvs" in c["detail"]
    assert result.status == "fail"


def test_coverage_rollups_fail_when_maswe_active_cited_but_rows_empty(tmp_path):
    """MASWE active + a finding cites a MASWE id, but maswe_coverage rows are empty => FAIL."""
    dst = _copy_example(tmp_path)

    def _mut(d):
        d["meta"]["active_taxonomies"] = ["masvs", "maswe"]
        d["findings"][0].setdefault("mappings", {})["maswe"] = ["MASWE-0001"]
        d["taxonomy"]["MASWE-0001"] = {
            "family": "OWASP MASWE", "title": "Sensitive data stored unencrypted."}
        d["maswe_coverage"] = []
    _mutate_data_js(dst, _mut)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "fail", c
    assert "maswe" in c["detail"]


def test_coverage_rollups_pass_when_mas_active_cited_and_rows_present(tmp_path):
    """MASVS+MASWE active + cited + non-empty rendered rows => PASS."""
    dst = _copy_example(tmp_path)

    def _mut(d):
        d["meta"]["active_taxonomies"] = ["masvs", "maswe"]
        cm = d["findings"][0].setdefault("mappings", {})
        cm["masvs"] = ["MASVS-STORAGE-1"]
        cm["maswe"] = ["MASWE-0001"]
        d["taxonomy"]["MASVS-STORAGE-1"] = {"family": "OWASP MASVS", "title": "Secure storage."}
        d["taxonomy"]["MASWE-0001"] = {
            "family": "OWASP MASWE", "title": "Sensitive data unencrypted."}
        d["masvs_coverage"] = [{"masvs_id": "MASVS-STORAGE-1", "finding_count": 1}]
        d["maswe_coverage"] = [{"maswe_id": "MASWE-0001", "finding_count": 1}]
    _mutate_data_js(dst, _mut)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"][0]
    assert c["status"] == "pass", c


def test_completeness_gate_emits_all_mas_checks_and_stays_green(tmp_path):
    """The committed example cites no MAS ids and declares no active MAS taxonomy,
    so the new checks are emitted AND pass, leaving overall status pass."""
    dst = _copy_example(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed
    names = {c["name"] for c in result.checks}
    for expected in ("id_coverage_masvs", "id_coverage_maswe", "coverage_rollups_nonempty"):
        assert expected in names, f"missing check {expected}"
    # Every check still carries a valid klass.
    for c in result.checks:
        assert c["klass"] in ("structural", "editorial"), c


# ---------------------------------------------------------------------------
# Shipped mobile-example audit (MAS-enabled run) — build then audit
# ---------------------------------------------------------------------------

MOBILE = REPO / "examples" / "apd-20260602-acme-mobile-banking" / "expected"


def _copy_mobile(tmp_path):
    dst = tmp_path / "mobile"
    shutil.copytree(MOBILE, dst)
    return dst


def test_mobile_example_audit_passes_after_build_with_mas_coverage(tmp_path):
    """Build the mobile report fresh from the committed YAMLs, then audit — the
    MAS-enabled run must pass the completeness gate with MAS id-coverage present.
    report-html/ is gitignored, so the audit MUST build-report first (CI lesson)."""
    dst = _copy_mobile(tmp_path)
    build = CliRunner().invoke(main, ["build-report", str(dst), "--quiet"])
    assert build.exit_code == 0, build.output
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed
    names = {c["name"] for c in result.checks}
    # The MAS id-coverage gate checks must be present (they guard against bare,
    # unresolved ids leaking into the report).
    assert "id_coverage_masvs" in names
    assert "id_coverage_maswe" in names
    masvs_check = [c for c in result.checks if c["name"] == "id_coverage_masvs"][0]
    maswe_check = [c for c in result.checks if c["name"] == "id_coverage_maswe"][0]
    assert masvs_check["status"] == "pass", masvs_check
    assert maswe_check["status"] == "pass", maswe_check
    # The id-coverage gate passes vacuously when no MAS id is cited, so assert the
    # SUBSTANTIVE evidence directly: the rendered data.js findings must carry the
    # mobile run's MAS mappings (a regression that drops MAS rendering fails here).
    parsed = parse_data_js(dst / "40-synthesis" / "report-html" / "data.js")
    rendered_masvs: set[str] = set()
    rendered_maswe: set[str] = set()
    for f in parsed.get("findings", []):
        mappings = f.get("mappings") or {}
        rendered_masvs.update(mappings.get("masvs") or [])
        rendered_maswe.update(mappings.get("maswe") or [])
    assert {"MASVS-CRYPTO-2", "MASVS-STORAGE-1", "MASVS-AUTH-1"} <= rendered_masvs, \
        f"mobile run lost MASVS mappings in data.js: {sorted(rendered_masvs)}"
    assert {"MASWE-0014", "MASWE-0006", "MASWE-0042"} <= rendered_maswe, \
        f"mobile run lost MASWE mappings in data.js: {sorted(rendered_maswe)}"
    # And the populated coverage rollups must carry rows for those same ids.
    synth = dst / "40-synthesis"
    masvs_cov = yaml.safe_load((synth / "masvs-coverage.yaml").read_text())
    maswe_cov = yaml.safe_load((synth / "maswe-coverage.yaml").read_text())
    cov_masvs = {row["masvs_id"] for row in masvs_cov.get("controls", [])}
    cov_maswe = {row["maswe_id"] for row in maswe_cov.get("entries", [])}
    assert {"MASVS-CRYPTO-2", "MASVS-STORAGE-1", "MASVS-AUTH-1"} <= cov_masvs, cov_masvs
    assert {"MASWE-0014", "MASWE-0006", "MASWE-0042"} <= cov_maswe, cov_maswe
