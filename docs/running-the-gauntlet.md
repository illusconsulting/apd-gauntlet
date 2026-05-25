# Running the Gauntlet

Operator guide. How to set up a run, invoke the orchestrator, and interpret the outputs.

## Prerequisites

- Claude Code with agent and skill support.
- Python ≥ 3.10 (for the `apd-gauntlet` validator CLI).
- A tech plan or design document for the change you want to review.
- Optional but recommended: PRD, source code, IaC, architecture diagrams, threat models, ADRs, runbooks, test reports.

## Install

```bash
pip install apd-gauntlet
apd-gauntlet --version
```

The CLI exposes eight subcommands:

```
apd-gauntlet validate <run-dir>           # three-pass validation
apd-gauntlet init-run <run-id> ...        # scaffold a run directory
apd-gauntlet build-domain-skill <pack>    # generate the apd-domain skill
apd-gauntlet summarize <run-dir>          # finding/capability statistics
apd-gauntlet lint-agents                  # validate agent file frontmatter
apd-gauntlet check-ids <yaml-file>        # verify deterministic IDs
apd-gauntlet validate-domain <pack>       # validate a domain pack
apd-gauntlet refresh-mitre                # refresh the cached MITRE crosswalk
```

## Step 1: Scaffold the run

Pick a run id. Convention: `apd-YYYYMMDD-<short-slug>` (e.g. `apd-20260601-claim-event-bus`).

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ~/my-project/tech-plans/claim-event-bus/ \
  --domain pbm
```

This creates `runs/apd-20260601-claim-event-bus/` with subdirectories for each phase output, copies your artifacts into `inputs/`, and records the active domain.

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

## Step 2: Invoke the orchestrator in Claude Code

In Claude Code, invoke the `apd-orchestrator` agent against the run directory:

```
> Run apd-orchestrator on runs/apd-20260601-claim-event-bus/
```

The orchestrator phases the run end-to-end. It:

1. Builds the `apd-domain` skill from the active pack.
2. Validates the domain pack.
3. Dispatches `apd-intake`.
4. Dispatches the three tier-1 specialists in parallel and validates their output.
5. Dispatches the three tier-2 specialists and validates.
6. Dispatches the three tier-3 specialists and validates.
7. Dispatches `apd-synthesizer`.
8. Reports the final summary.

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

Pass scope hints when invoking the orchestrator:

| Hint | Effect |
|---|---|
| `"Emphasize PHI exposure"` | Pass-through framing for the executive summary; no agent changes |
| `"Skip Distributed"` | Omit a specialist; orchestrator emits a stub file at the expected path so downstream tiers don't break |
| `"Focus on the Kafka design"` | Pass component focus to every specialist |
| `"domain=saas"` | Use a non-default domain pack |

Skipping multiple specialists degrades the advisory report. The orchestrator warns before proceeding.

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

Then invoke `apd-orchestrator` against the new directory.

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

The orchestrator allows up to two retries per agent when validation fails. If a specialist still fails after two retries, the orchestrator surfaces the failure and proceeds without that agent's output for the affected record. This is rare; investigate the agent's input (sometimes the tech plan section it's being asked about is genuinely undecidable).

## See also

- [Architecture](architecture.md) — how the gauntlet works under the hood
- [Adapting to other domains](adapting-to-other-domains.md) — authoring a non-PBM domain pack
- [Schema evolution](schema-evolution.md) — versioning policy
