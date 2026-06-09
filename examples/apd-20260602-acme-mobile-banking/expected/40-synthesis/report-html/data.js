window.APD_DATA = {
  "meta": {
    "framework_version": "1.7.0",
    "domain_pack": {
      "name": "mobile-applications",
      "version": "1.0.0"
    },
    "run_id": "apd-20260602-acme-mobile-banking",
    "synthesizer_version": "1.7.0",
    "specialists_skipped": [
      "code-recon",
      "threat-model-recon",
      "attack-path-analyzer"
    ],
    "subject": "apd-20260602-acme-mobile-banking",
    "subject_tagline": "",
    "date": "2026-06-09",
    "artifact_count": 0,
    "artifact_types": [],
    "crown_jewels": [
      "stored_session_and_refresh_tokens",
      "embedded_api_keys_and_secrets",
      "mobile_backend_api_surface"
    ],
    "attacker_positions": [
      "network_mitm",
      "physical_thief_with_stolen_device",
      "rooted_device_attacker_with_frida",
      "reverse_engineer_with_ipa_apk"
    ],
    "is_empty_run": false,
    "reference_db_versions": {
      "nist": {
        "fetched_at": "2026-05-29",
        "source": "https://github.com/usnistgov/oscal-content/raw/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog-min.json",
        "count": 1196
      },
      "attack": {
        "fetched_at": "2026-05-29",
        "source": "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json",
        "count": 1034
      },
      "cwe": {
        "fetched_at": null,
        "source": null,
        "count": 970
      },
      "d3fend": {
        "fetched_at": null,
        "source": null,
        "count": 149
      },
      "atlas": {
        "fetched_at": "2026-06-02",
        "source": "https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/dist/ATLAS.yaml",
        "count": 170
      },
      "masvs": {
        "fetched_at": "2026-06-09",
        "source": "https://raw.githubusercontent.com/OWASP/masvs/c0db792d48206186874b8b10818e117226eb1d68/OWASP_MASVS.yaml",
        "count": 24
      },
      "maswe": {
        "fetched_at": "2026-06-09",
        "source": "https://github.com/OWASP/maswe",
        "count": 118
      }
    },
    "active_taxonomies": [
      "cwe",
      "mitre_attack",
      "masvs",
      "maswe"
    ],
    "has_threat_model": false,
    "section_errors": {},
    "warnings": []
  },
  "summary": {
    "findings_total": 9,
    "findings_pre_dedup": 9,
    "cross_lens_merged_clusters": 0,
    "linked_clusters": 0,
    "unresolved_authored_merges": 0,
    "bySeverity": {
      "critical": 2,
      "high": 6,
      "medium": 1,
      "low": 0,
      "info": 0
    },
    "byDisposition": {
      "gap": 8,
      "blocked": 0,
      "risk": 1,
      "uncertainty": 0,
      "ok": 0
    },
    "byTier": {
      "trustworthiness": 4,
      "scalability": 2,
      "auditability": 3
    },
    "capabilities_total": 2,
    "capabilities_pre_dedup": 2,
    "capabilitiesByMaturity": {
      "designed": 0,
      "implemented": 2,
      "tested": 0,
      "operationalized": 0
    },
    "contradictions": 0,
    "severity_disagreements": 0
  },
  "exec_summary": [
    "This APD gauntlet run reviews the Acme mobile banking app under the mobile-applications domain pack, with OWASP MASVS (control) and MASWE (weakness) promoted to first-class mapped taxonomies. The app splits trust between an adversary-controlled client and the backend; the highest-leverage gaps are structural client-trust failures, each of which needs a server-side invariant rather than a client-side measure.",
    "The headline concerns are a fleet-wide hardcoded HMAC request-signing secret compiled into every install (conf-4149d0db, critical) and a daily transfer limit enforced only client-side while the backend honors any submitted amount (intg-573fc767, critical), compounded by session and refresh tokens persisted in plaintext SharedPreferences/NSUserDefaults instead of the platform hardware-backed key store (conf-9c065684, high). Confirmed capabilities are narrow but real — HTTPS-only transport with no cleartext exemptions — and do not offset the structural gaps."
  ],
  "posture_summary": {
    "trustworthiness": "A hardcoded HMAC signing secret is compiled into every install (conf-4149d0db) and session/refresh tokens are stored in plaintext key-value stores rather than the hardware-backed key store (conf-9c065684); biometric unlock gates the UI but does not gate a Keystore/Keychain key release (auth-e0cc47fc).",
    "scalability": "Session lifetime is governed by a 90-day refresh token with no server-side revocation and no device-binding (ephem-260cbeab), and a single certificate pin with no backup pin or rotation path can brick the app fleet on rotation (resil-d7f2b8e9).",
    "auditability": "Consequential-action audit is kept only on the attacker-controlled device (nonrep-38caffd0), and the backend cannot prove a genuine app on a genuine device because there is no hardware attestation (auth-a66343a2), leaving consequential transfers unprovable."
  },
  "capabilities": [
    {
      "id": "auth-cap-7f003829",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "Certificate pinning on the Android API channel",
      "scope": "Confirmed for api.acmebank.com on Android via Network Security Config. iOS uses the default system trust store with no pinning, and pin agility is absent — both tracked as findings."
    },
    {
      "id": "conf-cap-3ad59773",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "HTTPS-only transport with no cleartext exemptions",
      "scope": "Confirmed for the api.acmebank.com channel on Android (Network Security Config) and iOS (ATS). Scope is transport encryption only; endpoint-identity pinning is partial and tracked separately under Resilient/Authenticity."
    }
  ],
  "strengths": [
    {
      "id": "conf-cap-3ad59773",
      "title": "HTTPS-only transport with no cleartext exemptions",
      "goal": "confidentiality",
      "maturity": "implemented",
      "caveats": [
        "HTTPS-only transport protects data in motion but does not address the hardcoded HMAC signing secret (conf-4149d0db) or plaintext token storage at rest (conf-9c065684)"
      ]
    },
    {
      "id": "auth-cap-7f003829",
      "title": "Certificate pinning on the Android API channel",
      "goal": "authenticity",
      "maturity": "implemented",
      "caveats": [
        "Certificate pinning is single-pin with no backup pin or documented rotation, risking a self-inflicted lockout (resil-d7f2b8e9)",
        "Pinning is present on the Android API channel only; it does not establish device or app integrity (auth-a66343a2)"
      ]
    }
  ],
  "findings": [
    {
      "id": "auth-a66343a2",
      "title": "No hardware attestation — backend cannot prove a genuine app on a genuine device",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The app has no Play Integrity / App Attest, so the backend has no cryptographic way to distinguish a genuine app on a stock device from a repackaged build on a rooted device.",
      "detail": "Per MASVS-RESILIENCE-4, hardware attestation is the verifiable answer to client trust that makes runtime detection heuristics (root/Frida checks) moot. With no Play Integrity (Android) or App Attest (iOS) verdict consumed server-side, the backend cannot tell a real install from a repackaged or instrumented one, so every client-trusted signal (and the hardcoded HMAC) collapses against the reverse-engineer and rooted-device positions. CWE-345 (insufficient verification of data authenticity) frames the gap. The structural control is a server-verified attestation verdict consumed as a write-authorization input — the verifiable client identity that the other RESILIENCE heuristics only approximate.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 Integrity and platform",
          "excerpt": "no root/jailbreak detection, no anti-tampering, and no hardware attestation (Play Integrity / App Attest)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Adopt Play Integrity / App Attest and verify the verdict server-side as a write-authorization input.",
        "detail": "Integrate Play Integrity (Android) and App Attest (iOS), verify the verdict on the backend with freshness/nonce checks, and gate consequential write operations on a passing, fresh attestation rather than on client-side root/tamper heuristics."
      },
      "mappings": {
        "nist": [
          "IA-9",
          "IA-3",
          "SI-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-345"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "auth-e0cc47fc",
      "title": "Biometric unlock is a UI gate, not a Keystore/Keychain key release",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Face ID / fingerprint success merely loads the saved refresh token; no hardware-backed key is bound to the biometric, so a patched client resumes the session without it.",
      "detail": "Per MASVS-AUTH-3, a sensitive operation must be bound to the authenticator, not gated by a UI check. Using LAContext.evaluatePolicy (iOS) and BiometricPrompt (Android) only to decide whether to read the token means the biometric is decorative: a rooted-device attacker or a patched binary skips evaluatePolicy and loads the token directly. CWE-287 / CWE-603 describe the class. The structural control is a biometric-gated key RELEASE — the refresh token (or a per-session key) sealed under a Keychain/Keystore key whose use requires successful biometric authentication, so the secret is cryptographically unavailable without the live factor.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§2 Authentication and session",
          "excerpt": "the biometric check is a UI gate via LAContext.evaluatePolicy (iOS) and BiometricPrompt (Android)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Bind the token to a biometric-gated hardware key so its release requires a live biometric.",
        "detail": "Seal the refresh token or a per-session key under a Keychain/Keystore key configured to require biometric authentication for use (setUserAuthenticationRequired / kSecAccessControlBiometryCurrentSet), so a patched client cannot obtain the secret without the live factor."
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-2(1)",
          "SI-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-287",
          "CWE-603"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 5
    },
    {
      "id": "conf-4149d0db",
      "title": "Hardcoded HMAC client secret compiled into the binary and shared across all installs",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "A single ACME_CLIENT_HMAC_KEY ships in every app install and is recoverable from any APK/IPA by static analysis, granting backend request-signing for the whole fleet.",
      "detail": "Per the severity rubric, a hardcoded shared secret recoverable from the binary loads the scale-vector and all-users blast-radius modifiers — obfuscation (MASVS-RESILIENCE-2) only delays recovery, it is not a mitigant. MASVS-CRYPTO-2 (key management) and CWE-798 (use of hard-coded credentials) describe the weakness; a reverse-engineer holding the IPA/APK extracts the key and forges the 'genuine Acme app' request signature for every user. The structural fix is that no secret the backend trusts may live in the client: use per-install/per-device keys provisioned at runtime into the Keystore/Secure Enclave, or move the trust to a server-verified attestation.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 On-device storage",
          "excerpt": "the client signs each API request with an HMAC using a shared secret ACME_CLIENT_HMAC_KEY that is compiled into the app"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Remove the shared embedded secret; provision per-device keys at runtime or rely on server-verified attestation.",
        "detail": "Eliminate the compiled-in HMAC key. Provision a per-install key into the hardware-backed key store at first run, or replace the client-secret trust with Play Integrity / App Attest verified server-side, so that extracting one binary does not yield fleet-wide request forgery."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(7)",
          "SC-12",
          "SC-28"
        ],
        "attack": [],
        "cwe": [
          "CWE-798",
          "CWE-321"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-CRYPTO-2",
          "MASVS-RESILIENCE-2"
        ],
        "maswe": [
          "MASWE-0014"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 1
    },
    {
      "id": "conf-9c065684",
      "title": "Session and refresh tokens stored in SharedPreferences/NSUserDefaults, not Keystore/Keychain",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Access and refresh tokens are persisted in plaintext key-value stores readable from a device backup or a stolen/rooted device.",
      "detail": "Per MASVS-STORAGE-1, sensitive data must be stored in hardware-backed storage. Persisting the access and refresh tokens in SharedPreferences (Android) and NSUserDefaults (iOS) places long-lived bearer credentials in world-of-the-app plaintext that survives in cleartext backups (allowBackup is true) and is recoverable by a physical thief or a co-resident app on a compromised device. The structural control is the Android Keystore/StrongBox and iOS Keychain/Secure Enclave with non-exportable keys; the MASWE storage-leakage area and CWE-312 describe the exposure.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 On-device storage",
          "excerpt": "The access token and refresh token are persisted in SharedPreferences (Android) and NSUserDefaults (iOS) so the session survives app restarts"
        },
        {
          "artifact": "AndroidManifest.xml",
          "locator": "application android:allowBackup",
          "excerpt": "android:allowBackup=\"true\""
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Move tokens to the platform hardware-backed key store and disable cleartext backup of sensitive data.",
        "detail": "Store the refresh token (and any cached secret) in the Android Keystore/StrongBox and iOS Keychain/Secure Enclave with non-exportable keys, exclude it from backups via dataExtractionRules / Keychain access controls, and treat the device as untrusted for any long-lived credential."
      },
      "mappings": {
        "nist": [
          "SC-28",
          "SC-28(1)",
          "IA-5"
        ],
        "attack": [],
        "cwe": [
          "CWE-312",
          "CWE-522"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-STORAGE-1",
          "MASVS-STORAGE-2"
        ],
        "maswe": [
          "MASWE-0006"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 3
    },
    {
      "id": "ephem-260cbeab",
      "title": "90-day refresh token with no server-side revocation and no device-binding",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The on-device refresh token lives for 90 days, is not bound to the device, and cannot be revoked server-side, so a stolen or extracted token grants long-lived access.",
      "detail": "Per MASVS-AUTH-2, on-device session material must be short-lived, revocable, and ideally device-bound. A 90-day bearer refresh token with no revocation list and no device-binding means a physical thief, a co-resident app, or a rooted-device attacker who extracts it from SharedPreferences replays it for up to 90 days with no recovery path. CWE-613 (insufficient session expiration) describes the lifetime gap. The structural controls are short-TTL access tokens, rotating refresh tokens with reuse detection, server-side revocation, and device-binding (DPoP / mTLS) keyed to a hardware-backed key; the token-issuance protocol routes to the identity-security pack.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§2 Authentication and session",
          "excerpt": "there is no server-side revocation list and the token is not bound to the device"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Shorten and rotate the refresh token, add server-side revocation, and bind it to a hardware-backed device key.",
        "detail": "Reduce the refresh-token lifetime, rotate it on use with reuse detection, maintain a server-side revocation list invalidated on logout and credential change, and bind the token to a non-exportable Keystore/Secure-Enclave key. Route the OAuth token-issuance design to the identity-security pack."
      },
      "mappings": {
        "nist": [
          "AC-12",
          "IA-5",
          "IA-5(13)"
        ],
        "attack": [],
        "cwe": [
          "CWE-613"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 4
    },
    {
      "id": "intg-573fc767",
      "title": "Daily transfer limit enforced only client-side; backend accepts any amount",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The app refuses transfers above the member's daily limit, but the backend records whatever amount the client submits — the limit is not a control.",
      "detail": "This is the pack's central-tension Critical: client-side enforcement of a server-side control is not a control. The client reads dailyLimit and blocks oversized transfers, but a patched or instrumented client (or a direct API call) submits any amount and the backend honors it. Per MASVS-AUTH-1, the authorization/business-rule decision must be enforced server-side, and per MASVS-AUTH-2 the authorization must be enforced on the server side rather than only locally on the device; CWE-602 (client-side enforcement of server-side security) and CWE-603 describe the class, and MASWE-0042 (authorization enforced only locally instead of on the server-side) names the weakness. The finding of record is the missing server-side limit check; routes to the api-security pack for the endpoint-side enforcement in a multi-domain run.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§5 Transfers and limits",
          "excerpt": "The backend accepts whatever amount the client submits and records the transfer"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Enforce the daily transfer limit on the backend; treat the client check as UX only.",
        "detail": "Move the daily-limit and all business-rule checks to the backend, validate the amount server-side on every transfer, and keep the client-side check purely as input-friendly UX. Route the server-side enforcement design to the api-security pack."
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-4",
          "SI-10"
        ],
        "attack": [],
        "cwe": [
          "CWE-602",
          "CWE-603"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-AUTH-1",
          "MASVS-AUTH-2"
        ],
        "maswe": [
          "MASWE-0042"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 2
    },
    {
      "id": "intg-80dbf492",
      "title": "Unverified acmebank:// deep link drives a pre-filled transfer with no caller verification",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "A custom-scheme deep link opens the transfer screen with attacker-supplied to/amount parameters and no verification of the invoking app or link.",
      "detail": "Per MASVS-PLATFORM-1, inbound IPC and deep links are an untrusted-input boundary. The acmebank://transfer handler is an exported activity reached by any app or web page, the custom scheme is not an Android App Link (no autoVerify / domain verification), and the parameters drive an in-app action without re-authentication or server re-verification. CWE-939 (improper authorization in handler for custom URL scheme) describes the weakness; the phishing-deep-link attacker position reaches it. The structural controls are App Links / Universal Links domain verification, parameter validation, and a server-side re-authorization of the action the link requests.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§5 Transfers and limits",
          "excerpt": "The deep link handler performs the pre-filled transfer screen with no verification of which app or link invoked it"
        },
        {
          "artifact": "AndroidManifest.xml",
          "locator": "activity .TransferDeepLinkActivity",
          "excerpt": "Deep-link handler for transfers. Custom scheme, NOT an autoVerify App Link"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Adopt verified App Links / Universal Links, validate parameters, and re-authorize the action server-side.",
        "detail": "Replace the unverified custom scheme with autoVerify Android App Links and iOS Universal Links bound to the Acme domain, validate every deep-link parameter, and require re-authentication plus server-side authorization before executing a transfer initiated by a link."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "AC-3",
          "AC-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-939",
          "CWE-749"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 7
    },
    {
      "id": "nonrep-38caffd0",
      "title": "Consequential-action audit kept only on the device, which is attacker-erasable",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Transfers, bill-pay, and profile edits are logged to a local on-device audit log; the backend records only raw HTTP lines without device or app-version attribution.",
      "detail": "On-device-only audit is no audit: a rooted or stolen device can rewrite or delete the local log, so the durable record of a consequential action does not exist. Per the consequential-action surface, transfers, bill-pay, and profile edits must produce a server-anchored, attributable record carrying the actor, device, app version, and (where present) the attestation verdict; CWE-778 (insufficient logging) frames the gap. The backend's raw HTTP access lines lack the device/app-version/attestation attribution needed to tie an action to a genuine client during a dispute or breach investigation.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§7 Audit and privacy",
          "excerpt": "Consequential actions (transfers, bill-pay, profile edits) are written to a local on-device audit log"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Record consequential actions server-side with device, app-version, and attestation attribution.",
        "detail": "Emit a durable, server-anchored audit record for every consequential action carrying actor, device identifier, app version, and attestation verdict; treat the on-device log as corroborating only. Route the audit-content design for the backend to the api-security pack."
      },
      "mappings": {
        "nist": [
          "AU-2",
          "AU-3",
          "AU-9",
          "AU-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-778"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 6
    },
    {
      "id": "resil-d7f2b8e9",
      "title": "Single certificate pin with no backup pin or documented rotation bricks clients on rotation",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "risk",
      "summary": "The Android config pins one leaf certificate with no backup pin and no rotation procedure, so a routine certificate rotation hard-fails every installed client.",
      "detail": "Per MASVS-NETWORK-2, certificate pinning is correct only with pin agility. A single pin with no backup and no rotation runbook means the day the production leaf rotates, every client that has not yet updated fails to connect — pinning brittleness turns a routine operational event into a fleet outage. The structural controls are a backup pin (and/or pinning to an intermediate/SPKI), a documented rotation procedure that publishes the next pin before the cert changes, and a soft-fail-to-report path rather than a hard brick on pin mismatch. iOS additionally has no pinning at all, so the two platforms degrade differently.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "network_security_config.xml",
          "locator": "domain-config pin-set",
          "excerpt": "Single pin, no backup pin, no documented rotation"
        },
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Network",
          "excerpt": "a single pin is configured with no backup pin and no documented rotation procedure"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add a backup pin and a documented rotation procedure with a soft-fail-to-report path.",
        "detail": "Configure a backup pin (or pin to a stable intermediate/SPKI), publish the next pin before each certificate rotation, and report pin-validation failures to the backend rather than hard-failing the client, so rotation cannot brick the fleet."
      },
      "mappings": {
        "nist": [
          "SC-8(1)",
          "SC-17",
          "CP-13"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    }
  ],
  "contradictions": [],
  "contradictions_notes": null,
  "severity_disagreements": [],
  "severity_disagreements_notes": null,
  "nist_rollup": [
    {
      "family": "IA",
      "title": "Identification & Authentication",
      "covered": 1,
      "gapped": 7,
      "both": 0,
      "notable": "IA-3(1) strong; IA-9, IA-3, IA-2 gapped"
    },
    {
      "family": "SC",
      "title": "System & Communications Protection",
      "covered": 2,
      "gapped": 3,
      "both": 2,
      "notable": "SC-13, SC-8 strong; SC-12, SC-28, SC-28(1) gapped"
    },
    {
      "family": "AU",
      "title": "Audit & Accountability",
      "covered": 0,
      "gapped": 4,
      "both": 0,
      "notable": "AU-2, AU-3, AU-9 gapped"
    },
    {
      "family": "AC",
      "title": "Access Control",
      "covered": 0,
      "gapped": 3,
      "both": 0,
      "notable": "AC-12, AC-3, AC-4 gapped"
    },
    {
      "family": "SI",
      "title": "System & Information Integrity",
      "covered": 0,
      "gapped": 2,
      "both": 0,
      "notable": "SI-7, SI-10 gapped"
    },
    {
      "family": "CP",
      "title": "Contingency Planning",
      "covered": 0,
      "gapped": 1,
      "both": 0,
      "notable": "CP-13 gapped"
    }
  ],
  "attack_exposure": [],
  "masvs_coverage": [
    {
      "masvs_id": "MASVS-AUTH-1",
      "name": "The app uses secure authentication and authorization protocols and follows the relevant best practices.",
      "category": "MASVS-AUTH",
      "category_title": "Authentication and Authorization",
      "finding_count": 1,
      "finding_ids": [
        "intg-573fc767"
      ],
      "surfaces": [
        "§5 Transfers and limits"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-AUTH-2",
      "name": "The app performs local authentication securely according to the platform best practices.",
      "category": "MASVS-AUTH",
      "category_title": "Authentication and Authorization",
      "finding_count": 1,
      "finding_ids": [
        "intg-573fc767"
      ],
      "surfaces": [
        "§5 Transfers and limits"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-CRYPTO-2",
      "name": "The app performs key management according to industry best practices.",
      "category": "MASVS-CRYPTO",
      "category_title": "Cryptography",
      "finding_count": 1,
      "finding_ids": [
        "conf-4149d0db"
      ],
      "surfaces": [
        "§3 On-device storage"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-NETWORK-1",
      "name": "The app secures all network traffic according to the current best practices.",
      "category": "MASVS-NETWORK",
      "category_title": "Network Communication",
      "finding_count": 0,
      "finding_ids": [],
      "surfaces": [],
      "capability_count": 1,
      "capability_ids": [
        "conf-cap-3ad59773"
      ],
      "posture": "covered"
    },
    {
      "masvs_id": "MASVS-RESILIENCE-2",
      "name": "The app implements anti-tampering mechanisms.",
      "category": "MASVS-RESILIENCE",
      "category_title": "Resilience Against Reverse Engineering and Tampering",
      "finding_count": 1,
      "finding_ids": [
        "conf-4149d0db"
      ],
      "surfaces": [
        "§3 On-device storage"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-STORAGE-1",
      "name": "The app securely stores sensitive data.",
      "category": "MASVS-STORAGE",
      "category_title": "Storage",
      "finding_count": 1,
      "finding_ids": [
        "conf-9c065684"
      ],
      "surfaces": [
        "application android:allowBackup",
        "§3 On-device storage"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-STORAGE-2",
      "name": "The app prevents leakage of sensitive data.",
      "category": "MASVS-STORAGE",
      "category_title": "Storage",
      "finding_count": 1,
      "finding_ids": [
        "conf-9c065684"
      ],
      "surfaces": [
        "application android:allowBackup",
        "§3 On-device storage"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    }
  ],
  "maswe_coverage": [
    {
      "maswe_id": "MASWE-0006",
      "name": "Sensitive Data Stored Unencrypted in Private Storage Locations",
      "category": "MASVS-STORAGE",
      "status": "new",
      "parent_masvs": [
        "MASVS-STORAGE-1",
        "MASVS-CRYPTO-2"
      ],
      "finding_count": 1,
      "finding_ids": [
        "conf-9c065684"
      ],
      "surfaces": [
        "application android:allowBackup",
        "§3 On-device storage"
      ]
    },
    {
      "maswe_id": "MASWE-0014",
      "name": "Cryptographic Keys Not Properly Protected at Rest",
      "category": "MASVS-CRYPTO",
      "status": "new",
      "parent_masvs": [
        "MASVS-CRYPTO-2",
        "MASVS-STORAGE-1"
      ],
      "finding_count": 1,
      "finding_ids": [
        "conf-4149d0db"
      ],
      "surfaces": [
        "§3 On-device storage"
      ]
    },
    {
      "maswe_id": "MASWE-0042",
      "name": "Authorization Enforced Only Locally Instead of on the Server-side",
      "category": "MASVS-AUTH",
      "status": "placeholder",
      "parent_masvs": [
        "MASVS-AUTH-2"
      ],
      "finding_count": 1,
      "finding_ids": [
        "intg-573fc767"
      ],
      "surfaces": [
        "§5 Transfers and limits"
      ]
    }
  ],
  "apd_matrix": {
    "goals": [
      "conf",
      "intg",
      "avail",
      "dist",
      "resil",
      "ephem",
      "auth",
      "nonrep",
      "immut"
    ],
    "goalLabels": {
      "conf": "Conf",
      "intg": "Intg",
      "avail": "Avail",
      "dist": "Dist",
      "resil": "Resil",
      "ephem": "Ephem",
      "auth": "Auth",
      "nonrep": "NonRep",
      "immut": "Immut"
    },
    "rows": [
      {
        "component": "network_security_config.xml",
        "cells": {
          "conf": "covered",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "gapped",
          "ephem": "silent",
          "auth": "covered",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "tech_plan.md",
        "cells": {
          "conf": "gapped",
          "intg": "gapped",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "gapped",
          "auth": "gapped",
          "nonrep": "gapped",
          "immut": "silent"
        }
      }
    ]
  },
  "attack_paths": null,
  "next_steps": [
    {
      "rank": 1,
      "text": "Remove the hardcoded HMAC request-signing secret from the binary; move request authentication to a per-device server-issued credential so a single extracted key cannot forge requests for the whole fleet.",
      "refs": [
        "conf-4149d0db"
      ]
    },
    {
      "rank": 2,
      "text": "Enforce the daily transfer limit as a server-side invariant; the backend must reject any amount over the limit regardless of what the client submits.",
      "refs": [
        "intg-573fc767"
      ]
    },
    {
      "rank": 3,
      "text": "Persist session and refresh tokens in the platform hardware-backed key store (Android Keystore / iOS Keychain) instead of SharedPreferences/NSUserDefaults.",
      "refs": [
        "conf-9c065684"
      ]
    },
    {
      "rank": 4,
      "text": "Add server-side refresh-token revocation and device-binding so a stolen 90-day refresh token can be invalidated.",
      "refs": [
        "ephem-260cbeab"
      ]
    },
    {
      "rank": 5,
      "text": "Move consequential-action audit off the attacker-controlled device to a server-side append-only store so actions are reconstructable and tamper-evident.",
      "refs": [
        "nonrep-38caffd0"
      ]
    }
  ],
  "taxonomy": {
    "AC-12": {
      "family": "NIST 800-53r5",
      "title": "Session Termination"
    },
    "AC-3": {
      "family": "NIST 800-53r5",
      "title": "Access Enforcement"
    },
    "AC-4": {
      "family": "NIST 800-53r5",
      "title": "Information Flow Enforcement"
    },
    "AU-12": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Generation"
    },
    "AU-2": {
      "family": "NIST 800-53r5",
      "title": "Event Logging"
    },
    "AU-3": {
      "family": "NIST 800-53r5",
      "title": "Content of Audit Records"
    },
    "AU-9": {
      "family": "NIST 800-53r5",
      "title": "Protection of Audit Information"
    },
    "CP-13": {
      "family": "NIST 800-53r5",
      "title": "Alternative Security Mechanisms"
    },
    "IA-2": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users)"
    },
    "IA-2(1)": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users) | Multi-factor Authentication to Privileged Accounts"
    },
    "IA-3": {
      "family": "NIST 800-53r5",
      "title": "Device Identification and Authentication"
    },
    "IA-3(1)": {
      "family": "NIST 800-53r5",
      "title": "Device Identification and Authentication | Cryptographic Bidirectional Authentication"
    },
    "IA-5": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management"
    },
    "IA-5(13)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | Expiration of Cached Authenticators"
    },
    "IA-5(7)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | No Embedded Unencrypted Static Authenticators"
    },
    "IA-9": {
      "family": "NIST 800-53r5",
      "title": "Service Identification and Authentication"
    },
    "SC-12": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management"
    },
    "SC-13": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Protection"
    },
    "SC-17": {
      "family": "NIST 800-53r5",
      "title": "Public Key Infrastructure Certificates"
    },
    "SC-28": {
      "family": "NIST 800-53r5",
      "title": "Protection of Information at Rest"
    },
    "SC-28(1)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Information at Rest | Cryptographic Protection"
    },
    "SC-8": {
      "family": "NIST 800-53r5",
      "title": "Transmission Confidentiality and Integrity"
    },
    "SC-8(1)": {
      "family": "NIST 800-53r5",
      "title": "Transmission Confidentiality and Integrity | Cryptographic Protection"
    },
    "SI-10": {
      "family": "NIST 800-53r5",
      "title": "Information Input Validation"
    },
    "SI-7": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity"
    },
    "CWE-287": {
      "family": "CWE",
      "title": "Improper Authentication"
    },
    "CWE-312": {
      "family": "CWE",
      "title": "Cleartext Storage of Sensitive Information"
    },
    "CWE-321": {
      "family": "CWE",
      "title": "Use of Hard-coded Cryptographic Key"
    },
    "CWE-345": {
      "family": "CWE",
      "title": "Insufficient Verification of Data Authenticity"
    },
    "CWE-522": {
      "family": "CWE",
      "title": "Insufficiently Protected Credentials"
    },
    "CWE-602": {
      "family": "CWE",
      "title": "Client-Side Enforcement of Server-Side Security"
    },
    "CWE-603": {
      "family": "CWE",
      "title": "Use of Client-Side Authentication"
    },
    "CWE-613": {
      "family": "CWE",
      "title": "Insufficient Session Expiration"
    },
    "CWE-749": {
      "family": "CWE",
      "title": "Exposed Dangerous Method or Function"
    },
    "CWE-778": {
      "family": "CWE",
      "title": "Insufficient Logging"
    },
    "CWE-798": {
      "family": "CWE",
      "title": "Use of Hard-coded Credentials"
    },
    "CWE-939": {
      "family": "CWE",
      "title": "Improper Authorization in Handler for Custom URL Scheme"
    },
    "MASVS-AUTH-1": {
      "family": "OWASP MASVS",
      "title": "The app uses secure authentication and authorization protocols and follows the relevant best practices.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-AUTH-1/"
    },
    "MASVS-AUTH-2": {
      "family": "OWASP MASVS",
      "title": "The app performs local authentication securely according to the platform best practices.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-AUTH-2/"
    },
    "MASVS-CRYPTO-2": {
      "family": "OWASP MASVS",
      "title": "The app performs key management according to industry best practices.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-CRYPTO-2/"
    },
    "MASVS-NETWORK-1": {
      "family": "OWASP MASVS",
      "title": "The app secures all network traffic according to the current best practices.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-NETWORK-1/"
    },
    "MASVS-RESILIENCE-2": {
      "family": "OWASP MASVS",
      "title": "The app implements anti-tampering mechanisms.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-RESILIENCE-2/"
    },
    "MASVS-STORAGE-1": {
      "family": "OWASP MASVS",
      "title": "The app securely stores sensitive data.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-1/"
    },
    "MASVS-STORAGE-2": {
      "family": "OWASP MASVS",
      "title": "The app prevents leakage of sensitive data.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-2/"
    },
    "MASWE-0006": {
      "family": "OWASP MASWE",
      "title": "Sensitive Data Stored Unencrypted in Private Storage Locations",
      "url": "https://mas.owasp.org/MASWE/MASVS-STORAGE/MASWE-0006/"
    },
    "MASWE-0014": {
      "family": "OWASP MASWE",
      "title": "Cryptographic Keys Not Properly Protected at Rest",
      "url": "https://mas.owasp.org/MASWE/MASVS-CRYPTO/MASWE-0014/"
    },
    "MASWE-0042": {
      "family": "OWASP MASWE",
      "title": "Authorization Enforced Only Locally Instead of on the Server-side",
      "url": "https://mas.owasp.org/MASWE/MASVS-AUTH/MASWE-0042/"
    }
  },
  "threat_model": {
    "present": false,
    "authored": false,
    "supplied_present": false,
    "comparator": false,
    "generated_by": null,
    "methodology": null,
    "source_artifact": null,
    "entry_count": 0,
    "grounded_count": 0,
    "gap_count": 0,
    "entries": [],
    "stride_matrix": {
      "letters_present": [],
      "rows": []
    },
    "surface_coverage": null,
    "surface_graph": null,
    "comparator_delta": null
  }
};
