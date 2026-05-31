---
name: apd-orchestrator
description: Deprecated — superseded by the apd-gauntlet workflow runner (.claude/workflows/apd-gauntlet.js, invoked via the Workflow tool). This agent no longer orchestrates runs; retained as a historical-topology reference.
tools: Read, Glob, Grep, Write, Agent
---

# APD Gauntlet Orchestrator (DEPRECATED)

**DEPRECATED.** The APD gauntlet is now run by the deterministic workflow
runner `.claude/workflows/apd-gauntlet.js` (invoke it via the Workflow tool).
This agent no longer orchestrates runs — the runner dispatches intake, the tier
specialists, the decomposed synthesis pipeline, and the gated report audit
directly, with native auto-resume. See
`docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` §4 for the
architecture and §7 for the decomposed Phase 5.

`apd-cluster-adjudicator`, `apd-report-writer`, and `apd-report-auditor` are
workflow-runner agents (Plan 3) dispatched by the runner, not by this agent.

## Historical topology (for reference)

Before the workflow runner, this orchestrator coordinated 16 agents. The
mapping below is retained so historical run notes remain legible; it is NOT a
live contract.

### Tier-0 (intake / context)

- `apd-intake` (required); `apd-code-recon` (optional); `apd-threat-model-recon`
  (optional). When `crown_jewels` are declared, intake also emits
  `00-context/asset-inventory.yaml`.

### Tier-1 (Trustworthiness)

- `apd-confidentiality`, `apd-integrity`, `apd-availability`

### Tier-2 (Scalability)

- `apd-distributed`, `apd-resilient`, `apd-ephemeral`

### Tier-3 (Auditability)

- `apd-authenticity`, `apd-non-repudiation`, `apd-immutability`

### Tier-4 (synthesis)

- `apd-synthesizer` (now the workflow's fallback path);
  `apd-threat-model-evaluator` (Phase 5.5, threat-model gate);
  `apd-attack-path-analyzer` (Phase 5.6, `crown_jewels` activation gate; emits
  `asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`,
  `attack-path.findings.yaml`).

The runner realizes the same phase ordering deterministically; consult the
design spec rather than this block for current behavior.
