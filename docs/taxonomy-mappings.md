# Taxonomy mappings (v1.2+)

APD Gauntlet maps every finding and capability to NIST SP 800-53r5 and (high-confidence-only) MITRE ATT&CK by default. As of v1.2, findings and capabilities can also carry optional mappings to additional widely-adopted frameworks: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10, and MITRE D3FEND. These additional mappings make the gauntlet's output legible to reviewers fluent in those vocabularies without changing the underlying lens-driven analysis.

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

D3FEND attaches to **capabilities** (defensive techniques the design implements), not findings — symmetric with the existing ATT&CK-technique-on-findings, ATT&CK-mitigation-on-capabilities split.

## Declaring taxonomies per run

The set of taxonomies in scope for a run is declared in `.apd-run.yaml`:

```yaml
run_id: apd-20260601-claim-event-bus
domain: pbm
taxonomies:
  - cwe              # default-on (always available)
  - mitre_attack     # default-on
  - d3fend           # default-on
  - owasp_api_top10  # opt-in (the SUT exposes a REST API)
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

- **CWE** — use base or variant abstractions only; pillar/category entries are too abstract. Each mapping must be justified by the finding's `detail` text.
- **OWASP Top 10 / API / LLM** — preserve edition year in the ID (`A03:2021` stays `A03:2021` even after OWASP publishes the 2024 edition). Map only when the SUT exposes the relevant surface.
- **D3FEND** — `counters_attack` cross-reference is **required**; the cited ATT&CK technique must also appear in the same capability's `mitre_attack[].technique` list (with sub-technique parent matching — `T1110.001` is satisfied by `T1110`). The validator enforces this; map-by-name-similarity is forbidden. D3FEND IDs are 2-to-7 letter short codes (e.g., `D3-NTA`, `D3-NTF`, `D3-PHDURA`); reference data at `tools/apd_gauntlet/data/d3fend.json` lists all 149 published techniques.

## Synthesizer rollups

When the relevant taxonomies are declared and findings/capabilities carry the mappings, the synthesizer emits:

- `40-synthesis/cwe-coverage.yaml` — CWE IDs grouped by abstraction and parent pillar.
- `40-synthesis/owasp-coverage.yaml` — OWASP categories per variant; categories with no finding coverage are emitted with `silent: true` to make absence visible.
- `40-synthesis/d3fend-coverage.yaml` — D3FEND techniques implemented by capabilities plus a `counter_coverage` view (for each exposed ATT&CK technique, whether a D3FEND-backed capability counters it).

The advisory report links to each rollup in a "Framework Coverage" section.

## Reference-data refresh

The gauntlet ships projected reference data at `tools/apd_gauntlet/data/`. To refresh from upstream sources:

```bash
apd-gauntlet refresh-cwe
apd-gauntlet refresh-owasp
apd-gauntlet refresh-d3fend
```

Each script applies a 60-second HTTP timeout, a 200 MiB response cap, and records a `source_sha256` and `fetched_at` in the projected JSON. Recommended cadence: **quarterly**, or whenever a taxonomy publishes a new edition you intend to adopt.

**Current data state (v1.2.0):**

- CWE: 969 weaknesses, live-fetched from MITRE CWE v4.20
- OWASP Top 10 / API / LLM: 30 categories total (10 each), seed-only (OWASP project endpoints returned 404 at ship time)
- D3FEND: 149 defensive techniques with 3234 counter relations, live-fetched
