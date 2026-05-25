# ADR-0006: LLM-Driven Clustering in the Synthesizer (No Algorithmic Cluster Code)

**Status:** Accepted
**Date:** 2026-05-24

## Context

Nine specialist agents each examine the same architecture through a different goal lens. It is expected that multiple specialists will find evidence of the same root cause — for example, a missing mTLS configuration may appear as a Confidentiality finding, an Integrity finding, and an Authenticity finding. The synthesizer must decide whether these are the same finding (merge), related findings that share evidence but address distinct concerns (link), or coincidentally similar findings that should remain separate.

This clustering decision is semantically subtle. String-similarity heuristics (Jaccard, cosine on TF-IDF vectors) match on surface features — two findings with the same title but different root causes would be merged, and two findings with different titles but the same root cause would be separated. ML-based clustering would require training data that doesn't exist, and the hyperparameters would need tuning that OSS contributors cannot reasonably perform.

The synthesizer already operates as an LLM-driven agent with access to all nine specialists' outputs simultaneously. It is the natural place for semantic reasoning about related concerns.

## Decision

Clustering remains LLM-driven prompt work in `apd-synthesizer.md`. The synthesizer is instructed to identify merges (same root cause, different lenses), links (shared evidence, distinct concerns), and separates (surface similarity only). No algorithmic clustering code lives in the Python validator. The validator checks that the synthesizer's output is structurally valid (ADR-0004) and that cross-references point to real finding IDs (ADR-0005), but does not verify clustering decisions.

## Consequences

- The synthesizer leverages the LLM's semantic understanding of related security concerns, which is superior to string similarity for this task.
- No risk of false-positive merges from string-similarity heuristics matching surface features.
- No training data or hyperparameter tuning required.
- Clustering decisions are not fully reproducible — re-running the synthesizer against the same inputs may yield slightly different merge/link decisions. This is an accepted trade-off.
- The validator cannot catch incorrect clustering (a semantic error), only structural errors. Clustering quality depends on synthesizer prompt quality.
- Future work could add a deterministic post-hoc check for obvious errors (e.g. a finding merged with itself), but that is out of scope for v1.0.

## Alternatives considered

- **Jaccard/cosine similarity on titles and evidence** — findings that are string-similar but semantically unrelated (e.g. two different controls that both affect "TLS configuration") would be incorrectly merged; semantically related findings with different titles would be missed.
- **ML-based clustering** — no training data exists; OSS contributors cannot tune ML models; the authoring and maintenance burden is disproportionate to the gain.
- **Cluster-by-rule (e.g. same `related_concerns` tags)** — too rigid; the `related_concerns` field was designed for cross-referencing, not as a clustering key, and rule-based clustering would create perverse incentives to add shared tags to avoid merges.
- **No clustering (all findings remain separate)** — produces redundant findings that dilute the report and make remediation prioritization harder for engineering teams.
