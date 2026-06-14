window.APD_DATA = {
  "meta": {
    "framework_version": "1.4.0",
    "domain_pack": {
      "name": "pbm",
      "version": "1.0.0"
    },
    "run_id": "apd-20260601-claim-event-bus",
    "synthesizer_version": "1.4.0",
    "specialists_skipped": [
      "threat-model-recon"
    ],
    "subject": "apd-20260601-claim-event-bus",
    "subject_tagline": "",
    "date": "2026-06-13",
    "artifact_count": 0,
    "artifact_types": [],
    "crown_jewels": [
      "phi_store",
      "pde_submission_pipeline"
    ],
    "attacker_positions": [
      "external_internet",
      "compromised_pharmacy_credential",
      "compromised_vendor_integration"
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
      "owasp_api_top10"
    ],
    "has_threat_model": true,
    "section_errors": {},
    "warnings": []
  },
  "summary": {
    "findings_total": 19,
    "findings_pre_dedup": 19,
    "cross_lens_merged_clusters": 0,
    "linked_clusters": 0,
    "bySeverity": {
      "critical": 1,
      "high": 10,
      "medium": 7,
      "low": 1,
      "info": 0
    },
    "byDisposition": {
      "gap": 9,
      "blocked": 3,
      "risk": 5,
      "uncertainty": 2,
      "ok": 0
    },
    "byTier": {
      "trustworthiness": 8,
      "scalability": 4,
      "auditability": 7
    },
    "capabilities_total": 10,
    "capabilities_pre_dedup": 10,
    "capabilitiesByMaturity": {
      "designed": 8,
      "implemented": 2,
      "tested": 0,
      "operationalized": 0
    },
    "contradictions": 1,
    "severity_disagreements": 1
  },
  "exec_summary": [
    "This APD gauntlet run reviews the claim-event-bus reference architecture under the pbm domain pack: a Kafka-based pipeline carrying PHI claim-events across a multi-AZ deployment. The 9-specialist gauntlet assessed operational consequences across all nine APD goals over the deduped corpus plus the attack-path analysis.",
    "The highest-leverage concern is the unsigned, mutably-stored audit log (merged-4dd83f6a, critical): consequential claim actions cannot be reconstructed or proven tamper-free. High-severity gaps cluster around authentication assurance (SMS MFA fallback), availability (single-region 99.95% SLO, untested DR failover), and confidentiality (PHI in the Kafka topic lacking envelope encryption; unspecified KMS DEK rotation)."
  ],
  "posture_summary": {
    "trustworthiness": "PHI in the claim-event topic lacks envelope encryption and DEK rotation is unspecified; Kafka event payloads also lack producer signing (intg-42a3ebbd), leaving end-to-end payload integrity unverified beyond TLS transport.",
    "scalability": "Single-region active-passive topology is the dominant distribution risk, and automatic KMS key rotation is disabled for the MSK cluster key (enable_key_rotation = false, ephem-bff0e958), accumulating cryptographic exposure on the broker at-rest key.",
    "auditability": "The audit log is unsigned and stored in a mutable table — the single critical finding — undermining non-repudiation and tamper-evidence for every consequential claim action."
  },
  "capabilities": [
    {
      "id": "conf-cap-89e19793",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "designed",
      "title": "Field-level envelope encryption on PHI columns at rest",
      "scope": "Confirmed for: member_demographics table (all PHI columns), claims table (member_id, drug_ndc, prescriber_npi). Not addressed: audit_log table, Kafka event payloads."
    },
    {
      "id": "conf-cap-d0590471",
      "tier": "trustworthiness",
      "goal": "confidentiality",
      "maturity": "implemented",
      "title": "MSK cluster with KMS-managed at-rest encryption",
      "scope": "Confirmed for: MSK cluster pbm-claim-events broker storage. Scope is broker-level only; payload-level PHI remains in plaintext at the application layer."
    },
    {
      "id": "intg-cap-d4ef7325",
      "tier": "trustworthiness",
      "goal": "integrity",
      "maturity": "implemented",
      "title": "TLS 1.2 or higher enforced on all Kafka transport paths",
      "scope": "Confirmed for: MSK cluster transport layer (client_broker=TLS, in_cluster=true). Does not cover payload-level end-to-end integrity."
    },
    {
      "id": "avail-cap-39c7f671",
      "tier": "trustworthiness",
      "goal": "availability",
      "maturity": "designed",
      "title": "DR recovery time objective documented at four hours",
      "scope": "Confirmed as documented target for the claim event bus system. Not confirmed as tested or validated through DR exercise."
    },
    {
      "id": "dist-cap-f1542e43",
      "tier": "scalability",
      "goal": "distributed",
      "maturity": "designed",
      "title": "Multi-AZ active-passive deployment within us-east-1",
      "scope": "Confirmed for: MSK cluster broker placement across AZs (6 brokers). Covers intra-region AZ failures only; cross-region failover not implemented."
    },
    {
      "id": "resil-cap-4a157ac3",
      "tier": "scalability",
      "goal": "resilient",
      "maturity": "designed",
      "title": "Kafka replication factor 3 provides broker-level fault tolerance",
      "scope": "Confirmed for: claim-events topic broker replication. Covers broker-level failures; does not address AZ-level or region-level outages."
    },
    {
      "id": "ephem-cap-32d883ee",
      "tier": "scalability",
      "goal": "ephemeral",
      "maturity": "designed",
      "title": "HashiCorp Vault centrally manages service-to-service token lifecycle",
      "scope": "Confirmed for: service-to-service bearer token storage. Vault provides revocation capability; dynamic short-lived token issuance is not yet in use."
    },
    {
      "id": "auth-cap-53d41613",
      "tier": "auditability",
      "goal": "authenticity",
      "maturity": "designed",
      "title": "Okta SAML SSO with mandatory MFA for internal admin tools",
      "scope": "Confirmed for: internal admin tools via SAML SSO with MFA required. Does not cover member portal (separate Okta application with SMS fallback) or service-to-service auth."
    },
    {
      "id": "nonrep-cap-1ca07ca1",
      "tier": "auditability",
      "goal": "non_repudiation",
      "maturity": "designed",
      "title": "Audit log captures authentication events and PHI access actions",
      "scope": "Confirmed for: event types logged (PHI access, config changes, auth events). Does not include user-level attribution, integrity protection, or WORM enforcement."
    },
    {
      "id": "immut-cap-3ce60962",
      "tier": "auditability",
      "goal": "immutability",
      "maturity": "designed",
      "title": "RDS cluster with deletion protection enabled for adjudication data",
      "scope": "Covers RDS cluster-level deletion protection only. Does not address table-level mutability, backup immutability, or audit log WORM protection."
    }
  ],
  "strengths": [
    {
      "id": "conf-cap-d0590471",
      "title": "MSK cluster with KMS-managed at-rest encryption",
      "goal": "confidentiality",
      "maturity": "implemented",
      "caveats": [
        "At-rest KMS encryption only; PHI in the topic still lacks field-level envelope encryption (conf-7aa376c5)",
        "Broker key auto-rotation is disabled (ephem-bff0e958)"
      ]
    },
    {
      "id": "intg-cap-d4ef7325",
      "title": "TLS 1.2 or higher enforced on all Kafka transport paths",
      "goal": "integrity",
      "maturity": "implemented",
      "caveats": [
        "TLS protects transport, not end-to-end payload integrity; events are unsigned (intg-42a3ebbd)"
      ]
    }
  ],
  "findings": [
    {
      "id": "conf-7aa376c5",
      "title": "PHI fields in Kafka claim-events topic lack envelope encryption",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Broker-level encryption only; PHI flows in plaintext between producers and consumers within the broker layer.",
      "detail": "Per the PBM PHI exposure rubric, broker-managed encryption grants all platform admins and consumers access to cleartext PHI. The claim-events topic carries member_id, drug_ndc, prescriber_npi, and pharmacy_id in every event payload. Field-level envelope encryption in the producer SDK is needed to enforce minimum-necessary access at the payload level.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§4.2 paragraph 3",
          "excerpt": "All Kafka topics use AES-256 at-rest encryption via broker-managed keys"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Apply field-level envelope encryption to PHI fields before producer serialization.",
        "detail": "Replace broker-level encryption with envelope encryption applied in the producer SDK before serialization, using DEKs issued by the KMS hierarchy in §3."
      },
      "mappings": {
        "nist": [
          "SC-8(1)",
          "SC-13",
          "SC-28(1)"
        ],
        "attack": [
          "T1530"
        ],
        "cwe": [],
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
      "id": "conf-98a543cd",
      "title": "KMS DEK rotation cadence not specified",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "low",
      "disposition": "blocked",
      "summary": "The tech plan references a DEK-issuer service but does not specify rotation cadence, automation, or revocation procedures.",
      "detail": "Without a defined rotation policy, long-lived DEKs increase the window of exposure if a key is compromised. HIPAA requires documented key management procedures. The tech plan explicitly calls out this gap at §3.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§3 paragraph 4",
          "excerpt": "rotation cadence, automation, and revocation procedure are NOT specified in this tech plan"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Document and enforce a DEK rotation schedule with automated key revocation.",
        "detail": "Define rotation cadence (e.g., 90-day maximum), automate rotation via KMS key aliases, and document a tested revocation runbook before GA."
      },
      "mappings": {
        "nist": [
          "SC-12",
          "SC-12(1)"
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
        "DEK rotation policy document with cadence, automation trigger, and revocation runbook"
      ],
      "headline": true,
      "headline_rank": 6
    },
    {
      "id": "conf-e443de8b",
      "title": "Service-to-service authentication uses shared bearer tokens",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "medium",
      "confidence": "high",
      "disposition": "risk",
      "summary": "All service-to-service calls use shared bearer tokens from Vault rather than per-service mTLS identities.",
      "detail": "Shared bearer tokens create broad blast-radius if a single token is exfiltrated. A compromised service can impersonate any other service that shares the same token. mTLS or per-service SPIFFE/SPIRE identities would enforce least-privilege service identity.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§8 paragraph 4",
          "excerpt": "Service-to-service: shared bearer tokens stored in HashiCorp Vault"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Replace shared bearer tokens with per-service mTLS certificates or SPIFFE identities.",
        "detail": "Issue per-service X.509 certificates via a service mesh (e.g., Istio) or SPIRE. Revoke shared tokens once migration is validated."
      },
      "mappings": {
        "nist": [
          "IA-3",
          "SC-8(1)"
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
    },
    {
      "id": "intg-42a3ebbd",
      "title": "Kafka event messages lack producer payload signing",
      "goal": "integrity",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "TLS secures transit but provides no end-to-end payload integrity guarantee; a compromised broker or consumer can receive tampered events without detection.",
      "detail": "The threat model notes 'no end-to-end payload integrity check' for the claim-events topic. An adversary with broker access or a man-in-the-middle post-TLS-termination can modify adjudication outcome events without consumers detecting the tampering. HMAC or digital signatures on the payload would provide end-to-end integrity.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "Tampering paragraph 2",
          "excerpt": "TLS in transit; no end-to-end payload integrity check"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Add HMAC or producer-signed envelope to every claim event payload.",
        "detail": "Sign each ClaimEvent with the producer's asymmetric key or an HMAC derived from a shared secret provisioned via KMS. Consumers must verify the signature before processing."
      },
      "mappings": {
        "nist": [
          "SC-8(1)",
          "SI-7",
          "SI-7(1)"
        ],
        "attack": [
          "T1565"
        ],
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
    },
    {
      "id": "avail-ce35b2ed",
      "title": "DR failover has not been tested in the past 12 months",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The tech plan documents RTO and RPO targets but acknowledges DR failover has not been exercised in over a year.",
      "detail": "An untested DR procedure provides no assurance that RTO of 4 hours or RPO of 15 minutes can actually be met during an incident. NIST SP 800-34 requires periodic DR exercises. Without a tested runbook, the documented targets are aspirational rather than verified.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 paragraph 3",
          "excerpt": "DR failover has not been tested in the last 12 months"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Execute a full DR failover test and update the runbook with observed RTO and RPO metrics.",
        "detail": "Schedule a DR exercise within 90 days. Record actual RTO and RPO against targets. If targets are missed, update the SLO commitments or invest in automation to close the gap."
      },
      "mappings": {
        "nist": [
          "CP-4",
          "CP-4(1)"
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
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 4
    },
    {
      "id": "avail-4e08f6d8",
      "title": "99.95 percent SLO target with single-region active-passive topology",
      "goal": "availability",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "risk",
      "summary": "The 99.95% availability SLO relies solely on multi-AZ within us-east-1; a regional AWS outage would breach this target.",
      "detail": "us-east-1 experiences periodic multi-AZ outages that exceed the allowable downtime window for a 99.95% monthly SLO (approximately 22 minutes/month). The tech plan explicitly states cross-region failover is not yet implemented. The SLO target may be unachievable under realistic failure scenarios.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§6 paragraph 1",
          "excerpt": "system targets 99.95% uptime over a rolling 30-day window"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Implement cross-region active-passive or reduce the SLO commitment to match the single-region topology.",
        "detail": "Either implement automated cross-region failover to a warm standby in us-west-2, or adjust the SLO to 99.9% to match demonstrated single-region resilience. Document the risk acceptance if adjusting the SLO."
      },
      "mappings": {
        "nist": [
          "CP-7",
          "CP-9"
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
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 3
    },
    {
      "id": "dist-d697bb34",
      "title": "Single-region active-passive topology limits availability under region failure",
      "goal": "distributed",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "risk",
      "summary": "The system is deployed exclusively in us-east-1 with no cross-region failover, creating a single point of failure at the AWS region level.",
      "detail": "As documented in tech_plan.md §7, cross-region failover is not yet implemented. This conflicts with the 99.95% SLO target and means any us-east-1 regional incident would cause an unrecoverable outage beyond SLO bounds. The CAP decision (ADR-001) favoring consistency further means the system stops rather than degrades gracefully during partition events.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§7 paragraph 1",
          "excerpt": "system is deployed in a single AWS region (us-east-1) with multi-AZ active-passive"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Implement cross-region failover or formally reduce SLO to match single-region risk.",
        "detail": "Pilot a warm standby in us-west-2 using MSK replication and RDS Multi-Region read replicas. Alternatively, formally accept the single-region risk via documented exception with reduced SLO commitment."
      },
      "mappings": {
        "nist": [
          "CP-7",
          "CP-7(1)"
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
    },
    {
      "id": "resil-0173b90b",
      "title": "Consumer-side backpressure policy not specified for claim-events topic",
      "goal": "resilient",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "low",
      "disposition": "blocked",
      "summary": "The threat model documents a producer rate limit but consumer-side backpressure and lag management are not specified, leaving unclear how the system handles consumer failures or slowdowns.",
      "detail": "Without consumer backpressure controls, a lagging consumer (e.g., fraud detection service) can accumulate unbounded lag. Combined with 7-day topic retention, a sustained consumer outage will cause data loss once retention expires. The threat model explicitly calls out 'consumer side has no backpressure' but the tech plan does not address remediation.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "Denial of service paragraph 2",
          "excerpt": "Per-producer rate limit of 1000 msg/sec; consumer side has no backpressure"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Define consumer backpressure policy, lag alerting thresholds, and dead-letter topic strategy.",
        "detail": "Configure consumer group lag alerting at 50% of retention window. Implement dead-letter topics for poison messages. Document the maximum acceptable consumer lag before manual intervention is required."
      },
      "mappings": {
        "nist": [
          "SI-13",
          "SC-5"
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
        "Consumer lag monitoring and alerting configuration",
        "Consumer group error handling and dead-letter topic policy"
      ]
    },
    {
      "id": "ephem-bff0e958",
      "title": "KMS key rotation disabled in Terraform configuration",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The customer-managed KMS key for the MSK cluster has enable_key_rotation set to false, meaning the key material never rotates automatically.",
      "detail": "A non-rotating KMS key accumulates cryptographic exposure over time. AWS best practice and NIST SP 800-57 recommend annual key rotation for symmetric keys protecting data at rest. The Terraform configuration explicitly sets this to false with a comment noting the intent. This compounds the risk identified in the Confidentiality agent regarding the KMS rotation gap.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "iac/kafka.tf",
          "locator": "resource aws_kms_key enable_key_rotation line",
          "excerpt": "enable_key_rotation = false # NOTE: rotation not enabled per current config"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Enable automatic KMS key rotation for the MSK cluster key.",
        "detail": "Set enable_key_rotation = true in the aws_kms_key resource. AWS KMS will rotate the backing key material annually. Existing ciphertexts remain decryptable; no re-encryption is needed."
      },
      "mappings": {
        "nist": [
          "SC-12",
          "SC-12(1)"
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
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 7
    },
    {
      "id": "ephem-eb51a236",
      "title": "Service-to-service shared bearer tokens are static credentials",
      "goal": "ephemeral",
      "tier": "scalability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Shared bearer tokens stored in HashiCorp Vault are long-lived static credentials with no documented rotation cadence.",
      "detail": "Static long-lived credentials violate the ephemeral credential principle. A leaked token grants persistent access until manually revoked. Vault's dynamic secrets engine can issue short-lived tokens that expire automatically; the current architecture does not leverage this capability for service-to-service auth.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§8 paragraph 4",
          "excerpt": "Service-to-service: shared bearer tokens stored in HashiCorp Vault"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Migrate service-to-service auth to Vault dynamic secrets or mTLS with short-lived certificates.",
        "detail": "Use Vault's AppRole or AWS IAM auth backend to issue short-lived tokens (TTL ≤ 1 hour). Alternatively, migrate to mTLS with certificates rotated via a service mesh CA."
      },
      "mappings": {
        "nist": [
          "IA-5(1)",
          "SC-12"
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
    },
    {
      "id": "auth-dbba3dea",
      "title": "SMS MFA fallback weakens authentication assurance for PHI-bearing surfaces",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "risk",
      "summary": "SMS-based MFA is accepted as a fallback factor for member portal access, which bears PHI, reducing authentication assurance to NIST AAL1 equivalent.",
      "detail": "NIST SP 800-63B designates SMS OTP as a restricted authenticator due to SIM-swap and SS7 interception vulnerabilities. Member portal access exposes PHI fields (member_id, drug_ndc, prescriber_npi). Accepting SMS as a fallback lowers effective AAL to AAL1 for any user who relies on it, below the AAL2 floor required for PHI-bearing applications under HIPAA.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§8 paragraph 1",
          "excerpt": "MFA factors accepted: TOTP, push, SMS (fallback)"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Remove SMS as an accepted MFA factor for PHI-bearing surfaces or enforce TOTP/push-only enrollment.",
        "detail": "Restrict Okta MFA policy for the member portal application to TOTP and push factors only. Provide a grace period for users currently enrolled with SMS to migrate. Document exceptions via risk acceptance if SMS must be retained."
      },
      "mappings": {
        "nist": [
          "IA-2(1)",
          "IA-2(2)",
          "IA-5(1)"
        ],
        "attack": [
          "T1621"
        ],
        "cwe": [],
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
      "headline_rank": 2
    },
    {
      "id": "auth-8d386c2f",
      "title": "Service-to-service authentication uses shared bearer tokens not mTLS",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Service-to-service calls use shared bearer tokens that do not provide cryptographic service identity verification, making service impersonation undetectable.",
      "detail": "Shared bearer tokens cannot prove which specific service instance made a request. Unlike mTLS, where each service presents a certificate with its identity, bearer tokens are opaque to intermediaries and cannot distinguish between authorized services and an attacker who obtained the token. This gap is particularly significant because the claim-events producer holds a bearer token that grants access to write PHI to the event bus.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§8 paragraph 4",
          "excerpt": "Service-to-service: shared bearer tokens stored in HashiCorp Vault"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Migrate service-to-service authentication to mTLS or SPIFFE/SPIRE for cryptographic service identity.",
        "detail": "Deploy Istio or SPIRE to issue per-service X.509 SVIDs. Retire shared bearer tokens once all services are enrolled. This also enables granular network policy enforcement at the service mesh layer."
      },
      "mappings": {
        "nist": [
          "IA-3",
          "IA-9",
          "SC-8(1)"
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
    },
    {
      "id": "nonrep-cf99a733",
      "title": "Audit log omits on-behalf-of user identity for producer actions",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "high",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The audit log captures the producer service identity but not the end-user identity on whose behalf the action was taken, preventing attribution of PHI access to individual users.",
      "detail": "The threat model explicitly notes that on-behalf-of user identity is NOT captured in audit entries. For HIPAA audit requirements, PHI access must be attributable to the individual user, not just the service. Without this attribution, a breach investigation cannot determine which user triggered a specific claim adjudication event, creating a regulatory gap.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "threat-model.md",
          "locator": "Repudiation paragraph 2",
          "excerpt": "Producer service identity captured in audit; on-behalf-of user identity is NOT captured"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Propagate authenticated user context through the producer call chain and include it in every audit log entry.",
        "detail": "Implement JWT or SAML assertion forwarding from the edge authentication layer to the adjudication service. Include the user sub claim in the Kafka message header and audit log entry. This satisfies HIPAA audit trail requirements for individual user attribution."
      },
      "mappings": {
        "nist": [
          "AU-9",
          "AU-12",
          "AU-12(1)"
        ],
        "attack": [
          "T1562"
        ],
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
    },
    {
      "id": "immut-067a7391",
      "title": "Backup immutability and object-lock policy not specified",
      "goal": "immutability",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "low",
      "disposition": "blocked",
      "summary": "The tech plan does not specify whether database backups use immutable storage or object-lock policies, leaving the backup chain's integrity unverifiable.",
      "detail": "Without knowing whether RDS snapshots or backup exports are stored with WORM protection, it is unclear if backup data can be altered or deleted by an attacker who gains S3 access. Immutable backups are a key control for ransomware resilience and forensic integrity.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§5.2 paragraph 1",
          "excerpt": "Adjudication outcomes are persisted to a PostgreSQL RDS cluster"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Document and enforce immutable backup storage with object-lock for RDS snapshots.",
        "detail": "Enable RDS automated backups with export to S3. Apply S3 Object Lock in Compliance mode with a retention period matching regulatory requirements (minimum 6 years for HIPAA). Document the policy in the DR runbook."
      },
      "mappings": {
        "nist": [
          "CP-9",
          "CP-9(8)"
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
        "Backup retention policy specifying storage location, immutability settings, and object-lock configuration"
      ]
    },
    {
      "id": "merged-4dd83f6a",
      "title": "Audit log is unsigned and stored in a mutable table with no WORM enforcement",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "critical",
      "confidence": "high",
      "disposition": "gap",
      "summary": "The audit_log table lacks both cryptographic signing and storage-layer immutability, meaning records can be altered or deleted by privileged users without detection.",
      "detail": "Non-Repudiation and Immutability agents both identified this risk from complementary angles. The Non-Repudiation lens focuses on the inability to prove audit entries were not tampered with after the fact. The Immutability lens focuses on the absence of storage-layer WORM protection that would physically prevent modification. Together, these gaps mean the audit log cannot serve as reliable evidence in a HIPAA breach investigation or regulatory audit.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "tech_plan.md",
          "locator": "§5.2 paragraph 2",
          "excerpt": "normal append-only table with application-level discipline — no WORM enforcement"
        },
        {
          "artifact": "threat-model.md",
          "locator": "Audit log Tampering paragraph",
          "excerpt": "No HMAC or signing on audit entries; mutable table"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Implement HMAC signing on all audit entries and migrate to WORM-protected storage.",
        "detail": "Sign each audit entry with a KMS-derived HMAC at write time. Migrate audit log storage to S3 with Object Lock in Compliance mode. Remove DBA-level DELETE permissions on the audit_log table as an interim control. Verify integrity on a scheduled basis via batch HMAC verification."
      },
      "mappings": {
        "nist": [
          "AU-9",
          "AU-9(2)",
          "AU-9(3)",
          "AU-10"
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
      "prerequisite_evidence": [],
      "headline": true,
      "headline_rank": 1
    },
    {
      "id": "apath-d066312b",
      "title": "Suppressed risk attack paths collapsed into one aggregate",
      "goal": "authenticity",
      "tier": "trustworthiness",
      "severity": "low",
      "confidence": "low",
      "disposition": "uncertainty",
      "summary": "75 additional risk-eligible attack path(s) of 75 enumerated were suppressed from the findings file (per-pair cap = 1 risk finding(s) per attacker x crown-jewel pair). Only the worst path per pair is surfaced as a discrete risk finding.",
      "detail": "To keep the advisory signal focused, the analyzer bounds risk findings to the worst 1 path(s) per (attacker_position, crown_jewel) pair. 75 lower-ranked risk-eligible path(s) (of 75 total enumerated paths) are collapsed into this single aggregate. Every enumerated path — suppressed or not — is retained verbatim in 40-synthesis/attack-paths.yaml, the artifact of record; consult it to inspect the full set.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "40-synthesis/attack-paths.yaml",
          "locator": "paths",
          "excerpt": "75 of 75 enumerated paths suppressed from findings (per-pair cap=1)"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Review 40-synthesis/attack-paths.yaml for the full path set; raise max_risk_findings_per_pair if more per-pair detail is wanted."
      },
      "mappings": {
        "nist": [
          "CA-3",
          "SA-8"
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
    },
    {
      "id": "tmeval-e5b594b0",
      "title": "Threat model omits Repudiation analysis for audit-log-writer",
      "goal": "non_repudiation",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "gap",
      "summary": "Non-repudiation specialist findings nonrep-cf99a733 and nonrep-62124087 flagged audit-log-writer for missing user attribution and unsigned mutable audit entries. The threat model STRIDE coverage for this surface covers S, T, I, D, E (5 threats) but has no Repudiation entry.",
      "detail": "The audit-log-writer surface has five STRIDE entries (tm-04b76ff1 through tm-8df8b2f3) covering Spoofing, Tampering, Information Disclosure, Denial of Service, and Elevation of Privilege. The Repudiation category is entirely absent. This is significant because specialist finding nonrep-62124087 identified that audit entries are unsigned and stored in a mutable table — an active non-repudiation risk. A complete STRIDE analysis must explicitly evaluate who can deny having performed an action and how the system refutes such denial.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-context/threat-model-normalized.yaml",
          "locator": "entries[asset=audit-log-writer]",
          "excerpt": "5 entries: tm-04b76ff1 (S), tm-9a8c9ce4 (T), tm-99aa91ca (I), tm-6dc432fd (D), tm-8df8b2f3 (E); no R entry"
        }
      ],
      "recommendation": {
        "posture": "recommended",
        "summary": "Extend threat model with Repudiation analysis for audit-log-writer",
        "detail": "Add a Repudiation entry covering: who can deny having written an audit entry, how the write-once property prevents post-hoc denial (th-8 mentions IAM deny-update but not log deletion by a privileged actor), and what cryptographic mechanism — such as HMAC signing — allows the system to refute a denial claim. Reference nonrep-62124087 for the remediation specifics already identified by the specialist."
      },
      "mappings": {
        "nist": [
          "AU-9",
          "AU-10"
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
    },
    {
      "id": "tmeval-6e33edd4",
      "title": "Threat model asserts TLS that conf-7aa376c5 contradicts",
      "goal": "confidentiality",
      "tier": "trustworthiness",
      "severity": "high",
      "confidence": "high",
      "disposition": "risk",
      "summary": "TM entry tm-1a799f16 for adjudication-to-pricing claims mitigation 'TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing'. Confidentiality specialist finding conf-7aa376c5 shows PHI flows in plaintext between producers and consumers at the Kafka broker layer — broker-level encryption only, no envelope encryption.",
      "detail": "The threat model marks th-6 (adjudication-to-pricing Information Disclosure) as 'Mitigated' based on the assertion that TLS 1.3 is enforced end-to-end on this Kafka topic. However, confidentiality finding conf-7aa376c5 contradicts this: the tech plan describes broker-managed AES-256 at-rest encryption, which grants all platform admins and consumers access to PHI in cleartext within the broker layer. TLS in transit does not prevent PHI exposure after decryption at the broker. The TM's mitigation claim is factually incorrect or describes a control that does not exist in the current implementation. This contradiction means the threat is categorised as 'Mitigated' in the TM when it should remain 'Open' pending implementation of field-level envelope encryption.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-context/threat-model-normalized.yaml",
          "locator": "entries[entry_id=tm-1a799f16]",
          "excerpt": "mitigation: TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing"
        }
      ],
      "recommendation": {
        "posture": "required",
        "summary": "Reconcile threat model and implementation reality for adjudication-to-pricing",
        "detail": "Either enforce field-level envelope encryption on the adjudication-to-pricing Kafka topic so the TM's intended mitigated state becomes accurate (see conf-7aa376c5 for the DEK-based remediation approach), or reopen th-6 in the threat model to reflect that the topic currently operates without adequate PHI protection, and raise its severity to Critical given the regulatory exposure of PHI in transit at AAL2 surfaces."
      },
      "mappings": {
        "nist": [
          "SC-8",
          "SC-8(1)"
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
    },
    {
      "id": "tmeval-cb19d940",
      "title": "Threat model is silent on vendor-API integration surface",
      "goal": "authenticity",
      "tier": "auditability",
      "severity": "medium",
      "confidence": "high",
      "disposition": "uncertainty",
      "summary": "Authenticity specialist finding auth-dbba3dea flagged the member portal authentication surface for weak SMS MFA. The threat model has zero entries for any vendor-API or member-portal integration surface — neither analyzed in scope nor explicitly declared out of scope.",
      "detail": "The threat model covers three surfaces: claim-ingress-API, adjudication-to-pricing, and audit-log-writer. The member portal and vendor-API integration — where auth-dbba3dea identified SMS OTP fallback lowering authentication assurance to AAL1 for PHI-bearing interactions — are entirely absent from the model. Complete silence is ambiguous: the surface may have been intentionally excluded from this threat model's scope, or it may have been overlooked. Without an explicit out-of-scope annotation or a reference to a separate threat model artifact, reviewers cannot determine whether this gap represents a deliberate scoping decision or an unanalyzed attack surface.",
      "rubric_clause": null,
      "evidence": [
        {
          "artifact": "00-context/threat-model-normalized.yaml",
          "locator": "(no entries for surface=vendor-API or member-portal)",
          "excerpt": "surfaces modelled: claim-ingress-API, adjudication-to-pricing, audit-log-writer; vendor-API absent"
        }
      ],
      "recommendation": {
        "posture": "consider",
        "summary": "Clarify whether vendor-API and member-portal surfaces are intentionally out of scope",
        "detail": "Either add threat-model entries for the member portal authentication surface covering at minimum Spoofing (weak MFA) and Information Disclosure (PHI exposure post-auth), or annotate the threat model with a deliberate out-of-scope note naming the artifact — such as the vendor security review or a separate portal threat model — that covers authentication threats for this surface. This ensures reviewers can distinguish intentional scoping from oversight."
      },
      "mappings": {
        "nist": [
          "IA-3",
          "IA-5(1)"
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
  "contradictions": [
    {
      "id": "contra-a1b2c3d4",
      "finding": {
        "id": "conf-7aa376c5",
        "assertion": "PHI fields in the Kafka claim-events topic are protected only at the broker level; payload-level PHI is in plaintext."
      },
      "capability": {
        "ids": [
          "conf-cap-89e19793"
        ],
        "id": "conf-cap-89e19793",
        "assertion": "Field-level envelope encryption is applied to PHI columns in member_demographics and claims tables at rest."
      },
      "comparison": "Finding cites tech_plan.md §4.2 (Kafka broker encryption). Capability cites tech_plan.md §5.1 (RDS field-level encryption). The capability covers RDS storage; the finding covers Kafka topics. Different storage layers, different encryption postures.",
      "resolution": "Reviewer confirm whether the field-level encryption capability's scope explicitly excludes Kafka payloads and update the capability scope statement accordingly. The finding and capability are not contradictory if scopes are clearly delimited."
    }
  ],
  "contradictions_notes": null,
  "severity_disagreements": [
    {
      "id": "merged-4dd83f6a",
      "agents": [
        {
          "lens": "non_repudiation",
          "severity": "high"
        },
        {
          "lens": "immutability",
          "severity": "high"
        }
      ],
      "chosen": "critical",
      "rationale": "Synthesizer elevates to critical because the combination of unsigned entries and mutable storage means the audit log cannot serve as evidence in HIPAA breach investigations, triggering regulatory breach-notification exposure beyond what either agent assessed in isolation."
    }
  ],
  "severity_disagreements_notes": null,
  "nist_rollup": [
    {
      "family": "IA",
      "title": "Identification & Authentication",
      "covered": 3,
      "gapped": 4,
      "both": 1,
      "notable": "IA-2, IA-5, IA-8 strong; IA-3, IA-5(1), IA-2(2) gapped"
    },
    {
      "family": "SC",
      "title": "System & Communications Protection",
      "covered": 1,
      "gapped": 1,
      "both": 6,
      "notable": "SC-28 strong; SC-5 gapped"
    },
    {
      "family": "AU",
      "title": "Audit & Accountability",
      "covered": 1,
      "gapped": 5,
      "both": 1,
      "notable": "AU-2 strong; AU-9, AU-12(1), AU-9(2) gapped"
    },
    {
      "family": "CP",
      "title": "Contingency Planning",
      "covered": 1,
      "gapped": 4,
      "both": 2,
      "notable": "CP-2 strong; CP-4, CP-4(1), CP-7(1) gapped"
    },
    {
      "family": "SI",
      "title": "System & Information Integrity",
      "covered": 1,
      "gapped": 2,
      "both": 1,
      "notable": "SI-12 strong; SI-7, SI-7(1) gapped"
    },
    {
      "family": "CA",
      "title": "Assessment, Authorization, and Monitoring",
      "covered": 0,
      "gapped": 1,
      "both": 0,
      "notable": "CA-3 gapped"
    },
    {
      "family": "SA",
      "title": "System & Services Acquisition",
      "covered": 0,
      "gapped": 1,
      "both": 0,
      "notable": "SA-8 gapped"
    }
  ],
  "attack_exposure": [
    {
      "id": "T1530",
      "name": "Data from Cloud Storage",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1562",
      "name": "Impair Defenses",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1565",
      "name": "Data Manipulation",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    },
    {
      "id": "T1621",
      "name": "Multi-Factor Authentication Request Generation",
      "findings": 1,
      "mitigations": [],
      "coverage": "uncovered",
      "note": ""
    }
  ],
  "masvs_coverage": [],
  "maswe_coverage": [],
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
        "component": "00-context/threat-model-normalized.yaml",
        "cells": {
          "conf": "gapped",
          "intg": "silent",
          "avail": "silent",
          "dist": "silent",
          "resil": "silent",
          "ephem": "silent",
          "auth": "gapped",
          "nonrep": "gapped",
          "immut": "silent"
        }
      },
      {
        "component": "40-synthesis/attack-paths.yaml",
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
        "component": "adjudication-service",
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
        "component": "audit-log-store",
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
        "component": "audit-log-writer",
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
        "component": "claim-ingress-api",
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
        "component": "iac/kafka.tf",
        "cells": {
          "conf": "covered",
          "intg": "covered",
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
        "component": "member-record-store",
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
        "component": "pde-submission-service",
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
        "component": "pharmacy-edge-gateway",
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
        "component": "pricing-service",
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
        "component": "tech_plan.md",
        "cells": {
          "conf": "both",
          "intg": "silent",
          "avail": "both",
          "dist": "both",
          "resil": "covered",
          "ephem": "both",
          "auth": "both",
          "nonrep": "both",
          "immut": "both"
        }
      },
      {
        "component": "threat-model.md",
        "cells": {
          "conf": "silent",
          "intg": "gapped",
          "avail": "silent",
          "dist": "silent",
          "resil": "gapped",
          "ephem": "silent",
          "auth": "silent",
          "nonrep": "gapped",
          "immut": "silent"
        }
      }
    ]
  },
  "attack_paths": {
    "graph": {
      "nodes": [
        {
          "id": "asset-1a2b3c4d",
          "type": "asset",
          "label": "claim-ingress-api",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§4 Event Bus Architecture"
          },
          "confidence": "high"
        },
        {
          "id": "asset-2b3c4d5e",
          "type": "asset",
          "label": "pharmacy-edge-gateway",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§8 Authentication (Member portal: OAuth + MFA via Okta)"
          },
          "confidence": "medium"
        },
        {
          "id": "asset-3c4d5e6f",
          "type": "asset",
          "label": "adjudication-service",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§5.1 Database (Adjudication outcomes persisted to RDS)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-4d5e6f7a",
          "type": "asset",
          "label": "pricing-service",
          "provenance": {
            "artifact": "00-context/threat-model-normalized.yaml",
            "locator": "tm-1a799f16 (adjudication-to-pricing)"
          },
          "confidence": "medium"
        },
        {
          "id": "asset-5e6f7a8b",
          "type": "asset",
          "label": "audit-log-writer",
          "provenance": {
            "artifact": "00-context/threat-model-normalized.yaml",
            "locator": "tm-04b76ff1 (audit-log-writer)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-6f7a8b9c",
          "type": "asset",
          "label": "audit-log-store",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§5.2 Audit log (audit_log table in RDS)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-7a8b9c0d",
          "type": "asset",
          "label": "member-record-store",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§5.1 Database (member_demographics and claims tables, PostgreSQL RDS)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-8b9c0d1e",
          "type": "asset",
          "label": "pde-submission-service",
          "provenance": {
            "artifact": "domains/pbm/domain.yaml",
            "locator": "crown_jewels[].pattern=pde_submission_pipeline"
          },
          "confidence": "low"
        },
        {
          "id": "atk-2d392558",
          "type": "attacker_position",
          "label": "compromised_vendor_integration",
          "provenance": {
            "artifact": ".apd-run.yaml",
            "locator": null
          },
          "confidence": "high"
        },
        {
          "id": "atk-accb3a4c",
          "type": "attacker_position",
          "label": "compromised_pharmacy_credential",
          "provenance": {
            "artifact": ".apd-run.yaml",
            "locator": null
          },
          "confidence": "high"
        },
        {
          "id": "atk-e0a03f74",
          "type": "attacker_position",
          "label": "external_internet",
          "provenance": {
            "artifact": ".apd-run.yaml",
            "locator": null
          },
          "confidence": "high"
        },
        {
          "id": "idn-aabbccdd",
          "type": "identity",
          "label": "pharmacy-submitter-role",
          "provenance": {
            "artifact": "00-context/threat-model-normalized.yaml",
            "locator": "tm-43625e57 (pharmacy credential)"
          },
          "confidence": "high"
        },
        {
          "id": "idn-bbccddee",
          "type": "identity",
          "label": "adjudication-service-account",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§8 Authentication (Service-to-service shared bearer tokens)"
          },
          "confidence": "medium"
        },
        {
          "id": "idn-ccddeeff",
          "type": "identity",
          "label": "member-services-agent-role",
          "provenance": {
            "artifact": "domains/pbm/domain.yaml",
            "locator": "attacker_positions[].position=insider_with_member_service_role"
          },
          "confidence": "low"
        },
        {
          "id": "jewel-358e9430",
          "type": "crown_jewel",
          "label": "phi_store",
          "confidence": "high"
        },
        {
          "id": "jewel-e9cb35a7",
          "type": "crown_jewel",
          "label": "pde_submission_pipeline",
          "confidence": "high"
        }
      ],
      "edges": [
        {
          "id": "edge-07946d39",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-0ec04856",
          "type": "trusts",
          "source": "asset-3c4d5e6f",
          "target": "asset-8b9c0d1e",
          "bottleneck": true
        },
        {
          "id": "edge-1457b95a",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-17783b27",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-1c7d8d1d",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-20d89553",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-27e4ec84",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-2a479259",
          "type": "trusts",
          "source": "asset-6f7a8b9c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-33cbe3d9",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-37b95b02",
          "type": "trusts",
          "source": "asset-5e6f7a8b",
          "target": "asset-6f7a8b9c",
          "bottleneck": true
        },
        {
          "id": "edge-47ab0bcb",
          "type": "compromisable_via_finding",
          "source": "asset-5e6f7a8b",
          "target": "asset-1a2b3c4d",
          "bottleneck": true
        },
        {
          "id": "edge-4b6f06ec",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-4f04c048",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-5074ec19",
          "type": "trusts",
          "source": "asset-3c4d5e6f",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-5b51f5a8",
          "type": "trusts",
          "source": "asset-3c4d5e6f",
          "target": "asset-7a8b9c0d",
          "bottleneck": true
        },
        {
          "id": "edge-631176ba",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-67448007",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-67b87381",
          "type": "trusts",
          "source": "asset-8b9c0d1e",
          "target": "asset-3c4d5e6f",
          "bottleneck": true
        },
        {
          "id": "edge-6dbad8bd",
          "type": "trusts",
          "source": "asset-7a8b9c0d",
          "target": "asset-3c4d5e6f",
          "bottleneck": false
        },
        {
          "id": "edge-6e130fc8",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-78b786a1",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-867e7d3e",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-88ca3e5d",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-8af9f7aa",
          "type": "trusts",
          "source": "asset-1a2b3c4d",
          "target": "asset-2b3c4d5e",
          "bottleneck": true
        },
        {
          "id": "edge-94c86287",
          "type": "trusts",
          "source": "asset-2b3c4d5e",
          "target": "asset-1a2b3c4d",
          "bottleneck": true
        },
        {
          "id": "edge-989fc99a",
          "type": "data_resides_on",
          "source": "asset-6f7a8b9c",
          "target": "jewel-358e9430",
          "bottleneck": true
        },
        {
          "id": "edge-99707e24",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-9a22b4a2",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-9bf0cb8d",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-af0b27e9",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-bd61022c",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-c41dcef1",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-cb1c4890",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-cd042314",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-d6d18ce6",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-dceeaa66",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-dd4a931c",
          "type": "trusts",
          "source": "asset-1a2b3c4d",
          "target": "asset-3c4d5e6f",
          "bottleneck": true
        },
        {
          "id": "edge-decfffea",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-e6170ee9",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-f29aefbf",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-f2a4568b",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-f3c575df",
          "type": "data_resides_on",
          "source": "asset-7a8b9c0d",
          "target": "jewel-358e9430",
          "bottleneck": true
        },
        {
          "id": "edge-f4e846c9",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        }
      ]
    },
    "graph_path_focused": {
      "nodes": [
        {
          "id": "asset-1a2b3c4d",
          "type": "asset",
          "label": "claim-ingress-api",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§4 Event Bus Architecture"
          },
          "confidence": "high"
        },
        {
          "id": "asset-2b3c4d5e",
          "type": "asset",
          "label": "pharmacy-edge-gateway",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§8 Authentication (Member portal: OAuth + MFA via Okta)"
          },
          "confidence": "medium"
        },
        {
          "id": "asset-3c4d5e6f",
          "type": "asset",
          "label": "adjudication-service",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§5.1 Database (Adjudication outcomes persisted to RDS)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-5e6f7a8b",
          "type": "asset",
          "label": "audit-log-writer",
          "provenance": {
            "artifact": "00-context/threat-model-normalized.yaml",
            "locator": "tm-04b76ff1 (audit-log-writer)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-6f7a8b9c",
          "type": "asset",
          "label": "audit-log-store",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§5.2 Audit log (audit_log table in RDS)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-7a8b9c0d",
          "type": "asset",
          "label": "member-record-store",
          "provenance": {
            "artifact": "inputs/tech_plan.md",
            "locator": "§5.1 Database (member_demographics and claims tables, PostgreSQL RDS)"
          },
          "confidence": "high"
        },
        {
          "id": "asset-8b9c0d1e",
          "type": "asset",
          "label": "pde-submission-service",
          "provenance": {
            "artifact": "domains/pbm/domain.yaml",
            "locator": "crown_jewels[].pattern=pde_submission_pipeline"
          },
          "confidence": "low"
        },
        {
          "id": "atk-2d392558",
          "type": "attacker_position",
          "label": "compromised_vendor_integration",
          "provenance": {
            "artifact": ".apd-run.yaml",
            "locator": null
          },
          "confidence": "high"
        },
        {
          "id": "atk-accb3a4c",
          "type": "attacker_position",
          "label": "compromised_pharmacy_credential",
          "provenance": {
            "artifact": ".apd-run.yaml",
            "locator": null
          },
          "confidence": "high"
        },
        {
          "id": "atk-e0a03f74",
          "type": "attacker_position",
          "label": "external_internet",
          "provenance": {
            "artifact": ".apd-run.yaml",
            "locator": null
          },
          "confidence": "high"
        },
        {
          "id": "jewel-358e9430",
          "type": "crown_jewel",
          "label": "phi_store",
          "confidence": "high"
        }
      ],
      "edges": [
        {
          "id": "edge-07946d39",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-0ec04856",
          "type": "trusts",
          "source": "asset-3c4d5e6f",
          "target": "asset-8b9c0d1e",
          "bottleneck": false
        },
        {
          "id": "edge-1457b95a",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-17783b27",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-1c7d8d1d",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-20d89553",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-27e4ec84",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-33cbe3d9",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-37b95b02",
          "type": "trusts",
          "source": "asset-5e6f7a8b",
          "target": "asset-6f7a8b9c",
          "bottleneck": false
        },
        {
          "id": "edge-47ab0bcb",
          "type": "compromisable_via_finding",
          "source": "asset-5e6f7a8b",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-4b6f06ec",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-4f04c048",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-5b51f5a8",
          "type": "trusts",
          "source": "asset-3c4d5e6f",
          "target": "asset-7a8b9c0d",
          "bottleneck": false
        },
        {
          "id": "edge-631176ba",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-67448007",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-67b87381",
          "type": "trusts",
          "source": "asset-8b9c0d1e",
          "target": "asset-3c4d5e6f",
          "bottleneck": false
        },
        {
          "id": "edge-6e130fc8",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-78b786a1",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-867e7d3e",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-88ca3e5d",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-8af9f7aa",
          "type": "trusts",
          "source": "asset-1a2b3c4d",
          "target": "asset-2b3c4d5e",
          "bottleneck": false
        },
        {
          "id": "edge-94c86287",
          "type": "trusts",
          "source": "asset-2b3c4d5e",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-989fc99a",
          "type": "data_resides_on",
          "source": "asset-6f7a8b9c",
          "target": "jewel-358e9430",
          "bottleneck": false
        },
        {
          "id": "edge-99707e24",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-9a22b4a2",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-9bf0cb8d",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-af0b27e9",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-bd61022c",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-c41dcef1",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-cb1c4890",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-cd042314",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-d6d18ce6",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-dceeaa66",
          "type": "network_reachable",
          "source": "atk-accb3a4c",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-dd4a931c",
          "type": "trusts",
          "source": "asset-1a2b3c4d",
          "target": "asset-3c4d5e6f",
          "bottleneck": false
        },
        {
          "id": "edge-decfffea",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-e6170ee9",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-1a2b3c4d",
          "bottleneck": false
        },
        {
          "id": "edge-f29aefbf",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-f2a4568b",
          "type": "network_reachable",
          "source": "atk-e0a03f74",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        },
        {
          "id": "edge-f3c575df",
          "type": "data_resides_on",
          "source": "asset-7a8b9c0d",
          "target": "jewel-358e9430",
          "bottleneck": false
        },
        {
          "id": "edge-f4e846c9",
          "type": "network_reachable",
          "source": "atk-2d392558",
          "target": "asset-5e6f7a8b",
          "bottleneck": false
        }
      ]
    },
    "pairs": [
      {
        "attacker_position": "atk-2d392558",
        "attacker_position_name": "compromised_vendor_integration",
        "crown_jewel": "jewel-358e9430",
        "crown_jewel_name": "phi_store",
        "paths": [
          {
            "path_id": "path-1ada4385",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-867e7d3e",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-867e7d3e",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-28639f10",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-78b786a1",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-78b786a1",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-2c821529",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-1457b95a",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-1457b95a",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-4bf9db48",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-99707e24",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-99707e24",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-e585d2cd",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-f4e846c9",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-f4e846c9",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-0f2e2ec6",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-99707e24",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-99707e24",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-124a8df8",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-1457b95a",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-1457b95a",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-17c53ecb",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-867e7d3e",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-867e7d3e",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a5b32741",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-f4e846c9",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-f4e846c9",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-ed2bc188",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-78b786a1",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-78b786a1",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-2c4e2248",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-9bf0cb8d",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-9bf0cb8d",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-49b5b04b",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-6e130fc8",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-6e130fc8",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-64622465",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-d6d18ce6",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-d6d18ce6",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-66bf81b1",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-cd042314",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-cd042314",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-eb2df0b5",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-e6170ee9",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-e6170ee9",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-02621d38",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-cd042314",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-cd042314",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-349ed5b3",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-d6d18ce6",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-d6d18ce6",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-3db0a547",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-d6d18ce6",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-d6d18ce6",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-4d3f1119",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-9bf0cb8d",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-9bf0cb8d",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-88e551bf",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-e6170ee9",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-e6170ee9",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-bc155c6f",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-cd042314",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-cd042314",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-bff16166",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-e6170ee9",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-e6170ee9",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-c53dc1a5",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-6e130fc8",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-6e130fc8",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-ddaa8bca",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-9bf0cb8d",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-9bf0cb8d",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-e522f8ab",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-6e130fc8",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-6e130fc8",
                "from_id": "atk-2d392558",
                "from_name": "compromised_vendor_integration",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          }
        ]
      },
      {
        "attacker_position": "atk-accb3a4c",
        "attacker_position_name": "compromised_pharmacy_credential",
        "crown_jewel": "jewel-358e9430",
        "crown_jewel_name": "phi_store",
        "paths": [
          {
            "path_id": "path-4d156d6c",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-1c7d8d1d",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-1c7d8d1d",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-71952af7",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-c41dcef1",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-c41dcef1",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a078d3bb",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-9a22b4a2",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-9a22b4a2",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a6e1bb6e",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-dceeaa66",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-dceeaa66",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-bce8d25b",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-33cbe3d9",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-33cbe3d9",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-029bb1f8",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-c41dcef1",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-c41dcef1",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-3700ac90",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-dceeaa66",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-dceeaa66",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-9e540001",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-1c7d8d1d",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-1c7d8d1d",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-c7af1885",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-33cbe3d9",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-33cbe3d9",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-d182c6dc",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-9a22b4a2",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-9a22b4a2",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-1f9d8e59",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-4b6f06ec",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-4b6f06ec",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-2efebc82",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-af0b27e9",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-af0b27e9",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-33307cbf",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-88ca3e5d",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-88ca3e5d",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-4a223504",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-67448007",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-67448007",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-e80b432f",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-20d89553",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-20d89553",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-0e2cc09b",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-88ca3e5d",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-88ca3e5d",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-1f1be954",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-4b6f06ec",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-4b6f06ec",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-266f3ab1",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-4b6f06ec",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-4b6f06ec",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-625e48c6",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-af0b27e9",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-af0b27e9",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-6862c9e4",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-67448007",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-67448007",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-6c664a81",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-67448007",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-67448007",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-847fcd0f",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-af0b27e9",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-af0b27e9",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a46546ce",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-20d89553",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-20d89553",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-bd5dc0c0",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-20d89553",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-20d89553",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-cef99a0e",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-88ca3e5d",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-88ca3e5d",
                "from_id": "atk-accb3a4c",
                "from_name": "compromised_pharmacy_credential",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          }
        ]
      },
      {
        "attacker_position": "atk-e0a03f74",
        "attacker_position_name": "external_internet",
        "crown_jewel": "jewel-358e9430",
        "crown_jewel_name": "phi_store",
        "paths": [
          {
            "path_id": "path-30aa43dd",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-f29aefbf",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-f29aefbf",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-75e4e247",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-631176ba",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-631176ba",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-75f72b59",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-4f04c048",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-4f04c048",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-89179e11",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-f2a4568b",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-f2a4568b",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-96c29211",
            "hop_count": 5,
            "feasibility": "high",
            "severity_sum": 2,
            "mitigation_count": 0,
            "edges": [
              "edge-cb1c4890",
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-47ab0bcb",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-cb1c4890",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-47ab0bcb",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "compromisable_via_finding",
                "finding_id": "tmeval-cb19d940",
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-1cba6d30",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-4f04c048",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-4f04c048",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-4b7506ed",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-f29aefbf",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-f29aefbf",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-575eea43",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-cb1c4890",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-cb1c4890",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a7acb679",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-f2a4568b",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-f2a4568b",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-d0e7a036",
            "hop_count": 3,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-631176ba",
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "bottleneck_edges": [
              "edge-37b95b02",
              "edge-989fc99a"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-631176ba",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-5e6f7a8b",
                "to_name": "audit-log-writer",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-37b95b02",
                "from_id": "asset-5e6f7a8b",
                "from_name": "audit-log-writer",
                "to_id": "asset-6f7a8b9c",
                "to_name": "audit-log-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-989fc99a",
                "from_id": "asset-6f7a8b9c",
                "from_name": "audit-log-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-5da3ef2d",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-bd61022c",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-bd61022c",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-64d45d5c",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-27e4ec84",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-27e4ec84",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-77fb16e8",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-17783b27",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-17783b27",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-b98dfc6a",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-decfffea",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-decfffea",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-e1ffabb7",
            "hop_count": 4,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-07946d39",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-07946d39",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-06e1b64c",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-17783b27",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-17783b27",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-0afaab97",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-decfffea",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-decfffea",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-1205d587",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-bd61022c",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-bd61022c",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-15202959",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-27e4ec84",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-27e4ec84",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-35771f32",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-decfffea",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-decfffea",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-9985cc0e",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-07946d39",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-07946d39",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a58f9934",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-17783b27",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-17783b27",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-a7584bdb",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-27e4ec84",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-27e4ec84",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-c26b08c6",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-07946d39",
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-dd4a931c",
              "edge-0ec04856",
              "edge-67b87381",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-07946d39",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-0ec04856",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-8b9c0d1e",
                "to_name": "pde-submission-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-67b87381",
                "from_id": "asset-8b9c0d1e",
                "from_name": "pde-submission-service",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          },
          {
            "path_id": "path-e5de83f1",
            "hop_count": 6,
            "feasibility": "high",
            "severity_sum": 0,
            "mitigation_count": 0,
            "edges": [
              "edge-bd61022c",
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "bottleneck_edges": [
              "edge-8af9f7aa",
              "edge-94c86287",
              "edge-dd4a931c",
              "edge-5b51f5a8",
              "edge-f3c575df"
            ],
            "edges_detailed": [
              {
                "edge_id": "edge-bd61022c",
                "from_id": "atk-e0a03f74",
                "from_name": "external_internet",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "network_reachable",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": false
              },
              {
                "edge_id": "edge-8af9f7aa",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-2b3c4d5e",
                "to_name": "pharmacy-edge-gateway",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-94c86287",
                "from_id": "asset-2b3c4d5e",
                "from_name": "pharmacy-edge-gateway",
                "to_id": "asset-1a2b3c4d",
                "to_name": "claim-ingress-api",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-dd4a931c",
                "from_id": "asset-1a2b3c4d",
                "from_name": "claim-ingress-api",
                "to_id": "asset-3c4d5e6f",
                "to_name": "adjudication-service",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-5b51f5a8",
                "from_id": "asset-3c4d5e6f",
                "from_name": "adjudication-service",
                "to_id": "asset-7a8b9c0d",
                "to_name": "member-record-store",
                "edge_type": "trust_boundary",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              },
              {
                "edge_id": "edge-f3c575df",
                "from_id": "asset-7a8b9c0d",
                "from_name": "member-record-store",
                "to_id": "jewel-358e9430",
                "to_name": "phi_store",
                "edge_type": "data_resides_on",
                "finding_id": null,
                "capability_id": null,
                "confidence": "high",
                "is_bottleneck": true
              }
            ]
          }
        ]
      }
    ],
    "bottleneck_overlays": [],
    "bottleneck_threshold": 4,
    "max_edge_traversal_count": 60,
    "summary": {
      "total_paths": 75,
      "total_pairs": 3,
      "bottleneck_count": 0
    },
    "asset_graph_summary": {
      "node_count": 16,
      "edge_count": 43,
      "attacker_position_count": 3,
      "crown_jewel_count": 2,
      "asset_count": 8,
      "identity_count": 3,
      "trust_boundary_edge_count": 10,
      "finding_derived_edge_count": 1,
      "capability_derived_edge_count": 0
    }
  },
  "c4_model": {
    "present": false,
    "nodes": [],
    "edges": [],
    "unlocalized_findings": 0,
    "not_analyzed_count": 0,
    "levels_present": []
  },
  "next_steps": [
    {
      "rank": 1,
      "text": "Sign every audit record (HMAC or asymmetric) and move the audit store to a WORM substrate (object-lock) so consequential claim actions are tamper-evident and reconstructable.",
      "refs": [
        "merged-4dd83f6a"
      ]
    },
    {
      "rank": 2,
      "text": "Replace SMS MFA fallback with TOTP/WebAuthn to raise authentication assurance on claim-submitter and operator surfaces.",
      "refs": [
        "auth-dbba3dea"
      ]
    },
    {
      "rank": 3,
      "text": "Add envelope encryption for PHI fields in the Kafka claim-events topic and pin a KMS DEK rotation cadence.",
      "refs": [
        "conf-7aa376c5",
        "conf-98a543cd"
      ]
    },
    {
      "rank": 4,
      "text": "Establish a tested DR failover procedure (document RTO/RPO, run a game-day) and evaluate multi-region active-active to meet the 99.95% SLO.",
      "refs": [
        "avail-ce35b2ed",
        "avail-4e08f6d8"
      ]
    },
    {
      "rank": 5,
      "text": "Enable automatic KMS key rotation for the MSK cluster key (enable_key_rotation = true) to stop accumulating static-key exposure on the broker at-rest encryption.",
      "refs": [
        "ephem-bff0e958"
      ]
    }
  ],
  "taxonomy": {
    "AU-10": {
      "family": "NIST 800-53r5",
      "title": "Non-repudiation"
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
    "CA-3": {
      "family": "NIST 800-53r5",
      "title": "Information Exchange"
    },
    "CP-2": {
      "family": "NIST 800-53r5",
      "title": "Contingency Plan"
    },
    "CP-4": {
      "family": "NIST 800-53r5",
      "title": "Contingency Plan Testing"
    },
    "CP-4(1)": {
      "family": "NIST 800-53r5",
      "title": "Contingency Plan Testing | Coordinate with Related Plans"
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
    "IA-3": {
      "family": "NIST 800-53r5",
      "title": "Device Identification and Authentication"
    },
    "IA-5": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management"
    },
    "IA-5(1)": {
      "family": "NIST 800-53r5",
      "title": "Authenticator Management | Password-based Authentication"
    },
    "IA-8": {
      "family": "NIST 800-53r5",
      "title": "Identification and Authentication (Non-organizational Users)"
    },
    "IA-9": {
      "family": "NIST 800-53r5",
      "title": "Service Identification and Authentication"
    },
    "SA-8": {
      "family": "NIST 800-53r5",
      "title": "Security and Privacy Engineering Principles"
    },
    "SC-12": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management"
    },
    "SC-12(1)": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Key Establishment and Management | Availability"
    },
    "SC-13": {
      "family": "NIST 800-53r5",
      "title": "Cryptographic Protection"
    },
    "SC-28": {
      "family": "NIST 800-53r5",
      "title": "Protection of Information at Rest"
    },
    "SC-28(1)": {
      "family": "NIST 800-53r5",
      "title": "Protection of Information at Rest | Cryptographic Protection"
    },
    "SC-5": {
      "family": "NIST 800-53r5",
      "title": "Denial-of-service Protection"
    },
    "SC-8": {
      "family": "NIST 800-53r5",
      "title": "Transmission Confidentiality and Integrity"
    },
    "SC-8(1)": {
      "family": "NIST 800-53r5",
      "title": "Transmission Confidentiality and Integrity | Cryptographic Protection"
    },
    "SI-12": {
      "family": "NIST 800-53r5",
      "title": "Information Management and Retention"
    },
    "SI-13": {
      "family": "NIST 800-53r5",
      "title": "Predictable Failure Prevention"
    },
    "SI-7": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity"
    },
    "SI-7(1)": {
      "family": "NIST 800-53r5",
      "title": "Software, Firmware, and Information Integrity | Integrity Checks"
    },
    "T1530": {
      "family": "MITRE ATT&CK",
      "title": "Data from Cloud Storage",
      "url": "https://attack.mitre.org/techniques/T1530/"
    },
    "T1562": {
      "family": "MITRE ATT&CK",
      "title": "Impair Defenses",
      "url": "https://attack.mitre.org/techniques/T1562/"
    },
    "T1565": {
      "family": "MITRE ATT&CK",
      "title": "Data Manipulation",
      "url": "https://attack.mitre.org/techniques/T1565/"
    },
    "T1621": {
      "family": "MITRE ATT&CK",
      "title": "Multi-Factor Authentication Request Generation",
      "url": "https://attack.mitre.org/techniques/T1621/"
    }
  },
  "threat_model": {
    "present": true,
    "authored": false,
    "supplied_present": false,
    "comparator": false,
    "generated_by": "threat_model_recon",
    "methodology": "stride",
    "source_artifact": "examples/apd-20260601-claim-event-bus/inputs/threat-model.json",
    "entry_count": 11,
    "grounded_count": 11,
    "gap_count": 0,
    "entries": [
      {
        "asset": "claim-ingress-API",
        "threat": "Pharmacy credential theft via phishing",
        "stride_letter": "S",
        "linddun_letter": null,
        "mitigation": "MFA required on pharmacy portal; rotating short-lived tokens",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[0].threats[0]",
        "apd_goals": [
          "authenticity"
        ]
      },
      {
        "asset": "claim-ingress-API",
        "threat": "Replay of submitted claim with altered NDC",
        "stride_letter": "T",
        "linddun_letter": null,
        "mitigation": "Payload signing with HMAC over canonical JSON",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[0].threats[1]",
        "apd_goals": [
          "integrity"
        ]
      },
      {
        "asset": "claim-ingress-API",
        "threat": "Token in CloudFront access logs",
        "stride_letter": "I",
        "linddun_letter": null,
        "mitigation": "CloudFront logging filters strip Authorization header",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[0].threats[2]",
        "apd_goals": [
          "confidentiality"
        ]
      },
      {
        "asset": "claim-ingress-API",
        "threat": "High-volume duplicate submission DoS",
        "stride_letter": "D",
        "linddun_letter": null,
        "mitigation": "Rate limiting at API gateway",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[0].threats[3]",
        "apd_goals": [
          "availability"
        ]
      },
      {
        "asset": "claim-ingress-API",
        "threat": "Pharmacy account elevated via missing tenant check",
        "stride_letter": "E",
        "linddun_letter": null,
        "mitigation": "Tenant ID validated on every claim against pharmacy-to-tenant mapping",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[0].threats[4]",
        "apd_goals": [
          "authenticity",
          "integrity"
        ]
      },
      {
        "asset": "adjudication-to-pricing",
        "threat": "PHI in transit between adjudication and pricing services",
        "stride_letter": "I",
        "linddun_letter": null,
        "mitigation": "TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[1].threats[0]",
        "apd_goals": [
          "confidentiality"
        ]
      },
      {
        "asset": "audit-log-writer",
        "threat": "Service account compromise allows audit write impersonation",
        "stride_letter": "S",
        "linddun_letter": null,
        "mitigation": "Service account isolation per writer process",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[2].threats[0]",
        "apd_goals": [
          "authenticity"
        ]
      },
      {
        "asset": "audit-log-writer",
        "threat": "Audit entry modification after write",
        "stride_letter": "T",
        "linddun_letter": null,
        "mitigation": "Write-once storage on DynamoDB with deny-update IAM policy",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[2].threats[1]",
        "apd_goals": [
          "integrity"
        ]
      },
      {
        "asset": "audit-log-writer",
        "threat": "Audit entries leak PHI in error fields",
        "stride_letter": "I",
        "linddun_letter": null,
        "mitigation": "Error redaction in audit serializer",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[2].threats[2]",
        "apd_goals": [
          "confidentiality"
        ]
      },
      {
        "asset": "audit-log-writer",
        "threat": "Audit writer DOS via flood",
        "stride_letter": "D",
        "linddun_letter": null,
        "mitigation": "Per-source rate limit",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[2].threats[3]",
        "apd_goals": [
          "availability"
        ]
      },
      {
        "asset": "audit-log-writer",
        "threat": "Direct DynamoDB write bypasses audit serializer",
        "stride_letter": "E",
        "linddun_letter": null,
        "mitigation": "IAM policy restricts table writes to audit-writer role",
        "confidence": "high",
        "source_locator": "diagrams[0].cells[2].threats[4]",
        "apd_goals": [
          "authenticity",
          "integrity"
        ]
      }
    ],
    "stride_matrix": {
      "letters_present": [
        "S",
        "T",
        "I",
        "D",
        "E"
      ],
      "rows": [
        {
          "asset": "audit-log-writer",
          "cells": {
            "S": "covered",
            "T": "covered",
            "I": "covered",
            "D": "covered",
            "E": "covered"
          }
        },
        {
          "asset": "claim-ingress-API",
          "cells": {
            "S": "covered",
            "T": "covered",
            "I": "covered",
            "D": "covered",
            "E": "covered"
          }
        },
        {
          "asset": "adjudication-to-pricing",
          "cells": {
            "S": "silent",
            "T": "silent",
            "I": "covered",
            "D": "silent",
            "E": "silent"
          }
        }
      ]
    },
    "surface_coverage": {
      "rows": [
        {
          "surface": "claim-ingress-API",
          "present": [
            "S",
            "T",
            "I",
            "D",
            "E"
          ],
          "absent": [
            "R"
          ],
          "entry_count": 5
        },
        {
          "surface": "adjudication-to-pricing",
          "present": [
            "I"
          ],
          "absent": [
            "S",
            "T",
            "R",
            "D",
            "E"
          ],
          "entry_count": 1
        },
        {
          "surface": "audit-log-writer",
          "present": [
            "S",
            "T",
            "I",
            "D",
            "E"
          ],
          "absent": [
            "R"
          ],
          "entry_count": 5
        }
      ],
      "summary": {
        "total_entries": 11,
        "contradictions_emitted": 1,
        "silences_emitted": 1,
        "coverage_gaps_emitted": 1,
        "surfaces_examined": 3
      }
    },
    "surface_graph": {
      "nodes": [
        {
          "id": "adjudication-to-pricing",
          "type": "asset",
          "label": "adjudication-to-pricing",
          "badge": "I",
          "hot": false
        },
        {
          "id": "audit-log-writer",
          "type": "asset",
          "label": "audit-log-writer",
          "badge": "S T I D E",
          "hot": false
        },
        {
          "id": "claim-ingress-API",
          "type": "asset",
          "label": "claim-ingress-API",
          "badge": "S T I D E",
          "hot": false
        }
      ],
      "edges": []
    },
    "comparator_delta": null
  }
};
