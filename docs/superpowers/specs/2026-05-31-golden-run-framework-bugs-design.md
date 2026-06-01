# Golden-run framework-bug fixes — Design

**Status:** approved design (brainstorming) → ready for implementation plan
**Branch:** `fix/golden-run-framework-bugs`
**Date:** 2026-05-31

## Context

The first real-world gauntlet run of the `agentic-ai` pack against `hexo-ai/sia`
(`runs/apd-20260531-sia-self-improving-agent/`, driven interactively in the
foreground) surfaced five framework defects that the normal background path hides.
The root insight: **LLM specialist agents cannot reliably produce the canonical
record envelope or the deterministic SHA-256 IDs the contract requires, and the
validators pass *vacuously* on the non-canonical output they actually emit.** This
design makes the gauntlet robust to that reality: tooling owns the structural
correctness agents can't, the validators stop passing vacuously, and the remaining
diagnosed bugs are fixed.

### The five defects (from `runs/.../RUN-NOTES-framework-findings.md`)

- **F1 (critical):** `validate._iter_records` and the `check-ids` command read ONLY
  the singular root key (`finding`/`capability`). All nine specialists emitted the
  PLURAL key (`findings:`/`capabilities:`), so both tools matched **zero records**
  and exited 0 — validation was a no-op on every tier gate and the full gate.
- **F2 (high):** specialist output drifts from the contract (masked by F1): plural
  root keys (9/9); per-record `finding:`/`capability:` wrapping (4/9); **fabricated
  IDs** instead of `compute_id(prefix, title, evidence[0].locator)` (74/74 — LLMs
  cannot SHA-256 by hand); `context-brief.md` cited as an evidence artifact
  (rejected by the intake-brief artifact check); occasional over-length titles
  (>200) / excerpts (>25 tokens).
- **F3 (medium):** `synthesis/loader.py` capability branch lacks the missing-`id`
  skip guard the findings branch has → `KeyError` crash in `cluster-candidates`.
- **F4 (medium, fix already applied on this branch):** `validate.resolve_report_data`
  did not union the deduped corpus, so a report headlining a legitimate
  `merged-<sha8>` id failed "unknown finding". The applied fix mirrors the sibling
  `_validate_domain_improvements_cross_refs` union (validate.py). Needs a test.
- **F5 (low):** `attack_path/build.py:_node_name_index` raises `BuilderBlocked` on
  any case-insensitive node-name collision. An inventory asset named after a
  crown-jewel *pattern* string collides with that crown-jewel's own node (same
  concept), blocking the builder.

## Locked design decisions

1. **`canonicalize` owns IDs (tooling authoritative).** It recomputes every
   deterministic id and rewrites `cross_references`, overwriting whatever the agents
   wrote. Agents may still author a best-effort id; tooling is the source of truth.
2. **Structural-only repair.** `canonicalize` repairs only what is derivable/
   structural: envelope (singular root + unwrap), deterministic ids + cross-refs,
   per-record `schema_version`. It does NOT edit semantic content (titles, excerpts,
   evidence). Discipline agents *can* control (evidence artifact = input artifact
   not `context-brief.md`; lengths) is enforced by `validate` and fixed by tightened
   agent prompts.
3. **Per-tier canonicalize + strict validate.** `canonicalize` runs (idempotent,
   whole-run) before EACH tier's validate gate. `validate` and `check-ids` are made
   non-vacuous AND emit a hard error when a plural-root/wrapped file reaches them.

## Components

### C1 — `canonicalize` command (new) — `tools/apd_gauntlet/canonicalize.py`

`apd-gauntlet canonicalize <run_dir>` — idempotent, whole-run, structural-only.
Reuses `linters.compute_id`, the capability-id rule, and `linters._PREFIX_BY_AGENT`
as the single source of truth for id computation (no duplicated hash logic).

**Scope of records touched:** records in `*.findings.yaml` / `*.capabilities.yaml`
under the run dir whose `agent` field maps to a known lens prefix in
`_PREFIX_BY_AGENT` (the nine lenses). This deliberately leaves alone:

- `40-synthesis/deduped-*.yaml` (apply.py already mints canonical `merged-*` ids),
- `40-synthesis/attack-path.findings.yaml` (`agent: attack_path_analyzer` is not in
  `_PREFIX_BY_AGENT`; its ids follow a separate rule and validate does not check
  them via `check_finding_id`).

**Algorithm:**

1. **Per-file load + envelope normalize (in memory):** read records via singular-
   or-plural root key (`finding`→`findings` fallback); unwrap any per-record
   `finding:`/`capability:` wrapper (a record dict whose only key is the kind and
   whose value is a dict); ensure each record carries `schema_version` (default 1).
2. **Global pass 1 — recompute ids:** for each in-scope record (deterministic file-
   sorted, then index order), compute `new_id` via `compute_id(prefix, title,
   evidence[0].locator)` for findings or the `-cap-` infix rule for capabilities,
   where `prefix = _PREFIX_BY_AGENT[record['agent']]`. Build a global
   `old_id → new_id` map; overwrite `record['id'] = new_id`. Skip records with no
   evidence or unmapped agent (leave id untouched, like the linters).
3. **Global pass 2 — rewrite cross-references:** for every in-scope record, rewrite
   each `cross_references` entry through the map (entries are id strings; also handle
   the dict-with-`id` form defensively).
4. **Write back** as `{<singular root>: [<bare records>]}` (PyYAML dump,
   `sort_keys=False`, `allow_unicode=True`, wide width).

**Idempotency:** a second run recomputes the same ids (deterministic), the envelope
is already singular/bare, and the cross-ref map is identity → no-op. **Collision
guard:** if two records would receive the same `new_id`, exit non-zero with a clear
message (do not silently coalesce).

**Output:** prints `canonicalize: N records recanonicalized, M cross-refs rewritten`;
exit 0 on success, non-zero on collision / parse error. CLI command added in
`cli.py` mirroring the existing pyStep-style commands.

### C2 — F1: non-vacuous + strict validators — `tools/apd_gauntlet/validate.py`, `cli.py`

- **`_iter_records`:** fall back to the plural root key when the singular is absent,
  and unwrap wrapped records in memory, so every per-record check runs (no vacuous
  pass). Single shared helper for "extract records from a findings/capabilities doc"
  to avoid drift between `_iter_records`, the loader, and `check-ids`.
- **New envelope check** (Pass-1 or a dedicated pass): a `*.findings.yaml` /
  `*.capabilities.yaml` whose root key is plural, or any of whose records is wrapped,
  produces a hard **ERROR**: `non-canonical envelope: use singular root key
  '<finding|capability>' with bare records (run 'apd-gauntlet canonicalize')`.
- **`check_ids_cmd`** (cli.py): apply the same singular-or-plural + unwrap extraction
  so it is non-vacuous (it has the identical bug today).

### C3 — F3: loader capability guard — `tools/apd_gauntlet/synthesis/loader.py`

Add the missing-`id` skip-with-warning guard to the capability branch
(loader.py:58-67), mirroring the findings branch (loader.py:54-56): a capability
record missing `id` is warned and skipped, not crashed on.

### C4 — F4: regression test for the applied resolver fix

The validate.py change is already on the branch. Add a test asserting that a
`report-data.yaml` whose `headline_findings` / `next_steps.refs` reference a
`merged-<sha8>` id present only in `deduped-findings.yaml` validates clean (and that
a genuinely unknown id still errors).

### C5 — F5: attack-path builder collision — `tools/apd_gauntlet/attack_path/build.py`

`_node_name_index` (build.py:364-382): when two nodes share a lowercased name,
resolve a **crown_jewel ↔ asset** pair (the asset realizes the crown jewel) instead
of raising — map the shared name deterministically to one of the pair (the concrete
asset node) so downstream text matching is unambiguous. Reserve `BuilderBlocked` for
genuinely ambiguous collisions between two nodes of the *same* type. **Core
requirement:** the builder no longer blocks on a crown_jewel↔asset name collision.
**Contingent enhancement:** if the graph already has a suitable edge type for
"asset realizes crown jewel", emit that edge to improve connectivity; if no such
edge type exists in the current schema, the planning step adds the unify-without-
block fix only (do NOT introduce a new edge type / schema change in this effort).

### C6 — F2 agent-side: prompt/skill tightening

- **`apd-finding-schema` skill** (`.claude/skills/apd-finding-schema/SKILL.md`): make
  the canonical envelope explicit — singular `finding:` / `capability:` root, **bare**
  records (no per-record wrapper), per-record `schema_version`; never plural. Add a
  short "common mistakes" block. Note that ids are tooling-canonicalized, so agents
  author a best-effort id and must not hand-tune it.
- **The nine specialist agent definitions** (`.claude/agents/apd-{confidentiality,
  integrity,availability,distributed,resilient,ephemeral,authenticity,
  non-repudiation,immutability}.md`): a single shared reminder in each Output section
  — emit a bare singular `finding:`/`capability:` list; evidence `artifact` values
  must be **input artifacts** (e.g. `tech_plan.md`), never `context-brief.md`; titles
  ≤200 chars, excerpts ≤25 tokens. Keep edits minimal and identical across agents.

### C7 — workflow wiring — `.claude/workflows/apd-gauntlet.js`

- Add a `pyStep('canonicalize', …)` inside `runTier`, **before** the tier validate
  gate (idempotent whole-run; positional = run dir). After canonicalize, the
  existing tier `validate --tier` gate sees canonical input.
- Add `'canonicalize'` to `meta.phases`.
- The existing structural workflow test (`tests/test_workflow_apd_gauntlet.py`) is
  updated to pin: canonicalize precedes each tier gate; `meta.phases` includes it.

## Data flow

Specialists write per-lens files (possibly non-canonical) → **canonicalize**
(envelope + ids + cross-refs) → tier `validate --tier` gate (now meaningful) →
(next tier reads already-canonical earlier-tier ids) → … → full pre-Phase-5 gate →
synthesis. Because canonicalize runs before each tier gate and tiers run in order,
later tiers read canonical earlier-tier ids, so their cross-references are authored
against canonical targets; canonicalize's own pass-2 remap covers within-tier and
any residual references.

## Error handling

- `canonicalize` id collision → non-zero exit, named records (never silent coalesce).
- `validate` non-canonical envelope → hard ERROR (does not silently normalize at
  validate time; canonicalize is the normalizer).
- `canonicalize` is structural-only: a record that is non-canonical in *content*
  (over-length, `context-brief.md` evidence) is left for `validate` to flag.

## Testing

- **canonicalize (unit):** plural→singular; per-record unwrap; `schema_version`
  injection; id recompute equals `linters.compute_id` / capability rule; cross-ref
  remap (string + dict forms); idempotency (second run no-op); collision → non-zero;
  structural-only (titles/excerpts/evidence untouched); out-of-scope records
  (`merged-*`, `apath-*`) untouched.
- **validate / check-ids (F1):** a plural-root file is now non-vacuously validated
  (a bad record IS caught) AND raises the envelope error; a wrapped-record file too;
  canonical singular input stays clean.
- **loader (F3):** a capabilities file with a missing-`id` record skips with a
  warning, no crash; `cluster-candidates` tolerates it.
- **resolver (F4):** report-data referencing a deduped `merged-*` id validates;
  unknown id still errors.
- **builder (F5):** a graph with an asset named identically (case-insensitive) to a
  crown-jewel pattern builds (no `BuilderBlocked`) and links them; a same-type
  ambiguous collision still blocks.
- **workflow:** structural test pins canonicalize-before-each-tier-gate + phases.
- **agents/skill:** `lint-agents` stays green; a doc/staleness assertion that the
  schema skill states the singular-bare envelope.
- **integration:** a fixture run with non-canonical specialist output →
  `canonicalize` → `validate` exits 0.

## Out of scope

- Re-running the SIA gauntlet (the existing run already validates clean).
- Changing the deterministic-id algorithm itself (only *who computes it*).
- Reworking attack-path bridging beyond the F5 collision fix (the 0-paths outcome
  for the SIA run is a separate, correctly-surfaced `code_recon: disabled` gap).
- Canonicalizing `apath-*` / `merged-*` records (owned by their own producers).
