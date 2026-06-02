# Mobile Application Security Severity Rubric (impact-to-mobile-app-and-its-backend)

Calibrated against impact-to-the-mobile-application-its-users-and-the-backend-it-fronts, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive. OWASP MASVS 2.1.0 control IDs (e.g. MASVS-STORAGE-1), the OWASP MASWE weakness areas, OWASP MASTG test/technique references, and the MITRE ATT&CK Mobile matrix are referenced inline in finding detail. The NIST SP 800-163r1 app-vetting lifecycle (planning → app testing → app approval/rejection, by static, dynamic, and human analysis against organization-defined security requirements) is the governance frame for managed/enterprise distribution: where an organization vets and approves apps before deployment, a finding can be framed as input to the vetting/approval gate, and the absence of a re-vetting-on-update control or a durable approval-decision record is itself a finding under the Auditability tier (Non-Repudiation / Immutability). NIST SP 800-163r1 supplies the organizational software-assurance process; OWASP MAS supplies the technical requirements it evaluates against.

Severity calibrates impact using five mobile modifiers:

- **device-trust assumption** — does the attack require a rooted/jailbroken device, physical theft, a user-installed MitM CA, or dynamic instrumentation, or does it hit a stock, locked, current-OS device with no special preconditions?
- **blast radius** — single owned device, versus pivots-to-backend, versus all-users.
- **reversibility / data-sensitivity** — exfiltration of a long-lived credential, key, or PII/PHI versus an ephemeral cache value.
- **scale-vector** — the mobile-specific multipliers: one hardcoded secret in every install, one malicious in-process SDK across the install base, or one forced-update bypass keeping vulnerable clients alive fleet-wide.
- **client-side-only enforcement** — the security decision is made on the device only; against a rooted or instrumented client it is no control.

Raise severity when an attack hits stock devices, pivots from the client to the backend or to all users, or reaches a write/credential through a control that exists only client-side. Lower it when exploitation requires a device the attacker already fully controls and the blast radius stays on that one device.

> **The eight MASVS categories are cross-cutting, not goals.** No MASVS category maps to a single APD goal. MASVS-RESILIENCE decomposes — runtime detection (root/jailbreak/Frida/debugger/emulator) is an *advisory* signal under Integrity, anti-reversing/obfuscation is defense-in-depth under Confidentiality, anti-tamper/repackaging detection is tamper-evidence under Integrity, and hardware attestation is the *verifiable* client identity under Authenticity. MASVS-PLATFORM decomposes by flow direction (inbound untrusted input → Integrity, outbound leakage → Confidentiality, caller identity → Authenticity). MASVS-CODE decomposes sub-control by sub-control. MASVS-PRIVACY splits protection (Confidentiality) from proof (Non-Repudiation). Each goal's patterns own their facet.
>
> **Client-side enforcement of a server-side control is not a control.** A check that runs only on an attacker-controlled device — a root-detection verdict, a "step-up passed" flag, an entitlement gate, a price or amount computed on the client — raises the cost of attack but is bypassable on the device it runs on. Score it as defense-in-depth; the finding of record is the missing server-side invariant. Do not score the bypassability of the client check; score the consequence of the server trusting it.

## Critical

Any of the following:

- **Hardcoded backend credential, shared symmetric secret, or signing key embedded in the binary** and recoverable by static analysis from any IPA/APK, granting backend or third-party access for the entire install base. The scale-vector and all-users blast-radius modifiers both load; obfuscation (MASVS-RESILIENCE-2) is not a mitigant. Maps to MASVS-CRYPTO-2 and the MASWE hardcoded-secret area.
- **The backend trusts a client-asserted security signal as an authorization input** — a root/jailbreak verdict, a "biometric/step-up passed" assertion, an entitlement or feature flag, or a price/amount/quantity computed client-side and accepted server-side without re-verification. The client-side-only-enforcement modifier pivots a device-local bypass into a backend write at fleet scale.
- **No transport encryption, or certificate validation disabled / trust-all on a PII- or credential-bearing channel, on stock devices** — a network MitM yields token or PII theft at scale without needing a rooted device. Maps to MASVS-NETWORK-1.
- **A privileged or consequential action gated only by client-side local authentication** (a `BiometricPrompt`/`LAContext` UI check or `canEvaluatePolicy`-style gate) with no server re-authentication of the action — a patched or instrumented client performs the action with no factor presented. Maps to MASVS-AUTH-3.
- **A malicious, compromised, or over-broad in-process third-party SDK** with network, storage, and reflection capability shipped to the install base — the backdoored-SDK scale-vector reaching every user's on-device data and tokens. Maps to MASVS-CODE-2.
- **A backend authorization decision (object-level or function-level) made client-side**, so backend endpoints accept any request the patched app can send — equivalent to BOLA/BFLA at fleet scale. Routes to api-security / identity-security for the server-side decision; filed here as the mobile-origin critical with the "the client is not an authorization point" framing.

## High

Any of the following:

- **Sensitive data — access/refresh tokens, PII/PHI, or keys — persisted in unprotected on-device storage** (plist, `SharedPreferences`, unencrypted SQLite, plain files, NSUserDefaults) rather than the Keystore/Keychain, readable from a device backup or a stolen device, or by a co-resident app where the storage is shared. Maps to MASVS-STORAGE-1.
- **A long-lived access or refresh token stored on the device with no server-side revocation, rotation, or device-binding** — stolen-device or extracted-token replay grants the token's full lifetime. Maps to MASVS-AUTH-2.
- **A WebView JavaScript bridge exposes native capability or data to loaded web content without origin allowlisting** (`addJavascriptInterface`, `WKScriptMessageHandler`, `file://` access, mixed content) — untrusted content crosses into native privilege. Maps to MASVS-PLATFORM-2.
- **An exported component, unverified deep link, or custom URL scheme accepts unauthenticated parameters that drive an in-app state change or sensitive data read** without server re-verification. Maps to MASVS-PLATFORM-1.
- **No certificate or public-key pinning on a high-value channel** whose threat model includes user-installed MitM CAs or hostile networks. High rather than critical because stock-device default TLS still holds against the casual on-path case. Maps to MASVS-NETWORK-2.
- **Sensitive data leaks to system surfaces** — clipboard, keyboard cache, task-switcher screenshot/backgrounding snapshot, autofill, or analytics-SDK egress carrying PII or tokens. Maps to MASVS-STORAGE-2 and MASVS-PLATFORM-3.

## Medium

Any of the following:

- **Root/jailbreak/Frida/debugger/emulator detection absent or trivially bypassable** — Medium because it is an advisory defense-in-depth signal, not a control; it escalates to the Critical client-side-enforcement clause only if the backend actually relies on the verdict. Maps to MASVS-RESILIENCE-1.
- **No obfuscation or anti-decompilation on a binary that embeds sensitive (but non-secret) business logic or endpoint inventory** — a cost-raiser gap, not an exposure on its own. Maps to MASVS-RESILIENCE-2.
- **No anti-tamper or repackaging/re-sign detection, with no compensating server-side attestation** — Medium absent a server-trusted decision behind it; escalates if a client-trusted control depends on binary integrity. Maps to MASVS-RESILIENCE-3.
- **No forced-update / minimum-version kill-switch** — vulnerable client versions linger indefinitely; escalates with a known client CVE. Maps to MASVS-CODE-4.
- **Outdated minimum-OS or target-SDK floor** losing a platform security feature, with a compensating control present. Maps to MASVS-CODE-1.

## Low

Any of the following:

- **A rooted-device-only finding with single-device blast radius** — an attacker who already fully owns their own device reading their own app's data. Worth recording; low because the device-trust assumption is maximal and the blast radius does not pivot to the backend or other users.
- **Verbose but non-sensitive debug logging present in release builds** with no PII or token content.
- **A hardening gap reachable only after the attacker already controls the device and affecting only that device.**
- **Pinning present but pin-rotation or backup-pin strategy undocumented** — operational hygiene with no current exposure.

## Informational

Observations that do not rise to remediation but are worth the architecture record. Used sparingly. Examples: the chosen Keystore/Keychain abstraction; the selected attestation provider (Play Integrity / App Attest); the MASTG testing profile (L1, L2, or R) the app targets; or a MASVS category the app meaningfully addresses that the specialist should record as a confirmed capability rather than a finding.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`, and state the device-trust assumption explicitly.** "This is Medium because the bypass requires a rooted device with Frida (device-trust-assumption modifier), and the verdict is advisory only — the backend does not consume it. Were the backend to trust it, the Critical client-side-enforcement clause would govern."
- **Rooted-device-only, single-device-blast-radius findings drop a level.** The attacker owning their own device and reading only their own data is not a fleet risk.
- **But a client weakness that pivots to the backend or to all users is high/critical regardless of needing a rooted device** — the scale-vector and blast-radius modifiers dominate the device-trust modifier.
- **"Client-side enforcement of a server-side control" reframes severity to the missing server invariant.** Name the server-side control that must exist; do not litigate how the client check is bypassed.
- **Cite the MASVS control(s) and the MASWE area** when one applies; multiple may apply (a hardcoded key is MASVS-CRYPTO-2 plus MASVS-RESILIENCE-2).
- **Do not average across multiple impacts.** A finding that exposes a token AND leaks PII takes the higher band.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high. The synthesizer can escalate based on cross-lens corroboration; it cannot reliably de-escalate a confidently-asserted critical.
- **Calibrate the severity floor to the declared MASTG testing profile.** MASVS 2.x replaces the old L1/L2/R verification levels with MASTG testing profiles — L1 (baseline), L2 (defense-in-depth for apps handling sensitive data), and R (resilience, for apps at high risk of targeted client-side attack: banking, payment, high-value-account, and content-protection apps). The target profile is a property of the app under review, not the pack, and must be captured at intake. A gap in an L2- or R-tier control on an app that targets L2/R sits at its full rubric severity; the same gap on an L1-only app may drop a level. When the artifacts do not declare a target profile, raise it as a blocked/uncertainty finding (prerequisite_evidence: the app's target MASTG testing profile / assurance level and the rationale — the data sensitivity and threat exposure that justify L2 or R) rather than assuming one, and record the confirmed target profile as an Informational capability.
- **Distinguish capability from exploited.** The rubric scores realistic attack capability, not whether exploitation has been observed.
