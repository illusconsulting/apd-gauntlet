# CAT1 — Threat Catalog Data, Loader and Editions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the 2.0 line a validated, licence-safe threat catalog (the vendored 1.1.0 release as `open`, and an optional operator-supplied local file as `full`) behind the `threat_catalog` run-config key, and align the gauntlet's OWASP editions with the catalog's: Top 10 2025, and LLM Top 10 2025 with year-qualified ids.

**Architecture:** A new `apd_gauntlet.catalog` package has four core modules (plus `alignment` for the CI guards and `doctor` for LA3). `config` parses the run-config key and the selection parameters. `load` runs the seven §12.1 checks and loads a catalog with edition fallback. `model` holds frozen `Threat` and `Catalog` records with no `source`, `stub` or HITRUST field. `translate` maps catalog vocabularies to the gauntlet's. `refresh-threat-catalog` vendors a pinned open release the way the `refresh-*` commands vendor KBs. Separately, the OWASP KBs and the `apd-control-mappings` skill move to 2025. `canonicalize` qualifies bare LLM ids on 2.0 runs, and rollups mark older ids. `compare-runs` translates 2021 Top 10 ids and refuses to compare LLM ids across the 2.0 boundary.

**Tech Stack:** Python 3.10+, click, PyYAML, jsonschema (Draft 2020-12), stdlib `hashlib`/`json`/`fnmatch`/`subprocess`/`tempfile`; pytest with `click.testing.CliRunner`; synthetic catalog fixtures. No new dependencies.

**Spec:**

- `docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md`:
  - §6, §7 (the `threat_catalog` key) and §8 (`config`, `load`, `model`, `translate`);
  - §10, §12.1 and §12.3 (the CI tests, and the loader's part of the HITRUST check);
  - §13 rows 1–3.
- `docs/superpowers/plans/2026-10-10-program-master-plan.md`: R1 (`refresh-threat-catalog`), R2 (`apd_gauntlet.catalog`), R4, R7, R8, R10 (ADR-0030), §A3, and Task 6 Step 2a.
- The CAT brief's fixed cross-plan interfaces.

This is plan CAT1 of four (WS10).

**Amended 2026-10-17** per the amendments register (A7.25, A7.26, A7.27, A7.28, A7.29, A7.30, A7.31, A7.32, A7.33, A7.34, A7.35, A7.36, A7.37, A7.38, A7.51, A7.52, A7.59, A7.60, A7.61, A7 anchors after WS1, A10.3, A14.1, A15.18).

## Global Constraints

- Ships on `next`. CHANGELOG bullets go under ``## Unreleased — 2.0 line (`next`)``. "Decided 2026-10-11: it is fixed on 2.0 only (CAT1, §10). 1.7.x keeps the 2023 list and skill text."
- "CI never touches the network" (ADR-0017). `illusconsulting/threat-catalog` has published no release yet, so every test uses the synthetic fixtures under `tests/fixtures/threat_catalog/`. Vendoring the real open file is Task 14 (operator).
- A `full` file is an operator-supplied local catalog in the release schema (A7). It is never committed, vendored or copied into a run, and it validates against the vendored `open.schema.json` exactly as the vendored file does. There is no second schema.
- Release contract: tag `v<X.Y.Z>`, with assets `threat-catalog-X.Y.Z.json`, `threat-catalog.schema.json` and `SHA256SUMS`. Downloads are anonymous unless the variable named by `--token-env` (default `GITHUB_TOKEN`) is set. The token is then sent only to `github.com`, `api.github.com` and `objects.githubusercontent.com`.
- Confirmed catalog id formats:
  - `owasp_top10` ids are `Ann:2025`;
  - `owasp_llm_2025` ids are `LLMnn:2025`;
  - `maestro` ids are `L1`–`L7` plus `CL` (cross-layer);
  - `frameworks[].version` is a free-form string, compared by exact string only where the KB records an edition or version, and otherwise reported as unversioned.
- No HITRUST content (A7): the loader refuses any key containing `hitrust` and any per-threat `source` or `stub` key in either edition, and any `hitrust` text in the vendored file. `model.py` has no `source`, `stub` or lineage field.
- `threat_catalog` (R4): "`off | open | full`, or an object with `edition`, `path`, `system_types`, `exclude_system_types`".
  - "Absent means the release default: `off` until CAT4 passes, then `open`." CAT1 ships `DEFAULT_EDITION = "off"`; only CAT4 changes it.
  - "`edition: full` without a readable, valid file falls back to `open` and writes a warning … it never fails the run."
  - A vendored file that fails validation is different: "CI fails; a run with `open` exits at `catalog-scope` with the validation error".
- Until Task 14, `data/threat-catalog/open.json` is not committed. The `open` edition then reports "vendored catalog not installed", and downstream steps behave as `off` (CAT brief).
- §12.1 load checks, in order:
  1. at most 20 MB;
  2. JSON;
  3. no HITRUST content: no key containing `hitrust` (any case, any depth), and no per-threat `source` or `stub` key; for the vendored file, also no string value containing `hitrust`;
  4. validates against the vendored `open.schema.json`;
  5. ids are unique and well formed, `parent`, `children` and `related` resolve, and `catalog.counts.threats` and `.families` equal the array lengths;
  6. version within `compat.yaml`;
  7. for the vendored file, the SHA-256 matches `open.provenance.json`.
- Full path (§6.4): "The loader refuses a path inside the installed package or the run directory, and warns when the path is inside a git working tree and not ignored."
- `selection.yaml`, version 1:
  - `top_n` 3, `max_per_family` 2, `shortlist_cap` 40 and `silence_cap` 15;
  - `exclude_families` `[EN, FA, CF, PH, LG]`;
  - truncation at 160 characters in shortlists and 400 in candidates.
- LINDDUN translation (§8.6): `L→L`, `I→I`, `Nr→N_repudiation`, `D→D_etectability`, `DD→D_isclosure`, `U→U`, `Nc→N_compliance`.
- §8.6 taxonomy table:
  - `attack_enterprise` and `attack_mobile` → `mitre_attack` (`mitre-attack-techniques.json`);
  - `atlas` → `atlas` (`atlas-techniques.json`);
  - `cwe` → `cwe` (`cwe.json`);
  - `owasp_top10` → `owasp_top10` (`owasp_top10.json`);
  - `owasp_api` → `owasp_api_top10` (`owasp_api_top10.json`);
  - `owasp_llm_2025` → `owasp_llm_top10` (`owasp_llm_top10.json`);
  - `maswe` → `maswe` (`maswe.json`);
  - `capec` → `capec` (`capec.json`);
  - controls `nist_800_53` → `nist_800_53r5` (`nist-controls.json`);
  - controls `d3fend` → `d3fend` (`d3fend.json`).
- OWASP LLM Top 10 2025: LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM03 Supply Chain, LLM04 Data and Model Poisoning, LLM05 Improper Output Handling, LLM06 Excessive Agency, LLM07 System Prompt Leakage, LLM08 Vector and Embedding Weaknesses, LLM09 Misinformation, LLM10 Unbounded Consumption.
- The OWASP Top 10 2025 ids and names, and the 2021→2025 mapping, are copied from OWASP's published pages (owasp.org/Top10), never from memory, and each file records the URL it was copied from.
- CAT1 edits no workflow or runner file. It adds no phase and no workflow step (master plan: "CAT1 with LA1 … CAT1 edits no workflow or runner file").
- Quality gates: `ruff check tools/ tests/`, `mypy tools/` (strict), `pytest` (coverage `fail_under = 85`) and `markdownlint-cli2` on the linted globs.
- Locate edits by anchor; line numbers predate WS1. The citations of `cli.py`, `canonicalize.py`, `build_domain_skill.py`, `resume_plan.py` and `docs/running-the-gauntlet.md` carry the post-WS1 values of the register's "A7 anchors after WS1" table.

## Review Focus

- **The open edition before Task 14 vendors a release** (`open.json` absent): `load_catalog` returns `None` with `VENDORED_NOT_INSTALLED`, the freshness gate passes, `doctor` warns, and the vendored CI guards skip with that reason. Nothing crashes. Pinned in Task 9 (`test_open_not_installed_returns_none_with_warning`) and Task 11 (`test_sidecar_not_installed_passes`).
- **A full catalog path that is missing, invalid, inside the package or run directory, or inside a git tree without being ignored:** the first four fall back to `open` with a warning naming the cause. The git case loads `full` and warns. None fails the run. Pinned in Task 9 (`test_full_missing_falls_back`, `test_full_inside_run_dir_refused`, `test_full_in_unignored_git_tree_warns`).
- **A bad or tampered release** (hash mismatch, a `hitrust` key or text, a pre-1.1.0 `source`/`stub` field, a version outside `compat.yaml`): `refresh-threat-catalog` exits 1 and leaves the vendored files byte-identical. Pinned in Task 10 (`test_sha_mismatch_writes_nothing`, `test_hitrust_content_refused`, `test_version_outside_compat_refused`) and Task 8 (`test_hitrust_key_refused_in_both_editions`, `test_hitrust_text_refused_in_open_only`).
- **A bare `LLM06` from a 1.7 run beside `LLM06:2025` from a 2.0 run:** canonicalize leaves pre-2.0 runs alone, the rollup marks the bare id `edition: unknown` with both names, and `compare-runs` reports `not_comparable` instead of guessing. Pinned in Task 3 (`test_pre_2_0_run_not_rewritten`), Task 4 (`test_bare_llm_id_edition_unknown_with_both_names`) and Task 5 (`test_llm_not_comparable_across_2_0`).
- **A 1.7 baseline citing 2021 Top 10 ids against a 2.0 candidate citing 2025 ids:** `compare-runs` counts the translated ids as unchanged, not as churn. Pinned in Task 5 (`test_top10_crosswalk_counts_translated_not_churn`).

---

## File Structure

| Path | Responsibility | Action | Task |
|---|---|---|---|
| `tools/apd_gauntlet/catalog/__init__.py` | R2 exports | Create | 1, 7, 9 |
| `tools/apd_gauntlet/catalog/config.py` | `CatalogConfig`, run-config parsing, `SelectionParams`, vocabularies | Create | 1 |
| `tools/apd_gauntlet/catalog/translate.py` | LINDDUN table, taxonomy map, KB ids and versions, NIST normalization | Create | 6 |
| `tools/apd_gauntlet/catalog/model.py` | `MappingRef`, `Threat`, `Catalog`, `build_catalog` | Create | 7 |
| `tools/apd_gauntlet/catalog/load.py` | `validate_catalog_file`, `hitrust_errors`, `reference_errors`, `load_catalog`, local-path rules, `CatalogError` | Create | 8, 9 |
| `tools/apd_gauntlet/catalog/alignment.py` | Catalog mapping ids and framework versions against the KBs | Create | 12 |
| `tools/apd_gauntlet/catalog/doctor.py` | `threat-catalog` doctor check | Create | 13 |
| `tools/apd_gauntlet/owasp_editions.py` | LLM id qualification, 2023 names, Top 10 crosswalk, run framework major | Create | 2 |
| `tools/apd_gauntlet/refresh_threat_catalog.py` | Release fetch with host-scoped token, verification, staging, diff | Create | 10 |
| `tools/apd_gauntlet/measure/taxonomy_delta.py` | OWASP edition-aware taxonomy delta for `compare-runs` | Create | 5 |
| `tools/apd_gauntlet/data/threat-catalog/selection.yaml` | Selection parameters | Create | 1 |
| `tools/apd_gauntlet/data/threat-catalog/owasp-crosswalks.yaml` | OWASP Top 10 2021↔2025 | Create | 2 |
| `tools/apd_gauntlet/data/threat-catalog/{compat,system-types,apd-goals,taxonomy-map}.yaml` | Static catalog data | Create | 6 |
| `tools/apd_gauntlet/data/threat-catalog/open.schema.json` | The release schema, byte-identical | Create | 7 |
| `tools/apd_gauntlet/data/threat-catalog/{open.json,open.provenance.json}` | Vendored release | Create | 14 (operator) |
| `tools/apd_gauntlet/data/owasp_{top10,llm_top10,api_top10}.json` | 2025 seeds; `edition` | Modify | 2 |
| `tools/apd_gauntlet/refresh_owasp.py` | 2025 sources, `edition`, LLM qualification, `write_seed` | Modify | 2 |
| `tools/apd_gauntlet/canonicalize.py`, `tools/apd_gauntlet/cli.py` | Qualify bare LLM ids on 2.0 runs | Modify | 3 |
| `tools/apd_gauntlet/synthesis/rollup.py` | OWASP editions in `owasp-coverage` | Modify | 4 |
| `tools/apd_gauntlet/measure/compare.py` (WS2) | Pair taxonomy deltas, JSON, text, warnings | Modify | 5 |
| `tools/apd_gauntlet/cli.py` | `refresh-threat-catalog`; doctor registration | Modify | 10, 13 |
| `tools/apd_gauntlet/data/schemas/run-config.schema.json` | `threat_catalog` | Modify | 1 |
| `tools/apd_gauntlet/data/schemas/finding.schema.json` | `LLMnn:2025` | Modify | 3 |
| `tools/apd_gauntlet/data/schemas/owasp-coverage.schema.json` | `edition`, `edition_names`, `crosswalked`, `crosswalked_from` | Modify | 4 |
| `tools/apd_gauntlet/data/schemas/_defs.schema.json` | `catalog_threat_id` | Modify | 7 |
| `tools/check_kb_cache_freshness.py` | Sidecar provenance for `threat-catalog/open.json` | Modify | 11 |
| `tools/check_notice_present.py`, `NOTICE` | Attribution for the vendored catalog | Modify | 14 |
| `.claude/skills/apd-control-mappings/SKILL.md` | 2025 OWASP teaching | Modify | 2 |
| `.claude/skills/apd-domain/lens/*.md` | Lens packets rebuilt by `build-lens-skills` (WS5 Task 11) | Modify | 2 |
| `pyproject.toml` | Package data | Modify | 1 |
| `docs/adrs/0030-threat-catalog-enrichment-layer.md` | ADR-0030 | Create | 1 |
| `docs/running-the-gauntlet.md`, `docs/taxonomy-mappings.md`, `docs/schema-evolution.md`, `docs/deterministic-field-register.md`, `docs/measuring-changes.md`, `docs/ci-gate-model.md`, `CHANGELOG.md` | Docs | Modify | per task |
| `tests/fixtures/threat_catalog/{open.json,open.provenance.json,open.schema.json,full.json}` | Synthetic catalog, 1.1.0 shape; `full.json` = `open.json` + `TC-OT-901` | Create | 7 |
| `tests/fixtures/kb_golden/threat_catalog/open.provenance.json` | Refresh golden | Create | 10 |
| `tests/conftest.py` (WS2) | `catalog_fixture_dir` (Task 8), `load_fixture_catalog` (Task 9) | Modify | 8, 9 |
| `tests/test_catalog_*.py`, `tests/test_owasp_*.py`, `tests/test_canonicalize_owasp_llm.py`, `tests/test_rollup_owasp_editions.py`, `tests/test_measure_taxonomy_delta.py`, `tests/test_refresh_threat_catalog.py`, `tests/test_adr_0030.py` | Tests | Create | per task |

---

### Task 1: `threat_catalog` run-config key and `catalog/config.py`

**Files:**

- Create: `tools/apd_gauntlet/catalog/__init__.py`, `tools/apd_gauntlet/catalog/config.py`, `tools/apd_gauntlet/data/threat-catalog/selection.yaml`, `docs/adrs/0030-threat-catalog-enrichment-layer.md`, `tests/fixtures/valid/run-config-with-threat-catalog.yaml`, `tests/fixtures/invalid/run-config-threat-catalog-full-without-path.yaml`
- Modify: `tools/apd_gauntlet/data/schemas/run-config.schema.json` (property after `threat_model`; top-level `$defs`), `pyproject.toml` (`[tool.setuptools.package-data]` gains `"data/threat-catalog/*"`), `docs/running-the-gauntlet.md` (new `### Threat catalog (v2.0+)` after "Taxonomy scope (v1.2+)", `:199-222`), `docs/schema-evolution.md`, `CHANGELOG.md`
- Test: `tests/test_catalog_config.py`, `tests/test_adr_0030.py`, `tests/test_run_config_schema.py` (extend), `tests/test_cli_validate_run_config.py` (extend)

**Interfaces:**

- Produces (`config.py`):
  - `CATALOG_SYSTEM_TYPES: tuple[str, ...]` — the 24 catalog system types in the catalog schema's order: `web_app, api, mobile, endpoint, server, network, cloud, container_k8s, serverless, saas, identity, data_store, ci_cd, ai_ml, agentic_ai, ot_ics, iot_embedded, medical_device, email_messaging, telecom, b2b_integration, physical_facility, people_process, third_party`
  - `CATALOG_FAMILY_CODES: tuple[str, ...]` — `SE, IA, AC, IN, AP, MW, NW, AV, CR, DP, SC, CL, AI, AG, MB, OT, RC, LD, IS, OP, PH, FA, EN, CF, LG`
  - `DEFAULT_EDITION: Literal["off", "open"] = "off"`
  - `@dataclass(frozen=True) class CatalogConfig: edition: Literal["open", "full"]; path: Path | None; system_types: tuple[str, ...]; exclude_system_types: tuple[str, ...]`
  - `def catalog_config_from_run_config(run_cfg: Mapping[str, Any]) -> CatalogConfig | None`
  - `@dataclass(frozen=True) class SelectionParams: version: int; top_n: int; max_per_family: int; shortlist_cap: int; silence_cap: int; exclude_families: tuple[str, ...]; summary_chars_shortlist: int; summary_chars_candidate: int`
  - `def catalog_data_dir() -> Path` → `resources.data_dir() / "threat-catalog"`
  - `def load_selection_params(path: Path | None = None) -> SelectionParams` (default `catalog_data_dir() / "selection.yaml"`)
- `catalog/__init__.py` re-exports the config names; Tasks 7 and 9 add `Threat`, `Catalog` and `load_catalog` (R2).

`selection.yaml` (exact):

```yaml
# Catalog selection parameters (threat catalog spec §8.1–8.3, §14).
# Tuned on development data only; bump version when any value changes.
version: 1
top_n: 3
max_per_family: 2
shortlist_cap: 40
silence_cap: 15
exclude_families: [EN, FA, CF, PH, LG]
summary_chars_shortlist: 160
summary_chars_candidate: 400
```

`run-config.schema.json` additions (exact). The run config is validated without a `$ref` registry (`cli.py:288-292` and `:399-401`, and `resume_plan.py:107/126`; `tests/test_run_config_schema.py:12` reads `schemas/`, a symlink to `tools/apd_gauntlet/data/schemas`), so the system-type enum lives in the schema's own `$defs`:

```json
"threat_catalog": {
  "description": "Threat catalog enrichment (ADR-0030): off | open | full, or an object. Absent means the release default (off until the CAT4 gates pass). edition full needs path; an unreadable or invalid full file falls back to open with a warning.",
  "oneOf": [
    { "type": "string", "enum": ["off", "open", "full"] },
    {
      "type": "object",
      "additionalProperties": false,
      "required": ["edition"],
      "properties": {
        "edition": { "type": "string", "enum": ["off", "open", "full"] },
        "path": { "type": "string", "minLength": 1, "pattern": "^(~|/|[A-Za-z]:[\\\\/])" },
        "system_types": { "$ref": "#/$defs/catalog_system_types" },
        "exclude_system_types": { "$ref": "#/$defs/catalog_system_types" }
      },
      "if": { "properties": { "edition": { "const": "full" } } },
      "then": { "required": ["path"] }
    }
  ]
}
```

The top-level `"$defs": {"catalog_system_types": {"type": "array", "uniqueItems": true, "items": {"type": "string", "enum": [<CATALOG_SYSTEM_TYPES>]}}}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_catalog_config.py
def test_absent_is_off_by_default():
    assert DEFAULT_EDITION == "off"
    assert catalog_config_from_run_config({"run_id": "r"}) is None

def test_absent_follows_default_when_open(monkeypatch):
    monkeypatch.setattr(config_mod, "DEFAULT_EDITION", "open")
    assert catalog_config_from_run_config({}) == CatalogConfig("open", None, (), ())

@pytest.mark.parametrize("value", ["off", {"edition": "off"}])
def test_off_is_none(value):
    assert catalog_config_from_run_config({"threat_catalog": value}) is None

def test_string_open():
    assert catalog_config_from_run_config({"threat_catalog": "open"}) == CatalogConfig("open", None, (), ())

def test_object_full_expands_home_and_sorts_types(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = catalog_config_from_run_config({"threat_catalog": {
        "edition": "full", "path": "~/tc/full.json",
        "system_types": ["cloud", "api"], "exclude_system_types": ["ot_ics"]}})
    assert cfg == CatalogConfig("full", tmp_path / "tc/full.json", ("api", "cloud"), ("ot_ics",))

def test_string_full_has_no_path():
    assert catalog_config_from_run_config({"threat_catalog": "full"}) == CatalogConfig("full", None, (), ())

def test_unknown_shape_raises():
    with pytest.raises(ValueError, match="threat_catalog"):
        catalog_config_from_run_config({"threat_catalog": 3})

def test_selection_defaults():
    assert load_selection_params() == SelectionParams(1, 3, 2, 40, 15, ("EN", "FA", "CF", "PH", "LG"), 160, 400)

@pytest.mark.parametrize("patch,needle", [({"bogus": 1}, "bogus"), ({"exclude_families": ["ZZ"]}, "ZZ"), ({"top_n": 0}, "top_n")])
def test_selection_rejects_bad_values(tmp_path, patch, needle):
    data = {**yaml.safe_load((catalog_data_dir() / "selection.yaml").read_text()), **patch}
    p = tmp_path / "s.yaml"; p.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match=needle):
        load_selection_params(p)

def test_running_doc_documents_threat_catalog():
    text = (REPO / "docs/running-the-gauntlet.md").read_text()
    assert "### Threat catalog (v2.0+)" in text and "threat_catalog: open" in text and "vendored catalog not installed" in text
```

Extend `tests/test_run_config_schema.py`:

```python
BASE = {"run_id": "r", "domains": ["pbm"], "framework_version": "2.0.0"}

@pytest.mark.parametrize("value", ["off", "open", "full", {"edition": "open"},
    {"edition": "full", "path": "~/tc/full.json", "system_types": ["api"], "exclude_system_types": ["ot_ics"]}])
def test_threat_catalog_accepted(value):
    assert list(Draft202012Validator(SCHEMA).iter_errors({**BASE, "threat_catalog": value})) == []

@pytest.mark.parametrize("value", ["on", {"edition": "full"}, {"edition": "full", "path": "relative/x.json"},
    {"edition": "open", "system_types": ["mainframe"]}, {"edition": "open", "bogus": True}])
def test_threat_catalog_rejected(value):
    assert list(Draft202012Validator(SCHEMA).iter_errors({**BASE, "threat_catalog": value}))

def test_threat_catalog_system_types_match_catalog_vocabulary():
    assert tuple(SCHEMA["$defs"]["catalog_system_types"]["items"]["enum"]) == CATALOG_SYSTEM_TYPES
```

Extend `tests/test_cli_validate_run_config.py` with `test_validate_run_config_accepts_threat_catalog` (the valid fixture, exit 0, "OK") and `test_validate_run_config_rejects_full_without_path` (the invalid fixture, exit ≠ 0, "Schema error:"). The valid fixture is `run-config-with-taxonomies.yaml` plus `threat_catalog: {edition: open, system_types: [api, cloud]}`. The invalid one has `threat_catalog: {edition: full}`.

`tests/test_adr_0030.py`: the ADR exists. Its first line starts `# ADR-0030:`, and it has `Status:`, `Date:`, `## Context`, `## Decision`, `## Consequences` and `## Alternatives considered`. Its lowercased body contains "single vendored catalog", "enrichment layer", "no hitrust content", "threat_catalog", "off" and "2.0 only".

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_config.py tests/test_run_config_schema.py tests/test_cli_validate_run_config.py tests/test_adr_0030.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.catalog`, schema has no `threat_catalog`, ADR missing)

- [ ] **Step 3: Implement `config.py`, the schema change, the data file, the ADR and the docs**

`catalog_config_from_run_config`:

- an absent key uses `DEFAULT_EDITION`, read at call time so a monkeypatch takes effect;
- `off`, in string or object form, gives `None`;
- a `path` becomes `Path(os.path.expanduser(p))`;
- the type tuples are `tuple(sorted(set(...)))`;
- any other shape raises `ValueError("threat_catalog: …")`.

`load_selection_params` checks the eight keys exactly, positive ints, and `exclude_families ⊆ CATALOG_FAMILY_CODES`. It raises `ValueError` naming the key or code and keeps the family order as written.

ADR-0030, "Threat Catalog as an Enrichment Layer", is Accepted on 2026-10-11 and links the spec:

- Context: spec §1.
- Decision:
  - the four rows of spec §3, as amended by register A7: a single vendored catalog (the whole release, as `open`), and `full` as an operator-supplied local file in the release schema;
  - catalog 1.1.0 carries no HITRUST content, and the loader refuses any;
  - the OWASP LLM fix is 2.0 only;
  - `DEFAULT_EDITION` stays `off` until CAT4's gates pass.
- Consequences: what is vendored, CI guards, the fallback.
- Alternatives considered:
  - designs B and C;
  - shipping the full catalog;
  - shipping nothing;
  - a git submodule;
  - fetching at run time;
  - an open subset with HITRUST stubs (1.0.0 design);
  - dropping `full`.

The running-doc section covers:

- both key forms;
- the `off` default;
- that `full` needs `path`: an operator-supplied file in the release schema;
- that the `open` edition reports "vendored catalog not installed" and behaves as `off` until a release is vendored.

Schema-evolution gets a section `## v2.0.0 — Threat catalog data and OWASP editions (CAT1)`, whose first dated entry is `run-config.schema.json` gaining `threat_catalog`. The CHANGELOG bullet covers the key and ADR-0030.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_config.py tests/test_run_config_schema.py tests/test_cli_validate_run_config.py tests/test_adr_0030.py tests/test_meta_schemas.py -v && mypy tools/ && markdownlint-cli2 docs/running-the-gauntlet.md docs/adrs/0030-threat-catalog-enrichment-layer.md docs/schema-evolution.md`
Expected: PASS; mypy clean; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog tools/apd_gauntlet/data/threat-catalog/selection.yaml tools/apd_gauntlet/data/schemas/run-config.schema.json pyproject.toml docs/adrs/0030-threat-catalog-enrichment-layer.md docs/running-the-gauntlet.md docs/schema-evolution.md CHANGELOG.md tests/test_catalog_config.py tests/test_adr_0030.py tests/test_run_config_schema.py tests/test_cli_validate_run_config.py tests/fixtures/valid/run-config-with-threat-catalog.yaml tests/fixtures/invalid/run-config-threat-catalog-full-without-path.yaml
git commit -m "feat(catalog): add threat_catalog run-config key, selection parameters and ADR-0030"
```

### Task 2: OWASP 2025 KBs, edition-aware `refresh-owasp`, Top 10 crosswalk and skill text

**Files:**

- Create: `tools/apd_gauntlet/owasp_editions.py`, `tools/apd_gauntlet/data/threat-catalog/owasp-crosswalks.yaml`
- Modify:
  - `tools/apd_gauntlet/refresh_owasp.py`:
    - `:1-29` (docstring: 2.0 qualifies LLM ids with the edition year);
    - `:53-62` (URLs);
    - `:78-99` (`_project_categories`);
    - `:120-150` (`_write_projected`);
    - `:153-191` (`refresh_owasp`);
  - `tools/apd_gauntlet/data/owasp_top10.json`, `owasp_llm_top10.json` and `owasp_api_top10.json`;
  - `.claude/skills/apd-control-mappings/SKILL.md:256-260` (Top 10) and `:268-272` (LLM);
  - `.claude/skills/apd-domain/lens/*.md` (rebuilt by `apd-gauntlet build-lens-skills examples/apd-20260601-claim-event-bus`, WS5 Task 11; register A10.3);
  - `docs/taxonomy-mappings.md:60` (mapping discipline) and `:189-207` (refresh and data state);
  - `tests/fixtures/kb_golden/owasp/{owasp_top10,owasp_llm_top10,owasp_api_top10}.json`;
  - `docs/schema-evolution.md` and `CHANGELOG.md`.
- Test: `tests/test_owasp_editions.py`, `tests/test_owasp_seeds.py` (create); `tests/test_refresh_owasp.py`, `tests/test_refresh_byte_stable.py:167-179` and `:277-301`, and `tests/test_skill_apd_control_mappings.py` (modify); `tests/test_lens_skills.py::test_committed_packets_match_rebuild` (WS5 Task 11, run unchanged)

**Interfaces:**

- Produces (`refresh_owasp.py`):
  - `EDITIONS: dict[str, str] = {"top10": "2025", "api_top10": "2023", "llm_top10": "2025"}`
  - `_project_categories(payload: Any, *, qualify_llm: bool = False) -> list[dict[str, Any]]`
  - `_write_projected(entries, url, output_path, raw_bytes=None, *, edition: str | None = None) -> None` (writes the top-level key `edition` when given; the existing callers in `tests/test_refresh_owasp.py` keep working)
  - `def write_seed(entries: list[dict[str, Any]], output_path: Path, *, edition: str, seed_source: str, fetched_at: str | None = None) -> None`. It writes `{edition, entries, fetched_at, seed_source, source_sha256, source_url: "seed_only"}`, with `source_sha256` hashed over the entries as seed mode does today.
  - `refresh_owasp` raises `ValueError("<file>: upstream id <id> is not edition <year>")` when a projected id's `:YYYY` suffix is missing or differs from `EDITIONS` (LLM ids are qualified first). `fetch_owasp_llm_top10` qualifies too.
- Produces (`owasp_editions.py`):
  - `LLM_BARE_RE = re.compile(r"^LLM(0[1-9]|10)$")`; `TOP10_2021_RE = re.compile(r"^A(0[1-9]|10):2021$")`
  - `LLM_2023_NAMES: Mapping[str, str]` — bare id → the 2023 name, exactly the current `owasp_llm_top10.json`: LLM01 Prompt Injection, LLM02 Insecure Output Handling, LLM03 Training Data Poisoning, LLM04 Model Denial of Service, LLM05 Supply Chain Vulnerabilities, LLM06 Sensitive Information Disclosure, LLM07 Insecure Plugin Design, LLM08 Excessive Agency, LLM09 Overreliance, LLM10 Model Theft
  - `def qualify_llm_id(cat_id: str) -> str` (bare → `:2025`; anything else unchanged)
  - `def llm_edition(cat_id: str) -> Literal["2025", "unknown"]`
  - `@dataclass(frozen=True) class Top10Crosswalk: source_url: str; names_2021: Mapping[str, str]; to_2025: Mapping[str, tuple[str, ...]]`
  - `def load_top10_crosswalk(path: Path | None = None) -> Top10Crosswalk` (default `catalog_data_dir() / "owasp-crosswalks.yaml"`; `ValueError` on a malformed file)
  - `def translate_top10(cat_id: str, xw: Top10Crosswalk) -> tuple[tuple[str, ...], bool]` — a 2021 id with targets → `(targets, True)`; any other id → `((cat_id,), False)`
  - `def framework_major(run_dir: Path) -> int | None` — major of `.apd-run.yaml` `framework_version`; `None` when missing or unparseable

`owasp-crosswalks.yaml` shape. The `name` values are the current 2021 seed names. OWASP publishes the 2021→2025 mapping as an image; the `to` values and `source_url` below are copied from the text of <https://owasp.org/Top10/2025/0x00_2025-Introduction/> (no date shown; register A7.52), and the implementer re-checks them there:

```yaml
schema_version: 1
owasp_top10:
  from_edition: "2021"
  to_edition: "2025"
  source_url: https://owasp.org/Top10/2025/0x00_2025-Introduction/
  retrieved: "<YYYY-MM-DD>"
  rows:
    - {from: "A01:2021", name: "Broken Access Control", to: ["A01:2025"]}
    - {from: "A02:2021", name: "Cryptographic Failures", to: ["A04:2025"]}
    - {from: "A03:2021", name: "Injection", to: ["A05:2025"]}
    - {from: "A04:2021", name: "Insecure Design", to: ["A06:2025"]}
    - {from: "A05:2021", name: "Security Misconfiguration", to: ["A02:2025"]}
    - {from: "A06:2021", name: "Vulnerable and Outdated Components", to: ["A03:2025"]}  # "an expansion of A06:2021"
    - {from: "A07:2021", name: "Identification and Authentication Failures", to: ["A07:2025"]}
    - {from: "A08:2021", name: "Software and Data Integrity Failures", to: ["A08:2025"]}
    - {from: "A09:2021", name: "Security Logging and Monitoring Failures", to: ["A09:2025"]}
    - {from: "A10:2021", name: "Server-Side Request Forgery", to: ["A01:2025"]}  # "SSRF has been rolled into this category"
```

A row whose `to` is empty must carry a `note` string. Every row above has a target, so no `note` row is needed. The relation is many-to-many: several 2021 rows may name the same 2025 id (A01:2021 and A10:2021 both name A01:2025).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_owasp_seeds.py
LLM_2025 = ["Prompt Injection", "Sensitive Information Disclosure", "Supply Chain", "Data and Model Poisoning",
            "Improper Output Handling", "Excessive Agency", "System Prompt Leakage",
            "Vector and Embedding Weaknesses", "Misinformation", "Unbounded Consumption"]

def test_top10_seed_is_2025():
    d = json.loads((DATA / "owasp_top10.json").read_text())
    assert [e["category_id"] for e in d["entries"]] == [f"A{n:02d}:2025" for n in range(1, 11)]
    assert all(e["name"].strip() for e in d["entries"])
    assert d["edition"] == "2025" and d["source_url"] == "seed_only" and d["seed_source"].startswith("https://owasp.org/Top10")

def test_llm_seed_is_2025_qualified():
    d = json.loads((DATA / "owasp_llm_top10.json").read_text())
    assert [(e["category_id"], e["name"]) for e in d["entries"]] == [(f"LLM{n:02d}:2025", nm) for n, nm in enumerate(LLM_2025, 1)]
    assert d["edition"] == "2025" and d["seed_source"].startswith("https://genai.owasp.org/")

def test_api_seed_records_2023():
    d = json.loads((DATA / "owasp_api_top10.json").read_text())
    assert d["edition"] == "2023" and len(d["entries"]) == 10

@pytest.mark.parametrize("name", ["owasp_top10.json", "owasp_llm_top10.json", "owasp_api_top10.json"])
def test_seed_hash_is_entries_hash(name):
    d = json.loads((DATA / name).read_text())
    assert d["source_sha256"] == hashlib.sha256(json.dumps(d["entries"], sort_keys=True).encode()).hexdigest()

# tests/test_owasp_editions.py
def test_qualify_llm_id():
    assert [qualify_llm_id(x) for x in ("LLM06", "LLM06:2025", "A01:2021")] == ["LLM06:2025", "LLM06:2025", "A01:2021"]

def test_llm_edition():
    assert llm_edition("LLM06") == "unknown" and llm_edition("LLM06:2025") == "2025"

def test_llm_2023_names_pinned():
    assert len(LLM_2023_NAMES) == 10 and LLM_2023_NAMES["LLM06"] == "Sensitive Information Disclosure"
    assert LLM_2023_NAMES["LLM07"] == "Insecure Plugin Design" and LLM_2023_NAMES["LLM10"] == "Model Theft"

def test_crosswalk_file_complete():
    xw = load_top10_crosswalk()
    assert sorted(xw.names_2021) == [f"A{n:02d}:2021" for n in range(1, 11)] == sorted(xw.to_2025)
    assert xw.names_2021["A10:2021"] == "Server-Side Request Forgery"
    kb = {e["category_id"] for e in json.loads((DATA / "owasp_top10.json").read_text())["entries"]}
    assert all(set(t) <= kb for t in xw.to_2025.values()) and xw.source_url.startswith("https://owasp.org/")

def test_crosswalk_empty_row_needs_note(tmp_path):
    p = tmp_path / "x.yaml"; p.write_text(_crosswalk_text(rows=[{"from": "A01:2021", "name": "x", "to": []}]))
    with pytest.raises(ValueError, match="A01:2021"):
        load_top10_crosswalk(p)

def test_translate_top10():
    xw = Top10Crosswalk("test", {"A03:2021": "Injection"}, {"A03:2021": ("A05:2025",)})
    assert translate_top10("A03:2021", xw) == (("A05:2025",), True)
    assert translate_top10("A01:2025", xw) == (("A01:2025",), False)

@pytest.mark.parametrize("fv,major", [("2.0.0", 2), ("1.7.0", 1), (None, None)])
def test_framework_major(tmp_path, fv, major):
    if fv: (tmp_path / ".apd-run.yaml").write_text(f"run_id: r\nframework_version: {fv}\n")
    assert framework_major(tmp_path) == major
```

`_crosswalk_text` is a test helper that dumps the YAML shape above. In `tests/test_refresh_owasp.py`:

- `test_refresh_owasp_writes_three_files` feeds `A01:2025`/`A02:2025`, `API3:2023` and bare `LLM01`. It asserts `edition` in each file (`2025`, `2023`, `2025`) and `llm["entries"][0]["category_id"] == "LLM01:2025"`.
- `test_refresh_owasp_preserves_edition_in_category_id` becomes `test_refresh_owasp_rejects_wrong_edition`: an `A03:2021` payload gives `ValueError` matching `"not edition 2025"`.
- `test_fetch_owasp_llm_top10_projects_categories` expects `LLM01:2025`.
- New `test_write_seed_records_edition_and_source` checks the six keys and `source_url == "seed_only"`.

In `tests/test_refresh_byte_stable.py`, the top 10 payload uses `A01:2025` and `A02:2025` with neutral titles ("Test category one", "Test category two"). In `tests/test_skill_apd_control_mappings.py`, add a new helper `_section(title)` (none exists yet), which returns the text from the `### <title>` heading to the next level-3 heading:

```python
def test_owasp_top10_section_teaches_2025():
    s = _section("OWASP Top 10 (web — on findings, optional)")
    assert "A<NN>:2025" in s and "A03:2021" not in s and "2021 ids stay valid" in s

def test_owasp_llm_section_teaches_year_qualified_2025():
    s = _section("OWASP LLM Top 10 (on findings, optional)")
    assert "LLM<NN>:2025" in s and "LLM06:2025 (Excessive Agency)" in s
    assert "LLM02:2025 (Sensitive Information Disclosure)" in s and "Insecure Plugin Design" not in s
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_owasp_seeds.py tests/test_owasp_editions.py tests/test_refresh_owasp.py tests/test_refresh_byte_stable.py tests/test_skill_apd_control_mappings.py -v`
Expected: FAIL (2021/2023 seeds, `owasp_editions` missing, no `edition` key, old skill text)

- [ ] **Step 3: Implement the module, seeds, refresh changes, crosswalk and text**

1. Open the published OWASP Top 10 2025 list (<https://owasp.org/Top10/>, 2025 edition). Write `owasp_top10.json` with `write_seed`, copying the ten ids and names verbatim and recording the page URL as `seed_source`. The names at <https://owasp.org/Top10/2025/> (register A7.52): A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions.
2. Write `owasp_llm_top10.json` with the ten names in Global Constraints, ids `LLMnn:2025`, and `seed_source` set to the OWASP GenAI LLM Top 10 page the implementer verifies (<https://genai.owasp.org/llm-top-10/>, whose 2025 names match the list; register A7.52).
3. Rewrite `owasp_api_top10.json` through `write_seed` with `edition="2023"`, unchanged entries and its current `fetched_at`. Only `edition`, `seed_source` (the API Security project page) and key order may change.
4. Fill `owasp-crosswalks.yaml` with the rows above, re-checked against OWASP's published 2021→2025 mapping.
5. Point `OWASP_TOP10_URL` and `OWASP_LLM_TOP10_URL` at the 2025 sources. Verify them at implementation time and note in the module docstring any that is not machine-readable; the seed then stays authoritative, as today.
6. Regenerate the three `kb_golden/owasp/` files from the new byte-stable payloads. The diff may show only the new ids, the `edition` key, the new `source_url`s and the LLM qualification.
7. After the skill edit, rerun `apd-gauntlet build-lens-skills examples/apd-20260601-claim-event-bus` from the repo root and commit the rebuilt `.claude/skills/apd-domain/lens/*.md` (WS5 Task 11's rule, register A10.3); otherwise `test_committed_packets_match_rebuild` fails on this PR.

Skill text:

- Top 10: the format is `A<NN>:2025` with the example `A01:2025`. "2021 ids stay valid (the pattern accepts them) and rollups crosswalk them; new findings use 2025."
- LLM:
  - the format is `LLM<NN>:2025`;
  - the most-cited line is "LLM01:2025 (Prompt Injection), LLM02:2025 (Sensitive Information Disclosure), LLM06:2025 (Excessive Agency)";
  - "always write the year; canonicalize rewrites a bare `LLM<NN>` to `LLM<NN>:2025` on 2.0 runs".

In `docs/taxonomy-mappings.md`, line 60 gets a 2.0 sentence on editions: the 2025 KBs, the crosswalk, the qualified LLM ids, and `edition: unknown` for bare ids in older runs. The data-state list notes the 2025 seeds.

Schema-evolution entry: "KB files `owasp_*.json` gain `edition` and, on seeds, `seed_source`." CHANGELOG bullets cover the 2025 lists, the skill and the crosswalk.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_owasp_seeds.py tests/test_owasp_editions.py tests/test_refresh_owasp.py tests/test_refresh_byte_stable.py tests/test_skill_apd_control_mappings.py tests/test_lint_skills.py tests/test_check_kb_cache_freshness.py tests/test_lens_skills.py -v && python tools/check_kb_cache_freshness.py && markdownlint-cli2 docs/taxonomy-mappings.md ".claude/**/*.md"`
Expected: PASS; freshness OK; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/owasp_editions.py tools/apd_gauntlet/refresh_owasp.py tools/apd_gauntlet/data/owasp_top10.json tools/apd_gauntlet/data/owasp_llm_top10.json tools/apd_gauntlet/data/owasp_api_top10.json tools/apd_gauntlet/data/threat-catalog/owasp-crosswalks.yaml .claude/skills/apd-control-mappings/SKILL.md .claude/skills/apd-domain/lens docs/taxonomy-mappings.md docs/schema-evolution.md CHANGELOG.md tests/test_owasp_seeds.py tests/test_owasp_editions.py tests/test_refresh_owasp.py tests/test_refresh_byte_stable.py tests/test_skill_apd_control_mappings.py tests/fixtures/kb_golden/owasp
git commit -m "feat(owasp): move Top 10 and LLM Top 10 KBs and skill to 2025 with a 2021 crosswalk"
```

Measured with Tasks 3–5 at Task 5 Step 6 (one PR group).

### Task 3: Year-qualified LLM ids in the finding schema and `canonicalize`

**Files:**

- Modify:
  - `tools/apd_gauntlet/data/schemas/finding.schema.json:90-93`;
  - `tools/apd_gauntlet/canonicalize.py`:
    - `:1-38` (docstring);
    - `:143-157` (`CanonicalizeResult`, after WS1 Task 9's `context_ids_minted`; it also has `context_parse_errors`);
    - `:167-246` (`_recompute_ids_for_file`);
    - `:424-477` (`canonicalize_run`; `_mint_threat_model_ids` is at `:383-421`);
  - `tools/apd_gauntlet/cli.py` `canonicalize_cmd` `:1298-1340` (summary line, `:1318-1331`; the blocked message goes to stderr);
  - `docs/deterministic-field-register.md` ("Other derived fields" table);
  - `docs/schema-evolution.md` and `CHANGELOG.md`.
- Create: `tests/fixtures/valid/finding-with-owasp-llm-2025.yaml`, `tests/fixtures/invalid/finding-with-owasp-llm-2023-suffix.yaml`
- Test: `tests/test_canonicalize_owasp_llm.py` (create), `tests/test_finding_schema.py` (extend)

**Interfaces:**

- Consumes: `owasp_editions.qualify_llm_id`, `framework_major`, `LLM_BARE_RE` (Task 2)
- Produces:
  - finding `control_mappings.owasp_llm_top10` items: pattern `^LLM(0[1-9]|10)(:2025)?$`
  - `canonicalize._qualify_llm_ids(record: dict[str, Any]) -> int` — rewrites bare ids in `control_mappings.owasp_llm_top10` (strings and `{"id": str}` items), drops duplicates in first-seen order, and returns the number of ids rewritten
  - `@dataclass class FileResult: records: list[dict[str, Any]] | None; ids_changed: int; llm_qualified: int = 0`
  - `_recompute_ids_for_file(path, root_key, id_map, seen_new_ids, *, qualify_llm: bool = False) -> FileResult` (after WS1 it returns `tuple[list | None, int]`; `FileResult` replaces that tuple, so CAT3 Task 2 can add its own field without changing the arity); qualification runs right after `_normalize_control_mappings` and counts as a normalization for the write-back rule
  - `CanonicalizeResult.llm_ids_qualified: int = 0`
  - `canonicalize_run` sets `qualify_llm = (framework_major(run_dir) or 0) >= 2`
  - CLI summary appends `, {n} OWASP LLM ids qualified` only when `n > 0`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_canonicalize_owasp_llm.py  (helpers _write/_finding as in tests/test_canonicalize_control_mappings.py)
def _run(tmp_path, fv, llm):
    if fv: (tmp_path / ".apd-run.yaml").write_text(f"run_id: r\ndomains: [agentic-ai]\nframework_version: {fv}\n")
    _write(tmp_path / "10-trustworthiness/integrity.findings.yaml", {"finding": [_finding(
        "integrity", "Agent writes without authorization", "#p1",
        control_mappings={"nist_800_53r5": ["AC-6"], "owasp_llm_top10": llm})]})
    return tmp_path

def _llm(run):
    doc = yaml.safe_load((run / "10-trustworthiness/integrity.findings.yaml").read_text())
    return doc["finding"][0]["control_mappings"]["owasp_llm_top10"]

def test_bare_llm_ids_qualified_on_2_0(tmp_path):
    run = _run(tmp_path, "2.0.0", ["LLM06", {"id": "LLM01"}, "LLM06:2025"])
    res = canonicalize_run(run)
    assert _llm(run) == ["LLM06:2025", {"id": "LLM01:2025"}] and res.llm_ids_qualified == 2

def test_pre_2_0_run_not_rewritten(tmp_path):
    run = _run(tmp_path, "1.7.0", ["LLM06"])
    assert canonicalize_run(run).llm_ids_qualified == 0 and _llm(run) == ["LLM06"]

def test_missing_run_config_not_rewritten(tmp_path):
    run = _run(tmp_path, None, ["LLM06"])
    canonicalize_run(run); assert _llm(run) == ["LLM06"]

def test_root_level_llm_key_lifted_then_qualified(tmp_path):
    (tmp_path / ".apd-run.yaml").write_text("run_id: r\ndomains: [agentic-ai]\nframework_version: 2.0.0\n")
    _write(tmp_path / "10-trustworthiness/integrity.findings.yaml", {"finding": [_finding(
        "integrity", "Agent writes without authorization", "#p1",
        control_mappings={"nist_800_53r5": ["AC-6"]}, owasp_llm_top10=["LLM08"])]})
    canonicalize_run(tmp_path); assert _llm(tmp_path) == ["LLM08:2025"]

def test_qualification_idempotent(tmp_path):
    run = _run(tmp_path, "2.0.0", ["LLM06"]); canonicalize_run(run)
    first = (run / "10-trustworthiness/integrity.findings.yaml").read_bytes()
    assert canonicalize_run(run).llm_ids_qualified == 0
    assert (run / "10-trustworthiness/integrity.findings.yaml").read_bytes() == first

def test_cli_reports_qualified_count(tmp_path):
    run = _run(tmp_path, "2.0.0", ["LLM06", "LLM01"])
    r = CliRunner().invoke(main, ["canonicalize", str(run)])
    assert r.exit_code == 0 and "2 OWASP LLM ids qualified" in r.output
```

In `tests/test_finding_schema.py`, `test_finding_accepts_year_qualified_llm` (valid fixture with `["LLM06:2025", "LLM01"]`) and `test_finding_rejects_other_llm_years` (invalid fixture with `["LLM06:2023"]`) follow the file's `_load_schema`/`_build_validator` pattern. The existing `LLM00` test stays.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_canonicalize_owasp_llm.py tests/test_finding_schema.py -v`
Expected: FAIL (`llm_ids_qualified` missing; `LLM06:2025` rejected by the schema)

- [ ] **Step 3: Implement the pattern, `_qualify_llm_ids` and the plumbing**

Register row: "`control_mappings.owasp_llm_top10` edition qualification (bare `LLMnn` → `LLMnn:2025`, framework ≥ 2.0 runs only) | `canonicalize._qualify_llm_ids` | the 2.0 skill and KB teach 2025 meanings; bare ids in pre-2.0 runs stay ambiguous (threat catalog spec §10)". Schema-evolution entry: the finding pattern accepts `LLMnn:2025` (additive). CHANGELOG bullet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_canonicalize_owasp_llm.py tests/test_finding_schema.py tests/test_canonicalize.py tests/test_canonicalize_control_mappings.py tests/test_cli_canonicalize.py tests/test_validate_example_run.py tests/test_register_consistency.py -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas/finding.schema.json tools/apd_gauntlet/canonicalize.py tools/apd_gauntlet/cli.py docs/deterministic-field-register.md docs/schema-evolution.md CHANGELOG.md tests/test_canonicalize_owasp_llm.py tests/test_finding_schema.py tests/fixtures/valid/finding-with-owasp-llm-2025.yaml tests/fixtures/invalid/finding-with-owasp-llm-2023-suffix.yaml
git commit -m "feat(canonicalize): qualify bare OWASP LLM ids as 2025 on framework 2.0 runs"
```

Measured at Task 5 Step 6.

### Task 4: OWASP editions in `owasp-coverage`

**Files:**

- Modify:
  - `tools/apd_gauntlet/synthesis/rollup.py`: `:375` (call site), `:737-753` (`_owasp_names`) and `:755-782` (`_owasp_rollup`);
  - `tools/apd_gauntlet/data/schemas/owasp-coverage.schema.json`;
  - `docs/taxonomy-mappings.md` ("Synthesizer rollups", owasp bullet);
  - `docs/schema-evolution.md` and `CHANGELOG.md`.
- Test: `tests/test_rollup_owasp_editions.py` (create)

**Interfaces:**

- Consumes: `Top10Crosswalk`, `load_top10_crosswalk`, `translate_top10`, `LLM_BARE_RE`, `LLM_2023_NAMES`, `qualify_llm_id` (Task 2)
- Produces:
  - `_owasp_rollup(findings: list[dict[str, Any]], declared: set[str], *, crosswalk: Top10Crosswalk | None = None) -> dict[str, Any]` (`None` loads the packaged crosswalk)
  - `owasp_top10` entries:
    - a 2021 id with targets contributes its findings to each 2025 target;
    - a target reached that way carries `crosswalked: true` and `crosswalked_from` (sorted 2021 ids);
    - a 2021 id without targets stays under its own id, named from `names_2021`.
  - `owasp_llm_top10` entries carry `edition`:
    - `"2025"` for qualified ids, named from the KB;
    - `"unknown"` for bare ids, with `edition_names: {"2023": …, "2025": …}` and `name` = `"<2023 name> (2023) / <2025 name> (2025)"`.
  - Schema:
    - entry properties gain `edition` (enum `2025`, `unknown`), `edition_names` (object with required string keys `2023` and `2025`, no others), `crosswalked` (boolean) and `crosswalked_from` (array, items `^A(0[1-9]|10):2021$`);
    - the LLM `category_id` pattern becomes `^LLM(0[1-9]|10)(:2025)?$`.

- [ ] **Step 1: Write the failing tests**

```python
XW = Top10Crosswalk("test", {"A03:2021": "Injection", "A06:2021": "Vulnerable and Outdated Components"},
                    {"A03:2021": ("A05:2025",), "A06:2021": ()})
def f(fid, **cm): return {"id": fid, "control_mappings": {"nist_800_53r5": ["AC-3"], **cm}, "evidence": []}

def test_2021_ids_crosswalked():
    doc = _owasp_rollup([f("intg-00000001", owasp_top10=["A03:2021"]), f("intg-00000002", owasp_top10=["A05:2025"])],
                        {"owasp_top10"}, crosswalk=XW)
    (e,) = doc["entries"]
    assert e["category_id"] == "A05:2025" and e["finding_ids"] == ["intg-00000001", "intg-00000002"]
    assert e["crosswalked"] is True and e["crosswalked_from"] == ["A03:2021"]
    assert e["name"] == _owasp_names("owasp_top10")["A05:2025"]

def test_untranslatable_2021_id_kept_with_2021_name():
    (e,) = _owasp_rollup([f("intg-00000001", owasp_top10=["A06:2021"])], {"owasp_top10"}, crosswalk=XW)["entries"]
    assert e["category_id"] == "A06:2021" and e["name"] == "Vulnerable and Outdated Components" and "crosswalked" not in e

def test_bare_llm_id_edition_unknown_with_both_names():
    (e,) = _owasp_rollup([f("intg-00000001", owasp_llm_top10=["LLM06"])], {"owasp_llm_top10"})["entries"]
    assert e["edition"] == "unknown" and e["edition_names"] == {"2023": "Sensitive Information Disclosure", "2025": "Excessive Agency"}
    assert e["name"] == "Sensitive Information Disclosure (2023) / Excessive Agency (2025)"

def test_qualified_llm_id_edition_2025():
    (e,) = _owasp_rollup([f("intg-00000001", owasp_llm_top10=["LLM06:2025"])], {"owasp_llm_top10"})["entries"]
    assert e["edition"] == "2025" and e["name"] == "Excessive Agency"

def test_output_validates_against_schema():
    doc = _owasp_rollup([f("intg-00000001", owasp_top10=["A03:2021"], owasp_llm_top10=["LLM06", "LLM01:2025"])],
                        {"owasp_top10", "owasp_llm_top10"}, crosswalk=XW)
    assert list(Draft202012Validator(read_schema("owasp-coverage.schema.json")).iter_errors(doc)) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_rollup_owasp_editions.py -v`
Expected: FAIL (`crosswalk` keyword unknown; no edition fields)

- [ ] **Step 3: Implement the rollup and schema changes**

Translation happens before grouping, so a finding counts once per target. Entry order stays first-appearance order. The docs bullet names the new fields. Schema-evolution entry: owasp-coverage gains the four fields (additive). CHANGELOG bullet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_rollup_owasp_editions.py tests/test_cli_rollup.py tests/test_validate_schema_pass.py tests/test_validate_example_run.py tests/test_examples.py -v && mypy tools/`
Expected: PASS (the committed examples cite no 2021 or LLM ids, so their rollups are unchanged)

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/rollup.py tools/apd_gauntlet/data/schemas/owasp-coverage.schema.json docs/taxonomy-mappings.md docs/schema-evolution.md CHANGELOG.md tests/test_rollup_owasp_editions.py
git commit -m "feat(rollup): crosswalk OWASP Top 10 2021 ids and mark editionless LLM ids"
```

Measured at Task 5 Step 6.

### Task 5: `compare-runs` taxonomy deltas across OWASP editions

Depends on WS2 Tasks 1, 2 and 6 (`docs/superpowers/plans/2026-10-10-ws2-measurement-and-evaluation.md`).

**Files:**

- Create: `tools/apd_gauntlet/measure/taxonomy_delta.py`
- Modify: `tools/apd_gauntlet/measure/compare.py` (WS2: `PairDelta`, `compare_pair`, `compare_sides`, `comparison_json`, `render_text`), `docs/measuring-changes.md` (WS2 runbook), `CHANGELOG.md`
- Test: `tests/test_measure_taxonomy_delta.py` (create), `tests/test_cli_compare_runs.py`, `tests/test_measuring_changes_doc.py` (extend)

**Interfaces:**

- Consumes:
  - from WS2 Task 1: `RunSnapshot` (`path`, `findings`) and `load_run(path) -> RunSnapshot`;
  - from WS2 Tasks 2 and 6: `PairDelta`, `compare_pair(baseline, candidate, *, excused) -> PairDelta`, `Comparison` (`warnings`), `compare_sides`, `comparison_json`, `render_text`;
  - WS2's `make_run` and `edit` fixtures;
  - from Task 2: `framework_major`, `qualify_llm_id`, `LLM_BARE_RE`, `translate_top10`, `load_top10_crosswalk`, `Top10Crosswalk`.
- Produces:
  - `EDITION_SENSITIVE: tuple[str, ...] = ("owasp_top10", "owasp_llm_top10")`
  - `@dataclass(frozen=True) class TaxonomyDelta: taxonomy: str; status: Literal["compared", "not_comparable"]; added: tuple[str, ...]; removed: tuple[str, ...]; crosswalked: tuple[str, ...]; reason: str | None`
  - `def taxonomy_deltas(baseline: RunSnapshot, candidate: RunSnapshot, *, crosswalk: Top10Crosswalk | None = None) -> tuple[TaxonomyDelta, ...]` — one delta per edition-sensitive taxonomy that either run cites
  - `def taxonomy_delta_json(d: TaxonomyDelta) -> dict[str, Any]`
  - `PairDelta.taxonomy_deltas: tuple[TaxonomyDelta, ...] = ()` (last field), filled by `compare_pair`. `comparison_json` pairs gain `"taxonomies"`. `render_text` prints one line per delta. `compare_sides` adds the warning `"OWASP LLM ids not comparable across the 2.0 boundary: <baseline> vs <candidate>"` once per such pair.

Rules. Ids come from every finding's `control_mappings.<taxonomy>`, as strings or `{"id"}` items.

- **Top 10:** each run's id set is the union of `translate_top10` outputs. `crosswalked` lists the 2021 ids translated on either side. `added` is the candidate set minus the baseline set, and `removed` the reverse.
- **LLM:** a run with major ≥ 2 has its ids passed through `qualify_llm_id`.
  - When one run is pre-2.0 (major `< 2` or `None`), the other is ≥ 2.0, and the pre-2.0 run cites at least one bare id, the result is `not_comparable` with the reason `"OWASP LLM ids in <run> (framework <version>) carry no edition; 2023 and 2025 ids are not comparable"`.
  - Otherwise the sets are compared as they are.

Deltas are reported, never gated: no gate metric is added.

- [ ] **Step 1: Write the failing tests**

```python
XW = Top10Crosswalk("test", {"A03:2021": "Injection"}, {"A03:2021": ("A05:2025",)})
def set_mapping(edit, run, rid, key, ids):
    rec = load_run(run).findings[rid]; edit.finding(run, rid, control_mappings={**rec["control_mappings"], key: ids})
def set_framework(run, v):
    p = run / ".apd-run.yaml"; d = yaml.safe_load(p.read_text()); d["framework_version"] = v; p.write_text(yaml.safe_dump(d))

def test_top10_crosswalk_counts_translated_not_churn(make_run, edit):
    b, c = make_run("b"), make_run("c")
    set_mapping(edit, b, "conf-7aa376c5", "owasp_top10", ["A03:2021"])
    set_mapping(edit, c, "conf-7aa376c5", "owasp_top10", ["A05:2025"]); set_framework(c, "2.0.0")
    (d,) = taxonomy_deltas(load_run(b), load_run(c), crosswalk=XW)
    assert (d.taxonomy, d.status, d.added, d.removed, d.crosswalked) == ("owasp_top10", "compared", (), (), ("A03:2021",))

def test_top10_real_change_reported(make_run, edit):
    b, c = make_run("b"), make_run("c")
    set_mapping(edit, b, "conf-7aa376c5", "owasp_top10", ["A03:2021"]); set_mapping(edit, c, "conf-7aa376c5", "owasp_top10", ["A01:2025"])
    (d,) = taxonomy_deltas(load_run(b), load_run(c), crosswalk=XW)
    assert d.added == ("A01:2025",) and d.removed == ("A05:2025",)

def test_llm_not_comparable_across_2_0(make_run, edit):
    b, c = make_run("b"), make_run("c")                                      # example framework_version 1.4.0
    set_mapping(edit, b, "conf-7aa376c5", "owasp_llm_top10", ["LLM06"])
    set_mapping(edit, c, "conf-7aa376c5", "owasp_llm_top10", ["LLM06:2025"]); set_framework(c, "2.0.0")
    (d,) = taxonomy_deltas(load_run(b), load_run(c))
    assert d.status == "not_comparable" and "1.4.0" in d.reason and d.added == d.removed == ()

def test_llm_compared_when_both_2_0(make_run, edit):
    b, c = make_run("b"), make_run("c"); set_framework(b, "2.0.0"); set_framework(c, "2.0.0")
    set_mapping(edit, b, "conf-7aa376c5", "owasp_llm_top10", ["LLM06"]); set_mapping(edit, c, "conf-7aa376c5", "owasp_llm_top10", ["LLM06:2025"])
    (d,) = taxonomy_deltas(load_run(b), load_run(c))
    assert d.status == "compared" and d.added == d.removed == ()

def test_llm_compared_when_pre_2_0_side_cites_none(make_run, edit):
    b, c = make_run("b"), make_run("c"); set_framework(c, "2.0.0")
    set_mapping(edit, c, "conf-7aa376c5", "owasp_llm_top10", ["LLM01:2025"])
    (d,) = taxonomy_deltas(load_run(b), load_run(c))
    assert d.status == "compared" and d.added == ("LLM01:2025",)
```

Extend `tests/test_cli_compare_runs.py` with `test_json_reports_llm_not_comparable`. It uses the same edits as `test_llm_not_comparable_across_2_0`, then runs `cr(b, c, "--json")`. It asserts `out["pairs"][0]["taxonomies"][0]["status"] == "not_comparable"`, `any("2.0 boundary" in w for w in out["warnings"])` and exit 0. `test_runbook_covers_owasp_editions` asserts that `not_comparable`, `owasp-crosswalks.yaml` and `crosswalked` appear in `docs/measuring-changes.md`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_measure_taxonomy_delta.py tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.measure.taxonomy_delta`)

- [ ] **Step 3: Implement `taxonomy_delta.py` and the `compare.py` changes**

`compare_pair` loads the crosswalk once per process (`functools.lru_cache` on a zero-argument loader). The runbook gets a section "OWASP editions across the 2.0 boundary": 2021 ids are translated through `owasp-crosswalks.yaml`, LLM ids are `not_comparable` when a pre-2.0 run cites bare ids, and deltas are informational. CHANGELOG bullet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_measure_taxonomy_delta.py tests/test_measure_compare.py tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py -v && mypy tools/ && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS; mypy clean; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/measure/taxonomy_delta.py tools/apd_gauntlet/measure/compare.py docs/measuring-changes.md CHANGELOG.md tests/test_measure_taxonomy_delta.py tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py
git commit -m "feat(compare-runs): crosswalk OWASP Top 10 ids and mark LLM ids not comparable across 2.0"
```

- [ ] **Step 6 (operator): Measure Tasks 2–5**

Run the master plan Task 1 set twice on this commit, with names ending `-owasp-r1` and `-owasp-r2`. For each example, run `apd-gauntlet compare-runs runs/<example>-next-baseline runs/<example>-owasp --gates eval/gates.yaml`, then `apd-gauntlet compare-runs runs/<example>-baseline runs/<example>-owasp --gates eval/gates.yaml --json`.
Expected:

- exit 0 for every pair;
- `pass_with_gaps` is allowed only against the 1.7.1 baseline;
- in the JSON, `owasp_llm_top10` appears as `not_comparable` only where the 1.7.1 run cites bare LLM ids;
- `owasp_top10` deltas list no 2021 id as removed when its 2025 target is present.

### Task 6: Catalog static data and `translate.py`

**Files:**

- Create: `tools/apd_gauntlet/data/threat-catalog/{compat,system-types,apd-goals,taxonomy-map}.yaml`, `tools/apd_gauntlet/catalog/translate.py`
- Test: `tests/test_catalog_translate.py`, `tests/test_catalog_data_files.py`

**Interfaces:**

- Consumes: `catalog_data_dir`, `CATALOG_SYSTEM_TYPES`, `CATALOG_FAMILY_CODES` (Task 1); `LINDDUN_TO_APD_GOALS` (`tools/apd_gauntlet/threat_model/mappings.py:22-30`)
- Produces (`translate.py`):
  - `LINDDUN_CATALOG_TO_GAUNTLET: Mapping[str, str]` (read-only; the §8.6 table)
  - `@dataclass(frozen=True) class TaxonomyMapEntry: key: str; section: Literal["mappings", "controls"]; taxonomy: str; kb: str`
  - `def taxonomy_map() -> tuple[TaxonomyMapEntry, ...]` (sorted by key; cached)
  - `def taxonomy_for(catalog_key: str) -> str | None`
  - `def kb_ids(taxonomy: str) -> frozenset[str]` (cached; `ValueError` naming an unknown taxonomy)
  - `def kb_version(taxonomy: str) -> str | None` — first non-empty, non-`"unknown"` value of `_meta.version`, top-level `edition`, then top-level `version`
  - `def normalize_nist(control_id: str) -> str`
- Data consumed by CAT2: `system-types.yaml` (`asset_types`, `identity_types`, `iac_resource_types`) and `apd-goals.yaml` (`families`).

`compat.yaml`: `catalog_compat: ">=1.1.0,<2.0.0"`. The three-part form suits the existing range parser (`build_domain_skill.py` `_parse_semver_range` `:70-82`, `_version_in_range` `:85-91`), and the coordinator aligns the spec to it.

`taxonomy-map.yaml`:

```yaml
schema_version: 1
mappings:
  attack_enterprise: {taxonomy: mitre_attack, kb: mitre-attack-techniques.json}
  attack_mobile:     {taxonomy: mitre_attack, kb: mitre-attack-techniques.json}
  atlas:             {taxonomy: atlas, kb: atlas-techniques.json}
  cwe:               {taxonomy: cwe, kb: cwe.json}
  owasp_top10:       {taxonomy: owasp_top10, kb: owasp_top10.json}
  owasp_api:         {taxonomy: owasp_api_top10, kb: owasp_api_top10.json}
  owasp_llm_2025:    {taxonomy: owasp_llm_top10, kb: owasp_llm_top10.json}
  maswe:             {taxonomy: maswe, kb: maswe.json}
  capec:             {taxonomy: capec, kb: capec.json}
controls:
  nist_800_53:       {taxonomy: nist_800_53r5, kb: nist-controls.json}
  d3fend:            {taxonomy: d3fend, kb: d3fend.json}
```

KB id readers (shapes checked in the shipped files):

- `techniques` keys for `mitre_attack` and `atlas`;
- `entries[].cwe_id` for `cwe`;
- `entries[].category_id` for the OWASP files;
- `weaknesses` keys for `maswe`;
- `attack_patterns` keys for `capec`;
- `controls` keys for `nist_800_53r5`;
- `entries[].d3fend_id` for `d3fend`.

`system-types.yaml` (asset and identity rows exact; the IaC rows are the starting set CAT4 tunes):

```yaml
version: 1
asset_types:
  service:             {candidates: [web_app, api, serverless, saas, ai_ml, agentic_ai], default: api}
  data_store:          {candidates: [data_store, cloud, saas], default: data_store}
  secret_store:        {candidates: [identity, data_store, cloud], default: identity}
  queue:               {candidates: [b2b_integration, cloud, data_store], default: data_store}
  network:             {candidates: [network, cloud], default: network}
  external_dependency: {candidates: [third_party, saas, b2b_integration], default: third_party}
  compute:             {candidates: [server, cloud, container_k8s, serverless, ai_ml, ci_cd], default: server}
identity_types:
  human_role:          {candidates: [identity, people_process], default: identity}
  service_account:     {candidates: [identity], default: identity}
  workload_identity:   {candidates: [identity], default: identity}
  external_party:      {candidates: [third_party, b2b_integration, identity], default: third_party}
iac_resource_types:    # fnmatch on the Terraform resource type
  - {pattern: "aws_lambda_function", system_types: [serverless, cloud]}
  - {pattern: "aws_eks_cluster", system_types: [container_k8s, cloud]}
  - {pattern: "aws_ecs_*", system_types: [container_k8s, cloud]}
  - {pattern: "kubernetes_*", system_types: [container_k8s]}
  - {pattern: "aws_api_gateway_*", system_types: [api, cloud]}
  - {pattern: "aws_apigatewayv2_*", system_types: [api, cloud]}
  - {pattern: "aws_db_instance", system_types: [data_store, cloud]}
  - {pattern: "aws_rds_cluster", system_types: [data_store, cloud]}
  - {pattern: "aws_dynamodb_table", system_types: [data_store, cloud]}
  - {pattern: "aws_s3_bucket", system_types: [data_store, cloud]}
  - {pattern: "aws_iam_*", system_types: [identity, cloud]}
  - {pattern: "aws_instance", system_types: [server, cloud]}
  - {pattern: "aws_codebuild_project", system_types: [ci_cd, cloud]}
  - {pattern: "aws_sagemaker_*", system_types: [ai_ml, cloud]}
```

Domain-pack system types live in each pack's `threat_profile` (CAT2), so this file carries no pack hints.

`apd-goals.yaml`: `families:` lists all 25 codes. CAT1 writes only the four §8.4 rows: `IA: [ephemeral]`, `LD: [non_repudiation, immutability]`, `AV: [availability, resilient, distributed]` and `OP: [availability, resilient, distributed]`. The other 21 families are `[]`; CAT2 Task 2 fills them. The test below pins only the four rows, so CAT2's values do not break it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_catalog_translate.py
def test_linddun_table_pinned():
    assert dict(LINDDUN_CATALOG_TO_GAUNTLET) == {"L": "L", "I": "I", "Nr": "N_repudiation", "D": "D_etectability",
                                                 "DD": "D_isclosure", "U": "U", "Nc": "N_compliance"}
    assert set(LINDDUN_CATALOG_TO_GAUNTLET.values()) == set(LINDDUN_TO_APD_GOALS)

@pytest.mark.parametrize("key,tax", [("attack_enterprise", "mitre_attack"), ("attack_mobile", "mitre_attack"),
    ("atlas", "atlas"), ("cwe", "cwe"), ("owasp_top10", "owasp_top10"), ("owasp_api", "owasp_api_top10"),
    ("owasp_llm_2025", "owasp_llm_top10"), ("maswe", "maswe"), ("capec", "capec"), ("nist_800_53", "nist_800_53r5"),
    ("d3fend", "d3fend"), ("owasp_llm", None), ("maestro", None), ("hicp", None), ("owasp_agentic", None)])
def test_taxonomy_for(key, tax):
    assert taxonomy_for(key) == tax

def test_taxonomy_map_entries():
    m = taxonomy_map()
    assert len(m) == 11 and [e.key for e in m] == sorted(e.key for e in m)
    assert {e.key for e in m if e.section == "controls"} == {"nist_800_53", "d3fend"}

def test_kb_ids_reads_each_kb():
    assert "T1078.004" in kb_ids("mitre_attack") and "AML.T0051" in kb_ids("atlas") and "CWE-79" in kb_ids("cwe")
    assert "AC-2(1)" in kb_ids("nist_800_53r5") and "D3-MFA" in kb_ids("d3fend") and "CAPEC-66" in kb_ids("capec")
    assert "MASWE-0001" in kb_ids("maswe") and "API1:2023" in kb_ids("owasp_api_top10")
    assert "A01:2025" in kb_ids("owasp_top10") and "LLM01:2025" in kb_ids("owasp_llm_top10")

def test_kb_ids_unknown_taxonomy():
    with pytest.raises(ValueError, match="nope"): kb_ids("nope")

def test_kb_version():
    assert kb_version("atlas") == "5.6.0" and kb_version("owasp_top10") == "2025" and kb_version("owasp_api_top10") == "2023"
    assert kb_version("mitre_attack") is None and kb_version("cwe") is None

@pytest.mark.parametrize("raw,norm", [("AC-2", "AC-2"), ("ac-2", "AC-2"), ("AC-02", "AC-2"), ("AC-2(1)", "AC-2(1)"),
    ("AC-2 (1)", "AC-2(1)"), ("AC-02(01)", "AC-2(1)"), ("AC-2.1", "AC-2(1)"), (" IA-2(1) ", "IA-2(1)"), ("bogus", "BOGUS")])
def test_normalize_nist(raw, norm):
    assert normalize_nist(raw) == norm

# tests/test_catalog_data_files.py
def test_system_types_file():
    d = yaml.safe_load((catalog_data_dir() / "system-types.yaml").read_text())
    inv = read_schema("asset-inventory.schema.json")["properties"]
    assert set(d["asset_types"]) == set(inv["assets"]["items"]["properties"]["asset_type"]["enum"])
    assert set(d["identity_types"]) == set(inv["identities"]["items"]["properties"]["identity_type"]["enum"])
    for spec in [*d["asset_types"].values(), *d["identity_types"].values()]:
        assert spec["default"] in spec["candidates"] and set(spec["candidates"]) <= set(CATALOG_SYSTEM_TYPES)
    assert d["asset_types"]["service"] == {"candidates": ["web_app", "api", "serverless", "saas", "ai_ml", "agentic_ai"], "default": "api"}
    assert d["asset_types"]["compute"] == {"candidates": ["server", "cloud", "container_k8s", "serverless", "ai_ml", "ci_cd"], "default": "server"}
    assert d["asset_types"]["queue"]["default"] == "data_store"
    reachable = {t for spec in [*d["asset_types"].values(), *d["identity_types"].values()] for t in spec["candidates"]}
    assert {"ai_ml", "agentic_ai", "ci_cd"} <= reachable      # AI-only threats (e.g. TC-AG-001) can reach a surface
    rows = {r["pattern"]: r["system_types"] for r in d["iac_resource_types"]}
    assert "serverless" in rows["aws_lambda_function"] and "container_k8s" in rows["aws_eks_cluster"] and "api" in rows["aws_api_gateway_*"]
    assert all(set(v) <= set(CATALOG_SYSTEM_TYPES) for v in rows.values())

def test_apd_goals_file():
    fam = yaml.safe_load((catalog_data_dir() / "apd-goals.yaml").read_text())["families"]
    goals = set(read_schema("_defs.schema.json")["$defs"]["apd_goal"]["enum"])
    assert set(fam) == set(CATALOG_FAMILY_CODES) and all(set(v) <= goals for v in fam.values())
    assert fam["IA"] == ["ephemeral"] and fam["LD"] == ["non_repudiation", "immutability"]
    assert fam["AV"] == fam["OP"] == ["availability", "resilient", "distributed"]

def test_compat_file():
    assert yaml.safe_load((catalog_data_dir() / "compat.yaml").read_text()) == {"catalog_compat": ">=1.1.0,<2.0.0"}

def test_taxonomy_map_kbs_exist():
    assert all((resources.data_dir() / e.kb).is_file() for e in taxonomy_map())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_translate.py tests/test_catalog_data_files.py -v`
Expected: FAIL (module and data files missing)

- [ ] **Step 3: Write the data files and implement `translate.py`**

`normalize_nist` uses `^\s*([A-Za-z]{2})-0*(\d+)(?:\s*\(\s*0*(\d+)\s*\)|\.0*(\d+))?\s*$`. A non-matching input is returned stripped and uppercased, so the KB check then reports it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_translate.py tests/test_catalog_data_files.py -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/threat-catalog/compat.yaml tools/apd_gauntlet/data/threat-catalog/system-types.yaml tools/apd_gauntlet/data/threat-catalog/apd-goals.yaml tools/apd_gauntlet/data/threat-catalog/taxonomy-map.yaml tools/apd_gauntlet/catalog/translate.py tests/test_catalog_translate.py tests/test_catalog_data_files.py
git commit -m "feat(catalog): add taxonomy map, system types, APD goal hints and translation helpers"
```

### Task 7: Catalog model, release schema and synthetic fixtures

**Files:**

- Create: `tools/apd_gauntlet/catalog/model.py`, `tools/apd_gauntlet/data/threat-catalog/open.schema.json`, `tests/fixtures/threat_catalog/{full.json,open.json,open.provenance.json,open.schema.json}`
- Modify: `tools/apd_gauntlet/catalog/__init__.py` (export `MappingRef`, `Threat`, `Catalog`), `tools/apd_gauntlet/data/schemas/_defs.schema.json` (`catalog_threat_id`), `docs/schema-evolution.md`
- Test: `tests/test_catalog_model.py`, `tests/test_catalog_fixtures.py`

**Interfaces:**

- Consumes: `CATALOG_SYSTEM_TYPES`, `CATALOG_FAMILY_CODES` (Task 1); `taxonomy_map` (Task 6)
- Produces (`model.py`, as the CAT brief fixes them, without `source` and `stub`):
  - `@dataclass(frozen=True) class MappingRef: id: str; name: str; fit: Literal["primary", "partial"]`
  - `@dataclass(frozen=True) class Threat: id: str; name: str; family: str; family_name: str; abstraction: str; kind: str; summary: str; parent: str | None; children: tuple[str, ...]; system_types: tuple[str, ...]; stride: tuple[str, ...]; linddun: tuple[str, ...]; impacts: tuple[str, ...]; related: tuple[str, ...]; mappings: Mapping[str, tuple[MappingRef, ...]]; controls: Mapping[str, tuple[MappingRef, ...]]; attack_tactics: tuple[str, ...]`. `linddun` holds catalog codes; there is no `source`, `stub` or `hitrust` field.
  - `@dataclass(frozen=True) class Catalog: edition: Literal["open", "full"]; version: str; sha256: str; threats: Mapping[str, Threat]; frameworks: Mapping[str, Mapping[str, Any]]; fallback_from: str | None; warnings: tuple[str, ...]`
  - Methods `by_system_type(t: str)`, `by_stride(letter: str)`, `by_mapping(key: str, mapping_id: str)` and `by_linddun(code: str)`, each `-> tuple[Threat, ...]` sorted by threat id. Indexes are built once per instance with `functools.cached_property`. `by_mapping` searches `mappings` and `controls`.
  - `def build_catalog(doc: Mapping[str, Any], *, edition: Literal["open", "full"], sha256: str, fallback_from: str | None = None, warnings: Sequence[str] = ()) -> Catalog`. It reads only the `Threat` fields plus `catalog.version` and `frameworks`, and never touches `hitrust`, `hitrust_crosswalk` or any `frameworks` key containing "hitrust" (case-insensitive). `children`, `related` and every `MappingRef` tuple are sorted by id; the other tuples keep file order. All mappings are read-only (`types.MappingProxyType`).
- `_defs.schema.json` gains `catalog_threat_id` (`{"type": "string", "pattern": "^TC-[A-Z]{2}-\\d{3}$"}`) for CAT2 and CAT3 (spec §9).

Schema. `open.schema.json` is the 1.1.0 release's `threat-catalog.schema.json`, byte for byte: no derivation, and no added `stub` property. Prerequisite: the catalog release from the master plan's operator work (register A7.24) is published. No full-edition schema is committed; a local file validates against this one. Task 10's refresh replaces it on each refresh.

Fixtures have the 1.1.0 shape: `catalog.version: 1.1.0`, `generated: 2026-10-14`, and `catalog.counts` exactly `{threats, families, mappings}`, with `mappings` counted as the 1.1.0 build does (UNVERIFIED rule). `open.json` holds 24 threats. All 24 are complete, with synthetic prose (`summary`, `description`, `example`) and no `hitrust`, `source`, `stub` or `hitrust_crosswalk`; mapping names are copied from the KBs. These rows are fixed ("p" = primary):

| Id | Fam | Abstraction | Kind | Links | STRIDE | LINDDUN | System types | Mappings; controls |
|---|---|---|---|---|---|---|---|---|
| `TC-AC-001` | AC | class | event | children 002, 003 | E | — | web_app, api | attack_enterprise T1078 p; owasp_top10 A01:2025 p; cwe CWE-862 p; nist_800_53 AC-3 p, AC-6 partial |
| `TC-AC-002` | AC | technique | event | parent 001 | E | — | api | attack_enterprise T1078.004 p; owasp_api API1:2023 p; d3fend D3-UAP p |
| `TC-AC-003` | AC | technique | condition | parent 001 | E, T | — | web_app | cwe CWE-306 p; nist_800_53 AC-3 p |
| `TC-IA-001` | IA | technique | event | related AC-001 | S | — | identity, api | attack_enterprise T1110.003 p; nist_800_53 IA-02(01) p, d3fend D3-MFA p |
| `TC-IN-001` | IN | technique | event | — | T, I | — | api, web_app | cwe CWE-89 p, CWE-99999 partial (absent from `cwe.json` on purpose); capec CAPEC-66 p |
| `TC-DP-001` | DP | class | condition | — | I | D, DD | data_store | cwe CWE-200 p; nist_800_53 SC-28 p |
| `TC-DP-002` | DP | technique | event | — | I | L, I, Nr, U, Nc | data_store, api | nist_800_53 AC-3 partial |
| `TC-AI-001` | AI | technique | event | — | T, E | — | ai_ml, api | owasp_llm_2025 LLM01:2025 p; atlas AML.T0051 p; nist_800_53 SI-10 p |
| `TC-AG-001` | AG | technique | event | — | E | — | agentic_ai | maestro L3 p; owasp_agentic AGT-01 p (synthetic); nist_800_53 AC-6 p |
| `TC-EN-001` | EN | outcome | hazard | — | D | — | physical_facility | nist_800_53 CP-9 p |
| `TC-LG-001` | LG | outcome | consequence | — | — | Nc | people_process | — |
| `TC-NW-001` | NW | technique | event | — | I, T | — | network | attack_enterprise T1565 partial; nist_800_53 SC-8 p |
| `TC-OP-001` | OP | class | hazard | — | D | — | cloud, server | hicp HICP-T01 p (synthetic); controls hicp HICP-P01 p (synthetic), nist_800_53 CP-9 p |

The other eleven threats are `TC-AV-001`, `TC-SC-001`, `TC-CL-001`, `TC-CR-001`, `TC-LD-001`, `TC-MB-001`, `TC-RC-001`, `TC-SE-001`, `TC-IS-001`, `TC-MW-001` and `TC-IA-002`. Each is `technique` and `event`, with no parent and STRIDE and system types chosen from the vocabularies. They map only to ids present in the KBs, for example T1499, T1195, T1530, T1059, T1606, AU-2 and MASWE-0001.

The remaining blocks:

- `frameworks` has an entry for every key used, with `version: null`.
- `families` lists the 25 families from the CAT brief's families file, each with its fixture count.

`full.json` is `open.json` plus `TC-OT-901`: OT family, `technique`, `event`, `system_types: [ot_ics]`, STRIDE `T`, controls `nist_800_53` SI-7 primary (present in the KB). Its counts are `threats: 25`, and the OT family count is one higher. `open.provenance.json` is `{"source": "https://github.com/illusconsulting/threat-catalog/releases/download/v1.1.0/threat-catalog-1.1.0.json", "source_sha256": <sha256 of open.json>, "fetched_at": "2026-10-11", "version": "1.1.0"}`. The fixture `open.schema.json` is a copy of the data schema. `TC-AG-001`'s `maestro` mapping uses the confirmed id form (`L3`); one of the free rows adds a `maestro` `CL` (cross-layer) mapping.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_catalog_model.py
FIX = REPO / "tests/fixtures/threat_catalog"
@pytest.fixture
def full_doc(): return json.loads((FIX / "full.json").read_text())
@pytest.fixture
def open_doc(): return json.loads((FIX / "open.json").read_text())

def test_build_full(full_doc):
    cat = build_catalog(full_doc, edition="full", sha256="0" * 64)
    assert len(cat.threats) == 25 and cat.version == "1.1.0" and cat.edition == "full"
    t = cat.threats["TC-AC-001"]
    assert t.children == ("TC-AC-002", "TC-AC-003") and t.parent is None and t.abstraction == "class"
    assert cat.threats["TC-DP-001"].linddun == ("D", "DD")
    assert cat.threats["TC-IN-001"].mappings["cwe"] == (MappingRef("CWE-89", ANY_NAME, "primary"), MappingRef("CWE-99999", ANY_NAME, "partial"))

def test_open_threat_complete(open_doc):
    t = build_catalog(open_doc, edition="open", sha256="0" * 64).threats["TC-IA-001"]
    assert t.summary and t.mappings["attack_enterprise"][0].id == "T1110.003"

def test_indexes_sorted(full_doc):
    cat = build_catalog(full_doc, edition="full", sha256="0" * 64)
    for res in (cat.by_system_type("api"), cat.by_stride("E"), cat.by_linddun("DD")):
        assert [t.id for t in res] == sorted(t.id for t in res)
    assert {"TC-AC-001", "TC-AC-002", "TC-AC-003", "TC-AI-001", "TC-AG-001"} <= {t.id for t in cat.by_stride("E")}
    assert [t.id for t in cat.by_mapping("attack_enterprise", "T1110.003")] == ["TC-IA-001"]
    assert [t.id for t in cat.by_mapping("maestro", "L3")] == ["TC-AG-001"]
    assert [t.id for t in cat.by_mapping("nist_800_53", "SC-28")] == ["TC-DP-001"]

def test_reordered_threats_build_equal_catalog(full_doc):
    rev = {**full_doc, "threats": list(reversed(full_doc["threats"]))}
    assert build_catalog(rev, edition="full", sha256="0" * 64) == build_catalog(full_doc, edition="full", sha256="0" * 64)

def test_model_has_no_source_stub_or_lineage_fields(full_doc):
    names = {f.name for cls in (MappingRef, Threat, Catalog) for f in dataclasses.fields(cls)}
    assert not names & {"source", "stub", "hitrust", "hitrust_crosswalk", "lineage"}
    keys, _ = walk(build_catalog(full_doc, edition="full", sha256="0" * 64))
    assert not any("hitrust" in k.lower() for k in keys)
```

`ANY_NAME` is an object equal to any string. `walk(obj) -> tuple[set[str], set[str]]` collects mapping keys, dataclass field names and string values recursively through dataclasses, Mappings and tuples.

```python
# tests/test_catalog_fixtures.py
def test_open_fixture_valid(): assert not list(_validator("open.schema.json").iter_errors(_load("open.json")))

def test_full_fixture_is_open_plus_extension():
    full, opn = _load("full.json"), _load("open.json")
    assert {k: v for k, v in full.items() if k not in ("threats", "catalog", "families")} == {k: v for k, v in opn.items() if k not in ("threats", "catalog", "families")}
    by_id = {t["id"]: t for t in full["threats"]}
    assert sorted(by_id) == sorted([t["id"] for t in opn["threats"]] + ["TC-OT-901"])
    assert all(by_id[t["id"]] == t for t in opn["threats"])
    ot = by_id["TC-OT-901"]
    assert ot["family"] == "OT" and ot["system_types"] == ["ot_ics"] and ot["stride"] == ["T"]
    assert full["catalog"]["counts"]["threats"] == 25 and opn["catalog"]["counts"]["threats"] == 24

def test_fixture_coverage():
    ts = _load("open.json")["threats"]
    assert len(ts) == 24 and {t["abstraction"] for t in ts} == {"outcome", "class", "technique"}
    assert {t["kind"] for t in ts} == {"event", "condition", "hazard", "consequence"}
    assert "EN" in {t["family"] for t in ts}
    assert {"D", "DD"} <= {c for t in ts for c in t["linddun"]}
    assert {"attack_enterprise", "cwe", "owasp_top10", "owasp_llm_2025", "owasp_agentic", "maestro", "hicp"} <= {k for t in ts for k in t["mappings"]}
    assert {"nist_800_53", "d3fend"} <= {k for t in ts for k in t["controls"]}

def test_fixture_provenance_matches():
    prov = _load("open.provenance.json")
    assert prov["source_sha256"] == hashlib.sha256((FIX / "open.json").read_bytes()).hexdigest() and prov["version"] == "1.1.0"

def test_open_schema_meta_valid(): Draft202012Validator.check_schema(json.loads((catalog_data_dir() / "open.schema.json").read_text()))

def test_no_full_schema_vendored():
    assert not (catalog_data_dir() / "full.schema.json").exists() and not (FIX / "full.schema.json").exists()

def test_open_schema_vocabularies_match():
    s = json.loads((catalog_data_dir() / "open.schema.json").read_text())["$defs"]["threat"]["properties"]
    assert tuple(s["system_types"]["items"]["enum"]) == CATALOG_SYSTEM_TYPES
    assert {e.key for e in taxonomy_map() if e.section == "mappings"} <= set(s["mappings"]["propertyNames"]["enum"])
    assert {e.key for e in taxonomy_map() if e.section == "controls"} <= set(s["controls"]["propertyNames"]["enum"])

def test_defs_catalog_threat_id():
    assert read_schema("_defs.schema.json")["$defs"]["catalog_threat_id"]["pattern"] == r"^TC-[A-Z]{2}-\d{3}$"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_model.py tests/test_catalog_fixtures.py -v`
Expected: FAIL (module, schema and fixtures missing)

- [ ] **Step 3: Write the schema and fixtures, and implement `model.py`**

Schema-evolution entry: `_defs` gains `catalog_threat_id` (additive). The catalog's open schema is vendored data, not a gauntlet schema.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_model.py tests/test_catalog_fixtures.py tests/test_meta_schemas.py tests/test_schema_vocab_centralized.py -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/model.py tools/apd_gauntlet/catalog/__init__.py tools/apd_gauntlet/data/threat-catalog/open.schema.json tools/apd_gauntlet/data/schemas/_defs.schema.json docs/schema-evolution.md tests/fixtures/threat_catalog tests/test_catalog_model.py tests/test_catalog_fixtures.py
git commit -m "feat(catalog): add frozen threat model, release schema and fixtures"
```

### Task 8: `validate_catalog_file` (§12.1)

**Files:**

- Create: `tools/apd_gauntlet/catalog/load.py`
- Modify: `tests/conftest.py` (WS2 Task 2 creates it)
- Test: `tests/test_catalog_validate.py`

**Interfaces:**

- Consumes: `catalog_data_dir` (Task 1); `build_domain_skill._version_in_range` (`tools/apd_gauntlet/build_domain_skill.py:85-91`)
- Produces:
  - conftest fixture `catalog_fixture_dir` (session scope) → `REPO / "tests/fixtures/threat_catalog"`
  - conftest fixture `catalog_fixture_copy` → `Callable[..., Path]` with keyword `corrupt_sha: bool = False`. It copies the fixture directory to a fresh `tmp_path` subdirectory. With `corrupt_sha=True`, it sets `open.provenance.json` `source_sha256` to 64 zeros.
  - `class CatalogError(Exception)`
  - `MAX_CATALOG_BYTES = 20 * 1024 * 1024`
  - `def validate_catalog_file(path: Path, *, edition: Literal["open", "full"], provenance: Path | None, schema_dir: Path | None = None) -> list[str]`. Both editions use `(schema_dir or catalog_data_dir()) / "open.schema.json"`; no full-edition schema exists.
  - `def hitrust_errors(doc: Any, *, text: bool) -> list[str]` (check 3; sorted; at most 20). With `text=True` (the vendored `open` file) it also reports string values containing `hitrust`.
  - `def reference_errors(doc: Mapping[str, Any]) -> list[str]` (check 5), which also compares `catalog.counts.threats` and `.families` with the array lengths when `catalog.counts` is present

Checks run in the §12.1 order. Checks 1–4 stop at the first failure, and checks 5–7 accumulate. Check 3 runs `hitrust_errors(doc, text=edition == "open")`; check 7 applies to the vendored `open` file only. A schema file that is missing or not a valid JSON Schema is an error. Messages, which the tests match on:

1. `"<name> is <n> bytes; the limit is <MAX_CATALOG_BYTES> (20 MB)"`
2. `"<name> is not valid JSON: …"`
3. `"hitrust key at <path>"`; `"hitrust text at <path>"` (open only); `"<id> carries <source|stub>, a pre-1.1.0 field"`
4. `"schema: <json path>: <message>"`, at most 20, sorted by path
5. `"duplicate id <id>"`, `"malformed id <id>"`, `"<id>: parent|child|related <ref> does not resolve"`, `"catalog.counts.threats <n> does not match <m> threats"`, `"catalog.counts.families <n> does not match <m> families"`
6. `"catalog version <v> is outside catalog_compat <spec>"`
7. `"open.provenance.json not found"`, `"open.provenance.json lacks <key>"` (keys `source`, `source_sha256`, `fetched_at`, `version`), `"<name> sha256 <a> does not match open.provenance.json source_sha256 <b>"`, `"open.provenance.json version <a> does not match catalog version <b>"`

- [ ] **Step 1: Write the failing tests**

```python
def test_fixtures_validate_clean(catalog_fixture_dir):
    d = catalog_fixture_dir
    assert validate_catalog_file(d / "open.json", edition="open", provenance=d / "open.provenance.json", schema_dir=d) == []
    assert validate_catalog_file(d / "full.json", edition="full", provenance=None, schema_dir=d) == []

def test_oversize_refused(tmp_path, monkeypatch, catalog_fixture_dir):
    monkeypatch.setattr(load_mod, "MAX_CATALOG_BYTES", 10)
    (err,) = validate_catalog_file(catalog_fixture_dir / "full.json", edition="full", provenance=None, schema_dir=catalog_fixture_dir)
    assert "the limit is 10" in err

def test_not_json(tmp_path, catalog_fixture_dir):
    p = tmp_path / "x.json"; p.write_text("{nope")
    (err,) = validate_catalog_file(p, edition="full", provenance=None, schema_dir=catalog_fixture_dir)
    assert "not valid JSON" in err

def test_schema_errors_reported(tmp_path, catalog_fixture_dir):
    errs = _validate_mutated(tmp_path, catalog_fixture_dir, "full", lambda d: d.pop("families"))
    assert errs and all(e.startswith("schema:") for e in errs)

def test_reference_errors():
    doc = {"threats": [{"id": "TC-AC-001", "parent": "TC-AC-999", "children": ["TC-AC-001"], "related": ["TC-ZZ-001"]},
                       {"id": "TC-AC-001", "parent": None, "children": [], "related": []}]}
    errs = reference_errors(doc)
    assert "duplicate id TC-AC-001" in errs and "TC-AC-001: parent TC-AC-999 does not resolve" in errs
    assert "TC-AC-001: related TC-ZZ-001 does not resolve" in errs

@pytest.mark.parametrize("version", ["1.0.0", "2.0.0"])
def test_version_outside_compat(tmp_path, catalog_fixture_dir, version):
    errs = _validate_mutated(tmp_path, catalog_fixture_dir, "full", lambda d: d["catalog"].update(version=version))
    assert f"catalog version {version} is outside catalog_compat >=1.1.0,<2.0.0" in errs

def test_provenance_sha_mismatch(catalog_fixture_copy):
    d = catalog_fixture_copy(corrupt_sha=True)
    errs = validate_catalog_file(d / "open.json", edition="open", provenance=d / "open.provenance.json", schema_dir=d)
    assert any("does not match open.provenance.json source_sha256" in e for e in errs)

@pytest.mark.parametrize("edition", ["open", "full"])
@pytest.mark.parametrize("mutate", [lambda d: d["threats"][0].update(hitrust={"ids": ["X1"]}),   # a threat-level block
                                    lambda d: d.update(hitrust_crosswalk=[])])                   # a top-level crosswalk
def test_hitrust_key_refused_in_both_editions(tmp_path, catalog_fixture_dir, edition, mutate):
    (err,) = _validate_mutated(tmp_path, catalog_fixture_dir, edition, mutate, with_provenance=edition == "open")
    assert err.startswith("hitrust key at ")

def _leak_hitrust_text(d):
    d["threats"][0].update(summary="Mapped from HITRUST control 01.a")

def test_hitrust_text_refused_in_open_only(tmp_path, catalog_fixture_dir):
    (err,) = _validate_mutated(tmp_path / "o", catalog_fixture_dir, "open", _leak_hitrust_text, with_provenance=True)
    assert err.startswith("hitrust text at ")
    assert _validate_mutated(tmp_path / "f", catalog_fixture_dir, "full", _leak_hitrust_text) == []

@pytest.mark.parametrize("field,value", [("source", "added"), ("stub", False)])
def test_pre_1_1_shape_refused(tmp_path, catalog_fixture_dir, field, value):
    tid = json.loads((catalog_fixture_dir / "full.json").read_text())["threats"][0]["id"]
    errs = _validate_mutated(tmp_path, catalog_fixture_dir, "full", lambda d: d["threats"][0].update({field: value}))
    assert errs == [f"{tid} carries {field}, a pre-1.1.0 field"]

def test_counts_must_match(tmp_path, catalog_fixture_dir):
    errs = _validate_mutated(tmp_path, catalog_fixture_dir, "full", lambda d: d["catalog"]["counts"].update(threats=1, families=2))
    assert "catalog.counts.threats 1 does not match 25 threats" in errs
    assert "catalog.counts.families 2 does not match 25 families" in errs
```

The test file's own helpers:

- `_validate_mutated(tmp_path, fixture_dir, edition, mutate, with_provenance=False)` copies the fixture directory, applies `mutate` to the edition's JSON, rehashes the provenance when asked, and validates;
- `open_doc` and `full_doc` are fixtures that load `open.json` and `full.json` fresh.

Step 1 also adds `catalog_fixture_dir` and `catalog_fixture_copy` to `tests/conftest.py`; Task 9 adds `load_fixture_catalog` beside them.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_validate.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.catalog.load`)

- [ ] **Step 3: Implement the validation half of `load.py`**

Hash the bytes read once, parse them once, and validate with `Draft202012Validator(schema)`. The open schema carries no external `$ref`. Nothing in `load.py` reads the content of a `hitrust` key: `hitrust_errors` only reports where one is.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_validate.py -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/load.py tests/conftest.py tests/test_catalog_validate.py
git commit -m "feat(catalog): validate catalog files in the seven load-time checks"
```

### Task 9: `load_catalog` with edition fallback and full-path rules

**Files:**

- Modify: `tools/apd_gauntlet/catalog/load.py`, `tools/apd_gauntlet/catalog/__init__.py` (export `load_catalog`), `tests/conftest.py` (WS2), `docs/running-the-gauntlet.md` (the Task 1 section gains the full-path rules)
- Test: `tests/test_catalog_load.py`

**Interfaces:**

- Consumes: `CatalogConfig`, `catalog_data_dir` (Task 1); `build_catalog` (Task 7); `validate_catalog_file`, `CatalogError` (Task 8); `resources.data_dir`
- Produces:
  - `VENDORED_NOT_INSTALLED = "vendored catalog not installed (tools/apd_gauntlet/data/threat-catalog/open.json); run 'apd-gauntlet refresh-threat-catalog'"`
  - `def check_full_path(path: Path, *, run_dir: Path | None) -> tuple[str | None, str | None]` — `(refusal, warning)`:
    - `"<path> is inside the installed package"` (under `resources.data_dir().parent`);
    - `"<path> is inside the run directory"`;
    - the warning `"<path> is inside a git working tree and is not ignored by git; never commit a local catalog"` when `git -c core.fsmonitor=false -C <parent> check-ignore -q <path>` exits 1. A tracked file counts as not ignored. Exit 0, exit 128 or no `git` on PATH gives no warning.
  - `def load_catalog(cfg: CatalogConfig, *, data_dir: Path | None = None, run_dir: Path | None = None, warnings_out: list[str] | None = None) -> Catalog | None`. `data_dir` defaults to `catalog_data_dir()` and holds `open.json`, `open.provenance.json` and `open.schema.json`, which validates full files too; `compat.yaml` always comes from the package. `warnings_out` (when given) receives every warning, including on a `None` return. CAT2's `catalog scope` writes `catalog: null` plus those warnings, and treats `None` as `off`.
  - conftest fixture `load_fixture_catalog` → `Callable[[Literal["open", "full"]], Catalog]`. For `"open"` it loads with `data_dir=catalog_fixture_dir` (Task 8). For `"full"` it copies `full.json` into a `tmp_path_factory` directory outside any git tree, so the git warning never appears, and loads with `data_dir=catalog_fixture_dir`.

Flow:

1. `full`: refusal, then a missing `path`, then a missing file, then validation errors each fall back to the open edition. They add the warning `"threat_catalog full: <reason>; using the open edition"`; the reasons are the refusal, `"edition full requires threat_catalog.path"`, `"<path> not found"` and `"<path> is invalid (<first error>; <n> errors)"`. A valid file returns `build_catalog(doc, edition="full", …)` with the git warning, if any.
2. Open (directly or as fallback): if `<data>/open.json` is absent, the loader appends `VENDORED_NOT_INSTALLED` and returns `None`.
3. Otherwise, validation errors raise `CatalogError("vendored open catalog invalid: " + "; ".join(errs))`.
4. Otherwise it returns `edition="open"`, with `fallback_from="full"` after a fallback, and the warnings.

- [ ] **Step 1: Write the failing tests**

```python
OPEN = CatalogConfig("open", None, (), ())
def full(p): return CatalogConfig("full", p, (), ())

def test_load_open_fixture(load_fixture_catalog, catalog_fixture_dir):
    cat = load_fixture_catalog("open")
    assert cat.edition == "open" and cat.fallback_from is None and cat.warnings == ()
    assert cat.sha256 == hashlib.sha256((catalog_fixture_dir / "open.json").read_bytes()).hexdigest()

def test_load_full_fixture(load_fixture_catalog):
    cat = load_fixture_catalog("full"); assert cat.edition == "full" and cat.warnings == ()

def test_open_not_installed_returns_none_with_warning(tmp_path):
    out: list[str] = []
    assert load_catalog(OPEN, data_dir=tmp_path, warnings_out=out) is None and out == [VENDORED_NOT_INSTALLED]

def test_packaged_open_until_vendored():
    if (catalog_data_dir() / "open.json").exists(): pytest.skip("vendored catalog installed")
    assert load_catalog(OPEN) is None

def test_vendored_invalid_raises(catalog_fixture_copy):
    with pytest.raises(CatalogError, match="sha256"): load_catalog(OPEN, data_dir=catalog_fixture_copy(corrupt_sha=True))

def test_full_missing_falls_back(tmp_path, catalog_fixture_dir):
    cat = load_catalog(full(tmp_path / "nope.json"), data_dir=catalog_fixture_dir)
    assert cat.edition == "open" and cat.fallback_from == "full" and "not found" in cat.warnings[0]

def test_full_without_path_falls_back(catalog_fixture_dir):
    assert "requires threat_catalog.path" in load_catalog(full(None), data_dir=catalog_fixture_dir).warnings[0]

def test_full_invalid_falls_back(tmp_path, catalog_fixture_dir):
    p = _write_full_with_duplicate_id(tmp_path, catalog_fixture_dir)
    w = load_catalog(full(p), data_dir=catalog_fixture_dir).warnings[0]
    assert "is invalid" in w and "using the open edition" in w

def test_full_with_hitrust_key_falls_back(tmp_path, catalog_fixture_dir):
    doc = json.loads((catalog_fixture_dir / "full.json").read_text()); doc["threats"][0]["hitrust"] = {"ids": ["X1"]}
    p = tmp_path / "local.json"; p.write_text(json.dumps(doc))
    cat = load_catalog(full(p), data_dir=catalog_fixture_dir)
    assert cat.edition == "open" and cat.fallback_from == "full" and "hitrust key" in cat.warnings[0]

def test_full_inside_package_refused(catalog_fixture_dir):
    p = resources.data_dir() / "threat-catalog" / "full.json"
    assert "inside the installed package" in load_catalog(full(p), data_dir=catalog_fixture_dir).warnings[0]

def test_full_inside_run_dir_refused(tmp_path, catalog_fixture_dir):
    run = tmp_path / "run"; (run / "inputs").mkdir(parents=True)
    p = shutil.copy(catalog_fixture_dir / "full.json", run / "inputs/full.json")
    cat = load_catalog(full(Path(p)), data_dir=catalog_fixture_dir, run_dir=run)
    assert cat.edition == "open" and "inside the run directory" in cat.warnings[0]

@needs_git
def test_full_in_unignored_git_tree_warns(tmp_path, catalog_fixture_dir):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    p = shutil.copy(catalog_fixture_dir / "full.json", tmp_path / "full.json")
    cat = load_catalog(full(Path(p)), data_dir=catalog_fixture_dir)
    assert cat.edition == "full" and any("not ignored by git" in w for w in cat.warnings)

@needs_git
def test_full_in_ignored_git_tree_no_warning(tmp_path, catalog_fixture_dir):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True); (tmp_path / ".gitignore").write_text("full.json\n")
    p = shutil.copy(catalog_fixture_dir / "full.json", tmp_path / "full.json")
    assert load_catalog(full(Path(p)), data_dir=catalog_fixture_dir).warnings == ()

def test_full_and_open_missing_returns_none_with_both_warnings(tmp_path):
    out: list[str] = []
    assert load_catalog(full(tmp_path / "nope.json"), data_dir=tmp_path, warnings_out=out) is None
    assert len(out) == 2 and out[1] == VENDORED_NOT_INSTALLED

def test_r2_exports():
    from apd_gauntlet.catalog import Catalog, Threat, catalog_config_from_run_config, load_catalog, load_selection_params  # noqa: F401
```

`needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")`. `_write_full_with_duplicate_id(tmp_path, fixture_dir) -> Path` writes a copy of `full.json` whose second threat repeats the first id.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_load.py -v`
Expected: FAIL (`load_catalog` not defined; `load_fixture_catalog` fixture missing)

- [ ] **Step 3: Implement `check_full_path`, `load_catalog`, the conftest fixtures and the doc paragraph**

Paths are compared after `Path.resolve()`, using `is_relative_to`. The `git` call uses `subprocess.run([...], capture_output=True, timeout=10, check=False)`. The doc paragraph covers the three refusal and warning cases and the fallback.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_load.py tests/test_catalog_validate.py -v && mypy tools/ && markdownlint-cli2 docs/running-the-gauntlet.md`
Expected: PASS; mypy clean; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/load.py tools/apd_gauntlet/catalog/__init__.py tests/conftest.py tests/test_catalog_load.py docs/running-the-gauntlet.md
git commit -m "feat(catalog): load catalogs with full-to-open fallback and full-path guards"
```

### Task 10: `refresh-threat-catalog`

**Files:**

- Create: `tools/apd_gauntlet/refresh_threat_catalog.py`, `tests/fixtures/kb_golden/threat_catalog/open.provenance.json`
- Modify: `tools/apd_gauntlet/cli.py` (after `refresh-capec`, `cli.py:709-716`), `docs/taxonomy-mappings.md` ("Reference-data refresh", `:189-207`), `CHANGELOG.md`
- Test: `tests/test_refresh_threat_catalog.py` (create), `tests/test_refresh_byte_stable.py` (extend)

**Interfaces:**

- Consumes: the size-cap discipline of `kb_fetch.fetch_pinned` (`tools/apd_gauntlet/kb_fetch.py:23-59`; `kb_fetch` itself is unchanged, because it sends no headers and other refreshers' tests patch its `urlopen`); `validate_catalog_file`, `CatalogError` (Task 8); `catalog_data_dir` (Task 1)
- Produces:
  - `RELEASE_BASE = "https://github.com/illusconsulting/threat-catalog/releases/download"`; `LATEST_API = "https://api.github.com/repos/illusconsulting/threat-catalog/releases/latest"`; `MAX_RESPONSE_BYTES = 20 * 1024 * 1024`; `DEFAULT_TIMEOUT_SECONDS = 60`
  - `TOKEN_HOSTS = frozenset({"github.com", "api.github.com", "objects.githubusercontent.com"})`
  - `def asset_names(version: str) -> dict[str, str]` → `{"catalog": f"threat-catalog-{version}.json", "schema": "threat-catalog.schema.json", "sums": "SHA256SUMS"}`; the asset URL is `f"{RELEASE_BASE}/v{version}/{name}"`. Staging writes the catalog and schema assets as `open.json` and `open.schema.json`.
  - `def auth_headers(url: str, token: str | None) -> dict[str, str]` → `{"Authorization": f"Bearer {token}"}` only when `token` is set, the scheme is `https` and `urlsplit(url).hostname` (lowercased) is exactly in `TOKEN_HOSTS`; otherwise `{}`
  - `class ScopedAuthRedirectHandler(urllib.request.HTTPRedirectHandler)` with `__init__(self, token: str | None)`. `redirect_request` builds the follow-up request with the parent's logic, removes `Authorization` from its headers and unredirected headers, then adds back only `auth_headers(newurl, token)`.
  - `def fetch_asset(url: str, *, token: str | None = None) -> bytes` (the test seam): an opener built with `ScopedAuthRedirectHandler(token)`, the request carrying `auth_headers(url, token)`, and the same Content-Length and post-read caps as `fetch_pinned`
  - `def latest_version(*, token: str | None = None) -> str` (`tag_name` from `LATEST_API` through `fetch_asset`, leading `v` stripped)
  - `def parse_sha256sums(text: str) -> dict[str, str]` (lines `<64 hex>␠␠<name>`; `CatalogError` on a malformed line)
  - `@dataclass(frozen=True) class CatalogDiff: added: tuple[str, ...]; removed: tuple[str, ...]; changed: tuple[str, ...]; mapping_counts: dict[str, tuple[int, int]]`
  - `def diff_catalogs(old: Mapping[str, Any] | None, new: Mapping[str, Any]) -> CatalogDiff` — ids sorted; `changed` = same id, different canonical JSON; counts per mapping and control key, `(old, new)`
  - `def render_diff(d: CatalogDiff) -> list[str]` — lines `added: <n> (<ids, comma-separated>)`, `removed: …`, `changed: …`, then `mappings <key>: <old> -> <new>` per key
  - `@dataclass(frozen=True) class RefreshResult: version: str; written: tuple[Path, ...]; diff: CatalogDiff`
  - `def refresh_threat_catalog(version: str | None = None, *, output_dir: Path | None = None, dry_run: bool = False, fetched_at: str | None = None, token: str | None = None) -> RefreshResult`
  - CLI `refresh-threat-catalog [--version X.Y.Z] [--dry-run] [--out-dir DIR] [--token-env NAME]`:
    - `--token-env` defaults to `GITHUB_TOKEN`; the token is `os.environ.get(NAME)`, and an unset variable means an anonymous download;
    - the token never appears in output or error messages;
    - exit 0 on success;
    - exit 1 on `CatalogError`, `ValueError` or `OSError`, with one stderr line;
    - exit 2 when `--version` does not match `^\d+\.\d+\.\d+$`.

Flow:

1. Resolve the version.
2. Fetch the three assets.
3. Check that the two content assets each have a `SHA256SUMS` entry that matches their bytes.
4. Stage `open.json` (the downloaded bytes, unchanged), `open.schema.json` and `open.provenance.json` in a `tempfile.TemporaryDirectory`. The provenance is `{source, source_sha256, fetched_at, version}`, written with `json.dumps(…, indent=2, sort_keys=True) + "\n"`; `fetched_at` defaults to today's ISO date.
5. Run `validate_catalog_file(staged/open.json, edition="open", provenance=staged/open.provenance.json, schema_dir=staged)`, and check that the file's `catalog.version` equals the requested version.
6. Diff against the current `<output_dir>/open.json`, when there is one.
7. With `--dry-run`, print the diff and `dry run: nothing written`, and stop. Otherwise move each staged file into place with `os.replace`.

- [ ] **Step 1: Write the failing tests**

```python
def _assets(fix, *, version="1.1.0", open_bytes=None, bad_sum=None):
    files = {f"threat-catalog-{version}.json": open_bytes or (fix / "open.json").read_bytes(),
             "threat-catalog.schema.json": (fix / "open.schema.json").read_bytes()}
    sums = "".join(f"{bad_sum if bad_sum == n else hashlib.sha256(b).hexdigest()}  {n}\n" for n, b in files.items())
    return {**files, "SHA256SUMS": sums.encode()}

@pytest.fixture
def served(monkeypatch, catalog_fixture_dir):
    def serve(**kw):
        a = _assets(catalog_fixture_dir, **kw)
        monkeypatch.setattr(rtc, "fetch_asset", lambda url, **k: a[url.rsplit("/", 1)[1]])
    return serve

def test_refresh_writes_byte_identical_open_and_provenance(served, tmp_path, catalog_fixture_dir):
    served(); res = refresh_threat_catalog("1.1.0", output_dir=tmp_path, fetched_at="2026-10-11")
    assert (tmp_path / "open.json").read_bytes() == (catalog_fixture_dir / "open.json").read_bytes()
    assert {p.name for p in res.written} == {"open.json", "open.schema.json", "open.provenance.json"}

@pytest.mark.parametrize("url,sent", [
    ("https://github.com/illusconsulting/threat-catalog/releases/download/v1.1.0/SHA256SUMS", True),
    ("https://api.github.com/repos/illusconsulting/threat-catalog/releases/latest", True),
    ("https://objects.githubusercontent.com/github-production-release-asset/x", True),
    ("https://release-assets.githubusercontent.com/x", False), ("http://github.com/x", False),
    ("https://github.com.evil.example/x", False), ("https://evil.example/?next=https://github.com", False)])
def test_token_scoped_to_github_hosts(url, sent):
    assert ("Authorization" in auth_headers(url, "tok-123")) is sent
    assert auth_headers(url, None) == {}

def test_redirect_to_other_host_drops_token():
    req = urllib.request.Request("https://github.com/a", headers=auth_headers("https://github.com/a", "tok-123"))
    new = ScopedAuthRedirectHandler("tok-123").redirect_request(req, io.BytesIO(), 302, "Found", {}, "https://evil.example/b")
    assert new.get_header("Authorization") is None and "tok-123" not in repr(new.header_items())

def test_redirect_within_allowlist_keeps_token():
    req = urllib.request.Request("https://github.com/a", headers=auth_headers("https://github.com/a", "tok-123"))
    new = ScopedAuthRedirectHandler("tok-123").redirect_request(req, io.BytesIO(), 302, "Found", {}, "https://objects.githubusercontent.com/b")
    assert new.get_header("Authorization") == "Bearer tok-123"

def test_cli_reads_token_env_and_never_prints_it(monkeypatch, served, tmp_path):
    seen = []
    served(bad_sum="threat-catalog-1.1.0.json")
    orig = rtc.fetch_asset
    monkeypatch.setattr(rtc, "fetch_asset", lambda url, **k: seen.append(k.get("token")) or orig(url, **k))
    monkeypatch.setenv("CAT_TOKEN", "tok-SECRET-999")
    r = CliRunner().invoke(main, ["refresh-threat-catalog", "--version", "1.1.0", "--out-dir", str(tmp_path), "--token-env", "CAT_TOKEN"])
    assert r.exit_code == 1 and set(seen) == {"tok-SECRET-999"}
    assert "tok-SECRET-999" not in r.output          # click's default output carries stderr too

def test_sha_mismatch_writes_nothing(served, tmp_path):
    served(bad_sum="threat-catalog-1.1.0.json")
    with pytest.raises(CatalogError, match="sha256"): refresh_threat_catalog("1.1.0", output_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []

def test_missing_sums_entry_refused(monkeypatch, tmp_path, catalog_fixture_dir): ...   # SHA256SUMS lacks the schema line → CatalogError "SHA256SUMS"
def test_version_outside_compat_refused(served, tmp_path, catalog_fixture_dir):
    served(version="2.0.0", open_bytes=_with_version(catalog_fixture_dir, "2.0.0"))
    with pytest.raises(CatalogError, match="outside catalog_compat"): refresh_threat_catalog("2.0.0", output_dir=tmp_path)

def test_hitrust_content_refused(served, tmp_path, catalog_fixture_dir):
    served(open_bytes=_with_hitrust(catalog_fixture_dir, "TC-IA-001"))
    before = sorted(tmp_path.iterdir())
    with pytest.raises(CatalogError): refresh_threat_catalog("1.1.0", output_dir=tmp_path)
    assert sorted(tmp_path.iterdir()) == before

def test_requested_version_must_match_file(served, tmp_path, catalog_fixture_dir): ...  # asset named 1.1.1, file says 1.1.0 → CatalogError "1.1.1"
def test_latest_version(monkeypatch):
    monkeypatch.setattr(rtc, "fetch_asset", lambda url, **k: b'{"tag_name": "v1.2.3"}')
    assert latest_version() == "1.2.3"

def test_cli_dry_run_prints_diff(served, tmp_path, catalog_fixture_dir):
    shutil.copy(catalog_fixture_dir / "open.json", tmp_path / "open.json"); _drop_threat(tmp_path / "open.json", "TC-MW-001")
    served(); before = (tmp_path / "open.json").read_bytes()
    r = CliRunner().invoke(main, ["refresh-threat-catalog", "--version", "1.1.0", "--dry-run", "--out-dir", str(tmp_path)])
    assert r.exit_code == 0 and "added: 1 (TC-MW-001)" in r.output and "dry run: nothing written" in r.output
    assert (tmp_path / "open.json").read_bytes() == before

def test_cli_bad_version_exit_2():
    assert CliRunner().invoke(main, ["refresh-threat-catalog", "--version", "1.0"]).exit_code == 2

def test_cli_failure_exit_1(served, tmp_path):
    served(bad_sum="threat-catalog-1.1.0.json")
    assert CliRunner().invoke(main, ["refresh-threat-catalog", "--version", "1.1.0", "--out-dir", str(tmp_path)]).exit_code == 1
```

`_with_version`, `_with_hitrust` and `_drop_threat` are JSON-rewrite helpers in the test file. In `tests/test_refresh_byte_stable.py`, `test_threat_catalog_byte_stable` serves the fixture assets through `fetch_asset`, refreshes with `fetched_at="2026-10-11"`, and asserts that `open.provenance.json` bytes equal `tests/fixtures/kb_golden/threat_catalog/open.provenance.json` and that `open.json` bytes equal the fixture.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_refresh_threat_catalog.py tests/test_refresh_byte_stable.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.refresh_threat_catalog`)

- [ ] **Step 3: Implement the module, the command and the golden file**

Generate the golden by running the refresh once in the test conditions. Its `source` is the 1.1.0 URL from Task 7's fixture provenance.

The docs refresh list gains `apd-gauntlet refresh-threat-catalog --version X.Y.Z`, with a note that it:

- verifies `SHA256SUMS`, validates, checks `compat.yaml` and supports `--dry-run`;
- downloads anonymously unless the variable named by `--token-env` (default `GITHUB_TOKEN`) is set;
- sends that token only to the three GitHub hosts.

CHANGELOG bullet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_refresh_threat_catalog.py tests/test_refresh_byte_stable.py -v && mypy tools/ && markdownlint-cli2 docs/taxonomy-mappings.md`
Expected: PASS; mypy clean; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/refresh_threat_catalog.py tools/apd_gauntlet/cli.py tests/test_refresh_threat_catalog.py tests/test_refresh_byte_stable.py tests/fixtures/kb_golden/threat_catalog docs/taxonomy-mappings.md CHANGELOG.md
git commit -m "feat(cli): add refresh-threat-catalog with checksum, validation and compat checks"
```

### Task 11: KB cache freshness reads the catalog's sidecar provenance

**Files:**

- Modify: `tools/check_kb_cache_freshness.py` (`:23-57` constants, `:86-125` `main`), `docs/ci-gate-model.md:46`
- Test: `tests/test_check_kb_cache_freshness.py` (extend)

**Interfaces:**

- Produces:
  - `SIDECAR_COVERED: dict[str, str] = {"threat-catalog/open.json": "threat-catalog/open.provenance.json"}`
  - `def check_sidecar(data: pathlib.Path, name: str, sidecar: str) -> tuple[bool, str]`:
    - both absent → `(True, "<name>: not installed")`;
    - one absent → `(False, "<name>: … missing")`;
    - provenance lacking any of `source`, `source_sha256`, `fetched_at`, `version` → `False`, naming the keys;
    - `sha256(<name> bytes) != source_sha256` → `(False, "<name>: sha256 does not match <sidecar>")`;
    - else `(True, "")`.
  - `main()` runs `check_sidecar(DATA, …)` for every entry. Its OK line becomes `check_kb_cache_freshness: OK (<n> covered, <m> exempt; threat-catalog/open.json not installed)`, or `… verified` once vendored.

- [ ] **Step 1: Write the failing tests**

```python
def _sidecar(tmp_path, *, body=b"{}", prov=None):
    d = tmp_path / "threat-catalog"; d.mkdir()
    if body is not None: (d / "open.json").write_bytes(body)
    if prov is not None: (d / "open.provenance.json").write_text(json.dumps(prov))
    return tmp_path

def test_sidecar_not_installed_passes(tmp_path):
    (tmp_path / "threat-catalog").mkdir()
    assert mod.check_sidecar(tmp_path, "threat-catalog/open.json", "threat-catalog/open.provenance.json") == (True, "threat-catalog/open.json: not installed")

def test_sidecar_missing_provenance_fails(tmp_path):
    ok, why = mod.check_sidecar(_sidecar(tmp_path), "threat-catalog/open.json", "threat-catalog/open.provenance.json")
    assert not ok and "missing" in why

def test_sidecar_hash_mismatch_fails(tmp_path):
    prov = {"source": "u", "source_sha256": "0" * 64, "fetched_at": "2026-10-11", "version": "1.0.0"}
    ok, why = mod.check_sidecar(_sidecar(tmp_path, prov=prov), "threat-catalog/open.json", "threat-catalog/open.provenance.json")
    assert not ok and "sha256" in why

def test_sidecar_ok(tmp_path):
    prov = {"source": "u", "source_sha256": hashlib.sha256(b"{}").hexdigest(), "fetched_at": "2026-10-11", "version": "1.0.0"}
    assert mod.check_sidecar(_sidecar(tmp_path, prov=prov), "threat-catalog/open.json", "threat-catalog/open.provenance.json") == (True, "")

def test_sidecar_entry_registered():
    assert mod.SIDECAR_COVERED == {"threat-catalog/open.json": "threat-catalog/open.provenance.json"}
```

The existing `test_main_passes_on_the_real_data_dir` must keep passing while the file is not installed.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_check_kb_cache_freshness.py -v`
Expected: FAIL (`check_sidecar` missing)

- [ ] **Step 3: Implement the sidecar check and update the doc line**

The doc line adds: "and `threat-catalog/open.json` matches the `source_sha256` in its `open.provenance.json` sidecar (the vendored file stays byte-identical; passes while not installed)".

- [ ] **Step 4: Run the tests and the gate**

Run: `pytest tests/test_check_kb_cache_freshness.py tests/test_ci_gate_docs.py -v && python tools/check_kb_cache_freshness.py && markdownlint-cli2 docs/ci-gate-model.md`
Expected: PASS; `check_kb_cache_freshness: OK (12 covered, 4 exempt; threat-catalog/open.json not installed)`

- [ ] **Step 5: Commit**

```bash
git add tools/check_kb_cache_freshness.py tests/test_check_kb_cache_freshness.py docs/ci-gate-model.md
git commit -m "ci: verify the vendored threat catalog against its sidecar provenance"
```

### Task 12: CI guards for the vendored catalog (KB alignment, no HITRUST content, committed examples)

**Files:**

- Create: `tools/apd_gauntlet/catalog/alignment.py`
- Modify: `docs/taxonomy-mappings.md` (new subsection "Threat catalog KB alignment (2.0)"), `docs/ci-gate-model.md`, `CHANGELOG.md`
- Test: `tests/test_catalog_ci_guards.py`

**Interfaces:**

- Consumes: `Catalog` (Task 7); `taxonomy_map`, `kb_ids`, `kb_version`, `normalize_nist` (Task 6); `load_catalog`, `validate_catalog_file`, `hitrust_errors`, `VENDORED_NOT_INSTALLED` (Tasks 8–9); `catalog_config_from_run_config`, `catalog_data_dir` (Task 1)
- Produces:
  - `def kb_alignment_errors(catalog: Catalog) -> list[str]`, sorted:
    - every mapping or control id, primary or partial, under a `taxonomy_map()` key must be in `kb_ids(taxonomy)`. NIST ids go through `normalize_nist` first. A miss gives `"<key> id <id> (<threat id>) not in <kb>"`.
    - where the framework entry (`<key>`, or `ctl_<key>` for controls) records a version and `kb_version` returns one, the two must be the exact same string (`frameworks[].version` is free-form); else `"<key>: catalog records version <a>, <kb> records <b>"`.
  - `def unversioned_frameworks(catalog: Catalog) -> list[str]` — sorted keys where either side records no version (informational)

- [ ] **Step 1: Write the failing tests**

```python
VENDORED = catalog_data_dir() / "open.json"
needs_vendored = pytest.mark.skipif(not VENDORED.exists(), reason=VENDORED_NOT_INSTALLED)

@needs_vendored
def test_vendored_open_catalog_validates():
    assert validate_catalog_file(VENDORED, edition="open", provenance=VENDORED.with_name("open.provenance.json")) == []

@needs_vendored
def test_vendored_catalog_has_no_hitrust_content():
    assert hitrust_errors(json.loads(VENDORED.read_text()), text=True) == []

def test_catalog_data_and_fixtures_have_no_hitrust_text():
    roots = (catalog_data_dir(), REPO / "tests/fixtures/threat_catalog")
    hits = [p for r in roots for p in sorted(r.rglob("*")) if p.is_file() and "hitrust" in p.read_text(errors="ignore").lower()]
    assert hits == []

@needs_vendored
def test_vendored_mapping_ids_exist_in_kbs():
    errs = kb_alignment_errors(load_catalog(CatalogConfig("open", None, (), ())))
    assert [e for e in errs if " not in " in e] == []

@needs_vendored
def test_vendored_framework_versions_match_kbs():
    errs = kb_alignment_errors(load_catalog(CatalogConfig("open", None, (), ())))
    assert [e for e in errs if "records version" in e] == []

def test_fixture_alignment_reports_only_the_absent_id(load_fixture_catalog):
    assert kb_alignment_errors(load_fixture_catalog("full")) == ["cwe id CWE-99999 (TC-IN-001) not in cwe.json"]

def test_version_mismatch_names_both_versions(load_fixture_catalog):
    cat, kv = load_fixture_catalog("open"), kb_version("atlas")
    for catalog_version in ("0.1.0", f"v{kv}"):                   # exact string compare: "v5.6.0" != "5.6.0"
        fw = {**cat.frameworks, "atlas": {**cat.frameworks.get("atlas", {"key": "atlas"}), "version": catalog_version}}
        errs = kb_alignment_errors(dataclasses.replace(cat, frameworks=fw))
        assert f"atlas: catalog records version {catalog_version}, atlas-techniques.json records {kv}" in errs

def test_equal_versions_pass(load_fixture_catalog):
    cat = load_fixture_catalog("open")
    fw = {**cat.frameworks, "atlas": {**cat.frameworks.get("atlas", {"key": "atlas"}), "version": kb_version("atlas")}}
    assert not [e for e in kb_alignment_errors(dataclasses.replace(cat, frameworks=fw)) if e.startswith("atlas:")]

def test_unversioned_frameworks_listed(load_fixture_catalog):
    assert "attack_enterprise" in unversioned_frameworks(load_fixture_catalog("open"))

def test_committed_examples_use_off_or_open():
    for cfg_path in REPO.glob("examples/*/expected/.apd-run.yaml"):
        cfg = catalog_config_from_run_config(yaml.safe_load(cfg_path.read_text()) or {})
        assert cfg is None or cfg.edition == "open", cfg_path
    for scope in REPO.glob("examples/**/00-context/threat-scope.yaml"):
        cat = (yaml.safe_load(scope.read_text()) or {}).get("catalog")
        assert cat is None or cat["edition"] == "open", scope

@needs_vendored
def test_notice_names_vendored_catalog_version():
    v = json.loads(VENDORED.with_name("open.provenance.json").read_text())["version"]
    notice = (REPO / "NOTICE").read_text()
    assert "data/threat-catalog/open.json" in notice and f"threat catalog {v}" in notice
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_ci_guards.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.catalog.alignment`); the five vendored tests SKIP

- [ ] **Step 3: Implement `alignment.py` and the docs**

The taxonomy-mappings subsection explains the CI check: ids and versions, the unversioned KBs (ATT&CK techniques, CWE, CAPEC, NIST, D3FEND and MASWE record no version, so only presence is checked for them), and the skip before vendoring. `docs/ci-gate-model.md` lists `tests/test_catalog_ci_guards.py` under the pytest gate. CHANGELOG bullet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_ci_guards.py -v && mypy tools/ && markdownlint-cli2 docs/taxonomy-mappings.md docs/ci-gate-model.md`
Expected: six PASS and five SKIP (reason `vendored catalog not installed …`); mypy clean; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/alignment.py docs/taxonomy-mappings.md docs/ci-gate-model.md CHANGELOG.md tests/test_catalog_ci_guards.py
git commit -m "test(catalog): CI guards for KB alignment, HITRUST-free content and committed examples"
```

### Task 12a: Record knowledge-base versions

(Consolidated plan task N17.)

**Files:** `tools/apd_gauntlet/refresh_mitre.py`, `refresh_capec.py`, `refresh_cwe.py`, their data files (`data/mitre-attack-*.json`, `data/capec.json`, `data/cwe.json`) on the next refresh, `tools/apd_gauntlet/catalog/alignment.py` (CAT1 Task 12); tests `tests/test_refresh_versions.py`.

**Interfaces:** `refresh-mitre` writes the collection version to `_meta.version` (and `attack_version` in the detection file); `refresh-capec` writes `_meta.version` and `_meta.count`; `refresh-cwe` writes `_meta.version` from `Weakness_Catalog@Version`. CAT1 Task 12 compares recorded versions instead of listing these KBs as unversioned.

- [ ] **Step 1:** Tests feed each refresher a minimal upstream fixture and assert the recorded version string; `test_detection_file_has_attack_version`.
- [ ] **Step 2–4:** Fail, implement, pass; QG. Commit: `feat(kb): record ATT&CK, CAPEC and CWE versions`.

### Task 13: `threat-catalog` doctor check

Depends on LA3 Task 3 as amended by master plan §A3 (`docs/superpowers/plans/2026-10-10-local-apps-plan3-setup-tui-web.md`), and on LA1 Task 1 (`UserConfig`).

**Files:**

- Create: `tools/apd_gauntlet/catalog/doctor.py`
- Modify: `tools/apd_gauntlet/cli.py` (call `register_catalog_doctor_check()` once at import, beside IAC1's `register_iac_doctor_checks()`), `CHANGELOG.md`
- Test: `tests/test_catalog_doctor.py`

**Interfaces:**

- Consumes:
  - from `apd_gauntlet.app.services`: `@dataclass class Check: name: str; status: Literal["pass", "warn", "fail"]; detail: str; fix: str | None`, `doctor(cfg, …) -> list[Check]` and `register_doctor_check(name: str, fn: Callable[[UserConfig], Check]) -> None`;
  - `apd_gauntlet.config.UserConfig` (its `workspace` field);
  - `validate_catalog_file`, `load_catalog`, `check_full_path`, `VENDORED_NOT_INSTALLED` (Tasks 8–9); `catalog_config_from_run_config`, `catalog_data_dir` (Task 1).
- Produces:
  - `def catalog_doctor_check(cfg: UserConfig, *, data_dir: Path | None = None) -> Check` (name `threat-catalog`):
    - the vendored file is absent → `warn`, detail `VENDORED_NOT_INSTALLED`, fix `apd-gauntlet refresh-threat-catalog --version <X.Y.Z>`;
    - the vendored file is invalid → `fail`, detail = the first error, fix `apd-gauntlet refresh-threat-catalog`;
    - each full path found in `cfg.workspace / "runs" / "*" / ".apd-run.yaml"` whose `threat_catalog` edition is `full` is checked with `check_full_path` and `validate_catalog_file`. Any problem → `warn` ("runs fall back to open"), with the detail naming each path and its first problem;
    - else `pass`, detail `"open <version> (sha256 <first 12 hex>); <n> full path(s) valid"`.
  - `def register_catalog_doctor_check() -> None` (idempotent)

- [ ] **Step 1: Write the failing tests**

```python
def ws(tmp_path): return UserConfig(workspace=tmp_path / "ws")

def test_registered_after_builtins(tmp_path):
    names = [c.name for c in doctor(ws(tmp_path))]
    assert "threat-catalog" in names and names.index("threat-catalog") > names.index("code-recon")

def test_warns_when_not_installed(tmp_path):
    c = catalog_doctor_check(ws(tmp_path), data_dir=tmp_path)
    assert c.status == "warn" and "not installed" in c.detail and "refresh-threat-catalog" in c.fix

def test_passes_with_valid_vendored(tmp_path, catalog_fixture_dir):
    c = catalog_doctor_check(ws(tmp_path), data_dir=catalog_fixture_dir)
    assert c.status == "pass" and "open 1.1.0" in c.detail and "0 full path(s) valid" in c.detail

def test_fails_on_invalid_vendored(tmp_path, catalog_fixture_copy):
    assert catalog_doctor_check(ws(tmp_path), data_dir=catalog_fixture_copy(corrupt_sha=True)).status == "fail"

def test_warns_on_bad_full_path(tmp_path, catalog_fixture_dir):
    cfg = ws(tmp_path); run = cfg.workspace / "runs/r1"; run.mkdir(parents=True)
    (run / ".apd-run.yaml").write_text("run_id: r1\ndomains: [pbm]\nframework_version: 2.0.0\n"
                                       "threat_catalog: {edition: full, path: /nonexistent/full.json}\n")
    c = catalog_doctor_check(cfg, data_dir=catalog_fixture_dir)
    assert c.status == "warn" and "/nonexistent/full.json" in c.detail
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_catalog_doctor.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.catalog.doctor`)

- [ ] **Step 3: Implement the check and its registration**

Unparseable run configs in the workspace are skipped. Full paths are deduplicated and checked in sorted order. CHANGELOG bullet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_catalog_doctor.py tests/app -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/doctor.py tools/apd_gauntlet/cli.py CHANGELOG.md tests/test_catalog_doctor.py
git commit -m "feat(doctor): add threat-catalog check for the vendored and configured full catalogs"
```

### Task 14: Vendor catalog release 1.1.0 (operator)

Prerequisite (master plan, operator work, as amended by register A7.24): `illusconsulting/threat-catalog` 1.1.0 is published with tag `v1.1.0`, with `threat-catalog-1.1.0.json`, `threat-catalog.schema.json` and `SHA256SUMS` on the release. If the release is not public, export a token with read access in `GITHUB_TOKEN`, or name another variable with `--token-env`.

**Files:**

- Create (by the command): `tools/apd_gauntlet/data/threat-catalog/open.json`, `open.provenance.json`; replace: `open.schema.json`
- Modify: `NOTICE` (an entry for `data/threat-catalog/open.json`), `tools/check_notice_present.py` (`REQUIRED` gains `"threat-catalog/open.json"`), `CHANGELOG.md`

- [ ] **Step 1: Preview the release**

Run: `apd-gauntlet refresh-threat-catalog --version 1.1.0 --dry-run`
Expected: exit 0; `added: 367 (…)`, a line per mapping key with its counts, and `dry run: nothing written`

- [ ] **Step 2: Vendor it**

Run: `apd-gauntlet refresh-threat-catalog --version 1.1.0`
Expected: exit 0; three `Wrote` lines; `git status` shows `open.json` and `open.provenance.json` added and `open.schema.json` unchanged

- [ ] **Step 3: Attribute it**

Add a NOTICE entry, written as `illusconsulting threat catalog 1.1.0 — <licence and URL from the release LICENSE>: data/threat-catalog/open.json, data/threat-catalog/open.schema.json`, followed by "Third-party framework ids and names in the catalog remain under their own terms; see the catalog's NOTICE at <v1.1.0 NOTICE URL>." Add nothing beyond that. Add the `REQUIRED` entry (`threat-catalog/open.json`).
Run: `python tools/check_notice_present.py && pytest tests/test_catalog_ci_guards.py::test_notice_names_vendored_catalog_version -v`
Expected: `NOTICE present for all attribution-required KBs.`; PASS

- [ ] **Step 4: Run the CI guards against the real file**

Run: `pytest tests/test_catalog_ci_guards.py tests/test_catalog_load.py -v -rs && python tools/check_kb_cache_freshness.py`
Expected:

- the five vendored guards (`test_vendored_open_catalog_validates`, `test_vendored_mapping_ids_exist_in_kbs`, `test_vendored_framework_versions_match_kbs`, `test_vendored_catalog_has_no_hitrust_content` and `test_notice_names_vendored_catalog_version`) PASS, not skipped;
- `test_packaged_open_until_vendored` skips;
- the gate prints `… threat-catalog/open.json verified`.

If an id or version check fails, follow spec §10.3. Run the matching `refresh-mitre`, `refresh-mitre-mobile`, `refresh-atlas`, `refresh-cwe`, `refresh-capec` or `refresh-mas`, then rerun this step. If upstream has moved past the version the catalog records, publish a catalog patch release built against the current upstream versions, and restart at Step 1 with it. Never commit a release that fails this step.

ATT&CK note: ATT&CK v20.0 was released 2026-10-13 and the catalog maps v19.2. Run `refresh-mitre` only if an id check fails, and record the outcome.

- [ ] **Step 5: Check a local catalog (optional)**

Copy `open.json` to a path outside any git tree, for example `~/threat-catalog/local-catalog.json`, and add one `TC-<FAMILY>-9NN` threat (raising `catalog.counts.threats` and that family's count by one, so check 5 passes). Point a scratch run config in the workspace at it with `threat_catalog: {edition: full, path: ~/threat-catalog/local-catalog.json}`.
Run: `apd-gauntlet doctor`
Expected: `threat-catalog` pass, `1 full path(s) valid`.

- [ ] **Step 6: Milestone comparison (master plan Task 6 Step 2a)**

Run the master plan Task 1 set twice with `threat_catalog: off` (names ending `-cat1-r1` and `-cat1-r2`), then `apd-gauntlet compare-runs runs/<example>-next-baseline runs/<example>-cat1 --gates eval/gates.yaml`.
Expected: exit 0 for each example

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/data/threat-catalog NOTICE tools/check_notice_present.py CHANGELOG.md
git commit -m "chore(catalog): vendor threat catalog 1.1.0"
```

## Follow-ups (not tasks in this plan)

- **KB version recording.** `refresh-cwe`, `refresh-capec` and the ATT&CK writers record no version. `mitre-attack-techniques.json` has no Enterprise writer at all. Task 12 can therefore check only id presence for those KBs and lists them as unversioned. A later change can record the upstream version, for example `Weakness_Catalog@Version` and the ATT&CK collection version, so that §10.4 compares them too.
- **Private-release downloads** (applies only if the catalog repository stays private). GitHub can refuse `releases/download/…` URLs for a private repository even with a token, and serve them only through the API asset endpoint. If Task 14 Step 1 gets a 404 with a token set, switch `fetch_asset` to the asset endpoint. The token-scoping rules stay the same.
- **ATT&CK v20.** ATT&CK v20.0 (2026-10-13) is newer than the catalog's v19.2, and `mitre-attack-techniques.json` (fetched 2026-05-29) records no version. Record the collection version in `_meta.version`, then build catalog 1.2.0 against v20.
