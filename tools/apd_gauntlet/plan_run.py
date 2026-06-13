"""plan-run — emit the deterministic foreground drive-checklist for a run.

The background Workflow primitive (.claude/workflows/apd-gauntlet.js) drives the
gauntlet by DISPATCHING subagents, but running it headlessly can interrupt those
dispatches and wipe a run. `plan-run` gives operators a first-class FOREGROUND
alternative: it reads runs/<id>/.apd-run.yaml and emits the EXACT ordered
phase->step list the runner executes, honoring the run-config gates, so an
operator can drive each step in-session (AGENT rows = foreground Agent
dispatches; CLI rows = Bash).

The ordered phase model below MUST stay aligned with the runner's execution
order in apd-gauntlet.js (see tests/test_cli_plan_run.py: the consistency test
parses meta.phases and asserts the two cannot silently drift).
"""
from __future__ import annotations

from typing import Any

# Per-tier lens dispatch order, matching runTier() calls in the workflow JS.
# (tier_dir, lenses). plan-run uses the concrete tier-dir as the phase name (the
# runner's abstract tier-1/2/3 phase() breadcrumbs alias to these dirs, which are
# what the tier validate gate actually targets).
_TIERS: list[tuple[str, list[str]]] = [
    ("10-trustworthiness", ["confidentiality", "integrity", "availability"]),
    ("20-scalability", ["distributed", "resilient", "ephemeral"]),
    ("30-auditability", ["authenticity", "non-repudiation", "immutability"]),
]


def _step(phase: str, kind: str, ref: str, outputs: str, gate: str = "") -> dict[str, str]:
    """Build one step record. Every step carries all five documented keys."""
    return {"phase": phase, "kind": kind, "ref": ref, "outputs": outputs, "gate": gate}


def build_plan(cfg: dict[str, Any]) -> list[dict[str, str]]:
    """Return the ordered list of step dicts the runner would execute for ``cfg``.

    Gates honored (mirroring apd-gauntlet.js):
      - code-recon: present unless cfg["code_recon"] == "disabled".
      - tm-recon: only when cfg["threat_model"] is truthy.
      - apath: only when cfg["crown_jewels"] is a non-empty list.
      - tmeval: ALWAYS (the always-on authored baseline TM always exists).
    """
    run_dir = "runs/" + str(cfg.get("run_id", "<run-id>"))
    domains = " ".join(cfg.get("domains") or [])
    plan: list[dict[str, str]] = []

    # 1 — setup
    plan.append(
        _step("setup", "CLI", f"build-domain-skill {domains}".rstrip(),
              ".claude/skills/apd-domain/SKILL.md + by-goal/<goal>.md (9 lens sidecars)")
    )
    plan.append(
        _step("setup", "CLI", f"validate-domain {domains}".rstrip(),
              f"domain pack {domains} (read-only check)")
    )

    # 2 — intake
    plan.append(
        _step("intake", "AGENT", "apd-intake",
              "00-context/context-brief.md, 00-context/asset-inventory.yaml")
    )
    # 2b — FW-2: schema-gate 00-context right after intake so an invalid
    # asset-inventory (e.g. a data_classifications value outside the enum) is
    # caught here, not 9 specialists later at the pre-synthesis whole-run gate.
    plan.append(
        _step("intake", "CLI", f"validate {run_dir} --schema-only --errors-only",
              "00-context schema gate (asset-inventory + brief frontmatter)",
              gate=f"validate {run_dir} --schema-only --errors-only")
    )

    # 3 — code-recon (present unless disabled; default "auto" => present)
    if str(cfg.get("code_recon") or "auto") != "disabled":
        plan.append(
            _step("code-recon", "AGENT", "apd-code-recon",
                  "00-context/code-evidence-index.yaml "
                  "(multi-repo: per-repo passes + cross-repo edges when repos[] declared)")
        )

    # 4 — threat-model-author (always-on)
    plan.append(
        _step("threat-model-author", "CLI", f"author-threat-model {run_dir}",
              "00-context/threat-model-skeleton.yaml")
    )
    plan.append(
        _step("threat-model-author", "AGENT", "apd-threat-model-author",
              "00-context/threat-model-normalized.yaml, threat-model-authored.md")
    )

    # 5 — tm-recon (only if a TM was supplied)
    if cfg.get("threat_model"):
        plan.append(
            _step("tm-recon", "AGENT", "apd-threat-model-recon",
                  "00-context/threat-model-supplied-normalized.yaml")
        )

    # 6/7/8 — the three parallel lens tiers, each canonicalize + tier gate.
    for tier_dir, lenses in _TIERS:
        for lens in lenses:
            plan.append(
                _step(tier_dir, "AGENT", f"apd-{lens}",
                      f"{tier_dir}/{lens}.findings.yaml, {tier_dir}/{lens}.capabilities.yaml")
            )
        plan.append(
            _step(tier_dir, "CLI", f"canonicalize {run_dir}",
                  f"canonicalized lens records under {run_dir}")
        )
        plan.append(
            _step(tier_dir, "CLI", f"validate {run_dir} --tier {tier_dir} --errors-only",
                  f"tier {tier_dir} records (read-only gate)",
                  gate=f"validate {run_dir} --tier {tier_dir} --errors-only")
        )

    # 9 — full pre-Phase-5 cross-file gate
    plan.append(
        _step("tier-3", "CLI", f"validate {run_dir} --errors-only",
              "whole-run cross-file clean (read-only gate)",
              gate=f"validate {run_dir} --errors-only")
    )

    # 10/11/12 — decomposed synthesis
    plan.append(
        _step("synthesis-cluster", "CLI", f"cluster-candidates {run_dir}",
              "40-synthesis/cluster-candidates.yaml")
    )
    plan.append(
        _step("synthesis-adjudicate", "AGENT", "apd-cluster-adjudicator",
              "40-synthesis/cluster-decisions.yaml")
    )
    plan.append(
        _step("synthesis-apply", "CLI", f"apply-clusters {run_dir}",
              "40-synthesis/deduped-findings.yaml, deduped-capabilities.yaml, "
              "rejected-records.yaml, severity-disagreements.yaml, contradictions.yaml")
    )

    # 13 — tmeval (ALWAYS)
    plan.append(
        _step("tmeval", "AGENT", "apd-threat-model-evaluator",
              "40-threat-model/threat-model.findings.yaml, "
              "40-synthesis/threat-model-coverage.yaml, threat-model-coverage-report.md")
    )

    # 14 — apath (only if crown_jewels is a non-empty list)
    crown = cfg.get("crown_jewels")
    if isinstance(crown, list) and crown:
        plan.append(
            _step("apath", "AGENT", "apd-attack-path-analyzer",
                  "40-synthesis/asset-graph.yaml, attack-paths.yaml, defense-graph.yaml, "
                  "attack-path.findings.yaml, attack-path-report.md")
        )

    # 15 — rollup (runs after tmeval/apath so coverage unions the tier-4 findings)
    plan.append(
        _step("synthesis-rollup", "CLI", f"rollup {run_dir}",
              "40-synthesis/nist-coverage.yaml, attack-exposure.yaml, "
              "apd-coverage-matrix.yaml, metrics.yaml")
    )

    # 16 — report-writer
    plan.append(
        _step("synthesis-report", "AGENT", "apd-report-writer",
              "40-synthesis/report-data.yaml, advisory-report.md")
    )

    # 17 — build-report
    plan.append(
        _step("synthesis-build", "CLI", f"build-report {run_dir}",
              "40-synthesis/report-html/data.js, build-manifest.txt")
    )

    # 18 — audit (CLI structural gate + AGENT semantic gate, non-blocking)
    plan.append(
        _step("synthesis-audit", "CLI", f"audit-report {run_dir}",
              "40-synthesis/report-audit.yaml",
              gate=f"audit-report {run_dir} (structural completeness must pass)")
    )
    plan.append(
        _step("synthesis-audit", "AGENT", "apd-report-auditor",
              "semantic critique (GATE: pass/fail; semantic residual non-blocking)")
    )

    # 19/20 — domain improvement capture (advisory)
    plan.append(
        _step("domain-coverage-delta", "CLI", f"domain-coverage-delta {run_dir}",
              "40-synthesis/domain-coverage-delta.yaml")
    )
    plan.append(
        _step("domain-improvements", "AGENT", "apd-domain-auditor",
              "40-synthesis/domain-improvements.yaml")
    )

    # 21 — closeout
    plan.append(
        _step("closeout", "CLI", f"summarize {run_dir}",
              f"{run_dir} run summary (read-only)")
    )

    return plan


def render_markdown(plan: list[dict[str, str]], cfg: dict[str, Any]) -> str:
    """Render the plan as a numbered, phase-grouped foreground drive checklist."""
    run_id = str(cfg.get("run_id", "<run-id>"))
    domains = ", ".join(cfg.get("domains") or []) or "(none)"
    lines: list[str] = []
    lines.append(f"# APD gauntlet foreground drive plan — {run_id}")
    lines.append("")
    lines.append(
        f"Run `{run_id}` — domains: {domains}. foreground drive order "
        "(run each step in-session; AGENT rows = foreground Agent dispatches, "
        "CLI rows = Bash)."
    )
    lines.append("")

    last_phase: str | None = None
    for step in plan:
        if step["phase"] != last_phase:
            lines.append(f"## {step['phase']}")
            last_phase = step["phase"]
        lines.append(
            f"- [ ] **{step['phase']}** — {step['kind']}: "
            f"`{step['ref']}` -> {step['outputs']}"
        )
        if step["gate"]:
            lines.append(f"  - gate: `{step['gate']}`")

    # apath gate note: if no apath step was emitted, tell the operator when it runs.
    if not any(s["ref"] == "apd-attack-path-analyzer" for s in plan):
        lines.append("")
        lines.append(
            "> Note: the attack-path analysis phase is omitted for this run — it "
            "runs when the run-config or the domain pack declares a non-empty "
            "crown_jewels list."
        )

    lines.append("")
    return "\n".join(lines)
