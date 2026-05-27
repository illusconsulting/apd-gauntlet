// LegacyExample quickpath — extracted advisory data
// Source: runs/apd-legacy-example-run/40-synthesis/advisory-report.md
window.APD_DATA = {
  meta: {
    framework_version: "1.4.0",
    domain_pack: { name: "pbm", version: "1.0.0" },
    run_id: "apd-legacy-example-run",
    synthesizer_version: "1.0.0",
    specialists_skipped: [],
    subject: "LegacyExample v4.0",
    subject_tagline: "Render-path mediator for sensitive values",
    date: "2026-05-26",
    artifact_count: 13,
    artifact_types: ["tech_plan", "adr×5", "threat_model", "runbook", "test_report", "other×4"],
    crown_jewels: [
      "cleartext_in_main_thread_dom",
      "chain_secret_in_worker",
      "bundle_decryption_keys",
      "authorized_resolve_egress",
    ],
    attacker_positions: [
      "xss_pre_bootstrap",
      "compromised_main_thread_script",
      "compromised_browser_extension",
      "mitm_sidecar_upstream",
      "compromised_agui_agent",
    ],
  },

  // ────────────────────────────────────────────────────────────────────────
  // Summary roll-ups
  // ────────────────────────────────────────────────────────────────────────
  summary: {
    findings_total: 44,
    findings_pre_dedup: 51,
    cross_lens_merged_clusters: 4,
    linked_clusters: 6,
    bySeverity: { critical: 0, high: 16, medium: 21, low: 4, info: 3 },
    byDisposition: { gap: 14, blocked: 22, risk: 6, ok: 2 },
    byTier: { trustworthiness: 13, scalability: 14, auditability: 17 },
    capabilities_total: 48,
    capabilities_pre_dedup: 51,
    capabilitiesByMaturity: { designed: 4, implemented: 39, tested: 5, operationalized: 0 },
    contradictions: 3,
    severity_disagreements: 3,
  },

  // ────────────────────────────────────────────────────────────────────────
  // Confirmed capabilities (section 2 of the report)
  // ────────────────────────────────────────────────────────────────────────
  capabilities: [
    // Confidentiality
    { id: "conf-cap-3f6176f9", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Envelope encryption at the mediation boundary", scope: "AES-256-GCM field/record/list-level envelope encryption applied at the GraphQL/REST/AGUI mediation boundary before any byte of cleartext reaches the sidecar's response writer." },
    { id: "conf-cap-bc41682b", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "CryptoWorker as sole client-side realm", scope: "CryptoWorker is the sole client-side realm holding chain secrets and performing bundle decryption; main thread is provably unable to obtain either." },
    { id: "conf-cap-75a51217", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Closed Shadow DOM textContent-only writer", scope: "Cleartext renders exclusively inside closed Shadow DOM via <cg-protected> with textContent-only writer discipline; no innerHTML / host-attribute / dataset / CustomEvent detail path." },
    { id: "conf-cap-6966e78a", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Version-scoped HKDF labels + per-purpose AAD", scope: "Version-scoped HKDF labels and per-purpose AAD on bootstrap-sealed secrets prevent in-transit blob-slot swap and cross-purpose key reuse." },
    { id: "conf-cap-c90c72c5", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "v4 session secrets envelope-sealed at rest in Valkey", scope: "v4 session secrets at rest in Valkey envelope-sealed AES-256-GCM under contextID-bound AAD with namespace isolation from retired v2/v3 keyspaces." },
    { id: "conf-cap-ca3b86a0", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Closed-shadow form input tokenization", scope: "Closed-shadow form input cleartext tokenized as opaque inp_v4_* handles, AES-GCM-sealed at rest under handle-bound AAD, class-scoped consume validation." },
    { id: "conf-cap-693f8d10", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Out-of-wallet factors Worker-hashed", scope: "Out-of-wallet verification factors hashed inside the Worker; wire carries only HMAC-SHA256." },
    { id: "conf-cap-740046f7", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "AGUI per-line outbound mediation", scope: "AGUI generative-UI agents see only lmn_v4_* handles via per-line outbound mediation; inbound is structurally cleartext-free by design." },
    { id: "conf-cap-1183e9f6", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Slice 8 REST byte-parity with GraphQL", scope: "Slice 8 REST mediation reuses the v4 bundle envelope byte-identically; no new HKDF labels, Valkey namespaces, or wire format." },
    { id: "conf-cap-5db4f7d5", tier: "trustworthiness", goal: "confidentiality", maturity: "implemented", title: "Bootstrap zeroization + decrypt-surface absence", scope: "Bootstrap-path secret zeroization and build-tagged absence of bundle decryption surface in production binaries." },
    // Integrity
    { id: "intg-cap-5b243079", tier: "trustworthiness", goal: "integrity", maturity: "implemented", title: "Analyzer-authoritative schema-driven mediation", scope: "Analyzer-authoritative schema-driven mediation across GraphQL, REST, AGUI." },
    { id: "intg-cap-4dbe84b2", tier: "trustworthiness", goal: "integrity", maturity: "tested", title: "Chain-bound HMAC request proof", scope: "Chain-bound HMAC request proof with constant-time compare and Go/TS byte-parity." },
    { id: "intg-cap-ebd366bc", tier: "trustworthiness", goal: "integrity", maturity: "implemented", title: "Class-scoped input-token consume", scope: "Class-scoped input-token consume with atomic delete-after-validate and class-mismatch fail-closed." },
    { id: "intg-cap-42652738", tier: "trustworthiness", goal: "integrity", maturity: "tested", title: "Go↔TypeScript byte-parity conformance vectors", scope: "Go↔TypeScript byte-parity for every v4.* envelope pinned by tooling/conformance/vectors.json." },
    { id: "intg-cap-238b2c8f", tier: "trustworthiness", goal: "integrity", maturity: "implemented", title: "Bundle mint-time invariant", scope: "Bundle mint-time invariant (MemberID == '' iff len(VerifyFields) == 0); half-set state returns 500." },
    { id: "cap-merged-1", tier: "trustworthiness", goal: "integrity", maturity: "tested", merged: true, cross_lens: ["integrity", "availability", "resilient"], title: "Buffer-then-mediate-then-write fail-closed pipeline", scope: "Cross-lens fail-closed pipeline across GraphQL/REST/AGUI/subscription edges." },
    // Availability
    { id: "avail-cap-b34eddef", tier: "trustworthiness", goal: "availability", maturity: "implemented", title: "Per-route HTTP body size caps + 32 MiB pre-buffer cap", scope: "Per-route HTTP request-body size caps on every public v4 endpoint plus 32 MiB pre-buffer cap on REST binary pass-through." },
    { id: "avail-cap-0fb36640", tier: "trustworthiness", goal: "availability", maturity: "designed", title: "60-second Worker-side idle watchdog", scope: "60-second Worker-side idle watchdog on every subscription transport." },
    { id: "avail-cap-1d36e721", tier: "trustworthiness", goal: "availability", maturity: "designed", title: "WAF tier-1 rate limit on bootstrap", scope: "WAF tier-1 rate limit on /legacy_example/v4/bootstrap (100/min/IP) plus outcome-labeled bootstrap counter." },
    { id: "avail-cap-af79feb9", tier: "trustworthiness", goal: "availability", maturity: "implemented", title: "Atomic Valkey ops on subscription position", scope: "Atomic Valkey operations on subscription position and input-token consumption prevent races under sidecar scale-out." },
    { id: "cap-merged-2", tier: "trustworthiness", goal: "availability", maturity: "implemented", merged: true, cross_lens: ["availability", "distributed", "resilient", "ephemeral"], title: "SIGHUP-driven server-secret reload", scope: "SIGHUP-driven server-secret reload preserves in-flight session continuity." },
    // Distributed
    { id: "dist-cap-39f8bd9c", tier: "scalability", goal: "distributed", maturity: "implemented", title: "Stateless sidecar tier", scope: "Stateless sidecar application tier with all state externalized to Valkey, admits horizontal scale-out without inter-instance coordination." },
    { id: "dist-cap-bfb19b8b", tier: "scalability", goal: "distributed", maturity: "implemented", title: "Strict Valkey namespace isolation", scope: "Strict Valkey namespace isolation under cg:v4:* with documented per-key TTL discipline." },
    { id: "dist-cap-c3e50aa1", tier: "scalability", goal: "distributed", maturity: "implemented", title: "WebSocket Origin allowlist", scope: "Browser-facing WebSocket Origin allowlist enables multi-host topologies while keeping default same-Host posture." },
    { id: "dist-cap-f630bc43", tier: "scalability", goal: "distributed", maturity: "implemented", title: "Routing isolation — sealed v4 mux", scope: "v4 mux is a sealed surface with no fallthrough." },
    // Resilient
    { id: "resil-cap-92e1ed60", tier: "scalability", goal: "resilient", maturity: "designed", title: "Idle watchdog + classification", scope: "60-second Worker-side idle watchdog + per-event decrypt-failed / attestation-failed / watchdog-idle classification." },
    { id: "resil-cap-c33222af", tier: "scalability", goal: "resilient", maturity: "implemented", title: "Memory bulkheading via body caps", scope: "Per-route request body caps and 32 MiB binary pre-buffer cap implement memory bulkheading." },
    { id: "resil-cap-1222d324", tier: "scalability", goal: "resilient", maturity: "implemented", title: "STRICT-mode 404 + boot-time validation", scope: "STRICT-mode 404 on un-indexed REST paths + boot-time OpenAPI/AGUI registry validation." },
    { id: "resil-cap-8e0493b6", tier: "scalability", goal: "resilient", maturity: "implemented", title: "Atomic Valkey ops", scope: "Atomic Valkey operations on subscription position counter (INCR) and input-token consumption (atomic Get+Del)." },
    // Ephemeral
    { id: "ephem-cap-ed8a05d8", tier: "scalability", goal: "ephemeral", maturity: "implemented", title: "Per-session HKDF-derived key triple", scope: "Per-session HKDF-derived chain/bundle/attestation key triple bound to a fresh contextID." },
    { id: "ephem-cap-53a78e47", tier: "scalability", goal: "ephemeral", maturity: "implemented", title: "Single-use class-validated input tokens", scope: "Single-use class-validated input tokens (inp_v4_*) with atomic Get+Del consume and 5-min server-controlled TTL clamped to [60s, 30min]." },
    { id: "ephem-cap-fa25165b", tier: "scalability", goal: "ephemeral", maturity: "designed", title: "Bootstrap-handler stack zeroization", scope: "Bootstrap-handler stack zeroization for chain/bundle/attestation secrets immediately after response encoding." },
    { id: "ephem-cap-40e85ca3", tier: "scalability", goal: "ephemeral", maturity: "implemented", title: "Disjoint v4 Valkey namespaces", scope: "Disjoint v4 Valkey namespaces with class-specific TTL discipline." },
    // Authenticity
    { id: "auth-cap-3b0e216a", tier: "auditability", goal: "authenticity", maturity: "implemented", title: "OoW factor authenticity (3-strike lockout)", scope: "Out-of-wallet verification factor authenticity (Worker-hashed, session-salted, constant-time, three-strikes lockout)." },
    { id: "auth-cap-8961b46f", tier: "auditability", goal: "authenticity", maturity: "implemented", title: "Bootstrap handshake binds to fresh nonces", scope: "Bootstrap handshake binds session secrets to fresh client+server CSPRNG nonces per session." },
    { id: "auth-cap-14b5ae22", tier: "auditability", goal: "authenticity", maturity: "implemented", title: "Captured-natives snapshot", scope: "Captured-natives snapshot defeats post-bootstrap prototype poisoning." },
    { id: "auth-cap-f03a1f1b", tier: "auditability", goal: "authenticity", maturity: "implemented", title: "AGUI fields-registry boot-time class identity validation", scope: "AGUI fields-registry boot-time class identity validation." },
    { id: "auth-cap-fa1b5307", tier: "auditability", goal: "authenticity", maturity: "implemented", title: "Per-element MessagePort identity isolation", scope: "Per-element MessagePort identity isolation." },
    // Non-Repudiation
    { id: "nonrep-cap-e5f01dc0", tier: "auditability", goal: "non_repudiation", maturity: "implemented", title: "Per-request chain-proof HMAC", scope: "Per-request chain-proof HMAC binds caller to action data — cryptographic non-repudiation on every authenticated v4 request." },
    { id: "nonrep-cap-52ab2641", tier: "auditability", goal: "non_repudiation", maturity: "designed", title: "PHI-light AuditEvent schema", scope: "Verification audit schema (AuditEvent) deliberately PHI-light." },
    { id: "nonrep-cap-0cca2a8b", tier: "auditability", goal: "non_repudiation", maturity: "implemented", title: "Reveal-failure 401-collapse + audit-only Reason", scope: "Reveal-failure 401-collapse with audit-only Reason preservation." },
    { id: "nonrep-cap-e354b1a9", tier: "auditability", goal: "non_repudiation", maturity: "implemented", title: "Outcome-labeled Prometheus metrics", scope: "Outcome-labeled Prometheus metrics surface." },
    // Immutability
    { id: "immut-cap-a65a11f5", tier: "auditability", goal: "immutability", maturity: "tested", title: "Retirement-check drift detector", scope: "tooling/ci/retirement_check.sh declared-state-vs-actual drift detector." },
    { id: "immut-cap-8f558be6", tier: "auditability", goal: "immutability", maturity: "tested", title: "Byte-parity conformance vectors", scope: "Go↔TypeScript byte-parity conformance vectors pin the immutable wire format." },
    { id: "immut-cap-3cbe0761", tier: "auditability", goal: "immutability", maturity: "tested", title: "Production binary lacks decrypt surface", scope: "Production binary intentionally lacks any bundle-decryption surface (inspect build tag)." },
    { id: "immut-cap-0dddda77", tier: "auditability", goal: "immutability", maturity: "implemented", title: "npm provenance + SRI report", scope: "npm provenance attestation per release + per-release SRI hash report." },
    { id: "immut-cap-26932c78", tier: "auditability", goal: "immutability", maturity: "implemented", title: "Boot-time fail-closed validation", scope: "Boot-time fail-closed validation of OpenAPI x-legacy_example-class extensions and AGUI fields registry." },
    { id: "immut-cap-5bebafc8", tier: "auditability", goal: "immutability", maturity: "implemented", title: "Read-only /v4/explain", scope: "POST /legacy_example/v4/explain is read-only by construction." },
    { id: "immut-cap-455c9807", tier: "auditability", goal: "immutability", maturity: "tested", title: "Bundle handles AAD-bound to SessionID", scope: "Bundle handles cryptographically bind cleartext to a specific SessionID via AES-GCM AAD." },
    { id: "cap-merged-3", tier: "auditability", goal: "immutability", maturity: "tested", merged: true, cross_lens: ["integrity", "authenticity", "non_repudiation", "ephemeral", "immutability"], title: "Per-event subscription attestation", scope: "Per-event subscription attestation, cross-lens." },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // Strengths-notwithstanding-gaps (section 6)
  // ────────────────────────────────────────────────────────────────────────
  strengths: [
    { id: "conf-cap-3f6176f9", goal: "confidentiality", maturity: "implemented", caveats: [
      "32 MiB binary pass-through is mediation-exempt by spec (rule 77, INV-V4-REST-BINARY-1); adopters with cleartext PHI in binary payloads must apply complementary controls.",
      "Multipart file parts pass through byte-identical (rule 76).",
    ] },
    { id: "conf-cap-bc41682b", goal: "confidentiality", maturity: "implemented", caveats: [
      "Pre-bootstrap XSS defeats this boundary by patching natives before captureNatives runs (threat-model rows 1, 11).",
      "The Worker blob-URL runtime self-integrity check (WORKER_BLOB_DIGEST) is phase-8 work; see merged-3a8e5d77.",
    ] },
    { id: "conf-cap-75a51217", goal: "confidentiality", maturity: "implemented", caveats: [
      "aria-label on the container exposes full cleartext to assistive technology and DevTools (INV-V4-DOMSEG-6, threat-model row 10); auto-cleared on remask (default 30s).",
      "Slice 3.6 makes NO claim against screen capture, accessibility-tree reads from a motivated DevTools user, browser-bug closed-shadow bypass, Worker compromise, or sidecar compromise.",
    ] },
    { id: "conf-cap-c90c72c5", goal: "confidentiality", maturity: "implemented", caveats: [
      "KEK rotation cadence, KMS vendor, and key hierarchy not specified in inputs (see merged-9c1f8d62).",
      "Dual-compromise property (sidecar memory + Valkey) requires KEK to genuinely not be in Valkey — deployment-time assertion only, not runtime invariant.",
    ] },
    { id: "cap-merged-1", goal: "integrity", maturity: "tested", caveats: [
      "Addresses sidecar-side processing failures; does not address undetected upstream tampering of well-formed JSON (see merged-7c2a4f91).",
    ] },
    { id: "cap-merged-3", goal: "immutability", maturity: "tested", caveats: [
      "SSE Last-Event-ID reconnect path is silently unsupported (see intg-84204fa0).",
    ] },
    { id: "immut-cap-3cbe0761", goal: "immutability", maturity: "tested", caveats: [
      "Build-tag discipline enforced by Go's build system; a misconfigured release pipeline that built with -tags inspect would ship the decryption surface.",
      "CI gates and tooling/ci/retirement_check.sh don't currently assert on this combination.",
    ] },
    { id: "immut-cap-0dddda77", goal: "immutability", maturity: "implemented", caveats: [
      "Customer-side SRI gate plus provenance attestation check is partially documented (see auth-e2b416d3).",
      "One floating action reference in docs.yml (pnpm/action-setup@v4) — see immut-6b45175c, ephem-821f0fdb.",
    ] },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // Findings (sections 3 + 4 — both blocked and non-blocked)
  // ────────────────────────────────────────────────────────────────────────
  findings: [
    {
      id: "merged-7c2a4f91",
      title: "Sidecar→external transport lacks channel confidentiality/integrity AND workload identity",
      goal: "confidentiality", tier: "trustworthiness",
      severity: "high", confidence: "high", disposition: "gap",
      headline: true, headline_rank: 1,
      rubric_clause: "PBM rubric HIPAA breach-notification anchor — cross-member PHI exposure or forged identifier triggers §164.502(b) + §164.402.",
      summary: "On the sidecar↔upstream pre-seal hop, channel confidentiality, channel integrity, and workload identity are all absent simultaneously — closes the mitm_sidecar_upstream attacker position.",
      detail: "Tech plan describes egress to upstream GraphQL/REST endpoints, but the inputs do not specify mTLS, HMAC-signed response verification, or workload identity. An in-path adversary on the pre-seal hop could substitute upstream response fields and LegacyExample would seal attacker-chosen plaintext. Cross-lens framing preserved from conf-947d3b24, intg-ae62a427, auth-ff1237d0, intg-afd6e3a8.",
      evidence: [
        { artifact: "tech_plan.md", locator: "§sidecar-egress", excerpt: "Sidecar mediates calls to upstream GraphQL / REST endpoints …" },
        { artifact: "adrs/0002-worker-trust-boundary.md", locator: "L41-58", excerpt: "Worker trust boundary terminates at the sidecar; upstream channel out of scope." },
      ],
      recommendation: { posture: "required", detail: "Pin mTLS to customer-controlled CA on every sidecar→external edge, or add HMAC-signed response verification keyed via External Secrets Operator. Closes the mitm_sidecar_upstream attacker position." },
      mappings: {
        nist: ["SC-8", "SC-8(1)", "SC-13", "SC-16", "SC-23", "SC-23(3)", "SI-7", "SI-7(1)", "SI-10"],
        attack: ["T1040", "T1565.002", "T1557"],
        cwe: ["CWE-319", "CWE-345", "CWE-353", "CWE-295", "CWE-306"],
        owasp_api: ["API8:2023"],
      },
      lens_perspectives: ["conf-947d3b24", "intg-ae62a427", "auth-ff1237d0", "intg-afd6e3a8"],
    },
    {
      id: "merged-9c1f8d62",
      title: "KEK lifecycle unspecified across vendor, hierarchy, rotation, revocation, cross-instance consistency",
      goal: "confidentiality", tier: "trustworthiness",
      severity: "high", confidence: "high", disposition: "blocked",
      headline: true, headline_rank: 2,
      prerequisite_evidence: ["kek-hierarchy.md runbook", "kek-rotation.md runbook", "ESO HA topology spec"],
      summary: "KEK vendor, hierarchy, rotation cadence, revocation procedure, and cross-instance consistency are not stated in the inputs.",
      detail: "Compromise of the KEK unseals every active session simultaneously. Without published rotation cadence or revocation procedure, this is an unaccountable root of trust. Lens perspectives from conf-baad5c5c, ephem-2f1f4bf6, dist-5ac9ea77.",
      evidence: [
        { artifact: "tech_plan.md", locator: "§secret-management", excerpt: "Server secrets are KEK-sealed in Valkey." },
      ],
      recommendation: { posture: "required", detail: "Publish kek-hierarchy.md and kek-rotation.md runbooks naming vendor, hierarchy depth, rotation cadence, revocation procedure, ESO HA topology, and cross-instance consistency model." },
      mappings: {
        nist: ["SC-12", "SC-12(1)", "SC-12(2)", "SC-12(3)", "SC-28", "SC-28(1)", "IA-7"],
        cwe: ["CWE-321", "CWE-323", "CWE-324"],
        attack: [],
      },
      lens_perspectives: ["conf-baad5c5c", "ephem-2f1f4bf6", "dist-5ac9ea77"],
    },
    {
      id: "nonrep-bf44cc75",
      title: "Production audit sink silent in indexed code (only demodata AuditHook for /verify wired)",
      goal: "non_repudiation", tier: "auditability",
      severity: "high", confidence: "high", disposition: "gap",
      headline: true, headline_rank: 3,
      summary: "The production audit sink is silent in indexed code; only the demodata AuditHook for /verify is wired up.",
      detail: "Audit emission is missing for bootstrap, query mediation, input-token mint/consume, explain, AGUI mediation, REST mediation, and subscription mediation. HIPAA §164.312(b) audit-controls cannot be evaluated.",
      evidence: [
        { artifact: "code_repo", locator: "pkg/audit/", excerpt: "Only AuditHook implementation in tree is `demodata.AuditHook`, wired into /verify only." },
      ],
      recommendation: { posture: "required", detail: "Wire production audit emission for bootstrap, query mediation, input-token mint/consume, explain, AGUI mediation, REST mediation, and subscription mediation." },
      mappings: { nist: ["AU-2", "AU-3", "AU-3(1)", "AU-12", "AU-12(1)"], cwe: ["CWE-778", "CWE-223"], owasp_api: ["API9:2023"], attack: [] },
    },
    {
      id: "nonrep-6ec7b7bc",
      title: "No cryptographic protection on audit entries (no signing, no hash-chaining, no Merkle)",
      goal: "non_repudiation", tier: "auditability",
      severity: "high", confidence: "high", disposition: "gap",
      headline: true, headline_rank: 4,
      summary: "Audit entries lack cryptographic protection — no signing, no hash-chaining, no Merkle.",
      detail: "Without tamper-evidence, an insider or compromised audit pipeline can remove or rewrite audit records without detection. Pairs with `immut-041c80d2` (storage tier) and `nonrep-bf44cc75` (production sink).",
      recommendation: { posture: "required", detail: "Add hash-chaining or signing to audit entries; pin Merkle root in WORM storage." },
      mappings: { nist: ["AU-9", "AU-9(2)", "AU-9(3)", "AU-10", "AU-10(1)", "AU-10(2)"], attack: ["T1070.002"], cwe: ["CWE-345", "CWE-732", "CWE-778"] },
    },
    {
      id: "immut-041c80d2",
      title: "Production audit sink storage tier — WORM/append-only, hash-chaining, retention, legal-hold unspecified",
      goal: "immutability", tier: "auditability",
      severity: "high", confidence: "high", disposition: "blocked",
      headline: true, headline_rank: 5,
      prerequisite_evidence: ["audit-sink specification", "retention policy", "legal-hold procedure"],
      summary: "Storage tier, WORM/append-only posture, hash-chaining, retention, and legal-hold for the production audit sink are not specified.",
      recommendation: { posture: "required", detail: "Publish audit-sink specification — name storage tier, WORM/append-only posture, hash-chaining strategy, retention, and legal-hold procedure." },
      mappings: { nist: ["AU-9", "AU-9(2)", "AU-9(3)", "AU-11", "AU-11(1)"], cwe: ["CWE-778", "CWE-117"], attack: [] },
    },
    {
      id: "merged-2b9e1c4a",
      title: "Valkey unavailability → 401-collapse → re-bootstrap amplification loop",
      goal: "availability", tier: "trustworthiness",
      severity: "high", confidence: "high", disposition: "risk",
      headline: true, headline_rank: 6,
      summary: "Valkey unavailability collapses to 401 across every public handler, triggering client-side re-bootstrap → re-failure that amplifies Valkey write load.",
      detail: "The 401-collapse rule pairs with client-side re-bootstrap to produce a self-reinforcing failure pattern. Lens perspectives: avail-1cc6c326 (medium) and resil-3f41d9b1 (high).",
      recommendation: { posture: "recommended", detail: "Add jittered client-side retry and server-side 503 response when Valkey is unreachable; bypass re-bootstrap on Valkey health failure." },
      mappings: { nist: ["SI-13", "CP-2(3)", "AU-12", "SC-5", "SC-5(1)"], attack: ["T1499"], cwe: ["CWE-1188"] },
      lens_perspectives: ["avail-1cc6c326", "resil-3f41d9b1"],
    },
    {
      id: "resil-f1707918",
      title: "Outbound HTTP/WS timeout discipline unspecified for sidecar→upstream/AGUI/Valkey",
      goal: "resilient", tier: "scalability",
      severity: "high", confidence: "high", disposition: "blocked",
      headline: true, headline_rank: 7,
      prerequisite_evidence: ["outbound-timeout policy"],
      summary: "Outbound HTTP/WS timeout discipline is not specified for sidecar→upstream, sidecar→AGUI, or sidecar→Valkey.",
      mappings: { nist: ["SC-5", "SC-6", "SI-13"], attack: ["T1499"], cwe: [] },
    },
    {
      id: "resil-03bc8e63",
      title: "No circuit breaker on any outbound dependency",
      goal: "resilient", tier: "scalability",
      severity: "high", confidence: "high", disposition: "gap",
      headline: true, headline_rank: 8,
      summary: "No circuit breaker on any outbound dependency; single dependency degradation cascades through every handler.",
      mappings: { nist: ["SC-5", "SC-5(1)", "SC-6", "CP-2(3)"], attack: ["T1499"], cwe: [] },
    },
    {
      id: "avail-a553fbd0",
      title: "No DR/BCP/RTO/RPO for sidecar or Valkey-resident state",
      goal: "availability", tier: "trustworthiness",
      severity: "high", confidence: "high", disposition: "blocked",
      headline: true, headline_rank: 9,
      prerequisite_evidence: ["DR/BCP plan", "RTO/RPO targets"],
      summary: "HIPAA §164.308(a)(7) contingency-plan obligation cannot be evaluated.",
      mappings: { nist: ["CP-2", "CP-7", "CP-9", "CP-10", "CP-10(2)"], attack: [], cwe: [] },
    },
    {
      id: "auth-582e3252",
      title: "Required AAL (NIST 800-63B) for verification factor flow not specified",
      goal: "authenticity", tier: "auditability",
      severity: "high", confidence: "high", disposition: "blocked",
      headline: true, headline_rank: 10,
      prerequisite_evidence: ["AAL declaration", "verification-factor flow spec"],
      summary: "End-user identity assurance for <cg-protected> reveal-on-verify is delegated to adopter IAM but required AAL is not specified.",
      mappings: { nist: ["IA-2", "IA-2(1)", "IA-2(2)", "IA-8"], cwe: ["CWE-287", "CWE-308"], owasp_api: ["API8:2023"], owasp: ["A07:2021"], attack: [] },
    },
    // Remaining high (non-headline)
    { id: "dist-1a34b9ed", title: "Valkey deployment topology unspecified (replica/sentinel/cluster, AZ, persistence)", goal: "distributed", tier: "scalability", severity: "high", confidence: "high", disposition: "blocked", prerequisite_evidence: ["Valkey topology spec"], summary: "Valkey deployment topology (replica/sentinel/cluster, AZ, persistence) unspecified.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "dist-bbbafeef", title: "Sidecar multi-instance topology unspecified (sharding, PDB, anti-affinity)", goal: "distributed", tier: "scalability", severity: "high", confidence: "high", disposition: "blocked", prerequisite_evidence: ["sidecar Helm chart"], summary: "Sidecar multi-instance topology, sharding, PDB, anti-affinity unspecified.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "dist-6b113e98", title: "Multi-region/AZ posture across all tiers unspecified", goal: "distributed", tier: "scalability", severity: "high", confidence: "high", disposition: "blocked", prerequisite_evidence: ["multi-region deployment spec"], summary: "Multi-region / AZ posture across all tiers unspecified.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "nonrep-3da682b2", title: "Time-source policy for audit timestamps unspecified", goal: "non_repudiation", tier: "auditability", severity: "high", confidence: "high", disposition: "blocked", prerequisite_evidence: ["time-source policy"], summary: "Time-source policy for audit timestamps unspecified.", mappings: { nist: ["AU-8"], attack: [], cwe: [] } },
    { id: "nonrep-ae18bdde", title: "Audit shipping reliability unspecified (buffer/retry/no-audit-no-action)", goal: "non_repudiation", tier: "auditability", severity: "high", confidence: "high", disposition: "blocked", prerequisite_evidence: ["audit-shipping spec"], summary: "Audit shipping reliability — buffer, retry, no-audit-no-action behavior — unspecified.", mappings: { nist: ["AU-5"], attack: [], cwe: [] } },
    { id: "immut-a7e1e954", title: "Class registry / SDL point-in-time snapshot not retained", goal: "immutability", tier: "auditability", severity: "high", confidence: "high", disposition: "blocked", prerequisite_evidence: ["snapshot retention policy"], summary: "Class registry / SDL / OpenAPI spec point-in-time snapshot not retained.", mappings: { nist: ["CM-2", "CM-3"], attack: [], cwe: [] } },

    // Medium — selected
    { id: "merged-3a8e5d77", title: "Worker blob digest check site uncertainty (three-lens)", goal: "confidentiality", tier: "trustworthiness", severity: "medium", confidence: "high", disposition: "gap", summary: "WORKER_BLOB_DIGEST call site is unconfirmed; pre-init blob-URL-swap window may remain open.", mappings: { nist: ["SI-7", "SI-7(1)"], attack: ["T1055", "T1574"], cwe: [] } },
    { id: "conf-6dd180a1", title: "CSP nonce contract failure modes", goal: "confidentiality", tier: "trustworthiness", severity: "medium", confidence: "medium", disposition: "gap", summary: "Adopter CSP nonce contract failure modes not documented; weak nonces or unsafe-inline regressions go undetected.", mappings: { nist: ["SI-10"], attack: [], cwe: ["CWE-693"] } },
    { id: "conf-33f675ee", title: "Audit-event storage encryption-at-rest + PHI scope unspecified", goal: "confidentiality", tier: "trustworthiness", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["audit storage spec"], summary: "Audit-event storage tier encryption-at-rest and PHI-content scoping unspecified.", mappings: { nist: ["SC-28"], attack: [], cwe: [] } },
    { id: "conf-bf801274", title: "Sidecar memory in-use encryption residual", goal: "confidentiality", tier: "trustworthiness", severity: "medium", confidence: "medium", disposition: "risk", summary: "Sidecar holds cleartext PHI in-process between unseal and re-seal — residual risk requires runtime memory protections.", mappings: { nist: ["SC-28(1)"], attack: ["T1055"], cwe: [] } },
    { id: "intg-8c5135a7", title: "Adversarial-composition coverage on class registry + SDL", goal: "integrity", tier: "trustworthiness", severity: "medium", confidence: "medium", disposition: "blocked", prerequisite_evidence: ["class registry", "SDL", "AGUI fields registry"], summary: "Class registry / customer SDL / AGUI fields registry contents not in inputs — adversarial composition coverage unverifiable.", mappings: { nist: ["SI-10", "CM-7"], attack: [], cwe: [] } },
    { id: "avail-184abd68", title: "No SLO/SLI declared", goal: "availability", tier: "trustworthiness", severity: "medium", confidence: "high", disposition: "gap", summary: "No SLO or SLI declared for LegacyExample sidecar.", mappings: { nist: ["SI-13"], attack: [], cwe: [] } },
    { id: "avail-e052f6ab", title: "Sidecar liveness/readiness probe spec + depth unspecified", goal: "availability", tier: "trustworthiness", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["probe spec"], summary: "Sidecar liveness/readiness probe specification and depth unspecified.", mappings: { nist: ["CP-2"], attack: [], cwe: [] } },
    { id: "avail-7609c7d6", title: "Capacity headroom, body-cap concurrency budget, Valkey pool ceiling unspecified", goal: "availability", tier: "trustworthiness", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["capacity plan"], summary: "Sidecar capacity headroom, body-cap concurrency budget, Valkey pool ceiling unspecified.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "avail-4691a737", title: "Upstream/AGUI dependency availability targets unspecified", goal: "availability", tier: "trustworthiness", severity: "medium", confidence: "medium", disposition: "blocked", prerequisite_evidence: ["upstream SLAs"], summary: "Upstream/AGUI dependency availability targets unspecified for SLO composition.", mappings: { nist: ["SA-9"], attack: [], cwe: [] } },
    { id: "dist-c530001a", title: "CAP positioning unstated", goal: "distributed", tier: "scalability", severity: "medium", confidence: "medium", disposition: "gap", summary: "CAP positioning unstated; client semantics under Valkey partition unclear.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "dist-f79abbb8", title: "Failure-domain isolation between tenants unspecified", goal: "distributed", tier: "scalability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Failure-domain isolation between tenants unspecified — single tenant outage may cascade.", mappings: { nist: ["SC-7"], attack: [], cwe: [] } },
    { id: "resil-ca13438c", title: "No bulkheads between handler classes", goal: "resilient", tier: "scalability", severity: "medium", confidence: "medium", disposition: "gap", summary: "No bulkheads between handler classes — a single handler class can exhaust the goroutine pool.", mappings: { nist: ["SC-6"], attack: [], cwe: [] } },
    { id: "resil-10b83680", title: "Retry policy (jitter, backoff, budget) unspecified", goal: "resilient", tier: "scalability", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["retry policy spec"], summary: "Retry policy — jitter, backoff, budget — unspecified.", mappings: { nist: ["SC-5"], attack: [], cwe: [] } },
    { id: "resil-8432021a", title: "Worker death recovery contract unspecified", goal: "resilient", tier: "scalability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Worker death recovery contract unspecified — main thread behavior on Worker death undefined.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "resil-cf6e6715", title: "Subscription backpressure mechanism unspecified", goal: "resilient", tier: "scalability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Subscription backpressure mechanism unspecified for slow consumers.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "ephem-a5db1981", title: "v4 session lifetime / idle timeout / forced re-bootstrap cadence unspecified", goal: "ephemeral", tier: "scalability", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["session-lifetime policy"], summary: "v4 session lifetime, idle timeout, and forced re-bootstrap cadence unspecified.", mappings: { nist: ["AC-12"], attack: [], cwe: [] } },
    { id: "ephem-832c5f14", title: "Bundle/Attestation key rotation within session unspecified", goal: "ephemeral", tier: "scalability", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["key rotation policy"], summary: "BundleKey/AttestationKey rotation cadence within a long-lived session unspecified.", mappings: { nist: ["SC-12(2)"], attack: [], cwe: [] } },
    { id: "ephem-d9769328", title: "SIGHUP scope unstated for non-secret config", goal: "ephemeral", tier: "scalability", severity: "medium", confidence: "medium", disposition: "gap", summary: "SIGHUP-driven reload scope undocumented for non-secret config (class registry, SDL).", mappings: { nist: ["CM-3"], attack: [], cwe: [] } },
    { id: "ephem-821f0fdb", title: "pnpm/action-setup floating tag", goal: "ephemeral", tier: "scalability", severity: "medium", confidence: "high", disposition: "gap", summary: "Floating action reference (pnpm/action-setup@v4) in docs.yml CI workflow.", mappings: { nist: ["SR-3"], attack: ["T1195"], cwe: [] } },
    { id: "ephem-918f33a5", title: "Sidecar→upstream egress credential lifecycle unspecified", goal: "ephemeral", tier: "scalability", severity: "medium", confidence: "medium", disposition: "blocked", prerequisite_evidence: ["egress credential policy"], summary: "Sidecar→upstream egress credential lifecycle unspecified (gated on resolution of merged-7c2a4f91).", mappings: { nist: ["IA-5"], attack: [], cwe: [] } },
    { id: "auth-517aa7ed", title: "Chain-proof identity attribution scope limited", goal: "authenticity", tier: "auditability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Chain-proof HMAC binds caller to session, not to adopter IAM principal.", mappings: { nist: ["IA-2"], attack: [], cwe: [] } },
    { id: "auth-e2b416d3", title: "SDK supply-chain admission partially documented", goal: "authenticity", tier: "auditability", severity: "medium", confidence: "high", disposition: "gap", summary: "Adopter-side SRI gate + npm provenance verification flow partially documented.", mappings: { nist: ["SR-4"], attack: ["T1195"], cwe: [] } },
    { id: "auth-c4dfba09", title: "Bootstrap session identity binding to adopter IAM user unspecified", goal: "authenticity", tier: "auditability", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["adopter IAM binding spec"], summary: "Bootstrap session identity binding to adopter IAM user unspecified.", mappings: { nist: ["IA-2"], attack: [], cwe: [] } },
    { id: "nonrep-93d604a8", title: "Audit log access controls and SoD unspecified", goal: "non_repudiation", tier: "auditability", severity: "medium", confidence: "high", disposition: "blocked", prerequisite_evidence: ["audit access policy"], summary: "Audit log access controls and separation-of-duties unspecified.", mappings: { nist: ["AC-3", "AC-5"], attack: [], cwe: [] } },
    { id: "nonrep-e9995235", title: "/explain audit emission unspecified", goal: "non_repudiation", tier: "auditability", severity: "medium", confidence: "medium", disposition: "gap", summary: "/v4/explain reveal audit emission unspecified.", mappings: { nist: ["AU-2"], attack: [], cwe: [] } },
    { id: "nonrep-b01e188d", title: "Verification-failure sub-class taxonomy unstated", goal: "non_repudiation", tier: "auditability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Verification-failure sub-class taxonomy unstated in audit schema.", mappings: { nist: ["AU-3"], attack: [], cwe: [] } },
    { id: "immut-9d4f5b46", title: "Production drift detection limited to retirement_check", goal: "immutability", tier: "auditability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Production drift detection limited to retirement_check; no continuous policy-as-code admission.", mappings: { nist: ["CM-3"], attack: [], cwe: [] } },
    { id: "immut-6b45175c", title: "Build chain immutability — floating action references", goal: "immutability", tier: "auditability", severity: "medium", confidence: "high", disposition: "gap", summary: "One floating action reference (pnpm/action-setup@v4) in docs.yml — see ephem-821f0fdb.", mappings: { nist: ["SR-3"], attack: ["T1195"], cwe: [] } },
    { id: "immut-f8a2844a", title: "Post-session event delivery proof unspecified", goal: "immutability", tier: "auditability", severity: "medium", confidence: "medium", disposition: "gap", summary: "Post-session event delivery proof — store-and-forward audit semantics — unspecified.", mappings: { nist: ["AU-5"], attack: [], cwe: [] } },
    { id: "immut-d1b5722f", title: "Post-session immutable record of mints/consumes/mediations", goal: "immutability", tier: "auditability", severity: "medium", confidence: "medium", disposition: "blocked", prerequisite_evidence: ["post-session record spec"], summary: "Post-session immutable record of mints/consumes/mediations unspecified.", mappings: { nist: ["AU-11"], attack: [], cwe: [] } },

    // Low
    { id: "conf-0af0e8f2", title: "aria-label honest-boundary cleartext exposure (auto-clear 30s)", goal: "confidentiality", tier: "trustworthiness", severity: "low", confidence: "high", disposition: "risk", summary: "aria-label on <cg-protected> container exposes cleartext to AT and DevTools; auto-cleared on remask (default 30s).", mappings: { nist: ["SC-28"], attack: [], cwe: [] } },
    { id: "intg-84204fa0", title: "SSE Last-Event-ID reconnect path silently unsupported", goal: "integrity", tier: "trustworthiness", severity: "low", confidence: "high", disposition: "gap", summary: "SSE Last-Event-ID reconnect path silently unsupported; clients may experience event-loss on reconnect.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "dist-716102c7", title: "Worker per-tab failure domain (no cross-tab coordination)", goal: "distributed", tier: "scalability", severity: "low", confidence: "high", disposition: "risk", summary: "Worker per-tab failure domain — no cross-tab coordination.", mappings: { nist: [], attack: [], cwe: [] } },
    { id: "avail-b6972e05", title: "Security CI gate prod-mode gap", goal: "availability", tier: "trustworthiness", severity: "low", confidence: "medium", disposition: "gap", summary: "Security CI gate runs in development mode; prod-mode CI gap.", mappings: { nist: ["CM-3"], attack: [], cwe: [] } },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // Contradictions (section 5)
  // ────────────────────────────────────────────────────────────────────────
  contradictions: [
    {
      id: "contra-7f3a1e92",
      finding: { id: "merged-7c2a4f91", assertion: "cleartext PHI in motion on sidecar↔upstream channel without protection" },
      capability: { id: "conf-cap-3f6176f9", assertion: "envelope encryption applies before any byte of cleartext reaches the response writer" },
      comparison: "Not in conflict: the capability addresses the sidecar's own response writer on /legacy_example/v4/*, not the upstream's connection.",
      resolution: "Annotate the capability scope to name 'the sidecar's HTTP response writer' explicitly so the wording is not over-read.",
    },
    {
      id: "contra-3b1d8f44",
      finding: { id: "merged-7c2a4f91 (lens)", assertion: "in-path adversary substitutes upstream response fields → LegacyExample seals attacker-chosen plaintext" },
      capability: { id: "intg-cap-1732f37b / cap-merged-1", assertion: "buffer-then-mediate-then-write fail-closed" },
      comparison: "Not in conflict: fail-closed addresses sidecar-side processing errors (parse, seal, class-mismatch), not undetected upstream tampering of well-formed JSON.",
      resolution: "Clarify scope of 'fail-closed' in capability documentation.",
    },
    {
      id: "contra-5d9c2a13",
      finding: { id: "merged-3a8e5d77", assertion: "WORKER_BLOB_DIGEST call site unconfirmed" },
      capability: { id: "conf-cap-bc41682b / auth-cap-14b5ae22", assertion: "Worker isolation + captured-natives confirmed" },
      comparison: "Not in conflict: capabilities address post-init and post-bootstrap windows respectively; the finding is on the pre-init blob-URL-swap window.",
      resolution: "Existing capability caveat ('Pre-bootstrap XSS defeats this boundary…') already names the residual.",
    },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // Severity disagreements (section 10)
  // ────────────────────────────────────────────────────────────────────────
  severity_disagreements: [
    {
      id: "merged-7c2a4f91",
      agents: [
        { lens: "confidentiality", severity: "high" },
        { lens: "integrity (tamper)", severity: "high" },
        { lens: "authenticity", severity: "high" },
        { lens: "integrity (TLS)", severity: "medium" },
      ],
      chosen: "high",
      rationale: "Higher dominates per merge rule; HIPAA breach-notification anchor controls.",
    },
    {
      id: "merged-9c1f8d62",
      agents: [
        { lens: "ephemeral", severity: "high" },
        { lens: "confidentiality", severity: "medium" },
        { lens: "distributed", severity: "medium" },
      ],
      chosen: "high",
      rationale: "Higher dominates because the three concerns compose into an unaccountable root-of-trust posture; KEK compromise unseals every active session.",
    },
    {
      id: "merged-2b9e1c4a",
      agents: [
        { lens: "resilient", severity: "high" },
        { lens: "availability", severity: "medium" },
      ],
      chosen: "high",
      rationale: "Higher dominates because the re-bootstrap amplification is a self-reinforcing failure structurally, not merely an observability deficit.",
    },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // NIST family rollup (section 7)
  // ────────────────────────────────────────────────────────────────────────
  nist_rollup: [
    { family: "SC", title: "System & Communications Protection", covered: 18, gapped: 6, both: 6, notable: "SC-8(1), SC-12, SC-13, SC-23(3), SC-28 strong; SC-16 gapped" },
    { family: "SI", title: "System & Information Integrity", covered: 7, gapped: 5, both: 3, notable: "SI-7, SI-7(1), SI-10 strong; SI-7(7), SI-13(1) gapped" },
    { family: "AU", title: "Audit & Accountability", covered: 5, gapped: 9, both: 1, notable: "AU-2/3/9/10/11/12 nearly all gapped — largest family-level gap" },
    { family: "CM", title: "Configuration Management", covered: 7, gapped: 4, both: 2, notable: "CM-3/5/7 strong; CM-4, CM-6, CM-8 gapped" },
    { family: "CP", title: "Contingency Planning", covered: 2, gapped: 6, both: 0, notable: "CP-2/7/9/10 widely gapped — DR/BCP blocked on evidence" },
    { family: "AC", title: "Access Control", covered: 4, gapped: 5, both: 2, notable: "AC-3 strong; AC-5/6 gapped" },
    { family: "IA", title: "Identification & Authentication", covered: 1, gapped: 3, both: 1, notable: "IA-2 partial; IA-4, IA-8, IA-9 gapped" },
    { family: "SR", title: "Supply Chain Risk Management", covered: 3, gapped: 2, both: 0, notable: "SR-3/4 partial (supply chain)" },
    { family: "SA", title: "System & Services Acquisition", covered: 0, gapped: 2, both: 0, notable: "SA-9, SA-11 gapped" },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // ATT&CK exposure (section 8)
  // ────────────────────────────────────────────────────────────────────────
  attack_exposure: [
    { id: "T1499", name: "Endpoint Denial of Service", findings: 5, mitigations: ["avail-cap-b34eddef", "avail-cap-1d36e721", "resil-cap-c33222af", "resil-cap-92e1ed60"], coverage: "partial", note: "Volumetric covered, dependency-degradation gapped" },
    { id: "T1040", name: "Network Sniffing", findings: 1, mitigations: ["conf-cap-3f6176f9", "conf-cap-1183e9f6"], coverage: "partial", note: "Pre-seal hop uncovered" },
    { id: "T1055", name: "Process Injection", findings: 1, mitigations: ["conf-cap-bc41682b", "auth-cap-14b5ae22"], coverage: "partial", note: "Pre-init blob-URL window uncovered" },
    { id: "T1059.007", name: "JavaScript", findings: 1, mitigations: ["auth-cap-14b5ae22"], coverage: "partial", note: "Pre-bootstrap window gapped" },
    { id: "T1070.002", name: "Audit clearing", findings: 1, mitigations: [], coverage: "uncovered", note: "Phase-C bottleneck" },
    { id: "T1078", name: "Valid Accounts", findings: 1, mitigations: ["auth-cap-3b0e216a"], coverage: "partial", note: "Does not bind to adopter IAM" },
    { id: "T1195", name: "Supply Chain Compromise", findings: 1, mitigations: ["immut-cap-0dddda77", "immut-cap-a65a11f5"], coverage: "covered" },
    { id: "T1530", name: "Data from Cloud Storage", findings: 0, mitigations: ["conf-cap-c90c72c5", "conf-cap-740046f7"], coverage: "covered" },
    { id: "T1552", name: "Unsecured Credentials", findings: 1, mitigations: ["ephem-cap-ed8a05d8"], coverage: "partial", note: "Session-key rotation within session uncovered" },
    { id: "T1557", name: "Adversary-in-the-Middle", findings: 1, mitigations: ["auth-cap-fa1b5307", "conf-cap-ca3b86a0"], coverage: "partial", note: "Sidecar↔upstream uncovered" },
    { id: "T1565.002", name: "Transmitted-data manipulation", findings: 1, mitigations: ["immut-cap-455c9807", "cap-merged-3", "auth-cap-f03a1f1b"], coverage: "partial", note: "Sidecar↔upstream response tampering uncovered" },
    { id: "T1574", name: "Hijack Execution Flow", findings: 1, mitigations: ["conf-cap-bc41682b"], coverage: "partial", note: "Pre-init artifact-identity check gap" },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // APD coverage matrix (section 9)
  // ────────────────────────────────────────────────────────────────────────
  apd_matrix: {
    goals: ["conf", "intg", "avail", "dist", "resil", "ephem", "auth", "nonrep", "immut"],
    goalLabels: { conf: "Conf", intg: "Intg", avail: "Avail", dist: "Dist", resil: "Resil", ephem: "Ephem", auth: "Auth", nonrep: "NonRep", immut: "Immut" },
    rows: [
      { component: "Go sidecar process",     cells: { conf: "both", intg: "both", avail: "both", dist: "both", resil: "both", ephem: "both", auth: "both", nonrep: "both", immut: "both" } },
      { component: "Valkey store",           cells: { conf: "both", intg: "covered", avail: "both", dist: "both", resil: "both", ephem: "both", auth: "covered", nonrep: "silent", immut: "both" } },
      { component: "CryptoWorker",           cells: { conf: "both", intg: "both", avail: "gapped", dist: "gapped", resil: "covered", ephem: "covered", auth: "both", nonrep: "covered", immut: "covered" } },
      { component: "<cg-protected> element", cells: { conf: "both", intg: "covered", avail: "covered", dist: "covered", resil: "covered", ephem: "covered", auth: "covered", nonrep: "silent", immut: "covered" } },
      { component: "Audit log pipeline",     cells: { conf: "gapped", intg: "silent", avail: "gapped", dist: "silent", resil: "silent", ephem: "silent", auth: "silent", nonrep: "gapped", immut: "gapped" } },
      { component: "WAF + Helm deployment",  cells: { conf: "covered", intg: "covered", avail: "both", dist: "gapped", resil: "covered", ephem: "silent", auth: "covered", nonrep: "silent", immut: "gapped" } },
      { component: "GraphQL/REST mux",       cells: { conf: "covered", intg: "both", avail: "covered", dist: "covered", resil: "covered", ephem: "silent", auth: "covered", nonrep: "covered", immut: "covered" } },
      { component: "AGUI surface",           cells: { conf: "both", intg: "covered", avail: "covered", dist: "covered", resil: "covered", ephem: "covered", auth: "covered", nonrep: "silent", immut: "covered" } },
    ],
  },

  // ────────────────────────────────────────────────────────────────────────
  // Next steps (report tail)
  // ────────────────────────────────────────────────────────────────────────
  next_steps: [
    { rank: 1, text: "Resolve the sidecar→external transport cluster (merged-7c2a4f91) — the single architectural change that closes T1040, T1557, T1565.002 against mitm_sidecar_upstream. mTLS with customer-controlled CA is the lowest-friction path.", refs: ["merged-7c2a4f91"] },
    { rank: 2, text: "Publish KEK lifecycle documentation (merged-9c1f8d62) — name vendor, hierarchy, rotation cadence, revocation procedure, ESO HA topology.", refs: ["merged-9c1f8d62"] },
    { rank: 3, text: "Wire production audit emission for consequential actions beyond /verify (nonrep-bf44cc75) and decide audit cryptographic protection (nonrep-6ec7b7bc) + storage tier (immut-041c80d2) + access controls (nonrep-93d604a8) + retention — these four tend to land together as a single audit-pipeline runbook.", refs: ["nonrep-bf44cc75", "nonrep-6ec7b7bc", "immut-041c80d2", "nonrep-93d604a8"] },
    { rank: 4, text: "Resolve DR/BCP/RTO/RPO + Valkey topology + sidecar replica posture + multi-region — the four together compose the operator-runbook section that's referenced but not in inputs.", refs: ["avail-a553fbd0", "dist-1a34b9ed", "dist-bbbafeef", "dist-6b113e98"] },
    { rank: 5, text: "Resolve outbound timeout / circuit-breaker / retry cluster (resil-f1707918, resil-03bc8e63, resil-10b83680) — closes T1499 dependency-degradation flavor.", refs: ["resil-f1707918", "resil-03bc8e63", "resil-10b83680"] },
    { rank: 6, text: "Confirm WORKER_BLOB_DIGEST call site (merged-3a8e5d77) — closes T1055/T1574 pre-init artifact-identity window.", refs: ["merged-3a8e5d77"] },
    { rank: 7, text: "Publish session-lifetime / AAL / adopter-IAM-binding (ephem-a5db1981, auth-582e3252, auth-c4dfba09).", refs: ["ephem-a5db1981", "auth-582e3252", "auth-c4dfba09"] },
    { rank: 8, text: "Remaining medium and low findings, in any order.", refs: [] },
  ],

  // ────────────────────────────────────────────────────────────────────────
  // Tiny taxonomy hover dictionary
  // ────────────────────────────────────────────────────────────────────────
  taxonomy: {
    "SC-8": { family: "NIST 800-53r5", title: "Transmission Confidentiality and Integrity" },
    "SC-8(1)": { family: "NIST 800-53r5", title: "Transmission Confidentiality and Integrity | Cryptographic Protection" },
    "SC-12": { family: "NIST 800-53r5", title: "Cryptographic Key Establishment and Management" },
    "SC-13": { family: "NIST 800-53r5", title: "Cryptographic Protection" },
    "SC-16": { family: "NIST 800-53r5", title: "Transmission of Security and Privacy Attributes" },
    "SC-23": { family: "NIST 800-53r5", title: "Session Authenticity" },
    "SC-23(3)": { family: "NIST 800-53r5", title: "Session Authenticity | Unique System-Generated Identifiers" },
    "SC-28": { family: "NIST 800-53r5", title: "Protection of Information at Rest" },
    "SC-28(1)": { family: "NIST 800-53r5", title: "Protection of Information at Rest | Cryptographic Protection" },
    "SC-5": { family: "NIST 800-53r5", title: "Denial-of-Service Protection" },
    "SC-6": { family: "NIST 800-53r5", title: "Resource Availability" },
    "SC-7": { family: "NIST 800-53r5", title: "Boundary Protection" },
    "SI-7": { family: "NIST 800-53r5", title: "Software, Firmware, and Information Integrity" },
    "SI-7(1)": { family: "NIST 800-53r5", title: "Integrity Checks" },
    "SI-10": { family: "NIST 800-53r5", title: "Information Input Validation" },
    "SI-13": { family: "NIST 800-53r5", title: "Predictable Failure Prevention" },
    "AU-2": { family: "NIST 800-53r5", title: "Event Logging" },
    "AU-3": { family: "NIST 800-53r5", title: "Content of Audit Records" },
    "AU-3(1)": { family: "NIST 800-53r5", title: "Content of Audit Records | Additional Audit Information" },
    "AU-5": { family: "NIST 800-53r5", title: "Response to Audit Logging Process Failures" },
    "AU-8": { family: "NIST 800-53r5", title: "Time Stamps" },
    "AU-9": { family: "NIST 800-53r5", title: "Protection of Audit Information" },
    "AU-9(2)": { family: "NIST 800-53r5", title: "Audit Storage on Separate Systems" },
    "AU-9(3)": { family: "NIST 800-53r5", title: "Audit Information | Cryptographic Protection" },
    "AU-10": { family: "NIST 800-53r5", title: "Non-Repudiation" },
    "AU-11": { family: "NIST 800-53r5", title: "Audit Record Retention" },
    "AU-12": { family: "NIST 800-53r5", title: "Audit Record Generation" },
    "AU-12(1)": { family: "NIST 800-53r5", title: "Audit Record Generation | System-Wide / Time-Correlated Audit Trail" },
    "CP-2": { family: "NIST 800-53r5", title: "Contingency Plan" },
    "CP-2(3)": { family: "NIST 800-53r5", title: "Resume Mission and Business Functions" },
    "CP-7": { family: "NIST 800-53r5", title: "Alternate Processing Site" },
    "CP-9": { family: "NIST 800-53r5", title: "System Backup" },
    "CP-10": { family: "NIST 800-53r5", title: "System Recovery and Reconstitution" },
    "CP-10(2)": { family: "NIST 800-53r5", title: "Transaction Recovery" },
    "AC-3": { family: "NIST 800-53r5", title: "Access Enforcement" },
    "AC-5": { family: "NIST 800-53r5", title: "Separation of Duties" },
    "AC-12": { family: "NIST 800-53r5", title: "Session Termination" },
    "IA-2": { family: "NIST 800-53r5", title: "Identification and Authentication (Organizational Users)" },
    "IA-2(1)": { family: "NIST 800-53r5", title: "Multi-Factor Authentication to Privileged Accounts" },
    "IA-2(2)": { family: "NIST 800-53r5", title: "Multi-Factor Authentication to Non-Privileged Accounts" },
    "IA-5": { family: "NIST 800-53r5", title: "Authenticator Management" },
    "IA-7": { family: "NIST 800-53r5", title: "Cryptographic Module Authentication" },
    "IA-8": { family: "NIST 800-53r5", title: "Identification and Authentication (Non-Organizational Users)" },
    "CM-3": { family: "NIST 800-53r5", title: "Configuration Change Control" },
    "CM-7": { family: "NIST 800-53r5", title: "Least Functionality" },
    "SA-9": { family: "NIST 800-53r5", title: "External System Services" },
    "SR-3": { family: "NIST 800-53r5", title: "Supply Chain Controls and Processes" },
    "SR-4": { family: "NIST 800-53r5", title: "Provenance" },
    "T1040": { family: "MITRE ATT&CK", title: "Network Sniffing" },
    "T1055": { family: "MITRE ATT&CK", title: "Process Injection" },
    "T1059.007": { family: "MITRE ATT&CK", title: "Command & Scripting Interpreter: JavaScript" },
    "T1070.002": { family: "MITRE ATT&CK", title: "Indicator Removal: Clear Linux or Mac System Logs" },
    "T1078": { family: "MITRE ATT&CK", title: "Valid Accounts" },
    "T1195": { family: "MITRE ATT&CK", title: "Supply Chain Compromise" },
    "T1499": { family: "MITRE ATT&CK", title: "Endpoint Denial of Service" },
    "T1530": { family: "MITRE ATT&CK", title: "Data from Cloud Storage" },
    "T1552": { family: "MITRE ATT&CK", title: "Unsecured Credentials" },
    "T1557": { family: "MITRE ATT&CK", title: "Adversary-in-the-Middle" },
    "T1565.002": { family: "MITRE ATT&CK", title: "Data Manipulation: Transmitted Data Manipulation" },
    "T1574": { family: "MITRE ATT&CK", title: "Hijack Execution Flow" },
    "CWE-117": { family: "CWE", title: "Improper Output Neutralization for Logs" },
    "CWE-223": { family: "CWE", title: "Omission of Security-Relevant Information" },
    "CWE-287": { family: "CWE", title: "Improper Authentication" },
    "CWE-295": { family: "CWE", title: "Improper Certificate Validation" },
    "CWE-306": { family: "CWE", title: "Missing Authentication for Critical Function" },
    "CWE-308": { family: "CWE", title: "Use of Single-Factor Authentication" },
    "CWE-319": { family: "CWE", title: "Cleartext Transmission of Sensitive Information" },
    "CWE-321": { family: "CWE", title: "Use of Hard-coded Cryptographic Key" },
    "CWE-323": { family: "CWE", title: "Reusing a Nonce, Key Pair in Encryption" },
    "CWE-324": { family: "CWE", title: "Use of a Key Past Its Expiration Date" },
    "CWE-345": { family: "CWE", title: "Insufficient Verification of Data Authenticity" },
    "CWE-353": { family: "CWE", title: "Missing Support for Integrity Check" },
    "CWE-693": { family: "CWE", title: "Protection Mechanism Failure" },
    "CWE-732": { family: "CWE", title: "Incorrect Permission Assignment for Critical Resource" },
    "CWE-778": { family: "CWE", title: "Insufficient Logging" },
    "CWE-1188": { family: "CWE", title: "Initialization of a Resource with an Insecure Default" },
    "API8:2023": { family: "OWASP API Top 10", title: "Security Misconfiguration" },
    "API9:2023": { family: "OWASP API Top 10", title: "Improper Inventory Management" },
    "A07:2021": { family: "OWASP Top 10", title: "Identification and Authentication Failures" },
  },
};
