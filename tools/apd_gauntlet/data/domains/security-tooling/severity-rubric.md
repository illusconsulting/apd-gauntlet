# Security tooling severity rubric (impact-to-the-platform-and-its-targets)

Calibrated against impact-to-the-security-tool-and-its-targets, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive.

Security-tooling severities have a **second dimension** beyond classic confidentiality / integrity / availability: the **weapons-platform-misuse dimension**. A finding that exposes data is scored on the CIA axis; a finding that exposes the platform's offensive capability — the ability to wield deployed implants, initiate engagements, or substitute commands — is scored on the misuse axis. Many findings score on both axes; severity is the higher of the two.

References inline: NIST SP 800-115 (Pentest Guide), NIST SP 800-53r5 control families, MITRE ATT&CK techniques, MITRE D3FEND countermeasures, OWASP API Top 10 categories for operator-console surfaces.

## Critical

Any of the following:

- **C2 signing key compromise** — adversary holds the cryptographic material the platform uses to authenticate operator commands to deployed implants. Equivalent to a global authentication bypass against every fielded executor; attacker commands are indistinguishable from legitimate operator traffic in the implant's trust model. Recovery requires re-keying every deployed implant, which often means burning the engagement. Maps to T1552 (Unsecured Credentials), T1606 (Forge Web Credentials) applied to the C2 trust domain.
- **Unauthorized engagement-initiation capability** — a non-operator (or an under-privileged operator) can trigger attacks against arbitrary targets via the platform. This is the legally-load-bearing finding: out-of-scope engagement initiation creates Computer Fraud and Abuse Act (18 U.S.C. § 1030) exposure regardless of platform-operator intent. Includes ROE-enforcement bypass, target-attestation bypass, engagement-API authentication bypass, and SSRF on the c2_orchestrator_to_target_environment boundary that reaches arbitrary IP space.
- **Operator authentication bypass to admin or operator console** — admin or operator UI/API reachable without credentials, with default credentials, with bypassable MFA, or via authentication-decision bypass (JWT `alg:none`, signature-skip, key confusion). Equivalent to unauthorized_operator at the highest privilege level. Maps to OWASP API2 (Broken Authentication) at its sharpest edge.
- **Audit trail loss or alterability covering operator actions, command-issued events, or result-data access** — destroys legal defensibility under CFAA, destroys ROE attestation, destroys customer-deliverable provenance, and renders dispute resolution impossible. Regulators and customers treat absence-of-audit as presumption of misuse. Maps to T1070 (Indicator Removal); D3FEND counter is D3-SBV (System Behavior Validation) plus immutable storage.
- **Implant callback channel substitution** — attacker hijacks the listener (DNS takeover, BGP hijack, TLS termination at attacker-controlled proxy, compromised reverse-proxy) and issues commands to every existing deployed implant whose callback resolves to that endpoint. Turnkey conversion of the platform's fielded agents into attacker tools. Maps to T1090 (Proxy) abused defensively; D3FEND counter is D3-CP (Certificate Pinning) at the implant.
- **Mass result-data exfiltration** — captured screenshots, harvested credentials, harvested files, command outputs, or pivoted access tokens exposed at bulk scale. Frequently the most PII-dense and customer-credential-rich store in the platform; a successful engagement against a customer's HR or finance system places that customer's most sensitive data inside the security tool. Combine-and-amplify with cross-tenant isolation gaps for catastrophic blast radius.
- **Plugin code execution by untrusted source** — supply-chain compromise where a malicious plugin (typosquatted name, compromised author, backdoored dependency, intentionally weaponized community contribution) executes in the platform's privileged context with access to signing keys, implant registry, and result data. Maps to T1195.002 (Software Supply Chain Compromise); D3FEND counter is D3-EAL (Executable Allowlisting) plus signature verification.
- **Cross-tenant data exposure in SaaS-delivered tooling** — operator A reads or modifies operator B's customer engagement data, target inventory, or result store. Breaches the multi-tenant trust contract; effectively a breach of every affected customer simultaneously.

## High

Any of the following:

- **MITM on implant callback channel without certificate pinning** — attacker on-path can decrypt or modify implant traffic, including command and result payloads. Severity escalates to critical if the attacker can substitute commands and the implant has no command-signature verification independent of channel encryption. Maps to T1557 (Adversary-in-the-Middle); D3FEND counter is D3-CP (Certificate Pinning).
- **Operator role bypass (BFLA equivalent)** — low-privilege operator reaches admin functions via HTTP method swap, undocumented routes, predictable URL patterns, or missing role checks on privilege-altering operations. OWASP API5 applied to the operator console. Maps to T1078 (Valid Accounts) when paired with role escalation.
- **Implant authentication bypass** — an unauthorized callback can register as a legitimate implant in the agent registry, gaining whatever capability legitimate implants have (poll for tasks, submit results, exhaust orchestrator resources). Severity escalates to critical if registered implants can issue commands or receive operator-attributed data.
- **Plugin sandbox escape** — a module reads or writes outside its declared scope (filesystem, network, signing-key handle, implant registry, audit log). Severity escalates to critical if escape reaches signing material or audit alteration.
- **Audit log content forgery** — an operator can backdate, falsify, or rewrite their own audit entries while the platform accepts the result as authoritative. Distinct from audit-loss (operator-can-delete is critical); operator-can-rewrite is high because the falsified record actively misleads. Maps to T1070 / T1036 (Masquerading) at the audit layer.
- **Engagement scope bypass** — operator targets a system outside the declared ROE without bypassing authentication. The platform allows the command but no enforcement gate refuses the out-of-scope target. Creates legal exposure even when the operator is acting in good faith; the platform is supposed to be the enforcement layer.
- **Result data accessible across engagements** — operator A reads operator B's harvested credentials, screenshots, or command outputs from a different engagement against a different target. Within a single tenant this is a horizontal-privilege violation; across tenants it is the cross-tenant critical case above.
- **Weak operator MFA or MFA-bypass paths** — SMS fallback that defeats a phishing-resistant primary factor, MFA optional on admin operators, MFA enrollment endpoint reachable without re-authentication, MFA recovery flow without rate-limiting or strong identity proofing. Maps to T1621 (MFA Request Generation); T1556.006 (MFA Bypass).
- **Credential leak in operator API tokens** — tokens stored in plaintext or with reversible encryption, tokens long-lived without rotation, tokens scoped broader than the operator's role, tokens exposed in logs or backup snapshots. Maps to T1552.001 (Credentials in Files).
- **Implant command issued without per-command signature verification at the implant** — even if the channel is mTLS-encrypted, channel compromise yields command-substitution capability without a defense-in-depth signature layer. D3FEND counter is D3-MA (Message Authentication) at the implant.
- **Out-of-tenant plugin load** — a tenant or operator can load a plugin that affects another tenant's engagements, results, or signing material.

## Medium

Any of the following:

- **Rate-limiting absent on operator console authentication** — credential-stuffing and password-spray surface; combine-and-amplify with weak password policy or absent CAPTCHA. Lower than the High `weak MFA` clause because credential-stuffing alone, against MFA-enforced accounts, is bounded.
- **Plugin update mechanism unsigned** — supply-chain risk for the next update, not an immediate compromise. Escalates to High if the unsigned update mechanism is also unauthenticated or pulls from a user-writable mirror.
- **No audit on plugin module load** — provenance gap for which module ran when; impairs incident reconstruction. Escalates to High if combined with mutable plugin storage.
- **Operator session lifetime exceeds policy** — stolen session usable longer than necessary; severity tracks policy gap and the consequential surfaces the session reaches.
- **Misconfigured CORS on operator API** — cross-origin authenticated read or write from operator-controlled browsers; severity escalates if combined with reflected ACAO and credentials.
- **Listener fingerprinting trivial via banner, default port, default TLS certificate, or default URL paths** — accelerates target-side defender detection but also accelerates attacker-side discovery of unauthorized listeners. Maps to T1592 (Gather Victim Host Information).
- **No detection on listener probe activity** — the platform fails to alert operators when target-side defenders or third parties enumerate the listener. Operationally significant; not directly a compromise.
- **Result data retained beyond engagement-completion + customer-policy window** — accumulating PII and customer credentials past their useful life; GDPR Article 5(1)(e) storage-limitation concern if EU personal data is in scope.
- **Implant retry backoff absent or aggressive** — DoS pressure on target network (callback storms during listener outage); ethical and operational issue distinct from compromise.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated TLS cipher with no client support, redundant control with overlapping coverage, verbose response headers on the operator API with no fingerprintable signal benefit.
- **Documentation deficiency** — runbook formatting inconsistency, ROE template drift from regulator/customer guidance, plugin-development docs lacking signature-requirement section.
- **Defense-in-depth gap fully compensated by upstream controls** — useful to know but architecturally non-urgent.
- **Configuration drift on non-production environments** — operator-console staging environment with weaker MFA, sandbox tenants without production-grade signing keys.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Examples: notable architectural choices with security implications (e.g., chosen sandbox technology for plugins, chosen mutual-authentication scheme for implants), confirmed capabilities that should be recorded as `capability` records rather than findings, parity gaps with industry peers that are not actually risks.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is critical severity because it falls under 'Implant callback channel substitution' per the security-tooling rubric, specifically because the listener accepts TLS connections with any valid CA and the implant has no certificate-pinning and no command-signature verification layered above the channel."
- **Cite the matching weapons-platform-misuse axis when it applies.** A finding scoring high on CIA but critical on misuse is critical. Examples: credential leak in operator API tokens (high CIA) scoring critical on misuse if the tokens grant engagement initiation.
- **Cite the legally-load-bearing axis when relevant.** Unauthorized engagement initiation and audit trail loss have a separate CFAA / ROE / customer-contract consequence; the `detail` should name the specific legal exposure (CFAA out-of-scope-access, ROE breach, customer MSA audit clause).
- **Do not average across multiple impacts.** A finding that has critical misuse capability AND medium operational risk is critical.
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements; over-claiming degrades the cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high. The synthesizer can escalate based on cross-lens corroboration; it cannot reliably de-escalate a confidently-asserted critical.
- **Distinguish capability from exploited.** The rubric scores realistic attack capability, not whether exploitation has been observed. An undisclosed engagement-initiation bypass and an actively-exploited one are both critical.
- **Distinguish offensive-capability misuse from data exposure.** A finding may expose result data (CIA axis) without enabling new offensive activity (misuse axis), or vice versa. Score both axes, take the higher.
