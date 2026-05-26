# Threat Model Evaluation (v1.3+)

When a tech plan includes a threat model — STRIDE diagram, LINDDUN privacy
analysis, attack tree, or even a narrative document — the APD Gauntlet can
evaluate it against the specialist findings: surfacing coverage gaps,
contradictions between TM claims and what specialists actually found, and
silences (surfaces specialists flagged that the TM never addressed).

## What's supported

### Native parsing (high extraction confidence)

| Methodology | Format | Notes |
|---|---|---|
| STRIDE | OWASP Threat Dragon JSON (`.json`) | Auto-detected by `{summary, detail.diagrams}` shape |
| STRIDE | Microsoft TMT (`.tm7`) | XML; XXE-safe parser via lxml |
| STRIDE | Per-element tables (`.md` / `.csv`) | Header: `S T R I D E` or full category names |
| LINDDUN | Per-element tables (`.md` / `.csv`) | Header: `L I N D D U N` with column-position disambiguation |
| Attack tree | Indented prose (`.txt`) | 4-space or tab indentation; OR/AND keyword gates |
| Attack tree | ADTool XML (`.adtool.xml`, `.xml`) | `refinement="conjunctive\|disjunctive"` |
| Attack tree | Generic JSON (`.json`) | `{goal, gate, children[]}` convention |

### Reduced-fidelity support (low extraction confidence)

PASTA, VAST, Trike, and free-form prose are accepted via the
`--methodology-hint` flag or by setting `methodology_hint:` in
`.apd-run.yaml`. The recon agent's LLM does the extraction; the entries are
marked `extraction_confidence: low` and cannot drive contradiction findings
(only silence / uncertainty). See "Confidence cascading" below.

## Declaring a threat model

### In `.apd-run.yaml`

```yaml
run_id: apd-20260601-claim-event-bus
domain: pbm
taxonomies: [cwe, mitre_attack, d3fend, owasp_api_top10]
threat_model: inputs/threat-model.json
methodology_hint: stride          # optional — auto-detected if absent
```

The `threat_model` path is relative to the run directory's `inputs/`
directory. The `methodology_hint` is optional; the parser auto-detects
methodology from the file format when the hint is absent. See "When to use
methodology_hint" below.

### Via `apd-gauntlet init-run`

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ./artifacts \
  --domain pbm \
  --threat-model my-threat-model.tm7 \
  --methodology-hint stride
```

### When to use `methodology_hint`

The hint forces a specific methodology, overriding auto-detection. Use it when:

- The file format is ambiguous (e.g., a `.json` file that's not Threat Dragon
  but is your own custom JSON convention; hint `attack_tree` or similar)
- You want to force `pasta` / `vast` / `trike` / `free_form` interpretation
  even if the file extension would suggest something else
- The auto-detection picks the wrong methodology (rare; file an issue if you
  hit this)

Valid hints: `stride`, `linddun`, `attack_tree`, `pasta`, `vast`, `trike`,
`free_form`.

## What the recon agent produces

`apd-threat-model-recon` (tier-0, activation-gated on the
`threat_model:` declaration) parses the file and emits:

- `00-context/threat-model-normalized.yaml` — normalized graph of all entries

This file is consumed by:

- All tier-1/2/3 specialist agents as an evidence pointer (alongside the
  intake brief)
- `apd-threat-model-evaluator` (tier-4) for evaluation

See `templates/threat-model-normalized.template.md` for the file's structure
and field semantics.

## What the evaluator agent produces

`apd-threat-model-evaluator` (tier-4, activation-gated on the normalized YAML
existing) emits:

- Finding files at `20-findings/40-threat-model/tmeval-*.yaml`
- `40-synthesis/threat-model-coverage-report.md` (human-readable)
- `40-synthesis/threat-model-coverage.yaml` (machine-readable)

### The three finding flavors

| Disposition | Flavor | What it means |
| --- | --- | --- |
| `gap` | **Coverage gap** | TM omits methodology category for a surface a specialist flagged (e.g., TM has no Repudiation analysis for audit-log-writer but a Non-Repudiation specialist found a gap there) |
| `risk` | **Contradiction** | TM asserts a mitigation a specialist showed broken (e.g., TM claims TLS but specialist found plaintext) |
| `uncertainty` | **Silence** | TM has no entries for a surface a specialist flagged (e.g., specialist flagged vendor-API integration, TM never mentions it) |

Each `tmeval-` finding cross-references the specialist finding(s) it relates
to via `cross_references`. Contradiction findings additionally have an
evidence entry quoting the TM's mitigation claim. Silence findings note the
absence as "(no entries for surface=X)".

### Confidence cascading

The evaluator's discipline (Rule 6 in `apd-threat-model-methodologies` skill):

| TM entry `extraction_confidence` | Maximum contradiction finding `confidence` |
| --- | --- |
| `high` | `high` |
| `medium` | `medium` |
| `low` | (Cannot emit as contradiction; emitted as silence-style uncertainty instead) |

This prevents low-confidence LLM extractions from driving high-confidence
contradiction findings.

## Common pitfalls

### "The evaluator missed an obvious threat"

The evaluator does not invent threats. If you expect a contradiction or
coverage-gap finding that didn't appear, check:

1. Is the TM entry actually parsed? (Look at `00-context/threat-model-normalized.yaml`)
2. Does the entry's `asset` field match the surface a specialist finding's
   `evidence[*].artifact` points at? Surface matching is by string identity.
3. For contradictions: does the TM entry have a `mitigation` field? Entries
   without mitigations can't be contradicted (there's no claim to contradict).
4. Is the TM entry's `extraction_confidence` `low`? Low-confidence entries
   can't drive contradiction findings (Rule 6).

### "The TM says everything is mitigated; why are there contradictions?"

The evaluator compares mitigation CLAIMS against what specialists actually
FOUND. The TM's mitigation list may be aspirational; the contradictions
identify where the implementation hasn't caught up to the design intent.

### "methodology_hint changed; output is the same"

The hint applies to the WHOLE document. One TM = one methodology. If your
document genuinely mixes methodologies (rare), split it into multiple TM
files and supply each separately in a future run.

### "Validator rejects my tmeval- finding"

Two validator checks (Task B-25):

- Every `tmeval-` finding must have at least one evidence entry pointing at
  `00-context/threat-model-normalized.yaml` or the source TM artifact
- Every `tmeval-` finding with `disposition: risk` (contradiction) must have
  non-empty `cross_references`

If you're hand-authoring tmeval- findings (e.g., extending the bundled
example), make sure both conditions hold.

## Design rationale

See `docs/adrs/0009-methodology-aware-threat-model-evaluator.md` for the
full decision record (why two agents, why comparator-only, why Python
parsers for structured formats + LLM for prose, why two sources of truth
for the mapping tables).
