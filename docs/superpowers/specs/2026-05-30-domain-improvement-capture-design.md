# APD Gauntlet Domain-Improvement Capture & Draft Design

- **Date:** 2026-05-30
- **Status:** Approved (design); implementation plan pending
- **Author:** brainstormed with Claude Code
- **Scope:** A gauntlet run reveals where the active domain pack(s) are
  *incomplete* — a harm with no matching severity clause, a crown jewel present
  in the asset inventory but declared by no selected pack, a consequential action
  not enumerated. This subsystem **captures** those gaps as typed, pack-attributed
  *domain-improvement opportunities* on every run (advisory, non-blocking, cheap),
  and provides an **on-demand** CLI command that turns chosen opportunities into a
  validated, reviewable, `git apply`-able patch against `domains/<pack>/`. Two
  clean halves: NOTICE (automatic, every run) and ACT (author-triggered). No
  auto-PR, no auto-edit of packs.
- **Subsystem:** B (of the domain-system evolution). Subsystem A
  (`docs/superpowers/specs/2026-05-30-multi-domain-runs-design.md`) already wired
  B's first trigger condition — a harm matching **no** severity-rubric clause in
  **any** selected pack is recorded as a domain-improvement-opportunity candidate
  (A §7; `.claude/skills/apd-evidence-discipline/SKILL.md` severity section). This
  spec builds the capture artifact, the new `apd-domain-auditor` agent, the
  advisory workflow phase, and the `draft-domain-improvements` command that A only
  promised.

## 1. Problem / Context

The gauntlet's analytic quality is bounded by its domain calibration. A specialist
agent cites the active pack's severity rubric
(`domains/<pack>/severity-rubric.md`), its consequential-action surface
(`consequential-actions.md`), its immutability classes
(`immutability-classes.md`), its data taxonomy (`data-taxonomy.md`), and its
per-goal pattern library (`common-patterns/<goal>.md`). When a real solution
exercises a harm, an asset class, an audit-worthy action, or a regulatory regime
that the loaded pack(s) do **not** describe, three bad things happen silently:

1. The specialist either over-blocks (`disposition: blocked`, "no clause matched")
   or guesses a severity it cannot defend against a cited clause — both degrade the
   report.
2. The pack stays incomplete forever, because nothing records *which* clause was
   missing or *which* pack should grow.
3. Subsystem A (multi-domain) made this worse, not better: a blended `pbm` +
   `api-security` run now means "no clause in **any** selected pack," so the union
   of packs is what a gap is measured against, and a gap must be **attributed** to
   the best-fit pack before an author can act on it.

Today the only artifact of such a gap is prose in a finding's `detail` field (A §7)
or a `disposition: blocked` finding — neither is typed, neither is pack-attributed,
neither is actionable, and neither survives the synthesis dedup/rollup as a
first-class object. The original A design explicitly deferred "the capture
mechanism is Subsystem B" (A §7, §13) and noted that "documentation should include
guidance on how to do this." B closes both.

The run already produces, by the time synthesis settles, exactly the corpus needed
to detect these gaps deterministically *and* by judgment:

- `00-context/asset-inventory.yaml` — the run's concrete assets, identities, and
  trust boundaries, each `provenance.source`-tagged
  (`artifact | domain_default | threat_model | code_evidence`;
  `schemas/asset-inventory.schema.json`).
- `40-synthesis/deduped-findings.yaml` — the settled, deduped specialist corpus,
  including the apath-`*` / tmeval-`*` tier-4 findings (after A's Gap-1 reorder,
  tmeval + apath now precede the rollup, so the corpus is fully settled before
  closeout; `.claude/workflows/apd-gauntlet.js` Phase 5.5/5.6).
- The merged `apd-domain` skill (`.claude/skills/apd-domain/SKILL.md`) — the union
  of every selected pack's surfaces and prose, with the per-pack provenance headers
  A introduced (`## Domain: <pack> — Source: <file>`) and the
  `## Domain attack-path defaults (merged across packs)` surface section.
- Each `domains/<pack>/domain.yaml` — the structured `crown_jewels`,
  `attacker_positions`, `default_trust_boundaries`, and `regulatory_anchors`
  declarations (`schemas/domain.schema.json`).

B reads that corpus, produces one typed artifact, and stops there for the NOTICE
half. The ACT half is a separate, deterministic CLI command the author runs when
they choose to.

## 2. Goals / Non-Goals

**Goals**

- **Capture every run, cheaply and non-blockingly.** A new advisory phase emits
  `40-synthesis/domain-improvements.yaml` after the audit loop and before closeout.
  It never gates the run, never touches the HTML report, and emits an
  empty-but-schema-valid artifact when there are no opportunities.
- **Hybrid capture.** A deterministic Python pre-pass computes mechanical coverage
  deltas (asset-inventory vs. the union of pack declarations); a thin LLM agent
  (`apd-domain-auditor`) reads those candidate signals plus the settled findings and
  the merged skill, harvests prose-judgment opportunities, assigns each a best-fit
  `target_pack`, and **drafts a paste-ready `draft_snippet` at capture time**. Both
  feed one artifact.
- **Typed, pack-attributed, evidence-disciplined records.** Each opportunity is a
  `domain-improvement` record with a deterministic `dimpr-<sha8>` id, one of nine
  `improvement_type`s, a `target_pack` + `target_file`, an `evidence[]` array that
  cites a **real** run signal (a finding id or an asset-inventory id —
  `asset_id` / `identity_id` / `boundary_id` — never invented, same discipline as
  findings), and a `draft_snippet`.
- **On-demand, deterministic drafting.** `apd-gauntlet draft-domain-improvements
  <run>` inserts each chosen opportunity's `draft_snippet` into the right pack file
  **in a temp copy** of `domains/`, runs `validate-domain` + `build-domain-skill` to
  prove the edited pack stays schema-valid and rebuildable, **drops** any snippet
  that fails (reporting it), and emits a unified, `git apply`-able diff. The LLM does
  judgment + drafting **once**, at capture; the on-demand path is pure
  insert → validate → diff.
- **Author documentation.** A new `docs/improving-domain-packs.md` triage guide plus
  a pointer from `docs/adapting-to-other-domains.md`, satisfying A's deferred
  "documentation should include guidance."

**Non-Goals**

- **No auto-PR.** A `--open-pr` wrapper over the patch is explicitly deferred
  (§11). B stops at a reviewed local diff.
- **No auto-apply / no closed loop.** B never edits a real pack file and never
  re-runs the gauntlet against the improved pack. The output is a patch for a human
  to review and `git apply`.
- **No new finding semantics.** B does not change the nine APD goals, the
  finding/capability schema semantics, the NIST/ATT&CK/D3FEND mapping guidance, or
  the evidence-discipline rules. The `disposition` enum stays
  `[gap, risk, uncertainty, blocked]`; pack-improvement is **not** a finding
  disposition (decided in §4 / §10).
- **No HTML-report change.** `report-data.yaml` is `additionalProperties: false`
  and serves engineering review, not pack authoring. B is a side channel; it does
  not migrate the report schema or template (§8).
- **No broader authoring-doc overhaul.** B adds only the improvement-triage guide;
  the larger domain-pack authoring-doc refresh is a separate effort (§11).
- **No new domain packs.** The repo ships four packs (`domains/`: `api-security`,
  `identity-security`, `pbm`, `security-tooling`); B's tests primarily validate
  against `pbm` + `api-security`, but any test fixture that globs `domains/`
  wholesale must tolerate all four. B authors no new packs.

## 3. Decisions (resolved during brainstorming)

| Decision | Choice |
|---|---|
| Capturer architecture | **Hybrid** — a deterministic Python pre-pass computes mechanical coverage deltas; a thin `apd-domain-auditor` LLM agent harvests prose-judgment candidates + holistic opportunities. Both feed ONE artifact. |
| Loop depth | **Capture + auto-drafted pack diff** — a reviewable patch for the author; never auto-merged, never auto-applied. |
| Delivery | **Capture per-run** (advisory `40-synthesis/domain-improvements.yaml`); **draft on-demand** via a CLI command that emits a validated, `git apply`-able patch. No auto-PR (deferred). |
| Where judgment runs | **Once, at capture.** The agent drafts every `draft_snippet` at capture time. The on-demand path is pure Python: insert → `validate-domain` → `build-domain-skill` → diff. |
| `dimpr-` id prefix | **NEW prefix lives ONLY in the new schemas** (`domain-improvement.schema.json` / `-doc`). It is **NOT** added to `finding.schema.json` id / `cross_references` / `merged_from` patterns. Improvement records are never findings, are never cross-referenced as findings, and never enter `_iter_records` (which globs only `*.findings.yaml` / `*.capabilities.yaml`). See §4 / §10. |
| Capture phase placement | **New advisory, NON-BLOCKING phase AFTER 5g audit and BEFORE closeout.** Reads the settled corpus; never gates the run; emits an empty-but-valid artifact when no opportunities found. |
| Multi-domain attribution | An item is an opportunity only if **no** selected pack already covers it (union check, deduped by key). `target_pack` is assigned by best domain-fit (LLM); the deterministic pre-pass proposes the run's **primary/first** domain as the default. |
| Surfacing | **Side channel** — standalone `domain-improvements.yaml` + a one-line closeout summary. NOT added to `report-data.yaml`/HTML. |
| Empty-run behavior | Emit a schema-valid empty artifact (`{schema_version: 1, generated_by: domain-auditor, examined_domains: [...], improvements: []}` — `examined_domains` is always present so the artifact stays self-describing, §4.2); the closeout summary says "0 opportunities." |
| `dimpr-` id derivation | A **NEW** dedicated helper `compute_improvement_id(...)` (§4.1 / §7.4) — **not** a call to or a mirror of `compute_id`, whose signature is `(prefix, title, first_locator)` over a 2-field `title\|locator` payload with no lowercasing. The dimpr key is the **lowercased**, `\|`-joined 4-tuple `improvement_type\|target_pack\|target_file\|evidence[0].ref`. |

## 4. Data model

Two new schemas in `schemas/`: a per-record schema and an array-wrapper "doc"
schema, following the two-file record/doc split used across the synthesis rollups
(e.g. `nist-coverage.schema.json` + `nist-coverage-doc.schema.json`). **Note on the
wrapper envelope:** unlike the bare coverage-rollup `-doc` wrappers (which require
only their array key, e.g. `required: ["controls"]`, with no envelope fields), the
`domain-improvements-doc` wrapper intentionally follows the
`asset-inventory` / `report-data` *self-describing* envelope style —
`schema_version` + `generated_by` + an `examined_domains` provenance list — so the
on-demand `draft-domain-improvements` command and the author can read the artifact's
provenance without the run context (§4.2). It is therefore **not** a byte-for-byte
mirror of the coverage `-doc` wrappers; an implementer copying a coverage `-doc` as
a template would produce a non-conforming file.

**Note on the `source` field.** The record carries a `source`
(`deterministic | judgment`) discriminator that is **not** in the approved design's
enumerated record-field list. It is a deliberate addition: it lets the author triage
mechanical vs. interpretive opportunities and lets the §12 pre-pass test assert that
deterministic candidates are tagged `deterministic`. The record deliberately omits a
`schema_version` field (the doc wrapper carries it, matching the synthesis
rollup-row pattern where the row schema has no `schema_version`); this differs from
the *finding* record (which carries `schema_version: const 1`) by design.

### 4.1 `schemas/domain-improvement.schema.json` (the record)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvement.schema.json",
  "title": "APD Gauntlet Domain-Improvement Opportunity",
  "type": "object",
  "required": [
    "id", "improvement_type", "target_pack", "target_file",
    "source", "priority", "evidence", "rationale",
    "suggested_action", "draft_snippet"
  ],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "string", "pattern": "^dimpr-[0-9a-f]{8}$" },
    "improvement_type": {
      "type": "string",
      "enum": [
        "missing_crown_jewel",
        "missing_attacker_position",
        "missing_trust_boundary",
        "missing_severity_clause",
        "missing_consequential_action",
        "missing_immutability_class",
        "missing_data_class",
        "missing_regulatory_anchor",
        "missing_common_pattern"
      ]
    },
    "target_pack": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
    "target_file": {
      "type": "string",
      "enum": [
        "domain.yaml",
        "severity-rubric.md",
        "consequential-actions.md",
        "immutability-classes.md",
        "data-taxonomy.md",
        "common-patterns/confidentiality.md",
        "common-patterns/integrity.md",
        "common-patterns/availability.md",
        "common-patterns/distributed.md",
        "common-patterns/resilient.md",
        "common-patterns/ephemeral.md",
        "common-patterns/authenticity.md",
        "common-patterns/non-repudiation.md",
        "common-patterns/immutability.md"
      ]
    },
    "apd_goal": {
      "type": "string",
      "enum": [
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability"
      ]
    },
    "source": { "type": "string", "enum": ["deterministic", "judgment"] },
    "priority": { "type": "string", "enum": ["high", "medium", "low"] },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["kind", "ref"],
        "additionalProperties": false,
        "properties": {
          "kind": { "type": "string", "enum": ["finding", "asset_inventory"] },
          "ref": { "type": "string", "minLength": 1 },
          "note": { "type": "string", "minLength": 1, "maxLength": 280 }
        }
      }
    },
    "rationale": { "type": "string", "minLength": 20 },
    "suggested_action": { "type": "string", "minLength": 10 },
    "draft_snippet": { "type": "string", "minLength": 1 },
    "insertion_hint": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "yaml_path": { "type": "string", "minLength": 1 },
        "markdown_section": {
          "type": "object",
          "additionalProperties": false,
          "required": ["level", "text"],
          "properties": {
            "level": { "type": "integer", "minimum": 1, "maximum": 6 },
            "text": { "type": "string", "minLength": 1 }
          }
        }
      }
    }
  },
  "allOf": [
    {
      "comment": "missing_common_pattern requires apd_goal so the target_file goal is named.",
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" } } },
      "then": { "required": ["apd_goal"] }
    },
    {
      "comment": "missing_common_pattern: apd_goal must match the common-patterns/<goal>.md target_file. apd_goal uses underscores (non_repudiation); the filename uses hyphens (non-repudiation.md). Each branch pins one goal const to its hyphenated file const.",
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "confidentiality" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/confidentiality.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "integrity" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/integrity.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "availability" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/availability.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "distributed" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/distributed.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "resilient" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/resilient.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "ephemeral" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/ephemeral.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "authenticity" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/authenticity.md" } } }
    },
    {
      "comment": "non_repudiation (underscore) -> non-repudiation.md (hyphen).",
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "non_repudiation" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/non-repudiation.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "immutability" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/immutability.md" } } }
    }
  ]
}
```

The nine per-goal `if/then` branches above bind `apd_goal` ↔ `target_file` for
`missing_common_pattern` so a self-contradictory record (e.g.
`apd_goal: confidentiality` + `target_file: common-patterns/integrity.md`) is
rejected at schema-validation time. They also pin the single underscore→hyphen
normalization the rest of the system must honor: **`non_repudiation` (the
`apd_goal` enum value, matching `finding.schema.json`) maps to the on-disk file
`common-patterns/non-repudiation.md`.** §6.3's `draft.py` resolves the file from
`apd_goal` via this exact rule (replace `_`→`-` only for the `non_repudiation`
case; all other goals are spelled identically in enum and filename).

**Field-by-field semantics**

- `id` — deterministic `dimpr-<sha8>`, computed by a **NEW dedicated helper**
  `compute_improvement_id(improvement_type, target_pack, target_file, primary_ref)`
  added to `tools/apd_gauntlet/linters.py`. This is **not** a call to, and does
  **not** mirror, the existing `compute_id(prefix, title, first_locator)` — that
  helper hashes a fixed 2-field `f"{title}|{first_locator}"` payload with **no**
  lowercasing and a different signature, so it cannot produce the dimpr id.
  Likewise `check_domain_improvement_id` is **not** a thin mirror of
  `check_finding_id`, which early-returns unless `record['agent']` is in
  `_PREFIX_BY_AGENT` (improvement records have no `agent` field). The exact,
  verbatim algorithm — the single source of truth the agent (§7.2 step 5) and the
  linter (§7.4) both call:

  ```python
  primary_ref = record["evidence"][0]["ref"]   # the FIRST evidence ref, exactly
  key = "|".join([improvement_type, target_pack, target_file, primary_ref]).lower()
  digest = hashlib.sha256(key.encode()).hexdigest()[:8]
  id = f"dimpr-{digest}"
  ```

  `primary_ref` is **always `evidence[0].ref`**. For a deterministic opportunity
  that ref is the asset/identity/boundary **id** the pre-pass supplied
  (`{kind: asset_inventory, ref: <asset_id>}`, e.g. `asset-1a2b3c4d`) — the same
  schema-pattern'd id the §4.3 cross-ref validator resolves against, **never** a
  free-form `provenance.locator`. For a judgment opportunity it is the first cited
  finding id (e.g. `conf-9f8e7d6c`). Because the id key, the `evidence[].ref`
  semantics (below), and the §4.3 resolver all key off the same value, the id is
  reproducible across re-runs and dedups identical opportunities from the
  deterministic and judgment halves (same `improvement_type|target_pack|target_file|ref`
  collapses to one id). The linter `check_domain_improvement_id` (§7.4)
  re-computes via the **same helper** and flags any mismatch.
- `improvement_type` — one of the nine taxonomy values (§5). Drives
  `target_file` and the `draft_snippet` shape.
- `target_pack` — the best-fit pack name (the LLM's domain-fit judgment;
  deterministic items default to the run's primary/first domain). Must be one of
  the run's `args.domains` (the on-demand command verifies the pack dir exists,
  §6.4).
- `target_file` — the exact pack file the snippet edits, constrained to the known
  pack file set (`domains/<name>/` layout: `domain.yaml`, the four calibration
  `.md` files, and the nine `common-patterns/<goal>.md`).
- `apd_goal` — optional in general; **required** for `missing_common_pattern`
  (names which `common-patterns/<goal>.md` is targeted, and the schema's per-goal
  `allOf` binds it to the matching `target_file`). It is **optional but
  encouraged** for `missing_severity_clause` when the agent can attribute the harm
  to a goal — the schema does **not** require it there, matching the single
  `missing_common_pattern` conditional in the `allOf` block. It is absent for
  structural `domain.yaml` items.
- `source` — `deterministic` (pre-pass) or `judgment` (agent). Lets the author
  triage mechanical vs. interpretive opportunities and lets tests assert the
  pre-pass emits `deterministic`.
- `priority` — `high | medium | low`. Deterministic items default `medium`
  (a present-but-undeclared crown jewel with `provenance.source: artifact` is
  `high`); judgment priority is the agent's call, justified in `rationale`.
- `evidence[]` — **the run signal that revealed the opportunity, never invented.**
  Each item is `{kind, ref, note?}`. `kind: finding` ⇒ `ref` is a real finding id
  present in the run corpus (e.g. a `disposition: blocked` "no clause matched"
  finding, or a tmeval "not enumerated" finding); `kind: asset_inventory` ⇒ `ref`
  is **always** one of the schema-pattern'd ids `asset_id` / `identity_id` /
  `boundary_id` from `00-context/asset-inventory.yaml` — **never** a
  `provenance.locator` (which is optional and free-form, and would not resolve
  through the §4.3 cross-ref check). A `provenance.locator` may be carried only as
  optional context in `note`, never as `ref`. This is the same evidence-pointer
  discipline the finding schema enforces; the validator cross-checks these refs
  against the real ids (§4.3 / §7).
- `rationale` — why this is a real gap (what the run exercised that the pack does
  not describe).
- `suggested_action` — one-line human instruction ("add a `payment_methods_store`
  crown jewel to `api-security/domain.yaml`").
- `draft_snippet` — **paste-ready content** drafted by the agent at capture time:
  for `domain.yaml` targets, a YAML list-item block (`- pattern: …` /
  `- position: …` / `- boundary: …` / a `regulatory_anchors` string) ready to
  append under the right key; for `.md` targets, a markdown clause/section ready to
  append to the right section. The on-demand command inserts this verbatim into a
  temp copy (§6).
- `insertion_hint` — optional structured hint the on-demand command uses to choose
  the insertion point deterministically: `yaml_path` (e.g.
  `crown_jewels`, `attacker_positions`, `default_trust_boundaries`,
  `regulatory_anchors`) for `domain.yaml` targets; `markdown_section` for `.md`
  targets — a **level-qualified anchor** `{level: <int 1–6>, text: <exact heading
  text>}` (e.g. `{level: 2, text: "High"}`), required because heading text recurs
  across levels in the real packs (§6.3). When absent — or on zero/multiple matches
  at the requested level — the command falls back to the deterministic EOF append
  rule in §6.3.

### 4.2 `schemas/domain-improvements-doc.schema.json` (the array wrapper)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvements-doc.schema.json",
  "title": "APD Gauntlet Domain-Improvements Document",
  "type": "object",
  "required": ["schema_version", "generated_by", "examined_domains", "improvements"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["domain-auditor"] },
    "examined_domains": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" }
    },
    "improvements": {
      "type": "array",
      "items": { "$ref": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvement.schema.json" }
    }
  }
}
```

`examined_domains` is a **required** field: it records the run's `args.domains` so
the artifact is self-describing for the on-demand command and the author, and so
the §6.4 unknown-target_pack guard and the §7.2 step 7 self-check
(`every target_pack is in examined_domains`) always have a populated authority to
check against. An artifact omitting it is rejected at schema-validation time. An
empty run still emits `examined_domains: [...]`:
`{schema_version: 1, generated_by: domain-auditor, examined_domains: [...],
improvements: []}` — schema-valid, `improvements` empty.

The `improvements[].items` `$ref` uses the **full absolute `$id` URI**
(`https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvement.schema.json`),
matching the five existing `-doc` wrappers (`nist-coverage-doc` et al.) and
resolving through `validate.build_registry()` (which indexes every
`schemas/*.schema.json` by its absolute `$id`, not by relative filename). A bare
relative `$ref: "domain-improvement.schema.json"` would **not** resolve against
that `$id`-keyed registry and would error on every non-empty doc — so the absolute
form is load-bearing, not cosmetic.

### 4.3 Validate wiring

`tools/apd_gauntlet/validate.py`, `SYNTHESIS_ROLLUPS` dict — add one entry so the
existing `_validate_synthesis_rollups` walker schema-validates the artifact exactly
as it validates `nist-coverage.yaml` et al.:

```python
"domain-improvements.yaml":   "domain-improvements-doc.schema.json",
```

Because the doc wrapper's `improvements[].items.$ref` is the **full absolute `$id`
URI** of the record schema (§4.2), it resolves through the existing
`build_registry()` (which indexes every `schemas/*.schema.json` by its absolute
`$id`), so the doc wrapper validates each record against the record schema with no
further wiring. The artifact lives under `40-synthesis/`, so it is picked up by the
synthesis-dir walker; it is **not** added to `RECORD_KINDS` (it is not a
`*.findings.yaml` / `*.capabilities.yaml`) and therefore never enters
`_iter_records`, the semantic-pass finding/capability linters, or the
cross-file finding-id resolution. This is what keeps `dimpr-` out of
`finding.schema.json` (§4.4).

**One pass owns the improvements-doc walk: `run_cross_file_pass`.** A targeted
helper `_validate_domain_improvements_cross_refs` is added to `run_cross_file_pass`
(mirroring `_validate_report_data_cross_refs`) — the cross-file pass is the natural
home because it already holds the run corpus needed to resolve evidence refs. This
single helper does **both** of B's improvements-doc checks in one walk:

1. **Evidence-ref resolution:** for each improvement, every `evidence[].ref` with
   `kind: finding` must resolve to a real finding id in the run corpus, and every
   `kind: asset_inventory` ref must resolve to a real `asset_id` / `identity_id` /
   `boundary_id` in `00-context/asset-inventory.yaml`. A dangling ref is an ERROR —
   same evidence discipline as findings.
2. **`dimpr-` id recomputation:** it invokes the `check_domain_improvement_id`
   linter (§7.4) on each record. The id check does **not** run in
   `run_semantic_pass` (which globs only `*.findings.yaml` / `*.capabilities.yaml`
   via `_iter_records` — and the improvements artifact is neither). Both the id
   recomputation and the evidence-ref resolution live in this one cross-file
   helper; §7.4 reflects this.

### 4.4 The `dimpr-` prefix question — DECIDED

**Decision: `dimpr-` is added ONLY to the two new schemas. It is NOT added to
`finding.schema.json`'s `id`, `cross_references`, or `merged_from` patterns.**

Rationale, against the criterion in the approved design ("the finding ID prefix
regex must learn the `dimpr-` prefix only **if** these IDs are cross-referenced as
findings; otherwise `dimpr-` lives only in the new schema"):

- A domain-improvement record is **not** a finding. It has no `apd_tier`,
  `disposition`, `severity`, `confidence`, `control_mappings`, or `recommendation`
  — none of the finding-required fields — and none of the finding dispositions
  (`gap | risk | uncertainty | blocked`) describe "the pack should grow."
- Improvement records are **never** cross-referenced *as findings*. The reference
  direction is the reverse: an improvement *cites* a finding id in its
  `evidence[].ref` (so it points **into** the finding corpus, not the other way).
  No finding's `cross_references` / `merged_from` ever contains a `dimpr-` id,
  because findings are authored before B runs and B never edits them.
- The validator never feeds improvement records through the finding validator:
  the file matches no `RECORD_KINDS` glob, so `finding.schema.json`'s
  `additionalProperties: false` + required-field set would *reject* every
  improvement record if it ever did — which is the correct, fail-loud behavior and
  another reason to keep them separate.

Therefore the finding schema is left untouched. `dimpr-` is owned solely by
`domain-improvement.schema.json`. (If a future effort ever cross-links the two —
e.g. a finding that points at the improvement it spawned — that is a deliberate
schema change at that time, out of scope here.)

## 5. Improvement-type taxonomy (the nine signals)

Each type names a `target_file`, a capture mechanism (deterministic vs. judgment),
and a draft-snippet shape. The deterministic three derive from the asset-inventory
vs. pack-declaration delta; the six judgment types derive from cited findings.

| `improvement_type` | mechanism | `target_file` | signal source |
|---|---|---|---|
| `missing_crown_jewel` | **deterministic** | `domain.yaml` (`crown_jewels`) | an asset in `asset-inventory.yaml` with `provenance.source: artifact` that maps to no `crown_jewels[].pattern` in the union of selected packs |
| `missing_attacker_position` | **deterministic** | `domain.yaml` (`attacker_positions`) | an identity / trust-boundary in the inventory implying an attacker position declared by no pack |
| `missing_trust_boundary` | **deterministic** | `domain.yaml` (`default_trust_boundaries`) | a `trust_boundaries[]` entry in the inventory matching no `default_trust_boundaries[].boundary` in the union |
| `missing_severity_clause` | judgment | `severity-rubric.md` | A's wired no-clause-match note — a finding whose `detail` records "matched no severity-rubric clause in any selected pack" (A §7), or a `disposition: blocked` finding citing missing rubric coverage |
| `missing_consequential_action` | judgment | `consequential-actions.md` | a non-repudiation (`nonrep-*`) finding noting an audit-worthy action "not enumerated" in the consequential-action surface |
| `missing_immutability_class` | judgment | `immutability-classes.md` | an immutability (`immut-*`) finding noting a data class whose immutability is "not addressed" |
| `missing_data_class` | judgment | `data-taxonomy.md` | an intake/confidentiality finding noting data elements "not enumerated" in the data taxonomy |
| `missing_regulatory_anchor` | judgment | `domain.yaml` (`regulatory_anchors`) | a finding citing a regulatory regime no selected pack lists in `regulatory_anchors` |
| `missing_common_pattern` | judgment | `common-patterns/<goal>.md` | a recurring finding pattern (per `apd_goal`) absent from the pack's pattern library for that goal |

**Multi-domain rule.** An item is an opportunity only if **no** selected pack
already covers it (union check, deduped by key). The deterministic pre-pass
performs the union check mechanically (§5.1); the agent performs it for judgment
types by reading the merged `apd-domain` skill (which already concatenates every
pack's prose under `## Domain: <pack> — Source: <file>` headers, A §5).
`target_pack` is the LLM's best domain-fit; deterministic items default to the
run's primary/first domain (`args.domains[0]`).

**Deterministic vs. agent-keep semantics (the three deterministic types).** The
pre-pass *emits* a `missing_crown_jewel` / `missing_attacker_position` /
`missing_trust_boundary` **candidate**; the agent decides whether to keep it and
how to phrase the `rationale` / `draft_snippet`. Two rules pin this so "deterministic"
stays meaningful: (1) when the agent keeps a deterministic candidate, its `source`
**stays `deterministic`** even if the agent substantially rephrases the position or
boundary text — the source records *how the opportunity was detected*, not how it
was worded. (2) An agent-*dropped* deterministic candidate simply does not appear in
`domain-improvements.yaml`; it is not separately recorded (the durable trace is the
`domain-coverage-delta.yaml` candidate list, which the author can diff against the
emitted records if they want to see what the agent discarded).

**`apd_goal` ↔ `target_file` for `missing_common_pattern`.** Beyond the soft
"required" of §4.1's first `allOf` branch, the nine per-goal `allOf` branches (§4.1)
make the value pairing *enforceable* in JSON Schema, including the single
underscore→hyphen case (`non_repudiation` → `non-repudiation.md`). For the other
eight improvement types `apd_goal` is unconstrained against `target_file`.

### 5.1 Deterministic coverage-delta pre-pass algorithm

Command: `apd-gauntlet domain-coverage-delta <run_dir>` (new, in
`tools/apd_gauntlet/synthesis/`, e.g. `coverage_delta.py`, exposed via `cli.py`).
Pure Python, no LLM. Writes
`40-synthesis/domain-coverage-delta.yaml` — the candidate signal file the agent
reads. The algorithm:

1. **Load the run's selected packs.** Read `runs/<id>/.apd-run.yaml` →
   `args.domains` (a list, post-A hard cutover). For each pack name, load
   `domains/<name>/domain.yaml`.
2. **Build the declared union, deduped by key.** Over all selected packs:
   - `declared_crown_jewels` = set of `crown_jewels[].pattern` (lowercased).
   - `declared_positions` = set of `attacker_positions[].position` (lowercased).
   - `declared_boundaries` = set of `default_trust_boundaries[].boundary`
     (lowercased).
   This mirrors A §5 step 3 (surface union, dedup-by-key). Each declared key
   retains the contributing pack(s) for attribution.
3. **Load the run's asset inventory.** Read
   `00-context/asset-inventory.yaml`. If absent or empty-valid (`assets: []`),
   the pre-pass emits a delta file with empty candidate lists (no deterministic
   opportunities) and exits 0 — the empty-but-valid principle (§9).
4. **Crown-jewel delta.** For each `assets[]` entry whose
   `provenance.source == "artifact"` (i.e. grounded in a real run artifact, not a
   `domain_default` the pack itself injected), normalize its `name` to a candidate
   key (lowercase, non-alphanumeric → `_`, collapse repeats). If that key is **not**
   in `declared_crown_jewels` (exact or via a small synonym map seeded from the
   pack `pattern` vocabulary, e.g. `payment_methods_store` ~ `payment card data`),
   emit a `missing_crown_jewel` candidate. Its evidence ref is the schema-pattern'd
   id `{kind: asset_inventory, ref: <asset_id>}` (the value the §4.3 cross-ref
   check and the `dimpr-` id key both consume) — **never** the free-form
   `provenance.locator`, which is carried only as optional context. The candidate
   record is `{asset_id, name, data_classifications,
   provenance_locator (context only, not the ref), provenance.artifact,
   default_target_pack: args.domains[0]}`. Assets with
   `provenance.source in {domain_default}` are **excluded** — they originate from a
   pack declaration, so by definition they are already covered (no delta). Assets
   from `threat_model` / `code_evidence` are **included** (they are run-grounded,
   not pack-injected).
5. **Attacker-position delta.** For each `identities[]` entry and each
   `trust_boundaries[]` entry whose `provenance.source != "domain_default"`, derive
   the implied attacker position(s) (a small deterministic mapping:
   `identity_type: external_party` ⇒ an `external_*` position; a boundary crossing
   an external asset ⇒ a `*_to_*` ingress position). If the implied position key is
   not in `declared_positions`, emit a `missing_attacker_position` candidate. (This
   mapping is intentionally conservative — it only proposes a *candidate*; the agent
   decides whether to keep it, per the candidate/source rules in §5. A kept
   candidate's `source` stays `deterministic`; a dropped one simply does not appear
   in the emitted artifact.) The candidate's evidence ref keys off the
   schema-guaranteed `identity_id` / `boundary_id`
   (`{kind: asset_inventory, ref: <identity_id|boundary_id>}`), never the free-text
   `name`.
6. **Trust-boundary delta.** For each `trust_boundaries[]` entry whose
   `provenance.source != "domain_default"`, normalize `name` to a boundary key; if
   not in `declared_boundaries`, emit a `missing_trust_boundary` candidate carrying
   `{boundary_id, name, crosses}`, with evidence ref keyed off the schema-guaranteed
   `boundary_id` (`{kind: asset_inventory, ref: <boundary_id>}`), not the free-text
   `name`. (`provenance.locator`, if present, is optional context only.)
7. **Default priority.** A `missing_crown_jewel` from a
   `provenance.source: artifact` asset is `high`; everything else is `medium`. The
   agent may revise priority with justification.
8. **Write the delta file** `40-synthesis/domain-coverage-delta.yaml`:
   `{schema_version: 1, generated_by: coverage-delta, examined_domains: [...],
   declared_union: {crown_jewels: [...], attacker_positions: [...],
   trust_boundaries: [...]}, candidates: [ {improvement_type, source:
   deterministic, default_target_pack, evidence: [{kind: asset_inventory, ref:
   <id>}], asset_name, data_classifications?, crosses?} ]}`. Determinism: candidate
   order = inventory order then `improvement_type`; keys sorted; byte-stable for a
   given inventory + pack set. This file is validated by a small
   `domain-coverage-delta-doc.schema.json` added to `SYNTHESIS_ROLLUPS` (same
   wiring as §4.3) so a malformed delta is caught. That schema's shape:
   `required: [schema_version, generated_by, examined_domains, declared_union,
   candidates]`, `additionalProperties: false`; `schema_version: const 1`;
   `generated_by: enum ["coverage-delta"]`; `declared_union` an object with array
   members `crown_jewels` / `attacker_positions` / `trust_boundaries` (each
   `items: string`); `candidates` an array of objects with
   `required: [improvement_type, source, default_target_pack, evidence]` where
   `improvement_type` is the deterministic-three enum subset, `source: const
   "deterministic"`, and `evidence` items are `{kind: asset_inventory, ref}`. §12
   adds a valid/invalid schema test for this delta-doc alongside the record/doc
   tests.

The pre-pass produces **candidate signals only** — it does not draft snippets and
does not write `domain-improvements.yaml`. Its `missing_crown_jewel` /
`missing_attacker_position` / `missing_trust_boundary` candidates flow into the
agent, which materializes them into full `domain-improvement` records (adding
`rationale`, `suggested_action`, `draft_snippet`, computing the `dimpr-` id) and
merges them with its own judgment opportunities into the one artifact.

## 6. The on-demand draft command — `draft-domain-improvements`

`apd-gauntlet draft-domain-improvements <run_dir> [--out <patch-path>]
[--id <dimpr-…>]… [--type <improvement_type>]… [--target-pack <name>]…`

New command in `cli.py` backed by a new module
`tools/apd_gauntlet/synthesis/draft.py`. **Pure Python, deterministic** — the LLM
already did all judgment at capture. The command never edits a real pack file; it
operates on a temp copy and emits a diff. Default `--out` is
`<run_dir>/40-synthesis/domain-improvements.patch`.

### 6.1 Selection

Read `40-synthesis/domain-improvements.yaml`. Select the set to draft:

- No filter flags ⇒ all `improvements[]`.
- `--id dimpr-…` (repeatable) ⇒ only those records.
- `--type …` / `--target-pack …` (repeatable) ⇒ filter by `improvement_type` /
  `target_pack`.
- Empty selection (no improvements, or filters match none) ⇒ print
  "0 opportunities selected; nothing to draft" and exit 0 (no patch written). This
  is the no-opportunities path (§9).

### 6.2 Temp-copy workspace

The whole workspace is wrapped in a `tempfile.TemporaryDirectory()` (or an
equivalent `try` / `finally shutil.rmtree`), so the temp copy is **always** removed
on exit — including on the §6.5 internal-error exit path and on any mid-insert
exception (no `/tmp` leak across repeated author runs).
`shutil.copytree("domains/", <tmpdir>/domains)` populates it. **All edits happen in
the copy**; the real `domains/` tree is never written. The command orders selected
improvements deterministically by `(target_pack, target_file, dimpr-id)` (§6.6) and
processes them in that stable per-file order; **each snippet is inserted and
validated individually (§6.4)** so a failing snippet can be reverted without
affecting the others. (Grouping by file is only for stable ordering and the
per-file in-memory snapshot; it is **not** a batch insert.)

### 6.3 Insertion (per improvement)

First, the **path resolution** is escape-proof by construction: `target_pack`
matches `^[a-z][a-z0-9-]*$` (no `.`/`/`) and `target_file` is enum-constrained, so
no component can contain `/` or `..`. `draft.py` resolves
`<tmpdir>/domains/<target_pack>/<target_file>`; for `missing_common_pattern` the
`<target_file>` is derived from `apd_goal` via the §4.1 normalization rule
(`non_repudiation` → `non-repudiation.md`; all other goals spelled identically).
The §6.4 unknown-target_pack guard runs **before** any path join/open and checks
`<tmpdir>/domains/<pack>/domain.yaml` (the **copy**, not the live tree).

- **`domain.yaml` targets** (`missing_crown_jewel`, `missing_attacker_position`,
  `missing_trust_boundary`, `missing_regulatory_anchor`): load the YAML with
  **`yaml.safe_load`** (never full load — this blocks `!!python/object` and other
  tag injection in the agent-authored snippet). Parse the `draft_snippet` with
  `yaml.safe_load` as well, then **assert it is exactly one node of the expected
  shape for the target list**, and append it to the list named by
  `insertion_hint.yaml_path` (`crown_jewels` / `attacker_positions` /
  `default_trust_boundaries` / `regulatory_anchors`; default by `improvement_type`
  when the hint is absent):
  - For `crown_jewels` / `attacker_positions` / `default_trust_boundaries` the
    snippet must `safe_load` to a **single mapping (`dict`)** matching the item
    shape (`- pattern:` / `- position:` / `- boundary:`). A snippet that loads to a
    **list** (e.g. two `- pattern:` items) or a **scalar** is **rejected and
    dropped** (reason `snippet shape: expected one mapping`) — this keeps the
    invariant *1 improvement = exactly 1 list entry*, preserves the `dimpr-` dedup
    accounting, and (combined with the item schema's `additionalProperties: false`,
    enforced by the validate gate) blocks extra-key smuggling.
  - For `regulatory_anchors` the snippet is a **YAML scalar** (`items: string` in
    `domain.schema.json`); it must `safe_load` to a single `str` and is appended as
    a string element. This is the one list whose element is a scalar, distinct from
    the mapping-item append above; a snippet that loads to a mapping or list is
    dropped (reason `snippet shape: expected one string`).
  Re-dump with `yaml.safe_dump(..., sort_keys=False, default_flow_style=False,
  allow_unicode=True, width=4096)` — `allow_unicode=True` keeps em-dashes / `§` and
  other non-ASCII pack content un-escaped (so the diff stays minimal and
  byte-stable), and the wide `width` prevents line-wrapping noise. If the target
  list does not yet exist in `domain.yaml`, create it.
- **`.md` targets** (the four calibration files and `common-patterns/<goal>.md`):
  insertion is **level-aware**, not bare heading-text match (heading text recurs in
  the real packs — e.g. `severity-rubric.md` has both a `## Critical` data-axis H2
  and a `### Critical (clinical patient-harm)` H3; appending under the wrong
  boundary silently mis-files the clause). The `insertion_hint.markdown_section` is
  therefore a level-qualified anchor `{level: <int>, text: <exact heading text>}`.
  The command matches the **first** heading at that exact level with that exact
  text and inserts **immediately before the next heading of level ≤ the matched
  level, else at EOF**. On **zero matches OR multiple matches** at the requested
  level, the command does **not** guess: it falls back to appending under a
  generated `## Captured improvement (<dimpr-id>)` heading at EOF and records the
  fallback (the mis-targeting) in `dropped[]`-adjacent `retargeted[]` notes and the
  stdout summary so the author sees it. A single blank line separates the appended
  block from prior content, and the written file is **normalized to end in exactly
  one trailing newline** (so the `\ No newline at end of file` diff edge never
  arises — see §6.5).
- **New-file `.md` targets.** A `missing_common_pattern` may target a
  `common-patterns/<goal>.md` the pack does not yet ship. (All nine goal files ship
  by default in `pbm` / `api-security`, so this is rare in practice, but the command
  handles it.) Creating a new pattern file is a **coupled edit**: the new file alone
  is invisible to `build-domain-skill` (it globs `meta['includes']`), so `draft.py`
  **also** appends the include glob (e.g. `common-patterns/<goal>.md`, if not
  already covered by an existing `common-patterns/*.md` include) to the same pack's
  `domain.yaml` in the temp copy, and the §6.4 validate+build gate runs over the
  coupled pair. The §6.5 diff then carries a proper new-file hunk (see §6.5). If the
  pack's `includes` already globs `common-patterns/*.md`, only the new file is
  created (no `domain.yaml` edit needed).

### 6.4 Per-improvement gate + drop-on-fail

**Pre-condition guards (before any insertion, in this order):**

1. **Unknown target_pack.** Check `(<tmpdir>/domains/<target_pack>/domain.yaml)`
   exists on the **temp copy** (not the live tree). Because `target_pack` matches
   `^[a-z][a-z0-9-]*$` and `target_file` is enum-constrained, no escaping path can
   reach this point. If the pack dir/`domain.yaml` is absent (e.g. an attribution to
   a pack not authored locally yet), the improvement is dropped with reason
   `unknown target_pack`. This guard runs **before** the path is constructed/opened.
2. **Already-declared duplicate (domain.yaml types).** `domain.schema.json` has **no
   `uniqueItems`** on `crown_jewels` / `attacker_positions` /
   `default_trust_boundaries` / `regulatory_anchors`, and `build-domain-skill` does
   **not** de-dup, so the validate+build gate **cannot** distinguish "new and valid"
   from "duplicate and valid." `draft.py` therefore adds a cheap pre-insert
   duplicate check: normalize the snippet's `pattern` / `position` / `boundary` /
   anchor and, if the declared union for `<target_pack>` already contains it, **drop**
   the improvement with reason `already declared in <pack>` (a first-class drop
   reason, not a silent literal duplicate). (Adding `uniqueItems` to
   `domain.schema.json` would let `validate-domain` catch it too, but that is a
   broader schema change deferred here; noted as the tradeoff.)

**Per-improvement gate** — applied to each snippet **one at a time**, so a bad
snippet is isolated (a per-file pre-insertion snapshot is held in memory for the
revert):

1. **`domain.yaml`-target snippets** are gated by `validate-domain <target_pack>
   --domains-dir <tmpdir>/domains` (the same schema + include-resolution check
   `validate_domain_cmd` runs) **plus** the rebuild in step 3. `validate-domain`
   meaningfully gates these because it schema-validates `domain.yaml` against
   `domain.schema.json`.
2. **`.md`-target snippets** (the 5 `.md` types: `missing_severity_clause`,
   `missing_consequential_action`, `missing_immutability_class`,
   `missing_data_class`, `missing_common_pattern`) are **NOT** gated by
   `validate-domain` — `validate_domain_cmd` only loads `domain.yaml`,
   schema-validates it, and checks `includes` globs resolve; it **never opens,
   parses, or validates any `.md` file**. So for these types `validate-domain`
   passes unconditionally regardless of the snippet's content. The real gates for
   `.md` targets are (a) an explicit **markdown structural check** in `draft.py`
   and (b) the `build-domain-skill` rebuild (step 3). The structural check, run
   before the rebuild, asserts: code fences are balanced; the inserted block
   introduces **no heading that collides with the builder's reserved
   `## Domain: <pack> — Source: …` / `## Domain attack-path defaults` section
   markers**; and the snippet is within a size cap. A snippet failing the structural
   check is dropped (reason `markdown structural check: <detail>`).
3. **Rebuild gate (all types).** Run `build-domain-skill <…all run packs…>
   --domains-dir <tmpdir>/domains --out <tmpdir>/skill-<dimpr-id>` to prove the
   edited pack still **compiles into a rebuildable skill**. **Use a FRESH out dir
   per improvement** (`skill-<dimpr-id>`): `build_domain_skill` short-circuits via
   `_existing_pack_signature` and returns the **stale** `SKILL.md` without
   re-reading the edited files whenever the existing out-dir's `(pack, version)` set +
   `framework_version` matches the request — and the per-improvement edits never
   bump a pack version. Reusing one out dir would make every build after the first
   hit the idempotent skip, silently passing snippets 2..N without re-reading them
   and defeating per-improvement isolation. A fresh out dir per improvement
   guarantees each rebuild actually reads the edited pack. (Equivalently, delete the
   out-dir `SKILL.md` before each build, or pass a no-cache flag if one is added to
   `build_domain_skill`; the fresh-dir approach is the chosen one.)
4. **On success**, keep the edit and record it for the diff.
5. **On failure** (any gate above fails / exits nonzero), **revert that single
   snippet** in the temp copy (restore the file from the pre-insertion snapshot
   held in memory), **drop** the improvement, and record it in a `dropped[]` report
   list with the `dimpr-` id, the `target_file`, and the gate's error message. Other
   improvements are unaffected. This is the "DROPS any edit that fails (reporting
   it)" behavior.

**Gate-strength honesty.** For the 4 `domain.yaml` types the validate gate is
strong (schema-validates the edited `domain.yaml`). For the 5 `.md` types the only
content gates are the `draft.py` structural check and the rebuild-doesn't-crash
check — the snippet's *prose quality* is **not** validated. The spec does not claim
otherwise; the author's review of the emitted patch is the quality backstop.

### 6.5 Diff emission

After all kept edits, compute a unified diff between the **original `domains/`
tree** and the temp copy (per changed file). Two cases:

- **Modified existing file:** `difflib.unified_diff` with `a/domains/<pack>/<file>`
  and `b/domains/<pack>/<file>` headers.
- **New file** (a `missing_common_pattern` creating a `common-patterns/<goal>.md`
  the pack lacked, per §6.3): a plain `a/`/`b/` diff is **not** `git apply`-able for
  a non-existent target. The command emits a proper new-file hunk:
  `diff --git a/domains/<pack>/<file> b/domains/<pack>/<file>`,
  `new file mode 100644`, `--- /dev/null`, `+++ b/domains/<pack>/<file>`. The
  coupled `domain.yaml` include edit (§6.3) appears as an ordinary modify hunk in
  the same patch.

Because every written file is normalized to end in exactly one trailing newline
(§6.3), the `\ No newline at end of file` edge never arises, so `difflib`'s
line-based output stays `git apply`-clean. Write the patch to `--out`. Print a
summary to stdout: `N drafted, M dropped` plus the `dropped[]` reasons (and any
`retargeted[]` markdown-fallback notes from §6.3). The patch is **never applied**;
the author reviews it and runs `git apply <patch>` themselves (§10 docs). Exit 0
even when some snippets were dropped (a partial patch is still useful); exit nonzero
only on an internal error (artifact missing/malformed, temp-copy failure). On any
error exit the `TemporaryDirectory` (§6.2) is still cleaned up.

### 6.6 Determinism

Same input artifact + same `domains/` tree ⇒ byte-identical patch. Improvements are
processed in a stable order (`(target_pack, target_file, dimpr-id)` sort); YAML
serialization is stable and byte-deterministic via
`yaml.safe_dump(..., sort_keys=False, default_flow_style=False, allow_unicode=True,
width=4096)` (§6.3 — `allow_unicode` prevents non-ASCII escaping noise, the wide
`width` prevents wrap noise); markdown insertion is deterministic (level-aware
anchor, §6.3); the temp dir path is normalized out of the diff headers (`a/` / `b/`
prefixes are relative to the tree root, not the tmpdir). A golden-patch test pins
this against a **frozen fixture pack copy** (not the live `domains/` tree), so the
pin is decoupled from live-pack drift (§12).

## 7. The `apd-domain-auditor` agent

A **new** repo agent at `.claude/agents/apd-domain-auditor.md`. It is distinct from
the existing `apd-report-auditor` (`.claude/agents/apd-report-auditor.md`), which is
report-faithfulness only and must **not** be extended. The domain-auditor is the
judgment half of capture: it harvests prose-judgment opportunities, materializes the
deterministic candidates into full records, drafts snippets, and writes the one
artifact.

### 7.1 Contract — inputs

- `40-synthesis/domain-coverage-delta.yaml` — the deterministic candidate signals
  (§5.1).
- `40-synthesis/deduped-findings.yaml` — the settled, deduped corpus (incl.
  apath-`*` / tmeval-`*`), read for the judgment signals in §5: no-clause-match
  notes (A §7), "not enumerated" / "not addressed" notes, and recurring patterns.
- `.claude/skills/apd-domain/SKILL.md` — the merged pack content (the union check
  for judgment types: an opportunity is real only if no pack's section already
  covers it; the per-pack `## Domain: <pack> — Source: <file>` headers tell the
  agent which pack to attribute and where).
- `00-context/asset-inventory.yaml` — to ground asset-derived evidence refs and
  resolve the deterministic candidates' `asset_id`s.
- The run's `.apd-run.yaml` `domains` list — for `examined_domains` and the
  primary/first-domain default.

**Missing delta file.** The deterministic pre-pass is best-effort and
non-blocking (§8): if `40-synthesis/domain-coverage-delta.yaml` is **absent** (the
pre-pass failed), the agent proceeds on judgment signals only and still emits a
schema-valid `domain-improvements.yaml`. A missing delta is treated as **zero
deterministic candidates**, never an error. (An empty-but-valid delta is likewise
zero candidates.) Because `examined_domains` is always sourced from
`.apd-run.yaml domains` (not from the delta), the agent can always populate the
required `examined_domains` field even with no delta.

### 7.2 Contract — behavior

1. **Required reading** (frontmatter + body, mirroring sibling agents):
   `.claude/skills/apd-framework/SKILL.md`,
   `.claude/skills/apd-evidence-discipline/SKILL.md` (evidence-pointer +
   block-on-ambiguity discipline applies here too — never invent an evidence ref),
   and this spec's taxonomy (§5).
2. **Materialize deterministic candidates.** For each candidate in the delta file,
   build a full `domain-improvement` record: carry `improvement_type`,
   `target_pack` (= `default_target_pack` unless the agent's domain-fit judgment
   reassigns it), `target_file`, `evidence` (the asset-inventory ref the pre-pass
   supplied), write a `rationale` + `suggested_action`, and draft a
   `draft_snippet`. `source` stays `deterministic`.
3. **Harvest judgment opportunities.** Scan the deduped corpus for the six judgment
   signals (§5). For each genuine gap (verified absent from the merged skill —
   union check), emit a `domain-improvement` record with `source: judgment`,
   `evidence` citing the **real** finding id(s) that revealed it, the best-fit
   `target_pack`, and a drafted `draft_snippet`.
4. **Draft every `draft_snippet` at capture time** (the load-bearing decision —
   judgment runs once). Snippet shapes by `target_file`:
   - `domain.yaml` crown jewel: a YAML list item
     `- pattern: <key>\n  description: "<≥10 chars>"` ready to append under
     `crown_jewels`.
   - `domain.yaml` attacker position / trust boundary: `- position:` / `- boundary:`
     items with descriptions.
   - `domain.yaml` regulatory anchor: a single quoted string list item under
     `regulatory_anchors`.
   - `severity-rubric.md`: a `- **<Harm name>** — <impact-to-service clause>`
     bullet, with the right tier named in the level-qualified
     `insertion_hint.markdown_section` (e.g. `{level: 2, text: "High"}`).
   - `consequential-actions.md`: a `- <action>` bullet under the right
     `## <category>` section, named via `{level: 2, text: "<category>"}`.
   - `immutability-classes.md` / `data-taxonomy.md`: the file's clause/row shape.
   - `common-patterns/<goal>.md`: a pattern block in that file's house format.
   Each snippet must be schema/build-valid in isolation; the agent is told the
   `domain.schema.json` constraints (e.g. `description` `minLength: 10`,
   `pattern` non-empty) so its drafts pass the on-demand validate gate.
5. **Compute the `dimpr-` id** per the §4.1 algorithm — the lowercased, `|`-joined
   4-tuple `improvement_type|target_pack|target_file|evidence[0].ref`,
   `sha256[:8]`, `dimpr-` prefix (the same logic the §7.4 `compute_improvement_id`
   helper implements; the linter §7.4 re-verifies via that helper). Dedup identical
   opportunities (same id) across the deterministic and judgment halves — keep one,
   prefer `source: deterministic`.
6. **Write** `40-synthesis/domain-improvements.yaml` (doc wrapper §4.2). When there
   are no opportunities, write the empty-but-valid artifact.
7. **Self-check before returning:** every `evidence[].ref` resolves to a real
   finding id or a real asset/identity/boundary id; every `target_pack` is in
   `examined_domains`; every `draft_snippet` is non-empty. Block (status `blocked`)
   rather than invent if a candidate's evidence cannot be grounded.

### 7.3 Contract — output + receipt

- **File output:** `40-synthesis/domain-improvements.yaml`.
- **Final message:** a **receipt only** (no prose), conforming to
  `schemas/agent-receipt.schema.json`, exactly as the sibling agents return. The
  workflow's `llmStep` dispatches the agent with `{schema: RECEIPT}`:

  ```yaml
  agent: apd-domain-auditor
  status: ok | blocked | error
  outputs:
    - path: 40-synthesis/domain-improvements.yaml
      schema_valid: true
  counts: {}        # advisory; no findings_by_severity. Optionally blocked: N.
  errors: []        # populate only on status: error
  ```

  An empty-but-valid artifact still returns `status: ok` with the output marked
  `schema_valid: true` (and the idempotent-skip sentinel when the guard short-
  circuits, per the workflow's SKIP CONVENTION). The `llmStep` guard's
  `validateScope: runDir + '/40-synthesis'` (§8) validates every synthesis rollup in
  that dir, including the freshly-written `domain-coverage-delta.yaml`; if the
  best-effort pre-pass failed and no delta exists, the guard still passes on the
  rest of `40-synthesis` and the agent proceeds with zero deterministic candidates
  (§7.1, missing-delta behavior) rather than erroring.

### 7.4 Linter

Add **two** new functions to `tools/apd_gauntlet/linters.py`:

1. `compute_improvement_id(improvement_type, target_pack, target_file, primary_ref)`
   — the **new** id helper, implementing the verbatim algorithm in §4.1
   (lowercased, `|`-joined 4-tuple, `sha256[:8]`, `dimpr-` prefix). It is **NOT**
   `compute_id` and does not share its `(prefix, title, first_locator)` signature or
   its 2-field `title|locator` payload; do not reuse `compute_id`.
2. `check_domain_improvement_id(record)` — recompute the `dimpr-<sha8>` by calling
   `compute_improvement_id(record['improvement_type'], record['target_pack'],
   record['target_file'], record['evidence'][0]['ref'])` and flag any mismatch with
   `record['id']`. It is **not** a thin mirror of `check_finding_id` (which
   early-returns unless `record['agent']` is in `_PREFIX_BY_AGENT`; improvement
   records carry no `agent` field).

The id check runs from the `_validate_domain_improvements_cross_refs` helper in
`run_cross_file_pass` (§4.3) — **not** from `run_semantic_pass`. The improvements
artifact is not a `*.findings.yaml`, so it never enters `_iter_records` or the
semantic pass; the cross-file helper is the single place that walks the
improvements doc, applying both the id recomputation and the evidence-ref
resolution (§4.3). Both the agent (§7.2 step 5) and this linter call the **same**
`compute_improvement_id`, so the at-capture id and the recomputed id are guaranteed
to agree.

## 8. Capture-phase placement in the workflow

A new **advisory, NON-BLOCKING** phase pair in
`.claude/workflows/apd-gauntlet.js`, placed **AFTER the 5g audit loop** (which ends
at the `for (let i = 0; i <= 2; i++)` audit/remediate loop) and **BEFORE**
`phase('closeout')` (the `summarize` + `validate-final` pyStep block). The phase
reads the SETTLED corpus — deduped + apath/tmeval (which, after A's Gap-1 reorder,
precede the rollup, so the corpus is fully settled here) + asset-inventory + the
merged `apd-domain` skill.

It adds two entries to the `meta.phases` array — `'domain-coverage-delta'` and
`'domain-improvements'` — inserted between `'synthesis-audit'` and `'closeout'`.
The phase body:

```js
// ===========================================================================
// PHASE 5h — domain-improvement capture (Subsystem B). ADVISORY / NON-BLOCKING.
// Runs AFTER the 5g audit loop and BEFORE closeout, over the SETTLED corpus.
// Never gates the run, never touches the HTML report. Empty-but-valid artifact
// when there are no opportunities.
// ===========================================================================
phase('domain-coverage-delta');
// 5h-i — deterministic coverage-delta pre-pass (Python). Best-effort: a failure
// here does NOT halt the run; the agent can still harvest judgment opportunities.
pyStep('domain-coverage-delta', {
  phase: 'domain-coverage-delta', label: 'domain-coverage-delta',
  outputs: runDir + '/40-synthesis/domain-coverage-delta.yaml' });

phase('domain-improvements');
// 5h-ii — apd-domain-auditor (LLM) reads the delta + settled findings + the merged
// apd-domain skill + asset-inventory; writes domain-improvements.yaml. Advisory:
// NOT wrapped in isErr()/HALT; a single best-effort dispatch (no retry storm), and
// the run proceeds to closeout regardless of its status.
llmStep('apd-domain-auditor',
  'Capture domain-improvement opportunities for this run. Read ' +
  '40-synthesis/domain-coverage-delta.yaml + 40-synthesis/deduped-findings.yaml + ' +
  '.claude/skills/apd-domain/SKILL.md + 00-context/asset-inventory.yaml; emit ' +
  '40-synthesis/domain-improvements.yaml (an empty-but-valid {schema_version:1, ' +
  'generated_by:domain-auditor, examined_domains:[...], improvements:[]} when there ' +
  'are no opportunities). ADVISORY — this never gates the run.',
  { phase: 'domain-improvements', label: 'domain-auditor',
    validateScope: runDir + '/40-synthesis',
    outputs: runDir + '/40-synthesis/domain-improvements.yaml' });
```

**Non-blocking discipline:** neither step is wrapped in the `isErr()` /
`throw new Error(...)` HALT pattern used by Phase 1.5 code-recon. A failure in
either step logs and proceeds — the run still completes and the report still ships;
B is purely additive.

**Idempotency.** The `domain-improvements` agent step (5h-ii) is idempotent under
the cross-session guard: its embedded IDEMPOTENCY GUARD validates
`domain-improvements.yaml` (`validateScope: runDir + '/40-synthesis'`), and an
existing valid artifact short-circuits cheaply via the skip sentinel. The
coverage-delta pre-pass (5h-i) is **always recomputed** on re-run — it is pure,
cheap, and byte-stable for a fixed inventory + pack set (§5.1), so recomputation is
harmless and no guard is needed; it overwrites the prior `domain-coverage-delta.yaml`
deterministically. (The pre-pass also writes `domain-coverage-delta.yaml`, validated
by `domain-coverage-delta-doc.schema.json` in `SYNTHESIS_ROLLUPS`, §5.1 step 8.)

**Closeout surfacing hook.** The N-opportunities advisory line is **not** emitted by
this phase. It is injected by the **closeout** phase's `summarize` pyStep, which
`summary.summarize_run` extends to read `40-synthesis/domain-improvements.yaml` and
`render_summary` emits the line (§9). That is the single concrete wiring point for
the surfacing requirement; §8's two steps only write the artifact.

The on-demand `draft-domain-improvements` command is **not** in the workflow — it is
author-run.

## 9. Surfacing

Author-facing, **side channel only** (NOTICE half):

- **The artifact:** `40-synthesis/domain-improvements.yaml` — the standalone,
  typed, validated record set. This is the durable surface.
- **Closeout summary:** the `closeout` phase's `summarize` pyStep gains one
  advisory line, read deterministically from the artifact's `improvements` length.
  This requires a concrete edit to **`tools/apd_gauntlet/summary.py`**:
  `summary.summarize_run` reads `40-synthesis/domain-improvements.yaml` **when
  present** (a pre-B run dir, where the artifact is absent, must **not** error — the
  line is simply omitted), and `render_summary` emits the advisory line
  unconditionally from the count (the `summarize` pyStep gains no new flag):
  `"N domain-improvement opportunities captured; run
  apd-gauntlet draft-domain-improvements <run> to draft pack edits."` When `N == 0`,
  `"0 domain-improvement opportunities captured."` (`tools/apd_gauntlet/summary.py`
  is a touched file for this effort; tested per §12.)
- **NOT in the report:** the artifact is **not** added to `report-data.yaml` or the
  HTML report. `report-data.schema.json` is `additionalProperties: false` and the
  report serves engineering review, not pack authors; adding a block would force a
  schema + template migration for an audience the report does not serve. B avoids
  that entirely. The `apd-report-auditor` and the 5g audit loop are untouched.

**Empty-run / no-opportunities behavior:** every step emits a schema-valid empty
artifact rather than no file — the pre-pass writes a delta with empty `candidates`,
the agent writes `improvements: []`, the closeout reports `0`, and
`draft-domain-improvements` prints "0 opportunities selected; nothing to draft" and
exits 0. No phase ever fails on emptiness.

## 10. Author documentation

- **New `docs/improving-domain-packs.md`** — the triage workflow:
  1. After a run, read `runs/<id>/40-synthesis/domain-improvements.yaml`; each
     record names the gap, the `target_pack`/`target_file`, the priority, the
     evidence (the finding or asset that revealed it), and a paste-ready
     `draft_snippet`.
  2. Run `apd-gauntlet draft-domain-improvements runs/<id>` (optionally filtered by
     `--id` / `--type` / `--target-pack`) to produce
     `runs/<id>/40-synthesis/domain-improvements.patch`.
  3. Review the patch (it is a standard unified diff against `domains/<pack>/`);
     note any improvements the command **dropped** (with their validate/build error)
     and address them by hand or discard.
  4. `git apply runs/<id>/40-synthesis/domain-improvements.patch` to apply the
     reviewed edits to the real pack.
  5. Re-validate: `apd-gauntlet validate-domain <pack>` and
     `apd-gauntlet build-domain-skill <packs…>` to confirm the pack stays valid and
     the skill rebuilds; commit the pack change as a normal authoring edit.
  The guide states plainly that B never auto-applies and never opens a PR — the
  author owns the apply + commit.
- **Pointer from `docs/adapting-to-other-domains.md`** — a short subsection
  ("Evolving a pack from gauntlet runs") linking to `improving-domain-packs.md`, so
  the existing authoring guide funnels readers to the triage workflow. This
  satisfies A's deferred "documentation should include guidance on how to do this."

## 11. Out of scope (deferred)

- **`--open-pr` wrapper** (auto-PR over the patch). B stops at a reviewed local
  diff; an optional later effort may wrap the patch in a branch + PR.
- **Auto-applying edits / SIA-style closed loop.** B never edits a real pack and
  never re-runs the gauntlet against the improved pack. Stop at a reviewed patch.
- **Broader domain-pack authoring-doc overhaul** — a separate effort; B adds only
  the improvement-triage guide (§10).
- **Cross-linking `dimpr-` ↔ findings** (a finding pointing at the improvement it
  spawned). Not needed for B; would be a deliberate `finding.schema.json` change at
  that time (§4.4).
- **Authoring new packs** (`web-app` / `agentic`) — B is validated on `pbm` +
  `api-security`.

## 12. Testing

- **Schema (record + doc wrapper + delta-doc).** Valid + invalid fixtures for
  `domain-improvement.schema.json`, `domain-improvements-doc.schema.json`, **and
  `domain-coverage-delta-doc.schema.json`** (§5.1 step 8): a good record validates;
  a bad id (`dimpr-XYZ`, wrong length), an unknown `improvement_type`, an
  out-of-enum `target_file`, an empty `evidence[]`, a missing `draft_snippet`, a
  `missing_common_pattern` record without `apd_goal`, **and a `missing_common_pattern`
  whose `apd_goal` does not match its `target_file`** (e.g. `apd_goal:
  confidentiality` + `target_file: common-patterns/integrity.md`, and the
  underscore/hyphen case `apd_goal: non_repudiation` +
  `target_file: common-patterns/non-repudiation.md` which must **pass**) each
  validate/reject as expected via the per-goal `allOf` branches. The empty-but-valid
  doc (`improvements: []`, with `examined_domains` present) validates; a doc
  **missing `examined_domains`** rejects (it is now `required`, §4.2). The delta-doc
  test covers a valid delta and a malformed one (e.g. `generated_by` not
  `coverage-delta`, or a candidate `source` other than `deterministic`).
- **Validate wiring (incl. the record `$ref`).** A run dir containing a well-formed
  `domain-improvements.yaml` passes `validate --schema-only`; a malformed one fails
  — proving the `SYNTHESIS_ROLLUPS` entry (§4.3) is live. **Crucially, the wiring
  test uses a NON-empty `improvements` doc (≥1 real record)** so the doc wrapper's
  absolute-`$id` `$ref` into `domain-improvement.schema.json` is actually exercised
  end-to-end (the empty-doc test never traverses the `$ref` and would hide a broken
  ref). A dangling `evidence[].ref` (a finding id absent from the corpus, or an
  `asset_id` absent from the inventory) fails the new cross-file check.
- **Deterministic pre-pass.** Given an `asset-inventory.yaml` with an asset
  `provenance.source: artifact` whose name maps to no `crown_jewels[].pattern` in
  the union of `pbm` + `api-security`, `domain-coverage-delta` emits exactly one
  `missing_crown_jewel` candidate (`source: deterministic`, `priority: high`,
  `evidence[0] = {kind: asset_inventory, ref: <asset_id>}`,
  `default_target_pack: <args.domains[0]>`). An asset with
  `provenance.source: domain_default` emits **no** candidate (it is already a pack
  declaration). An empty inventory emits empty `candidates` and exits 0. Output is
  byte-stable for a fixed inventory + pack set. The pre-pass test **also** pins
  `missing_attacker_position` and `missing_trust_boundary` candidate emission (a
  non-`domain_default` identity/boundary not in the declared union yields exactly
  one candidate of the right type with `source: deterministic` and an evidence ref
  keyed off `identity_id` / `boundary_id`) — so determinism is covered for all three
  deterministic types, not crown-jewel alone.
- **`dimpr-` id linter.** `check_domain_improvement_id` recomputes the sha8 by
  calling `compute_improvement_id` and flags a mismatch; a record whose id matches
  passes. The test asserts against the **exact byte payload**:
  `key = "|".join([improvement_type, target_pack, target_file,
  evidence[0].ref]).lower()`, `sha256(key.encode()).hexdigest()[:8]` — so the
  agent's at-capture computation and the linter's recomputation are guaranteed to
  agree (it does **not** test against `compute_id`, which has different semantics).
- **`draft-domain-improvements` happy path.** A captured `missing_crown_jewel`
  opportunity targeting `api-security/domain.yaml` inserts its `draft_snippet` into
  a temp copy, passes `validate-domain` + `build-domain-skill` (the rebuilt skill is
  clean), and produces a unified diff that `git apply --check` accepts. **The
  golden-patch determinism pin runs against a FROZEN fixture pack copied into the
  test tmpdir, not the live `domains/` tree** — `git apply --check` runs against that
  same frozen copy — so the pin is decoupled from live-pack drift (§6.6). Same input
  ⇒ byte-identical patch.
- **`draft-domain-improvements` new-file happy path.** A `missing_common_pattern`
  targeting a `common-patterns/<goal>.md` **absent** from the frozen fixture pack
  produces a proper new-file hunk (`new file mode 100644`, `--- /dev/null`) plus the
  coupled `domain.yaml` include edit (§6.3/§6.5), and `git apply --check`
  **accepts** the new-file patch (not just a modify patch).
- **`draft-domain-improvements` drop-on-fail (domain.yaml target).** A deliberately
  malformed `draft_snippet` (a `crown_jewels` item missing `description`, violating
  `domain.schema.json` `minLength: 10`) is **dropped** by the `validate-domain`
  gate — it appears in `dropped[]` with the validate error, the temp copy is
  reverted for that snippet, and a second, valid opportunity in the same run still
  lands in the patch. Exit code 0 (partial patch still useful).
- **`draft-domain-improvements` drop-on-fail (`.md` target).** Because
  `validate-domain` does **not** gate `.md` files (§6.4), a separate drop-on-fail
  test exercises an `.md`-target snippet (e.g. a `missing_severity_clause` snippet
  with unbalanced code fences, or one whose heading collides with the builder's
  reserved `## Domain:` marker) and asserts it is dropped by the **`draft.py`
  markdown structural check** and/or the `build-domain-skill` rebuild — proving the
  real gate for `.md` types catches it, not the (no-op-for-`.md`) `validate-domain`
  call.
- **Per-improvement rebuild isolation.** A two-snippet run where the **second**
  snippet is malformed asserts the second is dropped while the first lands — proving
  the per-improvement rebuild uses a **fresh out dir** (`skill-<dimpr-id>`) and does
  **not** hit `build_domain_skill`'s `_existing_pack_signature` idempotent
  short-circuit (which would otherwise pass snippet 2 against the stale skill from
  snippet 1, §6.4).
- **Already-declared duplicate drop.** A snippet re-adding an already-declared
  `crown_jewels[].pattern` is dropped with reason `already declared in <pack>`
  (§6.4 pre-insert duplicate check), not silently duplicated.
- **Multi-domain attribution edge.** An opportunity whose `target_pack` is not a
  real dir under `domains/` (on the temp copy) is dropped with reason
  `unknown target_pack`; an opportunity attributed to the correct best-fit pack
  (verified against `examined_domains`) lands.
- **Path-safety negative test.** A record carrying `target_pack: '../x'` or
  `target_pack: 'PBM'` is rejected at **schema-validation time** (the
  `^[a-z][a-z0-9-]*$` pattern), proving the artifact can never carry an escaping or
  upper-case pack name into the `draft.py` path builder.
- **No-opportunities path.** An empty `improvements: []` artifact ⇒
  `draft-domain-improvements` prints "0 opportunities selected; nothing to draft",
  writes no patch, exits 0; the closeout summary reports `0`.
- **Closeout summary line.** A unit test on `summary.render_summary` /
  `summary.summarize_run` (§9): given a run dir with a `domain-improvements.yaml` of
  `N` records, `summarize` emits the exact
  `"N domain-improvement opportunities captured; run apd-gauntlet
  draft-domain-improvements <run> to draft pack edits."` line; `N == 0` emits the
  `"0 domain-improvement opportunities captured."` variant; and the artifact being
  **absent** (a pre-B run dir) does **not** error and simply omits the line.
- **Agent receipt / lint.** A markdown-frontmatter lint on
  `.claude/agents/apd-domain-auditor.md` (name, description, tools, model present;
  required-reading lines present) and a contract test asserting the agent's
  documented final message conforms to `agent-receipt.schema.json`
  (status enum, `outputs[].schema_valid`, advisory `counts: {}`).
  **Agent discretion is NOT unit-tested** (the two judgment behaviors — the
  union-check that suppresses an opportunity already covered by a selected pack, and
  best-fit `target_pack` attribution — are non-deterministic LLM output and out of
  scope for a deterministic test). The enforcement boundary for them is instead the
  **deterministic** machinery that IS tested: the §4.3 cross-file validator (which
  enforces `every evidence[].ref resolves` and is exercised by the dangling-ref
  test) and the §6.4 draft-time validate/build gate. This is a documented decision,
  not a silent omission.
- **Command registration.** Both new commands MUST be registered as
  `@main.command` in `tools/apd_gauntlet/cli.py`, following the existing pattern
  (e.g. `rollup_cmd`). `domain-coverage-delta` is additionally gated by
  `tests/test_workflow_apd_gauntlet.py::test_every_cli_command_is_registered`
  (it is `pyStep`-scraped, so a missing registration fails that test). Because
  `draft-domain-improvements` is **author-run** and never appears in a `pyStep`, it
  is not scraped — so this effort adds an explicit `CliRunner`
  registration/`--help`-resolvable test for `draft-domain-improvements`.
- **Workflow pin.** A structural test on `.claude/workflows/apd-gauntlet.js`
  asserting (a) `meta.phases` contains `'domain-coverage-delta'` then
  `'domain-improvements'`; (b) those `phase('…')` literals appear **after** the
  `phase('synthesis-audit')` block and **before** `phase('closeout')`; (c) the
  `apd-domain-auditor` dispatch is **not** wrapped in a HALT (`throw`) — i.e. the
  phase is non-blocking; (d) `report-data` / the 5g audit loop are unchanged
  (B does not touch the report path). **Existing pins must also be updated, not just
  added to.** Both new phase names (`'domain-coverage-delta'`,
  `'domain-improvements'`) are emitted via **direct `phase('…')` literals** (not
  `runTier`-dynamic), so they MUST be added to **both** `EXPECTED_PHASES` and
  `DIRECT_PHASE_LITERALS` in `tests/test_workflow_apd_gauntlet.py`. Without that,
  three existing tests break:
  `test_every_meta_phase_is_emitted_one_way_or_the_other` (asserts
  `set(DIRECT_PHASE_LITERALS) | set(TIER_PHASES_VIA_RUNTIER) == set(EXPECTED_PHASES)`),
  `test_every_expected_phase_present_in_meta_phases`, and
  `test_direct_phase_literals_invoked_in_body`. These three named tests are required
  edits.

## 13. Open questions / risks

- **Synonym mapping for the crown-jewel delta.** The deterministic pre-pass needs a
  small, conservative synonym map (asset name ↔ pack `pattern` vocabulary) to avoid
  false `missing_crown_jewel` candidates when the inventory names an asset the pack
  already declares under a different label. Seeded from the selected packs' existing
  `pattern` strings; kept intentionally narrow so the pre-pass under-proposes rather
  than over-proposes (the agent can always add a judgment opportunity the pre-pass
  missed, but a noisy pre-pass erodes trust in the advisory). Flagged for tuning,
  not solved here.
- **Snippet rot vs. pack drift.** A `draft_snippet` is drafted at capture time
  against the pack as it was during the run. If the author improves the pack between
  capture and `draft-domain-improvements`, the snippet may already be covered. The
  validate/build gate catches *breakage* but not *redundancy* (`domain.schema.json`
  has no `uniqueItems`, and `build-domain-skill` does not de-dup), so redundancy is
  caught instead by the **§6.4 pre-insert duplicate check**, which normalizes the
  snippet's `pattern` / `position` / `boundary` / anchor and **drops** an
  already-declared `domain.yaml` item with reason `already declared in <pack>` — a
  first-class drop reason rather than a silent literal duplicate. (Markdown
  redundancy is not mechanically detectable and remains an author-review concern.)
  Adding `uniqueItems` to `domain.schema.json` would let `validate-domain` catch the
  `domain.yaml` case too, but that is a broader schema change deferred here.
- **Best-fit `target_pack` in blended runs.** Domain-fit attribution is the LLM's
  judgment; a mis-attribution lands the snippet in the wrong pack's diff, which the
  author rejects during review. The deterministic default (`args.domains[0]`) bounds
  the blast radius for the mechanical types. No structured ground truth exists for
  attribution; review is the backstop.
- **Empty / sparse inventories.** Runs with no `provenance.source: artifact` assets
  (e.g. a design-doc-only run) yield no deterministic candidates; capture then rests
  entirely on judgment signals. This is correct (nothing was grounded to delta
  against) but means the advisory is thinner for low-evidence runs — expected, not a
  defect.
