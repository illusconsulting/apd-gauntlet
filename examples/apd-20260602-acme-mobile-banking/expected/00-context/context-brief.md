---
run_id: apd-20260602-acme-mobile-banking
domains:
  - mobile-applications
artifacts:
  - filename: tech_plan.md
    type: tech_plan
    relevance_hints: [confidentiality, integrity, authenticity, ephemeral, non_repudiation]
  - filename: AndroidManifest.xml
    type: config
    relevance_hints: [integrity, authenticity, confidentiality]
  - filename: Info.plist
    type: config
    relevance_hints: [authenticity, confidentiality]
  - filename: network_security_config.xml
    type: config
    relevance_hints: [confidentiality, authenticity, resilient]
data_inventory:
  - stored_access_token
  - stored_refresh_token
  - embedded_api_key
  - cached_pii_phi_on_device
  - advertising_id
  - deep_link_parameters
trust_boundaries:
  - client_to_backend_api
  - app_to_platform_keystore_tee
  - deep_link_ipc_entry_boundary
  - device_to_attestation_authority
---

# Context Brief — Acme Mobile Banking (mobile client)

A native Android + iOS banking client fronting the Acme banking REST API. The
review scope is the **mobile client and the mobile↔backend trust boundary**; the
backend authorization model is owned by a separate team and routes to the
api-security / identity-security packs in a multi-domain run.

## Capability surface

Authentication (password + biometric unlock), session/token storage on device,
fund transfer and bill-pay (including a `acmebank://transfer` deep link), offline
cached balances and profile, an in-app WebView, and bundled analytics /
crash-reporting SDKs.

## PHI/PII data inventory

On-device: access and refresh tokens, an embedded HMAC client secret, cached
member profile (name, email, masked account numbers), and the advertising
identifier. See the data taxonomy for field-level sensitivity.

## Evidence gaps

Backend authorization enforcement, server-side audit content, and the OAuth/OIDC
token-issuance design are not in the supplied artifacts and are routed to the
api-security / identity-security packs rather than analyzed here.
