---
framework_version: 1.0.0
domain_pack: { name: pbm, version: 1.0.0 }
run_id: <run-id>
synthesizer_version: 1.0.0
specialists_skipped: []
---

# APD Gauntlet Advisory Report — Run `<run-id>`

> Produced by `apd-synthesizer` from the nine specialist outputs.
> This report is advisory input to architecture review. It does not gate.
> Reviewers should cross-reference the YAML outputs in `40-synthesis/` for the canonical data.

**Run id:** `<run-id>`
**Date:** `YYYY-MM-DD`
**Inputs assessed:** `<n>` artifacts (`<types>`)
**Tech plan:** `<filename>`

---

## 1. Executive Summary

> Three paragraphs maximum. No finding details, no recommendations beyond "review findings in priority order."

**Scope.** One paragraph naming what was assessed (the change covered by the tech plan), what supplementary artifacts were available, and what was out of scope. Reference the context brief for canonical scope.

**Finding posture.** One paragraph naming the headline finding numbers — `<n>` critical, `<n>` high, `<n>` medium, `<n>` low, `<n>` informational, plus `<n>` blocked-on-evidence and `<n>` strengths called out. State the architectural signal these numbers carry (e.g. "predominantly auditability gaps with strong trustworthiness posture," "broad coverage gaps across all tiers indicating early-stage design," etc.). Do not editorialize; report the shape of the assessment.

**Capability posture.** One paragraph naming what was confirmed — `<n>` capabilities at designed maturity, `<n>` at implemented, `<n>` at tested, `<n>` at operationalized. Identify the tier or goal with strongest coverage and the one with thinnest coverage.

---

## 2. Confirmed Security Posture

> Affirmative section. Reviewers read this first to contextualize findings as gaps in a partially-built picture.

### Trustworthiness

**Confidentiality.**
- `<capability-title-1>` — maturity: `<level>`. Scope: `<one-line summary>`.
- `<capability-title-2>` — maturity: `<level>`. Scope: `<one-line summary>`.

**Integrity.**
- ...

**Availability.**
- ...

### Scalability

**Distributed.** ...

**Resilient.** ...

**Ephemeral.** ...

### Auditability

**Authenticity.** ...

**Non-Repudiation.** ...

**Immutability.** ...

> If a goal has no confirmed capabilities, state: "No capabilities confirmed at this stage. See findings in section 4 for gaps; see section 3 for blocked-on-evidence items."

---

## 3. Blocked-on-Evidence

> Findings where the lens could not be fully assessed without prerequisite evidence. This section is the gauntlet's structured request for more artifacts.

### Confidentiality

**`<finding-id>` — `<title>`**
- **Prerequisite evidence:** `<list of needed artifacts or properties>`
- **Apparent severity if resolved:** `<critical | high | medium | low>` (per the finding's detail)
- **Brief:** `<one-paragraph context from the finding>`

### Integrity

...

> Continue for all nine goals. Empty subsections may be omitted.

---

## 4. Findings

> Non-blocked findings sorted by severity descending, then by APD tier ascending (Trustworthiness → Scalability → Auditability).

### Critical

#### `<finding-id>` — `<title>`

- **APD goal:** `<goal>` (tier: `<tier>`)
- **Severity:** Critical — rubric clause: `<cited clause>`
- **Confidence:** `<high | medium | low>`
- **Lens perspectives:** `<list of agents if merged; omit if single-agent>`

**Summary.** `<from finding>`

**Detail.** `<from finding>`

**Evidence.**
- `<artifact>` — `<locator>` — "`<excerpt>`"
- ...

**Recommendation (`<posture>`).** `<from recommendation.detail>`

**Control mappings.**
- NIST 800-53r5: `<list>`
- MITRE ATT&CK: `<list with rationales>` (if any)

**References to consult.**
- `<from recommendation.references>`

**Related concerns:** `<list>` (if any)
**Cross-references:** `<list of finding IDs>` (if any)
**Merged from:** `<list of original finding IDs>` (if merged)

---

#### `<next finding>`

...

### High

...

### Medium

...

### Low

...

### Informational

...

---

## 5. Contradiction Annex

> Cases where a finding asserts a property is absent and a capability confirms it is present, or vice versa. Reviewers determine the correct interpretation.

### `<contradiction-id>`

- **Finding:** `<finding-id>` — `<finding assertion>`
- **Capability:** `<capability-id>` — `<capability assertion>`
- **Evidence comparison:** `<from contradictions.yaml>`
- **Recommended resolution:** `<from contradictions.yaml>`

---

## 6. Strengths-Notwithstanding-Gaps

> Confirmed capabilities with material caveats. Surfaced separately from section 2 because the caveats matter — these capabilities are real but not yet complete.

### `<capability-title>`

- **APD goal:** `<goal>`
- **Maturity:** `<level>`
- **Confirmed scope:** `<from capability>`
- **Caveats:**
  - `<caveat 1>`
  - `<caveat 2>`
- **Related findings:** `<list of finding IDs that bound the capability's scope>`

---

## 7. NIST 800-53r5 Coverage Matrix

> Per-control rollup. Highlighted rows are `gapped` (findings reference, no capabilities) or `gapped_and_covered` (both, suggesting scope mismatch).

| Control | Family | Title | Findings | Capabilities | Posture |
|---------|--------|-------|----------|--------------|---------|
| SC-8(1) | SC | Transmission Confidentiality and Integrity \| Cryptographic Protection | 3 | 1 | gapped_and_covered |
| SC-13 | SC | Cryptographic Protection | 2 | 1 | gapped_and_covered |
| AU-9(3) | AU | Protection of Audit Information \| Cryptographic Protection | 4 | 0 | gapped |
| ... | | | | | |

> Authoritative version in `40-synthesis/nist-coverage.yaml`.

---

## 8. ATT&CK Technique Exposure

> Techniques mapped by findings, with any mitigating capabilities.

| Technique | Sub-technique | Tactic | Name | Exposure | Mitigated by |
|-----------|---------------|--------|------|----------|--------------|
| T1530 | — | TA0010 | Data from Cloud Storage | 2 findings | M1041 (1 capability) |
| T1557 | T1557.003 | TA0006 | Adversary-in-the-Middle \| DHCP Spoofing | 1 finding | — |
| ... | | | | | |

> Authoritative version in `40-synthesis/attack-exposure.yaml`.

---

## 9. APD Coverage Matrix

> Per-component coverage across the nine APD goals.

| Component | Conf | Intg | Avail | Dist | Resil | Ephem | Auth | NonRep | Immut |
|-----------|------|------|-------|------|-------|-------|------|--------|-------|
| Kafka claim-events topic | gapped | gapped_and_covered | covered | gapped | silent | silent | silent | gapped | gapped |
| Member portal | covered | covered | covered | covered | covered | gapped | gapped_and_covered | covered | gapped |
| ... | | | | | | | | | |

Legend: `covered` (capabilities, no gaps), `gapped` (findings, no capabilities), `gapped_and_covered` (both — review scope alignment), `silent` (no findings or capabilities in this cell).

> Authoritative version in `40-synthesis/apd-coverage-matrix.yaml`.

---

## 10. Severity Disagreement Annex

> Records where two agents agreed on the concern but disagreed on severity. The merged finding takes the higher severity per the synthesis rule; the disagreement is preserved here for transparency.

### `<finding-id>`

- **Agents and severities:**
  - `<agent A>`: `<severity>`
  - `<agent B>`: `<severity>`
- **Chosen severity:** `<chosen>`
- **Rationale:** `<from severity-disagreements.yaml>`

---

## Appendix: Specialist Output Index

For drill-down beyond the synthesis-level view, consult the per-specialist files:

```
10-trustworthiness/
  confidentiality.findings.yaml      confidentiality.capabilities.yaml
  integrity.findings.yaml            integrity.capabilities.yaml
  availability.findings.yaml         availability.capabilities.yaml

20-scalability/
  distributed.findings.yaml          distributed.capabilities.yaml
  resilient.findings.yaml            resilient.capabilities.yaml
  ephemeral.findings.yaml            ephemeral.capabilities.yaml

30-auditability/
  authenticity.findings.yaml         authenticity.capabilities.yaml
  non-repudiation.findings.yaml      non-repudiation.capabilities.yaml
  immutability.findings.yaml         immutability.capabilities.yaml
```

Synthesis-level data:

```
40-synthesis/
  deduped-findings.yaml              deduped-capabilities.yaml
  contradictions.yaml                severity-disagreements.yaml
  nist-coverage.yaml                 attack-exposure.yaml
  apd-coverage-matrix.yaml           rejected-records.yaml
```
