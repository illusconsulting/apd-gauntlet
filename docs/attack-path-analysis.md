# Attack-Path Analysis (v1.4+)

When a run declares crown jewels and attacker positions, the APD Gauntlet's
tier-4 `apd-attack-path-analyzer` performs BloodHound-style enumeration over
a graph built from intake artifacts, threat-model entries, code evidence,
specialist findings, and confirmed capabilities. It surfaces the highest-
leverage paths an attacker could take from each declared position to each
declared crown jewel, identifies the bottleneck edges those paths share,
and recommends D3FEND-backed defensive investments only where the
underlying ATT&CK techniques are documented in upstream evidence.

This document is the operator guide for that analyzer. It covers what the
analyzer is (and is not), how to declare crown jewels and attacker
positions, how to tune enumeration bounds, how to read the four output
artifacts, how to interpret the bundled Mermaid diagrams, what the four
finding flavors mean, and the common pitfalls.

## What attack-path analysis is

Attack-path analysis is BloodHound-style enumeration *over a partial
graph*. The graph is assembled exclusively from artifacts the gauntlet
already trusts:

| Source | Contribution |
| --- | --- |
| `00-context/asset-inventory.yaml` | Assets, trust boundaries, data classifications |
| `00-context/threat-model-normalized.yaml` | `network_reachable` edges, attacker-surface entries |
| `00-context/code-evidence-index.yaml` | `data_resides_on` / `trusts` edges from declared call graphs |
| `10-trustworthiness/`, `20-scalability/`, `30-auditability/` findings | `compromisable_via_finding` edges with severity and confidence |
| `40-synthesis/deduped-capabilities.yaml` | Mitigation overlays that reduce path feasibility |

The analyzer **never invents nodes or edges**. If your intake does not
mention a service, no node exists for it. If the threat model never
declares a reachability arc, no `network_reachable` edge exists. This is
intentional: a partial graph that admits its gaps is more honest than a
fabricated complete one. The corollary is on you, the operator: **never
claim all paths are enumerated**. The output is a top-N view bounded by
the enumeration knobs below, not an exhaustive proof.

The analyzer is also bound by the discipline rules in
`apd-attack-path-discipline`. The two that matter most to operators are:

1. **D3FEND-must-counter-ATT&CK.** A D3FEND defensive technique can be
   recommended only when the underlying bottleneck edge exposes an
   ATT&CK technique through a specialist finding's `control_mappings`.
   No ATT&CK mapping, no D3FEND counter.
2. **Block-on-missing-crown-jewels.** A run that declares crown jewels in
   the domain pack but explicitly empties them in `.apd-run.yaml`
   produces a `disposition: blocked` finding rather than a silent skip.
   See "When it activates" below.

## When it activates

The analyzer is activation-gated. Whether it runs depends on the
intersection of the domain pack's defaults and the run-config override:

| Domain pack `crown_jewels` | Run-config override | Behavior |
| --- | --- | --- |
| Non-empty | Absent | Run with domain-pack defaults |
| Non-empty | Non-empty | Run with run-config values (full override) |
| Empty / undeclared | Absent | Skipped silently — writes `40-synthesis/attack-path-analyzer-skipped.txt` with the reason |
| Empty / undeclared | Non-empty | Run with run-config values |
| Non-empty | Explicitly `crown_jewels: []` | **Blocked** — emits a `disposition: blocked` finding pointing the operator at this doc |

The "explicitly empty" case is treated as a deliberate operator
declaration that there are no crown jewels for this run, which is almost
always a mistake when the domain itself declares some. The block prevents
a quiet skip from masking a misconfigured run.

The same activation table applies to `attacker_positions`. If the
attacker side is empty (no domain declaration and no run-config
declaration), the analyzer cannot enumerate any source nodes and skips
silently with the same `attack-path-analyzer-skipped.txt` reason.

## Declaring crown jewels

Crown jewels are declared in two places, with run-config winning when
both are present.

### In the domain pack (preferred default)

The PBM domain pack (`domains/pbm/domain.yaml`) declares three crown
jewels — the canonical pattern:

```yaml
crown_jewels:
  - pattern: phi_store
    description: "Member PHI store carrying demographics, claims history, prescriber/diagnosis associations subject to HIPAA breach-notification thresholds."
  - pattern: pde_submission_pipeline
    description: "CMS Part D Prescription Drug Event submission pipeline — submission integrity is regulator-anchored under CMS rules and material to plan revenue."
  - pattern: claim_adjudication_engine
    description: "Real-time claim adjudication engine — pricing accuracy and decision integrity drive member out-of-pocket and pharmacy reimbursement."
```

Each entry pairs a `pattern` (matched against asset names and data
classifications in the inventory; the analyzer also strips a trailing
`_pipeline` suffix when matching against data classifications) with a
short rationale. The rationale ends up in `attack-path-report.md` so an
auditor can see why a jewel was declared.

### In `.apd-run.yaml` (per-run override)

A run can curate a subset or extend the domain defaults:

```yaml
run_id: apd-20260601-claim-event-bus
domain: pbm
crown_jewels:
  - phi_store
  - pde_submission_pipeline
attacker_positions:
  - external_internet
  - compromised_pharmacy_credential
  - compromised_vendor_integration
attack_path_analysis:
  max_hop: 6
  max_paths_per_pair: 25
  bottleneck_threshold: 4
```

The bundled `examples/apd-20260601-claim-event-bus/.apd-run.yaml`
demonstrates this exact override: two of the three domain-pack jewels
are selected, three of the five domain-pack attacker positions, and the
enumeration is tightened from the defaults.

To **deliberately block** the analyzer for a run that should not perform
attack-path analysis (e.g., a smoke-test run where you do not want the
analyzer to fire), set `crown_jewels: []` explicitly. The analyzer will
emit a `disposition: blocked` finding rather than silently skip — see
"When it activates" above.

## Declaring attacker positions

Attacker positions follow the same shape as crown jewels. The PBM domain
pack declares five canonical positions:

```yaml
attacker_positions:
  - position: external_internet
    description: "Untrusted external internet client; the default external attacker position for any internet-facing surface."
  - position: compromised_pharmacy_credential
    description: "An attacker holding a valid pharmacy-submitter credential through phishing, credential stuffing, or insider abuse at a pharmacy partner."
  - position: compromised_vendor_integration
    description: "An attacker who has compromised a third-party vendor's integration credentials (e.g., a benefits-management vendor or analytics partner)."
  - position: insider_with_member_service_role
    description: "An insider holding a legitimate member-services role but acting outside their minimum-necessary scope (e.g., bulk PHI export, unauthorized member lookups)."
  - position: compromised_dev_workstation
    description: "An attacker who has compromised a developer or operator workstation with production deployment or break-glass access."
```

Each position becomes a source node in the enumeration. The analyzer
generates one Cartesian pair per declared `(attacker_position,
crown_jewel)` tuple and runs bounded enumeration on each pair. With the
PBM defaults of 5 positions and 3 jewels that is 15 pairs per run. The
"Common pitfalls" section below explains why this can blow up quickly.

A run-config override is a flat list of position names (the same shape
as crown jewels) and fully replaces the domain defaults.

## Tuning enumeration

Three knobs control enumeration. They live under `attack_path_analysis:`
in `.apd-run.yaml`:

| Knob | Default | Range | When to raise | When to lower |
| --- | --- | --- | --- | --- |
| `max_hop` | `8` | `2`–`12` | A complex backplane where critical paths legitimately span many trust boundaries (e.g., contractor laptop → VPN → jumpbox → app server → DB) | The graph is small and all interesting paths are short; raising the bound just inflates redundant traversals |
| `max_paths_per_pair` | `50` | `1`–`200` | You want a richer top-N view per (attacker, jewel) pair for an audit deliverable | Smoke-test runs or quick triage — `5` or `10` keeps the output focused |
| `bottleneck_threshold` | `5` | `2`–`50` | Sparse graphs where the default produces zero bottlenecks; lower it to `2` or `3` to surface edges appearing on a handful of paths | Dense graphs where almost every edge appears on many paths — raise it so only true chokepoints emerge |

The output is **always** top-N per pair: paths are sorted by descending
`severity_sum`, then ascending `hop_count`, then descending feasibility,
and truncated at `max_paths_per_pair`. When truncation happens the
`attack-path-report.md` headline summary calls it out explicitly
("**3** pair(s) truncated at `max_paths_per_pair=25`"); the analyzer
never claims an exhaustive enumeration.

## Reading the outputs

The analyzer writes five artifacts. The bundled
`examples/apd-20260601-claim-event-bus/expected/` run is the canonical
reference; open it alongside this guide.

| Artifact | What's in it | Bundled example |
| --- | --- | --- |
| `40-synthesis/asset-graph.yaml` | Nodes, edges, provenance, confidence | 16 nodes (8 assets, 3 identities, 3 attacker positions, 2 crown jewels), 43 edges |
| `40-synthesis/attack-paths.yaml` | Enumerated paths and the bottleneck-edge set | 75 paths, 24 bottleneck edges, `enumeration_parameters` block |
| `40-synthesis/defense-graph.yaml` | D3FEND overlay on bottleneck edges | 0 net-new D3FEND counters (see below) |
| `40-synthesis/attack-path.findings.yaml` | One finding per enumerated path or bottleneck | uncertainty / risk / gap / blocked dispositions |
| `40-synthesis/attack-path-report.md` | Human-readable executive summary with the Mermaid diagram | Headline summary, bottleneck table, path catalogue |

Note the **dot** in `attack-path.findings.yaml`. The dot-separated naming
distinguishes analyzer-emitted findings from synthesis dedup output;
older drafts of the spec used `attack-path-findings.yaml` (hyphenated).
If you see the hyphenated form in a generated run, the analyzer is on a
pre-C-20 build.

### The "0 net-new D3FEND" case

The bundled `claim-event-bus` example has **24 bottleneck edges and 0
net-new D3FEND counters**, which is the canonical low-ATT&CK-coverage
disposition. The reason is deterministic: D3FEND counters can be added
only on bottleneck edges that expose an ATT&CK technique through the
backing finding's `control_mappings.mitre_attack` block. In the bundled
example, 23 of the 24 bottlenecks are `network_reachable`, `trusts`, or
`data_resides_on` edges (inventory- and TM-derived; no ATT&CK link).
The single `compromisable_via_finding` bottleneck edge backs a finding
(`tmeval-eeee5555`) with no ATT&CK mapping, so the D3FEND-must-counter-
ATT&CK rule produces zero recommendations.

That outcome is informative, not a bug. It flags a gap in upstream
specialist evidence — the appropriate response is to revisit the
backing findings and ask whether they should carry ATT&CK mappings,
not to relax the discipline rule.

## Interpreting Mermaid diagrams

`attack-path-report.md` includes a `flowchart LR` rendering of the asset
graph. The rendering rules follow the C-13 Mermaid contract:

- **Node labels** are short asset identifiers (`atk_external_internet`,
  `asset_claim_ingress_api`, `jewel_phi_store`). Crown jewels and
  attacker positions get distinct shapes so they read as endpoints.
- **Edge labels** show `<edge_type>/<confidence>` — e.g.,
  `network_reachable/high`, `compromisable_via_finding/medium`.
- **Bidirectional `trusts` edges** are collapsed into a single
  bidirectional arrow rather than two parallel arrows; the report's
  bottleneck table is the authoritative source if you need to count
  directional edges.
- **The 50-node cap.** When the asset graph has more than 50 nodes the
  diagram is partitioned by `attacker_position`: one Mermaid block per
  attacker, scoped to the subgraph reachable from that source. This
  preserves readability without dropping nodes silently. The bundled
  16-node example fits in a single block.
- The report always states the node count next to the diagram so an
  auditor can see immediately whether they are looking at a single
  view or a partitioned one.

The diagram is a *visual aid* over the same graph in
`asset-graph.yaml`; if the diagram and the YAML disagree, the YAML
wins.

## The four finding flavors

The analyzer emits `apath-*` findings under
`40-synthesis/attack-path.findings.yaml`. Every finding carries
evidence pointers back into the asset graph, the attack-paths file, and
the backing specialist findings. The four dispositions are:

| Disposition | Flavor | When emitted | What to do |
| --- | --- | --- | --- |
| `risk` | **High-feasibility, no mitigation** | Path with feasibility floor `high` and zero capability overlays | Treat as a real exposure — add a compensating capability on a high-confidence edge or remove the reachability assumption upstream |
| `uncertainty` | **Low-feasibility OR partial mitigation** | Path with feasibility floor `medium`/`low`, or a path that has at least one capability overlay but is not fully mitigated | Investigate the lowest-confidence edge on the path; if you can promote it to `high` confidence the finding promotes to `risk` |
| `gap` | **Bottleneck without D3FEND coverage** | Bottleneck edge with no D3FEND-backed capability defending it | Either add a D3FEND-backed capability to the deduped-capabilities set, or accept the gap with an ADR |
| `blocked` | **No crown jewels declared** | Run that explicitly empties `crown_jewels` despite the domain declaring some | Read this doc, decide whether to restore the domain defaults or accept the block in a run-config comment |

Severity floors track the impact-to-PBM rubric in
`apd-evidence-discipline`. The analyzer never invents severity — it
copies the `severity_sum` from the path and the per-finding ceiling
from the lowest-confidence edge on the path.

## Common pitfalls

### Over-declaring attacker positions

The enumeration cost is multiplicative. With the PBM defaults of **5
attacker positions × 3 crown jewels × `max_paths_per_pair=50`** the
output ceiling is 750 path records. Most of those records will share
identical tail edges and produce visually redundant entries in the
report. If your run is over-declaring positions, prefer raising
`bottleneck_threshold` (so only true chokepoints surface) over lowering
`max_paths_per_pair` (which throws away high-severity tail paths).

### Under-declaring crown jewels

If neither the domain pack nor the run-config declares any crown
jewels, the analyzer skips silently with a `attack-path-analyzer-
skipped.txt` reason. The skip is not a failure — but it is invisible to
anyone reading the synthesis report later. If a run *should* be doing
attack-path analysis and is not, check both the domain pack and the
run-config for a missing or empty `crown_jewels:` block before assuming
the analyzer is broken.

### Confusing path feasibility with severity

Feasibility is a property of the path (the floor of edge confidences
along it). Severity is a property of the *finding* the path produces
(the lowest-confidence specialist finding on a `compromisable_via_finding`
edge sets the ceiling). A high-feasibility path with zero capability
overlays may still emit a `medium` severity finding if every backing
specialist finding was `medium`. The analyzer does not promote
severity to match feasibility — that would be inventing impact.

### Treating the partial graph as exhaustive

Attack-path analysis is enumeration over a partial graph built from the
evidence the gauntlet was handed. Paths that do not appear in the
output may still exist in the real system if their constituent edges
were not declared in the intake. The report's headline always names
the number of paths enumerated and the number of pairs truncated at
the cap — quote those numbers, not "all attack paths".

## Reference data refresh

D3FEND counter-mappings are sourced from the MITRE D3FEND release that
the gauntlet was built against. To keep them current with new D3FEND
releases run:

```bash
apd-gauntlet refresh-d3fend
```

The refresh updates `reference_data/d3fend/` in-place. Re-running an
existing attack-path analysis after a refresh will pick up the new
counter-mappings without any other configuration change. The same
cadence applies to the companion `refresh-mitre`, `refresh-cwe`, and
`refresh-owasp` commands — see `docs/taxonomy-mappings.md` for the
full reference-data lifecycle.

## Design rationale

See `docs/adrs/0010-attack-path-analysis-on-partial-graphs.md` for the
full decision record — why BloodHound-style
enumeration over a partial graph, why the D3FEND-must-counter-ATT&CK
discipline, why bounded enumeration with explicit truncation, and the
two-sources-of-truth model for crown jewels (domain defaults plus
run-config override).
