# Measuring changes

This runbook is for anyone who changes the gauntlet and has to show what the
change did: that it kept the findings, and what it saved in tokens and cost. It
covers capturing a baseline, recording Claude Code's telemetry, summarising a
run's usage with `apd-gauntlet usage`, the retry and audit counts the workflow
records, comparing runs with `apd-gauntlet compare-runs`, scoring runs against
reviewed labels with `apd-gauntlet eval`, calibrating decision thresholds with
`apd-gauntlet calibrate`, and checking with `apd-gauntlet metamorphic` that
changes which should not matter leave the results alone.

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
as `/apd-gauntlet:run` does) or start a new session. A workflow run on the 2.0
line ends with `.apd-state/attempts.yaml` in its run directory (see
[Retries and audit iterations](#retries-and-audit-iterations)); the 1.7.1
baseline runs have none.

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

The repository's `.gitignore` lists `telemetry/`, as it lists `runs/`,
`eval/results/` and `eval/local/`, because every export holds Bash commands,
tool input, `user.email` and account ids. Before the first capture, check that
Git ignores it: `git check-ignore telemetry/x.otlp.jsonl` prints the path when
it does. A checkout of an older branch (`main` and the 1.7.x releases) does
not list it. If the command prints nothing, add the line `telemetry/` to
`.git/info/exclude`, which Git reads but never commits, so that `git add -A`
cannot stage an export. You can also give `path` an absolute directory outside
the repository and pass that file to `--otel`.

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

## Retries and audit iterations

The workflow runner counts its lens retries, tier repairs and report-audit
attempts while it runs. At closeout its `summarize` step writes them to
`<run>/.apd-state/attempts.yaml`:

```bash
apd-gauntlet summarize runs/<id> --record-attempts '<json>'
```

`summarize` checks the object against `run-attempts.schema.json`, writes the
file, prints `Recorded attempts -> <path>` on stderr, and then prints the usual
summary. A rejected object writes nothing. The step always runs, so each
invocation that reaches closeout replaces an earlier file. `compare-runs` reads
the file for gates 4 and 5 (`first_pass_and_retries` and `audit_iterations`).

| Key | What it records |
|---|---|
| `recorded_by` | Who wrote the file: `workflow` for a workflow run |
| `lens_retries` | For each lens, how many times it was dispatched again (0 to 2) because its receipt was an error or never came back |
| `first_pass_invalid` | The lenses whose first receipt was an error or listed an output that failed schema validation |
| `skipped` | The lenses whose first receipt listed a `.skipped` output: `resume-plan` found their outputs complete, so they were not dispatched |
| `tier_gate_failures` | The tier directories whose first tier gate failed, before any repair |
| `tier_repairs` | For each tier directory, how many files went to the tier repair agent |
| `lens_reruns` | The lenses the tier repair loop re-ran from scratch, 1 each |
| `audit_iterations` | How many report-audit attempts the run made, the last one included (1 to 3) |

The counts cover one workflow invocation, from setup to closeout. The runner
keeps them in memory and writes them only at closeout, so an invocation that
halts or is interrupted writes no file. When you invoke the runner again on
such a run, `resume-plan` reports the lens steps that are already complete. The
runner skips them and lists them under `skipped`, and the retries of the
earlier invocation are not counted. `compare-runs` therefore reads gates 4 and
5 as `not_available` for any run whose `skipped` list is not empty. To measure
a configuration, run it from setup to closeout in one invocation.

A foreground drive, where you work through the `plan-run` checklist yourself,
records no attempts: its `summarize` step has no `--record-attempts`, so no
file is written, and gates 4 and 5 read `not_available` for that run, as for a
1.7 run.

To check a run, look for the file:
`cat runs/<name>-wf-r1/.apd-state/attempts.yaml`.

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
retries, and for a `plan-run` drive, which records no attempts (see
[Retries and audit iterations](#retries-and-audit-iterations)).

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

## Evaluate against labels

`compare-runs` says what changed between two runs. `apd-gauntlet eval` says how
good one run is: it scores runs against labels that a person reviewed, entry by
entry, and writes the counts and metrics to a local results file.

### Corpus layout

A corpus is a manifest, `eval/<area>/corpus.yaml` (schema `eval-corpus`), and
one labels file per entry under `eval/<area>/labels/` (schema `eval-labels`).
Each entry has an `id`, a `set` (`dev` or `heldout`), a finished run directory
(`run`), a repository pinned by its full commit SHA (`repo`), or both, and its
`labels` file. `run` and `labels` are relative to the manifest's directory, or
absolute.

```yaml
schema_version: 1
name: findings
entries:
  - id: claim-event-bus
    set: dev
    run: ../../examples/apd-20260601-claim-event-bus/expected
    labels: labels/claim-event-bus.yaml
```

A committed corpus references only committed fixtures (the synthetic examples
under `examples/`) or public repositories pinned by commit
([ADR-0028](adrs/0028-committed-calibration-and-frozen-evaluation.md)). A
corpus over private runs, with its labels, goes under `eval/local/<area>/`,
which Git ignores.

### Labelling

`eval label-template` writes a findings labels file for a run, with one
`unreviewed` item per finding:

```bash
apd-gauntlet eval label-template runs/<name> --entry <id> --out eval/local/findings/labels/<id>.yaml
```

Review every item. Set its verdict to `true_positive` for a real finding,
correcting `apd_goal` or `severity` where the run got them wrong, or to
`false_positive` for a wrong one, and add the true positives the run missed.
Evaluators refuse a labels file that still has an `unreviewed` item. The
command never overwrites an existing file.

### Dev and held-out sets

Tune on the `dev` set and measure once on the `heldout` set. The two sets must
be disjoint: the manifest loader refuses a run directory, or a repository at
one commit, that appears in both.

The tunables are the decision thresholds
(`tools/apd_gauntlet/data/decide/thresholds.yaml`) and every
`tools/apd_gauntlet/data/*/context-params.yaml`. The freeze protocol
(ADR-0028):

1. Tune on dev only, with `eval run --set dev` after each change.
2. Freeze: `apd-gauntlet eval freeze` records the SHA-256 of every tunables
   file in `eval/frozen.yaml`. It compares content, not modification times.
3. Measure: `eval run --set heldout` checks the freeze before it reads the
   corpus, and again after the last entry. It exits 2 when `eval/frozen.yaml`
   is missing or a tunables file was added, removed or changed since the
   freeze, and writes nothing.
4. Each held-out results file records the frozen hash (`frozen_sha256`). Once
   one does, `eval freeze` exits 1 instead of re-freezing changed tunables. A
   tunable changed after a held-out run means a new held-out set: build one,
   then run `eval freeze --new-heldout-set`, which raises the file's
   `generation` by one.

### Running

```bash
apd-gauntlet eval run eval/findings/corpus.yaml --set dev --evaluator findings
```

`eval run CORPUS --set dev|heldout --evaluator NAME [--root DIR] [--results-dir DIR] [--json]`
scores every entry of the set with the evaluator, in manifest order. The
`findings` evaluator ships with the engine. `--root` (default `.`) is the
repository whose `eval/frozen.yaml` and tunables are checked. The manifest and
every labels file are read before the first entry is scored, and an error in
any entry writes nothing.

The results file is `eval/results/<evaluator>/<set>-<timestamp>.yaml`, with the
time in UTC (`20261017T123045Z`); `--results-dir` replaces `eval/results`. It
records the evaluator, the set, the corpus (name, path and the SHA-256 of the
manifest), `frozen_sha256`, the engine version and the time, then one row per
entry (`counts`, `metrics` and `notes`) and the `totals`: the entries' counts
summed, and the metrics the evaluator computes from those sums (pooled, not
averaged; empty for an evaluator that reports no totals). A dev run records
the frozen hash when the tunables match the freeze, and `null` otherwise. An
existing results file is never overwritten.

Results stay local: Git ignores `eval/results/`, and the numbers are never
committed (ADR-0028). `eval freeze` looks for held-out results only under
`<root>/eval/results`, so `eval run --set heldout` warns when `--results-dir`
points elsewhere.

`--json` prints `path` (the results file), `result` (its content) and
`warnings`.

Exit codes:

- `0`: the results file is written.
- `1`: the results file exists or cannot be written.
- `2`: the manifest or a labels file cannot be read or is invalid, the
  evaluator is unknown or refuses an entry (an `unreviewed` item, labels for
  another entry), the set has no entries, or, for `--set heldout`, the
  tunables are not frozen or changed since the freeze.

## Calibrate a decision threshold

A decision task compares one value per item with a threshold. Finding QA flags
an item whose value is below its threshold, and an auto-decision task decides
an item whose score is above it. `apd-gauntlet calibrate` picks the threshold
from labelled decision records, so it rests on a measured precision instead of
a guess. Until a key is calibrated, it never decides on its own:
`tools/apd_gauntlet/data/decide/thresholds.yaml` ships as an empty mapping, so
the key has no entry there, or has a proposal entry that reads
`calibrated: false` (the finding-QA proposals that the decision layer appends).

### Decision labels

Decision records live in the runs
(`<run>/40-synthesis/decisions/<task>.<scope>.yaml`), and runs stay local, so
their labels go in `eval/local/decide/<key>.labels.yaml`, which Git ignores.
`<key>` is the threshold key, `<task>` or `<task>.<flag>`, for example
`finding-qa.unsupported`. The labels file is an `eval-labels` file of kind
`decisions`:

```yaml
schema_version: 1
kind: decisions
set: dev
task: finding-qa.unsupported
records:
  - path: ../../../runs/<name>/40-synthesis/decisions/finding-qa.10-trustworthiness.yaml
    items:
      - {ref: conf-1a2b3c4d, gold: true}
      - {ref: conf-5e6f7a8b, gold: false}
```

`path` is relative to the labels file, or absolute, and must name a record in
a run's `40-synthesis/decisions/` directory; the record's `task` must be the
key's task. Set `gold` to `true` when the item belongs to the class the
threshold selects. For a finding-QA flag, that means the flag should fire: for
`finding-qa.unsupported`, the cited excerpts do not support the finding. For an
auto-decision task, it means the item can be decided without review. Every
`ref` must be an item of its record, and each item is labelled once. Items with
`outcome: error`, and items with no value (for `finding-qa.lens_drift`, an item
whose finding is no longer in the run), are skipped, and the command says how
many.

Two keys ship with a value: `finding-qa.unsupported` (the probability that the
excerpts support the claim) and `finding-qa.lens_drift` (the probability of the
finding's own goal). Both flag values below the threshold. The decision tasks
register their own keys when they ship.

### Choosing the threshold

```bash
apd-gauntlet calibrate <task> --labels <file> --target-precision 0.98
```

`calibrate TASK --labels FILE --target-precision P [--min-support N] [--thresholds PATH]`
takes the labelled items' values and tries a cut at the midpoint between each
pair of neighbouring distinct values, so no labelled value sits on a cut. A cut
qualifies when at least `--min-support` items (default 10) fall on the selected
side and its precision on them is at least P. Of the cuts that qualify, it
takes the one with the highest recall, then the highest precision. The target
of 0.98 is a proposal. The threshold written is the cut rounded to six decimal
places, unless rounding would carry it onto a labelled value.

The entry goes to `--thresholds`, by default the packaged
`tools/apd_gauntlet/data/decide/thresholds.yaml`. Every other entry is kept:

```yaml
finding-qa.unsupported:
  calibrated: true
  labels_sha256: <SHA-256 of the labels file>
  model: <model id>
  n: 212
  precision: 0.9811
  provider: <provider>
  recall: 0.6512
  threshold: 0.18
  weights_revision: null
```

`n` is the number of labelled items used, and `labels_sha256` the SHA-256 of
the labels file's bytes. `provider`, `model` (the id the provider returned) and
`weights_revision` come from the records. A threshold holds only for the model
it was calibrated on, so `calibrate` refuses labelled records that mix models.
An entry holds one model: calibrating the same key on another model's records
replaces it. The entry's numbers are aggregate statistics that may be
committed ([ADR-0028](adrs/0028-committed-calibration-and-frozen-evaluation.md));
the labels and the records stay local.

### When no threshold qualifies

When no cut qualifies, `calibrate` prints
`no threshold reaches precision ≥ P with at least N predicted positives (best: Q); <task> stays uncalibrated`,
exits 1 and leaves the file as it was. `Q` is the best precision reached by a
cut with enough support, or `none` when no cut had N predicted positives. Label
more items, above all in the region the threshold would select, or leave the
key uncalibrated. Lowering `--min-support` to get a threshold defeats the
floor: a threshold that rests on a few items proves nothing.

### Freeze after calibrating

Calibrate on dev labels only. `calibrate` refuses labels marked `set: heldout`
(exit 2), because thresholds are tuned on dev data and frozen before held-out
runs. A calibration changes a tunable, so run `apd-gauntlet eval freeze` before
any held-out run ("Dev and held-out sets" above); `calibrate` prints that
reminder after it writes.

Exit codes:

- `0`: the entry is written; the command prints it.
- `1`: no threshold qualifies, or the thresholds file cannot be written. The
  file is left as it was.
- `2`: `TASK` has no value spec (the message lists the known keys); `P` is not
  a number in (0, 1] (`nan` included); the labels
  file cannot be read, is invalid, is not of kind `decisions`, is for another
  key or has `set: heldout`; a record cannot be read, is not in a run's
  `40-synthesis/decisions/`, is for another task, lacks a provider or model,
  or lists a ref twice; a `ref` is not an item of its record or is labelled
  twice; the records mix models; no labelled item has `gold: true`; or the
  existing thresholds file cannot be read or is not a mapping.

## Behaviour-preserving transformations

Some changes to an input should never change the results: renaming a
component, reordering the rows of a table, moving a column. A metamorphic suite
checks that. It applies each such transformation to a fixture and compares the
results with the untouched fixture's. No model runs, so a suite can run in CI.

```bash
apd-gauntlet metamorphic run --suite stride-table
```

`metamorphic run --suite NAME [--root DIR] [--json]` runs every case of the
suite: each transformation on each fixture. Fixtures are directories relative
to `--root` (default `.`, so run it from the repository root). The transformed
copies go to a temporary directory that is removed afterwards. `--json` prints
the suite name and every case with its `fixture`, `transform`, `status`,
`missing` and `extra` result tuples, and `reason`.

### Suites

A suite (`apd_gauntlet.eval.metamorphic.Suite`) declares:

- `name`, which `--suite` takes.
- `fixtures`: directories relative to the root.
- `transforms`: name to function. A transform copies the fixture into an empty
  directory, changes the copy, and returns a rename map from each new name to
  the original one (`{}` when it renames nothing).
- `extract`: reads a fixture directory and returns the results as a set of
  tuples of strings.
- `normalise`: maps the transformed copy's results back through the rename
  map, so a renamed element compares equal to the original.
- `known_non_invariant`: the allowlist, keyed by `(transform, fixture)`, each
  with a reason.

The engine ships one demonstration suite, `stride-table`, over the parser
behind `parse-threat-model`. Its fixture is
`tests/fixtures/metamorphic/stride-table/basic/threat-model.md`, a STRIDE
table, and its results are the parsed entries as (element, STRIDE letter,
threat, goals). Its transforms are `rename-elements` (each element becomes
`element-<n>`, in row order), `reorder-rows` (the data rows reversed) and
`reorder-columns` (the six STRIDE columns reversed, the Element column kept
first).

Each case ends in one of four statuses:

- `holds`: the normalised results are the same.
- `violated`: they differ. The report lists the `missing` tuples (only in the
  untouched fixture's results) and the `extra` ones (only in the copy's).
- `allowlisted`: they differ, and the allowlist lists the case.
- `stale_allowlist`: the allowlist lists the case, but it holds.

### Adding a suite

A new suite, such as the IaC pipeline's or the code-flow layer's, lives in its
own module that calls `register_suite(suite)` at import. Add the module to
`BUILTIN_SUITE_MODULES` in `tools/apd_gauntlet/eval/metamorphic.py`, so
`metamorphic run` loads it. `register_suite` refuses a name that is taken, a
suite with no fixtures or no transforms, two fixtures with the same directory
name, a transform name that is not a plain directory name, and an allowlist
entry that names no case of the suite or has no reason.
When `extract` cannot run (a tool the suite needs is not installed), it raises
`MetamorphicError`, and the command exits 2 with its message.

### The allowlist

A known non-invariance, such as a scanner that reads one file format
differently, is listed explicitly in the suite's `known_non_invariant` with a
reason. A difference that the gauntlet's own code causes is a defect to fix,
not an entry to add. An entry whose case holds again is reported as
`stale_allowlist` and fails the run, so remove it; the list then names only
the differences that still exist.

Exit codes:

- `0`: every case holds or is allowlisted.
- `1`: a case is violated, or an allowlist entry is stale.
- `2`: `NAME` is not a registered suite (the message lists the registered
  ones), a fixture is not a directory under the root, or the suite cannot run:
  a tool it needs is missing, a file cannot be read or written, or a transform
  or `extract` returns the wrong type.
