---
name: apd-threat-model-methodologies
description: |
  Methodology-aware discipline for parsing and evaluating user-supplied threat
  models. Canonical STRIDE/LINDDUN→APD-goal mapping tables. Discipline rules
  for the apd-threat-model-recon (parsing + enrichment) and
  apd-threat-model-evaluator (coverage/contradiction/silence finding emission)
  agents. Required reading for both agents.
---

# APD Threat-Model Methodology Discipline

## What this skill covers

This skill governs how the gauntlet handles user-supplied threat models. It is
required reading for two agents:

- **`apd-threat-model-recon`** (tier-0): parses TM files into normalized graph;
  enriches structural output with semantic mappings.
- **`apd-threat-model-evaluator`** (tier-4): evaluates the normalized graph
  against specialist findings; emits coverage-gap, contradiction, and silence
  findings.

Native support: **STRIDE** (OWASP Threat Dragon JSON, Microsoft TMT `.tm7`,
STRIDE-per-element Markdown/CSV), **LINDDUN** (Markdown/CSV tables), **attack
trees** (indented prose, ADTool XML, JSON).

Reduced-fidelity support: **PASTA**, **VAST**, **Trike**, free-form prose. The
recon agent's LLM does extraction; entries get `extraction_confidence: low`.

## Methodology → APD-goal mapping (canonical)

These tables are the **single source of truth** for STRIDE/LINDDUN → APD goal
inference. They mirror the Python module
`tools/apd_gauntlet/threat_model/mappings.py` — when one changes, the other
must change. The Python module is authoritative for parser code; this skill is
authoritative for agent reasoning.

### STRIDE

| Letter | Category | APD Goal(s) |
|---|---|---|
| S | Spoofing | Authenticity |
| T | Tampering | Integrity |
| R | Repudiation | Non-Repudiation |
| I | Information Disclosure | Confidentiality |
| D | Denial of Service | Availability |
| E | Elevation of Privilege | Authenticity + Integrity |

The `E` case maps to two goals because privilege escalation crosses the
authentication/authorization boundary (Authenticity) and typically involves
manipulating data the privileged role can write (Integrity).

### LINDDUN

LINDDUN's single-letter codes overlap (`D` and `N` are reused). The parser
disambiguates via column position; this skill uses compound keys:

| Compound Key | Full Category | Position | APD Goal(s) |
|---|---|---|---|
| `L` | Linkability | 1 | Confidentiality |
| `I` | Identifiability | 2 | Confidentiality |
| `N_repudiation` | Non-repudiation (privacy harm) | 3 | Non-Repudiation |
| `D_etectability` | Detectability | 4 | Confidentiality |
| `D_isclosure` | Disclosure of information | 5 | Confidentiality |
| `U` | Unawareness (lack of consent) | 6 | Authenticity |
| `N_compliance` | Non-compliance | 7 | Non-Repudiation (domain-mapped) |

**N_compliance domain mapping:** when the domain pack defines a non-compliance
override (e.g., PBM maps `N_compliance` to HIPAA breach-notification controls
under Non-Repudiation), use the domain-specific goal set. Default falls back to
Non-Repudiation.

### Attack tree

Attack-tree leaves get ATT&CK technique mappings via the parser's keyword
heuristic (see `tools/apd_gauntlet/threat_model/attack_tree.py::_ATTACK_TECHNIQUE_KEYWORDS`).
The recon agent (Task B-20) refines these via LLM judgment, then derives
`inferred_apd_goals` from the ATT&CK technique → APD goal mapping (already
documented in the `apd-control-mappings` skill).

## Format detection heuristics (for the recon agent)

The recon agent's first step is to call `apd-gauntlet parse-threat-model`,
which handles auto-detection. The agent SHOULD pass `--methodology-hint <X>`
when the `.apd-run.yaml` declares `methodology_hint: <X>`; otherwise let the
CLI auto-detect.

| Artifact pattern | Methodology | Notes |
|---|---|---|
| `.tm7` file | STRIDE (Microsoft TMT) | Always; .tm7 is TMT-only |
| `.adtool.xml` file | Attack tree (ADTool) | Always |
| `.json` with `summary`+`detail.diagrams` keys | STRIDE (Threat Dragon) | Auto-sniffed |
| `.json` with `goal`+`children` keys | Attack tree | Auto-sniffed |
| `.md`/`.csv` with `Linkability`/`Identifiability`/etc. in header | LINDDUN | `is_linddun_table()` heuristic |
| `.md`/`.csv` otherwise | STRIDE per-element | Default |
| `.txt` | Attack tree (indented prose) | Default |
| Free-form prose, narrative docs | `free_form` | LLM extraction by agent |

When the parser returns `methodology: free_form` with zero entries, that
signals the recon agent to perform LLM extraction directly from the artifact
text (read the file, identify asset/threat/mitigation triples, emit entries
with `extraction_confidence: low`).

## Discipline rules

These rules apply to BOTH the recon agent (when enriching parser output) and
the evaluator agent (when emitting findings).

### Rule 1 — Never invent threats

**The recon agent never adds threats the operator didn't write.** Parser output
defines the entry set; the recon agent enriches existing entries with mappings
but does not create new ones. The only exception is `methodology: free_form`,
where the agent extracts entries from prose — but each extracted entry must
correspond to a discrete claim in the source text, not the agent's own
brainstorm.

**The evaluator agent never emits findings about threats that aren't in the
normalized graph.** Coverage-gap findings (Rule 5) fire only when a specialist
finding shows the gap is real on a real surface; they do not fire because the
agent thinks "the operator should have considered X."

### Rule 2 — Never re-derive STRIDE/LINDDUN coverage from scratch

If the TM author chose to leave a STRIDE category blank for a surface, that's
their assessment — don't fabricate threats to fill it. The evaluator's
coverage-gap findings only fire when (a) the TM is silent on the category AND
(b) a specialist finding on the same surface flags risk in the APD goals that
category maps to.

### Rule 3 — Free-form extraction caps at `low` confidence

When the recon agent does LLM extraction (free-form prose), every emitted
entry has `extraction_confidence: low`. Low-confidence entries cannot drive
**contradiction** findings (Rule 6) — they can only drive **uncertainty**
findings. Reason: the agent's interpretation of free-form prose is fallible;
contradicting a specialist finding on the basis of a fallible interpretation
is too aggressive.

### Rule 4 — Block-on-ambiguity

If the supplied artifact cannot be parsed into ANY entries (parser returns
empty AND LLM extraction confidence is below threshold for the whole
document), the recon agent emits the envelope with `entries: []` and a
`methodology: unknown` flag. The evaluator agent then emits a single finding
with:

- `disposition: blocked`
- `prerequisite_evidence: ["normalized threat model in supported format"]`
- A recommendation pointing to `docs/threat-modeling.md` for supported formats

and skips coverage/contradiction/silence evaluation entirely.

### Rule 5 — Coverage gap (`disposition: gap`)

**Algorithm:**

1. Build a per-surface map: `surface → {APD goals flagged by specialist
   findings}`. Use evidence locators in specialist findings to identify
   surfaces.
2. Build a per-surface map: `surface → {APD goals covered by TM entries}`.
3. For each surface where a specialist flagged goal G but no TM entry maps
   to G on that surface: emit a coverage-gap finding.

**Example:** A specialist Non-Repudiation finding flags `audit-log-writer` for
missing immutability. The TM has 5 STRIDE-per-element entries for
`audit-log-writer` covering S, T, I, D, E — but no R. The evaluator emits:

```yaml
disposition: gap
severity: medium   # inherit from the flagging specialist finding's severity
title: "Threat model omits Repudiation analysis for audit-log-writer"
summary: "Specialist non-repudiation finding nonrep-... flagged audit-log-writer
  for missing immutability. The threat model's STRIDE entries for this surface
  cover S, T, I, D, E but not R."
```

### Rule 6 — Contradiction (`disposition: risk`)

**Algorithm:**

1. For each TM entry with a `mitigation` claim (e.g., "TLS 1.3 enforced on
   pricing-service traffic"), parse the claim for asserted controls.
2. Search specialist findings for the SAME surface AND the SAME control area.
3. If a specialist finding shows the control is absent/broken (e.g.,
   `conf-...` shows plaintext where the TM claims TLS), emit a contradiction
   finding cross-referencing the specialist finding's ID.

**Example:**

```yaml
disposition: risk
severity: high   # inherit from the contradicting specialist finding
title: "Threat model asserts mitigation that specialist finding contradicts"
summary: "TM entry tm-1a2b3c4d for adjudication→pricing flow claims:
  'mitigation: TLS 1.3 enforced on pricing-service traffic'. Confidentiality
  specialist finding conf-9e8d7c6b shows plaintext HTTP on this path."
cross_references:
  - conf-9e8d7c6b
evidence:
  - artifact: "00-context/threat-model-normalized.yaml"
    locator: "entries[entry_id=tm-1a2b3c4d]"
    excerpt: "mitigation: TLS 1.3 enforced..."
```

Contradiction findings have **two evidence pointers**: one for the TM claim
(quote the relevant excerpt from normalized.yaml) and one or more for the
contradicting specialist finding(s) (via cross-references).

**Confidence cap:** if the TM entry's `extraction_confidence` is `low`,
demote `disposition: risk` → `disposition: uncertainty` (Rule 3). Free-form
extractions are too fallible to assert contradiction.

### Rule 7 — Silence (`disposition: uncertainty`)

**Algorithm:**

1. Identify surfaces that specialist findings flagged as risky.
2. For each such surface, check whether the TM has ANY entries (regardless
   of methodology category).
3. If the TM has zero entries for the surface: emit a silence finding noting
   the gap.

**Example:** Authenticity specialist finds `auth-...` flagging the vendor API
integration for weak mTLS. The TM has zero entries mentioning that surface.
Evaluator emits:

```yaml
disposition: uncertainty
severity: low   # silence is informational unless the spec finding was high
title: "Threat model is silent on vendor-API integration"
summary: "Specialist authenticity finding auth-5d4c3b2a flagged the
  vendor-API integration for weak mTLS. The threat model has no entries
  for this surface."
cross_references:
  - auth-5d4c3b2a
```

Silence findings are not contradictions — the TM didn't make a wrong claim,
it made no claim. The disposition is `uncertainty` because reviewers may
need to ask the TM author whether the omission was deliberate (out of scope)
or accidental.

## Validation contract

After emitting findings, validate against `schemas/threat-model-normalized.schema.json`
and `schemas/threat-model-coverage.schema.json`. Validator's per-record check
for `tmeval-` findings (Task B-25) enforces:

- Each `tmeval-` finding has at least one evidence entry pointing at
  `00-context/threat-model-normalized.yaml` or the source artifact
- Each contradiction (`disposition: risk`) finding has at least one entry in
  `cross_references` (pointing to the contradicting specialist finding)
