# Threat Model — Claim Event Bus

Abbreviated STRIDE analysis covering the event bus and its immediate consumers.

## Assets

- PHI in `member_id`, `drug_ndc`, `prescriber_npi`, `pharmacy_id`.
- Audit log entries (regulatory artifact).
- Adjudication outcome events.

## STRIDE per component

### `claim-events` topic

- **Spoofing:** Producer identity verified by mTLS to the broker. No payload-level signing.
- **Tampering:** TLS in transit; no end-to-end payload integrity check.
- **Repudiation:** Producer service identity captured in audit; on-behalf-of user identity is NOT captured.
- **Information disclosure:** Broker-level encryption only. Plaintext PHI in payloads.
- **Denial of service:** Per-producer rate limit of 1000 msg/sec; consumer side has no backpressure.
- **Elevation of privilege:** Broker access is platform-admin only.

### Audit log

- **Tampering:** No HMAC or signing on audit entries; mutable table.
