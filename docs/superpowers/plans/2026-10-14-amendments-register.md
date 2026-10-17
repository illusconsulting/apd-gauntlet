# Amendments Register for the 2026-10 Program Plans (2026-10-14)

Companion to `docs/superpowers/plans/2026-10-14-consolidated-execution-plan.md`. Each entry changes a plan or spec on `next` before that plan is executed. Phase 2 (Task 2.1) applies them in one docs PR, in the order of this file.

**Conventions.**

- Entries continue the master plan's §A numbering: A1–A3 below make the master plan's A1–A3 concrete; A4–A6 stand as written; A7–A15 are new.
- "Old → New" gives exact replacement text. Where a plan cites a line number, the number is the one on `origin/next` (`0642673`); for the threat-catalog entries `Lphys (nl N)` gives the physical line and the number plain `nl` prints.
- Code anchors refer to `fix/ws1-1.7.1` merged with `main` (the code every `next` plan will meet). Locate edits by function, label or heading; line numbers are hints.
- "OP" marks an operator step (live runs, keys, labelling); everything else is CI-testable.

---

## A1–A3. Master-plan amendments, made concrete (LA1–LA3; not yet applied on `next`)

Evidence: only the PR #29 commits touch the three LA plans; none of `consent.json[`, `load_threshold`, `thresholds.yaml`, `calibrated`, `prepare-run`, `tier-gate`, `resume-plan`, `repair.md`, `apd-tier-repair`, `write_attempts`, `register_doctor_check` appears in them.

### A1 — LA1 (`2026-10-10-local-apps-plan1-config-keys-decision-models.md`)

- **A1.1 Global Constraints (finding-QA thresholds bullet).** Old: "Finding-QA thresholds: `lens_drift` 0.5, `unsupported` 0.3, `severity_delta` 1.0." New: "Finding-QA thresholds load through `decide.policy.load_threshold` from `tools/apd_gauntlet/data/decide/thresholds.yaml` (WS2 `THRESHOLDS_PATH`) under keys `finding-qa.lens_drift`, `finding-qa.unsupported` and `finding-qa.severity_delta`. LA1 appends the proposals 0.5, 0.3 and 1.0 as `{threshold, precision: null, recall: null, n: 0, labels_sha256: null, calibrated: false, provider: null, model: null}`. Every decision record copies `calibrated` (true only when all three are calibrated for the record's provider and model)."
- **A1.2 Task 2 Files.** Old: "`tests/conftest.py` (fixture `memory_keyring` …)". New: "`tests/conftest.py` (created by WS2; LA1 adds fixture `memory_keyring` …)".
- **A1.3 Task 5 record shape.** After `thresholds: {…}` add `calibrated: false`; `decision-record.schema.json` gains a required boolean `calibrated`.
- **A1.4 Task 6 Files (ordering defect).** LA1 creates `tools/apd_gauntlet/decide/policy.py` with `ThresholdEntry` and `load_threshold(key: str, path: Path | None = None) -> ThresholdEntry`, using exactly WS6 Task 1's signatures (WS6 runs two milestones later). It also modifies `eval/calibrate.py` registration and `data/decide/thresholds.yaml`. **Cross-edit WS6:** in WS6's File Structure and Task 1 Files, `decide/policy.py` changes from "Create" to "Modify (LA1 created `ThresholdEntry` and `load_threshold`)".
- **A1.5 Task 6 Interfaces (`finding_qa.py`).** Replace `THRESHOLDS;` with: `SEVERITY_LEVEL = {s: i for i, s in enumerate(SEVERITIES)}` (0–4; System One's `score` is the probability-weighted 0-based level index); `def thresholds() -> dict[str, ThresholdEntry]`; per item `delta = abs(score - SEVERITY_LEVEL[severity])`; LA1 registers `ValueSpec("finding-qa", "above", lambda item, f: item.get("delta"))` under `finding-qa.severity_delta` (WS2's plan says LA1 registers it).
- **A1.6 Task 6 Interfaces (`record_consent`).** Old: "… writes `runs/<id>/.apd-state/consent.json` `{provider, model, granted_at, method}` …". New: "… reads and writes only the `decision_model` subject of `consent.json`, a JSON object keyed by subject (R6): `consent["decision_model"] = {provider, model, granted_at, method}`; other subjects such as `iac_module_fetch` are preserved; `has_consent` reads only `consent.get("decision_model")`." Add tests `test_consent_preserves_other_subjects`, `test_has_consent_ignores_other_subjects`.
- **A1.7 Task 6 (`factory.py`): shared decision spend.** Add `run_spend(run_dir: Path, *, exclude: Path | None = None) -> float` (sum of `usage.cost_usd` over `40-synthesis/decisions/*.yaml`). `decide finding-qa` builds its client with `budget = budget_usd_per_run - run_spend(exclude=<own record>)` and exits 1 with `decision budget for this run is exhausted` when ≤ 0. **Cross-edit WS6 Task 3:** reuse `run_spend` rather than create it.
- **A1.8 Task 6 (`record_is_current`).** Also compares each item's `state_sha256` (A12.2).

### A2 — LA2 (`2026-10-10-local-apps-plan2-agent-sdk-runner.md`)

- **A2.1 Global Constraints (labels).** Labels equal the workflow's on the WS1 + WS3 base; tests derive expected labels from WS3's `tests/js/workflow_dispatch_trace.mjs` (`trace`, `CLI_LABELS`), never hand-written lists.
- **A2.2 Global Constraints (tier gate).** Append: "Tier gate (WS1): one `apd-tier-repair` dispatch per failing file, prompt rendered by `resources.read_prompt("repair")`; then one re-run of the owning lenses; then halt."
- **A2.3 Global Constraints (three new bullets).** Agent specs read `model` and `effort` from frontmatter (R5). The runner calls `check_engine_compat(run_dir)` before any step; `EngineMismatch` → `RunHalted("setup")`, exit 3 (effective once `FRAMEWORK_VERSION` is 2.x). The runner calls `measure.attempts.write_attempts` at closeout.
- **A2.4 Task 3 (`error_files`).** New signature `error_files(gate_json: str, run_dir: Path) -> dict[str, list[str]]`: parses `{"errors":[{"file","id","message","path"}]}` from `tier-gate --json`; keeps only `*.findings.yaml` and `*.capabilities.yaml` under the tier (as the workflow's `failingFiles` does).
- **A2.5 Task 3 (`test_parse_audit_counts`).** Old: `"audit-report: FAIL (checks=12 structural_failed=1 editorial_failed=3)\n"`. New: `"audit-report: fail (12 checks, 4 failed; structural_failed=1 editorial_failed=3)\n"` (the real format in `cli.py`'s `audit-report`).
- **A2.6 Task 3 (composites, DEC-16).** The runner runs `prepare-run`, `tier-gate`, `post-tier4` and `closeout` as `apd-gauntlet <composite>` subprocesses; tests build the expected argv with WS3's `composite.*_steps` builders.
- **A2.7 Task 5 (`INSTRUCTIONS`).** Replace `apd-<lens>:repair` with `apd-<lens>:rerun` and `apd-tier-repair` (rendered from `repair.md`).
- **A2.8 Task 5 (`test_load_spec_comma_tools`).** Drop the literal `s.model is None`; compare model and effort with the agent's frontmatter (WS3 adds `effort`; WS5 Task 23 requires `model`).
- **A2.9 Task 5 (`make_result`).** Mandatory helper: `claude-agent-sdk` 0.2.167's `ResultMessage` also requires `duration_ms`, `duration_api_ms` and `session_id`.
- **A2.10 Task 6 `setup` row.** Old: "validate-scaffold; build-domain-skill; validate-domain". New: in-process `check_engine_compat` plus `build_resume_plan` (label `resume-plan`; steps it marks complete become `skipped`), then `prepare-run` (always).
- **A2.11 Task 6 canonicalize steps.** Add `canonicalize-code-evidence` (phase `canonicalize`) after code recon and `canonicalize-threat-model` (phase `canonicalize`) after the TM-recon block, as the workflow has them.
- **A2.12 Task 6 tier row.** Old: "canonicalize-<tier>; validate --tier --errors-only (validate-<tier>); … one :repair per lens … -r1 …; continue either way". New: (1) `tier-gate <run> --tier <tier> --json` (`tier-gate-<tier>`); (2) on red, one `apd-tier-repair` per file (`repair-<tier>-<basename>`); (3) `tier-gate-<tier>-after-repair`; (4) `<lens>-rerun`; (5) `tier-gate-<tier>-after-rerun`; (6) `RunHalted`; (7) then `decide-finding-qa-<tier>`, only when the tier is green.
- **A2.13 Task 6 (`test_happy_path_labels`).** Derive from `trace()`; the prefix is `resume-plan, prepare-run, intake, assemble-inventory, intake-schema-gate, code-recon, canonicalize-code-evidence, author-threat-model-floor, threat-model-author, tm-recon, canonicalize-threat-model`.
- **A2.14 Task 6 (`test_tier_gate_repair`).** Expect `repair-10-trustworthiness-integrity.findings.yaml` and `tier-gate-10-trustworthiness-after-repair`; add `test_tier_gate_halts_after_rerun` expecting ledger state `failed`.
- **A2.15 Task 7 rows.** `assemble-c4`, `canonicalize-tmeval` and `rollup` become `post-tier4` with WS3's `stepFailed` rule: retry once (`post-tier4-retry-1`) only when the `rollup` constituent failed, then `synthesizer-fallback-rollup`. Closeout becomes `closeout --record-attempts <json>` (`closeout`).
- **A2.16 Task 7 missing branch.** After `adjudicate-retry-1`, a non-exit-2 error leads to `apply-clusters-retry-2`, and an error there to the fallback, as in the workflow. Add the label to `test_labels_exist_in_workflow`.
- **A2.17 Task 7 domain capture.** Runs only when `domain_improvement_capture: true` (WS3), otherwise `skipped`; `canonicalize-dimpr` is removed because `closeout` canonicalizes.
- **A2.18 Task 7 (`test_full_happy_path_tail`).** Derive the tail from `trace()`.

### A3 — LA3 Task 3 (`2026-10-10-local-apps-plan3-setup-tui-web.md`)

- **A3.1 Files.** Modify `tools/apd_gauntlet/app/services.py` (adds `register_doctor_check`).
- **A3.2 Interfaces.** `def register_doctor_check(name: str, fn: Callable[[UserConfig], Check]) -> None`; registered checks run after the eight built-in checks, in registration order; a duplicate or built-in name raises `ValueError`; an exception inside `fn` becomes `Check(name, "fail", <exception class and first 200 characters>, None)`; `doctor --json` lists registered checks; IAC1 and CF1 register theirs at import.
- **A3.3 Tests.** `test_registered_check_runs_after_builtins`, `test_register_duplicate_rejected`, `test_registered_check_exception_is_fail`.
- **A3.4 Self-hosted provider in setup and doctor (consolidated plan N5).** Setup's decision-model prompt gains "Self-hosted (System One endpoint)", asking for the base URL and context window; flags `--decision-base-url` and `--decision-context-window` set `decision_model.base_url` and `decision_model.context_window`; `--decision-provider` accepts `selfhosted`. `doctor --online` sends one `noul` question to the self-hosted endpoint and reports latency. Tests `test_setup_selfhosted_flags_write_config`, `test_doctor_online_uses_selfhosted` (mock transport).

**Lint note.** CI's markdownlint globs exclude `docs/superpowers/plans/**`; lint the edited plans explicitly (`npx --yes markdownlint-cli2 <files>`). They lint clean today (`Summary: 0 error(s)` with the repo's `.markdownlint.json`).

---

## A7. Threat catalog 1.1.0 (spec, master plan, CAT1–CAT4)

Decision (DEC-6): option A — vendor the whole 1.1.0 release as `open`; `full` is an operator-supplied local catalog file in the release schema. Option B (drop `full`) would change R4, delete C6, rewrite more than 30 test sites and lose private extensions and pre-vendoring trials.

| Criterion | A: single vendored edition, `full` = local file | B: no `full` |
|---|---|---|
| R4 | Unchanged; add a note on what `full` means | `full`, `path` and the `if/then` dropped; `off \| on` would also rename `open` everywhere |
| `catalogEdition()` and `CATALOG_DEFAULT_EDITION` mirror | Unchanged (`!== 'off'`) | Unchanged with `off \| open`. With `off \| on`, the constants, the `WORKFLOW_DEFAULT_RE` tests and the decision values change |
| CAT4 A/B design | Unchanged | `CONFIGS`, `run_config_name`, `test_full_fallback_refused` and the `full.*` metrics in T4–T7 removed |
| Fixtures | Rewrite to the 1.1.0 shape; `full.json` = open + 1 ineligible extension | Rewrite; delete `full.json` and rework the tests in CAT1 T8/T9/T12, CAT2 T4/T9/T10, CAT3 T1/T7/T15 |
| Loader | `strip_lineage`, `stub_rule_errors`, `full_mode_errors` and `STUB_REMOVED_FIELDS` go; `hitrust_errors` comes in | Also loses `check_full_path`, the fallback and the git warning |
| C6 | Reworded; kept | Deleted; M5 gate changes |
| Capability | Private extensions; trial of a new release before vendoring | Lost |

- **A7. Threat catalog 1.1.0 removes HITRUST; one vendored catalog (decided 2026-10-14; from the catalog build session 2026-10-12/13).** Catalog 1.1.0 changes only the HITRUST material:
  - It keeps 367 threats in 25 families, the `TC-<FAMILY>-<NNN>` ids, and about 9,800 mappings across 33 frameworks, all unchanged.
  - It removes per-threat `source` and `hitrust`, top-level `hitrust_crosswalk`, and `$defs.normalization`.
  - `catalog.counts` is exactly `threats`, `families`, `mappings`.
  - Version 1.0.0 was never published.

  The whole release is vendored as `open`. `full` names an operator-supplied local catalog in the same schema. The stub rule, `strip_lineage`, full mode and the `.gitignore` guard are dropped, and one HITRUST guard replaces them. Apply A7.1–A7.61 before executing CAT1.

**Spec**

- **A7.1. Header and §2.**
  - L11 (nl 10) becomes "(catalog 1.1.0: 367 threats in 25 families and about 9,800 mappings across 33 frameworks, built separately in claude.ai; it carries no HITRUST content)".
  - L58 (nl 50) becomes "Keep content the catalog may not redistribute out of every artifact. Catalog 1.1.0 carries no HITRUST content, and a load-time and CI guard keeps it that way (§12.3)."
- **A7.2. §3, L77–78 (nl 65–66).**
  - Licensing: "**Single vendored catalog, optional local file.** The whole release is vendored as `open`. `full` names an operator-supplied local file in the release schema (private extensions, or a release being trialled), loaded only from `threat_catalog.path`."
  - Rejected: "An open subset with HITRUST stubs (1.0.0 design, obsolete); dropping `full` (loses private extensions and pre-vendoring trials; changes R4, the workflow mirror and CAT4)."
  - Source row: "vendors the release file and its schema with provenance".
- **A7.3. F10, L98 (nl 83).**
  - Fact: "Catalog 1.1.0 removed every HITRUST field (`source`, `hitrust`, `hitrust_crosswalk`, `$defs.normalization`); `catalog.counts` is exactly `threats`, `families`, `mappings`; every threat carries `summary`, `description` and `example`."
  - Consequence: "One schema, the release's, validates the vendored file and any local file. The model has no `source` or `stub`. Selection reads the same fields from either file (§11)."
- **A7.4. §5 diagram, L104–105 (nl 87–88).**
  - First line: `threat-catalog repo ──release──▶ threat-catalog-<v>.json ──vendored──▶ data/threat-catalog/open.json`.
  - Second line: `operator's local catalog file ──threat_catalog.path (edition full)─┐`.
- **A7.5. §6.1, L132–150 (nl 111–126).** Replace with:
  - "`illusconsulting/threat-catalog` owns the source YAML, the build and validation scripts, `LICENSE` and `NOTICE`."
  - Per version `X.Y.Z`, on tag `vX.Y.Z`, it publishes `threat-catalog-X.Y.Z.json`, `threat-catalog.schema.json` and `SHA256SUMS`, plus optional `.md`, `coverage.md` and `.html` renders, which the gauntlet ignores.
  - "There is no private release, no full asset and no stub rule. The catalog repo's CI refuses any `hitrust` key or text."
- **A7.6. §6.2 table, L158–161 (nl 131–134).**
  - `open.json`: "the pinned release asset `threat-catalog-<v>.json`, byte-identical".
  - `open.schema.json`: "the release's `threat-catalog.schema.json`, byte-identical; it also validates local files".
  - `compat.yaml`: `catalog_compat: ">=1.1.0,<2.0.0"`.
  - The vendored names stay `open.*`.
- **A7.7. §6.3, L174 (nl 144).**
  - "downloads the open asset and its schema" becomes "downloads `threat-catalog-<v>.json` and `threat-catalog.schema.json`".
  - Add "including the HITRUST check" after "validates the file (§12.1)".
- **A7.8. §6.4, L185–192 (nl 154–160).** Retitle "The local catalog (`full`)".
  - First sentence: "A local catalog is the operator's own file in the release schema: for example the vendored release plus private threats, numbered `TC-<FAMILY>-9NN` by convention, or a newer release being trialled."
  - The rest is unchanged.
- **A7.9. §7, L199–203 (nl 164–167).** The example path becomes `path: ~/threat-catalog/local-catalog.json  # required for full: an operator-supplied catalog file`.
- **A7.10. §8.1, L278 (nl 228).** `version: 1.1.0`.
- **A7.11. §8.4, L361–363 (nl 294–296).** "the `summary`, clipped to 160 characters (every 1.1.0 threat has one); the family name when a local file's summary is empty".
- **A7.12. §8.9, L520 (nl 420).** "rows show id, name and the clipped summary".
- **A7.13. §11, L596–598 (nl 483–485).** "**Same function, either file.** Selection reads only catalog fields. A local file whose threats equal the vendored file's gives identical scope, candidates and silence lists; its extra threats join only where eligible. Only the recorded `edition` differs."
- **A7.14. §12.1, L611–628 (nl 495–510).** The checks, in order:
  1. at most 20 MB;
  2. JSON;
  3. no HITRUST content: no key containing `hitrust` (any case, any depth), and no per-threat `source` or `stub` key; for the vendored file, also no string value containing `hitrust`;
  4. validates against the vendored `open.schema.json`;
  5. ids are unique and well formed, `parent`, `children` and `related` resolve, and `catalog.counts.threats` and `.families` equal the array lengths;
  6. version within `compat.yaml`;
  7. for the vendored file, the SHA-256 matches `open.provenance.json`.

  In the closing sentence, "full file" becomes "local file".
- **A7.15. §12.3, L639–652 (nl 518–530).** The bullets become:
  - CI: check 3 runs on the vendored file, and no file under `data/threat-catalog/` or `tests/fixtures/threat_catalog/` contains `hitrust` in any case.
  - CI: committed examples have no scope file, or `edition` `open`; a local catalog's private prose must never be committed.
  - Report and coverage: id, name and clipped summary for every threat.
  - Export: no catalog prose.
  - Run directories: with `full`, they carry the operator's local prose; they are local-only, and the log records the edition.
  - NOTICE: carries the catalog licence and points to the catalog NOTICE for third-party terms.
- **A7.16. C6, L712 (nl 577).** "| C6 | Run through `edition: full` with a local file equal to the vendored catalog plus threats eligible on no surface | Identical scope, candidates and silence lists |".
- **A7.17. §15, L730–731 (nl 589–590).**
  - "Publish `illusconsulting/threat-catalog` `v1.1.0` with `threat-catalog-1.1.0.json`, `threat-catalog.schema.json`, `SHA256SUMS`, `LICENSE` and `NOTICE`, before CAT1 Task 7."
  - Keep "Label threats for the corpora (CAT4)".
  - Delete "Confirm the HITRUST position".

**Master plan**

- **A7.18. R4, L158 (nl 125).** Append "`full` is an operator-supplied local catalog file in the release schema (A7)."
- **A7.19. R8, L214 (nl 170).** Replace the full-edition sentence with: "`open.json` and `open.schema.json` are the release's `threat-catalog-<v>.json` and `threat-catalog.schema.json`, byte-identical. A local catalog file (`threat_catalog: full`) is never committed or vendored; the loader warns when it sits in an unignored git tree."
- **A7.20. M4, L80 (nl 63).** "catalog load, no-HITRUST, KB-alignment and KB-edition tests green".
- **A7.21. Task 6 Step 2a, L405 (nl 323).** "passes the load, no-HITRUST, KB-alignment and KB-edition tests".
- **A7.22. Decision 14, L484 (nl 389).** After "(A5 declined).": "Catalog 1.1.0 (2026-10-13) removed all HITRUST content. The whole release is vendored as `open`; `full` is an operator-supplied local file; the loader and CI refuse any `hitrust` key or text (A7)."
- **A7.23. Decisions still needed, L495 (nl 398).** Replace the row with the consolidated plan's DEC-7 (repository public; data CC BY-SA 4.0, code Apache-2.0; CIS ids only; CSA ids plus short attributed titles), DEC-8 (compat and asset names) and DEC-9 (ATT&CK v20.0 follow-up).
- **A7.24. Operator work, L530 (nl 427).**
  - "**Threat catalog release:** create `illusconsulting/threat-catalog` (public by default), push the 1.1.0 sources, and add `LICENSE` and `NOTICE`."
  - "Tag `v1.1.0` and publish `threat-catalog-1.1.0.json`, `threat-catalog.schema.json` and `SHA256SUMS`."
  - "Do this before CAT1 Task 7, which copies the release schema. CAT1 Task 14 vendors the file."

**CAT1**

- **A7.25. Header, L5, L7, L15 (nl 3, 4, 9).**
  - Goal: "(the vendored 1.1.0 release as `open`, and an optional operator-supplied local file as `full`)".
  - Model: "with no `source`, `stub` or HITRUST field".
  - Scope: "the HITRUST check".
- **A7.26. Global Constraints, L26–39 and L45–52 (nl 17–30, 36–43).**
  - The full-mode bullet becomes: "A `full` file is an operator-supplied local catalog in the release schema (A7). It is never committed, vendored or copied into a run, and it validates against the vendored `open.schema.json` exactly as the vendored file does. There is no second schema."
  - L30, assets: `threat-catalog-X.Y.Z.json`, `threat-catalog.schema.json`, `SHA256SUMS` (token rules unchanged).
  - L36–39 become: "No HITRUST content (A7): the loader refuses any key containing `hitrust` and any per-threat `source` or `stub` key in either edition, and any `hitrust` text in the vendored file. `model.py` has no `source`, `stub` or lineage field."
  - L45–52 become the seven checks of A7.14.
- **A7.27. Review Focus, L79 (nl 68).**
  - The case becomes "(hash mismatch, a `hitrust` key or text, a pre-1.1.0 `source`/`stub` field, a version outside `compat.yaml`)".
  - Pinned tests: `test_sha_mismatch_writes_nothing`, `test_hitrust_content_refused`, `test_version_outside_compat_refused` (Task 10); `test_hitrust_key_refused_in_both_editions`, `test_hitrust_text_refused_in_open_only` (Task 8).
- **A7.28. File Structure, L92–93, L102, L117, L120 (nl 78–79, 88, 103, 106).**
  - `model.py`: `MappingRef`, `Threat`, `Catalog`, `build_catalog`.
  - `load.py`: `validate_catalog_file`, `hitrust_errors`, `reference_errors`, `load_catalog`, local-path rules, `CatalogError`.
  - `open.schema.json`: "the release schema, byte-identical".
  - Drop `.gitignore` from its row.
  - Fixtures: "synthetic 1.1.0 shape; `full.json` = `open.json` + `TC-OT-901`".
- **A7.29. Task 1, L258 and L277–298 (nl 215, 227–245).**
  - ADR test phrases: "single vendored catalog" and "no hitrust content" replace "open subset" and "lineage".
  - ADR Decision: §3 as amended; catalog 1.1.0 carries no HITRUST and the loader refuses any; the LLM fix is 2.0 only; `DEFAULT_EDITION` stays `off`.
  - ADR Alternatives add "an open subset with HITRUST stubs (1.0.0 design)" and "dropping `full`".
  - The running doc says "`full` needs `path`: an operator-supplied file in the release schema".
  - Optional: L248 (nl 208) `hitrust_lineage` becomes `bogus`.
- **A7.30. Task 6, L809 (nl 633), L942 (nl 747).** `catalog_compat: ">=1.1.0,<2.0.0"`.
- **A7.31. Task 7, L969–1135 (nl 760–892).**
  - **Title:** "Catalog model, release schema and synthetic fixtures".
  - **`Threat`:** drop `source` and `stub`; `summary: str`. Delete `STUB_REMOVED_FIELDS`.
  - **`open.schema.json`:** the 1.1.0 release's `threat-catalog.schema.json`, byte for byte, with no derivation and no added `stub` property. Prerequisite A7.24. Task 10 replaces it on refresh.
  - **Fixtures:** 1.1.0 shape, `catalog.version: 1.1.0`, `generated: 2026-10-14`, `catalog.counts` exactly `{threats, families, mappings}`, with `mappings` counted as the 1.1.0 build does (UNVERIFIED rule).
  - **Fixture table:** drop the "Source (`hitrust.ids`)" column. All 24 threats are complete, with synthetic prose and no `hitrust`, `source`, `stub` or `hitrust_crosswalk`. `open.json` holds the 24.
  - **`full.json`:** `open.json` plus `TC-OT-901`: OT family, technique, event, `system_types: [ot_ics]`, STRIDE `T`, controls `nist_800_53` SI-7 primary (present in the KB). Counts: `threats: 25`, OT family count +1.
  - **Provenance:** source `https://github.com/illusconsulting/threat-catalog/releases/download/v1.1.0/threat-catalog-1.1.0.json`, version `1.1.0`.
  - **Test changes:**
    - `test_build_full`: 25 threats, version 1.1.0;
    - `test_open_stub` becomes `test_open_threat_complete`;
    - `test_model_never_loads_hitrust` becomes `test_model_has_no_source_stub_or_lineage_fields`;
    - delete `test_full_fixture_keeps_lineage_for_no_lineage_tests`;
    - `test_open_fixture_is_full_with_stub_rule` becomes `test_full_fixture_is_open_plus_extension`;
    - `test_fixture_coverage` runs on `open.json` (24) and drops the HITRUST count;
    - provenance test expects `1.1.0`;
    - the schema vocab test drops `hitrust`/`stub`.
  - **Commit:** "feat(catalog): add frozen threat model, release schema and fixtures".
- **A7.32. Task 8, L1138–1275 (nl 893–997).**
  - **Produces:** drop `strip_lineage`, `stub_rule_errors` and `full_mode_errors`. Add `def hitrust_errors(doc: Any, *, text: bool) -> list[str]` (check 3; sorted; at most 20). Keep `reference_errors` (check 5), now also comparing `catalog.counts.threats` and `.families`. Checks 1–4 stop at the first failure; checks 5–7 accumulate.
  - **Check 3 messages:** `"hitrust key at <path>"`; `"hitrust text at <path>"` (open only); `"<id> carries <source|stub>, a pre-1.1.0 field"`.
  - **Check 5 message:** add `"catalog.counts.threats <n> does not match <m> threats"`, and the same for `families`.
  - **Tests to delete:** the four `stub_rule` tests, `test_leaked_summary_fails_validation`, `test_strip_lineage`, `test_full_mode_rejects_stub_and_missing_prose`, `test_full_validates_against_open_schema_without_lineage`.
  - **Tests to add:**
    - `test_hitrust_key_refused_in_both_editions` (a threat-level block, then a top-level `hitrust_crosswalk`);
    - `test_hitrust_text_refused_in_open_only`;
    - `test_pre_1_1_shape_refused`;
    - `test_counts_must_match`.
  - **Compat test:** parametrize `1.0.0` and `2.0.0`, with the message `outside catalog_compat >=1.1.0,<2.0.0`.
- **A7.33. Task 9, L1277–1393 (nl 998–1083).**
  - Drop `strip_lineage`; a valid local file gives `build_catalog(doc, edition="full", …)`.
  - The git warning ends "; never commit a local catalog".
  - Add `test_full_with_hitrust_key_falls_back`: it expects `edition == "open"`, `fallback_from == "full"`, and a warning containing "hitrust key".
- **A7.34. Task 10, L1395–1553 (nl 1084–1206).**
  - `asset_names(version)` returns `{"catalog": f"threat-catalog-{version}.json", "schema": "threat-catalog.schema.json", "sums": "SHA256SUMS"}`. Staging writes them as `open.json` and `open.schema.json`.
  - All tests use 1.1.0: `_assets(fix, version="1.1.0")`, `bad_sum="threat-catalog-1.1.0.json"`, URLs `v1.1.0`.
  - `test_stub_rule_violation_refused` becomes `test_hitrust_content_refused`, and `_with_leak` becomes `_with_hitrust`.
  - The version-mismatch test uses 1.1.1 against 1.1.0.
  - The golden `source` is the 1.1.0 URL.
- **A7.35. Task 12, L1627–1719 (nl 1262–1329).**
  - **Title:** "CI guards for the vendored catalog (KB alignment, no HITRUST content, committed examples)".
  - **Removed:** the `.gitignore` edit and `test_full_catalog_pattern_gitignored`.
  - **Renamed:** `…_validates_and_obeys_stub_rule` becomes `test_vendored_open_catalog_validates`.
  - **Added:** `@needs_vendored test_vendored_catalog_has_no_hitrust_content`; and `test_catalog_data_and_fixtures_have_no_hitrust_text`, which always runs.
  - **Notice test:** asserts `f"threat catalog {v}"`.
  - **Step 4 Expected:** "six PASS and five SKIP".
  - **Commit:** "test(catalog): CI guards for KB alignment, HITRUST-free content and committed examples".
- **A7.36. Task 13, L1760 (nl 1360).** `"open 1.1.0"`.
- **A7.37. Task 14, L1794–1846 (nl 1383–1416).**
  - **Title:** "Vendor catalog release 1.1.0 (operator)".
  - **Prerequisite:** A7.24.
  - **Step 1:** `apd-gauntlet refresh-threat-catalog --version 1.1.0 --dry-run`. Expected: `added: 367 (…)`, a line per mapping key, `dry run: nothing written`.
  - **Step 2:** `--version 1.1.0`. Expected: three `Wrote` lines; `git status` shows `open.json` and `open.provenance.json` added and `open.schema.json` unchanged.
  - **Step 3, NOTICE:** `illusconsulting threat catalog 1.1.0 — <licence and URL from the release LICENSE>: data/threat-catalog/open.json, data/threat-catalog/open.schema.json`, followed by "Third-party framework ids and names in the catalog remain under their own terms; see the catalog's NOTICE at <v1.1.0 NOTICE URL>." `REQUIRED` gains `threat-catalog/open.json`.
  - **Step 4:** the five vendored guards pass.
  - **ATT&CK note:** ATT&CK v20.0 was released 2026-10-13 and the catalog maps v19.2. Run `refresh-mitre` only if an id check fails, and record the outcome.
  - **Step 5:** "Check a local catalog (optional)": copy `open.json` outside git, add a `TC-<FAMILY>-9NN` threat, set `{edition: full, path: …}`, run `apd-gauntlet doctor`. Expected: `1 full path(s) valid`. Delete the stub-schema remark.
  - **Commit:** "chore(catalog): vendor threat catalog 1.1.0".
- **A7.38. Follow-ups, after L1851 (nl 1419).** Add: "ATT&CK v20.0 (2026-10-13) is newer than the catalog's v19.2, and `mitre-attack-techniques.json` (fetched 2026-05-29) records no version. Record the collection version in `_meta.version`, then build catalog 1.2.0 against v20." The private-download bullet applies only if the repo stays private.

**CAT2**

- **A7.39. L36 (nl 28).** "No HITRUST content (CAT1 A7): candidate text is the clipped `summary`, or the family name when it is empty."
- **A7.40. L193 (nl 152).** Delete "source `added`, stub `False`".
- **A7.41. L1357 (nl 1091).** The else-branch becomes `{edition: full, path: <the release's threat-catalog-1.1.0.json, outside any git tree>}`.
- **A7.42. L1388 (nl 1117).** Add: "`full.json` = `open.json` + `TC-OT-901`, eligible on no fixture surface (`pbm` and `agentic-ai` never yield `ot_ics`), so C6 holds."

**CAT3**

- **A7.43. L25 (nl 17).** "No HITRUST content (CAT1 A7): the loader refuses any `hitrust` key, and the model has no `source`. Task 15 proves that no output carries `hitrust`. `export-gaps` never includes catalog prose."
- **A7.44. L40 (nl 30).** "**A local catalog carrying a `hitrust` key:** the loader falls back to open, and no output carries `hitrust`. Pinned by CAT1 `test_full_with_hitrust_key_falls_back` and Task 15 `test_catalog_steps_never_emit_hitrust`."
- **A7.45. L577–579 (nl 445–447).** The stub becomes `make_threat(id="TC-IN-005", summary="", family_name="Injection & Input Handling")`; the expected lines become `["Injection & Input Handling", "Summary of TC-IN-006"]`.
- **A7.46. Task 11, L1218, L1237, L1271–1277, L1315 (nl 932, 949, 978–984, 1014).**
  - The threat row drops `source`.
  - `summary` appears for every threat, clipped and on one line, and is omitted when empty.
  - The HITRUST test becomes `test_coverage_summary_is_clipped_and_one_line`.
  - The docs drop "no HITRUST lineage view".
- **A7.47. L1487 (nl 1141).** "gap reasons in `full` runs may paraphrase the operator's local catalog prose".
- **A7.48. Task 14, L1516, L1526–1535, L1572 (nl 1161, 1169–1177, 1204).**
  - `summary` passes through when present.
  - The COV rows drop `source`.
  - The test becomes `test_view_attention`.
  - The docs drop "the HITRUST rule".
- **A7.49. Task 15, L1591–1650 (nl 1216–1260).**
  - **Title:** "No HITRUST content in any output, and the first `open` comparison".
  - `test_catalog_steps_never_emit_hitrust` runs the same steps and asserts no output contains `hitrust` in any case; it drops `_hitrust_ids` and `KEY_RE`.
  - Add `test_hitrust_bearing_local_catalog_never_reaches_outputs`, which calls `load_catalog` directly on a copy with a `hitrust` block and expects the fallback warning.
  - **Commit:** "test(catalog): no HITRUST content reaches any catalog output".

**CAT4**

- **A7.50. L30 (nl 23).** "CAT4 reads no catalog prose, and no CAT4 output carries any." Everything else is unchanged.

**Staleness and cross-plan amendments**

- **A7.51. `_recompute_ids_for_file` return arity (CAT1 Task 3 and CAT3 Task 2).**
  - After WS1 the function is `(path, root_key, id_map, seen_new_ids) -> tuple[list | None, int]` (`canonicalize.py:167-246`), and CAT1 (L520) and CAT3 (L232) each add a different third return value.
  - Fix: CAT1 introduces `@dataclass class FileResult: records: list[dict[str, Any]] | None; ids_changed: int; llm_qualified: int = 0`, with the keyword `*, qualify_llm=False`.
  - CAT3 adds `catalog_changed: int = 0` and the keyword `rc=None`.
- **A7.52. CAT1 Task 2 crosswalk content.** OWASP publishes the 2021→2025 mapping as an image. The text of `https://owasp.org/Top10/2025/0x00_2025-Introduction/` (no date shown) gives:

  | 2021 id | 2025 target |
  |---|---|
  | A01:2021 | A01:2025 |
  | A02:2021 | A04:2025 |
  | A03:2021 | A05:2025 |
  | A04:2021 | A06:2025 |
  | A05:2021 | A02:2025 |
  | A06:2021 | A03:2025 ("an expansion of A06:2021") |
  | A07:2021 | A07:2025 |
  | A08:2021 | A08:2025 |
  | A09:2021 | A09:2025 |
  | A10:2021 | A01:2025 ("SSRF has been rolled into this category") |

  - Every row has a target, so no `note` row is needed.
  - The 2025 names, from `https://owasp.org/Top10/2025/`: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions.
  - The LLM 2025 names at `https://genai.owasp.org/llm-top-10/` match CAT1's list.
  - `tests/test_skill_apd_control_mappings.py` needs a new `_section()` helper; none exists.
- **A7.53. CAT2 Task 3, L305–306 (nl 241–242).** Pin CAT1's rows: `service` `TypeHint(("web_app","api","serverless","saas","ai_ml","agentic_ai"),"api")` and `compute` `TypeHint(("server","cloud","container_k8s","serverless","ai_ml","ci_cd"),"server")`. As written, the test conflicts with CAT1 L925–926. Spec §8.1, L254–259 (nl 208–212), should say CAT1 extends both lists.
- **A7.54. Conftest helpers (CAT2 Task 2, CAT3 Task 1).**
  - CAT2 keeps the plain helpers.
  - It also registers `@pytest.fixture(name="make_threat")`, returning `lambda *, id="TC-AC-001", **kw: make_threat(id, **kw)`, and `@pytest.fixture(name="make_catalog")`, returning `make_catalog`.
  - There is one default summary, `Summary of <id>`.
  - CAT3 L20, L80, L87: `catalog_run` becomes `make_scope_run`; drop "gains `frameworks=None`", which CAT2 already has.
- **A7.55. CAT2 L23 (nl 15).** The R3 quote becomes the current master text: "`catalog-scope` is the first step of `threat-model-author`, and `catalog-shortlists` runs in the `canonicalize` phase right after WS1's `canonicalize-threat-model`, before tier 1."
- **A7.56. `validate.py` after WS1 (CAT2 Task 7, CAT3 Task 8).**
  - `_validate_context_rollups` is gone. WS1 uses `_validate_rollups(run_dir, subdir, …)` (`validate.py:691`) and `_ROLLUP_TABLES` (`validate.py:560-563`).
  - CAT2: call `_validate_tm_catalog_fields` right after `_validate_rollups(run_dir, "00-context", …)` (`validate.py:736`).
  - CAT3: add `"40-threat-model": THREAT_MODEL_ROLLUPS` to `_ROLLUP_TABLES`, plus `_validate_rollups(run_dir, "40-threat-model", …)` in `run_schema_pass`; no new function is needed. `schema_for_run_file` and `schema_errors_for_file`, which `resume-plan` and the repair loop use, then cover the dismissals file.
- **A7.57. CAT3 Run lines.** Replace `/home/claude/venv-apd/bin/…` with plain `pytest`, `ruff`, `mypy` and `apd-gauntlet`. The path does not exist.
- **A7.58. CAT3 L20 (nl 12).** Add WS5 Task 1 to the prerequisites. It creates `ha_run` (WS5 L123), which Tasks 2, 3, 5, 7, 9 and 10 use.
- **A7.59. Absolute paths.** CAT1 L1723 (nl 1332) and CAT2 L16 (nl 10) cite `/home/claude/illusconsulting/apd-gauntlet/docs/...`. Use repo-relative `docs/superpowers/plans/2026-10-10-local-apps-plan{2,3}-*.md`; both exist on `next`.
- **A7.60. Locate edits by anchor.** CAT1 and CAT3 should say "Locate edits by anchor; line numbers predate WS1", as CAT2 L44 already does. Corrected values are in "A7 anchors after WS1" below.
- **A7.61. CAT1 Task 1, L163 (nl 140).**
  - The run config is validated without a registry at `cli.py:288-292` and `:399-401`, and at `resume_plan.py:107/126`, not at `cli.py:276/385`.
  - `tests/test_run_config_schema.py:12` reads `schemas/`, a symlink to `tools/apd_gauntlet/data/schemas`.

### A7 anchors after WS1 (CAT plans; locate by anchor)

| Plan claim | Now (worktree) |
|---|---|
| CAT1 T1: "Taxonomy scope (v1.2+)" ends at L220 | `:199-222` |
| CAT1 T1: run config at `cli.py:276/385`, test `:13` | `cli.py:288-292`, `:399-401`; `resume_plan.py:107/126`; test `:11` |
| CAT1 T3: `canonicalize.py` `:1-26`, `:120-127`, `:138-216`, `:272-310` | `:1-38`; `:143-157` (also has `context_parse_errors`); `:167-246`; `:424-477`; `_mint_threat_model_ids` `:383-421` |
| CAT1 T3: `cli.py:1266-1274` | `canonicalize_cmd` `:1298-1340`, summary `:1318-1331`; the blocked message goes to stderr |
| CAT1 T6/T8: `build_domain_skill.py:60-81`, `:75-81` | `_parse_semver_range` `:70-82`, `_version_in_range` `:85-91` |
| CAT1 T10: `cli.py:658-664` | `:709-716` |
| CAT2 T1: `cli.py:254`, `build_domain_skill.py:89`, `draft.py:119` | `:254/268`, `:99`, `:132` |
| CAT2 T3: `author.py:33-48` | `:35-48` |
| CAT2 T3: `load_packs` mirrors `attack_path/build.py:245-249` | That code tries `domains/<id>.yaml` first, then `<id>/domain.yaml`; mirror both |
| CAT2 T4/T6: `cli.py:758-780` | `:809-831` |
| CAT2 T4: `validate.py:291-307`, `:221-228` | `:537-553`, `:467-474` |
| CAT2 T6: `author.py:72-140` | `:83-125`, `:128-133` |
| CAT2 T7: `run_schema_pass :426-455` after `_validate_context_rollups` | `:711-738`; the function is gone (A7.56) |
| CAT2 T8: agent Steps 5/6/7/Discipline at `:123/:139/:147/:161` | `:130/:146/:154/:168`; Step 4 retitled by WS1 (`:110`) |
| CAT2 T9: workflow `:131-132`, `:384`, `:385-389` | `:164`, `:515`, `:516-520` |
| CAT2 T9: `plan_run.py:80-88` | `:93-100` |
| CAT3 T2: `cli.py:1247-1281` | `:1298-1340` |
| CAT3 T2: `schema-evolution.md:77` | `:87` |
| CAT3 T3: `validate.py:471-525`, `:702-865` | `:773`, `:1069` (`*, strict_excerpts`; semantic re-run at `:1155`) |
| CAT3 T5: workflow `:400-420` | `canonicalize-threat-model` `:552-557`; `function runTier` `:700` |
| CAT3 T5: `plan_run.py:80-95` | `:110-116` |
| CAT3 T8: evaluator Step 5 `:264-298`; tmeval thunk `:607-624` | `:271-306`; `phase('tmeval')` `:870` |
| CAT3 T9: `cli.py:783/1037/1085/1102` | `:834`, `:1088`, `:1136`, `:1153` |
| CAT3 T11: `cli.py:1350-1361`; `validate.py:234-287` | `:1409`; `:480` |
| CAT3 Run lines: `/home/claude/venv-apd/bin/pytest` | Does not exist |

**Expected absences.** These files do not exist yet; upstream plans create them: `tests/conftest.py`, `tests/test_bundle.py`, `tests/test_workflow_dispatch_trace.py`, `tests/test_tm_candidates.py`, the compare and metamorphic tests, `runner/`, `tm-candidates.schema.json`.

### A7 cross-plan conflicts (tests break as written)

1. `system-types.yaml` rows: CAT1 L925–926 against CAT2 L305–306 (A7.53).
2. `_recompute_ids_for_file` arity: CAT1 Task 3 against CAT3 Task 2 (A7.51).
3. The `make_threat` helper: positional plain function against keyword fixture; different default summaries; the `catalog_run` and `make_scope_run` name mismatch (A7.54).
4. CAT2's stale R3 quote (A7.55).
5. The pre-WS1 `validate.py` rollup functions (A7.56).

---

## A8. WS1 and the 1.7.1 release (`2026-10-10-ws1-defect-fixes-1.7.1.md`, master plan M1 and Task 2)

- **A8.1 WS1 Task 12 Step 1; master M1 exit gate; master Task 2 Step 2.** `compare-runs` exists on neither line, so "recorded compare-runs results for PR groups A, B, C and E" and the M1 gate are replaced by the 1.7.1 substitute gate: the offline example regression (consolidated plan Task 1.4, Appendix 1: `validate`, `canonicalize`, `build-report`, `audit-report`, `resume-plan` on the three committed examples, each identical to the 1.7.0 engine's output) plus one live run of `examples/apd-20260601-claim-event-bus/inputs` with the `metrics.yaml` comparison (Task 1.5). Keep the 1.7.1 run directory `runs/apd-20261016-ws1-gate` for WS2 (it has no telemetry); no 1.7.0 live run exists (A15.1). A 1.7.1 defect found later ships as 1.7.2.
- **A8.2 WS1 Task 12 Step 2.** Change the literal at `tests/test_workflow_apd_gauntlet.py` (`assert py_version == "1.7.1", (`) **and** the message on the next line ("expected the 1.7.1 release version"). Also bump `docs/QUICKSTART.md` (`# should print 1.7.1`; `framework_version: 1.7.1`).
- **A8.3 WS1 task groups and Task 12 Step 5.** WS1 was executed as one branch (`fix/ws1-1.7.1`, 19 commits), not PR groups A–G. Open one PR to `main` and merge with a merge commit. Merge the release PR and push `v1.7.1` in the same session: the 1.7.1 workflow halts on any engine without `resume-plan`, and the marketplace serves `main` HEAD.
- **A8.4 WS1 Task 12 Step 7; master Task 2 Step 4; RELEASING.md "Cutting a stable 1.7.x release" step 5.** While `next` has no 2.0 pre-release, `git merge --no-ff main` into `next` is conflict-free and takes 1.7.1 in all five version places; keep them. In the same merge commit, reword next's CHANGELOG bullet "Version stays `1.7.0` for now" to "Version tracks the stable line (1.7.1) until the first 2.0 pre-release", and delete the empty `## [Unreleased]` heading that comes from `main`. "Keep next's values" applies only once `2.0.0aN` is on `next`. The 1.7.1 release PR adds that rule to RELEASING.md step 5: "(While `next` has no 2.0 pre-release, take `main`'s version values.)"
- **A8.5 WS1 Review Focus 5 (record only).** On 1.7.1 the workflow halts with an upgrade message when the engine has no `resume-plan` command (`.claude/workflows/apd-gauntlet.js`, the `resume-plan` refusal branch; pinned by `tests/test_workflow_apd_gauntlet.py::test_resume_plan_refusal_halts_and_failure_falls_back`); the plan described a fallback.
- **A8.6 Master Task 4 Step 3 (cutting `v2.0.0a1`).** The workflow's older-engine halt says `pip install --upgrade "apd-gauntlet>=1.7.1,<2"` and "upgrade apd-gauntlet to 1.7.1", pinned by two assertions in `tests/test_workflow_apd_gauntlet.py`. `docs/running-the-gauntlet.md` repeats the command. The `2.0.0a1` version-bump PR changes the strings, both assertions and the docs copy to `pip install --upgrade --pre "apd-gauntlet>=2.0.0a1,<3"` and "upgrade apd-gauntlet to 2.0.0a1" (the CHANGELOG's v1.7.1 entry stays as history).
- **A8.7 WS1 Task 12 Step 3 (CHANGELOG).** New `## v1.7.1 — <date>`, every new bullet ending with its PR number, for example `(#9)`: Added — #7 (Quickstart guide); Changed — PR #27's two bullets, #10 (loader-contract test, `lint-skills`, pinned `claude plugin validate`), #44/#45 (report bundle rebuilt with cytoscape 3.34.3, react 19.3.0, cytoscape-dagre 4.0.1); Fixed — the 12 WS1 bullets and N1 (symlinks) with the WS1 PR number, #8 (plugin `skills` point at directories), #9 (freshness gate: hash parity and rebuild-diff). Move the six "Added" bullets and "Agents emit content only" that were under `[Unreleased]` at tag `v1.7.0` into `## v1.7.0`, and add the never-logged #104 bullet there (W0 `SerializationIntegrityError`, dict `scope` rejection, blocking prephase-5 gate; W1a `infrastructure.{mode,static}` and `manual-audit-prompts`; W1b `repos[]` and the zero-entry warning, ADR-0019; `kb_fetch.fetch_pinned` and `tools/check_kb_cache_freshness.py`). Keep an empty `## [Unreleased]`. Check: the consolidated plan's N2 loop prints nothing.
- **A8.8 WS1, new Task 11b.** Consolidated plan task N1 (`init-run` refuses escaping symlinks), before Task 12.
- **A8.9 Cosmetic.** `plan_run.py`'s tier-gate row text says `--errors-only` while the workflow runs `--tier <dir> --json`; align the text in WS3 Task 3. WS3's plan cites "WS1 Task 10 `check_excerpts_verbatim`"; it is WS1 Task 11.

## A9. WS2 and WS3 (`2026-10-10-ws2-measurement-and-evaluation.md`, `2026-10-10-ws3-cost-wave1-quick-wins.md`)

- **A9.1 WS2 anchors.** Locate by anchor: Task 3's CLI insertion is in `summarize` (`cli.py` ≈ 367–377); Task 4's `if __name__` line ≈ 1524; the lens retry loop is inside `runTier` (workflow ≈ 715–724); `isErr` ≈ 327; `bailIfInterrupted` ≈ 337–346; `tierGate` ≈ 634–641; the audit loop ≈ 1000; `summarize` ≈ 1106–1107; `report/loader.py` `load_corpus` starts ≈ 24.
- **A9.2 WS2 Task 4 (`AGENT_PHASES`).** Add `apd-tier-repair: canonicalize` (the agent exists from WS1, and WS2's own `test_agent_phases_cover_agents_and_workflow_phases` fails without it); add `test_tier_repair_counts_under_canonicalize`. WS3 Task 4 drops its `usage.py` edit. Registry R9 becomes "`AGENT_PHASES` (WS2 lists `apd-tier-repair`; WS3 adds `apd-cli-runner`)".
- **A9.3 WS2 Task 7 Step 3.** Old: "The tier gate becomes `const gate = pyStep('validate', …)`". New: "After `const gate = tierGate(phaseName, tierDir, '');` insert `if (isErr(gate)) attempts.tier_gate_failures.push(tierDir);` before `repairTierGate(phaseName, tierDir, lenses, gate);`; leave `tierGate` and `regate` unchanged."
- **A9.4 WS2 Tasks 3 and 7 (count WS1's repair loop, DEC-17).** `run-attempts` gains required `tier_repairs` (`{tierDir: int ≥ 0}`) and `lens_reruns` (`{lens: int ≥ 0}`); `repairTierGate` adds the number of repaired files to `tier_repairs[tierDir]` and sets `lens_reruns[lens] = 1` for re-run lenses; gate `first_pass_and_retries` adds `tier_repairs_delta le 0` and `lens_reruns_delta le 0`; `METRICS` gains both.
- **A9.5 WS2 Task 6 (`--excuse`, DEC-17).** `--excuse VALUE` is repeatable. `<gate-id>:<reason>`, where the prefix is a gate id, marks that gate `excused` (counts as pass; JSON carries `excuse`; text prints `EXCUSED (<reason>)`); any other value is a finding id (finding ids never contain `:`). Add `test_gate_excuse_passes_and_is_recorded`.
- **A9.6 WS2 Task 11.** Add `telemetry/` to `.gitignore`, assert it in the test, state it in `docs/measuring-changes.md` (exports hold Bash commands, tool input, `user.email` and account ids).
- **A9.7 WS2 Task 4 (optional; folded into N10).** Record `effort` per request.
- **A9.8 WS3 Task 1 (DEC-17).** Keep WS1's always-run line verbatim (`'Always run this command; this step has no idempotency check and no skip.'`) and drop `NO IDEMPOTENT SKIP`. Update `test_always_run_pystep_prompt_offers_no_skip` and `test_pystep_always_run_branch_is_pinned_in_the_source` to the `COMMAND:`/`RECEIPT AGENT:` contract; the `WORK COMMAND`/`short-circuited` pins move to the agent-body test. `pyStep` uses no new top-level constants (WS1's node renderer extracts only the `guard` and `pyStep` bodies).
- **A9.9 WS3 Task 1 counts.** `docs/architecture.md` says 21 agents today (three places); after Task 1 it says 22 and the orchestrator paragraph reads "twenty-third … among the 22"; `test_docs_v14.py` asserts "22 agents"; `lint-agents` reports 23 after Tasks 1 and 4, 22 after Tasks 5 and 6. Identifier checks go after the `args.domains` check.
- **A9.10 WS3 Task 2.** Anchor the composite registration next to `canonicalize` in `cli.py` (≈ 1358–1365). Add N19 (`manual-audit-prompts` in `closeout`).
- **A9.11 WS3 Task 3.** The canonicalize to remove is inside `regate()` (not `repairTierGate`); keep `function regate(` (`test_gate_helpers_are_defined_before_run_tier` requires it). Add `test_read_only_gates_always_run` to the change list (drop `validate-final`; assert `alwaysRun` in the `pyStep('closeout'` block). Reuse the existing `_plan` helper in `tests/test_cli_plan_run.py` (redefining trips ruff F811). Base `pyStep(` call sites are 32, not 33. Tier rows in `plan_run.py` must use phase `<tierDir>` so `test_plan_run_mints_context_ids_before_tier_1` still sees exactly two canonicalize-phase rows.
- **A9.12 WS3 Task 3 (DEC-17).** The tier-gate dispatch keeps WS1's `phase: phaseName`; the test asserts `"tier-2"`, not `'canonicalize'`.
- **A9.13 WS3 Task 4 (replaces master A6's task text).** Existing frontmatter: `name: apd-tier-repair`, a 150-character description, `tools: [Read, Edit]`, `model: sonnet`, no `effort`. Files: modify `.claude/agents/apd-tier-repair.md` (add `effort: low` after `model: sonnet`), `tests/test_lint_agent_apd_tier_repair.py`, `CHANGELOG.md`; do not create the agent or touch `plugin.json`, the workflow, `architecture.md`, `test_docs_v14.py` or `usage.py`. Step 1: in `test_agent_frontmatter` replace `assert "effort" not in meta` with `assert meta["effort"] == "low"` and add `assert len(meta["description"]) <= 160`; add `test_repair_template_carries_the_excerpt_rule` (asserts "not found verbatim", "exact words" and "never paraphrase" are in `read_prompt("repair")`); append `test_repair_dispatches_tier_repair_agent` to `tests/test_workflow_dispatch_trace.py`. Step 2: run → FAIL (`KeyError: 'effort'`). Step 3: add the line. Step 4: `pytest -q && apd-gauntlet lint-agents && markdownlint-cli2 .claude/agents/apd-tier-repair.md CHANGELOG.md` → pass, "Lint clean: 23 agents checked." Step 5: commit `perf(agents): run apd-tier-repair at low effort`. Step 6 (OP): as written, plus the repair's `api_request` events carry `effort: "low"`. R9 wording: "New agent `apd-tier-repair` (WS1; WS3 adds `effort: low`)".
- **A9.14 WS3 Task 5.** 20 descriptions to rewrite (tier-repair is already ≤ 160 characters); always-on bytes are 16,579 on the base, about 3,536 after.
- **A9.15 WS3 Task 7.** Anchors: `init_run.py` ≈ 80–96; `plan_run.py` ≈ 205–213 and 250–257; workflow domain-capture block ≈ 1065–1100 and header ≈ 32–39; `architecture.md` ≈ 44; `running-the-gauntlet.md` before `## Code reconnaissance (optional)`. After Task 3, phase 5h holds only `domain-coverage-delta` and `domain-auditor`.
- **A9.16 WS3 Task 8 (strict excerpts; DEC-18).** Before flipping the default: (a) make the matcher case-insensitive and remove whitespace adjacent to punctuation instead of collapsing it (`normalize_excerpt_text` in `validate.py`), with tests for the two observed false positives (acme `conf-4149d0db` "the client signs…" versus "**The client signs…"; Home Assistant `conf-3060c50e` `{access_token` versus `{\n  access_token`); (b) fix the remaining non-verbatim excerpts in the committed examples (Home Assistant has 23 genuine ones) — absence and summary notes become wholly parenthesised markers; (c) teach that marker rule in `apd-evidence-discipline` ("Evidence"); (d) make `test_committed_examples_validate_strict` copy `examples/<e>/inputs` into its temporary run (today it validates `expected/` without inputs and checks nothing); (e) the five WS1 tests that assume the warning default (`test_paraphrase_warns_but_exits_zero`, `test_errors_only_hides_the_warning`, `test_tier_gate_reports_excerpt_violations`, `test_tier_gate_json_carries_the_violation_by_severity`, `test_pathological_input_without_a_match_warns_and_never_fails_a_gate`) pass `--no-strict-excerpts` or are rewritten; (f) structured inputs searched only as whole text (YAML/JSON over 1 MiB, aliases, nesting over 100) keep producing warnings, never errors. Expected after: `apd-gauntlet validate <copy with inputs> --errors-only --strict-excerpts` exits 0 on all three examples.
- **A9.17 WS3 Task 9.** "CLI dispatches 24 (1.7.0; 27 on WS1+WS2) → 17 (18 with capture); general-purpose dispatches 24 → 0."
- **A9.18 WS3 Task 6.** Add N18 (pin each agent's `tools`).
- **A9.19 WS2 (new).** Add N20 (real pre-dedup counts) after Task 13.
- **A9.20 CI.** Add a SHA-pinned `actions/setup-node` (Node 22) to the `test` job in `.github/workflows/python-tests.yml`; without it the dispatch-trace tests skip in CI.

## A10. WS5 (`2026-10-10-ws5-cost-waves2-3-context-and-tiering.md`)

- **A10.1 Global Constraints and every operator gate (OG).** Line numbers are at `856ea96`; locate by anchor (A10.13). "WS3 … (its Task 4)" becomes "(its Task 5)" (WS3 Task 5 deletes the orchestrator). "LA1 creates `tests/conftest.py`" becomes "WS2 creates it; LA1 adds to it". Every OG becomes `apd-gauntlet compare-runs runs/<id>-<prev> runs/<id>-ws5-<tag> --gates eval/gates.yaml --strict`, where `<prev>` is the last accepted WS5 tag (for Task 1, the `v2.0.0a2` runs or `-next-baseline`); only the milestone exits (after Task 14, after the last Wave 3 task) compare against `runs/<id>-baseline` without `--strict`. OG preconditions: same Claude Code version, provider and session model for `<prev>` and candidate; `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, `CLAUDE_CODE_EFFORT_LEVEL` unset. Wave 3 runs each configuration three times and gates on the median. The re-measure rule names "WS1 or WS3 Task 8".
- **A10.2 Task 9.** `_existing_pack_signature` returns a 3-tuple `(packs, framework_version, content_sha256)` and is compared later in `build_domain_skill`; adding `BUILDER_FORMAT` changes both the tuple and the comparison. Task 9's tests build with framework `2.0.0`, so they pass only on `next` (packs declare `<3.0.0` there).
- **A10.3 Task 11 (Global Constraints rule).** Any later edit to the four shared skills or to a pack reruns `apd-gauntlet build-lens-skills examples/apd-20260601-claim-event-bus` and commits `.claude/skills/apd-domain/lens/*.md`. **CAT1 Task 2 gains this step** (it edits `apd-control-mappings/SKILL.md`; otherwise `test_committed_packets_match_rebuild` fails on CAT1's PR).
- **A10.4 Task 11 (output skeleton).** `lens_skills` appends `## Output skeleton (emit exactly this shape)`, generated from the schema enums with `agent`, `apd_tier` and `apd_goal` pre-filled. Test `tests/test_lens_skills.py::test_packet_ends_with_emittable_skeleton`.
- **A10.5 Task 14.** `test_resume_plan_lists_shard_labels` goes in `tests/test_cli_plan_run.py` (it uses `_write_run` and `FULL_CFG`). Registry R9's "`steps` lists the 18 agent steps only" becomes "agent steps with `code-recon` expanded per `recon_shards(cfg)` plus `code-recon-cross-repo`"; `build_resume_plan` must read `.apd-run.yaml`. Add N21's coverage and warning items to Tasks 13–14.
- **A10.6 Task 15 Step 1.** Grep `.claude/agents .claude-plugin .claude/skills tools/apd_gauntlet/lint_agents.py tools/apd_gauntlet/data/claude tests/test_lint_agents_receipt.py tests/test_doc_domain_pack_authoring.py docs/architecture.md`; the mentions in the workflow header comment, its `meta.description` and `tests/test_workflow_apd_gauntlet.py` are intended.
- **A10.7 Task 2.** "Inputs lines 46–54" becomes "the `## Inputs` list" of `apd-report-writer.md`.
- **A10.8 Wave 3 revert rule (DEC-22).** A failing tier first retries its OG one effort step up (`medium` → `high`, `high` → `xhigh`); if it still fails, set explicit `model: opus` with the WS3 effort — never restore an absent `model` (Task 23 makes `model` required). After Task 16, LA2's `test_model_precedence` keeps a default-path case through a fixture agent without `model`.
- **A10.9 Task 23.** Its audit-iteration criterion only fires with A10.1's `<prev>` + `--strict`. Record the Opus residue (adjudicator, report auditor, synthesizer) in the "Models and effort" table.
- **A10.10 Additions for the Sonnet/Haiku requirement.** Wave 2 starts with N14 and N15; N10–N13 become Tasks 15a–15d before Task 16; Wave 3b is N16 (Tasks 24–28). With N15 (`omitClaudeMd`), R5/R9 add "every agent also sets `omitClaudeMd: true`".
- **A10.11 Per-tier revert criteria (Tasks 16–23).** Base: any `compare-runs` exit 1 on either repetition for any of the four runs, against `<prev>`, with `--strict`, after the A10.8 ladder. Additionally revert if:

  | Task | Tier → target | Extra criteria |
  |---|---|---|
  | T16 | tier-1 lenses → sonnet/medium | `usage --expect-model` fails; per-lens first-pass invalid, lens retries or Python repairs above `<prev>`; tier cost not lower than `<prev>` |
  | T17 | tier-2 lenses → sonnet/medium | as T16, plus tier-2 cross-references to tier-1 ids below 90 % of `<prev>` |
  | T18 | tier-3 lenses → sonnet/medium | as T17 |
  | T19 | intake, code recon → sonnet/medium; TM recon → sonnet/low | `inventory_assets_ratio < 0.9`; `cev_entries_ratio < 0.9` or a new `not_analyzed` project; `tm_supplied_entry_jaccard < 0.95` |
  | T20 | TM author → sonnet/medium | `tm_grounded_ratio_delta_pts < −5`; Home Assistant's `tm-f8db6c3a` / `auth-1787eae1` contradiction lost downstream |
  | T21 | TM evaluator → sonnet/high; attack-path analyzer → sonnet/medium | that contradiction missing; `apath_findings_ratio` outside 0.9–1.1 |
  | T22 | domain auditor → sonnet/medium | improvements file invalid, or count outside ±30 % |
  | T23 | report writer → sonnet/medium | `audit_iterations_delta > 0`; `headline_overlap_pct < 80` |

- **A10.12 Cross-plan.** Task 1's `_plan(tmp_path, cfg)` helper already exists from WS1 (`tests/test_cli_plan_run.py`); do not redefine it.
- **A10.13 Anchors moved by WS1** (plan citation → current): `runTier` 425–475 → ≈ 700 (retry loop ≈ 717); attempt-0 writer 697–703 → ≈ 963–968; TM author 384–398 → ≈ 515–526; `canonicalize-threat-model` → ≈ 552–557; apath thunk 625–637 → ≈ 892–903; tmeval thunk 608–624 → ≈ 873–891; writer and audit loop 697–794 → ≈ 963–1055; remediation 785–791 → ≈ 1049–1054; code-recon phase 348–371 → ≈ 475–502; `pyStep` ≈ 228, `llmStep` ≈ 301; "after post-tier4" exists only after WS3. `plan_run.py`: 97–112 → 119–131; 159–180 → 184–205; 80–88 → 95–104; 143–150 → 166–174; 136–141 → 161–165; 48–56 → 52–66; 72–78 → 79–93. `cli.py`: `canonicalize` 1247 → 1298–1342; `validate-domain` 232–267 → 246–283; `_write_blocked_finding` 910 → 961; `FAIL [` 1458–1460 → 1519. `validate.py` `SYNTHESIS_ROLLUPS` 234 → 480; `extract_records` 85 → 87. `canonicalize_run` 272–310 → 424–475. `build_domain_skill.py`: `_render_surfaces_section` 121–141 → 131–152; `_pack_content_sha256` ≈ 154, `_existing_pack_signature` 177–204, compared ≈ 321–323; `_sidecar_frontmatter` 196–235 → 235–276; `build_domain_skill` 238 → 277.

## A11. LA1–LA3, non-provider items

- **A11.1 LA1 Task 4 and LA3 Task 7 (async tests).** pytest 9.1.1 fails bare `async def` tests ("async def functions are not natively supported"). Add `pytest-asyncio>=1.0` to the `dev` extra and `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`.
- **A11.2 LA1 Task 5 and WS6 Task 1 (validator routing).** `schema_for_run_file` (the shared lookup used by `validate` and `resume-plan`) maps `40-synthesis/decisions/*.yaml` to `decision-record.schema.json` and `40-synthesis/escalations/*.yaml` to `decision-escalations.schema.json`; `run_schema_pass` validates through it. Test: `schema_errors_for_file(run, "40-synthesis/decisions/finding-qa.all.yaml")` reports schema errors.
- **A11.3 LA1 Task 6 (`rubric_digest`).** With no bold lead phrase, use the bullet's first sentence (≤ 160 characters); fold `### <Severity>` sub-sections into their severity (the agentic-ai rubric has no bold bullets; pbm has `###` patient-harm sub-sections). Test all six bundled packs.
- **A11.4 LA1 Task 1 (secret-key regex).** The current regex rejects `context_tokens`. Use `(?i)(^|_)(api_?key|access_?token|token|secret|password)$`; name new numeric fields `context_window`.
- **A11.5 Pins (LA1 Task 2, LA2 Task 5, LA3 Task 8).** `claude-agent-sdk>=0.2.167,<0.3`, `textual>=8.2,<9`, `starlette>=1.0,<2`, `httpx>=0.27,<1`, `keyring>=25.7,<26`. CI runs the app tests on Python 3.10 and 3.12 (Starlette 1.8 and platformdirs 4.13 need 3.11; 3.10 resolves older versions).
- **A11.6 LA1 test helpers and fixtures.** The validator test constant is `FIXTURES`, not `FIX`; `tests/fixtures/runs/clean-run` has no `.apd-run.yaml`, so fixtures write a complete one (`run_id`, `domains`, `framework_version`); Task 8 inserts the finding-QA step after `repairTierGate(...)`; use `_text()` (not `WORKFLOW_JS`) and `_plan` (not `plan_json`); plan rows use the tier directory as their phase. Catalog packaging is already covered by `data/*.json` in `pyproject.toml`.
- **A11.7 LA3 Task 7 (Textual 8).** `Static` exposes `.content`, not `.renderable`.
- **A11.8 LA3 Task 3 (doctor).** The `agent-sdk` check verifies the Claude Code CLI bundled in the SDK wheel (2.1.300 in 0.2.167).
- **A11.9 LA3 Task 1 (`check_inputs`).** `check_inputs(inputs: Path) -> tuple[int, int]` calls `init_run.find_escaping_links(inputs)` (N1) and raises `InputsRejected` naming every escaping link; `create_run` then calls the unchanged `scaffold_run`, which refuses the same links, so `init-run` and `new` share one rule. Test `test_create_run_rejects_escaping_link`.

## A12. Decision models and Clef (LA1, WS6, WS2)

- **A12.1 LA1 Tasks 3, 4, 9 (provider facts, verified 2026-10-14).** Catalog rows (`verified_on: "2026-10-14"`):

  | Provider | Model | Context | Images | $/M input | Default |
  |---|---|---|---|---|---|
  | cloudflare | `clef` | 65536 | yes | 0.24 | yes |
  | cloudflare | `clef-flash` | 24576 | yes | 0.038 | |
  | cloudflare | `clef-omni` | 64000 | yes | 0.15 | |
  | typesafe | `jev-latest` | 32000 | no | 0.042 | yes |
  | openrouter | `typesafe/jev-1.13` | 32000 | no | 0.042 | yes |
  | openrouter | `~typesafe/jev-latest` | 32000 | no | 0.042 | |

  Delete the `cloudflare / typesafe/jev` row and `test_cloudflare_jev_uses_input_wrapper` (no Workers AI page lists it). Parse a `noul` answer from `answers[id]["noul"]`; `score` legends and probabilities are keyed by index strings. Raise `InvalidQuestion` for a choice with more than 255 options or a score outside 2–10 levels. Images: ≤ 4 per call, PNG/JPEG/WebP, ≤ 4 MiB and ≤ 16 MP each, ≤ 8 MiB decoded in total, request ≤ 13 MiB, remote URLs not accepted. `estimate_tokens` adds 1,024 per image; the client refuses above `context − 1024`. LA1 Task 9 records the ratio of the estimate to the reported `input_tokens` and confirms the Cloudflare `result`/`success` envelope; spec §5.2's open items shrink to that one.
- **A12.2 LA1 Task 6 and WS6 Task 2 (reuse keyed by content).** Each item stores `state_sha256` over the state, the question-schema hash, image digests and the model; reuse is per item and only changed items are re-decided (finding ids hash only `title|first_locator`, so after a repair the id is unchanged and a stale decision would otherwise be reused). Tests `test_changed_summary_redecides_one_item`, `test_unchanged_run_makes_no_calls`.
- **A12.3 LA1 Task 8 and WS6 Task 3 (finding QA's own switch, DEC-12).** `decision_model.tasks.finding-qa` takes `off | shadow`, default `shadow` when a provider is set; `active` is rejected; the workflow condition becomes `decideMode('finding-qa') !== 'off'`.
- **A12.4 WS6 (anchors and limits).** Replace line numbers with label and heading anchors (current: `isErr` ≈ 327; cluster candidates and adjudicate ≈ 779–795; tmeval thunk ≈ 873–891; apath thunk ≈ 892–903; audit loop ≈ 1000–1057; `build-report` calls ≈ 971, 979, 986, 1055; prephase-5 gate ≈ 758–770; `phase('intake')` ≈ 437–444; `run_schema_pass` ≈ 711–740). `_inputs.file_units` refuses images over 16 MP or over the per-request limits and records an `error` item.
- **A12.5 WS6 Global Constraints (truncation).** Replace "hosted Clef silently truncates `state` beyond 64k tokens" with: "Long text state is truncated to the model's window (Clef 65,536; Clef-flash 24,576; Clef-omni 64,000; Jev 32,000); a request whose media plus questions exceed the window fails. Count tokens and split before every call."
- **A12.6 WS2 Task 12, WS6 Task 1, registry R1/R8 (thresholds keyed by model, DEC-13).** A threshold entry gains `provider`, `model` (the provider-returned id) and `weights_revision`; `calibrate` exits 2 if the labelled records mix models; `TaskPolicy.calibrated` also requires the client's provider and model to match, otherwise every item escalates with a warning. Test `test_threshold_for_other_model_never_autos`.
- **A12.7 LA1 Task 4 (truncation detection).** A reported `input_tokens ≥ context − 16` marks the result `possibly_truncated`; the item escalates as an error. Test `test_possibly_truncated_escalates`.
- **A12.8 WS2 Task 4, WS6 Tasks 3–4 (decision spend visible).** `usage.yaml` gains `decision_models` (totals by task and by cost basis) and `cost_usd_all`; `compare-runs` reports the combined cost; the report header shows the decision cost; the LA2 ledger records the cost of `decide` steps.
- **A12.9 WS6 Task 3 (per-task model, DEC-11).** Run-config `decision_model.task_models: {<task>: <model id>}`, ids validated against the catalog; each task's client is built for its own model; consent covers the provider plus the set of models; thresholds keyed per A12.6. Tests `test_task_model_overrides_run_model`, `test_unknown_task_model_rejected`, and Clef-flash refused for an unsplittable IaC packet over 24,576 tokens.
- **A12.10 Small items.** Treat Workers AI `rejectIfBusy` rejections as retryable; accept `CLOUDFLARE_ACCOUNT_ID` from the environment; `keys test cloudflare` prints the required token permissions ("Workers AI - Read", "Workers AI - Edit") on a 403; plugin-channel docs prefer keychain or `op://` storage over environment variables, which every Bash-capable agent can read.
- **A12.11 New tasks.** N5 (LA1 Task 10, self-hosted provider), N6 (LA1 Task 11, AI Gateway), N7 (WS6 Task 14, `diagram-check`), N8 and N9 (WS6 Tasks 15–16, optional).

## A13. IaC (`2026-10-10-iac-terraform-opentofu-atmos-design.md`, IAC1–IAC4) and the code-flow draft

- **A13.1 IAC1 Tasks 2 and 7 (force provenance).** The `describe component` vector adds `--provenance=true` (Step 1 confirms the flag); the provenance regex accepts an optional `:col`; prefer `__atmos_provenance` from JSON output when present. Test `test_provenance_forced_on_against_client_config`.
- **A13.2 IAC1 Task 7.** `TEMPLATE_REMNANT_RE` also matches `(computed)` (Atmos's placeholder under the `warn` error mode). Test `test_computed_marker_is_unknown`.
- **A13.3 IAC1 Tasks 2 and 6 (Atmos defaults).** `ATMOS_ENV` adds `ATMOS_TOOLCHAIN_INSTALL=never` and `ATMOS_EDITION=<edition recorded in data/iac/tools.yaml>`; the sanitiser strips `toolchain`, top-level `dependencies` and `auth` from the copied `atmos.yaml` and records each as unknown `atmos_config_stripped`. Tests `test_atmos_env_registered` (telemetry, version check, toolchain and edition settings present) and, in Task 13, `test_toolchain_and_auth_make_no_connection` with a loopback HTTP sentinel.
- **A13.4 IAC1 Task 2.** The Trivy validator rejects `--quiet` (it hides parse errors); the builder test asserts it is absent.
- **A13.5 `data/iac/tools.yaml`, spec §14, Global Constraints (floors).** OpenTofu ≥ 1.12.6 (GHSA-q7j3-v8qv-22vq, arbitrary file read during git operations, affects < 1.11.10 / < 1.12.3 and all 1.10.x; 1.12.6 also fixes credential resend on redirect); Trivy ≥ 0.71.1 (CVE-2026-54448 Helm tar bomb < 0.71.0; CVE-2026-55092 path traversal < 0.71.1). Add `tested: {atmos: 1.232.0, tofu: 1.13.1, trivy: 0.75.0, checkov: 3.3.29, shellcheck: 0.11.0}`; `doctor` warns above tested versions. Replace the 1.10.6 examples with 1.13.1. CI keeps Atmos 1.231.0 until the probes pass on 1.232.0.
- **A13.6 IAC1 Task 13 (CI downloads).** Verify each binary against SHA-256 values committed in `data/iac/tools.yaml`, not only the release's checksum file; verify Trivy's cosign signature; never use `trivy-action` or `setup-trivy` (March 2026 malicious Trivy v0.69.4 and affected actions); pin every action by full commit SHA; install OpenTofu 1.13.1 so the live fetch test runs in CI.
- **A13.7 IAC1 Tasks 9 and 11 (transitive modules, DEC-24).** After `tofu get`, compare the sources in `.terraform/modules/modules.json` with the consented list. For any unconsented (transitive) source: remove that workspace's fetched tree, mark `not_fetched`, record `remote_module_not_fetched` with `transitive source not consented: <src>`; `collect_fetch_sources` lists those sources on the next `iac consent`. Tests `test_transitive_source_not_consented_rolled_back`, `test_consent_lists_transitive_sources_after_first_fetch`.
- **A13.8 IAC2 Task 3 (`neutralise`; scanners never fetch).** Trivy downloads remote modules during `trivy config` and this "cannot be turned off from the CLI"; Go programs bypass `HTTPS_PROXY` for `127.0.0.1` and `localhost`. Rewrite every remote module `source` absent from `modules.json` to `./.apd-unfetched/<name>` (an empty directory; one line, so line numbers hold). Test `test_scanners_never_contact_module_sources` with `source = "http://127.0.0.1:<sentinel>/m.zip"`, expecting zero requests. Docs keep the advice to run hostile repositories in a container with no network.
- **A13.9 IAC1 Task 9.** Never copy archives (`*.tgz`, `*.tar*`, `*.zip`) or files over 5 MB into workspaces; list them under `not_analysed`.
- **A13.10 IAC1 Task 8.** Export `read_consent(run_dir: Path) -> dict[str, Any]` (IAC3 Task 9 consumes it).
- **A13.11 IAC1 Task 11.** The stamp adds `data_sha256` over `data/iac/*.yaml`.
- **A13.12 All IaC Run lines and IAC1 Task 12.** `/home/claude/venv-apd/bin/...` and the old scratchpad tool paths do not exist; use the venv's `pytest` and `PATH="$APD_IAC_TOOLS_BIN:$PATH"`. Anchors: `meta.phases` (`phases: [`); setup — after the last setup step (`prepare-run`, then `build-lens-skills`), before `phase('intake')`; `plan_run.py` — after the last setup row; `running-the-gauntlet.md` — by row text; run-config — anchor on `"infrastructure"` (LA1 and CAT1 edit the schema first).
- **A13.13 IAC2 Task 1.** Route `schema_for_run_file` through `EVIDENCE_INDEXES` for keys under `00-context/`; `_validate_context_ids` stays code-only. Locate by function: `CODE_EVIDENCE_INDEX_FILENAME`, `_code_evidence_index_path`, `_validate_code_evidence_index`.
- **A13.14 IAC2 Task 3.** Module-level Checkov results (`('CKV_TF_1', 'm')`) map to address `module.<name>`. Test `test_checkov_module_check_address`.
- **A13.15 IAC2 Task 5 (DEC-24).** Insert the `ci` stage after `inventory` (it needs the execution points `inventory` produces); use only the `# apd-recorded shellcheck-disable=` neutraliser (the `# shellcheck-disable-recorded=` form raises SC1073/SC1072 on ShellCheck 0.9.0 and 0.11.0); keep levels error, warning and info (SC2086 is `info`); the scanner severity enum gains `INFO`.
- **A13.16 IAC2 Task 8, IAC3 Tasks 5–7.** End each with `python -I -m apd_gauntlet.bundle --sync`, commit the packaged copies, add `tests/test_bundle.py` to the Run line.
- **A13.17 IAC2 Task 8 (raw fallback for Atmos).** For an `unresolved-raw` Atmos root, read `<root>/atmos.yaml`, `<stacks.base_path>/**/*.y*ml` and `<components.terraform.base_path>/**/*.tf`.
- **A13.18 IAC3 Task 4, IAC4 header and Task 6.** WS6 numbering: `iac-triage` is WS6 Task 12 (not 11); labelling is Task 13 ("Tasks 11–12" → "12–13").
- **A13.19 IAC3 Task 9.** LA3's TUI is the package `app/tui/{__init__,app,screens}.py`; web tests are `tests/app/web/test_routes.py`.
- **A13.20 IAC4 Task 1.** Read `licence` from the raw manifest (`CorpusEntry` drops it); entries whose root uses `../` modules put the whole checkout in `inputs/`.
- **A13.21 IAC4 Task 1.** For Atmos entries the 1.7.1 baseline is `terraform: ["<root>/components/terraform/**/*.tf"]`, with stacks as ordinary inputs.
- **A13.22 IAC4 Task 2.** Missing tools raise WS2 Task 13's existing `MetamorphicError` (do not define a new one); confirm `metamorphic run` maps it to exit 2 and add `test_missing_tool_exits_2`.
- **A13.23 IAC4 Task 6 Step 7.** Create `### Beta gates (v2.0.0b1)` in RELEASING.md (no such checklist exists).
- **A13.24 IAC4 Task 6 Steps 2 and 6.** Run baseline and candidate twice per entry; gate on mean per-category recall; `iac-index` runs once (deterministic).
- **A13.25 IAC3 Task 9 docs.** `apd-gauntlet run --yes` never grants `iac_module_fetch`.
- **A13.26 IaC docs.** The `agentic-ai`, `mobile-applications` and `security-tooling` packs declare no internet attacker position, so IaC internet edges never start in those runs.
- **A13.27 WS2 Task 10 and code-flow CF3 (freeze scope).** Adding `data/codeflow/context-params.yaml` after the 2.0 freeze changes WS2's tunables hash and makes every held-out `eval run` exit 2. Give `eval freeze` a per-family scope (`iac`, `catalog`, `decide`, `codeflow`) before CF3, or use `--new-heldout-set` for code-flow only.
- **A13.28 M5 merge order.** Merge one at a time and rebuild the bundle after each: IAC3 T5 with CAT3 T6; WS6 T4, IAC3 T8 and CAT3 T14; IAC3 T6 with CAT3 T2–T4; IAC3 T7, WS6 T7 and CAT3 T9.

## A14. Cross-cutting

- **A14.1 CAT1 (new Task 12a).** Consolidated plan task N17 (record ATT&CK, CAPEC and CWE versions); CAT1 Task 12 then compares recorded versions.
- **A14.2 CAT3 Task 11 (DEC-30).** Catalog control rows (for example `ctl_nist_csf2`) render apart from the "Compliance crosswalk" sub-tab, labelled "catalog threat control refs — not an attestation".
- **A14.3 Master plan R10.** Add rows: "0016, 0018: unused (reserved 2026-06; never landed)"; "0031–0039: code-flow (CF1–CF4)"; "0040: healthcare / clinical-FHIR pack (N22)". N5 and N6 amend ADR-0024; N7–N9 amend ADR-0029; N1 needs no ADR.
- **A14.4 Threat-catalog spec §8.6.** The catalog key `capec` is not consumed by the CAPEC bridge in 2.0 (CAT3 Task 11 excludes it); relabel "CAPEC bridge input" accordingly, and note that catalog-derived ATT&CK ids do not reach the detection overlay in 2.0 (DEC-30).
- **A14.5 Master plan Global Constraints.** Add the external tool floors, Python pins and the "plan files are linted explicitly" rule from the consolidated plan's Global Constraints.
- **A14.6 Master plan registry additions.** R1: `usage … --expect-model <agent-glob>=<model-prefix>` (N10). R4: `decision_model.task_models`, `decision_model.cache` (N8), `decision_model.tasks.finding-qa` (`off|shadow`), `decision_model.tasks.diagram-check` (N7), provider `selfhosted` (N5). User config: `decision_model.base_url`, `context_window`, `images`, `ca_bundle`, `cloudflare_gateway_id`, `gateway_log_payloads`. R7: `decision-record` gains `calibrated` (required), `endpoint`, per-item `state_sha256`, `possibly_truncated`; threshold entries gain `provider`, `model`, `weights_revision`; `run-attempts` gains `tier_repairs`, `lens_reruns`, optional `llm_first_pass_invalid`, `repairs`, `python_repairs`; new file `40-synthesis/routing.yaml` (N9, outside `decisions/`); `code-evidence-index` gains optional `repos[].coverage`; `metrics` gains real `findings_pre_dedup` and `capabilities_pre_dedup`. R8: `eval/gates-wave3.yaml`; `docs/superpowers/ledgers/`. R9 (agents): every agent sets `omitClaudeMd: true` (N15).

- **A14.7 Master plan: remove the company name (2026-10-15; applied 2026-10-16 in PR #48, merge `0e72b9b`; Phase 2 skips it).** In "Decisions still needed" (the first row, on where Clef runs) and in "Operator work outside the code" (the "Hosting decision for Clef" bullet), replace each occurrence of the company name with neutral wording: "reviews of PHI-handling systems", "the client's Cloudflare agreements" and "a PHI review". Verify with `git grep -n -i -E -f .superpowers/redact-patterns.txt -- .`, which must print nothing. The pattern file is local only (`.superpowers/` is gitignored); never commit the pattern. This cleans the current tree only; the two commits that introduced the text stay in history (see the consolidated plan's Phase 0 note on history).

## A15. State after the 1.7.1 release (2026-10-17)

Facts verified 2026-10-15 to 2026-10-17, after `v1.7.1` shipped; sources are in parentheses. Code anchors in this section are on `main` (`0145775`) and `next` (`ad9ec66`), where the runner has 1,126 lines; for `.claude/workflows/apd-gauntlet.js` and `tools/apd_gauntlet/validate.py` they replace the hints in A7–A14. Plan line hints stay on `origin/next` `0642673`. Locate every edit by anchor. "(record)" marks an entry that changes no plan text beyond a dated status note.

**Records**

- **A15.1 (record) The 1.7.0 runner cannot run on current Claude Code (PR #50).** In the Workflow runtime `agent()` and `parallel()` return Promises, and `.claude/workflows/apd-gauntlet.js` has no `await` at tag `v1.7.0`. Every step therefore "passed" at once, and every run failed in about 24 ms at the report-audit gate; a probe workflow confirmed that `agent()` returns a Promise. #50 fixed it (merged to `main` as `377a7d9`, released in 1.7.1). No 1.7.0 live run can be produced, so every live 1.7.0 baseline in the plans becomes a 1.7.1 baseline (A15.13–A15.20, A15.29). Offline engine-only comparisons against the 1.7.0 engine (consolidated plan Appendix 1, Task 1.4) stay valid.
- **A15.2 (record) The runner after #50.** It has 1,126 lines and 62 `await`s. `tierGate`, `regate`, `repairTierGate` and `runTier` are `async` and await every dispatch, for example `const gate = await tierGate(phaseName, tierDir, '');`, `await repairTierGate(phaseName, tierDir, lenses, gate);`, `const rp = await pyStep('resume-plan', …)` and `await parallel(…)`. `runTier`'s lens-retry loop is a `for` loop, because `forEach` cannot await. `pyStep`, `llmStep` and `guard` stay synchronous, because tests rebuild them under node with a synchronous stub. `tests/test_workflow_runner_awaits.py` (11 tests) is the tripwire: its static check fails on any un-awaited dispatch. The JS that WS1 Tasks 2–3 quote is history; the shipped code is the awaited form.
- **A15.3 `validate.py` after #50 (CAT2 Task 7, CAT3 Tasks 3 and 8; amends A7.56 and the `validate.py` rows of "A7 anchors after WS1").** `run_cross_file_pass` resolved every `cross_references` and `merged_from` entry against finding ids, although `capability.schema.json` requires a capability's `cross_references` to be capability ids, so the whole-run gate before synthesis halted any run with a capability-to-capability reference. #50 resolves them per record kind. `_deduped_record_ids(run_dir, kind)` is the shared reader of `40-synthesis/deduped-findings.yaml` and `deduped-capabilities.yaml` for `run_cross_file_pass`, the report-data check and the domain-improvements check; a malformed or unreadable file gives no ids.
  - Anchors: `_validate_rollups` `validate.py:691`; `run_schema_pass` `:711` (its `00-context` rollup call `:736`, as A7.56 says); `run_semantic_pass` `:773`; `_deduped_record_ids` `:1039`; `run_cross_file_pass` `:1069` (its semantic re-run `:1155`).
  - CAT2 Task 7 (`_validate_tm_catalog_fields`) and CAT3 Task 8 (`_check_catalog_dismissals`, called from `run_cross_file_pass`) resolve each new reference against the ids of the record kind it names, read deduped ids only through `_deduped_record_ids`, and locate their edits by these function names.
  - A7 anchors, CAT3 T3 row: "`:1058` (`*, strict_excerpts`; semantic re-run at `:1147`)" → "`:1069` (`*, strict_excerpts`; semantic re-run at `:1155`)".
- **A15.4 (record) Repository state on 2026-10-17 (master plan Task 3 Step 4).**
  - `v1.7.1` is published: the tag is on `main` `0145775`, PyPI lists 1.7.0 and 1.7.1, and the release is marked Latest. PR #52 merged `main` into `next` (`ad9ec66`); `next` carries 1.7.1 in all five version places.
  - Ruleset `next-protection-rules` protects `next`: a pull request with 1 approval; required checks `test (3.10)`, `test (3.11)`, `test (3.12)`, `wheel-smoke`, `bundle-rebuild-diff`, `validate-example` and `plugin-manifest`; no force-push or deletion. The owner merges plan PRs by bypassing the approval rule. `main` is not protected, and no ruleset limits `v*` tags yet.
  - `fix/report-freshness-gate` and `feat/plugin-channel-guardrails` are deleted. `fix/ws1-1.7.1`, `fix/workflow-await-dispatches`, `chore/release-1.7.1` and `chore/merge-1.7.1-into-next` are merged and can be deleted. History rewrite: decided against (DEC-34).
  - PRs since 2026-10-14: #48 (A14.7 on `next`), #49 (WS1, N1 and N3 into `main`), #50 (A15.1–A15.3), #51 (the 1.7.1 release: version bump, CHANGELOG per A8.7 and N2, RELEASING note per A8.4, domain-skill restamp), #52 (consolidated Task 1.8, with A8.4's CHANGELOG rewording).
  - Master plan Task 3 Step 4 gains: "(2026-10-17: `next` is protected by ruleset `next-protection-rules`; the `v*` tag ruleset is still open, consolidated Task 0.2 Step 1.)"
- **A15.5 (record) WS1 executed and released (updates A8; WS1 plan, master plan M1 and Task 2).** WS1 Tasks 1–11 plus N1 (Task 11b) and N3 shipped in #49, the fixes of A15.1–A15.3 in #50 and the release in #51; #52 merged `main` forward.
  - WS1 plan: add under the header "Executed and released as v1.7.1 (#49–#52; register A8, A15)" and tick its tasks. The four "Step 6: Operator — compare PR group … against the 1.7.0 baseline" steps (Tasks 2, 4, 7 and 10) and Task 12 Step 1's compare-runs check are marked "not run: replaced by A8.1's substitute gate; no 1.7.0 live run can exist (A15.1)".
  - Master plan Task 2 Steps 1–4: tick, noting "one branch and PR #49 (A8.3); substitute gate (A8.1); tag `v1.7.1`; merge-forward #52 (A8.4)".
  - Master plan M1 row: Contents "Baseline captured on 1.7.0; WS1" → "WS1 (released as v1.7.1)"; Exit gate "WS1 tests green; `compare-runs` 1.7.1 vs 1.7.0 passes the gates" → "WS1 tests green; the 1.7.1 substitute gate (A8.1): offline regression passed (consolidated Task 1.4), live run clean (consolidated Task 1.5 Steps 1–4), metrics comparison inconclusive against the 1.4.0-era example (A15.9); 1.7.1 released on that basis (consolidated DEC-1)".
  - A8.2, A8.3 and A8.8 are done (#49, #51). A8.5 stays a record. A8.6 still applies at consolidated Task 3.4, and A8.9 at WS3 Task 3.
- **A15.6 A8.1 amended.** "Keep the 1.7.0 and 1.7.1 run directories and telemetry so WS2's `compare-runs` can run against them later; a retroactive failure ships as 1.7.2." → "Keep the 1.7.1 run directory `runs/apd-20261016-ws1-gate` for WS2 (it has no telemetry); no 1.7.0 live run exists (A15.1). A 1.7.1 defect found later ships as 1.7.2." The 1.7.1 substitute gate: the offline regression passed (consolidated Task 1.4); the live run completed clean (Task 1.5 Steps 1–4); its metrics comparison (Step 6) was inconclusive against the 1.4.0-era example (A15.9); 1.7.1 was released on that basis (DEC-1).
- **A15.7 A8.4 done (record).** #52 took 1.7.1 in all five version places and reworded next's CHANGELOG bullet; #51 added the RELEASING.md step-5 note. Phase 2 marks WS1 Task 12 Step 7 and master plan Task 2 Step 4 done, with A8.4's text as the record; no other file changes.
- **A15.8 A8.7 done (record).** #51 wrote the `## v1.7.1` CHANGELOG section per A8.7 and N2. Phase 2 marks WS1 Task 12 Step 3 done with that note; no other file changes.
- **A15.9 (record) Consolidated Task 1.5 and the committed example.**
  - Run `runs/apd-20261016-ws1-gate` completed: `validate` printed `Clean.`, `audit-report` passed 23/23, all 213 threat-model entries carry minted `tm-` ids, and a cross-session resume skipped 13 completed agent steps.
  - Step 6 was inconclusive. Against the committed example, critical plus high went 11 → 40 (the example's only critical, an unsigned mutable audit log, is covered by three high findings: `immut-5ab6b159`, `nonrep-a4023adf`, `intg-6efd4065`), and the blocked share went 15.8 % → 34.5 %. The run had no code recon.
  - `examples/apd-20260601-claim-event-bus/expected` was produced at framework 1.4.0 (its `.apd-run.yaml`), with a code-evidence index. It is not a 1.7 baseline, and no plan may compare against it as one.
  - The run directory is the first 1.7.1 data point for WS2 (A15.14; consolidated Task 3.2 Step 2, A15.29).
- **A15.10 (record) Cost of a live run; DEC-35 proposed (consolidated Part C, Part D, J.1 and J.2; once decided, the comparison bullets of the master plan, WS2, WS3, WS5 and WS6).**
  - One live 1.7.1 run on the claim-event-bus inputs, without telemetry: 69 dispatches over two sessions (29, then 40 after a resume that skipped 13 agent steps), about 6.2 million subagent tokens and about 3.1 hours of wall-clock time. The report auditor needed 3 attempts and ended with non-blocking semantic residuals.
  - An SCP of 8 runs is therefore about 50 million subagent tokens and about 25 hours. This raises the priority of WS3 and WS5, the cost waves.
  - **DEC-35 (proposed; the owner decides): SCP run-set size.** Proposed default: claim-event-bus and the private PBM review, two runs each (4 runs; about 25 million tokens and 12.5 hours), plus any committed example a task's own gate criteria name (for example Home Assistant for WS5 Tasks 14, 19 and 20). Milestone exits and WS5 Wave 3 keep the full set (8 runs; 12 with Wave 3's three repetitions). Until the owner decides, the plans' 8-run set stands.
  - Phase 2 changes no plan text for A15.10: the consolidated plan's Part C, Part D (DEC-35), J.1 and J.2 already carry it (A15.31). Once the owner decides DEC-35, a later docs PR applies the decision to the comparison bullets of the master plan, WS2, WS3, WS5 and WS6.
- **A15.11 New files under `docs/superpowers/` are git-ignored (commit `f465d5d`, on `main` and `next`).** New plan, spec and ledger files are added with `git add -f <path>`; edits to files already tracked there are tracked normally.
  - Master plan Task 10 Step 2: append "Add each new plan file with `git add -f`."
  - Master plan registry R8 (the `docs/superpowers/ledgers/` entry from A14.6): append "(new files there need `git add -f`)".
  - The consolidated plan's own sites are in A15.30.
- **A15.12 Running a changed runner.** `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started. To exercise a changed runner, run it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or start a new session. This applies to every SCP and every OP step that runs a modified runner. Append that rule as one sentence to:
  - master plan Global Constraints, the "Every behaviour-changing task ships behind `compare-runs`" bullet;
  - WS3 Global Constraints, "Each behaviour-changing task ends with master plan Task 4 Step 2"; WS5 Global Constraints, the OG bullet; WS6 Global Constraints, "Every behaviour-changing task ends with `compare-runs`";
  - CAT2 "Comparison policy"; CAT3's OG bullet; CAT4 "Measured with the WS2 harness"; IAC1 "Behaviour-changing tasks gate against the previous accepted state"; IAC2 and IAC3 "Tasks that change what agents read";
  - WS2 Task 7 Step 6; IAC4 Task 6 Steps 2 and 6.

**1.7.1 baselines (A15.1)**

- **A15.13 Master plan.**
  - Architecture: "passes the comparison gates against the 1.7.0 baseline" → "passes the comparison gates against the 1.7.1 baseline (A15.1)".
  - Global Constraints, "Every behaviour-changing task ships behind `compare-runs`": "Each milestone exit gates against the 1.7.0 baseline." → "Each milestone exit gates against the 1.7.1 baseline (Task 1)."
  - Global Constraints, "Gates that a baseline cannot measure": "against the 1.7.0 baseline" → "against the 1.7.1 baseline" ("1.7 runs record no retries" stays true of 1.7.1).
  - Milestones: M6 "Held-out IaC recall ≥ 1.7 baseline" → "Held-out IaC recall ≥ 1.7.1 baseline"; M8 "CF4 evaluation vs the 1.7 CBM-only baseline" → "CF4 evaluation vs the 1.7.1 CBM-only baseline". M1 is in A15.5.
  - Task 1: title "Capture the 1.7.0 baseline (operator)" → "Capture the 1.7.1 baseline (operator)"; Step 2 "Run the baseline set twice each on 1.7.0:" → "Run the baseline set twice each on 1.7.1 (`pip install apd-gauntlet==1.7.1` and the 1.7.1 plugin from `main`):".
  - Task 8 Step 1: "run the 1.7 raw-read baseline" → "run the 1.7.1 raw-read baseline". Task 10 Step 3: "against the 1.7 CBM-only baseline" → "against the 1.7.1 CBM-only baseline".
  - "Decisions taken while planning", item 7: "milestones compare against 1.7.0." → "milestones compare against the 1.7.1 baseline (A15.1)."
  - The five gate bullets under "The comparison gates" are a fixture (WS2 Task 5) and stay unchanged.
- **A15.14 WS2.** Task 7 Step 6 Expected: "gates 4–5 unavailable against the 1.7.0 baseline" → "gates 4–5 unavailable against the 1.7.1 baseline". Task 14, under its heading, add: "The master plan Task 1 baselines are 1.7.1 runs (A15.1). `runs/apd-20261016-ws1-gate` is one more 1.7.1 run of claim-event-bus (single run, no code recon, no telemetry)."
- **A15.15 WS3.** Global Constraints, "Comparison baseline": "The milestone exit (Task 9) gates against the 1.7.0 baseline." → "The milestone exit (Task 9) gates against the 1.7.1 baseline." Task 9: title "Measure Wave 1 against the 1.7.0 baseline and record it" → "Measure Wave 1 against the 1.7.1 baseline and record it"; Step 2 "against the 1.7.0 baseline" → "against the 1.7.1 baseline"; Step 3 "the median cost on the 1.7.0 baseline and on WS3" → "the median cost on the 1.7.1 baseline and on WS3". A9.17's static dispatch counts stay; they come from the source, not from runs.
- **A15.16 WS5 (amends A10.1).** After "only the milestone exits (after Task 14, after the last Wave 3 task) compare against `runs/<id>-baseline` without `--strict`" add "; `runs/<id>-baseline` is the 1.7.1 set from master plan Task 1 (A15.13)". No WS5 text names 1.7.0.
- **A15.17 WS6.** Global Constraints: "milestone exits (M5 shadow, M6 enablement) gate against the 1.7.0 baseline." → "milestone exits (M5 shadow, M6 enablement) gate against the 1.7.1 baseline." Task 12 Step 7: title "M5 exit against the 1.7.0 baseline" → "M5 exit against the 1.7.1 baseline"; in its `compare-runs` command, `<1.7.0-baseline>` → `<1.7.1-baseline>`. Task 13 Step 8: the same two replacements ("WS6 part of the M6 exit against the 1.7.1 baseline").
- **A15.18 CAT1 Task 5 Step 6 Expected.** "`pass_with_gaps` is allowed only against the 1.7.0 baseline;" → "`pass_with_gaps` is allowed only against the 1.7.1 baseline;"; "where the 1.7.0 run cites bare LLM ids" → "where the 1.7.1 run cites bare LLM ids". The Review Focus case "A 1.7 baseline citing 2021 Top 10 ids" stays.
- **A15.19 IAC4 (amends A13.21).**
  - Goal: "against the 1.7 raw-read baseline" → "against the 1.7.1 raw-read baseline".
  - Global Constraints, "Baseline.": "computed for 1.7's raw-read path" → "computed for 1.7.1's raw-read path"; the quoted M6 text becomes "Held-out IaC recall ≥ 1.7.1 baseline" (A15.13).
  - Review Focus: "with no recorded 1.7 run for an entry" → "with no recorded 1.7.1 run for an entry".
  - Task 6 Step 2: title "Run the 1.7 raw-read baseline" → "Run the 1.7.1 raw-read baseline"; "with `apd-gauntlet==1.7.0` and the 1.7.0 plugin" → "with `apd-gauntlet==1.7.1` and the 1.7.1 plugin" (the 1.7.0 runner cannot run, A15.1).
  - Task 6 Step 6 Expected: "≥ the 1.7 baseline" → "≥ the 1.7.1 baseline"; Step 8 commit message "against the 1.7 baseline" → "against the 1.7.1 baseline".
  - A13.21: "the 1.7 baseline is" → "the 1.7.1 baseline is". The "1.7 glob form" of `baseline_infrastructure` names a config shape and stays.
- **A15.20 Specs.** IaC spec §13.2, "Baseline." bullet: "computed for 1.7's raw-read path on the" → "computed for 1.7.1's raw-read path on the". Code-flow spec §10, "Baseline." bullet: "The 1.7 CBM-only path, scored on the same labels." → "The 1.7.1 CBM-only path, scored on the same labels (the 1.7.0 runner cannot run; register A15.1)." The threat-catalog spec's "1.7 baselines" (F6, §10) stay.

**Workflow edits after #50 (A15.2)**

- **A15.21 Rules for every task that edits the workflow** (WS2 T7; WS3 T1, T3, T7; WS5 T1–T8, T11, T12, T14; WS6 T5–T12; LA1 T8; IAC1 T12; IAC3 T5; CAT2 T9; CAT3 T5, T8; CAT4 T12; Part G N7, N11). WS3 T4 is not one: A9.13 replaces its text and leaves the workflow alone, and the runner already dispatches the repair with `agentType: 'apd-tier-repair'`. The task-specific entries A15.22–A15.27 apply these rules:
  - Quoted call sites and inserted dispatches use the awaited form: `await pyStep(…)`, `const x = await pyStep(…)`, `await llmStep(…)`, `await parallel(…)`. Inside a `parallel` thunk a dispatch stays `return <dispatch>(…)`.
  - A new helper that consumes a dispatch result is an `async function <name>(…)`. Its name joins `ASYNC_HELPERS` (read by `test_helpers_that_consume_a_dispatch_are_async` and `test_no_other_function_is_async`) and `CALLS` in `tests/test_workflow_runner_awaits.py`. An `async` callback (an `async` thunk, `.map(async …)`) fails `test_no_other_function_is_async`; put the body in a named async helper instead.
  - A plain helper that only returns a dispatch, as `pyStep` does, joins `PASS_THROUGH` and `CALLS`; its callers await it. `pyStep`, `llmStep` and `guard` never await (WS3 Task 1 rewrites `pyStep`'s prompt and dispatch inside that rule).
  - A task that adds, removes or renames a dispatch label of the harness's green run, or changes a parallel group, updates `EXPECTED_GREEN_LABELS` (52 labels today), `LENS_GROUPS`, `LARGEST_PARALLEL_GROUP = 3` and the label slices of the node tests in the same commit. The harness `ARGS` set no threat model, crown jewels, decision model, catalog or infrastructure, so steps behind those switches stay out of the green list. The catalog is the exception from CAT4 Task 12 on: an absent `threat_catalog` then means `open`, so its two steps join the green list unless the harness `ARGS` set `threat_catalog: 'off'` (A15.27).
  - Workflow line numbers in the plans and in A7 anchors, A9.1, A9.15, A10.13 and A12.4 are shifted (A15.28).
- **A15.22 WS2 Task 7 (amends A9.3).**
  - A9.3's New text becomes: "After `const gate = await tierGate(phaseName, tierDir, '');` insert `if (isErr(gate)) attempts.tier_gate_failures.push(tierDir);` before `await repairTierGate(phaseName, tierDir, lenses, gate);`; leave `tierGate` and `regate` unchanged."
  - Interfaces: "In `runTier`'s `forEach`:" → "In `runTier`'s lens-retry `for` loop (where `r` is `receipts[i]`):"; the closeout block's first line `pyStep('summarize', { phase: 'closeout', label: 'summarize', alwaysRun: true,` → `await pyStep('summarize', { phase: 'closeout', label: 'summarize', alwaysRun: true,`.
  - Files: `:242`, `:425-475`, `:736` and `:844-846` → the anchors `function isErr`, `async function runTier`, the audit loop and `await pyStep('summarize'` (A15.28). No dispatch label changes.
- **A15.23 WS3 Task 3.**
  - Files: "in WS1's `tierGate`, `pyStep('validate', …)` becomes `pyStep('tier-gate', …)`" → "in WS1's `tierGate`, `return await pyStep('validate', …)` becomes `return await pyStep('tier-gate', …)`". The canonicalize steps removed are the `await pyStep('canonicalize', …)` in `runTier` and the one in `regate` (A9.11); `regate` stays `async`, because it still awaits `tierGate`.
  - Step 3 (each Old is the verbatim start of the call; the rest of each object literal stays): "`pyStep('prepare-run', {phase: 'setup',`" → "`await pyStep('prepare-run', {phase: 'setup',`"; "`tierGate` becomes `pyStep('tier-gate', {phase: 'canonicalize',`" → "`tierGate` returns `await pyStep('tier-gate', {phase: 'canonicalize',`"; "`pyStep('closeout', {phase: 'closeout',`" → "`await pyStep('closeout', {phase: 'closeout',`". In the post-tier4 block, `let pt = pyStep('post-tier4', {` → `let pt = await pyStep('post-tier4', {` and `pt = pyStep('post-tier4', { /* same opts */` → `pt = await pyStep('post-tier4', { /* same opts */`; the synthesizer fallback dispatch stays awaited.
  - Files and Step 1 gain `tests/test_workflow_runner_awaits.py`. In `EXPECTED_GREEN_LABELS`: `"validate-scaffold", "build-domain-skill", "validate-domain"` → `"prepare-run"`; each tier's `"canonicalize-<tierDir>", "validate-<tierDir>"` → `"tier-gate-<tierDir>"`; `"assemble-c4", "canonicalize-tmeval", "rollup"` → `"post-tier4"`; `"canonicalize-dimpr", "summarize", "validate-final"` → `"closeout"`. The slices of `test_failed_lens_is_retried_after_the_fan_out`, `test_rejected_lens_dispatch_becomes_null_and_is_retried` and `test_red_tier_gate_is_repaired_before_the_next_tier` (its responder key and its `-after-repair` labels) take the `tier-gate-` labels and lose the canonicalize ones.
- **A15.24 WS3 Task 7.** With `domain_improvement_capture` absent from the harness `ARGS`, `domain-coverage-delta` and `domain-auditor` leave `EXPECTED_GREEN_LABELS`; add `tests/test_workflow_runner_awaits.py` to Files. Inside the new condition the capture steps stay `await pyStep('domain-coverage-delta', …)` and `await llmStep('apd-domain-auditor', …)`.
- **A15.25 WS5 Wave 2 dispatches.**
  - Task 1: `pyStep('xref-digest', { phase: phaseName, …` → `await pyStep('xref-digest', { phase: phaseName, …`; `xref-digest-20-scalability` and `xref-digest-30-auditability` join `EXPECTED_GREEN_LABELS` before those tiers' lens fan-outs.
  - Tasks 2, 3, 5, 6 and 11: each inserted `pyStep(…)` is `await pyStep(…)`. `report-digest`, `render-threat-model-authored`, `render-threat-model-coverage-report`, `render-advisory-report-attempt-0`, `-1` and `-2`, and `build-lens-skills` join `EXPECTED_GREEN_LABELS` at their positions.
  - Tasks 4 and 7 (apath thunk) and Task 8 (tmeval thunk): a dispatch before or after the thunk's existing dispatch makes the thunk read a receipt. Move each thunk's body into a named helper, `async function apathBranch()` and `async function tmevalBranch()`, that awaits every dispatch and returns the analyzer's or the evaluator's receipt. The thunks become `function () { return apathBranch(); }` and `function () { return tmevalBranch(); }`, and both names join `ASYNC_HELPERS` and `CALLS`. `tm-candidates` joins `EXPECTED_GREEN_LABELS` before `tmeval`; the apath steps do not (the harness has no crown jewels).
  - WS3 Task 1's dispatch-trace harness (`tests/js/workflow_dispatch_trace.mjs`, used by the WS3, WS5 and WS6 trace-order tests): `parallel: (ts) => ts.map((t) => t())` → `parallel: (ts) => Promise.all(ts.map((t) => t()))`. A thunk now returns its helper's Promise, and the synchronous stub does not wait for it: once `tmevalBranch` awaits twice before the evaluator (WS6 Task 8's `decide-tm-screen`, A15.26), the trace lists `assemble-c4` before `tmeval` (checked under node). Phase 2 writes the change into WS3 Task 1's harness code block, where it changes no trace; if WS3 Task 1 has already shipped, it goes in the commit that creates the first of these helpers (WS5 Task 4's `apathBranch`).
  - CAT3 Task 8 Files: "(the tmeval `llmStep` instruction WS5 Task 8 wrote; at `856ea96` the thunk is `:607-624`)" → "(the tmeval `llmStep` instruction WS5 Task 8 wrote, inside `async function tmevalBranch()` after WS5 Task 8 (register A15.25); locate it by that anchor)". Only the instruction text changes, so no `await` or label changes.
  - Task 14: `const rs = parallel(shards.map(...))` → `const rs = await parallel(shards.map(...))`. The shard labels (`code-recon-<id>`, plus `code-recon-cross-repo` with two or more repos) replace `code-recon` in `EXPECTED_GREEN_LABELS` per `recon_shards` for the harness `ARGS`. The shard group joins the listed parallel groups, and `LARGEST_PARALLEL_GROUP` rises when a test drives more than three shards.
- **A15.26 WS6 Tasks 5–12 (`decideStep`).** `decideStep` stays a plain function that returns `pyStep('decide', …)` or `null`. Task 5 adds `decideStep` to `PASS_THROUGH` and `CALLS` in `tests/test_workflow_runner_awaits.py`. Every call is the statement `await decideStep(…);`. Task 7's `asset-match` is the first statement of the crown-jewels branch in `apathBranch`, and Task 8's `tm-screen` sits in `tmevalBranch` before the evaluator (A15.25; create the helper as there if it is absent). The harness sets no `decision_model`, so `EXPECTED_GREEN_LABELS` is unchanged.
- **A15.27 LA1 Task 8 (amends A11.6), IAC1 Task 12, CAT2 Task 9, CAT3 Task 5, CAT4 Task 12.**
  - LA1 Task 8 Interfaces (the Old is the verbatim start of the call; the rest of the object literal stays): "one `pyStep('decide', {phase, label: 'decide-finding-qa-' + tierDir,`" → "one `await pyStep('decide', {phase, label: 'decide-finding-qa-' + tierDir,`". The step sits inside `runTier` after `await repairTierGate(phaseName, tierDir, lenses, gate);`; A11.6's "after `repairTierGate(...)`" means that statement.
  - IAC1 Task 12: `const iacReceipt = pyStep('iac', {` → `const iacReceipt = await pyStep('iac', {`.
  - CAT2 Task 9: `const cs = pyStep('catalog', {` → `const cs = await pyStep('catalog', {`. Files: "before `pyStep('author-threat-model'` (`:385-389`)" → "before `await pyStep('author-threat-model'`"; `:131-132` and `:384` → the anchors `const runDir` and `phase('threat-model-author')` (A15.28).
  - CAT3 Task 5: `const sl = pyStep('catalog', {` → `const sl = await pyStep('catalog', {`.
  - All four steps sit behind switches the harness leaves off, so `EXPECTED_GREEN_LABELS` is unchanged until CAT4 Task 12 turns the catalog on by default (next bullet). Their text tests (`"pyStep('iac'" in text`, `"pyStep('catalog', { phase: 'canonicalize', label: 'catalog-shortlists'" in block`) still match the awaited form.
  - CAT4 Task 12, open branch: CAT2's `catalogEdition(a)` returns `CATALOG_DEFAULT_EDITION` when `threat_catalog` is absent. With `CATALOG_DEFAULT_EDITION = 'open'`, the harness `ARGS` (no `threat_catalog`) therefore dispatch `catalog-scope` (first in `threat-model-author`, before `author-threat-model-floor`) and `catalog-shortlists` (right after `canonicalize-threat-model`, as CAT3 Task 5 pins). Add both to `EXPECTED_GREEN_LABELS` in the same commit, or set `threat_catalog: 'off'` in the harness `ARGS`; either way `tests/test_workflow_runner_awaits.py` joins the open branch's Files. The off branch changes no workflow text.
- **A15.28 Workflow anchors after #50** (amends the workflow rows of "A7 anchors after WS1", A9.1, A9.15, A10.13 and A12.4). Locate by the anchor; the line numbers are hints:

  | Register citation | Anchor | Now |
  |---|---|---|
  | A9.15 header ≈ 32–39 | the SKIP CONVENTION paragraph of the header comment | 45–52 |
  | A10.13 `pyStep` ≈ 228, `llmStep` ≈ 301 | `function pyStep(`, `function llmStep(` | 241, 314 |
  | A9.1, A12.4 `isErr` ≈ 327 | `function isErr(` | 340 |
  | A9.1 `bailIfInterrupted` ≈ 337–346 | `function bailIfInterrupted(` | 351–359 |
  | A7 anchors, CAT2 T9: `const runDir` `:164` | `const runDir` | 177 |
  | A12.4 `phase('intake')` ≈ 437–444 | `phase('intake')` and the intake `llmStep` | 450–457 |
  | A10.13 code-recon phase ≈ 475–502 | `phase('code-recon')` | 488–515 |
  | A7 anchors, CAT2 T9: `:515`, `:516-520`; A10.13 TM author ≈ 515–526 | `phase('threat-model-author')`; `await pyStep('author-threat-model'`; `await llmStep('apd-threat-model-author'` | 528; 529–533; 534–539 |
  | A7 anchors, CAT3 T5; A10.13: `canonicalize-threat-model` ≈ 552–557 | `label: 'canonicalize-threat-model'` | 565–570 |
  | A9.1 `tierGate` ≈ 634–641 | `async function tierGate(` | 647–654 |
  | A7 anchors, CAT3 T5; A10.13: `runTier` ≈ 700 | `async function runTier(` | 713 |
  | A9.1 retry loop ≈ 715–724; A10.13 ≈ 717 | `for (let i = 0; i < lenses.length; i++)` | 729–739 |
  | A12.4 prephase-5 gate ≈ 758–770 | `label: 'validate-full-prephase5'` and its `isErr` throw | 773–785 |
  | A12.4 cluster candidates and adjudicate ≈ 779–795 | `phase('synthesis-cluster')` to `label: 'adjudicate'` | 793–810 |
  | A7 anchors, CAT3 T8: `phase('tmeval')` `:870` | `phase('tmeval')` | 885 |
  | A10.13, A12.4 tmeval thunk ≈ 873–891 | first thunk of `await parallel([` | 888–906 |
  | A10.13, A12.4 apath thunk ≈ 892–903 | second thunk | 907–918 |
  | A10.13 attempt-0 writer ≈ 963–968; writer and audit loop ≈ 963–1055 | `label: 'report-writer-attempt-0'`; through the audit loop | 978–983; 978–1072 |
  | A12.4 `build-report` calls ≈ 971, 979, 986, 1055 | `pyStep('build-report'` | 986, 994, 1001, 1070 |
  | A9.1, A12.4 audit loop ≈ 1000–1057 | `for (let i = 0; i <= 2; i++)` | 1015–1072 |
  | A10.13 remediation ≈ 1049–1054 | `'report-writer-attempt-' + (i + 1)` | 1064–1069 |
  | A9.15 domain-capture block ≈ 1065–1100 | `PHASE 5h` | 1080–1115 |
  | A9.1 `summarize` ≈ 1106–1107 | `await pyStep('summarize'` | 1121–1122 |

**Consolidated plan**

- **A15.29 Consolidated plan: 1.7.1 baselines (Phase 2 applies these in Task 2.1).**
  - DEC-19 Default: "`<prev>` with `--strict`; 1.7.0 only at milestone exits" → "`<prev>` with `--strict`; the 1.7.1 baseline (Task 0.4) only at milestone exits".
  - DEC-24 Default: "two runs per held-out entry; 1.7.0 baseline" → "two runs per held-out entry; 1.7.1 baseline".
  - Part E: Phase 0 Contents "telemetry, 1.7.0 baseline" → "telemetry, 1.7.1 baseline"; Phase 7 Exit gate "Held-out IaC recall ≥ 1.7 baseline" → "Held-out IaC recall ≥ 1.7.1 baseline"; Phase 9 Exit gate "CF4 evaluation against the 1.7 CBM-only baseline" → "CF4 evaluation against the 1.7.1 CBM-only baseline".
  - Task 1.9 Step 3: "Any retroactive `compare-runs` failure of 1.7.1 against 1.7.0 (run once WS2 lands, from `next`, on the run directories kept in Tasks 0.4 and 1.5)." → "Any 1.7.1 defect that the Task 0.4 baseline runs or Task 3.2 Step 2 reveal; no 1.7.0 live run exists to compare against (A15.1)."
  - Task 3.2 Step 2: "Run `compare-runs` retroactively for 1.7.1 on claim-event-bus: `apd-gauntlet compare-runs runs/<id>-baseline runs/<id>-ws1-gate --gates eval/gates.yaml` (a single 1.7.1 run, so expect the single-run warning). A failure becomes a 1.7.2 fix (Task 1.9 Step 3)." → "Compare the Task 1.5 run with the Task 0.4 claim-event-bus baseline, both 1.7.1: `apd-gauntlet compare-runs runs/<id>-baseline runs/apd-20261016-ws1-gate --gates eval/gates.yaml` (a single run without code recon, so expect the single-run warning). Record the result as WS2 data; a 1.7.1 defect becomes a 1.7.2 fix (Task 1.9 Step 3)."
  - Task 7.4 Exit: "cost per run recorded against the 1.7.0 baseline" → "cost per run recorded against the 1.7.1 baseline".
  - Phase 8 Step 1: "`compare-runs` against the 1.7.0 baseline (milestone exit, no `--strict`)" → "`compare-runs` against the 1.7.1 baseline (milestone exit, no `--strict`)".
  - Phase 9 Steps 3 and 4: "the 1.7 CBM-only baseline" → "the 1.7.1 CBM-only baseline" (both places).
- **A15.30 Consolidated plan: Part G and other sites (Phase 2 applies these in Task 2.1, before Task 2.2 copies Part G).**
  - Part G N7 Files: "one `decideStep('diagram-check', 'intake', 'decide-diagram-check')` right after `assemble-inventory`" → "one `await decideStep('diagram-check', 'intake', 'decide-diagram-check');` right after `assemble-inventory` (A15.26)".
  - Part G N11 Files: "workflow `llmStep`," → "the workflow (a named async helper that awaits `llmStep` and records the result, listed in `ASYNC_HELPERS` and `CALLS`; `llmStep` stays synchronous, A15.21),".
  - SEP step 3: "(committed with the PR, so the next plan's executor can read them)" → "(added with `git add -f`, because new files under `docs/superpowers/` are git-ignored, and committed with the PR, so the next plan's executor can read them)".
  - Phase 9 Step 3: "Write CF1–CF4 with superpowers:writing-plans." → "Write CF1–CF4 with superpowers:writing-plans, and add each new plan file with `git add -f`."
  - Part G N22: "then a plan with superpowers:writing-plans." → "then a plan with superpowers:writing-plans; add both new files with `git add -f` (A15.11)."
  - "Spec and inputs": "(A1–A3 made concrete, A7–A14)" → "(A1–A3 made concrete, A7–A15)"; "Implementation branch: `fix/ws1-1.7.1` (WS1, unmerged)." → "Implementation branch: none open; WS1 merged in #49 and shipped in v1.7.1 (A15.4)." Part K, the "Improvements on `next`" row: "register A1–A3, A7–A14" → "register A1–A3, A7–A15".
  - Task 2.1 Step 2: "A14 (cross-cutting)." → "A14 (cross-cutting), A15 (state after 1.7.1)."
- **A15.31 (record) Consolidated plan update of 2026-10-17.** Already made in the consolidated plan, so Phase 2 skips it: the title's update date; Part A (branches and pull requests); Part B rows 1–6, 22, 24 and 25, and new rows 29–30 for the A15.1 and A15.3 defects; Part C (the A15 facts, and the version bullet: `next` carries 1.7.1 since #52); Part D (DEC-1 and DEC-34 outcomes, DEC-35 proposed); Global Constraints "Comparisons"; SCP Step 1; Task 0.2 Step 1's note and Step 4's outcome (A14.7 applied in #48; DEC-34, no rewrite); Task 0.4 on 1.7.1; the Phase 0 and Phase 1 ticks with their outcomes; Task 2.2 Step 3 (`git add -f`); the J.1 and J.2 cost rows.

## Sources (fetched 2026-10-14 unless dated)

- Clef: <https://developers.cloudflare.com/workers-ai/models/clef/>, <https://developers.cloudflare.com/workers-ai/models/clef-flash/>, <https://developers.cloudflare.com/workers-ai/models/clef-omni/>, <https://blog.cloudflare.com/clef-faster-cheaper-multimodal/> (2026-10-09), <https://blog.cloudflare.com/clef-decision-models/> (2026-10-01), <https://huggingface.co/collections/Cloudflare/clef>, <https://developers.cloudflare.com/workers-ai/platform/data-usage/>, <https://developers.cloudflare.com/ai-gateway/>.
- Jev: <https://docs.typesafe.ai/api>, <https://typesafe.ai>, <https://openrouter.ai/models/typesafe/jev-1.13>.
- Claude Code: <https://code.claude.com/docs/en/monitoring-usage>, <https://code.claude.com/docs/en/sub-agents>, <https://code.claude.com/docs/en/model-config>, <https://code.claude.com/docs/en/workflows>.
- Python packages: <https://pypi.org/project/claude-agent-sdk/>, <https://pypi.org/project/textual/>, <https://pypi.org/project/starlette/>, <https://pypi.org/project/apd-gauntlet/> (1.7.0 only, uploaded 2026-06-25).
- IaC tools: <https://github.com/advisories/GHSA-q7j3-v8qv-22vq>, <https://github.com/opentofu/opentofu/releases/tag/v1.13.1>, <https://github.com/aquasecurity/trivy/releases/tag/v0.75.0>, <https://github.com/advisories/GHSA-q3fv-x8vg-qqm4>, <https://github.com/advisories/GHSA-mcj4-mphf-j9ff>, <https://github.com/advisories/GHSA-69fq-xp46-6x23> (malicious Trivy v0.69.4), <https://github.com/cloudposse/atmos/releases/tag/v1.232.0>, <https://atmos.tools/cli/configuration/edition>, <https://pypi.org/project/checkov/>, <https://github.com/koalaman/shellcheck/releases>.
- Code-flow engines: <https://github.com/joernio/joern/releases>, <https://github.com/opengrep/opengrep/releases>.
- codebase-memory-mcp: <https://github.com/DeusData/codebase-memory-mcp/releases/tag/v0.10.0>, <https://github.com/DeusData/codebase-memory-mcp/releases/tag/v0.10.8>, <https://github.com/DeusData/codebase-memory-mcp/releases/tag/v0.11.0>.
- Catalog licences: <https://attack.mitre.org/resources/legal-and-branding/terms-of-use/>, <https://capec.mitre.org/about/termsofuse.html>, <https://cwe.mitre.org/about/termsofuse.html>, <https://d3fend.mitre.org/about/>, <https://raw.githubusercontent.com/OWASP/Top10/master/LICENSE>, <https://owasp.org/Top10/2025/>, <https://genai.owasp.org/llm-top-10/>.
