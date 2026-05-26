# Threat Model Coverage Report

**Run:** apd-20260601-claim-event-bus
**Methodology:** STRIDE
**Source artifact:** inputs/threat-model.json (Threat Dragon format)
**Generated:** 2026-06-01

---

## Summary

| Metric | Value |
|---|---|
| Total TM entries | 11 |
| Extraction confidence | 11 high / 0 medium / 0 low |
| Surfaces examined | 3 |
| Surfaces absent (silent) | 1 |
| Coverage gaps emitted | 1 |
| Contradictions emitted | 1 |
| Silences emitted | 1 |
| Blocked findings | 0 |

---

## Surface Coverage

### claim-ingress-API

| STRIDE | Entry ID | Status |
|---|---|---|
| S — Spoofing | tm-43625e57 | Open |
| T — Tampering | tm-b9c3c1b5 | Open |
| I — Information Disclosure | tm-5eadb570 | Mitigated |
| D — Denial of Service | tm-f2d83cb5 | Open |
| E — Elevation of Privilege | tm-4d037558 | Open |
| R — Repudiation | *(absent)* | — |

**Notes:** R is absent for claim-ingress-API, but no specialist finding specifically flagged repudiation risk on this surface — no evaluator finding was emitted for this absence.

---

### adjudication-to-pricing

| STRIDE | Entry ID | Status |
|---|---|---|
| I — Information Disclosure | tm-1a799f16 | **Mitigated** (contradicted) |
| S, T, R, D, E | *(absent)* | — |

**Contradiction finding: `tmeval-dddd4444` (high severity)**
The TM marks th-6 as Mitigated via "TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing." Specialist finding `conf-7aa376c5` demonstrates that PHI flows in plaintext at the broker layer — the claimed mitigation does not reflect implementation reality.

---

### audit-log-writer

| STRIDE | Entry ID | Status |
|---|---|---|
| S — Spoofing | tm-04b76ff1 | Open |
| T — Tampering | tm-9a8c9ce4 | Mitigated |
| I — Information Disclosure | tm-99aa91ca | Open |
| D — Denial of Service | tm-6dc432fd | Open |
| E — Elevation of Privilege | tm-8df8b2f3 | Open |
| R — Repudiation | *(absent)* | — |

**Coverage gap finding: `tmeval-cccc3333` (medium severity)**
Repudiation is absent for audit-log-writer. Specialist findings `nonrep-cf99a733` (missing user attribution) and `nonrep-62124087` (unsigned mutable audit entries) both flagged active non-repudiation risks on this surface. The STRIDE analysis is incomplete without a Repudiation entry.

---

## Silent Surfaces

### vendor-API / member-portal integration

No entries — not modelled in scope, not declared out of scope.

**Silence finding: `tmeval-eeee5555` (medium severity)**
Specialist finding `auth-dbba3dea` flagged SMS MFA fallback on the member portal, which is a PHI-bearing surface. The threat model contains zero entries for this surface. Reviewers cannot determine whether the omission was intentional (with coverage in another artifact) or an oversight.

---

## Evaluator Findings Emitted

| ID | Flavor | Severity | Related specialist findings |
|---|---|---|---|
| tmeval-cccc3333 | Coverage gap | medium | nonrep-cf99a733, nonrep-62124087 |
| tmeval-dddd4444 | Contradiction | high | conf-7aa376c5 |
| tmeval-eeee5555 | Silence | medium | auth-dbba3dea |

---

## Disposition

The threat model is structurally incomplete: it omits Repudiation analysis for the most sensitive store (audit-log-writer), incorrectly marks a PHI-in-transit threat as mitigated, and is entirely silent on the member portal authentication surface. These gaps are flagged as evaluator findings and should be resolved before the threat model is accepted as a design control artifact.
