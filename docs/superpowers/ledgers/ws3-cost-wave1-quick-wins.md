# WS3 execution ledger

Plan: `docs/superpowers/plans/2026-10-10-ws3-cost-wave1-quick-wins.md`; base commit `c275c9f` (`feat/ws2-measurement-and-evaluation`, stacked on `origin/next` `c2be739`); started 2026-10-17.

## Rulings

## Deviations

- Task 1 (`4736891`), files beyond the plan's list, each needed to keep a WS2 test green:
  - `docs/measuring-changes.md` gains the ``| `apd-cli-runner` | `cli-steps` |`` row, because `test_runbook_phase_table_matches_agent_phases` needs a row for every `AGENT_PHASES` entry. The sentence under the table now names `apd-cli-runner`.
  - `tests/test_measure_usage.py::test_agent_phases_is_the_planned_table`, WS2's pin of the whole map, gains `apd-cli-runner`.
  - `tests/test_workflow_runner_awaits.py`: `_recorded_attempts` found the summarize command as a prompt line that starts with `apd-gauntlet summarize`. It now reads the `COMMAND:` line. No dispatch label, parallel group or async helper changed, so `EXPECTED_GREEN_LABELS`, `LENS_GROUPS`, `ASYNC_HELPERS`, `PASS_THROUGH` and `CALLS` stay as they were (A15.21).
  - `AGENT_PHASES` keeps `general-purpose: cli-steps`. 1.7 runs used that worker for CLI steps, and the synthesis fallback's `run-state-fallback` breadcrumb still runs on it.
- Task 1, harness: `tests/js/workflow_dispatch_trace.mjs` prints the dispatch list on stdout even when the workflow throws. It then sets `process.exitCode = 3` and does not call `process.exit(3)`, because a pipe write can still be pending on macOS. The plan only says it exits 3 with the message on stderr. The extra output lets `test_refusal_names_the_key_and_comes_before_any_dispatch` check that a refusal comes before the first dispatch, which the Review Focus asks for.
- Task 1, agent body: the plan's Job rule lists the extra receipt lines as "(`REPORT AUDIT`, WS1's verbatim `resume_plan` copy, WS1's JSON error mapping)". The body names them by their receipt keys (`report_audit`, `resume_plan`, `errors`), because `pyStep` keeps those lines as they stand and they start with those keys.
- Task 1, agent body, the guard check: the agent has only Bash, and every command it runs must begin with `apd-gauntlet`, so it cannot list files. The body therefore judges the guard from the guard's own `apd-gauntlet validate` command. If that command does not show that every expected output exists and is valid, the step is NOT-DONE and the work command runs. The plan does not state this rule. It keeps the guard's "never skip on a partial file" direction: a guarded step re-runs an idempotent command rather than skipping on doubt.
- Task 1, tests beyond the plan's:
  - `tests/test_agent_apd_cli_runner.py`: the exact frontmatter block; the A9.8 pins that moved from `pyStep` to the body (`work command`, `short-circuited`, the always-run line, `RECEIPT AGENT`, the status and counts lines); the three sections and the Job rules; the manifest entry right after `apd-availability.md`; and the `docs/architecture.md` counts and row.
  - `tests/test_workflow_dispatch_trace.py`: nine refusal cases that name the key and come before any dispatch (the plan's three, plus `r/../../x`, a leading `-`, an uppercase domain, a non-string domain, `1.7`, an empty framework version); identifiers that match the schema; the `--framework-version` flag left out when the key is absent; phase and guard in the trace; a failing `cluster-candidates` whose retry also goes to the runner; and the CI test job's SHA-pinned Node 22 step.
  - The rewritten WS1 tests also pin the line order: the guard or always-run line, then `COMMAND:`, then `RECEIPT AGENT:`.
- Task 1, A9.20: the plan places it in Task 1 (Files, `.github/workflows/python-tests.yml`), and it ships in `4736891`. The `test` job gains `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020  # v7.0.0` with `node-version: "22"` before `pip install`. That is the SHA the `bundle-rebuild-diff` job already pins, so nothing was fetched to find it.
- Task 2 (`9930a32`), `prepare-run` checks its values: each domain (from `--domain` or `.apd-run.yaml`) and `framework_version` must fully match its `run-config.schema.json` pattern, and a `.apd-run.yaml` that is not a mapping is refused. Each case raises `click.UsageError` (exit 2) naming the key before any step runs. The plan does not ask for this. The values become argv of in-process commands, where a leading `-` parses as an option: a config domain `--out=elsewhere` would redirect the `build-domain-skill` output. The workflow refuses the same values before its first dispatch (Task 1). An unquoted `framework_version: 1.4` loads as a float and is refused too.
- Task 2, `run_composite` raises `ValueError` when `gate` names no step. `invoke` also returns the code that click returns in non-standalone mode for `ctx.exit(N)`, the one case the plan's three do not cover, and 0 when the command returns normally.
- Task 2, the plan's test code is adapted for ruff with the assertions unchanged: `codes = lambda …` (E731) is the helper `_codes`, `l` (E741) is `line`, and lines over 100 characters are wrapped (E501, with a `CONF` path constant). `GOOD_ATTEMPTS` is imported from `test_summarize`, as the plan says.
- Task 2, tests beyond the plan's: unparseable `.apd-run.yaml`; five refusal cases; `tier-gate --json` stdout is pure JSON in a real subprocess, where the runner reads it; the final status line of `tier-gate` and `post-tier4`; the `RuntimeError` traceback on stderr; `closeout` keeps `summarize`'s exit 2 for bad attempts JSON and still runs `validate`; the step builders' argv; one status line per step; the stdout redirect applies only to the flagged step; the unknown gate; and `invoke`'s exit codes for `--version`, an unknown command and a bad argument.
- Task 2, docs: besides the four CLI reference lines, one sentence after the block states the status-line contract.

## Pending operator steps

- Task 1 Step 6 (SCP, not performed: it needs live runs with telemetry). On this branch's head, run the master plan Task 1 set twice. Run the changed runner by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})` (A15.12), as `runs/<x>-ws3t1-r1` and `runs/<x>-ws3t1-r2`, with telemetry in `telemetry/<x>-ws3t1-r<k>.otlp.jsonl`. Then run, for each run and each example:

  ```bash
  apd-gauntlet usage runs/<x>-ws3t1-r<k> --otel telemetry/<x>-ws3t1-r<k>.otlp.jsonl
  apd-gauntlet compare-runs <prev> runs/<x>-ws3t1 --gates eval/gates.yaml
  ```

  `<prev>` is the last accepted runs on `next` before WS3. The consolidated plan's SCP form keeps telemetry under `~/apd-telemetry/` and adds `--strict` to `compare-runs`.

  Expected: every `compare-runs` exits 0 (`pass` or `pass_with_gaps`). In each `usage.yaml`, `by_agent` has `apd-cli-runner` and no `general-purpose`. The `cost_usd` that `compare-runs --json` reports per run is at or below `<prev>`. If a gate fails, do not merge. For the private PBM run, the ledger and the PR carry only gate ids, pass/fail and aggregate numbers. Statically, the Task 1 harness measures 45 dispatches on a clean HA-shaped run: 27 to `apd-cli-runner` and 18 LLM dispatches, as the plan's "WS1 + WS2 base" column says.
- Task 2: none. The plan says the task needs no operator step, because nothing dispatches the composites yet.
