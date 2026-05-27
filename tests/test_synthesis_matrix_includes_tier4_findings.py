"""C-20: synthesizer 9xN coverage matrix includes tier-4 finding sources.

The synthesizer aggregates findings via ``validate._iter_records``. For the
9xN APD coverage matrix to include both ``tmeval-*`` (threat-model-evaluator)
and ``apath-*`` (attack-path-analyzer) findings, ``_iter_records`` must pick
up findings from:

1. Specialist files under ``10-trustworthiness/`` / ``20-scalability/`` /
   ``30-auditability/``.
2. The threat-model evaluator's ``40-threat-model/threat-model.findings.yaml``.
3. The attack-path analyzer's ``40-synthesis/attack-path.findings.yaml``.

This test file constructs a synthetic run directory with all three sources
present and asserts every record is aggregated. It also asserts the
synthesizer agent's prompt documents the tier-4 input paths, so the
documentation contract is in sync with the implementation contract.
"""
from __future__ import annotations

import pathlib
from textwrap import dedent

from apd_gauntlet import validate as v

AGENT = (
    pathlib.Path(__file__).resolve().parent.parent
    / ".claude" / "agents" / "apd-synthesizer.md"
)


def _write_specialist_finding(run: pathlib.Path) -> None:
    """Write a single conf-* finding under 10-trustworthiness/."""
    tier = run / "10-trustworthiness"
    tier.mkdir(parents=True, exist_ok=True)
    (tier / "confidentiality.findings.yaml").write_text(dedent("""\
        finding:
          - schema_version: 1
            id: conf-11111111
            agent: confidentiality
            apd_tier: trustworthiness
            apd_goal: confidentiality
            disposition: gap
            severity: high
            confidence: high
            title: "PHI in plaintext on adjudication link"
            summary: "PHI traverses the link unencrypted."
            detail: "Detailed exposition of the gap."
            evidence:
              - artifact: tech_plan.md
                locator: "section 4.2"
                excerpt: "PHI written in plaintext"
            control_mappings:
              nist_800_53r5: ["SC-8(1)"]
            recommendation:
              posture: required
              summary: "Apply envelope encryption."
              detail: "Encrypt PHI fields in the producer SDK."
    """))


def _write_tmeval_finding(run: pathlib.Path) -> None:
    """Write a tmeval-* finding under 40-threat-model/."""
    tier = run / "40-threat-model"
    tier.mkdir(parents=True, exist_ok=True)
    (tier / "threat-model.findings.yaml").write_text(dedent("""\
        finding:
          - schema_version: 1
            id: tmeval-22222222
            agent: threat_model_evaluator
            apd_tier: auditability
            apd_goal: non_repudiation
            disposition: gap
            severity: medium
            confidence: high
            title: "Threat model omits Repudiation for audit-log-writer"
            summary: "STRIDE Repudiation entry absent for audit-log-writer."
            detail: "Full STRIDE analysis is required for the audit surface."
            evidence:
              - artifact: "00-context/threat-model-normalized.yaml"
                locator: "entries[asset=audit-log-writer]"
                excerpt: "5 entries: S, T, I, D, E; no R entry"
            control_mappings:
              nist_800_53r5: ["AU-10"]
            recommendation:
              posture: recommended
              summary: "Add Repudiation entry for audit-log-writer."
              detail: "Cover non-repudiation explicitly in the threat model."
    """))


def _write_apath_finding(run: pathlib.Path) -> None:
    """Write an apath-* finding under 40-synthesis/attack-path.findings.yaml.

    Uses the post-C-20 filename (``attack-path.findings.yaml`` with the dot
    separator) and the ``finding:`` root key convention that the validator's
    ``RECORD_KINDS`` glob expects.
    """
    tier = run / "40-synthesis"
    tier.mkdir(parents=True, exist_ok=True)
    (tier / "attack-path.findings.yaml").write_text(dedent("""\
        finding:
          - schema_version: 1
            id: apath-33333333
            agent: attack_path_analyzer
            apd_tier: trustworthiness
            apd_goal: confidentiality
            disposition: risk
            severity: high
            confidence: high
            title: "Bottleneck edge from external_user to phi_store"
            summary: "Six enumerated paths converge on a single bottleneck edge."
            detail: "Bottleneck analysis identifies a high-leverage chokepoint."
            evidence:
              - artifact: "40-synthesis/attack-paths.yaml"
                locator: "paths[0..5].edges[2]"
                excerpt: "edge=adjudication->phi_store appears in 6 paths"
            control_mappings:
              nist_800_53r5: ["SC-7"]
            recommendation:
              posture: required
              summary: "Harden the adjudication-to-phi_store edge."
              detail: "Apply egress filtering and authenticated channel."
    """))


# ---------------------------------------------------------------------------
# Aggregation behavior — _iter_records picks up all three sources
# ---------------------------------------------------------------------------


def test_iter_records_aggregates_specialist_findings(tmp_path: pathlib.Path) -> None:
    """Baseline: specialist findings under 10-trustworthiness/ are aggregated."""
    run = tmp_path / "run"
    _write_specialist_finding(run)
    ids = [rec.get("id") for _path, _kind, rec in v._iter_records(run)]
    assert "conf-11111111" in ids


def test_iter_records_aggregates_tmeval_findings(tmp_path: pathlib.Path) -> None:
    """Tier-4 threat-model-evaluator findings under
    ``40-threat-model/threat-model.findings.yaml`` are aggregated by the same
    ``*.findings.yaml`` rglob the synthesizer uses for specialist files.
    """
    run = tmp_path / "run"
    _write_tmeval_finding(run)
    ids = [rec.get("id") for _path, _kind, rec in v._iter_records(run)]
    assert "tmeval-22222222" in ids


def test_iter_records_aggregates_apath_findings(tmp_path: pathlib.Path) -> None:
    """Tier-4 attack-path-analyzer findings under
    ``40-synthesis/attack-path.findings.yaml`` (post-C-20 filename) are
    aggregated. The pre-C-20 filename ``attack-path-findings.yaml`` did not
    end in ``.findings.yaml`` so the rglob silently skipped it; the rename
    closes that gap.
    """
    run = tmp_path / "run"
    _write_apath_finding(run)
    ids = [rec.get("id") for _path, _kind, rec in v._iter_records(run)]
    assert "apath-33333333" in ids


def test_iter_records_aggregates_all_three_sources(tmp_path: pathlib.Path) -> None:
    """End-to-end: a run directory containing specialist + tmeval + apath
    findings yields every record from a single ``_iter_records`` call.

    This is the core C-20 contract: the synthesizer's APD 9xN coverage
    matrix step iterates over the union of these sources.
    """
    run = tmp_path / "run"
    _write_specialist_finding(run)
    _write_tmeval_finding(run)
    _write_apath_finding(run)
    ids = sorted(
        rec.get("id") for _path, _kind, rec in v._iter_records(run)
        if rec.get("id")
    )
    assert ids == ["apath-33333333", "conf-11111111", "tmeval-22222222"]


# ---------------------------------------------------------------------------
# Documentation contract — synthesizer agent prompt mentions tier-4 sources
# ---------------------------------------------------------------------------


def test_synthesizer_agent_documents_tmeval_input_path() -> None:
    """The synthesizer agent's Inputs section must mention the tier-4
    threat-model-evaluator finding path so reviewers reading the agent
    description know the matrix includes tmeval-* findings when present.
    """
    text = AGENT.read_text()
    assert "40-threat-model/" in text or "threat-model.findings.yaml" in text


def test_synthesizer_agent_documents_apath_input_path() -> None:
    """The synthesizer agent's Inputs section must mention the post-C-20
    attack-path findings filename ``attack-path.findings.yaml`` (with the dot
    separator) so the documented input set matches what ``_iter_records``
    actually picks up.
    """
    text = AGENT.read_text()
    assert "attack-path.findings.yaml" in text


def test_synthesizer_agent_matrix_step_acknowledges_tier4() -> None:
    """The APD coverage matrix step (Step 8) must explicitly note that
    tier-4 findings (``tmeval-*`` and ``apath-*``) participate in the
    9xN rollup when present, so the documented behavior matches the
    aggregation behavior under C-20.
    """
    text = AGENT.read_text()
    assert "tmeval" in text and "apath" in text
