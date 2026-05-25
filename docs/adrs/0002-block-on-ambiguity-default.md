# ADR-0002: Block on Ambiguity as the Default Disposition

**Status:** Accepted
**Date:** 2026-05-24

## Context

Security architecture reviews frequently encounter artifacts that are incomplete, contradictory, or silent on key properties. A specialist reviewing an artifact for, say, data-at-rest encryption may find no mention of encryption configuration at all — this silence could mean "encryption is handled elsewhere," "the author forgot to document it," or "it genuinely doesn't exist." Any of these interpretations produces a different finding.

Low-confidence or hedged findings ("might be a problem," "could indicate a gap") are common in manual review outputs and are treated as noise by engineering teams. When a reviewer hedges, the finding is dismissed rather than actioned. Conversely, inferring properties from silence — asserting "this system lacks encryption" because the artifact doesn't mention it — produces wrong-asserted findings that damage the framework's credibility when engineering teams can point to controls that exist but were not visible in the submitted artifacts.

The gauntlet is a structured, multi-artifact process. When the right artifact hasn't been submitted yet, the correct response is to say so, not to speculate or hedge.

## Decision

The default disposition under any artifact ambiguity is `blocked`. When a specialist cannot determine whether a property holds or fails because the necessary evidence is absent, the finding record is emitted with `disposition: blocked` and `prerequisite_evidence` populated, naming the specific artifact or excerpt that would resolve the ambiguity. A blocked finding is a structured request for more artifacts — it is a deliverable, not a failure state.

Specialists may only emit `confirmed` or `failed` dispositions when evidence in the submitted artifacts directly supports the determination. Inference from silence is prohibited.

## Consequences

- Blocked findings become an actionable artifact request list that the intake agent can surface to the user.
- False-positive failure findings are reduced because specialists cannot assert failure from silence.
- The framework's credibility is higher — every `failed` finding is backed by explicit evidence.
- Review runs against sparse artifact sets produce more `blocked` entries and fewer `confirmed`/`failed` entries, which may feel like lower throughput until the full artifact set is available.
- The validator enforces that `blocked` findings include a non-empty `prerequisite_evidence` field, making the schema constraint the enforcement mechanism rather than reviewer discipline.

## Alternatives considered

- **Low-confidence findings** — emitting findings with a `low_confidence` flag was trialed in early runs. Engineering teams dismissed them at a higher rate than high-confidence findings, and the hedging language made triage harder.
- **Inferring properties from silence** — treating absence of evidence as evidence of absence produces wrong-asserted findings. When a control exists in infrastructure-as-code but not in the architecture diagram, asserting failure damages credibility.
- **Abstaining (no finding emitted)** — silent abstention gives no signal that more artifacts are needed, defeating the structured-review purpose.
