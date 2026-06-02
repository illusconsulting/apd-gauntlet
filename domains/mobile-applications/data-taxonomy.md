# Mobile application data taxonomy

Specialist agents treat the following fields as sensitive when they appear in artifacts. The intake brief's data inventory MUST enumerate every field present; missing fields become evidence gaps surfaced as `blocked-on-evidence` findings against the intake set. The taxonomy is calibrated for a mobile client where the device is partially adversarial — so it separates data that is sensitive because it is *secret* (must not be readable on a compromised device) from data that is sensitive because it is *untrusted attack input* (must be validated before the app acts on it).

This taxonomy is consulted by Confidentiality, Integrity, Authenticity, and Non-Repudiation specialists.

## On-device secrets and key material (highest sensitivity)

- `keystore_keychain_key` (hardware-backed symmetric/asymmetric key; the `exportable`/software-fallback flag is the risk — a key that can leave the TEE is client-extractable)
- `secure_enclave_key` (iOS Secure Enclave / Android StrongBox key; non-exportable by design — flag any design that copies it into app memory)
- `biometric_gated_secret` (the key-release event bound to a biometric/device-credential authenticator — sensitive as the *release*, not the prompt)
- `embedded_api_key`, `hardcoded_secret`, `embedded_signing_key` (compiled into the binary; recoverable from any IPA/APK — flag any secret shared across the install base)
- `pinning_public_key_set` (the pinned cert/public-key/SPKI set; less secret than a private key but integrity-critical — a wrong or unrotatable pin is its own finding)

## Session and authentication state

- `stored_access_token` (bearer; treat as session-equivalent for the token lifetime)
- `stored_refresh_token` (longer-lived; replayable; storage must be hardware-backed and the token server-revocable)
- `oauth_bearer_token`, `session_cookie`
- `device_bound_credential`, `device_key_pair` (the device-binding material that makes a token non-replayable off-device — e.g. DPoP/mTLS key custody)
- `attestation_token_jwt` (Play Integrity / App Attest verdict; freshness-sensitive — a stale verdict is replayable)

## On-device PII / PHI (GDPR Article 4(1) and Article 9)

- cached `profile_pii` (name, email, phone, address, date of birth, government-ID equivalents)
- `health_fitness_data` (Article 9 special-category — HealthKit / Health Connect data, fitness metrics)
- `geolocation` (precise and coarse), `messages_documents` in offline stores, `photos_media` and any biometric-adjacent media
- Offline/cached datasets that mirror backend PII for offline-first flows

## Device and tracking identifiers (PRIVACY-2)

- `advertising_id` (IDFA / GAID), `device_identifier` / `vendor_id` (IDFV / SSAID), `push_token`
- `persistent_install_id`, `fingerprinting_signals` (the combinable quasi-identifiers that re-identify a user even when no single field is PII)

## Inbound untrusted-input fields (sensitive as attack input, not as secrets)

- `deep_link_parameters`, `custom_scheme_params`, `universal_app_link_params`
- `intent_extras`, `ipc_payload`, `content_provider_query`
- `push_payload`, `webview_bridge_payload`, `imported_file`, `untrusted_server_response`

The intake MUST enumerate these so Integrity findings on input validation have a concrete field set to reason about; their sensitivity is that the app trusts them by default.

## Transient leakage surfaces

- `clipboard_contents`, `keyboard_cache` (predictive-text learning of typed secrets)
- `screenshot_snapshot` (task-switcher / app-backgrounding snapshot), `autofill_data`
- `device_log_entry` (PII/tokens spilled to logcat / os_log / crash reports)

## SDK-collected data and consent

- `sdk_collected_field` (the per-SDK field set the SDK reads in-process)
- `consent_record`, `tracking_permission_state`, `privacy_manifest_declaration` (what the app declares versus what it collects)

## App-vetting artifacts (managed/enterprise distribution — NIST SP 800-163r1)

- `vetting_report` (static / dynamic / human-analysis results for a build; sensitive — it enumerates the app's weaknesses)
- `app_approval_decision` (approve/reject against the security-requirements baseline, with the approver identity)
- `security_requirements_baseline` (the organization-defined requirements the app is vetted against)
- `reputation_signal` (developer / app reputation input to the vetting decision)

## Audit content

- `actor_identifier` (user / device / app-version / installation), `action`, `resource`, `attestation_verdict`, `decision_outcome`, `request_metadata` (IP, OS version, app version, attestation freshness)
- Audit storage inherits the highest sensitivity of any field captured — a device log carrying a token is token-sensitive.

## Out of scope

- Fully anonymized aggregates and de-identified telemetry that cannot be re-identified.
- Pseudonymous identifiers whose re-identification key is held server-side and is unreachable from the device.
- Public-by-design material: the app's published bundle identifier, public OAuth `client_id` for a public client (the absence of a secret is the point), and store-listing metadata.

This taxonomy is consulted by Confidentiality, Integrity, Authenticity, and Non-Repudiation specialists. The intake agent enumerates fields by reading artifacts against this list and surfaces missing-field declarations as `blocked-on-evidence` findings against the intake set.
