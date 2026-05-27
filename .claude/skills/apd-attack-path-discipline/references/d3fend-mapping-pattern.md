# D3FEND Mapping Pattern

This reference is the practical walk-through of section 6 (D3FEND must counter
ATT&CK) of the parent [SKILL.md](../SKILL.md). It shows, on two concrete
bottleneck edges, how the analyzer derives `candidate_d3fend[]`, partitions it
against existing capabilities, and what to emit when the D3FEND data file
returns no counters.

> **Field-name disambiguation.** `counters_attack[]` is the field name in
> `tools/apd_gauntlet/data/d3fend.json` — the raw attack-counter table that
> the analyzer reads. `counters[]` is the projected field name on each
> `candidate_d3fend[]` overlay item (the intersection of the d3fend
> technique's full `counters_attack[]` set with the bottleneck's
> `exposed_attack_techniques`). When this document refers to the input
> lookup it says `counters_attack[]`; when it refers to the overlay output
> shape it says `counters[]`.

The authoritative source is `tools/apd_gauntlet/data/d3fend.json`. The lookup
is mechanical: for each technique in the bottleneck edge's
`exposed_attack_techniques`, collect every `entries[*].d3fend_id` whose
`counters_attack[]` contains that technique. The overlay then projects each
hit into a `candidate_d3fend[]` item whose `counters[]` field carries the
intersection (sorted, deduped). Never extend the candidate list by name
similarity or by analogy to a related technique.

## Example 1: Bottleneck edge with multiple D3FEND counters

> **Note.** This example reflects the candidate set per
> `tools/apd_gauntlet/data/d3fend.json` as bundled with v1.4. The MITRE
> D3FEND attack-counter mapping evolves; if `apd-gauntlet refresh-d3fend`
> updates the data file, re-verify this candidate set against the refreshed
> source-of-truth before quoting it in design review.

### Set up

A bottleneck edge of type `compromisable_via_finding` sits on six of the
enumerated paths from `position:internet_unauth` to
`asset:member_portal_db`. The backing finding exposes one ATT&CK technique:

```yaml
exposed_attack_techniques:
  - T1078   # Valid Accounts
```

### D3FEND candidate lookup

Filtering `d3fend.json` entries where `counters_attack[]` contains `T1078`
yields seven candidates in the current dataset:

| D3FEND ID  | Name                          |
|------------|-------------------------------|
| D3-AA      | Agent Authentication          |
| D3-AL      | Account Locking               |
| D3-AM      | Access Modeling               |
| D3-CDP     | Change Default Password       |
| D3-RUAA    | Restore User Account Access   |
| D3-UAP     | User Account Permissions      |
| D3-ULA     | Unlock Account                |

This is the full `candidate_d3fend[]` for this edge.

**Why not D3-MFA or D3-NTSA?** Both techniques exist in `d3fend.json` and
their names sound related to credential abuse — but neither lists `T1078` in
its `counters_attack[]` array. Per rule 6 of the parent skill, the bundled
data file (not name-similarity) is the source of truth. This is the rule in
action: discipline says no, even when the names suggest yes.

### Partition by existing-capability backing

Assume the synthesizer's deduped capability set contains one record:

```yaml
- capability_id: cap-authn-0007
  goal: authenticity
  title: Member portal account lockout after repeated failures
  control_mappings:
    d3fend:
      - technique: D3-AL
        name: Account Locking
```

`D3-AL` appears in the candidate list, so it moves into
`existing_capability_backing[]`. The remaining six are net-new. The overlay
item on the bottleneck edge becomes (the shape conforms to
`schemas/defense-graph.schema.json`'s `bottleneck_overlays[]` item — flat
fields, no wrapping `d3fend_overlay:` key, no `edge_type`/`finding_id`):

```yaml
- edge_id: edge-0042
  paths_traversing: 6
  exposed_attack_techniques:
    - T1078
  candidate_d3fend:
    - d3fend_id: D3-AA
      counters: [T1078]
      rationale: D3FEND D3-AA (Agent Authentication) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
    - d3fend_id: D3-AL
      counters: [T1078]
      rationale: D3FEND D3-AL (Account Locking) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
    - d3fend_id: D3-AM
      counters: [T1078]
      rationale: D3FEND D3-AM (Access Modeling) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
    - d3fend_id: D3-CDP
      counters: [T1078]
      rationale: D3FEND D3-CDP (Change Default Password) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
    - d3fend_id: D3-RUAA
      counters: [T1078]
      rationale: D3FEND D3-RUAA (Restore User Account Access) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
    - d3fend_id: D3-UAP
      counters: [T1078]
      rationale: D3FEND D3-UAP (User Account Permissions) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
    - d3fend_id: D3-ULA
      counters: [T1078]
      rationale: D3FEND D3-ULA (Unlock Account) counters ATT&CK T1078 per MITRE D3FEND attack-counter mapping
  existing_capability_backing:
    - d3fend_id: D3-AL
      capability_ids:
        - cap-authn-0007
  net_new_d3fend:
    - D3-AA
    - D3-AM
    - D3-CDP
    - D3-RUAA
    - D3-UAP
    - D3-ULA
```

Each `candidate_d3fend[]` item's `counters[]` array is the intersection of
that D3FEND technique's `counters_attack[]` (from `d3fend.json`) with this
edge's `exposed_attack_techniques`. For this edge that intersection is the
single technique `T1078`.

### Resulting gap-finding narrative

The analyzer emits one `disposition: gap` attack-path finding referencing
`edge-0042`. The narrative quotes the partition directly, without paraphrase:

> The member-portal database is reachable from the internet via six paths that
> all traverse edge-0042 (T1078, Valid Accounts). One existing capability,
> `cap-authn-0007`, supplies D3-AL (Account Locking) along this edge. The
> remaining D3FEND techniques that the MITRE attack-counter table maps to
> T1078 — D3-AA, D3-AM, D3-CDP, D3-RUAA, D3-UAP, D3-ULA — are net-new with no
> backing capability in the current synthesizer output.

The recommendation must name a specific net-new D3FEND technique and the
edge it covers (per `apd-evidence-discipline` rule 4, reproduce before
recommend); generic "add MFA" prose is rejected because `D3-MFA` is not in
this edge's `candidate_d3fend[]`.

## Example 2: Bottleneck edge with NO D3FEND counters

### Set up

A different bottleneck edge sits on three paths, backed by a finding whose
`mitre_attack[]` lists a single technique that the D3FEND attack-counter table
does not currently map:

```yaml
exposed_attack_techniques:
  - T1499   # Endpoint Denial of Service
```

### D3FEND candidate lookup

Filtering `d3fend.json` entries where `counters_attack[]` contains `T1499`
returns an empty set. `candidate_d3fend[]` is `[]`. The same outcome applies
for any other technique with no counters in the current data file (for
example, `T1530` or `T1657`).

The overlay records the empty partitions directly — there is no special
status field; the absence of candidates IS the signal:

```yaml
- edge_id: edge-0107
  paths_traversing: 3
  exposed_attack_techniques:
    - T1499
  candidate_d3fend: []
  existing_capability_backing: []
  net_new_d3fend: []
```

The shape above matches `schemas/defense-graph.schema.json`'s
`bottleneck_overlays[]` item exactly: `edge_id`, `paths_traversing`,
`exposed_attack_techniques`, `candidate_d3fend`, `existing_capability_backing`,
`net_new_d3fend`. No other fields are permitted (the schema sets
`additionalProperties: false`).

### Discipline rule

This is the case where the overlay path produces NO `gap` finding. Per
`tools/apd_gauntlet/attack_path/findings.py`'s `_finding_from_bottleneck`,
a gap-flavored attack-path finding is emitted only when `net_new_d3fend` is
non-empty AND `existing_capability_backing` is empty. Here both are empty,
so the overlay contributes nothing to the apath-* finding stream.

The path-level risk is not silently dropped, however: the underlying
`compromisable_via_finding` edge still drives a path-flavored finding via
`_finding_from_path` (a risk or uncertainty disposition depending on
feasibility and severity_sum). The advisor's narrative for that
path-finding must call out the empty candidate set explicitly rather than
implying D3FEND coverage:

> Edge edge-0107 exposes T1499 (Endpoint Denial of Service). No D3FEND
> technique counters T1499 in the current
> `tools/apd_gauntlet/data/d3fend.json` data file, so `candidate_d3fend[]`
> is empty and no D3FEND-grounded recommendation is available. The
> recommendation must be either a custom mitigation, an external
> compensating control, or an explicit acceptance of the residual risk by
> the architecture owner.

Do not invent a D3FEND ID to fill the slot. Do not pattern-match to a related
technique whose `counters_attack[]` lists a sibling ATT&CK ID. Do not add an
ad-hoc status field to the overlay — the schema forbids it, and the empty
`candidate_d3fend[]` is itself the honest signal.

## Cross-references

- Parent: [../SKILL.md](../SKILL.md) — full discipline rules, especially
  section 6.
- Module: `tools/apd_gauntlet/attack_path/d3fend_overlay.py` — the
  implementation that produces each `bottleneck_overlays[]` item (the
  `candidate_d3fend` / `existing_capability_backing` / `net_new_d3fend`
  partition).
- Data: `tools/apd_gauntlet/data/d3fend.json` — the projected
  attack-counter table; refresh via the `apd-gauntlet refresh-d3fend` CLI.
- Severity calibration: `apd-evidence-discipline` skill — the severity rubric
  and the reproduce-before-recommend rule that govern gap-finding text.
