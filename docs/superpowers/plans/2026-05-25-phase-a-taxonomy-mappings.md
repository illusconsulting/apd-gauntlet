# Phase A — Multi-Framework Taxonomy Mappings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional CWE, OWASP Top 10 / API / LLM, and MITRE D3FEND mappings to findings and capabilities, with per-run scoping, intake auto-detect suggestions, new synthesizer coverage rollups, and three reference-data refresh scripts. Ship as `apd-gauntlet` v1.2.0 — fully additive within v1.x.

**Architecture:** Schema-first additive extensions to `finding.schema.json` and `capability.schema.json` (new optional sibling arrays inside `control_mappings`). New `run-config.schema.json` `taxonomies[]` field gates which taxonomies are in scope per run; intake writes auto-detect suggestions; specialists honor the declared scope via the updated `apd-control-mappings` skill; synthesizer emits three new coverage rollup artifacts validated by three new schema files. Three new `refresh-*` CLI subcommands fetch and project reference data with the same security hardening already applied to `refresh-mitre` (60s timeout, 200 MiB cap, `source_sha256` in projected payload).

**Tech Stack:** Python 3.10+, `jsonschema>=4.20`, `pyyaml>=6.0`, `click>=8.1`, `pytest>=8.0`, `ruff`, `mypy --strict`. JSON Schema draft 2020-12. Reference data shipped at `tools/apd_gauntlet/data/`.

---

## Pre-flight verification

Before starting Task 1, verify clean working tree and current passing state:

```bash
git status                          # expect: clean
pytest -q                           # expect: 114 passed
pytest --cov --cov-fail-under=85    # expect: pass
ruff check tools/ tests/            # expect: clean
mypy tools/                         # expect: clean
apd-gauntlet lint-agents            # expect: 13 agents clean
apd-gauntlet validate-domain pbm    # expect: clean
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # expect: 18 files, 26 records, clean
```

If any of the above fail, stop and investigate before starting the plan.

---

## Task 1: Pre-flight version bump (1.1.0 → 1.2.0-dev)

**Files:**

- Modify: `pyproject.toml:7`
- Modify: `tools/apd_gauntlet/__init__.py`
- Modify: `plugin.json`
- Modify: `tools/apd_gauntlet/cli.py` (search for `framework-version` default)

- [ ] **Step 1: Bump version in `pyproject.toml`**

Change `version = "1.1.0"` to `version = "1.2.0.dev0"` at line 7.

- [ ] **Step 2: Bump version in `tools/apd_gauntlet/__init__.py`**

Find `__version__ = "1.1.0"`; change to `__version__ = "1.2.0.dev0"`.

- [ ] **Step 3: Bump version in `plugin.json`**

Find `"version": "1.1.0"`; change to `"version": "1.2.0.dev0"`.

- [ ] **Step 4: Verify CLI `--framework-version` default**

Search `tools/apd_gauntlet/cli.py` for the `--framework-version` default. If hard-coded, update to `"1.2.0.dev0"`. If it reads from `apd_gauntlet.__version__`, no change needed.

- [ ] **Step 5: Run tests to confirm version bump doesn't break anything**

Run: `pytest -q`
Expected: PASS (114 tests)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tools/apd_gauntlet/__init__.py plugin.json tools/apd_gauntlet/cli.py
git commit -m "chore: bump version to 1.2.0.dev0 for Phase A work"
```

---

## Task 2: Extend `finding.schema.json` with four optional taxonomy fields

**Goal:** Add optional `cwe[]`, `owasp_top10[]`, `owasp_api_top10[]`, `owasp_llm_top10[]` arrays inside `control_mappings`, each with strict regex validation.

**Files:**

- Modify: `schemas/finding.schema.json` (extend `control_mappings.properties`)
- Modify: `tests/test_finding_schema.py` (add validation tests)
- Add: `tests/fixtures/findings/finding-with-cwe.yaml`
- Add: `tests/fixtures/findings/finding-with-owasp.yaml`
- Add: `tests/fixtures/findings/finding-with-invalid-cwe.yaml`

- [ ] **Step 1: Write failing tests**

In `tests/test_finding_schema.py`, add the following tests:

```python
def test_finding_accepts_optional_cwe():
    finding = load_fixture("findings/finding-with-cwe.yaml")
    # finding has control_mappings.cwe: ["CWE-79", "CWE-89"]
    assert validate_finding(finding) is None  # None = no error

def test_finding_accepts_optional_owasp_taxonomies():
    finding = load_fixture("findings/finding-with-owasp.yaml")
    # has owasp_top10: ["A03:2021"], owasp_api_top10: ["API3:2023"], owasp_llm_top10: ["LLM01"]
    assert validate_finding(finding) is None

def test_finding_rejects_invalid_cwe_format():
    finding = load_fixture("findings/finding-with-invalid-cwe.yaml")
    # has control_mappings.cwe: ["CWE-79-foo"]  -- invalid
    err = validate_finding(finding)
    assert err is not None
    assert "cwe" in err.message.lower() or "pattern" in err.message.lower()

def test_finding_without_new_taxonomies_still_valid():
    # Existing test pattern: load a v1.1-format finding (no cwe/owasp fields)
    finding = load_fixture("findings/minimal-finding.yaml")
    assert validate_finding(finding) is None  # backward-compat sanity check
```

Create fixtures:

`tests/fixtures/findings/finding-with-cwe.yaml`:

```yaml
schema_version: 1
id: conf-a1b2c3d4
agent: confidentiality
apd_tier: trustworthiness
apd_goal: confidentiality
disposition: gap
severity: medium
confidence: high
title: "PHI transmitted without TLS to pricing-service"
summary: "Adjudication service sends PHI in plaintext over internal network to pricing-service."
detail: "Code at services/adjudication/pricing_client.py:42 uses http:// not https://; CWE-319 cleartext transmission of sensitive data."
evidence:
  - artifact: services/adjudication/pricing_client.py
    locator: "L42"
    excerpt: 'response = requests.post("http://pricing-service/quote", json=phi_payload)'
control_mappings:
  nist_800_53r5: ["SC-8", "SC-8(1)"]
  cwe: ["CWE-319"]
recommendation:
  posture: required
  summary: "Switch the pricing client to HTTPS and verify the server certificate."
  detail: "Update the call to use https:// and confirm the gateway terminates with a valid cert chain; mTLS preferred since both services are internal."
```

`tests/fixtures/findings/finding-with-owasp.yaml`: similar shape, with the three OWASP fields populated.

`tests/fixtures/findings/finding-with-invalid-cwe.yaml`: same shape, but `cwe: ["CWE-79-foo"]`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_finding_schema.py -v -k "cwe or owasp"`
Expected: FAIL — schema doesn't yet accept these fields, so the valid fixtures fail validation, and the invalid-cwe test fails because validation passes when it should fail.

- [ ] **Step 3: Extend the schema**

In `schemas/finding.schema.json`, locate the `control_mappings.properties` block (around lines 62–84). Add four new optional sibling properties next to `nist_800_53r5` and `mitre_attack`:

```jsonc
"cwe": {
  "type": "array",
  "items": { "type": "string", "pattern": "^CWE-[0-9]+$" }
},
"owasp_top10": {
  "type": "array",
  "items": { "type": "string", "pattern": "^A[0-9]{2}:20[0-9]{2}$" }
},
"owasp_api_top10": {
  "type": "array",
  "items": { "type": "string", "pattern": "^API[0-9]{1,2}:20[0-9]{2}$" }
},
"owasp_llm_top10": {
  "type": "array",
  "items": { "type": "string", "pattern": "^LLM[0-9]{2}$" }
}
```

The `control_mappings.required` array stays at `["nist_800_53r5"]` only (new fields are optional). `additionalProperties: false` stays as-is — the schema now explicitly allows the four new fields.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_finding_schema.py -v`
Expected: PASS (all tests including the four new ones)

- [ ] **Step 5: Run full suite + linters to confirm no regressions**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add schemas/finding.schema.json tests/test_finding_schema.py tests/fixtures/findings/
git commit -m "feat(schema): finding.control_mappings gains optional cwe/owasp_top10/owasp_api_top10/owasp_llm_top10"
```

---

## Task 3: Extend `capability.schema.json` with optional `d3fend` field

**Goal:** Add optional `d3fend[]` array inside `control_mappings` on capability records. Each entry requires `technique`, `counters_attack` (list of ATT&CK technique IDs from the same record's `mitre_attack` block), and `rationale`. Schema-level validation enforces the format; cross-reference validation (`counters_attack` must intersect `mitre_attack`) is added in the validator module (Task 17 — `validate.py`).

**Files:**

- Modify: `schemas/capability.schema.json`
- Modify: `tests/test_capability_schema.py`
- Add: `tests/fixtures/capabilities/capability-with-d3fend.yaml`
- Add: `tests/fixtures/capabilities/capability-with-malformed-d3fend.yaml`

- [ ] **Step 1: Write failing tests**

In `tests/test_capability_schema.py`, add:

```python
def test_capability_accepts_optional_d3fend():
    cap = load_fixture("capabilities/capability-with-d3fend.yaml")
    # has control_mappings.d3fend: [{technique: "D3-NTA", counters_attack: ["T1078"], rationale: "..."}]
    assert validate_capability(cap) is None

def test_capability_rejects_d3fend_without_counters_attack():
    cap = load_fixture("capabilities/capability-with-malformed-d3fend.yaml")
    # missing counters_attack on the d3fend entry
    err = validate_capability(cap)
    assert err is not None
    assert "counters_attack" in err.message.lower() or "required" in err.message.lower()

def test_capability_without_d3fend_still_valid():
    cap = load_fixture("capabilities/minimal-capability.yaml")
    assert validate_capability(cap) is None  # backward-compat
```

`tests/fixtures/capabilities/capability-with-d3fend.yaml`:

```yaml
schema_version: 1
id: cap-1a2b3c4d
agent: authenticity
# ... existing required fields ...
control_mappings:
  nist_800_53r5: ["AC-3", "IA-5"]
  mitre_attack:
    - technique: T1078
      tactic: TA0001
      rationale: "mTLS prevents valid-account abuse on internal service-to-service paths."
  d3fend:
    - technique: D3-NTA
      counters_attack: ["T1078"]
      rationale: "Network traffic analysis with mTLS-enforced identity detects and prevents unauthorized service-to-service traversal."
```

`tests/fixtures/capabilities/capability-with-malformed-d3fend.yaml`: same but the `d3fend[0]` entry omits `counters_attack`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_capability_schema.py -v -k "d3fend"`
Expected: FAIL.

- [ ] **Step 3: Extend the schema**

In `schemas/capability.schema.json`, locate `control_mappings.properties` and add:

```jsonc
"d3fend": {
  "type": "array",
  "items": {
    "type": "object",
    "required": ["technique", "counters_attack", "rationale"],
    "additionalProperties": false,
    "properties": {
      "technique":        { "type": "string", "pattern": "^D3-[A-Z]{2,5}$" },
      "counters_attack":  {
        "type": "array",
        "minItems": 1,
        "items": { "type": "string", "pattern": "^T[0-9]{4}(\\.[0-9]{3})?$" }
      },
      "rationale":        { "type": "string", "minLength": 30 }
    }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_capability_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Run full suite + linters**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 6: Commit**

```bash
git add schemas/capability.schema.json tests/test_capability_schema.py tests/fixtures/capabilities/
git commit -m "feat(schema): capability.control_mappings gains optional d3fend[] with counters_attack requirement"
```

---

## Task 4: Extend `run-config.schema.json` with optional `taxonomies` array

**Goal:** Add optional `taxonomies` field that lists which framework taxonomies the run has in scope. Allowed values: `cwe`, `mitre_attack`, `d3fend`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`.

**Files:**

- Modify: `schemas/run-config.schema.json`
- Modify: `tests/test_run_config_schema.py`
- Add: `tests/fixtures/run-configs/run-config-with-taxonomies.yaml`
- Add: `tests/fixtures/run-configs/run-config-with-invalid-taxonomy.yaml`

- [ ] **Step 1: Write failing tests**

```python
def test_run_config_accepts_taxonomies():
    cfg = load_fixture("run-configs/run-config-with-taxonomies.yaml")
    # taxonomies: [cwe, mitre_attack, d3fend, owasp_api_top10]
    assert validate_run_config(cfg) is None

def test_run_config_rejects_unknown_taxonomy():
    cfg = load_fixture("run-configs/run-config-with-invalid-taxonomy.yaml")
    # taxonomies: [cwe, made_up_framework]
    err = validate_run_config(cfg)
    assert err is not None

def test_run_config_without_taxonomies_still_valid():
    cfg = load_fixture("run-configs/minimal-run-config.yaml")  # existing v1.1 fixture
    assert validate_run_config(cfg) is None  # backward-compat
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_run_config_schema.py -v -k "taxonom"`
Expected: FAIL.

- [ ] **Step 3: Extend the schema**

In `schemas/run-config.schema.json`, add to `properties`:

```jsonc
"taxonomies": {
  "type": "array",
  "uniqueItems": true,
  "items": {
    "type": "string",
    "enum": ["cwe", "mitre_attack", "d3fend", "owasp_top10", "owasp_api_top10", "owasp_llm_top10"]
  }
}
```

Do not add `taxonomies` to `required[]`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_run_config_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 6: Commit**

```bash
git add schemas/run-config.schema.json tests/test_run_config_schema.py tests/fixtures/run-configs/
git commit -m "feat(schema): run-config gains optional taxonomies[] declaration"
```

---

## Task 5: New schema `cwe-coverage.schema.json`

**Goal:** Schema for synthesizer-emitted CWE coverage rollup, analogous to existing `attack-exposure.schema.json`.

**Files:**

- Create: `schemas/cwe-coverage.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/rollups/cwe-coverage-valid.yaml`

- [ ] **Step 1: Write failing test**

In `tests/test_other_schemas.py`, add:

```python
def test_cwe_coverage_schema_validates():
    rollup = load_fixture("rollups/cwe-coverage-valid.yaml")
    err = validate_against_schema(rollup, "cwe-coverage.schema.json")
    assert err is None
```

Fixture `tests/fixtures/rollups/cwe-coverage-valid.yaml`:

```yaml
schema_version: 1
generated_by: synthesizer
entries:
  - cwe_id: CWE-79
    name: "Improper Neutralization of Input During Web Page Generation"
    abstraction: base
    parent_pillar: CWE-707
    finding_count: 2
    finding_ids: [intg-a1b2c3d4, intg-5e6f7g8h]
    surfaces:
      - "member-portal/profile-edit"
      - "member-portal/search-results"
  - cwe_id: CWE-319
    name: "Cleartext Transmission of Sensitive Information"
    abstraction: base
    parent_pillar: CWE-693
    finding_count: 1
    finding_ids: [conf-a1b2c3d4]
    surfaces:
      - "internal/adjudication-to-pricing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_other_schemas.py::test_cwe_coverage_schema_validates -v`
Expected: FAIL — schema file doesn't exist yet.

- [ ] **Step 3: Create the schema**

Create `schemas/cwe-coverage.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/cwe-coverage.schema.json",
  "title": "APD Gauntlet CWE Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "entries"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["cwe_id", "name", "abstraction", "finding_count", "finding_ids"],
        "additionalProperties": false,
        "properties": {
          "cwe_id":         { "type": "string", "pattern": "^CWE-[0-9]+$" },
          "name":           { "type": "string", "minLength": 3 },
          "abstraction":    { "type": "string", "enum": ["pillar", "class", "base", "variant", "compound"] },
          "parent_pillar":  { "type": ["string", "null"], "pattern": "^CWE-[0-9]+$" },
          "finding_count":  { "type": "integer", "minimum": 0 },
          "finding_ids":    { "type": "array", "items": { "type": "string" } },
          "surfaces":       { "type": "array", "items": { "type": "string", "minLength": 1 } }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_other_schemas.py::test_cwe_coverage_schema_validates -v`
Expected: PASS.

- [ ] **Step 5: Run full suite + meta-schema check**

Run: `pytest tests/test_meta_schemas.py -v && pytest -q`
Expected: PASS (meta-schema test validates the new schema file is itself a valid JSON Schema).

- [ ] **Step 6: Commit**

```bash
git add schemas/cwe-coverage.schema.json tests/test_other_schemas.py tests/fixtures/rollups/cwe-coverage-valid.yaml
git commit -m "feat(schema): add cwe-coverage rollup schema"
```

---

## Task 6: New schema `owasp-coverage.schema.json`

**Goal:** Schema for OWASP coverage rollup. Covers all three OWASP variants (Top 10, API Top 10, LLM Top 10) in one rollup, with `taxonomy` discriminator per entry.

**Files:**

- Create: `schemas/owasp-coverage.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/rollups/owasp-coverage-valid.yaml`

- [ ] **Step 1: Write failing test**

```python
def test_owasp_coverage_schema_validates():
    rollup = load_fixture("rollups/owasp-coverage-valid.yaml")
    err = validate_against_schema(rollup, "owasp-coverage.schema.json")
    assert err is None
```

Fixture covers entries from each of the three OWASP variants and one `silent: true` entry (no findings touched the category):

```yaml
schema_version: 1
generated_by: synthesizer
entries:
  - taxonomy: owasp_top10
    category_id: A03:2021
    name: "Injection"
    finding_count: 2
    finding_ids: [intg-a1b2c3d4, intg-5e6f7g8h]
    surfaces: ["member-portal/search"]
    silent: false
  - taxonomy: owasp_top10
    category_id: A05:2021
    name: "Security Misconfiguration"
    finding_count: 0
    finding_ids: []
    surfaces: []
    silent: true
  - taxonomy: owasp_api_top10
    category_id: API3:2023
    name: "Broken Object Property Level Authorization"
    finding_count: 1
    finding_ids: [auth-9f8e7d6c]
    surfaces: ["api/v1/members/{id}"]
    silent: false
  - taxonomy: owasp_llm_top10
    category_id: LLM01
    name: "Prompt Injection"
    finding_count: 0
    finding_ids: []
    surfaces: []
    silent: true
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_other_schemas.py::test_owasp_coverage_schema_validates -v`
Expected: FAIL.

- [ ] **Step 3: Create the schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/owasp-coverage.schema.json",
  "title": "APD Gauntlet OWASP Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "entries"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["taxonomy", "category_id", "name", "finding_count", "finding_ids", "silent"],
        "additionalProperties": false,
        "properties": {
          "taxonomy":      { "type": "string", "enum": ["owasp_top10", "owasp_api_top10", "owasp_llm_top10"] },
          "category_id":   { "type": "string", "minLength": 3 },
          "name":          { "type": "string", "minLength": 3 },
          "finding_count": { "type": "integer", "minimum": 0 },
          "finding_ids":   { "type": "array", "items": { "type": "string" } },
          "surfaces":      { "type": "array", "items": { "type": "string", "minLength": 1 } },
          "silent":        { "type": "boolean" }
        },
        "allOf": [
          {
            "if": { "properties": { "taxonomy": { "const": "owasp_top10" } } },
            "then": { "properties": { "category_id": { "pattern": "^A[0-9]{2}:20[0-9]{2}$" } } }
          },
          {
            "if": { "properties": { "taxonomy": { "const": "owasp_api_top10" } } },
            "then": { "properties": { "category_id": { "pattern": "^API[0-9]{1,2}:20[0-9]{2}$" } } }
          },
          {
            "if": { "properties": { "taxonomy": { "const": "owasp_llm_top10" } } },
            "then": { "properties": { "category_id": { "pattern": "^LLM[0-9]{2}$" } } }
          }
        ]
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_other_schemas.py::test_owasp_coverage_schema_validates -v`
Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest -q
```

- [ ] **Step 6: Commit**

```bash
git add schemas/owasp-coverage.schema.json tests/test_other_schemas.py tests/fixtures/rollups/owasp-coverage-valid.yaml
git commit -m "feat(schema): add owasp-coverage rollup schema (covers Top 10 / API / LLM)"
```

---

## Task 7: New schema `d3fend-coverage.schema.json`

**Goal:** Schema for D3FEND coverage rollup. Lists D3FEND techniques referenced by capabilities, plus a counter-coverage view (which exposed ATT&CK techniques have D3FEND-backed capabilities vs. which don't — feeds Phase C bottleneck analysis).

**Files:**

- Create: `schemas/d3fend-coverage.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/rollups/d3fend-coverage-valid.yaml`

- [ ] **Step 1: Write failing test**

```python
def test_d3fend_coverage_schema_validates():
    rollup = load_fixture("rollups/d3fend-coverage-valid.yaml")
    err = validate_against_schema(rollup, "d3fend-coverage.schema.json")
    assert err is None
```

Fixture (illustrative):

```yaml
schema_version: 1
generated_by: synthesizer
defensive_entries:
  - d3fend_id: D3-NTA
    name: "Network Traffic Analysis"
    capability_count: 2
    capability_ids: [cap-1a2b3c4d, cap-5e6f7g8h]
    counters_attack: ["T1078", "T1190"]
counter_coverage:
  - attack_technique: T1078
    exposed_by_finding_count: 3
    exposed_by_finding_ids: [auth-9f8e7d6c, auth-7g8h9i0j, auth-1k2l3m4n]
    countered_by_d3fend: ["D3-NTA"]
    countered_by_capability_ids: [cap-1a2b3c4d]
    has_capability_coverage: true
  - attack_technique: T1486
    exposed_by_finding_count: 1
    exposed_by_finding_ids: [intg-9f8e7d6c]
    countered_by_d3fend: []
    countered_by_capability_ids: []
    has_capability_coverage: false
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL.

- [ ] **Step 3: Create the schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/d3fend-coverage.schema.json",
  "title": "APD Gauntlet D3FEND Coverage Rollup",
  "type": "object",
  "required": ["schema_version", "generated_by", "defensive_entries", "counter_coverage"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["synthesizer"] },
    "defensive_entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["d3fend_id", "name", "capability_count", "capability_ids", "counters_attack"],
        "additionalProperties": false,
        "properties": {
          "d3fend_id":         { "type": "string", "pattern": "^D3-[A-Z]{2,5}$" },
          "name":              { "type": "string", "minLength": 3 },
          "capability_count":  { "type": "integer", "minimum": 0 },
          "capability_ids":    { "type": "array", "items": { "type": "string" } },
          "counters_attack":   { "type": "array", "items": { "type": "string", "pattern": "^T[0-9]{4}(\\.[0-9]{3})?$" } }
        }
      }
    },
    "counter_coverage": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["attack_technique", "exposed_by_finding_count", "exposed_by_finding_ids", "countered_by_d3fend", "countered_by_capability_ids", "has_capability_coverage"],
        "additionalProperties": false,
        "properties": {
          "attack_technique":             { "type": "string", "pattern": "^T[0-9]{4}(\\.[0-9]{3})?$" },
          "exposed_by_finding_count":     { "type": "integer", "minimum": 0 },
          "exposed_by_finding_ids":       { "type": "array", "items": { "type": "string" } },
          "countered_by_d3fend":          { "type": "array", "items": { "type": "string", "pattern": "^D3-[A-Z]{2,5}$" } },
          "countered_by_capability_ids":  { "type": "array", "items": { "type": "string" } },
          "has_capability_coverage":      { "type": "boolean" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 6: Commit**

```bash
git add schemas/d3fend-coverage.schema.json tests/test_other_schemas.py tests/fixtures/rollups/d3fend-coverage-valid.yaml
git commit -m "feat(schema): add d3fend-coverage rollup schema with counter-coverage view"
```

---

## Task 8: Refresh script for CWE — `refresh_cwe.py` + initial reference data

**Goal:** Python module that fetches MITRE CWE XML, projects to a compact JSON shape, writes to `tools/apd_gauntlet/data/cwe.json` with `source_sha256` and `fetched_at`. Mirrors `refresh_mitre.py` security hardening (timeout=60s, max=200 MiB, no shell-injection).

**Files:**

- Create: `tools/apd_gauntlet/refresh_cwe.py`
- Create: `tools/apd_gauntlet/data/cwe.json` (initial seeded copy committed to repo so first-time install has working data)
- Create: `tests/test_refresh_cwe.py`

**CWE source:** MITRE publishes a comprehensive CWE XML at `https://cwe.mitre.org/data/xml/cwec_latest.xml.zip` (~5 MB). The projection extracts: id, name, abstraction, parent IDs, demonstrative_examples_present, observed_examples_present.

- [ ] **Step 1: Write failing tests**

Create `tests/test_refresh_cwe.py`:

```python
import hashlib
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from apd_gauntlet.refresh_cwe import (
    fetch_cwe_xml,
    project_cwe_xml_to_json,
    refresh_cwe,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
)


def test_refresh_cwe_timeout_constant_is_60s():
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_refresh_cwe_size_cap_is_200_mib():
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_project_extracts_required_fields(sample_cwe_xml_bytes):
    """sample_cwe_xml_bytes is a tiny fixture XML with 2 weaknesses."""
    projected = project_cwe_xml_to_json(sample_cwe_xml_bytes)
    assert "entries" in projected
    assert "source_sha256" in projected
    assert "fetched_at" in projected
    assert len(projected["entries"]) == 2
    entry = projected["entries"][0]
    assert set(entry.keys()) >= {"cwe_id", "name", "abstraction"}
    # source_sha256 matches actual content
    assert projected["source_sha256"] == hashlib.sha256(sample_cwe_xml_bytes).hexdigest()


def test_fetch_cwe_xml_passes_timeout(mock_urlopen):
    fetch_cwe_xml()
    args, kwargs = mock_urlopen.call_args
    assert kwargs.get("timeout") == 60


def test_fetch_cwe_xml_rejects_oversize_response():
    """Mock urlopen to return a response that claims Content-Length > 200 MiB."""
    with patch("apd_gauntlet.refresh_cwe.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(201 * 1024 * 1024)}
        mock.return_value.__enter__.return_value = response
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_cwe_xml()


def test_refresh_cwe_writes_to_data_dir(tmp_path, sample_cwe_xml_bytes):
    """End-to-end: refresh_cwe writes a valid JSON to the target path."""
    with patch("apd_gauntlet.refresh_cwe.fetch_cwe_xml", return_value=sample_cwe_xml_bytes):
        target = tmp_path / "cwe.json"
        refresh_cwe(output_path=target)
        assert target.exists()
        data = json.loads(target.read_text())
        assert data["source_sha256"] == hashlib.sha256(sample_cwe_xml_bytes).hexdigest()


@pytest.fixture
def sample_cwe_xml_bytes():
    """Two-weakness fixture XML matching the CWE 4.x schema shape."""
    return Path("tests/fixtures/reference_data/cwe-sample.xml").read_bytes()


@pytest.fixture
def mock_urlopen(sample_cwe_xml_bytes):
    with patch("apd_gauntlet.refresh_cwe.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(sample_cwe_xml_bytes))}
        response.read.return_value = sample_cwe_xml_bytes
        mock.return_value.__enter__.return_value = response
        yield mock
```

Create `tests/fixtures/reference_data/cwe-sample.xml` — a minimal CWE XML with two `<Weakness>` elements matching the schema shape (use the actual MITRE CWE 4.x DTD; the engineer can fetch a real CWE XML and trim it). Two weaknesses are enough.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_refresh_cwe.py -v`
Expected: FAIL — `apd_gauntlet.refresh_cwe` doesn't exist yet.

- [ ] **Step 3: Implement `tools/apd_gauntlet/refresh_cwe.py`**

```python
"""Refresh MITRE CWE reference data for the apd-gauntlet."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen
from xml.etree import ElementTree as ET

CWE_XML_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB

# CWE 4.x XML namespace
NS = {"cwe": "http://cwe.mitre.org/cwe-7"}


def fetch_cwe_xml() -> bytes:
    """Fetch and unzip the latest CWE XML. Returns raw XML bytes."""
    with urlopen(CWE_XML_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
            raise ValueError(
                f"CWE XML response Content-Length ({content_length}) exceeds maximum ({MAX_RESPONSE_BYTES})"
            )
        zipped = response.read(MAX_RESPONSE_BYTES + 1)
        if len(zipped) > MAX_RESPONSE_BYTES:
            raise ValueError("CWE XML response exceeds maximum allowed size")
    with zipfile.ZipFile(io.BytesIO(zipped)) as zf:
        xml_name = next(name for name in zf.namelist() if name.endswith(".xml"))
        return zf.read(xml_name)


def project_cwe_xml_to_json(xml_bytes: bytes) -> dict[str, Any]:
    """Project CWE XML into compact JSON for runtime consumption."""
    root = ET.fromstring(xml_bytes)
    entries: list[dict[str, Any]] = []
    for weakness in root.iter("{http://cwe.mitre.org/cwe-7}Weakness"):
        cwe_id = weakness.get("ID")
        name = weakness.get("Name") or ""
        abstraction = (weakness.get("Abstraction") or "").lower()
        parents = [
            rel.get("CWE_ID")
            for rel in weakness.iter("{http://cwe.mitre.org/cwe-7}Related_Weakness")
            if rel.get("Nature") == "ChildOf"
        ]
        has_demo = weakness.find("{http://cwe.mitre.org/cwe-7}Demonstrative_Examples") is not None
        has_obs = weakness.find("{http://cwe.mitre.org/cwe-7}Observed_Examples") is not None
        entries.append({
            "cwe_id": f"CWE-{cwe_id}",
            "name": name,
            "abstraction": abstraction,
            "parents": [f"CWE-{p}" for p in parents if p],
            "demonstrative_examples_present": has_demo,
            "observed_examples_present": has_obs,
        })
    return {
        "source_sha256": hashlib.sha256(xml_bytes).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_url": CWE_XML_URL,
        "entries": entries,
    }


def refresh_cwe(output_path: Path | None = None) -> Path:
    """Fetch, project, and write CWE reference data. Returns the output path."""
    if output_path is None:
        output_path = Path(__file__).parent / "data" / "cwe.json"
    xml_bytes = fetch_cwe_xml()
    projected = project_cwe_xml_to_json(xml_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True))
    return output_path


if __name__ == "__main__":
    path = refresh_cwe()
    print(f"Wrote {path}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_refresh_cwe.py -v`
Expected: PASS.

- [ ] **Step 5: Ship initial `data/cwe.json`**

Run the refresh script once against live MITRE to seed the repo with current data:

```bash
python -m apd_gauntlet.refresh_cwe
```

If MITRE is unreachable at plan-execution time, commit a minimal seed file with 5–10 commonly-referenced CWEs (CWE-79, CWE-89, CWE-200, CWE-287, CWE-306, CWE-319, CWE-352, CWE-434, CWE-502, CWE-798) using the same schema shape; document the partial-seed status in the file's `source_url` field as `"seed_only"`.

- [ ] **Step 6: Run full suite + linters + mypy**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/refresh_cwe.py tools/apd_gauntlet/data/cwe.json tests/test_refresh_cwe.py tests/fixtures/reference_data/cwe-sample.xml
git commit -m "feat: refresh_cwe script + seeded CWE reference data"
```

---

## Task 9: Refresh script for OWASP — `refresh_owasp.py` + initial reference data

**Goal:** One module that fetches three OWASP Top 10 lists (web, API, LLM) and projects each to JSON. Same security hardening as `refresh_cwe`. Edition versioning preserved (a finding mapped to A03:2021 stays A03:2021 even after A03:2024 ships).

**Sources** (GitHub-hosted JSONs maintained by the OWASP project; URLs may need verification at execution time):

- Top 10 (web): `https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/A00_2021.json` (or whichever consolidated source the OWASP project currently maintains; engineer should verify at execution time)
- API Top 10: `https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xx-introduction.json` (similar — verify at execution time)
- LLM Top 10: `https://raw.githubusercontent.com/OWASP/www-project-top-10-for-large-language-model-applications/main/2_0_vulns/translations/en-US/LLM01_PromptInjection.md` etc. (the LLM project ships per-category markdown; engineer parses titles + IDs)

If live sources are unreachable or the engineer determines the URLs above are out of date, seed `data/owasp_*.json` from the current published edition by hand (10 categories per list = 30 entries total — small) and document the seed approach in each file's `source_url` field.

**Files:**

- Create: `tools/apd_gauntlet/refresh_owasp.py`
- Create: `tools/apd_gauntlet/data/owasp_top10.json`
- Create: `tools/apd_gauntlet/data/owasp_api_top10.json`
- Create: `tools/apd_gauntlet/data/owasp_llm_top10.json`
- Create: `tests/test_refresh_owasp.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_refresh_owasp.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from apd_gauntlet.refresh_owasp import (
    refresh_owasp,
    fetch_owasp_top10,
    fetch_owasp_api_top10,
    fetch_owasp_llm_top10,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
)


def test_owasp_timeout_constant_is_60s():
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_owasp_size_cap_is_200_mib():
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_refresh_owasp_writes_three_files(tmp_path):
    fake_categories = [
        {"category_id": "A03:2021", "name": "Injection"},
        {"category_id": "A05:2021", "name": "Security Misconfiguration"},
    ]
    fake_api = [{"category_id": "API3:2023", "name": "Broken Object Property Level Authorization"}]
    fake_llm = [{"category_id": "LLM01", "name": "Prompt Injection"}]
    with (
        patch("apd_gauntlet.refresh_owasp.fetch_owasp_top10", return_value=fake_categories),
        patch("apd_gauntlet.refresh_owasp.fetch_owasp_api_top10", return_value=fake_api),
        patch("apd_gauntlet.refresh_owasp.fetch_owasp_llm_top10", return_value=fake_llm),
    ):
        paths = refresh_owasp(output_dir=tmp_path)
        assert (tmp_path / "owasp_top10.json").exists()
        assert (tmp_path / "owasp_api_top10.json").exists()
        assert (tmp_path / "owasp_llm_top10.json").exists()
        data = json.loads((tmp_path / "owasp_top10.json").read_text())
        assert "source_sha256" in data
        assert "fetched_at" in data
        assert data["entries"][0]["category_id"] == "A03:2021"


def test_refresh_owasp_preserves_edition_in_category_id(tmp_path):
    fake = [{"category_id": "A03:2021", "name": "Injection"}]
    with (
        patch("apd_gauntlet.refresh_owasp.fetch_owasp_top10", return_value=fake),
        patch("apd_gauntlet.refresh_owasp.fetch_owasp_api_top10", return_value=[]),
        patch("apd_gauntlet.refresh_owasp.fetch_owasp_llm_top10", return_value=[]),
    ):
        refresh_owasp(output_dir=tmp_path)
        data = json.loads((tmp_path / "owasp_top10.json").read_text())
        assert data["entries"][0]["category_id"] == "A03:2021"  # edition year preserved
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Implement `tools/apd_gauntlet/refresh_owasp.py`**

```python
"""Refresh OWASP Top 10 (web / API / LLM) reference data for the apd-gauntlet."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

DEFAULT_TIMEOUT_SECONDS = 60
MAX_RESPONSE_BYTES = 200 * 1024 * 1024

# Engineer: verify these URLs at execution time; OWASP project may have moved them.
OWASP_TOP10_URL = "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/categories.json"
OWASP_API_TOP10_URL = "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/categories.json"
OWASP_LLM_TOP10_URL = "https://raw.githubusercontent.com/OWASP/www-project-top-10-for-large-language-model-applications/main/categories.json"


def _fetch_json(url: str) -> Any:
    """Fetch a JSON document with the standard timeout + size cap."""
    with urlopen(url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
            raise ValueError(f"OWASP response from {url} exceeds maximum ({MAX_RESPONSE_BYTES})")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"OWASP response from {url} exceeds maximum allowed size")
    return body, json.loads(body)


def fetch_owasp_top10() -> list[dict[str, Any]]:
    """Fetch OWASP Top 10 (web). Returns list of {category_id, name}."""
    _, data = _fetch_json(OWASP_TOP10_URL)
    return [{"category_id": entry["id"], "name": entry["title"]} for entry in data.get("categories", [])]


def fetch_owasp_api_top10() -> list[dict[str, Any]]:
    _, data = _fetch_json(OWASP_API_TOP10_URL)
    return [{"category_id": entry["id"], "name": entry["title"]} for entry in data.get("categories", [])]


def fetch_owasp_llm_top10() -> list[dict[str, Any]]:
    _, data = _fetch_json(OWASP_LLM_TOP10_URL)
    return [{"category_id": entry["id"], "name": entry["title"]} for entry in data.get("categories", [])]


def _write_projected(entries: list[dict[str, Any]], url: str, output_path: Path) -> None:
    body = json.dumps(entries, sort_keys=True).encode("utf-8")
    projected = {
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_url": url,
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True))


def refresh_owasp(output_dir: Path | None = None) -> dict[str, Path]:
    """Fetch all three OWASP lists; write to data/owasp_*.json. Returns paths dict."""
    if output_dir is None:
        output_dir = Path(__file__).parent / "data"
    paths = {
        "top10":     output_dir / "owasp_top10.json",
        "api_top10": output_dir / "owasp_api_top10.json",
        "llm_top10": output_dir / "owasp_llm_top10.json",
    }
    _write_projected(fetch_owasp_top10(),     OWASP_TOP10_URL,     paths["top10"])
    _write_projected(fetch_owasp_api_top10(), OWASP_API_TOP10_URL, paths["api_top10"])
    _write_projected(fetch_owasp_llm_top10(), OWASP_LLM_TOP10_URL, paths["llm_top10"])
    return paths


if __name__ == "__main__":
    for name, path in refresh_owasp().items():
        print(f"Wrote {name}: {path}")
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS.

- [ ] **Step 5: Seed `data/owasp_*.json`**

Either run `python -m apd_gauntlet.refresh_owasp` against live OWASP sources, or hand-seed all three files with the published categories from the current editions. Each file's `entries[]` is the full taxonomy (10 entries per list).

- [ ] **Step 6: Run full suite + linters**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/refresh_owasp.py tools/apd_gauntlet/data/owasp_top10.json tools/apd_gauntlet/data/owasp_api_top10.json tools/apd_gauntlet/data/owasp_llm_top10.json tests/test_refresh_owasp.py
git commit -m "feat: refresh_owasp script + seeded OWASP Top 10 / API / LLM reference data"
```

---

## Task 10: Refresh script for D3FEND — `refresh_d3fend.py` + initial reference data

**Goal:** Module that fetches the D3FEND ontology (OWL/JSON-LD), projects to a compact JSON shape preserving D3FEND ID, name, tactic, and the `counters_attack` cross-reference table. Same security hardening.

**Source:** MITRE D3FEND publishes JSON-LD at `https://d3fend.mitre.org/api/ontology/inference/d3fend-full-mappings.json`. Each technique has `d3fend:Technique` records with `d3fend:d3f-counters` relations to ATT&CK technique IDs.

**Files:**

- Create: `tools/apd_gauntlet/refresh_d3fend.py`
- Create: `tools/apd_gauntlet/data/d3fend.json`
- Create: `tests/test_refresh_d3fend.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_refresh_d3fend.py` mirroring the pattern from `test_refresh_cwe.py`: `timeout=60s`, `max=200 MiB`, projection extracts D3FEND ID + name + counters_attack list, source_sha256 set.

```python
def test_d3fend_timeout_constant_is_60s():
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_d3fend_size_cap_is_200_mib():
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


def test_project_extracts_d3fend_entries_with_counter_mappings(sample_d3fend_json_bytes):
    projected = project_d3fend_json(sample_d3fend_json_bytes)
    assert "entries" in projected
    assert "source_sha256" in projected
    entry = next(e for e in projected["entries"] if e["d3fend_id"] == "D3-NTA")
    assert entry["name"]
    assert "T1078" in entry["counters_attack"]


def test_refresh_d3fend_writes_to_data_dir(tmp_path, sample_d3fend_json_bytes):
    with patch("apd_gauntlet.refresh_d3fend.fetch_d3fend_json", return_value=sample_d3fend_json_bytes):
        target = tmp_path / "d3fend.json"
        refresh_d3fend(output_path=target)
        assert target.exists()
        data = json.loads(target.read_text())
        assert data["source_sha256"] == hashlib.sha256(sample_d3fend_json_bytes).hexdigest()
```

Fixture `tests/fixtures/reference_data/d3fend-sample.json`: minimal JSON-LD with 2–3 D3FEND techniques and their counter-mappings, matching the live API shape.

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL.

- [ ] **Step 3: Implement `tools/apd_gauntlet/refresh_d3fend.py`**

```python
"""Refresh MITRE D3FEND reference data for the apd-gauntlet."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

D3FEND_JSON_URL = "https://d3fend.mitre.org/api/ontology/inference/d3fend-full-mappings.json"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_RESPONSE_BYTES = 200 * 1024 * 1024


def fetch_d3fend_json() -> bytes:
    with urlopen(D3FEND_JSON_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
            raise ValueError(f"D3FEND response Content-Length ({content_length}) exceeds maximum")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("D3FEND response exceeds maximum allowed size")
    return body


def project_d3fend_json(json_bytes: bytes) -> dict[str, Any]:
    """Project D3FEND JSON-LD into a compact runtime shape."""
    data = json.loads(json_bytes)
    entries: dict[str, dict[str, Any]] = {}

    # Engineer: the exact shape of the live D3FEND JSON-LD may evolve.
    # The pattern is: each Technique node has @id (D3FEND IRI), label, and
    # d3f-counters relations pointing to ATT&CK technique IRIs.
    for node in data.get("@graph", []):
        ntype = node.get("@type")
        if ntype != "d3fend:Technique" and "d3fend:Technique" not in (ntype if isinstance(ntype, list) else [ntype]):
            continue
        iri = node.get("@id", "")
        d3fend_id = _iri_to_d3fend_id(iri, node=node)
        if not d3fend_id:
            continue
        name = _label(node)
        counters = []
        for relation in node.get("d3fend:d3f-counters", []) or []:
            attack_iri = relation.get("@id") if isinstance(relation, dict) else relation
            attack_id = _iri_to_attack_id(attack_iri)
            if attack_id:
                counters.append(attack_id)
        entries[d3fend_id] = {
            "d3fend_id": d3fend_id,
            "name": name,
            "counters_attack": sorted(set(counters)),
        }

    return {
        "source_sha256": hashlib.sha256(json_bytes).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_url": D3FEND_JSON_URL,
        "entries": sorted(entries.values(), key=lambda e: e["d3fend_id"]),
    }


def _iri_to_d3fend_id(iri: str, node: dict[str, Any] | None = None) -> str | None:
    """Extract 'D3-NTA' style short code from a D3FEND IRI or node.

    Strategy (in order):
      1. If the node exposes a `d3fend:d3f-id` property, use it.
      2. If the IRI's last path-segment already matches `D3-XXX`, use it.
      3. Walk a name-to-code map seeded from the live D3FEND ontology
         (e.g., 'NetworkTrafficAnalysis' -> 'D3-NTA').
    """
    if node is not None:
        explicit = node.get("d3fend:d3f-id") or node.get("d3f:d3f-id")
        if isinstance(explicit, str) and explicit.startswith("D3-"):
            return explicit
    if not iri:
        return None
    last = iri.rsplit(":", 1)[-1].rsplit("/", 1)[-1]
    if last.startswith("D3-"):
        return last
    return _LONG_NAME_TO_SHORT_CODE.get(last)


# Seeded from the public D3FEND ontology. The refresh script supplements this
# from the live JSON-LD when fresh data is available; the seed covers the
# techniques most commonly cited in healthcare/PBM defensive architectures.
_LONG_NAME_TO_SHORT_CODE: dict[str, str] = {
    "NetworkTrafficAnalysis":           "D3-NTA",
    "FileAnalysis":                     "D3-FA",
    "FileEncryption":                   "D3-FE",
    "FileHashing":                      "D3-FH",
    "MessageEncryption":                "D3-MENCR",
    "MultiFactorAuthentication":        "D3-MFA",
    "NetworkIsolation":                 "D3-NI",
    "ResourceAccessControl":            "D3-RAC",
    "StrongPasswordPolicy":             "D3-SPP",
    "SystemConfigurationPermissions":   "D3-SCP",
    "InboundTrafficFiltering":          "D3-ITF",
    "OutboundTrafficFiltering":         "D3-OTF",
    "BackupRecoveryAndIntegrityAnalysis": "D3-FBA",
    "ProcessAnalysis":                  "D3-PA",
    "AuthenticationEventThresholding":  "D3-ANET",
}


def _iri_to_attack_id(iri: str | None) -> str | None:
    """Extract 'T1078' from an ATT&CK IRI like 'attack:T1078'."""
    if not iri:
        return None
    last = iri.rsplit(":", 1)[-1].rsplit("/", 1)[-1]
    if last.startswith("T") and len(last) >= 5 and last[1:5].isdigit():
        return last
    return None


def _label(node: dict[str, Any]) -> str:
    label = node.get("rdfs:label") or node.get("label") or ""
    if isinstance(label, dict):
        return label.get("@value", "")
    if isinstance(label, list):
        for item in label:
            if isinstance(item, str):
                return item
            if isinstance(item, dict) and "@value" in item:
                return item["@value"]
    return label if isinstance(label, str) else ""


def refresh_d3fend(output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).parent / "data" / "d3fend.json"
    json_bytes = fetch_d3fend_json()
    projected = project_d3fend_json(json_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True))
    return output_path


if __name__ == "__main__":
    print(f"Wrote {refresh_d3fend()}")
```

Note: `_iri_to_d3fend_id` is left as a placeholder for the engineer to fill in based on the live D3FEND JSON-LD shape — this is one of the few unknowns in this plan and requires verifying against the actual API response. If the live API is unreachable, hand-seed `data/d3fend.json` with ~30 commonly-cited D3FEND techniques (D3-NTA, D3-ANCI, D3-FA, D3-FBA, D3-FE, D3-FH, D3-IRA, D3-MENCR, D3-MFA, D3-NI, D3-NTF, D3-PA, D3-RAC, D3-RKD, D3-SAOR, D3-SCF, D3-SDA, D3-SEA, D3-SFA, D3-SU, etc.) with their `counters_attack` lists pulled from the D3FEND web UI.

- [ ] **Step 4: Run tests to verify they pass**

Expected: PASS (with sample fixture). The `_iri_to_d3fend_id` placeholder must be implemented enough for the sample-fixture tests to pass — even if the live API isn't yet fully wired up.

- [ ] **Step 5: Seed `data/d3fend.json`**

Run `python -m apd_gauntlet.refresh_d3fend` or hand-seed per the fallback above.

- [ ] **Step 6: Run full suite + linters**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/refresh_d3fend.py tools/apd_gauntlet/data/d3fend.json tests/test_refresh_d3fend.py tests/fixtures/reference_data/d3fend-sample.json
git commit -m "feat: refresh_d3fend script + seeded D3FEND reference data with counters_attack mappings"
```

---

## Task 11: CLI subcommands `refresh-cwe`, `refresh-owasp`, `refresh-d3fend`

**Goal:** Expose three new `apd-gauntlet` subcommands that wrap the refresh modules, mirroring the existing `refresh-mitre` subcommand pattern.

**Files:**

- Modify: `tools/apd_gauntlet/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

In `tests/test_cli.py`, add:

```python
from unittest.mock import patch

def test_cli_refresh_cwe_invokes_refresh(cli_runner):
    with patch("apd_gauntlet.cli.refresh_cwe") as mock:
        mock.return_value = Path("/tmp/cwe.json")
        result = cli_runner.invoke(main, ["refresh-cwe"])
        assert result.exit_code == 0
        mock.assert_called_once()

def test_cli_refresh_owasp_invokes_refresh(cli_runner):
    with patch("apd_gauntlet.cli.refresh_owasp") as mock:
        mock.return_value = {
            "top10": Path("/tmp/owasp_top10.json"),
            "api_top10": Path("/tmp/owasp_api_top10.json"),
            "llm_top10": Path("/tmp/owasp_llm_top10.json"),
        }
        result = cli_runner.invoke(main, ["refresh-owasp"])
        assert result.exit_code == 0
        mock.assert_called_once()

def test_cli_refresh_d3fend_invokes_refresh(cli_runner):
    with patch("apd_gauntlet.cli.refresh_d3fend") as mock:
        mock.return_value = Path("/tmp/d3fend.json")
        result = cli_runner.invoke(main, ["refresh-d3fend"])
        assert result.exit_code == 0
        mock.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v -k "refresh_cwe or refresh_owasp or refresh_d3fend"`
Expected: FAIL — subcommands don't exist.

- [ ] **Step 3: Add subcommands to `tools/apd_gauntlet/cli.py`**

Locate the existing `refresh-mitre` subcommand. Add three parallel subcommands:

```python
from apd_gauntlet.refresh_cwe import refresh_cwe
from apd_gauntlet.refresh_owasp import refresh_owasp
from apd_gauntlet.refresh_d3fend import refresh_d3fend

@main.command("refresh-cwe")
def refresh_cwe_cmd() -> None:
    """Refresh MITRE CWE reference data (writes to package data dir)."""
    path = refresh_cwe()
    click.echo(f"Wrote {path}")


@main.command("refresh-owasp")
def refresh_owasp_cmd() -> None:
    """Refresh OWASP Top 10 / API Top 10 / LLM Top 10 reference data."""
    for name, path in refresh_owasp().items():
        click.echo(f"Wrote {name}: {path}")


@main.command("refresh-d3fend")
def refresh_d3fend_cmd() -> None:
    """Refresh MITRE D3FEND reference data."""
    path = refresh_d3fend()
    click.echo(f"Wrote {path}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Manual smoke-test (optional — only if live sources reachable)**

```bash
apd-gauntlet refresh-cwe --help    # confirm subcommand registered
apd-gauntlet refresh-owasp --help
apd-gauntlet refresh-d3fend --help
```

- [ ] **Step 6: Run full suite + linters**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli.py
git commit -m "feat(cli): add refresh-cwe, refresh-owasp, refresh-d3fend subcommands"
```

---

## Task 12: Update `apd-control-mappings` skill with per-taxonomy discipline

**Goal:** Extend the existing `.claude/skills/apd-control-mappings/SKILL.md` with five new discipline sections (CWE, OWASP Top 10 web, OWASP API, OWASP LLM, D3FEND). Same authority style as the existing NIST 800-53r5 and ATT&CK sections.

**Files:**

- Modify: `.claude/skills/apd-control-mappings/SKILL.md`

- [ ] **Step 1: Read the existing skill to understand its current shape**

```bash
cat .claude/skills/apd-control-mappings/SKILL.md
```

- [ ] **Step 2: Add a "Per-taxonomy discipline" section**

Append the following section to the skill, after the existing NIST/ATT&CK guidance:

```markdown
## Per-taxonomy discipline (v1.2+)

A run may declare additional taxonomies in `.apd-run.yaml` (`taxonomies: [cwe, owasp_top10, owasp_api_top10, owasp_llm_top10, d3fend]`). The intake brief lists which are in scope plus any taxonomies intake auto-suggested. **Only emit mappings for taxonomies declared in the run.** Auto-suggestions that the operator did not adopt do not authorize emission.

### CWE (on findings, optional)

- Map only when the finding describes a specific weakness pattern that matches a CWE entry's **Demonstrative Examples** or **Observed Examples**.
- Use **base** or **variant** abstractions only. **Pillar** and **category** entries (e.g., CWE-693 "Protection Mechanism Failure") are too abstract for actionable mapping and must not be used.
- Each `cwe` mapping is just the ID string (no rationale field on the schema — but the finding's `detail` text must justify the weakness-pattern match. Reviewers should be able to read the detail and see why CWE-79 applies.)
- One finding may carry multiple CWE IDs when the weakness composes.

### OWASP Top 10 (web — on findings, optional)

- Map only when the SUT has a web surface (HTML routes, browser-rendered templates, session cookies). Intake auto-suggests this taxonomy when those surfaces are detected.
- Use the current edition format `A<NN>:<YYYY>` (e.g., A03:2021). Do not silently re-map findings to newer editions when they ship — the edition year is part of the ID.
- Limit one OWASP Top 10 ID per finding except when the finding genuinely spans categories (e.g., a single misconfiguration that's both A05 and A07). Multiple IDs require the `detail` text to walk through each.

### OWASP API Top 10 (on findings, optional)

- Map when the SUT exposes an API (OpenAPI/Swagger spec, REST/GraphQL endpoints, API gateway config).
- Format `API<N>:<YYYY>` (e.g., API3:2023).
- Same per-finding multiplicity discipline as OWASP Top 10.

### OWASP LLM Top 10 (on findings, optional)

- Map only when the SUT integrates an LLM (SDK imports of `openai`, `anthropic`, `langchain`, etc.; vector store usage; prompt templates).
- Format `LLM<NN>` (e.g., LLM01).
- LLM01 (Prompt Injection), LLM06 (Sensitive Information Disclosure), LLM07 (Insecure Plugin Design) are most often-cited; map only when the finding actually describes the categorized risk pattern.

### D3FEND (on capabilities, optional)

- D3FEND attaches to **capabilities**, not findings. A capability earns a D3FEND mapping when its design demonstrably implements the technique.
- Each D3FEND entry **must** cite which ATT&CK techniques it counters via `counters_attack`. The cited ATT&CK technique(s) must also appear in the same capability's `mitre_attack` block. Schema validates the format; cross-reference is checked by the validator. Map-by-name-similarity is forbidden.
- Each D3FEND entry requires `rationale` (≥30 chars) explaining how the capability implements the D3FEND technique.
- Use the format `D3-<short_code>` (e.g., D3-NTA for Network Traffic Analysis). Reference data is at `tools/apd_gauntlet/data/d3fend.json`.

## High-confidence-only rule (extends unchanged)

The existing high-confidence-only rule applies to all five new taxonomies. When uncertain whether a CWE matches the weakness pattern, when uncertain whether the SUT actually exposes the OWASP-categorized surface, when uncertain whether a capability truly implements a D3FEND technique — **do not map**. Leave the field absent.
```

- [ ] **Step 3: Run skill validation (if a linter exists) and the lint-agents check**

```bash
apd-gauntlet lint-agents     # confirms agent frontmatter still clean (no skill validation today)
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/apd-control-mappings/SKILL.md
git commit -m "feat(skill): apd-control-mappings gains per-taxonomy discipline for CWE/OWASP/D3FEND"
```

---

## Task 13: Update `apd-intake.md` agent — emit `taxonomy_suggestions` block

**Goal:** Extend the intake agent's authoring contract to inspect supplied artifacts and write a `taxonomy_suggestions:` block into its context brief, distinguishing taxonomies declared in run-config from taxonomies intake auto-detects as relevant. Specialists honor only the operator-accepted set (declared in run-config) — auto-suggestions are advisory.

**Files:**

- Modify: `.claude/agents/apd-intake.md`
- Modify: `templates/context-brief.template.md`
- Modify: `tests/test_lint_agents.py` (extend frontmatter / contract checks if needed)

- [ ] **Step 1: Read existing intake agent and context-brief template**

```bash
cat .claude/agents/apd-intake.md
cat templates/context-brief.template.md
```

- [ ] **Step 2: Add taxonomy-detection responsibility to the agent**

In `.claude/agents/apd-intake.md`, add a new step to the **Process** section (after the existing data-inventory step):

```markdown
### 6. Taxonomy scope and auto-detection (v1.2+)

Read the `taxonomies:` list from `.apd-run.yaml` (may be absent — defaults to `[]` if so).

Inspect the supplied artifacts for surfaces that suggest additional taxonomies the run did not declare. Heuristics:

- **owasp_top10** — declare-or-suggest if you see: HTML templates, browser-targeted routes, session cookies, CSRF tokens, web framework imports (Django, Flask, Rails, Express, Next.js).
- **owasp_api_top10** — declare-or-suggest if you see: OpenAPI/Swagger spec, REST endpoint declarations, GraphQL schema, API gateway config, JWT bearer auth on HTTP endpoints.
- **owasp_llm_top10** — declare-or-suggest if you see: `openai` / `anthropic` / `langchain` / `llama-index` SDK imports, prompt template files (`*.prompt`, `*.tmpl`), vector store usage (Pinecone, Weaviate, Chroma), LLM-tool-use patterns.
- **cwe**, **mitre_attack**, **d3fend** — default-on; do not suggest (they're always-on unless the operator explicitly removed them from `taxonomies:`).

Write the result into the context brief as a `taxonomy_suggestions:` block (see template). Specialists are bound by the operator-accepted scope (i.e., what's in `taxonomies:` at run time) — auto-suggestions are advisory only and must not drive specialist mappings unless the operator re-runs with them added.
```

- [ ] **Step 3: Update the context-brief template**

In `templates/context-brief.template.md`, add a section:

```markdown
## Taxonomy scope (v1.2+)

declared_in_run_config: [...]   # from .apd-run.yaml taxonomies: list

suggested_additional:
  - taxonomy: <name>
    reason:   "<one-sentence evidence from artifacts>"
    artifact: "<artifact path or null>"
```

If `taxonomies:` is absent or empty in run-config and intake found no surfaces warranting suggestion, render the section as:

```markdown
## Taxonomy scope (v1.2+)

declared_in_run_config: []
suggested_additional: []
note: "No taxonomies declared and no surfaces detected warranting suggestion."
```

- [ ] **Step 4: Add lint test for the new contract**

In `tests/test_lint_agents.py` (or wherever frontmatter / contract checks live), ensure the intake agent file is checked by the existing lint pass. No new test logic required if the lint pass is content-agnostic — it should already validate the file structure.

If lint-agents has a contract section that lists required process-step headings, extend it to require the new "Taxonomy scope and auto-detection" step on `apd-intake.md`.

- [ ] **Step 5: Run lint-agents and test suite**

```bash
apd-gauntlet lint-agents
pytest -q
```

Expected: lint-agents passes; tests pass.

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/apd-intake.md templates/context-brief.template.md tests/test_lint_agents.py
git commit -m "feat(agent): apd-intake emits taxonomy_suggestions block with auto-detect heuristics"
```

---

## Task 14: Update `apd-synthesizer.md` agent — emit new coverage rollups

**Goal:** Extend the synthesizer's authoring contract to emit three new rollup artifacts (`cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`) into `40-synthesis/` when the relevant taxonomies are declared in run-config and findings/capabilities carry the relevant mappings.

**Files:**

- Modify: `.claude/agents/apd-synthesizer.md`
- Modify: `templates/advisory-report.template.md`
- Modify: `tests/test_lint_agents.py` (if needed)

- [ ] **Step 1: Read existing synthesizer**

```bash
cat .claude/agents/apd-synthesizer.md
```

- [ ] **Step 2: Add three new rollup outputs to the synthesizer**

In `.claude/agents/apd-synthesizer.md`, extend the **Outputs** section:

```markdown
## Outputs (v1.2+ additions)

The synthesizer emits the existing rollups (`nist-coverage.yaml`, `attack-exposure.yaml`, `coverage-matrix.yaml`, plus advisory report and annexes), and additionally when the run declares the relevant taxonomies:

- **`40-synthesis/cwe-coverage.yaml`** — emitted when `cwe` is declared in run-config and any finding carries a `control_mappings.cwe[]` value. Validates against `schemas/cwe-coverage.schema.json`. Group entries by CWE ID; populate `parent_pillar` from the projected reference data at `tools/apd_gauntlet/data/cwe.json` when available; list `surfaces` derived from the finding's evidence locators.

- **`40-synthesis/owasp-coverage.yaml`** — emitted when any of `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10` is declared and any finding carries the corresponding mapping. Validates against `schemas/owasp-coverage.schema.json`. One entry per (taxonomy, category_id) pair. Categories never touched by a finding are emitted with `silent: true` to make coverage gaps explicit.

- **`40-synthesis/d3fend-coverage.yaml`** — emitted when `d3fend` is declared and any capability carries `control_mappings.d3fend[]`. Validates against `schemas/d3fend-coverage.schema.json`. Includes both the `defensive_entries` (D3FEND techniques implemented by capabilities) and the `counter_coverage` view (for each ATT&CK technique exposed by a finding, list which D3FEND-backed capabilities counter it — or `has_capability_coverage: false` if none do). The `counter_coverage` view feeds Phase C bottleneck analysis.

Discipline:
- Rollup an entry only when at least one finding (or capability for D3FEND) cites it; do not synthesize coverage from reference data alone.
- `silent: true` entries in OWASP coverage exist to make absence visible to reviewers; reference the full taxonomy from `tools/apd_gauntlet/data/owasp_*.json`.
- Never invent CWE/OWASP/D3FEND mappings — only roll up what specialists emitted.
```

- [ ] **Step 3: Update the advisory-report template**

In `templates/advisory-report.template.md`, add a new top-level section (after the existing rollup references):

```markdown
## Framework Coverage (v1.2+, when declared)

### CWE coverage

Linked rollup: `40-synthesis/cwe-coverage.yaml`. Lists CWE IDs touched by findings, grouped by abstraction (base/variant) and parent pillar. Use this view to communicate developer-facing weakness exposure.

### OWASP coverage

Linked rollup: `40-synthesis/owasp-coverage.yaml`. Lists OWASP Top 10 / API / LLM categories with finding count and `silent: true` entries marking absence. Use this view for reviewer-facing risk summary aligned to industry-standard taxonomies.

### D3FEND defensive coverage

Linked rollup: `40-synthesis/d3fend-coverage.yaml`. Two views: `defensive_entries` (D3FEND techniques implemented by capabilities, with backing capability IDs) and `counter_coverage` (for each exposed ATT&CK technique, whether a D3FEND-backed capability counters it). Use this view for architect-facing defensive posture analysis.

(Sections appear only when the relevant rollup file exists.)
```

- [ ] **Step 4: Run lint-agents and test suite**

```bash
apd-gauntlet lint-agents
pytest -q
```

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-synthesizer.md templates/advisory-report.template.md tests/test_lint_agents.py
git commit -m "feat(agent): apd-synthesizer emits cwe/owasp/d3fend coverage rollups when taxonomies declared"
```

---

## Task 15: Update 9 specialist agents — reference updated `apd-control-mappings` skill

**Goal:** Each of the 9 specialist agents needs a short pointer in its frontmatter or process steps noting that taxonomy mappings beyond NIST 800-53r5 and ATT&CK are now possible per run-config. The actual mapping discipline lives in the `apd-control-mappings` skill (updated in Task 12); the agent files just need to point readers there.

**Files:**

- Modify each of:
  - `.claude/agents/apd-confidentiality.md`
  - `.claude/agents/apd-integrity.md`
  - `.claude/agents/apd-availability.md`
  - `.claude/agents/apd-distributed.md`
  - `.claude/agents/apd-resilient.md`
  - `.claude/agents/apd-ephemeral.md`
  - `.claude/agents/apd-authenticity.md`
  - `.claude/agents/apd-non-repudiation.md`
  - `.claude/agents/apd-immutability.md`

- [ ] **Step 1: For each specialist agent, add one short paragraph in the "Control mappings" / "Outputs" section**

Insert (or append to the existing control_mappings discussion):

```markdown
**Taxonomy scope (v1.2+).** Beyond the always-required NIST 800-53r5 mapping and the high-confidence-only ATT&CK mapping, you may emit CWE (on findings, when the finding describes a specific weakness pattern) and D3FEND (on capabilities, with `counters_attack` cross-reference required). When the run declares OWASP Top 10 / API / LLM taxonomies in `.apd-run.yaml` and the SUT has the relevant surface, you may emit those mappings too. The full discipline lives in the `apd-control-mappings` skill — consult it before authoring any new-taxonomy mapping.
```

Adjust phrasing slightly per lens — e.g., the D3FEND-on-capabilities note is more relevant to specialists that frequently emit capabilities (authenticity, integrity, immutability) than to those that primarily emit findings. Don't manufacture differences; the canonical text above is fine for all nine.

- [ ] **Step 2: Run lint-agents**

```bash
apd-gauntlet lint-agents
```

Expected: PASS — agent frontmatter unchanged.

- [ ] **Step 3: Run full suite**

```bash
pytest -q
```

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/apd-{confidentiality,integrity,availability,distributed,resilient,ephemeral,authenticity,non-repudiation,immutability}.md
git commit -m "feat(agents): specialists reference v1.2 taxonomy scope in apd-control-mappings"
```

---

## Task 16: Update `init-run` CLI with `--taxonomies` flag

**Goal:** Extend the `init-run` subcommand to accept a `--taxonomies` comma-separated list (or repeated `--taxonomies` flag) that pre-populates the `taxonomies:` field in the scaffolded `.apd-run.yaml`.

**Files:**

- Modify: `tools/apd_gauntlet/init_run.py`
- Modify: `tools/apd_gauntlet/cli.py` (the `init-run` Click command)
- Modify: `tests/test_init_run.py` and/or `tests/test_init_run_config.py`

- [ ] **Step 1: Write failing test**

In `tests/test_init_run.py`:

```python
def test_init_run_writes_taxonomies_to_config(tmp_path):
    target = tmp_path / "apd-20260601-test"
    init_run(
        run_id="apd-20260601-test",
        inputs=tmp_path / "inputs",
        domain="pbm",
        target_root=tmp_path,
        taxonomies=["cwe", "mitre_attack", "d3fend", "owasp_api_top10"],
    )
    cfg = yaml.safe_load((target / ".apd-run.yaml").read_text())
    assert cfg["taxonomies"] == ["cwe", "mitre_attack", "d3fend", "owasp_api_top10"]


def test_init_run_without_taxonomies_omits_field(tmp_path):
    target = tmp_path / "apd-20260601-test2"
    init_run(
        run_id="apd-20260601-test2",
        inputs=tmp_path / "inputs",
        domain="pbm",
        target_root=tmp_path,
    )
    cfg = yaml.safe_load((target / ".apd-run.yaml").read_text())
    assert "taxonomies" not in cfg  # backward-compat: absent means absent
```

And in `tests/test_cli.py`:

```python
def test_cli_init_run_accepts_taxonomies_flag(cli_runner, tmp_path):
    result = cli_runner.invoke(main, [
        "init-run", "apd-20260601-flag",
        "--inputs", str(tmp_path / "inputs"),
        "--domain", "pbm",
        "--taxonomies", "cwe,mitre_attack,d3fend",
        "--target-root", str(tmp_path),
    ])
    assert result.exit_code == 0
    cfg = yaml.safe_load((tmp_path / "apd-20260601-flag" / ".apd-run.yaml").read_text())
    assert cfg["taxonomies"] == ["cwe", "mitre_attack", "d3fend"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_init_run.py tests/test_cli.py -v -k "taxonom"`
Expected: FAIL.

- [ ] **Step 3: Extend `init_run.py`**

Add a `taxonomies` parameter to `init_run`. When provided and non-empty, include it in the scaffolded `.apd-run.yaml`. When omitted or empty, do not include the field.

```python
def init_run(
    *,
    run_id: str,
    inputs: Path,
    domain: str,
    target_root: Path,
    taxonomies: list[str] | None = None,
    # ... existing parameters ...
) -> Path:
    # ... existing logic ...
    config: dict[str, Any] = {
        "run_id": run_id,
        # ... existing fields ...
    }
    if taxonomies:
        config["taxonomies"] = list(taxonomies)
    # ... write .apd-run.yaml ...
```

- [ ] **Step 4: Extend the CLI command**

In `tools/apd_gauntlet/cli.py`'s `init-run` definition, add:

```python
@main.command("init-run")
@click.argument("run_id")
@click.option("--inputs", required=True, type=click.Path(path_type=Path))
@click.option("--domain", required=True)
@click.option("--target-root", default=Path("runs"), type=click.Path(path_type=Path))
@click.option(
    "--taxonomies",
    default=None,
    help="Comma-separated taxonomies (cwe,mitre_attack,d3fend,owasp_top10,owasp_api_top10,owasp_llm_top10).",
)
def init_run_cmd(run_id: str, inputs: Path, domain: str, target_root: Path, taxonomies: str | None) -> None:
    parsed = [t.strip() for t in taxonomies.split(",") if t.strip()] if taxonomies else None
    path = init_run(
        run_id=run_id,
        inputs=inputs,
        domain=domain,
        target_root=target_root,
        taxonomies=parsed,
    )
    click.echo(f"Scaffolded {path}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_init_run.py tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 6: Run full suite + linters**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/init_run.py tools/apd_gauntlet/cli.py tests/test_init_run.py tests/test_cli.py
git commit -m "feat(cli): init-run accepts --taxonomies flag to pre-populate run-config"
```

---

## Task 17: Validator cross-reference check — D3FEND `counters_attack` must intersect capability's `mitre_attack`

**Goal:** Add a semantic validation check (not schema-level) that every D3FEND entry on a capability has at least one `counters_attack` ID that also appears in the same capability's `mitre_attack[].technique` list. Schema-level constraints can't express cross-property references; this lives in `validate.py`.

**Files:**

- Modify: `tools/apd_gauntlet/validate.py`
- Modify: `tests/test_validate_semantic.py` (or `tests/test_validate_cross_file.py`)
- Add: `tests/fixtures/capabilities/capability-d3fend-counters-mismatch.yaml`

- [ ] **Step 1: Write failing test**

In `tests/test_validate_semantic.py`:

```python
def _err_text(err: object) -> str:
    """Return the error's message body in whatever shape validate.py emits.

    Works for jsonschema.ValidationError (.message), custom dataclasses with
    .message, plain Exceptions (.args[0]), and stringifiable error objects.
    """
    return (
        getattr(err, "message", None)
        or (err.args[0] if getattr(err, "args", None) else None)
        or str(err)
    ).lower()


def test_validate_rejects_d3fend_counters_attack_not_in_mitre_attack(tmp_path):
    """D3FEND counters_attack must intersect the capability's mitre_attack."""
    cap = load_fixture("capabilities/capability-d3fend-counters-mismatch.yaml")
    # cap has d3fend.counters_attack = ["T9999"] but mitre_attack only lists T1078
    write_capability(tmp_path / "10-capabilities" / "cap-x.yaml", cap)
    errors = validate_run(tmp_path)
    assert any("counters_attack" in _err_text(e) for e in errors)


def test_validate_accepts_d3fend_counters_attack_intersects_mitre_attack(tmp_path):
    cap = load_fixture("capabilities/capability-with-d3fend.yaml")
    # d3fend.counters_attack = ["T1078"]; mitre_attack lists T1078
    write_capability(tmp_path / "10-capabilities" / "cap-x.yaml", cap)
    errors = validate_run(tmp_path)
    assert not any("counters_attack" in _err_text(e) for e in errors)
```

Fixture `tests/fixtures/capabilities/capability-d3fend-counters-mismatch.yaml`:

```yaml
schema_version: 1
id: cap-1a2b3c4d
# ... existing fields ...
control_mappings:
  nist_800_53r5: ["AC-3"]
  mitre_attack:
    - technique: T1078
      tactic: TA0001
      rationale: "..."
  d3fend:
    - technique: D3-NTA
      counters_attack: ["T9999"]  # intentionally not in mitre_attack
      rationale: "..."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_validate_semantic.py -v -k "d3fend_counters"`
Expected: FAIL.

- [ ] **Step 3: Add the cross-reference check to `validate.py`**

First inspect `validate.py` to identify the project's existing error type and accumulator pattern (e.g., does it return a list of strings? `dataclass` errors? `jsonschema.ValidationError`?):

```bash
grep -nE "class.*Error|def validate|append" tools/apd_gauntlet/validate.py | head -40
```

Then add a check that follows the existing pattern. The structure to add (adjust the error-construction line to match the file's existing pattern):

```python
def _check_d3fend_counters_attack(capability: dict[str, Any]) -> list[<ExistingErrorType>]:
    """Every d3fend.counters_attack ID must appear in mitre_attack[].technique."""
    errors: list[<ExistingErrorType>] = []
    cm = capability.get("control_mappings", {})
    d3fend_entries = cm.get("d3fend") or []
    if not d3fend_entries:
        return errors
    declared_attack = {entry["technique"] for entry in (cm.get("mitre_attack") or [])}
    for d3_entry in d3fend_entries:
        unmatched = [c for c in d3_entry.get("counters_attack", []) if c not in declared_attack]
        if unmatched:
            message = (
                f"capability {capability.get('id')}: d3fend entry {d3_entry['technique']} "
                f"counters_attack {unmatched} not in mitre_attack[]; "
                f"D3FEND mappings require the countered ATT&CK technique to also appear in mitre_attack."
            )
            errors.append(<construct_error_using_existing_pattern>)
    return errors
```

Wire the new check into the existing per-capability validation pass. If `validate.py` accumulates errors as plain strings, the constructor is just the message; if it uses a dataclass, instantiate it with the message field; if it uses jsonschema's `ValidationError`, raise it. Mirror whatever the file already does for cross-record checks like the existing finding-ID reference check.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_validate_semantic.py -v`
Expected: PASS.

- [ ] **Step 5: Run full suite + linters + mypy**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
```

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/validate.py tests/test_validate_semantic.py tests/fixtures/capabilities/capability-d3fend-counters-mismatch.yaml
git commit -m "feat(validate): enforce D3FEND counters_attack ⊆ capability's mitre_attack"
```

---

## Task 18: Update `lint-agents` to recognize updated agent contracts

**Goal:** `apd-gauntlet lint-agents` already validates frontmatter; no contract changes were introduced that require new lint rules. This task confirms the lint still passes after Tasks 12–15. If lint-agents has any heuristic checks on agent content (e.g., "must reference the apd-control-mappings skill"), extend them; otherwise this is a verification task only.

**Files:**

- Verify only — modify `tools/apd_gauntlet/lint_agents.py` and `tests/test_lint_agents.py` only if existing checks need updating.

- [ ] **Step 1: Run lint-agents to confirm current pass**

```bash
apd-gauntlet lint-agents
```

Expected: 13 agents clean.

- [ ] **Step 2: Inspect `lint_agents.py` to see if any content checks exist**

```bash
cat tools/apd_gauntlet/lint_agents.py
```

If the lint pass already enforces frontmatter only, this task is verification-only and no changes are needed — skip to Step 4.

If the lint pass enforces specific content sections (e.g., "must have a Process section"), add a check that:

- `apd-intake.md` has a "Taxonomy scope and auto-detection" subsection in Process
- `apd-synthesizer.md` documents the three new rollup outputs

- [ ] **Step 3: If lint-agents was modified, run its tests**

```bash
pytest tests/test_lint_agents.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit (only if changes were made)**

```bash
git add tools/apd_gauntlet/lint_agents.py tests/test_lint_agents.py
git commit -m "feat(lint): lint-agents recognizes v1.2 agent contract additions"
```

If no changes were needed, no commit. Move to Task 19.

---

## Task 19: Integration test — extend bundled example with taxonomy mappings

**Goal:** Extend the existing `examples/apd-20260601-claim-event-bus/` sample run to exercise the v1.2 taxonomies end-to-end. Add `taxonomies:` to its `.apd-run.yaml`, add CWE/OWASP/D3FEND mappings to a handful of expected findings/capabilities, and add the three new rollup files. The `apd-gauntlet validate examples/.../expected/` invocation continues to pass.

**Files:**

- Modify: `examples/apd-20260601-claim-event-bus/.apd-run.yaml` (or wherever the example's run config lives)
- Modify: 3–5 findings under `examples/apd-20260601-claim-event-bus/expected/20-findings/` — add `cwe`, `owasp_api_top10`, etc. to `control_mappings`
- Modify: 2–3 capabilities under `examples/apd-20260601-claim-event-bus/expected/10-capabilities/` — add `d3fend` to `control_mappings`
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/cwe-coverage.yaml`
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/owasp-coverage.yaml`
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/d3fend-coverage.yaml`
- Modify: `tests/test_examples.py` if the test enumerates expected file counts

- [ ] **Step 1: Examine the existing example structure**

```bash
ls examples/apd-20260601-claim-event-bus/
ls examples/apd-20260601-claim-event-bus/expected/
cat examples/apd-20260601-claim-event-bus/.apd-run.yaml  # may or may not exist; check
```

- [ ] **Step 2: Add taxonomies to the example's run-config**

Add `taxonomies: [cwe, mitre_attack, d3fend, owasp_api_top10]` to the example's run-config (a claim event bus has API surface, justifies OWASP API Top 10; no web UI, no LLM, so neither owasp_top10 nor owasp_llm_top10).

- [ ] **Step 3: Extend 3–5 findings with new taxonomy mappings**

Pick existing findings in the example that clearly map. Suggested:

- A Confidentiality finding about plaintext PHI → add `cwe: ["CWE-319"]`
- An Integrity finding about missing input validation → add `cwe: ["CWE-20"]`, `owasp_api_top10: ["API3:2023"]`
- An Authenticity finding about weak auth → add `cwe: ["CWE-287"]`, `owasp_api_top10: ["API2:2023"]`

Add the mappings to the YAML's `control_mappings` block alongside the existing `nist_800_53r5` and `mitre_attack` entries.

- [ ] **Step 4: Extend 2–3 capabilities with D3FEND mappings**

Pick capabilities that demonstrably implement a D3FEND technique. Suggested:

- An mTLS / workload-identity capability → `d3fend: [{technique: "D3-NTA", counters_attack: ["T1078"], rationale: "..."}]`
- A WORM audit log capability → `d3fend: [{technique: "D3-FBA", counters_attack: ["T1070"], rationale: "..."}]`

Ensure each `counters_attack` ID actually appears in the capability's existing `mitre_attack[].technique` list (or add it if missing).

- [ ] **Step 5: Create the three new rollup files in `expected/40-synthesis/`**

Hand-author the rollups to match what the synthesizer would emit given the findings/capabilities you modified. They must validate against the schemas built in Tasks 5–7.

- [ ] **Step 6: Run the validator on the example**

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

Expected: all files validate; record count increases by 3 (the new rollups).

- [ ] **Step 7: Update test_examples.py if it counts expected files**

If `tests/test_examples.py` asserts specific file counts, update them. Otherwise no change needed.

```bash
pytest tests/test_examples.py -v
```

Expected: PASS.

- [ ] **Step 8: Run full suite + linters**

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
apd-gauntlet lint-agents
apd-gauntlet validate-domain pbm
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

All expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add examples/apd-20260601-claim-event-bus/ tests/test_examples.py
git commit -m "feat(example): claim-event-bus exercises v1.2 CWE/OWASP API/D3FEND mappings end-to-end"
```

---

## Task 20: Architecture Decision Record — ADR 0008

**Goal:** Document the design decisions captured in §2 of the design spec.

**Files:**

- Create: `docs/adrs/0008-multi-framework-taxonomy-mappings.md`

- [ ] **Step 1: Read an existing ADR to match the format**

```bash
cat docs/adrs/0001-three-tier-structure.md
```

The 0001–0006 ADRs use the hyphen+colon style (see project memory). Match that style.

- [ ] **Step 2: Write the ADR**

`docs/adrs/0008-multi-framework-taxonomy-mappings.md`:

```markdown
# ADR 0008 - Multi-Framework Taxonomy Mappings

**Status:** Accepted
**Date:** 2026-05-25
**Context release:** v1.2.0

## Context

APD Gauntlet through v1.1 maps findings and capabilities to NIST 800-53r5 and (high-confidence-only) MITRE ATT&CK. The output is rigorous but speaks the APD taxonomy fluently; reviewers who know CWE, OWASP, or D3FEND but not APD lose information in translation. Practitioners' default frameworks vary by role — developers reach for CWE, application reviewers for OWASP Top 10, API reviewers for OWASP API Top 10, AI-app reviewers for OWASP LLM Top 10, defensive architects for D3FEND. Extending the gauntlet's vocabulary to these frameworks broadens the audience for its output without changing the underlying lens-driven analysis.

## Decision

Findings carry optional CWE, OWASP Top 10 (web / API / LLM) mappings inside `control_mappings`. Capabilities carry optional D3FEND mappings inside `control_mappings`. All additions are schema-optional; v1.1-format records continue to validate against the v1.2 schemas unchanged.

D3FEND on capabilities is the symmetric complement of the existing split: ATT&CK techniques attach to findings (the adversary technique the finding enables), ATT&CK mitigations and now D3FEND attach to capabilities (the defensive techniques the capability provides). D3FEND entries require a `counters_attack` cross-reference that must intersect the same capability's `mitre_attack[].technique` list, preventing D3FEND-by-name-similarity mappings.

Per-run scoping (`taxonomies: [...]` in `.apd-run.yaml`) controls which taxonomies are in scope. CWE, ATT&CK, and D3FEND are default-on; OWASP variants are opt-in (each scoped to a specific surface — web / API / LLM — that not every SUT exposes). Intake auto-detects relevant surfaces and writes a `taxonomy_suggestions:` block into the context brief, but specialists are bound only by the operator-accepted scope.

## Alternatives considered

**Domain pack declares the taxonomies.** Rejected — would tie taxonomy scope to domain (PBM declares OWASP because healthcare apps usually have web/API surface) rather than to the SUT under review. A PBM SUT with an LLM-bearing surface would need a PBM domain update to pull in OWASP LLM. Per-run scoping is more flexible.

**Always-on core taxonomies.** Rejected — agents would over-map (emit OWASP Top 10 tags on backend-only systems because it "kind of fits"), diluting signal.

**Auto-detect only, no declared scope.** Rejected — opaque to reviewers ("why was OWASP API mapped on this finding?"). The declared-scope + auto-detect-suggestion split preserves operator authority.

## Consequences

- Schema additions are fully additive within v1.x — no breaking changes.
- Synthesizer emits three new rollup artifacts (`cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`) when relevant.
- Three new reference-data refresh scripts (`refresh-cwe`, `refresh-owasp`, `refresh-d3fend`) require operator-driven refresh; documented cadence is quarterly.
- D3FEND `counters_attack` cross-reference rule prevents shotgun D3FEND mapping.
- Reference data shipped at `tools/apd_gauntlet/data/{cwe,owasp_top10,owasp_api_top10,owasp_llm_top10,d3fend}.json`.
```

- [ ] **Step 3: Run any ADR linter (if present)**

```bash
ls .github/workflows/   # check if there's an ADR linter / markdownlint applies
markdownlint docs/adrs/0008-multi-framework-taxonomy-mappings.md  # if markdownlint installed
```

- [ ] **Step 4: Commit**

```bash
git add docs/adrs/0008-multi-framework-taxonomy-mappings.md
git commit -m "docs(adr): 0008 multi-framework taxonomy mappings"
```

---

## Task 21: New documentation — `docs/taxonomy-mappings.md`

**Goal:** Operator-facing guide explaining the new taxonomies, how to enable them per run, how to read the new rollups, and the reference-data refresh cadence.

**Files:**

- Create: `docs/taxonomy-mappings.md`

- [ ] **Step 1: Write the doc**

```markdown
# Taxonomy mappings (v1.2+)

APD Gauntlet maps every finding and capability to NIST SP 800-53r5 and (high-confidence-only) MITRE ATT&CK by default. As of v1.2, findings and capabilities can also carry optional mappings to additional widely-adopted frameworks: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10, and MITRE D3FEND. These additional mappings make the gauntlet's output legible to reviewers fluent in those vocabularies without changing the underlying lens-driven analysis.

## Which taxonomies, where, and why

| Taxonomy | Attached to | Audience |
|---|---|---|
| NIST 800-53r5 | findings + capabilities (required) | Compliance, FedRAMP, audit |
| MITRE ATT&CK (technique) | findings (optional, high-confidence) | Threat intel, detection engineering |
| MITRE ATT&CK (mitigation) | capabilities (optional) | Defensive architecture |
| CWE | findings (optional, v1.2+) | Developers, AppSec |
| OWASP Top 10 (web) | findings (optional, v1.2+) | Application reviewers |
| OWASP API Top 10 | findings (optional, v1.2+) | API reviewers |
| OWASP LLM Top 10 | findings (optional, v1.2+) | AI-app reviewers |
| MITRE D3FEND | capabilities (optional, v1.2+) | Defensive architects |

D3FEND attaches to **capabilities** (defensive techniques the design implements), not findings — symmetric with the existing ATT&CK-technique-on-findings, ATT&CK-mitigation-on-capabilities split.

## Declaring taxonomies per run

The set of taxonomies in scope for a run is declared in `.apd-run.yaml`:

```yaml
run_id: apd-20260601-claim-event-bus
domain: pbm
taxonomies:
  - cwe              # default-on (always available)
  - mitre_attack     # default-on
  - d3fend           # default-on
  - owasp_api_top10  # opt-in (the SUT exposes a REST API)
```

The `init-run` CLI accepts `--taxonomies`:

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ./artifacts \
  --domain pbm \
  --taxonomies cwe,mitre_attack,d3fend,owasp_api_top10
```

Intake inspects the supplied artifacts and may suggest additional taxonomies in the context brief (e.g., an OpenAPI spec triggers an `owasp_api_top10` suggestion; an LLM SDK import triggers `owasp_llm_top10`). Suggestions are advisory — specialists honor only the declared scope. Re-run with the suggested taxonomy added to `taxonomies:` to incorporate it.

## Mapping discipline

Each taxonomy has discipline rules documented in the `apd-control-mappings` skill. Summary:

- **CWE** — use base or variant abstractions only; pillar/category entries are too abstract. Each mapping must be justified by the finding's `detail` text.
- **OWASP Top 10 / API / LLM** — preserve edition year in the ID (`A03:2021` stays `A03:2021` even after OWASP publishes the 2024 edition). Map only when the SUT exposes the relevant surface.
- **D3FEND** — `counters_attack` cross-reference is **required**; the cited ATT&CK technique must also appear in the same capability's `mitre_attack[].technique` list. The validator enforces this; map-by-name-similarity is forbidden.

## Synthesizer rollups

When the relevant taxonomies are declared and findings/capabilities carry the mappings, the synthesizer emits:

- `40-synthesis/cwe-coverage.yaml` — CWE IDs grouped by abstraction and parent pillar.
- `40-synthesis/owasp-coverage.yaml` — OWASP categories per variant; categories with no finding coverage are emitted with `silent: true` to make absence visible.
- `40-synthesis/d3fend-coverage.yaml` — D3FEND techniques implemented by capabilities plus a `counter_coverage` view (for each exposed ATT&CK technique, whether a D3FEND-backed capability counters it).

The advisory report links to each rollup in a "Framework Coverage" section.

## Reference-data refresh

The gauntlet ships projected reference data at `tools/apd_gauntlet/data/`. To refresh from upstream sources:

```bash
apd-gauntlet refresh-cwe
apd-gauntlet refresh-owasp
apd-gauntlet refresh-d3fend
```

Each script applies a 60-second HTTP timeout, a 200 MiB response cap, and records a `source_sha256` and `fetched_at` in the projected JSON. Recommended cadence: **quarterly**, or whenever a taxonomy publishes a new edition you intend to adopt.

```

- [ ] **Step 2: Commit**

```bash
git add docs/taxonomy-mappings.md
git commit -m "docs: add docs/taxonomy-mappings.md operator guide for v1.2 taxonomies"
```

---

## Task 22: Update existing docs for v1.2

**Goal:** Refresh `docs/architecture.md`, `docs/running-the-gauntlet.md`, and `docs/schema-evolution.md` to mention the v1.2 additions.

**Files:**

- Modify: `docs/architecture.md`
- Modify: `docs/running-the-gauntlet.md`
- Modify: `docs/schema-evolution.md`
- Modify: `README.md` (if it lists features or schemas)

- [ ] **Step 1: Update `docs/architecture.md`**

In the "Output files" section (or wherever the rollup list lives), add the three new rollups to the tree:

```
40-synthesis/
  ├── advisory-report.md
  ├── nist-coverage.yaml
  ├── attack-exposure.yaml
  ├── coverage-matrix.yaml
  ├── cwe-coverage.yaml         # NEW v1.2 (when cwe declared)
  ├── owasp-coverage.yaml       # NEW v1.2 (when any owasp_* declared)
  ├── d3fend-coverage.yaml      # NEW v1.2 (when d3fend declared)
  └── ...
```

Add a brief paragraph noting v1.2 additions are activation-gated by `taxonomies:` declaration in run-config.

- [ ] **Step 2: Update `docs/running-the-gauntlet.md`**

Add a short subsection in the operator workflow describing the `--taxonomies` flag and pointing to `docs/taxonomy-mappings.md`:

```markdown
### Taxonomy scope (v1.2+)

Declare taxonomies in `.apd-run.yaml` or pass `--taxonomies cwe,mitre_attack,d3fend,owasp_api_top10` to `init-run`. CWE, ATT&CK, and D3FEND are default-on; OWASP variants are opt-in (gated on the SUT having the relevant web/API/LLM surface). See [docs/taxonomy-mappings.md](taxonomy-mappings.md) for the full operator guide.
```

- [ ] **Step 3: Update `docs/schema-evolution.md`**

Document the additive cadence:

```markdown
## v1.2.0 — Multi-framework taxonomy mappings (Phase A)

Additive within v1.x. Extensions:
- `finding.schema.json` gains optional `control_mappings.cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10`.
- `capability.schema.json` gains optional `control_mappings.d3fend` (with required `counters_attack` cross-reference).
- `run-config.schema.json` gains optional `taxonomies` array.
- New schemas: `cwe-coverage`, `owasp-coverage`, `d3fend-coverage`.

PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 without changes.

## v1.3.0 — Methodology-aware threat-model evaluator (Phase B)

(Coming next — see `docs/superpowers/specs/2026-05-25-threat-model-and-attack-path-analysis-design.md`.)

## v1.4.0 — Attack-path enumeration and D3FEND defense graph (Phase C)

(Coming after Phase B.)
```

- [ ] **Step 4: Update README.md feature list (if applicable)**

If `README.md` has a feature list that mentions specific taxonomies, extend it. If it stays at the conceptual level ("Both streams are organized along the nine APD goals... Every finding and capability carries NIST 800-53r5 control mappings..."), extend that paragraph:

```diff
- Both streams are organized along the nine APD goals listed above. Every finding and capability carries NIST 800-53r5 control mappings. Findings carry MITRE ATT&CK technique mappings when an agent has high confidence; capabilities carry ATT&CK mitigation mappings.
+ Both streams are organized along the nine APD goals listed above. Every finding and capability carries NIST 800-53r5 control mappings. Findings carry MITRE ATT&CK technique mappings (and, when the run declares the relevant taxonomies, CWE / OWASP Top 10 / API / LLM mappings) when an agent has high confidence. Capabilities carry ATT&CK mitigation mappings (and optional MITRE D3FEND mappings with required ATT&CK counter-references).
```

- [ ] **Step 5: Run any markdown linter**

```bash
markdownlint docs/ README.md  # if installed
```

- [ ] **Step 6: Commit**

```bash
git add docs/architecture.md docs/running-the-gauntlet.md docs/schema-evolution.md README.md
git commit -m "docs: refresh architecture/running/schema-evolution/README for v1.2 taxonomies"
```

---

## Task 23: CHANGELOG entry + final version bump (1.2.0.dev0 → 1.2.0)

**Goal:** Finalize the v1.2.0 release artifact.

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `tools/apd_gauntlet/__init__.py`
- Modify: `plugin.json`
- Modify: `tools/apd_gauntlet/cli.py` (if framework-version is hardcoded)

- [ ] **Step 1: Write the CHANGELOG entry**

Add to the top of `CHANGELOG.md` (above the existing `[1.1.0]` and `[1.0.0]` entries):

```markdown
## [1.2.0] - 2026-XX-XX

### Added
- Multi-framework taxonomy mappings on findings: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10
- D3FEND mappings on capabilities, with required `counters_attack` cross-reference to the same capability's `mitre_attack` block
- Per-run taxonomy scoping via `taxonomies:` field in `.apd-run.yaml`
- Intake `taxonomy_suggestions` block auto-detects relevant surfaces (web routes, OpenAPI specs, LLM SDK imports)
- Three new synthesizer coverage rollups: `cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`
- Three new schemas: `cwe-coverage.schema.json`, `owasp-coverage.schema.json`, `d3fend-coverage.schema.json`
- Three new CLI subcommands: `refresh-cwe`, `refresh-owasp`, `refresh-d3fend` (with v1.0 security-review hardening: 60s timeout, 200 MiB cap, source_sha256)
- Seeded reference data at `tools/apd_gauntlet/data/{cwe,owasp_top10,owasp_api_top10,owasp_llm_top10,d3fend}.json`
- `apd-control-mappings` skill gains per-taxonomy discipline sections
- `init-run --taxonomies` CLI flag
- Cross-reference validation: D3FEND `counters_attack` must intersect capability's `mitre_attack`
- ADR 0008 — Multi-framework taxonomy mappings
- `docs/taxonomy-mappings.md` operator guide

### Changed
- `finding.schema.json` — `control_mappings` accepts optional `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10` arrays
- `capability.schema.json` — `control_mappings` accepts optional `d3fend` array
- `run-config.schema.json` — accepts optional `taxonomies` array

### Backward compatibility
- All schema changes additive. v1.1-format runs validate unchanged against v1.2 schemas.
- Minimum-viable run with no `taxonomies:` declaration produces identical output to v1.1.
- PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 with no changes.
```

Leave the date as `2026-XX-XX` per the project's tag-time convention (filled in when the actual tag is cut, as v1.0 and v1.1 entries do).

- [ ] **Step 2: Bump version to 1.2.0**

```bash
# In each of the version-holding files:
pyproject.toml:                version = "1.2.0"
tools/apd_gauntlet/__init__.py: __version__ = "1.2.0"
plugin.json:                   "version": "1.2.0"
# tools/apd_gauntlet/cli.py:   if framework-version default is hardcoded
```

- [ ] **Step 3: Final verification sweep**

```bash
pytest -q                                                            # expect: all pass
pytest --cov --cov-fail-under=85                                     # expect: pass
ruff check tools/ tests/                                             # expect: clean
mypy tools/                                                          # expect: clean
apd-gauntlet lint-agents                                             # expect: 13 agents clean
apd-gauntlet validate-domain pbm                                     # expect: clean
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # expect: ~21 files clean (was 18 + 3 new rollups)
```

If any fail, stop and fix before committing the version bump.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md pyproject.toml tools/apd_gauntlet/__init__.py plugin.json tools/apd_gauntlet/cli.py
git commit -m "release: v1.2.0 — multi-framework taxonomy mappings (Phase A)"
```

- [ ] **Step 5: Push and leave tag for the maintainer**

```bash
git push origin main
```

Tagging (`git tag -a v1.2.0 -m "v1.2.0"`) and publishing are operator decisions per the project's deferred-items convention — do not tag unless explicitly asked.

---

## Verification — final state

After Task 23 lands and is pushed, the repo should be in this state:

- **Version:** 1.2.0 (untagged)
- **Tests:** ~129 passing (was 114; +15 from Phase A — schemas + refresh scripts + init-run + validator cross-ref)
- **Coverage:** ≥85% on `tools/apd_gauntlet/`; target ≥90% on new modules
- **Agents:** 13 (unchanged — Phase A modifies existing agents and skill; new agents introduced in Phase B / C)
- **Schemas:** 13 (was 10; +3 new coverage rollups)
- **Skills:** 5 (unchanged — `apd-control-mappings` enhanced)
- **Reference data files:** 6 (was 1 — `mitre.json` only; +5 — cwe, owasp_top10, owasp_api_top10, owasp_llm_top10, d3fend)
- **CLI subcommands:** +3 (`refresh-cwe`, `refresh-owasp`, `refresh-d3fend`) plus `init-run --taxonomies`
- **Docs:** +1 (`docs/taxonomy-mappings.md`); 4 updated (architecture, running, schema-evolution, README)
- **ADRs:** 8 (added 0008)
- **CHANGELOG:** v1.2.0 entry filled with feature list, date placeholder

Next: Phase B (v1.3.0) — methodology-aware threat-model evaluator. Plan file: `docs/superpowers/plans/2026-05-XX-phase-b-threat-model-evaluation.md` (to be written after Phase A is complete and merged).

---

## Notes for the executor

- **TDD discipline:** every task that touches code follows write-test → run-fail → implement → run-pass → commit. Don't skip the run-fail step — it confirms the test actually tests something.
- **Commit cadence:** each task ends with one commit. Don't batch multiple tasks into one commit.
- **No --no-verify:** if a pre-commit hook fails, fix the underlying issue. The v1.0 release added Dependabot + CodeQL; both run on push.
- **Reference-data placeholders:** if MITRE / OWASP / D3FEND APIs are unreachable at execution time, hand-seed the JSON files per the fallback instructions in Tasks 8–10. Document `source_url: "seed_only"` in those files. The refresh scripts must still work (verified via fixture tests); operator-driven live refresh is deferred until upstream sources are reachable.
- **D3FEND IRI parser (Task 10):** Task 10 ships a working parser with a seeded long-name→short-code map covering ~15 commonly-cited D3FEND techniques. If the live D3FEND JSON-LD includes `d3fend:d3f-id` properties directly (recommended path), the parser uses those; otherwise it falls back to the seeded map. The engineer should *supplement* the seed map (don't replace it) if a live refresh surfaces additional techniques the seed doesn't cover. The sample-fixture test gives a concrete target shape.
- **No new agents in Phase A.** All three new agents (`apd-threat-model-recon`, `apd-threat-model-evaluator`, `apd-attack-path-analyzer`) are deferred to Phases B and C. Don't introduce them here.
