# apd-gauntlet — Quickstart

**Multi-agent security architecture review for technical plans and running systems.** You give it a
tech plan plus any supporting artifacts; nine specialist AI agents review it through nine security
lenses; it produces an advisory report with an interactive HTML view.

The output is **structured advisory input for a human architect — not a gate.** It doesn't approve or
block changes; it makes the human review better-informed and harder to bypass.

There are two ways to drive it:

- **[Just chat with Claude](#the-easiest-way-just-chat-with-claude)** (recommended) — describe what you
  want in plain language and Claude does the rest.
- **[Run the commands yourself](#prefer-explicit-commands-the-cli-path)** — for scripting, CI, or when
  you want explicit control.

Both use the same engine under the hood.

## How it works (the mental model)

There are **two pieces**, and a real review uses both:

| Piece | What it does | How you get it |
| --- | --- | --- |
| **`apd-gauntlet` CLI** (Python) | The deterministic engine — scaffolds runs, validates them, builds the HTML report | `pip install apd-gauntlet` |
| **The agents** (Claude Code) | The actual security analysis — the nine lenses, synthesis, attack paths | Run inside a **Claude Code** session |

So every review follows the same shape: **set up a run → let the agents analyze it → read the report.**
The CLI does the deterministic bookkeeping; the agents (driven from a live Claude Code session) do the
thinking.

## What you'll need

- **Python ≥ 3.10**
- **[Claude Code](https://claude.com/claude-code)** (the agents run as subagents of a live session)
- A **tech plan** to review, plus any optional artifacts (PRD, source code, IaC, diagrams, threat
  models, ADRs)

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install apd-gauntlet
apd-gauntlet --version          # should print 1.7.0
```

To use the chat-driven workflow, Claude also needs the agents and skills. Get them **either** way:

- **Clone the repo** and open it in Claude Code (the agents + skills live under `.claude/`):

  ```bash
  git clone https://github.com/illusconsulting/apd-gauntlet.git && cd apd-gauntlet
  ```

- **Or install the Claude Code plugin** (from any project):

  ```text
  /plugin marketplace add illusconsulting/apd-gauntlet
  /plugin install apd-gauntlet@apd-security
  ```

The plugin still needs the `apd-gauntlet` CLI (the `pip install` above) on your PATH — the workflow
shells out to it for the deterministic passes.

## The easiest way: just chat with Claude

Once Claude Code has the apd-gauntlet skill and agents available (you cloned the repo or installed the
plugin), **you don't have to memorize any commands.** Describe what you want in plain language. Claude
recognizes the intent, scaffolds the run with the CLI, dispatches the nine specialist agents, and builds
the report — then you can ask follow-up questions about the results in the same conversation.

> **Run it in the foreground.** The nine specialists run as subagents of your live session. Don't ask
> Claude to run it in the background or headlessly — that can interrupt the agent dispatches and leave an
> empty run folder. Keep the session open while it works (~10–30 minutes).

### Start a review from scratch

You point Claude at a folder of artifacts and a domain pack; it scaffolds and runs in one go.

```text
Set up and run an apd-gauntlet review of the tech plan and diagrams in ./my-inputs,
using the api-security domain pack.
```

```text
I have a PRD, Terraform, and a threat model in ~/review-bundle/ for a mobile banking app.
Scaffold a gauntlet run against the mobile-applications pack and run it.
```

```text
Which domain pack should I use for an internal SSO / identity service?
Then scaffold and run a review of the design doc in ./inputs with that pack.
```

### Run a review you've already scaffolded

```text
Run the apd-gauntlet workflow on runs/apd-20260625-my-feature/
```

```text
Drive the gauntlet on runs/apd-20260625-my-feature/ in the foreground.
```

### Turn on the optional analyses

```text
Run the gauntlet on runs/apd-20260625-my-feature/ with code recon enabled
against the CBM project "payments-service" and my supplied threat model at
inputs/threat-model.json.
```

```text
Scaffold a run against the api-security and mobile-applications packs with the
cwe, owasp_api_top10, and mitre_atlas taxonomies, then run it.
```

### Use code grounding (the biggest accuracy boost)

If you have the source code, index it first so the agents trace real call paths instead of inferring
from prose:

```text
Index the repo at ./payments-service into codebase-memory-mcp, confirm the index
status, then scaffold a gauntlet run with code recon enabled pointing at that project.
```

```text
List the indexed codebase-memory projects and their status.
```

### Work with the results

After a run, keep chatting in the same session:

```text
Summarize the critical and high findings from runs/apd-20260625-my-feature/.
```

```text
What are the top attack paths and bottleneck edges in the latest run?
```

```text
Which findings have no NIST 800-53 control mapping, and why?
```

```text
Open the HTML report for runs/apd-20260625-my-feature/.
```

### Rebuild or fix the report

```text
Rebuild the HTML report for runs/apd-20260625-my-feature/.
```

```text
The report failed its completeness audit — what's missing and how do I fix it?
```

### Tip: the slash command

If you installed the plugin, `/apd-gauntlet:run` is a shortcut that preflights the CLI, checks the run is
scaffolded, and drives the runner in the foreground — the same thing the natural-language prompts trigger.

## Prefer explicit commands? The CLI path

The same lifecycle, done by hand. Useful for scripting, CI, or full control.

### Step 1 — See a finished report first (no AI session needed)

A complete synthetic example ships in the repo source. This proves your install works and shows you the
output:

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/      # prints "Clean."
open examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/index.html
```

### Step 2 — Scaffold your run

Put the artifacts you want reviewed in a folder, then:

```bash
apd-gauntlet init-run apd-$(date +%Y%m%d)-my-feature \
  --inputs ~/path/to/your/artifacts/ \
  --domain pbm \
  --taxonomies cwe,mitre_attack,d3fend
```

This creates `runs/apd-YYYYMMDD-my-feature/` containing your copied `inputs/`, the tier folders
(`00-context`, `10-trustworthiness`, `20-scalability`, `30-auditability`, `40-synthesis`), and a
`.apd-run.yaml` config you can edit:

```yaml
run_id: apd-20260625-my-feature
domains:
  - pbm
framework_version: 1.7.0
code_recon: auto          # runs code analysis if available, skips otherwise
taxonomies:
  - cwe
  - mitre_attack
  - d3fend
```

`runs/` is gitignored, so a real report is never committed by accident.

### Step 3 — Run it in Claude Code

Open a live Claude Code session in the repo and tell it to run (this is the one step that needs the
agents — it cannot be done from the shell alone):

```text
Run the apd-gauntlet workflow on runs/apd-20260625-my-feature/
```

It builds the domain skill, runs intake, dispatches the nine lens agents by tier, synthesizes, and runs a
completeness audit that **blocks rather than ships a degraded report.**

### Step 4 — View the report

```bash
apd-gauntlet validate runs/apd-20260625-my-feature/         # confirms it's complete
open runs/apd-20260625-my-feature/40-synthesis/report-html/index.html
# If graphs don't render from file://, serve over HTTP:
#   cd runs/apd-20260625-my-feature/40-synthesis/report-html && python3 -m http.server 8080
```

## What you get

The interactive HTML report (under `runs/<id>/40-synthesis/report-html/`) has tabs for **Start-here,
Overview, Findings, Capabilities, Coverage, Threat model, Attack paths, Architecture, and Annexes.** Each
finding is severity-calibrated against your domain pack and mapped to NIST 800-53r5 and MITRE ATT&CK by
default (plus CWE, OWASP, ATLAS, MASVS/MASWE, and D3FEND when you declare them).

## The CLI commands you'll actually type

Out of the engine's full command surface, these are the operator-facing ones — everything else is called
by the workflow runner, not by you:

| Command | What it does |
| --- | --- |
| `apd-gauntlet --version` | confirm the install |
| `apd-gauntlet validate <run-dir>` | check a run is structurally complete |
| `apd-gauntlet init-run <id> --inputs … --domain …` | scaffold a new run |
| `apd-gauntlet build-report <run-dir>` | rebuild the HTML report (also done automatically) |
| `apd-gauntlet validate-domain <pack>` | check a domain pack is valid |

## Optional add-ons

Turn these on in `.apd-run.yaml` (or just ask Claude to):

- **Code grounding (biggest accuracy boost)** — index your source into
  [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (CBM) and set `code_recon: enabled`
  plus `cbm_project: <name>` so the `apd-code-recon` agent traces real call paths instead of inferring from
  prose.
- **Threat-model evaluation** — add `threat_model: <path>` (Threat Dragon, MS TMT, STRIDE, LINDDUN, …); the
  gauntlet checks coverage, contradictions, and silence against your model.
- **Attack-path analysis** — declare crown jewels and attacker positions in your inputs; it builds a
  BloodHound-style asset graph with a D3FEND defensive overlay on the bottleneck edges.
- **More taxonomies** — add to `taxonomies:` (e.g. `owasp_api_top10`, `mitre_atlas`, `cwe`, `d3fend`).
- **Domain packs** — six ship today: `pbm`, `api-security`, `identity-security`, `security-tooling`,
  `agentic-ai`, `mobile-applications`. The pack calibrates severity and lens context for your domain.

## Troubleshooting

- **`No matching distribution` on `pip install`** — upgrade pip and confirm Python ≥ 3.10.
- **Empty run folder after a run** — it was driven in the background; re-run in a **foreground** Claude
  Code session and keep it open.
- **`validate` reports errors** — the run is incomplete; re-run the gauntlet (the report gate blocks
  shipping degraded output by design).
- **Graphs blank in the HTML** — serve the report over `python3 -m http.server` instead of opening
  `file://`.
- **Code recon was skipped** — that's expected with `code_recon: auto` when CBM isn't reachable; the run
  falls back to prose-only analysis. Set `code_recon: enabled` to require it.

## Go deeper

- [README](../README.md) — overview and the full feature list.
- [Running the gauntlet](running-the-gauntlet.md) — the complete operator guide (preflight, code recon,
  threat-model and attack-path passes, the full subcommand list).
- [Architecture](architecture.md) — how the agents, tiers, and run lifecycle fit together.
- [Adapting to other domains](adapting-to-other-domains.md) — write your own domain pack.
