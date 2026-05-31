# Domain-Improvement Capture & Draft (Subsystem B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture, on every gauntlet run, the typed and pack-attributed places where the selected domain pack(s) are incomplete (advisory `40-synthesis/domain-improvements.yaml`), and give the author an on-demand, deterministic `draft-domain-improvements` command that turns chosen opportunities into a validated, `git apply`-able patch against `domains/<pack>/` — never auto-applied, never auto-PR'd.

**Architecture:** Two clean halves. NOTICE (every run, advisory, non-blocking): a deterministic Python coverage-delta pre-pass writes candidate signals; a new `apd-domain-auditor` LLM agent reads those plus the settled corpus + merged `apd-domain` skill and emits one typed `domain-improvement` record set (each with a deterministic `dimpr-<sha8>` id computed by a new `compute_improvement_id` helper). ACT (on demand, pure Python): `draft-domain-improvements` inserts each chosen `draft_snippet` into a temp copy of `domains/`, gates it with `validate-domain` + `build-domain-skill`, drops failures, and emits a unified diff. The `dimpr-` prefix lives only in two new schemas; the finding schema is untouched.

**Tech Stack:** Python 3.11+ (Click CLI, jsonschema Draft 2020-12, PyYAML), pytest + click.testing.CliRunner, a plain-JS Workflow runner pinned by a text-contract test.

**Spec:** docs/superpowers/specs/2026-05-30-domain-improvement-capture-design.md

---

## File structure (locks the decomposition — read before any task)

**New files (created):**

| Path | One responsibility |
|---|---|
| `schemas/domain-improvement.schema.json` | The `domain-improvement` record schema: `dimpr-<sha8>` id, nine `improvement_type`s, `target_pack`/`target_file` enums, `evidence[]`, `draft_snippet`, the nine `apd_goal`↔`target_file` `allOf` branches for `missing_common_pattern`. (§4.1) |
| `schemas/domain-improvements-doc.schema.json` | The array-wrapper doc: self-describing envelope `schema_version`/`generated_by`/`examined_domains` + `improvements[]` with an absolute-`$id` `$ref` into the record schema. (§4.2) |
| `schemas/domain-coverage-delta-doc.schema.json` | The deterministic pre-pass output schema: `declared_union` + `candidates[]` (deterministic-three subset, `source: const deterministic`). (§5.1 step 8) |
| `tools/apd_gauntlet/synthesis/coverage_delta.py` | The deterministic `domain-coverage-delta` pre-pass: load packs + asset-inventory, compute crown-jewel/attacker-position/trust-boundary deltas, write `domain-coverage-delta.yaml`. (§5.1) |
| `tools/apd_gauntlet/synthesis/draft.py` | The on-demand `draft-domain-improvements` engine: select → temp-copy → per-snippet insert → validate/build gate → drop-on-fail → unified diff. (§6) |
| `.claude/agents/apd-domain-auditor.md` | The judgment-half LLM agent: materialize deterministic candidates, harvest judgment opportunities, draft snippets, compute ids, write the artifact; receipt-only. (§7) |
| `docs/improving-domain-packs.md` | The author triage guide (read → draft → review → `git apply` → re-validate). (§10) |
| `tests/test_domain_improvement_schema.py` | Valid/invalid fixtures for the record + doc + delta-doc schemas. (§12) |
| `tests/test_coverage_delta.py` | The deterministic pre-pass tests (all three candidate types, empty inventory, determinism). (§12) |
| `tests/test_domain_improvement_linter.py` | `compute_improvement_id` + `check_domain_improvement_id` byte-payload tests. (§12) |
| `tests/test_validate_domain_improvements.py` | Validate wiring + cross-file evidence-ref (incl. a `merged-<sha8>` ref resolved from `deduped-findings.yaml`) + id-recompute tests. (§12) |
| `tests/test_draft_domain_improvements.py` | The on-demand command: happy path, new-file (append-include + glob-covered), both drop-on-fail kinds, md structural branches, regulatory-anchor scalar + duplicate + shape, retarget EOF fallback, isolation, duplicate, unknown-pack, invalid-pack-name, no-op, determinism. (§12) |
| `tests/test_summary_domain_improvements.py` | The closeout summary line (N>0, N==0, absent-artifact). (§12) |
| `tests/test_lint_agent_apd_domain_auditor.py` | Frontmatter + whole-doc receipt-schema-conformance lint on the new agent. (§12) |
| `tests/test_doc_improving_domain_packs.py` | Pins the §10 pointer deliverable (guide exists + adapting doc links to it). |
| `tests/fixtures/valid/dimpr-*.yaml` | Valid record + doc + delta-doc fixtures. **Note the `dimpr-` prefix, NOT `domain-improvement-`:** `tests/test_other_schemas.py` globs `valid/domain-*.yaml` (and `invalid/domain-*.yaml`) against the *pack* `domain.schema.json`; any new `domain-*.yaml` fixture would be picked up by that pre-existing test and fail (the improvement record carries `id`/`improvement_type`/… that `domain.schema.json`'s `additionalProperties:false` rejects, and lacks the required pack keys). The `dimpr-` prefix dodges that glob entirely (§ Task 1 Step 8 gate). |
| `tests/fixtures/invalid/dimpr-*.yaml` | Invalid record/doc/delta-doc fixtures (bad id, bad enum, empty evidence, missing snippet, common_pattern mismatch, uppercase + traversal pack name, missing examined_domains). |
| `tests/fixtures/frozen-domains/<pack>/...` | A frozen copy of two packs for the golden-patch determinism pin (decoupled from live-pack drift, §6.6). |

**Modified files:**

| Path | Change |
|---|---|
| `tools/apd_gauntlet/linters.py` | Add `compute_improvement_id(...)` and `check_domain_improvement_id(record)`. (§7.4) |
| `tools/apd_gauntlet/validate.py` | Add the two new entries to `SYNTHESIS_ROLLUPS`; add `_validate_domain_improvements_cross_refs` called from `run_cross_file_pass`. (§4.3) |
| `tools/apd_gauntlet/cli.py` | Register `domain-coverage-delta` and `draft-domain-improvements` `@main.command`s. (§5.1/§6) |
| `tools/apd_gauntlet/summary.py` | `summarize_run` reads `domain-improvements.yaml` when present; `render_summary` emits the advisory line. (§9) |
| `.claude/workflows/apd-gauntlet.js` | Add `meta.phases` entries + the Phase 5h advisory phase pair (non-blocking). (§8) |
| `tests/test_workflow_apd_gauntlet.py` | Add the two phase names to `EXPECTED_PHASES` + `DIRECT_PHASE_LITERALS`; add the non-blocking/ordering pins. (§12) |
| `docs/adapting-to-other-domains.md` | Add an "Evolving a pack from gauntlet runs" pointer subsection. (§10) |

**Build order rationale:** schemas first (everything validates against them) → deterministic pre-pass (no LLM, fully testable) → validate wiring + cross-file validator → linter helpers → agent + lint → workflow phase + pins → on-demand draft command → summary closeout → docs → final full-suite gate. Each task leaves the full suite green and `mypy tools/` clean.

---

## Task 1: The three new schemas (record + doc-wrapper + delta-doc)

**Files:**
- Create: `schemas/domain-improvement.schema.json`
- Create: `schemas/domain-improvements-doc.schema.json`
- Create: `schemas/domain-coverage-delta-doc.schema.json`
- Create: `tests/test_domain_improvement_schema.py`
- Create: `tests/fixtures/valid/dimpr-record.yaml`, `tests/fixtures/valid/dimpr-common-pattern.yaml`, `tests/fixtures/valid/dimpr-nonrep-pattern.yaml`, `tests/fixtures/valid/dimpr-doc.yaml`, `tests/fixtures/valid/dimpr-doc-empty.yaml`, `tests/fixtures/valid/dimpr-coverage-delta-doc.yaml`
- Create: `tests/fixtures/invalid/dimpr-bad-id.yaml`, `tests/fixtures/invalid/dimpr-bad-type.yaml`, `tests/fixtures/invalid/dimpr-bad-target-file.yaml`, `tests/fixtures/invalid/dimpr-empty-evidence.yaml`, `tests/fixtures/invalid/dimpr-no-snippet.yaml`, `tests/fixtures/invalid/dimpr-common-pattern-no-goal.yaml`, `tests/fixtures/invalid/dimpr-common-pattern-mismatch.yaml`, `tests/fixtures/invalid/dimpr-bad-pack-traversal.yaml`, `tests/fixtures/invalid/dimpr-uppercase-pack.yaml`, `tests/fixtures/invalid/dimpr-doc-no-examined.yaml`, `tests/fixtures/invalid/dimpr-coverage-delta-doc-bad-genby.yaml`

**Naming note (CRITICAL, ordering — see Step 8 gate):** every new fixture uses the `dimpr-` prefix, **not** `domain-improvement-` / `domain-improvements-doc` / `domain-coverage-delta-doc`. The pre-existing `tests/test_other_schemas.py` discovers fixtures by globbing `valid/domain-*.yaml` and `invalid/domain-*.yaml` and validates each against the *pack* `domain.schema.json` (`additionalProperties:false`, required `[name, display_name, version, framework_compat, description, includes, regulatory_anchors]`). A `domain-improvement-*.yaml` valid fixture would be swept up by `test_other_schemas.py::test_valid_fixtures_pass[domain-…]` and FAIL the moment Task 1 commits — reddening the whole suite before any later task runs. The `dimpr-` prefix is outside that glob, so the two suites stay disjoint.

- [ ] **Step 1: Write the failing schema-fixture test**

**Precondition.** `jsonschema` (Draft 2020-12) and `referencing` are already project deps — `tools/apd_gauntlet/validate.py:12` does `from referencing import Registry, Resource`, and ~10 existing tests (e.g. `tests/test_other_schemas.py:11`) import the same. If `python3 -c 'import referencing, jsonschema'` fails on a fresh checkout, install them before starting, so the Step 2 red-state is a genuine "schema files / fixtures missing" collection error and not a spurious `ImportError` for a missing dep.

Create `tests/test_domain_improvement_schema.py`:

```python
"""Schema validation tests for the domain-improvement record + doc + delta-doc."""
from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
FIXTURES = REPO / "tests" / "fixtures"


def _build_registry() -> Registry:
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator(schema_name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / schema_name).read_text())
    return Draft202012Validator(schema, registry=_build_registry())


# (fixture file, schema file) for fixtures that MUST validate clean.
# All fixtures use the dimpr- prefix so they never collide with the domain-*.yaml
# glob in tests/test_other_schemas.py (which validates against the PACK schema).
VALID = [
    ("valid/dimpr-record.yaml", "domain-improvement.schema.json"),
    ("valid/dimpr-common-pattern.yaml", "domain-improvement.schema.json"),
    ("valid/dimpr-nonrep-pattern.yaml", "domain-improvement.schema.json"),
    ("valid/dimpr-doc.yaml", "domain-improvements-doc.schema.json"),
    ("valid/dimpr-doc-empty.yaml", "domain-improvements-doc.schema.json"),
    ("valid/dimpr-coverage-delta-doc.yaml", "domain-coverage-delta-doc.schema.json"),
]

# (fixture file, schema file) for fixtures that MUST be rejected.
INVALID = [
    ("invalid/dimpr-bad-id.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-bad-type.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-bad-target-file.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-empty-evidence.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-no-snippet.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-common-pattern-no-goal.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-common-pattern-mismatch.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-bad-pack-traversal.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-uppercase-pack.yaml", "domain-improvement.schema.json"),
    ("invalid/dimpr-doc-no-examined.yaml", "domain-improvements-doc.schema.json"),
    ("invalid/dimpr-coverage-delta-doc-bad-genby.yaml", "domain-coverage-delta-doc.schema.json"),
]


@pytest.mark.parametrize(("fixture", "schema"), VALID)
def test_valid_fixtures_pass(fixture, schema):
    errors = list(_validator(schema).iter_errors(yaml.safe_load((FIXTURES / fixture).read_text())))
    assert errors == [], f"Unexpected errors in {fixture}: {[e.message for e in errors]}"


@pytest.mark.parametrize(("fixture", "schema"), INVALID)
def test_invalid_fixtures_rejected(fixture, schema):
    errors = list(_validator(schema).iter_errors(yaml.safe_load((FIXTURES / fixture).read_text())))
    assert errors, f"Expected {fixture} to be rejected by {schema}, but it validated clean"


def test_doc_ref_resolves_record_schema():
    """A doc with one real record exercises the absolute-$id $ref into the record schema."""
    doc = yaml.safe_load((FIXTURES / "valid/dimpr-doc.yaml").read_text())
    assert doc["improvements"], "doc fixture must carry >=1 record to exercise the $ref"
    errors = list(_validator("domain-improvements-doc.schema.json").iter_errors(doc))
    assert errors == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_domain_improvement_schema.py -q`
Expected: errors/collection failures — the three schema files and the fixtures do not exist yet.

- [ ] **Step 3: Create `schemas/domain-improvement.schema.json`**

Copy the §4.1 record schema verbatim into `schemas/domain-improvement.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvement.schema.json",
  "title": "APD Gauntlet Domain-Improvement Opportunity",
  "type": "object",
  "required": [
    "id", "improvement_type", "target_pack", "target_file",
    "source", "priority", "evidence", "rationale",
    "suggested_action", "draft_snippet"
  ],
  "additionalProperties": false,
  "properties": {
    "id": { "type": "string", "pattern": "^dimpr-[0-9a-f]{8}$" },
    "improvement_type": {
      "type": "string",
      "enum": [
        "missing_crown_jewel",
        "missing_attacker_position",
        "missing_trust_boundary",
        "missing_severity_clause",
        "missing_consequential_action",
        "missing_immutability_class",
        "missing_data_class",
        "missing_regulatory_anchor",
        "missing_common_pattern"
      ]
    },
    "target_pack": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
    "target_file": {
      "type": "string",
      "enum": [
        "domain.yaml",
        "severity-rubric.md",
        "consequential-actions.md",
        "immutability-classes.md",
        "data-taxonomy.md",
        "common-patterns/confidentiality.md",
        "common-patterns/integrity.md",
        "common-patterns/availability.md",
        "common-patterns/distributed.md",
        "common-patterns/resilient.md",
        "common-patterns/ephemeral.md",
        "common-patterns/authenticity.md",
        "common-patterns/non-repudiation.md",
        "common-patterns/immutability.md"
      ]
    },
    "apd_goal": {
      "type": "string",
      "enum": [
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability"
      ]
    },
    "source": { "type": "string", "enum": ["deterministic", "judgment"] },
    "priority": { "type": "string", "enum": ["high", "medium", "low"] },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["kind", "ref"],
        "additionalProperties": false,
        "properties": {
          "kind": { "type": "string", "enum": ["finding", "asset_inventory"] },
          "ref": { "type": "string", "minLength": 1 },
          "note": { "type": "string", "minLength": 1, "maxLength": 280 }
        }
      }
    },
    "rationale": { "type": "string", "minLength": 20 },
    "suggested_action": { "type": "string", "minLength": 10 },
    "draft_snippet": { "type": "string", "minLength": 1 },
    "insertion_hint": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "yaml_path": { "type": "string", "minLength": 1 },
        "markdown_section": {
          "type": "object",
          "additionalProperties": false,
          "required": ["level", "text"],
          "properties": {
            "level": { "type": "integer", "minimum": 1, "maximum": 6 },
            "text": { "type": "string", "minLength": 1 }
          }
        }
      }
    }
  },
  "allOf": [
    {
      "comment": "missing_common_pattern requires apd_goal so the target_file goal is named.",
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" } } },
      "then": { "required": ["apd_goal"] }
    },
    {
      "comment": "missing_common_pattern: apd_goal must match the common-patterns/<goal>.md target_file. apd_goal uses underscores (non_repudiation); the filename uses hyphens (non-repudiation.md). Each branch pins one goal const to its hyphenated file const.",
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "confidentiality" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/confidentiality.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "integrity" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/integrity.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "availability" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/availability.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "distributed" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/distributed.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "resilient" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/resilient.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "ephemeral" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/ephemeral.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "authenticity" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/authenticity.md" } } }
    },
    {
      "comment": "non_repudiation (underscore) -> non-repudiation.md (hyphen).",
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "non_repudiation" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/non-repudiation.md" } } }
    },
    {
      "if": { "properties": { "improvement_type": { "const": "missing_common_pattern" }, "apd_goal": { "const": "immutability" } }, "required": ["apd_goal"] },
      "then": { "properties": { "target_file": { "const": "common-patterns/immutability.md" } } }
    }
  ]
}
```

- [ ] **Step 4: Create `schemas/domain-improvements-doc.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvements-doc.schema.json",
  "title": "APD Gauntlet Domain-Improvements Document",
  "type": "object",
  "required": ["schema_version", "generated_by", "examined_domains", "improvements"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["domain-auditor"] },
    "examined_domains": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" }
    },
    "improvements": {
      "type": "array",
      "items": { "$ref": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-improvement.schema.json" }
    }
  }
}
```

- [ ] **Step 5: Create `schemas/domain-coverage-delta-doc.schema.json`** (per §5.1 step 8)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/domain-coverage-delta-doc.schema.json",
  "title": "APD Gauntlet Domain Coverage-Delta Document",
  "type": "object",
  "required": ["schema_version", "generated_by", "examined_domains", "declared_union", "candidates"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by": { "type": "string", "enum": ["coverage-delta"] },
    "examined_domains": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" }
    },
    "declared_union": {
      "type": "object",
      "additionalProperties": false,
      "required": ["crown_jewels", "attacker_positions", "trust_boundaries"],
      "properties": {
        "crown_jewels": { "type": "array", "items": { "type": "string" } },
        "attacker_positions": { "type": "array", "items": { "type": "string" } },
        "trust_boundaries": { "type": "array", "items": { "type": "string" } }
      }
    },
    "candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["improvement_type", "source", "default_target_pack", "evidence"],
        "properties": {
          "improvement_type": {
            "type": "string",
            "enum": ["missing_crown_jewel", "missing_attacker_position", "missing_trust_boundary"]
          },
          "source": { "type": "string", "const": "deterministic" },
          "default_target_pack": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
          "priority": { "type": "string", "enum": ["high", "medium", "low"] },
          "asset_name": { "type": "string" },
          "data_classifications": { "type": "array", "items": { "type": "string" } },
          "crosses": { "type": "array", "items": { "type": "string" } },
          "evidence": {
            "type": "array",
            "minItems": 1,
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["kind", "ref"],
              "properties": {
                "kind": { "type": "string", "const": "asset_inventory" },
                "ref": { "type": "string", "minLength": 1 }
              }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 6: Create the valid fixtures**

`tests/fixtures/valid/dimpr-record.yaml` (a deterministic crown-jewel record; `id` is a placeholder hex — schema only checks the `dimpr-[0-9a-f]{8}` pattern, not the hash, which Task 4's linter test pins separately):

```yaml
id: dimpr-1a2b3c4d
improvement_type: missing_crown_jewel
target_pack: api-security
target_file: domain.yaml
source: deterministic
priority: high
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
    note: "asset-inventory locator inputs/design.md#payments (context only)"
rationale: "The run exercised a payment-methods data store that no selected pack declares as a crown jewel."
suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
draft_snippet: |
  - pattern: payment_methods_store
    description: "PCI-scope cardholder data store grounded in the run's asset inventory."
insertion_hint:
  yaml_path: crown_jewels
```

`tests/fixtures/valid/dimpr-common-pattern.yaml`:

```yaml
id: dimpr-2b3c4d5e
improvement_type: missing_common_pattern
apd_goal: confidentiality
target_pack: pbm
target_file: common-patterns/confidentiality.md
source: judgment
priority: medium
evidence:
  - kind: finding
    ref: conf-9f8e7d6c
rationale: "A recurring field-level-encryption confidentiality pattern is absent from the pbm pattern library."
suggested_action: "add a field-level encryption pattern to pbm/common-patterns/confidentiality.md"
draft_snippet: |
  ### Field-level envelope encryption for PHI columns
  When PHI lives beside non-PHI in the same table, encrypt at the column level.
insertion_hint:
  markdown_section:
    level: 1
    text: "Confidentiality patterns"
```

`tests/fixtures/valid/dimpr-nonrep-pattern.yaml` (the underscore→hyphen case that must PASS):

```yaml
id: dimpr-3c4d5e6f
improvement_type: missing_common_pattern
apd_goal: non_repudiation
target_pack: pbm
target_file: common-patterns/non-repudiation.md
source: judgment
priority: low
evidence:
  - kind: finding
    ref: nonrep-11223344
rationale: "A signed-audit-event pattern recurs but is absent from the non-repudiation pattern library."
suggested_action: "add a signed audit-event pattern to pbm/common-patterns/non-repudiation.md"
draft_snippet: |
  ### Signed, append-only consequential-action events
  Sign each consequential-action record with a per-tenant key.
```

`tests/fixtures/valid/dimpr-doc.yaml` (non-empty — exercises the `$ref`):

```yaml
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
  - api-security
improvements:
  - id: dimpr-1a2b3c4d
    improvement_type: missing_crown_jewel
    target_pack: api-security
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence:
      - kind: asset_inventory
        ref: asset-1a2b3c4d
    rationale: "The run exercised a payment-methods data store no selected pack declares."
    suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
    draft_snippet: |
      - pattern: payment_methods_store
        description: "PCI-scope cardholder data store grounded in the run's asset inventory."
```

`tests/fixtures/valid/dimpr-doc-empty.yaml`:

```yaml
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements: []
```

`tests/fixtures/valid/dimpr-coverage-delta-doc.yaml`:

```yaml
schema_version: 1
generated_by: coverage-delta
examined_domains:
  - api-security
declared_union:
  crown_jewels:
    - audit_log_store
  attacker_positions:
    - unauthenticated_internet
  trust_boundaries:
    - public_internet_to_edge
candidates:
  - improvement_type: missing_crown_jewel
    source: deterministic
    default_target_pack: api-security
    priority: high
    asset_name: payment_methods_store
    data_classifications:
      - pci
    evidence:
      - kind: asset_inventory
        ref: asset-1a2b3c4d
```

- [ ] **Step 7: Create the invalid fixtures**

Each fixture below is given as a **complete verbatim body** so no hand-merging from a sibling is required.

`tests/fixtures/invalid/dimpr-bad-id.yaml` — id violates `^dimpr-[0-9a-f]{8}$` (`XYZ` non-hex, wrong length); the only thing that fails is the id:

```yaml
id: dimpr-XYZ
improvement_type: missing_crown_jewel
target_pack: api-security
target_file: domain.yaml
source: deterministic
priority: high
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
rationale: "The run exercised a payment-methods data store no selected pack declares."
suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
draft_snippet: "- pattern: payment_methods_store\n  description: \"x\""
```

`tests/fixtures/invalid/dimpr-bad-type.yaml` — copy `tests/fixtures/valid/dimpr-record.yaml` verbatim and change **only** the `improvement_type:` line to `missing_widget`; leave `id: dimpr-1a2b3c4d` and every other line untouched so **exactly one** keyword (the enum) fails:

```yaml
id: dimpr-1a2b3c4d
improvement_type: missing_widget
target_pack: api-security
target_file: domain.yaml
source: deterministic
priority: high
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
    note: "asset-inventory locator inputs/design.md#payments (context only)"
rationale: "The run exercised a payment-methods data store that no selected pack declares as a crown jewel."
suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
draft_snippet: |
  - pattern: payment_methods_store
    description: "PCI-scope cardholder data store grounded in the run's asset inventory."
insertion_hint:
  yaml_path: crown_jewels
```

`tests/fixtures/invalid/dimpr-bad-target-file.yaml` — copy `dimpr-record.yaml` and change **only** the `target_file:` line to `README.md` (not in the enum):

```yaml
id: dimpr-1a2b3c4d
improvement_type: missing_crown_jewel
target_pack: api-security
target_file: README.md
source: deterministic
priority: high
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
rationale: "The run exercised a payment-methods data store that no selected pack declares as a crown jewel."
suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
draft_snippet: |
  - pattern: payment_methods_store
    description: "PCI-scope cardholder data store grounded in the run's asset inventory."
```

`tests/fixtures/invalid/dimpr-empty-evidence.yaml` — copy `dimpr-record.yaml` and replace the `evidence:` block with `evidence: []` (violates `minItems: 1`); everything else valid:

```yaml
id: dimpr-1a2b3c4d
improvement_type: missing_crown_jewel
target_pack: api-security
target_file: domain.yaml
source: deterministic
priority: high
evidence: []
rationale: "The run exercised a payment-methods data store that no selected pack declares as a crown jewel."
suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
draft_snippet: |
  - pattern: payment_methods_store
    description: "PCI-scope cardholder data store grounded in the run's asset inventory."
```

`tests/fixtures/invalid/dimpr-no-snippet.yaml` — copy `dimpr-record.yaml` and **omit `draft_snippet` entirely** (violates `required`); everything else valid:

```yaml
id: dimpr-1a2b3c4d
improvement_type: missing_crown_jewel
target_pack: api-security
target_file: domain.yaml
source: deterministic
priority: high
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
rationale: "The run exercised a payment-methods data store that no selected pack declares as a crown jewel."
suggested_action: "add a payment_methods_store crown jewel to api-security/domain.yaml"
```

`tests/fixtures/invalid/dimpr-common-pattern-no-goal.yaml`:

```yaml
id: dimpr-4d5e6f70
improvement_type: missing_common_pattern
target_pack: pbm
target_file: common-patterns/confidentiality.md
source: judgment
priority: low
evidence:
  - kind: finding
    ref: conf-9f8e7d6c
rationale: "A pattern is absent from the pbm pattern library but apd_goal is omitted."
suggested_action: "add a confidentiality pattern to pbm/common-patterns/confidentiality.md"
draft_snippet: "### x\ny"
```

`tests/fixtures/invalid/dimpr-common-pattern-mismatch.yaml` — `apd_goal: confidentiality` but `target_file: common-patterns/integrity.md` (rejected by the per-goal `allOf` branch):

```yaml
id: dimpr-5e6f7081
improvement_type: missing_common_pattern
apd_goal: confidentiality
target_pack: pbm
target_file: common-patterns/integrity.md
source: judgment
priority: low
evidence:
  - kind: finding
    ref: conf-9f8e7d6c
rationale: "apd_goal confidentiality contradicts the integrity target_file."
suggested_action: "add a confidentiality pattern to the wrong file (should be rejected)"
draft_snippet: "### x\ny"
```

`tests/fixtures/invalid/dimpr-bad-pack-traversal.yaml` — `target_pack: '../x'` (path-safety, §12 path-safety negative test; rejected by `^[a-z][a-z0-9-]*$`):

```yaml
id: dimpr-60718293
improvement_type: missing_crown_jewel
target_pack: "../x"
target_file: domain.yaml
source: deterministic
priority: medium
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
rationale: "A traversal pack name must never reach the draft.py path builder."
suggested_action: "this record must be rejected at schema time"
draft_snippet: "- pattern: x\n  description: \"escaping pack name\""
```

`tests/fixtures/invalid/dimpr-uppercase-pack.yaml` — `target_pack: PBM` (uppercase; the second §12 path-safety case, a non-traversal `^[a-z][a-z0-9-]*$` violation called out verbatim in the spec):

```yaml
id: dimpr-71829304
improvement_type: missing_crown_jewel
target_pack: PBM
target_file: domain.yaml
source: deterministic
priority: medium
evidence:
  - kind: asset_inventory
    ref: asset-1a2b3c4d
rationale: "An upper-case pack name must never reach the draft.py path builder."
suggested_action: "this record must be rejected at schema time"
draft_snippet: "- pattern: x\n  description: \"upper-case pack name\""
```

`tests/fixtures/invalid/dimpr-doc-no-examined.yaml` — doc omitting the now-required `examined_domains`:

```yaml
schema_version: 1
generated_by: domain-auditor
improvements: []
```

`tests/fixtures/invalid/dimpr-coverage-delta-doc-bad-genby.yaml` — `generated_by: synthesizer` (not `coverage-delta`):

```yaml
schema_version: 1
generated_by: synthesizer
examined_domains:
  - pbm
declared_union:
  crown_jewels: []
  attacker_positions: []
  trust_boundaries: []
candidates: []
```

- [ ] **Step 8: Run the schema tests + the collision-guard test + mypy**

Run: `python3 -m pytest tests/test_domain_improvement_schema.py -q`
Expected: PASS (all valid validate clean; all invalid rejected; `$ref` resolves).
Run: `python3 -m pytest tests/test_other_schemas.py -q`
Expected: PASS — **this is the collision gate.** Because the new fixtures use the `dimpr-` prefix (not `domain-*`), `test_other_schemas.py`'s `valid/domain-*.yaml` / `invalid/domain-*.yaml` globs do not pick them up, so this pre-existing suite stays green. If a fixture were accidentally named `domain-improvement-*.yaml`, this command would go RED here (catching the collision at Task 1, not at Task 12).
Run: `python3 -m mypy tools/`
Expected: Success (no Python changed this task; sanity gate).

- [ ] **Step 9: Commit**

```bash
git add schemas/domain-improvement.schema.json schemas/domain-improvements-doc.schema.json schemas/domain-coverage-delta-doc.schema.json tests/test_domain_improvement_schema.py tests/fixtures/valid tests/fixtures/invalid
git commit -m "feat(schema): add domain-improvement record + doc + coverage-delta-doc schemas"
```

---

## Task 2: Deterministic `domain-coverage-delta` pre-pass + CLI

**Files:**
- Create: `tools/apd_gauntlet/synthesis/coverage_delta.py`
- Modify: `tools/apd_gauntlet/cli.py` (register `domain-coverage-delta` after `rollup_cmd`, ~line 1008)
- Create: `tests/test_coverage_delta.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_coverage_delta.py`:

```python
"""Tests for the deterministic domain-coverage-delta pre-pass (§5.1)."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.synthesis.coverage_delta import build_coverage_delta
from click.testing import CliRunner

DOMAINS = pathlib.Path("domains")


def _run_dir(tmp_path, inventory_yaml: str, domains_list):
    run_dir = tmp_path / "run"
    (run_dir / "00-context").mkdir(parents=True)
    (run_dir / "40-synthesis").mkdir(parents=True)
    domains_block = "domains:\n" + "".join(f"  - {d}\n" for d in domains_list)
    (run_dir / ".apd-run.yaml").write_text(
        f"run_id: test\n{domains_block}framework_version: 1.5.0\n", encoding="utf-8"
    )
    (run_dir / "00-context" / "asset-inventory.yaml").write_text(inventory_yaml, encoding="utf-8")
    return run_dir


_INV_CROWN_JEWEL = """\
schema_version: 1
generated_by: intake
assets:
  - asset_id: asset-1a2b3c4d
    name: novel_widget_store
    asset_type: data_store
    data_classifications: [pci]
    provenance:
      source: artifact
      locator: inputs/design.md#widgets
    confidence: high
  - asset_id: asset-2b3c4d5e
    name: pack_default_store
    asset_type: data_store
    provenance:
      source: domain_default
    confidence: medium
identities: []
trust_boundaries: []
"""


def test_crown_jewel_delta_emits_one_candidate(tmp_path):
    run_dir = _run_dir(tmp_path, _INV_CROWN_JEWEL, ["api-security", "pbm"])
    result = build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    assert doc["generated_by"] == "coverage-delta"
    assert doc["examined_domains"] == ["api-security", "pbm"]
    cj = [c for c in doc["candidates"] if c["improvement_type"] == "missing_crown_jewel"]
    assert len(cj) == 1
    c = cj[0]
    assert c["source"] == "deterministic"
    assert c["priority"] == "high"
    assert c["default_target_pack"] == "api-security"
    assert c["evidence"][0] == {"kind": "asset_inventory", "ref": "asset-1a2b3c4d"}
    # The domain_default asset emits no candidate.
    assert all(c.get("asset_name") != "pack_default_store" for c in doc["candidates"])
    # The build returns the same path the CLI writes.
    assert result == run_dir / "40-synthesis" / "domain-coverage-delta.yaml"


def test_attacker_position_and_trust_boundary_candidates(tmp_path):
    inv = """\
schema_version: 1
generated_by: intake
assets:
  - asset_id: asset-aaaaaaaa
    name: ext_dep
    asset_type: external_dependency
    provenance: { source: artifact }
    confidence: high
  - asset_id: asset-bbbbbbbb
    name: core_svc
    asset_type: service
    provenance: { source: artifact }
    confidence: high
identities:
  - identity_id: idn-cccccccc
    name: partner_portal
    identity_type: external_party
    provenance: { source: artifact }
    confidence: high
trust_boundaries:
  - boundary_id: tb-dddddddd
    name: novel_partner_to_core
    crosses: [asset-aaaaaaaa, asset-bbbbbbbb]
    provenance: { source: artifact }
"""
    run_dir = _run_dir(tmp_path, inv, ["api-security"])
    build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    pos = [c for c in doc["candidates"] if c["improvement_type"] == "missing_attacker_position"]
    bnd = [c for c in doc["candidates"] if c["improvement_type"] == "missing_trust_boundary"]
    assert pos and pos[0]["evidence"][0]["ref"] == "idn-cccccccc"
    assert pos[0]["source"] == "deterministic"
    assert bnd and bnd[0]["evidence"][0]["ref"] == "tb-dddddddd"
    assert bnd[0]["source"] == "deterministic"


def test_empty_inventory_emits_empty_candidates(tmp_path):
    inv = "schema_version: 1\ngenerated_by: intake\nassets: []\nidentities: []\ntrust_boundaries: []\n"
    run_dir = _run_dir(tmp_path, inv, ["pbm"])
    build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    assert doc["candidates"] == []
    assert doc["examined_domains"] == ["pbm"]


def test_missing_inventory_emits_empty_candidates(tmp_path):
    run_dir = tmp_path / "run"
    (run_dir / "00-context").mkdir(parents=True)
    (run_dir / "40-synthesis").mkdir(parents=True)
    (run_dir / ".apd-run.yaml").write_text(
        "run_id: t\ndomains:\n  - pbm\nframework_version: 1.5.0\n", encoding="utf-8"
    )
    build_coverage_delta(run_dir, DOMAINS)
    doc = yaml.safe_load((run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text())
    assert doc["candidates"] == []


def test_output_byte_stable(tmp_path):
    run_dir = _run_dir(tmp_path, _INV_CROWN_JEWEL, ["api-security", "pbm"])
    build_coverage_delta(run_dir, DOMAINS)
    first = (run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text()
    build_coverage_delta(run_dir, DOMAINS)
    second = (run_dir / "40-synthesis" / "domain-coverage-delta.yaml").read_text()
    assert first == second


def test_cli_registered_and_runs(tmp_path):
    run_dir = _run_dir(tmp_path, _INV_CROWN_JEWEL, ["api-security"])
    result = CliRunner().invoke(main, ["domain-coverage-delta", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert (run_dir / "40-synthesis" / "domain-coverage-delta.yaml").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_coverage_delta.py -q`
Expected: ImportError — `apd_gauntlet.synthesis.coverage_delta` does not exist.

- [ ] **Step 3: Create `tools/apd_gauntlet/synthesis/coverage_delta.py`**

```python
"""Deterministic domain-coverage-delta pre-pass (Subsystem B, spec §5.1).

Pure Python, no LLM. Computes mechanical coverage deltas between the run's
asset-inventory and the union of the selected packs' declarations, and writes
``40-synthesis/domain-coverage-delta.yaml`` — the candidate-signal file the
``apd-domain-auditor`` agent reads. Candidate signals only: no snippets, no
``dimpr-`` ids, no ``domain-improvements.yaml``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_NONALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    """Lowercase, non-alphanumeric -> '_', collapse repeats, strip edges."""
    return _NONALNUM.sub("_", str(text).lower()).strip("_")


def _load_pack(domains_dir: Path, name: str) -> dict[str, Any]:
    meta_path = domains_dir / name / "domain.yaml"
    if not meta_path.exists():
        return {}
    data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _declared_union(domains_dir: Path, domains: list[str]) -> dict[str, set[str]]:
    union: dict[str, set[str]] = {
        "crown_jewels": set(),
        "attacker_positions": set(),
        "trust_boundaries": set(),
    }
    specs = [
        ("crown_jewels", "pattern", "crown_jewels"),
        ("attacker_positions", "position", "attacker_positions"),
        ("default_trust_boundaries", "boundary", "trust_boundaries"),
    ]
    for name in domains:
        meta = _load_pack(domains_dir, name)
        for field, key, bucket in specs:
            for item in meta.get(field, []) or []:
                if isinstance(item, dict) and item.get(key):
                    union[bucket].add(_normalize(item[key]))
    return union


def _candidates(
    inventory: dict[str, Any],
    union: dict[str, set[str]],
    primary_pack: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Crown-jewel delta: artifact/threat_model/code_evidence assets only.
    for asset in inventory.get("assets", []) or []:
        if not isinstance(asset, dict):
            continue
        prov = (asset.get("provenance") or {}).get("source")
        if prov == "domain_default":
            continue
        key = _normalize(asset.get("name", ""))
        if not key or key in union["crown_jewels"]:
            continue
        cand: dict[str, Any] = {
            "improvement_type": "missing_crown_jewel",
            "source": "deterministic",
            "default_target_pack": primary_pack,
            "priority": "high" if prov == "artifact" else "medium",
            "asset_name": asset.get("name", ""),
            "evidence": [{"kind": "asset_inventory", "ref": asset["asset_id"]}],
        }
        classes = asset.get("data_classifications")
        if classes:
            cand["data_classifications"] = list(classes)
        out.append(cand)
    # Attacker-position delta: non-domain_default identities (external_party).
    for ident in inventory.get("identities", []) or []:
        if not isinstance(ident, dict):
            continue
        if (ident.get("provenance") or {}).get("source") == "domain_default":
            continue
        if ident.get("identity_type") != "external_party":
            continue
        key = _normalize("external_" + str(ident.get("name", "")))
        if key in union["attacker_positions"]:
            continue
        out.append({
            "improvement_type": "missing_attacker_position",
            "source": "deterministic",
            "default_target_pack": primary_pack,
            "priority": "medium",
            "asset_name": ident.get("name", ""),
            "evidence": [{"kind": "asset_inventory", "ref": ident["identity_id"]}],
        })
    # Trust-boundary delta: non-domain_default boundaries.
    for bnd in inventory.get("trust_boundaries", []) or []:
        if not isinstance(bnd, dict):
            continue
        if (bnd.get("provenance") or {}).get("source") == "domain_default":
            continue
        key = _normalize(bnd.get("name", ""))
        if not key or key in union["trust_boundaries"]:
            continue
        out.append({
            "improvement_type": "missing_trust_boundary",
            "source": "deterministic",
            "default_target_pack": primary_pack,
            "priority": "medium",
            "asset_name": bnd.get("name", ""),
            "crosses": list(bnd.get("crosses", []) or []),
            "evidence": [{"kind": "asset_inventory", "ref": bnd["boundary_id"]}],
        })
    return out


def build_coverage_delta(run_dir: Path, domains_dir: Path) -> Path:
    """Compute the coverage delta and write domain-coverage-delta.yaml. Returns
    the written path. Best-effort: a missing/empty inventory yields empty
    candidates and exits cleanly."""
    run_cfg_path = run_dir / ".apd-run.yaml"
    run_cfg: dict[str, Any] = (
        yaml.safe_load(run_cfg_path.read_text(encoding="utf-8")) or {}
        if run_cfg_path.exists()
        else {}
    )
    domains: list[str] = [str(d) for d in (run_cfg.get("domains") or [])]
    primary_pack = domains[0] if domains else ""

    inv_path = run_dir / "00-context" / "asset-inventory.yaml"
    inventory: dict[str, Any] = (
        yaml.safe_load(inv_path.read_text(encoding="utf-8")) or {}
        if inv_path.exists()
        else {}
    )

    union = _declared_union(domains_dir, domains)
    candidates = _candidates(inventory, union, primary_pack)

    doc = {
        "schema_version": 1,
        "generated_by": "coverage-delta",
        "examined_domains": domains,
        "declared_union": {
            "crown_jewels": sorted(union["crown_jewels"]),
            "attacker_positions": sorted(union["attacker_positions"]),
            "trust_boundaries": sorted(union["trust_boundaries"]),
        },
        "candidates": candidates,
    }
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True, exist_ok=True)
    out_path = synth / "domain-coverage-delta.yaml"
    out_path.write_text(
        yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out_path
```

- [ ] **Step 4: Register the CLI command**

In `tools/apd_gauntlet/cli.py`, add after `rollup_cmd` (after the block ending ~line 1008, before `audit_report_cmd`):

```python
@main.command("domain-coverage-delta")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("domains"),
)
def domain_coverage_delta_cmd(run_dir: Path, domains_dir: Path) -> None:
    """5h-i: deterministic coverage-delta pre-pass; emit domain-coverage-delta.yaml."""
    from .synthesis.coverage_delta import build_coverage_delta

    path = build_coverage_delta(run_dir, domains_dir)
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    click.echo(f"domain-coverage-delta: wrote {len(doc.get('candidates') or [])} candidates")
```

- [ ] **Step 5: Run the tests + mypy**

Run: `python3 -m pytest tests/test_coverage_delta.py -q`
Expected: PASS.
Run: `python3 -m mypy tools/`
Expected: Success.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/coverage_delta.py tools/apd_gauntlet/cli.py tests/test_coverage_delta.py
git commit -m "feat(synthesis): deterministic domain-coverage-delta pre-pass + CLI"
```

---

## Task 3: Wire `domain-coverage-delta.yaml` + `domain-improvements.yaml` into `SYNTHESIS_ROLLUPS`

**Files:**
- Modify: `tools/apd_gauntlet/validate.py:103-133` (the `SYNTHESIS_ROLLUPS` dict)
- Create: `tests/test_validate_domain_improvements.py` (this task adds only the schema-wiring tests; the cross-file tests come in Task 5)

- [ ] **Step 1: Write the failing wiring test**

Create `tests/test_validate_domain_improvements.py`:

```python
"""Validate-wiring tests for the domain-improvements + coverage-delta artifacts."""
from __future__ import annotations

import pathlib

from apd_gauntlet.validate import SYNTHESIS_ROLLUPS, run_schema_pass

REPO = pathlib.Path(__file__).parent.parent


def _run_with(tmp_path, **synth_files: str) -> pathlib.Path:
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    synth.mkdir(parents=True)
    for name, text in synth_files.items():
        (synth / name).write_text(text, encoding="utf-8")
    return run_dir


def test_rollups_dict_has_both_new_entries():
    assert SYNTHESIS_ROLLUPS["domain-improvements.yaml"] == "domain-improvements-doc.schema.json"
    assert SYNTHESIS_ROLLUPS["domain-coverage-delta.yaml"] == "domain-coverage-delta-doc.schema.json"


_GOOD_DOC = """\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: dimpr-1a2b3c4d
    improvement_type: missing_crown_jewel
    target_pack: pbm
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence:
      - kind: asset_inventory
        ref: asset-1a2b3c4d
    rationale: "The run exercised a data store no selected pack declares."
    suggested_action: "add a crown jewel to pbm/domain.yaml"
    draft_snippet: |
      - pattern: novel_store
        description: "A store grounded in the run inventory."
"""

_BAD_DOC = """\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: dimpr-BADID
    improvement_type: not_a_type
    target_pack: pbm
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence: []
    rationale: short
    suggested_action: short
    draft_snippet: ""
"""


def test_schema_pass_accepts_good_improvements_doc(tmp_path):
    run_dir = _run_with(tmp_path, **{"domain-improvements.yaml": _GOOD_DOC})
    report = run_schema_pass(run_dir)
    assert report.is_clean, report.render()


def test_schema_pass_rejects_bad_improvements_doc(tmp_path):
    run_dir = _run_with(tmp_path, **{"domain-improvements.yaml": _BAD_DOC})
    report = run_schema_pass(run_dir)
    assert not report.is_clean
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_validate_domain_improvements.py -q`
Expected: FAIL — the two keys are not in `SYNTHESIS_ROLLUPS` yet; `_GOOD_DOC` is not validated and `_BAD_DOC` is not rejected.

- [ ] **Step 3: Add the two entries to `SYNTHESIS_ROLLUPS`**

In `tools/apd_gauntlet/validate.py`, inside the `SYNTHESIS_ROLLUPS` dict, after the `"contradictions.yaml": "contradictions-doc.schema.json",` line, add:

```python
    # Subsystem B — domain-improvement capture artifacts. The doc wrapper's
    # improvements[].items.$ref is the absolute $id of domain-improvement.schema.json,
    # which build_registry() indexes, so each record validates against the record
    # schema with no further wiring. Neither file is a *.findings.yaml, so neither
    # enters _iter_records / the semantic pass / cross-file finding-id resolution.
    "domain-coverage-delta.yaml":  "domain-coverage-delta-doc.schema.json",
    "domain-improvements.yaml":    "domain-improvements-doc.schema.json",
```

- [ ] **Step 4: Run the tests + mypy**

Run: `python3 -m pytest tests/test_validate_domain_improvements.py -q`
Expected: PASS.
Run: `python3 -m mypy tools/`
Expected: Success.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tests/test_validate_domain_improvements.py
git commit -m "feat(validate): wire domain-improvements + coverage-delta into SYNTHESIS_ROLLUPS"
```

---

## Task 4: The `compute_improvement_id` + `check_domain_improvement_id` linters

**Files:**
- Modify: `tools/apd_gauntlet/linters.py` (add two functions after `compute_id`, ~line 22)
- Create: `tests/test_domain_improvement_linter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_domain_improvement_linter.py`:

```python
"""Tests for compute_improvement_id + check_domain_improvement_id (§4.1 / §7.4)."""
from __future__ import annotations

import hashlib

from apd_gauntlet.linters import check_domain_improvement_id, compute_improvement_id


def _expected(itype, pack, tfile, ref):
    key = "|".join([itype, pack, tfile, ref]).lower()
    return "dimpr-" + hashlib.sha256(key.encode()).hexdigest()[:8]


def test_compute_improvement_id_matches_verbatim_payload():
    got = compute_improvement_id(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d"
    )
    assert got == _expected("missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d")


def test_compute_improvement_id_is_not_compute_id():
    """It does NOT reuse compute_id's (prefix, title, locator) 2-field payload."""
    from apd_gauntlet.linters import compute_id

    a = compute_improvement_id("missing_crown_jewel", "pbm", "domain.yaml", "asset-1a2b3c4d")
    b = compute_id("dimpr", "missing_crown_jewel", "asset-1a2b3c4d")
    assert a != b


def test_compute_improvement_id_lowercases_key():
    lower = compute_improvement_id("missing_crown_jewel", "pbm", "domain.yaml", "asset-1A2B")
    same = compute_improvement_id("missing_crown_jewel", "pbm", "domain.yaml", "asset-1a2b")
    assert lower == same


def _record(itype="missing_crown_jewel", pack="api-security",
            tfile="domain.yaml", ref="asset-1a2b3c4d", rid=None):
    rid = rid or compute_improvement_id(itype, pack, tfile, ref)
    return {
        "id": rid,
        "improvement_type": itype,
        "target_pack": pack,
        "target_file": tfile,
        "evidence": [{"kind": "asset_inventory", "ref": ref}],
    }


def test_check_passes_on_matching_id():
    assert check_domain_improvement_id(_record()) == []


def test_check_flags_mismatched_id():
    rec = _record(rid="dimpr-deadbeef")
    msgs = check_domain_improvement_id(rec)
    assert msgs and "id mismatch" in msgs[0]


def test_check_uses_first_evidence_ref():
    rec = _record()
    rec["evidence"].insert(0, {"kind": "finding", "ref": "conf-00000000"})
    # id was computed from the (now-second) asset ref, so prepending a finding
    # ref makes primary_ref the finding ref -> mismatch.
    assert check_domain_improvement_id(rec)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_domain_improvement_linter.py -q`
Expected: ImportError — neither function exists.

- [ ] **Step 3: Add the two functions to `linters.py`**

In `tools/apd_gauntlet/linters.py`, immediately after `compute_id` (after line 22), add:

```python
def compute_improvement_id(
    improvement_type: str,
    target_pack: str,
    target_file: str,
    primary_ref: str,
) -> str:
    """Deterministic dimpr- id (§4.1). NOT compute_id: the key is the LOWERCASED,
    '|'-joined 4-tuple improvement_type|target_pack|target_file|evidence[0].ref,
    sha256[:8], 'dimpr-' prefix. The agent (§7.2 step 5) and the linter below both
    call this, so the at-capture id and the recomputed id are guaranteed to agree.
    """
    key = "|".join([improvement_type, target_pack, target_file, primary_ref]).lower()
    digest = hashlib.sha256(key.encode()).hexdigest()[:8]
    return f"dimpr-{digest}"


def check_domain_improvement_id(record: dict[str, Any]) -> list[str]:
    """Recompute the dimpr-<sha8> via compute_improvement_id and flag a mismatch.

    NOT a mirror of check_finding_id (which early-returns unless record['agent']
    is in _PREFIX_BY_AGENT — improvement records carry no 'agent' field). The
    primary ref is ALWAYS evidence[0].ref.
    """
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    primary_ref = evidence[0].get("ref", "")
    expected = compute_improvement_id(
        record.get("improvement_type", ""),
        record.get("target_pack", ""),
        record.get("target_file", ""),
        primary_ref,
    )
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per dimpr- deterministic rule"]
    return []
```

- [ ] **Step 4: Run the tests + mypy**

Run: `python3 -m pytest tests/test_domain_improvement_linter.py -q`
Expected: PASS.
Run: `python3 -m mypy tools/`
Expected: Success.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/linters.py tests/test_domain_improvement_linter.py
git commit -m "feat(linters): compute_improvement_id + check_domain_improvement_id"
```

---

## Task 5: Cross-file validator — `_validate_domain_improvements_cross_refs`

**Files:**
- Modify: `tools/apd_gauntlet/validate.py` (add `_validate_domain_improvements_cross_refs`; call it from `run_cross_file_pass` near the `_validate_report_data_cross_refs(run_dir, report)` line ~486)
- Modify: `tests/test_validate_domain_improvements.py` (add the cross-file tests)

- [ ] **Step 1: Write the failing cross-file tests**

Append to `tests/test_validate_domain_improvements.py`:

```python
from apd_gauntlet.validate import run_cross_file_pass


def _run_with_corpus(tmp_path, improvements_doc: str, *, inventory: str, findings: str | None = None):
    run_dir = tmp_path / "run"
    synth = run_dir / "40-synthesis"
    ctx = run_dir / "00-context"
    synth.mkdir(parents=True)
    ctx.mkdir(parents=True)
    (synth / "domain-improvements.yaml").write_text(improvements_doc, encoding="utf-8")
    (ctx / "asset-inventory.yaml").write_text(inventory, encoding="utf-8")
    if findings is not None:
        (synth / "deduped-findings.yaml").write_text(findings, encoding="utf-8")
    return run_dir


_INV = """\
schema_version: 1
generated_by: intake
assets:
  - asset_id: asset-1a2b3c4d
    name: novel_store
    asset_type: data_store
    provenance: { source: artifact }
    confidence: high
identities: []
trust_boundaries: []
"""


def _doc_with_ref(itype, pack, tfile, kind, ref):
    from apd_gauntlet.linters import compute_improvement_id
    rid = compute_improvement_id(itype, pack, tfile, ref)
    return f"""\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: {rid}
    improvement_type: {itype}
    target_pack: {pack}
    target_file: {tfile}
    source: deterministic
    priority: high
    evidence:
      - kind: {kind}
        ref: {ref}
    rationale: "The run exercised something no selected pack declares fully."
    suggested_action: "add the missing item to the pack"
    draft_snippet: |
      - pattern: novel_store
        description: "grounded in the run inventory"
"""


def test_cross_file_accepts_resolving_asset_ref(tmp_path):
    doc = _doc_with_ref("missing_crown_jewel", "pbm", "domain.yaml", "asset_inventory", "asset-1a2b3c4d")
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV)
    report = run_cross_file_pass(run_dir)
    assert report.is_clean, report.render()


def test_cross_file_rejects_dangling_asset_ref(tmp_path):
    doc = _doc_with_ref("missing_crown_jewel", "pbm", "domain.yaml", "asset_inventory", "asset-deadbeef")
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV)
    report = run_cross_file_pass(run_dir)
    assert not report.is_clean
    assert any("asset-deadbeef" in v.message for v in report.errors)


def test_cross_file_rejects_dangling_finding_ref(tmp_path):
    doc = _doc_with_ref("missing_severity_clause", "pbm", "severity-rubric.md", "finding", "conf-deadbeef")
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV, findings="finding: []\n")
    report = run_cross_file_pass(run_dir)
    assert not report.is_clean
    assert any("conf-deadbeef" in v.message for v in report.errors)


def test_cross_file_recomputes_dimpr_id(tmp_path):
    tampered = """\
schema_version: 1
generated_by: domain-auditor
examined_domains:
  - pbm
improvements:
  - id: dimpr-deadbeef
    improvement_type: missing_crown_jewel
    target_pack: pbm
    target_file: domain.yaml
    source: deterministic
    priority: high
    evidence:
      - kind: asset_inventory
        ref: asset-1a2b3c4d
    rationale: "The id below does not match the deterministic recomputation."
    suggested_action: "add the missing item to the pack"
    draft_snippet: |
      - pattern: novel_store
        description: "grounded in the run inventory"
"""
    run_dir = _run_with_corpus(tmp_path, tampered, inventory=_INV)
    report = run_cross_file_pass(run_dir)
    assert not report.is_clean
    assert any("id mismatch" in v.message for v in report.errors)


def test_cross_file_resolves_merged_finding_ref_from_deduped(tmp_path):
    """A merged-<sha8> id lives ONLY in 40-synthesis/deduped-findings.yaml (the
    decomposed apply path writes no merged.findings.yaml), which does NOT match the
    *.findings.yaml glob _iter_records walks. The validator must union in the
    deduped-findings corpus, else a legitimate merged-* evidence ref false-positives
    as 'not found in run corpus'. This pins that union (§4.3 / Issue: merged-* refs)."""
    doc = _doc_with_ref(
        "missing_severity_clause", "pbm", "severity-rubric.md", "finding", "merged-44bdb663"
    )
    deduped = """\
finding:
  - id: merged-44bdb663
    schema_version: 1
"""
    run_dir = _run_with_corpus(tmp_path, doc, inventory=_INV, findings=None)
    (run_dir / "40-synthesis" / "deduped-findings.yaml").write_text(deduped, encoding="utf-8")
    report = run_cross_file_pass(run_dir)
    assert report.is_clean, report.render()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_validate_domain_improvements.py -q`
Expected: FAIL — the cross-file pass does not yet walk `domain-improvements.yaml`.

- [ ] **Step 3: Add `_validate_domain_improvements_cross_refs`**

In `tools/apd_gauntlet/validate.py`, add the import `from . import linters` is already present. Add this function immediately after `_validate_report_data_cross_refs` (after line 358):

```python
def _validate_domain_improvements_cross_refs(
    run_dir: pathlib.Path,
    report: ValidationReport,
) -> None:
    """Subsystem B (§4.3): resolve every domain-improvement evidence[].ref and
    recompute each dimpr- id. This is the ONE pass that walks the improvements
    doc — it is not a *.findings.yaml, so it never enters _iter_records / the
    semantic pass. Both checks live here.
    """
    path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    if not path.exists():
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return  # the schema pass already complained

    # Real finding ids in the SETTLED corpus the agent actually reads. Two sources,
    # unioned:
    #   (a) _iter_records — globs *.findings.yaml (the per-lens / attack-path /
    #       (legacy) merged.findings.yaml files), the synthesizer-fallback path.
    #   (b) 40-synthesis/deduped-findings.yaml (root key 'finding') — the DEDUPED
    #       corpus. Its filename does NOT match the *.findings.yaml glob, so
    #       _iter_records never sees it; yet a multi-member cluster minted by
    #       apply.py gets a 'merged-<sha8>' id that exists ONLY here in a decomposed
    #       run (the decomposed apply path writes no merged.findings.yaml). The
    #       auditor legitimately cites such a merged-* id as evidence, so it must
    #       resolve. Union (b) in so a real merged-* ref is not a false positive.
    finding_ids: set[str] = set()
    for _p, kind, rec in _iter_records(run_dir):
        if "_parse_error" in rec or "id" not in rec:
            continue
        if kind == "finding":
            finding_ids.add(rec["id"])
    deduped_path = run_dir / "40-synthesis" / "deduped-findings.yaml"
    if deduped_path.exists():
        try:
            deduped = yaml.safe_load(deduped_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            deduped = {}
        for rec in deduped.get("finding") or []:
            if isinstance(rec, dict) and rec.get("id"):
                finding_ids.add(rec["id"])

    # Real asset/identity/boundary ids in the inventory.
    inv_path = run_dir / "00-context" / "asset-inventory.yaml"
    inventory_ids: set[str] = set()
    if inv_path.exists():
        try:
            inv = yaml.safe_load(inv_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            inv = {}
        for a in inv.get("assets") or []:
            if isinstance(a, dict) and a.get("asset_id"):
                inventory_ids.add(a["asset_id"])
        for i in inv.get("identities") or []:
            if isinstance(i, dict) and i.get("identity_id"):
                inventory_ids.add(i["identity_id"])
        for b in inv.get("trust_boundaries") or []:
            if isinstance(b, dict) and b.get("boundary_id"):
                inventory_ids.add(b["boundary_id"])

    for imp in data.get("improvements") or []:
        if not isinstance(imp, dict):
            continue
        rid = imp.get("id")
        for j, ev in enumerate(imp.get("evidence") or []):
            kind = ev.get("kind")
            ref = ev.get("ref")
            if kind == "finding" and ref not in finding_ids:
                report.errors.append(Violation(
                    path, rid,
                    f"evidence[{j}].ref {ref!r} (kind: finding) not found in run corpus",
                ))
            elif kind == "asset_inventory" and ref not in inventory_ids:
                report.errors.append(Violation(
                    path, rid,
                    f"evidence[{j}].ref {ref!r} (kind: asset_inventory) not found in "
                    "00-context/asset-inventory.yaml",
                ))
        for msg in linters.check_domain_improvement_id(imp):
            report.errors.append(Violation(path, rid, msg))
```

Then, in `run_cross_file_pass`, immediately after the existing line `    _validate_report_data_cross_refs(run_dir, report)` (line 486), add:

```python
    _validate_domain_improvements_cross_refs(run_dir, report)
```

- [ ] **Step 4: Run the tests + mypy + full suite spot-check**

Run: `python3 -m pytest tests/test_validate_domain_improvements.py -q`
Expected: PASS.
Run: `python3 -m mypy tools/`
Expected: Success.
Run: `python3 -m pytest tests/test_validate_schema_pass.py tests/test_cli_rollup.py -q`
Expected: PASS (no regression in existing validate flows).

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tests/test_validate_domain_improvements.py
git commit -m "feat(validate): cross-file evidence-ref + dimpr-id check for domain-improvements"
```

---

## Task 6: The `apd-domain-auditor` agent + lint test

**Files:**
- Create: `.claude/agents/apd-domain-auditor.md`
- Create: `tests/test_lint_agent_apd_domain_auditor.py`

- [ ] **Step 1: Write the failing lint/contract test**

Create `tests/test_lint_agent_apd_domain_auditor.py`:

```python
"""Frontmatter + receipt-schema-conformance lint for the apd-domain-auditor agent (§7, §12)."""
from __future__ import annotations

import json
import pathlib
import re

import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
AGENT = REPO / ".claude" / "agents" / "apd-domain-auditor.md"
RECEIPT_SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _meta_and_body():
    text = AGENT.read_text(encoding="utf-8")
    m = FRONTMATTER.match(text)
    assert m, "apd-domain-auditor.md must start with a YAML frontmatter block"
    return yaml.safe_load(m.group(1)), text


def test_agent_file_exists():
    assert AGENT.is_file()


def test_frontmatter_fields_present():
    meta, _ = _meta_and_body()
    assert meta.get("name") == "apd-domain-auditor"
    assert meta.get("description")
    assert meta.get("tools")
    assert meta.get("model")


def test_required_reading_paths_resolve():
    """Every backticked `.claude/...md` reference ANYWHERE in the body must resolve
    (this scans the whole file, not just the Required-reading section). The body
    cites `.claude/skills/apd-domain/SKILL.md` in Inputs — that path is committed
    (verified: `git ls-files` tracks it, not gitignored), so it resolves at lint
    time. Keep all `.claude/...md` paths exact."""
    _, text = _meta_and_body()
    for ref in re.findall(r"`(\.claude/[^`]+\.md)`", text):
        assert (REPO / ref).exists(), f"required reading target not found: {ref}"


def test_documented_receipt_conforms_to_schema():
    """§12: the agent's documented final message CONFORMS TO agent-receipt.schema.json
    (status enum, outputs[].schema_valid, advisory counts: {}). Extract the fenced
    YAML receipt block under '## Final message', safe_load it, and validate it against
    the real schema — a string grep cannot catch a drifted key / missing required
    field. The documented block uses a single concrete `status: ok` so it is loadable."""
    _, text = _meta_and_body()
    after = text.split("## Final message", 1)
    assert len(after) == 2, "missing '## Final message' receipt section"
    m = re.search(r"```ya?ml\n(.*?)\n```", after[1], re.DOTALL)
    assert m, "receipt section must contain a fenced ```yaml block"
    receipt = yaml.safe_load(m.group(1))
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(receipt))
    assert errors == [], [e.message for e in errors]
    # And pin the B-specific receipt content.
    assert receipt["agent"] == "apd-domain-auditor"
    assert receipt["status"] == "ok"
    assert receipt["counts"] == {}
    assert any(
        o["path"] == "40-synthesis/domain-improvements.yaml" and o["schema_valid"] is True
        for o in receipt["outputs"]
    )


def test_lint_agents_dir_passes_on_new_agent():
    from apd_gauntlet.lint_agents import lint_agent_file
    errors = lint_agent_file(AGENT, REPO)
    assert errors == [], errors
```

For the schema-conformance test to `yaml.safe_load` the receipt block cleanly, the documented receipt in Step 3 uses a **single concrete `status: ok`** (not the enum-style `status: ok | blocked | error`, which `safe_load` would read as the string `"ok | blocked | error"` — not in the enum). The Step 3 agent body below is written that way; an inline comment documents that all three statuses are valid.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_lint_agent_apd_domain_auditor.py -q`
Expected: FAIL — the agent file does not exist.

- [ ] **Step 3: Create `.claude/agents/apd-domain-auditor.md`**

**Path-resolution caveat (load-bearing).** `test_required_reading_paths_resolve` scans the **whole** agent body (not just the Required-reading section) for every backticked `` `.claude/…md` `` reference and asserts each resolves on disk. This body cites three: `.claude/skills/apd-framework/SKILL.md` and `.claude/skills/apd-evidence-discipline/SKILL.md` (Required reading) and `.claude/skills/apd-domain/SKILL.md` (Inputs). **All three are committed** — `git ls-files .claude/skills/apd-domain/SKILL.md` returns the path and `git check-ignore` does not match it, so the build-generated `apd-domain` skill is present in a clean checkout and the lint test passes. Keep these three `.claude/…md` paths byte-exact; do **not** add any new backticked `.claude/…md` reference that does not resolve. (The two `target_file` references inside the nine-types table — e.g. `severity-rubric.md`, `common-patterns/<goal>.md` — are not `.claude/…` paths and are correctly skipped by the regex.)

```markdown
---
name: apd-domain-auditor
description: |
  Subsystem-B capture agent (advisory, non-blocking). The judgment half of
  domain-improvement capture: reads the deterministic coverage-delta candidates,
  the settled deduped corpus, the merged apd-domain skill, and the asset
  inventory; materializes the deterministic candidates into full
  domain-improvement records, harvests prose-judgment opportunities, drafts a
  paste-ready draft_snippet for each, computes the dimpr- id, and writes ONE
  artifact 40-synthesis/domain-improvements.yaml. It NEVER edits a pack, never
  opens a PR, and never gates the run. Distinct from apd-report-auditor (which is
  report-faithfulness only and must not be extended).
tools:
  - Read
  - Glob
  - Grep
  - Write
model: opus
---

# apd-domain-auditor

## Required reading

- `.claude/skills/apd-framework/SKILL.md`
- `.claude/skills/apd-evidence-discipline/SKILL.md`

The evidence-pointer and block-on-ambiguity discipline applies here too: never
invent an evidence ref. Cite a real finding id or a real asset/identity/boundary
id, exactly as a specialist agent must.

## Job

Capture domain-improvement opportunities for this run — the typed, pack-attributed
places where the selected pack(s) are incomplete. Two sources feed one artifact:
the deterministic pre-pass candidates and your own prose judgment.

## Inputs

- `40-synthesis/domain-coverage-delta.yaml` — the deterministic candidate signals
  (crown-jewel / attacker-position / trust-boundary deltas). If this file is
  ABSENT or empty, treat it as zero deterministic candidates — never an error.
- `40-synthesis/deduped-findings.yaml` — the settled, deduped corpus (incl.
  apath-* / tmeval-*), read for the judgment signals below.
- `.claude/skills/apd-domain/SKILL.md` — the merged pack content. Use the per-pack
  `## Domain: <pack> — Source: <file>` headers to (a) perform the union check (an
  opportunity is real only if no pack's section already covers it) and (b) attribute
  each opportunity to its best-fit `target_pack`.
- `00-context/asset-inventory.yaml` — to ground asset-derived evidence refs and
  resolve the deterministic candidates' asset/identity/boundary ids.
- The run's `.apd-run.yaml` `domains` list — populate `examined_domains` from this
  (always available even with no delta), and use `domains[0]` as the primary/first
  default `target_pack`.

## The nine improvement types

| improvement_type | mechanism | target_file |
|---|---|---|
| missing_crown_jewel | deterministic | domain.yaml (crown_jewels) |
| missing_attacker_position | deterministic | domain.yaml (attacker_positions) |
| missing_trust_boundary | deterministic | domain.yaml (default_trust_boundaries) |
| missing_severity_clause | judgment | severity-rubric.md |
| missing_consequential_action | judgment | consequential-actions.md |
| missing_immutability_class | judgment | immutability-classes.md |
| missing_data_class | judgment | data-taxonomy.md |
| missing_regulatory_anchor | judgment | domain.yaml (regulatory_anchors) |
| missing_common_pattern | judgment | common-patterns/<goal>.md |

Only `missing_common_pattern` has its `target_file` **pinned by schema** (the nine
per-goal `allOf` branches in `domain-improvement.schema.json`, §4.1). The other eight
types' `target_file` is **advisory/conventional**: the schema's `target_file` enum
admits every value but does not bind it to `improvement_type`, and the routing is
enforced only by `draft.py`'s `_YAML_PATH_BY_TYPE` (Task 9). Treat the table's other
eight rows as the agreed convention, not a schema constraint.

Judgment signals in the deduped corpus: a finding whose `detail` records "matched
no severity-rubric clause in any selected pack" (missing_severity_clause); a
`nonrep-*` finding noting an audit-worthy action "not enumerated"
(missing_consequential_action); an `immut-*` finding noting a data class "not
addressed" (missing_immutability_class); an intake/confidentiality finding noting
data "not enumerated" (missing_data_class); a finding citing a regulatory regime no
pack lists (missing_regulatory_anchor); a recurring per-`apd_goal` finding pattern
absent from the pattern library (missing_common_pattern).

## Behavior

1. **Materialize deterministic candidates.** For each candidate in the delta file,
   build a full `domain-improvement` record: carry `improvement_type`, `target_pack`
   (= `default_target_pack` unless your domain-fit judgment reassigns it),
   `target_file`, `evidence` (the asset-inventory ref the pre-pass supplied); write a
   `rationale` (≥20 chars) + `suggested_action` (≥10 chars); draft a `draft_snippet`.
   `source` STAYS `deterministic` even if you substantially rephrase the text.
2. **Harvest judgment opportunities.** Scan the deduped corpus for the six judgment
   signals. For each genuine gap (verified absent from the merged skill — union
   check), emit a record with `source: judgment`, `evidence` citing the REAL finding
   id(s) that revealed it, the best-fit `target_pack`, and a drafted `draft_snippet`.
3. **Draft every draft_snippet at capture time** (judgment runs ONCE). Snippet shapes:
   - domain.yaml crown jewel: a YAML list item
     `- pattern: <key>\n  description: "<≥10 chars>"` ready to append under `crown_jewels`.
   - domain.yaml attacker position / trust boundary: `- position:` / `- boundary:` items
     with `description` (≥10 chars).
   - domain.yaml regulatory anchor: a single quoted string list item.
   - severity-rubric.md: a `- **<Harm>** — <impact clause>` bullet, with the tier named
     in the level-qualified `insertion_hint.markdown_section` (e.g. `{level: 2, text: "High"}`).
   - consequential-actions.md: a `- <action>` bullet under the right `## <category>` section.
   - immutability-classes.md / data-taxonomy.md: the file's clause/row shape.
   - common-patterns/<goal>.md: a pattern block in that file's house format.
   Each snippet must be schema/build-valid in isolation (`domain.schema.json` requires
   `description` minLength 10, `pattern` non-empty), so it passes the on-demand validate gate.
   For exactly ONE crown_jewels/attacker_positions/trust_boundaries item per record:
   the on-demand command rejects a snippet that loads to a list or a scalar.
4. **Compute the dimpr- id** per the deterministic rule: the LOWERCASED, `|`-joined
   4-tuple `improvement_type|target_pack|target_file|evidence[0].ref`, sha256[:8],
   `dimpr-` prefix. Dedup identical opportunities (same id) across the deterministic
   and judgment halves — keep one, prefer `source: deterministic`.
5. **apd_goal for missing_common_pattern.** `apd_goal` is REQUIRED for
   missing_common_pattern and must match the `common-patterns/<goal>.md` target_file.
   `non_repudiation` (the apd_goal value) maps to the file `common-patterns/non-repudiation.md`.
6. **Write** `40-synthesis/domain-improvements.yaml` (the doc wrapper). When there are
   no opportunities, write the empty-but-valid artifact:
   `{schema_version: 1, generated_by: domain-auditor, examined_domains: [...], improvements: []}`.
7. **Self-check before returning:** every `evidence[].ref` resolves to a real finding
   id or a real asset/identity/boundary id; every `target_pack` is in `examined_domains`;
   every `draft_snippet` is non-empty. Block (status `blocked`) rather than invent if a
   candidate's evidence cannot be grounded.

## Outputs

- `40-synthesis/domain-improvements.yaml` (doc wrapper, schema
  `domain-improvements-doc.schema.json`).

## Final message (receipt only)

Your final message back to the run driver is a **receipt, not prose**. Return only a
compact object conforming to `schemas/agent-receipt.schema.json`. `status` is one of
`ok` | `blocked` | `error`; the example below shows the success case verbatim:

```yaml
agent: apd-domain-auditor
status: ok           # one of: ok | blocked | error
outputs:
  - path: 40-synthesis/domain-improvements.yaml
    schema_valid: true
counts: {}           # advisory; no findings_by_severity. Optionally blocked: N.
errors: []           # populate only on status: error
```

An empty-but-valid artifact still returns `status: ok`. This phase is ADVISORY — it
never gates the run. The driver retains only this receipt.
```

- [ ] **Step 4: Run the lint test + the repo-wide agent lint + mypy**

Run: `python3 -m pytest tests/test_lint_agent_apd_domain_auditor.py tests/test_lint_agents.py -q`
Expected: PASS (the new agent lints clean; the repo-wide lint still in `(0, 1)`).
Run: `python3 -m mypy tools/`
Expected: Success.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-domain-auditor.md tests/test_lint_agent_apd_domain_auditor.py
git commit -m "feat(agents): add apd-domain-auditor capture agent + lint contract"
```

---

## Task 7: Workflow advisory Phase 5h + the structural pins

**Files:**
- Modify: `.claude/workflows/apd-gauntlet.js` (meta.phases + the Phase 5h block between the 5g audit loop and `phase('closeout')`)
- Modify: `tests/test_workflow_apd_gauntlet.py` (`EXPECTED_PHASES`, `DIRECT_PHASE_LITERALS`, new pins)

- [ ] **Step 1: Write the failing pins**

In `tests/test_workflow_apd_gauntlet.py`, **append** `"domain-coverage-delta", "domain-improvements"` to BOTH `EXPECTED_PHASES` and `DIRECT_PHASE_LITERALS`. Position within each list is irrelevant: the union check at `test_every_meta_phase_is_emitted_one_way_or_the_other` (line ~100) is pure set-equality, and the per-name `assert … in found` / `assert f"phase('{p}')" in text` checks are order-independent. **The real lists end with `…"tmeval", "apath", "closeout",`** (tmeval/apath moved before closeout in a prior refactor — do NOT look for a `synthesis-audit`-then-`closeout` adjacency, it does not exist). Concretely, change the closing lines of each list:

`EXPECTED_PHASES` (lines ~33-35):
```python
    "synthesis-report", "synthesis-build", "synthesis-audit",
    "tmeval", "apath",
    "domain-coverage-delta", "domain-improvements", "closeout",
```

`DIRECT_PHASE_LITERALS` (lines ~42-44):
```python
    "synthesis-report", "synthesis-build", "synthesis-audit",
    "tmeval", "apath",
    "domain-coverage-delta", "domain-improvements", "closeout",
```

(Both new names are emitted via direct `phase('…')` literals, not via `runTier`, so they go in `DIRECT_PHASE_LITERALS` too; `TIER_PHASES_VIA_RUNTIER` is unchanged.) Then add new test functions:

```python
def test_phase_5h_names_in_meta_and_body() -> None:
    text = _text()
    for p in ("domain-coverage-delta", "domain-improvements"):
        assert f"phase('{p}')" in text, f"phase('{p}') not invoked in body"


def test_phase_5h_is_after_audit_and_before_closeout() -> None:
    text = _text()
    i_audit = text.index("phase('synthesis-audit')")
    i_delta = text.index("phase('domain-coverage-delta')")
    i_imp = text.index("phase('domain-improvements')")
    i_closeout = text.index("phase('closeout')")
    assert i_audit < i_delta < i_imp < i_closeout


def test_domain_auditor_dispatch_is_non_blocking() -> None:
    """The apd-domain-auditor llmStep must NOT be wrapped in a HALT (throw)."""
    text = _text()
    assert "llmStep('apd-domain-auditor'" in text
    # Bound a window from the domain-improvements phase to closeout and assert no throw.
    window = text[text.index("phase('domain-improvements')"):text.index("phase('closeout')")]
    assert "throw" not in window, "Phase 5h must be advisory / non-blocking (no throw)"


def test_domain_auditor_resolves_to_agent_file() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    assert "apd-domain-auditor" in referenced
    assert (AGENTS_DIR / "apd-domain-auditor.md").is_file()


def test_report_path_unchanged_by_5h() -> None:
    """B does not touch the report path: the 5g audit loop literal still present."""
    text = _text()
    assert "i <= 2" in text  # audit loop cap unchanged
    assert "report-data" in text  # report path still wired
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_workflow_apd_gauntlet.py -k "5h or domain_auditor or report_path_unchanged or meta_phase or expected_phase" -q`
Expected: FAIL — the phases and dispatch do not exist in the runner yet.

- [ ] **Step 3: Add the meta.phases entries**

In `.claude/workflows/apd-gauntlet.js`, in the `meta.phases` array, change the line:

```javascript
    'synthesis-report', 'synthesis-build', 'synthesis-audit',
    'closeout',
```
to:
```javascript
    'synthesis-report', 'synthesis-build', 'synthesis-audit',
    'domain-coverage-delta', 'domain-improvements',
    'closeout',
```

- [ ] **Step 4: Insert the Phase 5h block before `phase('closeout')`**

In `.claude/workflows/apd-gauntlet.js`, immediately before the `// PHASE 6 — closeout.` comment block and its `phase('closeout');` line (~line 571), insert:

```javascript
// ===========================================================================
// PHASE 5h — domain-improvement capture (Subsystem B). ADVISORY / NON-BLOCKING.
// Runs AFTER the 5g audit loop and BEFORE closeout, over the SETTLED corpus.
// Never gates the run, never touches the HTML report. Empty-but-valid artifact
// when there are no opportunities. Neither step is wrapped in isErr()/throw.
// ===========================================================================
phase('domain-coverage-delta');
// 5h-i — deterministic coverage-delta pre-pass (Python). Best-effort: a failure
// here does NOT halt the run; the agent can still harvest judgment opportunities.
pyStep('domain-coverage-delta', {
  phase: 'domain-coverage-delta', label: 'domain-coverage-delta',
  outputs: runDir + '/40-synthesis/domain-coverage-delta.yaml' });

phase('domain-improvements');
// 5h-ii — apd-domain-auditor (LLM) reads the delta + settled findings + the merged
// apd-domain skill + asset-inventory; writes domain-improvements.yaml. Advisory:
// NOT wrapped in isErr()/HALT; a single best-effort dispatch, and the run proceeds
// to closeout regardless of its status.
llmStep('apd-domain-auditor',
  'Capture domain-improvement opportunities for this run. Read ' +
  '40-synthesis/domain-coverage-delta.yaml + 40-synthesis/deduped-findings.yaml + ' +
  '.claude/skills/apd-domain/SKILL.md + 00-context/asset-inventory.yaml; emit ' +
  '40-synthesis/domain-improvements.yaml (an empty-but-valid {schema_version:1, ' +
  'generated_by:domain-auditor, examined_domains:[...], improvements:[]} when there ' +
  'are no opportunities). ADVISORY — this never gates the run.',
  { phase: 'domain-improvements', label: 'domain-auditor',
    validateScope: runDir + '/40-synthesis',
    outputs: runDir + '/40-synthesis/domain-improvements.yaml' });

```

- [ ] **Step 5: Run the full workflow contract test + mypy**

Run: `python3 -m pytest tests/test_workflow_apd_gauntlet.py -q`
Expected: PASS (the three existing union/coverage tests now pass because both lists carry the new names, and the new pins pass).
Run: `python3 -m mypy tools/`
Expected: Success (no Python changed; sanity gate).

- [ ] **Step 6: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tests/test_workflow_apd_gauntlet.py
git commit -m "feat(workflow): advisory Phase 5h domain-improvement capture (non-blocking)"
```

---

## Task 8: Frozen fixture packs for the on-demand draft tests

**Files:**
- Create: `tests/fixtures/frozen-domains/api-security/domain.yaml`, `.../severity-rubric.md`, `.../consequential-actions.md`, `.../immutability-classes.md`, `.../data-taxonomy.md`, and `.../common-patterns/{confidentiality,integrity}.md`
- Create: `tests/fixtures/frozen-domains/pbm/domain.yaml` (minimal second pack so `build-domain-skill <both>` is exercised; uses a `common-patterns/*.md` glob include to exercise the `_ensure_include_glob` covered branch), `.../pbm/severity-rubric.md`, `.../pbm/common-patterns/integrity.md`

The frozen pack decouples the golden-patch determinism pin from live `domains/` drift (§6.6). Keep it minimal but `domain.schema.json`-valid and `build-domain-skill`-buildable. It deliberately OMITS `common-patterns/availability.md` so the new-file test (Task 9) can target it.

- [ ] **Step 1: Create `tests/fixtures/frozen-domains/api-security/domain.yaml`**

```yaml
name: api-security
display_name: "Frozen API Security (test fixture)"
version: 1.0.0
framework_compat: ">=1.0.0,<2.0.0"
description: "Frozen api-security pack used only for draft-domain-improvements golden tests."
includes:
  - severity-rubric.md
  - consequential-actions.md
  - immutability-classes.md
  - data-taxonomy.md
  - common-patterns/confidentiality.md
  - common-patterns/integrity.md
regulatory_anchors:
  - "OWASP API Top 10 (2023)"
crown_jewels:
  - pattern: audit_log_store
    description: "Security and consequential-action event log for the API tier."
attacker_positions:
  - position: unauthenticated_internet
    description: "Untrusted external client with no credentials and no prior foothold."
default_trust_boundaries:
  - boundary: public_internet_to_edge
    description: "First crossing from untrusted client to the edge tier."
```

- [ ] **Step 2: Create the five `.md` files** (each with at least one H2 heading so the level-aware insertion has an anchor)

`tests/fixtures/frozen-domains/api-security/severity-rubric.md`:

```markdown
# Frozen API Security Severity Rubric

## Critical

- Catastrophic API harm clause.

## High

- Serious API harm clause.
```

`tests/fixtures/frozen-domains/api-security/consequential-actions.md`:

```markdown
# Frozen consequential-action surface

## Authentication events

- Login success and failure.
```

`tests/fixtures/frozen-domains/api-security/immutability-classes.md`:

```markdown
# Frozen immutability classes

## Append-only

- Audit log entries.
```

`tests/fixtures/frozen-domains/api-security/data-taxonomy.md`:

```markdown
# Frozen data taxonomy

## PII

- Email, name, address.
```

`tests/fixtures/frozen-domains/api-security/common-patterns/confidentiality.md`:

```markdown
# Confidentiality patterns (frozen)

## Encryption at rest

Illustrative pattern.
```

`tests/fixtures/frozen-domains/api-security/common-patterns/integrity.md`:

```markdown
# Integrity patterns (frozen)

## Input validation

Illustrative pattern.
```

- [ ] **Step 3: Create `tests/fixtures/frozen-domains/pbm/domain.yaml`** (minimal, with its own single include)

```yaml
name: pbm
display_name: "Frozen PBM (test fixture)"
version: 1.0.0
framework_compat: ">=1.0.0,<2.0.0"
description: "Frozen pbm pack used only for draft-domain-improvements golden tests."
includes:
  - severity-rubric.md
  - common-patterns/*.md
regulatory_anchors: []
crown_jewels:
  - pattern: phi_store
    description: "PHI store for the PBM tier."
```

**Note the `common-patterns/*.md` glob include in pbm** (api-security lists its
common-patterns files individually instead). This deliberate asymmetry lets Task 9
exercise BOTH branches of `_ensure_include_glob`: api-security exercises the
append-the-include branch (a new `common-patterns/<goal>.md` is not yet covered, so
`domain.yaml` is edited), and pbm exercises the `covered` short-circuit (the glob
already covers any new `common-patterns/*.md`, so **no** `domain.yaml` edit is needed).

`tests/fixtures/frozen-domains/pbm/severity-rubric.md`:

```markdown
# Frozen PBM Severity Rubric

## High

- Serious PBM harm clause.
```

`tests/fixtures/frozen-domains/pbm/common-patterns/integrity.md` (so the
`common-patterns/*.md` glob resolves to at least one file at build time; pbm
deliberately omits `availability.md` so the Task 9 glob-covered new-file test can
target it):

```markdown
# Integrity patterns (frozen pbm)

## Input validation

Illustrative pattern.
```

- [ ] **Step 4: Verify the frozen packs are valid + buildable**

Run: `python3 -m apd_gauntlet.cli validate-domain api-security pbm --domains-dir tests/fixtures/frozen-domains`
Expected: exit 0, two "OK" lines (pbm's `common-patterns/*.md` glob resolves to
`common-patterns/integrity.md`).
Run: `python3 -m apd_gauntlet.cli build-domain-skill api-security pbm --domains-dir tests/fixtures/frozen-domains --out /tmp/apd-frozen-skill --framework-version 1.0.0`
Expected: exit 0, "Wrote …/SKILL.md".

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/frozen-domains
git commit -m "test(fixtures): frozen domain packs for draft-domain-improvements golden tests"
```

---

## Task 9: The on-demand `draft-domain-improvements` command (engine + CLI)

**Files:**
- Create: `tools/apd_gauntlet/synthesis/draft.py`
- Modify: `tools/apd_gauntlet/cli.py` (register `draft-domain-improvements` after `domain-coverage-delta`)
- Create: `tests/test_draft_domain_improvements.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_draft_domain_improvements.py`:

```python
"""Tests for the on-demand draft-domain-improvements command (§6, §12)."""
from __future__ import annotations

import pathlib
import subprocess

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_improvement_id
from click.testing import CliRunner

FROZEN = pathlib.Path("tests/fixtures/frozen-domains").resolve()


def _record(itype, pack, tfile, ref, snippet, *, kind="asset_inventory",
            apd_goal=None, hint=None, priority="high"):
    rid = compute_improvement_id(itype, pack, tfile, ref)
    rec = {
        "id": rid,
        "improvement_type": itype,
        "target_pack": pack,
        "target_file": tfile,
        "source": "deterministic" if kind == "asset_inventory" else "judgment",
        "priority": priority,
        "evidence": [{"kind": kind, "ref": ref}],
        "rationale": "The run exercised something no selected pack fully declares here.",
        "suggested_action": "add the missing item to the pack",
        "draft_snippet": snippet,
    }
    if apd_goal:
        rec["apd_goal"] = apd_goal
    if hint:
        rec["insertion_hint"] = hint
    return rec


def _write_run(tmp_path, records, examined=("api-security", "pbm")):
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    doc = {
        "schema_version": 1,
        "generated_by": "domain-auditor",
        "examined_domains": list(examined),
        "improvements": records,
    }
    (run_dir / "40-synthesis" / "domain-improvements.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )
    return run_dir


def _invoke(run_dir, *extra):
    return CliRunner().invoke(
        main,
        ["draft-domain-improvements", str(run_dir),
         "--domains-dir", str(FROZEN), *extra],
    )


def _git_apply_check(patch_path, frozen_copy):
    """Return True if `git apply --check` accepts the patch against frozen_copy."""
    r = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        cwd=frozen_copy, capture_output=True, text=True,
    )
    return r.returncode == 0, r.stderr


def _frozen_git_tree(tmp_path):
    """A git-initialized copy of the frozen packs (parent of a `domains/` dir),
    so `git apply --check` on an a/domains/... patch resolves."""
    import shutil
    root = tmp_path / "tree"
    (root / "domains").mkdir(parents=True)
    for pack in ("api-security", "pbm"):
        shutil.copytree(FROZEN / pack, root / "domains" / pack)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "frozen"], cwd=root, check=True)
    return root


def test_happy_path_domain_yaml(tmp_path):
    rec = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 0 dropped" in result.output
    patch = run_dir / "40-synthesis" / "domain-improvements.patch"
    assert patch.exists()
    text = patch.read_text()
    assert "a/domains/api-security/domain.yaml" in text
    assert "payment_methods_store" in text
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(patch, tree)
    assert ok, err


def test_determinism_byte_identical(tmp_path):
    rec = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec])
    _invoke(run_dir, "--out", str(run_dir / "a.patch"))
    _invoke(run_dir, "--out", str(run_dir / "b.patch"))
    assert (run_dir / "a.patch").read_text() == (run_dir / "b.patch").read_text()


def test_new_file_common_pattern(tmp_path):
    # availability.md is absent from the frozen api-security pack.
    rec = _record(
        "missing_common_pattern", "api-security", "common-patterns/availability.md",
        "avail-11112222", "### Rate limiting\nIllustrative availability pattern.\n",
        kind="finding", apd_goal="availability",
    )
    run_dir = _write_run(tmp_path, [rec])
    # The cross-file validator would flag the finding ref; the draft command does
    # NOT re-resolve evidence — it trusts the captured artifact. So no corpus needed.
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "new file mode 100644" in patch
    assert "--- /dev/null" in patch
    assert "b/domains/api-security/common-patterns/availability.md" in patch
    # Coupled domain.yaml include edit appears (includes did not glob common-patterns/*.md).
    assert "a/domains/api-security/domain.yaml" in patch
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(run_dir / "40-synthesis" / "domain-improvements.patch", tree)
    assert ok, err


def test_new_file_common_pattern_glob_covered_no_domain_yaml_edit(tmp_path):
    # pbm's includes already globs common-patterns/*.md, so a new common-patterns
    # file needs NO domain.yaml edit (_ensure_include_glob `covered` short-circuit).
    # availability.md is absent from the frozen pbm pack.
    rec = _record(
        "missing_common_pattern", "pbm", "common-patterns/availability.md",
        "avail-33334444", "### Bulkheads\nIllustrative availability pattern.\n",
        kind="finding", apd_goal="availability",
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "new file mode 100644" in patch
    assert "b/domains/pbm/common-patterns/availability.md" in patch
    # The glob already covers it, so NO domain.yaml modify hunk for pbm.
    assert "a/domains/pbm/domain.yaml" not in patch
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(run_dir / "40-synthesis" / "domain-improvements.patch", tree)
    assert ok, err


def test_drop_on_fail_domain_yaml_target(tmp_path):
    bad = _record(  # crown_jewels item missing required `description`
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-bad00000",
        "- pattern: broken_store\n", hint={"yaml_path": "crown_jewels"}, priority="medium",
    )
    good = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [bad, good])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 1 dropped" in result.output
    assert bad["id"] in result.output  # dropped id reported
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "payment_methods_store" in patch
    assert "broken_store" not in patch


def test_drop_on_fail_md_target_reserved_marker(tmp_path):
    # An .md snippet introducing the builder's reserved `## Domain:` marker is
    # dropped by the draft.py structural check (validate-domain does NOT gate .md).
    bad = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-22223333",
        "## Domain: spoofed — Source: `x`\nmalicious heading collision\n",
        kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "High"}},
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "markdown structural check" in result.output


def test_rebuild_isolation_second_snippet_dropped(tmp_path):
    good = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    bad = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-bad00000",
        "- pattern: broken_store\n", hint={"yaml_path": "crown_jewels"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [good, bad])
    result = _invoke(run_dir)
    assert "1 drafted, 1 dropped" in result.output


def test_already_declared_duplicate_dropped(tmp_path):
    dup = _record(  # audit_log_store already declared in frozen api-security
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-dup00000",
        "- pattern: audit_log_store\n  description: \"Duplicate of an existing crown jewel.\"\n",
        hint={"yaml_path": "crown_jewels"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [dup])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "already declared in api-security" in result.output


def test_unknown_target_pack_dropped(tmp_path):
    rec = _record(
        "missing_crown_jewel", "no-such-pack", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: x_store\n  description: \"A store in a pack that does not exist.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec], examined=("no-such-pack",))
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "unknown target_pack" in result.output


def test_no_opportunities_path(tmp_path):
    run_dir = _write_run(tmp_path, [])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "0 opportunities selected; nothing to draft" in result.output
    assert not (run_dir / "40-synthesis" / "domain-improvements.patch").exists()


def test_id_filter_selects_subset(tmp_path):
    a = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    b = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-2b3c4d5e",
        "- pattern: secrets_store\n  description: \"Secrets store grounded in the inventory.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [a, b])
    result = _invoke(run_dir, "--id", a["id"])
    assert "1 drafted" in result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "payment_methods_store" in patch and "secrets_store" not in patch


def test_regulatory_anchor_happy_path(tmp_path):
    # A new regulatory_anchors string lands (the scalar-append branch, distinct from
    # the mapping-item append the crown-jewel tests exercise).
    rec = _record(
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-aaaa1111",
        "PCI DSS v4.0\n", kind="finding",
        hint={"yaml_path": "regulatory_anchors"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 0 dropped" in result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "PCI DSS v4.0" in patch


def test_regulatory_anchor_already_declared_dropped(tmp_path):
    # "OWASP API Top 10 (2023)" is already in the frozen api-security regulatory_anchors.
    dup = _record(
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-bbbb2222",
        "OWASP API Top 10 (2023)\n", kind="finding",
        hint={"yaml_path": "regulatory_anchors"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [dup])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "already declared in api-security" in result.output


def test_regulatory_anchor_shape_mismatch_dropped(tmp_path):
    # A regulatory_anchors snippet that safe_loads to a MAPPING (not a string) is
    # dropped with the scalar-shape reason 'expected one string'.
    bad = _record(
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-cccc3333",
        "- anchor: HIPAA\n  note: wrong shape\n", kind="finding",
        hint={"yaml_path": "regulatory_anchors"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "expected one string" in result.output


def test_md_unbalanced_code_fence_dropped(tmp_path):
    # Structural-check branch (a): a single unbalanced ``` fence.
    bad = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-dddd4444",
        "```\nunterminated fence\n", kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "High"}},
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "unbalanced code fences" in result.output


def test_md_oversized_snippet_dropped(tmp_path):
    # Structural-check branch (c): a snippet over _MAX_SNIPPET_BYTES (8192).
    bad = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-eeee5555",
        "- **Harm** — " + ("x" * 9000) + "\n", kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "High"}},
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "snippet exceeds size cap" in result.output


def test_md_retarget_eof_fallback_on_no_heading_match(tmp_path):
    # §6.3 EOF fallback: an insertion_hint whose heading matches ZERO headings in the
    # frozen file. The snippet still LANDS (drafted, not dropped) under a generated
    # '## Captured improvement (<dimpr-id>)' heading, and RETARGETED is surfaced.
    rec = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-ffff6666",
        "- **Novel harm** — disrupts a service tier the rubric does not name.\n",
        kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "Nonexistent Heading"}},
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 0 dropped" in result.output
    assert f"RETARGETED {rec['id']}" in result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert f"## Captured improvement ({rec['id']})" in patch
    assert "Novel harm" in patch


def test_invalid_target_pack_name_dropped(tmp_path):
    # ACT-path defence-in-depth (Guard 0): a corrupted artifact whose target_pack is a
    # traversal name is dropped with 'invalid target_pack name' BEFORE any path build,
    # so the §12 path-safety claim holds at draft time too. We bypass the schema by
    # hand-writing the doc (the schema would reject '../x' at capture, but the draft
    # command does NOT re-validate the on-disk artifact).
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    (run_dir / "40-synthesis" / "domain-improvements.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: domain-auditor\n"
        "examined_domains:\n  - api-security\n"
        "improvements:\n"
        "  - id: dimpr-00000000\n"
        "    improvement_type: missing_crown_jewel\n"
        "    target_pack: ../x\n"
        "    target_file: domain.yaml\n"
        "    source: deterministic\n    priority: medium\n"
        "    evidence:\n      - kind: asset_inventory\n        ref: asset-1a2b3c4d\n"
        "    rationale: \"corrupted artifact carrying a traversal pack name\"\n"
        "    suggested_action: \"must be dropped, not path-built\"\n"
        "    draft_snippet: \"- pattern: x\\n  description: escaping pack name\"\n",
        encoding="utf-8",
    )
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "invalid target_pack name" in result.output
    assert not (run_dir / "40-synthesis" / "domain-improvements.patch").exists()


def test_command_registered():
    result = CliRunner().invoke(main, ["draft-domain-improvements", "--help"])
    assert result.exit_code == 0
    assert "draft-domain-improvements" in result.output or "Usage" in result.output
```

The `_MAX_SNIPPET_BYTES`-oversize and unbalanced-fence tests pin structural-check branches (a) and (c); the reserved-marker test above pins branch (b) (§6.4 names all three). The retarget test pins the §6.3 EOF-fallback insert AND the author-facing `RETARGETED` surfacing (otherwise untested). The `regulatory_anchors` duplicate-drop and shape-mismatch tests cover the scalar list type — the one with a distinct shape rule (`expected one string`) — so all four `domain.yaml` list types are exercised, not crown_jewels alone.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_draft_domain_improvements.py -q`
Expected: errors — `draft-domain-improvements` is not a registered command.

- [ ] **Step 3: Create `tools/apd_gauntlet/synthesis/draft.py`**

```python
"""On-demand draft-domain-improvements engine (Subsystem B, spec §6).

PURE PYTHON, deterministic — the LLM already did all judgment at capture. The
command never edits a real pack file: it operates on a tempfile copy of domains/
and emits a unified, `git apply`-able diff. Each selected improvement's
draft_snippet is inserted and gated INDIVIDUALLY (validate-domain for the 4
domain.yaml types; a markdown structural check for the 5 .md types) plus a fresh
build-domain-skill rebuild; a failing snippet is reverted and DROPPED (reported).
"""
from __future__ import annotations

import difflib
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Reserved builder markers a .md snippet must NOT introduce (build_domain_skill).
_RESERVED_MARKERS = (
    "## Domain: ",
    "## Domain attack-path defaults",
)
_MAX_SNIPPET_BYTES = 8192

# Defence-in-depth pack-name guard on the ACT path. The CAPTURE path is protected by
# the schema's ^[a-z][a-z0-9-]*$ target_pack pattern, but _load_improvements only
# yaml.safe_loads the on-disk artifact and does NOT re-validate it against the schema.
# A hand-edited/corrupted artifact carrying target_pack '../x' would otherwise build
# pack_dir = copy_domains/'../x', resolving OUTSIDE the temp domains/ subtree. Re-apply
# the same pattern here so the §12 path-safety claim ("a traversal pack name never
# reaches the draft.py path builder") holds at draft time too, not only at capture.
_PACK_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")

_YAML_PATH_BY_TYPE = {
    "missing_crown_jewel": "crown_jewels",
    "missing_attacker_position": "attacker_positions",
    "missing_trust_boundary": "default_trust_boundaries",
    "missing_regulatory_anchor": "regulatory_anchors",
}
_ITEM_KEY_BY_PATH = {
    "crown_jewels": "pattern",
    "attacker_positions": "position",
    "default_trust_boundaries": "boundary",
}
# apd_goal -> on-disk common-patterns file stem. This is the INVERSE-EXCEPTION of
# the nine `apd_goal` -> `target_file` allOf branches in
# schemas/domain-improvement.schema.json (Task 1 Step 3): the schema enumerates the
# full nine-row table; here we encode only the ONE goal whose stem differs from its
# enum spelling (non_repudiation -> non-repudiation.md), and _GOAL_FILE.get(goal, goal)
# passes the other eight through unchanged. These two encodings MUST stay consistent:
# if a goal is ever renamed, update BOTH the schema allOf branch and this dict (they
# are the single underscore/hyphen contract the rest of the system honors, §4.1).
_GOAL_FILE = {
    "non_repudiation": "non-repudiation",
}


@dataclass
class DraftResult:
    drafted: list[str] = field(default_factory=list)        # dimpr- ids kept
    dropped: list[tuple[str, str, str]] = field(default_factory=list)  # (id, target_file, reason)
    retargeted: list[tuple[str, str]] = field(default_factory=list)    # (id, note)
    patch_text: str = ""
    patch_written: bool = False


class DraftError(Exception):
    """Internal error (artifact missing/malformed, temp-copy failure)."""


def _load_improvements(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    if not path.exists():
        raise DraftError(f"domain-improvements.yaml not found at {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise DraftError(f"domain-improvements.yaml is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise DraftError("domain-improvements.yaml is not a mapping")
    return data


def _select(
    improvements: list[dict[str, Any]],
    ids: tuple[str, ...],
    types: tuple[str, ...],
    packs: tuple[str, ...],
) -> list[dict[str, Any]]:
    out = improvements
    if ids:
        out = [i for i in out if i.get("id") in ids]
    if types:
        out = [i for i in out if i.get("improvement_type") in types]
    if packs:
        out = [i for i in out if i.get("target_pack") in packs]
    return out


def _resolve_target_file(imp: dict[str, Any]) -> str:
    """For missing_common_pattern, derive target_file from apd_goal (§4.1 rule)."""
    if imp.get("improvement_type") == "missing_common_pattern":
        goal = imp.get("apd_goal", "")
        stem = _GOAL_FILE.get(goal, goal)
        return f"common-patterns/{stem}.md"
    return imp.get("target_file", "")


def _validate_domain(pack: str, domains_dir: Path) -> tuple[bool, str]:
    """Run the same schema + include-resolution check validate_domain_cmd runs."""
    import json

    from jsonschema import Draft202012Validator

    repo = Path(__file__).resolve().parent.parent.parent.parent
    schema = json.loads((repo / "schemas" / "domain.schema.json").read_text(encoding="utf-8"))
    pack_dir = domains_dir / pack
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        return False, f"domain pack '{pack}' not found"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    if errors:
        return False, "; ".join(e.message for e in errors[:3])
    missing = [g for g in meta.get("includes", []) if not list(pack_dir.glob(g))]
    if missing:
        return False, f"unresolved includes: {missing}"
    return True, ""


_FALLBACK_FRAMEWORK_VERSION = "1.0.0"


def _framework_version(run_dir: Path) -> str:
    """Read framework_version from <run_dir>/.apd-run.yaml (the same source
    coverage_delta reads), falling back to a constant only when absent. Passing the
    live floor keeps the rebuild gate honest against a real pack whose framework_compat
    floor is above 1.0.0 (a hardcoded 1.0.0 would spuriously fail the build and drop
    every snippet, §6.4 / Issue: hardcoded framework version)."""
    cfg_path = run_dir / ".apd-run.yaml"
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            cfg = {}
        fv = cfg.get("framework_version")
        if isinstance(fv, str) and fv:
            return fv
    return _FALLBACK_FRAMEWORK_VERSION


def _rebuild(
    packs: list[str], domains_dir: Path, out_dir: Path, framework_version: str
) -> tuple[bool, str]:
    """Fresh-out-dir build (§6.4 step 3) so _existing_pack_signature never skips."""
    from ..build_domain_skill import build_domain_skill

    try:
        build_domain_skill(packs, domains_dir, out_dir, framework_version)
    except (FileNotFoundError, ValueError) as e:
        return False, str(e)
    return True, ""


def _markdown_structural_check(snippet: str) -> tuple[bool, str]:
    if len(snippet.encode("utf-8")) > _MAX_SNIPPET_BYTES:
        return False, "snippet exceeds size cap"
    if snippet.count("```") % 2 != 0:
        return False, "unbalanced code fences"
    for line in snippet.splitlines():
        for marker in _RESERVED_MARKERS:
            if line.startswith(marker):
                return False, f"collides with reserved builder marker {marker!r}"
    return True, ""


def _insert_domain_yaml(
    pack_dir: Path, imp: dict[str, Any], declared: set[str]
) -> tuple[bool, str]:
    """Append exactly one list item to the right domain.yaml key. Returns
    (ok, reason). On failure NOTHING is written (the caller's snapshot is intact)."""
    yaml_path = (imp.get("insertion_hint") or {}).get("yaml_path") or \
        _YAML_PATH_BY_TYPE.get(imp["improvement_type"], "")
    if not yaml_path:
        return False, "no yaml_path for domain.yaml target"
    try:
        node = yaml.safe_load(imp["draft_snippet"])
    except yaml.YAMLError as e:
        return False, f"snippet not valid YAML: {e}"

    meta_path = pack_dir / "domain.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))

    if yaml_path == "regulatory_anchors":
        if not isinstance(node, str):
            return False, "snippet shape: expected one string"
        if node.strip().lower() in declared:
            return False, f"already declared in {pack_dir.name}"
        meta.setdefault("regulatory_anchors", [])
        meta["regulatory_anchors"].append(node)
    else:
        if not isinstance(node, dict):
            return False, "snippet shape: expected one mapping"
        key = _ITEM_KEY_BY_PATH[yaml_path]
        if key not in node:
            return False, f"snippet shape: expected one mapping with '{key}'"
        if str(node[key]).strip().lower() in declared:
            return False, f"already declared in {pack_dir.name}"
        meta.setdefault(yaml_path, [])
        meta[yaml_path].append(node)

    meta_path.write_text(
        yaml.safe_dump(meta, sort_keys=False, default_flow_style=False,
                       allow_unicode=True, width=4096),
        encoding="utf-8",
    )
    return True, ""


def _declared_keys(pack_dir: Path, yaml_path: str) -> set[str]:
    meta = yaml.safe_load((pack_dir / "domain.yaml").read_text(encoding="utf-8")) or {}
    if yaml_path == "regulatory_anchors":
        return {str(x).strip().lower() for x in (meta.get("regulatory_anchors") or [])}
    key = _ITEM_KEY_BY_PATH.get(yaml_path)
    out: set[str] = set()
    for item in (meta.get(yaml_path) or []):
        if isinstance(item, dict) and item.get(key):
            out.add(str(item[key]).strip().lower())
    return out


def _ensure_trailing_newline(text: str) -> str:
    return text.rstrip("\n") + "\n"


def _insert_markdown(
    target: Path, imp: dict[str, Any], dimpr_id: str
) -> tuple[bool, str, str | None]:
    """Insert the snippet into a .md file (creating it if absent). Returns
    (ok, reason, retarget_note). Level-aware anchor with EOF fallback (§6.3)."""
    snippet = _ensure_trailing_newline(imp["draft_snippet"])
    new_file = not target.exists()
    if new_file:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(snippet, encoding="utf-8")
        return True, "", None

    body = target.read_text(encoding="utf-8")
    lines = body.splitlines()
    hint = (imp.get("insertion_hint") or {}).get("markdown_section")
    retarget: str | None = None
    insert_at: int | None = None
    if hint:
        level, text = hint["level"], hint["text"]
        prefix = "#" * level + " "
        matches = [k for k, ln in enumerate(lines) if ln.strip() == (prefix + text).strip()]
        if len(matches) == 1:
            start = matches[0]
            insert_at = len(lines)
            for k in range(start + 1, len(lines)):
                stripped = lines[k].lstrip("#")
                hlevel = len(lines[k]) - len(stripped)
                if lines[k].startswith("#") and hlevel <= level:
                    insert_at = k
                    break
        else:
            retarget = f"{len(matches)} heading matches at level {level} for {text!r}; appended at EOF"
    if insert_at is None:
        # EOF fallback under a generated heading.
        block = _ensure_trailing_newline(body) + "\n" + \
            f"## Captured improvement ({dimpr_id})\n\n" + snippet
        target.write_text(_ensure_trailing_newline(block), encoding="utf-8")
        return True, "", retarget

    new_lines = lines[:insert_at] + ["", snippet.rstrip("\n")] + lines[insert_at:]
    target.write_text(_ensure_trailing_newline("\n".join(new_lines)), encoding="utf-8")
    return True, "", retarget


def _ensure_include_glob(pack_dir: Path, target_file: str) -> bool:
    """Couple a new common-patterns/<goal>.md into domain.yaml includes (§6.3).
    Returns True if domain.yaml was edited (the include was appended), False if the
    file was already covered by an existing glob/explicit include (the `covered`
    short-circuit — spec §6.3 "If the pack's includes already globs
    common-patterns/*.md, only the new file is created, no domain.yaml edit needed").
    The caller uses the return to decide whether a domain.yaml modify hunk is emitted."""
    meta_path = pack_dir / "domain.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    includes = meta.get("includes", [])
    covered = any(
        g == target_file or (g == "common-patterns/*.md" and target_file.startswith("common-patterns/"))
        for g in includes
    )
    if covered:
        return False
    includes.append(target_file)
    meta["includes"] = includes
    meta_path.write_text(
        yaml.safe_dump(meta, sort_keys=False, default_flow_style=False,
                       allow_unicode=True, width=4096),
        encoding="utf-8",
    )
    return True


def _unified_diff(orig_root: Path, copy_root: Path, rel: str) -> str:
    """Per-file unified diff. Emits a git new-file hunk when the original is absent."""
    a_path = orig_root / rel
    b_path = copy_root / rel
    b_text = b_path.read_text(encoding="utf-8")
    if not a_path.exists():
        body = "".join(
            difflib.unified_diff(
                [], b_text.splitlines(keepends=True),
                fromfile="/dev/null", tofile="b/" + rel,
            )
        )
        return (
            f"diff --git a/{rel} b/{rel}\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            f"+++ b/{rel}\n"
            + "".join(body.splitlines(keepends=True)[2:])  # drop difflib's --- /+++ header
        )
    a_text = a_path.read_text(encoding="utf-8")
    return "".join(
        difflib.unified_diff(
            a_text.splitlines(keepends=True),
            b_text.splitlines(keepends=True),
            fromfile="a/" + rel, tofile="b/" + rel,
        )
    )


def draft_domain_improvements(
    run_dir: Path,
    domains_dir: Path,
    out: Path,
    *,
    ids: tuple[str, ...] = (),
    types: tuple[str, ...] = (),
    packs: tuple[str, ...] = (),
) -> DraftResult:
    data = _load_improvements(run_dir)
    examined = [str(d) for d in (data.get("examined_domains") or [])]
    framework_version = _framework_version(run_dir)
    selected = _select(list(data.get("improvements") or []), ids, types, packs)
    result = DraftResult()
    if not selected:
        return result  # no-op; caller prints the message and exits 0

    # Stable processing order (§6.6): (target_pack, resolved target_file, dimpr-id).
    selected.sort(key=lambda i: (
        i.get("target_pack", ""), _resolve_target_file(i), i.get("id", "")))

    all_packs = sorted({i["target_pack"] for i in selected
                        if _PACK_NAME_RE.match(i.get("target_pack", ""))
                        and (domains_dir / i["target_pack"] / "domain.yaml").exists()})

    with tempfile.TemporaryDirectory() as tmp:
        tmproot = Path(tmp)
        copy_domains = tmproot / "domains"
        shutil.copytree(domains_dir, copy_domains)

        changed: set[str] = set()  # rel paths that were kept
        for imp in selected:
            dimpr_id = imp.get("id", "")
            pack = imp.get("target_pack", "")
            target_file = _resolve_target_file(imp)

            # Guard 0: pack-name shape (defence-in-depth on the ACT path). A traversal
            # or upper-case name from a corrupted artifact is dropped BEFORE any path
            # is constructed, so it never reaches the path builder (§12 path-safety).
            if not _PACK_NAME_RE.match(pack):
                result.dropped.append((dimpr_id, target_file, "invalid target_pack name"))
                continue

            rel = f"domains/{pack}/{target_file}"
            pack_dir = copy_domains / pack

            # Guard 1: unknown target_pack (check the COPY, before any path open).
            if not (pack_dir / "domain.yaml").exists():
                result.dropped.append((dimpr_id, target_file, "unknown target_pack"))
                continue

            # Snapshot the files this insert may touch (for revert).
            target_path = copy_domains / pack / target_file
            snap_meta = (pack_dir / "domain.yaml").read_text(encoding="utf-8")
            snap_target = target_path.read_text(encoding="utf-8") if target_path.exists() else None
            target_existed = target_path.exists()

            is_yaml = target_file == "domain.yaml"
            ok, reason = True, ""
            retarget: str | None = None
            coupled_yaml = False

            if is_yaml:
                yaml_path = (imp.get("insertion_hint") or {}).get("yaml_path") or \
                    _YAML_PATH_BY_TYPE.get(imp["improvement_type"], "")
                declared = _declared_keys(pack_dir, yaml_path) if yaml_path else set()
                ok, reason = _insert_domain_yaml(pack_dir, imp, declared)
            else:
                ok, reason = _markdown_structural_check(imp["draft_snippet"])
                if ok:
                    ins_ok, ins_reason, retarget = _insert_markdown(target_path, imp, dimpr_id)
                    ok, reason = ins_ok, ins_reason
                    if ok and not target_existed:
                        # coupled_yaml is True ONLY if the include was actually appended;
                        # a glob-covered pack ("common-patterns/*.md") needs no edit, so
                        # no domain.yaml hunk and no validate-domain re-gate for it.
                        coupled_yaml = _ensure_include_glob(pack_dir, target_file)
                if not ok:
                    reason = f"markdown structural check: {reason}"

            # Gate: validate-domain (meaningful for domain.yaml + the coupled edit) + rebuild.
            if ok and (is_yaml or coupled_yaml):
                v_ok, v_reason = _validate_domain(pack, copy_domains)
                if not v_ok:
                    ok, reason = False, v_reason
            if ok:
                build_out = tmproot / f"skill-{dimpr_id}"
                b_ok, b_reason = _rebuild(all_packs, copy_domains, build_out, framework_version)
                if not b_ok:
                    ok, reason = False, f"build-domain-skill: {b_reason}"

            if not ok:
                # Revert this single snippet (restore the in-memory snapshot).
                (pack_dir / "domain.yaml").write_text(snap_meta, encoding="utf-8")
                if snap_target is None:
                    if target_path.exists():
                        target_path.unlink()
                else:
                    target_path.write_text(snap_target, encoding="utf-8")
                result.dropped.append((dimpr_id, target_file, reason))
                continue

            result.drafted.append(dimpr_id)
            changed.add(rel)
            if coupled_yaml:
                changed.add(f"domains/{pack}/domain.yaml")
            if retarget:
                result.retargeted.append((dimpr_id, retarget))

        # Build the patch from kept changes, deterministic file order.
        parts = [_unified_diff(domains_dir.parent, tmproot, rel) for rel in sorted(changed)]
        result.patch_text = "".join(parts)

    if result.drafted:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.patch_text, encoding="utf-8")
        result.patch_written = True
    return result
```

Note on `_unified_diff(domains_dir.parent, tmproot, rel)`: the `rel` paths are `domains/<pack>/<file>`, so the original tree root is `domains_dir.parent` and the copy root is `tmproot` (which contains `domains/`). This makes `a/domains/...` / `b/domains/...` headers resolve under a repo root for `git apply`.

- [ ] **Step 4: Register the CLI command**

In `tools/apd_gauntlet/cli.py`, add after `domain_coverage_delta_cmd`:

```python
@main.command("draft-domain-improvements")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--domains-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("domains"),
)
@click.option("--out", "out", type=click.Path(path_type=Path), default=None,
              help="Patch output path. Default: <run_dir>/40-synthesis/domain-improvements.patch")
@click.option("--id", "ids", multiple=True, help="Only draft these dimpr- ids (repeatable).")
@click.option("--type", "types", multiple=True, help="Filter by improvement_type (repeatable).")
@click.option("--target-pack", "packs", multiple=True, help="Filter by target_pack (repeatable).")
def draft_domain_improvements_cmd(run_dir, domains_dir, out, ids, types, packs) -> None:  # type: ignore[no-untyped-def]
    """On-demand: insert chosen draft_snippets into a temp copy, gate, emit a diff."""
    from .synthesis.draft import DraftError, draft_domain_improvements

    out_path = out or (run_dir / "40-synthesis" / "domain-improvements.patch")
    try:
        res = draft_domain_improvements(
            run_dir, domains_dir, out_path, ids=ids, types=types, packs=packs
        )
    except DraftError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None

    if not res.drafted and not res.dropped:
        click.echo("0 opportunities selected; nothing to draft")
        return
    click.echo(f"{len(res.drafted)} drafted, {len(res.dropped)} dropped")
    for dimpr_id, tfile, reason in res.dropped:
        click.echo(f"  DROPPED {dimpr_id} ({tfile}): {reason}")
    for dimpr_id, note in res.retargeted:
        click.echo(f"  RETARGETED {dimpr_id}: {note}")
    if res.patch_written:
        click.echo(f"Wrote patch to {out_path}")
```

- [ ] **Step 5: Run the tests + mypy**

Run: `python3 -m pytest tests/test_draft_domain_improvements.py -q`
Expected: PASS.
Run: `python3 -m mypy tools/`
Expected: Success.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/draft.py tools/apd_gauntlet/cli.py tests/test_draft_domain_improvements.py
git commit -m "feat(cli): draft-domain-improvements — temp-copy insert, gate, drop, diff"
```

---

## Task 10: Closeout summary line

**Files:**
- Modify: `tools/apd_gauntlet/summary.py` (`summarize_run` + `render_summary`)
- Create: `tests/test_summary_domain_improvements.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_summary_domain_improvements.py`:

```python
"""Closeout summary line for domain-improvement opportunities (§9, §12)."""
from __future__ import annotations

import pathlib

from apd_gauntlet.summary import render_summary, summarize_run


def _run_with_doc(tmp_path, n: int | None) -> pathlib.Path:
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    if n is not None:
        improvements = "\n".join(
            f"  - id: dimpr-0000000{i}\n"
            f"    improvement_type: missing_crown_jewel\n"
            f"    target_pack: pbm\n    target_file: domain.yaml\n"
            f"    source: deterministic\n    priority: high\n"
            f"    evidence:\n      - kind: asset_inventory\n        ref: asset-0000000{i}\n"
            f"    rationale: \"grounded gap number {i} in the run inventory data\"\n"
            f"    suggested_action: \"add crown jewel\"\n"
            f"    draft_snippet: \"- pattern: s{i}\\n  description: x\"\n"
            for i in range(n)
        )
        doc = (
            "schema_version: 1\ngenerated_by: domain-auditor\n"
            "examined_domains:\n  - pbm\nimprovements:\n" + (improvements if n else "  []\n")
        )
        (run_dir / "40-synthesis" / "domain-improvements.yaml").write_text(doc, encoding="utf-8")
    return run_dir


def test_summarize_counts_improvements(tmp_path):
    run_dir = _run_with_doc(tmp_path, 2)
    stats = summarize_run(run_dir)
    assert stats["domain_improvements"] == 2


def test_render_emits_line_for_nonzero(tmp_path):
    run_dir = _run_with_doc(tmp_path, 2)
    out = render_summary(summarize_run(run_dir))
    assert ("2 domain-improvement opportunities captured; run apd-gauntlet "
            "draft-domain-improvements <run> to draft pack edits.") in out


def test_render_emits_zero_variant(tmp_path):
    run_dir = _run_with_doc(tmp_path, 0)
    out = render_summary(summarize_run(run_dir))
    assert "0 domain-improvement opportunities captured." in out


def test_absent_artifact_does_not_error_and_omits_line(tmp_path):
    run_dir = _run_with_doc(tmp_path, None)  # no artifact at all
    stats = summarize_run(run_dir)
    assert stats["domain_improvements"] is None
    out = render_summary(stats)
    assert "domain-improvement opportunities" not in out
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_summary_domain_improvements.py -q`
Expected: FAIL — `summarize_run` returns no `domain_improvements` key; `render_summary` emits no line.

- [ ] **Step 3: Extend `summary.py`**

In `tools/apd_gauntlet/summary.py`, inside `summarize_run`, after the `severity_disagreements` block (before the `return`), add:

```python
    domain_improvements_path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    domain_improvements: int | None = None
    if domain_improvements_path.exists():
        di = yaml.safe_load(domain_improvements_path.read_text(encoding="utf-8")) or {}
        domain_improvements = len(di.get("improvements") or [])
```

and add `"domain_improvements": domain_improvements,` to the returned dict.

In `render_summary`, before the final `return "\n".join(lines)`, add:

```python
    n = stats.get("domain_improvements")
    if n is not None:
        if n:
            lines.append(
                f"{n} domain-improvement opportunities captured; run apd-gauntlet "
                "draft-domain-improvements <run> to draft pack edits."
            )
        else:
            lines.append("0 domain-improvement opportunities captured.")
```

- [ ] **Step 4: Run the tests + mypy**

Run: `python3 -m pytest tests/test_summary_domain_improvements.py -q`
Expected: PASS.
Run: `python3 -m mypy tools/`
Expected: Success.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/summary.py tests/test_summary_domain_improvements.py
git commit -m "feat(summary): closeout line for domain-improvement opportunities"
```

---

## Task 11: Author documentation

**Files:**
- Create: `docs/improving-domain-packs.md`
- Modify: `docs/adapting-to-other-domains.md` (add the pointer subsection)
- Create: `tests/test_doc_improving_domain_packs.py` (pins the §10 pointer deliverable: guide exists + adapting doc links to it)

- [ ] **Step 1: Create `docs/improving-domain-packs.md`** (the §10 triage workflow)

```markdown
# Improving domain packs from gauntlet runs

A gauntlet run reveals where the active domain pack(s) are *incomplete* — a harm
with no matching severity clause, a crown jewel present in the run but declared by
no pack, a consequential action not enumerated. Subsystem B captures those gaps on
every run (advisory, non-blocking) and lets you turn chosen ones into a reviewable
patch. **B never auto-applies and never opens a PR — you own the apply + commit.**

## 1. Read the captured opportunities

After a run, open `runs/<id>/40-synthesis/domain-improvements.yaml`. Each record
names:

- the gap (`improvement_type`, one of the nine types),
- the `target_pack` / `target_file` it would edit,
- the `priority` and `source` (`deterministic` from the mechanical pre-pass, or
  `judgment` from the `apd-domain-auditor` agent),
- the `evidence` — the real finding id or asset/identity/boundary id that revealed
  it,
- a paste-ready `draft_snippet`.

A run with no opportunities emits a schema-valid empty artifact and the closeout
reports `0 domain-improvement opportunities captured.`

## 2. Draft a patch

```bash
apd-gauntlet draft-domain-improvements runs/<id>
```

Filter the set with repeatable flags:

```bash
apd-gauntlet draft-domain-improvements runs/<id> \
  --id dimpr-1a2b3c4d --type missing_crown_jewel --target-pack api-security
```

The command inserts each chosen `draft_snippet` into a **temp copy** of `domains/`,
runs `validate-domain` + `build-domain-skill` to prove the edited pack stays
schema-valid and rebuildable, **drops** any snippet that fails (reporting the
reason), and writes a unified diff to
`runs/<id>/40-synthesis/domain-improvements.patch`. It prints `N drafted, M dropped`
plus every dropped id with its gate error. The real `domains/` tree is never
touched.

## 3. Review the patch

The patch is a standard unified diff against `domains/<pack>/`. Note any dropped
improvements (e.g. `already declared in <pack>`, `unknown target_pack`, a validate
or markdown-structural error) and address them by hand or discard them. For `.md`
targets the gate only checks structure and rebuildability — the prose quality is
your review's responsibility.

## 4. Apply and re-validate

```bash
git apply runs/<id>/40-synthesis/domain-improvements.patch
apd-gauntlet validate-domain <pack>
apd-gauntlet build-domain-skill <packs…> --framework-version <v>
```

Commit the pack change as a normal authoring edit. B stops here: there is no
auto-PR and no closed loop back into the gauntlet.
```

- [ ] **Step 2: Add the pointer to `docs/adapting-to-other-domains.md`**

Append a subsection (place it near the end of the authoring guide):

```markdown
## Evolving a pack from gauntlet runs

Once a pack is in use, every gauntlet run captures the places it is still
incomplete into `runs/<id>/40-synthesis/domain-improvements.yaml` and offers a
deterministic command to turn chosen gaps into a reviewable patch. See
[improving-domain-packs.md](improving-domain-packs.md) for the read → draft →
review → `git apply` → re-validate workflow. The capture is advisory and
non-blocking; you always own the apply and the commit.
```

- [ ] **Step 3: Add a pointer-deliverable test, then run the doc suite**

There is **no** repo test that enumerates `docs/*.md` (verified: the only docs-pinning test is `tests/test_doc_attack_path_analysis.py`, which pins one specific guide, not a `docs/*.md` glob). So nothing currently verifies the §10 pointer deliverable. Add a one-file test `tests/test_doc_improving_domain_packs.py` that pins both halves of the §10 pointer (the new guide exists, and the adapting doc links to it):

```python
"""Pins the §10 author-doc pointer deliverable for Subsystem B."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"


def test_improving_domain_packs_guide_exists():
    guide = DOCS / "improving-domain-packs.md"
    assert guide.is_file(), "docs/improving-domain-packs.md must exist (§10)"
    assert "draft-domain-improvements" in guide.read_text(encoding="utf-8")


def test_adapting_doc_links_to_improving_guide():
    text = (DOCS / "adapting-to-other-domains.md").read_text(encoding="utf-8")
    assert "improving-domain-packs.md" in text, (
        "adapting-to-other-domains.md must link to improving-domain-packs.md (§10 pointer)"
    )
```

Run: `python3 -m pytest tests/test_doc_improving_domain_packs.py -q`
Expected: PASS (the guide exists and the adapting doc links to it).

Run: `python3 -m pytest tests/ -k "doc" -q`
Expected: PASS. No test pins `docs/*.md` as a set, so this is a smoke check over the existing doc tests plus the new one; it should report all-pass. Treat any failure as a real regression and stop — do not wave it through.

- [ ] **Step 4: Commit**

```bash
git add docs/improving-domain-packs.md docs/adapting-to-other-domains.md tests/test_doc_improving_domain_packs.py
git commit -m "docs: domain-pack improvement triage guide + adapting-doc pointer"
```

---

## Task 12: Final full-suite + mypy gate

**Files:** none (acceptance gate only).

- [ ] **Step 1: Full test suite**

Run: `python3 -m pytest -q`
Expected: PASS — the prior green baseline PLUS exactly the tests this plan added, and no change to any pre-existing test's count or status. The added test modules are: `test_domain_improvement_schema`, `test_coverage_delta`, `test_domain_improvement_linter`, `test_validate_domain_improvements` (schema-wiring + cross-file), `test_lint_agent_apd_domain_auditor`, the new `test_workflow_apd_gauntlet` Phase-5h pins, `test_draft_domain_improvements`, `test_summary_domain_improvements`, and `test_doc_improving_domain_packs`. (No absolute count is asserted — a fixed number is brittle the moment any unrelated commit lands; the gate is "prior baseline + this plan's tests, zero pre-existing test changes.")

- [ ] **Step 2: mypy strict**

Run: `python3 -m mypy tools/`
Expected: Success: no issues found.

- [ ] **Step 3: Verify both new commands are registered + the workflow scrape is green**

Run: `python3 -m pytest tests/test_workflow_apd_gauntlet.py::test_every_cli_command_is_registered tests/test_workflow_apd_gauntlet.py::test_referenced_commands_cover_the_pipeline -q`
Expected: PASS (`domain-coverage-delta` is pyStep-scraped and registered; `draft-domain-improvements` is author-run, never in a pyStep, and has its own `--help` registration test in Task 9).

- [ ] **Step 4: Final commit (if any incidental tidy)**

```bash
git add -A
git commit -m "test(b): full-suite + mypy green for domain-improvement capture & draft"
```

(Skip if the working tree is already clean.)

---

## Self-review notes (spec section → task mapping)

- **§1 Problem / §2 Goals / §3 Decisions:** realized across all tasks; the `dimpr-`-only-in-new-schemas decision (§3, §4.4) is enforced by Task 1 (no finding-schema edit) + Task 3 (file not in `RECORD_KINDS`).
- **§4 Data model:** §4.1 record schema → Task 1 Step 3 (incl. the nine `apd_goal`↔`target_file` `allOf` branches + the `source` discriminator + `dimpr-` pattern). §4.2 doc wrapper (self-describing envelope, required `examined_domains`, absolute-`$id` `$ref`) → Task 1 Step 4 + the `$ref`-resolves test. §4.3 validate wiring → Task 3 (`SYNTHESIS_ROLLUPS`) + Task 5 (`_validate_domain_improvements_cross_refs`, both id-recompute and evidence-ref in one cross-file helper; finding ids unioned from BOTH `_iter_records` (`*.findings.yaml`) AND `40-synthesis/deduped-findings.yaml`, so a `merged-<sha8>` id that lives only in the deduped corpus resolves — pinned by the merged-ref test). §4.4 dimpr- decision → Task 1 (finding schema untouched) + Task 3 comment.
- **§4.1 id algorithm:** the verbatim lowercased `|`-joined 4-tuple `compute_improvement_id` → Task 4 (with the explicit "not `compute_id`" test).
- **§5 taxonomy (nine types):** the three deterministic types → Task 2 pre-pass; the six judgment types → Task 6 agent contract. §5.1 pre-pass algorithm (union, artifact-only crown jewels, `domain_default` exclusion, evidence ref keyed off schema ids, byte-stable output, delta-doc schema) → Task 1 Step 5 (schema) + Task 2 (algorithm + tests).
- **§6 on-demand draft command:** §6.1 selection → Task 9 `_select`. §6.2 temp-copy (`TemporaryDirectory`) → Task 9. §6.3 insertion (yaml single-node shape, regulatory scalar, `allow_unicode`/`width=4096`, level-aware markdown anchor + EOF fallback, new-file coupled include edit) → Task 9. §6.4 per-improvement gate + drop (Guard-0 ACT-path pack-name shape guard / Guard-1 unknown-pack, already-declared duplicate across all four `domain.yaml` list types incl. the `regulatory_anchors` scalar shape, validate-domain for yaml / the three markdown structural branches for `.md`, fresh-out-dir rebuild keyed to the run's live `framework_version`, revert-on-fail) → Task 9 + its drop/isolation/duplicate/invalid-pack-name/md-structural/regulatory tests. §6.5 diff emission (modify + new-file hunk, trailing-newline normalization, summary line) → Task 9 `_unified_diff` + CLI. §6.3 new-file coupled include (append branch AND glob-covered `covered` short-circuit) → Task 9 `_ensure_include_glob` + both new-file tests; level-aware insert + EOF retarget fallback → Task 9 retarget test. §6.6 determinism (stable order, golden vs frozen fixture) → Task 8 frozen packs + Task 9 byte-identical test.
- **§7 apd-domain-auditor agent:** §7.1 inputs (incl. missing-delta tolerance) + §7.2 behavior (materialize, harvest, draft-once, id, dedup, self-check) + §7.3 receipt → Task 6 agent file. §7.4 linter (two functions, called from the cross-file helper, not the semantic pass) → Task 4 (helpers) + Task 5 (call site).
- **§8 capture-phase placement:** advisory non-blocking Phase 5h between 5g audit and closeout, two `meta.phases` entries, no `throw`, closeout surfacing via `summarize` → Task 7 (workflow + pins) + Task 10 (summary wiring).
- **§9 surfacing:** side-channel artifact + closeout line, no report-data change → Task 10; empty-run behavior → Task 2 (empty delta) + Task 6 (empty artifact) + Task 9 (no-op) + Task 10 (zero variant).
- **§10 author docs:** `docs/improving-domain-packs.md` + `adapting-to-other-domains.md` pointer → Task 11; the pointer deliverable (guide exists + adapting doc links to it) is pinned by `tests/test_doc_improving_domain_packs.py`.
- **§11 out of scope:** no `--open-pr`, no auto-apply, no finding cross-link, no new packs — honored (nothing in any task adds them).
- **§12 testing:** schema valid/invalid (incl. common_pattern mismatch + non_repudiation pass + missing examined_domains + delta-doc + BOTH path-safety rejects: `../x` traversal and `PBM` uppercase) → Task 1; validate wiring with non-empty doc + dangling-ref + merged-* deduped-corpus resolution → Tasks 3, 5; pre-pass all three types + empty + byte-stable → Task 2; id linter exact payload → Task 4; draft happy/new-file (append + glob-covered)/both-drop-kinds/md-structural-three-branches/regulatory-anchor scalar+duplicate+shape/retarget-EOF/isolation/duplicate/unknown-pack/invalid-pack-name/no-op/path-safety/determinism/id-filter → Tasks 1 (path-safety schema reject), 8, 9; closeout line → Task 10; agent receipt CONFORMS-TO-schema (whole-block jsonschema validation, not greps) + frontmatter lint (discretion NOT unit-tested) → Task 6; command registration (pyStep-scrape vs author-run `--help`) → Tasks 2, 9, 12; workflow pin (both new phase names appended to `EXPECTED_PHASES`+`DIRECT_PHASE_LITERALS`, ordering, non-blocking) → Task 7.
- **§13 risks:** synonym map / snippet rot / best-fit attribution / sparse inventories are acknowledged design risks; the duplicate-drop (§6.4) mitigation is implemented in Task 9; the rest are review-backstopped, not code in this plan.
```
