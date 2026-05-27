# D3FEND Mapping Pattern

This reference is the practical walk-through of section 6 (D3FEND must counter
ATT&CK) of the parent [SKILL.md](../SKILL.md). It shows, on two concrete
bottleneck edges, how the analyzer derives `candidate_d3fend[]`, partitions it
against existing capabilities, and what to emit when the D3FEND data file
returns no counters.

The authoritative source is `tools/apd_gauntlet/data/d3fend.json`. The lookup
is mechanical: for each technique in the bottleneck edge's
`exposed_attack_techniques`, collect every `entries[*].d3fend_id` whose
`counters_attack[]` contains that technique. Never extend the candidate list by
name similarity or by analogy to a related technique.

## Example 1: Bottleneck edge with multiple D3FEND counters

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

This is the full `candidate_d3fend[]` for this edge. The analyzer does NOT
extend it with related-by-name techniques (e.g. `D3-MFA`, `D3-NTSA`); those
entries do not list `T1078` in their `counters_attack[]` and are therefore not
candidates for this edge under the discipline rule.

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
`existing_capability_backing[]`. The remaining six are net-new. The overlay on
the bottleneck edge becomes:

```yaml
- edge_id: edge-0042
  edge_type: compromisable_via_finding
  finding_id: f-authn-0012
  exposed_attack_techniques:
    - T1078
  d3fend_overlay:
    candidate_d3fend:
      - D3-AA
      - D3-AL
      - D3-AM
      - D3-CDP
      - D3-RUAA
      - D3-UAP
      - D3-ULA
    existing_capability_backing:
      - d3fend_id: D3-AL
        capability_id: cap-authn-0007
    net_new_d3fend:
      - D3-AA
      - D3-AM
      - D3-CDP
      - D3-RUAA
      - D3-UAP
      - D3-ULA
```

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

The overlay records the empty list and the lookup_status explicitly:

```yaml
- edge_id: edge-0107
  edge_type: compromisable_via_finding
  finding_id: f-avail-0003
  exposed_attack_techniques:
    - T1499
  d3fend_overlay:
    candidate_d3fend: []
    existing_capability_backing: []
    net_new_d3fend: []
    lookup_status: no_counters_in_d3fend
```

### Discipline rule

The analyzer still emits the gap-finding for the path — the path exists and
the edge exposes a real ATT&CK technique. The finding text says so explicitly
rather than silently dropping the edge:

> Edge edge-0107 exposes T1499 (Endpoint Denial of Service). No D3FEND
> technique is mapped to T1499 in the current `tools/apd_gauntlet/data/d3fend.json`
> data file, so `candidate_d3fend[]` is empty. The advisor should treat this
> as an uncovered gap: there is no D3FEND counter to recommend; consider a
> custom mitigation, an external compensating control, or an explicit accept
> of the residual risk by the architecture owner.

Do not invent a D3FEND ID to fill the slot. Do not pattern-match to a related
technique whose `counters_attack[]` lists a sibling ATT&CK ID. The empty
`candidate_d3fend[]` plus the `lookup_status: no_counters_in_d3fend` flag is
the honest output.

## Cross-references

- Parent: [../SKILL.md](../SKILL.md) — full discipline rules, especially
  section 6.
- Module: `tools/apd_gauntlet/attack_path/d3fend_overlay.py` — the
  implementation that produces the `d3fend_overlay` block on each bottleneck
  edge.
- Data: `tools/apd_gauntlet/data/d3fend.json` — the projected
  attack-counter table; refresh via the `apd-gauntlet refresh-d3fend` CLI.
- Severity calibration: `apd-evidence-discipline` skill — the severity rubric
  and the reproduce-before-recommend rule that govern gap-finding text.
