# Measuring changes

This runbook is for anyone who changes the gauntlet and has to show what the
change did: that it kept the findings, and what it saved in tokens and cost. It
covers capturing a baseline, recording Claude Code's telemetry, summarising a
run's usage with `apd-gauntlet usage`, and comparing runs with
`apd-gauntlet compare-runs`.

## Why measure

Model output varies from run to run, and a change that cuts tokens can quietly
drop findings. So a change to what the agents see or do is measured before and
after: the same inputs, run on the old code and on the new code, then compared.
[ADR-0017](adrs/0017-local-only-accuracy-benchmark.md) splits that work in two:

- CI checks structure (schemas, byte-stable output, provenance) against
  committed synthetic fixtures. It never runs a model and never touches the
  network.
- Accuracy and cost are measured locally, on real runs. Those runs, their
  telemetry and every number taken from them stay on your machine and are never
  committed.

Run each configuration twice. Model output varies between runs, so one
comparison can't tell a regression from noise; two runs of the same
configuration show how far the output moves on its own.

## Capture a baseline

A baseline is a set of runs made on the code you are about to change. For the
2.0 line it is the 1.7.1 release: `pip install apd-gauntlet==1.7.1` and the
1.7.1 plugin.

1. Start the Collector and export the telemetry variables (see
   [Telemetry](#telemetry)).
2. Run the baseline set twice: the three committed examples under `examples/`,
   plus one private PBM run. Scaffold each example run from its
   `inputs/`, with the domains listed in its `expected/.apd-run.yaml`:

   ```bash
   apd-gauntlet init-run apd-20260601-claim-event-bus-baseline-r1 \
     --inputs examples/apd-20260601-claim-event-bus/inputs --domain pbm
   ```

   Then run the gauntlet as usual (see [Running the Gauntlet](running-the-gauntlet.md)).
3. Keep each run directory and its telemetry export under a name ending
   `-baseline-r1` or `-baseline-r2`: `runs/<name>-baseline-r1/` and
   `telemetry/<name>-baseline-r1.otlp.jsonl`.
4. Check every run. `apd-gauntlet validate runs/<name>-baseline-r1` prints
   `Clean.`, and the export holds `claude_code.api_request` events
   (`grep -c claude_code.api_request telemetry/<name>-baseline-r1.otlp.jsonl`
   prints a number above 0).
5. Summarise each run's usage (see [Usage](#usage)).
6. Compare the changed runs with the baseline (see [Compare runs](#compare-runs)).

Run the changed code the same way, twice, under its own suffix (for example
`-wf-r1` and `-wf-r2`). A Claude Code session runs the copy of the
`apd-gauntlet` workflow registered when the session started. To run a changed
runner, run it by path
(`Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`,
as `/apd-gauntlet:run` does) or start a new session.

## Telemetry

With telemetry on, Claude Code exports one `claude_code.api_request` event per
model request. The event carries the agent name, the model, four token counts
and the cost. `apd-gauntlet usage` reads those events.

### Variables

Export these in the shell that launches Claude Code:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_LOG_TOOL_DETAILS=1
```

- Set the protocol and the endpoint explicitly: Claude Code has no default
  OTLP protocol.
- `OTEL_LOG_TOOL_DETAILS=1` makes custom agents, the gauntlet's among them,
  report their real names. Without it they report as `custom`, and `usage`
  cannot tell which phase their cost belongs to. Real agent names on
  `api_request` events also need Claude Code 2.1.273 or later.
- The console exporter (`OTEL_LOGS_EXPORTER=console`) is not parsed. Its output
  is not JSON, and `usage` refuses it with exit 2.

Every export holds the account e-mail address (`user.email`) and the
organization id whenever Claude Code is signed in, and by default the account
ids (`user.account_uuid`, `user.account_id`). `OTEL_LOG_TOOL_DETAILS=1` adds
Bash commands, tool input, and the names of MCP servers, tools, skills and
workflows. Treat every export like the run itself: keep it local and never
commit it.

### Collector

Run a local OpenTelemetry Collector with an OTLP HTTP receiver and a `file`
exporter. The `file` exporter ships in the Collector's contrib distribution
(`otelcol-contrib`), and it writes each export batch as one line of OTLP/JSON,
the format `usage` reads. Save this configuration outside the repository as
`collector.yaml`, with `<run-id>` replaced by the run's name:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 127.0.0.1:4318
exporters:
  file:
    path: telemetry/<run-id>.otlp.jsonl
service:
  pipelines:
    logs:
      receivers: [otlp]
      exporters: [file]
```

Create `telemetry/` in the repository root and start the Collector from there,
so the relative path lands in it:

```bash
mkdir -p telemetry
otelcol-contrib --config /path/to/collector.yaml
```

Before the first capture, check that Git ignores `telemetry/`:
`git check-ignore telemetry/x.otlp.jsonl` prints the path when it does. If it
prints nothing, add the line `telemetry/` to `.git/info/exclude`, which Git
reads but never commits, so that `git add -A` cannot stage an export. You can
also give `path` an absolute directory outside the repository and pass that
file to `--otel`.

Restart the Collector with a new `path` before each run, so that every run has
its own file. The receiver listens on 127.0.0.1 only. If the file also receives
metrics or traces, `usage` skips them.

## Usage

```bash
apd-gauntlet usage runs/<name>-baseline-r1 --otel telemetry/<name>-baseline-r1.otlp.jsonl
```

Stop the Collector before you run `usage`, so that the export is complete and
`source.sha256` describes the same bytes that were counted.

- `--workflow-run ID` counts only events whose `workflow.run_id` is `ID`.
- `--json` prints the written summary as JSON on stdout.

Exit codes:

- `0`: `<run>/.apd-state/usage.yaml` was written.
- `1`: no `api_request` event is left after filtering, or
  `<run>/.apd-state/usage.yaml` cannot be written (for example, `.apd-state`
  is a file). Nothing is written, and an earlier `usage.yaml` is kept.
- `2`: the export is not OTLP/JSON, a decision record under
  `40-synthesis/decisions/` cannot be read, or the directory is not a run
  directory (it has no `.apd-run.yaml`).

### Output

`<run>/.apd-state/usage.yaml` holds:

| Key | Contents |
|---|---|
| `schema_version`, `generated_by` | `1` and `apd-gauntlet usage` |
| `source` | the export's `file` and `sha256`, the number of `api_requests` in it, and the ids of its `sessions` and `workflow_runs` |
| `filter` | `workflow_run`: the `--workflow-run` value, or `null` |
| `totals` | `requests`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` and `cost_usd` |
| `by_agent` | the same counters for each agent name as reported, plus the agent's `phase` |
| `by_phase` | the same counters for each phase |
| `decision_models` | decision-model spend, from the `usage` block of every `40-synthesis/decisions/*.yaml` record: `totals` of `calls`, `input_tokens` and `cost_usd`, and the same counters `by_task` and `by_cost_basis`. The totals are zero and both mappings empty when the run has no records |
| `cost_usd_all` | `totals.cost_usd` plus `decision_models.totals.cost_usd` |
| `warnings` | the warnings below |

A request's cost is its `cost_usd_micros` attribute when present, otherwise its
`cost_usd`. A request with neither counts as 0 and is reported in `warnings`.
`cost_usd` in the file is the sum in micro-dollars divided by 1,000,000.

### Agents and phases

Telemetry carries no phase, so `usage` maps the agent name to one. A
`<plugin>:` prefix is ignored: `apd-gauntlet:apd-report-writer` counts as
`apd-report-writer`. An event without `agent.name` comes from the launching
session and counts as `main`.

| Agent | Phase |
|---|---|
| `apd-intake` | `intake` |
| `apd-code-recon` | `code-recon` |
| `apd-threat-model-author` | `threat-model-author` |
| `apd-threat-model-recon` | `tm-recon` |
| `apd-confidentiality` | `tier-1` |
| `apd-integrity` | `tier-1` |
| `apd-availability` | `tier-1` |
| `apd-distributed` | `tier-2` |
| `apd-resilient` | `tier-2` |
| `apd-ephemeral` | `tier-2` |
| `apd-authenticity` | `tier-3` |
| `apd-non-repudiation` | `tier-3` |
| `apd-immutability` | `tier-3` |
| `apd-cluster-adjudicator` | `synthesis-adjudicate` |
| `apd-synthesizer` | `synthesis-fallback` |
| `apd-threat-model-evaluator` | `tmeval` |
| `apd-attack-path-analyzer` | `apath` |
| `apd-report-writer` | `synthesis-report` |
| `apd-report-auditor` | `synthesis-audit` |
| `apd-domain-auditor` | `domain-improvements` |
| `apd-tier-repair` | `canonicalize` |
| `general-purpose` | `cli-steps` |
| `main` | `session` |

Any other agent, `custom` and `third-party` included, counts under
`unattributed`. `cli-steps` is the general-purpose worker that runs each CLI
step of the workflow, and `session` is the launching session itself; neither is
a workflow phase.

### Warnings

`usage` prints each warning on stderr and also stores it under `warnings`:

- `agent names redacted on N requests ('custom'/'third-party'): set OTEL_LOG_TOOL_DETAILS=1 and use Claude Code 2.1.273 or later`.
  The cost of those requests lands in `unattributed`. Capture the run again
  with the variable set and a current Claude Code.
- `multiple workflow runs in this file (<ids>): pass --workflow-run`. The
  export covers more than one workflow run. `source.workflow_runs` lists their
  ids; run `usage` again with `--workflow-run <id>` for the run you are
  summarising.
- `N requests carried no cost attribute`. Those requests count as 0 in every
  `cost_usd`.

A clean baseline export gives no redaction warning, and its `unattributed`
cost is close to zero.

## Compare runs

```bash
apd-gauntlet compare-runs runs/<name>-baseline runs/<name>-wf --gates eval/gates.yaml
```

`compare-runs BASELINE CANDIDATE [--json] [--gates eval/gates.yaml] [--excuse VALUE]... [--strict]`
compares a candidate with a baseline and applies the comparison gates. It reads
only the run directories, never the network.

### Run sets

Each side is a run directory, or the name of a run set. A run directory is one
that holds `.apd-run.yaml`. For a name, `compare-runs` takes `<name>-r1`,
`<name>-r2` and so on, up to the first number that is missing, so
`runs/<name>-baseline` means `runs/<name>-baseline-r1` and
`runs/<name>-baseline-r2`. Name both runs of a configuration that way and pass
the name without the suffix.

Every baseline run is compared with every candidate run: two runs a side give
four pairs.

### Matching findings

Findings, and capabilities, are matched one to one across each pair. Two
records match when they have the same `apd_goal`, share at least one asset key,
and their titles reach a token Jaccard of at least 0.5 (stopwords left out,
case ignored). Asset keys come from the record's evidence (the code symbol of a
`code:` locator, else the normalised artifact path) and from the asset-graph
nodes its edges target. Pairs are taken greedily in a fixed order, so the same
runs always give the same matches.

A baseline record without a match is missing, and a candidate record without a
match is new. A missing finding of severity `critical` or `high` is lost.

### Excuses

A lost finding is excused in two cases:

- `evidence_reassigned:<id>`: a new candidate finding or capability `<id>`
  cites one of the lost finding's evidence pointers (the same artifact and
  locator). The evidence moved to another record.
- `operator`: you passed `--excuse <finding-id>`, after reviewing the loss.

`--excuse` is repeatable. A value `<gate-id>:<reason>` whose prefix is a gate id
in the gates file excuses that whole gate instead. The gate then reads
`excused` and counts as a pass. The JSON entry carries `excuse: <reason>`, and
the text report prints `EXCUSED (<reason>)`. The reason must not be empty. When
one gate id is the start of another (a gate id may contain `:`), the longer id
wins. Any other value is a finding id; finding ids never contain `:`. An
excused finding id that is not lost in any pair excuses nothing, and an excused
gate that passed stays `pass`; `compare-runs` warns about both. Give the reason
for every excuse in the PR description.

### Medians

- `unexcused_lost_critical_high` and `severity_agreement_pct` are the median
  over all pairs. A pair without matched findings has no severity agreement and
  is left out.
- The per-run values (blocked rate, the attempts counts and the usage cost) get
  a median per side, reported as `baseline_<metric>` and `candidate_<metric>`.
  A side's median is not available when any of its runs lacks the value, so a
  gate never judges part of a side.
- `blocked_rate_abs_delta_pts` is the absolute difference of the two blocked-rate
  medians. Each attempts delta (`first_pass_validator_errors_delta`,
  `lens_retries_delta`, `tier_repairs_delta`, `lens_reruns_delta`,
  `audit_iterations_delta`) is the candidate median minus the baseline median.

The usage cost (`cost_usd`, and `cost_usd_all` with the decision models) is
reported, per run under `runs` and as side medians, but never gated.

### Gates

`eval/gates.yaml` holds the five proposal gates. Change a threshold only by PR,
with the rationale in the PR description.

| Gate | Passes when |
|---|---|
| `no_lost_critical_high` | `unexcused_lost_critical_high` is 0 |
| `severity_agreement` | `severity_agreement_pct` is at least 90 |
| `blocked_rate` | `blocked_rate_abs_delta_pts` is at most 5 |
| `first_pass_and_retries` | the first-pass, retry, tier-repair and lens-rerun deltas are each at most 0 |
| `audit_iterations` | `audit_iterations_delta` is at most 0 |

A gate whose data is missing reads `not_available`, with the reason, and is
never printed as passed. Gates 4 and 5 (`first_pass_and_retries` and
`audit_iterations`) read `not_available` against every 1.7 baseline, 1.7.1
included, because 1.7 runs record no `.apd-state/attempts.yaml`. They also read
`not_available` when a run was resumed, because a resumed run under-counts its
retries.

The overall status is `fail` when any gate fails, else `pass_with_gaps` when
any gate is `not_available`, else `pass`. Without `--gates` the status is
`delta_only`. `--strict` makes `pass_with_gaps` exit 1, so use it only when
both sides recorded attempts.

### Exit codes

- `0`: no gate failed (`pass`, or `pass_with_gaps` without `--strict`), or no
  gates were applied (`delta_only`).
- `1`: a gate failed, or a gate is `not_available` under `--strict`.
- `2`: a side does not resolve (the message names `-r1` and `-r2`), both sides
  share a run directory, a baseline run has no findings (a scaffold or an
  unfinished run), two runs have different `inputs/`, a run fails to load, or
  the `--gates` file cannot be read. Never compare against nothing: capture the
  baseline first (see [Capture a baseline](#capture-a-baseline)).

### Report

The text report lists the runs of each side, one line per pair (matched,
missing and new findings by severity, severity and maturity shifts, headline
overlap), each lost critical or high finding with its excuse, the values, each
distinct reason a value is missing, the gate table (`PASS`, `FAIL`,
`NOT AVAILABLE` with the reason, or `EXCUSED (<reason>)`) and the warnings. Its
last line is `RESULT: <status>`, followed by the ids of the failed, unavailable
and excused gates. Control characters and line separators in a title, an id or
a path are printed as escapes (`\n`, `\x1b`), so text from a run cannot add a
line to the report or send an escape sequence to your terminal. Read the status
from the last line, or from `status` in the JSON.

`--json` prints the same comparison as JSON, with the keys `status`,
`baseline`, `candidate`, `pairs`, `runs` (keyed by each run's path as you gave
it), `values`, `gates` and `warnings`.

`compare-runs` warns when:

- the gates are applied to a single run on a side (run each configuration
  twice);
- an excused finding id is not lost in any pair;
- an excused gate passed, so its excuse is not used;
- a run has a finding whose severity is not one of `informational`, `low`,
  `medium`, `high` and `critical` (in a baseline run such a finding is never
  counted as a lost critical or high finding; in a candidate run it never
  agrees with a baseline severity on that scale);
- a run has no `inputs/`, so its inputs cannot be checked against the others;
- `--strict` is given without `--gates`.
