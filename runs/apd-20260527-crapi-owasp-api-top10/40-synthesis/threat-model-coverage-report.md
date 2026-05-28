# Threat Model Coverage Report — crAPI v1.1.5

Phase 5.5 evaluator output. Evaluates `00-context/threat-model-normalized.yaml`
against the dedup'd finding set in `40-synthesis/deduped-findings.yaml`.

- **Run id:** `apd-20260527-crapi-owasp-api-top10`
- **Methodology:** STRIDE (per threat-model.md frontmatter)
- **Total threats normalized:** 32 STRIDE entries

## Summary

| Coverage status | Count | Notes |
|-----------------|------:|-------|
| Full            |    28 | Threat is covered by ≥1 dedup'd finding with matching scope and severity |
| Partial         |     1 | T-4 — covered as uncertainty pending source review |
| Contextual      |     1 | I-5 — properly framed as a capability with caveats, not a finding |
| Silence         |     1 | E-2 — unknown endpoint; tmeval-e2unsp01 surfaces the gap |
| Uncovered       |     0 | — |

The threat model is honest about its silence (T-4 explicitly flags the
unit_price question as residual; E-2 explicitly leaves the endpoint
unspecified), and the gauntlet's coverage tracks the honesty —
findings carry uncertainty/blocked dispositions where the threat
model itself is unresolved.

## Per-category coverage

### Spoofing (6 threats → 6 covered)

All six S-* threats are folded into the merged-c829ffc8 finding
(S-1, S-2, S-3, S-4) plus targeted findings on the gateway-service
basic-auth (S-5 → ephem-a39a1f7b + conf-d760cafe) and the password-
reset path (S-6 → auth-b57f022f + avail-c1ffcf8e + avail-e96ad7ff +
conf-8f7c8c8d).

### Tampering (5 threats → 4 full + 1 partial)

T-1 (mass-assignment orders), T-2 (mass-assignment videos), T-3
(NoSQL/SQL coupons), T-5 (chatbot prompt-injection) all fully
covered. **T-4** (server trusts client price) is covered as
`intg-6d98c520` with disposition `uncertainty` — the threat model
itself flags the question as unresolved; full closure requires
source review.

### Repudiation (3 threats → 3 covered)

R-1 (audit absence) → nonrep-7fad26d8 + immut-e50364e4. R-2 (no
token-revocation) → resil-776fc650 + ephem-96d3befb. R-3 (chatbot
attribution) → merged-d2e871f5 (4-lens merge that includes
the attribution lens).

### Information Disclosure (8 threats → 7 full + 1 contextual)

I-1 (BOLA #1), I-2 (BOLA #2), I-3 (EDE), I-4 (SSRF), I-6 (Mailhog),
I-7 (datastore creds), I-8 (gateway oracle) fully covered. **I-5**
(public JWKS leaks key + algorithm) is framed as a capability with
caveats (conf-cap-c354ef8e) — the standard OIDC posture is the
intended behavior; the real threat is the algorithm-confusion
combination which is covered by merged-c829ffc8. The threat
model's framing of I-5 as **low**-impact-in-isolation matches the
gauntlet's choice to record it as a capability rather than a finding.

### Denial of Service (4 threats → 4 covered)

D-1 (contact_mechanic) → merged-514507e6. D-2
(OTP brute force) → avail-e96ad7ff. D-3 (LLM cost amp) →
avail-004444b5. D-4 (tight compose limits) → avail-b01847b0.

### Elevation of Privilege (5 threats → 4 full + 1 silence)

E-1 (BFLA admin video delete) → auth-4ef8b512. E-3 (mass-assignment
to role) → intg-a6b6d147. E-4 (chatbot admin abuse) →
merged-d2e871f5. E-5 (direct DB bypass) →
merged-44bdb663. **E-2** (unauthenticated access on
an unspecified endpoint) → tmeval-e2unsp01 surfaces the gap as
blocked-on-evidence.

## Cross-cutting residual questions

The threat model's §7 Cross-cutting residual questions are also
covered:

- **Key rotation** → ephem-30d38360 + ephem-22c2358c + ephem-a39a1f7b +
  merged-d2e871f5 + immut-49cb874c
- **Backup / restore** → avail-8ad04f0e + immut-a6c69999
- **Audit log retention** → nonrep-7fad26d8 + immut-e50364e4 + immut-56949f0a
- **Per-service datastore least-privilege** → merged-44bdb663
- **TLS posture** → conf-5f25ca4e + auth-5b90d6c3
- **Inbound WAF / rate-limit** → avail-4f60016d + avail-e96ad7ff +
  avail-c1ffcf8e + merged-514507e6

## Conclusion

The threat model and the gauntlet's specialist outputs are
**substantially aligned**: 28 of 32 STRIDE threats have full
coverage, the 4 remaining are either explicitly known-unresolved in
the threat model itself (T-4, E-2) or appropriately framed as
capability-with-caveats (I-5). The single net-new evaluator finding
(tmeval-e2unsp01) surfaces a known silence rather than a gap the
specialists missed.

The threat model adds value beyond the dedup'd finding set in the
form of attack scenario narratives that the synthesizer's
finding-level prose does not duplicate — readers seeking concrete
attack-chain walkthroughs should consult `inputs/threat-model.md`
directly.
