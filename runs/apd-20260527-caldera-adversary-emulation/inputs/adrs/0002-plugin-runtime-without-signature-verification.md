---
title: 0002 — Plugins loaded as in-process Python modules without signature verification
status: accepted
date: 2018-11-12
---

# ADR-0002: Plugins loaded as in-process Python modules without signature verification

- **Status:** Accepted
- **Date:** 2018-11-12

## Context

Caldera's value to a red-team or detection-engineering operator
comes largely from its plugin ecosystem: 17 plugins ship in the
default distribution (`access`, `atomic`, `builder`, `compass`,
`debrief`, `emu`, `fieldmanual`, `gameboard`, `human`, `magma`,
`manx`, `response`, `sandcat`, `ssl`, `stockpile`, `training`,
and historical others), and operators routinely add third-party
plugins from MITRE-related projects (`arsenal`, `bountyhunter`,
`caltack`, `saml`) or their own internal plugins.

Plugins need to contribute *everything* — abilities, payloads,
parsers, UI panels, REST routes, login handlers, planners,
obfuscators, contact protocols, data encoders. The framework is
designed for extension. The operator audience is technical
enough to read plugin source before enabling it.

Caldera does not have, and has never claimed to have, a
software-supply-chain story analogous to e.g. signed
Docker-content-trust images or signed npm packages.

## Decision

Plugins are **directories under `plugins/`**, each containing a
`hook.py` that the server imports via `importlib.import_module`
at startup. The plugin is enabled if it appears in the
`plugins:` list of the active `conf/<env>.yml`. The plugin's
`enable(services)` method runs synchronously in the server's
event loop with full server privilege.

There is:

- **No plugin signing.** No PGP signature, no Sigstore, no
  in-tree checksum file.
- **No publisher allowlist.** Any directory the operator drops
  into `plugins/` is loadable.
- **No runtime sandbox.** Plugins use the same Python
  interpreter, the same filesystem permissions, the same
  network egress as the core server.
- **No per-plugin permission scope.** A plugin may register
  routes that overlap or override core routes; may
  monkey-patch any service; may read or write any file the
  server user can access.

Plugin trust is **operator-declared**: by adding the plugin
directory and enabling it in `conf/<env>.yml`, the operator is
asserting that the plugin's code is trusted.

## Consequences

**Positive (intended flexibility).**

- The framework is genuinely extensible. Every extension point
  (auth, planner, contact, obfuscator, parser, route) is
  plugin-replaceable without modifying core.
- New TTPs ship as YAML files in a plugin's `data/abilities/`,
  no code change required.
- Operators can write internal plugins without engaging the
  upstream maintainers.

**Negative / trade-offs.**

- **Supply-chain compromise of any plugin = full server
  compromise.** A typosquatted plugin source, a compromised
  GitHub account hosting a plugin, or a malicious internal
  contributor can place arbitrary Python in a plugin's
  `hook.py` that runs with full server privilege on next
  restart.
- **No restart-safe revocation.** Once an attacker has
  established persistence via a plugin, operator removal of
  the plugin requires identifying the malicious files. There
  is no signature-verification step at load time that would
  flag a tampered plugin.
- **Operator must read every plugin's source.** For 17 default
  plugins plus N operator-added plugins, this is operationally
  expensive — and the operator audience may not be qualified
  to audit every contributed dependency. Plugins themselves
  carry transitive Python dependencies installed into the
  Caldera virtualenv.
- **The `builder` plugin is especially privileged.** It invokes
  the system Go toolchain (`go build`) via subprocess to
  compile implant payloads, expanding the trusted boundary to
  the Go toolchain, the Go standard library, and any
  operator-supplied Go module dependency.
- **Login-handler plugin can silently capture credentials.**
  Setting `auth.login.handler.module: <plugin>` in
  `conf/<env>.yml` reroutes every login attempt through the
  plugin's code (threat-model S-4).

**Invariants pinned by this ADR (intended, not enforced).**

- Operators trust the plugins they enable. (Load-bearing
  trust assumption.)
- Plugin code runs in the same security context as the server.
- The `plugins/` directory is treated as part of the server
  binary for the purposes of integrity.

## Enforcement

- `AppService.load_plugins` iterates enabled plugins and calls
  `import_module(plugin_module_path)` then plugin.enable().
- No signature or hash check occurs.
- Operator filesystem permissions on `plugins/` are the only
  defence against post-deploy tampering.

## Notes

A future "signed plugins" posture would:

1. Require plugins to ship a manifest with a publisher key and
   a content hash of every plugin file.
2. Verify the manifest signature at load time against an
   operator-configurable trusted-publisher set.
3. Refuse to load plugins whose manifest is missing or
   whose hash does not match the on-disk content.

This would meaningfully reduce the WP-1 weapons-platform-misuse
risk, at the cost of operational friction for the long tail of
operator-authored internal plugins.
