# Infra reuse map

**Status:** Active
**Date:** 2026-06-10

"Reuse, do not reinvent" is a non-negotiable program principle (design spec §3).
Every workstream extends existing infrastructure rather than building a parallel
implementation. This map is the authoritative index: each existing module, the
workstream(s) that extend it, and a do-not-reinvent note. If you are about to add
a validator, a serializer, a metrics computation, or a fetcher, find it here
first.

| Existing module / surface | Extended by | Do-not-reinvent note |
|---|---|---|
| `tools/apd_gauntlet/validate.py` (`run_schema_pass`, Registry pass) | W0, W1a, W1b, W3b | The schema gate already encodes every needed constraint. W0 only makes the existing `validate-full-prephase5` receipt block; W1a/W1b/W3b add schema fields validated for free by the two existing validators. Never write a second validator. |
| `tools/apd_gauntlet/canonicalize.py` | W0, W2 | Canonical YAML round-trip lives here. Re-emit through it; do not hand-roll serialization. |
| `tools/apd_gauntlet/synthesis/audit.py` (structural/editorial `_check(klass=...)` split) | W0, W2, W3b | Add a gate row via `_check(klass="structural")` (blocks) or `klass="editorial"` (non-blocking). Do not add a parallel audit pass. |
| `tools/apd_gauntlet/synthesis/metrics.py` (`compute_metrics`) | W3a | `compute_metrics` is the ONE report-summary implementation. W3a edits it in place to make `findings_pre_dedup` real. Do not compute metrics anywhere else. |
| `tools/apd_gauntlet/synthesis/apply.py` (`_merge_capabilities`, `_write_outputs`) | W0, W3a | The single emit point. W0 stops the `str(scope)` coercion here; W3a threads the pre-dedup census through here. |
| `tests/test_synthesis_equivalence.py` | W0, W3a | The round-trip / behavior-preservation home. New synthesis behavior gets a sibling test here. |
| The report-completeness gate (`audit.py`) | W2, W3b | Extend with one more `_check`; it already checks counts/coverage/sections. |
| `tools/apd_gauntlet/kb_fetch.py` (`fetch_pinned`) — new in CC | W2, W4 | CC factors the six `refresh_*.py` fetchers into one helper. W2 (assumption citations) and W4 (clinical-FHIR standards lookup) import it for cached, version-pinned external fetch. Never re-copy the Content-Length/size-cap block again. |
| The six `refresh_*.py` fetchers + the `data/*.json` `_meta` cache convention | CC | CC standardizes the `_meta` provenance shape (`source`, `source_sha256` or `commit`, `fetched_at`) and enforces it with `tools/check_kb_cache_freshness.py`. |
| `tools/check_report_template_freshness.py` (freshness-gate idiom) | CC | The model for `check_kb_cache_freshness.py`: a stdlib script wired into `python-tests.yml` that exits non-zero with a clear instruction. |
| `enumerate.py` (`compute_bottleneck_edges`) | W3b | Bottleneck frequency is already computed over all paths. W3b surfaces it; it does not re-derive. |
| The `attack_path_analysis` nested-object schema pattern | W1a, W1b, W5 | The shape precedent for new nested run-config objects (`infrastructure`, `repos[]`). |
| `apd-code-recon.md` agent template | W5 | The exact template for a gated, least-privilege, non-finding-emitting introspection agent. |
| `build_domain_skill.py` (data-driven off `domain.yaml`) | W4 | A new sibling pack compiles for free — no code change. |

## See also

- [CI gate model](ci-gate-model.md)
- [Schema evolution](schema-evolution.md)
