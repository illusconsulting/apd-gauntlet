# authentik — Happy Path

The "happy path" is the workflow authentik is designed to support
when used as intended. This document describes the legitimate user
journeys (end-user enrollment, end-user login, operator administration)
so reviewers can distinguish expected behaviour from the threat-model
scenarios in `threat-model.md`.

## Prerequisites

- authentik is running per `install-config/install/docker-compose.mdx`
  or `install-config/install/kubernetes.md`.
- The operator has reached `http://<host>:9000` (or the
  reverse-proxy-fronted equivalent) and completed the initial
  admin-password setup for the `akadmin` user.
- The operator has configured (optionally) global email per
  `install-config/email.mdx`.
- DNS / TLS termination is in place per the operator's chosen
  topology.

## Conceptual model

authentik is a backend for:

- Authenticating end users via a configurable Flow + Stage + Policy
  pipeline.
- Issuing tokens (OAuth/OIDC), assertions (SAML), LDAP/RADIUS/RAC
  responses, and SCIM provisioning calls to downstream applications.
- Federating from upstream identity providers (Sources) into the
  local user model.
- Auditing every consequential action via the Event log.

The happy path is how a single end user enrols, authenticates,
gains access to a federated application, and how an operator
configures that application.

## End-user journey

### 1. End-user enrollment (Flow-driven)

The default-enrollment-flow (when enabled by the operator) is
typically:

```
Prompt (email, name, password) → User Write → User Login
```

- **Surface:** `/if/flow/default-enrollment-flow/` (or the
  operator-chosen slug).
- **What happens:** The Prompt stage collects user-supplied data.
  The User Write stage materialises the User record in PostgreSQL
  (with the password hashed via the platform's password hasher,
  per Django defaults augmented by `argon2-cffi==25.1.0` per
  `pyproject.toml`). The User Login stage materialises a session.
- **Expected result:** The user is enrolled and signed in. An
  `Event` of action `user_write` is created with the actor and
  context. If the Brand has a configured default Application, the
  user is redirected there per `sys-mgmt/brands/index.md`.

### 2. MFA enrollment (optional Flow-driven)

The default-user-settings-flow exposes authenticator-enrollment
stages. A typical WebAuthn enrollment is:

```
User accesses /if/user/#/settings →
  Authenticator-WebAuthn stage →
  WebAuthn ceremony (browser ↔ FIDO2 token) →
  Authenticator record bound to the user
```

- **Surface:** `/if/flow/default-user-settings-flow/`.
- **What happens:** The Authenticator-WebAuthn stage initiates the
  WebAuthn credential-creation ceremony per `webauthn==2.7.1`. On
  success, an authenticator device record is persisted bound to the
  user.
- **Expected result:** The user now has a WebAuthn factor. On next
  login, the default-authentication-flow's
  authenticator-validate stage will accept the WebAuthn factor.

### 3. End-user login (Flow-driven)

The default-authentication-flow:

```
Identification stage (username/email) →
  (Policy: which auth path?) →
  Password stage OR WebAuthn-only path →
  Authenticator Validation stage (MFA) →
  User Login stage
```

- **Surface:** `/if/flow/default-authentication-flow/`.
- **What happens:** The Identification stage takes the
  username/email and resolves the User record. Bound policies may
  branch (e.g. send corp users to a Source via the Source stage;
  send other users to the Password stage). The Password stage
  verifies the hashed password. The Authenticator Validation stage
  prompts for MFA. The User Login stage materialises the session.
- **Expected result:** A session cookie is set. If the user
  arrived via a `?next=` redirect from an Application access, the
  redirect resolves; otherwise the user lands on the Brand's
  Default Application or the user UI launcher.
- **Audit:** Per `sys-mgmt/events/index.md`, every Flow execution
  is event-logged.

### 4. Application access (OAuth/OIDC happy path)

The user clicks an application tile in the user UI launcher (or
the application redirects the user to the Provider's authorization
endpoint directly).

- **Surface:** `/application/o/authorize/?client_id=...&...`.
- **What happens (authorization-code grant):**
  1. The user (already authenticated per step 3) is presented with
     the Consent stage if scope consent has not been granted.
  2. authentik issues an authorization code, redirects the browser
     to the RP's `redirect_uri` with the code.
  3. The RP makes a server-side POST to `/application/o/token/`
     with the code + client_id + client_secret (or PKCE
     `code_verifier` for public clients).
  4. authentik validates and returns an access token, an ID token
     (if `openid` scope), and optionally a refresh token (if the
     `offline_access` scope was requested and granted, per the
     OAuth provider doc).
  5. The RP optionally calls `/application/o/userinfo/` with the
     access token to fetch the user claims.
- **Expected result:** The user is signed into the RP. An audit
  Event records the authorization and the token issuance.

### 5. Application access (SAML happy path)

For a SAML SP, the user clicks the application tile or the SP
initiates the request.

- **Surface:** `/application/saml/<slug>/` (SP-initiated) or
  `/application/saml/<slug>/init/` (IdP-initiated).
- **What happens:**
  1. authentik receives the AuthnRequest (or initiates one), runs
     the Authorization flow (per Provider configuration), and
     produces a signed SAML Response containing the AuthnAssertion.
  2. The AuthnAssertion includes the NameID per the Provider's
     NameID policy (Persistent / x509 / Windows / Transient /
     Email) and the configured attribute set per the property
     mappings.
  3. authentik delivers the Response to the SP's ACS URL per the
     selected binding (Redirect / POST).
- **Expected result:** The SP signs the user in based on the
  assertion. An audit Event records the SAML response issuance.

### 6. LDAP backend usage (legacy app)

A legacy application binds to the LDAP outpost as a configured
service-account user (or as the end user, depending on the app's
auth pattern).

- **Surface:** `ldap://<outpost-host>:389` or
  `ldaps://<outpost-host>:636`.
- **What happens:**
  1. The legacy app sends an LDAP BindRequest with the user's
     credentials.
  2. The LDAP outpost (per the LDAP provider doc) executes the
     Provider's configured Bind flow — i.e. the same Flow + Stage +
     Policy pipeline as web logins, just with LDAP transport.
  3. On success, the BindResponse is "success"; on failure,
     "invalidCredentials".
  4. Subsequent search operations against the bound session return
     User and Group records subject to the bound user's
     `Search full LDAP directory` permission.
- **Expected result:** The legacy app sees a "real" LDAP directory
  backed by authentik's User and Group corpus.

### 7. Proxy-protected app access (forward-auth happy path)

The user navigates to a legacy app behind the proxy outpost in
forward-auth mode.

- **Surface:** the legacy app's domain (e.g. `https://grafana.corp.example`).
- **What happens:**
  1. The reverse proxy in front of the legacy app forwards the
     request to the proxy outpost at `/outpost.goauthentik.io/...`
     for an auth decision.
  2. The proxy outpost checks the cookie; if absent or expired, it
     redirects the user to authentik's Authorization flow.
  3. On successful auth, the proxy outpost stamps
     `X-authentik-username`, `X-authentik-groups`,
     `X-authentik-email`, etc. headers on the forwarded request to
     the legacy app.
- **Expected result:** The legacy app reads the headers and signs
  the user in without needing native federation support.

### 8. Source-driven first login (federated identity)

A user authenticates against an upstream Source (e.g. corporate
SAML IdP).

- **Surface:** the Source stage in the authentik Flow.
- **What happens:**
  1. The Identification stage's "Selected sources" presents the
     Source as a login option.
  2. The Source stage hands the user off to the upstream IdP.
  3. The upstream IdP authenticates the user and returns the
     assertion / token to authentik.
  4. The Source's property mappings transform the upstream
     attributes into authentik User attribute writes.
  5. If this is a first login, a User record is created (per
     Source configuration); subsequent logins re-use the existing
     record.
- **Expected result:** The user has a local authentik User record
  reflecting the upstream IdP's attributes. The session is local;
  the user can now exercise OAuth/SAML/LDAP per steps 4–7 against
  authentik-configured Providers.

## Operator journey

### 9. Operator creates an OAuth Application + Provider pair

Per `add-secure-apps/providers/oauth2/create-oauth2-provider.md`:

1. Admin opens `/if/admin/#/core/applications` and clicks
   **New Application**.
2. Selects "New application with provider"; chooses the OAuth2/OpenID
   Provider type.
3. Configures:
   - Authentication flow (typically `default-authentication-flow`).
   - Authorization flow (typically `default-provider-authorization-explicit-consent`).
   - Client type (Confidential / Public).
   - Redirect URI(s).
   - Signing Key (CertificateKeyPair selection).
   - Encryption Key (optional).
   - Scopes (default + custom property-mapping-based scopes).
   - Subject mode (hashed user ID is the default).
4. Saves. The Application appears in the user-UI launcher; the
   OAuth endpoints are immediately functional.

### 10. Operator configures an outpost

Per `add-secure-apps/outposts/index.mdx`:

1. Admin opens `/if/admin/#/outpost/outposts` and clicks **Create**.
2. Sets:
   - Name.
   - Type (Proxy / LDAP / RADIUS / RAC).
   - Integration (Docker / Kubernetes / manual).
   - Applications (the Provider pairs the outpost serves).
3. Saves. authentik auto-generates a service-account token,
   auto-deploys the outpost container (if Docker/K8s integration
   is active), and begins streaming configuration over WebSocket.
4. The operator verifies the outpost shows healthy in
   `Dashboards > System Tasks`.

### 11. Operator audits Events

Per `sys-mgmt/events/index.md`:

1. Admin opens `/if/admin/#/events/log`.
2. Reviews the volume-graph for anomaly spikes.
3. Drills into individual Events to read the actor, action, app,
   and context.
4. Optionally configures Notification Rules bound to Event Matcher
   policies (e.g. "alert on user_write where context.action_id =
   account_lockdown" per the account lockdown doc).

## Normal usage past the happy path

- End users continue to access Applications via the launcher,
  passing the configured Authorization flow per Application.
- Operators continue to manage Users, Groups, Roles, Flows,
  Stages, Policies, Providers, Sources, Brands, and Outposts via
  the Admin UI.
- Tokens issued by OAuth Providers continue to be honored until
  expiry; SAML assertions are session-scoped to the SP.

## Next steps

Once the happy path is understood, reviewers proceed to:

- `threat-model.md` — STRIDE-organised view of where authentik
  deviates from this baseline (intentional configurability vs.
  unintentional misconfiguration risk).
- `invariants.md` — the architect-asserted invariants the platform
  claims; specialist reviewers should validate each.
- `prior-audit.md` — the carry-forward security posture from the
  upstream audits (Cure53, Cobalt, IncludeSec) and the CVE
  archive.
