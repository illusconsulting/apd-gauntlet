# Agentic-AI Domain Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a new `agentic-ai` APD domain pack (14 files) that calibrates the gauntlet for autonomous LLM-agent systems, then execute and commit a full golden gauntlet run against `hexo-ai/sia`.

**Architecture:** A domain pack is content — one `domain.yaml` (schema-validated metadata + crown jewels / attacker positions / trust boundaries / regulatory anchors / an `includes` list) plus markdown hint files. The compiled `.claude/skills/apd-domain/SKILL.md` is a build artifact the gauntlet workflow regenerates per run; it is NOT committed as part of pack authoring. There is no application code; the per-task "test" is the deterministic gate `apd-gauntlet validate-domain` plus `markdownlint-cli2`. We author incrementally: each task appends one path to `includes` and authors that file, so `validate-domain` genuinely fails before the file exists and passes after. The golden run is an analytical execution of the `apd-gauntlet` Workflow, quality-reviewed and committed like the existing crapi/authentik/caldera fixtures.

**Tech Stack:** YAML + Markdown content; `apd-gauntlet` CLI (`validate-domain`, `build-domain-skill`, `init-run`, `validate`); `markdownlint-cli2`; the `apd-gauntlet` Workflow runner (`.claude/workflows/apd-gauntlet.js`) for the golden run.

---

## Sources of truth

- **Spec:** `docs/superpowers/specs/2026-05-31-agentic-ai-domain-pack-design.md` — the approved design (scope, taxonomy backbone, the four agentic severity modifiers, the nine common-patterns, the three Resolutions, the mapping cleanup checklist, the golden-run methodology, the acceptance bar).
- **Pattern drafts (build input):** `docs/superpowers/plans/2026-05-31-agentic-ai-pack-pattern-drafts.md` — the 52 grounded pattern drafts (threat, ATLAS/MAESTRO prose grounding, SIA instantiation, candidate `taxonomy_mappings`, NIST families) for the nine common-patterns. The `taxonomy_mappings` there are the SPECIALIST's mapping guidance for the golden run, surfaced in the pattern `Detail:` prose — not literal CWE/ATT&CK bullets in the markdown. Apply the spec's mapping cleanup checklist to the golden-run findings.
- **Structural exemplar:** `domains/api-security/` — the newest shipped pack. Match its file conventions exactly; `domains/api-security/common-patterns/non-repudiation.md` is the canonical pattern-file format.

## Conventions every task follows

- **Pack dir:** `domains/agentic-ai/`.
- **`domain.yaml` schema** (`schemas/domain.schema.json`): required `name` (`^[a-z][a-z0-9-]*$`), `display_name` (≥3), `version` (semver string), `framework_compat` (range string), `description` (≥20), `includes` (≥1 path; no leading `/`, no `..`), `regulatory_anchors` (string list). Optional `crown_jewels` / `attacker_positions` / `default_trust_boundaries` — each an item list of `{pattern|position|boundary: <key ≥1>, description: <≥10>}`.
- **Per-task gate** (run from repo root): `apd-gauntlet validate-domain agentic-ai` plus `npx --yes markdownlint-cli2 "domains/agentic-ai/**/*.md"`.
  - `validate-domain` success line: `Domain pack 'agentic-ai' OK: schema valid, <N> include patterns all resolved.`
  - `validate-domain` failure when an include path matches no file: `Missing include in 'agentic-ai': <path>` (exit 1).
  - `validate-domain` failure when the pack does not exist yet: `Error: domain pack 'agentic-ai' not found at domains/agentic-ai` (exit 1).
  - `markdownlint-cli2` success: `Summary: 0 error(s)`.
  - If the installed entrypoint is unavailable, the equivalent is `python3 -m apd_gauntlet.cli validate-domain agentic-ai` (the package is installed editable from `tools/`; `cli.py` has a `__main__` guard).
- **`build-domain-skill` is NOT a per-task gate.** It is run once in Task 14 to confirm the full pack compiles, after which the tracked `.claude/skills/apd-domain/SKILL.md` is restored with `git checkout` — pack authoring never commits that build artifact. (Building it commits an overwrite of whatever domain the live skill currently represents; we avoid that.)
- **Markdown discipline** (`.markdownlint.json`): dash bullets, blank lines around lists/headings/fences, no trailing-colon headings, single H1 per file. `MD036:false` permits the bold-paragraph `**Pattern: …**` style; `MD024:siblings_only` permits the repeated `## Common finding patterns` heading across files.
- **Mapping discipline** (per spec + `apd-control-mappings` skill) applies to what specialists EMIT in the golden run, not to the pattern markdown: `taxonomy_mappings` use only `owasp_llm_top10` / `mitre_attack` (enterprise T-codes, high-confidence) / `cwe` (base/variant — no pillars, no categories); ATLAS + MAESTRO are prose only; on provenance/audit-completeness gaps emit an empty ATT&CK list with a NIST control, not a forced `T1059`.
- **The three Resolutions are binding:** R1 Excessive Agency is a cross-goal theme (read→Confidentiality, tool/write authz→Integrity, permission lifetime→Ephemeral, blast-radius→Resilient) with a short cross-cutting note in the severity rubric; R2 Integrity owns prompt-injection input defense; R3 Confidentiality owns inter-agent encryption-in-transit and Integrity owns gaming-detection.

## File structure

| File | Responsibility | Task |
|------|----------------|------|
| `domains/agentic-ai/domain.yaml` | Metadata + crown jewels / attacker positions / trust boundaries / anchors / includes | 1 |
| `domains/agentic-ai/severity-rubric.md` | Impact-to-severity calibration (4 agentic modifiers) + the R1 cross-goal note | 1 |
| `domains/agentic-ai/consequential-actions.md` | High-stakes action surface | 2 |
| `domains/agentic-ai/immutability-classes.md` | Tamper-evident / retained record classes | 3 |
| `domains/agentic-ai/data-taxonomy.md` | Data sensitivity tiers + handling | 4 |
| `domains/agentic-ai/common-patterns/confidentiality.md` | Confidentiality patterns (+ inter-agent encryption, R3) | 5 |
| `domains/agentic-ai/common-patterns/integrity.md` | Integrity patterns (+ injection-input defense R2, gaming-detection R3) | 6 |
| `domains/agentic-ai/common-patterns/availability.md` | Availability patterns | 7 |
| `domains/agentic-ai/common-patterns/distributed.md` | Distributed patterns | 8 |
| `domains/agentic-ai/common-patterns/resilient.md` | Resilient patterns | 9 |
| `domains/agentic-ai/common-patterns/ephemeral.md` | Ephemeral patterns | 10 |
| `domains/agentic-ai/common-patterns/authenticity.md` | Authenticity patterns | 11 |
| `domains/agentic-ai/common-patterns/non-repudiation.md` | Non-Repudiation patterns | 12 |
| `domains/agentic-ai/common-patterns/immutability.md` | Immutability patterns | 13 |
| `tests/test_agentic_ai_pack.py` | Pytest: pack validates + structural/grounding guards | 14 |
| `runs/apd-<date>-sia-self-improving-agent/` | Golden run fixture | 15 |

---

### Task 1: domain.yaml + severity-rubric.md (validating skeleton)

**Files:**

- Create: `domains/agentic-ai/domain.yaml`
- Create: `domains/agentic-ai/severity-rubric.md`

- [ ] **Step 1: Write the failing test**

Run: `apd-gauntlet validate-domain agentic-ai`
Expected: FAIL — `Error: domain pack 'agentic-ai' not found at domains/agentic-ai` (exit 1).

- [ ] **Step 2: Create `domain.yaml`** (note `includes` starts with only `severity-rubric.md`; later tasks append):

```yaml
name: agentic-ai
display_name: "Agentic AI (Autonomous LLM Agents)"
version: 1.0.0
framework_compat: ">=1.0.0,<2.0.0"
description: "Security-architecture calibration for autonomous LLM-agent systems — tool-use agents, multi-agent topologies, autonomous task loops, and code-generation-and-execution — with self-improving / self-modifying systems treated as a first-class sub-surface. Anchored to the EU AI Act, NIST AI RMF (AI 100-1), ISO/IEC 42001, NIST SP 800-53r5, and grounded in the OWASP LLM Top 10 (2025), MITRE ATLAS, and CSA MAESTRO."
includes:
  - severity-rubric.md
regulatory_anchors:
  - "EU AI Act"
  - "NIST AI RMF (AI 100-1)"
  - "ISO/IEC 42001"
  - "NIST SP 800-53r5"
crown_jewels:
  - pattern: tool_execution_capability
    description: "The agent's authority to invoke side-effecting tools and execute generated code (shell, file, network, API-mutate). Compromise turns the agent into a remote-code-execution proxy wielding the agent's full privilege."
  - pattern: model_provider_credentials
    description: "Model-provider API keys and tool/service credentials the agent uses to authorize its own calls. Exposure yields billing fraud and lateral access to every provider and tool the keys unlock."
  - pattern: training_and_eval_data
    description: "Training/fine-tune data and the held-out evaluation ground truth that defines the optimization signal. Leakage collapses eval validity; tampering corrupts what the agent learns and rewards."
  - pattern: agent_memory_store
    description: "The agent's persistent memory, conversation context, and vector/embedding store. Holds user PII and prior tool outputs; a poisoning and read-bleed target across sessions and tenants."
  - pattern: self_improvement_loop
    description: "The generate-execute-score-promote loop and the agent code it produces across generations. A single compromised generation can persist and amplify a backdoor across the lineage."
  - pattern: orchestration_control_plane
    description: "The orchestrator that schedules agents, routes inter-agent messages, and holds system prompts, tool manifests, and guardrail config. Takeover lets an attacker act as the system at scale."
attacker_positions:
  - position: untrusted_content_source
    description: "Any untrusted input the agent ingests and may act on — user messages, tool/function outputs, retrieved documents, web content. The carrier for direct and indirect prompt injection; the default agentic attacker position."
  - position: malicious_task_author
    description: "An actor supplying the agent's task, goal, or benchmark definition. In a self-improving system this controls the optimization target and can steer generations toward unsafe behavior or reward hacking."
  - position: malicious_tool_or_plugin
    description: "A compromised or hostile tool, plugin, or MCP server the agent binds to. Returns adversarial outputs, harvests inputs/credentials, or abuses the trust the agent places in tool results."
  - position: compromised_model_provider
    description: "A compromised or malicious model/inference provider returning manipulated completions, exfiltrating prompts, or degrading output quality. Models supply-chain trust in the model layer."
  - position: cotenant_or_sandbox_neighbor
    description: "A co-tenant or neighboring workload sharing the agent's execution substrate, memory store, or sandbox. Models cross-tenant bleed and sandbox-escape lateral movement."
  - position: malicious_peer_agent
    description: "A peer or sub-agent in a multi-agent system attempting impersonation, Sybil identity, goal-manipulation cascade, or collusion against the joint objective."
default_trust_boundaries:
  - boundary: untrusted_content_to_agent_reasoning
    description: "Crossing from untrusted content (user input, tool output, retrieved docs, web) into the agent's reasoning/instruction context. Where injection isolation, spotlighting, and provenance tagging keep data from being treated as instructions."
  - boundary: agent_to_execution_sandbox
    description: "Crossing from the agent to the tool/code-execution sandbox. Where capability scoping, syscall/network egress limits, and per-exec ephemerality contain what generated code may do."
  - boundary: agent_to_model_provider
    description: "Crossing from the agent to the model/inference provider. Where egress identity, prompt minimization, and response validation enforce confidentiality and integrity of the model channel."
  - boundary: agent_to_secret_store
    description: "Crossing from the agent to the secrets/credential store. Where JIT scoping, short-lived credentials, and least-privilege gate which secrets the agent can reach."
  - boundary: generation_n_to_n_plus_1
    description: "Crossing from one self-improvement generation to the next. Where provenance signing, promotion gates, and append-only lineage stop a compromised generation propagating silently."
  - boundary: agent_to_agent_channel
    description: "Crossing between agents/sub-agents in a multi-agent topology. Where message signing, identity verification, and channel encryption prevent impersonation, tampering, and eavesdropping."
```

- [ ] **Step 3: Create `severity-rubric.md`** (api-security format: `# <title>` then `## Critical` / `## High` / `## Medium` / `## Low`; includes the R1 cross-cutting note):

```markdown
# Agentic AI Severity Rubric (impact-to-agent-system)

Severity calibrates impact using four agentic modifiers: **autonomy** (acted without human
confirmation), **reversibility**, **blast radius** (single session vs cross-tenant or
cross-generation persistence), and **data sensitivity**. Raise severity when an outcome is
autonomous, irreversible, persists across sessions or generations, or crosses a tenant or
provider boundary.

> **Excessive Agency is cross-cutting.** OWASP LLM06 (Excessive Agency) is not a single
> goal here. It decomposes across goals: read-scope under Confidentiality, side-effecting
> tool/write authorization under Integrity, just-in-time permission lifetime under
> Ephemeral, and blast-radius isolation under Resilient. Each goal's patterns own their
> facet; there is no separate "confinement" goal.

## Critical

- Attacker-controlled code or tool execution against production from a prompt-injected or
  poisoned agent (autonomous, irreversible).
- Exfiltration of model-provider API keys or held-out evaluation ground truth.
- A self-improvement loop propagating a backdoor or unsafe behavior across generations.
- Takeover of the orchestration control plane (system prompts, tool manifests, routing).

## High

- Prompt injection driving a single high-privilege tool misuse (funds, data deletion,
  outbound comms) within one session.
- Disclosure of one principal's memory/context across a session or tenant boundary.
- Memory or RAG poisoning that alters future agent decisions.
- Unbounded consumption (tokens, generations, sub-agents) causing cost blow-up or DoS.

## Medium

- Injection that degrades output quality or leaks non-sensitive information.
- A consequential tool action caught by a guardrail or human-in-the-loop check.
- Observability gaps that materially delay detection of agent misbehavior.

## Low

- Missing rate limit on a low-risk read-only tool.
- Verbose logging of non-sensitive agent traces.
- A missing but non-critical guardrail with no demonstrated exposure.
```

- [ ] **Step 4: Run the gate**

Run: `apd-gauntlet validate-domain agentic-ai`
Expected: `Domain pack 'agentic-ai' OK: schema valid, 1 include patterns all resolved.`

Run: `npx --yes markdownlint-cli2 "domains/agentic-ai/**/*.md"`
Expected: `Summary: 0 error(s)`

- [ ] **Step 5: Commit**

```bash
git add domains/agentic-ai/domain.yaml domains/agentic-ai/severity-rubric.md
git commit -m "feat(agentic-ai): pack skeleton — domain.yaml + severity rubric"
```

---

### Task 2: consequential-actions.md

**Files:**

- Modify: `domains/agentic-ai/domain.yaml` (append `  - consequential-actions.md` to `includes`)
- Create: `domains/agentic-ai/consequential-actions.md`

- [ ] **Step 1: Failing test** — append `  - consequential-actions.md` to the `includes:` block, then run `apd-gauntlet validate-domain agentic-ai`. Expected: FAIL — `Missing include in 'agentic-ai': consequential-actions.md`.

- [ ] **Step 2: Author the file**:

```markdown
# Agentic AI consequential-action surface

These are the actions an agentic system can take that must be authorized, attributable,
and audited. Specialists treat each as a write/decision whose absence from the audit log
or whose missing authorization is a finding.

## Tool and code execution

- Side-effecting tool invocation: shell, file write, network/API mutate, financial
  transaction, outbound communication, database write.
- Execution of agent-generated code.

## Self-modification

- Generating or rewriting agent code, prompts, or policies.
- Promoting or committing a new generation in a self-improvement loop.

## Credential and data access

- Retrieving or using secrets and model-provider/tool credentials.
- Reading held-out evaluation data or training ground truth.

## Memory and delegation

- Writing to long-term memory or the RAG/vector store.
- Spawning or delegating to a sub-agent.

## Configuration and escalation

- Switching model or provider.
- Acquiring new tools, scopes, or privileges at runtime.
- Merging agent output into a system of record.
```

- [ ] **Step 3: Pass** — `apd-gauntlet validate-domain agentic-ai` → `... 2 include patterns all resolved.`; `npx --yes markdownlint-cli2 "domains/agentic-ai/**/*.md"` → `0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add domains/agentic-ai/domain.yaml domains/agentic-ai/consequential-actions.md
git commit -m "feat(agentic-ai): consequential-action surface"
```

---

### Task 3: immutability-classes.md

**Files:**

- Modify: `domains/agentic-ai/domain.yaml` (append `  - immutability-classes.md` to `includes`)
- Create: `domains/agentic-ai/immutability-classes.md`

- [ ] **Step 1: Failing test** — append `  - immutability-classes.md` to `includes`, run `apd-gauntlet validate-domain agentic-ai`. Expected: FAIL — `Missing include in 'agentic-ai': immutability-classes.md`.

- [ ] **Step 2: Author the file**:

```markdown
# Agentic AI required-immutable data classes

Each class must be tamper-evident and retained. For each, the pack expects a retention
basis and a tamper-evidence mechanism (WORM, hash chain, signed commit, object lock).

## Agent execution and decision traces

Per-step tool calls, inputs, outputs, and the reasoning record. Basis: forensics and
attribution. Mechanism: append-only / hash-chained.

## Generation provenance and lineage

Which generation produced which agent code, under which model, prompt, and parent hash.
Basis: self-improvement accountability. Mechanism: append-only Merkle/git-style chain.

## Prompt, policy, and tool-manifest version history

The system prompts, guardrail config, and tool manifests that governed each decision.
Basis: drift detection and audit. Mechanism: config-as-code with signed commits.

## Evaluation results and scores

The held-out evaluation outcomes per generation. Basis: anti-gaming of the optimization
metric. Mechanism: scores hash-committed at compute time; WORM preservation.

## Model, tool, and SBOM provenance

Which model version and tool/dependency hashes were in play. Basis: supply-chain
attestation. Mechanism: signed SBOM / attestation store.

## Human and HITL approval records

Sign-offs on consequential actions. Basis: accountability and segregation of duties.
Mechanism: signed, append-only.
```

- [ ] **Step 3: Pass** — `validate-domain` → `3 include patterns all resolved.`; markdownlint `0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add domains/agentic-ai/domain.yaml domains/agentic-ai/immutability-classes.md
git commit -m "feat(agentic-ai): required-immutable data classes"
```

---

### Task 4: data-taxonomy.md

**Files:**

- Modify: `domains/agentic-ai/domain.yaml` (append `  - data-taxonomy.md` to `includes`)
- Create: `domains/agentic-ai/data-taxonomy.md`

- [ ] **Step 1: Failing test** — append `  - data-taxonomy.md` to `includes`, run `apd-gauntlet validate-domain agentic-ai`. Expected: FAIL — `Missing include in 'agentic-ai': data-taxonomy.md`.

- [ ] **Step 2: Author the file**:

```markdown
# Agentic AI data taxonomy

Sensitivity tiers and handling, tagged with the APD goals that care.

## Secrets and credentials (Confidentiality, Ephemeral)

Model-provider API keys, tool credentials, signing keys. Highest sensitivity; encryption,
JIT scoping, rotation, and no persistence in traces.

## Held-out evaluation data and ground truth (Confidentiality, Integrity)

The private eval set and labels. Read-scoped away from the agent process; leakage breaks
the optimization signal.

## Generated agent code and artifacts (Integrity, Authenticity)

Self-produced code. Integrity-critical and a backdoor vector; signed and provenance-tracked.

## Agent memory, context, and history (Confidentiality, Integrity)

May contain user PII, prior tool outputs, retrieved documents. Per-session/tenant scoped;
a poisoning target.

## Untrusted tool I/O and external content (Integrity)

Tool outputs, retrieved docs, web content. The injection carrier; provenance-tagged and
never trusted as instructions.

## Training and fine-tune data (Integrity)

A poisoning surface; provenance and validation on ingest.

## Decision and telemetry logs (Non-Repudiation, Confidentiality)

Audit-relevant; may carry sensitive content. Retained, attributable, access-scoped.

## Model weights and configuration (Confidentiality)

IP and an extraction target; encrypted at rest and access-scoped.
```

- [ ] **Step 3: Pass** — `validate-domain` → `4 include patterns all resolved.`; markdownlint `0 error(s)`.

- [ ] **Step 4: Commit**

```bash
git add domains/agentic-ai/domain.yaml domains/agentic-ai/data-taxonomy.md
git commit -m "feat(agentic-ai): data taxonomy"
```

---

## Tasks 5–13: the nine common-patterns

Each of Tasks 5–13 authors one `common-patterns/<goal>.md` file and appends its path to
`domain.yaml` `includes`. They share an identical rhythm; only the goal and its patterns
differ. **Author the prose from the pattern drafts** in
`docs/superpowers/plans/2026-05-31-agentic-ai-pack-pattern-drafts.md` (the goal's section),
in the canonical format below.

### Canonical pattern-file format

Match `domains/api-security/common-patterns/non-repudiation.md` exactly. Each file:

````markdown
# Agentic AI common patterns — <Goal>

These are illustrative templates, not all-inclusive. Use them to calibrate analytical
style, severity assignment per the agentic-AI rubric, and NIST/ATT&CK mapping habits. The
specialist agent's checklist still drives the actual analysis.

## Common finding patterns

**Pattern: <one-sentence statement of the agentic issue to look for>.**

- Severity: <critical|high|medium|low> (<one-clause rationale tied to the rubric>)
- NIST: <specific 800-53r5 controls, e.g. AC-6, AU-10, SC-7>
- Related concerns: <adjacent-goal routing, e.g. "ephemeral (credential lifetime); integrity (write authorization)">
- Detail: <prose that grounds the pattern — name the OWASP LLM item (LLM0x), the relevant ATLAS technique, the MAESTRO layer, and how SIA instantiates it>

**Pattern: <an evidence-gap variant uses the uncertainty form>.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "<the exact artifact needed to resolve it>"

## Common capability patterns

**Pattern: <the mature control, one sentence>.** <Inline maturity/scope cue — nascent / developing / robust, and what evidence raises it.>
````

Rules for every pattern file:

- **No CWE / ATT&CK / OWASP-LLM bullet fields.** The shipped packs do not carry them; specialists emit `taxonomy_mappings` (CWE/OWASP) and `control_mappings` (NIST + ATT&CK) in the FINDINGS at run time, guided by the `apd-control-mappings` skill. The pack hints with specific NIST controls in the `NIST:` bullet and grounds the OWASP-LLM / ATLAS / MAESTRO / SIA context in the `Detail:` prose. The candidate `taxonomy_mappings` in the drafts file are the specialist's guidance for the golden run, not markdown content.
- 6–8 finding patterns + 2–4 capability patterns per file (api-security convention). Use the goal's pattern list below.
- Weave the R1 cross-goal Excessive-Agency routing into `Related concerns` wherever a pattern touches agency (e.g. "read-scope is the Confidentiality facet of excessive agency").
- `NIST:` controls are specific (e.g. `AU-10`, `AC-6`, `SC-7`, `SI-10`), never bare families.

### Per-task rhythm (apply to each of Tasks 5–13)

- [ ] **Step 1: Failing test** — append `  - common-patterns/<goal>.md` to `domain.yaml`
  `includes`; run `apd-gauntlet validate-domain agentic-ai`. Expected: FAIL —
  `Missing include in 'agentic-ai': common-patterns/<goal>.md`.
- [ ] **Step 2: Author** `domains/agentic-ai/common-patterns/<goal>.md` per the format and
  the goal's pattern list (below), drawing prose/grounding/SIA from the drafts file.
- [ ] **Step 3: Pass** — `validate-domain` reports the incremented include count;
  `npx --yes markdownlint-cli2 "domains/agentic-ai/**/*.md"` → `0 error(s)`.
- [ ] **Step 4: Commit** — `git add domains/agentic-ai/domain.yaml domains/agentic-ai/common-patterns/<goal>.md && git commit -m "feat(agentic-ai): <Goal> patterns"`.

### Task 5 — `common-patterns/confidentiality.md`

- Provider API keys / secrets exposed to the agent's execution surface (LLM02/LLM06).
- Held-out evaluation ground-truth leakage into the optimization loop (LLM02/LLM06).
- Sensitive data in prompts, traces, run artifacts, and execution logs (LLM02/LLM05).
- System-prompt and meta-prompt leakage (LLM07/LLM02).
- Cross-session / cross-tenant agent memory and context bleed (LLM02/LLM08).
- **Inter-agent channel encryption-in-transit (Resolution R3 — new)** (LLM02): the
  inter-agent message bus payload must be encrypted; this owns channel-in-transit
  confidentiality (Authenticity owns who is on the bus; this owns secrecy of the payload).
- Model-weight / fine-tune-artifact extraction and exfiltration (LLM02).

### Task 6 — `common-patterns/integrity.md`

- **Prompt-injection input defense (Resolution R2 — new)** (LLM01): untrusted-context
  isolation, spotlighting/delimiting, dual-LLM/quarantine, and indirect injection from
  tool/RAG/web content. Owns input-side injection handling at the trust boundary, distinct
  from write authorization.
- Injected-instruction write/tool-action laundering (LLM01/LLM06/LLM05).
- Unverified self-modification merge — generated-code integrity (LLM04/LLM05/LLM03).
- Reward/eval-target tampering and **specification-gaming detection (Resolution R3)**
  (LLM04/LLM06): owns the eval-validity signal that Resilient consumes to trip its breaker.
- Agent memory / RAG write-path poisoning (LLM08/LLM04/LLM01).
- Tool-output trust without validation (LLM05/LLM06).
- Write-path authorization for self-modification and system-of-record merges (LLM06/LLM01).

### Task 7 — `common-patterns/availability.md`

- Unbounded autonomous-loop consumption — no generation/token/wall-clock/cost budget (LLM10/LLM06).
- Model-provider dependency reliability — no SLA, rate-limit headroom, degraded-mode plan (LLM10/LLM03).
- No SLO/SLI for autonomous task completion (LLM06).
- Capacity headroom for concurrent agents and execution sandboxes (LLM10/LLM06).
- Failure-domain and blast-radius analysis for the shared agent substrate (LLM10/LLM03).
- Shallow health checks and no liveness/progress detection for stuck loops (LLM10).

### Task 8 — `common-patterns/distributed.md`

- Orchestrator / control-plane as a single point of failure (LLM06/LLM10).
- Model-provider / inference endpoint as a single point of failure (LLM03/LLM10).
- Stateful agent memory versus stateless workers boundary (LLM06).
- Multi-agent topology, message routing, and CAP positioning under partition (LLM06).
- Shared vector store / agent memory — locality, replication, consistency (LLM08).
- Sub-agent fan-out and inference load distribution (LLM10/LLM06).

### Task 9 — `common-patterns/resilient.md`

- No circuit breaker on the autonomous self-improvement / task loop (LLM06/LLM10).
- Retry/backoff discipline on model and tool calls (LLM10/LLM05).
- Bulkheads / resource isolation around code-exec sandboxes and per-agent quotas (LLM10/LLM06).
- Timeout discipline on autonomous steps, tool calls, and reasoning chains (LLM10/LLM06).
- Graceful degradation when a model/tool/guardrail is down — fail-safe, not
  fail-open-and-keep-acting (LLM06/LLM05).
- Backpressure on generation / sub-agent fan-out and the inter-agent message bus (LLM10).

### Task 10 — `common-patterns/ephemeral.md`

- Standing broad agency versus JIT scoped tool credentials (LLM06/LLM01).
- Long-lived provider API keys with no rotation cadence or automation (LLM02).
- No ephemeral sandbox per code-execution (LLM06/LLM05).
- Sub-agent / spawned-agent credentials lack independent expiry and revocation (LLM06/LLM01).
- Compromised-generation credential revocation and blast-radius containment (LLM04/LLM06).
- Unbounded agent session / memory TTL (LLM10/LLM06).

### Task 11 — `common-patterns/authenticity.md`

- Self-produced agent code emitted unsigned / no per-generation provenance (LLM06/LLM05/LLM03).
- Agent / sub-agent workload identity absent — shared API keys, no SPIFFE-class identity (LLM06).
- Inter-agent messages unsigned — impersonation, Sybil, goal-manipulation cascade (LLM01/LLM06).
- Tool / plugin / MCP-server authenticity not verified before binding (LLM03/LLM06).
- Model and dependency provenance unattested — no SBOM / SLSA (LLM03/LLM04).
- Human operator of the autonomous loop authenticated below the required AAL (LLM06).

### Task 12 — `common-patterns/non-repudiation.md`

- Consequential-action audit completeness vs the agentic action surface (LLM06/LLM05).
- Per-entry actor attribution across agent / sub-agent / human / generation (LLM06).
- Signed, hash-chained decision/action traces (LLM05/LLM06).
- Reliable, ordered time source across the loop and across generations (LLM06).
- Audit-read/alter access control with segregation of duties from the agents (LLM06).
- Audit shipping reliability to a durable off-host sink (LLM10).

### Task 13 — `common-patterns/immutability.md`

- Append-only generation lineage / provenance chain (LLM04/LLM03/LLM06).
- WORM execution / decision traces — tool-call and action ledger (LLM06/LLM05).
- Immutable eval results / scores — anti-gaming of the optimization metric (LLM04/LLM09/LLM06).
- Guardrail config-as-code version history and drift detection (LLM06/LLM01/LLM07).
- Backup immutability for held-out ground truth and golden agent state (LLM04/LLM10).
- Snapshot integrity of agent / shared memory state (LLM04/LLM08).

---

### Task 14: pack validation test + compile check

**Files:**

- Create: `tests/test_agentic_ai_pack.py`

- [ ] **Step 1: Write the test**

```python
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "domains" / "agentic-ai"
GOALS = [
    "confidentiality", "integrity", "availability", "distributed", "resilient",
    "ephemeral", "authenticity", "non-repudiation", "immutability",
]


def test_all_14_files_present():
    assert (PACK / "domain.yaml").is_file()
    for f in ["severity-rubric.md", "consequential-actions.md",
              "immutability-classes.md", "data-taxonomy.md"]:
        assert (PACK / f).is_file(), f
    for g in GOALS:
        assert (PACK / "common-patterns" / f"{g}.md").is_file(), g


def test_includes_list_all_thirteen():
    data = yaml.safe_load((PACK / "domain.yaml").read_text())
    expected = {"severity-rubric.md", "consequential-actions.md",
                "immutability-classes.md", "data-taxonomy.md"} | {
        f"common-patterns/{g}.md" for g in GOALS}
    assert set(data["includes"]) == expected


def test_validate_domain_passes():
    r = subprocess.run(
        [sys.executable, "-m", "apd_gauntlet.cli", "validate-domain", "agentic-ai"],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout


def test_pattern_files_have_sections_and_grounding():
    for g in GOALS:
        text = (PACK / "common-patterns" / f"{g}.md").read_text()
        assert "## Common finding patterns" in text, g
        assert "## Common capability patterns" in text, g
        # OWASP-LLM grounding must be woven into the Detail prose (LLM01..LLM10).
        assert re.search(r"LLM0[1-9]|LLM10", text), f"{g}: no OWASP-LLM grounding"
```

- [ ] **Step 2: Run the test**

Run: `python3 -m pytest tests/test_agentic_ai_pack.py -v`
Expected: PASS (all four). If `test_pattern_files_have_sections_and_grounding` fails, the
pattern file is missing a required section or did not weave its OWASP-LLM grounding into
the prose — fix the file, not the test.

- [ ] **Step 3: Compile check + full regression**

Run: `apd-gauntlet build-domain-skill agentic-ai`
Expected: `Wrote .claude/skills/apd-domain/SKILL.md` (confirms the 14 files compile).

Run: `git checkout -- .claude/skills/apd-domain/SKILL.md`
(Restore the tracked build artifact — pack authoring does not commit it; the gauntlet
workflow regenerates it per run.)

Run: `python3 -m pytest -q` → all green (no regression).
Run: `python3 -m mypy tools/` → clean.
Run: `ruff check tools/ tests/` → clean.
Run: `npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"` → `0 error(s)` (the full CI glob — the new pack is under `domains/**`).

- [ ] **Step 4: Commit**

```bash
git add tests/test_agentic_ai_pack.py
git commit -m "test(agentic-ai): pack validates + structural/grounding guard"
```

---

### Task 15: golden run against hexo-ai/sia

Executes the `apd-gauntlet` Workflow against the real SIA codebase and commits the run as a
golden fixture. It is analytical (LLM-driven), not unit-tested for content; its gate is
structural validity plus a quality review.

**Files:**

- Create: `runs/apd-<date>-sia-self-improving-agent/` (the full run tree)

- [ ] **Step 1: Clone the target and prepare inputs**

```bash
git clone --depth 1 https://github.com/hexo-ai/sia /tmp/sia
mkdir -p /tmp/sia-inputs
```

Author `/tmp/sia-inputs/tech_plan.md` — a concise architecture description of SIA (the
Meta-Agent generates `target_agent.py` which executes arbitrary Python; the Target Agent
runs the task logging to `agent_execution.json`; the Feedback Agent rewrites the target
across `--max_gen` generations; optimization is against a benchmark with held-out
`data/private/` ground truth via `evaluate.py`; multiple model-provider API keys; artifacts
under `runs/run_id/gen_n/`; built on the Claude Agent SDK + OpenHands). Note the local clone
path `/tmp/sia`. Optionally also write `architecture-index.md` and `happy-path.md`.

- [ ] **Step 2: Scaffold the run**

Pick `<date>` = today (e.g. `20260605`).

```bash
apd-gauntlet init-run apd-<date>-sia-self-improving-agent \
  --inputs /tmp/sia-inputs \
  --domain agentic-ai \
  --taxonomies owasp_llm_top10,mitre_attack,cwe
```

- [ ] **Step 3: Complete `.apd-run.yaml`**

Edit `runs/apd-<date>-sia-self-improving-agent/.apd-run.yaml`:

- Set `framework_version: 1.5.0` (`init-run` scaffolds `1.1.0`; match the sibling golden runs).
- Set `code_recon: disabled` with a comment that the SIA repo is at `/tmp/sia`, not
  CBM-indexed (or `enabled` if you index it first via codebase-memory-mcp).
- Add a `subject:` line describing the target. Note: `subject:` is a convention used by the
  committed golden runs; it is NOT in `run-config.schema.json`, so do not validate this file
  with `validate-run-config` (which has `additionalProperties: false`). The `validate
  <run-dir>` gate in Step 6 does not check the run-config schema, so `subject:` is fine.
- **Mirror the pack's crown jewels and attacker positions** (the attack-path builder looks
  them up from the run dir, so they must be declared here — corroborated by the crapi run):

```yaml
crown_jewels:
  - tool_execution_capability
  - model_provider_credentials
  - training_and_eval_data
  - agent_memory_store
  - self_improvement_loop
  - orchestration_control_plane
attacker_positions:
  - untrusted_content_source
  - malicious_task_author
  - malicious_tool_or_plugin
  - compromised_model_provider
  - cotenant_or_sandbox_neighbor
  - malicious_peer_agent
```

- [ ] **Step 4: Execute the gauntlet Workflow**

Invoke the registered `apd-gauntlet` Workflow with the run config as `args` (the controller
runs this via the Workflow tool, not a shell command):

```text
Workflow(name: "apd-gauntlet", args: <parsed runs/apd-<date>-sia-self-improving-agent/.apd-run.yaml>)
```

The Workflow runs setup (validate-domain + build-domain-skill agentic-ai) → intake → the
nine specialists → attack-path → synthesis → HTML report → audit → domain-improvement
capture → closeout.

- [ ] **Step 5: Quality-review the output**

Read `40-synthesis/advisory-report.md` and a sample of the specialist findings. Confirm
they are grounded in SIA's actual code/architecture (evidence pointers resolve), in-lens
for their goal, and that the agentic crown jewels (self-improvement loop, eval data, keys,
tool execution) surface across the nine goals. Confirm the mapping discipline held in the
emitted findings (no pillar/category CWEs; high-confidence ATT&CK; empty ATT&CK on
provenance/audit-completeness gaps). If a specialist produced thin or off-lens output,
re-dispatch that lens (the Workflow supports resume).

- [ ] **Step 6: Structural gate**

Run: `apd-gauntlet validate runs/apd-<date>-sia-self-improving-agent/`
Expected: `Clean.` (exit 0 — schema valid, ids resolve, cross-file refs resolve). Confirm
`40-synthesis/report-html/data.js` exists.

- [ ] **Step 7: Commit the golden run**

```bash
git add runs/apd-<date>-sia-self-improving-agent/
git commit -m "feat(agentic-ai): golden gauntlet run vs hexo-ai/sia"
```

- [ ] **Step 8: Capture dogfood notes** — append any authoring friction encountered against
  today's `docs/adapting-to-other-domains.md` to a scratch list for sub-project 2 (the docs
  overhaul). This is a note, not a committed artifact.

---

## Self-review

1. **Spec coverage** — every spec section maps to a task: 14 files (Tasks 1–13), the
   validate gate (every task), the canonical format + mapping guidance (Tasks 5–13), the
   three Resolutions (Tasks 5/6/9 prose + the severity-rubric note), structural/grounding
   guards + compile check (Task 14), the golden run (Task 15), the acceptance bar
   (Tasks 14–15). Future efforts (ATLAS/MAESTRO) are out of scope by design.
2. **Placeholder scan** — `<goal>`, `<date>`, `<Goal>` are explicit templates with
   concrete substitution rules, not unfilled blanks; no `TBD`/`TODO`.
3. **Consistency** — `name: agentic-ai`, the 13 `includes` paths, the nine goal filenames
   (`non-repudiation.md` hyphenated), and the crown-jewel/attacker-position keys are
   identical across `domain.yaml` (Task 1), Task 15's `.apd-run.yaml` mirror, and the test
   (Task 14). The pattern markdown carries no CWE/ATT&CK bullets (matches the shipped
   packs); mappings are emitted in findings and guarded in the golden-run review, not the
   markdown.
