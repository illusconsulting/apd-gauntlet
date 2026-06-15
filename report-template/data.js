window.APD_DATA = {
  "meta": {
    "framework_version": "1.7.0",
    "domain_pack": {
      "name": "api-security + mobile-applications",
      "version": "1.0.0+1.0.0"
    },
    "run_id": "apd-20260612-home-assistant",
    "synthesizer_version": "1.7.0",
    "specialists_skipped": [
      "threat-model-recon",
      "attack-path-analyzer"
    ],
    "subject": "Home Assistant",
    "subject_tagline": "",
    "date": "2026-06-14",
    "artifact_count": 0,
    "artifact_types": [],
    "crown_jewels": [
      "user_credentials_store",
      "refresh_token_jwt_signing_keys",
      "user_permission_policy_engine",
      "integration_secret_storage",
      "recorder_history_db",
      "supervisor_backup_archive",
      "supervisor_docker_control_plane",
      "mobile_stored_session_and_refresh_tokens",
      "android_keystore_mtls_client_key",
      "mobile_on_device_location_and_entity_cache",
      "ios_bundled_firebase_config_secrets",
      "app_signing_identity",
      "mobile_app_webhook_api"
    ],
    "attacker_positions": [
      "unauthenticated_internet",
      "network_mitm",
      "compromised_user_session_token",
      "authenticated_low_priv_user_with_bola_target",
      "compromised_admin_session",
      "compromised_third_party_integration",
      "supply_chain_attacker",
      "internal_lateral_attacker",
      "malicious_or_compromised_addon",
      "leaked_device_webhook_id",
      "physical_thief_with_stolen_device",
      "rooted_device_attacker_with_frida",
      "reverse_engineer_with_ipa_apk",
      "phishing_deep_link_or_ipc_caller",
      "compromised_backend_or_response"
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
      "d3fend",
      "owasp_top10",
      "owasp_api_top10",
      "masvs",
      "maswe"
    ],
    "has_threat_model": false,
    "section_errors": {},
    "warnings": []
  },
  "summary": {
    "findings_total": 46,
    "findings_pre_dedup": 46,
    "cross_lens_merged_clusters": 0,
    "linked_clusters": 0,
    "unresolved_authored_merges": 0,
    "bySeverity": {
      "critical": 3,
      "high": 24,
      "medium": 16,
      "low": 3,
      "info": 0
    },
    "byDisposition": {
      "gap": 35,
      "blocked": 3,
      "risk": 8,
      "uncertainty": 0,
      "ok": 0
    },
    "byTier": {
      "trustworthiness": 17,
      "scalability": 12,
      "auditability": 17
    },
    "capabilities_total": 28,
    "capabilities_pre_dedup": 28,
    "capabilitiesByMaturity": {
      "designed": 2,
      "implemented": 26,
      "tested": 0,
      "operationalized": 0
    },
    "contradictions": 0,
    "severity_disagreements": 0
  },
  "exec_summary": [
    "Run summary not provided by synthesizer."
  ],
  "posture_summary": {
    "trustworthiness": "Posture statement not provided by synthesizer.",
    "scalability": "Posture statement not provided by synthesizer.",
    "auditability": "Posture statement not provided by synthesizer."
  },
  "capabilities": [
    {
      "id": "auth-cap-42c6a13f",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "Android Companion mTLS client-cert private key held in the hardware-backed AndroidKeyStore",
      "scope": "Confirmed in code for the Android client: the mTLS client-cert private key is\ncreated/held in the AndroidKeyStore and used by the OkHttp client SSL socket\nfactory. NOT addressed: this is a CLIENT-to-server identity control gated on the\nuser/server having configured mTLS (optional, not default); it does not provide\ndevice attestation (see the no-attestation finding) and does not authenticate the\nSERVER (see the no-pinning finding). iOS mTLS parity is not confirmed in the\nevidence reviewed. The hardware non-exportability is the protection — a\nsoftware-fallback key would void it.\n"
    },
    {
      "id": "auth-cap-8144e2be",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "Homeassistant auth provider uses bcrypt password hashing with constant-time, enumeration-resistant login",
      "scope": "Confirmed in code for the homeassistant password provider: bcrypt rounds=12 +\nconstant-time validate_login with a dummy-hash miss path. NOT addressed: this is the\nsingle knowledge factor only — MFA is opt-in and not enforced (see the MFA finding),\nand bcrypt's 72-byte input truncation means passwords longer than 72 bytes are\nsilently truncated before hashing. Does not speak to the legacy_api_password /\ntrusted_networks providers, which carry their own authenticity weaknesses.\n"
    },
    {
      "id": "auth-cap-e9f55df8",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "Supervisor SecurityMiddleware authenticates the add-on by SUPERVISOR_TOKEN and gates by declared role with default-deny",
      "scope": "Confirmed in code: token->app resolution + per-role regex URL ACL with default-deny.\nAuthenticity-relevant face: the caller identity (which add-on) is established from the\nSUPERVISOR_TOKEN and bound to a role. NOT addressed here: an add-on running with the\nadmin role or with protection-mode disabled matches ROLE_ADMIN's .* and reaches the\nfull API including the Docker host-root plane — so the gate's strength depends on the\nrole/protection configuration (an authorization-scope concern routed to api-security /\nIntegrity), and the SUPERVISOR_TOKEN lifecycle (rotation/expiry) is unspecified\n(Ephemeral).\n"
    },
    {
      "id": "auth-cap-eba3a527",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "Supervisor ingress strips client-supplied X-Remote-User-* headers before injecting its own",
      "scope": "Confirmed in code: ingress overwrites the X-Remote-User-* headers from session data\nand strips inbound copies in the forward path. This is a PARTIAL authenticity control:\nit closes client-through-ingress header spoofing, but the conveyed identity remains an\nUNSIGNED header the add-on cannot independently verify, so an add-on reached outside\ningress (host network / direct container call) or trusting the header on faith is still\nexposed (see the header-trust finding). Scope is the ingress hop only.\n"
    },
    {
      "id": "auth-cap-f01e6108",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "Single revocation-aware access-token validation chokepoint for REST and WebSocket",
      "scope": "Confirmed in code for Core's interactive bearer path (REST middleware + WS handshake):\nalgorithm is pinned to HS256, the signing key is the per-refresh-token jwt_key, and\nrevocation/inactive-user are enforced at validation. NOT addressed: the per-token\njwt_key never rotates and refresh/long-lived tokens are effectively non-expiring\n(Ephemeral findings) — so authenticity verification is strong at the moment of check\nbut the credential it verifies is long-lived; and this chokepoint does NOT cover the\nbearer-LESS mobile_app webhook path (separate finding). Algorithm-pinning prevents\nkey-confusion only because HS256 is the sole accepted algorithm.\n"
    },
    {
      "id": "avail-cap-f97d3d6b",
      "tier": "trustworthiness",
      "goal": "availability",
      "maturity": "implemented",
      "title": "Per-token rate limiting on the Firebase push-relay request handler",
      "scope": "Confirmed for the push-relay request handler (functions/handlers.js,\ncev-08000001): per-token (push_token) rate limit with a 429 breach\nresponse. NOT addressed: this is the only rate limit observed anywhere in\nthe Home Assistant availability surface — the Core REST boundary, the WS\nauth_required handshake, the bearer-less mobile_app webhook entrypoint, and\nthe Supervisor API all lack a documented rate limit (see availability\nfindings avail-0002webh, avail-0003rest, and the threat-model D cells). The\nrelay limit bounds notification-spam abuse, not relay-outage availability.\n"
    },
    {
      "id": "conf-cap-01c47d42",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "Android mTLS client-cert private key held in non-exportable hardware-backed AndroidKeyStore",
      "scope": "Confirmed for the Android Companion mTLS client-cert private key via the\nAndroidKeyStore (code-grounded, cev-f6000001). NOT extended to the\nsession/refresh bearer tokens or the location_history table, which live in\nthe UNENCRYPTED Room database (see finding conf-androidr) — so this\ncapability covers the mTLS key only, not the broader on-device secret\nestate. iOS-side key custody (Keychain) is evaluated separately and has a\nhardening gap (finding conf-ioskeych).\n"
    },
    {
      "id": "conf-cap-1044dbb3",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "User passwords stored as bcrypt hashes (rounds=12) with a constant-time miss path",
      "scope": "Confirmed for the homeassistant auth provider's password factor\n(code-grounded, cev-a1000004/5). Important boundary: the bcrypt HASH is\nstrong, but it is persisted to .storage as PLAINTEXT JSON (no\nencryption-at-rest layer, finding conf-st0rag31) alongside the MFA/TOTP\nseeds and the per-token jwt_keys — so this capability protects the\npassword factor specifically, NOT the surrounding secret estate. The\n72-byte bcrypt truncation is noted but standard.\n"
    },
    {
      "id": "conf-cap-277b2364",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "Optional NaCl SecretBox encryption of mobile_app webhook payload bodies (in-transit confidentiality, opt-in)",
      "scope": "Confirmed that the registration path mints a SecretBox key and the webhook\nsupports encrypted bodies (code-grounded, cev-a1000014). The decisive\ncaveat: encryption is OPT-IN (`supports_encryption`), so the default /\nnon-encrypting client sends payloads in cleartext at the application layer,\nand the per-device secret is itself persisted to the on-device store\n(unencrypted Android Room, finding conf-androidr) and to plaintext\n.storage server-side (finding conf-st0rag31). This capability covers\npayload-body confidentiality ONLY when a client opts in; it does not\nprotect the webhook_id (which is the bearer-less authenticator) and does\nnot add per-entity authorization to the service-call path (cev-a1000015).\n"
    },
    {
      "id": "conf-cap-88473a97",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "Per-entity READ permission enforced at the state-read API (access scoping at data-element granularity)",
      "scope": "Confirmed for entity-state READS on GET /api/states/{entity_id}\n(cev-a1000011) and the filtered list path (cev-a1000007), with deny-all\ndefault (cev-a1000006). NOT extended in two material ways: (1) the filter\nSHORT-CIRCUITS to allow-all for ANY admin (cev-a1000007) and the owner is\nunconditional all-access (cev-a1000008), so this scoping protects against\nnon-admin over-reach only; (2) the WRITE path (POST /api/states) is\nadmin-or-deny with NO per-entity write policy (cev-a1000012), and\n/api/config is unscoped (finding conf-apiconfig). The webhook service-call\npath applies no per-entity check at all (cev-a1000015).\n"
    },
    {
      "id": "dist-cap-43ec806f",
      "tier": "scalability",
      "goal": "distributed",
      "maturity": "designed",
      "title": "Single-host single-instance topology is an explicit, documented architectural choice across all four supported deployment methods",
      "scope": "Confirmed: the four single-instance deployment topologies are documented and\nintentional (overview lines 108-116; ADRs 0012-0016, 0018). NOT confirmed and\nexplicitly NOT provided by this capability: any redundancy, replication,\nmulti-AZ/multi-region placement, clustering, or automated failover — none\nexists in any topology. This is a documentation/intent capability about the\nboundary being declared, not a resilience capability. Data-residency /\nregion-binding policy is unaddressed (no multi-region surface exists).\n"
    },
    {
      "id": "dist-cap-827afb47",
      "tier": "scalability",
      "goal": "distributed",
      "maturity": "implemented",
      "title": "Token-revocation state is consistently propagated to the live WebSocket connection within the single Core process",
      "scope": "Confirmed in code for the WebSocket auth handshake path (cev-a1000010):\nrevocation drops the live socket within the single Core process. NOT a\ndistributed capability — it works precisely because there is exactly one\nprocess and one failure domain; it does not extend to any multi-instance,\nreplicated, or cross-host topology (none exists). The REST request path is\nre-validated per request (cev-a1000002) rather than via a held callback.\nDoes not address availability of the single instance (see findings) or\ncross-node consistency (not applicable — no second node).\n"
    },
    {
      "id": "ephem-cap-32f4a499",
      "tier": "scalability",
      "goal": "ephemeral",
      "maturity": "implemented",
      "title": "Core container image pins base layers and binaries by immutable sha256 digest",
      "scope": "Confirmed for the Core image: the buildkit frontend and the go2rtc binary\nare digest-pinned (IaC evidence, infra/core-Dockerfile). NOT addressed —\nand explicitly contradicted — at the add-on layer: the mosquitto add-on base\nis pinned to the mutable floating `:trixie` tag (finding ephem-0a000007), so\nthis capability does not extend to the add-on build path. The `BUILD_FROM`\narg of the Core image itself is supplied externally and its digest-pinning\nis not visible in this Dockerfile.\n"
    },
    {
      "id": "ephem-cap-5113fad9",
      "tier": "scalability",
      "goal": "ephemeral",
      "maturity": "implemented",
      "title": "Immediate refresh-token revocation that cascades to all access tokens and drops live WebSocket sockets",
      "scope": "Confirmed: revocation is immediate, cascades from refresh token to all\nderived access tokens, and propagates to live WS sockets via a revoke\ncallback (cev-a1000010). NOT addressed: revocation is user-initiated and\nmanual — there is no automatic time-based expiry or rotation that would\nfire revocation without a human action (findings ephem-0a000001/0a000002),\nand the WS revoke-callback cross-cuts Distributed for connection-lifecycle.\n"
    },
    {
      "id": "ephem-cap-f5d582d0",
      "tier": "scalability",
      "goal": "ephemeral",
      "maturity": "implemented",
      "title": "Short-lived (1800s) access tokens backed by a separate longer-lived refresh token",
      "scope": "Confirmed: access-token TTL is 1800s and is enforced at the central\nvalidation chokepoint (cev-a1000002) for both REST and WS auth. NOT\naddressed by this capability: the backing refresh token never expires and\nis not rotated (finding ephem-0a000001), Long-Lived Access Tokens last 10\nyears (ephem-0a000002), and the per-token jwt_key never rotates\n(ephem-0a000003) — so the short access-token TTL is undermined by the\nunbounded refresh-token lifetime behind it. This capability is the\naccess-token half only.\n"
    },
    {
      "id": "ephem-cap-fb2d6d4d",
      "tier": "scalability",
      "goal": "ephemeral",
      "maturity": "designed",
      "title": "Short-lived signed paths with a 30-second default expiry for GET authorization",
      "scope": "Confirmed from the developer auth documentation: signed paths default to a\n30-second expiry and are invalidated on refresh-token deletion, user\ndeletion, and restart. Maturity is designed (the evidence is the auth\nreference doc, not a code-recon pointer to the signing/verification\nimplementation). NOT addressed: the access check is only at request receipt\n— a response that streams past the expiry continues (documented caveat), and\nthis capability covers only the signed-path GET surface, not the bearer or\nwebhook paths.\n"
    },
    {
      "id": "immut-cap-5e14aa20",
      "tier": "auditability",
      "goal": "immutability",
      "maturity": "implemented",
      "title": "Supervisor backup supports optional password-based archive protection (default off)",
      "scope": "Confirmed present as an OPTIONAL parameter that defaults to None (off) — see\nfinding immut-bkp00002 for the gap. NOT addressed: there is no object-lock/WORM/\nretention/legal-hold on the archive store, no signed integrity manifest\nindependent of the password, and no default protection — when the password is\nunset (the default) the archive has neither encryption nor any integrity MAC.\nThis capability is a per-backup opt-in only; it provides no immutability of the\nstorage tier and no protection against deletion.\n"
    },
    {
      "id": "immut-cap-937d14c1",
      "tier": "auditability",
      "goal": "immutability",
      "maturity": "implemented",
      "title": "Core Dockerfile pins the docker/dockerfile build frontend by immutable sha256 content digest",
      "scope": "Confirmed ONLY for the dockerfile *syntax frontend* in the core Dockerfile (line\n1). NOT addressed and explicitly absent (see finding immut-img00005): the base\nimage itself (core/supervisor build FROM mutable BUILD_FROM / version tags) and\nthe add-on base images (mosquitto build_from :trixie floating tags) are NOT\ndigest-pinned, and there is no retained per-deploy SBOM or immutable\ndeployment-provenance record. This capability covers a single build-frontend pin,\nnot the runtime image artifacts.\n"
    },
    {
      "id": "intg-cap-70ef26f7",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "Optional NaCl SecretBox authenticated encryption on mobile_app webhook payload bodies",
      "scope": "Confirmed: the secret is minted at registration and SecretBox AEAD protects the\nbody when supports_encryption is enabled (cev-a1000014; sending-data.md). NOT\ncovered / caveated: encryption is OPTIONAL (a registration may proceed without it\nif libsodium is unavailable), it protects only the body — NOT webhook_call_service\nauthorization (intg-webhook-callservice-noauthz) — and no nonce/sequence binding\nis documented, so it is not a replay-protection control\n(intg-webhook-no-idempotency).\n"
    },
    {
      "id": "intg-cap-7a54b1a7",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "Single-chokepoint access-token validation rejects revoked refresh tokens and inactive users before any write",
      "scope": "Confirmed: centralized validation with fixed algorithm, revocation check, and\nactive-user check (cev-a1000002) reused by REST middleware (cev-a1000009) and the\nWS handshake (cev-a1000010). NOT covered: the integrity of the per-refresh-token\njwt_key itself is only 0600-file-protected at rest with no MAC\n(intg-storage-no-integrity-mac), so a tampered/leaked jwt_key forges a token that\nthis chokepoint accepts as valid; revocation is by refresh-token delete only, with\nno automatic access-token expiry analysis in this lens (routed to ephemeral).\n"
    },
    {
      "id": "intg-cap-e18bb24c",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "Permission policy compilation fails closed to deny-all on an empty or corrupt policy",
      "scope": "Confirmed: deny-all compilation for empty/None policy (cev-a1000006). NOT covered:\nthis protects against absent/corrupt-to-empty policy only; a DIRECTED tamper that\nsets a policy to True (allow-all) or flips is_admin still escalates silently\nbecause there is no integrity MAC on the record (finding\nintg-storage-no-integrity-mac); owner all-access (cev-a1000008) is unconditional\nregardless of policy state.\n"
    },
    {
      "id": "intg-cap-e88c8857",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "Supervisor SecurityMiddleware enforces a default-deny per-role URL ACL on the privileged add-on API",
      "scope": "Confirmed: token->app->role-ACL default-deny enforcement (cev-b2000001), per-role\npath allow-lists (cev-b2000002), and ingress header-injection-with-strip\n(cev-b2000005). NOT covered: ROLE_ADMIN matches everything (re.compile(\".*\"),\ncev-b2000002), so an admin-role add-on or one with protection mode disabled\nreaches the full Supervisor API and the Docker socket -> host root — the gate\nweakens to nothing for that configuration; runtime enforcement of protection-mode\nand AppArmor was not separately confirmed in code beyond the role ACL.\n"
    },
    {
      "id": "intg-cap-ecebb879",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "Per-entity READ permission enforced at the state view with deny-all-by-default policy compilation",
      "scope": "Confirmed: per-entity READ enforcement on GET /api/states/{entity_id}\n(cev-a1000011) and per-entity scoping of bulk reads (cev-a1000007), with\ndeny-all-by-default compilation (cev-a1000006). NOT covered (see related\nfindings): the WRITE path is admin-or-deny with no per-entity write policy\n(intg-state-write-coarse-authz); the per-entity filter SHORT-CIRCUITS to allow-all\nfor any admin (cev-a1000007) and owner is unconditional all-access (cev-a1000008),\nso there is no sub-admin write scoping; the webhook path bypasses this engine\nentirely (intg-webhook-callservice-noauthz).\n"
    },
    {
      "id": "nonrep-cap-510a35c7",
      "tier": "auditability",
      "goal": "non_repudiation",
      "maturity": "implemented",
      "title": "Recorder history DB with context_user_id field provides a durable, queryable record of entity-state changes",
      "scope": "Confirmed: a durable, queryable history of entity-state changes exists in the\nRecorder DB with a context_user_id field for actor association\n(cev-a1000018; /api/logbook in api/rest.md).\nNOT addressed / explicitly out of scope: this is a user-facing state-history\nsurface, NOT a security audit log — it does not record authentication events,\ntoken/credential lifecycle, permission decisions, administrative/Supervisor\noperations, or host-root actions (see findings nonrep-00000001 / 4 / 5 / 6).\nThe actor field is observed NULL in the documented sample (context_user_id:\nnull), so attribution is frequently absent (finding nonrep-00000002).\nTamper-resistance and retention of these rows is an Immutability question (the\nrows have no MAC / append-only protection); the recorder is a mutable store.\n"
    },
    {
      "id": "nonrep-cap-e865e0d3",
      "tier": "auditability",
      "goal": "non_repudiation",
      "maturity": "implemented",
      "title": "Supervisor SecurityMiddleware emits a diagnostic warning naming the add-on on a role-denied privileged API call",
      "scope": "Confirmed: denied (role-miss) privileged Supervisor API calls produce a\ndiagnostic warning naming the add-on and path (cev-b2000001).\nNOT addressed / explicitly out of scope: this is a diagnostic logger line, NOT\na durable, tamper-evident, retained audit stream; and it covers only the DENY\nbranch — successful (ALLOWED) privileged operations such as add-on install,\nbackup create/restore, and Docker container exec produce NO record (finding\nnonrep-00000005). There is no actor beyond the add-on identity, no separate\naudit sink, and no retention/access-control posture.\n"
    },
    {
      "id": "resil-cap-6a038f48",
      "tier": "scalability",
      "goal": "resilient",
      "maturity": "implemented",
      "title": "WebSocket connection state self-corrects by dropping the live socket on token revocation",
      "scope": "Confirmed for the Core WebSocket connection lifecycle (cev-a1000010),\ngrounded in code evidence. Covers the drop-on-revocation transition only;\nit does NOT address reconnect/backoff behavior on the client side\n(unspecified — resil-01000005), nor any WS connection/subscription quota\n(an open Availability finding, avail-4be2dd70). The recovery here is the\nserver forcing the socket closed; the client's resilient reconnection is\nout of scope of this capability.\n"
    },
    {
      "id": "resil-cap-c76c9240",
      "tier": "scalability",
      "goal": "resilient",
      "maturity": "implemented",
      "title": "Push relay enforces a per-token rate limit bounding abuse on the single notification path",
      "scope": "Confirmed at the relay's handleRequest entrypoint (cev-08000001), grounded\nin code evidence — a per-token (not per-caller) rate limit returning 429.\nIt bounds per-token volume only; it is NOT relay-outage resilience (no\nretry/queue/fallback when the relay itself is down — resil-01000006), does\nNOT authenticate the caller (any valid-format token drives the relay — a\nNon-Repudiation/Authenticity gap owned elsewhere), and does not provide a\nrelay availability SLA or regional redundancy (avail-a2cfd41c).\n"
    },
    {
      "id": "resil-cap-fa365a2d",
      "tier": "scalability",
      "goal": "resilient",
      "maturity": "implemented",
      "title": "Permission engine fails closed (deny-all) on an empty, missing, or unparseable policy",
      "scope": "Confirmed for the per-entity permission decision path in Core\n(compile_policy, cev-a1000006), grounded in code evidence. This is one\nfail-safe point, NOT a platform-wide degradation strategy: it does not\naddress the shared-event-loop stall failure mode, outbound-integration\ntimeouts/breakers, or any declared read-only/safe-mode for dependency\nunavailability — those are open Resilient findings (resil-01000001/2/8).\nThe owner identity short-circuits the policy entirely (cev-a1000008), so\nthe fail-closed property protects non-owner scoping only.\n"
    }
  ],
  "strengths": [],
  "findings": [
    {
      "id": "avail-235dacf0",
      "title": "No per-integration resource quota; one of 2000+ in-process integrations can stall the Core event loop or recorder DB",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "2000+ integrations share Core's single event loop and recorder DB with no per-integration resource quota, so one slow or misbehaving integration degrades the whole platform's availability.",
      "detail": "Integrations run unsandboxed in Core's single asyncio process at full\nprivilege, and the threat model records that \"a misbehaving integration\nblocks Core's single event loop or exhausts the recorder DB ... integrations\nshare Core's single event loop with no per-integration resource quota\"\n(tm-35a0b188). The recorder DB session path (cev-a1000018) is the\nhome-occupancy/lock/alarm history store; recorder exhaustion or a blocking\nintegration call also degrades /api/history and any automation that reads\nhistory (tm-60f1d9cf). Because there is one process and one host, the blast\nradius of a single slow integration or an unbounded recorder write is the\nentire automation platform, including safety automations.\n\nThis is the capacity/resource-availability facet (no quota / no ceiling on\na shared resource). The *behavior* a healthy design would add — timeouts,\nbulkheads, circuit-breaking around an integration — is owned by Resilient;\nthe *isolation topology* (sandboxing integrations out of the single\nprocess) is owned by Distributed. Here the Availability concern is the\nabsence of any capacity ceiling or resource quota protecting the shared\nevent loop and recorder DB.\n\nSeverity is high under the *api-security* rubric availability common-pattern\n\"no timeout on outbound calls ... thread-pool exhaustion possible during\nvendor degradation\" (high: vendor/integration slow-down cascades to total\nexhaustion, not remediable mid-incident without restart). Confidence is\nmedium: the absence of a quota is confirmed in the threat model, but the\nprecise recorder back-pressure behavior (e.g. queue bound) is not in the\ncode-evidence index.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "Recorder DB session for entity-state history"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.AuthManager.async_create_access_token:L599-L617@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "return jwt.encode({...}, refresh_token.jwt_key, algorithm=\"HS256\")"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Bound per-integration resource use (execution timeout + recorder write back-pressure) so one integration cannot starve the shared loop.",
        "detail": "Introduce a per-integration execution-time budget / watchdog on the\nshared event loop and a bounded recorder write queue (cev-a1000018) so a\nsingle slow or runaway integration cannot block the loop or exhaust the\nrecorder DB that backs alarm/lock history. This is a capacity ceiling;\npair it with the Resilient lens's timeout/bulkhead recommendation and\nthe Distributed lens's integration-isolation recommendation rather than\nduplicating them.\n",
        "references": [
          "internal: 00-context/context-brief.md §8 (integrations run unsandboxed in one process)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-6",
          "SC-5",
          "SI-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-400"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Recorder DB write back-pressure / queue-bound behavior and any per-integration execution timeout or watchdog"
      ]
    },
    {
      "id": "avail-4be2dd70",
      "title": "No rate limit on Core REST/WS boundary, including the WS auth_required handshake and expensive routes",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "The Core REST and WebSocket boundary has no documented rate limit; unauthenticated WS auth_required handshakes and expensive REST routes can exhaust the single event loop.",
      "detail": "The Core REST API (tm-04eb6424) and WebSocket API (tm-621d5347) are served\nby the single Core asyncio process with no documented throttle at the\nboundary. Three resource-exhaustion surfaces follow on the single event\nloop:\n\n- The WS handshake (cev-a1000010) runs auth_required -> auth before the\n  socket is authenticated; an attacker can open many sockets to occupy the\n  handshake/validation path on the one event loop with no connection\n  quota documented.\n- Expensive REST routes (/api/template server-side Jinja2 render\n  cev-a1000013, and /api/history) do proportional work; the threat model\n  notes \"no documented throttle on expensive routes.\"\n- The WS server holds long-lived sockets/subscriptions with \"no stated\n  connection/subscription quota\" (tm-621d5347).\n\nTLS terminates at a reverse proxy and HA serves HTTP on 8123, but the\nthreat model records no throttle is documented at the Core boundary\nitself, so any reverse-proxy throttle (if present) is not in evidence.\n\nSeverity is high under the *api-security* rubric: the availability\ncommon-pattern \"no timeout/quota on a path that exhausts the single\nrequest handler\" is high, and OWASP API4 (Unrestricted Resource\nConsumption) applies to the auth-handshake and expensive-route surfaces.\nConfidence is medium because a reverse-proxy or per-IP guard could exist\nout-of-band; the artifacts are silent on it, but the in-code WS handshake\nand expensive-route surfaces are confirmed.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.websocket_api.auth.AuthPhase.async_handle:L85-L123@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "auth_required->auth handshake; validates access token"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APITemplateView.post:L479-L505@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "tpl = _cached_template(data[\"template\"], ...); tpl.async_render(...)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Enforce per-IP/per-token connection and request rate limits at the Core boundary, including the pre-auth WS handshake and expensive routes.",
        "detail": "Add a connection/handshake quota on the WS path (cev-a1000010) so a\nflood of unauthenticated auth_required sockets cannot saturate the event\nloop, and a per-route rate limit on /api/template (cev-a1000013) and\n/api/history. Specify per-endpoint thresholds, the identity dimension\n(per-IP for pre-auth, per-token post-auth), the time window, and the\nbreach behavior. If a reverse-proxy throttle is the intended control,\ndocument it in the hardening baseline so the boundary is not silently\nunbounded.\n",
        "references": [
          "internal: 00-context/context-brief.md §6 (TLS posture at the Core boundary)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-5(1)",
          "SC-6"
        ],
        "attack": [
          "T1499"
        ],
        "cwe": [
          "CWE-770"
        ],
        "owasp_api": [
          "API4:2023"
        ],
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
      "id": "avail-5af6fee5",
      "title": "Supervisor backup is the sole recovery path with no RTO/RPO, restore verification, or retention",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Full/partial Supervisor backups are the only recovery mechanism for the single-host instance, yet no recovery-time/recovery-point objective, restore-test cadence, or retention is defined.",
      "detail": "Supervisor backups (cev-b2000006) bundle config, the recorder DB, and\nsecrets/tokens into full/partial archives and are the recovery path for\nthe single-host instance (tm-28d50718: \"Backups are the recovery path for\nthe single-host instance; denial of service / data-loss applies if backups\nare absent, corrupted, or destroyed\"). The intake evidence-gap list\nrecords \"No SLO/RTO/RPO\" and \"No object-lock/WORM/retention policy stated\nfor backups.\" There is therefore no stated recovery-point objective (how\nmuch history loss is acceptable on restore), no recovery-time objective\n(how long to stand the instance back up), and no documented periodic\nrestore verification.\n\nThe availability concern here is the recovery-timeliness/recoverability\nfacet of the contingency plan: a recovery mechanism whose timeliness and\npoint-of-recovery are undefined cannot be relied on to meet any\nreachability objective after a host loss or the catastrophic\nScheduleWipeDevice path (cev-c3000002). The *confidentiality* of the\ndefault-unencrypted backup is routed to Confidentiality; the *immutability*\n/ retention / object-lock gap is routed to Immutability; this finding is\nstrictly the absence of recovery objectives and restore verification.\n\nSeverity is medium under the *api-security* rubric availability\ncommon-pattern family (SLO/contingency undeclared for the recovery path).\nIt is medium rather than high because backups do exist (a recovery path is\npresent), but their objectives are unstated and unverified.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.backups.backup.Backup.set_password:L122-L353@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "full snapshots (config + recorder DB + secrets/tokens)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.ScheduleWipeDevice:L29-L55@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "schedule factory-reset / datadisk wipe over D-Bus"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Define RTO/RPO for restore from backup, document a periodic restore-verification procedure, and state a retention policy.",
        "detail": "State the recovery-point objective the backup cadence delivers (the\nacceptable recorder-history loss window) and a recovery-time objective\nfor rebuilding the single-host instance from a Supervisor archive\n(cev-b2000006). Document and schedule a restore-verification procedure so\nbackups are known-good (an unverified backup is not a recovery control).\nCoordinate the retention/immutability half with the Immutability lens and\nthe at-rest-encryption half with the Confidentiality lens.\n",
        "references": [
          "internal: 00-context/context-brief.md §6 (DR/RTO/RPO + availability targets; Backup immutability / retention)"
        ]
      },
      "mappings": {
        "nist": [
          "CP-9",
          "CP-9(1)",
          "CP-10",
          "CP-2"
        ],
        "attack": [],
        "cwe": [
          "CWE-404"
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
      "id": "avail-754cfc01",
      "title": "No availability SLO/SLI declared for the Core device-control + alarm path",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Home Assistant Core declares no availability target, SLI, or error budget for its consequential device-control/alarm/lock path, so reachability against a stated objective cannot be verified.",
      "detail": "The consequential-action path in this system is physical device control\nand alarm/lock state mutation (POST /api/services/<domain>/<service> and\nPOST /api/states/<entity_id>), which the brief identifies as the\nadjudication-equivalent path with real safety stakes (a downed instance =\nno automation, no alarm). The threat-model author flagged D=21 blocked\ncells: \"no documented rate-limit / SLO / capacity model,\" and the intake\nevidence-gap list records \"No SLO/RTO/RPO; HA is single-Core single-host\nby design.\" No artifact states an availability objective (e.g. monthly\nuptime), a success-rate or p95-latency SLI on the service-call path, a\ntime window, or an error budget.\n\nWithout a declared SLO and matching SLIs there is no objective against\nwhich to measure whether the platform is reachable when an alarm or lock\nautomation must fire, and no basis to prioritize reliability work. This is\na measurement gap, not a topology gap; the single-host topology that\n*produces* the availability ceiling is routed to Distributed and the\nfailure-on-component-loss behavior to Resilient.\n\nSeverity is medium under the *api-security* rubric clause \"SLO and error\nbudget undeclared for consequential paths (authentication, payment,\nPII-read)\" — here the consequential path is device-control/alarm. The\nrubric pegs this pattern at medium (cannot verify implicit availability\ncommitments; cannot prioritize reliability work). It does not rise higher\nbecause Home Assistant is a self-hosted, owner-operated product with no\ncontractual uptime clause in the artifacts.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "No bearer, no rate-limit observed here."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.webhook_call_service:L269-L292@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "await hass.services.async_call(...) # actuates locks/alarms"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Declare an availability SLO + SLIs for the device-control/alarm path and publish a hardening baseline target.",
        "detail": "Define an availability objective for the consequential path\n(service-call success rate and end-to-end latency on POST\n/api/services/<domain>/<service> and POST /api/states/<entity_id>),\nan SLI to measure it, and a rolling window. For a single-host\nowner-operated deployment the realistic ceiling is the host's own\nuptime; state that ceiling explicitly in the hardening guidance\n(org/SECURITY.md is currently a 6-line pointer with no hardening\ncontent) so operators of safety automations (alarm, lock) understand\nthe reachability they are committing to. Pair this with the capacity\nand health-check work in the related findings.\n",
        "references": [
          "internal: 00-context/context-brief.md §6 Evidence Gaps (No SLO/RTO/RPO)"
        ]
      },
      "mappings": {
        "nist": [
          "CP-2",
          "CP-2(3)",
          "SI-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-770"
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
      "id": "avail-a292763c",
      "title": "mobile_app webhook entrypoint has no rate limit, exhausting the single Core event loop",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "handle_webhook accepts unauthenticated webhook_id-keyed requests that drive blocking service calls on the single Core event loop with no observed rate limit, enabling resource-exhaustion DoS of the whole platform.",
      "detail": "handle_webhook (cev-a1000016) maps a webhook_id to a config_entry with no\nbearer token and the code recon explicitly notes \"No bearer, no rate-limit\nobserved here.\" The path then reaches webhook_call_service (cev-a1000015),\nwhich calls arbitrary services with blocking=True on Core's single asyncio\nevent loop. Because Core is a single process on a single host\n(tm-296e2800) with no documented per-caller throttle, a holder (or\nguesser) of a webhook_id — or any party hitting the public cloudhook URL —\ncan flood the one event loop with blocking service calls and degrade or\nstall the entire automation platform, including the alarm and lock paths.\n\nThis is the Availability facet (resource consumption / SC-5) of the\nbearer-less webhook surface. The authentication-by-possession and\nmissing-authz facets are owned by Authenticity/Integrity; here the concern\nis strictly unrestricted resource consumption against the single-process\nfailure domain.\n\nSeverity is high under the *api-security* rubric. The availability\ncommon-pattern \"No timeout/quota on a path that can exhaust the single\nrequest handler\" calibrates to high because vendor/caller slow-down\ncascades to total handler exhaustion and cannot be remediated mid-incident\nwithout restart; here the blocking=True service call on the single event\nloop is exactly that single-handler exhaustion surface, and the caller is\nunauthenticated. OWASP API4 (Unrestricted Resource Consumption) applies.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "No bearer, no rate-limit observed here."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.webhook_call_service:L269-L292@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "async_call(..., blocking=True, context=registration_context(...))"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add a per-webhook_id and per-source rate limit + a non-blocking dispatch bound on the webhook path.",
        "detail": "Apply a rate limit keyed on webhook_id and on source identity at the\nhandle_webhook entrypoint (cev-a1000016) before the call reaches\nwebhook_call_service (cev-a1000015), with explicit behavior on breach\n(reject with 429 + Retry-After). Bound the work the single event loop\nwill accept from one webhook so a flood of blocking=True service calls\ncannot starve alarm/lock automations. Because the cloudhook URL is\ninternet-reachable, the limit must apply at the Core boundary, not only\nat the reverse proxy.\n",
        "references": [
          "internal: 00-context/context-brief.md §6 (mobile_app webhook authN/authZ; no rate-limiting)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-5(1)",
          "SC-6"
        ],
        "attack": [
          "T1499"
        ],
        "cwe": [
          "CWE-770"
        ],
        "owasp_api": [
          "API4:2023"
        ],
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
      "id": "avail-a2cfd41c",
      "title": "Push-notification delivery depends on a single Firebase relay with no stated availability SLA",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "low",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "Mobile push notifications (including alarm/security alerts) route through a single hosted Firebase Cloud Functions relay whose availability characteristics and SLA are unstated.",
      "detail": "The mobile-apps-fcm-push relay (cev-08000001, cev-08000002) is a single\nFirebase Cloud Functions service that forwards every push notification to\nAPNS/FCM. Security-relevant alerts (alarm-triggered, lock, presence\nnotifications) depend on this relay being reachable. The relay is named in\nthe inventory as an external_dependency with medium confidence, and no\nartifact states its availability target, regional redundancy, or a\nfallback delivery path if the relay (or its single configured region,\nus-central1 per the README) is unavailable. The relay does apply a\nper-token rate limit (a capability recorded separately), which bounds\nabuse but does not address relay-outage availability.\n\nThe Availability concern is dependency reliability: a critical\nnotification dependency with no cited SLA, where the design's overall\nnotification-delivery availability is bounded by this single relay's\navailability. The *behavior* when the relay is down (retry, queue, degrade)\nis routed to Resilient.\n\nSeverity is low under the *api-security* rubric: this is a\ndefense-in-depth / dependency-reliability gap on a notification path, not\nthe primary control plane (device control works LAN-locally without the\nrelay). Confidence is medium because the relay's redundancy posture is not\nin the artifacts.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:__route__POST__/api/sendPushNotification:L40-L43@142579dc41ee534f0d60bc390c4661dba051a995",
          "excerpt": "Public relay route forwarding notifications to APNS/FCM"
        },
        {
          "artifact": "mobile/mobile-apps-fcm-push-README.md",
          "locator": "lines 36-41",
          "excerpt": "set the app.region setting ... another location than us-central1"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "State the push-relay availability dependency and a degraded notification path for relay outage.",
        "detail": "Document the Firebase relay as a single external availability dependency\nfor notification delivery (cev-08000002) and define the behavior when it\nis unreachable — e.g. a local/persistent-notification fallback so that an\nalarm event is still surfaced in the app on next reachable connection.\nCoordinate the outage-behavior half with the Resilient lens.\n",
        "references": [
          "internal: 00-context/asset-inventory.yaml (asset-8c1d7e46 push relay; tb-1f5c9a83)"
        ]
      },
      "mappings": {
        "nist": [
          "CP-2(5)",
          "SC-5",
          "SI-13"
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
      "prerequisite_evidence": [
        "Firebase relay availability SLA / regional-redundancy posture and any push-delivery fallback path"
      ]
    },
    {
      "id": "conf-2029ce78",
      "title": "Android Companion trusts user-installed CAs with no certificate pinning, exposing tokens and PII in transit to MitM",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "risk",
      "summary": "`TLSHelper.setupOkHttpClientSSLSocketFactory` initializes the OkHttp trust manager from the AndroidCAStore, which includes user-installed CAs, and applies no fixed-server pinning; a user-installed/malicious CA lets a network MitM decrypt the token- and PII-bearing channel to Core.",
      "detail": "`common...data.TLSHelper.setupOkHttpClientSSLSocketFactory` (cev-f6000002)\nbuilds the OkHttp SSL socket factory from\n`KeyStore.getInstance(\"AndroidCAStore\")` and initializes the\n`TrustManagerFactory` with that store. The AndroidCAStore trusts\nUSER-installed CA certificates, and no certificate/public-key pinning is\napplied (the recon note: \"No fixed-server pinning (self-hosted)\"). The\nvalidation itself is standard X509, so this is not a trust-all/disabled-\nvalidation case — but the trust anchor set is attacker-influenceable.\n\nThe confidentiality consequence is in-transit exposure: against the\n`network_mitm` position, an attacker who can get a CA into the user store\n(social engineering, MDM, a malicious profile) or who already controls a\ntrusted-but-mis-issued CA can transparently intercept the\nmobile->Core channel (cev-0a000005), which carries the bearer token and\nhome-occupancy/location PII. Because HA is self-hosted there is no fixed\nserver certificate to pin to a vendor root, so the design accepts a broad\ntrust anchor by default.\n\nHigh severity under the *mobile-applications* rubric clause \"No\ncertificate or public-key pinning on a high-value channel whose threat\nmodel includes user-installed MitM CAs or hostile networks\" (MAS mapping:\nMASVS-NETWORK-2). High rather than critical because stock-device default\nTLS still defeats the casual on-path attacker who has not placed a CA. The\n*identity*-of-endpoint (pinning-as-authentication) facet routes to\nAuthenticity; this finding owns the confidentiality of the data in\ntransit.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "KeyStore.getInstance(\"AndroidCAStore\")... builder.sslSocketFactory(..., trustManagers[0] as X509TrustManager)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Offer optional public-key pinning / trust-on-first-use and exclude user CAs for the configured instance channel.",
        "detail": "In `TLSHelper.setupOkHttpClientSSLSocketFactory` (cev-f6000002), since a\nfixed vendor root cannot be pinned for self-hosted instances, support a\ntrust-on-first-use (TOFU) public-key pin captured at instance\nonboarding and enforced on subsequent connections, and provide a\nuser-visible option to exclude user-installed CAs (build the trust\nmanager from the system CA store plus the pinned key only). Surface a\npin-mismatch as a security event. This preserves self-signed/custom-CA\nsupport for advanced users while removing the silent-MitM default for\nthe token/PII channel.\n",
        "references": [
          "external: OWASP MASTG MASVS-NETWORK-2 (identity pinning)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-8",
          "SC-8(1)",
          "SC-23",
          "SC-17"
        ],
        "attack": [
          "T1557"
        ],
        "cwe": [
          "CWE-295"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-NETWORK-2"
        ],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-205c53a5",
      "title": "Android Companion Room database stores location history and bearer tokens as unencrypted SQLite (no SQLCipher)",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "`DatabaseModule.provideAppDatabase` builds the Room AppDatabase with no SQLCipher/openHelperFactory, so the location_history table (raw lat/long) and the ServerSessionInfo access/refresh tokens persist as unencrypted SQLite, readable from a stolen or rooted device or a device backup.",
      "detail": "`common...database.DatabaseModule.provideAppDatabase` (cev-f6000003)\nconstructs the Room database via\n`Room.databaseBuilder(context, AppDatabase::class.java, DATABASE_NAME)...build()`\nwith NO `openHelperFactory` and no SQLCipher integration. The resulting\nSQLite file is plaintext on disk. Two crown-jewel data classes live in\nthis database:\n\n- `location_history` (raw latitude/longitude + zones) — on-device PII at\n  rest (mobile_on_device_location_and_entity_cache).\n- `ServerSessionInfo` (cev-f6000004) — the persisted access AND refresh\n  bearer tokens (mobile_stored_session_and_refresh_tokens), with an\n  observed in-degree of 21 (heavily depended upon).\n\nAgainst the `physical_thief_with_stolen_device` and\n`rooted_device_attacker_with_frida` positions, the app's own intent of\n\"EncryptedSharedPreferences/Keystore\" (android docs) does not extend to\nthis Room store, so a backup extraction or root read yields both the\noccupant's location history and a live refresh token that replays into the\nCore backend (the mobile->Core hop, cev-0a000005). The refresh token's\nlack of server-side rotation/expiry amplifies this (route to Ephemeral).\n\nHigh severity under the *mobile-applications* rubric clause \"Sensitive\ndata — access/refresh tokens, PII/PHI, or keys — persisted in unprotected\non-device storage (… unencrypted SQLite …) rather than the\nKeystore/Keychain, readable from a device backup or a stolen device\"\n(MAS mapping: MASVS-STORAGE-1; MASWE-0006). The reversibility/data-\nsensitivity modifier (a long-lived refresh token + PII) and the\nblast-radius modifier (token pivots to backend) both load.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...database.DatabaseModule.DatabaseModule.provideAppDatabase:L38-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "Room.databaseBuilder(context, AppDatabase::class.java, DATABASE_NAME).addMigrations(...).build()"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...database.server.ServerSessionInfo.ServerSessionInfo:L1-L1@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "persisted access + refresh bearer tokens (in_degree 21)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Encrypt the Room AppDatabase (SQLCipher) with a Keystore-held key, or move tokens out of the plaintext DB.",
        "detail": "Pass a SQLCipher `SupportFactory` to `Room.databaseBuilder` in\n`provideAppDatabase` (cev-f6000003) with the passphrase wrapped by a\nnon-exportable AndroidKeyStore key (the app already uses the hardware-\nbacked Keystore for the mTLS key, cev-f6000001 — reuse that custody\npath). At minimum, relocate the `ServerSessionInfo` access/refresh\ntokens (cev-f6000004) out of the plaintext Room store into a\nKeystore-backed EncryptedSharedPreferences/DataStore so a backup or root\nread does not yield a replayable backend credential. Pair with\n`android:allowBackup=false` / backup-exclusion for the DB file.\n",
        "references": [
          "external: OWASP MASTG MASVS-STORAGE-1 (secure local storage)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-28",
          "SC-28(1)",
          "SC-13"
        ],
        "attack": [
          "T1409"
        ],
        "cwe": [
          "CWE-312",
          "CWE-922"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-STORAGE-1"
        ],
        "maswe": [
          "MASWE-0006"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-3060c50e",
      "title": "Access token crosses the native-to-WebView JS external-auth bridge in cleartext to a remotely-served frontend",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The Companion apps hand the Core access token to the in-WebView frontend over the external-auth JS bridge (window.externalAppV2 / webkit.messageHandlers) in cleartext; the frontend is the remote self-hosted instance's page, so a hostile/MitM'd server response that runs in the WebView can read the bearer token.",
      "detail": "The frontend requests the bearer token from native by posting\n`getExternalAuth` over the bridge, and native replies by calling\n`window.externalAuthSetToken(true, {access_token, expires_in})`\n(frontend-external-authentication.md). On the JS side,\n`ExternalMessaging._sendExternal` (cev-07000001) dispatches to\n`window.externalAppV2.postMessage(...)` /\n`window.webkit.messageHandlers.externalBus.postMessage(msg)`, and the iOS\nnative handler `WebViewExternalMessageHandler.handleExternalMessage`\n(cev-e5000001) switches on the message type with NO origin/integrity check\non the message source. The token therefore transits the bridge as\ncleartext JSON.\n\nThe amplifier is that the WebView renders the REMOTE server frontend\n(cev-0a000005): the JS that runs alongside the token-bearing bridge is\nserved by the user-configured Core instance over the network. Against the\n`compromised_backend_or_response` and `network_mitm` positions (and the\nAndroid user-CA trust of conf-androidtls), a hostile or MitM'd frontend\npayload executing in the WebView can call `getExternalAuth` and exfiltrate\nthe access token — the doc itself warns that callback names must be\nverified \"to ensure the callback has not been forged\"\n(frontend-external-authentication.md), confirming the channel's trust is\nname-based, not origin/integrity-based.\n\nHigh severity under the *mobile-applications* rubric clause \"A WebView\nJavaScript bridge exposes native capability or data to loaded web content\nwithout origin allowlisting\" (MAS mapping: MASVS-PLATFORM-2; here the data\nexposed is the backend bearer token). The blast-radius modifier loads:\ntoken theft pivots from the device to the Core backend at the token's full\nprivilege. The identity/forgery half of the warned callback-forgery risk\nroutes to Authenticity; this finding owns the confidentiality of the token\non the channel.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:src.external_app.external_messaging.ExternalMessaging._sendExternal:L491-L505@505966e84f3a90347c66261592908a02a4118189",
          "excerpt": "window.webkit!.messageHandlers.externalBus.postMessage(msg)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "guard let incomingMessage = WebSocketMessage(dictionary) ... switch externalBusMessage"
        },
        {
          "artifact": "auth/frontend-external-authentication.md",
          "locator": "## Get access token, lines 44-55",
          "excerpt": "window.externalAuthSetToken(true, {access_token: \"qwere\", expires_in: 1800})"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Gate the external-auth bridge by verified origin and stop handing the bearer token to remotely-served WebView content.",
        "detail": "On the native handlers (`handleExternalMessage`, cev-e5000001) enforce\nan origin allowlist so only the trusted first-party frontend origin can\ninvoke `getExternalAuth`, and reject bridge messages whose source frame\nis not the configured instance origin. Prefer not to expose the raw\naccess token to WebView JS at all: scope the bridge to the specific\noperations the frontend needs rather than returning the bearer, or use a\nshort-lived, audience-restricted token minted for the WebView session.\nOn the JS side (`_sendExternal`, cev-07000001) bind the channel to a\nper-session nonce rather than a stable callback name (the doc's\nname-verification guidance is necessary but not sufficient against a\ncompromised in-WebView origin).\n",
        "references": [
          "external: OWASP MASTG MASVS-PLATFORM-2 (WebView/JS-bridge hardening)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-8",
          "SC-8(1)",
          "AC-4",
          "SC-23"
        ],
        "attack": [
          "T1417"
        ],
        "cwe": [
          "CWE-749"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-PLATFORM-2"
        ],
        "maswe": [
          "MASWE-0068"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-7a74a4a0",
      "title": "iOS Companion compiles git-tracked GoogleService-Info Firebase config secrets into the IPA, recoverable by static analysis",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "risk",
      "summary": "`AppDelegate.setupFirebase` initializes Firebase from a git-tracked GoogleService-Info plist bundled into the IPA, so the Firebase project config (API key, sender/app IDs) is recoverable from any installed app by a reverse engineer.",
      "detail": "`Sources.App.AppDelegate.setupFirebase` (cev-e5000003) configures Firebase\nfrom the bundled `GoogleService-Info-*.plist`, which the run scope\nconfirms is git-tracked and compiled into the IPA\n(ios_bundled_firebase_config_secrets). Against the\n`reverse_engineer_with_ipa_apk` position, these config values are\nextractable from any copy of the app — they are binary-recoverable, not\nconfidential.\n\nThe confidentiality framing must be calibrated: a Firebase\nGoogleService-Info plist is a project CONFIG bundle (API key + sender ID +\napp ID), not a backend signing secret, and Google's model treats the\nmobile API key as identifying-not-authenticating when backend security\nrules are enforced server-side. So this is not the critical\n\"hardcoded backend credential granting backend access for the entire\ninstall base\" case unless the Firebase project's security rules are\npermissive. It IS a real exposure of a shared-across-the-install-base\nconfig secret whose abuse (quota/billing abuse, project enumeration,\npush-channel reconnaissance toward the fcm-push relay) is bounded by the\nserver-side rules.\n\nMedium severity: it sits below the *mobile-applications* Critical\n\"hardcoded backend credential … granting backend or third-party access for\nthe entire install base\" clause because the recovered material is config,\nnot a backend-access secret, but it remains a shared-secret exposure worth\nremediating. Confidence is medium because the abuse ceiling depends on the\n(unseen) Firebase security-rule posture. If code/config evidence shows the\nbundle carries a privileged key or permissive rules, this escalates to\ncritical.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.App.AppDelegate.AppDelegate.setupFirebase:L1-L1@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "configures Firebase from bundled GoogleService-Info plist"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Treat the Firebase config as non-confidential and enforce the security boundary server-side; remove it from version control.",
        "detail": "Confirm the Firebase project relies on server-side security rules and an\nApp Check / attestation gate rather than the bundled key for any\nsensitive operation, so the binary-recoverable config (cev-e5000003)\nconfers no backend privilege. Remove the git-tracked\nGoogleService-Info plist from version control (inject at CI build time)\nto limit casual disclosure, and rotate if it ever carried a privileged\nvalue. Document the asset explicitly as binary-recoverable config so it\nis not relied upon as a secret.\n",
        "references": [
          "external: OWASP MASTG MASVS-CRYPTO-2 (no secrets in the app package)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-28",
          "IA-5(7)",
          "SA-15"
        ],
        "attack": [
          "T1577"
        ],
        "cwe": [
          "CWE-312"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-STORAGE-1"
        ],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Firebase project security-rule posture and whether the bundled key carries privileged scope (determines abuse ceiling)"
      ]
    },
    {
      "id": "conf-a30cca33",
      "title": "iOS Companion stores access/refresh tokens in Keychain with default (non-hardened) accessibility",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "medium",
      "disposition": "risk",
      "summary": "`ServerManagerKeychain` persists the OAuth access/refresh tokens via KeychainAccess with no explicit kSecAttrAccessible set in source, defaulting to AccessibleWhenUnlocked (device-migratable) rather than the ThisDeviceOnly hardening expected for backend credentials.",
      "detail": "`Sources.Shared.API.ServerManagerPersistence.ServerManagerKeychain`\n(cev-e5000002) stores the access/refresh tokens via the KeychainAccess\n`set(_:key:)` path with `ignoringAttributeSynchronizable: true`. The recon\nnote records zero hits for `.accessibility(` across Sources, so no explicit\n`kSecAttrAccessible` is set — meaning the items default to\n`kSecAttrAccessibleWhenUnlocked`, NOT\n`…WhenUnlockedThisDeviceOnly` or `…WhenPasscodeSetThisDeviceOnly`.\n\nThe practical consequence is that the token items are eligible to migrate\nvia an unencrypted-or-weakly-protected device backup and are not bound to\nthe originating device, widening the `physical_thief_with_stolen_device`\nextraction surface: the tokens are the persisted session/refresh bearer\nestate (mobile_stored_session_and_refresh_tokens) that replays into Core\n(cev-0a000005). The Keychain still provides at-rest protection while the\ndevice is locked — which is why this is a hardening risk rather than a\nplaintext-storage gap like the Android Room case (conf-androidr).\n\nHigh severity under the *mobile-applications* rubric clause \"Sensitive\ndata — access/refresh tokens … persisted in unprotected on-device storage\n… readable from a device backup or a stolen device\" (MAS mapping:\nMASVS-STORAGE-1). Confidence is medium because the accessibility class is\ninferred from the absence of an explicit attribute in Sources rather than\na positive `kSecAttrAccessibleWhenUnlocked` declaration; a code-grounded\nconfirmation of the effective accessibility attribute would raise it to\nhigh confidence.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.Shared.API.ServerManagerPersistence.ServerManagerKeychain:L6-L35@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "func set(_ value: Data, key: String) ... ignoringAttributeSynchronizable: true"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Set kSecAttrAccessibleWhenUnlockedThisDeviceOnly on the token Keychain items.",
        "detail": "In `ServerManagerKeychain` (cev-e5000002), set the Keychain\naccessibility on the access/refresh-token items to\n`kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (or\n`…WhenPasscodeSetThisDeviceOnly` where a passcode requirement is\nacceptable) so the items are non-migratable across devices and excluded\nfrom device backups. This is the iOS analog of the Android Room\nrecommendation (conf-androidr) and uses the same KeychainAccess API the\nclass already calls.\n",
        "references": [
          "external: OWASP MASTG MASVS-STORAGE-1 (Keychain accessibility)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-28",
          "SC-28(1)",
          "MP-5"
        ],
        "attack": [
          "T1634"
        ],
        "cwe": [
          "CWE-312"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-STORAGE-1"
        ],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Effective kSecAttrAccessible attribute on the token Keychain items (confirm WhenUnlocked vs WhenUnlockedThisDeviceOnly)"
      ]
    },
    {
      "id": "conf-ef49b4b0",
      "title": "GET /api/config returns instance latitude/longitude, config_dir and whitelist_external_dirs in cleartext to any bearer holder",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The /api/config response exposes precise instance geolocation, the on-disk config directory, and the external-directory allowlist to any authenticated token holder regardless of scope, with no per-data-element access scoping on these high-sensitivity properties.",
      "detail": "`GET /api/config` (api/rest.md lines 110-128) returns `latitude`,\n`longitude`, `elevation`, `config_dir`, and `whitelist_external_dirs` in\ncleartext. Unlike entity-state reads — which the code DOES scope per-entity\nvia `APIEntityStateView.get` -> `check_entity(entity_id, POLICY_READ)`\n(cev-a1000011) — `/api/config` applies no per-property access scoping: any\nvalid bearer (including a low-privilege user or a non-owner Long-Lived\nAccess Token) reads the precise home location and internal filesystem\nlayout.\n\nThis is an excessive-property-exposure / minimum-necessary failure at\ndata-element granularity: the instance's precise latitude/longitude is the\nsingle most sensitive privacy datum in the system (it geolocates the home\nitself), and `config_dir` / `whitelist_external_dirs` disclose internal\npaths useful for the path-traversal / file-serving surface. A scope that\nreturns aggregate config (units, version) to all holders but reserves\nprecise coordinates and filesystem paths to admins would be\nminimum-necessary; the current response is not.\n\nMedium severity under the *api-security* rubric — it matches the\n\"excessive property exposure\" pattern (OWASP API3 / BOPLA read-side) but\nis bounded: the exposure requires a valid token (not unauthenticated), the\ndata set is single-instance (not bulk multi-subject), and the coordinates\nare coarse-home-location rather than per-person tracking. It escalates if\ncombined with a low-privilege token issuance path. The path-disclosure\nfacet feeding path traversal routes to Integrity.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "api/rest.md",
          "locator": "GET /api/config response, lines 111-128",
          "excerpt": "\"config_dir\":\"/home/ha/.homeassistant\", ... \"latitude\":45.8781529, ... \"longitude\":8.458853651"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APIEntityStateView.get:L242-L255@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "if not user.permissions.check_entity(entity_id, POLICY_READ): raise Unauthorized(entity_id=entity_id)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Scope precise location and filesystem paths in /api/config to admin/owner, returning coarse or omitted values to non-admin holders.",
        "detail": "Apply the same per-caller scoping that entity reads already enforce\n(cev-a1000011) to the `/api/config` response: gate `latitude`,\n`longitude`, `config_dir`, and `whitelist_external_dirs` behind\n`user.is_admin` (or a dedicated POLICY), and return either coarse\nlocation (zone name only) or omit the precise coordinates for\nnon-admin/non-owner bearers. This converts the endpoint to a\nminimum-necessary response without breaking the units/version/components\nfields the frontend relies on.\n",
        "references": [
          "external: OWASP API Security Top 10 API3:2023 (BOPLA)"
        ]
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-6",
          "AC-6(1)",
          "SI-15",
          "AC-4"
        ],
        "attack": [
          "T1213"
        ],
        "cwe": [
          "CWE-200"
        ],
        "owasp_api": [
          "API3:2023"
        ],
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
      "id": "intg-2b80f92e",
      "title": "mobile_app webhook rejects invalid plaintext JSON but documents no validation error for invalid encrypted JSON",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "low",
      "confidence": "medium",
      "disposition": "risk",
      "summary": "The webhook contract returns 400 for invalid plaintext JSON but explicitly does not for invalid encrypted JSON, leaving malformed decrypted payloads without a defined reject-on-fail / dead-letter behavior.",
      "detail": "The documented webhook data-quality contract (sending-data.md) states a 400 is\nreturned \"if your JSON is invalid. However, you will not receive this error if the\nencrypted JSON is invalid.\" This is an input-validation/data-quality asymmetry on\nthe write path: the plaintext branch has a defined reject-on-fail (400), but the\nencrypted branch's behavior on a malformed decrypted payload is undefined in the\ncontract — there is no documented reject, quarantine, or dead-letter outcome, so a\nmalformed-after-decrypt message may be silently dropped or partially processed.\nThe typed field constraints documented for messages such as update_location\n(gps_accuracy \"Must be greater than 0\", etc.) further imply per-field validation\nwhose enforcement on the encrypted branch is unspecified.\n\nThis is the data-quality-contract facet (defined behavior for malformed input at\nan ingestion point). Severity is low under the *api-security* rubric clause\n\"Documentation deficiency / OpenAPI specification drift from implemented behavior\nin non-security-critical surfaces\" — the asymmetry is primarily a contract/\nobservability gap rather than a direct exploit — but it is recorded because the\nencrypted branch is the one carrying location PII. Confidence is medium because\nthe asymmetry is documented but the actual server-side handling of a malformed\ndecrypted body is not enumerated in the code-evidence-index.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "api/native-app/sending-data.md",
          "locator": "#response, line 88",
          "excerpt": "You will receive a 400 status code if your JSON is invalid. However, you will not receive this error if the encrypted JSON is invalid."
        },
        {
          "artifact": "api/native-app/sending-data.md",
          "locator": "#update-device-location, gps_accuracy row",
          "excerpt": "GPS accuracy in meters. Must be greater than 0."
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Define and document a reject-on-fail outcome for malformed decrypted webhook payloads symmetric with the plaintext 400.",
        "detail": "Extend the webhook data-quality contract so a payload that decrypts to invalid\nJSON or fails per-field validation returns a defined error (or is dead-lettered\nwith a logged, monitorable outcome) symmetric with the plaintext 400 path\ndocumented in sending-data.md, rather than being silently dropped. This gives\nthe location-PII-carrying encrypted branch the same reject-on-fail data-quality\nguarantee as the plaintext branch.\n",
        "references": [
          "internal: api/native-app/sending-data.md #response"
        ]
      },
      "mappings": {
        "nist": [
          "SI-10"
        ],
        "attack": [],
        "cwe": [
          "CWE-20"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Server-side handling of a malformed-after-decrypt webhook body (reject / quarantine / dead-letter behavior) — not enumerated in code-evidence-index.yaml"
      ]
    },
    {
      "id": "intg-8b158cfe",
      "title": "Core integrations consume untrusted device/cloud responses with no central response validation while running unsandboxed at Core's full privilege",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "Integration responses and forged inbound webhooks from untrusted devices/clouds are trusted per-integration with no central schema/response validation, and a single integration's tampering reaches all Core state because integrations are unsandboxed.",
      "detail": "The context brief and trust-boundary map state that Core integrations consume\nresponses from untrusted devices/clouds and forged inbound webhooks\n(compromised_third_party_integration; API10 unsafe consumption), and that response/\nendpoint authenticity is \"per-integration (not centrally enforced).\" The system\noverview is explicit that integrations are NOT sandboxed from each other and run\nwith Core's full privilege, so a single integration that ingests a malicious\nresponse tampers with all Core state, the permission engine, and .storage with no\nin-process integrity boundary (the threat model records this as tm-d98660ae /\ntm-e185c6a7, Tampering). There is no central response-validation or schema-\nenforcement layer at the Core<->external-device boundary (asset-inventory\nboundary tb-6a2d8c14).\n\nThis is the unsafe-consumption / inbound-integrity facet (validate-before-act on\nuntrusted upstream responses), distinct from the SSRF/outbound concern. Severity\nis high under the *api-security* rubric: it matches \"Unsafe consumption of\nthird-party APIs without response validation (OWASP API10)\" (which the rubric bands\nmedium) but escalates to high here because the *amplifier* — no inter-integration\nisolation, full Core privilege — turns a single trusted-but-wrong response into\ntampering of the entire Core state machine (the rubric's \"do not average\" rule\ntakes the higher band driven by the unsandboxed-privilege multiplier). Confidence\nis medium: the unsandboxed-privilege design is high-confidence (overview lines\n20-22), but per-vendor response-validation behavior is modeled at the aggregate\nlevel and not enumerated per integration in the code-evidence-index.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#what-home-assistant-is, lines 20-22 (trust posture)",
          "excerpt": "integrations are not sandboxed from each other and run with Core's full privilege"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APITemplateView.post:L479-L505@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "@require_admin async def post ... tpl = _cached_template(data[\"template\"], ...); tpl.async_render(...)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Introduce a central inbound-response validation contract at the integration boundary and constrain integration privilege.",
        "detail": "Provide a shared, framework-level response-validation helper at the\nCore<->external-device boundary (tb-6a2d8c14) that integrations use to validate\nuntrusted device/cloud responses against a typed schema with reject-on-fail\nbefore the response mutates Core state, rather than each integration trusting\nthe remote schema (API10). Because the unsandboxed full-privilege model means a\nsingle bad response tampers all Core state, pair the validation contract with the\nlonger-term integration-isolation direction (process/capability sandboxing) so\nthe blast radius of one misbehaving integration is bounded. The admin-gated\n/api/template render (cev-a1000013) is a related server-side-template sink that\nshould not be reachable from integration-controlled input.\n",
        "references": [
          "internal: 00-SYSTEM-OVERVIEW.md #trust-boundaries item 6"
        ]
      },
      "mappings": {
        "nist": [
          "SI-10",
          "SI-15",
          "SC-7",
          "AC-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-20",
          "CWE-345"
        ],
        "owasp_api": [
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Per-integration inbound-response validation behavior (schema enforcement / response allowlisting) for the high-traffic integration classes — not enumerated per integration in code-evidence-index.yaml"
      ]
    },
    {
      "id": "dist-66e3e208",
      "title": "Single-host single-process Core is a platform-wide single point of failure with no replication or multi-node topology",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "HA Core, the auth subsystem, the Recorder DB, Supervisor, and os-agent all run in one process or one host with no clustering, no replication, and no second failure domain, so host loss takes the entire automation platform offline.",
      "detail": "Home Assistant is, by design, a single Python asyncio Core process on a\nsingle host. The system overview states verbatim that \"A single trusted\nPython Core process exposes a local-first REST + WebSocket API, runs 2,000+\nin-process integrations ... and persists automation state and history,\" and\nthat \"Core is a single, highly-privileged trust domain.\" The threat model\nrecords this as a single point of failure (tm-296e2800): \"Core is a single\nasyncio process on a single host by design (no clustering claim) ...\nexhausting the event loop, the recorder DB, or the host crashes the whole\nautomation platform including locks/alarms.\" All of the load-bearing\ncomponents co-reside in this one failure domain: the auth subsystem is\nin-process with Core (tm-6fab88e3), the Recorder history DB shares the same\nhost (tm-60f1d9cf), and the Supervisor + add-on/plugin containers + os-agent\nsit on the same host.\n\nThis is the topology root cause behind several Availability findings. There\nis no second node, no multi-AZ placement, no multi-region posture, no\nprimary/replica or quorum replication of state, and no horizontal scaling.\nThe only \"copy\" of the system is the Supervisor backup archive (a recovery\nartifact, not a live replica), and a host loss or the os-agent\nScheduleWipeDevice path (cev-c3000002) destroys the single live instance with\nno automatic failover. The deployment-topology section (overview lines\n108-116) enumerates four install methods (OS, Supervised, Container, Core)\nbut all four are single-instance; none introduces a clustered or replicated\nmode.\n\nThis finding is strictly the TOPOLOGY fact (one failure domain, no\nreplication). The uptime/SLO consequence is routed to Availability\n(avail-754cfc01) and the failure-on-component-loss behavior (degrade,\nrestart, recovery) to Resilient. Severity is high under the *api-security*\nrubric distributed common-pattern \"Single-AZ deployment of the authentication\nservice, session store, or payment service\" calibrated to high: here the\nsingle host is the failure domain for the entire platform including the\nin-process authentication service, so a host incident produces total\nauthentication and automation outage. It does not rise to critical in this\nlens because the harm is availability/topology, not a confidentiality or\nauthentication-bypass impact; HA is also an owner-operated self-hosted\nproduct with no contractual multi-node commitment in the artifacts.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#what-home-assistant-is, lines 12-22",
          "excerpt": "A single trusted Python Core process ... Core is a single, highly-privileged trust domain"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "Recorder DB session for entity-state history"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document the single-host SPOF as an explicit architectural constraint and define the failure domain in the hardening baseline.",
        "detail": "State explicitly in the hardening guidance (org/SECURITY.md is currently a\n6-line pointer) that the supported topologies (overview lines 108-116) are\nall single-instance: there is no Core clustering, no state replication, and\nno automated failover, so the host is the platform's single failure domain.\nWhere higher availability of the consequential alarm/lock path is required,\nname the compensating pattern operators must supply out of band (a\nwarm-standby host restored from a recent Supervisor backup with a defined\nRTO/RPO, or LAN-local device-side automations that survive a Core outage),\nrather than implying a resilience the single-host topology does not provide.\nCoordinate the SLO half with the Availability lens and the failover-behavior\nhalf with the Resilient lens.\n",
        "references": [
          "internal: 00-context/context-brief.md §6 (No SLO/RTO/RPO; HA is single-Core single-host by design)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-36",
          "SC-36(1)",
          "CP-7",
          "CP-7(1)",
          "SC-7(21)"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
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
      "id": "dist-69bbaf5c",
      "title": "No replication topology for the Recorder DB or .storage; the single live copy of all state and secrets has no replica",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The Recorder history DB and the .storage estate (auth, tokens, integration secrets) exist as a single live copy on the one host with no primary/replica, quorum, or cross-node replication; the Supervisor backup archive is the only redundant copy and is a recovery artifact, not a live replica.",
      "detail": "Home Assistant persists two state estates: the Recorder history DB\n(SQLite/MariaDB/PostgreSQL per ADR-0018, default SQLite) and the .storage\nconfig directory holding auth records, refresh tokens, jwt_keys, and\nintegration OAuth secrets, all written as plaintext JSON (cev-a1000017). The\nartifacts specify no replication topology for either: there is no\nprimary/replica configuration, no multi-primary or quorum scheme, and no\ncross-node or cross-AZ replication. ADR-0018 constrains the supported DB\nengines but says nothing about replicating the recorder; the recommended\ndefault is the built-in SQLite, which is an in-host file with no replication\nprimitive at all. The only redundant copy of this state is the Supervisor\nbackup archive (cev-b2000006), which is a point-in-time recovery artifact —\nasynchronous, manually or schedule-triggered, and not a live replica that\ncan take over on host loss.\n\nThe Distributed concern is data locality and replication topology: a single\nlive copy of the entire state-and-secret estate, bound to one host, with no\nreplica. Combined with the single-host SPOF (dist-0a1b2c3d), this means a\nstorage-substrate loss (disk failure, the ScheduleWipeDevice path\ncev-c3000002, or host loss) loses the only live copy with no replicated\nfallback. The recovery-objective and restore-verification facet of the backup\nis routed to Availability (avail-5af6fee5); the at-rest-encryption facet to\nConfidentiality; the immutability/retention facet to Immutability. Here the\nconcern is strictly the absence of a replication topology for the live state.\n\nSeverity is medium under the *api-security* rubric distributed\ncommon-patterns (the \"single AZ / single failure domain for state\" family,\ncalibrated below the auth-service-outage high because a recovery path —\nbackup — does exist even though no live replica does). It is not high because\nthe data is recoverable from backup; it is not low because the loss window\nbetween backups is the full RPO and there is no replicated copy to bound it.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "architecture/adr/0018-supported-databases.md",
          "locator": "#decision, lines 36-54",
          "excerpt": "The recommendation is to use the built-in SQLite database when possible."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.storage.Store._write_prepared_data:L602-L618@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "ALL .storage ... written as PLAINTEXT UTF-8 JSON"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document that recorder/.storage state has no live replica and name the replication option for higher-durability deployments.",
        "detail": "State in the hardening baseline that the default topology keeps a single\nlive copy of the Recorder DB and the .storage estate (cev-a1000017) with no\nreplication, and that the Supervisor backup (cev-b2000006) is the only\nredundancy — a point-in-time recovery artifact, not a live replica. For\ndeployments needing higher durability, name the available option (point the\nrecorder at an external MariaDB/PostgreSQL per ADR-0018 with engine-level\nreplication, so at least the history estate has a replicated copy) and note\nthat .storage/auth and integration secrets still travel only with the\nbackup. Coordinate the RTO/RPO half with Availability and the\nbackup-encryption half with Confidentiality.\n",
        "references": [
          "internal: 00-context/asset-inventory.yaml (asset-a5e2c738 recorder DB; asset-1f6a8c40 backup archive)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-36",
          "SC-36(1)",
          "CP-9",
          "CP-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
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
      "id": "dist-a0ea311c",
      "title": "DNS resolution topology (plugin-dns CoreDNS) as a potential single dependency for the HA network is undocumented",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "low",
      "confidence": "low",
      "disposition": "blocked",
      "summary": "The HAOS topology routes the HA network's DNS through a single CoreDNS plugin container, but the artifacts do not document its redundancy, fallback resolver, or failure behavior, so whether DNS is a hidden single dependency cannot be assessed.",
      "detail": "The run config and overview name a plugin-dns CoreDNS plugin container that\nprovides \"DNS for the HA network\" (overview line 38, run-config line 31),\nmaking it a plausible hidden single dependency: integrations, add-ons, and\nCore's outbound calls to devices/clouds (the SSRF/outbound surface,\ntb-6a2d8c14) likely resolve names through this one plugin. A single DNS plane\nis a classic hidden SPOF — if it is the only resolver and it fails, name\nresolution for every integration and update path fails even though the rest\nof the host is healthy.\n\nHowever, none of the supplied artifacts document the CoreDNS plugin's\ntopology: whether it forwards to redundant upstream resolvers, whether Core\nor add-ons have a fallback resolver if the plugin is down, or how a DNS-plane\nfailure propagates. The plugin-dns repo is dependency-role and was not\ndeep-read into the input set, and the code-evidence index contains no\nplugin-dns entry. Per the block-on-ambiguity discipline I do not infer the\nDNS plane is a single point of failure from its mere presence — its\nredundancy posture is unknown. This is recorded as blocked with the\nprerequisite evidence named.\n\nSeverity is low and confidence low because the topology is unknown; the\nfinding would calibrate higher only if the DNS plane is confirmed to be a\nsingle non-redundant resolver with no fallback (the *api-security* rubric\ndistributed single-dependency pattern), which the artifacts do not establish.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#repository-map, line 38 (plugin-dns row)",
          "excerpt": "CoreDNS plugin container (DNS for the HA network)"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Document the CoreDNS plugin's redundancy and fallback-resolver behavior to confirm whether DNS is a single dependency.",
        "detail": "Provide the plugin-dns CoreDNS topology: the upstream resolvers it forwards\nto, whether those are redundant, and what Core and add-ons do for name\nresolution if the plugin container is unavailable. This resolves whether the\nDNS plane is a hidden single dependency for the integration-outbound\n(tb-6a2d8c14), add-on, and update paths, or whether a fallback resolver\nbounds that failure. Until documented, operators cannot reason about\nDNS-plane redundancy on the appliance topology.\n",
        "references": [
          "internal: .apd-run.yaml (plugin-dns: CoreDNS plugin container — LAN discovery / DNS plane)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-22",
          "SC-20",
          "SC-36"
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
      "prerequisite_evidence": [
        "plugin-dns CoreDNS topology: upstream resolver redundancy and forwarding configuration",
        "Whether Core and add-ons have a fallback resolver if the CoreDNS plugin is unavailable",
        "How a DNS-plane failure propagates to integration outbound, add-on, and update paths"
      ]
    },
    {
      "id": "dist-b98dc00a",
      "title": "2000+ integrations share Core's single process and event loop with no failure-domain isolation, preventing fault containment or horizontal scale",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Every integration runs in-process at Core's full privilege on the one asyncio event loop with no isolation boundary, so the integration tier cannot be scaled out, partitioned, or fault-contained — one integration's failure is the whole platform's failure domain.",
      "detail": "The integration tier is the largest moving part of Core, and it is entirely\nco-located inside the single Core process. The overview states \"integrations\nare not sandboxed from each other and run with Core's full privilege,\" and\nthe threat model records that integrations \"share Core's single event loop\nwith no per-integration resource quota\" (tm-35a0b188) and that there is \"no\nin-process integrity boundary protecting Core's state machine from a single\nmisbehaving integration\" (tm-d98660ae). From the Distributed lens this is an\nin-process-state / no-failure-domain-boundary topology problem: because the\n2000+ integrations and Core's own state machine occupy one process and one\nevent loop, the integration tier has no failure domain of its own. It cannot\nbe partitioned across processes or hosts, cannot be horizontally scaled\nindependently of Core, and a fault in any one integration is not contained —\nit shares the single failure domain with the auth subsystem, the API\nsurface, and the recorder write path (cev-a1000018).\n\nThis is distinct from the Availability finding on the missing per-integration\nresource quota (avail-235dacf0, which owns the capacity-ceiling facet) and\nfrom the Integrity findings on the absent inter-integration trust boundary\n(tm-e185c6a7). The topology fact owned here is that the design provides no\nprocess/host boundary along which the integration tier could be isolated into\nits own failure domain — the standard distributed remedy (run untrusted or\nhigh-fan-out workers in a separate, independently-restartable process or\ncontainer) is structurally absent.\n\nSeverity is high under the *api-security* rubric distributed common-pattern\n\"In-process state in the application tier preventing horizontal scale\"\n(calibrated medium-to-high \"depending on what's in-process\"); here what is\nin-process is the entire 2000+-integration tier plus Core's authorization\nstate, so the upper bound of that band applies. The blast radius of the\nmissing isolation is the whole single failure domain. The behavior a healthy\ndesign would add around an integration (timeout, bulkhead, circuit-break) is\nrouted to Resilient; the capacity ceiling to Availability; here the concern\nis strictly the absence of a failure-domain boundary for the integration\ntier.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#what-home-assistant-is, lines 20-22",
          "excerpt": "integrations are not sandboxed from each other and run with Core's full privilege"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "Recorder DB session for entity-state history"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Provide a failure-domain boundary for the integration tier (out-of-process or per-integration worker isolation) so one integration is not the whole platform's failure domain.",
        "detail": "Introduce a topology boundary that lets high-fan-out, untrusted, or\nblocking integrations run in a separate, independently-restartable failure\ndomain (a worker process or sidecar container) rather than on Core's single\nevent loop alongside the auth subsystem and recorder write path\n(cev-a1000018). This is the topology complement to the Availability lens's\nper-integration resource quota and the Resilient lens's timeout/bulkhead\nwork — isolate the tier into its own failure domain so a fault in one\nintegration can be contained and restarted without taking Core down. Do not\nduplicate the quota or bulkhead recommendations; this one is specifically\nabout creating the process/host boundary they would then be applied across.\n",
        "references": [
          "internal: 00-context/context-brief.md §8 (integrations run unsandboxed in one process)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-36",
          "SC-7(21)",
          "SC-7(5)",
          "SC-6"
        ],
        "attack": [],
        "cwe": [
          "CWE-1189"
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
      "id": "dist-d08ed969",
      "title": "Control plane (Supervisor/os-agent) and data plane (Core) share one host and one failure domain",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The Supervisor control plane that manages Core's lifecycle, and the os-agent host bridge, are co-resident host-root processes on the same host as the Core data plane, so a control-plane fault or host incident takes the data plane with it and there is no out-of-band management domain.",
      "detail": "A resilient distributed design separates the control plane (which manages,\nschedules, restarts, and recovers workloads) from the data plane (which\nserves traffic) so that one can survive and act on the other's failure. Home\nAssistant co-locates them: the Supervisor manages the Core container,\nbackups, and add-on lifecycle (overview line 34) and binds the Docker socket\n(cev-b2000003), and os-agent exposes host operations over D-Bus\n(cev-c3000001/2) — all on the same host as the Core data plane. There is no\nseparate management host or out-of-band control domain. The cross-repo edges\nconfirm the tight coupling: Supervisor mints and holds a Core access token\nand calls Core as a privileged client (cev-0a000002), and Supervisor drives\nthe host Docker daemon and os-agent over local sockets/D-Bus\n(cev-0a000003/cev-0a000004).\n\nThe Distributed consequence is a shared failure domain across the\ncontrol/data-plane boundary: a host incident, a host-root compromise, or the\nScheduleWipeDevice path (cev-c3000002) takes down both the workload and the\nplane that would otherwise recover it; conversely the control plane has no\nsurviving peer to fail over to. The management plane cannot act on the data\nplane's failure from outside the failed domain because it is inside it. The\nprivilege-escalation and host-root-blast-radius facets of this co-location\nare owned by the tier-1 Integrity/Authenticity findings (tm-83f43c8e,\ntm-cbe50d76); the topology fact owned here is the absence of any\ncontrol-plane/data-plane failure-domain separation.\n\nSeverity is medium under the *api-security* rubric distributed\ncommon-patterns (single-failure-domain family). It is medium rather than\nhigh because, for the supported single-host topologies (overview lines\n108-116), control/data-plane co-location is the intended appliance model and\nthe dominant security harm (host-root blast radius) is carried by the\ntier-1 trustworthiness findings; the Distributed concern is the topology\nconstraint that no out-of-band recovery domain exists.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#trust-boundaries, lines 88-89",
          "excerpt": "Supervisor controls the Docker socket ... the container-to-host-root boundary"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.docker.manager.DockerAPI.__init__:L271-L279@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "Supervisor binds the Docker socket (/run/docker.sock)"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Document the control-plane/data-plane co-location and name the out-of-band recovery the appliance topology lacks.",
        "detail": "Note in the hardening baseline that the Supervisor control plane and the\nCore data plane share one host and one failure domain, so the management\nplane cannot recover Core from outside a failed/compromised host\n(cev-b2000003, cev-0a000002). For operators who need management-plane\nsurvivability, name the out-of-band recovery pattern they must supply (a\nseparate host that can restore the Supervisor backup, or external\nmonitoring that triggers a rebuild), rather than relying on the in-host\nSupervisor watchdog alone. Coordinate the host-root-blast-radius half with\nthe tier-1 Integrity/Authenticity findings and the watchdog-behavior half\nwith Resilient.\n",
        "references": [
          "internal: 00-context/threat-model-normalized.yaml (tm-83f43c8e, tm-cbe50d76 host-root scope)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-7",
          "SC-7(21)",
          "SC-36",
          "CP-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-1189"
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
      "id": "ephem-053957f3",
      "title": "Device webhook_id is a permanent bearer-less credential with no rotation or expiry that actuates services",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The per-device webhook_id minted at mobile registration is a permanent, unscoped, bearer-less secret with no rotation or expiry; possession alone calls arbitrary services for the life of the registration.",
      "detail": "Mobile registration mints a `webhook_id` via `secrets.token_hex()`\n(`RegistrationsView.post`, cev-a1000014) and the registration docs instruct\nthe client \"You should permanently store this information\"\n(`api/native-app/setup.md` §\"Registering the device\"). The webhook entry\npoint authenticates purely on possession of the `webhook_id`\n(`handle_webhook` maps `webhook_id` → config_entry, cev-a1000016 — \"No\nbearer\", and the deleted-id set is the only invalidation path), and a\nholder can drive `webhook_call_service` to call arbitrary services such as\nlocks and alarms (cev-a1000015). The `webhook_id` is opaque and bearer-less\nby design, so it crosses the boundary the OAuth bearer path does not.\n\nEphemeral's concern is that this credential has no lifecycle: it is minted\nonce and is then a permanent secret with no rotation cadence, no expiry, and\nno automatic re-issuance — the only invalidation is the user deleting the\nwhole device registration (the deleted-ids check in cev-a1000016). There is\nno documented webhook_id rotation that a client can perform after suspected\nleakage short of de-registering and re-registering the device. The\nleaked_device_webhook_id attacker position therefore enjoys a credential\nthat, once captured (cloudhook URL exposure, on-device extraction from the\nunencrypted stores conf-205c53a5, log leakage), is replayable for the life\nof the registration with no time bound.\n\nThis is high severity under the *api-security* rubric Ephemeral pattern\n\"Service account tokens or API keys are static long-lived secrets … with\nno rotation\" — the webhook_id is a static long-lived shared secret on a\nconsequential-action path. The authentication-design weakness of the\nwebhook path (bearer-less, no per-entity authz) is already filed under\nIntegrity (intg-5df46115); this finding constrains itself to the missing\nrotation/expiry lifecycle of the credential.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "api/native-app/setup.md",
          "locator": "§'Registering the device', line 71",
          "excerpt": "You should permanently store this information"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.http_api.RegistrationsView.post:L67-L88@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "webhook_id = secrets.token_hex()"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "config_entry = hass.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add webhook_id rotation and optional expiry without forcing device re-registration.",
        "detail": "Add a client-invokable webhook_id rotation action that mints a fresh\n`secrets.token_hex()` (cev-a1000014), atomically swaps it into the\nconfig_entry map consumed by `handle_webhook` (cev-a1000016), and adds\nthe prior id to the deleted-ids set — so a device that suspects its\nwebhook_id leaked can rotate without tearing down and rebuilding the\nwhole registration. Optionally support a registration-level expiry that\nrequires periodic webhook_id refresh for high-sensitivity instances.\nPair this lifetime control with the per-entity write authorization that\nIntegrity recommends on the same path (intg-5df46115).\n",
        "references": [
          "external: NIST SP 800-53r5 IA-5(1) — authenticator management"
        ]
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "AC-2(3)",
          "AC-12"
        ],
        "attack": [
          "T1078"
        ],
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
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-9915ab91",
      "title": "Long-Lived Access Tokens are valid for 10 years with no rotation, the longest-lived static credential in the system",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "User-generated Long-Lived Access Tokens are issued with a 10-year validity, no rotation mechanism, and no per-token risk-tiered expiry, making each one a decade-long static bearer credential to the full Core API.",
      "detail": "`auth_api.md` §\"Long-lived access token\" states verbatim \"Long-lived\naccess tokens are valid for 10 years\" and that the token string \"is not\nsaved in Home Assistant; you must record it in a secure place\". These are\nbacked by a dedicated refresh-token type (`auth_index.md` line 50:\n\"Long-lived Access Token … created internally and never exposed to the\nuser\") that inherits the never-expire refresh-token semantics\n(cev-a1000003). The creation WebSocket command exposes a `lifespan` field\n(`auth_api.md` `\"lifespan\": 365`), but the documented validity of the\nresulting token is 10 years, with no rotation routine and no\nrisk-class-driven shortening for tokens used by third-party integrations\nand webhook-style clients (the stated use case).\n\nEphemeral owns the lifetime facet: a 10-year static bearer credential to a\nPHI-equivalent home-control API (presence, geolocation, lock/alarm\nactuation) is a grant-and-leave credential rather than a grant-as-needed\none. Because the token string is recorded out-of-band by the user\n(\"record it in a secure place\"), it is exactly the leakage-prone class the\nrubric calls out — recoverable from CI logs, config files, scripts, and\nmobile apps — and its decade lifetime means a single leak is exploitable\nfor the credential's full life with no automatic invalidation. The\ncryptographic verifiability of the token and the issuance identity are\nAuthenticity concerns; the at-rest protection is Confidentiality.\n\nThis is high severity under the *api-security* rubric clause \"Service\naccount tokens or API keys are static long-lived secrets … with no\nrotation\" (broad blast radius on credential leak, no automatic\ninvalidation, no detection signal on use of a leaked credential) — a\nLong-Lived Access Token is the api-key-equivalent for HA, and the 10-year\nhorizon is the maximal expression of that clause.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_api.md",
          "locator": "§'Long-lived access token', line 151",
          "excerpt": "Long-lived access tokens are valid for 10 years"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "§'Refresh token types', line 50",
          "excerpt": "Long-lived Access Token … created internally and never exposed to the user"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.models.RefreshToken:L104-L121@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "jwt_key: str = attr.ib(factory=lambda: secrets.token_hex(64))"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add a default and maximum lifetime to Long-Lived Access Tokens and a rotation/re-issue workflow.",
        "detail": "Bound the Long-Lived Access Token validity (currently documented as 10\nyears in `auth_api.md`) to a configurable default and hard maximum\n(e.g. default 1 year, surface the `lifespan` already present in the\ncreation command as the authoritative expiry), and add a profile-page\nrotation flow that re-issues and revokes the prior token in one step so\noperators can rotate without losing integration continuity. Record the\ntoken's expiry as a first-class field on its backing internal refresh\ntoken (cev-a1000003) so `async_validate_access_token` (cev-a1000002)\nenforces it. Surface near-expiry warnings so a rotation is not a\nsurprise outage for webhook/integration consumers.\n",
        "references": [
          "external: NIST SP 800-53r5 IA-5(1) — authenticator management, change/refresh"
        ]
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-5(7)",
          "AC-2(3)"
        ],
        "attack": [
          "T1078"
        ],
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
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-9c322627",
      "title": "Add-on images are pinned to a mutable floating base tag (:trixie) rather than an immutable digest",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "risk",
      "summary": "The add-on build pins its base image to the floating :trixie tag while the Core image pins base layers and binaries by sha256 digest, so add-on rebuilds can silently pull a mutated base, undermining immutable-infrastructure guarantees.",
      "detail": "The mosquitto add-on build references its base image by a mutable floating\ntag: `build_from: amd64: ghcr.io/home-assistant/amd64-base-debian:trixie`\n(`infra/addon-mosquitto-build.yaml`), and the add-on manifest declares\n`startup: system` host mounts (`mosquitto/config.yaml`, cev-09000001). By\ncontrast the Core image pins its base/buildkit and the go2rtc binary by\nimmutable sha256 digest (`infra/core-Dockerfile` lines 1, 29:\n`docker/dockerfile@sha256:…`, `go2rtc:1.9.14@sha256:…`), demonstrating the\nproject knows the digest-pinning pattern. The add-on path does not follow\nit, so a rebuild of the add-on against `:trixie` resolves to whatever the\ntag points at that day.\n\nEphemeral's immutable-infrastructure lens asks whether infrastructure is\ndeploy-replace against a fixed, reproducible artifact. A floating base tag\nmeans the add-on's deployed bytes are not reproducible across rebuilds: the\nsame add-on version can carry different base-layer contents over time, which\nis the mutable-infrastructure / configuration-drift failure mode the lens\nflags. The signature/provenance of the image (Cosign signing per\n`mobile/supervisor-apps-security.md`) and whether signatures are verified at\ninstall are Authenticity concerns; the Ephemeral concern is strictly the\nmutable-tag → non-reproducible-rebuild facet.\n\nThis is medium severity under the *api-security* rubric Ephemeral pattern\n\"Container images mutable in production — `:latest` tags … carrying\nproduction state\" (severity medium to high depending on what's mutable):\nhere the mutable tag is a base image rather than the application layer and\nthe Core image is digest-pinned, so the blast radius is bounded — hence\nmedium.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "infra/addon-mosquitto-build.yaml",
          "locator": "lines 2-4, build_from amd64",
          "excerpt": "amd64: ghcr.io/home-assistant/amd64-base-debian:trixie"
        },
        {
          "artifact": "infra/core-Dockerfile",
          "locator": "line 29, go2rtc COPY --from",
          "excerpt": "go2rtc:1.9.14@sha256:675c318b23c06fd862a61d262240c9a63436b4050d177ffc68a32710d9e05bae"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Pin add-on base images by sha256 digest as the Core image already does.",
        "detail": "Pin the add-on `build_from` base images in\n`infra/addon-mosquitto-build.yaml` (and the broader add-on collection)\nby immutable `@sha256:` digest rather than the floating `:trixie` tag,\nmirroring the digest pinning already used in `infra/core-Dockerfile`\n(line 29) for go2rtc and the dockerfile frontend. Advance the pinned\ndigest through a deliberate, reviewable base-image update so an add-on\nrebuild is reproducible and a base-layer change is an explicit version\nbump rather than an implicit pull. Pair with Authenticity's image-signing\nverification so the pinned digest is also provenance-checked.\n",
        "references": [
          "external: NIST SP 800-53r5 CM-2(2) — baseline configuration, automation support"
        ]
      },
      "mappings": {
        "nist": [
          "CM-2",
          "CM-2(2)",
          "CM-3",
          "SA-15(7)"
        ],
        "attack": [],
        "cwe": [
          "CWE-1357"
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
      "id": "ephem-a879a34b",
      "title": "Owner account holds a standing unconditional all-access grant with no just-in-time elevation for admin operations",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The owner principal is hard-coded to unconditional all-access for the life of the account, with no just-in-time elevation, time-boxed admin grant, or step-up for consequential operations, so the standing grant is always-on.",
      "detail": "The owner created during onboarding \"will always have access to all\npermissions\" (`auth_index.md` §\"Owner\"), and in code `_OwnerPermissions`\nreturns `access_all_entities → True` and an unconditional\n`lambda entity_id, key: True` (cev-a1000008). Admin-gated consequential\noperations — state writes (`APIEntityStateView.post`, admin-or-deny,\ncev-a1000012), server-side template render (`APITemplateView.post`,\n`@require_admin`, cev-a1000013), and the per-role Supervisor surface — are\nreachable on the strength of the standing admin/owner session with no\njust-in-time request/approve/time-box and no step-up re-authentication for\nthe sensitive action.\n\nEphemeral owns the access-lifetime facet here: the question is not whether\nthe owner's identity is verified (Authenticity) but whether the\nhigh-privilege grant is short-lived and requested-as-needed versus\nstanding-and-always-on. HA implements the latter — there is no JIT access\npattern, no time-boxed elevation, and no break-glass-style bounded grant for\nadmin operations on a system that controls physical locks/alarms and holds\nhome-occupancy data. A compromised_admin_session therefore holds the full\nprivilege continuously rather than only during an approved, expiring window.\n\nThis is medium severity under the *api-security* rubric clause \"Hardening\nweakness exploitable only after adjacent compromise\" — the standing grant\nis consequential only once an owner/admin session or token is already\ncompromised (the dominant blast-radius fact noted across tier 1), so its\nindependent severity is medium, weighed up by the PHI-equivalent\nconsequential-action surface and weighed down because JIT elevation is a\ndefense-in-depth control HA does not currently model rather than a missing\nmandatory control. The account-takeover blast radius itself is owned by\nAuthenticity/Confidentiality.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_index.md",
          "locator": "§'Owner', lines 28-29",
          "excerpt": "The owner … will always have access to all permissions"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.permissions._OwnerPermissions:L84-L96@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "def access_all_entities(self, key): return True"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APITemplateView.post:L479-L505@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "@require_admin async def post"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Add an optional just-in-time elevation and step-up for owner/admin consequential operations.",
        "detail": "Consider an optional just-in-time elevation model for the most\nconsequential admin operations (template render cev-a1000013, add-on\ninstall / Supervisor proxy, backup creation): require a step-up\nre-authentication that opens a short, time-boxed elevated window rather\nthan relying on the standing owner/admin session that `_OwnerPermissions`\n(cev-a1000008) grants for the account's whole life. This bounds the\nwindow in which a compromised_admin_session can exercise the standing\ngrant. Frame as defense-in-depth — it does not replace the existing admin\ngate, it time-bounds it.\n",
        "references": [
          "external: NIST SP 800-53r5 AC-6(5) — privileged accounts, limited use"
        ]
      },
      "mappings": {
        "nist": [
          "AC-2",
          "AC-2(2)",
          "AC-6",
          "AC-6(5)"
        ],
        "attack": [],
        "cwe": [
          "CWE-269"
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
      "id": "ephem-db8641be",
      "title": "Web/portal session absolute lifetime, idle timeout, and behavior on credential change are unspecified",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "low",
      "disposition": "blocked",
      "summary": "Beyond the documented 1800s access-token TTL and the never-expiring refresh token, the artifacts do not specify a maximum portal session lifetime, idle timeout, or session-invalidation behavior on password or MFA change, so session-lifetime policy cannot be fully assessed.",
      "detail": "The token primitives are partly specified — access tokens expire in 1800s\n(`auth_api.md` `expires_in: 1800`), refresh tokens never expire\n(ephem-0a000001), and the WS handshake registers a revoke callback that\ndrops the socket on token revocation (`AuthPhase.async_handle`,\ncev-a1000010). What is NOT specified is the session-management policy as a\nwhole: there is no documented maximum absolute session lifetime for the\nfrontend/portal session, no idle timeout, and no stated behavior on\ncredential change (does changing the password or MFA enrollment revoke all\nexisting refresh tokens / sessions, or do they survive?). The\n`auth_permissions.md` and `auth_index.md` docs cover the token model but not\na session policy.\n\nPer the Ephemeral common pattern \"Session lifetime unspecified — no maximum\nabsolute lifetime, no idle timeout, no behavior on credential change\", the\ncorrect disposition is blocked rather than asserting a gap: the artifacts\nare silent, and the WS revoke callback shows some session-termination\nmachinery exists. The session-lifetime policy is material because the\nnever-expiring refresh token (ephem-0a000001) means that, absent a\nrevoke-on-password-change rule, a password reset after a suspected\ncompromise may not actually log the attacker out.\n\nSeverity is provisionally medium pending the evidence. No rubric clause is\ncited because this is blocked; the governing pattern once resolved would be\nthe api-security session-management clause.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_api.md",
          "locator": "§'Authorization code', lines 86-95",
          "excerpt": "\"expires_in\": 1800"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.websocket_api.auth.AuthPhase.async_handle:L85-L123@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "async_register_revoke_token_callback"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Document and confirm the session-management policy, especially revoke-on-credential-change.",
        "detail": "Confirm from frontend and core code the absolute session lifetime, idle\ntimeout, and — most importantly given the never-expiring refresh token\n(ephem-0a000001) — whether a password or MFA-enrollment change revokes all\nexisting refresh tokens server-side. If credential change does not cascade\nto refresh-token revocation, re-file as a confirmed gap: a post-compromise\npassword reset that leaves the attacker's refresh token alive is the\nload-bearing failure.\n",
        "references": []
      },
      "mappings": {
        "nist": [
          "AC-12",
          "AC-12(1)",
          "IA-5",
          "SC-10"
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
      "prerequisite_evidence": [
        "Frontend/portal session-management policy: maximum absolute lifetime and idle timeout",
        "Behavior on password change and on MFA-enrollment change (revoke all refresh tokens/sessions vs. preserve)",
        "Explicit logout semantics (does logout revoke the backing refresh token server-side)"
      ]
    },
    {
      "id": "ephem-f19f24f9",
      "title": "Home Assistant refresh tokens never expire and are not rotated, valid until manual deletion",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Normal and long-lived refresh tokens have no absolute lifetime, no automatic rotation, and no expiry binding; they remain valid until a user manually deletes them, so a stolen refresh token is replayable indefinitely.",
      "detail": "The authentication model documents verbatim that \"refresh tokens will\nremain valid until a user deletes it\" (`auth_index.md` line 41), and the\ntoken endpoint mints new access tokens on each refresh-grant exchange with\nno rotation of the refresh token itself (`auth_api.md` §\"Refresh token\":\nthe response is a fresh `access_token` only — the refresh token is reused).\nThe refresh-token record in code is a static `secrets.token_hex(64)`\ncreated once at issuance, with no `expire_at`/rotation field\n(`homeassistant.auth.models.RefreshToken`, cev-a1000003 — \"no key rotation\nobserved\"). `async_validate_access_token` rejects only on refresh-token\nrevocation or an inactive user (cev-a1000002) — there is no time-based\nexpiry of the refresh token.\n\nThis is the lifetime facet only — the at-rest protection of the token\nstore is owned by Confidentiality (the plaintext `.storage` finding\nconf-fdf0fb06 and the on-device stores conf-a30cca33 / conf-205c53a5), and\nthe cryptographic strength / device-binding of the token is owned by\nAuthenticity. The Ephemeral gap is that there is no rotation cadence and no\nabsolute lifetime: a refresh token captured via any of those at-rest paths,\nor via the compromised_user_session_token attacker position, grants the\nholder unbounded access-token minting until and unless the user happens to\nnotice and manually delete it. There is no automatic refresh-token rotation\n(the OAuth2.1 hardening pattern) and therefore no refresh-token-reuse\ndetection signal that would convert a theft into a detectable event.\n\nThis is high severity under the *api-security* rubric clause \"JWT\naccess-token lifetime exceeds 1 hour with no refresh-token rotation and no\nrevocation channel\" — the access-token TTL here is a defensible 1800s\n(`auth_api.md` `expires_in: 1800`), but the refresh token that backs it has\nno rotation and an unbounded lifetime, which the rubric's Ephemeral pattern\n(\"refresh-rotation collapses the window\") treats as the load-bearing gap.\nA manual user-initiated revocation channel does exist (cev-a1000002 and the\n`action=revoke` endpoint), so this is a rotation/expiry gap, not a total\nrevocation gap.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_index.md",
          "locator": "§'Access and refresh tokens', line 41",
          "excerpt": "refresh tokens will remain valid until a user deletes it"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.models.RefreshToken:L104-L121@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "token: str = attr.ib(factory=lambda: secrets.token_hex(64))"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.AuthManager.async_validate_access_token:L654-L682@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "not refresh_token.user.is_active"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Introduce an absolute refresh-token lifetime and refresh-token rotation with reuse detection.",
        "detail": "Augment the `RefreshToken` model (cev-a1000003) with an absolute-expiry\ntimestamp and enforce it in `async_validate_access_token` (cev-a1000002)\nalongside the existing revoke/inactive checks, so a refresh token cannot\noutlive a configurable maximum (e.g. 90 days for Normal tokens). Add\nrefresh-token rotation in the `auth/token` refresh-grant path so each\nrefresh issues a new refresh token and invalidates the prior one, and\ndetect reuse of a retired refresh token as a token-family-revocation\nevent. Keep the existing user-initiated `action=revoke` channel; this\nadds the time-bound and rotation layer the OAuth2.1 hardening pattern\nexpects. The reuse-detection event doubles as a Resilient recovery signal.\n",
        "references": [
          "external: OAuth 2.1 draft §6.1 refresh-token rotation",
          "external: NIST SP 800-53r5 IA-5(13) — hardware token-based authentication / expiration"
        ]
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-5(13)",
          "AC-12"
        ],
        "attack": [
          "T1550"
        ],
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
      "prerequisite_evidence": []
    },
    {
      "id": "resil-93866115",
      "title": "No enumerated failure-mode catalog or declared graceful-degradation modes for the Core automation platform",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "The design enumerates no failure modes (integration unavailable, recorder DB full, push relay down, host loss) with their user-visible effect, and declares no degradation modes (read-only, last-known-good, safe-mode), so failure behavior is implicit and largely fail-by-stall.",
      "detail": "Across the artifacts there is no failure-mode catalog: the design does not\nenumerate the failure modes the platform handles (single integration\nunavailable, dependency degraded-but-responding, recorder DB full/locked,\npush relay down, certificate expiry on a reverse proxy, host loss) nor\nstate, per mode, the intended user-visible effect (hard error, retry-then-\nsucceed, degraded response, queued-for-later). The threat model's\navailability cells repeatedly record the *absence* of the controls that a\ncatalog would drive — \"no documented rate-limit / SLO / capacity model,\"\n\"no stated timeout/circuit-breaker\" (tm-17b14550), \"no per-integration\nresource quota\" (tm-35a0b188) — which together imply the de-facto failure\nmode is \"stall the shared event loop,\" but no mode is named or designed.\n\nEqually, no graceful-degradation modes are declared: there is no documented\nread-only or safe-mode for when the recorder DB or a dependency is\nunavailable, no last-known-good fallback policy, and no user-disclosed\ndegraded-state signaling. The permission engine does fail closed (deny-all\non empty/None policy, cev-a1000006) — recorded as a capability — but that is\none fail-safe point, not a platform degradation strategy.\n\nThe Resilient concern is that without an enumerated failure-mode catalog and\ndeclared degradation modes, every Resilient control (timeouts, breakers,\nbulkheads, backpressure) is added ad hoc rather than driven by a stated\nbehavior contract, and the system's behavior under partial failure is\nunpredictable. Severity is medium under the *api-security* rubric: this is a\ndesign-completeness / predictable-failure gap rather than a single\nexploitable control absence (those are filed separately above), and it\noverlaps the Availability SLO finding (avail-754cfc01) which the synthesizer\nmay merge. Confidence is medium: the absence of a catalog is evident from\nthe artifact set, but a hardening doc out-of-band (org/SECURITY.md is a\n6-line pointer) could carry some of it.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "org/SECURITY.md",
          "locator": "full file (6 lines)",
          "excerpt": "Security-policy pointer; no embedded hardening or failure-mode content"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.permissions.util.compile_policy:L23-L52@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "def apply_policy_deny_all(entity_id, key): return False"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Author a failure-mode catalog with per-mode user-visible effect and declare the platform's graceful-degradation modes (read-only/safe-mode/last-known-good).",
        "detail": "Produce a failure-mode catalog enumerating the failure modes the platform\nhandles — integration unavailable, dependency degraded-but-responding,\nrecorder DB full/locked, push relay down, host loss — and, for each, the\nintended user-visible effect (hard error, retry-then-succeed, degraded\nresponse, queued-for-later). Declare the platform's graceful-degradation\nmodes: a read-only / safe-mode when the recorder DB or a dependency is\nunavailable, a last-known-good entity-state fallback, and user-disclosed\ndegraded-state signaling so operators of safety automations know when the\nplatform is degraded. Capture this in the hardening baseline\n(org/SECURITY.md is currently a 6-line pointer with no such content). This\ncontract is what the per-control findings above (timeouts, breakers,\nbulkheads, backpressure) should be designed against. Coordinate with the\nAvailability SLO finding (avail-754cfc01).\n",
        "references": [
          "internal: 00-context/context-brief.md §6 Evidence Gaps (DR/RTO/RPO + availability targets)"
        ]
      },
      "mappings": {
        "nist": [
          "SI-13",
          "CP-12",
          "SI-17",
          "SC-24"
        ],
        "attack": [],
        "cwe": [
          "CWE-636"
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
      "id": "auth-1787eae1",
      "title": "Android Companion verifies the server with default CA trust plus user-installed CAs and no pinning, so the backend identity is forgeable to a MitM",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The custom TLS factory trusts user-installed CAs with no certificate/public-key pinning, so a MitM with an installed CA impersonates the self-hosted backend.",
      "detail": "The Android Companion's TLSHelper.setupOkHttpClientSSLSocketFactory loads the\nAndroidCAStore into its trust manager (code: L24-L43), which includes USER-installed\nCAs, and performs standard X509 validation with no certificate or public-key (SPKI)\npinning. Because the backend is a user-entered self-hosted instance URL with no fixed\ncertificate, the client cannot verify the SERVER's identity beyond \"some CA in the\ndevice trust store signed this leaf\". An on-path adversary who can get a CA into the\nstore (a user-installed MitM CA, an enterprise/MDM CA, or a compromised public CA —\nthe network_mitm position) presents a certificate the client accepts, impersonating\nthe Home Assistant backend and harvesting the bearer token passed over the channel or\nrewriting responses the WebView/native bridge then trusts.\n\nThis is the server-identity-verification face of Authenticity (verifying who the\nserver is), distinct from the eavesdropping/confidentiality face. Per the\n*mobile-applications* authenticity pattern \"No certificate or public-key pinning on a\nhigh-value channel (MASVS-NETWORK-2)\" this is high: stock-device default TLS still\nholds against the casual on-path case with no installed CA, but the device-trust\nassumption is low for the installed-CA case and the blast radius pivots to backend\nimpersonation and token theft. Pinning a self-hosted, user-chosen server is genuinely\nhard (no fixed cert), so the finding of record is the absent trust-on-first-use pin or\nuser-confirmable certificate identity, not a static pin set.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "KeyStore.getInstance(\"AndroidCAStore\")... builder.sslSocketFactory(..., trustManagers[0] as X509TrustManager)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add trust-on-first-use pinning and exclude user-installed CAs for the configured instance.",
        "detail": "For each configured server, capture the leaf/SPKI on first successful\nconnection and pin it (trust-on-first-use) so a later MitM with a different\ncertificate is rejected and surfaced to the user, and scope the OkHttp trust\nmanager to the system CA store (excluding user-added CAs) for the instance\nchannel unless the user explicitly opted into a custom CA. Report a pin /\ncertificate-identity mismatch to the user as a security event rather than\nsilently proceeding. The eavesdropping face of this same channel is owned by\nthe Confidentiality finding on user-installed-CA trust.\n",
        "references": [
          "external: OWASP MASVS-NETWORK-2 (server-identity verification / pinning)"
        ]
      },
      "mappings": {
        "nist": [
          "SC-8",
          "SC-8(1)",
          "SC-23",
          "IA-9",
          "SC-17"
        ],
        "attack": [
          "T1557"
        ],
        "cwe": [
          "CWE-295"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-NETWORK-2"
        ],
        "maswe": [
          "MASWE-0052"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 4
    },
    {
      "id": "auth-23048c0c",
      "title": "Inter-service calls (Supervisor->Core, CLI->Supervisor, Core->push relay) carry no payload-level signing, relying on bearer/transport identity only",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Cross-service requests are authenticated by bearer token or local socket only, with no per-message workload-identity signature, so a host-root-plane compromise forges any peer.",
      "detail": "Across the ecosystem, service-to-service authenticity rests on bearer tokens and\nlocal sockets, never on a signed payload binding the message to a verified workload\nidentity. Supervisor acts as a privileged Core client: it POSTs {api_url}/auth/token\nand holds a Core access token (code: x0000002), so the host-root control plane can\nmint/forge Core admin requests; the `ha` CLI builds a runtime endpoint URL into the\nSupervisor API with no mutual workload authentication (URLHelper x0000001); Core's\nnotify path calls the external Firebase push relay (x0000006) whose handler\nauthenticates no caller (handleRequest consumes push_token from the body with no\ncaller authn). None of these hops attaches a producer signature a consumer verifies;\nthere is no SPIFFE/SPIRE, no mTLS between Core and Supervisor (the Android mTLS key is\na client->Core control, not an internal-mesh control), and no event-bus message\nsigning.\n\nConsequently a foothold on any one component (the internal_lateral_attacker /\nmalicious_or_compromised_addon positions) cannot be cryptographically distinguished\nfrom a legitimate peer at the next hop. This is high severity under the *api-security*\nrubric clause \"Service-to-service inside the cluster uses shared bearer tokens, not\nmTLS or workload identity\" — lateral-movement amplification with no identity binding on\nthe credential. The token-lifetime/rotation concern routes to Ephemeral; this finding\nis bounded to the absent per-message workload-identity verification.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.homeassistant.api.HomeAssistantAPI._ensure_access_token -> homeassistant.components.api (Core /auth/token):L145-L173@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "CROSS_HTTP_CALLS: Supervisor POSTs {api_url}/auth/token and calls Core's API as a privileged client"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:client.helper.URLHelper:L45-L71@c5f716eb5f62c337c603e144f23cd74ac25da98e",
          "excerpt": "base := viper.GetString(\"endpoint\") ... uri := fmt.Sprintf(\"%s%s/%s/%s\", scheme, base, section, command)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:functions.handlers.handleRequest:L51-L95@142579dc41ee534f0d60bc390c4661dba051a995",
          "excerpt": "const { push_token: token } = req.body; if (!token) return res.status(403)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add workload identity (mTLS or signed payloads) on the Supervisor<->Core and CLI<->Supervisor hops and authenticate the push-relay caller.",
        "detail": "Introduce a workload-identity layer on the internal hops: mutually\nauthenticate Supervisor<->Core with mTLS using per-component certificates\n(rather than only a bearer token the host-root plane can replay), and require\nthe `ha` CLI to present a verifiable client identity to the Supervisor API\ninstead of a runtime-trusted endpoint. For the Core->push-relay hop, require\nthe relay to authenticate the calling instance (a signed request or\nper-instance credential) so a third party holding a valid-format FCM token\ncannot drive notifications. Where full mTLS is impractical, sign consequential\ninter-service payloads (e.g. with a per-component key) and verify the\nsignature at the consumer.\n",
        "references": [
          "external: NIST SP 800-53r5 IA-9 Service Identification and Authentication",
          "external: SPIFFE/SPIRE workload identity"
        ]
      },
      "mappings": {
        "nist": [
          "IA-9",
          "IA-3",
          "SC-8(1)",
          "SC-23",
          "SC-23(3)"
        ],
        "attack": [
          "T1557"
        ],
        "cwe": [
          "CWE-345"
        ],
        "owasp_api": [
          "API2:2023"
        ],
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
      "id": "auth-3794d338",
      "title": "Companion apps and Core have no hardware device attestation (Play Integrity / App Attest), so the backend has no genuine-client proof",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "No Play Integrity / App Attest / key attestation anywhere; the backend cannot cryptographically verify a request came from a genuine, untampered app on a genuine device.",
      "detail": "The run's crown-jewel enumeration confirms attestation_tokens_and_jwts is ABSENT —\nno Play Integrity, App Attest, DeviceCheck, or SafetyNet exists in either Companion\napp or Core. Code recon corroborates: the Android client's only client-side identity\ncontrols are the mTLS key in the AndroidKeyStore (KeyStoreRepositoryImpl) and the\ncustom TLS factory (TLSHelper), and there is no root/jailbreak/Frida detection\n(rooted_device_attacker_with_frida position). Consequently the backend has no\ncryptographic proof that a request originates from a genuine, untampered Companion\nbuild running on an uncompromised device — a repackaged or emulated client, or a\ndirect API caller replaying extracted tokens, is indistinguishable to Core.\n\nThis is the *verifiable* counterpart to the missing runtime-detection signal (which\nIntegrity owns as advisory). Per the *mobile-applications* authenticity pattern \"No\nhardware attestation (MASVS-RESILIENCE-4)\", severity is high here rather than critical\nbecause the consequential backend writes the client commands (device control via the\nmobile_app webhook / call_service) are additionally guarded by the bearer/permission\nmodel rather than accepted on the bare client assertion alone; it would be critical if\na high-value write were accepted on nothing but a client-side root verdict. Recorded as\nthe structural gap: the backend has no genuine-client proof at all, so every\ndevice-trust argument about the mobile clients is unresolvable.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...data.keychain.KeyStoreRepositoryImpl:L108-L112@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "KeyStore.getInstance(\"AndroidKeyStore\") // hardware-backed key store for mTLS client-cert private key"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "KeyStore.getInstance(\"AndroidCAStore\")... trustManagerFactory.init(androidCaStore)"
        },
        {
          "artifact": "mobile/android-CLAUDE.md",
          "locator": "run-config crown_jewels EXCLUDED note (attestation_tokens_and_jwts absent)",
          "excerpt": "no Play Integrity / App Attest / DeviceCheck / SafetyNet anywhere"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Request and server-verify a fresh hardware attestation verdict and bind it to high-value actions.",
        "detail": "Add Play Integrity (Android) and DCAppAttest / App Attest (iOS) to the\nCompanion apps, request a fresh nonce-bound verdict at session establishment\nand before consequential device-control actions, and verify the\nGoogle/Apple-signed verdict plus key-attestation chain SERVER-SIDE in the\nmobile_app integration before honoring webhook_call_service / state writes —\nbinding the verdict to the issued session or per-action step-up rather than\nlogging it. Because self-hosted instances vary, gate this as an opt-in\nhardening tier for users who expose Core to the internet. This is the\nverifiable floor that makes the absent root/Frida heuristics moot.\n",
        "references": [
          "external: OWASP MASVS-RESILIENCE-4 (hardware-backed attestation)",
          "external: Google Play Integrity API / Apple App Attest"
        ]
      },
      "mappings": {
        "nist": [
          "IA-9",
          "SI-7",
          "SI-7(6)",
          "SC-23",
          "RA-3"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-RESILIENCE-4"
        ],
        "maswe": [
          "MASWE-0099"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 6
    },
    {
      "id": "auth-3dbf15e7",
      "title": "IndieAuth authorization-code flow on the mobile public client omits PKCE, so an intercepted code redeems for tokens",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The token endpoint binds the authorization code only to a public client_id (the redirect URL) with no PKCE code_verifier, so a code intercepted at a custom-scheme redirect is redeemable.",
      "detail": "Home Assistant's auth flow is OAuth2 + the IndieAuth extension where the client_id IS\nthe application's website URL and the redirect must share its host (auth_api.md). A\nnative app whitelists a custom-scheme redirect such as hass://auth via a link tag. The\ntoken endpoint requires only that the authorization_code request carry \"the exact same\nclient_id\" used at authorize — there is NO PKCE code_challenge / code_verifier in the\ndocumented flow (auth_api.md authorize + token sections show client_id and code only).\nA mobile app is an OAuth public client holding no confidential secret (the run-config\nconfirms client_id IS the redirect URL, no client secret), so without PKCE the only\nthing binding the authorization code to the requesting app is a PUBLIC client_id that\nany party can replay.\n\nAn authorization code delivered to a hijackable custom-scheme redirect (a co-resident\napp registering the same scheme, or the phishing_deep_link_or_ipc_caller position) can\ntherefore be intercepted and exchanged for an access+refresh token by an attacker who\nreplays the same public client_id — no device-rooting required. Per the\n*mobile-applications* authenticity pattern \"OAuth public client performs authorization\nwithout PKCE (MASVS-AUTH-1)\" this is high: code interception by a co-resident app or\nduplicate-scheme registration needs no rooted device, and the intercepted refresh token\nis long-lived (Ephemeral owns the lifetime). The OAuth/OIDC protocol decision routes to\nidentity-security; filed here as the mobile-origin authenticity gap.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_api.md",
          "locator": "#token / Authorization code, lines 72-82",
          "excerpt": "grant_type=authorization_code& code=12345& client_id=https%3A%2F%2Fhass-auth-demo.glitch.me"
        },
        {
          "artifact": "auth/auth_api.md",
          "locator": "#clients, lines 14-23 (client_id is the website; custom-scheme redirect)",
          "excerpt": "The client ID you need to use is the website of your application ... <link rel='redirect_uri' href='hass://auth'>"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Require PKCE (RFC 7636) on the authorization-code flow and prefer domain-verified redirects over custom schemes.",
        "detail": "Add PKCE support to the /auth/authorize and /auth/token endpoints: require a\ncode_challenge (S256) at authorize and a matching code_verifier at token\nexchange, so an intercepted code is unredeemable without the per-flow secret\nheld only by the initiating app. In the Companion apps, prefer a\ndomain-verified Android App Link / iOS Universal Link redirect over the\nhijackable hass:// custom scheme. Because IndieAuth public clients hold no\nsecret, PKCE is the only mechanism that binds the code to the requesting app.\n",
        "references": [
          "external: RFC 7636 Proof Key for Code Exchange",
          "external: OWASP MASVS-AUTH-1"
        ]
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-5",
          "IA-5(2)",
          "IA-8"
        ],
        "attack": [
          "T1528"
        ],
        "cwe": [
          "CWE-287"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-AUTH-1"
        ],
        "maswe": [
          "MASWE-0040"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 7
    },
    {
      "id": "auth-3f2314a4",
      "title": "mobile_app webhook authenticates by possession of a 32-hex webhook_id alone, with no caller identity or signature",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The mobile_app webhook entrypoint accepts a webhook_id as the sole identity proof — no bearer, no per-request signature, no caller authentication.",
      "detail": "The mobile_app webhook path (handle_webhook, code: L172-L180) maps an inbound\nwebhook_id directly to a config_entry; the only authenticator is possession of\nthe 32-hex webhook_id (secrets.token_hex, minted at registration —\nRegistrationsView.post L67-L88). The resulting webhook is bearer-LESS: unlike the\nOAuth bearer path validated by async_validate_access_token, no access token, no\nper-request HMAC, and no caller-identity assertion is required. The optional NaCl\n\"secret\" provides body confidentiality/integrity only if the app enabled\nsupports_encryption; it is not a mandatory request authenticator and the registration\ndoc presents encryption as optional (supports_encryption flag). Through this path\nwebhook_call_service (L269-L292) invokes ARBITRARY services (locks, alarms) under a\nsynthesized registration_context.\n\nThe identity asserting \"I am this registered device\" is therefore unverifiable beyond\na single static bearer-equivalent string. Any holder of a leaked webhook_id or\ncloudhook URL (the leaked_device_webhook_id attacker position) is cryptographically\nindistinguishable from the genuine device. This is high severity under the\n*api-security* rubric clause \"MFA bypass or weak MFA on PII or payment surfaces\" /\n\"Broken Authentication (API2)\" applied to a consequential control surface — a single\npossession factor with no proof-of-holder gates physical-device actuation. The\ndouble-actuation and arbitrary-service concerns route to Integrity; this finding is\nbounded to the unverifiable caller identity.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "config_entry = hass.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.http_api.RegistrationsView.post:L67-L88@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "webhook_id = secrets.token_hex(); ... data[CONF_SECRET] = secrets.token_hex(SecretBox.KEY_SIZE)"
        },
        {
          "artifact": "api/native-app/setup.md",
          "locator": "registration response, lines 73-87 (webhook_id / secret optional)",
          "excerpt": "\"secret\": \"qwerty\", \"webhook_id\": \"abcdefgh\""
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Make the per-request NaCl signature mandatory and bind webhook calls to a verifiable device identity.",
        "detail": "Require the registration-time secret (the NaCl SecretBox key minted in\nRegistrationsView.post) on every webhook request rather than treating\nsupports_encryption as optional, so handle_webhook authenticates a\nper-request MAC/signature over the body and replay-protects it with a nonce,\ninstead of trusting bare possession of the webhook_id. For consequential\nwebhook_call_service actions, additionally bind the device to the issuing\nuser's refresh-token identity so a leaked webhook_id alone cannot actuate\nlocks/alarms. Pair with rate-limiting on the bearer-less entrypoint.\n",
        "references": [
          "external: OWASP API Security Top 10 2023 API2 Broken Authentication"
        ]
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-9",
          "SC-23",
          "IA-3(1)"
        ],
        "attack": [
          "T1078"
        ],
        "cwe": [
          "CWE-306",
          "CWE-345"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 8
    },
    {
      "id": "auth-4e7d1059",
      "title": "Add-on user identity is asserted via unsigned X-Remote-User-* headers the add-on must trust on faith",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "risk",
      "summary": "Ingress conveys the authenticated user to an add-on as plain injected X-Remote-User-* headers with no signature, so the add-on cannot independently verify the asserted identity.",
      "detail": "When an add-on is reached via Supervisor ingress, the authenticated user is conveyed by\nSupervisor injecting X-Remote-User-Id / X-Remote-User-Name / X-Remote-User-Display-Name\nheaders (supervisor-apps-security.md; ingress._init_header code: L320-L349). Supervisor\ndoes strip inbound copies of these headers in the same loop, which prevents a client\nfrom spoofing them THROUGH ingress (a real and credited control — see the corresponding\ncapability). The residual Authenticity gap is that the asserted user identity reaching\nthe add-on is an UNSIGNED plaintext header: the add-on has no cryptographic means to\nverify the identity claim, and the model collapses to \"trust whatever sets these\nheaders\". An add-on placed on the host network, reached by a path that bypasses ingress,\nor a co-resident container able to call the add-on directly, can present forged\nX-Remote-User-* headers the add-on will treat as a genuine identity, because identity\nhere is conveyed by header position, not by a verifiable token.\n\nThis is medium severity under the *api-security* rubric clause \"Defense-in-depth gap\nwhere a single compensating control is the only barrier\" — the inbound-strip is the only\nthing standing between the header-trust model and identity forgery, and it is enforced\nat the ingress hop only. Recorded as the header-trust authenticity weakness, with the\nanti-spoof strip credited as a partial control in the capabilities file.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "mobile/supervisor-apps-security.md",
          "locator": "#authenticating-a-user-when-using-ingress, lines 40-48",
          "excerpt": "the supervisor then adds some headers identifying the user ... X-Remote-User-Id / X-Remote-User-Name"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.api.ingress._init_header:L320-L349@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "headers[HEADER_REMOTE_USER_ID] = session_data.user.id ... for name in request.headers: ... continue"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Convey ingress user identity as a signed, add-on-verifiable token rather than a bare header.",
        "detail": "For add-ons that make authorization decisions on the conveyed identity,\nreplace (or supplement) the plaintext X-Remote-User-* headers with a\nshort-lived signed assertion (e.g. a Supervisor-signed JWT carrying the user\nid/name) the add-on can verify against a Supervisor public key, so the\nidentity is verifiable rather than positional. Continue stripping inbound\ncopies, document that add-ons reached outside ingress must not trust these\nheaders, and keep add-ons off the host network so the ingress strip remains\nthe sole inbound path.\n",
        "references": [
          "external: NIST SP 800-53r5 IA-9 Service Identification and Authentication"
        ]
      },
      "mappings": {
        "nist": [
          "IA-9",
          "SC-23",
          "IA-8",
          "AC-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-290"
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
      "id": "auth-6924f467",
      "title": "os-agent D-Bus host-root methods (AddSSHAuthKey, ScheduleWipeDevice) verify no caller identity before host-root ops",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "os-agent exposes host-root D-Bus methods that perform privileged operations with no cryptographic or platform verification of the calling identity.",
      "detail": "The os-agent Go daemon exposes system D-Bus methods on the io.hass.os interface\nthat perform host-root operations — system.system.AddSSHAuthKey appends an\narbitrary key to root's authorized_keys (code: L57-L75), and\nsystem.system.ScheduleWipeDevice schedules a destructive datadisk/factory wipe\n(L29-L55). Neither method performs any in-method authentication of the D-Bus\ncaller: there is no verification of the caller's bus name, uid, PID, or any\nsigned/attested token proving the caller is the legitimate Supervisor. The\nidentity of the principal invoking a container->host-root bridge is therefore\nunverifiable at the moment of the privileged action — any process able to reach\nthe system D-Bus (a compromised add-on container that has escaped to the\ncontainer->host bridge per the internal_lateral_attacker / malicious_or_\ncompromised_addon positions) is indistinguishable from the genuine Supervisor.\n\nThis is an Authenticity gap (is the claimed identity of the caller verifiable),\ndistinct from the write-path-authorization concern Integrity owns: even a correct\nauthorization policy cannot be enforced when the caller identity it would gate on\nis never established. This is high severity under the *api-security* rubric clause\n\"Authentication bypass to high-privilege functions with no factor required\" — a\nhost-root primitive reachable with no identity factor — escalated to critical\nbecause the affected functions are host-root SSH-key injection and device wipe (the\nsingle most consequential privilege boundary in the system), matching the rubric's\nframing of authentication bypass to high-privilege functions at its sharpest edge.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.AddSSHAuthKey:L57-L75@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "file.WriteString(newKey) ... \"key added for user root\""
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.ScheduleWipeDevice:L29-L55@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "schedule factory-reset / datadisk wipe over D-Bus"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor (D-Bus client) -> system.system.AddSSHAuthKey (os-agent):L57-L75@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "CROSS_CHANNEL: Supervisor calls os-agent host methods over the system D-Bus (io.hass.os)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Authenticate the D-Bus caller in each os-agent host-root method before acting.",
        "detail": "Replace the unauthenticated method dispatch in system/system.go with a\nD-Bus PolicyKit / bus-name + uid check (or an io.hass.os Polkit action\npolicy) so AddSSHAuthKey and ScheduleWipeDevice verify the caller is the\nSupervisor service identity before performing the host-root operation.\nBind the privileged interface to a dedicated system bus name restricted by\na D-Bus policy file that grants the methods only to the Supervisor's uid,\nand reject calls whose caller credentials (read via the bus daemon's\nGetConnectionUnixUser / GetConnectionUnixProcessID) do not match. Do not\nrely on the D-Bus socket's filesystem permissions alone as the identity\nproof for host-root primitives.\n",
        "references": [
          "external: NIST SP 800-53r5 IA-3 Device Identification and Authentication",
          "external: freedesktop.org D-Bus / polkit caller authorization"
        ]
      },
      "mappings": {
        "nist": [
          "IA-3",
          "IA-9",
          "IA-2",
          "SC-23",
          "AC-6"
        ],
        "attack": [
          "T1543"
        ],
        "cwe": [
          "CWE-306",
          "CWE-862"
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
      "headline_rank": 1
    },
    {
      "id": "auth-7162fd48",
      "title": "MFA/TOTP is optional and user-opt-in with no enforced AAL, so the all-access owner account can be password-only",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "TOTP MFA is available but per-user opt-in via the profile page; no surface — including the unconditional all-access owner — mandates a second factor and no AAL target is declared.",
      "detail": "Home Assistant ships a TOTP MFA module, but MFA is purely opt-in: \"All available\nmodules will be listed in user profile page, user can enable the module he/she wants\nto use\" (auth_auth_module.md). The credential path is bcrypt password validation\n(Data.validate_login / hash_password); nothing in the auth flow mandates a second\nfactor on any surface. The owner account holds an unconditional all-access grant\n(_OwnerPermissions.access_all_entities returns True; filter short-circuits for admins),\nso a single phished/guessed/breach-reused password on the owner yields total control of\nCore, the integration secret vault, the Recorder DB, and (via the Supervisor proxy) the\nhost-root plane — with no second factor required. No NIST 800-63B AAL target is declared\nfor any surface.\n\nThis is high severity under the *api-security* rubric clause \"MFA optional on\nadministrative surfaces\" — here the administrative surface is the owner all-access\ngrant, the dominant blast-radius identity in the system. It is the all-access\nsensitivity that pins it high rather than critical (the rubric reserves critical for an\noutright bypass with NO factor available; here a strong factor exists but is not\nenforced). The AAL erosion from non-rotating long-lived tokens that bypass interactive\nMFA entirely routes to Ephemeral.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_auth_module.md",
          "locator": "#setup-flow, lines 30-31",
          "excerpt": "All available modules will be listed in user profile page, user can enable the module he/she wants to use."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.permissions._OwnerPermissions:L84-L96@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "def access_all_entities(self, key): return True ... return lambda entity_id, key: True"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "#owner, lines 27-29",
          "excerpt": "The owner ... will always have access to all permissions."
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Require MFA for the owner / admin surfaces and declare an AAL target per surface.",
        "detail": "Enforce TOTP (or a phishing-resistant FIDO2/WebAuthn factor) as mandatory for\nthe owner account and any admin-group user, rather than leaving the existing\nTOTP module opt-in on the profile page; add the enforcement at the\nhomeassistant auth provider's post-validate_login step so a missing factor\nblocks the all-access session. Declare an explicit NIST 800-63B AAL target by\nsurface (AAL2 for admin, and consider AAL3/WebAuthn for the owner and for\nhost-root-reaching Supervisor proxy access) and gate step-up on consequential\nadmin operations. Couples to the Ephemeral findings on long-lived tokens that\nsidestep interactive MFA.\n",
        "references": [
          "external: NIST SP 800-63B Authenticator Assurance Levels",
          "external: OWASP API Security Top 10 2023 API2"
        ]
      },
      "mappings": {
        "nist": [
          "IA-2(1)",
          "IA-2(2)",
          "IA-2(8)",
          "AC-6",
          "AC-6(2)"
        ],
        "attack": [
          "T1078"
        ],
        "cwe": [
          "CWE-308"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 9
    },
    {
      "id": "auth-8a380b11",
      "title": "No SBOM or SLSA build provenance over Core/Supervisor/add-on/mobile builds, so a swapped dependency or artifact is unattested",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "Build artifacts ship with no generated/signed SBOM and no build-provenance attestation, so the composition and origin of a release cannot be verified.",
      "detail": "The build inputs reviewed (supervisor-Dockerfile, the add-on manifest) show no\ngeneration of a CycloneDX/SPDX SBOM, no SLSA-style build-provenance attestation, and\nno in-toto link metadata accompanying the images or wheels. The Supervisor image\ninstalls requirements via `uv pip install` from a requirements file plus optional\nlocal wheels with no recorded, signed manifest of what went in, and there is no\nevidence of a continuous process to evaluate new vulnerabilities against a stored SBOM.\nConsequently, for any Core/Supervisor/add-on/mobile release there is no attested record\nof the components it contains or of the build that produced it — a swapped, backdoored,\nor typosquatted dependency (the supply_chain_attacker / malicious_in_process_sdk\npositions) leaves no provenance trail that would let a consumer detect it.\n\nThis is medium severity under the *api-security* rubric clause \"Unsafe consumption /\nsupply-chain hardening weakness\" framing: the absent SBOM/provenance is a supply-chain\nattestation gap that does not itself grant access but removes the authenticity record\nneeded to detect a component swap. Marked medium confidence because the review covers\nthe Dockerfiles and manifest in scope and the CI/release pipeline configuration that\nwould generate provenance is not in the artifact set — if a CI provenance step exists\nout-of-band, this downgrades. Pairs with the image-signing finding (a signature is only\nmeaningful when it attests a known SBOM).\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "infra/supervisor-Dockerfile",
          "locator": "lines 36-56 (build/install, no SBOM/provenance emission)",
          "excerpt": "uv pip install --no-cache -e ./supervisor && python3 -m compileall ./supervisor/supervisor"
        },
        {
          "artifact": "infra/addon-mosquitto-config.yaml",
          "locator": "config.yaml (manifest declares role/mounts, no provenance)",
          "excerpt": "auth_api: true; map: [ssl, share]; startup: system"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Generate, sign, and store an SBOM and SLSA provenance per release and verify it at deploy.",
        "detail": "Emit a CycloneDX or SPDX SBOM as a build step for the Core, Supervisor,\nadd-on, and mobile artifacts, sign it, and store it alongside the release;\nproduce SLSA Level 2+ build provenance (e.g. via the build platform's\nattestation, in-toto, or GitHub Actions provenance) and verify the provenance\nat the deploy/admission boundary together with the image signature. Wire a\ncontinuous job that re-evaluates new CVEs against the stored SBOM so a newly\ndisclosed component vulnerability is detectable across releases.\n",
        "references": [
          "external: SLSA build provenance levels",
          "external: CycloneDX / SPDX SBOM"
        ]
      },
      "mappings": {
        "nist": [
          "SR-3",
          "SR-4",
          "SR-4(4)",
          "SR-11",
          "SI-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-1395"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "CI/release pipeline configuration showing whether a CycloneDX/SPDX SBOM is generated and signed per release",
        "Whether SLSA build-provenance / in-toto attestations are produced and verified for Core/Supervisor/add-on/mobile artifacts"
      ]
    },
    {
      "id": "auth-8f0d8172",
      "title": "Add-on image signing (Cosign) is a developer recommendation, not enforced by admission control, and base images are pinned to a mutable tag",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Image signing is advisory best-practice with no verification gate at install/run, and the Supervisor base image is a floating tag — unsigned/tampered artifacts run unverified.",
      "detail": "Supply-chain artifact authenticity is unenforced. Add-on image signing is documented\nonly as a developer best-practice — \"Sign published images (the supported publishing\nworkflow can sign images with Cosign)\" (supervisor-apps-security.md) — with no\nstatement that the Supervisor VERIFIES a Cosign signature before installing or running\nan add-on image, and the add-on manifest (mosquitto config.yaml) declares role / mounts\n/ startup with no signature requirement. The Supervisor build itself derives from a\nbase image pinned to a registry tag (BUILD_FROM ghcr.io/home-assistant/base-python:\n3.14-alpine3.22-2026.05.0) rather than an immutable digest, and installs Python wheels\nwith no signature/attestation step. There is therefore no admission-control policy that\nblocks an unsigned or tampered image from running in production, and the identity of a\npulled artifact (is this the image the publisher signed?) is not verified at deploy time.\n\nThis is high severity under the *api-security* authenticity pattern \"Container images\ndeployed without signature verification or admission control\" — a supply-chain\ncompromise vector where a swapped add-on image or a tampered base/wheel runs with no\nauthenticity check, and add-ons can escalate to the supervisor/Docker host-root plane.\nThe artifact-immutability / digest-pinning lifecycle concern routes to Immutability /\nEphemeral; this finding is bounded to the absent signature verification.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "mobile/supervisor-apps-security.md",
          "locator": "#making-a-secure-app, line 33",
          "excerpt": "Sign published images (the supported publishing workflow can sign images with Cosign)"
        },
        {
          "artifact": "infra/supervisor-Dockerfile",
          "locator": "line 1 (BUILD_FROM floating tag)",
          "excerpt": "ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.14-alpine3.22-2026.05.0"
        },
        {
          "artifact": "infra/supervisor-Dockerfile",
          "locator": "lines 36-48 (wheels install, no attestation)",
          "excerpt": "uv pip install --compile-bytecode --no-cache --no-build -r requirements.txt"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Enforce Cosign signature verification at add-on install/run and pin base images by digest with attestation.",
        "detail": "Make image signature verification a hard admission gate in the Supervisor's\nadd-on install/start path: verify a Cosign signature (and ideally a\nkeyless/Fulcio identity) against the expected publisher before pulling/running\nany add-on image, and fail closed on an unsigned or mismatched image rather\nthan treating signing as a publisher courtesy. Pin the supervisor/core base\nimages by immutable digest (FROM ...@sha256:...) instead of the floating\nbase-python tag, and verify wheel integrity hashes/attestations at build.\nPair with SBOM/provenance (see the SBOM finding) so the verified signature\nattests a known artifact.\n",
        "references": [
          "external: Sigstore / cosign image signing and verification",
          "external: NIST SP 800-53r5 SR-4 Provenance"
        ]
      },
      "mappings": {
        "nist": [
          "SI-7",
          "SR-4",
          "SR-4(3)",
          "SR-11",
          "CM-5"
        ],
        "attack": [
          "T1195"
        ],
        "cwe": [
          "CWE-494"
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
      "headline_rank": 10
    },
    {
      "id": "auth-dfed90e4",
      "title": "trusted_networks (IP-address) and legacy api_password auth providers accept network position or a static shared secret as identity proof",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "risk",
      "summary": "Auth providers include IP-address-based trusted_networks and a legacy shared api_password, both of which prove no individual identity and are spoofable/replayable.",
      "detail": "The auth-provider set includes, alongside the homeassistant password provider,\ntrusted_networks (which authenticates a user by the SOURCE IP being in a configured\nrange) and the legacy_api_password provider (a single static shared secret), per the\nMFA configuration example listing legacy_api_password as a selectable provider\n(auth_auth_module.md) and the run/overview's record of trusted_networks + legacy\napi_password as enabled provider options. An IP address is not an identity: behind a\nreverse proxy, on a shared LAN, or under source-IP spoofing, \"in the trusted range\"\nproves only network position, and a trusted_networks user typically bypasses the\npassword factor entirely. A shared api_password is a single bearer secret common to all\ncallers, with no per-user identity and no second factor.\n\nNeither provider yields a verifiable individual identity, and trusted_networks in\nparticular substitutes network topology for authentication. This is medium severity\nunder the *api-security* rubric clause \"Defense-in-depth / weak authentication on\nsurfaces\" — these providers are opt-in and a hardened deployment uses the password\nprovider, but where enabled they materially weaken identity assurance. Medium confidence\nbecause the precise default-enabled state and per-deployment configuration are\noperator-controlled and not fixed in the reviewed artifacts.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/auth_auth_module.md",
          "locator": "#configuration-example, lines 52-63",
          "excerpt": "auth_providers: - type: homeassistant - type: legacy_api_password"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "#authentication-providers, lines 12-16",
          "excerpt": "It's up to the authentication provider to choose the method of authentication and the backend to use."
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Deprecate IP-as-identity and shared-secret providers, or constrain them with MFA and proxy-aware source validation.",
        "detail": "Treat trusted_networks as a convenience gate, not an authenticator: where it\nis used, still require the homeassistant password provider plus MFA for any\nconsequential action, and ensure the source IP is derived from a trusted proxy\nconfiguration (not a client-settable X-Forwarded-For) so it cannot be spoofed.\nRetire legacy_api_password in favor of per-user credentials and long-lived\ntokens with identity. Document that IP-range trust proves location, not\nidentity, and must not gate admin/owner access.\n",
        "references": [
          "external: NIST SP 800-53r5 IA-2 Identification and Authentication"
        ]
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-8",
          "IA-2(8)",
          "SC-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-291"
        ],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Whether trusted_networks / legacy_api_password are enabled by default or only on explicit operator configuration, and whether trusted_networks bypasses the password/MFA step"
      ]
    },
    {
      "id": "auth-ea69d3a2",
      "title": "Native<->WebView external-auth bridge dispatches on remote-frontend messages with only doc-only, unenforced callback-origin verification",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "risk",
      "summary": "The JS bridge that carries the access token native<->WebView relies on a documented 'verify the callback name' convention with no enforced origin/integrity check on the remotely-served frontend message source.",
      "detail": "The external-auth bridge moves the access token between the native Companion app and\nthe frontend loaded in the WebView. The frontend dispatches to native via\nwindow.externalAppV2 / webkit.messageHandlers (ExternalMessaging._sendExternal, code:\nL491-L505) and registers the native->WebView callback on window[CALLBACK_EXTERNAL_BUS]\n(fireMessage L381-L428); the iOS native handler switches on the incoming message TYPE\nwith no origin/integrity check (WebViewExternalMessageHandler.handleExternalMessage\nL37-L76). The only stated protection against a forged message is a DOCUMENTED\nconvention: \"Apps should verify the callback name matches the expected value to ensure\nthe callback has not been forged\" (frontend-external-authentication.md). This is\nguidance, not an enforced control, and the WebView renders the REMOTE, user-configured\nserver frontend — so a compromised backend or MitM-substituted response\n(compromised_backend_or_response position) is the very source the bridge trusts.\n\nThe identity of the party sending a bridge message (is this really the genuine frontend,\nnot hostile injected content?) is therefore not verifiable: there is no per-message\nauthentication binding the message to a trusted origin, only a stable callback name an\nattacker who controls the rendered content already knows. This is high severity under\nthe *mobile-applications* authenticity pattern for unverified bridge/caller identity\n(MASVS-PLATFORM-1/2): untrusted web content crosses into native capability, and the\nblast radius includes the access token the bridge carries. The input-validation and\ntoken-confidentiality faces route to Integrity and Confidentiality respectively.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "auth/frontend-external-authentication.md",
          "locator": "#get-access-token, line 19",
          "excerpt": "Apps should verify the callback name matches the expected value to ensure the callback has not been forged."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "switch externalBusMessage { case .configGet ... case .tagRead ... } // no origin/integrity check"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:src.external_app.external_messaging.ExternalMessaging.fireMessage:L381-L428@505966e84f3a90347c66261592908a02a4118189",
          "excerpt": "window[CALLBACK_EXTERNAL_BUS] = (msg) => this.receiveMessage(msg)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Enforce origin/integrity verification on the bridge rather than relying on a documented callback-name convention.",
        "detail": "Make the bridge authenticate its peer rather than trusting a stable callback\nname: on Android, use the WebViewFeature.WEB_MESSAGE_LISTENER (the V2 path\nalready required) with an allowlisted origin so only the genuine\nsame-origin frontend can post, and on iOS validate message.frameInfo /\nsecurityOrigin in the WKScriptMessageHandler against the configured instance\norigin before dispatching on the message type. Minimize the native\ncapability the bridge exposes to untrusted content, and never release the\naccess token to a message whose origin is not the verified instance frontend.\n",
        "references": [
          "external: OWASP MASVS-PLATFORM-2 (WebView / JS bridge)",
          "external: Android WebViewCompat WebMessageListener allowlisted origins"
        ]
      },
      "mappings": {
        "nist": [
          "IA-9",
          "SC-23",
          "AC-4",
          "SI-10"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [
          "MASVS-PLATFORM-2"
        ],
        "maswe": [
          "MASWE-0072"
        ]
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "immut-5a5ef5bd",
      "title": "Add-on and base images reference mutable floating tags with no digest pinning or immutable deployment record, so what runs in a container is not reproducible from an immutable provenance reference",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The mosquitto add-on build_from pins to floating ghcr.io base-debian:trixie tags and the core Dockerfile takes an unpinned BUILD_FROM, so the image actually deployed can change under a fixed reference with no immutable digest, SBOM, or deploy-record linking running container to a frozen artifact.",
      "detail": "Home Assistant's container build configuration references base images by mutable\nfloating tag rather than by immutable content digest. The official mosquitto\nadd-on build manifest pins both architectures to `ghcr.io/home-assistant/\n<arch>-base-debian:trixie` — a rolling tag that the registry owner can re-point\nat any time. The core Dockerfile takes `BUILD_FROM` as an unpinned ARG (`FROM\n${BUILD_FROM}`) and, while it pins the dockerfile *frontend* by digest\n(`# syntax=docker/dockerfile@sha256:...`), the *base image* it builds on is not\ndigest-pinned. The Supervisor Dockerfile similarly builds `FROM\nghcr.io/home-assistant/base-python:3.14-alpine3.22-2026.05.0` — a version tag,\nstill a mutable reference, not a digest.\n\nFrom the Immutability lens the defect is twofold: (1) the deployed image is not\nreproducible from an immutable reference — a fixed `:trixie` tag can resolve to\ndifferent content over time, so \"the image we ran\" cannot be frozen and re-proven;\nand (2) there is no immutable deployment/provenance record — no retained per-deploy\nSBOM, no signed image digest pinned at install, and no link from a running add-on\ncontainer back to a frozen artifact digest. This defeats the\ncode-and-artifact-deployment-record immutability class: there is no immutable\nrecord of what artifact produced the current runtime behavior.\n\nThe supply-chain *trust* question (is the image signed/verified at install,\nCosign) is an Authenticity concern and is routed there via related_concerns; this\nfinding is specifically the immutability/reproducibility/deployment-record gap of\npinning to mutable references and retaining no frozen provenance.\n\nSeverity is medium under the *api-security* Immutability common-pattern \"SBOM and\nartifact-provenance history not retained — only current SBOM stored,\" at the\nmedium end because no contractual supply-chain-attestation obligation is evidenced\nfor this self-hosted platform; it would escalate where such an attestation is\nrequired. The mosquitto add-on was flagged ephemeral on the `:trixie` floating\ntag in the run scope, corroborating the mutable-reference observation.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "infra/addon-mosquitto-build.yaml",
          "locator": "lines 2-4 build_from base-debian tags",
          "excerpt": "build_from: aarch64: ghcr.io/home-assistant/aarch64-base-debian:trixie; amd64: ...:trixie"
        },
        {
          "artifact": "infra/supervisor-Dockerfile",
          "locator": "line 1 ARG BUILD_FROM",
          "excerpt": "ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.14-alpine3.22-2026.05.0"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Pin base and add-on images by immutable content digest, retain a per-deploy SBOM and signed digest, and link the running container to that frozen provenance record.",
        "detail": "Replace the floating `:trixie` base references in the add-on build manifests\n(infra/addon-mosquitto-build.yaml lines 3-4) and the unpinned BUILD_FROM in the\ncore/supervisor Dockerfiles with `@sha256:<digest>` content-digest pins, mirroring\nthe digest pin already applied to the dockerfile syntax frontend in the core\nDockerfile (line 1). Retain a per-deploy SBOM and the signed image digest as an\nimmutable deployment record so the artifact that produced a running container is\nreconstructible after the fact, and surface the deployed digest from the running\ninstance so it can be reconciled against that record. Pair this with the\nAuthenticity recommendation that add-on/base images be Cosign-signed AND verified\nat install — pinning makes the artifact immutable; signing makes it attributable.\n",
        "references": [
          "external: NIST SP 800-53r5 SR-4(3) Provenance, CM-8 System Component Inventory"
        ]
      },
      "mappings": {
        "nist": [
          "CM-2",
          "CM-8",
          "SR-4",
          "SR-4(3)",
          "SI-7",
          "AU-11"
        ],
        "attack": [
          "T1525"
        ],
        "cwe": [
          "CWE-829"
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
      "id": "nonrep-af1c55d3",
      "title": "logbook entries carry null context_user_id, so even the state-history surface lacks an attributable actor for consequential state changes",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The only persisted trace of state changes (logbook) records context_user_id as null in the documented sample, so a consequential action cannot be tied to the user, token, or principal that caused it.",
      "detail": "Even setting aside that `logbook` is a history surface and not a security\naudit (Finding nonrep-00000001), the trace it does provide lacks actor\nattribution. The brief's `/api/logbook` sample shows `\"context_user_id\": null`\n— the field that would name the acting user is empty. AU-3 (Content of Audit\nRecords) and AU-10 (Non-Repudiation) both require that each record bind the\naction to an actor; a null actor field defeats both.\n\nThis is structurally worse than a \"system account\" attribution because there\nis no actor at all to even disambiguate. Two paths make the actor\nunrecoverable by construction: (1) the bearer-less webhook path —\nwebhook_call_service runs every service call under a SYNTHESIZED\n`registration_context` (cev-a1000015), not a user identity, so a leaked\nwebhook_id holder who actuates a lock is attributable to no human; and\n(2) the supervisor-socket and signed-query auth paths in the middleware\n(cev-a1000009) authenticate a request without necessarily resolving it to a\nnamed interactive user.\n\nSeverity HIGH under the api-security rubric \"Partial audit gap on\nconsequential-action flows\" — attribution loss specifically named in that\nclause (\"logged ... without actor attribution; impairs incident\nreconstruction\"). The actor field is only as strong as the authentication\nthat would populate it; that strength question is Authenticity's (the webhook\npossession-only model and synthesized context are already filed there).\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "api/rest.md",
          "locator": "/api/logbook sample response, lines 360-383",
          "excerpt": "\"context_user_id\": null"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.webhook_call_service:L269-L292@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "async_call(... context=registration_context(...)) # synthesized context, no per-entity permission check"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Populate a resolved actor identity on every audit record, and for the synthesized webhook context record the registering device/user as the on-behalf-of principal.",
        "detail": "On the new audit stream (Finding nonrep-00000001), require a non-null actor\non every record. For interactive REST/WS requests the actor is the resolved\nuser from the validated access token (cev-a1000002). For the webhook path\n(cev-a1000015), the synthesized `registration_context` must carry — and the\naudit record must capture — the device's `webhook_id`-to-config_entry binding\nand the registering user (the bearer principal recorded at\ncev-a1000014 registration time) as the on-behalf-of actor, so a\nlock/alarm actuation through a leaked webhook_id is attributable to the\nregistered device rather than to no one. For supervisor-socket and\nsigned-query auth (cev-a1000009), record the service principal explicitly\nrather than emitting a null actor.\n",
        "references": [
          "external: NIST SP 800-53r5 AU-3, AU-10"
        ]
      },
      "mappings": {
        "nist": [
          "AU-3",
          "AU-3(1)",
          "AU-10",
          "AU-10(1)",
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
      "prerequisite_evidence": []
    },
    {
      "id": "nonrep-d23de889",
      "title": "Time-source discipline for event ordering (NTP topology, drift bounds, timestamp precision) is unspecified across Core, Supervisor, and os-agent",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "low",
      "disposition": "blocked",
      "summary": "No artifact specifies the time source, NTP discipline, drift bounds, or timestamp precision that any future audit (or the existing logbook timestamps) would rely on for reliable event ordering.",
      "detail": "AU-8 (Time Stamps) requires a reliable, disciplined time source so audit\nevents can be ordered and correlated, especially across the Core / Supervisor /\nos-agent / host-Docker tiers that an incident must be reconstructed across. The\nartifacts are silent on the time source: there is no NTP topology, no drift\nbound, no fallback-on-time-source-failure behavior, and no timestamp-precision\nstatement (millisecond vs microsecond). The logbook entries carry timestamps\nbut the discipline behind them is undocumented.\n\nPer the evidence-discipline block-on-ambiguity rule and the api-security\nnon-repudiation common pattern \"No time-source policy — disposition:\nuncertainty or blocked\", this is recorded as BLOCKED rather than asserted: the\nartifacts neither confirm a disciplined source nor confirm its absence. It is\npre-loaded here because any remediation of Findings 1-8 (introducing an audit\nstream) depends on a trustworthy time source to make the records orderable and\ncorrelatable across tiers.\n\nSeverity MEDIUM reflects that this is a prerequisite-for-correct-audit concern\nrather than a confirmed gap; it would rise if a cross-tier correlation\nrequirement were confirmed against an undisciplined clock.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "api/rest.md",
          "locator": "/api/logbook sample, lines 360-383",
          "excerpt": "\"when\": \"2016-...Z\" # timestamp present; time-source discipline undocumented"
        },
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#deployment-topologies, lines 108-116",
          "excerpt": "Home Assistant OS (appliance image) ... Supervised ... Container ... Core"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Specify and enforce a disciplined UTC time source with documented drift bounds for the audit stream introduced by Findings 1-8.",
        "detail": "Document and enforce the time source the audit subsystem (Finding\nnonrep-00000001) will stamp records with: an NTP-disciplined UTC clock on the\nHAOS appliance and the Supervised host, sub-second precision, a documented\ndrift bound, and a defined behavior when the time source is unavailable.\nWithout this, audit records across the Core / Supervisor / os-agent tiers\ncannot be reliably ordered during incident reconstruction.\n",
        "references": [
          "external: NIST SP 800-53r5 AU-8 Time Stamps"
        ]
      },
      "mappings": {
        "nist": [
          "AU-8",
          "AU-8(1)"
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
      "prerequisite_evidence": [
        "Time-source specification for Core/Supervisor/os-agent — NTP topology, time authority, drift bounds, behavior on time-source failure, and audit timestamp precision (ms/us)",
        "Whether timestamps are recorded in UTC with monotonic-on-write ordering across the Core/Supervisor/host-Docker tiers"
      ]
    },
    {
      "id": "merged-4f0fe6c1",
      "title": "Supervisor health-check depth and watchdog auto-recovery / restart policy for Core and add-ons are undocumented, so failure detection and recovery cannot be assessed",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "low",
      "disposition": "gap",
      "summary": "The artifacts do not document the Supervisor's liveness/readiness/dependency health-check depth or its watchdog/observer auto-recovery and add-on restart policy, so on this single-host instance neither whether a hung-but-alive Core is detected nor whether it is automatically restarted (with what backoff and cap) can be assessed.",
      "detail": "The Availability and Resilient lenses raise the same uncertainty about the\nsame artifact (the Supervisor README) from two sides of one mechanism.\nAvailability (avail-77752ee2): the depth of health checks — liveness vs\nreadiness vs dependency health — and the watchdog/observer semantics are\nundocumented, so whether failures are DETECTED cannot be assessed.\nResilient (resil-b1d0c558): whether the watchdog auto-restarts a\nhung-but-alive Core, with what backoff and restart cap, and the add-on\nrestart policy on crash, are undocumented, so whether failures are\nRECOVERED cannot be assessed. Detection and recovery are the two halves of\nthe Supervisor watchdog/observer's role; both are open against the same\nREADME evidence, and the resolving evidence (the watchdog/observer source\nand its restart config) is identical for both. This is one uncertainty —\nthe Supervisor self-healing behavior is unspecified in the artifacts —\nkept as a single record so the evidence request is made once.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "repos/supervisor-README.md",
          "locator": "lines 5-9",
          "excerpt": "container-based system for managing your Home Assistant Core installation"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document and verify the Supervisor watchdog/observer health-check depth, auto-recovery, and add-on restart policy.",
        "detail": "Obtain and record the Supervisor watchdog/observer behavior: the\nliveness/readiness/dependency health-check definitions Core and add-ons\nexpose, the conditions under which the watchdog restarts a hung-but-alive\nCore, the backoff curve and restart cap, and the per-add-on restart\npolicy on crash. Both lenses are satisfied by the same evidence, so\nrequest it once. Posture is recommended rather than required because the\nfinding is an uncertainty (the behavior may well be adequate but is\nunverified in the artifacts) — code recon of the supervisor watchdog\nmodule would likely resolve it.\n"
      },
      "mappings": {
        "nist": [
          "CP-10",
          "SC-5",
          "SI-13",
          "SI-17"
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
      "lens_perspectives": [
        null,
        null
      ],
      "prerequisite_evidence": []
    },
    {
      "id": "merged-66801b1b",
      "title": "Core and Supervisor emit no attributable security-audit record over the consequential-action surface (device actuation, auth lifecycle, privileged Supervisor API)",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "There is no security-purposed audit stream in Core or Supervisor: admin-gated state writes and service calls that actuate locks/alarms, the entire auth/token/credential lifecycle, and the host-root-equivalent Supervisor operations (add-on install, backup, container-exec) all complete with no attributable record naming who did what, leaving the highest-impact action paths fully deniable and credential-compromise reconstruction impossible.",
      "detail": "Three Non-Repudiation findings cite distinct entrypoints (POST /api/states\nand service dispatch; the Core auth subsystem's token/credential events;\nthe Supervisor privileged-API middleware) but share one root cause: the\nsystem has no security-audit stream over its consequential-action surface.\nThe device-actuation path emits no record naming who actuated which lock\nor alarm (nonrep-12328d11). The auth subsystem produces no auditable event\nfor login success/failure, token issuance/refresh/revocation, or\npassword/MFA change (nonrep-5dd8b9f0). The Supervisor middleware logs only\nrole-DENY misses as a diagnostic warning; the host-root-equivalent\noperations it ALLOWS (add-on lifecycle, backup, Docker exec) produce no\nrecord of the allowed action or its caller (nonrep-3b6ebb6c). Each is the\nsame gap — no attributable audit over consequential actions — observed at\na different surface. Merging them yields one coherent finding: the\naudit-stream absence, scoped across the three action surfaces, so the\nremediation is designed once rather than three times. The os-agent\nhost-root audit gap (nonrep-177fa3cc) and the audit-read/SoD gap\n(nonrep-30404306) are downstream of the same absence and are linked.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APIEntityStateView.post:L257-L275@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "if not user.is_admin: raise Unauthorized(entity_id=entity_id)  # NO per-entity write policy"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APIEntityStateView.get:L242-L255@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "if not user.permissions.check_entity(entity_id, POLICY_READ): raise Unauthorized(entity_id=entity_id)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.permissions.filter_entity_ids_by_permission:L32-L39@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "if user.is_admin or user.permissions.access_all_entities(key): return list(entity_ids)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "config_entry = hass.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]  # no bearer, no rate-limit / dedup observed"
        },
        {
          "artifact": "api/native-app/sending-data.md",
          "locator": "#response, line 86",
          "excerpt": "As a general rule, expect to receive a 200 response for all your requests."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APIEntityStateView.post:L257-L275@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "if not user.is_admin: raise Unauthorized(entity_id=entity_id) # state WRITE admin-or-deny"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.webhook_call_service:L269-L292@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "async_call(data[ATTR_DOMAIN], data[ATTR_SERVICE], ... ) # arbitrary service call, no audit"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.AddSSHAuthKey:L57-L75@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "file.WriteString(newKey) ... \"key added for user root\" # no in-method authz, no audit"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.ScheduleWipeDevice:L29-L55@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "func (d system) ScheduleWipeDevice(...) # schedule factory-reset / datadisk wipe over D-Bus"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.permissions._OwnerPermissions:L84-L96@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "def access_all_entities(self, key): return True # owner unconditional all-access"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "#owner, lines 27-29",
          "excerpt": "The onboarding user is the owner (all permissions)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.api.middleware.security.SecurityMiddleware.token_validation:L302-L375@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "if patterns.role_access[app.hassio_role].match(request.path): ... else: _LOGGER.warning(\"%s no role for %s\")"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.docker.manager.DockerAPI.container_run_inside:L935-L935@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "async def container_run_inside(self, name: str, command: str) -> ExecReturn:"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:functions.handlers.handleRequest:L51-L95@142579dc41ee534f0d60bc390c4661dba051a995",
          "excerpt": "const { push_token: token } = req.body; if (!token) return res.status(403) ... checkRateLimit(token)"
        },
        {
          "artifact": "mobile/mobile-apps-fcm-push-README.md",
          "locator": "#deploy-your-own, lines 27-47",
          "excerpt": "forwards notifications ... without exposing device push tokens to the instance"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.AuthManager.async_create_access_token:L599-L617@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "jwt.encode({\"iss\": refresh_token.id ...}, refresh_token.jwt_key, algorithm=\"HS256\")"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "#refresh-token-types, lines 49-51",
          "excerpt": "Long-Lived Access Token (user-generated, long horizon) ... remain valid until a user deletes it"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Introduce one security-audit stream covering device actuation, auth lifecycle, and privileged Supervisor operations, with actor attribution on every entry.",
        "detail": "The three lenses reinforce a single program. Define the consequential-\naction surface (device actuation via /api/states and service calls; the\nfull auth/token/credential/MFA lifecycle; every ALLOWED Supervisor\nprivileged operation — add-on install/remove, backup, container exec),\nthen emit a security-purposed audit record on each, distinct from the\nuser-facing logbook and the diagnostic logger, carrying actor (subject,\non-behalf-of, source), action, target, and time. Critically, log\nALLOWED privileged operations, not only DENIED ones — the current\nSupervisor middleware inverts this. Pair the stream with tamper-evidence\nand an audit-read/segregation-of-duties role (tracked in the linked\nos-agent and audit-read records) so the new evidence is itself durable\nand access-controlled. This is required: without it the highest-impact\nactions in the system are unattributable and disputes are unwinnable.\n"
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-3(7)",
          "AC-5",
          "AC-6(1)",
          "AC-6(9)",
          "AU-10",
          "AU-12",
          "AU-12(1)",
          "AU-2",
          "AU-3",
          "AU-6(3)",
          "AU-9",
          "AU-9(4)",
          "AU-9(6)",
          "IA-5",
          "SC-5",
          "SI-10"
        ],
        "attack": [
          "T1098"
        ],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [
        null
      ],
      "prerequisite_evidence": []
    },
    {
      "id": "merged-a49cb674",
      "title": "Recorder history DB persists home-occupancy/geolocation state with neither encryption nor tamper-evidence at rest",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The Recorder history store holds raw presence, geolocation, and lock/alarm state with no encryption-at-rest and no append-only/WORM/content-hash protection, so any filesystem or DB read both discloses the home-occupancy fact base and can silently rewrite or delete it undetected.",
      "detail": "Two lenses converge on the single Recorder store (session_scope, an\nordinary mutable SQLite/MariaDB/Postgres database). The Confidentiality\nlens establishes the store has no encryption-at-rest layer over a\nhigh-privacy fact base (presence, geolocation/zones, lock and alarm\nhistory), so a host or DB read discloses where occupants are and were.\nThe Immutability lens establishes the same store has no append-only tier,\nno WORM, and no content-hash, so the same actor with DB or host access\ncan rewrite or delete that history with no detection. The two are the\nsame architectural decision — Recorder is a plain mutable, plaintext DB —\nassessed for the two distinct properties it lacks (secrecy at rest, and\npreservation against alteration). Treating them as one record keeps the\nremediation coherent: an at-rest protection program for Recorder must\naddress both encryption and tamper-evidence together, because partial\nwork (encrypt-only, or hash-only) leaves the other exposure standing.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.backups.backup.Backup.set_password:L122-L353@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "self._password: str | None = None ... self._password = password or None"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "Recorder DB session for entity-state history"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.storage.Store._write_prepared_data:L602-L618@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "write_method(path, json_data, self._private, mode=mode)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.models.RefreshToken:L104-L121@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "jwt_key: str = attr.ib(factory=lambda: secrets.token_hex(64))"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.AuthManager.async_create_access_token:L599-L617@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "jwt.encode({...}, refresh_token.jwt_key, algorithm=\"HS256\")"
        },
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#sensitive-data-inventory (presence/geolocation/lock/alarm)",
          "excerpt": "Recorder history of entity state: presence, geolocation/zones, camera/voice events, lock/alarm state"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:iOS WebView (remote frontend) -> Core REST+WS API (user instance URL):L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "Target is the user-entered self-hosted instance URL (no fixed host)"
        },
        {
          "artifact": "api/native-app/setup.md",
          "locator": "registration response, lines 74-79",
          "excerpt": "returns webhook_id, secret, cloudhook_url"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.websocket_api.auth.AuthPhase.async_handle:L85-L123@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "registers revoke callback to drop the socket on token revocation"
        },
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#what-home-assistant-is, lines 20-22",
          "excerpt": "integrations are not sandboxed from each other and run with Core's full privilege"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.api.middleware.security.SecurityMiddleware.token_validation:L302-L375@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "if patterns.role_access[app.hassio_role].match(request.path)"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "§'Refresh token types', line 51",
          "excerpt": "System … generated and used by system users … never exposed"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.Shared.API.ServerManagerPersistence.ServerManagerKeychain:L6-L35@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "iOS access/refresh tokens persist via KeychainAccess"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...database.server.ServerSessionInfo.ServerSessionInfo:L1-L1@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "persisted access + refresh bearer tokens (in_degree 21)"
        },
        {
          "artifact": "auth/auth_index.md",
          "locator": "§'Access and refresh tokens', line 41",
          "excerpt": "refresh tokens will remain valid until a user deletes it"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Apply both encryption-at-rest and tamper-evidence to the Recorder history store as one program.",
        "detail": "The two lenses reinforce rather than conflict, so integrate the\nremediation: place the Recorder DB on an encrypted-at-rest backing\n(full-disk or DB-native TDE plus, where feasible, field-level\nprotection of the highest-privacy presence/geo columns) AND add\ntamper-evidence over the history records (append-only/WORM tier or a\nperiodic content-hash/Merkle anchor with an external chain head). Both\nare required because each closes a different exposure on the same\nstore; shipping only one leaves either the disclosure or the silent-\nalteration risk fully open. Sequence the at-rest encryption first\n(it gates the Immutability-over-PHI cross-tier dependency) then layer\nthe integrity anchoring.\n"
      },
      "mappings": {
        "nist": [
          "AC-12",
          "AC-2",
          "AC-2(3)",
          "AC-4",
          "CP-7",
          "CP-9",
          "CP-9(8)",
          "IA-5",
          "IA-5(1)",
          "IA-5(13)",
          "SC-12",
          "SC-12(1)",
          "SC-13",
          "SC-28",
          "SC-28(1)",
          "SC-36",
          "SC-5",
          "SC-7",
          "SC-7(21)"
        ],
        "attack": [
          "T1005",
          "T1530",
          "T1552",
          "T1606"
        ],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [
        null,
        null
      ],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 3
    },
    {
      "id": "merged-0ccd3ea6",
      "title": "2000+ in-process integrations and the recorder write path share one asyncio event loop with no per-integration timeout, bulkhead, or circuit breaker",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Every one of 2000+ integrations and the recorder write path run on Core's single shared asyncio loop with no per-call timeout, circuit breaker, bulkhead, or execution-time budget, so one slow or hostile integration or outbound call blocks the loop and cascades to a platform-wide stall that starves the consequential alarm/lock and recorder paths.",
      "detail": "Two Resilient findings describe the same structural decision from the\ninbound and outbound sides of the shared loop. resil-5e5a02f0: outbound\ncalls from 2000+ in-process integrations to external devices/clouds run on\nthe shared loop with no per-call timeout or circuit breaker, so a slow or\nhostile endpoint blocks the loop. resil-cb12ebae: the same 2000+\nintegrations plus the recorder write path share one asyncio loop with no\nbulkhead, per-integration execution-time budget, or watchdog, so one\nblocking integration starves the consequential alarm/lock and recorder\npaths. Both name the identical root cause — a single shared event loop\nwith no isolation primitive — one emphasizing the missing outbound\ntimeout/breaker and the other the missing bulkhead/budget. Merging keeps\nthe isolation remediation as one design problem (loop isolation) rather\nthan two partial patches. The webhook-backpressure (resil-872de693),\nmobile-reconnect (resil-895658c9), and push-queue-replay (resil-a4c9535c)\nrecords are distinct resilience gaps on other surfaces and are linked, as\nare the WebView fail-safe (resil-43c0c35b) and the two audit records that\nbelong to the cross-group audit-absence finding.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "@contextmanager def session_scope(...): # Recorder DB session for entity-state history"
        },
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "#sensitive-data-inventory, line 100-102",
          "excerpt": "History / state DB (Recorder) ... presence, geolocation, camera/voice events, lock/alarm state"
        },
        {
          "artifact": "api/rest.md",
          "locator": "/api/logbook sample, lines 360-383",
          "excerpt": "\"context_user_id\": null"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "config_entry = hass.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id] # webhook_id is the authenticator"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:iOS WebView (remote frontend) -> Core REST+WS API (user instance URL):L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "CROSS_HTTP_CALLS: Companion WebView loads + calls the user-configured Core instance"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "switch externalBusMessage { case .configGet ... case .tagRead ... }"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "trustManagerFactory.init(androidCaStore) ... trusts USER-installed CAs"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "Recorder DB session for entity-state history"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.api.APITemplateView.post:L479-L505@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "tpl = _cached_template(data[\"template\"], ...); tpl.async_render(...)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "No bearer, no rate-limit observed here."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.webhook_call_service:L269-L292@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "async_call(..., blocking=True, context=registration_context(...))"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:common...database.server.ServerSessionInfo.ServerSessionInfo:L1-L1@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
          "excerpt": "persisted access + refresh bearer tokens (in_degree 21)"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:__route__POST__/api/sendPushNotification:L40-L43@142579dc41ee534f0d60bc390c4661dba051a995",
          "excerpt": "Public relay route forwarding notifications to APNS/FCM"
        },
        {
          "artifact": "mobile/mobile-apps-fcm-push-README.md",
          "locator": "lines 42-47",
          "excerpt": "forwards notifications without exposing device push tokens to the instance"
        },
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "lines 20-22 (trust posture)",
          "excerpt": "integrations are not sandboxed from each other and run with Core's full privilege"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Isolate integrations and the recorder path from the shared loop with per-call timeouts, circuit breakers, and bulkheads.",
        "detail": "The two lenses reinforce one isolation design. Add a per-call timeout\nand circuit breaker on every outbound integration call so a slow or\nhostile external endpoint cannot pin the loop (resil-5e5a02f0), AND add\na bulkhead / per-integration execution-time budget plus a watchdog so a\nsingle misbehaving integration cannot starve the consequential\nalarm/lock and recorder paths (resil-cb12ebae). Run the recorder write\npath and the consequential-actuation path in protected lanes (separate\nexecutor or priority budget) so they survive a noisy integration. This\nis required: the alarm/lock control path is the highest-consequence\nsurface and it currently shares an unbounded loop with 2000+ third-party\nintegrations.\n"
      },
      "mappings": {
        "nist": [
          "AU-10",
          "AU-12",
          "AU-2",
          "AU-3",
          "AU-3(1)",
          "AU-6",
          "CP-10",
          "CP-12",
          "CP-13",
          "IA-3",
          "SC-5",
          "SC-6",
          "SI-13",
          "SI-17"
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
      "lens_perspectives": [
        null
      ],
      "prerequisite_evidence": []
    },
    {
      "id": "merged-1119b0be",
      "title": "Core .storage is plaintext JSON with no content MAC, version history, or drift detection, so a file-write tampers keys/policy and config changes leave no immutable record",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "All Home Assistant .storage (refresh-token jwt_keys, user/group policy, integration secrets, plus configuration.yaml) is mutable plaintext gated only by 0600 file permissions, with no content MAC, no required version history or signed-commit path, and no declared-vs-actual drift detection, so a single file-write both forges signing keys/escalates privilege undetected and leaves config changes with no immutable change record.",
      "detail": "The Integrity and Immutability lenses converge on the same artifact —\n.storage written in place by Store._write_prepared_data as plaintext\nUTF-8 JSON, protected only by 0600 filesystem permissions — for two\nproperties it lacks. The Integrity lens: there is no MAC or content hash\nover the records, so a file-write primitive forges refresh-token jwt_keys\n(minting valid access tokens) or rewrites the user/group permission\npolicy (escalating a principal) with no detection at read time. The\nImmutability lens: the same plaintext store, plus configuration.yaml, has\nno required version history, no signed-commit/GitOps-only change path, and\nno drift detection between declared and running state, so the change that\ntampers it also leaves no immutable record that it occurred. These are one\nroot cause — .storage has no cryptographic protection and no change\nprovenance — viewed as a write-time forgery risk and as a preservation/\nchange-record gap. The Confidentiality lens on the same .storage\n(conf-fdf0fb06, no encryption at rest, critical) is the third face of the\nconvergence and is linked rather than merged because it lives in another\ncandidate group; together the three are the Conf+Integrity+Immutability\n.storage triad.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.api.middleware.security.SecurityMiddleware.token_validation:L302-L375@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "if patterns.role_access[app.hassio_role].match(request.path): ... else: _LOGGER.warning(\"%s no role for %s\")"
        },
        {
          "artifact": "org/SECURITY.md",
          "locator": "whole file (6-line pointer; no audit/hardening content)",
          "excerpt": "security-policy pointer to website; no embedded audit or log-protection content"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.recorder.session_scope:L71-L72@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "@contextmanager def session_scope(...): # Recorder DB session for entity-state history"
        },
        {
          "artifact": "architecture/adr/0018-supported-databases.md",
          "locator": "ADR-0018 supported databases (SQLite / MariaDB / PostgreSQL)",
          "excerpt": "supported recorder databases — SQLite, MariaDB, PostgreSQL"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.storage.Store._write_prepared_data:L602-L618@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "mode, json_data = json_helper.prepare_save_json(data, ...) ... write_method(path, json_data, self._private, mode=mode)"
        },
        {
          "artifact": "architecture/adr/0021-YAML-integration-configuration-deprecation-policy.md",
          "locator": "ADR-0021 YAML integration configuration deprecation policy",
          "excerpt": "integration configuration migrates from YAML toward UI/.storage-managed config entries"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor.backups.backup.Backup.set_password:L122-L353@7eaf69fcab6a9fd1607b6d7000cbe75b3c96b7b2",
          "excerpt": "self._password: str | None = None ... def set_password(self, password): self._password = password or None"
        },
        {
          "artifact": "00-SYSTEM-OVERVIEW.md",
          "locator": "§Sensitive-data inventory, backup artifact line",
          "excerpt": "full snapshots bundle config + recorder DB + secrets; backup password optional; weakest-protected copy"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
          "excerpt": "guard let incomingMessage = WebSocketMessage(dictionary) ... switch externalBusMessage { case .configGet ... case .tagRead ... }"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:src.external_app.external_messaging.ExternalMessaging.fireMessage:L381-L428@505966e84f3a90347c66261592908a02a4118189",
          "excerpt": "window[CALLBACK_EXTERNAL_BUS] = (msg) => this.receiveMessage(msg)"
        },
        {
          "artifact": "auth/frontend-external-authentication.md",
          "locator": "#external-authentication, callback-name forgery warning",
          "excerpt": "callback names must be verified to avoid forgery"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.helpers.storage.Store._write_prepared_data:L602-L618@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "write_method(path, json_data, self._private, mode=mode)  # plaintext UTF-8 JSON; 0600 only, NO encryption/MAC"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.permissions.util.compile_policy:L23-L52@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "def apply_policy_deny_all(entity_id, key): return False ... if policy is True: def apply_policy_allow_all"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.auth.models.RefreshToken:L104-L121@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "jwt_key: str = attr.ib(factory=lambda: secrets.token_hex(64))"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.webhook_call_service:L269-L292@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "await hass.services.async_call(data[ATTR_DOMAIN], data[ATTR_SERVICE], ... context=registration_context(...))"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:homeassistant.components.mobile_app.webhook.handle_webhook:L172-L180@28076bcad6158160647ac62c92f1ff5acd4851ca",
          "excerpt": "config_entry = hass.data[DOMAIN][DATA_CONFIG_ENTRIES][webhook_id]"
        },
        {
          "artifact": "api/native-app/sending-data.md",
          "locator": "#interaction-basics, line 63",
          "excerpt": "These requests do not need to contain authentication."
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.AddSSHAuthKey:L57-L75@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "file := os.OpenFile(sshAuthKeyFileName, O_APPEND|O_CREATE|O_WRONLY, 0644) ... \"key added for user root\""
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:system.system.ScheduleWipeDevice:L29-L55@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "func (d system) ScheduleWipeDevice(...) # schedule factory-reset / datadisk wipe over D-Bus"
        },
        {
          "artifact": "code-evidence-index.yaml",
          "locator": "code:supervisor (D-Bus client) -> system.system.AddSSHAuthKey (os-agent):L57-L75@bbaf039bab5024f5397f442b081bb964c9d4f7f6",
          "excerpt": "CROSS_CHANNEL: Supervisor calls os-agent host methods over the system D-Bus (io.hass.os)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add a content MAC plus a versioned, drift-detected change path over .storage so tampering both fails verification and leaves an immutable record.",
        "detail": "The two lenses reinforce: a single protection program closes both. (1)\nIntegrity — add a keyed MAC or signed-content envelope over each\n.storage record (key held outside the .storage tree), verified on read,\nso a directed file-write that forges a jwt_key or flips a policy fails\nverification rather than silently taking effect. (2) Immutability —\nroute config-affecting .storage and configuration.yaml changes through a\nversioned, signed-commit/GitOps path as the only sanctioned mutation\nroute, and run declared-vs-actual drift detection so an out-of-band edit\nis both rejected and recorded. Pair this with the Confidentiality\nat-rest encryption tracked in the linked .storage record — the MAC\nprotects against tamper, the encryption against disclosure, and the\nversion history against silent change; all three are required because\neach leaves a distinct exposure standing if omitted.\n"
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-3(7)",
          "AC-6",
          "AU-11",
          "AU-9",
          "AU-9(2)",
          "AU-9(3)",
          "CM-2",
          "CM-2(2)",
          "CM-2(3)",
          "CM-3",
          "CM-3(1)",
          "CM-5",
          "CM-6",
          "CP-9",
          "CP-9(1)",
          "CP-9(8)",
          "MP-4",
          "SC-18",
          "SC-28",
          "SC-7",
          "SI-10",
          "SI-7",
          "SI-7(1)",
          "SI-7(8)"
        ],
        "attack": [
          "T1070",
          "T1098",
          "T1190",
          "T1490",
          "T1565",
          "T1606"
        ],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": [],
        "atlas": [],
        "masvs": [],
        "maswe": []
      },
      "lens_perspectives": [
        null,
        null
      ],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 2
    }
  ],
  "contradictions": [],
  "contradictions_notes": null,
  "severity_disagreements": [],
  "severity_disagreements_notes": null,
  "nist_rollup": [
    {
      "family": "SC",
      "title": "System & Communications Protection",
      "covered": 1,
      "gapped": 7,
      "both": 16,
      "notable": "SC-12(3) strong; SC-36(1), SC-7(21), SC-22 gapped"
    },
    {
      "family": "AU",
      "title": "Audit & Accountability",
      "covered": 0,
      "gapped": 14,
      "both": 3,
      "notable": "AU-11, AU-3(1), AU-10 gapped"
    },
    {
      "family": "AC",
      "title": "Access Control",
      "covered": 1,
      "gapped": 7,
      "both": 7,
      "notable": "AC-24 strong; AC-2(3), AC-2, AC-2(2) gapped"
    },
    {
      "family": "IA",
      "title": "Identification & Authentication",
      "covered": 1,
      "gapped": 5,
      "both": 8,
      "notable": "IA-7 strong; IA-5(7), IA-5(13), IA-8 gapped"
    },
    {
      "family": "CP",
      "title": "Contingency Planning",
      "covered": 0,
      "gapped": 9,
      "both": 2,
      "notable": "CP-9, CP-9(1), CP-10 gapped"
    },
    {
      "family": "CM",
      "title": "Configuration Management",
      "covered": 0,
      "gapped": 6,
      "both": 2,
      "notable": "CM-3, CM-5, CM-8 gapped"
    },
    {
      "family": "SI",
      "title": "System & Information Integrity",
      "covered": 0,
      "gapped": 5,
      "both": 3,
      "notable": "SI-15, SI-17, SI-7(6) gapped"
    },
    {
      "family": "SR",
      "title": "Supply Chain Risk Management",
      "covered": 0,
      "gapped": 4,
      "both": 1,
      "notable": "SR-3, SR-4(4), SR-11 gapped"
    },
    {
      "family": "MP",
      "title": "Media Protection",
      "covered": 0,
      "gapped": 1,
      "both": 1,
      "notable": "MP-5 gapped"
    },
    {
      "family": "SA",
      "title": "System & Services Acquisition",
      "covered": 0,
      "gapped": 1,
      "both": 1,
      "notable": "SA-15 gapped"
    },
    {
      "family": "RA",
      "title": "Risk Assessment",
      "covered": 0,
      "gapped": 1,
      "both": 0,
      "notable": "RA-3 gapped"
    }
  ],
  "attack_exposure": [
    {
      "id": "T1078",
      "name": "Valid Accounts",
      "findings": 4,
      "mitigations": [
        "conf-cap-1044dbb3",
        "ephem-cap-5113fad9",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1557",
      "name": "Adversary-in-the-Middle",
      "findings": 3,
      "mitigations": [
        "conf-cap-01c47d42",
        "conf-cap-277b2364",
        "intg-cap-70ef26f7"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1098",
      "name": "Account Manipulation",
      "findings": 2,
      "mitigations": [
        "ephem-cap-5113fad9",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1499",
      "name": "Endpoint Denial of Service",
      "findings": 2,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1606",
      "name": "Forge Web Credentials",
      "findings": 2,
      "mitigations": [
        "auth-cap-f01e6108",
        "ephem-cap-5113fad9",
        "intg-cap-7a54b1a7",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1005",
      "name": "Data from Local System",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1070",
      "name": "Indicator Removal",
      "findings": 1,
      "mitigations": [
        "conf-cap-01c47d42",
        "conf-cap-277b2364",
        "intg-cap-70ef26f7"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1190",
      "name": "Exploit Public-Facing Application",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1195",
      "name": "Supply Chain Compromise",
      "findings": 1,
      "mitigations": [
        "ephem-cap-5113fad9",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1213",
      "name": "Data from Information Repositories",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "conf-cap-01c47d42",
        "conf-cap-277b2364",
        "ephem-cap-5113fad9",
        "intg-cap-70ef26f7",
        "intg-cap-7a54b1a7",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1409",
      "name": "Stored Application Data",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1417",
      "name": "Input Capture",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1490",
      "name": "Inhibit System Recovery",
      "findings": 1,
      "mitigations": [
        "ephem-cap-5113fad9",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1525",
      "name": "Implant Internal Image",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "intg-cap-7a54b1a7"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1528",
      "name": "Steal Application Access Token",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "ephem-cap-5113fad9",
        "intg-cap-7a54b1a7",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1530",
      "name": "Data from Cloud Storage",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "conf-cap-01c47d42",
        "conf-cap-277b2364",
        "ephem-cap-5113fad9",
        "intg-cap-70ef26f7",
        "intg-cap-7a54b1a7",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1543",
      "name": "Create or Modify System Process",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "ephem-cap-5113fad9",
        "intg-cap-7a54b1a7",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1550",
      "name": "Use Alternate Authentication Material",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "conf-cap-1044dbb3",
        "ephem-cap-5113fad9",
        "intg-cap-7a54b1a7",
        "intg-cap-e88c8857",
        "intg-cap-ecebb879"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1552",
      "name": "Unsecured Credentials",
      "findings": 1,
      "mitigations": [
        "auth-cap-f01e6108",
        "conf-cap-01c47d42",
        "conf-cap-1044dbb3",
        "conf-cap-277b2364",
        "intg-cap-70ef26f7",
        "intg-cap-7a54b1a7"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1565",
      "name": "Data Manipulation",
      "findings": 1,
      "mitigations": [
        "conf-cap-01c47d42",
        "conf-cap-277b2364",
        "intg-cap-70ef26f7"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1577",
      "name": "Compromise Application Executable",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1634",
      "name": "Credentials from Password Store",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    }
  ],
  "masvs_coverage": [
    {
      "masvs_id": "MASVS-STORAGE-1",
      "name": "The app securely stores sensitive data.",
      "category": "MASVS-STORAGE",
      "category_title": "Storage",
      "finding_count": 3,
      "finding_ids": [
        "conf-205c53a5",
        "conf-7a74a4a0",
        "conf-a30cca33"
      ],
      "surfaces": [
        "code:Sources.App.AppDelegate.AppDelegate.setupFirebase:L1-L1@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
        "code:Sources.Shared.API.ServerManagerPersistence.ServerManagerKeychain:L6-L35@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
        "code:common...database.DatabaseModule.DatabaseModule.provideAppDatabase:L38-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
        "code:common...database.server.ServerSessionInfo.ServerSessionInfo:L1-L1@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea"
      ],
      "capability_count": 1,
      "capability_ids": [
        "conf-cap-01c47d42"
      ],
      "posture": "gapped_and_covered"
    },
    {
      "masvs_id": "MASVS-AUTH-2",
      "name": "The app performs local authentication securely according to the platform best practices.",
      "category": "MASVS-AUTH",
      "category_title": "Authentication and Authorization",
      "finding_count": 0,
      "finding_ids": [],
      "surfaces": [],
      "capability_count": 2,
      "capability_ids": [
        "auth-cap-42c6a13f",
        "ephem-cap-f5d582d0"
      ],
      "posture": "covered"
    },
    {
      "masvs_id": "MASVS-NETWORK-2",
      "name": "The app performs identity pinning for all remote endpoints under the developer's control.",
      "category": "MASVS-NETWORK",
      "category_title": "Network Communication",
      "finding_count": 2,
      "finding_ids": [
        "auth-1787eae1",
        "conf-2029ce78"
      ],
      "surfaces": [
        "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-PLATFORM-2",
      "name": "The app uses WebViews securely.",
      "category": "MASVS-PLATFORM",
      "category_title": "Platform Interaction",
      "finding_count": 2,
      "finding_ids": [
        "auth-ea69d3a2",
        "conf-3060c50e"
      ],
      "surfaces": [
        "## Get access token, lines 44-55",
        "#get-access-token, line 19",
        "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
        "code:src.external_app.external_messaging.ExternalMessaging._sendExternal:L491-L505@505966e84f3a90347c66261592908a02a4118189",
        "code:src.external_app.external_messaging.ExternalMessaging.fireMessage:L381-L428@505966e84f3a90347c66261592908a02a4118189"
      ],
      "capability_count": 0,
      "capability_ids": [],
      "posture": "gapped"
    },
    {
      "masvs_id": "MASVS-AUTH-1",
      "name": "The app uses secure authentication and authorization protocols and follows the relevant best practices.",
      "category": "MASVS-AUTH",
      "category_title": "Authentication and Authorization",
      "finding_count": 1,
      "finding_ids": [
        "auth-3dbf15e7"
      ],
      "surfaces": [
        "#clients, lines 14-23 (client_id is the website; custom-scheme redirect)",
        "#token / Authorization code, lines 72-82"
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
      "finding_count": 0,
      "finding_ids": [],
      "surfaces": [],
      "capability_count": 1,
      "capability_ids": [
        "conf-cap-01c47d42"
      ],
      "posture": "covered"
    },
    {
      "masvs_id": "MASVS-RESILIENCE-4",
      "name": "The app implements anti-dynamic analysis techniques.",
      "category": "MASVS-RESILIENCE",
      "category_title": "Resilience Against Reverse Engineering and Tampering",
      "finding_count": 1,
      "finding_ids": [
        "auth-3794d338"
      ],
      "surfaces": [
        "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
        "code:common...data.keychain.KeyStoreRepositoryImpl:L108-L112@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
        "run-config crown_jewels EXCLUDED note (attestation_tokens_and_jwts absent)"
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
        "conf-205c53a5"
      ],
      "surfaces": [
        "code:common...database.DatabaseModule.DatabaseModule.provideAppDatabase:L38-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
        "code:common...database.server.ServerSessionInfo.ServerSessionInfo:L1-L1@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea"
      ]
    },
    {
      "maswe_id": "MASWE-0040",
      "name": "Insecure Authentication in WebViews",
      "category": "MASVS-AUTH",
      "status": "placeholder",
      "parent_masvs": [
        "MASVS-AUTH-1",
        "MASVS-PLATFORM-2"
      ],
      "finding_count": 1,
      "finding_ids": [
        "auth-3dbf15e7"
      ],
      "surfaces": [
        "#clients, lines 14-23 (client_id is the website; custom-scheme redirect)",
        "#token / Authorization code, lines 72-82"
      ]
    },
    {
      "maswe_id": "MASWE-0052",
      "name": "Insecure Certificate Validation",
      "category": "MASVS-NETWORK",
      "status": "new",
      "parent_masvs": [
        "MASVS-NETWORK-1"
      ],
      "finding_count": 1,
      "finding_ids": [
        "auth-1787eae1"
      ],
      "surfaces": [
        "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea"
      ]
    },
    {
      "maswe_id": "MASWE-0068",
      "name": "JavaScript Bridges in WebViews",
      "category": "MASVS-PLATFORM",
      "status": "placeholder",
      "parent_masvs": [
        "MASVS-PLATFORM-2",
        "MASVS-STORAGE-2"
      ],
      "finding_count": 1,
      "finding_ids": [
        "conf-3060c50e"
      ],
      "surfaces": [
        "## Get access token, lines 44-55",
        "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
        "code:src.external_app.external_messaging.ExternalMessaging._sendExternal:L491-L505@505966e84f3a90347c66261592908a02a4118189"
      ]
    },
    {
      "maswe_id": "MASWE-0072",
      "name": "Universal XSS",
      "category": "MASVS-PLATFORM",
      "status": "placeholder",
      "parent_masvs": [
        "MASVS-PLATFORM-2",
        "MASVS-CODE-4"
      ],
      "finding_count": 1,
      "finding_ids": [
        "auth-ea69d3a2"
      ],
      "surfaces": [
        "#get-access-token, line 19",
        "code:Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage:L37-L76@8f26f9e7d5bb9ca7d55d563ceb685ed77a76a740",
        "code:src.external_app.external_messaging.ExternalMessaging.fireMessage:L381-L428@505966e84f3a90347c66261592908a02a4118189"
      ]
    },
    {
      "maswe_id": "MASWE-0099",
      "name": "Emulator Detection Not Implemented",
      "category": "MASVS-RESILIENCE",
      "status": "placeholder",
      "parent_masvs": [
        "MASVS-RESILIENCE-1"
      ],
      "finding_count": 1,
      "finding_ids": [
        "auth-3794d338"
      ],
      "surfaces": [
        "code:common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory:L24-L43@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
        "code:common...data.keychain.KeyStoreRepositoryImpl:L108-L112@bf8215602c19f20f4abf9c1dbfcbc2a3e4cf1bea",
        "run-config crown_jewels EXCLUDED note (attestation_tokens_and_jwts absent)"
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
        "component": ".storage config_entries + OAuth2 token storage (integration secret vault)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": ".storage/auth + auth_provider.homeassistant (user credentials store)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "00-SYSTEM-OVERVIEW.md",
        "cells": {
          "conf": "silent",
          "intg": "gapped",
          "avail": "silent",
          "dist": "both",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "APNS / FCM push providers",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Add-on containers (third-party Docker images w/ config.yaml role/AppArmor)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Android Companion app (Kotlin, WebView, Keystore, FCM)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Android hardware-backed Keystore (mTLS client-cert private key)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Container base images (alpine/debian) + wheels/npm supply chain",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Core REST API (/api/, port 8123)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Core WebSocket API (/api/websocket)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Core auth subsystem (providers, users, groups, tokens)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Core integration runtime (2000+ in-process integrations)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Core user permission policy engine",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Docker socket / host-root control plane (/run/docker.sock)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "External devices / cloud services reached by integrations (outbound)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "HAOS appliance image (Buildroot operating-system)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Home Assistant Core (Python asyncio app)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "JS external-auth bridge (window.externalAppV2 / webkit.messageHandlers)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Lit/TS web frontend SPA",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Mobile app release signing identity (Android keystore/cert, iOS provisioning)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Nabu Casa cloud relay / cloudhook (remote access + cloudhook_url)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "On-device location/entity cache (Android Room location_history / iOS AppEntityRegistry)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "On-device session/refresh token store (iOS Keychain / Android ServerSessionInfo)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Privileged Supervisor API (http://supervisor/)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Recorder history DB (SQLite/MariaDB/PostgreSQL)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Refresh-token / JWT signing key store (per-refresh-token jwt_key)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Reverse-proxy / internet edge to Core (port 8123)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Supervisor backup archive store (full/partial snapshots)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Supervisor ingress proxy (X-Remote-User-* header injection)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "Supervisor service (add-on lifecycle, ingress, backups, Core mgmt)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "api/native-app/sending-data.md",
        "cells": {
          "conf": "silent",
          "intg": "gapped",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "api/native-app/setup.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "gapped",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "api/rest.md",
        "cells": {
          "conf": "gapped",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "gapped",
          "immut": "silent"
        }
      },
      {
        "component": "architecture/adr/0018-supported-databases.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "gapped",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "auth/auth_api.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "both",
          "auth": "gapped",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "auth/auth_auth_module.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "gapped",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "auth/auth_index.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "gapped",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "auth/frontend-external-authentication.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "gapped",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "code-evidence-index.yaml",
        "cells": {
          "conf": "both",
          "intg": "both",
          "avail": "both",
          "dist": "covered",
          "resil": "covered",
          "ephem": "silent",
          "auth": "both",
          "nonrep": "both",
          "immut": "both"
        }
      },
      {
        "component": "configuration.yaml + .storage config directory",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "iOS Companion app (Swift, WKWebView, Keychain, APNS)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "iOS-bundled GoogleService-Info plist (Firebase config secrets)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "infra/addon-mosquitto-build.yaml",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "gapped",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "gapped"
        }
      },
      {
        "component": "infra/core-Dockerfile",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "covered",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "covered"
        }
      },
      {
        "component": "infra/supervisor-Dockerfile",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "gapped",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "mDNS / Zeroconf LAN discovery surface (_home-assistant._tcp.local.)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "mobile-apps-fcm-push relay (Firebase Cloud Functions)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "mobile/supervisor-apps-security.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "gapped",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "mobile_app integration backend (registrations + webhook in Core)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "org/SECURITY.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "gapped",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "os-agent (Go D-Bus host daemon)",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      },
      {
        "component": "repos/supervisor-README.md",
        "cells": {
          "conf": "silent",
          "intg": "silent",
          "avail": "gapped",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "silent",
          "immut": "silent"
        }
      }
    ]
  },
  "attack_paths": null,
  "c4_model": {
    "present": true,
    "nodes": [
      {
        "id": "c4-00ca2e01",
        "label": "docker-base",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:docker-base"
        }
      },
      {
        "id": "c4-07930fa1",
        "label": "Sources.Shared.API.ServerManagerPersistence.ServerManagerKey",
        "type": "code",
        "parent": "c4-208b6a15",
        "badge": 2,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "class",
        "provenance": {
          "source": "code_evidence",
          "locator": "Sources.Shared.API.ServerManagerPersistence.ServerManagerKeychain",
          "repo": "iOS",
          "first_finding_id": "conf-a30cca33"
        }
      },
      {
        "id": "c4-07f5a3e6",
        "label": "plugin-dns",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:plugin-dns"
        }
      },
      {
        "id": "c4-11fbf1b9",
        "label": "system.system.AddSSHAuthKey",
        "type": "code",
        "parent": "c4-d304503a",
        "badge": 3,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "system.system.AddSSHAuthKey",
          "repo": "os-agent",
          "first_finding_id": "auth-6924f467"
        }
      },
      {
        "id": "c4-2085cc3a",
        "label": "Long-Lived Access Token holder",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "human_role",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#rest-api, line 15 (Long-Lived Access Token from /profile)"
        }
      },
      {
        "id": "c4-208b6a15",
        "label": "iOS",
        "type": "container",
        "parent": null,
        "badge": 7,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:iOS",
          "first_finding_id": "auth-ea69d3a2"
        }
      },
      {
        "id": "c4-227eeec3",
        "label": "homeassistant.auth.AuthManager.async_create_access_token",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 3,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.AuthManager.async_create_access_token",
          "repo": "core",
          "first_finding_id": "avail-235dacf0"
        }
      },
      {
        "id": "c4-22aa1f41",
        "label": "companion.home-assistant",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:companion.home-assistant"
        }
      },
      {
        "id": "c4-24c82330",
        "label": "android",
        "type": "container",
        "parent": null,
        "badge": 6,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:android",
          "first_finding_id": "auth-1787eae1"
        }
      },
      {
        "id": "c4-26ccbc53",
        "label": "homeassistant.components.http.auth.async_setup_auth.auth_mid",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.http.auth.async_setup_auth.auth_middleware",
          "repo": "core"
        }
      },
      {
        "id": "c4-2b1193ee",
        "label": "homeassistant.auth.providers.homeassistant.Data.hash_passwor",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": null,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.providers.homeassistant.Data.hash_password",
          "repo": "core"
        }
      },
      {
        "id": "c4-30b671c0",
        "label": "plugin-audio",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:plugin-audio"
        }
      },
      {
        "id": "c4-35f5b73c",
        "label": "homeassistant.auth.providers.homeassistant.Data.validate_log",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": null,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.providers.homeassistant.Data.validate_login",
          "repo": "core"
        }
      },
      {
        "id": "c4-37c54a76",
        "label": "IndieAuth OAuth2 client (client_id IS the redirect URL no se",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_party",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#authenticating-the-user, lines 8-11 (IndieAuth OAuth2)"
        }
      },
      {
        "id": "c4-380ece15",
        "label": "homeassistant.helpers.storage.Store._write_prepared_data",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 3,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.helpers.storage.Store._write_prepared_data",
          "repo": "core",
          "first_finding_id": "dist-69bbaf5c"
        }
      },
      {
        "id": "c4-3ace82b7",
        "label": "supervisor.api.middleware.security.SecurityMiddleware.token_",
        "type": "code",
        "parent": "c4-f3adbac9",
        "badge": 3,
        "capability_badge": 3,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "supervisor.api.middleware.security.SecurityMiddleware.token_validation",
          "repo": "supervisor",
          "first_finding_id": "merged-1119b0be"
        }
      },
      {
        "id": "c4-3b7aa86f",
        "label": "functions.handlers.handleRequest",
        "type": "code",
        "parent": "c4-804f909b",
        "badge": 2,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "functions.handlers.handleRequest",
          "repo": "mobile-apps-fcm-push",
          "first_finding_id": "auth-23048c0c"
        }
      },
      {
        "id": "c4-3bfb10f9",
        "label": "Trusted-networks / command-line / legacy auth provider princ",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "human_role",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#authentication-authorization-model, lines 67-69"
        }
      },
      {
        "id": "c4-3d5dca87",
        "label": "Home Assistant",
        "type": "system",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "software_system",
        "provenance": {
          "source": "run_config",
          "locator": "subject"
        }
      },
      {
        "id": "c4-3ebb6da2",
        "label": "common...data.keychain.KeyStoreRepositoryImpl",
        "type": "code",
        "parent": "c4-24c82330",
        "badge": 1,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "class",
        "provenance": {
          "source": "code_evidence",
          "locator": "common...data.keychain.KeyStoreRepositoryImpl",
          "repo": "android",
          "first_finding_id": "auth-3794d338"
        }
      },
      {
        "id": "c4-43797bde",
        "label": "plugin-observer",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:plugin-observer"
        }
      },
      {
        "id": "c4-442e5014",
        "label": "common...database.DatabaseModule.DatabaseModule.provideAppDa",
        "type": "code",
        "parent": "c4-24c82330",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "common...database.DatabaseModule.DatabaseModule.provideAppDatabase",
          "repo": "android",
          "first_finding_id": "conf-205c53a5"
        }
      },
      {
        "id": "c4-5c0062f1",
        "label": "homeassistant.components.mobile_app.webhook.handle_webhook",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 7,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.mobile_app.webhook.handle_webhook",
          "repo": "core",
          "first_finding_id": "auth-3f2314a4"
        }
      },
      {
        "id": "c4-5cb67c4d",
        "label": "plugin-multicast",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:plugin-multicast"
        }
      },
      {
        "id": "c4-5dcd06fe",
        "label": "common...database.server.ServerSessionInfo.ServerSessionInfo",
        "type": "code",
        "parent": "c4-24c82330",
        "badge": 3,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "class",
        "provenance": {
          "source": "code_evidence",
          "locator": "common...database.server.ServerSessionInfo.ServerSessionInfo",
          "repo": "android",
          "first_finding_id": "conf-205c53a5"
        }
      },
      {
        "id": "c4-5eb43478",
        "label": "addons",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:addons"
        }
      },
      {
        "id": "c4-6877897a",
        "label": "operating-system",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:operating-system"
        }
      },
      {
        "id": "c4-69f67c4e",
        "label": "Registered mobile device (webhook_id / cloudhook holder)",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_party",
        "provenance": {
          "source": "asset_inventory",
          "locator": "registration response, lines 74-79 (webhook_id, secret)"
        }
      },
      {
        "id": "c4-6a7f39f8",
        "label": "supervisor.api.middleware.security.SecurityMiddleware.ADDONS",
        "type": "code",
        "parent": "c4-f3adbac9",
        "badge": null,
        "capability_badge": 1,
        "analysis_state": "analyzed",
        "kind": "module",
        "provenance": {
          "source": "code_evidence",
          "locator": "supervisor.api.middleware.security.SecurityMiddleware.ADDONS_ROLE_ACCESS",
          "repo": "supervisor"
        }
      },
      {
        "id": "c4-6b059adc",
        "label": "External devices / cloud services reached by integrations (o",
        "type": "external_system",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_dependency",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#trust-boundaries item 6 (Core integration -> external device/cloud; SSRF)"
        }
      },
      {
        "id": "c4-714c61de",
        "label": "APNS / FCM push providers",
        "type": "external_system",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_dependency",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#trust-boundaries item 7 (HA instance <-> push relay <-> APNS/FCM)"
        }
      },
      {
        "id": "c4-7978cb3b",
        "label": "Non-admin / low-priv user (group-scoped permission policy)",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "human_role",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#permissions, lines 9-12 (group membership grants permissions)"
        }
      },
      {
        "id": "c4-7bf521e1",
        "label": "Container base images (alpine/debian) wheels/npm supply chai",
        "type": "external_system",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_dependency",
        "provenance": {
          "source": "asset_inventory",
          "locator": "line 1 (BUILD_FROM ghcr.io base-python image) + wheels mount lines 36-48"
        }
      },
      {
        "id": "c4-7e096663",
        "label": "homeassistant.auth.permissions.util.compile_policy",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 2,
        "capability_badge": 3,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.permissions.util.compile_policy",
          "repo": "core",
          "first_finding_id": "merged-1119b0be"
        }
      },
      {
        "id": "c4-7f55d47c",
        "label": "mobile-apps-fcm-push relay (Firebase Cloud Functions)",
        "type": "external_system",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_dependency",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#mobile-apps-fcm-push, lines 1-2, 42-47 (firebase deploy, push relay)"
        }
      },
      {
        "id": "c4-804f909b",
        "label": "mobile-apps-fcm-push",
        "type": "container",
        "parent": null,
        "badge": 4,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:mobile-apps-fcm-push",
          "first_finding_id": "auth-23048c0c"
        }
      },
      {
        "id": "c4-8116f952",
        "label": "Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessa",
        "type": "code",
        "parent": "c4-208b6a15",
        "badge": 4,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage",
          "repo": "iOS",
          "first_finding_id": "auth-ea69d3a2"
        }
      },
      {
        "id": "c4-85956d05",
        "label": "home-assistant.io",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:home-assistant.io"
        }
      },
      {
        "id": "c4-8bd848dd",
        "label": "plugin-cli",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:plugin-cli"
        }
      },
      {
        "id": "c4-8e8627db",
        "label": "supervisor.api.ingress._init_header",
        "type": "code",
        "parent": "c4-f3adbac9",
        "badge": 1,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "supervisor.api.ingress._init_header",
          "repo": "supervisor",
          "first_finding_id": "auth-4e7d1059"
        }
      },
      {
        "id": "c4-93744d34",
        "label": "homeassistant.auth.models.RefreshToken",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 4,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "class",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.models.RefreshToken",
          "repo": "core",
          "first_finding_id": "ephem-9915ab91"
        }
      },
      {
        "id": "c4-93b2d512",
        "label": "homeassistant.auth.AuthManager.async_validate_access_token",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 1,
        "capability_badge": 3,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.AuthManager.async_validate_access_token",
          "repo": "core",
          "first_finding_id": "ephem-f19f24f9"
        }
      },
      {
        "id": "c4-975cfbd4",
        "label": "wheels",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:wheels"
        }
      },
      {
        "id": "c4-9904ee7d",
        "label": "Third-party integration / device principal (untrusted device",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_party",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#trust-boundaries item 6 (untrusted device/cloud responses)"
        }
      },
      {
        "id": "c4-9a8a0efa",
        "label": "Owner user (onboarding user all permissions)",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "human_role",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#owner, lines 27-29 (always all permissions)"
        }
      },
      {
        "id": "c4-a889fd4f",
        "label": "homeassistant.auth.permissions._OwnerPermissions",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 3,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "class",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.permissions._OwnerPermissions",
          "repo": "core",
          "first_finding_id": "auth-7162fd48"
        }
      },
      {
        "id": "c4-ab1ad354",
        "label": "Nabu Casa cloud relay / cloudhook (remote access cloudhook_u",
        "type": "external_system",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "external_dependency",
        "provenance": {
          "source": "asset_inventory",
          "locator": "registration response, lines 74-79 (cloudhook_url, remote_ui_url)"
        }
      },
      {
        "id": "c4-abf37f83",
        "label": "homeassistant.components.api.APITemplateView.post",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 4,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "route",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.api.APITemplateView.post",
          "repo": "core",
          "first_finding_id": "avail-4be2dd70"
        }
      },
      {
        "id": "c4-ae12fda6",
        "label": "core",
        "type": "container",
        "parent": null,
        "badge": 22,
        "capability_badge": 15,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:core",
          "first_finding_id": "auth-3f2314a4"
        }
      },
      {
        "id": "c4-b46f0cb3",
        "label": "homeassistant.components.api.APIEntityStateView.get",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 2,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "route",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.api.APIEntityStateView.get",
          "repo": "core",
          "first_finding_id": "conf-ef49b4b0"
        }
      },
      {
        "id": "c4-b600dc37",
        "label": "cli",
        "type": "container",
        "parent": null,
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:cli",
          "first_finding_id": "auth-23048c0c"
        }
      },
      {
        "id": "c4-b6a8c480",
        "label": "homeassistant.helpers.recorder.session_scope",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 6,
        "capability_badge": 1,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.helpers.recorder.session_scope",
          "repo": "core",
          "first_finding_id": "avail-235dacf0"
        }
      },
      {
        "id": "c4-bc1e61b2",
        "label": "docker",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:docker"
        }
      },
      {
        "id": "c4-c0ed4020",
        "label": "client.helper.URLHelper",
        "type": "code",
        "parent": "c4-b600dc37",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "client.helper.URLHelper",
          "repo": "cli",
          "first_finding_id": "auth-23048c0c"
        }
      },
      {
        "id": "c4-c16a99ce",
        "label": "src.external_app.external_messaging.ExternalMessaging.fireMe",
        "type": "code",
        "parent": "c4-ff4e5342",
        "badge": 2,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "src.external_app.external_messaging.ExternalMessaging.fireMessage",
          "repo": "frontend",
          "first_finding_id": "auth-ea69d3a2"
        }
      },
      {
        "id": "c4-caa451ad",
        "label": "supervisor.backups.backup.Backup.set_password",
        "type": "code",
        "parent": "c4-f3adbac9",
        "badge": 3,
        "capability_badge": 1,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "supervisor.backups.backup.Backup.set_password",
          "repo": "supervisor",
          "first_finding_id": "avail-5af6fee5"
        }
      },
      {
        "id": "c4-cc1569b3",
        "label": "home-assistant-js-websocket",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:home-assistant-js-websocket"
        }
      },
      {
        "id": "c4-cdad5cce",
        "label": "supervisor.docker.manager.DockerAPI.container_run_inside",
        "type": "code",
        "parent": "c4-f3adbac9",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "supervisor.docker.manager.DockerAPI.container_run_inside",
          "repo": "supervisor",
          "first_finding_id": "merged-66801b1b"
        }
      },
      {
        "id": "c4-ceca8483",
        "label": "developers.home-assistant",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:developers.home-assistant"
        }
      },
      {
        "id": "c4-d0f7c0e3",
        "label": "homeassistant.components.websocket_api.auth.AuthPhase.async_",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 3,
        "capability_badge": 5,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.websocket_api.auth.AuthPhase.async_handle",
          "repo": "core",
          "first_finding_id": "avail-4be2dd70"
        }
      },
      {
        "id": "c4-d304503a",
        "label": "os-agent",
        "type": "container",
        "parent": null,
        "badge": 4,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:os-agent",
          "first_finding_id": "auth-6924f467"
        }
      },
      {
        "id": "c4-d3b30ed4",
        "label": "architecture",
        "type": "container",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "not_analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:architecture"
        }
      },
      {
        "id": "c4-d439ef43",
        "label": "Ingress-authenticated user (X-Remote-User-Id/Name headers)",
        "type": "person",
        "parent": null,
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "human_role",
        "provenance": {
          "source": "asset_inventory",
          "locator": "#authenticating-a-user-when-using-ingress, lines 40-48"
        }
      },
      {
        "id": "c4-d61da7fa",
        "label": "homeassistant.components.mobile_app.http_api.RegistrationsVi",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 2,
        "capability_badge": 2,
        "analysis_state": "analyzed",
        "kind": "route",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.mobile_app.http_api.RegistrationsView.post",
          "repo": "core",
          "first_finding_id": "auth-3f2314a4"
        }
      },
      {
        "id": "c4-d77ad419",
        "label": "mosquitto.config.yaml",
        "type": "code",
        "parent": "c4-5eb43478",
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "module",
        "provenance": {
          "source": "code_evidence",
          "locator": "mosquitto.config.yaml",
          "repo": "addons"
        }
      },
      {
        "id": "c4-d844acf8",
        "label": "src.external_app.external_messaging.ExternalMessaging._sendE",
        "type": "code",
        "parent": "c4-ff4e5342",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "src.external_app.external_messaging.ExternalMessaging._sendExternal",
          "repo": "frontend",
          "first_finding_id": "conf-3060c50e"
        }
      },
      {
        "id": "c4-ea3b1062",
        "label": "common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocket",
        "type": "code",
        "parent": "c4-24c82330",
        "badge": 4,
        "capability_badge": 1,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory",
          "repo": "android",
          "first_finding_id": "auth-1787eae1"
        }
      },
      {
        "id": "c4-eab86774",
        "label": "system.system.ScheduleWipeDevice",
        "type": "code",
        "parent": "c4-d304503a",
        "badge": 4,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "system.system.ScheduleWipeDevice",
          "repo": "os-agent",
          "first_finding_id": "auth-6924f467"
        }
      },
      {
        "id": "c4-ee82d1c7",
        "label": "app...launch.LaunchActivity.LaunchActivity",
        "type": "code",
        "parent": "c4-24c82330",
        "badge": null,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "class",
        "provenance": {
          "source": "code_evidence",
          "locator": "app...launch.LaunchActivity.LaunchActivity",
          "repo": "android"
        }
      },
      {
        "id": "c4-f11bfdd4",
        "label": "Sources.App.AppDelegate.AppDelegate.setupFirebase",
        "type": "code",
        "parent": "c4-208b6a15",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "Sources.App.AppDelegate.AppDelegate.setupFirebase",
          "repo": "iOS",
          "first_finding_id": "conf-7a74a4a0"
        }
      },
      {
        "id": "c4-f3adbac9",
        "label": "supervisor",
        "type": "container",
        "parent": null,
        "badge": 6,
        "capability_badge": 5,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:supervisor",
          "first_finding_id": "auth-4e7d1059"
        }
      },
      {
        "id": "c4-f4fe8030",
        "label": "supervisor.docker.manager.DockerAPI.__init__",
        "type": "code",
        "parent": "c4-f3adbac9",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "supervisor.docker.manager.DockerAPI.__init__",
          "repo": "supervisor",
          "first_finding_id": "dist-d08ed969"
        }
      },
      {
        "id": "c4-fd7e1885",
        "label": "homeassistant.auth.permissions.filter_entity_ids_by_permissi",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 1,
        "capability_badge": 1,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.auth.permissions.filter_entity_ids_by_permission",
          "repo": "core",
          "first_finding_id": "merged-66801b1b"
        }
      },
      {
        "id": "c4-fe030826",
        "label": "homeassistant.components.mobile_app.webhook.webhook_call_ser",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 6,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "function",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.mobile_app.webhook.webhook_call_service",
          "repo": "core",
          "first_finding_id": "avail-754cfc01"
        }
      },
      {
        "id": "c4-fe18ba53",
        "label": "__route__POST__/api/sendPushNotification",
        "type": "code",
        "parent": "c4-804f909b",
        "badge": 2,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "route",
        "provenance": {
          "source": "code_evidence",
          "locator": "__route__POST__/api/sendPushNotification",
          "repo": "mobile-apps-fcm-push",
          "first_finding_id": "avail-a2cfd41c"
        }
      },
      {
        "id": "c4-fe67977e",
        "label": "homeassistant.components.api.APIEntityStateView.post",
        "type": "code",
        "parent": "c4-ae12fda6",
        "badge": 1,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "route",
        "provenance": {
          "source": "code_evidence",
          "locator": "homeassistant.components.api.APIEntityStateView.post",
          "repo": "core",
          "first_finding_id": "merged-66801b1b"
        }
      },
      {
        "id": "c4-ff4e5342",
        "label": "frontend",
        "type": "container",
        "parent": null,
        "badge": 3,
        "capability_badge": 0,
        "analysis_state": "analyzed",
        "kind": "service",
        "provenance": {
          "source": "code_evidence",
          "locator": "repos[]:frontend",
          "first_finding_id": "auth-ea69d3a2"
        }
      }
    ],
    "edges": [
      {
        "id": "c4e-14e42e27",
        "source": "c4-f3adbac9",
        "target": "c4-ae12fda6",
        "label": "CROSS_HTTP_CALLS: Supervisor POSTs api_url /auth/token and c",
        "machine_extracted": false
      },
      {
        "id": "c4e-1892f066",
        "source": "c4-b600dc37",
        "target": "c4-f3adbac9",
        "label": "(unnamed)",
        "machine_extracted": false
      },
      {
        "id": "c4e-50e1a463",
        "source": "c4-ae12fda6",
        "target": "c4-804f909b",
        "label": "CROSS_HTTP_CALLS: Core notify pushes to the FCM push-relay C",
        "machine_extracted": false
      },
      {
        "id": "c4e-a4678462",
        "source": "c4-f3adbac9",
        "target": "c4-d304503a",
        "label": "CROSS_CHANNEL: Supervisor calls os-agent host methods over t",
        "machine_extracted": false
      },
      {
        "id": "c4e-c1d084fd",
        "source": "c4-ff4e5342",
        "target": "c4-ae12fda6",
        "label": "CROSS_HTTP_CALLS: iOS/Android Companion WebView loads calls ",
        "machine_extracted": false
      }
    ],
    "unlocalized_findings": 10,
    "not_analyzed_count": 14,
    "levels_present": [
      "system",
      "person",
      "external_system",
      "container",
      "code"
    ],
    "finding_to_c4": {
      "avail-235dacf0": "c4-b6a8c480",
      "avail-4be2dd70": "c4-d0f7c0e3",
      "avail-5af6fee5": "c4-caa451ad",
      "avail-754cfc01": "c4-5c0062f1",
      "avail-a292763c": "c4-5c0062f1",
      "avail-a2cfd41c": "c4-fe18ba53",
      "conf-2029ce78": "c4-ea3b1062",
      "conf-205c53a5": "c4-442e5014",
      "conf-3060c50e": "c4-d844acf8",
      "conf-7a74a4a0": "c4-f11bfdd4",
      "conf-a30cca33": "c4-07930fa1",
      "conf-ef49b4b0": "c4-b46f0cb3",
      "intg-8b158cfe": "c4-abf37f83",
      "dist-66e3e208": "c4-b6a8c480",
      "dist-69bbaf5c": "c4-380ece15",
      "dist-b98dc00a": "c4-b6a8c480",
      "dist-d08ed969": "c4-f4fe8030",
      "ephem-053957f3": "c4-d61da7fa",
      "ephem-9915ab91": "c4-93744d34",
      "ephem-a879a34b": "c4-a889fd4f",
      "ephem-db8641be": "c4-d0f7c0e3",
      "ephem-f19f24f9": "c4-93744d34",
      "resil-93866115": "c4-7e096663",
      "auth-1787eae1": "c4-ea3b1062",
      "auth-3794d338": "c4-3ebb6da2",
      "auth-3f2314a4": "c4-5c0062f1",
      "auth-4e7d1059": "c4-8e8627db",
      "auth-6924f467": "c4-11fbf1b9",
      "auth-7162fd48": "c4-a889fd4f",
      "auth-ea69d3a2": "c4-8116f952",
      "nonrep-af1c55d3": "c4-fe030826",
      "merged-66801b1b": "c4-fe67977e",
      "merged-a49cb674": "c4-caa451ad",
      "merged-0ccd3ea6": "c4-b6a8c480",
      "merged-1119b0be": "c4-3ace82b7"
    },
    "asset_to_c4": {}
  },
  "next_steps": [],
  "taxonomy": {
    "AC-12": {
      "family": "NIST 800-53r5",
      "title": "Session Termination"
    },
    "AC-12(1)": {
      "family": "NIST 800-53r5",
      "title": "Session Termination | User-initiated Logouts"
    },
    "AC-2": {
      "family": "NIST 800-53r5",
      "title": "Account Management"
    },
    "AC-2(2)": {
      "family": "NIST 800-53r5",
      "title": "Account Management | Automated Temporary and Emergency Account Management"
    },
    "AC-2(3)": {
      "family": "NIST 800-53r5",
      "title": "Account Management | Disable Accounts"
    },
    "AC-24": {
      "family": "NIST 800-53r5",
      "title": "Access Control Decisions"
    },
    "AC-3": {
      "family": "NIST 800-53r5",
      "title": "Access Enforcement"
    },
    "AC-3(7)": {
      "family": "NIST 800-53r5",
      "title": "Access Enforcement | Role-based Access Control"
    },
    "AC-4": {
      "family": "NIST 800-53r5",
      "title": "Information Flow Enforcement"
    },
    "AC-5": {
      "family": "NIST 800-53r5",
      "title": "Separation of Duties"
    },
    "AC-6": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege"
    },
    "AC-6(1)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Authorize Access to Security Functions"
    },
    "AC-6(2)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Non-privileged Access for Nonsecurity Functions"
    },
    "AC-6(5)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Privileged Accounts"
    },
    "AC-6(9)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Log Use of Privileged Functions"
    },
    "AU-10": {
      "family": "NIST 800-53r5",
      "title": "Non-repudiation"
    },
    "AU-10(1)": {
      "family": "NIST 800-53r5",
      "title": "Non-repudiation | Association of Identities"
    },
    "AU-11": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Retention"
    },
    "AU-12": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Generation"
    },
    "AU-12(1)": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Generation | System-wide and Time-correlated Audit Trail"
    },
    "AU-2": {
      "family": "NIST 800-53r5",
      "title": "Event Logging"
    },
    "AU-3": {
      "family": "NIST 800-53r5",
      "title": "Content of Audit Records"
    },
    "AU-3(1)": {
      "family": "NIST 800-53r5",
      "title": "Content of Audit Records | Additional Audit Information"
    },
    "AU-6": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Review, Analysis, and Reporting"
    },
    "AU-6(3)": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Review, Analysis, and Reporting | Correlate Audit Record Repositories"
    },
    "AU-8": {
      "family": "NIST 800-53r5",
      "title": "Time Stamps"
    },
    "AU-8(1)": {
      "family": "NIST 800-53r5",
      "title": "Time Stamps | Synchronization with Authoritative Time Source"
    },
    "AU-9": {
      "family": "NIST 800-53r5",
      "title": "Protection of Audit Information"
    },
    "AU-9(2)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Audit Information | Store on Separate Physical Systems or Components"
    },
    "AU-9(3)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Audit Information | Cryptographic Protection"
    },
    "AU-9(4)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Audit Information | Access by Subset of Privileged Users"
    },
    "AU-9(6)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Audit Information | Read-only Access"
    },
    "CM-2": {
      "family": "NIST 800-53r5",
      "title": "Baseline Configuration"
    },
    "CM-2(2)": {
      "family": "NIST 800-53r5",
      "title": "Baseline Configuration | Automation Support for Accuracy and Currency"
    },
    "CM-2(3)": {
      "family": "NIST 800-53r5",
      "title": "Baseline Configuration | Retention of Previous Configurations"
    },
    "CM-3": {
      "family": "NIST 800-53r5",
      "title": "Configuration Change Control"
    },
    "CM-3(1)": {
      "family": "NIST 800-53r5",
      "title": "Configuration Change Control | Automated Documentation, Notification, and Prohibition of Changes"
    },
    "CM-5": {
      "family": "NIST 800-53r5",
      "title": "Access Restrictions for Change"
    },
    "CM-6": {
      "family": "NIST 800-53r5",
      "title": "Configuration Settings"
    },
    "CM-8": {
      "family": "NIST 800-53r5",
      "title": "System Component Inventory"
    },
    "CP-10": {
      "family": "NIST 800-53r5",
      "title": "System Recovery and Reconstitution"
    },
    "CP-12": {
      "family": "NIST 800-53r5",
      "title": "Safe Mode"
    },
    "CP-13": {
      "family": "NIST 800-53r5",
      "title": "Alternative Security Mechanisms"
    },
    "CP-2": {
      "family": "NIST 800-53r5",
      "title": "Contingency Plan"
    },
    "CP-2(3)": {
      "family": "NIST 800-53r5",
      "title": "Contingency Plan | Resume Mission and Business Functions"
    },
    "CP-2(5)": {
      "family": "NIST 800-53r5",
      "title": "Contingency Plan | Continue Mission and Business Functions"
    },
    "CP-7": {
      "family": "NIST 800-53r5",
      "title": "Alternate Processing Site"
    },
    "CP-7(1)": {
      "family": "NIST 800-53r5",
      "title": "Alternate Processing Site | Separation from Primary Site"
    },
    "CP-9": {
      "family": "NIST 800-53r5",
      "title": "System Backup"
    },
    "CP-9(1)": {
      "family": "NIST 800-53r5",
      "title": "System Backup | Testing for Reliability and Integrity"
    },
    "CP-9(8)": {
      "family": "NIST 800-53r5",
      "title": "System Backup | Cryptographic Protection"
    },
    "IA-2": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users)"
    },
    "IA-2(1)": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users) | Multi-factor Authentication to Privileged Accounts"
    },
    "IA-2(2)": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users) | Multi-factor Authentication to Non-privileged Accounts"
    },
    "IA-2(8)": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users) | Access to Accounts — Replay Resistant"
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
    "IA-5(1)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | Password-based Authentication"
    },
    "IA-5(13)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | Expiration of Cached Authenticators"
    },
    "IA-5(2)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | Public Key-based Authentication"
    },
    "IA-5(7)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | No Embedded Unencrypted Static Authenticators"
    },
    "IA-7": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Module Authentication"
    },
    "IA-8": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Non-organizational Users)"
    },
    "IA-9": {
      "family": "NIST 800-53r5",
      "title": "Service Identification and Authentication"
    },
    "MP-4": {
      "family": "NIST 800-53r5",
      "title": "Media Storage"
    },
    "MP-5": {
      "family": "NIST 800-53r5",
      "title": "Media Transport"
    },
    "RA-3": {
      "family": "NIST 800-53r5",
      "title": "Risk Assessment"
    },
    "SA-15": {
      "family": "NIST 800-53r5",
      "title": "Development Process, Standards, and Tools"
    },
    "SA-15(7)": {
      "family": "NIST 800-53r5",
      "title": "Development Process, Standards, and Tools | Automated Vulnerability Analysis"
    },
    "SC-10": {
      "family": "NIST 800-53r5",
      "title": "Network Disconnect"
    },
    "SC-12": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management"
    },
    "SC-12(1)": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management | Availability"
    },
    "SC-12(3)": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management | Asymmetric Keys"
    },
    "SC-13": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Protection"
    },
    "SC-17": {
      "family": "NIST 800-53r5",
      "title": "Public Key Infrastructure Certificates"
    },
    "SC-18": {
      "family": "NIST 800-53r5",
      "title": "Mobile Code"
    },
    "SC-20": {
      "family": "NIST 800-53r5",
      "title": "Secure Name/Address Resolution Service (Authoritative Source)"
    },
    "SC-22": {
      "family": "NIST 800-53r5",
      "title": "Architecture and Provisioning for Name/Address Resolution Service"
    },
    "SC-23": {
      "family": "NIST 800-53r5",
      "title": "Session Authenticity"
    },
    "SC-23(3)": {
      "family": "NIST 800-53r5",
      "title": "Session Authenticity | Unique System-generated Session Identifiers"
    },
    "SC-24": {
      "family": "NIST 800-53r5",
      "title": "Fail in Known State"
    },
    "SC-28": {
      "family": "NIST 800-53r5",
      "title": "Protection of Information at Rest"
    },
    "SC-28(1)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Information at Rest | Cryptographic Protection"
    },
    "SC-36": {
      "family": "NIST 800-53r5",
      "title": "Distributed Processing and Storage"
    },
    "SC-36(1)": {
      "family": "NIST 800-53r5",
      "title": "Distributed Processing and Storage | Polling Techniques"
    },
    "SC-5": {
      "family": "NIST 800-53r5",
      "title": "Denial-of-service Protection"
    },
    "SC-5(1)": {
      "family": "NIST 800-53r5",
      "title": "Denial-of-service Protection | Restrict Ability to Attack Other Systems"
    },
    "SC-6": {
      "family": "NIST 800-53r5",
      "title": "Resource Availability"
    },
    "SC-7": {
      "family": "NIST 800-53r5",
      "title": "Boundary Protection"
    },
    "SC-7(21)": {
      "family": "NIST 800-53r5",
      "title": "Boundary Protection | Isolation of System Components"
    },
    "SC-7(5)": {
      "family": "NIST 800-53r5",
      "title": "Boundary Protection | Deny by Default — Allow by Exception"
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
    "SI-13": {
      "family": "NIST 800-53r5",
      "title": "Predictable Failure Prevention"
    },
    "SI-15": {
      "family": "NIST 800-53r5",
      "title": "Information Output Filtering"
    },
    "SI-17": {
      "family": "NIST 800-53r5",
      "title": "Fail-safe Procedures"
    },
    "SI-7": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity"
    },
    "SI-7(1)": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity | Integrity Checks"
    },
    "SI-7(6)": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity | Cryptographic Protection"
    },
    "SI-7(8)": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity | Auditing Capability for Significant Events"
    },
    "SR-11": {
      "family": "NIST 800-53r5",
      "title": "Component Authenticity"
    },
    "SR-3": {
      "family": "NIST 800-53r5",
      "title": "Supply Chain Controls and Processes"
    },
    "SR-4": {
      "family": "NIST 800-53r5",
      "title": "Provenance"
    },
    "SR-4(3)": {
      "family": "NIST 800-53r5",
      "title": "Provenance | Validate as Genuine and Not Altered"
    },
    "SR-4(4)": {
      "family": "NIST 800-53r5",
      "title": "Provenance | Supply Chain Integrity — Pedigree"
    },
    "T1005": {
      "family": "MITRE ATT&CK",
      "title": "Data from Local System",
      "url": "https://attack.mitre.org/techniques/T1005/"
    },
    "T1040": {
      "family": "MITRE ATT&CK",
      "title": "Network Sniffing",
      "url": "https://attack.mitre.org/techniques/T1040/"
    },
    "T1070": {
      "family": "MITRE ATT&CK",
      "title": "Indicator Removal",
      "url": "https://attack.mitre.org/techniques/T1070/"
    },
    "T1078": {
      "family": "MITRE ATT&CK",
      "title": "Valid Accounts",
      "url": "https://attack.mitre.org/techniques/T1078/"
    },
    "T1098": {
      "family": "MITRE ATT&CK",
      "title": "Account Manipulation",
      "url": "https://attack.mitre.org/techniques/T1098/"
    },
    "T1110": {
      "family": "MITRE ATT&CK",
      "title": "Brute Force",
      "url": "https://attack.mitre.org/techniques/T1110/"
    },
    "T1190": {
      "family": "MITRE ATT&CK",
      "title": "Exploit Public-Facing Application",
      "url": "https://attack.mitre.org/techniques/T1190/"
    },
    "T1195": {
      "family": "MITRE ATT&CK",
      "title": "Supply Chain Compromise",
      "url": "https://attack.mitre.org/techniques/T1195/"
    },
    "T1213": {
      "family": "MITRE ATT&CK",
      "title": "Data from Information Repositories",
      "url": "https://attack.mitre.org/techniques/T1213/"
    },
    "T1409": {
      "family": "MITRE ATT&CK",
      "title": "Stored Application Data",
      "url": "https://attack.mitre.org/techniques/T1409/"
    },
    "T1417": {
      "family": "MITRE ATT&CK",
      "title": "Input Capture",
      "url": "https://attack.mitre.org/techniques/T1417/"
    },
    "T1490": {
      "family": "MITRE ATT&CK",
      "title": "Inhibit System Recovery",
      "url": "https://attack.mitre.org/techniques/T1490/"
    },
    "T1499": {
      "family": "MITRE ATT&CK",
      "title": "Endpoint Denial of Service",
      "url": "https://attack.mitre.org/techniques/T1499/"
    },
    "T1525": {
      "family": "MITRE ATT&CK",
      "title": "Implant Internal Image",
      "url": "https://attack.mitre.org/techniques/T1525/"
    },
    "T1528": {
      "family": "MITRE ATT&CK",
      "title": "Steal Application Access Token",
      "url": "https://attack.mitre.org/techniques/T1528/"
    },
    "T1530": {
      "family": "MITRE ATT&CK",
      "title": "Data from Cloud Storage",
      "url": "https://attack.mitre.org/techniques/T1530/"
    },
    "T1543": {
      "family": "MITRE ATT&CK",
      "title": "Create or Modify System Process",
      "url": "https://attack.mitre.org/techniques/T1543/"
    },
    "T1550": {
      "family": "MITRE ATT&CK",
      "title": "Use Alternate Authentication Material",
      "url": "https://attack.mitre.org/techniques/T1550/"
    },
    "T1552": {
      "family": "MITRE ATT&CK",
      "title": "Unsecured Credentials",
      "url": "https://attack.mitre.org/techniques/T1552/"
    },
    "T1557": {
      "family": "MITRE ATT&CK",
      "title": "Adversary-in-the-Middle",
      "url": "https://attack.mitre.org/techniques/T1557/"
    },
    "T1565": {
      "family": "MITRE ATT&CK",
      "title": "Data Manipulation",
      "url": "https://attack.mitre.org/techniques/T1565/"
    },
    "T1577": {
      "family": "MITRE ATT&CK",
      "title": "Compromise Application Executable",
      "url": "https://attack.mitre.org/techniques/T1577/"
    },
    "T1606": {
      "family": "MITRE ATT&CK",
      "title": "Forge Web Credentials",
      "url": "https://attack.mitre.org/techniques/T1606/"
    },
    "T1634": {
      "family": "MITRE ATT&CK",
      "title": "Credentials from Password Store",
      "url": "https://attack.mitre.org/techniques/T1634/"
    },
    "CWE-1188": {
      "family": "CWE",
      "title": "Initialization of a Resource with an Insecure Default"
    },
    "CWE-1189": {
      "family": "CWE",
      "title": "Improper Isolation of Shared Resources on System-on-a-Chip (SoC)"
    },
    "CWE-1357": {
      "family": "CWE",
      "title": "Reliance on Insufficiently Trustworthy Component"
    },
    "CWE-1395": {
      "family": "CWE",
      "title": "Dependency on Vulnerable Third-Party Component"
    },
    "CWE-20": {
      "family": "CWE",
      "title": "Improper Input Validation"
    },
    "CWE-200": {
      "family": "CWE",
      "title": "Exposure of Sensitive Information to an Unauthorized Actor"
    },
    "CWE-269": {
      "family": "CWE",
      "title": "Improper Privilege Management"
    },
    "CWE-287": {
      "family": "CWE",
      "title": "Improper Authentication"
    },
    "CWE-290": {
      "family": "CWE",
      "title": "Authentication Bypass by Spoofing"
    },
    "CWE-291": {
      "family": "CWE",
      "title": "Reliance on IP Address for Authentication"
    },
    "CWE-295": {
      "family": "CWE",
      "title": "Improper Certificate Validation"
    },
    "CWE-306": {
      "family": "CWE",
      "title": "Missing Authentication for Critical Function"
    },
    "CWE-308": {
      "family": "CWE",
      "title": "Use of Single-factor Authentication"
    },
    "CWE-312": {
      "family": "CWE",
      "title": "Cleartext Storage of Sensitive Information"
    },
    "CWE-345": {
      "family": "CWE",
      "title": "Insufficient Verification of Data Authenticity"
    },
    "CWE-400": {
      "family": "CWE",
      "title": "Uncontrolled Resource Consumption"
    },
    "CWE-404": {
      "family": "CWE",
      "title": "Improper Resource Shutdown or Release"
    },
    "CWE-494": {
      "family": "CWE",
      "title": "Download of Code Without Integrity Check"
    },
    "CWE-613": {
      "family": "CWE",
      "title": "Insufficient Session Expiration"
    },
    "CWE-636": {
      "family": "CWE",
      "title": "Not Failing Securely ('Failing Open')"
    },
    "CWE-749": {
      "family": "CWE",
      "title": "Exposed Dangerous Method or Function"
    },
    "CWE-770": {
      "family": "CWE",
      "title": "Allocation of Resources Without Limits or Throttling"
    },
    "CWE-778": {
      "family": "CWE",
      "title": "Insufficient Logging"
    },
    "CWE-829": {
      "family": "CWE",
      "title": "Inclusion of Functionality from Untrusted Control Sphere"
    },
    "CWE-862": {
      "family": "CWE",
      "title": "Missing Authorization"
    },
    "CWE-922": {
      "family": "CWE",
      "title": "Insecure Storage of Sensitive Information"
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
    "MASVS-NETWORK-2": {
      "family": "OWASP MASVS",
      "title": "The app performs identity pinning for all remote endpoints under the developer's control.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-NETWORK-2/"
    },
    "MASVS-PLATFORM-2": {
      "family": "OWASP MASVS",
      "title": "The app uses WebViews securely.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-PLATFORM-2/"
    },
    "MASVS-RESILIENCE-4": {
      "family": "OWASP MASVS",
      "title": "The app implements anti-dynamic analysis techniques.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-RESILIENCE-4/"
    },
    "MASVS-STORAGE-1": {
      "family": "OWASP MASVS",
      "title": "The app securely stores sensitive data.",
      "url": "https://mas.owasp.org/MASVS/controls/MASVS-STORAGE-1/"
    },
    "MASWE-0006": {
      "family": "OWASP MASWE",
      "title": "Sensitive Data Stored Unencrypted in Private Storage Locations",
      "url": "https://mas.owasp.org/MASWE/MASVS-STORAGE/MASWE-0006/"
    },
    "MASWE-0040": {
      "family": "OWASP MASWE",
      "title": "Insecure Authentication in WebViews",
      "url": "https://mas.owasp.org/MASWE/MASVS-AUTH/MASWE-0040/"
    },
    "MASWE-0052": {
      "family": "OWASP MASWE",
      "title": "Insecure Certificate Validation",
      "url": "https://mas.owasp.org/MASWE/MASVS-NETWORK/MASWE-0052/"
    },
    "MASWE-0068": {
      "family": "OWASP MASWE",
      "title": "JavaScript Bridges in WebViews",
      "url": "https://mas.owasp.org/MASWE/MASVS-PLATFORM/MASWE-0068/"
    },
    "MASWE-0072": {
      "family": "OWASP MASWE",
      "title": "Universal XSS",
      "url": "https://mas.owasp.org/MASWE/MASVS-PLATFORM/MASWE-0072/"
    },
    "MASWE-0099": {
      "family": "OWASP MASWE",
      "title": "Emulator Detection Not Implemented",
      "url": "https://mas.owasp.org/MASWE/MASVS-RESILIENCE/MASWE-0099/"
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
