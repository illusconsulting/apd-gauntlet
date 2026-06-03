# ADR-0013: Author a Grounded Baseline Threat Model

**Status:** Accepted
**Date:** 2026-06-03
**Supersedes:** ADR-0009 (the reviewer-only posture; the methodology-aware
evaluator design is preserved and extended)
**Superseded by:** —

## Context

ADR-0009 established the gauntlet as a threat-model *reviewer*, not an author.
It explicitly rejected "active augmentation" — having the gauntlet propose
threats beyond what the operator wrote — on two grounds: it "crosses the line
from threat-model reviewer to threat-model author," and it risks "the gauntlet's
threat brainstorming becoming the authoritative list, undermining the original
TM author's process." Under that posture, `apd-threat-model-recon` only parses a
*supplied* threat model, and `apd-threat-model-evaluator` only grades it.

That posture leaves a gap: a run with no supplied threat model produces no
threat-model artifact at all. The specialists analyze the design, but nothing
assembles their evidence into a structured, surface-by-surface threat baseline,
and the evaluator has nothing to grade. Operators who have not yet authored a
threat model — the common case for an early tech-plan review — get none of the
coverage/contradiction signal the evaluator exists to provide.

The reason ADR-0009 gave for rejecting authoring was sound but specific: an
author that *brainstorms* threats becomes the authoritative list and, worse, if
the same system that authors a threat model then grades it with the
coverage/silence passes, those findings become **tautological** — the gauntlet
would be marking its own homework. Any always-on author-then-grade design must
engineer that tautology out, not wish it away. This ADR records a design that
does exactly that.

## Decision

Adopt an **always-on, grounded baseline threat-model author**, layered on top of
ADR-0009's two-agent split, with the self-grading tautology engineered out.

**Always-on baseline.** A new tier-0 `apd-threat-model-author` agent runs on
every gauntlet run, after intake/code-recon and before tier-1. It emits the
canonical `00-context/threat-model-normalized.yaml` with
`generated_by: threat_model_author`, plus a human-readable
`00-context/threat-model-authored.md`. It is a pure context-builder: it emits no
findings, no severity, and is not in the finding-dedup/rollup pipeline. The
existing evaluator turns the baseline into findings.

**Supplied TM becomes a comparator seed.** When the operator supplies a threat
model, `apd-threat-model-recon` parses it into the **sibling**
`00-context/threat-model-supplied-normalized.yaml` (not the canonical file —
there is exactly one producer per file). The evaluator diffs the supplied TM
against the authored baseline and emits an omission finding flavor for material
threats the supplied TM omitted.

**Mechanical never-invent (the CLI floor).** A deterministic
`apd-gauntlet author-threat-model` CLI builds the threat *skeleton* — one entry
per (surface, applicable-STRIDE category) cell — directly from the asset
inventory using a fixed element-type -> applicable-STRIDE matrix. The CLI never
invents a surface; the agent may only **ground** or **block** the skeleton cells
the CLI produced. This makes "completeness" mechanical rather than a brainstorm,
the precise failure mode ADR-0009 feared.

**Weakest-source confidence floor.** Each grounded threat's
`extraction_confidence` is set to the weakest grounding source backing it
(code-evidence edge -> high; context-brief prose -> medium; domain-default-only
or inference-only -> low). Ungrounded-but-applicable cells become blocked
placeholders with a structured `prerequisite_evidence` array — gap-markers,
never counted as coverage.

**Anti-tautology carve-out (first-class decision).** When the canonical TM is
`generated_by: threat_model_author` and no supplied sibling exists, the
evaluator does NOT run the intrinsic coverage-gap / silence passes against
authored entries — those passes only mean something against a *human* TM, and
running them on authored content would be self-grading. Baseline-only grading is
limited to (a) the **contradiction pass** (an author-asserted `mitigation`
checked against specialist reality) and (b) an
**independent-specialist-corroboration gate** (an authored threat is "material"
only if an independent specialist finding flags the same surface + goal). When a
supplied TM is present, the full comparator runs against the human TM, where the
coverage/silence semantics are valid again.

## Alternatives considered

### Keep the reviewer-only posture (ADR-0009 unchanged)

**Rejected.** It leaves every no-supplied-TM run with no threat-model artifact
and nothing for the evaluator to grade, which is the majority of early
tech-plan reviews. The motivating value of the evaluator — coverage and
contradiction signal — is unavailable exactly when operators most need a
starting baseline.

### Always-on author that also self-grades (no carve-out)

**Rejected.** This is the tautology ADR-0009 warned about: the system authors a
threat list and then "discovers" that the list covers the surfaces — a circular,
information-free result for the coverage/silence passes. The anti-tautology
carve-out is what makes an always-on author defensible.

### LLM-only authoring (no deterministic CLI floor)

**Rejected.** Asking the LLM to enumerate "all applicable threats" reintroduces
the brainstorm-becomes-authoritative-list failure mode. A deterministic CLI
floor that derives surfaces and applicable-STRIDE cells from the inventory keeps
the surface set mechanical and auditable; the LLM's judgment is confined to
grounding or blocking each cell and to in-LLM data-flow reconstruction, where
semantic interpretation of human prose is its real strength.

## Consequences

- Every run now produces a grounded baseline threat model and a human-readable
  render, even with no supplied TM. The tier-4 evaluator always runs because the
  authored baseline always exists.
- What ADR-0009 **preserves** carries forward intact: the evaluator's
  methodology-awareness, the never-invent rigor of the parse path, the
  recon/evaluator two-agent split, and the co-equal mapping tables in
  `mappings.py` and the `apd-threat-model-methodologies` skill.
- What this ADR (ADR-0013) **supersedes** from ADR-0009 is narrow: the reviewer-only stance. The
  framework now authors a grounded baseline; the "never invent threats" rule is
  re-scoped to bind the recon + evaluator parsing/grading path, while the
  author's proactive-completeness mandate is governed by the methodologies
  skill's `## Authoring discipline` section.
- The `threat_model_author` value is added to the normalized schema's
  `generated_by` enum, and an optional entry-level `prerequisite_evidence` array
  is added — both additive within v1.x. Consumers that load the canonical TM
  (notably `tools/apd_gauntlet/attack_path/build.py`) gain a `generated_by`
  guard so author-inferred threats are treated as inferred, not operator-declared
  ground truth.
- A blocked placeholder is a structured gap-marker, never coverage. Operators
  see, in the authored baseline, exactly which applicable cells lack grounding
  and what evidence would ground them.
