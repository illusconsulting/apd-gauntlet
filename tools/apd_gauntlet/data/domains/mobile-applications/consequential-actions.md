# Mobile application consequential-action surface

For a mobile application and the backend it fronts, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list; gaps become findings against AU-2 (Auditable Events) and AU-3 (Content of Audit Records).

**The authoritative audit lives server-side.** On-device-only logs are attacker-erasable on a rooted or stolen device and are not a durable record. Each class below names where the durable, attributable record must sit: a device-originated event is *corroborating*, and the backend's record of the action it performed is *authoritative*. A consequential action whose only trace is on the device is an audit gap, not an audit.

## Authentication and session events

- Interactive sign-in success and failure, with reason categorization, against the backend (not the device).
- Local-authentication / biometric unlock of the app as a **device-local** event distinct from server authentication — it gates UI or key release, it is not a server auth event.
- Step-up / re-authentication for a sensitive transaction (the AUTH-3 event; the high-value anchor).
- Token issuance, refresh, and rotation; refresh-token reuse detected.
- Logout and the corresponding **server-side session/token invalidation** (the client clearing local state is not revocation).
- Account-recovery initiated from the device and its completion.

## Device-binding and attestation events

- Device enrollment / key-pair generation in the Keystore / Secure Enclave (the device identity is established here).
- Attestation-verdict request (Play Integrity / App Attest) and the **backend's verification outcome** — pass, fail, or replay/stale detected.
- Device de-registration / unbinding.
- Certificate-pinning validation failure (a pin mismatch is a security-relevant event).

## Biometric and local-authentication events

- Biometric-enrollment change detected by the platform (it invalidates biometric-gated Keystore keys; the invalidation is the anchor).
- Local-auth success or failure that gates a key release — **the key-release event is the audit anchor, not the biometric prompt**.
- Fallback-to-passcode / device-credential events when a biometric gate steps down.

## Sensitive on-device data access and export

- Read of cached PII/PHI from on-device stores by a flow that exports or transmits it.
- On-device export, share-sheet, or "save to files" of sensitive data.
- Inclusion of sensitive data in a device or cloud backup.
- Screenshot or clipboard capture of a sensitive surface where the platform makes it detectable.

## Permission and consent events

- Runtime OS-permission grant, denial, and later revocation (location, contacts, camera, microphone, photos, notifications).
- Tracking-consent grant and withdrawal (the App Tracking Transparency / consent-banner decision) — the PRIVACY-3 record.
- Privacy-manifest / Data-Safety declaration changes (what the app declares it collects).
- Per-SDK data-collection consent toggles.

## Deep-link, IPC, and push-initiated actions

- Any state change or sensitive data access triggered by an inbound deep link, App Link / Universal Link, custom URL scheme, intent, IPC call, or push payload — capture the source and **whether the link was domain-verified** (App Links verification status), because an unverified inbound action is attributable to no one.

## Third-party SDK actions

- SDK initialization and the capability set it was granted in-process.
- SDK data-collection events and SDK network egress carrying PII or tokens (the destination is part of the record).
- SDK version change (a new SDK build is a new in-process trust decision).

## Client-version lifecycle

- Forced-update / minimum-version-gate enforcement events — client refused, client upgraded.
- Kill-switch activation for a vulnerable build (the CODE-4 sunset event).

## App vetting and approval lifecycle (NIST SP 800-163r1)

For apps distributed through a managed or enterprise channel (MDM, an internal app store) — or any organization that vets apps before deployment — the app-vetting lifecycle is consequential and must be auditable. The authoritative record sits with the vetting system / backend, never on the device.

- App submission / intake for vetting (which build, which version, which developer/signing identity).
- Vetting analysis run and its outcome — the static, dynamic, and human/manual analysis results, and any reputation-analysis signal.
- App approval or rejection decision against the organization-defined security requirements (the approver/auditor identity and the requirements baseline applied are part of the record).
- Re-vetting triggered by an app update or a changed security requirement (a new build, or a new bundled SDK, is a new vetting decision).
- Allowlist / blocklist change for a vetted app (deploy, retire, or block a version across the fleet).

## Consequential backend transactions initiated from the device

- Funds movement, profile or credential mutation, sharing/permission changes, and deletion initiated from the app. **The backend, not the client, is the authoritative recorder**; the device-side event is corroborating and should carry the device, app version, and attestation verdict for attribution.

## Tamper and integrity-signal events

- Root/jailbreak/Frida/debugger/emulator detection firing, repackaging or re-sign detection, and attestation failure — recorded as **advisory signals shipped to and evaluated by the server**, never as a client-side block whose only record is on the compromised device.

---

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms whether the action is in scope for auditing, and confirming for every class that the durable record sits server-side rather than only on the device.
