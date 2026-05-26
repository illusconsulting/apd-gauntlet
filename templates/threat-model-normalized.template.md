# Normalized Threat Model Template

> This template documents the canonical shape of `00-context/threat-model-normalized.yaml`,
> emitted by the `apd-threat-model-recon` agent (tier-0).
>
> Validates against `schemas/threat-model-normalized.schema.json`.

## When this artifact is produced

`apd-threat-model-recon` produces this file when activated (per Task B-20's
activation contract): the operator declared `threat_model: <path>` in
`.apd-run.yaml`, or `apd-intake` detected a TM-like artifact in the
inputs directory.

The file is consumed by:
- All tier-1/2/3 specialist agents (as an evidence pointer, alongside their
  primary inputs from intake)
- `apd-threat-model-evaluator` (tier-4) for coverage / contradiction /
  silence analysis

## Output shape

```yaml
schema_version: 1
generated_by: threat_model_recon
source_artifact: inputs/threat-model.json   # path relative to run dir
methodology: stride                          # or: linddun | attack_tree | pasta | vast | trike | free_form | unknown
extraction_summary:
  entry_count: 12
  high_confidence_count: 10
  medium_confidence_count: 1
  low_confidence_count: 1
  parser_used: threat_dragon                 # or: microsoft_tmt | stride_table.md | linddun_table.csv | attack_tree.adtool_xml | etc.
entries:
  # ----- A high-confidence STRIDE entry from a structured parser -----
  - entry_id: tm-a1b2c3d4
    asset: claim-ingress-API
    threat: "Pharmacy credential theft via phishing"
    mitigation: "MFA required on pharmacy portal; rotating short-lived tokens"
    methodology: stride
    source_locator: "diagrams[0].cells[3].threats[0]"
    extraction_confidence: high
    framework_refs:
      stride_letter: S
      linddun_letter: null
      attack_tree_position: null
      mitre_attack: []           # parsers don't infer ATT&CK from STRIDE; recon agent may add
    inferred_apd_goals: [authenticity]

  # ----- A medium-confidence entry where ATT&CK was inferred -----
  - entry_id: tm-5e6f7g8h
    asset: "(attack-tree node)"   # attack trees model adversary actions, not assets
    threat: "SMB lateral movement to adjudication network segment"
    mitigation: null               # attack-tree leaves typically have no mitigation
    methodology: attack_tree
    source_locator: "root/lateral-movement-from-vendor/smb-lateral-movement (OR)"
    extraction_confidence: medium  # ATT&CK heuristic match, not a structured assertion
    framework_refs:
      stride_letter: null
      linddun_letter: null
      attack_tree_position: "root/lateral-movement-from-vendor/smb-lateral-movement (OR)"
      mitre_attack: [T1021.002]
    inferred_apd_goals: [authenticity, integrity]   # from ATT&CK→APD-goal lookup

  # ----- A low-confidence entry from free-form prose extraction -----
  - entry_id: tm-9i0j1k2l
    asset: member-portal/profile-edit
    threat: "Cross-site scripting via name field"
    mitigation: "Server-side HTML escaping documented in threat-model.md"
    methodology: free_form
    source_locator: "inputs/threat-model.md, ~line 47: 'profile edit form must escape...'"
    extraction_confidence: low     # LLM-extracted from prose — fallible
    framework_refs:
      stride_letter: T             # best-effort inference from prose
      linddun_letter: null
      attack_tree_position: null
      mitre_attack: []
    inferred_apd_goals: [integrity]
```

## Field semantics

### `methodology` (envelope)

The dominant methodology of the source document. When mixed methodologies
appear in one document (rare), choose the one with the most entries. Use
`unknown` only when the parser produced zero entries AND LLM extraction
yielded nothing.

### `extraction_summary.parser_used`

The Python parser module name (or `"none — <reason>"` when the recon agent
did LLM extraction directly). Useful for debugging and for the operator to
understand how the file was produced.

### `entries[*].asset`

For STRIDE / LINDDUN: the component or data-flow name (from the TM author's
labels). For attack trees: always `"(attack-tree node)"` — attack trees
model adversary actions, not asset surfaces.

### `entries[*].mitigation`

The mitigation text from the TM, when present. `null` when:
- The TM author did not provide a mitigation
- The format does not have a mitigation column (STRIDE-per-element tables)
- The entry is an attack-tree leaf (leaves model attacker actions; the
  mitigation perspective is on the defender side)

### `entries[*].extraction_confidence`

- **high**: structural parser extracted from a well-formed file (Threat
  Dragon JSON, .tm7 XML, STRIDE/LINDDUN tables)
- **medium**: heuristic mapping applied (attack-tree leaf got ATT&CK
  technique via keyword match; recon agent inferred mapping beyond the
  parser's output)
- **low**: LLM extraction from free-form prose; the agent's interpretation
  could be wrong

This field gates evaluator behavior — low-confidence entries cannot drive
contradiction findings (only uncertainty / silence). See Rule 3 in
`apd-threat-model-methodologies` skill.

### `entries[*].framework_refs`

One field per methodology; the parser sets the relevant one, leaves
others null. The agent may add `mitre_attack` entries during enrichment.

### `entries[*].inferred_apd_goals`

Derived via the canonical mapping tables in
`tools/apd_gauntlet/threat_model/mappings.py` (STRIDE/LINDDUN) or the
ATT&CK→APD-goal lookup in `apd-control-mappings` skill. Empty `[]` is
acceptable when the entry has no mapping basis (rare; usually means the
parser misfired or the prose was unclear).

## Discipline reminders for the recon agent

See `apd-threat-model-methodologies` skill. Critical rules:

- **Never invent threats.** Parser output is the entry baseline.
- **Low-confidence is honest, not lazy.** Mark prose extractions `low`;
  don't optimistically claim `medium` to make the file look better.
- **Block, don't fabricate.** If the source is unparseable, emit empty
  entries with `methodology: unknown`. The evaluator handles the blocked
  case.
