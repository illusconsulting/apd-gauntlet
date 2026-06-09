# Taxonomy mappings (v1.6+)

APD Gauntlet maps every finding and capability to NIST SP 800-53r5 and (high-confidence-only) MITRE ATT&CK by default. As of v1.2, findings and capabilities can also carry optional mappings to additional widely-adopted frameworks: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10, and MITRE D3FEND. As of v1.6, MITRE ATLAS is available as a first-class finding taxonomy for adversarial-ML threat coverage. As of v1.7, OWASP MASVS (mobile verification controls) and OWASP MASWE (mobile weakness enumeration) are available as first-class mobile taxonomies, auto-seeded into a run's scope when the `mobile-applications` domain pack is selected. These additional mappings make the gauntlet's output legible to reviewers fluent in those vocabularies without changing the underlying lens-driven analysis.

## Which taxonomies, where, and why

| Taxonomy | Attached to | Audience |
| --- | --- | --- |
| NIST 800-53r5 | findings + capabilities (required) | Compliance, FedRAMP, audit |
| MITRE ATT&CK (technique) | findings (optional, high-confidence) | Threat intel, detection engineering |
| MITRE ATT&CK (technique) | capabilities (optional, v1.2+) | Defensive architecture — documents what techniques the capability defends against |
| MITRE ATT&CK (mitigation) | capabilities (optional) | Defensive architecture |
| CWE | findings (optional, v1.2+) | Developers, AppSec |
| OWASP Top 10 (web) | findings (optional, v1.2+) | Application reviewers |
| OWASP API Top 10 | findings (optional, v1.2+) | API reviewers |
| OWASP LLM Top 10 | findings (optional, v1.2+) | AI-app reviewers |
| MITRE D3FEND | capabilities (optional, v1.2+) | Defensive architects |
| MITRE ATLAS | findings (optional, v1.6+) | AI/ML security, adversarial-ML threat coverage |
| OWASP MASVS | findings + capabilities (optional, v1.7+) | Mobile security, app-vetting |
| OWASP MASWE | findings (optional, v1.7+) | Mobile security, AppSec |

D3FEND attaches to **capabilities** (defensive techniques the design implements), not findings — symmetric with the existing ATT&CK-technique-on-findings, ATT&CK-mitigation-on-capabilities split.

ATLAS attaches to **findings** as an offensive adversarial-ML technique catalog — distinct from NIST/D3FEND (which are defensive) and complementary to ATT&CK for AI/ML system reviews.

MASVS attaches to **both findings and capabilities** — a verification control a capability satisfies or a finding flags as unmet. MASWE attaches to **findings only** as a mobile weakness catalog, parallel to ATLAS. Both are auto-seeded from the `mobile-applications` pack's `domain.yaml` `taxonomies:` declaration (`[masvs, maswe]`) at `init-run`; operators may still adjust the run-config `taxonomies:` list afterward.

## Declaring taxonomies per run

The set of taxonomies in scope for a run is declared in `.apd-run.yaml`:

```yaml
run_id: apd-20260601-claim-event-bus
domains:
  - pbm
taxonomies:
  - cwe              # default-on (always available)
  - mitre_attack     # default-on
  - d3fend           # default-on
  - owasp_api_top10  # opt-in (the SUT exposes a REST API)
  - mitre_atlas      # opt-in (AI/ML systems with adversarial-ML threat surface)
```

The `init-run` CLI accepts `--taxonomies`:

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ./artifacts \
  --domain pbm \
  --taxonomies cwe,mitre_attack,d3fend,owasp_api_top10
```

Intake inspects the supplied artifacts and may suggest additional taxonomies in the context brief (e.g., an OpenAPI spec triggers an `owasp_api_top10` suggestion; an LLM SDK import triggers `owasp_llm_top10`). Suggestions are advisory — specialists honor only the declared scope. Re-run with the suggested taxonomy added to `taxonomies:` to incorporate it.

## Mapping discipline

Each taxonomy has discipline rules documented in the `apd-control-mappings` skill. Summary:

- **CWE** — use base or variant abstractions only; pillar and category entries (e.g., CWE-840) are too abstract and must not be used. Each mapping must be justified by the finding's `detail` text. (The bundled catalog *does* carry category entries so that a finding which nonetheless cites one resolves to a title rather than a bare ID in the report — see the reference-data note below — but they remain out of discipline for new mappings.)
- **OWASP Top 10 / API / LLM** — preserve edition year in the ID (`A03:2021` stays `A03:2021` even after OWASP publishes the 2024 edition). Map only when the SUT exposes the relevant surface.
- **D3FEND** — `counters_attack` cross-reference is **required**; the cited ATT&CK technique must also appear in the same capability's `mitre_attack[].technique` list (with sub-technique parent matching — `T1110.001` is satisfied by `T1110`). The validator enforces this; map-by-name-similarity is forbidden. D3FEND IDs are 2-to-7 letter short codes (e.g., `D3-NTA`, `D3-NTF`, `D3-PHDURA`); reference data at `tools/apd_gauntlet/data/d3fend.json` lists all 149 published techniques.
- **MITRE ATLAS** — map only when the SUT processes ML models, training data, or inference pipelines and the finding relates to adversarial-ML threats. IDs follow the pattern `AML.T####` (top-level) or `AML.T####.###` (sub-technique). Map to the most-specific applicable technique; do not map by name-similarity alone.
- **OWASP MASVS / MASWE** — map only when the SUT is (or includes) a mobile application. MASVS control IDs follow `MASVS-<CATEGORY>-<n>` (categories: STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, RESILIENCE, PRIVACY); MASWE IDs follow `MASWE-####`. MASVS on a capability means the control is satisfied; MASVS on a finding means it is unmet. Map a MASWE weakness to the specific weakness observed, not the broad category.

## MITRE ATLAS

ATLAS is MITRE's catalog of adversarial-ML tactics and techniques targeting AI/ML systems. Unlike NIST 800-53r5 and D3FEND (which catalog defensive controls), ATLAS is an **offensive** catalog — it describes how an adversary attacks an AI system. This makes it the adversarial-ML counterpart to MITRE ATT&CK, and it rides on findings (not capabilities) for the same reason ATT&CK techniques do.

### Schema shape

ATLAS IDs live at `control_mappings.atlas` in the finding schema as a **flat ID list** — not the dict-with-rationale shape that ATT&CK uses:

```yaml
control_mappings:
  nist_800_53r5: [SI-3, SC-8]
  atlas:
    - AML.T0040
    - AML.T0043.001
```

This is consistent with how CWE and OWASP IDs are stored (plain string arrays). The rationale for the ATLAS mapping lives in the finding's `detail` field, as with CWE.

### ID format

`AML.T####` (top-level technique) or `AML.T####.###` (sub-technique). Both forms are valid. Sub-technique names resolve in the report as `Parent: Leaf` for tooltip clarity.

### Declaring and refreshing

Add `mitre_atlas` to `taxonomies:` in `.apd-run.yaml` to activate ATLAS coverage for a run. Refresh the bundled catalog:

```bash
apd-gauntlet refresh-atlas
```

The catalog is fetched from `mitre-atlas/atlas-data` (YAML bundle), projected to `{id: name}`, and written to `tools/apd_gauntlet/data/atlas-techniques.json`.

### Coverage rollup

When `mitre_atlas` is declared, the synthesizer emits `40-synthesis/atlas-coverage.yaml` (schema: `atlas-coverage.schema.json`). Each entry records the technique ID, resolved name, and the finding IDs that cite it. The report surfaces this as the **"MITRE ATLAS"** taxonomy family in the Coverage tab's tooltip layer.

## OWASP MASVS and MASWE

OWASP MAS is the mobile-security counterpart to the web/API/LLM OWASP catalogs. **MASVS** is the verification standard — eight control categories (Storage, Crypto, Auth, Network, Platform, Code, Resilience, Privacy). **MASWE** is the weakness enumeration; each MASWE weakness maps to a MASVS v2 control and, where applicable, to CWE.

### Schema shape

Both ride in `control_mappings` as flat ID lists. MASVS is on findings **and** capabilities; MASWE is findings-only:

```yaml
control_mappings:
  nist_800_53r5: [SC-28, SC-13]
  masvs:
    - MASVS-STORAGE-1
    - MASVS-CRYPTO-1
  maswe:
    - MASWE-0001
```

### ID format and URLs

- MASVS control: `MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-<n>` → `https://mas.owasp.org/MASVS/controls/{id}/` (resolved by `masvs_url()`, pure regex, no catalog read).
- MASWE weakness: `MASWE-####` → `https://mas.owasp.org/MASWE/{category}/{id}/`, where `{category}` is the weakness's filing category read from `maswe.json` (`maswe_url()`; returns `None` if the category is unknown).

### Declaring and refreshing

Selecting the `mobile-applications` pack auto-seeds `masvs` and `maswe` into `.apd-run.yaml`'s `taxonomies:` list. Refresh the two bundled catalogs in one pass:

```bash
apd-gauntlet refresh-mas
```

This writes `tools/apd_gauntlet/data/masvs.json` (MASVS v2.1.0 controls) and `tools/apd_gauntlet/data/maswe.json` (MASWE weaknesses, pinned to the upstream `commit` recorded in `_meta`). MASWE is a **Beta** enumeration; each weakness carries its `status`, and the catalog is pinned per refresh rather than tracking the moving tip.

### Coverage rollups

When `masvs` is declared, the synthesizer emits `40-synthesis/masvs-coverage.yaml` (schema: `masvs-coverage.schema.json`) — one entry per cited control with `finding_count`, `capability_count`, surfaces, and a `posture` from `coverage_logic.posture()`. When `maswe` is declared, it emits `40-synthesis/maswe-coverage.yaml` (schema: `maswe-coverage.schema.json`) — one entry per cited weakness with `finding_count`, the filing `category`/`status`, and the `parent_masvs` controls. The report renders these as the **"OWASP MASVS"** and **"OWASP MASWE"** taxonomy families in two Coverage sub-tabs.

## Synthesizer rollups

When the relevant taxonomies are declared and findings/capabilities carry the mappings, the synthesizer emits:

- `40-synthesis/cwe-coverage.yaml` — CWE IDs grouped by abstraction and parent pillar.
- `40-synthesis/owasp-coverage.yaml` — OWASP categories per variant; categories with no finding coverage are emitted with `silent: true` to make absence visible.
- `40-synthesis/d3fend-coverage.yaml` — D3FEND techniques implemented by capabilities plus a `counter_coverage` view (for each exposed ATT&CK technique, whether a D3FEND-backed capability counters it).
- `40-synthesis/atlas-coverage.yaml` — ATLAS technique IDs cited by findings, with resolved names and per-technique finding counts. Only emitted when `mitre_atlas` is declared and at least one finding carries an ATLAS mapping; the synthesizer skips this rollup on empty runs.
- `40-synthesis/masvs-coverage.yaml` — MASVS controls cited by findings and capabilities, with per-control counts, surfaces, and posture. Only emitted when `masvs` is declared and at least one record carries a MASVS mapping.
- `40-synthesis/maswe-coverage.yaml` — MASWE weaknesses cited by findings, with finding counts, filing category/status, and parent MASVS controls. Only emitted when `maswe` is declared and at least one finding carries a MASWE mapping.

The advisory report links to each rollup in a "Framework Coverage" section.

## Reference-data refresh

The gauntlet ships projected reference data at `tools/apd_gauntlet/data/`. To refresh from upstream sources:

```bash
apd-gauntlet refresh-cwe
apd-gauntlet refresh-owasp
apd-gauntlet refresh-d3fend
apd-gauntlet refresh-atlas
apd-gauntlet refresh-mas
```

Each script applies a 60-second HTTP timeout, a 200 MiB response cap, and records a `source_sha256` and `fetched_at` in the projected JSON. Recommended cadence: **quarterly**, or whenever a taxonomy publishes a new edition you intend to adopt.

**Current data state (v1.7.0):**

- CWE: 969 weaknesses (plus Category entries, e.g., CWE-840), live-fetched from MITRE CWE v4.20
- OWASP Top 10 / API / LLM: 30 categories total (10 each), seed-only (OWASP project endpoints returned 404 at ship time)
- D3FEND: 149 defensive techniques with 3234 counter relations, live-fetched
- MITRE ATLAS: 170 techniques (top-level and sub-techniques), live-fetched from MITRE ATLAS v5.6.0
- OWASP MASVS: 24 controls across 8 categories, projected from MASVS v2.1.0
- OWASP MASWE: weakness enumeration (Beta), pinned per refresh to the upstream `commit` recorded in `maswe.json` `_meta`
