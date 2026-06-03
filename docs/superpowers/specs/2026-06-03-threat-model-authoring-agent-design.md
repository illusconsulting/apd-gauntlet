# Threat-Model Authoring Agent — Design

**Status:** approved design (brainstorming) → ready for implementation plan
**Branch:** `feat/threat-model-authoring-agent`
**Date:** 2026-06-03

## Context

The APD gauntlet (v1.6.0) only *consumes* threat models today:
`apd-threat-model-recon` parses a **user-supplied** threat model into
`00-context/threat-model-normalized.yaml`, and `apd-threat-model-evaluator`
grades it (coverage-gap / contradiction / silence findings). There is no agent
that *authors* a threat model. This design adds one.

The repo's earlier **Phase B plan deliberately rejected authoring** ("crosses the
line from reviewer to author… undermining the original TM author's process") and
warned that if the gauntlet *authors and grades its own TM*, the
coverage/contradiction/silence findings become tautological. This design
**reverses that posture** (recorded in **ADR-0013**) and **engineers out the
self-grading tautology** — that is the central design constraint, not an
afterthought.

An exploration workflow (8 parallel readers) mapped the pipeline; a judge-panel
workflow (3 designs → adversarial scoring → synthesis) produced the chosen
architecture. The adversarial pass surfaced one flaw shared by every
always-on-author-then-grade design — the self-grading tautology — which §"Locked
decisions" item 9 and §"Anti-tautology" address explicitly.

## Locked decisions (from brainstorming)

1. **Role = always-on baseline + comparator.** The gauntlet ALWAYS authors a
   grounded baseline TM; a user-supplied TM becomes a seed to diff against.
2. **Coverage = tiered.** On well-grounded surfaces, author a threat for every
   *applicable* STRIDE category (proactive completeness); on thin-evidence
   surfaces, author only what is grounded and emit explicit blocked/uncertain
   placeholders with structured `prerequisite_evidence`.
3. **Output = pure context-builder.** The author emits ONLY the authored
   `threat-model-normalized.yaml` (+ a human-readable doc) — no findings, no
   severity, not in the finding-dedup/rollup pipeline. The existing evaluator
   turns it into findings.
4. **Comparator = findings + delta report.** When a TM is supplied, extend the
   evaluator to emit a new finding flavor for material threats the supplied TM
   omitted vs the grounded baseline, plus a supplied-vs-authored delta section in
   the coverage report.
5. **CLI floor in cut 1.** A deterministic `apd-gauntlet author-threat-model`
   builds the threat *skeleton* (surface × applicable-STRIDE) from the inventory;
   the agent can only ground/block skeleton cells — mechanical never-invent.
6. **Human-readable `threat-model-authored.md`** is emitted alongside the YAML.
7. **Extend the existing `apd-threat-model-methodologies` skill** with an
   authoring section (single-sourced mapping tables) rather than a new skill.
8. **Direct-emit** the canonical `threat-model-normalized.yaml`; a supplied TM is
   parsed by recon to the **sibling** `threat-model-supplied-normalized.yaml`.
   DFD reconstruction is **in-LLM** for cut 1; a machine `data_flows[]` graph at
   the source is **Phase-2** (out of scope here).
9. **Anti-tautology carve-out.** The evaluator does NOT grade authored-only
   content with the coverage/silence passes (those only mean something against a
   *human* TM); baseline-only grading = the contradiction pass + an
   independent-specialist-corroboration gate.

## Architecture

```
intake (always) ──▶ asset-inventory.yaml + context-brief.md
code-recon (gated) ─▶ code-evidence-index.yaml
                         │
   ┌─────────────────────▼──────────────────────────────────────────┐
   │ PHASE: threat-model-author (ALWAYS-ON; replaces the gated slot) │
   │  1. apd-gauntlet author-threat-model  (deterministic CLI FLOOR) │
   │     → surface × applicable-STRIDE skeleton (low-confidence,      │
   │       provenance-anchored placeholders) at a scaffold path       │
   │  2. apd-threat-model-author agent (LLM ENRICH)                   │
   │     → grounds or blocks each skeleton cell; reconstructs flow    │
   │       direction in-LLM; emits the canonical normalized TM +      │
   │       the human-readable doc                                     │
   └─────────────────────┬───────────────────────────────────────────┘
                         ▼
   00-context/threat-model-normalized.yaml  (generated_by: threat_model_author)
   00-context/threat-model-authored.md      (human-readable)
                         │
   (if user supplied a TM) apd-threat-model-recon ─▶ threat-model-supplied-normalized.yaml
                         │
 tier-1/2/3 specialists cite the authored baseline as evidence
                         ▼
 apd-threat-model-evaluator (tier-4):
   • baseline-only  → contradiction pass + specialist-corroboration ONLY
   • supplied present → supplied-vs-authored delta → omission findings +
                        delta section in threat-model-coverage report
```

The authoring phase occupies the current `tm-recon` slot with its gate removed;
recon still runs **only when a TM is supplied**, now writing to the sibling file.
`apd-threat-model-evaluator` always runs (the authored baseline always exists).

## Components

### C1 — Deterministic CLI floor: `author-threat-model`

**Files:** create `tools/apd_gauntlet/threat_model/author.py`; register
`@main.command("author-threat-model")` in `tools/apd_gauntlet/cli.py`
(mirrors `parse-threat-model` / `analyze-attack-paths`).

**Responsibility (deterministic, no LLM):** read `00-context/asset-inventory.yaml`
(+ optional `code-evidence-index.yaml` + the compiled `apd-domain` skill's
`crown_jewels` / `attacker_positions` / `default_trust_boundaries`) and emit a
**skeleton** of normalized-TM entries — one per (surface, applicable-STRIDE
category) cell — to a scaffold file `00-context/threat-model-skeleton.yaml`.
Each skeleton entry:
- `asset` = the inventory surface's canonical name/key (so the evaluator's
  string-identity surface matching binds);
- `framework_refs.stride_letter` = the cell's category;
- `extraction_confidence` = `low`;
- `source_locator` = the inventory record's `provenance` locator;
- `threat` = a templated stub ("(<category> on <surface>: to be grounded)");
- `prerequisite_evidence` = [] (the agent fills it when blocking).

**Element-type → applicable-STRIDE matrix** (Shostack/Microsoft canonical; the
floor's core — surfaces derive their element type from the inventory `type`):

| Inventory surface | Element type | Applicable STRIDE |
|---|---|---|
| `identity` (actor/external entity) | external entity | **S, R** |
| `asset` type service/process/api/gateway | process | **S, T, R, I, D, E** |
| `asset` type data_store/database/queue/topic | data store | **T, R, I, D** |
| reconstructed data flow (a directed edge) | data flow | **T, I, D** |

The CLI **never invents a surface**: every skeleton cell traces to an
inventory/code-evidence/domain-pack record. Directed *flows* that exist only as
an unordered `trust_boundaries.crosses[]` pair with no directional evidence are
NOT manufactured as flows by the CLI — flow direction is the agent's in-LLM step
(C2), and an ungrounded flow becomes a blocked placeholder.

`author-threat-model` is idempotent and pure-function-testable.

### C2 — `apd-threat-model-author` agent (LLM enrichment)

**Files:** create `.claude/agents/apd-threat-model-author.md`.

Modeled structurally on `apd-threat-model-recon` (a receipt-only context-builder).
Frontmatter: `name`, `description` (block `|`: tier-0, always-on, inputs/outputs
by name), `tools: Read, Glob, Grep, Write, Bash` (Bash only to invoke the CLI
floor), `model: opus`. No network tools.

**Process:** (1) run `apd-gauntlet author-threat-model` to get the skeleton; (2)
reconstruct directed data-flows in-LLM from `context-brief.md` PHI/PII rows +
posture-annotated trust-boundary map + `code-evidence-index.yaml` edges/routes;
(3) for each skeleton cell, **ground** it (write a specific threat + mitigation
from the domain pack's `common-patterns/<goal>.md` prose, set `framework_refs`,
set `extraction_confidence` to the weakest grounding source, fill `mitigation`
with the contradictable design-intent control) **or BLOCK** it (leave
`mitigation: null`, set `extraction_confidence: low`, populate structured
`prerequisite_evidence[]` naming the missing artifact/property); (4) compute
`entry_id = "tm-" + sha8(asset + threat + source_locator)`; (5) emit the canonical
`threat-model-normalized.yaml` (`generated_by: threat_model_author`) and the
human-readable `threat-model-authored.md`.

**Required reading:** `apd-framework`, `apd-threat-model-methodologies` (incl. the
new authoring section), `apd-evidence-discipline`. **Not** `apd-finding-schema`
(emits no findings). **Final message:** receipt only (conforms to
`schemas/agent-receipt.schema.json`; `status: ok|blocked|error`; omit
findings/capabilities counts, like recon/intake).

**Methodology:** STRIDE-per-element is the default and always produced (broadest
APD-goal coverage, native-parser fidelity). Domain auto-augment: add LINDDUN
entries when the asset inventory carries PHI/PII data classifications; add MAESTRO
framing when the active domain pack is agentic-ai. (MAESTRO has no structured
`framework_refs` slot — it rides as `methodology: maestro` + threat text; this is
accepted reduced-fidelity, consistent with the methodologies skill.)

### C3 — Schema changes

**`schemas/threat-model-normalized.schema.json`:**
- Widen `generated_by` enum: `["threat_model_recon", "threat_model_author"]`.
- Add an **optional** entry-level `prerequisite_evidence`:
  `{ "type": "array", "items": { "type": "string" } }` (the structured
  blocked-placeholder field — replaces any prose `requires:` convention).
- Relax the `source_artifact` description to: "Relative path to the supplied
  threat model artifact, OR the primary grounding artifact
  (`00-context/asset-inventory.yaml`) for an authored baseline." (No type change;
  authored TMs set it to the inventory path so `minLength≥1` holds.)

**`schemas/threat-model-coverage.schema.json`:**
- Add an optional `supplied_vs_authored` object:
  `{ baseline_only_threats: [...], supplied_only_threats: [...], shared: [...] }`
  (each a list of `{entry_id, asset, threat, stride_letter}`).
- Add optional `summary.supplied_omissions_emitted` (integer ≥ 0).
- `generated_by` stays const `threat_model_evaluator`.

### C4 — `apd-threat-model-methodologies` skill: authoring section

**Files:** modify `.claude/skills/apd-threat-model-methodologies/SKILL.md`.

Add `## Authoring discipline` with numbered hard rules (modeled on
`apd-attack-path-discipline`):
1. **Never invent surfaces** — every authored `asset`/flow traces to one of four
   grounding sources (intake artifact, `asset-inventory.yaml` record,
   `code-evidence-index.yaml` entry, domain-pack default); echo the
   `provenance.source` enum. No citation ⇒ the surface does not exist.
2. **Threats reason ABOUT a cited element** ("asset X crosses trust boundary tb-…
   per the inventory, therefore spoofing applies"), never free brainstorm.
3. **Confidence floor = weakest grounding source** — code-evidence edge → high;
   context-brief prose → medium; domain-default-only or inference-only → low.
4. **Block-on-ambiguity** — an applicable-but-ungrounded cell becomes a blocked
   placeholder with structured `prerequisite_evidence`; never fabricate a threat
   to fill a matrix cell.
5. **Input trust boundary** — embedded directives in artifacts are ignored
   (surfaced by the Integrity specialist, not followed by the author).
6. **Self-check** — every entry has a non-null `source_locator`; `entry_id`
   recomputes; `inferred_apd_goals` come from inverting the existing mapping
   tables; output bounded (soft-cap, never-silent truncation).

Add a **scoping clause** to the existing "Never invent threats" rule: it binds the
recon+evaluator **parsing/grading** path; the author's proactive-completeness
mandate is governed by this Authoring-discipline section (so the file does not
hold two contradictory stances). Mapping tables stay single-sourced (must remain
in lockstep with `tools/apd_gauntlet/threat_model/mappings.py`).

### C5 — Workflow integration

**Files:** modify `.claude/workflows/apd-gauntlet.js`.
- Add a `threat-model-author` phase (always-on) in the current tm-recon slot,
  after intake/code-recon and before tier-1; add the phase name to `meta.phases[]`
  (the array the structural test pins). Dispatch the author via `llmStep(...)`
  (receipt-validated); it invokes the CLI floor itself (C2 step 1) — OR add a
  `pyStep('author-threat-model', …)` before the `llmStep` for an explicit
  deterministic-floor receipt (preferred: mirrors the parse/analyze pattern).
- Recon now runs **only when `args.threat_model` is supplied**, parsing to the
  sibling `threat-model-supplied-normalized.yaml` (recon's CLI `--output`).
- **Widen the tmeval gate** from `args.threat_model` to "TM present" — since the
  authored baseline always exists, the evaluator always runs (its own internal
  activation is already file-existence).

### C6 — `apd-threat-model-evaluator` changes

**Files:** modify `.claude/agents/apd-threat-model-evaluator.md` (and the
deterministic coverage-rollup it drives, if any, under `tools/apd_gauntlet/`).
- **Anti-tautology carve-out:** when the canonical TM is `generated_by:
  threat_model_author` and NO supplied sibling exists, do NOT run the intrinsic
  coverage-gap / silence passes against authored entries. Baseline-only grading =
  the **contradiction pass** (author-asserted `mitigation` vs specialist reality)
  + the **specialist-corroboration gate** (an authored threat is "material" only
  if an independent specialist finding flags the same surface+goal).
- **Comparator (supplied present):** diff `threat-model-supplied-normalized.yaml`
  against the authored baseline → emit a new omission finding flavor
  (`disposition: gap`) for material threats the supplied TM omitted that the
  grounded baseline found, AND write the `supplied_vs_authored` block + a delta
  section in the coverage report.
- A blocked placeholder (entry with non-empty `prerequisite_evidence`) is **never
  counted as coverage** — it is a gap-marker.

### C7 — Consumer guards & rendering

- **`tools/apd_gauntlet/validate.py`** — add
  `"threat-model-supplied-normalized.yaml": "threat-model-normalized.schema.json"`
  to `CONTEXT_ROLLUPS` (line 227) so the sibling is schema-validated. (The
  `threat_model_author` enum value validates via the C3 schema change.)
- **`tools/apd_gauntlet/attack_path/build.py`** — `build.py:63` loads
  `threat-model-normalized.yaml` as *declared* coverage (`build.py:99-100`,
  edge confidence from `extraction_confidence` at `build.py:548`). Add a
  `generated_by` guard: when `threat_model_author`, treat its edges as **inferred**
  (do not present author-inferred threats as operator-*declared* TM coverage —
  e.g. annotate provenance `inferred` / keep the entry's own confidence rather
  than declared-ground-truth weight). Confirm the hexo-ai/sia golden run is
  unaffected.
- **`tools/apd_gauntlet/report/transform.py`** — recognize the authored TM + the
  supplied comparator; render `threat-model-authored.md` from the normalized YAML
  via a new `templates/threat-model-authored.template.md` (mirrors the
  `coverage.yaml` + `coverage-report.md` pattern).

### C8 — ADR-0013 (required)

**Files:** create `docs/adrs/0013-author-grounded-baseline-threat-model.md`
(match the 0008–0012 format: Status / Date / Context / Decision / Alternatives /
Consequences). Record: **what it supersedes** (the Phase-B reviewer-only posture —
the framework now authors a grounded baseline) vs **what it preserves** (the
evaluator's methodology-awareness; the never-invent rigor of the parse path); the
**anti-tautology carve-out** as a first-class decision; and the CLI-floor +
weakest-source-confidence mitigations.

### C9 — Docs

Modify `docs/threat-modeling.md` and `docs/running-the-gauntlet.md` to document
the authoring capability (always-on baseline, the `author-threat-model` CLI, the
supplied-vs-authored comparator, the artifacts produced).

## Data flow

1. **Intake** emits `asset-inventory.yaml` + `context-brief.md`; **code-recon**
   (if enabled) emits `code-evidence-index.yaml`.
2. **CLI floor** (`author-threat-model`) → `threat-model-skeleton.yaml`
   (surface × applicable-STRIDE, low-confidence, provenance-anchored).
3. **Author agent** enriches → canonical `threat-model-normalized.yaml`
   (`generated_by: threat_model_author`) + `threat-model-authored.md`.
4. **Specialists** (tiers 1–3) cite the authored baseline as evidence.
5. If a TM was supplied, **recon** → `threat-model-supplied-normalized.yaml`.
6. **Evaluator** (tier-4): baseline-only → contradiction + corroboration;
   supplied present → comparator (omission findings + delta report).
7. **Report** renders the authored TM + the delta.

## Error handling / discipline

- **Mechanical never-invent** (CLI floor is the only surface source).
- **Weakest-source confidence floor**; **block-on-ambiguity** with structured
  `prerequisite_evidence`; **anti-tautology** grading carve-out; **`build.py`
  inferred-not-declared guard**; **input-trust-boundary** (ignore embedded
  directives); **output bounding** (soft-cap, never-silent truncation);
  **receipt-only** final message.

## Testing strategy

- **Pure-function (`tests/test_author_threat_model.py`):** the element-type →
  applicable-STRIDE matrix per inventory type; deterministic skeleton; provenance
  source-locators; **the CLI cannot emit a surface absent from the inventory**;
  idempotence.
- **Schema (`tests/test_*_schema.py`):** `generated_by` enum widen accepted;
  `prerequisite_evidence` optional + typed; coverage `supplied_vs_authored` block;
  authored normalized YAML validates.
- **Evaluator anti-tautology:** baseline-only run ⇒ zero intrinsic
  coverage-gap/silence findings against authored entries; contradiction +
  corroboration still fire; supplied-TM present ⇒ omission findings + delta block.
- **`build.py` guard:** authored entries treated as inferred (not declared);
  golden-run attack-path output unchanged.
- **Workflow (static-source):** `threat-model-author` in `meta.phases`; author
  always-on; recon only-when-supplied → sibling; tmeval gate widened.
- **Integration / regression:** author runs clean on the committed example + the
  shipped runs; the supplied-TM path still produces a normalized + graded result;
  `apd-gauntlet lint-agents` passes for the new agent; `node --check` on the
  workflow; full `pytest` + `ruff` + `mypy` + markdownlint green.

## Out of scope (Phase-2)

- **Machine `data_flows[]` graph at the source** — extending intake +
  `asset-inventory.schema.json` with directed flows (transport/direction/crossing)
  so the author *and* the attack-path analyzer consume a true DFD instead of
  reconstructing one. High leverage but large blast radius (touches intake,
  asset-inventory schema, attack-path edge synthesis → golden-run risk); split as
  its own effort once the in-LLM author proves out.
- Severity-bearing residual-risk findings from the author (it stays a pure
  context-builder; the evaluator + specialists own findings).

## Self-review

**Decision coverage.** All nine locked decisions map to a component: D1 → C5
(always-on phase) + C6 (always-run evaluator); D2 → C1 matrix + C2 ground/block +
C3 `prerequisite_evidence`; D3 → C2 (receipt-only, no findings); D4 → C6 +
C3 coverage block; D5 → C1; D6 → C2 + C7 (`threat-model-authored.md`); D7 → C4;
D8 → C2 (direct-emit) + C5 (recon→sibling); D9 → C6 (anti-tautology) + C8 (ADR).

**Placeholder scan.** No TBD/TODO; every component names real files + exact schema
edits verified against the repo (`threat-model-normalized.schema.json` enum +
entry shape; `validate.py:227` CONTEXT_ROLLUPS; `build.py:63/99/548`; coverage
`generated_by` const).

**Internal consistency.** The author owns the canonical
`threat-model-normalized.yaml`; recon owns the supplied sibling — no two producers
of one file. The evaluator's anti-tautology carve-out keys on
`generated_by == threat_model_author` + sibling-absence, consistent across C6/C8.
`source_artifact` tension resolved in C3.

**Scope.** Single feature (TM authoring) — one agent + one CLI + one skill section
+ schema/workflow/evaluator/consumer edits + ADR + docs. DFD-at-source and
severity-findings are explicitly deferred. Focused enough for one implementation
plan.

**Ambiguity.** The CLI-floor-vs-agent split is explicit (CLI = deterministic
surfaces+applicable-categories; agent = flow-direction inference + ground/block +
emit). "Material omission" is defined (corroborated by an independent specialist
finding). Blocked-placeholder is a structured field, not prose.
