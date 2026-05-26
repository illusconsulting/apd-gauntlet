# APD Gauntlet — Threat Model & Attack Path Analysis — Design Spec

**Date:** 2026-05-25
**Status:** Approved (brainstorming complete; ready for implementation planning)
**Scope:** Add multi-framework taxonomy mappings (CWE / OWASP Top 10 / OWASP API Top 10 / OWASP LLM Top 10 / MITRE D3FEND, extending existing MITRE ATT&CK + NIST 800-53r5), methodology-aware threat-model evaluation (STRIDE / LINDDUN / attack-tree), and BloodHound-style attack-path enumeration with a D3FEND defensive overlay. Three phases, one epic, additive within v1.x — no breaking schema changes.

---

## 1. Context

APD Gauntlet v1.1 ships 13 agents (orchestrator, intake, synthesizer, 9 specialists, optional `apd-code-recon`) and produces findings + capabilities mapped to NIST 800-53r5 and (high-confidence-only) MITRE ATT&CK. The output is rigorous but speaks the APD taxonomy fluently; reviewers who know CWE, OWASP, or D3FEND but not APD lose information in translation.

Two related capability gaps:

1. **Limited framework vocabulary.** Findings and capabilities don't carry CWE, OWASP (web / API / LLM), or D3FEND mappings. These are the vocabularies most security practitioners read fluently. Adding them makes the same analysis legible to wider audiences without changing the underlying lens-driven work.
2. **Threat models are inert inputs.** The intake agent currently catalogs supplied threat models as evidence pointers but does not actively evaluate them. Practitioners produce STRIDE-per-element diagrams, LINDDUN tables, attack trees, and PASTA narratives that contain rich claims about adversary models — the gauntlet should be able to *interrogate* those claims, surface contradictions with its own findings, and identify coverage gaps.
3. **No attack-path synthesis.** Today every finding is independent. Adversaries chain techniques; the gauntlet's exposed-technique list doesn't tell a reviewer which combinations of findings constitute a credible kill chain from an attacker position to a crown-jewel asset, or which capabilities sit on bottleneck edges along those chains.

This spec describes the additions to address all three, sequenced as three internally independent phases.

## 2. Design Decisions (locked)

| Dimension | Decision |
|---|---|
| Distribution | Same repo, same plugin, same Python package — no separate distribution |
| Phasing | Three phases (Track 1 → Track 2 → Track 3), each independently ship-able |
| Versioning | Additive within v1.x — Phase A v1.2.0, Phase B v1.3.0, Phase C v1.4.0; all new schema fields optional; no v2 breaking-change cliff |
| Taxonomy scoping | Per-run config (`taxonomies: [...]`) with intake auto-detect suggestions; CWE/ATT&CK/D3FEND default-on, OWASP variants opt-in |
| Taxonomy attachment | Findings carry CWE + OWASP; capabilities carry D3FEND (symmetry with existing ATT&CK technique-on-findings, mitigation-on-capabilities split) |
| Threat-model evaluator | Methodology-aware (STRIDE / LINDDUN / attack-tree natively in v1; PASTA / VAST / Trike / free-form accepted with reduced fidelity) |
| TM agent topology | Two-agent split parallel to `apd-code-recon`: tier-0 `apd-threat-model-recon` (parser/normalizer) + tier-4 `apd-threat-model-evaluator` (comparator) |
| Attack-path approach | BloodHound-style path enumeration over a partial graph with provenance + confidence on every node and edge; never-invent rule; bounded enumeration |
| Crown-jewel declaration | Domain pack declares defaults; run-config overrides; missing-crown-jewels → `disposition: blocked` (no guessing) |
| D3FEND placement | On capabilities (defensive techniques the design implements); also used as the overlay vocabulary for bottleneck edges in attack-path analysis |
| Evidence discipline | Existing high-confidence-only rule, block-on-ambiguity default, and never-invent rules extend unchanged to all new taxonomies and analyses |

## 3. Goals & non-goals

**Goals.**
- Make every finding/capability carry the framework IDs (CWE / OWASP / D3FEND) that match what the system under review actually exposes, in addition to the existing NIST 800-53r5 + ATT&CK mappings.
- When the operator supplies a threat model, evaluate it methodology-aware: surface coverage gaps (which STRIDE/LINDDUN categories are absent for which surfaces), contradictions (TM claim vs. specialist finding), and silences (TM mute where specialists found risk).
- When crown jewels are declared, enumerate plausible attack paths from declared attacker positions to crown jewels, identify bottleneck edges, and emit a D3FEND-tagged "highest-leverage defensive investments" view.
- Preserve evidence discipline end-to-end — every mapping, every TM evaluation finding, every attack-path finding must be evidence-grounded.
- Keep the framework backward-compatible: a v1.1 run with no run-config changes must continue to work unmodified, producing exactly the outputs it does today.
- Ship reference-data refresh scripts for the new taxonomies with the same security hardening already applied to `refresh_mitre.py` (60s timeout, 200 MiB cap, `source_sha256` in projected payload).

**Non-goals (this epic).**
- Native parsing for PASTA, VAST, Trike, or other narrative methodologies. Accepted as free-form prose with reduced extraction confidence; native support deferred.
- Active threat-model augmentation (the gauntlet inventing threats the user's TM should have included). The evaluator is comparator-only; never generates threats not grounded in specialist findings.
- Graph-database backing for the asset graph. In-memory graph; export to JSON/YAML; downstream tooling can ingest if desired.
- Interactive HTML attack-path visualization. Mermaid diagrams embedded in the markdown advisory report only.
- LLM-driven attack-path inference. Path enumeration is deterministic graph traversal over the asset graph; the LLM's role is to author edge provenance from artifact evidence during specialist runs, not to invent paths.
- GUI for declaring crown jewels or attacker positions. Declaration is via domain pack (`domain.yaml`) and/or run-config (`.apd-run.yaml`) text edits.
- Backwards-compatibility shims for the (currently empty) v2.x schema namespace. All changes additive within v1.x; v2.x reserved for future breaking change if needed.

## 4. Architecture

### 4.1 New gauntlet topology

Three new agents — all activation-gated so a minimum-viable v1.1-style run with no threat model, no taxonomies declared, and no crown jewels declared still produces identical output to today.

```
Tier 0 (intake)
  apd-intake                          [existing — enhanced]
  apd-code-recon          (optional)  [v1.1]
  apd-threat-model-recon  (optional)  [NEW — Track 2 parser/normalizer]
       │
       ▼
Tier 1 (Trustworthiness)
  apd-confidentiality · apd-integrity · apd-availability     [existing — gain new taxonomy fields]
Tier 2 (Scalability)
  apd-distributed · apd-resilient · apd-ephemeral            [existing — gain new taxonomy fields]
Tier 3 (Auditability)
  apd-authenticity · apd-non-repudiation · apd-immutability  [existing — gain new taxonomy fields]
       │
       ▼
Tier 4 (synthesis)
  apd-synthesizer              [existing — enhanced with new rollups]
  apd-threat-model-evaluator   [NEW — Track 2 comparator]
  apd-attack-path-analyzer     [NEW — Track 3 path enumeration + D3FEND defense overlay]
```

### 4.2 Internal phasing

Three phases, each ship-able independently. Each phase ships with full tests, docs, ADR, and CHANGELOG entry.

| Phase | Release | Scope |
|---|---|---|
| **A** | v1.2.0 | Track 1 — taxonomy mappings (CWE / OWASP / D3FEND), per-run scoping via `run-config`, intake auto-detect suggestions, new synthesizer rollups, three reference-data refresh scripts. Foundation that B and C cite. |
| **B** | v1.3.0 | Track 2 — `apd-threat-model-recon` + `apd-threat-model-evaluator` agents, methodology grammars (STRIDE, LINDDUN, attack-tree), two new schemas, methodology→APD-goal mapping skill, operator docs. |
| **C** | v1.4.0 | Track 3 — `apd-attack-path-analyzer` agent, asset/attack-path/defense-graph schemas, domain-pack additions (`crown_jewels[]` etc.), bounded path enumeration, D3FEND defensive overlay, Mermaid diagrams in advisory report. |

### 4.3 Schema evolution strategy

All schema changes additive. Existing v1.x schemas extend with **optional** fields only; new schemas introduced for new artifacts. No required field added to any existing schema. No enum value removed. The `framework_compat: ">=1.0.0,<2.0.0"` constraint in the PBM domain pack continues to accept v1.2.0, v1.3.0, and v1.4.0 without changes.

The only enum-extension changes are:
- `finding.schema.json#agent` — add `threat_model_evaluator`, `attack_path_analyzer`
- `finding.schema.json#id` pattern — relax to also accept `tmeval-[0-9a-f]{8}` and `apath-[0-9a-f]{8}` prefixes

These are additive (existing IDs still match the old pattern; existing agent values still validate). Older validators reading v1.2+ records they don't recognize the agent value for will reject — acceptable because operators must update the framework version to consume new-agent output anyway.

## 5. Track 1 — Multi-framework taxonomy mappings (Phase A, v1.2.0)

### 5.1 What gets mapped where

| Taxonomy | Attached to | Why |
|---|---|---|
| CWE | findings | Weakness in the design; developer-facing vocabulary |
| OWASP Top 10 (web) | findings | Web-app risk category; reviewer-facing |
| OWASP API Top 10 | findings | API-specific risk category |
| OWASP LLM Top 10 | findings | LLM-app risk category |
| MITRE D3FEND | **capabilities** | Defensive techniques the design *implements*; architect-facing |
| MITRE ATT&CK technique | findings (existing) | Adversary technique the finding enables |
| MITRE ATT&CK mitigation | capabilities (existing) | Defensive control the capability provides |
| NIST 800-53r5 | both (existing) | Required on every record |

D3FEND-on-capabilities completes the symmetry already established by ATT&CK (technique-on-findings, mitigation-on-capabilities).

### 5.2 Schema additions

**`finding.schema.json`** — extend `control_mappings` block with optional sibling arrays:

```jsonc
{
  "control_mappings": {
    "nist_800_53r5":     [...],           // existing, required
    "mitre_attack":      [...],           // existing, optional
    "cwe":               ["CWE-79", ...], // NEW, optional
    "owasp_top10":       ["A03:2021", ...], // NEW, optional
    "owasp_api_top10":   ["API3:2023", ...], // NEW, optional
    "owasp_llm_top10":   ["LLM01", ...]   // NEW, optional
  }
}
```

Each new array's items follow a strict regex (e.g., `^CWE-[0-9]+$`, `^A[0-9]{2}:20[0-9]{2}$`).

**`capability.schema.json`** — extend `control_mappings` block with:

```jsonc
{
  "control_mappings": {
    "nist_800_53r5":   [...],           // existing
    "mitre_attack":    [...],           // existing (mitigations)
    "d3fend":          [                // NEW, optional
      {
        "technique":         "D3-NTA",
        "counters_attack":   ["T1078"],
        "rationale":         "..."
      }
    ]
  }
}
```

D3FEND entries require `counters_attack` — every D3FEND mapping must cite which ATT&CK technique(s) it counters from the same record's `mitre_attack` block. This prevents D3FEND-by-name-similarity mappings.

**`run-config.schema.json`** — extend with:

```yaml
taxonomies:
  - cwe              # default-on
  - mitre_attack     # default-on
  - d3fend           # default-on
  - owasp_top10      # opt-in
  - owasp_api_top10  # opt-in
  - owasp_llm_top10  # opt-in
```

**New schemas (synthesizer rollups), analogous to `attack-exposure.schema.json`:**

- `cwe-coverage.schema.json` — CWE IDs grouped by Pillar/Class/Base with finding count per ID.
- `owasp-coverage.schema.json` — three sub-rollups (Top 10, API Top 10, LLM Top 10); per category: findings present, findings silent, surfaces affected.
- `d3fend-coverage.schema.json` — D3FEND tactic/technique tree with capability backing; counter-coverage view (which exposed ATT&CK techniques have D3FEND-backed capabilities vs. which don't — feeds Track 3 bottleneck analysis).

### 5.3 Discipline rules (extended via `apd-control-mappings` skill)

The existing high-confidence-only and rationale-required rules apply unchanged to all new taxonomies. Per-taxonomy additions:

- **CWE.** Map only when the finding describes a specific weakness pattern that matches a CWE entry's *Demonstrative Examples* or *Observed Examples*. Use **base or variant** entries (CWE-79 OK, CWE-693 category-level not OK — too abstract for actionable mapping). Each CWE mapping requires a `rationale` field explaining the weakness pattern match.
- **OWASP Top 10 (Web).** Gated on `owasp_top10` being declared in `run-config`. Intake auto-suggests addition when it detects web routes, HTML templates, or HTTP-facing components in supplied artifacts. Use current edition format (e.g., A01:2021); rotate when OWASP publishes new editions.
- **OWASP API Top 10.** Same gating pattern. Auto-suggest on API gateway configs, OpenAPI/Swagger specs, or REST/GraphQL endpoint declarations.
- **OWASP LLM Top 10.** Same gating pattern. Auto-suggest on LLM SDK imports (`openai`, `anthropic`, `langchain`, etc.), prompt template files, or vector store usage.
- **D3FEND.** Capability must *actually implement* the technique; never map by name similarity. Each D3FEND mapping requires both a `rationale` and the `counters_attack` cross-reference. D3FEND-without-corresponding-ATT&CK on the same record is a schema validation error.

### 5.4 Intake auto-detect

Intake examines supplied artifacts during context-briefing and writes a `taxonomy_suggestions:` block into the context brief:

```yaml
taxonomy_suggestions:
  declared_in_run_config: [cwe, mitre_attack, d3fend]
  suggested_additional:
    - taxonomy: owasp_api_top10
      reason: "OpenAPI spec detected at artifacts/api/openapi.yaml; REST endpoints declared"
    - taxonomy: owasp_llm_top10
      reason: "anthropic SDK import detected in code-evidence-index"
```

The operator can then re-run with `apd-gauntlet init-run ... --taxonomies cwe,mitre_attack,d3fend,owasp_api_top10,owasp_llm_top10` to incorporate suggestions. Specialists never act on suggestions that weren't accepted into the run-config; this preserves operator authority over scope.

### 5.5 Reference-data refresh

Three new scripts mirroring `refresh_mitre.py` with the v1.0 security-review hardening:

- `tools/apd_gauntlet/refresh_cwe.py` — fetches MITRE CWE XML; projects to JSON (id, name, abstraction, parents, demonstrative_examples_present, observed_examples_present). Stored at `tools/apd_gauntlet/reference_data/cwe.json` with `source_sha256` and `fetched_at`.
- `tools/apd_gauntlet/refresh_owasp.py` — fetches three GitHub-hosted JSONs (Top 10, API Top 10, LLM Top 10) with edition versioning preserved (a finding mapped to A03:2021 stays A03:2021 even after A03:2024 ships).
- `tools/apd_gauntlet/refresh_d3fend.py` — fetches D3FEND OWL/JSON-LD; projects to a tactic/technique tree with ATT&CK counter-mappings preserved.

All apply: `timeout=60s`, `max_response_size=200 MiB`, `source_sha256` in projected payload, no shell-injectable inputs.

CLI: new subcommands `apd-gauntlet refresh-cwe`, `apd-gauntlet refresh-owasp`, `apd-gauntlet refresh-d3fend`.

## 6. Track 2 — Methodology-aware threat-model evaluation (Phase B, v1.3.0)

### 6.1 Two-agent split (parallel to `apd-code-recon`)

- **`apd-threat-model-recon`** — tier-0, optional. Activated when `.apd-run.yaml` declares `threat_model: <path>` or intake detects a TM-like artifact. Parses the threat model into a normalized graph; emits `00-context/threat-model-normalized.yaml`. **Does not emit findings.** Pure context-builder.
- **`apd-threat-model-evaluator`** — tier-4. Activated when `00-context/threat-model-normalized.yaml` exists. Consumes normalized graph + all specialist findings + all capabilities. Emits findings + `40-synthesis/threat-model-coverage-report.md`.

### 6.2 Input format support (v1)

| Format | Native parsing | Notes |
|---|---|---|
| OWASP Threat Dragon JSON | yes | Methodology, components, threats — fully structured |
| Microsoft TMT `.tm7` | yes | XML; well-understood schema |
| STRIDE-per-element Markdown/CSV tables | yes | Column headers `S T R I D E`, rows = components |
| Attack tree (indented prose, ADTool XML, JSON) | yes | Tree structure preserved; AND/OR semantics |
| LINDDUN tables (Markdown/CSV) | yes | Same shape as STRIDE-per-element with LINDDUN columns |
| PASTA / VAST / Trike / other narrative | reduced-fidelity | Extraction confidence noted; `methodology: free_form` |
| Free-form prose (any) | reduced-fidelity | Same as above |

### 6.3 Normalized graph schema (`threat-model-normalized.schema.json`)

Each entry:

```yaml
- entry_id:                tm-<sha8>
  asset:                   "<asset name from TM>"
  threat:                  "<threat name from TM>"
  mitigation:              "<mitigation listed in TM or null>"
  methodology:             stride | linddun | attack_tree | free_form | unknown
  source_locator:          "<file>#<location>"
  extraction_confidence:   high | medium | low
  framework_refs:
    stride_letter:         S | T | R | I | D | E | null
    linddun_letter:        L | I | N | D | D | U | N | null
    attack_tree_position:  "<root>/<child>/<leaf>" | null
    mitre_attack:          [T0000, ...]   # only if attack-tree leaf maps cleanly
  inferred_apd_goals:      [confidentiality, integrity, ...]
```

### 6.4 Methodology → APD-goal mapping (canonical, in `apd-threat-model-methodologies` skill)

| Methodology | Category | APD goal(s) |
|---|---|---|
| STRIDE | S — Spoofing | Authenticity |
| STRIDE | T — Tampering | Integrity |
| STRIDE | R — Repudiation | Non-Repudiation |
| STRIDE | I — Information Disclosure | Confidentiality |
| STRIDE | D — Denial of Service | Availability |
| STRIDE | E — Elevation of Privilege | Authenticity + Integrity |
| LINDDUN | L — Linkability | Confidentiality |
| LINDDUN | I — Identifiability | Confidentiality |
| LINDDUN | N — Non-repudiation (privacy harm) | Non-Repudiation |
| LINDDUN | D — Detectability | Confidentiality |
| LINDDUN | D — Disclosure of information | Confidentiality |
| LINDDUN | U — Unawareness (consent) | Authenticity |
| LINDDUN | N — Non-compliance | Domain-specific (e.g., HIPAA-mapped for PBM) |
| Attack tree | leaf | ATT&CK technique mapping when achievable; otherwise inherited from parent |
| Attack tree | intermediate | union of child APD goal coverage |

### 6.5 Evaluator outputs

Three finding flavors, all using existing `finding.schema.json` with `agent: threat_model_evaluator` and id prefix `tmeval-`:

- **Coverage gap** (`disposition: gap`) — a methodology category is absent for a surface that should have it. *"TM has no Repudiation analysis for the audit-log surface."* Only fires when a specialist finding shows the gap is real (i.e., Non-Repudiation specialist flagged something on that surface).
- **Contradiction** (`disposition: risk`) — TM claim conflicts with a specialist finding. *"TM asserts PHI is encrypted in transit between adjudication-service and pricing-service (mitigation entry tm-a1b2c3d4); `conf-9e8d7c6b` shows plaintext on that path."* Includes both the TM entry ID and the contradicting finding ID in `cross_references`.
- **Silence** (`disposition: uncertainty`) — TM is mute on a surface specialists flagged as risky. *"TM does not address the new vendor API integration that `auth-5d4c3b2a` flagged for weak mTLS."*

### 6.6 Discipline rules (`apd-threat-model-methodologies` skill)

- **Never invent threats the TM should have included.** Coverage-gap findings only fire when a specialist finding shows the gap is real.
- **Never re-derive STRIDE/LINDDUN coverage from scratch.** Only evaluate what the TM author actually wrote.
- **Free-form prose extraction records confidence.** Low-confidence extractions (`extraction_confidence: low`) cannot drive contradiction findings — only `uncertainty` findings.
- **Block-on-ambiguity extends here.** If the TM format isn't parseable and prose extraction confidence is below threshold for the whole document, emit `disposition: blocked` with `prerequisite_evidence: ["normalized threat model in supported format"]` and skip evaluation.

### 6.7 Schema additions

- `finding.schema.json` — extend `agent` enum with `threat_model_evaluator`; relax `id` pattern to accept `tmeval-[0-9a-f]{8}`.
- New: `threat-model-normalized.schema.json` (§6.3).
- New: `threat-model-coverage.schema.json` — per-surface coverage matrix vs. methodology categories + summary statistics.
- `run-config.schema.json` — extend with optional `threat_model: <path>` and `methodology_hint: <name>` fields. `methodology_hint` lets the operator nudge ambiguous TM documents toward a specific parser.

### 6.8 New templates

- `templates/threat-model-normalized.template.md` — narrative briefing the operator on what the recon agent extracted, including extraction confidence flags.
- `templates/threat-model-coverage-report.template.md` — synthesizer-format report covering: per-surface coverage matrix, contradiction list, silence list, methodology summary statistics.

## 7. Track 3 — Asset graph + attack-path enumeration + D3FEND defense overlay (Phase C, v1.4.0)

### 7.1 Critical framing

BloodHound works on Active Directory because every node and edge is queryable from authoritative APIs. The gauntlet sees human-authored artifacts — incomplete, ambiguous, sometimes contradictory. The analyzer therefore operates on a **partial graph** and must remain honest about that: every node and edge carries provenance and confidence, and every enumerated path is annotated with the assumptions it requires. The output is never "the attack paths"; it's "the attack paths *that the supplied artifacts support, given declared crown jewels and attacker positions, with these confidence floors*."

### 7.2 One new agent: `apd-attack-path-analyzer` (tier-4)

Runs after `apd-synthesizer` completes (needs dedup'd findings and capabilities). Activation-gated on crown jewels being declared (domain-pack default + optional run-config override). Inputs:

- Intake brief (asset inventory, trust boundaries, identity model if present)
- All findings (each is a potential `compromisable_via_finding` edge)
- All capabilities (each is a potential `mitigated_by_capability` edge that subtracts)
- `00-context/threat-model-normalized.yaml` if present (TM-declared attacker vectors become declared edges with `provenance: threat_model`)
- `00-context/code-evidence-index.yaml` if present (cross-service call graph informs `network_reachable` edges)
- Domain pack: `crown_jewels[]`, `attacker_positions[]`, `default_trust_boundaries[]`
- Run-config overrides for crown jewels and attacker positions

### 7.3 Graph model

**Node types** — each with `provenance` (artifact citation or domain-pack default) and `confidence` (high / medium / low):

- `asset` — services, data stores, secrets, queues, networks
- `identity` — human role, service account, workload identity
- `attacker_position` — external internet, compromised vendor, compromised employee, insider, compromised dev workstation, supply chain (declared per domain)
- `crown_jewel` — declared per domain pack, overridable per run

**Edge types** — each with `provenance`, `confidence`, and `traversal_cost`:

- `network_reachable` — declared in IaC/architecture artifacts
- `authn_required` — auth contract declared
- `authz_grants` — RBAC/policy declared
- `data_resides_on` — from intake's data inventory
- `trusts` — cross-boundary trust declaration
- `compromisable_via_finding` — a specific gauntlet finding describes attacker traversal; links to finding ID
- `mitigated_by_capability` — capability subtracts the edge from the compromisable set; links to capability ID

### 7.4 Path enumeration algorithm

Deterministic graph traversal. For each `(attacker_position, crown_jewel)` pair, find paths bounded by:

- `max_hop = 8` (configurable per-run; cap at 12)
- `max_paths_per_pair = 50` (configurable per-run; cap at 200)

Path metadata:

- `feasibility = min(edge_confidence along path)`
- `severity = max(finding_severity along compromisable_via_finding edges)`
- `mitigated = capabilities encountered on the path` (subtracts from feasibility)
- `bottleneck_edges = edges shared with N or more other enumerated paths` (threshold configurable, default N=5)

Path enumeration is bounded → tractable for SUTs of reasonable scale. For very complex SUTs the analyzer summarizes ("100+ paths share this bottleneck edge") rather than dumping all paths.

### 7.5 D3FEND defense overlay

For each bottleneck edge:

1. Identify the underlying `compromisable_via_finding` (the finding that creates the edge)
2. Pull the finding's `mitre_attack` block (from Track 1 mapping)
3. Look up D3FEND techniques that counter those ATT&CK techniques (from `d3fend.json` reference data)
4. Note which D3FEND techniques are *already* implemented by capabilities elsewhere in the graph vs. which would be net-new investments

Surface as **"highest-leverage defensive investments"** in the attack-path report: actionable architecture guidance keyed to D3FEND vocabulary.

### 7.6 Findings the analyzer emits

All use `agent: attack_path_analyzer` and id prefix `apath-`:

- **High-feasibility path with no capability coverage** (`disposition: risk`, `severity: critical|high`) — path from declared attacker position to crown jewel exists with no mitigating capability on any edge.
- **Path with low-confidence edges** (`disposition: uncertainty`) — paths whose feasibility floor is low cap at uncertainty; never escalate to risk on weak provenance.
- **Bottleneck edge without D3FEND-backed capability** (`disposition: gap`) — bottleneck edge exists; D3FEND counters available; no capability in the design implements any of them.
- **No crown jewels declared** (`disposition: blocked`, `prerequisite_evidence: ["domain pack or run-config must declare crown jewels"]`) — analyzer skips enumeration entirely.

### 7.7 Discipline rules (`apd-attack-path-discipline` skill)

- **Never invent nodes.** Every node cites an artifact, intake's asset inventory, or a domain-pack default. Invented nodes are evidence-discipline violations.
- **Never invent edges.** Every edge is declared (architecture/IaC/threat model), inferred from a specific finding (with finding ID), or a domain-pack default trust pattern.
- **Bounded enumeration; honest output.** Hop and count caps explicit in output; never claim "all paths" — output always says "top-N paths under K hops."
- **Confidence floors severity.** Low-confidence paths cap at `uncertainty`; never escalate to `risk` or `gap` on weak provenance.
- **Block-on-missing-crown-jewels.** No declared targets → no enumeration. Don't guess. (PBM domain pack will ship sensible defaults: PHI stores, PDE submission pipeline, claim adjudication engine.)
- **Mermaid diagram cap.** Diagrams cap at 50 nodes for readability; larger graphs render as multiple sub-diagrams partitioned by attacker position.

### 7.8 Schema additions

- `finding.schema.json` — extend `agent` enum with `attack_path_analyzer`; relax `id` pattern to accept `apath-[0-9a-f]{8}`.
- New: `asset-graph.schema.json` — nodes + edges with provenance and confidence.
- New: `attack-path.schema.json` — enumerated path record (sequence of edges, feasibility, severity, mitigation, bottleneck membership).
- New: `defense-graph.schema.json` — D3FEND overlay on bottleneck edges with capability backing.
- `domain.schema.json` — extend with optional `crown_jewels[]`, `attacker_positions[]`, `default_trust_boundaries[]`.
- `run-config.schema.json` — extend with optional `crown_jewels[]` (override list) and `attacker_positions[]` (override list).

### 7.9 Outputs

- `40-synthesis/asset-graph.yaml` — full node/edge graph with provenance
- `40-synthesis/attack-paths.yaml` — top-N paths per (attacker, crown-jewel) pair
- `40-synthesis/defense-graph.yaml` — D3FEND overlay on bottleneck edges
- `40-synthesis/attack-path-report.md` — narrative report with Mermaid diagrams (≤50 nodes per diagram)
- Findings appended to specialist outputs that the synthesizer already aggregates

### 7.10 PBM domain pack additions (proves the abstraction)

```yaml
# domains/pbm/domain.yaml additions
crown_jewels:
  - pattern:       "phi_store"
    description:   "Any data store holding PHI (member records, claim history, prescription history)"
  - pattern:       "pde_submission_pipeline"
    description:   "CMS Part D Prescription Drug Event submission pipeline"
  - pattern:       "claim_adjudication_engine"
    description:   "Core adjudication decision system; integrity affects payment correctness"

attacker_positions:
  - position:      "external_internet"
    description:   "Unauthenticated network attacker"
  - position:      "compromised_pharmacy_credential"
    description:   "Attacker has stolen credentials of a legitimate pharmacy submitter"
  - position:      "compromised_vendor_integration"
    description:   "Compromise of upstream vendor (drug pricing data, clinical rules)"
  - position:      "insider_with_member_service_role"
    description:   "Authorized member-services agent acting maliciously"
  - position:      "compromised_dev_workstation"
    description:   "Engineering workstation with elevated cluster access"

default_trust_boundaries:
  - boundary:      "pharmacy_submission_ingress"
    description:   "External pharmacy systems → internal claim intake"
  - boundary:      "member_portal_ingress"
    description:   "Plan member browser → member-services API"
  - boundary:      "internal_to_pde_submission"
    description:   "Internal adjudication → CMS-bound PDE submission"
```

## 8. Skills inventory after this epic

| Skill | Status | Purpose |
|---|---|---|
| `apd-framework` | unchanged | Three tiers, nine goals, boundary calls |
| `apd-evidence-discipline` | unchanged | Evidence-pointer rule, block-on-ambiguity, never-invent (extends to new agents implicitly) |
| `apd-finding-schema` | minor update | Document new agent enum values and id prefixes |
| `apd-control-mappings` | major update | Add per-taxonomy discipline sections for CWE / OWASP / D3FEND |
| `apd-domain` | minor update | Document new domain-pack fields |
| `apd-threat-model-methodologies` | **NEW** | STRIDE/LINDDUN/attack-tree grammars, methodology→APD-goal mappings, parsing patterns, discipline rules |
| `apd-attack-path-discipline` | **NEW** | Node/edge provenance rules, never-invent rules, confidence propagation, bounded enumeration, block-on-missing-crown-jewels |

## 9. Testing strategy

TDD-first per project convention. Preserve the existing 85% coverage gate; target 90%+ on the new modules.

### 9.1 Schema validation tests
Every new schema gets a validator + valid/invalid fixtures. Roughly six new schemas → twelve new test files.

### 9.2 Methodology parser tests (Track 2)
Fixtures covering each supported format:

- Threat Dragon JSON (with all six STRIDE letters represented across multiple components)
- Microsoft TMT `.tm7` XML
- STRIDE-per-element Markdown tables
- STRIDE-per-element CSV
- Attack tree as indented prose
- Attack tree as ADTool XML
- LINDDUN Markdown tables
- Free-form prose at varying complexity (high/medium/low extraction confidence)
- Malformed inputs → expected `disposition: blocked` outputs

### 9.3 Mapping discipline tests
Assert STRIDE→APD-goal and LINDDUN→APD-goal mapping tables in `apd-threat-model-methodologies` skill match a canonical Python constant — single source of truth, prevents drift.

### 9.4 Path-enumeration unit tests (Track 3)

- Bounded depth honored
- Path dedup correct
- Ordering by feasibility / severity correct
- Confidence propagation (path feasibility = min edge confidence)
- Capability subtraction (capabilities along path reduce feasibility)
- No-crown-jewels → `disposition: blocked`
- Mermaid output never exceeds 50 nodes per diagram
- Path-count caps honored

### 9.5 Integration test
Extend `examples/apd-20260601-claim-event-bus/` with:

- A Threat Dragon JSON threat model covering the claim event bus
- Run-config declaring `taxonomies: [cwe, mitre_attack, d3fend, owasp_api_top10]` and `crown_jewels: [phi_store, pde_submission_pipeline]`

Ship Phase A/B/C outputs as new expected golden artifacts. The validator's `apd-gauntlet validate examples/.../expected/` continues to pass.

### 9.6 Expected test growth

| Phase | New tests (approx) |
|---|---|
| A | 15 (schemas + mapping discipline + intake auto-detect + refresh scripts) |
| B | 25 (methodology parsers across formats + evaluator output flavors + new schemas) |
| C | 20 (graph model + enumeration + D3FEND overlay + new schemas) |
| **Total** | **~60** (today: 114 → ~174 after Phase C) |

## 10. Documentation

### 10.1 New pages

- `docs/threat-modeling.md` — Track 2 operator guide. Supported formats, methodology hints, what the evaluator emits, how to read coverage reports, common pitfalls.
- `docs/attack-path-analysis.md` — Track 3 operator guide. Declaring crown jewels, attacker positions, trust boundaries; reading the asset graph, attack-path, and defense-graph outputs; interpreting Mermaid diagrams.
- `docs/taxonomy-mappings.md` — Track 1 operator guide. Which taxonomies, when to enable them, how to interpret coverage rollups, reference-data refresh cadence.

### 10.2 Updated pages

- `docs/architecture.md` — topology diagram with three new agents; output-files tree updated with new artifacts.
- `docs/running-the-gauntlet.md` — new run-config fields, new CLI flags, three-phase opt-in narrative.
- `docs/adapting-to-other-domains.md` — new domain-pack fields (`crown_jewels[]`, `attacker_positions[]`, `default_trust_boundaries[]`) with worked examples.
- `docs/schema-evolution.md` — v1.2 / v1.3 / v1.4 additive cadence documented as the versioning model for this epic.
- `docs/extending-agents.md` — pattern for activation-gated optional agents (already established by `apd-code-recon`, now reinforced by three more).

## 11. Architecture Decision Records

Three new ADRs, using the harmonized 0001–0006 format (hyphen+colon style). Opportunistically harmonize ADR 0007 to match.

- **ADR 0008 — Multi-framework taxonomy mappings.** Why per-run scoping (vs. domain-pack-only or always-on). Why D3FEND attaches to capabilities only (symmetry with ATT&CK). Why CWE/ATT&CK/D3FEND default-on but OWASP variants opt-in. Why D3FEND mappings require `counters_attack` cross-reference.
- **ADR 0009 — Methodology-aware threat-model evaluator.** Why two-agent split (tier-0 recon + tier-4 evaluator) mirrors `apd-code-recon`. Why STRIDE/LINDDUN/attack-tree are v1 methodologies. Why never-invent rule (the evaluator is a comparator, not a threat generator). Why free-form prose gets reduced fidelity rather than no support.
- **ADR 0010 — Attack-path analysis on partial graphs.** Why BloodHound-style enumeration is valid only with explicit provenance + confidence per node/edge. Why crown jewels must be declared (no guessing). Why bounded enumeration. Why D3FEND overlay surfaces bottlenecks (highest defensive leverage).

## 12. CLI changes (`apd-gauntlet`)

| Subcommand | Change |
|---|---|
| `init-run` | Accept `--threat-model <path>`, `--methodology-hint <name>`, `--taxonomies <comma-list>`, `--crown-jewels <comma-list>`, `--attacker-positions <comma-list>` |
| `validate` | Validate new optional artifacts when present; pass when absent |
| `validate-domain` | Validate new optional `crown_jewels[]`, `attacker_positions[]`, `default_trust_boundaries[]` fields |
| `validate-run-config` | Validate new optional `threat_model`, `methodology_hint`, `taxonomies`, `crown_jewels`, `attacker_positions` fields |
| `lint-agents` | Validate the three new agents (frontmatter, activation contract, lens scoping) |
| `refresh-cwe` | **NEW.** Fetch + project CWE reference data (timeout=60s, max=200 MiB, source_sha256). |
| `refresh-owasp` | **NEW.** Fetch + project all three OWASP Top 10 reference data. |
| `refresh-d3fend` | **NEW.** Fetch + project D3FEND reference data. |

## 13. CHANGELOG

Three placeholder entries (release dates pending tag):

```markdown
## [1.4.0] - 2026-XX-XX
### Added
- Attack-path analyzer agent with BloodHound-style enumeration over a partial graph
- Asset graph + attack-paths + defense-graph schemas
- D3FEND defensive overlay on bottleneck edges with capability backing
- Domain-pack additions: crown_jewels, attacker_positions, default_trust_boundaries
- Mermaid attack-path diagrams in advisory report
- ADR 0010
- apd-attack-path-discipline skill

## [1.3.0] - 2026-XX-XX
### Added
- Methodology-aware threat-model evaluator (STRIDE, LINDDUN, attack-tree native; PASTA/VAST/Trike/free-form reduced-fidelity)
- apd-threat-model-recon (tier-0) + apd-threat-model-evaluator (tier-4) agents
- threat-model-normalized + threat-model-coverage schemas
- apd-threat-model-methodologies skill
- ADR 0009

## [1.2.0] - 2026-XX-XX
### Added
- Multi-framework taxonomy mappings: CWE, OWASP Top 10/API/LLM, MITRE D3FEND
- Per-run taxonomy scoping with intake auto-detect suggestions
- cwe-coverage, owasp-coverage, d3fend-coverage synthesizer rollup schemas
- refresh-cwe, refresh-owasp, refresh-d3fend CLI subcommands (with v1.0 security hardening)
- ADR 0008
```

## 14. Backward compatibility & migration

- **Pre-existing runs continue to work unchanged.** A v1.1-style `.apd-run.yaml` with no `taxonomies`, no `threat_model`, no `crown_jewels` produces identical output to today (modulo CHANGELOG version stamp).
- **No required-field additions** on any existing schema. Validators reading v1.2+ records from v1.x agents will pass.
- **PBM domain pack stays valid** with `framework_compat: ">=1.0.0,<2.0.0"` — no domain-pack format change required to consume Phase A or B; Phase C consumes the new optional domain-pack fields if present, ignores them gracefully if not.
- **Older validators** reading v1.2+ records they don't recognize agent values for (e.g., `threat_model_evaluator`) will reject — acceptable because operators must update the framework version to consume new-agent output anyway.
- **`framework_version` default in CLI** bumps with each phase (1.2.0, 1.3.0, 1.4.0).

## 15. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Methodology parsers brittle on real-world TM formats | Comprehensive fixture coverage in `tests/`; extraction-confidence field surfaces parser uncertainty rather than silently producing wrong normalized graph |
| Attack-path enumeration blows up on large SUTs | Bounded hop count + path count per pair; summarization for very large graphs; degraded-but-honest output preferred over silent truncation |
| D3FEND counter-mappings inaccurate | Discipline rule: D3FEND requires `counters_attack` cross-reference and `rationale`; mapping derived from MITRE D3FEND's own attack-counter tables, not inferred |
| Operator over-declares taxonomies (e.g., declares `owasp_llm_top10` on a non-LLM system) | Intake auto-detect *cannot* be overridden by operator declarations on the negative side — if operator declares `owasp_llm_top10` and intake finds no LLM surface, intake emits a warning in the context brief; specialists still attempt mapping but with low confidence |
| BloodHound-style output looks authoritative despite partial-graph caveat | Every path output includes `feasibility`, list of assumptions (provenance), and explicit "bounded at N hops, M paths" disclosure; report template emphasizes this in standard language |
| Three new agents inflate context budget | Agents are activation-gated; minimum-viable run unchanged; full-fat run with all three new agents is opt-in, and operators who can't afford the context budget simply don't declare the inputs |
| ATT&CK / CWE / OWASP / D3FEND reference data goes stale | `refresh-*` subcommands; documented operator refresh cadence (quarterly) in `docs/taxonomy-mappings.md` |
| Threat-model evaluator emits findings that overlap with specialist findings | Synthesizer's existing dedup/merge/link/separate clustering applies; TM contradiction findings explicitly cite the specialist finding ID in `cross_references` so the linkage is preserved through clustering |

## 16. Open questions

None blocking. The following may surface during implementation planning:

- Whether `apd-threat-model-evaluator` should be combinable with `apd-attack-path-analyzer` outputs in a single synthesis-tier pass (Phase C consideration; not blocking Phase B).
- Whether the `attack-path-report.md` template should embed full Mermaid diagrams inline vs. linking to side-car `.mmd` files (rendering performance question; not blocking design).
- Whether reference-data refresh should be a CI job (weekly) vs. operator-driven only (the v1.0 security review hardening was operator-driven; CI scheduling deferred to a separate ops decision).

## 17. Implementation sequencing summary

1. **Phase A (v1.2.0)** — Track 1. Schemas + skill updates + intake auto-detect + three refresh scripts + three coverage rollups + ADR 0008 + CHANGELOG entry. Most mechanical of the three; lowest risk.
2. **Phase B (v1.3.0)** — Track 2. Two new agents + two new schemas + methodology grammars + new skill + new templates + operator doc + ADR 0009. Depends on Phase A taxonomies for evaluator output mapping.
3. **Phase C (v1.4.0)** — Track 3. One new agent + three new schemas + domain-pack extensions + path-enumeration logic + D3FEND overlay + new skill + Mermaid rendering + operator doc + ADR 0010. Depends on Phase A (D3FEND mappings on capabilities) and benefits from Phase B (TM-declared attack vectors as edge provenance).

Each phase culminates in: full test suite green, coverage gate met, validator clean on the extended sample run, docs updated, ADR landed, CHANGELOG entry filled in, tag-ready.
