# Improving domain packs from gauntlet runs

A gauntlet run reveals where the active domain pack(s) are *incomplete* — a harm
with no matching severity clause, a crown jewel present in the run but declared by
no selected pack, a consequential action not enumerated. Subsystem B captures those
gaps on **every** run as typed, pack-attributed *domain-improvement opportunities*,
then lets you turn the ones you choose into a validated, reviewable, `git apply`-able
patch against `domains/<pack>/`.

This guide covers the full loop: how capture works, what an opportunity record
contains, how opportunities are attributed to the right pack under a multi-domain
run, and the read -> draft -> review -> apply workflow.

## 1. The capture -> draft -> apply loop

Two clean halves: **NOTICE** (automatic, every run) and **ACT** (you trigger it).

**NOTICE — capture, every run (advisory, non-blocking).** A dedicated workflow
phase (Phase 5h, after the synthesis audit loop and before closeout) emits
`runs/<id>/40-synthesis/domain-improvements.yaml`. Capture is hybrid:

- A deterministic Python pre-pass (`apd-gauntlet domain-coverage-delta`) computes
  mechanical coverage deltas — assets, identities, and trust boundaries in
  `00-context/asset-inventory.yaml` that no selected pack declares — and writes the
  candidate signals to `40-synthesis/domain-coverage-delta.yaml`.
- The `apd-domain-auditor` agent then reads those candidates plus the settled,
  deduped findings and the merged `apd-domain` skill, harvests prose-judgment
  opportunities, assigns each a best-fit `target_pack`, drafts a paste-ready
  `draft_snippet` at capture time, and writes `domain-improvements.yaml`.

The phase is purely additive: it never gates the run, never touches the HTML report,
and writes a schema-valid empty artifact when there are no opportunities. A run with
no opportunities emits `improvements: []` and the closeout reports
`0 domain-improvement opportunities captured.`; a run with opportunities reports
`N domain-improvement opportunities captured; run apd-gauntlet
draft-domain-improvements <run> to draft pack edits.`

**ACT — draft, on demand.** When you choose to act, run:

```bash
apd-gauntlet draft-domain-improvements runs/<id>
```

This turns the chosen opportunities' `draft_snippet`s into a validated, unified diff.
It edits only a temp copy of `domains/` — the real pack tree is never written — and
it never auto-applies and never opens a PR. **You own the apply + commit.**

## 2. The opportunity record

Each entry in `domain-improvements.yaml` is a `domain-improvement` record with a
deterministic `dimpr-<sha8>` id. The doc wrapper carries `schema_version`,
`generated_by: domain-auditor`, and `examined_domains` (the run's selected packs);
each record carries these fields:

- `improvement_type` — one of the nine taxonomy values. Three are detected
  **deterministically** (from the asset-inventory vs. pack-declaration delta) and six
  by **judgment** (from cited findings):

  - `missing_severity_clause` — a harm matched no clause in any pack's
    `severity-rubric.md`.
  - `missing_crown_jewel` — a run asset maps to no `crown_jewels[].pattern`
    in the union of selected packs.
  - `missing_attacker_position` — an identity or boundary implies an attacker
    position no pack declares in `attacker_positions`.
  - `missing_trust_boundary` — an inventory trust boundary matches no
    `default_trust_boundaries[].boundary`.
  - `missing_consequential_action` — an audit-worthy action is not enumerated in
    `consequential-actions.md`.
  - `missing_immutability_class` — a data class whose immutability is not addressed
    in `immutability-classes.md`.
  - `missing_data_class` — data elements not enumerated in `data-taxonomy.md`.
  - `missing_common_pattern` — a recurring per-goal finding pattern absent from the
    pack's `common-patterns/<goal>.md`.
  - `missing_regulatory_anchor` — a regulatory regime no pack lists in
    `regulatory_anchors`.

- `target_pack` — the pack the snippet would edit (one of `examined_domains`).
- `target_file` — the exact pack file (`domain.yaml`, one of the four calibration
  `.md` files, or a `common-patterns/<goal>.md`).
- `priority` — `high`, `medium`, or `low`.
- `source` — `deterministic` (the mechanical pre-pass) or `judgment` (the
  `apd-domain-auditor` agent). Use it to triage mechanical vs. interpretive gaps.
- `evidence` — the **real** run signal that revealed the gap, never invented: an
  array of `{kind, ref}` items where `kind: finding` cites a finding id from the run
  corpus and `kind: asset_inventory` cites an `asset_id` / `identity_id` /
  `boundary_id` from `00-context/asset-inventory.yaml`. The validator cross-checks
  every ref against the real ids.
- `draft_snippet` — paste-ready content (a `domain.yaml` list item or a markdown
  clause) that the draft command inserts verbatim.

Records also carry `rationale` and `suggested_action` prose, and an optional
`apd_goal` (required for `missing_common_pattern`) and `insertion_hint` that tells
the draft command where to insert the snippet.

## 3. `target_pack` attribution under multi-domain

When a run loads more than one pack — selected at scaffold time via repeatable
`--domain` and recorded in the run's `domains:` list — every gap is measured against
the **union** of all selected packs. An item is an opportunity only if **no** selected
pack already covers it. Attribution then names exactly one pack:

- The deterministic pre-pass keys off the run's `domains` and defaults each
  mechanical candidate to the run's primary (first) domain.
- The `apd-domain-auditor` agent attributes each opportunity to the specific pack it
  would best fit, and may reassign a deterministic candidate's `target_pack`.

The doc wrapper's `examined_domains` records the packs that were examined, so every
record's `target_pack` is one of them. The draft command verifies the
`target_pack` directory exists before editing; an opportunity attributed to a pack
not present locally is dropped (see §4).

## 4. Read -> draft -> review -> apply

### Read the captured opportunities

After a run, open `runs/<id>/40-synthesis/domain-improvements.yaml` and read each
record's `improvement_type`, `target_pack` / `target_file`, `priority`, `source`,
`evidence`, and `draft_snippet`. Decide which gaps are worth acting on.

### Draft a patch

```bash
apd-gauntlet draft-domain-improvements runs/<id>
```

With no filter flags the command drafts every opportunity. Narrow the set with
repeatable filters:

```bash
apd-gauntlet draft-domain-improvements runs/<id> \
  --id dimpr-1a2b3c4d --type missing_crown_jewel --target-pack api-security
```

The available flags are `--id` (a `dimpr-` id), `--type` (an `improvement_type`),
`--target-pack` (a pack name) — each repeatable — plus `--out` (patch path, default
`runs/<id>/40-synthesis/domain-improvements.patch`) and `--domains-dir` (the packs
directory, default `domains`).

The command copies `domains/` to a temp directory, inserts each chosen `draft_snippet`
there, and gates it: `domain.yaml` snippets are checked with `validate-domain`, all
snippets are proven to rebuild via `build-domain-skill`, and `.md` snippets get a
markdown structural check. Any snippet that fails its gate — or is already declared
in the pack, or targets an unknown pack — is **dropped** (its temp-copy edit reverted)
and reported, while the others proceed. The command prints `N drafted, M dropped`
with each dropped id and its reason, then writes the diff to `--out`. Exit code is 0
even when some snippets drop; a partial patch is still useful.

### Review the patch

The patch is a standard unified diff against `domains/<pack>/`. A `domain.yaml`
insertion is line-anchored — the hunk adds only the new list item and leaves every
other line byte-identical, so a one-item addition is a one-item diff (the sole
exception is un-inlining an empty inline list such as `regulatory_anchors: []`).
For `.md` targets the gate only checks structure and rebuildability, so the prose
quality is your review's responsibility. Address or discard any dropped improvements
noted in the command's output.

### Apply and re-validate

```bash
git apply runs/<id>/40-synthesis/domain-improvements.patch
apd-gauntlet validate-domain <pack>
apd-gauntlet build-domain-skill <packs…>
```

`validate-domain` and `build-domain-skill` confirm the pack stays schema-valid and
the skill rebuilds. Commit the pack change as a normal authoring edit. B stops here:
there is no auto-PR and no closed loop back into the gauntlet.

For authoring packs from scratch, see
[adapting-to-other-domains.md](adapting-to-other-domains.md).
