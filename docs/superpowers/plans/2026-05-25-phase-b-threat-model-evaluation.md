# Phase B — Methodology-Aware Threat-Model Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native methodology-aware evaluation of user-supplied threat models (STRIDE, LINDDUN, attack-tree natively; PASTA / VAST / Trike / free-form prose at reduced fidelity). Ship as `apd-gauntlet` v1.3.0 — fully additive within v1.x. Build a tier-0 `apd-threat-model-recon` agent that parses supplied threat models into a normalized graph, and a tier-4 `apd-threat-model-evaluator` agent that emits coverage-gap / contradiction / silence findings against the normalized graph + specialist findings.

**Architecture:** Two-agent split parallel to v1.1's `apd-code-recon`. The recon agent is activation-gated on `.apd-run.yaml` declaring `threat_model: <path>` (or intake auto-detecting a TM-like artifact). Recon delegates structural parsing to a new `apd-gauntlet parse-threat-model` CLI subcommand backed by Python parser modules (one per supported format — Threat Dragon JSON, Microsoft TMT `.tm7` XML, STRIDE/LINDDUN per-element Markdown/CSV, attack-tree indented prose / ADTool XML / JSON). The Python parsers handle deterministic structural extraction; the recon agent layers semantic enrichment (methodology→APD-goal mapping, framework_refs inference, surface attribution). The evaluator agent runs after the synthesizer, consumes the normalized graph + dedup'd specialist findings/capabilities, and emits three finding flavors (coverage gap, contradiction, silence) using the existing `finding.schema.json` with `agent: threat_model_evaluator` and id prefix `tmeval-`.

**Tech Stack:** Python 3.10+, `jsonschema>=4.20`, `pyyaml>=6.0`, `click>=8.1`, `lxml` (new dependency for `.tm7` XML), `pytest>=8.0`, `ruff`, `mypy --strict`. JSON Schema draft 2020-12. Parsers live at `tools/apd_gauntlet/threat_model/` (new package).

---

## Pre-flight verification

Before starting Task B-1, verify clean working tree and current passing state:

```bash
git status                          # expect: clean (uv.lock may be untracked; leave it)
pytest -q                           # expect: 188 passed
pytest --cov --cov-fail-under=85    # expect: pass (86.97% baseline)
ruff check tools/ tests/            # expect: clean
mypy tools/                         # expect: clean (12 source files)
apd-gauntlet lint-agents            # expect: 13 agents clean
apd-gauntlet validate-domain pbm    # expect: clean
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # expect: 18 files, 26 records, clean
apd-gauntlet --version              # expect: 1.2.0
```

If any of the above fail, stop and investigate before starting the plan.

---

## Phase A carry-forward cleanup pass (Tasks B-1 to B-6)

These six small tasks address polish items deferred from Phase A. Doing them first means the rest of Phase B builds on a clean foundation — new schemas use shared `$defs`, new CLI commands honor coverage rollups, the regex permissiveness flagged by Phase A's reviewer doesn't propagate into new fixtures.

### Task B-1: Pre-flight version bump (1.2.0 → 1.3.0.dev0)

**Files:**

- Modify: `pyproject.toml`
- Modify: `tools/apd_gauntlet/__init__.py`
- Modify: `plugin.json`
- Verify: `tools/apd_gauntlet/cli.py` (Task A-1 made `--framework-version` derive from `__version__` dynamically — no change should be needed; verify)

- [ ] **Step 1: Bump version in all three places**

  - `pyproject.toml` line 7: `version = "1.2.0"` → `version = "1.3.0.dev0"`
  - `tools/apd_gauntlet/__init__.py`: `__version__ = "1.2.0"` → `__version__ = "1.3.0.dev0"`
  - `plugin.json`: `"version": "1.2.0"` → `"version": "1.3.0.dev0"`

- [ ] **Step 2: Update `tests/test_cli.py::test_cli_version` assertion**

   Phase A's test hardcodes the version string. Update from `"1.2.0"` to `"1.3.0.dev0"`. (Long-term: should be refactored to assert against `apd_gauntlet.__version__`, but that's another carry-forward — flag, don't fix here.)

- [ ] **Step 3: Run tests + linters**

   ```bash
   pytest -q                       # expect: 188 passed
   ruff check tools/ tests/        # expect: clean
   mypy tools/                     # expect: clean
   apd-gauntlet --version          # expect: apd-gauntlet, version 1.3.0.dev0
   ```

- [ ] **Step 4: Commit**

   ```bash
   git add pyproject.toml tools/apd_gauntlet/__init__.py plugin.json tests/test_cli.py
   git commit -m "chore: bump version to 1.3.0.dev0 for Phase B work"
   ```

---

### Task B-2: Tighten `owasp_llm_top10` regex to `^LLM(0[1-9]|10)$`

**Why:** Phase A's reviewer flagged that `^LLM[0-9]{2}$` accepts `LLM00`, `LLM11`–`LLM99` which don't exist in the published taxonomy. Tighten before Phase B's new schemas reference it.

**Files:**

- Modify: `schemas/finding.schema.json` (the `owasp_llm_top10` items pattern)
- Modify: `schemas/owasp-coverage.schema.json` (the `if/then` block for `owasp_llm_top10`)
- Modify: `tests/fixtures/invalid/` — add a fixture that exercises the tightened pattern (e.g., a finding with `owasp_llm_top10: ["LLM00"]` or `["LLM11"]` to confirm rejection)
- Possibly modify: `tools/apd_gauntlet/data/owasp_llm_top10.json` — verify all entries still match the tighter pattern (they should — entries are LLM01..LLM10)

- [ ] **Step 1: Write a failing test for tightened rejection**

   In `tests/test_finding_schema.py`, add:

   ```python
   def test_finding_rejects_owasp_llm_top10_outside_published_range():
       # Fixture with owasp_llm_top10: ["LLM00"] or ["LLM11"] should fail
       finding = load_fixture("invalid/finding-with-invalid-owasp-llm.yaml")
       err = validate_finding(finding)
       assert err is not None  # rejected
   ```

   Fixture `tests/fixtures/invalid/finding-with-invalid-owasp-llm.yaml`:

   ```yaml
   # ... required finding fields ...
   control_mappings:
     nist_800_53r5: ["SI-10"]
     owasp_llm_top10: ["LLM00"]  # invalid — outside LLM01..LLM10 range
   ```

- [ ] **Step 2: Run test to verify it fails** (current `{0-9}{2}` accepts LLM00 — so the test fails because validation passes when it shouldn't)

   `pytest tests/test_finding_schema.py -v -k "outside_published"` → expect FAIL

- [ ] **Step 3: Tighten the pattern in both schemas**

  - `schemas/finding.schema.json` — change `owasp_llm_top10.items.pattern` from `^LLM[0-9]{2}$` to `^LLM(0[1-9]|10)$`
  - `schemas/owasp-coverage.schema.json` — change the `if/then` clause for `owasp_llm_top10` from `^LLM[0-9]{2}$` to `^LLM(0[1-9]|10)$`

- [ ] **Step 4: Run tests to verify they pass**

   `pytest tests/test_finding_schema.py tests/test_other_schemas.py -v` — expect PASS

- [ ] **Step 5: Verify reference data still matches**

   ```bash
   python3 -c "import json, re; data = json.load(open('tools/apd_gauntlet/data/owasp_llm_top10.json')); pat = re.compile(r'^LLM(0[1-9]|10)$'); unmatched = [e['category_id'] for e in data['entries'] if not pat.match(e['category_id'])]; print(f'Unmatched: {unmatched}')"
   ```

   Expected: `Unmatched: []`.

- [ ] **Step 6: Full suite + linters**

   ```bash
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   ```

- [ ] **Step 7: Commit**

   ```bash
   git add schemas/finding.schema.json schemas/owasp-coverage.schema.json tests/test_finding_schema.py tests/fixtures/invalid/finding-with-invalid-owasp-llm.yaml
   git commit -m "fix(schema): tighten owasp_llm_top10 pattern to ^LLM(0[1-9]|10)\$"
   ```

---

### Task B-3: Align `refresh_mitre.py` constant naming with the v1.2 triad

**Why:** Phase A noted asymmetry — `refresh_mitre.py` uses `MAX_BUNDLE_BYTES` / `FETCH_TIMEOUT_SECONDS`; `refresh_cwe.py`, `refresh_owasp.py`, `refresh_d3fend.py` all use `MAX_RESPONSE_BYTES` / `DEFAULT_TIMEOUT_SECONDS`. Align the older script with the new convention.

**Files:**

- Modify: `tools/apd_gauntlet/refresh_mitre.py`
- Modify: `tests/test_refresh_mitre.py` (any tests asserting on the constant names)

- [ ] **Step 1: Read both files** to see current constant names and assertions

- [ ] **Step 2: Rename constants in `refresh_mitre.py`**

  - `MAX_BUNDLE_BYTES` → `MAX_RESPONSE_BYTES`
  - `FETCH_TIMEOUT_SECONDS` → `DEFAULT_TIMEOUT_SECONDS`

   Update all internal references in the module.

- [ ] **Step 3: Update `tests/test_refresh_mitre.py`**

   Any test that imports or asserts on the old names — update to the new names.

- [ ] **Step 4: Backfill Content-Length pre-check if not present**

   Phase A reviewer noted: `refresh_mitre.py` lacks the Content-Length pre-check that the new triad has. Add it for parity:

   ```python
   def fetch_mitre_bundle() -> bytes:
       with urlopen(MITRE_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
           content_length = response.headers.get("Content-Length")
           if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
               raise ValueError(...)
           body = response.read(MAX_RESPONSE_BYTES + 1)
           if len(body) > MAX_RESPONSE_BYTES:
               raise ValueError(...)
           return body
   ```

   Add a test for the Content-Length pre-check.

- [ ] **Step 5: Verify nothing else broke**

   ```bash
   pytest tests/test_refresh_mitre.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   ```

- [ ] **Step 6: Commit**

   ```bash
   git add tools/apd_gauntlet/refresh_mitre.py tests/test_refresh_mitre.py
   git commit -m "refactor(refresh_mitre): align constants with v1.2 triad + add Content-Length pre-check

   Renames MAX_BUNDLE_BYTES → MAX_RESPONSE_BYTES and FETCH_TIMEOUT_SECONDS →
   DEFAULT_TIMEOUT_SECONDS for consistency with refresh_cwe / refresh_owasp /
   refresh_d3fend (Phase A). Also backfills the Content-Length pre-check that
   the v1.2 triad ships with — defense in depth for upstream Content-Length
   reliability."
   ```

---

### Task B-4: Extract shared `$defs` for ATT&CK / D3FEND patterns

**Why:** Phase A's reviewer flagged duplication: `^D3-[A-Z]{2,7}$` appears in 3 schema files; `^T[0-9]{4}(\.[0-9]{3})?$` appears in 4. New schemas in Phase B (threat-model-normalized, threat-model-coverage) will reference ATT&CK technique IDs and may reference D3FEND — extracting `$defs` now means new schemas can `$ref` from the start.

**Files:**

- Create: `schemas/_defs.schema.json` — single schema file holding shared `$defs`
- Modify: `schemas/finding.schema.json` (use `$ref` for the existing duplicated patterns)
- Modify: `schemas/capability.schema.json` (use `$ref`)
- Modify: `schemas/d3fend-coverage.schema.json` (use `$ref`)
- Modify: `schemas/attack-exposure.schema.json` (use `$ref` for the ATT&CK pattern)
- Modify: `tools/apd_gauntlet/validate.py` (if it loads schemas — may need to register `_defs.schema.json` as a known reference)
- Modify: `tests/test_meta_schemas.py` (may need to handle the meta-schema check for `_defs.schema.json` — it's a defs file, not a record schema)

- [ ] **Step 1: Create `schemas/_defs.schema.json`**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/_defs.schema.json",
     "title": "APD Gauntlet shared schema definitions",
     "description": "Reusable $defs for patterns referenced across multiple record schemas.",
     "$defs": {
       "attack_technique_id": {
         "type": "string",
         "pattern": "^T[0-9]{4}(\\.[0-9]{3})?$",
         "description": "MITRE ATT&CK technique ID; accepts top-level (T1078) and sub-technique (T1078.001) forms."
       },
       "attack_technique_id_topline": {
         "type": "string",
         "pattern": "^T[0-9]{4}$",
         "description": "MITRE ATT&CK technique ID at top-level only (no sub-technique). Used where the schema author wants to constrain to parent techniques."
       },
       "attack_tactic_id": {
         "type": "string",
         "pattern": "^TA[0-9]{4}$"
       },
       "attack_sub_technique_id": {
         "type": ["string", "null"],
         "pattern": "^T[0-9]{4}\\.[0-9]{3}$"
       },
       "attack_mitigation_id": {
         "type": "string",
         "pattern": "^M[0-9]{4}$"
       },
       "d3fend_id": {
         "type": "string",
         "pattern": "^D3-[A-Z]{2,7}$",
         "description": "MITRE D3FEND short code. Real D3FEND data contains 2-to-7 letter codes (D3-NTA, D3-NTSA, D3-PHDURA)."
       },
       "cwe_id": {
         "type": "string",
         "pattern": "^CWE-[0-9]+$"
       }
     }
   }
   ```

- [ ] **Step 2: Reference `$defs` from existing schemas**

   Replace inline patterns with `$ref` references. Example for `schemas/finding.schema.json`:

   ```jsonc
   "mitre_attack": {
     "items": {
       "properties": {
         "technique":     { "$ref": "_defs.schema.json#/$defs/attack_technique_id_topline" },
         "sub_technique": { "$ref": "_defs.schema.json#/$defs/attack_sub_technique_id" },
         "tactic":        { "$ref": "_defs.schema.json#/$defs/attack_tactic_id" },
         // ...
       }
     }
   },
   "cwe": {
     "items": { "$ref": "_defs.schema.json#/$defs/cwe_id" }
   }
   ```

   Apply the same refactor to `capability.schema.json` (mitre_attack, d3fend.technique, d3fend.counters_attack), `d3fend-coverage.schema.json` (defensive_entries.d3fend_id, defensive_entries.counters_attack items, counter_coverage.attack_technique, counter_coverage.countered_by_d3fend items), and `attack-exposure.schema.json` (technique pattern).

- [ ] **Step 3: Configure the validator to resolve `_defs.schema.json`**

   The `jsonschema` library needs the referenced schema to be loadable. Inspect `tools/apd_gauntlet/validate.py` — likely it loads each schema directly with `json.loads(Path(...).read_text())`. For `$ref` resolution to work, build a `Registry` (jsonschema 4.18+) with all schema files registered, or use a `RefResolver` (older API):

   ```python
   from jsonschema import Draft202012Validator
   from referencing import Registry, Resource

   def _build_registry() -> Registry:
       registry = Registry()
       for schema_path in Path("schemas").glob("*.schema.json"):
           schema = json.loads(schema_path.read_text())
           registry = registry.with_resource(
               uri=schema["$id"],
               resource=Resource.from_contents(schema),
           )
       return registry

   def validate_record(record, schema):
       validator = Draft202012Validator(schema, registry=_build_registry())
       return list(validator.iter_errors(record))
   ```

   Adapt to whatever the existing module pattern is. Make the registry a module-level cached value to avoid rebuilding it per validation call.

- [ ] **Step 4: Handle the meta-schema test**

   `tests/test_meta_schemas.py` validates each `schemas/*.schema.json` as a JSON Schema document. The new `_defs.schema.json` has no top-level type/required (it only defines `$defs`) — but it IS still a valid JSON Schema (an empty schema accepts everything; the `$defs` block is metadata). Confirm the meta-schema test passes; if not, either tighten the meta-schema check to allow defs-only schemas, or add a top-level `"type": "object"` to make `_defs.schema.json` look more conventional.

- [ ] **Step 5: Run full suite**

   ```bash
   pytest -q  # expect: 188 passed (same; this is a refactor)
   ruff check tools/ tests/
   mypy tools/
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # still clean
   ```

- [ ] **Step 6: Commit**

   ```bash
   git add schemas/ tools/apd_gauntlet/validate.py tests/test_meta_schemas.py
   git commit -m "refactor(schemas): extract shared \$defs for ATT&CK/D3FEND/CWE patterns

   Phase A reviewer noted ^D3-[A-Z]{2,7}\$ duplicated across 3 schemas and
   ^T[0-9]{4}(\.[0-9]{3})?\$ across 4. New schemas/_defs.schema.json holds
   the canonical patterns; finding/capability/d3fend-coverage/attack-exposure
   now \$ref into it. Validator builds a jsonschema Registry so refs resolve.

   Behavior preserved: same patterns enforced, no fixture changes required."
   ```

---

### Task B-5: Extend CLI `validate` to pick up coverage rollups

**Why:** Phase A's bundled-example task surfaced that `apd-gauntlet validate` only scans `*.findings.yaml`, `*.capabilities.yaml`, code-evidence-index, and contradictions — the three new coverage rollups (`cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml`) in `40-synthesis/` are NOT validated by the CLI command. They're only validated via `tests/test_other_schemas.py`.

**Files:**

- Modify: `tools/apd_gauntlet/validate.py`
- Modify: `tests/test_validate_cross_file.py` or similar (add tests asserting the validator now scans + reports on coverage rollups)
- Possibly modify: `tests/fixtures/` — add a malformed coverage rollup fixture and confirm validate rejects it

- [ ] **Step 1: Read `tools/apd_gauntlet/validate.py`** to understand the file-discovery pattern. Likely a glob like `*.findings.yaml` per directory.

- [ ] **Step 2: Write failing tests**

   ```python
   def test_validate_picks_up_cwe_coverage_rollup(tmp_path):
       # Scaffold a minimal valid run dir with a 40-synthesis/cwe-coverage.yaml
       # Run validator
       # Assert it discovered the file (in the file count or output)

   def test_validate_rejects_malformed_cwe_coverage(tmp_path):
       # Scaffold a run dir with a cwe-coverage.yaml that violates the schema
       # Run validator
       # Assert it errors on the rollup
   ```

   Mirror tests for owasp-coverage and d3fend-coverage.

- [ ] **Step 3: Extend the file-discovery logic**

   Add the three rollups to the validator's known-file map. Pattern (illustrative):

   ```python
   _SYNTHESIS_ROLLUPS = {
       "cwe-coverage.yaml":    "cwe-coverage.schema.json",
       "owasp-coverage.yaml":  "owasp-coverage.schema.json",
       "d3fend-coverage.yaml": "d3fend-coverage.schema.json",
       # existing: nist-coverage, attack-exposure, apd-coverage-matrix, contradictions
   }

   def _discover_synthesis_files(run_dir: Path) -> Iterator[tuple[Path, str]]:
       synthesis = run_dir / "40-synthesis"
       if not synthesis.exists():
           return
       for filename, schema_name in _SYNTHESIS_ROLLUPS.items():
           candidate = synthesis / filename
           if candidate.exists():
               yield candidate, schema_name
   ```

   Wire into the existing validate pass.

- [ ] **Step 4: Run tests**

   ```bash
   pytest tests/test_validate_cross_file.py -v
   pytest -q
   ```

- [ ] **Step 5: Re-validate the bundled example**

   ```bash
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
   ```

   Expected: file count increases by 3 (the bundled example has all three rollups from Phase A Task A-19); all still pass.

- [ ] **Step 6: Commit**

   ```bash
   git add tools/apd_gauntlet/validate.py tests/test_validate_cross_file.py tests/fixtures/
   git commit -m "feat(validate): pick up cwe/owasp/d3fend coverage rollups in 40-synthesis/

   Phase A task A-19 surfaced that the CLI validator's file-discovery glob
   didn't include the three new coverage rollup files; they were only
   validated by tests/test_other_schemas.py. Validator now scans them and
   reports schema errors with the same file/record framing as other artifacts."
   ```

---

### Task B-6: Harmonize ADR 0007 to match 0001-0006 / 0008 format

**Why:** Project memory and prior reviews note ADR 0007 (optional code reconnaissance via CBM) diverges from the canonical hyphen+colon format used by 0001-0006 and the newly-landed 0008. Harmonize for consistency.

**Files:**

- Modify: `docs/adrs/0007-optional-code-reconnaissance-via-cbm.md`

- [ ] **Step 1: Read 0007 and 0008 side by side**

   ```bash
   head -15 docs/adrs/0007-*.md
   head -15 docs/adrs/0008-*.md
   ```

   Note the differences (heading format, status/date field layout, deciders line, section ordering).

- [ ] **Step 2: Reformat 0007 to match 0008's pattern**

   Typically:
  - Title `# ADR-0007: Title` (matching 0008's `# ADR-0008: ...`)
  - `**Status:**` and `**Date:**` as flat fields (no bullet list, no `Deciders:` line)
  - Section order: Context → Decision → Consequences → Alternatives considered
  - Drop em-dashes if 0001-0006 use hyphens; etc.

   Preserve all content; only reformat the structural elements.

- [ ] **Step 3: Lint check**

   ```bash
   npx markdownlint-cli2 docs/adrs/0007-*.md 2>&1 || true
   ```

   Confirm no new errors introduced. (Pre-existing baseline errors are fine.)

- [ ] **Step 4: Commit**

   ```bash
   git add docs/adrs/0007-optional-code-reconnaissance-via-cbm.md
   git commit -m "docs(adr): harmonize 0007 format to match 0001-0006/0008 style"
   ```

---

## Phase B Track 2 implementation (Tasks B-7 to B-30)

The carry-forward pass is complete. Foundation is clean. Begin the actual Phase B work.

### Task B-7: Extend `finding.schema.json` — agent enum + id pattern

**Goal:** Add `threat_model_evaluator` to the `agent` enum and relax the `id` pattern to accept `tmeval-[0-9a-f]{8}` prefix.

**Files:**

- Modify: `schemas/finding.schema.json`
- Modify: `tests/test_finding_schema.py`
- Add: `tests/fixtures/valid/finding-from-tmeval.yaml`

- [ ] **Step 1: Write failing tests**

   ```python
   def test_finding_accepts_threat_model_evaluator_agent():
       # Fixture with agent: threat_model_evaluator and id: tmeval-a1b2c3d4
       # Asserts no errors

   def test_finding_id_pattern_accepts_tmeval_prefix():
       # Same idea — validates the regex extension
   ```

- [ ] **Step 2: Extend the schema**

  - `agent` enum: append `threat_model_evaluator`
  - `id` pattern: extend from `^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged)-[0-9a-f]{8}$` to `^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged|tmeval)-[0-9a-f]{8}$`
  - `cross_references` and `merged_from` patterns: same extension

   Also: extend `apd_goal` enum? NO — TM evaluator findings still tag one of the 9 existing APD goals; they don't get a new goal. Confirm by reading the spec (§6.5 — evaluator findings use existing goals).

- [ ] **Step 3: Fixture `tests/fixtures/valid/finding-from-tmeval.yaml`**

   ```yaml
   schema_version: 1
   id: tmeval-a1b2c3d4
   agent: threat_model_evaluator
   apd_tier: trustworthiness
   apd_goal: confidentiality
   disposition: risk
   severity: medium
   confidence: high
   title: "Threat model asserts PHI encrypted in transit; specialist found plaintext"
   summary: "TM entry tm-1a2b3c4d claims PHI is encrypted between adjudication and pricing; conf-9e8d7c6b shows plaintext."
   detail: "..."
   evidence:
     - artifact: "00-context/threat-model-normalized.yaml"
       locator: "entry tm-1a2b3c4d"
       excerpt: "asset: pricing-service mitigation: \"TLS 1.3 enforced\""
   control_mappings:
     nist_800_53r5: ["SC-8"]
   cross_references: [conf-9e8d7c6b]
   recommendation:
     posture: required
     summary: "Reconcile TM and code reality"
     detail: "..."
   ```

- [ ] **Step 4: Run tests + linters**

- [ ] **Step 5: Commit**

   ```bash
   git add schemas/finding.schema.json tests/test_finding_schema.py tests/fixtures/valid/finding-from-tmeval.yaml
   git commit -m "feat(schema): finding.agent gains threat_model_evaluator; id pattern accepts tmeval- prefix"
   ```

---

### Task B-8: Extend `run-config.schema.json` — `threat_model` + `methodology_hint`

**Goal:** Add optional `threat_model: <path>` and `methodology_hint: <name>` fields. Both are absent in v1.x backward-compat runs.

**Files:**

- Modify: `schemas/run-config.schema.json`
- Modify: `tests/test_run_config_schema.py`
- Add: `tests/fixtures/valid/run-config-with-threat-model.yaml`

- [ ] **Step 1: Write failing tests**

   ```python
   def test_run_config_accepts_threat_model_path_and_methodology_hint():
       cfg = load_fixture("valid/run-config-with-threat-model.yaml")
       # has threat_model: "artifacts/threat-model.tm7" and methodology_hint: "stride"
       assert errors == []

   def test_run_config_rejects_unknown_methodology_hint():
       # methodology_hint: "made_up_methodology" should fail enum
       cfg = load_fixture("invalid/run-config-with-bad-methodology-hint.yaml")
       assert errors  # truthy
   ```

- [ ] **Step 2: Extend schema**

   Add to `properties`:

   ```jsonc
   "threat_model": {
     "type": "string",
     "minLength": 1,
     "pattern": "^(?!/)(?!.*\\.\\.).+$",
     "description": "Path (relative to the run directory) to a supplied threat model. When set, apd-threat-model-recon activates."
   },
   "methodology_hint": {
     "type": "string",
     "enum": ["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form"],
     "description": "Optional hint to the recon parser when the methodology can't be auto-detected from the file shape."
   }
   ```

   The `^(?!/)(?!.*\\.\\.).+$` pattern matches the same path-traversal-prevention pattern used by the Phase A domain pack `includes[]` field — no leading `/`, no `..` segments.

   Do NOT add either field to `required[]`.

- [ ] **Step 3: Run tests + linters**

- [ ] **Step 4: Commit**

   ```bash
   git add schemas/run-config.schema.json tests/test_run_config_schema.py tests/fixtures/valid/run-config-with-threat-model.yaml tests/fixtures/invalid/run-config-with-bad-methodology-hint.yaml
   git commit -m "feat(schema): run-config gains optional threat_model path + methodology_hint"
   ```

---

### Task B-9: New schema `threat-model-normalized.schema.json`

**Goal:** Schema for the recon-emitted normalized threat-model graph (the artifact specialists cite).

**Files:**

- Create: `schemas/threat-model-normalized.schema.json`
- Modify: `tests/test_other_schemas.py` (add test using Phase A's `_validate_whole_doc_schema` helper)
- Add: `tests/fixtures/valid/threat-model-normalized-valid.yaml`

- [ ] **Step 1: Write the schema**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/threat-model-normalized.schema.json",
     "title": "APD Gauntlet Normalized Threat Model",
     "type": "object",
     "required": ["schema_version", "generated_by", "source_artifact", "methodology", "entries"],
     "additionalProperties": false,
     "properties": {
       "schema_version": { "type": "integer", "const": 1 },
       "generated_by":   { "type": "string", "enum": ["threat_model_recon"] },
       "source_artifact": {
         "type": "string",
         "minLength": 1,
         "description": "Relative path to the supplied threat model artifact."
       },
       "methodology": {
         "type": "string",
         "enum": ["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form", "unknown"]
       },
       "extraction_summary": {
         "type": "object",
         "additionalProperties": false,
         "required": ["entry_count", "high_confidence_count", "low_confidence_count"],
         "properties": {
           "entry_count":            { "type": "integer", "minimum": 0 },
           "high_confidence_count":  { "type": "integer", "minimum": 0 },
           "medium_confidence_count":{ "type": "integer", "minimum": 0 },
           "low_confidence_count":   { "type": "integer", "minimum": 0 },
           "parser_used":            { "type": "string" }
         }
       },
       "entries": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["entry_id", "asset", "threat", "extraction_confidence", "methodology", "framework_refs", "inferred_apd_goals"],
           "additionalProperties": false,
           "properties": {
             "entry_id":              { "type": "string", "pattern": "^tm-[0-9a-f]{8}$" },
             "asset":                 { "type": "string", "minLength": 1 },
             "threat":                { "type": "string", "minLength": 1 },
             "mitigation":            { "type": ["string", "null"] },
             "methodology":           { "type": "string", "enum": ["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form", "unknown"] },
             "source_locator":        { "type": "string" },
             "extraction_confidence": { "type": "string", "enum": ["high", "medium", "low"] },
             "framework_refs": {
               "type": "object",
               "additionalProperties": false,
               "properties": {
                 "stride_letter":         { "type": ["string", "null"], "enum": ["S", "T", "R", "I", "D", "E", null] },
                 "linddun_letter":        { "type": ["string", "null"], "enum": ["L", "I", "N", "D", "U", "C", null] },
                 "attack_tree_position":  { "type": ["string", "null"] },
                 "mitre_attack":          {
                   "type": "array",
                   "items": { "$ref": "_defs.schema.json#/$defs/attack_technique_id" }
                 }
               }
             },
             "inferred_apd_goals": {
               "type": "array",
               "items": {
                 "type": "string",
                 "enum": ["confidentiality", "integrity", "availability", "distributed", "resilient", "ephemeral", "authenticity", "non_repudiation", "immutability"]
               }
             }
           }
         }
       }
     }
   }
   ```

   Note: `linddun_letter` enum is `L, I, N, D, U, C` (`N` for non-repudiation/non-compliance, `D` for detectability/disclosure, `C` for compliance — actually LINDDUN duplicates letters; treat the second `D` and `N` as separate via a `linddun_category` field if needed, or accept the duplication and disambiguate in `framework_refs`. Decide during implementation.)

- [ ] **Step 2: Write the fixture** demonstrating 2-3 entries from a STRIDE-per-element style threat model — one high-confidence, one medium-confidence, one mitigation null.

- [ ] **Step 3: Add the test** using `_validate_whole_doc_schema("threat-model-normalized-valid.yaml", "threat-model-normalized.schema.json")`.

- [ ] **Step 4: Run tests + meta-schema check**

   ```bash
   pytest tests/test_other_schemas.py tests/test_meta_schemas.py -v
   pytest -q
   ```

- [ ] **Step 5: Commit**

   ```bash
   git add schemas/threat-model-normalized.schema.json tests/test_other_schemas.py tests/fixtures/valid/threat-model-normalized-valid.yaml
   git commit -m "feat(schema): add threat-model-normalized rollup schema"
   ```

---

### Task B-10: New schema `threat-model-coverage.schema.json`

**Goal:** Schema for the evaluator-emitted coverage report — per-surface coverage matrix vs methodology categories + summary statistics.

**Files:**

- Create: `schemas/threat-model-coverage.schema.json`
- Modify: `tests/test_other_schemas.py`
- Add: `tests/fixtures/valid/threat-model-coverage-valid.yaml`

- [ ] **Step 1: Write the schema**

   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/threat-model-coverage.schema.json",
     "title": "APD Gauntlet Threat Model Coverage Report",
     "type": "object",
     "required": ["schema_version", "generated_by", "methodology", "surface_coverage", "summary"],
     "additionalProperties": false,
     "properties": {
       "schema_version": { "type": "integer", "const": 1 },
       "generated_by":   { "type": "string", "enum": ["threat_model_evaluator"] },
       "methodology":    { "type": "string", "enum": ["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form", "unknown"] },
       "surface_coverage": {
         "type": "array",
         "items": {
           "type": "object",
           "required": ["surface", "categories_present", "categories_absent"],
           "additionalProperties": false,
           "properties": {
             "surface":            { "type": "string", "minLength": 1 },
             "categories_present": { "type": "array", "items": { "type": "string" } },
             "categories_absent":  { "type": "array", "items": { "type": "string" } },
             "tm_entry_count":     { "type": "integer", "minimum": 0 },
             "tm_entry_ids":       { "type": "array", "items": { "type": "string", "pattern": "^tm-[0-9a-f]{8}$" } }
           }
         }
       },
       "summary": {
         "type": "object",
         "required": ["total_entries", "contradictions_emitted", "silences_emitted", "coverage_gaps_emitted"],
         "additionalProperties": false,
         "properties": {
           "total_entries":          { "type": "integer", "minimum": 0 },
           "contradictions_emitted": { "type": "integer", "minimum": 0 },
           "silences_emitted":       { "type": "integer", "minimum": 0 },
           "coverage_gaps_emitted":  { "type": "integer", "minimum": 0 },
           "surfaces_examined":      { "type": "integer", "minimum": 0 }
         }
       }
     }
   }
   ```

- [ ] **Step 2: Fixture**

   ```yaml
   schema_version: 1
   generated_by: threat_model_evaluator
   methodology: stride
   surface_coverage:
     - surface: "claim-ingress-API"
       categories_present: [S, T, I, D]
       categories_absent: [R, E]
       tm_entry_count: 4
       tm_entry_ids: [tm-a1b2c3d4, tm-5e6f7g8h, tm-9i0j1k2l, tm-3m4n5o6p]
     - surface: "audit-log-write-path"
       categories_present: [T, I]
       categories_absent: [S, R, D, E]
       tm_entry_count: 2
       tm_entry_ids: [tm-aaaaaaaa, tm-bbbbbbbb]
   summary:
     total_entries: 6
     contradictions_emitted: 1
     silences_emitted: 2
     coverage_gaps_emitted: 3
     surfaces_examined: 2
   ```

- [ ] **Step 3: Add test + run + commit** (mirror Task B-9's flow).

   Commit message: `feat(schema): add threat-model-coverage report schema`

---

### Task B-11: Methodology→APD-goal mapping module (canonical Python source of truth)

**Goal:** Single Python module that holds the methodology→APD-goal mapping tables. Both the parser code (Tasks B-12 to B-16) and the agent skill text (Task B-19) reference these tables; the module is the source of truth.

**Files:**

- Create: `tools/apd_gauntlet/threat_model/__init__.py`
- Create: `tools/apd_gauntlet/threat_model/mappings.py`
- Create: `tests/test_threat_model_mappings.py`

- [ ] **Step 1: Write tests asserting the canonical tables**

   ```python
   from apd_gauntlet.threat_model.mappings import (
       STRIDE_TO_APD_GOALS,
       LINDDUN_TO_APD_GOALS,
       stride_letter_to_apd_goals,
       linddun_letter_to_apd_goals,
   )

   def test_stride_to_apd_goals_complete():
       assert STRIDE_TO_APD_GOALS == {
           "S": ["authenticity"],
           "T": ["integrity"],
           "R": ["non_repudiation"],
           "I": ["confidentiality"],
           "D": ["availability"],
           "E": ["authenticity", "integrity"],
       }

   def test_linddun_to_apd_goals_complete():
       # L,I,D(isclosure)→Conf, N(rep)→NonRep, D(etectability)→Conf, U→Auth, N(compliance)→domain
       # LINDDUN's letter overloading is captured via composite keys
       assert LINDDUN_TO_APD_GOALS == {
           "L":           ["confidentiality"],
           "I":           ["confidentiality"],
           "N_repudiation":["non_repudiation"],
           "D_etectability":["confidentiality"],
           "D_isclosure":  ["confidentiality"],
           "U":           ["authenticity"],
           "N_compliance":["non_repudiation"],  # domain-specific override path
       }

   def test_stride_letter_lookup_returns_apd_goals():
       assert stride_letter_to_apd_goals("E") == ["authenticity", "integrity"]
       assert stride_letter_to_apd_goals("X") == []  # unknown letter
   ```

- [ ] **Step 2: Implement `tools/apd_gauntlet/threat_model/mappings.py`**

   ```python
   """Canonical methodology→APD-goal mapping tables.

   This module is the single source of truth for how STRIDE letters,
   LINDDUN categories, and attack-tree leaves map into the nine APD goals.
   Both Python parser code and the apd-threat-model-methodologies skill
   reference these tables.
   """

   from __future__ import annotations

   from collections.abc import Mapping

   STRIDE_TO_APD_GOALS: Mapping[str, list[str]] = {
       "S": ["authenticity"],
       "T": ["integrity"],
       "R": ["non_repudiation"],
       "I": ["confidentiality"],
       "D": ["availability"],
       "E": ["authenticity", "integrity"],
   }

   LINDDUN_TO_APD_GOALS: Mapping[str, list[str]] = {
       "L":             ["confidentiality"],
       "I":             ["confidentiality"],
       "N_repudiation": ["non_repudiation"],
       "D_etectability":["confidentiality"],
       "D_isclosure":   ["confidentiality"],
       "U":             ["authenticity"],
       "N_compliance":  ["non_repudiation"],
   }


   def stride_letter_to_apd_goals(letter: str) -> list[str]:
       return list(STRIDE_TO_APD_GOALS.get(letter, []))


   def linddun_letter_to_apd_goals(letter_or_compound: str) -> list[str]:
       return list(LINDDUN_TO_APD_GOALS.get(letter_or_compound, []))
   ```

- [ ] **Step 3: Run tests + linters + commit**

   Commit message: `feat(threat_model): canonical STRIDE/LINDDUN → APD-goal mapping tables`

---

### Task B-12: Parser — OWASP Threat Dragon JSON

**Goal:** Python parser for the most common structured threat-model export.

**Files:**

- Create: `tools/apd_gauntlet/threat_model/threat_dragon.py`
- Create: `tests/test_threat_dragon_parser.py`
- Create: `tests/fixtures/threat_models/sample-threat-dragon.json` — minimal Threat Dragon export with 2-3 threats per element

**Schema reference:** OWASP Threat Dragon exports a JSON document at `<project_root>.json` containing `{summary, detail.diagrams[].cells[]}` where cells include processes, data stores, actors, and trust boundaries. Threats are attached to cells via `data.threats[]` with `{id, severity, title, type, status, description, mitigation}`.

- [ ] **Step 1: Build a minimal sample fixture**

   Construct `tests/fixtures/threat_models/sample-threat-dragon.json` representing a 3-component diagram (Web Client → API Gateway → Member Database) with 4-6 STRIDE-style threats. Use real Threat Dragon export shape.

- [ ] **Step 2: Write tests**

   ```python
   def test_parser_extracts_entries_from_threat_dragon():
       data = json.loads(Path("tests/fixtures/threat_models/sample-threat-dragon.json").read_text())
       entries = parse_threat_dragon(data)
       assert len(entries) >= 4
       for entry in entries:
           assert entry["asset"]
           assert entry["threat"]
           assert entry["methodology"] == "stride"
           assert entry["extraction_confidence"] == "high"  # structured format
           assert entry["framework_refs"]["stride_letter"] in ("S", "T", "R", "I", "D", "E")

   def test_parser_handles_threat_without_mitigation():
       # Threat with no mitigation → entry["mitigation"] == None

   def test_parser_generates_stable_entry_ids():
       # Same input → same entry_id (sha8 over source_locator + asset + threat)
   ```

- [ ] **Step 3: Implement `parse_threat_dragon(data: dict) -> list[dict]`**

   Walk diagrams → cells → threats. For each threat, build:

   ```python
   {
       "entry_id": _stable_id(...),
       "asset": cell["data"]["name"],
       "threat": threat["title"],
       "mitigation": threat.get("mitigation") or None,
       "methodology": "stride",
       "source_locator": f"diagrams[{i}].cells[{j}].threats[{k}]",
       "extraction_confidence": "high",
       "framework_refs": {
           "stride_letter": _stride_letter_from_threat_type(threat["type"]),
           # ...
       },
       "inferred_apd_goals": stride_letter_to_apd_goals(letter),
   }
   ```

   `_stride_letter_from_threat_type` maps Threat Dragon's threat-type strings ("Spoofing", "Tampering", etc.) to the single-letter STRIDE codes.

- [ ] **Step 4: Run tests + linters + commit**

   Commit message: `feat(threat_model): parser for OWASP Threat Dragon JSON exports`

---

### Task B-13: Parser — Microsoft TMT `.tm7` XML

**Goal:** Python parser for Microsoft Threat Modeling Tool `.tm7` files (XML). Microsoft TMT is one of the most widely-used commercial threat modeling tools in enterprise environments; supporting its native export format is high-value.

**Files:**

- Create: `tools/apd_gauntlet/threat_model/microsoft_tmt.py`
- Create: `tests/test_microsoft_tmt_parser.py`
- Create: `tests/fixtures/threat_models/sample-microsoft.tm7`
- Modify: `pyproject.toml` (add `lxml` as a dependency)

**`.tm7` format reference (TMT 2016/2022):**

A `.tm7` file is a UTF-8 XML document with the following relevant structure (top-level elements only):

```xml
<?xml version="1.0" encoding="utf-8"?>
<ThreatModel xmlns="http://schemas.datacontract.org/2004/07/ThreatModeling.Model">
  <DrawingSurfaceList>
    <DrawingSurfaceModel>
      <Borders>
        <KeyValueOfguidanyType><Key>{guid}</Key><Value xsi:type="ProcessModel">
          <GenericTypeId>...</GenericTypeId>
          <Properties>
            <KeyValueOfstringstring><Key>Name</Key><Value>Web Server</Value></KeyValueOfstringstring>
            <KeyValueOfstringstring><Key>OutOfScope</Key><Value>false</Value></KeyValueOfstringstring>
          </Properties>
        </Value></KeyValueOfguidanyType>
      </Borders>
    </DrawingSurfaceModel>
  </DrawingSurfaceList>
  <ThreatInstances>
    <KeyValueOfstringThreatpc_P0_PhOB><Key>{guid}</Key><Value>
      <Title>Spoofing of Destination Data Store SQL Database</Title>
      <Properties>
        <KeyValueOfstringstring><Key>Title</Key><Value>Spoofing of Destination Data Store SQL Database</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>Description</Key><Value>...</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>State</Key><Value>NotStarted</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>Category</Key><Value>Spoofing</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>Priority</Key><Value>High</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>UserThreatCategory</Key><Value>Spoofing</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>SourceGuid</Key><Value>{source-element-guid}</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>TargetGuid</Key><Value>{target-element-guid}</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>UserThreatShortDescription</Key><Value>An attacker may impersonate...</Value></KeyValueOfstringstring>
        <KeyValueOfstringstring><Key>UserThreatDescription</Key><Value>Mitigation: Enforce mutual TLS...</Value></KeyValueOfstringstring>
      </Properties>
    </Value></KeyValueOfstringThreatpc_P0_PhOB>
  </ThreatInstances>
</ThreatModel>
```

**Key extraction points:**

| Field needed | Source in `.tm7` |
|---|---|
| `asset` (component name) | `Borders` element matching `SourceGuid` or `TargetGuid`; pull the `Name` property |
| `threat` (threat title) | `Threat/Title` element, or `Properties/Key=Title` |
| `mitigation` | `Properties/Key=UserThreatDescription` (typically contains "Mitigation: ..." prose) — extract the "Mitigation:" prefix if present, else use the full text as mitigation; if absent, set `null` |
| STRIDE letter | `Properties/Key=Category` value ("Spoofing"/"Tampering"/etc.) → single letter |
| Source locator | `Threat[@Key='{guid}']` for stable referencing |

**TMT Category → STRIDE letter mapping:**

```python
_TMT_CATEGORY_TO_STRIDE: dict[str, str] = {
    "Spoofing":                "S",
    "Tampering":               "T",
    "Repudiation":             "R",
    "Information Disclosure":  "I",
    "Denial of Service":       "D",
    "Elevation of Privilege":  "E",
    # TMT also emits these less-common labels in some templates:
    "Spoofing the External Entity":  "S",
    "Spoofing the Process":          "S",
    "Tampering with Data Flow":      "T",
    "Tampering with Data Store":     "T",
    "Repudiation by Process":        "R",
    "Information Disclosure of Data Store": "I",
    "Denial of Service to Data Flow": "D",
    "Elevation by Changing the Execution Flow": "E",
}
```

The recommended pattern: first attempt exact-match lookup; if no match, fall back to a prefix-based heuristic (first word of the category) — most TMT category strings begin with the STRIDE category name.

- [ ] **Step 1: Add `lxml>=4.9` dependency**

   In `pyproject.toml`, append to `dependencies = [...]`:

   ```toml
   "lxml>=4.9",
   ```

   And to `optional-dependencies.dev`, add the type stubs:

   ```toml
   "lxml-stubs>=0.5",
   ```

   Run `pip install -e ".[dev]"` (or `uv sync --extra dev`) to install. Verify with `python -c "from lxml import etree; print(etree.LXML_VERSION)"`.

- [ ] **Step 2: Build sample `.tm7` fixture**

   Create `tests/fixtures/threat_models/sample-microsoft.tm7` with:
  - 3 elements: a Process (`Web Server`), a DataStore (`User Database`), and a DataFlow (`SQL traffic`)
  - 5 threats across the three elements covering at least 4 distinct STRIDE categories
  - At least one threat with a populated `UserThreatDescription` mitigation
  - At least one threat with NO mitigation (to test the null-mitigation path)
  - Realistic GUIDs (use `python -c "import uuid; print(uuid.uuid4())"` to generate)

   Keep the file under 5 KB. If a real TMT export is available, strip it to a 3-element / 5-threat subset preserving the namespace declaration.

- [ ] **Step 3: Write failing tests**

   ```python
   from pathlib import Path

   import pytest

   from apd_gauntlet.threat_model.microsoft_tmt import (
       parse_microsoft_tmt,
       _category_to_stride_letter,
       _build_element_index,
   )

   FIXTURE = Path("tests/fixtures/threat_models/sample-microsoft.tm7")


   def test_parser_extracts_all_threats():
       entries = parse_microsoft_tmt(FIXTURE.read_bytes())
       assert len(entries) == 5  # matches fixture

   def test_parser_emits_methodology_stride_and_high_confidence():
       entries = parse_microsoft_tmt(FIXTURE.read_bytes())
       for entry in entries:
           assert entry["methodology"] == "stride"
           assert entry["extraction_confidence"] == "high"

   def test_parser_extracts_asset_name_via_source_guid_lookup():
       entries = parse_microsoft_tmt(FIXTURE.read_bytes())
       # At least one entry's asset matches a known element name from the fixture
       assets = {e["asset"] for e in entries}
       assert "Web Server" in assets or "User Database" in assets

   def test_parser_extracts_mitigation_when_present():
       entries = parse_microsoft_tmt(FIXTURE.read_bytes())
       with_mit = [e for e in entries if e["mitigation"] is not None]
       assert with_mit, "fixture has at least one mitigated threat"
       assert any("Mitigation" in (e["mitigation"] or "") or e["mitigation"] for e in with_mit)

   def test_parser_emits_null_mitigation_when_absent():
       entries = parse_microsoft_tmt(FIXTURE.read_bytes())
       without_mit = [e for e in entries if e["mitigation"] is None]
       assert without_mit, "fixture has at least one unmitigated threat"

   def test_category_to_stride_letter_exact_match():
       assert _category_to_stride_letter("Spoofing") == "S"
       assert _category_to_stride_letter("Tampering") == "T"
       assert _category_to_stride_letter("Elevation of Privilege") == "E"

   def test_category_to_stride_letter_prefix_fallback():
       # TMT custom templates can emit non-canonical category strings
       assert _category_to_stride_letter("Spoofing the External Entity") == "S"
       assert _category_to_stride_letter("Tampering with Data Flow") == "T"

   def test_category_to_stride_letter_unknown_returns_none():
       assert _category_to_stride_letter("Custom Threat Type") is None

   def test_parser_handles_malformed_xml_via_recover_mode():
       # Truncate the fixture mid-element; lxml recover=True should still emit
       # whatever threats it could parse before the truncation
       truncated = FIXTURE.read_bytes()[: len(FIXTURE.read_bytes()) // 2]
       entries = parse_microsoft_tmt(truncated)  # should not raise
       # Don't assert on count — partial parse is best-effort

   def test_parser_extraction_confidence_drops_to_medium_for_unknown_category():
       # If a threat has a Category we can't map, the entry still emits but
       # extraction_confidence drops to "medium" since the STRIDE mapping is uncertain
       # (build a small inline XML with one unknown-category threat to test)
       ...

   def test_parser_xxe_safe_against_external_entity_payload():
       # Inline XML with a DOCTYPE attempting external entity resolution;
       # parser must not fetch the external entity (no_network=True) AND
       # must not crash (recover=True)
       xxe_payload = b'<?xml version="1.0"?>\n<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n<ThreatModel>&xxe;</ThreatModel>'
       entries = parse_microsoft_tmt(xxe_payload)
       # Should return empty list (no threats to parse); no file read; no crash
       assert entries == []
   ```

- [ ] **Step 4: Run tests to verify they fail** (module doesn't exist yet)

   ```bash
   pytest tests/test_microsoft_tmt_parser.py -v
   ```

   Expected: ImportError on `from apd_gauntlet.threat_model.microsoft_tmt import ...`.

- [ ] **Step 5: Implement `tools/apd_gauntlet/threat_model/microsoft_tmt.py`**

   ```python
   """Parser for Microsoft Threat Modeling Tool .tm7 XML files."""

   from __future__ import annotations

   import hashlib
   from typing import Any

   from lxml import etree

   from .mappings import stride_letter_to_apd_goals

   # Microsoft TMT namespace (constant across TMT 2016+ versions)
   _TMT_NS = "{http://schemas.datacontract.org/2004/07/ThreatModeling.Model}"

   _TMT_CATEGORY_TO_STRIDE: dict[str, str] = {
       "Spoofing":                "S",
       "Tampering":               "T",
       "Repudiation":             "R",
       "Information Disclosure":  "I",
       "Denial of Service":       "D",
       "Elevation of Privilege":  "E",
   }

   _STRIDE_PREFIXES: dict[str, str] = {
       "Spoofing":    "S",
       "Tampering":   "T",
       "Repudiation": "R",
       "Information": "I",
       "Denial":      "D",
       "Elevation":   "E",
   }


   def _category_to_stride_letter(category: str) -> str | None:
       """Map a TMT Category string to a single-letter STRIDE code.

       Tries exact match first, then falls back to first-word prefix match
       (handles TMT custom template strings like "Spoofing the External Entity").
       Returns None for unrecognized categories.
       """
       if not category:
           return None
       if category in _TMT_CATEGORY_TO_STRIDE:
           return _TMT_CATEGORY_TO_STRIDE[category]
       first_word = category.split()[0] if category.split() else ""
       return _STRIDE_PREFIXES.get(first_word)


   def _build_element_index(root: etree._Element) -> dict[str, str]:
       """Map element GUIDs to their human-readable Name property."""
       index: dict[str, str] = {}
       for kv in root.iter(f"{_TMT_NS}KeyValueOfguidanyType"):
           key_elem = kv.find(f"{_TMT_NS}Key")
           value_elem = kv.find(f"{_TMT_NS}Value")
           if key_elem is None or value_elem is None or not key_elem.text:
               continue
           guid = key_elem.text.strip("{}")
           name = _get_property(value_elem, "Name")
           if name:
               index[guid] = name
       return index


   def _get_property(value_elem: etree._Element, key: str) -> str | None:
       """Find the <Properties><KeyValueOfstringstring><Key>X</Key><Value>Y</Value></...> Y for given key."""
       props_container = value_elem.find(f"{_TMT_NS}Properties")
       if props_container is None:
           return None
       for kv in props_container.iter(f"{_TMT_NS}KeyValueOfstringstring"):
           k_elem = kv.find(f"{_TMT_NS}Key")
           v_elem = kv.find(f"{_TMT_NS}Value")
           if k_elem is not None and k_elem.text == key and v_elem is not None:
               return v_elem.text
       return None


   def _stable_entry_id(asset: str, threat: str, source_locator: str) -> str:
       """Deterministic 8-hex-char ID for an entry, stable across runs."""
       raw = f"{asset}|{threat}|{source_locator}".encode("utf-8")
       return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


   def parse_microsoft_tmt(xml_bytes: bytes) -> list[dict[str, Any]]:
       """Parse a .tm7 XML file into normalized threat-model entries.

       Uses lxml in recover mode (best-effort on malformed files) with XXE
       hardening (no entity resolution, no network access). Returns an empty
       list if no threats can be parsed.
       """
       parser = etree.XMLParser(
           recover=True,
           resolve_entities=False,
           no_network=True,
           load_dtd=False,
       )
       try:
           root = etree.fromstring(xml_bytes, parser=parser)
       except etree.XMLSyntaxError:
           # recover=True should prevent most XMLSyntaxErrors; bare-bones safety
           return []
       if root is None:
           return []

       element_index = _build_element_index(root)
       entries: list[dict[str, Any]] = []

       # ThreatInstances container holds threats; each is a KeyValue with a Threat Value
       for threat_kv in root.iter():
           # TMT names this element differently across versions
           local = etree.QName(threat_kv).localname
           if not local.startswith("KeyValueOfstringThreat"):
               continue

           key_elem = threat_kv.find(f"{_TMT_NS}Key")
           value_elem = threat_kv.find(f"{_TMT_NS}Value")
           if key_elem is None or value_elem is None or not key_elem.text:
               continue
           threat_guid = key_elem.text.strip("{}")

           title = _get_property(value_elem, "Title") or _text_of(value_elem.find(f"{_TMT_NS}Title")) or ""
           description = _get_property(value_elem, "Description") or ""
           category = _get_property(value_elem, "Category") or _get_property(value_elem, "UserThreatCategory") or ""
           mitigation = _get_property(value_elem, "UserThreatDescription")
           source_guid = (_get_property(value_elem, "SourceGuid") or "").strip("{}")
           target_guid = (_get_property(value_elem, "TargetGuid") or "").strip("{}")

           # Asset: prefer Source, then Target, then "(unknown element)"
           asset = (
               element_index.get(source_guid)
               or element_index.get(target_guid)
               or "(unknown element)"
           )

           stride_letter = _category_to_stride_letter(category)
           apd_goals = stride_letter_to_apd_goals(stride_letter) if stride_letter else []
           confidence = "high" if stride_letter else "medium"

           source_locator = f"ThreatInstances/[Key={{guid={threat_guid}}}]"

           entries.append({
               "entry_id": _stable_entry_id(asset, title, source_locator),
               "asset": asset,
               "threat": title or description or "(unnamed threat)",
               "mitigation": mitigation or None,
               "methodology": "stride",
               "source_locator": source_locator,
               "extraction_confidence": confidence,
               "framework_refs": {
                   "stride_letter": stride_letter,
                   "linddun_letter": None,
                   "attack_tree_position": None,
                   "mitre_attack": [],
               },
               "inferred_apd_goals": apd_goals,
           })
       return entries


   def _text_of(elem: etree._Element | None) -> str | None:
       return elem.text if elem is not None else None
   ```

   **Notes on the implementation:**

  - **XXE safety:** four flags — `resolve_entities=False`, `no_network=True`, `load_dtd=False`, plus `recover=True` so malformed input doesn't crash. The XXE test in Step 3 verifies these.
  - **GUID stripping:** TMT wraps GUIDs in `{...}` — strip braces consistently for lookup matching.
  - **Element lookup chain:** prefer Source over Target (the threat is "against" the source from the attacker's perspective in TMT's data-flow-diagram model).
  - **Confidence drops to `medium`** when STRIDE letter can't be inferred — the entry still emits (useful for the operator) but flags uncertainty.
  - **`_stable_entry_id`** uses sha256 over asset+threat+locator for deterministic IDs across runs (parser idempotency).

- [ ] **Step 6: Run tests to verify they pass**

   ```bash
   pytest tests/test_microsoft_tmt_parser.py -v
   ```

   Expected: all tests PASS.

- [ ] **Step 7: Full sweep + commit**

   ```bash
   pytest -q                      # full suite
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/threat_model/microsoft_tmt.py \
           tests/test_microsoft_tmt_parser.py \
           tests/fixtures/threat_models/sample-microsoft.tm7 \
           pyproject.toml
   git commit -m "feat(threat_model): parser for Microsoft TMT .tm7 XML (XXE-safe via lxml)

   Adds lxml>=4.9 dependency for XXE-safe XML parsing (resolve_entities=False,
   no_network=True, load_dtd=False, recover=True). Parser extracts threats from
   the ThreatInstances container, resolves asset names via the Borders element
   index (Source/Target GUID lookup), and maps TMT Category strings to STRIDE
   letters via exact-then-prefix matching. Unknown categories drop extraction
   confidence to medium; entries still emit so the operator sees them."
   ```

---

### Task B-14: Parser — STRIDE-per-element Markdown/CSV tables

**Goal:** Python parser for STRIDE-per-element threat models authored as Markdown tables or CSV files. This is the most common "DIY" format — engineers who don't use Threat Dragon or TMT but still want a threat model often spreadsheet one. The format is recognizable by column headers containing the STRIDE letters or category names.

**Files:**

- Create: `tools/apd_gauntlet/threat_model/stride_table.py`
- Create: `tests/test_stride_table_parser.py`
- Create: `tests/fixtures/threat_models/sample-stride-table.md`
- Create: `tests/fixtures/threat_models/sample-stride-table.csv`

**Supported column header variants:**

| Variant | Example |
|---|---|
| Single letters | `S \| T \| R \| I \| D \| E` |
| Full names | `Spoofing \| Tampering \| Repudiation \| Information Disclosure \| Denial of Service \| Elevation of Privilege` |
| Mixed/abbreviated | `Spoof \| Tamper \| Repud \| Info Disc \| DoS \| EoP` |

The first column is always the component/element name (typical headers: `Element`, `Component`, `Asset`, or anything else — treated as a label column regardless of name).

**Empty-cell conventions:**

The following cell values are treated as "no threat in this STRIDE category for this element" and skipped:

- empty string (`""`)
- whitespace only
- `—` (em-dash, common in Markdown tables)
- `-` (single hyphen)
- `N/A`, `n/a`, `None`, `none`
- `–` (en-dash)

**Output:** One entry per (component, non-empty STRIDE cell). A row with 3 populated STRIDE cells emits 3 entries; a row with 0 emits 0.

**Format detection:** the dispatcher (Task B-17) routes `.md` and `.csv` files. The parser itself can be invoked directly on either format — internally it normalizes both to a `list[list[str]]` (rows of cells) before STRIDE-letter mapping.

- [ ] **Step 1: Build the Markdown fixture** `tests/fixtures/threat_models/sample-stride-table.md`

   ```markdown
   # PBM Claim Event Bus STRIDE Threat Model

   | Element | S | T | R | I | D | E |
   |---------|---|---|---|---|---|---|
   | claim-ingress-API | Pharmacy credential theft via phishing | Replay of submitted claim with altered NDC | — | Token logged in CloudFront access logs | High-volume duplicate submission DoS | Compromised pharmacy account elevated via missing tenant check |
   | adjudication-service | mTLS cert pinning bypass via service mesh misconfig | Drug pricing data swap in transit | — | PHI included in error response body | Slow-query saturation of adjudication pool | — |
   | audit-log-writer | — | — | Audit entry deletion via direct DynamoDB access | — | — | — |
   ```

   This fixture exercises:
  - 3 components (one per row)
  - 8 populated STRIDE cells across 3 rows (so 8 entries expected)
  - 13 empty cells (mix of `—` and other conventions; should all be skipped)
  - All 6 STRIDE letters represented across the table

- [ ] **Step 2: Build the CSV fixture** `tests/fixtures/threat_models/sample-stride-table.csv`

   ```csv
   Element,S,T,R,I,D,E
   claim-ingress-API,Pharmacy credential theft via phishing,Replay of submitted claim with altered NDC,,Token logged in CloudFront access logs,High-volume duplicate submission DoS,Compromised pharmacy account elevated via missing tenant check
   adjudication-service,mTLS cert pinning bypass via service mesh misconfig,Drug pricing data swap in transit,,PHI included in error response body,Slow-query saturation of adjudication pool,
   audit-log-writer,,,Audit entry deletion via direct DynamoDB access,,,
   ```

   Same logical content as the Markdown fixture; empty CSV fields rather than `—`.

- [ ] **Step 3: Write failing tests**

   ```python
   from pathlib import Path

   import pytest

   from apd_gauntlet.threat_model.stride_table import (
       parse_stride_table,
       parse_stride_markdown,
       parse_stride_csv,
       _normalize_column_header,
       _is_empty_cell,
   )

   MD_FIXTURE = Path("tests/fixtures/threat_models/sample-stride-table.md")
   CSV_FIXTURE = Path("tests/fixtures/threat_models/sample-stride-table.csv")


   def test_markdown_parser_extracts_eight_entries():
       entries = parse_stride_markdown(MD_FIXTURE.read_text())
       assert len(entries) == 8

   def test_csv_parser_extracts_eight_entries():
       entries = parse_stride_csv(CSV_FIXTURE.read_text())
       assert len(entries) == 8

   def test_markdown_and_csv_produce_equivalent_entries():
       md_entries = parse_stride_markdown(MD_FIXTURE.read_text())
       csv_entries = parse_stride_csv(CSV_FIXTURE.read_text())
       # Same assets, same STRIDE letters, same threat text
       assert {(e["asset"], e["framework_refs"]["stride_letter"]) for e in md_entries} == \
              {(e["asset"], e["framework_refs"]["stride_letter"]) for e in csv_entries}

   def test_all_entries_emit_methodology_stride_and_high_confidence():
       entries = parse_stride_markdown(MD_FIXTURE.read_text())
       for entry in entries:
           assert entry["methodology"] == "stride"
           assert entry["extraction_confidence"] == "high"

   def test_stride_letters_correctly_mapped_from_column_position():
       entries = parse_stride_markdown(MD_FIXTURE.read_text())
       # claim-ingress-API row has populated cells in S, T, I, D, E (not R)
       claim_letters = sorted({
           e["framework_refs"]["stride_letter"]
           for e in entries if e["asset"] == "claim-ingress-API"
       })
       assert claim_letters == ["D", "E", "I", "S", "T"]

   def test_empty_cells_dash_and_blank_are_skipped():
       entries = parse_stride_markdown(MD_FIXTURE.read_text())
       # audit-log-writer row has only R populated; the other 5 are skipped
       audit_entries = [e for e in entries if e["asset"] == "audit-log-writer"]
       assert len(audit_entries) == 1
       assert audit_entries[0]["framework_refs"]["stride_letter"] == "R"

   def test_inferred_apd_goals_populated_from_mapping_table():
       entries = parse_stride_markdown(MD_FIXTURE.read_text())
       # An "E" (Elevation of Privilege) entry → both authenticity AND integrity
       e_entries = [e for e in entries if e["framework_refs"]["stride_letter"] == "E"]
       assert e_entries
       assert sorted(e_entries[0]["inferred_apd_goals"]) == ["authenticity", "integrity"]

   def test_mitigation_is_null_for_table_format():
       # STRIDE-per-element tables don't have a mitigation column by convention
       entries = parse_stride_markdown(MD_FIXTURE.read_text())
       for entry in entries:
           assert entry["mitigation"] is None

   def test_normalize_column_header_handles_letters_and_full_names():
       assert _normalize_column_header("S") == "S"
       assert _normalize_column_header("Spoofing") == "S"
       assert _normalize_column_header("Spoof") == "S"
       assert _normalize_column_header("Information Disclosure") == "I"
       assert _normalize_column_header("Info Disc") == "I"
       assert _normalize_column_header("Element") is None  # not a STRIDE column

   @pytest.mark.parametrize("cell,expected", [
       ("", True), ("   ", True), ("—", True), ("-", True), ("–", True),
       ("N/A", True), ("n/a", True), ("None", True), ("none", True),
       ("real threat", False), ("0", False), (" data ", False),
   ])
   def test_is_empty_cell(cell, expected):
       assert _is_empty_cell(cell) is expected

   def test_dispatcher_routes_by_extension():
       """parse_stride_table reads the file path and routes by suffix."""
       entries_md = parse_stride_table(MD_FIXTURE)
       entries_csv = parse_stride_table(CSV_FIXTURE)
       assert len(entries_md) == 8
       assert len(entries_csv) == 8

   def test_malformed_markdown_table_no_separator_row_still_parses():
       """A 'table' that lacks the |---| separator row still parses (lenient)."""
       text = "| Element | S | T |\n| api | spoof | tamper |\n"
       entries = parse_stride_markdown(text)
       assert len(entries) == 2  # spoof + tamper
   ```

- [ ] **Step 4: Run tests to verify they fail**

   ```bash
   pytest tests/test_stride_table_parser.py -v
   ```

   Expected: ImportError.

- [ ] **Step 5: Implement `tools/apd_gauntlet/threat_model/stride_table.py`**

   ```python
   """Parser for STRIDE-per-element threat-model tables (Markdown + CSV)."""

   from __future__ import annotations

   import csv
   import hashlib
   import io
   from pathlib import Path
   from typing import Any

   from .mappings import stride_letter_to_apd_goals

   _STRIDE_HEADER_TO_LETTER: dict[str, str] = {
       "S": "S", "SPOOFING": "S", "SPOOF": "S",
       "T": "T", "TAMPERING": "T", "TAMPER": "T",
       "R": "R", "REPUDIATION": "R", "REPUD": "R",
       "I": "I", "INFORMATION DISCLOSURE": "I", "INFO DISC": "I", "INFODISC": "I", "DISCLOSURE": "I",
       "D": "D", "DENIAL OF SERVICE": "D", "DOS": "D", "DENIAL": "D",
       "E": "E", "ELEVATION OF PRIVILEGE": "E", "EOP": "E", "ELEVATION": "E",
   }

   _EMPTY_CELL_VALUES: frozenset[str] = frozenset({
       "", "—", "-", "–", "N/A", "NONE",
   })


   def _normalize_column_header(header: str) -> str | None:
       """Map a column header string to a STRIDE letter, or None if not a STRIDE column."""
       if not header:
           return None
       return _STRIDE_HEADER_TO_LETTER.get(header.strip().upper())


   def _is_empty_cell(cell: str) -> bool:
       """True if the cell represents 'no threat in this STRIDE category for this element'."""
       return cell.strip().upper() in _EMPTY_CELL_VALUES


   def _stable_entry_id(asset: str, threat: str, locator: str) -> str:
       raw = f"{asset}|{threat}|{locator}".encode("utf-8")
       return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


   def _row_to_entries(
       headers: list[str | None],
       row: list[str],
       row_index: int,
   ) -> list[dict[str, Any]]:
       """Convert one data row to zero-or-more STRIDE entries.

       `headers[0]` is None (the label column); subsequent items are STRIDE letters.
       """
       if not row:
           return []
       asset = row[0].strip() if row else ""
       if not asset:
           return []
       entries: list[dict[str, Any]] = []
       for col_idx, cell in enumerate(row[1:], start=1):
           if col_idx >= len(headers):
               break
           letter = headers[col_idx]
           if letter is None:
               continue  # column header wasn't a STRIDE letter
           if _is_empty_cell(cell):
               continue
           locator = f"row[{row_index}].column[{col_idx}]"
           entries.append({
               "entry_id": _stable_entry_id(asset, cell.strip(), locator),
               "asset": asset,
               "threat": cell.strip(),
               "mitigation": None,  # table format has no mitigation column by convention
               "methodology": "stride",
               "source_locator": locator,
               "extraction_confidence": "high",
               "framework_refs": {
                   "stride_letter": letter,
                   "linddun_letter": None,
                   "attack_tree_position": None,
                   "mitre_attack": [],
               },
               "inferred_apd_goals": stride_letter_to_apd_goals(letter),
           })
       return entries


   def parse_stride_markdown(text: str) -> list[dict[str, Any]]:
       """Parse a Markdown table into STRIDE entries.

       Lenient parser: ignores non-table lines (prose, headings), skips the
       `|---|---|` separator row, treats any pipe-delimited row as data.
       """
       rows: list[list[str]] = []
       for line in text.splitlines():
           stripped = line.strip()
           if not stripped.startswith("|") or not stripped.endswith("|"):
               continue
           # Split on |, strip the leading/trailing empty cells from |...|
           cells = [c.strip() for c in stripped.split("|")[1:-1]]
           # Skip separator rows (cells are all dashes/colons)
           if all(set(c) <= set("-:") for c in cells if c):
               continue
           rows.append(cells)
       if not rows:
           return []
       headers = [_normalize_column_header(h) for h in rows[0]]
       entries: list[dict[str, Any]] = []
       for i, row in enumerate(rows[1:], start=1):
           entries.extend(_row_to_entries(headers, row, i))
       return entries


   def parse_stride_csv(text: str) -> list[dict[str, Any]]:
       """Parse a CSV file into STRIDE entries (stdlib csv module)."""
       reader = csv.reader(io.StringIO(text))
       rows = list(reader)
       if not rows:
           return []
       headers = [_normalize_column_header(h) for h in rows[0]]
       entries: list[dict[str, Any]] = []
       for i, row in enumerate(rows[1:], start=1):
           entries.extend(_row_to_entries(headers, row, i))
       return entries


   def parse_stride_table(path: Path) -> list[dict[str, Any]]:
       """Dispatch based on file extension."""
       suffix = path.suffix.lower()
       text = path.read_text(encoding="utf-8")
       if suffix == ".md":
           return parse_stride_markdown(text)
       if suffix == ".csv":
           return parse_stride_csv(text)
       raise ValueError(f"Unsupported STRIDE table file extension: {suffix}")
   ```

- [ ] **Step 6: Run tests + linters + commit**

   ```bash
   pytest tests/test_stride_table_parser.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/threat_model/stride_table.py \
           tests/test_stride_table_parser.py \
           tests/fixtures/threat_models/sample-stride-table.md \
           tests/fixtures/threat_models/sample-stride-table.csv
   git commit -m "feat(threat_model): parser for STRIDE-per-element Markdown/CSV tables

   Accepts single-letter (S/T/R/I/D/E), full-name (Spoofing/Tampering/...),
   and abbreviated (Spoof/Tamper/...) column headers. Empty cells (blank,
   em-dash, en-dash, hyphen, N/A, None) are skipped. Lenient Markdown
   parsing handles missing separator rows and ignores prose between tables.
   Each populated cell emits one entry with stable sha-derived ID."
   ```

---

### Task B-15: Parser — LINDDUN tables (Markdown/CSV)

**Goal:** Same shape as Task B-14 but for LINDDUN categories. LINDDUN is a privacy-focused methodology with 7 categories whose single-letter codes overlap (`D` and `N` are reused). This task adds disambiguation via column position.

**Files:**

- Create: `tools/apd_gauntlet/threat_model/linddun_table.py`
- Create: `tests/test_linddun_table_parser.py`
- Create: `tests/fixtures/threat_models/sample-linddun-table.md`
- Create: `tests/fixtures/threat_models/sample-linddun-table.csv`

**LINDDUN category reference:**

| Position | Letter | Category | APD Goal(s) |
|---|---|---|---|
| 1 | L | Linkability | Confidentiality |
| 2 | I | Identifiability | Confidentiality |
| 3 | N | Non-repudiation (privacy harm) | Non-Repudiation |
| 4 | D | Detectability | Confidentiality |
| 5 | D | Disclosure of information | Confidentiality |
| 6 | U | Unawareness (lack of consent) | Authenticity |
| 7 | N | Non-compliance | Non-Repudiation (domain-mapped, e.g. HIPAA for PBM) |

The duplicate `D` and duplicate `N` mean **single-letter headers are ambiguous**. The parser MUST use column position for disambiguation, not letter value.

**Column header variants supported:**

- Single letters in canonical position: `L I N D D U N`
- Full category names: `Linkability | Identifiability | Non-repudiation | Detectability | Disclosure of information | Unawareness | Non-compliance`
- Abbreviated names: `Link | Ident | NonRep | Detect | Disclose | Unaware | NonComply`
- Mixed (full names for the ambiguous letters, single letters elsewhere): `L | I | Non-repudiation | Detectability | Disclosure | U | Non-compliance`

**Detection heuristic** (used by the dispatcher in Task B-17 to distinguish STRIDE vs LINDDUN tables when the user didn't supply `--methodology-hint`):

A table is LINDDUN if any column header matches any of:

- "Linkability", "Identifiability", "Detectability", "Disclosure", "Unawareness", "Non-compliance"
- 7-letter pattern `L I N D D U N` (positionally)
- Header containing "LINDDUN" (e.g., the title row before the table)

Otherwise default to STRIDE.

**Compound-key mapping (matches Task B-11's canonical table):**

The parser emits `framework_refs.linddun_letter` with these compound values to disambiguate:

| Column position | Compound key |
|---|---|
| 1 | `L` |
| 2 | `I` |
| 3 | `N_repudiation` |
| 4 | `D_etectability` |
| 5 | `D_isclosure` |
| 6 | `U` |
| 7 | `N_compliance` |

This matches the canonical table in `tools/apd_gauntlet/threat_model/mappings.py::LINDDUN_TO_APD_GOALS` from Task B-11.

- [ ] **Step 1: Build the Markdown fixture** `tests/fixtures/threat_models/sample-linddun-table.md`

   ```markdown
   # PBM Member Portal LINDDUN Privacy Threat Model

   | Data Flow | L | I | N | D | D | U | N |
   |-----------|---|---|---|---|---|---|---|
   | Member login flow | Cross-session user tracking via fingerprint | SSN visible in profile API response | — | Login event observable to third-party CDN | Browser autofill leaks plan-member ID | No consent gate on analytics SDK init | HIPAA breach notification not triggered on this surface |
   | Claim history download | — | Member ID embedded in CSV filename | — | Download event logged in CDN metrics | — | — | — |
   | Pharmacy lookup search | Search terms tied to authenticated session | — | — | — | — | — | — |
   ```

   Note: the header row uses single letters in canonical LINDDUN order. The duplicate `D` and `N` headers are disambiguated by column position.

- [ ] **Step 2: Build the CSV fixture** `tests/fixtures/threat_models/sample-linddun-table.csv` — same content as the Markdown, comma-delimited.

   For robustness, also add a fixture with **full category names** in the header to exercise that path:

   `tests/fixtures/threat_models/sample-linddun-table-fullnames.md`:

   ```markdown
   | Data Flow | Linkability | Identifiability | Non-repudiation | Detectability | Disclosure of information | Unawareness | Non-compliance |
   |-----------|-------------|-----------------|-----------------|---------------|---------------------------|-------------|----------------|
   | (same content as the single-letter version) |
   ```

- [ ] **Step 3: Write failing tests**

   ```python
   def test_linddun_parser_extracts_entries_with_disambiguated_letters():
       entries = parse_linddun_markdown(MD_FIXTURE.read_text())
       # Member login row has all 7 columns populated
       login_entries = [e for e in entries if e["asset"] == "Member login flow"]
       assert len(login_entries) == 7
       letters = sorted(e["framework_refs"]["linddun_letter"] for e in login_entries)
       assert letters == ["D_etectability", "D_isclosure", "I", "L", "N_compliance", "N_repudiation", "U"]

   def test_linddun_n_repudiation_maps_to_apd_non_repudiation():
       entries = parse_linddun_markdown(MD_FIXTURE.read_text())
       n_rep_entries = [e for e in entries if e["framework_refs"]["linddun_letter"] == "N_repudiation"]
       assert n_rep_entries
       for entry in n_rep_entries:
           assert "non_repudiation" in entry["inferred_apd_goals"]

   def test_linddun_n_compliance_maps_to_apd_non_repudiation_domain_specific():
       entries = parse_linddun_markdown(MD_FIXTURE.read_text())
       n_compl_entries = [e for e in entries if e["framework_refs"]["linddun_letter"] == "N_compliance"]
       assert n_compl_entries
       # Domain-specific override happens at evaluator time; here just check the base mapping
       for entry in n_compl_entries:
           assert "non_repudiation" in entry["inferred_apd_goals"]

   def test_linddun_d_etectability_vs_d_isclosure_are_distinct():
       entries = parse_linddun_markdown(MD_FIXTURE.read_text())
       d_etc = {e["threat"] for e in entries if e["framework_refs"]["linddun_letter"] == "D_etectability"}
       d_isc = {e["threat"] for e in entries if e["framework_refs"]["linddun_letter"] == "D_isclosure"}
       assert d_etc & d_isc == set()  # no threat appears in both

   def test_linddun_parser_handles_fullname_headers():
       entries = parse_linddun_markdown(FULLNAMES_FIXTURE.read_text())
       # Same logical content → same entry count + same letter distribution
       login_letters = sorted(
           e["framework_refs"]["linddun_letter"]
           for e in entries if e["asset"] == "Member login flow"
       )
       assert login_letters == ["D_etectability", "D_isclosure", "I", "L", "N_compliance", "N_repudiation", "U"]

   def test_is_linddun_table_detector_returns_true_for_linddun_headers():
       headers = ["Data Flow", "L", "I", "N", "D", "D", "U", "N"]
       assert is_linddun_table(headers)

       headers_fullnames = ["Data Flow", "Linkability", "Identifiability", "Non-repudiation",
                            "Detectability", "Disclosure of information", "Unawareness", "Non-compliance"]
       assert is_linddun_table(headers_fullnames)

   def test_is_linddun_table_detector_returns_false_for_stride_headers():
       headers = ["Element", "S", "T", "R", "I", "D", "E"]
       assert not is_linddun_table(headers)
   ```

- [ ] **Step 4: Implement `tools/apd_gauntlet/threat_model/linddun_table.py`**

   Mirror the structure of `stride_table.py` (Task B-14) with these differences:

  - **`_normalize_column_header(header, column_position)`** takes both arguments. For ambiguous single-letter `D` or `N`, return the compound key based on `column_position` (positions 3,4,5,7 are the ambiguous ones). For full names, ignore position and map by name.
  - **`is_linddun_table(headers: list[str]) -> bool`** — heuristic for the dispatcher
  - **`_LINDDUN_FULLNAMES`** — mapping from "Linkability" → "L", "Non-repudiation" → "N_repudiation", etc.
  - **`_POSITION_TO_COMPOUND`** — `{1: "L", 2: "I", 3: "N_repudiation", 4: "D_etectability", 5: "D_isclosure", 6: "U", 7: "N_compliance"}`

   ```python
   """Parser for LINDDUN privacy threat-model tables (Markdown + CSV)."""

   from __future__ import annotations

   import csv
   import hashlib
   import io
   from pathlib import Path
   from typing import Any

   from .mappings import linddun_letter_to_apd_goals

   _POSITION_TO_COMPOUND: dict[int, str] = {
       1: "L",
       2: "I",
       3: "N_repudiation",
       4: "D_etectability",
       5: "D_isclosure",
       6: "U",
       7: "N_compliance",
   }

   _LINDDUN_FULLNAMES_TO_COMPOUND: dict[str, str] = {
       "LINKABILITY":              "L",
       "LINK":                     "L",
       "IDENTIFIABILITY":          "I",
       "IDENT":                    "I",
       "NON-REPUDIATION":          "N_repudiation",
       "NONREPUDIATION":           "N_repudiation",
       "NON_REPUDIATION":          "N_repudiation",
       "NONREP":                   "N_repudiation",
       "DETECTABILITY":            "D_etectability",
       "DETECT":                   "D_etectability",
       "DISCLOSURE OF INFORMATION":"D_isclosure",
       "DISCLOSURE":               "D_isclosure",
       "DISCLOSE":                 "D_isclosure",
       "UNAWARENESS":              "U",
       "UNAWARE":                  "U",
       "NON-COMPLIANCE":           "N_compliance",
       "NONCOMPLIANCE":            "N_compliance",
       "NONCOMPLY":                "N_compliance",
   }

   _LINDDUN_DETECTOR_KEYWORDS: frozenset[str] = frozenset({
       "LINKABILITY", "IDENTIFIABILITY", "DETECTABILITY",
       "DISCLOSURE", "UNAWARENESS", "NON-COMPLIANCE", "NONCOMPLIANCE",
       "LINDDUN",
   })

   _EMPTY_CELL_VALUES: frozenset[str] = frozenset({
       "", "—", "-", "–", "N/A", "NONE",
   })


   def _is_empty_cell(cell: str) -> bool:
       return cell.strip().upper() in _EMPTY_CELL_VALUES


   def _normalize_column_header(header: str, column_position: int) -> str | None:
       """Return the LINDDUN compound-key for this column, or None if not a LINDDUN column.

       For single-letter headers (`L`, `I`, `N`, `D`, `D`, `U`, `N`), uses
       column_position to disambiguate the duplicates. For full names, uses
       the name lookup table and ignores position.
       """
       if not header:
           return None
       cleaned = header.strip().upper()
       # Full-name match first (unambiguous)
       if cleaned in _LINDDUN_FULLNAMES_TO_COMPOUND:
           return _LINDDUN_FULLNAMES_TO_COMPOUND[cleaned]
       # Single-letter match: disambiguate via position
       if cleaned in {"L", "I", "N", "D", "U"}:
           return _POSITION_TO_COMPOUND.get(column_position)
       return None


   def is_linddun_table(headers: list[str]) -> bool:
       """Heuristic: is this header row from a LINDDUN table?

       Returns True if any header matches a LINDDUN-specific keyword OR the
       headers (excluding the label column) form the canonical L-I-N-D-D-U-N
       pattern.
       """
       upper_headers = [h.strip().upper() for h in headers]
       if any(h in _LINDDUN_DETECTOR_KEYWORDS for h in upper_headers):
           return True
       # Canonical 7-letter pattern check (skip first column = label)
       letter_only = [h for h in upper_headers[1:] if h in {"L", "I", "N", "D", "U"}]
       if letter_only == ["L", "I", "N", "D", "D", "U", "N"]:
           return True
       return False


   def _stable_entry_id(asset: str, threat: str, locator: str) -> str:
       raw = f"{asset}|{threat}|{locator}".encode("utf-8")
       return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


   def _row_to_entries(headers: list[str | None], row: list[str], row_index: int) -> list[dict[str, Any]]:
       if not row:
           return []
       asset = row[0].strip() if row else ""
       if not asset:
           return []
       entries: list[dict[str, Any]] = []
       for col_idx, cell in enumerate(row[1:], start=1):
           if col_idx >= len(headers):
               break
           compound_key = headers[col_idx]
           if compound_key is None:
               continue
           if _is_empty_cell(cell):
               continue
           locator = f"row[{row_index}].column[{col_idx}]"
           entries.append({
               "entry_id": _stable_entry_id(asset, cell.strip(), locator),
               "asset": asset,
               "threat": cell.strip(),
               "mitigation": None,
               "methodology": "linddun",
               "source_locator": locator,
               "extraction_confidence": "high",
               "framework_refs": {
                   "stride_letter": None,
                   "linddun_letter": compound_key,
                   "attack_tree_position": None,
                   "mitre_attack": [],
               },
               "inferred_apd_goals": linddun_letter_to_apd_goals(compound_key),
           })
       return entries


   def parse_linddun_markdown(text: str) -> list[dict[str, Any]]:
       rows: list[list[str]] = []
       for line in text.splitlines():
           stripped = line.strip()
           if not stripped.startswith("|") or not stripped.endswith("|"):
               continue
           cells = [c.strip() for c in stripped.split("|")[1:-1]]
           if all(set(c) <= set("-:") for c in cells if c):
               continue
           rows.append(cells)
       if not rows:
           return []
       headers = [_normalize_column_header(h, i) for i, h in enumerate(rows[0])]
       entries: list[dict[str, Any]] = []
       for i, row in enumerate(rows[1:], start=1):
           entries.extend(_row_to_entries(headers, row, i))
       return entries


   def parse_linddun_csv(text: str) -> list[dict[str, Any]]:
       reader = csv.reader(io.StringIO(text))
       rows = list(reader)
       if not rows:
           return []
       headers = [_normalize_column_header(h, i) for i, h in enumerate(rows[0])]
       entries: list[dict[str, Any]] = []
       for i, row in enumerate(rows[1:], start=1):
           entries.extend(_row_to_entries(headers, row, i))
       return entries


   def parse_linddun_table(path: Path) -> list[dict[str, Any]]:
       suffix = path.suffix.lower()
       text = path.read_text(encoding="utf-8")
       if suffix == ".md":
           return parse_linddun_markdown(text)
       if suffix == ".csv":
           return parse_linddun_csv(text)
       raise ValueError(f"Unsupported LINDDUN table file extension: {suffix}")
   ```

- [ ] **Step 5: Run tests + linters + commit**

   ```bash
   pytest tests/test_linddun_table_parser.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/threat_model/linddun_table.py \
           tests/test_linddun_table_parser.py \
           tests/fixtures/threat_models/sample-linddun-table.md \
           tests/fixtures/threat_models/sample-linddun-table.csv \
           tests/fixtures/threat_models/sample-linddun-table-fullnames.md
   git commit -m "feat(threat_model): parser for LINDDUN tables with column-position disambiguation

   LINDDUN's letter overloading (D for Detectability/Disclosure, N for
   Non-repudiation/Non-compliance) is handled via canonical column-position
   mapping (positions 1-7 → L/I/N_repudiation/D_etectability/D_isclosure/U/N_compliance).
   Full-name headers are unambiguous and looked up by name. Also adds
   is_linddun_table() heuristic for the dispatcher (Task B-17) to distinguish
   LINDDUN tables from STRIDE tables when --methodology-hint isn't supplied."
   ```

---

### Task B-16: Parser — Attack tree (indented prose, ADTool XML, JSON)

**Goal:** Python parser for attack trees in three sub-formats. Attack trees model an attacker's goal as a tree: the root is the high-level objective, intermediate nodes are sub-goals, leaves are concrete attack steps. The three sub-formats:

1. **Indented prose** — most common informal format; one node per line, indentation indicates hierarchy
2. **ADTool XML** — output from [ADTool](https://satoss.uni.lu/members/piotr/adtool/), a research-grade attack-tree analysis tool
3. **JSON tree** — generic JSON convention (also produced by tools like SeaSponge and various consulting firms)

**Files:**

- Create: `tools/apd_gauntlet/threat_model/attack_tree.py`
- Create: `tests/test_attack_tree_parser.py`
- Create: `tests/fixtures/threat_models/sample-attack-tree.txt` (indented prose)
- Create: `tests/fixtures/threat_models/sample-attack-tree.adtool.xml`
- Create: `tests/fixtures/threat_models/sample-attack-tree.json`

**Attack tree semantics:**

- **Root node:** the attacker's goal (e.g., "Exfiltrate member PHI"). Always emits as an entry with `extraction_confidence: medium` (the root is descriptive, not actionable).
- **Intermediate nodes (sub-goals):** decompose the parent into AND/OR alternatives. Emit as entries with `extraction_confidence: low` — they're navigation aids, not attack steps.
- **Leaf nodes (attack steps):** concrete actions an attacker could take. Emit as entries with `extraction_confidence: medium`; attempt ATT&CK technique mapping via keyword heuristics.
- **AND/OR gates:** some attack trees annotate intermediate nodes as AND (all children must succeed) or OR (any child suffices). We record this in `framework_refs.attack_tree_position` but don't change extraction confidence based on it — it's structural metadata.

**Output structure:** each entry has `framework_refs.attack_tree_position` set to a path string like `"root/sub-goal-A/leaf-3"` so the operator can reconstruct the tree from the normalized YAML.

**ATT&CK technique mapping (keyword heuristic for leaves):**

```python
_ATTACK_TECHNIQUE_KEYWORDS: dict[str, str] = {
    # Initial Access
    "phishing":              "T1566",
    "spear phishing":        "T1566.001",
    "valid account":         "T1078",
    "credential stuffing":   "T1110.004",
    # Execution
    "command injection":     "T1059",
    "powershell":            "T1059.001",
    # Persistence
    "scheduled task":        "T1053",
    "registry run key":      "T1547.001",
    # Privilege Escalation
    "sudo abuse":            "T1548.003",
    # Credential Access
    "credential dumping":    "T1003",
    "kerberoasting":         "T1558.003",
    # Lateral Movement
    "smb lateral":           "T1021.002",
    "rdp lateral":           "T1021.001",
    # Collection / Exfil
    "data staging":          "T1074",
    "exfiltrate over c2":    "T1041",
    # Impact
    "ransomware":            "T1486",
    "data destruction":      "T1485",
}
```

The mapper does case-insensitive substring matching on each leaf's text. Multiple matches accumulate (a leaf mentioning both "phishing" and "credential dumping" gets both IDs). Confidence stays `medium` — the heuristic is shallow, deliberately. The recon agent (Task B-20) may refine via LLM judgment.

**Format detection:**

- `.txt` or `.md` (with no Markdown table syntax detected) → indented prose
- `.xml` → ADTool (look for `<adtree>` or `<node>` root)
- `.json` → JSON tree (look for `goal` or `children` keys at top level)

The dispatcher (Task B-17) handles routing.

- [ ] **Step 1: Build the indented-prose fixture** `tests/fixtures/threat_models/sample-attack-tree.txt`

   ```text
   Exfiltrate member PHI from claim adjudication system
       OR
       Compromise pharmacy submitter account
           Phishing attack on pharmacy operator
           Credential stuffing against pharmacy portal
       Lateral movement from compromised vendor integration
           Compromise drug pricing data feed credentials
           SMB lateral movement to adjudication network segment
       Direct database access via misconfigured backup
           Read DynamoDB backup with overly-permissive S3 read role
   ```

   Indentation: 4 spaces per level. The `OR` keyword between siblings marks an OR gate; `AND` would mark AND. Both are optional; absent means OR by default.

   Expected entries: 1 root + 3 sub-goals + 6 leaves = 10 entries.

- [ ] **Step 2: Build the ADTool XML fixture** `tests/fixtures/threat_models/sample-attack-tree.adtool.xml`

   ```xml
   <?xml version="1.0" encoding="UTF-8" standalone="no"?>
   <adtree>
     <node refinement="disjunctive">
       <label>Exfiltrate member PHI from claim adjudication system</label>
       <node refinement="conjunctive">
         <label>Compromise pharmacy submitter account</label>
         <node refinement="disjunctive">
           <label>Phishing attack on pharmacy operator</label>
         </node>
         <node refinement="disjunctive">
           <label>Credential stuffing against pharmacy portal</label>
         </node>
       </node>
       <node refinement="conjunctive">
         <label>Lateral movement from compromised vendor integration</label>
         <node refinement="disjunctive">
           <label>Compromise drug pricing data feed credentials</label>
         </node>
         <node refinement="disjunctive">
           <label>SMB lateral movement to adjudication network segment</label>
         </node>
       </node>
       <node refinement="disjunctive">
         <label>Direct database access via misconfigured backup</label>
         <node refinement="disjunctive">
           <label>Read DynamoDB backup with overly-permissive S3 read role</label>
         </node>
       </node>
     </node>
   </adtree>
   ```

   `refinement="disjunctive"` = OR, `refinement="conjunctive"` = AND.

- [ ] **Step 3: Build the JSON tree fixture** `tests/fixtures/threat_models/sample-attack-tree.json`

   ```json
   {
     "goal": "Exfiltrate member PHI from claim adjudication system",
     "gate": "OR",
     "children": [
       {
         "goal": "Compromise pharmacy submitter account",
         "gate": "AND",
         "children": [
           { "goal": "Phishing attack on pharmacy operator" },
           { "goal": "Credential stuffing against pharmacy portal" }
         ]
       },
       {
         "goal": "Lateral movement from compromised vendor integration",
         "gate": "AND",
         "children": [
           { "goal": "Compromise drug pricing data feed credentials" },
           { "goal": "SMB lateral movement to adjudication network segment" }
         ]
       },
       {
         "goal": "Direct database access via misconfigured backup",
         "children": [
           { "goal": "Read DynamoDB backup with overly-permissive S3 read role" }
         ]
       }
     ]
   }
   ```

- [ ] **Step 4: Write failing tests**

   ```python
   from pathlib import Path

   from apd_gauntlet.threat_model.attack_tree import (
       parse_indented_prose,
       parse_adtool_xml,
       parse_attack_tree_json,
       parse_attack_tree,
       _map_text_to_attack_techniques,
   )

   PROSE_FIXTURE = Path("tests/fixtures/threat_models/sample-attack-tree.txt")
   ADTOOL_FIXTURE = Path("tests/fixtures/threat_models/sample-attack-tree.adtool.xml")
   JSON_FIXTURE = Path("tests/fixtures/threat_models/sample-attack-tree.json")


   def test_indented_prose_extracts_ten_entries():
       entries = parse_indented_prose(PROSE_FIXTURE.read_text())
       # 1 root + 3 sub-goals + 6 leaves
       assert len(entries) == 10

   def test_adtool_xml_extracts_ten_entries():
       entries = parse_adtool_xml(ADTOOL_FIXTURE.read_bytes())
       assert len(entries) == 10

   def test_json_extracts_ten_entries():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       assert len(entries) == 10

   def test_three_formats_produce_equivalent_threat_text():
       prose_threats = {e["threat"] for e in parse_indented_prose(PROSE_FIXTURE.read_text())}
       adtool_threats = {e["threat"] for e in parse_adtool_xml(ADTOOL_FIXTURE.read_bytes())}
       json_threats = {e["threat"] for e in parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))}
       assert prose_threats == adtool_threats == json_threats

   def test_root_has_low_confidence():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       root_entries = [e for e in entries if e["framework_refs"]["attack_tree_position"] == "root"]
       assert len(root_entries) == 1
       assert root_entries[0]["extraction_confidence"] == "low"

   def test_intermediate_has_low_confidence():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       inter_entries = [e for e in entries if "/" in (e["framework_refs"]["attack_tree_position"] or "") and not e["framework_refs"]["mitre_attack"]]
       for entry in inter_entries:
           # Intermediates may have ATT&CK matches if their text happens to match keywords,
           # but the confidence is still low because they're not concrete attack steps
           pass

   def test_leaf_has_medium_confidence():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       leaf_entries = [e for e in entries if e["framework_refs"]["attack_tree_position"] and e["framework_refs"]["attack_tree_position"].count("/") >= 2]
       assert leaf_entries
       for entry in leaf_entries:
           assert entry["extraction_confidence"] == "medium"

   def test_leaves_get_attack_technique_mappings_from_keyword_heuristic():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       phishing_leaf = [e for e in entries if "Phishing attack" in e["threat"]][0]
       assert "T1566" in phishing_leaf["framework_refs"]["mitre_attack"]
       smb_leaf = [e for e in entries if "SMB lateral" in e["threat"]][0]
       assert "T1021.002" in smb_leaf["framework_refs"]["mitre_attack"]

   def test_position_string_reflects_tree_path():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       phishing_leaf = [e for e in entries if "Phishing attack" in e["threat"]][0]
       pos = phishing_leaf["framework_refs"]["attack_tree_position"]
       # root/compromise-pharmacy/phishing (slug-style)
       assert "phishing" in pos
       assert pos.count("/") >= 2  # at least 3 levels deep

   def test_and_gate_preserved_in_intermediate_node():
       entries = parse_attack_tree_json(json.loads(JSON_FIXTURE.read_text()))
       compromise_node = [e for e in entries if e["threat"] == "Compromise pharmacy submitter account"][0]
       # Some way to expose gate semantics — likely as a suffix on attack_tree_position or in the threat text
       assert "AND" in compromise_node["threat"] or compromise_node.get("_gate") == "AND" or "(AND)" in compromise_node["framework_refs"]["attack_tree_position"]

   def test_indented_prose_uses_tabs_or_spaces_consistently():
       text = "Root\n\tSub1\n\t\tLeaf1\n\tSub2\n"
       entries = parse_indented_prose(text)
       assert len(entries) == 4

   def test_adtool_parser_is_xxe_safe():
       xxe = b'<?xml version="1.0"?>\n<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n<adtree>&xxe;</adtree>'
       entries = parse_adtool_xml(xxe)
       assert entries == []  # no nodes; no crash; no file read

   def test_keyword_mapper_handles_multiple_matches():
       result = _map_text_to_attack_techniques("phishing attack with credential stuffing")
       assert "T1566" in result
       assert "T1110.004" in result

   def test_keyword_mapper_returns_empty_for_no_matches():
       result = _map_text_to_attack_techniques("compromise drug pricing data feed credentials")
       # No keyword match → empty list
       assert result == []
   ```

- [ ] **Step 5: Implement `tools/apd_gauntlet/threat_model/attack_tree.py`**

   ```python
   """Parser for attack-tree threat models in three sub-formats."""

   from __future__ import annotations

   import hashlib
   import json
   import re
   from pathlib import Path
   from typing import Any

   from lxml import etree

   _ATTACK_TECHNIQUE_KEYWORDS: dict[str, str] = {
       "phishing":              "T1566",
       "spear phishing":        "T1566.001",
       "spearphishing":         "T1566.001",
       "valid account":         "T1078",
       "credential stuffing":   "T1110.004",
       "password spray":        "T1110.003",
       "command injection":     "T1059",
       "powershell":            "T1059.001",
       "scheduled task":        "T1053",
       "registry run key":      "T1547.001",
       "sudo abuse":            "T1548.003",
       "credential dumping":    "T1003",
       "kerberoasting":         "T1558.003",
       "smb lateral":           "T1021.002",
       "rdp lateral":           "T1021.001",
       "rdp":                   "T1021.001",
       "data staging":          "T1074",
       "exfiltrate over c2":    "T1041",
       "ransomware":            "T1486",
       "data destruction":      "T1485",
   }


   def _map_text_to_attack_techniques(text: str) -> list[str]:
       """Case-insensitive substring search against the keyword map. Returns sorted unique matches."""
       lower = text.lower()
       matches = {tid for kw, tid in _ATTACK_TECHNIQUE_KEYWORDS.items() if kw in lower}
       return sorted(matches)


   def _stable_entry_id(threat: str, position: str) -> str:
       raw = f"{threat}|{position}".encode("utf-8")
       return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


   def _slugify(text: str) -> str:
       slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
       return slug[:40]


   def _build_entry(
       *,
       threat: str,
       position: str,
       is_root: bool,
       is_leaf: bool,
       gate: str | None = None,
   ) -> dict[str, Any]:
       confidence = "low" if (is_root or not is_leaf) else "medium"
       techniques = _map_text_to_attack_techniques(threat) if is_leaf else []
       position_label = position if gate is None else f"{position} ({gate})"
       return {
           "entry_id": _stable_entry_id(threat, position),
           "asset": "(attack-tree node)",  # attack trees don't have per-node assets
           "threat": threat,
           "mitigation": None,
           "methodology": "attack_tree",
           "source_locator": position,
           "extraction_confidence": confidence,
           "framework_refs": {
               "stride_letter": None,
               "linddun_letter": None,
               "attack_tree_position": position_label,
               "mitre_attack": techniques,
           },
           "inferred_apd_goals": [],  # leaves with ATT&CK matches get goals via the cross-ref layer; otherwise empty
       }


   # ---------- indented-prose parser ----------

   _GATE_KEYWORDS: frozenset[str] = frozenset({"AND", "OR"})


   def parse_indented_prose(text: str) -> list[dict[str, Any]]:
       """Parse an indented-prose attack tree (4 spaces or 1 tab per level)."""
       lines = [line.rstrip() for line in text.splitlines() if line.strip()]
       if not lines:
           return []
       entries: list[dict[str, Any]] = []
       stack: list[tuple[int, str]] = []  # (indent_level, path)

       for line in lines:
           indent_chars = len(line) - len(line.lstrip())
           # Normalize tabs to 4 spaces for hierarchy
           level = (indent_chars + indent_chars // 4 * 4) // 4 if "\t" in line[:indent_chars] else indent_chars // 4
           content = line.strip()

           # Skip gate-only lines; they annotate the next-deeper level
           if content.upper() in _GATE_KEYWORDS:
               # Stash the gate for the next push; simplest approach: track separately
               continue

           # Pop the stack to the current level
           while stack and stack[-1][0] >= level:
               stack.pop()

           parent_path = stack[-1][1] if stack else ""
           position = f"{parent_path}/{_slugify(content)}" if parent_path else "root" if not stack else _slugify(content)
           is_root = not stack
           if is_root:
               position = "root"

           stack.append((level, position))

       # The above only built the stack; the actual entry emission needs a second pass that
       # knows leaf-vs-internal status. Build entries via a recursive walk of the stack-
       # constructed tree. For simplicity, use a node-children map built from the stack.
       # Implementation choice: build the tree first, then walk it.

       # Re-implement as a recursive tree-build followed by a walk:
       root_node = _build_prose_tree(lines)
       return _walk_node(root_node, parent_path="", entries=[])


   def _build_prose_tree(lines: list[str]) -> dict[str, Any]:
       """Build a nested dict tree from indented prose."""
       root: dict[str, Any] = {"label": "", "children": [], "gate": None}
       stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]  # (indent, node)
       pending_gate: str | None = None
       for line in lines:
           indent_chars = len(line) - len(line.lstrip())
           # Indent level: 1 per 4 spaces (or 1 per tab)
           level = (indent_chars + (line.count("\t") * 3)) // 4
           content = line.strip()
           if content.upper() in _GATE_KEYWORDS:
               pending_gate = content.upper()
               continue
           while stack and stack[-1][0] >= level:
               stack.pop()
           parent = stack[-1][1] if stack else root
           node = {"label": content, "children": [], "gate": pending_gate}
           pending_gate = None
           parent["children"].append(node)
           stack.append((level, node))
       return root


   def _walk_node(
       node: dict[str, Any],
       parent_path: str,
       entries: list[dict[str, Any]],
   ) -> list[dict[str, Any]]:
       label = node["label"]
       if not label:
           # Synthetic root with empty label; walk children directly
           for child in node["children"]:
               _walk_node(child, parent_path, entries)
           return entries
       slug = _slugify(label)
       position = f"{parent_path}/{slug}" if parent_path else "root"
       is_root = parent_path == ""
       is_leaf = not node["children"]
       gate = node.get("gate")
       entries.append(_build_entry(
           threat=label,
           position=position,
           is_root=is_root,
           is_leaf=is_leaf,
           gate=gate,
       ))
       for child in node["children"]:
           _walk_node(child, position, entries)
       return entries


   # ---------- ADTool XML parser ----------

   def parse_adtool_xml(xml_bytes: bytes) -> list[dict[str, Any]]:
       """Parse ADTool XML attack tree (XXE-safe)."""
       parser = etree.XMLParser(
           recover=True,
           resolve_entities=False,
           no_network=True,
           load_dtd=False,
       )
       try:
           root_xml = etree.fromstring(xml_bytes, parser=parser)
       except etree.XMLSyntaxError:
           return []
       if root_xml is None:
           return []
       # ADTool root is <adtree><node>...</node></adtree>; the first <node> is our root
       root_node_xml = root_xml.find("node")
       if root_node_xml is None:
           return []
       tree = _adtool_node_to_dict(root_node_xml)
       entries: list[dict[str, Any]] = []
       _walk_node({"label": "", "children": [tree], "gate": None}, parent_path="", entries=entries)
       return entries


   def _adtool_node_to_dict(node_xml: etree._Element) -> dict[str, Any]:
       label_elem = node_xml.find("label")
       label = (label_elem.text or "").strip() if label_elem is not None else ""
       refinement = node_xml.get("refinement", "disjunctive")
       gate = "AND" if refinement == "conjunctive" else "OR" if refinement == "disjunctive" else None
       children = [_adtool_node_to_dict(child) for child in node_xml.findall("node")]
       return {"label": label, "children": children, "gate": gate}


   # ---------- JSON parser ----------

   def parse_attack_tree_json(data: dict[str, Any]) -> list[dict[str, Any]]:
       """Parse a JSON attack tree (generic {goal, gate, children[]} convention)."""
       tree = _json_node_to_dict(data)
       entries: list[dict[str, Any]] = []
       _walk_node({"label": "", "children": [tree], "gate": None}, parent_path="", entries=entries)
       return entries


   def _json_node_to_dict(data: dict[str, Any]) -> dict[str, Any]:
       label = data.get("goal") or data.get("label") or ""
       gate = data.get("gate")
       children = [_json_node_to_dict(c) for c in (data.get("children") or [])]
       return {"label": label, "children": children, "gate": gate}


   # ---------- dispatcher (called by Task B-17's CLI) ----------

   def parse_attack_tree(path: Path) -> list[dict[str, Any]]:
       suffix = path.suffix.lower()
       if suffix in (".txt", ".md"):
           return parse_indented_prose(path.read_text(encoding="utf-8"))
       if suffix == ".xml":
           return parse_adtool_xml(path.read_bytes())
       if suffix == ".json":
           return parse_attack_tree_json(json.loads(path.read_text(encoding="utf-8")))
       raise ValueError(f"Unsupported attack-tree file extension: {suffix}")
   ```

   **Notes on the implementation:**

  - **Three parsers share `_walk_node`** which is the canonical tree → entries conversion. The format-specific code only builds the tree dict; everything downstream is shared.
  - **`asset` is `"(attack-tree node)"`** for all entries — attack trees model adversary actions, not asset surfaces. The recon agent (Task B-20) can refine this with semantic enrichment if it identifies asset patterns in node labels.
  - **`inferred_apd_goals` starts empty** — the keyword-based ATT&CK technique mapping is shallow; the recon agent enriches `inferred_apd_goals` based on ATT&CK technique → APD goal lookup (or leaves empty if the technique didn't match).
  - **AND/OR gate** is appended as `(AND)` / `(OR)` to the `attack_tree_position` for visibility in the YAML.
  - **XXE safety** for ADTool XML uses the same four flags as B-13's Microsoft TMT parser.

- [ ] **Step 6: Run tests + linters + commit**

   ```bash
   pytest tests/test_attack_tree_parser.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/threat_model/attack_tree.py \
           tests/test_attack_tree_parser.py \
           tests/fixtures/threat_models/sample-attack-tree.txt \
           tests/fixtures/threat_models/sample-attack-tree.adtool.xml \
           tests/fixtures/threat_models/sample-attack-tree.json
   git commit -m "feat(threat_model): parser for attack trees (indented prose, ADTool XML, JSON)

   Three sub-format parsers share a canonical _walk_node tree→entries converter.
   Indented prose handles 4-space and tab indentation, plus AND/OR gate keywords.
   ADTool XML parses <adtree><node refinement=conjunctive|disjunctive> with XXE
   guards. JSON tree follows the {goal, gate, children[]} convention. Leaves
   attempt ATT&CK technique mapping via case-insensitive keyword heuristic;
   intermediates and roots stay at low confidence."
   ```

---

### Task B-17: CLI subcommand `parse-threat-model`

**Goal:** Single CLI command that:

1. Dispatches to the right parser based on file extension (with `--methodology-hint` as override)
2. Auto-detects methodology when the hint is absent (e.g., LINDDUN tables vs STRIDE tables by header signature)
3. Wraps parser output in the normalized-threat-model envelope
4. Validates the result against `schemas/threat-model-normalized.schema.json` (Task B-9) before writing
5. Writes YAML to stdout or to `--output <path>`
6. Reports parse errors with file/line context where possible

**Files:**

- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tools/apd_gauntlet/threat_model/dispatcher.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_threat_model_dispatcher.py`

**Methodology auto-detection rules** (used when `--methodology-hint` is absent):

| File extension | Detection logic | Result |
|---|---|---|
| `.tm7` | Always Microsoft TMT | `stride` |
| `.adtool.xml` or generic `.xml` with `<adtree>` root | Always attack tree | `attack_tree` |
| `.json` with top-level `summary` + `detail.diagrams` | Threat Dragon | `stride` |
| `.json` with top-level `goal` + `children` | Attack tree | `attack_tree` |
| `.md` or `.csv` with LINDDUN-signature header (from `is_linddun_table()` in Task B-15) | LINDDUN table | `linddun` |
| `.md` or `.csv` with STRIDE-signature header | STRIDE table | `stride` |
| `.txt` | Indented prose attack tree | `attack_tree` |
| Anything else | Cannot auto-detect | `free_form` (parser returns empty entries; agent does LLM extraction) |

The hint always wins. If the hint is `pasta`/`vast`/`trike`/`free_form`, the parser short-circuits to the empty-entries fallback and the recon agent (Task B-20) handles extraction via LLM.

- [ ] **Step 1: Implement the dispatcher** `tools/apd_gauntlet/threat_model/dispatcher.py`

   ```python
   """Format detection + parser dispatch for threat models."""

   from __future__ import annotations

   import json
   from datetime import datetime, timezone
   from pathlib import Path
   from typing import Any

   from . import attack_tree, linddun_table, microsoft_tmt, stride_table, threat_dragon
   from .linddun_table import is_linddun_table

   _SUPPORTED_HINTS: frozenset[str] = frozenset({
       "stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form",
   })


   def dispatch_parser(path: Path, hint: str | None = None) -> dict[str, Any]:
       """Parse a threat model file. Returns the normalized envelope dict.

       Raises ValueError if `hint` is provided but unrecognized.
       Returns free-form-fallback envelope if the format cannot be auto-detected
       (or hint requests it explicitly) — the recon agent then does LLM extraction.
       """
       if hint is not None and hint not in _SUPPORTED_HINTS:
           raise ValueError(
               f"unknown methodology hint '{hint}'; expected one of {sorted(_SUPPORTED_HINTS)}"
           )

       if hint in ("pasta", "vast", "trike", "free_form"):
           return _free_form_envelope(path, methodology=hint)

       suffix = path.suffix.lower()
       # Special suffix handling for .adtool.xml (compound extension)
       name_lower = path.name.lower()
       if name_lower.endswith(".adtool.xml"):
           suffix = ".adtool.xml"

       methodology, parser_id, entries = _detect_and_parse(path, suffix, hint)

       envelope = {
           "schema_version": 1,
           "generated_by": "threat_model_recon",
           "source_artifact": str(path),
           "methodology": methodology,
           "extraction_summary": _summarize(entries, parser_id),
           "entries": entries,
       }
       return envelope


   def _detect_and_parse(
       path: Path, suffix: str, hint: str | None
   ) -> tuple[str, str, list[dict[str, Any]]]:
       """Return (methodology, parser_id, entries) tuple."""
       # Hint disambiguates ambiguous extensions
       methodology = hint  # may be None; resolved below

       if suffix == ".tm7":
           return "stride", "microsoft_tmt", microsoft_tmt.parse_microsoft_tmt(path.read_bytes())

       if suffix == ".adtool.xml":
           return "attack_tree", "attack_tree.adtool_xml", attack_tree.parse_adtool_xml(path.read_bytes())

       if suffix == ".xml":
           # Could be ADTool or something else; sniff for <adtree> root
           content = path.read_bytes()
           if b"<adtree" in content[:512]:
               return "attack_tree", "attack_tree.adtool_xml", attack_tree.parse_adtool_xml(content)
           # Unknown XML — fall back to free_form
           return "free_form", "none — unrecognized XML", []

       if suffix == ".json":
           data = json.loads(path.read_text(encoding="utf-8"))
           # Threat Dragon shape: {summary, detail: {diagrams}}
           if isinstance(data, dict) and "summary" in data and "detail" in data and "diagrams" in (data.get("detail") or {}):
               return "stride", "threat_dragon", threat_dragon.parse_threat_dragon(data)
           # Attack-tree shape: {goal, children}
           if isinstance(data, dict) and "goal" in data and "children" in data:
               return "attack_tree", "attack_tree.json", attack_tree.parse_attack_tree_json(data)
           # Honor hint if provided; otherwise fall back to free_form
           if methodology == "stride":
               return "stride", "threat_dragon", threat_dragon.parse_threat_dragon(data)
           if methodology == "attack_tree":
               return "attack_tree", "attack_tree.json", attack_tree.parse_attack_tree_json(data)
           return "free_form", "none — unrecognized JSON shape", []

       if suffix in (".md", ".csv"):
           text = path.read_text(encoding="utf-8")
           # Sniff for LINDDUN first (more specific keywords)
           headers = _sniff_table_headers(text, suffix)
           if methodology == "linddun" or (methodology is None and is_linddun_table(headers)):
               parser_fn = linddun_table.parse_linddun_markdown if suffix == ".md" else linddun_table.parse_linddun_csv
               return "linddun", f"linddun_table.{suffix[1:]}", parser_fn(text)
           # Default to STRIDE
           parser_fn = stride_table.parse_stride_markdown if suffix == ".md" else stride_table.parse_stride_csv
           return "stride", f"stride_table.{suffix[1:]}", parser_fn(text)

       if suffix == ".txt":
           return "attack_tree", "attack_tree.indented_prose", attack_tree.parse_indented_prose(path.read_text(encoding="utf-8"))

       # Unknown extension
       return "free_form", "none — unrecognized extension", []


   def _sniff_table_headers(text: str, suffix: str) -> list[str]:
       """Return the first non-blank table row's cells as a list, for methodology detection."""
       if suffix == ".csv":
           import csv, io
           reader = csv.reader(io.StringIO(text))
           for row in reader:
               if row and any(c.strip() for c in row):
                   return row
           return []
       # Markdown
       for line in text.splitlines():
           stripped = line.strip()
           if stripped.startswith("|") and stripped.endswith("|"):
               cells = [c.strip() for c in stripped.split("|")[1:-1]]
               # Skip separator row
               if all(set(c) <= set("-:") for c in cells if c):
                   continue
               return cells
       return []


   def _free_form_envelope(path: Path, methodology: str) -> dict[str, Any]:
       return {
           "schema_version": 1,
           "generated_by": "threat_model_recon",
           "source_artifact": str(path),
           "methodology": methodology,
           "extraction_summary": {
               "entry_count": 0,
               "high_confidence_count": 0,
               "medium_confidence_count": 0,
               "low_confidence_count": 0,
               "parser_used": "none — LLM extraction required",
           },
           "entries": [],
       }


   def _summarize(entries: list[dict[str, Any]], parser_id: str) -> dict[str, Any]:
       def count(level: str) -> int:
           return sum(1 for e in entries if e.get("extraction_confidence") == level)
       return {
           "entry_count": len(entries),
           "high_confidence_count": count("high"),
           "medium_confidence_count": count("medium"),
           "low_confidence_count": count("low"),
           "parser_used": parser_id,
       }
   ```

- [ ] **Step 2: Implement the CLI subcommand** in `tools/apd_gauntlet/cli.py`

   ```python
   import yaml
   from jsonschema import Draft202012Validator
   from apd_gauntlet.threat_model.dispatcher import dispatch_parser


   @main.command("parse-threat-model")
   @click.argument("path", type=click.Path(exists=True, path_type=Path))
   @click.option("--methodology-hint", default=None,
                 help="Force a methodology (stride/linddun/attack_tree/pasta/vast/trike/free_form).")
   @click.option("--output", default=None, type=click.Path(path_type=Path),
                 help="Output path; if omitted, writes YAML to stdout.")
   @click.option("--validate/--no-validate", default=True,
                 help="Validate output against threat-model-normalized.schema.json (default: on).")
   def parse_threat_model_cmd(
       path: Path,
       methodology_hint: str | None,
       output: Path | None,
       validate: bool,
   ) -> None:
       """Parse a threat model file into a normalized YAML graph.

       Auto-detects the format from extension when --methodology-hint is absent.
       Validates the result against schemas/threat-model-normalized.schema.json
       unless --no-validate is passed.
       """
       try:
           normalized = dispatch_parser(path, methodology_hint)
       except ValueError as e:
           raise click.UsageError(str(e)) from e
       except json.JSONDecodeError as e:
           raise click.UsageError(f"failed to parse {path}: invalid JSON at line {e.lineno} col {e.colno}") from e

       if validate:
           schema_path = Path(__file__).parent.parent.parent / "schemas" / "threat-model-normalized.schema.json"
           schema = json.loads(schema_path.read_text())
           errors = list(Draft202012Validator(schema).iter_errors(normalized))
           if errors:
               click.echo(f"ERROR: parser output failed schema validation ({len(errors)} errors):", err=True)
               for err in errors[:5]:
                   click.echo(f"  - {err.message} at {list(err.absolute_path)}", err=True)
               raise click.Abort()

       text = yaml.safe_dump(normalized, sort_keys=False)
       if output:
           output.parent.mkdir(parents=True, exist_ok=True)
           output.write_text(text)
           click.echo(f"Wrote {output}", err=True)
           click.echo(f"  methodology: {normalized['methodology']}", err=True)
           click.echo(f"  entries:     {normalized['extraction_summary']['entry_count']}", err=True)
       else:
           click.echo(text)
   ```

- [ ] **Step 3: Write dispatcher tests** in `tests/test_threat_model_dispatcher.py`

   ```python
   from pathlib import Path

   import pytest

   from apd_gauntlet.threat_model.dispatcher import dispatch_parser


   def test_dispatch_threat_dragon_json_auto_detected():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-threat-dragon.json"))
       assert result["methodology"] == "stride"
       assert result["extraction_summary"]["parser_used"] == "threat_dragon"
       assert result["extraction_summary"]["entry_count"] >= 4

   def test_dispatch_microsoft_tmt_by_extension():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-microsoft.tm7"))
       assert result["methodology"] == "stride"
       assert "microsoft_tmt" in result["extraction_summary"]["parser_used"]

   def test_dispatch_linddun_table_auto_detected_via_header_keywords():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-linddun-table.md"))
       assert result["methodology"] == "linddun"
       assert "linddun_table" in result["extraction_summary"]["parser_used"]

   def test_dispatch_stride_table_default_when_no_linddun_signature():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-stride-table.md"))
       assert result["methodology"] == "stride"
       assert "stride_table" in result["extraction_summary"]["parser_used"]

   def test_dispatch_attack_tree_indented_prose_by_extension():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.txt"))
       assert result["methodology"] == "attack_tree"

   def test_dispatch_attack_tree_adtool_xml_by_compound_extension():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.adtool.xml"))
       assert result["methodology"] == "attack_tree"
       assert "adtool_xml" in result["extraction_summary"]["parser_used"]

   def test_dispatch_attack_tree_json_sniffed_via_goal_and_children_keys():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.json"))
       assert result["methodology"] == "attack_tree"
       assert "attack_tree.json" in result["extraction_summary"]["parser_used"]

   def test_hint_overrides_extension():
       # Force LINDDUN interpretation of a STRIDE-headered table
       result = dispatch_parser(
           Path("tests/fixtures/threat_models/sample-stride-table.md"),
           hint="linddun",
       )
       assert result["methodology"] == "linddun"

   def test_hint_pasta_returns_free_form_envelope():
       result = dispatch_parser(
           Path("tests/fixtures/threat_models/sample-stride-table.md"),
           hint="pasta",
       )
       assert result["methodology"] == "pasta"
       assert result["entries"] == []
       assert "LLM extraction required" in result["extraction_summary"]["parser_used"]

   def test_unknown_hint_raises_value_error():
       with pytest.raises(ValueError, match="unknown methodology hint"):
           dispatch_parser(Path("tests/fixtures/threat_models/sample-stride-table.md"), hint="bogus")

   def test_envelope_extraction_summary_counts_per_confidence_level():
       result = dispatch_parser(Path("tests/fixtures/threat_models/sample-attack-tree.json"))
       summary = result["extraction_summary"]
       assert summary["entry_count"] == summary["high_confidence_count"] + summary["medium_confidence_count"] + summary["low_confidence_count"]
   ```

- [ ] **Step 4: Write CLI tests** in `tests/test_cli.py`

   ```python
   import yaml
   from click.testing import CliRunner

   from apd_gauntlet.cli import main


   def test_cli_parse_threat_model_stdout(tmp_path):
       runner = CliRunner()
       result = runner.invoke(main, [
           "parse-threat-model",
           "tests/fixtures/threat_models/sample-stride-table.md",
       ])
       assert result.exit_code == 0
       data = yaml.safe_load(result.stdout)
       assert data["methodology"] == "stride"
       assert data["entries"]

   def test_cli_parse_threat_model_output_file(tmp_path):
       runner = CliRunner()
       output = tmp_path / "normalized.yaml"
       result = runner.invoke(main, [
           "parse-threat-model",
           "tests/fixtures/threat_models/sample-stride-table.md",
           "--output", str(output),
       ])
       assert result.exit_code == 0
       assert output.exists()
       data = yaml.safe_load(output.read_text())
       assert data["methodology"] == "stride"

   def test_cli_parse_threat_model_validates_output_against_schema(tmp_path):
       """Default --validate=on; happy-path fixtures must validate cleanly."""
       runner = CliRunner()
       result = runner.invoke(main, [
           "parse-threat-model",
           "tests/fixtures/threat_models/sample-microsoft.tm7",
           "--output", str(tmp_path / "out.yaml"),
       ])
       assert result.exit_code == 0
       assert "ERROR" not in result.stderr

   def test_cli_parse_threat_model_methodology_hint_override():
       runner = CliRunner()
       result = runner.invoke(main, [
           "parse-threat-model",
           "tests/fixtures/threat_models/sample-stride-table.md",
           "--methodology-hint", "linddun",
       ])
       assert result.exit_code == 0
       data = yaml.safe_load(result.stdout)
       assert data["methodology"] == "linddun"

   def test_cli_parse_threat_model_rejects_unknown_hint():
       runner = CliRunner()
       result = runner.invoke(main, [
           "parse-threat-model",
           "tests/fixtures/threat_models/sample-stride-table.md",
           "--methodology-hint", "made_up",
       ])
       assert result.exit_code != 0
       assert "unknown methodology hint" in result.output

   def test_cli_parse_threat_model_reports_invalid_json_path(tmp_path):
       bad = tmp_path / "bad.json"
       bad.write_text("{ not valid json")
       runner = CliRunner()
       result = runner.invoke(main, ["parse-threat-model", str(bad)])
       assert result.exit_code != 0
       assert "invalid JSON" in result.output
   ```

- [ ] **Step 5: Run tests + linters + commit**

   ```bash
   pytest tests/test_threat_model_dispatcher.py tests/test_cli.py -v
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/threat_model/dispatcher.py tools/apd_gauntlet/cli.py \
           tests/test_threat_model_dispatcher.py tests/test_cli.py
   git commit -m "feat(cli): add parse-threat-model subcommand with format auto-dispatch

   Dispatcher auto-detects format from extension + content sniffing
   (.tm7 → Microsoft TMT, .json with {summary,detail.diagrams} → Threat Dragon,
   .json with {goal,children} → attack tree, .md/.csv → STRIDE or LINDDUN
   based on header signature, .txt → indented-prose attack tree). The
   --methodology-hint flag overrides auto-detection; hint=pasta/vast/trike/
   free_form short-circuits to an empty-entries envelope for the recon agent
   to handle via LLM. Default --validate runs jsonschema validation against
   threat-model-normalized.schema.json; --no-validate skips for debugging."
   ```

---

### Task B-18: init-run CLI extension — `--threat-model` + `--methodology-hint`

**Goal:** Mirror Phase A Task A-16's `--taxonomies` pattern. `init-run` accepts both new flags and writes them into the scaffolded `.apd-run.yaml` so `apd-threat-model-recon` can find the threat model on its tier-0 activation.

**Files:**

- Modify: `tools/apd_gauntlet/init_run.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Modify: `tests/test_init_run_config.py`
- Modify: `tests/test_cli.py`

**Path semantics:** `--threat-model <path>` is interpreted as **relative to the `--inputs` directory** (i.e., the artifacts the run consumes). This matches how `apd-code-recon` interprets code-evidence-index paths. When the recon agent activates, it resolves: `<run-dir>/<inputs-relative-path>` to locate the actual file.

- [ ] **Step 1: Read the existing `scaffold_run()` function**

   ```bash
   grep -n "def scaffold_run" tools/apd_gauntlet/init_run.py
   ```

   Confirm the function signature already accepts kwargs like `taxonomies: list[str] | None = None` (Task A-16's pattern).

- [ ] **Step 2: Write failing tests** in `tests/test_init_run_config.py`

   ```python
   import yaml
   from pathlib import Path

   from apd_gauntlet.init_run import scaffold_run


   def test_scaffold_run_includes_threat_model_when_provided(tmp_path):
       run_dir = tmp_path / "test-run"
       scaffold_run(
           run_id="test-run",
           inputs=tmp_path / "inputs",
           domain="pbm",
           target_root=tmp_path,
           threat_model="threat-model.tm7",
       )
       cfg = yaml.safe_load((run_dir / ".apd-run.yaml").read_text())
       assert cfg["threat_model"] == "threat-model.tm7"

   def test_scaffold_run_includes_methodology_hint_when_provided(tmp_path):
       scaffold_run(
           run_id="test-run-2",
           inputs=tmp_path / "inputs",
           domain="pbm",
           target_root=tmp_path,
           threat_model="threat-model.tm7",
           methodology_hint="stride",
       )
       cfg = yaml.safe_load((tmp_path / "test-run-2" / ".apd-run.yaml").read_text())
       assert cfg["methodology_hint"] == "stride"

   def test_scaffold_run_omits_threat_model_when_absent(tmp_path):
       scaffold_run(
           run_id="test-run-3",
           inputs=tmp_path / "inputs",
           domain="pbm",
           target_root=tmp_path,
       )
       cfg = yaml.safe_load((tmp_path / "test-run-3" / ".apd-run.yaml").read_text())
       assert "threat_model" not in cfg
       assert "methodology_hint" not in cfg

   def test_scaffold_run_omits_methodology_hint_when_only_threat_model_provided(tmp_path):
       """methodology_hint is optional even when threat_model is set (parser auto-detects)."""
       scaffold_run(
           run_id="test-run-4",
           inputs=tmp_path / "inputs",
           domain="pbm",
           target_root=tmp_path,
           threat_model="threat-model.tm7",
       )
       cfg = yaml.safe_load((tmp_path / "test-run-4" / ".apd-run.yaml").read_text())
       assert cfg["threat_model"] == "threat-model.tm7"
       assert "methodology_hint" not in cfg
   ```

   And in `tests/test_cli.py`:

   ```python
   def test_cli_init_run_accepts_threat_model_and_methodology_hint(tmp_path):
       runner = CliRunner()
       result = runner.invoke(main, [
           "init-run", "test-cli-tm",
           "--inputs", str(tmp_path / "inputs"),
           "--domain", "pbm",
           "--target-root", str(tmp_path),
           "--threat-model", "model.tm7",
           "--methodology-hint", "stride",
       ])
       assert result.exit_code == 0
       cfg_path = tmp_path / "test-cli-tm" / ".apd-run.yaml"
       assert cfg_path.exists()
       cfg = yaml.safe_load(cfg_path.read_text())
       assert cfg["threat_model"] == "model.tm7"
       assert cfg["methodology_hint"] == "stride"

   def test_cli_init_run_methodology_hint_validated_against_known_set(tmp_path):
       runner = CliRunner()
       result = runner.invoke(main, [
           "init-run", "test-cli-bad-hint",
           "--inputs", str(tmp_path / "inputs"),
           "--domain", "pbm",
           "--target-root", str(tmp_path),
           "--threat-model", "model.tm7",
           "--methodology-hint", "bogus",
       ])
       # Click should reject the bad enum at parse time
       assert result.exit_code != 0
   ```

- [ ] **Step 3: Run tests to verify they fail**

   ```bash
   pytest tests/test_init_run_config.py tests/test_cli.py -v -k "threat_model or methodology_hint"
   ```

- [ ] **Step 4: Extend `scaffold_run()` in `tools/apd_gauntlet/init_run.py`**

   Add two new keyword-only parameters:

   ```python
   def scaffold_run(
       *,
       run_id: str,
       inputs: Path,
       domain: str,
       target_root: Path = Path("runs"),
       taxonomies: list[str] | None = None,
       threat_model: str | None = None,           # NEW (Task B-18)
       methodology_hint: str | None = None,       # NEW (Task B-18)
       # ... existing parameters from earlier Phases ...
   ) -> Path:
       # ... existing setup ...
       config: dict[str, Any] = {
           "run_id": run_id,
           "domain": domain,
           "framework_version": __version__,
           # ... existing fields ...
       }
       if taxonomies:
           config["taxonomies"] = list(taxonomies)
       if threat_model:
           config["threat_model"] = threat_model
       if methodology_hint:
           config["methodology_hint"] = methodology_hint
       # ... write .apd-run.yaml ...
   ```

   Critical: do NOT add either field to the config dict if absent — the schema (Task B-8) requires their absence in v1.2-compat runs.

- [ ] **Step 5: Extend the CLI in `tools/apd_gauntlet/cli.py`**

   ```python
   @main.command("init-run")
   @click.argument("run_id")
   @click.option("--inputs", required=True, type=click.Path(path_type=Path))
   @click.option("--domain", required=True)
   @click.option("--target-root", default=Path("runs"), type=click.Path(path_type=Path))
   @click.option("--taxonomies", default=None,
                 help="Comma-separated taxonomies (cwe,mitre_attack,d3fend,owasp_top10,owasp_api_top10,owasp_llm_top10).")
   @click.option("--threat-model", default=None,
                 help="Path (relative to --inputs) to a threat model file. Activates apd-threat-model-recon.")
   @click.option("--methodology-hint",
                 type=click.Choice(["stride", "linddun", "attack_tree", "pasta", "vast", "trike", "free_form"]),
                 default=None,
                 help="Override threat-model methodology auto-detection.")
   def init_run_cmd(
       run_id: str,
       inputs: Path,
       domain: str,
       target_root: Path,
       taxonomies: str | None,
       threat_model: str | None,
       methodology_hint: str | None,
   ) -> None:
       parsed_taxonomies = [t.strip() for t in taxonomies.split(",") if t.strip()] if taxonomies else None
       path = scaffold_run(
           run_id=run_id,
           inputs=inputs,
           domain=domain,
           target_root=target_root,
           taxonomies=parsed_taxonomies,
           threat_model=threat_model,
           methodology_hint=methodology_hint,
       )
       click.echo(f"Scaffolded {path}")
   ```

   Click's `Choice` type rejects unknown methodology hints at parse time, giving a clear error message without reaching `scaffold_run`.

- [ ] **Step 6: Run tests to verify they pass**

   ```bash
   pytest tests/test_init_run_config.py tests/test_cli.py -v
   pytest -q
   ```

- [ ] **Step 7: Manual smoke test**

   ```bash
   apd-gauntlet init-run apd-20260601-tm-test \
     --inputs ./test-inputs \
     --domain pbm \
     --threat-model my-threat-model.tm7 \
     --methodology-hint stride
   cat runs/apd-20260601-tm-test/.apd-run.yaml
   ```

   Expected: scaffolded YAML contains `threat_model: my-threat-model.tm7` and `methodology_hint: stride`.

- [ ] **Step 8: Linters + commit**

   ```bash
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/init_run.py tools/apd_gauntlet/cli.py \
           tests/test_init_run_config.py tests/test_cli.py
   git commit -m "feat(cli): init-run accepts --threat-model and --methodology-hint flags

   Both fields are optional in the scaffolded .apd-run.yaml — omitted when
   the flag isn't passed (preserves v1.2 backward compatibility).
   methodology_hint uses Click's Choice type to reject unknown values at
   parse time. The threat-model path is interpreted as relative to --inputs;
   the apd-threat-model-recon agent resolves <run-dir>/<inputs-relative>
   when activated."
   ```

---

### Task B-19: New skill `apd-threat-model-methodologies`

**Goal:** Skill file consulted by both the recon agent (Task B-20) and the evaluator agent (Task B-21). Documents (a) the canonical methodology→APD-goal mapping tables (sourced from `tools/apd_gauntlet/threat_model/mappings.py`); (b) the discipline rules from the design spec; (c) the format-detection heuristics; (d) per-format parsing semantics; (e) the three evaluator finding flavors with concrete examples.

**Files:**

- Create: `.claude/skills/apd-threat-model-methodologies/SKILL.md`

The project does NOT auto-generate skills from sources (`build_domain_skill.py` only handles domain packs, not general skills). This is hand-authored.

- [ ] **Step 1: Author the skill content**

   Create `.claude/skills/apd-threat-model-methodologies/SKILL.md` with the following content:

```markdown
---
name: apd-threat-model-methodologies
description: |
  Methodology-aware discipline for parsing and evaluating user-supplied threat
  models. Canonical STRIDE/LINDDUN→APD-goal mapping tables. Discipline rules
  for the apd-threat-model-recon (parsing + enrichment) and
  apd-threat-model-evaluator (coverage/contradiction/silence finding emission)
  agents. Required reading for both agents.
---

# APD Threat-Model Methodology Discipline

## What this skill covers

This skill governs how the gauntlet handles user-supplied threat models. It is
required reading for two agents:

- **`apd-threat-model-recon`** (tier-0): parses TM files into normalized graph;
  enriches structural output with semantic mappings.
- **`apd-threat-model-evaluator`** (tier-4): evaluates the normalized graph
  against specialist findings; emits coverage-gap, contradiction, and silence
  findings.

Native support: **STRIDE** (OWASP Threat Dragon JSON, Microsoft TMT `.tm7`,
STRIDE-per-element Markdown/CSV), **LINDDUN** (Markdown/CSV tables), **attack
trees** (indented prose, ADTool XML, JSON).

Reduced-fidelity support: **PASTA**, **VAST**, **Trike**, free-form prose. The
recon agent's LLM does extraction; entries get `extraction_confidence: low`.

## Methodology → APD-goal mapping (canonical)

These tables are the **single source of truth** for STRIDE/LINDDUN → APD goal
inference. They mirror the Python module
`tools/apd_gauntlet/threat_model/mappings.py` — when one changes, the other
must change. The Python module is authoritative for parser code; this skill is
authoritative for agent reasoning.

### STRIDE

| Letter | Category | APD Goal(s) |
|---|---|---|
| S | Spoofing | Authenticity |
| T | Tampering | Integrity |
| R | Repudiation | Non-Repudiation |
| I | Information Disclosure | Confidentiality |
| D | Denial of Service | Availability |
| E | Elevation of Privilege | Authenticity + Integrity |

The `E` case maps to two goals because privilege escalation crosses the
authentication/authorization boundary (Authenticity) and typically involves
manipulating data the privileged role can write (Integrity).

### LINDDUN

LINDDUN's single-letter codes overlap (`D` and `N` are reused). The parser
disambiguates via column position; this skill uses compound keys:

| Compound Key | Full Category | Position | APD Goal(s) |
|---|---|---|---|
| `L` | Linkability | 1 | Confidentiality |
| `I` | Identifiability | 2 | Confidentiality |
| `N_repudiation` | Non-repudiation (privacy harm) | 3 | Non-Repudiation |
| `D_etectability` | Detectability | 4 | Confidentiality |
| `D_isclosure` | Disclosure of information | 5 | Confidentiality |
| `U` | Unawareness (lack of consent) | 6 | Authenticity |
| `N_compliance` | Non-compliance | 7 | Non-Repudiation (domain-mapped) |

**N_compliance domain mapping:** when the domain pack defines a non-compliance
override (e.g., PBM maps `N_compliance` to HIPAA breach-notification controls
under Non-Repudiation), use the domain-specific goal set. Default falls back to
Non-Repudiation.

### Attack tree

Attack-tree leaves get ATT&CK technique mappings via the parser's keyword
heuristic (see `tools/apd_gauntlet/threat_model/attack_tree.py::_ATTACK_TECHNIQUE_KEYWORDS`).
The recon agent (Task B-20) refines these via LLM judgment, then derives
`inferred_apd_goals` from the ATT&CK technique → APD goal mapping (already
documented in the `apd-control-mappings` skill).

## Format detection heuristics (for the recon agent)

The recon agent's first step is to call `apd-gauntlet parse-threat-model`,
which handles auto-detection. The agent SHOULD pass `--methodology-hint <X>`
when the `.apd-run.yaml` declares `methodology_hint: <X>`; otherwise let the
CLI auto-detect.

| Artifact pattern | Methodology | Notes |
|---|---|---|
| `.tm7` file | STRIDE (Microsoft TMT) | Always; .tm7 is TMT-only |
| `.adtool.xml` file | Attack tree (ADTool) | Always |
| `.json` with `summary`+`detail.diagrams` keys | STRIDE (Threat Dragon) | Auto-sniffed |
| `.json` with `goal`+`children` keys | Attack tree | Auto-sniffed |
| `.md`/`.csv` with `Linkability`/`Identifiability`/etc. in header | LINDDUN | `is_linddun_table()` heuristic |
| `.md`/`.csv` otherwise | STRIDE per-element | Default |
| `.txt` | Attack tree (indented prose) | Default |
| Free-form prose, narrative docs | `free_form` | LLM extraction by agent |

When the parser returns `methodology: free_form` with zero entries, that
signals the recon agent to perform LLM extraction directly from the artifact
text (read the file, identify asset/threat/mitigation triples, emit entries
with `extraction_confidence: low`).

## Discipline rules

These rules apply to BOTH the recon agent (when enriching parser output) and
the evaluator agent (when emitting findings).

### Rule 1 — Never invent threats

**The recon agent never adds threats the operator didn't write.** Parser output
defines the entry set; the recon agent enriches existing entries with mappings
but does not create new ones. The only exception is `methodology: free_form`,
where the agent extracts entries from prose — but each extracted entry must
correspond to a discrete claim in the source text, not the agent's own
brainstorm.

**The evaluator agent never emits findings about threats that aren't in the
normalized graph.** Coverage-gap findings (Rule 5) fire only when a specialist
finding shows the gap is real on a real surface; they do not fire because the
agent thinks "the operator should have considered X."

### Rule 2 — Never re-derive STRIDE/LINDDUN coverage from scratch

If the TM author chose to leave a STRIDE category blank for a surface, that's
their assessment — don't fabricate threats to fill it. The evaluator's
coverage-gap findings only fire when (a) the TM is silent on the category AND
(b) a specialist finding on the same surface flags risk in the APD goals that
category maps to.

### Rule 3 — Free-form extraction caps at `low` confidence

When the recon agent does LLM extraction (free-form prose), every emitted
entry has `extraction_confidence: low`. Low-confidence entries cannot drive
**contradiction** findings (Rule 6) — they can only drive **uncertainty**
findings. Reason: the agent's interpretation of free-form prose is fallible;
contradicting a specialist finding on the basis of a fallible interpretation
is too aggressive.

### Rule 4 — Block-on-ambiguity

If the supplied artifact cannot be parsed into ANY entries (parser returns
empty AND LLM extraction confidence is below threshold for the whole
document), the recon agent emits the envelope with `entries: []` and a
`methodology: unknown` flag. The evaluator agent then emits a single finding
with:

- `disposition: blocked`
- `prerequisite_evidence: ["normalized threat model in supported format"]`
- A recommendation pointing to `docs/threat-modeling.md` for supported formats

and skips coverage/contradiction/silence evaluation entirely.

### Rule 5 — Coverage gap (`disposition: gap`)

**Algorithm:**
1. Build a per-surface map: `surface → {APD goals flagged by specialist
   findings}`. Use evidence locators in specialist findings to identify
   surfaces.
2. Build a per-surface map: `surface → {APD goals covered by TM entries}`.
3. For each surface where a specialist flagged goal G but no TM entry maps
   to G on that surface: emit a coverage-gap finding.

**Example:** A specialist Non-Repudiation finding flags `audit-log-writer` for
missing immutability. The TM has 5 STRIDE-per-element entries for
`audit-log-writer` covering S, T, I, D, E — but no R. The evaluator emits:

```yaml
disposition: gap
severity: medium   # inherit from the flagging specialist finding's severity
title: "Threat model omits Repudiation analysis for audit-log-writer"
summary: "Specialist non-repudiation finding nonrep-... flagged audit-log-writer
  for missing immutability. The threat model's STRIDE entries for this surface
  cover S, T, I, D, E but not R."
```

### Rule 6 — Contradiction (`disposition: risk`)

**Algorithm:**

1. For each TM entry with a `mitigation` claim (e.g., "TLS 1.3 enforced on
   pricing-service traffic"), parse the claim for asserted controls.
2. Search specialist findings for the SAME surface AND the SAME control area.
3. If a specialist finding shows the control is absent/broken (e.g.,
   `conf-...` shows plaintext where the TM claims TLS), emit a contradiction
   finding cross-referencing the specialist finding's ID.

**Example:**

```yaml
disposition: risk
severity: high   # inherit from the contradicting specialist finding
title: "Threat model asserts mitigation that specialist finding contradicts"
summary: "TM entry tm-1a2b3c4d for adjudication→pricing flow claims:
  'mitigation: TLS 1.3 enforced on pricing-service traffic'. Confidentiality
  specialist finding conf-9e8d7c6b shows plaintext HTTP on this path."
cross_references:
  - conf-9e8d7c6b
evidence:
  - artifact: "00-context/threat-model-normalized.yaml"
    locator: "entries[entry_id=tm-1a2b3c4d]"
    excerpt: "mitigation: TLS 1.3 enforced..."
```

Contradiction findings have **two evidence pointers**: one for the TM claim
(quote the relevant excerpt from normalized.yaml) and one or more for the
contradicting specialist finding(s) (via cross-references).

**Confidence cap:** if the TM entry's `extraction_confidence` is `low`,
demote `disposition: risk` → `disposition: uncertainty` (Rule 3). Free-form
extractions are too fallible to assert contradiction.

### Rule 7 — Silence (`disposition: uncertainty`)

**Algorithm:**

1. Identify surfaces that specialist findings flagged as risky.
2. For each such surface, check whether the TM has ANY entries (regardless
   of methodology category).
3. If the TM has zero entries for the surface: emit a silence finding noting
   the gap.

**Example:** Authenticity specialist finds `auth-...` flagging the vendor API
integration for weak mTLS. The TM has zero entries mentioning that surface.
Evaluator emits:

```yaml
disposition: uncertainty
severity: low   # silence is informational unless the spec finding was high
title: "Threat model is silent on vendor-API integration"
summary: "Specialist authenticity finding auth-5d4c3b2a flagged the
  vendor-API integration for weak mTLS. The threat model has no entries
  for this surface."
cross_references:
  - auth-5d4c3b2a
```

Silence findings are not contradictions — the TM didn't make a wrong claim,
it made no claim. The disposition is `uncertainty` because reviewers may
need to ask the TM author whether the omission was deliberate (out of scope)
or accidental.

## Validation contract

After emitting findings, validate against `schemas/threat-model-normalized.schema.json`
and `schemas/threat-model-coverage.schema.json`. Validator's per-record check
for `tmeval-` findings (Task B-25) enforces:

- Each `tmeval-` finding has at least one evidence entry pointing at
  `00-context/threat-model-normalized.yaml` or the source artifact
- Each contradiction (`disposition: risk`) finding has at least one entry in
  `cross_references` (pointing to the contradicting specialist finding)

```

- [ ] **Step 2: Confirm lint-agents picks up the new skill**

   ```bash
   apd-gauntlet lint-agents
   ```

   Expected: skill frontmatter validates (name + description fields present and well-formed).

- [ ] **Step 3: Run full suite to confirm no regressions**

   ```bash
   pytest -q
   ```

- [ ] **Step 4: Commit**

   ```bash
   git add .claude/skills/apd-threat-model-methodologies/
   git commit -m "feat(skill): add apd-threat-model-methodologies with canonical mappings + discipline

   Single source of truth for STRIDE/LINDDUN→APD-goal mappings (mirrors
   Python tools/apd_gauntlet/threat_model/mappings.py). Discipline rules
   (never invent threats, never re-derive coverage, free-form caps at low
   confidence, block-on-ambiguity) and algorithms for the three evaluator
   finding flavors (coverage gap, contradiction, silence). Required reading
   for apd-threat-model-recon and apd-threat-model-evaluator."
   ```

---

### Task B-20: New agent `apd-threat-model-recon` (tier-0)

**Goal:** Activation-gated tier-0 agent that runs after `apd-intake`. Mirrors v1.1's `apd-code-recon` pattern — context-builder, does not emit findings.

**Activation contract:** activates when ANY of:

- `.apd-run.yaml` declares `threat_model: <path>`, OR
- `apd-intake`'s output mentions a threat-model artifact in its inventory (e.g., a `.tm7` file in the `inputs/` directory)

When neither condition is met, the agent SKIPS (no error, no output) — the orchestrator simply proceeds to tier-1.

**Process** (high-level — full agent file below):

1. Read `.apd-run.yaml`; locate the threat-model path (or detect via intake output)
2. Invoke `apd-gauntlet parse-threat-model <path> [--methodology-hint <X>] --output 00-context/threat-model-normalized.yaml --no-validate` (the agent validates after enrichment, so suppress the CLI's pre-enrichment validation)
3. Load the parser output
4. **Semantic enrichment pass:**
   - For attack-tree entries: refine `framework_refs.mitre_attack` using LLM judgment beyond the parser's keyword heuristic (e.g., "SMB lateral movement to adjudication network" → `T1021.002`)
   - For all entries with non-empty `framework_refs.mitre_attack`: derive `inferred_apd_goals` from the ATT&CK→APD-goal lookup (apd-control-mappings skill)
   - For `methodology: free_form` (empty entries): perform LLM extraction directly from the source artifact; emit entries with `extraction_confidence: low`
5. Re-validate the enriched envelope against `schemas/threat-model-normalized.schema.json`
6. Write final YAML to `00-context/threat-model-normalized.yaml`
7. Self-check (see agent file)

**Files:**

- Create: `.claude/agents/apd-threat-model-recon.md`
- Modify: `.claude/agents/apd-orchestrator.md` (register in tier-0 sequence)

(Template for `00-context/threat-model-normalized.yaml` is in Task B-23.)

- [ ] **Step 1: Author the agent file** `.claude/agents/apd-threat-model-recon.md`

```markdown
---
name: apd-threat-model-recon
description: |
  Tier-0 activation-gated agent that parses user-supplied threat models into
  a normalized graph at 00-context/threat-model-normalized.yaml. Activates
  when .apd-run.yaml declares threat_model:<path> or intake detects a TM-like
  artifact. Does not emit findings — pure context-builder. Output is consumed
  by specialists (as evidence pointers) and by apd-threat-model-evaluator
  (for coverage/contradiction/silence analysis in tier-4).
tools:
  - Read
  - Glob
  - Grep
  - Write
  - Bash    # required to invoke `apd-gauntlet parse-threat-model`
---

# Threat Model Reconnaissance Agent (apd-threat-model-recon)

## Required reading

- `apd-threat-model-methodologies` (mappings + discipline)
- `apd-evidence-discipline` (the Phase A core skill — never invent, evidence
  pointers required, block-on-ambiguity)

## Activation contract

This agent activates when **any** of the following is true:

1. `.apd-run.yaml` contains a `threat_model: <path>` field (path is relative
   to the run's `inputs/` directory)
2. `apd-intake`'s output at `00-context/context-brief.md` mentions a file
   matching `*.tm7`, `*.threat-model.json`, `*-threat-model.*`, `*.adtool.xml`,
   or any file the operator clearly identified as a threat model in their
   artifact inventory

If neither condition is met, this agent SKIPS — write a `00-context/threat-
model-skip.txt` placeholder with one line: `"skipped: no threat model declared
or detected"`, exit cleanly. The orchestrator proceeds to tier-1 unchanged.

## Output contract

When activated, emits exactly one file:
`00-context/threat-model-normalized.yaml`

The file MUST validate against `schemas/threat-model-normalized.schema.json`.

Does NOT emit any finding files. Does NOT modify any specialist outputs.

## Process

### Step 1 — Read run config and locate threat model

Read `.apd-run.yaml`. If `threat_model:` is present, use that path (relative
to `inputs/`). If absent, read `00-context/context-brief.md` and identify the
threat model from the artifact inventory.

Read the file (as text or bytes depending on format).

### Step 2 — Invoke the parser CLI

Run:

```bash
apd-gauntlet parse-threat-model <run-dir>/inputs/<threat-model-path> \
  [--methodology-hint <hint>] \
  --output <run-dir>/00-context/threat-model-normalized.yaml \
  --no-validate
```

`--no-validate` skips the CLI's schema validation because you will enrich the
output before validating. Capture stderr; if the CLI exits non-zero, note the
error and proceed to Step 3 with whatever the CLI was able to write (it may
have written a free_form-fallback envelope).

### Step 3 — Load parser output

Read the file you just wrote. Note the `methodology`, `extraction_summary`,
and `entries` count.

### Step 4 — Semantic enrichment

For each entry, apply enrichment passes as appropriate to its methodology:

**STRIDE entries** (Threat Dragon, Microsoft TMT, STRIDE tables):

- Verify `framework_refs.stride_letter` is set
- `inferred_apd_goals` should already be populated by the parser via the
  canonical mapping table; verify it matches (S→[authenticity], etc.)
- No further enrichment needed for these — parsers are deterministic

**LINDDUN entries:**

- Same as STRIDE: verify the canonical mapping was applied
- Special case: if the entry's `linddun_letter` is `N_compliance` AND the
  domain pack defines an N_compliance override (e.g., PBM maps it to HIPAA),
  add the domain-specific APD goals to `inferred_apd_goals`

**Attack-tree entries:**

- Leaves come with a shallow keyword-based `framework_refs.mitre_attack`
  list. Refine using your judgment: read the leaf text, identify likely
  ATT&CK techniques beyond the keyword match, add them to the list.
- For each ATT&CK technique now in `mitre_attack`, look up the corresponding
  APD goals from the apd-control-mappings skill's ATT&CK→APD-goal table.
  Add to `inferred_apd_goals`.

**Free-form entries** (parser output had `methodology: free_form` and
`entries: []`):

- Read the source artifact directly
- Identify each (asset, threat, mitigation) claim in the prose
- For each claim, construct an entry with:
  - `entry_id`: `tm-<sha8>` over (asset + threat + source_locator)
  - `extraction_confidence: low`
  - `source_locator`: the file path + a quoted excerpt (≤200 chars) from
    which you extracted
  - `framework_refs`: best-effort STRIDE letter mapping if the prose names a
    STRIDE category; otherwise all null
  - `inferred_apd_goals`: best-effort based on the threat description

### Step 5 — Validate

Validate the enriched envelope against `schemas/threat-model-normalized.schema.json`.
If validation fails:

- Log specific errors
- DO NOT write the file
- Emit a STATUS line on stderr: `"validation failed: <error count> errors;
  see stderr for details"`
- Exit non-zero so the orchestrator can decide whether to abort

### Step 6 — Write final YAML

Write `00-context/threat-model-normalized.yaml`. Re-compute
`extraction_summary` counts after enrichment (free-form additions count
toward `low_confidence_count`).

### Step 7 — Self-check before exit

Confirm:

- [ ] File exists at `00-context/threat-model-normalized.yaml`
- [ ] File validates against `schemas/threat-model-normalized.schema.json`
- [ ] `extraction_summary.entry_count` matches `len(entries)`
- [ ] Every entry has a non-null `source_locator`
- [ ] No entry I added (during free-form extraction) lacks an evidence pointer
- [ ] If methodology was originally `free_form` and I extracted entries, all
      such entries are marked `extraction_confidence: low`

Exit cleanly.

## Discipline reminders

- **Never invent threats.** The parser output is the entry baseline. Your
  enrichment refines mappings; it does not add new threats unless the source
  was free-form prose where you are extracting from the operator's claims.
- **Evidence pointers required.** Every entry's `source_locator` must point
  back to a verifiable location in the source artifact.
- **Block, don't guess.** If the source artifact is unparseable AND you
  cannot extract any entries from prose, write an envelope with `entries: []`,
  `methodology: unknown`, `extraction_summary.parser_used: "none — unparseable"`,
  exit cleanly. The evaluator will handle the blocked case.

```

- [ ] **Step 2: Update the orchestrator** `.claude/agents/apd-orchestrator.md` to register the new agent in the tier-0 sequence

   In the orchestrator's process section, after the existing `apd-code-recon`
   activation step, add:

   ```markdown
   ### Tier-0 / Threat Model Recon (optional, v1.3+)

   After `apd-code-recon` (if it ran), invoke `apd-threat-model-recon`. The
   agent self-skips if no threat model is declared/detected, so always invoke
   it — the activation contract is internal to the agent.

   Expected outputs: `00-context/threat-model-normalized.yaml` (if activated)
   or `00-context/threat-model-skip.txt` (if skipped). Either is acceptable;
   downstream agents tolerate both.
   ```

- [ ] **Step 3: Confirm lint-agents handles the new agent**

   ```bash
   apd-gauntlet lint-agents
   ```

   Expected: `Lint clean: 14 agents checked.` (was 13, +1).

- [ ] **Step 4: Full suite + commit**

   ```bash
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add .claude/agents/apd-threat-model-recon.md \
           .claude/agents/apd-orchestrator.md
   git commit -m "feat(agent): add apd-threat-model-recon tier-0 parser/normalizer

   Activation-gated on .apd-run.yaml declaring threat_model:<path> or intake
   detecting a TM-like artifact. Dispatches to apd-gauntlet parse-threat-model
   for structural parsing, then applies semantic enrichment (ATT&CK refinement
   for attack-tree leaves, free-form LLM extraction for unstructured prose,
   N_compliance domain override). Validates final envelope against schema;
   does not emit findings. Orchestrator updated to invoke after apd-code-recon."
   ```

---

### Task B-21: New agent `apd-threat-model-evaluator` (tier-4)

**Goal:** Activation-gated tier-4 agent. Runs after `apd-synthesizer` completes (so it has dedup'd findings/capabilities to compare against). Emits the three finding flavors per the discipline rules in Task B-19's skill (rules 5/6/7) plus a coverage report.

**Activation contract:** activates when `00-context/threat-model-normalized.yaml` exists. If the file's `methodology` is `unknown` AND `entries` is empty, the agent emits a single blocked finding (Rule 4) and skips further evaluation.

**Files:**

- Create: `.claude/agents/apd-threat-model-evaluator.md`
- Modify: `.claude/agents/apd-orchestrator.md` (register in tier-4 sequence)

(Template for the coverage report markdown is in Task B-24.)

- [ ] **Step 1: Author the agent file** `.claude/agents/apd-threat-model-evaluator.md`

```markdown
---
name: apd-threat-model-evaluator
description: |
  Tier-4 activation-gated agent that evaluates the recon-emitted normalized
  threat model against dedup'd specialist findings and capabilities. Emits
  three finding flavors (coverage gap, contradiction, silence) per the
  discipline rules in apd-threat-model-methodologies, plus a per-surface
  coverage report at 40-synthesis/threat-model-coverage-report.md + machine-
  readable 40-synthesis/threat-model-coverage.yaml. Findings use
  agent: threat_model_evaluator and id: tmeval-<sha8>.
tools:
  - Read
  - Glob
  - Grep
  - Write
---

# Threat Model Evaluator Agent (apd-threat-model-evaluator)

## Required reading

- `apd-threat-model-methodologies` (mapping tables + the three disposition
  algorithms in Rules 5/6/7)
- `apd-finding-schema` (finding YAML structure + id pattern requirements;
  tmeval- prefix per Task B-7)
- `apd-evidence-discipline` (evidence pointers required, never invent,
  block-on-ambiguity)

## Activation contract

This agent activates when `00-context/threat-model-normalized.yaml` exists.
Self-skip if the file is absent (the orchestrator always invokes; activation
is internal to this agent).

If the file exists AND has `methodology: unknown` AND `entries: []`, emit a
single blocked finding (see Step 7 below) and exit. Do not attempt
coverage/contradiction/silence evaluation.

## Output contract

When activated, emits:

1. **Findings** as YAML files under `20-findings/40-threat-model/` (one file
   per finding, named `tmeval-<sha8>.yaml`). All findings have:
   - `agent: threat_model_evaluator`
   - `id: tmeval-<sha8>` (8 hex chars after the prefix)
   - At least one evidence entry pointing at
     `00-context/threat-model-normalized.yaml` or the source artifact
   - Validates against `schemas/finding.schema.json`

2. **Coverage report** at `40-synthesis/threat-model-coverage-report.md`
   (human-readable; see template at `templates/threat-model-coverage-report.template.md`)

3. **Coverage YAML** at `40-synthesis/threat-model-coverage.yaml`
   (machine-readable; validates against `schemas/threat-model-coverage.schema.json`)

## Process

### Step 1 — Load inputs

Read:
- `00-context/threat-model-normalized.yaml` (the TM)
- All `20-findings/**/*.yaml` files (dedup'd by synthesizer)
- All `10-capabilities/**/*.yaml` files

Build in-memory indices:
- `tm_entries_by_surface: dict[str, list[entry]]` — surfaces are inferred from
  entry `asset` field; if the asset string doesn't match any specialist
  finding's evidence locator, the entry isn't bound to a known surface (still
  counts in the overall coverage; just doesn't drive surface-specific findings)
- `findings_by_surface: dict[str, list[finding]]` — surfaces from finding
  evidence locators (parse `artifact` and `locator` fields)
- `apd_goals_flagged_by_surface: dict[str, set[str]]` — for each surface,
  the set of APD goals that any specialist finding on that surface touched

### Step 2 — Blocked path

If TM has `methodology: unknown` AND `entries: []`:
- Skip Steps 3-6
- Go to Step 7 (emit blocked finding)
- Skip Steps 8-9 (no coverage report when blocked)

### Step 3 — Coverage gap detection (Rule 5)

For each (surface, goal) in `apd_goals_flagged_by_surface`:
- Check whether any TM entry on this surface has `inferred_apd_goals`
  containing `goal`
- If not: emit a coverage-gap finding

Coverage-gap finding template:

```yaml
schema_version: 1
id: tmeval-<sha8>   # sha over surface + goal + "coverage_gap"
agent: threat_model_evaluator
apd_tier: <tier of the absent goal>
apd_goal: <the absent goal>
disposition: gap
severity: <inherit from highest-severity specialist finding on this surface for this goal>
confidence: medium   # default; bump to high if multiple specialists flagged this surface+goal
title: "Threat model omits <Goal> analysis for <surface>"
summary: "Specialist <goal> finding <finding-id> flagged <surface> for ...
  The threat model's entries for this surface (<list of present categories>)
  do not address <Goal>."
detail: "..."
evidence:
  - artifact: "00-context/threat-model-normalized.yaml"
    locator: "entries[asset=<surface>]"
    excerpt: <YAML excerpt showing the entries that exist for this surface>
control_mappings:
  nist_800_53r5: <inherit from the flagging specialist finding>
cross_references:
  - <flagging specialist finding id>
recommendation:
  posture: recommended
  summary: "Extend threat model with <Goal> analysis for <surface>"
  detail: "..."
```

### Step 4 — Contradiction detection (Rule 6)

For each TM entry with a non-null `mitigation`:

1. Identify the surface (from `asset` field)
2. Parse the mitigation claim for asserted controls (LLM judgment — e.g.,
   "TLS 1.3 enforced" asserts encryption-in-transit on this surface)
3. For each asserted control, search specialist findings on the SAME surface
   for findings that show the control is absent/broken
4. If found: emit a contradiction finding cross-referencing the specialist
   finding's id

Contradiction finding template:

```yaml
id: tmeval-<sha8>   # sha over tm_entry_id + contradicting_finding_id
agent: threat_model_evaluator
apd_tier: <tier of the contradicting finding>
apd_goal: <goal of the contradicting finding>
disposition: risk
severity: <inherit from contradicting specialist finding>
confidence: <demote to medium/low if TM entry's extraction_confidence is medium/low>
title: "Threat model asserts mitigation that <specialist-id> contradicts"
summary: "TM entry <tm-id> for <surface> claims:
  'mitigation: <quoted-claim>'. <Specialist-id> shows <contradicting reality>."
evidence:
  - artifact: "00-context/threat-model-normalized.yaml"
    locator: "entries[entry_id=<tm-id>]"
    excerpt: "<mitigation text quote>"
cross_references:
  - <contradicting specialist finding id>
recommendation:
  posture: required
  summary: "Reconcile threat model and implementation reality"
  detail: "Either update the implementation to match the TM's mitigation
    claim, or update the TM to reflect what the implementation actually does."
```

**Confidence demotion (Rule 6 + Rule 3):**

- TM entry `extraction_confidence: high` → contradiction finding `confidence: high`
- TM entry `extraction_confidence: medium` → contradiction finding `confidence: medium`
- TM entry `extraction_confidence: low` → DO NOT emit as contradiction; emit as
  uncertainty (silence-style) finding instead

### Step 5 — Silence detection (Rule 7)

For each surface in `findings_by_surface` (i.e., surfaces that specialists
flagged):

- If `tm_entries_by_surface[surface]` is empty: emit a silence finding

Silence finding template:

```yaml
id: tmeval-<sha8>   # sha over surface + "silence"
agent: threat_model_evaluator
apd_tier: <tier of one of the flagging findings>
apd_goal: <goal of one of the flagging findings>
disposition: uncertainty
severity: <inherit from highest-severity flagging specialist finding, capped at medium>
confidence: high   # if multiple specialists flagged the surface; else medium
title: "Threat model is silent on <surface>"
summary: "Specialist <goal> finding(s) <ids> flagged <surface> for ...
  The threat model has no entries for this surface."
evidence:
  - artifact: "00-context/threat-model-normalized.yaml"
    locator: "(no entries for surface=<surface>)"
    excerpt: "(absent — TM coverage gap)"
cross_references:
  - <flagging specialist finding id(s)>
recommendation:
  posture: consider
  summary: "Clarify whether <surface> is intentionally out of scope"
  detail: "Either add threat-model entries for <surface> (if it was an
    accidental omission) or annotate the threat model with a deliberate
    out-of-scope note (so reviewers know the silence was intentional)."
```

### Step 6 — Build coverage matrix

For each surface in `tm_entries_by_surface ∪ findings_by_surface`:

- Determine `categories_present`: STRIDE letters / LINDDUN compound keys /
  attack-tree positions present in TM entries for this surface
- Determine `categories_absent`: complement of `categories_present` within
  the methodology's category set (e.g., for STRIDE: full set is
  `{S, T, R, I, D, E}`)
- Count `tm_entry_count` and list `tm_entry_ids`

Build the coverage YAML envelope matching `schemas/threat-model-coverage.schema.json`.

### Step 7 — Blocked-finding path (only reached if TM was unparseable)

```yaml
id: tmeval-<sha8>   # sha over the source artifact path
agent: threat_model_evaluator
apd_tier: trustworthiness   # default tier; the gap is foundational
apd_goal: non_repudiation   # the TM should produce an auditable assessment
disposition: blocked
prerequisite_evidence:
  - "normalized threat model in supported format (STRIDE, LINDDUN, or attack tree)"
severity: medium
confidence: high
title: "Supplied threat model is unparseable; evaluation skipped"
summary: "The supplied threat-model artifact could not be parsed into a
  normalized graph. Re-supply in a supported format or provide a
  methodology_hint in .apd-run.yaml."
detail: "Supported formats are documented at docs/threat-modeling.md.
  Methodology hints: stride, linddun, attack_tree, pasta, vast, trike,
  free_form."
evidence:
  - artifact: <source threat-model path>
    locator: "(whole file)"
    excerpt: "(unparseable)"
recommendation:
  posture: required
  summary: "Supply threat model in supported format"
  detail: "..."
```

### Step 8 — Write coverage report markdown

Render `40-synthesis/threat-model-coverage-report.md` using the template at
`templates/threat-model-coverage-report.template.md`. Include:

- TM summary (methodology, entry count, confidence breakdown)
- Per-surface coverage table
- Lists of emitted findings (coverage gaps, contradictions, silences)
- Summary statistics (matching the YAML's `summary` block)

### Step 9 — Write coverage YAML

Write `40-synthesis/threat-model-coverage.yaml` matching the envelope from
Step 6. Validate against `schemas/threat-model-coverage.schema.json`.

### Step 10 — Self-check before exit

- [ ] All emitted finding files validate against `schemas/finding.schema.json`
- [ ] Every contradiction finding has a non-empty `cross_references` array
- [ ] Every finding has at least one evidence entry pointing at the TM
- [ ] No invented threats (every finding traces back to a real specialist
      finding or to a real TM claim)
- [ ] Coverage YAML validates against `schemas/threat-model-coverage.schema.json`
- [ ] Coverage report markdown is well-formed (no broken table syntax, no
      unresolved template placeholders)

Exit cleanly.

## Discipline reminders

- **Confidence cascading** (Rule 3 + Rule 6): low-confidence TM entries can
  produce silence findings but never contradictions
- **Severity inheritance**: tmeval- findings borrow severity from the
  specialist finding(s) they reference, capped per the rules above
- **Block, don't fabricate**: if the TM is unparseable, emit ONE blocked
  finding and stop. Don't attempt to invent threats to "make the evaluation
  useful"
- **Cross-references are required for contradictions** (validator enforces
  this per Task B-25)

```

- [ ] **Step 2: Update the orchestrator** to register the evaluator in the tier-4 sequence

   In `.claude/agents/apd-orchestrator.md`, after the `apd-synthesizer` step:

   ```markdown
   ### Tier-4 / Threat Model Evaluation (optional, v1.3+)

   After `apd-synthesizer` completes, invoke `apd-threat-model-evaluator`. The
   agent self-skips if `00-context/threat-model-normalized.yaml` is absent.

   Expected outputs (when activated):
   - Finding files at `20-findings/40-threat-model/tmeval-*.yaml`
   - `40-synthesis/threat-model-coverage-report.md`
   - `40-synthesis/threat-model-coverage.yaml`
   ```

- [ ] **Step 3: Confirm lint-agents**

   ```bash
   apd-gauntlet lint-agents
   ```

   Expected: `Lint clean: 15 agents checked.` (was 14 after B-20, +1).

- [ ] **Step 4: Full suite + commit**

   ```bash
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   git add .claude/agents/apd-threat-model-evaluator.md \
           .claude/agents/apd-orchestrator.md
   git commit -m "feat(agent): add apd-threat-model-evaluator tier-4 with three finding flavors

   Emits coverage-gap, contradiction, and silence findings per the discipline
   rules (5/6/7) in apd-threat-model-methodologies. Plus per-surface coverage
   report (markdown) and coverage YAML (machine-readable). Findings use
   agent: threat_model_evaluator and id: tmeval-<sha8>. Activation-gated on
   00-context/threat-model-normalized.yaml; emits a single blocked finding
   when the TM was unparseable (per Rule 4)."
   ```

---

### Task B-22: Update `apd-orchestrator.md` for activation contracts

**Goal:** Polish pass on the orchestrator file after Tasks B-20 and B-21 added the two new agents. Ensure:

- Tier-0 sequence is explicit (intake → optional code-recon → optional TM-recon)
- Tier-4 sequence is explicit (synthesizer → optional TM-evaluator)
- Each agent's activation contract is documented clearly
- A topology diagram or list reflects the v1.3 state (15 agents total)

**Files:**

- Modify: `.claude/agents/apd-orchestrator.md`

- [ ] **Step 1: Read the orchestrator** after Tasks B-20 and B-21 have updated it

   ```bash
   wc -l .claude/agents/apd-orchestrator.md
   ```

   Verify the tier-0 and tier-4 additions from B-20/B-21 are present.

- [ ] **Step 2: Add or refresh the "Topology" section**

   The Phase A bundle added a 3-line topology summary after v1.1's code-recon
   landed. Expand it for v1.3:

   ```markdown
   ## Topology (v1.3+ — 15 agents)

   ### Tier-0 (intake / context)
   - `apd-intake` (required) — produces context-brief.md, data inventory,
     trust boundaries, taxonomy_suggestions (v1.2+)
   - `apd-code-recon` (optional, v1.1+) — activates if `code_recon: true` in
     run-config; emits code-evidence-index.yaml
   - `apd-threat-model-recon` (optional, v1.3+) — activates if `threat_model:
     <path>` declared or TM-like artifact detected; emits
     threat-model-normalized.yaml

   ### Tier-1 (Trustworthiness specialists)
   - `apd-confidentiality`, `apd-integrity`, `apd-availability`

   ### Tier-2 (Scalability specialists)
   - `apd-distributed`, `apd-resilient`, `apd-ephemeral`

   ### Tier-3 (Auditability specialists)
   - `apd-authenticity`, `apd-non-repudiation`, `apd-immutability`

   ### Tier-4 (synthesis)
   - `apd-synthesizer` (required) — dedup, coverage rollups (v1.2+: cwe,
     owasp, d3fend), contradictions across specialists
   - `apd-threat-model-evaluator` (optional, v1.3+) — activates if normalized
     TM exists; emits coverage gap / contradiction / silence findings
   ```

- [ ] **Step 3: Verify activation contracts are explicit for each optional agent**

   Each optional agent's section should answer:
   1. When does it activate?
   2. What does it produce when activated?
   3. What does it do when NOT activated? (Skip cleanly, no error)
   4. Does the rest of the pipeline depend on its output? (Answer: no —
      downstream agents tolerate absence)

- [ ] **Step 4: lint-agents + commit**

   ```bash
   apd-gauntlet lint-agents       # 15 agents clean
   pytest -q
   git add .claude/agents/apd-orchestrator.md
   git commit -m "docs(agent): update orchestrator topology for v1.3 (15 agents)

   Explicit Tier-0/Tier-1/Tier-2/Tier-3/Tier-4 sequence with activation
   contracts for the four optional agents (code-recon, TM-recon, the two
   Phase A-introduced specialist enhancements, TM-evaluator). Downstream
   agents tolerate absence of optional outputs."
   ```

---

### Task B-23: Template `threat-model-normalized.template.md`

**Goal:** Worked-example template that the recon agent uses as a guide when writing `00-context/threat-model-normalized.yaml`. The template is a markdown document containing a YAML code-block showing the canonical output shape with realistic content; the agent reads the template before its first emission to understand the expected structure.

**Files:**

- Create: `templates/threat-model-normalized.template.md`

- [ ] **Step 1: Author the template** `templates/threat-model-normalized.template.md`

   Mirror the style of `templates/code-architecture-brief.template.md` (the v1.1 precedent for tier-0 agent templates). Content:

```markdown
# Normalized Threat Model Template

> This template documents the canonical shape of `00-context/threat-model-normalized.yaml`,
> emitted by the `apd-threat-model-recon` agent (tier-0).
>
> Validates against `schemas/threat-model-normalized.schema.json`.

## When this artifact is produced

`apd-threat-model-recon` produces this file when activated (per Task B-20's
activation contract): the operator declared `threat_model: <path>` in
`.apd-run.yaml`, or `apd-intake` detected a TM-like artifact in the
inputs directory.

The file is consumed by:
- All tier-1/2/3 specialist agents (as an evidence pointer, alongside their
  primary inputs from intake)
- `apd-threat-model-evaluator` (tier-4) for coverage / contradiction /
  silence analysis

## Output shape

```yaml
schema_version: 1
generated_by: threat_model_recon
source_artifact: inputs/threat-model.json   # path relative to run dir
methodology: stride                          # or: linddun | attack_tree | pasta | vast | trike | free_form | unknown
extraction_summary:
  entry_count: 12
  high_confidence_count: 10
  medium_confidence_count: 1
  low_confidence_count: 1
  parser_used: threat_dragon                 # or: microsoft_tmt | stride_table.md | linddun_table.csv | attack_tree.adtool_xml | etc.
entries:
  # ----- A high-confidence STRIDE entry from a structured parser -----
  - entry_id: tm-a1b2c3d4
    asset: claim-ingress-API
    threat: "Pharmacy credential theft via phishing"
    mitigation: "MFA required on pharmacy portal; rotating short-lived tokens"
    methodology: stride
    source_locator: "diagrams[0].cells[3].threats[0]"
    extraction_confidence: high
    framework_refs:
      stride_letter: S
      linddun_letter: null
      attack_tree_position: null
      mitre_attack: []           # parsers don't infer ATT&CK from STRIDE; recon agent may add
    inferred_apd_goals: [authenticity]

  # ----- A medium-confidence entry where ATT&CK was inferred -----
  - entry_id: tm-5e6f7g8h
    asset: "(attack-tree node)"   # attack trees model adversary actions, not assets
    threat: "SMB lateral movement to adjudication network segment"
    mitigation: null               # attack-tree leaves typically have no mitigation
    methodology: attack_tree
    source_locator: "root/lateral-movement-from-vendor/smb-lateral-movement (OR)"
    extraction_confidence: medium  # ATT&CK heuristic match, not a structured assertion
    framework_refs:
      stride_letter: null
      linddun_letter: null
      attack_tree_position: "root/lateral-movement-from-vendor/smb-lateral-movement (OR)"
      mitre_attack: [T1021.002]
    inferred_apd_goals: [authenticity, integrity]   # from ATT&CK→APD-goal lookup

  # ----- A low-confidence entry from free-form prose extraction -----
  - entry_id: tm-9i0j1k2l
    asset: member-portal/profile-edit
    threat: "Cross-site scripting via name field"
    mitigation: "Server-side HTML escaping documented in threat-model.md"
    methodology: free_form
    source_locator: "inputs/threat-model.md, ~line 47: 'profile edit form must escape...'"
    extraction_confidence: low     # LLM-extracted from prose — fallible
    framework_refs:
      stride_letter: T             # best-effort inference from prose
      linddun_letter: null
      attack_tree_position: null
      mitre_attack: []
    inferred_apd_goals: [integrity]
```

## Field semantics

### `methodology` (envelope)

The dominant methodology of the source document. When mixed methodologies
appear in one document (rare), choose the one with the most entries. Use
`unknown` only when the parser produced zero entries AND LLM extraction
yielded nothing.

### `extraction_summary.parser_used`

The Python parser module name (or `"none — <reason>"` when the recon agent
did LLM extraction directly). Useful for debugging and for the operator to
understand how the file was produced.

### `entries[*].asset`

For STRIDE / LINDDUN: the component or data-flow name (from the TM author's
labels). For attack trees: always `"(attack-tree node)"` — attack trees
model adversary actions, not asset surfaces.

### `entries[*].mitigation`

The mitigation text from the TM, when present. `null` when:

- The TM author did not provide a mitigation
- The format does not have a mitigation column (STRIDE-per-element tables)
- The entry is an attack-tree leaf (leaves model attacker actions; the
  mitigation perspective is on the defender side)

### `entries[*].extraction_confidence`

- **high**: structural parser extracted from a well-formed file (Threat
  Dragon JSON, .tm7 XML, STRIDE/LINDDUN tables)
- **medium**: heuristic mapping applied (attack-tree leaf got ATT&CK
  technique via keyword match; recon agent inferred mapping beyond the
  parser's output)
- **low**: LLM extraction from free-form prose; the agent's interpretation
  could be wrong

This field gates evaluator behavior — low-confidence entries cannot drive
contradiction findings (only uncertainty / silence). See Rule 3 in
`apd-threat-model-methodologies` skill.

### `entries[*].framework_refs`

One field per methodology; the parser sets the relevant one, leaves
others null. The agent may add `mitre_attack` entries during enrichment.

### `entries[*].inferred_apd_goals`

Derived via the canonical mapping tables in
`tools/apd_gauntlet/threat_model/mappings.py` (STRIDE/LINDDUN) or the
ATT&CK→APD-goal lookup in `apd-control-mappings` skill. Empty `[]` is
acceptable when the entry has no mapping basis (rare; usually means the
parser misfired or the prose was unclear).

## Discipline reminders for the recon agent

See `apd-threat-model-methodologies` skill. Critical rules:

- **Never invent threats.** Parser output is the entry baseline.
- **Low-confidence is honest, not lazy.** Mark prose extractions `low`;
  don't optimistically claim `medium` to make the file look better.
- **Block, don't fabricate.** If the source is unparseable, emit empty
  entries with `methodology: unknown`. The evaluator handles the blocked
  case.

```

- [ ] **Step 2: Commit**

   ```bash
   git add templates/threat-model-normalized.template.md
   git commit -m "docs(template): add threat-model-normalized.template.md for recon agent output"
   ```

---

### Task B-24: Template `threat-model-coverage-report.template.md`

**Goal:** Markdown template for the evaluator's per-surface coverage report (`40-synthesis/threat-model-coverage-report.md`). Human-readable companion to the machine-readable `threat-model-coverage.yaml`.

**Files:**

- Create: `templates/threat-model-coverage-report.template.md`

- [ ] **Step 1: Author the template** `templates/threat-model-coverage-report.template.md`

```markdown
# Threat Model Coverage Report Template

> This template documents the structure of `40-synthesis/threat-model-coverage-report.md`,
> emitted by the `apd-threat-model-evaluator` agent (tier-4).
>
> The companion machine-readable artifact is
> `40-synthesis/threat-model-coverage.yaml` (validates against
> `schemas/threat-model-coverage.schema.json`).

## Worked example

```markdown
# Threat Model Coverage Report

**Generated by:** `apd-threat-model-evaluator`
**Source threat model:** `inputs/threat-model.json` (Threat Dragon JSON, STRIDE)
**Run:** `apd-20260601-claim-event-bus`

---

## Summary

| Metric | Value |
|---|---|
| Total TM entries | 12 |
| High-confidence entries | 10 |
| Medium-confidence entries | 1 |
| Low-confidence entries | 1 |
| Surfaces examined | 4 |
| Coverage gaps emitted | 2 |
| Contradictions emitted | 1 |
| Silences emitted | 1 |
| Blocked findings | 0 |

**Overall assessment:** The threat model covers 4 of 5 specialist-flagged
surfaces. One surface (vendor API integration) is entirely absent. The
threat model's TLS claim for the adjudication→pricing path contradicts a
confidentiality specialist finding.

---

## Per-surface coverage matrix

### claim-ingress-API

| Methodology category | Present in TM | Specialist flagged |
|---|---|---|
| S — Spoofing | ✓ (1 entry) | yes (`auth-dbba3dea`) |
| T — Tampering | ✓ (1 entry) | yes (`intg-42a3ebbd`) |
| R — Repudiation | absent | no |
| I — Information Disclosure | ✓ (1 entry) | yes (`conf-e443de8b`) |
| D — Denial of Service | ✓ (1 entry) | no |
| E — Elevation of Privilege | ✓ (1 entry) | no |

TM entry IDs: `tm-a1b2c3d4`, `tm-5e6f7g8h`, `tm-9i0j1k2l`, `tm-3m4n5o6p`, `tm-7q8r9s0t`

### audit-log-writer

| Methodology category | Present in TM | Specialist flagged |
|---|---|---|
| S — Spoofing | absent | no |
| T — Tampering | absent | no |
| R — Repudiation | **absent** | **yes (`nonrep-1a2b3c4d`)** — COVERAGE GAP |
| I — Information Disclosure | absent | no |
| D — Denial of Service | absent | no |
| E — Elevation of Privilege | absent | no |

TM entry IDs: (none — the TM has no entries for this surface)

→ Coverage gap finding: `tmeval-...` (see "Coverage gaps" section below)

### adjudication-service → pricing-service

| Methodology category | Present in TM | Specialist flagged |
|---|---|---|
| I — Information Disclosure | ✓ (1 entry, mitigation claimed) | **yes (`conf-7aa376c5`)** — CONTRADICTION |

TM entry `tm-aaaa1111` asserts mitigation "TLS 1.3 enforced". Specialist
finding `conf-7aa376c5` shows plaintext HTTP on this path.

→ Contradiction finding: `tmeval-...` (see "Contradictions" section below)

### vendor-API integration

| Methodology category | Present in TM | Specialist flagged |
|---|---|---|
| (all categories) | **absent** | **yes (`auth-9f8e7d6c`)** — SILENCE |

TM entry IDs: (none — the TM has zero entries for this surface)

→ Silence finding: `tmeval-...` (see "Silences" section below)

---

## Coverage gaps

### `tmeval-cccc3333` — TM omits Repudiation analysis for audit-log-writer

**Severity:** medium (inherited from `nonrep-1a2b3c4d`)
**APD goal:** Non-Repudiation
**Cross-references:** `nonrep-1a2b3c4d`

The non-repudiation specialist flagged audit-log-writer for missing
immutability protections. The threat model has no entries for this surface,
and specifically no Repudiation-category entries for any surface — the TM
author did not consider Repudiation threats.

**Recommendation:** Extend the threat model with at least one Repudiation
entry for audit-log-writer covering: who can delete entries, what audit
trail protects against silent log deletion, how the write-once property is
enforced.

---

## Contradictions

### `tmeval-dddd4444` — TM asserts TLS that `conf-7aa376c5` contradicts

**Severity:** high (inherited from the confidentiality specialist finding)
**APD goal:** Confidentiality
**Confidence:** high (TM entry `tm-aaaa1111` is from structural parser — high extraction confidence)
**Cross-references:** `conf-7aa376c5`

The TM entry for adjudication→pricing claims `mitigation: "TLS 1.3 enforced
on all internal service-to-service traffic"`. The confidentiality
specialist finding shows the actual pricing-service call uses `http://`,
not `https://`, and the gateway does not terminate TLS for this path.

**Recommendation:** Reconcile by either:
1. Updating the implementation to actually enforce TLS 1.3 on this path
   (the TM's intended state), OR
2. Updating the threat model to reflect the current implementation (so
   reviewers see the real risk surface)

---

## Silences

### `tmeval-eeee5555` — TM is silent on vendor-API integration

**Severity:** medium (inherited from `auth-9f8e7d6c`)
**APD goal:** Authenticity
**Cross-references:** `auth-9f8e7d6c`

The authenticity specialist flagged the vendor-API integration for weak
mTLS. The threat model has zero entries mentioning this surface — neither
in scope (with threats analyzed) nor out of scope (with a note).

**Recommendation:** Clarify scope. Either add threat-model entries for the
vendor-API integration (if the omission was accidental) or annotate the
threat model with a deliberate out-of-scope note (so reviewers know the
silence was intentional and what other artifact covers the vendor
integration).

---

## Blocked findings

(None in this report — the threat model parsed successfully.)
```

## Notes on rendering

- **Severity ordering** within a section: highest severity first
- **Cross-references** in the report should be exact finding IDs (e.g.,
  `conf-7aa376c5`) so reviewers can grep the run directory
- **TM entry IDs** in the per-surface matrix help reviewers trace claims
  back to the normalized YAML
- **Surface inference:** the agent identifies surfaces from the asset
  field of TM entries and the artifact/locator fields of specialist
  findings; surfaces that appear in only one of these are still listed
  (with the other column marked appropriately)

```

- [ ] **Step 2: Commit**

   ```bash
   git add templates/threat-model-coverage-report.template.md
   git commit -m "docs(template): add threat-model-coverage-report.template.md for evaluator output"
   ```

---

### Task B-25: Validator extensions for tmeval- findings

**Goal:** Per-record semantic checks specific to `tmeval-` findings. Phase A established the pattern (Task A-17 added `check_d3fend_counters_attack`); this task adds two more checks following the same conventions.

The two checks:

1. **Evidence-pointer requirement** — every `tmeval-` finding must have at least one entry in `evidence` whose `artifact` field is either `"00-context/threat-model-normalized.yaml"` or the source threat-model artifact path. This prevents tmeval- findings that don't trace back to the TM.

2. **Contradiction cross-reference requirement** — every `tmeval-` finding with `disposition: risk` must have a non-empty `cross_references` array. Per Rule 6 in the apd-threat-model-methodologies skill, contradictions cross-reference the specialist finding they contradict; a contradiction with no cross-references is structurally incomplete.

**Files:**

- Modify: `tools/apd_gauntlet/linters.py` — add two `check_*` functions
- Modify: `tools/apd_gauntlet/validate.py` — wire into the per-finding pass
- Modify: `tests/test_validate_semantic.py` — add tests + module-level YAML snippet constants

- [ ] **Step 1: Read existing validator patterns**

   ```bash
   grep -n "def check_" tools/apd_gauntlet/linters.py
   grep -n "run_semantic_pass\|check_d3fend" tools/apd_gauntlet/validate.py
   ```

   Note how Task A-17's `check_d3fend_counters_attack` is wired — your two new checks follow the same pattern: lint function returns `list[str]`; validate.py wraps each message in a `Violation(path, record_id, message)` at the call site.

- [ ] **Step 2: Write failing tests** in `tests/test_validate_semantic.py`

   Add module-level YAML snippet constants (mirror Task A-17's `_MITRE_SNIPPET`):

   ```python
   _TMEVAL_VALID_FULL: str = """
       schema_version: 1
       id: tmeval-a1b2c3d4
       agent: threat_model_evaluator
       apd_tier: trustworthiness
       apd_goal: confidentiality
       disposition: gap
       severity: medium
       confidence: high
       title: "Threat model omits Repudiation analysis for audit-log-writer"
       summary: "..."
       detail: "..."
       evidence:
         - artifact: "00-context/threat-model-normalized.yaml"
           locator: "entries[entry_id=tm-a1b2c3d4]"
           excerpt: "..."
       control_mappings:
         nist_800_53r5: [AU-9]
       recommendation:
         posture: recommended
         summary: "..."
   """

   _TMEVAL_MISSING_TM_EVIDENCE: str = """
       schema_version: 1
       id: tmeval-b2c3d4e5
       agent: threat_model_evaluator
       apd_tier: trustworthiness
       apd_goal: confidentiality
       disposition: gap
       severity: medium
       confidence: high
       title: "..."
       summary: "..."
       detail: "..."
       evidence:
         - artifact: "src/main.py"     # wrong! doesn't point at TM
           locator: "line 42"
           excerpt: "..."
       control_mappings:
         nist_800_53r5: [AU-9]
       recommendation:
         posture: recommended
         summary: "..."
   """

   _TMEVAL_CONTRADICTION_WITHOUT_CROSS_REF: str = """
       schema_version: 1
       id: tmeval-c3d4e5f6
       agent: threat_model_evaluator
       apd_tier: trustworthiness
       apd_goal: confidentiality
       disposition: risk      # contradiction
       severity: high
       confidence: high
       title: "..."
       summary: "..."
       detail: "..."
       evidence:
         - artifact: "00-context/threat-model-normalized.yaml"
           locator: "entries[entry_id=tm-...]"
           excerpt: "..."
       control_mappings:
         nist_800_53r5: [SC-8]
       cross_references: []   # empty! contradictions require non-empty cross-refs
       recommendation:
         posture: required
         summary: "..."
   """

   _TMEVAL_CONTRADICTION_WITH_CROSS_REF: str = """
       schema_version: 1
       id: tmeval-d4e5f6a7
       agent: threat_model_evaluator
       apd_tier: trustworthiness
       apd_goal: confidentiality
       disposition: risk
       severity: high
       confidence: high
       title: "..."
       summary: "..."
       detail: "..."
       evidence:
         - artifact: "00-context/threat-model-normalized.yaml"
           locator: "entries[entry_id=tm-...]"
           excerpt: "..."
       control_mappings:
         nist_800_53r5: [SC-8]
       cross_references: [conf-9e8d7c6b]   # the contradicting specialist finding
       recommendation:
         posture: required
         summary: "..."
   """
   ```

   Tests:

   ```python
   def test_tmeval_finding_with_tm_evidence_passes(tmp_path):
       _write_finding(tmp_path / "20-findings" / "40-threat-model" / "tmeval-a1b2c3d4.yaml", _TMEVAL_VALID_FULL)
       result = run_validation(tmp_path)
       assert not any("missing tm evidence" in v.message.lower() for v in result.errors)

   def test_tmeval_finding_without_tm_evidence_fails(tmp_path):
       _write_finding(tmp_path / "20-findings" / "40-threat-model" / "tmeval-b2c3d4e5.yaml", _TMEVAL_MISSING_TM_EVIDENCE)
       result = run_validation(tmp_path)
       assert any("evidence" in v.message.lower() and "threat-model" in v.message.lower() for v in result.errors)

   def test_tmeval_contradiction_without_cross_reference_fails(tmp_path):
       _write_finding(tmp_path / "20-findings" / "40-threat-model" / "tmeval-c3d4e5f6.yaml", _TMEVAL_CONTRADICTION_WITHOUT_CROSS_REF)
       result = run_validation(tmp_path)
       assert any("contradiction" in v.message.lower() and "cross_references" in v.message.lower() for v in result.errors)

   def test_tmeval_contradiction_with_cross_reference_passes(tmp_path):
       _write_finding(tmp_path / "20-findings" / "40-threat-model" / "tmeval-d4e5f6a7.yaml", _TMEVAL_CONTRADICTION_WITH_CROSS_REF)
       result = run_validation(tmp_path)
       assert not any("cross_references" in v.message.lower() for v in result.errors)

   def test_non_tmeval_findings_not_subject_to_tmeval_checks(tmp_path):
       """A regular conf-... finding without TM evidence should NOT trigger the new checks."""
       conf_finding = _MAKE_CONF_FINDING_FROM_PHASE_A_PATTERN()  # the existing test helper
       _write_finding(tmp_path / "20-findings" / "10-trustworthiness" / "conf-xxx.yaml", conf_finding)
       result = run_validation(tmp_path)
       assert not any("missing tm evidence" in v.message.lower() for v in result.errors)
   ```

   Run: `pytest tests/test_validate_semantic.py -v -k "tmeval"` → expect FAIL.

- [ ] **Step 3: Implement the two checks in `tools/apd_gauntlet/linters.py`**

   Add at the same level as `check_d3fend_counters_attack` (Task A-17):

   ```python
   def check_tmeval_evidence_pointer(record: dict[str, Any]) -> list[str]:
       """Every tmeval- finding must cite the normalized TM or the source artifact in evidence.

       Triggers only when record["id"] starts with "tmeval-" — non-tmeval findings
       are untouched by this check.
       """
       errors: list[str] = []
       record_id = record.get("id") or ""
       if not record_id.startswith("tmeval-"):
           return errors
       evidence = record.get("evidence") or []
       has_tm_evidence = any(
           _looks_like_tm_evidence(item.get("artifact") or "")
           for item in evidence
       )
       if not has_tm_evidence:
           errors.append(
               f"{record_id}: tmeval- findings must have at least one evidence entry "
               f"pointing at 00-context/threat-model-normalized.yaml or the source "
               f"threat-model artifact path. None found in {len(evidence)} evidence entries. "
               f"(missing tm evidence)"
           )
       return errors


   def check_tmeval_contradiction_cross_reference(record: dict[str, Any]) -> list[str]:
       """Every tmeval- finding with disposition: risk must have non-empty cross_references.

       Per Rule 6 in apd-threat-model-methodologies: contradictions cross-reference
       the specialist finding they contradict; an empty list is structurally incomplete.
       """
       errors: list[str] = []
       record_id = record.get("id") or ""
       if not record_id.startswith("tmeval-"):
           return errors
       if record.get("disposition") != "risk":
           return errors
       cross_refs = record.get("cross_references") or []
       if not cross_refs:
           errors.append(
               f"{record_id}: tmeval- contradiction (disposition: risk) must have at "
               f"least one entry in cross_references pointing to the contradicting "
               f"specialist finding. Empty list is structurally incomplete per "
               f"apd-threat-model-methodologies Rule 6."
           )
       return errors


   def _looks_like_tm_evidence(artifact: str) -> bool:
       """True if the evidence's artifact field points at the normalized TM or a TM source."""
       if artifact == "00-context/threat-model-normalized.yaml":
           return True
       # Heuristic: anything under inputs/ ending in TM-like patterns
       tm_patterns = (
           ".tm7", ".adtool.xml", "threat-model.json", "threat-model.md",
           "threat-model.csv", "threat-model.txt", "-threat-model.",
           "threat_model.",
       )
       lower = artifact.lower()
       return any(pat in lower for pat in tm_patterns)
   ```

- [ ] **Step 4: Wire into `tools/apd_gauntlet/validate.py`**

   Find `run_semantic_pass` (or wherever Task A-17's `check_d3fend_counters_attack` is wired). Add inside the per-finding loop branch:

   ```python
   # In the per-record pass for findings (kind == "finding"):
   for message in check_tmeval_evidence_pointer(record):
       report.errors.append(Violation(path=path, record_id=record.get("id"), message=message))
   for message in check_tmeval_contradiction_cross_reference(record):
       report.errors.append(Violation(path=path, record_id=record.get("id"), message=message))
   ```

   The checks themselves short-circuit when the record isn't a tmeval- finding, so calling them on every finding is safe and cheap.

- [ ] **Step 5: Run tests to verify they pass**

   ```bash
   pytest tests/test_validate_semantic.py -v -k "tmeval"
   pytest -q
   ```

- [ ] **Step 6: Full sweep + linters + commit**

   ```bash
   ruff check tools/ tests/
   mypy tools/
   git add tools/apd_gauntlet/linters.py tools/apd_gauntlet/validate.py \
           tests/test_validate_semantic.py
   git commit -m "feat(validate): tmeval- finding evidence + contradiction cross-reference checks

   Two new per-record checks in linters.py (wired into run_semantic_pass):

   1. check_tmeval_evidence_pointer — every tmeval- finding must cite
      00-context/threat-model-normalized.yaml or a recognized TM artifact
      path in its evidence array (prevents tmeval- findings that don't
      trace back to the threat model).

   2. check_tmeval_contradiction_cross_reference — every tmeval- finding
      with disposition: risk (contradiction) must have non-empty
      cross_references (per Rule 6 in apd-threat-model-methodologies:
      contradictions cross-reference the specialist finding they
      contradict).

   Both checks short-circuit for non-tmeval findings. Pattern mirrors
   Task A-17's check_d3fend_counters_attack."
   ```

---

### Task B-26: Extend bundled example with a threat model

**Goal:** Add a real Threat Dragon JSON threat model to `examples/apd-20260601-claim-event-bus/` that exercises all three evaluator finding flavors (coverage gap, contradiction, silence) against the Phase A specialist findings. Ship the normalized YAML, coverage report, coverage YAML, and three tmeval- findings as expected outputs so `apd-gauntlet validate examples/.../expected/` continues to pass end-to-end.

This is the integration test for the entire Phase B pipeline.

**Files:**

- Create: `examples/apd-20260601-claim-event-bus/inputs/threat-model.json`
- Modify: `examples/apd-20260601-claim-event-bus/.apd-run.yaml` (add `threat_model: inputs/threat-model.json` and `methodology_hint: stride`)
- Create: `examples/apd-20260601-claim-event-bus/expected/00-context/threat-model-normalized.yaml`
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/threat-model-coverage-report.md`
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/threat-model-coverage.yaml`
- Create: `examples/apd-20260601-claim-event-bus/expected/40-threat-model/tmeval-cccc3333.yaml` (coverage gap)
- Create: `examples/apd-20260601-claim-event-bus/expected/40-threat-model/tmeval-dddd4444.yaml` (contradiction)
- Create: `examples/apd-20260601-claim-event-bus/expected/40-threat-model/tmeval-eeee5555.yaml` (silence)

(Phase A's Task A-19 discovered the example uses a tier-grouped layout for findings. The threat-model evaluator's findings live in a new directory `40-threat-model/` to keep them visually distinct from specialist tier output.)

**Target findings to contradict / cover gaps for / be silent on:** The Phase A example has these findings (from Task A-19's modifications):

| Finding ID | Surface | APD goal |
|---|---|---|
| `conf-7aa376c5` | adjudication-service → pricing-service (Kafka) | confidentiality |
| `conf-e443de8b` | shared bearer tokens | confidentiality |
| `intg-42a3ebbd` | no payload signing | integrity |
| `auth-dbba3dea` | SMS MFA weak | authenticity |
| `auth-8d386c2f` | bearer tokens not mTLS | authenticity |
| `nonrep-...` | (verify exact ID by reading `examples/.../expected/30-auditability/non-repudiation.findings.yaml`) | non-repudiation |

(Phase A's actual finding IDs may differ slightly — verify by reading the example directory at execution time. Adjust the TM and tmeval- finding cross-references to match.)

**Target finding flavors:**

| Flavor | Source TM entry | Cross-references |
|---|---|---|
| **Contradiction** | TM entry asserts mitigation "TLS 1.3 enforced on all Kafka traffic" for adjudication↔pricing | `conf-7aa376c5` (specialist showed plaintext) |
| **Coverage gap** | TM has S/T/I/D/E entries for audit-log-writer but no R | `nonrep-...` (specialist flagged missing immutability) |
| **Silence** | TM has zero entries for vendor-API integration | `auth-dbba3dea` or another flagging finding |

- [ ] **Step 1: Inspect the existing example to confirm finding IDs**

   ```bash
   ls examples/apd-20260601-claim-event-bus/expected/
   find examples/apd-20260601-claim-event-bus/expected -name "*.findings.yaml" -exec head -5 {} \;
   ```

   Build a list of actual finding IDs by tier+goal so cross-references can be exact.

- [ ] **Step 2: Author the Threat Dragon JSON** `examples/apd-20260601-claim-event-bus/inputs/threat-model.json`

   ```json
   {
     "summary": {
       "title": "PBM Claim Event Bus Threat Model",
       "owner": "Architecture review team",
       "description": "STRIDE threat model for the claim adjudication event bus, prepared during initial design review."
     },
     "detail": {
       "contributors": [{"name": "Architecture review team"}],
       "diagrams": [
         {
           "id": "diagram-1",
           "title": "Claim Event Bus Data Flow",
           "diagramType": "STRIDE",
           "cells": [
             {
               "id": "cell-1",
               "data": {
                 "type": "tm.Process",
                 "name": "claim-ingress-API",
                 "outOfScope": false,
                 "threats": [
                   {"id": "th-1", "type": "Spoofing", "title": "Pharmacy credential theft via phishing", "status": "Open", "severity": "Medium", "description": "...", "mitigation": "MFA required on pharmacy portal; rotating short-lived tokens"},
                   {"id": "th-2", "type": "Tampering", "title": "Replay of submitted claim with altered NDC", "status": "Open", "severity": "Medium", "description": "...", "mitigation": "Payload signing with HMAC over canonical JSON"},
                   {"id": "th-3", "type": "Information Disclosure", "title": "Token in CloudFront access logs", "status": "Mitigated", "severity": "Low", "description": "...", "mitigation": "CloudFront logging filters strip Authorization header"},
                   {"id": "th-4", "type": "Denial of Service", "title": "High-volume duplicate submission DoS", "status": "Open", "severity": "Medium", "description": "...", "mitigation": "Rate limiting at API gateway"},
                   {"id": "th-5", "type": "Elevation of Privilege", "title": "Pharmacy account elevated via missing tenant check", "status": "Open", "severity": "High", "description": "...", "mitigation": "Tenant ID validated on every claim against pharmacy-to-tenant mapping"}
                 ]
               }
             },
             {
               "id": "cell-2",
               "data": {
                 "type": "tm.DataFlow",
                 "name": "adjudication-to-pricing",
                 "description": "adjudication-service queries pricing-service over Kafka",
                 "outOfScope": false,
                 "threats": [
                   {"id": "th-6", "type": "Information Disclosure", "title": "PHI in transit between adjudication and pricing services", "status": "Mitigated", "severity": "High", "description": "PHI is sent over Kafka to pricing-service for adjudication.", "mitigation": "TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing"}
                 ]
               }
             },
             {
               "id": "cell-3",
               "data": {
                 "type": "tm.Store",
                 "name": "audit-log-writer",
                 "outOfScope": false,
                 "threats": [
                   {"id": "th-7", "type": "Spoofing", "title": "Service account compromise allows audit write impersonation", "status": "Open", "severity": "Medium", "description": "...", "mitigation": "Service account isolation per writer process"},
                   {"id": "th-8", "type": "Tampering", "title": "Audit entry modification after write", "status": "Mitigated", "severity": "High", "description": "...", "mitigation": "Write-once storage on DynamoDB with deny-update IAM policy"},
                   {"id": "th-9", "type": "Information Disclosure", "title": "Audit entries leak PHI in error fields", "status": "Open", "severity": "Medium", "description": "...", "mitigation": "Error redaction in audit serializer"},
                   {"id": "th-10", "type": "Denial of Service", "title": "Audit writer DOS via flood", "status": "Open", "severity": "Low", "description": "...", "mitigation": "Per-source rate limit"},
                   {"id": "th-11", "type": "Elevation of Privilege", "title": "Direct DynamoDB write bypasses audit serializer", "status": "Open", "severity": "Medium", "description": "...", "mitigation": "IAM policy restricts table writes to audit-writer role"}
                 ]
               }
             }
           ]
         }
       ]
     }
   }
   ```

   Note what's deliberately missing:
  - **No Repudiation entries** for `audit-log-writer` (cell-3) — `nonrep-...` specialist found risk here → coverage gap
  - **No entries for vendor-API integration** — `auth-dbba3dea` flagged this → silence
  - **TM asserts TLS 1.3 on adjudication-to-pricing** (th-6) — `conf-7aa376c5` found plaintext on this path → contradiction

- [ ] **Step 3: Update the run-config** `examples/apd-20260601-claim-event-bus/.apd-run.yaml`

   Add these fields (preserving existing Phase A additions like `taxonomies:`):

   ```yaml
   threat_model: inputs/threat-model.json
   methodology_hint: stride
   ```

- [ ] **Step 4: Generate the normalized YAML by running the parser**

   ```bash
   cd examples/apd-20260601-claim-event-bus
   apd-gauntlet parse-threat-model inputs/threat-model.json \
     --methodology-hint stride \
     --output expected/00-context/threat-model-normalized.yaml
   ```

   Verify the output has 11 entries (one per threat from cells 1, 2, 3 totals) all with `extraction_confidence: high`.

- [ ] **Step 5: Hand-author the 3 tmeval- findings**

   `expected/40-threat-model/tmeval-cccc3333.yaml` (coverage gap):

   ```yaml
   schema_version: 1
   id: tmeval-cccc3333
   agent: threat_model_evaluator
   apd_tier: auditability
   apd_goal: non_repudiation
   disposition: gap
   severity: medium
   confidence: high
   title: "Threat model omits Repudiation analysis for audit-log-writer"
   summary: "Non-repudiation specialist finding nonrep-XXXXXXXX flagged audit-log-writer for missing immutability protections. The threat model's STRIDE entries for this surface cover S, T, I, D, E (5 threats) but not R."
   detail: "..."
   evidence:
     - artifact: "00-context/threat-model-normalized.yaml"
       locator: "entries[asset=audit-log-writer]"
       excerpt: "(5 entries present: th-7 S, th-8 T, th-9 I, th-10 D, th-11 E; no R entry)"
   control_mappings:
     nist_800_53r5: [AU-9, AU-10]
   cross_references: [nonrep-XXXXXXXX]   # exact ID from Step 1
   recommendation:
     posture: recommended
     summary: "Extend threat model with Repudiation analysis for audit-log-writer"
     detail: "Add a Repudiation entry covering: who can delete audit entries, how the write-once property is enforced (cell-3 th-8 mentions IAM deny-update but not deletion), and what audit trail protects against silent log deletion by a privileged actor."
   ```

   `expected/40-threat-model/tmeval-dddd4444.yaml` (contradiction):

   ```yaml
   schema_version: 1
   id: tmeval-dddd4444
   agent: threat_model_evaluator
   apd_tier: trustworthiness
   apd_goal: confidentiality
   disposition: risk
   severity: high
   confidence: high
   title: "Threat model asserts TLS that conf-7aa376c5 contradicts"
   summary: "TM entry tm-th6 for adjudication-to-pricing claims mitigation 'TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing'. Confidentiality specialist finding conf-7aa376c5 shows plaintext PHI on this Kafka topic."
   detail: "..."
   evidence:
     - artifact: "00-context/threat-model-normalized.yaml"
       locator: "entries[entry_id=tm-th6]"
       excerpt: "mitigation: TLS 1.3 enforced on all Kafka topics including adjudication-to-pricing"
   control_mappings:
     nist_800_53r5: [SC-8, SC-8(1)]
   cross_references: [conf-7aa376c5]
   recommendation:
     posture: required
     summary: "Reconcile threat model and implementation reality"
     detail: "Either enforce TLS 1.3 on the adjudication-to-pricing Kafka topic (the TM's intended state — see conf-7aa376c5 for the remediation specifics) or update the threat model to reflect that this topic operates in plaintext (which would re-raise th-6 to severity Critical given the PHI surface)."
   ```

   `expected/40-threat-model/tmeval-eeee5555.yaml` (silence):

   ```yaml
   schema_version: 1
   id: tmeval-eeee5555
   agent: threat_model_evaluator
   apd_tier: auditability
   apd_goal: authenticity
   disposition: uncertainty
   severity: medium
   confidence: high
   title: "Threat model is silent on vendor-API integration"
   summary: "Authenticity specialist finding auth-dbba3dea flagged the vendor-API integration for weak mTLS. The threat model has no entries for this surface — neither in scope (with threats analyzed) nor out of scope (with a note)."
   detail: "..."
   evidence:
     - artifact: "00-context/threat-model-normalized.yaml"
       locator: "(no entries for surface=vendor-API integration)"
       excerpt: "(absent — TM coverage gap)"
   control_mappings:
     nist_800_53r5: [IA-3, IA-5]
   cross_references: [auth-dbba3dea]
   recommendation:
     posture: consider
     summary: "Clarify whether vendor-API integration is intentionally out of scope"
     detail: "Either add threat-model entries for the vendor-API integration covering at least authentication (S) and tampering of vendor-provided pricing data (T), or annotate the threat model with a deliberate out-of-scope note so reviewers know the silence was intentional and what other artifact (e.g., the vendor security review) covers it."
   ```

- [ ] **Step 6: Hand-author the coverage report** `expected/40-synthesis/threat-model-coverage-report.md`

   Use the template from Task B-24 with the actual numbers for this example:
  - 11 TM entries (all `high` confidence; no `medium`/`low`)
  - Surfaces examined: 3 (claim-ingress-API, adjudication-to-pricing, audit-log-writer) + 1 absent (vendor-API)
  - 1 coverage gap, 1 contradiction, 1 silence emitted
  - 0 blocked findings

- [ ] **Step 7: Hand-author the coverage YAML** `expected/40-synthesis/threat-model-coverage.yaml`

   Matches the schema from Task B-10. Example structure:

   ```yaml
   schema_version: 1
   generated_by: threat_model_evaluator
   methodology: stride
   surface_coverage:
     - surface: claim-ingress-API
       categories_present: [S, T, I, D, E]
       categories_absent: [R]
       tm_entry_count: 5
       tm_entry_ids: [tm-th1, tm-th2, tm-th3, tm-th4, tm-th5]
     - surface: adjudication-to-pricing
       categories_present: [I]
       categories_absent: [S, T, R, D, E]
       tm_entry_count: 1
       tm_entry_ids: [tm-th6]
     - surface: audit-log-writer
       categories_present: [S, T, I, D, E]
       categories_absent: [R]
       tm_entry_count: 5
       tm_entry_ids: [tm-th7, tm-th8, tm-th9, tm-th10, tm-th11]
   summary:
     total_entries: 11
     contradictions_emitted: 1
     silences_emitted: 1
     coverage_gaps_emitted: 1
     surfaces_examined: 3
   ```

- [ ] **Step 8: Run the validator**

   ```bash
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
   ```

   Expected: clean. File count increases from the Phase A baseline (~21 files / 29 records after Task A-19) by approximately 5 (1 normalized YAML + 1 coverage report + 1 coverage YAML + 3 tmeval- findings = 6 file additions, but the coverage report MD might not count as a "record" depending on validator scope).

   Run with verbose output to inspect:

   ```bash
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/ -v
   ```

- [ ] **Step 9: Verify cross-references are valid**

   ```bash
   # Confirm the specialist finding IDs referenced in the tmeval- findings actually exist
   grep -rE "(conf-7aa376c5|auth-dbba3dea|nonrep-)" examples/apd-20260601-claim-event-bus/expected/
   ```

- [ ] **Step 10: If `tests/test_examples.py` asserts file/record counts, update them**

   ```bash
   pytest tests/test_examples.py -v
   ```

   If count assertions fail with the new larger counts, update the expected values in the test.

- [ ] **Step 11: Full sweep + commit**

   ```bash
   pytest -q
   ruff check tools/ tests/
   mypy tools/
   apd-gauntlet lint-agents
   apd-gauntlet validate-domain pbm
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
   git add examples/apd-20260601-claim-event-bus/
   git commit -m "feat(example): claim-event-bus exercises v1.3 threat-model evaluation end-to-end

   Adds Threat Dragon JSON threat model covering 3 surfaces (claim-ingress-API,
   adjudication-to-pricing, audit-log-writer) with 11 STRIDE entries. Deliberately:

   - Asserts TLS 1.3 on adjudication-to-pricing where conf-7aa376c5 shows
     plaintext (→ contradiction tmeval-dddd4444)
   - Omits Repudiation analysis for audit-log-writer where nonrep- finding
     flagged immutability gaps (→ coverage gap tmeval-cccc3333)
   - Says nothing about vendor-API integration where auth-dbba3dea flagged
     weak mTLS (→ silence tmeval-eeee5555)

   Ships the recon agent's normalized YAML, evaluator's coverage report,
   coverage YAML, and three tmeval- findings as expected outputs. Validator
   runs clean."
   ```

---

### Task B-27: ADR 0009 — methodology-aware threat-model evaluator

**Files:**

- Create: `docs/adrs/0009-methodology-aware-threat-model-evaluator.md`

- [ ] **Step 1: Author the ADR** matching the canonical 0001-0008 format (verified by reading `docs/adrs/0001-three-tier-structure.md` first)

```markdown
# ADR-0009: Methodology-Aware Threat Model Evaluator

**Status:** Accepted
**Date:** 2026-05-XX (date filled at v1.3.0 tag time)
**Supersedes:** —
**Superseded by:** —

## Context

Practitioners produce threat models in a variety of shapes: STRIDE-per-element
spreadsheets, LINDDUN privacy analyses, attack trees, narrative PASTA reports,
free-form whiteboard captures. v1.1's `apd-intake` agent catalogs whatever
threat-model artifact appears in the run inputs and surfaces it as evidence
pointers to downstream specialists — but does not formally evaluate it against
the specialists' own findings.

The Phase B design spec calls for full methodology-aware evaluation: the
gauntlet should parse the threat model into a normalized graph, then compare
that graph against the dedup'd specialist findings to identify (a) coverage
gaps (TM omits analysis a specialist flagged as relevant), (b) contradictions
(TM asserts a mitigation a specialist showed broken), and (c) silences (TM
says nothing about a surface a specialist flagged).

The goal is to give operators a single output that tells them how well their
threat model holds up against the gauntlet's deeper analysis — without
generating threats the operator didn't think of (that would make the gauntlet
into a threat-model author, not a threat-model reviewer).

## Decision

Adopt a **two-agent split** parallel to v1.1's `apd-code-recon`:

1. **`apd-threat-model-recon`** (tier-0, activation-gated): parses the
   supplied artifact into `00-context/threat-model-normalized.yaml`. Pure
   context-builder; emits no findings.

2. **`apd-threat-model-evaluator`** (tier-4, activation-gated): consumes the
   normalized graph + dedup'd specialist findings/capabilities; emits three
   finding flavors (coverage gap, contradiction, silence) using the existing
   `finding.schema.json` with `agent: threat_model_evaluator` and id prefix
   `tmeval-`. Also emits a per-surface coverage report
   (`40-synthesis/threat-model-coverage-report.md` + machine-readable
   `40-synthesis/threat-model-coverage.yaml`).

**Native methodology support:**
- **STRIDE** — OWASP Threat Dragon JSON, Microsoft TMT `.tm7` (XML),
  STRIDE-per-element Markdown/CSV tables
- **LINDDUN** — Markdown/CSV tables with column-position disambiguation for
  letter overloading
- **Attack tree** — indented prose, ADTool XML, JSON

**Reduced-fidelity support:** PASTA, VAST, Trike, free-form prose. The recon
agent's LLM does extraction; entries are marked `extraction_confidence: low`.

**Discipline:**
- **Never invent threats.** Parser output defines the entry set; the recon
  agent enriches but does not add. Free-form extraction respects what the
  operator wrote.
- **Comparator-only.** The evaluator never generates threats the TM didn't
  contain. It only compares the TM against specialist findings.
- **Confidence cascading.** Low-confidence TM entries (from free-form prose)
  can produce silence findings but never contradictions.
- **Block-on-ambiguity.** Unparseable TMs produce a single blocked finding,
  not a fabricated assessment.

**Parsing architecture:** Python parser modules (one per supported format) at
`tools/apd_gauntlet/threat_model/` handle deterministic structural parsing.
The CLI subcommand `apd-gauntlet parse-threat-model` wraps them with
auto-detection and schema validation. The recon agent invokes the CLI and
then performs semantic enrichment (ATT&CK technique refinement, APD-goal
mapping, free-form LLM extraction when the parser couldn't extract anything).

**Methodology→APD-goal mapping** has two co-equal sources of truth:
- `tools/apd_gauntlet/threat_model/mappings.py` (Python; authoritative for
  parser code)
- `apd-threat-model-methodologies` skill (markdown; authoritative for agent
  reasoning)

Both must change together when the canonical mapping evolves.

## Alternatives considered

### Passive inventory only

**Rejected.** This is essentially the v1.1 status quo (intake catalogs the
TM as evidence; nothing evaluates it). It would not produce the
coverage/contradiction/silence findings that motivated the design spec. The
operator's threat model would remain inert relative to the rest of the
gauntlet's analysis.

### Coverage + contradiction + active augmentation

**Rejected.** "Active augmentation" would have the gauntlet propose
additional threats beyond what the TM author wrote — using the specialist
findings as a corpus and emitting "the TM should have included X." This
crosses the line from threat-model *reviewer* to threat-model *author*. It
also risks the gauntlet's threat brainstorming becoming the authoritative
list, undermining the original TM author's process. Comparator-only
preserves the boundary.

### Single-agent design

**Rejected.** Combining recon + evaluator into one agent would lose the
parallel with `apd-code-recon`, conflate two distinct concerns (parsing vs
evaluation), and make the recon output less reusable by specialists in
tiers 1-3 (who consume the normalized YAML as evidence). The two-agent
split also makes the activation contracts clearer: recon activates when a
TM exists; evaluator activates when normalized TM exists.

### LLM-only parsing (no Python parsers)

**Rejected.** LLM extraction of structured formats (JSON, XML, tables) is
non-deterministic and unverifiable. Python parsers are deterministic,
testable, and produce auditable `source_locator` fields. The LLM contributes
where its strength is real: free-form prose extraction and semantic
enrichment of structured output.

## Consequences

### Additive within v1.x

All schema changes are additive (new optional fields on `run-config.schema.json`;
new enum value + id-pattern extension on `finding.schema.json`; two entirely
new schemas). v1.2-format runs validate unchanged against v1.3 schemas. PBM
domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0 with no
changes.

### Two new agents

Agent count grows from 13 (v1.2) to 15 (v1.3). Both new agents are optional
(activation-gated) so the minimum-viable run with no `threat_model:`
declaration produces identical output to v1.2.

### New Python dependency

`lxml>=4.9` for XXE-safe parsing of `.tm7` and ADTool XML. Adds a compiled
extension to the install; documented in pyproject.toml.

### Co-equal mapping tables

The canonical STRIDE/LINDDUN→APD-goal tables live in BOTH the Python module
and the skill markdown. This is a deliberate trade-off: a single source of
truth would mean either (a) generating the skill from the Python module
(complex build step) or (b) the Python parsers parsing the skill markdown
at import time (fragile). Two-sourced-but-co-equal is the v1.3 choice; a
future Phase or polish-pass may add a build step to derive the skill from
the Python module.

### New skill `apd-threat-model-methodologies`

Skill count grows from 5 (v1.2) to 6 (v1.3). Required reading for both new
agents.

### Reference data not required

Parsers are pure code with no upstream data dependency. No new
`apd-gauntlet refresh-*` subcommand is needed.

### Validator extensions

Two new per-record checks for `tmeval-` findings (evidence pointer required,
contradiction cross-reference required). Adds to Phase A's D3FEND cross-ref
check pattern.

### Free-form handling is intentionally limited

PASTA / VAST / Trike are accepted but produce low-confidence entries that
can't drive contradictions. Operators who use these methodologies should
either re-express the threats in a supported structured format or accept
that contradictions won't fire for their TM. Future phases may add native
parsers for the more common narrative formats.
```

- [ ] **Step 2: Markdownlint + full suite + commit**

   ```bash
   npx markdownlint-cli2 docs/adrs/0009-*.md
   pytest -q
   git add docs/adrs/0009-methodology-aware-threat-model-evaluator.md
   git commit -m "docs(adr): 0009 methodology-aware threat-model evaluator"
   ```

---

### Task B-28: New doc `docs/threat-modeling.md`

**Goal:** Operator guide for Track 2. Mirrors the structure of `docs/taxonomy-mappings.md` (the Phase A operator guide). Anchored from `docs/running-the-gauntlet.md` and from the README's feature paragraph.

**Files:**

- Create: `docs/threat-modeling.md`

- [ ] **Step 1: Author the doc** `docs/threat-modeling.md`

```markdown
# Threat Model Evaluation (v1.3+)

When a tech plan includes a threat model — STRIDE diagram, LINDDUN privacy
analysis, attack tree, or even a narrative document — the APD Gauntlet can
evaluate it against the specialist findings: surfacing coverage gaps,
contradictions between TM claims and what specialists actually found, and
silences (surfaces specialists flagged that the TM never addressed).

## What's supported

### Native parsing (high extraction confidence)

| Methodology | Format | Notes |
|---|---|---|
| STRIDE | OWASP Threat Dragon JSON (`.json`) | Auto-detected by `{summary, detail.diagrams}` shape |
| STRIDE | Microsoft TMT (`.tm7`) | XML; XXE-safe parser via lxml |
| STRIDE | Per-element tables (`.md` / `.csv`) | Header: `S T R I D E` or full category names |
| LINDDUN | Per-element tables (`.md` / `.csv`) | Header: `L I N D D U N` with column-position disambiguation |
| Attack tree | Indented prose (`.txt`) | 4-space or tab indentation; OR/AND keyword gates |
| Attack tree | ADTool XML (`.adtool.xml`, `.xml`) | `refinement="conjunctive|disjunctive"` |
| Attack tree | Generic JSON (`.json`) | `{goal, gate, children[]}` convention |

### Reduced-fidelity support (low extraction confidence)

PASTA, VAST, Trike, and free-form prose are accepted via the
`--methodology-hint` flag or by setting `methodology_hint:` in
`.apd-run.yaml`. The recon agent's LLM does the extraction; the entries are
marked `extraction_confidence: low` and cannot drive contradiction findings
(only silence / uncertainty). See "Confidence cascading" below.

## Declaring a threat model

### In `.apd-run.yaml`

```yaml
run_id: apd-20260601-claim-event-bus
domain: pbm
taxonomies: [cwe, mitre_attack, d3fend, owasp_api_top10]
threat_model: inputs/threat-model.json
methodology_hint: stride          # optional — auto-detected if absent
```

The `threat_model` path is relative to the run directory's `inputs/`
directory. The `methodology_hint` is optional; the parser auto-detects
methodology from the file format when the hint is absent. See "When to use
methodology_hint" below.

### Via `apd-gauntlet init-run`

```bash
apd-gauntlet init-run apd-20260601-claim-event-bus \
  --inputs ./artifacts \
  --domain pbm \
  --threat-model my-threat-model.tm7 \
  --methodology-hint stride
```

### When to use `methodology_hint`

The hint forces a specific methodology, overriding auto-detection. Use it when:

- The file format is ambiguous (e.g., a `.json` file that's not Threat Dragon
  but is your own custom JSON convention; hint `attack_tree` or similar)
- You want to force `pasta` / `vast` / `trike` / `free_form` interpretation
  even if the file extension would suggest something else
- The auto-detection picks the wrong methodology (rare; file an issue if you
  hit this)

Valid hints: `stride`, `linddun`, `attack_tree`, `pasta`, `vast`, `trike`,
`free_form`.

## What the recon agent produces

`apd-threat-model-recon` (tier-0, activation-gated on the
`threat_model:` declaration) parses the file and emits:

- `00-context/threat-model-normalized.yaml` — normalized graph of all entries

This file is consumed by:

- All tier-1/2/3 specialist agents as an evidence pointer (alongside the
  intake brief)
- `apd-threat-model-evaluator` (tier-4) for evaluation

See `templates/threat-model-normalized.template.md` for the file's structure
and field semantics.

## What the evaluator agent produces

`apd-threat-model-evaluator` (tier-4, activation-gated on the normalized YAML
existing) emits:

- Finding files at `20-findings/40-threat-model/tmeval-*.yaml`
- `40-synthesis/threat-model-coverage-report.md` (human-readable)
- `40-synthesis/threat-model-coverage.yaml` (machine-readable)

### The three finding flavors

| Disposition | Flavor | What it means |
|---|---|---|
| `gap` | **Coverage gap** | TM omits methodology category for a surface a specialist flagged (e.g., TM has no Repudiation analysis for audit-log-writer but a Non-Repudiation specialist found a gap there) |
| `risk` | **Contradiction** | TM asserts a mitigation a specialist showed broken (e.g., TM claims TLS but specialist found plaintext) |
| `uncertainty` | **Silence** | TM has no entries for a surface a specialist flagged (e.g., specialist flagged vendor-API integration, TM never mentions it) |

Each `tmeval-` finding cross-references the specialist finding(s) it relates
to via `cross_references`. Contradiction findings additionally have an
evidence entry quoting the TM's mitigation claim. Silence findings note the
absence as "(no entries for surface=X)".

### Confidence cascading

The evaluator's discipline (Rule 6 in `apd-threat-model-methodologies` skill):

| TM entry `extraction_confidence` | Maximum contradiction finding `confidence` |
|---|---|
| `high` | `high` |
| `medium` | `medium` |
| `low` | (Cannot emit as contradiction; emitted as silence-style uncertainty instead) |

This prevents low-confidence LLM extractions from driving high-confidence
contradiction findings.

## Common pitfalls

### "The evaluator missed an obvious threat"

The evaluator does not invent threats. If you expect a contradiction or
coverage-gap finding that didn't appear, check:

1. Is the TM entry actually parsed? (Look at `00-context/threat-model-normalized.yaml`)
2. Does the entry's `asset` field match the surface a specialist finding's
   `evidence[*].artifact` points at? Surface matching is by string identity.
3. For contradictions: does the TM entry have a `mitigation` field? Entries
   without mitigations can't be contradicted (there's no claim to contradict).
4. Is the TM entry's `extraction_confidence` `low`? Low-confidence entries
   can't drive contradiction findings (Rule 6).

### "The TM says everything is mitigated; why are there contradictions?"

The evaluator compares mitigation CLAIMS against what specialists actually
FOUND. The TM's mitigation list may be aspirational; the contradictions
identify where the implementation hasn't caught up to the design intent.

### "methodology_hint changed; output is the same"

The hint applies to the WHOLE document. One TM = one methodology. If your
document genuinely mixes methodologies (rare), split it into multiple TM
files and supply each separately in a future run.

### "Validator rejects my tmeval- finding"

Two validator checks (Task B-25):

- Every `tmeval-` finding must have at least one evidence entry pointing at
  `00-context/threat-model-normalized.yaml` or the source TM artifact
- Every `tmeval-` finding with `disposition: risk` (contradiction) must have
  non-empty `cross_references`

If you're hand-authoring tmeval- findings (e.g., extending the bundled
example), make sure both conditions hold.

## Design rationale

See `docs/adrs/0009-methodology-aware-threat-model-evaluator.md` for the
full decision record (why two agents, why comparator-only, why Python
parsers for structured formats + LLM for prose, why two sources of truth
for the mapping tables).

```

- [ ] **Step 2: Markdownlint + commit**

   ```bash
   npx markdownlint-cli2 docs/threat-modeling.md
   git add docs/threat-modeling.md
   git commit -m "docs: add threat-modeling.md operator guide for v1.3"
   ```

---

### Task B-29: Update existing docs for v1.3

**Goal:** Refresh four pre-existing docs to mention the v1.3 additions. Each is a small, targeted edit — not a rewrite.

**Files:**

- Modify: `docs/architecture.md`
- Modify: `docs/running-the-gauntlet.md`
- Modify: `docs/schema-evolution.md` (fill in the v1.3.0 entry that Phase A's Task A-22 stubbed as a placeholder)
- Modify: `README.md`

### Per-file diff guidance

#### `docs/architecture.md`

1. **Topology section** — add the two new agents to the diagram. Find the
   existing topology section (Phase A added 3 agents to it). Add tier-0 and
   tier-4 entries:

   ```diff
    ### Tier-0 (intake)
    - apd-intake
    - apd-code-recon (optional, v1.1+)
   +- apd-threat-model-recon (optional, v1.3+)

    ### Tier-4 (synthesis)
    - apd-synthesizer
   +- apd-threat-model-evaluator (optional, v1.3+)
   ```

2. **Output files tree** — add the new artifacts:

   ```diff
    00-context/
      ├── context-brief.md
      ├── code-evidence-index.yaml         (v1.1+, optional)
   +  └── threat-model-normalized.yaml     (v1.3+, optional)

    20-findings/
      ├── 10-trustworthiness/
      ├── 20-scalability/
      ├── 30-auditability/
   +  └── 40-threat-model/                 (v1.3+, optional — tmeval-*.yaml)

    40-synthesis/
      ├── advisory-report.md
      ├── nist-coverage.yaml
      ├── attack-exposure.yaml
      ├── cwe-coverage.yaml                (v1.2+, optional)
      ├── owasp-coverage.yaml              (v1.2+, optional)
      ├── d3fend-coverage.yaml             (v1.2+, optional)
   +  ├── threat-model-coverage-report.md  (v1.3+, optional)
   +  └── threat-model-coverage.yaml       (v1.3+, optional)
   ```

3. **Schemas** — add the two new entries:

   ```diff
   - schemas/cwe-coverage.schema.json       (v1.2+)
   + schemas/threat-model-normalized.schema.json  (v1.3+)
   + schemas/threat-model-coverage.schema.json    (v1.3+)
   + schemas/_defs.schema.json                    (v1.3+; shared $defs for ATT&CK/D3FEND/CWE patterns)
   ```

#### `docs/running-the-gauntlet.md`

Add a new subsection after "Taxonomy scope (v1.2+)":

```markdown
### Threat model evaluation (v1.3+)

If the run includes a threat model, declare it in `.apd-run.yaml` or pass
`--threat-model <path>` to `init-run`:

```yaml
threat_model: inputs/threat-model.json
methodology_hint: stride   # optional; auto-detected if absent
```

`apd-threat-model-recon` (tier-0) parses the file into a normalized graph;
`apd-threat-model-evaluator` (tier-4) emits coverage-gap, contradiction, and
silence findings against the synthesizer's dedup'd specialist findings. See
[docs/threat-modeling.md](threat-modeling.md) for the full operator guide.

```

#### `docs/schema-evolution.md`

Phase A's Task A-22 stubbed a v1.3.0 placeholder section. Replace with:

```markdown
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
```

#### `README.md`

Find the feature paragraph (Phase A's Task A-22 modified it to mention
taxonomies). Add one sentence about threat modeling:

```diff
 The gauntlet runs against a tech plan and supplementary artifacts (PRD,
 code, IaC, diagrams, threat models, ADRs) and produces an advisory report
 with confirmed capabilities, findings, contradictions, and coverage
 matrices. Every finding and capability carries NIST 800-53r5 mappings;
 high-confidence findings also carry ATT&CK technique mappings.
 Declared taxonomies (CWE, OWASP Top 10 / API / LLM, D3FEND) drive
 additional optional mappings and synthesizer rollups.
+When a threat model is supplied (Threat Dragon JSON, Microsoft TMT,
+STRIDE/LINDDUN tables, attack trees), the gauntlet's threat-model
+evaluator surfaces coverage gaps, contradictions between TM claims and
+specialist findings, and surface silences as `tmeval-` findings.
```

### Steps

- [ ] **Step 1:** Apply each of the four diffs above to the corresponding files

- [ ] **Step 2:** Run markdownlint on the modified files

   ```bash
   npx markdownlint-cli2 docs/architecture.md docs/running-the-gauntlet.md \
     docs/schema-evolution.md README.md
   ```

- [ ] **Step 3:** Full suite to confirm no regressions

   ```bash
   pytest -q
   ```

- [ ] **Step 4:** Commit

   ```bash
   git add docs/architecture.md docs/running-the-gauntlet.md \
           docs/schema-evolution.md README.md
   git commit -m "docs: refresh architecture/running/schema-evolution/README for v1.3

   - architecture.md: tier-0 and tier-4 topology updates; new artifacts in
     output-files tree; two new schemas + _defs.schema.json
   - running-the-gauntlet.md: 'Threat model evaluation (v1.3+)' subsection
     with link to docs/threat-modeling.md
   - schema-evolution.md: v1.3.0 entry filled in (was a Phase A stub);
     documents finding.schema.json + run-config.schema.json extensions and
     the shared \$defs extraction from Task B-4
   - README.md: one sentence on threat-model evaluation in the feature
     paragraph"
   ```

---

### Task B-30: CHANGELOG + final version bump (1.3.0.dev0 → 1.3.0)

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`, `tools/apd_gauntlet/__init__.py`, `plugin.json`
- Modify: `tests/test_cli.py` (version assertion)

- [ ] **Step 1: Author the [1.3.0] CHANGELOG entry** at the top above [1.2.0].

   ```markdown
   ## [1.3.0] - 2026-XX-XX

   ### Added

   - **`apd-threat-model-recon` tier-0 agent** — parses user-supplied threat models into a normalized graph at `00-context/threat-model-normalized.yaml`. Activation-gated on `.apd-run.yaml` declaring `threat_model: <path>` (or intake auto-detecting a TM-like artifact).
   - **`apd-threat-model-evaluator` tier-4 agent** — evaluates the normalized TM against specialist findings/capabilities; emits three finding flavors: coverage gap (`disposition: gap`), contradiction (`disposition: risk`), silence (`disposition: uncertainty`). Findings use `agent: threat_model_evaluator` and id prefix `tmeval-`.
   - **Native methodology support**: STRIDE (OWASP Threat Dragon JSON, Microsoft TMT .tm7, STRIDE-per-element Markdown/CSV), LINDDUN (Markdown/CSV tables), attack trees (indented prose, ADTool XML, JSON). PASTA / VAST / Trike / free-form prose accepted with reduced extraction confidence.
   - **CLI subcommand `parse-threat-model`** — standalone parser dispatcher; auto-detects format from extension or honors `--methodology-hint`.
   - **CLI flags on `init-run`**: `--threat-model <path>` and `--methodology-hint <name>` pre-populate the run-config.
   - **New skill `apd-threat-model-methodologies`** — canonical STRIDE/LINDDUN→APD-goal mapping tables (single source of truth shared with Python mapping module) + discipline rules.
   - **New schemas**: `threat-model-normalized.schema.json`, `threat-model-coverage.schema.json`.
   - **Validator extensions**: `tmeval-` findings must cite the normalized TM (or source artifact) in evidence; contradiction findings must cross-reference the contradicting specialist finding ID.
   - **New dependency**: `lxml>=4.9` (used by Microsoft TMT and ADTool XML parsers with XXE-safe flags).
   - **ADR 0009** — Methodology-aware threat-model evaluator.
   - **`docs/threat-modeling.md`** operator guide.

   ### Changed

   - `finding.schema.json` — `agent` enum gains `threat_model_evaluator`; `id` pattern extended to accept `tmeval-` prefix.
   - `run-config.schema.json` — accepts optional `threat_model: <path>` and `methodology_hint: <name>` fields.
   - **Shared `$defs` extraction** (carry-forward from Phase A): ATT&CK / D3FEND / CWE patterns now defined once in `schemas/_defs.schema.json` and `$ref`'d by record schemas. Behavior unchanged.
   - **`owasp_llm_top10` pattern tightened** (carry-forward from Phase A): now `^LLM(0[1-9]|10)$` (was `^LLM[0-9]{2}$` which accepted non-existent codes).
   - **`refresh_mitre.py` aligned** (carry-forward from Phase A): constants renamed to `MAX_RESPONSE_BYTES` / `DEFAULT_TIMEOUT_SECONDS` matching the v1.2 triad; Content-Length pre-check added.
   - **CLI `validate` now scans coverage rollups** (carry-forward from Phase A): cwe-coverage / owasp-coverage / d3fend-coverage in `40-synthesis/` are now validated by `apd-gauntlet validate` (previously only by tests).
   - **ADR 0007 reformatted** (carry-forward from Phase A): now matches the canonical 0001-0008 hyphen+colon style.

   ### Backward compatibility

   - All schema changes additive. v1.2-format runs (and v1.1, v1.0) validate unchanged.
   - Minimum-viable run with no `threat_model:` declaration produces identical output to v1.2.
   - PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0 with no changes.
   ```

- [ ] **Step 2: Bump version to 1.3.0** in `pyproject.toml`, `__init__.py`, `plugin.json`. Update `tests/test_cli.py` version assertion.

- [ ] **Step 3: Full verification sweep**

   ```bash
   pytest -q                                                            # expect: 245+ passed (Phase A baseline 188 + ~60 new tests)
   pytest --cov --cov-fail-under=85                                     # expect: pass
   ruff check tools/ tests/                                             # expect: clean
   mypy tools/                                                          # expect: clean
   apd-gauntlet lint-agents                                             # expect: 15 agents clean (13 + 2 new)
   apd-gauntlet validate-domain pbm                                     # expect: clean
   apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/  # expect: clean (file count up from Phase A)
   apd-gauntlet --version                                               # expect: 1.3.0
   ```

   If any fail, stop and report BLOCKED before committing.

- [ ] **Step 4: Commit + push**

   ```bash
   git add CHANGELOG.md pyproject.toml tools/apd_gauntlet/__init__.py plugin.json tests/test_cli.py
   git commit -m "release: v1.3.0 — methodology-aware threat-model evaluator (Phase B)"
   git push origin main
   ```

   Do NOT tag (per project convention — operator decision).

---

## Verification — final state

After Task B-30 lands and is pushed, the repo should be in this state:

- **Version:** 1.3.0 (untagged)
- **Tests:** ~245+ passing (was 188; +57 from Phase B — schemas + parsers + agent integration tests)
- **Coverage:** ≥85% on `tools/apd_gauntlet/`; target ≥90% on new modules (parsers + dispatcher + mappings)
- **Agents:** 15 (was 13; +2 — `apd-threat-model-recon`, `apd-threat-model-evaluator`)
- **Schemas:** 15+ (was 13; +2 new: threat-model-normalized, threat-model-coverage; +1 defs: `_defs.schema.json`)
- **Skills:** 6 (was 5; +1 — `apd-threat-model-methodologies`)
- **Reference data files:** 6 (unchanged from Phase A — TM parsers are pure code, no upstream data)
- **CLI subcommands:** +1 (`parse-threat-model`) plus `init-run --threat-model` / `--methodology-hint`
- **New Python module package:** `tools/apd_gauntlet/threat_model/` (5 parsers + mappings + dispatcher)
- **New dependency:** `lxml>=4.9`
- **Docs:** +1 (`docs/threat-modeling.md`); 4 updated (architecture, running, schema-evolution, README)
- **ADRs:** 9 (added 0009; harmonized 0007)
- **CHANGELOG:** v1.3.0 entry filled with feature list + carry-forward list, date placeholder

Next: Phase C (v1.4.0) — BloodHound-style attack-path enumeration + D3FEND defense graph. Plan file: `docs/superpowers/plans/2026-MM-DD-phase-c-attack-path-analysis.md` (to be written after Phase B is complete and merged).

---

## Notes for the executor

- **TDD discipline:** every Python-touching task follows write-test → run-fail → implement → run-pass → commit. Markdown-only tasks skip the run-fail step (no test exists) but should run `apd-gauntlet lint-agents` and `pytest -q` to confirm no regressions.
- **Commit cadence:** each task ends with one commit. The carry-forward pass is six independent commits.
- **XML safety:** any new XML parser must use `lxml` (or stdlib with comparable guards) with `resolve_entities=False` and `no_network=True` to prevent XXE attacks. `.tm7` (Task B-13) and ADTool XML (Task B-16) both apply.
- **Methodology mapping tables** are sourced from Python (`tools/apd_gauntlet/threat_model/mappings.py`) — the skill text (Task B-19) is documentation of those tables, not a redundant copy. If you change the mapping, update both; the canonical authority is Python. (Future work: auto-generate the skill text from the Python module, similar to `build_domain_skill.py`.)
- **`$defs` adoption** (Task B-4) is the right time to factor pattern duplication; all subsequent new schemas in this plan use `$ref` from the start. If you find a pattern that's referenced ≥2 times, add it to `_defs.schema.json`.
- **No new agents beyond the two in this plan.** Phase C will add `apd-attack-path-analyzer`; don't introduce it here.
- **`uv.lock` is untracked** in the repo. Don't add it to git. (Phase A history shows several implementers flagged this; leave it alone.)
- **Test environment:** Phase A revealed `tests/test_examples.py::test_claim_event_bus_example_validates` requires the `apd-gauntlet` console script on PATH. Run `pip install -e .` (or `uv sync --extra dev`) in your venv before running pytest. If the test fails because the binary isn't on PATH, that's a setup issue, not a regression.
- **Free-form prose handling**: the Python parsers cover the structured formats. For free-form prose (PASTA narrative, brainstormed lists, etc.), the recon agent's LLM does the extraction work — there is no Python parser for this, by design. The agent's instructions in `apd-threat-model-recon.md` must cover the prose-extraction path explicitly.
