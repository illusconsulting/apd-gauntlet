# ADR-0014: OWASP MAS (MASVS + MASWE) as Mobile Finding/Capability Taxonomies

**Status:** Accepted
**Date:** 2026-06-09
**Supersedes:** —
**Superseded by:** —

## Context

APD Gauntlet v1.7.0 ships the `mobile-applications` domain pack, which targets
the adversary-controlled-client surface: on-device storage, keystore/TEE, TLS
pinning, WebView/JS bridges, deep-link/IPC, in-process SDKs, reverse-engineering
resilience, and hardware attestation. The control and weakness vocabulary the
mobile-security community uses for this surface is the **OWASP Mobile Application
Security (MAS)** project: **MASVS** (the verification standard — eight control
categories: Storage, Crypto, Auth, Network, Platform, Code, Resilience, Privacy)
and **MASWE** (the weakness enumeration that maps each weakness to a MASVS v2
control and, where applicable, to CWE).

Neither MITRE ATT&CK (Enterprise or Mobile) nor MITRE ATLAS expresses the
client-side verification requirements MASVS catalogs, and CWE — while it covers
many underlying weakness classes — does not carry the mobile-specific
verification framing (e.g. "MASVS-RESILIENCE-2: the app implements anti-tampering
mechanisms") that a mobile reviewer expects to see. Without MASVS/MASWE IDs,
`mobile-applications` findings can express the mobile control gap only in prose,
losing the structured cross-referencing and coverage rollups that taxonomy IDs
enable.

ADR-0008 codified the multi-framework taxonomy approach (per-run-scoped IDs in
`control_mappings`, coverage rollups synthesized from them, reference data via a
`refresh-*` verb), and ADR-0012 extended it to a findings-only offensive catalog
(ATLAS). MAS sits across both halves of the finding/capability split: a MASVS
control is a *verification requirement* a capability can satisfy and a finding
can flag as unmet, so MASVS belongs on **both** findings and capabilities; MASWE
is a *weakness* catalog — what is wrong — so it belongs on **findings only**,
parallel to ATLAS.

## Decision

Adopt **OWASP MASVS and MASWE as per-run-scoped mobile taxonomies**, extending
the multi-framework taxonomy-mapping approach of ADR-0008 and ADR-0012.

**Schema placement.** Specialists emit MASVS control IDs in
`control_mappings.masvs` and MASWE weakness IDs in `control_mappings.maswe`, both
as flat ID lists (the CWE/OWASP/ATLAS shape, not the dict-with-rationale ATT&CK
shape). `masvs` appears on **both** findings and capabilities; `maswe` is
**findings-only**. The `$defs` add `maswe_id` (`^MASWE-[0-9]{4}$`),
`masvs_control_id`
(`^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$`),
and `masvs_category_id`
(`^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)$`).

**Activation by pack declaration, then auto-seed.** Unlike ATLAS (declared
directly in `.apd-run.yaml`), MAS activates through the domain pack: a pack
declares a top-level optional `taxonomies:` array in `domain.yaml`, and the
`mobile-applications` pack declares `taxonomies: [masvs, maswe]`. At `init-run`,
the selected packs' declared taxonomies are unioned into the run-config
`taxonomies:` list (pack -> run auto-seed), so an operator who selects
`--domain mobile-applications` gets MASVS/MASWE in scope without naming them.
The operator can still add or remove taxonomies in `.apd-run.yaml` afterward.
Default-off for every other pack.

**Reference data.** Two bundled catalogs ship with the gauntlet:
`tools/apd_gauntlet/data/masvs.json` (MASVS v2.1.0 controls, keyed by control
ID, carrying title + category + category title) and
`tools/apd_gauntlet/data/maswe.json` (MASWE weaknesses, keyed by weakness ID,
carrying title + filing category + status + parent MASVS v2 controls + CWE
list). A new `apd-gauntlet refresh-mas` verb refreshes both in one pass.

**URL resolution.** `masvs_url(control_id)` is pure-regex and resolves to
`https://mas.owasp.org/MASVS/controls/{id}/` with no catalog read.
`maswe_url(weakness_id)` reads `maswe.json` for the weakness's filing category
and resolves to `https://mas.owasp.org/MASWE/{category}/{id}/`, returning `None`
when the category is unknown.

**Coverage rollups.** Two gated synthesis rollups are emitted when the matching
taxonomy is declared and at least one record cites it:
`40-synthesis/masvs-coverage.yaml` (controls with finding/capability counts,
surfaces, and a `posture` from `coverage_logic.posture()`) and
`40-synthesis/maswe-coverage.yaml` (weaknesses with finding counts and parent
MASVS controls). New single-file schemas `masvs-coverage.schema.json` and
`maswe-coverage.schema.json` (no `-doc` wrapper, the `cwe-coverage.schema.json`
convention) register directly in `validate.py`'s `SYNTHESIS_ROLLUPS`. The report
surfaces them as the **"OWASP MASVS"** and **"OWASP MASWE"** taxonomy families
in two Coverage sub-tabs.

**MASWE-Beta pinning.** MASWE is published as a Beta enumeration. The bundled
`maswe.json` records the upstream `commit` it was projected from in `_meta`, and
each weakness carries its `status` (e.g. `new`). The catalog is pinned to a
specific upstream commit per refresh; we do not track the moving Beta tip
silently. Refresh cadence follows the quarterly pattern of the other `refresh-*`
verbs.

## Alternatives considered

### MASVS/MASWE in narrative prose only (no structured field)

**Rejected.** Prose references cannot drive coverage rollups, the
`taxonomy_titles_resolve` audit check, or the report's taxonomy family
rendering. Structured `control_mappings.masvs`/`.maswe` enables all three and is
additive within `control_mappings`, consistent with ADR-0008's additive-only
policy.

### Fold MASWE into CWE (map mobile weaknesses to their CWE parents only)

**Rejected.** Many MASWE weaknesses carry a CWE list, but the mobile-verification
framing (which MASVS control the weakness violates) is exactly what a mobile
reviewer needs and what CWE does not express. Keeping MASWE first-class preserves
the MASWE -> MASVS-v2 linkage in `maswe.json` that the rollup uses.

### MASVS findings-only, like ATLAS

**Rejected.** A MASVS control is a verification requirement, not an attack
technique. A capability that implements (say) certificate pinning *satisfies*
MASVS-NETWORK; recording that on the capability is exactly the
defensive-coverage signal the coverage rollup needs. Restricting MASVS to
findings would discard the capability-side coverage. MASWE, by contrast, is
weakness-only and stays findings-only.

### Declare MAS directly in `.apd-run.yaml` (like ATLAS), no pack auto-seed

**Rejected.** MASVS/MASWE are relevant precisely when the
`mobile-applications` pack is in scope. Auto-seeding the taxonomies from the
pack's `domain.yaml` removes a manual step that an operator would otherwise have
to remember, while still allowing explicit override. ATLAS pre-dates the pack
`taxonomies:` field; the auto-seed is the new general mechanism and ATLAS-style
direct declaration remains supported.

## Consequences

- Mobile findings and capabilities carry precise MASVS control IDs and (findings)
  MASWE weakness IDs rather than prose; the `masvs-coverage` and `maswe-coverage`
  rollups quantify which controls and weaknesses the run addresses.
- Schema additions are fully additive within v1.x: `control_mappings.masvs` (on
  findings and capabilities) and `control_mappings.maswe` (findings) are new
  optional arrays. v1.6-format findings validate unchanged against v1.7 schemas.
- A new top-level optional `taxonomies:` field on `domain.yaml` lets any pack
  declare its default taxonomies; `init-run` unions them into the run config.
  Packs that omit the field are unaffected.
- `report-audit.yaml` gains `id_coverage_masvs` and `id_coverage_maswe` checks,
  and `coverage_rollups_nonempty` extends to the MAS rollups when MAS is active
  and cited. Runs without MAS in scope are exempt.
- A new `refresh-mas` CLI verb and the `masvs.json`/`maswe.json` catalogs join
  the quarterly refresh cadence. Operators who never select the
  `mobile-applications` pack (or never declare `masvs`/`maswe`) are unaffected.
- MASWE is pinned per refresh to an upstream commit recorded in `_meta.commit`;
  the Beta status is surfaced per weakness so consumers can see which weaknesses
  are provisional.
