# Security tooling common patterns — Integrity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Plugin/module loaded without signature verification; install path accepts any tarball or any registry URL the operator (or attacker-controlled config) points at.**

- Severity: critical (rubric clause: "Plugin code execution by untrusted source"; supply-chain compromise vector with execution in the platform's privileged context — access to signing keys, implant registry, audit log)
- NIST: SI-7 (Software, Firmware, and Information Integrity), SI-7(1), SI-7(15), SR-4 (Provenance), SR-4(3), SR-11 (Component Authenticity)
- ATT&CK: T1195.002 (Software Supply Chain Compromise); T1505 (Server Software Component) for the plugin-as-server-component path
- D3FEND: D3-EAL (Executable Allowlisting), D3-SU (Software Update verification), D3-DA (Dynamic Analysis) for sandbox-execution-before-trust
- Related concerns: authenticity (signing-root custody), non_repudiation (plugin-load audit), immutability (plugin install records)

**Pattern: Command sent to implant is authenticated only by channel TLS — no per-command signature the implant verifies independent of channel encryption.**

- Severity: high (rubric clause: "Implant command issued without per-command signature verification at the implant"; channel compromise yields command-substitution capability)
- NIST: SI-7, SC-23, IA-3, IA-3(1)
- ATT&CK: T1557 (Adversary-in-the-Middle) escalated by command-substitution; T1078 (Valid Accounts) at the implant trust boundary
- D3FEND: D3-MA (Message Authentication) layered above the channel; D3-CP (Certificate Pinning) for channel-level defense
- Related concerns: authenticity (implant identity verification), confidentiality (channel encryption)

**Pattern: Engagement-scope enforcement happens at the operator UI but not at command-issue time in the orchestrator — UI hides out-of-scope targets but API accepts them.**

- Severity: critical (rubric clause: "Unauthorized engagement-initiation capability"; out-of-scope command issuance creates CFAA exposure even from a legitimate operator)
- NIST: AC-3, AC-4 (Information Flow Enforcement), CM-7 (Least Functionality), SI-10
- ATT&CK: T1190 (Exploit Public-Facing Application) for the API-bypass-of-UI path
- D3FEND: D3-DTP (Domain Trust Policy), D3-NTSA (Network Traffic Signature Analysis) for catching out-of-scope egress
- Related concerns: authenticity (operator role check), non_repudiation (command-authorization decision audit)

**Pattern: Audit log entries written without hash chaining or external timestamp anchor — operator with database write access can rewrite history.**

- Severity: high (rubric clause: "Audit log content forgery"; escalates to critical if the same operator can also delete entries — "Audit trail loss")
- NIST: SI-7, SI-7(2), SI-7(8), AU-9 (Protection of Audit Information), AU-9(3), AU-10 (Non-Repudiation)
- ATT&CK: T1070 (Indicator Removal); T1565 (Data Manipulation)
- D3FEND: D3-SBV (System Behavior Validation), D3-MA (Message Authentication) for signed entries
- Related concerns: non_repudiation (the merged record carries both), immutability (storage substrate), authenticity (audit-signing-key custody)

**Pattern: Implant binary modifiable post-build — the deployed implant accepts module updates from the C2 channel without verifying signature against a separately-managed implant-update key.**

- Severity: high (compromised C2 yields persistent control via implant-update backdoor; also a target-side defender concern because reverse-engineered implants can be modified and re-injected)
- NIST: SI-7, SI-7(6), SI-7(15), CM-3
- ATT&CK: T1574 (Hijack Execution Flow); T1554 (Compromise Host Software Binary)
- D3FEND: D3-EAL plus D3-SU at the implant
- Related concerns: authenticity (implant-update key custody), ephemeral (implant credential rotation)

**Pattern: Result data ingested from implants is stored without integrity hashing — operator (or post-compromise attacker) can modify captured credentials, screenshots, or command outputs after the fact.**

- Severity: high (destroys chain-of-custody for customer-deliverable findings; impairs dispute resolution)
- NIST: SI-7, SI-7(6), AU-9, MP-4
- D3FEND: D3-MA for per-record signatures; D3-HFS (Hierarchical File System) for content-addressable storage
- Related concerns: non_repudiation (result-harvest log), immutability (result-data WORM substrate)

**Pattern: Tech plan describes "signed plugins" without specifying signing-root custody, signature algorithm, revocation mechanism, or verification-failure behavior.**

- Disposition: blocked or uncertainty
- prerequisite_evidence: "Plugin-signing policy — signing-root custody (HSM, KMS, ceremony-based), signature algorithm and key size, revocation mechanism (CRL, OCSP, transparency log), verification-failure behavior (fail-closed mandatory), and emergency-rotation procedure for the signing root"

## Common capability patterns

**Pattern: Plugin signature verification at install AND at load-time, against a signing root held in HSM or KMS, with revocation enforced via a transparency log.** Capability scope must enumerate which plugin classes are confirmed under verification; partial coverage (e.g., first-party plugins covered, community-contributed not) is a partial-coverage finding.

**Pattern: Per-command signatures the implant verifies against a key held only at the orchestrator (not at the listener) — channel compromise alone does not yield command-substitution.** Higher maturity when the implant logs signature-verification failures and refuses to execute on failure.

**Pattern: Audit log hash chaining with daily chain-head anchored externally (separate cloud account, separate KMS, external timestamp authority, or transparency log).** Cross-cuts Non-Repudiation and Immutability; mention via `related_concerns`.

**Pattern: Engagement-scope enforced at command-issue time in the orchestrator with allow/deny decisions logged, AND a defense-in-depth scope check at the listener before command delivery.** Maturity higher when chaos-test or adversarial-test evidence exists for the dual-enforcement path.

**Pattern: Result-data content-addressable storage with per-record SHA-256 (or stronger) digests, integrity verified at every read.** Cross-cuts Immutability; the digest is the content-addressed identifier and the integrity proof.
