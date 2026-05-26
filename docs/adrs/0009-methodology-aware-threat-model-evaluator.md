# ADR-0009: Methodology-Aware Threat Model Evaluator

**Status:** Accepted
**Date:** 2026-05-26
**Supersedes:** —
**Superseded by:** —

## Context

Practitioners produce threat models in a variety of shapes: STRIDE-per-element
spreadsheets, LINDDUN privacy analyses, attack trees, narrative PASTA reports,
free-form whiteboard captures. v1.1's `apd-intake` agent catalogs whatever
threat-model artifact appears in the run inputs and surfaces it as evidence
pointers to downstream specialists — but does not formally evaluate it against
the specialists' own findings.

The Phase B design spec calls for full methodology-aware evaluation: the
gauntlet should parse the threat model into a normalized graph, then compare
that graph against the dedup'd specialist findings to identify (a) coverage
gaps (TM omits analysis a specialist flagged as relevant), (b) contradictions
(TM asserts a mitigation a specialist showed broken), and (c) silences (TM
says nothing about a surface a specialist flagged).

The goal is to give operators a single output that tells them how well their
threat model holds up against the gauntlet's deeper analysis — without
generating threats the operator didn't think of (that would make the gauntlet
into a threat-model author, not a threat-model reviewer).

## Decision

Adopt a **two-agent split** parallel to v1.1's `apd-code-recon`:

1. **`apd-threat-model-recon`** (tier-0, activation-gated): parses the
   supplied artifact into `00-context/threat-model-normalized.yaml`. Pure
   context-builder; emits no findings.

2. **`apd-threat-model-evaluator`** (tier-4, activation-gated): consumes the
   normalized graph + dedup'd specialist findings/capabilities; emits three
   finding flavors (coverage gap, contradiction, silence) using the existing
   `finding.schema.json` with `agent: threat_model_evaluator` and id prefix
   `tmeval-`. Also emits a per-surface coverage report
   (`40-synthesis/threat-model-coverage-report.md` + machine-readable
   `40-synthesis/threat-model-coverage.yaml`).

**Native methodology support:**

- **STRIDE** — OWASP Threat Dragon JSON, Microsoft TMT `.tm7` (XML),
  STRIDE-per-element Markdown/CSV tables
- **LINDDUN** — Markdown/CSV tables with column-position disambiguation for
  letter overloading
- **Attack tree** — indented prose, ADTool XML, JSON

**Reduced-fidelity support:** PASTA, VAST, Trike, free-form prose. The recon
agent's LLM does extraction; entries are marked `extraction_confidence: low`.

**Discipline:**

- **Never invent threats.** Parser output defines the entry set; the recon
  agent enriches but does not add. Free-form extraction respects what the
  operator wrote.
- **Comparator-only.** The evaluator never generates threats the TM didn't
  contain. It only compares the TM against specialist findings.
- **Confidence cascading.** Low-confidence TM entries (from free-form prose)
  can produce silence findings but never contradictions.
- **Block-on-ambiguity.** Unparseable TMs produce a single blocked finding,
  not a fabricated assessment.

**Parsing architecture:** Python parser modules (one per supported format) at
`tools/apd_gauntlet/threat_model/` handle deterministic structural parsing.
The CLI subcommand `apd-gauntlet parse-threat-model` wraps them with
auto-detection and schema validation. The recon agent invokes the CLI and
then performs semantic enrichment (ATT&CK technique refinement, APD-goal
mapping, free-form LLM extraction when the parser couldn't extract anything).

**Methodology→APD-goal mapping** has two co-equal sources of truth:

- `tools/apd_gauntlet/threat_model/mappings.py` (Python; authoritative for
  parser code)
- `apd-threat-model-methodologies` skill (markdown; authoritative for agent
  reasoning)

Both must change together when the canonical mapping evolves.

## Alternatives considered

### Passive inventory only

**Rejected.** This is essentially the v1.1 status quo (intake catalogs the
TM as evidence; nothing evaluates it). It would not produce the
coverage/contradiction/silence findings that motivated the design spec. The
operator's threat model would remain inert relative to the rest of the
gauntlet's analysis.

### Coverage + contradiction + active augmentation

**Rejected.** "Active augmentation" would have the gauntlet propose
additional threats beyond what the TM author wrote — using the specialist
findings as a corpus and emitting "the TM should have included X." This
crosses the line from threat-model *reviewer* to threat-model *author*. It
also risks the gauntlet's threat brainstorming becoming the authoritative
list, undermining the original TM author's process. Comparator-only
preserves the boundary.

### Single-agent design

**Rejected.** Combining recon + evaluator into one agent would lose the
parallel with `apd-code-recon`, conflate two distinct concerns (parsing vs
evaluation), and make the recon output less reusable by specialists in
tiers 1-3 (who consume the normalized YAML as evidence). The two-agent
split also makes the activation contracts clearer: recon activates when a
TM exists; evaluator activates when normalized TM exists.

### LLM-only parsing (no Python parsers)

**Rejected.** LLM extraction of structured formats (JSON, XML, tables) is
non-deterministic and unverifiable. Python parsers are deterministic,
testable, and produce auditable `source_locator` fields. The LLM contributes
where its strength is real: free-form prose extraction and semantic
enrichment of structured output.

## Consequences

### Additive within v1.x

All schema changes are additive (new optional fields on `run-config.schema.json`;
new enum value + id-pattern extension on `finding.schema.json`; two entirely
new schemas). v1.2-format runs validate unchanged against v1.3 schemas. PBM
domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0 with no
changes.

### Two new agents

Agent count grows from 13 (v1.2) to 15 (v1.3). Both new agents are optional
(activation-gated) so the minimum-viable run with no `threat_model:`
declaration produces identical output to v1.2.

### New Python dependency

`lxml>=4.9` for XXE-safe parsing of `.tm7` and ADTool XML. Adds a compiled
extension to the install; documented in pyproject.toml.

### Co-equal mapping tables

The canonical STRIDE/LINDDUN→APD-goal tables live in BOTH the Python module
and the skill markdown. This is a deliberate trade-off: a single source of
truth would mean either (a) generating the skill from the Python module
(complex build step) or (b) the Python parsers parsing the skill markdown
at import time (fragile). Two-sourced-but-co-equal is the v1.3 choice; a
future Phase or polish-pass may add a build step to derive the skill from
the Python module.

### New skill `apd-threat-model-methodologies`

Skill count grows from 5 (v1.2) to 6 (v1.3). Required reading for both new
agents.

### Reference data not required

Parsers are pure code with no upstream data dependency. No new
`apd-gauntlet refresh-*` subcommand is needed.

### Validator extensions

Two new per-record checks for `tmeval-` findings (evidence pointer required,
contradiction cross-reference required). Adds to Phase A's D3FEND cross-ref
check pattern.

### Free-form handling is intentionally limited

PASTA / VAST / Trike are accepted but produce low-confidence entries that
can't drive contradictions. Operators who use these methodologies should
either re-express the threats in a supported structured format or accept
that contradictions won't fire for their TM. Future phases may add native
parsers for the more common narrative formats.
