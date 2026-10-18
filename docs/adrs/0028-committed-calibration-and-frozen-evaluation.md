# ADR-0028: Committed calibration statistics and frozen held-out evaluation

**Status:** Accepted
**Date:** 2026-10-17
**Amends:** [ADR-0017](0017-local-only-accuracy-benchmark.md) (local-only accuracy benchmark)

## Context

[ADR-0017](0017-local-only-accuracy-benchmark.md) keeps every accuracy
measurement out of the repository: "not the run, not the report, not even a
bare count". That rule protects real review subjects, and it held while
accuracy was something the maintainer judged by hand against a private
baseline.

The 2.0 line needs two things that rule forbids.

1. **Calibrated thresholds that ship.** Decision models may decide an item on
   their own only above a threshold chosen on labelled data (`calibrate`, set
   for at least 98% precision on the labelled set). The program's registry
   fixes the entry format in `tools/apd_gauntlet/data/decide/thresholds.yaml`:
   the threshold, the precision and recall it reached, the number of labelled
   items `n`, the SHA-256 of the labels, and the provider, model and weights
   revision it was calibrated on. An engine that cannot ship those numbers can
   never ship a calibrated threshold, so every auto-decision would stay off.
2. **A held-out measurement that stays honest.** IaC context parameters,
   threat-catalog selection parameters and decision thresholds are all tuned
   on labelled data. GRAML (arXiv:2610.09605, §II-E) picks its threshold on
   validation data and then fixes it, and removes overlap between its datasets
   before measuring. The IaC spec (§13.2) states the same rule: tunables are
   tuned on development data only and frozen before held-out runs, and a
   tunable changed after a held-out run means a new held-out set. Nothing
   enforced it. A held-out number measured after tuning against held-out
   results reports a fit, not an accuracy.

## Decision

### What is committed

- `eval/gates.yaml`: the comparison gates `compare-runs` applies. It holds
  thresholds, no run data.
- Corpus manifests and labels that reference only committed fixtures (the
  synthetic examples under `examples/`) or public repositories pinned by a
  full commit SHA, for example `eval/findings/corpus.yaml` and
  `eval/findings/labels/`.
- `eval/frozen.yaml`: the SHA-256 of every tunables file and of the set, the
  freeze time and its generation.
- `thresholds.yaml` entries written by `calibrate`: `threshold`, `precision`,
  `recall`, `n`, `labels_sha256`, `provider`, `model`, `weights_revision` and
  `calibrated: true`.

This is a narrow exception to ADR-0017's "not even a bare count". A threshold
entry may come from labels over private runs, but it holds only aggregate
calibration statistics: a cut-off value, two ratios, an item count and a hash.
They describe how a decision model behaves on labelled items, and they carry
no subject data: no finding, title, evidence, asset name or path. The
registry's entry format requires them, and without them nothing can ship
calibrated.

### What stays local

- `eval/results/`, where `eval run` writes per-entry counts and metrics.
- `eval/local/`: corpus manifests and labels over private runs.
- `.apd-state/usage.yaml` and `.apd-state/attempts.yaml` of every run.
- Every run (`runs/`) and every telemetry export (`telemetry/`).

ADR-0017 applies to all of these unchanged.

### The freeze protocol

1. **Disjoint sets.** A corpus entry is in the `dev` set or the `heldout` set.
   The corpus loader refuses a run directory, or a `(repo.url, repo.commit)`
   pair, that appears in both sets, as GRAML deduplicates its held-out data.
2. **Tune on dev only.** Thresholds, context parameters and other tunables are
   changed against dev results. `calibrate` refuses labels marked
   `set: heldout` (exit 2).
3. **Freeze before held-out runs.** `apd-gauntlet eval freeze` records the
   SHA-256 of each tunables file (`thresholds.yaml` and every
   `tools/apd_gauntlet/data/*/context-params.yaml`) and of the whole set in
   `eval/frozen.yaml`. It writes nothing when the set is unchanged.
4. **Refuse a held-out run on a mismatch.** `eval run --set heldout` exits 2
   when `eval/frozen.yaml` is missing or when any tunables file was added,
   removed or changed since the freeze. The comparison is by content, never
   by modification time.
5. **A new held-out set after held-out use.** Each held-out result records the
   hash it ran under. When a result under `eval/results/` records the frozen
   hash, `eval freeze` exits 1 instead of re-freezing changed tunables. With
   `--new-heldout-set`, given once a new held-out set exists, it re-freezes and
   raises `generation` by one.

## Consequences

- Thresholds ship with their evidence. Anyone can read what a threshold
  reached and on how many items, and a calibration over committed labels can
  be checked against its `labels_sha256`.
- The held-out guard is code, and CI tests it on synthetic trees
  (`tests/test_eval_freeze.py`). It needs no network and no real run.
- Every tunables file is in one hash. A tunables file added after the freeze,
  such as code-flow's `data/codeflow/context-params.yaml`, changes the hash and
  makes every held-out `eval run` exit 2 until the next freeze, and that
  re-freeze needs `--new-heldout-set` when held-out results used the old hash.
  Before code-flow adds its parameters, `eval freeze` needs a per-family scope
  (`iac`, `catalog`, `decide`, `codeflow`), or code-flow takes a new held-out
  set of its own.
- A workstream that adds a tunables file adds its path to `TUNABLE_GLOBS` in
  `tools/apd_gauntlet/eval/freeze.py`, so the freeze covers it.
- Held-out results stay local, so the re-freeze check sees only the results on
  the machine that ran them. A fresh checkout has no `eval/results/`. The
  generation in the committed `eval/frozen.yaml` and review of any change to
  that file and to the tunables carry the rule between machines.
- A workstream may keep more local than this ADR allows, for example labels
  for the committed examples. It may not commit more.

## Alternatives considered

- **Freshness by modification time** (refuse when a tunables file is newer
  than `eval/frozen.yaml`). Rejected: a git checkout, a rebase or a copy
  resets mtimes, so the rule would refuse or accept at random. Content hashes
  give the same answer on every machine.
- **Freezing the commit SHA.** Rejected: any unrelated commit would break the
  freeze, and a modified working tree at the same commit would pass.
- **Committing nothing** (keep ADR-0017 as written). Rejected: thresholds could
  never ship calibrated, so every decision task would escalate every item, and
  the registry's threshold entry format could not be met.
- **Thresholds stored per run** (in each run's `.apd-state/` or run config).
  Rejected: runs are local and never committed, so a calibrated threshold
  would not ship with the engine, two runs could use different values, and
  nothing would tie a held-out run to the values frozen before it.
