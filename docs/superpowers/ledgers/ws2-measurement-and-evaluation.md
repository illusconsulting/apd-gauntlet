# WS2 execution ledger

Plan: `docs/superpowers/plans/2026-10-10-ws2-measurement-and-evaluation.md`; base commit `c2be739` (`origin/next`); started 2026-10-17.

## Rulings

- Task 1 review, `RunLoadError` coverage: `load_run` now raises `RunLoadError` naming the file for every read or parse failure. That covers `yaml.YAMLError`, a `ValueError` from PyYAML (an unquoted impossible date such as `2026-02-30`), text that is not UTF-8, and an `OSError`. It also covers any file whose top level is not a mapping (corpus files, `asset-graph.yaml`, `report-data.yaml`, `deduped-findings.yaml`) and any corpus record whose `id` is not a string. Such a record raises rather than being dropped, because a dropped record would look lost and fail Gate 1 for the wrong reason. When `load_corpus` fails and no corpus file is at fault, the original exception is re-raised.
- Task 1 review, `inputs_digest` and dotfiles: the digest keeps "every file", dotfiles included, as the plan says. A stray Finder `.DS_Store` makes Task 6 refuse with exit 2, which is loud and fixed by deleting the file. Skipping dotfiles would hide genuine inputs such as `.github/` or `.terraform.lock.hcl` and let runs over different inputs compare silently. Files are hashed in 1 MiB chunks. The walk uses `os.walk` with an error handler instead of `rglob`, because `rglob` skips an unreadable directory without saying so; an unreadable file or directory now raises `RunLoadError` naming it.
- Task 1 review, code locators: `_CODE_LOCATOR` is `^code:([^:@]+)`, the codebase's `code:<qualified_name>[:Lx-Ly][@sha]` grammar (`assemble_c4.py` `_CODE_LOCATOR_RE`, `report/transform.py` `_C4_CODE_LOCATOR_RE`), not the plan's `^code:([^:]+):`. The line range is optional in that grammar and the validator does not enforce it. Under the plan's regex a range-less locator fell back to the shared `artifact:code-evidence-index.yaml` key, which every code-citing record shares. Every code locator in the committed examples carries a range, so their keys do not change, and the plan's `test_asset_keys_code_artifact_and_graph` still passes.
- Task 1 review, `merged_from`: only string members count when a headline is expanded; an id with no string member expands to itself.
- Task 1 review, `merged-*` ids on asset-graph edges: declined, no change. The engine builds edges from `**/*.findings.yaml` with pre-dedup ids (`attack_path/build.py` `_load_all_records(run_dir, key="finding", glob="**/*.findings.yaml")` and `finding_id=f["id"]`), and `deduped-findings.yaml` does not match that glob. A `merged-*` edge id can only come from a hand edit the schema allows. None of the three examples has one, and the plan is silent. Revisit if a real run shows one.
- Task 1 second review, plural root keys: `_records` maps each record kind to the plural `load_corpus` accepts (`findings`, `capabilities`). It used to build `key + "s"`, which gave `capabilitys`. A `capabilities:` file with a non-string `id` then raised `RunLoadError` naming the run directory, not the file.
- Task 1 second review, YAML nested too deeply: a `RecursionError` from PyYAML (for example 5000 nested `[`) becomes `RunLoadError` naming the file, in `_parse` and around `load_corpus`. Left uncaught, it ends the process with a traceback and exit 1, and `compare-runs` uses exit 1 to mean "a gate failed". Task 6 needs exit 2 when a run fails to load.
- Task 1 second review, links in `inputs/`: init-run keeps internal links (`copytree(symlinks=True)`, `copy2(follow_symlinks=False)`, then `_relativize_links`), so a real run can hold them. A link to a file is still hashed by its bytes, as the planned line format says. A link to a directory, which `os.walk` lists but does not enter, and a dangling link now each add `"<path>\0link:<link text>\n"`. Before this, two runs whose `docs` link pointed at different internal directories got the same digest. Following links would loop on an internal link to an ancestor, which init-run allows. A run with no directory links and no dangling links keeps the planned digest unchanged.
- Task 1 second review, `rank: true`: a boolean is not a rank (`report-data.schema.json` types `rank` as an integer from 1 to 10). It sorts with the unranked headlines, last and in file order, rather than as rank 1.
- Task 1 second review, empty `headlines`: kept as the plan says. `headlines` is `None` only when `report-data.yaml` or `deduped-findings.yaml` is missing. It is `()` when both exist but no headline has a string `id`, and a test pins that. Task 2's `headline_overlap_pct` ("`None` when either side has no headlines") must therefore test `not snapshot.headlines`, not `is None`.

## Deviations

- Task 1 (`b9baeed`): the Step 1 test block is reformatted, not changed. Statements joined by `;` are split onto separate lines (ruff E702), and long lines are wrapped to the 100-character limit. The assertions are the plan's.
- Task 1: register A9.1 places `load_corpus` in `report/loader.py` (≈ 24). In the codebase it is in `tools/apd_gauntlet/synthesis/loader.py:26`, as the Task 1 Interfaces line says, and `report/loader.py` has no `load_corpus`. `runs.py` imports it from `synthesis.loader`.
- Task 2 (`2de9b09`): the Step 1 test block is reformatted, not changed. Statements joined by `;` are split (ruff E702), and the over-long first assertion of `test_mutations_are_reported` is split into two `assert` lines. The assertions are the plan's.
- Task 2: an evidence pair with an empty artifact or an empty locator never excuses a lost finding (`_pointers` in `compare.py`). The plan says only "shares one of its `evidence_pairs`". The finding schema requires both parts, so such a pair comes only from an invalid record, and two invalid records would share `("", "")` and quietly excuse a lost critical or high finding, which Gate 1 must not allow. `test_evidence_pointer_without_artifact_or_locator_does_not_excuse` pins it.
- Task 2: `tests/test_measure_compare.py` has 14 tests beyond the plan's four. They cover the identical-run delta, new-finding counts, the order of lost findings, operator excuse over reassigned evidence, reassignment to a new capability, the `unknown` level, the `None` cases, and the `make_run` and `edit` fixtures.

## Pending operator steps

- Task 1: none (the task has no operator step).
- Task 2: none (the task has no operator step).

## WS2 summary

Final check on 2026-10-17 at `8a00e07`. WS2 is not complete. Task 1 is still unresolved after two review rounds, and Tasks 2 to 14 (13a included) have not started.

### Status by task

| Task | Status | Commits |
|---|---|---|
| 1 Matcher and run snapshot (A9.1) | Unresolved after 2 review rounds; two review items open (below) | `b9baeed`, `2d41ebc` (ledger), `b82f0bb`, `8a00e07` |
| 2 Pairwise delta; `tests/conftest.py` | Not started | none |
| 3 Attempts file, `summarize --record-attempts` (A9.4) | Not started | none |
| 4 `usage` from OpenTelemetry (A9.2, A9.7) | Not started | none |
| 5 Gates file and gate evaluation | Not started | none |
| 6 `compare-runs` (A9.5) | Not started | none |
| 7 Workflow records attempts (A9.3) | Not started | none |
| 8 Evaluation schemas, corpus loader, evaluator registry | Not started | none |
| 9 Findings evaluator, label template | Not started | none |
| 10 Freeze protocol, ADR-0028 | Not started | none |
| 11 `eval run` (A9.6) | Not started | none |
| 12 `calibrate` (A12.6) | Not started | none |
| 13 Metamorphic harness, `stride-table` suite | Not started | none |
| 13a Real pre-dedup counts (N20) | Not started | none |
| 14 Acceptance on the baselines (operator) | Not started; needs Tasks 1 to 13 and the Task 0.4 baselines | none |

The branch also holds `657511b` (ledger start), on base `c2be739`.

### Rulings and deviations

- Rulings: the ten Task 1 entries under "Rulings" above. No other task has rulings.
- Deviations: the two Task 1 entries under "Deviations" above. Three Task 1 rulings also depart from the plan text: the code-locator regex is `^code:([^:@]+)`, not the plan's `^code:([^:]+):`; `inputs_digest` adds `"<path>\0link:<link text>\n"` lines for links to directories and for dangling links (runs with neither keep the planned digest); and `RunLoadError` covers every read or parse failure, where the plan names only `yaml.YAMLError`.
- Carried forward to Task 2: `headline_overlap_pct` must test `not snapshot.headlines`, not `is None` (ruling on empty `headlines`).

### Open Task 1 review items

Both reproduce at `8a00e07` (Python 3.12) on scratch copies of the committed examples:

1. An unlistable directory under the run is skipped without an error. `load_corpus` and `_corpus_files` use `Path.glob("**/...")`, and glob skips a directory it cannot list. With `10-trustworthiness/` of the claim-event-bus example at mode 0, `load_run` returns 14 findings instead of 20 and raises nothing. A comparison would then report lost findings and fail Gate 1 for the wrong reason. The review's fix is to walk the run with `os.walk(run_dir, onerror=_walk_error)`, without following links, before trusting `load_corpus`'s result. A test would set a copied example's `10-trustworthiness/` to mode 0 (root-skip guard, chmod restored in `finally`) and assert that the error starts with the path `<run>/10-trustworthiness` followed by a colon.
2. An `OSError` from a stat call escapes as a raw exception. On Python 3.12, `Path.is_file()` and `Path.is_symlink()` re-raise `PermissionError`. With `40-synthesis/` of the acme-mobile-banking example at mode 0o644, `load_run` raises `PermissionError` for `40-synthesis/asset-graph.yaml`, not `RunLoadError`. Task 6 would then exit 1 with a traceback where it needs exit 2. The same applies to `p.is_file()` and `p.is_symlink()` in `inputs_digest`, and to the `report_file` and `deduped_file` checks in `load_run`. The review's fix is one helper that wraps these checks and turns `OSError` into `_unreadable(p, exc)`, with tests for `inputs/sub` at 0o644 holding a file and for `40-synthesis/` at 0o644.

### Pending operator steps

- Task 7 Step 6 (measure the change): needs Task 7 delivered and live, telemetry-instrumented runs. Run the master plan Task 1 set twice on that commit (names ending `-wf-r1`, `-wf-r2`), with this checkout's runner run by path (`Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`) or from a new session (A15.12). Then, for each example, run `apd-gauntlet compare-runs runs/<example>-baseline runs/<example>-wf --gates eval/gates.yaml`. Expected: exit 0 (`pass_with_gaps`, gates 4 and 5 unavailable against the 1.7.1 baseline), and every `-wf` run has `.apd-state/attempts.yaml`.
- Task 14 Steps 1 to 5 (acceptance): needs Tasks 1 to 13 delivered and the consolidated plan's Task 0.4 baselines, which are 1.7.1 runs (A15.1): `runs/<name>-baseline-r1` and `-r2` with their exports in `telemetry/`. Step 1 runs `usage` on every baseline run (exit 0, no "agent names redacted" warning, `unattributed` cost near zero). Step 2 is the noise floor, `compare-runs` of `-baseline-r1` against `-baseline-r2` per example; if a gate fails, record it in private notes and raise the set to three runs before WS3. Step 3 labels the three committed examples, writes `eval/findings/corpus.yaml` (`set: dev`) and runs `eval run`. Step 4 is `eval freeze` (generation 1). Step 5 commits `eval/findings` and `eval/frozen.yaml` only; nothing run-derived.
- Consolidated plan Task 3.2 (after Task 7 merges): rerun the baseline set twice on `next` (`-next-baseline-r1`, `-r2`), then compare the Task 1.5 run (`runs/apd-20261016-ws1-gate`) with the Task 0.4 claim-event-bus baseline and record the result as WS2 data.
- Owner: push the branch and open the PR to `next` once WS2 is complete. Nothing has been pushed.

### Not delivered

Not delivered, and not an operator step:

- Task 1: the two open review items above.
- Tasks 2 to 13 and 13a, all of it: `measure/compare.py`, `attempts.py`, `usage.py`, `gates.py`; the `eval` package (`corpus.py`, `evaluators.py`, `findings_eval.py`, `freeze.py`, `runner.py`, `calibrate.py`, `metamorphic.py`, `suites/stride_table.py`); the `run-attempts`, `eval-corpus` and `eval-labels` schemas; `data/decide/thresholds.yaml` and its package data in `pyproject.toml`; the CLI commands `summarize --record-attempts`, `usage`, `compare-runs`, the `eval` group, `calibrate` and `metamorphic run`; attempt recording in `.claude/workflows/apd-gauntlet.js` (and the `tests/test_workflow_runner_awaits.py` lists if a label or async helper changes); `eval/gates.yaml`; `docs/measuring-changes.md`; ADR-0028 and its cross-references in ADR-0017, `docs/ci-gate-model.md` and `docs/running-the-gauntlet.md`; the `docs/schema-evolution.md` and CHANGELOG entries; `tests/conftest.py`; the fixtures under `tests/fixtures/otel/`, `tests/fixtures/eval/` and `tests/fixtures/metamorphic/`; and N20's pre-dedup counts in `compute_metrics` and `build_rollups`.
- The plan's `.gitignore` change (`eval/results/`, `eval/local/`, `telemetry/`; Task 11, A9.6) is a step these workflow runs may not make, because they must not touch `.gitignore`. An operator, or a run allowed to edit that file, has to make it.

### Final quality gate

At `8a00e07`, with the repo venv (Python 3.12) and node v26:

- `ruff check tools/ tests/`: `All checks passed!`
- `mypy tools/`: `Success: no issues found in 67 source files`
- `python -m pytest -q -p no:cacheprovider`: `2291 passed in 49.43s`; with `--cov` as CI runs it, `Required test coverage of 85.0% reached. Total coverage: 88.54%`
- `apd-gauntlet lint-agents --agent-dir .claude/agents/`: `Lint clean: 22 agents checked.`
- `apd-gauntlet lint-skills --skill-dir .claude/skills/`: `Lint clean: 8 skills checked.`
- markdownlint-cli2 0.23.2 on the linted globs: `Summary: 0 issues in 0 files`
- `git status --porcelain` was empty before this entry, `git ls-remote origin refs/heads/feat/ws2-measurement-and-evaluation` prints nothing, and `git worktree list` shows only the main checkout.
