# APD Gauntlet Consolidated Execution Plan (state on 2026-10-14, updated 2026-10-17)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take every improvement defined on the repository's branches and in the apd-gauntlet project (1.7.1 defect fixes, measurement, cost waves, Sonnet/Haiku tiering, local apps, Clef and Jev decision models, Terraform/OpenTofu/Atmos evaluation, the threat catalog, the code-flow layer and the backlog found on 2026-10-14) from its current state to shipped releases: `v1.7.1`, `v2.0.0` and `v2.1.0`.

**Architecture:** This plan sits on top of the program master plan and the per-workstream plans on `next`. It does not repeat their code-level steps. It adds three things they lack: (1) the verified state of every branch and plan on 2026-10-14; (2) the amendments those plans need before execution, collected in the companion file `2026-10-14-amendments-register.md`; (3) new tasks for gaps no plan covers, written in full in Part G. Phases follow the master plan's milestones M1–M8, with each step ending in a command and the output that proves it.

**Tech Stack:** Python 3.10–3.12 engine (`tools/apd_gauntlet`), the Claude Code workflow (`.claude/workflows/apd-gauntlet.js`), the Claude Agent SDK runner (`claude-agent-sdk`), Textual and Starlette for the local apps, the System One decision API (Cloudflare Clef, TypeSafe Jev, OpenRouter Jev, self-hosted SGLang), and pinned external tools (Atmos, OpenTofu, Trivy, Checkov, ShellCheck, Joern, OpenGrep).

**Spec and inputs** (executors read these with this plan):

- Master plan: `docs/superpowers/plans/2026-10-10-program-master-plan.md` on `next` (registry R1–R10, amendments A1–A6, milestones M1–M8).
- Amendments register (companion to this plan): `docs/superpowers/plans/2026-10-14-amendments-register.md` (A1–A3 made concrete, A7–A15).
- Specs on `next`: `docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md`, `2026-10-10-iac-terraform-opentofu-atmos-design.md`, `2026-10-10-code-flow-layer-design.md` (draft), `2026-10-11-threat-catalog-integration-design.md`.
- Detailed plans on `next` (186 tasks): WS1, WS2, WS3, WS5, WS6, LA1–LA3, IAC1–IAC4, CAT1–CAT4 under `docs/superpowers/plans/2026-10-1{0,1}-*.md`.
- Implementation branch: none open; WS1 merged in #49 and shipped in v1.7.1 (A15.4).
- Project context: the Clef decision-model analysis and cost audit (2026-10-10), the threat catalog build (catalog 1.1.0, 2026-10-13), and the owner's standing requirements (Sonnet/Haiku tiering; optional Cloudflare, Jev or OpenRouter key or no decision model; local CLI/TUI/web; two release lines; IaC via static analysis plus optional plan JSON, remote modules only behind consent).

**How the documents relate.** Where this plan and an older plan disagree, this plan wins on sequencing, and the amendments register wins on the content of a task. A detailed plan's task is executed only after every register entry that names it has been applied (Phase 2). Line numbers in the 2026-10-10/11 plans predate WS1; locate every edit by its anchor (function name, label, heading), never by line number.

## Global Constraints

- **Release lines** (RELEASING.md): fixes go to `main` by PR and merge forward into `next`; features go to `next` by PR. Tags are `v` + the PyPI string and must pass `python tools/check_release_tag.py --tag <tag>`.
- **Versions:** PEP 440 in `pyproject.toml` and `tools/apd_gauntlet/__init__.py` (`2.0.0aN`); SemVer in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (`2.0.0-alpha.N`); the literal in `tests/test_workflow_apd_gauntlet.py::test_plugin_manifest_version_matches_pyproject` and its message move together.
- **No network in CI** (ADR-0017). Real runs, telemetry exports and labels stay local: `runs/`, `telemetry/`, `eval/local/`, `eval/results/` are never committed.
- **Ids are minted by Python only** (ADR-0020); agents emit content.
- **Nothing from a client repository executes.** Every external tool runs through `apd_gauntlet.sandbox.tools.run_tool`; no tool may fetch a module, include or provider without a recorded consent subject in `.apd-state/consent.json`.
- **Decision models default to `none`;** every WS6 task defaults to `off`; finding QA defaults to `shadow` when a provider is set. Auto-decisions use only `calibrate`d thresholds keyed by provider, model and weights revision; uncalibrated thresholds never auto-decide.
- **No HITRUST content** in any vendored file, fixture, output or doc (catalog 1.1.0 removed it).
- **Quality gates on every PR:** `ruff check tools/ tests/`, `mypy tools/`, `pytest -q` with the venv's `bin` on `PATH`, `apd-gauntlet lint-agents --agent-dir .claude/agents/`, `apd-gauntlet lint-skills --skill-dir .claude/skills/`, and `markdownlint-cli2` on the CI globs. CI excludes `docs/superpowers/plans/**`, so a PR that edits a plan file lints it explicitly: `npx --yes markdownlint-cli2 <plan files>`.
- **One-at-a-time files:** every PR that edits `.claude/workflows/apd-gauntlet.js`, `tools/apd_gauntlet/runner/flow.py`, `tools/apd_gauntlet/report/transform.py` or the report bundle merges alone, then the next rebases. The parity tests (`tests/test_cli_plan_run.py::test_plan_run_phase_names_consistent_with_workflow`, LA2's `tests/runner/test_flow_parity.py::test_phases_match_workflow`) are the tripwire.
- **Bundle sync:** after LA2 Task 1 lands, every task that edits an agent, skill or template ends with `python -I -m apd_gauntlet.bundle --sync` and commits the packaged copies.
- **Comparisons:** every behaviour-changing PR group runs `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-<cand> --gates eval/gates.yaml --strict` on the baseline set (its size is DEC-35), two runs per configuration (three, gated on the median, in WS5 Wave 3). Milestone exits compare against the 1.7.1 baseline (Task 0.4) without `--strict`: the 1.7.0 runner cannot run on current Claude Code, so no 1.7.0 live run exists, while offline engine-only comparisons against the 1.7.0 engine (Appendix 1) stay valid (register A15.1). Measured runs use the same Claude Code version (≥ 2.1.273), provider and session model as `<prev>`, with `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` and `CLAUDE_CODE_EFFORT_LEVEL` unset. A run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or in a new session: `Workflow({name: "apd-gauntlet"})` runs the copy registered when the session started (A15.12).
- **External tool floors:** OpenTofu ≥ 1.12.6 (tested 1.13.1), Trivy ≥ 0.71.1 (tested 0.75.0), Atmos ≥ 1.231.0 (tested 1.232.0), Checkov ≥ 3.3.26 (tested 3.3.29), ShellCheck ≥ 0.9 (tested 0.11.0), python-hcl2 `>=7,<8`.
- **Python dependency pins:** `claude-agent-sdk>=0.2.167,<0.3`, `textual>=8.2,<9`, `starlette>=1.0,<2`, `httpx>=0.27,<1`, `keyring>=25.7,<26`, dev `pytest-asyncio>=1.0` with `asyncio_mode = "auto"`.
- **Master-plan gate text is a fixture.** WS2 Task 5 reads the five gate bullets in `docs/superpowers/plans/2026-10-10-program-master-plan.md`; never move or reword them.
- **Execution:** superpowers:subagent-driven-development for every plan (fresh implementer and reviewer per task, controller ledger of rulings). Implementers commit only to local feature branches. Every push, tag, branch deletion, PR merge, repository setting and release is an owner action, marked **(owner)** in the steps below.
- **Client data never enters the repository.** Ledgers, PR descriptions and committed docs carry only gate ids, pass/fail and aggregate numbers for private runs; full `compare-runs`, `usage` and decision output stays under `runs/` and `~/apd-telemetry/`.

## Review Focus

The five inputs most likely to bite a user that no existing task tested on 2026-10-14. Each has a test in the task named.

1. **A symlink in `inputs/` that points outside it** (for example `inputs/keys -> ~/.ssh`). Today `init-run` exits 0 and copies the target's content into the run (reproduced on `main`). Expected: exit 1 naming the link, nothing copied. Pinned by N1 `test_escaping_dir_link_refused` and `test_escaping_file_link_refused`.
2. **A hostile IaC module source** (`source = "http://127.0.0.1:<port>/m.zip"`, or a transitive module behind a consented one). Go tools bypass the closed proxy for loopback, and Trivy downloads remote modules by itself. Expected: no connection and no fetch without consent for that exact source. Pinned by A13.8 `test_scanners_never_contact_module_sources` and A13.7 `test_transitive_source_not_consented_rolled_back`.
3. **Plugin and engine out of step during a release.** The 1.7.1 workflow halts on any engine without `resume-plan`, and the 2.0 workflow must not tell users to install `<2`. Expected: release the engine in the same session as the plugin change; the 2.0.0a1 bump rewrites the upgrade message. Pinned by A8.6's test edits in `tests/test_workflow_apd_gauntlet.py`.
4. **A decision threshold reused with a different model or provider** (calibrated on Clef, run on Clef-flash or Jev). Expected: every item escalates, with a warning. Pinned by A12.6 `test_threshold_for_other_model_never_autos`.
5. **A WS5 Wave 3 measurement taken under drifting session conditions** (Bedrock alias to Sonnet 4.5, or an environment override of model or effort). Expected: the gate fails rather than passing a tier that never ran on the intended model. Pinned by N10 `test_expect_model_fails_on_mismatch`.

---

## Part A — Branch analysis (state on 2026-10-17)

Verified on 2026-10-14 from a full clone of `illusconsulting/apd-gauntlet` with every branch and every `refs/pull/*/head`, and from the local checkout at `~/Documents/GitHub/apd-gauntlet` (then on `fix/ws1-1.7.1` at `d7de88e`, clean; local `main` equal to `origin/main` at `bc0a661`). Updated on 2026-10-17 after the 1.7.1 release (register A15.4).

| Branch | Tip | Relative to `main` | What it holds | Verdict |
|---|---|---|---|---|
| `main` | `0145775` (merge of #51) | — | The 1.7 line at 1.7.1: #49 (WS1 Tasks 1–11, N1, N3), #50 (the runner awaits every dispatch; cross-file references resolve per record kind; register A15.1–A15.3), #51 (the 1.7.1 release). Tag `v1.7.1` is on `0145775`; PyPI lists 1.7.0 and 1.7.1; the release is marked Latest. Not protected. | Stable line. Next: the 1.7.2 candidates (Task 1.9). |
| `next` | `ad9ec66` (merge of #52) | Contains `main` (merged forward by #52) | The 2.0 integration branch, at 1.7.1 in all five version places; #48 applied A14.7. Protected by ruleset `next-protection-rules`: a pull request with 1 approval; required checks `test (3.10)`, `test (3.11)`, `test (3.12)`, `wheel-smoke`, `bundle-rebuild-diff`, `validate-example`, `plugin-manifest`; no force-push or deletion. | **No 2.0 implementation has started.** Phase 2 starts here. |
| `fix/ws1-1.7.1`, `fix/workflow-await-dispatches`, `chore/release-1.7.1`, `chore/merge-1.7.1-into-next` | — | Merged (#49, #50, #51, #52) | WS1, the await and cross-file fixes, the release, the merge-forward. | Merged; can be deleted **(owner)**. |
| `fix/report-freshness-gate`, `feat/plugin-channel-guardrails` | — | — | Guardrail spec PRs B and A (squash-merged as #9 and #10). | Deleted. |
| `docs/amendments-2026-10-14` | from `next` `ad9ec66` | — | This plan's Phase 2 docs PR (amendments register, Part G tasks). | Local; Phase 2. |

**Pull requests.** All 47 heads were checked by content on 2026-10-14. #27–#31, #33, #34 and #47 are merge commits on `main` or `next`; #6–#14, #21–#23, #25, #32, #41, #42 and #44–#46 were squash-merged; the remaining dependabot heads (#1–#5, #15–#20, #24, #26, #35–#40, #43) are superseded by later bumps on `main`. GitHub's API was not reachable from the analysis session, so PR state was inferred from content. Since then: #48 (A14.7 applied on `next`), #49 (WS1 + N1 + N3 into `main`), #50 (the await and cross-file fixes, register A15.1–A15.3), #51 (the 1.7.1 release: version bump, CHANGELOG per A8.7/N2, RELEASING note per A8.4, domain skill restamp), #52 (Task 1.8 merge-forward with the A8.4 CHANGELOG rewording). Nothing is pending outside the `next` plans and this docs branch. The owner merges plan PRs into `next` by bypassing the ruleset's approval rule.

**WS1 deviations from its plan** (all on the branch, all sound; the register records them): `apd-tier-repair` ships on 1.7 (A6); the excerpt check is hardened against hostile YAML (20 MiB skip, no parse over 1 MiB, 100,000-scalar and 4 MiB caps, aliases or depth over 100 searched as text); a 1.7.1 workflow on an engine without `resume-plan` **halts** with `pip install --upgrade "apd-gauntlet>=1.7.1,<2"` instead of falling back; always-run steps offer no skip; `inferred_apd_goals` stays agent-authorable; the work is one branch rather than PR groups A–G; no `compare-runs` step ran because the command does not exist yet.

## Part B — Improvement inventory

Every improvement defined on a branch, in a plan or spec, or in the project, with its state and where this plan lands it.

| # | Improvement | Defined in | State on 2026-10-14 (updated 2026-10-17) | Lands in |
|---|---|---|---|---|
| 1 | Report-freshness gate (guardrail PR B) | `fix/report-freshness-gate`, spec 2026-07-14 | Done (#9); branch deleted | — |
| 2 | Plugin-channel guardrails (PR A) | `feat/plugin-channel-guardrails` | Done (#10); branch deleted; agent `tools` lint never added | N18 |
| 3 | CAPEC bridge, ATT&CK detection overlay, compliance projections | specs 2026-06-14 | Done in v1.7.0 (#110); spec status lines corrected by N3 in 1.7.1; versions unrecorded; thin HIPAA/CSF crosswalks | N17; N22 |
| 4 | Two release lines (WS0) | PRs #27, #28 | Done; `next` protected by ruleset `next-protection-rules`; `main` unprotected and no `v*` tag ruleset yet | Task 0.2 Step 1 |
| 5 | Audit defect fixes (WS1) | `fix/ws1-1.7.1`, WS1 plan | Released in v1.7.1 (#49; release PR #51) | Phase 1 (done) |
| 6 | `init-run` refuses escaping symlinks | Found 2026-10-14; owner noted it in the local-apps review | Fixed in v1.7.1 (N1, `5bb52ec`, in #49) | Phase 1 (done) |
| 7 | Measurement and evaluation harness (WS2) | WS2 plan | Not started; 7 amendments | Phase 3 |
| 8 | Cost wave 1 (WS3) | WS3 plan, cost audit | Not started; 9 amendments | Phase 3 |
| 9 | Optional decision models: Cloudflare Clef, TypeSafe Jev, OpenRouter Jev, or none (LA1) | Local-apps spec, LA1; owner requirement | Not started; A1 not applied; provider facts changed | Phase 4 |
| 10 | Agent SDK runner (LA2) | LA2 | Not started; step tables stale against WS1 and WS3 | Phase 4 |
| 11 | Local CLI, TUI and web (LA3) | LA3; owner requirement | Not started | Phase 5 |
| 12 | Context and determinism, Wave 2 (WS5 Tasks 1–15) | WS5, cost audit | Not started | Phase 5 |
| 13 | Run effectively on Sonnet and Haiku (WS5 Wave 3) | WS5 Tasks 16–23; owner requirement | Not started; three agents stay on Opus; no model provenance; revert rule conflicts with Task 23 | Phase 7; N10–N16 |
| 14 | Decision tasks beyond finding QA (WS6, "Wave 4: Clef as a decision layer") | WS6 | Not started | Phase 6 (shadow), Phase 7 (enable) |
| 15 | Clef opportunities no plan covers: self-hosted endpoint, AI Gateway, diagram checks, per-task model, cache, spend in `usage`, escalate-on-doubt | Clef analysis, verification 2026-10-14 | Unplanned | N5–N9; A12 |
| 16 | Terraform, OpenTofu and Atmos evaluation (WS7) | IaC spec, IAC1–IAC4; owner requirement | Not started; two consent holes; vulnerable tool floors | Phases 6–7; A13 |
| 17 | Threat catalog as an enrichment layer (WS10) | Catalog spec, CAT1–CAT4 | Not started; written for catalog 1.0.0; 1.1.0 removed HITRUST | Phases 5–7; A7; Part I |
| 18 | Code-flow layer (WS8) | Draft spec | Awaiting approval; CF1–CF4 unwritten | Phase 9 |
| 19 | Healthcare / clinical-FHIR domain pack (FHIR remediation W4) | FHIR benchmark remediation | Never landed; no pack covers FHIR or HL7 | N22 |
| 20 | Real pre-dedup counts (FHIR remediation W3a) | `synthesis/metrics.py` | Counts equal deduped length | N20 |
| 21 | `manual-audit-prompts` wired into a run (FHIR remediation W1a) | `cli.py` | Command orphaned | N19 |
| 22 | Code-recon index coverage and minimum codebase-memory-mcp | ADR-0019, docs promises | Docs recommend v0.10.8 (N3, 1.7.1); coverage capture and the zero-entry warning text not started (14 of 23 repos on Home Assistant) | N21 |
| 23 | Knowledge-base versions recorded (ATT&CK, CAPEC, CWE) | Detection and CAPEC specs, catalog spec §10.3 | `attack_version: "unknown"`; no CAPEC/CWE version | N17 |
| 24 | PEP 639 licence metadata before 2027-02-18 | RELEASING.md "Known follow-up" | Not started; N4 due before 2027-01-31 | N4 (1.7.2) |
| 25 | CHANGELOG completeness for 1.7.0 and 1.7.1 | Repo history | Done in 1.7.1 (#51, A8.7/N2); next's version bullet reworded in #52 (A8.4) | Phase 1 (done) |
| 26 | FHIR remediation W2 (assumption citations), W5 (live infrastructure) | FHIR remediation | W2 unscoped; W5 is an IaC spec non-goal | Phase 10 backlog |
| 27 | Deterministic Kubernetes, Helm and Istio checks; detection overlay v2 | Backlog | Unplanned | Phase 10 backlog |
| 28 | Gap list from the Cloudflare and Anthropic security skill-library comparison | Owner's earlier analysis | Not recorded anywhere in the repo or project | DEC-27 (owner supplies) |
| 29 | The workflow runner awaits every dispatch (the 1.7.0 runner cannot run on current Claude Code) | Found 2026-10-15–17 (register A15.1, A15.2) | Fixed in v1.7.1 (#50); tripwire `tests/test_workflow_runner_awaits.py` | Phase 1 (done); A15.21 for later workflow edits |
| 30 | The whole-run cross-file gate resolves `cross_references` and `merged_from` per record kind (capability-to-capability references halted runs before synthesis) | Found 2026-10-15–17 (register A15.3) | Fixed in v1.7.1 (#50) | Phase 1 (done); A15.3 for CAT2 T7, CAT3 T8 |

## Part C — What changed after the plans were written

These facts drive the amendments. Each is verified (command or source in the register).

- **WS1 was executed** on one branch, with the deviations listed in Part A. Downstream plans cite pre-WS1 line numbers and names: the tier gate is now `tierGate()` plus `repairTierGate()`, canonicalize runs inside `regate()`, `_validate_context_rollups` became `_validate_rollups`/`_ROLLUP_TABLES`, `schema_for_run_file` is the shared schema lookup, `_plan` already exists in `tests/test_cli_plan_run.py`, there are 22 agents, and the workflow grew from 850 to 1,111 lines.
- **`next` carries version 1.7.1** in all five version places since #52, the merge-forward of 1.7.1 (A8.4, A15.7); "keep next's values" applies only after `2.0.0a1`.
- **Threat catalog 1.1.0** (2026-10-13) removed every HITRUST field (`source`, `hitrust`, `hitrust_crosswalk`, `$defs.normalization`); 367 threats, 25 families, ids and about 9,800 mappings are unchanged; `catalog.counts` is exactly `threats`, `families`, `mappings`. The open/full stub design is obsolete (A7). `illusconsulting/threat-catalog` is not publicly reachable and no release exists. ATT&CK v20.0 shipped 2026-10-13; the catalog maps v19.2.
- **Decision-model facts** (2026-10-14): hosted Clef-flash context is 24,576 tokens and Clef-omni 64,000; no Workers AI page lists a Jev route (`typesafe/jev` is dropped); Jev costs $0.042 per million input tokens on TypeSafe and OpenRouter; a `noul` answer's field is `noul`; choice ≤ 255 options, score 2–10 levels; images ≤ 4, ≤ 4 MiB and 16 MP each, ≤ 8 MiB decoded in total, ≤ 13 MiB per request, up to 1,024 tokens each; all three Clef weights are Apache-2.0 and SGLang's `dev-clef` image serves `/v1/systemone`; Cloudflare's public HIPAA material offers a BAA to Enterprise customers but does not name Workers AI or AI Gateway.
- **Python dependencies moved:** `claude-agent-sdk` 0.2.167 (bundles Claude Code CLI 2.1.300; `ResultMessage` needs `duration_ms`, `duration_api_ms`, `session_id`), Textual 8 removed `Static.renderable`, Starlette 1.8 needs Python 3.11, pytest 9.1 fails bare `async def` tests.
- **Tool advisories:** OpenTofu GHSA-q7j3-v8qv-22vq (arbitrary file read in git operations, before 1.11.10/1.12.3 and all 1.10.x); Trivy CVE-2026-54448 (before 0.71.0) and CVE-2026-55092 (before 0.71.1); the March 2026 malicious Trivy v0.69.4 release; Atmos 1.232.0 adds `toolchain.install` (default `auto`) and edition-dependent defaults for provenance and error mode.
- **Claude Code facts:** 5.5 models default to effort `medium`; on Bedrock and Google Cloud the `sonnet` and `haiku` aliases resolve to 4.5 models without effort support; `CLAUDE_CODE_EFFORT_LEVEL` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` override frontmatter; agent names appear in telemetry from v2.1.273; `omitClaudeMd` needs v2.1.271.
- **codebase-memory-mcp** v0.10.0 added `index_status` coverage and `check_index_coverage`; v0.10.8 reports persisted coverage truthfully; latest is v0.11.0. The gauntlet pins nothing.
- **Cross-plan conflicts that break tests as written:** CAT1/CAT2 `system-types.yaml` rows; CAT1/CAT3 `_recompute_ids_for_file` return; CAT2/CAT3 `make_threat`; WS3 Task 1's prompt line versus WS1's pinned test; WS2's `AGENT_PHASES` without `apd-tier-repair`; LA1 needing `decide/policy.py` before WS6 creates it; CAT1 Task 2 not rebuilding WS5 Task 11's lens packets; WS6 task numbers cited off by one in IAC plans. All are fixed in the register.

Found 2026-10-15 to 2026-10-17, after the 1.7.1 release (register A15):

- **The 1.7.0 runner cannot run on current Claude Code** (A15.1). In the Workflow runtime `agent()` and `parallel()` return Promises, and the workflow had no `await` at tag `v1.7.0`, so every step "passed" at once and every run failed in about 24 ms at the report-audit gate. #50 fixed it in 1.7.1. No 1.7.0 live run can be produced: every live 1.7.0 baseline in the plans becomes a 1.7.1 baseline, while offline engine-only comparisons against the 1.7.0 engine (Appendix 1) stay valid.
- **The runner awaits every dispatch** (A15.2, A15.21). It has 1,126 lines and 62 `await`s; `tierGate`, `regate`, `repairTierGate` and `runTier` are `async`; the lens-retry loop is a `for` loop; `pyStep`, `llmStep` and `guard` stay synchronous. `tests/test_workflow_runner_awaits.py` (11 tests) fails on any un-awaited dispatch. A new helper that reads a dispatch result must be `async` and join `ASYNC_HELPERS`; `EXPECTED_GREEN_LABELS` (52 labels) and `LARGEST_PARALLEL_GROUP` (3) move with every label or parallel-group change. Plan text quotes the awaited form, and workflow line numbers in the plans are shifted (A15.28).
- **A changed runner runs by path** (A15.12). `Workflow({name: "apd-gauntlet"})` runs the copy registered when the Claude Code session started. To exercise a changed runner, run it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or start a new session.
- **Cross-file references resolve per record kind** (A15.3). Before #50 the whole-run gate before synthesis halted any run with a capability-to-capability reference. `_deduped_record_ids(run_dir, kind)` is now the shared reader of the deduped findings and capabilities. Anchors: `_validate_rollups` `validate.py:691`, `run_schema_pass` `:711`, `_deduped_record_ids` `:1039`, `run_cross_file_pass` `:1069`; CAT2 T7 and CAT3 T8 resolve new references per kind.
- **Live runs are expensive** (A15.10). One live 1.7.1 run on the claim-event-bus inputs, without telemetry, took 69 dispatches over two sessions, about 6.2 million subagent tokens and about 3.1 hours; the report auditor needed 3 attempts. An 8-run SCP is therefore about 50 million subagent tokens and 25 hours. This raises the priority of WS3 and WS5 and makes the SCP run-set size an owner decision (DEC-35).
- **New files under `docs/superpowers/` are git-ignored** (`f465d5d`, on `main` and `next`; A15.11). New plans, specs and ledgers are added with `git add -f`; edits to tracked files there are tracked normally.
- **The committed claim-event-bus example is not a 1.7 baseline** (A15.9). Its `expected/` was produced at framework 1.4.0 (its `.apd-run.yaml`), with a code-evidence index.

## Part D — Decisions (defaults apply unless the owner overrides)

| Id | Decision | Default | Blocks |
|---|---|---|---|
| DEC-1 | Release 1.7.1 on the substitute gate instead of waiting for WS2's `compare-runs` | **Done:** 1.7.1 was released on the substitute gate (Tasks 1.4, 1.5; tag `v1.7.1` on `0145775`). No 1.7.0 live run can exist (A15.1), so no retroactive 1.7.1-against-1.7.0 comparison will run; a 1.7.1 defect found later ships as 1.7.2 | — (done) |
| DEC-2 | Shape of the WS1 merge | One PR from `fix/ws1-1.7.1`, merge commit, merged in the same session as the release | Task 1.7 |
| DEC-3 | Ship the symlink fix (N1) in 1.7.1 | Yes | Task 1.1 |
| DEC-4 | PEP 639 licence metadata | 1.7.2, before 2027-01-31 (N4) | — |
| DEC-5 | `next`'s version after the 1.7.1 merge-forward | Take 1.7.1; reword next's CHANGELOG bullet | Task 1.8 |
| DEC-6 | Threat catalog edition model | Option A: vendor the whole 1.1.0 release as `open`; `full` = operator-supplied local file in the release schema | CAT1–CAT4 |
| DEC-7 | Catalog repo visibility and licence | Public; data CC BY-SA 4.0, build code Apache-2.0; CIS ids only; CSA ids plus short attributed titles | Task 5.3 |
| DEC-8 | Catalog compat floor and asset names | `>=1.1.0,<2.0.0`; `threat-catalog-<v>.json`, `threat-catalog.schema.json`, `SHA256SUMS`; vendored names stay `open.*` | CAT1 T6, T10 |
| DEC-9 | ATT&CK v20.0 versus the catalog's v19.2 | Vendor 1.1.0; refresh ATT&CK only if an id check fails; plan catalog 1.2.0 on v20 | CAT1 T14 |
| DEC-10 | Where Clef runs for reviews of PHI-handling systems | No decision model until either an Enterprise BAA explicitly covers Workers AI (and AI Gateway if used) or a self-hosted SGLang `/v1/systemone` endpoint runs inside the client's network boundary; prefer self-hosted (N5) | WS6 and finding QA on PHI reviews |
| DEC-11 | Cloudflare default model and per-task models | `clef`; `clef-omni` for `intake-score`, `asset-match`, `diagram-check`; `clef-flash` only as a shadow cost candidate for `output-screen` | LA1 T3; A12.9 |
| DEC-12 | Finding-QA mode | `shadow` by default when a provider is set; `off` allowed; `active` rejected | LA1 T8 |
| DEC-13 | Thresholds keyed by provider, model and weights revision | Yes | WS2 T12, WS6 T1 |
| DEC-14 | AI Gateway payload logging; cross-run decision cache | Off; off | N6; N8 |
| DEC-15 | Decision budget per run | $2.00, shared by all tasks | LA1 T6 |
| DEC-16 | LA2 runs composites | As `apd-gauntlet <composite>` subprocesses with workflow labels | LA2 T3, T6, T7 |
| DEC-17 | WS3 details | Keep WS1's tier-gate phase (`phaseName`) and always-run prompt line; `--excuse` accepts `<gate>:<reason>` and finding ids; attempts count repairs and lens re-runs; pinned Node in the CI `test` job | WS2 T3/T6/T7, WS3 T1/T3 |
| DEC-18 | Strict excerpts by default on `next` | Yes, after fixing case and whitespace false positives and the 25 example excerpts; unparsed structured inputs stay warnings | WS3 T8 |
| DEC-19 | Comparison base for WS5 | `<prev>` with `--strict`; the 1.7.1 baseline (Task 0.4) only at milestone exits | WS5 |
| DEC-20 | Acceptance provider for Wave 3 | The provider used for real reviews; on Bedrock or Google Cloud set `ANTHROPIC_DEFAULT_SONNET_MODEL` and `ANTHROPIC_DEFAULT_HAIKU_MODEL` to effort-capable models; three runs, median | WS5 T16–T23 |
| DEC-21 | Sonnet/Haiku scope | Every lens, intake, code recon, TM author/evaluator, attack-path analyzer, domain auditor and report writer on Sonnet; TM recon and domain auditor then tried on Haiku; adjudicator, report auditor and synthesizer stay on Opus as the backstop until optional N16 tasks pass | WS5 Wave 3, N16 |
| DEC-22 | Revert ladder and agent options | Retry a failing tier one effort step up, then revert to explicit `model: opus`; `omitClaudeMd: true` on every agent; escalate-on-retry off; `maxTurns` unset in the workflow | WS5 |
| DEC-23 | Domain consumer map | Each pack's stated consumers | WS5 T9 |
| DEC-24 | IaC tools and consent | Floors per Global Constraints; pin `ATMOS_EDITION`; roll back unconsented transitive modules and ask again; ShellCheck levels error, warning and info; two runs per held-out entry; 1.7.1 baseline | IAC1–IAC4 |
| DEC-25 | Held-out IaC repositories | `cloudposse/atmos` `examples/quick-start-advanced`, `terraform-aws-modules/terraform-aws-vpc` `examples/complete`, `terraform-aws-modules/terraform-aws-eks` `examples/eks-managed-node-group`, plus one OSI-licensed OpenTofu repository with ≥ 10 resources in `.tofu` files; licences checked at the pinned commit | IAC4 T1 |
| DEC-26 | Code-flow | Approve the spec's six §3 decisions; release in 2.1 after GA; per-language severity gate; resolve the freeze-scope conflict before CF3 | Phase 9 |
| DEC-27 | Skill-library comparison gaps | Owner supplies the list; until then out of scope | Phase 10 |
| DEC-28 | Healthcare pack | Pack only (no new agents), after CAT2 and WS5 T9, before the M6 freeze; else 2.1 | N22 |
| DEC-29 | `manual-audit-prompts` | Wire into `closeout` | N19 |
| DEC-30 | Catalog mappings in the ADR-0022 compliance views | Not in 2.0; render catalog control refs separately, labelled "catalog threat control refs, not an attestation" | CAT3 T11 |
| DEC-31 | codebase-memory-mcp minimum | Recommend v0.10.8 in docs; no hard failure | N21 |
| DEC-32 | CAT4 held-out systems | Two private systems: one with PHI-classified assets, one using the `agentic-ai` pack | CAT4 T11 |
| DEC-33 | Match parameters for `compare-runs` | Title similarity 0.5, at least 10 predicted positives for `calibrate`; confirm with WS2 Task 14 | Phase 3 |
| DEC-34 | Company references in git history and commit metadata (Task 0.2 Step 4) | **Decided 2026-10-16: no history rewrite; the current state is accepted.** The current tree was cleared by A14.7 (a normal commit; PR #48, 2026-10-16) | — (decided) |
| DEC-35 | SCP run-set size (one live 1.7.1 run costs about 6.2 million subagent tokens and 3.1 hours, A15.10) | **Proposed; the owner decides.** Default: claim-event-bus and the private PBM review, two runs each (4 runs, about 25 million tokens and 12.5 hours), plus any committed example a task's own gate criteria name (for example Home Assistant for WS5 Tasks 14, 19 and 20); milestone exits and WS5 Wave 3 keep the full set (8 runs; 12 in Wave 3). Until decided, the plans' 8-run set stands (about 50 million tokens and 25 hours per SCP) | Every SCP (Phases 3–7) |

## Part E — Sequence at a glance

| Phase | Milestone and tag | Line | Contents | Exit gate |
|---|---|---|---|---|
| 0 | — | both | Local environment, telemetry, 1.7.1 baseline, branch cleanup, repository settings | Baseline runs validate; stale branches gone |
| 1 | M1 `v1.7.1` | `main` | N1 symlink fix; WS1 merged; CHANGELOG completed; docs corrections; release; merge-forward | Substitute gate (Tasks 1.4–1.5) passes; release gate prints `prerelease=false, make_latest=true`; `next` CI green |
| 2 | — | `next` | One docs PR applying the amendments register and adding the Part G tasks to their plans | `markdownlint-cli2` clean on every touched plan; registry updated |
| 3 | M2 `v2.0.0a1` | `next` | WS2, second baseline, WS3 | Gates pass against `<prev>`; `usage` shows lower cost per run |
| 4 | M3 `v2.0.0a2` | `next` | LA1 (+N5, N6), LA2; finding QA in shadow | Runner completes the committed examples; `compare-runs` workflow vs runner passes |
| 5 | M4 `v2.0.0a3` | `next` | LA3; WS5 Wave 2 (+N14, N15, N21); catalog release; CAT1 (+N17) | Gates pass after each Wave 2 item; catalog load, no-HITRUST, KB-alignment and KB-edition tests green |
| 6 | M5 `v2.0.0a4` | `next` | IAC1–IAC3; WS6 Tasks 1–13 in shadow (+N7, optional N8, N9); CAT2, CAT3 with `threat_catalog: off` | IaC security regressions green; catalog metamorphic suite C1–C6 green; `off` comparisons unchanged |
| 7 | M6 `v2.0.0b1` | `next` | Shared freeze; IAC4; calibration and enablement; WS5 Tasks 15a–15d, Wave 3, Wave 3b; CAT4; healthcare pack (N22) | Held-out IaC recall ≥ 1.7.1 baseline; per-tier gates; catalog gates decide the default; feature freeze |
| 8 | M7 `v2.0.0rc1` → `v2.0.0` | both | Fixes only; GA runbook | RELEASING.md "2.0.0 GA" complete; `pip install apd-gauntlet` resolves 2.0.0 |
| 9 | M8 `v2.1.0aN` | `next` | Code-flow spec approval; CF1–CF4 | CF4 evaluation against the 1.7.1 CBM-only baseline |
| 10 | post-GA | — | Backlog (Part F, Phase 10) | Per item |

**Parallel-safe pairs** (separate worktrees, after Phase 2 has merged): LA1 with WS3 once WS3 Task 1 has merged; CAT1 with LA3 (neither edits the workflow or runner; CAT1 Task 2 still follows WS5 Task 11 per A10.3); IAC1 with WS5 data-only items (digests, renders); the N22 spec with anything; the catalog release (owner) with anything. Phase 1 runs alone: Phase 2, and so every `next` plan, starts only after Task 1.8.

**Merge one at a time** (they edit the same files; rebuild the bundle after each): WS3 T1/T3; LA2 T6/T7; WS5 T1–T8, T11, T14; IAC1 T12; CAT2 T9; CAT3 T5, T6, T8; and the M5 hotspots — IAC3 T5 with CAT3 T6 (lens dispatch); WS6 T4, IAC3 T8 and CAT3 T14 (report header and bundle); IAC3 T6 with CAT3 T2–T4 (`finding.schema.json`, `synthesis/apply.py`); IAC3 T7, WS6 T7 and CAT3 T9 (`attack_path/build.py`, `asset-graph.schema.json`).

## Part F — Phases and tasks

### Standard procedures (referenced by every phase)

**ENV — working environment** (once per worktree):

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
export PATH="$PWD/.venv/bin:$PATH"      # tests/test_examples.py shells out to apd-gauntlet
node --version                          # >= 22; the WS3 dispatch-trace tests skip without node
```

**QG — quality gate** (end of every task; the expected output is the success line of each tool):

```bash
ruff check tools/ tests/                          # All checks passed!
mypy tools/                                       # Success: no issues found in N source files
pytest -q                                         # N passed in …s (no failed, no errors)
apd-gauntlet lint-agents --agent-dir .claude/agents/   # Lint clean: N agents checked.
apd-gauntlet lint-skills --skill-dir .claude/skills/   # Lint clean: N skills checked.
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "tools/apd_gauntlet/data/domains/**/*.md" README.md CONTRIBUTING.md CHANGELOG.md CODE_OF_CONDUCT.md   # Summary: 0 error(s)
```

On 2026-10-14 the base (`fix/ws1-1.7.1` merged with `main`) gives 2146 passed, 64 mypy source files, 22 agents and 8 skills.

**SEP — standard execution of a detailed plan:**

1. `git fetch origin && git worktree add ../wt-<plan> -b feat/<plan-slug> origin/next` (or `origin/main` for 1.7.x work). Run ENV.
2. Confirm Phase 2 has merged: `git log --oneline origin/next -- docs/superpowers/plans/<plan file> | head -3` shows the amendments commit.
3. Execute the plan with superpowers:subagent-driven-development: one fresh implementer per task, spec review and code-quality review before the next task, controller records rulings in `docs/superpowers/ledgers/<plan-slug>.md` (added with `git add -f`, because new files under `docs/superpowers/` are git-ignored, and committed with the PR, so the next plan's executor can read them). The ledger holds rulings, deviations and, for SCPs, only gate ids, pass/fail and aggregate numbers; never finding titles, evidence, asset names or other client text.
4. After each task, QG. After each task the plan marks behaviour-changing, SCP.
5. Whole-branch review (superpowers:requesting-code-review). **(owner)** Push the branch, open a PR to the target line, merge with a merge commit once CI is green; delete the worktree.

**SCP — standard comparison** (after a behaviour-changing task or PR group; operator):

1. Install the candidate engine in a clean venv and launch Claude Code ≥ 2.1.273 with telemetry (Task 0.3) and the same session model, provider and environment as `<prev>`. Run the candidate runner by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or start a new session after changing it: `Workflow({name: "apd-gauntlet"})` runs the copy registered when the session started (A15.12). The first `<prev>` is the 1.7.1 baseline (Task 0.4) or the `-next-baseline` set (Task 3.2), never a 1.7.0 live run, which cannot exist (A15.1).
2. Run the baseline set (the three committed examples plus one private PBM review) twice: `runs/<id>-<tag>-r1`, `-r2`. For WS5 Wave 3, three runs.
3. `apd-gauntlet usage runs/<id>-<tag>-r1 --otel ~/apd-telemetry/<id>-<tag>-r1.otlp.jsonl` for each run (telemetry always lives in `~/apd-telemetry/`, outside the repository).
4. `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-<tag> --gates eval/gates.yaml --strict` — pass the run-set stem; `compare-runs` finds the `-rN` directories and gates on the median. Expected: exit 0, result `pass`. Record in the ledger only the gate ids, pass/fail and aggregate deltas (full output stays under `runs/`). A failure reverts or fixes before the next task starts.

### Phase 0 — Environment, baseline and repository hygiene

#### Task 0.1: Local checkout and environment

- [x] **Step 1:** In `~/Documents/GitHub/apd-gauntlet`: `git fetch origin --prune && git status -sb`. Expected: `## fix/ws1-1.7.1...origin/fix/ws1-1.7.1`, clean tree. **Done.**
- [x] **Step 2:** Run ENV, then QG on `fix/ws1-1.7.1`. Expected: 2146 passed; lint 22 agents, 8 skills. **Done.**
- [x] **Step 3:** Confirm the plans exist: `git ls-tree --name-only origin/next docs/superpowers/plans/ | grep -c 2026-10-1`. Expected: `17` (the master plan plus 16 workstream plans) before Phase 2 commits this plan and the register. **Done.**

#### Task 0.2: Repository settings and stale branches (owner)

- [ ] **Step 1 (owner; partly done — 2026-10-17: ruleset `next-protection-rules` protects `next` with a pull request and 1 approval, required checks `test (3.10)`, `test (3.11)`, `test (3.12)`, `wheel-smoke`, `bundle-rebuild-diff`, `validate-example` and `plugin-manifest`, and no force-push or deletion; `main` is not protected and no ruleset limits `v*` tags):** Protect `next` like `main` (require a PR plus the `python-tests` and `validate` checks) and add a tag ruleset limiting who may create `v*` tags (RELEASING.md "Repository settings"). Still open: `main` and the `v*` tag ruleset.
- [x] **Step 2 (owner; done by 2026-10-16):** Delete the merged branches: `git push origin --delete fix/report-freshness-gate feat/plugin-channel-guardrails`. Expected: two `- [deleted]` lines. (Their content is on `main` as #9 and #10.) The merged `fix/ws1-1.7.1`, `fix/workflow-await-dispatches`, `chore/release-1.7.1` and `chore/merge-1.7.1-into-next` can be deleted the same way.
- [x] **Step 3:** Remove the local review branches if a review session left any: `git branch --list 'ws1-*'` should print nothing. **Done.**
- [x] **Step 4 (owner, DEC-34; decided 2026-10-16: no rewrite): company references outside the current files.** Found on 2026-10-15 with `git log --all -i -G "$(cat .superpowers/redact-patterns.txt)"` and a search of commit messages and author fields (the pattern file is local only; never commit it):
  - **History and commit metadata:** the affected commits, pull-request heads and tag are listed in the local-only `.superpowers/history-findings.md` (never committed). They are on `next`'s history and on every branch's history, including tag `v1.7.0`.
  - **What fixes what:** A14.7 cleared the current tree (a normal commit; PR #48, 2026-10-16). Removing the history and metadata would need `git filter-repo` (`--replace-text`, `--mailmap`, `--replace-message`) and force-pushes of the affected branches, a re-created `v1.7.0` tag (the PyPI 1.7.0 release was built from it), re-cloning by every contributor, and GitHub Support to purge the read-only `refs/pull/*` heads and cached views. DEC-34 decided against a rewrite on 2026-10-16, before the 1.7.1 release.
  - **Verify after any change:** `git grep -n -i -E -f .superpowers/redact-patterns.txt $(git for-each-ref --format='%(refname)' refs/remotes/origin) -- .` prints nothing; for a history rewrite also `git log --all -i -G "$(cat .superpowers/redact-patterns.txt)" --oneline` and `git log --all --format='%an %ae %B' | grep -i -c -E -f .superpowers/redact-patterns.txt` print nothing and `0`.

#### Task 0.3: Telemetry collector (operator; needed by every SCP)

- [ ] **Step 1:** Run a local OpenTelemetry Collector (`otelcol-contrib`, which has the `file` exporter) writing **outside the repository**. Exports contain `user.email`, Bash commands and tool input; WS2 Task 11 also adds `telemetry/` to `.gitignore` (A9.6) as a second guard. Config `~/apd-telemetry/collector.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 127.0.0.1:4318
exporters:
  file:
    path: ${env:HOME}/apd-telemetry/${env:APD_RUN_ID}.otlp.jsonl
service:
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [file]
```

Start it per run: `APD_RUN_ID=<run-id> otelcol-contrib --config ~/apd-telemetry/collector.yaml`.

- [ ] **Step 2:** In the shell that launches Claude Code (≥ 2.1.273): `export CLAUDE_CODE_ENABLE_TELEMETRY=1 OTEL_LOGS_EXPORTER=otlp OTEL_EXPORTER_OTLP_PROTOCOL=http/json OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 OTEL_LOG_TOOL_DETAILS=1`, and `unset CLAUDE_CODE_SUBAGENT_MODEL CLAUDE_CODE_SUBAGENT_MODEL_FORCE CLAUDE_CODE_EFFORT_LEVEL`.
- [ ] **Step 3:** Verify with one short session: `grep -c claude_code.api_request ~/apd-telemetry/*.jsonl` is non-zero and `agent.name` values are real names, not `custom`.

#### Task 0.4: Capture the 1.7.1 baseline (master plan Task 1, register A15.13; operator)

The 1.7.0 runner cannot run on current Claude Code (register A15.1), so the baseline is captured on 1.7.1.

- [ ] **Step 1:** In a clean venv: `pip install apd-gauntlet==1.7.1`. In Claude Code: `/plugin marketplace add illusconsulting/apd-gauntlet` then `/plugin install apd-gauntlet@apd-security` (it serves `main`, at 1.7.1 since Task 1.7).
- [ ] **Step 2:** For each example: `apd-gauntlet init-run <id>-baseline-r1 --inputs examples/<example>/inputs --domain <pack from the example's .apd-run.yaml>` (plus `--threat-model`/`--methodology-hint` where the example has one), start the collector with `APD_RUN_ID=<id>-baseline-r1`, then run `/apd-gauntlet:run <id>-baseline-r1` in Claude Code. Repeat for `-r2` and for the private PBM review.
- [ ] **Step 3:** Verify: `apd-gauntlet validate runs/<id>-baseline-r1` prints `Clean.` or warnings only for every run; every telemetry file contains `claude_code.api_request`. Keep everything under `runs/` and `~/apd-telemetry/`; WS2's `compare-runs` reads them later.

### Phase 1 — M1: release 1.7.1 from `main`

#### Task 1.1: Add N1 (`init-run` refuses escaping symlinks) to the WS1 branch

- [x] **Step 1:** Execute Part G task N1 on `fix/ws1-1.7.1` (it becomes WS1 Task 11b, A8.8). Expected: its tests pass; QG green. **Done 2026-10-16 as commit `5bb52ec`, merged in #49: 7 tests in `tests/test_init_run_symlinks.py`; QG 2153 passed, 22 agents, 8 skills.**

#### Task 1.2: Merge `main` into the WS1 branch

- [x] **Step 1:** `git switch fix/ws1-1.7.1 && git merge --no-ff origin/main`. Expected: no conflicts (the two sides touch disjoint files). **Done: merge `d60e1dd`.**
- [x] **Step 2:** QG. Expected: 2146 passed plus N1's tests; `pytest --cov` reports coverage ≥ 85 % (88.08 % on 2026-10-14). **Done: 2153 passed; coverage 88.13 %.**
- [x] **Step 3:** CI-equivalent checks: `python tools/check_report_template_freshness.py` (`OK`), `python tools/check_kb_cache_freshness.py` (`OK (12 covered, 4 exempt)`), `python tools/check_notice_present.py` (`NOTICE present for all attribution-required KBs.`). **Done: all OK.**
- [x] **Step 4 (owner):** `git push origin fix/ws1-1.7.1`. **Done (merged in #49).**

#### Task 1.3: Docs corrections on `main` (N3)

- [x] **Step 1:** Execute Part G task N3 on the same branch (or a small docs PR to `main` merged first). Expected: markdownlint clean. **Done: commit `9392178` (all 7 items), merged in #49.**

#### Task 1.4: Substitute release gate, offline

- [x] **Step 1:** Check out tag `v1.7.0` into `../apd-1.7.0` (`git worktree add ../apd-1.7.0 v1.7.0`). **Done.**
- [x] **Step 2:** Save the script in Appendix 1 as `~/apd-scripts/release-gate.sh` and run `bash ~/apd-scripts/release-gate.sh "$PWD" ../apd-1.7.0 /tmp/apd-gate`. **Done: the offline gate passed on all three examples.** Expected (2026-10-14 values):

| Check | claim-event-bus | acme-mobile-banking | home-assistant |
|---|---|---|---|
| `validate expected/` | exit 0, `Clean.`, same as 1.7.0 | exit 0, `Clean.`, same | exit 0, 16 warnings, same |
| `canonicalize` | `0 records recanonicalized, 0 cross-refs rewritten`; `00-context` identical | same | same |
| `build-report` then `audit-report` | `audit-report: pass (23 checks, 0 failed; structural_failed=0 editorial_failed=0)`; `data.js` identical to 1.7.0's (`app.js` and `vendor-licenses.txt` differ because `main` rebuilt the bundle in #44/#45; the script excludes them) | same | same |
| `resume-plan --json` | 12/18 complete | 3/18 | 17/18 (only `tm-recon` pending) |
| excerpts with `inputs/` copied, default / `--strict-excerpts` | 0 warnings / exit 0 | 1 / exit 1 | 24 / exit 1 |
| 2.x run directory | `resume-plan` exits 3, "refusing to resume" | | |
| 1.7.0 engine | `No such command 'resume-plan'` | | |

The strict-excerpt column is information only on 1.7.1 (warn by default); WS3 Task 8 fixes it (A9.16).

#### Task 1.5: Substitute release gate, live (operator)

- [x] **Step 1:** Create the release branch first: `git switch -c chore/release-1.7.1 fix/ws1-1.7.1` and make Task 1.6 Step 2's version-bump commit on it (the release PR reuses this commit). Then `python -m build`, and in a clean venv `pip install dist/apd_gauntlet-1.7.1-py3-none-any.whl` (`apd-gauntlet --version` prints `apd-gauntlet, version 1.7.1`). In Claude Code, load the plugin from the checkout: `/plugin marketplace add <path to the checkout>` then `/plugin install apd-gauntlet@apd-security` (remove the 1.7.0 install first). **Done.**
- [x] **Step 2:** `apd-gauntlet init-run apd-$(date +%Y%m%d)-ws1-gate --inputs examples/apd-20260601-claim-event-bus/inputs --domain pbm --threat-model threat-model.md --methodology-hint stride`. Expected: `Run scaffolded at runs/apd-…-ws1-gate`; `resume-plan` shows 0/18 complete. **Done: `runs/apd-20261016-ws1-gate`.**
- [x] **Step 3:** Start the collector with `APD_RUN_ID=<run-id>` and run `/apd-gauntlet:run <run-id>`. Expected in the log: `resume-plan: engine 1.7.1; 0 agent step(s) already complete.`; `canonicalize-code-evidence` and `canonicalize-threat-model` run; tier gates pass or show `tier <tier>: gate failed; repairing N file(s).` followed by `repair-*` dispatches; `validate-final` passes. **Done: the run completed over two sessions (69 dispatches; no telemetry, no code recon; register A15.10).**
- [x] **Step 4:** End state: `apd-gauntlet validate runs/<id>` prints `Clean.` or warnings only; `apd-gauntlet audit-report runs/<id>` passes; every `tm-` id in `00-context/threat-model-*normalized.yaml` was minted. **Done: `Clean.`; `audit-report` 23/23; all 213 threat-model entries carry minted `tm-` ids.**
- [ ] **Step 5:** Resume test: delete `runs/<id>/20-scalability/resilient.capabilities.yaml` and re-invoke. Expected: `resume: skipping <label> (outputs present and valid).` for every other agent step; only `resilient` is re-dispatched. **Partly shown: a cross-session resume skipped 13 completed agent steps; the `resilient` deletion variant is not recorded.**
- [ ] **Step 6:** Compare with a 1.7.0 run on the same inputs (`40-synthesis/metrics.yaml`: `findings_total`, `bySeverity`, `byDisposition`). Expected: critical plus high does not drop without an evidence-traced reason; blocked share moves ≤ 5 points. Keep both run directories and telemetry (they become WS2 baseline data). **Inconclusive, and not possible as written (no 1.7.0 live run can exist, register A15.1):** against the 1.4.0-era committed example, critical plus high went 11 → 40 (the example's only critical, an unsigned mutable audit log, is covered by three high findings: `immut-5ab6b159`, `nonrep-a4023adf`, `intg-6efd4065`) and the blocked share went 15.8 % → 34.5 %; the run had no code recon. The run directory is the first 1.7.1 data point for WS2 (A15.9).

#### Task 1.6: Release PR `chore/release-1.7.1`

- [x] **Step 1 (owner):** Open the WS1 PR first: `fix/ws1-1.7.1` → `main` (DEC-2). Do not merge yet. **Done: #49 (WS1 with N1 and N3).**
- [x] **Step 2:** On `chore/release-1.7.1` (created from the WS1 branch tip in Task 1.5 Step 1, so the release PR stacks on the WS1 PR), the version-bump commit: bump `pyproject.toml` `version = "1.7.1"`, `tools/apd_gauntlet/__init__.py` `__version__ = "1.7.1"`, `.claude-plugin/plugin.json` `"version": "1.7.1"`, the `apd-gauntlet` entry in `.claude-plugin/marketplace.json` `"version": "1.7.1"`, `tests/test_workflow_apd_gauntlet.py` literal `assert py_version == "1.7.1"` and its message "expected the 1.7.1 release version" (A8.2), `docs/QUICKSTART.md` (`# should print 1.7.1`; `framework_version: 1.7.1`). **Done in #51.**
- [x] **Step 3:** CHANGELOG per A8.7: new `## v1.7.1 — <tag date>` with PR #27's two bullets and #10, #44/#45 under Changed; #7 (Quickstart guide) under Added; the 12 WS1 bullets, N1, #8 and #9 under Fixed; each new bullet ends with its PR number, for example `(#9)`. Move the seven v1.7.0-era bullets (six Added, "Agents emit content only") into `## v1.7.0`, and add the missing #104 bullet there. Keep an empty `## [Unreleased]`. RELEASING.md "Cutting a stable 1.7.x release" step 5 gains: "(While `next` has no 2.0 pre-release, take `main`'s version values.)" Check: `git log --oneline v1.7.0..HEAD | grep -v 'build(deps' | grep -oE '#[0-9]+' | sort -u` — every number printed appears in the v1.7.1 section. **Done in #51 (A8.7/N2; the RELEASING.md note per A8.4).**
- [x] **Step 4 (optional):** Rebuild the committed domain skill so it carries `content_sha256`: `apd-gauntlet build-domain-skill pbm` (default `--out .claude/skills/apd-domain`; expected `Wrote …/SKILL.md`) and commit `.claude/skills/apd-domain/`. **Done: domain skill restamped in #51.**
- [x] **Step 5:** QG plus `pytest tests/test_workflow_apd_gauntlet.py::test_plugin_manifest_version_matches_pyproject tests/test_check_release_tag.py tests/test_plugin_manifest.py`. Expected: 26 passed. Then `python -m build` and a clean-venv smoke: `apd-gauntlet --version` prints `apd-gauntlet, version 1.7.1`; `apd-gauntlet validate-domain pbm` prints `Domain pack 'pbm' OK: …`. **Done: 2219 tests passed; 26 release tests passed; clean-venv smoke OK.**
- [x] **Step 6 (owner):** `git push origin chore/release-1.7.1` and open the PR against `main` (after the WS1 PR in Step 1). **Done: PR #51.**

#### Task 1.7: Merge, tag and publish in one session (A8.3; owner)

- [x] **Step 1 (owner):** Merge the WS1 PR (merge commit), then the release PR (merge commit). Reason for one session: the 1.7.1 workflow halts on an engine without `resume-plan`, and the marketplace serves `main` HEAD. **Done: #49, then #50 (the await and cross-file fixes, register A15.1–A15.3), then #51.**
- [x] **Step 2 (owner):** `git switch main && git fetch origin && git pull && git tag v1.7.1 <release-merge-sha> && python tools/check_release_tag.py --tag v1.7.1` (the gate checks which remote branches contain the commit, so fetch first). Expected: `release gate: ok — version=1.7.1, prerelease=false, make_latest=true`. **Done: tag `v1.7.1` on `0145775`.**
- [x] **Step 3 (owner):** `git push origin v1.7.1`. The release workflow runs the gate, `pytest --cov`, `validate` on claim-event-bus, the wheel smoke, attestations, PyPI trusted publishing and a GitHub Release. **Done: the tag was pushed after `main` CI was green; the release workflow succeeded.**
- [ ] **Step 4:** Verify: `pip index versions apd-gauntlet` lists 1.7.1; a fresh `/plugin install` plus `pip install apd-gauntlet` completes `resume-plan` on a new run. **Partly shown: PyPI lists 1.7.0 and 1.7.1 and the release is marked Latest; the fresh-install `resume-plan` check is not recorded.**

#### Task 1.8: Merge `main` forward into `next` (A8.4)

- [x] **Step 1:** `git switch -c chore/merge-1.7.1-into-next origin/next && git merge --no-ff origin/main`. Expected: no conflicts; `next` now carries 1.7.1 in all five version places (keep them; `next` has no 2.0 pre-release yet). **Done in #52 (`ad9ec66`).**
- [x] **Step 2:** In the same merge commit (amend before pushing): reword next's CHANGELOG bullet "Version stays `1.7.0` for now" to "Version tracks the stable line (1.7.1) until the first 2.0 pre-release", and delete the empty `## [Unreleased]` heading that came from `main`. **Done in #52.**
- [x] **Step 3:** QG. Expected: green, including `test_plan_run_phase_names_consistent_with_workflow`. **(owner)** Push, PR to `next`, merge. **Done: #52 merged.**

#### Task 1.9: 1.7.2 candidates (schedule, do not block 1.7.1)

- [ ] **Step 1:** N4 (PEP 639 licence metadata) before 2027-01-31.
- [x] **Step 2:** N21's documentation half (recommend codebase-memory-mcp ≥ v0.10.8 in `docs/running-the-gauntlet.md` and `docs/schema-evolution.md`) if not already in N3. **Done in N3 (`9392178`).**
- [ ] **Step 3:** Any 1.7.1 defect that the Task 0.4 baseline runs or Task 3.2 Step 2 reveal; no 1.7.0 live run exists to compare against (A15.1).

### Phase 2 — Program docs PR on `next` (amendments and new tasks)

#### Task 2.1: Apply the amendments register to the plans

**Files:** every plan and spec named in `docs/superpowers/plans/2026-10-14-amendments-register.md`; the master plan.

- [ ] **Step 1:** Branch `docs/amendments-2026-10-14` from `next` (after Task 1.8).
- [ ] **Step 2:** Apply the register in this order: A1–A3 (LA plans), A7 (catalog: spec, master plan, CAT1–CAT4), A8 (WS1 plan record and master Task 2), A9 (WS2, WS3), A10 (WS5), A11 and A12 (LA1–LA3, WS6), A13 (IaC plans and spec), A14 (cross-cutting), A15 (state after 1.7.1). Each entry names plan, task, step and the replacement text.
- [ ] **Step 3:** Add a dated "Amended 2026-10-14 (register Axx)" line under each touched plan's header.
- [ ] **Step 4:** `npx --yes markdownlint-cli2 docs/superpowers/plans/2026-10-1*.md docs/superpowers/specs/2026-10-1*.md`. Expected: `Summary: 0 error(s)`.
- [ ] **Step 5:** Verify the WS2 gate-text fixture still parses: the five gate bullets in the master plan are unchanged (`git diff origin/next -- docs/superpowers/plans/2026-10-10-program-master-plan.md | grep -c '^-.*no critical or high finding lost'` prints `0`).

#### Task 2.2: Insert the Part G tasks into their owning plans

- [ ] **Step 1:** Copy each Part G task into its plan at the position named in its header (for example N5 becomes LA1 Task 10 after Task 9; N10–N13 become WS5 Tasks 15a–15d before Task 16; N17 becomes CAT1 Task 12a). Keep the text verbatim so this plan and the owning plan agree.
- [ ] **Step 2:** Add the new shared names to the master plan registry (A14.6): CLI `usage --expect-model`, run-config `decision_model.task_models`, `decision_model.cache`, provider `selfhosted`, user-config `decision_model.base_url`, `decision_model.context_window`, `decision_model.images`, `decision_model.ca_bundle`, `decision_model.cloudflare_gateway_id`, `decision_model.gateway_log_payloads`, decide task `diagram-check`, the `40-synthesis/routing.yaml` file, and the ADR numbers in A14.3.
- [ ] **Step 3:** Add this plan and the register with `git add -f docs/superpowers/plans/2026-10-14-consolidated-execution-plan.md docs/superpowers/plans/2026-10-14-amendments-register.md` (new files under `docs/superpowers/` are git-ignored since `f465d5d`, register A15.11; edits to the tracked plans and specs stage normally) and commit them under `docs/superpowers/plans/` in the same PR. Lint as in Task 2.1 Step 4. **(owner)** Push, PR to `next`, merge (the owner bypasses the approval rule of `next-protection-rules`).

### Phase 3 — M2: WS2 and WS3, then `v2.0.0a1`

#### Task 3.1: WS2 (measurement and evaluation) — SEP on `next`

- [ ] T1 Matcher and snapshot (A9.1) — CI
- [ ] T2 Pairwise delta; creates `tests/conftest.py` — CI
- [ ] T3 Attempts and `summarize --record-attempts`; `tier_repairs`, `lens_reruns` (A9.4) — CI
- [ ] T4 `usage`; `AGENT_PHASES` includes `apd-tier-repair` (A9.2); records effort (A9.7) — CI
- [ ] T5 Gates (`eval/gates.yaml`) — CI
- [ ] T6 `compare-runs`; `--excuse <gate>:<reason>` (A9.5) — CI
- [ ] T7 Workflow records attempts at `tierGate`/`repairTierGate` (A9.3) — CI; Step 6 OP
- [ ] T8 Eval schemas, corpus, registry — CI
- [ ] T9 Findings evaluator, `eval label-template` — CI
- [ ] T10 `eval freeze`, ADR-0028 — CI
- [ ] T11 `eval run`, `.gitignore` gains `telemetry/` (A9.6) — CI
- [ ] T12 `calibrate`, `data/decide/thresholds.yaml` keyed by provider and model (A12.6) — CI
- [ ] T13 Metamorphic `stride-table` — CI
- [ ] N20 Real pre-dedup counts (W3a) — CI
- [ ] T14 Acceptance (OP): `usage` on the Task 0.4 baselines; WS2 Task 14's noise-floor check on the two baseline repetitions; labelling; freeze. Expected: the noise-floor check passes with the DEC-33 match parameters, or they are adjusted and recorded.

#### Task 3.2: Second baseline on `next` (OP)

- [ ] **Step 1:** After WS2 T7 merges, rerun the baseline set twice on `next` (`-next-baseline-r1/-r2`). Expected: each run has `.apd-state/attempts.yaml`; gates 4–5 are now measurable.
- [ ] **Step 2:** Compare the Task 1.5 run with the Task 0.4 claim-event-bus baseline, both 1.7.1: `apd-gauntlet compare-runs runs/<id>-baseline runs/apd-20261016-ws1-gate --gates eval/gates.yaml` (a single run without code recon, so expect the single-run warning). Record the result as WS2 data; a 1.7.1 defect becomes a 1.7.2 fix (Task 1.9 Step 3).

#### Task 3.3: WS3 (cost wave 1) — SEP on `next`, SCP after each behaviour-changing task

- [ ] T1 `apd-cli-runner` (A9.8, A9.9) — CI; SCP
- [ ] T2 Composites `prepare-run`, `tier-gate`, `post-tier4`, `closeout` (A9.10); `closeout` runs `manual-audit-prompts` (N19) — CI
- [ ] T3 Workflow and plan-run use composites (A9.11, A9.12) — CI; SCP
- [ ] T4 `apd-tier-repair` at `effort: low` (A9.13) — CI; SCP
- [ ] T5 One-line descriptions; delete `apd-orchestrator` (A9.14) — CI
- [ ] T6 `effort` on every agent; N18 agent `tools` lint — CI; SCP
- [ ] T7 `domain_improvement_capture` (A9.15) — CI; SCP
- [ ] T8 Strict excerpts by default after the matcher and example fixes (A9.16) — CI; SCP with `--excuse first_pass_and_retries:new-error-class`
- [ ] T9 Measure Wave 1 (A9.17) — Step 1 CI, Steps 2–3 OP. Expected: CLI dispatches 24 (1.7.0) → 17 (18 with capture); general-purpose dispatches → 0; cost per run below `<prev>`.
- [ ] CI change (A9.20): add `actions/setup-node` (pinned by SHA, Node 22) to the `test` job in `.github/workflows/python-tests.yml` so the dispatch-trace tests run.

#### Task 3.4: Cut `v2.0.0a1`

- [ ] **Step 1:** On a branch from `next`: versions `2.0.0a1` (pyproject, `__init__`, test literal) and `2.0.0-alpha.1` (both manifests); `## v2.0.0a1 — <date>` section; replace next's "Version tracks the stable line" bullet; change the workflow's older-engine message, its two test assertions and the copy in `docs/running-the-gauntlet.md` to `pip install --upgrade --pre "apd-gauntlet>=2.0.0a1,<3"` (A8.6).
- [ ] **Step 2 (owner):** QG; push; PR; merge; `git fetch origin && git tag v2.0.0a1 <sha> && python tools/check_release_tag.py --tag v2.0.0a1`. Expected: `prerelease=true, make_latest=false`. Push the tag.
- [ ] **Step 3:** Verify `pip install --pre apd-gauntlet==2.0.0a1` and `/plugin marketplace add illusconsulting/apd-gauntlet#next` install the pair.

### Phase 4 — M3: LA1 and LA2, then `v2.0.0a2`

#### Task 4.1: LA1 (config, keys, decision models) — SEP

- [ ] T1 User config; secret-key regex anchored, `context_window` naming (A11.4) — CI
- [ ] T2 Credentials; conftest fixture added to WS2's `tests/conftest.py` (A1.2); pins (A11.5) — CI
- [ ] T3 Types, catalog, adapters with the 2026-10-14 provider facts; no Workers AI Jev row (A12.1) — CI
- [ ] T4 `DecisionClient`; async tests via `pytest-asyncio` (A11.1); image accounting; truncation detection (A12.7) — CI
- [ ] T5 Run-config block, `decision-record` schema with `calibrated`, validator routing through `schema_for_run_file` (A1.3, A11.2) — CI
- [ ] T6 Finding QA; creates `decide/policy.py`; thresholds from `thresholds.yaml`; consent keyed by subject; shared spend; per-item hashes (A1.1, A1.4–A1.8, A11.3, A12.2) — CI
- [ ] T7 `keys` group — CI
- [ ] T8 Workflow and plan-run wiring after `repairTierGate`; `decideMode('finding-qa') !== 'off'` (A11.6, A12.3) — CI
- [ ] T9 Live fixtures (maintainer, real keys): Cloudflare envelope, `noul` field, estimate-vs-reported token ratio — OP
- [ ] N5 (LA1 T10) Self-hosted System One provider — CI
- [ ] N6 (LA1 T11) Cloudflare AI Gateway option — CI (+ one OP check with a real gateway)

Exit: `apd-gauntlet decide finding-qa <run>` on a copy of claim-event-bus with a mocked provider writes `40-synthesis/decisions/finding-qa.*.yaml` that validates; finding QA runs in shadow on a live run.

#### Task 4.2: LA2 (Agent SDK runner) — SEP

- [ ] T1 Bundle and materialize — CI
- [ ] T2 Ledger, events, lock — CI
- [ ] T3 CLI step executor; composites as subprocesses; `error_files(gate_json, run_dir)`; real `audit-report` line (A2.4–A2.6) — CI
- [ ] T4 Tool-use guard — CI
- [ ] T5 Agent specs and SDK executor; `claude-agent-sdk>=0.2.167,<0.3`; `make_result` with `duration_ms`, `duration_api_ms`, `session_id`; `INSTRUCTIONS` gain `:rerun` and `apd-tier-repair` (A2.7–A2.9) — CI
- [ ] T6 Flow to the pre-synthesis gate: `resume-plan` then `prepare-run`; canonicalize steps; WS1 repair → re-run → halt; finding QA only on green tiers (A2.10–A2.14) — CI
- [ ] T7 Flow to closeout: `post-tier4`, `apply-clusters-retry-2`, capture switch, `closeout --record-attempts` (A2.15–A2.18) — CI
- [ ] T8 `run`, `status`, `cancel`; refuses to resume a 1.7 run (exit 3) — CI
- [ ] T9 Docs, ADR-0025, manual end-to-end run — OP

#### Task 4.3: Workflow versus runner equivalence (OP), then `v2.0.0a2`

- [ ] **Step 1:** Run claim-event-bus twice through the workflow (`runs/ceb-workflow-r1`, `-r2`) and twice through `apd-gauntlet run` (`runs/ceb-runner-r1`, `-r2`). `apd-gauntlet compare-runs runs/ceb-workflow runs/ceb-runner --gates eval/gates.yaml`. Expected: exit 0.
- [ ] **Step 2:** Cut `v2.0.0a2` as in Task 3.4 Steps 1–3 (versions `2.0.0a2` / `2.0.0-alpha.2`).

### Phase 5 — M4: LA3, WS5 Wave 2, the catalog release and CAT1, then `v2.0.0a3`

#### Task 5.1: LA3 (setup, doctor, TUI, web) — SEP

- [ ] T1 Input safety and `create_run` (reuses N1's helper), `list_runs` — CI
- [ ] T2 Start, cancel, report — CI
- [ ] T3 Setup and doctor; `register_doctor_check` (A3.1–A3.3); doctor checks the CLI bundled in the SDK (A11.8); self-hosted provider in setup and doctor (A3.4) — CI
- [ ] T4 `new`, `runs`, `report` — CI
- [ ] T5 Web security middleware — CI
- [ ] T6 Web pages, event stream, report serving — CI
- [ ] T7 Textual TUI (`Static.content`, `textual>=8.2,<9`) (A11.7) — CI
- [ ] T8 Packaging, docs, ADR-0026; CI runs the app tests on Python 3.10 and 3.12 — CI

Exit: the golden path works from a clean machine: `pipx install "apd-gauntlet[app]"`, `apd-gauntlet setup`, `apd-gauntlet new claims-api --inputs <dir>`, `apd-gauntlet run claims-api`, `apd-gauntlet report claims-api --open`.

#### Task 5.2: WS5 Wave 2 (context and determinism) — SEP; SCP after each task against `<prev>` with `--strict` (A10.1)

- [ ] N14 (WS5 T0a) Emit-shape consistency in the schema skill, templates and pbm pack — CI; SCP
- [ ] N15 (WS5 T0b) `omitClaudeMd: true` on every agent — CI; SCP with a 20 KB client CLAUDE.md in the workspace
- [ ] T1 `xref-digest` — CI; SCP
- [ ] T2 `report-digest` (A10.7) — CI; SCP
- [ ] T3 `render` and the authored TM — CI; SCP
- [ ] T4 Render attack-path report — CI; SCP
- [ ] T5 Render TM coverage report — CI; SCP
- [ ] T6 Render advisory report — CI; SCP
- [ ] T7 `edge-review` — CI; SCP
- [ ] T8 `tm-candidates` — CI; SCP
- [ ] T9 `consumers:` sidecar pruning; signature tuple gains `BUILDER_FORMAT` (A10.2) — CI; SCP
- [ ] T10 Attack-path defaults sidecar — CI; SCP
- [ ] T11 `build-lens-skills` with the output skeleton (A10.3, A10.4) — CI; SCP
- [ ] T12 Patch-mode remediation — CI; SCP
- [ ] T13 Code-recon shards; N21 coverage capture — CI
- [ ] T14 Code-recon fan-out; `resume-plan` per-shard rows (A10.5); N21 warning and edges — CI; SCP
- [ ] T15 Remove leftover orchestrator files (A10.6) — CI

#### Task 5.3: Threat catalog release (owner, any time before CAT1 Task 7)

- [ ] Execute Part I "Release runbook" Steps 1–9. Expected: anonymous download plus `sha256sum -c SHA256SUMS` prints two `OK` lines.

#### Task 5.4: CAT1 (catalog data, loader, editions) — SEP, as amended by A7

- [ ] T1 `threat_catalog` key and `catalog/config.py`; ADR-0030 (A7.29) — CI
- [ ] T2 OWASP 2025 KBs, crosswalk (A7.52), control-mappings skill; reruns `build-lens-skills` and commits packets (A10.3) — CI
- [ ] T3 Year-qualified LLM ids; `FileResult` return (A7.51) — CI
- [ ] T4 OWASP editions in `owasp-coverage` — CI
- [ ] T5 `compare-runs` taxonomy deltas — CI
- [ ] T6 Static data, `compat` `>=1.1.0,<2.0.0` (A7.30, A7.53) — CI
- [ ] T7 Model, release schema byte-identical, 1.1.0-shape fixtures; `full.json` = open + `TC-OT-901` (A7.31) — CI
- [ ] T8 `validate_catalog_file` with `hitrust_errors` (A7.32) — CI
- [ ] T9 `load_catalog`; local file falls back on a `hitrust` key (A7.33) — CI
- [ ] T10 `refresh-threat-catalog` with 1.1.0 asset names (A7.34) — CI
- [ ] T11 Freshness sidecar — CI
- [ ] T12 CI guards: KB alignment, no HITRUST content, committed examples (A7.35) — CI
- [ ] N17 (CAT1 T12a) Record ATT&CK, CAPEC and CWE versions — CI
- [ ] T13 Doctor check (`open 1.1.0`) — CI
- [ ] T14 Vendor release 1.1.0 (OP) (A7.37): `apd-gauntlet refresh-threat-catalog --version 1.1.0 --dry-run`, then without `--dry-run`; NOTICE entry; `pytest tests/test_catalog_ci_guards.py -v` passes every vendored guard.

Exit: `compare-runs` with `threat_catalog: off` passes against `<prev>` (CAT1 changes OWASP editions, so crosswalked comparisons are part of the check). Cut `v2.0.0a3`.

### Phase 6 — M5: IaC 1–3, WS6 in shadow, CAT2 and CAT3, then `v2.0.0a4`

#### Task 6.1: IAC1 (resolution and workspaces) — SEP, as amended by A13

- [ ] T1 `run_tool` gateway — CI
- [ ] T2 Invocation allowlist; Trivy rejects `--quiet`; Atmos env pins `ATMOS_TOOLCHAIN_INSTALL=never` and `ATMOS_EDITION`; `--provenance=true` (A13.1, A13.3, A13.4) — CI
- [ ] T3 `infrastructure` run-config keys (anchor on `"infrastructure"`) — CI
- [ ] T4 HCL block parser — CI
- [ ] T5 Root discovery and engine selection — CI
- [ ] T6 Atmos sanitiser strips `toolchain`, `dependencies`, `auth` (A13.3) — CI
- [ ] T7 Atmos resolve and provenance (`:col`, `__atmos_provenance`, `(computed)` unknown) (A13.1, A13.2) — CI + live
- [ ] T8 Fetch consent; exports `read_consent` (A13.10) — CI
- [ ] T9 Workspaces and consented fetch; transitive rollback; archives and > 5 MB skipped (A13.7, A13.9) — CI + live
- [ ] T10 Execution points, index skeleton, summary — CI
- [ ] T11 `iac run`, `iac consent`; stamp `data_sha256` (A13.11) — CI
- [ ] T12 `iac` phase in workflow, plan-run and runner (anchors per A13.12) — CI
- [ ] T13 Security regressions; `iac-tools` CI job with digest-pinned binaries, cosign for Trivy, OpenTofu 1.13.1 (A13.6) — CI
- [ ] T14 Doctor checks (`register_doctor_check`), ADR-0027; tested-version warnings (A13.5) — CI

#### Task 6.2: IAC2 (scanning, checks, plan JSON) — SEP

- [ ] T1 Evidence-index registry behind `schema_for_run_file` (A13.13) — CI
- [ ] T2 Full index schema, check→goal map, control allowlist — CI
- [ ] T3 Scanners, normalisation, suppressions; module checks map to `module.<name>`; neutralise unfetched remote sources (A13.8, A13.14) — CI
- [ ] T4 APD checks — CI
- [ ] T5 CI execution points after `inventory`; ShellCheck `# apd-recorded shellcheck-disable=`; levels incl. `info` (A13.15) — CI
- [ ] T6 Client plan JSON — CI
- [ ] T7 Citation and factual-consistency gates (after `add_excerpt_violations`) — CI
- [ ] T8 Evidence-discipline skill, intake, raw Atmos fallback; bundle sync (A13.16, A13.17) — CI

#### Task 6.3: IAC3 (graph, packets, integration) — SEP; merge-order rules (A13.28)

- [ ] T1 Infrastructure graph — CI
- [ ] T2 Graph citations in the validator — CI
- [ ] T3 Packet selector (`context.select`) — CI
- [ ] T4 Packets and counter-evidence (WS6 Task 12 `packet_for`, A13.18) — CI
- [ ] T5 Packets to lenses; trust edges to intake; bundle sync — CI; SCP
- [ ] T6 `alternatives_considered` — CI
- [ ] T7 IaC edges in the attack-path graph — CI; SCP
- [ ] T8 Report header — CI
- [ ] T9 Setup hints and fetch-consent dialogs (`app/tui/`, `tests/app/web/test_routes.py`, A13.19); document that `run --yes` never grants `iac_module_fetch` (A13.25) — CI
- [ ] T10 Docs and manual acceptance on one private Atmos repository — OP

#### Task 6.4: WS6 (decision tasks) — SEP; every task `off` by default, then shadow

- [ ] T1 Policy (modifies LA1's `decide/policy.py`), record formats, schemas; thresholds keyed by model (A1.4, A12.6) — CI
- [ ] T2 Token-budgeted runner; per-model limits; per-item hashes (A12.2, A12.5) — CI
- [ ] T3 Registry, modes, routing, consent; `task_models`; reuses `run_spend` (A12.9, A1.7) — CI
- [ ] T4 Decision checks in the report header; decision cost (A12.8) — CI
- [ ] T5 `cluster-pairs` — CI
- [ ] T6 `report-claims` — CI
- [ ] T7 `asset-match` (`clef-omni` default) — CI
- [ ] T8 `tm-screen` — CI
- [ ] T9 `intake-score` (`clef-omni`; image limits, A12.4) — CI
- [ ] T10 `input-screen` — CI
- [ ] T11 `output-screen` — CI
- [ ] T12 `iac-triage` — CI
- [ ] T13 Labelling kit and enablement — CI
- [ ] N7 (WS6 T14) `diagram-check` — CI
- [ ] N8 (WS6 T15, optional) Workspace decision cache — CI
- [ ] N9 (WS6 T16, optional) `routing` (escalate-on-doubt), shadow only — CI
- [ ] OP: turn every task to `shadow` on the baseline set with a provider allowed by DEC-10; records written; nothing acted on; SCP passes (shadow must not change outputs).

#### Task 6.5: CAT2 and CAT3 — SEP, `threat_catalog: off` default; as amended by A7

- [ ] CAT2 T1–T10 (A7.39–A7.42, A7.53–A7.55; validator per A7.56) — CI; T9 merges alone
- [ ] CAT3 T1–T15 (A7.43–A7.49, A7.56–A7.58; T11 labels per A14.2) — CI; T5, T6, T8 merge alone
- [ ] OP: SCP with `threat_catalog: off` (expected: outputs unchanged), then one `open` comparison recorded for information.
- [ ] Exit: `apd-gauntlet metamorphic run --suite catalog --json` exits 0 with C1–C6 `holds`. Cut `v2.0.0a4`.

### Phase 7 — M6: evaluation, calibration, tiering; `v2.0.0b1` and feature freeze

#### Task 7.1: One shared freeze

- [ ] **Step 1:** Tune on development data only: IAC4 context parameters, CAT4 selection parameters, `calibrate` thresholds per task and model, and the healthcare pack's calibration (if N22 is in 2.0).
- [ ] **Step 2:** `apd-gauntlet eval freeze`. Expected: `eval/frozen.yaml` records the tunables hash. Any later tuning needs `eval freeze --new-heldout-set`.

#### Task 7.2: IAC4 (evaluation) — SEP, as amended by A13.20–A13.24

- [ ] T1 Corpus and `iac` labels (licence from the raw manifest; whole checkout for `../` modules; Atmos baseline globs) — CI
- [ ] T2 T1–T8 transformation suite; `MetamorphicError` → exit 2 — CI
- [ ] T3 Evaluators and release gate — CI
- [ ] T4 Tune packet parameters (before the freeze) — OP
- [ ] T5 Pre-fill `iac-triage` labels (WS6 T12/T13) — CI
- [ ] T6 Run the evaluation: two runs per entry, mean recall; `### Beta gates (v2.0.0b1)` in RELEASING.md — OP. Expected: `apd-gauntlet eval run eval/iac/corpus.yaml --set heldout --evaluator iac-delta` reports `gate_pass: 1.0`.

#### Task 7.3: Calibrate and enable decision tasks one at a time (OP)

- [ ] **Step 1:** `apd-gauntlet calibrate <task> --labels eval/local/decide/<task>.yaml --target-precision 0.98` for `finding-qa` and each WS6 task, per provider and model in use. Expected: entries with `calibrated: true`, `provider`, `model`.
- [ ] **Step 2:** Enable in this order, SCP after each: finding QA (`active` is not allowed; it stays advisory), `cluster-pairs`, `report-claims`, `asset-match`, `tm-screen`, `intake-score`, `input-screen`, `iac-triage`, `diagram-check`. Expected: gates pass; a failing task returns to `shadow`.

#### Task 7.4: WS5 Wave 3 and 3b — run effectively on Sonnet and Haiku

- [ ] N10 (T15a) Model and effort provenance in `usage` — CI
- [ ] N11 (T15b) First-pass tracking for every LLM step — CI
- [ ] N12 (T15c) Artifact-level metrics and `eval/gates-wave3.yaml` — CI
- [ ] N13 (T15d) Canonicalize fills derivable lens fields — CI; SCP
- [ ] T16 Tier-1 lenses → `sonnet`/`medium` — SCP ×3 median with `--expect-model` and the A10.11 criteria; revert ladder (A10.8)
- [ ] T17 Tier-2 lenses → `sonnet`/`medium` — same
- [ ] T18 Tier-3 lenses → `sonnet`/`medium` — same
- [ ] T19 Intake and code recon → `sonnet`/`medium`; TM recon → `sonnet`/`low` — same
- [ ] T20 TM author → `sonnet`/`medium` — same
- [ ] T21 TM evaluator → `sonnet`/`high`; attack-path analyzer → `sonnet`/`medium` — same
- [ ] T22 Domain auditor → `sonnet`/`medium`; synthesizer pinned `opus` — same
- [ ] T23 Report writer → `sonnet`/`medium`; `model` required by the linter — same (A10.9)
- [ ] N16 Wave 3b: TM recon → `haiku`/`low`; domain auditor → `haiku`/`medium`; optional tier-repair → `haiku`/`low`; optional adjudicator and report auditor → `sonnet`/`high` — SCP each

Exit: `usage` shows every agent on its target model (`--expect-model` passes); cost per run recorded against the 1.7.1 baseline.

#### Task 7.5: CAT4 (catalog evaluation) — SEP, then OP

- [ ] T1–T10 (CI) as amended by A7.50.
- [ ] T11 Label threats on the development and held-out sets (DEC-32); tune selection before the freeze (Task 7.1); measure once on held-out — OP.
- [ ] T12 Set the default: `apd-gauntlet catalog gates eval/local/catalog/corpus.yaml --set heldout --record eval/catalog/decision.yaml`. Expected: every catalog gate passes and `DEFAULT_EDITION` flips to `open`; otherwise it stays `off` for 2.0.

#### Task 7.6: Healthcare / clinical-FHIR pack (N22), if DEC-28 keeps it in 2.0

- [ ] Execute N22 (spec first, then pack tasks). Exit: `apd-gauntlet validate-domain healthcare` OK; the synthetic FHIR example validates; SCP on one private FHIR review.

#### Task 7.7: Cut `v2.0.0b1`; feature freeze on `next`

- [ ] Versions `2.0.0b1` / `2.0.0-beta.1`; gate prints `prerelease=true, make_latest=false`. From here only fixes land on `next`.

### Phase 8 — M7: release candidate and GA

- [ ] **Step 1:** Fix-only PRs on `next`; cut `v2.0.0rc1`; install plugin and engine from it on a clean machine; run the baseline set; `compare-runs` against the 1.7.1 baseline (milestone exit, no `--strict`). Expected: exit 0.
- [ ] **Step 2 (owner):** RELEASING.md "2.0.0 GA": `git push origin main:release/1.7`; rename the 1.7 marketplace to `apd-security-1.7` on `release/1.7`; merge `main` into `next` one last time; on `next` set every version to `2.0.0`, rename the marketplace back to `apd-security`, remove the README pre-release notice and the `--pre` hint in `commands/run.md`, write `## v2.0.0` with upgrade notes; merge `next` into `main` (merge commit); tag `v2.0.0` on `main`.
- [ ] **Step 3:** Expected: gate prints `make_latest=true`; `pip install apd-gauntlet` resolves 2.0.0. Housekeeping per RELEASING.md (dependabot `target-branch`, release-lines table, reset `next` for 2.1).

### Phase 9 — M8: code-flow layer (2.1)

- [ ] **Step 1:** Approve `docs/superpowers/specs/2026-10-10-code-flow-layer-design.md`: its six §3 decisions as written; §13 answers — release 2.1 after GA; per-language severity gate (verdicts advisory until CF4 development precision ≥ 0.9 with an accepted unknown rate, Java first); freeze the §5.3 framework list and extend through `data/codeflow/frameworks/*.yaml`; per-service CPGs with a 4 GB default heap and per-service timeout, `unknown` with reason `resource_limit`, `doctor` checks JDK 21 and memory.
- [ ] **Step 2:** Resolve the freeze-scope conflict first (A13.27): WS2 `eval freeze` gains a per-family scope so adding `data/codeflow/context-params.yaml` does not invalidate the IaC and catalog held-out sets.
- [ ] **Step 3:** Write CF1–CF4 with superpowers:writing-plans, and add each new plan file with `git add -f`. Skeleton: CF1 services, OpenGrep labels (rules authored in-repo; OpenGrep v1.30.2 LGPL-2.1), Java and Go framework models, Joern summaries (v4.0.655, Apache-2.0, JDK 21), call-graph merge, graph cut, `code-flow-index` schema, `code-flow run`, phase `code-flow` after `code-recon` with parity, doctor checks, ADR-0031. CF2 Python and TypeScript frameworks, GraphQL (`graphql-core` 3.3.0, MIT), contracts, deployment config (reads `iac-graph.yaml`), traces, SARIF. CF3 DFDs, packets through `context.select.select_packet`, lens dispatch in both channels, validator `cf:` gates, infrastructure-to-code join, `asset-graph` provenance `code_flow`. CF4 corpora and labels, metamorphic suite, freeze, `eval run`, the 1.7.1 CBM-only baseline, the per-language gate.
- [ ] **Step 4:** Execute CF1–CF4 (SEP) and cut `v2.1.0aN`. Exit: CF4 beats the 1.7.1 CBM-only baseline on held-out precision and recall of code-cited findings.

### Phase 10 — Post-GA backlog (scheduled after `v2.0.0`)

- [ ] Deterministic Kubernetes, Helm and Istio checks on `sandbox.run_tool` (today only the intake agent reads them).
- [ ] ATT&CK detection overlay v2 (covered and uncovered telemetry).
- [ ] Threat catalog 1.2.0 on ATT&CK v20; catalog repo CI (N23) if not done in Phase 5.
- [ ] FHIR remediation W2 (assumption citations) once the owner scopes it; W5 live infrastructure stays a non-goal unless re-approved.
- [ ] Remove `Bash` from the four text-reading agents that still hold it (`apd-threat-model-recon`, `apd-threat-model-author`, `apd-attack-path-analyzer`, `apd-domain-auditor`) once `apd-cli-runner` runs their CLI steps.
- [ ] Gaps from the Cloudflare and Anthropic security skill-library comparison (DEC-27), once supplied.
- [ ] Fourth compliance projection and the specialist confirm-loop deferred by ADR-0022.

## Part G — New tasks (gaps no existing plan covers)

Each task names the plan and position it joins in Phase 2 (Task 2.2). Interfaces from other plans are quoted exactly as those plans define them.

### Task N1: `init-run` refuses links that escape `inputs/` (WS1 Task 11b, `main`, ships in 1.7.1)

**Files:**

- Modify: `tools/apd_gauntlet/init_run.py` (`scaffold_run`, new helpers)
- Modify: `tools/apd_gauntlet/cli.py` (`init_run_cmd`)
- Create: `tests/test_init_run_symlinks.py`
- Modify: `docs/running-the-gauntlet.md` (one sentence under the `init-run` section), `CHANGELOG.md` (Fixed)

**Interfaces:**

- Produces (`init_run.py`): `class UnsafeInputsError(ValueError)`; `def find_escaping_links(inputs_src: pathlib.Path) -> list[str]` — walks with `os.walk(followlinks=False)`, returns sorted POSIX paths relative to `inputs_src` of every symlink (file, directory or dangling) whose `os.path.realpath` is not `inputs_src.resolve()` or below it; `scaffold_run(...)` raises `UnsafeInputsError` **before creating any directory**, with the message `inputs contain links that point outside the inputs folder: <rel> -> <target>; …`.
- Copy rule: directories with `shutil.copytree(item, target, symlinks=True, dirs_exist_ok=True)`; top-level links with `shutil.copy2(item, target, follow_symlinks=False)`; after copying, any link whose target is absolute is rewritten to `os.path.relpath(<realpath mapped into the run's inputs/>, <link's parent>)`, so the run stays self-contained.
- Consumed by: LA3 Task 1 `check_inputs` (calls `find_escaping_links`).

- [ ] **Step 1: Write the failing tests** in `tests/test_init_run_symlinks.py` (use `click.testing.CliRunner` and `tmp_path`):

```python
def test_escaping_dir_link_refused(tmp_path):
    outside = tmp_path / "outside"; outside.mkdir(); (outside / "id_rsa").write_text("SECRET")
    inputs = tmp_path / "in"; inputs.mkdir(); (inputs / "plan.md").write_text("x")
    (inputs / "keys").symlink_to(outside, target_is_directory=True)
    r = CliRunner().invoke(main, ["init-run", "r1", "--inputs", str(inputs), "--root", str(tmp_path / "runs")])
    assert r.exit_code == 1 and "keys" in r.output
    assert not (tmp_path / "runs" / "r1").exists()

def test_escaping_file_link_refused(tmp_path): ...  # inputs/key-file -> outside/id_rsa; exit 1; no file under runs/ contains "SECRET"
def test_nested_escaping_link_refused(tmp_path): ...  # inputs/docs/deep -> outside; exit 1; "docs/deep" in output
def test_dangling_outside_link_refused(tmp_path): ...  # link to a missing path outside inputs; exit 1
def test_internal_link_kept_relative(tmp_path):
    # inputs/a.md and inputs/alias.md -> <absolute path of inputs/a.md>
    run = scaffold_run("r2", inputs, ["pbm"], tmp_path / "runs")
    link = run / "inputs" / "alias.md"
    assert link.is_symlink() and not os.path.isabs(os.readlink(link))
    assert link.resolve() == (run / "inputs" / "a.md").resolve()
def test_find_escaping_links_sorted_relative(tmp_path):
    assert find_escaping_links(inputs) == ["b/link", "keys"]
```

- [ ] **Step 2:** `pytest tests/test_init_run_symlinks.py -v`. Expected: FAIL (`ImportError: cannot import name 'find_escaping_links'`; the CLI test exits 0).
- [ ] **Step 3:** Implement `UnsafeInputsError`, `find_escaping_links` and the copy rule in `init_run.py`; in `init_run_cmd`, catch `UnsafeInputsError` → `click.echo(f"init-run: {e}", err=True)` and `raise SystemExit(1)`.
- [ ] **Step 4:** `pytest tests/test_init_run_symlinks.py tests/test_init_run*.py -v` then QG. Expected: PASS; the full suite still passes.
- [ ] **Step 5:** Commit: `fix(init-run): refuse input links that point outside the inputs folder`.

### Task N2: CHANGELOG completeness (part of Task 1.6 Step 3)

Defined by A8.7 (every new bullet ends with its PR number). Verification: `for n in $(git log --oneline v1.7.0..HEAD | grep -v 'build(deps' | grep -oE '#[0-9]+' | sort -u); do grep -q "($n)" CHANGELOG.md || echo "missing $n"; done` prints nothing (expected numbers include #7, #8, #9, #10, #27, #44, #45 and the WS1 PR), and `grep -c '(#104)' CHANGELOG.md` is 1 (in the v1.7.0 section).

### Task N3: Documentation corrections (`main`, ships in 1.7.1)

**Files:** `docs/superpowers/specs/2026-06-14-capec-bridge-design.md:4`, `docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md:4`, `docs/superpowers/specs/2026-06-14-compliance-projection-layer-design.md` (default-on sentences near lines 20, 31, 54), `docs/adrs/0019-*.md:6-7`, `docs/adrs/0021-*.md:6-7`, `docs/ci-gate-model.md` (pointer near lines 31–35), `tools/apd_gauntlet/cli.py` (TODO at the `# TODO: reference ADR-0010` line), `docs/running-the-gauntlet.md` and `docs/schema-evolution.md` (codebase-memory-mcp minimum).

- [ ] **Step 1:** Status lines: CAPEC → "Implemented (v1.7.0, #110)"; guardrail → "Implemented: PR B #9, PR A #10; no further PR". Compliance projection: say projections are opt-in through `projections` in `.apd-run.yaml` (matching `run-config.schema.json` and `docs/taxonomy-mappings.md`).
- [ ] **Step 2:** ADR-0019 and ADR-0021: add "ADR-0016 and ADR-0018 were reserved and never used." `docs/ci-gate-model.md`: remove the pointer to the remediation design doc that is not in the repository (keep any sentence `tests/test_ci_gate_docs.py` asserts).
- [ ] **Step 3:** Replace the `cli.py` TODO with a reference to `docs/adrs/0010-*.md`.
- [ ] **Step 4:** Docs: "Recommended codebase-memory-mcp: v0.10.8 or later (index coverage reported in `index_status`; `check_index_coverage` tool)."
- [ ] **Step 5:** `pytest tests/test_ci_gate_docs.py tests/test_docs_v14.py -q` and the markdownlint line of QG. Expected: pass, `Summary: 0 error(s)`. Commit: `docs: correct spec status lines, ADR reservations and codebase-memory-mcp minimum`.

### Task N4: PEP 639 licence metadata (`main`, 1.7.2, before 2027-01-31)

**Files:** `pyproject.toml`; `tests/integration/test_wheel_install_smoke.py`; `RELEASING.md` ("Known follow-up").

- [ ] **Step 1:** Add to the wheel smoke test (marker `wheel`): `test_wheel_metadata_has_license_expression` asserting the built wheel's `METADATA` contains `License-Expression: Apache-2.0` and no `Classifier: License ::` line.
- [ ] **Step 2:** `pytest -m wheel tests/integration/test_wheel_install_smoke.py -v`. Expected: FAIL.
- [ ] **Step 3:** Per RELEASING.md's recipe: `license = "Apache-2.0"`; move `license-files = ["LICENSE", "NOTICE"]` under `[project]`; drop the `License :: OSI Approved :: Apache Software License` classifier; `requires = ["setuptools>=77", "wheel"]`.
- [ ] **Step 4:** Rerun; `python -m build 2>&1 | grep -c deprecated` prints `0` (today it prints the setuptools licence-table deprecation). Remove the "Known follow-up" bullet. Commit: `build: PEP 639 license metadata`.

### Task N5: Self-hosted System One provider (LA1 Task 10, after Task 9)

Purpose: the PHI-safe path for DEC-10. Clef weights are Apache-2.0; SGLang's `lmsysorg/sglang:dev-clef` image (SGLang 0.5.22 once released) serves `POST /v1/systemone`; vLLM serves chat only.

**Files:**

- Modify: `tools/apd_gauntlet/decide/providers.py`, `decide/catalog.py`, `decide/factory.py`, `config.py`, `credentials.py`, `data/schemas/user-config.schema.json`, `data/schemas/run-config.schema.json` (provider enum), `docs/decision-models.md`
- Create: `tests/decide/test_selfhosted_provider.py`

**Interfaces:**

- Consumes (LA1): `Provider` protocol (`build_request(self, info, state, questions, images) -> httpx.Request`; `parse_response(self, info, resp, question_ids) -> tuple[str, dict[str, Answer], Usage]`), `ModelInfo`, `ResolvedSecret`, `client_for(provider, model, cfg, *, transport=None)`, `DecisionModelConfig`.
- Produces:
  - `class SystemOneProvider` with `__init__(self, base_url: str, api_key: ResolvedSecret | None, *, name: str = "selfhosted", path: str = "/v1/systemone", ca_bundle: Path | None = None)`; `TypeSafeProvider` and `OpenRouterProvider` become thin subclasses with their fixed URLs.
  - `DecisionModelConfig` gains `base_url: str | None = None`, `context_window: int | None = None`, `images: bool = False`, `ca_bundle: Path | None = None`; provider literal gains `"selfhosted"`.
  - `catalog.selfhosted_model(cfg: DecisionModelConfig) -> ModelInfo` (`provider="selfhosted"`, `id=cfg.model or "clef"`, `route=cfg.base_url`, `context_tokens=cfg.context_window`, `images=cfg.images`, `usd_per_mtok_input=None`).
  - `CredentialName` gains `"selfhosted"` with env var `APD_DECISION_API_KEY` (optional: no key means no `Authorization` header).
  - Decision records gain `endpoint` (host only, never path or query).

- [ ] **Step 1: Write the failing tests** (`httpx.MockTransport`):
  - `test_request_goes_to_base_url_systemone` — `req.url == "https://clef.internal:8443/v1/systemone"`.
  - `test_no_auth_header_without_key` / `test_bearer_with_key` — header absent / `Bearer <key>`.
  - `test_https_required_except_loopback` — `http://10.0.0.5` raises `ConfigError`; `http://127.0.0.1:30000` and `http://localhost:30000` allowed.
  - `test_userinfo_in_url_rejected` — `https://u:p@host` raises `ConfigError` whose message contains neither `u` nor `p` credentials.
  - `test_missing_context_window_is_config_error`.
  - `test_images_refused_unless_enabled` — `InvalidQuestion` (or the client's image error) when `images=False`.
  - `test_record_carries_endpoint_host_only` — record `endpoint == "clef.internal:8443"`.
  - `test_keys_test_selfhosted` — `apd-gauntlet keys test selfhosted` (LA1 Task 7) sends one `noul` question to the mock and prints the model and latency.
- [ ] **Step 2:** `pytest tests/decide/test_selfhosted_provider.py -v`. Expected: FAIL (`ImportError: SystemOneProvider`).
- [ ] **Step 3:** Implement the interfaces above; `client_for("selfhosted", model, cfg)` (where `cfg` is the `UserConfig`) builds `SystemOneProvider(cfg.decision_model.base_url, resolve("selfhosted", cfg), ca_bundle=cfg.decision_model.ca_bundle)` with `selfhosted_model(cfg.decision_model)`; the egress notice names the host; `docs/decision-models.md` gains "Self-hosting Clef" (SGLang `dev-clef`, one H200-class GPU, no vLLM). Setup flags and the `doctor --online` check for this provider land with LA3 Task 3 (register A3.4).
- [ ] **Step 4:** Tests pass; QG. Commit: `feat(decide): self-hosted System One provider`.

### Task N6: Cloudflare AI Gateway option (LA1 Task 11, after N5)

**Files:** `decide/providers.py` (`CloudflareProvider`), `config.py`, `user-config.schema.json`, `decide/errors.py`, `docs/decision-models.md`; Create `tests/decide/test_ai_gateway.py`.

**Interfaces:** `DecisionModelConfig` gains `cloudflare_gateway_id: str | None = None`, `gateway_log_payloads: bool = False`. When a gateway id is set, `CloudflareProvider.build_request` adds `cf-aig-gateway-id: <id>` and, unless `gateway_log_payloads`, `cf-aig-collect-log-payload: false`. A 400 response carrying a `cf-aig-dlp` header raises `ProviderResponseError("blocked by AI Gateway DLP")`; the item is recorded with `outcome: error`, escalated, and the payload is never written. `usage.dlp_flags: int` counts them.

- [ ] **Step 1:** Tests: `test_gateway_headers_present`, `test_payload_logging_off_by_default`, `test_dlp_block_is_item_error_without_payload`, `test_no_gateway_no_headers`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement. Docs state that header routing on `/ai/run` is checked live in LA1 Task 9; if it does not route, use the gateway URL form instead and record the outcome.
- [ ] **Step 4:** Tests pass; QG. Commit: `feat(decide): optional Cloudflare AI Gateway routing with DLP handling`.
- [ ] **Step 5 (OP):** One live call through a real gateway; record whether `/ai/run` honours the header.

### Task N7: `diagram-check` decision task (WS6 Task 14, after Task 13)

Shadow and advisory only. Asks, for each architecture image in `inputs/`, whether it shows each inventory asset, so the attack-path analyzer and the report see where a diagram and the inventory disagree. It runs after `assemble-inventory` (which runs after the intake agent), so intake is not a consumer.

**Files:** Create `tools/apd_gauntlet/decide/tasks/diagram_check.py`, `tests/decide/test_diagram_check.py`, `tests/fixtures/decide/diagram/arch.png` (synthetic: three labelled boxes); Modify `decide/policy.py` (`WS6_TASKS` gains `"diagram-check"`), `decide/tasks/__init__.py` (`TASK_EGRESS["diagram-check"]`), `decide/command.py` (`FULL_INPUT_TASKS` gains `"diagram-check"`, so WS6 Task 3's `allow_full_inputs` guard applies), `run-config.schema.json` (`decision_model.tasks` property), `decision-record.schema.json` (task enum), workflow and `plan_run.py` and `runner/flow.py` (one `await decideStep('diagram-check', 'intake', 'decide-diagram-check');` right after `assemble-inventory` (A15.26)), `.claude/agents/apd-attack-path-analyzer.md` (escalation note), WS6 Task 4's report-header decision checks, docs.

**Interfaces:**

- Consumes: `TaskSpec`, `run_task`, `_inputs.iter_inputs`, `InputFile`, `IMAGE_TYPES`, `MAX_IMAGE_BYTES` (WS6 Tasks 2, 9); `inventory_options` (WS6 Task 7).
- Produces: `SPEC` (`name = "diagram-check"`, `egress = TASK_EGRESS["diagram-check"]`); one unit per image × up to 64 `Noul` questions `"Does this diagram show <name> (<type>)?"` keyed `a<k>`; `requires allow_full_inputs: true`; default model `clef-omni`; record items `{ref: "<image ref>:<node_id>", score, flags: ["absent_from_diagram"] when p < 0.2, ["absent_from_inventory"] reserved}`.

- [ ] **Step 1:** Tests: `test_requires_allow_full_inputs` (exit 2 without it), `test_one_unit_per_image_with_at_most_64_questions`, `test_image_limits_enforced` (> 4 MiB or > 16 MP → item `error`), `test_jev_provider_skips_with_notice` (no image support → notice, no call), `test_shadow_writes_record_and_changes_nothing`, plus the workflow trace row `("diagram-check", "decide-diagram-check", "assemble-inventory", "intake")`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement; update both channels and the parity test; bundle sync.
- [ ] **Step 4:** Tests pass; QG. Commit: `feat(decide): diagram-check task (shadow, advisory)`.

### Task N8 (optional): Workspace decision cache (WS6 Task 15)

**Interfaces:** run-config `decision_model.cache: run | workspace` (default `run`); cache path `<workspace>/.apd-cache/decide/<provider>/<model>/<state_sha256>.json` holding answers only; keyed by the per-item `state_sha256` from A12.2 (state, schema hash, image digests, model). Tests: `test_workspace_cache_hit_makes_no_call`, `test_cache_never_stores_state`, `test_model_change_misses`. Commit: `feat(decide): optional workspace decision cache`.

### Task N9 (optional): `routing` — escalate-on-doubt, shadow only (WS6 Task 16)

Writes `40-synthesis/routing.yaml` (outside `decisions/`, so it is neither validated as a decision record nor counted by `run_spend`) with `rerun_on_opus: [<lens>]` when a Sonnet-tier lens's share of calibrated finding-QA flags exceeds a calibrated cut (`routing.flag_share`). Acts only in the LA2 runner through `model_overrides`, and only after an SCP passes with it enabled. The workflow never acts on it until a per-dispatch model in `agent()` is confirmed (parity forbids otherwise). Tests: `test_routing_shadow_never_changes_models`, `test_runner_applies_override_only_when_active`. Commit: `feat(decide): shadow routing suggestions for lens re-runs`.

### Task N10: Model and effort provenance in `usage` (WS5 Task 15a, before Task 16)

**Files:** Modify `tools/apd_gauntlet/measure/usage.py`, `tools/apd_gauntlet/cli.py` (`usage`), `measure/compare.py`, `tests/fixtures/otel/*`; Create `tests/test_measure_usage_models.py`.

**Interfaces:** `ApiRequest` gains `model: str` and `effort: str | None`; `usage.yaml` `by_agent.<agent>` gains `models: {<model id>: <requests>}` and `efforts: {<level>: <requests>}`; CLI `usage <run-dir> --otel <file> --expect-model <agent-glob>=<model-prefix>` (repeatable) exits 1 and prints `expect-model: <agent> ran <model>, expected <prefix>*` on any mismatch; `compare-runs` prints the per-agent model mix of both sides.

- [ ] **Step 1:** Tests: `test_by_agent_records_models_and_effort` (fixture with two models for one agent), `test_expect_model_fails_on_mismatch` (`apd-confidentiality=claude-sonnet` against an Opus fixture → exit 1, message as above), `test_expect_model_passes`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Pass; QG. Commit: `feat(measure): record and assert per-agent model and effort`.

### Task N11: First-pass tracking for every LLM step (WS5 Task 15b)

**Files:** the workflow (a named async helper that awaits `llmStep` and records the result, listed in `ASYNC_HELPERS` and `CALLS`; `llmStep` stays synchronous, A15.21), `runner/flow.py`, `data/schemas/run-attempts.schema.json`, `measure/attempts.py`, `measure/compare.py`; Create `tests/test_attempts_llm_steps.py`.

**Interfaces:** `attempts.yaml` gains optional `llm_first_pass_invalid: {<label>: int}`, `repairs: {<label>: int}` (agent repair dispatches) and `python_repairs: int` (fields canonicalize normalized, from N13); `compare-runs` reports `llm_first_pass_invalid_delta` per step and `python_repairs_delta`; old attempt files still load.

- [ ] **Step 1:** Tests: `test_non_lens_first_pass_recorded` (trace with a failing TM-evaluator output), runner mirror test, `test_attempts_v1_without_new_keys_loads`.
- [ ] **Step 2–4:** Fail, implement in both channels (parity), pass, QG. Commit: `feat(measure): first-pass validity for every LLM step`.

### Task N12: Artifact-level metrics and Wave 3 gates (WS5 Task 15c)

**Files:** `measure/compare.py`, `measure/gates.py`; Create `eval/gates-wave3.yaml`, `tests/test_measure_context_metrics.py`.

**Interfaces:** new comparison metrics `tm_grounded_ratio_delta_pts`, `cev_entries_ratio`, `inventory_assets_ratio`, `tm_supplied_entry_jaccard`, `tmeval_contradictions_delta`, `apath_findings_ratio`, `headline_overlap_pct`; `eval/gates-wave3.yaml` holds the A10.11 thresholds (for example `inventory_assets_ratio ge 0.9`, `tm_supplied_entry_jaccard ge 0.95`, `headline_overlap_pct ge 80`).

- [ ] **Step 1:** Tests on the Home Assistant example versus a mutated copy (drop 10 % of assets, remove one contradiction): each metric moves as expected and `compare-runs --gates eval/gates-wave3.yaml` exits 1.
- [ ] **Step 2–4:** Fail, implement, pass, QG. Commit: `feat(measure): artifact-level metrics for model tiering`.

### Task N13: Canonicalize fills derivable lens fields (WS5 Task 15d)

**Files:** `tools/apd_gauntlet/canonicalize.py`; Create `tests/test_canonicalize_lens_fields.py`.

**Interfaces:** for lens files only, fill an absent `agent`, `apd_goal` or `apd_tier` from the file path (never overwrite, so a relabel stays an error through `check_lens_consistency`); case-fold `severity`, `confidence`, `disposition`, `maturity`, `posture`; map goal names in `related_concerns` to ids; `CanonicalizeResult.fields_normalized: int`, recorded by N11 as `attempts.python_repairs`.

- [ ] **Step 1:** Tests: `test_absent_goal_filled_from_path`, `test_present_wrong_goal_not_overwritten`, `test_enum_case_folded`, `test_related_concerns_names_mapped`, `test_fields_normalized_counted`.
- [ ] **Step 2–4:** Fail, implement, pass, QG; SCP. Commit: `feat(canonicalize): fill derivable lens fields and fold enum case`.

### Task N14: Emit-shape consistency (WS5 Task 0a, first in Wave 2)

Smaller models copy examples literally; today the examples contradict the rules.

**Files:** `.claude/skills/apd-finding-schema/SKILL.md` (example blocks), `templates/finding.template.yaml`, `templates/capability.template.yaml`, `tools/apd_gauntlet/data/domains/pbm/immutability-classes.md`, `tools/apd_gauntlet/data/domains/pbm/data-taxonomy.md`; Create `tests/test_emit_examples.py`.

- [ ] **Step 1:** Tests: `test_schema_skill_and_templates_show_emit_shape` (every YAML example block parses, has no `id` or `schema_version`, and canonicalizes and validates inside a temporary run); `test_no_pack_tells_specialists_to_emit_lens_perspectives` (grep the pack files).
- [ ] **Step 2–4:** Fail; rewrite the examples in list form without `id`/`schema_version`, and reword the two pbm sentences so only the synthesizer writes `lens_perspectives`; pass; QG; bundle sync; SCP. Commit: `fix(skills): examples show exactly what agents emit`.

### Task N15: `omitClaudeMd: true` on every agent (WS5 Task 0b)

Requires Claude Code ≥ 2.1.271. Stops a client repository's `CLAUDE.md` from loading into every subagent (LA2 already loads no settings).

- [ ] **Step 1:** Test `tests/test_agent_effort.py::test_every_agent_omits_claude_md` (every `.claude/agents/*.md` frontmatter has `omitClaudeMd: true`).
- [ ] **Step 2–4:** Fail; add the key; `lint_agents` accepts it; pass; QG; bundle sync. SCP with a 20 KB `CLAUDE.md` placed in the workspace: outputs unchanged, input tokens lower. Commit: `perf(agents): do not load the workspace CLAUDE.md into subagents`.

### Task N16: Wave 3b and the Opus residue (WS5 Tasks 24–28)

Same shape as WS5 Tasks 16–23 (frontmatter change, `EXPECTED` row in `tests/test_agent_effort.py`, SCP ×3 median with `--expect-model`, revert ladder):

- [ ] T24 `apd-threat-model-recon` → `haiku`/`low`. Extra gate: `tm_supplied_entry_jaccard ≥ 0.95` on claim-event-bus.
- [ ] T25 `apd-domain-auditor` → `haiku`/`medium`. Extra gate: run with `domain_improvement_capture: true`; the improvements file validates and its count is within ±30 % of `<prev>`.
- [ ] T26 (optional) `apd-tier-repair` → `haiku`/`low`. Needs a fault-injection corpus under `eval/local/repair/`; update `tests/test_lint_agent_apd_tier_repair.py`'s model pin.
- [ ] T27 (optional, after `cluster-pairs` is active) `apd-cluster-adjudicator` → `sonnet`/`high`.
- [ ] T28 (optional, last) `apd-report-auditor` → `sonnet`/`high`, with a seeded-defect check: an inserted invented-content line must yield `GATE: fail`.

### Task N17: Record knowledge-base versions (CAT1 Task 12a)

**Files:** `tools/apd_gauntlet/refresh_mitre.py`, `refresh_capec.py`, `refresh_cwe.py`, their data files (`data/mitre-attack-*.json`, `data/capec.json`, `data/cwe.json`) on the next refresh, `tools/apd_gauntlet/catalog/alignment.py` (CAT1 Task 12); tests `tests/test_refresh_versions.py`.

**Interfaces:** `refresh-mitre` writes the collection version to `_meta.version` (and `attack_version` in the detection file); `refresh-capec` writes `_meta.version` and `_meta.count`; `refresh-cwe` writes `_meta.version` from `Weakness_Catalog@Version`. CAT1 Task 12 compares recorded versions instead of listing these KBs as unversioned.

- [ ] **Step 1:** Tests feed each refresher a minimal upstream fixture and assert the recorded version string; `test_detection_file_has_attack_version`.
- [ ] **Step 2–4:** Fail, implement, pass; QG. Commit: `feat(kb): record ATT&CK, CAPEC and CWE versions`.

### Task N18: Lint each agent's tools (WS3 Task 6 addition)

**Files:** `tools/apd_gauntlet/lint_agents.py`; `tests/test_lint_agents.py`.

**Interfaces:** `lint_agent_file` requires `tools` and parses both the comma-string and YAML-list forms; `tests/test_lint_agents.py::EXPECTED_TOOLS: dict[str, frozenset[str]]` pins every agent's tool set, recording that `apd-threat-model-recon`, `apd-threat-model-author`, `apd-attack-path-analyzer` and `apd-domain-auditor` still hold `Bash` (Phase 10 removes it).

- [ ] Steps: test `test_every_agent_tool_set_is_pinned` and `test_missing_tools_is_an_error` → fail → implement → pass → QG. Commit: `test(agents): pin each agent's tool set`.

### Task N19: Run `manual-audit-prompts` at closeout (WS3 Task 2 addition)

`closeout` gains an always-run constituent `manual-audit-prompts <run-dir>` after `summarize`, writing `40-synthesis/manual-audit-prompts.md` (the command exists since 1.7.0 but nothing calls it). Tests: `tests/test_cli_composites.py::test_closeout_runs_manual_audit_prompts` (status line `closeout: manual-audit-prompts exit=0`), and the docs row in `docs/running-the-gauntlet.md`.

### Task N20: Real pre-dedup counts (WS2 addition, FHIR remediation W3a)

**Files:** `tools/apd_gauntlet/synthesis/metrics.py` (`compute_metrics`), `tools/apd_gauntlet/synthesis/rollup.py` (`build_rollups`); tests `tests/test_metrics_pre_dedup.py`.

**Interfaces:** `compute_metrics(..., *, findings_pre_dedup: int | None = None, capabilities_pre_dedup: int | None = None)`; `None` keeps today's value (the deduped length), so callers and committed examples are unaffected until `build_rollups` passes the counts of records in the tier directories' `*.findings.yaml` and `*.capabilities.yaml`.

- [ ] Steps: test that a run with two lens findings merged into one reports `findings_pre_dedup == 2` and `findings_total == 1` → fail → implement → pass → QG; regenerate nothing in `examples/` (they keep their values until rerun). Commit: `fix(metrics): report real pre-dedup counts`.

### Task N21: Code-recon index coverage (WS5 Tasks 13–14 additions; docs in N3)

- [ ] Code recon and shard agents add `mcp__codebase-memory-mcp__check_index_coverage` to their tools and record per-repo coverage (parse-partial and skipped counts) in optional `repos[].coverage` of `code-evidence-index.schema.json`.
- [ ] The zero-entry warning in `validate.py` (the `declared repo '<name>' has zero attributed entries` message) skips repos marked `not_analyzed` and states their reason; otherwise it reads "agent coverage gap or partial index (see `repos[].coverage`)".
- [ ] Code recon reads `CROSS_GRPC_CALLS`, `CROSS_GRAPHQL_CALLS` and `CROSS_TRPC_CALLS` edges in addition to today's three.
- [ ] Tests: `test_zero_entry_warning_skips_not_analyzed`, `test_coverage_block_validates`. Measure: on the Home Assistant example the zero-entry warnings fall below 14 of 23 after a rerun.

### Task N22: Healthcare / clinical-FHIR domain pack (new plan HC, Phase 7 or 2.1 per DEC-28)

This is a subsystem of its own: write a spec with superpowers:brainstorming, then a plan with superpowers:writing-plans; add both new files with `git add -f` (A15.11). Scope to carry into the spec:

- **Pack id** `healthcare`, `framework_compat ">=2.0.0,<3.0.0"`; `pbm/domain.yaml` keeps excluding generic healthcare.
- **Crown jewels:** FHIR server or clinical data repository; HL7 v2 / MLLP interface engine; SMART authorization server; bulk `$export` staging; Consent, Provenance and AuditEvent stores; MPI and terminology services.
- **Attacker positions:** malicious SMART app; compromised backend-services client; patient-portal account takeover; clinician outside the treatment relationship; compromised interface partner.
- **Nine `common-patterns/<goal>.md`** covering SMART scope over-grant and launch-context binding, `_include`/`_revinclude` over-fetch and compartment bypass, bulk-export authorization, forgeable AuditEvent/Provenance, Consent and sensitive-data segmentation, unauthenticated MLLP, Bundle transaction integrity.
- **Data taxonomy** of FHIR resources and HL7 v2 segments; **severity rubric** reusing the pbm clinical patient-harm axis; **regulatory anchors** verified at writing time (ONC/ASTP certification rules, CMS interoperability and prior-authorization APIs, 42 CFR Part 2, HICP).
- **2.0 fields:** `threat_profile` (CAT2) mapping to catalog families; `consumers` (WS5 Task 9).
- **Wider HIPAA and CSF 2.0 crosswalks** for the compliance projection (today 16 HIPAA targets, 8 CSF subcategories).
- **Synthetic FHIR example** under `examples/`; the private FHIR benchmark stays under `eval/local/`.
- **Gates:** `apd-gauntlet validate-domain healthcare` OK; the example validates; SCP on one private FHIR review against a `pbm`-only run of the same inputs (more applicable findings, no loss of critical/high).

### Task N23: Threat-catalog repository CI (in `illusconsulting/threat-catalog`)

- [ ] A workflow on every PR and tag: schema validation of `dist/threat-catalog.json` against `schema/threat-catalog.schema.json`; `if grep -rIil hitrust dist schema src; then exit 1; fi` (data directories only, so the workflow file and guard scripts that contain the word do not trip it); the build's own validator; on tags, `sha256sum -c SHA256SUMS` on the release assets.
- [ ] Expected on 1.1.0: zero schema errors; `367` threats; no `hitrust` match.

## Part H — Clef decision-model integration

### H.1 Role in the gauntlet

Clef (Cloudflare) and Jev (TypeSafe) are "decision models": they take a `state` plus up to 64 typed questions (`noul` = probability a statement is true; `choice` = pick one of ≤ 255 options; `score` = an ordered 2–10-level scale) and return calibrated probabilities. They never write findings or prose. In the gauntlet they are an optional, advisory layer that (a) checks agent output cheaply (finding QA), and (b) lets an expensive agent look only at the items a decision model could not settle (WS6). Defaults: provider `none`; every WS6 task `off`; finding QA `shadow` when a provider is set; no auto-decision without a calibrated, model-keyed threshold.

### H.2 Providers (verified 2026-10-14; LA1 Task 3 catalog per A12.1)

| Provider | Endpoint | Credential | Model | Context (tokens) | Images | $ per M input |
|---|---|---|---|---|---|---|
| Cloudflare Workers AI | `POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/cloudflare/{model}` | `CLOUDFLARE_API_TOKEN` (+ account id) | `clef` (default) | 65,536 | ≤ 4 | 0.24 |
| | | | `clef-flash` | 24,576 hosted (256k self-hosted) | ≤ 4 | 0.038 |
| | | | `clef-omni` | 64,000 | ≤ 4 (also audio/video) | 0.15 |
| TypeSafe | `POST https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` (Bearer) | `jev-latest` | 32,000 | no | 0.042 |
| OpenRouter | `POST https://openrouter.ai/api/v1/systemone` | `OPENROUTER_API_KEY` (Bearer) | `typesafe/jev-1.13` (default), `~typesafe/jev-latest` | 32,000 | no | 0.042 |
| Self-hosted (N5) | `POST <base_url>/v1/systemone` (SGLang `dev-clef`) | optional `APD_DECISION_API_KEY` | `clef`, `clef-flash`, `clef-omni` weights (Apache-2.0) | operator-declared `context_window` | operator-declared | operator's cost |

Output tokens are not billed by any provider. The Workers AI Jev route in the original spec is not on any Cloudflare page and is removed.

### H.3 Every decision-model use, with the recommended model

| Use (plan, task) | Questions | Consumer | Default mode | Model (Cloudflare) | Why |
|---|---|---|---|---|---|
| finding QA (LA1 T6, T8) | choice over 9 goals; noul on the excerpt; score over 5 severities | report header (advisory) | shadow | `clef` | goal choice is intent-like; Clef-flash scores 66.8 on CLINC150+OOS against Clef's 97.4; uncut excerpts can exceed 24,576 tokens |
| `cluster-pairs` (WS6 T5) | choice per pair (3 relations) | cluster adjudicator | off | `clef` | cross-lens judgement; 64k keeps whole groups |
| `report-claims` (WS6 T6) | noul + score | report auditor | off | `clef` | support judgement across several records |
| `asset-match` (WS6 T7) | choice over ≤ 60 inventory options + `none` | attack-path build, `edge-review` | off | `clef-omni` | `none` is out-of-scope detection (omni 97.7, Clef 97.4, flash 66.8) and omni costs less |
| `tm-screen` (WS6 T8) | choice per TM entry × finding | TM evaluator | off | `clef` | contradiction is the class that matters |
| `intake-score` (WS6 T9) | choice (12 types); score × 9; noul × 4 | intake | off; needs `allow_full_inputs` | `clef-omni` | leads on classification benchmarks; takes images; cheapest 64k option |
| `input-screen` (WS6 T10) | noul × 3 (agent instructions, PHI, credentials) | intake; operator notice | off; needs `allow_full_inputs` | `clef` | leads PhishNChips (79.6 against omni 73.2) |
| `output-screen` (WS6 T11) | noul × 2 per excerpt | `build-report` notices | off; needs `allow_full_inputs` | `clef` (`clef-flash` as a shadow cost candidate) | excerpts are short; confirm PHI recall in shadow first |
| `iac-triage` (WS6 T12) | noul per high/critical IaC finding over its packet | severity-disagreements annex | off | `clef` | packets cannot be split; the largest context wins |
| `diagram-check` (N7) | noul per image × asset | attack-path analyzer; report header | off; needs `allow_full_inputs` | `clef-omni` | image understanding |
| `routing` (N9, optional) | derived from finding-QA flags | LA2 runner only | off | — | WS5 Wave 3 safety net |

On TypeSafe or OpenRouter every task uses Jev (no images, 32k). `diagram-check` and the image half of `intake-score` skip with a notice.

### H.4 Gaps closed by this plan

| Gap | Fix |
|---|---|
| No PHI-safe hosting path (DEC-10) | N5 self-hosted provider |
| Thresholds tuned on one model reused on another | A12.6 (key by provider, model, weights revision) |
| Finding QA cannot be turned off | A12.3 (`off \| shadow`) |
| Stale decisions survive repairs (ids hash only title and first locator) | A12.2 per-item `state_sha256` |
| Image limits and token accounting missing; no image fixtures | A12.1, A12.4, N7 fixture |
| Silent truncation of long `state` | A12.7 `possibly_truncated` when `input_tokens ≥ context − 16` |
| Decision spend invisible to `usage` and `compare-runs` | A12.8 |
| One model for every task | A12.9 `decision_model.task_models` |
| No logging/DLP posture on Cloudflare | N6 AI Gateway |
| Re-paying for unchanged inputs across runs | N8 (optional) |
| Model tiering has no safety net | N9 (optional, shadow) |

### H.5 Rollout and data-handling rules

1. LA1 ships providers, finding QA (shadow) and N5/N6 (Phase 4); live fixtures are recorded once with real keys (LA1 T9).
2. WS6 ships every task `off`; operators turn tasks to `shadow` on non-PHI reviews (Phase 6).
3. Labels are collected locally (`decide-labels sheet|annotate|export`); `calibrate` runs per task, provider and model at target precision 0.98 (Phase 7, Task 7.3).
4. Tasks are enabled one at a time with an SCP after each; a failing task returns to `shadow`.
5. PHI reviews use no decision model until DEC-10's condition holds; then only the self-hosted endpoint or a BAA-covered Workers AI account. `allow_full_inputs` stays `false` on PHI reviews unless the endpoint is inside the boundary.
6. Cost envelope: the default per-run budget is $2.00 shared by all tasks; a whole-input task on the Home Assistant example (about 177k input tokens) costs about $0.04 on Clef.

## Part I — Threat catalog integration

### I.1 Approach (spec §5, unchanged except for editions)

The catalog is a deterministic enrichment layer; no agent reads all 367 threats.

1. `catalog scope` (CAT2) filters threats by the run's system types, domain `threat_profile` and inventory surfaces, writing `00-context/threat-scope.yaml`.
2. Ranked candidates per threat-model cell feed the TM author (CAT2); TM entries gain `catalog_refs` or a `catalog_gap_reason`.
3. `catalog shortlists` writes one shortlist per APD goal for the lenses (CAT3).
4. Canonicalize derives `catalog_mappings` (ATT&CK, CWE, CAPEC, 800-53, D3FEND and the OWASP lists the gauntlet already validates) from cited threat ids, kept apart from lens-authored mappings (CAT3).
5. The TM evaluator receives `catalog_silence` candidates: applicable threats nothing addressed (CAT3).
6. Attack paths gain `threat_refs` and tactic sequences; the report gains a catalog coverage view; `catalog-gaps.yaml` and `catalog export-gaps` feed improvements back to the catalog repository without client data (CAT3).
7. CAT4 measures TM recall, mapping precision, silence precision, grounding and tokens against `off`, and its gates decide whether `threat_catalog` defaults to `open` in 2.0.

### I.2 Editions after catalog 1.1.0 (DEC-6, register A7)

- `off` — today's behaviour; the default until CAT4 decides.
- `open` — the vendored release, byte-identical: `tools/apd_gauntlet/data/threat-catalog/open.json`, `open.schema.json`, `open.provenance.json`.
- `full` — an operator-supplied local catalog in the release schema (private threats numbered `TC-<FAMILY>-9NN`, or a release being trialled), loaded only from `threat_catalog.path`, never committed or vendored.
- One guard replaces the stub rule: the loader and CI refuse any key containing `hitrust`, any per-threat `source` or `stub` key, and any `hitrust` text in the vendored file.

### I.3 Release runbook (operator; Task 5.3; before CAT1 Task 7)

The input is `unified-threat-catalog-1.1.0.zip`, sent as an attachment in the catalog-build chat ("Comprehensive threat catalog creation"); download it again from there if it is not already saved. Do not use the 1.0.0 archive (it still contains HITRUST material).

- [ ] **Step 1 — Unpack and inspect** (owner). `mkdir ~/tc-unzip && unzip unified-threat-catalog-1.1.0.zip -d ~/tc-unzip && ls ~/tc-unzip`. If it shows one top-level folder (for example `threat-catalog/`), `mv ~/tc-unzip/threat-catalog ~/tc-1.1.0`; otherwise `mv ~/tc-unzip ~/tc-1.1.0`. Expected tree: `src/` (threat YAML and `index.yaml`), `schema/threat-catalog.schema.json`, `tools/` (build and validate scripts), `dist/` (`threat-catalog.json`, `.md`, `coverage.md`, `.html`), `docs/`, `README.md`, and possibly `review/` working notes.
- [ ] **Step 2 — Check content** (owner). `grep -rIil hitrust ~/tc-1.1.0/src ~/tc-1.1.0/schema ~/tc-1.1.0/dist ~/tc-1.1.0/tools || echo clean` → `clean`. Validate:

```bash
python3 -m pip install --user jsonschema
python3 -I -c "import json,sys; from jsonschema import Draft202012Validator as V; s=json.load(open(sys.argv[1])); d=json.load(open(sys.argv[2])); print(len(list(V(s).iter_errors(d))), d['catalog']['version'], d['catalog']['counts'], len(d['threats']))" ~/tc-1.1.0/schema/threat-catalog.schema.json ~/tc-1.1.0/dist/threat-catalog.json
```

Expected: `0 1.1.0 {'threats': 367, 'families': 25, 'mappings': …} 367`. Then print each framework's recorded version (`python3 -I -c "import json,sys; fw=json.load(open(sys.argv[1]))['frameworks']; it=fw.items() if isinstance(fw,dict) else ((f.get('key'),f) for f in fw); [print(k, f.get('version')) for k,f in sorted(it, key=lambda x: str(x[0]))]" ~/tc-1.1.0/dist/threat-catalog.json`) and compare `atlas` with `5.6.0`, `owasp_top10` with `2025`, `owasp_api` with `2023`, `owasp_llm_2025` with `2025` (CAT1 Task 12 compares version strings exactly).

- [ ] **Step 3 — Review third-party text** (owner, DEC-7). CIS Controls mappings carry ids only; CSA mappings carry ids plus short attributed titles; check EMB3D's terms. Decide whether `review/` is published (default: leave it out).
- [ ] **Step 4 — Create the repository private** (owner). `gh repo create illusconsulting/threat-catalog --private --description "Unified threat catalog (367 threats, 25 families) with framework mappings"`.
- [ ] **Step 5 — Licence and notices, then push** (owner). In `~/tc-1.1.0` add `LICENSE` (CC BY-SA 4.0 for the data), `LICENSE-CODE` (Apache-2.0 for the build scripts) and `NOTICE` with entries for MITRE ATT&CK, CAPEC, CWE (MITRE copyright designation plus licence paragraph), D3FEND (terms of use), ATLAS (Apache-2.0), the OWASP Top 10 and GenAI lists (CC BY-SA 4.0), NIST 800-53, CSF 2.0 and HHS HICP (public domain, courtesy attribution), CIS Controls (ids only) and CSA (ids and short titles with attribution). Then `git init -b main && git add src schema tools dist docs README.md LICENSE LICENSE-CODE NOTICE && git status --short` (check nothing else is staged) `&& git commit -m "Threat catalog 1.1.0" && git remote add origin https://github.com/illusconsulting/threat-catalog.git && git push -u origin main`.
- [ ] **Step 6 — Catalog CI** (owner; N23). Add the workflow; expected green on `main`.
- [ ] **Step 7 — Build assets.** `mkdir release && cp dist/threat-catalog.json release/threat-catalog-1.1.0.json && cp schema/threat-catalog.schema.json release/ && (cd release && sha256sum threat-catalog-1.1.0.json threat-catalog.schema.json > SHA256SUMS)`. Keep `release/` out of git (`echo release/ >> .gitignore`).
- [ ] **Step 8 — Make the repository public, tag and release** (owner, DEC-7). `gh repo edit illusconsulting/threat-catalog --visibility public --accept-visibility-change-consequences && git tag -a v1.1.0 -m "Threat catalog 1.1.0" && git push origin v1.1.0 && gh release create v1.1.0 release/threat-catalog-1.1.0.json release/threat-catalog.schema.json release/SHA256SUMS --title "Threat catalog 1.1.0" --notes "367 threats, 25 families, ~9,800 mappings across 33 frameworks. No HITRUST content."`.
- [ ] **Step 9 — Verify the anonymous download.** `cd "$(mktemp -d)" && for f in threat-catalog-1.1.0.json threat-catalog.schema.json SHA256SUMS; do curl -fsSLO "https://github.com/illusconsulting/threat-catalog/releases/download/v1.1.0/$f"; done && sha256sum -c SHA256SUMS` → two `OK` lines.

### I.4 Catalog gates and the default

- M4 (Phase 5): catalog load, no-HITRUST, KB-alignment and KB-edition tests green; `compare-runs` with `off` passes.
- M5 (Phase 6): metamorphic suite C1–C6 holds (C6 now: a local file equal to the vendored catalog plus threats eligible on no surface gives identical scope, candidates and silence lists); `off` outputs unchanged; one `open` comparison recorded.
- M6 (Phase 7): `apd-gauntlet catalog gates eval/local/catalog/corpus.yaml --set heldout --record eval/catalog/decision.yaml` decides `DEFAULT_EDITION`.
- Follow-ups: catalog 1.2.0 on ATT&CK v20.0 (DEC-9); recorded KB versions (N17) so refreshes can pin to the catalog's framework versions (spec §10.3).

## Part J — Operator workload, risks and tracking

### J.1 Operator work outside the code

| Work | When | Size |
|---|---|---|
| Telemetry collector; 1.7.1 baseline (×2 per configuration; Task 0.4) | Phase 0 | 8 runs (about 50 million subagent tokens and 25 hours, at the cost of one live run below) |
| 1.7.1 live gate and resume test | Phase 1 (done) | 1 run over two sessions: 69 dispatches, about 6.2 million subagent tokens, about 3.1 hours (no telemetry; register A15.10) |
| Second baseline on `next` | Phase 3 | 8 runs (about 50 million tokens, 25 hours) |
| SCP per behaviour-changing PR group | Phases 3–7 | about 8 runs each, about 50 million tokens and 25 hours (12 runs, about 75 million tokens and 37 hours, in Wave 3); the run-set size is DEC-35 |
| Decision-provider keys; live fixtures (LA1 T9); AI Gateway check (N6) | Phase 4 | 1 session |
| Catalog release and repository | Phase 5 | half a day |
| Private Atmos acceptance run (IAC3 T10) | Phase 6 | 1 run |
| Labelling: ~200 cluster pairs; finding goal/severity labels; IaC corpus; catalog threats per corpus system; mapping labels for a finding sample; decision-task labels; code-flow labels (2.1) | Phases 3–9 (start IaC and cluster-pair labelling during Phase 5) | the long pole |
| Hosting decision for Clef on PHI reviews (DEC-10) | Before any decision task runs on a PHI review | owner |

### J.2 Risks

| Risk | Mitigation |
|---|---|
| Workflow and runner merge conflicts | One PR at a time on the listed files; parity tests as tripwire |
| Measurement noise on small effects | Two runs per configuration; three and the median in Wave 3; `--strict` against `<prev>` |
| Operator cost and wall-clock time of live runs (about 6.2 million subagent tokens and 3.1 hours per run; an 8-run SCP about 50 million tokens and 25 hours) | DEC-35 sets the SCP run-set size; WS3 and WS5, the cost waves, move up in priority (register A15.10) |
| Smaller models regress quietly on non-lens agents | N11 first-pass tracking, N12 artifact metrics, N10 model assertions, per-tier revert ladder |
| Release-window skew between plugin and engine | Same-session merge and publish (A8.3); 2.0.0a1 message change (A8.6) |
| Strict excerpts halting real runs | Fix false positives and the 25 example excerpts first (A9.16); unparsed structured inputs warn |
| IaC tools fetching or executing client content | Consent per source including transitive modules (A13.7), neutralised sources (A13.8), Atmos toolchain/auth stripped (A13.3), pinned and digest-checked binaries (A13.6) |
| External tool churn (Trivy, Checkov, Atmos editions) | Floors plus tested versions in `data/iac/tools.yaml`; doctor warns above tested; re-probe on upgrade |
| Catalog mapping error (about 1–2 %) flowing into findings | `catalog_mappings` kept apart and gated on precision (CAT4) |
| Decision thresholds outliving a model change | Model-keyed thresholds (A12.6) |
| Labelling effort delays M6 | Start in Phase 5; one shared freeze (Task 7.1) |
| Code-flow tunables invalidating 2.0 held-out sets | Per-family freeze scope before CF3 (A13.27) |

### J.3 Tracking

- This plan's checkboxes are the program tracker; each detailed plan's checkboxes track its tasks.
- Each plan's execution ledger (`docs/superpowers/ledgers/<plan-slug>.md`) records rulings, deviations and SCP results; the next plan's executor reads the previous ledgers first.
- After each milestone, update Part A (branch table) and Part B (state column) in a short docs PR.

## Part K — Self-review: coverage of every source requirement

| Requirement (source) | Covered by |
|---|---|
| Analyze all branches | Part A; Phase 0 Task 0.2 |
| Implement improvements on branches: WS1 (`fix/ws1-1.7.1`) | Phase 1 |
| Improvements on `next`: WS2, WS3, WS5, WS6, LA1–LA3, IAC1–IAC4, CAT1–CAT4, code-flow | Phases 3–9 with register A1–A3, A7–A15 |
| Merged August branches | Part A verdicts; Task 0.2 |
| Clef integration opportunities | Part H; LA1, WS6; N5–N9; A12 |
| Comprehensive threat catalog integration | Part I; CAT1–CAT4; A7; Task 5.3; N17; N23 |
| Optional Cloudflare / Jev / OpenRouter key or no decision model | LA1 (A12.1), N5, DEC-10–DEC-15 |
| Local CLI, TUI and web via the Agent SDK runner | LA2, LA3 (A2, A3, A11) |
| Two release lines (1.7 on `main`, 2.0 on `next`) | Phase 1, Task 1.8, Task 3.4, Phase 8 |
| Evaluate Terraform, OpenTofu, Atmos; static plus optional plan JSON; remote modules only with consent | IAC1–IAC4 with A13 (consent holes closed) |
| Run effectively on Sonnet and Haiku | WS5 Wave 3 with A10; N10–N16; DEC-19–DEC-22 |
| FHIR benchmark remediation items | Part B rows 19–22, 26; N20, N21, N22, N19 |
| Security defects found during analysis | N1 (symlinks), A13.7–A13.9 (IaC egress), A13.5 (tool advisories) |
| Do not commit to origin | This plan and the register are written to the local working tree only; every push in this plan is an owner action |

Review Focus check: each of the five items has a named test in a named task (N1; A13.7/A13.8; A8.6; A12.6; N10). Type and name consistency: names used across tasks (`find_escaping_links`, `SystemOneProvider`, `selfhosted_model`, `--expect-model`, `decision_model.task_models`, `WS6_TASKS`, `TASK_EGRESS`, `FileResult`, `hitrust_errors`) are each defined once, in the task or register entry that produces them.

## Appendix 1 — Offline 1.7.1 release gate (`release-gate.sh`)

Usage: `bash release-gate.sh <candidate checkout with its venv active> <v1.7.0 checkout> <scratch dir>`. Runs the candidate engine from the active venv and the 1.7.0 engine through `PYTHONPATH`; about 80 seconds.

```bash
#!/usr/bin/env bash
# Offline 1.7.1 release gate (substitute for compare-runs on the 1.7 line).
set -u
REPO=$1; BASE=$2; OUT=$3
EXAMPLES="apd-20260601-claim-event-bus apd-20260602-acme-mobile-banking apd-20260612-home-assistant"
base() { PYTHONPATH="$BASE/tools" python -c "import sys; from apd_gauntlet.cli import main; sys.exit(main())" "$@"; }
rm -rf "$OUT" && mkdir -p "$OUT/cand" "$OUT/base"
echo "engine: $(apd-gauntlet --version)"
for e in $EXAMPLES; do
  for side in cand base; do
    src=$REPO; [ $side = base ] && src=$BASE
    cp -a "$src/examples/$e/expected" "$OUT/$side/$e"
    cp -a "$src/examples/$e/inputs" "$OUT/$side/$e/inputs"
  done
  c=$OUT/cand/$e; b=$OUT/base/$e
  apd-gauntlet validate "$REPO/examples/$e/expected/" > "$OUT/$e.validate.txt" 2>&1; v=$?
  base validate "$BASE/examples/$e/expected/" > "$OUT/$e.validate.base.txt" 2>&1
  same=$(diff <(sed -E 's#^(WARNING|ERROR) [^ ]*/examples/#\1 examples/#' "$OUT/$e.validate.txt") \
              <(sed -E 's#^(WARNING|ERROR) [^ ]*/examples/#\1 examples/#' "$OUT/$e.validate.base.txt") >/dev/null && echo same || echo DIFFERENT)
  echo "[$e] validate expected/: exit=$v errors=$(grep -c '^ERROR' "$OUT/$e.validate.txt") warnings=$(grep -c '^WARNING' "$OUT/$e.validate.txt") vs-1.7.0=$same"
  apd-gauntlet canonicalize "$c" > "$OUT/$e.canon.txt" 2>&1; cc=$?
  base canonicalize "$b" > /dev/null 2>&1
  ctx=$(diff -rq "$REPO/examples/$e/expected/00-context" "$c/00-context" >/dev/null && echo identical || echo CHANGED)
  tree=$(diff -rq -x inputs "$b" "$c" >/dev/null && echo same || echo DIFFERENT)
  echo "[$e] canonicalize: exit=$cc '$(tail -1 "$OUT/$e.canon.txt")' 00-context=$ctx output-vs-1.7.0=$tree"
  apd-gauntlet validate "$c" > "$OUT/$e.excerpts.txt" 2>&1; ev=$?
  apd-gauntlet validate "$c" --strict-excerpts > /dev/null 2>&1; es=$?
  echo "[$e] validate with inputs/: exit=$ev excerpt-warnings=$(grep -c 'not found verbatim' "$OUT/$e.excerpts.txt") strict-exit=$es"
  apd-gauntlet build-report "$c" --quiet > /dev/null 2>&1; br=$?
  base build-report "$b" --quiet > /dev/null 2>&1
  # app.js and vendor-licenses.txt differ by design: main rebuilt the report bundle (#44, #45).
  rep=$(diff -rq -x build-manifest.txt -x app.js -x vendor-licenses.txt "$b/40-synthesis/report-html" "$c/40-synthesis/report-html" >/dev/null && echo same || echo DIFFERENT)
  echo "[$e] build-report: exit=$br report-vs-1.7.0=$rep; $(apd-gauntlet audit-report "$c" 2>&1 | tail -1)"
  apd-gauntlet resume-plan "$c" --json > "$OUT/$e.resume.json"; rp=$?
  echo "[$e] resume-plan: exit=$rp $(python -c "import json,sys; d=json.load(open(sys.argv[1])); s=d['steps']; print(f\"{sum(x['complete'] for x in s)}/{len(s)} complete; pending: {[x['label'] for x in s if not x['complete']]}\")" "$OUT/$e.resume.json")"
done
mkdir -p "$OUT/fut" && printf 'run_id: fut\ndomains: [pbm]\nframework_version: 2.0.0\n' > "$OUT/fut/.apd-run.yaml"
apd-gauntlet resume-plan "$OUT/fut" --json > /dev/null 2> "$OUT/fut.err"; echo "[2.x run] resume-plan exit=$? stderr: $(cat "$OUT/fut.err")"
base resume-plan "$OUT/fut" > /dev/null 2> "$OUT/old.err"; echo "[1.7.0 engine] resume-plan exit=$? $(grep -o "No such command 'resume-plan'" "$OUT/old.err")"
```

## Appendix 2 — Evidence behind this plan

- Repository state: full clone of `illusconsulting/apd-gauntlet` on 2026-10-14 (all branches; all 47 `refs/pull/*/head`), plus the local checkout.
- Seven independent verification passes on 2026-10-14, each on `fix/ws1-1.7.1` merged with `main` (clean merge, 2146 tests passing): WS1 release readiness; WS2/WS3; LA1–LA3/WS6/Clef; WS5 and model tiering; IaC and code-flow; threat catalog after 1.1.0; backlog and older specs. Their findings are distilled into Parts A–D, G and the register.
- External sources checked 2026-10-14: Cloudflare Workers AI model pages and the 2026-10-09 Clef-omni post; Hugging Face Clef model cards; TypeSafe API docs and pricing; OpenRouter Jev guide; PyPI (`claude-agent-sdk`, `textual`, `starlette`, `httpx`, `keyring`, `pytest`, `sglang`, `checkov`, `apd-gauntlet`); Claude Code docs (monitoring, sub-agents, model configuration, workflows); GitHub releases and advisories for OpenTofu, Trivy, Atmos, Checkov, ShellCheck, Joern, OpenGrep and codebase-memory-mcp; MITRE, OWASP, CIS and CSA terms pages. Citations sit next to each fact in the register.
