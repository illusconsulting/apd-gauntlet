# Security tooling data taxonomy

Specialist agents treat the following data classes as sensitive when they appear in artifacts. The intake brief's data inventory MUST enumerate every class present; missing classes become evidence gaps surfaced as `blocked-on-evidence` findings against the intake set.

Security-tooling data taxonomy has an unusual property: many classes are **dual-natured** — they are both operationally sensitive to the platform AND inherit the highest sensitivity of any field they capture from customer or target environments. Result-data and engagement-audit content frequently inherit PHI, payment data, or credentialed-secret sensitivity from the engagements that produced them.

## Operator authentication material

- operator_password (cleartext — must never persist beyond hashing)
- operator_password_hash (argon2/scrypt/bcrypt; treat as sensitive even though irreversible)
- operator_mfa_seed (TOTP shared secret; equivalent to a long-lived credential bypass)
- operator_mfa_recovery_code (single-use bypass; equivalent to a knowledge-factor reset)
- operator_webauthn_credential (public key plus credential ID; less sensitive than seeds but still attributable)
- operator_api_token (bearer secret; long-lived credential — scope must be enumerated)
- operator_session_cookie (browser session identifier; equivalent to bearer token for the session window)
- operator_oauth_refresh_token (SSO-integrated platforms; longer-lived than access token)
- service_account_token for inter-platform integration (SIEM forwarder, ticketing-system bridge)

## Platform cryptographic material

- c2_signing_key (private half — the keys used to authenticate operator commands to implants; compromise yields global authentication bypass against fielded implants)
- c2_signing_key_public_half (still sensitive when paired with key-identifier — discloses platform fingerprint)
- implant_communication_key (per-implant or per-engagement keys used for callback encryption beyond TLS)
- listener_tls_certificate_chain (private half — separate concern from c2 signing keys but compromise enables MITM on the callback channel)
- listener_tls_intermediate_ca (if the platform operates its own CA for listener certificates)
- plugin_signing_root (the key the platform uses to verify plugin signatures — compromise enables plugin-trust subversion)
- audit_log_signing_key (used to hash-chain or sign audit entries; compromise enables undetectable audit forgery)

## Implant credentials

- implant_authentication_token (per-implant token implants present when callback registers; if compromised, attacker can substitute implants)
- implant_command_decryption_key (some implant designs encrypt the command channel beyond TLS using a per-implant key)
- implant_callback_url (the URL implants reach; sensitive because it inventories listener topology)
- implant_unique_identifier (per-implant ID burned into the deployed binary; correlates implant traffic to engagement)
- implant_capability_inventory (the list of abilities a given implant can execute; reveals operator tradecraft per-deployment)

## Engagement metadata

- target_inventory (in-scope hosts, networks, accounts, tenants; legally load-bearing as ROE evidence)
- roe_document (the Rules of Engagement contract — scope, authorization windows, target attestation, contact list)
- engagement_scope_definition (machine-readable form of the ROE used for runtime enforcement)
- customer_identification (organization name, point-of-contact, MSA reference; sensitive at the platform-multi-tenancy boundary)
- engagement_lifecycle_state (active/paused/closed; sensitive because active vs. closed determines lawful command issuance)
- authorization_window (time bounds for engagement activity; commands outside window are out-of-scope)

## Engagement results (highest-sensitivity inherited class)

- harvested_credentials (passwords, password hashes, API tokens, kerberos tickets, browser cookies captured from target environments; frequently customer-environment credentials usable in further attacks)
- harvested_files (documents, source code, configuration files, database dumps exfiltrated from targets)
- captured_screenshots (often contain PII, payment data, PHI, customer business data — inherits the highest-sensitivity classification of any field rendered)
- captured_keystrokes (often contain credentials being typed; equivalent to harvested credentials)
- command_outputs (results of commands executed on target hosts — process lists, network configurations, file contents)
- pivoted_access_tokens (cloud credentials, kerberos tickets, OAuth tokens obtained during the engagement)
- network_maps (target network topology, host inventory, service inventory — sensitive operational disclosure)

Result-data classes inherit the highest-sensitivity classification of any field they capture. A screenshot of a HIPAA-covered EHR system places the screenshot in PHI scope; a credential harvested from a PCI-scope cardholder data environment places the harvested credential in PCI scope.

## Plugin / module material

- plugin_source_code (source for community or third-party modules loaded into the platform)
- plugin_compiled_binary (precompiled module distribution — supply-chain provenance concerns)
- plugin_signature (the cryptographic signature attesting plugin authorship)
- plugin_manifest (declared capabilities, declared scope, declared dependencies)
- plugin_runtime_configuration (per-installation configuration; may contain credentials for external services the plugin integrates with)
- plugin_dependency_lockfile (the supply-chain manifest for the plugin's own dependencies)

## Audit content

- operator_action_event (login, logout, MFA challenge, role change, command issuance, result access — actor + action + target + outcome)
- implant_lifecycle_event (deployment, callback registration, decommission)
- engagement_lifecycle_event (start, scope-change, pause, resume, finalize — the legally-load-bearing audit class)
- command_issued_event (every command sent to every implant — including the command text, the operator who issued it, the target implant, the issue-time)
- result_access_event (operator reads harvested credentials/screenshots/files — actor + accessed-record + access-time)
- plugin_lifecycle_event (install, update, enable, disable, remove — with signature-verification outcome captured)
- configuration_change_event (admin changes to operator roles, audit configuration, signing-key lifecycle, listener configuration)
- audit_access_event (audit-of-audit: operator queried audit logs — actor + query + result count)

Audit content inherits the sensitivity of the highest-sensitivity field it captures, with an additional legal-defensibility dimension absent in non-security-tooling domains: the audit IS the evidence base for distinguishing authorized testing from unauthorized intrusion under CFAA, and IS the customer-deliverable provenance for engagement results.

## Result-correlation data

- engagement_to_customer_mapping (which engagement belongs to which customer — sensitive at multi-tenancy boundary)
- engagement_to_target_mapping (which engagement touched which target — legally load-bearing for ROE attestation)
- engagement_to_result_mapping (which engagement produced which result records — chain-of-custody for customer-deliverable findings)
- operator_to_engagement_mapping (which operator(s) participated in which engagement — accountability evidence)
- implant_to_engagement_mapping (which implant deployments belong to which engagement)
- timestamp_correlation_data (synchronized timestamps across operator-action, command-issued, and result-captured events — required for after-action review and dispute resolution)

## Out of scope

- public MITRE ATT&CK technique definitions (public knowledge; published by MITRE)
- public TTP catalogs (Atomic Red Team test definitions, public emulation plans)
- public CVE references and exploit metadata (already disclosed by the original source)
- public plugin manifests for plugins published in public registries (the existence of the plugin is not sensitive; the platform's choice of which to load may be)

This taxonomy is consulted primarily by the Confidentiality, Integrity, Non-Repudiation, and Authenticity specialists. The intake agent enumerates classes by reading artifacts against this list and surfaces missing-class declarations as `blocked-on-evidence` findings.
