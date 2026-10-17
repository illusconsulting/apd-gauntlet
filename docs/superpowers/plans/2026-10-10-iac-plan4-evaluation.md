# IaC Plan 4 — Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the IaC pipeline on labelled development and held-out repositories against the 1.7.1 raw-read baseline, prove its results survive behaviour-preserving changes (T1–T8), tune the packet parameters on development data only before WS2's freeze, and pre-fill the `iac-triage` calibration labels from the IaC labels.

**Architecture:** Everything plugs into WS2's harness instead of adding commands. The corpus is a WS2 `eval-corpus` manifest; labels use a new `iac` kind of WS2's `eval-labels` schema; three evaluators register with `apd_gauntlet.eval.evaluators.register` for `apd-gauntlet eval run`; suite `iac` registers with `apd_gauntlet.eval.metamorphic.register_suite` for `apd-gauntlet metamorphic run --suite iac`; WS2's `eval freeze` already covers `data/iac/context-params.yaml`. A local tuning script writes new parameters for the operator to freeze, and a helper pre-fills WS6's `iac-triage` label sheet from the IaC labels before `calibrate`.

**Tech Stack:** Python 3.10–3.12, PyYAML, jsonschema, python-hcl2 7.x; WS2 `eval run`, `eval freeze`, `metamorphic run`, `calibrate`; WS6 `decide-labels`; Atmos, Trivy, Checkov and OpenTofu for local runs; pytest with the `iac_tools` marker.

**Spec:** `docs/superpowers/specs/2026-10-10-iac-terraform-opentofu-atmos-design.md` §10 (frozen parameters), §11 item 7, §13.2 (including the 1.7 baseline amendment), §13.3, §15 item 4. Master plan R1 (`eval run`, `calibrate`, `metamorphic run`; `iac-triage` owned by WS6), R2 (`apd_gauntlet.eval.evaluators`), R7 (`eval-corpus`, `eval-labels`), R8 (`eval/` at the repo root), Task 8 Step 1, M6 exit gate. WS2 plan Tasks 8–13 and WS6 plan Tasks 12–13 (`docs/superpowers/plans/2026-10-10-ws2-measurement-and-evaluation.md`, `2026-10-10-ws6-decision-tasks.md`). This is Plan 4 of 4; it consumes Plans 1–3.

**Amended 2026-10-17** per the amendments register (A13.12, A13.18, A13.20, A13.21, A13.22, A13.23, A13.24, A15.12, A15.19).

## Global Constraints

- **Corpus manifest.** `eval/iac/corpus.yaml` pins repositories by commit SHA in two disjoint sets: development (synthetic fixtures plus intentionally vulnerable Terraform such as TerraGoat) and held-out (realistic Atmos and OpenTofu repositories by other authors). The plan confirms candidates and licences (spec §13.2).
- **Labels.** Each repository has a hand-labelled file of expected results: check category, address and verdict (spec §13.2).
- **Metrics.** Precision, recall and F1 per check category for the deterministic index; the same end to end for final findings; unknown rate; packet tokens per goal (spec §13.2).
- **Tuning protocol.** Tunables are tuned on development only and frozen before held-out runs: edge weights, score coefficients, K, reliability weights, and decision thresholds. A tunable changed after a held-out run means a new held-out set (spec §13.2). WS2 enforces this: `TUNABLE_GLOBS` includes `tools/apd_gauntlet/data/*/context-params.yaml`, `eval run --set heldout` exits 2 when tunables changed since `eval freeze`, and `eval freeze` refuses after held-out use without `--new-heldout-set`.
- **Baseline.** Every metric is also computed for 1.7.1's raw-read path on the same corpus and labels; a release that lowers recall of labelled issues against that baseline does not ship (spec §13.2 amendment; master plan M6: "Held-out IaC recall ≥ 1.7.1 baseline").
- **Transformation suite.** Each of T1–T8 is applied to the fixtures and the normalised result set `{(check id, address modulo rename map, verdict)}` must not change; known non-invariances are listed in the suite's allowlist with a reason (spec §13.3). WS2's allowlist is keyed by `(transform, fixture)`, so each IaC metamorphic fixture covers one concern.
- **Local only (ADR-0017, amended by WS2's ADR-0028).** Tests never touch the network; real runs, checkouts and results stay under the gitignored `eval/local/` and `eval/results/`. The transformation suite runs offline on committed fixtures in the `iac-tools` CI job, whose setup step alone downloads the pinned tool binaries (coordinator decision, 2026-10-11).
- **Decision thresholds** come from `calibrate` on development labels and are frozen before held-out runs (master plan Global Constraints). `decide iac-triage` is WS6's task (R1); this plan supplies its labels.

## Review Focus

- **Tuning that sees held-out data:** editing `data/iac/context-params.yaml` after `eval freeze` must make a held-out `eval run` exit 2, and the tuning script must never freeze. Pinned by Task 3 `test_context_params_are_tunables`, `test_heldout_refused_after_param_edit` and Task 4 `test_tune_writes_unfrozen_params`.
- **An operator who never ran the baseline:** `iac-delta` with no recorded 1.7.1 run for an entry fails with a message, never passes against nothing. Pinned by Task 3 `test_delta_without_baseline_fails`.
- **An undeclared or hiding non-invariance:** a transformation that changes a result set fails the suite unless that `(transform, fixture)` is allowlisted with a reason; the allowlist may never cover T1, T2, T4 or T7, which change nothing a scanner can see. Pinned by Task 2 `test_suite_flags_changed_results` and `test_allowlist_excludes_pipeline_transforms`.
- **A leaky corpus:** the same repository directory in both sets (even at different commits), a held-out entry without a licence, or a labels file of the wrong kind is a manifest error. Pinned by Task 1 `test_same_directory_in_both_sets_rejected`, `test_heldout_requires_licence`, `test_labels_must_be_iac_kind`.
- **A recall regression hidden by an average:** one category whose held-out recall falls below the baseline fails the gate even when total F1 rises. Pinned by Task 3 `test_delta_gate_fails_on_one_category`.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/data/schemas/eval-labels.schema.json`, `tools/apd_gauntlet/eval/corpus.py` | `iac` labels kind | Modify (WS2 files) |
| `eval/iac/corpus.yaml`, `eval/iac/labels/*.yaml` | Corpus manifest and labels | Create |
| `tools/apd_gauntlet/iac/evaluation.py` | IaC corpus checks, matching, metrics, evaluators | Create |
| `tools/apd_gauntlet/eval/evaluators.py` | `load_builtin_evaluators` imports the IaC evaluators | Modify (WS2 file) |
| `tools/apd_gauntlet/iac/metamorphic.py` | T1–T8, extract, normalise, suite | Create |
| `tools/apd_gauntlet/eval/metamorphic.py` | `BUILTIN_SUITE_MODULES` gains the IaC suite | Modify (WS2 file) |
| `tests/fixtures/iac/metamorphic/{sg,s3,rds,module,atmos}/` | One concern per fixture | Create |
| `tools/apd_gauntlet/iac/tuning.py`, `tools/scripts/tune_iac_context.py` | Grid, objective, parameter writer | Create |
| `tools/apd_gauntlet/iac/triage_labels.py`, `tools/scripts/prefill_iac_triage.py` | Pre-fill WS6's `iac-triage` sheet | Create |
| `.github/workflows/python-tests.yml` | `iac-tools` job runs the suite | Modify |
| `docs/iac-evaluation.md`, `docs/measuring-changes.md`, `docs/schema-evolution.md`, `RELEASING.md`, `CHANGELOG.md` | Docs and the release line | Modify |
| `tests/iac/test_corpus.py`, `test_metamorphic.py`, `test_evaluators.py`, `test_tuning.py`, `test_triage_labels.py` | Tests | Create |
| `tests/context/graphs.py` | Shared test graphs (Plan 3's `hub_graph`) | Create |

---

### Task 1: Corpus manifest and the `iac` labels kind

**Files:**

- Modify: `tools/apd_gauntlet/data/schemas/eval-labels.schema.json` (new `kind: iac` branch), `tools/apd_gauntlet/eval/corpus.py` (`Labels.kind` gains `"iac"`), `docs/schema-evolution.md`
- Create: `tools/apd_gauntlet/iac/evaluation.py` (corpus half), `eval/iac/corpus.yaml`, `eval/iac/labels/` (one file per development entry)
- Test: `tests/iac/test_corpus.py`

**Interfaces:**

- Consumes: WS2 `load_corpus_manifest`, `load_labels`, `Corpus`, `CorpusEntry(id, set, run_dir, repo: RepoPin | None, labels_path)`, `RepoPin(url, commit, path)`, `Labels(kind, path, sha256, data)`, `CorpusError`; Plan 2 `load_goal_map`
- Produces:
  - `eval-labels` kind `iac` (R7 change, additive): `{schema_version: 1, kind: iac, entry: str, repo_kind: synthetic|vulnerable|atmos|opentofu|terraform, infrastructure: <run-config infrastructure object>, baseline_infrastructure: <the same in its 1.7 glob form>, items: [{category: str, address: str, verdict: issue|no_issue, instance?: str, relevant?: [str], triage?: reachable_effective|not_reachable|not_effective, note?: str}] (minItems 1)}`
  - `@dataclass(frozen=True) class IacLabel: category: str; address: str; verdict: Literal["issue", "no_issue"]; instance: str | None = None; relevant: tuple[str, ...] = (); triage: str | None = None; note: str = ""`
  - `def iac_labels(labels: Labels) -> list[IacLabel]` (`ValueError` when `labels.kind != "iac"`)
  - `def validate_iac_corpus(corpus: Corpus, root: Path) -> list[str]` — beyond WS2's checks: the same `(repo.url, repo.path)` in both sets at any commit; a held-out entry without `licence`; a labels file not of kind `iac`; a label category absent from the goal map; a development set without one `synthetic` and one `vulnerable` entry
  - `def checkout_dir(entry: CorpusEntry, root: Path) -> Path` — `root / repo.path` when `repo.url` is this repository, else `root / "eval/local/iac/checkouts" / entry.id`

Manifest entries use WS2's shape `{id, set, repo: {url, commit, path}, labels, licence}`. Development entries: this repository's Plan 1–3 fixtures (`repo.url` `https://github.com/illusconsulting/apd-gauntlet.git` at the commit that last changed each fixture, `path: tests/fixtures/iac/<name>`) and `https://github.com/bridgecrewio/terragoat.git`, path `terraform/aws` (Apache-2.0). Held-out candidates, confirmed in Step 1: `https://github.com/cloudposse/atmos.git` `examples/quick-start-advanced` (Apache-2.0; Atmos with catalogs and inheritance), `https://github.com/terraform-aws-modules/terraform-aws-vpc.git` `examples/complete` (Apache-2.0), `https://github.com/terraform-aws-modules/terraform-aws-eks.git` `examples/eks-managed-node-group` (Apache-2.0; IAM-heavy), and one public OpenTofu repository with `.tofu` files, chosen in Step 1. TerraGoat is maintained by the Checkov authors, so it stays in development only.

`CorpusEntry` drops `licence`, so `validate_iac_corpus` reads it from the raw manifest. An entry whose root uses `../` modules puts the whole checkout in `inputs/` (register A13.20). For Atmos entries the 1.7.1 baseline is `terraform: ["<root>/components/terraform/**/*.tf"]`, with stacks as ordinary inputs (register A13.21, A15.19).

- [ ] **Step 1: Confirm candidates and licences (operator)**

Clone each held-out candidate at its current default-branch commit into `eval/local/iac/checkouts/<id>`, read `LICENSE` at that commit, and record `commit` and `licence`. Replace a candidate that is not Apache-2.0, MIT, MPL-2.0 or BSD, that has fewer than 10 resources, or whose authors overlap with this project's. Expected: four held-out entries with commit and licence; the OpenTofu entry contains at least one `.tofu` file.

- [ ] **Step 2: Write the failing tests**

```python
def test_committed_manifest_valid():
    corpus = load_corpus_manifest(REPO / "eval/iac/corpus.yaml")
    assert validate_iac_corpus(corpus, REPO) == [] and {e.set for e in corpus.entries} == {"dev", "heldout"}

def test_same_directory_in_both_sets_rejected(tmp_path):
    c = corpus_of(tmp_path, [entry("a", "dev", url="https://x/y.git", commit="a" * 40, path="p"),
                             entry("b", "heldout", url="https://x/y.git", commit="b" * 40, path="p")])
    assert any("both sets" in e for e in validate_iac_corpus(c, tmp_path))

def test_heldout_requires_licence(tmp_path): ...   # held-out entry without licence → error naming it
def test_labels_must_be_iac_kind(tmp_path): ...    # labels of kind findings → error naming the file
def test_unknown_category_rejected(tmp_path): ...  # label category "vibes" → error

def test_iac_labels_parse(tmp_path):
    labels = load_labels(write_iac_labels(tmp_path, items=[
        {"category": "network_exposure", "address": "aws_security_group.ssh", "verdict": "issue", "triage": "reachable_effective"}]))
    (lab,) = iac_labels(labels)
    assert (lab.verdict, lab.triage) == ("issue", "reachable_effective") and labels.data["repo_kind"]

def test_checkout_dir(tmp_path): ...   # this repo → root/path; other repo → root/eval/local/iac/checkouts/<id>
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/iac/test_corpus.py tests/test_eval_corpus.py -v`
Expected: FAIL on the new tests (WS2's own corpus tests still pass)

- [ ] **Step 4: Implement the kind, the checks, the manifest and the development labels**

Label the Plan 1–3 fixtures and TerraGoat's `terraform/aws` by hand: every check category each exercises, both verdicts, `relevant` addresses for each issue (what a good packet should contain), and `triage` where reachability is clear from the code. `docs/schema-evolution.md` gains a dated entry: `eval-labels` gains kind `iac`.

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/iac/test_corpus.py tests/test_eval_corpus.py tests/test_meta_schemas.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/data/schemas/eval-labels.schema.json tools/apd_gauntlet/eval/corpus.py tools/apd_gauntlet/iac/evaluation.py eval/iac docs/schema-evolution.md tests/iac/test_corpus.py
git commit -m "feat(eval): add the IaC corpus and the iac labels kind"
```

### Task 2: Behaviour-preserving transformation suite

**Files:**

- Create: `tools/apd_gauntlet/iac/metamorphic.py`, `tests/fixtures/iac/metamorphic/` (`sg/` an internet-open security group attached to an instance; `s3/` an unencrypted, unversioned bucket; `rds/` a public, unencrypted database referencing a subnet group; `module/` a self-contained resource suitable for T3; `atmos/` an Atmos root whose prod stack sets `map_public_ip_on_launch: true`, for T6; each with an `iac-fixture.yaml` holding its run-config `infrastructure` block)
- Modify: `tools/apd_gauntlet/eval/metamorphic.py` (`BUILTIN_SUITE_MODULES` gains `"apd_gauntlet.iac.metamorphic"`), `.github/workflows/python-tests.yml` (`iac-tools` job runs `apd-gauntlet metamorphic run --suite iac`)
- Test: `tests/iac/test_metamorphic.py`

**Interfaces:**

- Consumes: WS2 `RenameMap` (transformed name → original name), `ResultSet`, `Transform`, `Suite(name, fixtures, transforms, extract, normalise, known_non_invariant)`, `register_suite`, `run_suite`, `CaseResult`, `MetamorphicError` (WS2 Task 13's existing class; do not define a new one, register A13.22); Plan 1 `run_iac`, `parse_file`
- Produces:
  - Transforms (`(src, dst) -> RenameMap`): `t1_rename_resources`, `t2_rename_vars_locals`, `t3_move_to_local_module`, `t4_split_files`, `t4_merge_files` (registered as `T4-split` and `T4-merge`), `t5_tf_to_tofu`, `t6_move_to_catalog`, `t7_add_noise`, `t8_hcl_to_json`. A rename-map key ending in `.` is a prefix: T3 returns `{"module.moved.": ""}`.
  - `def extract(fixture: Path) -> ResultSet` — builds a temporary run with `inputs/` = the fixture and the fixture's `iac-fixture.yaml` infrastructure block, runs `run_iac`, and returns `{(check id, address, "fail" | "pass")}` over `check` and `control` entries; raises `MetamorphicError("suite iac needs trivy and checkov on PATH")` when either is missing
  - `def normalise(results: ResultSet, rename: RenameMap) -> ResultSet` — maps each address through exact keys, then prefix keys
  - `IAC_SUITE = Suite(name="iac", fixtures=(…the five fixture paths…), transforms={"T1": …, "T8": …}, extract=extract, normalise=normalise, known_non_invariant=KNOWN_NON_INVARIANT)`, registered at import
  - `KNOWN_NON_INVARIANT: dict[tuple[str, str], str]` — filled in Step 4 from real runs only
  - `PIPELINE_TRANSFORMS = frozenset({"T1", "T2", "T4-split", "T4-merge", "T7"})`

Transform behaviour: T1 renames every resource label and rewrites `type.old` references in all files; T2 renames every `variable` and `locals` key and rewrites `var.`/`local.` uses and var files; T3 moves the fixture's single self-contained resource into `modules/moved/` and adds `module "moved" { source = "./modules/moved" }`; T4 writes one block per file, or merges every file into `main.tf`; T5 renames every `.tf` to `.tofu` and sets the fixture's engine to `opentofu`; T6 moves one prod stack var into a new abstract catalog component and adds it to `metadata.inherits`; T7 adds comments, an unused variable and a dead local to every file; T8 rewrites each `.tf` as `.tf.json` from its parsed form.

- [ ] **Step 1: Write the failing tests**

```python
def test_t1_rewrites_references(tmp_path):
    rename = t1_rename_resources(FIX / "metamorphic/sg", tmp_path / "t1")
    text = (tmp_path / "t1/main.tf").read_text()
    (new,) = [k for k, v in rename.items() if v == "aws_security_group.ssh"]
    assert f"{new}.id" in text and "aws_security_group.ssh" not in text

def test_t3_prefix_map(tmp_path):
    assert t3_move_to_local_module(FIX / "metamorphic/module", tmp_path / "t3") == {"module.moved.": ""}
    assert (tmp_path / "t3/modules/moved/main.tf").exists()

def test_normalise_exact_then_prefix():
    rs = frozenset({("AWS-0107", "aws_security_group.x1", "fail"), ("CKV_AWS_19", "module.moved.aws_s3_bucket.b", "fail")})
    assert normalise(rs, {"aws_security_group.x1": "aws_security_group.ssh", "module.moved.": ""}) == frozenset(
        {("AWS-0107", "aws_security_group.ssh", "fail"), ("CKV_AWS_19", "aws_s3_bucket.b", "fail")})

def test_t5_renames_every_file(tmp_path): ...       # no .tf left; iac-fixture.yaml engine opentofu; map {}
def test_t6_moves_value_to_catalog(tmp_path): ...   # prod manifest no longer sets the var; the new catalog component does; inherits lists it
def test_t7_noise_parses(tmp_path): ...             # parse_file succeeds on every file; block addresses unchanged plus one variable and one local
def test_t8_json_same_blocks(tmp_path):
    t8_hcl_to_json(FIX / "metamorphic/s3", tmp_path / "t8")
    assert {b.address for b in parse_file(tmp_path / "t8/main.tf.json")} == {b.address for b in parse_file(FIX / "metamorphic/s3/main.tf")}

def test_missing_tool_exits_2(tmp_path, monkeypatch): ...   # trivy and checkov absent from PATH → `metamorphic run --suite iac` exits 2 naming them (register A13.22)

def test_suite_registered():
    load_builtin_suites()
    assert SUITES["iac"] is IAC_SUITE and set(IAC_SUITE.transforms) == {"T1", "T2", "T3", "T4-split", "T4-merge", "T5", "T6", "T7", "T8"}

def test_allowlist_excludes_pipeline_transforms():
    assert not [k for k in KNOWN_NON_INVARIANT if k[0] in PIPELINE_TRANSFORMS]
    assert all(reason.strip() for reason in KNOWN_NON_INVARIANT.values())

def test_suite_flags_changed_results(tmp_path, monkeypatch):
    monkeypatch.setattr(metamorphic, "extract", lambda d: frozenset() if "T1" in str(d) else frozenset({("AWS-0107", "a.b", "fail")}))
    cases = run_suite(dataclasses.replace(IAC_SUITE, extract=metamorphic.extract,
                                          fixtures=("tests/fixtures/iac/metamorphic/sg",)), REPO, tmp_path)
    assert {(c.transform, c.status) for c in cases if c.transform == "T1"} == {("T1", "violated")}

@pytest.mark.iac_tools
def test_suite_green_on_fixtures(require_tools):
    require_tools("trivy", "checkov", "atmos")
    r = CliRunner().invoke(main, ["metamorphic", "run", "--suite", "iac", "--root", str(REPO), "--json"])
    assert r.exit_code == 0, r.output
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/iac/test_metamorphic.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the transforms, `extract`, `normalise` and the registration**

Missing tools raise WS2's `MetamorphicError`; confirm that `metamorphic run` maps it to exit 2 (register A13.22).

- [ ] **Step 4: Run the live suite and record genuine non-invariances**

Run: `PATH="$APD_IAC_TOOLS_BIN:$PATH" apd-gauntlet metamorphic run --suite iac --json`
Expected: exit 0. Each `violated` case is either a pipeline defect, fixed in the owning plan's module with a regression test there, or a scanner limitation (for example a scanner treating `.tf.json` differently) recorded in `KNOWN_NON_INVARIANT` with the tool version and reason. A `stale_allowlist` case means the row is no longer needed and is removed.

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/iac/test_metamorphic.py tests/test_eval_metamorphic.py -v`
Expected: PASS (the live test skips without the tools)

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/iac/metamorphic.py tools/apd_gauntlet/eval/metamorphic.py tests/fixtures/iac/metamorphic .github/workflows/python-tests.yml tests/iac/test_metamorphic.py
git commit -m "test(iac): add the T1–T8 behaviour-preserving transformation suite"
```

### Task 3: Evaluators and the release gate

**Files:**

- Modify: `tools/apd_gauntlet/iac/evaluation.py` (matching, metrics, evaluators), `tools/apd_gauntlet/eval/evaluators.py` (`load_builtin_evaluators` also imports `apd_gauntlet.iac.evaluation`)
- Test: `tests/iac/test_evaluators.py`

**Interfaces:**

- Consumes: WS2 `register`, `EvalResult(entry_id, counts, metrics, notes, derive)`, `CorpusEntry`, `Labels`, `tunables`, `freeze`, `eval run` exit codes; Task 1 `iac_labels`, `checkout_dir`; Plan 1 `run_iac`; Plan 2 `load_goal_map`; Plan 3 packet files
- Produces:
  - `RUNS_RELPATH = Path("eval/local/iac/runs.yaml")` — `{entry id: {baseline: run dir, candidate: run dir}}`, local only
  - `def match_index(entries: Sequence[Mapping[str, Any]], labels: Sequence[IacLabel]) -> dict[str, int]` — counts `tp.<category>`, `fp.<category>`, `fn.<category>`: a failed `check` entry that is not `plan_refuted` (with or without `suppressed_in_repo`, since a client suppression records acceptance, not absence) matches a label with the same category and the same trailing `type.name` address (and instance, when the label names one); an `issue` label with a match is TP, without one FN; a matched `no_issue` label is FP
  - `def match_findings(run_dir: Path, labels: Sequence[IacLabel]) -> dict[str, int]` — the same counts end to end: a final finding (`40-synthesis/deduped-findings.yaml`, else every `*.findings.yaml`) covers a label when its title, summary, detail or evidence locators name the label's trailing `type.name` and its `apd_goal` is one of the category's goals; a finding naming a labelled address that covers no `issue` label counts FP in that label's category
  - `def iac_metrics_from_counts(counts: Mapping[str, int]) -> dict[str, float | None]` — `precision.<c>`, `recall.<c>`, `f1.<c>` per category and `all` (`None` on a zero denominator), `unknown_rate` = `unknown` ÷ `entries`, `packet_tokens.<goal>` and `raw_iac_tokens` passed through
  - `def packet_tokens(run_dir: Path) -> dict[str, int]` — characters ÷ 4 of each `00-context/iac-packets/<goal>.md`
  - `def raw_iac_tokens(checkout: Path, baseline_infrastructure: Mapping[str, Any]) -> int` — characters ÷ 4 of the files the 1.7 glob form declares (the baseline's evidence cost)
  - `def delta_counts(base: Mapping[str, int], cand: Mapping[str, int]) -> dict[str, int]` and `def delta_metrics(counts: Mapping[str, int]) -> dict[str, float | None]` — `recall.<c>.baseline`, `recall.<c>.candidate`, `recall_delta.<c>`, and `gate_pass` = 1.0 only when every category with baseline issues has `recall_delta.<c> ≥ 0`
  - Evaluators, each `(entry: CorpusEntry, labels: Labels) -> EvalResult` with `derive` set, registered at import: `iac-index` (runs `run_iac` on a temporary run built from `checkout_dir(entry)` and the labels' `infrastructure`; counts from `match_index` plus `unknown`, `entries`, `packet_tokens.<goal>`), `iac-findings` (the candidate run from `RUNS_RELPATH` or `entry.run_dir`), `iac-findings-baseline` (the baseline run, plus `raw_iac_tokens`), `iac-delta` (both, through `delta_counts`/`delta_metrics`). A missing run directory raises `ValueError` naming the entry and side, which `eval run` turns into exit 2.

- [ ] **Step 1: Write the failing tests**

```python
LABELS = [IacLabel("network_exposure", "aws_security_group.ssh", "issue"),
          IacLabel("encryption_at_rest", "aws_s3_bucket.logs", "issue"),
          IacLabel("public_access", "aws_db_instance.db", "no_issue")]

def test_match_index_counts():
    entries = [check_entry("network_exposure", "module.net.aws_security_group.ssh"),
               check_entry("public_access", "aws_db_instance.db"),
               check_entry("network_exposure", "aws_security_group.ssh", confidence="plan_refuted")]
    c = match_index(entries, LABELS)
    assert (c["tp.network_exposure"], c["fn.encryption_at_rest"], c["fp.public_access"]) == (1, 1, 1)
    m = iac_metrics_from_counts(c)
    assert m["recall.network_exposure"] == 1.0 and m["recall.encryption_at_rest"] == 0.0

def test_suppressed_entry_still_matches():
    e = check_entry("encryption_at_rest", "aws_s3_bucket.logs") | {"suppressed_in_repo": True}
    assert match_index([e], LABELS)["tp.encryption_at_rest"] == 1

def test_match_findings_requires_goal(tmp_path): ...   # finding names the address with apd_goal availability → not TP for network_exposure

def test_delta_gate_fails_on_one_category():
    base = {"tp.network_exposure": 4, "fn.network_exposure": 1, "tp.logging": 2, "fn.logging": 2}
    cand = {"tp.network_exposure": 5, "fn.network_exposure": 0, "tp.logging": 1, "fn.logging": 3}
    m = delta_metrics(delta_counts(base, cand))
    assert m["recall_delta.logging"] == pytest.approx(-0.25) and m["gate_pass"] == 0.0

def test_delta_without_baseline_fails(tmp_path, monkeypatch):
    write_runs(tmp_path, {"h1": {"candidate": str(tmp_path / "c")}})
    with pytest.raises(ValueError, match="h1.*baseline"):
        get("iac-delta")(entry_for(tmp_path, "h1", "dev"), labels_for(tmp_path))

def test_evaluators_registered():
    load_builtin_evaluators()
    assert {"iac-index", "iac-findings", "iac-findings-baseline", "iac-delta"} <= set(EVALUATORS)

def test_context_params_are_tunables():
    assert "tools/apd_gauntlet/data/iac/context-params.yaml" in tunables(REPO)

def test_heldout_refused_after_param_edit(tmp_path):
    root = repo_copy_with_corpus(tmp_path)          # tunables, eval/iac/corpus.yaml with one held-out entry and its labels
    freeze(root)
    p = root / "tools/apd_gauntlet/data/iac/context-params.yaml"; p.write_text(p.read_text().replace("k: 20", "k: 21"))
    r = CliRunner().invoke(main, ["eval", "run", str(root / "eval/iac/corpus.yaml"), "--set", "heldout",
                                  "--evaluator", "iac-index", "--root", str(root)])
    assert r.exit_code == 2 and "tunables changed since freeze" in r.output

def test_packet_tokens(tmp_path): ...   # 400-character confidentiality.md → {"confidentiality": 100, …}
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/iac/test_evaluators.py -v`
Expected: FAIL

- [ ] **Step 3: Implement matching, metrics and the evaluators; add the import to `load_builtin_evaluators`**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/iac/test_evaluators.py tests/test_eval_evaluators.py tests/test_cli_eval_run.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/evaluation.py tools/apd_gauntlet/eval/evaluators.py tests/iac/test_evaluators.py
git commit -m "feat(eval): add IaC index, findings and baseline-delta evaluators"
```

### Task 4: Tune the packet parameters on development data

**Files:**

- Create: `tools/apd_gauntlet/iac/tuning.py`, `tools/scripts/tune_iac_context.py`
- Test: `tests/iac/test_tuning.py`

**Interfaces:**

- Consumes: Plan 3 `ContextParams`, `load_context_params`, `select_packet`, `TypedGraph`, `seeds_from_index`, `render_packet`; Task 1 labels (`relevant`); Task 3 `checkout_dir`
- Produces:
  - `GRID: dict[str, tuple[float, ...]] = {"k": (10, 15, 20, 25), "exposure": (0.25, 0.30, 0.35), "trust": (0.20, 0.25, 0.30), "coef_diversity": (0.10, 0.20, 0.30), "coef_redundancy": (0.05, 0.10, 0.20), "uncertain": (0.4, 0.5, 0.6)}` — `exposure` and `trust` set both weights of their pair (exposure/routing, trust/grants); `uncertain` is the reliability weight
  - `@dataclass(frozen=True) class TuneCase: graph: TypedGraph; seeds: dict[str, float]; relevant: frozenset[str]; chars: Callable[[Packet], int]`
  - `def packet_recall(params: ContextParams, cases: Sequence[TuneCase]) -> tuple[float, float]` — mean fraction of each case's `relevant` nodes in its packet, and mean packet tokens (`chars ÷ 4`)
  - `def choose_params(base: ContextParams, grid: Mapping[str, Sequence[float]], evaluate: Callable[[ContextParams], tuple[float, float]]) -> ContextParams` — highest recall with mean tokens ≤ `base.token_cap`; ties go to fewer tokens, then to the grid point nearest `base`
  - `def write_params(params: ContextParams, *, dev_corpus_sha256: str, labels_sha256: str, path: Path) -> ContextParams` — writes `version + 1` and `tuned_on: {set: dev, corpus_sha256, labels_sha256, date}`; it never runs `eval freeze`
  - Script: `python -I tools/scripts/tune_iac_context.py --corpus eval/iac/corpus.yaml` — builds development cases with real tools, refuses any held-out entry, runs `choose_params` and `write_params`, prints the values with their development recall and tokens, and ends with `re-run 'apd-gauntlet eval freeze' before any held-out run`

- [ ] **Step 1: Write the failing tests**

```python
def test_choose_prefers_recall_within_cap():
    table = {10: (0.70, 900.0), 15: (0.80, 1400.0), 20: (0.85, 1500.0), 25: (0.86, 7000.0)}
    assert choose_params(load_context_params("iac"), {"k": (10, 15, 20, 25)}, lambda p: table[p.k]).k == 20

def test_choose_ties_prefer_fewer_tokens(): ...   # equal recall at k 15 (1400) and 20 (1500) → 15

def test_tune_writes_unfrozen_params(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("apd_gauntlet.eval.freeze.freeze", lambda *a, **k: calls.append(a))
    out = write_params(load_context_params("iac"), dev_corpus_sha256="a" * 64, labels_sha256="b" * 64, path=tmp_path / "p.yaml")
    doc = yaml.safe_load((tmp_path / "p.yaml").read_text())
    assert (out.version, doc["tuned_on"]["set"]) == (2, "dev") and calls == []

def test_packet_recall():
    case = TuneCase(hub_graph(), {"sg": 0.8}, frozenset({"sg", "igw", "rt", "nat"}), lambda p: 400)
    assert packet_recall(load_context_params("iac"), [case]) == (0.5, 100.0)   # sg and igw selected; rt and nat not

def test_script_refuses_heldout_entries(tmp_path): ...   # a corpus whose only entries are held-out → exit 2, nothing written
```

`hub_graph()` is Plan 3 Task 3's test graph, moved to `tests/context/graphs.py` so both suites import it.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/iac/test_tuning.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `tuning.py` and the script**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/iac/test_tuning.py tests/context -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/tuning.py tools/scripts/tune_iac_context.py tests/iac/test_tuning.py tests/context
git commit -m "feat(eval): tune IaC packet parameters on development data"
```

### Task 5: Pre-fill the `iac-triage` label sheet

**Files:**

- Create: `tools/apd_gauntlet/iac/triage_labels.py`, `tools/scripts/prefill_iac_triage.py`
- Test: `tests/iac/test_triage_labels.py`

**Interfaces:**

- Consumes: WS6 `apd_gauntlet.decide.labels` (`build_sheet`, `set_label`, `write_yaml_local`, `sheet_path`, `LABEL_CHOICES["iac-triage"]`) (`reachable_effective`, `not_reachable`, `not_effective`), the sheet item shape `{record, ref, score, context, label}` with `ref = "<finding id>@<sha8>"`; WS6 `apd_gauntlet.decide.tasks.iac_triage.cited_iac_ids`; Task 1 `iac_labels`; Plan 2 index entries
- Produces:
  - `def label_for_finding(run_dir: Path, finding_id: str, labels: Sequence[IacLabel]) -> str | None` — the `triage` value of the `issue` label matching any `check` entry the finding cites (via `cited_iac_ids` and the run's index), when exactly one distinct value applies
  - `def prefill_sheet(sheet: dict[str, Any], labels_for_run: Callable[[Path], Sequence[IacLabel]]) -> tuple[int, int]` — calls `set_label` for every unlabelled item whose finding resolves to a triage value; returns (filled, left for review); a record's run directory is `Path(item["record"]).parents[2]`
  - Script: `python -I tools/scripts/prefill_iac_triage.py SHEET --corpus eval/iac/corpus.yaml` — maps each run directory to its development entry through `RUNS_RELPATH`, refuses held-out entries, pre-fills, and saves with `write_yaml_local`

- [ ] **Step 1: Write the failing tests**

```python
def test_label_for_finding(tmp_path):
    run = triage_run(tmp_path)   # index with iev-3f9a0c12 on aws_security_group.ssh; finding conf-1 cites it
    labels = [IacLabel("network_exposure", "aws_security_group.ssh", "issue", triage="not_reachable")]
    assert label_for_finding(run, "conf-1", labels) == "not_reachable"
    assert label_for_finding(run, "conf-2", labels) is None          # cites no IaC entry

def test_prefill_counts_and_labels(tmp_path):
    sheet = {"task": "iac-triage", "choices": {"reachable_effective": True, "not_reachable": False, "not_effective": False},
             "items": [sheet_item(tmp_path, "conf-1@abcd1234"), sheet_item(tmp_path, "conf-2@abcd1234")]}
    filled, left = prefill_sheet(sheet, lambda run: [IacLabel("network_exposure", "aws_security_group.ssh", "issue", triage="reachable_effective")])
    assert (filled, left) == (1, 1) and sheet["items"][0]["label"] == "reachable_effective"

def test_conflicting_labels_left_for_review(tmp_path): ...   # finding cites two entries labelled differently → None
def test_script_refuses_heldout(tmp_path): ...               # sheet whose run maps to a held-out entry → exit 2, sheet untouched
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/iac/test_triage_labels.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `triage_labels.py` and the script**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/iac/test_triage_labels.py tests/decide/test_labels.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/triage_labels.py tools/scripts/prefill_iac_triage.py tests/iac/test_triage_labels.py
git commit -m "feat(eval): pre-fill iac-triage labels from the IaC corpus labels"
```

### Task 6: Run the evaluation and gate the release (operator)

**Files:**

- Modify: `docs/iac-evaluation.md` ("Evaluation"), `docs/measuring-changes.md` (WS2 runbook: "IaC corpus" pointer), `RELEASING.md` (a new `### Beta gates (v2.0.0b1)` checklist in "Cutting a 2.0 pre-release"; none exists yet, register A13.23), `CHANGELOG.md`, `tools/apd_gauntlet/data/iac/context-params.yaml` (Task 4 output), `eval/frozen.yaml` (WS2 `eval freeze` output)

Every step runs locally (ADR-0017, ADR-0028); run directories, checkouts and results stay under `eval/local/` and `eval/results/`.

- [ ] **Step 1: Label the held-out set**

Label each held-out checkout before any candidate run on it. Expected: `validate_iac_corpus` clean; held-out labels committed; no run output consulted while labelling.

- [ ] **Step 2: Run the 1.7.1 raw-read baseline**

In a separate virtual environment with `apd-gauntlet==1.7.1` and the 1.7.1 plugin, run the gauntlet twice per corpus entry with the labels' `baseline_infrastructure` (register A13.24), and record each run directory as `baseline` in `eval/local/iac/runs.yaml`. Because `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started, every run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or starts a new session (register A15.12). Expected: every run completes and passes `apd-gauntlet validate`.

- [ ] **Step 3: Development evaluation and tuning**

Run: `apd-gauntlet eval run eval/iac/corpus.yaml --set dev --evaluator iac-index`, then `python -I tools/scripts/tune_iac_context.py --corpus eval/iac/corpus.yaml`, then the same `eval run` again.
Expected: the second run's development packet recall is at least the first's, with mean packet tokens within the cap; commit `data/iac/context-params.yaml` with `chore(iac): packet parameters tuned on development data`.

- [ ] **Step 4: Calibrate triage (after WS6 Task 12 lands `iac-triage`)**

Run `decide iac-triage` in shadow mode on the development candidate runs, then: `apd-gauntlet decide-labels sheet iac-triage <dev run dirs…>`, `python -I tools/scripts/prefill_iac_triage.py eval/local/decide/iac-triage.sheet.yaml --corpus eval/iac/corpus.yaml`, `apd-gauntlet decide-labels annotate eval/local/decide/iac-triage.sheet.yaml` for the rest, `apd-gauntlet decide-labels export eval/local/decide/iac-triage.sheet.yaml`, and `apd-gauntlet calibrate iac-triage --labels eval/local/decide/iac-triage.labels.yaml --target-precision 0.98` (master plan Task 8 Step 2).
Expected: `data/decide/thresholds.yaml` gains `iac-triage` with `calibrated: true`, or exit 1 with the task left uncalibrated.

- [ ] **Step 5: Freeze**

Run: `apd-gauntlet eval freeze`
Expected: `eval/frozen.yaml` written; commit it with the tuned parameters and thresholds.

- [ ] **Step 6: Held-out candidate runs and the gate**

Run the 2.0 gauntlet twice per held-out entry, record each as `candidate` in `eval/local/iac/runs.yaml`, then `apd-gauntlet eval run eval/iac/corpus.yaml --set heldout --evaluator iac-delta` and `--evaluator iac-index` (`iac-index` runs once; it is deterministic, register A13.24). Because `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started, every run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or starts a new session (register A15.12).
Expected: `gate_pass: 1.0` in the `iac-delta` totals (mean per-category recall of labelled issues over the two runs ≥ the 1.7.1 baseline in every category, register A13.24; master plan M6). If it fails, fix the defect; any tunable change after this point needs a new held-out set (`eval freeze --new-heldout-set`).

- [ ] **Step 7: Record the results and the release line**

`docs/iac-evaluation.md` "Evaluation": the corpus (ids, kinds, licences), how to reproduce Steps 2–6, the metrics table (per-category P/R/F1 for the index and end to end, unknown rate, packet tokens per goal against the baseline's raw IaC tokens) and the frozen parameter values. `docs/measuring-changes.md` points at it. `RELEASING.md` gains a `### Beta gates (v2.0.0b1)` checklist in "Cutting a 2.0 pre-release" (none exists yet, register A13.23) with "Held-out `iac-delta` totals report `gate_pass: 1.0`". `CHANGELOG.md` notes the evaluation.

Run: `markdownlint-cli2 docs/iac-evaluation.md docs/measuring-changes.md RELEASING.md CHANGELOG.md`
Expected: 0 lint errors

- [ ] **Step 8: Commit**

```bash
git add docs/iac-evaluation.md docs/measuring-changes.md RELEASING.md CHANGELOG.md eval/iac/labels
git commit -m "docs(iac): record the held-out evaluation against the 1.7.1 baseline"
```
