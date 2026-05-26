# Schema Evolution

APD Gauntlet has three independent versions:

| Thing | Where it lives | Bumped when |
|---|---|---|
| **Framework version** | `pyproject.toml`, git tags, `framework_version` field on context brief and advisory report | The `.claude/` content or schemas change in a way users notice |
| **Schema version** | `schema_version` integer field on each finding and capability record | A schema gets a breaking change |
| **Domain pack version** | `version` field in each pack's `domain.yaml` | Pack-specific rubric or pattern content shifts |

## Schema breaking-change semantics

| Change | Bump |
|---|---|
| Renaming a required field | Major |
| Adding a required field | Major |
| Removing a field (required or optional) | Major |
| Adding an optional field | Minor |
| Tightening a constraint (shorter maxLength, narrower enum) | Minor |
| Loosening a constraint (longer maxLength, wider enum) | Patch |
| Documentation-only changes | Patch |

When bumping the schema_version:

1. Update the `const` value in the schema (e.g., `"schema_version": { "type": "integer", "const": 2 }`).
2. Update existing fixtures, templates, the bundled example, and the apd-finding-schema skill.
3. Document the breaking change in `CHANGELOG.md`.
4. Consider whether old YAML records should be auto-migratable; if so, ship a migration script.

## Domain pack compatibility

Each pack declares a `framework_compat` semver range:

```yaml
framework_compat: ">=1.0.0,<2.0.0"
```

The validator refuses to build the apd-domain skill if the active framework version is outside the declared range. When the framework hits a major bump:

- Pack maintainers update `framework_compat` to include the new range.
- Existing packs continue working on the previous major version; users pin a specific framework version if needed.

## Framework version compatibility

The framework's external surface includes:

- The CLI command set and flag semantics.
- The schema files in `schemas/`.
- The plugin manifest format.
- The expected directory layout of a run.
- The expected frontmatter fields on context-brief and advisory-report.

Changes to any of these surfaces require a version bump. Internal refactors of `tools/apd_gauntlet/` modules don't.

## PyPI trusted publishing

The release workflow publishes to PyPI via trusted publishing. This requires a one-time setup:

1. Create the `apd-gauntlet` project on PyPI (manual; reserved by initial release).
2. In PyPI's "Publishing" tab, add a trusted publisher entry for the GitHub repo `shoveleejoe/apd-gauntlet`, workflow `release.yml`, environment unset.
3. Tag a release (`git tag v1.0.0 && git push origin v1.0.0`). The release workflow publishes automatically.

If trusted publishing isn't set up, the workflow's PyPI step fails; the GitHub Release still succeeds. Set up trusted publishing before the first tag.

## Deprecation policy

When a field or behavior is deprecated:

1. Add a deprecation note to the relevant skill or doc file. Cite the version in which removal will occur.
2. Keep the deprecated surface working through at least one minor release.
3. Remove in a major bump.

## v1.2.0 — Multi-framework taxonomy mappings (Phase A)

Additive within v1.x. Extensions:

- `finding.schema.json` gains optional `control_mappings.cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`.
- `capability.schema.json` gains optional `control_mappings.d3fend` (with required `counters_attack` cross-reference) AND optional `control_mappings.mitre_attack` (parallel to the field on findings; technique-level claims the capability defends against).
- `run-config.schema.json` gains optional `taxonomies` array.
- New schemas: `cwe-coverage`, `owasp-coverage`, `d3fend-coverage`.

PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 without changes.

## v1.3.0 — Methodology-aware threat-model evaluator (Phase B)

Additive within v1.x. Extensions:

- `finding.schema.json` — `agent` enum gains `threat_model_evaluator`;
  `id` pattern extended to accept `tmeval-<sha8>` prefix; same extension
  on `cross_references` and `merged_from` patterns.
- `run-config.schema.json` — accepts optional `threat_model: <path>` and
  `methodology_hint: <name>` fields. Methodology hint enum:
  stride / linddun / attack_tree / pasta / vast / trike / free_form.
- New: `threat-model-normalized.schema.json` (recon output).
- New: `threat-model-coverage.schema.json` (evaluator output).

Shared `$defs` extraction (Task B-4): `schemas/_defs.schema.json` holds
the canonical regex patterns for ATT&CK technique IDs, D3FEND IDs, and
CWE IDs. The four existing schemas (finding, capability, d3fend-coverage,
attack-exposure) `$ref` into `_defs.schema.json`. Validator builds a
jsonschema `Registry` so refs resolve. Behavior preserved (same patterns
enforced).

PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0
with no changes.

## v1.4.0 — Attack-path enumeration and D3FEND defense graph (Phase C)

(Coming after Phase B.)

## See also

- [Architecture](architecture.md)
- [Extending agents](extending-agents.md)
- [CONTRIBUTING](../CONTRIBUTING.md)
