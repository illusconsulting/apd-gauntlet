# CI gate model: CI-enforceable vs locally-measured

**Status:** Active
**Date:** 2026-06-10
**Applies to:** apd-gauntlet v1.7.0 and the report-accuracy/UX remediation program.

The remediation program splits its Definition of Done into two tracks. This is
the authoritative reference every workstream's "Acceptance" section points at.

## Why a split

The original plan gated its entire Definition of Done on re-running a real
subject's gauntlet run. `runs/` is gitignored by policy (`.gitignore` — the run
"may contain a sensitive security review — never commit them"), so that gate is
unexecutable for anyone but the maintainer, and committing the run to satisfy CI
would leak a sensitive review. We resolve it with two tracks.

## The two tracks

| Track | What it measures | Where it runs | Fixtures it uses | Committed? |
|---|---|---|---|---|
| **CI-enforceable** | Structural, schema, and unit correctness. Does a committed synthetic artifact validate? Does a refactor stay byte-stable? Does the cache carry provenance? | Every PR, for everyone, via `.github/workflows/validate.yml` and `.github/workflows/python-tests.yml`. | Hand-authored synthetic fixtures only: `examples/apd-20260601-claim-event-bus/expected/`, `examples/apd-20260602-acme-mobile-banking/expected/`, `examples/apd-20260612-home-assistant/expected/`, the negative fixtures under `tests/fixtures/invalid/`, and `tests/fixtures/`. | Yes — these are synthetic, no real-subject data. |
| **Locally measured** | Holistic accuracy and insight: false-uncertainty promotion rate, redundancy collapsed, chokepoint-finding count, etc. | The maintainer's own machine, against a gitignored real run. | The maintainer's own run output (`40-synthesis/metrics.yaml`, produced by `compute_metrics`, `tools/apd_gauntlet/synthesis/metrics.py`). | **No.** All outputs of all real runs stay fully out-of-band — including bare metric counts and the baseline `B0`. Nothing run-derived is ever committed. |

## Version target: held at 1.7.0

The framework version is **held at 1.7.0** for the entire program. Workstreams
are sequenced by dependency phase, not by release version. Schema additions are
additive/optional and recorded as dated entries under the 1.7.0 section of
[Schema evolution](schema-evolution.md). The authoritative issue crosswalk
(prior "plan"/"notes" numbering → this program's workstreams) and the per-phase
sequencing live in the program design spec under `docs/superpowers/specs/` (the
remediation design doc, §4 "Issue crosswalk"), referenced from each workstream's
plan; it is not reproduced here to keep program-internal identifiers out of the
shipped reference docs.

## What CI enforces (the committed gates)

- `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/` exits 0 (`validate.yml`).
- `apd-gauntlet validate examples/apd-20260602-acme-mobile-banking/expected/` exits 0 (`validate.yml`).
- `apd-gauntlet validate examples/apd-20260612-home-assistant/expected/` exits 0 (`validate.yml`).
- `apd-gauntlet validate-domain pbm` (and any additional packs) exits 0 (`validate.yml`).
- `pytest tests/test_meta_schemas.py` — every schema is itself valid Draft 2020-12 (`validate.yml`).
- `ruff check tools/ tests/`, `mypy tools/`, `pytest --cov` with `fail_under = 85` (`python-tests.yml`).
- `python tools/check_report_template_freshness.py` — the precompiled report bundle matches its source (`python-tests.yml`).
- `python tools/check_kb_cache_freshness.py` — every fetched `tools/apd_gauntlet/data/*.json` carries provenance metadata (`python-tests.yml`; see [Schema evolution](schema-evolution.md)).
- markdownlint over `docs/**/*.md` (excluding `docs/superpowers/plans/**`), `.claude/**/*.md`, `tools/apd_gauntlet/data/domains/**/*.md`, and the root `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, and `CODE_OF_CONDUCT.md` (`markdown-lint.yml`).

## What is measured locally (never committed)

The maintainer runs the gauntlet against their own subject, reads
`40-synthesis/metrics.yaml`, and records a baseline `B0` **outside the
repository** (a private note). Run-over-run deltas are judged against `B0`. No
part of this — not the run, not the report, not even a bare count — is committed.
See [Local accuracy benchmark (out-of-band)](running-the-gauntlet.md#local-accuracy-benchmark-out-of-band)
and [ADR-0017](adrs/0017-local-only-accuracy-benchmark.md).

## See also

- [Running the gauntlet](running-the-gauntlet.md)
- [Infra reuse map](infra-reuse-map.md)
- [ADR-0017: local-only accuracy benchmark](adrs/0017-local-only-accuracy-benchmark.md)
