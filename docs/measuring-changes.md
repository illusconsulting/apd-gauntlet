# Measuring changes

This runbook is for anyone who changes the gauntlet and has to show what the
change did: that it kept the findings, and what it saved in tokens and cost. It
covers capturing a baseline, recording Claude Code's telemetry, and summarising
a run's usage with `apd-gauntlet usage`.

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
