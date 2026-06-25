# APD Gauntlet

**Multi-agent security architecture review for technical plans and running systems.** You give it a tech plan plus whatever supporting artifacts you have (PRD, source code, IaC, diagrams, threat models, ADRs); nine specialist agents — orchestrated by Claude Code — review it through nine independent security lenses; a synthesizer dedups across lenses, surfaces contradictions, and emits an advisory report with an interactive HTML view.

The output is **structured advisory input for an architect — not a gate.** It doesn't approve or block changes; it makes the human review better-informed and harder to bypass.

## 1. What it does

The review is organized around the **APD framework — three tiers, nine goals:**

```text
Trustworthiness  →  Confidentiality · Integrity · Availability
Scalability      →  Distributed · Resilient · Ephemeral
Auditability     →  Authenticity · Non-Repudiation · Immutability
```

Each run produces:

- **An advisory report** (`40-synthesis/advisory-report.md`) and a self-contained interactive **HTML report** with tabs for Start-here, Overview, Findings, Capabilities, Coverage, Threat model, Attack paths, Architecture, and Annexes.
- **Findings and capabilities**, each severity-calibrated against an explicit domain rubric and mapped to **NIST 800-53r5** and **MITRE ATT&CK** by default — plus **CWE, OWASP Top 10 / API / LLM, MITRE ATLAS, OWASP MASVS/MASWE, and D3FEND** when the run declares them.
- **Derived cross-framework views** the synthesizer computes for free: a **CAPEC bridge** (corroborating each finding's CWE ↔ ATT&CK technique), an **ATT&CK detection overlay** (the telemetry needed to detect each exposed technique), and a **compliance crosswalk** projecting NIST 800-53r5 coverage into the **HIPAA Security Rule** and **NIST CSF 2.0** (opt-in via the run's `projections:` setting).

Optional, when you supply the inputs:

- **Threat-model evaluation** — coverage / contradiction / silence against a supplied TM (Threat Dragon, MS TMT, STRIDE, LINDDUN, MAESTRO, attack trees).
- **Code reconnaissance (accuracy/quality boost)** — grounds findings in *real call-graph behavior* instead of design-doc intent, via the **DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (CBM)** graph. The `apd-code-recon` agent queries an indexed codebase with the `mcp__codebase-memory-mcp__*` tools — `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_architecture`, `search_code` — and emits a code-evidence index the nine lens agents cite (across one or many repositories). This is the single biggest lever on finding accuracy when source is available.
- **Attack-path analysis** — a BloodHound-style asset graph from declared crown jewels + attacker positions, with a **D3FEND** defensive overlay on bottleneck edges.
- **Domain packs** — calibrate severity and lens context for your domain. Six ship today: `pbm`, `api-security`, `identity-security`, `security-tooling`, `agentic-ai`, `mobile-applications`.

## 2. How to run it

**Prerequisites:** Python ≥ 3.10, [Claude Code](https://claude.com/claude-code) (with agent + skill support), and a tech plan (plus any optional artifacts) for the change you want reviewed.

**1 — Get the repo and install the CLI.** Running the gauntlet happens from a clone of this repo (the workflow runner, agents, and skills live here):

```bash
git clone https://github.com/illusconsulting/apd-gauntlet.git && cd apd-gauntlet
python3 -m venv .venv && . .venv/bin/activate
pip install apd-gauntlet      # installs the apd-gauntlet CLI + the Claude Code agent/skill bundle
apd-gauntlet --version        # confirms the CLI is on your PATH
```

**Install the Claude Code plugin (optional — loads agents and skills automatically):**

```text
/plugin marketplace add illusconsulting/apd-gauntlet
/plugin install apd-gauntlet@apd-security
```

The `apd-gauntlet` PyPI package (step above) must be on your PATH first — the plugin ships agents and skills; the workflow runner shells out to the CLI for deterministic passes. Once installed, the gauntlet runs via `/apd-gauntlet:run` (foreground, interactive — same discipline as the natural-language invocation).

**Optional: code_recon via codebase-memory-mcp (CBM)**

`codebase-memory-mcp` is an **optional** external MCP server. With `code_recon: auto` (the default) the gauntlet degrades gracefully to prose-only analysis when CBM is absent; `code_recon: enabled` requires it and hard-fails if unreachable. See the code-grounding note below and the [full guide](docs/running-the-gauntlet.md).

**2 — (Optional) See a finished report first.** A complete synthetic example ships in the repo — validate it and open its HTML, no Claude Code session required:

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/        # prints "Clean."
open examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/index.html
```

**3 — Scaffold your run.** Point `--inputs` at a folder of your artifacts and pick a domain pack:

```bash
apd-gauntlet init-run apd-$(date +%Y%m%d)-my-feature \
  --inputs ~/path/to/artifacts/ \
  --domain pbm \
  --taxonomies cwe,mitre_attack,d3fend        # optional; add owasp_api_top10, mitre_atlas, …
```

This creates `runs/apd-YYYYMMDD-my-feature/` (gitignored, so a real report is never committed by accident) and copies your artifacts into `inputs/`.

> **For code-grounded reviews (strongly recommended when you have the source — it's the biggest accuracy lever):** index the codebase into the DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (CBM) so the `apd-code-recon` agent can trace real call paths rather than infer from prose.
>
> 1. Install and run `codebase-memory-mcp` and register it in your Claude Code config so its `mcp__codebase-memory-mcp__*` tools (`index_repository`, `index_status`, `list_projects`, `get_architecture`, `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `search_code`) are reachable from the agent runtime.
> 2. Index each repo under review into a CBM **project** (e.g. ask Claude Code to `index_repository`; confirm with `list_projects` / `index_status`).
> 3. Enable it in `.apd-run.yaml`:
>
> ```yaml
> code_recon: auto             # default — runs if CBM is reachable, skips with a note otherwise
> # code_recon: enabled        # hard-fail if CBM is unreachable
> cbm_project: <project-name>  # the indexed CBM project (or repos: [{cbm_project: …}] for multi-repo systems)
> ```
>
> The agent emits `00-context/code-evidence-index.yaml` (cited by every lens) and a code-architecture brief. Full guide: **[docs/running-the-gauntlet.md](docs/running-the-gauntlet.md)**.

**4 — Run the gauntlet in Claude Code.** From the repo root, in a live session, drive the runner against your run directory:

```text
Run the apd-gauntlet workflow on runs/apd-YYYYMMDD-my-feature/
```

> **Run it in the foreground** — the nine specialists run as subagents of your live session. Don't run it in the background or headlessly, which can interrupt the dispatches and leave an empty run directory. See **[docs/running-the-gauntlet.md](docs/running-the-gauntlet.md)** for the full operator guide (preflight, code recon, threat-model and attack-path passes).

The runner builds the domain skill, runs intake, dispatches the nine lens agents by tier, then synthesizes and runs a report-completeness audit that **blocks rather than ships a degraded report**. It finishes in ~10–30 minutes depending on artifact volume.

**5 — View the report.** Validate and open it exactly like step 2:

```bash
apd-gauntlet validate runs/apd-YYYYMMDD-my-feature/
open runs/apd-YYYYMMDD-my-feature/40-synthesis/report-html/index.html
# Or serve over HTTP (recommended; some browsers block file:// for graph rendering):
#   cd runs/apd-YYYYMMDD-my-feature/40-synthesis/report-html && python3 -m http.server 8080
```

## 3. Example prompts & commands

**In a Claude Code session** (natural language — the `apd-gauntlet` skill picks it up):

- `Run the apd-gauntlet workflow on runs/apd-20260612-home-assistant/`
- `Scaffold a gauntlet run for the artifacts in ./inputs against the api-security and mobile-applications packs, then run it`
- `Run the gauntlet on runs/apd-…/ with code recon enabled and my supplied threat model`
- `Rebuild the HTML report for runs/apd-…/`

**Code-grounding with CBM** — prepare the codebase-memory-mcp graph before a code-recon run (the `mcp__codebase-memory-mcp__*` tools, called from a Claude Code session):

- `Index the repo at ./payments-service into codebase-memory-mcp` → `index_repository`
- `List the indexed CBM projects and their index status` → `list_projects` · `index_status`
- `Show the architecture of the payments-service project` → `get_architecture`
- `Trace the call path from handle_request to the audit logger; show the snippet` → `search_graph` · `trace_path` · `get_code_snippet`
- …then run the gauntlet with `code_recon: enabled` and `cbm_project: payments-service` in `.apd-run.yaml`.

**From your terminal** (the `apd-gauntlet` CLI — every command supports `--help`):

```bash
# Scaffold · validate · report
apd-gauntlet init-run <id> --inputs DIR --domain pbm [--taxonomies cwe,mitre_attack,d3fend]
apd-gauntlet validate <run-dir>                 # schema + semantic + cross-file checks
apd-gauntlet build-report <run-dir>             # (re)generate the HTML report
apd-gauntlet summarize <run-dir>                # finding / capability statistics

# Optional passes
apd-gauntlet parse-threat-model <file>          # normalize a supplied threat model
apd-gauntlet analyze-attack-paths <run-dir>     # asset graph + enumerated paths + D3FEND overlay

# Domain packs
apd-gauntlet build-domain-skill <pack>          # assemble the apd-domain skill from a pack
apd-gauntlet validate-domain <pack>             # lint a pack for completeness

# Refresh cached reference data (quarterly, or when a taxonomy publishes a new edition)
apd-gauntlet refresh-mitre        # ATT&CK techniques + mitigations + detection overlay
apd-gauntlet refresh-cwe          # CWE
apd-gauntlet refresh-capec        # CAPEC (CWE ↔ ATT&CK bridge)
apd-gauntlet refresh-d3fend / refresh-atlas / refresh-mas / refresh-owasp
apd-gauntlet refresh-crosswalks --csf2-json <export> --hipaa-json <export>   # HIPAA + CSF 2.0
```
