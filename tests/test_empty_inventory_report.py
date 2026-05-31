"""Gap-2 regression: an empty (schema-valid) asset-inventory + a run with NO crown
jewels still builds the coverage rollups AND the HTML report. The report hard-requires
00-context/asset-inventory.yaml, and intake now always emits it (empty when there is
nothing to inventory), so build-report's required-input contract is always satisfiable.
"""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.report.build import build_report
from apd_gauntlet.synthesis.rollup import build_rollups

EMPTY_INVENTORY = {
    "schema_version": 1,
    "generated_by": "intake",
    "assets": [],
    "identities": [],
    "trust_boundaries": [],
}

# No crown_jewels, no attacker_positions, no taxonomies — the minimal multi-domain run.
RUN_CFG = "run_id: empty-inv-run\ndomains:\n  - pbm\nframework_version: '1.4.0'\n"

FINDINGS = """\
schema_version: 1
finding:
  - schema_version: 1
    id: conf-deadbeef
    agent: confidentiality
    apd_tier: trustworthiness
    apd_goal: confidentiality
    disposition: gap
    severity: high
    confidence: high
    title: "Example store: plaintext at rest"
    summary: "Plaintext at rest in the example store."
    detail: "The example store holds data unencrypted at rest."
    evidence:
      - artifact: tech_plan.md
        locator: "§1 ¶1"
        excerpt: "stored as plaintext at rest"
    control_mappings:
      nist_800_53r5: [SC-28]
    recommendation:
      posture: required
      summary: "Encrypt the example store at rest."
      detail: "Apply envelope encryption to the example store."
"""

CAPS = "schema_version: 1\ncapability: []\n"


def _minimal_run(tmp_path: pathlib.Path) -> pathlib.Path:
    run = tmp_path / "run"
    (run / "00-context").mkdir(parents=True)
    (run / "40-synthesis").mkdir(parents=True)
    (run / ".apd-run.yaml").write_text(RUN_CFG, encoding="utf-8")
    (run / "00-context" / "asset-inventory.yaml").write_text(
        yaml.safe_dump(EMPTY_INVENTORY, sort_keys=False), encoding="utf-8"
    )
    (run / "40-synthesis" / "deduped-findings.yaml").write_text(FINDINGS, encoding="utf-8")
    (run / "40-synthesis" / "deduped-capabilities.yaml").write_text(CAPS, encoding="utf-8")
    return run


def test_empty_inventory_no_crown_jewels_builds_rollups_and_report(tmp_path):
    run = _minimal_run(tmp_path)

    # 1) rollup tolerates an empty inventory and produces the report's required inputs.
    build_rollups(run)
    for name in ("nist-coverage.yaml", "attack-exposure.yaml", "apd-coverage-matrix.yaml"):
        assert (run / "40-synthesis" / name).is_file(), f"rollup did not write {name}"

    # 2) build-report succeeds: the required asset-inventory input is present (empty),
    #    no section crashes on the empty inventory, and the finding is rendered.
    target, data = build_report(run, quiet=True)
    assert (target / "data.js").is_file()
    assert (target / "index.html").is_file()
    assert data["meta"]["section_errors"] == {}, data["meta"]["section_errors"]
    assert data["findings"], "the deduped finding should appear in the report"
