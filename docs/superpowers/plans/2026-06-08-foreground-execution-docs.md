# Foreground-execution Documentation & Preflight Pass — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the "run the gauntlet in the foreground / in-session" requirement consistent across every operator- and Claude-facing surface, add a doc-only preflight checklist, and recommend an isolated (venv/pipx) install — docs and descriptions only.

**Architecture:** One canonical foreground statement lives in `docs/running-the-gauntlet.md` Step 2; every other surface (README, architecture.md, extending-agents.md, the workflow `meta.description`, the `apd-orchestrator` shim) states a one-line version and links back, so the message cannot drift. A new "Preflight" section in `running-the-gauntlet.md` walks existing CLI commands. No code, no new CLI command, no golden/example regeneration, no schema or report-template change.

**Tech Stack:** Markdown docs, a JS workflow `meta` literal, agent YAML frontmatter. Verification: `markdownlint-cli2`, `apd-gauntlet lint-agents`, `pytest` (regression only).

**Spec:** [docs/superpowers/specs/2026-06-08-foreground-execution-docs-design.md](../specs/2026-06-08-foreground-execution-docs-design.md)

---

## Conventions used by every task

- **Branch:** work on `docs/foreground-execution-docs` (already created; the spec is committed there as `5d059a2`).
- **markdownlint command** (the exact CI glob — run it after every doc edit; a prior PR was reddened by linting only the edited file):

  ```bash
  npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
  ```

  Note: `docs/superpowers/specs/**` **is** linted (only `plans/**` is excluded), so the spec from the prior step is in scope; this plan file is not.
- **lint-agents command:** `apd-gauntlet lint-agents --agent-dir .claude/agents/`
- **markdownlint config** (`.markdownlint.json`): `MD013` (line length) is **off**, so long prose lines are fine; `MD024` is `siblings_only`. Do not introduce a duplicate sibling heading.
- Each task is a single focused commit. Use the commit message shown in the task's final step.

---

## Task 1: `docs/running-the-gauntlet.md` — Install, CLI reference, Preflight, canonical Step 2

This is the source-of-truth doc. Four edits, one commit.

**Files:**

- Modify: `docs/running-the-gauntlet.md`

- [ ] **Step 1: Add the isolated-install recommendation to the Install section**

Find this exact block (lines ~12–19):

```markdown
## Install

```bash
pip install apd-gauntlet
apd-gauntlet --version
```

The CLI exposes the following operator subcommands:
```

Replace it with:

```markdown
## Install

Install the CLI into an isolated environment so the `apd-gauntlet` console script
stays off your system Python and on your `PATH` — a virtual environment (matching
the contributor setup in `CONTRIBUTING.md`) or `pipx`:

```bash
python3 -m venv .venv && . .venv/bin/activate   # or: pipx install apd-gauntlet
pip install apd-gauntlet
apd-gauntlet --version
```

The CLI exposes the following operator subcommands:
```

- [ ] **Step 2: Add `plan-run` to the CLI command-reference list**

In the fenced command list, find this line:

```text
apd-gauntlet validate-run-config <config>        # validate a .apd-run.yaml against the schema
```

Insert a new line immediately after it:

```text
apd-gauntlet plan-run <run-dir>                  # emit the ordered foreground-drive checklist (CLI/AGENT steps) for a run
```

- [ ] **Step 3: Add the Preflight section immediately before "## Step 2: Run the gauntlet"**

Find the line `## Step 2: Run the gauntlet` and insert the following section directly above it (so it sits after the optional-feature sections it references, and before Step 2):

````markdown
## Preflight: confirm scaffolding is in place

Before you launch a run, confirm every piece of scaffolding your `.apd-run.yaml`
implies is present. Each check maps to a command you already have — there is no
separate preflight tool. Items tagged *(conditional)* apply only when the run
config declares the relevant feature.

When Claude walks you through this list, it will recommend an isolated install
(an activated virtual environment, or `pipx`) at the first step — unless the CLI
is already isolated and on `PATH`. That is a nudge, not a gate.

| Check | Command / signal | When |
|---|---|---|
| CLI installed in an isolated env; version matches `plugin.json` | `apd-gauntlet --version` | always |
| Run scaffolded (`runs/<id>/` + `.apd-run.yaml`) | output of `init-run` (Step 1) | always |
| Run-config valid | `apd-gauntlet validate-run-config runs/<id>/.apd-run.yaml` | always |
| Domain pack(s) valid | `apd-gauntlet validate-domain <pack…>` | always |
| `apd-domain` skill built (with per-goal sidecars) | `apd-gauntlet build-domain-skill <pack…>` | always |
| Agent frontmatter clean | `apd-gauntlet lint-agents` | always |
| Declared taxonomy catalogs present | `apd-gauntlet refresh-{mitre,cwe,owasp,d3fend,atlas}` as the `taxonomies:` list requires | conditional |
| CBM reachable + codebase indexed | codebase-memory-mcp `index_status` / server registered | if `code_recon: enabled`/`auto` |
| Threat-model file exists at declared path | inspect `inputs/` against the `threat_model:` path | if `threat_model:` declared |
| `crown_jewels` + `attacker_positions` declared | inspect `.apd-run.yaml` (or the active pack's `domain.yaml`) | if you want attack-path output |
| Dry-run the gated phase order | `apd-gauntlet plan-run runs/<id>` | recommended last step |

The final check — `plan-run` — doubles as your confidence check and as the entry
point to the supported foreground-drive path described in Step 2: it reads
`.apd-run.yaml`, validates it, and prints the exact ordered phase → step checklist
the runner would execute, honoring the run-config gates.
````

- [ ] **Step 4: Refine the Step 2 foreground statement to be canonical (foreground-first framing) + cross-link Preflight**

Find this exact block (currently lines ~263–278):

```markdown
The specialists run as subagents of your Claude Code session, so this is an
interactive, in-session operation — it is not meant to be driven headlessly.

> **Run it in the foreground.** The runner dispatches each specialist as a
> subagent of the live session. Driving it through the background `Workflow`
> primitive can interrupt those dispatches mid-flight (the subagents are
> cancelled and no phase output is written), leaving an empty run directory.
> If the background path is unavailable or keeps interrupting, drive the runner
> in the foreground instead: run the deterministic CLI phases yourself
> (`build-domain-skill`, `canonicalize`, `validate`, `cluster-candidates`,
> `apply-clusters`, `rollup`, `build-report`, `audit-report`) and dispatch the
> LLM specialists/judges (`apd-intake`, `apd-code-recon`,
> `apd-threat-model-author`, the nine lenses, `apd-cluster-adjudicator`,
> `apd-threat-model-evaluator`, `apd-attack-path-analyzer`, `apd-report-writer`,
> `apd-report-auditor`, `apd-domain-auditor`) as foreground agents, in the phase
> order below. Foreground subagents are not interrupted.
```

Replace it with:

```markdown
Work through [Preflight](#preflight-confirm-scaffolding-is-in-place) first to
confirm the run is ready. The specialists run as subagents of your Claude Code
session, so this is an interactive, **in-session (foreground)** operation — it is
not meant to be driven headlessly.

> **Run it in the foreground (in-session).** The runner dispatches each specialist
> as a subagent of your live Claude Code session. Both supported drive modes are
> foreground: (1) prompt Claude to run the workflow in your session, as above; or
> (2) drive it explicitly with `apd-gauntlet plan-run` (below). Do **not** launch
> the runner in the background (`run_in_background`) or headlessly — a background
> launch can interrupt the specialist dispatches mid-flight (the subagents are
> cancelled and no phase output is written), leaving an empty or partial run
> directory. If a run is interrupted, **re-invoke it in the foreground**; the
> runner is resumable and idempotency guards replay completed phases.
>
> For the explicit foreground drive, run the deterministic CLI phases yourself
> (`build-domain-skill`, `canonicalize`, `validate`, `cluster-candidates`,
> `apply-clusters`, `rollup`, `build-report`, `audit-report`) and dispatch the LLM
> specialists/judges (`apd-intake`, `apd-code-recon`, `apd-threat-model-author`,
> the nine lenses, `apd-cluster-adjudicator`, `apd-threat-model-evaluator`,
> `apd-attack-path-analyzer`, `apd-report-writer`, `apd-report-auditor`,
> `apd-domain-auditor`) as foreground agents, in the phase order below —
> `apd-gauntlet plan-run` emits this exact list for you.
```

- [ ] **Step 5: Lint the doc**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: exit 0, no errors. (If a table or list triggers `MD058`/`MD032` "blanks around" rules, ensure a blank line precedes and follows each table/list — the inserted blocks already include them.)

- [ ] **Step 6: Verify the new content is present**

Run:

```bash
grep -nE "Preflight: confirm scaffolding|plan-run <run-dir>|pipx|Run it in the foreground \(in-session\)" docs/running-the-gauntlet.md
```

Expected: four matches (one per anchor string).

- [ ] **Step 7: Commit**

```bash
git add docs/running-the-gauntlet.md
git commit -m "docs(running): canonical foreground statement, preflight checklist, plan-run in CLI ref, venv install"
```

---

## Task 2: `README.md` — isolated install + §4 foreground/preflight callout

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Add the isolated-install recommendation to the Install section**

Find this exact block (lines ~38–45):

```markdown
## Install

```bash
pip install apd-gauntlet
apd-gauntlet --version    # prints the installed version, confirming the CLI is on your PATH
```

That installs both the Python CLI and the Claude Code agent + skill bundle.
```

Replace it with:

```markdown
## Install

Install into an isolated environment — a virtual environment or `pipx` — so the
`apd-gauntlet` console script stays off system Python and on your `PATH`:

```bash
python3 -m venv .venv && . .venv/bin/activate   # or: pipx install apd-gauntlet
pip install apd-gauntlet
apd-gauntlet --version    # prints the installed version, confirming the CLI is on your PATH
```

That installs both the Python CLI and the Claude Code agent + skill bundle.
```

- [ ] **Step 2: Add the foreground + preflight callout to §4 "Run the gauntlet"**

Find this exact block (lines ~96–100):

```markdown
```text
> Run the apd-gauntlet workflow on runs/apd-YYYYMMDD-my-feature/
```

The runner (`.claude/workflows/apd-gauntlet.js`) phases the run end-to-end:
```

Replace it with (inserting the blockquote between the code block and the "The runner…" paragraph):

```markdown
```text
> Run the apd-gauntlet workflow on runs/apd-YYYYMMDD-my-feature/
```

> **Run it in the foreground.** The specialists run as subagents of your live
> Claude Code session — drive the runner in-session, not via the background
> `Workflow` tool or headlessly, which can interrupt the dispatches and leave an
> empty run directory. Confirm scaffolding with the **Preflight checklist** and
> read the full foreground statement in
> [docs/running-the-gauntlet.md](docs/running-the-gauntlet.md).

The runner (`.claude/workflows/apd-gauntlet.js`) phases the run end-to-end:
```

- [ ] **Step 3: Lint**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: exit 0.

- [ ] **Step 4: Verify**

Run:

```bash
grep -nE "pipx install apd-gauntlet|Run it in the foreground|Preflight checklist" README.md
```

Expected: at least three matches (the install comment line + the two callout strings).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs(readme): foreground/preflight callout in quickstart + venv install"
```

---

## Task 3: `.claude/workflows/apd-gauntlet.js` — `meta.description` foreground clause

The workflow static-text test (`tests/test_workflow_apd_gauntlet.py`) asserts only that `description:` is present, not its content — so appending is safe. The file is `.js`, not markdown, so it is not in the markdownlint glob.

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js` (the `meta.description` line, ~line 35)
- Test: `tests/test_workflow_apd_gauntlet.py` (regression — no edit)

- [ ] **Step 1: Replace the `meta.description` line**

Find this exact line:

```javascript
  description: 'Deterministic APD gauntlet runner (replaces apd-orchestrator); receipt-only dispatch + decomposed synthesis + gated report audit + synthesizer fallback.',
```

Replace it with:

```javascript
  description: 'Deterministic APD gauntlet runner (replaces apd-orchestrator); receipt-only dispatch + decomposed synthesis + gated report audit + synthesizer fallback. Runs INTERACTIVE/FOREGROUND — specialists are subagents of the launching session; do not drive it in the background or headlessly (a background launch can interrupt dispatches). See docs/running-the-gauntlet.md.',
```

(The string is single-quoted and contains no single quotes — it parses cleanly.)

- [ ] **Step 2: Run the workflow static-text test**

Run:

```bash
python -m pytest tests/test_workflow_apd_gauntlet.py -q
```

Expected: PASS (all tests). The `test_meta_block_is_pure_literal_first_export` test still finds `description:` and the pure-literal `meta` block.

- [ ] **Step 3: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js
git commit -m "docs(workflow): state the foreground/in-session requirement in meta.description"
```

---

## Task 4: `.claude/agents/apd-orchestrator.md` — foreground note (shim)

`tests/test_orchestrator_deprecation.py` pins four facts that the edit MUST preserve: the literal `DEPRECATED` (uppercase) marker, `.claude/workflows/apd-gauntlet.js`, `2026-05-29-apd-token-resilience-design.md`, and a single trailing newline. The edits below keep all four. `.md` under `.claude/**` is linted; `lint-agents` only requires `name` + `description` present.

**Files:**

- Modify: `.claude/agents/apd-orchestrator.md`
- Test: `tests/test_orchestrator_deprecation.py`, `tests/test_lint_agents_receipt.py` (regression — no edit)

- [ ] **Step 1: Update the frontmatter `description`**

Find this exact line:

```text
description: Deprecated — superseded by the apd-gauntlet workflow runner (.claude/workflows/apd-gauntlet.js, invoked via the Workflow tool). This agent no longer orchestrates runs; retained as a historical-topology reference.
```

Replace it with:

```text
description: Deprecated — superseded by the apd-gauntlet workflow runner (.claude/workflows/apd-gauntlet.js, invoked via the Workflow tool from a live foreground/in-session Claude Code session; never driven in the background or headlessly, which can interrupt the subagent dispatches). This agent no longer orchestrates runs; retained as a historical-topology reference.
```

- [ ] **Step 2: Add the foreground note to the body's first paragraph**

Find this exact paragraph:

```markdown
**DEPRECATED.** The APD gauntlet is now run by the deterministic workflow
runner `.claude/workflows/apd-gauntlet.js` (invoke it via the Workflow tool).
This agent no longer orchestrates runs — the runner dispatches intake, the tier
specialists, the decomposed synthesis pipeline, and the gated report audit
directly, with native auto-resume. See
`docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` §4 for the
architecture and §7 for the decomposed Phase 5.
```

Replace it with:

```markdown
**DEPRECATED.** The APD gauntlet is now run by the deterministic workflow
runner `.claude/workflows/apd-gauntlet.js` (invoke it via the Workflow tool from
a live, **foreground / in-session** Claude Code session — the dispatched
specialists are subagents of that session, so the runner must not be driven in
the background or headlessly, which can interrupt the dispatches and leave an
empty or partial run directory; see `docs/running-the-gauntlet.md`). This agent
no longer orchestrates runs — the runner dispatches intake, the tier specialists,
the decomposed synthesis pipeline, and the gated report audit directly, with
native auto-resume. See
`docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` §4 for the
architecture and §7 for the decomposed Phase 5.
```

- [ ] **Step 3: Run the deprecation + lint-agents tests**

Run:

```bash
python -m pytest tests/test_orchestrator_deprecation.py tests/test_lint_agents_receipt.py -q && apd-gauntlet lint-agents --agent-dir .claude/agents/
```

Expected: pytest PASS (all four deprecation assertions + receipt lint), and `lint-agents` prints no errors (exit 0).

- [ ] **Step 4: Lint markdown**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-orchestrator.md
git commit -m "docs(orchestrator): note the runner is foreground/in-session (preserve pinned facts)"
```

---

## Task 5: `docs/architecture.md` — "Execution model: foreground / in-session"

**Files:**

- Modify: `docs/architecture.md`

- [ ] **Step 1: Insert the execution-model subsection before "## Tier topology"**

Find this exact block (the deprecated-shim paragraph followed by the Tier-topology heading, lines ~45–47):

```markdown
A twenty-first file, `apd-orchestrator.md`, remains in [.claude/agents/](../.claude/agents/) as a **deprecated shim** — superseded by the `apd-gauntlet` workflow runner and retained only as a historical-topology reference; it is not a functional agent and is not counted among the 20.

## Tier topology
```

Replace it with:

```markdown
A twenty-first file, `apd-orchestrator.md`, remains in [.claude/agents/](../.claude/agents/) as a **deprecated shim** — superseded by the `apd-gauntlet` workflow runner and retained only as a historical-topology reference; it is not a functional agent and is not counted among the 20.

## Execution model: foreground / in-session

The runner is **interactive**: every specialist it dispatches runs as a subagent of the live Claude Code session that launched the run. Drive it in the **foreground / in-session** — either by prompting Claude to run the `apd-gauntlet` workflow, or via the explicit `apd-gauntlet plan-run` drive checklist. A background (`run_in_background`) or headless launch can interrupt the specialist dispatches mid-flight, cancelling the subagents and leaving an empty or partial run directory. The runner is resumable: re-invoke it in the foreground and idempotency guards replay completed phases. See [Running the gauntlet](running-the-gauntlet.md) for the operator-facing foreground statement and the preflight checklist.

## Tier topology
```

- [ ] **Step 2: Lint**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: exit 0.

- [ ] **Step 3: Verify**

Run:

```bash
grep -n "Execution model: foreground / in-session" docs/architecture.md
```

Expected: one match.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture.md
git commit -m "docs(architecture): document the foreground/in-session execution model"
```

---

## Task 6: `docs/extending-agents.md` — runner (not orchestrator) dispatches, foreground

Two stale "the orchestrator dispatches" references become "the `apd-gauntlet` workflow runner dispatches (as a foreground subagent)".

**Files:**

- Modify: `docs/extending-agents.md`

- [ ] **Step 1: Fix the activation-gated-agent intro (line ~121)**

Find this exact sentence:

```markdown
These are added as **activation-gated optional agents**: they sit at tier 0 (intake-enrichment) or tier 4 (synthesis-augmentation), the orchestrator dispatches them only when their preconditions are met, and they emit a finding-prefix the synthesizer recognizes.
```

Replace it with:

```markdown
These are added as **activation-gated optional agents**: they sit at tier 0 (intake-enrichment) or tier 4 (synthesis-augmentation), the `apd-gauntlet` workflow runner dispatches them — as foreground subagents of the live session, like every other specialist — only when their preconditions are met, and they emit a finding-prefix the synthesizer recognizes.
```

- [ ] **Step 2: Fix workflow step 5 (line ~141)**

Find this exact list item:

```markdown
5. **Wire activation into the orchestrator.** Document the activation table in the agent's operator doc (e.g., `docs/attack-path-analysis.md`). The orchestrator dispatches when the precondition table evaluates to "run"; emits a skip artifact when it evaluates to "skipped silently"; or emits a `disposition: blocked` finding when it evaluates to "blocked".
```

Replace it with:

```markdown
5. **Wire activation into the runner.** Document the activation table in the agent's operator doc (e.g., `docs/attack-path-analysis.md`). The `apd-gauntlet` workflow runner dispatches the agent (as a foreground subagent) when the precondition table evaluates to "run"; emits a skip artifact when it evaluates to "skipped silently"; or emits a `disposition: blocked` finding when it evaluates to "blocked".
```

- [ ] **Step 3: Confirm no stale "orchestrator dispatches" remains**

Run:

```bash
grep -niE "orchestrator dispatches|into the orchestrator" docs/extending-agents.md
```

Expected: no matches (exit 1). If any remain, replace them the same way (runner, foreground).

- [ ] **Step 4: Lint**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add docs/extending-agents.md
git commit -m "docs(extending-agents): runner (not orchestrator) dispatches agents as foreground subagents"
```

---

## Task 7: `CHANGELOG.md` — record the docs pass

**Files:**

- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add a bullet at the end of the `[Unreleased] → ### Changed` list**

Find this exact line (the last bullet in the `### Changed` block, immediately above the blank line and `### Fixed`):

```markdown
- **Specialist agent guardrails hardened** against recurring output friction seen in multi-pack runs. The `apd-finding-schema` skill now stresses the 200-character `title` cap, mandatory YAML-quoting of colon/em-dash/leading-special scalars (an unquoted colon also aborts canonicalization), and writing findings only to the canonical tier path (no invented nested directories). The `apd-control-mappings` skill now stresses that every taxonomy mapping lives under `control_mappings` (never at the finding root) with the MITRE ATLAS key spelled `atlas` (not `mitre_atlas`), and that only concrete CWEs that resolve in the bundled catalog may be cited (no pillar/category CWEs such as CWE-320).
```

Insert this new bullet immediately after it:

```markdown
- **Documentation: foreground-execution requirement made consistent + preflight checklist added.** `running-the-gauntlet.md` gains a "Preflight: confirm scaffolding is in place" section and lists `plan-run` in the CLI reference; its Step 2 foreground statement is now the canonical source that the README, `architecture.md`, `extending-agents.md`, the workflow `meta.description`, and the `apd-orchestrator` shim all point to (run the gauntlet in-session — a background or headless launch can interrupt the subagent dispatches and leave an empty run directory). The operator install path now recommends an isolated install (venv / `pipx`), mirroring `CONTRIBUTING.md`. Docs and descriptions only — no runtime, CLI, schema, or report-template change.
```

- [ ] **Step 2: Lint**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): record foreground-execution & preflight documentation pass"
```

---

## Task 8: Full verification gate

Run every CI gate locally before opening the PR. No Python changed, so `ruff`/`mypy`/`pytest` should pass unchanged — running them confirms no doc edit accidentally broke a static-text test.

**Files:** none (verification only).

- [ ] **Step 1: Run the full test suite**

Run:

```bash
python -m pytest -q
```

Expected: PASS, same count as `main` (the only behavior-adjacent edits — `meta.description` and the orchestrator shim — are covered by `test_workflow_apd_gauntlet.py` and `test_orchestrator_deprecation.py`, both green).

- [ ] **Step 2: Run ruff + mypy (no-op confirmation)**

Run:

```bash
ruff check tools/ tests/ && mypy tools/
```

Expected: both clean (no Python files were modified).

- [ ] **Step 3: Run the full markdownlint glob + lint-agents**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md" && apd-gauntlet lint-agents --agent-dir .claude/agents/
```

Expected: both exit 0.

- [ ] **Step 4: Confirm scope discipline (no code/golden/template touched)**

Run:

```bash
git diff --name-only main...HEAD
```

Expected: only these paths — `CHANGELOG.md`, `README.md`, `docs/architecture.md`, `docs/extending-agents.md`, `docs/running-the-gauntlet.md`, `docs/superpowers/plans/2026-06-08-foreground-execution-docs.md`, `docs/superpowers/specs/2026-06-08-foreground-execution-docs-design.md`, and `.claude/agents/apd-orchestrator.md`, `.claude/workflows/apd-gauntlet.js`. No file under `tools/`, `schemas/`, `report-template/`, `templates/`, or `examples/`.

- [ ] **Step 5: Open the PR**

```bash
git push -u origin docs/foreground-execution-docs
gh pr create --base main --title "docs: make the foreground/in-session run requirement consistent + add preflight checklist" --body "Propagates the foreground-execution requirement across docs, agent/workflow descriptions, and adds a doc-only preflight checklist + isolated-install recommendation. Docs and descriptions only — no code, CLI, schema, golden, or report-template change. Spec: docs/superpowers/specs/2026-06-08-foreground-execution-docs-design.md."
```

---

## Self-review (completed by plan author)

**Spec coverage** — every spec surface maps to a task:

- §4 canonical foreground statement → Task 1 Step 4.
- §5 preflight checklist (incl. soft LLM venv nudge) → Task 1 Step 3 + Task 1 Step 1 (install) + Task 2 Step 1.
- §6.1 running-the-gauntlet (plan-run in CLI ref, Preflight, Step 2, Install venv) → Task 1.
- §6.2 README (§4 callout + Install venv) → Task 2.
- §6.3 workflow meta.description → Task 3.
- §6.4 apd-orchestrator shim → Task 4.
- §6.5 architecture.md execution model → Task 5.
- §6.6 extending-agents.md → Task 6.
- §6.7 CHANGELOG → Task 7.
- §7 done criteria → Task 8.

**Placeholder scan** — no TBD/TODO; every edit shows exact old/new text and exact commands.

**Consistency** — the foreground wording is intentionally repeated near-verbatim across surfaces (canonical in Task 1 Step 4; one-line echoes elsewhere), each pointing back to `running-the-gauntlet.md`. The Preflight anchor `#preflight-confirm-scaffolding-is-in-place` (Task 1 Step 4 link) matches the heading created in Task 1 Step 3. The venv one-liner (`python3 -m venv .venv && . .venv/bin/activate   # or: pipx install apd-gauntlet`) is identical in Task 1 Step 1 and Task 2 Step 1.
