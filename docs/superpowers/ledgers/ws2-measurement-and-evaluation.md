# WS2 execution ledger

Plan: `docs/superpowers/plans/2026-10-10-ws2-measurement-and-evaluation.md`; base commit `c2be739` (`origin/next`); started 2026-10-17.

## Rulings

- Task 1 review, `RunLoadError` coverage: `load_run` now raises `RunLoadError` naming the file for every read or parse failure. That covers `yaml.YAMLError`, a `ValueError` from PyYAML (an unquoted impossible date such as `2026-02-30`), text that is not UTF-8, and an `OSError`. It also covers any file whose top level is not a mapping (corpus files, `asset-graph.yaml`, `report-data.yaml`, `deduped-findings.yaml`) and any corpus record whose `id` is not a string. Such a record raises rather than being dropped, because a dropped record would look lost and fail Gate 1 for the wrong reason. When `load_corpus` fails and no corpus file is at fault, the original exception is re-raised.
- Task 1 review, `inputs_digest` and dotfiles: the digest keeps "every file", dotfiles included, as the plan says. A stray Finder `.DS_Store` makes Task 6 refuse with exit 2, which is loud and fixed by deleting the file. Skipping dotfiles would hide genuine inputs such as `.github/` or `.terraform.lock.hcl` and let runs over different inputs compare silently. Files are hashed in 1 MiB chunks. The walk uses `os.walk` with an error handler instead of `rglob`, because `rglob` skips an unreadable directory without saying so; an unreadable file or directory now raises `RunLoadError` naming it.
- Task 1 review, code locators: `_CODE_LOCATOR` is `^code:([^:@]+)`, the codebase's `code:<qualified_name>[:Lx-Ly][@sha]` grammar (`assemble_c4.py` `_CODE_LOCATOR_RE`, `report/transform.py` `_C4_CODE_LOCATOR_RE`), not the plan's `^code:([^:]+):`. The line range is optional in that grammar and the validator does not enforce it. Under the plan's regex a range-less locator fell back to the shared `artifact:code-evidence-index.yaml` key, which every code-citing record shares. Every code locator in the committed examples carries a range, so their keys do not change, and the plan's `test_asset_keys_code_artifact_and_graph` still passes.
- Task 1 review, `merged_from`: only string members count when a headline is expanded; an id with no string member expands to itself.
- Task 1 review, `merged-*` ids on asset-graph edges: declined, no change. The engine builds edges from `**/*.findings.yaml` with pre-dedup ids (`attack_path/build.py` `_load_all_records(run_dir, key="finding", glob="**/*.findings.yaml")` and `finding_id=f["id"]`), and `deduped-findings.yaml` does not match that glob. A `merged-*` edge id can only come from a hand edit the schema allows. None of the three examples has one, and the plan is silent. Revisit if a real run shows one.

## Deviations

- Task 1 (`b9baeed`): the Step 1 test block is reformatted, not changed. Statements joined by `;` are split onto separate lines (ruff E702), and long lines are wrapped to the 100-character limit. The assertions are the plan's.
- Task 1: register A9.1 places `load_corpus` in `report/loader.py` (≈ 24). In the codebase it is in `tools/apd_gauntlet/synthesis/loader.py:26`, as the Task 1 Interfaces line says, and `report/loader.py` has no `load_corpus`. `runs.py` imports it from `synthesis.loader`.

## Pending operator steps

- Task 1: none (the task has no operator step).
