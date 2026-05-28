window.APD_DATA = {
  "meta": {
    "framework_version": "1.5.0",
    "domain_pack": {
      "name": "api-security",
      "version": ""
    },
    "run_id": "apd-20260527-crapi-owasp-api-top10",
    "synthesizer_version": "1.0.0",
    "specialists_skipped": [],
    "subject": "OWASP crAPI v1.1.5",
    "subject_tagline": "automotive B2C demonstration platform (Apache-2.0)",
    "date": "",
    "artifact_count": 9,
    "artifact_types": [
      "md×8",
      "file"
    ],
    "crown_jewels": [
      "user_credentials_store",
      "payment_methods_store",
      "pii_profile_store",
      "session_token_signing_keys",
      "authorization_decision_engine",
      "audit_log_store",
      "backup_artifact_store",
      "third_party_integration_secrets"
    ],
    "attacker_positions": [
      "unauthenticated_internet",
      "authenticated_low_priv_user_with_bola_target",
      "authenticated_user_seeking_authz_bypass",
      "compromised_user_session_token",
      "compromised_oauth_client_credentials",
      "compromised_third_party_integration",
      "compromised_admin_session",
      "supply_chain_attacker",
      "internal_lateral_attacker"
    ]
  },
  "summary": {
    "findings_total": 72,
    "findings_pre_dedup": 72,
    "cross_lens_merged_clusters": 0,
    "linked_clusters": 0,
    "bySeverity": {
      "critical": 5,
      "high": 29,
      "medium": 38,
      "low": 0,
      "info": 0
    },
    "byDisposition": {
      "gap": 54,
      "blocked": 17,
      "risk": 0,
      "uncertainty": 1,
      "ok": 0
    },
    "byTier": {
      "trustworthiness": 31,
      "scalability": 21,
      "auditability": 20
    },
    "capabilities_total": 22,
    "capabilities_pre_dedup": 22,
    "capabilitiesByMaturity": {
      "designed": 8,
      "implemented": 14,
      "tested": 0,
      "operationalized": 0
    },
    "contradictions": 0,
    "severity_disagreements": 0
  },
  "exec_summary": [
    "This APD gauntlet run reviews OWASP crAPI v1.1.5, an intentionally vulnerable automotive B2C demonstration platform built around the OWASP API Security Top 10 (2023). The api-security domain pack applies. The 9-artifact intake is candid about the 18+ vulnerabilities crAPI ships by design (BOLA on vehicle and mechanic-report, BFLA on admin video delete, mass-assignment on orders and videos, SQL/NoSQL injection on coupons, SSRF on contact_mechanic, JWT forgery via four documented patterns, broken OTP brute-force, chatbot prompt-injection); the gauntlet's role is to assess the operational consequences across all 9 APD goals rather than re-derive the vulnerability catalog.",
    "Across 9 specialists, 62 deduped findings emerged after merging 4 cross-lens clusters (JWT trust chain, chatbot admin credential, SSRF contact_mechanic, shared datastore credential). 5 critical, 25 high, 32 medium; 0 contradictions; 0 severity disagreements. 20 findings (32%) are dispositioned `blocked` on prerequisite evidence — consistent with the demo-intent gap-rich nature of the inputs (no audit, no backups, no SLO, no rotation procedures). The single highest-leverage architectural concern is the JWT trust chain: default private key shipped in repo + verifier accepts four documented forgery patterns produces cluster-wide forge-any-identity capability. The most strategically urgent gap is the total absence of audit-logging on consequential actions, which prevents forensic reconstruction of any incident."
  ],
  "posture_summary": {
    "trustworthiness": "Single critical (forgeable JWTs at platform scope) and three critical injection vectors (SQL, NoSQL, mass-assignment to credit) dominate; data-at-rest encryption and password-storage scheme are blocked on evidence.",
    "scalability": "Single-host SPOF on identity by design (demo intent); shared datastore credential collapses isolation; no refresh-token rotation, no rotation tooling for any credential, no circuit breakers on three outbound integrations.",
    "auditability": "Audit log is structurally absent across the platform; no actor attribution on any consequential action; mutable substrate awaits when audit is introduced; chatbot admin-credential breaks attribution even hypothetically."
  },
  "capabilities": [
    {
      "id": "conf-cap-c354ef8e",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "designed",
      "title": "JWKS endpoint published over standard /.well-known/jwks.json path",
      "scope": "Mechanism in place. Significantly weakened by default private key in repo (merged-c829ffc8) and verifier multi-algo acceptance."
    },
    {
      "id": "conf-cap-0eea8c9d",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "designed",
      "title": "Default Mailhog loopback binding (LISTEN_IP=127.0.0.1)",
      "scope": "Confirmed for documented default. NOT enforced — LISTEN_IP=0.0.0.0 override removes it."
    },
    {
      "id": "conf-cap-545144bc",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "Datastores not exposed externally by default compose",
      "scope": "Confirmed for default Compose. NOT confirmed for Helm — NetworkPolicy not in values."
    },
    {
      "id": "conf-cap-95d55d61",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "designed",
      "title": "TLS-capable mode (TLS_ENABLED=true) available across all services",
      "scope": "Mechanism exists. NOT confirmed production posture (real certs, TLS policy, mTLS)."
    },
    {
      "id": "conf-cap-e149eaec",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "UUID identifier choice on vehicles (vs sequential integer)",
      "scope": "Confirmed for vehicles. Weakened in practice by leak via community recent-posts."
    },
    {
      "id": "intg-cap-4212a616",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "OpenAPI specification published for the API surface",
      "scope": "Confirmed: spec exists, is served, is indexed. NOT confirmed: handler conformance."
    },
    {
      "id": "intg-cap-d764e156",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "designed",
      "title": "RS256 asymmetric JWT mint (signing key not distributed to verifiers)",
      "scope": "Asymmetric design choice confirmed. Significantly weakened by default key in repo, multi-algo acceptance, no rotation."
    },
    {
      "id": "intg-cap-a070072a",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "designed",
      "title": "Coupon claim-state column (intended per-user idempotency)",
      "scope": "Mechanism in place as column. Defeated by SQL injection in apply_coupon."
    },
    {
      "id": "intg-cap-c6f2bf49",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "Rate limit on /identity/api/auth/v2/check-otp (partial coverage)",
      "scope": "Confirmed for v2/check-otp. NOT confirmed for any other auth surface."
    },
    {
      "id": "avail-cap-a85aeb7f",
      "tier": "trustworthiness",
      "goal": "availability",
      "maturity": "implemented",
      "title": "Per-service health.sh scripts with compose healthcheck wiring",
      "scope": "Confirmed for identity/workshop/community/mailhog. NOT confirmed for chatbot."
    },
    {
      "id": "avail-cap-5af461f2",
      "tier": "trustworthiness",
      "goal": "availability",
      "maturity": "implemented",
      "title": "Rate limit on /v2/check-otp (partial coverage)",
      "scope": "Confirmed v2 only; v3 and forget-password absent."
    },
    {
      "id": "avail-cap-26d2f293",
      "tier": "trustworthiness",
      "goal": "availability",
      "maturity": "implemented",
      "title": "Per-service compose resource limits prevent single-service runaway",
      "scope": "Confirmed for compose. NOT confirmed for Helm values."
    },
    {
      "id": "dist-cap-a2ac68b2",
      "tier": "scalability",
      "goal": "distributed",
      "maturity": "implemented",
      "title": "Microservice split with per-service container boundary",
      "scope": "Confirmed for compose. Boundary is process-only — not network-policy, not credential."
    },
    {
      "id": "dist-cap-452d749b",
      "tier": "scalability",
      "goal": "distributed",
      "maturity": "designed",
      "title": "Stateless application tier — JWT-based auth, no in-process session",
      "scope": "Confirmed for auth path. NOT confirmed for chatbot per-session LLM state via /genai/init."
    },
    {
      "id": "dist-cap-90969f60",
      "tier": "scalability",
      "goal": "distributed",
      "maturity": "implemented",
      "title": "JWKS endpoint at standard path — externalizable",
      "scope": "Endpoint exists at standard path. NOT confirmed any actual CDN/external replication."
    },
    {
      "id": "resil-cap-35c0088d",
      "tier": "scalability",
      "goal": "resilient",
      "maturity": "implemented",
      "title": "depends_on: service_healthy gating in compose enforces startup order",
      "scope": "Confirmed for compose. Helm equivalents not in input set."
    },
    {
      "id": "resil-cap-c6fc34e3",
      "tier": "scalability",
      "goal": "resilient",
      "maturity": "designed",
      "title": "Multi-provider chatbot architecture supports provider fallback (not yet implemented)",
      "scope": "Multi-provider support confirmed. NOT confirmed: automatic fallback on failure."
    },
    {
      "id": "ephem-cap-fd22b084",
      "tier": "scalability",
      "goal": "ephemeral",
      "maturity": "implemented",
      "title": "Image versioning on Postgres (postgres:14) and Mongo (mongo:4.4)",
      "scope": "Confirmed for Postgres/Mongo. NOT confirmed for ChromaDB (:latest)."
    },
    {
      "id": "auth-cap-125067f9",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "implemented",
      "title": "RS256 asymmetric JWT mint + JWKS publication (OIDC-style identity provenance)",
      "scope": "Mint and JWKS-publication confirmed. Significantly weakened by default private key, multi-algo verifier, no rotation."
    },
    {
      "id": "auth-cap-9703a609",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "designed",
      "title": "OpenAPI bearerAuth security scheme declared on every authenticated path",
      "scope": "Confirmed in spec. NOT confirmed in implementation per challenge 14 and INV-AUTH-001."
    },
    {
      "id": "nonrep-cap-81fb6e54",
      "tier": "auditability",
      "goal": "non_repudiation",
      "maturity": "implemented",
      "title": "Stdout logging at LOG_LEVEL=INFO across all services (operational, not auditable)",
      "scope": "Stdout streams exist. NOT confirmed: schema, content coverage, or consequential-action coverage."
    },
    {
      "id": "immut-cap-8e77982d",
      "tier": "auditability",
      "goal": "immutability",
      "maturity": "implemented",
      "title": "Pinned image versions on Postgres and Mongo",
      "scope": "Confirmed for Postgres/Mongo. NOT confirmed for ChromaDB, Mailhog, crAPI service images (digest not pinned)."
    }
  ],
  "strengths": [
    {
      "id": "conf-cap-545144bc",
      "title": "Datastores not exposed externally by default compose",
      "goal": "confidentiality",
      "maturity": "implemented",
      "caveats": [
        "Helm NetworkPolicy not in shipped values; segmentation is compose-only",
        "SSRF on contact_mechanic penetrates segmentation from any in-cluster service"
      ]
    },
    {
      "id": "intg-cap-4212a616",
      "title": "OpenAPI specification published for the API surface",
      "goal": "integrity",
      "maturity": "implemented",
      "caveats": [
        "Spec ≠ enforced schema; handlers accept inputs the spec doesn't document",
        "No CI gate verifying handler behavior matches the spec"
      ]
    },
    {
      "id": "auth-cap-125067f9",
      "title": "RS256 asymmetric JWT mint + JWKS publication (OIDC-style identity provenance)",
      "goal": "authenticity",
      "maturity": "implemented",
      "caveats": [
        "Default private key in repo (merged-c829ffc8)",
        "Verifier accepts multiple algorithms (merged-c829ffc8)",
        "No rotation procedure (ephem-30d38360)"
      ]
    },
    {
      "id": "dist-cap-452d749b",
      "title": "Stateless application tier — JWT-based auth, no in-process session",
      "goal": "distributed",
      "maturity": "designed",
      "caveats": [
        "Chatbot per-session key may introduce in-process state",
        "Theoretical replication; single-host SPOF unresolved (dist-1f123cef)"
      ]
    },
    {
      "id": "resil-cap-35c0088d",
      "title": "depends_on: service_healthy gating in compose enforces startup order",
      "goal": "resilient",
      "maturity": "implemented",
      "caveats": [
        "Healthchecks are shallow; do not gate on dependency health (avail-898bfad0)",
        "Startup-only; runtime degradation not addressed"
      ]
    },
    {
      "id": "intg-cap-a070072a",
      "title": "Coupon claim-state column (intended per-user idempotency)",
      "goal": "integrity",
      "maturity": "designed",
      "caveats": [
        "Idempotency check defeated by SQL injection (intg-ab3edc7a, intg-2aeb03f1)",
        "No DB-level unique constraint backing the application check"
      ]
    },
    {
      "id": "ephem-cap-fd22b084",
      "title": "Image versioning on Postgres (postgres:14) and Mongo (mongo:4.4)",
      "goal": "ephemeral",
      "maturity": "implemented",
      "caveats": [
        "ChromaDB pinned to :latest (ephem-edcc17b4)",
        "Mongo 4.4 past upstream EOL",
        "Image digests not pinned"
      ]
    }
  ],
  "findings": [
    {
      "id": "conf-fb05be4e",
      "title": "Vehicle-location endpoint discloses owner identity + GPS across users (BOLA #1)",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "GET /identity/api/v2/vehicle/{vehicleId}/location returns latitude/longitude and owner full name to any authenticated caller; vehicleId leaks via community recent-posts.",
      "detail": "See finding source; not duplicated in synthesis.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 BOLA #1",
          "excerpt": "endpoint accepts any UUID and returns latitude, longitude, and the owner's full name"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add ownership check on /vehicle/{vehicleId}/location and strip vehicleid from community recent-posts response."
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-3(7)",
          "AC-4",
          "AC-6",
          "SC-8",
          "SI-15"
        ],
        "attack": [
          "T1213"
        ],
        "cwe": [
          "CWE-639",
          "CWE-285"
        ],
        "owasp_api": [
          "API1:2023",
          "API3:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-5369e807",
      "title": "Mechanic-report endpoint discloses report bodies across users (BOLA #2)",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "GET /workshop/api/mechanic/mechanic_report?report_id=N uses sequential integer IDs with no ownership check.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 BOLA #2",
          "excerpt": "Mechanic report IDs are sequential integers; the endpoint does not authorise the requester against the report owner"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add ownership check on mechanic_report and migrate report_id to UUID."
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-4",
          "AC-6",
          "SI-15"
        ],
        "attack": [
          "T1213"
        ],
        "cwe": [
          "CWE-639",
          "CWE-285",
          "CWE-340"
        ],
        "owasp_api": [
          "API1:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-c237e01d",
      "title": "User dashboard and video responses leak internal fields (BOPLA read-side, EDE #4/#5)",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Dashboard and /videos/{video_id} serialize underlying ORM objects, exposing fields the UI never consumes (e.g., conversion_params).",
      "detail": "Linked to intg-62ebf664 (write-side of same field name).",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 EDE #4 and #5",
          "excerpt": "user dashboard / profile endpoints serialize fields the UI does not display; video object response includes an internal property"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add explicit response-field allowlists to dashboard and video serializers."
      },
      "mappings": {
        "nist": [
          "AC-4",
          "SI-15",
          "SC-8"
        ],
        "attack": [
          "T1213"
        ],
        "cwe": [
          "CWE-200",
          "CWE-213"
        ],
        "owasp_api": [
          "API3:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "merged-c829ffc8",
      "title": "Default JWT signing key + multi-algorithm verifier accepts forgeries — cluster-wide identity trust broken",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Merged: (a) services/identity/jwks.json ships private-key components by default, (b) verifier accepts alg:none, HS256-confusion, jku-fetch, kid-traversal; cluster auth is forgeable.",
      "detail": "Merged from three specialist findings (conf-c66f08cf Confidentiality,\nintg-15c04a1c Integrity, auth-09ae00ed Authenticity).\n\nThe architectural concern combines two failures: (a) the default\ninstall ships an RSA private key in `services/identity/jwks.json`\ncommitted to the repo, and (b) the verifier accepts at least four\ndocumented JWT forgery patterns. Either failure independently\nyields forge-any-identity capability; together they are critical\nauthentication-bypass.\n\nSeverity is critical per \"Forgeable session tokens at platform\nscope\" and \"Authentication bypass to high-privilege functions\nwith no factor required\" — both rubric clauses independently\napply.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication",
          "excerpt": "crAPI ships a default jwks.json containing the private key components (d, p, q, dp, dq, qi)"
        },
        {
          "artifact": "adrs/0002-jwt-with-rsa-and-jwks.md",
          "locator": "Consequences",
          "excerpt": "Algorithm-confusion (RS256 ↔ HS256) is the headline forgery vector"
        },
        {
          "artifact": "tech_plan.md",
          "locator": "§9 JWT vulnerabilities #15",
          "excerpt": "Four documented variants: RS256↔HS256 algorithm confusion, alg:none on dashboard, jku misuse, kid path traversal"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Generate fresh per-install keypair; pin alg:RS256; remove JWT_SECRET; allowlist jku; restrict kid to known set."
      },
      "mappings": {
        "nist": [
          "SC-12",
          "SC-12(1)",
          "SC-12(2)",
          "SC-13",
          "IA-2",
          "IA-2(1)",
          "IA-2(8)",
          "IA-5(2)",
          "SI-7",
          "SI-7(1)",
          "SC-23",
          "SC-23(3)",
          "SC-17",
          "SC-28(1)"
        ],
        "attack": [
          "T1552",
          "T1606",
          "T1550"
        ],
        "cwe": [
          "CWE-321",
          "CWE-347",
          "CWE-345",
          "CWE-22",
          "CWE-798",
          "CWE-287"
        ],
        "owasp_api": [
          "API2:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [
        null,
        null,
        null
      ],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 1
    },
    {
      "id": "conf-8f7c8c8d",
      "title": "Mailhog web UI on :8025 exposes every OTP and password-reset email when LISTEN_IP!=127.0.0.1",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "No authentication on Mailhog UI; documented LISTEN_IP=0.0.0.0 override removes the only barrier with no startup warning.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "adrs/0003-mailhog-for-otp-delivery.md",
          "locator": "Consequences",
          "excerpt": "Mailhog has no built-in authentication on :8025"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Gate Mailhog UI behind basic-auth; emit startup warning on LISTEN_IP override."
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-4",
          "SC-7",
          "IA-2",
          "SC-8"
        ],
        "attack": [
          "T1110"
        ],
        "cwe": [
          "CWE-306",
          "CWE-200"
        ],
        "owasp_api": [
          "API8:2023",
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "merged-44bdb663",
      "title": "Shared plaintext admin/crapisecretpassword on Postgres+Mongo, all services, repo-tracked",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Merged: single shared credential in compose env (Confidentiality disclosure) collapses datastore tier into one failure domain (Distributed) and enables direct DB write bypass of service-layer controls.",
      "detail": "Merged from conf-3e324699 and dist-c047a7c0. The plaintext\ncredential is both a credential-disclosure concern\n(Confidentiality) and a topology-of-trust concern (Distributed).\nThe same fix — per-service users + rotation — addresses both.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 Persistence and storage",
          "excerpt": "user/password admin / crapisecretpassword (hardcoded in deploy/docker/docker-compose.yml)"
        },
        {
          "artifact": "adrs/0004-dual-datastore-postgres-and-mongo.md",
          "locator": "Decision",
          "excerpt": "Both datastores accept the same admin credential. Every service that needs either datastore authenticates as admin"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Provision per-service Postgres+Mongo users with collection-scoped grants; remove static creds from compose; rotate per-deploy."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-5(7)",
          "SC-12",
          "SC-28(1)",
          "AC-2",
          "AC-6",
          "AC-6(1)",
          "AC-6(5)",
          "SC-7"
        ],
        "attack": [
          "T1552"
        ],
        "cwe": [
          "CWE-798",
          "CWE-256",
          "CWE-250"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [
        null,
        null
      ],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 8
    },
    {
      "id": "merged-514507e6",
      "title": "SSRF on contact_mechanic with unbounded rate — cloud metadata + internal services exfiltration",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Merged: (a) no URL allowlist on outbound fetch, (b) no input validation on URL field, (c) no rate limit, (d) response body returned to caller.",
      "detail": "Merged from conf-cf457739 (Confidentiality / data exfiltration),\nintg-5c659bdb (Integrity / input validation), and avail-6af5aff7\n(Availability / rate limit). The single architectural fix —\ninput-validating typed URL with allowlist + per-token rate limit\n+ no response-body return — closes all three concerns.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 SSRF #11",
          "excerpt": "mechanic_api URL fetched server-side, returning the HTTP response body to the caller. No allowlist"
        },
        {
          "artifact": "tech_plan.md",
          "locator": "§9 No Rate Limit #6",
          "excerpt": "No throttle on the contact-mechanic submission endpoint; arbitrary outbound webhook fan-out"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add typed URL field with hostname allowlist + IP-resolution check; per-token rate limit (10/min); do not return fetched body to caller."
      },
      "mappings": {
        "nist": [
          "SC-7",
          "SC-7(5)",
          "AC-4",
          "SC-8(1)",
          "SI-10",
          "SC-5",
          "SC-5(1)",
          "SC-6",
          "SI-13"
        ],
        "attack": [
          "T1190",
          "T1499"
        ],
        "cwe": [
          "CWE-918",
          "CWE-441",
          "CWE-770",
          "CWE-400",
          "CWE-20"
        ],
        "owasp_api": [
          "API7:2023",
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [
        null,
        null,
        null
      ],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 7
    },
    {
      "id": "conf-bd613330",
      "title": "Encryption at rest unconfigured on Postgres, Mongo, ChromaDB",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "tech_plan and ADR-0004 explicitly state no encryption-at-rest is configured; specifics of remediation depend on deploy substrate.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§10 Out-of-scope",
          "excerpt": "Encryption at rest. Not configured anywhere in the inputs"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add encryption-at-rest posture to ADR-0004 with deploy-substrate-specific implementation."
      },
      "mappings": {
        "nist": [
          "SC-28",
          "SC-28(1)",
          "SC-12",
          "MP-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-311",
          "CWE-312"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Target deploy substrate and disk-encryption posture",
        "Field-level vs full-disk encryption decision; key-management hierarchy"
      ]
    },
    {
      "id": "conf-b7aaa1e7",
      "title": "Password storage scheme unspecified in inputs",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "users.password storage is not described; modern API security demands argon2/scrypt/bcrypt with tuned parameters.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§5 Data model",
          "excerpt": "password (storage scheme unspecified in inputs)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document password-storage posture in ADRs or tech_plan and confirm via code review."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "SC-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-916",
          "CWE-256",
          "CWE-326"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Spring Security password-encoder bean configuration in identity",
        "argon2/scrypt/bcrypt cost factor in effect"
      ]
    },
    {
      "id": "conf-d760cafe",
      "title": "Gateway-service VIN-to-PII oracle exposes bulk PII and payment data",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "api.mypremiumdealership.com returns SSN/address/card_number deterministically seeded by VIN; basic-auth alone gates.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "architecture-index.md",
          "locator": "§api.mypremiumdealership.com",
          "excerpt": "Returns deterministically faked PII (name, phone, ssn, address, card_number) seeded from fnv32a(VIN)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Replace deterministic VIN-seeding with per-deploy random; add rate-limit + audit on /owners."
      },
      "mappings": {
        "nist": [
          "AC-3",
          "AC-4",
          "AC-6",
          "SC-7",
          "IA-5"
        ],
        "attack": [
          "T1213"
        ],
        "cwe": [
          "CWE-639",
          "CWE-340",
          "CWE-200"
        ],
        "owasp_api": [
          "API1:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-fffef009",
      "title": "JWT carries excessive claims — full PII profile likely embedded in 7-day bearer tokens",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "7-day TTL with no documented claim-minimization; standard Spring practice serializes full user record.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication and sessions",
          "excerpt": "Expiration defaults to JWT_EXPIRATION=604800000 milliseconds (7 days)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Reduce JWT TTL to 1 hour and limit claims to {sub, iss, aud, exp, jti, scope}."
      },
      "mappings": {
        "nist": [
          "SC-8",
          "AC-4",
          "SC-28",
          "AU-3"
        ],
        "attack": [],
        "cwe": [
          "CWE-200",
          "CWE-532"
        ],
        "owasp_api": [
          "API3:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "conf-5f25ca4e",
      "title": "TLS configuration policy unspecified when TLS_ENABLED=true",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "Version floor, cipher suite, certificate validation, mTLS topology unspecified.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§2 Deployment topologies",
          "excerpt": "TLS_ENABLED=true to switch services into HTTPS-backed mode"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add TLS policy section to tech_plan.md naming version floor, cipher allowlist, certificate-validation."
      },
      "mappings": {
        "nist": [
          "SC-8",
          "SC-8(1)",
          "SC-12",
          "SC-23",
          "IA-3"
        ],
        "attack": [],
        "cwe": [
          "CWE-326",
          "CWE-319"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "TLS policy: version floor, cipher suite allowlist, certificate-validation on outbound",
        "mTLS posture at in-cluster service-to-service hop"
      ]
    },
    {
      "id": "intg-e7ebcc95",
      "title": "Mass assignment on /workshop/api/shop/orders accepts negative quantity → arbitrary credit inflation",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Server multiplies unit_price × quantity unconditionally; quantity:-100 inflates balance by 100×price.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 Mass Assignment #8/#9",
          "excerpt": "POST /workshop/api/shop/orders allows negative quantity. The server applies the credit delta unconditionally, letting the caller mint balance"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Enforce quantity ≥ 1 server-side; replace ORM-bind with explicit allowlist serializer; compute unit_price server-side."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "SI-10(5)",
          "AC-3",
          "SI-15",
          "CM-5"
        ],
        "attack": [
          "T1190"
        ],
        "cwe": [
          "CWE-915",
          "CWE-20",
          "CWE-840"
        ],
        "owasp_api": [
          "API3:2023",
          "API6:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 3
    },
    {
      "id": "intg-6d98c520",
      "title": "Server-derived unit_price not confirmed on order-create path",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "medium",
      "disposition": "uncertainty",
      "summary": "Inputs do not confirm whether unit_price is server-derived from product record or accepted from request body.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "§2 T-4",
          "excerpt": "If unit_price or total is passed in the request body and stored verbatim, the attacker pays an arbitrary amount"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Confirm unit_price is server-derived; if not, fix per intg-e7ebcc95."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "AC-3",
          "SI-15"
        ],
        "attack": [],
        "cwe": [
          "CWE-915",
          "CWE-840"
        ],
        "owasp_api": [
          "API3:2023",
          "API6:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "POST /shop/orders request-body schema",
        "OrderCreateView source for unit_price assignment"
      ]
    },
    {
      "id": "intg-b7417f91",
      "title": "NoSQL injection on /community/api/v2/coupon/validate-coupon",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Request body is parsed directly into a Mongo query selector; arbitrary document read across shared-credential collections.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 NoSQL Injection #12",
          "excerpt": "/community/api/v2/coupon/validate-coupon endpoint parses the request body directly into a Mongo query selector"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Unmarshal into typed struct; never pass user input as Mongo selector."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "SI-10(5)",
          "AC-3",
          "AC-6"
        ],
        "attack": [
          "T1190"
        ],
        "cwe": [
          "CWE-943",
          "CWE-89",
          "CWE-20"
        ],
        "owasp_api": [
          "API10:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 4
    },
    {
      "id": "intg-2aeb03f1",
      "title": "SQL injection on /workshop/api/shop/apply_coupon (string-concat UPDATE)",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Coupon code concatenated into SQL UPDATE; UPDATE injection re-arms claimed flags; UNION reads PII tables under shared admin.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 SQL Injection #13",
          "excerpt": "workshop apply_coupon flow concatenates SQL; UPDATE statements can be injected to clear claimed flags"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Replace string-concat SQL with parameterized queries; audit every workshop handler."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "SI-10(5)",
          "AC-3",
          "AC-6",
          "CM-5"
        ],
        "attack": [
          "T1190"
        ],
        "cwe": [
          "CWE-89",
          "CWE-20"
        ],
        "owasp_api": [
          "API10:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 5
    },
    {
      "id": "intg-62ebf664",
      "title": "Mass assignment on /identity/api/v2/user/videos/{video_id} accepts internal fields",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Shadow video-update endpoint persists arbitrary request body fields including the conversion_params field leaked by EDE #5.",
      "detail": "Linked to conf-c237e01d (read-side leak of same field).",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 Mass Assignment #10",
          "excerpt": "shadow update endpoint accepts arbitrary internal video fields, reachable by leveraging the leaked field name from #5"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add allowlist serializer on video-update; strip conversion_params from writeable set."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "AC-3",
          "SI-15"
        ],
        "attack": [
          "T1190"
        ],
        "cwe": [
          "CWE-915",
          "CWE-20"
        ],
        "owasp_api": [
          "API3:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "intg-a6b6d147",
      "title": "Mass-assignment on user-update may expose role field (E-3)",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "Possible mass-assignment to users.role on self-update endpoint; not confirmed in OpenAPI but consistent with pattern.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "§6 E-3",
          "excerpt": "Caller submits {role: admin} alongside benign fields on a self-update; the field is bound to the user record"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add allowlist DTO that excludes role on any user-update endpoint."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "AC-3",
          "AC-6"
        ],
        "attack": [
          "T1078"
        ],
        "cwe": [
          "CWE-915",
          "CWE-269"
        ],
        "owasp_api": [
          "API3:2023",
          "API5:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Identity user-update endpoint definition and request schema",
        "Spring binding-allowlist or @JsonIgnoreProperties on User entity"
      ]
    },
    {
      "id": "intg-ab3edc7a",
      "title": "Coupon redemption is not idempotent — SQL injection re-arms claimed flag",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "INV-INPUT-003 asserts idempotency; SQL injection on apply_coupon defeats the claimed-state check.",
      "detail": "Linked to intg-2aeb03f1.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "invariants.md",
          "locator": "INV-INPUT-003",
          "excerpt": "Challenge 13 contradicts via SQL injection on the claimed-state UPDATE"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Fix underlying SQL injection (intg-2aeb03f1); add UNIQUE (coupon_code, claimed_by) constraint."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "SI-7",
          "SC-5",
          "AU-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-89",
          "CWE-840"
        ],
        "owasp_api": [
          "API6:2023",
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "merged-d2e871f5",
      "title": "Chatbot prompt-injection drives admin actions; embedded credential breaks attribution",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Merged: (a) chatbot holds admin credential, (b) prompt-injection induces tool calls under admin authority, (c) downstream audit attributes to admin not prompt author.",
      "detail": "Merged from intg-078ee9f6 (Integrity write-path), auth-55e76c4d\n(Authenticity credential-binding), nonrep-fc423071 (Non-\nRepudiation attribution), ephem-b95a7d11 (Ephemeral rotation).\nFour-lens merge; single fix.\n",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "architecture-index.md",
          "locator": "§crapi-chatbot Role",
          "excerpt": "API_USER=admin@example.com / API_PASSWORD=Admin!123 — a privileged crAPI credential used to act on behalf of users"
        },
        {
          "artifact": "tech_plan.md",
          "locator": "§9 LLM #16/17/18",
          "excerpt": "Chatbot prompt-injection allowing client-side rendering injection (#16), credential extraction (#17), action-on-behalf-of (#18)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Remove embedded credential; chatbot acts under prompt author's bearer; tool-call allowlist per user role; audit every chat-driven call."
      },
      "mappings": {
        "nist": [
          "SI-10",
          "AC-3",
          "AC-6",
          "AC-6(1)",
          "AC-6(5)",
          "IA-9",
          "IA-2",
          "AU-3",
          "AU-3(1)",
          "AU-10",
          "IA-5"
        ],
        "attack": [
          "T1078",
          "T1552"
        ],
        "cwe": [
          "CWE-77",
          "CWE-285",
          "CWE-269",
          "CWE-94",
          "CWE-798",
          "CWE-223"
        ],
        "owasp_api": [
          "API5:2023",
          "API8:2023",
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [
        null,
        null,
        null,
        null
      ],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 6
    },
    {
      "id": "intg-8d97cd9f",
      "title": "ENABLE_LOG4J and ENABLE_SHELL_INJECTION feature flags wire deliberate injection sinks",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Default-false env flags activate log4shell-style and command-injection sinks when flipped; no operator signal on activation.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 Implicit posture facts",
          "excerpt": "ENABLE_LOG4J=false flag exists. ENABLE_SHELL_INJECTION=false flag exists in the identity env"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Remove injection-sink flags entirely; replace with explicit demo-mode versioning with startup banner."
      },
      "mappings": {
        "nist": [
          "CM-7",
          "CM-7(5)",
          "SI-10",
          "SI-7",
          "CM-3"
        ],
        "attack": [],
        "cwe": [
          "CWE-94",
          "CWE-78",
          "CWE-117"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "intg-b097f9a8",
      "title": "Cross-store consistency between coupons (Postgres) and coupon_documents (Mongo) is application-mediated",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "No coordination protocol; partial-failure behavior unspecified.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "adrs/0004-dual-datastore-postgres-and-mongo.md",
          "locator": "Consequences",
          "excerpt": "Cross-store consistency is the application's responsibility"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document the coupon-flow saga; add reconciliation runbook and periodic divergence check."
      },
      "mappings": {
        "nist": [
          "SI-7",
          "SI-10",
          "CP-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-362",
          "CWE-840"
        ],
        "owasp_api": [
          "API6:2023",
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Cross-store coupon-flow source",
        "Reconciliation script or runbook"
      ]
    },
    {
      "id": "avail-e96ad7ff",
      "title": "No rate limit on /identity/api/auth/v3/check-otp (4-digit space, 10k entries)",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Unbounded guess attempts against trivial OTP space; brute force completes in seconds.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication, /v3/check-otp",
          "excerpt": "rate-limiting on v2 was added but v3 and other variants remain bypassable"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Apply identical rate-limit + lockout to every check-otp variant; centralize OTP-verification logic; increase OTP entropy to 6+ digits."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-5(1)",
          "AC-7",
          "AC-7(2)",
          "IA-5"
        ],
        "attack": [
          "T1110"
        ],
        "cwe": [
          "CWE-307",
          "CWE-770"
        ],
        "owasp_api": [
          "API4:2023",
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "avail-c1ffcf8e",
      "title": "No rate limit on /identity/api/auth/forget-password",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Unbounded OTP-issuance saturates mailhog ring buffer and resets active OTP.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "adrs/0003-mailhog-for-otp-delivery.md",
          "locator": "Consequences",
          "excerpt": "No replay or throttling discipline on OTP issuance"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Cap OTP issuance to 3 per account per hour; per-IP cap 20/hour."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "AC-7",
          "IA-5"
        ],
        "attack": [],
        "cwe": [
          "CWE-307",
          "CWE-770"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "avail-fb795bfb",
      "title": "No timeout on outbound calls — identity→gateway, workshop→mechanic, chatbot→LLM",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Outbound HTTP timeout discipline undocumented; vendor slowdown pins thread pools.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #5",
          "excerpt": "identity → gateway-service. Outbound HTTPS to https://api.mypremiumdealership.com"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Establish outbound timeout policy: 5s connect, 10s total per call."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SI-13",
          "CP-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-400",
          "CWE-1088"
        ],
        "owasp_api": [
          "API4:2023",
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "avail-470902f0",
      "title": "No SLO/SLI declared for any service or surface",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "agents.md explicitly states no SLO commitment; no error budget, no burn-rate alerting.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "agents.md",
          "locator": "§Who operates crAPI",
          "excerpt": "There is no enterprise operator. There is no on-call rotation. There is no SLO commitment"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "If non-demo deploy contemplated, declare 99% SLO on auth path."
      },
      "mappings": {
        "nist": [
          "CP-2",
          "CP-2(3)",
          "SI-13"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Declared availability target for any production-intent deploy"
      ]
    },
    {
      "id": "avail-898bfad0",
      "title": "Health checks are shallow — port-availability, not dependency-aware",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "/health_check endpoints probe local readiness only; chatbot has no documented external health endpoint.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§2 Health checks",
          "excerpt": "Each service ships a health.sh invoked by the compose healthcheck: block"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add dependency-aware /readyz endpoints; document expected shape."
      },
      "mappings": {
        "nist": [
          "SI-13",
          "CP-10",
          "SC-5"
        ],
        "attack": [],
        "cwe": [
          "CWE-754",
          "CWE-1088"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "avail-8ad04f0e",
      "title": "No backup or restore procedure documented",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "Runbook §10 explicitly states no backup/restore tooling; PITR, RPO/RTO unspecified.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 Persistence and storage",
          "excerpt": "Backups: unspecified. No backup, restore, or PITR procedure ships"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, add coordinated Postgres+Mongo backup with stated RPO/RTO."
      },
      "mappings": {
        "nist": [
          "CP-9",
          "CP-9(1)",
          "CP-9(8)",
          "CP-10",
          "CP-10(2)"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Deploy intent and corresponding RPO/RTO target",
        "Cross-store consistency requirement for backup approach"
      ]
    },
    {
      "id": "avail-b01847b0",
      "title": "Compose resource limits (cpus:0.8, memory:384M) easily exhausted by DoS",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Tight limits + rate-limit gaps = trivial pod OOM under modest probe traffic.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "adrs/0001-microservice-split-by-language.md",
          "locator": "Consequences",
          "excerpt": "Resource limits are uniformly tight. cpus: 0.8, memory: 384M per service"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, raise limits to ≥1 vCPU/1 GiB; add per-service profiles in Helm."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-6",
          "SI-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-770",
          "CWE-400"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "avail-004444b5",
      "title": "Chatbot LLM cost amplification (denial of wallet)",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "No prompt-length cap, no per-user rate limit, no token-budget guardrail.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "§5 D-3",
          "excerpt": "Caller submits very long prompts that the chatbot forwards to the configured LLM provider"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add prompt-length cap (4K tokens), per-user 10/hr, per-user daily token budget."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-6",
          "AC-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-770",
          "CWE-400"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "avail-4f60016d",
      "title": "No unbounded-request-size guard documented on ingress or backend services",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "max_request_body_size unspecified; 200 MiB POST can pin a worker on a 384 MiB pod.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "architecture-index.md",
          "locator": "§crapi-web",
          "excerpt": "Nginx config templates under services/web/ (nginx.conf.template, nginx.ssl.conf.template)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Set client_max_body_size=2M on OpenResty; mirror in each backend service."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-5(1)",
          "SI-10"
        ],
        "attack": [],
        "cwe": [
          "CWE-400",
          "CWE-770"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "nginx.conf.template content showing client_max_body_size directive",
        "Per-backend service request-size configuration"
      ]
    },
    {
      "id": "dist-1f123cef",
      "title": "Single-host topology by design — identity is a cluster-wide SPOF",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "All services on one host per agents.md; identity service compromise/outage = total cluster auth failure.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "agents.md",
          "locator": "§Intended runtime",
          "excerpt": "Default target: a single host"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, split into ≥2 AZs with identity replicated."
      },
      "mappings": {
        "nist": [
          "SC-7",
          "CP-7",
          "SC-36",
          "CP-2"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "dist-04709717",
      "title": "Postgres and Mongo are single-instance with no replication topology",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Single-container datastores; no Mongo replSet, no Postgres streaming replication; single corrupted volume = total data loss.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 Persistence and storage",
          "excerpt": "PostgreSQL 14 (postgresdb). Single database crapi"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, configure Postgres streaming replication and Mongo replSet."
      },
      "mappings": {
        "nist": [
          "SC-36",
          "CP-7",
          "CP-9",
          "SC-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "dist-5e588812",
      "title": "Service-to-service auth via shared single JWKS — coupled failure with identity",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Every service fetches JWKS from identity; identity unavailability eventually fails every verifier.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #3",
          "excerpt": "Other services consume IDENTITY_SERVICE=crapi-identity:8080 to validate bearer JWTs against the JWKS endpoint"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document and harden per-service JWKS cache: TTL 1h, last-known-good 24h on fetch failure."
      },
      "mappings": {
        "nist": [
          "SC-7",
          "SC-22",
          "CP-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-754"
        ],
        "owasp_api": [
          "API4:2023",
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "dist-bc4789b6",
      "title": "No network policy in shipped Helm values restricts in-cluster reachability",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "Default-Kubernetes networking allows any-to-any; combined with shared creds, SSRF pivots to direct datastore access.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "prior-audit.md",
          "locator": "§Operational gaps",
          "excerpt": "No network policy in shipped Helm values"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add per-service NetworkPolicy resources to Helm chart."
      },
      "mappings": {
        "nist": [
          "SC-7",
          "SC-7(5)",
          "SC-7(21)",
          "AC-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-732"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "deploy/helm/values.yaml content",
        "Cluster CNI declaration"
      ]
    },
    {
      "id": "dist-0a56c5f0",
      "title": "Heterogeneous JWT-verifier implementations across language stacks (no shared module)",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Each service picks its own JWT library; verifier consistency is operator-discipline; alg-pinning drifts per challenge 15.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "adrs/0001-microservice-split-by-language.md",
          "locator": "Consequences",
          "excerpt": "JWT verification surface is heterogeneous. Every service has to pick a JWT library. There is no shared verification module"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Adopt a verifier-validation matrix in CI: single test suite hits every service's verifier with same forgery samples."
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-5(2)",
          "SC-23",
          "CM-2"
        ],
        "attack": [],
        "cwe": [
          "CWE-345",
          "CWE-347"
        ],
        "owasp_api": [
          "API2:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "dist-c5b2799b",
      "title": "Mailhog is single instance with in-memory storage — OTP delivery is SPOF",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Container restart drops every captured OTP; no production SMTP path.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "architecture-index.md",
          "locator": "§mailhog Datastores touched",
          "excerpt": "In-memory ring buffer"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, swap Mailhog for real SMTP relay."
      },
      "mappings": {
        "nist": [
          "CP-7",
          "SI-13",
          "SC-36"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "resil-c7975476",
      "title": "No circuit breaker on outbound calls — three integration points unprotected",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "identity→gateway, workshop→mechanic, chatbot→LLM all lack documented circuit breakers; vendor degradation cascades.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #5",
          "excerpt": "identity → gateway-service. Outbound HTTPS"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add per-target circuit breakers with failure-rate threshold (50%, 5s window) on every outbound integration."
      },
      "mappings": {
        "nist": [
          "SI-13",
          "SC-5",
          "CP-13",
          "SI-17"
        ],
        "attack": [],
        "cwe": [
          "CWE-405",
          "CWE-754"
        ],
        "owasp_api": [
          "API4:2023",
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "resil-776fc650",
      "title": "No refresh-token rotation, no refresh-token reuse detection — 7-day session theft has no recovery signal",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "7-day bearer-token TTL with no revocation; stolen token persists full lifetime with no detection signal.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§10 Respond to user account takeover",
          "excerpt": "Cannot invalidate the attacker's session. No JTI revocation list"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Short-lived (1h) access + rotating refresh + reuse-detection + JTI deny-list."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(13)",
          "AC-12",
          "SI-4",
          "SI-17"
        ],
        "attack": [
          "T1550"
        ],
        "cwe": [
          "CWE-613",
          "CWE-384"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 10
    },
    {
      "id": "resil-5738d03e",
      "title": "No graceful degradation for identity outage — total auth failure across cluster",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Identity unavailability collapses entire deploy; no documented degraded-mode.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #3",
          "excerpt": "identity ↔ peers. Other services consume IDENTITY_SERVICE"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Document degraded-mode: verifiers retain last-known-good JWKS for 24h on identity outage."
      },
      "mappings": {
        "nist": [
          "CP-12",
          "CP-13",
          "IA-2",
          "SI-17"
        ],
        "attack": [],
        "cwe": [
          "CWE-754"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "resil-9e865b2e",
      "title": "No bulkhead between consumer-facing API paths and admin / contact_mechanic outbound paths",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "All workshop endpoints share one thread pool; admin enumeration or contact_mechanic burst starves customer traffic.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§8 Workshop surface",
          "excerpt": "GET /workshop/api/shop/orders/all <-- admin-shaped enumeration. POST /workshop/api/merchant/contact_mechanic <-- SSRF webhook, no rate limit"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Move /contact_mechanic and admin paths to separate worker pool or deployment."
      },
      "mappings": {
        "nist": [
          "SC-5",
          "SC-6",
          "SI-13"
        ],
        "attack": [],
        "cwe": [
          "CWE-400",
          "CWE-770"
        ],
        "owasp_api": [
          "API4:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "resil-01a11294",
      "title": "Retry policy unspecified — no backoff, jitter, budget, idempotency-key interaction",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "Three outbound paths have no documented retry posture; thundering-herd risk.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #5",
          "excerpt": "identity → gateway-service"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document retry policy: 3 retries, exponential backoff with jitter, idempotency keys."
      },
      "mappings": {
        "nist": [
          "SI-13",
          "SI-13(4)",
          "SC-5(1)"
        ],
        "attack": [],
        "cwe": [
          "CWE-754",
          "CWE-755"
        ],
        "owasp_api": [
          "API4:2023",
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Per-service outbound HTTP client wrapper code",
        "Idempotency-key handling on each outbound path"
      ]
    },
    {
      "id": "resil-373918f9",
      "title": "No graceful degradation specified for vendor outage (gateway or LLM)",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Vendor 5xx cascades to user-facing 500; no cached fallback or multi-provider switching.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #5",
          "excerpt": "identity → gateway-service. Outbound HTTPS"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Cached-fallback for gateway VIN lookups; multi-provider fallback for LLM."
      },
      "mappings": {
        "nist": [
          "CP-12",
          "CP-13",
          "SI-17",
          "SC-5"
        ],
        "attack": [],
        "cwe": [
          "CWE-1188"
        ],
        "owasp_api": [
          "API10:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "resil-592113d0",
      "title": "No chaos-engineering or game-day evidence; runbook lacks failure-mode catalog",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "Operational maturity for Resilient capabilities requires chaos/game-day evidence; demo intent makes this blocked.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§12 Troubleshooting reference",
          "excerpt": "For in-depth issues, the operator is referred to the upstream GitHub Issues; no internal escalation path is defined"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, add failure-mode catalog; quarterly game-days for production-contemplated."
      },
      "mappings": {
        "nist": [
          "CP-2",
          "CP-2(5)",
          "SI-13"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Deploy intent declaration",
        "Failure-mode catalog",
        "Game-day or chaos-engineering exercise records"
      ]
    },
    {
      "id": "ephem-30d38360",
      "title": "JWT signing key has no rotation procedure (jwks.json effectively static)",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Runbook §5 GAP; ADR-0002 confirms no rotation tooling; key has indefinite lifetime.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§5 Rotate the JWT signing key",
          "excerpt": "GAP. No documented procedure ships in the input set"
        },
        {
          "artifact": "adrs/0002-jwt-with-rsa-and-jwks.md",
          "locator": "Consequences",
          "excerpt": "No rotation tooling"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Ship rotate-jwks.sh with multi-kid grace window; document cutover policy."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-5(7)",
          "SC-12",
          "SC-12(1)",
          "AC-2"
        ],
        "attack": [
          "T1552"
        ],
        "cwe": [
          "CWE-321",
          "CWE-798"
        ],
        "owasp_api": [
          "API2:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-22c2358c",
      "title": "Datastore admin credentials static — multi-service simultaneous restart required to rotate",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Runbook §6 GAP; rotation requires all consuming services restart simultaneously.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§6 Rotate datastore credentials",
          "excerpt": "GAP. The Postgres and Mongo passwords (crapisecretpassword) are hardcoded"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Per-service credentials via init container; rotate independently via secret store."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-5(7)",
          "AC-2",
          "SC-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-798",
          "CWE-321"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-96d3befb",
      "title": "7-day JWT TTL with no refresh-token rotation, no idle timeout, no logout",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Per tech_plan §4: 7-day bearer; no /logout endpoint; no idle-timeout, no credential-change-revokes-sessions semantics.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication and sessions",
          "excerpt": "There is no MFA. There is no documented session-revocation surface (no /logout endpoint)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "JWT TTL 1h; refresh-token rotation; /logout with JTI deny-list; idle timeout 30m."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(13)",
          "AC-12",
          "AC-12(1)",
          "SC-10"
        ],
        "attack": [],
        "cwe": [
          "CWE-613",
          "CWE-384"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-6020f861",
      "title": "OTP TTL implied ~10 minutes but not asserted; re-issuance unbounded",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "Challenge 3 implies TTL; ADR-0003 explicit on no throttling discipline.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§7 OTP delivery",
          "excerpt": "TTL: per challenge 3 solution discussion, the OTP expiry is short (~10 minutes) but the per-OTP attempt count on the v3 variant is unbounded"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Pin OTP TTL to 5 minutes; invalidate prior OTP on re-issuance."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(13)",
          "AC-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-613"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Identity OTP-handler TTL config value",
        "OTP re-issuance behavior (invalidates prior?)"
      ]
    },
    {
      "id": "ephem-a39a1f7b",
      "title": "Gateway-service basic-auth credential undocumented and unrotated",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Per S-5 hard-coded in identity binary; rotation requires rebuild and redeploy.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "§1 S-5",
          "excerpt": "if static and obtainable (env dump, log leak, or simple guess against admin / Admin!123 — visible in the chatbot env)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Externalize gateway basic-auth credential to env or vault; document rotation."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-5(7)",
          "SC-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-798"
        ],
        "owasp_api": [
          "API2:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-edcc17b4",
      "title": "ChromaDB pinned to :latest — image content can change without pull event",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Mutable image tag introduces deploy-time version drift.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§2 Services table",
          "excerpt": "chromadb — chromadb (chromadb/chroma:latest)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Pin ChromaDB to specific version + digest; apply digest-pinning to all images."
      },
      "mappings": {
        "nist": [
          "CM-2",
          "CM-3",
          "SA-15(7)",
          "SI-7",
          "SR-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-1357"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-2c1c7ecf",
      "title": "Just-in-time human access not modeled; operator uses shared admin against datastores",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Runbook §9 instructs docker compose exec into postgresdb as admin; no time-boxed, audited, or approval-gated access.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§9 Respond to balance went wrong",
          "excerpt": "docker compose exec postgresdb psql -U admin -d crapi"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For shared deploys, per-operator credentials via vault dynamic secrets + bastion."
      },
      "mappings": {
        "nist": [
          "AC-2",
          "AC-2(2)",
          "AC-2(3)",
          "AC-6",
          "AC-6(9)",
          "AU-12"
        ],
        "attack": [],
        "cwe": [
          "CWE-269"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "ephem-3ad94819",
      "title": "Per-session chatbot LLM provider key bootstrap has no session-end revocation documented",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "POST /chatbot/genai/init accepts per-session OpenAI/Anthropic key; storage location and lifetime unspecified.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§8 Chatbot endpoints",
          "excerpt": "POST /genai/init <-- per-session LLM provider key bootstrap (OpenAI/Anthropic only)"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document per-session key handling: in-memory only, scrubbed on session end, never logged."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "AC-12",
          "SC-28"
        ],
        "attack": [],
        "cwe": [
          "CWE-256",
          "CWE-613"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "auth-4ef8b512",
      "title": "BFLA — admin video-delete reachable by non-admin tokens",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "DELETE /identity/api/v2/admin/videos/{id} accepts any user token; role claim not checked.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 BFLA #7",
          "excerpt": "The admin path DELETE /identity/api/v2/admin/videos/{video_id} does not check the caller's role"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add role check on /admin/* prefix; audit /shop/orders/all, /management/users/all for same pattern."
      },
      "mappings": {
        "nist": [
          "IA-2",
          "AC-3",
          "AC-6",
          "AC-6(1)",
          "AC-6(7)"
        ],
        "attack": [
          "T1078"
        ],
        "cwe": [
          "CWE-285",
          "CWE-269",
          "CWE-862"
        ],
        "owasp_api": [
          "API5:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "auth-0925a719",
      "title": "No MFA on any authentication surface — including admin",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Per tech_plan §4: 'There is no MFA' on any surface, including admin actions.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication and sessions",
          "excerpt": "There is no MFA"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add TOTP MFA on login (optional user, required admin); WebAuthn for admin step-up."
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-2(1)",
          "IA-2(2)",
          "IA-2(6)",
          "IA-2(8)",
          "AC-6"
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
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 2
    },
    {
      "id": "auth-b57f022f",
      "title": "OTP-based password reset is single-factor account-recovery",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Forget-password initiates reset via email-only claim; OTP success completes recovery with no additional verification.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication endpoints",
          "excerpt": "POST /identity/api/auth/forget-password — OTP email dispatch"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Require knowledge of prior password OR MFA factor for password reset; rate-limit forget-password."
      },
      "mappings": {
        "nist": [
          "IA-5",
          "IA-5(1)",
          "IA-2",
          "IA-2(8)",
          "AC-7"
        ],
        "attack": [],
        "cwe": [
          "CWE-640",
          "CWE-308"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "auth-5b90d6c3",
      "title": "Service-to-service authentication via bearer JWT only, not mTLS or workload identity",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Plaintext HTTP in-cluster with header-trust; no mTLS, no SPIFFE.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 boundary #2",
          "excerpt": "Plain HTTP inside the Compose network unless TLS_ENABLED=true. No mutual TLS"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "For non-demo deploys, enable mTLS via service mesh (Linkerd/Istio) with SPIFFE workload identity."
      },
      "mappings": {
        "nist": [
          "SC-8",
          "SC-8(1)",
          "SC-23",
          "IA-3",
          "IA-9"
        ],
        "attack": [
          "T1557"
        ],
        "cwe": [
          "CWE-319",
          "CWE-345"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "auth-04fcfb9a",
      "title": "Container images not signed; no admission control verifies image authenticity",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "gap",
      "summary": "No cosign/notation signature posture, no admission control; image-pull trust relies on registry.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§2 Services",
          "excerpt": "crapi/crapi-identity:${VERSION}"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Upstream: sign crAPI images via cosign; publish verification key; document operator verification."
      },
      "mappings": {
        "nist": [
          "SI-7",
          "SR-4",
          "SR-4(3)",
          "SR-4(4)",
          "SR-11",
          "CM-5"
        ],
        "attack": [],
        "cwe": [
          "CWE-345"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "auth-c990b0ff",
      "title": "AAL target undeclared (NIST SP 800-63B AAL1/AAL2/AAL3 not stated)",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "No Authenticator Assurance Level target; cannot evaluate MFA-strength against defined standard.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4 Authentication and sessions",
          "excerpt": "There is no MFA. There is no documented session-revocation surface"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Add AAL target to tech_plan §4; couple with MFA introduction."
      },
      "mappings": {
        "nist": [
          "IA-2",
          "IA-2(1)",
          "IA-2(2)",
          "IA-2(8)"
        ],
        "attack": [],
        "cwe": [
          "CWE-308"
        ],
        "owasp_api": [
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "AAL target declaration per deploy intent",
        "Per-surface AAL declaration"
      ]
    },
    {
      "id": "nonrep-7fad26d8",
      "title": "No application-level audit log for consequential actions across any service",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Per runbook §8: GAP. No audit log; only LOG_LEVEL=INFO stdout. No actor attribution, no schema, no retention.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§8 Inspect audit data",
          "excerpt": "GAP. No application-level audit log is shipped"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Define audit schema; emit per consequential action with actor attribution; ship to separate sink."
      },
      "mappings": {
        "nist": [
          "AU-2",
          "AU-3",
          "AU-3(1)",
          "AU-3(3)",
          "AU-6",
          "AU-12",
          "AU-12(1)"
        ],
        "attack": [
          "T1562"
        ],
        "cwe": [
          "CWE-778",
          "CWE-223"
        ],
        "owasp_api": [
          "API9:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 9
    },
    {
      "id": "nonrep-fa2c351c",
      "title": "OTP issuance and verification not audit-logged at application layer",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "ADR-0003 explicit: identity does not audit-log dispatch; mailhog records SMTP envelope only.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "adrs/0003-mailhog-for-otp-delivery.md",
          "locator": "Consequences",
          "excerpt": "OTP delivery is unattributed at the application layer"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Audit-log OTP issuance and verification per nonrep-7fad26d8 schema with source IP / user-agent."
      },
      "mappings": {
        "nist": [
          "AU-2",
          "AU-3",
          "AU-12",
          "AU-10"
        ],
        "attack": [],
        "cwe": [
          "CWE-778"
        ],
        "owasp_api": [
          "API9:2023",
          "API2:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "nonrep-304b32af",
      "title": "No source IP / user-agent attribution on any consequential action",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Runbook §10: no source IP/UA in audit trail; per-request actor context missing.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§10 Respond to user account takeover",
          "excerpt": "There is no source IP / user-agent in the audit trail"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Propagate source IP, user-agent, request-id from OpenResty into backend services; include in every audit event."
      },
      "mappings": {
        "nist": [
          "AU-3",
          "AU-3(1)",
          "AU-3(3)"
        ],
        "attack": [],
        "cwe": [
          "CWE-778"
        ],
        "owasp_api": [
          "API9:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "nonrep-9faa010e",
      "title": "Audit shipping reliability — no documented shipper, retention, or buffering posture",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "Runbook §8 punts log-shipper/retention/schema/tamper-evidence to operator.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§8 Inspect audit data",
          "excerpt": "A log shipper (Fluent Bit, Filebeat) collecting per-container stdout. A retention policy. A schema. Tamper-evidence"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "When nonrep-7fad26d8 is addressed, ship via buffered, retry-aware shipper with documented dead-letter."
      },
      "mappings": {
        "nist": [
          "AU-4",
          "AU-5",
          "AU-5(1)",
          "AU-5(2)"
        ],
        "attack": [],
        "cwe": [
          "CWE-778"
        ],
        "owasp_api": [
          "API9:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Operator-chosen log shipper and aggregator",
        "Retention policy",
        "Shipping reliability posture"
      ]
    },
    {
      "id": "nonrep-c32e3967",
      "title": "Time-source policy unspecified — audit timestamps will be local clocks without drift bounds",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "No NTP policy, no drift bounds; per-container clock drift defeats forensic ordering.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§8",
          "excerpt": "Tamper-evidence on stored logs (currently none)"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Document NTP posture: chrony on host; drift bound <1s for audit consistency."
      },
      "mappings": {
        "nist": [
          "AU-8",
          "AU-8(1)"
        ],
        "attack": [],
        "cwe": [
          "CWE-829"
        ],
        "owasp_api": [
          "API9:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Host time-source posture",
        "Per-container clock-source declaration"
      ]
    },
    {
      "id": "nonrep-b9ba65ab",
      "title": "No audit-of-audit-access; audit access controls undefined because audit does not exist",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Rubric requires separate-role audit access and audit-of-audit-access; both contingent on audit existing.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§8",
          "excerpt": "What an operator would need: A log shipper. A retention policy. A schema. Tamper-evidence on stored logs"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Design audit-introduction with separate-role audit access and audit-of-audit-access emission."
      },
      "mappings": {
        "nist": [
          "AU-9",
          "AU-9(4)",
          "AU-9(6)",
          "AC-5",
          "AC-6"
        ],
        "attack": [],
        "cwe": [
          "CWE-732"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "nonrep-af88acb6",
      "title": "Break-glass and emergency-action audit not designed",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Runbook lacks emergency-action procedure; no distinguishable audit stream for break-glass events.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§10 Respond to user account takeover",
          "excerpt": "Cannot invalidate the attacker's session"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, add break-glass procedures and dedicated audit streams."
      },
      "mappings": {
        "nist": [
          "AU-3",
          "AU-12(1)",
          "AC-6(9)",
          "AC-6(10)",
          "IR-4"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [
          "API9:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "immut-e50364e4",
      "title": "Audit substrate is mutable — no append-only, WORM, or hash-chain",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "When audit is introduced (nonrep-7fad26d8), substrate must enforce immutability; default would land in Postgres/Mongo.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§8",
          "excerpt": "Tamper-evidence on stored logs (currently none)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Ship audit to WORM substrate (object-lock S3, append-only Loki, or hash-chained Postgres audit-table)."
      },
      "mappings": {
        "nist": [
          "AU-9",
          "AU-9(2)",
          "AU-9(3)",
          "AU-11",
          "SI-7",
          "SI-7(8)"
        ],
        "attack": [
          "T1070"
        ],
        "cwe": [
          "CWE-117",
          "CWE-778"
        ],
        "owasp_api": [
          "API9:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "immut-a6c69999",
      "title": "Backup immutability not addressed — no backups exist; ransomware resilience absent",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "Per rubric backups must be immutable; crAPI has no backups (avail-8ad04f0e).",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 Persistence and storage",
          "excerpt": "Backups: unspecified. No backup, restore, or PITR procedure ships"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "When backups introduced (avail-8ad04f0e), use S3 object-lock compliance mode, ≥30 days primary, ≥1 year monthlies."
      },
      "mappings": {
        "nist": [
          "CP-9",
          "CP-9(1)",
          "CP-9(8)",
          "MP-4",
          "SI-7"
        ],
        "attack": [
          "T1490"
        ],
        "cwe": [
          "CWE-1188"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Backup procedure introduction per avail-8ad04f0e",
        "Choice of backup substrate"
      ]
    },
    {
      "id": "immut-79a844dd",
      "title": "Configuration spread across compose env, env-vars, mounted files, and hard-coded binary — no drift detection",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "ENABLE_LOG4J/SHELL flags, JWKS file, gateway basic-auth in binary; no declared baseline.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§9 Implicit posture facts",
          "excerpt": "Postgres + Mongo creds are static literals in the compose file. JWT_SECRET=crapi shipped alongside the RS256 keys"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Declare baseline in IaC (Helm values + compose with required overrides); add config-drift check."
      },
      "mappings": {
        "nist": [
          "CM-2",
          "CM-2(2)",
          "CM-3",
          "CM-3(1)",
          "CM-6",
          "CM-6(1)",
          "CM-6(2)"
        ],
        "attack": [],
        "cwe": [
          "CWE-1357"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "immut-c97f668f",
      "title": "Configuration repository protected-branch / signed-commit posture unspecified",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "medium",
      "disposition": "blocked",
      "summary": "Project repo branch-protection and signed-commit settings not in input scope.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "prior-audit.md",
          "locator": "§Source",
          "excerpt": "synthesised from the upstream OWASP crAPI documentation and the shipped artifacts"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Upstream recommendation: protected main, required signed commits, PR review for security paths."
      },
      "mappings": {
        "nist": [
          "CM-3",
          "CM-3(1)",
          "SI-7(8)",
          "SA-10",
          "SR-4"
        ],
        "attack": [],
        "cwe": [
          "CWE-345"
        ],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "GitHub repo branch-protection settings",
        "Signed-commit requirement status"
      ]
    },
    {
      "id": "immut-b74ae78a",
      "title": "No SBOM, no per-deployment artifact-provenance history",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Upstream does not publish per-version SBOMs nor SLSA provenance; chain from running image to source commit unverifiable.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§2 Services",
          "excerpt": "crapi/crapi-identity:${VERSION}"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Upstream: publish SBOMs per release; integrate SLSA-3 build provenance."
      },
      "mappings": {
        "nist": [
          "SR-4",
          "SR-4(3)",
          "CM-8",
          "AU-11",
          "SR-11"
        ],
        "attack": [
          "T1195"
        ],
        "cwe": [],
        "owasp_api": [
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "immut-49cb874c",
      "title": "Cryptographic key lifecycle events not auditable",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "No record of jwks.json mutation or credential rotation; key-lifecycle events go unaudited.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "runbook.md",
          "locator": "§5 Rotate the JWT signing key",
          "excerpt": "GAP. No documented procedure ships"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "When rotation tooling added, rotation scripts emit key-lifecycle audit events."
      },
      "mappings": {
        "nist": [
          "AU-3",
          "AU-12",
          "SC-12",
          "IA-5"
        ],
        "attack": [],
        "cwe": [
          "CWE-778"
        ],
        "owasp_api": [
          "API9:2023",
          "API8:2023"
        ],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": []
    },
    {
      "id": "immut-56949f0a",
      "title": "Retention policy for any data class is unspecified",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "blocked",
      "summary": "No per-data-class retention declared; rubric requires regulatory-anchored retention.",
      "detail": "See finding source.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§10 Out-of-scope",
          "excerpt": "Operational hardening. crAPI does not target production deployment. No on-call posture, no SLO commitments, no key rotation, no log retention"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "For non-demo deploys, declare per-data-class retention in tech_plan §11 with regulatory citation."
      },
      "mappings": {
        "nist": [
          "AU-11",
          "AU-11(1)",
          "SI-12"
        ],
        "attack": [],
        "cwe": [],
        "owasp_api": [],
        "owasp": [],
        "d3fend": []
      },
      "lens_perspectives": [],
      "prerequisite_evidence": [
        "Deploy intent and regulatory anchors",
        "Per-data-class retention table"
      ]
    }
  ],
  "contradictions": [],
  "severity_disagreements": [],
  "nist_rollup": [],
  "attack_exposure": [],
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
    "rows": []
  },
  "attack_paths": {
    "mermaid": "graph TD\n  asset-a1b2c3d4[\"crapi-identity\"]\n  asset-a3b4c5d6[\"API_USER/API_PASSWORD (chatbot admin credential)\"]\n  asset-a7b8c9d0[\"mongodb\"]\n  asset-b2c3d4e5[\"crapi-workshop\"]\n  asset-b8c9d0e1[\"chromadb\"]\n  asset-c3d4e5f6[\"crapi-community\"]\n  asset-c9d0e1f2[\"mailhog\"]\n  asset-d0e1f2a3[\"api.mypremiumdealership.com\"]\n  asset-d4e5f6a7[\"crapi-chatbot\"]\n  asset-e1f2a3b4[\"services/identity/jwks.json (private key)\"]\n  asset-e5f6a7b8[\"crapi-web\"]\n  asset-f2a3b4c5[\"JWT_SECRET env var\"]\n  asset-f6a7b8c9[\"postgresdb\"]\n  atk-264bde5f((\"internal_lateral_attacker\"))\n  atk-2a628eed((\"authenticated_user_seeking_authz_bypass\"))\n  atk-3f205280((\"compromised_admin_session\"))\n  atk-404a3c86((\"unauthenticated_internet\"))\n  atk-43ba1c0a((\"supply_chain_attacker\"))\n  atk-5331accf((\"compromised_user_session_token\"))\n  atk-5ec33a11((\"compromised_oauth_client_credentials\"))\n  atk-82a39ff7((\"authenticated_low_priv_user_with_bola_target\"))\n  atk-a3d36625((\"compromised_third_party_integration\"))\n  jewel-10ff98db{{\"session_token_signing_keys\"}}\n  jewel-168c256c{{\"backup_artifact_store\"}}\n  jewel-277b3f04{{\"third_party_integration_secrets\"}}\n  jewel-3257f37f{{\"pii_profile_store\"}}\n  jewel-47b02c84{{\"payment_methods_store\"}}\n  jewel-4da600e8{{\"audit_log_store\"}}\n  jewel-61f49a34{{\"authorization_decision_engine\"}}\n  jewel-681465d8{{\"user_credentials_store\"}}\n  asset-d0e1f2a3 --> asset-a1b2c3d4\n  asset-d0e1f2a3 --> asset-d4e5f6a7\n  asset-c9d0e1f2 --> asset-a1b2c3d4\n  asset-a1b2c3d4 --> asset-c9d0e1f2\n  asset-a7b8c9d0 --> asset-f6a7b8c9\n  asset-a1b2c3d4 --> asset-e5f6a7b8\n  asset-a1b2c3d4 --> asset-e5f6a7b8\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-e5f6a7b8 --> asset-d0e1f2a3\n  asset-a1b2c3d4 --> asset-d0e1f2a3\n  asset-a7b8c9d0 --> asset-b8c9d0e1\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-b8c9d0e1 --> asset-d0e1f2a3\n  asset-d0e1f2a3 --> asset-e5f6a7b8\n  asset-f6a7b8c9 --> asset-b8c9d0e1\n  asset-d4e5f6a7 --> asset-d0e1f2a3\n  asset-e5f6a7b8 --> asset-a1b2c3d4",
    "pairs": [],
    "bottleneck_overlays": [],
    "summary": {
      "total_paths": 0,
      "total_pairs": 0,
      "bottleneck_count": 0
    }
  },
  "next_steps": [
    {
      "rank": 1,
      "text": "Generate a fresh per-install JWKS, pin alg:RS256 in every verifier, remove JWT_SECRET, and allowlist jku — single highest-leverage fix; closes the cluster-wide forge-any-identity capability.",
      "refs": [
        "merged-c829ffc8",
        "ephem-30d38360",
        "dist-0a56c5f0"
      ]
    },
    {
      "rank": 2,
      "text": "Add MFA (TOTP for users, WebAuthn step-up for admin) on every authentication surface; bring AAL target into tech_plan.md.",
      "refs": [
        "auth-0925a719",
        "auth-b57f022f",
        "auth-c990b0ff"
      ]
    },
    {
      "rank": 3,
      "text": "Apply allowlist serializers + server-side validation to /shop/orders (quantity ≥ 1, server-derived unit_price), /user/videos/{id} (strip internal fields), and any user-update path (strip role).",
      "refs": [
        "intg-e7ebcc95",
        "intg-62ebf664",
        "intg-a6b6d147",
        "intg-6d98c520"
      ]
    },
    {
      "rank": 4,
      "text": "Parameterize every SQL/Mongo query path — apply_coupon (parameterized UPDATE) and validate-coupon (typed-struct unmarshal); add CI lint to fail on string-concatenated SQL.",
      "refs": [
        "intg-2aeb03f1",
        "intg-b7417f91",
        "intg-ab3edc7a"
      ]
    },
    {
      "rank": 5,
      "text": "Remove the chatbot's embedded admin credential; chatbot acts under the prompt author's bearer token with a tool-call allowlist per user role.",
      "refs": [
        "merged-d2e871f5"
      ]
    },
    {
      "rank": 6,
      "text": "Add typed URL allowlist + IP-resolution check + per-token rate limit + drop response body on /contact_mechanic outbound fetch.",
      "refs": [
        "merged-514507e6"
      ]
    },
    {
      "rank": 7,
      "text": "Provision per-service Postgres+Mongo users with collection-scoped grants; remove static credentials from compose; rotate per-deploy.",
      "refs": [
        "merged-44bdb663",
        "ephem-22c2358c"
      ]
    },
    {
      "rank": 8,
      "text": "Define an audit-event schema, emit per consequential action with actor attribution, ship to a separate WORM-substrate sink (S3 object-lock).",
      "refs": [
        "nonrep-7fad26d8",
        "immut-e50364e4",
        "nonrep-fa2c351c",
        "nonrep-304b32af"
      ]
    },
    {
      "rank": 9,
      "text": "Drop JWT TTL to 1 hour; introduce refresh-token rotation with reuse-detection; expose /logout backed by a JTI deny-list.",
      "refs": [
        "resil-776fc650",
        "ephem-96d3befb"
      ]
    },
    {
      "rank": 10,
      "text": "Apply uniform rate limits across every check-otp variant, forget-password, and login; increase OTP entropy to ≥6 digits.",
      "refs": [
        "avail-e96ad7ff",
        "avail-c1ffcf8e"
      ]
    }
  ],
  "taxonomy": {
    "AC-12": {
      "family": "NIST 800-53r5",
      "title": "AC-12"
    },
    "AC-12(1)": {
      "family": "NIST 800-53r5",
      "title": "AC-12(1)"
    },
    "AC-2": {
      "family": "NIST 800-53r5",
      "title": "AC-2"
    },
    "AC-2(2)": {
      "family": "NIST 800-53r5",
      "title": "AC-2(2)"
    },
    "AC-2(3)": {
      "family": "NIST 800-53r5",
      "title": "AC-2(3)"
    },
    "AC-3": {
      "family": "NIST 800-53r5",
      "title": "AC-3"
    },
    "AC-3(7)": {
      "family": "NIST 800-53r5",
      "title": "AC-3(7)"
    },
    "AC-4": {
      "family": "NIST 800-53r5",
      "title": "AC-4"
    },
    "AC-5": {
      "family": "NIST 800-53r5",
      "title": "AC-5"
    },
    "AC-6": {
      "family": "NIST 800-53r5",
      "title": "AC-6"
    },
    "AC-6(1)": {
      "family": "NIST 800-53r5",
      "title": "AC-6(1)"
    },
    "AC-6(10)": {
      "family": "NIST 800-53r5",
      "title": "AC-6(10)"
    },
    "AC-6(5)": {
      "family": "NIST 800-53r5",
      "title": "AC-6(5)"
    },
    "AC-6(7)": {
      "family": "NIST 800-53r5",
      "title": "AC-6(7)"
    },
    "AC-6(9)": {
      "family": "NIST 800-53r5",
      "title": "AC-6(9)"
    },
    "AC-7": {
      "family": "NIST 800-53r5",
      "title": "AC-7"
    },
    "AC-7(2)": {
      "family": "NIST 800-53r5",
      "title": "AC-7(2)"
    },
    "AU-10": {
      "family": "NIST 800-53r5",
      "title": "AU-10"
    },
    "AU-11": {
      "family": "NIST 800-53r5",
      "title": "AU-11"
    },
    "AU-11(1)": {
      "family": "NIST 800-53r5",
      "title": "AU-11(1)"
    },
    "AU-12": {
      "family": "NIST 800-53r5",
      "title": "AU-12"
    },
    "AU-12(1)": {
      "family": "NIST 800-53r5",
      "title": "AU-12(1)"
    },
    "AU-2": {
      "family": "NIST 800-53r5",
      "title": "AU-2"
    },
    "AU-3": {
      "family": "NIST 800-53r5",
      "title": "AU-3"
    },
    "AU-3(1)": {
      "family": "NIST 800-53r5",
      "title": "AU-3(1)"
    },
    "AU-3(3)": {
      "family": "NIST 800-53r5",
      "title": "AU-3(3)"
    },
    "AU-4": {
      "family": "NIST 800-53r5",
      "title": "AU-4"
    },
    "AU-5": {
      "family": "NIST 800-53r5",
      "title": "AU-5"
    },
    "AU-5(1)": {
      "family": "NIST 800-53r5",
      "title": "AU-5(1)"
    },
    "AU-5(2)": {
      "family": "NIST 800-53r5",
      "title": "AU-5(2)"
    },
    "AU-6": {
      "family": "NIST 800-53r5",
      "title": "AU-6"
    },
    "AU-8": {
      "family": "NIST 800-53r5",
      "title": "AU-8"
    },
    "AU-8(1)": {
      "family": "NIST 800-53r5",
      "title": "AU-8(1)"
    },
    "AU-9": {
      "family": "NIST 800-53r5",
      "title": "AU-9"
    },
    "AU-9(2)": {
      "family": "NIST 800-53r5",
      "title": "AU-9(2)"
    },
    "AU-9(3)": {
      "family": "NIST 800-53r5",
      "title": "AU-9(3)"
    },
    "AU-9(4)": {
      "family": "NIST 800-53r5",
      "title": "AU-9(4)"
    },
    "AU-9(6)": {
      "family": "NIST 800-53r5",
      "title": "AU-9(6)"
    },
    "CM-2": {
      "family": "NIST 800-53r5",
      "title": "CM-2"
    },
    "CM-2(2)": {
      "family": "NIST 800-53r5",
      "title": "CM-2(2)"
    },
    "CM-3": {
      "family": "NIST 800-53r5",
      "title": "CM-3"
    },
    "CM-3(1)": {
      "family": "NIST 800-53r5",
      "title": "CM-3(1)"
    },
    "CM-5": {
      "family": "NIST 800-53r5",
      "title": "CM-5"
    },
    "CM-6": {
      "family": "NIST 800-53r5",
      "title": "CM-6"
    },
    "CM-6(1)": {
      "family": "NIST 800-53r5",
      "title": "CM-6(1)"
    },
    "CM-6(2)": {
      "family": "NIST 800-53r5",
      "title": "CM-6(2)"
    },
    "CM-7": {
      "family": "NIST 800-53r5",
      "title": "CM-7"
    },
    "CM-7(5)": {
      "family": "NIST 800-53r5",
      "title": "CM-7(5)"
    },
    "CM-8": {
      "family": "NIST 800-53r5",
      "title": "CM-8"
    },
    "CP-10": {
      "family": "NIST 800-53r5",
      "title": "CP-10"
    },
    "CP-10(2)": {
      "family": "NIST 800-53r5",
      "title": "CP-10(2)"
    },
    "CP-12": {
      "family": "NIST 800-53r5",
      "title": "CP-12"
    },
    "CP-13": {
      "family": "NIST 800-53r5",
      "title": "CP-13"
    },
    "CP-2": {
      "family": "NIST 800-53r5",
      "title": "CP-2"
    },
    "CP-2(3)": {
      "family": "NIST 800-53r5",
      "title": "CP-2(3)"
    },
    "CP-2(5)": {
      "family": "NIST 800-53r5",
      "title": "CP-2(5)"
    },
    "CP-7": {
      "family": "NIST 800-53r5",
      "title": "CP-7"
    },
    "CP-9": {
      "family": "NIST 800-53r5",
      "title": "CP-9"
    },
    "CP-9(1)": {
      "family": "NIST 800-53r5",
      "title": "CP-9(1)"
    },
    "CP-9(8)": {
      "family": "NIST 800-53r5",
      "title": "CP-9(8)"
    },
    "IA-2": {
      "family": "NIST 800-53r5",
      "title": "IA-2"
    },
    "IA-2(1)": {
      "family": "NIST 800-53r5",
      "title": "IA-2(1)"
    },
    "IA-2(2)": {
      "family": "NIST 800-53r5",
      "title": "IA-2(2)"
    },
    "IA-2(6)": {
      "family": "NIST 800-53r5",
      "title": "IA-2(6)"
    },
    "IA-2(8)": {
      "family": "NIST 800-53r5",
      "title": "IA-2(8)"
    },
    "IA-3": {
      "family": "NIST 800-53r5",
      "title": "IA-3"
    },
    "IA-5": {
      "family": "NIST 800-53r5",
      "title": "IA-5"
    },
    "IA-5(1)": {
      "family": "NIST 800-53r5",
      "title": "IA-5(1)"
    },
    "IA-5(13)": {
      "family": "NIST 800-53r5",
      "title": "IA-5(13)"
    },
    "IA-5(2)": {
      "family": "NIST 800-53r5",
      "title": "IA-5(2)"
    },
    "IA-5(7)": {
      "family": "NIST 800-53r5",
      "title": "IA-5(7)"
    },
    "IA-9": {
      "family": "NIST 800-53r5",
      "title": "IA-9"
    },
    "IR-4": {
      "family": "NIST 800-53r5",
      "title": "IR-4"
    },
    "MP-4": {
      "family": "NIST 800-53r5",
      "title": "MP-4"
    },
    "SA-10": {
      "family": "NIST 800-53r5",
      "title": "SA-10"
    },
    "SA-15(7)": {
      "family": "NIST 800-53r5",
      "title": "SA-15(7)"
    },
    "SC-10": {
      "family": "NIST 800-53r5",
      "title": "SC-10"
    },
    "SC-12": {
      "family": "NIST 800-53r5",
      "title": "SC-12"
    },
    "SC-12(1)": {
      "family": "NIST 800-53r5",
      "title": "SC-12(1)"
    },
    "SC-12(2)": {
      "family": "NIST 800-53r5",
      "title": "SC-12(2)"
    },
    "SC-13": {
      "family": "NIST 800-53r5",
      "title": "SC-13"
    },
    "SC-17": {
      "family": "NIST 800-53r5",
      "title": "SC-17"
    },
    "SC-22": {
      "family": "NIST 800-53r5",
      "title": "SC-22"
    },
    "SC-23": {
      "family": "NIST 800-53r5",
      "title": "SC-23"
    },
    "SC-23(3)": {
      "family": "NIST 800-53r5",
      "title": "SC-23(3)"
    },
    "SC-28": {
      "family": "NIST 800-53r5",
      "title": "SC-28"
    },
    "SC-28(1)": {
      "family": "NIST 800-53r5",
      "title": "SC-28(1)"
    },
    "SC-36": {
      "family": "NIST 800-53r5",
      "title": "SC-36"
    },
    "SC-5": {
      "family": "NIST 800-53r5",
      "title": "SC-5"
    },
    "SC-5(1)": {
      "family": "NIST 800-53r5",
      "title": "SC-5(1)"
    },
    "SC-6": {
      "family": "NIST 800-53r5",
      "title": "SC-6"
    },
    "SC-7": {
      "family": "NIST 800-53r5",
      "title": "SC-7"
    },
    "SC-7(21)": {
      "family": "NIST 800-53r5",
      "title": "SC-7(21)"
    },
    "SC-7(5)": {
      "family": "NIST 800-53r5",
      "title": "SC-7(5)"
    },
    "SC-8": {
      "family": "NIST 800-53r5",
      "title": "SC-8"
    },
    "SC-8(1)": {
      "family": "NIST 800-53r5",
      "title": "SC-8(1)"
    },
    "SI-10": {
      "family": "NIST 800-53r5",
      "title": "SI-10"
    },
    "SI-10(5)": {
      "family": "NIST 800-53r5",
      "title": "SI-10(5)"
    },
    "SI-12": {
      "family": "NIST 800-53r5",
      "title": "SI-12"
    },
    "SI-13": {
      "family": "NIST 800-53r5",
      "title": "SI-13"
    },
    "SI-13(4)": {
      "family": "NIST 800-53r5",
      "title": "SI-13(4)"
    },
    "SI-15": {
      "family": "NIST 800-53r5",
      "title": "SI-15"
    },
    "SI-17": {
      "family": "NIST 800-53r5",
      "title": "SI-17"
    },
    "SI-4": {
      "family": "NIST 800-53r5",
      "title": "SI-4"
    },
    "SI-7": {
      "family": "NIST 800-53r5",
      "title": "SI-7"
    },
    "SI-7(1)": {
      "family": "NIST 800-53r5",
      "title": "SI-7(1)"
    },
    "SI-7(8)": {
      "family": "NIST 800-53r5",
      "title": "SI-7(8)"
    },
    "SR-11": {
      "family": "NIST 800-53r5",
      "title": "SR-11"
    },
    "SR-4": {
      "family": "NIST 800-53r5",
      "title": "SR-4"
    },
    "SR-4(3)": {
      "family": "NIST 800-53r5",
      "title": "SR-4(3)"
    },
    "SR-4(4)": {
      "family": "NIST 800-53r5",
      "title": "SR-4(4)"
    },
    "T1070": {
      "family": "MITRE ATT&CK",
      "title": "T1070"
    },
    "T1078": {
      "family": "MITRE ATT&CK",
      "title": "T1078"
    },
    "T1110": {
      "family": "MITRE ATT&CK",
      "title": "T1110"
    },
    "T1190": {
      "family": "MITRE ATT&CK",
      "title": "T1190"
    },
    "T1195": {
      "family": "MITRE ATT&CK",
      "title": "T1195"
    },
    "T1213": {
      "family": "MITRE ATT&CK",
      "title": "T1213"
    },
    "T1490": {
      "family": "MITRE ATT&CK",
      "title": "T1490"
    },
    "T1499": {
      "family": "MITRE ATT&CK",
      "title": "T1499"
    },
    "T1550": {
      "family": "MITRE ATT&CK",
      "title": "T1550"
    },
    "T1552": {
      "family": "MITRE ATT&CK",
      "title": "T1552"
    },
    "T1557": {
      "family": "MITRE ATT&CK",
      "title": "T1557"
    },
    "T1562": {
      "family": "MITRE ATT&CK",
      "title": "T1562"
    },
    "T1606": {
      "family": "MITRE ATT&CK",
      "title": "T1606"
    },
    "CWE-1088": {
      "family": "CWE",
      "title": "Synchronous Access of Remote Resource without Timeout"
    },
    "CWE-117": {
      "family": "CWE",
      "title": "Improper Output Neutralization for Logs"
    },
    "CWE-1188": {
      "family": "CWE",
      "title": "Initialization of a Resource with an Insecure Default"
    },
    "CWE-1357": {
      "family": "CWE",
      "title": "Reliance on Insufficiently Trustworthy Component"
    },
    "CWE-20": {
      "family": "CWE",
      "title": "Improper Input Validation"
    },
    "CWE-200": {
      "family": "CWE",
      "title": "Exposure of Sensitive Information to an Unauthorized Actor"
    },
    "CWE-213": {
      "family": "CWE",
      "title": "Exposure of Sensitive Information Due to Incompatible Policies"
    },
    "CWE-22": {
      "family": "CWE",
      "title": "Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')"
    },
    "CWE-223": {
      "family": "CWE",
      "title": "Omission of Security-relevant Information"
    },
    "CWE-250": {
      "family": "CWE",
      "title": "Execution with Unnecessary Privileges"
    },
    "CWE-256": {
      "family": "CWE",
      "title": "Plaintext Storage of a Password"
    },
    "CWE-269": {
      "family": "CWE",
      "title": "Improper Privilege Management"
    },
    "CWE-285": {
      "family": "CWE",
      "title": "Improper Authorization"
    },
    "CWE-287": {
      "family": "CWE",
      "title": "Improper Authentication"
    },
    "CWE-306": {
      "family": "CWE",
      "title": "Missing Authentication for Critical Function"
    },
    "CWE-307": {
      "family": "CWE",
      "title": "Improper Restriction of Excessive Authentication Attempts"
    },
    "CWE-308": {
      "family": "CWE",
      "title": "Use of Single-factor Authentication"
    },
    "CWE-311": {
      "family": "CWE",
      "title": "Missing Encryption of Sensitive Data"
    },
    "CWE-312": {
      "family": "CWE",
      "title": "Cleartext Storage of Sensitive Information"
    },
    "CWE-319": {
      "family": "CWE",
      "title": "Cleartext Transmission of Sensitive Information"
    },
    "CWE-321": {
      "family": "CWE",
      "title": "Use of Hard-coded Cryptographic Key"
    },
    "CWE-326": {
      "family": "CWE",
      "title": "Inadequate Encryption Strength"
    },
    "CWE-340": {
      "family": "CWE",
      "title": "Generation of Predictable Numbers or Identifiers"
    },
    "CWE-345": {
      "family": "CWE",
      "title": "Insufficient Verification of Data Authenticity"
    },
    "CWE-347": {
      "family": "CWE",
      "title": "Improper Verification of Cryptographic Signature"
    },
    "CWE-362": {
      "family": "CWE",
      "title": "Concurrent Execution using Shared Resource with Improper Synchronization ('Race Condition')"
    },
    "CWE-384": {
      "family": "CWE",
      "title": "Session Fixation"
    },
    "CWE-400": {
      "family": "CWE",
      "title": "Uncontrolled Resource Consumption"
    },
    "CWE-405": {
      "family": "CWE",
      "title": "Asymmetric Resource Consumption (Amplification)"
    },
    "CWE-441": {
      "family": "CWE",
      "title": "Unintended Proxy or Intermediary ('Confused Deputy')"
    },
    "CWE-532": {
      "family": "CWE",
      "title": "Insertion of Sensitive Information into Log File"
    },
    "CWE-613": {
      "family": "CWE",
      "title": "Insufficient Session Expiration"
    },
    "CWE-639": {
      "family": "CWE",
      "title": "Authorization Bypass Through User-Controlled Key"
    },
    "CWE-640": {
      "family": "CWE",
      "title": "Weak Password Recovery Mechanism for Forgotten Password"
    },
    "CWE-732": {
      "family": "CWE",
      "title": "Incorrect Permission Assignment for Critical Resource"
    },
    "CWE-754": {
      "family": "CWE",
      "title": "Improper Check for Unusual or Exceptional Conditions"
    },
    "CWE-755": {
      "family": "CWE",
      "title": "Improper Handling of Exceptional Conditions"
    },
    "CWE-77": {
      "family": "CWE",
      "title": "Improper Neutralization of Special Elements used in a Command ('Command Injection')"
    },
    "CWE-770": {
      "family": "CWE",
      "title": "Allocation of Resources Without Limits or Throttling"
    },
    "CWE-778": {
      "family": "CWE",
      "title": "Insufficient Logging"
    },
    "CWE-78": {
      "family": "CWE",
      "title": "Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')"
    },
    "CWE-798": {
      "family": "CWE",
      "title": "Use of Hard-coded Credentials"
    },
    "CWE-829": {
      "family": "CWE",
      "title": "Inclusion of Functionality from Untrusted Control Sphere"
    },
    "CWE-840": {
      "family": "CWE",
      "title": "CWE-840"
    },
    "CWE-862": {
      "family": "CWE",
      "title": "Missing Authorization"
    },
    "CWE-89": {
      "family": "CWE",
      "title": "Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')"
    },
    "CWE-915": {
      "family": "CWE",
      "title": "Improperly Controlled Modification of Dynamically-Determined Object Attributes"
    },
    "CWE-916": {
      "family": "CWE",
      "title": "Use of Password Hash With Insufficient Computational Effort"
    },
    "CWE-918": {
      "family": "CWE",
      "title": "Server-Side Request Forgery (SSRF)"
    },
    "CWE-94": {
      "family": "CWE",
      "title": "Improper Control of Generation of Code ('Code Injection')"
    },
    "CWE-943": {
      "family": "CWE",
      "title": "Improper Neutralization of Special Elements in Data Query Logic"
    }
  }
};
