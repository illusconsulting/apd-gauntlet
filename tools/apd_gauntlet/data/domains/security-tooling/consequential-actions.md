# Security tooling consequential-action surface

For a platform that wields offensive capability or operates critical defensive functions, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list; gaps become findings against NIST SP 800-53r5 AU-2 (Auditable Events) and AU-12 (Audit Generation), with a security-tooling-specific overlay because the audit IS the legal-defensibility evidence base under CFAA and the customer-deliverable provenance under MSAs.

## Operator authentication events

- Operator authentication success (interactive UI login, API authentication, SSO-federated login)
- Operator authentication failure (with failure categorization — bad password, expired account, locked, unknown user, MFA challenge failure)
- MFA challenge issued, succeeded, failed, bypassed via recovery
- Operator password change (by the user, by an administrator, via reset flow)
- Operator account lockout, lockout-reset, and lockout-override
- Session step-up authentication (re-auth required for engagement initiation, signing-key access, audit-read, plugin install)
- Operator session establishment and termination (idle timeout, absolute timeout, explicit logout, admin-revoked)
- API token issuance, scope-change, revocation

## Engagement lifecycle

- Engagement start (with ROE attestation captured — operator, target inventory, authorization window, customer reference)
- Engagement scope-change (any modification to target inventory, authorization window, or capability scope after start — the highest-sensitivity audit class under ROE attestation)
- Engagement pause and resume (with operator attribution and reason)
- Engagement finalization (closeout, results-delivered timestamp, ROE-closure attestation)
- Engagement-record signing event (the cryptographic seal applied at start to bind ROE evidence to a tamper-evident record)

## Implant / agent lifecycle

- Implant deployment (operator, target, implant variant, engagement reference)
- Implant callback registration (first-callback event, with implant identifier and source address captured)
- Implant heartbeat (sampled or aggregated; not every callback, but anomaly events — first-callback, callback-from-new-source, callback-after-decommission)
- Implant capability invocation (every command/ability executed by the implant — distinct from the orchestrator's command-issued event, captured at the implant if telemetry channel allows)
- Implant decommission (with operator-issued kill, expired-engagement auto-kill, or implant-self-destruct events distinguished)

## Plugin / module lifecycle

- Plugin install (with signature-verification outcome, source registry, version, dependency lockfile reference)
- Plugin update (with version-diff, signature-verification, and pre-update version retained)
- Plugin enable and disable (per-tenant or platform-wide scope captured)
- Plugin remove (with retention of historical install records — plugin removal does not erase the prior-install audit)
- Plugin-load event at runtime (which process loaded which plugin at which time; required for incident reconstruction when a plugin is later discovered malicious)
- Plugin signature-verification failure (with the plugin identity, source, and the reason for verification failure captured)

## Command execution against implants

- Command issued (operator, target implant, command text or command-identifier, engagement reference, timestamp) — the highest-volume audit class and the load-bearing class for after-action review and dispute resolution
- Command-issuance authorization decision (the role-and-ROE check outcome; capture allow AND deny with reason)
- Command-execution outcome at implant (success, partial, failed, timed-out; if telemetry channel supports it)
- Command queued for offline implant (with eventual delivery event linked to the issuance event)
- Bulk command issuance (multi-implant or multi-target broadcast — capture target set and per-target outcome)

## Result data access

- Operator reads harvested credentials (per-record, with the credential-identifier captured; the credential value itself MUST NOT appear in the audit log)
- Operator reads captured screenshots (per-screenshot, with the screenshot identifier and engagement reference)
- Operator reads harvested files (per-file, with file identifier and engagement reference)
- Operator reads command outputs (per-command-output, with command and target identifiers)
- Bulk result export (CSV, PDF, archive) — capture record count, field set, and destination of the export
- Result-data search query (capture query terms and result count; query terms are sensitive because they may contain operator hypothesis about target data)

## Customer-data egress

- Export of engagement results to customer (with the export package digest, recipient identification, delivery mechanism)
- Export of engagement results to internal storage (separate from customer-delivery; e.g., analytics, retention archive)
- Cross-tenant access attempt (operator from tenant A attempting to read tenant B's data — capture even denied attempts; these are insider-threat signals)
- Result-data deletion (in response to customer request, retention-policy expiry, or operator action; capture the deletion-authority and the deleted-record manifest)

## Administrative changes

- Operator role assignment, modification, revocation
- ROE template modification (changes to the platform's ROE schema — separate from per-engagement ROE)
- Audit-pipeline configuration change (sink, retention, schema, redaction policy)
- Signing-key lifecycle (creation, rotation, revocation, destruction — including the c2_signing_key, plugin_signing_root, audit_log_signing_key, and listener_tls_intermediate_ca)
- Listener configuration change (bind address, port, TLS material, callback protocol, accepted-implant policy)
- Policy modification (engagement-scope policy, plugin-load policy, command-authorization policy)
- Feature-flag toggle on any security-relevant flag (authentication path changes, audit-pipeline configuration, ROE-enforcement gating)

## C2 channel changes

- Listener bind / unbind (start and stop of a listener — operator, listener identity, bind details)
- Listener protocol change (TCP/UDP/HTTP/HTTPS/DNS-over-HTTPS variant changes)
- Listener TLS certificate rotation (with the previous certificate digest retained for provenance)
- Callback-domain registration or change (operationally sensitive; informs target-side defender tracking)

## Audit access (audit-of-audit)

- Operator queries audit logs (with query terms and result count — separation-of-duties relevant)
- Operator exports audit logs (with the export digest and recipient)
- Audit-pipeline failure event (sink unreachable, buffer overflow, schema rejection — the platform must surface these as alerts, not silent loss)
- Audit-retention enforcement event (record-aged-out events; in regulated environments, the absence of an aged-out event is itself a sign of audit pipeline failure)

## Break-glass and emergency override

- Break-glass authentication (with justification captured, and the break-glass event automatically routing to security-review independent of normal audit consumption)
- Emergency engagement termination (operator forces an active engagement to stop outside the normal closeout flow)
- Emergency credential rotation (out-of-cycle rotation of c2_signing_key, plugin_signing_root, or operator-class credentials)
- Emergency policy override (ROE-enforcement disabled, command-authorization bypassed) — the highest-severity audit class outside of the audit log itself
- Disaster-recovery failover initiation (listener failover, orchestrator failover, audit-pipeline failover)

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms whether the action is in scope for auditing. The CFAA / ROE / customer-MSA overlay means that "we didn't think it needed to be audited" is a much weaker defense in security-tooling than in conventional API surfaces.
