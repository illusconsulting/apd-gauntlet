# WS1 — Audit Defect Fixes and the 1.7.1 Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the cost-and-token audit's seven defects plus the Python verbatim-excerpt check on `main`, and release them as 1.7.1 without changing models or adding features.

**Architecture:** A new read-only `resume-plan` command decides which agent steps a resumed run can skip, so the workflow strips the guard text from every agent prompt. Tier gates stop being advisory: a failure dispatches one repair agent per failing file, then re-runs the lens, then halts. The read-only gates also stop skipping themselves. Prompt fixes remove stale paths and contradictory steps, `canonicalize` becomes the only minter of `cev-` and `tm-` ids, the domain-skill cache keys on pack content, and `validate` warns when an excerpt is not in the input it cites.

**Tech Stack:** Python 3.10–3.12 (`tools/apd_gauntlet`: click, PyYAML, jsonschema Draft 2020-12), the Claude Code workflow script `.claude/workflows/apd-gauntlet.js` (pinned by static text tests), Markdown agent prompts under `.claude/agents/`, pytest, ruff, mypy (strict), markdownlint-cli2.

**Spec:**

- Program master plan `docs/superpowers/plans/2026-10-10-program-master-plan.md`: Global Constraints, Review Focus (first item), Registry §R1 (`resume-plan`), §R3, §A2 (repair template), Task 2.
- Cost and token audit: "Defects that cost tokens and threaten accuracy" (seven rows), "Where it doesn't go" (verbatim-excerpt check), "Rollout" step 1, "Protecting accuracy".
- `RELEASING.md` from PR #27 (`origin/chore/two-line-releases`): "Version lockstep", "The release gate", "Cutting a stable 1.7.x release (from `main`)".

**Executed and released as v1.7.1** (#49–#52; register A8, A15).

**Amended 2026-10-17** per the amendments register (A8.1, A8.2, A8.3, A8.4, A8.5, A8.7, A8.8, A15.2, A15.5, A15.6, A15.7, A15.8).

## Global Constraints

- Every task lands on `main`, on branches cut from `main` after PR #27 merges (so `FRAMEWORK_VERSION`, `release_of()` and `tools/check_release_tag.py` exist). The release is `1.7.1`, tag `v1.7.1`.
- No model or `effort` change: every agent's frontmatter `model` stays as shipped. WS3 adds `effort`; WS5 Wave 3 moves models.
- No feature beyond the fixes in the tasks below. No phase is added or renamed: `meta.phases` is unchanged (R3).
- R1, verbatim: `resume-plan <run-dir> --json` prints `{"engine_version": str, "steps": [{"label": str, "complete": bool, "reason": str}]}`. Exits 0 and writes nothing. The workflow and runner skip steps marked complete; LLM prompts carry no guard text.
- Ids are minted by Python only (ADR-0020); agents emit content.
- The repair prompt template lives at `tools/apd_gauntlet/data/prompts/repair.md`; LA2 reuses it (§A2).
- The verbatim-excerpt check covers only citations of files under the run's `inputs/` directory, and runs at tier gates and in the whole-run pass. On 1.7.1 it is a WARNING by default; `--strict-excerpts` makes it an ERROR at both. WS3 flips the default, so 1.7.1 and 2.0 apply the same rules.
- CI never touches the network (ADR-0017). Real runs are never committed.
- Quality gates on every PR: `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest`, `markdownlint-cli2` on the linted globs.
- Comparison gates (`eval/gates.yaml`, proposals): no critical or high finding lost unless the loss traces to evidence; severity agrees on at least 90% of matched findings; blocked rate moves by no more than 5 points; first-pass schema validity and retry count no worse than baseline; report audit passes in no more iterations than baseline.
- `compare-runs` ships with WS2 on `next`. It reads run directories only, so it runs from a `next` checkout against `main`-produced run directories. It runs once per behaviour-changing PR group (A, B, C and E), at the end of that group's last task.
- Version lockstep (RELEASING.md): `pyproject.toml`, `tools/apd_gauntlet/__init__.py`, `.claude-plugin/plugin.json`, the `apd-gauntlet` entry in `.claude-plugin/marketplace.json`, the literal in `test_plugin_manifest_version_matches_pyproject`, and a `## v1.7.1 — YYYY-MM-DD` CHANGELOG section.

## Review Focus

1. **A 2.0 run directory resumed by 1.7.1.** `resume-plan` exits 3 naming both versions and writes nothing; the workflow throws before any dispatch. Pinned in Task 1 (`test_refuses_run_from_another_major`) and Task 2 (`test_resume_plan_refusal_halts_and_failure_falls_back`).
2. **A run interrupted mid-lens** (the findings file is valid, its capabilities sibling is missing or truncated). That lens is not complete and re-runs. Pinned in Task 1 (`test_truncated_sibling_is_not_complete`, `test_missing_sibling_is_not_complete`).
3. **A 1.7.0 run directory canonicalized by 1.7.1.** Its hand-assigned `cev-`/`tm-` ids do not match the hash, and findings and `c4-recon.yaml` cite them. Every `00-context` file stays byte-identical. Pinned in Task 9 (`test_existing_context_ids_are_never_rewritten`).
4. **Faithful excerpts that are not character-identical:** quoted from Markdown with inline code or emphasis, shortened with an ellipsis, or written as absence markers such as `(absent in supplied TM)`. None raises a false warning, while out-of-order ellipsis fragments still do. Pinned in Task 11 (`test_markdown_inline_markup_is_ignored`, `test_ellipsis_fragments_must_appear_in_order`, `test_absence_marker_is_not_checked`).
5. **The 1.7.1 plugin driving an older 1.7.0 engine** that has no `resume-plan` command. The workflow logs and runs every agent step instead of halting. Pinned in Task 2 (`test_resume_plan_refusal_halts_and_failure_falls_back`). Record (register A8.5): on 1.7.1 the workflow halts with an upgrade message when the engine has no `resume-plan` command (`.claude/workflows/apd-gauntlet.js`, the `resume-plan` refusal branch; pinned by `tests/test_workflow_apd_gauntlet.py::test_resume_plan_refusal_halts_and_failure_falls_back`); the plan described a fallback.

---

## File Structure

| Path | Responsibility | Action | Task |
|---|---|---|---|
| `tools/apd_gauntlet/resume_plan.py` | Resumable-step table, per-step completion, engine-major check | Create | 1 |
| `tools/apd_gauntlet/validate.py` | `schema_errors_for_file`; context-id presence check; verbatim-excerpt check | Modify | 1, 9, 11 |
| `tools/apd_gauntlet/cli.py` | `resume-plan` command; canonicalize summary; `validate --strict-excerpts` | Modify | 1, 9, 11 |
| `tools/apd_gauntlet/data/schemas/agent-receipt.schema.json` | Optional `resume_plan` block | Modify | 1 |
| `.claude/workflows/apd-gauntlet.js` | Resume from `resume-plan`; guard-free LLM prompts; tier-gate repair; read-only gates always run; tmeval paths; context-id canonicalize steps | Modify | 2, 3, 4, 5, 10 |
| `tools/apd_gauntlet/plan_run.py` | Mirror the new CLI rows and the tier-gate repair note | Modify | 2, 3, 10 |
| `tools/apd_gauntlet/data/prompts/repair.md` | Repair-agent prompt template (shared with LA2) | Create | 3 |
| `tools/apd_gauntlet/resources.py`, `pyproject.toml` | `read_prompt()`; ship `data/prompts/*.md` | Modify | 3 |
| `.claude/agents/apd-threat-model-evaluator.md`, `docs/threat-modeling.md` | Canonical input and output paths | Modify | 5 |
| `.claude/agents/apd-attack-path-analyzer.md` | Drop the obsolete Step 5 hedge and Step 6 manual checks | Modify | 6 |
| `.claude/agents/apd-confidentiality.md` | Drop self-check item 10 | Modify | 7 |
| `tools/apd_gauntlet/build_domain_skill.py` | Pack content hash in the skill signature | Modify | 8 |
| `tools/apd_gauntlet/linters.py`, `tools/apd_gauntlet/threat_model/author.py` | `compute_cev_id`, `compute_tm_entry_id` | Modify | 9 |
| `tools/apd_gauntlet/canonicalize.py` | Mint missing `cev-`/`tm-` ids and goals | Modify | 9 |
| `tools/apd_gauntlet/data/schemas/{code-evidence-index,threat-model-normalized}.schema.json` | Ids optional at emission | Modify | 9 |
| `docs/adrs/0020-tooling-authored-derived-fields.md` | Amendment: `cev-`/`tm-` minted when absent | Modify | 9 |
| `.claude/agents/apd-{code-recon,threat-model-author,threat-model-recon}.md`, `.claude/skills/apd-threat-model-methodologies/SKILL.md`, `templates/{code-architecture-brief,threat-model-authored}.template.md` | Agents emit content only | Modify | 10 |
| `docs/{running-the-gauntlet,architecture,adapting-to-other-domains,deterministic-field-register,schema-evolution,QUICKSTART}.md`, `CHANGELOG.md` | Docs for each behaviour change; release notes | Modify | 1–12 |
| Version files (Global Constraints, last line) | 1.7.1 lockstep | Modify | 12 |
| `tests/test_cli_resume_plan.py`, `tests/test_canonicalize_context_ids.py`, `tests/test_validate_excerpts.py` | New suites | Create | 1, 9, 11 |
| `tests/test_workflow_apd_gauntlet.py`, `tests/test_cli_plan_run.py`, `tests/test_resources.py`, `tests/test_tmeval_agent_contract.py`, `tests/test_lint_agent_*.py`, `tests/test_agent_prompt_id_contract.py`, `tests/test_build_domain_skill.py`, `tests/test_validate_cross_file.py`, `tests/test_threat_model_authored_template.py`, `tests/test_skill_apd_threat_model_methodologies_authoring.py`, `tests/integration/test_wheel_install_smoke.py` | Extended pins | Modify | 2–10 |

## Task groups (one PR each, merged in this order)

| PR | Tasks | Edits the workflow | compare-runs after |
|---|---|---|---|
| A — resume | 1, 2 | yes | Task 2 |
| B — gates | 3, 4 | yes | Task 4 |
| C — prompt fixes | 5, 6, 7 | yes (Task 5) | Task 7 |
| D — domain skill cache | 8 | no | — |
| E — Python-minted context ids | 9, 10 | yes (Task 10) | Task 10 |
| F — verbatim excerpts | 11 | no | — |
| G — release 1.7.1 | 12 | no | — |

Amended (register A8.3): WS1 was executed as one branch (`fix/ws1-1.7.1`, 19 commits), not PR groups A–G. Open one PR to `main` and merge with a merge commit. Done: #49 (register A15.5).

Each CHANGELOG bullet in Tasks 2–11 goes under `## [Unreleased]` → `### Fixed`. The first task to land creates that subsection after `### Changed`.

Test snippets show only the new code. Add any import a module lacks (`re`, `shutil`, `json`, `hashlib`, `pytest`, `yaml`, `Draft202012Validator`, the `apd_gauntlet` names under test) in the same step.

---

### Task 1: `resume-plan` command

**Files:**

- Create: `tools/apd_gauntlet/resume_plan.py`
- Modify: `tools/apd_gauntlet/validate.py` (add `schema_errors_for_file` after `run_schema_pass`, `:426-455`)
- Modify: `tools/apd_gauntlet/cli.py` (register after `plan-run`, `:366-397`)
- Modify: `tools/apd_gauntlet/data/schemas/agent-receipt.schema.json` (add the `resume_plan` property)
- Modify: `docs/running-the-gauntlet.md:41-60` (CLI list)
- Test: `tests/test_cli_resume_plan.py`

**Interfaces:**

- Consumes: `FRAMEWORK_VERSION`, `__version__` (`apd_gauntlet/__init__.py`, PR #27); `plan_run._TIERS`; `validate.RECORD_KINDS`, `CONTEXT_ROLLUPS`, `SYNTHESIS_ROLLUPS`, `CODE_EVIDENCE_INDEX_FILENAME`, `extract_records`, `build_registry`, `parse_intake_brief`.
- Produces:
  - `@dataclass(frozen=True) class ResumeStep: label: str; alternatives: tuple[tuple[str, ...], ...]` (run-relative output sets; the step is complete when every file of any one set is present and valid)
  - `RESUMABLE_STEPS: tuple[ResumeStep, ...]` (workflow order, table below)
  - `class EngineMismatch(Exception)`
  - `def check_engine_compat(run_dir: Path) -> None` (raises `EngineMismatch`)
  - `def step_status(run_dir: Path, step: ResumeStep) -> tuple[bool, str]`
  - `def build_resume_plan(run_dir: Path) -> dict[str, Any]` (the R1 shape)
  - `validate.schema_errors_for_file(run_dir: pathlib.Path, rel: str) -> list[str]` (YAML parse plus the schema the validator would apply to that path; `[]` when no schema applies)
  - CLI `apd-gauntlet resume-plan RUN_DIR [--json]`: exit 0 on success; exit 2 when `RUN_DIR/.apd-run.yaml` is missing or unparseable; exit 3 when the run's `framework_version` major differs from `FRAMEWORK_VERSION`'s major. Nothing is printed on stdout on exit 2 or 3.
  - `agent-receipt.schema.json` gains an optional `resume_plan`: `{type: object, additionalProperties: false, required: [engine_version, steps], properties: {engine_version: string, steps: array of {label: string, complete: boolean, reason: string} with additionalProperties false and all three required}}`

`RESUMABLE_STEPS` (labels are the workflow's first-attempt `llmStep` labels; retries, re-runs and report remediations are deliberately absent so they always run):

| label | alternatives |
|---|---|
| `intake` | (`00-context/context-brief.md`, `00-context/asset-inventory.yaml`) |
| `code-recon` | (`00-context/code-evidence-index.yaml`, `00-context/code-architecture-brief.md`, `00-context/c4-recon.yaml`) or (`00-context/code-recon-skipped.md`) |
| `threat-model-author` | (`00-context/threat-model-normalized.yaml`, `00-context/threat-model-authored.md`) |
| `tm-recon` | (`00-context/threat-model-supplied-normalized.yaml`) |
| each lens in `plan_run._TIERS` (label = lens, e.g. `non-repudiation`) | (`<tier>/<lens>.findings.yaml`, `<tier>/<lens>.capabilities.yaml`) |
| `adjudicate` | (`40-synthesis/cluster-decisions.yaml`) |
| `tmeval` | (`40-synthesis/threat-model-coverage.yaml`, `40-synthesis/threat-model-coverage-report.md`) |
| `apath` | (`40-synthesis/attack-path.findings.yaml`, `40-synthesis/attack-path-report.md`) |
| `report-writer-attempt-0` | (`40-synthesis/report-data.yaml`, `40-synthesis/advisory-report.md`) |
| `domain-auditor` | (`40-synthesis/domain-improvements.yaml`) |

- [x] **Step 1: Write the failing tests**

```python
FIX = Path(__file__).resolve().parent / "fixtures"

def _run(tmp_path, framework_version="1.7.1", *, clean=False) -> Path:
    run = tmp_path / "run"
    if clean:
        shutil.copytree(FIX / "runs" / "clean-run", run)
    else:
        run.mkdir()
    (run / ".apd-run.yaml").write_text(yaml.safe_dump(
        {"run_id": "run", "domains": ["pbm"], "framework_version": framework_version}))
    return run

def _plan(run):
    r = CliRunner().invoke(main, ["resume-plan", str(run), "--json"])
    assert r.exit_code == 0, r.output
    return json.loads(r.stdout)

def _step(plan, label):
    return next(s for s in plan["steps"] if s["label"] == label)

def test_fresh_run_lists_every_step_incomplete(tmp_path):
    plan = _plan(_run(tmp_path))
    assert plan["engine_version"] == __version__
    assert [s["label"] for s in plan["steps"]] == [s.label for s in RESUMABLE_STEPS]
    assert not any(s["complete"] for s in plan["steps"])
    assert _step(plan, "intake")["reason"] == "missing 00-context/context-brief.md"

def test_output_matches_receipt_schema(tmp_path):
    schema = json.loads((FIX.parent.parent / "schemas/agent-receipt.schema.json").read_text())
    Draft202012Validator(schema["properties"]["resume_plan"]).validate(_plan(_run(tmp_path, clean=True)))

def test_finished_lens_is_complete(tmp_path):
    assert _step(_plan(_run(tmp_path, clean=True)), "confidentiality") == {
        "label": "confidentiality", "complete": True, "reason": "outputs present and valid"}

def test_truncated_sibling_is_not_complete(tmp_path):  # Review Focus 2
    run = _run(tmp_path, clean=True)
    (run / "10-trustworthiness/confidentiality.capabilities.yaml").write_text('capability:\n  - title: "unterminated\n')
    s = _step(_plan(run), "confidentiality")
    assert not s["complete"]
    assert s["reason"].startswith("unparseable 10-trustworthiness/confidentiality.capabilities.yaml")

def test_missing_sibling_is_not_complete(tmp_path):  # Review Focus 2
    run = _run(tmp_path, clean=True)
    (run / "10-trustworthiness/confidentiality.capabilities.yaml").unlink()
    assert _step(_plan(run), "confidentiality")["reason"] == "missing 10-trustworthiness/confidentiality.capabilities.yaml"

def test_schema_invalid_output_is_not_complete(tmp_path):
    run = _run(tmp_path, clean=True)
    (run / "10-trustworthiness/confidentiality.findings.yaml").write_text("finding:\n  - agent: confidentiality\n")
    assert _step(_plan(run), "confidentiality")["reason"].startswith(
        "schema-invalid 10-trustworthiness/confidentiality.findings.yaml")

def test_empty_markdown_is_not_complete(tmp_path):
    run = _run(tmp_path, clean=True)
    shutil.copy(FIX / "valid/asset-inventory-valid.yaml", run / "00-context/asset-inventory.yaml")
    assert _step(_plan(run), "intake")["complete"] is True
    (run / "00-context/context-brief.md").write_text("")
    assert _step(_plan(run), "intake")["reason"] == "empty 00-context/context-brief.md"

def test_code_recon_skip_note_counts_as_complete(tmp_path):
    run = _run(tmp_path)
    (run / "00-context").mkdir()
    (run / "00-context/code-recon-skipped.md").write_text("CBM not reachable; recon cannot complete\n")
    assert _step(_plan(run), "code-recon")["complete"] is True

def _snapshot(run):
    return {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in run.rglob("*") if p.is_file()}

def test_writes_nothing(tmp_path):
    run = _run(tmp_path, clean=True)
    before = _snapshot(run)
    _plan(run)
    assert _snapshot(run) == before

def test_refuses_run_from_another_major(tmp_path):  # Review Focus 1
    r = CliRunner().invoke(main, ["resume-plan", str(_run(tmp_path, "2.0.0")), "--json"])
    assert r.exit_code == 3 and r.stdout == ""
    assert "2.0.0" in r.stderr and __version__ in r.stderr and "apd-gauntlet 2.x engine" in r.stderr

def test_accepts_older_run_on_same_major(tmp_path):
    assert _plan(_run(tmp_path, "1.6.0"))["engine_version"] == __version__

def test_missing_run_config_exits_2(tmp_path):
    r = CliRunner().invoke(main, ["resume-plan", str(tmp_path), "--json"])
    assert r.exit_code == 2 and "No .apd-run.yaml" in r.stderr

def test_text_mode_lists_labels(tmp_path):
    r = CliRunner().invoke(main, ["resume-plan", str(_run(tmp_path))])
    assert r.exit_code == 0 and "intake" in r.stdout and "domain-auditor" in r.stdout
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_cli_resume_plan.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.resume_plan`)

- [x] **Step 3: Implement `resume_plan.py`, `schema_errors_for_file`, the command and the receipt property**

Per-file status, checked in order: absent gives `missing <rel>`; whitespace-only content gives `empty <rel>`; `context-brief.md` with no parseable frontmatter (`parse_intake_brief` returns `{}`) gives `no frontmatter in <rel>`; for `.yaml`, a `YAML parse error` from `schema_errors_for_file` gives `unparseable <rel>: <error>`, and any other first error gives `schema-invalid <rel>: <error>`. A step's reason is `outputs present and valid` when complete, otherwise the first failing file's reason in its first alternative. `schema_errors_for_file` picks the schema the way `run_schema_pass` does: `*.findings.yaml` / `*.capabilities.yaml` validate each `extract_records` record, `00-context/<name>` uses `CONTEXT_ROLLUPS` or `code-evidence-index.schema.json`, `40-synthesis/<name>` uses `SYNTHESIS_ROLLUPS`. The envelope check is skipped, because canonicalize normalizes envelopes. `EngineMismatch` text: `resume-plan: refusing to resume {run_dir}: it was created by framework {fv} and this engine is {__version__} (framework {FRAMEWORK_VERSION}). Resume it with an apd-gauntlet {run_major}.x engine.` JSON goes to stdout as `json.dumps(plan)` on one line. Text mode prints `engine <version>` and then one `complete|pending  <label>  <reason>` line per step. Add `apd-gauntlet resume-plan <run-dir> [--json]  # which agent steps are already complete (read-only; the runner resumes from it)` to the docs CLI list.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_cli_resume_plan.py tests/test_agent_receipt_schema.py -v && mypy tools/`
Expected: PASS; mypy clean

- [x] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/resume_plan.py tools/apd_gauntlet/validate.py tools/apd_gauntlet/cli.py tools/apd_gauntlet/data/schemas/agent-receipt.schema.json docs/running-the-gauntlet.md tests/test_cli_resume_plan.py
git commit -m "feat(cli): add read-only resume-plan step-completion map"
```

### Task 2: The workflow resumes from `resume-plan`; agent prompts lose the guard

2026-10-17 (register A15.2): the JS this task quotes is history; the shipped code is the awaited form.

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js`: header comment `:16-31`; `RECEIPT` `:50-104`; `pyStep` `:175-216` (new `opts.resumePlan`); `llmStep` `:221-239`; `bailIfInterrupted` message `:254-259`; setup `:265-308`; every `llmStep(...)` call site (`:314-321`, `:353-358`, `:390-398`, `:409-417`, `:433-438`, `:446-451`, `:525-529`, `:541-545`, `:616-623`, `:627-633`, `:698-703`, `:711-714`, `:785-791`, `:820-829`)
- Modify: `tools/apd_gauntlet/plan_run.py:47-56` (first setup row)
- Modify: `docs/running-the-gauntlet.md:380-390`, `docs/architecture.md:49`, `CHANGELOG.md`
- Test: `tests/test_workflow_apd_gauntlet.py`, `tests/test_cli_plan_run.py`

**Interfaces:**

- Consumes: Task 1's CLI contract and `RESUMABLE_STEPS`.
- Produces:
  - JS `let RESUME_DONE = {}` (label to reason), declared next to `runDir`.
  - `pyStep` option `resumePlan: true`, which tells the worker to copy the command's stdout JSON verbatim into the receipt as `resume_plan`.
  - `llmStep(agentType, instruction, opts)`: `opts` carries only `phase` and `label`. When the label is in `RESUME_DONE`, it logs and returns `{agent: agentType, status: 'ok', outputs: [{path: label + '.skipped', schema_valid: true}], counts: {}}` without dispatching.
  - `RECEIPT.properties.resume_plan`, mirroring the Task 1 schema property.
  - plan-run's first row: `{"phase": "setup", "kind": "CLI", "ref": "resume-plan runs/<id> --json", "outputs": "step completion map (read-only); skip AGENT steps marked complete", "gate": ""}`.

- [x] **Step 1: Write the failing tests**

```python
LENSES = {"confidentiality", "integrity", "availability", "distributed", "resilient",
          "ephemeral", "authenticity", "non-repudiation", "immutability"}

def _fn_body(text: str, name: str) -> str:
    return text.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]

def _llmstep_calls(text: str) -> list[str]:
    # The comma requirement skips the header comment's "llmStep('apd-threat-model-author')";
    # on today's file this yields the 14 real call sites.
    return re.findall(r"llmStep\('[^'\n]*'(?: \+ \w+)?,.*?\}\);", text, re.DOTALL)

def test_llmstep_prompt_has_no_guard() -> None:
    body = _fn_body(_text(), "llmStep")
    assert "guard(" not in body and "IDEMPOTENCY" not in body

def test_llmstep_skips_steps_resume_plan_marks_complete() -> None:
    body = _fn_body(_text(), "llmStep")
    assert "RESUME_DONE" in body and "'.skipped'" in body

def test_llmstep_calls_carry_no_guard_options() -> None:
    for call in _llmstep_calls(_text()):
        assert "validateScope" not in call and "validateFlags" not in call, call[:80]

def test_resume_plan_is_first_setup_step() -> None:
    t = _text()
    assert t.index("phase('setup')") < t.index("pyStep('resume-plan'") < t.index("label: 'validate-scaffold'")

def test_resume_plan_refusal_halts_and_failure_falls_back() -> None:  # Review Focus 1 and 5
    t = _text()
    block = t[t.index("pyStep('resume-plan'"):t.index("label: 'validate-scaffold'")]
    assert "/exit=3/" in block and "throw new Error(" in block and "refusing to resume" in block
    assert "resume-plan unavailable" in block

def test_receipt_carries_resume_plan() -> None:
    block = re.search(r"const RECEIPT\s*=.*?^\};", _text(), re.DOTALL | re.MULTILINE).group(0)
    for key in ("resume_plan", "engine_version", "steps", "complete", "reason"):
        assert key in block

def test_pystep_lifts_resume_plan_json_verbatim() -> None:
    body = _fn_body(_text(), "pyStep")
    assert "opts.resumePlan" in body and "VERBATIM" in body

def test_resumable_labels_match_workflow_llmstep_labels() -> None:
    from apd_gauntlet.resume_plan import RESUMABLE_STEPS
    quoted = {m for c in _llmstep_calls(_text()) for m in re.findall(r"label:\s*'([^']+)'", c)}
    first = {lb for lb in quoted if "retry" not in lb and "build-fix" not in lb and not lb.endswith("-")}
    assert {s.label for s in RESUMABLE_STEPS} == first | LENSES
```

In `tests/test_cli_plan_run.py`:

```python
def test_plan_run_starts_with_resume_plan(tmp_path):
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, FULL_CFG))]).output)
    assert plan[0]["ref"] == "resume-plan runs/apd-test-full --json" and plan[0]["phase"] == "setup"
```

Extend `test_plan_run_phase_names_consistent_with_workflow`, after its phase assertion:

```python
    workflow_cmds = set(re.findall(r"pyStep\('([a-z][a-z0-9-]+)'", js))
    plan_cmds = {s["ref"].split()[0] for s in plan if s["kind"] == "CLI"}
    assert plan_cmds <= workflow_cmds, f"plan-run CLI steps the runner never runs: {plan_cmds - workflow_cmds}"
    assert "resume-plan" in plan_cmds & workflow_cmds
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py -v`
Expected: FAIL on nine of the ten new or extended tests. `test_resumable_labels_match_workflow_llmstep_labels` already passes, because it pins Task 1's table against labels the workflow already uses. Every other test still passes.

- [x] **Step 3: Implement the workflow and plan-run changes**

The `resume-plan` step is the first call after `phase('setup')`:

```js
const rp = pyStep('resume-plan', { phase: 'setup', label: 'resume-plan', cliArgs: '--json',
  alwaysRun: true, resumePlan: true, outputs: 'none (read-only step-completion map)' });
bailIfInterrupted(rp, 'setup');
const rpErr = rp.status === 'error' && rp.errors && rp.errors[0] ? rp.errors[0].message : '';
if (/exit=3/.test(rpErr)) {
  throw new Error('apd-gauntlet: refusing to resume ' + runDir + ' — ' + rpErr);
}
if (rp.status === 'ok' && rp.resume_plan && Array.isArray(rp.resume_plan.steps)) {
  rp.resume_plan.steps.forEach(function (s) { if (s.complete) { RESUME_DONE[s.label] = s.reason; } });
  log('resume-plan: engine ' + rp.resume_plan.engine_version + '; ' +
      Object.keys(RESUME_DONE).length + ' agent step(s) already complete.');
} else {
  log('resume-plan unavailable (' + (rpErr || 'no resume_plan in receipt') +
      ') — running every agent step.');
}
```

`llmStep` builds its prompt from `instruction` plus the existing two receipt lines only. `guard()` stays, because pySteps still use it. Remove `outputs`, `validateScope` and `validateFlags` from every `llmStep` call site; the instructions already name each step's outputs. Rewrite the header's two-layer resume note: same-session resume still replays the harness cache, and cross-session resume now comes from one `resume-plan` call that skips agent steps whose outputs are present and valid, while CLI steps keep pyStep's guard. Make the `bailIfInterrupted` text read `(resume-plan skips completed agent steps)`. In both docs, replace "idempotency guards replay completed phases" with "the runner calls `apd-gauntlet resume-plan` once and skips every agent step whose outputs are already present and valid". CHANGELOG bullet: agents no longer receive a resume guard they cannot run; the runner decides skips from `apd-gauntlet resume-plan`, refuses run directories from another major engine, and report-writer remediation passes always run.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py tests/test_cli_resume_plan.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tools/apd_gauntlet/plan_run.py docs/running-the-gauntlet.md docs/architecture.md CHANGELOG.md tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py
git commit -m "fix(workflow): resume from resume-plan and drop guard text from agent prompts"
```

- [ ] **Step 6: Operator — compare PR group A against the 1.7.0 baseline**

Not run: replaced by A8.1's substitute gate; no 1.7.0 live run can exist (A15.1).

Run the master plan Task 1 set twice on this branch (telemetry on). From a `next` checkout with WS2 merged, run `apd-gauntlet compare-runs <baseline> <candidate> --gates eval/gates.yaml` for each pair. Also interrupt one run during tier-2 and re-invoke it in a fresh session; the log must show `resume-plan: … agent step(s) already complete` and tier-1 lenses must not be re-dispatched.
Expected: exit 0 for every pair. `compare-runs` exists only once WS2 lands on `next`; until then keep the candidate run directories and finish this step before Task 12. The same procedure closes groups B (Task 4), C (Task 7) and E (Task 10).

### Task 3: Tier gates repair, re-run, then halt

2026-10-17 (register A15.2): the JS this task quotes is history; the shipped code is the awaited form.

**Files:**

- Create: `tools/apd_gauntlet/data/prompts/repair.md`
- Modify: `tools/apd_gauntlet/resources.py` (add `read_prompt`), `pyproject.toml` (`[tool.setuptools.package-data]`: add `"data/prompts/*.md"`)
- Modify: `.claude/workflows/apd-gauntlet.js`: `pyStep` (new `opts.errorsFromJson`); new `REPAIR_TEMPLATE`, `repairPrompt`, `tierGate`, `repairTierGate`, defined before `runTier`; `runTier` gate `:465-474`
- Modify: `tools/apd_gauntlet/plan_run.py:111-116` (tier-gate `gate` text)
- Modify: `docs/running-the-gauntlet.md:530-532` (replace "Specialist hit two retries and was dropped" with "A tier gate failed"), `CHANGELOG.md`
- Test: `tests/test_resources.py`, `tests/test_workflow_apd_gauntlet.py`, `tests/test_cli_plan_run.py`, `tests/integration/test_wheel_install_smoke.py`

**Interfaces:**

- Consumes: Task 2's `llmStep`, `RECEIPT`, `bailIfInterrupted`; the CLI `validate --tier <dir> --json`, which prints `{"errors": [{"file", "id", "message", "path"}], …}`.
- Produces:
  - `resources.read_prompt(name: str) -> str`, reading `data/prompts/<name>.md` (LA2 reuses it for `repair`).
  - Template placeholders `{{RUN_DIR}}`, `{{FILE}}`, `{{ERRORS}}`. The template has no `'` and no `\`, so it embeds as single-quoted JS strings.
  - JS `REPAIR_TEMPLATE` (the template's lines joined by `'\n'`); `repairPrompt(file, errorLines) -> string`; `tierGate(phaseName, tierDir, suffix) -> receipt`; `repairTierGate(phaseName, tierDir, lenses, gate) -> void` (throws when the tier stays red).
  - `pyStep` option `errorsFromJson: true`: on a nonzero exit the worker maps each JSON error to `{path: <file>, message: "<id> <path>: <message>"}`, at most 50. When stdout is not JSON it falls back to the default `exit=<N>` entry.
  - Labels: `validate-<tier>`, `repair-<tier>-<file basename>`, `canonicalize-<tier>-after-repair`, `validate-<tier>-after-repair`, `<lens>-rerun`, `canonicalize-<tier>-after-rerun`, `validate-<tier>-after-rerun`.

Template text (exact copy; LA2 and the workflow both use it):

```text
You are the APD gauntlet repair worker for run {{RUN_DIR}}.
The tier gate rejected one record file: {{FILE}}
Validator errors for that file:
{{ERRORS}}

Fix ONLY what these errors require, editing ONLY {{FILE}}:
- YAML syntax and quoting: quote any scalar that contains a colon-space, an em-dash or a leading special character.
- Field placement and enum values named in the errors; taxonomy keys belong under control_mappings.
- An excerpt over 25 tokens: shorten it to a contiguous run of the same words; never paraphrase.
- An excerpt not found verbatim in its artifact: copy the exact words from the cited file under inputs/ (an ellipsis may join exact fragments, in order); never paraphrase.
- A title over 200 characters: shorten it without changing the claim.
Never add, drop or merge records. Never change severity, disposition, evidence artifacts or locators unless an error names that field.
Never invent evidence. Never add an id or schema_version field: apd-gauntlet canonicalize mints them.
If an error cannot be fixed without new analysis, leave that record unchanged and report it.
Return ONLY a receipt conforming to schemas/agent-receipt.schema.json:
  agent: "repair"
  status: "ok" when every listed error is fixed, else "error"
  outputs: [{path: "{{FILE}}", schema_valid: true or false}]
  counts: {}
  errors: one {path: "{{FILE}}", message: <the error line>} per error you could not fix
```

- [x] **Step 1: Write the failing tests**

```python
# tests/test_resources.py
def test_read_prompt_repair_is_js_safe_and_has_placeholders() -> None:
    text = resources.read_prompt("repair")
    for ph in ("{{RUN_DIR}}", "{{FILE}}", "{{ERRORS}}"):
        assert ph in text
    assert "'" not in text and "\\" not in text
```

```python
# tests/test_workflow_apd_gauntlet.py
def test_repair_template_embedded_verbatim() -> None:
    from apd_gauntlet.resources import read_prompt
    js = _text()
    assert [ln for ln in read_prompt("repair").splitlines() if ln and f"'{ln}'" not in js] == []

def test_tier_gate_always_runs_and_reports_json_errors() -> None:
    body = _fn_body(_text(), "tierGate")
    assert "pyStep('validate'" in body and "alwaysRun: true" in body
    assert "errorsFromJson: true" in body and "' --json'" in body

def test_run_tier_repairs_before_rerunning_lens() -> None:
    assert "repairTierGate(phaseName, tierDir, lenses, gate)" in _fn_body(_text(), "runTier")
    rep = _fn_body(_text(), "repairTierGate")
    assert rep.index("agent(repairPrompt(") < rep.index("'-after-repair'") < rep.index("'-rerun'")

def test_tier_gate_halts_when_repair_and_rerun_fail() -> None:
    rep = _fn_body(_text(), "repairTierGate")
    assert rep.count("throw new Error(") >= 2
    assert "after repair and lens re-run" in rep and "no attributable file" in rep

def test_pystep_maps_validate_json_errors() -> None:
    body = _fn_body(_text(), "pyStep")
    assert "opts.errorsFromJson" in body and "at most 50" in body
```

Change `test_canonicalize_precedes_tier_validate_gate` to compare `run_tier.index("pyStep('canonicalize'")` with `run_tier.index("tierGate(")`, because the gate's `pyStep('validate'` now lives in `tierGate`.

```python
# tests/test_cli_plan_run.py
def test_plan_run_tier_gates_name_the_repair_path(tmp_path):
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, FULL_CFG))]).output)
    gates = [s for s in plan if s["ref"].startswith("validate ") and "--tier" in s["ref"]]
    assert len(gates) == 3 and all("repair.md" in s["gate"] and "halt" in s["gate"] for s in gates)
```

```python
# tests/integration/test_wheel_install_smoke.py
def test_repair_prompt_ships_in_wheel(venv_bin: Path, tmp_path: Path) -> None:
    code = "from apd_gauntlet.resources import read_prompt; print(read_prompt('repair'))"
    r = _run([str(venv_bin / "python"), "-c", code], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "{{FILE}}" in r.stdout
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_resources.py tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py -v`
Expected: FAIL (`read_prompt` missing; `tierGate` and `repairTierGate` absent)

- [x] **Step 3: Implement the template, `read_prompt`, and the gate repair loop**

`runTier` keeps its lens dispatch, retries and canonicalize step, then calls `const gate = tierGate(phaseName, tierDir, ''); repairTierGate(phaseName, tierDir, lenses, gate);`. `tierGate` is the existing validate pyStep with `cliArgs: '--tier ' + tierDir + ' --json'`, `alwaysRun: true` (a gate that can skip itself is not a gate) and `errorsFromJson: true`. The repair loop:

```js
function repairTierGate(phaseName, tierDir, lenses, gate) {
  bailIfInterrupted(gate, phaseName);
  if (!isErr(gate)) { return; }
  const byFile = failingFiles(gate, tierDir);        // {path: [lines]} for record files under tierDir
  if (!Object.keys(byFile).length) {
    throw new Error('tier gate ' + tierDir + ' FAILED with no attributable file: ' + errorText(gate));
  }
  parallel(Object.keys(byFile).map(function (f) { return function () {
    return agent(repairPrompt(f, byFile[f]), { schema: RECEIPT, phase: phaseName,
      label: 'repair-' + tierDir + '-' + baseName(f) }); }; }));
  pyStep('canonicalize', { phase: 'canonicalize', label: 'canonicalize-' + tierDir + '-after-repair',
    alwaysRun: true, outputs: 'canonicalized repaired records under ' + runDir });
  gate = tierGate(phaseName, tierDir, '-after-repair');
  bailIfInterrupted(gate, phaseName);
  if (!isErr(gate)) { return; }
  const rerun = lensesOf(Object.keys(failingFiles(gate, tierDir)), lenses);   // unique, in tier order
  parallel(rerun.map(function (lens) { return function () {
    return llmStep('apd-' + lens, 'Re-run the ' + lens + ' lens from scratch and overwrite ' + tierDir + '/' +
      lens + '.findings.yaml and ' + tierDir + '/' + lens + '.capabilities.yaml; the previous output ' +
      'still failed validation after a repair attempt.', { phase: phaseName, label: lens + '-rerun' }); }; }));
  pyStep('canonicalize', { phase: 'canonicalize', label: 'canonicalize-' + tierDir + '-after-rerun',
    alwaysRun: true, outputs: 'canonicalized re-run records under ' + runDir });
  gate = tierGate(phaseName, tierDir, '-after-rerun');
  bailIfInterrupted(gate, phaseName);
  if (isErr(gate)) {
    throw new Error('tier gate ' + tierDir + ' FAILED after repair and lens re-run: ' + errorText(gate) +
      '. Fix the records under ' + runDir + '/' + tierDir + ', then re-invoke the runner (resume-plan skips completed steps).');
  }
}
```

`failingFiles` keeps the receipt errors whose `path` contains `/<tierDir>/` and ends in `.findings.yaml` or `.capabilities.yaml`, grouping their messages by path. `lensesOf` maps a path ending `/<lens>.findings.yaml` or `/<lens>.capabilities.yaml` to a lens in `lenses`. `errorText` joins the receipt's first five error messages with `'; '`. `repairPrompt` substitutes the placeholders with `split(...).join(...)`. The plan-run tier gate `gate` becomes `validate {run_dir} --tier {tier_dir} --errors-only; on failure repair each failing file (tools/apd_gauntlet/data/prompts/repair.md), re-run the lens if repair fails, then halt`. The docs section says a dispatch failure still retries the lens twice, and a schema or semantic failure at the tier gate now gets one repair per file, then one lens re-run, then a halt that names the files. CHANGELOG bullet: tier gates now block, with repair before re-run.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_resources.py tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py -v && pytest -m wheel tests/integration -v`
Expected: PASS (the wheel test skips only where `uv` is absent)

- [x] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/prompts/repair.md tools/apd_gauntlet/resources.py pyproject.toml .claude/workflows/apd-gauntlet.js tools/apd_gauntlet/plan_run.py docs/running-the-gauntlet.md CHANGELOG.md tests/test_resources.py tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py tests/integration/test_wheel_install_smoke.py
git commit -m "fix(workflow): make tier gates blocking with a repair agent before lens re-run"
```

### Task 4: Read-only gates always run

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js:341-346` (`intake-schema-gate`), `:491-496` (`validate-full-prephase5`), `:847-849` (`validate-final`)
- Modify: `CHANGELOG.md`
- Test: `tests/test_workflow_apd_gauntlet.py`

**Interfaces:**

- Consumes: `pyStep`'s `alwaysRun` option (`:187-189`), which replaces `guard()` with "always perform the WORK COMMAND".
- Produces: those three `pyStep('validate', …)` calls carry `alwaysRun: true` and no `validateScope`/`validateFlags`. Their `cliArgs`, the pre-Phase-5 `isErr` throw (`:497-503`) and every other gate behaviour stay as they are. The guard runs only `validate --schema-only`, so a run with only semantic or cross-file errors made these gates return a skip receipt; now they run the full command every time. The tier gates got the same treatment in Task 3 (`tierGate`).

- [x] **Step 1: Write the failing test**

```python
READ_ONLY_GATES = ("intake-schema-gate", "validate-full-prephase5", "validate-final")

def test_read_only_gates_always_run() -> None:
    t = _text()
    for label in READ_ONLY_GATES:
        at = t.index(f"label: '{label}'")
        block = t[t.rindex("pyStep('validate'", 0, at):t.index("});", at)]
        assert "alwaysRun: true" in block, label
        assert "validateScope" not in block and "validateFlags" not in block, label
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_workflow_apd_gauntlet.py -k read_only_gates -v`
Expected: FAIL (`intake-schema-gate`)

- [x] **Step 3: Set `alwaysRun: true` on the three gates and drop their guard-only options**

CHANGELOG bullet: the intake schema gate, the pre-synthesis whole-run gate and the final validate now always run the full validation. Previously a schema-only guard could skip them on runs with only semantic or cross-file errors, so the pre-synthesis halt can now fire on errors it used to miss.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js CHANGELOG.md tests/test_workflow_apd_gauntlet.py
git commit -m "fix(workflow): stop read-only validate gates from skipping themselves"
```

- [ ] **Step 6: Operator — compare PR group B against the 1.7.0 baseline**

Not run: replaced by A8.1's substitute gate; no 1.7.0 live run can exist (A15.1).

Same procedure as Task 2 Step 6. Also, in a copy of a finished run, break one lens file by putting an unquoted colon in a title. Re-invoke and confirm that one `repair-…` dispatch fixes it and no lens re-runs. Then, in another copy, add a `cross_references` entry that names an unknown id, and confirm the run halts at `validate-full-prephase5`.
Expected: exit 0 for every pair; the retry count is no worse than baseline.

### Task 5: Threat-model evaluator reads and writes the canonical paths

**Files:**

- Modify: `.claude/agents/apd-threat-model-evaluator.md:3-10` (description), `:40-57` (output contract), `:61-67` (Step 1), `:363` (self-check)
- Modify: `.claude/workflows/apd-gauntlet.js:616-623` (tmeval instruction)
- Modify: `docs/threat-modeling.md:147`, `CHANGELOG.md`
- Test: `tests/test_tmeval_agent_contract.py`, `tests/test_workflow_apd_gauntlet.py`

**Interfaces:**

- Consumes: the paths the code reads: `validate.CANONICAL_RECORD_DIRS` (includes `40-threat-model`), `report/loader.py:613` and `synthesis/audit.py:116` (`40-threat-model/threat-model.findings.yaml`, root key `finding`), and the decomposed and fallback synthesis outputs `40-synthesis/deduped-findings.yaml` and `deduped-capabilities.yaml`.
- Produces: none (prompt contract only).

- [x] **Step 1: Write the failing tests**

```python
# tests/test_tmeval_agent_contract.py
def test_evaluator_reads_the_deduped_corpus():
    text = AGENT.read_text(encoding="utf-8")
    assert "20-findings" not in text and "10-capabilities" not in text
    assert "40-synthesis/deduped-findings.yaml" in text and "40-synthesis/deduped-capabilities.yaml" in text

def test_evaluator_writes_one_canonical_findings_file():
    text = AGENT.read_text(encoding="utf-8")
    assert "40-threat-model/threat-model.findings.yaml" in text
    assert "one file per finding" not in text and "tmeval-<sha8>.yaml" not in text

def test_canonical_dir_is_what_the_validator_accepts():
    from apd_gauntlet.validate import CANONICAL_RECORD_DIRS
    assert "40-threat-model" in CANONICAL_RECORD_DIRS

def test_threat_modeling_doc_names_the_canonical_path():
    doc = (AGENT.parents[2] / "docs" / "threat-modeling.md").read_text(encoding="utf-8")
    assert "40-threat-model/threat-model.findings.yaml" in doc and "20-findings/" not in doc
```

```python
# tests/test_workflow_apd_gauntlet.py
def test_tmeval_instruction_names_canonical_inputs_and_output() -> None:
    call = re.search(r"llmStep\('apd-threat-model-evaluator'.*?\}\);", _text(), re.DOTALL).group(0)
    for path in ("40-synthesis/deduped-findings.yaml", "40-synthesis/deduped-capabilities.yaml",
                 "40-threat-model/threat-model.findings.yaml", "40-synthesis/threat-model-coverage.yaml"):
        assert path in call
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_tmeval_agent_contract.py tests/test_workflow_apd_gauntlet.py -k "evaluator or tmeval or canonical_dir or threat_modeling_doc" -v`
Expected: FAIL on four new tests. `test_canonical_dir_is_what_the_validator_accepts` passes already, because it pins the code's truth. The existing tests in the selection pass.

- [x] **Step 3: Rewrite the stale passages**

Output contract item 1: all findings go in the single file `40-threat-model/threat-model.findings.yaml` under the root key `finding:` as a list (the finding-schema list form). Step 1 reads `00-context/threat-model-normalized.yaml`, `40-synthesis/deduped-findings.yaml` and `40-synthesis/deduped-capabilities.yaml`, plus the supplied sibling when present. The self-check names the same file. In the workflow instruction, add the two deduped inputs and the single output file next to the coverage YAML and report; keep both `00-context/…normalized.yaml` names (pinned by `test_tmeval_gate_widened_to_tm_present`). In the doc, line 147 names the canonical file. CHANGELOG bullet.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_tmeval_agent_contract.py tests/test_workflow_apd_gauntlet.py tests/test_evaluator_agent_authoring.py tests/test_lint_agents.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/agents/apd-threat-model-evaluator.md .claude/workflows/apd-gauntlet.js docs/threat-modeling.md CHANGELOG.md tests/test_tmeval_agent_contract.py tests/test_workflow_apd_gauntlet.py
git commit -m "fix(agents): point the threat-model evaluator at the deduped corpus and its canonical output"
```

### Task 6: Attack-path analyzer drops obsolete steps

**Files:**

- Modify: `.claude/agents/apd-attack-path-analyzer.md:98-123` (Step 5 hedge, Step 6 manual checks), `CHANGELOG.md`
- Test: `tests/test_validate_cross_file.py` (validator coverage, written first), `tests/test_lint_agent_apd_attack_path_analyzer.py`

**Interfaces:**

- Consumes: `validate.SYNTHESIS_ROLLUPS` (`asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`) and `RECORD_KINDS` (`*.findings.yaml` matches `attack-path.findings.yaml`); `templates/attack-path-report.template.md` (exists).
- Produces: none.

- [x] **Step 1: Pin the validator coverage the deletion relies on**

```python
@pytest.mark.parametrize("name, body", [
    ("asset-graph.yaml", "bogus_key: 1\n"),
    ("attack-paths.yaml", "bogus_key: 1\n"),
    ("defense-graph.yaml", "bogus_key: 1\n"),
    ("attack-path.findings.yaml", "finding:\n  - agent: attack_path_analyzer\n"),
])
def test_validate_schema_checks_each_attack_path_artifact(tmp_path, name, body):
    dst = _copy_clean_run(tmp_path)
    (dst / "40-synthesis" / name).write_text(body)
    result = CliRunner().invoke(main, ["validate", "--schema-only", "--errors-only", str(dst)])
    assert result.exit_code == 1 and name in result.output
```

Run: `pytest tests/test_validate_cross_file.py -k each_attack_path_artifact -v`
Expected: PASS (four cases). This confirms `validate` already covers all four files. If any case fails, stop and report: Step 6 must not be deleted.

- [x] **Step 2: Write the failing agent-text tests**

```python
def test_agent_has_no_obsolete_template_hedge() -> None:
    text = AGENT.read_text()
    assert "does not yet exist" not in text and "Task C-22" not in text
    assert "templates/attack-path-report.template.md" in text
    assert (REPO_ROOT / "templates" / "attack-path-report.template.md").is_file()

def test_agent_has_no_manual_schema_check_passage() -> None:
    text = AGENT.read_text()
    for stale in ("Task C-21", "direct schema check", "vacuously"):
        assert stale not in text
    assert "apd-gauntlet validate" in text
```

Run: `pytest tests/test_lint_agent_apd_attack_path_analyzer.py -v`
Expected: FAIL on the two new tests

- [x] **Step 3: Delete both passages**

Step 5 keeps only "Render `40-synthesis/attack-path-report.md` from `templates/attack-path-report.template.md`" plus the Mermaid sentence. Step 6 becomes: run `apd-gauntlet validate <run_dir>`, which schema-checks the three graph files and every record in `attack-path.findings.yaml` and checks edge integrity; fix any reported error before declaring success. CHANGELOG bullet.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_lint_agent_apd_attack_path_analyzer.py tests/test_validate_cross_file.py tests/test_lint_agents.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/agents/apd-attack-path-analyzer.md CHANGELOG.md tests/test_lint_agent_apd_attack_path_analyzer.py tests/test_validate_cross_file.py
git commit -m "fix(agents): drop the attack-path analyzer's obsolete template hedge and manual schema checks"
```

### Task 7: Remove the contradictory id self-check

**Files:**

- Modify: `.claude/agents/apd-confidentiality.md:136` (delete item 10), `CHANGELOG.md`
- Test: `tests/test_agent_prompt_id_contract.py`

**Interfaces:**

- Consumes: `LENS_AGENTS` in the test module.
- Produces: none. A scan of the other eight lenses' `## Self-check before emitting` sections found no id item; the new test keeps all nine clean.

- [x] **Step 1: Write the failing test**

```python
def test_lens_self_checks_never_ask_for_an_id():
    offenders = []
    for name in LENS_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8")
        section = text.split("## Self-check", 1)[1].split("\n## ", 1)[0]
        if re.search(r"(?i)\bID\b[^\n]*(computed|deterministic)", section):
            offenders.append(name)
    assert offenders == [], f"self-check asks the lens to author an id: {offenders}"
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_agent_prompt_id_contract.py -v`
Expected: FAIL (`apd-confidentiality.md`)

- [x] **Step 3: Delete item 10** (the list ends at item 9) and add the CHANGELOG bullet.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_agent_prompt_id_contract.py tests/test_lint_agents.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add .claude/agents/apd-confidentiality.md CHANGELOG.md tests/test_agent_prompt_id_contract.py
git commit -m "fix(agents): drop the confidentiality self-check item that asked for an id"
```

- [ ] **Step 6: Operator — compare PR group C (Tasks 5–7) against the 1.7.0 baseline**

Not run: replaced by A8.1's substitute gate; no 1.7.0 live run can exist (A15.1).

Same procedure as Task 2 Step 6. Also confirm that no candidate has a file under `20-findings/` and that each candidate's tmeval findings are in `40-threat-model/threat-model.findings.yaml`.
Expected: exit 0 for every pair.

### Task 8: Domain skill rebuilds when pack content changes

**Files:**

- Modify: `tools/apd_gauntlet/build_domain_skill.py:144-165` (`_existing_pack_signature`), `:275-281` (freshness check), `:291-304` (frontmatter)
- Modify: `docs/adapting-to-other-domains.md:189`, `CHANGELOG.md`
- Test: `tests/test_build_domain_skill.py`

**Interfaces:**

- Consumes: `_iter_pack_files` order (declared pack, include glob, sorted match).
- Produces:
  - `def _pack_content_sha256(metas: list[tuple[str, dict[str, Any], pathlib.Path]]) -> str`: SHA-256 hex over each pack in declared order, first its `domain.yaml`, then every included file. Each file contributes `f"{name}\0{rel}\0".encode()`, its raw bytes and `b"\0"`.
  - `_existing_pack_signature(out_path) -> tuple[list[tuple[str, str]], str | None, str | None] | None` (packs, framework_version, content_sha256)
  - Full-skill frontmatter key `metadata.content_sha256: <64 hex>` (indented two spaces, like `framework_version`), on the line directly after `framework_version`.

- [x] **Step 1: Write the failing tests**

```python
def _copied_pack(tmp_path) -> pathlib.Path:
    shutil.copytree(DOMAINS / "sample", tmp_path / "domains" / "sample")
    return tmp_path / "domains"

def test_rebuild_when_pack_file_edited_without_version_bump(tmp_path):
    domains, out = _copied_pack(tmp_path), tmp_path / "apd-domain"
    build_domain_skill(["sample"], domains, out, "1.0.0")
    rubric = domains / "sample" / "severity-rubric.md"
    rubric.write_text(rubric.read_text() + "\nEDITED-WITHOUT-BUMP\n")
    build_domain_skill(["sample"], domains, out, "1.0.0")
    assert "EDITED-WITHOUT-BUMP" in (out / "SKILL.md").read_text()
    assert "EDITED-WITHOUT-BUMP" in (out / "by-goal" / "confidentiality.md").read_text()

def test_rebuild_when_domain_yaml_edited(tmp_path):
    domains, out = _copied_pack(tmp_path), tmp_path / "apd-domain"
    build_domain_skill(["sample"], domains, out, "1.0.0")
    meta = domains / "sample" / "domain.yaml"
    meta.write_text(meta.read_text().replace("PHI store specific to the sample domain.", "EDITED store."))
    build_domain_skill(["sample"], domains, out, "1.0.0")
    assert "EDITED store." in (out / "SKILL.md").read_text()

def test_content_hash_recorded_in_frontmatter(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    fm = _yaml.safe_load((out / "SKILL.md").read_text().split("---\n")[1])
    assert re.fullmatch(r"[0-9a-f]{64}", fm["metadata"]["content_sha256"])

def test_legacy_skill_without_hash_is_rebuilt_once(tmp_path):
    out = tmp_path / "apd-domain"
    p = build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    p.write_text(re.sub(r"(?m)^  content_sha256: .*\n", "", p.read_text()))
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    assert "content_sha256:" in p.read_text()
```

The existing `test_idempotent_no_rewrite_when_pack_set_unchanged` must stay green unchanged.

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_build_domain_skill.py -v`
Expected: FAIL on the four new tests

- [x] **Step 3: Implement the hash and the three-part signature**

Compute the hash before the freshness check and compare against `(requested, framework_version, content_hash)`. Do not regenerate the committed `.claude/skills/apd-domain/`: its frontmatter has no hash, so the first run's setup rebuilds it. In the docs, line 189 says the staleness guard compares `metadata.packs`, `framework_version` and `metadata.content_sha256`, so an edit without a version bump still rebuilds. CHANGELOG bullet.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_build_domain_skill.py tests/test_build_domain_skill_pruning.py tests/test_lint_skills.py -v && mypy tools/`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/build_domain_skill.py docs/adapting-to-other-domains.md CHANGELOG.md tests/test_build_domain_skill.py
git commit -m "fix(domain-skill): rebuild when pack content changes without a version bump"
```

### Task 9: `canonicalize` mints `cev-` and `tm-` ids

**Files:**

- Modify: `tools/apd_gauntlet/linters.py` (add two helpers after `compute_boundary_id`, `:107-109`)
- Modify: `tools/apd_gauntlet/threat_model/author.py:51-58` (`entry_id_for` delegates)
- Modify: `tools/apd_gauntlet/canonicalize.py:1-26` (docstring), `:120-127` (`CanonicalizeResult`), `:272-310` (`canonicalize_run`)
- Modify: `tools/apd_gauntlet/cli.py:1266-1274` (summary line)
- Modify: `tools/apd_gauntlet/data/schemas/code-evidence-index.schema.json:51-54`, `tools/apd_gauntlet/data/schemas/threat-model-normalized.schema.json:36-39,64`
- Modify: `tools/apd_gauntlet/validate.py` (`run_cross_file_pass`, `:702-865`: call the presence check)
- Modify: `docs/deterministic-field-register.md:17-29` (two rows), `docs/schema-evolution.md` (new section above `:77`), `CHANGELOG.md`
- Modify: `docs/adrs/0020-tooling-authored-derived-fields.md` (new `## Amendment (v1.7.1)` section before `## References`)
- Test: `tests/test_canonicalize_context_ids.py`

**Interfaces:**

- Consumes: `threat_model.mappings.stride_letter_to_apd_goals`, `linddun_letter_to_apd_goals`; `CanonicalizeResult.parse_errors`.
- Produces:
  - `linters.compute_cev_id(qualified_name: str, line_range: str, repo: str | None = None) -> str`: `cev-` + sha256(`qualified_name|line_range`)[:8], or sha256(`repo|qualified_name|line_range`)[:8] when `repo` is given.
  - `linters.compute_tm_entry_id(asset: str, threat: str, source_locator: str) -> str`: `tm-` + sha256(`asset + threat + source_locator`)[:8], with no separator, the same formula as today's `entry_id_for`.
  - `canonicalize.THREAT_MODEL_CONTEXT_FILES = ("threat-model-normalized.yaml", "threat-model-supplied-normalized.yaml")`
  - `canonicalize._mint_code_evidence_ids(run_dir: Path) -> int` and `canonicalize._mint_threat_model_ids(run_dir: Path) -> int`
  - `CanonicalizeResult.context_ids_minted: int = 0`
  - `validate._validate_context_ids(run_dir: pathlib.Path, report: ValidationReport) -> None`: one ERROR per `00-context` entry with no `id`, no `entry_id` or no `inferred_apd_goals`; the message ends `run 'apd-gauntlet canonicalize'`.
  - Rules: fill a field only when it is absent and never rewrite an existing one, because findings, `c4-recon.yaml` and tmeval keys may already cite it. Use the repo-qualified `cev-` input only when the index declares top-level `repos` and the entry has `repo`. Derive goals from `stride_letter`, else `linddun_letter`, else `[]`. Rewrite a file only when a field was filled; a minted `id` becomes the entry's first key. A YAML parse failure is appended to `parse_errors`, not raised.

- [x] **Step 1: Write the failing tests**

```python
ENTRY = {"qualified_name": "svc.auth.verify", "kind": "function", "file_path": "src/auth.py",
         "line_range": "L10-L20", "excerpt": "if not verify(token): raise", "apd_relevance": ["authenticity"]}
TM = {"asset": "pricing-service", "threat": "Spoofed caller at the pricing API",
      "source_locator": "inventory:pricing-service", "extraction_confidence": "medium",
      "methodology": "stride", "framework_refs": {"stride_letter": "S"}, "mitigation": "mTLS"}

def _write(run, name, doc):
    p = run / "00-context" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p

def _index_doc(entries, repos=None):
    idx = {"indexed_commit_sha": "abc1234", "cbm_project": "p",
           "generated_at": "2026-10-11T00:00:00Z", "entries": entries}
    return {"code_evidence_index": {**idx, "repos": repos} if repos else idx}

def _tm_doc(entries, generated_by="threat_model_author"):
    return {"schema_version": 1, "generated_by": generated_by, "methodology": "stride",
            "source_artifact": "00-context/asset-inventory.yaml", "entries": entries}

def _index(run, entries, repos=None):
    return _write(run, "code-evidence-index.yaml", _index_doc(entries, repos))

def _tm(run, entries, name="threat-model-normalized.yaml", generated_by="threat_model_author"):
    return _write(run, name, _tm_doc(entries, generated_by))

def _entries(path):
    doc = yaml.safe_load(path.read_text())
    return (doc.get("code_evidence_index") or doc)["entries"]

def test_cev_formula():
    assert compute_cev_id("svc.auth.verify", "L10-L20") == "cev-" + hashlib.sha256(b"svc.auth.verify|L10-L20").hexdigest()[:8]
    assert compute_cev_id("a", "L1", repo="core") == "cev-" + hashlib.sha256(b"core|a|L1").hexdigest()[:8]

def test_tm_formula_matches_skeleton_helper():
    assert compute_tm_entry_id("a", "t", "l") == entry_id_for("a", "t", "l") == "tm-" + hashlib.sha256(b"atl").hexdigest()[:8]

def test_mints_missing_cev_id(tmp_path):
    p = _index(tmp_path, [dict(ENTRY)])
    res = canonicalize_run(tmp_path)
    e = _entries(p)[0]
    assert e["id"] == compute_cev_id("svc.auth.verify", "L10-L20") and list(e)[0] == "id"
    assert res.context_ids_minted == 1

def test_multi_repo_ids_include_repo(tmp_path):
    repos = [{"cbm_project": r, "indexed_commit_sha": "abc1234"} for r in ("core", "supervisor")]
    p = _index(tmp_path, [dict(ENTRY, repo="core"), dict(ENTRY, repo="supervisor")], repos=repos)
    canonicalize_run(tmp_path)
    ids = [e["id"] for e in _entries(p)]
    assert ids == [compute_cev_id("svc.auth.verify", "L10-L20", repo=r) for r in ("core", "supervisor")]
    assert ids[0] != ids[1]

def test_mints_tm_entry_id_and_stride_goals(tmp_path):
    p = _tm(tmp_path, [dict(TM)])
    canonicalize_run(tmp_path)
    e = _entries(p)[0]
    assert e["entry_id"] == entry_id_for(TM["asset"], TM["threat"], TM["source_locator"])
    assert e["inferred_apd_goals"] == ["authenticity"]

def test_linddun_maestro_and_authored_goals(tmp_path):
    p = _tm(tmp_path, [dict(TM, threat="t1", methodology="linddun", framework_refs={"linddun_letter": "L"}),
                       dict(TM, threat="t2", methodology="maestro", framework_refs={}),
                       dict(TM, threat="t3", inferred_apd_goals=["integrity", "availability"])])
    canonicalize_run(tmp_path)
    goals = [e["inferred_apd_goals"] for e in _entries(p)]
    assert goals == [linddun_letter_to_apd_goals("L"), [], ["integrity", "availability"]]

def test_supplied_sibling_is_minted_too(tmp_path):
    p = _tm(tmp_path, [dict(TM)], name="threat-model-supplied-normalized.yaml", generated_by="threat_model_recon")
    canonicalize_run(tmp_path)
    assert _entries(p)[0]["entry_id"].startswith("tm-")

def test_existing_context_ids_are_never_rewritten(tmp_path):  # Review Focus 3
    run = shutil.copytree(REPO / "examples/apd-20260612-home-assistant/expected", tmp_path / "run")
    files = [run / "00-context" / n for n in ("code-evidence-index.yaml", "threat-model-normalized.yaml", "c4-recon.yaml")]
    before = [f.read_bytes() for f in files]
    assert canonicalize_run(run).context_ids_minted == 0
    assert [f.read_bytes() for f in files] == before

def test_second_pass_is_a_no_op(tmp_path):
    p = _index(tmp_path, [dict(ENTRY)])
    canonicalize_run(tmp_path)
    first = p.read_bytes()
    assert canonicalize_run(tmp_path).context_ids_minted == 0 and p.read_bytes() == first

def test_unparseable_context_file_is_reported(tmp_path):
    (tmp_path / "00-context").mkdir()
    (tmp_path / "00-context/code-evidence-index.yaml").write_text("code_evidence_index: [unclosed\n")
    assert any("code-evidence-index.yaml" in p for p, _ in canonicalize_run(tmp_path).parse_errors)

def test_relaxed_schemas_accept_id_less_entries_but_reject_bad_ids():
    reg = build_registry()
    cev = Draft202012Validator(read_schema("code-evidence-index.schema.json"), registry=reg)
    tm = Draft202012Validator(read_schema("threat-model-normalized.schema.json"), registry=reg)
    assert list(cev.iter_errors(_index_doc([dict(ENTRY)]))) == []
    assert list(tm.iter_errors(_tm_doc([dict(TM)]))) == []
    assert list(cev.iter_errors(_index_doc([dict(ENTRY, id="cev-XYZ")])))
    assert list(tm.iter_errors(_tm_doc([dict(TM, entry_id="tm-nothex!")])))

def test_validate_requires_minted_context_ids(tmp_path):
    run = shutil.copytree(FIX / "runs/clean-run", tmp_path / "run")
    _index(run, [dict(ENTRY)])
    r = CliRunner().invoke(main, ["validate", str(run)])
    assert r.exit_code == 1 and "has no id" in r.output
    canonicalize_run(run)
    assert "has no id" not in CliRunner().invoke(main, ["validate", str(run)]).output

def test_adr_0020_records_the_mint_when_absent_amendment():
    text = next((REPO / "docs" / "adrs").glob("0020-*.md")).read_text(encoding="utf-8")
    section = text.split("## Amendment (v1.7.1)", 1)[1]
    assert "cev-" in section and "tm-" in section and "minted only when absent" in section
```

`REPO = Path(__file__).resolve().parent.parent` and `FIX = REPO / "tests" / "fixtures"`, as in the sibling suites.

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_canonicalize_context_ids.py -v`
Expected: FAIL (`ImportError: compute_cev_id`)

- [x] **Step 3: Implement the helpers, the two minting passes, the schema relaxations, the presence check and the docs**

`canonicalize_run` calls `_mint_code_evidence_ids` and `_mint_threat_model_ids` before Pass 1 and adds their counts to `context_ids_minted`. The CLI summary appends `, {n} context ids minted` only when `n > 0`, so existing outputs are unchanged. In both schemas, drop the fields from `required`, keep their patterns and add `"readOnly": true`. Register rows: `cev-*` (`linters.compute_cev_id` via `canonicalize._mint_code_evidence_ids`; `qualified_name|line_range`, repo-qualified in multi-repo indexes; enforced by `validate._validate_context_ids`; the agent emits no `id`) and `tm-*` (`linters.compute_tm_entry_id` via `canonicalize._mint_threat_model_ids`; also derives `inferred_apd_goals` from `framework_refs`). Both rows note "minted only when absent; an existing id is never rewritten". The `tm-*` row also notes that the deterministic parsers keep their own pipe-joined variant. Schema-evolution section `## v1.7.1 — Context ids minted by canonicalize`, worded like the v1.7.0 id-ownership entry. The ADR-0020 amendment says three things. `cev-` and `tm-` join the families the assembler owns. For these two families an id is minted only when absent, and an existing id is never rewritten. The reason is back-compatibility with committed examples and older runs, whose hand-assigned `cev-` ids (0 of 46 match the hash in the Home Assistant example) and `tm-` ids are already cited by findings, `c4-recon.yaml` and tmeval keys; rewriting them would orphan those references. Agents no longer emit either id, so in a 1.7.1 run every one is Python-minted. CHANGELOG bullet.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_canonicalize_context_ids.py tests/test_canonicalize.py tests/test_cli_canonicalize.py tests/test_register_consistency.py tests/test_code_evidence_index_schema.py tests/test_other_schemas.py tests/test_author_threat_model.py tests/test_validate_example_run.py -v && mypy tools/`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/linters.py tools/apd_gauntlet/threat_model/author.py tools/apd_gauntlet/canonicalize.py tools/apd_gauntlet/cli.py tools/apd_gauntlet/validate.py tools/apd_gauntlet/data/schemas/code-evidence-index.schema.json tools/apd_gauntlet/data/schemas/threat-model-normalized.schema.json docs/deterministic-field-register.md docs/schema-evolution.md docs/adrs/0020-tooling-authored-derived-fields.md CHANGELOG.md tests/test_canonicalize_context_ids.py
git commit -m "feat(canonicalize): mint missing cev- and tm- ids in Python"
```

### Task 10: Code recon and threat-model agents emit content only

**Files:**

- Modify: `.claude/agents/apd-code-recon.md:66-89` (entry shape and rules), `:176` and `:182` (c4-recon provenance), `:216-223` (self-check)
- Modify: `.claude/agents/apd-threat-model-author.md:110-121` (Step 4), `:155` (self-check)
- Modify: `.claude/agents/apd-threat-model-recon.md:123` (free-form `entry_id`; the MAESTRO goal rule at `:139-141` stays agent-authored and unchanged)
- Modify: `.claude/skills/apd-threat-model-methodologies/SKILL.md:328-332` (rule 6)
- Modify: `templates/code-architecture-brief.template.md:36-47`, `templates/threat-model-authored.template.md:54,62,71,94-96`
- Modify: `.claude/workflows/apd-gauntlet.js` (two canonicalize steps), `tools/apd_gauntlet/plan_run.py:74-99` (two rows), `CHANGELOG.md`
- Test: `tests/test_agent_prompt_id_contract.py`, `tests/test_lint_agent_apd_code_recon.py`, `tests/test_lint_agent_apd_threat_model_author.py`, `tests/test_skill_apd_threat_model_methodologies_authoring.py`, `tests/test_threat_model_authored_template.py`, `tests/test_workflow_apd_gauntlet.py`, `tests/test_cli_plan_run.py`

**Interfaces:**

- Consumes: Task 9's minting (absent fields are filled), Task 2's `llmStep`.
- Produces:
  - Workflow `pyStep('canonicalize', {phase: 'canonicalize', label: 'canonicalize-code-evidence', alwaysRun: true, …})` inside the code-recon branch, after the halt check.
  - Workflow `pyStep('canonicalize', {phase: 'canonicalize', label: 'canonicalize-threat-model', alwaysRun: true, …})` right after the tm-recon `if/else`, before `function runTier`.
  - Two plan-run `CLI` rows `canonicalize runs/<id>` with phase `canonicalize`: one after the code-recon row (same condition), one after the tm-recon block (always).
  - Contract text: code recon emits entries without `id` and cites edges in `c4-recon.yaml` as `code:<qualified_name>:<line_range>`. The TM author emits no `entry_id`, and no `inferred_apd_goals` for STRIDE or LINDDUN entries, even on cells copied from the skeleton. The TM recon emits no `entry_id` for free-form or MAESTRO entries.

- [x] **Step 1: Write the failing tests**

```python
# tests/test_agent_prompt_id_contract.py
CONTEXT_AGENTS = ["apd-code-recon.md", "apd-threat-model-author.md", "apd-threat-model-recon.md"]

def test_context_agents_leave_ids_to_canonicalize():
    for name in CONTEXT_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8")
        assert re.search(r"cev-<sha8>|tm-<sha8>|sha8\(|sha256\(", text) is None, name
        assert "apd-gauntlet canonicalize" in text, name
```

```python
# tests/test_lint_agent_apd_code_recon.py
def test_agent_emits_no_cev_ids() -> None:
    text = AGENT.read_text()
    assert "Do NOT emit `id`" in text and "cev-0a000001" not in text

def test_brief_template_cites_code_locators_not_ids() -> None:
    assert "cev-" not in (REPO_ROOT / "templates/code-architecture-brief.template.md").read_text()
```

```python
# tests/test_lint_agent_apd_threat_model_author.py
def test_agent_does_not_compute_entry_ids_or_goals() -> None:
    text = AGENT.read_text()
    assert "Do NOT emit `entry_id`" in text and "inverting the canonical mapping tables" not in text
```

```python
# tests/test_skill_apd_threat_model_methodologies_authoring.py
def test_rule6_defers_entry_ids_to_canonicalize() -> None:
    section = _authoring_section()
    assert "canonicalize" in section and "recomputes as" not in section
```

```python
# tests/test_threat_model_authored_template.py
def test_template_carries_no_tm_ids() -> None:
    assert re.search(r"tm-[0-9a-f]{8}", _text()) is None
```

```python
# tests/test_workflow_apd_gauntlet.py
def test_context_ids_minted_before_their_consumers() -> None:
    t = _text()
    assert t.index("llmStep('apd-code-recon'") < t.index("label: 'canonicalize-code-evidence'") < t.index("phase('threat-model-author')")
    assert t.index("phase('tm-recon')") < t.index("label: 'canonicalize-threat-model'") < t.index("function runTier")
```

```python
# tests/test_cli_plan_run.py
def test_plan_run_mints_context_ids_before_tier_1(tmp_path):
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, FULL_CFG))]).output)
    canon = [i for i, s in enumerate(plan) if s["phase"] == "canonicalize"]
    first_lens = next(i for i, s in enumerate(plan) if s["ref"] == "apd-confidentiality")
    assert len(canon) == 2 and max(canon) < first_lens

def test_plan_run_without_code_recon_mints_tm_ids_only(tmp_path):
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, dict(BASE_CFG, code_recon="disabled")))]).output)
    assert sum(1 for s in plan if s["phase"] == "canonicalize") == 1
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_agent_prompt_id_contract.py tests/test_lint_agent_apd_code_recon.py tests/test_lint_agent_apd_threat_model_author.py tests/test_skill_apd_threat_model_methodologies_authoring.py tests/test_threat_model_authored_template.py tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py -v`
Expected: FAIL on the nine new tests

- [x] **Step 3: Rewrite the contracts and wire the two steps**

Code recon: drop `id: cev-<sha8>` from the shape, and replace the "`id` is deterministic" rule with "Do NOT emit `id` on entries: `apd-gauntlet canonicalize` mints `cev-` ids right after this phase." The c4-recon example locator and the `uses_edges` rule cite `code:<qualified_name>:<line_range>`, which satisfies the c4-discipline skill's "points at that edge". Self-check item 7: no entry carries an `id`. TM author Step 4 becomes "Leave ids and goals to the assembler": "Do NOT emit `entry_id`", and for STRIDE and LINDDUN entries do not emit `inferred_apd_goals` either (also drop both from cells copied from the skeleton); `apd-gauntlet canonicalize` mints `tm-` from `asset + threat + source_locator` and derives goals with `threat_model/mappings.py`; MAESTRO entries still carry agent-set `inferred_apd_goals` from the layer table. The self-check line becomes "no entry carries `entry_id`". TM recon line 123 becomes "Do NOT emit `entry_id`: `apd-gauntlet canonicalize` mints it after this phase." Skill rule 6 says both fields are minted by `apd-gauntlet canonicalize` and still names `entry_id` and `source_locator`. Templates: the brief's column becomes "Code anchors (`qualified_name:Lx-Ly`)"; the authored template drops the `TM entry IDs:` lines and labels entries `<letter>/<surface>`, because ids live only in the YAML. CHANGELOG bullet.

- [x] **Step 4: Run to verify pass**

Run: `pytest -q && markdownlint-cli2 ".claude/**/*.md" "docs/**/*.md" "!docs/superpowers/plans/**"`
Expected: all pass; 0 lint errors

- [x] **Step 5: Commit**

```bash
git add .claude/agents/apd-code-recon.md .claude/agents/apd-threat-model-author.md .claude/agents/apd-threat-model-recon.md .claude/skills/apd-threat-model-methodologies/SKILL.md templates/code-architecture-brief.template.md templates/threat-model-authored.template.md .claude/workflows/apd-gauntlet.js tools/apd_gauntlet/plan_run.py CHANGELOG.md tests
git commit -m "fix(agents): code recon and threat-model agents emit content; canonicalize mints cev-/tm- ids"
```

- [ ] **Step 6: Operator — compare PR group E (Tasks 9–10) against the 1.7.0 baseline**

Not run: replaced by A8.1's substitute gate; no 1.7.0 live run can exist (A15.1).

Same procedure as Task 2 Step 6. Also confirm in each candidate that `apd-gauntlet validate <run>` reports no `has no id` errors, and that rerunning `apd-gauntlet canonicalize <run>` prints no `context ids minted`, which shows every id was minted once.
Expected: exit 0 for every pair.

### Task 11: `validate` checks that excerpts appear verbatim in the cited input

**Files:**

- Modify: `tools/apd_gauntlet/validate.py` (new helpers after `ANALYZER_DERIVED_ARTIFACTS`, `:202-208`)
- Modify: `tools/apd_gauntlet/cli.py:50-126` (`--strict-excerpts`; route the check in the `--tier` and whole-run branches)
- Modify: `docs/running-the-gauntlet.md:42` (validate line), `:512-520` (troubleshooting bullet), `CHANGELOG.md`
- Test: `tests/test_validate_excerpts.py`

**Interfaces:**

- Consumes: `_iter_records`, `Violation`; the CLI's existing `run_dir` / `--tier` target split (`cli.py:73`).
- Produces:
  - `def normalize_excerpt_text(text: str) -> str`: removes the Markdown inline markers `` ` `` and `*`, then collapses whitespace to single spaces
  - `def excerpt_fragments(excerpt: str) -> list[str]`: splits at every `...` and `…`, normalizes each piece and drops the empty ones (no ellipsis gives one fragment)
  - `def check_excerpts_verbatim(run_dir: pathlib.Path, *, records_dir: pathlib.Path | None = None) -> list[Violation]`: checks the records under `records_dir` (default `run_dir`), resolving artifacts against `run_dir`
  - CLI `apd-gauntlet validate RUN_DIR [--tier DIR] --strict-excerpts`. Unless `--schema-only` is set, both the `--tier` branch and the whole-run branch append the check's violations to `warnings`, or to `errors` with `--strict-excerpts`. `--strict` keeps escalating every warning, these included. `run_cross_file_pass` is unchanged, so the tier gates (`validate --tier <dir> --json`, Task 3) see the same violations, and the repair template covers them.
  - Message: `evidence[{i}].excerpt not found verbatim in artifact '{artifact}'`
  - Scope: only an artifact that resolves, as `run_dir/inputs/<artifact>` or `run_dir/<artifact>`, to a file inside `(run_dir / "inputs").resolve()`. Run-internal artifacts (`00-context/`, `40-synthesis/`, the tier dirs, `code-evidence-index.yaml`) are skipped silently, as are excerpts wholly in parentheses (absence markers such as `(absent in supplied TM)`), unresolvable paths, paths that escape `inputs/`, and files that are not UTF-8.
  - Matching: every fragment must appear, in order, in one haystack: each fragment is searched from the end of the previous match. The haystacks are the artifact's whole normalized text and, for `.yaml`, `.yml` and `.json` inputs, each normalized parsed string scalar.

- [x] **Step 1: Write the failing tests**

```python
FINDING_EX = "All Kafka topics use AES-256 at-rest encryption via broker-managed keys"
CAP_EX = "Field-level envelope encryption for PHI columns with DEKs from KMS"

def _run(tmp_path, tech_plan: str | bytes | None) -> Path:
    run = shutil.copytree(FIX / "runs" / "clean-run", tmp_path / "run")
    target = run / "inputs" / "tech_plan.md"
    if isinstance(tech_plan, bytes):
        target.write_bytes(tech_plan)
    elif tech_plan is not None:
        target.write_text(tech_plan)
    return run

def _set_excerpt_from(run, old, new):
    f = run / "10-trustworthiness/confidentiality.findings.yaml"
    f.write_text(f.read_text().replace(old, new))

def _set_excerpt(run, excerpt):
    _set_excerpt_from(run, FINDING_EX, excerpt)

def _validate(run, *flags):
    return CliRunner().invoke(main, ["validate", *flags, str(run)])

def test_verbatim_excerpts_are_clean(tmp_path):
    r = _validate(_run(tmp_path, f"## 4.2\n{FINDING_EX}.\n\n## 5.3\n{CAP_EX}.\n"))
    assert r.exit_code == 0 and "not found verbatim" not in r.output

def test_reflowed_whitespace_still_matches(tmp_path):
    src = "All Kafka topics use AES-256\n   at-rest encryption via\tbroker-managed keys\n" + CAP_EX
    assert "not found verbatim" not in _validate(_run(tmp_path, src)).output

def test_markdown_inline_markup_is_ignored(tmp_path):  # Review Focus 4
    src = "All **Kafka topics** use `AES-256` at-rest encryption via broker-managed keys\n" + CAP_EX
    assert "not found verbatim" not in _validate(_run(tmp_path, src)).output

def test_absence_marker_is_not_checked(tmp_path):  # Review Focus 4
    run = _run(tmp_path, CAP_EX)
    _set_excerpt(run, "(absent in supplied TM)")
    assert "not found verbatim" not in _validate(run).output

def test_paraphrase_warns_but_exits_zero(tmp_path):
    r = _validate(_run(tmp_path, "Topics are encrypted with broker keys.\n" + CAP_EX))
    assert r.exit_code == 0
    assert "WARNING" in r.output and "evidence[0].excerpt not found verbatim in artifact 'tech_plan.md'" in r.output

def test_strict_excerpts_makes_it_an_error(tmp_path):
    r = _validate(_run(tmp_path, "Topics are encrypted with broker keys.\n" + CAP_EX), "--strict-excerpts")
    assert r.exit_code == 1 and "ERROR" in r.output and "not found verbatim" in r.output

def test_missing_or_binary_artifact_is_skipped(tmp_path):
    assert check_excerpts_verbatim(_run(tmp_path / "a", None)) == []
    assert check_excerpts_verbatim(_run(tmp_path / "b", b"\xff\xfe\x00binary")) == []

def _cite_from(run, old, new):
    _set_excerpt_from(run, f"artifact: {old}", f"artifact: {new}")

def _cite(run, artifact):
    _cite_from(run, "tech_plan.md", artifact)

def test_ellipsis_fragments_must_appear_in_order(tmp_path):  # Review Focus 4
    run = _run(tmp_path, "Topics use AES-256 at rest. Keys rotate yearly.\n" + CAP_EX)
    _set_excerpt(run, "Topics use AES-256 ... Keys rotate yearly")
    assert check_excerpts_verbatim(run) == []
    _set_excerpt_from(run, "Topics use AES-256 ... Keys rotate yearly", "Keys rotate yearly … Topics use AES-256")
    assert len(check_excerpts_verbatim(run)) == 1

def test_run_internal_artifacts_are_skipped(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "00-context/code-evidence-index.yaml").write_text("note: unrelated text\n")
    _cite(run, "code-evidence-index.yaml")
    assert check_excerpts_verbatim(run) == []
    _cite_from(run, "code-evidence-index.yaml", "40-synthesis/attack-paths.yaml")
    assert check_excerpts_verbatim(run) == []

def test_paths_escaping_inputs_are_not_read(tmp_path):
    (tmp_path / "secret.md").write_text("unrelated text")
    run = _run(tmp_path, CAP_EX)
    _cite(run, "../secret.md")
    assert check_excerpts_verbatim(run) == []
    _cite_from(run, "../secret.md", "inputs/../00-context/context-brief.md")
    assert check_excerpts_verbatim(run) == []

def test_yaml_input_matches_parsed_scalars(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/kafka.yaml").write_text("note: 'it''s replicated: factor 3'\n")
    _cite(run, "kafka.yaml")
    _set_excerpt(run, "it's replicated: factor 3")
    assert check_excerpts_verbatim(run) == []

def test_tier_gate_reports_excerpt_violations(tmp_path):
    run = _run(tmp_path, "Topics are encrypted with broker keys.\n" + CAP_EX)
    r = _validate(run, "--tier", "10-trustworthiness")
    assert r.exit_code == 0 and "WARNING" in r.output and "not found verbatim" in r.output
    r = _validate(run, "--tier", "10-trustworthiness", "--strict-excerpts")
    assert r.exit_code == 1 and "not found verbatim" in r.output

def test_schema_only_skips_the_check(tmp_path):
    run = _run(tmp_path, "Topics are encrypted with broker keys.\n" + CAP_EX)
    assert "not found verbatim" not in _validate(run, "--schema-only").output
```

- [x] **Step 2: Run to verify failure**

Run: `pytest tests/test_validate_excerpts.py -v`
Expected: FAIL (`ImportError: check_excerpts_verbatim`)

- [x] **Step 3: Implement the check, the flag and the docs**

Read each artifact once per call (dict cache). A `UnicodeDecodeError` skips the artifact; a parse error on a `.yaml`/`.yml`/`.json` input leaves only the whole-text haystack. The docs validate line becomes `apd-gauntlet validate <run-dir> [--strict-excerpts]   # three-pass validation`. The troubleshooting bullet covers:

- the warning and its scope (files under `inputs/` only, at tier gates and in the whole-run pass);
- the normalization (whitespace, backticks, `*`) and ellipsis fragments;
- the absence-marker exemption;
- that WS3 makes the warning an error by default.

CHANGELOG bullet: the new check warns by default and `--strict-excerpts` makes it an error.

- [x] **Step 4: Run to verify pass**

Run: `pytest tests/test_validate_excerpts.py tests/test_validate_cross_file.py tests/test_validate_tier.py tests/test_validate_example_run.py tests/test_examples.py -v && mypy tools/`
Expected: PASS. The three committed examples print no excerpt warnings, because their `inputs/` directory sits beside `expected/`, not inside it. Pointed at those sibling inputs during planning, the same rules gave 0, 1 and 24 warnings (claim-event-bus, acme mobile banking, Home Assistant), so a run with its own `inputs/` should expect a small count like these.

- [x] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tools/apd_gauntlet/cli.py docs/running-the-gauntlet.md CHANGELOG.md tests/test_validate_excerpts.py
git commit -m "feat(validate): warn when an evidence excerpt is not verbatim in its artifact"
```

### Task 11b: `init-run` refuses links that escape `inputs/`

(Consolidated plan task N1.)

Executed 2026-10-16 as commit `5bb52ec`, merged in #49 (register A8.8, A15.5).

**Files:**

- Modify: `tools/apd_gauntlet/init_run.py` (`scaffold_run`, new helpers)
- Modify: `tools/apd_gauntlet/cli.py` (`init_run_cmd`)
- Create: `tests/test_init_run_symlinks.py`
- Modify: `docs/running-the-gauntlet.md` (one sentence under the `init-run` section), `CHANGELOG.md` (Fixed)

**Interfaces:**

- Produces (`init_run.py`): `class UnsafeInputsError(ValueError)`; `def find_escaping_links(inputs_src: pathlib.Path) -> list[str]` — walks with `os.walk(followlinks=False)`, returns sorted POSIX paths relative to `inputs_src` of every symlink (file, directory or dangling) whose `os.path.realpath` is not `inputs_src.resolve()` or below it; `scaffold_run(...)` raises `UnsafeInputsError` **before creating any directory**, with the message `inputs contain links that point outside the inputs folder: <rel> -> <target>; …`.
- Copy rule: directories with `shutil.copytree(item, target, symlinks=True, dirs_exist_ok=True)`; top-level links with `shutil.copy2(item, target, follow_symlinks=False)`; after copying, any link whose target is absolute is rewritten to `os.path.relpath(<realpath mapped into the run's inputs/>, <link's parent>)`, so the run stays self-contained.
- Consumed by: LA3 Task 1 `check_inputs` (calls `find_escaping_links`).

- [x] **Step 1: Write the failing tests** in `tests/test_init_run_symlinks.py` (use `click.testing.CliRunner` and `tmp_path`):

```python
def test_escaping_dir_link_refused(tmp_path):
    outside = tmp_path / "outside"; outside.mkdir(); (outside / "id_rsa").write_text("SECRET")
    inputs = tmp_path / "in"; inputs.mkdir(); (inputs / "plan.md").write_text("x")
    (inputs / "keys").symlink_to(outside, target_is_directory=True)
    r = CliRunner().invoke(main, ["init-run", "r1", "--inputs", str(inputs), "--root", str(tmp_path / "runs")])
    assert r.exit_code == 1 and "keys" in r.output
    assert not (tmp_path / "runs" / "r1").exists()

def test_escaping_file_link_refused(tmp_path): ...  # inputs/key-file -> outside/id_rsa; exit 1; no file under runs/ contains "SECRET"
def test_nested_escaping_link_refused(tmp_path): ...  # inputs/docs/deep -> outside; exit 1; "docs/deep" in output
def test_dangling_outside_link_refused(tmp_path): ...  # link to a missing path outside inputs; exit 1
def test_internal_link_kept_relative(tmp_path):
    # inputs/a.md and inputs/alias.md -> <absolute path of inputs/a.md>
    run = scaffold_run("r2", inputs, ["pbm"], tmp_path / "runs")
    link = run / "inputs" / "alias.md"
    assert link.is_symlink() and not os.path.isabs(os.readlink(link))
    assert link.resolve() == (run / "inputs" / "a.md").resolve()
def test_find_escaping_links_sorted_relative(tmp_path):
    assert find_escaping_links(inputs) == ["b/link", "keys"]
```

- [x] **Step 2:** `pytest tests/test_init_run_symlinks.py -v`. Expected: FAIL (`ImportError: cannot import name 'find_escaping_links'`; the CLI test exits 0).
- [x] **Step 3:** Implement `UnsafeInputsError`, `find_escaping_links` and the copy rule in `init_run.py`; in `init_run_cmd`, catch `UnsafeInputsError` → `click.echo(f"init-run: {e}", err=True)` and `raise SystemExit(1)`.
- [x] **Step 4:** `pytest tests/test_init_run_symlinks.py tests/test_init_run*.py -v` then QG. Expected: PASS; the full suite still passes.
- [x] **Step 5:** Commit: `fix(init-run): refuse input links that point outside the inputs folder`.

### Task 12: Release 1.7.1

**Files:**

- Modify: `pyproject.toml` (`version`), `tools/apd_gauntlet/__init__.py` (`__version__`), `.claude-plugin/plugin.json` (`"version"`), `.claude-plugin/marketplace.json` (the `apd-gauntlet` entry's `"version"`), `tests/test_workflow_apd_gauntlet.py` (`test_plugin_manifest_version_matches_pyproject` literal), `CHANGELOG.md`
- Modify: `docs/QUICKSTART.md:44` and `:200` (not in the lockstep list; they would read 1.7.0)
- Test: `tests/test_workflow_apd_gauntlet.py::test_plugin_manifest_version_matches_pyproject`, `tests/test_check_release_tag.py`

**Interfaces:**

- Consumes: Tasks 1–11 merged on `main`; the compare-runs steps for PR groups A, B, C and E passed (M1 exit gate); PR #27's `tools/check_release_tag.py`.
- Produces: tag `v1.7.1`; PyPI `apd-gauntlet==1.7.1`; plugin `1.7.1`; `FRAMEWORK_VERSION == "1.7.1"`.

- [x] **Step 1: Confirm the preconditions**

Run: `git switch main && git pull && python -c "from apd_gauntlet import FRAMEWORK_VERSION; print(FRAMEWORK_VERSION)" && git switch -c chore/release-1.7.1`
Expected: prints `1.7.0`. Confirm the recorded `compare-runs` results for PR groups A (Task 2), B (Task 4), C (Task 7) and E (Task 10) all exited 0. If any is missing or failing, stop.

The `compare-runs` check: not run: replaced by A8.1's substitute gate; no 1.7.0 live run can exist (A15.1). Amended (register A8.1, as amended by A15.6): `compare-runs` exists on neither line, so the recorded `compare-runs` results for PR groups A, B, C and E are replaced by the 1.7.1 substitute gate: the offline example regression (consolidated plan Task 1.4, Appendix 1: `validate`, `canonicalize`, `build-report`, `audit-report`, `resume-plan` on the three committed examples, each identical to the 1.7.0 engine's output) plus one live run of `examples/apd-20260601-claim-event-bus/inputs` with the `metrics.yaml` comparison (Task 1.5). Keep the 1.7.1 run directory `runs/apd-20261016-ws1-gate` for WS2 (it has no telemetry); no 1.7.0 live run exists (A15.1). A 1.7.1 defect found later ships as 1.7.2. The 1.7.1 substitute gate: the offline regression passed (consolidated Task 1.4); the live run completed clean (Task 1.5 Steps 1–4); its metrics comparison (Step 6) was inconclusive against the 1.4.0-era example (A15.9); 1.7.1 was released on that basis (DEC-1).

- [x] **Step 2: Move the version-floor test first**

Change the literal in `test_plugin_manifest_version_matches_pyproject` to `assert py_version == "1.7.1"`.
Run: `pytest tests/test_workflow_apd_gauntlet.py::test_plugin_manifest_version_matches_pyproject -v`
Expected: FAIL (`pyproject reports '1.7.0'`)

Amended (register A8.2): change the literal at `tests/test_workflow_apd_gauntlet.py` (`assert py_version == "1.7.1", (`) **and** the message on the next line ("expected the 1.7.1 release version"). Also bump `docs/QUICKSTART.md` (`# should print 1.7.1`; `framework_version: 1.7.1`). Done in #51.

- [x] **Step 3: Bump the lockstep places and write the changelog section**

Set `1.7.1` in `pyproject.toml`, `__init__.py`, `plugin.json` and the marketplace entry, and update the QUICKSTART lines to `should print 1.7.1` and `framework_version: 1.7.1`. Then rework `CHANGELOG.md` in two moves:

1. **Housekeeping (1.7.0-era bullets).** Every `[Unreleased]` bullet that was already under `[Unreleased]` at tag `v1.7.0` (check with `git show v1.7.0:CHANGELOG.md`) moves into the existing `## v1.7.0 — 2026-06-09` section. Those are `### Added`: Two-channel distribution; Derived cross-framework views; ATT&CK detection overlay; Compliance projection layer; the per-finding attack-path hop-strip; Deterministic assembler owns all derived ids. And `### Changed`: Agents emit content only. Each one is appended after the existing bullets of the matching v1.7.0 subsection, with its text unchanged.
2. **1.7.1.** Add `## v1.7.1 — YYYY-MM-DD` (the tag date) directly above `## v1.7.0`. Under `### Changed` go PR #27's two bullets ("Two release lines.", "Pre-release engines stamp a release framework version."); under `### Fixed` go every bullet Tasks 2–11 added. `## [Unreleased]` stays as an empty heading.

Amended (register A8.7): New `## v1.7.1 — <date>`, every new bullet ending with its PR number, for example `(#9)`: Added — #7 (Quickstart guide); Changed — PR #27's two bullets, #10 (loader-contract test, `lint-skills`, pinned `claude plugin validate`), #44/#45 (report bundle rebuilt with cytoscape 3.34.3, react 19.3.0, cytoscape-dagre 4.0.1); Fixed — the 12 WS1 bullets and N1 (symlinks) with the WS1 PR number, #8 (plugin `skills` point at directories), #9 (freshness gate: hash parity and rebuild-diff). Move the six "Added" bullets and "Agents emit content only" that were under `[Unreleased]` at tag `v1.7.0` into `## v1.7.0`, and add the never-logged #104 bullet there (W0 `SerializationIntegrityError`, dict `scope` rejection, blocking prephase-5 gate; W1a `infrastructure.{mode,static}` and `manual-audit-prompts`; W1b `repos[]` and the zero-entry warning, ADR-0019; `kb_fetch.fetch_pinned` and `tools/check_kb_cache_freshness.py`). Keep an empty `## [Unreleased]`. Check: the consolidated plan's N2 loop prints nothing.

Done (register A15.8): #51 wrote the `## v1.7.1` CHANGELOG section per A8.7 and N2.

- [x] **Step 4: Run the full gates**

Run: `pytest -q && ruff check tools/ tests/ && mypy tools/ && markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "tools/apd_gauntlet/data/domains/**/*.md" README.md CONTRIBUTING.md CHANGELOG.md CODE_OF_CONDUCT.md`
Expected: all pass; 0 lint errors

- [x] **Step 5: Commit, open the PR against `main`, merge**

```bash
git add pyproject.toml tools/apd_gauntlet/__init__.py .claude-plugin/plugin.json .claude-plugin/marketplace.json tests/test_workflow_apd_gauntlet.py CHANGELOG.md docs/QUICKSTART.md
git commit -m "chore(release): 1.7.1"
```

Expected: CI green on the PR; merged with a merge commit.

Amended (register A8.3): Merge the release PR and push `v1.7.1` in the same session: the 1.7.1 workflow halts on any engine without `resume-plan`, and the marketplace serves `main` HEAD. Done: the release PR is #51, merged after #49 and #50 (register A15.5).

- [x] **Step 6: Tag, check the gate locally, push the tag**

Run: `git switch main && git pull && git tag v1.7.1 <merge-sha> && python tools/check_release_tag.py --tag v1.7.1 && git push origin v1.7.1`
Expected: `release gate: ok — version=1.7.1, prerelease=false, make_latest=true`. The release workflow then publishes 1.7.1 to PyPI and creates a GitHub Release marked Latest.

- [x] **Step 7: Merge `main` into `next`, keeping `next`'s versions**

Run: `git switch next && git pull && git merge --no-ff main`. Resolve conflicts by keeping `next`'s values in the five version places (`2.0.0aN`, plugin `2.0.0-alpha.N`) and in `docs/QUICKSTART.md`. In `CHANGELOG.md`, keep `next`'s `## Unreleased — 2.0 line`, add the `## v1.7.1 — YYYY-MM-DD` section under its own heading, and take `main`'s v1.7.0 housekeeping. Then push.
Expected: CI green on `next`, including `test_plan_run_phase_names_consistent_with_workflow`.

Done in #52 (register A15.7), with A8.4's text as the record: While `next` has no 2.0 pre-release, `git merge --no-ff main` into `next` is conflict-free and takes 1.7.1 in all five version places; keep them. In the same merge commit, reword next's CHANGELOG bullet "Version stays `1.7.0` for now" to "Version tracks the stable line (1.7.1) until the first 2.0 pre-release", and delete the empty `## [Unreleased]` heading that comes from `main`. "Keep next's values" applies only once `2.0.0aN` is on `next`. The 1.7.1 release PR adds that rule to RELEASING.md step 5: "(While `next` has no 2.0 pre-release, take `main`'s version values.)"

---

## Self-review record

- Coverage: defect 1 is covered by Tasks 1–2, 2 by Task 3, 3 by Task 5, 4 by Task 6, 5 by Task 8, 6 by Tasks 9–10, 7 by Task 7; the self-skipping read-only gates by Task 4; the excerpt check by Task 11; the release by Task 12.
- The workflow-editing tasks (2, 3, 4, 5, 10) run in that order, one PR at a time. They keep the existing static pins green. Only three existing tests change: the extended parity test (Task 2), the canonicalize-before-gate test (Task 3) and the version literal (Task 12).
- Names used across tasks: `RESUME_DONE`, `RESUMABLE_STEPS`, `tierGate`, `repairTierGate`, `read_prompt`, `compute_cev_id`, `compute_tm_entry_id`, `context_ids_minted`, `check_excerpts_verbatim`, `excerpt_fragments`, `--strict-excerpts`.
