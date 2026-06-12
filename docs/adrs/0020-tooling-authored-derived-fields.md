# ADR-0020: Derived Fields Are Tooling-Authored; Agents Emit Content Only

**Status:** Accepted
**Date:** 2026-06-12
**Amends:** [ADR-0005](0005-deterministic-finding-ids.md) (deterministic finding/capability IDs)

## Context

[ADR-0005](0005-deterministic-finding-ids.md) established that finding and capability IDs are deterministic — `<prefix>-<sha8(title|first_evidence_locator)>` — and it had specialist agents author a *best-effort* ID that the `canonicalize` tooling then recomputed and overwrote. As the gauntlet grew, the same "agent computes a hash" pattern spread to other record families with inconsistent rigor:

- **finding / capability** (`conf-…`, `intg-…`, `merged-…`) — agent authored a best-effort ID; `canonicalize` overwrote it. The agent's value was *always* discarded.
- **`tmeval-*`** (threat-model evaluator) — the agent computed the SHA itself from ad-hoc inputs, and **nothing recomputed or verified it**. Fabricated and unchecked.
- **`dimpr-*`** (domain-improvement auditor) — the agent shelled out to `apd-gauntlet mint-improvement-id` and pasted the result. Script-minted, but with manual friction at the agent boundary.
- **`asset-` / `idn-` / `tb-`** (intake asset inventory) — the agent fabricated the SHA "from name + locator"; **nothing recomputed it**.
- **`apath-*`** (attack-path analyzer) and **`merged-*`** (dedup) — already minted by Python (the attack-path emitter and `apply.py`). Clean.

Two problems followed. First, an LLM cannot reliably compute SHA-256 — it invents plausible hex. So every agent-authored ID was either wasted work (overwritten) or, worse, fabricated-and-unverified (`tmeval-*`, inventory). Second, the *intermediate* artifacts carried fake-authoritative IDs, which is misleading when a run is inspected mid-pipeline.

The deterministic floor was already substantial — run-directory scaffolding (`init_run.scaffold_run`), `control_mappings` normalization, `cross_references` rewriting, and the NIST/ATT&CK/coverage rollups are all script-authored. The gap was that *identity* was still partly the agent's job.

## Decision

**Every field that is a pure function of authored content is authored solely by the deterministic assembler. Agents author content only.**

Concretely:

- The `apd-gauntlet canonicalize` command (plus the sibling `assemble-inventory` pass for the asset inventory) is the **sole author** of every record ID and of `schema_version`.
- Specialist agents emit findings/capabilities with **no `id` and no `schema_version`**. The threat-model evaluator emits a structured **`tmeval_key`** (flavor + components) instead of a hand-computed ID. The domain-improvement auditor emits record content with **no `id`**. Intake emits inventory records with **no `asset_id`/`identity_id`/`boundary_id`** and authors `trust_boundaries.crosses` by asset **name**; the assembler mints the IDs and rewrites `crosses` name→id.
- Where a pre-assembly reference is genuinely needed, agents use a **stable handle they can author** (the asset *name*) rather than an ID they cannot compute. The assembler resolves the handle to the minted ID.
- JSON Schemas mark the derived fields `readOnly` and drop them from `required` (optional-at-emission). Presence/consistency **linters** (`check_id_present`, `check_tmeval_id`, the existing `check_domain_improvement_id`, and the inventory cross-ref pass) run *after* assembly as the backstop.
- The workflow runner invokes `canonicalize` / `assemble-inventory` at the points where a phase has just emitted records and before the next consumer reads their IDs (per-tier, after the tmeval/apath barrier and before rollup, after the domain-improvements phase, and in the intake phase before specialists).

The ID algorithms themselves are unchanged from ADR-0005 (and the `dimpr-` 4-tuple rule). This ADR changes *who authors them*, not *how they are computed*.

## Consequences

**Positive.**

- Eliminates the fabricated-hash error class entirely — an LLM is never asked to produce a hash.
- One source of truth for identity. No drift between agent-authored and tooling-recomputed IDs; the `tmeval-*` and inventory IDs are now verified rather than trusted.
- Intermediate artifacts stop carrying fake-authoritative IDs — an id-less pre-assembly record is honestly id-less.
- Agent prompts shed deterministic busywork and focus on judgment.
- The verification linters demote from "catch routine agent error" to genuine defense-in-depth.

**Negative / bounded.**

- The assembler (`canonicalize` + `assemble_inventory`) becomes a more critical chokepoint. Mitigated by the `test_canonicalize` / `test_assemble_inventory` / `test_tmeval_id` suites and idempotency tests.
- The pipeline must guarantee the assembler runs before any consumer of an ID. The workflow runner is wired accordingly; standalone callers must run `canonicalize` (and `assemble-inventory`) before `validate`'s semantic pass, which now enforces ID presence for in-scope records.
- **No change to run-to-run ID *stability*.** IDs remain a function of authored content (e.g. `title|locator`); if an agent rephrases a title between runs, the ID still changes. Moving authorship to the assembler fixes *consistency within a run*, not *stability across runs* — that is a separate content-normalization concern.

## Alternatives considered

- **Keep emit-then-overwrite, just document it as non-authoritative.** Rejected: retains the fabricated-hash class and the misleading intermediate IDs; the agent work stays pure waste.
- **Have agents emit a human-readable local slug as a handle.** Considered for debuggability, but there are no within-emission ID references today (cross-references are synthesizer-authored post-assembly), so a slug would buy little. The one place a pre-assembly reference exists — trust-boundary `crosses` — uses the asset *name*, which agents already author. Adopted that narrowly rather than a general slug scheme.

## References

- [ADR-0005: Deterministic Finding and Capability IDs](0005-deterministic-finding-ids.md) (amended by this ADR)
- [ADR-0006: LLM-Driven Clustering](0006-llm-driven-clustering.md) (synthesizer authors `merged-*` IDs and cross-references)
- `docs/deterministic-field-register.md` — the per-field authored-vs-derived register
