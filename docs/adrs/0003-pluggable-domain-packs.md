# ADR-0003: Pluggable Domain Packs (PBM-as-Default, Generic-as-Extension)

**Status:** Accepted
**Date:** 2026-05-24

## Context

Security severity calibration is domain-specific. A finding that is Critical in a Pharmacy Benefit Management (PBM) context — because it touches ePHI and triggers HIPAA breach notification — may be High or Medium in a generic SaaS context. Similarly, immutability classes, data taxonomies, and consequential-action surfaces differ substantially between regulated healthcare, financial services, and general software. A single hardcoded rubric cannot serve all domains without either being too conservative (noise) or too permissive (misses).

At the same time, the core analytical lenses — the nine APD goals and their associated specialist reasoning — are domain-neutral. Confidentiality analysis asks the same structural questions regardless of whether the data is ePHI or payment card data; only the calibration of what constitutes an acceptable risk differs.

The framework was initially built for PBM clients. However, given OSS ambitions and a desire for external domain pack authors, hardcoding PBM-specific calibration into the core framework would limit adoption and make it harder for contributors to reason about where domain-specific logic lives.

## Decision

Lens definitions, specialist skills, and the synthesizer are domain-neutral. Domain-specific content — severity rubric, consequential-action surface, immutability classes, data taxonomy, and per-goal common patterns — lives in `domains/<pack-name>/` packs. The PBM pack ships with v1.0 at `domains/pbm/` and is the default when no pack is specified. The synthesizer skill accepts a `--domain` flag at invocation time and loads the named pack's content.

Pack structure is defined by a schema at `schemas/domain.schema.json` (canonical `tools/apd_gauntlet/data/schemas/domain.schema.json`). New packs must pass `apd-gauntlet validate-domain` before being accepted.

## Consequences

- The PBM pack ships with v1.0 and is immediately useful for the target client base.
- External authors can contribute SaaS, banking, healthcare, or other packs without modifying core framework files.
- The synthesizer remains domain-neutral, making its logic easier to test and reason about.
- Per-goal common patterns are duplicated across packs (each pack must define patterns for all nine goals), which is verbose but ensures each pack is self-contained.
- Users who omit `--domain` get PBM calibration silently, which may surprise non-PBM users until documentation improves.

## Alternatives considered

- **Hardcode PBM** — limits OSS adoption; any non-PBM user must fork the framework or live with miscalibrated severity.
- **Fully generic (no domain pack mechanism)** — defers calibration to every user, reducing immediate usefulness and producing inconsistent outputs across runs.
- **Domain packs as Python plugins** — stronger isolation, but raises the authoring barrier for domain experts who are not Python developers; YAML/Markdown packs are accessible to more contributors.
