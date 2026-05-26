# ADR-0008: Multi-Framework Taxonomy Mappings

**Status:** Accepted
**Date:** 2026-05-25

## Context

APD Gauntlet through v1.1 maps findings and capabilities to NIST 800-53r5 and (high-confidence-only) MITRE ATT&CK. The output is rigorous but speaks the APD taxonomy fluently; reviewers who know CWE, OWASP, or D3FEND but not APD lose information in translation. Practitioners' default frameworks vary by role — developers reach for CWE, application reviewers for OWASP Top 10, API reviewers for OWASP API Top 10, AI-app reviewers for OWASP LLM Top 10, defensive architects for D3FEND. Extending the gauntlet's vocabulary to these frameworks broadens the audience for its output without changing the underlying lens-driven analysis.

## Decision

Findings carry optional CWE, OWASP Top 10 (web / API / LLM) mappings inside `control_mappings`. Capabilities carry optional D3FEND mappings inside `control_mappings`. All additions are schema-optional; v1.1-format records continue to validate against the v1.2 schemas unchanged.

Capabilities now also carry an optional `mitre_attack` block (parallel to the one on findings) that documents which ATT&CK techniques the capability defends against. This supports the D3FEND `counters_attack` cross-reference rule: every D3FEND mapping must cite the ATT&CK technique(s) it counters via `counters_attack`, and those technique(s) must also appear in the same capability's `mitre_attack[].technique` list (with sub-technique parent matching — T1110.001 is satisfied by T1110). This prevents D3FEND-by-name-similarity mappings.

D3FEND on capabilities is the symmetric complement of the existing split: ATT&CK techniques attach to findings (the adversary technique the finding enables), ATT&CK mitigations and now D3FEND attach to capabilities (the defensive techniques the capability provides). Capability identifiers use the existing `<agent_prefix>-cap-<hex8>` pattern.

Per-run scoping (`taxonomies: [...]` in `.apd-run.yaml`) controls which taxonomies are in scope. CWE, ATT&CK, and D3FEND are default-on; OWASP variants are opt-in (each scoped to a specific surface — web / API / LLM — that not every SUT exposes). Intake auto-detects relevant surfaces and writes a `taxonomy_suggestions:` block into the context brief, but specialists are bound only by the operator-accepted scope.

## Consequences

- Schema additions are fully additive within v1.x — no breaking changes. PBM domain pack consumes v1.2.0 without modification.
- Capability schema gained `mitre_attack` field (parallel to finding's) to support the D3FEND cross-reference rule.
- Synthesizer emits three new rollup artifacts (`cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`) when relevant.
- Three new reference-data refresh scripts (`refresh-cwe`, `refresh-owasp`, `refresh-d3fend`) require operator-driven refresh; documented cadence is quarterly.
- D3FEND `counters_attack` cross-reference rule (with sub-technique parent matching) prevents shotgun D3FEND mapping.
- D3FEND ID pattern accommodates 2-to-7-letter short codes (real MITRE D3FEND data contains codes up to 7 letters: D3-PHDURA, D3-DNSTA, etc.).
- Reference data shipped at `tools/apd_gauntlet/data/{cwe,owasp_top10,owasp_api_top10,owasp_llm_top10,d3fend}.json`. Live-fetched at v1.2.0: 969 CWEs, 30 OWASP categories (3 lists × 10), 149 D3FEND techniques with 3234 counter relations. OWASP data is currently seed-only because OWASP project URLs returned 404 at v1.2.0 ship time.

## Alternatives considered

- **Domain pack declares the taxonomies.** Rejected — would tie taxonomy scope to domain (PBM declares OWASP because healthcare apps usually have web/API surface) rather than to the SUT under review. A PBM SUT with an LLM-bearing surface would need a PBM domain update to pull in OWASP LLM. Per-run scoping is more flexible.
- **Always-on core taxonomies.** Rejected — agents would over-map (emit OWASP Top 10 tags on backend-only systems because it "kind of fits"), diluting signal.
- **Auto-detect only, no declared scope.** Rejected — opaque to reviewers ("why was OWASP API mapped on this finding?"). The declared-scope + auto-detect-suggestion split preserves operator authority.
- **Drop the cross-reference requirement; treat `counters_attack` as informational.** Rejected — would weaken D3FEND discipline by allowing capabilities to claim D3FEND mappings that don't relate to any technique the capability actually defends against. The cross-reference rule (with sub-technique parent matching for usability) keeps the mappings grounded.
