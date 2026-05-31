# Improving domain packs from gauntlet runs

A gauntlet run reveals where the active domain pack(s) are *incomplete* — a harm
with no matching severity clause, a crown jewel present in the run but declared by
no pack, a consequential action not enumerated. Subsystem B captures those gaps on
every run (advisory, non-blocking) and lets you turn chosen ones into a reviewable
patch. **B never auto-applies and never opens a PR — you own the apply + commit.**

## 1. Read the captured opportunities

After a run, open `runs/<id>/40-synthesis/domain-improvements.yaml`. Each record
names:

- the gap (`improvement_type`, one of the nine types),
- the `target_pack` / `target_file` it would edit,
- the `priority` and `source` (`deterministic` from the mechanical pre-pass, or
  `judgment` from the `apd-domain-auditor` agent),
- the `evidence` — the real finding id or asset/identity/boundary id that revealed
  it,
- a paste-ready `draft_snippet`.

A run with no opportunities emits a schema-valid empty artifact and the closeout
reports `0 domain-improvement opportunities captured.`

## 2. Draft a patch

```bash
apd-gauntlet draft-domain-improvements runs/<id>
```

Filter the set with repeatable flags:

```bash
apd-gauntlet draft-domain-improvements runs/<id> \
  --id dimpr-1a2b3c4d --type missing_crown_jewel --target-pack api-security
```

The command inserts each chosen `draft_snippet` into a **temp copy** of `domains/`,
runs `validate-domain` + `build-domain-skill` to prove the edited pack stays
schema-valid and rebuildable, **drops** any snippet that fails (reporting the
reason), and writes a unified diff to
`runs/<id>/40-synthesis/domain-improvements.patch`. It prints `N drafted, M dropped`
plus every dropped id with its gate error. The real `domains/` tree is never
touched.

## 3. Review the patch

The patch is a standard unified diff against `domains/<pack>/`. Note any dropped
improvements (e.g. `already declared in <pack>`, `unknown target_pack`, a validate
or markdown-structural error) and address them by hand or discard them. For `.md`
targets the gate only checks structure and rebuildability — the prose quality is
your review's responsibility.

A `domain.yaml` insertion is line-anchored: the hunk adds only the new list item and
leaves every other line of the file byte-identical, so a one-item addition is a
one-item diff. (The sole exception is converting an inline-empty list — e.g.
`regulatory_anchors: []` — into a block, which also un-inlines that one key line.)
The result is deterministic and applies cleanly; review the inserted entry.

## 4. Apply and re-validate

```bash
git apply runs/<id>/40-synthesis/domain-improvements.patch
apd-gauntlet validate-domain <pack>
apd-gauntlet build-domain-skill <packs…> --framework-version <v>
```

Commit the pack change as a normal authoring edit. B stops here: there is no
auto-PR and no closed loop back into the gauntlet.
