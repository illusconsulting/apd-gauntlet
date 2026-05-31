# Domain-Pack Authoring Docs Overhaul — Design

**Date** 2026-05-31 · **Status** Approved, pending user review · **Branch** `design/domain-pack-docs-overhaul`

## Summary

This is **sub-project 2** of the effort that began as "provide comprehensive and accurate
information about building domain packs." Sub-project 1 built the `agentic-ai` domain pack
(merged, PR #56). This sub-project overhauls the user-facing documentation so a newcomer
can author a pack end-to-end, operate multi-domain runs, and use the domain-improvement
loop — with the `agentic-ai` pack as the worked example.

The shape is **Hybrid**: comprehensively rebuild the two authoring guides, and surgically
fix the genuinely stale operator/reference docs. The worked example is `agentic-ai`
(dissected file-by-file); PBM is retained only where it uniquely illustrates a
regulated-data pattern.

## Corrected staleness finding

A re-audit of `main` corrected the original premise:

- The CLI flag is `--domain` (repeatable: `--domain pbm --domain api-security`). The
  `--domain pbm` examples in the docs are **correct, not stale** — there is no
  `--domain` → `--domains` rename to do.
- Do not conflate two distinct flags: **`--domain`** selects packs (repeatable) while
  **`--domains-dir`** points at the packs *directory* (default `domains/`). And
  `build-domain-skill` / `validate-domain` take **positional, space-separated** pack names
  (`build-domain-skill pbm api-security`), not a `--domain` flag. The guides must use each
  form correctly.
- Subsystem A already cut every run-config `domain:` (singular key) over to `domains:`
  (a list). Zero singular keys remain in user-facing docs. The one
  `run_cfg.get("domain")` in `report/loader.py` is an intentional legacy back-compat
  fallback, not something to document as current.

So the real surgical work is narrower than first thought, and is more about **coverage**
(new commands, multi-domain examples) than staleness. The one true staleness item is the
retired `apd-orchestrator` reference.

## Scope

**In scope.**

- Rebuild `docs/adapting-to-other-domains.md` (the authoring guide).
- Rebuild `docs/improving-domain-packs.md` (the improvement-loop guide).
- Surgical fixes to `docs/running-the-gauntlet.md`, `docs/architecture.md`, and `README.md`.
- A small staleness-guard pytest.

**Out of scope.**

- The deferred `hexo-ai/sia` golden run (a separate interactive effort).
- Framework-level efforts recorded earlier: ATLAS as a taxonomy, MAESTRO as a methodology.
- Other docs not listed above (`attack-path-analysis.md`, `threat-modeling.md`,
  `taxonomy-mappings.md`, `extending-agents.md`, `html-report.md`, `schema-evolution.md`)
  beyond incidental cross-link fixes — they are already accurate on the cutover.

## `docs/adapting-to-other-domains.md` — rebuilt structure

The current file is a 254-line PBM-based 10-step walkthrough with thin "rewrite X"
per-file sections, no full anatomy/schema, no multi-domain mechanics, and a
one-paragraph improvement-loop mention. Rebuild into these sections:

1. **Overview — how a pack influences a run.** A pack compiles via `build-domain-skill`
   into the `apd-domain` skill that every specialist loads; it calibrates severity, the
   consequential-action surface, crown jewels / attacker positions (attack-path), and the
   per-goal pattern catalogs. This answers the original "understand the influence" ask.
2. **Anatomy of a domain pack.** The 14 files and each file's responsibility, with the
   **full `domain.yaml` schema**: required `name` (`^[a-z][a-z0-9-]*$`), `display_name`,
   `version` (semver), `framework_compat` (range), `description` (>= 20 chars), `includes`
   (>= 1 path; no leading `/`, no `..`), `regulatory_anchors`; optional `crown_jewels` /
   `attacker_positions` / `default_trust_boundaries`, each `{<key>, description (>= 10)}`.
3. **Step-by-step authoring** (dissecting `agentic-ai` file-by-file): copy a starting pack
   → `domain.yaml` (the six crown jewels / attacker positions / trust boundaries) →
   `severity-rubric.md` (the four agentic modifiers) → the three support files → the
   **nine common-patterns** in the canonical `**Pattern:**` format. State the key lesson:
   **taxonomy mappings (CWE / ATT&CK / OWASP-LLM) are emitted in findings, not written in
   the pattern markdown** — the markdown carries `Severity` / `NIST` / `Related concerns`
   / `Detail`, and grounds the rest (OWASP-LLM / ATLAS / MAESTRO) in prose. Then
   `validate-domain` → `build-domain-skill` → a sample run.
4. **Multi-domain mechanics (new).** The `domains: [list]` model; how `build-domain-skill`
   merges packs (union/dedup of structured fields, concatenated markdown with provenance
   headers, per-pack severity rubrics under `## Domain:` headers, `metadata.packs`);
   severity union/max/provenance; composing your pack with others. Cross-link the
   run-time selection in `running-the-gauntlet.md`.
5. **Taxonomy & mapping discipline.** OWASP / ATT&CK / CWE / NIST guidance and the
   ATLAS/MAESTRO-as-prose lesson (with a one-line pointer that ATLAS-as-taxonomy and
   MAESTRO-as-methodology are possible future framework efforts).
6. **Reusable pattern: multi-regulator retention pinning** (PBM example, retained).
7. **Evolving a pack from gauntlet runs** (brief; links to the improvement-loop guide).
8. **Submitting the pack** (a concrete PR checklist).
9. **What stays the same across domains.**

## `docs/improving-domain-packs.md` — rebuilt structure

The current file is 69 lines / 4 thin sections. Rebuild into:

1. **Overview** — the capture → draft → apply loop. Every run emits advisory
   `40-synthesis/domain-improvements.yaml` via a deterministic coverage-delta pre-pass plus
   the `apd-domain-auditor` agent (non-blocking Phase 5h); on demand,
   `draft-domain-improvements` turns chosen opportunities into a validated, `git apply`-able
   patch. No auto-apply, no auto-PR.
2. **The opportunity record** — enumerate the **nine `improvement_type` values** (the exact
   enum in `schemas/domain-improvement.schema.json`): `missing_severity_clause`,
   `missing_crown_jewel`, `missing_attacker_position`, `missing_trust_boundary`,
   `missing_consequential_action`, `missing_immutability_class`, `missing_data_class`,
   `missing_common_pattern`, `missing_regulatory_anchor` — and the fields (`target_pack`,
   `target_file`, `priority`, `source` = deterministic vs judgment, `evidence`,
   `draft_snippet`).
3. **`target_pack` attribution under multi-domain** — which pack an opportunity edits when
   several packs are active (deterministic deltas key off the run's `domains`; the auditor
   attributes per-pack).
4. **Read → Draft → Review → Apply & re-validate** — the `draft-domain-improvements`
   command, its filters, the temp-copy `validate-domain` + `build-domain-skill` gate,
   drop-on-fail, and the minimal line-anchored diff.

## Surgical fixes

1. **`apd-orchestrator` → workflow runner** in the three user-facing docs that still cite
   the retired deprecation shim: `docs/architecture.md` (the coordinator line),
   `docs/running-the-gauntlet.md` (the "invoke the apd-orchestrator agent" step), and
   `README.md`. The deterministic `.claude/workflows/apd-gauntlet.js` runner replaced it.
2. **CLI-reference refresh** in `docs/running-the-gauntlet.md`: add the newer subcommands
   missing from the list — `draft-domain-improvements`, `domain-coverage-delta` — and
   verify the synthesis subcommands (`rollup`, `cluster-candidates`, `apply-clusters`,
   `audit-report`) are represented; note that `build-domain-skill` and `validate-domain`
   accept **multiple packs**.
3. **Multi-domain run example** in `docs/running-the-gauntlet.md` Step 1: show
   `--domain pbm --domain api-security` producing `domains: [pbm, api-security]`.

## Acceptance bar

1. Both authoring guides are complete and their `agentic-ai` examples match the pack on
   `main` (file names, crown-jewel keys, the `**Pattern:**` format).
2. Zero `apd-orchestrator` references remain in user-facing docs (`docs/*.md` + `README.md`);
   the `running-the-gauntlet.md` CLI reference includes `draft-domain-improvements`.
3. `markdownlint-cli2` is clean on the full CI glob.
4. A small staleness-guard pytest (`tests/test_doc_domain_pack_authoring.py`, mirroring
   Subsystem B's `tests/test_doc_improving_domain_packs.py`) asserts: no `apd-orchestrator`
   in `docs/*.md` + `README.md`; the CLI reference lists `draft-domain-improvements`; the
   authoring guide references the `agentic-ai` pack and enumerates the nine
   `improvement_type` values in the improvement guide.
5. CI green (the existing suite plus the new guard test; `markdownlint`; `lint-agents`;
   `validate-example`).

## References

- The `agentic-ai` pack on `main` (`domains/agentic-ai/`) — the worked example.
- `docs/superpowers/specs/2026-05-31-agentic-ai-domain-pack-design.md` — the pack design
  (severity modifiers, the three resolutions, the mapping discipline) the guide teaches.
- `docs/superpowers/specs/2026-05-30-multi-domain-runs-design.md` (Subsystem A) and
  `docs/superpowers/specs/2026-05-30-domain-improvement-capture-design.md` (Subsystem B) —
  the mechanics the guides document.
- `tests/test_doc_improving_domain_packs.py` — the doc-test pattern to mirror.
