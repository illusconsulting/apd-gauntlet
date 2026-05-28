# Threat Model Coverage Report

**Run:** `apd-20260527-caldera-adversary-emulation`
**Methodology:** STRIDE per surface, augmented with security-tooling-pack weapons-platform-misuse (WP) class.
**Normalized input:** `00-context/threat-model-normalized.yaml`

## Summary

- **21 threats** in the normalized model.
- **21 covered** by at least one APD finding (100%).
- **0 silences** (no threats unaddressed).
- **0 contradictions** between TM-asserted severities and synthesizer-assigned severities. Where the synthesizer escalated severity relative to the TM, the escalation is justified by the security-tooling rubric's weapons-platform-misuse axis (which the original threat model did not separately score).

## Coverage by STRIDE category

| Category | Threats | Covered |
|----------|---------|---------|
| Spoofing | 3 | 3 |
| Tampering | 3 | 3 |
| Repudiation | 3 | 3 |
| Information Disclosure | 4 | 4 |
| Denial of Service | 3 | 3 |
| Elevation of Privilege | 3 | 3 |
| Weapons-platform misuse | 4 | 4 |
| **Total** | **21** | **21** |

## Severity-alignment notes

- **S-1, I-2** — TM scored high; synthesizer escalated to critical for the underlying confidentiality findings (conf-a1b2c3d4, conf-b2c3d4e5). Escalation justified per the security-tooling rubric's "Operator authentication bypass to admin or operator console" clause, which scores the weapons-platform-misuse axis.
- **T-2** — TM scored medium; synthesizer scored high. Escalation justified per the rubric's chain-of-custody concern (impairs dispute resolution and customer-deliverable provenance).
- **R-1** — TM scored high; synthesizer escalated to critical for nonrep-a1b2c3d4 and immut-a1b2c3d4. Escalation justified per the rubric's "Audit trail loss" clause (CFAA defensibility).

All other coverages are severity-aligned between TM and synthesizer.

## Notable observations

- The four WP- (weapons-platform-misuse) threats are covered by 13 unique APD findings, indicating the security-tooling pack's lens is well-exercised in this run.
- The audit-vacuum cluster (R-1, R-3) maps to 6 non_repudiation + immutability findings, which is the synthesizer's largest single cluster.
- The default-credential surface (S-1, I-2) is covered across all three tiers (trustworthiness/confidentiality, scalability/ephemeral, auditability/authenticity), demonstrating the cross-lens nature of the gap.
