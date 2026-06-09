# Adapting to Other Domains

The APD Gauntlet framework is domain-neutral. The nine APD goals, the finding and capability schemas, the evidence-discipline rules, and the validator behavior never change. What changes per domain is the *calibration*: the severity rubric, the consequential-action surface, the immutability classes, the data taxonomy, the crown jewels and attacker positions that drive attack-path analysis, and the per-goal pattern catalogs.

This guide is a complete reference for authoring a domain pack. It dissects the shipped `agentic-ai` pack (autonomous LLM-agent systems) as the running worked example, and keeps the reusable PBM multi-regulator retention-pinning pattern. When you are ready to evolve a pack from real runs, see [improving-domain-packs.md](improving-domain-packs.md).

## 1. How a pack influences a run

A domain pack is compiled by `apd-gauntlet build-domain-skill` into the `.claude/skills/apd-domain/` skill that every specialist loads at the start of a run. Through that skill the pack does four things:

- **Calibrates severity.** Each specialist cites the active pack's `severity-rubric.md` clause in a finding's `detail`, so the rubric thresholds decide what is critical versus high versus medium for this domain.
- **Defines the consequential-action surface.** `consequential-actions.md` enumerates the audit-worthy actions the Non-Repudiation lens checks for, and `immutability-classes.md` names the data classes the Immutability lens expects to be write-once.
- **Supplies crown jewels and attacker positions.** The `crown_jewels`, `attacker_positions`, and `default_trust_boundaries` blocks in `domain.yaml` activate the `apd-attack-path-analyzer`: they become the default enumeration sinks, the default source set, and the trust-topology hints when `.apd-run.yaml` does not override them.
- **Seeds the per-goal pattern catalogs.** The nine `common-patterns/<goal>.md` files calibrate the analytical style, the severity assignment, and the NIST/ATT&CK mapping habits a specialist applies in each lens.

Everything else — the lens definitions, the boundary calls between adjacent goals, the three analytical disciplines — stays identical across domains. The pack is calibration, not a rewrite of the framework.

**Full skill vs per-goal sidecars.** `build-domain-skill` emits the full cross-goal `SKILL.md` *and* nine goal-scoped sidecars at `.claude/skills/apd-domain/by-goal/<goal>.md`. Each sidecar carries all four calibration files plus the merged attack-path defaults, but only its own goal's `common-patterns` — so a lens specialist (e.g. `apd-confidentiality`) reads `by-goal/confidentiality.md`, not the other eight goals' patterns. This bounds per-lens context on multi-domain runs (the saving grows with pack count). The full `SKILL.md` is still read by the cross-goal consumers — `apd-intake`, `apd-attack-path-analyzer`, and `apd-domain-auditor`. Every sidecar's frontmatter carries a `pruned` manifest naming exactly which goal it is scoped to and which goal-pattern files were omitted (no silent caps). Pass `--full-only` to suppress sidecar emission.

## 2. Anatomy: the 14 files and the `domain.yaml` schema

A pack is a directory under `domains/<name>/` containing exactly 14 files — `domain.yaml`, the four calibration files, and the nine per-goal pattern files:

```text
domains/<name>/
├── domain.yaml                  # metadata + crown jewels / attacker positions / trust boundaries
├── severity-rubric.md           # critical/high/medium/low thresholds for this domain
├── consequential-actions.md     # audit-worthy actions (for Non-Repudiation)
├── immutability-classes.md      # data classes that must not change (for Immutability)
├── data-taxonomy.md             # field-level data classification with regulatory citations
└── common-patterns/
    ├── confidentiality.md
    ├── integrity.md
    ├── availability.md
    ├── distributed.md
    ├── resilient.md
    ├── ephemeral.md
    ├── authenticity.md
    ├── non-repudiation.md
    └── immutability.md
```

### The `domain.yaml` schema

`domain.yaml` is validated against `schemas/domain.schema.json`. The required fields are:

- `name` — `^[a-z][a-z0-9-]*$` (lowercase, the directory name).
- `display_name` — at least 3 characters.
- `version` — semver `^[0-9]+\.[0-9]+\.[0-9]+$`.
- `framework_compat` — a semver range string (at least 5 characters); the validator refuses to build the skill if the active framework version falls outside it.
- `description` — at least 20 characters.
- `includes` — at least one path, each with no leading `/` and no `..`; the runtime skill is assembled from these files.
- `regulatory_anchors` — a list of strings.

There is also one optional top-level field beyond the three attack-path blocks:

- `taxonomies` — an optional array of taxonomy enum strings (e.g. `masvs`, `maswe`, `mitre_atlas`) the pack wants in scope by default. At `init-run`, the selected packs' declared taxonomies are unioned into the run-config `taxonomies:` list (pack -> run auto-seed), so an operator who selects the pack gets those taxonomies without naming them. The operator can still add or remove taxonomies in `.apd-run.yaml` afterward. The `mobile-applications` pack declares `taxonomies: [masvs, maswe]`; a pack that omits the field changes nothing about run scope.

The three attack-path blocks are optional. Each is a list of `{<key>, description}` objects where the key is `pattern` (for `crown_jewels`), `position` (for `attacker_positions`), or `boundary` (for `default_trust_boundaries`), and `description` is at least 10 characters. A pack that omits all three remains framework-compatible; the analyzer simply has no defaults to enumerate over unless the run supplies them.

### The `agentic-ai` `domain.yaml`

```yaml
name: agentic-ai
display_name: "Agentic AI (Autonomous LLM Agents)"
version: 1.0.0
framework_compat: ">=1.0.0,<2.0.0"
description: "Security-architecture calibration for autonomous LLM-agent systems — tool-use agents, multi-agent topologies, autonomous task loops, and code-generation-and-execution — with self-improving / self-modifying systems treated as a first-class sub-surface. Anchored to the EU AI Act, NIST AI RMF (AI 100-1), ISO/IEC 42001, NIST SP 800-53r5, and grounded in the OWASP LLM Top 10 (2025), MITRE ATLAS, and CSA MAESTRO."
includes:
  - severity-rubric.md
  - consequential-actions.md
  - immutability-classes.md
  - data-taxonomy.md
  - common-patterns/confidentiality.md
  - common-patterns/integrity.md
  - common-patterns/availability.md
  - common-patterns/distributed.md
  - common-patterns/resilient.md
  - common-patterns/ephemeral.md
  - common-patterns/authenticity.md
  - common-patterns/non-repudiation.md
  - common-patterns/immutability.md
regulatory_anchors:
  - "EU AI Act"
  - "NIST AI RMF (AI 100-1)"
  - "ISO/IEC 42001"
  - "NIST SP 800-53r5"
```

The pack declares six crown jewels under `crown_jewels`, each a `{pattern, description}` object:

```yaml
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
```

It declares six `attacker_positions` (`untrusted_content_source`, `malicious_task_author`, `malicious_tool_or_plugin`, `compromised_model_provider`, `cotenant_or_sandbox_neighbor`, `malicious_peer_agent`) and six `default_trust_boundaries` (`untrusted_content_to_agent_reasoning`, `agent_to_execution_sandbox`, `agent_to_model_provider`, `agent_to_secret_store`, `generation_n_to_n_plus_1`, `agent_to_agent_channel`), each with the same `{<key>, description}` shape.

## 3. Step-by-step authoring (dissecting agentic-ai)

### 3.1 Copy a starting pack

```bash
cp -r domains/pbm domains/agentic-ai
```

Start from an existing pack so all 14 files and the `includes` list exist, then rewrite each.

### 3.2 Edit `domain.yaml`

Set `name`, `display_name`, `version`, `framework_compat`, `description`, and `regulatory_anchors`. The `agentic-ai` pack anchors to the EU AI Act, NIST AI RMF (AI 100-1), ISO/IEC 42001, and NIST SP 800-53r5 (see the block in section 2). Then declare the crown jewels, attacker positions, and trust boundaries — the six-of-each agentic example above is the model.

### 3.3 Rewrite `severity-rubric.md` (the four agentic modifiers)

The rubric anchors severity to domain impact. The `agentic-ai` rubric calibrates impact using four agentic modifiers — **autonomy** (acted without human confirmation), **reversibility**, **blast radius** (single session versus cross-tenant or cross-generation persistence), and **data sensitivity** — and raises severity when an outcome is autonomous, irreversible, persists across sessions or generations, or crosses a tenant or provider boundary. For example, its **Critical** band includes attacker-controlled code or tool execution against production from a prompt-injected or poisoned agent, exfiltration of model-provider API keys or held-out evaluation ground truth, a self-improvement loop propagating a backdoor across generations, and takeover of the orchestration control plane. The rubric also notes that OWASP LLM06 (Excessive Agency) is cross-cutting: it decomposes across goals (read-scope under Confidentiality, side-effecting write authorization under Integrity, just-in-time permission lifetime under Ephemeral, blast-radius isolation under Resilient) rather than living in a separate confinement goal. Cite the regulatory anchors precisely; specialists reference the matching clause in finding `detail` fields, so clauses must be specific enough to reference.

### 3.4 Rewrite the three support files

- **`consequential-actions.md`** — the audit-worthy actions for Non-Repudiation. For agentic systems these are tool invocations, code execution, generation-promotion events, and inter-agent message routing.
- **`immutability-classes.md`** — the data classes that must not change after writing. For agentic systems these include prior-generation agent code, recorded eval scores, and provenance lineage.
- **`data-taxonomy.md`** — the field-level data classification with regulatory citations (agent memory and PII, model-provider credentials, training and held-out eval data).

### 3.5 Rewrite the nine `common-patterns/<goal>.md` files (the canonical format)

Each goal file has a "Common finding patterns" section and a "Common capability patterns" section. The canonical finding-pattern format — verified against `domains/agentic-ai/common-patterns/integrity.md` — is a bold `**Pattern: …**` line followed by a dash-bulleted block carrying these keys:

- `Severity` — the severity band and the rubric rationale (which agentic modifiers load).
- `NIST` — the relevant SP 800-53r5 control IDs (e.g. `SI-10, SI-15, SC-7, AC-4`).
- `Related concerns` — the adjacent goals the pattern touches.
- `Detail` — prose that grounds the threat in OWASP LLM, MITRE ATLAS, and CSA MAESTRO language and names the structural control.

A blocked/uncertainty pattern instead carries a `Disposition` line and a `prerequisite_evidence` line. The capability patterns are bold `**Pattern: …**` lines with an inline `Maturity:` ladder. For example, the first integrity finding pattern in the pack reads (abridged):

```text
**Pattern: Untrusted context (tool output, fetched web/RAG content, a peer
agent's message, task input) flows into the model's instruction channel with
no isolation, spotlighting, or quarantine — indirect prompt injection has an
open lane.**

- Severity: high to critical (critical when the injected lane can reach a
  privileged write or code-exec sink…)
- NIST: SI-10, SI-15, SC-7, AC-4
- Related concerns: confidentiality…, agency-write-authz=Integrity…
- Detail: …the threat is ATLAS LLM Prompt Injection (AML.T0051)… MAESTRO L2
  Data Operations… the structural fix is to spotlight/quarantine untrusted
  spans and treat them as data, never as instructions.
```

#### The lesson: taxonomy mappings live in findings, not in pattern bullets

Taxonomy mappings — CWE, MITRE ATT&CK/ATLAS technique IDs, OWASP-LLM categories — are emitted by the specialists **in the findings they produce**, not written as structured bullet rows in the pattern markdown. The `common-patterns/<goal>.md` markdown carries the four calibration keys (`Severity`, `NIST`, `Related concerns`, `Detail`) and grounds OWASP-LLM / ATLAS / MAESTRO references **in prose inside the `Detail` field** to calibrate how a specialist should think. A specialist then maps the specific technique to the specific finding it raises, on that finding's record, where the evidence pointer makes the mapping defensible. Do not add a CWE bullet or an ATT&CK-IDs bullet to the pattern file; that calibrates nothing and duplicates what the finding already carries.

### 3.6 Validate, build, and run

Once the 14 files are written, validate the pack:

```bash
apd-gauntlet validate-domain agentic-ai
```

This loads `domain.yaml`, validates it against `schemas/domain.schema.json`, and verifies every `includes` file resolves. `validate-domain` takes positional, space-separated pack names, so you can validate several packs at once. Then compile the skill:

```bash
apd-gauntlet build-domain-skill agentic-ai --framework-version 1.0.0
```

This writes `.claude/skills/apd-domain/SKILL.md` from the pack. Confirm the generated skill carries all the expected sections, then author a sample run under `examples/` and validate it (`apd-gauntlet validate examples/<your-example>/expected/`), wiring it into `tests/test_examples.py`.

## 4. Multi-domain mechanics

A single run can examine a solution across more than one pack at once. The run-config key is `domains:` — a YAML list — and `build-domain-skill` accepts an ordered set of positional pack names, merging them into one `apd-domain` skill. The merge engine (see `docs/superpowers/specs/2026-05-30-multi-domain-runs-design.md`) is per-component:

- **Surface union, deduped by key.** `crown_jewels`, `attacker_positions`, and `default_trust_boundaries` are concatenated across packs and deduped by key (`pattern` / `position` / `boundary`); each retained item records the contributing pack(s). When two packs define the same key with materially different descriptions, both are retained, attributed.
- **Calibration prose, per pack under provenance headers.** Each pack's `severity-rubric.md`, `consequential-actions.md`, `immutability-classes.md`, and `data-taxonomy.md` is emitted under a `## Domain: <pack> — Source: <file>` header, so every rubric and surface is present and labeled by origin.
- **Patterns, per goal, unioned.** For each of the nine goals, the contributing packs' `common-patterns/<goal>.md` files are concatenated under the same provenance headers.
- **`metadata.packs` frontmatter.** The compiled skill records `metadata.packs: [{name, version}, …]` in declared order; the workflow rebuilds the skill whenever the selected pack set changes (the staleness guard compares `metadata.packs` to the run's `domains`).

Severity reconciliation is **union + max + provenance**: a specialist cites the governing pack and clause, takes the max severity when more than one pack's clause matches, and a harm that matches no clause in any selected pack becomes a domain-improvement-opportunity candidate. For how packs are selected at run time (`init-run --domain pbm --domain api-security` and the resulting `domains:` block in `.apd-run.yaml`), see [running-the-gauntlet.md](running-the-gauntlet.md).

## 5. Taxonomy and mapping discipline

Two structural conventions for MITRE ATT&CK references have emerged across the shipped packs. The PBM pack carries a dedicated `## ATT&CK + D3FEND defensive mapping` section in every common-patterns goal file *as well as* inline ATT&CK references on individual patterns. The three newer packs (`api-security`, `identity-security`, `security-tooling`) use inline references only. Both are valid; choose one and apply it consistently within a pack — do not mix conventions across goals. For new packs the recommended default is inline-only: it matches the newer packs and keeps the per-pattern prose the unambiguous source of truth.

For agentic packs specifically, the threat frameworks are grounded **as prose in the `Detail` field**, not as taxonomy bullets: OWASP LLM Top 10 categories (e.g. LLM01 Prompt Injection), MITRE ATLAS technique IDs (e.g. AML.T0051), and CSA MAESTRO layers (e.g. L2 Data Operations) appear inside the pattern's `Detail` narrative to calibrate the specialist's mapping habits. **MITRE ATLAS is also a first-class taxonomy**: declare `mitre_atlas` in `.apd-run.yaml` and specialists emit `atlas` technique IDs in structured finding fields — feeding the `atlas-coverage` synthesis rollup (emitted when the taxonomy is declared, as for CWE and D3FEND) and the report's taxonomy tooltips, with titles resolved by `apd-gauntlet refresh-atlas` (see the `apd-control-mappings` skill). **CSA MAESTRO is also a recognized threat-model methodology** for *supplied threat models* — a reduced-fidelity `methodology_hint: maestro` that routes through the free-form envelope with an L1–L7 → APD-goal mapping in the `apd-threat-model-methodologies` skill, so MAESTRO layers shape an entry's `inferred_apd_goals` even though, within pack pattern `Detail` fields, they stay calibration prose. Treating MAESTRO layers as a structured finding field (rather than `Detail` prose) remains a possible future framework effort. The actual CWE/ATT&CK/ATLAS/OWASP-LLM mapping is emitted on the finding the specialist raises, per the lesson in section 3.5.

The `mobile-applications` pack additionally declares the **OWASP MASVS** and **OWASP MASWE** taxonomies via the optional `taxonomies: [masvs, maswe]` field in its `domain.yaml`, so selecting the pack auto-seeds both into the run's `taxonomies:` list. Mobile specialists emit `masvs` control IDs (on findings **and** capabilities) and `maswe` weakness IDs (findings only) in `control_mappings`, feeding the `masvs-coverage`/`maswe-coverage` synthesis rollups and the report's MASVS/MASWE Coverage sub-tabs; titles resolve via `apd-gauntlet refresh-mas`. As with CWE/ATT&CK/ATLAS, the actual MASVS/MASWE mapping is emitted on the finding or capability the specialist raises — not as bullet rows in the pattern markdown.

## 6. Reusable pattern: multi-regulator retention pinning

When a single data class is governed by more than one regulator (or by a regulator plus a contract floor), `immutability-classes.md` should not pick one and ignore the others. Instead, declare retention by *pinning to the longest applicable floor* and enumerate every floor that contributes. The canonical phrasing used in `domains/pbm/immutability-classes.md` is:

> Retention is pinned to the longest of (a) *regulatory floor A*, (b) *regulatory floor B*, (c) *contract floor*.

Use this pattern whenever a data class is covered by overlapping obligations — for example, HIPAA plus CMS Part D plus a network-pharmacy contract; or GDPR plus a sector-specific national retention law plus a customer master agreement; or PCI-DSS plus a card-network operating regulation plus a merchant contract. The trigger is "more than one source can independently demand a retention floor on this class," not "we have lots of regulators."

Specify each floor concretely. A regulatory floor needs a CFR or USC (or non-US-equivalent) section citation so the synthesizer and downstream auditors can verify the duration without re-deriving it. A contract floor needs a reference to the master-agreement type whose retention clause is the source. A signed-artifact floor — used when the artifact's signature must remain verifiable for as long as the signed artifact itself is retained anywhere — needs a reference to the retention obligation on the signed artifact, not a fixed duration.

The synthesizer's posture when the declared floors disagree: the **longest floor wins** for the actual retention configuration, and the others remain operative as audit-defensibility evidence. Specialists do not file a contradiction finding when the floors differ in duration — that is the *expected* shape of multi-regulator overlap. Specialists do file a finding when (a) only one floor is named and the data class plainly falls under another regulator the pack lists, or (b) the configured retention is shorter than the longest declared floor.

### Worked example: cryptographic key lifecycle records (from PBM pack)

The cryptographic key lifecycle class in `domains/pbm/immutability-classes.md` covers every CMS PDE signing key, NCPDP SCRIPT message-signing key, and key-encrypting key in the PBM's custody — creation, rotation, suspension, and destruction events. Retention is pinned to the longest of:

- **(a) HIPAA 6-year** per 45 CFR §164.316(b)(2)(i) — covers the key records as HIPAA security-policy documentation.
- **(b) CMS Part D 10-year PDE retention** per 42 CFR §423.505(d) — required because PDE submissions are signed with these keys and CMS audit defensibility depends on proving which key signed which PDE.
- **(c) Any signed-artifact retention floor that outlives both** — covers cases where a long-lived signed artifact (e.g. a multi-year rebate contract attestation) still references a key, so the key record must survive as long as the artifact does.

The configured floor is 10 years from CMS Part D, *unless* a covered signed artifact extends past that. The HIPAA 6-year clause is not redundant: it is the floor the PBM cites to HHS OCR if the CMS retention is ever shortened, and the floor an HHS investigator references when reviewing security-policy documentation. All three remain operative as audit-defensibility evidence even though only the longest controls the storage configuration.

## 7. Evolving a pack from runs

Once a pack is in use, every gauntlet run captures the places it is still incomplete into `runs/<id>/40-synthesis/domain-improvements.yaml` and offers a deterministic command to turn chosen gaps into a reviewable patch. See [improving-domain-packs.md](improving-domain-packs.md) for the read → draft → review → `git apply` → re-validate workflow. The capture is advisory and non-blocking; you always own the apply and the commit.

## 8. Submitting the pack

Open a PR with a complete pack. The checklist:

- **All 14 files present** — `domain.yaml`, the four calibration files, and the nine `common-patterns/<goal>.md` files.
- **`apd-gauntlet validate-domain <pack>` clean** — `domain.yaml` validates against `schemas/domain.schema.json` and every `includes` file resolves.
- **`apd-gauntlet build-domain-skill <pack> --framework-version <v>` clean** — the pack compiles into a rebuildable `apd-domain` skill.
- **Taxonomy mappings are in findings, not markdown** — the pattern files carry `Severity` / `NIST` / `Related concerns` / `Detail` and ground OWASP-LLM/ATLAS/MAESTRO in prose; CWE/ATT&CK technique IDs are emitted on the findings the specialists raise.
- **A sample run validates** — add a curated `examples/<your-sample-run>/` whose expected outputs pass `apd-gauntlet validate examples/<your-sample-run>/expected/`, and wire it into `tests/test_examples.py`.

Use the [domain_pack_proposal](../.github/ISSUE_TEMPLATE/domain_pack_proposal.yml) issue template to open a discussion first. CI runs `apd-gauntlet validate-domain <pack>` automatically on every PR touching a `domains/` directory.

## 9. What stays the same across domains

- Lens definitions (the `apd-framework` skill) and the nine APD goals.
- Boundary calls between adjacent goals.
- The three analytical disciplines (evidence-pointer, block-on-ambiguity, stay-in-your-lens).
- The finding and capability schema contracts.
- Validator behavior and the NIST/ATT&CK/D3FEND mapping guidance.

Only the calibration files in `domains/<name>/` change. The framework's analytical structure is domain-agnostic by design — that is what makes the pack model workable.
