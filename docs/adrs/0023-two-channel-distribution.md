# ADR-0023: Two-Channel Distribution — PyPI Engine + Claude Code Plugin

**Status:** Accepted
**Date:** 2026-06-24
**Relates to:** [ADR-0007](0007-optional-code-reconnaissance-via-cbm.md) (CBM integration — the plugin's external dependency)

## Context

The APD gauntlet has two distinct distribution needs that don't map cleanly to a
single channel:

1. **A standalone Python engine** — the deterministic CLI (`apd-gauntlet`),
   bundled schemas/domains/taxonomies, and prebuilt HTML report bundle. This must
   install with a bare `pip install` and work offline with no repo clone or Claude
   Code session. In the first implementation the wheel crashed on import because
   `resources.py` resolved `schemas/` and `domains/` relative to the repo root —
   paths that don't exist inside a wheel.

2. **An agentic Claude Code plugin** — the agents, skills, and workflow runner
   that Claude Code loads by name. The workflow runner is not a plugin component
   (Claude Code's plugin system has no "workflow" primitive), but can be bridged
   via a slash command. The plugin manifest (`plugin.json`) lived at the repo root,
   which is not where Claude Code's plugin discovery expects it.

Shipping both under a single channel (PyPI-only, or plugin-only) would either
break the standalone wheel use-case or require consumers to clone the repo just to
get the CLI.

## Decision

Ship via **two lockstep channels** — one PyPI package and one Claude Code plugin
— with the following concrete choices:

### PyPI engine — wheel-safe resource resolution

- **Relocate `schemas/` and `domains/` into the package tree** at
  `tools/apd_gauntlet/data/{schemas,domains}`. These directories are now the
  single source of truth; the wheel includes them via `package_data` /
  `include_package_data`.
- **Keep repo-root symlinks** (`schemas/ → tools/apd_gauntlet/data/schemas`,
  `domains/ → tools/apd_gauntlet/data/domains`) so all dev/test/CI paths that
  reference the repo root continue to work unchanged.
- **Add `tools/apd_gauntlet/resources.py`** — a locator that resolves bundled
  data paths via `importlib.resources` when running from a wheel, and falls back
  to the package-relative path in editable installs. All package reads route
  through this module; no code accesses repo-root paths at runtime.

### Claude Code plugin — manifest location and marketplace

- **Move the plugin manifest** to `.claude-plugin/plugin.json` (the directory
  Claude Code's plugin loader expects).
- **Add `.claude-plugin/marketplace.json`** — a marketplace descriptor with
  `name: apd-security` and `owner: { name: "APD Gauntlet contributors" }` so the
  plugin is installable via `/plugin install apd-gauntlet@apd-security`. The
  `illusconsulting/apd-gauntlet` in `/plugin marketplace add
  illusconsulting/apd-gauntlet` is the GitHub org/repo the marketplace is fetched
  from, not the `owner` field.
- **Add `commands/run.md`** — a `/apd-gauntlet:run` slash command that bridges
  the non-component workflow runner via `${CLAUDE_PLUGIN_ROOT}` and enforces the
  foreground/interactive execution requirement (consistent with the gauntlet's
  existing discipline — background launch can interrupt subagent dispatches).
- **The plugin requires the `apd-gauntlet` PyPI package on PATH.** The plugin
  ships agents and skills; the workflow runner shells out to the CLI for
  deterministic passes. This is declared in `plugin.json`'s description and the
  `commands/run.md` preflight step.

### Versioning and attribution

- **Lockstep versioning at 1.7.0** — `pyproject.toml`, `tools/apd_gauntlet/__init__.py`,
  `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` all carry the
  same version. This is the first version shipped under the two-channel model;
  it was never previously released as a versioned artifact.
- **`NOTICE` file at repo root** — attributes bundled, redistributed knowledge
  bases (MITRE ATT&CK, CAPEC, D3FEND, CWE, OWASP, NIST reference data) to their
  respective authorities and licenses, satisfying open-source redistribution
  requirements.

## Consequences

**Positive:**

- `pip install apd-gauntlet` produces a fully self-contained CLI with no repo
  clone required; all schemas, domains, and reference data are bundled in the
  wheel and resolved via `importlib.resources`.
- The plugin is installable from the Claude Code marketplace without a manual
  manifest path. Version pinning means consumers only receive updates when the
  version changes.
- Attribution for bundled third-party knowledge bases is centralized in `NOTICE`
  and survives packaging.
- Lockstep versioning makes version drift detectable in CI
  (`test_plugin_manifest_version_matches_pyproject`).

**Negative / tradeoffs:**

- **Committed symlinks** (`schemas/ → …/data/schemas`, `domains/ → …/data/domains`)
  must be maintained as real filesystem symlinks. Git tracks them; CI must run on
  a POSIX filesystem where symlinks resolve correctly.
- **Explicit `agents[]` and `skills[]` arrays in `plugin.json`** require a
  manual update whenever an agent or skill is added or removed. Drift-guard CI
  checks (`test_agents_array_matches_dir` / `test_skills_array_matches_dir` in
  `tests/test_plugin_manifest.py`) catch this before release.
- **The plugin depends on the wheel being installed separately** — installing the
  plugin alone does not give the user a working CLI. The `commands/run.md`
  preflight step checks `apd-gauntlet --version` and stops with an actionable
  message if it is missing.
- **PEP 639 license metadata migration** — `pyproject.toml` already sets
  `license-files = ["LICENSE", "NOTICE"]` (under `[tool.setuptools]`). The
  remaining migration is replacing the table-form `license = { text = "Apache-2.0" }`
  with the PEP 639 string form `license = "Apache-2.0"`, dropping the `License ::`
  classifier, and bumping the build requirement to `setuptools>=77`. See
  `RELEASING.md` for the migration steps.

## Alternatives considered

- **PyPI-only, no plugin.** Rejected: the nine specialist agents and skills exist
  in the plugin layer; publishing them to PyPI as Python assets would be
  non-standard and lose the plugin discovery mechanism.
- **Plugin-only, no PyPI package.** Rejected: the deterministic CLI passes
  (`canonicalize`, `build-report`, `analyze-attack-paths`) must be available
  headlessly and in CI, where no Claude Code session is running.
- **Keep schemas/domains at repo root, resolve them at runtime via env var.**
  Rejected: it makes the wheel's behavior environment-dependent and requires
  callers to set an env var on every install, eliminating the "bare pip install
  just works" guarantee.

## References

- [ADR-0007](0007-optional-code-reconnaissance-via-cbm.md) — CBM integration
  (the external optional dependency the plugin wraps)
- [ADR-0020](0020-tooling-authored-derived-fields.md) — deterministic field
  ownership (the principle that motivates keeping the CLI deterministic and
  separable from the agentic layer)
- `tools/apd_gauntlet/resources.py` — the `importlib.resources` locator
- `.claude-plugin/plugin.json` — plugin manifest
- `.claude-plugin/marketplace.json` — marketplace descriptor
- `commands/run.md` — `/apd-gauntlet:run` slash command
- `NOTICE` — bundled knowledge-base attribution
- `RELEASING.md` — release runbook for both channels
