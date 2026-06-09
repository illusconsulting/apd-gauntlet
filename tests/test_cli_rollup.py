"""rollup: emits the canonical list-shaped coverage YAMLs validated by the doc-wrappers."""
from __future__ import annotations

import json
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.validate import build_registry
from click.testing import CliRunner
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _copy_example(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    return dst


def _validate(doc, schema_name):
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    return list(Draft202012Validator(schema, registry=build_registry()).iter_errors(doc))


def test_rollup_emits_doc_wrapper_valid_nist_attack_matrix(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["rollup", str(dst)])
    assert result.exit_code == 0, result.output
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    assert _validate(nist, "nist-coverage-doc.schema.json") == []
    attack = yaml.safe_load((dst / "40-synthesis" / "attack-exposure.yaml").read_text())
    assert _validate(attack, "attack-exposure-doc.schema.json") == []
    matrix = yaml.safe_load((dst / "40-synthesis" / "apd-coverage-matrix.yaml").read_text())
    assert _validate(matrix, "coverage-matrix-doc.schema.json") == []


def test_nist_finding_count_equals_len_finding_ids(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    for ctrl in nist["controls"]:
        assert ctrl["finding_count"] == len(ctrl["finding_ids"])
        assert ctrl["capability_count"] == len(ctrl["capability_ids"])
        has_f, has_c = bool(ctrl["finding_ids"]), bool(ctrl["capability_ids"])
        expect = ("gapped_and_covered" if has_f and has_c
                  else "gapped" if has_f else "covered" if has_c else "silent")
        assert ctrl["posture"] == expect


def test_attack_technique_present_only_if_a_finding_maps_it(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    attack = yaml.safe_load((dst / "40-synthesis" / "attack-exposure.yaml").read_text())
    for tech in attack["techniques"]:
        assert tech["exposure_finding_count"] >= 1


def test_attack_name_never_empty_and_schema_valid(tmp_path):
    # C4: name must be looked up (minLength:3); name:"" would FAIL the wrapper
    # schema. Validate via the doc-wrapper AND assert each name is non-empty.
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    attack = yaml.safe_load((dst / "40-synthesis" / "attack-exposure.yaml").read_text())
    assert _validate(attack, "attack-exposure-doc.schema.json") == []
    for tech in attack["techniques"]:
        assert len(tech["name"]) >= 3, tech["id"]
    # T1530 resolves to its real title from the bundled catalog.
    by_id = {t["id"]: t for t in attack["techniques"]}
    if "T1530" in by_id:
        assert by_id["T1530"]["name"] == "Data from Cloud Storage"


def test_owasp_d3fend_names_resolved_when_declared(tmp_path):
    # I2: owasp/d3fend names come from the bundled catalogs, not raw ids.
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    owasp = dst / "40-synthesis" / "owasp-coverage.yaml"
    if owasp.exists():
        doc = yaml.safe_load(owasp.read_text())
        for e in doc["entries"]:
            # A resolved name is non-empty; for known cats it differs from the id.
            assert e["name"]
            if e["category_id"] == "API2:2023":
                assert e["name"] == "Broken Authentication"
    d3 = dst / "40-synthesis" / "d3fend-coverage.yaml"
    if d3.exists():
        doc = yaml.safe_load(d3.read_text())
        for e in doc["defensive_entries"]:
            assert e["name"]


def test_matrix_emits_all_nine_goals_per_component(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["rollup", str(dst)])
    matrix = yaml.safe_load((dst / "40-synthesis" / "apd-coverage-matrix.yaml").read_text())
    nine = {"confidentiality", "integrity", "availability", "distributed", "resilient",
            "ephemeral", "authenticity", "non_repudiation", "immutability"}
    for comp in matrix["components"]:
        assert set(comp["cells"].keys()) == nine


def test_cwe_owasp_d3fend_emitted_only_when_declared(tmp_path):
    dst = _copy_example(tmp_path)
    # The example .apd-run.yaml declares taxonomies; rollup should emit cwe/owasp/d3fend.
    CliRunner().invoke(main, ["rollup", str(dst)])
    cwe = dst / "40-synthesis" / "cwe-coverage.yaml"
    if cwe.exists():
        doc = yaml.safe_load(cwe.read_text())
        assert doc["generated_by"] == "synthesizer"
        assert _validate(doc, "cwe-coverage.schema.json") == []


def _build_minimal_run(tmp_path, run_yaml: str, findings_yaml: str, caps_yaml: str) -> pathlib.Path:
    """Construct a minimal run dir that build_rollups / the rollup CLI can consume."""
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    ctx = run_dir / "00-context"
    synth.mkdir(parents=True)
    ctx.mkdir(parents=True)
    (run_dir / ".apd-run.yaml").write_text(run_yaml, encoding="utf-8")
    (synth / "deduped-findings.yaml").write_text(findings_yaml, encoding="utf-8")
    (synth / "deduped-capabilities.yaml").write_text(caps_yaml, encoding="utf-8")
    (ctx / "asset-inventory.yaml").write_text("assets: []\n", encoding="utf-8")
    return run_dir


def test_nist_title_never_below_minlength_for_unknown_control(tmp_path):
    """Fix 1: title fallback must be >=5 chars even for controls not in catalog or families."""
    run_yaml = "run_id: test-run\ndomain: pbm\nframeworkversion: '1.0'\n"
    # ZZ is not a real NIST family and is not in nist-families.json → fallback fires
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      nist_800_53r5: [\"ZZ-99\"]\n"
    )
    caps_yaml = "capability: []\n"
    run_dir = _build_minimal_run(tmp_path, run_yaml, findings_yaml, caps_yaml)

    from apd_gauntlet.synthesis.rollup import build_rollups
    result = build_rollups(run_dir)

    for row in result.nist:
        assert len(row["title"]) >= 5, f"title too short for {row['id']!r}: {row['title']!r}"

    nist_doc = yaml.safe_load((run_dir / "40-synthesis" / "nist-coverage.yaml").read_text())
    assert _validate(nist_doc, "nist-coverage-doc.schema.json") == []


def test_d3fend_rollup_merges_duplicate_techniques(tmp_path):
    """Fixes 2 & 3: two caps citing same D3FEND id → one row; two findings citing same
    ATT&CK technique → one counter_coverage row."""
    run_yaml = "run_id: test-d3fend\ndomain: pbm\ntaxonomies: [d3fend, mitre_attack]\n"
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-f1111111\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      mitre_attack:\n"
        "        - technique: T1530\n"
        "          tactic: TA0010\n"
        "  - schema_version: 1\n"
        "    id: conf-f2222222\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      mitre_attack:\n"
        "        - technique: T1530\n"
        "          tactic: TA0010\n"
    )
    caps_yaml = (
        "capability:\n"
        "  - schema_version: 1\n"
        "    id: conf-cap-c1111111\n"
        "    apd_goal: confidentiality\n"
        "    control_mappings:\n"
        "      d3fend:\n"
        "        - technique: D3-AE\n"
        "  - schema_version: 1\n"
        "    id: conf-cap-c2222222\n"
        "    apd_goal: confidentiality\n"
        "    control_mappings:\n"
        "      d3fend:\n"
        "        - technique: D3-AE\n"
    )
    run_dir = _build_minimal_run(tmp_path, run_yaml, findings_yaml, caps_yaml)

    result = CliRunner().invoke(main, ["rollup", str(run_dir)])
    assert result.exit_code == 0, result.output

    d3_doc = yaml.safe_load((run_dir / "40-synthesis" / "d3fend-coverage.yaml").read_text())
    assert _validate(d3_doc, "d3fend-coverage.schema.json") == []

    # One defensive entry for D3-AE, capability_count == 2
    d_entries = d3_doc["defensive_entries"]
    d3ae_rows = [e for e in d_entries if e["d3fend_id"] == "D3-AE"]
    assert len(d3ae_rows) == 1, f"expected 1 row for D3-AE, got {len(d3ae_rows)}"
    assert d3ae_rows[0]["capability_count"] == 2
    assert sorted(d3ae_rows[0]["capability_ids"]) == ["conf-cap-c1111111", "conf-cap-c2222222"]

    # One counter_coverage row for T1530, exposed_by_finding_count == 2
    ctr = d3_doc["counter_coverage"]
    t1530_rows = [e for e in ctr if e["attack_technique"] == "T1530"]
    assert len(t1530_rows) == 1, f"expected 1 row for T1530, got {len(t1530_rows)}"
    assert t1530_rows[0]["exposed_by_finding_count"] == 2
    assert sorted(t1530_rows[0]["exposed_by_finding_ids"]) == ["conf-f1111111", "conf-f2222222"]


def test_atlas_coverage_emitted_only_when_declared(tmp_path):
    """atlas-coverage.yaml is written iff the run declares mitre_atlas; the rows
    group by atlas_id, resolve names from the bundled catalog, and validate."""
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: intg-a1111111\n"
        "    apd_goal: integrity\n"
        "    disposition: gap\n"
        "    evidence:\n"
        "      - artifact: plan.md\n"
        "        locator: '§3'\n"
        "    control_mappings:\n"
        "      atlas: [AML.T0051, AML.T0051.000]\n"
        "  - schema_version: 1\n"
        "    id: intg-a2222222\n"
        "    apd_goal: integrity\n"
        "    disposition: gap\n"
        "    evidence:\n"
        "      - artifact: plan.md\n"
        "        locator: '§4'\n"
        "    control_mappings:\n"
        "      atlas: [AML.T0051]\n"
    )
    caps_yaml = "capability: []\n"

    # 1) Not declared → file absent.
    undeclared = _build_minimal_run(
        tmp_path / "u", "run_id: t\ndomain: agentic-ai\n", findings_yaml, caps_yaml
    )
    CliRunner().invoke(main, ["rollup", str(undeclared)])
    assert not (undeclared / "40-synthesis" / "atlas-coverage.yaml").exists()

    # 2) Declared → file present, valid, grouped by atlas_id with resolved names.
    declared = _build_minimal_run(
        tmp_path / "d",
        "run_id: t\ndomain: agentic-ai\ntaxonomies: [mitre_atlas]\n",
        findings_yaml,
        caps_yaml,
    )
    result = CliRunner().invoke(main, ["rollup", str(declared)])
    assert result.exit_code == 0, result.output
    doc = yaml.safe_load((declared / "40-synthesis" / "atlas-coverage.yaml").read_text())
    assert _validate(doc, "atlas-coverage.schema.json") == []
    by_id = {e["atlas_id"]: e for e in doc["entries"]}
    # AML.T0051 cited by two findings → one row, finding_count == 2.
    assert by_id["AML.T0051"]["finding_count"] == 2
    assert by_id["AML.T0051"]["name"] == "LLM Prompt Injection"
    assert sorted(by_id["AML.T0051"]["finding_ids"]) == ["intg-a1111111", "intg-a2222222"]
    # Sub-technique resolves with a parent-prefixed name.
    assert ":" in by_id["AML.T0051.000"]["name"]


def test_rollup_result_has_masvs_and_maswe_fields():
    from apd_gauntlet.synthesis.rollup import RollupResult

    rr = RollupResult()
    assert rr.masvs is None
    assert rr.maswe is None


def test_maswe_rollup_groups_by_id_with_surfaces_and_first_appearance_order():
    from apd_gauntlet.synthesis.rollup import _maswe_rollup
    findings = [
        {"id": "intg-b2222222", "evidence": [{"artifact": "p.md", "locator": "src/B.kt:9"}],
         "control_mappings": {"maswe": ["MASWE-0002"]}},
        {"id": "conf-a1111111", "evidence": [{"artifact": "p.md", "locator": "src/A.kt:3"}],
         "control_mappings": {"maswe": ["MASWE-0001"]}},
        {"id": "conf-a3333333", "evidence": [{"artifact": "p.md", "locator": "src/A.kt:7"}],
         "control_mappings": {"maswe": ["MASWE-0001"]}},
    ]
    doc = _maswe_rollup(findings)
    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "synthesizer"
    by_id = {e["maswe_id"]: e for e in doc["entries"]}
    # MASWE-0002 cited first → appears before MASWE-0001 (first-appearance order).
    assert [e["maswe_id"] for e in doc["entries"]] == ["MASWE-0002", "MASWE-0001"]
    # MASWE-0001 cited by two findings → one entry, finding_count == 2, sorted ids + surfaces.
    assert by_id["MASWE-0001"]["finding_count"] == 2
    assert by_id["MASWE-0001"]["finding_ids"] == ["conf-a1111111", "conf-a3333333"]
    assert by_id["MASWE-0001"]["surfaces"] == ["src/A.kt:3", "src/A.kt:7"]
    # name/category/status/parent_masvs resolved from the maswe.json catalog.
    assert by_id["MASWE-0001"]["category"] == "MASVS-STORAGE"
    assert by_id["MASWE-0001"]["status"] == "new"
    # MASWE-0001 maps to both MASVS-STORAGE-2 and MASVS-PRIVACY-1 upstream; the
    # filing category (path-derived) is still MASVS-STORAGE.
    assert by_id["MASWE-0001"]["parent_masvs"] == ["MASVS-STORAGE-2", "MASVS-PRIVACY-1"]
    assert len(by_id["MASWE-0001"]["name"]) >= 3


def test_maswe_rollup_falls_back_to_id_when_weakness_unknown():
    from apd_gauntlet.synthesis.rollup import _maswe_rollup
    findings = [{"id": "conf-z9999999", "control_mappings": {"maswe": ["MASWE-9999"]}}]
    doc = _maswe_rollup(findings)
    e = doc["entries"][0]
    assert e["maswe_id"] == "MASWE-9999"
    assert e["name"] == "MASWE-9999"
    assert e["category"] is None
    assert e["status"] is None
    assert e["parent_masvs"] == []


def test_masvs_rollup_posture_transitions_and_union():
    from apd_gauntlet.synthesis.rollup import _masvs_rollup
    findings = [
        # gapped: finding only
        {"id": "conf-a1111111", "evidence": [{"artifact": "p.md", "locator": "src/A.kt:3"}],
         "control_mappings": {"masvs": ["MASVS-STORAGE-1"]}},
        # gapped_and_covered: shares MASVS-CRYPTO-1 with a capability below
        {"id": "conf-a2222222", "evidence": [{"artifact": "p.md", "locator": "src/B.kt:5"}],
         "control_mappings": {"masvs": ["MASVS-CRYPTO-1"]}},
    ]
    capabilities = [
        # covered: capability only
        {"id": "auth-cap-c1111111", "control_mappings": {"masvs": ["MASVS-AUTH-1"]}},
        # gapped_and_covered partner for MASVS-CRYPTO-1
        {"id": "crypto-cap-c2222222", "control_mappings": {"masvs": ["MASVS-CRYPTO-1"]}},
    ]
    doc = _masvs_rollup(findings, capabilities)
    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "synthesizer"
    by_id = {c["masvs_id"]: c for c in doc["controls"]}
    assert by_id["MASVS-STORAGE-1"]["posture"] == "gapped"
    assert by_id["MASVS-STORAGE-1"]["finding_ids"] == ["conf-a1111111"]
    assert by_id["MASVS-STORAGE-1"]["surfaces"] == ["src/A.kt:3"]
    assert by_id["MASVS-STORAGE-1"]["capability_count"] == 0
    assert by_id["MASVS-AUTH-1"]["posture"] == "covered"
    assert by_id["MASVS-AUTH-1"]["capability_ids"] == ["auth-cap-c1111111"]
    assert by_id["MASVS-AUTH-1"]["finding_count"] == 0
    assert by_id["MASVS-CRYPTO-1"]["posture"] == "gapped_and_covered"
    assert by_id["MASVS-CRYPTO-1"]["finding_ids"] == ["conf-a2222222"]
    assert by_id["MASVS-CRYPTO-1"]["capability_ids"] == ["crypto-cap-c2222222"]
    # name/category/category_title resolved from masvs.json catalog.
    assert by_id["MASVS-STORAGE-1"]["category"] == "MASVS-STORAGE"
    assert by_id["MASVS-STORAGE-1"]["category_title"] == "Storage"
    assert len(by_id["MASVS-STORAGE-1"]["name"]) >= 3


def test_masvs_rollup_first_appearance_then_id_ordering():
    from apd_gauntlet.synthesis.rollup import _masvs_rollup
    findings = [
        {"id": "conf-b2222222", "control_mappings": {"masvs": ["MASVS-CRYPTO-1"]}},
        {"id": "conf-a1111111", "control_mappings": {"masvs": ["MASVS-STORAGE-1"]}},
    ]
    # Capability cites an id not in any finding → appended after the finding-ordered ids.
    capabilities = [{"id": "net-cap-c1", "control_mappings": {"masvs": ["MASVS-NETWORK-1"]}}]
    doc = _masvs_rollup(findings, capabilities)
    ids = [c["masvs_id"] for c in doc["controls"]]
    # finding first-appearance: CRYPTO-1 then STORAGE-1; cap-only NETWORK-1 last.
    assert ids == ["MASVS-CRYPTO-1", "MASVS-STORAGE-1", "MASVS-NETWORK-1"]
    assert doc["controls"][2]["posture"] == "covered"


def test_build_rollups_skips_masvs_maswe_when_not_declared(tmp_path):
    from apd_gauntlet.synthesis.rollup import build_rollups
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-STORAGE-1]\n"
        "      maswe: [MASWE-0001]\n"
    )
    run_dir = _build_minimal_run(
        tmp_path, "run_id: t\ndomain: pbm\n", findings_yaml, "capability: []\n"
    )
    result = build_rollups(run_dir)
    assert result.masvs is None
    assert result.maswe is None


def test_build_rollups_emits_masvs_maswe_when_declared(tmp_path):
    from apd_gauntlet.synthesis.rollup import build_rollups
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-STORAGE-1]\n"
        "      maswe: [MASWE-0001]\n"
    )
    run_dir = _build_minimal_run(
        tmp_path,
        "run_id: t\ndomain: mobile-applications\ntaxonomies: [masvs, maswe]\n",
        findings_yaml,
        "capability: []\n",
    )
    result = build_rollups(run_dir)
    assert result.masvs is not None
    assert result.maswe is not None
    assert result.masvs["controls"][0]["masvs_id"] == "MASVS-STORAGE-1"
    assert result.maswe["entries"][0]["maswe_id"] == "MASWE-0001"


def test_masvs_maswe_coverage_written_and_schema_valid_only_when_declared(tmp_path):
    findings_yaml = (
        "finding:\n"
        "  - schema_version: 1\n"
        "    id: conf-aabbccdd\n"
        "    apd_goal: confidentiality\n"
        "    disposition: gap\n"
        "    evidence:\n"
        "      - artifact: scan.md\n"
        "        locator: 'src/Store.kt:12'\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-STORAGE-1]\n"
        "      maswe: [MASWE-0001]\n"
    )
    caps_yaml = (
        "capability:\n"
        "  - schema_version: 1\n"
        "    id: auth-cap-c1111111\n"
        "    apd_goal: authenticity\n"
        "    control_mappings:\n"
        "      masvs: [MASVS-AUTH-1]\n"
    )

    # 1) Not declared → both files absent.
    undeclared = _build_minimal_run(
        tmp_path / "u", "run_id: t\ndomain: pbm\n", findings_yaml, caps_yaml
    )
    CliRunner().invoke(main, ["rollup", str(undeclared)])
    assert not (undeclared / "40-synthesis" / "masvs-coverage.yaml").exists()
    assert not (undeclared / "40-synthesis" / "maswe-coverage.yaml").exists()

    # 2) Declared → both present and schema-valid.
    declared = _build_minimal_run(
        tmp_path / "d",
        "run_id: t\ndomain: mobile-applications\ntaxonomies: [masvs, maswe]\n",
        findings_yaml,
        caps_yaml,
    )
    result = CliRunner().invoke(main, ["rollup", str(declared)])
    assert result.exit_code == 0, result.output
    masvs_doc = yaml.safe_load((declared / "40-synthesis" / "masvs-coverage.yaml").read_text())
    assert _validate(masvs_doc, "masvs-coverage.schema.json") == []
    maswe_doc = yaml.safe_load((declared / "40-synthesis" / "maswe-coverage.yaml").read_text())
    assert _validate(maswe_doc, "maswe-coverage.schema.json") == []
    # MASVS-AUTH-1 cap-only → covered; MASVS-STORAGE-1 finding-only → gapped.
    by_id = {c["masvs_id"]: c for c in masvs_doc["controls"]}
    assert by_id["MASVS-AUTH-1"]["posture"] == "covered"
    assert by_id["MASVS-STORAGE-1"]["posture"] == "gapped"
    assert maswe_doc["entries"][0]["maswe_id"] == "MASWE-0001"


def test_existing_rollups_unchanged_when_mas_not_declared(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["rollup", str(dst)])
    assert result.exit_code == 0, result.output
    # MAS files must NOT appear for a non-mobile example run.
    assert not (dst / "40-synthesis" / "masvs-coverage.yaml").exists()
    assert not (dst / "40-synthesis" / "maswe-coverage.yaml").exists()
    # The canonical nist/attack/matrix outputs still validate.
    nist = yaml.safe_load((dst / "40-synthesis" / "nist-coverage.yaml").read_text())
    assert _validate(nist, "nist-coverage-doc.schema.json") == []
