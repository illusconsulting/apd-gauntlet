# Running the Gauntlet

Operator guide. How to set up a run, run the gauntlet, and interpret the outputs.

## Prerequisites

- Claude Code with agent and skill support.
- Python ≥ 3.10 (for the `apd-gauntlet` validator CLI).
- A tech plan or design document for the change you want to review.
- Optional but recommended: PRD, source code, IaC, architecture diagrams, threat models, ADRs, runbooks, test reports.

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
apd-gauntlet validate <run-dir>                  # three-pass validation
apd-gauntlet init-run <run-id> --inputs DIR --domain pbm [--domain api-security] ...
apd-gauntlet build-domain-skill <pack...>        # compile one or more packs into the apd-domain skill
apd-gauntlet validate-domain <pack...>           # validate one or more domain packs
apd-gauntlet validate-run-config <config>        # validate a .apd-run.yaml against the schema
apd-gauntlet plan-run <run-dir>                  # emit the ordered foreground-drive checklist (CLI/AGENT steps) for a run
apd-gauntlet canonicalize <run-dir>              # idempotent structural canonicalizer (envelope + deterministic IDs + cross-refs)
apd-gauntlet assemble-inventory <run-dir>        # mint asset-/idn-/tb- inventory ids + wire trust-boundary crosses (by name)
apd-gauntlet draft-domain-improvements <run-dir> # draft a pack patch from a run's captured opportunities
apd-gauntlet domain-coverage-delta <run-dir>     # deterministic pack-coverage gaps for a run
apd-gauntlet summarize <run-dir>                 # finding/capability statistics
apd-gauntlet check-ids <yaml-file>               # verify deterministic record IDs
apd-gauntlet lint-agents                         # validate agent file frontmatter
apd-gauntlet parse-threat-model <path>           # parse a SUPPLIED threat model file into a normalized YAML graph
apd-gauntlet author-threat-model <run-dir>       # v1.7+: build the deterministic baseline threat-model skeleton
apd-gauntlet analyze-attack-paths <run-dir>      # v1.4+: run the attack-path analyzer
apd-gauntlet build-report <run-dir>              # (re)generate the HTML advisory report
apd-gauntlet audit-report <run-dir>              # cross-check data.js vs YAMLs; enforces 8 completeness checks (structural + editorial)
apd-gauntlet refresh-mitre                       # refresh the cached MITRE ATT&CK crosswalk
apd-gauntlet refresh-mitre-mobile                # additively merge the ATT&CK Mobile matrix into the bundled catalogs
apd-gauntlet refresh-nist                        # refresh the bundled NIST 800-53r5 control catalog
apd-gauntlet refresh-cwe                         # refresh MITRE CWE reference data (also projects Category entries)
apd-gauntlet refresh-owasp                       # refresh OWASP Top 10 / API Top 10 / LLM Top 10 reference data
apd-gauntlet refresh-d3fend                      # refresh MITRE D3FEND reference data
apd-gauntlet refresh-atlas                       # refresh MITRE ATLAS technique-title reference data (AML.T####)
apd-gauntlet refresh-mas                         # refresh OWASP MASVS + MASWE mobile taxonomy reference data
```

`build-domain-skill` and `validate-domain` take one or more space-separated pack names as positional arguments (e.g. `apd-gauntlet build-domain-skill pbm api-security`). By default, `build-domain-skill` also emits per-goal sidecars under `.claude/skills/apd-domain/by-goal/<goal>.md` — one slice per APD goal — which lens agents load to bound their context on multi-domain runs; pass `--full-only` to write only the full cross-goal `SKILL.md` and suppress the sidecars. The decomposed-synthesis subcommands — `rollup`, `cluster-candidates`, `apply-clusters`, `audit-report` — are driven by the `apd-gauntlet` workflow runner, not invoked by operators.

## Step 1: Scaffold the run

Pick a run id. Convention: `apd-YYYYMMDD-<short-slug>` (e.g. `apd-20260601-claim-event-bus`).

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ~/my-project/tech-plans/claim-event-bus/ \
  --domain pbm
```

This creates `runs/apd-20260601-claim-event-bus/` with subdirectories for each phase output, copies your artifacts into `inputs/`, and records the active domain.

To review a change against more than one domain pack, repeat the `--domain` flag:

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ~/my-project/tech-plans/claim-event-bus/ \
  --domain pbm --domain api-security
```

The scaffolded `.apd-run.yaml` records every selected pack as a `domains:` list:

```yaml
domains:
  - pbm
  - api-security
```

In a multi-domain run, the change is reviewed across all selected packs at once: `build-domain-skill` merges them into one `apd-domain` skill (union/dedup of crown jewels, attacker positions, and trust boundaries; concatenated per-pack pattern catalogs), and every specialist loads the merged calibration.

## Code reconnaissance (optional)

The framework can include an optional code-grounded view of the system under review, produced by `apd-code-recon` using the DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) (CBM) graph. When enabled, specialists may cite call-graph and symbol evidence in addition to document evidence, which is particularly load-bearing for findings under Non-Repudiation (audit log coverage), Authenticity (identity-verification call paths), and Distributed (outbound-edge topology).

### When to enable

Enable code recon when:

- The artifact set includes a substantial codebase (more than ~20 source files), and
- A CBM server is available and has indexed the same codebase, and
- The reviewer wants findings grounded in actual call-graph behavior rather than design-doc intent only.

Skip code recon (`code_recon: disabled`) for tech-plan-only reviews where no code is available yet.

### Setup

1. Install and run `codebase-memory-mcp` per its [project README](https://github.com/DeusData/codebase-memory-mcp).
2. Index the codebase you intend to review.
3. Register the CBM server in your Claude Code configuration so its tools (`mcp__codebase-memory-mcp__*`) are reachable from the agent runtime.

### Configuration

In `.apd-run.yaml`:

```yaml
code_recon: auto  # default — runs if CBM reachable, skips with note otherwise
# code_recon: enabled  # hard-fail if CBM not reachable
# code_recon: disabled # never dispatch
cbm_project: <project-name>  # optional CBM project pointer
```

### Outputs

When the agent runs successfully, two files appear under `00-context/`:

- `code-architecture-brief.md` — human-readable narrative.
- `code-evidence-index.yaml` — machine-readable index that specialists cite.

The validator recognizes `code-evidence-index.yaml` as a known artifact source automatically; no manual amendment of the intake brief is required.

### Skipping behaviour

If CBM is unreachable when the recon agent runs:

- Under `code_recon: enabled`, the run halts; surface the CBM availability issue, then either fix it or relax to `auto`.
- Under `code_recon: auto`, the agent writes `00-context/code-recon-skipped.md` and the run proceeds without code-grounded evidence.

### Multi-repo systems

A system that spans more than one repository (e.g. an API service, an async
worker, and a frontend, each its own CBM project) declares all of them with a
`repos[]` array in `.apd-run.yaml`:

```yaml
subject: Polyglot Payments Platform   # prefer an explicit title in multi-repo mode
code_recon: enabled
repos:
  - cbm_project: payments-api
    role: primary                     # seeds the report title and crown-jewel proximity
    repo_path: services/api           # optional, relative to inputs/
  - cbm_project: payments-worker
    role: dependency
  - cbm_project: payments-frontend
```

`cbm_project` (singular) remains valid for single-repo runs; `repos[]` is the
multi-repo form. When `repos[]` is declared, `apd-code-recon`:

1. Runs its passes once per repo, calling every CBM tool with that repo's
   `project:`, and tags each evidence entry with `repo: <cbm_project>`.
2. Requests CBM's `index_repository(mode='cross-repo-intelligence', ...)` to
   link the projects, then records the returned `CROSS_HTTP_CALLS` /
   `CROSS_ASYNC_CALLS` / `CROSS_CHANNEL` edges as `kind: edge` index entries.
   These cross-service edges let attack-path analysis traverse hops that cross
   a repo boundary instead of stopping inside one service.
3. Records per-repo provenance in `code-evidence-index.yaml`'s top-level
   `repos[]` (one `{cbm_project, indexed_commit_sha}` per repo).

In multi-repo mode prefer an explicit `subject:` for the report title; absent
one, the report falls back to the `role: primary` repo (else the first).

> **Upstream caveat (CBM provider-discovery defect).** A separate CBM defect
> can leave only a subset of extraction providers registered (the observed
> "1/6 providers indexed" symptom), producing a *partial* index that silently
> yields confidently-wrong "no auth on this path" conclusions. This repo can
> only **detect and surface** that: `validate` emits a non-blocking warning of
> the form `declared repo '<name>' has zero attributed entries (partial
> index ...)` when a declared repo contributes no evidence. The provider-
> discovery fix itself is **upstream CBM**, not patchable here. Once the
> upstream fix ships, pin a minimum CBM version in this section and in the
> setup steps above. Track: file the upstream CBM issue and reference it here.

### Taxonomy scope (v1.2+)

Declare taxonomies in `.apd-run.yaml` or pass `--taxonomies cwe,mitre_attack,d3fend,owasp_api_top10` to `init-run`. CWE, ATT&CK, and D3FEND are default-on; OWASP variants are opt-in (gated on the SUT having the relevant web/API/LLM surface). To include MITRE ATLAS coverage (adversarial ML technique IDs of the form `AML.T####`), add `mitre_atlas` to the `taxonomies` list in `.apd-run.yaml`:

```yaml
taxonomies:
  - cwe
  - mitre_attack
  - d3fend
  - mitre_atlas   # opt-in: MITRE ATLAS adversarial-ML finding taxonomy
```

Refresh the bundled ATLAS data with `apd-gauntlet refresh-atlas`. When `mitre_atlas` is declared, the rollup phase includes an atlas-coverage summary. See [docs/taxonomy-mappings.md](taxonomy-mappings.md) for the full operator guide.

Selecting the `mobile-applications` pack (`--domain mobile-applications`) auto-seeds the OWASP **MASVS** and **MASWE** mobile taxonomies into `.apd-run.yaml`'s `taxonomies:` list (declared as `taxonomies: [masvs, maswe]` in the pack's `domain.yaml`), so you do not name them explicitly:

```yaml
taxonomies:
  - masvs   # auto-seeded by the mobile-applications pack
  - maswe   # auto-seeded by the mobile-applications pack
```

Refresh the bundled MAS reference data with `apd-gauntlet refresh-mas`. When `masvs`/`maswe` are declared, the rollup phase includes MASVS and MASWE coverage summaries. See [docs/taxonomy-mappings.md](taxonomy-mappings.md) for the full operator guide.

### Threat model evaluation (v1.3+)

If the run includes a threat model, declare it in `.apd-run.yaml` or pass
`--threat-model <path>` to `init-run`:

```yaml
threat_model: inputs/threat-model.json
methodology_hint: stride   # optional; auto-detected if absent
# methodology_hint: maestro  # routes the threat model through the CSA MAESTRO
                              # free-form envelope (L1–L7 → APD-goal mapping)
```

`apd-threat-model-recon` (tier-0) parses the file into the sibling
`00-context/threat-model-supplied-normalized.yaml`;
`apd-threat-model-evaluator` (tier-4) emits coverage-gap, contradiction, and
silence findings against the synthesizer's dedup'd specialist findings. See
[docs/threat-modeling.md](threat-modeling.md) for the full operator guide.

### Authored baseline threat model (v1.7+)

Independent of any supplied threat model, the gauntlet **always** authors a
grounded baseline. The tier-0, always-on `apd-threat-model-author` agent runs
after intake/code-recon and before tier-1. It drives the deterministic CLI floor
`apd-gauntlet author-threat-model <run-dir>` to build a
surface x applicable-STRIDE skeleton, then grounds or blocks each cell and emits:

- `00-context/threat-model-normalized.yaml` — the canonical authored baseline
  (`generated_by: threat_model_author`)
- `00-context/threat-model-authored.md` — the human-readable render

Because the authored baseline always exists, `apd-threat-model-evaluator` always
runs. When you also supply a threat model, the evaluator runs the
supplied-vs-authored comparator (omission findings + a delta section in the
coverage report). The evaluator never grades the authored baseline's
coverage/silence against itself — see the anti-tautology carve-out in
[docs/threat-modeling.md](threat-modeling.md) and
[docs/adrs/0013-author-grounded-baseline-threat-model.md](adrs/0013-author-grounded-baseline-threat-model.md).

### Attack-path analysis (v1.4+)

When the run has at least one declared crown jewel and at least one declared
attacker position — either inherited from the active domain pack or set in
`.apd-run.yaml` — the tier-4 `apd-attack-path-analyzer` enumerates
BloodHound-style attack paths over a partial graph assembled from the
intake, the normalized threat model, the code-evidence index, the
specialist findings, and the dedup'd capabilities.

Declare crown jewels, attacker positions, and enumeration tuning in
`.apd-run.yaml`:

```yaml
crown_jewels:
  - phi_store
  - pde_submission_pipeline
attacker_positions:
  - external_internet
  - compromised_pharmacy_credential
  - compromised_vendor_integration
attack_path_analysis:
  max_hop: 6
  max_paths_per_pair: 25
  bottleneck_threshold: 4
```

If `crown_jewels` and `attacker_positions` are absent from `.apd-run.yaml`,
the analyzer falls back to the values declared in the active domain pack's
`domain.yaml`. The bundled PBM pack ships with three crown jewels and five
attacker positions. The run-config values fully replace the domain defaults
when present.

The analyzer is **activation-gated**: when neither the domain pack nor the
run-config declares any crown jewels (or any attacker positions), the
analyzer writes `40-synthesis/attack-path-analyzer-skipped.txt` and the
synthesis proceeds without attack-path output. The one exception is when
the operator *explicitly* sets `crown_jewels: []` against a domain that
declares some — that is treated as a deliberate misconfiguration and emits
a `disposition: blocked` finding rather than a silent skip.

Invoke the analyzer in two ways:

- **Inline as part of the run.** When the runner reaches Phase 5
  (Synthesis), it dispatches `apd-attack-path-analyzer` if the activation
  preconditions are satisfied. No extra operator action is required.
- **Stand-alone, post-hoc.** After a run completes, re-run the analyzer
  against an existing run directory:

  ```bash
  apd-gauntlet analyze-attack-paths runs/apd-20260601-claim-event-bus/
  ```

  This is the canonical workflow for re-running the analyzer after a
  `apd-gauntlet refresh-d3fend` updates the D3FEND counter mappings, or
  after a domain-pack edit changes the declared crown jewels.

Outputs land in `40-synthesis/`:

```
40-synthesis/
├── asset-graph.yaml              # nodes + typed edges with provenance
├── attack-paths.yaml             # enumerated paths + bottleneck edges
├── defense-graph.yaml            # D3FEND overlay on bottleneck edges
├── attack-path.findings.yaml     # one apath-* finding per path or bottleneck
└── attack-path-report.md         # human-readable executive summary + Mermaid
```

The `apath-*` findings carry one of four dispositions: `risk` (high
feasibility, no mitigation), `uncertainty` (low feasibility or partial
mitigation), `gap` (bottleneck edge without D3FEND coverage), or `blocked`
(explicit empty `crown_jewels` against a domain that declares some). See
[docs/attack-path-analysis.md](attack-path-analysis.md) for the full
operator guide, including the discipline rules (no invented nodes or
edges, D3FEND must counter ATT&CK, bounded enumeration with explicit
truncation).

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
| Declared taxonomy catalogs present | `apd-gauntlet refresh-{mitre,mitre-mobile,cwe,owasp,d3fend,atlas,mas}` as the `taxonomies:` list requires | conditional |
| CBM reachable + codebase indexed | codebase-memory-mcp `index_status` / server registered | if `code_recon: enabled`/`auto` |
| Threat-model file exists at declared path | inspect `inputs/` against the `threat_model:` path | if `threat_model:` declared |
| `crown_jewels` + `attacker_positions` declared | inspect `.apd-run.yaml` (or the active pack's `domain.yaml`) | if you want attack-path output |
| Static infra globs resolve under `inputs/` | inspect `infrastructure.static.*` globs against `inputs/` | if `infrastructure.mode: static` |
| Dry-run the gated phase order | `apd-gauntlet plan-run runs/<id>` | recommended last step |

The final check — `plan-run` — doubles as your confidence check and as the entry
point to the supported foreground-drive path described in Step 2: it reads
`.apd-run.yaml`, validates it, and prints the exact ordered phase → step checklist
the runner would execute, honoring the run-config gates.

## Step 2: Run the gauntlet

The run must already be scaffolded (Step 1's `init-run`). In Claude Code, from the
repo root, run the `apd-gauntlet` workflow runner against the run directory:

```
> Run the apd-gauntlet workflow on runs/apd-20260601-claim-event-bus/
```

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

For the supported foreground-drive path, run `apd-gauntlet plan-run <run-dir>`:
it reads the run's `.apd-run.yaml`, validates it, and emits the exact ordered
phase → step checklist the runner would execute (honoring the run-config gates),
with each step tagged `CLI` (run it via Bash) or `AGENT` (dispatch it as a
foreground agent). Work the list top to bottom; pass `--json` for a
machine-readable list of step records.

```sh
apd-gauntlet plan-run runs/apd-20260601-claim-event-bus
```

The runner (`.claude/workflows/apd-gauntlet.js`) is deterministic: it phases the
run end-to-end and branches only on the receipts its dispatched agents return.
It:

1. Builds the `apd-domain` skill from the active pack(s) and validates them.
2. Dispatches `apd-intake` (plus the optional code-recon and threat-model-recon
   agents when their preconditions are met).
3. Dispatches the three tier-1 specialists, then tier-2, then tier-3. Before
   each tier's validate gate, the runner runs `canonicalize` (idempotent
   structural canonicalizer: normalizes envelopes, recomputes deterministic IDs,
   rewrites cross-references) so the gate always sees canonical records.
4. Runs the decomposed synthesis (cluster → adjudicate → apply → rollup),
   dispatches the optional attack-path analyzer when activated, builds the
   advisory report and HTML bundle, then runs the report completeness gate
   (`audit-report`). The gate enforces 8 completeness checks (structural and
   editorial). A structural failure that is unresolved after two remediation
   attempts **blocks the run** — a degraded HTML report cannot ship silently.
   Editorial-only residuals are surfaced non-blocking.
5. Returns the final summary at closeout.

The runner is resumable: re-running it against the same directory replays
completed steps from cache, and each agent re-checks whether its outputs already
exist and validate, so a partially completed run picks up where it left off.

## Step 3: Read the advisory report

The deliverable is `40-synthesis/advisory-report.md`. Ten sections:

1. Executive Summary
2. Confirmed Security Posture
3. Blocked-on-Evidence
4. Findings
5. Contradiction Annex
6. Strengths-Notwithstanding-Gaps
7. NIST 800-53r5 Coverage Matrix
8. ATT&CK Technique Exposure
9. APD Coverage Matrix
10. Severity Disagreement Annex

The YAML files in `40-synthesis/` are the canonical data; the report is composed from them. If you want to programmatically consume the output (dashboard, ticketing integration, etc.), parse the YAML.

## Scope hints

Pass scope hints when you start the runner:

| Hint | Effect |
|---|---|
| `"Emphasize PHI exposure"` | Pass-through framing for the executive summary; no agent changes |
| `"Skip Distributed"` | Omit a specialist; the runner emits a stub file at the expected path so downstream tiers don't break |
| `"Focus on the Kafka design"` | Pass component focus to every specialist |

Domain packs are not a runtime hint: choose them at `init-run` time with the
repeatable `--domain` flag (which records the `domains:` list in `.apd-run.yaml`),
not in the prompt that starts the run.

Skipping multiple specialists degrades the advisory report. The runner warns before proceeding.

## Interpreting findings

Each finding has a `disposition`:

- `gap` — required control or property is absent. Take action.
- `risk` — present but inadequate or with material weakness. Take action.
- `uncertainty` — concern identified but evidence is incomplete. Provide the missing evidence and re-run.
- `blocked` — cannot assess this lens without prerequisite evidence. The finding's `prerequisite_evidence` field names what's needed.

`blocked` is **first-class output**, not failure. The "Blocked-on-Evidence" section of the advisory report is a structured request for more artifacts.

Each finding also carries:

- **Severity** — `critical | high | medium | low | informational`, calibrated against the active domain's severity rubric (see `domains/<active>/severity-rubric.md`).
- **Confidence** — `high | medium | low`. Low-confidence findings often pair with `disposition: uncertainty`.
- **Recommendation posture** — `required | recommended | consider`. `required` is reserved for severity ≥ high.

## Interpreting capabilities

Capabilities have a `maturity` ladder:

- `designed` — intent stated in tech plan or design doc. Floor for tech plan reviews.
- `implemented` — runtime evidence required (config, IaC, code, screenshot).
- `tested` — test artifact required.
- `operationalized` — operational artifact required (runbook, monitoring dashboard, alert).

`maturity ≥ implemented` requires at least one non-tech-plan evidence entry. The validator enforces this rule.

Every capability has a `scope` field stating what is confirmed AND what is not addressed. A capability with broad caveats appears in section 6 of the advisory report (Strengths-Notwithstanding-Gaps).

## Re-running after providing more artifacts

If a run produces `blocked` findings, gather the prerequisite evidence and start a new run. Closing blocked findings requires another run with the additional artifacts — the gauntlet does not retry blocked findings without them.

```bash
apd-gauntlet init-run apd-20260615-claim-event-bus-v2 \
  --inputs ~/my-project/tech-plans/claim-event-bus-v2/ \
  --domain pbm
```

Then run the `apd-gauntlet` workflow against the new directory.

## Troubleshooting

### `apd-gauntlet validate` reports errors

Read the error message carefully — it cites the file, the record id, and the specific violation. Common causes:

- **Schema validation**: missing required fields, wrong enum values, malformed IDs. Fix the agent output; re-validate.
- **Excerpt too long (semantic lint)**: trim the evidence excerpt to ≤ 25 whitespace-separated tokens.
- **ID mismatch (semantic lint)**: the deterministic ID didn't match the recomputed hash. Either the title or the first evidence locator changed; recompute and update.
- **Unknown artifact**: the evidence cites an artifact that isn't in the intake brief's frontmatter. Either fix the citation or update the brief.
- **maturity ≥ implemented without non-tech-plan evidence**: either downgrade to `designed` or add evidence from a non-tech-plan artifact (IaC, code, test report, runbook).

### Synthesizer flagged a contradiction

Read the contradiction annex. A contradiction means a finding asserts a property is absent while a capability asserts it is present. Resolution requires human judgment — the synthesizer never silently picks one. Typical outcomes:

- Capability scope was too broad; narrow it and re-run.
- Finding cited the wrong artifact section; correct the citation.
- Both are partially right; the contradiction notes the disagreement and is annotated `Reviewer determine`.

### Specialist hit two retries and was dropped

The runner allows up to two retries per agent when validation fails. If a specialist still fails after two retries, the runner surfaces the failure and proceeds without that agent's output for the affected record. This is rare; investigate the agent's input (sometimes the tech plan section it's being asked about is genuinely undecidable).

## Local accuracy benchmark (out-of-band)

CI enforces structure (schemas validate, refactors stay byte-stable, the cache
carries provenance) against committed synthetic fixtures only. Holistic accuracy
— how much redundancy collapsed, how many false "unknowns" became cited
assumptions, how many chokepoints surfaced — is measured **locally**, never in
CI, because it requires a real gauntlet run and `runs/` is gitignored by policy.

To record your own baseline:

1. Run the gauntlet against your subject as usual (`init-run` → run the
   `apd-gauntlet` workflow). The run lands under `runs/<run-id>/`, which is
   gitignored.
2. Read the canonical metrics block: `runs/<run-id>/40-synthesis/metrics.yaml`.
   It is produced by `compute_metrics` (`tools/apd_gauntlet/synthesis/metrics.py`)
   and is the single source of truth for the report summary numbers.
3. Record the figures you care about (findings totals, redundancy collapsed,
   chokepoint count, assumption-promotion count) as a baseline `B0` in your own
   private notes **outside this repository**.
4. Judge later runs' deltas against `B0`.

> **Out-of-band rule.** All outputs of all real runs — the run tree, the report,
> and even bare metric counts including `B0` itself — stay fully out-of-band.
> Never commit them. The committed `examples/*/expected/` and `tests/fixtures/`
> are hand-authored synthetic fixtures with no real-subject data; they are the
> sole basis for CI. See [CI gate model](ci-gate-model.md) and
> [ADR-0017](adrs/0017-local-only-accuracy-benchmark.md).

## See also

- [Architecture](architecture.md) — how the gauntlet works under the hood
- [Adapting to other domains](adapting-to-other-domains.md) — authoring a non-PBM domain pack
- [Schema evolution](schema-evolution.md) — versioning policy
