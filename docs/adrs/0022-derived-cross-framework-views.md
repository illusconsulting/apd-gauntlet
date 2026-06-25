# ADR-0022: Derived Cross-Framework Views (Bridges, Overlays, Projections) Are Synthesis-Authored, Not Specialist-Emitted

**Status:** Accepted
**Date:** 2026-06-14
**Implemented:** PR #110
**Complements:** [ADR-0008](0008-multi-framework-taxonomy-mappings.md) (multi-framework taxonomy mappings — the *emission* class this sits beside)
**Shares philosophy with:** [ADR-0020](0020-tooling-authored-derived-fields.md) (derive deterministically; never ask the LLM to author what is a pure function of existing content)

## Context

Every taxonomy the gauntlet speaks today is **specialist-emitted**. A specialist writes a mapping ID into a record's `control_mappings` block under the discipline in the `apd-control-mappings` skill:

- weakness / adversary side, on findings — `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`, `mitre_attack` (technique), `atlas`, `maswe`;
- defensive side, on capabilities — `nist_800_53r5` (required), `mitre_attack_mitigations`, `d3fend`, `masvs`.

Adding a new framework by this mechanism (per [ADR-0008](0008-multi-framework-taxonomy-mappings.md) / [ADR-0012](0012-mitre-atlas-finding-taxonomy.md) / [ADR-0014](0014-owasp-mas-mobile-taxonomy.md)) means: a new `control_mappings` key, a new `run-config` `taxonomies` enum value, a new section of specialist discipline, and a per-mapping high-confidence bar the specialist must clear. That cost is justified when the mapping is a **judgment** — when only a human-style reading of the architecture decides whether `CWE-79` applies.

But a large and growing set of valuable cross-framework relationships are **not judgments** — they are already authoritatively defined by external bodies, as machine-readable data:

- **MITRE CAPEC** links CWE weaknesses ↔ ATT&CK techniques (each CAPEC carries `Related_Weaknesses` and an ATT&CK `Taxonomy_Mapping`).
- **ATT&CK** (enterprise STIX) links each technique ↔ the **data components** required to detect it.
- **NIST** publishes 800-53r5 ↔ HIPAA Security Rule (SP 800-66r2) and 800-53r5 ↔ CSF 2.0 (CPRT/OLIR) crosswalks as JSON/XLSX.

Re-asking a specialist to author these is wasteful and *less* defensible than citing the authority directly: the specialist would be reconstructing, by hand and under a confidence bar, a relationship MITRE/NIST already publish. It also re-introduces the shotgun-mapping risk [ADR-0008](0008-multi-framework-taxonomy-mappings.md) deliberately fenced off ("always-on core taxonomies — rejected; agents would over-map").

The gauntlet already has the right home for authoritative, derived facts: the **synthesizer**, which authors the NIST/ATT&CK/coverage rollups from specialist content (and, per [ADR-0020](0020-tooling-authored-derived-fields.md), the assembler authors every field that is a pure function of authored content). What was missing is a *named class* for cross-framework views derived this way.

## Decision

Introduce a second class of taxonomy artifact — the **derived view** — authored solely by the synthesizer from (a) anchors specialists already emit and (b) a bundled, authoritative crosswalk catalog. A derived view **never** adds a `control_mappings` key, **never** appears in specialist discipline, and **never** gates specialist emission. It is computed at synthesis time and emitted as a rollup when its input anchors are present.

Three kinds, by what they relate:

| Kind | Relates | Catalog | First instance |
|---|---|---|---|
| **Bridge** | two existing finding-side anchors, to each other | CAPEC (`CWE ↔ ATT&CK`) | CAPEC bridge |
| **Overlay** | one existing anchor → related metadata | ATT&CK (`technique → detection data components`) | detection-coverage overlay |
| **Projection** | one capability-side anchor → another framework's vocabulary | NIST CPRT / 800-66r2 (`800-53r5 → HIPAA, CSF 2.0`) | compliance-crosswalk projection |

### Mechanics (uniform across all three)

1. **Reference data** ships as bundled JSON at `tools/apd_gauntlet/data/*.json` with a `_meta` freshness block, refreshed by a `refresh-*` CLI verb using the existing hardened fetch pattern (60s timeout, response-size cap, `source_sha256` + `fetched_at`) — identical to the emission catalogs (`refresh-cwe`, `refresh-d3fend`, …).
2. **The synthesizer** emits a `40-synthesis/<view>.yaml` rollup, schema-validated (single-file `cwe-coverage.schema.json` convention — the YAML *is* the validated document), **when its input anchors are present**; absent inputs → no artifact (graceful, like the existing gated rollups).
3. **Gating is on input-anchor presence, not on a new enum value.** The `run-config` `taxonomies:` enum keeps its meaning — *specialist-emission vocabularies*. Derived views are **not** added to it. A bridge emits when both its anchor taxonomies are declared; an overlay when its anchor is declared; a projection when its (always-present) anchor has coverage.
4. **The report** renders derived views as Coverage families, explicitly labeled **derived**. Projections additionally carry the per-mapping **relationship fidelity** (NIST IR 8477 STRM: `subset` / `superset` / `intersect` / `equal`) and a *"derived projection — not an audit attestation"* caveat.
5. **Every derived-view audit check is advisory / non-blocking.** A sparse or stale crosswalk must never block a report. The governing honesty rule:

   > **Absence of a crosswalk link is silence, never a negative finding.** A derived view asserts only what the authority asserts; it never infers a gap, a contradiction, or a mismatch from the *absence* of a published relationship.

6. **No change to `finding.schema.json` / `capability.schema.json` `control_mappings`.** No new specialist vocabulary; no new high-confidence bar.

### Derived view vs. emission taxonomy

| | Emission taxonomy (ADR-0008/0012/0014) | Derived view (this ADR) |
|---|---|---|
| Authored by | specialist agent (judgment) | synthesizer (authority) |
| Lives in | `control_mappings` on a record | `40-synthesis/<view>.yaml` |
| Run-config | a `taxonomies` enum value gates emission | not in the enum; gated on input anchors |
| Discipline | a section of `apd-control-mappings` + high-confidence bar | none |
| Schema impact | new `control_mappings` key | new rollup schema only |
| Failure mode it guards | shotgun mapping | over-derivation → **advisory only + silence-on-absence** |

## Consequences

**Positive.**

- Framework coverage grows without taxing specialists or re-opening the shotgun-mapping risk. The three highest-value additions on the roadmap (CAPEC, detection, HIPAA/CSF2) all land as derived views with **zero** specialist-prompt change.
- Mappings are provably consistent: a projection is a pure function of one anchor (`nist-coverage.yaml`) plus a published crosswalk, so two runs with the same NIST coverage project identically.
- Honest about fidelity by construction — projections carry STRM relationship types; bridges report corroboration vs. suggestion; nothing is asserted that the authority does not.
- Cheap to extend: a fourth projection target (HITRUST, ISO 27001) is a new catalog + a row in the projection rollup, not a new ADR.

**Negative / bounded.**

- Derived views inherit the coverage gaps of their upstream crosswalks. CAPEC maps only ~20% of its catalog to ATT&CK; many findings will have no CAPEC connecting their CWE and technique. The view must present this as **"not determinable,"** never as incoherence — enforced by the silence-on-absence rule and advisory-only checks.
- Projections can be misread as compliance attestations. Mitigated by mandatory `derived` + STRM-fidelity + "not an audit attestation" labeling in the report; the projection is a *coverage view in another vocabulary*, not a certification.
- Each crosswalk catalog adds a `refresh-*` verb and a freshness surface. Mitigated by reusing the existing hardened-fetch + `_meta` machinery; cadence stays quarterly.

## Alternatives considered

- **Add each as an emission taxonomy** (the MASVS/ATLAS path). Rejected for these three: the relationships are externally authoritative, so specialist authoring is wasted effort, less defensible than citing MITRE/NIST, and re-opens shotgun mapping. Reserve emission for genuine judgments.
- **Compute at report-time only, no synthesis artifact.** Rejected: no schema-validation surface, not reusable by external consumers of `40-synthesis/`, and inconsistent with the established rollup-then-render pipeline.
- **One generic `crosswalk.yaml` for all derived views.** Rejected: bridge, overlay, and projection have materially different shapes and render treatments; separate, tight schemas beat one loose union.
- **Let specialists optionally confirm derived suggestions** (the "both" option for CAPEC). Deferred, not rejected — v1 keeps derivation fully synthesizer-side to prove the class; a confirm-loop can be added later without schema change.

## References

- [ADR-0008: Multi-Framework Taxonomy Mappings](0008-multi-framework-taxonomy-mappings.md) (the emission class)
- [ADR-0012: MITRE ATLAS Finding Taxonomy](0012-mitre-atlas-finding-taxonomy.md)
- [ADR-0014: OWASP MAS Mobile Taxonomy](0014-owasp-mas-mobile-taxonomy.md)
- [ADR-0020: Derived Fields Are Tooling-Authored](0020-tooling-authored-derived-fields.md) (same philosophy, applied to identity)
- `docs/superpowers/specs/2026-06-14-capec-bridge-design.md` (Bridge — first implementation)
- `docs/superpowers/specs/2026-06-14-attack-detection-overlay-design.md` (Overlay)
- `docs/superpowers/specs/2026-06-14-compliance-projection-layer-design.md` (Projection)
