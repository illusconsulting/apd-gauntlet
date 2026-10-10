# Local Apps and Optional Decision Models Design

- **Date:** 2026-10-10
- **Status:** Draft for review
- **Author:** maintainer, drafted with Claude
- **Scope:** Let operators run the gauntlet and build the report from a local
  CLI, terminal UI (TUI) or browser UI without an interactive Claude Code
  session, and optionally call a decision model (Clef or Jev) through
  Cloudflare, TypeSafe or OpenRouter. Using no decision model stays the default.

## 1. Problem

1. **The gauntlet only runs inside Claude Code.** The runner
   (`.claude/workflows/apd-gauntlet.js`) depends on the Workflow tool, so a run
   needs a live, foreground Claude Code session. There is no way to start a run,
   watch progress or open the report from a plain terminal or a browser.
2. **Setup is manual and spread across docs.** An operator installs the PyPI
   engine, installs the plugin, scaffolds a run with `init-run`, edits
   `.apd-run.yaml` by hand and then prompts Claude Code to run it.
   `docs/running-the-gauntlet.md` is 31 KB.
3. **There is no decision-model layer.** The cost audit (Wave 4) found several
   steps that ask bounded questions with a fixed answer set: is this finding in
   the right lens, does its excerpt support its title, which severity does the
   rubric give. A decision model answers these with calibrated probabilities at a
   fraction of LLM cost. Nothing in the engine can call one today.

## 2. Goals / Non-Goals

**Goals**

- One install and one short setup give an operator three interfaces over the
  same engine: CLI, TUI and local web UI.
- Each interface can create a run, start or resume it, show live progress and
  cost, and build and open the HTML report.
- A run can use a decision model through Cloudflare Workers AI, TypeSafe or
  OpenRouter, each with the operator's own API key. A run can also use none.
- Secrets live in the OS keychain, an environment variable or a 1Password
  reference. They are never written to a run directory, a config file or a log.
- The local runner and the Claude Code plugin produce the same run directory,
  so either can resume the other's run and `validate` treats them alike.

**Non-Goals**

- Changing the APD framework, lenses, schemas or agent prompts.
- Routing the LLM agents through OpenRouter or any non-Claude model. The Agent
  SDK supports Anthropic API keys, Amazon Bedrock, Google Vertex and Microsoft
  Foundry; that set is the scope.
- Remote or multi-user hosting of the web UI. It binds to loopback only.
- Wave 4 decision tasks beyond the first one (finding QA). Cluster triage,
  report-claim checks, threat-model screening, edge scoring and intake triage
  reuse this layer in later plans.
- A self-hosted Clef endpoint. The provider interface leaves room for it.

## 3. Decisions

| Decision | Choice | Why |
|---|---|---|
| Run engine for local apps | Python runner using the Claude Agent SDK | Standalone, scriptable, streams progress; chosen by the maintainer 2026-10-10 |
| Decision-model protocol | TypeSafe's System One API (`state` + typed `questions` → probabilities) | All three providers speak it; one client covers them |
| Default decision model | `none` | Data egress is opt-in; plugin behavior is unchanged |
| Where a run records its decision model | `.apd-run.yaml` `decision_model:` block, no secrets | The run is self-describing and auditable; both channels honor it |
| Secret storage | Env var, then OS keychain, then `op://` reference | Never plaintext on disk; fits 1Password users |
| UI stack | Click (CLI), Textual (TUI), Starlette + Jinja2 + server-sent events (web) | Python-only, no front-end build step |
| Packaging | Optional extras: `[decide]`, `[runner]`, `[tui]`, `[web]`, `[app]` | The plugin channel's base install stays small |
| Prompts in the wheel | Bundle `.claude/agents`, `.claude/skills` and `templates/` as package data with a byte-equality CI test | The runner works from `pip install` alone, per ADR-0023 |

## 4. Architecture

```text
                 apd-gauntlet CLI ─┐
     apd-gauntlet tui (Textual) ───┼──► app.services ──► runner (Agent SDK)
apd-gauntlet web (127.0.0.1 only) ─┘        │                 │
                                             │                 ├─ CLI steps: subprocess `apd-gauntlet <cmd>`
                                             │                 ├─ agent steps: claude_agent_sdk.query()
                                             │                 └─ decide steps: DecisionClient (optional)
                                             │
                     config.yaml (no secrets) + credentials (env | keychain | op://)
                                             │
                      workspace/
                        .claude/agents, .claude/skills, templates/   (materialized from the wheel)
                        runs/<run-id>/ ... + .apd-state/{ledger.json, events.jsonl, lock}
```

- **One engine, three faces.** The CLI, TUI and web UI call `app.services`.
  None of them talks to the runner, keychain or provider APIs directly.
- **The runner owns orchestration.** It runs CLI steps as subprocesses (no LLM
  needed), agent steps through the Agent SDK, and decide steps through the
  decision client. It writes progress to `events.jsonl` and state to
  `ledger.json`, so any interface can attach to a run that another started.
- **The plugin channel keeps working.** `apd-gauntlet.js` stays the Claude Code
  runner. Both runners share the phase list; a test keeps them in step.

## 5. Decision-model providers

### 5.1 Protocol

Every provider accepts a `state` (string or JSON) and up to 64 `questions` keyed
by id (`[A-Za-z0-9_.-]{1,100}`). Question types:

- `noul`: returns the probability that a statement is true.
- `choice`: `criteria` maps option keys to descriptions; returns the chosen
  option, a confidence and per-option probabilities.
- `score`: `criteria` is an ordered list from lowest to highest; returns a
  probability-weighted score, a confidence, a legend and probabilities.

Output tokens are not billed. Clef accepts up to 4 images (PNG, JPEG or WebP,
4 MiB each); Jev accepts none.

### 5.2 Providers

| Provider | Endpoint | Credential | Models | Context |
|---|---|---|---|---|
| Cloudflare Workers AI | `POST https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/cloudflare/{model}` | `CLOUDFLARE_API_TOKEN` + account ID | `clef`, `clef-flash`, `clef-omni` | 64k, 24k, undocumented |
| Cloudflare Workers AI (Jev) | `POST …/accounts/{account_id}/ai/run`, `"model": "typesafe/jev"` with the payload under `input` | same | `typesafe/jev` | 32k |
| TypeSafe | `POST https://api.typesafe.ai/v1/systemone` | `TYPESAFE_API_KEY` | `jev-latest` | 32k |
| OpenRouter | `POST https://openrouter.ai/api/v1/systemone` | `OPENROUTER_API_KEY` | `typesafe/jev-1.13`, `~typesafe/jev-latest` | 32k |

Hosted prices per million input tokens: Clef $0.24, Clef-flash $0.038,
Clef-omni $0.15, Jev on Cloudflare $0.042. OpenRouter reports cost per call in
`usage.cost`. TypeSafe's direct price is not on its quickstart page. The catalog
lives in `data/decision-models.json` with a `verified_on` date so stale figures
are visible.

Items to confirm against a live call during Plan 1, recorded as test fixtures:
Workers AI's response envelope (`{"result": …, "success": …}`), the Jev `input`
wrapper on Cloudflare, Clef-omni's context window, and the OpenRouter auth
header (assumed `Authorization: Bearer`).

### 5.3 Client rules

- **No silent truncation.** Hosted Clef truncates `state` to fit its context.
  That breaks the evidence-discipline rule against silent caps. The client
  estimates tokens before each call (UTF-8 bytes ÷ 3, rounded up, a deliberate
  overestimate) and raises `StateTooLarge` instead of sending.
- **Bounded retries.** 429 and 5xx retry up to 3 times with exponential backoff
  and jitter, honoring `Retry-After`. 401 and 403 raise `AuthRejected` with no
  retry; the message names the provider and never echoes the key.
- **Spend cap.** The client tracks spend per run (reported cost when the
  provider gives one, else input tokens × catalog price) and raises
  `BudgetExceeded` before a call that would pass `budget_usd_per_run`
  (default $2.00).
- **Reproducibility.** Every decision record stores provider, the model id the
  provider returned, the SHA-256 of the question schema, thresholds and
  per-item probabilities.

### 5.4 First decision task: finding QA (advisory)

After each tier gate, `apd-gauntlet decide finding-qa <run> --tier <dir>` asks
three questions about every lens finding in that tier:

| Question id | Type | Asks |
|---|---|---|
| `goal` | `choice` over the 9 APD goals | Which goal is this finding substantively about? |
| `excerpt_supports_claim` | `noul` | Do the cited excerpts support the title and summary? |
| `severity` | `score` (informational → critical) | Which severity does the pack rubric's summary give? |

It writes `40-synthesis/decisions/finding-qa.yaml` with a flag per finding:
`lens_drift` (P(own goal) < 0.5), `unsupported` (P(supported) < 0.3) or
`severity_disagree` (expected score ≥ 1 level from the lens's severity). These
starting thresholds are proposals. Flags
are advisory: no finding is changed, no gate blocks, and thresholds live in the
record so a later plan can calibrate them against the committed examples.

### 5.5 Run-level opt-in

`.apd-run.yaml` gains an optional block. Absent means no decision model.

```yaml
decision_model:
  provider: cloudflare        # none | cloudflare | typesafe | openrouter
  model: clef                 # optional; provider default when omitted
```

The schema keeps `additionalProperties: false`, so `api_key` or `token` keys are
rejected. `apd-gauntlet new` writes this block from the operator's default; an
operator reviewing a PHI-handling design can set `none` for that run.

## 6. Credentials and configuration

### 6.1 User config

`<user config dir>/apd-gauntlet/config.yaml` (via `platformdirs`), validated by
`user-config.schema.json`. It holds no secrets.

```yaml
schema_version: 1
workspace: ~/apd-gauntlet
llm:
  provider: anthropic           # anthropic | bedrock | vertex | foundry
  default_model: opus           # used when an agent's frontmatter sets no model
  model_overrides: {}           # agent name -> model
  max_parallel_agents: 3
  run_budget_usd: 100.0
  extra_env: {}                 # allowlisted non-secret names, e.g. AWS_PROFILE
decision_model:
  provider: none                # default for new runs
  model: null
  cloudflare_account_id: null
  timeout_s: 30
  max_concurrency: 8
  budget_usd_per_run: 2.0
defaults:
  domains: [pbm]
  code_recon: auto
mcp_servers: {}                 # e.g. codebase-memory-mcp: {command, args}
secret_refs: {}                 # credential name -> op:// reference
```

`default_model: opus` keeps today's accuracy. The cost audit's Wave 3 model map
becomes an operator choice through `model_overrides`, not a silent change.

### 6.2 Credential resolution

Credentials: `anthropic`, `cloudflare`, `typesafe`, `openrouter`. For each, the
first match wins:

1. Environment variable: `ANTHROPIC_API_KEY`, `CLOUDFLARE_API_TOKEN`,
   `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`.
2. OS keychain through `keyring`, service `apd-gauntlet`, username = credential
   name.
3. `secret_refs.<name>`: an `op://` reference read with `op read`, 15-second
   timeout.

If no keychain backend exists (common on headless Linux), `keys set` refuses and
explains the environment-variable route. There is no plaintext fallback.

Bedrock, Vertex and Foundry use their own credential chains (AWS profile, gcloud
ADC). The runner passes `CLAUDE_CODE_USE_BEDROCK=1` (or the Vertex or Foundry
equivalent) plus the allowlisted `extra_env` names to the SDK.

Claude.ai subscription login is not an option. Anthropic's Agent SDK terms do not
allow third-party products to offer claude.ai login unless previously approved.

### 6.3 Secret hygiene

- `ResolvedSecret` keeps the value out of `repr`; `masked()` shows the last 4
  characters.
- The runner deletes decision-model keys from `os.environ` after resolving them,
  so agent subprocesses never inherit them.
- Events, ledger, decision records and web pages never contain a secret value.
  A test greps all of them for a planted canary key.

## 7. Agent SDK runner

### 7.1 Workspace and bundled prompts

The wheel carries `.claude/agents/`, `.claude/skills/` and `templates/` under
`apd_gauntlet/data/claude/` and `apd_gauntlet/data/templates/`. The repo copies
stay the source of truth for the plugin; a CI test fails if the packaged copy
differs by one byte, following the report bundle's freshness gate.

`materialize(workspace)` copies them into the workspace on first use and on
version change. It never touches `.claude/skills/apd-domain/`, which
`build-domain-skill` generates. The runner sets the SDK's `cwd` to the
workspace, so agents' relative paths (`.claude/skills/…`, `templates/…`,
`runs/<id>/…`) resolve as they do in the plugin.

### 7.2 Steps

- **CLI steps** run as `python -m apd_gauntlet.cli <cmd> …` subprocesses with
  the same arguments the workflow uses. Exit codes carry the same meaning (exit 2
  from `apply-clusters` is `AdjudicationMissing`).
- **Agent steps** call `claude_agent_sdk.query()` once per dispatch:
  - `system_prompt`: the agent file's body. The workspace also gets `schemas/`
    (from package data), because agent prompts cite `schemas/*.schema.json`.
  - `model`: the operator's `model_overrides` entry, then frontmatter `model`,
    then `default_model`.
  - `effort` from frontmatter when set; `max_turns`: 80.
  - `setting_sources=[]` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, so the
    operator's own CLAUDE.md, settings and memory never leak into a review.
  - `allowed_tools`: the frontmatter tools; agents with Bash get
    `Bash(apd-gauntlet *)`. `permission_mode="dontAsk"`.
  - `output_format`: JSON schema `agent-receipt.schema.json`; the receipt comes
    from `ResultMessage.structured_output`. The synthesizer and report auditor
    stay schema-free, as in the workflow.
  - `max_budget_usd`: the run's remaining budget.
  - `mcp_servers`: only `codebase-memory-mcp`, only for `apd-code-recon`, and
    only when configured, with strict MCP config so claude.ai connectors stay out.
- **Decide steps** run in-process after each tier gate when the run enables a
  decision model.

### 7.3 Enforcement hook

The SDK docs state that a Bash prefix rule is not a security boundary. A
`PreToolUse` hook enforces the real one and holds in every permission mode:

- **Bash:** the command's first word must be `apd-gauntlet`, and it must
  contain no shell metacharacters (`` ; & | $ ` < > `` or a newline) and no `..`.
- **Write and Edit:** the resolved path must sit inside the run directory.
- **Read, Glob and Grep:** the resolved path must sit inside the run directory
  or the workspace's `.claude/`, `templates/` or `schemas/`. Other runs in the
  workspace stay unreadable, so an injection in one review can't reach another.

Review inputs are untrusted and may carry prompt injection. The hook limits what
an injected instruction can reach: no home-directory reads, no network tools, no
writes outside the run.

### 7.4 Flow

`runner/flow.py` mirrors `apd-gauntlet.js` phase for phase: setup, intake,
inventory assembly, intake schema gate, gated code recon, threat-model author,
gated TM recon, three parallel tiers (2 retries per lens, canonicalize, tier
gate, optional finding QA), the pre-Phase-5 hard gate, decomposed synthesis with
the exit-2 adjudicator retry and synthesizer fallback, parallel TM evaluation and
attack-path analysis, C4 assembly, tmeval canonicalize, rollup with retry and
fallback, the report writer, build and audit loop (2 remediations, structural
failures block), domain-improvement capture (advisory) and closeout.

Differences from the workflow, all to the local channel's benefit:

- CLI steps cost no LLM tokens; the workflow dispatches an agent for each.
- Resume is decided in Python from `ledger.json` plus a `validate
  --schema-only` check of each step's outputs, never by an agent.
- A schema-invalid tier output gets one repair dispatch of the same lens with
  the validator's error lines before the run halts.

`runner.flow.PHASES` must equal the workflow's `meta.phases`; the existing
plan-run consistency test is extended to assert it.

### 7.5 Ledger, events, lock and budget

- `runs/<id>/.apd-state/ledger.json`: per-phase status, attempts, timestamps,
  agent turns and cost; run state `idle | running | completed | failed |
  cancelled | budget_exhausted`.
- `runs/<id>/.apd-state/events.jsonl`: append-only events (`phase_started`,
  `step_started`, `step_finished`, `tool_used`, `cost`, `warning`, `error`,
  `run_finished`). Tool events carry the tool name and path only, never file
  contents, so a review's sensitive text doesn't spread into logs.
- `runs/<id>/.apd-state/lock`: holder PID, host and start time. A second runner
  refuses; a lock whose PID is dead on the same host is reclaimed.
- **Budget:** the runner stops before starting any agent once spend reaches
  `run_budget_usd`, lets in-flight agents finish, and marks the run
  `budget_exhausted`. Resuming with `--budget` raises the cap.
- **Cancel:** Ctrl-C or `apd-gauntlet cancel` lets the current CLI step finish,
  cancels agent tasks, marks the run `cancelled` and releases the lock.

## 8. Local interfaces

### 8.1 Golden path

```bash
pipx install "apd-gauntlet[app]"
apd-gauntlet setup                       # 4 prompts, about a minute
apd-gauntlet new claims-api --inputs ~/reviews/claims-api
apd-gauntlet run claims-api
apd-gauntlet report claims-api --open
```

`apd-gauntlet tui` and `apd-gauntlet web` offer the same steps as screens.

### 8.2 Setup

`apd-gauntlet setup` asks four things, each with a detected default:

1. **Workspace folder** (default `~/apd-gauntlet`).
2. **Claude access:** detected from the environment (API key, Bedrock, Vertex or
   Foundry), or enter an Anthropic API key to store in the keychain.
3. **Decision model:** None (default), Cloudflare (Clef), TypeSafe (Jev) or
   OpenRouter (Jev). For a provider: the key (hidden input), the Cloudflare
   account ID when needed, the model, then a one-question test call that shows
   the model, latency and cost.
4. **Default domain packs** (from the bundled packs).

Every prompt has a flag (`--workspace`, `--llm-provider`, `--decision-provider`,
`--decision-model`, `--domain`, `--yes`) for unattended setup. The TUI and web
setup screens call the same `apply_setup()`.

`apd-gauntlet doctor` reports each check as pass, warn or fail: Python version,
installed extras, workspace and bundle version, Claude credentials, the Claude
Code binary the SDK needs, keychain backend, each decision provider's key and
reachability (`--online`), and CBM when a default enables code recon.

### 8.3 Commands

| Command | Purpose |
|---|---|
| `setup` | Interactive or flag-driven first-run setup |
| `doctor [--online]` | Environment checks with fixes |
| `keys set\|show\|test\|clear <name>` | Manage the four credentials |
| `new <run-id> --inputs DIR [--domain …] [--decision-provider …]` | Create a run, prompting for anything missing |
| `runs` | List runs with state, last phase, spend and report status |
| `run <run-id> [--detach] [--restart-from PHASE] [--budget USD]` | Start or resume |
| `status <run-id> [--json]` | Ledger summary |
| `cancel <run-id>` | Stop a running run |
| `report <run-id> [--build] [--open]` | Build and open the HTML report |
| `decide <task> <run-dir> [--tier DIR]` | Run a decision task |
| `tui` / `web [--port N] [--no-browser]` | Launch an interface |

Existing commands (`init-run`, `validate`, `build-report` and the rest) are
unchanged; the plugin and power users keep them.

### 8.4 TUI

A Textual app with five screens: Home (runs table, actions), Setup, New run
(form with a directory picker, domain list and decision-model select), Run
(phase list with state marks, current agent, elapsed time, spend against budget,
event log, cancel and resume) and Report (metrics summary, build, open in
browser). It tails `events.jsonl`, so it can attach to a run started elsewhere.

### 8.5 Web UI

A Starlette app with Jinja2 pages and a small vanilla-JS `EventSource` client.
Pages: runs, setup and keys, new run, run progress, report. The report is the
existing static bundle served from `runs/<id>/40-synthesis/report-html/`.

New-run inputs come from a server-side folder path or a browser folder upload
(`webkitdirectory`), capped at 200 MB and 2,000 files.

Security posture:

- Binds `127.0.0.1` only; there is no host option.
- A 256-bit token per launch, in the URL the CLI opens, is exchanged for an
  `HttpOnly`, `SameSite=Strict` cookie, then dropped from the URL by redirect.
- Requests whose `Host` isn't `127.0.0.1:<port>` or `localhost:<port>` get 403,
  which blocks DNS rebinding.
- State-changing requests need the cookie and a matching `X-APD-CSRF` header,
  and an `Origin` that matches when present.
- Headers: a `default-src 'self'` CSP, `nosniff`, `Referrer-Policy:
  no-referrer`, `frame-ancestors 'none'`. No CORS.
- Key forms are POST-only password inputs and never render a stored value.
- Static serving stays inside the report folder; symlinks are refused.

### 8.6 Input safety (all interfaces)

`scaffold_run` copies inputs with `shutil.copytree`, which follows symlinks: an
input folder holding a link to `~/.ssh` copies its target into the run. The new
`create_run` service refuses any symlink that resolves outside the input root,
and the 200 MB cap applies to folder paths as well as uploads.

### 8.7 Data egress notice

The first time a run would send data to a decision provider, the interface
states what goes where: "Finding titles, summaries and evidence excerpts for run
claims-api will be sent to Cloudflare Workers AI (clef)". The CLI needs `--yes`
or a typed confirmation; the TUI and web show a confirm dialog.
`.apd-state/consent.json` records the consent. The Claude provider is named in setup the same way.

## 9. Testing

- **No network in CI** (ADR-0017). Provider tests use `httpx.MockTransport` with
  fixtures recorded once against live endpoints and scrubbed of identifiers.
- **Keychain:** an in-memory `keyring` backend in tests; a separate test asserts
  the refusal path when no backend exists.
- **Runner:** an `AgentExecutor` protocol with the SDK implementation and a
  scripted fake. Flow tests drive the fake through success, lens retry,
  adjudicator exit 2, synthesizer fallback, audit loop, budget stop, cancel and
  resume.
- **Hook:** table-driven allow and deny cases for Bash, Write, Edit, Read, Glob
  and Grep.
- **Web:** Starlette `TestClient` for the token exchange, `Host` check, CSRF,
  headers, upload caps and path confinement.
- **TUI:** Textual's `run_test()` pilot drives each screen.
- **Canary:** a planted fake key must not appear in any file under the workspace
  or in any web response after a full fake run.
- **Coverage** stays at the repo's 85% floor; `mypy --strict` and `ruff` cover
  the new modules.

## 10. Packaging and versioning

- Base dependencies add only `platformdirs`. New extras:

  | Extra | Packages |
  |---|---|
  | `decide` | `httpx>=0.27`, `keyring>=25` |
  | `runner` | `claude-agent-sdk` plus `decide` |
  | `tui` | `textual>=0.80` |
  | `web` | `starlette>=0.40`, `uvicorn>=0.30`, `jinja2>=3.1`, `python-multipart>=0.0.9` |
  | `app` | all of the above |

- Package data adds `data/claude/**`, `data/templates/*`,
  `data/decision-models.json` and the app's templates and static files.
- This work ships as **2.0.0** on the `next` release line, while `main` keeps
  publishing 1.7.x. Pre-releases (`2.0.0aN`, `bN`, `rcN`) go to PyPI as
  pre-releases and to the `apd-security-next` plugin marketplace. GA merges
  `next` into `main`. `RELEASING.md` covers both lines. The plugin stays in
  lockstep per ADR-0023. Run-config changes are additive, so 1.7 run
  directories still validate. Bundled domain packs declare
  `framework_compat: ">=1.0.0,<3.0.0"`.

## 11. Delivery

Three plans, each shippable alone:

1. **Config, keys and decision providers:** user config, credentials, the System
   One client, `keys` and `decide`, the run-config block, finding QA, and the
   workflow step that runs finding QA when a run enables it.
2. **Agent SDK runner:** bundled prompts, ledger, lock, steps, enforcement hook,
   flow, `run`, `status` and `cancel`.
3. **Setup, TUI and web:** services, `setup`, `doctor`, `new`, `runs`,
   `report`, the TUI and the web UI, plus the quickstart rewrite.

New ADRs: 0024 (optional decision-model layer), 0025 (standalone Agent SDK
runner), 0026 (local web UI security posture).

## 12. Risks and open questions

- **Two runners can drift.** The shared `PHASES` test catches renamed or missing
  phases but not changed retry or fallback logic. Mitigation: one scenario table
  drives tests for both, and the JS structural test asserts the same retry caps.
- **Agent SDK changes.** The SDK is young; field names (`output_format`,
  `max_budget_usd`, `sandbox`) should be pinned to a tested version range.
- **Hosted decision models see review content.** For reviews of PHI-handling
  systems, confirm each provider's agreement covers this data before enabling
  it. The default stays `none`, and the egress notice makes the
  choice explicit per run.
- **Provider facts are unverified** in four places listed in §5.2. Plan 1's
  first task records live fixtures; until then those adapters are marked
  experimental.
- **Cost.** The local runner removes the per-step agent dispatches the plugin
  pays for, so a local run should cost less than a plugin run at the same models.
  The budget cap bounds the downside.
