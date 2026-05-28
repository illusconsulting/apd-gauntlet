# Identity Security Severity Rubric (impact-to-identity-service-and-its-relying-parties)

Calibrated against impact-to-the-identity-provider-and-every-application-that-federates-with-it, not against generic CVSS. The specialist agent cites the matching clause in finding `detail` fields. Cited examples in each tier are illustrative, not exhaustive. NIST SP 800-63B Authenticator Assurance Levels (AAL1/AAL2/AAL3), NIST SP 800-63C Federation Assurance Levels (FAL1/FAL2/FAL3), the OAuth 2.0 Security BCP (RFC 9700), OIDC Core 1.0 §16, and the SAML 2.0 Security Considerations profile are referenced inline.

## Critical

Any of the following:

- **Token signing key compromise** — attacker can mint arbitrary access tokens, refresh tokens, ID tokens, or SAML assertions for any subject in any audience. Yields universal authentication bypass across every relying party that trusts the issuer. Recovery requires JWKS rotation, mass session invalidation, and (for asymmetric SAML signing keys) re-establishment of trust at every SP. Maps to NIST SP 800-63C §4.7 (assertion signing keys must be protected at the highest assurance level used).
- **Authentication bypass on the primary login** — no credential required: JWT `alg:none` accepted, signature verification skipped, SAML signature wrapping (XSW) yielding identity substitution, OIDC ID-token accepted without signature check, password-grant accepting empty password against legacy backends, or LDAP anonymous-bind producing authenticated session. The defining critical case under NIST SP 800-63B §4.
- **Mass credential exfiltration** — password hash dump from the credential store, MFA seed table export, WebAuthn credential record dump, or recovery-code table exfil. Triggers GDPR Article 33 72-hour notification, mass password-reset enforcement, mandatory MFA re-enrollment, and downstream credential-stuffing exposure across every external service the user population shares passwords with.
- **MFA bypass for high-AAL surface** — any path that silently downgrades a NIST 800-63B AAL3-required surface to AAL1 (password only) or AAL2 (SMS, knowledge-based) without policy decision, alert, or audit. Includes WebAuthn-enrollment endpoints reachable without re-authentication, MFA-disable through profile-edit injection, and recovery flows that bypass possession factors entirely.
- **Audit trail loss for authentication or authorization events** — destroys the forensic fact base for credential-compromise reconstruction, renders GDPR Article 33 breach scoping un-meetable, renders SOC 2 CC7.2 un-attestable, and produces the regulatory presumption-of-breach default. Includes audit pipeline silent-loss, audit-shipping fire-and-forget under broker outage, and audit-store deletion-by-single-credential.
- **Total IdP outage exceeding contractual SLA** — sustained inability to authenticate any user; every dependent application loses auth simultaneously. Cascading total platform outage with contractual SLA breach across every customer organization. Severity is critical regardless of cause (region outage, signing-key unavailability, database failure, session-store wipe).
- **OAuth confused deputy / relying-party impersonation** — relying party can act as another user via token misuse: unbound assertion accepted across audiences, OAuth client_id mix-up attack (RFC 9700 §4.4.2), missing audience claim validation, or token exchange (RFC 8693) without authorization-server-side scope reduction. The compromise unit is "any user of any RP via any RP."
- **SAML signature wrapping (XSW) accepted** — an SAML SP/IdP that processes assertions without canonicalizing the signed region and re-validating against the parsed assertion: attacker can substitute a forged inner assertion while preserving the outer signature. Yields arbitrary subject impersonation. Maps to SAML 2.0 Security Considerations §6.3 and the foundational SAML implementation flaw class.
- **JWT algorithm confusion at the issuer** — `alg:none` accepted, asymmetric public key used as HMAC secret (RS256 verified as HS256), key-ID confusion via JWKS URL injection, or kid-header path traversal yielding key substitution. Yields forgeable tokens at platform scope.

## High

Any of the following:

- **AAL downgrade** — high-AAL surface accepts low-AAL evidence: WebAuthn-required admin surface accepts password-only via a back-door endpoint, AAL3-target tenant accepts AAL2 SMS-fallback on a subset of flows, or step-up authentication is offered but bypassable. Maps to NIST SP 800-63B §4.4 (AAL boundary discipline) and §5.1 (authenticator types per AAL).
- **Open redirect on OAuth callback** — `redirect_uri` allowlist permissive (suffix match, wildcard, missing path check), permitting authorization-code or token leak via redirect manipulation. Includes covert-redirect / parameter-pollution variants (RFC 9700 §4.1).
- **CSRF on OAuth authorization flow** — `state` parameter not validated, not bound to session, or omitted entirely; permits authorization-code injection / session fixation in OAuth (RFC 9700 §4.7).
- **PKCE bypass or absence** — confidential clients accepting authorization codes without PKCE verification when configured, or public clients (native, SPA) onboarded without PKCE requirement. Authorization-code interception on public clients is the canonical OAuth 2.1 hardening.
- **Session fixation in interactive login** — the IdP issues a session identifier before authentication that survives the authentication step, permitting the attacker to plant a session ID the victim later authenticates into. Maps to OWASP ASVS V3.2.
- **SAML signature wrapping (XSW) partially mitigated** — the SP validates signatures but the canonical-region resolution is library-default and known to be bypassable (e.g., XML namespace tricks, Comment injection in subject NameID). High rather than critical when exploitation requires non-trivial wrapping variants.
- **JWT alg confusion on a downstream RP** — relying party rather than IdP accepts `alg:none` or HMAC-with-public-key; severity tracks the RP's blast radius. Cross-cutting RP-hardening guidance, not the IdP's exclusive concern, but the IdP-issued tooling and SDK posture drives the outcome.
- **Brute force / password spray without rate-limit + lockout** — credential-stuffing surface open. The OWASP API Top 10 calls this out as API4 (Unrestricted Resource Consumption) on the most-abused identity surface. NIST SP 800-63B §5.2.2 requires throttling.
- **Refresh token replay without proof-of-possession or rotation** — refresh tokens long-lived, bearer-only, no rotation-with-reuse-detection, no DPoP/mTLS binding. A stolen refresh token grants the attacker the lifetime of the token plus all subsequent rotations.
- **Privilege escalation via group/role mapping bug** — federation attribute mapping, JIT-provisioning logic, or claim-transformation expression permits a user to declare or influence their own group membership (self-attestable `groups` claim accepted, mapping expression with operator precedence flaw, attribute-collision yielding admin-group membership).
- **OAuth dynamic client registration without rate-limit or identity proofing** — open or weakly-gated client registration permits attacker-registered clients with attacker-controlled redirect_uri, enabling malicious-RP attacks against any user who can be lured to /authorize for the attacker's client_id.
- **Mass-assignment on user profile / consent surface** — self-service profile-edit accepts writes to `is_admin`, `groups`, `roles`, `email_verified`, or `mfa_enrolled` fields that should be server-managed. The mass-assignment class on the IdP itself is high-trending-critical.
- **Audit gap on token issuance, MFA enrollment, or consent grant** — partial loss of the consequential-action fact base. The merged finding with any Non-Repudiation gap on the same event class commonly escalates to critical.
- **Cross-tenant token bleed** — multi-tenant IdP issues a token with one tenant's scope that decodes against another tenant's audience, or a session cookie scoped too broadly (parent-domain Cookie with tenant subdomains).
- **Service account token long-lived and unrotated** — non-human identities authenticating to the IdP backend via static credentials (LDAP bind, SMTP, database, vendor APIs). The IdP's own backend-credential hygiene is in scope because IdP-tier compromise pivots outward.

## Medium

Any of the following:

- **Missing rate-limit on credential-recovery endpoints** — password-reset request, MFA recovery, recovery-code regeneration, email-change-confirmation. Severity escalates to high if combined with weak email-channel trust or absent re-authentication on the receiving end.
- **Session lifetime exceeds policy without justification** — absolute session > 24h without step-up, refresh-token lifetime > 30 days without rotation discipline, OAuth `offline_access` grants with no expiry.
- **OAuth client registration without strong identity proofing** — manual review present but human-only, no domain-control validation for redirect_uri host, no contact attestation. The compensating control exists but is human-velocity.
- **Misconfigured CORS on token endpoint** — token endpoint should generally not need CORS at all (browser-to-token is not the OAuth contract for public clients in OAuth 2.1); permissive ACAO on /token is a finding even if not directly exploitable.
- **Missing audit on OAuth client registration changes** — administrative-tier audit gap on the federation-trust surface; cross-references Non-Repudiation and Immutability findings on the consent/grant table.
- **Recovery flow weaker than primary login** — primary login enforces AAL2 with WebAuthn, recovery flow accepts email-only knowledge factor. The attacker takes the weakest path; recovery weakness silently downgrades the primary AAL claim.
- **Verbose error messages on /authorize or /token** — error responses differentiate "unknown client_id" vs. "invalid redirect_uri" vs. "unknown user," enabling enumeration.
- **Anonymous LDAP bind permitted by upstream directory** — IdP-to-directory boundary accepts unauthenticated reads; medium because typically the IdP itself enforces bind, but the latent posture is a finding.
- **Defense-in-depth gap on signing-key access** — signing key in HSM/KMS but the wrapping-key access is broad (every IdP pod can decrypt); the inner layer is strong but the outer layer is single-credential.
- **Weak password policy on non-admin surfaces** — minimum length below NIST SP 800-63B §5.1.1.2 guidance (8 chars min, 64 max permitted), no breached-password check via HIBP-style API, password complexity rules instead of length-and-uniqueness.
- **SAML metadata mutable without re-attestation** — federation-trust metadata can be edited inline by tenant admins without an approval workflow or re-attestation of the SP's identity.

## Low

Any of the following:

- **Hygiene issue with no realistic exploit path** — deprecated TLS cipher with no client population that requires it, redundant audit redaction overlapping a stronger upstream filter, verbose Server header on the IdP edge.
- **Documentation deficiency** — SAML metadata XML drift from federation-partner contract on a non-security-critical attribute, OAuth scope documentation lag, runbook formatting drift.
- **Defense-in-depth gap fully compensated by upstream controls** — useful to know but architecturally non-urgent.
- **Configuration drift on non-production realms** — sandbox tenants, ephemeral test realms, dev IdP instances without production credential mirror.

## Informational

Observations that do not rise to remediation but are worth surfacing for the architecture record. Used sparingly. Examples: notable architectural choices with security implications worth documenting (chosen JWT library and its alg-pinning posture, chosen OAuth library and its PKCE default, chosen federation topology — hub-and-spoke vs. mesh), parity gaps with industry peers that are not actually risks, NIST 800-63 / OAuth 2.1 capabilities the system meaningfully addresses that the specialist should record as a confirmed capability rather than a finding.

---

## Severity calibration discipline

- **Cite the rubric clause in `detail`.** "This is high severity because it falls under 'Privilege escalation via group/role mapping bug' per the identity security rubric, specifically because the `attributes.groups` claim from the upstream IdP is mapped through an expression that uses string concatenation with a user-controllable `email_domain` field."
- **Cite the matching NIST 800-63B AAL / 800-63C FAL clause** when the finding turns on assurance-level mismatch. Multiple anchors may apply — cite the OAuth/OIDC Security BCP section and the NIST clause together when an OAuth flow weakens an AAL claim.
- **Cite the SAML XSW class explicitly when applicable.** "This matches SAML 2.0 Security Considerations §6.3 (signature wrapping); the assertion is signed but the signature-validation library returns the parsed inner assertion after validating an outer envelope."
- **Do not average across multiple impacts.** A finding that yields signing-key exposure AND has a partial-rotation runbook is critical (signing-key exposure dominates).
- **Do not inflate to signal importance.** The synthesizer escalates and reconciles severity disagreements between agents; over-claiming on one agent degrades cross-agent reconciliation signal.
- **When in doubt, drop one level.** A high-confidence medium is more useful than a low-confidence high. The synthesizer can escalate based on cross-lens corroboration; it cannot reliably de-escalate a confidently-asserted critical.
- **Distinguish capability from exploited.** The rubric scores realistic attack capability, not whether exploitation has been observed. An undisclosed authentication bypass and an actively-exploited one are both critical.
- **AAL/FAL downgrade is the dominant high-severity pattern.** Anchor every authentication-related finding to the AAL/FAL claim the surface is meant to meet; the gap between target AAL/FAL and effective AAL/FAL is the severity dial.
