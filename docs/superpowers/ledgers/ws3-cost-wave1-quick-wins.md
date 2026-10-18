# WS3 execution ledger

Plan: `docs/superpowers/plans/2026-10-10-ws3-cost-wave1-quick-wins.md`; base commit `c275c9f` (`feat/ws2-measurement-and-evaluation`, stacked on `origin/next` `c2be739`); started 2026-10-17.

## Rulings

- Task 3 review, applied: the retry is pinned as always-run. `test_rollup_failure_retry_carries_the_same_command` asserts `guard is False` on `post-tier4-retry-1`. With `alwaysRun: true` removed from that `pyStep` (the pre-task guarded `rollup-retry-1` state), it fails, and so does the new static `test_post_tier4_retry_repeats_the_first_call_options`.
- Task 3 review, applied, a deviation from the plan's code block: the advisory log moves out of the `else if` and runs after the retry block. It names each of `assemble-c4` and `canonicalize` that the last post-tier4 receipt reports failed. The plan's form logged nothing when the retry fixed `rollup` but `assemble-c4` or `canonicalize` still failed on it. The text changes from the plan's `… failed — advisory, as before WS3.` to `post-tier4: <steps> failed — advisory; the run continues.`, because operators read it and a plan's workstream name means nothing to them. Only logging changes: no dispatch, label or retry condition does. Tests: `test_advisory_post_tier4_failures_are_logged` (four cases, all failing before the fix), `test_no_advisory_log_without_a_named_advisory_failure` and `test_runner_logs_name_no_workstream`. The CHANGELOG's Task 3 entry says so.
- Task 3 review, harness: to let those tests read `log()` lines, `tests/js/workflow_dispatch_trace.mjs` also prints each one on stderr as `log: <message>` when `TRACE_LOGS` is set. Without it, stdout and stderr are as before, so the refusal tests that pin stderr's start and end are unaffected. `trace_raw` takes `logs=True` and drops an inherited `TRACE_LOGS` otherwise.
- Task 3 review, declined: one shared options object for both post-tier4 calls. The plan writes two `pyStep('post-tier4', {…})` calls, and `test_post_tier4_outputs_label_includes_metrics` reads the first call's inline literal. The drift the reviewer points at is covered instead: the new static test checks that the two literals differ only in `label`, and the trace test pins the retry's guard.
- Task 3 review, declined: `stepFailed` reading a failed receipt that names no step as a failed rollup. The plan's code specifies `named.length === 0 ||`, and its `test_rollup_fallback_keys_on_rollup_step` requires `{"post-tier4": [], "post-tier4-retry-1": []}` to reach the synthesizer. The reviewer marks the cost as accepted.
- Task 3 review, no change: `pyStep`'s unused `noRunDir` and `positional` options stay, as Deviations already records.
- Task 3 review, applied: `docs/architecture.md` (the skills paragraph and the Phase 0 lifecycle line) now says the runner runs `build-domain-skill` as a step of `prepare-run`. `docs/running-the-gauntlet.md` lists `rollup` as a step of `post-tier4`.
- Task 3 review, declined: the double space in `plan_run`'s `prepare-run` outputs text when `domains` is empty. `run-config.schema.json` sets `domains` to `minItems: 1`, and `plan-run` validates `.apd-run.yaml` against it before it calls `build_plan` (`tools/apd_gauntlet/cli.py`, `plan_run_cmd`), so the CLI never builds that row. The old `validate-domain` row had the same text.

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
- Task 2a (`ef46786`), commit message: neither the plan's Task 2a nor the consolidated plan's N19 gives a commit step, so the commit uses `feat(cli): run manual-audit-prompts at closeout`, in Task 2's style.
- Task 2a, placement: "after `summarize`" puts the step between `summarize` and the final `validate`, so `closeout` runs `canonicalize`, `summarize`, `manual-audit-prompts`, `validate`. The final `validate` stays last because R1 calls it the "final `validate`", and Task 8's test reads `closeout_steps(...)[-1]` as the `validate` argv.
- Task 2a, "always-run": a composite already runs every constituent whatever an earlier one returned, so no new option was needed. `closeout` keeps Task 2's exit rule (the first failing step's code), so a run without `40-synthesis/deduped-findings.yaml` now ends `closeout: failed manual-audit-prompts` (exit 1), where it ended `ok` before. A workflow run reaches closeout only after the decomposed apply or the synthesizer fallback has written that file (the workflow comment "deduped-findings/-capabilities exist via the decomposed apply OR the fallback"). On a run that has synthesis output, a missing file already fails the final `validate` (checked on a scratch copy of the claim-event-bus example).
- Task 2a, files beyond the plan's list: `CHANGELOG.md`, because Task 2's Unreleased "Added" bullet lists closeout's steps and now names `manual-audit-prompts` and its output; and the `closeout` help text in `tools/apd_gauntlet/cli.py`, which now names four steps.
- Task 2a, docs: "the docs row" is read both ways. The `closeout` row in the CLI reference names `manual-audit-prompts`, and the reference gains a `manual-audit-prompts <run-dir>` row, because the command had none.
- Task 2a, tests beyond the plan's `test_closeout_runs_manual_audit_prompts`, which also checks that the example had no prompts file before the run and that the written file equals `render_prompts` of the run's deduped findings:
  - Task 2's tests updated: `test_closeout_order_and_attempts` (first four status lines), `test_closeout_bad_attempts_keeps_the_summarize_code` (`manual-audit-prompts` still runs after `summarize` fails) and `test_step_builders_pass_the_run_dir_in_every_argv` (the closeout argv).
  - New: `test_closeout_manual_audit_failure_is_named_and_validate_still_runs`, on the clean-run fixture, whose missing deduped findings are a real failure (no mock); and `test_runbook_closeout_row_names_manual_audit_prompts`.
- Task 3 (`b370e1c`), files beyond the plan's list, each to keep a doc true after the switch:
  - `docs/measuring-changes.md`, "Retries and audit iterations": it named the workflow's `summarize` step and showed `apd-gauntlet summarize runs/<id> --record-attempts`. It now names `closeout` and shows `apd-gauntlet closeout runs/<id> --record-attempts`, and the foreground-drive sentence names the `closeout` row. The phrases `test_runbook_attempts_section` pins are kept.
  - `docs/running-the-gauntlet.md`, "A tier gate failed": its first sentence said the runner runs `canonicalize` and then `validate --tier`. It now names `tier-gate`. Runner step 4 is left alone, because the plan names steps 1, 3 and 5.
  - `CHANGELOG.md`: Task 2's Added entry ended "The workflow does not run them yet."; that sentence is removed, and the new Changed entry describes the switch.
- Task 3, `tests/test_workflow_runner_awaits.py` beyond the plan's `EXPECTED_GREEN_LABELS` and three slices. Without these changes the red gates would never fire, because the responder keys would not match a label, and no prompt would be logged:
  - WS2's attempts helpers key on the `closeout` label (`SUMMARIZE_MARK` is now `CLOSEOUT_MARK`). `_recorded_attempts` runs the `closeout` command the prompt names. On an empty run directory the later closeout steps fail, so it checks the `closeout: summarize exit=0` status line and the attempts file, not exit 0.
  - `test_attempts_count_the_tier_repair_loop` and `test_halted_run_records_no_attempts` key their red gates on `tier-gate-` labels, and the halted run checks that `closeout`, not `summarize`, was never dispatched.
  - The red receipts' `agent` is `pystep:tier-gate`.
- Task 3, Task 1 tests updated in `tests/test_workflow_dispatch_trace.py`:
  - `test_schema_valid_identifiers_are_accepted` pins the `prepare-run … --domain pbm --domain fhir-r4` command.
  - `test_absent_framework_version_omits_the_flag` is replaced by `test_prepare_run_reads_framework_version_from_the_run_config`: with or without the key, no CLI command carries `--framework-version`, because `prepare-run` reads it from `.apd-run.yaml`.
  - `test_trace_records_phase_and_guard` uses the `tier-gate-10-trustworthiness` label.
- Task 3, the plan's test code is adapted for ruff with the assertions unchanged: `labels = lambda fail: …` (E731) becomes the helper `_labels`, `l` (E741) becomes `label`, long lines are wrapped (E501), and `BAD`'s comment moves to the line above.
- Task 3, `test_prepare_run_step_always_runs` also asserts that the workflow builds no `'--framework-version '` argument. It replaces the plan's two `build-domain-skill` tests, including the guard test whose bug (`--framework-version undefined`) can no longer occur.
- Task 3, workflow: the `post-tier4-retry-1` dispatch writes out the plan's `/* same opts */` in full, with the first call's outputs (the old `rollup-retry-1` listed only `nist-coverage.yaml`). The `pyStep` body is unchanged: the `noRunDir` and `positional` options stay, though no caller sets them now, and only their comment changes. The `pyStep` header comment now describes the per-step errors.
- Task 3, agent body: the per-step error rule is a paragraph in `## Final message (receipt only)`, before the closing schema sentence. A new heading would break `test_body_sections_and_job_rules`, which pins the three headings and the closing sentence.
- Task 3, tests beyond the plan's:
  - `tests/test_workflow_dispatch_trace.py`:
    - the dispatch totals (18, 18, 36);
    - every composite always runs;
    - the JS `POST_TIER4_STEPS` equals `post_tier4_steps` names;
    - a rollup retry that succeeds carries the same command and phase and calls no synthesizer;
    - a lone `canonicalize` failure stays advisory;
    - `rollup` named among several failures triggers the retry;
    - the repair loop's `-after-repair` and `-after-rerun` gates both go through `tier-gate` with the tier's phase.
  - `tests/test_cli_plan_run.py`: the tier-gate rows' refs, phases and gate text (`<ref>; on failure repair …`); `test_plan_run_composite_rows` (the `assemble-inventory` row right after `apd-intake`, `post-tier4` outputs with `c4-model.yaml` and `metrics.yaml`, `closeout` last, and no `build-domain-skill`, `validate-domain`, `rollup` or `summarize` row).
  - `tests/test_agent_apd_cli_runner.py::test_composite_status_lines_become_one_error_per_failed_step`.

## Pending operator steps

- Task 1 Step 6 (SCP, not performed: it needs live runs with telemetry). On this branch's head, run the master plan Task 1 set twice. Run the changed runner by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})` (A15.12), as `runs/<x>-ws3t1-r1` and `runs/<x>-ws3t1-r2`, with telemetry in `telemetry/<x>-ws3t1-r<k>.otlp.jsonl`. Then run, for each run and each example:

  ```bash
  apd-gauntlet usage runs/<x>-ws3t1-r<k> --otel telemetry/<x>-ws3t1-r<k>.otlp.jsonl
  apd-gauntlet compare-runs <prev> runs/<x>-ws3t1 --gates eval/gates.yaml
  ```

  `<prev>` is the last accepted runs on `next` before WS3. The consolidated plan's SCP form keeps telemetry under `~/apd-telemetry/` and adds `--strict` to `compare-runs`.

  Expected: every `compare-runs` exits 0 (`pass` or `pass_with_gaps`). In each `usage.yaml`, `by_agent` has `apd-cli-runner` and no `general-purpose`. The `cost_usd` that `compare-runs --json` reports per run is at or below `<prev>`. If a gate fails, do not merge. For the private PBM run, the ledger and the PR carry only gate ids, pass/fail and aggregate numbers. Statically, the Task 1 harness measures 45 dispatches on a clean HA-shaped run: 27 to `apd-cli-runner` and 18 LLM dispatches, as the plan's "WS1 + WS2 base" column says.
- Task 2: none. The plan says the task needs no operator step, because nothing dispatches the composites yet.
- Task 2a: none. Nothing dispatches `closeout` until Task 3, so no run exercises the new step yet; Task 3's SCP covers it.
- Task 3 Step 6 (SCP, not performed: it needs live runs with telemetry). Same as Task 1 Step 6, with the suffix `-ws3t3` and `<prev>` set to the `-ws3t1` runs. On this branch's head, run the master plan Task 1 set twice. Run the changed runner by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})` (A15.12), as `runs/<x>-ws3t3-r1` and `runs/<x>-ws3t3-r2`, with telemetry in `telemetry/<x>-ws3t3-r<k>.otlp.jsonl`. Then run, for each run and each example:

  ```bash
  apd-gauntlet usage runs/<x>-ws3t3-r<k> --otel telemetry/<x>-ws3t3-r<k>.otlp.jsonl
  apd-gauntlet compare-runs runs/<x>-ws3t1 runs/<x>-ws3t3 --gates eval/gates.yaml
  ```

  The consolidated plan's SCP form keeps telemetry under `~/apd-telemetry/` and adds `--strict` to `compare-runs`.

  Expected: every `compare-runs` exits 0 (`pass` or `pass_with_gaps`), and the `cost_usd` that `compare-runs --json` reports per run is at or below the `-ws3t1` runs. If a gate fails, do not merge; attach the `--json` output to the PR. For the private PBM run, the ledger and the PR carry only gate ids, pass/fail and aggregate numbers. Statically, the harness measures 36 dispatches on a clean HA-shaped run against 45 for `-ws3t1`: 18 CLI dispatches to `apd-cli-runner` (27 before), 6 of them with guard text (9 before), and 18 LLM dispatches. `pyStep(` call sites go from 32 to 24. These are the plan's "After Task 3" numbers, and `CLI_LABELS` is the plan's 18-label list. This SCP also covers Task 2a: each run that reaches closeout writes `40-synthesis/manual-audit-prompts.md` and `.apd-state/attempts.yaml`.
