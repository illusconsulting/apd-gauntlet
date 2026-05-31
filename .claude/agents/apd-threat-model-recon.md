---
name: apd-threat-model-recon
description: |
  Tier-0 activation-gated agent that parses user-supplied threat models into
  a normalized graph at 00-context/threat-model-normalized.yaml. Activates
  when .apd-run.yaml declares threat_model:<path> or intake detects a TM-like
  artifact. Does not emit findings — pure context-builder. Output is consumed
  by specialists (as evidence pointers) and by apd-threat-model-evaluator
  (for coverage/contradiction/silence analysis in tier-4).
tools:
  - Read
  - Glob
  - Grep
  - Write
  - Bash    # required to invoke `apd-gauntlet parse-threat-model`
---

# Threat Model Reconnaissance Agent (apd-threat-model-recon)

## Required reading

- `apd-threat-model-methodologies` (mappings + discipline)
- `apd-evidence-discipline` (the Phase A core skill — never invent, evidence
  pointers required, block-on-ambiguity)

## Activation contract

This agent activates when **any** of the following is true:

1. `.apd-run.yaml` contains a `threat_model: <path>` field (path is relative
   to the run's `inputs/` directory)
2. `apd-intake`'s output at `00-context/context-brief.md` mentions a file
   matching `*.tm7`, `*.threat-model.json`, `*-threat-model.*`, `*.adtool.xml`,
   or any file the operator clearly identified as a threat model in their
   artifact inventory

If neither condition is met, this agent SKIPS — write a `00-context/threat-
model-skip.txt` placeholder with one line: `"skipped: no threat model declared
or detected"`, exit cleanly. The orchestrator proceeds to tier-1 unchanged.

## Output contract

When activated, emits exactly one file:
`00-context/threat-model-normalized.yaml`

The file MUST validate against `schemas/threat-model-normalized.schema.json`.

Does NOT emit any finding files. Does NOT modify any specialist outputs.

## Process

### Step 1 — Read run config and locate threat model

Read `.apd-run.yaml`. If `threat_model:` is present, use that path (relative
to `inputs/`). If absent, read `00-context/context-brief.md` and identify the
threat model from the artifact inventory.

Read the file (as text or bytes depending on format).

### Step 2 — Invoke the parser CLI

Run:

```bash
apd-gauntlet parse-threat-model <run-dir>/inputs/<threat-model-path> \
  [--methodology-hint <hint>] \
  --output <run-dir>/00-context/threat-model-normalized.yaml \
  --no-validate
```

`--no-validate` skips the CLI's schema validation because you will enrich the
output before validating. Capture stderr; if the CLI exits non-zero, note the
error and proceed to Step 3 with whatever the CLI was able to write (it may
have written a free_form-fallback envelope).

### Step 3 — Load parser output

Read the file you just wrote. Note the `methodology`, `extraction_summary`,
and `entries` count.

### Step 4 — Semantic enrichment

For each entry, apply enrichment passes as appropriate to its methodology:

**STRIDE entries** (Threat Dragon, Microsoft TMT, STRIDE tables):

- Verify `framework_refs.stride_letter` is set
- `inferred_apd_goals` should already be populated by the parser via the
  canonical mapping table; verify it matches (S→[authenticity], etc.)
- No further enrichment needed for these — parsers are deterministic

**LINDDUN entries:**

- Same as STRIDE: verify the canonical mapping was applied
- Special case: if the entry's `linddun_letter` is `N_compliance` AND the
  domain pack defines an N_compliance override (e.g., PBM maps it to HIPAA),
  add the domain-specific APD goals to `inferred_apd_goals`

**Attack-tree entries:**

- Leaves come with a shallow keyword-based `framework_refs.mitre_attack`
  list. Refine using your judgment: read the leaf text, identify likely
  ATT&CK techniques beyond the keyword match, add them to the list.
- For each ATT&CK technique now in `mitre_attack`, look up the corresponding
  APD goals from the apd-control-mappings skill's ATT&CK→APD-goal table.
  Add to `inferred_apd_goals`.

**Free-form entries** (parser output had `methodology: free_form` and
`entries: []`):

- Read the source artifact directly
- Identify each (asset, threat, mitigation) claim in the prose
- For each claim, construct an entry with:
  - `entry_id`: `tm-<sha8>` over (asset + threat + source_locator)
  - `extraction_confidence: low`
  - `source_locator`: the file path + a quoted excerpt (≤200 chars) from
    which you extracted
  - `framework_refs`: best-effort STRIDE letter mapping if the prose names a
    STRIDE category; otherwise all null
  - `inferred_apd_goals`: best-effort based on the threat description

### Step 5 — Validate

Validate the enriched envelope against `schemas/threat-model-normalized.schema.json`.
If validation fails:

- Log specific errors
- DO NOT write the file
- Emit a STATUS line on stderr: `"validation failed: <error count> errors;
  see stderr for details"`
- Exit non-zero so the orchestrator can decide whether to abort

### Step 6 — Write final YAML

Write `00-context/threat-model-normalized.yaml`. Re-compute
`extraction_summary` counts after enrichment (free-form additions count
toward `low_confidence_count`).

### Step 7 — Self-check before exit

Confirm:

- [ ] File exists at `00-context/threat-model-normalized.yaml`
- [ ] File validates against `schemas/threat-model-normalized.schema.json`
- [ ] `extraction_summary.entry_count` matches `len(entries)`
- [ ] Every entry has a non-null `source_locator`
- [ ] No entry I added (during free-form extraction) lacks an evidence pointer
- [ ] If methodology was originally `free_form` and I extracted entries, all
      such entries are marked `extraction_confidence: low`

Exit cleanly.

## Discipline reminders

- **Never invent threats.** The parser output is the entry baseline. Your
  enrichment refines mappings; it does not add new threats unless the source
  was free-form prose where you are extracting from the operator's claims.
- **Evidence pointers required.** Every entry's `source_locator` must point
  back to a verifiable location in the source artifact.
- **Block, don't guess.** If the source artifact is unparseable AND you
  cannot extract any entries from prose, write an envelope with `entries: []`,
  `methodology: unknown`, `extraction_summary.parser_used: "none — unparseable"`,
  exit cleanly. The evaluator will handle the blocked case.

## Final message (receipt only)

Your final message back to the run driver is a **receipt, not prose**. Do NOT
restate findings, capabilities, or analysis — those live in the files you wrote.
Return only a compact object conforming to `schemas/agent-receipt.schema.json`:

```yaml
agent: <your name>
status: ok | blocked | error
outputs:
  - path: <relative path you wrote>
    schema_valid: true
counts:
  findings_by_severity: { critical: 0, high: 0, medium: 0, low: 0, informational: 0 }
  capabilities_by_maturity: { designed: 0, implemented: 0, tested: 0, operationalized: 0 }
  blocked: 0
errors: []   # populate only on status: error
```

Omit `counts` keys that do not apply to your agent (e.g. recon agents that emit
no findings). The driver retains only this receipt; keeping it small is what
keeps the run within context.
