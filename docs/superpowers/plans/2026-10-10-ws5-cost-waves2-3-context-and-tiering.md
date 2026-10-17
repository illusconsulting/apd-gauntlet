# WS5 — Cost Waves 2–3: Context, Determinism and Model Tiering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut per-run tokens by having Python prepare exactly what each agent judges and render what nobody needs to judge (audit Wave 2), then move most agents off Opus one tier at a time behind measured gates (audit Wave 3).

**Architecture:** Six new CLI commands (`xref-digest`, `report-digest`, `render`, `edge-review`, `tm-candidates`, `build-lens-skills`) write small deterministic files that replace whole-corpus reads and LLM-written markdown. The domain skill builder routes calibration files through a declarative `consumers:` map and emits an attack-path-defaults sidecar. Code recon fans out into shards that Python merges inside `canonicalize`. Every new step lands in the workflow, `plan-run` and the Agent SDK runner together. Wave 3 then edits only agent frontmatter, one tier per task, with a revert rule.

**Tech Stack:** Python 3.10+ (`tools/apd_gauntlet`), click, PyYAML, jsonschema (Draft 2020-12), the Claude Code workflow (`.claude/workflows/apd-gauntlet.js`), the Agent SDK runner (`tools/apd_gauntlet/runner/flow.py`, LA2), pytest, markdownlint-cli2.

**Spec:**

- Cost and token audit (Claude Doc "APD Gauntlet cost and token audit", 2026-10-10): "Wave 2: context and determinism" table and the consumer-map paragraph; "Wave 3: model and effort tiering" table and the orchestrator line; "Protecting accuracy" rollout order.
- `docs/superpowers/plans/2026-10-10-program-master-plan.md`: Registry §R1 (`xref-digest`, `report-digest`, `edge-review`, `tm-candidates`, `render`, `build-lens-skills`), §R5, §R7 (`domain` gains `consumers`), Tasks 6 (Wave 2, M4) and 8 Step 3 (Wave 3, M6).
- LA2 runner plan (`2026-10-10-local-apps-plan2-agent-sdk-runner.md`, amended by A2): `runner/flow.py` step tables, `runner/instructions.py`, `tests/runner/*`.

**Amended 2026-10-17** per the amendments register (A10.1, A10.2, A10.3, A10.4, A10.5, A10.6, A10.7, A10.8, A10.9, A10.10, A10.11, A10.12, A10.13, A15.12, A15.16, A15.21, A15.25, A15.28, A15.30) and consolidated plan Part G (N14 and N15 as Tasks 0a–0b, N10–N13 as Tasks 15a–15d, N16 as Tasks 24–28, N21 in Tasks 13–14).

## Global Constraints

- Line: `next`. One PR per task. Every PR that edits `.claude/workflows/apd-gauntlet.js` or `tools/apd_gauntlet/runner/flow.py` merges alone (master plan "Parallel-safe pairs"); Tasks 1–8 are the "data-only items" that may run beside IAC1 in a separate worktree.
- Rollout order (audit, verbatim): "the seven defects; Wave 1; Wave 2 one item at a time, digests and renders first; Wave 3 one tier of lenses at a time, report writer last." Tasks 0a–14 run in M4; Tasks 15–28 run in M6 after IAC4 and calibration (master plan Task 8 Steps 1–2).
- Gates (master plan, verbatim): no critical or high finding lost unless the loss traces to evidence; severity agrees on at least 90% of matched findings; blocked rate moves by no more than 5 points; first-pass schema validity and retry count no worse than baseline; report audit passes in no more iterations than baseline.
- Run each configuration twice. If gates flap, raise to three runs and gate on the median (master plan Risks). Wave 3 runs each configuration three times and gates on the median (register A10.1).
- **Operator gate (OG, used by every behaviour-changing task).** On the task's commit, run the master plan Task 1 set (the three committed examples plus one private PBM run) twice with telemetry on, into `runs/<id>-ws5-<tag>-r1` and `-r2`. For each run id run `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-<tag> --gates eval/gates.yaml --strict` (WS2 `resolve_side` expands each side to its `-r1`/`-r2` runs; four comparisons), where `<prev>` is the last accepted WS5 tag (for the first gated task, Task 0a, the `v2.0.0a2` runs or `-next-baseline`), and, per run, `apd-gauntlet usage runs/<id>-ws5-<tag>-r<k> --otel <telemetry-file>`. Only the milestone exits (after Task 14, after the last Wave 3 task) compare against `runs/<id>-baseline` without `--strict`; `runs/<id>-baseline` is the 1.7.1 set from master plan Task 1 (A15.13). Pass: all four exit 0. Exit 2 means a missing baseline: capture it (master plan Task 1) and never compare against nothing. Preconditions (register A10.1): `<prev>` and the candidate use the same Claude Code version, provider and session model, with `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` and `CLAUDE_CODE_EFFORT_LEVEL` unset. A run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or in a new session: `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started (register A15.12).
- Ids are minted by Python only (ADR-0020); agents emit content.
- CI never touches the network (ADR-0017); real runs are never committed.
- Quality gates: `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest`, and `markdownlint-cli2` on the linted globs all pass on every PR.
- Three channels, one commit: every new CLI step appears in `.claude/workflows/apd-gauntlet.js`, `tools/apd_gauntlet/plan_run.py` and `tools/apd_gauntlet/runner/flow.py` with identical labels, plus `tests/runner/test_flow_parity.py::test_labels_exist_in_workflow`. WS5 adds no phase, so `meta.phases == runner.flow.PHASES` and `tests/test_cli_plan_run.py::test_plan_run_phase_names_consistent_with_workflow` stay green unchanged.
- Workflow ordering tests use WS3's dispatch-trace harness (`tests/test_workflow_dispatch_trace.py`: `trace(cfg, fail=None)` returns `{agentType, label, phase, guard, command}` per dispatch; `HA_SHAPED = {"run_id": "r", "domains": ["pbm"], "code_recon": "enabled", "crown_jewels": ["phi_store"]}`). Every task that adds a CLI dispatch inserts its label into that file's `CLI_LABELS` at its trace position, in the same commit.
- Resume table: when a task moves an output from an agent to Python, the agent's row in WS1's `tools/apd_gauntlet/resume_plan.py` `RESUMABLE_STEPS` drops that output (and `tests/test_cli_resume_plan.py` follows), so a crash between the agent and the render never re-dispatches the agent. Always-run CLI steps need no row.
- Instruction mirroring: an `llmStep`/`agent()` instruction changed in the workflow is changed identically in `tools/apd_gauntlet/runner/instructions.py` (`INSTRUCTIONS`, LA2 Task 5).
- Bundle sync: after any edit under `.claude/agents/`, `.claude/skills/` (outside `apd-domain/`) or `templates/`, run `python -I -m apd_gauntlet.bundle --sync` and commit the copies under `tools/apd_gauntlet/data/claude/` and `tools/apd_gauntlet/data/templates/` in the same commit (LA2 `tests/test_bundle.py::test_bundle_matches_repo`).
- Lens packets (Task 11 on, register A10.3): any later edit to the four shared skills or to a pack reruns `apd-gauntlet build-lens-skills examples/apd-20260601-claim-event-bus` and commits `.claude/skills/apd-domain/lens/*.md`; otherwise `tests/test_lens_skills.py::test_committed_packets_match_rebuild` fails.
- Determinism: digests, renders, packets and merges carry no timestamps or set-iteration order; a rerun on the same inputs is byte-identical. YAML is written with `yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096)`.
- No silent caps: every digest, packet and merge lists what it skipped or omitted, with a reason.
- Consumer map (audit, verbatim): "a `consumers:` list per calibration file in `domain.yaml`, defaulting to all nine lenses, so a pack author can widen it without code changes."
- Wave 3 table (audit): lenses Sonnet/medium; intake Sonnet/medium; code recon Sonnet/medium; TM author Sonnet/medium; TM recon Sonnet/low; TM evaluator Sonnet/high; attack-path analyzer Sonnet/medium; cluster adjudicator Opus/high; report writer Sonnet/medium; report auditor Opus/high; domain auditor Sonnet/medium; synthesizer (fallback) Opus/high; CLI runner Haiku/low. "Remove the deprecated `apd-orchestrator` rather than tiering it."
- Wave 3 revert rule (DEC-22, register A10.8): when a tier's OG fails on either repetition, first retry its OG one effort step up (`medium` → `high`, `high` → `xhigh`). If it still fails, set explicit `model: opus` with the WS3 effort on that tier's agents (never restore an absent `model`: Task 23 makes `model` required), set the task's rows in `tests/test_agent_effort.py` `EXPECTED` (and any lint test the task renamed) to those values, sync the bundle, and commit `revert(agents): keep <tier> on <model>` naming the failing gate and run ids. The next tier proceeds. `EXPECTED` always pins what ships.
- Per-tier revert criteria (Tasks 16–23, register A10.11): the base criterion is any `compare-runs` exit 1 on either repetition for any of the four runs, against `<prev>`, with `--strict`, after the effort ladder above. Each task's Step 6 adds its extra criteria.
- Measured numbers in this plan come from `examples/apd-20260612-home-assistant` at `856ea96`. If WS1 or WS3 Task 8 regenerated that example, re-measure with the task's own test and update the literals in the same commit.
- Line numbers are hints: citations updated by register A10.13 are positions after WS1 (the workflow's, from A15.28, after #50); every other citation is at `856ea96`. Locate every edit by anchor (function, label or heading).
- Docs live with behaviour: `CHANGELOG.md` `## Unreleased — 2.0 line`, the CLI list in `docs/running-the-gauntlet.md` (lines 42–71), the "Other derived fields" table in `docs/deterministic-field-register.md`, and `docs/schema-evolution.md` for every schema added or changed.
- Assumed state at execution (from the WS1, WS2, WS3 and LA plans):
  - WS1 adds `resume-plan` (`resume_plan.py`, `RESUMABLE_STEPS`), the tier-gate repair branch, and `canonicalize._mint_code_evidence_ids` / `_mint_threat_model_ids` (fill absent `cev-`/`tm-` ids only, never rewrite one), run by the workflow steps `canonicalize-code-evidence` (inside the code-recon branch, after the halt check) and `canonicalize-threat-model` (after the tm-recon `if/else`, before `runTier`). It points the TM evaluator at `40-synthesis/deduped-*.yaml` and `40-threat-model/threat-model.findings.yaml`, deletes the analyzer's obsolete Steps 5–6 hedges, and adds a pack-content hash to the domain-skill signature.
  - WS3 adds `apd-cli-runner`, the composites with labels `prepare-run`, `tier-gate-<tierDir>`, `post-tier4`, `post-tier4-retry-1` and `closeout`, `effort` on every agent at the audit's Wave 3 values (pinned by `tests/test_agent_effort.py` `EXPECTED`, models unchanged), one-line agent descriptions, the `domain_improvement_capture` key, and deletes `apd-orchestrator` (its Task 5).
  - WS2 adds `compare-runs` (sides resolve to `-r1`/`-r2`), `usage` and `eval/gates.yaml`. WS2 creates `tests/conftest.py`; LA1 adds to it. LA2 creates `runner/flow.py`, `runner/instructions.py`, `bundle.py` and `tests/runner/` (`scenario()`, `FakeCli`, `FakeExecutor`).
- Workflow snippets below use today's `pyStep` options (`phase`, `label`, `cliArgs`, `outputs`, `alwaysRun`). Keep whichever marker WS1 left for "rerun on resume" where this plan writes `alwaysRun: true`.
- Workflow edits after #50 (register A15.21): the runner awaits every dispatch, and `tests/test_workflow_runner_awaits.py` fails on any un-awaited one. Quoted call sites and inserted dispatches use the awaited form (`await pyStep(…)`, `const x = await pyStep(…)`, `await llmStep(…)`, `await parallel(…)`); inside a `parallel` thunk a dispatch stays `return <dispatch>(…)`. A new helper that consumes a dispatch result is a named `async function`, listed in that file's `ASYNC_HELPERS` and `CALLS` (an `async` thunk or a `.map(async …)` callback fails `test_no_other_function_is_async`); a plain helper that only returns a dispatch joins `PASS_THROUGH` and `CALLS`; `pyStep`, `llmStep` and `guard` never await. A task that adds, removes or renames a dispatch label of the harness's green run, or changes a parallel group, updates `EXPECTED_GREEN_LABELS`, `LENS_GROUPS`, `LARGEST_PARALLEL_GROUP` and the label slices of the node tests in the same commit. The harness `ARGS` set no supplied threat model, crown jewels, decision model, catalog or infrastructure, so steps behind those switches stay out of the green list.

## Review Focus

- **A third-party pack with no `consumers:` key.** Every lens must still receive every calibration file. Pinned by Task 9 `test_pack_without_consumers_keeps_every_calibration_file`.
- **An upgraded install whose generated `apd-domain` skill already matches the pack signature.** The builder must rebuild, or lenses keep reading unpruned sidecars and packets are built from stale ones. Pinned by Task 9 `test_builder_format_change_forces_rebuild`.
- **An earlier-tier lens file that is unparseable or has a record without an id when `xref-digest` runs.** It must be listed in `skipped_files` and warned, never dropped silently. Pinned by Task 1 `test_xref_digest_lists_unparseable_file`.
- **Multi-repo code recon where the cross-repo shard repeats a symbol, or a shard wrote nothing.** One merged entry with unioned `apd_relevance`; the missing shard's projects are recorded `not_analyzed`, never shown as clean. Pinned by Task 13 `test_merge_collapses_duplicate_and_unions_relevance` and `test_missing_shard_projects_are_not_analyzed`.
- **A run whose attack-path build blocked, or that declares no crown jewels.** `render --artifact attack-path-report` writes a short blocked report or exits 0 with "skipped", and `edge-review` writes an empty review, instead of crashing the apath branch. Pinned by Task 4 `test_render_attack_path_report_blocked_run` and Task 7 `test_edge_review_blocked_run`.

---

## Measured sizes (HA example)

| Audit row | Audit claim | Measured here | Pinned by |
|---|---|---|---|
| Cross-tier digest | 129 KB → 8 KB; 256 KB → 16 KB (−94%) | 128,812 B → 8,325 B (34 records); 255,786 B → 16,518 B (67 records); −94% both | Task 1 |
| Report-writer digest | 211 KB → 26.5 KB (−88%) | deduped only: 210,978 B → 26,201 B (−87.6%); with 18 apath findings and 28 capabilities: 309,126 B → 38,746 B (−87.5%) | Task 2 |
| Renders | 117 KB, 19.5 KB, 14.7 KB, 31 KB of LLM markdown | 117,197 B, 19,482 B, 14,689 B, 30,904 B (now zero LLM output) | Tasks 3–6 |
| Edge review | 714 KB, 3,298 edges → 37 edges (10 KB) | 713,922 B → 27,687 B (37 edges: 27 finding, 10 capability; titles and all excerpts included; the bare edge records are 10,133 B) | Task 7 |
| TM pre-pass | 151 + 211 + 69 KB read | 430,649 B → 53,562 B (94 pairs with anchors over 75 entries and 21 findings, plus 47 surfaces; −88%); recovers HA's one contradiction pair | Task 8 |
| Prune sidecars | −45% (pbm), −36% (api-security + mobile), −43% (identity + security-tooling) | Nine sidecars: pbm 911.2 KB → 408.6 KB (−55%); api-security + mobile 885.9 → 558.4 KB (−37%); identity + security-tooling 1,001.2 → 564.5 KB (−44%); pbm + api-security 1,230.6 → 597.1 KB (−51%) | Task 9 |
| Attack-path defaults sidecar | 15–25 KB vs 156 KB / 290 KB | pbm 14.6 KB vs 156.5 KB; api-security + mobile 19.3 KB vs 290.1 KB; identity + security-tooling 25.3 KB vs 220.1 KB | Task 10 |
| Lens packets | 65 KB, 14–20 KB smaller | 64,751 B of four skills; per lens 14.0–15.2 KB smaller with all nine taxonomies declared, 15.7–17.0 KB with HA's seven, 23.3–24.5 KB with none (the finding schema is kept whole) | Task 11 |

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/digests.py` | `xref-digest` and `report-digest` builders | Create (T1, T2) |
| `tools/apd_gauntlet/render/__init__.py` | Artifact registry, `render_artifact`, `md_cell` | Create (T3) |
| `tools/apd_gauntlet/render/tm_authored.py` | `threat-model-authored.md` renderer | Create (T3) |
| `tools/apd_gauntlet/threat_model/delta.py` | Supplied-vs-authored diff shared by T3 and T8 | Create (T3) |
| `tools/apd_gauntlet/attack_path/load.py` | Rebuild `Graph` and paths from the YAML artifacts | Create (T4) |
| `tools/apd_gauntlet/render/attack_path_report.py` | `attack-path-report.md` renderer | Create (T4) |
| `tools/apd_gauntlet/render/tm_coverage.py` | `threat-model-coverage-report.md` renderer | Create (T5) |
| `tools/apd_gauntlet/render/advisory.py` | `advisory-report.md` renderer | Create (T6) |
| `tools/apd_gauntlet/attack_path/edge_review.py` | Heuristic-edge review file | Create (T7) |
| `tools/apd_gauntlet/threat_model/candidates.py` | TM–finding join, surface coverage, coverage assembly | Create (T8) |
| `tools/apd_gauntlet/lens_skills.py` | Per-lens packet compiler | Create (T11) |
| `tools/apd_gauntlet/code_recon/__init__.py`, `shards.py`, `merge.py` | Shard partition and merge | Create (T13) |
| `tools/apd_gauntlet/data/schemas/{xref-digest,report-digest,edge-review,tm-candidates,code-recon-shard}.schema.json` | New file contracts | Create |
| `tools/apd_gauntlet/data/schemas/domain.schema.json` | `consumers` | Modify (T9) |
| `tools/apd_gauntlet/build_domain_skill.py` | Consumer routing, `builder_format`, defaults sidecar | Modify (T9, T10) |
| `tools/apd_gauntlet/canonicalize.py` | Call shard merge and TM coverage assembly | Modify (T8, T13) |
| `tools/apd_gauntlet/validate.py` | Wire new 40-synthesis files into `SYNTHESIS_ROLLUPS` | Modify |
| `tools/apd_gauntlet/cli.py` | Six commands; `validate-domain` consumer checks | Modify |
| `.claude/workflows/apd-gauntlet.js`, `tools/apd_gauntlet/plan_run.py`, `tools/apd_gauntlet/runner/flow.py`, `tools/apd_gauntlet/runner/instructions.py` | New steps and instructions | Modify |
| `.claude/agents/*.md` (and bundled copies) | Inputs, outputs, tools, then `model`/`effort` | Modify |
| `domains/*/domain.yaml` | `consumers` | Modify (T9) |
| `.claude/skills/apd-domain/{SKILL.md,by-goal/*.md,attack-path-defaults.md,lens/*.md}` | Regenerated committed pbm default | Modify/Create (T9–T11) |
| `templates/{advisory-report,threat-model-authored,threat-model-coverage-report,attack-path-report}.template.md` | Document Python rendering | Modify (T3–T6) |
| `tests/test_xref_digest.py`, `tests/test_report_digest.py`, `tests/test_render_*.py`, `tests/test_edge_review.py`, `tests/test_tm_candidates.py`, `tests/test_lens_skills.py`, `tests/test_code_recon_merge.py` and the agent-contract tests named per task | Tests | Create |
| `tests/test_agent_effort.py` (WS3), `tests/test_workflow_dispatch_trace.py` (WS3), `tests/test_cli_resume_plan.py` (WS1), `tests/runner/*` (LA2) | Pinned tables, trace labels, resume rows, runner order | Modify |
| `tools/apd_gauntlet/resume_plan.py` (WS1) | Agent rows lose Python-rendered outputs; code-recon rows per shard | Modify (T3–T8, T14) |
| `tools/apd_gauntlet/lint_agents.py` | `model` required | Modify (T23) |
| `tests/conftest.py` | `ha_run` fixture | Modify (T1) |
| Docs listed in Global Constraints, plus `docs/adapting-to-other-domains.md`, `docs/attack-path-analysis.md`, `docs/threat-modeling.md`, `docs/architecture.md` | Docs | Modify |

---

### Task 0a: Emit-shape consistency

(Consolidated plan task N14.)

Smaller models copy examples literally; today the examples contradict the rules.

**Files:** `.claude/skills/apd-finding-schema/SKILL.md` (example blocks), `templates/finding.template.yaml`, `templates/capability.template.yaml`, `tools/apd_gauntlet/data/domains/pbm/immutability-classes.md`, `tools/apd_gauntlet/data/domains/pbm/data-taxonomy.md`; Create `tests/test_emit_examples.py`.

- [ ] **Step 1:** Tests: `test_schema_skill_and_templates_show_emit_shape` (every YAML example block parses, has no `id` or `schema_version`, and canonicalizes and validates inside a temporary run); `test_no_pack_tells_specialists_to_emit_lens_perspectives` (grep the pack files).
- [ ] **Step 2–4:** Fail; rewrite the examples in list form without `id`/`schema_version`, and reword the two pbm sentences so only the synthesizer writes `lens_perspectives`; pass; QG; bundle sync; SCP. Commit: `fix(skills): examples show exactly what agents emit`.

### Task 0b: `omitClaudeMd: true` on every agent

(Consolidated plan task N15.)

Requires Claude Code ≥ 2.1.271. Stops a client repository's `CLAUDE.md` from loading into every subagent (LA2 already loads no settings).

- [ ] **Step 1:** Test `tests/test_agent_effort.py::test_every_agent_omits_claude_md` (every `.claude/agents/*.md` frontmatter has `omitClaudeMd: true`).
- [ ] **Step 2–4:** Fail; add the key; `lint_agents` accepts it; pass; QG; bundle sync. SCP with a 20 KB `CLAUDE.md` placed in the workspace: outputs unchanged, input tokens lower. Commit: `perf(agents): do not load the workspace CLAUDE.md into subagents`.

### Task 1: Cross-tier digest (`xref-digest`)

**Files:**

- Create: `tools/apd_gauntlet/digests.py`, `tools/apd_gauntlet/data/schemas/xref-digest.schema.json`, `tests/test_xref_digest.py`, `tests/test_lens_xref_digest_contract.py`
- Modify: `tools/apd_gauntlet/cli.py` (new command after `canonicalize`, lines 1298–1342); `tools/apd_gauntlet/validate.py:480` (`SYNTHESIS_ROLLUPS`); `.claude/workflows/apd-gauntlet.js` (`runTier`: `async function runTier(`, ≈ 713); `tools/apd_gauntlet/plan_run.py:119-131`; `tools/apd_gauntlet/runner/flow.py` (tier phases); `.claude/agents/apd-{distributed,resilient,ephemeral,authenticity,non-repudiation,immutability}.md` (Required reading item 7, line 19, and the Inputs line); `tests/conftest.py`; docs per Global Constraints
- Test: `tests/test_workflow_apd_gauntlet.py`, `tests/test_workflow_dispatch_trace.py`, `tests/test_cli_plan_run.py`, `tests/runner/test_flow_pre_synthesis.py`, `tests/runner/test_flow_parity.py`, `tests/test_workflow_runner_awaits.py`

**Interfaces:**

- Consumes: `validate.extract_records(doc, root_key)` (`validate.py:87`); LA2 `scenario()`, `Runner`.
- Produces:
  - `TIER_DIRS = ("10-trustworthiness", "20-scalability", "30-auditability")`
  - `@dataclass(frozen=True) class DigestResult: path: Path; records: int; skipped_files: tuple[tuple[str, str], ...]`
  - `def build_xref_digest(run_dir: Path, before: Literal["20-scalability", "30-auditability"]) -> DigestResult`
  - CLI `apd-gauntlet xref-digest RUN_DIR --before {20-scalability|30-auditability}` (click `Choice`; anything else is exit 2)
  - File `40-synthesis/digests/xref-<before>.yaml`: `{schema_version: 1, generated_by: apd-gauntlet, before, tiers: [...], records: [{id, kind: finding|capability, tier, apd_goal, title, severity?, disposition?, maturity?, related_concerns?}], skipped_files: [{path, reason}]}`; records ordered by tier, file name, document order
  - `tests/conftest.py` fixture `ha_run(tmp_path) -> Path`: copies `examples/apd-20260612-home-assistant/expected` to `tmp_path / "apd-20260612-home-assistant"` and copies the example's `.apd-run.yaml` into it
  - Step label `xref-digest-<tier_dir>` (tier-2 and tier-3 only)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_xref_digest.py
def _digest(run, before):
    r = CliRunner().invoke(main, ["xref-digest", str(run), "--before", before])
    assert r.exit_code == 0, r.output
    path = run / f"40-synthesis/digests/xref-{before}.yaml"
    return path, yaml.safe_load(path.read_text()), r

def test_xref_digest_before_tier2_on_ha(ha_run):
    path, doc, _ = _digest(ha_run, "20-scalability")
    assert doc["tiers"] == ["10-trustworthiness"] and len(doc["records"]) == 34
    full = sum(p.stat().st_size for p in (ha_run / "10-trustworthiness").glob("*.yaml"))
    assert full == 128_812 and path.stat().st_size * 10 < full
    assert {"id", "kind", "tier", "apd_goal", "title"} <= set(doc["records"][0])
    assert not {"detail", "evidence", "summary"} & set(doc["records"][0])

def test_xref_digest_before_tier3_covers_two_tiers(ha_run):
    path, doc, _ = _digest(ha_run, "30-auditability")
    assert doc["tiers"] == ["10-trustworthiness", "20-scalability"] and len(doc["records"]) == 67
    assert path.stat().st_size * 10 < 255_786

def test_xref_digest_lists_unparseable_file(ha_run):
    (ha_run / "10-trustworthiness/integrity.findings.yaml").write_text("finding:\n  - title: [unclosed")
    caps = ha_run / "10-trustworthiness/availability.capabilities.yaml"
    doc = yaml.safe_load(caps.read_text()); del doc["capability"][0]["id"]; caps.write_text(yaml.safe_dump(doc))
    _, out, r = _digest(ha_run, "20-scalability")
    skipped = {s["path"]: s["reason"] for s in out["skipped_files"]}
    assert "10-trustworthiness/integrity.findings.yaml" in skipped
    assert skipped["10-trustworthiness/availability.capabilities.yaml#0"] == "record has no id"
    assert "WARNING xref-digest" in r.output and "integrity.findings.yaml" in r.output

def test_xref_digest_rejects_tier1(ha_run):
    assert CliRunner().invoke(main, ["xref-digest", str(ha_run), "--before", "10-trustworthiness"]).exit_code == 2

def test_xref_digest_is_byte_stable(ha_run):
    a, _, _ = _digest(ha_run, "30-auditability"); first = a.read_bytes()
    assert _digest(ha_run, "30-auditability")[0].read_bytes() == first

def test_validate_checks_xref_digest(ha_run):
    _digest(ha_run, "20-scalability")
    r = CliRunner().invoke(main, ["validate", str(ha_run), "--schema-only", "--errors-only"])
    assert "xref-20-scalability.yaml" not in r.output
```

```python
# tests/test_lens_xref_digest_contract.py
CASES = [(l, "xref-20-scalability") for l in ("distributed", "resilient", "ephemeral")] + \
        [(l, "xref-30-auditability") for l in ("authenticity", "non-repudiation", "immutability")]

@pytest.mark.parametrize("lens,digest", CASES)
def test_tier23_lens_reads_digest_not_tier_files(lens, digest):
    text = (AGENTS / f"apd-{lens}.md").read_text()
    assert f"40-synthesis/digests/{digest}.yaml" in text
    assert "All `10-trustworthiness/*.findings.yaml`" not in text
    assert "`10-trustworthiness/confidentiality.findings.yaml` and" not in text
```

Append to the channel tests:

```python
# tests/test_workflow_dispatch_trace.py
def test_xref_digest_dispatch_order():
    tr = trace(HA_SHAPED); L = [d["label"] for d in tr]; by = {d["label"]: d for d in tr}
    assert L.index("tier-gate-10-trustworthiness") < L.index("xref-digest-20-scalability") < L.index("distributed")
    assert L.index("tier-gate-20-scalability") < L.index("xref-digest-30-auditability") < L.index("authenticity")
    assert by["xref-digest-20-scalability"]["command"] == "apd-gauntlet xref-digest runs/r --before 20-scalability"
    assert "xref-digest-10-trustworthiness" not in L

# tests/test_cli_plan_run.py
WS5_COMMANDS = ("xref-digest", "report-digest", "render", "analyze-attack-paths",
                "edge-review", "tm-candidates", "build-lens-skills")

def test_plan_run_lists_every_ws5_cli_step(tmp_path):          # _plan(tmp_path, cfg) is WS1's helper in this file; do not redefine it
    js = WORKFLOW_JS.read_text(encoding="utf-8")
    dispatched = {c for c in WS5_COMMANDS if f"pyStep('{c}'" in js}
    refs = {s["ref"].split()[0] for s in _plan(tmp_path, dict(FULL_CFG, threat_model="inputs/tm.md")) if s["kind"] == "CLI"}
    assert dispatched <= refs, dispatched - refs

def test_plan_run_xref_digest_rows(tmp_path):
    plan = _plan(tmp_path, FULL_CFG); refs = [s["ref"] for s in plan]
    for tier in ("20-scalability", "30-auditability"):
        i = refs.index(f"xref-digest runs/apd-test-full --before {tier}")
        assert plan[i]["phase"] == tier and plan[i + 1]["kind"] == "AGENT"
    assert not any(r.startswith("xref-digest") and r.endswith("10-trustworthiness") for r in refs)

# tests/runner/test_flow_pre_synthesis.py
def test_xref_digest_precedes_tier2_and_tier3(tmp_path):
    r = scenario(tmp_path); asyncio.run(r.runner.run(stop_after="tier-3")); L = r.labels
    assert max(L.index(x) for x in ("confidentiality", "integrity", "availability")) < L.index("xref-digest-20-scalability")
    assert L.index("xref-digest-20-scalability") < min(L.index(x) for x in ("distributed", "resilient", "ephemeral"))
    assert L.index("xref-digest-30-auditability") < L.index("authenticity")
```

In `tests/runner/test_flow_parity.py::test_labels_exist_in_workflow`, add a prefix check `assert "'xref-digest-'" in js`. In `tests/test_workflow_dispatch_trace.py`, insert `xref-digest-20-scalability` and `xref-digest-30-auditability` into `CLI_LABELS` after `tier-gate-10-trustworthiness` and `tier-gate-20-scalability` respectively (after any WS1 repair labels for that tier). In `tests/test_workflow_runner_awaits.py`, both labels join `EXPECTED_GREEN_LABELS` before those tiers' lens fan-outs (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_xref_digest.py tests/test_lens_xref_digest_contract.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "xref or ws5" -v`
Expected: FAIL (`No such command 'xref-digest'`; digest paths absent from agents; label missing)

- [ ] **Step 3: Implement**

- `digests.py`: load each `*.findings.yaml` / `*.capabilities.yaml` of the earlier tiers with `yaml.safe_load` and `extract_records`; a `yaml.YAMLError` or `OSError` adds `(relpath, reason)` to `skipped_files`, and a record without `id` adds `(f"{relpath}#{index}", "record has no id")`; each skip prints `WARNING xref-digest: skipped <path>: <reason>` to stderr. Keep only `related_concerns` when non-empty.
- Schema: `schema_version` const 1, `generated_by` const `apd-gauntlet`, `apd_goal`/`severity`/`disposition` via `"$ref": "_defs.schema.json#/$defs/<name>"`, `additionalProperties: false` throughout. Register `"digests/xref-20-scalability.yaml"` and `"digests/xref-30-auditability.yaml"` in `SYNTHESIS_ROLLUPS`.
- Workflow, first statements of `runTier` after `phase(phaseName)`:

```js
if (tierDir !== '10-trustworthiness') {
  await pyStep('xref-digest', { phase: phaseName, label: 'xref-digest-' + tierDir, cliArgs: '--before ' + tierDir,
    outputs: runDir + '/40-synthesis/digests/xref-' + tierDir + '.yaml', alwaysRun: true });
}
```

- `plan_run.py`: in the tier loop, before the lens rows for every tier except the first, `_step(tier_dir, "CLI", f"xref-digest {run_dir} --before {tier_dir}", f"40-synthesis/digests/xref-{tier_dir}.yaml")`.
- `runner/flow.py`: before dispatching the lenses of tier-2 and tier-3, run CLI `["xref-digest", str(run_dir), "--before", tier_dir]` with label `xref-digest-<tier_dir>`, always run.
- Agents: tier-2 item 7 becomes "`40-synthesis/digests/xref-20-scalability.yaml` — one line per tier-1 finding and capability (id, goal, severity or maturity, disposition, title, related concerns). Use it to fill `cross_references`. Grep `10-trustworthiness/` by id only when you need a full record." Tier-3 names `xref-30-auditability.yaml` and tiers 1–2. Update the matching Inputs line. Sync the bundle.
- Docs: CLI list line; field-register row (`xref digest` → `digests.build_xref_digest`); schema-evolution entry "v2.0.0 — WS5 context files" (this entry grows in Tasks 2, 7, 8, 9 and 13); CHANGELOG "Added".

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude docs CHANGELOG.md
git commit -m "feat(context): give tier-2 and tier-3 lenses a cross-tier digest instead of whole tier files"
```

- [ ] **Step 6: Operator gate (OG, tag `t1`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t1 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows tier-2 and tier-3 lens input tokens below baseline.

### Task 2: Report-writer digest (`report-digest`)

**Files:**

- Create: `tools/apd_gauntlet/data/schemas/report-digest.schema.json`, `tests/test_report_digest.py`
- Modify: `tools/apd_gauntlet/digests.py`, `tools/apd_gauntlet/cli.py`, `tools/apd_gauntlet/validate.py:480`, `.claude/workflows/apd-gauntlet.js` (attempt-0 writer, `label: 'report-writer-attempt-0'`, ≈ 978–983), `tools/apd_gauntlet/plan_run.py:182-186`, `tools/apd_gauntlet/runner/flow.py` (`synthesis-report`), `tools/apd_gauntlet/runner/instructions.py` (`apd-report-writer`), `.claude/agents/apd-report-writer.md` (tools lines 12–14, the `## Inputs` list), docs
- Test: `tests/test_workflow_apd_gauntlet.py`, `tests/test_workflow_dispatch_trace.py`, `tests/test_cli_plan_run.py`, `tests/runner/test_flow_synthesis.py`, `tests/runner/test_flow_parity.py`, `tests/test_report_writer_qualitative.py`, `tests/test_workflow_runner_awaits.py`

**Interfaces:**

- Consumes: Task 1 `DigestResult`.
- Produces:
  - `def build_report_digest(run_dir: Path) -> DigestResult` (raises `FileNotFoundError` naming `40-synthesis/deduped-findings.yaml` when absent)
  - CLI `apd-gauntlet report-digest RUN_DIR` (exit 1 with that message when the deduped corpus is missing)
  - File `40-synthesis/digests/report.yaml`: `{schema_version: 1, generated_by: apd-gauntlet, findings: [{id, source: deduped|attack-path, apd_goal, severity, disposition, confidence, title, summary, related_concerns?, merged_from?}], capabilities: [{id, apd_goal, maturity, title}], full_record_ids: [...], skipped_files: [...]}`; `full_record_ids` lists every critical and high finding id in `findings` order
  - Step label `report-digest`

- [ ] **Step 1: Write the failing tests**

```python
def test_report_digest_on_ha(ha_run):
    r = CliRunner().invoke(main, ["report-digest", str(ha_run)]); assert r.exit_code == 0, r.output
    doc = yaml.safe_load((ha_run / "40-synthesis/digests/report.yaml").read_text())
    by_src = Counter(f["source"] for f in doc["findings"])
    assert by_src == {"deduped": 46, "attack-path": 18} and len(doc["capabilities"]) == 28
    assert len(doc["full_record_ids"]) == 44
    assert not {"detail", "evidence", "recommendation"} & set(doc["findings"][0])
    assert (ha_run / "40-synthesis/digests/report.yaml").stat().st_size * 7 < 309_126

def test_report_digest_requires_deduped_corpus(ha_run):
    (ha_run / "40-synthesis/deduped-findings.yaml").unlink()
    r = CliRunner().invoke(main, ["report-digest", str(ha_run)])
    assert r.exit_code == 1 and "deduped-findings.yaml" in r.output

def test_report_digest_without_apath(ha_run):
    (ha_run / "40-synthesis/attack-path.findings.yaml").unlink()
    CliRunner().invoke(main, ["report-digest", str(ha_run)])
    doc = yaml.safe_load((ha_run / "40-synthesis/digests/report.yaml").read_text())
    assert {f["source"] for f in doc["findings"]} == {"deduped"}

def test_writer_reads_digest_and_can_grep():               # tests/test_report_writer_qualitative.py
    meta = yaml.safe_load(AGENT.split("---")[1])
    assert "Grep" in meta["tools"] and "40-synthesis/digests/report.yaml" in AGENT
    assert "full_record_ids" in AGENT

def test_report_digest_precedes_report_writer():           # tests/test_workflow_dispatch_trace.py
    L = [d["label"] for d in trace(HA_SHAPED)]
    assert L.index("post-tier4") < L.index("report-digest") < L.index("report-writer-attempt-0")

def test_writer_instruction_reads_digest():                # tests/test_workflow_apd_gauntlet.py
    m = re.search(r"llmStep\('apd-report-writer',(.*?)label: 'report-writer-attempt-0'", _text(), re.S)
    assert "digests/report.yaml" in m.group(1) and "deduped-findings.yaml +" not in m.group(1)

def test_plan_run_report_digest_row(tmp_path):              # tests/test_cli_plan_run.py
    refs = [s["ref"] for s in _plan(tmp_path, FULL_CFG)]
    assert refs.index("report-digest runs/apd-test-full") + 1 == refs.index("apd-report-writer")

def test_report_digest_precedes_writer(tmp_path):           # tests/runner/test_flow_synthesis.py
    r = scenario(tmp_path, auditor_text="GATE: pass"); asyncio.run(r.runner.run())
    assert r.labels.index("report-digest") + 1 == r.labels.index("report-writer-attempt-0")
    assert "digests/report.yaml" in r.instructions["report-writer-attempt-0"]
```

Add `"report-digest"` to `test_labels_exist_in_workflow`; insert `"report-digest"` before `"report-writer-attempt-0"` in `test_full_happy_path_tail`, and into `CLI_LABELS` after the `post-tier4` label. In `tests/test_workflow_runner_awaits.py`, `report-digest` joins `EXPECTED_GREEN_LABELS` at its position (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_report_digest.py tests/test_report_writer_qualitative.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "report_digest or writer or happy_path or labels" -v`
Expected: FAIL (command and step missing)

- [ ] **Step 3: Implement**

- `build_report_digest`: findings from `40-synthesis/deduped-findings.yaml` then `40-synthesis/attack-path.findings.yaml` (optional), capabilities from `40-synthesis/deduped-capabilities.yaml` (optional), via `extract_records`; drop empty `related_concerns`/`merged_from`. Schema `$ref`s `_defs` for goal, severity, disposition and confidence (`ordinal_level`); register `"digests/report.yaml"` in `SYNTHESIS_ROLLUPS`.
- Workflow: `await pyStep('report-digest', { phase: 'synthesis-report', label: 'report-digest', outputs: runDir + '/40-synthesis/digests/report.yaml', alwaysRun: true })` immediately before the attempt-0 writer. New attempt-0 instruction (mirror in `INSTRUCTIONS["apd-report-writer"]`):

```text
Read 40-synthesis/metrics.yaml + 40-synthesis/digests/report.yaml (every deduped and attack-path finding as a summary, every capability) + the COMPACT rollups + contradictions/severity-disagreements. Grep 40-synthesis/deduped-findings.yaml or attack-path.findings.yaml by id for a full record ONLY for ids in full_record_ids that you rank or cite. Rank the headline findings across BOTH sources; emit 40-synthesis/advisory-report.md + 40-synthesis/report-data.yaml.
```

- `plan_run.py`: `_step("synthesis-report", "CLI", f"report-digest {run_dir}", "40-synthesis/digests/report.yaml")` before the writer row. `runner/flow.py`: CLI `["report-digest", str(run_dir)]`, label `report-digest`, before `report-writer-attempt-0`.
- Writer agent: add `Grep` to `tools`; replace the `deduped-findings.yaml` input bullet with the digest and the `full_record_ids` grep rule, keeping the words `metrics.yaml` and `attack-path.findings.yaml`. Sync the bundle.
- Docs: CLI list, field register, schema-evolution, CHANGELOG.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude docs CHANGELOG.md
git commit -m "feat(context): feed the report writer a digest of the synthesis corpus"
```

- [ ] **Step 6: Operator gate (OG, tag `t2`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t2 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-report-writer` input tokens below baseline.

### Task 3: `render` command and the authored threat model

**Files:**

- Create: `tools/apd_gauntlet/render/__init__.py`, `tools/apd_gauntlet/render/tm_authored.py`, `tools/apd_gauntlet/threat_model/delta.py`, `tests/test_render_tm_authored.py`
- Modify: `tools/apd_gauntlet/cli.py`; `.claude/workflows/apd-gauntlet.js` (TM author instruction, `await llmStep('apd-threat-model-author'`, ≈ 534–539) plus the new render step; `tools/apd_gauntlet/plan_run.py:95-104`; `tools/apd_gauntlet/runner/flow.py` (`threat-model-author`); `tools/apd_gauntlet/runner/instructions.py` (`apd-threat-model-author`); `.claude/agents/apd-threat-model-author.md` (output contract item 2, Step 6, the self-check and the receipt example: lines 55, 139–145, 157 and 191 at `856ea96`); `tools/apd_gauntlet/resume_plan.py` (`threat-model-author` row); `templates/threat-model-authored.template.md` (intro); docs (`docs/threat-modeling.md`, field register, CHANGELOG)
- Test: `tests/test_workflow_apd_gauntlet.py`, `tests/test_workflow_dispatch_trace.py`, `tests/test_cli_plan_run.py`, `tests/runner/test_flow_pre_synthesis.py`, `tests/runner/test_flow_parity.py`, `tests/test_workflow_runner_awaits.py`

**Interfaces:**

- Produces:
  - `class RenderSkipped(Exception)`, `class RenderError(Exception)`
  - `ARTIFACTS: dict[str, tuple[str, Callable[[Path], str]]]` (name → (run-relative output path, renderer)); this task registers `threat-model-authored` → `00-context/threat-model-authored.md`
  - `def render_artifact(run_dir: Path, name: str) -> Path | None` (None when skipped; writes only when content changed)
  - `def md_cell(text: str) -> str` (escapes `|`, folds newlines to spaces)
  - `def render_tm_authored(run_dir: Path) -> str`
  - `delta.py`: `def supplied_vs_authored(authored: list[dict[str, Any]], supplied: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]` keyed on `(asset, framework_refs.stride_letter)`, entries with a null letter excluded, buckets `baseline_only_threats`, `supplied_only_threats`, `shared`, each item `{entry_id, asset, threat, stride_letter}`
  - CLI `apd-gauntlet render RUN_DIR --artifact NAME` (`Choice(sorted(ARTIFACTS))`): exit 0 and `render: wrote <path>`; exit 0 and `render: <name> skipped — <reason>`; exit 1 on `RenderError`; exit 2 on an unknown name
  - Step label `render-threat-model-authored`

- [ ] **Step 1: Write the failing tests**

```python
def _render(run, name):
    return CliRunner().invoke(main, ["render", str(run), "--artifact", name])

def test_render_tm_authored_on_ha(ha_run):
    (ha_run / "00-context/threat-model-authored.md").unlink()
    r = _render(ha_run, "threat-model-authored"); assert r.exit_code == 0, r.output
    md = (ha_run / "00-context/threat-model-authored.md").read_text()
    tm = yaml.safe_load((ha_run / "00-context/threat-model-normalized.yaml").read_text())
    assert all(e["entry_id"] in md for e in tm["entries"]) and len(tm["entries"]) == 212
    for row in ("| Total authored entries | 212 |", "| Grounded entries | 124 |",
                "| Blocked placeholders | 88 |", "| Surfaces covered | 47 |"):
        assert row in md
    assert "apd-threat-model-author" in md and "Supplied-vs-authored delta" not in md
    assert md.count("\n### ") == 47 and "\n\n\n" not in md and md.endswith("\n")

def test_render_is_byte_stable(ha_run):
    _render(ha_run, "threat-model-authored"); first = (ha_run / "00-context/threat-model-authored.md").read_bytes()
    _render(ha_run, "threat-model-authored"); assert (ha_run / "00-context/threat-model-authored.md").read_bytes() == first

def test_render_requires_minted_entry_ids(ha_run):
    p = ha_run / "00-context/threat-model-normalized.yaml"; doc = yaml.safe_load(p.read_text())
    del doc["entries"][0]["entry_id"]; p.write_text(yaml.safe_dump(doc))
    r = _render(ha_run, "threat-model-authored")
    assert r.exit_code == 1 and "run canonicalize first" in r.output

def test_render_supplied_delta(ha_run):
    doc = yaml.safe_load((ha_run / "00-context/threat-model-normalized.yaml").read_text())
    doc["entries"] = doc["entries"][1:]; doc["generated_by"] = "threat_model_recon"
    (ha_run / "00-context/threat-model-supplied-normalized.yaml").write_text(yaml.safe_dump(doc))
    _render(ha_run, "threat-model-authored")
    assert "| `baseline_only_threats` (authored found, supplied omitted) | 1 |" in \
        (ha_run / "00-context/threat-model-authored.md").read_text()

def test_render_unknown_artifact(ha_run):
    assert _render(ha_run, "nope").exit_code == 2
```

Channel tests: `test_tm_author_no_longer_writes_md` (the `llmStep('apd-threat-model-author'` block no longer contains `threat-model-authored.md`); in `tests/test_workflow_dispatch_trace.py`, `test_render_tm_authored_follows_tm_id_minting` (`L.index("canonicalize-threat-model") < L.index("render-threat-model-authored") < L.index("confidentiality")`, command `apd-gauntlet render runs/r --artifact threat-model-authored`) and the label inserted into `CLI_LABELS` after `canonicalize-threat-model`; `test_plan_run_render_tm_authored_row` (row `render runs/apd-test-full --artifact threat-model-authored` follows `apd-threat-model-author`); runner `test_render_tm_authored_after_author` (label order). Add the label to `test_labels_exist_in_workflow` and to `test_happy_path_labels` after `canonicalize-threat-model`. In `tests/test_cli_resume_plan.py`, the `threat-model-author` step is complete with only `00-context/threat-model-normalized.yaml` present. In `tests/test_workflow_runner_awaits.py`, `render-threat-model-authored` joins `EXPECTED_GREEN_LABELS` at its position (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_tm_authored.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "render or happy_path or labels" -v`
Expected: FAIL (`No such command 'render'`)

- [ ] **Step 3: Implement**

- Renderer sections, following the template's worked example: header lines (`**Generated by:** apd-threat-model-author`, methodology, `source_artifact`, run id from `.apd-run.yaml`); `## Summary` table (total, grounded = empty `prerequisite_evidence`, blocked, high/medium/low confidence, surfaces); `## Blocked cells by STRIDE category`; `## Highest-signal grounded threats` (every grounded high-confidence entry, entry order); `## Per-surface threats` with one `###` per surface in first-appearance order, a `Cat | Threat | Mitigation (design intent) | Confidence` table of grounded cells, a list of blocked cells with their `prerequisite_evidence`, and a `TM entry IDs:` line; `## Supplied-vs-authored delta` only when `00-context/threat-model-supplied-normalized.yaml` exists, using `supplied_vs_authored`. Raise `RenderError("threat-model-normalized.yaml has entries without entry_id; run canonicalize first")` when any id is missing.
- Workflow: in phase `threat-model-author`, drop "PLUS the human-readable 00-context/threat-model-authored.md" from the author instruction (WS1 removed `outputs` from `llmStep` call sites), then add `await pyStep('render', { phase: 'threat-model-author', label: 'render-threat-model-authored', cliArgs: '--artifact threat-model-authored', outputs: runDir + '/00-context/threat-model-authored.md', alwaysRun: true })` immediately after WS1's `canonicalize-threat-model` step (after the tm-recon `if/else`, before `async function runTier`), which mints the `tm-` ids the md lists. The step is advisory: its receipt is never wrapped in `isErr`. The `threat-model-author` row of `RESUMABLE_STEPS` becomes (`00-context/threat-model-normalized.yaml`,).
- Mirror in `runner/flow.py` (same position, label, args `["render", str(run_dir), "--artifact", "threat-model-authored"]`; failure logs a `warning`) and `INSTRUCTIONS["apd-threat-model-author"]`. `plan_run.py`: the agent row's outputs become `00-context/threat-model-normalized.yaml`, followed by a CLI row `render {run_dir} --artifact threat-model-authored`.
- Agent: the md is "rendered by `apd-gauntlet render --artifact threat-model-authored`; do not write it" (output contract item 2 and Step 6); drop the md from the self-check and receipt example. Template intro: produced by `apd-gauntlet render`, not the agent. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude templates docs CHANGELOG.md
git commit -m "feat(render): render the authored threat model from its YAML"
```

- [ ] **Step 6: Operator gate (OG, tag `t3`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t3 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-threat-model-author` output tokens below baseline.

### Task 4: Render the attack-path report

**Files:**

- Create: `tools/apd_gauntlet/attack_path/load.py`, `tools/apd_gauntlet/render/attack_path_report.py`, `tests/test_render_attack_path_report.py`
- Modify: `tools/apd_gauntlet/render/__init__.py` (register), `.claude/workflows/apd-gauntlet.js` (apath thunk, the second thunk of `await parallel([`, ≈ 907–918), `tools/apd_gauntlet/plan_run.py:166-174`, `tools/apd_gauntlet/runner/flow.py` (`apath`), `tools/apd_gauntlet/runner/instructions.py` (`apd-attack-path-analyzer`), `.claude/agents/apd-attack-path-analyzer.md` (Outputs lines 65–66 and Step 5 at `856ea96`), `tools/apd_gauntlet/resume_plan.py` (`apath` row), `tests/test_workflow_dispatch_trace.py` (`CLI_LABELS`), `tests/test_workflow_runner_awaits.py` (`ASYNC_HELPERS`, `CALLS`), `tests/js/workflow_dispatch_trace.mjs` (the `parallel` stub, only if WS3 Task 1 shipped it synchronous), `templates/attack-path-report.template.md` (intro; its `30-graph/` paths become `40-synthesis/`), `docs/attack-path-analysis.md`, field register, CHANGELOG
- Test: channel tests as in Task 3

**Interfaces:**

- Consumes: `Graph`, `Node`, `Edge` (`attack_path/graph.py`), `Path as APath` (`attack_path/enumerate.py:47`), `render_partitioned_diagrams` (`attack_path/mermaid.py:86`).
- Produces:
  - `def load_graph(path: Path) -> Graph` (maps YAML `from`/`to` to `from_node`/`to_node`)
  - `def load_paths(path: Path) -> list[APath]`
  - `TOP_PATHS = 20`
  - `def render_attack_path_report(run_dir: Path) -> str`: `RenderSkipped` when `40-synthesis/attack-path.findings.yaml` is absent; a blocked report when `asset-graph.yaml` is absent and the findings file holds a blocked finding
  - Step label `render-attack-path-report`

- [ ] **Step 1: Write the failing tests**

```python
def test_render_attack_path_report_on_ha(ha_run):
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "attack-path-report"]); assert r.exit_code == 0, r.output
    md = (ha_run / "40-synthesis/attack-path-report.md").read_text()
    for needle in ("1545", "195", "90", "max_hop=7", "max_paths_per_pair=12", "never claim"):
        assert needle in md
    assert md.count("\n#### Path ") == 20 and "20 of 1545" in md
    assert md.count("\n| atk-") == 195                      # one pair-summary row per pair
    for block in re.findall(r"```mermaid\n(.*?)```", md, re.S):
        assert len(re.findall(r'^\w+\["', block, re.M)) <= 50
    apath = yaml.safe_load((ha_run / "40-synthesis/attack-path.findings.yaml").read_text())["finding"]
    assert all(f["id"] in md for f in apath)

def test_render_attack_path_report_blocked_run(ha_run):
    syn = ha_run / "40-synthesis"
    for f in ("asset-graph.yaml", "attack-paths.yaml", "defense-graph.yaml"):
        (syn / f).unlink()
    _write_blocked_finding(syn, reason="crown_jewels: [] override")         # cli.py:961
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "attack-path-report"])
    assert r.exit_code == 0 and "## Attack-path analysis blocked" in (syn / "attack-path-report.md").read_text()

def test_render_attack_path_report_skips_without_apath(ha_run):
    (ha_run / "40-synthesis/attack-path.findings.yaml").unlink()
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "attack-path-report"])
    assert r.exit_code == 0 and "skipped" in r.output

def test_load_graph_round_trip(ha_run):
    g = load_graph(ha_run / "40-synthesis/asset-graph.yaml")
    assert g.node_count == 75 and g.edge_count == 3298                    # properties, graph.py:131-137
```

Channel tests: in `tests/test_workflow_dispatch_trace.py`, `L.index("apath") < L.index("render-attack-path-report") < L.index("post-tier4")` for `HA_SHAPED`, the label is absent for `{**HA_SHAPED, "crown_jewels": []}`, and it is inserted into `CLI_LABELS` before `post-tier4`; `plan_run` adds the CLI row after the analyzer row only when `crown_jewels` is non-empty; runner label order `apath` < `render-attack-path-report`. The `apath` row of `RESUMABLE_STEPS` becomes (`40-synthesis/attack-path.findings.yaml`,) and `tests/test_cli_resume_plan.py` follows.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_attack_path_report.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "attack_path_report or render or labels" -v`
Expected: FAIL (artifact not registered)

- [ ] **Step 3: Implement**

- Sections (template order, real paths): Scope (jewel and attacker names from graph nodes, `enumeration_parameters`, `build_summary.sources_used`); Headline summary (`summary` counts of `attack-paths.yaml` plus the net-new D3FEND count from `defense-graph.yaml`); High-leverage findings (overlays with non-empty `net_new_d3fend`, or "No bottleneck edge lacks a capability-backed D3FEND counter."); Top attack paths (the `TOP_PATHS` paths by severity_sum desc, hop_count asc, feasibility desc, path_id asc, headed "`20 of 1545` paths shown; the full set is in `attack-paths.yaml`"); Pair summary table (attacker id, jewel id, paths, truncated, best severity_sum, min hops); Diagram(s) via `render_partitioned_diagrams(paths=top, graph=g)`; Findings (`apath-*` id, severity, title); Caveats (the template's four bullets verbatim). The blocked report lists each blocked finding's title, summary and `prerequisite_evidence`.
- Workflow: move the apath thunk's body into `async function apathBranch()`, which awaits every dispatch and returns the analyzer's receipt (its no-crown-jewels branch still logs and returns `null`); the thunk becomes `function () { return apathBranch(); }`, and `apathBranch` joins `ASYNC_HELPERS` and `CALLS` in `tests/test_workflow_runner_awaits.py` (register A15.25). Inside the crown-jewels branch, after the analyzer's `await llmStep('apd-attack-path-analyzer', …)`, add `await pyStep('render', { phase: 'apath', label: 'render-attack-path-report', cliArgs: '--artifact attack-path-report', outputs: runDir + '/40-synthesis/attack-path-report.md', alwaysRun: true })`, then return the analyzer's receipt. The apath steps stay out of `EXPECTED_GREEN_LABELS` (the harness has no crown jewels). If WS3 Task 1's dispatch-trace harness (`tests/js/workflow_dispatch_trace.mjs`) still stubs `parallel: (ts) => ts.map((t) => t())`, change it in this commit to `parallel: (ts) => Promise.all(ts.map((t) => t()))`: a thunk now returns its helper's Promise, which the synchronous stub does not wait for. Drop `attack-path-report.md` from the analyzer instruction. Runner and `plan_run.py` mirror it.
- Agent: delete Step 5 ("Write the markdown report"); Outputs say the report is rendered by `apd-gauntlet render`. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude templates docs CHANGELOG.md
git commit -m "feat(render): render the attack-path report from the graph artifacts"
```

- [ ] **Step 6: Operator gate (OG, tag `t4`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t4 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-attack-path-analyzer` output tokens below baseline.

### Task 5: Render the threat-model coverage report

**Files:**

- Create: `tools/apd_gauntlet/render/tm_coverage.py`, `tests/test_render_tm_coverage.py`
- Modify: `tools/apd_gauntlet/render/__init__.py`, `.claude/workflows/apd-gauntlet.js` (after the `post-tier4` block), `tools/apd_gauntlet/plan_run.py:161-165` and the row after `post-tier4`, `tools/apd_gauntlet/runner/flow.py`, `tools/apd_gauntlet/resume_plan.py` (`tmeval` row), `tests/test_workflow_dispatch_trace.py` (`CLI_LABELS`), `.claude/agents/apd-threat-model-evaluator.md` (output contract item 2 lines 53–54, Step 8 lines 346–354, self-check lines 369–370 at `856ea96`), `templates/threat-model-coverage-report.template.md` (intro), `docs/threat-modeling.md`, field register, CHANGELOG
- Test: channel tests as in Task 3

**Interfaces:**

- Produces: `def render_tm_coverage_report(run_dir: Path) -> str` (`RenderError` naming `40-synthesis/threat-model-coverage.yaml` when absent); step label `render-threat-model-coverage-report`.

- [ ] **Step 1: Write the failing tests**

```python
def test_render_tm_coverage_on_ha(ha_run):
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "threat-model-coverage-report"]); assert r.exit_code == 0, r.output
    md = (ha_run / "40-synthesis/threat-model-coverage-report.md").read_text()
    assert "## Mode: authored baseline" in md and "| Contradictions emitted | 1 |" in md
    contra = md.split("## Contradictions", 1)[1].split("\n## ", 1)[0]
    assert "tmeval-5c02d052" in contra and "auth-1787eae1" in contra
    matrix = md.split("## Per-surface coverage matrix", 1)[1].split("\n## ", 1)[0]
    rows = [l for l in matrix.splitlines() if l.startswith("| ") and not l.startswith("| Surface")]
    assert len(rows) == 47
    assert "None emitted." in md.split("## Silences", 1)[1].split("\n## ", 1)[0]

def test_render_tm_coverage_requires_coverage_yaml(ha_run):
    (ha_run / "40-synthesis/threat-model-coverage.yaml").unlink()
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "threat-model-coverage-report"])
    assert r.exit_code == 1 and "threat-model-coverage.yaml" in r.output
```

Channel tests: in `tests/test_workflow_dispatch_trace.py`, `L.index("post-tier4") < L.index("render-threat-model-coverage-report") < L.index("report-writer-attempt-0")`, and the label goes into `CLI_LABELS` right after `post-tier4`; the tmeval `plan_run` row no longer lists the md; runner order `post-tier4` < `render-threat-model-coverage-report` < `report-writer-attempt-0`. The `tmeval` row of `RESUMABLE_STEPS` drops `40-synthesis/threat-model-coverage-report.md`. In `tests/test_workflow_runner_awaits.py`, `render-threat-model-coverage-report` joins `EXPECTED_GREEN_LABELS` at its position (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_tm_coverage.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "coverage or render or labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- Sections: header (generated by `apd-threat-model-evaluator`, source TM with its `generated_by` and methodology, run id); `## Mode` (fixed text per case: authored baseline with or without a supplied sibling, or recon-canonical); `## Summary` table (coverage `summary` plus confidence counts from the normalized TM); `## Per-surface coverage matrix` (`Surface | Present | Absent | Entries`); `## Coverage gaps`, `## Contradictions`, `## Silences`, `## Supplied omissions`, `## Blocked findings`, each listing the `40-threat-model/threat-model.findings.yaml` records whose `tmeval_key.flavor` matches (id, title, summary, cross-references, first evidence excerpt) or "None emitted."; `## Supplied-vs-authored delta` when the coverage YAML carries it.
- Workflow: `await pyStep('render', { phase: 'tmeval', label: 'render-threat-model-coverage-report', cliArgs: '--artifact threat-model-coverage-report', outputs: runDir + '/40-synthesis/threat-model-coverage-report.md', alwaysRun: true })` immediately after the `post-tier4` block (after `post-tier4-retry-1` and the synthesizer rollup fallback). Mirror in the runner and `plan_run.py`.
- Agent: delete Step 8; the output contract says the report is rendered by `apd-gauntlet render`. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude templates docs CHANGELOG.md
git commit -m "feat(render): render the threat-model coverage report from coverage YAML"
```

- [ ] **Step 6: Operator gate (OG, tag `t5`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t5 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-threat-model-evaluator` output tokens below baseline.

### Task 6: Render the advisory report

**Files:**

- Create: `tools/apd_gauntlet/render/advisory.py`, `tests/test_render_advisory.py`
- Modify: `tools/apd_gauntlet/render/__init__.py`; `.claude/workflows/apd-gauntlet.js` (writer instructions and the audit loop, from `label: 'report-writer-attempt-0'` through `for (let i = 0; i <= 2; i++)`, ≈ 978–1072); `tools/apd_gauntlet/plan_run.py:184-205`; `tools/apd_gauntlet/runner/flow.py` (`synthesis-audit`); `tools/apd_gauntlet/runner/instructions.py` (`apd-report-writer`, `:build-fix`, `:remediate`); `tools/apd_gauntlet/resume_plan.py` (`report-writer-attempt-0` row); `tests/test_workflow_dispatch_trace.py` (`CLI_LABELS`); `.claude/agents/apd-report-writer.md` (Required reading, Job, Outputs, receipt example); `templates/advisory-report.template.md` (§1 documents the headline and next-steps lists); `docs/html-report.md` (advisory markdown provenance), field register, CHANGELOG
- Test: `tests/test_report_writer_qualitative.py`, channel tests

**Interfaces:**

- Produces: `def render_advisory_report(run_dir: Path) -> str` (requires `report-data.yaml`, `metrics.yaml`, `deduped-findings.yaml`; other inputs optional); step label `'render-advisory-report-attempt-' + i`.

- [ ] **Step 1: Write the failing tests**

```python
def test_render_advisory_on_ha(ha_run):
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "advisory-report"]); assert r.exit_code == 0, r.output
    md = (ha_run / "40-synthesis/advisory-report.md").read_text()
    heads = re.findall(r"^## (\d+)\. ", md, re.M); assert heads == [str(i) for i in range(1, 11)]
    rd = yaml.safe_load((ha_run / "40-synthesis/report-data.yaml").read_text())
    s1 = md.split("## 1. ", 1)[1].split("\n## 2. ", 1)[0]
    assert all(h["id"] in s1 for h in rd["headline_findings"]) and all(n["text"] in s1 for n in rd["next_steps"])
    assert rd["exec_summary"]["paragraphs"][0] in s1
    assert md.split("## 4. ", 1)[1].split("\n## 5. ", 1)[0].count("\n#### ") == 43
    assert md.split("## 3. ", 1)[1].split("\n## 4. ", 1)[0].count("**`") == 3
    assert not re.search(r"<n>\s+(critical|high|medium|low)", s1)

def test_render_advisory_requires_report_data(ha_run):
    (ha_run / "40-synthesis/report-data.yaml").unlink()
    r = CliRunner().invoke(main, ["render", str(ha_run), "--artifact", "advisory-report"])
    assert r.exit_code == 1 and "report-data.yaml" in r.output

def test_writer_no_longer_writes_advisory_md():                 # tests/test_report_writer_qualitative.py
    assert "40-synthesis/advisory-report.md" not in AGENT.split("## Outputs", 1)[1].split("##", 1)[0]
    assert "metrics.yaml" in AGENT and "attack-path.findings.yaml" in AGENT

def test_audit_loop_renders_before_each_audit():                # tests/test_workflow_apd_gauntlet.py
    loop = _text().split("for (let i = 0; i <= 2; i++)", 1)[1]
    assert loop.index("'render-advisory-report-attempt-' + i") < loop.index("pyStep('audit-report'")
```

Runner: `test_render_precedes_each_audit` (`render-advisory-report-attempt-0` precedes `audit-report-attempt-0`, and `-attempt-1` precedes `audit-report-attempt-1` in the remediation scenario of `test_audit_loop_remediates_then_passes`); update `test_full_happy_path_tail`; add the `'render-advisory-report-attempt-'` prefix to the parity test. Insert `render-advisory-report-attempt-0` into `CLI_LABELS` before `audit-report-attempt-0`. In `tests/test_workflow_runner_awaits.py`, `render-advisory-report-attempt-0`, `-1` and `-2` join `EXPECTED_GREEN_LABELS` at their positions (register A15.25). The `report-writer-attempt-0` row of `RESUMABLE_STEPS` becomes (`40-synthesis/report-data.yaml`,).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_advisory.py tests/test_report_writer_qualitative.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/runner -k "advisory or writer or audit or happy_path or labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- Renderer follows `templates/advisory-report.template.md`: frontmatter (`framework_version`, packs from `.apd-run.yaml` domains, `run_id`); §1 exec-summary paragraphs, `posture_summary`, a ranked headline list (id, severity, title, resolved from deduped or `attack-path.findings.yaml`) and the ranked next steps; §2 deduped capabilities by tier and goal; §3 blocked findings by goal; §4 non-blocked deduped findings by severity then tier, each with the template's field blocks; §5 `contradictions.yaml`; §6 `report-data.strengths` with caveats; §7–§9 one row per entry of `nist-coverage.yaml`, `attack-exposure.yaml`, `apd-coverage-matrix.yaml`; Framework coverage pointers for each present rollup; §10 `severity-disagreements.yaml`; the appendix verbatim. Counts are never hand-typed: they come from the YAML.
- Workflow: first statement of each audit-loop iteration: `await pyStep('render', { phase: 'synthesis-audit', label: 'render-advisory-report-attempt-' + i, cliArgs: '--artifact advisory-report', outputs: runDir + '/40-synthesis/advisory-report.md', alwaysRun: true })`. Writer instructions emit only `40-synthesis/report-data.yaml` ("Python renders advisory-report.md"); remove `advisory-report.md` from the three writer instructions. Mirror in the runner and the three `INSTRUCTIONS` keys. `plan_run.py`: writer outputs `40-synthesis/report-data.yaml`; a CLI row `render {run_dir} --artifact advisory-report` before the `audit-report` row.
- Agent: outputs only `report-data.yaml`; drop `templates/advisory-report.template.md` from Required reading; receipt example lists one output. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude templates docs CHANGELOG.md
git commit -m "feat(render): render advisory-report.md from report-data and the synthesis corpus"
```

- [ ] **Step 6: Operator gate (OG, tag `t6`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t6 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four (gate 5 is the one to watch: the auditor now reads Python-rendered prose); `usage` shows `apd-report-writer` output tokens below baseline.

### Task 7: Attack-path edge review (`edge-review`)

**Files:**

- Create: `tools/apd_gauntlet/attack_path/edge_review.py`, `tools/apd_gauntlet/data/schemas/edge-review.schema.json`, `tests/test_edge_review.py`
- Modify: `tools/apd_gauntlet/cli.py`, `tools/apd_gauntlet/validate.py:480`, `.claude/workflows/apd-gauntlet.js` (`async function apathBranch()`, Task 4), `tools/apd_gauntlet/plan_run.py:166-174`, `tools/apd_gauntlet/runner/flow.py` (`apath`), `tools/apd_gauntlet/runner/instructions.py`, `.claude/agents/apd-attack-path-analyzer.md` (Inputs lines 39–56, Steps 2–4 lines 74–97), `tools/apd_gauntlet/resume_plan.py` (`apath` row), `tests/test_workflow_dispatch_trace.py` (`CLI_LABELS`), `docs/attack-path-analysis.md`, docs per Global Constraints
- Test: channel tests

**Interfaces:**

- Consumes: `synthesis.loader.load_corpus(run_dir)` (record titles and excerpts by id).
- Produces:
  - `REVIEWED_EDGE_TYPES = ("compromisable_via_finding", "mitigated_by_capability")`
  - `@dataclass(frozen=True) class EdgeReviewResult: path: Path; edges: int; missing_records: tuple[str, ...]; blocked: bool`
  - `def build_edge_review(run_dir: Path) -> EdgeReviewResult`
  - CLI `apd-gauntlet edge-review RUN_DIR` (exit 1 when `asset-graph.yaml` is absent and the run is not blocked)
  - File `40-synthesis/edge-review.yaml`: `{schema_version: 1, generated_by: apd-gauntlet, blocked: bool, edges: [{edge_id, edge_type, from: {node_id, name, node_type}, to: {node_id, name, node_type}, record_id, record_title, confidence, excerpts: [...]}], missing_records: [...]}` in `edge_id` order
  - Step labels `analyze-attack-paths`, `edge-review`

- [ ] **Step 1: Write the failing tests**

```python
def test_edge_review_on_ha(ha_run):
    r = CliRunner().invoke(main, ["edge-review", str(ha_run)]); assert r.exit_code == 0, r.output
    path = ha_run / "40-synthesis/edge-review.yaml"; doc = yaml.safe_load(path.read_text())
    assert Counter(e["edge_type"] for e in doc["edges"]) == {"compromisable_via_finding": 27, "mitigated_by_capability": 10}
    assert doc["missing_records"] == [] and all(e["record_title"] and e["from"]["name"] for e in doc["edges"])
    assert path.stat().st_size * 20 < 713_922

def test_edge_review_blocked_run(ha_run):
    (ha_run / "40-synthesis/asset-graph.yaml").unlink()
    _write_blocked_finding(ha_run / "40-synthesis", reason="crown_jewels: [] override")
    r = CliRunner().invoke(main, ["edge-review", str(ha_run)])
    doc = yaml.safe_load((ha_run / "40-synthesis/edge-review.yaml").read_text())
    assert r.exit_code == 0 and doc["blocked"] is True and doc["edges"] == []

def test_edge_review_needs_graph(ha_run):
    (ha_run / "40-synthesis/asset-graph.yaml").unlink()
    r = CliRunner().invoke(main, ["edge-review", str(ha_run)])
    assert r.exit_code == 1 and "run analyze-attack-paths first" in r.output

def test_apath_branch_runs_floor_then_review_then_agent():        # tests/test_workflow_dispatch_trace.py
    L = [d["label"] for d in trace(HA_SHAPED)]
    assert L.index("analyze-attack-paths") < L.index("edge-review") < L.index("apath")
    assert "edge-review" not in [d["label"] for d in trace({**HA_SHAPED, "crown_jewels": []})]

def test_analyzer_instruction_reads_edge_review():                 # tests/test_workflow_apd_gauntlet.py
    src = _text(); g = src.index("llmStep('apd-attack-path-analyzer'"); block = src[g:src.index("});", g)]
    assert "edge-review.yaml" in block and "never read asset-graph.yaml whole" in block
```

Plan-run and runner tests: `analyze-attack-paths` and `edge-review` rows and labels precede the analyzer when `crown_jewels` is non-empty, and are absent otherwise. Add both labels to `test_labels_exist_in_workflow` and to `CLI_LABELS` (before `render-attack-path-report`). The `apath` row of `RESUMABLE_STEPS` becomes (`40-synthesis/attack-path.findings.yaml`, `40-synthesis/edge-review.yaml`); a crash during the analyzer's review therefore resumes past it, which this plan accepts because the review only corrects excerpts.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_edge_review.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "edge or apath or labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- Build from `asset-graph.yaml` nodes and edges; records from `load_corpus`; an edge whose record id is unknown lands in `missing_records`. Blocked = no graph and `attack-path.findings.yaml` holds a `disposition: blocked` record. Schema `$ref`s `_defs` `ordinal_level` for confidence; register `"edge-review.yaml"`.
- Workflow, inside the crown-jewels branch of `apathBranch` (Task 4; register A15.25) before the analyzer: `await pyStep('analyze-attack-paths', { phase: 'apath', label: 'analyze-attack-paths', outputs: runDir + '/40-synthesis/asset-graph.yaml, attack-paths.yaml, defense-graph.yaml, attack-path.findings.yaml', alwaysRun: true })` then `await pyStep('edge-review', { phase: 'apath', label: 'edge-review', outputs: runDir + '/40-synthesis/edge-review.yaml', alwaysRun: true })`. New analyzer instruction (mirror in `INSTRUCTIONS["apd-attack-path-analyzer"]`):

```text
The workflow has already run apd-gauntlet analyze-attack-paths and edge-review. Review ONLY 40-synthesis/edge-review.yaml (each heuristic compromisable_via_finding / mitigated_by_capability edge with its endpoints, record title and evidence excerpts); never read asset-graph.yaml whole. Correct an edge only when the evidence names a different endpoint: fix the record's evidence excerpt, then re-run apd-gauntlet analyze-attack-paths. Emit nothing else; Python renders the report.
```

- Agent: Step 2 says the floor already ran; Step 3 ("Author edge provenance") reads `40-synthesis/edge-review.yaml` and greps `asset-graph.yaml` by `edge_id` only; Inputs gain the review file. Mirror runner and `plan_run.py` rows. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude docs CHANGELOG.md
git commit -m "feat(context): review heuristic attack-path edges from a 37-edge file, not the whole graph"
```

- [ ] **Step 6: Operator gate (OG, tag `t7`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t7 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-attack-path-analyzer` input tokens below baseline.

### Task 8: Threat-model evaluator pre-pass (`tm-candidates`)

**Files:**

- Create: `tools/apd_gauntlet/threat_model/candidates.py`, `tools/apd_gauntlet/data/schemas/tm-candidates.schema.json`, `tests/test_tm_candidates.py`
- Modify: `tools/apd_gauntlet/cli.py`, `tools/apd_gauntlet/validate.py:480`, `tools/apd_gauntlet/canonicalize.py:424-475` (`canonicalize_run`), `.claude/workflows/apd-gauntlet.js` (tmeval thunk, the first thunk of `await parallel([`, ≈ 888–906), `tools/apd_gauntlet/plan_run.py:161-165`, `tools/apd_gauntlet/runner/flow.py` (`tmeval`), `tools/apd_gauntlet/runner/instructions.py`, `tools/apd_gauntlet/resume_plan.py` (`tmeval` row), `tests/test_workflow_dispatch_trace.py` (`CLI_LABELS`), `tests/test_workflow_runner_awaits.py` (`ASYNC_HELPERS`, `CALLS`, `EXPECTED_GREEN_LABELS`), `.claude/agents/apd-threat-model-evaluator.md` (Step 1, Step 2c's coverage-YAML paragraph lines 169–174, Steps 6 and 9, self-check), `docs/threat-modeling.md`, docs per Global Constraints
- Test: `tests/test_tmeval_agent_contract.py` (extend), channel tests

**Interfaces:**

- Consumes: Task 3 `supplied_vs_authored`; `00-context/code-evidence-index.yaml` entries (`qualified_name`, `id`).
- Produces:
  - `CATEGORY_SETS = {"stride": ("S", "T", "R", "I", "D", "E"), "linddun": ("L", "I", "N_repudiation", "D_etectability", "D_isclosure", "U", "N_compliance")}`
  - `def surface_coverage(tm: dict[str, Any]) -> list[dict[str, Any]]` (the `threat-model-coverage.schema.json` `surface_coverage` shape)
  - `def finding_anchors(finding: dict[str, Any], cev_by_qn: dict[str, set[str]]) -> frozenset[str]`
  - `@dataclass(frozen=True) class TmCandidatesResult: path: Path; pairs: int; entries: int; findings: int`
  - `def build_tm_candidates(run_dir: Path) -> TmCandidatesResult`
  - `def assemble_tm_coverage(run_dir: Path) -> Path | None` (None when `tm-candidates.yaml` is absent)
  - CLI `apd-gauntlet tm-candidates RUN_DIR`
  - File `40-synthesis/tm-candidates.yaml`: `{schema_version: 1, generated_by: apd-gauntlet, tm_generated_by, methodology, total_entries, candidates: [{tm_entry_id, finding_id, anchors: [...]}], tm_entries: [{entry_id, asset, category, inferred_apd_goals, mitigation, extraction_confidence}], findings: [{id, apd_goal, severity, title, summary}], surface_coverage: [...], supplied_vs_authored?: {baseline_only_threats: [{entry_id, asset, threat, stride_letter, corroborated_by: [...]}], supplied_only_threats, shared}}`. WS6 `tm-screen` reads `candidates[].tm_entry_id` and `candidates[].finding_id`.
  - Step label `tm-candidates`

Join rule (exact): a pair `(entry, finding)` is a candidate when `entry.mitigation` is non-null, `finding.apd_goal ∈ entry.inferred_apd_goals`, and they share an anchor: `finding_anchors(finding)` (every `cev-[0-9a-f]{8}` in the finding's title, summary, detail, evidence excerpts and locators, plus the `cev-` ids whose `qualified_name` equals the `<qn>` of an evidence locator matching `^code:(?P<qn>.+?):L\d+`) intersects the `cev-` ids in the entry's threat, mitigation and `source_locator`, or the finding text contains `entry.entry_id`. Findings come from `40-synthesis/deduped-findings.yaml`. A baseline-only entry is `corroborated_by` the findings that satisfy the same rule without the mitigation condition.

- [ ] **Step 1: Write the failing tests**

```python
def test_tm_candidates_on_ha(ha_run):
    r = CliRunner().invoke(main, ["tm-candidates", str(ha_run)]); assert r.exit_code == 0, r.output
    doc = yaml.safe_load((ha_run / "40-synthesis/tm-candidates.yaml").read_text())
    assert (len(doc["candidates"]), len(doc["tm_entries"]), len(doc["findings"])) == (94, 75, 21)
    assert {"tm_entry_id": "tm-f8db6c3a", "finding_id": "auth-1787eae1"} in \
        [{k: c[k] for k in ("tm_entry_id", "finding_id")} for c in doc["candidates"]]   # HA's emitted contradiction
    assert (ha_run / "40-synthesis/tm-candidates.yaml").stat().st_size * 7 < 430_649       # measured 53,562 B

def test_surface_coverage_matches_ha_evaluator_output(ha_run):
    tm = yaml.safe_load((ha_run / "00-context/threat-model-normalized.yaml").read_text())
    cov = yaml.safe_load((ha_run / "40-synthesis/threat-model-coverage.yaml").read_text())
    assert surface_coverage(tm) == cov["surface_coverage"]                            # 47 surfaces, exact

def test_assemble_coverage_counts_flavors(ha_run):
    CliRunner().invoke(main, ["tm-candidates", str(ha_run)])
    (ha_run / "40-synthesis/threat-model-coverage.yaml").unlink()
    assert CliRunner().invoke(main, ["canonicalize", str(ha_run)]).exit_code == 0
    cov = yaml.safe_load((ha_run / "40-synthesis/threat-model-coverage.yaml").read_text())
    assert cov["summary"] == {"total_entries": 212, "contradictions_emitted": 1, "silences_emitted": 0,
                              "coverage_gaps_emitted": 0, "surfaces_examined": 47}

def test_supplied_delta_carries_corroboration(ha_run): ...     # supplied copy minus tm-f8db6c3a -> baseline_only has it with corroborated_by ["auth-1787eae1", "auth-3794d338"]

def test_evaluator_reads_candidates_only():                    # tests/test_tmeval_agent_contract.py
    text = AGENT.read_text(encoding="utf-8")
    assert "40-synthesis/tm-candidates.yaml" in text and "### Step 9" not in text
```

Channel tests: in `tests/test_workflow_dispatch_trace.py`, `L.index("tm-candidates") < L.index("tmeval")` and the label goes into `CLI_LABELS` first among the tier-4 CLI labels; the evaluator instruction contains `tm-candidates.yaml` and no longer `Emit 40-synthesis/threat-model-coverage.yaml`; matching `plan_run` row and runner label order; label added to the parity test. The `tmeval` row of `RESUMABLE_STEPS` becomes (`40-threat-model/threat-model.findings.yaml`,). In `tests/test_workflow_runner_awaits.py`, `tmevalBranch` joins `ASYNC_HELPERS` and `CALLS`, and `tm-candidates` joins `EXPECTED_GREEN_LABELS` before `tmeval` (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tm_candidates.py tests/test_tmeval_agent_contract.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "tm_candidates or tmeval or labels or candidates" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- `surface_coverage`: group entries by `asset` in first-appearance order; category = `stride_letter`, else `linddun_letter`, else `attack_tree_position`; present = categories of entries with empty `prerequisite_evidence`, ordered by the methodology's set; absent = the set minus present (empty for methodologies without a closed set).
- `assemble_tm_coverage` writes `40-synthesis/threat-model-coverage.yaml` (`generated_by: threat_model_evaluator`, the only value the schema allows) from `tm-candidates.yaml`, with `summary` counted from `40-threat-model/threat-model.findings.yaml` `tmeval_key.flavor` (`supplied_omissions_emitted` only when a sibling exists). Call it at the end of `canonicalize_run`, after the `tmeval-` minting.
- Workflow: move the tmeval thunk's body into `async function tmevalBranch()`, which awaits every dispatch and returns the evaluator's receipt; the thunk becomes `function () { return tmevalBranch(); }` (register A15.25). First statement of `tmevalBranch`: `await pyStep('tm-candidates', { phase: 'tmeval', label: 'tm-candidates', outputs: runDir + '/40-synthesis/tm-candidates.yaml', alwaysRun: true })`. New evaluator instruction (mirror in `INSTRUCTIONS["apd-threat-model-evaluator"]`):

```text
Read ONLY 40-synthesis/tm-candidates.yaml. Judge each candidate pair: emit a contradiction finding only when the finding's evidence shows the entry's mitigation is absent or broken. For each supplied_vs_authored.baseline_only_threats entry with a non-empty corroborated_by, emit a supplied_omission finding. Write tmeval findings (tmeval_key, no id) to 40-threat-model/threat-model.findings.yaml. Python writes threat-model-coverage.yaml and the coverage report.
```

- Agent: Step 1 reads the candidates file (the TM and deduped files only when `tm_generated_by` is `threat_model_recon`, for Steps 3 and 5); Step 2c's coverage paragraph and Steps 6 and 9 say Python assembles the coverage YAML. Schema: `surface_coverage` items `$ref` `threat-model-coverage.schema.json#/properties/surface_coverage/items`; register `"tm-candidates.yaml"`. Mirror runner and `plan_run.py`. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests .claude docs CHANGELOG.md
git commit -m "feat(tmeval): join threat-model entries to findings in Python and count coverage there"
```

- [ ] **Step 6: Operator gate (OG, tag `t8`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t8 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-threat-model-evaluator` input tokens below baseline.

### Task 9: Prune domain sidecars with a declarative `consumers:` map

**Files:**

- Modify: `tools/apd_gauntlet/data/schemas/domain.schema.json`; `tools/apd_gauntlet/build_domain_skill.py:154` and `:177-204` (signature: `_pack_content_sha256`, `_existing_pack_signature`; compared at `:321-323`), `:235-276` (`_sidecar_frontmatter`), `:277-375` (`build_domain_skill`); `tools/apd_gauntlet/cli.py:246-283` (`validate-domain`); `domains/{agentic-ai,api-security,identity-security,mobile-applications,pbm,security-tooling}/domain.yaml`; `.claude/skills/apd-domain/SKILL.md` and `by-goal/*.md` (regenerated pbm default); the nine lens agents' Required reading item 5 wording; `tests/test_build_domain_skill_pruning.py:88-97`; `docs/adapting-to-other-domains.md` (§2 schema list after line 59, §4); `docs/schema-evolution.md`; CHANGELOG
- Create: `tests/test_domain_consumers.py`

**Interfaces:**

- Produces:
  - Schema property `consumers`: object; property names match `^(?!common-patterns/)(?!/)(?!.*\.\.)[^/]+\.md$`; values arrays (`minItems: 1`, `uniqueItems`) of the nine goal stems (`GOAL_FILE_STEMS`, hyphenated)
  - `BUILDER_FORMAT = 2` (written as `metadata.builder_format` in every generated file and compared with WS1's signature)
  - `ALL_GOAL_STEMS: frozenset[str]`
  - `def pack_consumers(meta: dict[str, Any], calibration_rels: Iterable[str]) -> dict[str, frozenset[str]]` (missing key → `ALL_GOAL_STEMS`; raises `ValueError` for a key not among the pack's calibration includes or for `severity-rubric.md`, "severity-rubric.md must reach every lens")
  - Sidecar frontmatter `pruned.omitted_calibration: ["<pack>/<rel>", ...]`; `retained_calibration` keeps its meaning (stems any pack retained)
- Pack values (pack-stated consumers): every pack `consequential-actions.md: [non-repudiation]` and `immutability-classes.md: [immutability]`; `pbm` adds `data-taxonomy.md: [confidentiality, integrity, authenticity, non-repudiation, immutability]` (its "Consuming APD lenses" section) and widens `immutability-classes.md` to `[immutability, non-repudiation, confidentiality]` (its cross-reference, line 71). Pack versions stay; WS1's content hash invalidates caches.
- WS1's signature (register A10.2): `_existing_pack_signature` returns a 3-tuple `(packs, framework_version, content_sha256)`, which `build_domain_skill` compares later; adding `BUILDER_FORMAT` changes both the tuple and the comparison. Task 9's tests build with framework `2.0.0`, so they pass only on `next` (packs declare `<3.0.0` there).

- [ ] **Step 1: Write the failing tests**

```python
def _sidecars(out):
    return {p.stem: p.read_text() for p in (out / "by-goal").glob("*.md")}

def test_pbm_routing(tmp_path):
    build_domain_skill(["pbm"], REPO_DOMAINS, tmp_path, "2.0.0"); s = _sidecars(tmp_path)
    assert "Source: `consequential-actions.md`" in s["non-repudiation"]
    assert "Source: `consequential-actions.md`" not in s["confidentiality"]
    assert "Source: `data-taxonomy.md`" not in s["availability"]
    assert all("Source: `severity-rubric.md`" in t for t in s.values())
    assert all("Domain attack-path defaults" not in t for t in s.values())
    assert sum(len(t.encode()) for t in s.values()) * 2 < 911_200          # measured 408.6 KB of 911.2 KB

def test_pack_without_consumers_keeps_every_calibration_file(tmp_path):
    pack = shutil.copytree(REPO_DOMAINS / "api-security", tmp_path / "d/api-security")
    meta = yaml.safe_load((pack / "domain.yaml").read_text()); meta.pop("consumers")
    (pack / "domain.yaml").write_text(yaml.safe_dump(meta))
    build_domain_skill(["api-security"], tmp_path / "d", tmp_path / "out", "2.0.0")
    for text in _sidecars(tmp_path / "out").values():
        for cal in ("severity-rubric", "consequential-actions", "immutability-classes", "data-taxonomy"):
            assert f"Source: `{cal}.md`" in text

def test_builder_format_change_forces_rebuild(tmp_path, monkeypatch):
    build_domain_skill(["pbm"], REPO_DOMAINS, tmp_path, "2.0.0")
    monkeypatch.setattr(bds, "BUILDER_FORMAT", bds.BUILDER_FORMAT + 1)
    build_domain_skill(["pbm"], REPO_DOMAINS, tmp_path, "2.0.0")
    assert f"builder_format: {bds.BUILDER_FORMAT}" in (tmp_path / "by-goal/integrity.md").read_text()

def test_omitted_calibration_is_listed(tmp_path):
    build_domain_skill(["pbm"], REPO_DOMAINS, tmp_path, "2.0.0")
    meta = _frontmatter((tmp_path / "by-goal/availability.md").read_text())["metadata"]
    assert set(meta["pruned"]["omitted_calibration"]) == {"pbm/consequential-actions.md", "pbm/data-taxonomy.md", "pbm/immutability-classes.md"}

@pytest.mark.parametrize("bad,msg", [({"severity-rubric.md": ["integrity"]}, "must reach every lens"),
                                     ({"missing.md": ["integrity"]}, "not a calibration include")])
def test_validate_domain_rejects_bad_consumers(tmp_path, bad, msg): ...   # tmp pack -> validate-domain exit 1, msg in output

def test_committed_default_is_current(tmp_path):
    build_domain_skill(["pbm"], REPO_DOMAINS, tmp_path, "2.0.0")
    for p in (tmp_path / "by-goal").glob("*.md"):
        assert _strip_ts(p.read_text()) == _strip_ts((REPO / ".claude/skills/apd-domain/by-goal" / p.name).read_text())
```

Helpers: `REPO`, `REPO_DOMAINS = Path("domains")`, `FIXTURES`, `_frontmatter` and `_strip_ts` as in `tests/test_build_domain_skill_pruning.py`; `bds` is the `apd_gauntlet.build_domain_skill` module. Update `test_sidecar_keeps_calibration_and_only_own_goal_patterns` (lines 88–97) to assert pbm's confidentiality sidecar carries `severity-rubric`, `data-taxonomy` and `immutability-classes` but not `consequential-actions`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_domain_consumers.py tests/test_build_domain_skill_pruning.py tests/test_build_domain_skill.py tests/test_validate_domain.py -v`
Expected: FAIL (`consumers` rejected by `additionalProperties: false`; sidecars unpruned)

- [ ] **Step 3: Implement**

- Sidecar filter in `build_domain_skill`: keep a chunk when its goal stem is the sidecar's, or when it is a calibration chunk whose pack's `pack_consumers` includes the stem. Stop appending `surfaces` to sidecars (the full `SKILL.md` keeps them). Frontmatter note: "Calibration files are routed by each pack's `consumers:` map (default: all nine lenses); attack-path defaults are not included."
- `validate-domain` calls `pack_consumers` after the include check and prints `Consumers error in '<pack>': <message>` with exit 1.
- Regenerate the committed default: `apd-gauntlet build-domain-skill pbm` from the repo root.
- Lens agents, item 5: "your goal-scoped view of the active domain(s): the full severity rubric, the calibration files each pack routes to your lens (`pruned.omitted_calibration` lists the rest), and the <goal> common patterns." Sync the bundle.
- Docs: `consumers` in `docs/adapting-to-other-domains.md` §2 (default all nine; rubric always reaches every lens) and §4 (routing is per pack); schema-evolution entry for `domain` (R7).

- [ ] **Step 4: Run tests and lint**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/ && markdownlint-cli2 ".claude/**/*.md" "docs/**/*.md" "!docs/superpowers/plans/**"`
Expected: PASS, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet domains .claude tests docs CHANGELOG.md
git commit -m "feat(domain): route calibration files to lenses through a declarative consumers map"
```

- [ ] **Step 6: Operator gate (OG, tag `t9`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t9 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows lens input tokens below the Task 8 runs. A loss traced to a missing calibration file is fixed by widening that pack's `consumers` entry, not by code.

### Task 10: Attack-path defaults sidecar

**Files:**

- Modify: `tools/apd_gauntlet/build_domain_skill.py` (`build_domain_skill`, `_render_surfaces_section` lines 131–152), `tools/apd_gauntlet/cli.py:160-164` (echo the sidecar path), `.claude/agents/apd-intake.md` (lines 74, 269), `.claude/agents/apd-attack-path-analyzer.md` (lines 30, 56), `.claude/skills/apd-domain/attack-path-defaults.md` (regenerated), `docs/adapting-to-other-domains.md`, `docs/attack-path-analysis.md`, field register, CHANGELOG
- Test: `tests/test_domain_consumers.py` (extend), `tests/test_intake_contract.py` (extend), `tests/test_lint_agent_apd_attack_path_analyzer.py` (extend)

**Interfaces:**

- Produces: `ATTACK_PATH_DEFAULTS = "attack-path-defaults.md"`; `build_domain_skill` writes `out_dir / ATTACK_PATH_DEFAULTS` (frontmatter with packs and `builder_format`, then the merged surfaces section, or the single line "No selected pack declares crown jewels, attacker positions or default trust boundaries."); its absence counts as stale in the idempotency check.

- [ ] **Step 1: Write the failing tests**

```python
def test_attack_path_defaults_sidecar(tmp_path):
    build_domain_skill(["pbm"], REPO_DOMAINS, tmp_path, "2.0.0")
    text = (tmp_path / "attack-path-defaults.md").read_text()
    assert "### Crown jewels" in text and "phi_store" in text and "Source: `severity-rubric.md`" not in text
    assert len(text.encode()) * 10 < (tmp_path / "SKILL.md").stat().st_size        # 14.6 KB vs 156.5 KB

def test_attack_path_defaults_when_no_surfaces(tmp_path): ...     # tmp pack with no surface blocks -> the "No selected pack declares" line

def test_missing_defaults_sidecar_triggers_rebuild(tmp_path):
    build_domain_skill(["sample"], FIXTURES, tmp_path, "1.0.0"); (tmp_path / "attack-path-defaults.md").unlink()
    build_domain_skill(["sample"], FIXTURES, tmp_path, "1.0.0"); assert (tmp_path / "attack-path-defaults.md").exists()

@pytest.mark.parametrize("agent", ["apd-intake", "apd-attack-path-analyzer"])
def test_agent_reads_defaults_sidecar(agent):
    text = (AGENTS / f"{agent}.md").read_text()
    assert ".claude/skills/apd-domain/attack-path-defaults.md" in text
    assert "section of the `.claude/skills/apd-domain/SKILL.md`" not in text and "merged `Domain attack-path defaults` section" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_domain_consumers.py tests/test_intake_contract.py tests/test_lint_agent_apd_attack_path_analyzer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — write the sidecar beside `SKILL.md`; point the two agents at it; regenerate the default with `apd-gauntlet build-domain-skill pbm`; sync the bundle; docs.

- [ ] **Step 4: Run tests and lint**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/ && markdownlint-cli2 ".claude/**/*.md"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet .claude tests docs CHANGELOG.md
git commit -m "feat(domain): emit attack-path-defaults.md for intake and the attack-path analyzer"
```

- [ ] **Step 6: Operator gate (OG, tag `t10`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t10 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows `apd-intake` and `apd-attack-path-analyzer` input tokens below the Task 9 runs.

### Task 11: Per-lens skill packets (`build-lens-skills`)

**Files:**

- Create: `tools/apd_gauntlet/lens_skills.py`, `tests/test_lens_skills.py`, `.claude/skills/apd-domain/lens/*.md` (committed default)
- Modify: `tools/apd_gauntlet/cli.py`, `.claude/workflows/apd-gauntlet.js` (setup phase, after `prepare-run`), `tools/apd_gauntlet/plan_run.py:52-66`, `tools/apd_gauntlet/runner/flow.py` (`setup`), the nine lens agents (Required reading items 1–5), `docs/running-the-gauntlet.md` (line 74 paragraph), `docs/extending-agents.md`, CHANGELOG
- Test: channel tests, `tests/test_workflow_runner_awaits.py`

**Interfaces:**

- Consumes: Task 9 by-goal sidecars; `.claude/skills/{apd-framework,apd-evidence-discipline,apd-finding-schema,apd-control-mappings}/SKILL.md`; `.apd-run.yaml` `taxonomies`.
- Produces:
  - `SHARED_SKILLS = ("apd-framework", "apd-evidence-discipline", "apd-finding-schema", "apd-control-mappings")`
  - `TAXONOMY_HEADINGS: dict[str, tuple[str, ...]]` (`"### CWE"` → `("cwe",)`, `"### OWASP Top 10 (web"` → `("owasp_top10",)`, `"### OWASP API Top 10"` → `("owasp_api_top10",)`, `"### OWASP LLM Top 10"` → `("owasp_llm_top10",)`, `"### D3FEND"` → `("d3fend",)`, `"### MITRE ATLAS"` → `("mitre_atlas",)`, `"### OWASP MAS"` → `("masvs", "maswe")`)
  - `def extract_framework(text: str, stem: str) -> str` (preamble and "Lens versus scope"; the lens's own goal section; each other goal's `**Lens.**` line and any `**Boundary:` paragraph naming the lens; cross-tier bullets naming the lens; "How to use this skill")
  - `def extract_control_mappings(text: str, stem: str, taxonomies: Collection[str]) -> str` (drops other goals' NIST subsections and undeclared taxonomy subsections)
  - `def build_lens_skills(run_dir: Path, *, skills_dir: Path, out_dir: Path) -> list[Path]` (raises `FileNotFoundError` "run build-domain-skill first" when `out_dir/by-goal` is missing)
  - CLI `apd-gauntlet build-lens-skills RUN_DIR [--skills-dir .claude/skills] [--out .claude/skills/apd-domain]`
  - Packet `out_dir/lens/<stem>.md`: frontmatter `name: apd-domain-lens-<stem>`, `metadata: {lens, taxonomies, sources: [{path, sha256}], omitted_sections: [...]}`; body = the framework and control-mappings extracts, the evidence-discipline and finding-schema skills whole (the finding schema keeps "Specialist agents do not emit `lens_perspectives`", which some pack text contradicts), then `## Active domain calibration` and the by-goal body; every source heading demoted one level; the packet ends with `## Output skeleton (emit exactly this shape)`, generated from the schema enums with `agent`, `apd_tier` and `apd_goal` pre-filled (register A10.4)
  - Step label `build-lens-skills`

- [ ] **Step 1: Write the failing tests**

```python
def _build(tmp_path, taxonomies):
    run = tmp_path / "run"; run.mkdir(); (run / ".apd-run.yaml").write_text(yaml.safe_dump({"run_id": "r", "domains": ["pbm"], "taxonomies": taxonomies}))
    out = tmp_path / "apd-domain"; build_domain_skill(["pbm"], REPO_DOMAINS, out, "2.0.0")
    build_lens_skills(run, skills_dir=REPO / ".claude/skills", out_dir=out)
    return {p.stem: p.read_text() for p in (out / "lens").glob("*.md")}

def test_packet_scopes_framework_and_mappings(tmp_path):
    conf = _build(tmp_path, ["cwe"])["confidentiality"]
    assert "Is the data hidden from parties not authorized to see it?" in conf
    assert "Schema enforcement (typed schemas, contract validation)" not in conf      # integrity in-scope bullet
    assert "Demonstrative Examples" in conf and "MASWE-Beta caveat" not in conf
    assert "Specialist agents do not emit `lens_perspectives`" in conf
    assert "Source: `common-patterns/confidentiality.md`" in conf

ALL_TAX = ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10", "mitre_atlas", "masvs", "maswe"]
HA_TAX = ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "masvs", "maswe"]

@pytest.mark.parametrize("taxonomies,min_saving", [([], 22_500), (HA_TAX, 15_000), (ALL_TAX, 13_500)])
def test_packet_saving(tmp_path, taxonomies, min_saving):          # measured minimums 23,294 / 15,741 / 13,956 B
    shared = sum(len((REPO / ".claude/skills" / s / "SKILL.md").read_bytes()) for s in SHARED_SKILLS)   # 64,751
    for stem, text in _build(tmp_path, taxonomies).items():
        body = text.split("\n---\n", 1)[1].split("## Active domain calibration", 1)[0]
        assert shared - len(body.encode()) >= min_saving, stem

def test_packets_lint_clean_and_stable(tmp_path):
    first = _build(tmp_path, ["cwe"]); again = _build(tmp_path, ["cwe"])
    assert first == again and all("\n# " not in t and "\n\n\n" not in t for t in first.values())

def test_committed_packets_match_rebuild(tmp_path):
    out = shutil.copytree(REPO / ".claude/skills/apd-domain", tmp_path / "apd-domain")
    build_lens_skills(REPO / "examples/apd-20260601-claim-event-bus", skills_dir=REPO / ".claude/skills", out_dir=out)
    for p in (out / "lens").glob("*.md"):
        assert p.read_text() == (REPO / ".claude/skills/apd-domain/lens" / p.name).read_text()

@pytest.mark.parametrize("stem", GOAL_FILE_STEMS)
def test_lens_agent_reads_one_packet(stem):
    text = (AGENTS / f"apd-{stem}.md").read_text()
    assert f".claude/skills/apd-domain/lens/{stem}.md" in text and ".claude/skills/apd-control-mappings/SKILL.md" not in text
```

Helpers as in Task 9, plus `AGENTS`, `GOAL_FILE_STEMS` and `SHARED_SKILLS`. Channel tests: in `tests/test_workflow_dispatch_trace.py`, `L.index("prepare-run") < L.index("build-lens-skills") < L.index("intake")` with command `apd-gauntlet build-lens-skills runs/r`, and the label goes into `CLI_LABELS` right after `prepare-run`; `plan_run` emits `build-lens-skills {run_dir}` after the `prepare-run` row; runner label `build-lens-skills` follows `prepare-run` (update `test_happy_path_labels`); parity list. Add `tests/test_lens_skills.py::test_packet_ends_with_emittable_skeleton`: every packet ends with the `## Output skeleton (emit exactly this shape)` block, with `agent`, `apd_tier` and `apd_goal` pre-filled for its lens (register A10.4). In `tests/test_workflow_runner_awaits.py`, `build-lens-skills` joins `EXPECTED_GREEN_LABELS` at its position (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lens_skills.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -k "lens or setup or happy_path or labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- Section extraction walks headings outside code fences. Each source gets an HTML comment `<!-- source: <path> sha256=<hex> -->` before its demoted text; `omitted_sections` names every dropped heading. Write only when content changed; `_finalize` from `build_domain_skill` ends the file.
- Workflow: `await pyStep('build-lens-skills', { phase: 'setup', label: 'build-lens-skills', outputs: '.claude/skills/apd-domain/lens/<goal>.md (9 lens packets)', alwaysRun: true })` right after `prepare-run`. Mirror runner (`["build-lens-skills", str(run_dir)]`, cwd = workspace) and `plan_run.py`.
- Lens agents: items 1–5 become one item, "`.claude/skills/apd-domain/lens/<stem>.md` — your compiled packet: the framework section and boundary calls for your lens, evidence discipline, the finding schema, your NIST and ATT&CK mapping guidance plus the run's declared taxonomies, and your goal-scoped domain calibration. Do not open the four source skills separately." Renumber the rest. Sync the bundle.
- Committed default: `apd-gauntlet build-lens-skills examples/apd-20260601-claim-event-bus` from the repo root (pbm; taxonomies cwe, mitre_attack, d3fend, owasp_api_top10).

- [ ] **Step 4: Run tests and lint**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/ && apd-gauntlet lint-agents --agent-dir .claude/agents/ && markdownlint-cli2 ".claude/**/*.md"`
Expected: PASS, lint-agents clean, 0 markdown errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet .claude tests docs CHANGELOG.md
git commit -m "feat(context): compile one skill packet per lens"
```

- [ ] **Step 6: Operator gate (OG, tag `t11`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t11 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows four fewer turns and lower input tokens per lens than the Task 10 runs.

### Task 12: Patch-mode remediation

**Files:**

- Modify: `.claude/agents/apd-report-writer.md` (tools; new "## Patch mode" section), `.claude/workflows/apd-gauntlet.js` (remediation dispatch, `'report-writer-attempt-' + (i + 1)`, ≈ 1064–1069), `tools/apd_gauntlet/runner/instructions.py` (`apd-report-writer:remediate`), `tools/apd_gauntlet/runner/flow.py` (`synthesis-audit`), `tests/test_workflow_apd_gauntlet.py:448-451` (`test_report_writer_remediation_reads_report_audit`), CHANGELOG
- Test: `tests/test_report_writer_qualitative.py`, `tests/runner/test_flow_synthesis.py`

**Interfaces:**

- Consumes: the `audit-report` receipt's `errors[0].message` (`exit=<N>; <stderr-tail>`, which carries the `FAIL [<klass>]: <name> — <detail>` lines printed at `cli.py:1519`); LA2 `CliResult.stderr_tail`.
- Produces: remediation instruction text (both channels):

```text
PATCH MODE. Fix ONLY the failed report-audit checks and critique lines below by editing 40-synthesis/report-data.yaml in place with Edit. Do not regenerate it, do not re-read the corpus, and leave every other block unchanged; Grep a finding by id only when a fix needs it. FAILED CHECKS: <failed> CRITIQUE: <critique>
```

`<failed>` is the receipt message when the audit exited non-zero, else `none (structural and editorial checks passed)`; the runner passes the `FAIL [` lines of `audit-report-attempt-<i>`'s `stderr_tail` as `errors`.

- [ ] **Step 1: Write the failing tests**

```python
def test_writer_has_edit_and_patch_mode():                      # tests/test_report_writer_qualitative.py
    meta = yaml.safe_load(AGENT.split("---")[1])
    assert "Edit" in meta["tools"] and "## Patch mode" in AGENT

def test_report_writer_remediation_is_patch_mode():              # replaces lines 448-451
    src = _text()
    assert "PATCH MODE." in src and "FAILED CHECKS: " in src and "audit.errors[0].message" in src
    assert 'klass is "editorial"' not in src

def test_remediation_carries_failed_checks_only(tmp_path):        # tests/runner/test_flow_synthesis.py
    out = "audit-report: FAIL (structural_failed=0 editorial_failed=1)"
    err = "  FAIL [editorial]: exec_summary_present — paragraphs=0"
    r = scenario(tmp_path, auditor_texts=["GATE: fail\n- invented-content", "GATE: pass"],
                 cli_outcomes={"audit-report-attempt-0": (1, out, err)})
    asyncio.run(r.runner.run()); text = r.instructions["report-writer-attempt-1"]
    assert "PATCH MODE." in text and "exec_summary_present" in text and "invented-content" in text
    assert "id_coverage_findings" not in text
```

If LA2's `FakeCli` outcomes are `(exit_code, stdout)` pairs, extend them to an optional third `stderr` element in this task.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_report_writer_qualitative.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/runner/test_flow_synthesis.py -v`
Expected: FAIL

- [ ] **Step 3: Implement** — add `Edit` to the writer's tools and a "## Patch mode" section (smallest edit per listed check; never touch `advisory-report.md`); in the loop compute `const failed = (audit && audit.status === 'error' && audit.errors && audit.errors[0]) ? audit.errors[0].message : 'none (structural and editorial checks passed)';` and send the instruction above; mirror in `INSTRUCTIONS["apd-report-writer:remediate"]` and the runner. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .claude tools/apd_gauntlet tests CHANGELOG.md
git commit -m "feat(report): remediate the report in patch mode with only the failed checks and critique"
```

- [ ] **Step 6: Operator gate (OG, tag `t12`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t12 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; on runs that remediated, `usage` shows `report-writer-attempt-<n>` (n ≥ 1) output tokens below baseline.

### Task 13: Code-recon shard partition and merge

Not behaviour-changing on its own: the merge acts only when shard files exist, which Task 14 introduces. No operator gate.

**Files:**

- Create: `tools/apd_gauntlet/code_recon/__init__.py`, `tools/apd_gauntlet/code_recon/shards.py`, `tools/apd_gauntlet/code_recon/merge.py`, `tools/apd_gauntlet/data/schemas/code-recon-shard.schema.json`, `tests/test_code_recon_merge.py`
- Modify: `tools/apd_gauntlet/canonicalize.py:424-475` (first statement of `canonicalize_run`), `docs/schema-evolution.md`, field register

**Interfaces:**

- Produces:
  - `RECON_SHARD_SIZE = 6`
  - `@dataclass(frozen=True) class ReconShard: shard_id: str; projects: tuple[str, ...]`
  - `def recon_shards(cfg: dict[str, Any]) -> list[ReconShard]`: without `repos`, one shard `single` whose projects are `(cfg["cbm_project"],)` when set, else `()`; with `repos`, one `primary-<n>` shard per `role: primary` repo, then `dependency-<n>` and `peer-<n>` shards of at most `RECON_SHARD_SIZE` repos each in declared order (a repo without `role` counts as `peer`)
  - Shard file `00-context/code-recon/<shard_id>.yaml` (`cross-repo.yaml` for the cross-repo pass): `{schema_version: 1, generated_by: code_recon, shard, projects, generated_at, repos: [{cbm_project, indexed_commit_sha}], not_analyzed: [{cbm_project, reason}], entries: [<code-evidence entry without id>], containers: [<c4-recon container>], uses_edges: [<c4-recon edge>], brief_markdown}`
  - `@dataclass(frozen=True) class MergeResult: shards_merged: tuple[str, ...]; shards_missing: tuple[str, ...]; shards_invalid: tuple[str, ...]; duplicates_collapsed: int`
  - `def merge_recon_shards(run_dir: Path) -> MergeResult | None` (None, touching nothing, when `00-context/code-recon/` has no shard file, or when `merge-report.yaml` records the same `shard_sha256` map as the shard files on disk, so the later `canonicalize` passes at each tier gate never rewrite the merged files)
- Merge outputs: `00-context/code-evidence-index.yaml` (entries without ids, deduplicated on `(repo, qualified_name, line_range)` with `apd_relevance` unioned in goal order; `cbm_project` and `indexed_commit_sha` from the first primary repo; `generated_at` = the latest shard value; `repos[]` in declared order), then WS1's cev minting in the same `canonicalize_run` mints ids; `00-context/c4-recon.yaml` (containers by name, first wins; a `not_analyzed` container `{name: <repo short name>, kind: service, repo, provenance: {source: artifact, locator: ".apd-run.yaml#repos[<cbm_project>]"}, analysis_state: not_analyzed}` for each project of a missing or invalid shard or listed in `not_analyzed`); `00-context/code-architecture-brief.md` (header, one section per shard, a computed per-lens table of at most five entries per goal, and a "Not analyzed" list); `00-context/code-recon/merge-report.yaml`. When no shard has an entry, write `00-context/code-recon-skipped.md` listing the reasons and no index.

**Index coverage (consolidated plan task N21, coverage capture; its warning and edge items are in Task 14):**

- [ ] Code recon and shard agents add `mcp__codebase-memory-mcp__check_index_coverage` to their tools and record per-repo coverage (parse-partial and skipped counts) in optional `repos[].coverage` of `code-evidence-index.schema.json`.
- [ ] Tests: `test_coverage_block_validates`.

- [ ] **Step 1: Write the failing tests**

```python
HA_CFG = yaml.safe_load(Path("examples/apd-20260612-home-assistant/.apd-run.yaml").read_text())

def test_ha_shards():
    shards = recon_shards(HA_CFG)
    assert [s.shard_id for s in shards] == ["primary-1", "dependency-1", "dependency-2", "dependency-3", "peer-1"]
    assert sum(len(s.projects) for s in shards) == 23 and shards[0].projects == ("home-assistant-repos-core",)

def test_single_repo_shard():
    assert recon_shards({"cbm_project": "p"}) == [ReconShard("single", ("p",))]

def test_merge_collapses_duplicate_and_unions_relevance(tmp_path):
    run = shard_run(tmp_path, {"single": [entry("a.f", "L1-L2", ["integrity"])],
                               "cross-repo": [entry("a.f", "L1-L2", ["authenticity"])]})
    res = merge_recon_shards(run)
    idx = yaml.safe_load((run / "00-context/code-evidence-index.yaml").read_text())["code_evidence_index"]
    assert res.duplicates_collapsed == 1 and [e["apd_relevance"] for e in idx["entries"]] == [["integrity", "authenticity"]]

def test_missing_shard_projects_are_not_analyzed(tmp_path):
    run = shard_run(tmp_path, {"primary-1": [entry("a.f", "L1-L2", ["integrity"])]}, cfg=HA_CFG)
    res = merge_recon_shards(run)
    c4 = yaml.safe_load((run / "00-context/c4-recon.yaml").read_text())
    states = {c["repo"]: c["analysis_state"] for c in c4["containers"]}
    assert "dependency-1" in res.shards_missing and states["home-assistant-repos-supervisor"] == "not_analyzed"
    assert "home-assistant-repos-supervisor" in (run / "00-context/code-architecture-brief.md").read_text().split("## Not analyzed", 1)[1]

def test_invalid_shard_is_reported_not_merged(tmp_path): ...    # shard missing `entries` -> shards_invalid, its projects not_analyzed
def test_no_shards_is_noop(tmp_path): ...                       # merge returns None; existing code-evidence-index.yaml byte-identical
def test_merge_skipped_when_shards_unchanged(tmp_path): ...     # merge, then canonicalize twice -> second merge returns None, index bytes unchanged
def test_canonicalize_merges_then_mints(tmp_path):
    run = shard_run(tmp_path, {"single": [entry("a.f", "L1-L2", ["integrity"])]})
    assert CliRunner().invoke(main, ["canonicalize", str(run)]).exit_code == 0
    idx = yaml.safe_load((run / "00-context/code-evidence-index.yaml").read_text())["code_evidence_index"]
    assert re.fullmatch(r"cev-[0-9a-f]{8}", idx["entries"][0]["id"])
```

`shard_run(tmp_path, shards, cfg=None)` writes `.apd-run.yaml` (`cfg`, default `{"run_id": "r", "domains": ["pbm"], "cbm_project": "a"}`) and one schema-valid shard file per key; `entry(qualified_name, line_range, apd_relevance, repo="a")` builds an id-less entry. The merge merges every shard file present; the expected shard set from `recon_shards(cfg)` only decides what is missing.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_code_recon_merge.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.code_recon`)

- [ ] **Step 3: Implement** — validate each shard with the new schema (entry shape `$ref`s `code-evidence-index.schema.json#/$defs/entry` minus `id`: copy the properties, drop `id` from `required`); call `merge_recon_shards(run_dir)` as the first statement of `canonicalize_run`, before WS1's `_mint_code_evidence_ids`; `merge-report.yaml` records `shard_sha256: {<file>: <hex>}`. Docs: schema-evolution entry, field-register row (`code-evidence-index.yaml` assembly → `code_recon.merge.merge_recon_shards`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet tests docs
git commit -m "feat(code-recon): partition repos into shards and merge shard files in canonicalize"
```

### Task 14: Code-recon fan-out

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js` (code-recon phase, `phase('code-recon')`, ≈ 488–515; add `reconShards(a)` and `RECON_SHARD_SIZE` near the helpers `isErr` and `bailIfInterrupted`, ≈ 340–359), `tools/apd_gauntlet/plan_run.py:79-93`, `tools/apd_gauntlet/runner/flow.py` (`code-recon`), `tools/apd_gauntlet/runner/instructions.py` (`apd-code-recon:shard`, `apd-code-recon:cross-repo`; `instruction()` accepts `shard_id` and `projects`), `tools/apd_gauntlet/resume_plan.py` (`code-recon` row expanded per shard in `build_resume_plan`), `tests/test_cli_resume_plan.py`, `.claude/agents/apd-code-recon.md` (Outputs, Step 6b, Step 7, a new "## Shard mode" section), `docs/running-the-gauntlet.md` (§"Multi-repo systems", line 153), `docs/architecture.md`, CHANGELOG
- Test: `tests/test_workflow_apd_gauntlet.py`, `tests/test_workflow_dispatch_trace.py`, `tests/test_cli_plan_run.py:176-186`, `tests/runner/test_flow_pre_synthesis.py`, `tests/runner/test_flow_parity.py`, `tests/test_lint_agent_apd_code_recon.py`, `tests/test_workflow_runner_awaits.py`

**Interfaces:**

- Consumes: Task 13 `recon_shards`, `RECON_SHARD_SIZE`; R1 `resume-plan <run-dir> --json`.
- Consumes also: WS1's `canonicalize-code-evidence` step (inside the code-recon branch, after the halt check), which now runs the merge before minting; WS1's `ResumeStep`, `RESUMABLE_STEPS`, `build_resume_plan`.
- Produces: LLM labels `code-recon-<shard_id>` and `code-recon-cross-repo` (only when `repos` has two or more entries); no new CLI label.

**Index coverage (consolidated plan task N21, warning and edges; its coverage capture is in Task 13):**

- [ ] The zero-entry warning in `validate.py` (the `declared repo '<name>' has zero attributed entries` message) skips repos marked `not_analyzed` and states their reason; otherwise it reads "agent coverage gap or partial index (see `repos[].coverage`)".
- [ ] Code recon reads `CROSS_GRPC_CALLS`, `CROSS_GRAPHQL_CALLS` and `CROSS_TRPC_CALLS` edges in addition to today's three.
- [ ] Tests: `test_zero_entry_warning_skips_not_analyzed`. Measure: on the Home Assistant example the zero-entry warnings fall below 14 of 23 after a rerun.

- [ ] **Step 1: Write the failing tests**

```python
def test_recon_shard_size_matches_python():                     # tests/test_workflow_apd_gauntlet.py
    src = _text()
    assert f"const RECON_SHARD_SIZE = {RECON_SHARD_SIZE};" in src
    for frag in ("'primary-'", "'dependency-'", "'peer-'", "'single'", "'code-recon-' + s.id", "'code-recon-cross-repo'"):
        assert frag in src

def test_code_recon_shards_run_in_parallel_then_merge():
    phase = _text().split("phase('code-recon')", 1)[1].split("phase('threat-model-author')", 1)[0]
    assert phase.index("parallel(") < phase.index("label: 'canonicalize-code-evidence'")
    assert "00-context/code-recon/" in phase and "throw new Error" in phase

def test_trace_single_shard():                                   # tests/test_workflow_dispatch_trace.py
    L = [d["label"] for d in trace(HA_SHAPED)]
    assert L.index("code-recon-single") < L.index("canonicalize-code-evidence") and "code-recon" not in L
    repos = [{"cbm_project": f"p{i}", "role": "dependency"} for i in range(8)]
    L2 = [d["label"] for d in trace({**HA_SHAPED, "repos": repos})]
    assert [l for l in L2 if l.startswith("code-recon-")] == ["code-recon-dependency-1", "code-recon-dependency-2", "code-recon-cross-repo"]

def test_plan_run_code_recon_rows(tmp_path):                     # tests/test_cli_plan_run.py
    cfg = dict(FULL_CFG, repos=HA_CFG["repos"])
    recon = [s for s in _plan(tmp_path, cfg) if s["phase"] == "code-recon"]
    assert [s["ref"] for s in recon if s["kind"] == "AGENT"] == ["apd-code-recon"] * 6
    assert recon[0]["outputs"].startswith("00-context/code-recon/primary-1.yaml") and "cross-repo" in recon[0]["outputs"]

def test_runner_fans_out(tmp_path):                              # tests/runner/test_flow_pre_synthesis.py
    r = scenario(tmp_path, cfg={"code_recon": "enabled", "repos": HA_CFG["repos"]}, cbm=True)
    asyncio.run(r.runner.run(stop_after="code-recon"))
    assert {l for l in r.agent_labels if l.startswith("code-recon-")} == \
        {f"code-recon-{s.shard_id}" for s in recon_shards(HA_CFG)} | {"code-recon-cross-repo"}

def test_shard_error_halts_when_enabled(tmp_path): ...           # one shard "error" under enabled -> "failed"; under auto -> continues

def test_resume_plan_lists_shard_labels(tmp_path):              # tests/test_cli_plan_run.py (uses _write_run and FULL_CFG)
    run = _write_run(tmp_path, dict(FULL_CFG, repos=HA_CFG["repos"]))
    steps = json.loads(CliRunner().invoke(main, ["resume-plan", str(run), "--json"]).output)["steps"]
    assert {"code-recon-primary-1", "code-recon-cross-repo"} <= {s["label"] for s in steps}
```

`HA_CFG` is loaded as in Task 13. Keep `test_plan_run_code_recon_step_mentions_cross_repo` passing: the first recon row's outputs include "cross-repo". Extend `tests/test_lint_agent_apd_code_recon.py` with `test_agent_documents_shard_mode` (`"## Shard mode"`, `00-context/code-recon/<shard>.yaml`, "emit no `id`"). In `tests/test_workflow_runner_awaits.py`, the shard labels (`code-recon-<id>`, plus `code-recon-cross-repo` with two or more repos) replace `code-recon` in `EXPECTED_GREEN_LABELS` per `recon_shards` for the harness `ARGS`; the shard group joins the listed parallel groups, and `LARGEST_PARALLEL_GROUP` rises when a test drives more than three shards (register A15.25).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/test_lint_agent_apd_code_recon.py tests/runner -k "recon or shard or resume or labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- `reconShards(a)` is a pure-JS mirror of `recon_shards` returning `[{id, projects}]`. The phase body: `const rs = await parallel(shards.map(...))` of `llmStep('apd-code-recon', 'Run code reconnaissance for shard ' + s.id + ' (CBM projects: ' + s.projects.join(', ') + '); write ONLY 00-context/code-recon/' + s.id + '.yaml per schemas/code-recon-shard.schema.json. Python merges the shards into code-evidence-index.yaml, c4-recon.yaml and code-architecture-brief.md.', { phase: 'code-recon', label: 'code-recon-' + s.id })`; then, with two or more repos, the cross-repo `await llmStep(…)` (instruction: run only Step 6b's cross-repo request across every declared project and write `00-context/code-recon/cross-repo.yaml`); then the `code_recon === 'enabled'` halt when any shard receipt `isErr`; then WS1's `canonicalize-code-evidence` step, unchanged.
- `resume_plan.py`: `build_resume_plan` reads `.apd-run.yaml` and replaces the static `code-recon` row with one `ResumeStep(f"code-recon-{s.shard_id}", ((f"00-context/code-recon/{s.shard_id}.yaml",),))` per `recon_shards(cfg)` shard, plus `code-recon-cross-repo` (`cross-repo.yaml`) with two or more repos; update the label-list assertion in `tests/test_cli_resume_plan.py`.
- Runner and `plan_run.py` mirror the shards and the cross-repo step; `plan_run` keeps one row per shard with outputs `00-context/code-recon/<id>.yaml (per-role shards + a cross-repo pass when repos[] declared)`.
- Agent: "## Shard mode" (one shard per dispatch, its projects only, write only the shard file, entries carry no `id`, `not_analyzed` lists projects it could not index or read); Outputs and Step 7 point at the shard file; the C4 section keeps its rules and says Python assembles `00-context/c4-recon.yaml` (`generated_by: code_recon`) from the shards. Sync the bundle.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .claude tools/apd_gauntlet tests docs CHANGELOG.md
git commit -m "feat(code-recon): fan out one recon agent per repo group and merge in Python"
```

- [ ] **Step 6: Operator gate (OG, tag `t14`)**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t14 --gates eval/gates.yaml --strict` for each of the four run ids (the HA example exercises the fan-out).
Expected: exit 0 for all four; `usage` shows the code-recon phase's largest single-agent context well below baseline; `00-context/code-recon/merge-report.yaml` lists no missing shard.

### Task 15: Remove the deprecated `apd-orchestrator` (conditional)

WS3 Task 5 deletes the agent, its two content tests and every reference, and adds `tests/test_plugin_footprint.py::test_orchestrator_removed`. This task only makes sure nothing survived. Not behaviour-changing (the workflow never dispatches it); no operator gate.

**Files (only when something survived):** `.claude/agents/apd-orchestrator.md`, `tools/apd_gauntlet/data/claude/agents/apd-orchestrator.md`, `tests/test_orchestrator_deprecation.py`, `tests/test_orchestrator_topology.py` (delete); `.claude-plugin/plugin.json`, `tools/apd_gauntlet/lint_agents.py:14` (`RECEIPT_EXEMPT = {"apd-synthesizer"}`), `tests/test_lint_agents_receipt.py:22-26`, `tests/test_doc_domain_pack_authoring.py:20-30`, `docs/architecture.md:45`, `.claude/skills/apd-evidence-discipline/SKILL.md:16` (modify, as WS3 Task 5 specifies); CHANGELOG "Removed".

- [ ] **Step 1: Check what survived**

Run: `test -f .claude/agents/apd-orchestrator.md && echo present || echo absent; grep -rln "apd-orchestrator" .claude/agents .claude-plugin .claude/skills tools/apd_gauntlet/lint_agents.py tools/apd_gauntlet/data/claude tests/test_lint_agents_receipt.py tests/test_doc_domain_pack_authoring.py docs/architecture.md`
Expected: `absent` and no file listed → mark this task done with no commit. Otherwise continue. The mentions in the workflow header comment, its `meta.description` and `tests/test_workflow_apd_gauntlet.py` are intended, so the grep leaves them out (register A10.6).

- [ ] **Step 2: Write the failing test** — if `tests/test_plugin_footprint.py` lacks it, add WS3's `test_orchestrator_removed` (the file is absent and no `plugin.json` agent path names it) plus `assert "apd-orchestrator" not in lint_agents.RECEIPT_EXEMPT`.
- [ ] **Step 3: Run** `pytest tests/test_plugin_footprint.py -v` — Expected: FAIL on the surviving reference.
- [ ] **Step 4: Delete or edit each surviving item from the file list; sync the bundle; run** `pytest -q && apd-gauntlet lint-agents --agent-dir .claude/agents/ && markdownlint-cli2 "docs/**/*.md" ".claude/**/*.md" "!docs/superpowers/plans/**"` — Expected: PASS, including `tests/test_plugin_manifest.py::test_agents_array_matches_dir`.
- [ ] **Step 5: Commit** — `git add -A .claude .claude-plugin tools/apd_gauntlet tests docs CHANGELOG.md && git commit -m "chore: remove leftover apd-orchestrator references"`

### Task 15a: Model and effort provenance in `usage`

(Consolidated plan task N10.)

**Files:** Modify `tools/apd_gauntlet/measure/usage.py`, `tools/apd_gauntlet/cli.py` (`usage`), `measure/compare.py`, `tests/fixtures/otel/*`; Create `tests/test_measure_usage_models.py`.

**Interfaces:** `ApiRequest` gains `model: str` and `effort: str | None`; `usage.yaml` `by_agent.<agent>` gains `models: {<model id>: <requests>}` and `efforts: {<level>: <requests>}`; CLI `usage <run-dir> --otel <file> --expect-model <agent-glob>=<model-prefix>` (repeatable) exits 1 and prints `expect-model: <agent> ran <model>, expected <prefix>*` on any mismatch; `compare-runs` prints the per-agent model mix of both sides.

- [ ] **Step 1:** Tests: `test_by_agent_records_models_and_effort` (fixture with two models for one agent), `test_expect_model_fails_on_mismatch` (`apd-confidentiality=claude-sonnet` against an Opus fixture → exit 1, message as above), `test_expect_model_passes`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Pass; QG. Commit: `feat(measure): record and assert per-agent model and effort`.

### Task 15b: First-pass tracking for every LLM step

(Consolidated plan task N11.)

**Files:** the workflow (a named async helper that awaits `llmStep` and records the result, listed in `ASYNC_HELPERS` and `CALLS`; `llmStep` stays synchronous, A15.21), `runner/flow.py`, `data/schemas/run-attempts.schema.json`, `measure/attempts.py`, `measure/compare.py`; Create `tests/test_attempts_llm_steps.py`.

**Interfaces:** `attempts.yaml` gains optional `llm_first_pass_invalid: {<label>: int}`, `repairs: {<label>: int}` (agent repair dispatches) and `python_repairs: int` (fields canonicalize normalized, from N13); `compare-runs` reports `llm_first_pass_invalid_delta` per step and `python_repairs_delta`; old attempt files still load.

- [ ] **Step 1:** Tests: `test_non_lens_first_pass_recorded` (trace with a failing TM-evaluator output), runner mirror test, `test_attempts_v1_without_new_keys_loads`.
- [ ] **Step 2–4:** Fail, implement in both channels (parity), pass, QG. Commit: `feat(measure): first-pass validity for every LLM step`.

### Task 15c: Artifact-level metrics and Wave 3 gates

(Consolidated plan task N12.)

**Files:** `measure/compare.py`, `measure/gates.py`; Create `eval/gates-wave3.yaml`, `tests/test_measure_context_metrics.py`.

**Interfaces:** new comparison metrics `tm_grounded_ratio_delta_pts`, `cev_entries_ratio`, `inventory_assets_ratio`, `tm_supplied_entry_jaccard`, `tmeval_contradictions_delta`, `apath_findings_ratio`, `headline_overlap_pct`; `eval/gates-wave3.yaml` holds the A10.11 thresholds (for example `inventory_assets_ratio ge 0.9`, `tm_supplied_entry_jaccard ge 0.95`, `headline_overlap_pct ge 80`).

- [ ] **Step 1:** Tests on the Home Assistant example versus a mutated copy (drop 10 % of assets, remove one contradiction): each metric moves as expected and `compare-runs --gates eval/gates-wave3.yaml` exits 1.
- [ ] **Step 2–4:** Fail, implement, pass, QG. Commit: `feat(measure): artifact-level metrics for model tiering`.

### Task 15d: Canonicalize fills derivable lens fields

(Consolidated plan task N13.)

**Files:** `tools/apd_gauntlet/canonicalize.py`; Create `tests/test_canonicalize_lens_fields.py`.

**Interfaces:** for lens files only, fill an absent `agent`, `apd_goal` or `apd_tier` from the file path (never overwrite, so a relabel stays an error through `check_lens_consistency`); case-fold `severity`, `confidence`, `disposition`, `maturity`, `posture`; map goal names in `related_concerns` to ids; `CanonicalizeResult.fields_normalized: int`, recorded by N11 as `attempts.python_repairs`.

- [ ] **Step 1:** Tests: `test_absent_goal_filled_from_path`, `test_present_wrong_goal_not_overwritten`, `test_enum_case_folded`, `test_related_concerns_names_mapped`, `test_fields_normalized_counted`.
- [ ] **Step 2–4:** Fail, implement, pass, QG; SCP. Commit: `feat(canonicalize): fill derivable lens fields and fold enum case`.

### Task 16: Tier-1 lenses to Sonnet

WS3 already set every agent's `effort` to the audit's Wave 3 value and pinned `(model, effort)` per agent in `tests/test_agent_effort.py` `EXPECTED`. Wave 3 tasks change `model` only and edit those `EXPECTED` rows.

**Files:**

- Modify: `.claude/agents/apd-{confidentiality,integrity,availability}.md` (frontmatter `model`), their bundled copies, `tests/test_agent_effort.py` (`EXPECTED`), `tests/runner/test_agents.py` (`test_load_spec_comma_tools`, `test_model_precedence`: the assertions that pin these agents' previous model), CHANGELOG

**Interfaces:**

- Consumes: WS3 `EXPECTED: dict[str, tuple[str | None, str]]` and `test_every_agent_has_expected_model_and_effort`; LA2 `load_agent_spec`, `resolve_model`.

- [ ] **Step 1: Write the failing test** — in `EXPECTED`, after the lens comprehension, set:

```python
EXPECTED |= {"apd-confidentiality": ("sonnet", "medium"), "apd-integrity": ("sonnet", "medium"),
             "apd-availability": ("sonnet", "medium")}        # WS5 Task 16
```

In `tests/runner/test_agents.py`, `test_load_spec_comma_tools` asserts `s.model == "sonnet"` for `apd-confidentiality`, and `test_model_precedence` asserts `resolve_model(load_agent_spec(ws, "apd-integrity"), UserConfig()) == "sonnet"`. `test_model_precedence` keeps a default-path case through a fixture agent without `model` (register A10.8).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_effort.py tests/runner/test_agents.py -v`
Expected: FAIL (model is unset)

- [ ] **Step 3: Set `model: sonnet` in the three files; sync the bundle**

- [ ] **Step 4: Run tests**

Run: `pytest -q && apd-gauntlet lint-agents --agent-dir .claude/agents/`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .claude/agents tools/apd_gauntlet/data/claude tests CHANGELOG.md
git commit -m "perf(agents): run tier-1 lenses on Sonnet"
```

- [ ] **Step 6: Operator gate (OG, tag `t16`) with revert criterion**

Run: `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t16 --gates eval/gates.yaml --strict` for each of the four run ids.
Expected: exit 0 for all four; `usage` shows tier-1 lens cost below the Task 14 runs. Revert criterion: any comparison exits 1, or an extra criterion (register A10.11: `usage --expect-model` fails; per-lens first-pass invalid, lens retries or Python repairs above `<prev>`; tier cost not lower than `<prev>`) → apply the Wave 3 revert rule to the three lenses, then continue with Task 17.

### Task 17: Tier-2 lenses to Sonnet

**Files:** Modify `.claude/agents/apd-{distributed,resilient,ephemeral}.md`, bundled copies, `tests/test_agent_effort.py`, CHANGELOG.

- [ ] **Step 1: Add the failing rows** — `EXPECTED |= {"apd-distributed": ("sonnet", "medium"), "apd-resilient": ("sonnet", "medium"), "apd-ephemeral": ("sonnet", "medium")}  # WS5 Task 17`.
- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py -v` — Expected: FAIL on the three agents.
- [ ] **Step 3: Set `model: sonnet` in the three files; sync the bundle.**
- [ ] **Step 4: Run** `pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** — `git add .claude/agents tools/apd_gauntlet/data/claude tests CHANGELOG.md && git commit -m "perf(agents): run tier-2 lenses on Sonnet"`
- [ ] **Step 6: Operator gate (OG, tag `t17`) with revert criterion** — `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t17 --gates eval/gates.yaml --strict` for each of the four run ids. Expected: exit 0 for all four. Any exit 1, or an extra criterion (register A10.11: Task 16's, plus tier-2 cross-references to tier-1 ids below 90 % of `<prev>`) → apply the Wave 3 revert rule, then continue with Task 18.

### Task 18: Tier-3 lenses to Sonnet

**Files:** Modify `.claude/agents/apd-{authenticity,non-repudiation,immutability}.md`, bundled copies, `tests/test_agent_effort.py`, CHANGELOG.

- [ ] **Step 1: Add the failing rows** — the three tier-3 lenses → `("sonnet", "medium")` under `# WS5 Task 18`.
- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py -v` — Expected: FAIL on the three agents.
- [ ] **Step 3: Set `model: sonnet`; sync the bundle.**
- [ ] **Step 4: Run** `pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** — same `git add` as Task 17; `git commit -m "perf(agents): run tier-3 lenses on Sonnet"`.
- [ ] **Step 6: Operator gate (OG, tag `t18`) with revert criterion** — `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t18 --gates eval/gates.yaml --strict` for each of the four run ids. Expected: exit 0 for all four. Any exit 1, or an extra criterion (register A10.11: as Task 17) → apply the Wave 3 revert rule, then continue with Task 19.

### Task 19: Context agents to Sonnet

**Files:** Modify `.claude/agents/apd-intake.md`, `apd-code-recon.md`, `apd-threat-model-recon.md`, bundled copies, `tests/test_agent_effort.py`, CHANGELOG.

- [ ] **Step 1: Add the failing rows** — `"apd-intake": ("sonnet", "medium")`, `"apd-code-recon": ("sonnet", "medium")`, `"apd-threat-model-recon": ("sonnet", "low")` under `# WS5 Task 19`.
- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py -v` — Expected: FAIL on the three agents.
- [ ] **Step 3: Set `model: sonnet`; sync the bundle.**
- [ ] **Step 4: Run** `pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "perf(agents): run intake, code recon and TM recon on Sonnet"`.
- [ ] **Step 6: Operator gate (OG, tag `t19`) with revert criterion** — `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t19 --gates eval/gates.yaml --strict` for each of the four run ids (the claim-event-bus example exercises TM recon; HA exercises the code-recon shards). Expected: exit 0 for all four. Any exit 1, or an extra criterion (register A10.11: `inventory_assets_ratio < 0.9`; `cev_entries_ratio < 0.9` or a new `not_analyzed` project; `tm_supplied_entry_jaccard < 0.95`) → apply the Wave 3 revert rule, then continue with Task 20.

### Task 20: Threat-model author to Sonnet

**Files:** Modify `.claude/agents/apd-threat-model-author.md`, bundled copy, `tests/test_lint_agent_apd_threat_model_author.py:47-49`, `tests/runner/test_agents.py` (`test_model_precedence`), `tests/test_agent_effort.py`, CHANGELOG.

- [ ] **Step 1: Write the failing tests** — row `"apd-threat-model-author": ("sonnet", "medium")`; rename `test_agent_model_is_opus` (lines 47–49) to `test_agent_model_is_sonnet` asserting `meta["model"] == "sonnet"`; `test_model_precedence` asserts the frontmatter value `"sonnet"` and keeps its override case.
- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py tests/test_lint_agent_apd_threat_model_author.py tests/runner/test_agents.py -v` — Expected: FAIL.
- [ ] **Step 3: Set `model: sonnet`; sync the bundle.**
- [ ] **Step 4: Run** `pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "perf(agents): run the threat-model author on Sonnet"`.
- [ ] **Step 6: Operator gate (OG, tag `t20`) with revert criterion** — `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t20 --gates eval/gates.yaml --strict` for each of the four run ids. Expected: exit 0 for all four. Any exit 1, or an extra criterion (register A10.11: `tm_grounded_ratio_delta_pts < −5`; Home Assistant's `tm-f8db6c3a` / `auth-1787eae1` contradiction lost downstream) → apply the Wave 3 revert rule (the author returns to `opus` and the lint test to `test_agent_model_is_opus`), then continue with Task 21.

### Task 21: Tier-4 analyzers to Sonnet

**Files:** Modify `.claude/agents/apd-threat-model-evaluator.md`, `apd-attack-path-analyzer.md`, bundled copies, `tests/test_lint_agent_apd_attack_path_analyzer.py:46-48`, `tests/test_agent_effort.py`, CHANGELOG.

- [ ] **Step 1: Write the failing tests** — rows `"apd-threat-model-evaluator": ("sonnet", "high")`, `"apd-attack-path-analyzer": ("sonnet", "medium")`; rename `test_agent_model_is_opus` (lines 46–48) to `test_agent_model_is_sonnet` asserting `"sonnet"`.
- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py tests/test_lint_agent_apd_attack_path_analyzer.py -v` — Expected: FAIL.
- [ ] **Step 3: Set `model: sonnet` in both files; sync the bundle.**
- [ ] **Step 4: Run** `pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "perf(agents): run the TM evaluator and attack-path analyzer on Sonnet"`.
- [ ] **Step 6: Operator gate (OG, tag `t21`) with revert criterion** — `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t21 --gates eval/gates.yaml --strict` for each of the four run ids. Expected: exit 0 for all four. Any exit 1, or an extra criterion (register A10.11: the `tm-f8db6c3a` / `auth-1787eae1` contradiction missing; `apath_findings_ratio` outside 0.9–1.1) → apply the Wave 3 revert rule (the analyzer's lint test back to `test_agent_model_is_opus`), then continue with Task 22.

### Task 22: Synthesis support agents

**Files:** Modify `.claude/agents/apd-domain-auditor.md`, `apd-synthesizer.md`, bundled copies, `tests/test_agent_effort.py`, CHANGELOG.

- [ ] **Step 1: Add the failing rows** — `"apd-domain-auditor": ("sonnet", "medium")`, `"apd-synthesizer": ("opus", "high")`. The cluster adjudicator and report auditor already match the audit (`("opus", "high")` from WS3) and stay.
- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py -v` — Expected: FAIL on the two agents.
- [ ] **Step 3: Set `model: sonnet` (domain auditor) and `model: opus` (synthesizer); sync the bundle.**
- [ ] **Step 4: Run** `pytest -q` — Expected: PASS (`test_lint_agent_apd_domain_auditor.py::test_frontmatter_fields_present` only requires a `model`).
- [ ] **Step 5: Commit** — `git commit -m "perf(agents): run the domain auditor on Sonnet and pin the synthesizer to Opus"`.
- [ ] **Step 6: Operator gate (OG, tag `t22`) with revert criterion** — run the set with `domain_improvement_capture: true` in each `.apd-run.yaml` (the auditor is opt-in after WS3), then `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t22 --gates eval/gates.yaml --strict` for each of the four run ids. Expected: exit 0 for all four. The synthesizer runs only on fallback, so the set does not exercise its change (accepted per the audit: "Rare, and it runs when something already failed"). Any exit 1, or an extra criterion (register A10.11: improvements file invalid, or count outside ±30 %) → apply the Wave 3 revert rule, then continue with Task 23.

### Task 23: Report writer to Sonnet (last); `model` becomes required

**Files:** Modify `.claude/agents/apd-report-writer.md`, bundled copy, `tests/test_agent_effort.py`, `tools/apd_gauntlet/lint_agents.py` (`lint_agent_file`, beside WS3's `effort` and model-value checks), `tests/test_validate_edge_cases.py::test_lint_agent_missing_name_and_description` (only if it asserts the exact error list), `docs/architecture.md` (a "Models and effort" table), `docs/extending-agents.md` (frontmatter now needs `model`), CHANGELOG.

- [ ] **Step 1: Write the failing tests**

```python
EXPECTED |= {"apd-report-writer": ("sonnet", "medium")}        # WS5 Task 23

def test_every_agent_sets_a_model():
    assert all(model for model, _ in EXPECTED.values())

def test_lint_requires_model(tmp_path):
    a = tmp_path / "apd-x.md"; a.write_text("---\nname: apd-x\ndescription: x\neffort: low\n---\n\n## Final message\n")
    assert any("frontmatter missing 'model'" in e for e in lint_agent_file(a, tmp_path))
```

- [ ] **Step 2: Run** `pytest tests/test_agent_effort.py -v` — Expected: FAIL (writer still `opus`; no `model` rule).
- [ ] **Step 3: Set `model: sonnet` on the writer; in `lint_agent_file` emit `"frontmatter missing 'model'"` when `model` is absent (R5: every agent sets `model` and `effort`); add the "Models and effort" table (agent, model, effort, why, from the audit's Wave 3 table) to `docs/architecture.md`, recording the Opus residue (adjudicator, report auditor, synthesizer) in it (register A10.9); sync the bundle.**
- [ ] **Step 4: Run** `pytest -q && apd-gauntlet lint-agents --agent-dir .claude/agents/ && markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**"` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "perf(agents): run the report writer on Sonnet; require model in agent frontmatter"`.
- [ ] **Step 6: Operator gate (OG, tag `t23`) with revert criterion** — `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-t23 --gates eval/gates.yaml --strict` for each of the four run ids. Expected: exit 0 for all four. Revert criterion (audit: "Opus auditor is the backstop; revert if audit iterations rise"): any exit 1, including the report-audit-iterations gate alone, or an extra criterion (register A10.11: `audit_iterations_delta > 0`; `headline_overlap_pct < 80`) → apply the Wave 3 revert rule to the writer only; the `model` lint rule and `test_every_agent_sets_a_model` stay. The audit-iteration criterion fires only with the `<prev>` comparison under `--strict` (register A10.9).

### Tasks 24–28: Wave 3b and the Opus residue

(Consolidated plan task N16.)

Same shape as WS5 Tasks 16–23 (frontmatter change, `EXPECTED` row in `tests/test_agent_effort.py`, SCP ×3 median with `--expect-model`, revert ladder):

- [ ] T24 `apd-threat-model-recon` → `haiku`/`low`. Extra gate: `tm_supplied_entry_jaccard ≥ 0.95` on claim-event-bus.
- [ ] T25 `apd-domain-auditor` → `haiku`/`medium`. Extra gate: run with `domain_improvement_capture: true`; the improvements file validates and its count is within ±30 % of `<prev>`.
- [ ] T26 (optional) `apd-tier-repair` → `haiku`/`low`. Needs a fault-injection corpus under `eval/local/repair/`; update `tests/test_lint_agent_apd_tier_repair.py`'s model pin.
- [ ] T27 (optional, after `cluster-pairs` is active) `apd-cluster-adjudicator` → `sonnet`/`high`.
- [ ] T28 (optional, last) `apd-report-auditor` → `sonnet`/`high`, with a seeded-defect check: an inserted invented-content line must yield `GATE: fail`.
