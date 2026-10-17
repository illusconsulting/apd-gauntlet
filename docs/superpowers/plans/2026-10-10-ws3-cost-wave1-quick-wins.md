# WS3 Cost Wave 1 (Quick Wins) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut dispatches and always-on context on the 2.0 line. WS3 adds a Bash-only Haiku CLI runner, four composite CLI commands, a narrow tier-repair agent, explicit `effort` on every agent, an opt-in domain auditor, trimmed plugin descriptions and a verbatim-excerpt check that is strict by default. Each change ships behind a measured `compare-runs`.

**Architecture:**

- CLI steps move from a general-purpose agent to `apd-cli-runner`. Its agent body holds the static receipt contract, so each dispatch prompt shrinks to a few lines.
- Four composites (`apd_gauntlet.composite`) run existing commands in-process and write one status line per constituent to stderr. `tier-gate` exits with its `validate` code; the others exit with the first failing constituent's code. The workflow switches to them: WS1's `tierGate` and repair loop, WS2's attempts recording, and `plan-run`.
- WS1's repair dispatch moves to `apd-tier-repair`, which has Read and Edit only and runs on Sonnet at low effort.
- Frontmatter and linters carry the rest: `effort` is required, descriptions are capped, a run-config key opts in to Phase 5h, and WS1's verbatim-excerpt check becomes strict by default. A strict failure at a tier gate goes through the repair loop.

**Tech Stack:** Python 3.10–3.12, click, PyYAML, jsonschema; the Workflow-primitive JS runner; Node 22 (`node:vm`) for a test-only dispatch-trace harness; pytest, ruff, mypy (strict), markdownlint-cli2.

**Spec:**

- `docs/superpowers/plans/2026-10-10-program-master-plan.md`: Registry R1 (`prepare-run`, `tier-gate`, `post-tier4`, `closeout`), R3, R4 (`domain_improvement_capture`), R5; Task 4 Step 2.
- Cost and token audit (Claude Doc "APD Gauntlet cost and token audit", 2026-10-10): "Wave 1: quick wins", plus the Effort column of the "Wave 3: model and effort tiering" table.
- Coordinator decisions of 2026-10-11:
  - the `apd-tier-repair` agent;
  - `tier-gate` canonicalizes the whole run;
  - the orchestrator is deleted;
  - the R5 rewording;
  - the comparison-baseline policy.
- Interfaces WS3 builds on:
  - `docs/superpowers/plans/2026-10-10-ws1-defect-fixes-1.7.1.md`, as revised:
    - Task 1 `resume-plan`; Task 2 `pyStep` `resumePlan`;
    - Task 3 `tierGate`, `repairTierGate`, `errorsFromJson` and `repair.md`;
    - Task 9 context canonicalize steps;
    - Task 11 `check_excerpts_verbatim` and `--strict-excerpts`, scoped to `inputs/` and run at tier gates;
    - guard removal on `intake-schema-gate`, `validate-full-prephase5` and `validate-final`.
  - `docs/superpowers/plans/2026-10-10-ws2-measurement-and-evaluation.md`: Task 3 `summarize --record-attempts`, Task 4 `usage` and `AGENT_PHASES`, Task 6 `compare-runs`, Task 7 workflow `attempts`.

**Amended 2026-10-17** per the amendments register (A8.9, A9.2, A9.8, A9.9, A9.10, A9.11, A9.12, A9.13, A9.14, A9.15, A9.16, A9.17, A9.18, A9.20, A15.12, A15.15, A15.21, A15.23, A15.24, A15.25, A15.28).

## Global Constraints

- Lands on `next` after WS1 has merged forward and WS2 has merged. One PR per task. PRs that edit `.claude/workflows/apd-gauntlet.js` merge one at a time.
- R5, verbatim: "New agent `apd-cli-runner` (WS3): tools `Bash` only, `model: haiku`, `effort: low`. `pyStep()` dispatches with `agentType: 'apd-cli-runner'`."
- R5, as reworded by the coordinator: every agent sets `effort` after WS3, and every agent sets `model` after WS5 Task 23. WS3 keeps today's models and leaves `model` absent where it is absent today. `tests/test_lint_agent_apd_attack_path_analyzer.py` and `tests/test_lint_agent_apd_threat_model_author.py` keep pinning `model: opus`.
- New agent `apd-tier-repair` (coordinator decision): tools `Read` and `Edit` only, `model: sonnet`, `effort: low`, usage phase `canonicalize`.
- R1, verbatim:
  - `prepare-run <run-dir> [--domain …]`: "Composite of scaffold `validate`, `build-domain-skill` and `validate-domain`, keeping their exit codes".
  - `tier-gate <run-dir> --tier <dir>`: "canonicalize the tier, then `validate --tier`. Exit 0 clean, 1 schema errors". Per the coordinator, it canonicalizes the whole run.
  - `post-tier4 <run-dir>`: "`assemble-c4`, tmeval canonicalize, `rollup`".
  - `closeout <run-dir>`: "dimpr canonicalize, `summarize`, final `validate`".
- R3, verbatim: "WS3 renames no phase. The `setup` phase runs `prepare-run`." `meta.phases` stays as WS1 and WS2 leave it.
- R4: `domain_improvement_capture` is optional, boolean, default `false`.
- Effort values come from the audit's Wave 3 Effort column, with the tier-repair row from the coordinator:

  | Agent | Effort |
  |---|---|
  | CLI runner | `low` |
  | 9 lenses | `medium` |
  | intake | `medium` |
  | code recon | `medium` |
  | TM author | `medium` |
  | TM recon | `low` |
  | TM evaluator | `high` |
  | attack-path analyzer | `medium` |
  | cluster adjudicator | `high` |
  | report writer | `medium` |
  | report auditor | `high` |
  | domain auditor | `medium` |
  | synthesizer | `high` |
  | tier repair | `low` |

- Claude Code subagent frontmatter (`code.claude.com/docs/en/sub-agents`):
  - `effort` is one of `low`, `medium`, `high`, `xhigh`, `max`.
  - `model` is `sonnet`, `opus`, `haiku`, `fable`, `inherit` or a full model id.
  - An omitted `model` differs from `inherit` when `CLAUDE_CODE_SUBAGENT_MODEL` is set.
- WS1 contracts kept unchanged:
  - `pyStep` options `resumePlan` and `errorsFromJson`;
  - `tierGate` (`alwaysRun`, `--json`) and `repairTierGate`'s `agent(repairPrompt(…), …)` call;
  - the repair template;
  - `RESUMABLE_STEPS` (agent steps only), so WS3 changes no `resume-plan` entry;
  - the excerpt check's `inputs/` scope, `...`/`…` fragments and tier-gate placement;
  - the message `evidence[{i}].excerpt not found verbatim in artifact '{artifact}'`;
  - the guard-free `intake-schema-gate`, `validate-full-prephase5` and `validate-final`.
- WS2 contracts kept unchanged:
  - workflow `attempts` recording, with `closeout` carrying `--record-attempts`;
  - `usage.yaml` `by_agent`, `by_phase`, `totals`;
  - `compare-runs BASELINE CANDIDATE`, which resolves `-r1`/`-r2` and exits 0 on `pass` or `pass_with_gaps`.
- Comparison baseline (coordinator decision):
  - Each behaviour-changing task gates against the previous accepted state (`<prev>` below). That is the last tagged pre-release or the prior PR group's runs. For Task 1, it is the last accepted runs on `next` before WS3; for later tasks, the previous behaviour-changing WS3 task's runs.
  - The milestone exit (Task 9) gates against the 1.7.1 baseline.
  - From Task 7 on, the private PBM run sets `domain_improvement_capture: true` in both baseline and candidate. Before Task 7, capture always runs and the key would fail `validate-run-config`. Each task from Task 7 on records one extra candidate PBM run with the key off, to measure the saving.
- Each behaviour-changing task ends with master plan Task 4 Step 2 against `<prev>`. Run the master plan Task 1 set twice, then `apd-gauntlet compare-runs <prev> <candidate> --gates eval/gates.yaml` must exit 0, and the usage cost must be at or below `<prev>`. Because `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started, every run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or starts a new session (register A15.12).
- CI never touches the network (ADR-0017). The Node harness tests skip when `node` is absent, as `test_c4_solve_routes_node_oracle` does.
- Quality gates on every PR: `ruff check tools/ tests/`, `mypy tools/`, `pytest` (coverage `fail_under = 85`), `apd-gauntlet lint-agents`, `apd-gauntlet lint-skills`, and `markdownlint-cli2` on the CI globs.
- CHANGELOG entries go under ``## Unreleased — 2.0 line (`next`)``.
- Line numbers below are at `856ea96` unless a WS1 or WS2 function is named. Locate each edit by the quoted anchor, because WS1 and WS2 shift the workflow.

## Review Focus

- **Shell metacharacters in `run_id`, `domains` or `framework_version`.** These values reach the Bash command line of a Bash-only agent, so the workflow must refuse before the first dispatch. Pinned by `test_trace_rejects_shell_metacharacters` (Task 1).
- **One constituent of a composite fails.** If `assemble-c4` raises, `rollup` still runs and the failure is named. The rollup retry and the synthesizer last resort fire only when `rollup` itself failed. A `canonicalize` failure under a clean `validate` does not fail `tier-gate`. Pinned by `test_post_tier4_assemble_failure_still_runs_rollup` and `test_tier_gate_exit_is_the_validate_gate` (Task 2), and `test_rollup_fallback_keys_on_rollup_step` (Task 3).
- **A tier gate rejects a lens file.** The narrow `apd-tier-repair` agent, with Read and Edit only, fixes that one file, and the re-gate runs through `tier-gate`, which canonicalizes again. Neither a general-purpose agent nor a standalone `canonicalize` step remains in the loop. Pinned by `test_repair_dispatches_tier_repair_agent` (Task 4) and `test_repair_loop_regates_through_tier_gate` (Task 3).
- **`domain_improvement_capture` absent, false, true, or the string `"true"`.** Absent or false skips Phase 5h with skip sentinels and keeps both phases declared. `true` runs it. A non-boolean fails both the schema and the workflow. Pinned by `test_domain_capture_default_off_and_opt_in` and `test_domain_capture_must_be_boolean` (Task 7).
- **A paraphrased `inputs/` excerpt on `next`, in a new run or a 1.7-era one.**
  - In a new run, it is an error by default, and at a tier gate a JSON error the repair loop receives, rather than a hard halt later.
  - For old runs, `--no-strict-excerpts` turns it back into a warning.
  - The committed examples still validate.

  Pinned by `test_paraphrase_is_an_error_by_default_on_2_0`, `test_tier_gate_is_strict_by_default_and_honours_the_escape_hatch`, `test_no_strict_excerpts_downgrades_to_warning` and `test_committed_examples_validate_strict` (Task 8).

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `.claude/agents/apd-cli-runner.md` | Bash-only Haiku agent that runs one `apd-gauntlet` command and returns its receipt | Create (1), modify (3) |
| `.claude/agents/apd-tier-repair.md` (WS1) | Read/Edit-only Sonnet agent that fixes one rejected record file; WS3 adds `effort: low` | Modify (4) |
| `tests/js/workflow_dispatch_trace.mjs` | Test-only harness: runs the workflow under stub Workflow globals and prints every dispatch | Create (1) |
| `tests/test_workflow_dispatch_trace.py` | Dispatch counts, labels, commands, guards, failure branches and the plan-run sequence, measured through the harness | Create (1), extend (3, 4, 7) |
| `tests/test_agent_apd_cli_runner.py` | Frontmatter and body contract of the CLI runner | Create (1), extend (3) |
| `tests/test_lint_agent_apd_tier_repair.py` (WS1) | Frontmatter of the tier-repair agent (`effort: low`) and its repair template | Modify (4) |
| `.claude/workflows/apd-gauntlet.js` | `pyStep` target, identifier checks, composite dispatches, Phase 5h gate | Modify (1, 3, 7) |
| `.claude-plugin/plugin.json` | Register `apd-cli-runner`; drop `apd-orchestrator` | Modify (1, 5) |
| `tools/apd_gauntlet/measure/usage.py` (WS2) | `AGENT_PHASES` entry for `apd-cli-runner` | Modify (1) |
| `tools/apd_gauntlet/composite.py` | `SubStep`, in-process `invoke`, `run_composite`, step builders | Create (2), modify (8) |
| `tools/apd_gauntlet/cli.py` | `prepare-run`, `tier-gate`, `post-tier4`, `closeout`; the strict-excerpt default | Modify (2, 8) |
| `tests/test_cli_composites.py` | Composite order, exit codes, status lines, JSON mode | Create (2) |
| `tools/apd_gauntlet/plan_run.py` | Composite rows, an `assemble-inventory` row, the Phase 5h gate and note | Modify (3, 7) |
| `tools/apd_gauntlet/lint_agents.py`, `tools/apd_gauntlet/lint_skills.py` | Description caps; `effort` required; `model` value check | Modify (5, 6) |
| `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` (not `apd-domain`) | One-line descriptions; `effort` | Modify (5, 6) |
| `.claude/agents/apd-orchestrator.md`, `tests/test_orchestrator_deprecation.py`, `tests/test_orchestrator_topology.py` | Retired shim and its two content tests | Delete (5) |
| `tests/test_plugin_footprint.py` | Always-on description budget; the orchestrator is gone | Create (5) |
| `tests/test_agent_effort.py` | Per-agent `(model, effort)` table | Create (6) |
| `tools/apd_gauntlet/data/schemas/run-config.schema.json` (also reached through the `schemas` symlink) | `domain_improvement_capture` | Modify (7) |
| `tools/apd_gauntlet/init_run.py` | Commented opt-in line in the scaffolded `.apd-run.yaml` | Modify (7) |
| `tests/test_validate_excerpts.py` (WS1) | Default flipped to strict; escape hatch; tier-gate pass-through | Modify (8) |
| `docs/architecture.md`, `docs/running-the-gauntlet.md`, `docs/improving-domain-packs.md`, `docs/extending-agents.md`, `docs/schema-evolution.md`, `CHANGELOG.md` | Docs, each in the task that changes the behaviour | Modify (1–9) |

`tools/apd_gauntlet/runner/flow.py` does not exist when WS3 runs. LA2 creates it after WS3 and adopts the composites and both agents, per master plan §A2.

## Dispatch count, before and after

The Task 1 harness reproduces the audit's 42 dispatches against `856ea96` with an HA-shaped config (`code_recon: enabled`, `crown_jewels` set, no `threat_model`). The "WS1 + WS2 base" column follows those plans:

- WS1 adds a `resume-plan` read, two context `canonicalize` steps (Task 9), and one `canonicalize` call site inside `regate()`, which `repairTierGate` calls.
- WS1 removes the guard from `intake-schema-gate`, `validate-full-prephase5` and `validate-final`, and from every agent prompt.
- WS2 makes `summarize` `alwaysRun`.
- Repair dispatches occur only when a tier gate fails, so no clean-run column includes them.

| | `856ea96` | WS1 + WS2 base | After Task 3 | After Task 7, default | After Task 7, capture `true` |
|---|---|---|---|---|---|
| `pyStep(` call sites | 28 | 32 | 24 | 24 | 24 |
| CLI dispatches, clean run | 24 | 27 | 18 | 17 | 18 |
| … of which carry guard text | 15 | 9 | 6 | 5 | 6 |
| LLM dispatches, clean run | 18 | 18 | 18 | 17 | 18 |
| … of which carry guard text | 18 | 0 | 0 | 0 | 0 |
| Total dispatches | 42 | 45 | 36 | 34 | 36 |

The composites remove 9 CLI dispatches from every clean run, as the audit's 24 → 15 does. They also remove the guard text from `validate-scaffold`, `validate-domain` and `rollup`. The R4 default removes one more CLI dispatch and one LLM dispatch.

After Task 1, every CLI dispatch goes to `apd-cli-runner`, and after Task 4 every repair dispatch goes to `apd-tier-repair`. The synthesis-fallback breadcrumb `run-state-fallback` stays general-purpose: it appends YAML with Bash and is not an `apd-gauntlet` command.

After Task 3, guard text stays on six dispatches: `author-threat-model-floor`, `cluster-candidates`, `apply-clusters`, `build-report-attempt-0`, `audit-report-attempt-0` and `domain-coverage-delta`.

`CLI_LABELS` on the WS1 + WS2 base (27), in order:

- setup and intake: `resume-plan`, `validate-scaffold`, `build-domain-skill`, `validate-domain`, `assemble-inventory`, `intake-schema-gate`;
- context: `canonicalize-code-evidence`, `author-threat-model-floor`, `canonicalize-threat-model`;
- tiers: `canonicalize-10-trustworthiness`, `validate-10-trustworthiness`, `canonicalize-20-scalability`, `validate-20-scalability`, `canonicalize-30-auditability`, `validate-30-auditability`, `validate-full-prephase5`;
- synthesis: `cluster-candidates`, `apply-clusters`, `assemble-c4`, `canonicalize-tmeval`, `rollup`, `build-report-attempt-0`, `audit-report-attempt-0`;
- Phase 5h and closeout: `domain-coverage-delta`, `canonicalize-dimpr`, `summarize`, `validate-final`.

After Task 3 (18):

- setup and intake: `resume-plan`, `prepare-run`, `assemble-inventory`, `intake-schema-gate`;
- context: `canonicalize-code-evidence`, `author-threat-model-floor`, `canonicalize-threat-model`;
- tiers: `tier-gate-10-trustworthiness`, `tier-gate-20-scalability`, `tier-gate-30-auditability`, `validate-full-prephase5`;
- synthesis: `cluster-candidates`, `apply-clusters`, `post-tier4`, `build-report-attempt-0`, `audit-report-attempt-0`;
- Phase 5h and closeout: `domain-coverage-delta`, `closeout`.

If the merged base prints different labels, pin what the harness prints there and keep the −9 delta.

---

### Task 1: `apd-cli-runner` agent and `pyStep` dispatch

**Files:**

- Create: `.claude/agents/apd-cli-runner.md`, `tests/js/workflow_dispatch_trace.mjs`, `tests/test_workflow_dispatch_trace.py`, `tests/test_agent_apd_cli_runner.py`
- Modify `.claude/workflows/apd-gauntlet.js`:
  - the header comment (`:1-31`): "pyStep() dispatches a general-purpose Bash agent" now names `apd-cli-runner`;
  - identifier checks after the `args.domains` check (`:126-129`);
  - `function pyStep`.
- Modify: `.claude-plugin/plugin.json` (`agents`: insert `./.claude/agents/apd-cli-runner.md` after `apd-availability.md`)
- Modify: `tools/apd_gauntlet/measure/usage.py` (WS2 `AGENT_PHASES`: `"apd-cli-runner": "cli-steps"`)
- Modify: `docs/architecture.md:25-41` (it says 21 agents in three places today; all three become 22: the heading reads "The 22 agents", and the orchestrator paragraph reads "twenty-third … among the 22"; add one table row), `tests/test_docs_v14.py:24-26` (`"22 agents"`), `CHANGELOG.md`
- Modify: `.github/workflows/python-tests.yml` (the `test` job gains a SHA-pinned `actions/setup-node` step with Node 22; without it the dispatch-trace tests skip in CI)
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_pystep_dispatches_cli_runner`; update WS1's `test_always_run_pystep_prompt_offers_no_skip` and `test_pystep_always_run_branch_is_pinned_in_the_source`), `tests/test_measure_usage.py` (append one assertion)

**Interfaces:**

- Consumes: `pyStep(cmd, opts)`, `guard()` and `RECEIPT` as WS1 left them, including the `opts.resumePlan` and `opts.errorsFromJson` prompt lines; WS2 `phase_for`.
- Produces:
  - Agent frontmatter, exactly:

    ```yaml
    ---
    name: apd-cli-runner
    description: "Runs one apd-gauntlet CLI command and returns its receipt; dispatched by the apd-gauntlet workflow only."
    tools: Bash
    model: haiku
    effort: low
    ---
    ```

  - The `pyStep` prompt, whose lines the runner and the harness parse:
    - first line: the guard block, or, when `opts.alwaysRun`, WS1's always-run line verbatim: `'Always run this command; this step has no idempotency check and no skip.'` (no `NO IDEMPOTENT SKIP` line; register A9.8, DEC-17);
    - `COMMAND: apd-gauntlet <cmd> [positional] [cliArgs]`;
    - `RECEIPT AGENT: pystep:<cmd>`;
    - then every `opts`-conditional line as it stands: `reportAudit` (856ea96), and WS1's `resumePlan` (`VERBATIM`) and `errorsFromJson` (`at most 50`). WS1's tests pin these in the `pyStep` body.
  - The dispatch is `agent(prompt, {agentType: 'apd-cli-runner', schema: RECEIPT, phase: opts.phase, label: …})`. `pyStep` stays synchronous: it returns that dispatch without `await`, and its callers await it (register A15.21). It uses no new top-level constants, because WS1's node renderer extracts only the `guard` and `pyStep` bodies (register A9.8).
  - JS constants `RUN_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/`, `DOMAIN_RE = /^[a-z][a-z0-9-]*$/` and `FRAMEWORK_VERSION_RE = /^[0-9]+\.[0-9]+\.[0-9]+$/`. These are the `run-config.schema.json` patterns at lines 9-11.
  - Harness CLI: `node tests/js/workflow_dispatch_trace.mjs <workflow.js> '<args-json>' ['<fail-json>']`.
    - It prints a JSON list of `{agentType: string|null, label, phase, guard: boolean, command: string|null}`.
    - If the workflow throws, it exits 3 with the message on stderr.
    - `fail-json` maps a label to the names of its failing steps. The stub then returns `status: 'error'` with one `errors[]` entry per name (`message: 'exit=1; stub'`). An empty list yields one error whose `path` is the label.
  - Python helpers in `tests/test_workflow_dispatch_trace.py`:
    - `trace_raw(cfg: dict[str, Any], fail: dict[str, list[str]] | None = None) -> subprocess.CompletedProcess[str]`, which calls `pytest.skip` when `shutil.which("node") is None`;
    - `trace(cfg, fail=None) -> list[dict[str, Any]]`;
    - `cli(t) -> list[dict]` and `llm(t) -> list[dict]`, which split a trace on `agentType == "apd-cli-runner"`;
    - constants `HA_SHAPED = {"run_id": "r", "domains": ["pbm"], "code_recon": "enabled", "crown_jewels": ["phi_store"]}` and `CLI_LABELS` (the 27 base labels above).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent_apd_cli_runner.py
AGENT = REPO / ".claude" / "agents" / "apd-cli-runner.md"

def test_frontmatter_is_registry_r5():
    meta = _frontmatter(AGENT)  # copy of _agent_frontmatter, tests/test_lint_agent_apd_threat_model_author.py:22-28
    assert (meta["name"], meta["tools"], meta["model"], meta["effort"]) == (
        "apd-cli-runner", "Bash", "haiku", "low")
    assert len(meta["description"]) <= 160 and "\n" not in meta["description"]

def test_body_contract():
    body = AGENT.read_text(encoding="utf-8").split("\n---\n", 1)[1]
    for phrase in ("COMMAND:", "begin with `apd-gauntlet`", "refused: not an apd-gauntlet command",
                   "exit=<N>; <stderr-tail>", "schemas/agent-receipt.schema.json"):
        assert phrase in body, phrase

def test_lints_clean():
    assert lint_agent_file(AGENT, REPO) == []
```

```python
# tests/test_workflow_dispatch_trace.py
def test_every_clean_run_dispatch_names_an_agent():
    assert all(d["agentType"] for d in trace(HA_SHAPED))

def test_cli_steps_go_to_cli_runner():
    steps = cli(trace(HA_SHAPED))
    assert [d["label"] for d in steps] == CLI_LABELS
    assert all(d["command"].startswith("apd-gauntlet ") for d in steps)

def test_llm_dispatch_count_unchanged():
    assert len(llm(trace(HA_SHAPED))) == 18

@pytest.mark.parametrize("patch", [{"run_id": "r; touch x"}, {"domains": ["pbm", "$(id)"]},
                                   {"framework_version": "1.7.0 && id"}])
def test_trace_rejects_shell_metacharacters(patch):
    r = trace_raw({**HA_SHAPED, **patch})
    assert r.returncode == 3 and "run-config.schema.json" in r.stderr
```

```python
# tests/test_workflow_apd_gauntlet.py (append; _fn_body comes from WS1 Task 2)
def test_pystep_dispatches_cli_runner() -> None:
    body = _fn_body(_text(), "pyStep")
    assert "agentType: 'apd-cli-runner'" in body and "'COMMAND: ' + invocation" in body
    assert "You are a python-step worker" not in body  # the static contract now lives in the agent body
```

Update WS1's `test_always_run_pystep_prompt_offers_no_skip` and `test_pystep_always_run_branch_is_pinned_in_the_source` to the `COMMAND:`/`RECEIPT AGENT:` contract; they keep the always-run line and the absence of `NO IDEMPOTENT SKIP`. The `WORK COMMAND` and `short-circuited` pins move to the agent-body test, `test_body_contract` (register A9.8).

```python
# tests/test_measure_usage.py (append)
def test_cli_runner_is_a_cli_step():
    assert phase_for("apd-cli-runner") == phase_for("apd-gauntlet:apd-cli-runner") == "cli-steps"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_agent_apd_cli_runner.py tests/test_workflow_dispatch_trace.py tests/test_workflow_apd_gauntlet.py tests/test_measure_usage.py -v`
Expected: FAIL. The agent file and the harness are missing, CLI dispatches have `agentType` null, and `phase_for("apd-cli-runner")` returns `unattributed`. WS2's `test_agent_phases_cover_agents_and_workflow_phases` also fails once the agent file exists, until `AGENT_PHASES` gains the entry.

- [ ] **Step 3: Write the agent, the harness, the `pyStep` change and the usage map entry**

The agent body has three sections: `# apd-cli-runner`, `## Job` and `## Final message (receipt only)`.

The `## Job` rules are:

- Run the guard check first when the prompt has an `IDEMPOTENCY GUARD` block, and follow its skip rule.
- Otherwise run the `COMMAND:` line exactly once with Bash, from the current directory.
- Every command run must begin with `apd-gauntlet`. If the `COMMAND:` line does not, run nothing and return `status: error` with `message: "refused: not an apd-gauntlet command"`.
- Never create, edit or delete files. Never run any other command. Never retry.
- Follow any extra receipt line the prompt carries (`REPORT AUDIT`, WS1's verbatim `resume_plan` copy, WS1's JSON error mapping).

`## Final message` takes the static receipt-mapping lines from `pyStep`, verbatim: `agent` from `RECEIPT AGENT`, the status, outputs and counts, and the default `exit=<N>; <stderr-tail>` error. It ends with a reference to `schemas/agent-receipt.schema.json`.

Error throws name the key and say it "does not match run-config.schema.json; refusing to build a shell command from it". The `framework_version` check applies only when the key is present.

Add an architecture table row: `| CLI step runner | apd-cli-runner | Runs one apd-gauntlet command per CLI step (Bash only, Haiku, low effort) and returns its receipt |`. The harness, whose algorithm the tests do not fix:

```js
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const [, , wfPath, argsJson, failJson] = process.argv;
const fail = failJson ? JSON.parse(failJson) : {};
const src = readFileSync(wfPath, 'utf8').replace(/^export const meta/m, 'const meta');
const trace = [];
function agent(prompt, opts = {}) {
  const m = /^COMMAND: (.+)$/m.exec(prompt);
  trace.push({ agentType: opts.agentType || null, label: opts.label, phase: opts.phase || null,
    guard: prompt.includes('IDEMPOTENCY GUARD'), command: m ? m[1] : null });
  if (!opts.schema) return 'GATE: pass';
  const base = { agent: 'stub', outputs: [], counts: {}, resume_plan: { engine_version: '0', steps: [] },
    report_audit: { structural_failed: 0, editorial_failed: 0 } };
  const names = fail[opts.label];
  if (!names) return { ...base, status: 'ok' };
  return { ...base, status: 'error',
    errors: (names.length ? names : [opts.label]).map((n) => ({ path: n, message: 'exit=1; stub' })) };
}
const ctx = { args: JSON.parse(argsJson), agent, phase() {}, log() {}, parallel: (ts) => Promise.all(ts.map((t) => t())) };
try { await vm.runInNewContext('(async function () {\n' + src + '\n})()', ctx); }
catch (e) { process.stderr.write(String((e && e.message) || e)); process.exit(3); }
process.stdout.write(JSON.stringify(trace));
```

CHANGELOG, under `### Changed`: CLI steps now run on `apd-cli-runner` (Bash only, Haiku, low effort) instead of a general-purpose agent on the session model. The workflow refuses run ids, domains and framework versions that do not match the run-config schema.

- [ ] **Step 4: Run the tests and the linters**

Run: `pytest tests/test_agent_apd_cli_runner.py tests/test_workflow_dispatch_trace.py tests/test_workflow_apd_gauntlet.py tests/test_measure_usage.py tests/test_plugin_manifest.py tests/test_docs_v14.py -v && apd-gauntlet lint-agents && markdownlint-cli2 .claude/agents/apd-cli-runner.md docs/architecture.md CHANGELOG.md`
Expected: PASS; "Lint clean: 23 agents checked."; 0 markdownlint errors.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-cli-runner.md .claude/workflows/apd-gauntlet.js .claude-plugin/plugin.json tools/apd_gauntlet/measure/usage.py tests/js tests/test_workflow_dispatch_trace.py tests/test_agent_apd_cli_runner.py tests/test_workflow_apd_gauntlet.py tests/test_measure_usage.py tests/test_docs_v14.py docs/architecture.md .github/workflows/python-tests.yml CHANGELOG.md
git commit -m "feat(workflow): dispatch CLI steps to a Bash-only Haiku apd-cli-runner"
```

- [ ] **Step 6 (operator): Compare against the previous accepted state**

Run the master plan Task 1 set twice on this PR's head, as `runs/<x>-ws3t1-r1` and `-r2`, with telemetry in `telemetry/<x>-ws3t1-r<k>.otlp.jsonl`. Then run `apd-gauntlet usage runs/<x>-ws3t1-r<k> --otel telemetry/<x>-ws3t1-r<k>.otlp.jsonl` for each run, and `apd-gauntlet compare-runs <prev> runs/<x>-ws3t1 --gates eval/gates.yaml` for each example.
Expected: every `compare-runs` exits 0 (`pass` or `pass_with_gaps`). In each `usage.yaml`, `by_agent` has `apd-cli-runner` and no `general-purpose`, and the `cost_usd` that `compare-runs --json` reports per run is at or below `<prev>`. If a gate fails, do not merge; attach the `--json` output to the PR.

### Task 2: Composite commands

**Files:**

- Create: `tools/apd_gauntlet/composite.py`, `tests/test_cli_composites.py`
- Modify: `tools/apd_gauntlet/cli.py`: add four commands next to the `canonicalize` command (`@main.command("canonicalize")`, ≈ 1358–1365)
- Modify: `docs/running-the-gauntlet.md:40-74` (CLI reference: four lines), `CHANGELOG.md` (`### Added`)

**Interfaces:**

- Consumes:
  - `validate`, `build-domain-skill`, `validate-domain`, `canonicalize`, `assemble-c4`, `rollup` and `summarize`, invoked through `apd_gauntlet.cli.main`;
  - WS2's `summarize --record-attempts JSON`;
  - `FRAMEWORK_VERSION` (PR #28) as `build-domain-skill`'s default.
- Produces (`apd_gauntlet.composite`):
  - `@dataclass(frozen=True) class SubStep: name: str; argv: tuple[str, ...]; stdout_to_stderr: bool = False`
  - `Invoke = Callable[[Sequence[str]], int]`
  - `def invoke(argv: Sequence[str]) -> int` calls `cli.main.main(args=list(argv), prog_name="apd-gauntlet", standalone_mode=False)` (with a lazy import). It returns the exit code the standalone command would have produced:
    - a `SystemExit` code;
    - for a `ClickException`, `show()` and then `exit_code`;
    - for any other `Exception`, a traceback on stderr and 1.
  - `def run_composite(name: str, steps: Sequence[SubStep], *, gate: str | None = None, invoke: Invoke = invoke) -> int`:
    - It runs every step in order, with stdout redirected to stderr for a step that sets `stdout_to_stderr`.
    - After each step it writes `f"{name}: {step.name} exit={code}"` to stderr. At the end it writes `f"{name}: ok"` or `f"{name}: failed {','.join(failed)}"`.
    - It returns the code of the step named `gate` when `gate` is set. Otherwise it returns the first non-zero code, or 0.
  - Step builders:
    - `prepare_run_steps(run_dir: Path, domains: Sequence[str], framework_version: str | None) -> list[SubStep]` gives `validate <run> --schema-only --errors-only`, then `build-domain-skill <domains…> [--framework-version V]`, then `validate-domain <domains…>`.
    - `tier_gate_steps(run_dir: Path, tier: str, *, json_output: bool = False) -> list[SubStep]` gives `canonicalize <run>` (whole run; `stdout_to_stderr=json_output`), then `validate <run> --tier <tier>` plus `--json` or `--errors-only`.
    - `post_tier4_steps(run_dir: Path) -> list[SubStep]` gives `assemble-c4`, `canonicalize`, `rollup`.
    - `closeout_steps(run_dir: Path, record_attempts: str | None = None) -> list[SubStep]` gives `canonicalize`, `summarize [--record-attempts JSON]`, `validate <run> --errors-only`.
  - CLI commands:
    - `prepare-run RUN_DIR [--domain D]...` takes domains from `--domain`, otherwise from `RUN_DIR/.apd-run.yaml` `domains`, and takes `framework_version` from that file when present. With no domains it raises `click.UsageError` (exit 2) naming `--domain`.
    - `tier-gate RUN_DIR --tier TIER [--json]` uses `gate="validate"`. With `--json`, stdout carries only `validate`'s JSON, which WS1's `errorsFromJson` parses.
    - `post-tier4 RUN_DIR`.
    - `closeout RUN_DIR [--record-attempts JSON]`.
    - Each command ends with `raise SystemExit(run_composite(...))`.

- [ ] **Step 1: Write the failing tests**

Fixtures:

- `ceb` copies `examples/apd-20260601-claim-event-bus/expected` to `tmp_path / "run"`. Its `.apd-run.yaml` has `domains: [pbm]` and `framework_version: 1.4.0`.
- `bare` copies `tests/fixtures/runs/clean-run`, which has no `40-synthesis` deduped files.
- Tests that build the domain skill call `monkeypatch.chdir(tmp_path)`.

Helpers:

- `_status(r, name)` returns the lines of `r.stderr` that start with `f"{name}: "`.
- `_set_first_finding(path, **fields)` updates the first record under `finding` and writes it back.
- `_raise(exc)` returns a function that raises `exc` whatever its arguments.
- `GOOD_ATTEMPTS` is WS2's `GOOD` mapping from `tests/test_summarize.py`.

```python
def test_prepare_run_runs_three_steps(ceb, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(main, ["prepare-run", str(ceb)])
    assert r.exit_code == 0, r.output
    assert _status(r, "prepare-run") == [
        "prepare-run: validate exit=0", "prepare-run: build-domain-skill exit=0",
        "prepare-run: validate-domain exit=0", "prepare-run: ok"]
    assert "framework_version: 1.4.0" in (tmp_path / ".claude/skills/apd-domain/SKILL.md").read_text()

def test_prepare_run_bad_domain_runs_all_and_keeps_code(ceb, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(main, ["prepare-run", str(ceb), "--domain", "nope"])
    assert r.exit_code == 1
    assert _status(r, "prepare-run")[-1] == "prepare-run: failed build-domain-skill,validate-domain"

def test_prepare_run_without_framework_version_uses_default(bare, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (bare / ".apd-run.yaml").write_text("run_id: run\ndomains: [pbm]\n")
    assert CliRunner().invoke(main, ["prepare-run", str(bare)]).exit_code == 0
    assert f"framework_version: {FRAMEWORK_VERSION}" in (tmp_path / ".claude/skills/apd-domain/SKILL.md").read_text()

def test_prepare_run_without_domains_is_usage_error(bare):
    r = CliRunner().invoke(main, ["prepare-run", str(bare)])
    assert r.exit_code == 2 and "--domain" in r.output

def test_tier_gate_clean_then_schema_error(ceb):
    assert CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "10-trustworthiness"]).exit_code == 0
    _set_first_finding(ceb / "10-trustworthiness/confidentiality.findings.yaml", severity="catastrophic")
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "10-trustworthiness"])
    assert r.exit_code == 1 and "ERROR" in r.stdout and "tier-gate: validate exit=1" in _status(r, "tier-gate")

def test_tier_gate_json_stdout_is_validate_json(ceb):
    _set_first_finding(ceb / "10-trustworthiness/confidentiality.findings.yaml", severity="catastrophic")
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "10-trustworthiness", "--json"])
    errors = json.loads(r.stdout)["errors"]
    assert r.exit_code == 1 and errors and errors[0]["file"].endswith("confidentiality.findings.yaml")

def test_tier_gate_exit_is_the_validate_gate(ceb, monkeypatch):
    from apd_gauntlet.canonicalize import CanonicalizeCollision
    monkeypatch.setattr("apd_gauntlet.canonicalize.canonicalize_run", _raise(CanonicalizeCollision("dup")))
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "10-trustworthiness"])
    assert r.exit_code == 0 and "tier-gate: canonicalize exit=1" in _status(r, "tier-gate")

def test_tier_gate_missing_tier_dir(ceb):
    r = CliRunner().invoke(main, ["tier-gate", str(ceb), "--tier", "99-nope"])
    assert r.exit_code == 1 and "--tier subdir not found" in r.output

def test_post_tier4_order(ceb):
    r = CliRunner().invoke(main, ["post-tier4", str(ceb)])
    assert [l.split()[1] for l in _status(r, "post-tier4")[:3]] == ["assemble-c4", "canonicalize", "rollup"]
    assert r.exit_code == 0 and (ceb / "40-synthesis/c4-model.yaml").is_file()

def test_post_tier4_rollup_failure_is_named(bare):
    r = CliRunner().invoke(main, ["post-tier4", str(bare)])
    assert r.exit_code == 1 and "post-tier4: rollup exit=1" in _status(r, "post-tier4")
    assert "post-tier4: assemble-c4 exit=0" in _status(r, "post-tier4")

def test_post_tier4_assemble_failure_still_runs_rollup(ceb, monkeypatch):
    monkeypatch.setattr("apd_gauntlet.assemble_c4.assemble_c4", _raise(RuntimeError("boom")))
    r = CliRunner().invoke(main, ["post-tier4", str(ceb)])
    assert r.exit_code == 1
    assert {"post-tier4: assemble-c4 exit=1", "post-tier4: rollup exit=0"} <= set(_status(r, "post-tier4"))

def test_closeout_order_and_attempts(ceb):
    r = CliRunner().invoke(main, ["closeout", str(ceb), "--record-attempts", json.dumps(GOOD_ATTEMPTS)])
    assert r.exit_code == 0 and (ceb / ".apd-state/attempts.yaml").is_file()
    assert [l.split()[1] for l in _status(r, "closeout")[:3]] == ["canonicalize", "summarize", "validate"]

def test_run_composite_exit_rules():
    steps = [SubStep(n, ()) for n in ("a", "b", "c")]
    codes = lambda seq: (lambda it: lambda argv: next(it))(iter(seq))
    assert run_composite("x", steps, invoke=codes([0, 3, 1])) == 3
    assert run_composite("x", steps, gate="c", invoke=codes([1, 0, 0])) == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cli_composites.py -v`
Expected: FAIL (`No such command 'prepare-run'`; `ModuleNotFoundError: apd_gauntlet.composite`).

- [ ] **Step 3: Implement `composite.py` and the four commands**

Pass `str(run_dir)` in every argv. Redirect with `contextlib.redirect_stdout(sys.stderr)`. `prepare-run` reads `.apd-run.yaml` with `yaml.safe_load`; on `yaml.YAMLError` it raises `click.UsageError`, as `cluster-candidates` does (`cli.py:1298-1306`). Add the four commands to the CLI reference, one line each, in the existing aligned-comment style. The `tier-gate` line says it canonicalizes the whole run and exits with the `validate` result.

- [ ] **Step 4: Run the tests, the type checker and the linter**

Run: `pytest tests/test_cli_composites.py tests/test_cli.py tests/test_summarize.py -v && mypy tools/ && ruff check tools/ tests/`
Expected: PASS; no mypy or ruff errors.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/composite.py tools/apd_gauntlet/cli.py tests/test_cli_composites.py docs/running-the-gauntlet.md CHANGELOG.md
git commit -m "feat(cli): add prepare-run, tier-gate, post-tier4 and closeout composites"
```

This task needs no operator step: nothing dispatches the composites yet.

### Task 2a: Run `manual-audit-prompts` at closeout

(Consolidated plan task N19.)

`closeout` gains an always-run constituent `manual-audit-prompts <run-dir>` after `summarize`, writing `40-synthesis/manual-audit-prompts.md` (the command exists since 1.7.0 but nothing calls it). Tests: `tests/test_cli_composites.py::test_closeout_runs_manual_audit_prompts` (status line `closeout: manual-audit-prompts exit=0`), and the docs row in `docs/running-the-gauntlet.md`.

### Task 3: Workflow and `plan-run` switch to the composites

WS1 already drops the guard from `intake-schema-gate`, `validate-full-prephase5` and `validate-final`. Here, the guard leaves the remaining read-only steps through the composites, which are all `alwaysRun`: `validate-scaffold` and `validate-domain` (inside `prepare-run`), and `rollup` (inside `post-tier4`).

**Files:**

- Modify `.claude/workflows/apd-gauntlet.js`:
  - setup: `validate-scaffold`, `build-domain-skill` and `validate-domain` become one `prepare-run`, after WS1's `resume-plan`;
  - in WS1's `tierGate`, `return await pyStep('validate', …)` becomes `return await pyStep('tier-gate', …)`;
  - remove the `await pyStep('canonicalize', …)` in `runTier` and the one in WS1's `regate()` (not `repairTierGate`); keep `regate`, which stays `async` because it still awaits `tierGate` (`test_gate_helpers_are_defined_before_run_tier` requires `function regate(`);
  - `assemble-c4`, `canonicalize-tmeval` and `rollup` become `post-tier4`;
  - `canonicalize-dimpr`, `summarize` (WS2's `--record-attempts` form) and `validate-final` become `closeout`.
- Modify: `.claude/agents/apd-cli-runner.md` (`## Final message`: the per-step error rule)
- Modify `tools/apd_gauntlet/plan_run.py`:
  - the setup rows after WS1's `resume-plan` row;
  - an `assemble-inventory` row after `apd-intake`;
  - the tier rows;
  - the rollup row;
  - the closeout row.
- Modify `tests/test_workflow_apd_gauntlet.py`:
  - `:53-57` (the `PYSTEP_PHASE_REFS` comment);
  - `test_referenced_commands_cover_the_pipeline`, `test_build_domain_skill_step_always_runs`, `test_build_domain_skill_framework_version_flag_is_guarded`, `test_canonicalize_pystep_uses_always_run` and `test_canonicalize_precedes_tier_validate_gate`;
  - `test_rollup_outputs_label_includes_metrics` and `test_assemble_c4_wired_after_apath_before_canonicalize`;
  - WS1's `test_resume_plan_is_first_setup_step`, `test_resume_plan_refusal_halts_and_failure_falls_back`, `test_tier_gate_always_runs_and_reports_json_errors` and `test_read_only_gates_always_run`;
  - WS2's `test_closeout_summarize_records_attempts_and_always_runs`.
- Modify `tests/test_workflow_runner_awaits.py`: `EXPECTED_GREEN_LABELS` and the label slices of three node tests (Step 1).
- Modify `tests/test_cli_plan_run.py`: extend `test_plan_run_phase_names_consistent_with_workflow`; update WS1's `test_plan_run_tier_gates_name_the_repair_path`.
- Modify: `docs/running-the-gauntlet.md` (Step 2: the foreground-drive CLI list and runner steps 1, 3 and 5), `CHANGELOG.md`
- Test: `tests/test_workflow_dispatch_trace.py`, `tests/test_agent_apd_cli_runner.py`

**Interfaces:**

- Consumes: Task 2's commands and status-line contract; Task 1's `trace`, `cli` and `llm`; WS1's `tierGate(phaseName, tierDir, suffix)`, `repairTierGate`, `RESUME_DONE` and `plan_run` rows; WS2's `attempts`.
- Produces:
  - Workflow labels `prepare-run`, `tier-gate-<tierDir>[<suffix>]` (WS1 suffixes `-after-repair` and `-after-rerun`), `post-tier4`, `post-tier4-retry-1` and `closeout`.
  - The tier-gate dispatch keeps WS1's `phase: phaseName` (register A9.12, DEC-17).
  - JS `const POST_TIER4_STEPS = ['assemble-c4', 'canonicalize', 'rollup']` and `function stepFailed(r, step, steps)`.
  - Runner rule: when stderr has lines ``<cmd>: <step> exit=<N>``, add one `errors[]` entry per line with N ≠ 0, as `{path: "<step>", message: "exit=<N>; <stderr-tail>"}`. WS1's `errorsFromJson` mapping takes precedence for `tier-gate`.
  - `plan_run.build_plan` CLI refs:
    - `prepare-run runs/<id> --domain <d>…` (phase `setup`);
    - `assemble-inventory runs/<id>` (phase `intake`);
    - `tier-gate runs/<id> --tier <tierDir> --json` (phase `<tierDir>`, so `test_plan_run_mints_context_ids_before_tier_1` still sees exactly two canonicalize-phase rows). The row text matches the workflow's `--tier <dir> --json`, not WS1's `--errors-only` (register A8.9). Its `gate` is WS1's repair text with the leading `validate … --tier … --errors-only` replaced by this ref.
    - `post-tier4 runs/<id>` (phase `synthesis-rollup`; outputs add `c4-model.yaml`);
    - `closeout runs/<id>` (phase `closeout`).
  - WS1's two context `canonicalize` rows stay.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_workflow_dispatch_trace.py: CLI_LABELS becomes the 18 labels under "Dispatch count"
COMPOSITES = {"prepare-run", "tier-gate-10-trustworthiness", "tier-gate-20-scalability",
              "tier-gate-30-auditability", "post-tier4", "closeout"}
GUARDED = {"author-threat-model-floor", "cluster-candidates", "apply-clusters", "build-report-attempt-0",
           "audit-report-attempt-0", "domain-coverage-delta"}

def test_guard_text_only_on_mutating_cli_steps():
    t = cli(trace(HA_SHAPED))
    assert {d["label"] for d in t if d["guard"]} == GUARDED and not COMPOSITES & GUARDED

def test_composite_commands_and_phase():
    t = {d["label"]: d for d in trace(HA_SHAPED)}
    assert t["prepare-run"]["command"] == "apd-gauntlet prepare-run runs/r --domain pbm"
    assert t["tier-gate-20-scalability"]["command"] == "apd-gauntlet tier-gate runs/r --tier 20-scalability --json"
    assert t["tier-gate-20-scalability"]["phase"] == "tier-2"
    assert t["post-tier4"]["command"] == "apd-gauntlet post-tier4 runs/r"
    assert t["closeout"]["command"].startswith("apd-gauntlet closeout runs/r --record-attempts '")

def test_rollup_fallback_keys_on_rollup_step():
    labels = lambda fail: [d["label"] for d in trace(HA_SHAPED, fail)]
    only_c4 = labels({"post-tier4": ["assemble-c4"]})
    assert "post-tier4-retry-1" not in only_c4 and "synthesizer-fallback-rollup" not in only_c4
    rollup = labels({"post-tier4": ["rollup"], "post-tier4-retry-1": ["rollup"]})
    i = rollup.index("post-tier4")
    assert rollup[i:i + 3] == ["post-tier4", "post-tier4-retry-1", "synthesizer-fallback-rollup"]
    assert "synthesizer-fallback-rollup" in labels({"post-tier4": [], "post-tier4-retry-1": []})

BAD = "runs/r/10-trustworthiness/integrity.findings.yaml"  # WS1's failingFiles needs a record-file path

def test_repair_loop_regates_through_tier_gate():
    labels = [d["label"] for d in trace(HA_SHAPED, {"tier-gate-10-trustworthiness": [BAD]})]
    assert labels.index("tier-gate-10-trustworthiness") < labels.index("tier-gate-10-trustworthiness-after-repair")
    assert not any(l.startswith("canonicalize-10-trustworthiness") for l in labels)

def test_plan_run_matches_workflow_dispatch_sequence():
    cfg = {"run_id": "apd-test-full", "domains": ["agentic-ai", "api-security"],
           "code_recon": "enabled", "crown_jewels": ["a"]}
    wf = [("CLI", d["command"].split()[1]) if d["agentType"] == "apd-cli-runner" else ("AGENT", d["agentType"])
          for d in trace(cfg)]
    assert [(s["kind"], s["ref"].split()[0]) for s in build_plan(cfg)] == wf
```

```python
# tests/test_cli_plan_run.py
# extend test_plan_run_phase_names_consistent_with_workflow:
    workflow_cmds = set(re.findall(r"pyStep\('([a-z][a-z0-9-]+)'", js))
    assert {s["ref"].split()[0] for s in plan if s["kind"] == "CLI"} == workflow_cmds

def test_plan_run_cli_rows_use_composites(tmp_path):
    cli = [s["ref"] for s in _plan(tmp_path, FULL_CFG) if s["kind"] == "CLI"]
    assert [r.split()[0] for r in cli] == ["resume-plan", "prepare-run", "assemble-inventory", "validate",
        "canonicalize", "author-threat-model", "canonicalize", "tier-gate", "tier-gate", "tier-gate", "validate",
        "cluster-candidates", "apply-clusters", "post-tier4", "build-report", "audit-report",
        "domain-coverage-delta", "closeout"]
    assert cli[1] == "prepare-run runs/apd-test-full --domain agentic-ai --domain api-security"
```

Reuse WS1's existing `_plan(tmp_path, cfg)` helper in `tests/test_cli_plan_run.py`, which returns `json.loads` of `plan-run --json` on `_write_run(tmp_path, cfg)` and asserts exit 0; do not redefine it (redefining trips ruff F811). WS1's `test_plan_run_tier_gates_name_the_repair_path` now selects refs that start with `"tier-gate "`.

Changes in `tests/test_workflow_apd_gauntlet.py`:

- **Pipeline commands.** `test_referenced_commands_cover_the_pipeline` lists `resume-plan`, `prepare-run`, `tier-gate`, `post-tier4`, `closeout`, `validate`, `canonicalize`, `cluster-candidates`, `apply-clusters`, `build-report` and `audit-report`. It asserts that `pyStep('build-domain-skill'`, `pyStep('validate-domain'`, `pyStep('assemble-c4'`, `pyStep('rollup'`, `pyStep('summarize'`, `label: 'canonicalize-tmeval'`, `label: 'canonicalize-dimpr'` and `'canonicalize-' + tierDir` are absent.
- **Setup.** `test_prepare_run_step_always_runs` replaces the two `build-domain-skill` tests. It applies the same 400-character `alwaysRun: true` regex to `pyStep('prepare-run'`.
- **Tier gate.** In WS1's `test_tier_gate_always_runs_and_reports_json_errors`, `pyStep('validate'` becomes `pyStep('tier-gate'`. `test_canonicalize_pystep_uses_always_run` and `test_canonicalize_precedes_tier_validate_gate` are deleted: the order now lives in `tier_gate_steps`, which Task 2 pins.
- **Resume anchors.** WS1's `test_resume_plan_is_first_setup_step` and `test_resume_plan_refusal_halts_and_failure_falls_back` anchor on `label: 'prepare-run'` instead of `label: 'validate-scaffold'`.
- **Post tier 4.** `test_post_tier4_outputs_label_includes_metrics` uses the regex `pyStep\('post-tier4',\s*\{[^}]*?\}\)`. `test_post_tier4_after_apath_before_report` asserts `phase('apath')` < `pyStep('post-tier4'` < `phase('synthesis-report')`.
- **Closeout.** WS2's attempts test slices from `pyStep('closeout'`.
- **Read-only gates.** WS1's `test_read_only_gates_always_run` drops `validate-final` from `READ_ONLY_GATES` and asserts `alwaysRun: true` in the `pyStep('closeout'` block (register A9.11).

In `tests/test_workflow_runner_awaits.py`, in the same commit (register A15.23):

- `EXPECTED_GREEN_LABELS`: `"validate-scaffold", "build-domain-skill", "validate-domain"` → `"prepare-run"`; each tier's `"canonicalize-<tierDir>", "validate-<tierDir>"` → `"tier-gate-<tierDir>"`; `"assemble-c4", "canonicalize-tmeval", "rollup"` → `"post-tier4"`; `"canonicalize-dimpr", "summarize", "validate-final"` → `"closeout"`.
- The slices of `test_failed_lens_is_retried_after_the_fan_out`, `test_rejected_lens_dispatch_becomes_null_and_is_retried` and `test_red_tier_gate_is_repaired_before_the_next_tier` (its responder key and its `-after-repair` labels) take the `tier-gate-` labels and lose the canonicalize ones.

In `tests/test_agent_apd_cli_runner.py`, extend the phrase list with ``"`<cmd>: <step> exit=<N>`"``.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/test_workflow_apd_gauntlet.py tests/test_agent_apd_cli_runner.py -v`
Expected: FAIL on every new or replaced test (old labels; `plan_run` still emits `build-domain-skill`).

- [ ] **Step 3: Switch the workflow, the runner rule and `plan_run`**

The workflow changes:

- **Setup.** `await pyStep('prepare-run', {phase: 'setup', label: 'prepare-run', cliArgs: args.domains.map(function (d) { return '--domain ' + d; }).join(' '), alwaysRun: true, outputs: …})`. `prepare-run` reads `framework_version` from `.apd-run.yaml`, so the JS `--framework-version` guard goes away.
- **Tier gate.** `tierGate` returns `await pyStep('tier-gate', {phase: phaseName, label: 'tier-gate-' + tierDir + suffix, cliArgs: '--tier ' + tierDir + ' --json', alwaysRun: true, errorsFromJson: true, outputs: …})`. WS2's `attempts.tier_gate_failures` push stays keyed on its receipt.
- **Closeout.** `await pyStep('closeout', {phase: 'closeout', label: 'closeout', alwaysRun: true, cliArgs: "--record-attempts '" + JSON.stringify(attempts) + "'", outputs: runDir + '/.apd-state/attempts.yaml'})`.
- **Post tier 4.** Rollup handling, whose shape the tests only partly fix:

```js
function stepFailed(r, step, steps) {
  if (!isErr(r)) return false;
  const named = ((r && r.errors) || []).filter(function (e) { return steps.indexOf(e.path) >= 0; });
  return named.length === 0 || named.some(function (e) { return e.path === step; });
}
phase('synthesis-rollup');
let pt = await pyStep('post-tier4', { phase: 'synthesis-rollup', label: 'post-tier4', alwaysRun: true,
  outputs: runDir + '/40-synthesis/c4-model.yaml, nist-coverage.yaml, attack-exposure.yaml, ' +
    'apd-coverage-matrix.yaml, metrics.yaml (+ declared-taxonomy coverage files)' });
if (stepFailed(pt, 'rollup', POST_TIER4_STEPS)) {
  pt = await pyStep('post-tier4', { /* same opts */ label: 'post-tier4-retry-1' });
  if (stepFailed(pt, 'rollup', POST_TIER4_STEPS)) { /* the synthesizer-fallback-rollup dispatch, unchanged */ }
} else if (isErr(pt)) {
  log('post-tier4: assemble-c4/canonicalize failed — advisory, as before WS3.');
}
```

In `plan_run`, a `prepare-run` row replaces the `build-domain-skill` and `validate-domain` rows. A `tier-gate` row replaces each tier's `canonicalize` and `validate` pair. A `post-tier4` row replaces `rollup`, and a `closeout` row replaces `summarize`. Add `_step("intake", "CLI", f"assemble-inventory {run_dir}", "00-context/asset-inventory.yaml (asset-/idn-/tb- ids minted; crosses wired)")` after `apd-intake`.

In the docs, the foreground-drive list names `prepare-run`, `tier-gate`, `post-tier4` and `closeout`. Runner step 3 says each tier ends in `tier-gate` (canonicalize the run, then validate the tier), with WS1's repair loop on failure.

- [ ] **Step 4: Run the full suite**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/ && apd-gauntlet lint-agents && markdownlint-cli2 docs/running-the-gauntlet.md CHANGELOG.md .claude/agents/apd-cli-runner.md`
Expected: all pass, including WS1's `test_resumable_labels_match_workflow_llmstep_labels` unchanged.

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js .claude/agents/apd-cli-runner.md tools/apd_gauntlet/plan_run.py tests docs/running-the-gauntlet.md CHANGELOG.md
git commit -m "perf(workflow): run CLI phases through composite commands (9 fewer dispatches per run)"
```

- [ ] **Step 6 (operator): Compare against the previous accepted state**

Same as Task 1 Step 6, with the suffix `-ws3t3` and `<prev>` set to the `-ws3t1` runs.
Expected: every `compare-runs` exits 0; cost at or below `<prev>`.

### Task 4: `effort: low` on WS1's `apd-tier-repair` agent

WS1 created `.claude/agents/apd-tier-repair.md`, and WS1's `repairTierGate` already dispatches it with `agentType: 'apd-tier-repair'` (master plan §A6; register A9.13). Its frontmatter today: `name: apd-tier-repair`, a 150-character description, `tools: [Read, Edit]`, `model: sonnet`, no `effort`. This task adds `effort: low` and WS3's tests. It does not create the agent or touch `plugin.json`, the workflow, `architecture.md`, `test_docs_v14.py` or `usage.py`; WS2 Task 4 lists `apd-tier-repair` under `canonicalize` in `AGENT_PHASES` (register A9.2).

**Files:**

- Modify: `.claude/agents/apd-tier-repair.md` (add `effort: low` after `model: sonnet`), `tests/test_lint_agent_apd_tier_repair.py`, `CHANGELOG.md`
- Test: `tests/test_lint_agent_apd_tier_repair.py`, `tests/test_workflow_dispatch_trace.py` (append one test)

**Interfaces:**

- Consumes:
  - WS1's `repairTierGate`, whose dispatch is `agent(repairPrompt(f, byFile[f]), {agentType: 'apd-tier-repair', schema: RECEIPT, phase: phaseName, label: 'repair-' + tierDir + '-' + baseName(f)})`;
  - WS1's `tools/apd_gauntlet/data/prompts/repair.md`, read through `read_prompt("repair")`, unchanged;
  - Task 1's `trace`.
- Produces: the frontmatter line `effort: low`, after `model: sonnet`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_lint_agent_apd_tier_repair.py`, `test_agent_frontmatter` replaces `assert "effort" not in meta` with `assert meta["effort"] == "low"` and adds `assert len(meta["description"]) <= 160`. Add `test_repair_template_carries_the_excerpt_rule`, which asserts that "not found verbatim", "exact words" and "never paraphrase" are in `read_prompt("repair")`:

```python
# tests/test_lint_agent_apd_tier_repair.py
def test_repair_template_carries_the_excerpt_rule() -> None:
    template = read_prompt("repair")
    for phrase in ("not found verbatim", "exact words", "never paraphrase"):
        assert phrase in template, phrase
```

Append to `tests/test_workflow_dispatch_trace.py`:

```python
# tests/test_workflow_dispatch_trace.py
def test_repair_dispatches_tier_repair_agent():
    t = trace(HA_SHAPED, {"tier-gate-10-trustworthiness": [BAD]})
    repair = [d for d in t if d["label"].startswith("repair-10-trustworthiness-")]
    assert [d["agentType"] for d in repair] == ["apd-tier-repair"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_lint_agent_apd_tier_repair.py tests/test_workflow_dispatch_trace.py -v`
Expected: FAIL in `test_agent_frontmatter` (`KeyError: 'effort'`).

- [ ] **Step 3: Add the line**

Add `effort: low` after `model: sonnet` in `.claude/agents/apd-tier-repair.md`. CHANGELOG, under `### Changed`: `apd-tier-repair` runs at low effort.

- [ ] **Step 4: Run the tests and the linters**

Run: `pytest -q && apd-gauntlet lint-agents && markdownlint-cli2 .claude/agents/apd-tier-repair.md CHANGELOG.md`
Expected: PASS; "Lint clean: 23 agents checked."; 0 markdownlint errors.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-tier-repair.md tests/test_lint_agent_apd_tier_repair.py tests/test_workflow_dispatch_trace.py CHANGELOG.md
git commit -m "perf(agents): run apd-tier-repair at low effort"
```

- [ ] **Step 6 (operator): Compare against the previous accepted state, and exercise a repair**

Same as Task 1 Step 6, with the suffix `-ws3t4` and `<prev>` set to the `-ws3t3` runs. Clean runs rarely repair, so also hand-break one lens file in a copy of a finished run (an unquoted colon in a title) and re-invoke.
Expected: every `compare-runs` exits 0. The broken run logs `tier-gate-<tier>` failing, one `repair-…` dispatch, `tier-gate-<tier>-after-repair` passing and no lens re-run. Its `usage.yaml` shows `apd-tier-repair` under phase `canonicalize`, and the repair's `api_request` events carry `effort: "low"`.

### Task 5: Trim the always-on footprint and remove `apd-orchestrator`

The trim changes no run output: the workflow names every `agentType`, and descriptions only steer delegation. So this task has no compare-runs step; Task 9's measurement covers it.

The coordinator accepted deleting the orchestrator. Keeping the file while dropping it from the manifest would break `tests/test_plugin_manifest.py::test_agents_array_matches_dir`.

**Files:**

- Modify: the `description` of 20 agents and 7 `.claude/skills/*/SKILL.md`. `apd-cli-runner` already complies, and WS1's `apd-tier-repair` description is already ≤ 160 characters. `apd-domain` is excluded: its 161-character description is generated.
- Delete: `.claude/agents/apd-orchestrator.md`, `tests/test_orchestrator_deprecation.py`, `tests/test_orchestrator_topology.py`
- Modify:
  - `.claude-plugin/plugin.json` (drop the orchestrator entry);
  - `tools/apd_gauntlet/lint_agents.py:14` (`RECEIPT_EXEMPT = {"apd-synthesizer"}`) and `:37-40` (description cap);
  - `tools/apd_gauntlet/lint_skills.py:41-49` (description cap);
  - `tests/test_lint_agents_receipt.py:22-26` (`test_synthesizer_is_exempt` writes `apd-synthesizer.md`);
  - `tests/test_doc_domain_pack_authoring.py:20-30` (`_ALLOWED = set()`, comment dropped);
  - `docs/architecture.md:45` (delete the paragraph);
  - `.claude/skills/apd-evidence-discipline/SKILL.md:16` (delete the parenthetical about the deprecated orchestrator);
  - `docs/extending-agents.md:9-13` (note the one-line description cap);
  - `CHANGELOG.md`.
- Create: `tests/test_plugin_footprint.py`
- Test: `tests/test_lint_agents.py`, `tests/test_lint_skills.py`

**Interfaces:**

- Produces:
  - `lint_agents.MAX_AGENT_DESCRIPTION_CHARS = 160` and `lint_skills.MAX_SKILL_DESCRIPTION_CHARS = 200`.
  - Error text, for agents and skills alike: `f"{path}: description is {n} characters (max {MAX}); it loads into every session with the plugin enabled — keep one line"`. A description that contains a newline gets `f"{path}: description must be one line"`.
  - The existing 1536-character skill rule stays.
- Descriptions are written as double-quoted YAML strings, because several contain a colon followed by a space.
  - The lens template is `"APD gauntlet tier-<N> <Goal> lens specialist; dispatched by the apd-gauntlet workflow only."`
  - Every other agent's text ends with `; dispatched by the apd-gauntlet workflow only.` appended directly.
  - Every skill's text ends with one space and then `Read through the agent's Required reading.`

| File | New description (before the fixed ending) |
|---|---|
| `apd-attack-path-analyzer` | `APD gauntlet tier-4 attack-path analysis: asset graph, paths to crown jewels, D3FEND counters` |
| `apd-cluster-adjudicator` | `APD gauntlet synthesis 5b: merge, link or separate candidate clusters` |
| `apd-code-recon` | `APD gauntlet optional code reconnaissance via codebase-memory-mcp (code evidence index, C4 recon)` |
| `apd-domain-auditor` | `APD gauntlet advisory domain-pack improvement capture` |
| `apd-intake` | `APD gauntlet intake: context brief and asset inventory from the run inputs` |
| `apd-report-auditor` | `APD gauntlet synthesis 5g: judges the advisory report's faithfulness to the findings` |
| `apd-report-writer` | `APD gauntlet synthesis 5e: writes the advisory report prose and report-data.yaml` |
| `apd-synthesizer` | `APD gauntlet synthesis fallback, used when the decomposed pipeline fails` |
| `apd-threat-model-author` | `APD gauntlet tier-0: authors the grounded baseline threat model` |
| `apd-threat-model-evaluator` | `APD gauntlet tier-4: checks findings against the threat model (gaps, contradictions, silences)` |
| `apd-threat-model-recon` | `APD gauntlet tier-0: parses a supplied threat model into normalized YAML` |
| `apd-attack-path-discipline` | `Discipline rules for apd-attack-path-analyzer: never-invent nodes and edges, bounded enumeration, D3FEND counters.` |
| `apd-c4-discipline` | `Discipline rules for apd-code-recon when it writes 00-context/c4-recon.yaml.` |
| `apd-control-mappings` | `NIST 800-53r5 and MITRE ATT&CK mapping rules for APD gauntlet findings and capabilities.` |
| `apd-evidence-discipline` | `Evidence, blocking, lens and severity discipline for APD gauntlet specialists.` |
| `apd-finding-schema` | `YAML contracts for APD gauntlet finding and capability records.` |
| `apd-framework` | `The APD framework: three tiers, nine security goals and the boundary rules between goals.` |
| `apd-threat-model-methodologies` | `STRIDE and LINDDUN to APD mappings and rules for the threat-model recon and evaluator agents.` |

The longest agent description is 144 characters and the longest skill description 157. The manifest-listed set, including `apd-cli-runner` and `apd-tier-repair`, totals about 3,536 bytes, down from 16,579 on the WS1 + WS2 base (16,289 at `856ea96`: 12,835 for agents, 3,454 for skills). Replacing every description with a placeholder on a scratch copy broke none of the 1,947 tests at `856ea96`.

- [ ] **Step 1: Write the failing tests**

Helpers: `_norm` is the one in `tests/test_plugin_manifest.py:16-18`. `_description(path)` returns the frontmatter `description` parsed with `lint_agents.FRONTMATTER_PATTERN`.

```python
# tests/test_plugin_footprint.py
def test_always_on_description_budget():
    m = json.loads(PLUGIN.read_text(encoding="utf-8"))
    files = [REPO / _norm(p) for p in m["agents"]] + [REPO / _norm(d) / "SKILL.md" for d in m["skills"]]
    assert sum(len(_description(f).encode("utf-8")) for f in files) <= 4096

def test_orchestrator_removed():
    assert not (REPO / ".claude/agents/apd-orchestrator.md").exists()
    assert not any("apd-orchestrator" in p for p in json.loads(PLUGIN.read_text())["agents"])
```

```python
# tests/test_lint_agents.py
def test_lint_agents_flags_long_description(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: " + "x" * 161 + "\n---\n\n## Final message\n")
    assert any("max 160" in e for e in lint_agent_file(a, tmp_path))

def test_lint_agents_flags_multiline_description(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text('---\nname: apd-x\ndescription: "a\\nb"\n---\n\n## Final message\n')
    assert any("one line" in e for e in lint_agent_file(a, tmp_path))
```

```python
# tests/test_lint_skills.py
def test_lint_skills_flags_description_over_budget(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo\ndescription: " + "x" * 201)
    assert any("max 200" in e for e in lint_skill_dir(d))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_plugin_footprint.py tests/test_lint_agents.py tests/test_lint_skills.py -v`
Expected: FAIL. The budget is over 16,000 bytes against a cap of 4,096, the orchestrator is present, and no cap rule exists.

- [ ] **Step 3: Add the caps, rewrite the descriptions, delete the shim and update the docs**

WS2's `test_agent_phases_cover_agents_and_workflow_phases` already excludes `apd-orchestrator`, so it needs no change.

- [ ] **Step 4: Run the full suite and the linters**

Run: `pytest -q && apd-gauntlet lint-agents && apd-gauntlet lint-skills && markdownlint-cli2 ".claude/**/*.md" docs/architecture.md docs/extending-agents.md CHANGELOG.md`
Expected: PASS; "Lint clean: 22 agents checked."; "Lint clean: 8 skills checked."; 0 markdownlint errors.

- [ ] **Step 5: Commit**

```bash
git add -A .claude .claude-plugin/plugin.json tools/apd_gauntlet/lint_agents.py tools/apd_gauntlet/lint_skills.py tests docs/architecture.md docs/extending-agents.md CHANGELOG.md
git commit -m "perf(plugin): one-line agent and skill descriptions; remove deprecated apd-orchestrator"
```

### Task 6: Set `effort` on every agent

**Files:**

- Modify: the frontmatter of the 20 `.claude/agents/*.md` files without `effort` (leave `model` as it is today)
- Modify:
  - `tools/apd_gauntlet/lint_agents.py:37-40` (rules);
  - `tests/test_validate_edge_cases.py:421-436` (`len(errors) == 3` becomes `4`; assert `any("effort" in e ...)`);
  - `docs/extending-agents.md:9-13` (the example frontmatter gains `effort: medium`);
  - `CHANGELOG.md`.
- Create: `tests/test_agent_effort.py`

**Interfaces:**

- Produces:
  - `lint_agents.ALLOWED_EFFORT = ("low", "medium", "high", "xhigh", "max")` and `lint_agents.MODEL_ALIASES = ("sonnet", "opus", "haiku", "fable", "inherit")`.
  - `lint_agents.FULL_MODEL_ID = re.compile(r"^claude-[a-z0-9.-]+$")`.
  - Errors: `"frontmatter missing 'effort'"`; `f"effort '{v}' is not one of …"`; `f"model '{v}' is not an alias or full model id"`. `model` stays optional until WS5 Task 23.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent_effort.py: (model as WS3 leaves it, effort per Global Constraints)
LENSES = ["confidentiality", "integrity", "availability", "distributed", "resilient", "ephemeral",
          "authenticity", "non-repudiation", "immutability"]
EXPECTED = {f"apd-{lens}": (None, "medium") for lens in LENSES} | {
    "apd-cli-runner": ("haiku", "low"), "apd-tier-repair": ("sonnet", "low"),
    "apd-intake": (None, "medium"), "apd-code-recon": (None, "medium"),
    "apd-threat-model-author": ("opus", "medium"), "apd-threat-model-recon": (None, "low"),
    "apd-threat-model-evaluator": (None, "high"), "apd-attack-path-analyzer": ("opus", "medium"),
    "apd-cluster-adjudicator": ("opus", "high"), "apd-report-writer": ("opus", "medium"),
    "apd-report-auditor": ("opus", "high"), "apd-domain-auditor": ("opus", "medium"),
    "apd-synthesizer": (None, "high")}

def test_every_agent_has_expected_model_and_effort():
    files = sorted(AGENTS.glob("*.md"))
    assert {f.stem for f in files} == set(EXPECTED)
    for f in files:
        meta = _frontmatter(f)
        assert (meta.get("model"), meta.get("effort")) == EXPECTED[f.stem], f.name

@pytest.mark.parametrize(("extra", "needle"), [("", "missing 'effort'"), ("effort: extreme\n", "effort 'extreme'"),
                                               ("effort: low\nmodel: opsu\n", "model 'opsu'")])
def test_lint_effort_and_model_rules(tmp_path, extra, needle):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: x\n" + extra + "---\n\n## Final message\n")
    assert any(needle in e for e in lint_agent_file(a, tmp_path))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_agent_effort.py tests/test_validate_edge_cases.py::test_lint_agent_missing_name_and_description -v`
Expected: FAIL (20 agents without `effort`; no lint rule).

- [ ] **Step 3: Add the rules and the `effort` lines**

- [ ] **Step 4: Run the full suite and the linter**

Run: `pytest -q && apd-gauntlet lint-agents`
Expected: PASS, including both Opus-pinning tests unchanged; "Lint clean: 22 agents checked."

- [ ] **Step 5: Commit**

```bash
git add .claude/agents tools/apd_gauntlet/lint_agents.py tests/test_agent_effort.py tests/test_validate_edge_cases.py docs/extending-agents.md CHANGELOG.md
git commit -m "perf(agents): set effort on every agent (audit Wave 3 values; models unchanged)"
```

- [ ] **Step 6 (operator): Compare against the previous accepted state**

Same as Task 1 Step 6, with the suffix `-ws3t6` and `<prev>` set to the `-ws3t4` runs. Launch the session at the same effort as for `<prev>`, so that only the frontmatter differs.
Expected: every `compare-runs` exits 0; cost at or below `<prev>`.

### Task 6a: Lint each agent's tools

(Consolidated plan task N18.)

**Files:** `tools/apd_gauntlet/lint_agents.py`; `tests/test_lint_agents.py`.

**Interfaces:** `lint_agent_file` requires `tools` and parses both the comma-string and YAML-list forms; `tests/test_lint_agents.py::EXPECTED_TOOLS: dict[str, frozenset[str]]` pins every agent's tool set, recording that `apd-threat-model-recon`, `apd-threat-model-author`, `apd-attack-path-analyzer` and `apd-domain-auditor` still hold `Bash` (Phase 10 removes it).

- [ ] Steps: test `test_every_agent_tool_set_is_pinned` and `test_missing_tools_is_an_error` → fail → implement → pass → QG. Commit: `test(agents): pin each agent's tool set`.

### Task 7: Domain auditor opt-in (`domain_improvement_capture`)

**Files:**

- Modify:
  - `tools/apd_gauntlet/data/schemas/run-config.schema.json` (a property after `infrastructure`, `:95`);
  - `tools/apd_gauntlet/init_run.py` ≈ 80–96 (template comment);
  - `tools/apd_gauntlet/plan_run.py` ≈ 205–213 and ≈ 250–257 (gate and note);
  - `.claude/workflows/apd-gauntlet.js`: the `PHASE 5h` domain-capture block (≈ 1080–1115; after Task 3 it holds only `domain-coverage-delta` and `domain-auditor`) for the Phase 5h gate, plus a type check next to the Task 1 identifier checks.
- Modify:
  - `docs/improving-domain-packs.md:3-35` ("every run", lines 6, 16 and 18, becomes opt-in);
  - `docs/architecture.md` ≈ 44 (`apd-domain-auditor` runs only when opted in);
  - `docs/running-the-gauntlet.md` (new subsection "Domain-improvement capture (opt-in)" before `## Code reconnaissance (optional)`);
  - `docs/schema-evolution.md` (a dated entry under WS2's 2.0 section);
  - `CHANGELOG.md`.
- Test:
  - `tests/test_run_config_schema.py` and `tests/test_init_run_config.py`;
  - `tests/test_cli_plan_run.py` (`FULL_CFG` gains `"domain_improvement_capture": True`, since it exercises every gate);
  - `tests/test_workflow_apd_gauntlet.py`, `tests/test_workflow_dispatch_trace.py` and `tests/test_workflow_runner_awaits.py`.

**Interfaces:**

- Produces:
  - Schema property `"domain_improvement_capture": {"type": "boolean", "default": false, "description": "Opt in to Phase 5h, the advisory domain-pack auditor. Absent or false skips it."}`.
  - Template line `"# domain_improvement_capture: true  # opt in to Phase 5h (advisory domain-pack auditor); default off\n"`.
  - JS helper:

    ```js
    function skipReceipt(phaseName, reason) {
      log(phaseName + ': skipped (' + reason + ')');
      return { agent: 'skip:' + phaseName, status: 'ok',
        outputs: [{ path: phaseName + '.skipped', schema_valid: true }], counts: {} };
    }
    ```

    It emits the skip sentinel that the SKIP CONVENTION paragraph of the workflow header comment documents (≈ 45–52) with no dispatch. The gate is `args.domain_improvement_capture === true`. Inside the condition the capture steps stay `await pyStep('domain-coverage-delta', …)` and `await llmStep('apd-domain-auditor', …)` (register A15.24). A defined non-boolean throws an error that names `domain_improvement_capture`.
  - `plan_run` emits both rows only when `cfg.get("domain_improvement_capture") is True`. Otherwise `render_markdown` adds `> Note: domain-improvement capture (Phase 5h) is off for this run — set domain_improvement_capture: true in .apd-run.yaml to run the advisory domain-pack auditor.`
  - `resume-plan` is unchanged. WS1 lists `domain-auditor` as it lists `tm-recon`, and the workflow gate decides whether either step dispatches.

- [ ] **Step 1: Write the failing tests**

Helpers:

- `_cfg(**kw)` is `{"run_id": "r", "domains": ["pbm"], "framework_version": "2.0.0", **kw}`.
- `_scaffold(tmp_path)` is `scaffold_run("run-dic", inputs, ["pbm"], tmp_path / "runs")` with a one-file `inputs` directory, as in `test_scaffold_run_writes_live_framework_version`.

```python
# tests/test_run_config_schema.py
@pytest.mark.parametrize("value", [True, False])
def test_domain_capture_accepts_booleans(value):
    assert not list(Draft202012Validator(SCHEMA).iter_errors(_cfg(domain_improvement_capture=value)))

@pytest.mark.parametrize("value", ["true", 1, None])
def test_domain_capture_must_be_boolean(value):
    errors = list(Draft202012Validator(SCHEMA).iter_errors(_cfg(domain_improvement_capture=value)))
    assert errors and "domain_improvement_capture" in str(errors[0].path)
```

```python
# tests/test_init_run_config.py
def test_scaffold_run_documents_domain_capture_opt_in(tmp_path):
    text = (_scaffold(tmp_path) / ".apd-run.yaml").read_text()
    assert "# domain_improvement_capture: true" in text
    assert "domain_improvement_capture" not in yaml.safe_load(text)
```

```python
# tests/test_cli_plan_run.py
def test_plan_run_domain_capture_default_off(tmp_path):
    run_dir = _write_run(tmp_path, BASE_CFG)
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(run_dir)]).output)
    assert not any(s["phase"] in {"domain-coverage-delta", "domain-improvements"} for s in plan)
    assert "domain_improvement_capture: true" in CliRunner().invoke(main, ["plan-run", str(run_dir)]).output
```

```python
# tests/test_workflow_dispatch_trace.py
def test_domain_capture_default_off_and_opt_in():
    off, on = trace(HA_SHAPED), trace({**HA_SHAPED, "domain_improvement_capture": True})
    assert not {"domain-coverage-delta", "domain-auditor"} & {d["label"] for d in off}
    assert {"domain-coverage-delta", "domain-auditor"} <= {d["label"] for d in on}
    assert (len(cli(off)), len(llm(off)), len(cli(on)), len(llm(on))) == (17, 17, 18, 18)
    assert trace_raw({**HA_SHAPED, "domain_improvement_capture": "true"}).returncode == 3
```

Also:

- In `tests/test_workflow_apd_gauntlet.py`, assert that `"args.domain_improvement_capture === true"`, `skipReceipt('domain-coverage-delta'` and `skipReceipt('domain-improvements'` are all in the text, and that both phase names stay in `meta.phases`.
- `CLI_LABELS` and `GUARDED` drop `domain-coverage-delta`, and `test_llm_dispatch_count_unchanged` expects 17.
- In `tests/test_workflow_runner_awaits.py`, `domain-coverage-delta` and `domain-auditor` leave `EXPECTED_GREEN_LABELS`, because the harness `ARGS` have no `domain_improvement_capture` (register A15.24).
- `test_plan_run_matches_workflow_dispatch_sequence` keeps passing unchanged: its config has no key, so both sides omit Phase 5h.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_run_config_schema.py tests/test_init_run_config.py tests/test_cli_plan_run.py tests/test_workflow_dispatch_trace.py tests/test_workflow_apd_gauntlet.py -v`
Expected: FAIL (`additionalProperties` rejects the key; the auditor is dispatched by default).

- [ ] **Step 3: Implement the schema, template, gate, note and docs**

- [ ] **Step 4: Run the full suite and markdownlint**

Run: `pytest -q && markdownlint-cli2 docs/improving-domain-packs.md docs/architecture.md docs/running-the-gauntlet.md docs/schema-evolution.md CHANGELOG.md`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas/run-config.schema.json tools/apd_gauntlet/init_run.py tools/apd_gauntlet/plan_run.py .claude/workflows/apd-gauntlet.js tests docs CHANGELOG.md
git commit -m "feat(run-config): make the domain auditor opt-in via domain_improvement_capture"
```

- [ ] **Step 6 (operator): Compare against the previous accepted state, and measure the saving**

Same as Task 1 Step 6, with the suffix `-ws3t7` and `<prev>` set to the `-ws3t6` runs. The private PBM candidate sets `domain_improvement_capture: true`, so it compares like for like with `<prev>`, where capture always ran. Then record one extra candidate PBM run with the key absent (`runs/<pbm>-ws3t7-off`), and run `usage` on it.
Expected: every `compare-runs` exits 0. The `-off` run has no `apd-domain-auditor` in `usage.yaml` `by_agent`. Record its `totals.cost_usd` saving against the `-ws3t7` PBM median in the PR.

### Task 8: Verbatim excerpts are strict by default

WS1 already scopes the check to `inputs/` artifacts, splits excerpts on `...`/`…` into in-order fragments, and runs it at tier gates and in the whole-run pass. It warns by default; `--strict-excerpts` makes it an error. This task flips the default on `next` and keeps `--no-strict-excerpts` for runs made before 2.0.

A strict error at a tier gate reaches WS1's repair loop. `tier-gate --json` exits 1 with the error under the record file's path, `errorsFromJson` maps it, and `apd-tier-repair` (Task 4) rewrites the excerpt from the artifact. The run halts only if the re-run lens still fails.

Before flipping the default (register A9.16, DEC-18):

- (a) Make the matcher case-insensitive and remove whitespace adjacent to punctuation instead of collapsing it (`normalize_excerpt_text` in `validate.py`), with tests for the two observed false positives: acme `conf-4149d0db` "the client signs…" versus "**The client signs…", and Home Assistant `conf-3060c50e` `{access_token` versus `{\n  access_token`.
- (b) Fix the remaining non-verbatim excerpts in the committed examples (Home Assistant has 23 genuine ones). Absence and summary notes become wholly parenthesised markers.
- (c) Teach that marker rule in `apd-evidence-discipline` ("Evidence").
- (d) Make `test_committed_examples_validate_strict` copy `examples/<e>/inputs` into its temporary run. Today it validates `expected/` without inputs and checks nothing.
- (e) The five WS1 tests that assume the warning default (`test_paraphrase_warns_but_exits_zero`, `test_errors_only_hides_the_warning`, `test_tier_gate_reports_excerpt_violations`, `test_tier_gate_json_carries_the_violation_by_severity`, `test_pathological_input_without_a_match_warns_and_never_fails_a_gate`) pass `--no-strict-excerpts` or are rewritten.
- (f) Structured inputs searched only as whole text (YAML/JSON over 1 MiB, aliases, nesting over 100) keep producing warnings, never errors.

Expected after: `apd-gauntlet validate <copy with inputs> --errors-only --strict-excerpts` exits 0 on all three examples.

**Files:**

- Modify: `tools/apd_gauntlet/validate.py` (`normalize_excerpt_text`, item (a)), `.claude/skills/apd-evidence-discipline/SKILL.md` ("Evidence", item (c)), the committed examples' `expected/` excerpts (item (b))
- Modify: `tools/apd_gauntlet/cli.py` (`validate`: WS1's `--strict-excerpts` flag becomes the pair `--strict-excerpts/--no-strict-excerpts`, default strict, applied to both the tier and the whole-run check; the `tier-gate` and `closeout` commands gain the same pair)
- Modify: `tools/apd_gauntlet/composite.py` (`tier_gate_steps` and `closeout_steps` gain `strict_excerpts`)
- Modify: `tests/test_validate_excerpts.py`. The five WS1 Task 11 tests that assume the warning default, item (e), pass `--no-strict-excerpts` or are rewritten.
- Modify: `docs/running-the-gauntlet.md` (the validate line and WS1's Troubleshooting bullet), `CHANGELOG.md`
- Test: `tests/test_validate_excerpts.py` (new tests after WS1's)

**Interfaces:**

- Consumes:
  - WS1's check and the `strict_excerpts` keyword it accepts;
  - the helpers in `tests/test_validate_excerpts.py`: `_run(tmp_path, tech_plan)`, `_validate(run, *flags)`, `FINDING_EX`, `CAP_EX`;
  - the message `evidence[{i}].excerpt not found verbatim in artifact '{artifact}'`.
- Produces:
  - CLI `validate RUN_DIR [--strict-excerpts/--no-strict-excerpts]`, strict by default. Library defaults inside `validate.py` stay as WS1 set them.
  - `tier_gate_steps(run_dir, tier, *, json_output=False, strict_excerpts: bool = True)` and `closeout_steps(run_dir, record_attempts=None, *, strict_excerpts: bool = True)` append `--no-strict-excerpts` to their `validate` argv when the flag is false.
  - `tier-gate` and `closeout` take the flag pair. The workflow passes neither.

- [ ] **Step 1: Write the failing tests**

```python
PARAPHRASE_PLAN = "Topics are encrypted with broker keys.\n" + CAP_EX

def test_paraphrase_is_an_error_by_default_on_2_0(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE_PLAN))
    assert r.exit_code == 1 and "ERROR" in r.output and "not found verbatim in artifact 'tech_plan.md'" in r.output

def test_no_strict_excerpts_downgrades_to_warning(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE_PLAN), "--no-strict-excerpts")
    assert r.exit_code == 0 and "WARNING" in r.output and "not found verbatim" in r.output

def test_tier_validate_reports_paraphrase_as_json_error(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE_PLAN), "--tier", "10-trustworthiness", "--json")
    errors = json.loads(r.stdout)["errors"]
    assert r.exit_code == 1 and errors[0]["file"].endswith("10-trustworthiness/confidentiality.findings.yaml")

def test_tier_gate_is_strict_by_default_and_honours_the_escape_hatch(tmp_path):
    run = _run(tmp_path, PARAPHRASE_PLAN)
    gate = lambda *f: CliRunner().invoke(main, ["tier-gate", str(run), "--tier", "10-trustworthiness", *f]).exit_code
    assert (gate(), gate("--no-strict-excerpts")) == (1, 0)

def test_composites_forward_the_flag():
    assert tier_gate_steps(Path("r"), "10-trustworthiness", strict_excerpts=False)[-1].argv[-1] == "--no-strict-excerpts"
    assert closeout_steps(Path("r"), strict_excerpts=False)[-1].argv[-1] == "--no-strict-excerpts"
    assert "--no-strict-excerpts" not in tier_gate_steps(Path("r"), "10-trustworthiness")[-1].argv

@pytest.mark.parametrize("example", ["apd-20260601-claim-event-bus", "apd-20260602-acme-mobile-banking",
                                     "apd-20260612-home-assistant"])
def test_committed_examples_validate_strict(example, tmp_path):
    run = tmp_path / example  # item (d): expected/ plus the example's inputs/, so the check has artifacts
    shutil.copytree(REPO / "examples" / example / "expected", run)
    shutil.copytree(REPO / "examples" / example / "inputs", run / "inputs")
    r = _validate(run, "--errors-only")
    assert r.exit_code == 0, r.output
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_validate_excerpts.py -v`
Expected: FAIL (the paraphrase only warns; `No such option: --no-strict-excerpts`).

- [ ] **Step 3: Flip the default, add the pairs, update WS1's warning-default tests and the docs**

The Troubleshooting bullet says excerpts quoting `inputs/` files are errors on 2.0, that the tier gate's `apd-tier-repair` fixes them during a run, and that `--no-strict-excerpts` validates runs made before 2.0. If `test_committed_examples_validate_strict` fails on an `inputs/` excerpt, correct that example's YAML excerpt to the artifact's literal text, 25 tokens or fewer. Leave titles, severities and ids untouched. Make items (a)–(c) and (f) above before flipping the default.

- [ ] **Step 4: Run the full suite**

Run: `pytest -q && mypy tools/ && ruff check tools/ tests/`
Expected: all pass, including `tests/test_examples.py` and `tests/test_validate_example_run.py`.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tools/apd_gauntlet/cli.py tools/apd_gauntlet/composite.py tests/test_validate_excerpts.py .claude/skills/apd-evidence-discipline/SKILL.md examples docs/running-the-gauntlet.md CHANGELOG.md
git commit -m "feat(validate): verbatim-excerpt check is strict by default on 2.0 (--no-strict-excerpts for old runs)"
```

- [ ] **Step 6 (operator): Compare against the previous accepted state, and exercise an excerpt repair**

Same as Task 1 Step 6, with the suffix `-ws3t8` and `<prev>` set to the `-ws3t7` runs. The `<prev>` runs predate the flip, so validate them with `--no-strict-excerpts` wherever a step validates them. Also paraphrase one `inputs/` excerpt in a lens file of a copy of a finished run, and re-invoke.
Expected: every `compare-runs` exits 0. The edited run logs `tier-gate-<tier>` failing with `not found verbatim`, one `repair-…` dispatch to `apd-tier-repair`, and `tier-gate-<tier>-after-repair` passing.

### Task 9: Measure Wave 1 against the 1.7.1 baseline and record it

**Files:**

- Modify: `CHANGELOG.md` (``## Unreleased — 2.0 line (`next`)``, `### Changed`)

**Interfaces:**

- Consumes: Task 1's harness counts; WS2's `usage.yaml` (`totals`, `by_agent`, `by_phase["cli-steps"]`) and `compare-runs --json` (`runs.<path>.cost_usd`).

- [ ] **Step 1: Confirm the static counts**

Run: `pytest tests/test_workflow_dispatch_trace.py -v`
Expected: PASS. Defaults: 17 CLI and 17 LLM dispatches, 5 of them with guard text. With `domain_improvement_capture: true`: 18 and 18.

- [ ] **Step 2 (operator): Run the Task 1 set twice on the WS3 head and summarise usage (milestone exit)**

Run the set as `runs/<x>-ws3-r<k>`, with the private PBM run setting `domain_improvement_capture: true`, plus one extra PBM run with the key absent (`runs/<pbm>-ws3-off`). For each run, run `apd-gauntlet usage runs/<x>-ws3-r<k> --otel telemetry/<x>-ws3-r<k>.otlp.jsonl`. For each example, run `apd-gauntlet compare-runs runs/<x>-baseline runs/<x>-ws3 --gates eval/gates.yaml --json` against the 1.7.1 baseline. Validate the baseline directories with `--no-strict-excerpts` wherever a step validates them.

Expected: `compare-runs` exits 0 for every example. For each example and side, record the median of these values:

- `totals.cost_usd`, plus the input, output and cache tokens;
- `by_phase["cli-steps"]` `requests` and `cost_usd`;
- the `requests` of `general-purpose` against `apd-cli-runner`;
- for the `-off` PBM run, `totals.cost_usd`.

- [ ] **Step 3: Record the deltas**

Add one bullet, "Cost wave 1, measured", with these values:

- CLI dispatches per clean HA-shaped run: 24 (1.7.0; 27 on WS1+WS2) → 17 (18 with capture);
- general-purpose dispatches: 24 → 0;
- always-on description bytes: 16,579 → the Task 5 total;
- per example, the median cost on the 1.7.1 baseline and on WS3 and the percentage change, set against the audit's modelled 10%;
- the `cli-steps` cost on each side;
- the PBM saving from leaving `domain_improvement_capture` off.

- [ ] **Step 4: Lint**

Run: `markdownlint-cli2 CHANGELOG.md`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record measured cost wave 1 dispatch and cost deltas"
```
