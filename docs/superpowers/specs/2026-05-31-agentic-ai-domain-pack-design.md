# Agentic-AI Domain Pack — Design

**Date** 2026-05-31 · **Status** Approved, pending user review · **Branch** `design/agentic-ai-pack`

## Summary

This spec designs a new APD domain pack, **`agentic-ai`**, that calibrates the gauntlet
for reviewing autonomous LLM-agent systems, plus a **full golden run** of the gauntlet
against the real `hexo-ai/sia` codebase as a committed fixture.

It is **sub-project 1** of a two-part effort. Sub-project 2 (a separate spec) is the
domain-pack authoring documentation overhaul, which will use this pack — and the gaps
surfaced while authoring it — as its worked example. Pack-first is deliberate: authoring
a real pack against today's docs is the best dogfood for the overhaul.

The pack is the gauntlet's first **AI-security** domain. It must be broadly useful for
autonomous agents in general (tool-use agents, multi-agent systems, autonomous task
loops, code-generation-and-execution) while treating **self-improving / self-modifying
systems (SIA-class) as a first-class sub-surface** so the `hexo-ai/sia` golden run is
fully served.

## Locked decisions

These were settled during brainstorming and drive the rest of the design.

- **Scope** — broad `agentic-ai`, with self-improving systems first-class (not a narrow
  self-improving-only pack, and not a layered base+add-on pair).
- **Content approach** — standards-anchored, SIA-instantiated: build the skeleton from
  established agentic-AI threat standards, instantiate every pattern with SIA as the
  concrete specimen.
- **Deliverable** — the pack **and** a full golden gauntlet run against `hexo-ai/sia`,
  committed under `runs/` like the existing crapi/authentik/caldera fixtures.
- **Excessive Agency** — handled as a **cross-goal theme** (see Resolutions), because
  APD's nine goals are fixed and a pack cannot add a tenth.

## Scope

**In scope.**

- The 14 pack files under `domains/agentic-ai/` (anatomy below).
- `validate-domain` + `build-domain-skill` passing on the pack.
- A committed golden run against `hexo-ai/sia`.

**Out of scope (future efforts, recorded here).**

- **ATLAS as a first-class framework taxonomy** — adding a `mitre_atlas` taxonomy enum
  value, ATLAS reference data, an `atlas-coverage` rollup, and `control_mappings`
  extension. This is a framework change (touches `validate.py`, the synthesizer,
  schemas, reference data, the report), not a pack change.
- **MAESTRO as a recognized threat-model methodology** — adding a `methodology_hint`
  enum value plus a MAESTRO-layer-to-APD-goal mapping in the
  `apd-threat-model-methodologies` skill, consumed by `apd-threat-model-recon` and
  `apd-threat-model-evaluator`.
- A multi-domain composition demo (this pack composing with another via Subsystem A).
- The domain-pack authoring docs overhaul (sub-project 2).

## Pack anatomy

`domains/agentic-ai/` mirrors the shipped packs and is compiled into the `apd-domain`
skill by `build-domain-skill`. Fourteen files:

- `domain.yaml` — crown jewels, attacker positions, default trust boundaries, regulatory
  anchors, includes.
- `severity-rubric.md` — impact-to-severity calibration.
- `consequential-actions.md` — the high-stakes action surface.
- `immutability-classes.md` — tamper-evident / retained record classes.
- `data-taxonomy.md` — data sensitivity tiers and handling.
- `common-patterns/<goal>.md` — one hint catalog per APD goal, nine files:
  `confidentiality.md`, `integrity.md`, `availability.md`, `distributed.md`,
  `resilient.md`, `ephemeral.md`, `authenticity.md`, `non-repudiation.md`,
  `immutability.md`.

## Taxonomy and standards backbone

**Structured taxonomies** (what findings emit and what the synthesizer rolls up) are
limited to the framework-supported set:

- `owasp_llm_top10` — primary. The pack exercises the full **LLM01–LLM10**.
- `mitre_attack` — enterprise technique T-codes, high-confidence only.
- `cwe` — base/variant weaknesses (no pillars, no categories).

**Prose grounding only** (never placed in `taxonomy_mappings`):

- **MITRE ATLAS** — cite the relevant technique by name/ID (for example,
  "LLM Prompt Injection / AML.T0051") in pattern prose. The framework has no structured
  ATLAS support, so where an ATLAS technique has a clean enterprise-ATT&CK analog (for
  example generated-code execution → T1059), the finding maps to the ATT&CK T-code.
- **CSA MAESTRO** — cite the relevant layer(s) per pattern. MAESTRO's seven layers double
  as a coverage checklist (below).

**Control mappings** use NIST SP 800-53r5 control families/controls plus ATT&CK, per the
`apd-control-mappings` skill.

### MAESTRO seven-layer coverage checklist

Each layer must be reflected somewhere in the pack:

- L1 Foundation Models — data-taxonomy (weights/extraction), severity (model stealing).
- L2 Data Operations — data-taxonomy (eval/RAG/training, poisoning), immutability (eval
  results).
- L3 Agent Frameworks — consequential-actions (tools/delegation), immutability (tool
  manifests/SBOM).
- L4 Deployment and Infrastructure — consequential-actions (code-exec sandbox), severity
  (escape blast radius).
- L5 Evaluation and Observability — immutability (traces, scores), consequential-actions
  (eval access).
- L6 Security and Compliance — severity modifiers, regulatory anchors.
- L7 Agent Ecosystem — consequential-actions (multi-agent delegation), data-taxonomy
  (inter-agent messages), severity (collusion/impersonation).

### Mapping discipline

- `taxonomy_mappings` contain only `owasp_llm_top10` / `mitre_attack` / `cwe`. ATLAS and
  MAESTRO are prose, never mappings.
- CWE entries are base/variant only — no pillars (for example never CWE-693) and no
  categories (for example never CWE-840, CWE-1357).
- ATT&CK techniques are assigned only when clearly applicable; no shotgun mapping. For
  defender-evidence gaps (provenance, audit completeness) emit an empty ATT&CK list with
  a NIST control instead of a forced technique.
- NIST entries narrow to 3–5 specific controls/enhancements when authored into findings.

## domain.yaml

- **crown_jewels** — the agent's tool/code-execution capability; secrets and
  model-provider API keys; training/eval data and held-out ground truth; the agent's
  persistent memory/context store; the self-improvement loop and generated agent code;
  the orchestration control plane.
- **attacker_positions** — untrusted input / tool-output (prompt-injection source);
  malicious task/goal author; malicious or compromised tool/plugin; compromised model
  provider; co-tenant / sandbox-escape neighbor.
- **default_trust_boundaries** — untrusted content → agent reasoning; agent → tool/
  code-exec sandbox; agent → model provider; agent → secrets store; generation N →
  generation N+1 (self-improvement).
- **regulatory_anchors** — EU AI Act; NIST AI RMF (AI 100-1); ISO/IEC 42001. (ATLAS and
  OWASP LLM Top 10 are deliberately not anchors — ATLAS is a threat knowledge base and
  OWASP LLM Top 10 is the taxonomy.)
- **includes** — glob the five top-level files and `common-patterns/*.md` per the pack
  convention.

## severity-rubric.md

Calibrates impact-to-severity using four agentic-specific modifiers: **autonomy** (acted
without human confirmation), **reversibility**, **blast radius** (single session versus
cross-tenant / cross-generation persistence), and **data sensitivity**.

- **Critical** — autonomous, irreversible, unbounded blast radius: attacker-controlled
  code/tool execution on production; exfiltration of provider API keys or held-out
  eval/ground-truth; a self-improvement loop propagating a backdoor across generations;
  takeover of the goal/control plane.
- **High** — serious but bounded: injection driving a high-privilege tool misuse in one
  session; disclosure of one principal's context/memory; memory/RAG poisoning affecting
  future decisions; unbounded consumption → cost/DoS.
- **Medium** — constrained/recoverable: quality-degrading injection; tool misuse caught
  by a guardrail/HITL; observability gaps delaying detection.
- **Low** — hardening: missing rate limit on a low-risk tool; verbose non-sensitive
  traces.

## consequential-actions.md

The high-stakes action surface that drives Non-Repudiation, Integrity, and Authenticity:

- Side-effecting tool invocation (code/shell/file write/API-mutate/financial/comms).
- Self-modification (generating or rewriting agent code; prompt/policy updates;
  committing a new generation).
- Secret/credential use.
- Memory writes (long-term memory / RAG store).
- Sub-agent spawn/delegation.
- Held-out eval-data access.
- Runtime privilege / tool / scope escalation.
- Model/provider switch.
- Merging agent output into a system of record.

## immutability-classes.md

Tamper-evident / retained classes, each with a retention basis and a tamper-evidence
mechanism:

- Agent execution and decision traces (tool calls, I/O per step).
- Generation provenance/lineage (append-only, Merkle/git-style — SIA's `runs/<id>/gen_n`).
- Prompt/policy/tool-manifest version history (config-as-code, signed).
- Eval results/scores (anti-gaming immutable record).
- Model/tool/SBOM provenance.
- Human/HITL approval records.

## data-taxonomy.md

Sensitivity tiers and handling, each tagged with the APD goals that care:

- Secrets/credentials — provider keys, tool creds, signing keys.
- Held-out eval data / ground truth.
- Generated agent code/artifacts — integrity-critical, backdoor vector.
- Agent memory/context/history — PII plus poisoning target.
- Untrusted tool I/O and external content — injection carrier; provenance class.
- Training/fine-tune data — poisoning surface.
- Decision/telemetry logs — audit-relevant.
- Model weights/config — IP plus extraction target.

## The nine common-patterns

Each file is a hint catalog of headline patterns — typically four to six, with
Confidentiality and Integrity carrying a seventh from Resolutions R2/R3. Patterns were
designed across all nine goals grounded in OWASP LLM Top 10 + ATLAS + MAESTRO + SIA, then
passed through a coherence/lens critic. The headline patterns and their primary OWASP-LLM grounding
follow; full prose, the exact per-pattern ATT&CK/CWE/NIST mappings, and the SIA
instantiation are authored during implementation under the mapping discipline above and
the cleanup checklist below.

### Confidentiality

- Provider API keys / secrets exposed to the agent's execution surface — LLM02/LLM06.
- Held-out evaluation ground-truth leakage into the optimization loop — LLM02/LLM06.
- Sensitive data in prompts, traces, run artifacts, and execution logs — LLM02/LLM05.
- System-prompt and meta-prompt leakage — LLM07/LLM02.
- Cross-session / cross-tenant agent memory and context bleed — LLM02/LLM08.
- Inter-agent channel encryption-in-transit (new, per Resolution R3) — LLM02.
- Model-weight / fine-tune-artifact extraction and exfiltration — LLM02.

### Integrity

- Prompt-injection input defense — untrusted-context isolation/quarantine/spotlighting at
  the trust boundary, including indirect injection from tool/RAG/web (new, per Resolution
  R2) — LLM01.
- Injected-instruction write/tool-action laundering — LLM01/LLM06/LLM05.
- Unverified self-modification merge (generated-code integrity) — LLM04/LLM05/LLM03.
- Reward/eval-target tampering and specification-gaming detection (per Resolution R3) —
  LLM04/LLM06.
- Agent memory / RAG write-path poisoning — LLM08/LLM04/LLM01.
- Tool-output trust without validation — LLM05/LLM06.
- Write-path authorization for self-modification and system-of-record merges — LLM06/LLM01.

### Availability

- Unbounded autonomous-loop consumption (no generation, token, wall-clock, or cost
  budget) — LLM10/LLM06.
- Model-provider dependency reliability — LLM10/LLM03.
- No SLO/SLI for autonomous task completion — LLM06.
- Capacity headroom for concurrent agents and execution sandboxes — LLM10/LLM06.
- Failure-domain and blast-radius analysis for the shared agent substrate — LLM10/LLM03.
- Shallow health checks and no liveness/progress detection for stuck loops — LLM10.

### Distributed

- Orchestrator / control-plane as single point of failure — LLM06/LLM10.
- Model-provider / inference endpoint as single point of failure — LLM03/LLM10.
- Stateful agent memory versus stateless workers boundary — LLM06.
- Multi-agent topology, message routing, and CAP positioning under partition — LLM06.
- Shared vector store / agent memory locality, replication, consistency — LLM08.
- Sub-agent fan-out and inference load distribution — LLM10/LLM06.

### Resilient

- No circuit breaker on the autonomous self-improvement / task loop — LLM06/LLM10.
- Retry/backoff discipline on model and tool calls — LLM10/LLM05.
- Bulkheads / resource isolation around code-exec sandboxes and per-agent quotas —
  LLM10/LLM06.
- Timeout discipline on autonomous steps, tool calls, and reasoning chains — LLM10/LLM06.
- Graceful degradation when a model, tool, or guardrail is down (fail-safe, not
  fail-open-and-keep-acting) — LLM06/LLM05.
- Backpressure on generation / sub-agent fan-out and the inter-agent message bus — LLM10.

### Ephemeral

- Standing broad agency versus JIT scoped tool credentials — LLM06/LLM01.
- Long-lived provider API keys with no rotation cadence or automation — LLM02.
- No ephemeral sandbox per code-execution — LLM06/LLM05.
- Sub-agent / spawned-agent credentials lack independent expiry and revocation —
  LLM06/LLM01.
- Compromised-generation credential revocation and blast-radius containment — LLM04/LLM06.
- Unbounded agent session / memory TTL — LLM10/LLM06.

### Authenticity

- Self-produced agent code emitted unsigned / no per-generation provenance —
  LLM06/LLM05/LLM03.
- Agent / sub-agent workload identity absent — LLM06.
- Inter-agent messages unsigned (impersonation, Sybil, goal-manipulation cascade) —
  LLM01/LLM06.
- Tool / plugin / MCP-server authenticity not verified before binding — LLM03/LLM06.
- Model and dependency provenance unattested (no SBOM / SLSA) — LLM03/LLM04.
- Human operator of the autonomous loop authenticated below the required AAL — LLM06.

### Non-Repudiation

- Consequential-action audit completeness versus the agentic action surface — LLM06/LLM05.
- Per-entry actor attribution across agent / sub-agent / human / generation — LLM06.
- Signed, hash-chained decision/action traces — LLM05/LLM06.
- Reliable, ordered time source across the loop and across generations — LLM06.
- Audit-read/alter access control with segregation of duties from the agents —
  LLM06/LLM02.
- Audit shipping reliability to a durable off-host sink — LLM10.

### Immutability

- Append-only generation lineage / provenance chain — LLM04/LLM03/LLM06.
- WORM execution / decision traces (tool-call and action ledger) — LLM06/LLM05.
- Immutable eval results / scores (anti-gaming of the optimization metric) —
  LLM04/LLM09/LLM06.
- Guardrail config-as-code version history and drift detection — LLM06/LLM01/LLM07.
- Backup immutability for held-out ground truth and golden agent state — LLM04/LLM10.
- Snapshot integrity of agent / shared memory state — LLM04/LLM08.

## Resolutions (cross-cutting structural decisions)

These resolve the three structural findings from the coherence critic and are binding on
the pattern authoring.

### R1 — Excessive Agency is a cross-goal theme

APD's nine goals are fixed; a pack cannot add a tenth, so LLM06 Excessive Agency is not a
single goal. It decomposes, with each goal explicitly owning its facet:

- read-scope (what the agent may read) → **Confidentiality**.
- side-effecting tool/write authorization (what the agent may do) → **Integrity**.
- JIT/scoped permission lifetime (how long an agent holds agency) → **Ephemeral**.
- blast-radius isolation (containing over-reach) → **Resilient**.

A short note in the pack (severity-rubric overview or a leading section of the relevant
common-patterns files) frames Excessive Agency as cross-cutting. No pattern routes to a
phantom "Confinement" goal.

### R2 — Integrity owns prompt-injection input defense

Untrusted-context isolation, quarantine/spotlighting/delimiting, and indirect injection
from tool/RAG/web content are owned by Integrity as an explicit pattern, distinct from
write-path authorization. (Previously every goal cited LLM01 only as a steering vector and
routed the actual handling away, orphaning it.)

### R3 — Multi-agent and self-improvement seams

- Inter-agent channel **encryption-in-transit** is an explicit Confidentiality pattern.
- Reward-hacking / specification-gaming **detection** is owned by Integrity (eval-validity
  signal); Resilient consumes the signal to trip its circuit breaker.
- Authenticated **collusion** / emergent multi-agent behavior is covered at the security
  facets (coordinated-action attribution → Non-Repudiation; joint-write impact →
  Integrity), and the pack honestly flags emergent-behavior detection as partly beyond a
  security-architecture lens.

### Mapping cleanup checklist (apply at authoring time)

- Drop pillar CWE-693 (Resilient, Immutability) and category CWE-840 / CWE-1357.
- Fix wrong CWEs: CWE-1059 (Availability, Immutability), CWE-1119 (Availability),
  CWE-322 (Ephemeral).
- Stop the boilerplate T1530 + T1213 pair on local-disk reads (SIA's `data/private/` and
  `runs/` are local disk, not cloud storage).
- Emit an empty ATT&CK list (not a forced T1059) on provenance and audit-completeness
  gaps; carry the NIST control instead.
- Replace T1565.002 with T1565.001 for local eval-store tampering; drop stretched T1610
  (Ephemeral), T1136 (Ephemeral), T1222 (Immutability).

## SIA golden run

An analytical execution of the gauntlet, like the existing crapi/authentik/caldera golden
runs — produced once, quality-reviewed, and committed (not a unit-testable artifact).

- **Target/input** — clone `hexo-ai/sia` as the run's input codebase (OSS code target).
- **Run config** — id `apd-<date>-sia-self-improving-agent`; `domains: [agentic-ai]`;
  `taxonomies: [owasp_llm_top10, mitre_attack, cwe]`. Crown jewels and attacker positions
  come from the pack's `domain.yaml`, so attack-path analysis activates against a real
  target.
- **Threat model** — none for v1 (MAESTRO methodology support is a future effort), so
  `tmeval` stays inactive.
- **Execution** — the `apd-gauntlet` workflow runner: intake → optional code-recon → nine
  specialists → attack-path → synthesis → HTML report → audit.
- **Acceptance** — `validate` structurally clean (schema, ids, cross-file); the HTML
  report builds; findings are quality-reviewed (grounded, in-lens, evidence-cited);
  committed under `runs/`.
- **Dogfood capture** — log every authoring friction point against today's
  `adapting-to-other-domains.md` as input for sub-project 2.

## Acceptance bar

1. All 14 pack files exist under `domains/agentic-ai/`.
2. `apd-gauntlet validate-domain agentic-ai` is clean and `build-domain-skill agentic-ai`
   compiles the `apd-domain` skill clean.
3. Mapping discipline holds: structured mappings only `owasp_llm_top10` / `mitre_attack` /
   `cwe`; ATLAS and MAESTRO prose-only; CWE base/variant; ATT&CK high-confidence; the
   cleanup checklist applied.
4. The three resolutions are reflected in the patterns.
5. The golden run validates structurally, its report builds, its findings are
   quality-reviewed, and it is committed.
6. CI is green: full `pytest`, `mypy tools/`, `ruff check tools/ tests/`, `lint-agents`,
   `markdownlint` (the full `docs/**` glob), and `validate-example`.

## References

- Brainstorming decisions captured in this session (scope, content approach, deliverable,
  Excessive Agency handling).
- The agentic-AI pattern design and coherence critique produced by the
  `agentic-ai-pack-patterns-design` workflow.
- Existing shipped packs under `domains/` (pbm, api-security, identity-security,
  security-tooling) as structural exemplars.
- `docs/adapting-to-other-domains.md` (the pack to be authored against it; its gaps feed
  sub-project 2).
- OWASP LLM Top 10 (2025); MITRE ATLAS; CSA MAESTRO; NIST AI RMF; EU AI Act; ISO/IEC 42001.
