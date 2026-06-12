# Gauntlet hardening plan — run-stopper, 3 new bugs, guardrail enforcement

Surfaced by the data-formulator multi-pack golden run (2026-06-06/07). Grounded by a
5-way code investigation. **Locked decisions:** 4 focused PRs · unresolved authored merge =
non-blocking + loud · attack-path emitter bound = worst-1-per-pair, on for all runs · CWE
check = block category/pillar (+ absent) only. Smaller defaults: finding-edge target =
realizing asset; checkpoint at `runDir/.apd-run-state.yaml`; capability merged-id
`cap-merged-<sha8>`, highest-maturity-wins.

Sequencing: **PR1 → PR2 → PR3 → PR4.** Each: TDD, full CI green
(`pytest`, `ruff check tools/ tests/`, `mypy tools/`, markdownlint, freshness, validate
example, lint-agents), example/golden regenerated where flagged.

---

## PR1 — Run-stopper robustness (no golden churn) — HIGHEST PRIORITY

Goal: a harness interruption can never silently wipe/fail a run, and there is a supported
foreground path.

Changes:
- `.claude/workflows/apd-gauntlet.js`
  - **(a) Args robustness** — top of file, before the `runDir` line: `let cfg = args; if (typeof cfg === 'string') cfg = JSON.parse(cfg)` (clear error on parse fail); presence checks naming `run_id` / `domains`; then `const args = cfg;` (alias — do NOT rename throughout, keeps existing static tests green).
  - **(b) Interruption resilience** — add `isInterrupted(r)` / `producedOutput(r)` helpers; a `checkpoint(phaseName)` that writes `runDir/.apd-run-state.yaml {last_completed_phase, drive}` after each gate; capture `currentPhase` via a thin `phase()` wrapper; before the report build/audit block, if `apply`/fallback/`rollup`/`build` produced no output → throw a **distinct** `"run interrupted at phase <X> — re-invoke in the FOREGROUND to resume (idempotency guards replay completed phases)"`; gate the existing `report completeness gate FAILED` throw behind `producedOutput(build) && producedOutput(rl)` so it only fires on genuine structural failure.
- `tools/apd_gauntlet/plan_run.py` (new) + register in `cli.py` (mirror `summarize_cmd`)
  - **(c) `apd-gauntlet plan-run <run-dir>`** — validate-run-config, then emit the ordered phase → {kind CLI|AGENT, command/agentType, output paths, validate gate} drive-checklist from a single ORDERED list matching the .js execution order, honoring `code_recon`/`threat_model`/`crown_jewels` gates. Markdown default, `--json` for tooling.
- `docs/running-the-gauntlet.md` Step 2 — make `plan-run` the first-class foreground path.
- Tests: `tests/test_workflow_apd_gauntlet.py` (static-text: args-normalize+validate present, interrupted-receipt helpers + gated completeness throw + distinct resume error, per-phase checkpoint); `tests/test_cli_plan_run.py` (CliRunner over `runs/apd-20260606-data-formulator`: gated phases present/absent, order matches; a phase-order consistency cross-check vs `meta.phases`).

Open micro-decisions (will default unless told): checkpoint file = `runDir/.apd-run-state.yaml`; plan-run emits the idempotency-guard text inline per AGENT row.

## PR2 — Guardrail enforcement (low churn)

- `tools/apd_gauntlet/canonicalize.py` — `_normalize_control_mappings(record)` pure helper: rename `mitre_atlas`→`control_mappings.atlas`; lift recognized taxonomy keys from record ROOT into `control_mappings` (create if absent); **loss-preventing** — on conflict with a non-empty existing sub-key, leave untouched so the schema gate still fires. Runs for **every** record (incl. `apath-`/`tmeval-`); extend the write-back trigger to fire when a normalization occurred. Runs before each tier validate (canonicalize already precedes the gate).
- `tools/apd_gauntlet/linters.py` + `validate.py` — **G6** new Pass-2 `check_cwe_resolves(record, catalog)`: error on category/pillar CWEs and ids absent from the bundled catalog (concrete weaknesses pass); reachable at the tier gate (not just report-audit). **G7** new Pass-3 check: finding files must live under the canonical tier dir (reject `20-findings/40-threat-model/…`-style paths).
- `tools/apd_gauntlet/report/taxonomy.py` — expose `{cwe_id: abstraction}` for the resolver.
- Confirm-only (regression tests, no behavior change): G1 title>200, G2 excerpt>25, G3 maturity-evidence (already gated); G5 colon/em-dash scalars (canonicalize `safe_dump` round-trip + skip-and-report).
- Tests: `test_canonicalize_control_mappings.py` (rename, lift, conflict-untouched, apath record fixed, idempotent), `test_canonicalize_quotes_colon_scalars.py`, `test_validate_cwe_resolves.py` (CWE-320 category → error, absent → error, CWE-79 → ok), `test_validate_finding_locations.py`.

## PR3 — Capability cross-lens merge fix (golden churn)

Root cause: `apply.py` merge branch resolves members only against `findings_by_id` ([apply.py:141](../../../tools/apd_gauntlet/synthesis/apply.py#L141)); capability clusters (`kind: capability`) never resolve → all 4 authored merges rejected; capability links get no cross-refs; metrics read 0.

- `tools/apd_gauntlet/synthesis/apply.py` — make merge/link **kind-aware**; `_merge_capabilities()` → `cap-merged-<sha8>`, `merged: true`, `lens_perspectives`, unioned maturity (highest)/scope/control_mappings, `merged_from`; source caps consumed/replaced. Apply capability link cross-refs (same as findings). **Unresolved authored merge = non-blocking + loud**: ApplyResult counter, surfaced.
- `tools/apd_gauntlet/synthesis/metrics.py` — count cross-lens capability merges/links; add `unresolved_authored_merges`/`_links` (+ metrics schema).
- `tools/apd_gauntlet/synthesis/audit.py` — audit row when authored merge-count > applied merge-count.
- `tools/apd_gauntlet/report/transform.py` — render merged-capability `lens_perspectives` (match the `cap-merged-` contract).
- `.claude/agents/apd-cluster-adjudicator.md` / `schemas/cluster-decisions.schema.json` — optionally promote `kind` to a first-class per-decision field so apply is explicitly kind-driven.
- Tests: `test_cli_apply_clusters.py` (capability merge resolves → one merged cap + lens_perspectives, 0 rejected; capability link cross-refs; unresolved merge is countable-not-silent; keep 12 finding-merge tests green), `test_metrics.py` (non-zero counts).
- **Golden churn:** regenerate example/golden deduped-capabilities + metrics + audit fixtures (review like the F1 90→93 change).

## PR4 — Attack-path correctness + emitter bound (golden churn)

WS3 finding-edge:
- `tools/apd_gauntlet/attack_path/build.py::_add_finding_edges` — deterministic role-based endpoints: attacker-position = source, evidence-named / jewel-realizing asset = target (target the realizing asset → existing #84 `data_resides_on` hop into the jewel); prose direction cue only as a tiebreaker; ties by text-offset then node_id (reproducible); never attacker→attacker.

WS4 emitter bound:
- `tools/apd_gauntlet/attack_path/findings.py` — `select_bounded(all_findings, paths, max_risk_per_pair=1)` ported from the run's proven `_select_findings.py`: keep all `gap`; worst risk path per (attacker,jewel) pair; 1 aggregate `uncertainty` disclosing suppressed count. `emit_findings(..., bound=True)` default.
- `tools/apd_gauntlet/cli.py` — `attack_path_analysis.max_risk_findings_per_pair` (default 1), bound **on for all runs**; optional fan-out density **warning** (no hard ceiling). `attack-paths.yaml` keeps ALL paths (artifact of record) — only the findings file is bounded.
- Tests: `test_attack_path_build.py` (edge orientation: source=attacker, target=asset, never attacker→attacker; #84 wiring intact), `test_attack_path_findings.py` (1 risk/pair, gaps kept, tail→single aggregate, knob), `test_cli_analyze_attack_paths.py`.
- Docs: `docs/attack-path-analysis.md`, attack-path-discipline skill.
- **Golden churn:** apath finding counts + example asset-graph regenerate.

---

## Done criteria (every PR)
`pytest` green · `ruff check tools/ tests/` · `mypy tools/` · markdownlint (docs/**, .claude/**, domains/**) · `check_report_template_freshness` (only if bundle touched — none here) · `validate examples/apd-20260601-claim-event-bus/expected/` · `lint-agents`. Example/golden regenerated + reviewed where flagged. PRs reference the run that surfaced each issue.
