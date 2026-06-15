# Phase C — Attack-Path Enumeration + D3FEND Defense Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add BloodHound-style attack-path enumeration over a partial provenance-and-confidence-aware graph, with a MITRE D3FEND defensive overlay on bottleneck edges. Ship as `apd-gauntlet` v1.4.0 — fully additive within v1.x. Introduce a tier-0 intake extension that emits a machine-readable asset inventory, and a tier-4 `apd-attack-path-analyzer` agent that consumes the asset inventory, dedup'd findings/capabilities, the normalized threat model (if present), and the code-evidence-index (if present) to build an asset graph, enumerate paths from declared attacker positions to declared crown jewels, identify bottleneck edges shared across paths, and overlay D3FEND defensive techniques.

**Architecture:** One new tier-4 agent (`apd-attack-path-analyzer`) parallel in placement to the v1.3 evaluator. It delegates deterministic work to a new `apd-gauntlet analyze-attack-paths` CLI subcommand backed by `tools/apd_gauntlet/attack_path/` Python modules — graph build, bounded-DFS enumeration with edge-set pruning, D3FEND counter lookup, Mermaid rendering, finding emission. The agent itself authors edge provenance from artifact evidence and writes the markdown advisory section. Activation-gated on at least one crown jewel being declared (domain-pack default or run-config override). The existing intake agent gains a structured `00-context/asset-inventory.yaml` artifact that the analyzer consumes; the rest of the gauntlet remains unchanged.

**Tech Stack:** Python 3.10+, `jsonschema>=4.20`, `pyyaml>=6.0`, `click>=8.1`, `lxml` (already added in Phase B), `pytest>=8.0`, `ruff`, `mypy --strict`. JSON Schema draft 2020-12. New package at `tools/apd_gauntlet/attack_path/`. No new runtime dependency.

---

## Pre-flight verification

Before starting Task C-1, verify clean working tree and current passing state:

```bash
git status                          # expect: clean (uv.lock may be untracked; leave it)
pytest -q                           # expect: 346 passed
ruff check tools/ tests/            # expect: clean
mypy tools/                         # expect: clean
apd-gauntlet lint-agents            # expect: 15 agents clean
apd-gauntlet validate-domain pbm    # expect: clean
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # expect: clean
apd-gauntlet --version              # expect: 1.3.0
```

If the project has `coverage` installed as a dev extra, also run `pytest --cov --cov-fail-under=85` and confirm the gate passes. (If `pytest --cov` errors with `unrecognized arguments: --cov`, the dev extras aren't installed — run `pip install -e ".[dev]"` first.)

If any of the above fail, stop and investigate before starting the plan.

---

## Task C-1: Pre-flight version bump (1.3.0 → 1.4.0.dev0)

**Files:**

- Modify: `pyproject.toml`
- Modify: `tools/apd_gauntlet/__init__.py`
- Modify: `plugin.json`
- Modify: `tests/test_cli.py` (the `test_cli_version` assertion hardcodes the string)

- [ ] **Step 1: Bump version in all three places**

  - `pyproject.toml` line 7: `version = "1.3.0"` → `version = "1.4.0.dev0"`
  - `tools/apd_gauntlet/__init__.py`: `__version__ = "1.3.0"` → `__version__ = "1.4.0.dev0"`
  - `plugin.json`: `"version": "1.3.0"` → `"version": "1.4.0.dev0"`

- [ ] **Step 2: Update `tests/test_cli.py::test_cli_version` assertion**

  Update the hardcoded version string from `"1.3.0"` to `"1.4.0.dev0"`.

- [ ] **Step 3: Run tests + linters**

  ```bash
  pytest -q                       # expect: 346 passed
  ruff check tools/ tests/        # expect: clean
  mypy tools/                     # expect: clean
  apd-gauntlet --version          # expect: apd-gauntlet, version 1.4.0.dev0
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add pyproject.toml tools/apd_gauntlet/__init__.py plugin.json tests/test_cli.py
  git commit -m "chore: bump version to 1.4.0.dev0 for Phase C work"
  ```

---

## Task C-2: Extend `finding.schema.json` — `attack_path_analyzer` agent + `apath-` id prefix

**Goal:** Add `attack_path_analyzer` to the `agent` enum and relax the `id` pattern to accept `apath-[0-9a-f]{8}` prefix. Mirrors the Phase B Task B-7 pattern for `threat_model_evaluator` / `tmeval-`.

**Files:**

- Modify: `schemas/finding.schema.json`
- Modify: `tests/test_finding_schema.py`
- Add: `tests/fixtures/valid/finding-from-apath.yaml`

- [ ] **Step 1: Write failing tests**

   In `tests/test_finding_schema.py`, append:

   ```python
   def test_finding_accepts_attack_path_analyzer_agent():
       finding = load_fixture("valid/finding-from-apath.yaml")
       errors = list(validate_finding(finding))
       assert errors == []

   def test_finding_id_pattern_accepts_apath_prefix():
       finding = load_fixture("valid/finding-from-apath.yaml")
       assert finding["id"].startswith("apath-")
       errors = list(validate_finding(finding))
       assert errors == []
   ```

- [ ] **Step 2: Run tests to verify they fail**

   ```bash
   pytest tests/test_finding_schema.py -v -k "attack_path_analyzer or apath_prefix"
   ```

   Expected: FAIL (schema rejects `attack_path_analyzer` agent value and `apath-` id prefix).

- [ ] **Step 3: Extend the schema**

  In `schemas/finding.schema.json`:

  - `id.pattern` (line 17): extend to `^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged|tmeval|apath)-[0-9a-f]{8}$`
  - `agent.enum`: append `"attack_path_analyzer"` after `"threat_model_evaluator"`
  - `cross_references.items.pattern`: same extension as `id.pattern`
  - `merged_from.items.pattern`: same extension as `id.pattern`

- [ ] **Step 4: Write the fixture**

   `tests/fixtures/valid/finding-from-apath.yaml`:

   ```yaml
   schema_version: 1
   id: apath-c0ffee01
   agent: attack_path_analyzer
   apd_tier: trustworthiness
   apd_goal: confidentiality
   disposition: risk
   severity: critical
   confidence: high
   title: "Compromised pharmacy credential reaches PHI store in 3 hops with no capability coverage"
   summary: "Path from attacker position compromised_pharmacy_credential to crown jewel phi_store traverses claim-ingress-API → adjudication-service → member-record-store with no D3FEND-backed capability on any edge."
   detail: "Path: compromised_pharmacy_credential --[authn_required:low_confidence]--> claim-ingress-API --[compromisable_via_finding:auth-9e8d7c6b]--> adjudication-service --[data_resides_on:high]--> member-record-store (crown jewel). Feasibility floor = low (one low-confidence authn edge). Severity sum = high. No capability_mitigates edges encountered."
   evidence:
     - artifact: "40-synthesis/asset-graph.yaml"
       locator: "paths[0]"
       excerpt: "from: compromised_pharmacy_credential to: phi_store hops: 3 feasibility: low"
     - artifact: "40-synthesis/attack-paths.yaml"
       locator: "paths[0].edges"
       excerpt: "edge_type: compromisable_via_finding finding_id: auth-9e8d7c6b confidence: high"
   control_mappings:
     nist_800_53r5: ["AC-3", "AC-6", "SC-7"]
     mitre_attack:
       - technique: "T1078"
         tactic: "TA0001"
         rationale: "Path begins with valid credential abuse; T1078 (Valid Accounts) is the entry technique."
   cross_references: [auth-9e8d7c6b]
   recommendation:
     posture: required
     summary: "Add D3-NTSA (Network Traffic Signature Analysis) or equivalent boundary control on claim-ingress-API"
     detail: "Three D3FEND techniques counter T1078 and would mitigate this path: D3-NTSA, D3-IBCA (Inbound Authentication), D3-CSPP (Credential Strong Password Policy). None are implemented by existing capabilities. Adding any one breaks this and 4 other paths sharing the claim-ingress-API edge (bottleneck threshold)."
   ```

- [ ] **Step 5: Run tests to verify they pass**

   ```bash
   pytest tests/test_finding_schema.py -v
   pytest -q   # expect: 348 passed (2 new tests)
   ruff check tools/ tests/
   mypy tools/
   ```

- [ ] **Step 6: Commit**

   ```bash
   git add schemas/finding.schema.json tests/test_finding_schema.py tests/fixtures/valid/finding-from-apath.yaml
   git commit -m "feat(schema): finding.agent gains attack_path_analyzer; id pattern accepts apath- prefix"
   ```

---

## Task C-3: Extend `run-config.schema.json` — `crown_jewels`, `attacker_positions`, `attack_path_analysis`

**Goal:** Three new optional fields. `crown_jewels` and `attacker_positions` override the domain pack defaults. `attack_path_analysis` is a tuning block (`max_hop`, `max_paths_per_pair`, `bottleneck_threshold`). All optional; absent fields → domain-pack defaults → hardcoded defaults.

**Files:**

- Modify: `schemas/run-config.schema.json`
- Modify: `tests/test_run_config_schema.py`
- Add: `tests/fixtures/valid/run-config-with-attack-path.yaml`
- Add: `tests/fixtures/invalid/run-config-with-bad-max-hop.yaml`

- [ ] **Step 1: Write failing tests**

   ```python
   def test_run_config_accepts_crown_jewels_and_attacker_positions():
       cfg = load_fixture("valid/run-config-with-attack-path.yaml")
       errors = list(validate_run_config(cfg))
       assert errors == []
       assert cfg["crown_jewels"] == ["phi_store", "pde_submission_pipeline"]
       assert "compromised_pharmacy_credential" in cfg["attacker_positions"]

   def test_run_config_accepts_attack_path_analysis_tuning_block():
       cfg = load_fixture("valid/run-config-with-attack-path.yaml")
       assert cfg["attack_path_analysis"]["max_hop"] == 6
       assert cfg["attack_path_analysis"]["max_paths_per_pair"] == 25
       assert cfg["attack_path_analysis"]["bottleneck_threshold"] == 4

   def test_run_config_rejects_max_hop_above_cap():
       cfg = load_fixture("invalid/run-config-with-bad-max-hop.yaml")
       errors = list(validate_run_config(cfg))
       assert errors, "max_hop=20 should violate maximum=12"

   def test_run_config_rejects_max_paths_per_pair_above_cap():
       # Inline-construct to keep fixture count small
       cfg = {"schema_version": 1, "framework_version": "1.4.0.dev0",
              "domain": {"id": "pbm", "version": "1.0.0"},
              "attack_path_analysis": {"max_paths_per_pair": 500}}
       errors = list(validate_run_config(cfg))
       assert errors, "max_paths_per_pair=500 should violate maximum=200"
   ```

- [ ] **Step 2: Extend schema**

   In `schemas/run-config.schema.json`, append to `properties`:

   ```jsonc
   "crown_jewels": {
     "type": "array",
     "minItems": 0,
     "items": { "type": "string", "minLength": 1 },
     "description": "Optional run-level override of the domain pack's crown_jewels[].pattern values. Specialists and the attack-path analyzer treat these as the run's protected targets. Empty list disables attack-path analysis for the run even if the domain declares defaults."
   },
   "attacker_positions": {
     "type": "array",
     "minItems": 0,
     "items": { "type": "string", "minLength": 1 },
     "description": "Optional run-level override of the domain pack's attacker_positions[].position values. Used by the attack-path analyzer as enumeration starting points."
   },
   "attack_path_analysis": {
     "type": "object",
     "additionalProperties": false,
     "description": "Tuning knobs for the attack-path analyzer. All fields optional; absent fields fall back to defaults (max_hop=8, max_paths_per_pair=50, bottleneck_threshold=5).",
     "properties": {
       "max_hop": {
         "type": "integer",
         "minimum": 2,
         "maximum": 12,
         "description": "Maximum hop depth for path enumeration. Bounded at 12 to keep enumeration tractable on partial graphs."
       },
       "max_paths_per_pair": {
         "type": "integer",
         "minimum": 1,
         "maximum": 200,
         "description": "Maximum paths emitted per (attacker_position, crown_jewel) pair. Bounded at 200; paths are sorted by descending severity_sum then ascending hop_count before truncation."
       },
       "bottleneck_threshold": {
         "type": "integer",
         "minimum": 2,
         "maximum": 50,
         "description": "Minimum number of enumerated paths an edge must appear on to be tagged as a bottleneck edge for the D3FEND overlay."
       }
     }
   }
   ```

   Do NOT add any of these to `required[]`.

- [ ] **Step 3: Write the fixtures**

   `tests/fixtures/valid/run-config-with-attack-path.yaml`:

   ```yaml
   schema_version: 1
   framework_version: "1.4.0.dev0"
   domain:
     id: pbm
     version: "1.0.0"
   taxonomies: [cwe, mitre_attack, d3fend]
   crown_jewels:
     - phi_store
     - pde_submission_pipeline
   attacker_positions:
     - external_internet
     - compromised_pharmacy_credential
     - insider_with_member_service_role
   attack_path_analysis:
     max_hop: 6
     max_paths_per_pair: 25
     bottleneck_threshold: 4
   ```

   `tests/fixtures/invalid/run-config-with-bad-max-hop.yaml`:

   ```yaml
   schema_version: 1
   framework_version: "1.4.0.dev0"
   domain: { id: pbm, version: "1.0.0" }
   attack_path_analysis:
     max_hop: 20   # exceeds maximum=12
   ```

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_run_config_schema.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add schemas/run-config.schema.json tests/test_run_config_schema.py tests/fixtures/valid/run-config-with-attack-path.yaml tests/fixtures/invalid/run-config-with-bad-max-hop.yaml
   git commit -m "feat(schema): run-config gains crown_jewels, attacker_positions, attack_path_analysis tuning"
   ```

---

## Task C-4: Extend `domain.schema.json` — `crown_jewels`, `attacker_positions`, `default_trust_boundaries`

**Goal:** Domain pack declares defaults for the three new attack-path inputs. All optional — a domain with no declarations means attack-path analysis is opt-in per run; with declarations it activates by default unless the run-config sets empty overrides.

**Files:**

- Modify: `schemas/domain.schema.json`
- Modify: `tests/test_domain_schema.py`
- Add: `tests/fixtures/valid/domain-with-attack-path.yaml`

- [ ] **Step 1: Write failing tests**

   ```python
   def test_domain_accepts_crown_jewels_and_attacker_positions():
       d = load_fixture("valid/domain-with-attack-path.yaml")
       errors = list(validate_domain(d))
       assert errors == []
       jewels = [j["pattern"] for j in d["crown_jewels"]]
       assert "phi_store" in jewels

   def test_domain_crown_jewel_requires_pattern_and_description():
       bad = {"schema_version": 1, "id": "test", "version": "1.0.0",
              "crown_jewels": [{"pattern": "foo"}]}  # missing description
       errors = list(validate_domain(bad))
       assert errors

   def test_domain_attacker_position_requires_position_and_description():
       bad = {"schema_version": 1, "id": "test", "version": "1.0.0",
              "attacker_positions": [{"position": "foo"}]}  # missing description
       errors = list(validate_domain(bad))
       assert errors

   def test_domain_default_trust_boundary_requires_boundary_and_description():
       bad = {"schema_version": 1, "id": "test", "version": "1.0.0",
              "default_trust_boundaries": [{"boundary": "foo"}]}  # missing description
       errors = list(validate_domain(bad))
       assert errors
   ```

- [ ] **Step 2: Extend schema**

   Append to `domain.schema.json`'s `properties`:

   ```jsonc
   "crown_jewels": {
     "type": "array",
     "items": {
       "type": "object",
       "required": ["pattern", "description"],
       "additionalProperties": false,
       "properties": {
         "pattern":     { "type": "string", "minLength": 1, "description": "Domain-recognized crown jewel name (e.g. phi_store). Run-config can override this list, in which case domain defaults are not used." },
         "description": { "type": "string", "minLength": 10 }
       }
     }
   },
   "attacker_positions": {
     "type": "array",
     "items": {
       "type": "object",
       "required": ["position", "description"],
       "additionalProperties": false,
       "properties": {
         "position":    { "type": "string", "minLength": 1 },
         "description": { "type": "string", "minLength": 10 }
       }
     }
   },
   "default_trust_boundaries": {
     "type": "array",
     "items": {
       "type": "object",
       "required": ["boundary", "description"],
       "additionalProperties": false,
       "properties": {
         "boundary":    { "type": "string", "minLength": 1 },
         "description": { "type": "string", "minLength": 10 }
       }
     }
   }
   ```

- [ ] **Step 3: Fixture**

   `tests/fixtures/valid/domain-with-attack-path.yaml` — a minimal valid domain doc with all three new arrays populated (3 crown jewels, 3 attacker positions, 2 trust boundaries).

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_domain_schema.py -v
   pytest -q
   git add schemas/domain.schema.json tests/test_domain_schema.py tests/fixtures/valid/domain-with-attack-path.yaml
   git commit -m "feat(schema): domain pack gains crown_jewels, attacker_positions, default_trust_boundaries"
   ```

---

## Task C-5: New schema `asset-inventory.schema.json`

**Goal:** Schema for the intake-emitted machine-readable asset inventory. This is the artifact the attack-path analyzer consumes as the seed for graph nodes. Holds assets (services, stores, queues, networks), identities, and declared trust boundaries with provenance.

**Files:**

- Create: `schemas/asset-inventory.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/valid/asset-inventory-valid.yaml`

- [ ] **Step 1: Write the schema**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/asset-inventory.schema.json",
     "title": "APD Gauntlet Asset Inventory",
     "type": "object",
     "required": ["schema_version", "generated_by", "assets", "identities", "trust_boundaries"],
     "additionalProperties": false,
     "properties": {
       "schema_version": { "type": "integer", "const": 1 },
       "generated_by":   { "type": "string", "enum": ["intake"] },
       "assets": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["asset_id", "name", "asset_type", "provenance", "confidence"],
           "additionalProperties": false,
           "properties": {
             "asset_id":   { "type": "string", "pattern": "^asset-[0-9a-f]{8}$" },
             "name":       { "type": "string", "minLength": 1 },
             "asset_type": { "type": "string", "enum": ["service", "data_store", "secret_store", "queue", "network", "external_dependency", "compute"] },
             "data_classifications": {
               "type": "array",
               "items": { "type": "string", "enum": ["phi", "pii", "pci", "phi_subset", "secret", "public", "internal", "confidential"] }
             },
             "provenance": {
               "type": "object",
               "required": ["source"],
               "additionalProperties": false,
               "properties": {
                 "source":  { "type": "string", "enum": ["artifact", "domain_default", "threat_model", "code_evidence"] },
                 "artifact":{ "type": "string" },
                 "locator": { "type": "string" }
               }
             },
             "confidence": { "type": "string", "enum": ["high", "medium", "low"] }
           }
         }
       },
       "identities": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["identity_id", "name", "identity_type", "provenance", "confidence"],
           "additionalProperties": false,
           "properties": {
             "identity_id":   { "type": "string", "pattern": "^idn-[0-9a-f]{8}$" },
             "name":          { "type": "string", "minLength": 1 },
             "identity_type": { "type": "string", "enum": ["human_role", "service_account", "workload_identity", "external_party"] },
             "provenance":    { "$ref": "#/properties/assets/items/properties/provenance" },
             "confidence":    { "type": "string", "enum": ["high", "medium", "low"] }
           }
         }
       },
       "trust_boundaries": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["boundary_id", "name", "crosses", "provenance"],
           "additionalProperties": false,
           "properties": {
             "boundary_id": { "type": "string", "pattern": "^tb-[0-9a-f]{8}$" },
             "name":        { "type": "string", "minLength": 1 },
             "crosses":     {
               "type": "array",
               "minItems": 2,
               "items": { "type": "string", "pattern": "^asset-[0-9a-f]{8}$" }
             },
             "provenance":  { "$ref": "#/properties/assets/items/properties/provenance" }
           }
         }
       },
       "extraction_summary": {
         "type": "object",
         "additionalProperties": false,
         "properties": {
           "asset_count":            { "type": "integer", "minimum": 0 },
           "identity_count":         { "type": "integer", "minimum": 0 },
           "trust_boundary_count":   { "type": "integer", "minimum": 0 },
           "high_confidence_count":  { "type": "integer", "minimum": 0 },
           "medium_confidence_count":{ "type": "integer", "minimum": 0 },
           "low_confidence_count":   { "type": "integer", "minimum": 0 }
         }
       }
     }
   }
   ```

- [ ] **Step 2: Fixture**

   `tests/fixtures/valid/asset-inventory-valid.yaml` — 4 assets (web client, API gateway, adjudication service, PHI store), 2 identities (pharmacy submitter role, adjudication service account), 2 trust boundaries (external→ingress, ingress→PHI). All with `provenance.source: "artifact"` and a real-looking artifact/locator.

- [ ] **Step 3: Test (mirror Phase B Task B-9 pattern using `_validate_whole_doc_schema`)**

- [ ] **Step 4: Run tests + meta-schema check + commit**

   ```bash
   pytest tests/test_other_schemas.py tests/test_meta_schemas.py -v
   pytest -q
   git add schemas/asset-inventory.schema.json tests/test_other_schemas.py tests/fixtures/valid/asset-inventory-valid.yaml
   git commit -m "feat(schema): add asset-inventory rollup schema (intake artifact)"
   ```

---

## Task C-6: New schema `asset-graph.schema.json`

**Goal:** Schema for the analyzer-built asset graph. Superset of the inventory — adds attacker_position and crown_jewel nodes, and adds the edge layer.

**Files:**

- Create: `schemas/asset-graph.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/valid/asset-graph-valid.yaml`

- [ ] **Step 1: Write the schema**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/asset-graph.schema.json",
     "title": "APD Gauntlet Asset Graph",
     "type": "object",
     "required": ["schema_version", "generated_by", "nodes", "edges"],
     "additionalProperties": false,
     "properties": {
       "schema_version": { "type": "integer", "const": 1 },
       "generated_by":   { "type": "string", "enum": ["attack_path_analyzer"] },
       "nodes": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["node_id", "node_type", "name", "provenance", "confidence"],
           "additionalProperties": false,
           "properties": {
             "node_id":   { "type": "string", "pattern": "^(asset|idn|atk|jewel)-[0-9a-f]{8}$" },
             "node_type": { "type": "string", "enum": ["asset", "identity", "attacker_position", "crown_jewel"] },
             "name":      { "type": "string", "minLength": 1 },
             "asset_type":{ "type": "string", "enum": ["service", "data_store", "secret_store", "queue", "network", "external_dependency", "compute"] },
             "data_classifications": {
               "type": "array",
               "items": { "type": "string", "enum": ["phi", "pii", "pci", "phi_subset", "secret", "public", "internal", "confidential"] }
             },
             "provenance": {
               "type": "object",
               "required": ["source"],
               "additionalProperties": false,
               "properties": {
                 "source":   { "type": "string", "enum": ["artifact", "domain_default", "threat_model", "code_evidence", "run_config"] },
                 "artifact": { "type": "string" },
                 "locator":  { "type": "string" }
               }
             },
             "confidence": { "type": "string", "enum": ["high", "medium", "low"] }
           }
         }
       },
       "edges": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["edge_id", "edge_type", "from", "to", "provenance", "confidence", "traversal_cost"],
           "additionalProperties": false,
           "properties": {
             "edge_id":   { "type": "string", "pattern": "^edge-[0-9a-f]{8}$" },
             "edge_type": { "type": "string", "enum": ["network_reachable", "authn_required", "authz_grants", "data_resides_on", "trusts", "compromisable_via_finding", "mitigated_by_capability"] },
             "from":      { "type": "string", "pattern": "^(asset|idn|atk|jewel)-[0-9a-f]{8}$" },
             "to":        { "type": "string", "pattern": "^(asset|idn|atk|jewel)-[0-9a-f]{8}$" },
             "finding_id":    { "type": "string", "pattern": "^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged|tmeval|apath)-[0-9a-f]{8}$" },
             "capability_id": { "type": "string", "pattern": "^cap-[0-9a-f]{8}$" },
             "provenance": { "$ref": "#/properties/nodes/items/properties/provenance" },
             "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
             "traversal_cost": { "type": "integer", "minimum": 1, "maximum": 100 }
           },
           "allOf": [
             {
               "if": { "properties": { "edge_type": { "const": "compromisable_via_finding" } } },
               "then": { "required": ["finding_id"] }
             },
             {
               "if": { "properties": { "edge_type": { "const": "mitigated_by_capability" } } },
               "then": { "required": ["capability_id"] }
             }
           ]
         }
       },
       "build_summary": {
         "type": "object",
         "additionalProperties": false,
         "properties": {
           "node_count":               { "type": "integer", "minimum": 0 },
           "edge_count":               { "type": "integer", "minimum": 0 },
           "attacker_position_count":  { "type": "integer", "minimum": 0 },
           "crown_jewel_count":        { "type": "integer", "minimum": 0 },
           "finding_edges_count":      { "type": "integer", "minimum": 0 },
           "capability_edges_count":   { "type": "integer", "minimum": 0 },
           "sources_used":             { "type": "array", "items": { "type": "string", "enum": ["asset_inventory", "threat_model_normalized", "code_evidence_index", "findings", "capabilities", "domain_defaults", "run_config"] } }
         }
       }
     }
   }
   ```

- [ ] **Step 2: Fixture**

   `tests/fixtures/valid/asset-graph-valid.yaml` — 6 nodes (1 attacker_position, 3 assets, 1 identity, 1 crown_jewel) and 5 edges (one of each edge_type that's relevant: network_reachable, authn_required, data_resides_on, compromisable_via_finding with finding_id, mitigated_by_capability with capability_id).

- [ ] **Step 3: Test + run + commit**

   Commit message: `feat(schema): add asset-graph schema with node/edge provenance and confidence`

---

## Task C-7: New schema `attack-path.schema.json`

**Goal:** Schema for the enumerated paths — sequence of edges with path-level metadata (feasibility, severity, bottleneck membership).

**Files:**

- Create: `schemas/attack-path.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/valid/attack-paths-valid.yaml`

- [ ] **Step 1: Write the schema**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/attack-path.schema.json",
     "title": "APD Gauntlet Attack Paths",
     "type": "object",
     "required": ["schema_version", "generated_by", "enumeration_parameters", "paths", "summary"],
     "additionalProperties": false,
     "properties": {
       "schema_version": { "type": "integer", "const": 1 },
       "generated_by":   { "type": "string", "enum": ["attack_path_analyzer"] },
       "enumeration_parameters": {
         "type": "object",
         "required": ["max_hop", "max_paths_per_pair", "bottleneck_threshold"],
         "additionalProperties": false,
         "properties": {
           "max_hop":              { "type": "integer", "minimum": 2, "maximum": 12 },
           "max_paths_per_pair":   { "type": "integer", "minimum": 1, "maximum": 200 },
           "bottleneck_threshold": { "type": "integer", "minimum": 2, "maximum": 50 }
         }
       },
       "paths": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["path_id", "attacker_position", "crown_jewel", "edges", "hop_count", "feasibility", "severity_sum", "mitigation_count", "bottleneck_edges"],
           "additionalProperties": false,
           "properties": {
             "path_id":           { "type": "string", "pattern": "^path-[0-9a-f]{8}$" },
             "attacker_position": { "type": "string", "pattern": "^atk-[0-9a-f]{8}$" },
             "crown_jewel":       { "type": "string", "pattern": "^jewel-[0-9a-f]{8}$" },
             "edges":             {
               "type": "array",
               "minItems": 1,
               "items": { "type": "string", "pattern": "^edge-[0-9a-f]{8}$" }
             },
             "hop_count":        { "type": "integer", "minimum": 1, "maximum": 12 },
             "feasibility":      { "type": "string", "enum": ["high", "medium", "low"], "description": "Floor of edge confidence along path (min)." },
             "severity_sum":     { "type": "integer", "minimum": 0, "description": "Sum of severity scores for compromisable_via_finding edges along path. critical=4, high=3, medium=2, low=1, informational=0." },
             "mitigation_count": { "type": "integer", "minimum": 0, "description": "Count of mitigated_by_capability edges along path." },
             "bottleneck_edges": {
               "type": "array",
               "items": { "type": "string", "pattern": "^edge-[0-9a-f]{8}$" }
             }
           }
         }
       },
       "summary": {
         "type": "object",
         "required": ["pairs_enumerated", "total_paths", "truncated_pairs", "bottleneck_edge_count"],
         "additionalProperties": false,
         "properties": {
           "pairs_enumerated":     { "type": "integer", "minimum": 0 },
           "total_paths":          { "type": "integer", "minimum": 0 },
           "truncated_pairs":      { "type": "integer", "minimum": 0, "description": "Number of (attacker, crown) pairs where enumeration hit max_paths_per_pair and was truncated." },
           "bottleneck_edge_count":{ "type": "integer", "minimum": 0 }
         }
       }
     }
   }
   ```

- [ ] **Step 2: Fixture** — 2 paths sharing one bottleneck edge.

- [ ] **Step 3: Test + run + commit**

   Commit message: `feat(schema): add attack-path schema with enumeration parameters + per-path metadata`

---

## Task C-8: New schema `defense-graph.schema.json`

**Goal:** Schema for the D3FEND defensive overlay — for each bottleneck edge, what ATT&CK techniques traverse it, what D3FEND techniques counter those, and which D3FEND techniques are already capability-backed vs net-new.

**Files:**

- Create: `schemas/defense-graph.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/valid/defense-graph-valid.yaml`

- [ ] **Step 1: Write the schema**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/defense-graph.schema.json",
     "title": "APD Gauntlet Defense Graph",
     "type": "object",
     "required": ["schema_version", "generated_by", "bottleneck_overlays", "summary"],
     "additionalProperties": false,
     "properties": {
       "schema_version": { "type": "integer", "const": 1 },
       "generated_by":   { "type": "string", "enum": ["attack_path_analyzer"] },
       "bottleneck_overlays": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["edge_id", "paths_traversing", "exposed_attack_techniques", "candidate_d3fend", "existing_capability_backing", "net_new_d3fend"],
           "additionalProperties": false,
           "properties": {
             "edge_id":              { "type": "string", "pattern": "^edge-[0-9a-f]{8}$" },
             "paths_traversing":     { "type": "integer", "minimum": 2 },
             "exposed_attack_techniques": {
               "type": "array",
               "items": { "$ref": "_defs.schema.json#/$defs/attack_technique_id" }
             },
             "candidate_d3fend": {
               "type": "array",
               "items": {
                 "type": "object",
                 "required": ["d3fend_id", "counters", "rationale"],
                 "additionalProperties": false,
                 "properties": {
                   "d3fend_id": { "$ref": "_defs.schema.json#/$defs/d3fend_id" },
                   "counters":  { "type": "array", "minItems": 1, "items": { "$ref": "_defs.schema.json#/$defs/attack_technique_id" } },
                   "rationale": { "type": "string", "minLength": 20 }
                 }
               }
             },
             "existing_capability_backing": {
               "type": "array",
               "items": {
                 "type": "object",
                 "required": ["d3fend_id", "capability_ids"],
                 "additionalProperties": false,
                 "properties": {
                   "d3fend_id":      { "$ref": "_defs.schema.json#/$defs/d3fend_id" },
                   "capability_ids": { "type": "array", "minItems": 1, "items": { "type": "string", "pattern": "^cap-[0-9a-f]{8}$" } }
                 }
               }
             },
             "net_new_d3fend": {
               "type": "array",
               "items": { "$ref": "_defs.schema.json#/$defs/d3fend_id" },
               "description": "D3FEND techniques that counter the exposed ATT&CK set but are NOT implemented by any existing capability — highest-leverage defensive investments."
             }
           }
         }
       },
       "summary": {
         "type": "object",
         "required": ["bottleneck_edge_count", "total_candidate_d3fend", "total_net_new_d3fend"],
         "additionalProperties": false,
         "properties": {
           "bottleneck_edge_count":   { "type": "integer", "minimum": 0 },
           "total_candidate_d3fend":  { "type": "integer", "minimum": 0 },
           "total_net_new_d3fend":    { "type": "integer", "minimum": 0 }
         }
       }
     }
   }
   ```

- [ ] **Step 2: Fixture** — one bottleneck edge overlay covering T1078 with candidate D3-NTSA / D3-IBCA, one already capability-backed and one net-new.

- [ ] **Step 3: Test + run + commit**

   Commit message: `feat(schema): add defense-graph schema with D3FEND overlay on bottleneck edges`

---

## Task C-9: Create `tools/apd_gauntlet/attack_path/` package — dataclasses + graph primitive

**Goal:** Skeleton package + `Node`, `Edge`, `Graph` types. Pure data — no algorithm yet. Mirrors Phase B's `tools/apd_gauntlet/threat_model/` package layout.

**Files:**

- Create: `tools/apd_gauntlet/attack_path/__init__.py`
- Create: `tools/apd_gauntlet/attack_path/graph.py`
- Create: `tests/test_attack_path_graph.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from apd_gauntlet.attack_path.graph import Node, Edge, Graph

   def test_node_requires_provenance_and_confidence():
       n = Node(node_id="asset-aaaaaaaa", node_type="asset", name="API",
                provenance={"source": "artifact", "artifact": "intake-brief.md", "locator": "L42"},
                confidence="high")
       assert n.node_id == "asset-aaaaaaaa"

   def test_node_rejects_malformed_id():
       with pytest.raises(ValueError, match="node_id"):
           Node(node_id="bad-id", node_type="asset", name="X",
                provenance={"source": "artifact"}, confidence="high")

   def test_node_id_prefix_matches_node_type():
       # asset-* for asset, idn-* for identity, atk-* for attacker_position, jewel-* for crown_jewel
       with pytest.raises(ValueError, match="prefix"):
           Node(node_id="asset-aaaaaaaa", node_type="identity", name="X",
                provenance={"source": "artifact"}, confidence="high")

   def test_edge_requires_from_to_provenance_confidence_cost():
       e = Edge(edge_id="edge-aaaaaaaa", edge_type="network_reachable",
                from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
                provenance={"source": "artifact"}, confidence="high", traversal_cost=1)
       assert e.edge_type == "network_reachable"

   def test_compromisable_via_finding_edge_requires_finding_id():
       with pytest.raises(ValueError, match="finding_id"):
           Edge(edge_id="edge-aaaaaaaa", edge_type="compromisable_via_finding",
                from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
                provenance={"source": "artifact"}, confidence="high", traversal_cost=1)

   def test_mitigated_by_capability_edge_requires_capability_id():
       with pytest.raises(ValueError, match="capability_id"):
           Edge(edge_id="edge-aaaaaaaa", edge_type="mitigated_by_capability",
                from_node="asset-bbbbbbbb", to_node="asset-cccccccc",
                provenance={"source": "artifact"}, confidence="high", traversal_cost=1)

   def test_graph_add_node_and_lookup():
       g = Graph()
       g.add_node(Node("asset-aaaaaaaa", "asset", "API",
                       {"source": "artifact"}, "high"))
       assert g.get_node("asset-aaaaaaaa").name == "API"

   def test_graph_add_duplicate_node_raises():
       g = Graph()
       n1 = Node("asset-aaaaaaaa", "asset", "A", {"source": "artifact"}, "high")
       g.add_node(n1)
       with pytest.raises(ValueError, match="duplicate"):
           g.add_node(n1)

   def test_graph_add_edge_requires_both_endpoints_present():
       g = Graph()
       with pytest.raises(ValueError, match="unknown node"):
           g.add_edge(Edge("edge-aaaaaaaa", "network_reachable",
                            "asset-bbbbbbbb", "asset-cccccccc",
                            {"source": "artifact"}, "high", 1))

   def test_graph_outgoing_edges_for_node():
       g = Graph()
       n1 = Node("asset-aaaaaaaa", "asset", "A", {"source": "artifact"}, "high")
       n2 = Node("asset-bbbbbbbb", "asset", "B", {"source": "artifact"}, "high")
       g.add_node(n1); g.add_node(n2)
       e = Edge("edge-aaaaaaaa", "network_reachable",
                "asset-aaaaaaaa", "asset-bbbbbbbb",
                {"source": "artifact"}, "high", 1)
       g.add_edge(e)
       outs = g.outgoing("asset-aaaaaaaa")
       assert len(outs) == 1 and outs[0].edge_id == "edge-aaaaaaaa"

   def test_stable_id_deterministic():
       from apd_gauntlet.attack_path.graph import stable_id
       assert stable_id("asset", "API", "intake-brief.md#L42") == stable_id("asset", "API", "intake-brief.md#L42")
       assert stable_id("asset", "API", "intake-brief.md#L42") != stable_id("asset", "API", "intake-brief.md#L43")
       assert stable_id("asset", "API", "intake-brief.md#L42").startswith("asset-")
   ```

- [ ] **Step 2: Run tests to verify they fail** (`ImportError`)

- [ ] **Step 3: Implement `tools/apd_gauntlet/attack_path/__init__.py`**

   ```python
   """Attack-path analysis primitives — graph, enumeration, D3FEND overlay, Mermaid rendering."""
   ```

- [ ] **Step 4: Implement `tools/apd_gauntlet/attack_path/graph.py`**

   ```python
   """Graph primitives for attack-path analysis.

   Defines Node, Edge, Graph dataclasses with strict construction rules:
   - Node IDs must match the prefix corresponding to node_type
   - compromisable_via_finding edges require finding_id
   - mitigated_by_capability edges require capability_id
   - Adding an edge whose endpoints don't exist in the graph raises ValueError
   """

   from __future__ import annotations

   import hashlib
   import re
   from dataclasses import dataclass, field
   from typing import Literal

   NodeType = Literal["asset", "identity", "attacker_position", "crown_jewel"]
   EdgeType = Literal[
       "network_reachable", "authn_required", "authz_grants",
       "data_resides_on", "trusts",
       "compromisable_via_finding", "mitigated_by_capability",
   ]
   Confidence = Literal["high", "medium", "low"]

   _NODE_PREFIX = {
       "asset": "asset-",
       "identity": "idn-",
       "attacker_position": "atk-",
       "crown_jewel": "jewel-",
   }
   _NODE_ID_RE = re.compile(r"^(asset|idn|atk|jewel)-[0-9a-f]{8}$")
   _EDGE_ID_RE = re.compile(r"^edge-[0-9a-f]{8}$")


   def stable_id(kind: str, *components: str) -> str:
       """Deterministic sha8-based ID with kind prefix.

       kind is one of: asset, idn, atk, jewel, edge.
       components are concatenated with '|' then hashed.
       """
       payload = "|".join((kind, *components)).encode("utf-8")
       digest = hashlib.sha256(payload).hexdigest()[:8]
       prefix = "edge-" if kind == "edge" else _NODE_PREFIX.get(kind, f"{kind}-")
       return f"{prefix}{digest}"


   @dataclass(frozen=True)
   class Node:
       node_id: str
       node_type: NodeType
       name: str
       provenance: dict
       confidence: Confidence
       asset_type: str | None = None
       data_classifications: tuple[str, ...] = ()

       def __post_init__(self) -> None:
           if not _NODE_ID_RE.match(self.node_id):
               raise ValueError(f"malformed node_id: {self.node_id}")
           expected_prefix = _NODE_PREFIX[self.node_type]
           if not self.node_id.startswith(expected_prefix):
               raise ValueError(
                   f"node_id prefix {self.node_id[:6]!r} does not match node_type {self.node_type!r} (expected {expected_prefix!r})"
               )
           if "source" not in self.provenance:
               raise ValueError("provenance must include 'source'")
           if self.confidence not in ("high", "medium", "low"):
               raise ValueError(f"invalid confidence: {self.confidence}")


   @dataclass(frozen=True)
   class Edge:
       edge_id: str
       edge_type: EdgeType
       from_node: str
       to_node: str
       provenance: dict
       confidence: Confidence
       traversal_cost: int
       finding_id: str | None = None
       capability_id: str | None = None

       def __post_init__(self) -> None:
           if not _EDGE_ID_RE.match(self.edge_id):
               raise ValueError(f"malformed edge_id: {self.edge_id}")
           if self.edge_type == "compromisable_via_finding" and not self.finding_id:
               raise ValueError("compromisable_via_finding edge requires finding_id")
           if self.edge_type == "mitigated_by_capability" and not self.capability_id:
               raise ValueError("mitigated_by_capability edge requires capability_id")
           if not 1 <= self.traversal_cost <= 100:
               raise ValueError(f"traversal_cost out of range: {self.traversal_cost}")


   @dataclass
   class Graph:
       """In-memory adjacency-list graph. Not thread-safe; not meant to be."""

       _nodes: dict[str, Node] = field(default_factory=dict)
       _edges: dict[str, Edge] = field(default_factory=dict)
       _adj: dict[str, list[str]] = field(default_factory=dict)  # node_id -> list[edge_id]

       def add_node(self, node: Node) -> None:
           if node.node_id in self._nodes:
               raise ValueError(f"duplicate node: {node.node_id}")
           self._nodes[node.node_id] = node
           self._adj.setdefault(node.node_id, [])

       def add_edge(self, edge: Edge) -> None:
           if edge.from_node not in self._nodes:
               raise ValueError(f"unknown node: {edge.from_node}")
           if edge.to_node not in self._nodes:
               raise ValueError(f"unknown node: {edge.to_node}")
           if edge.edge_id in self._edges:
               raise ValueError(f"duplicate edge: {edge.edge_id}")
           self._edges[edge.edge_id] = edge
           self._adj[edge.from_node].append(edge.edge_id)

       def get_node(self, node_id: str) -> Node:
           return self._nodes[node_id]

       def get_edge(self, edge_id: str) -> Edge:
           return self._edges[edge_id]

       def outgoing(self, node_id: str) -> list[Edge]:
           return [self._edges[eid] for eid in self._adj.get(node_id, [])]

       def nodes_by_type(self, node_type: NodeType) -> list[Node]:
           return [n for n in self._nodes.values() if n.node_type == node_type]

       @property
       def node_count(self) -> int:
           return len(self._nodes)

       @property
       def edge_count(self) -> int:
           return len(self._edges)
   ```

- [ ] **Step 5: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_path_graph.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/attack_path/ tests/test_attack_path_graph.py
   git commit -m "feat(attack_path): graph primitives (Node, Edge, Graph) with strict construction"
   ```

---

## Task C-10: Graph builder — consume all inputs

**Goal:** `tools/apd_gauntlet/attack_path/build.py` reads asset-inventory.yaml, threat-model-normalized.yaml (optional), code-evidence-index.yaml (optional), all findings, all capabilities, the domain pack, and the run-config — then constructs a `Graph` with attacker_position and crown_jewel nodes added, and all edge types populated with `provenance.source` set per origin artifact.

**Files:**

- Create: `tools/apd_gauntlet/attack_path/build.py`
- Create: `tests/test_attack_path_build.py`
- Create: `tests/fixtures/attack_path/minimal-run/` — directory tree with asset-inventory, finding files, capability files, etc.

- [ ] **Step 1: Build the minimal-run fixture**

   `tests/fixtures/attack_path/minimal-run/` directory:

   ```
   minimal-run/
     .apd-run.yaml                                  # crown_jewels: [phi_store], attacker_positions: [external]
     00-context/
       asset-inventory.yaml                         # 3 assets, 1 identity, 1 trust boundary
       threat-model-normalized.yaml                 # 2 entries (one mentions adjudication→PHI)
       code-evidence-index.yaml                     # 1 cross-service call (claim-ingress → adjudication)
     20-specialist-findings/
       confidentiality.findings.yaml                # 1 finding mentioning plaintext on adjudication→PHI
     30-specialist-capabilities/
       confidentiality.capabilities.yaml            # 1 capability — TLS on claim-ingress→adjudication
     domains/
       pbm.yaml                                     # crown_jewels: [phi_store], attacker_positions: [external]
   ```

   Use the existing valid fixtures as templates (`tests/fixtures/valid/finding-from-conf.yaml` etc.); minimize content while keeping it schema-valid.

- [ ] **Step 2: Write failing tests**

   ```python
   from pathlib import Path
   from apd_gauntlet.attack_path.build import build_graph

   FIXTURE_ROOT = Path("tests/fixtures/attack_path/minimal-run")

   def test_builder_emits_attacker_position_and_crown_jewel_nodes():
       graph = build_graph(FIXTURE_ROOT)
       assert any(n.node_type == "attacker_position" and n.name == "external" for n in graph.nodes_by_type("attacker_position"))
       assert any(n.node_type == "crown_jewel" and n.name == "phi_store" for n in graph.nodes_by_type("crown_jewel"))

   def test_builder_emits_asset_nodes_from_inventory():
       graph = build_graph(FIXTURE_ROOT)
       assets = graph.nodes_by_type("asset")
       assert len(assets) >= 3

   def test_builder_emits_compromisable_edges_from_findings():
       graph = build_graph(FIXTURE_ROOT)
       # The fixture finding cites adjudication→PHI plaintext
       comp_edges = [e for e in graph._edges.values() if e.edge_type == "compromisable_via_finding"]
       assert comp_edges
       assert all(e.finding_id for e in comp_edges)

   def test_builder_emits_capability_edges_from_capabilities():
       graph = build_graph(FIXTURE_ROOT)
       mit_edges = [e for e in graph._edges.values() if e.edge_type == "mitigated_by_capability"]
       assert mit_edges
       assert all(e.capability_id for e in mit_edges)

   def test_builder_threat_model_edges_carry_threat_model_provenance():
       graph = build_graph(FIXTURE_ROOT)
       tm_provenance_edges = [e for e in graph._edges.values() if e.provenance.get("source") == "threat_model"]
       assert tm_provenance_edges, "threat-model entries should produce at least one edge with threat_model provenance"

   def test_builder_skips_when_no_crown_jewels_declared(tmp_path):
       # Copy fixture, clear crown_jewels in .apd-run.yaml and domain
       # Expect builder to raise BuilderBlocked
       import shutil
       run = tmp_path / "run"
       shutil.copytree(FIXTURE_ROOT, run)
       cfg = run / ".apd-run.yaml"
       cfg.write_text(cfg.read_text().replace("crown_jewels:\n  - phi_store", "crown_jewels: []"))
       dom = run / "domains" / "pbm.yaml"
       dom.write_text(dom.read_text().replace("phi_store", "REMOVED"))
       from apd_gauntlet.attack_path.build import BuilderBlocked
       with pytest.raises(BuilderBlocked, match="no crown jewels"):
           build_graph(run)

   def test_builder_skips_when_no_attacker_positions_declared(tmp_path):
       # Same shape — clear attacker_positions
       import shutil
       run = tmp_path / "run"
       shutil.copytree(FIXTURE_ROOT, run)
       cfg = run / ".apd-run.yaml"
       cfg.write_text(cfg.read_text().replace("attacker_positions:\n  - external", "attacker_positions: []"))
       dom = run / "domains" / "pbm.yaml"
       dom.write_text(dom.read_text().replace("- position: external", "# (removed)"))
       from apd_gauntlet.attack_path.build import BuilderBlocked
       with pytest.raises(BuilderBlocked, match="no attacker positions"):
           build_graph(run)
   ```

- [ ] **Step 3: Implement `tools/apd_gauntlet/attack_path/build.py`**

   Structure:

   ```python
   """Graph builder. Reads run inputs and emits a populated Graph + build_summary dict."""

   from __future__ import annotations

   from dataclasses import dataclass
   from pathlib import Path
   from typing import Any

   import yaml

   from .graph import Edge, Graph, Node, stable_id


   class BuilderBlocked(Exception):
       """Raised when required inputs are absent (no crown jewels, no attacker positions)."""


   @dataclass(frozen=True)
   class BuildResult:
       graph: Graph
       sources_used: list[str]


   _SEVERITY_TO_COST = {"critical": 1, "high": 2, "medium": 4, "low": 8, "informational": 16}


   def build_graph(run_dir: Path) -> BuildResult:
       run_cfg     = _load_yaml(run_dir / ".apd-run.yaml")
       domain_cfg  = _load_domain(run_dir, run_cfg)
       inventory   = _load_yaml(run_dir / "00-context" / "asset-inventory.yaml")
       tm_norm     = _load_optional(run_dir / "00-context" / "threat-model-normalized.yaml")
       code_idx    = _load_optional(run_dir / "00-context" / "code-evidence-index.yaml")
       findings    = _load_all_records(run_dir / "20-specialist-findings", key="findings", glob="*.findings.yaml")
       capabilities= _load_all_records(run_dir / "30-specialist-capabilities", key="capabilities", glob="*.capabilities.yaml")

       crown_jewel_names      = _resolve_crown_jewels(run_cfg, domain_cfg)
       attacker_position_data = _resolve_attacker_positions(run_cfg, domain_cfg)

       if not crown_jewel_names:
           raise BuilderBlocked("no crown jewels declared (domain pack or run-config)")
       if not attacker_position_data:
           raise BuilderBlocked("no attacker positions declared (domain pack or run-config)")

       g = Graph()
       sources: list[str] = []

       _add_inventory_nodes(g, inventory); sources.append("asset_inventory")
       _add_attacker_positions(g, attacker_position_data, run_cfg, domain_cfg)
       _add_crown_jewels(g, crown_jewel_names, inventory, domain_cfg)

       _add_inventory_trust_edges(g, inventory)
       _add_finding_edges(g, findings); sources.append("findings")
       _add_capability_edges(g, capabilities); sources.append("capabilities")

       if tm_norm:
           _add_threat_model_edges(g, tm_norm)
           sources.append("threat_model_normalized")

       if code_idx:
           _add_code_evidence_edges(g, code_idx)
           sources.append("code_evidence_index")

       return BuildResult(graph=g, sources_used=sources)


   def _load_yaml(path: Path) -> dict:
       return yaml.safe_load(path.read_text()) or {}


   def _load_optional(path: Path) -> dict | None:
       return _load_yaml(path) if path.exists() else None


   def _load_all_records(dir_path: Path, *, key: str, glob: str) -> list[dict]:
       out: list[dict] = []
       if not dir_path.exists():
           return out
       for f in sorted(dir_path.glob(glob)):
           doc = _load_yaml(f)
           records = doc.get(key) if isinstance(doc, dict) else None
           if isinstance(records, list):
               out.extend(records)
       return out


   def _load_domain(run_dir: Path, run_cfg: dict) -> dict:
       dom_id = (run_cfg.get("domain") or {}).get("id") or "pbm"
       candidates = [
           run_dir / "domains" / f"{dom_id}.yaml",
           run_dir / "domains" / dom_id / "domain.yaml",
       ]
       for c in candidates:
           if c.exists():
               return _load_yaml(c)
       return {}


   def _resolve_crown_jewels(run_cfg: dict, domain: dict) -> list[str]:
       # Run-config overrides domain (including explicit empty list)
       if "crown_jewels" in run_cfg:
           return list(run_cfg["crown_jewels"])
       return [j["pattern"] for j in domain.get("crown_jewels", [])]


   def _resolve_attacker_positions(run_cfg: dict, domain: dict) -> list[dict]:
       if "attacker_positions" in run_cfg:
           # Run-config gives names only; pair with domain descriptions if present
           dom_by_name = {p["position"]: p for p in domain.get("attacker_positions", [])}
           return [
               dom_by_name.get(name, {"position": name, "description": "(undeclared in domain pack)"})
               for name in run_cfg["attacker_positions"]
           ]
       return list(domain.get("attacker_positions", []))


   def _add_inventory_nodes(g: Graph, inv: dict) -> None:
       for a in inv.get("assets", []):
           g.add_node(Node(
               node_id=a["asset_id"], node_type="asset", name=a["name"],
               provenance=a["provenance"], confidence=a["confidence"],
               asset_type=a.get("asset_type"),
               data_classifications=tuple(a.get("data_classifications", [])),
           ))
       for i in inv.get("identities", []):
           g.add_node(Node(
               node_id=i["identity_id"], node_type="identity", name=i["name"],
               provenance=i["provenance"], confidence=i["confidence"],
           ))


   def _add_attacker_positions(g: Graph, positions: list[dict], run_cfg: dict, domain: dict) -> None:
       run_override = "attacker_positions" in run_cfg
       source = "run_config" if run_override else "domain_default"
       for p in positions:
           name = p["position"]
           node_id = stable_id("atk", name, source)
           g.add_node(Node(
               node_id=node_id, node_type="attacker_position", name=name,
               provenance={"source": source, "artifact": ".apd-run.yaml" if run_override else f"domains/{domain.get('id', 'unknown')}.yaml"},
               confidence="high",
           ))


   def _add_crown_jewels(g: Graph, jewel_names: list[str], inventory: dict, domain: dict) -> None:
       # Each crown jewel is a synthetic node that points to any inventory asset matching its pattern
       # via a data_resides_on edge.
       for name in jewel_names:
           jewel_id = stable_id("jewel", name)
           g.add_node(Node(
               node_id=jewel_id, node_type="crown_jewel", name=name,
               provenance={"source": "domain_default" if any(j["pattern"] == name for j in domain.get("crown_jewels", [])) else "run_config"},
               confidence="high",
           ))
           # Wire to inventory assets whose data_classifications align with the jewel pattern.
           # The mapping pattern→classification is intentionally simple: pattern "phi_store" matches
           # assets carrying "phi" in data_classifications. Anything not matched leaves the jewel
           # as a standalone node — still useful as a target, even without inventory backing.
           target_classification = name.replace("_store", "").replace("_pipeline", "").replace("_engine", "")
           for asset in g.nodes_by_type("asset"):
               if target_classification in (asset.data_classifications or ()):
                   g.add_edge(Edge(
                       edge_id=stable_id("edge", asset.node_id, jewel_id, "data_resides_on"),
                       edge_type="data_resides_on",
                       from_node=asset.node_id, to_node=jewel_id,
                       provenance={"source": "asset_inventory"},
                       confidence=asset.confidence, traversal_cost=1,
                   ))


   def _add_inventory_trust_edges(g: Graph, inv: dict) -> None:
       for tb in inv.get("trust_boundaries", []):
           crossings = tb.get("crosses", [])
           # Wire pairwise `trusts` edges in both directions; provenance is the boundary record
           for i, src in enumerate(crossings):
               for dst in crossings[i + 1:]:
                   for from_id, to_id in ((src, dst), (dst, src)):
                       g.add_edge(Edge(
                           edge_id=stable_id("edge", from_id, to_id, "trusts", tb["boundary_id"]),
                           edge_type="trusts",
                           from_node=from_id, to_node=to_id,
                           provenance={"source": "asset_inventory", "locator": tb["boundary_id"]},
                           confidence="high", traversal_cost=2,
                       ))


   def _add_finding_edges(g: Graph, findings: list[dict]) -> None:
       """Each finding becomes a compromisable_via_finding edge between two nodes
       named in the finding's evidence excerpts. The simplest heuristic: scan the
       finding's `detail` and `evidence[].excerpt` for node names already in the
       graph; if exactly one pair is identifiable as (source, target), wire the edge.

       If no pair can be identified, the finding is left as a "free-floating" risk
       (no edge added); the analyzer documents this in the report as an unwired finding.
       """
       node_names = {n.name.lower(): n.node_id for n in [g.get_node(nid) for nid in g._nodes]}
       for f in findings:
           text = " ".join([f.get("detail", "")] + [e.get("excerpt", "") for e in f.get("evidence", [])])
           hits = [nid for name, nid in node_names.items() if name in text.lower()]
           if len(hits) >= 2:
               # Use first two hits in order of appearance. Heuristic; the agent's prompt
               # asks the LLM to author edge provenance more carefully — this is the deterministic floor.
               cost = _SEVERITY_TO_COST.get(f.get("severity", "medium"), 4)
               g.add_edge(Edge(
                   edge_id=stable_id("edge", hits[0], hits[1], "compromisable_via_finding", f["id"]),
                   edge_type="compromisable_via_finding",
                   from_node=hits[0], to_node=hits[1],
                   provenance={"source": "artifact", "artifact": "20-specialist-findings", "locator": f["id"]},
                   confidence=f.get("confidence", "medium"), traversal_cost=cost,
                   finding_id=f["id"],
               ))


   def _add_capability_edges(g: Graph, capabilities: list[dict]) -> None:
       node_names = {n.name.lower(): n.node_id for n in [g.get_node(nid) for nid in g._nodes]}
       for c in capabilities:
           text = " ".join([c.get("detail", "")] + [e.get("excerpt", "") for e in c.get("evidence", [])])
           hits = [nid for name, nid in node_names.items() if name in text.lower()]
           if len(hits) >= 2:
               g.add_edge(Edge(
                   edge_id=stable_id("edge", hits[0], hits[1], "mitigated_by_capability", c["id"]),
                   edge_type="mitigated_by_capability",
                   from_node=hits[0], to_node=hits[1],
                   provenance={"source": "artifact", "artifact": "30-specialist-capabilities", "locator": c["id"]},
                   confidence=c.get("confidence", "medium"), traversal_cost=1,
                   capability_id=c["id"],
               ))


   def _add_threat_model_edges(g: Graph, tm: dict) -> None:
       """For each TM entry whose `asset` matches an inventory asset, wire a
       network_reachable edge from any attacker_position to that asset with
       provenance.source = "threat_model".
       """
       node_names = {n.name.lower(): n.node_id for n in [g.get_node(nid) for nid in g._nodes]}
       attackers = g.nodes_by_type("attacker_position")
       for entry in tm.get("entries", []):
           asset_lower = entry["asset"].lower()
           if asset_lower in node_names:
               asset_id = node_names[asset_lower]
               for atk in attackers:
                   conf = entry.get("extraction_confidence", "medium")
                   g.add_edge(Edge(
                       edge_id=stable_id("edge", atk.node_id, asset_id, "network_reachable", entry["entry_id"]),
                       edge_type="network_reachable",
                       from_node=atk.node_id, to_node=asset_id,
                       provenance={"source": "threat_model", "locator": entry["entry_id"]},
                       confidence=conf, traversal_cost=2,
                   ))


   def _add_code_evidence_edges(g: Graph, code: dict) -> None:
       """code-evidence-index entries declaring cross-service calls become
       network_reachable edges between the corresponding asset nodes."""
       node_names = {n.name.lower(): n.node_id for n in [g.get_node(nid) for nid in g._nodes]}
       for call in code.get("cross_service_calls", []):
           src = call.get("caller", "").lower()
           dst = call.get("callee", "").lower()
           if src in node_names and dst in node_names:
               g.add_edge(Edge(
                   edge_id=stable_id("edge", node_names[src], node_names[dst], "network_reachable", call.get("locator", "")),
                   edge_type="network_reachable",
                   from_node=node_names[src], to_node=node_names[dst],
                   provenance={"source": "code_evidence", "artifact": "00-context/code-evidence-index.yaml", "locator": call.get("locator", "")},
                   confidence="high", traversal_cost=1,
               ))
   ```

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_path_build.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/attack_path/build.py tests/test_attack_path_build.py tests/fixtures/attack_path/
   git commit -m "feat(attack_path): graph builder consuming inventory, TM, code-evidence, findings, capabilities"
   ```

---

## Task C-11: Bounded DFS path enumeration with edge-set pruning

**Goal:** Pure algorithm — given a Graph plus `(attacker_position, crown_jewel)` pair and bounds, produce a sorted list of paths with per-path metadata. Deterministic ordering. No I/O.

**Files:**

- Create: `tools/apd_gauntlet/attack_path/enumerate.py`
- Create: `tests/test_attack_path_enumerate.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from apd_gauntlet.attack_path.graph import Edge, Graph, Node
   from apd_gauntlet.attack_path.enumerate import enumerate_paths, Path, EnumerationParams

   def _two_hop_graph():
       g = Graph()
       atk = Node("atk-aaaaaaaa", "attacker_position", "ext",
                  {"source": "domain_default"}, "high")
       a1  = Node("asset-aaaaaaaa", "asset", "gateway",
                  {"source": "artifact"}, "high")
       jwl = Node("jewel-aaaaaaaa", "crown_jewel", "phi",
                  {"source": "domain_default"}, "high")
       for n in (atk, a1, jwl): g.add_node(n)
       g.add_edge(Edge("edge-aaaaaaaa", "network_reachable",
                       "atk-aaaaaaaa", "asset-aaaaaaaa",
                       {"source": "artifact"}, "high", 1))
       g.add_edge(Edge("edge-bbbbbbbb", "data_resides_on",
                       "asset-aaaaaaaa", "jewel-aaaaaaaa",
                       {"source": "artifact"}, "high", 1))
       return g

   def test_enumerate_finds_simple_two_hop_path():
       g = _two_hop_graph()
       paths = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa",
                               EnumerationParams(max_hop=8, max_paths_per_pair=50, bottleneck_threshold=5))
       assert len(paths) == 1
       assert paths[0].hop_count == 2
       assert paths[0].edges == ("edge-aaaaaaaa", "edge-bbbbbbbb")

   def test_enumerate_honors_max_hop_cap():
       # Build a 5-hop graph; ask for max_hop=3 → no path reaches jewel
       # ...
       ...

   def test_enumerate_uses_edge_set_pruning_not_node_set():
       # Two parallel edges between the same nodes — enumeration must allow
       # both as alternate paths
       ...

   def test_enumerate_truncates_at_max_paths_per_pair():
       # Build a 'fan' graph with 50+ distinct paths; ask for max=10 → exactly 10
       ...

   def test_path_feasibility_is_floor_of_edge_confidences():
       # Graph with high → medium → low → high edges → feasibility low
       ...

   def test_path_severity_sum_aggregates_compromisable_edges():
       # Graph with two compromisable_via_finding edges (critical, high) → severity_sum 7 (4+3)
       ...

   def test_path_mitigation_count_aggregates_capability_edges():
       # Graph with two mitigated_by_capability edges along path → mitigation_count 2
       ...

   def test_enumerate_orders_paths_descending_severity_then_ascending_hops_then_descending_feasibility():
       # Build graph yielding 3 paths with distinguishable metadata; assert exact order
       ...

   def test_enumerate_self_loop_skipped():
       # Edge from node to itself — never traversed
       ...

   def test_enumerate_returns_empty_when_no_path_exists():
       # Disconnected attacker and jewel → []
       ...

   def test_enumerate_deterministic_across_runs():
       # Same input → identical path_id sequence
       g = _two_hop_graph()
       params = EnumerationParams(max_hop=8, max_paths_per_pair=50, bottleneck_threshold=5)
       p1 = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa", params)
       p2 = enumerate_paths(g, "atk-aaaaaaaa", "jewel-aaaaaaaa", params)
       assert [p.path_id for p in p1] == [p.path_id for p in p2]
   ```

   Fill in the omitted test bodies during implementation — each test should construct a small graph with 3-6 nodes proving the asserted property.

- [ ] **Step 2: Implement `tools/apd_gauntlet/attack_path/enumerate.py`**

   ```python
   """Bounded DFS path enumeration with edge-set pruning.

   Given a graph and (attacker, crown_jewel) pair, walks every distinct
   acyclic path (cycles prevented by visited-edge-set, not visited-node-set —
   so parallel edges between same nodes are valid alternate paths) up to
   max_hop depth. Sorts by (-severity_sum, hop_count, -feasibility_rank,
   path_id) and truncates at max_paths_per_pair.
   """

   from __future__ import annotations

   import hashlib
   from dataclasses import dataclass
   from typing import Literal

   from .graph import Edge, Graph

   _CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
   _SEVERITY_SCORE  = {"critical": 4, "high": 3, "medium": 2, "low": 1, "informational": 0}


   @dataclass(frozen=True)
   class EnumerationParams:
       max_hop: int
       max_paths_per_pair: int
       bottleneck_threshold: int


   @dataclass(frozen=True)
   class Path:
       path_id: str
       attacker_position: str
       crown_jewel: str
       edges: tuple[str, ...]
       hop_count: int
       feasibility: Literal["high", "medium", "low"]
       severity_sum: int
       mitigation_count: int


   def enumerate_paths(
       g: Graph,
       attacker_node_id: str,
       crown_jewel_node_id: str,
       params: EnumerationParams,
       *,
       findings_by_id: dict[str, dict] | None = None,
   ) -> list[Path]:
       """DFS from attacker to jewel; emits all acyclic paths up to max_hop."""
       findings_by_id = findings_by_id or {}
       raw: list[Path] = []
       _dfs(g, attacker_node_id, crown_jewel_node_id, params.max_hop,
            visited_edges=set(), trail=[], collector=raw,
            findings_by_id=findings_by_id,
            attacker=attacker_node_id, jewel=crown_jewel_node_id)
       raw.sort(key=lambda p: (
           -p.severity_sum,
           p.hop_count,
           -_CONFIDENCE_RANK[p.feasibility],
           p.path_id,
       ))
       return raw[: params.max_paths_per_pair]


   def _dfs(g, current, target, depth, *, visited_edges, trail, collector,
            findings_by_id, attacker, jewel):
       if depth <= 0:
           return
       for edge in g.outgoing(current):
           if edge.edge_id in visited_edges:
               continue
           if edge.from_node == edge.to_node:
               continue  # self-loop
           trail.append(edge.edge_id)
           visited_edges.add(edge.edge_id)
           if edge.to_node == target:
               collector.append(_finalize_path(g, attacker, jewel, tuple(trail), findings_by_id))
           else:
               _dfs(g, edge.to_node, target, depth - 1,
                    visited_edges=visited_edges, trail=trail, collector=collector,
                    findings_by_id=findings_by_id, attacker=attacker, jewel=jewel)
           trail.pop()
           visited_edges.discard(edge.edge_id)


   def _finalize_path(g, attacker, jewel, edge_ids, findings_by_id):
       edges = [g.get_edge(eid) for eid in edge_ids]
       confidences = [e.confidence for e in edges]
       feasibility = min(confidences, key=lambda c: _CONFIDENCE_RANK[c])
       severity_sum = sum(
           _SEVERITY_SCORE.get(findings_by_id.get(e.finding_id, {}).get("severity", "informational"), 0)
           for e in edges if e.edge_type == "compromisable_via_finding"
       )
       mitigation_count = sum(1 for e in edges if e.edge_type == "mitigated_by_capability")
       digest = hashlib.sha256("|".join(edge_ids).encode()).hexdigest()[:8]
       return Path(
           path_id=f"path-{digest}",
           attacker_position=attacker,
           crown_jewel=jewel,
           edges=edge_ids,
           hop_count=len(edge_ids),
           feasibility=feasibility,
           severity_sum=severity_sum,
           mitigation_count=mitigation_count,
       )


   def compute_bottleneck_edges(paths: list[Path], threshold: int) -> dict[str, list[str]]:
       """Returns {edge_id: [path_id, ...]} for edges appearing on `threshold` or more paths."""
       counts: dict[str, list[str]] = {}
       for p in paths:
           for eid in p.edges:
               counts.setdefault(eid, []).append(p.path_id)
       return {eid: pids for eid, pids in counts.items() if len(pids) >= threshold}
   ```

- [ ] **Step 3: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_path_enumerate.py -v
   pytest -q
   git add tools/apd_gauntlet/attack_path/enumerate.py tests/test_attack_path_enumerate.py
   git commit -m "feat(attack_path): bounded DFS enumeration with edge-set pruning + bottleneck detection"
   ```

---

## Task C-12: D3FEND overlay computation

**Goal:** Given a list of bottleneck edges plus dedup'd findings (for ATT&CK technique extraction) plus capabilities (for existing D3FEND backing), produce the defense-graph artifact's `bottleneck_overlays[]`.

**Files:**

- Create: `tools/apd_gauntlet/attack_path/d3fend_overlay.py`
- Create: `tests/test_d3fend_overlay.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from apd_gauntlet.attack_path.d3fend_overlay import (
       build_overlays, _lookup_d3fend_counters,
   )

   D3FEND_DATA = {
       "techniques": [
           {"id": "D3-NTSA", "name": "Network Traffic Signature Analysis",
            "counters_attack": ["T1078", "T1190"]},
           {"id": "D3-IBCA", "name": "Inbound Session Volume Analysis",
            "counters_attack": ["T1078"]},
           {"id": "D3-MFA",  "name": "Multi-factor Authentication",
            "counters_attack": ["T1078", "T1110"]},
       ]
   }

   def test_lookup_d3fend_counters_returns_only_techniques_that_counter_input():
       counters = _lookup_d3fend_counters(["T1078"], D3FEND_DATA)
       ids = {c["d3fend_id"] for c in counters}
       assert ids == {"D3-NTSA", "D3-IBCA", "D3-MFA"}

   def test_lookup_d3fend_counters_filters_by_intersection():
       counters = _lookup_d3fend_counters(["T1190"], D3FEND_DATA)
       ids = {c["d3fend_id"] for c in counters}
       assert ids == {"D3-NTSA"}

   def test_lookup_d3fend_counters_handles_empty():
       assert _lookup_d3fend_counters([], D3FEND_DATA) == []

   def test_build_overlays_extracts_attack_techniques_from_compromisable_edges():
       # Two finding-edges on a bottleneck edge → unioned ATT&CK techniques
       # Stub graph, findings_by_id, capabilities, d3fend_data, paths
       ...

   def test_build_overlays_marks_existing_capability_backing():
       # Capability has D3FEND mapping that counters the bottleneck's ATT&CK technique
       # → that D3FEND id appears in existing_capability_backing, not net_new_d3fend
       ...

   def test_build_overlays_net_new_d3fend_excludes_already_backed():
       # Bottleneck exposes T1078; D3-NTSA, D3-IBCA, D3-MFA all counter T1078;
       # one capability provides D3-MFA → net_new = {D3-NTSA, D3-IBCA}
       ...
   ```

- [ ] **Step 2: Implement `tools/apd_gauntlet/attack_path/d3fend_overlay.py`**

   ```python
   """D3FEND defensive overlay computation.

   For each bottleneck edge, collect the ATT&CK techniques exposed (from the
   finding(s) backing the edge), look up D3FEND techniques that counter those,
   partition by existing-capability-backing vs net-new.
   """

   from __future__ import annotations

   import json
   from pathlib import Path
   from typing import Any

   from .enumerate import Path as APath

   _D3FEND_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "d3fend.json"


   def load_d3fend_data() -> dict:
       return json.loads(_D3FEND_DATA_PATH.read_text())


   def _lookup_d3fend_counters(attack_technique_ids: list[str], d3fend: dict) -> list[dict]:
       wanted = set(attack_technique_ids)
       hits: list[dict] = []
       for t in d3fend.get("techniques", []):
           covered = set(t.get("counters_attack", [])) & wanted
           if not covered:
               continue
           hits.append({
               "d3fend_id": t["id"],
               "counters": sorted(covered),
               "rationale": f"D3FEND {t['id']} ({t.get('name', '')}) counters ATT&CK {', '.join(sorted(covered))} per MITRE D3FEND attack-counter mapping",
           })
       return sorted(hits, key=lambda h: h["d3fend_id"])


   def build_overlays(
       *,
       paths: list[APath],
       bottleneck_edges: dict[str, list[str]],
       graph,
       findings_by_id: dict[str, dict],
       capabilities: list[dict],
       d3fend_data: dict,
   ) -> list[dict]:
       """Returns list of bottleneck_overlay objects matching defense-graph.schema.json."""
       overlays: list[dict] = []

       # Index capabilities by D3FEND technique they implement
       cap_by_d3fend: dict[str, list[str]] = {}
       for cap in capabilities:
           for entry in (cap.get("control_mappings", {}).get("d3fend") or []):
               cap_by_d3fend.setdefault(entry["technique"], []).append(cap["id"])

       for edge_id, traversing_path_ids in sorted(bottleneck_edges.items()):
           edge = graph.get_edge(edge_id)
           # Bottleneck overlays are only meaningful for compromisable_via_finding edges
           # (other edge types don't have ATT&CK techniques to counter).
           if edge.edge_type != "compromisable_via_finding":
               continue
           finding = findings_by_id.get(edge.finding_id)
           if not finding:
               continue
           attack_techs = sorted({
               e["technique"]
               for e in (finding.get("control_mappings", {}).get("mitre_attack") or [])
           })
           if not attack_techs:
               continue
           candidate = _lookup_d3fend_counters(attack_techs, d3fend_data)

           existing_backing = []
           net_new = []
           for cand in candidate:
               backers = cap_by_d3fend.get(cand["d3fend_id"], [])
               if backers:
                   existing_backing.append({
                       "d3fend_id": cand["d3fend_id"],
                       "capability_ids": sorted(backers),
                   })
               else:
                   net_new.append(cand["d3fend_id"])

           overlays.append({
               "edge_id": edge_id,
               "paths_traversing": len(traversing_path_ids),
               "exposed_attack_techniques": attack_techs,
               "candidate_d3fend": candidate,
               "existing_capability_backing": existing_backing,
               "net_new_d3fend": sorted(net_new),
           })

       return overlays
   ```

- [ ] **Step 3: Run tests + linters + commit**

   ```bash
   pytest tests/test_d3fend_overlay.py -v
   pytest -q
   git add tools/apd_gauntlet/attack_path/d3fend_overlay.py tests/test_d3fend_overlay.py
   git commit -m "feat(attack_path): D3FEND defensive overlay with capability-backing partition"
   ```

---

## Task C-13: Mermaid diagram emission with 50-node cap + partitioning

**Goal:** Render the graph (or a path subset) as Mermaid `flowchart LR` syntax suitable for fenced ` ```mermaid ` blocks. Cap at 50 nodes per diagram; partition by attacker_position when the full graph exceeds the cap.

**Files:**

- Create: `tools/apd_gauntlet/attack_path/mermaid.py`
- Create: `tests/test_attack_path_mermaid.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from apd_gauntlet.attack_path.mermaid import render_path_diagram, render_partitioned_diagrams

   def test_render_path_diagram_emits_flowchart_lr():
       output = render_path_diagram(paths=[_sample_path()], graph=_sample_graph())
       assert output.startswith("flowchart LR\n")

   def test_render_path_diagram_includes_all_path_nodes():
       g = _sample_graph()
       p = _sample_path()
       output = render_path_diagram(paths=[p], graph=g)
       for node_id in _path_nodes(g, p):
           assert node_id in output

   def test_render_path_diagram_labels_edges_with_edge_type():
       output = render_path_diagram(paths=[_sample_path()], graph=_sample_graph())
       assert "compromisable_via_finding" in output or "network_reachable" in output

   def test_render_partitioned_diagrams_partitions_when_node_cap_exceeded():
       # Build graph with 100+ nodes spread across 3 attacker_positions
       diagrams = render_partitioned_diagrams(paths=_many_paths(), graph=_large_graph())
       assert len(diagrams) >= 3  # one per attacker partition
       for d in diagrams:
           # Node count check: count Mermaid node declarations (lines like "node_id[...]")
           node_lines = [l for l in d.splitlines() if "[" in l and l.strip()[0].isalpha()]
           assert len(node_lines) <= 50

   def test_render_partitioned_diagrams_single_diagram_when_below_cap():
       diagrams = render_partitioned_diagrams(paths=[_sample_path()], graph=_sample_graph())
       assert len(diagrams) == 1

   def test_mermaid_output_is_valid_against_basic_syntax_pattern():
       output = render_path_diagram(paths=[_sample_path()], graph=_sample_graph())
       # Every non-blank non-comment line should be either a node declaration or edge
       import re
       lines = [l for l in output.splitlines()[1:] if l.strip()]
       node_pat = re.compile(r"^\s*[A-Za-z_][\w-]*(\[.*\])?$")
       edge_pat = re.compile(r"^\s*[A-Za-z_][\w-]*\s*--.*-->\s*[A-Za-z_][\w-]*$")
       for line in lines:
           assert node_pat.match(line) or edge_pat.match(line), f"unrecognized mermaid syntax: {line!r}"
   ```

- [ ] **Step 2: Implement `tools/apd_gauntlet/attack_path/mermaid.py`**

   ```python
   """Mermaid flowchart rendering for attack-path diagrams.

   Constraints:
     - 50-node cap per diagram
     - When the path-set spans more than 50 nodes, partition by attacker_position
     - Mermaid uses `flowchart LR` (left-to-right) for readable kill-chains
     - Node IDs must be sanitized for Mermaid (no hyphens in identifiers → replace with underscore)
     - Edge labels are pipe-escaped to avoid breaking Mermaid syntax
   """

   from __future__ import annotations

   from collections import defaultdict

   from .enumerate import Path as APath
   from .graph import Graph

   _MAX_NODES_PER_DIAGRAM = 50


   def _sanitize(node_id: str) -> str:
       return node_id.replace("-", "_")


   def _node_label(graph: Graph, node_id: str) -> str:
       n = graph.get_node(node_id)
       icon = {
           "asset": "S",
           "identity": "I",
           "attacker_position": "X",
           "crown_jewel": "J",
       }[n.node_type]
       safe_name = n.name.replace("|", "/").replace("[", "(").replace("]", ")")
       return f'{_sanitize(node_id)}["{icon}: {safe_name}"]'


   def _edge_label(graph: Graph, edge_id: str) -> str:
       e = graph.get_edge(edge_id)
       label = f"{e.edge_type}/{e.confidence}"
       if e.edge_type == "compromisable_via_finding":
           label += f" ({e.finding_id})"
       elif e.edge_type == "mitigated_by_capability":
           label += f" ({e.capability_id})"
       label = label.replace("|", "/")
       return f"{_sanitize(e.from_node)} --|{label}|--> {_sanitize(e.to_node)}"


   def render_path_diagram(*, paths: list[APath], graph: Graph) -> str:
       node_ids: list[str] = []
       seen_nodes: set[str] = set()
       edge_ids: list[str] = []
       seen_edges: set[str] = set()
       for p in paths:
           for eid in p.edges:
               if eid in seen_edges:
                   continue
               seen_edges.add(eid)
               edge_ids.append(eid)
               e = graph.get_edge(eid)
               for nid in (e.from_node, e.to_node):
                   if nid not in seen_nodes:
                       seen_nodes.add(nid)
                       node_ids.append(nid)

       lines = ["flowchart LR"]
       lines.extend(_node_label(graph, nid) for nid in node_ids)
       lines.extend(_edge_label(graph, eid) for eid in edge_ids)
       return "\n".join(lines) + "\n"


   def render_partitioned_diagrams(*, paths: list[APath], graph: Graph) -> list[str]:
       all_nodes: set[str] = set()
       for p in paths:
           for eid in p.edges:
               e = graph.get_edge(eid)
               all_nodes.add(e.from_node); all_nodes.add(e.to_node)

       if len(all_nodes) <= _MAX_NODES_PER_DIAGRAM:
           return [render_path_diagram(paths=paths, graph=graph)]

       # Partition by attacker_position
       by_attacker: dict[str, list[APath]] = defaultdict(list)
       for p in paths:
           by_attacker[p.attacker_position].append(p)

       diagrams: list[str] = []
       for atk, ps in sorted(by_attacker.items()):
           # Further bound: take top-K paths whose union node count stays under cap
           subset: list[APath] = []
           subset_nodes: set[str] = set()
           for p in ps:
               candidate_nodes = set(subset_nodes)
               for eid in p.edges:
                   e = graph.get_edge(eid)
                   candidate_nodes.add(e.from_node); candidate_nodes.add(e.to_node)
               if len(candidate_nodes) > _MAX_NODES_PER_DIAGRAM:
                   break
               subset_nodes = candidate_nodes
               subset.append(p)
           if subset:
               diagrams.append(render_path_diagram(paths=subset, graph=graph))
       return diagrams
   ```

- [ ] **Step 3: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_path_mermaid.py -v
   pytest -q
   git add tools/apd_gauntlet/attack_path/mermaid.py tests/test_attack_path_mermaid.py
   git commit -m "feat(attack_path): Mermaid flowchart rendering with 50-node cap + attacker partitioning"
   ```

---

## Task C-14: Findings emission — the four `apath-*` flavors

**Goal:** Given enumerated paths + bottleneck overlays + graph + findings/capabilities, emit the four finding flavors per design spec §7.6. Each as a dict matching `finding.schema.json`.

**Files:**

- Create: `tools/apd_gauntlet/attack_path/findings.py`
- Create: `tests/test_attack_path_findings.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from apd_gauntlet.attack_path.findings import emit_findings

   def test_emits_high_severity_risk_for_high_feasibility_paths_with_no_mitigation():
       findings = emit_findings(paths=_high_path_no_mitigation(), overlays=[], graph=_g(), findings_by_id={}, capabilities=[])
       assert any(f["disposition"] == "risk" and f["severity"] in ("critical", "high") for f in findings)

   def test_emits_uncertainty_for_low_feasibility_paths():
       findings = emit_findings(paths=_low_feasibility_path(), overlays=[], graph=_g(), findings_by_id={}, capabilities=[])
       assert any(f["disposition"] == "uncertainty" for f in findings)
       # Severity caps at low for uncertainty paths
       for f in findings:
           if f["disposition"] == "uncertainty":
               assert f["severity"] in ("low", "informational", "medium")

   def test_emits_gap_for_bottleneck_with_no_d3fend_capability_backing():
       findings = emit_findings(
           paths=_paths_sharing_edge(),
           overlays=[{"edge_id": "edge-aaaaaaaa", "paths_traversing": 6,
                      "exposed_attack_techniques": ["T1078"],
                      "candidate_d3fend": [{"d3fend_id": "D3-NTSA", "counters": ["T1078"], "rationale": "..."}],
                      "existing_capability_backing": [],
                      "net_new_d3fend": ["D3-NTSA"]}],
           graph=_g(), findings_by_id={}, capabilities=[],
       )
       gap_findings = [f for f in findings if f["disposition"] == "gap"]
       assert gap_findings, "bottleneck with no capability backing must emit a gap finding"

   def test_emits_blocked_when_no_paths_no_overlays_but_crown_jewels_declared():
       # If enumeration ran but produced zero paths, that's interesting but not blocked.
       # Blocked is reserved for upstream BuilderBlocked — tested in CLI layer instead.
       # This test asserts emit_findings on empty inputs returns []
       assert emit_findings(paths=[], overlays=[], graph=_g(), findings_by_id={}, capabilities=[]) == []

   def test_all_findings_have_apath_id_pattern():
       findings = emit_findings(paths=_high_path_no_mitigation(), overlays=[], graph=_g(), findings_by_id={}, capabilities=[])
       for f in findings:
           assert f["id"].startswith("apath-")
           assert len(f["id"]) == len("apath-") + 8

   def test_all_findings_carry_at_least_one_evidence_entry():
       findings = emit_findings(paths=_high_path_no_mitigation(), overlays=[], graph=_g(), findings_by_id={}, capabilities=[])
       for f in findings:
           assert len(f["evidence"]) >= 1
   ```

- [ ] **Step 2: Implement `tools/apd_gauntlet/attack_path/findings.py`**

   ```python
   """Emit apath-* findings from enumeration results + D3FEND overlays.

   Four flavors per design spec §7.6:
     1. risk (severity critical|high) — high-feasibility path, no mitigation
     2. uncertainty — low-feasibility paths (capped at medium severity)
     3. gap — bottleneck edge with no D3FEND-backed capability
     4. blocked — emitted by the CLI/agent layer when BuilderBlocked is raised;
        this module does not need to emit blocked findings.
   """

   from __future__ import annotations

   import hashlib

   from .enumerate import Path as APath
   from .graph import Graph

   _SEVERITY_FOR_RISK = {3: "high", 4: "critical", 5: "critical", 6: "critical"}
   _UNCERTAINTY_SEVERITY = "low"


   def emit_findings(
       *, paths: list[APath], overlays: list[dict], graph: Graph,
       findings_by_id: dict[str, dict], capabilities: list[dict],
   ) -> list[dict]:
       out: list[dict] = []
       for p in paths:
           out.append(_finding_from_path(p, graph, findings_by_id))
       for overlay in overlays:
           if overlay.get("net_new_d3fend") and not overlay.get("existing_capability_backing"):
               out.append(_finding_from_bottleneck(overlay, graph, findings_by_id))
       # Deterministic order
       out.sort(key=lambda f: f["id"])
       return out


   def _finding_from_path(p: APath, g: Graph, findings_by_id: dict[str, dict]) -> dict:
       low_feasibility = p.feasibility == "low"
       no_mitigation = p.mitigation_count == 0

       if low_feasibility:
           disposition = "uncertainty"
           severity = _UNCERTAINTY_SEVERITY
           confidence = "low"
           title_prefix = "Low-feasibility attack path"
       elif no_mitigation and p.severity_sum >= 3:
           disposition = "risk"
           severity = _SEVERITY_FOR_RISK.get(p.severity_sum, "high")
           confidence = p.feasibility  # path's feasibility floor governs analyzer confidence
           title_prefix = "High-feasibility attack path with no capability coverage"
       else:
           disposition = "uncertainty"
           severity = "medium" if no_mitigation else "informational"
           confidence = p.feasibility
           title_prefix = "Attack path with partial mitigation"

       jewel = g.get_node(p.crown_jewel).name
       atk   = g.get_node(p.attacker_position).name
       short_hash = hashlib.sha256(p.path_id.encode()).hexdigest()[:8]
       summary = f"Path from {atk} to {jewel} in {p.hop_count} hop(s); feasibility={p.feasibility}; severity_sum={p.severity_sum}; mitigations on path={p.mitigation_count}."
       detail_edges = []
       for eid in p.edges:
           e = g.get_edge(eid)
           detail_edges.append(f"{g.get_node(e.from_node).name} --[{e.edge_type}/{e.confidence}]--> {g.get_node(e.to_node).name}")
       detail = f"Path: {' -> '.join(detail_edges)}. Feasibility floor = {p.feasibility}. Severity sum = {p.severity_sum}. Mitigations along path = {p.mitigation_count}."

       cross_refs = sorted({
           g.get_edge(eid).finding_id for eid in p.edges
           if g.get_edge(eid).edge_type == "compromisable_via_finding" and g.get_edge(eid).finding_id
       })

       return {
           "schema_version": 1,
           "id": f"apath-{short_hash}",
           "agent": "attack_path_analyzer",
           "apd_tier": _infer_tier(g, p, findings_by_id),
           "apd_goal": _infer_goal(g, p, findings_by_id),
           "disposition": disposition,
           "severity": severity,
           "confidence": confidence,
           "title": f"{title_prefix}: {atk} -> {jewel} in {p.hop_count} hop(s)",
           "summary": summary,
           "detail": detail,
           "evidence": [
               {"artifact": "40-synthesis/asset-graph.yaml",  "locator": f"edges (path {p.path_id})", "excerpt": detail_edges[0] if detail_edges else "(no edges)"},
               {"artifact": "40-synthesis/attack-paths.yaml", "locator": p.path_id,                  "excerpt": summary},
           ],
           "control_mappings": {
               "nist_800_53r5": _infer_nist_controls(g, p, findings_by_id),
           },
           "cross_references": list(cross_refs),
           "recommendation": {
               "posture": "required" if disposition == "risk" else "recommended",
               "summary": "Reduce path feasibility by adding capability coverage on the highest-confidence edge or removing a low-confidence reachability assumption",
               "detail": f"Path has {p.hop_count} hops with feasibility floor {p.feasibility}. Adding a capability on any high-confidence compromisable edge or strengthening identity controls along this path closes the kill-chain.",
           },
       }


   def _finding_from_bottleneck(overlay: dict, g: Graph, findings_by_id: dict[str, dict]) -> dict:
       edge_id = overlay["edge_id"]
       edge = g.get_edge(edge_id)
       net_new = overlay.get("net_new_d3fend", [])
       short_hash = hashlib.sha256(("bottleneck|" + edge_id).encode()).hexdigest()[:8]
       attack_techs = ", ".join(overlay.get("exposed_attack_techniques", []))
       d3fend_list = ", ".join(net_new)
       finding = findings_by_id.get(edge.finding_id, {})

       return {
           "schema_version": 1,
           "id": f"apath-{short_hash}",
           "agent": "attack_path_analyzer",
           "apd_tier": finding.get("apd_tier", "trustworthiness"),
           "apd_goal": finding.get("apd_goal", "authenticity"),
           "disposition": "gap",
           "severity": "high" if overlay.get("paths_traversing", 0) >= 5 else "medium",
           "confidence": "high",
           "title": f"Bottleneck edge {edge_id} exposes {attack_techs} with no D3FEND-backed capability ({d3fend_list} would counter)",
           "summary": f"Edge {edge_id} appears on {overlay.get('paths_traversing', 0)} enumerated paths and exposes ATT&CK technique(s) {attack_techs}. D3FEND counters {d3fend_list} are available but not implemented by any capability.",
           "detail": f"Bottleneck edge analysis: this edge sits on {overlay.get('paths_traversing', 0)} distinct enumerated paths. Adding a capability that implements any of {d3fend_list} breaks all of them. Existing capability backing for this technique: none.",
           "evidence": [
               {"artifact": "40-synthesis/asset-graph.yaml",   "locator": f"edges[{edge_id}]",  "excerpt": f"{edge.from_node} -> {edge.to_node} via {edge.edge_type}"},
               {"artifact": "40-synthesis/defense-graph.yaml", "locator": f"bottleneck_overlays[{edge_id}]", "excerpt": f"net_new_d3fend: {net_new}"},
           ],
           "control_mappings": {
               "nist_800_53r5": _infer_nist_controls_from_finding(finding),
           },
           "cross_references": [edge.finding_id] if edge.finding_id else [],
           "recommendation": {
               "posture": "required",
               "summary": f"Implement one of {d3fend_list} on the bottleneck edge {edge_id}",
               "detail": f"All {overlay.get('paths_traversing', 0)} enumerated paths through this edge share the same defensive opportunity. Single highest-leverage investment: pick a D3FEND technique from {d3fend_list} and design a capability around it.",
           },
       }


   def _infer_tier(g: Graph, p: APath, findings_by_id: dict[str, dict]) -> str:
       # If the path includes a compromisable_via_finding edge, inherit the finding's tier
       for eid in p.edges:
           e = g.get_edge(eid)
           if e.edge_type == "compromisable_via_finding" and e.finding_id in findings_by_id:
               return findings_by_id[e.finding_id].get("apd_tier", "trustworthiness")
       return "trustworthiness"


   def _infer_goal(g: Graph, p: APath, findings_by_id: dict[str, dict]) -> str:
       for eid in p.edges:
           e = g.get_edge(eid)
           if e.edge_type == "compromisable_via_finding" and e.finding_id in findings_by_id:
               return findings_by_id[e.finding_id].get("apd_goal", "authenticity")
       # Path with no finding-edge — pick by crown_jewel data class
       jewel = g.get_node(p.crown_jewel)
       if "phi" in (jewel.data_classifications or ()):
           return "confidentiality"
       return "authenticity"


   def _infer_nist_controls(g: Graph, p: APath, findings_by_id: dict[str, dict]) -> list[str]:
       controls: set[str] = set()
       for eid in p.edges:
           e = g.get_edge(eid)
           if e.edge_type == "compromisable_via_finding" and e.finding_id in findings_by_id:
               for c in findings_by_id[e.finding_id].get("control_mappings", {}).get("nist_800_53r5", []):
                   controls.add(c)
       if not controls:
           controls = {"CA-3", "SA-8"}  # baseline architecture controls
       return sorted(controls)


   def _infer_nist_controls_from_finding(finding: dict) -> list[str]:
       controls = list(finding.get("control_mappings", {}).get("nist_800_53r5", []))
       return sorted(set(controls) | {"SA-8"})  # SA-8 = security & privacy engineering principles
   ```

- [ ] **Step 3: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_path_findings.py -v
   pytest -q
   git add tools/apd_gauntlet/attack_path/findings.py tests/test_attack_path_findings.py
   git commit -m "feat(attack_path): emit four apath- finding flavors (risk, uncertainty, gap, partial)"
   ```

---

## Task C-15: CLI subcommand `apd-gauntlet analyze-attack-paths`

**Goal:** Wire the attack_path package into the CLI as a deterministic, headless-callable subcommand. Mirrors `apd-gauntlet parse-threat-model` from Phase B. Reads a run directory, writes `40-synthesis/asset-graph.yaml`, `40-synthesis/attack-paths.yaml`, `40-synthesis/defense-graph.yaml`, and a `40-synthesis/attack-path-findings.yaml` (the `apath-*` records, in the same wrapper shape specialist agents emit).

**Files:**

- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_cli_analyze_attack_paths.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from click.testing import CliRunner
   from apd_gauntlet.cli import main

   def test_analyze_attack_paths_writes_four_artifacts(tmp_path):
       runner = CliRunner()
       _scaffold_minimal_run(tmp_path)
       result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
       assert result.exit_code == 0, result.output
       synth = tmp_path / "40-synthesis"
       assert (synth / "asset-graph.yaml").exists()
       assert (synth / "attack-paths.yaml").exists()
       assert (synth / "defense-graph.yaml").exists()
       assert (synth / "attack-path-findings.yaml").exists()

   def test_analyze_attack_paths_emits_blocked_finding_when_no_crown_jewels(tmp_path):
       runner = CliRunner()
       _scaffold_run_without_crown_jewels(tmp_path)
       result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
       assert result.exit_code == 0  # blocked is not an error
       findings_doc = yaml.safe_load((tmp_path / "40-synthesis" / "attack-path-findings.yaml").read_text())
       blocked = [f for f in findings_doc["findings"] if f["disposition"] == "blocked"]
       assert blocked
       assert "crown jewels" in blocked[0]["title"].lower()

   def test_analyze_attack_paths_honors_run_config_tuning(tmp_path):
       runner = CliRunner()
       _scaffold_minimal_run(tmp_path, max_hop=4, max_paths_per_pair=10)
       result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
       assert result.exit_code == 0
       attack_paths = yaml.safe_load((tmp_path / "40-synthesis" / "attack-paths.yaml").read_text())
       assert attack_paths["enumeration_parameters"]["max_hop"] == 4
       assert attack_paths["enumeration_parameters"]["max_paths_per_pair"] == 10

   def test_analyze_attack_paths_validates_output_against_schemas(tmp_path):
       runner = CliRunner()
       _scaffold_minimal_run(tmp_path)
       result = runner.invoke(main, ["analyze-attack-paths", str(tmp_path)])
       assert result.exit_code == 0
       # Run validate-run on the output dir; assert clean
       result2 = runner.invoke(main, ["validate", str(tmp_path)])
       assert result2.exit_code == 0, result2.output
   ```

- [ ] **Step 2: Implement the subcommand**

   Add to `tools/apd_gauntlet/cli.py` (after the existing `parse-threat-model` command):

   ```python
   @main.command("analyze-attack-paths")
   @click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
   def analyze_attack_paths(run_dir: Path) -> None:
       """Build the asset graph, enumerate attack paths, compute D3FEND overlay, emit findings.

       Reads run_dir/00-context/asset-inventory.yaml plus optional TM/code-evidence
       artifacts and all specialist findings/capabilities. Writes:
         - 40-synthesis/asset-graph.yaml
         - 40-synthesis/attack-paths.yaml
         - 40-synthesis/defense-graph.yaml
         - 40-synthesis/attack-path-findings.yaml
       """
       from .attack_path.build import build_graph, BuilderBlocked
       from .attack_path.enumerate import EnumerationParams, enumerate_paths, compute_bottleneck_edges
       from .attack_path.d3fend_overlay import build_overlays, load_d3fend_data
       from .attack_path.findings import emit_findings

       synth = run_dir / "40-synthesis"
       synth.mkdir(parents=True, exist_ok=True)
       run_cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text()) if (run_dir / ".apd-run.yaml").exists() else {}
       tuning = run_cfg.get("attack_path_analysis", {}) or {}
       params = EnumerationParams(
           max_hop              = int(tuning.get("max_hop", 8)),
           max_paths_per_pair   = int(tuning.get("max_paths_per_pair", 50)),
           bottleneck_threshold = int(tuning.get("bottleneck_threshold", 5)),
       )

       try:
           result = build_graph(run_dir)
       except BuilderBlocked as exc:
           _write_blocked_finding(synth, reason=str(exc))
           click.echo(f"analyze-attack-paths: blocked — {exc}")
           return

       graph = result.graph
       attackers = graph.nodes_by_type("attacker_position")
       jewels    = graph.nodes_by_type("crown_jewel")

       # Index findings/capabilities for downstream use
       findings_by_id, capabilities = _load_records(run_dir)

       all_paths: list = []
       truncated_pairs = 0
       for atk in attackers:
           for jwl in jewels:
               raw = enumerate_paths(graph, atk.node_id, jwl.node_id, params, findings_by_id=findings_by_id)
               if len(raw) == params.max_paths_per_pair:
                   truncated_pairs += 1
               all_paths.extend(raw)

       bottleneck_edges = compute_bottleneck_edges(all_paths, params.bottleneck_threshold)
       d3fend_data = load_d3fend_data()
       overlays = build_overlays(
           paths=all_paths, bottleneck_edges=bottleneck_edges, graph=graph,
           findings_by_id=findings_by_id, capabilities=capabilities, d3fend_data=d3fend_data,
       )
       findings = emit_findings(
           paths=all_paths, overlays=overlays, graph=graph,
           findings_by_id=findings_by_id, capabilities=capabilities,
       )

       _write_asset_graph(synth / "asset-graph.yaml", graph, result.sources_used)
       _write_attack_paths(synth / "attack-paths.yaml", all_paths, params, truncated_pairs, len(bottleneck_edges))
       _write_defense_graph(synth / "defense-graph.yaml", overlays)
       _write_findings(synth / "attack-path-findings.yaml", findings)

       click.echo(f"analyze-attack-paths: wrote {len(all_paths)} paths, {len(bottleneck_edges)} bottlenecks, {len(findings)} findings")


   def _write_blocked_finding(synth: Path, *, reason: str) -> None:
       short_hash = hashlib.sha256(reason.encode()).hexdigest()[:8]
       doc = {
           "schema_version": 1,
           "findings": [{
               "schema_version": 1,
               "id": f"apath-{short_hash}",
               "agent": "attack_path_analyzer",
               "apd_tier": "trustworthiness",
               "apd_goal": "authenticity",
               "disposition": "blocked",
               "severity": "informational",
               "confidence": "high",
               "title": f"Attack-path analysis blocked: {reason}",
               "summary": f"The analyzer could not run because {reason}. Declare crown_jewels[] in the domain pack or .apd-run.yaml to enable attack-path analysis.",
               "detail": "See ADR-0010 (Attack-path analysis on partial graphs) for the block-on-missing-crown-jewels discipline.",
               "evidence": [{"artifact": ".apd-run.yaml", "locator": "crown_jewels", "excerpt": "(absent or empty)"}],
               "prerequisite_evidence": ["domain pack or run-config must declare crown_jewels[] and attacker_positions[]"],
               "control_mappings": {"nist_800_53r5": ["SA-8"]},
               "recommendation": {
                   "posture": "required",
                   "summary": "Declare crown jewels and attacker positions in the domain pack or run-config",
                   "detail": "The PBM domain pack ships defaults (phi_store, pde_submission_pipeline, claim_adjudication_engine); see docs/attack-path-analysis.md for declaration patterns in other domains.",
               },
           }],
       }
       (synth / "attack-path-findings.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


   def _load_records(run_dir: Path) -> tuple[dict[str, dict], list[dict]]:
       findings_by_id: dict[str, dict] = {}
       capabilities: list[dict] = []
       fdir = run_dir / "20-specialist-findings"
       if fdir.exists():
           for f in sorted(fdir.glob("*.findings.yaml")):
               doc = yaml.safe_load(f.read_text()) or {}
               for rec in doc.get("findings", []) or []:
                   findings_by_id[rec["id"]] = rec
       cdir = run_dir / "30-specialist-capabilities"
       if cdir.exists():
           for f in sorted(cdir.glob("*.capabilities.yaml")):
               doc = yaml.safe_load(f.read_text()) or {}
               capabilities.extend(doc.get("capabilities", []) or [])
       return findings_by_id, capabilities


   def _write_asset_graph(path: Path, graph, sources_used: list[str]) -> None:
       doc = {
           "schema_version": 1,
           "generated_by": "attack_path_analyzer",
           "nodes": [_serialize_node(n) for n in sorted(graph._nodes.values(), key=lambda n: n.node_id)],
           "edges": [_serialize_edge(e) for e in sorted(graph._edges.values(), key=lambda e: e.edge_id)],
           "build_summary": {
               "node_count": graph.node_count,
               "edge_count": graph.edge_count,
               "attacker_position_count": len(graph.nodes_by_type("attacker_position")),
               "crown_jewel_count":       len(graph.nodes_by_type("crown_jewel")),
               "finding_edges_count":     sum(1 for e in graph._edges.values() if e.edge_type == "compromisable_via_finding"),
               "capability_edges_count":  sum(1 for e in graph._edges.values() if e.edge_type == "mitigated_by_capability"),
               "sources_used": sources_used,
           },
       }
       path.write_text(yaml.safe_dump(doc, sort_keys=False))


   def _serialize_node(n) -> dict:
       out = {"node_id": n.node_id, "node_type": n.node_type, "name": n.name,
              "provenance": n.provenance, "confidence": n.confidence}
       if n.asset_type:           out["asset_type"] = n.asset_type
       if n.data_classifications: out["data_classifications"] = list(n.data_classifications)
       return out


   def _serialize_edge(e) -> dict:
       out = {"edge_id": e.edge_id, "edge_type": e.edge_type, "from": e.from_node, "to": e.to_node,
              "provenance": e.provenance, "confidence": e.confidence, "traversal_cost": e.traversal_cost}
       if e.finding_id:    out["finding_id"] = e.finding_id
       if e.capability_id: out["capability_id"] = e.capability_id
       return out


   def _write_attack_paths(path: Path, paths, params, truncated, bottleneck_count) -> None:
       doc = {
           "schema_version": 1,
           "generated_by": "attack_path_analyzer",
           "enumeration_parameters": {
               "max_hop": params.max_hop,
               "max_paths_per_pair": params.max_paths_per_pair,
               "bottleneck_threshold": params.bottleneck_threshold,
           },
           "paths": [{
               "path_id": p.path_id,
               "attacker_position": p.attacker_position,
               "crown_jewel": p.crown_jewel,
               "edges": list(p.edges),
               "hop_count": p.hop_count,
               "feasibility": p.feasibility,
               "severity_sum": p.severity_sum,
               "mitigation_count": p.mitigation_count,
               "bottleneck_edges": [],  # filled in by bottleneck-edge pass; CLI re-computes below
           } for p in paths],
           "summary": {
               "pairs_enumerated": len({(p.attacker_position, p.crown_jewel) for p in paths}),
               "total_paths": len(paths),
               "truncated_pairs": truncated,
               "bottleneck_edge_count": bottleneck_count,
           },
       }
       # Fill bottleneck_edges per path
       all_bn = {e for p in paths for e in p.edges}  # placeholder until full set passed in
       # CLI keeps simple semantics: bottleneck_edges per path filled by intersecting path edges
       # with the bottleneck dict. The cleaner refactor passes bottleneck_edges dict through;
       # for v1.4 keep it inline.
       path.write_text(yaml.safe_dump(doc, sort_keys=False))


   def _write_defense_graph(path: Path, overlays: list[dict]) -> None:
       doc = {
           "schema_version": 1,
           "generated_by": "attack_path_analyzer",
           "bottleneck_overlays": overlays,
           "summary": {
               "bottleneck_edge_count": len(overlays),
               "total_candidate_d3fend": sum(len(o.get("candidate_d3fend", [])) for o in overlays),
               "total_net_new_d3fend":   sum(len(o.get("net_new_d3fend", []))   for o in overlays),
           },
       }
       path.write_text(yaml.safe_dump(doc, sort_keys=False))


   def _write_findings(path: Path, findings: list[dict]) -> None:
       doc = {"schema_version": 1, "findings": findings}
       path.write_text(yaml.safe_dump(doc, sort_keys=False))
   ```

   Also ensure `import hashlib` and `import yaml` are at the top of `cli.py`.

   Plan note on the `_write_attack_paths` placeholder: the `bottleneck_edges` per-path field needs the full bottleneck dict to be passed through. Refactor `_write_attack_paths` to accept `bottleneck_edges: dict[str, list[str]]` and set each path's `bottleneck_edges` to `[eid for eid in p.edges if eid in bottleneck_edges]`. Add this in Step 3 before running tests.

- [ ] **Step 3: Plug the bottleneck-edges-per-path computation into `_write_attack_paths`**

   Refactor the function to accept `bottleneck_edges: dict[str, list[str]]` and compute each path's `bottleneck_edges` field as the intersection of `p.edges` with the bottleneck dict keys. Pass `bottleneck_edges` from the command body into the writer.

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_cli_analyze_attack_paths.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/cli.py tests/test_cli_analyze_attack_paths.py
   git commit -m "feat(cli): add analyze-attack-paths subcommand with deterministic headless enumeration"
   ```

---

## Task C-16: New skill `apd-attack-path-discipline`

**Goal:** Project skill consumed by the analyzer agent. Codifies the never-invent rules, confidence floors severity rule, bounded-enumeration discipline, and the block-on-missing-crown-jewels rule per design spec §7.7.

**Files:**

- Create: `.claude/skills/apd-attack-path-discipline/SKILL.md`
- Create: `.claude/skills/apd-attack-path-discipline/references/d3fend-mapping-pattern.md`
- Create: `tests/test_skill_apd_attack_path_discipline.py`

- [ ] **Step 1: Write failing tests**

   ```python
   import re
   from pathlib import Path

   SKILL = Path(".claude/skills/apd-attack-path-discipline/SKILL.md")
   REF   = Path(".claude/skills/apd-attack-path-discipline/references/d3fend-mapping-pattern.md")

   def test_skill_exists():
       assert SKILL.exists()
       assert REF.exists()

   def test_skill_has_frontmatter_with_name_and_description():
       content = SKILL.read_text()
       assert content.startswith("---\n")
       m = re.search(r"^name:\s*apd-attack-path-discipline\s*$", content, re.M)
       assert m
       assert re.search(r"^description:\s*\S", content, re.M)

   def test_skill_codifies_never_invent_nodes_rule():
       assert "never invent nodes" in SKILL.read_text().lower()

   def test_skill_codifies_never_invent_edges_rule():
       assert "never invent edges" in SKILL.read_text().lower()

   def test_skill_codifies_confidence_floors_severity_rule():
       text = SKILL.read_text().lower()
       assert "confidence" in text and "floor" in text and "severity" in text

   def test_skill_codifies_block_on_missing_crown_jewels():
       assert "block" in SKILL.read_text().lower() and "crown jewel" in SKILL.read_text().lower()

   def test_skill_codifies_bounded_enumeration():
       text = SKILL.read_text()
       assert "max_hop" in text or "bounded" in text.lower()

   def test_skill_referenced_by_analyzer_agent():
       agent = Path(".claude/agents/apd-attack-path-analyzer.md").read_text()
       assert "apd-attack-path-discipline" in agent
   ```

   The final test will only pass after Task C-17 lands. Mark it `@pytest.mark.xfail(strict=True, reason="agent ships in Task C-17")` or split into two PRs — recommend the latter: drop the cross-reference test in this task, add it back in Task C-17.

- [ ] **Step 2: Write the skill file `.claude/skills/apd-attack-path-discipline/SKILL.md`**

   ```markdown
   ---
   name: apd-attack-path-discipline
   description: Required discipline for the apd-attack-path-analyzer agent. Covers never-invent rules for nodes and edges, confidence floors severity rule, bounded-enumeration discipline, block-on-missing-crown-jewels rule, D3FEND-must-counter-ATT&CK mapping rule, and Mermaid diagram constraints. Required reading before emitting any apath-* finding or asset-graph node/edge.
   ---

   # APD Attack-Path Discipline

   The attack-path analyzer operates on a partial graph built from human-authored
   artifacts — incomplete, ambiguous, sometimes contradictory. Output is honest
   about that or it is harmful: paths that look authoritative on a partial graph
   become false confidence in shipping designs.

   ## Hard rules

   ### 1. Never invent nodes
   Every node in the asset graph must cite one of:
   - An asset/identity/trust-boundary record in `00-context/asset-inventory.yaml`
   - A normalized threat-model entry whose `asset` field is the node name
   - A code-evidence-index entry naming the service/component
   - A domain-pack `crown_jewels[]` or `attacker_positions[]` declaration
   - A run-config `crown_jewels[]` or `attacker_positions[]` override

   If a node has no citation, it does not exist. Do not add it because "it
   probably should be there."

   ### 2. Never invent edges
   Every edge must cite one of:
   - An IaC/architecture artifact declaring network reachability
   - A finding whose evidence describes attacker traversal (edge_type =
     `compromisable_via_finding`, finding_id required)
   - A capability whose evidence describes mitigation along a known path
     (edge_type = `mitigated_by_capability`, capability_id required)
   - A normalized threat-model entry naming both endpoints
   - A code-evidence-index cross-service call
   - A trust boundary declared in asset-inventory or domain-pack defaults

   ### 3. Confidence floors severity
   - Paths whose feasibility floor is `low` MUST cap at `disposition: uncertainty`
     and `severity ∈ {low, medium}`. Never escalate to `risk` on a low-confidence
     path.
   - Paths whose feasibility floor is `high` and whose severity_sum ≥ 3 with no
     mitigations along the path SHOULD emit `disposition: risk` at `severity:
     high` or `critical`.
   - When in doubt between two severity levels, take the lower. The path is
     interesting either way; over-escalating destroys signal in the rest of the
     advisory report.

   ### 4. Bounded enumeration; honest output
   - `max_hop` caps at 12 (schema-enforced). Default 8.
   - `max_paths_per_pair` caps at 200 (schema-enforced). Default 50.
   - When truncation occurs, the `attack-paths.yaml` summary records
     `truncated_pairs > 0` and the report says so explicitly.
   - Never claim "all paths" — output language is always "top-N paths under K
     hops."

   ### 5. Block on missing crown jewels
   No declared targets → analyzer emits a single `disposition: blocked` finding
   and does not enumerate. Do not guess. The block-finding must list
   `prerequisite_evidence: ["domain pack or run-config must declare
   crown_jewels[]"]`.

   ### 6. D3FEND must counter ATT&CK
   A D3FEND technique appearing in `candidate_d3fend[]` MUST have a non-empty
   `counters[]` array drawn from the bottleneck edge's `exposed_attack_techniques`.
   The MITRE D3FEND attack-counter table is the authoritative source; never map
   by name similarity ("the names sound related" is not evidence). The
   `tools/apd_gauntlet/data/d3fend.json` reference data is the projection of
   that table; always use it.

   See [d3fend-mapping-pattern.md](references/d3fend-mapping-pattern.md) for the
   walk-through.

   ### 7. Mermaid diagram cap
   Single diagram ≤ 50 nodes. Graphs above this cap partition by attacker_position
   into multiple inline `flowchart LR` diagrams in the report. The
   `tools/apd_gauntlet/attack_path/mermaid.py` module enforces this — do not
   bypass it.

   ## Tier ordering

   The analyzer runs in tier-4 AFTER `apd-synthesizer` has dedup'd specialist
   findings and capabilities. Inputs are read-only from the analyzer's
   perspective: it never modifies specialist records. Its own findings are
   appended to a separate file (`40-synthesis/attack-path-findings.yaml`) that
   the synthesizer's final coverage-matrix pass includes in the 9×N rollup.

   ## Out of scope (delegated)

   - Edge confidence is a property of the source artifact, not a judgment call —
     IaC says high, free-form prose says low, code-evidence with a clear file
     path says high.
   - Severity scoring uses the standard APD rubric (`apd-evidence-discipline`).
     Do not re-derive — apply.
   - Identity/authz semantics that ARE in scope for specialists (apd-authenticity,
     apd-ephemeral) MUST NOT be re-litigated. The analyzer reads their findings
     as edge attributes, not as its own analysis.
   ```

- [ ] **Step 3: Write the reference doc**

   `.claude/skills/apd-attack-path-discipline/references/d3fend-mapping-pattern.md` — 1-2 page walk-through with two worked examples: one bottleneck edge exposing T1078 → D3-MFA + D3-NTSA + D3-IBCA; the partition by existing-capability-backing vs net-new; and one bottleneck edge with NO D3FEND counters (gap; report says so).

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_skill_apd_attack_path_discipline.py -v
   pytest -q
   git add .claude/skills/apd-attack-path-discipline/ tests/test_skill_apd_attack_path_discipline.py
   git commit -m "feat(skill): add apd-attack-path-discipline with never-invent and bounded-enumeration rules"
   ```

---

## Task C-17: New agent `apd-attack-path-analyzer`

**Goal:** The tier-4 agent markdown file in `.claude/agents/`. Follows the same shape as Phase B's `apd-threat-model-evaluator` — frontmatter + activation contract + lens-scoping + invocation guidance + skill cross-references. The agent's job is to author edge provenance (where the deterministic builder's name-matching heuristic is too coarse) and write the markdown report; deterministic enumeration is delegated to the CLI subcommand from Task C-15.

**Files:**

- Create: `.claude/agents/apd-attack-path-analyzer.md`
- Modify: `tools/apd_gauntlet/lint_agents.py` (if it has an allow-list of agent names — extend; otherwise this is a no-op)
- Create: `tests/test_lint_agent_apd_attack_path_analyzer.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from pathlib import Path
   AGENT = Path(".claude/agents/apd-attack-path-analyzer.md")

   def test_agent_file_exists():
       assert AGENT.exists()

   def test_agent_has_required_frontmatter():
       text = AGENT.read_text()
       assert text.startswith("---\n")
       for field in ("name:", "description:", "tools:", "model:"):
           assert field in text

   def test_agent_declares_tier_4():
       assert "tier-4" in AGENT.read_text().lower()

   def test_agent_activation_gated_on_crown_jewels():
       assert "crown_jewels" in AGENT.read_text() or "crown jewels" in AGENT.read_text().lower()

   def test_agent_invokes_cli_subcommand():
       assert "analyze-attack-paths" in AGENT.read_text()

   def test_agent_consumes_dedup_findings_from_synthesizer():
       text = AGENT.read_text().lower()
       assert "synthesizer" in text or "dedup" in text

   def test_agent_references_attack_path_discipline_skill():
       assert "apd-attack-path-discipline" in AGENT.read_text()

   def test_agent_lints_clean():
       # apd-gauntlet lint-agents must include this agent and pass
       import subprocess
       result = subprocess.run(["apd-gauntlet", "lint-agents"], capture_output=True, text=True)
       assert result.returncode == 0, result.stdout + result.stderr
       assert "apd-attack-path-analyzer" in result.stdout
   ```

- [ ] **Step 2: Write the agent file**

   `.claude/agents/apd-attack-path-analyzer.md`:

   ```markdown
   ---
   name: apd-attack-path-analyzer
   description: Tier-4 activation-gated agent that builds an asset graph from intake/threat-model/code-evidence/findings/capabilities, enumerates bounded attack paths from declared attacker positions to declared crown jewels, identifies bottleneck edges, and overlays MITRE D3FEND defensive techniques. Activates when at least one crown jewel is declared (domain pack default or run-config override). Emits apath-* findings (risk, uncertainty, gap, blocked flavors) plus 40-synthesis/asset-graph.yaml, attack-paths.yaml, defense-graph.yaml, and attack-path-report.md. Does not modify specialist records — runs after apd-synthesizer.
   tools: Read, Glob, Grep, Write, Bash
   model: opus
   ---

   # apd-attack-path-analyzer

   ## Tier and activation

   Tier-4 agent. Runs AFTER `apd-synthesizer` has produced dedup'd findings and
   capabilities. Activation-gated:

   - Activates when the domain pack declares `crown_jewels[]` OR the run-config
     declares `crown_jewels[]` (and at least one attacker_position is similarly
     declared)
   - Skips silently when neither side declares targets — operator opted out of
     attack-path analysis for this run
   - Block-on-missing: if the operator declared `crown_jewels: []` (empty list,
     overriding the domain pack), the analyzer emits a single
     `disposition: blocked` finding and stops

   ## Inputs

   - `00-context/asset-inventory.yaml` (intake-emitted; required)
   - `00-context/threat-model-normalized.yaml` (optional; used for declared
     attacker-vector edges)
   - `00-context/code-evidence-index.yaml` (optional; used for cross-service
     reachability)
   - `20-specialist-findings/*.findings.yaml` (dedup'd; one finding can produce
     one `compromisable_via_finding` edge)
   - `30-specialist-capabilities/*.capabilities.yaml` (dedup'd; one capability
     can produce one `mitigated_by_capability` edge)
   - `.apd-run.yaml` (`crown_jewels[]`, `attacker_positions[]`,
     `attack_path_analysis.{max_hop,max_paths_per_pair,bottleneck_threshold}`)
   - The domain pack (defaults for the same fields)

   ## Outputs

   - `40-synthesis/asset-graph.yaml` — nodes + edges, schema-validated
   - `40-synthesis/attack-paths.yaml` — enumerated paths with feasibility/severity
   - `40-synthesis/defense-graph.yaml` — D3FEND overlay on bottleneck edges
   - `40-synthesis/attack-path-findings.yaml` — apath-* findings (schema = finding.schema.json)
   - `40-synthesis/attack-path-report.md` — markdown report with embedded Mermaid diagrams

   ## How this agent works

   1. **Pre-flight:** Verify crown_jewels/attacker_positions are resolvable from
      run-config or domain pack. If not, emit `disposition: blocked` and stop.
   2. **Build the graph:** Run `apd-gauntlet analyze-attack-paths <run_dir>` —
      this is the deterministic floor. The CLI builds the graph, enumerates
      paths, computes D3FEND overlay, and writes the four artifacts above.
   3. **Author edge provenance:** Read the emitted `asset-graph.yaml`. For each
      `compromisable_via_finding` and `mitigated_by_capability` edge, check that
      the deterministic name-matching heuristic chose plausible endpoints. When
      it did not (e.g., the finding's evidence excerpt mentions "the gateway"
      but the heuristic wired it to the wrong asset), correct the edge by
      editing `asset-graph.yaml` in place AND update the finding/capability's
      `evidence[].excerpt` to make the linkage explicit. Cite the edit by
      adding a `provenance.author_note` field; this is permitted by the schema's
      additionalProperties:false because... wait — additionalProperties is
      false. Use the existing `provenance.locator` field to point to the
      excerpt that justifies the correction. Do not invent new keys.
   4. **Re-run if you edited:** If you made edge corrections, re-run
      `apd-gauntlet analyze-attack-paths <run_dir>` to regenerate paths,
      bottlenecks, defense-graph, and findings. Do NOT hand-edit those files —
      they are derived.
   5. **Write the markdown report:** Render `40-synthesis/attack-path-report.md`
      from the template at `templates/attack-path-report.template.md`. Embed
      Mermaid diagrams inline (the CLI's mermaid module produces them; pull
      from a temporary output or call the renderer via Python one-liner from a
      Bash step).
   6. **Validate:** `apd-gauntlet validate <run_dir>` must pass on the artifacts
      you wrote. Schema mismatches block the agent from declaring success.

   ## Required reading

   - [apd-framework](../skills/apd-framework/SKILL.md) — three tiers, nine goals
   - [apd-evidence-discipline](../skills/apd-evidence-discipline/SKILL.md) — evidence-pointer rule, block-on-ambiguity, never-invent
   - [apd-attack-path-discipline](../skills/apd-attack-path-discipline/SKILL.md) — node/edge provenance, confidence floors severity, bounded enumeration, block-on-missing-crown-jewels, D3FEND mapping rules
   - [apd-finding-schema](../skills/apd-finding-schema/SKILL.md) — apath-* id pattern, finding/capability record shape
   - [apd-control-mappings](../skills/apd-control-mappings/SKILL.md) — D3FEND-must-counter-ATT&CK rule

   ## Out of scope (delegated)

   - Specialist analysis on individual findings — that's the tier-1/2/3
     specialists' job, completed before this agent runs.
   - Dedup/merge/cluster — that's the synthesizer, also completed before this
     agent runs.
   - Threat-model parsing or methodology coverage — that's `apd-threat-model-recon`
     (tier-0) and `apd-threat-model-evaluator` (tier-4); their outputs are
     INPUTS to this agent.
   ```

- [ ] **Step 3: Lint the agent**

   ```bash
   apd-gauntlet lint-agents
   ```

   Should report 16 agents clean.

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_lint_agent_apd_attack_path_analyzer.py -v
   pytest -q
   git add .claude/agents/apd-attack-path-analyzer.md tests/test_lint_agent_apd_attack_path_analyzer.py
   git commit -m "feat(agent): add apd-attack-path-analyzer tier-4 with deterministic-CLI delegation"
   ```

---

## Task C-18: Update `apd-intake` to emit `00-context/asset-inventory.yaml`

**Goal:** Extend the intake agent's contract so its output includes a machine-readable asset inventory (the artifact the analyzer consumes). The intake agent's prompt instructions get a new section; the existing context-brief output is unchanged.

**Files:**

- Modify: `.claude/agents/apd-intake.md`
- Add: `templates/asset-inventory.template.md` (a YAML template embedded in markdown — same convention as Phase B's `templates/threat-model-normalized.template.md`)
- Add: `tests/test_intake_asset_inventory_contract.py` (verifies the agent file references the new artifact and template)

- [ ] **Step 1: Write failing tests**

   ```python
   from pathlib import Path
   AGENT = Path(".claude/agents/apd-intake.md")
   TEMPLATE = Path("templates/asset-inventory.template.md")

   def test_intake_agent_emits_asset_inventory():
       text = AGENT.read_text()
       assert "asset-inventory.yaml" in text
       assert "00-context/asset-inventory.yaml" in text

   def test_intake_agent_references_asset_inventory_template():
       text = AGENT.read_text()
       assert "asset-inventory.template.md" in text

   def test_intake_agent_documents_asset_types():
       text = AGENT.read_text().lower()
       for kind in ("service", "data_store", "secret_store", "queue", "network", "external_dependency", "compute"):
           assert kind in text, f"asset_type {kind} should appear in intake instructions"

   def test_intake_agent_documents_identity_types():
       text = AGENT.read_text().lower()
       for kind in ("human_role", "service_account", "workload_identity", "external_party"):
           assert kind in text

   def test_asset_inventory_template_exists():
       assert TEMPLATE.exists()

   def test_asset_inventory_template_has_yaml_skeleton():
       text = TEMPLATE.read_text()
       assert "schema_version: 1" in text
       assert "generated_by: intake" in text
       assert "assets:" in text and "identities:" in text and "trust_boundaries:" in text
   ```

- [ ] **Step 2: Update `.claude/agents/apd-intake.md`**

   Find the existing "Outputs" section and append:

   ```markdown
   ### `00-context/asset-inventory.yaml` (NEW in v1.4 — required when crown_jewels declared)

   Machine-readable inventory of the assets, identities, and trust boundaries
   identified during context-briefing. Consumed by `apd-attack-path-analyzer`.

   - **Assets** — every named service, data store, secret store, queue,
     network, external dependency, or compute resource mentioned in supplied
     artifacts. Each carries:
     - `asset_id: asset-<sha8>` (deterministic ID from name + locator)
     - `name`: the canonical name as used in artifacts
     - `asset_type` ∈ {service, data_store, secret_store, queue, network, external_dependency, compute}
     - `data_classifications[]`: PHI / PII / PCI / secret / internal / etc.
     - `provenance.source` ∈ {artifact, domain_default, threat_model, code_evidence}, plus `artifact` and `locator` when applicable
     - `confidence` ∈ {high, medium, low} — high for IaC-declared, medium for prose-described, low for inferred

   - **Identities** — human roles, service accounts, workload identities,
     external parties mentioned in supplied artifacts. Each carries:
     - `identity_id: idn-<sha8>`
     - `name`: canonical name
     - `identity_type` ∈ {human_role, service_account, workload_identity, external_party}
     - provenance + confidence as above

   - **Trust boundaries** — declared cross-asset trust transitions. Each carries:
     - `boundary_id: tb-<sha8>`
     - `name`: human-readable description
     - `crosses[]`: array of `asset_id` values the boundary partitions

   Use [asset-inventory.template.md](../../templates/asset-inventory.template.md) as the YAML skeleton.

   **Discipline:** Same evidence-discipline rules apply. Never invent assets that
   no supplied artifact mentions. When an asset is described ambiguously, set
   `confidence: low`; the attack-path analyzer treats low-confidence nodes as
   bounded contributors to path feasibility, not as authoritative graph entries.
   ```

   Also update the agent's "Activation" section: the asset-inventory artifact is
   emitted whenever the run-config's `crown_jewels` list is non-empty OR the
   domain pack declares any crown_jewels. (For backward compatibility with v1.1
   runs that have neither, the inventory is optional and not emitted.)

- [ ] **Step 3: Write the template `templates/asset-inventory.template.md`**

   ```markdown
   # Asset Inventory — Template

   Emit this artifact as `00-context/asset-inventory.yaml`. Schema:
   `asset-inventory.schema.json`.

   ```yaml
   schema_version: 1
   generated_by: intake

   assets:
     - asset_id: asset-<sha8>             # sha8 of (name|primary_locator)
       name: "<canonical name>"
       asset_type: service                # service | data_store | secret_store | queue | network | external_dependency | compute
       data_classifications: [phi, internal]   # optional
       provenance:
         source: artifact                 # artifact | domain_default | threat_model | code_evidence
         artifact: "<file path>"
         locator: "<file#region>"
       confidence: high

   identities:
     - identity_id: idn-<sha8>
       name: "<canonical name>"
       identity_type: service_account     # human_role | service_account | workload_identity | external_party
       provenance:
         source: artifact
         artifact: "<file path>"
         locator: "<file#region>"
       confidence: high

   trust_boundaries:
     - boundary_id: tb-<sha8>
       name: "<boundary description>"
       crosses:
         - asset-<sha8>
         - asset-<sha8>
       provenance:
         source: artifact
         artifact: "<file path>"
         locator: "<file#region>"

   extraction_summary:
     asset_count: <int>
     identity_count: <int>
     trust_boundary_count: <int>
     high_confidence_count: <int>
     medium_confidence_count: <int>
     low_confidence_count: <int>
   ```
   ```

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_intake_asset_inventory_contract.py -v
   pytest -q
   apd-gauntlet lint-agents   # 16 agents clean
   git add .claude/agents/apd-intake.md templates/asset-inventory.template.md tests/test_intake_asset_inventory_contract.py
   git commit -m "feat(intake): emit machine-readable 00-context/asset-inventory.yaml for attack-path analyzer"
   ```

---

## Task C-19: Update `apd-orchestrator` agent for the new topology

**Goal:** Orchestrator agent text describes the run lifecycle. Add the analyzer to the tier-4 dispatch section. Bump the agent count.

**Files:**

- Modify: `.claude/agents/apd-orchestrator.md`
- Modify: `tests/test_orchestrator_topology.py` (if it asserts agent count)

- [ ] **Step 1: Read the current orchestrator agent**

   ```bash
   grep -n "agents\|tier" .claude/agents/apd-orchestrator.md | head -30
   ```

   Identify where Phase B's `apd-threat-model-evaluator` was added; the new agent goes alongside it in the tier-4 dispatch block.

- [ ] **Step 2: Update the topology section**

   Replace the tier-4 description block to include both evaluator and analyzer:

   ```markdown
   **Tier 4 (synthesis):**
   - `apd-synthesizer` — dedup'd findings/capabilities + 9×N coverage matrix
   - `apd-threat-model-evaluator` — methodology-aware TM evaluation (Phase B / v1.3)
   - `apd-attack-path-analyzer` — bounded attack-path enumeration + D3FEND overlay (Phase C / v1.4)

   The synthesizer runs first in tier 4. Evaluator and analyzer can run in
   parallel — they consume the same dedup'd outputs and write to non-overlapping
   files. The synthesizer's final coverage-matrix pass includes findings from
   both evaluator (tmeval-*) and analyzer (apath-*) in the 9×N rollup.
   ```

   Also update the agent-count line ("16 agents" — confirm exact wording by reading the file first).

- [ ] **Step 3: Update test if needed**

   If `tests/test_orchestrator_topology.py` exists, update any agent-count assertions from 15 → 16. If a new test is needed:

   ```python
   def test_orchestrator_documents_attack_path_analyzer():
       assert "apd-attack-path-analyzer" in Path(".claude/agents/apd-orchestrator.md").read_text()
   ```

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest -q
   apd-gauntlet lint-agents   # 16 agents clean
   git add .claude/agents/apd-orchestrator.md tests/test_orchestrator_topology.py
   git commit -m "feat(agent): orchestrator topology for v1.4 (16 agents with attack-path analyzer)"
   ```

---

## Task C-20: Synthesizer audit — include `apath-*` and `tmeval-*` findings in the 9×N coverage matrix

**Goal:** The synthesizer's `apd-coverage-matrix.yaml` rollup currently aggregates specialist findings. Verify it also picks up tier-4 findings emitted by the evaluator (Phase B) and the analyzer (Phase C). If it does not, extend the file-discovery glob.

**Files:**

- Inspect: the synthesizer's rollup logic (likely lives in `tools/apd_gauntlet/summary.py` or wherever the matrix is built — check first)
- Modify (if needed): the rollup file
- Modify: `.claude/agents/apd-synthesizer.md` (if it documents the file-discovery pattern)
- Add: `tests/test_synthesis_matrix_includes_tier4_findings.py`

- [ ] **Step 1: Locate the matrix-building code**

   ```bash
   grep -rln "apd-coverage-matrix\|coverage_matrix" tools/ tests/ | head -10
   grep -rln "20-specialist-findings\|*.findings.yaml" tools/ tests/ .claude/agents/ | head -20
   ```

   Identify the function or agent prompt that builds the 9×N matrix.

- [ ] **Step 2: Write failing tests**

   Construct a synthetic run dir with:
   - 2 specialist `.findings.yaml` files (conf, integ)
   - 1 tmeval finding file `40-synthesis/threat-model-coverage-findings.yaml` or wherever Phase B writes them — check the actual path used
   - 1 apath finding file `40-synthesis/attack-path-findings.yaml`

   Then run the synthesizer's matrix-building pass (either via CLI subcommand or directly via the Python entrypoint) and assert the matrix counts all four finding sources, partitioned by `apd_goal`.

   ```python
   def test_coverage_matrix_counts_specialist_findings():
       matrix = build_coverage_matrix(_fixture_run_dir())
       assert matrix["confidentiality"]["finding_count"] >= 1

   def test_coverage_matrix_counts_tmeval_findings():
       matrix = build_coverage_matrix(_fixture_run_dir())
       all_finding_ids = {fid for cell in matrix.values() for fid in cell.get("finding_ids", [])}
       assert any(fid.startswith("tmeval-") for fid in all_finding_ids)

   def test_coverage_matrix_counts_apath_findings():
       matrix = build_coverage_matrix(_fixture_run_dir())
       all_finding_ids = {fid for cell in matrix.values() for fid in cell.get("finding_ids", [])}
       assert any(fid.startswith("apath-") for fid in all_finding_ids)
   ```

- [ ] **Step 3: Extend the matrix-building pass**

   The fix depends on what the existing code looks like. Two common patterns:

   **If the matrix is built by a Python function:** extend the file-discovery glob set to include `40-synthesis/threat-model-coverage-findings.yaml` (or whichever path the evaluator writes to) and `40-synthesis/attack-path-findings.yaml`.

   **If the matrix is built by the synthesizer agent's prompt instructions (the LLM walks the dir):** extend the agent's prompt to include both tier-4 finding files in its scan.

   The recommended floor: a Python helper that returns the union of finding records from `20-specialist-findings/*.findings.yaml`, `40-synthesis/threat-model-coverage-findings.yaml`, and `40-synthesis/attack-path-findings.yaml`. Both the synthesizer agent's prompt AND the `apd-gauntlet validate` cross-file pass should reference this helper.

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_synthesis_matrix_includes_tier4_findings.py -v
   pytest -q
   git add tools/apd_gauntlet/summary.py .claude/agents/apd-synthesizer.md tests/test_synthesis_matrix_includes_tier4_findings.py
   git commit -m "feat(synth): include tmeval- and apath- findings in 9xN coverage matrix"
   ```

---

## Task C-21: Extend `apd-gauntlet validate` to pick up Phase C artifacts

**Goal:** Validator's file-discovery scan should detect and validate `00-context/asset-inventory.yaml`, `40-synthesis/asset-graph.yaml`, `40-synthesis/attack-paths.yaml`, `40-synthesis/defense-graph.yaml`, and the apath-* findings inside `40-synthesis/attack-path-findings.yaml`.

**Files:**

- Modify: `tools/apd_gauntlet/validate.py`
- Modify: `tests/test_validate_cross_file.py`
- Add: `tests/fixtures/malformed/asset-graph-with-orphan-edge.yaml` (edge references a node not in the nodes list)

- [ ] **Step 1: Write failing tests**

   ```python
   def test_validate_picks_up_asset_inventory(tmp_path):
       # Scaffold run dir with valid 00-context/asset-inventory.yaml
       # Assert validator reports it in file count
       ...

   def test_validate_rejects_malformed_asset_graph(tmp_path):
       # Scaffold with an asset-graph.yaml whose edge.from references a missing node_id
       # Assert validate exits non-zero
       ...

   def test_validate_accepts_valid_phase_c_artifacts(tmp_path):
       # Scaffold with all four Phase C artifacts valid
       # Assert validator passes
       ...

   def test_validate_picks_up_attack_path_findings(tmp_path):
       # Scaffold with 40-synthesis/attack-path-findings.yaml containing apath-* records
       # Assert validator validates each record against finding.schema.json
       ...
   ```

- [ ] **Step 2: Extend the file-discovery map**

   In `tools/apd_gauntlet/validate.py`, add to the synthesis-rollup map (the same map Phase B Task B-5 extended for `cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`):

   ```python
   _SYNTHESIS_ROLLUPS = {
       # ... existing entries ...
       "asset-graph.yaml":              "asset-graph.schema.json",
       "attack-paths.yaml":             "attack-path.schema.json",
       "defense-graph.yaml":            "defense-graph.schema.json",
       "attack-path-findings.yaml":     None,   # contains finding records; per-record validation
   }
   ```

   And to the context-rollup map (or wherever asset-inventory lives):

   ```python
   _CONTEXT_ROLLUPS = {
       # ... existing entries (code-evidence-index.yaml, threat-model-normalized.yaml) ...
       "asset-inventory.yaml":          "asset-inventory.schema.json",
   }
   ```

   For `attack-path-findings.yaml`, the file wraps a list of finding records under `findings:`; iterate and validate each record against `finding.schema.json`. Mirror the existing handler for `*.findings.yaml` files.

- [ ] **Step 3: Add cross-file integrity check — edge endpoints must reference real nodes**

   New check in the cross-file pass: for each `asset-graph.yaml`, every `edges[].from` and `edges[].to` must appear as a `nodes[].node_id`. Each `compromisable_via_finding` edge's `finding_id` must match a record in `20-specialist-findings/*.findings.yaml` OR `40-synthesis/attack-path-findings.yaml` OR `40-synthesis/threat-model-coverage-findings.yaml`. Each `mitigated_by_capability` edge's `capability_id` must match a capability record.

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_validate_cross_file.py -v
   pytest -q
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # should still pass
   git add tools/apd_gauntlet/validate.py tests/test_validate_cross_file.py tests/fixtures/malformed/asset-graph-with-orphan-edge.yaml
   git commit -m "feat(validate): pick up asset-inventory/asset-graph/attack-paths/defense-graph + cross-file edge integrity"
   ```

---

## Task C-22: Templates for the analyzer's output

**Goal:** Five new templates the analyzer agent uses to author its outputs. Two have YAML skeletons (asset-graph, attack-paths) for the agent to fill when manually editing; the third (defense-graph) is auto-generated and just needs a doc; the fourth (asset-inventory) was created in Task C-18; the fifth (attack-path-report) is the markdown narrative the analyzer authors.

**Files:**

- Create: `templates/asset-graph.template.md`
- Create: `templates/attack-paths.template.md`
- Create: `templates/defense-graph.template.md`
- Create: `templates/attack-path-report.template.md`
- Add: `tests/test_attack_path_templates.py`

- [ ] **Step 1: Write failing tests**

   ```python
   from pathlib import Path
   TPL = Path("templates")

   def test_asset_graph_template_has_yaml_skeleton():
       text = (TPL / "asset-graph.template.md").read_text()
       assert "schema_version: 1" in text
       assert "generated_by: attack_path_analyzer" in text
       assert "nodes:" in text and "edges:" in text

   def test_attack_paths_template_has_enumeration_parameters():
       text = (TPL / "attack-paths.template.md").read_text()
       assert "enumeration_parameters:" in text
       assert "max_hop" in text and "max_paths_per_pair" in text

   def test_defense_graph_template_documents_overlay_shape():
       text = (TPL / "defense-graph.template.md").read_text()
       assert "bottleneck_overlays" in text
       assert "candidate_d3fend" in text
       assert "net_new_d3fend" in text

   def test_attack_path_report_template_has_mermaid_block_placeholder():
       text = (TPL / "attack-path-report.template.md").read_text()
       assert "```mermaid" in text
       assert "flowchart LR" in text
       assert "## Crown jewels" in text or "Crown jewels" in text

   def test_attack_path_report_template_documents_50_node_cap():
       text = (TPL / "attack-path-report.template.md").read_text().lower()
       assert "50 node" in text or "50-node" in text or "50 nodes" in text
   ```

- [ ] **Step 2: Write the four templates**

   Templates should mirror the structure of Phase B's `templates/threat-model-normalized.template.md` and `templates/threat-model-coverage-report.template.md`. Each is a markdown file that begins with a brief "What this is" paragraph, then either a YAML skeleton (for the data artifacts) or a narrative report skeleton (for the report).

   For brevity, only the report template's outline is shown here; the three data templates follow the same shape as their respective schema fixtures.

   `templates/attack-path-report.template.md` outline:

   ```markdown
   # Attack-Path Analysis Report — Template

   This template is the structure for `40-synthesis/attack-path-report.md`.
   Authored by `apd-attack-path-analyzer` after enumeration. Render Mermaid
   diagrams inline; cap at 50 nodes per diagram and partition by
   attacker_position when needed.

   ---

   # Attack-Path Analysis — <Domain> — <Date>

   ## Scope

   - **Crown jewels declared:** <list>
   - **Attacker positions declared:** <list>
   - **Enumeration bounds:** max_hop=<N>, max_paths_per_pair=<M>, bottleneck_threshold=<K>
   - **Sources used to build the graph:** <asset_inventory | threat_model_normalized | code_evidence_index | findings | capabilities | domain_defaults | run_config>

   ## Headline summary

   - <P> distinct attack paths enumerated across <Q> (attacker, crown_jewel) pairs
   - <T> pair(s) truncated at max_paths_per_pair (output is top-N under bound)
   - <B> bottleneck edge(s) — edges appearing on ≥<K> paths
   - <D> net-new D3FEND defensive investments identified

   ## High-leverage findings

   The <D> net-new D3FEND techniques below counter ATT&CK exposure on bottleneck
   edges that no existing capability addresses. Single implementations of any
   one of these break multiple enumerated paths.

   | Bottleneck edge | Paths affected | Exposed ATT&CK | Candidate D3FEND |
   |---|---|---|---|
   | <edge_id> | <count> | <techniques> | <d3fend ids> |

   ## Path catalogue

   Top-N paths per (attacker_position, crown_jewel) pair, sorted by descending
   severity_sum then ascending hop_count then descending feasibility.

   ### <attacker_position> → <crown_jewel>

   #### Path <path_id> (hop_count=<N>, feasibility=<level>, severity_sum=<int>, mitigations=<int>)

   <node_a> → [<edge_type>/<confidence>] → <node_b> → ... → <crown_jewel>

   - **Edge provenance:** <list with citations>
   - **Compromisable findings on path:** <finding IDs>
   - **Mitigating capabilities on path:** <capability IDs or "none">
   - **Bottleneck membership:** <edges shared with other paths>

   ## Diagram(s)

   Inline Mermaid diagrams partitioned by attacker_position. Each diagram
   ≤50 nodes; multiple diagrams when the graph exceeds the cap.

   ```mermaid
   flowchart LR
       <generated from tools/apd_gauntlet/attack_path/mermaid.py>
   ```

   ## Caveats

   - Output is the top-N paths under <max_hop> hops; never claim "all paths."
   - Every node and edge cites artifact provenance. Low-confidence paths cap at
     `disposition: uncertainty` regardless of severity_sum.
   - D3FEND overlay candidates derive from the MITRE D3FEND attack-counter
     table (see `tools/apd_gauntlet/data/d3fend.json`); D3FEND-by-name-similarity
     is forbidden by the apd-attack-path-discipline skill.
   ```

- [ ] **Step 3: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_path_templates.py -v
   pytest -q
   git add templates/asset-graph.template.md templates/attack-paths.template.md templates/defense-graph.template.md templates/attack-path-report.template.md tests/test_attack_path_templates.py
   git commit -m "feat(template): add asset-graph/attack-paths/defense-graph/attack-path-report templates"
   ```

---

## Task C-23: PBM domain pack — add `crown_jewels`, `attacker_positions`, `default_trust_boundaries`

**Goal:** PBM domain pack ships sensible defaults. Per design spec §7.10 — three crown jewels, five attacker positions, three trust boundaries.

**Files:**

- Modify: `domains/pbm/domain.yaml` (or wherever the PBM domain pack's main YAML lives)
- Modify: `tests/test_domain_pbm.py` (assert the new fields validate and contain expected entries)

- [ ] **Step 1: Locate the PBM domain pack's main YAML**

   ```bash
   find domains/pbm -name "*.yaml" -o -name "domain.yaml" | head -5
   ```

- [ ] **Step 2: Write failing tests**

   ```python
   def test_pbm_domain_declares_phi_store_crown_jewel():
       d = load_pbm_domain()
       jewels = [j["pattern"] for j in d["crown_jewels"]]
       assert "phi_store" in jewels
       assert "pde_submission_pipeline" in jewels
       assert "claim_adjudication_engine" in jewels

   def test_pbm_domain_declares_compromised_pharmacy_credential_attacker_position():
       d = load_pbm_domain()
       positions = [p["position"] for p in d["attacker_positions"]]
       assert "compromised_pharmacy_credential" in positions
       assert "compromised_vendor_integration" in positions
       assert "insider_with_member_service_role" in positions
       assert "compromised_dev_workstation" in positions
       assert "external_internet" in positions

   def test_pbm_domain_declares_pharmacy_ingress_trust_boundary():
       d = load_pbm_domain()
       boundaries = [b["boundary"] for b in d["default_trust_boundaries"]]
       assert "pharmacy_submission_ingress" in boundaries
       assert "member_portal_ingress" in boundaries
       assert "internal_to_pde_submission" in boundaries

   def test_pbm_domain_validates_clean():
       d = load_pbm_domain()
       errors = list(validate_domain(d))
       assert errors == []
   ```

- [ ] **Step 3: Add the three new sections to `domains/pbm/domain.yaml`**

   Use the exact content from design spec §7.10. Each entry's `description`
   must be ≥10 characters (schema-enforced from Task C-4).

- [ ] **Step 4: Run tests + linters + commit**

   ```bash
   pytest tests/test_domain_pbm.py -v
   pytest -q
   apd-gauntlet validate-domain pbm   # expect: clean
   git add domains/pbm/domain.yaml tests/test_domain_pbm.py
   git commit -m "feat(domain/pbm): declare crown_jewels, attacker_positions, default_trust_boundaries"
   ```

---

## Task C-24: Extend the bundled example with Phase C artifacts

**Goal:** `examples/apd-20260601-claim-event-bus/` becomes a full end-to-end demonstration of v1.4. Add `crown_jewels`/`attacker_positions` to its run-config, add expected `asset-inventory.yaml`, `asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`, `attack-path-findings.yaml`, and `attack-path-report.md` artifacts. The validator's `apd-gauntlet validate <example>/expected/` must continue to pass with the extended artifact set.

**Files:**

- Modify: `examples/apd-20260601-claim-event-bus/expected/.apd-run.yaml`
- Add: `examples/apd-20260601-claim-event-bus/expected/00-context/asset-inventory.yaml`
- Add: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/asset-graph.yaml`
- Add: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/attack-paths.yaml`
- Add: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/defense-graph.yaml`
- Add: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/attack-path-findings.yaml`
- Add: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/attack-path-report.md`
- Modify: `examples/apd-20260601-claim-event-bus/README.md`

- [ ] **Step 1: Extend the run-config**

   ```yaml
   # Existing fields preserved
   crown_jewels:
     - phi_store
     - pde_submission_pipeline
   attacker_positions:
     - external_internet
     - compromised_pharmacy_credential
     - compromised_vendor_integration
   attack_path_analysis:
     max_hop: 6
     max_paths_per_pair: 25
     bottleneck_threshold: 4
   ```

- [ ] **Step 2: Construct the asset-inventory**

   Walk the existing intake-brief and threat-model entries in
   `examples/apd-20260601-claim-event-bus/expected/00-context/` and extract:

   - 5-7 assets: claim-ingress-api, pharmacy-edge-gateway, adjudication-service,
     pricing-service, audit-log-store, member-record-store (PHI), pde-submission-service
   - 2-3 identities: pharmacy-submitter-role, adjudication-service-account,
     member-services-agent-role
   - 2-3 trust boundaries: external→ingress, ingress→adjudication,
     adjudication→pde-submission

   Each with realistic `provenance.artifact` pointing to the existing intake
   brief or threat-model file. Confidence high for IaC-declared, medium for
   prose-described.

- [ ] **Step 3: Generate the four Phase C outputs**

   ```bash
   apd-gauntlet analyze-attack-paths examples/apd-20260601-claim-event-bus/expected/
   ```

   This produces the four data artifacts deterministically. The
   `attack-path-report.md` is hand-authored from the template; commit a
   reviewed version.

- [ ] **Step 4: Validate the extended example**

   ```bash
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
   ```

   Expected: file count grows by 6 (asset-inventory + 4 synthesis artifacts +
   1 markdown report — though markdown is not schema-validated, so the file
   count increase reported by validate is 5). All schema-validated artifacts
   pass.

- [ ] **Step 5: Update README**

   Add a "v1.4 — attack-path analysis" section documenting:

   - What the new artifacts demonstrate (3 attacker positions × 2 crown jewels = 6 pairs)
   - One concrete bottleneck-edge example with the D3FEND counter
   - The truncation count (if any pair truncated)
   - How to regenerate (`apd-gauntlet analyze-attack-paths .`)

- [ ] **Step 6: Run tests + linters + commit**

   ```bash
   pytest -q
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
   git add examples/apd-20260601-claim-event-bus/expected/ examples/apd-20260601-claim-event-bus/README.md
   git commit -m "feat(example): claim-event-bus exercises v1.4 attack-path analysis end-to-end"
   ```

---

## Task C-25: New doc `docs/attack-path-analysis.md`

**Goal:** Operator guide for Track 3 — declaring crown jewels and attacker positions, reading the asset graph / attack-path / defense-graph outputs, interpreting Mermaid diagrams, tuning enumeration bounds.

**Files:**

- Create: `docs/attack-path-analysis.md`
- Add: `tests/test_doc_attack_path_analysis.py`

- [ ] **Step 1: Write failing tests**

   ```python
   import re
   from pathlib import Path
   DOC = Path("docs/attack-path-analysis.md")

   def test_doc_exists_and_nonempty():
       assert DOC.exists()
       assert DOC.stat().st_size > 5000  # at least a meaningful page

   def test_doc_covers_declaring_crown_jewels():
       text = DOC.read_text().lower()
       assert "declare crown jewels" in text or "declaring crown jewels" in text

   def test_doc_covers_declaring_attacker_positions():
       text = DOC.read_text().lower()
       assert "attacker position" in text

   def test_doc_covers_tuning_knobs():
       text = DOC.read_text()
       assert "max_hop" in text and "max_paths_per_pair" in text and "bottleneck_threshold" in text

   def test_doc_explains_block_on_missing_crown_jewels():
       text = DOC.read_text().lower()
       assert "block" in text and "crown jewel" in text

   def test_doc_describes_d3fend_overlay():
       text = DOC.read_text()
       assert "D3FEND" in text and "bottleneck" in text.lower()

   def test_doc_describes_50_node_mermaid_cap():
       text = DOC.read_text().lower()
       assert "50 node" in text or "50-node" in text or "50 nodes" in text

   def test_doc_warns_against_partial_graph_overclaiming():
       text = DOC.read_text().lower()
       assert "partial graph" in text or "never claim all paths" in text or "top-n paths" in text
   ```

- [ ] **Step 2: Write the doc**

   Sections:

   1. **What attack-path analysis is** — BloodHound-style enumeration over a partial graph. Honest about caveats up front.
   2. **When it activates** — domain pack declares crown_jewels OR run-config declares them. Both empty → skipped silently. Empty run-config override of non-empty domain → `disposition: blocked` finding.
   3. **Declaring crown jewels** — domain pack pattern (PBM example), run-config override pattern (workflow examples).
   4. **Declaring attacker positions** — same shape.
   5. **Tuning enumeration** — `max_hop`, `max_paths_per_pair`, `bottleneck_threshold` with practical guidance (when to raise each).
   6. **Reading the outputs** — walk through asset-graph.yaml / attack-paths.yaml / defense-graph.yaml / attack-path-findings.yaml / attack-path-report.md with a worked example from the bundled `claim-event-bus`.
   7. **Interpreting Mermaid diagrams** — what nodes/edges look like, the 50-node cap, partitioning by attacker_position.
   8. **The four finding flavors** — risk, uncertainty, gap, blocked — what each means, what to do.
   9. **Common pitfalls** — over-declaring attacker positions (drives enumeration blow-up), under-declaring crown jewels (skips the analysis), confusing path feasibility with severity.
   10. **Reference data refresh** — `apd-gauntlet refresh-d3fend` quarterly to keep counter-mappings current.

- [ ] **Step 3: Run tests + linters + commit**

   ```bash
   pytest tests/test_doc_attack_path_analysis.py -v
   npx markdownlint-cli2 docs/attack-path-analysis.md 2>&1 || true
   git add docs/attack-path-analysis.md tests/test_doc_attack_path_analysis.py
   git commit -m "docs: add attack-path-analysis.md operator guide for v1.4"
   ```

---

## Task C-26: Refresh existing docs for v1.4 — architecture, running, adapting, schema-evolution

**Goal:** Update the four existing operator/architecture docs to describe the new agent, new artifacts, new domain-pack fields, and the additive v1.4 schema cadence.

**Files:**

- Modify: `docs/architecture.md`
- Modify: `docs/running-the-gauntlet.md`
- Modify: `docs/adapting-to-other-domains.md`
- Modify: `docs/schema-evolution.md`
- Modify: `docs/extending-agents.md`
- Modify: `README.md` (top-level repo README — feature checklist or version table likely needs the v1.4 entry)
- Add: `tests/test_docs_v14.py` (asserts each doc mentions the new pieces)

- [ ] **Step 1: Write failing tests**

   ```python
   from pathlib import Path

   def test_architecture_doc_documents_attack_path_analyzer():
       assert "apd-attack-path-analyzer" in Path("docs/architecture.md").read_text()

   def test_architecture_doc_shows_16_agents():
       text = Path("docs/architecture.md").read_text()
       assert "16 agents" in text or "16-agent" in text

   def test_running_doc_documents_new_run_config_fields():
       text = Path("docs/running-the-gauntlet.md").read_text()
       for field in ("crown_jewels", "attacker_positions", "attack_path_analysis"):
           assert field in text

   def test_running_doc_documents_analyze_attack_paths_cli():
       assert "analyze-attack-paths" in Path("docs/running-the-gauntlet.md").read_text()

   def test_adapting_doc_documents_new_domain_pack_fields():
       text = Path("docs/adapting-to-other-domains.md").read_text()
       for field in ("crown_jewels", "attacker_positions", "default_trust_boundaries"):
           assert field in text

   def test_schema_evolution_doc_documents_v14():
       text = Path("docs/schema-evolution.md").read_text()
       assert "1.4.0" in text or "v1.4" in text

   def test_extending_agents_doc_describes_phase_c_pattern():
       text = Path("docs/extending-agents.md").read_text().lower()
       assert "activation-gated" in text or "activation gated" in text
       assert "attack-path-analyzer" in text or "apd-attack-path-analyzer" in text

   def test_readme_features_v14():
       text = Path("README.md").read_text()
       assert "1.4" in text or "v1.4" in text
   ```

- [ ] **Step 2: Make the updates**

   - `docs/architecture.md` — update topology diagram to include analyzer; update agent count; describe asset-inventory artifact in the tier-0 outputs section; describe asset-graph/attack-paths/defense-graph in the tier-4 outputs section.
   - `docs/running-the-gauntlet.md` — document new `.apd-run.yaml` fields, new CLI subcommand, when the analyzer activates vs skips, where to look in the output tree.
   - `docs/adapting-to-other-domains.md` — show pattern for declaring `crown_jewels`/`attacker_positions`/`default_trust_boundaries` in a non-PBM domain pack. Provide a worked example for a fictional "healthcare-billing" domain or similar.
   - `docs/schema-evolution.md` — append the v1.4 row: schemas added (asset-inventory, asset-graph, attack-path, defense-graph), schemas extended (finding agent enum + id pattern, run-config, domain), nothing removed, framework_compat unchanged.
   - `docs/extending-agents.md` — point to the analyzer as a worked example of "activation-gated optional agent" pattern; reference the apd-attack-path-discipline skill as the discipline-skill pattern.
   - `README.md` — feature checklist or version table gets a v1.4 entry; the brief sentence describing v1.4 is "attack-path enumeration with D3FEND defensive overlay."

- [ ] **Step 3: Markdown lint + tests + commit**

   ```bash
   pytest tests/test_docs_v14.py -v
   pytest -q
   npx markdownlint-cli2 docs/ README.md 2>&1 || true   # tolerate any pre-existing baseline noise
   git add docs/ README.md tests/test_docs_v14.py
   git commit -m "docs: refresh architecture/running/adapting/schema-evolution/extending-agents/README for v1.4"
   ```

---

## Task C-27: ADR 0010 — Attack-path analysis on partial graphs

**Goal:** Architecture decision record covering the three key design choices: BloodHound-style enumeration on a partial graph with explicit provenance, crown-jewel-declaration-required, bounded-enumeration-with-honest-output, D3FEND overlay for highest-leverage defenses.

**Files:**

- Add: `docs/adrs/0010-attack-path-analysis-on-partial-graphs.md`
- Modify: `tests/test_adrs.py` (assert ADR 0010 exists, has required sections, references the design spec)

- [ ] **Step 1: Write failing tests**

   ```python
   from pathlib import Path
   ADR = Path("docs/adrs/0010-attack-path-analysis-on-partial-graphs.md")

   def test_adr_0010_exists():
       assert ADR.exists()

   def test_adr_0010_has_required_sections():
       text = ADR.read_text()
       assert "# ADR-0010" in text
       assert "Status:" in text
       assert "Date:" in text
       assert "## Context" in text
       assert "## Decision" in text
       assert "## Consequences" in text
       assert "## Alternatives considered" in text

   def test_adr_0010_justifies_partial_graph_approach():
       text = ADR.read_text().lower()
       assert "partial graph" in text
       assert "provenance" in text and "confidence" in text

   def test_adr_0010_justifies_crown_jewel_required():
       text = ADR.read_text().lower()
       assert "crown jewel" in text
       assert "block" in text or "no guessing" in text

   def test_adr_0010_justifies_bounded_enumeration():
       text = ADR.read_text().lower()
       assert "bounded" in text or "max_hop" in text

   def test_adr_0010_justifies_d3fend_overlay():
       assert "D3FEND" in ADR.read_text()

   def test_adr_0010_uses_harmonized_format_like_0008_0009():
       text = ADR.read_text().splitlines()[0]
       assert text.startswith("# ADR-0010:")   # matches 0008/0009 style
   ```

- [ ] **Step 2: Write the ADR**

   Use the canonical hyphen+colon format (same as ADR 0008 / 0009). Key
   sections:

   - **Context** — partial-graph reality of human-authored artifacts; BloodHound
     is the obvious mental model but BloodHound has authoritative AD APIs and
     we don't.
   - **Decision** — adopt BloodHound-style enumeration BUT only on a graph
     where every node and edge carries provenance and confidence. Crown jewels
     must be declared (no guessing). Bounded enumeration with honest output
     ("top-N paths under K hops"). D3FEND overlay for highest-leverage
     defensive guidance. Path enumeration is deterministic graph traversal;
     LLM authors edge provenance from artifact evidence during specialist runs,
     not paths themselves.
   - **Consequences** — analyzer ships behind activation gate, so v1.1-style
     runs unchanged; output is honest about uncertainty (cap at uncertainty
     disposition for low-feasibility paths); operators get actionable D3FEND
     guidance keyed to the bottleneck-edge concept; refresh cadence for D3FEND
     ref data introduced.
   - **Alternatives considered** — (1) graph-DB backing (rejected as overkill;
     in-memory is enough at the bounded sizes), (2) LLM-driven path inference
     (rejected — too easy to invent), (3) crown-jewel guessing from data
     classifications (rejected — operator authority over scope is a design
     principle; see ADR 0008's same posture on taxonomy scoping).

- [ ] **Step 3: Markdown lint + tests + commit**

   ```bash
   pytest tests/test_adrs.py -v
   npx markdownlint-cli2 docs/adrs/0010-*.md 2>&1 || true
   git add docs/adrs/0010-attack-path-analysis-on-partial-graphs.md tests/test_adrs.py
   git commit -m "docs(adr): 0010 attack-path analysis on partial graphs"
   ```

---

## Task C-28: CHANGELOG entry for v1.4.0

**Goal:** Replace the placeholder Phase C entry from the design spec §13 with the actual implementation summary.

**Files:**

- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read the existing CHANGELOG and locate the v1.3.0 entry as a style template**

   ```bash
   head -80 CHANGELOG.md
   ```

- [ ] **Step 2: Insert the v1.4.0 entry at the top of the version list**

   ```markdown
   ## [1.4.0] - 2026-XX-XX

   ### Added

   - **`apd-attack-path-analyzer`** tier-4 activation-gated agent with
     BloodHound-style bounded enumeration over a partial provenance-and-confidence-aware
     graph from declared attacker positions to declared crown jewels.
   - **Asset graph + attack-paths + defense-graph schemas** capturing nodes,
     edges, paths, and the D3FEND defensive overlay on bottleneck edges.
   - **Asset inventory** machine-readable artifact emitted by intake
     (`00-context/asset-inventory.yaml`).
   - **D3FEND defensive overlay** on bottleneck edges with capability backing
     and net-new investment partitioning — highest-leverage defensive guidance
     keyed to D3FEND vocabulary.
   - **Inline Mermaid attack-path diagrams** in the advisory report (≤50 nodes
     per diagram; partitioned by attacker_position for larger graphs).
   - **Domain-pack additions** for `crown_jewels[]`, `attacker_positions[]`,
     `default_trust_boundaries[]`. PBM domain pack ships defaults.
   - **Run-config additions** for `crown_jewels[]` / `attacker_positions[]`
     overrides and the `attack_path_analysis` tuning block (`max_hop`,
     `max_paths_per_pair`, `bottleneck_threshold`).
   - **CLI subcommand** `apd-gauntlet analyze-attack-paths <run_dir>` for
     deterministic, headless graph build + path enumeration + D3FEND overlay.
   - **`apd-attack-path-discipline` skill** codifying never-invent rules for
     nodes and edges, confidence-floors-severity rule, bounded-enumeration
     discipline, and the block-on-missing-crown-jewels rule.
   - **ADR 0010** documenting the partial-graph-with-provenance approach.
   - **`docs/attack-path-analysis.md`** operator guide.
   - **Bundled example** `examples/apd-20260601-claim-event-bus/` exercises the
     full v1.4 pipeline end-to-end (3 attacker positions × 2 crown jewels).

   ### Changed

   - `finding.schema.json` — `agent` enum gains `attack_path_analyzer`;
     `id`/`cross_references`/`merged_from` patterns accept `apath-[0-9a-f]{8}`.
   - `run-config.schema.json` — new optional `crown_jewels`,
     `attacker_positions`, `attack_path_analysis` blocks (all additive).
   - `domain.schema.json` — new optional `crown_jewels`, `attacker_positions`,
     `default_trust_boundaries` arrays (all additive).
   - `apd-intake` — gains `00-context/asset-inventory.yaml` emission when
     crown_jewels are declared.
   - `apd-orchestrator` — topology now describes 16 agents.
   - Synthesizer's 9×N coverage matrix now includes `tmeval-` and `apath-`
     findings from tier-4 specialists.
   - Validator's file-discovery scan picks up asset-inventory, asset-graph,
     attack-paths, defense-graph, attack-path-findings, and validates edge
     endpoints reference real nodes.

   ### Backward compatibility

   All changes additive within v1.x; framework_compat `>=1.0.0,<2.0.0` still
   accepts v1.4.0. A v1.1-style run with no `crown_jewels` and no
   `attacker_positions` produces identical output to v1.3 (analyzer skips
   silently).
   ```

- [ ] **Step 3: Markdown lint + commit**

   ```bash
   npx markdownlint-cli2 CHANGELOG.md 2>&1 || true
   git add CHANGELOG.md
   git commit -m "docs(changelog): v1.4.0 — attack-path analysis with D3FEND overlay"
   ```

---

## Task C-29: Final integration test pass + tag-ready release

**Goal:** Bump version 1.4.0.dev0 → 1.4.0, run full test suite, run all linters, run validator on bundled example, confirm tag-readiness.

**Files:**

- Modify: `pyproject.toml`
- Modify: `tools/apd_gauntlet/__init__.py`
- Modify: `plugin.json`
- Modify: `tests/test_cli.py::test_cli_version`
- Modify: `CHANGELOG.md` (replace `2026-XX-XX` with the release date)

- [ ] **Step 1: Full pre-release verification**

   ```bash
   git status                         # expect: clean
   pytest -q                          # expect: full pass (~410-440 tests after Phase C additions)
   pytest --cov --cov-fail-under=85   # expect: pass at or above gate
   ruff check tools/ tests/           # expect: clean
   mypy tools/                        # expect: clean
   apd-gauntlet lint-agents           # expect: 16 agents clean
   apd-gauntlet validate-domain pbm   # expect: clean
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/   # expect: clean

   # Re-run the bundled example end-to-end to confirm deterministic regeneration
   cp -R examples/apd-20260601-claim-event-bus/expected /tmp/v14-regen
   rm /tmp/v14-regen/40-synthesis/asset-graph.yaml /tmp/v14-regen/40-synthesis/attack-paths.yaml /tmp/v14-regen/40-synthesis/defense-graph.yaml /tmp/v14-regen/40-synthesis/attack-path-findings.yaml
   apd-gauntlet analyze-attack-paths /tmp/v14-regen
   diff -r examples/apd-20260601-claim-event-bus/expected/40-synthesis/ /tmp/v14-regen/40-synthesis/   # expect: only attack-path-report.md differs (hand-authored)
   ```

- [ ] **Step 2: Bump version**

   - `pyproject.toml` line 7: `version = "1.4.0.dev0"` → `version = "1.4.0"`
   - `tools/apd_gauntlet/__init__.py`: `__version__ = "1.4.0.dev0"` → `__version__ = "1.4.0"`
   - `plugin.json`: `"version": "1.4.0.dev0"` → `"version": "1.4.0"`
   - `tests/test_cli.py::test_cli_version`: update string
   - `CHANGELOG.md`: replace `2026-XX-XX` with the actual release date

- [ ] **Step 3: Final test pass after bump**

   ```bash
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   apd-gauntlet --version    # expect: apd-gauntlet, version 1.4.0
   ```

- [ ] **Step 4: Commit + tag**

   ```bash
   git add pyproject.toml tools/apd_gauntlet/__init__.py plugin.json tests/test_cli.py CHANGELOG.md
   git commit -m "release: v1.4.0 — attack-path enumeration with D3FEND defensive overlay (Phase C)"
   git tag -a v1.4.0 -m "APD Gauntlet v1.4.0 — Phase C: attack-path analysis"
   ```

   Do NOT push the tag until user confirms — Phase B's release pattern was to
   merge the PR first, then tag. Mirror that here.

- [ ] **Step 5: Open the release PR**

   ```bash
   git push -u origin <phase-c-branch>
   gh pr create --title "Phase C — Attack-path enumeration + D3FEND defense overlay (v1.4.0)" --body "$(cat <<'EOF'
   ## Summary

   - Adds tier-4 `apd-attack-path-analyzer` agent and supporting Python package (`tools/apd_gauntlet/attack_path/`)
   - Adds four new schemas (asset-inventory, asset-graph, attack-path, defense-graph) and extends finding/run-config/domain schemas
   - Adds CLI subcommand `apd-gauntlet analyze-attack-paths`
   - Adds skill `apd-attack-path-discipline` and ADR 0010
   - Extends intake to emit `00-context/asset-inventory.yaml`
   - Updates synthesizer to include `tmeval-` and `apath-` findings in 9×N coverage matrix
   - Updates PBM domain pack with crown jewels, attacker positions, trust boundaries
   - Extends the claim-event-bus bundled example with full Phase C artifacts
   - All changes additive within v1.x; framework_compat unchanged

   ## Test plan

   - [ ] `pytest -q` passes (expect ~410-440 tests)
   - [ ] `pytest --cov --cov-fail-under=85` passes
   - [ ] `ruff check tools/ tests/` clean
   - [ ] `mypy tools/` clean
   - [ ] `apd-gauntlet lint-agents` reports 16 clean agents
   - [ ] `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/` clean
   - [ ] Bundled example regenerates byte-identical data artifacts under `analyze-attack-paths`

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```

---

## Plan summary

| Track | Tasks | What it produces |
|---|---|---|
| Pre-flight | C-1 | Version bump to dev tag |
| Schema additions | C-2 to C-8 | 4 new schemas + extensions to finding/run-config/domain |
| Python package | C-9 to C-15 | `attack_path/` — graph, builder, enumeration, D3FEND overlay, Mermaid, findings, CLI |
| Skill + agents | C-16 to C-19 | New discipline skill, new tier-4 agent, intake update, orchestrator update |
| Validator + synthesizer | C-20 to C-21 | Validator picks up new artifacts; coverage matrix includes tier-4 findings |
| Templates + domain pack | C-22 to C-23 | 4 new templates; PBM domain pack defaults |
| Example | C-24 | Bundled claim-event-bus exercises full v1.4 pipeline |
| Docs | C-25 to C-26 | New attack-path-analysis.md + refresh of 5 existing docs |
| ADR + release | C-27 to C-29 | ADR 0010, CHANGELOG, v1.4.0 tag |

**Total:** 29 tasks. Expected test count: 346 → ~410-440. Expected file additions: ~30 (4 schemas, ~7 Python modules, ~5 templates, 4 example artifacts, 1 doc, 1 ADR, 1 skill, 1 agent, 1 inventory template, plus tests for each).

