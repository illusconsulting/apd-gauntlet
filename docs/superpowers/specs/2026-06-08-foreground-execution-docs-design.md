# Foreground-execution documentation & preflight pass — design

A documentation and description consistency pass that makes "run the gauntlet in
the **foreground / in-session**" a uniformly-stated requirement across every
operator- and Claude-facing surface, and gives operators a **preflight
checklist** to confirm all scaffolding is in place before launching a run.

**Docs + descriptions only.** No CLI/code changes, no new commands, no
golden/example regeneration, no report-template/bundle changes.

## 1. Background & source of truth

The gauntlet's specialists run as **subagents of the live Claude Code session**
that launches a run. Driving the runner through the background `Workflow`
primitive (or headlessly) can interrupt those subagent dispatches mid-flight —
the subagents are cancelled, no phase output is written, and the run directory is
left empty or partial. This has recurred across multiple golden runs
(data-formulator 2026-06-06/07, open-notebook 2026-06-07) and is the single most
load-bearing operational lesson the run notes carry: *drive the runner in the
foreground.*

The remediation work already partly landed in **PR1 of the gauntlet-hardening
plan** (`b689439`, #90):

- `apd-gauntlet plan-run <run-dir>` — emits the deterministic ordered
  phase → step (CLI / AGENT) foreground-drive checklist.
- The workflow runner is now interruption-resilient and throws a distinct
  `"run interrupted at phase <X> — re-invoke in the FOREGROUND to resume
  (idempotency guards replay completed phases)"` error.
- `.claude/workflows/apd-gauntlet.js` header declares the runner
  `INTERACTIVE / FOREGROUND`.
- `docs/running-the-gauntlet.md` Step 2 gained a foreground section
  (lines 266–289).

What is **not** yet done — and is the scope of this spec — is propagating the
requirement consistently to the remaining surfaces, and giving operators a
single preflight checklist:

- `plan-run` is missing from the CLI command-reference table in
  `running-the-gauntlet.md` (documented in Step 2 prose but unlisted).
- `README.md` §4 presents the background-workflow invocation as the primary path
  with no foreground warning or preflight pointer.
- The workflow `meta.description` does not mention the foreground requirement
  (only the file's header comment does).
- `docs/architecture.md` describes the workflow runner but not the
  foreground/in-session execution model.
- `docs/extending-agents.md` still uses stale "the orchestrator dispatches"
  language and says nothing about foreground dispatch for new agents.
- No consolidated "confirm scaffolding is in place" checklist exists.

## 2. Decisions (locked)

These were settled with the requester before writing this spec:

1. **Preflight form = documentation checklist only.** Add a "Preflight: confirm
   scaffolding is in place" section that walks the operator through the
   **existing** commands. No new `preflight`/`doctor` command, no `plan-run`
   code changes. Zero golden churn.
2. **Foreground fact across the 20 agent descriptions = central + targeted.** One
   authoritative foreground statement in the docs/workflow; a foreground-dispatch
   clause only on operator-facing surfaces (workflow `meta.description`, the
   `apd-orchestrator` deprecation shim, and `extending-agents.md`). The nine lens
   specialists and the other specialist agents keep their lens-focused
   descriptions — no boilerplate bloat.
3. **Process = full spec + plan.** This document, then the writing-plans flow,
   then execution.
4. **Recommend an isolated install.** Mirror `CONTRIBUTING.md`'s venv convention
   on the operator install path: recommend installing the CLI into a virtual
   environment (`python3 -m venv`) or via `pipx`. Soft, not mandatory — the
   guidance is "use an isolated env unless the CLI is already isolated / on
   PATH," so it neither nags nor forces a fresh venv when one already exists.

## 3. Goal & non-goals

**Goal.** A reader arriving at any operator- or Claude-facing surface learns
(a) that the gauntlet must be driven in the foreground and why, and (b) where to
find the supported foreground path and the preflight checklist. An operator can
confirm, before launching, that every piece of scaffolding their `.apd-run.yaml`
implies is present.

**Non-goals.**

- No new CLI command (`preflight`/`doctor`) and no changes to `plan-run`'s code.
- No edits to the nine lens specialists or the non-operator-facing specialist
  agent descriptions.
- No golden/example run regeneration; no report-template or HTML-bundle changes.
- No change to runtime behavior of the runner — it is already foreground and
  interruption-resilient.

## 4. The canonical foreground statement (single source of truth)

The authoritative paragraph lives in **`running-the-gauntlet.md` Step 2**
(refined from the existing block). Every other surface carries a one-line version
that links back to it, so the message cannot drift. The canonical statement
encodes exactly these points:

- The runner dispatches each specialist as a **subagent of the live Claude Code
  session**, so the gauntlet is an **interactive, in-session (foreground)**
  operation.
- Driving it via the background `Workflow` tool or headlessly can **interrupt the
  dispatches mid-flight** — subagents are cancelled, no phase output is written,
  and the run directory is left empty or partial.
- There are two supported foreground modes, both in-session:
  1. Prompt Claude — *"Run the apd-gauntlet workflow on `<run-dir>`"* — in a live
     session.
  2. Explicit drive — `apd-gauntlet plan-run <run-dir>` emits the ordered
     phase → step checklist (each step tagged `CLI` = run via Bash, or `AGENT` =
     dispatch as a foreground agent); work the list top to bottom.
- If a run is interrupted, **re-invoke in the foreground**; the runner is
  resumable and idempotency guards replay completed phases.

## 5. Preflight checklist (doc-only, existing commands)

New **"Preflight: confirm scaffolding is in place"** section in
`running-the-gauntlet.md`, placed between Step 1 (Scaffold) and Step 2 (Run),
with a one-line pointer from `README.md`. Each item maps to an existing command
or signal — nothing new is built. Items gated on `.apd-run.yaml` content are
marked conditional.

When Claude walks an operator through this checklist, it should recommend an
isolated install (an activated virtual environment, or `pipx`) at the first step
*unless the CLI is already isolated / on PATH* — a soft nudge, not a gate.

| Check | Command / signal | When |
|---|---|---|
| CLI installed in an isolated env; version matches `plugin.json` | `apd-gauntlet --version` (install via `python3 -m venv .venv && . .venv/bin/activate && pip install apd-gauntlet`, or `pipx install apd-gauntlet`) | always |
| Run scaffolded (`runs/<id>/` + `.apd-run.yaml`) | output of `init-run` | always |
| Run-config valid | `apd-gauntlet validate-run-config runs/<id>/.apd-run.yaml` | always |
| Domain pack(s) valid | `apd-gauntlet validate-domain <pack…>` | always |
| `apd-domain` skill built (with per-goal sidecars) | `apd-gauntlet build-domain-skill <pack…>` | always |
| Agent frontmatter clean | `apd-gauntlet lint-agents` | always |
| Declared taxonomy catalogs present | `refresh-{mitre,mitre-mobile,cwe,owasp,d3fend,atlas}` as the `taxonomies:` list requires | conditional |
| CBM reachable + codebase indexed | CBM `index_status` / server registered | if `code_recon: enabled`/`auto` |
| Threat-model file exists at declared path | filesystem check | if `threat_model:` declared |
| `crown_jewels` + `attacker_positions` declared (run-config or domain default) | inspect `.apd-run.yaml` / domain `domain.yaml` | if attack-path output wanted |
| Dry-run the gated phase order | `apd-gauntlet plan-run runs/<id>` | recommended last step |

The section closes by pointing to `plan-run` as both the final preflight
confidence check and the supported foreground-drive path — tying preflight and
Step 2 together.

## 6. Surface change list

Each unit is a self-contained doc/description edit. The canonical statement lives
in `running-the-gauntlet.md`; the rest link to it.

1. **`docs/running-the-gauntlet.md`**
   - Add a one-line isolated-install recommendation to the **Install** section
     (`python3 -m venv` or `pipx`), mirroring `CONTRIBUTING.md`.
   - Add `plan-run` to the CLI command-reference list (§ near lines 19–45) with a
     one-line description naming it the foreground-drive checklist emitter.
   - Add the **Preflight** section (§5) between Step 1 and Step 2.
   - Refine the Step 2 foreground block to be the canonical statement (§4) and
     cross-link the Preflight section and `plan-run`.

2. **`README.md` §4 "Run the gauntlet" + §Install**
   - Add a one-line isolated-install recommendation to the **Install** section
     (venv / `pipx`), consistent with running-the-gauntlet.md.
   - Add a concise foreground callout (run in a live session; do not drive via the
     background `Workflow` tool / headless) linking to the canonical statement.
   - Add a one-line preflight pointer to the new section.

3. **`.claude/workflows/apd-gauntlet.js`**
   - Append a short foreground clause to `meta.description`. (Safe: the workflow
     static-text test asserts only that `description:` is present, not its
     content.)

4. **`.claude/agents/apd-orchestrator.md`**
   - Add a foreground/in-session line to the body (and optionally a clause to the
     `description`). **Must preserve the four facts pinned by
     `test_orchestrator_deprecation.py`:** the "Deprecated"/"DEPRECATED" marker,
     the workflow-runner pointer, the design-spec reference, and a single
     trailing newline.

5. **`docs/architecture.md`**
   - Add a short "Execution model: foreground / in-session" note near the
     workflow-runner description (≈ lines 27 / 45): specialists are session
     subagents; foreground requirement; interruption behavior; resume.

6. **`docs/extending-agents.md`**
   - Replace stale "the orchestrator dispatches" language (≈ lines 121, 141) with
     "the apd-gauntlet workflow runner dispatches (as foreground subagents)".
   - Note that new activation-gated agents also run as foreground subagents and
     must carry the idempotency guard.

7. **`CHANGELOG.md`**
   - One entry under the docs section recording the foreground-execution &
     preflight documentation pass.

## 7. Validation & done criteria

- `markdownlint` over the **full CI glob** (`docs/**`, `.claude/**`,
  `domains/**`) — run locally before push; a prior PR was reddened by linting
  only the edited file.
- `apd-gauntlet lint-agents` green (orchestrator frontmatter still valid).
- `tests/test_orchestrator_deprecation.py` and
  `tests/test_workflow_apd_gauntlet.py` green after the shim and
  `meta.description` edits.
- Full `pytest` green — no behavior change expected.
- `check_report_template_freshness` unaffected (no bundle touched) — confirm it is
  not triggered.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Editing `meta.description` breaks a static-text assertion | Verified the test asserts only `"description:" in text`; append, don't restructure. |
| Editing the orchestrator shim breaks `test_orchestrator_deprecation.py` | Preserve the four pinned facts (marker, runner pointer, design-spec ref, single trailing newline); add the foreground note around them. |
| Message drift across surfaces | One canonical statement in `running-the-gauntlet.md`; every other surface states one line and links back. |
| markdownlint failure on push | Run the full CI glob locally before committing. |

## 9. Out of scope (YAGNI)

No `preflight`/`doctor` command, no `plan-run` code changes, no edits to the 19
lens/specialist agent descriptions, no golden/example regeneration, no
report-template/bundle changes, no runner behavior change.
