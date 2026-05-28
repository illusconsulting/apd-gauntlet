# Security tooling common patterns — Confidentiality

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the security-tooling rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: C2 signing keys stored on the orchestrator filesystem in cleartext or with a key the orchestrator process can recover unaided (no HSM, no KMS, no envelope-encryption with separate-domain key).**

- Severity: critical (rubric clause: "C2 signing key compromise"; orchestrator filesystem read yields global authentication bypass against fielded implants)
- NIST: SC-12 (Cryptographic Key Establishment and Management), SC-12(1), SC-28, SC-28(1), IA-5(2)
- ATT&CK: T1552.001 (Credentials in Files); T1552.004 (Private Keys); T1606 (Forge Web Credentials) applied to the C2 trust domain
- D3FEND: D3-HSM (Hardware Security Module) and D3-KM (Key Management) as the counter
- Related concerns: authenticity (the keys' identity-binding role), immutability (signing-key lifecycle records), ephemeral (rotation cadence)

**Pattern: Implant callback channel uses TLS to the listener but result payloads are not separately encrypted; any compromise of listener TLS yields plaintext access to captured credentials, screenshots, and file harvests.**

- Severity: high (rubric clause: "MITM on implant callback channel without certificate pinning" escalates here because the payload contains harvested credentials)
- NIST: SC-8, SC-8(1), SC-13, SC-28
- ATT&CK: T1557 (Adversary-in-the-Middle) with rationale on listener-TLS-only defense
- D3FEND: D3-CP (Certificate Pinning) plus D3-MA (Message Authentication) layered above the channel
- Related concerns: authenticity (mTLS provides identity; payload encryption provides defense-in-depth)

**Pattern: Result data store (captured credentials, screenshots, harvested files) encrypted with a single platform-wide key — no per-engagement or per-customer key isolation.**

- Severity: high (single-key compromise exposes every customer's harvested data; for SaaS-delivered platforms the rubric's "Cross-tenant data exposure" critical clause applies if combined with weak tenant-isolation in the application layer)
- NIST: SC-28, SC-12, SC-12(2)
- ATT&CK: T1530 (Data from Cloud Storage Object) when result store is in object storage
- Related concerns: distributed (per-tenant key residency), authenticity (key-access workload identity), immutability (key lifecycle audit)

**Pattern: Plugin runtime has full filesystem and network access — no sandbox, no syscall filtering, no per-plugin capability restriction.**

- Severity: high to critical (rubric: "Plugin sandbox escape" is high; if the plugin reaches signing keys or audit alteration, "Plugin code execution by untrusted source" critical clause applies)
- NIST: SI-3, SC-39 (Process Isolation), AC-6, CM-7
- ATT&CK: T1195.002 (Software Supply Chain Compromise); T1059 (Command and Scripting Interpreter) for the plugin-as-code-path
- D3FEND: D3-EAL (Executable Allowlisting), D3-PSEP (Process Segment Execution Prevention), D3-SU (Software Update) for plugin distribution
- Related concerns: authenticity (plugin signing), integrity (plugin manifest enforcement), non_repudiation (per-plugin audit attribution)

**Pattern: Operator console exposes PII (operator names, customer names, target hostnames) in URLs, browser history, and referer headers without minimization.**

- Severity: medium to high depending on what's in the URL (target hostnames in URLs are high — they leak through web-proxy logs in operator-environment monitoring)
- NIST: SC-8, SI-11, AC-4
- Related concerns: non_repudiation (operator-action audit content; the same data the URL exposes is also audit-bound)

**Pattern: Captured screenshots stored without redaction of session-resident PII, payment data, or PHI — full-fidelity copy in the result store inherits the target environment's data classification.**

- Severity: high (the result store inherits the highest sensitivity of any captured field; a screenshot of a HIPAA-covered EHR places the screenshot in PHI scope)
- NIST: SC-28, AC-3, AC-4, MP-4 (Media Protection)
- Related concerns: immutability (retention policy must reflect inherited classification), distributed (residency rules apply to the screenshot under the target's jurisdiction)

**Pattern: Tech plan describes "encrypted result storage" generically without specifying per-engagement keys, key-access workload identity, rotation cadence, or recovery procedure on engagement closure.**

- Disposition: blocked or uncertainty
- Severity: medium when blocked
- prerequisite_evidence: "Result-data encryption policy — key scope (per-customer, per-engagement, per-result-class), key-access identity, rotation cadence, behavior on engagement closure (key destruction vs. archive), and recovery procedure for legitimate operator re-access"

## Common capability patterns

**Pattern: C2 signing keys held in HSM or cloud KMS with envelope encryption; orchestrator process accesses the wrapping key via workload identity, not via filesystem credential.** Maturity ladder: `designed` from tech plan; `implemented` requires KMS configuration or IaC reference; `operationalized` requires rotation runbook plus key-use monitoring.

**Pattern: Per-engagement key derivation for result-data encryption with key destruction at engagement closure.** Scope must enumerate which engagement classes are confirmed; partial coverage (e.g., interactive engagements covered, scheduled-scan engagements not) is a partial-coverage finding rather than a capability.

**Pattern: Plugin sandbox via process isolation, seccomp filtering, namespaced filesystem, or capability-based runtime (V8 isolates, WebAssembly, restricted Python AST).** Higher maturity when the sandbox specification is in evidence with the syscall/capability allowlist explicit; designed-only maturity from tech plan.

**Pattern: PII minimization in operator console — target hostnames hashed in URLs, customer names abbreviated in lists, screenshots displayed with on-fly redaction in the operator UI.** Cross-cuts Non-Repudiation for the audit-content side; mention via `related_concerns`.

**Pattern: Result-data encryption with per-customer KMS keys held in the customer's own cloud account (BYOK or HYOK pattern for SaaS-delivered tooling).** Higher maturity than per-engagement keys when the trust model requires the platform operator be unable to access result data without the customer's key.
