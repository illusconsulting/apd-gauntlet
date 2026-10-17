# CAT4 — Threat Catalog Evaluation and the Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure `threat_catalog: open` against `off` with the WS2 harness (threat labels, four evaluators, six proposal gates, a frozen held-out measurement) and make `open` the 2.0 default only if every held-out gate passes; otherwise record that `off` stays.

**Architecture:** WS2's `eval-labels` gains a `threats` kind. A `catalog.evaluation` package finds each corpus entry's runs by name (`<prefix>-off-rN`, `<prefix>-open-rN`, optional `<prefix>-full-rN`), so each of the four evaluators registered with WS2's `register` scores both configurations in one `EvalResult`, pooling counts over the runs. `apd-gauntlet catalog gates` runs the four evaluators through WS2's `run_eval`, which keeps the held-out freeze guard. It adds the token ratio from WS2's `usage` files and the existing comparison gates from WS2's `compare_sides`, then evaluates a new `catalog_gates` section of `eval/gates.yaml`. On held-out data it writes an aggregate-only decision record, and a committed test ties that record to `DEFAULT_EDITION`, the CHANGELOG and the spec's status line.

**Tech Stack:** Python 3.10–3.12, click, PyYAML, jsonschema (Draft 2020-12); WS2 `apd_gauntlet.measure` and `apd_gauntlet.eval`; CAT1–CAT3 `apd_gauntlet.catalog`; pytest with `click.testing.CliRunner`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md` §14 (except the metamorphic suite, which CAT2 owns), §3 ("Default" row), §7 (absent key), §9 (`eval-labels` row), §11, §12.3, §15 (CAT4 row and operator work); master plan `docs/superpowers/plans/2026-10-10-program-master-plan.md` R1, R2, R7 (`eval-labels` gains kind `threats`), R8, R9, R10, Task 8 Step 3a, M6; WS2 plan `docs/superpowers/plans/2026-10-10-ws2-measurement-and-evaluation.md` Tasks 5, 6, 8–11 and 14, and its ADR-0028; IAC4 plan `docs/superpowers/plans/2026-10-10-iac-plan4-evaluation.md` (precedent for a labels kind, evaluators, freeze and runbook); the CAT brief's fixed cross-plan interfaces.

**Amended 2026-10-17** per the amendments register (A7.50, A15.12, A15.21, A15.27).

## Global Constraints

- Ships on `next` (2.0 line); CHANGELOG entries go under ``## Unreleased — 2.0 line (`next`)``.
- "Measured with the WS2 harness, on the master plan Task 1 set plus labelled development and held-out corpora (ADR-0017: local only; labels and results never committed)." (spec §14) Because `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started, every run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or starts a new session (register A15.12).
- Labels, corpus manifests and results for this plan live under the gitignored `eval/local/catalog/` and `eval/results/`, including labels for the committed examples (the spec is stricter than ADR-0028's labels clause, and the spec wins).
- The only committed evaluation artefact is `eval/catalog/decision.yaml`: aggregate gate values, entry and run counts, and SHA-256 digests. It never holds entry ids, run names, threat ids or labels. This is ADR-0028's narrow exception ("aggregate calibration statistics carry no subject data"), which Task 10 amends to name the file.
- "Each corpus system is run twice with `off` and twice with `open`, plus `full` locally." (spec §14). Runs are named `<prefix>-off-r1`, `<prefix>-off-r2`, `<prefix>-open-r1`, `<prefix>-open-r2`, and optionally `<prefix>-full-r1`, so WS2's `resolve_side` and `compare-runs` find them.
- Every measured run sets `threat_catalog` explicitly in `.apd-run.yaml`, because an absent key follows `DEFAULT_EDITION`.
- Evaluators: `catalog-tm-recall`, `catalog-mapping-precision` (lens `control_mappings` and derived `catalog_mappings` scored apart), `catalog-silence-precision`, `catalog-grounding`, "registered through `apd_gauntlet.eval.evaluators.register`".
- Proposed gates, verbatim from spec §14: "TM coverage recall with `open` not below `off`"; "lens mapping precision with `open` not below `off`"; "derived mapping precision at least 0.9"; "silence precision at least 0.8"; "tokens per run with `open` at most 1.05 × `off`"; "the existing gates all pass".
- Tuning: "`top_n`, `max_per_family`, `shortlist_cap`, `silence_cap`, the family exclusions and `system-types.yaml` are tuned on the development set only. They are then frozen (`selection.yaml` `version` bumped) and measured once on held-out. A held-out failure means `off` stays the default for 2.0."
- Selection defaults (CAT brief): `version: 1`, `top_n: 3`, `max_per_family: 2`, `shortlist_cap: 40`, `silence_cap: 15`, `exclude_families: [EN, FA, CF, PH, LG]`, `summary_chars_shortlist: 160`, `summary_chars_candidate: 400`.
- Default (spec §3): "`threat_catalog: open` on 2.0 only if the §14 gates pass; otherwise `off`." `DEFAULT_EDITION: Literal["off", "open"] = "off"` lives in `tools/apd_gauntlet/catalog/config.py`, and the workflow mirrors it as `const CATALOG_DEFAULT_EDITION = 'off';` in `.claude/workflows/apd-gauntlet.js` (CAT2 Task 9 pins the two equal in `tests/test_workflow_apd_gauntlet.py::test_catalog_default_edition_mirrors_python`). `plan_run` and `runner/flow.py` read the Python value through `catalog_config_from_run_config`, so they hold no copy. Only Task 12 changes the two values, together.
- One shared freeze (coordinator, 2026-10-12): CAT4's development tuning finishes before the M6 `eval freeze`, alongside IAC4's tuning and the `calibrate` runs; every held-out run of every workstream comes after that freeze.
- Unmeasured gates (coordinator, 2026-10-12): with zero `catalog_silence` findings, the silence gate reads `not_available` with the reason "no silence findings produced" and counts as passing. Any other `not_available` gate means `off`.
- Tokens per run are the sum of the four `usage.yaml` token counters (input, output, cache read, cache creation). `cost_usd` is reported alongside, never gated.
- Labelling every off-run TM entry on labelled surfaces is accepted (coordinator, 2026-10-12). The later WS6 decision task `threat-match` (spec §16) could pre-fill those rows.
- CAT4 reads no catalog prose, and no CAT4 output carries any.
- **CI never touches the network** (ADR-0017). Tests use synthetic run directories only.
- Quality gates: `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest` (coverage `fail_under = 85`), and `markdownlint-cli2` on the linted globs all pass on every PR.
- Every schema change `$ref`s `_defs.schema.json#/$defs/<name>` for goal and severity (`tests/test_schema_vocab_centralized.py`).

## Review Focus

- **A run filed under the wrong configuration.** Examples: an `-open-r1` directory whose `.apd-run.yaml` resolves to `off`, an open run whose scope reports `catalog: null` (vendored catalog not installed), or a `full` run that fell back to `open`. Each is refused with the run named, and the evaluators and `catalog gates` exit 2 rather than score `off` as `open`. Pinned in Task 2 (`test_config_mismatch_refused`, `test_open_run_without_catalog_refused`, `test_full_fallback_refused`).
- **Off-run TM entries the labeller did not map.** Unmapped entries would lower `off` recall and bias the gate toward `open`, so `catalog-tm-recall` refuses and names the run and the count. Pinned in Task 4 (`test_unmapped_off_entries_refused`).
- **Asset names that drift between runs.** A name declared as an alias resolves to its surface. A silence finding on an unknown name counts as unjudged, which lowers precision; it is never dropped. Pinned in Task 1 (`test_threat_labels_parse`) and Task 6 (`test_unknown_surface_counts_against_precision`).
- **A held-out gate computed on stale runs.** Held-out exits 2 when an open run used a `selection_version` other than the one on disk, when the selection was never bumped (version 1), when tunables changed after `eval freeze`, or when a configuration has fewer than two runs. Pinned in Task 9 (`test_stale_selection_version_heldout_exits_2`, `test_heldout_requires_bumped_selection`, `test_heldout_refused_after_selection_edit`, `test_heldout_requires_two_runs_per_config`).
- **A gate that could not be measured, or a second decision.** A run without `.apd-state/usage.yaml`, or existing gates at `pass_with_gaps`, makes the gate `not_available`, and the record then says `off`, never `open`. The one accepted gap is a silence gate with zero silence findings. An existing record is never overwritten. Pinned in Task 9 (`test_zero_silence_findings_accepted`) and Task 10 (`test_unmeasured_gate_records_off`, `test_zero_silence_findings_record_open`, `test_existing_record_not_overwritten`).

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/data/schemas/eval-labels.schema.json` | `kind: threats` branch | Modify (WS2) |
| `tools/apd_gauntlet/eval/corpus.py` | `Labels.kind` gains `"threats"` | Modify (WS2) |
| `tools/apd_gauntlet/catalog/evaluation/__init__.py` | Package marker | Create |
| `tools/apd_gauntlet/catalog/evaluation/labels.py` | `ThreatLabels`, `threat_labels`, `surface_key` | Create |
| `tools/apd_gauntlet/catalog/evaluation/runs.py` | Run-set resolution and the run readers | Create |
| `tools/apd_gauntlet/catalog/evaluation/template.py` | `threats` label template and merge | Create |
| `tools/apd_gauntlet/catalog/evaluation/recall.py` | `catalog-tm-recall` | Create |
| `tools/apd_gauntlet/catalog/evaluation/mapping.py` | `catalog-mapping-precision` | Create |
| `tools/apd_gauntlet/catalog/evaluation/silence.py` | `catalog-silence-precision` | Create |
| `tools/apd_gauntlet/catalog/evaluation/grounding.py` | `catalog-grounding` | Create |
| `tools/apd_gauntlet/catalog/evaluation/evaluators.py` | Imports the four evaluator modules (registration) | Create |
| `tools/apd_gauntlet/catalog/evaluation/gates.py` | Catalog gate values, token ratio, existing gates, report | Create |
| `tools/apd_gauntlet/catalog/evaluation/decision.py` | Decision record and the default consistency check | Create |
| `tools/apd_gauntlet/eval/evaluators.py` | `load_builtin_evaluators` imports the catalog evaluators | Modify (WS2) |
| `tools/apd_gauntlet/eval/freeze.py` | `TUNABLE_GLOBS` gains the two catalog tunables | Modify (WS2) |
| `tools/apd_gauntlet/measure/gates.py` | `load_gates(path, *, section, metrics)` | Modify (WS2) |
| `eval/gates.yaml` | `catalog_gates` section (six proposals) | Modify (WS2) |
| `tools/apd_gauntlet/cli.py` | `eval label-template --kind/--sample/--merge`; `catalog gates` | Modify |
| `tools/apd_gauntlet/catalog/config.py`, `.claude/workflows/apd-gauntlet.js` | `DEFAULT_EDITION` and its mirror `CATALOG_DEFAULT_EDITION` (Task 12, open branch only) | Modify (CAT1, CAT2) |
| `tools/apd_gauntlet/data/threat-catalog/selection.yaml`, `system-types.yaml` | Tuned values (Task 11, operator) | Modify (CAT1) |
| `eval/frozen.yaml` | Re-frozen tunables (Task 11, operator) | Modify (WS2) |
| `eval/catalog/decision.yaml` | Aggregate held-out decision record (Task 12) | Create |
| `docs/measuring-changes.md` | Section "Threat catalog default" | Modify (WS2) |
| `docs/adrs/0028-committed-calibration-and-frozen-evaluation.md` | Amendment naming the decision record | Modify (WS2) |
| `docs/schema-evolution.md`, `CHANGELOG.md`, `RELEASING.md`, the spec's status line | Records | Modify |
| `tests/catalog_eval/__init__.py`, `tests/catalog_eval/runs.py` | Synthetic labels, runs and scenarios | Create |
| `tests/catalog_eval/test_labels.py`, `test_runs.py`, `test_template.py`, `test_recall.py`, `test_mapping.py`, `test_silence.py`, `test_grounding.py`, `test_gates_file.py`, `test_catalog_gates.py`, `test_decision.py` | Tests | Create |
| `tests/test_measuring_changes_doc.py`, `tests/test_adr_0028.py` | Doc tests | Modify (WS2) |

---

### Task 1: `eval-labels` kind `threats` and its loader

**Files:**

- Modify: `tools/apd_gauntlet/data/schemas/eval-labels.schema.json` (new `kind: threats` branch in the `allOf` of `if`/`then` blocks), `tools/apd_gauntlet/eval/corpus.py` (`Labels.kind` Literal gains `"threats"`), `docs/schema-evolution.md`, `CHANGELOG.md`
- Create: `tools/apd_gauntlet/catalog/evaluation/__init__.py`, `tools/apd_gauntlet/catalog/evaluation/labels.py`, `tests/catalog_eval/__init__.py`, `tests/catalog_eval/runs.py` (labels half)
- Test: `tests/catalog_eval/test_labels.py`

**Interfaces:**

- Consumes:
  - WS2: `load_labels(path) -> Labels`, `Labels(kind, path, sha256, data)`, `CorpusError`.
  - CAT1: `Catalog` with `threats: Mapping[str, Threat]`; `_defs.schema.json#/$defs/catalog_threat_id` (CAT1 Task 7, pattern `^TC-[A-Z]{2}-\d{3}$`); the pytest fixture `load_fixture_catalog` (a `Callable[[Literal["open", "full"]], Catalog]`, CAT1 Task 9).
- Produces (schema, `kind: threats`; `additionalProperties: false` throughout):
  - Top level: `{schema_version: 1, kind: threats, entry: str, catalog_version: ^\d+\.\d+\.\d+$, surfaces, threats, tm_equivalents?, findings?}`.
  - `surfaces`: `[{name: str (minLength 1), aliases?: [str] (uniqueItems)}]`, minItems 1.
  - `threats`: `[{id: $ref catalog_threat_id, verdict: applicable|not_applicable|unreviewed, surfaces?: [str] (uniqueItems), note?}]`. `verdict: applicable` requires `surfaces` with minItems 1.
  - `tm_equivalents`: `[{run: str, entry_id: ^tm-[0-9a-f]{8}$, asset?: str, threat?: str, reviewed: bool, threats: [$ref catalog_threat_id] (uniqueItems)}]`.
  - `findings`: `[{id?: str, verdict: reviewed|excluded|unreviewed, apd_goal: $ref apd_goal, title: str, evidence: [{artifact, locator, excerpt?}] (minItems 1), expected: {mitre_attack: [$ref attack_technique_id], cwe: [$ref cwe_id], nist_800_53r5: [^[A-Z]{2}-[0-9]+(\([0-9]+\))?$]} (all three required), note?}]`.
- Produces (`labels.py`):
  - `TAXONOMIES: tuple[str, ...] = ("mitre_attack", "cwe", "nist_800_53r5")`
  - `def surface_key(name: str) -> str` — NFKC, `casefold()`, `re.sub(r"[^0-9a-z]+", "-", s).strip("-")`
  - `@dataclass(frozen=True) class FindingLabel: key: str; record: dict[str, Any]; expected: Mapping[str, frozenset[str]]`. `key` is the item's `id`, else `label-<index>`. `record` holds `id`, `apd_goal`, `title` and `evidence` in the shape WS2's `match_records` reads.
  - `@dataclass(frozen=True) class ThreatLabels`, with fields:
    - `entry: str`, `catalog_version: str`
    - `surface_names: Mapping[str, str]`: `surface_key` of each name and alias, mapped to the canonical name
    - `applicable: frozenset[tuple[str, str]]`: (threat id, canonical surface)
    - `labelled_surfaces: Mapping[str, frozenset[str]]`: canonical surfaces of each applicable threat
    - `not_applicable: frozenset[str]`
    - `tm_equivalents: Mapping[str, Mapping[str, frozenset[str]]]`: run directory name, then TM entry id, then the threat ids it maps to
    - `findings: tuple[FindingLabel, ...]`: `reviewed` items only; `excluded` items are dropped
  - `ThreatLabels` methods:
    - `resolve_surface(name: str) -> str | None`
    - `judge(threat_id: str, surface: str) -> Literal["applicable", "not_applicable", "unjudged"]`. A threat labelled `not_applicable` is `not_applicable` on any surface. An applicable threat on a known surface outside its labelled surfaces is `not_applicable`. An unknown surface, or an unlabelled threat, is `unjudged`.
  - `def threat_labels(labels: Labels, *, catalog: Catalog | None = None) -> ThreatLabels`. It raises `ValueError` for: a kind other than `threats`; any `unreviewed` threat, row or finding (message gives the count and the section); a threat surface not declared under `surfaces`; two names or aliases sharing a `surface_key`; a duplicate threat id; and, when `catalog` is given, a threat or row id absent from it.

Test-data module `tests/catalog_eval/runs.py` starts with `CATALOG_VERSION = "0.0.1"` (never a vendored version), `def write_labels(path: Path, data: Mapping[str, Any]) -> Path` and `SYS_LABELS`, a dict equal to this YAML, which every later task uses (tests `deepcopy` it before editing):

```yaml
schema_version: 1
kind: threats
entry: sys
catalog_version: "0.0.1"
surfaces: [{name: claims-api, aliases: [adjudication-svc]}, {name: claims-db}, {name: member}]
threats:
  - {id: TC-AC-001, verdict: applicable, surfaces: [claims-api, member]}
  - {id: TC-IN-002, verdict: applicable, surfaces: [claims-db]}
  - {id: TC-DP-003, verdict: applicable, surfaces: [claims-api]}
  - {id: TC-AI-004, verdict: not_applicable}
tm_equivalents:
  - {run: sys-off-r1, entry_id: tm-00000001, reviewed: true, threats: [TC-AC-001]}
  - {run: sys-off-r1, entry_id: tm-00000002, reviewed: true, threats: [TC-AC-001]}
  - {run: sys-off-r1, entry_id: tm-00000003, reviewed: true, threats: []}
  - {run: sys-off-r2, entry_id: tm-00000004, reviewed: true, threats: [TC-DP-003, TC-AC-001]}
  - {run: sys-off-r2, entry_id: tm-00000005, reviewed: true, threats: [TC-IN-002]}
findings:
  - {id: conf-aaaa0001, verdict: reviewed, apd_goal: confidentiality, title: Claims API accepts unsigned member tokens,
     evidence: [{artifact: inputs/api/auth.md, locator: "#tokens"}],
     expected: {mitre_attack: [T1078], cwe: [CWE-287], nist_800_53r5: [IA-2, AC-3]}}
  - {id: intg-aaaa0002, verdict: reviewed, apd_goal: integrity, title: Claims database rows editable without audit trail,
     evidence: [{artifact: inputs/db/schema.md, locator: "#claims"}],
     expected: {mitre_attack: [T1565.001], cwe: [], nist_800_53r5: [AU-9]}}
```

- [ ] **Step 1: Write the failing tests**

```python
def labels_from(tmp_path, data):
    return load_labels(write_labels(tmp_path / "l.yaml", data))

def test_surface_key():
    assert surface_key("  Claims API ") == surface_key("claims_api") == "claims-api"

def test_threat_labels_parse(tmp_path):
    tl = threat_labels(labels_from(tmp_path, SYS_LABELS))
    assert tl.applicable == {("TC-AC-001", "claims-api"), ("TC-AC-001", "member"),
                             ("TC-IN-002", "claims-db"), ("TC-DP-003", "claims-api")}
    assert tl.resolve_surface("Adjudication_Svc") == "claims-api" and tl.resolve_surface("billing-svc") is None
    assert tl.judge("TC-AI-004", "anything") == "not_applicable"
    assert tl.judge("TC-IN-002", "claims-api") == "not_applicable"
    assert tl.judge("TC-DP-003", "adjudication-svc") == "applicable"
    assert tl.judge("TC-ZZ-999", "claims-db") == tl.judge("TC-AC-001", "billing-svc") == "unjudged"
    assert tl.tm_equivalents["sys-off-r2"]["tm-00000004"] == {"TC-DP-003", "TC-AC-001"}
    assert [f.key for f in tl.findings] == ["conf-aaaa0001", "intg-aaaa0002"]
    assert tl.findings[1].expected == {"mitre_attack": {"T1565.001"}, "cwe": frozenset(), "nist_800_53r5": {"AU-9"}}

def test_unreviewed_refused(tmp_path):
    data = deepcopy(SYS_LABELS); data["threats"][0]["verdict"] = "unreviewed"
    with pytest.raises(ValueError, match="1 unreviewed threat"):
        threat_labels(labels_from(tmp_path, data))

def test_unreviewed_tm_row_refused(tmp_path): ...       # one row reviewed: false → ValueError "1 unreviewed tm_equivalents"
def test_excluded_finding_dropped(tmp_path): ...        # findings[1].verdict excluded → [f.key for f in tl.findings] == ["conf-aaaa0001"]

def test_applicable_needs_surfaces(tmp_path):
    data = deepcopy(SYS_LABELS); del data["threats"][1]["surfaces"]
    with pytest.raises(CorpusError, match="surfaces"):
        labels_from(tmp_path, data)

def test_undeclared_surface_refused(tmp_path): ...      # threats[1].surfaces = ["billing"] → ValueError "undeclared surface 'billing'"
def test_surface_key_collision_refused(tmp_path): ...   # add {name: x, aliases: [Claims API]} → ValueError naming "claims-api"
def test_duplicate_threat_refused(tmp_path): ...        # TC-AC-001 twice → ValueError "duplicate"

def test_unknown_id_refused_against_catalog(tmp_path, load_fixture_catalog):
    data = deepcopy(SYS_LABELS); data["threats"].append({"id": "TC-ZZ-999", "verdict": "not_applicable"})
    with pytest.raises(ValueError, match="TC-ZZ-999"):
        threat_labels(labels_from(tmp_path, data), catalog=load_fixture_catalog("open"))

def test_findings_kind_rejected(tmp_path): ...          # a WS2 findings-kind file → ValueError "threats"
```

`ZZ` is not a catalog family, so `TC-ZZ-999` cannot be in the fixture catalog.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_labels.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.catalog.evaluation`)

- [ ] **Step 3: Implement the schema branch, the `Labels.kind` value and `threat_labels`**

The `applicable` rule is an inner `allOf: [{if: {properties: {verdict: {const: applicable}}, required: [verdict]}, then: {required: [surfaces], properties: {surfaces: {minItems: 1}}}}]` on the threat item. Add a dated `### YYYY-MM-DD — eval-labels gains kind threats` entry (commit date) under WS2's `## v2.0.0 — Measurement and evaluation (additive)` section of `docs/schema-evolution.md`. Add a CHANGELOG `### Added` bullet: "`eval-labels` kind `threats` (applicable catalog threats with surfaces, off-run TM mappings, expected mappings for sampled findings)".

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_labels.py tests/test_eval_corpus.py tests/test_meta_schemas.py tests/test_schema_vocab_centralized.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas tools/apd_gauntlet/eval/corpus.py tools/apd_gauntlet/catalog/evaluation tests/catalog_eval docs/schema-evolution.md CHANGELOG.md
git commit -m "feat(eval): add the threats labels kind for the threat catalog evaluation"
```

### Task 2: Run sets, run readers and the synthetic fixture

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/runs.py`
- Modify: `tests/catalog_eval/runs.py` (run builders, `SYS_RUNS`, `sys_entry`)
- Test: `tests/catalog_eval/test_runs.py`

**Interfaces:**

- Consumes:
  - WS2: `resolve_side(path: Path) -> list[Path]`, `MissingRuns`, `CorpusEntry`, `Labels`, `load_labels`, `write_usage`, `write_attempts`.
  - CAT1: `catalog_config_from_run_config(run_cfg: Mapping[str, Any]) -> CatalogConfig | None`.
  - CAT2: `candidates.load_scope(run_dir: Path) -> dict[str, Any] | None` (`None` when the file is absent or `catalog` is `null`; `ScopeError` on a `threat-scope` schema error) and the `threat-scope` document keys (CAT2 Task 4).
  - Task 1: `ThreatLabels`.
- Produces (`runs.py`):
  - `CONFIGS: tuple[str, ...] = ("off", "open", "full")`
  - `@dataclass(frozen=True) class RunSets: entry_id: str; prefix: Path; runs: Mapping[str, tuple[Path, ...]]; catalog: Mapping[str, Any]; selection_version: int; notes: tuple[str, ...]`. `runs` always holds non-empty `off` and `open`, and `full` only when present. `catalog` and `selection_version` are the open runs' common scope values.
  - `def run_config_name(run: Path) -> Literal["off", "open", "full"]`: from `.apd-run.yaml` through `catalog_config_from_run_config` (`None` means `off`).
  - `def run_sets(prefix: Path, *, entry_id: str) -> RunSets`: `resolve_side(Path(f"{prefix}-{config}"))` per configuration. It raises `ValueError` naming the entry and run when:
    - `off` or `open` has no run (the message names `<prefix>-off-r1`);
    - a directory's configuration differs from its `.apd-run.yaml`;
    - an open or full run's `load_scope` returns `None` (`"<run>: no catalog in 00-context/threat-scope.yaml (absent, or vendored catalog not installed)"`) or raises `ScopeError` (message copied);
    - a full run's scope has `fallback_from: full` ("fell back to open");
    - open or full runs disagree on `catalog.version` or `selection_version`.

    A configuration with one run adds the note `"entry <id>: 1 <config> run; run each configuration twice"` (`full` is exempt).
  - `def tm_entries(run: Path) -> list[dict[str, Any]]`: the `entries` of `00-context/threat-model-normalized.yaml` (`[]` when absent).
  - `def skeleton_entries(run: Path) -> list[dict[str, Any]]`: the `entries` of `00-context/threat-model-skeleton.yaml` (`[]` when absent).
  - `def check_labels_version(labels: ThreatLabels, sets: RunSets) -> None`: `ValueError` naming both versions when `labels.catalog_version != sets.catalog["version"]`.
- Produces (`tests/catalog_eval/runs.py`):
  - `@dataclass class RunSpec: tm: list[dict[str, Any]]; findings: list[dict[str, Any]] = []; silence: list[tuple[str, str]] = []; skeleton: list[dict[str, Any]] | None = None; tokens: int | None = None` (list fields use `field(default_factory=list)`).
  - Entry builders:
    - `def tm(asset, letter, *, methodology="stride", refs=None, gap=None, blocked=False, entry_id=None) -> dict`: `framework_refs.stride_letter`, or `linddun_letter` for `linddun` (no letter slot for `maestro`); `catalog_refs` when `refs` is not `None`; `catalog_gap_reason` when `gap`; `prerequisite_evidence: ["design doc"]` when `blocked`.
    - `def finding(fid, goal, title, artifact, locator, *, severity, lens, derived=None) -> dict`: a schema-shaped lens finding with `disposition: gap`. `lens` is a `control_mappings` dict; `derived` becomes `catalog_mappings` `{tax: [{id, via: ["TC-AC-001"]}]}`.
    - `def cell(asset, letter, candidates, *, methodology="stride") -> dict`: a skeleton entry with `catalog_candidates: [{id, rank_reason: "fixture"}]`.
  - Run-directory writers:
    - `def write_run(root, name, config, spec, *, selection_version=2) -> Path`. It writes `.apd-run.yaml` as `{run_id: name, domains: [pbm], threat_catalog: …}` with the key set explicitly (`full` as `{edition: full, path: <root>/full.json}`, which it also creates). For `open` and `full` it writes a scope that validates against CAT2's `threat-scope` schema, built from the run's skeleton cells and TM entries:
      - `{schema_version: 1, generated_by: apd-gauntlet, catalog: {edition, version: CATALOG_VERSION, sha256: "a" * 64, fallback_from: null}, selection_version, emphasize_families: [], maestro_active: false, system_types: [], surfaces, threats, warnings: []}`;
      - `surfaces`: one per asset, `{asset, element, system_types, type_fallback: false, stride, linddun, crown_jewel: false}`. `claims-db` is a `data_store` (system type `data_store`), `member` an `external_entity` (`identity`), and every other asset a `process` (`api`);
      - `threats`: one per candidate or cited id, `{id, surfaces, reasons: ["system_type:<type>"], goals: ["confidentiality"]}`.

      It also writes:
      - TM entries to `00-context/threat-model-normalized.yaml`;
      - lens findings to `10-trustworthiness/lens.findings.yaml`;
      - silence findings to `40-threat-model/threat-model.findings.yaml` (`tmeval-…` ids, `disposition: uncertainty`, `severity: low`, `tmeval_key: {flavor: catalog_silence, threat_id, surface}`);
      - usage `totals.input_tokens = tokens`, with the other three token counters 0, and `totals.cost_usd = tokens / 1000`;
      - a clean WS2 attempts file (`recorded_by: operator`, `audit_iterations: 1`).
    - `def write_run_set(root, system, runs: Mapping[str, Sequence[RunSpec]], *, selection_version=2) -> Path`: returns the prefix `root/system`.
  - Fixture data:
    - `def sys_runs(*, passing: bool = False) -> dict[str, list[RunSpec]]`: fresh copies of the fixture below.
    - `SYS_RUNS = sys_runs()`.
  - Corpus helpers:
    - `def sys_entry(tmp_path, *, passing=False, runs=None, labels=None, set_name="dev") -> tuple[CorpusEntry, Labels]`: runs under `tmp_path/runs`, labels at `tmp_path/labels/sys.yaml`.
    - `def scenario(tmp_path, *, passing=False, set_name="dev", selection_version=2, open_runs=2, silence=True) -> tuple[Path, Path]`: returns `(root, manifest)`; `silence=False` empties every open run's silence list. `root` holds:
      - `eval/gates.yaml`, copied from the repository;
      - `tools/apd_gauntlet/data/threat-catalog/selection.yaml` (the packaged file with `version` set) and `system-types.yaml` (copied);
      - `tools/apd_gauntlet/data/decide/thresholds.yaml` (`{}`);
      - the runs under `root/runs`;
      - labels at `eval/local/catalog/labels/sys.yaml`;
      - the manifest `eval/local/catalog/corpus.yaml` with entry `{id: sys, set: <set_name>, run: ../../../runs/sys, labels: labels/sys.yaml}`.

The fixture (`F1` is `finding("conf-…", "confidentiality", "Claims API accepts unsigned member tokens", "inputs/api/auth.md", "#tokens", severity="high", …)`; `F2` is `finding("intg-…", "integrity", "Claims database rows editable without audit trail", "inputs/db/schema.md", "#claims", severity="medium", …)`; finding ids are unique per run):

| Run | TM entries | Lens / derived mappings | Silence (threat, surface) | Skeleton cells | Tokens |
|---|---|---|---|---|---|
| `sys-off-r1` | `tm-00000001` claims-api S; `tm-00000002` member S; `tm-00000003` claims-db T | F1 lens `nist [IA-2, SC-8]`, ATT&CK `T1078`/`T1078.004`, `cwe [CWE-287]`; F2 lens `nist [AU-9(2)]`, ATT&CK `T1565`, `cwe [CWE-284]` | — | — | 1000 |
| `sys-off-r2` | `tm-00000004` claims-api S; `tm-00000005` claims-db I | F1 lens `nist [IA-2]`, `cwe [CWE-287]` | — | — | 1200 |
| `sys-open-r1` | claims-api S refs `[TC-AC-001, TC-DP-003]`; claims-api T blocked; claims-db I refs `[TC-IN-002]`; claims-db D gap; member linddun I refs `[TC-DP-007]` | F1 lens `nist [IA-2, AC-3]`, ATT&CK `T1078`, `cwe [CWE-287]`, derived `mitre_attack [T1078]`, `cwe [CWE-287]`, `nist [AC-3, SC-7]`; F2 lens `nist [AU-9]`, ATT&CK `T1565`/`T1565.001`, derived `nist [AU-9]`, `cwe [CWE-284]` | (TC-AC-001, member), (TC-IN-002, claims-api), (TC-AI-004, claims-db), (TC-ZZ-999, claims-db) | claims-api S `[TC-AC-001, TC-AC-005]`; claims-api T `[TC-DP-003]`; claims-db I `[TC-IN-002, TC-IN-006]`; claims-db D `[TC-AV-009]`; member linddun I `[TC-DP-007]`; member S `[]` | 1100 |
| `sys-open-r2` | adjudication-svc S refs `[TC-AC-001]`; member S gap | F1 lens `nist [IA-2, CM-6]`, derived `nist [IA-2]` | (TC-DP-003, adjudication-svc), (TC-AC-001, billing-svc) | adjudication-svc S `[TC-AC-001]`; member S `[TC-AC-001, TC-AC-005]` | 1210 |

`sys_runs(passing=True)` makes four changes:

- `sys-open-r2` gains the TM entry claims-db I refs `[TC-IN-002]`.
- `sys-open-r2`'s member S entry becomes refs `[TC-AC-001]` (no gap).
- `sys-open-r1` drops derived `SC-7` and `CWE-284`.
- Silence keeps only (TC-AC-001, member) and (TC-DP-003, adjudication-svc).

- [ ] **Step 1: Write the failing tests**

```python
def test_run_sets_resolve(tmp_path):
    s = run_sets(write_run_set(tmp_path, "sys", sys_runs()), entry_id="sys")
    assert [p.name for p in s.runs["off"]] == ["sys-off-r1", "sys-off-r2"] and "full" not in s.runs
    assert (s.catalog["version"], s.selection_version, s.notes) == ("0.0.1", 2, ())

def test_missing_open_runs_refused(tmp_path):
    prefix = write_run_set(tmp_path, "sys", {"off": sys_runs()["off"]})
    with pytest.raises(ValueError, match="sys-open-r1"):
        run_sets(prefix, entry_id="sys")

def test_config_mismatch_refused(tmp_path):
    prefix = write_run_set(tmp_path, "sys", sys_runs())
    (tmp_path / "sys-open-r1/.apd-run.yaml").write_text("run_id: sys-open-r1\nthreat_catalog: off\n")
    with pytest.raises(ValueError, match=r"sys-open-r1.*off"):
        run_sets(prefix, entry_id="sys")

def test_open_run_without_catalog_refused(tmp_path):
    prefix = write_run_set(tmp_path, "sys", sys_runs())
    p = tmp_path / "sys-open-r2/00-context/threat-scope.yaml"
    doc = yaml.safe_load(p.read_text()); doc["catalog"] = None; p.write_text(yaml.safe_dump(doc))
    with pytest.raises(ValueError, match="vendored catalog not installed"):
        run_sets(prefix, entry_id="sys")

def test_full_fallback_refused(tmp_path): ...          # full run scope catalog {edition: open, fallback_from: full} → "fell back"
def test_mixed_selection_versions_refused(tmp_path): ...  # sys-open-r2 scope selection_version 3 → "selection_version"

def test_single_run_noted(tmp_path):
    runs = sys_runs(); runs["off"] = runs["off"][:1]
    assert run_sets(write_run_set(tmp_path, "sys", runs), entry_id="sys").notes == (
        "entry sys: 1 off run; run each configuration twice",)

def test_labels_version_checked(tmp_path):
    entry, labels = sys_entry(tmp_path, labels={**SYS_LABELS, "catalog_version": "0.0.2"})
    with pytest.raises(ValueError, match=r"0\.0\.2.*0\.0\.1"):
        check_labels_version(threat_labels(labels), run_sets(entry.run_dir, entry_id="sys"))

def test_readers(tmp_path):
    prefix = write_run_set(tmp_path, "sys", sys_runs())
    assert [e["entry_id"] for e in tm_entries(tmp_path / "sys-off-r2")] == ["tm-00000004", "tm-00000005"]
    assert len(skeleton_entries(tmp_path / "sys-open-r1")) == 6 and skeleton_entries(tmp_path / "sys-off-r1") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_runs.py -v`
Expected: FAIL (`ImportError: cannot import name 'run_sets'`)

- [ ] **Step 3: Implement `runs.py` and the fixture builders**

`run_sets` catches `MissingRuns` per configuration and maps a missing `off` or `open` side to the `ValueError` above. It reads scopes only through CAT2's `load_scope`, so a malformed scope fails here rather than being scored.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_runs.py tests/catalog_eval/test_labels.py -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation/runs.py tests/catalog_eval
git commit -m "feat(eval): resolve off/open/full run sets for the threat catalog evaluation"
```

### Task 3: `threats` label template

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/template.py`
- Modify: `tools/apd_gauntlet/cli.py` (WS2's `eval label-template` gains `--kind`, `--sample`, `--merge`), `docs/measuring-changes.md` (new section "Threat catalog default" with subsection "Label catalog threats"), `CHANGELOG.md`, `tests/test_measuring_changes_doc.py`
- Test: `tests/catalog_eval/test_template.py`

**Interfaces:**

- Consumes: `run_sets`, `tm_entries`, `CONFIGS` (Task 2); `surface_key` (Task 1); WS2 `load_run`, `match_records`, `label_template` (findings kind), `load_labels`; CAT2 `load_scope`
- Produces:
  - `SAMPLE_DEFAULT = 20`
  - `def label_template_threats(prefix: Path, entry_id: str, *, sample: int = SAMPLE_DEFAULT) -> dict[str, Any]`, with these sections:
    - `catalog_version`: from the run sets.
    - `surfaces`: the open runs' scope surfaces plus every TM entry asset in every run, de-duplicated by `surface_key` and sorted by key, as `{name}`.
    - `threats`: the union of every open run's scope `threats`, sorted by id, as `{id, verdict: unreviewed, surfaces: <sorted union of scope surfaces>}`.
    - `tm_equivalents`: one row per TM entry of every off run, in (run, entry id) order, as `{run: <dir name>, entry_id, asset, threat, reviewed: false, threats: []}`.
    - `findings`: off-r1's findings plus open-r1's findings that `match_records` does not match to off-r1. Ids starting `tmeval-` or `apath-` are excluded. The sample is the first `sample` by `sha256(f"{entry_id}:{id}")`, as `{id, verdict: unreviewed, apd_goal, title, evidence: [{artifact, locator}], expected: {mitre_attack: [], cwe: [], nist_800_53r5: []}}`.

    No run's `control_mappings`, `catalog_mappings` or `catalog_refs` appear, so labels are not anchored on either configuration's answers.
  - `def merge_threat_template(existing: Mapping[str, Any], fresh: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, int]]`: appends threats with unseen ids, rows with an unseen (run, entry id), and surfaces whose `surface_key` matches no name or alias. Existing items are never edited, and `findings` are never merged. Returns the added counts `{"surfaces", "threats", "tm_equivalents"}`.
  - CLI: `eval label-template RUN_DIR --entry ID --out FILE [--kind findings|threats] [--sample N] [--merge]`. `--kind` defaults to `findings` (WS2's behaviour, unchanged). For `threats`, `RUN_DIR` is the run-set prefix. Exits:
    - 1 when `FILE` exists without `--merge`;
    - 2 for `--merge` or `--sample` with `--kind findings`, `--merge` on a missing `FILE`, or a `ValueError` from the run sets;
    - 0 otherwise, printing `added <n> threats, <n> tm_equivalents, <n> surfaces` on merge.

- [ ] **Step 1: Write the failing tests**

```python
def test_template_sections(tmp_path):
    t = label_template_threats(write_run_set(tmp_path, "sys", sys_runs()), "sys")
    assert (t["kind"], t["entry"], t["catalog_version"]) == ("threats", "sys", "0.0.1")
    assert [s["name"] for s in t["surfaces"]] == ["adjudication-svc", "claims-api", "claims-db", "member"]
    assert [x["id"] for x in t["threats"]] == ["TC-AC-001", "TC-AC-005", "TC-AV-009", "TC-DP-003",
                                               "TC-DP-007", "TC-IN-002", "TC-IN-006"]
    assert t["threats"][0] == {"id": "TC-AC-001", "verdict": "unreviewed",
                               "surfaces": ["adjudication-svc", "claims-api", "member"]}
    assert [(r["run"], r["entry_id"]) for r in t["tm_equivalents"]] == [
        ("sys-off-r1", "tm-00000001"), ("sys-off-r1", "tm-00000002"), ("sys-off-r1", "tm-00000003"),
        ("sys-off-r2", "tm-00000004"), ("sys-off-r2", "tm-00000005")]
    assert len(t["findings"]) == 2
    text = yaml.safe_dump(t)
    assert "control_mappings" not in text and "catalog_mappings" not in text and "catalog_refs" not in text

def test_template_loads_but_is_unreviewed(tmp_path):
    p = write_labels(tmp_path / "l.yaml", label_template_threats(write_run_set(tmp_path, "sys", sys_runs()), "sys"))
    with pytest.raises(ValueError, match="7 unreviewed threats"):
        threat_labels(load_labels(p))

def test_sample_is_deterministic(tmp_path):
    prefix = write_run_set(tmp_path, "sys", sys_runs())
    a, b = (label_template_threats(prefix, "sys", sample=1)["findings"] for _ in range(2))
    assert len(a) == 1 and a == b

def test_merge_keeps_reviewed_items(tmp_path):
    merged, added = merge_threat_template(SYS_LABELS, label_template_threats(write_run_set(tmp_path, "sys", sys_runs()), "sys"))
    assert added == {"surfaces": 0, "threats": 4, "tm_equivalents": 0}
    assert merged["threats"][:4] == SYS_LABELS["threats"] and merged["findings"] == SYS_LABELS["findings"]

def test_cli_threats_template_and_merge(tmp_path):
    prefix = write_run_set(tmp_path, "sys", sys_runs()); out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(prefix), "--kind", "threats", "--entry", "sys", "--out", str(out)]
    assert CliRunner().invoke(main, args).exit_code == 0 and load_labels(out).kind == "threats"
    assert CliRunner().invoke(main, args).exit_code == 1
    r = CliRunner().invoke(main, [*args, "--merge"])
    assert r.exit_code == 0 and "added 0 threats" in r.output

def test_merge_with_findings_kind_exits_2(tmp_path): ...    # --kind findings --merge → 2
def test_template_without_open_runs_exits_2(tmp_path): ...  # only off runs → 2, output names sys-open-r1

# tests/test_measuring_changes_doc.py
def test_runbook_covers_catalog_labels():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("Threat catalog default", "eval/local/catalog/", "--kind threats", "-off-r1", "-open-r2",
              "tm_equivalents", "--merge", "aliases", "not_applicable", "threat-match"):
        assert s in t
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_template.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (`ModuleNotFoundError` for `template`; `no such option: --kind`)

- [ ] **Step 3: Implement the template, merge, CLI options and the runbook subsection**

Add a "Threat catalog default" section to `docs/measuring-changes.md` with a "Label catalog threats" subsection covering:

- **Corpus layout.** `eval/local/catalog/corpus.yaml` uses WS2's manifest shape; each entry's `run` is the run-set prefix `runs/<system>`, and labels go in `eval/local/catalog/labels/<id>.yaml`. Everything stays local (spec §14).
- **Run naming and keys.** Runs are named `-off-r1`, `-off-r2`, `-open-r1`, `-open-r2` and optionally `-full-r1`, each with an explicit `threat_catalog`.
- **The template.** `apd-gauntlet eval label-template runs/<system> --kind threats --entry <id> --out …`.
- **Review rules:**
  - mark every threat `applicable` (with surfaces) or `not_applicable`;
  - add catalog threats the scope missed;
  - list other names of a surface under `aliases`;
  - map every off-run TM entry (`tm_equivalents`, `reviewed: true`, `threats: []` when none applies). This is the spec's "judged equivalent for `off` runs by the labeller's mapping"; the later WS6 decision task `threat-match` (spec §16) could propose these rows, but until it exists they are labelled by hand;
  - fill `expected` ATT&CK, CWE and 800-53 ids from the KBs without opening the run's findings;
  - use `excluded` for a sampled finding that is itself wrong.
- **`--merge`.** Run it after a selection change or a new off run.

CHANGELOG `### Added` bullet: "`eval label-template --kind threats` (with `--sample` and `--merge`)".

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_template.py tests/test_eval_findings.py tests/test_measuring_changes_doc.py -v && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS (WS2's findings-kind tests unchanged); 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation/template.py tools/apd_gauntlet/cli.py docs/measuring-changes.md CHANGELOG.md tests/catalog_eval/test_template.py tests/test_measuring_changes_doc.py
git commit -m "feat(eval): add the threats label template with sampling and merge"
```

### Task 4: Evaluator `catalog-tm-recall`

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/recall.py`, `tools/apd_gauntlet/catalog/evaluation/evaluators.py`
- Modify: `tools/apd_gauntlet/eval/evaluators.py` (`load_builtin_evaluators` also imports `apd_gauntlet.catalog.evaluation.evaluators`), `CHANGELOG.md`
- Test: `tests/catalog_eval/test_recall.py`

**Interfaces:**

- Consumes: `threat_labels` (Task 1); `run_sets`, `tm_entries`, `check_labels_version` (Task 2); WS2 `register`, `get`, `EvalResult`, `load_builtin_evaluators`
- Produces:
  - `def evaluate_tm_recall(entry: CorpusEntry, labels: Labels) -> EvalResult`, registered as `catalog-tm-recall`, with `derive=recall_metrics`
  - `def recall_metrics(counts: Mapping[str, int]) -> dict[str, float | None]`, with these metrics:
    - `recall.<cfg>` = `<cfg>.covered / <cfg>.applicable` for `off`, `open` and `full` (`None` on a zero denominator);
    - `recall_delta` = `recall.open − recall.off` (`None` if either is `None`).
  - Counts per configuration present, with every run contributing:
    - `<cfg>.runs`;
    - `<cfg>.applicable`: `len(labels.applicable)` per run;
    - `<cfg>.covered`: labelled pairs the run covers;
    - `<cfg>.tm_unknown_surface`: TM entries whose asset does not resolve.
  - Coverage rules:
    - An open or full TM entry covers `(t, resolve_surface(entry.asset))` for each `t` in its `catalog_refs`.
    - An off entry covers the same pairs for each threat its `tm_equivalents` row maps.
    - A pair counts once per run.
  - `evaluate_tm_recall` raises `ValueError` when an off run has TM entries without a row: `"<n> TM entries of <run> have no tm_equivalents row; run 'eval label-template … --merge' and map them"`. Rows naming a run outside the set become a note.
  - Shared preamble for all four catalog evaluators (Tasks 4–7): `ValueError` when `entry.run_dir` is `None` (`"catalog corpus entries need run: <prefix>"`); then `threat_labels(labels)`, `run_sets(entry.run_dir, entry_id=entry.id)` and `check_labels_version`; `RunSets.notes` are copied into `EvalResult.notes`.

- [ ] **Step 1: Write the failing tests**

```python
def test_recall_counts_and_delta(tmp_path):
    r = evaluate_tm_recall(*sys_entry(tmp_path))
    assert r.counts == {"off.runs": 2, "off.applicable": 8, "off.covered": 5, "off.tm_unknown_surface": 0,
                        "open.runs": 2, "open.applicable": 8, "open.covered": 4, "open.tm_unknown_surface": 0}
    assert r.metrics == {"recall.off": 0.625, "recall.open": 0.5, "recall.full": None, "recall_delta": -0.125}

def test_passing_variant(tmp_path):
    m = evaluate_tm_recall(*sys_entry(tmp_path, passing=True)).metrics
    assert (m["recall.open"], m["recall_delta"]) == (0.75, 0.125)

def test_unmapped_off_entries_refused(tmp_path):
    labels = deepcopy(SYS_LABELS)
    labels["tm_equivalents"] = [r for r in labels["tm_equivalents"] if r["entry_id"] != "tm-00000005"]
    with pytest.raises(ValueError, match=r"1 TM entries of sys-off-r2"):
        evaluate_tm_recall(*sys_entry(tmp_path, labels=labels))

def test_full_runs_reported(tmp_path):
    runs = sys_runs(); runs["full"] = [runs["open"][0]]
    r = evaluate_tm_recall(*sys_entry(tmp_path, runs=runs))
    assert (r.counts["full.covered"], r.metrics["recall.full"]) == (3, 0.75)

def test_unknown_surface_entry_counted(tmp_path):
    runs = sys_runs(); runs["open"][1].tm.append(tm("billing-svc", "S", refs=["TC-AC-001"]))
    r = evaluate_tm_recall(*sys_entry(tmp_path, runs=runs))
    assert (r.counts["open.tm_unknown_surface"], r.counts["open.covered"]) == (1, 4)

def test_registered_with_derive(tmp_path):
    load_builtin_evaluators()
    assert get("catalog-tm-recall") is evaluate_tm_recall
    assert recall_metrics({"off.applicable": 4, "off.covered": 2, "open.applicable": 4, "open.covered": 3})["recall_delta"] == 0.25
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_recall.py -v`
Expected: FAIL (`ModuleNotFoundError: …recall`)

- [ ] **Step 3: Implement `recall.py`, the registration module and the WS2 import**

`evaluators.py` imports `recall` (Tasks 5–7 add their modules). `recall.py` calls `register` at import; Python's module cache makes a second `load_builtin_evaluators()` a no-op. CHANGELOG `### Added` bullet: "Threat catalog evaluators for `eval run`: `catalog-tm-recall`" (Tasks 5–7 extend the list).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_recall.py tests/test_eval_evaluators.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation tools/apd_gauntlet/eval/evaluators.py CHANGELOG.md tests/catalog_eval/test_recall.py
git commit -m "feat(eval): add catalog-tm-recall over off and open run sets"
```

### Task 5: Evaluator `catalog-mapping-precision`

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/mapping.py`
- Modify: `tools/apd_gauntlet/catalog/evaluation/evaluators.py`, `CHANGELOG.md`
- Test: `tests/catalog_eval/test_mapping.py`

**Interfaces:**

- Consumes: `threat_labels`, `TAXONOMIES`, `FindingLabel` (Task 1); `run_sets`, `check_labels_version` (Task 2); WS2 `load_run`, `match_records`, `register`, `EvalResult`; CAT1 `translate.normalize_nist(control_id: str) -> str`
- Produces:
  - `def parent_id(taxonomy: str, item: str) -> str | None`: `T1565.001` gives `T1565`, `AU-9(2)` gives `AU-9`, and anything else gives `None`.
  - `def ids_agree(taxonomy: str, predicted: str, expected: frozenset[str]) -> bool`: true when the predicted id is expected, its parent is expected, or it is the parent of an expected id. NIST ids are compared after `normalize_nist`; CWE ids exactly.
  - `def lens_ids(finding: Mapping[str, Any], taxonomy: str) -> frozenset[str]`: from `control_mappings`. ATT&CK uses `sub_technique` when it is set, else `technique`.
  - `def derived_ids(finding: Mapping[str, Any], taxonomy: str) -> frozenset[str]`: `{m["id"] for m in catalog_mappings[taxonomy]}`, using CAT3 Task 2's shape `{<taxonomy>: [{id, via: [TC-…]}]}`.
  - `def evaluate_mapping_precision(entry: CorpusEntry, labels: Labels) -> EvalResult`, registered as `catalog-mapping-precision`, with `derive=mapping_metrics`.
    - Scoring: per run, `match_records({f.key: f.record for f in labels.findings}, run.findings, candidate_targets=run.graph_targets)`. For each matched finding and taxonomy, each lens or derived id adds to `tp` when it agrees with an expected id, else to `fp`.
    - Counts: `<cfg>.lens.tp.<tax>`, `<cfg>.lens.fp.<tax>`, `<cfg>.derived.tp.<tax>`, `<cfg>.derived.fp.<tax>`, `<cfg>.findings_matched` and `<cfg>.findings_unmatched`, for every configuration present and every taxonomy.
    - `ValueError` when the labels hold no `reviewed` finding.
  - `def mapping_metrics(counts: Mapping[str, int]) -> dict[str, float | None]` returns, for `off`, `open` and `full`:
    - `lens_precision.<cfg>` and `derived_precision.<cfg>`, pooled over the three taxonomies;
    - `lens_precision.<cfg>.<tax>` and `derived_precision.<cfg>.<tax>`;
    - `lens_precision_delta` = open − off.

    Each is `None` on a zero denominator.

- [ ] **Step 1: Write the failing tests**

```python
def test_mapping_precision(tmp_path):
    r = evaluate_mapping_precision(*sys_entry(tmp_path)); c, m = r.counts, r.metrics
    assert (c["off.lens.tp.nist_800_53r5"], c["off.lens.fp.nist_800_53r5"]) == (3, 1)
    assert (c["off.lens.tp.cwe"], c["off.lens.fp.cwe"], c["off.lens.tp.mitre_attack"]) == (2, 1, 2)
    assert (c["open.derived.tp.nist_800_53r5"], c["open.derived.fp.nist_800_53r5"]) == (3, 1)
    assert (c["off.findings_matched"], c["off.findings_unmatched"], c["open.findings_matched"]) == (3, 1, 3)
    assert m["lens_precision.off"] == pytest.approx(7 / 9) and m["lens_precision.open"] == 0.875
    assert m["lens_precision_delta"] == pytest.approx(7 / 72)
    assert m["derived_precision.open"] == pytest.approx(5 / 7) and m["derived_precision.off"] is None

def test_passing_variant_derived(tmp_path):
    assert evaluate_mapping_precision(*sys_entry(tmp_path, passing=True)).metrics["derived_precision.open"] == 1.0

@pytest.mark.parametrize("tax,pred,expected,ok", [
    ("mitre_attack", "T1078.004", {"T1078"}, True), ("mitre_attack", "T1565", {"T1565.001"}, True),
    ("mitre_attack", "T1078.004", {"T1078.001"}, False), ("nist_800_53r5", "AU-9(2)", {"AU-9"}, True),
    ("nist_800_53r5", "AC-2", {"AC-3"}, False), ("cwe", "CWE-284", {"CWE-287"}, False)])
def test_ids_agree(tax, pred, expected, ok):
    assert ids_agree(tax, pred, frozenset(expected)) is ok

def test_excluded_finding_not_scored(tmp_path):
    labels = deepcopy(SYS_LABELS); labels["findings"][1]["verdict"] = "excluded"
    c = evaluate_mapping_precision(*sys_entry(tmp_path, labels=labels)).counts
    assert (c["off.findings_matched"], c["off.findings_unmatched"]) == (2, 0)

def test_no_reviewed_findings_refused(tmp_path): ...   # findings: [] → ValueError "no reviewed findings"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_mapping.py -v`
Expected: FAIL (`ModuleNotFoundError: …mapping`)

- [ ] **Step 3: Implement `mapping.py`; import it in `evaluators.py`; extend the CHANGELOG bullet**

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_mapping.py tests/catalog_eval/test_recall.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation CHANGELOG.md tests/catalog_eval/test_mapping.py
git commit -m "feat(eval): add catalog-mapping-precision scoring lens and derived mappings apart"
```

### Task 6: Evaluator `catalog-silence-precision`

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/silence.py`
- Modify: `tools/apd_gauntlet/catalog/evaluation/evaluators.py`, `CHANGELOG.md`
- Test: `tests/catalog_eval/test_silence.py`

**Interfaces:**

- Consumes: `ThreatLabels.judge` (Task 1); `run_sets`, `check_labels_version` (Task 2); WS2 `load_run`, `register`, `EvalResult`; CAT3 Task 7 records in `40-threat-model/threat-model.findings.yaml` with `tmeval_key: {flavor: catalog_silence, threat_id, surface}`
- Produces:
  - `def evaluate_silence_precision(entry: CorpusEntry, labels: Labels) -> EvalResult`, registered as `catalog-silence-precision`, with `derive=silence_metrics`. Every finding in an open or full run with `tmeval_key.flavor == "catalog_silence"` is judged with `labels.judge(threat_id, surface)`. Counts are `<cfg>.findings`, `<cfg>.applicable`, `<cfg>.not_applicable` and `<cfg>.unjudged`. Off runs are not read.
  - `def silence_metrics(counts: Mapping[str, int]) -> dict[str, float | None]` returns, for `open` and `full`:
    - `silence_precision.<cfg>` = applicable ÷ findings ("Share of `catalog_silence` findings the labels mark applicable", spec §14; unjudged findings are not marked applicable);
    - `silence_precision_judged.<cfg>` = applicable ÷ (applicable + not_applicable), for diagnosis.

    `None` on a zero denominator. With zero silence findings, Task 9 reports the gate `not_available` with the reason "no silence findings produced" and counts it as passing (coordinator, 2026-10-12).

- [ ] **Step 1: Write the failing tests**

```python
def test_silence_precision(tmp_path):
    r = evaluate_silence_precision(*sys_entry(tmp_path))
    assert r.counts == {"open.findings": 6, "open.applicable": 2, "open.not_applicable": 2, "open.unjudged": 2}
    assert r.metrics["silence_precision.open"] == pytest.approx(1 / 3)
    assert r.metrics["silence_precision_judged.open"] == 0.5 and r.metrics["silence_precision.full"] is None

def test_passing_variant(tmp_path):
    assert evaluate_silence_precision(*sys_entry(tmp_path, passing=True)).metrics["silence_precision.open"] == 1.0

def test_unknown_surface_counts_against_precision(tmp_path):
    runs = sys_runs()
    for spec in runs["open"]:
        spec.silence = [("TC-AC-001", "billing-svc")]
    r = evaluate_silence_precision(*sys_entry(tmp_path, runs=runs))
    assert r.counts["open.unjudged"] == 2 and r.metrics["silence_precision.open"] == 0.0
    assert r.metrics["silence_precision_judged.open"] is None

def test_other_tmeval_flavors_ignored(tmp_path): ...   # add a flavor "silence" finding → counts unchanged
def test_no_silence_findings_is_none(tmp_path): ...    # every open run silence=[] → counts open.findings 0; silence_precision.open is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_silence.py -v`
Expected: FAIL (`ModuleNotFoundError: …silence`)

- [ ] **Step 3: Implement `silence.py`; import it in `evaluators.py`; extend the CHANGELOG bullet**

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_silence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation CHANGELOG.md tests/catalog_eval/test_silence.py
git commit -m "feat(eval): add catalog-silence-precision"
```

### Task 7: Evaluator `catalog-grounding`

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/grounding.py`
- Modify: `tools/apd_gauntlet/catalog/evaluation/evaluators.py`, `CHANGELOG.md`
- Test: `tests/catalog_eval/test_grounding.py`

**Interfaces:**

- Consumes: `run_sets`, `tm_entries`, `skeleton_entries`, `check_labels_version` (Task 2); `threat_labels` (Task 1, for the kind check); WS2 `register`, `EvalResult`; CAT2 Task 6 skeleton: every STRIDE entry carries `catalog_candidates: [{id, rank_reason}]` (possibly `[]`), LINDDUN cells have `framework_refs: {linddun_letter}`, and MAESTRO cells have `framework_refs: {}` with the layer only in the stub threat text; TM fields `catalog_refs`, `catalog_gap_reason`, `prerequisite_evidence` (blocked when non-empty, per `threat-model-normalized.schema.json`)
- Produces:
  - `def cell_key(entry: Mapping[str, Any]) -> tuple[str, str, str | None]`: `(asset, methodology, stride_letter or linddun_letter or None)`. MAESTRO entries have no letter slot, so MAESTRO cells join per asset.
  - `def evaluate_grounding(entry: CorpusEntry, labels: Labels) -> EvalResult`, registered as `catalog-grounding`, with `derive=grounding_metrics`. The evaluation is descriptive and feeds no gate; it is the tuning signal for `top_n` and `max_per_family`. Rules for each skeleton entry with at least one candidate (a cell) in an open or full run, where E is the TM entries sharing its `cell_key`:
    - candidates cited in any E's `catalog_refs` are grounded, and the cell is grounded;
    - otherwise, if any E is blocked, every candidate is blocked;
    - remaining candidates are unconfirmed.
  - Counts per configuration:
    - `<cfg>.cells`, `<cfg>.cells_grounded`, `<cfg>.cells_blocked`;
    - `<cfg>.candidates`, `<cfg>.candidates_grounded`, `<cfg>.candidates_blocked`, `<cfg>.candidates_unconfirmed`;
    - `<cfg>.entries`, and `<cfg>.off_catalog_entries` (entries with `catalog_gap_reason`).
  - `def grounding_metrics(counts: Mapping[str, int]) -> dict[str, float | None]`: `grounded_rate`, `blocked_rate` and `unconfirmed_rate` (over candidates), `cells_grounded_rate` (over cells) and `off_catalog_rate` (over entries), each as `<metric>.<cfg>`.

- [ ] **Step 1: Write the failing tests**

```python
def test_grounding_counts(tmp_path):
    r = evaluate_grounding(*sys_entry(tmp_path))
    assert r.counts == {"open.cells": 7, "open.cells_grounded": 4, "open.cells_blocked": 1, "open.candidates": 10,
                        "open.candidates_grounded": 4, "open.candidates_blocked": 1,
                        "open.candidates_unconfirmed": 5, "open.entries": 7, "open.off_catalog_entries": 2}
    m = r.metrics
    assert (m["grounded_rate.open"], m["blocked_rate.open"], m["unconfirmed_rate.open"]) == (0.4, 0.1, 0.5)
    assert m["cells_grounded_rate.open"] == pytest.approx(4 / 7) and m["off_catalog_rate.open"] == pytest.approx(2 / 7)

def test_maestro_cells_join_by_asset(tmp_path):
    runs = sys_runs()
    runs["open"][0].skeleton.append(cell("agent-runtime", None, ["TC-AG-008"], methodology="maestro"))
    runs["open"][0].tm.append(tm("agent-runtime", None, methodology="maestro", refs=["TC-AG-008"]))
    assert evaluate_grounding(*sys_entry(tmp_path, runs=runs)).counts["open.candidates_grounded"] == 5

def test_cell_key():
    assert cell_key({"asset": "a", "methodology": "linddun", "framework_refs": {"linddun_letter": "I"}}) == ("a", "linddun", "I")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_grounding.py -v`
Expected: FAIL (`ModuleNotFoundError: …grounding`)

- [ ] **Step 3: Implement `grounding.py`; import it in `evaluators.py`; extend the CHANGELOG bullet**

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation CHANGELOG.md tests/catalog_eval/test_grounding.py
git commit -m "feat(eval): add catalog-grounding (grounded, blocked and unconfirmed candidates per cell)"
```

### Task 8: The six catalog gates in `eval/gates.yaml`

**Files:**

- Modify: `eval/gates.yaml` (append the `catalog_gates` section), `tools/apd_gauntlet/measure/gates.py` (`load_gates` gains `section` and `metrics`; `CATALOG_METRICS`)
- Test: `tests/catalog_eval/test_gates_file.py`

**Interfaces:**

- Consumes: WS2 `load_gates`, `METRICS`, `Gate`, `Check`, `GatesError`, the `compare-runs` command
- Produces:
  - `CATALOG_METRICS = frozenset({"tm_recall_delta", "lens_precision_delta", "derived_precision_open", "silence_precision_open", "tokens_ratio_open_off", "existing_gates_failed_entries"})`
  - `def load_gates(path: Path, *, section: str = "gates", metrics: frozenset[str] = METRICS) -> tuple[Gate, ...]`: reads only `section`. A missing section raises `GatesError` naming it. Other top-level keys are ignored, so `compare-runs` never sees the catalog gates.

Appended to `eval/gates.yaml`:

```yaml
# Threat catalog default gates: proposals from the threat catalog spec (2026-10-11) §14.
# Evaluated by `apd-gauntlet catalog gates`, never by compare-runs.
catalog_gates:
  - id: catalog_tm_recall
    text: "TM coverage recall with `open` not below `off`"
    checks: [{metric: tm_recall_delta, op: ge, value: 0}]
  - id: catalog_lens_precision
    text: "lens mapping precision with `open` not below `off`"
    checks: [{metric: lens_precision_delta, op: ge, value: 0}]
  - id: catalog_derived_precision
    text: "derived mapping precision at least 0.9"
    checks: [{metric: derived_precision_open, op: ge, value: 0.9}]
  - id: catalog_silence_precision
    text: "silence precision at least 0.8"
    checks: [{metric: silence_precision_open, op: ge, value: 0.8}]
  - id: catalog_tokens
    text: "tokens per run with `open` at most 1.05 × `off`"
    checks: [{metric: tokens_ratio_open_off, op: le, value: 1.05}]
  - id: catalog_existing_gates
    text: "the existing gates all pass"
    checks: [{metric: existing_gates_failed_entries, op: le, value: 0}]
```

- [ ] **Step 1: Write the failing tests**

```python
SPEC = REPO / "docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md"

def test_catalog_gate_texts_match_spec_verbatim():
    block = SPEC.read_text().split("**Proposed gates**, added to `eval/gates.yaml` as proposals:")[1].split("**Tuning.**")[0]
    bullets = [b.strip().rstrip(";.") for b in re.findall(r"^- (.+)$", block, re.MULTILINE)]
    gates = load_gates(REPO / "eval/gates.yaml", section="catalog_gates", metrics=CATALOG_METRICS)
    assert [g.text for g in gates] == bullets and len(bullets) == 6

def test_catalog_gate_checks():
    gates = load_gates(REPO / "eval/gates.yaml", section="catalog_gates", metrics=CATALOG_METRICS)
    assert [(g.id, c.metric, c.op, c.value) for g in gates for c in g.checks] == [
        ("catalog_tm_recall", "tm_recall_delta", "ge", 0), ("catalog_lens_precision", "lens_precision_delta", "ge", 0),
        ("catalog_derived_precision", "derived_precision_open", "ge", 0.9),
        ("catalog_silence_precision", "silence_precision_open", "ge", 0.8),
        ("catalog_tokens", "tokens_ratio_open_off", "le", 1.05),
        ("catalog_existing_gates", "existing_gates_failed_entries", "le", 0)]

def test_default_section_unchanged():
    assert [g.id for g in load_gates(REPO / "eval/gates.yaml")] == [
        "no_lost_critical_high", "severity_agreement", "blocked_rate", "first_pass_and_retries", "audit_iterations"]

def test_catalog_metric_rejected_in_default_section(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("schema_version: 1\ngates: [{id: x, text: x, checks: [{metric: tm_recall_delta, op: ge, value: 0}]}]\n")
    with pytest.raises(GatesError, match="tm_recall_delta"):
        load_gates(p)

def test_missing_section(tmp_path): ...   # file without catalog_gates → GatesError "catalog_gates"

def test_compare_runs_ignores_catalog_section(make_run):
    r = CliRunner().invoke(main, ["compare-runs", str(make_run("b")), str(make_run("c")),
                                  "--gates", str(REPO / "eval/gates.yaml"), "--json"])
    assert r.exit_code == 0 and len(json.loads(r.stdout)["gates"]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_gates_file.py -v`
Expected: FAIL (`load_gates() got an unexpected keyword argument 'section'`)

- [ ] **Step 3: Extend `load_gates`, add `CATALOG_METRICS`, append the section**

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval/test_gates_file.py tests/test_measure_gates.py tests/test_cli_compare_runs.py -v`
Expected: PASS (WS2's verbatim master-plan gate test still passes)

- [ ] **Step 5: Commit**

```bash
git add eval/gates.yaml tools/apd_gauntlet/measure/gates.py tests/catalog_eval/test_gates_file.py
git commit -m "feat(measure): add the six threat catalog proposal gates as a separate gates section"
```

### Task 9: `catalog gates` and the catalog tunables

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/gates.py`
- Modify:
  - `tools/apd_gauntlet/eval/freeze.py`: `TUNABLE_GLOBS` gains `"tools/apd_gauntlet/data/threat-catalog/selection.yaml"` and `"tools/apd_gauntlet/data/threat-catalog/system-types.yaml"`.
  - `tools/apd_gauntlet/cli.py`: `gates` subcommand on the `catalog` click group CAT2 adds.
  - `docs/measuring-changes.md`: subsection "Tune, freeze and gate".
  - `CHANGELOG.md`, `tests/test_measuring_changes_doc.py`.
- Test: `tests/catalog_eval/test_catalog_gates.py`

**Interfaces:**

- Consumes:
  - Tasks 1–8: `run_sets`, `RunSets`, `threat_labels`, `check_labels_version`, the four evaluator names, `load_gates(section=…)`, `CATALOG_METRICS`.
  - WS2: `run_eval(manifest, set_name, evaluator, *, root, results_dir, now=None) -> Path`, `load_corpus_manifest`, `CorpusError`, `FreezeError`, `check_frozen`, `load_run`, `RunSnapshot.usage_totals`, `RunSnapshot.findings`, `RunSnapshot.inputs_sha256`, `compare_sides`, `evaluate`, `overall`, `GateOutcome`, `GatesError`.
  - CAT1: `load_selection_params(path) -> SelectionParams`, `load_catalog`, `CatalogConfig`.
- Produces:
  - Constants:
    - `CATALOG_EVALUATORS = ("catalog-tm-recall", "catalog-mapping-precision", "catalog-silence-precision", "catalog-grounding")`
    - `RESULT_METRICS: Mapping[str, tuple[str, str]] = {"tm_recall_delta": ("catalog-tm-recall", "recall_delta"), "lens_precision_delta": ("catalog-mapping-precision", "lens_precision_delta"), "derived_precision_open": ("catalog-mapping-precision", "derived_precision.open"), "silence_precision_open": ("catalog-silence-precision", "silence_precision.open")}`
    - `SELECTION_RELPATH = Path("tools/apd_gauntlet/data/threat-catalog/selection.yaml")`
    - `SILENCE_NONE_REASON = "no silence findings produced"`
    - `ACCEPTED_GAPS: Mapping[str, str] = {"catalog_silence_precision": SILENCE_NONE_REASON}`: the only `not_available` outcome that counts as passing (gate id to required reason).
  - `class CatalogGateError(Exception)`
  - Pure helpers:
    - `def run_tokens(totals: Mapping[str, float]) -> int`: `input_tokens + output_tokens + cache_read_tokens + cache_creation_tokens`.
    - `def tokens_ratio(sets: Sequence[RunSets]) -> tuple[float | None, str | None, dict[str, float]]`: Σ over entries of the mean open-run tokens ÷ Σ of the mean off-run tokens, plus a reason (`"no .apd-state/usage.yaml in <run>; run 'apd-gauntlet usage'"`) and the per-entry ratios.
    - `def cost_summary(sets: Sequence[RunSets]) -> dict[str, float | None]`: `cost_usd_off` and `cost_usd_open` (Σ over entries of the mean `totals.cost_usd` per configuration) and `cost_ratio_open_off`; all `None` when any run lacks `usage.yaml`. Reported only; no gate reads it.
    - `def catalog_overall(outcomes: Sequence[GateOutcome]) -> Literal["pass", "pass_with_gaps", "fail"]`: WS2's `overall`, except that a `not_available` outcome whose gate id and reason match `ACCEPTED_GAPS` counts as `pass`.
    - `def existing_gates(sets: Sequence[RunSets], gates_path: Path) -> tuple[float | None, str | None, dict[str, str]]`: per entry, WS2 `compare_sides(off snapshots, open snapshots)` evaluated against `load_gates(gates_path)`, then `overall`. The value is the count of `fail` entries when any fail; else `None` when any entry is `pass_with_gaps` (the reason lists them); else 0. The dict maps entry to status. An off run with zero findings, or off and open runs with different non-`None` `inputs_sha256`, raises `CatalogGateError`.
  - `@dataclass(frozen=True) class CatalogGateReport: set_name: Literal["dev", "heldout"]; outcomes: tuple[GateOutcome, ...]; status: Literal["pass", "pass_with_gaps", "fail"]; values: dict[str, float | None]; informational: dict[str, float | None]; results: dict[str, Path]; provenance: dict[str, Any]; per_entry: dict[str, dict[str, Any]]; notes: tuple[str, ...]`. `informational` is `cost_summary(sets)`; `status` is `catalog_overall(outcomes)`. `provenance` keys: `catalog`, `selection_version`, `frozen_sha256`, `corpus_sha256`, `n_entries`, `runs` (configuration to total run count).
  - `def catalog_gate_report(manifest: Path, set_name: Literal["dev", "heldout"], *, root: Path, results_dir: Path, gates_path: Path, now: datetime | None = None) -> CatalogGateReport`. Everything is validated before the first results file is written:
    1. Run sets for every entry in the set.
    2. Labels through `threat_labels` and `check_labels_version`.
    3. Every entry's open runs share one `catalog` block and one `selection_version`, which must equal `load_selection_params(root / SELECTION_RELPATH).version`. A mismatch is a `CatalogGateError` with `"selection version"` in the message on held-out, and a note with the same words on dev.
    4. Held-out only:
       - the version is at least 2 (`"bump selection.yaml version when you freeze"`);
       - every entry has at least two off runs and two open runs (`"spec §14: run each corpus system twice with off and twice with open"`);
       - `check_frozen(root)` succeeds (its `FreezeError` exits 2 before any evaluator runs).
    5. Label ids are checked with `threat_labels(…, catalog=…)` against the vendored catalog when `load_catalog` returns one at the labels' version; otherwise a note says `"label ids not checked"`.
    6. `run_eval` runs each of `CATALOG_EVALUATORS`; `run_eval` checks the freeze on held-out.
    7. Values come from each results file's `totals.metrics` through `RESULT_METRICS`, plus `tokens_ratio` and `existing_gates`. When the silence results' `totals.counts["open.findings"]` is 0, the reason for `silence_precision_open` is `SILENCE_NONE_REASON`.
    8. `evaluate(load_gates(gates_path, section="catalog_gates", metrics=CATALOG_METRICS), values, reasons)` and `catalog_overall`.
  - `def report_json(r: CatalogGateReport) -> dict[str, Any]`: keys `status`, `set`, `values`, `informational`, `gates` (`[{id, status, value, reason}]`), `results`, `provenance`, `per_entry` and `notes`.
  - `def render_report(r: CatalogGateReport) -> str`: one line per gate (`PASS`/`FAIL`/`NOT AVAILABLE`, value, reason; an accepted gap reads `NOT AVAILABLE (accepted)`), a `cost_usd` line (off, open, ratio; "reported, not gated"), the notes, and a last line `RESULT: <status>`.
  - CLI: `catalog gates CORPUS --set dev|heldout [--root DIR] [--results-dir DIR] [--gates PATH] [--strict] [--json]`.
    - `--root` defaults to `.`; `--results-dir` to `<root>/eval/results`; `--gates` to `<root>/eval/gates.yaml`.
    - Exit 0 on `pass` (accepted gaps included), or on `pass_with_gaps` without `--strict`; 1 on `fail`, or gaps with `--strict`.
    - Exit 2 on `CorpusError`, `FreezeError`, `GatesError`, `CatalogGateError`, an evaluator `ValueError`, or a set with no entries.

- [ ] **Step 1: Write the failing tests**

```python
def gates(root, manifest, *args):
    return CliRunner().invoke(main, ["catalog", "gates", str(manifest), "--root", str(root), *args])

def test_dev_mixed_scenario(tmp_path):
    root, m = scenario(tmp_path)
    r = gates(root, m, "--set", "dev", "--json"); out = json.loads(r.stdout)
    assert r.exit_code == 1 and out["status"] == "fail"
    assert [(g["id"], g["status"]) for g in out["gates"]] == [
        ("catalog_tm_recall", "fail"), ("catalog_lens_precision", "pass"), ("catalog_derived_precision", "fail"),
        ("catalog_silence_precision", "fail"), ("catalog_tokens", "pass"), ("catalog_existing_gates", "pass")]
    v = out["values"]
    assert v["tm_recall_delta"] == -0.125 and v["lens_precision_delta"] == pytest.approx(7 / 72)
    assert v["derived_precision_open"] == pytest.approx(5 / 7) and v["silence_precision_open"] == pytest.approx(1 / 3)
    assert v["tokens_ratio_open_off"] == 1.05 and v["existing_gates_failed_entries"] == 0
    assert out["informational"] == {"cost_usd_off": pytest.approx(1.1), "cost_usd_open": pytest.approx(1.155),
                                    "cost_ratio_open_off": pytest.approx(1.05)}
    assert sorted(p.name for p in (root / "eval/results").iterdir()) == sorted(CATALOG_EVALUATORS)

def test_zero_silence_findings_accepted(tmp_path):
    root, m = scenario(tmp_path, passing=True, silence=False)          # every open run writes no silence finding
    r = gates(root, m, "--set", "dev", "--strict", "--json"); out = json.loads(r.stdout)
    assert r.exit_code == 0 and out["status"] == "pass"
    assert (out["gates"][3]["status"], out["gates"][3]["reason"]) == ("not_available", "no silence findings produced")

def test_dev_passing_scenario(tmp_path):
    root, m = scenario(tmp_path, passing=True)
    assert gates(root, m, "--set", "dev").exit_code == 0

def test_tokens_ratio_pools_entry_means(tmp_path):
    a = run_sets(write_run_set(tmp_path, "a", sys_runs()), entry_id="a")       # off 1000/1200, open 1100/1210
    runs = sys_runs()
    for spec, t in zip(runs["off"] + runs["open"], (100, 100, 300, 300)):
        spec.tokens = t
    b = run_sets(write_run_set(tmp_path, "b", runs), entry_id="b")
    ratio, reason, per_entry = tokens_ratio([a, b])
    assert ratio == pytest.approx(1455 / 1200) and reason is None and per_entry["b"] == 3.0

def test_missing_usage_not_available(tmp_path):
    root, m = scenario(tmp_path, passing=True); (root / "runs/sys-open-r2/.apd-state/usage.yaml").unlink()
    out = json.loads(gates(root, m, "--set", "dev", "--json").stdout)
    assert out["status"] == "pass_with_gaps" and out["gates"][4]["status"] == "not_available"
    assert "usage" in out["gates"][4]["reason"] and gates(root, m, "--set", "dev", "--strict").exit_code == 1

def test_existing_gate_failure_counted(tmp_path):
    root, m = scenario(tmp_path, passing=True)
    for run in ("sys-open-r1", "sys-open-r2"):
        drop_finding(root / "runs" / run, "Claims API accepts unsigned member tokens")   # high F1 lost on the open side
    out = json.loads(gates(root, m, "--set", "dev", "--json").stdout)
    assert out["values"]["existing_gates_failed_entries"] == 1 and out["gates"][5]["status"] == "fail"

def test_invalid_labels_write_no_results(tmp_path):
    root, m = scenario(tmp_path)
    set_label(root, "threats", 0, verdict="unreviewed")
    assert gates(root, m, "--set", "dev").exit_code == 2 and not (root / "eval/results").exists()

def test_stale_selection_version_heldout_exits_2(tmp_path):
    root, m = scenario(tmp_path, set_name="heldout"); set_selection_version(root, 3); freeze(root)
    r = gates(root, m, "--set", "heldout")
    assert r.exit_code == 2 and "selection version" in r.output and not (root / "eval/results").exists()

def test_dev_stale_selection_is_a_note(tmp_path):
    root, m = scenario(tmp_path); set_selection_version(root, 3)
    out = json.loads(gates(root, m, "--set", "dev", "--json").stdout)
    assert any("selection version" in n for n in out["notes"])

def test_heldout_requires_bumped_selection(tmp_path):
    root, m = scenario(tmp_path, set_name="heldout", selection_version=1); freeze(root)
    r = gates(root, m, "--set", "heldout"); assert r.exit_code == 2 and "bump" in r.output

def test_heldout_refused_after_selection_edit(tmp_path):
    root, m = scenario(tmp_path, set_name="heldout"); freeze(root)
    edit_selection(root, top_n=4)
    r = gates(root, m, "--set", "heldout"); assert r.exit_code == 2 and "changed since freeze" in r.output

def test_heldout_requires_two_runs_per_config(tmp_path):
    root, m = scenario(tmp_path, set_name="heldout", open_runs=1); freeze(root)
    r = gates(root, m, "--set", "heldout"); assert r.exit_code == 2 and "twice" in r.output

def test_catalog_files_are_tunables():
    t = tunables(REPO)
    assert {"tools/apd_gauntlet/data/threat-catalog/selection.yaml",
            "tools/apd_gauntlet/data/threat-catalog/system-types.yaml"} <= set(t)

# tests/test_measuring_changes_doc.py
def test_runbook_covers_catalog_gates():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("apd-gauntlet catalog gates", "--set dev", "--set heldout", "selection.yaml", "system-types.yaml",
              "version", "eval freeze", "catalog-grounding", "1.05", "pooled", "pass_with_gaps", "cost_usd",
              "no silence findings produced", "One shared freeze"):
        assert s in t
```

`drop_finding(run_dir, title)` (removes that lens finding from `10-trustworthiness/lens.findings.yaml`), `set_label(root, section, index, **fields)`, `set_selection_version(root, n)` and `edit_selection(root, **params)` are small helpers added to `tests/catalog_eval/runs.py`. Each rewrites one YAML file in the scenario root.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_catalog_gates.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (`No such command 'gates'`)

- [ ] **Step 3: Implement `gates.py`, the tunable globs, the command and the runbook subsection**

Runbook subsection "Tune, freeze and gate":

- **Dev loop.** Run `apd-gauntlet catalog gates eval/local/catalog/corpus.yaml --set dev`, read the gate table and the `catalog-grounding` rates, and change only `selection.yaml` (`top_n`, `max_per_family`, `shortlist_cap`, `silence_cap`, `exclude_families`) and `system-types.yaml`. Then rerun the open runs.
- **How "not below `off`" is computed.** Counts are pooled over both runs of each configuration and summed over entries; the gate requires delta ≥ 0.
- **Token ratio.** Σ of per-entry mean open tokens ÷ Σ of per-entry mean off tokens, where tokens are input + output + cache read + cache creation from `.apd-state/usage.yaml`; it must be ≤ 1.05. `cost_usd` is shown alongside (off, open, ratio) and never gated.
- **Silence with no findings.** If the open runs produce no `catalog_silence` finding, the silence gate reads `NOT AVAILABLE (accepted)` with "no silence findings produced" and counts as passing; any other unavailable gate blocks `open`.
- **Existing gates.** Evaluated per entry as `compare-runs <prefix>-off <prefix>-open --gates eval/gates.yaml`.
- **`pass_with_gaps` and `--strict`.**
- **Freeze sequence.**
  1. Bump `selection.yaml` `version`.
  2. Rerun the dev open runs only if you want dev numbers at the new version; otherwise dev reports a note.
  3. Run `apd-gauntlet eval freeze`.
  4. Commit the two files and `eval/frozen.yaml`.
- **One shared freeze.** WS2's `eval freeze` covers every workstream's tunables at once. Catalog development tuning finishes before the M6 `eval freeze`, together with IAC4's tuning and the `calibrate` runs (master plan Task 8); every held-out run of every workstream comes after it.
- **Held-out.** Run it once, at the frozen version.

CHANGELOG `### Added` bullet: "`catalog gates` evaluates the six threat catalog proposal gates on a labelled corpus", plus a `### Changed` bullet: "the threat catalog's `selection.yaml` and `system-types.yaml` are frozen tunables (`eval freeze`)".

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval tests/test_eval_freeze.py tests/test_cli_eval_run.py tests/test_measuring_changes_doc.py -v && mypy tools/ && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS; mypy clean; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation/gates.py tools/apd_gauntlet/eval/freeze.py tools/apd_gauntlet/cli.py docs/measuring-changes.md CHANGELOG.md tests/catalog_eval tests/test_measuring_changes_doc.py
git commit -m "feat(catalog): add catalog gates over off and open run sets; freeze the selection tunables"
```

### Task 10: The decision record and the default consistency check

**Files:**

- Create: `tools/apd_gauntlet/catalog/evaluation/decision.py`
- Modify: `tools/apd_gauntlet/cli.py` (`catalog gates --record PATH`), `docs/adrs/0028-committed-calibration-and-frozen-evaluation.md` (append `## Amendment (CAT4): threat catalog default decision`), `docs/measuring-changes.md` (subsection "Decide the default"), `CHANGELOG.md`, `tests/test_adr_0028.py`, `tests/test_measuring_changes_doc.py`
- Test: `tests/catalog_eval/test_decision.py`

**Interfaces:**

- Consumes: `CatalogGateReport`, `catalog_gate_report`, `CATALOG_EVALUATORS`, `ACCEPTED_GAPS`, `SILENCE_NONE_REASON` (Task 9); CAT1 `config.DEFAULT_EDITION`; CAT2's workflow constant `const CATALOG_DEFAULT_EDITION = '<edition>';` in `.claude/workflows/apd-gauntlet.js`
- Produces:
  - Constants:
    - `DECISION_RELPATH = Path("eval/catalog/decision.yaml")`
    - `WORKFLOW_RELPATH = Path(".claude/workflows/apd-gauntlet.js")`
    - `WORKFLOW_DEFAULT_RE = re.compile(r"const CATALOG_DEFAULT_EDITION = '(\w+)';")` (the same pattern as CAT2's parity test)
    - `UNMEASURED_REASON = "not measured"`
    - `CATALOG_GATE_IDS = ("catalog_tm_recall", "catalog_lens_precision", "catalog_derived_precision", "catalog_silence_precision", "catalog_tokens", "catalog_existing_gates")`
    - `RECORD_KEYS = frozenset({"schema_version", "decided_at", "decision", "set", "catalog", "selection_version", "frozen_sha256", "corpus_sha256", "n_entries", "runs", "results_sha256", "gates"})`
  - `@dataclass(frozen=True) class GateRecord: id: str; status: Literal["pass", "fail", "not_available"]; value: float | None; reason: str | None`. `reason` is `None` unless the status is `not_available`. It is then `SILENCE_NONE_REASON` for an accepted gap, else `UNMEASURED_REASON`; the detailed local reason, which may name runs, stays in the gate report and never reaches the record.
  - `@dataclass(frozen=True) class DecisionRecord`:
    - `decided_at: str`, `decision: Literal["open", "off"]`
    - `catalog: Mapping[str, str]`: `edition`, `version`, `sha256`
    - `selection_version: int`, `frozen_sha256: str`, `corpus_sha256: str`
    - `n_entries: int`, `runs: Mapping[str, int]`
    - `results_sha256: Mapping[str, str]`: evaluator name to the SHA-256 of its held-out results file
    - `gates: tuple[GateRecord, ...]`
  - `def gate_counts_as_pass(gate: GateRecord) -> bool`: `status == "pass"`, or `not_available` with `(id, reason)` matching `ACCEPTED_GAPS`.
  - `def decision_from_report(report: CatalogGateReport, *, today: date) -> DecisionRecord`: `decision` is `"open"` only when every gate counts as passing; values are rounded to 6 places. `ValueError` unless `report.set_name == "heldout"`.
  - `def write_decision(path: Path, record: DecisionRecord) -> None`: `FileExistsError` when `path` exists.
  - `def parse_decision_record(data: Mapping[str, Any]) -> DecisionRecord`: `ValueError` on any of:
    - a key outside `RECORD_KEYS`, or outside `{id, status, value, reason}` in a gate;
    - a `reason` other than `null`, `SILENCE_NONE_REASON` or `UNMEASURED_REASON`;
    - gate ids not equal to `CATALOG_GATE_IDS` in order;
    - `set != "heldout"`;
    - `decision: open` with any gate that does not count as passing.
  - `def workflow_default_edition(workflow_text: str) -> str | None`: the `WORKFLOW_DEFAULT_RE` group, `None` when absent.
  - `def load_decision(path: Path) -> DecisionRecord | None`: `None` when absent.
  - Fixed copy (exact):

    ```python
    CHANGELOG_OPEN = "**`threat_catalog` defaults to `open`.**"
    CHANGELOG_OFF = "**`threat_catalog` stays `off` by default for 2.0.**"
    SPEC_STATUS_BASE = "**Status:** Approved 2026-10-11"
    SPEC_STATUS_OPEN = SPEC_STATUS_BASE + "; default decided {decided_at}: `threat_catalog: open`"
    SPEC_STATUS_OFF = SPEC_STATUS_BASE + "; default decided {decided_at}: `threat_catalog` stays `off` for 2.0"
    ```

  - `def spec_status_line(record: DecisionRecord | None) -> str`: `SPEC_STATUS_BASE` without a record, else `SPEC_STATUS_OPEN` or `SPEC_STATUS_OFF` formatted with `decided_at`.
  - `def check_default_decision(record: DecisionRecord | None, *, default_edition: str, workflow_default_edition: str | None, changelog: str, spec: str) -> list[str]` returns one error string per mismatch:
    - `default_edition` (Python's `DEFAULT_EDITION`) must equal `record.decision`, or `"off"` without a record; the error names `DEFAULT_EDITION`;
    - `workflow_default_edition` (the workflow's `CATALOG_DEFAULT_EDITION`) must equal the same value; the error names `CATALOG_DEFAULT_EDITION` and `.claude/workflows/apd-gauntlet.js`;
    - the spec's `**Status:**` line must equal `spec_status_line(record)`;
    - the CHANGELOG must contain the matching sentence (`CHANGELOG_OPEN` or `CHANGELOG_OFF`) and not the other, or neither without a record.
  - CLI: `catalog gates … --record PATH` writes the record after the report. It exits 2 with `--set dev` (`"the default is decided on held-out results only"`) or when `PATH` exists (`"already decided; remove <path> deliberately to re-decide"`). Otherwise the exit code is Task 9's, and the output adds `Decision: <open|off> -> <path>`.

- [ ] **Step 1: Write the failing tests**

```python
def heldout(tmp_path, **kw):
    root, m = scenario(tmp_path, set_name="heldout", **kw); freeze(root); return root, m

def test_record_open_when_every_gate_passes(tmp_path):
    root, m = heldout(tmp_path, passing=True); rec = root / DECISION_RELPATH
    r = gates(root, m, "--set", "heldout", "--record", str(rec)); doc = yaml.safe_load(rec.read_text())
    assert r.exit_code == 0 and doc["decision"] == "open" and {g["status"] for g in doc["gates"]} == {"pass"}
    assert set(doc) == RECORD_KEYS and (doc["n_entries"], doc["runs"]) == (1, {"off": 2, "open": 2})
    assert doc["frozen_sha256"] == check_frozen(root) and doc["selection_version"] == 2
    assert set(doc["results_sha256"]) == set(CATALOG_EVALUATORS)
    text = rec.read_text()
    assert "TC-" not in text and "sys" not in text and "runs/" not in text

def test_record_off_on_mixed_scenario(tmp_path):
    root, m = heldout(tmp_path); rec = root / DECISION_RELPATH
    assert gates(root, m, "--set", "heldout", "--record", str(rec)).exit_code == 1
    assert yaml.safe_load(rec.read_text())["decision"] == "off"

def test_unmeasured_gate_records_off(tmp_path):
    root, m = heldout(tmp_path, passing=True); rec = root / DECISION_RELPATH
    (root / "runs/sys-open-r2/.apd-state/usage.yaml").unlink()
    assert gates(root, m, "--set", "heldout", "--record", str(rec)).exit_code == 0          # pass_with_gaps
    doc = yaml.safe_load(rec.read_text())
    assert doc["decision"] == "off" and doc["gates"][4] == {
        "id": "catalog_tokens", "status": "not_available", "value": None, "reason": "not measured"}
    assert "sys-open-r2" not in rec.read_text()

def test_zero_silence_findings_record_open(tmp_path):
    root, m = heldout(tmp_path, passing=True, silence=False); rec = root / DECISION_RELPATH
    assert gates(root, m, "--set", "heldout", "--record", str(rec)).exit_code == 0
    doc = yaml.safe_load(rec.read_text())
    assert doc["decision"] == "open"
    assert (doc["gates"][3]["status"], doc["gates"][3]["reason"]) == ("not_available", "no silence findings produced")

def test_record_requires_heldout(tmp_path):
    root, m = scenario(tmp_path, passing=True)
    assert gates(root, m, "--set", "dev", "--record", str(root / DECISION_RELPATH)).exit_code == 2
    assert not (root / DECISION_RELPATH).exists()

def test_existing_record_not_overwritten(tmp_path):
    root, m = heldout(tmp_path, passing=True); rec = root / DECISION_RELPATH
    gates(root, m, "--set", "heldout", "--record", str(rec)); before = rec.read_bytes()
    r = gates(root, m, "--set", "heldout", "--record", str(rec))
    assert r.exit_code == 2 and "already decided" in r.output and rec.read_bytes() == before

def test_parse_rejects_open_with_failing_gate(): ...      # OPEN_RECORD with gates[2].status fail → ValueError
def test_parse_rejects_open_with_unaccepted_gap(): ...    # OPEN_RECORD with catalog_tokens not_available "not measured" → ValueError
def test_parse_rejects_free_text_reason(): ...            # a gate reason "no usage in runs/x-open-r2" → ValueError
def test_parse_rejects_extra_keys(): ...                  # {"entries": [...]} or a gate with "entry" → ValueError
def test_parse_requires_the_six_gates(): ...              # five gates → ValueError naming catalog_existing_gates
def test_gate_ids_match_gates_file():
    assert tuple(g.id for g in load_gates(REPO / "eval/gates.yaml", section="catalog_gates",
                                          metrics=CATALOG_METRICS)) == CATALOG_GATE_IDS

SPEC_OPEN = f"# T\n\n{SPEC_STATUS_BASE}; default decided 2026-12-01: `threat_catalog: open`\n"
SPEC_OFF = f"# T\n\n{SPEC_STATUS_BASE}; default decided 2026-12-01: `threat_catalog` stays `off` for 2.0\n"

def test_check_open_branch():
    assert check_default_decision(OPEN_RECORD, default_edition="open", workflow_default_edition="open",
                                  changelog=f"- {CHANGELOG_OPEN} …", spec=SPEC_OPEN) == []

def test_check_off_branch():
    assert check_default_decision(OFF_RECORD, default_edition="off", workflow_default_edition="off",
                                  changelog=f"- {CHANGELOG_OFF} …", spec=SPEC_OFF) == []

def test_check_open_record_with_off_default():
    errs = check_default_decision(OPEN_RECORD, default_edition="off", workflow_default_edition="open",
                                  changelog=f"- {CHANGELOG_OPEN}", spec=SPEC_OPEN)
    assert len(errs) == 1 and "DEFAULT_EDITION" in errs[0] and "CATALOG_DEFAULT_EDITION" not in errs[0]

def test_check_workflow_mirror_must_match():
    errs = check_default_decision(OPEN_RECORD, default_edition="open", workflow_default_edition="off",
                                  changelog=f"- {CHANGELOG_OPEN}", spec=SPEC_OPEN)
    assert len(errs) == 1 and "CATALOG_DEFAULT_EDITION" in errs[0] and ".claude/workflows/apd-gauntlet.js" in errs[0]

def test_check_off_record_with_open_defaults(): ...       # both editions "open" → two errors, one per name
def test_check_wrong_changelog_sentence(): ...            # OFF_RECORD with CHANGELOG_OPEN → error naming the CHANGELOG
def test_check_status_date_must_match(): ...              # OPEN_RECORD decided 2026-12-01, spec says 2026-12-02 → error

def test_check_no_record():
    base = f"# T\n\n{SPEC_STATUS_BASE}\n"
    ok = dict(default_edition="off", workflow_default_edition="off", changelog="", spec=base)
    assert check_default_decision(None, **ok) == []
    assert check_default_decision(None, **{**ok, "default_edition": "open"})
    assert check_default_decision(None, **{**ok, "workflow_default_edition": None})
    assert check_default_decision(None, **{**ok, "changelog": CHANGELOG_OPEN})

def test_workflow_default_edition():
    assert workflow_default_edition("x\nconst CATALOG_DEFAULT_EDITION = 'off';\n") == "off"
    assert workflow_default_edition("nothing here") is None

def test_repository_default_matches_decision():
    spec = REPO / "docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md"
    assert check_default_decision(
        load_decision(REPO / DECISION_RELPATH), default_edition=DEFAULT_EDITION,
        workflow_default_edition=workflow_default_edition((REPO / WORKFLOW_RELPATH).read_text()),
        changelog=(REPO / "CHANGELOG.md").read_text(), spec=spec.read_text()) == []

# tests/test_adr_0028.py
def test_amendment_names_catalog_decision_record():
    t = ADR.read_text()
    assert "eval/catalog/decision.yaml" in t and "aggregate" in t.lower()

# tests/test_measuring_changes_doc.py
def test_runbook_covers_catalog_decision():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("--record eval/catalog/decision.yaml", "DEFAULT_EDITION", "CATALOG_DEFAULT_EDITION", "already decided",
              "ADR-0028"):
        assert s in t
```

`OPEN_RECORD` and `OFF_RECORD` are module-level `DecisionRecord`s in the test file (six `GateRecord`s with `reason=None`; all `pass` for `OPEN_RECORD`; `catalog_tm_recall` `fail` for `OFF_RECORD`; `decided_at="2026-12-01"`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/catalog_eval/test_decision.py tests/test_adr_0028.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (`ModuleNotFoundError: …decision`; `no such option: --record`)

- [ ] **Step 3: Implement `decision.py`, `--record`, the ADR amendment and the runbook subsection**

The ADR-0028 amendment (dated with the commit date) states:

- `eval/catalog/decision.yaml` is committed under the same narrow exception to ADR-0017;
- it holds only aggregate gate values over the held-out corpus, gate statuses with a reason from a fixed list, entry and run counts, the catalog version and digest, the selection version, and SHA-256 digests of local files;
- it never holds entry ids, run names, threat ids, labels or per-entry values;
- `parse_decision_record` enforces the field list.

Runbook subsection "Decide the default":

- the held-out command with `--record eval/catalog/decision.yaml`;
- the record is written once, and a second call is refused;
- `open` requires every gate to pass; a `not_available` gate counts against it, except the silence gate with "no silence findings produced";
- the record, `DEFAULT_EDITION`, the workflow's `CATALOG_DEFAULT_EDITION`, the CHANGELOG sentence and the spec status line are committed together, because `test_repository_default_matches_decision` ties them;
- the record falls under ADR-0028's exception.

CHANGELOG `### Added` bullet: "`catalog gates --record` writes the aggregate held-out decision record".

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/catalog_eval tests/test_adr_0028.py tests/test_measuring_changes_doc.py -v && ruff check tools/ tests/ && mypy tools/ && pytest -q && markdownlint-cli2 docs/measuring-changes.md docs/adrs/0028-*.md CHANGELOG.md`
Expected: PASS (`test_repository_default_matches_decision` passes with no record, both editions `"off"` and the unchanged status line); ruff and mypy clean; coverage ≥ 85; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/catalog/evaluation/decision.py tools/apd_gauntlet/cli.py docs/adrs/0028-*.md docs/measuring-changes.md CHANGELOG.md tests/catalog_eval/test_decision.py tests/test_adr_0028.py tests/test_measuring_changes_doc.py
git commit -m "feat(catalog): record the held-out default decision and pin it to DEFAULT_EDITION"
```

### Task 11: Label, tune on development data, freeze, measure held-out once (operator)

**Files:**

- Local only: `eval/local/catalog/corpus.yaml`, `eval/local/catalog/labels/*.yaml`, `runs/<system>-{off,open,full}-r<N>/`, `telemetry/*.otlp.jsonl`, `eval/results/catalog-*/`, and `eval/catalog/decision.yaml` (written here, committed in Task 12)
- Commit: `tools/apd_gauntlet/data/threat-catalog/selection.yaml`, `tools/apd_gauntlet/data/threat-catalog/system-types.yaml`, `eval/frozen.yaml`

Every step runs locally (ADR-0017, ADR-0028); nothing run-derived is committed here.

- [ ] **Step 1: Check the preconditions**

These must hold:

- CAT1's vendoring task is done: `tools/apd_gauntlet/data/threat-catalog/open.json` is committed, and `apd-gauntlet catalog scope` on a run with `threat_catalog: open` writes a scope whose `catalog` is not `null`.
- CAT2, CAT3, WS2 and Tasks 1–10 are merged on `next`.
- The telemetry collector from master plan Task 1 Step 1 is running.
- No held-out run of any workstream has happened yet. M6 has one shared freeze (master plan Task 8): catalog tuning (Steps 2–5) runs alongside IAC4's tuning and the `calibrate` runs, and every held-out run comes after the freeze.

Expected: all four hold; otherwise stop.

- [ ] **Step 2: Write the corpus manifest**

`eval/local/catalog/corpus.yaml` follows WS2's shape:

- **Development:** the master plan Task 1 systems (`examples/apd-20260601-claim-event-bus`, `examples/apd-20260602-acme-mobile-banking`, `examples/apd-20260612-home-assistant` and the private PBM system). Each entry has `run: ../../../runs/<system>` and `labels: labels/<id>.yaml`.
- **Held-out:** private systems never used in development, chosen by the operator.

Expected: `load_corpus_manifest` succeeds (disjoint sets).

- [ ] **Step 3: Run the development configurations**

For each development system:

- run the gauntlet twice with `threat_catalog: off` and twice with `threat_catalog: open` (names `runs/<system>-off-r1` … `-open-r2`), and optionally once with a local `full` path (`-full-r1`);
- run `apd-gauntlet usage <run> --otel telemetry/<run>.otlp.jsonl` and `apd-gauntlet validate <run>` for each run.

Expected: every run validates ("Clean."); each `usage` exits 0 without the "agent names redacted" warning.

- [ ] **Step 4: Label the development systems**

For each development system, run `apd-gauntlet eval label-template runs/<system> --kind threats --entry <id> --out eval/local/catalog/labels/<id>.yaml`, then review it per the runbook's "Label catalog threats". Expected: `threat_labels` raises nothing for any labels file.

- [ ] **Step 5: Tune on development data only**

Run `apd-gauntlet catalog gates eval/local/catalog/corpus.yaml --set dev`. Adjust `selection.yaml` (`top_n`, `max_per_family`, `shortlist_cap`, `silence_cap`, `exclude_families`) and `system-types.yaml` from the dev gate values and `catalog-grounding` rates, rerun the open runs, `--merge` the labels, and repeat. Expected: the dev gates pass, or the operator notes privately which gates still fail and proceeds; the held-out result decides either way.

- [ ] **Step 6: Freeze (the shared M6 freeze)**

Bump `selection.yaml` `version` by one (to at least 2). Once IAC4's parameters and the calibrated thresholds are also final, run the single M6 `apd-gauntlet eval freeze`; if another workstream runs it, this step only confirms the catalog files are in it. Expected: `eval/frozen.yaml` written, and `apd-gauntlet eval freeze` run again reports it unchanged.

```bash
git add tools/apd_gauntlet/data/threat-catalog/selection.yaml tools/apd_gauntlet/data/threat-catalog/system-types.yaml eval/frozen.yaml
git commit -m "chore(catalog): selection tuned on development data and frozen"
```

- [ ] **Step 7: Run and label the held-out systems**

Run the held-out systems as in Step 3, with the open runs at the frozen version, then label them as in Step 4. Do not change any tunable after this point. Expected: all runs validate; labels parse.

- [ ] **Step 8: Measure once**

Run: `apd-gauntlet catalog gates eval/local/catalog/corpus.yaml --set heldout --record eval/catalog/decision.yaml`
Expected: exit 0 or 1, and `Decision: open -> eval/catalog/decision.yaml` or `Decision: off -> …`. Do not rerun; the record is left uncommitted for Task 12.

### Task 12: Set the 2.0 default from the record (operator-gated)

**Files:**

- Create: `eval/catalog/decision.yaml` (from Task 11 Step 8)
- Modify:
  - `CHANGELOG.md`;
  - `docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md` (line 4, the status line);
  - `RELEASING.md` (the `v2.0.0b1` checklist IAC4 adds under "Cutting a 2.0 pre-release");
  - open branch only: `tools/apd_gauntlet/catalog/config.py` (`DEFAULT_EDITION`), `.claude/workflows/apd-gauntlet.js` (`CATALOG_DEFAULT_EDITION`, CAT2 Task 9), `docs/running-the-gauntlet.md` (CAT1's `### Threat catalog (v2.0+)`), `docs/adrs/0030-threat-catalog-enrichment-layer.md` (CAT1), `tests/test_catalog_config.py` (CAT1's `test_absent_is_off_by_default`), `tests/test_workflow_runner_awaits.py` (`EXPECTED_GREEN_LABELS`, or the harness `ARGS`; register A15.27), and test fixtures that relied on an absent key meaning `off`.
- Test: `tests/catalog_eval/test_decision.py::test_repository_default_matches_decision`

**Interfaces:**

- Consumes: `load_decision`, `spec_status_line`, `CHANGELOG_OPEN`, `CHANGELOG_OFF`, `check_default_decision`, `workflow_default_edition` (Task 10); CAT2's parity test `tests/test_workflow_apd_gauntlet.py::test_catalog_default_edition_mirrors_python`
- Produces: a committed decision record consistent with `DEFAULT_EDITION`, the workflow's `CATALOG_DEFAULT_EDITION`, the CHANGELOG and the spec status line. `plan_run` and `runner/flow.py` follow `DEFAULT_EDITION` through `catalog_config_from_run_config` (CAT2 Task 9), so they need no edit.

This task edits `.claude/workflows/apd-gauntlet.js` on the open branch, so its PR merges alone (master plan "merges one PR at a time").

- [ ] **Step 1: Read the decision**

Run: `python -c "from pathlib import Path; from apd_gauntlet.catalog.evaluation.decision import load_decision; print(load_decision(Path('eval/catalog/decision.yaml')).decision)"`
Expected: `open` or `off`. The test pins the branch the next step takes.

- [ ] **Step 2 (decision `open`): Flip the default**

Make these edits:

- In `tools/apd_gauntlet/catalog/config.py` set `DEFAULT_EDITION: Literal["off", "open"] = "open"`, and in `.claude/workflows/apd-gauntlet.js` set `const CATALOG_DEFAULT_EDITION = 'open';`, keeping CAT2's comment.
- In `tests/test_workflow_runner_awaits.py`, the harness `ARGS` set no `threat_catalog`, and CAT2's `catalogEdition(a)` returns `CATALOG_DEFAULT_EDITION` when the key is absent, so the green run now dispatches `catalog-scope` (first in `threat-model-author`, before `author-threat-model-floor`) and `catalog-shortlists` (right after `canonicalize-threat-model`, as CAT3 Task 5 pins). Add both to `EXPECTED_GREEN_LABELS` at those positions in this commit, or set `threat_catalog: 'off'` in the harness `ARGS` (register A15.21, A15.27).
- Under ``## Unreleased — 2.0 line (`next`)`` `### Changed`, add a bullet beginning with `CHANGELOG_OPEN`, followed by: "The held-out evaluation passed every threat catalog gate (`eval/catalog/decision.yaml`). Set `threat_catalog: off` to keep 1.7 behaviour."
- Replace the spec's status line with `spec_status_line(record)`.
- In `docs/running-the-gauntlet.md` `### Threat catalog (v2.0+)`, change the sentence about the absent key's default to say `open`. In ADR-0030, add a dated line under Consequences: "CAT4's held-out gates passed; `DEFAULT_EDITION` is `open` (`eval/catalog/decision.yaml`)."
- Rename CAT1's `test_absent_is_off_by_default` to `test_absent_follows_the_recorded_decision`, asserting `DEFAULT_EDITION == load_decision(REPO / DECISION_RELPATH).decision` and `catalog_config_from_run_config({"run_id": "r"}) == CatalogConfig("open", None, (), ())`.
- Run `pytest -q`. For each failure caused by a fixture whose `.apd-run.yaml` relied on an absent key meaning `off`, add `threat_catalog: off` to that fixture without changing its expectations.
- Append to the `v2.0.0b1` checklist: "`eval/catalog/decision.yaml` committed and `test_repository_default_matches_decision` green".

- [ ] **Step 2 (decision `off`): Record that `off` stays**

Make these edits; `DEFAULT_EDITION` and `CATALOG_DEFAULT_EDITION` stay `off`:

- Under ``## Unreleased — 2.0 line (`next`)`` `### Changed`, add a bullet beginning with `CHANGELOG_OFF`, followed by: "The held-out evaluation failed <gate ids from the record> (`eval/catalog/decision.yaml`). Set `threat_catalog: open` to opt in."
- Replace the spec's status line with `spec_status_line(record)`.
- Append the same `v2.0.0b1` checklist line as the open branch.

- [ ] **Step 3: Run the consistency test and the full suite**

Run: `pytest tests/catalog_eval/test_decision.py tests/test_workflow_apd_gauntlet.py tests/test_workflow_dispatch_trace.py tests/test_cli_plan_run.py tests/runner -v && ruff check tools/ tests/ && mypy tools/ && pytest -q && markdownlint-cli2 CHANGELOG.md RELEASING.md docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md`
Expected: PASS, including `test_repository_default_matches_decision`, CAT2's `test_catalog_default_edition_mirrors_python`, and the dispatch-trace and runner tests, which follow the new default; 0 lint errors

- [ ] **Step 4 (decision `open` only, operator): Measure the new default**

Run the master plan Task 1 set twice with no `threat_catalog` key (names ending `-default-r1` and `-default-r2`), then run `apd-gauntlet compare-runs runs/<example>-off runs/<example>-default --gates eval/gates.yaml` for each example, against Task 11's development `-off` runs.
Expected: exit 0 for each. A run without the key now behaves as `open`, and the `-default` scope files report `edition: open`.

- [ ] **Step 5: Commit**

```bash
git add eval/catalog/decision.yaml CHANGELOG.md RELEASING.md docs/superpowers/specs/2026-10-11-threat-catalog-integration-design.md tools/apd_gauntlet/catalog/config.py .claude/workflows/apd-gauntlet.js docs tests
git commit -m "feat(catalog): default threat_catalog to open (held-out gates passed)"
# or, for the off branch:
git commit -m "docs(catalog): threat_catalog stays off for 2.0 (held-out gates failed)"
```
