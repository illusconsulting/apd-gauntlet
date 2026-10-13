# WS2 Measurement and Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every later workstream a deterministic, local before-and-after measurement: `compare-runs` with gates, per-agent token and cost `usage`, an evaluation framework with a frozen held-out protocol, threshold `calibrate`, and a generic metamorphic harness.

**Architecture:** A `measure` package reads finished run directories (findings, capabilities, asset graph, report headlines, `.apd-state/` attempt and usage files) and computes a pairwise delta, then side medians and gate outcomes from `eval/gates.yaml`. An `eval` package holds the `eval-corpus` and `eval-labels` schemas, the evaluator registry (R2), the findings evaluator, a content-hash freeze guard for held-out sets, threshold calibration over LA1 decision records, and a metamorphic suite registry. The workflow records retries and audit iterations into `.apd-state/attempts.yaml` through the closeout `summarize` step, so 2.0 runs carry the data 1.7 runs lack.

**Tech Stack:** Python 3.10+, click, PyYAML, jsonschema (Draft 2020-12), stdlib `statistics`/`hashlib`/`json`; pytest with `click.testing.CliRunner`; hand-authored OTLP/JSON fixtures. No new dependencies.

**Spec:** Cost and token audit (Claude Doc "APD Gauntlet cost and token audit", 2026-10-10), "Protecting accuracy"; `docs/superpowers/plans/2026-10-10-program-master-plan.md` Global Constraints, Review Focus, Task 1, Registry R1, R2, R6, R7, R8; `docs/superpowers/specs/2026-10-10-iac-terraform-opentofu-atmos-design.md` §13.2–13.3; GRAML (arXiv:2610.09605) §II-E (τ* chosen on validation data, then fixed) and its dataset section (cross-dataset deduplication of held-out sets); `docs/adrs/0017-local-only-accuracy-benchmark.md`; Claude Code monitoring docs (`https://code.claude.com/docs/en/monitoring-usage`, read 2026-10-11).

## Global Constraints

- Ships on `next` (2.0 line); CHANGELOG entries go under ``## Unreleased — 2.0 line (`next`)``.
- **CI never touches the network** (ADR-0017). Real-run accuracy is judged locally, and real runs are never committed.
- Gate 1 (proposal, `eval/gates.yaml`): no critical or high finding lost unless the loss traces to evidence
- Gate 2: severity agrees on at least 90% of matched findings
- Gate 3: blocked rate moves by no more than 5 points
- Gate 4: first-pass schema validity and retry count no worse than baseline
- Gate 5: report audit passes in no more iterations than baseline
- Run each configuration twice. Model output varies between runs, so one comparison can't tell a regression from noise.
- Keep each run directory and its telemetry export under a name ending `-baseline-r1` or `-baseline-r2`.
- Telemetry (master plan Task 1): `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_LOGS_EXPORTER=otlp` (or `console`, redirected to a file), `OTEL_LOG_TOOL_DETAILS=1`; "Custom agents report as `custom` without the last one."
- `claude_code.api_request` attributes (docs, read 2026-10-11): `model`, `cost_usd`, `cost_usd_micros`, `duration_ms`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `request_id`, `query_source`, `effort`, `agent.name`; events also carry `event.name` (`api_request`), `session.id`, `workflow.run_id`, `workflow.name`.
- R1 `compare-runs <baseline> <candidate> [--json] [--gates eval/gates.yaml]`: "A deterministic delta. Exits 0 when every gate passes, 1 when any fails, 2 on usage errors or a missing baseline."
- R1 `usage <run-dir> --otel <file>`: "Summarises tokens and cost per agent and phase from OpenTelemetry `claude_code.api_request` events into `<run-dir>/.apd-state/usage.yaml`."
- R1 `eval run <corpus.yaml> --set dev|heldout --evaluator <name>`: "Runs a registered evaluator and writes `eval/results/<evaluator>/<set>-<timestamp>.yaml`."
- R1 `calibrate <task> --labels <file> --target-precision <p>`: "Writes or updates `tools/apd_gauntlet/data/decide/thresholds.yaml` entry `<task>: {threshold, precision, recall, n, labels_sha256, calibrated: true}`."
- R1 `metamorphic run --suite <name>`: "Generic invariance harness. Suites register transformations (IAC4: T1–T8; CF4 adds its own)."
- R2 `apd_gauntlet.eval.evaluators`: `register(name: str, fn: Callable[[CorpusEntry, Labels], EvalResult])`.
- Tuning protocol (IaC spec §13.2): "Tunables are tuned on development only and frozen before held-out runs … A tunable changed after a held-out run means a new held-out set."
- "Thresholds come from `calibrate` on development labels, frozen before held-out runs." (master plan)
- "Set each auto-decide threshold for at least 98% precision on the labeled set (a proposal)." (audit)
- Quality gates: `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest` (coverage `fail_under = 85`), and `markdownlint-cli2` on the linted globs all pass on every PR.
- Every new schema `$ref`s `_defs.schema.json#/$defs/<name>` for severity, goal, tier and disposition (`tests/test_schema_vocab_centralized.py`).

## Review Focus

- **Comparing against no baseline or the wrong one** (path missing, same directory as the candidate, a scaffold with no findings, runs over different `inputs/`): `compare-runs` exits 2 and names the problem. Pinned in Task 6 (`test_missing_baseline_exits_2`, `test_same_run_exits_2`, `test_scaffold_baseline_exits_2`, `test_different_inputs_exit_2`).
- **A gate whose data is missing** (1.7 runs record no attempts; a resumed run under-counts retries): the gate reads `not_available`, overall status `pass_with_gaps`, and `--strict` turns that into exit 1; it is never printed as passed. Pinned in Task 6 (`test_attempt_gates_not_available_on_1_7_runs`, `test_resumed_run_attempts_not_available`, `test_strict_fails_on_gaps`).
- **Telemetry exported without `OTEL_LOG_TOOL_DETAILS=1`, or in console format**: `usage` attributes `custom`/`third-party` agents to `unattributed` with a warning naming the variable, and refuses non-OTLP/JSON input with exit 2. Pinned in Task 4 (`test_redacted_agent_names_warn`, `test_console_export_refused`).
- **Tuning after a held-out run** (a tunable edited after `eval freeze`, or a re-freeze after held-out use): `eval run --set heldout` exits 2; `eval freeze` exits 1 unless `--new-heldout-set`. Pinned in Task 10 (`test_refreeze_after_heldout_use_refused`) and Task 11 (`test_heldout_after_tunable_edit_exits_2`).
- **Calibration that proves nothing** (held-out labels, fewer predicted positives than `--min-support`, no threshold meeting the target): `calibrate` never writes `calibrated: true`, exits 2 or 1, and leaves `thresholds.yaml` byte-identical. Pinned in Task 12 (`test_heldout_labels_refused`, `test_min_support_refuses_tiny_sets`).

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/measure/__init__.py` | Package marker | Create |
| `tools/apd_gauntlet/measure/match.py` | Title/asset normalisation, deterministic one-to-one record matching | Create |
| `tools/apd_gauntlet/measure/runs.py` | `RunSnapshot` loader, input digest, run-dir test | Create |
| `tools/apd_gauntlet/measure/compare.py` | Pairwise delta, side resolution, medians, rendering | Create |
| `tools/apd_gauntlet/measure/attempts.py` | `.apd-state/attempts.yaml` read/write | Create |
| `tools/apd_gauntlet/measure/usage.py` | OTLP/JSON parsing (one function), agent→phase map, `usage.yaml` | Create |
| `tools/apd_gauntlet/measure/gates.py` | `eval/gates.yaml` loader and gate evaluation | Create |
| `tools/apd_gauntlet/eval/__init__.py` | Package marker | Create |
| `tools/apd_gauntlet/eval/corpus.py` | Corpus manifests and labels (schemas, disjoint sets) | Create |
| `tools/apd_gauntlet/eval/evaluators.py` | R2 registry, `EvalResult` | Create |
| `tools/apd_gauntlet/eval/findings_eval.py` | `findings` evaluator, label template | Create |
| `tools/apd_gauntlet/eval/freeze.py` | Tunables hash, `eval/frozen.yaml`, held-out guard | Create |
| `tools/apd_gauntlet/eval/runner.py` | `eval run` orchestration and results file | Create |
| `tools/apd_gauntlet/eval/calibrate.py` | Value specs, threshold choice, `thresholds.yaml` writer | Create |
| `tools/apd_gauntlet/eval/metamorphic.py` | Suite registry and invariance runner | Create |
| `tools/apd_gauntlet/eval/suites/__init__.py`, `stride_table.py` | Demonstration suite over `parse-threat-model` | Create |
| `tools/apd_gauntlet/data/schemas/run-attempts.schema.json` | Attempts file schema | Create |
| `tools/apd_gauntlet/data/schemas/eval-corpus.schema.json`, `eval-labels.schema.json` | R7 schemas | Create |
| `tools/apd_gauntlet/data/decide/thresholds.yaml` | R8 thresholds (starts empty) | Create |
| `tools/apd_gauntlet/cli.py` | `summarize --record-attempts`; `usage`, `compare-runs`, `eval` group, `calibrate`, `metamorphic` group | Modify |
| `.claude/workflows/apd-gauntlet.js` | Count retries, first-pass failures, audit iterations; pass them to closeout | Modify |
| `eval/gates.yaml` | The five proposal gates | Create |
| `pyproject.toml` | Package data `data/decide/*.yaml` | Modify |
| `.gitignore` | `eval/results/`, `eval/local/` | Modify |
| `docs/measuring-changes.md` | Operator runbook | Create |
| `docs/adrs/0028-committed-calibration-and-frozen-evaluation.md` | Exception to ADR-0017 and the freeze protocol | Create |
| `docs/adrs/0017-local-only-accuracy-benchmark.md`, `docs/ci-gate-model.md`, `docs/running-the-gauntlet.md` | Cross-references | Modify |
| `docs/schema-evolution.md`, `CHANGELOG.md` | Records | Modify |
| `tests/conftest.py` | `make_run`, `edit` fixtures | Create |
| `tests/test_measure_*.py`, `tests/test_cli_compare_runs.py`, `tests/test_cli_usage.py`, `tests/test_eval_*.py`, `tests/test_cli_eval_run.py`, `tests/test_cli_calibrate.py`, `tests/test_adr_0028.py`, `tests/test_measuring_changes_doc.py` | Tests | Create |
| `tests/test_summarize.py`, `tests/test_workflow_apd_gauntlet.py` | Extend | Modify |
| `tests/fixtures/otel/*`, `tests/fixtures/eval/finding-qa.record.yaml`, `tests/fixtures/metamorphic/stride-table/basic/threat-model.md` | Fixtures | Create |

---

### Task 1: Finding matcher and run snapshot

**Files:**

- Create: `tools/apd_gauntlet/measure/__init__.py`, `tools/apd_gauntlet/measure/match.py`, `tools/apd_gauntlet/measure/runs.py`
- Test: `tests/test_measure_match.py`, `tests/test_measure_runs.py`

**Interfaces:**

- Consumes: `apd_gauntlet.synthesis.loader.load_corpus(run_dir, *, include_attack_path=True)` (`tools/apd_gauntlet/synthesis/loader.py:26-71`)
- Produces (`match.py`):
  - `STOPWORDS: frozenset[str]` = `{"a","an","and","are","at","be","by","for","from","in","is","of","on","or","the","to","via","with"}`
  - `TITLE_MIN_JACCARD: float = 0.5`
  - `def title_tokens(title: str) -> frozenset[str]` — NFKC, `casefold()`, `re.sub(r"[\W_]+", " ", s)`, split, drop `STOPWORDS`
  - `def asset_keys(record: Mapping[str, Any], graph_targets: Mapping[str, Sequence[str]]) -> frozenset[str]`
  - `def evidence_pairs(record: Mapping[str, Any]) -> frozenset[tuple[str, str]]` — `(normalised artifact, locator.strip())`
  - `def jaccard(a: frozenset[str], b: frozenset[str]) -> float` (0.0 when both empty)
  - `@dataclass(frozen=True) class Match: baseline_id: str; candidate_id: str; title_similarity: float; asset_similarity: float`
  - `@dataclass(frozen=True) class MatchResult: matched: tuple[Match, ...]; missing: tuple[str, ...]; new: tuple[str, ...]` (ids sorted)
  - `def match_records(baseline: Mapping[str, Mapping[str, Any]], candidate: Mapping[str, Mapping[str, Any]], *, baseline_targets: Mapping[str, Sequence[str]] | None = None, candidate_targets: Mapping[str, Sequence[str]] | None = None) -> MatchResult`
- Produces (`runs.py`):
  - `class RunLoadError(Exception)`
  - `@dataclass(frozen=True) class RunSnapshot: path: Path; findings: dict[str, dict[str, Any]]; capabilities: dict[str, dict[str, Any]]; graph_targets: dict[str, list[str]]; headlines: tuple[frozenset[str], ...] | None; inputs_sha256: str | None`
  - `def is_run_dir(path: Path) -> bool` → `(path / ".apd-run.yaml").is_file()`
  - `def inputs_digest(run_dir: Path) -> str | None` — SHA-256 over sorted `"<posix relpath>\0<sha256 of bytes>\n"` lines for every file under `<run>/inputs/`; `None` when the directory is absent
  - `def load_run(path: Path) -> RunSnapshot`

Finding records carry no asset field (`finding.schema.json` has none), so "asset" is derived. `asset_keys` returns, per evidence item, `code:<symbol casefolded>` when the locator matches `^code:([^:]+):`, else `artifact:<artifact>` normalised (backslashes to `/`, leading `./` stripped, casefolded); plus `graph:<node name casefolded, whitespace collapsed>` for each name in `graph_targets[record["id"]]`. `load_run` builds `graph_targets` from `40-synthesis/asset-graph.yaml` edges that carry `finding_id` or `capability_id`, mapping that id to the `name` of the edge's `to` node; `headlines` from `40-synthesis/report-data.yaml` `headline_findings[].id` in `rank` order, each expanded through `40-synthesis/deduped-findings.yaml` `merged_from` (a non-merged id expands to itself; `None` when either file is missing). A `yaml.YAMLError` becomes `RunLoadError` naming the file.

- [ ] **Step 1: Write the failing tests**

```python
HA = REPO / "examples/apd-20260612-home-assistant/expected"
CEB = REPO / "examples/apd-20260601-claim-event-bus/expected"

def rec(rid, goal, title, *ev):
    return {"id": rid, "apd_goal": goal, "title": title,
            "evidence": [{"artifact": a, "locator": loc, "excerpt": "x"} for a, loc in ev]}

def test_title_tokens_normalises():
    assert title_tokens("Core .storage (auth) written as PLAINTEXT JSON") == frozenset(
        {"core", "storage", "auth", "written", "as", "plaintext", "json"})

def test_asset_keys_code_artifact_and_graph():
    r = rec("conf-00000001", "confidentiality", "t" * 10,
            ("code-evidence-index.yaml", "code:pkg.Mod.Fn:L1-L9@abc"), ("./inputs/Auth/Login.md", "#login, lines 3-4"))
    assert asset_keys(r, {"conf-00000001": ["Token  Store"]}) == frozenset(
        {"code:pkg.mod.fn", "artifact:inputs/auth/login.md", "graph:token store"})

def test_identical_runs_match_one_to_one():
    s = load_run(HA)
    r = match_records(s.findings, s.findings, baseline_targets=s.graph_targets, candidate_targets=s.graph_targets)
    assert len(r.matched) == 94 and r.missing == () and r.new == ()
    assert all(m.baseline_id == m.candidate_id for m in r.matched)

def test_goal_is_a_hard_key():
    b = {"conf-00000001": rec("conf-00000001", "confidentiality", "Plaintext token store on disk", ("a.md", "#x"))}
    c = {"intg-00000001": rec("intg-00000001", "integrity", "Plaintext token store on disk", ("a.md", "#x"))}
    assert match_records(b, c) == MatchResult((), ("conf-00000001",), ("intg-00000001",))

def test_reworded_title_matches_at_threshold():
    b = {"b": rec("b", "ephemeral", "Refresh tokens never rotate", ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", "Refresh tokens are never rotated", ("a.md", "#y"))}
    (m,) = match_records(b, c).matched
    assert m.title_similarity == pytest.approx(0.6)

def test_disjoint_assets_block_match():
    b = {"b": rec("b", "ephemeral", "Refresh tokens never rotate", ("a.md", "#x"))}
    c = {"c": rec("c", "ephemeral", "Refresh tokens never rotate", ("b.md", "#x"))}
    assert match_records(b, c).matched == ()

def test_load_run_home_assistant():
    s = load_run(HA)
    assert len(s.findings) == 94 and len(s.capabilities) == 28
    assert s.graph_targets["avail-4be2dd70"] == ["recorder_history_db"]
    assert len(s.headlines) == 10 and len(s.headlines[1]) == 8      # merged-1119b0be
    assert s.inputs_sha256 is None                                   # expected/ has no inputs/

def test_inputs_digest_changes_with_content(tmp_path):
    (tmp_path / "inputs").mkdir(); (tmp_path / "inputs/a.md").write_text("x")
    d1 = inputs_digest(tmp_path); (tmp_path / "inputs/a.md").write_text("y")
    assert d1 != inputs_digest(tmp_path) and len(d1) == 64
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_measure_match.py tests/test_measure_runs.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.measure`)

- [ ] **Step 3: Implement `match_records` and `load_run`**

Candidate pairs: same `apd_goal`, non-empty `asset_keys` intersection, title Jaccard ≥ `TITLE_MIN_JACCARD`. Greedy one-to-one over pairs sorted by `(-title_similarity, -asset_similarity, baseline_id != candidate_id, baseline_id, candidate_id)`; ids are unique within a run, so the order is total.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_measure_match.py tests/test_measure_runs.py -v && mypy tools/`
Expected: PASS; mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/measure tests/test_measure_match.py tests/test_measure_runs.py
git commit -m "feat(measure): add deterministic finding matcher and run snapshot"
```

### Task 2: Pairwise delta

**Files:**

- Create: `tools/apd_gauntlet/measure/compare.py`, `tests/conftest.py`
- Test: `tests/test_measure_compare.py`

**Interfaces:**

- Consumes: `RunSnapshot`, `load_run`, `match_records`, `evidence_pairs` (Task 1)
- Produces:
  - `SEVERITY_ORDER = ("informational", "low", "medium", "high", "critical")`; `MATURITY_ORDER = ("designed", "implemented", "tested", "operationalized")`
  - `@dataclass(frozen=True) class LostFinding: id: str; severity: str; title: str; excuse: str | None` (`None`, `"operator"`, or `"evidence_reassigned:<candidate id>"`)
  - `@dataclass(frozen=True) class PairDelta: baseline: Path; candidate: Path; findings: MatchResult; capabilities: MatchResult; missing_by_severity: dict[str, int]; new_by_severity: dict[str, int]; severity_shifts: dict[str, int]; severity_agreement_pct: float | None; lost_critical_high: tuple[LostFinding, ...]; maturity_shifts: dict[str, int]; headline_overlap_pct: float | None`
  - `def compare_pair(baseline: RunSnapshot, candidate: RunSnapshot, *, excused: frozenset[str] = frozenset()) -> PairDelta`
  - `def blocked_rate_pct(run: RunSnapshot) -> float | None` (`None` with zero findings)
  - `def unexcused_lost(delta: PairDelta) -> int`
- `tests/conftest.py` fixtures:
  - `make_run(name: str) -> Path`: copies `examples/apd-20260601-claim-event-bus/expected` to `tmp_path/name` and that example's `inputs/` to `<run>/inputs`
  - `edit`: an object with `.finding(run, rid, **fields)`, `.capability(run, rid, **fields)`, `.drop(run, rid)`, `.add_finding(run, rel_path, record)`; it rewrites the YAML file holding `rid`, accepting `finding:`/`capability:` as a list or a single mapping

Shift keys are `"<from>-><to>"`. `severity_agreement_pct` is `100 × equal-severity pairs / matched`. A lost critical or high finding is excused as `operator` when its id is in `excused`, else as `evidence_reassigned:<id>` when a candidate finding in `findings.new` or capability in `capabilities.new` shares one of its `evidence_pairs` (a pair shared with a record that also exists in the baseline does not excuse). `headline_overlap_pct` is `100 × retained / len(baseline.headlines)`, where a baseline headline is retained when the candidate ids matched to its expanded ids intersect some expanded candidate headline; `None` when either side has no headlines.

- [ ] **Step 1: Write the failing tests**

```python
def test_mutations_are_reported(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "conf-7aa376c5")                                  # high, confidentiality
    edit.finding(c, "avail-ce35b2ed", severity="medium")
    edit.finding(c, "immut-067a7391", disposition="gap")
    edit.capability(c, "conf-cap-d0590471", maturity="tested")
    d = compare_pair(load_run(b), load_run(c))
    assert len(d.findings.matched) == 19 and d.findings.missing == ("conf-7aa376c5",) and d.findings.new == ()
    assert d.missing_by_severity == {"high": 1} and d.new_by_severity == {}
    assert d.severity_shifts == {"high->medium": 1}
    assert d.severity_agreement_pct == pytest.approx(1800 / 19)
    assert d.maturity_shifts == {"implemented->tested": 1}
    assert [(x.id, x.excuse) for x in d.lost_critical_high] == [("conf-7aa376c5", None)]
    assert d.headline_overlap_pct == pytest.approx(600 / 7)
    assert blocked_rate_pct(load_run(b)) == 15.0
    assert blocked_rate_pct(load_run(c)) == pytest.approx(200 / 19)

def test_operator_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c"); edit.drop(c, "conf-7aa376c5")
    d = compare_pair(load_run(b), load_run(c), excused=frozenset({"conf-7aa376c5"}))
    assert d.lost_critical_high[0].excuse == "operator" and unexcused_lost(d) == 0

def test_evidence_reassigned_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c")
    edit.drop(c, "intg-42a3ebbd")                                  # cites threat-model.md / Tampering paragraph 2
    edit.add_finding(c, "10-trustworthiness/confidentiality.findings.yaml", new_finding(
        "conf-0000beef", "Unsigned Kafka payloads allow claim tampering in transit",
        evidence=[("threat-model.md", "Tampering paragraph 2")]))
    d = compare_pair(load_run(b), load_run(c))
    assert d.lost_critical_high[0].excuse == "evidence_reassigned:conf-0000beef"

def test_shared_evidence_with_existing_capability_does_not_excuse(make_run, edit):
    b, c = make_run("b"), make_run("c"); edit.drop(c, "conf-7aa376c5")   # conf-cap-d0590471 cites the same pair in both runs
    assert unexcused_lost(compare_pair(load_run(b), load_run(c))) == 1
```

`new_finding` is a module-level helper in the test file that copies `conf-7aa376c5`'s record and replaces `id`, `title` and `evidence`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_measure_compare.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.measure.compare`)

- [ ] **Step 3: Implement `compare_pair`, `blocked_rate_pct`, `unexcused_lost` and the conftest fixtures**

Capabilities go through the same `match_records`, with `graph_targets` from the snapshot (the asset graph's `capability_id` edges).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_measure_compare.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/measure/compare.py tests/conftest.py tests/test_measure_compare.py
git commit -m "feat(measure): add pairwise run delta with excused losses and headline overlap"
```

### Task 3: Attempts file and `summarize --record-attempts`

**Files:**

- Create: `tools/apd_gauntlet/measure/attempts.py`, `tools/apd_gauntlet/data/schemas/run-attempts.schema.json`
- Modify: `tools/apd_gauntlet/cli.py:353-363` (`summarize`), `tools/apd_gauntlet/measure/runs.py` (`RunSnapshot.attempts`), `docs/schema-evolution.md`, `CHANGELOG.md`
- Test: `tests/test_measure_attempts.py`, `tests/test_summarize.py` (extend)

**Interfaces:**

- Produces:
  - Schema `$id` `https://github.com/illusconsulting/apd-gauntlet/schemas/run-attempts.schema.json`: object, `additionalProperties: false`, all keys required: `schema_version` (const 1), `recorded_by` (enum `workflow`, `runner`, `operator`), `lens_retries` (object of integers ≥ 0), `first_pass_invalid`, `tier_gate_failures`, `skipped` (arrays of unique non-empty strings), `audit_iterations` (integer ≥ 1)
  - `class AttemptsError(Exception)`
  - `@dataclass(frozen=True) class Attempts: recorded_by: str; lens_retries: dict[str, int]; first_pass_invalid: tuple[str, ...]; tier_gate_failures: tuple[str, ...]; skipped: tuple[str, ...]; audit_iterations: int` with properties `first_pass_validator_errors -> int` (`len(first_pass_invalid) + len(tier_gate_failures)`) and `lens_retries_total -> int`
  - `ATTEMPTS_RELPATH = Path(".apd-state/attempts.yaml")`
  - `def write_attempts(run_dir: Path, data: Mapping[str, Any]) -> Path` (validates, creates `.apd-state/`, raises `AttemptsError` listing schema messages)
  - `def read_attempts(run_dir: Path) -> Attempts | None` (`None` when absent; `AttemptsError` when invalid)
  - `RunSnapshot` gains `attempts: Attempts | None = None`; `load_run` maps `AttemptsError` to `RunLoadError`
  - CLI: `summarize RUN_DIR [--json] [--record-attempts JSON]`

In 1.7 runs none of these numbers is persisted: lens retries, first-pass receipts and tier-gate results live only in the workflow's JavaScript (`.claude/workflows/apd-gauntlet.js:442-453`), and `40-synthesis/report-audit.yaml` is overwritten on each audit attempt. This file is their only source; Task 7 makes the workflow write it, and LA2's runner calls `write_attempts` directly.

- [ ] **Step 1: Write the failing tests**

```python
GOOD = {"schema_version": 1, "recorded_by": "workflow", "lens_retries": {"integrity": 1, "availability": 0},
        "first_pass_invalid": ["integrity"], "tier_gate_failures": ["20-scalability"], "skipped": [], "audit_iterations": 2}

def test_round_trip(tmp_path):
    write_attempts(tmp_path, GOOD)
    a = read_attempts(tmp_path)
    assert a.first_pass_validator_errors == 2 and a.lens_retries_total == 1 and a.audit_iterations == 2

def test_absent_is_none(tmp_path):
    assert read_attempts(tmp_path) is None

@pytest.mark.parametrize("bad", [{"lens_retries": {"integrity": -1}}, {"audit_iterations": 0}, {"extra": 1}])
def test_invalid_rejected(tmp_path, bad):
    with pytest.raises(AttemptsError):
        write_attempts(tmp_path, {**GOOD, **bad})
    assert not (tmp_path / ".apd-state/attempts.yaml").exists()

# tests/test_summarize.py
def test_summarize_records_attempts(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", json.dumps(GOOD)])
    assert r.exit_code == 0 and (run / ".apd-state/attempts.yaml").exists() and "Findings:" in r.output

def test_summarize_bad_attempts_json_exits_2(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    assert CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", "{nope"]).exit_code == 2

def test_summarize_invalid_attempts_exits_1(tmp_path):
    run = shutil.copytree(FIXTURES / "clean-run", tmp_path / "run")
    r = CliRunner().invoke(main, ["summarize", str(run), "--record-attempts", json.dumps({**GOOD, "audit_iterations": 0})])
    assert r.exit_code == 1 and not (run / ".apd-state").exists()
```

`tests/test_summarize.py` repeats the `GOOD` mapping and imports `json` and `shutil`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_measure_attempts.py tests/test_summarize.py -v`
Expected: FAIL (module missing; `no such option: --record-attempts`)

- [ ] **Step 3: Implement the schema, `attempts.py` and the option**

Validate with `Draft202012Validator(read_schema("run-attempts.schema.json"), registry=build_registry())`. The option parses with `json.loads` (`click.BadParameter` on error), writes before summarising, and echoes `Recorded attempts -> <path>` to stderr. Schema-evolution gets a `## v2.0.0 — Measurement and evaluation (additive)` section with a dated `### YYYY-MM-DD — run-attempts (new)` entry (commit date). CHANGELOG gains `### Added` above `### Changed` under the 2.0 heading with a bullet for `summarize --record-attempts` and `.apd-state/attempts.yaml`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_measure_attempts.py tests/test_summarize.py tests/test_meta_schemas.py tests/test_schema_vocab_centralized.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/measure tools/apd_gauntlet/data/schemas/run-attempts.schema.json tools/apd_gauntlet/cli.py docs/schema-evolution.md CHANGELOG.md tests/test_measure_attempts.py tests/test_summarize.py
git commit -m "feat(measure): record lens retries, first-pass failures and audit iterations per run"
```

### Task 4: `usage` from OpenTelemetry

**Files:**

- Create: `tools/apd_gauntlet/measure/usage.py`, `tests/fixtures/otel/claude-code-logs.otlp.jsonl`, `tests/fixtures/otel/console-export.txt`, `docs/measuring-changes.md`, `tests/test_measuring_changes_doc.py`
- Modify: `tools/apd_gauntlet/cli.py` (append before `if __name__ == "__main__":`, line 1465), `tools/apd_gauntlet/measure/runs.py` (`RunSnapshot.usage_totals`), `docs/running-the-gauntlet.md` (one line in "Local accuracy benchmark (out-of-band)" linking the runbook), `CHANGELOG.md`
- Test: `tests/test_measure_usage.py`, `tests/test_cli_usage.py`

**Interfaces:**

- Produces:
  - `class UsageParseError(Exception)`
  - `@dataclass(frozen=True) class ApiRequest: agent: str; model: str; input_tokens: int; output_tokens: int; cache_read_tokens: int; cache_creation_tokens: int; cost_usd_micros: int; session_id: str | None; workflow_run_id: str | None`
  - `def iter_api_requests(path: Path) -> Iterator[ApiRequest]` — the only function that knows the file format
  - `AGENT_PHASES: dict[str, str]`; `PSEUDO_PHASES = frozenset({"cli-steps", "session", "unattributed"})`; `REDACTED_AGENTS = frozenset({"custom", "third-party"})`
  - `def phase_for(agent: str) -> str`
  - `def summarize_usage(requests: Iterable[ApiRequest], *, source: Path, workflow_run: str | None = None) -> dict[str, Any]`
  - `USAGE_RELPATH = Path(".apd-state/usage.yaml")`; `def write_usage(run_dir: Path, summary: Mapping[str, Any]) -> Path`
  - `RunSnapshot` gains `usage_totals: dict[str, float] | None = None` (`totals` of `usage.yaml`)
  - CLI: `usage RUN_DIR --otel FILE [--workflow-run ID] [--json]`; exit 0 written, 1 no `api_request` events after filtering (nothing written), 2 `UsageParseError`

The documented attribute names are fixed above; the file format is not documented (the page describes neither the console exporter's output nor the log record body). `iter_api_requests` therefore accepts OTLP/JSON only — the proto3 JSON mapping of `ExportLogsServiceRequest`, one document per line, as the OpenTelemetry Collector `file` exporter writes it (a single pretty-printed document is also accepted). A record counts when attribute `event.name == "api_request"` or `body.stringValue == "claude_code.api_request"`. Attribute values are decoded from `stringValue`, `intValue` (a JSON string or number), `doubleValue` or `boolValue`; token fields coerce with `int()`. Cost is `cost_usd_micros` when present, else `round(cost_usd × 1e6)`, else 0 with a `missing_cost` count. A missing `agent.name` becomes `main`. Record attributes override resource attributes. Lines that parse but hold no `resourceLogs` (metrics or traces in the same file) are skipped; text that is not JSON raises `UsageParseError` naming OTLP/JSON and the runbook.

Telemetry carries no phase attribute, so `phase_for` maps the agent name (any `<plugin>:` prefix stripped) through `AGENT_PHASES`:

| Agent | Phase |
|---|---|
| `apd-intake` | `intake` |
| `apd-code-recon` | `code-recon` |
| `apd-threat-model-author` | `threat-model-author` |
| `apd-threat-model-recon` | `tm-recon` |
| `apd-confidentiality`, `apd-integrity`, `apd-availability` | `tier-1` |
| `apd-distributed`, `apd-resilient`, `apd-ephemeral` | `tier-2` |
| `apd-authenticity`, `apd-non-repudiation`, `apd-immutability` | `tier-3` |
| `apd-cluster-adjudicator` | `synthesis-adjudicate` |
| `apd-synthesizer` | `synthesis-fallback` |
| `apd-threat-model-evaluator` | `tmeval` |
| `apd-attack-path-analyzer` | `apath` |
| `apd-report-writer` | `synthesis-report` |
| `apd-report-auditor` | `synthesis-audit` |
| `apd-domain-auditor` | `domain-improvements` |
| `general-purpose` (every `pyStep` worker) | `cli-steps` |
| `main` | `session` |
| anything else, including `custom` and `third-party` | `unattributed` |

`usage.yaml` keys: `schema_version: 1`, `generated_by: apd-gauntlet usage`, `source: {file, sha256, api_requests, sessions, workflow_runs}`, `filter: {workflow_run}`, `totals`, `by_agent: {<agent>: {phase, requests, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, cost_usd}}`, `by_phase: {<phase>: {…same counters…}}`, `warnings: [str]`. `cost_usd` is `micros / 1e6`.

Fixture `claude-code-logs.otlp.jsonl` (two lines, two export batches; every `api_request` record carries `event.name`, `session.id: s1`):

| # | Event | `agent.name` | tokens in/out/cache-read/cache-creation | cost | `workflow.run_id` |
|---|---|---|---|---|---|
| 1 | `api_request` | `apd-confidentiality` | `intValue` "1000"/"200"/"5000"/"300" | `cost_usd` double 0.5 | `wf_1` |
| 2 | `api_request` | `apd-confidentiality` | `stringValue` "500"/"100"/"0"/"0" | `cost_usd_micros` int "250000" | `wf_1` |
| 3 | `api_request` | `general-purpose` | 100/50/0/0 | `cost_usd` 0.01 | `wf_1` |
| 4 | `api_request` | (absent; `query_source: repl_main_thread`) | 10/5/0/0 | `cost_usd` 0.001 | (absent) |
| 5 | `tool_result` | — | — | — | `wf_1` |
| 6 | `api_request` | `custom` | 7/3/0/0 | `cost_usd` 0.002 | `wf_2` |

Line shape: `{"resourceLogs":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"claude-code"}}]},"scopeLogs":[{"scope":{"name":"com.anthropic.claude_code.events"},"logRecords":[{"timeUnixNano":"1760140800000000000","body":{"stringValue":"claude_code.api_request"},"attributes":[{"key":"event.name","value":{"stringValue":"api_request"}},{"key":"agent.name","value":{"stringValue":"apd-confidentiality"}},{"key":"input_tokens","value":{"intValue":"1000"}}]}]}]}]}`, with the remaining attributes from the table. `console-export.txt` holds three lines of Node `util.inspect` text: an opening `{`, then `body: 'claude_code.api_request',` and `attributes: { 'event.name': 'api_request', input_tokens: 12 } }`, each indented two spaces.

- [ ] **Step 1: Write the failing tests**

```python
OTEL = FIXTURES / "otel/claude-code-logs.otlp.jsonl"

def test_parses_only_api_requests():
    reqs = list(iter_api_requests(OTEL))
    assert [r.agent for r in reqs] == ["apd-confidentiality", "apd-confidentiality", "general-purpose", "main", "custom"]
    assert reqs[1].input_tokens == 500 and reqs[1].cost_usd_micros == 250_000

def test_summary_totals_and_phases():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    assert s["totals"] == {"requests": 5, "input_tokens": 1617, "output_tokens": 358, "cache_read_tokens": 5000,
                           "cache_creation_tokens": 300, "cost_usd": 0.763}
    assert s["by_agent"]["apd-confidentiality"] == {"phase": "tier-1", "requests": 2, "input_tokens": 1500,
        "output_tokens": 300, "cache_read_tokens": 5000, "cache_creation_tokens": 300, "cost_usd": 0.75}
    assert s["by_phase"]["cli-steps"]["cost_usd"] == 0.01 and s["by_agent"]["main"]["phase"] == "session"

def test_redacted_agent_names_warn():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    assert s["by_agent"]["custom"]["phase"] == "unattributed"
    assert any("OTEL_LOG_TOOL_DETAILS=1" in w for w in s["warnings"])
    assert any("wf_1" in w and "wf_2" in w for w in s["warnings"])

def test_workflow_run_filter():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL, workflow_run="wf_1")
    assert s["totals"]["requests"] == 3 and s["totals"]["cost_usd"] == 0.76

def test_plugin_prefix_stripped():
    assert phase_for("apd-gauntlet:apd-report-writer") == "synthesis-report"

def test_agent_phases_cover_agents_and_workflow_phases():
    agents = {p.stem for p in (REPO / ".claude/agents").glob("apd-*.md")} - {"apd-orchestrator"}
    assert agents <= set(AGENT_PHASES)
    m = re.search(r"phases:\s*\[(.*?)\]", WORKFLOW_JS.read_text(), re.DOTALL)
    assert set(AGENT_PHASES.values()) <= set(re.findall(r"'([^']+)'", m.group(1))) | PSEUDO_PHASES

# tests/test_cli_usage.py
def test_usage_writes_state_file(make_run):
    run = make_run("r")
    r = CliRunner().invoke(main, ["usage", str(run), "--otel", str(OTEL)])
    assert r.exit_code == 0 and yaml.safe_load((run / ".apd-state/usage.yaml").read_text())["totals"]["requests"] == 5

def test_console_export_refused(make_run):
    r = CliRunner().invoke(main, ["usage", str(make_run("r")), "--otel", str(FIXTURES / "otel/console-export.txt")])
    assert r.exit_code == 2 and "OTLP/JSON" in r.output

def test_no_events_exits_1(make_run, tmp_path):
    empty = tmp_path / "e.jsonl"; empty.write_text('{"resourceLogs": []}\n')
    run = make_run("r")
    assert CliRunner().invoke(main, ["usage", str(run), "--otel", str(empty)]).exit_code == 1
    assert not (run / ".apd-state/usage.yaml").exists()

# tests/test_measuring_changes_doc.py
def test_runbook_covers_baseline_capture():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("CLAUDE_CODE_ENABLE_TELEMETRY=1", "OTEL_LOGS_EXPORTER=otlp", "OTEL_EXPORTER_OTLP_PROTOCOL=http/json",
              "OTEL_LOG_TOOL_DETAILS=1", "2.1.273", "-baseline-r1", "-baseline-r2", "apd-gauntlet usage"):
        assert s in t
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_measure_usage.py tests/test_cli_usage.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (module, command and runbook missing)

- [ ] **Step 3: Implement `usage.py`, the command, fixtures and the runbook's first sections**

Warnings: `"agent names redacted on N requests ('custom'/'third-party'): set OTEL_LOG_TOOL_DETAILS=1 and use Claude Code 2.1.273 or later"`; `"multiple workflow runs in this file (wf_1, wf_2): pass --workflow-run"`; `"N requests carried no cost attribute"`. Runbook `docs/measuring-changes.md` sections written now: "Why measure" (the audit's before-and-after rule, ADR-0017's split); "Capture a baseline" (master plan Task 1 steps, the run naming, two runs per configuration, `apd-gauntlet validate` per run); "Telemetry" (the three master-plan variables plus `OTEL_EXPORTER_OTLP_PROTOCOL=http/json` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318`, because the docs say Claude Code has no default protocol; a minimal Collector config with an `otlp` HTTP receiver and a `file` exporter writing `telemetry/<run-id>.otlp.jsonl`; real agent names on `api_request` need Claude Code 2.1.273 or later; the console exporter is not parsed); "Usage" (command, output keys, the agent-to-phase table, warnings). CHANGELOG bullet for `usage`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_measure_usage.py tests/test_cli_usage.py tests/test_measuring_changes_doc.py -v && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/measure tools/apd_gauntlet/cli.py tests/fixtures/otel tests/test_measure_usage.py tests/test_cli_usage.py tests/test_measuring_changes_doc.py docs/measuring-changes.md docs/running-the-gauntlet.md CHANGELOG.md
git commit -m "feat(measure): add usage command summarising OpenTelemetry api_request events"
```

### Task 5: Gates file and gate evaluation

**Files:**

- Create: `eval/gates.yaml`, `tools/apd_gauntlet/measure/gates.py`
- Test: `tests/test_measure_gates.py`

**Interfaces:**

- Produces:
  - `METRICS = frozenset({"unexcused_lost_critical_high", "severity_agreement_pct", "blocked_rate_abs_delta_pts", "first_pass_validator_errors_delta", "lens_retries_delta", "audit_iterations_delta"})`
  - `@dataclass(frozen=True) class Check: metric: str; op: Literal["le", "ge"]; value: float`
  - `@dataclass(frozen=True) class Gate: id: str; text: str; checks: tuple[Check, ...]`
  - `class GatesError(Exception)`
  - `def load_gates(path: Path) -> tuple[Gate, ...]` (unknown metric, unknown op, duplicate id, or missing key → `GatesError` naming it)
  - `@dataclass(frozen=True) class GateOutcome: gate: Gate; status: Literal["pass", "fail", "not_available"]; values: dict[str, float | None]; reason: str | None`
  - `def evaluate(gates: Sequence[Gate], values: Mapping[str, float | None], reasons: Mapping[str, str]) -> list[GateOutcome]` — `fail` when any check with a value fails; else `not_available` when any value is `None` (reason copied from `reasons[metric]`); else `pass`
  - `def overall(outcomes: Sequence[GateOutcome]) -> Literal["pass", "pass_with_gaps", "fail"]`

`eval/gates.yaml`:

```yaml
# Comparison gates: proposals from the program master plan's Global Constraints.
# Change a threshold only by PR, with the rationale in the PR description.
schema_version: 1
status: proposal
gates:
  - id: no_lost_critical_high
    text: no critical or high finding lost unless the loss traces to evidence
    checks: [{metric: unexcused_lost_critical_high, op: le, value: 0}]
  - id: severity_agreement
    text: severity agrees on at least 90% of matched findings
    checks: [{metric: severity_agreement_pct, op: ge, value: 90}]
  - id: blocked_rate
    text: blocked rate moves by no more than 5 points
    checks: [{metric: blocked_rate_abs_delta_pts, op: le, value: 5}]
  - id: first_pass_and_retries
    text: first-pass schema validity and retry count no worse than baseline
    checks: [{metric: first_pass_validator_errors_delta, op: le, value: 0}, {metric: lens_retries_delta, op: le, value: 0}]
  - id: audit_iterations
    text: report audit passes in no more iterations than baseline
    checks: [{metric: audit_iterations_delta, op: le, value: 0}]
```

- [ ] **Step 1: Write the failing tests**

```python
def test_gate_texts_match_master_plan_verbatim():
    plan = (REPO / "docs/superpowers/plans/2026-10-10-program-master-plan.md").read_text()
    block = plan.split("These comparison gates are proposals, recorded in `eval/gates.yaml`:")[1].split("- **Ids")[0]
    bullets = [b.strip().rstrip(";.") for b in re.findall(r"^  - (.+)$", block, re.MULTILINE)]
    assert [g.text for g in load_gates(REPO / "eval/gates.yaml")] == bullets

def test_evaluate_statuses():
    gates = load_gates(REPO / "eval/gates.yaml")
    vals = {"unexcused_lost_critical_high": 0, "severity_agreement_pct": 89.9, "blocked_rate_abs_delta_pts": 5.0,
            "first_pass_validator_errors_delta": None, "lens_retries_delta": None, "audit_iterations_delta": None}
    out = evaluate(gates, vals, {"audit_iterations_delta": "no attempts file"})
    assert [o.status for o in out] == ["pass", "fail", "pass", "not_available", "not_available"]
    assert out[4].reason == "no attempts file" and overall(out) == "fail"
    assert overall([o for o in out if o.status != "fail"]) == "pass_with_gaps"

def test_unknown_metric_rejected(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text("schema_version: 1\ngates: [{id: x, text: x, checks: [{metric: nope, op: le, value: 0}]}]\n")
    with pytest.raises(GatesError, match="nope"):
        load_gates(p)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_measure_gates.py -v`
Expected: FAIL (module and `eval/gates.yaml` missing)

- [ ] **Step 3: Implement `gates.py` and write `eval/gates.yaml`**

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_measure_gates.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add eval/gates.yaml tools/apd_gauntlet/measure/gates.py tests/test_measure_gates.py
git commit -m "feat(measure): add proposal comparison gates and evaluator"
```

### Task 6: `compare-runs` command

**Files:**

- Modify: `tools/apd_gauntlet/measure/compare.py`, `tools/apd_gauntlet/cli.py` (append), `docs/measuring-changes.md`, `CHANGELOG.md`, `tests/test_measuring_changes_doc.py`
- Test: `tests/test_cli_compare_runs.py`

**Interfaces:**

- Consumes: `compare_pair`, `blocked_rate_pct`, `unexcused_lost` (Task 2); `Attempts` (Task 3); `usage_totals` (Task 4); `load_gates`, `evaluate`, `overall` (Task 5)
- Produces:
  - `class MissingRuns(Exception)`
  - `def resolve_side(path: Path) -> list[Path]` — `[path]` when `is_run_dir(path)`; else `<path>-r1`, `<path>-r2`, … while each exists as a run dir (at least one); else `MissingRuns`
  - `@dataclass(frozen=True) class Comparison: baseline: tuple[RunSnapshot, ...]; candidate: tuple[RunSnapshot, ...]; pairs: tuple[PairDelta, ...]; per_run: dict[str, dict[str, float | None]]; values: dict[str, float | None]; reasons: dict[str, str]; warnings: tuple[str, ...]`
  - `def compare_sides(baseline: Sequence[RunSnapshot], candidate: Sequence[RunSnapshot], *, excused: frozenset[str] = frozenset()) -> Comparison`
  - `def comparison_json(c: Comparison, outcomes: Sequence[GateOutcome] | None, status: str) -> dict[str, Any]` (top-level keys `status`, `baseline`, `candidate`, `pairs`, `runs` (keyed by the run path as `resolve_side` returned it, not `Path.resolve()`; the same-directory check alone uses `resolve()`), `values`, `gates`, `warnings`)
  - `def render_text(c: Comparison, outcomes: Sequence[GateOutcome] | None, status: str) -> str`
  - CLI: `compare-runs BASELINE CANDIDATE [--json] [--gates PATH] [--excuse ID]... [--strict]`

Values: pairwise metrics (`unexcused_lost_critical_high`, `severity_agreement_pct`) are `statistics.median` over all |B|×|C| pairs (pairs with `None` dropped; all `None` → `None`). Per-run metrics (`blocked_rate_pct`, `first_pass_validator_errors`, `lens_retries_total`, `audit_iterations`, usage `cost_usd`) take the median per side; `blocked_rate_abs_delta_pts = |med_c − med_b|`; the three attempts deltas are `med_c − med_b`, `None` when any run on either side has `attempts is None` (reason `"no .apd-state/attempts.yaml in <run> (1.7 runs and foreground drives record none)"`) or a non-empty `attempts.skipped` (reason `"<run> resumed: N steps skipped, retries under-counted"`). Usage cost is reported, never gated.

Exit codes: 2 when the baseline does not resolve (message names `-r1`/`-r2` and `docs/measuring-changes.md`), the candidate does not resolve, both sides share a directory, a baseline run has zero findings, two runs carry different non-`None` `inputs_sha256`, a run fails to load, or `--gates` is unreadable. With `--gates`: 1 when `overall` is `fail`, or `pass_with_gaps` under `--strict`; else 0. Without `--gates`: status `delta_only`, exit 0. One run on a side with `--gates` adds the warning "gates applied to a single run per side; run each configuration twice".

- [ ] **Step 1: Write the failing tests**

```python
GATES = str(REPO / "eval/gates.yaml")
def cr(*args): return CliRunner().invoke(main, ["compare-runs", *map(str, args)])

def test_missing_baseline_exits_2(make_run, tmp_path):
    r = cr(tmp_path / "nope", make_run("c"), "--gates", GATES)
    assert r.exit_code == 2 and "baseline not found" in r.output and "-r1" in r.output

def test_same_run_exits_2(make_run):
    run = make_run("b"); assert cr(run, run).exit_code == 2

def test_scaffold_baseline_exits_2(make_run, tmp_path):
    s = tmp_path / "scaffold"; s.mkdir(); (s / ".apd-run.yaml").write_text("run_id: scaffold\n")
    r = cr(s, make_run("c")); assert r.exit_code == 2 and "no findings" in r.output

def test_different_inputs_exit_2(make_run):
    b, c = make_run("b"), make_run("c"); (c / "inputs/extra.md").write_text("x")
    r = cr(b, c); assert r.exit_code == 2 and "different inputs" in r.output

def test_identical_runs_pass_with_gaps(make_run):
    r = cr(make_run("b"), make_run("c"), "--gates", GATES, "--json")
    out = json.loads(r.stdout)
    assert r.exit_code == 0 and out["status"] == "pass_with_gaps"
    assert [g["status"] for g in out["gates"]] == ["pass", "pass", "pass", "not_available", "not_available"]

def test_attempt_gates_not_available_on_1_7_runs(make_run):
    out = json.loads(cr(make_run("b"), make_run("c"), "--gates", GATES, "--json").stdout)
    assert "attempts.yaml" in out["gates"][3]["reason"]

def test_strict_fails_on_gaps(make_run):
    assert cr(make_run("b"), make_run("c"), "--gates", GATES, "--strict").exit_code == 1

def test_lost_high_fails_and_excuse_passes(make_run, edit):
    b, c = make_run("b"), make_run("c"); edit.drop(c, "conf-7aa376c5")
    assert cr(b, c, "--gates", GATES).exit_code == 1
    assert cr(b, c, "--gates", GATES, "--excuse", "conf-7aa376c5").exit_code == 0

def test_pair_convention_and_medians(make_run, edit, tmp_path):
    for n in ("x-base-r1", "x-base-r2", "x-cand-r1", "x-cand-r2"): make_run(n)
    edit.drop(tmp_path / "x-cand-r1", "conf-7aa376c5")
    out = json.loads(cr(tmp_path / "x-base", tmp_path / "x-cand", "--gates", GATES, "--json").stdout)
    assert len(out["baseline"]) == 2 and len(out["pairs"]) == 4
    assert out["values"]["unexcused_lost_critical_high"] == 0.5 and out["gates"][0]["status"] == "fail"

def test_attempt_medians(make_run, tmp_path):
    runs = {n: make_run(n) for n in ("y-base-r1", "y-base-r2", "y-cand-r1", "y-cand-r2")}
    for n, k in {"y-base-r1": 1, "y-base-r2": 1, "y-cand-r1": 0, "y-cand-r2": 2}.items():
        write_attempts(runs[n], {**GOOD_ATTEMPTS, "lens_retries": {"integrity": k}})
    out = json.loads(cr(tmp_path / "y-base", tmp_path / "y-cand", "--gates", GATES, "--json").stdout)
    assert out["values"]["lens_retries_delta"] == 0 and out["gates"][3]["status"] == "pass"

def test_resumed_run_attempts_not_available(make_run):
    b, c = make_run("b"), make_run("c")
    write_attempts(b, GOOD_ATTEMPTS); write_attempts(c, {**GOOD_ATTEMPTS, "skipped": ["integrity"]})
    out = json.loads(cr(b, c, "--gates", GATES, "--json").stdout)
    assert out["gates"][3]["status"] == "not_available" and "resumed" in out["gates"][3]["reason"]

def test_usage_cost_reported(make_run):
    b, c = make_run("b"), make_run("c")
    for run, cost in ((b, 2.0), (c, 1.5)):
        write_usage(run, {"schema_version": 1, "totals": {"requests": 1, "cost_usd": cost}})
    out = json.loads(cr(b, c, "--json").stdout)
    assert out["status"] == "delta_only" and out["runs"][str(c)]["cost_usd"] == 1.5
```

`GOOD_ATTEMPTS` is the Task 3 `GOOD` mapping with `first_pass_invalid`/`tier_gate_failures` empty. Add to `tests/test_measuring_changes_doc.py`: `test_runbook_covers_compare_runs` asserting `compare-runs`, `--gates eval/gates.yaml`, `pass_with_gaps`, `--strict`, `--excuse` and `not_available` appear.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (`No such command 'compare-runs'`)

- [ ] **Step 3: Implement side resolution, `compare_sides`, rendering and the command**

The text report prints the resolved runs, one summary line per pair (matched, missing and new by severity, severity shifts, maturity shifts, headline overlap), each lost critical or high finding with its excuse, the gate table with `PASS`, `FAIL` or `NOT AVAILABLE` and the reason, and a last line `RESULT: <status>` that lists the unavailable gates by id. Runbook section "Compare runs": arguments and the `-r1`/`-r2` convention, how findings are matched (goal, derived asset keys, title Jaccard ≥ 0.5), the excuse rules, the median rule, the exit codes, and that gates 4 and 5 read `not_available` against 1.7 baselines. CHANGELOG bullet for `compare-runs`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py -v && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/measure/compare.py tools/apd_gauntlet/cli.py tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py docs/measuring-changes.md CHANGELOG.md
git commit -m "feat(cli): add compare-runs with run pairs, medians and proposal gates"
```

### Task 7: The workflow records attempts

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js:242` (helpers), `:425-475` (`runTier`), `:736` (audit loop), `:844-846` (closeout `summarize`); `docs/measuring-changes.md`, `CHANGELOG.md`
- Test: `tests/test_workflow_apd_gauntlet.py` (extend), `tests/test_measuring_changes_doc.py` (extend)

**Interfaces:**

- Consumes: `summarize --record-attempts` (Task 3); `run-attempts.schema.json`
- Produces: every completed workflow run writes `runs/<id>/.apd-state/attempts.yaml` with `recorded_by: workflow`. No phase or CLI step is added or renamed: `plan_run.py` and the parity test are unchanged (run the parity test anyway). Foreground drives (`plan-run`) record no attempts.

JavaScript (exact copy; the static tests pin these strings):

```js
// Attempt counters for compare-runs gates 4-5 (run-attempts.schema.json),
// written by the closeout summarize step. Counts reflect this invocation only.
const attempts = {
  schema_version: 1, recorded_by: 'workflow',
  lens_retries: {}, first_pass_invalid: [], tier_gate_failures: [], skipped: [],
  audit_iterations: 0,
};
function isSkip(r) {
  return !!r && (r.outputs || []).some(function (o) { return /\.skipped$/.test(o.path); });
}
```

In `runTier`'s `forEach`: `if (isSkip(r)) attempts.skipped.push(lens);`, then `if (isErr(r) || r.outputs.some(function (o) { return !o.schema_valid; })) attempts.first_pass_invalid.push(lens);`, a `let retries = 0;` set to `k` inside the retry loop, and `attempts.lens_retries[lens] = retries;` after it. The tier gate becomes `const gate = pyStep('validate', {…unchanged…}); if (isErr(gate)) attempts.tier_gate_failures.push(tierDir);`. The audit loop's first statement is `attempts.audit_iterations = i + 1;`. Closeout:

```js
pyStep('summarize', { phase: 'closeout', label: 'summarize', alwaysRun: true,
  cliArgs: "--record-attempts '" + JSON.stringify(attempts) + "'",
  outputs: runDir + '/.apd-state/attempts.yaml' });
```

`alwaysRun` matters: the idempotency guard would otherwise skip `summarize`, whose old output was not a file, and the attempts would never be written.

- [ ] **Step 1: Write the failing tests**

```python
def test_attempts_object_matches_schema_keys():
    text = RUNNER.read_text()
    body = re.search(r"const attempts = \{(.*?)\};", text, re.DOTALL).group(1)
    schema = json.loads((REPO / "schemas/run-attempts.schema.json").read_text())
    assert set(re.findall(r"(\w+):", body)) == set(schema["properties"])

def test_attempts_counted_in_tiers_and_audit():
    text = RUNNER.read_text()
    tier = text[text.index("function runTier"):text.index("runTier('tier-1'")]
    for s in ("attempts.skipped.push(lens)", "attempts.first_pass_invalid.push(lens)",
              "attempts.lens_retries[lens] = retries", "attempts.tier_gate_failures.push(tierDir)"):
        assert s in tier
    assert "attempts.audit_iterations = i + 1;" in text

def test_closeout_summarize_records_attempts_and_always_runs():
    text = RUNNER.read_text()
    step = text[text.index("pyStep('summarize'"):]
    step = step[:step.index("});")]
    assert "--record-attempts" in step and "alwaysRun: true" in step and "attempts.yaml" in step
```

Add `test_runbook_covers_attempts` asserting `.apd-state/attempts.yaml`, `--record-attempts` and `plan-run` appear in the runbook.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL on the four new tests

- [ ] **Step 3: Edit the workflow and the runbook**

Runbook section "Retries and audit iterations": what the file records, that counts cover one workflow invocation, that a cross-session resume marks `skipped` and makes gates 4–5 unavailable, and that `plan-run` drives record nothing. CHANGELOG bullet: the workflow writes `.apd-state/attempts.yaml` at closeout.

- [ ] **Step 4: Run the workflow, parity and compare tests**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py tests/test_cli_compare_runs.py tests/test_measuring_changes_doc.py -v`
Expected: PASS (including `test_plan_run_phase_names_consistent_with_workflow`)

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tests/test_workflow_apd_gauntlet.py tests/test_measuring_changes_doc.py docs/measuring-changes.md CHANGELOG.md
git commit -m "feat(workflow): record lens retries, first-pass failures and audit iterations at closeout"
```

- [ ] **Step 6 (operator): Measure the change**

Run the master plan Task 1 set twice on this commit (names ending `-wf-r1`, `-wf-r2`), then for each example `apd-gauntlet compare-runs runs/<example>-baseline runs/<example>-wf --gates eval/gates.yaml`.
Expected: exit 0 (`pass_with_gaps`: gates 4–5 unavailable against the 1.7.0 baseline), and every `-wf` run has `.apd-state/attempts.yaml`.

### Task 8: Evaluation schemas, corpus loader and evaluator registry

**Files:**

- Create: `tools/apd_gauntlet/data/schemas/eval-corpus.schema.json`, `tools/apd_gauntlet/data/schemas/eval-labels.schema.json`, `tools/apd_gauntlet/eval/__init__.py`, `tools/apd_gauntlet/eval/corpus.py`, `tools/apd_gauntlet/eval/evaluators.py`
- Modify: `docs/schema-evolution.md`
- Test: `tests/test_eval_corpus.py`, `tests/test_eval_evaluators.py`, `tests/test_eval_committed_corpora.py`

**Interfaces:**

- Produces (schemas, `$id` under `https://github.com/illusconsulting/apd-gauntlet/schemas/`):
  - `eval-corpus`: `{schema_version: 1, name: ^[a-z0-9][a-z0-9-]*$, description?, entries: [{id: ^[a-z0-9][a-z0-9-]*$, set: dev|heldout, run?: str, repo?: {url, commit: ^[0-9a-f]{40}$, path?}, labels: str, licence?: str}]}`, each entry `anyOf` `run` or `repo`; `additionalProperties: false` throughout
  - `eval-labels`, discriminated by `kind` through `allOf` of `if`/`then` blocks (not `oneOf`, so a bad item reports its own JSON path):
    - `findings`: `{schema_version: 1, kind: findings, entry: str, items: [{id?, verdict: true_positive|false_positive|unreviewed, apd_goal: $ref apd_goal, severity: $ref severity, title: str, evidence: [{artifact, locator, excerpt?}] (minItems 1), note?}]}`
    - `decisions`: `{schema_version: 1, kind: decisions, set: dev|heldout, task: ^[a-z][a-z0-9-]*(\.[a-z][a-z0-9_]*)?$, records: [{path: str, items: [{ref: str, gold: bool}] (minItems 1)}] (minItems 1)}`
- Produces (`corpus.py`):
  - `class CorpusError(Exception)`
  - `@dataclass(frozen=True) class RepoPin: url: str; commit: str; path: str | None`
  - `@dataclass(frozen=True) class CorpusEntry: id: str; set: Literal["dev", "heldout"]; run_dir: Path | None; repo: RepoPin | None; labels_path: Path`
  - `@dataclass(frozen=True) class Corpus: name: str; path: Path; sha256: str; entries: tuple[CorpusEntry, ...]` with `def select(self, set_name: str) -> tuple[CorpusEntry, ...]`
  - `@dataclass(frozen=True) class Labels: kind: Literal["findings", "decisions"]; path: Path; sha256: str; data: dict[str, Any]`
  - `def load_corpus_manifest(path: Path) -> Corpus` — schema, unique ids, and disjoint sets: the same resolved `run` path or the same `(repo.url, repo.commit)` in both sets raises `CorpusError` naming both entry ids (GRAML's cross-dataset deduplication). `run` and `labels` resolve relative to the manifest's directory.
  - `def load_labels(path: Path) -> Labels` (schema errors → `CorpusError` with the JSON path)
- Produces (`evaluators.py`, R2):
  - `@dataclass(frozen=True) class EvalResult: entry_id: str; counts: dict[str, int]; metrics: dict[str, float | None]; notes: tuple[str, ...] = (); derive: Callable[[Mapping[str, int]], dict[str, float | None]] | None = field(default=None, compare=False, repr=False)`
  - `Evaluator = Callable[[CorpusEntry, Labels], EvalResult]`; `EVALUATORS: dict[str, Evaluator]`
  - `def register(name: str, fn: Evaluator) -> None` (`ValueError` on a duplicate name)
  - `def get(name: str) -> Evaluator` (`KeyError` whose message lists registered names)
  - `def load_builtin_evaluators() -> None` (imports `apd_gauntlet.eval.findings_eval` once Task 9 exists; a no-op list until then)

- [ ] **Step 1: Write the failing tests**

```python
def manifest(tmp_path, entries):
    p = tmp_path / "corpus.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1, "name": "t", "entries": entries})); return p

def test_valid_manifest_resolves_paths(tmp_path):
    c = load_corpus_manifest(manifest(tmp_path, [
        {"id": "a", "set": "dev", "run": "runs/a", "labels": "labels/a.yaml"},
        {"id": "b", "set": "heldout", "repo": {"url": "https://example.org/r.git", "commit": "a" * 40}, "labels": "labels/b.yaml"}]))
    assert c.select("dev")[0].run_dir == tmp_path / "runs/a" and c.select("heldout")[0].repo.commit == "a" * 40
    assert len(c.sha256) == 64

def test_same_run_in_both_sets_rejected(tmp_path):
    with pytest.raises(CorpusError, match="'a'.*'b'"):
        load_corpus_manifest(manifest(tmp_path, [
            {"id": "a", "set": "dev", "run": "runs/x", "labels": "l.yaml"},
            {"id": "b", "set": "heldout", "run": "./runs/x", "labels": "l.yaml"}]))

def test_duplicate_id_rejected(tmp_path): ...            # two entries id "a" → CorpusError "duplicate"
def test_short_commit_rejected(tmp_path): ...            # commit "abc" → CorpusError
def test_entry_needs_run_or_repo(tmp_path): ...          # neither → CorpusError

def test_findings_labels_use_shared_vocab(tmp_path):
    p = tmp_path / "l.yaml"
    p.write_text(yaml.safe_dump({"schema_version": 1, "kind": "findings", "entry": "a", "items": [
        {"verdict": "true_positive", "apd_goal": "confidentiality", "severity": "info", "title": "t" * 10,
         "evidence": [{"artifact": "a.md", "locator": "#x"}]}]}))
    with pytest.raises(CorpusError, match="severity"):
        load_labels(p)                                    # "info" is the display token, not data

def test_register_get_and_duplicates():
    fn = lambda e, l: EvalResult(e.id, {}, {})
    register("t-eval", fn)
    try:
        assert get("t-eval") is fn
        with pytest.raises(ValueError): register("t-eval", fn)
        with pytest.raises(KeyError, match="t-eval"): get("missing")
    finally:
        EVALUATORS.pop("t-eval")

# tests/test_eval_committed_corpora.py
@pytest.mark.parametrize("path", sorted((REPO / "eval").glob("*/corpus.yaml")), ids=str)
def test_committed_corpus_and_labels_valid(path):
    c = load_corpus_manifest(path)
    for e in c.entries:
        items = load_labels(e.labels_path).data.get("items", [])
        assert all(i.get("verdict") != "unreviewed" for i in items)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eval_corpus.py tests/test_eval_evaluators.py tests/test_eval_committed_corpora.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.eval`); the committed-corpora test reports an empty parameter set (skipped) until Task 14

- [ ] **Step 3: Implement the schemas, `corpus.py` and `evaluators.py`**

Schema-evolution: a dated `eval-corpus, eval-labels (new)` entry under the v2.0.0 section.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eval_corpus.py tests/test_eval_evaluators.py tests/test_eval_committed_corpora.py tests/test_meta_schemas.py tests/test_schema_vocab_centralized.py -v`
Expected: PASS (committed-corpora skipped)

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas/eval-*.schema.json tools/apd_gauntlet/eval docs/schema-evolution.md tests/test_eval_corpus.py tests/test_eval_evaluators.py tests/test_eval_committed_corpora.py
git commit -m "feat(eval): add eval-corpus and eval-labels schemas and the evaluator registry"
```

### Task 9: Findings evaluator and label template

**Files:**

- Create: `tools/apd_gauntlet/eval/findings_eval.py`
- Modify: `tools/apd_gauntlet/eval/evaluators.py` (`load_builtin_evaluators`), `tools/apd_gauntlet/cli.py` (append the `eval` group and `eval label-template`), `CHANGELOG.md`
- Test: `tests/test_eval_findings.py`

**Interfaces:**

- Consumes: `load_run`, `match_records` (Task 1); `CorpusEntry`, `Labels`, `register`, `EvalResult` (Task 8)
- Produces:
  - `GOALS: tuple[str, ...]` — the nine `apd_goal` values in `_defs.schema.json` order
  - `def evaluate_findings(entry: CorpusEntry, labels: Labels) -> EvalResult`, registered as `findings`
  - `def metrics_from_counts(counts: Mapping[str, int]) -> dict[str, float | None]`
  - `def label_template(run_dir: Path, entry_id: str) -> dict[str, Any]`
  - CLI: `eval label-template RUN_DIR --entry ID --out FILE` (exit 1 if `FILE` exists)

Scoring: gold = items with `verdict: true_positive` (their labelled goal and severity), keyed by the item's `id` when present, else `label-<index>`, so a label copied from a finding prefers that same finding on ties. Pass 1 matches gold → run findings (`match_records(gold, run.findings, candidate_targets=run.graph_targets)`): matched pairs are TP (counted under the gold goal, which equals the run goal), unmatched gold are FN. Pass 2 matches `false_positive` items → the run findings left over: matched run findings are FP; the rest are `unjudged`. Counts keys: `tp.<goal>`, `fp.<goal>`, `fn.<goal>`, `unjudged.<goal>` for every goal, and `severity_agree` (TP pairs whose run severity equals the gold severity). `metrics_from_counts` returns, for each goal and for `all`: `precision.<g>` = TP/(TP+FP), `precision_strict.<g>` = TP/(TP+FP+unjudged), `recall.<g>` = TP/(TP+FN), `f1.<g>` from `precision` and `recall` (`None` on a zero denominator), and `severity_agreement` = `severity_agree`/TP(all). `evaluate_findings` raises `ValueError` for an entry with no `run_dir`, labels of another kind, or any `unreviewed` item (message gives the count). `label_template` emits one item per finding from `load_run` (id, `apd_goal`, `severity`, title, evidence `artifact`/`locator`), `verdict: unreviewed`.

- [ ] **Step 1: Write the failing tests**

```python
def labelled(make_run, tmp_path, **overrides):
    run = make_run("r")
    data = label_template(run, "ceb")
    for it in data["items"]:
        it["verdict"] = "true_positive"; it.update(overrides.get(it["id"], {}))
    p = tmp_path / "labels.yaml"; p.write_text(yaml.safe_dump(data))
    return CorpusEntry("ceb", "dev", run, None, p), load_labels(p)

def test_template_lists_every_finding_unreviewed(make_run):
    data = label_template(make_run("r"), "ceb")
    assert len(data["items"]) == 20 and {i["verdict"] for i in data["items"]} == {"unreviewed"}

def test_perfect_labels(make_run, tmp_path):
    m = evaluate_findings(*labelled(make_run, tmp_path)).metrics
    assert m["precision.all"] == m["recall.all"] == m["f1.all"] == m["severity_agreement"] == 1.0

def test_false_positive_label(make_run, tmp_path):
    m = evaluate_findings(*labelled(make_run, tmp_path, **{"conf-98a543cd": {"verdict": "false_positive"}})).metrics
    assert m["precision.confidentiality"] == 0.75 and m["recall.confidentiality"] == 1.0

def test_severity_disagreement(make_run, tmp_path):
    m = evaluate_findings(*labelled(make_run, tmp_path, **{"avail-ce35b2ed": {"severity": "medium"}})).metrics
    assert m["severity_agreement"] == 0.95

def test_unjudged_finding(make_run, tmp_path):
    entry, labels = labelled(make_run, tmp_path)
    labels.data["items"] = [i for i in labels.data["items"] if i["id"] != "dist-d697bb34"]
    m = evaluate_findings(entry, labels).metrics
    assert m["precision.distributed"] is None and m["precision_strict.distributed"] == 0.0
    assert m["precision.all"] == 1.0 and m["precision_strict.all"] == 0.95

def test_unreviewed_refused(make_run, tmp_path):
    run = make_run("r"); p = tmp_path / "l.yaml"; p.write_text(yaml.safe_dump(label_template(run, "ceb")))
    with pytest.raises(ValueError, match="20 unreviewed"):
        evaluate_findings(CorpusEntry("ceb", "dev", run, None, p), load_labels(p))

def test_cli_label_template(make_run, tmp_path):
    out = tmp_path / "l.yaml"
    args = ["eval", "label-template", str(make_run("r")), "--entry", "ceb", "--out", str(out)]
    assert CliRunner().invoke(main, args).exit_code == 0 and load_labels(out).kind == "findings"
    assert CliRunner().invoke(main, args).exit_code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eval_findings.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Implement the evaluator, its registration and the CLI group**

CHANGELOG bullet for the `findings` evaluator and `eval label-template`.

`load_builtin_evaluators` imports `apd_gauntlet.eval.findings_eval`; registration happens at import, guarded so a second import does not raise.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eval_findings.py tests/test_eval_evaluators.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/eval tools/apd_gauntlet/cli.py CHANGELOG.md tests/test_eval_findings.py
git commit -m "feat(eval): add findings evaluator and label template"
```

### Task 10: Freeze protocol

**Files:**

- Create: `tools/apd_gauntlet/eval/freeze.py`, `docs/adrs/0028-committed-calibration-and-frozen-evaluation.md`
- Modify: `tools/apd_gauntlet/cli.py` (`eval freeze`), `CHANGELOG.md`, `docs/adrs/0017-local-only-accuracy-benchmark.md` (metadata line `**Amended by:** [ADR-0028](0028-committed-calibration-and-frozen-evaluation.md)`), `docs/ci-gate-model.md` ("What is measured locally" gets the ADR-0028 exception)
- Test: `tests/test_eval_freeze.py`, `tests/test_adr_0028.py`

**Interfaces:**

- Produces:
  - `TUNABLE_GLOBS: tuple[str, ...] = ("tools/apd_gauntlet/data/decide/thresholds.yaml", "tools/apd_gauntlet/data/*/context-params.yaml")` (thresholds per R8; `ContextParams` files per R2, `data/<domain>/context-params.yaml`)
  - `FROZEN_RELPATH = Path("eval/frozen.yaml")`; `RESULTS_RELPATH = Path("eval/results")`
  - `class FreezeError(Exception)`
  - `def tunables(root: Path) -> dict[str, str]` (posix relpath → SHA-256, sorted)
  - `def tunables_sha256(files: Mapping[str, str]) -> str` (SHA-256 over sorted `"<path>\0<sha>\n"` lines)
  - `def check_frozen(root: Path) -> str` — returns the frozen hash or raises `FreezeError`
  - `def heldout_uses(results_dir: Path, sha: str) -> list[Path]` — `**/heldout-*.yaml` whose `frozen_sha256` equals `sha`
  - `def freeze(root: Path, *, new_heldout_set: bool = False) -> Path`
  - CLI: `eval freeze [--root DIR] [--new-heldout-set]`; exit 0 written or unchanged, 1 `FreezeError`
- `eval/frozen.yaml`: `{schema_version: 1, frozen_at: <UTC ISO 8601>, generation: int, tunables_sha256: str, files: {path: sha}}`

"Older than the tunables files" is decided by content, not modification time: a git checkout resets mtimes, so an mtime rule would refuse or accept at random. `check_frozen` raises `"eval/frozen.yaml not found — tune on dev, then run 'apd-gauntlet eval freeze'"` when missing, and `"tunables changed since freeze: <added|removed|changed> <path>, …"` on any difference. `freeze` writes nothing when the hash is unchanged; on a changed hash it refuses with `"tunables frozen as <sha8> were used on held-out data (<file>); changing them needs a new held-out set (IaC spec §13.2) — pass --new-heldout-set once you have one"` when `heldout_uses` finds a result, and with the flag writes `generation + 1`; otherwise it rewrites with the same generation. An empty tunable set is valid (thresholds may not exist yet).

ADR-0028 (Context, Decision, Consequences, Alternatives considered; ≥ 3,000 bytes) records:

- what is committed: `eval/gates.yaml`; corpus manifests and labels that reference only committed fixtures or public repositories pinned by SHA; `eval/frozen.yaml`; `thresholds.yaml` entries (threshold, precision, recall, `n`, `labels_sha256`). This is a narrow exception to ADR-0017's "not even a bare count": aggregate calibration statistics carry no subject data, and the master plan's R1 entry format requires them.
- what stays local: `eval/results/`, `eval/local/` (manifests and labels over private runs), `.apd-state/usage.yaml` and `attempts.yaml`, and every run.
- the GRAML-derived protocol: disjoint dev and held-out sets; tunables changed on dev only; frozen before held-out runs; held-out runs refused on a hash mismatch; re-freezing after held-out use requires a new held-out set; `calibrate` refuses held-out labels.
- alternatives rejected: mtime freshness; committing nothing (thresholds could never ship calibrated); thresholds stored per run.

- [ ] **Step 1: Write the failing tests**

```python
def root(tmp_path):
    for rel, text in {"tools/apd_gauntlet/data/decide/thresholds.yaml": "{}\n",
                      "tools/apd_gauntlet/data/iac/context-params.yaml": "k: 20\n"}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True); (tmp_path / rel).write_text(text)
    return tmp_path

def test_tunables_found(tmp_path):
    assert list(tunables(root(tmp_path))) == ["tools/apd_gauntlet/data/decide/thresholds.yaml",
                                              "tools/apd_gauntlet/data/iac/context-params.yaml"]

def test_missing_freeze(tmp_path):
    with pytest.raises(FreezeError, match="eval freeze"): check_frozen(root(tmp_path))

def test_freeze_then_edit(tmp_path):
    r = root(tmp_path); freeze(r)
    assert check_frozen(r) == yaml.safe_load((r / "eval/frozen.yaml").read_text())["tunables_sha256"]
    (r / "tools/apd_gauntlet/data/iac/context-params.yaml").write_text("k: 21\n")
    with pytest.raises(FreezeError, match="changed tools/apd_gauntlet/data/iac/context-params.yaml"): check_frozen(r)

def test_added_tunable_counts(tmp_path):
    r = root(tmp_path); freeze(r)
    (r / "tools/apd_gauntlet/data/codeflow").mkdir(); (r / "tools/apd_gauntlet/data/codeflow/context-params.yaml").write_text("k: 1\n")
    with pytest.raises(FreezeError, match="added"): check_frozen(r)

def test_refreeze_after_heldout_use_refused(tmp_path):
    r = root(tmp_path); freeze(r); sha = check_frozen(r)
    res = r / "eval/results/findings/heldout-20261011T000000Z.yaml"; res.parent.mkdir(parents=True)
    res.write_text(yaml.safe_dump({"frozen_sha256": sha}))
    (r / "tools/apd_gauntlet/data/decide/thresholds.yaml").write_text("x: {}\n")
    with pytest.raises(FreezeError, match="new held-out set"): freeze(r)
    freeze(r, new_heldout_set=True)
    assert yaml.safe_load((r / "eval/frozen.yaml").read_text())["generation"] == 2

def test_refreeze_without_heldout_use_keeps_generation(tmp_path): ...   # edit, freeze → generation 1
def test_cli_freeze(tmp_path): ...                                     # exit 0, file written; second call "unchanged"

# tests/test_adr_0028.py — header format, the four sections, and:
def test_load_bearing_decisions_stated():
    t = ADR.read_text().lower()
    for s in ("adr-0017", "thresholds.yaml", "frozen.yaml", "held-out", "eval/results", "eval/local", "graml"):
        assert s in t
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eval_freeze.py tests/test_adr_0028.py -v`
Expected: FAIL (module and ADR missing)

- [ ] **Step 3: Implement `freeze.py`, the command, the ADR and the cross-references**

CHANGELOG bullet for `eval freeze` and ADR-0028.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eval_freeze.py tests/test_adr_0028.py tests/test_ci_gate_docs.py -v && markdownlint-cli2 docs/adrs/0028-*.md docs/ci-gate-model.md docs/adrs/0017-*.md`
Expected: PASS; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/eval/freeze.py tools/apd_gauntlet/cli.py CHANGELOG.md docs/adrs docs/ci-gate-model.md tests/test_eval_freeze.py tests/test_adr_0028.py
git commit -m "feat(eval): freeze tunables by content hash; ADR-0028 committed calibration"
```

### Task 11: `eval run`

**Files:**

- Create: `tools/apd_gauntlet/eval/runner.py`
- Modify: `tools/apd_gauntlet/cli.py` (`eval run`), `.gitignore` (append `eval/results/` and `eval/local/` under a comment citing ADR-0028), `docs/measuring-changes.md`, `CHANGELOG.md`, `tests/test_measuring_changes_doc.py`
- Test: `tests/test_cli_eval_run.py`

**Interfaces:**

- Consumes: `load_corpus_manifest`, `load_labels` (Task 8); `get`, `load_builtin_evaluators` (Tasks 8–9); `check_frozen`, `RESULTS_RELPATH` (Task 10)
- Produces:
  - `def run_eval(manifest: Path, set_name: Literal["dev", "heldout"], evaluator: str, *, root: Path, results_dir: Path, now: datetime | None = None) -> Path`
  - Results file `<results_dir>/<evaluator>/<set>-<now:%Y%m%dT%H%M%SZ>.yaml`: `{schema_version: 1, evaluator, set, corpus: {name, path, sha256}, frozen_sha256: str | None, engine_version, generated_at, entries: [{id, counts, metrics, notes}], totals: {counts, metrics}}`. `totals.counts` sums entry counts; `totals.metrics` is `entries[0].derive(totals.counts)` (empty when `derive` is `None`).
  - CLI: `eval run CORPUS --set dev|heldout --evaluator NAME [--root DIR] [--results-dir DIR] [--json]`. `--root` defaults to `.`; `--results-dir` defaults to `<root>/eval/results`. Exit 0 written; 2 on `CorpusError`, `FreezeError`, an unknown evaluator, an evaluator `ValueError`, or no entries in the set.

`--set heldout` calls `check_frozen(root)` first; `--set dev` records the frozen hash when `check_frozen` succeeds and `null` otherwise.

- [ ] **Step 1: Write the failing tests**

```python
def setup_corpus(make_run, tmp_path, set_name):
    root = tmp_path / "repo"; ...                       # tunables as in Task 10's root()
    run = make_run("r"); labels = root / "eval/findings/labels/ceb.yaml"   # label_template, all true_positive
    m = root / "eval/findings/corpus.yaml"              # one entry {id: ceb, set: set_name, run: <abs run>, labels: labels/ceb.yaml}
    return root, m

def ev(root, m, s): return CliRunner().invoke(main, ["eval", "run", str(m), "--set", s, "--evaluator", "findings", "--root", str(root)])

def test_dev_run_writes_results(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "dev")
    assert ev(root, m, "dev").exit_code == 0
    (res,) = (root / "eval/results/findings").glob("dev-*.yaml")
    data = yaml.safe_load(res.read_text())
    assert data["totals"]["metrics"]["precision.all"] == 1.0 and data["frozen_sha256"] is None

def test_heldout_without_freeze_exits_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout")
    r = ev(root, m, "heldout"); assert r.exit_code == 2 and "eval freeze" in r.output

def test_heldout_after_tunable_edit_exits_2(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout"); freeze(root)
    (root / "tools/apd_gauntlet/data/iac/context-params.yaml").write_text("k: 99\n")
    r = ev(root, m, "heldout"); assert r.exit_code == 2 and "changed since freeze" in r.output

def test_heldout_records_frozen_hash_and_blocks_refreeze(make_run, tmp_path):
    root, m = setup_corpus(make_run, tmp_path, "heldout"); freeze(root)
    assert ev(root, m, "heldout").exit_code == 0
    (res,) = (root / "eval/results/findings").glob("heldout-*.yaml")
    assert yaml.safe_load(res.read_text())["frozen_sha256"] == check_frozen(root)
    (root / "tools/apd_gauntlet/data/iac/context-params.yaml").write_text("k: 99\n")
    assert CliRunner().invoke(main, ["eval", "freeze", "--root", str(root)]).exit_code == 1

def test_unknown_evaluator_exits_2(make_run, tmp_path): ...    # "--evaluator nope" → 2, output lists "findings"

def test_results_and_local_are_gitignored():
    lines = (REPO / ".gitignore").read_text().splitlines()
    assert "eval/results/" in lines and "eval/local/" in lines
```

Add `test_runbook_covers_eval` asserting `eval run`, `--set heldout`, `eval freeze`, `--new-heldout-set`, `label-template` and `eval/local/` appear.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli_eval_run.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (`No such command 'run'` in the `eval` group)

- [ ] **Step 3: Implement the runner, the command, `.gitignore` and the runbook section**

Runbook section "Evaluate against labels": corpus layout (`eval/<area>/corpus.yaml`, `eval/<area>/labels/`; private corpora under `eval/local/`), labelling with `eval label-template`, dev versus held-out, the freeze protocol, results location. CHANGELOG bullet for `eval run`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli_eval_run.py tests/test_eval_freeze.py tests/test_measuring_changes_doc.py -v && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/eval/runner.py tools/apd_gauntlet/cli.py .gitignore docs/measuring-changes.md CHANGELOG.md tests/test_cli_eval_run.py tests/test_measuring_changes_doc.py
git commit -m "feat(eval): add eval run with the held-out freeze guard"
```

### Task 12: `calibrate`

**Files:**

- Create: `tools/apd_gauntlet/eval/calibrate.py`, `tools/apd_gauntlet/data/decide/thresholds.yaml`, `tests/fixtures/eval/finding-qa.record.yaml`
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]` adds `"data/decide/*.yaml"`), `tools/apd_gauntlet/cli.py` (`calibrate`), `docs/measuring-changes.md`, `CHANGELOG.md`, `tests/test_measuring_changes_doc.py`
- Test: `tests/test_eval_calibrate.py`, `tests/test_cli_calibrate.py`

**Interfaces:**

- Consumes: `load_labels` (`decisions` kind, Task 8); `load_corpus` (`tools/apd_gauntlet/synthesis/loader.py:26`); `resources.data_dir()`; LA1's decision record (LA1 plan Task 5): `{schema_version, task, scope, provider, model, schema_sha256, generated_at, thresholds, usage, items: [{ref, outcome: pass|flag|error, flags, answers: {<question>: {type, …}}, error}]}`, with `noul` answers serialised as `{type: noul, p}` and `choice` answers as `{type: choice, choice, confidence, probabilities}`
- Produces:
  - `@dataclass(frozen=True) class ValueSpec: task: str; direction: Literal["above", "below"]; value: Callable[[Mapping[str, Any], Mapping[str, Any] | None], float | None]`
  - `VALUE_SPECS: dict[str, ValueSpec]`; `def register_value(key: str, spec: ValueSpec) -> None`
  - Built-in specs, from LA spec §5.4: `finding-qa.unsupported` (`below`; `item.answers.excerpt_supports_claim.p`) and `finding-qa.lens_drift` (`below`; `item.answers.goal.probabilities[finding.apd_goal]`, `None` without the finding). `finding-qa.severity_delta` depends on LA1's score scale and is registered by LA1.
  - `class CalibrationError(Exception)`
  - `@dataclass(frozen=True) class Calibration: threshold: float | None; precision: float | None; recall: float | None; n: int; feasible: bool; best_precision: float | None`
  - `def choose_threshold(pairs: Sequence[tuple[float, bool]], *, direction: Literal["above", "below"], target_precision: float, min_support: int = 10) -> Calibration`
  - `def labelled_pairs(labels: Labels, key: str) -> tuple[list[tuple[float, bool]], int]` — (pairs, skipped)
  - `THRESHOLDS_PATH = resources.data_dir() / "decide" / "thresholds.yaml"` (resolved lazily)
  - `def write_threshold(path: Path, key: str, cal: Calibration, labels_sha256: str) -> None` — sets `<key>: {threshold, precision (4 dp), recall (4 dp), n, labels_sha256, calibrated: true}`, keeps other entries, re-emits the fixed comment header, `sort_keys=True`
  - CLI: `calibrate TASK --labels FILE --target-precision P [--min-support N] [--thresholds PATH]`; `P` is `click.FloatRange(0, 1, min_open=True)`

`choose_threshold`: sort the distinct values; candidate cuts are midpoints of consecutive distinct values, so no labelled value sits on a cut and LA1's strict `<` and an inclusive comparison classify the labelled set identically. For each cut, positives are values above it (`above`) or below it (`below`); precision = TP/positives; recall = TP/all gold positives. A cut is feasible when positives ≥ `min_support` and precision ≥ the target. Choose the feasible cut with the highest recall, then the highest precision (equivalently the most conservative cut; exact ties cannot occur). The written threshold is `round(cut, 6)` when that stays strictly between its two neighbours, else `cut`. No feasible cut → `feasible=False`, `threshold=None`, `best_precision` = the highest precision among cuts with enough support (or `None`). No gold positives → `CalibrationError`.

`labelled_pairs`: resolve each `records[].path` relative to the labels file; the record's `task` must equal the part of `key` before the first `.`; every labelled `ref` must exist in the record (else `CalibrationError` naming it); items with `outcome: error` or a `None` value are skipped. The finding passed to `value` comes from `load_corpus(record_path.parents[2], include_attack_path=True)` (a record lives at `<run>/40-synthesis/decisions/<file>`), cached per run.

CLI exits: 2 for a key missing from `VALUE_SPECS` (lists the keys), labels not of kind `decisions`, a labels `task` different from `TASK`, labels with `set: heldout` ("calibrate on dev labels only; thresholds freeze before held-out runs"), or a `CalibrationError`; 1 when infeasible (`"no threshold reaches precision ≥ P with at least N predicted positives (best: Q); <TASK> stays uncalibrated"`), file untouched; 0 written, printing the entry and `"re-run 'apd-gauntlet eval freeze' before any held-out run"`.

`thresholds.yaml` ships as a comment header (registry R8; keys `<task>` or `<task>.<flag>`; written by `calibrate`; proposal entries ship as `calibrated: false` per amendment A1) followed by `{}`.

Fixture `finding-qa.record.yaml` follows the LA1 shape with `task: finding-qa`, `scope: 10-trustworthiness`, and nine items `conf-00000001`…`conf-00000009`: items 1–8 have `answers.excerpt_supports_claim.p` = 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8 and `outcome: pass`; item 9 has `outcome: error`. Tests copy it to `<tmp>/run/40-synthesis/decisions/finding-qa.10-trustworthiness.yaml` and write labels with `gold` true, true, true, false, true, false, false, false, true for items 1–9.

- [ ] **Step 1: Write the failing tests**

```python
PAIRS = [(0.95, True), (0.9, True), (0.85, True), (0.8, False), (0.7, True), (0.6, False), (0.4, False), (0.2, False)]

def test_max_recall_subject_to_precision():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=1)
    assert (c.threshold, c.precision, c.recall, c.n, c.feasible) == (0.65, 0.8, 1.0, 8, True)

def test_higher_target_moves_cut_up():
    assert choose_threshold(PAIRS, direction="above", target_precision=0.9, min_support=1).threshold == 0.825

def test_below_mirrors_above():
    c = choose_threshold([(1 - v, g) for v, g in PAIRS], direction="below", target_precision=0.75, min_support=1)
    assert c.threshold == 0.35 and c.recall == 1.0

def test_min_support_makes_it_infeasible():
    c = choose_threshold(PAIRS, direction="above", target_precision=0.75, min_support=6)
    assert not c.feasible and c.threshold is None and c.best_precision == pytest.approx(4 / 6)

def test_no_positive_labels_raise():
    with pytest.raises(CalibrationError): choose_threshold([(0.1, False), (0.2, False)], direction="above", target_precision=0.9)

def test_lens_drift_value_uses_finding_goal():
    item = {"answers": {"goal": {"type": "choice", "probabilities": {"confidentiality": 0.2, "authenticity": 0.8}}}}
    assert VALUE_SPECS["finding-qa.lens_drift"].value(item, {"apd_goal": "confidentiality"}) == 0.2

# tests/test_cli_calibrate.py
def test_calibrate_writes_entry(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"; th.write_text("{}\n")
    r = CliRunner().invoke(main, ["calibrate", "finding-qa.unsupported", "--labels", str(decision_labels),
                                  "--target-precision", "0.75", "--min-support", "1", "--thresholds", str(th)])
    assert r.exit_code == 0
    assert yaml.safe_load(th.read_text())["finding-qa.unsupported"] == {
        "threshold": 0.35, "precision": 0.8, "recall": 1.0, "n": 8,
        "labels_sha256": hashlib.sha256(decision_labels.read_bytes()).hexdigest(), "calibrated": True}

def test_min_support_refuses_tiny_sets(decision_labels, tmp_path):
    th = tmp_path / "thresholds.yaml"; th.write_text("{}\n"); before = th.read_bytes()
    r = CliRunner().invoke(main, ["calibrate", "finding-qa.unsupported", "--labels", str(decision_labels),
                                  "--target-precision", "0.75", "--thresholds", str(th)])
    assert r.exit_code == 1 and "uncalibrated" in r.output and th.read_bytes() == before

def test_heldout_labels_refused(decision_labels, tmp_path): ...        # set: heldout → exit 2, file unchanged
def test_task_mismatch_refused(decision_labels, tmp_path): ...         # CLI task finding-qa.lens_drift vs labels task → 2
def test_unknown_ref_refused(decision_labels, tmp_path): ...           # labels ref conf-0000000a → 2, names the ref
def test_unknown_task_lists_keys(decision_labels, tmp_path): ...       # "nope" → 2, output contains "finding-qa.unsupported"
def test_packaged_thresholds_file_exists():
    assert (resources.data_dir() / "decide/thresholds.yaml").is_file()
```

`decision_labels` is a module fixture in `tests/test_cli_calibrate.py` that builds the run and labels from the fixture as described above. Add `test_runbook_covers_calibrate` asserting `calibrate`, `--target-precision 0.98`, `--min-support`, `calibrated: true` and `eval freeze` appear.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eval_calibrate.py tests/test_cli_calibrate.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (module, command and data file missing)

- [ ] **Step 3: Implement `calibrate.py`, the data file, the package-data glob, the command and the runbook section**

Runbook section "Calibrate a decision threshold": label layout (`eval/local/decide/<key>.labels.yaml`, because the records live in local runs), the M6 command form `apd-gauntlet calibrate <task> --labels <file> --target-precision 0.98`, the support floor, what infeasible means, and that a calibration changes a tunable, so `eval freeze` follows. CHANGELOG bullet for `calibrate`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_eval_calibrate.py tests/test_cli_calibrate.py tests/test_measuring_changes_doc.py -v && markdownlint-cli2 docs/measuring-changes.md`
Expected: PASS; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/eval/calibrate.py tools/apd_gauntlet/data/decide/thresholds.yaml pyproject.toml tools/apd_gauntlet/cli.py tests/fixtures/eval tests/test_eval_calibrate.py tests/test_cli_calibrate.py tests/test_measuring_changes_doc.py docs/measuring-changes.md CHANGELOG.md
git commit -m "feat(eval): add calibrate for decision thresholds over labelled decision records"
```

### Task 13: Metamorphic harness and the demonstration suite

**Files:**

- Create: `tools/apd_gauntlet/eval/metamorphic.py`, `tools/apd_gauntlet/eval/suites/__init__.py`, `tools/apd_gauntlet/eval/suites/stride_table.py`, `tests/fixtures/metamorphic/stride-table/basic/threat-model.md` (byte copy of `tests/fixtures/threat_models/sample-stride-table.md`)
- Modify: `tools/apd_gauntlet/cli.py` (`metamorphic` group, `run`), `docs/measuring-changes.md`, `CHANGELOG.md`, `tests/test_measuring_changes_doc.py`
- Test: `tests/test_eval_metamorphic.py`

**Interfaces:**

- Consumes: `apd_gauntlet.threat_model.dispatcher.dispatch_parser(path: Path, hint: str | None = None) -> dict[str, Any]` (`tools/apd_gauntlet/threat_model/dispatcher.py:17`), the function behind `parse-threat-model`
- Produces:
  - `RenameMap = dict[str, str]` (transformed name → original name); `ResultSet = frozenset[tuple[str, ...]]`
  - `Transform = Callable[[Path, Path], RenameMap]` (source dir, empty destination dir → rename map; writes the transformed copy)
  - `@dataclass(frozen=True) class Suite: name: str; fixtures: tuple[str, ...]; transforms: Mapping[str, Transform]; extract: Callable[[Path], ResultSet]; normalise: Callable[[ResultSet, RenameMap], ResultSet]; known_non_invariant: Mapping[tuple[str, str], str] = field(default_factory=dict)` (fixtures are directories relative to `--root`; allowlist keys are `(transform, fixture)`, values the reason)
  - `SUITES: dict[str, Suite]`; `def register_suite(suite: Suite) -> None` (`ValueError` on a duplicate)
  - `BUILTIN_SUITE_MODULES: tuple[str, ...] = ("apd_gauntlet.eval.suites.stride_table",)`; `def load_builtin_suites() -> None` (IAC4 and CF4 append their modules)
  - `class MetamorphicError(Exception)`
  - `@dataclass(frozen=True) class CaseResult: fixture: str; transform: str; status: Literal["holds", "violated", "allowlisted", "stale_allowlist"]; missing: tuple[tuple[str, ...], ...]; extra: tuple[tuple[str, ...], ...]; reason: str | None`
  - `def run_suite(suite: Suite, root: Path, workdir: Path) -> list[CaseResult]`
  - CLI: `metamorphic run --suite NAME [--root DIR] [--json]` (`--json` prints `{"suite": NAME, "cases": [CaseResult as a dict]}`); exit 0 when every case holds or is allowlisted, 1 on `violated` or `stale_allowlist`, 2 on an unknown suite (lists registered names) or a missing fixture
- Suite `stride-table`: fixture `tests/fixtures/metamorphic/stride-table/basic`; `extract(d)` = `{(e["asset"], e["framework_refs"]["stride_letter"], e["threat"], ",".join(e["inferred_apd_goals"])) for e in dispatch_parser(d / "threat-model.md")["entries"]}`; `normalise` maps the first tuple element through the rename map. Transforms:
  - `rename-elements`: each data row's Element cell becomes `element-<n>` (row order); returns `{"element-<n>": <original>}`
  - `reorder-rows`: reverses the data rows; `{}`
  - `reorder-columns`: reverses the six STRIDE columns in the header, separator and data rows, Element first; `{}`

For each fixture, `run_suite` extracts the untouched fixture once, then per transform (sorted by name) copies into `workdir/<fixture-name>/<transform>/`, normalises the extracted set and compares. A violated case in the allowlist is `allowlisted`; an allowlisted case that holds is `stale_allowlist`, so the list stays honest (IaC spec §13.3: known non-invariances "must be listed explicitly in the suite's allowlist with a reason").

- [ ] **Step 1: Write the failing tests**

```python
def test_stride_suite_holds_end_to_end():
    r = CliRunner().invoke(main, ["metamorphic", "run", "--suite", "stride-table", "--root", str(REPO), "--json"])
    assert r.exit_code == 0
    assert sorted((c["transform"], c["status"]) for c in json.loads(r.stdout)["cases"]) == [
        ("rename-elements", "holds"), ("reorder-columns", "holds"), ("reorder-rows", "holds")]

def drop_last_row(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)
    p = dst / "threat-model.md"; p.write_text("\n".join(p.read_text().splitlines()[:-1]) + "\n"); return {}

def test_violation_detected(tmp_path, monkeypatch):
    load_builtin_suites(); base = SUITES["stride-table"]
    monkeypatch.setitem(SUITES, "t-drop", replace(base, name="t-drop", transforms={"drop-last-row": drop_last_row}))
    (case,) = run_suite(SUITES["t-drop"], REPO, tmp_path)
    assert case.status == "violated" and len(case.missing) == 1 and case.extra == ()
    assert case.missing[0][0] == "audit-log-writer"

def test_allowlisted_violation(tmp_path): ...       # known_non_invariant={("drop-last-row", <fixture>): "demo"} → "allowlisted"
def test_stale_allowlist(tmp_path): ...             # allowlist on reorder-rows → "stale_allowlist"
def test_unknown_suite_exits_2():
    r = CliRunner().invoke(main, ["metamorphic", "run", "--suite", "nope", "--root", str(REPO)])
    assert r.exit_code == 2 and "stride-table" in r.output
```

Add `test_runbook_covers_metamorphic` asserting `metamorphic run --suite`, `register_suite`, `known_non_invariant` and `stride-table` appear.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_eval_metamorphic.py tests/test_measuring_changes_doc.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Implement the harness, the suite, the fixture copy, the command and the runbook section**

The CLI runs in a `tempfile.TemporaryDirectory()` workdir. Runbook section "Behaviour-preserving transformations": what a suite declares, how IAC4 and CF4 add suites (`register_suite` in a module listed in `BUILTIN_SUITE_MODULES`), and the allowlist rule. CHANGELOG bullet for `metamorphic run`.

- [ ] **Step 4: Run tests to verify they pass, then the full gates**

Run: `pytest tests/test_eval_metamorphic.py tests/test_measuring_changes_doc.py -v && ruff check tools/ tests/ && mypy tools/ && pytest -q && markdownlint-cli2 docs/measuring-changes.md CHANGELOG.md`
Expected: PASS; ruff and mypy clean; coverage ≥ 85; 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/eval tools/apd_gauntlet/cli.py tests/fixtures/metamorphic tests/test_eval_metamorphic.py tests/test_measuring_changes_doc.py docs/measuring-changes.md CHANGELOG.md
git commit -m "feat(eval): add metamorphic harness with a parse-threat-model demonstration suite"
```

### Task 14: Acceptance on the Task 1 baselines (operator)

**Files:**

- Create: `eval/findings/corpus.yaml`, `eval/findings/labels/{claim-event-bus,acme-mobile-banking,home-assistant}.yaml`, `eval/frozen.yaml`
- Nothing run-derived is committed (ADR-0017, ADR-0028).

- [ ] **Step 1: Summarise baseline usage.** For every master plan Task 1 run: `apd-gauntlet usage runs/<name>-baseline-r<k> --otel telemetry/<name>-baseline-r<k>.otlp.jsonl`. Expected: exit 0, `.apd-state/usage.yaml` written, no "agent names redacted" warning, `unattributed` cost near zero.
- [ ] **Step 2: Measure the noise floor.** For each example: `apd-gauntlet compare-runs runs/<name>-baseline-r1 runs/<name>-baseline-r2 --gates eval/gates.yaml`. Expected: exit 0. If any gate fails between two runs of the same configuration, record the gate and its values in private notes and raise the set to three runs (master plan Risks) before WS3 starts.
- [ ] **Step 3: Label the committed examples.** For each example: `apd-gauntlet eval label-template examples/<example>/expected --entry <id> --out eval/findings/labels/<id>.yaml`, then review every item (verdict, gold goal, gold severity). Write `eval/findings/corpus.yaml` with the three entries in `set: dev` and `run: ../../examples/<example>/expected`. Run `apd-gauntlet eval run eval/findings/corpus.yaml --set dev --evaluator findings`. Expected: exit 0; `pytest tests/test_eval_committed_corpora.py` passes with three parameters.
- [ ] **Step 4: Freeze.** `apd-gauntlet eval freeze`. Expected: `eval/frozen.yaml` written (generation 1).
- [ ] **Step 5: Commit**

```bash
git add eval/findings eval/frozen.yaml
git commit -m "eval: label the committed examples (dev) and freeze tunables"
```
