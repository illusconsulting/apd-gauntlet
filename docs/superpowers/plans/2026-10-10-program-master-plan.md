# APD Gauntlet 1.7.1 and 2.x Program — Master Implementation Plan

> **For agentic workers:** This plan sequences the program; it does not contain code. Each workstream has its own detailed plan, executed with superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship everything agreed on 2026-10-10:

- the audit's defect fixes as 1.7.1;
- a measured evaluation harness;
- the cost and token waves;
- local apps and optional decision models;
- Terraform, OpenTofu and Atmos evaluation;
- decision-model checks;

all on the 2.0 line, then the code-flow layer on 2.1. Every change lands behind a measured before-and-after comparison.

**Architecture:** Two release lines (RELEASING.md): fixes land on `main` and merge forward; everything else lands on `next`. Each milestone ends in a tagged pre-release that passes the comparison gates against the 1.7.0 baseline. Shared names and interfaces are fixed once, in the registry below, and every detailed plan uses them.

**Tech Stack:** Python 3.10–3.12 engine (`tools/apd_gauntlet`), the Claude Code workflow (`.claude/workflows/apd-gauntlet.js`), the Claude Agent SDK runner (2.0), and external tools: Atmos, OpenTofu, Trivy, Checkov, ShellCheck, Joern, OpenGrep.

**Specs:**

- `docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md` (PR #29)
- `docs/superpowers/specs/2026-10-10-iac-terraform-opentofu-atmos-design.md`
- `docs/superpowers/specs/2026-10-10-code-flow-layer-design.md` (draft, awaiting review)
- The cost and token audit (Claude Doc "APD Gauntlet cost and token audit", 2026-10-10), the source for WS1, WS3, WS5 and WS6.

## Global Constraints

- **Release lines:** per RELEASING.md. Bug fixes go to `main` by PR, then `main` merges into `next`. Features go to `next` by PR. Tags pass `tools/check_release_tag.py`.
- **Versions:** pyproject and `__init__` use PEP 440 (`2.0.0aN`); the plugin manifests use SemVer (`2.0.0-alpha.N`). The test literal moves with each pre-release.
- **CI never touches the network** (ADR-0017). Real-run accuracy is judged locally, and real runs are never committed.
- **Every behaviour-changing task ships behind `compare-runs`** against the baseline, run twice per configuration. These comparison gates are proposals, recorded in `eval/gates.yaml`:
  - no critical or high finding lost unless the loss traces to evidence;
  - severity agrees on at least 90% of matched findings;
  - blocked rate moves by no more than 5 points;
  - first-pass schema validity and retry count no worse than baseline;
  - report audit passes in no more iterations than baseline.
- **Ids are minted by Python only** (ADR-0020); agents emit content.
- **Nothing from a client repository executes.** Every external tool runs through `apd_gauntlet.sandbox.run_tool` (registry §R2).
- **Decision models default to `none`.** Their flags are advisory. Thresholds come from `calibrate` on development labels, frozen before held-out runs.
- **Quality gates:** `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest`, and `markdownlint-cli2` on the linted globs all pass on every PR.

## Review Focus

- **A 1.7 run resumed by a 2.0 runner, or a 2.0 run resumed by 1.7.1.** Both should refuse with a clear message rather than mix formats: `resume-plan` and the ledger record the engine version.
- **A workflow step added in one channel but not the other** (Claude Code workflow versus Agent SDK runner). The parity test must fail. Every plan that adds a phase or CLI step updates both and extends `test_plan_run_phase_names_consistent_with_workflow` (`tests/test_cli_plan_run.py`).
- **An operator who never runs the baseline.** `compare-runs` must refuse to call a candidate "passing" without a baseline directory, rather than compare against nothing.
- **Decision thresholds shipped uncalibrated.** Records must say `calibrated: false`, and flags from uncalibrated thresholds must be labelled as such in the report header.
- **Two consent subjects** (decision model, IaC module fetch). Granting one must not imply the other: `consent.json` is keyed by subject (§R6).

---

## Workstreams

| Id | Workstream | Line | Detailed plan | Depends on |
|---|---|---|---|---|
| WS0 | Release lines | both | Done: PRs #27, #28 | — |
| WS1 | Audit defect fixes → 1.7.1 | `main` | `2026-10-10-ws1-defect-fixes-1.7.1.md` | — |
| WS2 | Measurement and evaluation harness | `next` | `2026-10-10-ws2-measurement-and-evaluation.md` | — |
| WS3 | Cost wave 1 (quick wins) | `next` | `2026-10-10-ws3-cost-wave1-quick-wins.md` | WS1 merged forward, WS2 |
| WS4 | Local apps and decision models | `next` | `2026-10-10-local-apps-plan{1,2,3}-*.md` (PR #29), amended per §A | WS3 (LA2, LA3) |
| WS5 | Cost waves 2–3 (context, determinism, tiering) | `next` | `2026-10-10-ws5-cost-waves2-3-context-and-tiering.md` | WS3, WS2; Wave 3 also needs WS7-IAC4 calibration data |
| WS6 | Decision tasks beyond finding QA (audit wave 4) | `next` | `2026-10-10-ws6-decision-tasks.md` | LA1, WS2 (`calibrate`) |
| WS7 | IaC: Terraform, OpenTofu, Atmos | `next` | `2026-10-10-iac-plan{1,2,3,4}-*.md` | LA1 (consent), LA2 (runner phases) |
| WS8 | Code-flow layer, plus infrastructure-to-code join | `next` (2.1) | CF1–CF4, written after spec approval | WS7, WS2 |
| WS9 | 2.0.0 GA | both | RELEASING.md "2.0.0 GA" | M6 |

## Milestones and releases

| Milestone | Tag | Contents | Exit gate |
|---|---|---|---|
| M1 | `v1.7.1` (`main`) | Baseline captured on 1.7.0; WS1 | WS1 tests green; `compare-runs` 1.7.1 vs 1.7.0 passes the gates |
| M2 | `v2.0.0a1` | Docs PRs merged; WS2; WS3 | Gates pass vs baseline; cost per run measured lower |
| M3 | `v2.0.0a2` | LA1, LA2 (amended) | Runner completes the committed examples with parity; finding QA in shadow |
| M4 | `v2.0.0a3` | LA3; WS5 Wave 2 | Gates pass after each Wave 2 item |
| M5 | `v2.0.0a4` | IAC1–IAC3; WS6 tasks in shadow mode | IaC transformation suite green; IaC fixtures resolve with zero `!exec` executions |
| M6 | `v2.0.0b1` | IAC4; calibration; WS5 Wave 3, one tier at a time; WS6 tasks enabled one at a time | Held-out IaC recall ≥ 1.7 baseline; gates pass per tier; feature freeze |
| M7 | `v2.0.0rc1` → `v2.0.0` | Fixes only; WS9 | RELEASING.md GA checklist |
| M8 | `v2.1.0aN` | WS8 (CF1–CF4) after spec approval | CF4 evaluation vs the 1.7 CBM-only baseline |

**Parallel-safe pairs**, run in separate worktrees:

- WS1 with WS2;
- LA1 with WS3, once WS3 Task 1 (the runner agent) has merged;
- IAC1 with WS5 data-only items (digests and renders).

Everything that edits `.claude/workflows/apd-gauntlet.js` or `runner/flow.py` merges one PR at a time.

---

## Registry: names and interfaces shared across plans

Every detailed plan uses these exact names. A plan that needs a new shared name adds it here in the same PR.

### R1. New CLI commands

| Command | Owner | Contract |
|---|---|---|
| `resume-plan <run-dir> --json` | WS1 | Prints `{"engine_version": str, "steps": [{"label": str, "complete": bool, "reason": str}]}`. Exits 0 and writes nothing. The workflow and runner skip steps marked complete; LLM prompts carry no guard text. |
| `prepare-run <run-dir> [--domain …]` | WS3 | Composite of scaffold `validate`, `build-domain-skill` and `validate-domain`, keeping their exit codes. Named `prepare-run`, not the audit's `setup`, because LA3 owns `apd-gauntlet setup`. |
| `tier-gate <run-dir> --tier <dir>` | WS3 | Composite: canonicalize the tier, then `validate --tier`. Exit 0 clean, 1 schema errors. |
| `post-tier4 <run-dir>` | WS3 | Composite: `assemble-c4`, tmeval canonicalize, `rollup`. |
| `closeout <run-dir>` | WS3 | Composite: dimpr canonicalize, `summarize`, final `validate`. |
| `compare-runs <baseline> <candidate> [--json] [--gates eval/gates.yaml]` | WS2 | A deterministic delta. Exits 0 when every gate passes, 1 when any fails, 2 on usage errors or a missing baseline. |
| `usage <run-dir> --otel <file>` | WS2 | Summarises tokens and cost per agent and phase from OpenTelemetry `claude_code.api_request` events into `<run-dir>/.apd-state/usage.yaml`. |
| `eval run <corpus.yaml> --set dev\|heldout --evaluator <name>` | WS2 | Runs a registered evaluator and writes `eval/results/<evaluator>/<set>-<timestamp>.yaml`. |
| `calibrate <task> --labels <file> --target-precision <p>` | WS2 | Writes or updates `tools/apd_gauntlet/data/decide/thresholds.yaml` entry `<task>: {threshold, precision, recall, n, labels_sha256, calibrated: true}`. |
| `metamorphic run --suite <name>` | WS2 | Generic invariance harness. Suites register transformations (IAC4: T1–T8; CF4 adds its own). |
| `xref-digest <run-dir> --before <tier-dir>` | WS5 | Writes `40-synthesis/digests/xref-<tier>.yaml`. |
| `report-digest <run-dir>` | WS5 | Writes `40-synthesis/digests/report.yaml`. |
| `edge-review <run-dir>` | WS5 | Writes `40-synthesis/edge-review.yaml` (heuristic edges only). |
| `tm-candidates <run-dir>` | WS5 | Writes `40-synthesis/tm-candidates.yaml` (the Python join of TM entries and findings). |
| `render <run-dir> --artifact <name>` | WS5 | Renders markdown from YAML for `threat-model-authored`, `attack-path-report`, `threat-model-coverage-report` and `advisory-report`. |
| `build-lens-skills <run-dir>` | WS5 | One compiled skill packet per lens, under `.claude/skills/apd-domain/lens/<goal>.md`. |
| `decide <task> <run-dir>` | LA1 | Task registry `apd_gauntlet.decide.tasks`. LA1 owns `finding-qa`. WS6 adds `cluster-pairs`, `report-claims`, `tm-screen`, `asset-match`, `intake-score`, `input-screen` and `iac-triage`. |
| `iac run <run-dir>` / `iac consent <run-dir>` | IAC1 | Per the IaC spec. |
| `code-flow run <run-dir>` | CF1 | Per the code-flow spec. |

### R2. Shared Python modules

- **`apd_gauntlet.sandbox.tools`** (created by IAC1; refines the IaC spec's `iac/tools.py` location so CF1 can reuse it):
  - `run_tool(tool: str, args: list[str], *, cwd: Path, network: bool = False, timeout_s: int) -> ToolResult`, where `ToolResult` is `(returncode: int, stdout: str, stderr: str, duration_s: float)`;
  - `register_invocation(tool: str, validator: Callable[[list[str]], None]) -> None`;
  - `ToolNotAllowed(Exception)`.
- **`apd_gauntlet.context.select`** (created by IAC3; reused by CF3): `select_packet(graph: TypedGraph, seeds: dict[str, float], params: ContextParams) -> Packet`, with `ContextParams` loaded from `data/<domain>/context-params.yaml`.
- **`apd_gauntlet.validate` evidence-index registry** (created by IAC2): `EVIDENCE_INDEXES: dict[str, EvidenceIndexSpec]`, keyed by filename (`code-evidence-index.yaml`, `iac-evidence-index.yaml`, `iac-graph.yaml`, later `code-flow-index.yaml`), with `EvidenceIndexSpec(schema: str, locator_re: str, id_field: str)`. The existing code-evidence handling moves behind it unchanged.
- **`apd_gauntlet.eval.evaluators`** (created by WS2): `register(name: str, fn: Callable[[CorpusEntry, Labels], EvalResult])`.

### R3. Phases

The workflow's `meta.phases` and `runner.flow.PHASES` stay equal at every commit. Phases are added in this order:

- `iac`, after `setup` and before `intake` (IAC1);
- `code-flow`, after `code-recon` and before `threat-model-author` (CF1).

WS3 renames no phase. The `setup` phase runs `prepare-run`.

### R4. Run-config keys (all optional, additive)

| Key | Owner |
|---|---|
| `decision_model` | LA1 |
| `domain_improvement_capture: false` | WS3 |
| `infrastructure.static.atmos`, the object form of `infrastructure.static.terraform`, `infrastructure.modules`, `infrastructure.plans`, `infrastructure.require_tools` | IAC1 |
| `code_flow`, `repos[].deploys_as` | CF1 |

### R5. Agent frontmatter

- Every agent sets `model` and `effort`. WS3 adds `effort` everywhere and keeps today's models; WS5 Wave 3 changes models one tier at a time.
- New agent `apd-cli-runner` (WS3): tools `Bash` only, `model: haiku`, `effort: low`. `pyStep()` dispatches with `agentType: 'apd-cli-runner'`.

### R6. State files under `runs/<id>/.apd-state/`

`consent.json` is a JSON object keyed by subject:

```json
{
  "decision_model": {"provider": "…", "model": "…", "granted_at": "…", "method": "…"},
  "iac_module_fetch": {"sources": ["…"], "sources_sha256": "…", "granted_at": "…", "method": "…"}
}
```

LA1's `has_consent` and `record_consent` read and write the `decision_model` subject (§A1). IAC1 adds `has_fetch_consent(run_dir, sources)` and `record_fetch_consent(run_dir, sources, method)`.

### R7. Schemas (new or changed, all additive)

| Schema | Change | Owner |
|---|---|---|
| `decision-record` | New | LA1 |
| `iac-evidence-index` | New | IAC1 creates the skeleton; IAC2 completes it |
| `iac-graph` | New | IAC3 |
| `finding` | Gains `alternatives_considered` | IAC3 |
| `asset-graph` | Provenance gains `iac_evidence` | IAC3 |
| `asset-graph` | Provenance gains `code_flow` | CF3 |
| `domain` | Gains `consumers` per calibration file | WS5 |
| `eval-labels`, `eval-corpus` | New | WS2 |
| `code-flow-index` | New | CF1 |

Each change gets a dated entry in `docs/schema-evolution.md`.

### R8. Data files

- `tools/apd_gauntlet/data/decide/thresholds.yaml` (WS2 writes; LA1, WS6 read)
- `tools/apd_gauntlet/data/iac/` (WS7)
- `tools/apd_gauntlet/data/codeflow/` (WS8)
- `eval/` at the repo root, not packaged: corpora manifests, labels, gates and local results (results are gitignored)

---

## §A. Amendments to existing plans (make before executing the affected plan)

- **A1. LA1 Task 6.** `record_consent`/`has_consent` read and write `consent.json["decision_model"]` (R6). Finding-QA thresholds load from `data/decide/thresholds.yaml`. The proposal values ship as `calibrated: false` entries, and every decision record copies `calibrated`.
- **A2. LA2 Tasks 3, 6 and 7.**
  - The step table uses WS3's composite commands (`prepare-run`, `tier-gate`, `post-tier4`, `closeout`) and WS1's `resume-plan` semantics.
  - The repair dispatch reuses WS1's repair prompt template (`tools/apd_gauntlet/data/prompts/repair.md`).
  - Agent specs read `model` and `effort` from frontmatter (R5).
- **A3. LA3 Task 3.** `doctor` gains checks for the WS7 tools once IAC1 lands. LA3 leaves a `register_doctor_check(name, fn)` hook that IAC1 and CF1 call.
- **A4. IaC spec.** Done in this branch:
  - raw-read fallback for unresolved roots (§9);
  - 1.7 baseline in the evaluation (§13.2);
  - infrastructure-to-code join noted as an open item (§16).

---

## Task 1: Capture the 1.7.0 baseline (operator)

**Files:** none committed. Run directories stay local, under `runs/` (gitignored).

- [ ] **Step 1: Configure telemetry.** In the shell that launches Claude Code, export:
  - `CLAUDE_CODE_ENABLE_TELEMETRY=1`
  - `OTEL_LOGS_EXPORTER=otlp` (or `console`, redirected to a file)
  - `OTEL_LOG_TOOL_DETAILS=1`

  Custom agents report as `custom` without the last one.
- [ ] **Step 2: Run the baseline set twice each on 1.7.0:** the three committed examples (`examples/apd-20260601-claim-event-bus`, `examples/apd-20260602-acme-mobile-banking`, `examples/apd-20260612-home-assistant`), plus one private PBM run. Keep each run directory and its telemetry export under a name ending `-baseline-r1` or `-baseline-r2`.
- [ ] **Step 3: Verify.** Each run directory passes `apd-gauntlet validate <run-dir>`, and each telemetry file contains `claude_code.api_request` events. Expected: "Clean." for every run; a non-empty event count for every file.

## Task 2: Execute WS1 and release 1.7.1

- [ ] **Step 1:** Execute `2026-10-10-ws1-defect-fixes-1.7.1.md` on a branch from `main`, one PR per task group the plan names.
- [ ] **Step 2:** Rerun Task 1's set on the 1.7.1 candidate. Once WS2 Task "compare-runs" exists, run `apd-gauntlet compare-runs <baseline> <candidate> --gates eval/gates.yaml` for each pair. Expected: exit 0 for each.
- [ ] **Step 3:** Bump to 1.7.1 per RELEASING.md "Cutting a stable 1.7.x release". Tag and push. Expected: the release gate prints `prerelease=false, make_latest=true`.
- [ ] **Step 4:** Merge `main` into `next`, keeping `next`'s version values. Expected: CI green on `next`.

## Task 3: Merge pending docs and release-line PRs

- [ ] **Step 1:** Merge #27 into `main`, then `main` into `next`, then #28 into `next`.
- [ ] **Step 2:** Merge #29 into `next`, then this branch (IaC spec, code-flow draft, program plans).
- [ ] **Step 3:** Apply amendments A1–A3 to the LA plan files in one docs PR. Expected: `markdownlint-cli2` clean.
- [ ] **Step 4 (administrator):** Protect `next`, and add the `v*` tag ruleset.

## Task 4: M2 — WS2 and WS3, then `v2.0.0a1`

- [ ] **Step 1:** Execute the WS2 plan. Expected: `compare-runs` and `usage` work on the Task 1 baselines.
- [ ] **Step 2:** Execute the WS3 plan, one PR per task. After each behaviour-changing task, run the Task 1 set twice and `compare-runs`. Expected: every gate passes, and `usage` shows per-run cost at or below baseline.
- [ ] **Step 3:** Cut `v2.0.0a1` per RELEASING.md "Cutting a 2.0 pre-release". Expected: the gate prints `prerelease=true, make_latest=false`.

## Task 5: M3 — LA1 and LA2, then `v2.0.0a2`

- [ ] **Step 1:** Execute LA1, as amended by A1. Turn finding QA on in shadow mode (decision records written, nothing acted on).
- [ ] **Step 2:** Execute LA2, as amended by A2. Expected: `apd-gauntlet run` completes each committed example. The parity test asserts `runner.flow.PHASES == meta.phases`.
- [ ] **Step 3:** Run `compare-runs` on the workflow and runner outputs for the same example. Expected: gates pass, so runner output is equivalent.
- [ ] **Step 4:** Cut `v2.0.0a2`.

## Task 6: M4 — LA3 and WS5 Wave 2, then `v2.0.0a3`

- [ ] **Step 1:** Execute LA3, as amended by A3.
- [ ] **Step 2:** Execute the Wave 2 part of WS5 in the plan's order (digests and renders first), with `compare-runs` after each item. Expected: gates pass; `usage` shows the per-item saving.
- [ ] **Step 3:** Cut `v2.0.0a3`.

## Task 7: M5 — IAC1–IAC3 and WS6 shadow mode, then `v2.0.0a4`

- [ ] **Step 1:** Execute IAC1, IAC2 and IAC3 in order. Expected:
  - the transformation suite and the security tests (`!exec` canary, outside include, argument allowlist) pass in CI;
  - a manual run on one private Atmos repository completes.
- [ ] **Step 2:** Execute WS6 with every task in shadow mode.
- [ ] **Step 3:** Cut `v2.0.0a4`.

## Task 8: M6 — evaluation, calibration, tiering; `v2.0.0b1` and feature freeze

- [ ] **Step 1:** Execute IAC4. Label the development and held-out corpora, run the 1.7 raw-read baseline and the new path, then tune and freeze the context parameters. Expected: held-out recall of labelled issues ≥ baseline.
- [ ] **Step 2:** Run `calibrate` for `finding-qa` and each WS6 task on the development labels, with target precision 0.98. Then enable tasks one at a time: finding QA first, then `cluster-pairs`, `report-claims`, `asset-match`, `tm-screen`, `intake-score`, `input-screen`, `iac-triage`. Run `compare-runs` after each. Expected: gates pass.
- [ ] **Step 3:** Execute the Wave 3 part of WS5, one tier of lenses at a time, report writer last, with `compare-runs` after each. Expected: gates pass, or the tier reverts to its previous model.
- [ ] **Step 4:** Cut `v2.0.0b1`. Feature freeze on `next` until GA.

## Task 9: M7 — release candidate and 2.0.0 GA

- [ ] **Step 1:** Fix-only PRs on `next`; cut `v2.0.0rc1`; test the plugin and engine installed from it.
- [ ] **Step 2:** Follow RELEASING.md "2.0.0 GA":
  - `release/1.7`;
  - the marketplace renames;
  - remove the pre-release notices;
  - merge `next` into `main`;
  - tag `v2.0.0`.

  Expected: the gate prints `make_latest=true`; `pip install apd-gauntlet` resolves 2.0.0.

## Task 10: M8 — code-flow layer (2.1)

- [ ] **Step 1:** Review and approve `2026-10-10-code-flow-layer-design.md`, resolving its §13 open questions.
- [ ] **Step 2:** Write CF1–CF4 with superpowers:writing-plans, using registry R2 (`run_tool`, `select_packet`, `EVIDENCE_INDEXES`) and R3 (the `code-flow` phase).
- [ ] **Step 3:** Execute CF1–CF4. Gate on CF4's evaluation against the 1.7 CBM-only baseline.

---

## Operator work outside the code

- **Baseline capture** (Task 1) and every `compare-runs` rerun: about 8 gauntlet runs per behaviour-changing change.
- **Labelling:**
  - about 200 cluster pairs (WS6);
  - finding goal and severity labels from the committed examples (WS2);
  - IaC corpus labels (IAC4);
  - code-flow labels (CF4).

  All local, per ADR-0017.
- **Live fixture recording** for decision providers (LA1 Task 9) needs real keys.
- **Hosting decision for Clef** on SmithRx reviews: Workers AI only if SmithRx's Cloudflare agreements cover it, otherwise self-hosted. Needed before any decision task runs on a SmithRx review.
- **Repository administration:** branch protection and the tag ruleset (Task 3).

## Risks

- **Workflow merge conflicts.** WS3, WS5, LA2, IAC1 and CF1 all edit the workflow and runner flow. Mitigation: one PR at a time on those files, with the parity test as the tripwire.
- **Measurement noise.** Two runs per configuration may not separate noise from regressions on small effects. If gates flap, raise to three runs and gate on the median.
- **Labelling effort** is the long pole for M6. Start IaC and cluster-pair labelling during M4.
- **Tier-3 model moves** may raise audit iterations. Wave 3 reverts per tier on gate failure.
- **External tool churn** (Trivy and Checkov rules, Atmos flags). Versions are pinned, and evaluations rerun on every upgrade.
