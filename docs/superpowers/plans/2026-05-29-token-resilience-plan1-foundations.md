# Token-Resilience Plan 1 — Foundations (A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the behavioral hardening layer — quieter/scoped validation, a canonical agent-receipt contract, and specialist output bounding — so a full gauntlet run leaks far less context into its driver, with zero dependency on the future Workflow runner.

**Architecture:** Three independent, immediately-shippable changes: (1) add `--errors-only` and `--tier` flags to the existing `apd-gauntlet validate` command so tier-end checks emit compact, run-scoped output; (2) add a `schemas/agent-receipt.schema.json` and a lint rule that requires every dispatched agent `.md` to declare a "final message = receipt only" contract; (3) add a soft-cap / no-silent-truncation / relevance-table clause to the nine specialist agents. All three are covered by `pytest` against the existing fixtures.

**Tech Stack:** Python 3.10+, `click` (CLI), `jsonschema` (Draft 2020-12), `pytest` + `click.testing.CliRunner`, `ruff`, `mypy`. Source under `tools/apd_gauntlet/`; tests under `tests/`.

**Reference:** Design doc at `docs/superpowers/specs/2026-05-29-apd-token-resilience-design.md` (§5 receipt contract, §8 output bounding, §9 CLI changes). This is Plan 1 of 3 (Plan 2 = synthesis decomposition, Plan 3 = Workflow runner).

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/cli.py` | `validate` command — add `--errors-only`, `--tier` | Modify (`validate` fn, ~line 46–95) |
| `tools/apd_gauntlet/lint_agents.py` | add receipt-contract + bounding-clause checks | Modify |
| `schemas/agent-receipt.schema.json` | canonical receipt structure consumed by Plan 3's runner | Create |
| `.claude/agents/*.md` (13 dispatched agents) | add "Final message" receipt section; specialists also add bounding section | Modify |
| `tests/test_validate_errors_only.py` | cover `--errors-only` | Create |
| `tests/test_validate_tier.py` | cover `--tier` scoping | Create |
| `tests/test_agent_receipt_schema.py` | cover receipt schema content | Create |
| `tests/test_lint_agents_receipt.py` | cover lint receipt + bounding rules | Create |

**Dispatched-agent set** (must carry the receipt contract; `apd-orchestrator.md` is exempt — it is being retired in Plan 3, and `apd-synthesizer.md` is exempt as it returns its own run-status, not a parent receipt):

```
apd-intake, apd-code-recon, apd-threat-model-recon,
apd-confidentiality, apd-integrity, apd-availability,
apd-distributed, apd-resilient, apd-ephemeral,
apd-authenticity, apd-non-repudiation, apd-immutability,
apd-attack-path-analyzer, apd-threat-model-evaluator
```

That is 14 files. The nine specialists (confidentiality, integrity, availability, distributed, resilient, ephemeral, authenticity, non-repudiation, immutability) ALSO carry the output-bounding section (Task 5).

---

## Task 1: `validate --errors-only` flag

**Files:**
- Modify: `tools/apd_gauntlet/cli.py` (the `validate` command, ~line 46–95)
- Test: `tests/test_validate_errors_only.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_validate_errors_only.py`:

```python
"""--errors-only: suppress warnings + the scan/clean summary line; print only ERROR lines."""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_errors_only_clean_run_is_silent(tmp_path):
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--errors-only"])
    assert result.exit_code == 0
    # No "Files scanned" summary, no "Clean." line — completely quiet on success.
    assert result.output.strip() == ""


def test_errors_only_prints_errors_but_not_summary(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Inject a schema error: blank out a required field on a finding.
    f = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = f.read_text()
    text = text.replace("severity:", "not_severity:", 1)
    f.write_text(text)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--errors-only"])
    assert result.exit_code == 1
    assert "ERROR" in result.output
    assert "Files scanned" not in result.output
    assert "WARNING" not in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validate_errors_only.py -v`
Expected: FAIL — `--errors-only` is an unknown option (exit_code 2, "no such option"), so the silence/assertions fail.

- [ ] **Step 3: Add the flag and output branch**

In `tools/apd_gauntlet/cli.py`, add a new option decorator immediately below the existing `--json` decorator on the `validate` command:

```python
@click.option(
    "--errors-only",
    is_flag=True,
    help="Print only ERROR lines; suppress warnings and the scan/clean summary line.",
)
```

Add `errors_only` to the function signature (after `as_json`):

```python
def validate(run_dir, schema_only, strict, as_json, errors_only) -> None:  # type: ignore[no-untyped-def]
```

Replace the final output block (currently `else: click.echo(merged.render())`) so the JSON branch is unchanged and a new `elif` is inserted:

```python
    if as_json:
        # ...unchanged JSON serialization...
        click.echo(_json.dumps({ ... }, indent=2))
    elif errors_only:
        if merged.errors:
            click.echo("\n".join(f"ERROR   {v.render()}" for v in merged.errors))
    else:
        click.echo(merged.render())
    raise SystemExit(0 if merged.is_clean else 1)
```

(Keep the existing JSON body exactly as-is; only the `elif errors_only:` branch is new.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validate_errors_only.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_validate_errors_only.py
git commit -m "feat(validate): --errors-only flag for compact tier-end output"
```

---

## Task 2: `validate --tier <subdir>` scoping

**Files:**
- Modify: `tools/apd_gauntlet/cli.py` (the `validate` command)
- Test: `tests/test_validate_tier.py`

**Why this works:** `run_schema_pass(target)` and `run_semantic_pass(target)` both discover records via `_iter_records(target)` → `target.rglob(glob)`, and the schema pass's rollup checks (`_validate_context_rollups`, `_validate_synthesis_rollups`) early-return when `00-context/`/`40-synthesis/` are absent under `target`. So passing `run_dir / tier` as the scan root validates only that tier's `*.findings.yaml` / `*.capabilities.yaml`. The cross-file pass (Pass 3) spans the whole run and is skipped under `--tier`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_validate_tier.py`:

```python
"""--tier: validate only one subdir; skip the cross-file pass; tolerate later tiers absent."""
from __future__ import annotations

import pathlib
import shutil

from apd_gauntlet.cli import main
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def _copy_clean_run(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    return dst


def test_tier_scopes_to_subdir(tmp_path):
    dst = _copy_clean_run(tmp_path)
    # Break a record in tier-2; validate tier-1 only — should stay clean.
    f2 = dst / "20-scalability" / "distributed.findings.yaml"
    if f2.exists():
        f2.write_text(f2.read_text().replace("severity:", "not_severity:", 1))
    runner = CliRunner()
    result = runner.invoke(
        main, ["validate", str(dst), "--tier", "10-trustworthiness", "--errors-only"]
    )
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_tier_catches_error_in_scoped_dir(tmp_path):
    dst = _copy_clean_run(tmp_path)
    f1 = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    f1.write_text(f1.read_text().replace("severity:", "not_severity:", 1))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--tier", "10-trustworthiness"])
    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_tier_missing_subdir_errors_cleanly(tmp_path):
    dst = _copy_clean_run(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst), "--tier", "99-nope"])
    assert result.exit_code != 0
    assert "99-nope" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_validate_tier.py -v`
Expected: FAIL — `--tier` is an unknown option.

- [ ] **Step 3: Add the option and scoping logic**

Add the option decorator below `--errors-only`:

```python
@click.option(
    "--tier",
    default=None,
    help="Validate only this run subdir (e.g. 10-trustworthiness); skips the cross-file pass.",
)
```

Update the signature: `def validate(run_dir, schema_only, strict, as_json, errors_only, tier) -> None:`

Replace the head of the function body (the part that builds `merged`) with this complete form (cross-file is skipped when `tier` is set):

```python
def validate(run_dir, schema_only, strict, as_json, errors_only, tier) -> None:  # type: ignore[no-untyped-def]
    target = run_dir / tier if tier else run_dir
    if tier and not target.is_dir():
        raise click.ClickException(f"--tier subdir not found: {target}")

    schema_rep = run_schema_pass(target)
    if schema_only:
        merged = schema_rep
    elif tier:
        semantic_rep = run_semantic_pass(target)
        merged = ValidationReport(
            errors=schema_rep.errors + semantic_rep.errors,
            warnings=schema_rep.warnings + semantic_rep.warnings,
            files_seen=max(schema_rep.files_seen, semantic_rep.files_seen),
            records_seen=schema_rep.records_seen,
        )
    else:
        semantic_rep = run_semantic_pass(target)
        cross_file_rep = run_cross_file_pass(target)
        merged = ValidationReport(
            errors=schema_rep.errors + semantic_rep.errors + cross_file_rep.errors,
            warnings=schema_rep.warnings + semantic_rep.warnings + cross_file_rep.warnings,
            files_seen=max(
                schema_rep.files_seen, semantic_rep.files_seen, cross_file_rep.files_seen
            ),
            records_seen=schema_rep.records_seen,
        )
    # ...strict / as_json / errors-only / else output block unchanged from Task 1...
```

Confirm `ValidationReport` is imported in `cli.py` (it is used in the existing body via the local `from .validate import Violation`). If `ValidationReport` is not already importable in scope, add it to the existing import line: `from .validate import ValidationReport, Violation as _Violation` — check the top of the function; the original code already constructs `ValidationReport(...)`, so the name is in scope. No new import needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_validate_tier.py tests/test_validate_errors_only.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Run the full validate test suite for regressions**

Run: `python -m pytest tests/test_validate_schema_pass.py tests/test_validate_semantic.py tests/test_validate_cross_file.py tests/test_validate_edge_cases.py tests/test_cli.py -q`
Expected: PASS (no regressions — default behavior unchanged)

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_validate_tier.py
git commit -m "feat(validate): --tier scopes validation to one tier, skips cross-file pass"
```

---

## Task 3: `agent-receipt.schema.json`

**Files:**
- Create: `schemas/agent-receipt.schema.json`
- Test: `tests/test_agent_receipt_schema.py` (content); `tests/test_meta_schemas.py` already covers meta-validity via its glob.

- [ ] **Step 1: Write the failing test**

Create `tests/test_agent_receipt_schema.py`:

```python
"""The agent-receipt schema accepts a minimal valid receipt and rejects prose/extra keys."""
from __future__ import annotations

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_valid_receipt():
    receipt = {
        "agent": "apd-confidentiality",
        "status": "ok",
        "outputs": [
            {"path": "10-trustworthiness/confidentiality.findings.yaml", "schema_valid": True}
        ],
        "counts": {"findings_by_severity": {"high": 2}, "blocked": 0},
    }
    assert list(_validator().iter_errors(receipt)) == []


def test_rejects_unknown_top_level_key():
    receipt = {
        "agent": "apd-confidentiality",
        "status": "ok",
        "outputs": [],
        "counts": {},
        "summary_prose": "Here is a long narrative the driver should never receive.",
    }
    assert list(_validator().iter_errors(receipt))  # additionalProperties: false


def test_rejects_bad_status():
    receipt = {"agent": "x", "status": "done", "outputs": [], "counts": {}}
    assert list(_validator().iter_errors(receipt))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agent_receipt_schema.py -v`
Expected: FAIL — `schemas/agent-receipt.schema.json` does not exist (FileNotFoundError).

- [ ] **Step 3: Create the schema**

Create `schemas/agent-receipt.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/agent-receipt.schema.json",
  "title": "APD agent receipt",
  "description": "Compact structured value a dispatched APD agent emits as its FINAL MESSAGE instead of prose. The run driver retains only this — never finding/capability content.",
  "type": "object",
  "additionalProperties": false,
  "required": ["agent", "status", "outputs", "counts"],
  "properties": {
    "agent": { "type": "string", "minLength": 1 },
    "status": { "enum": ["ok", "blocked", "error"] },
    "outputs": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["path", "schema_valid"],
        "properties": {
          "path": { "type": "string", "minLength": 1 },
          "schema_valid": { "type": "boolean" }
        }
      }
    },
    "counts": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "findings_by_severity": { "type": "object" },
        "capabilities_by_maturity": { "type": "object" },
        "blocked": { "type": "integer", "minimum": 0 }
      }
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["path", "message"],
        "properties": {
          "path": { "type": "string" },
          "message": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agent_receipt_schema.py "tests/test_meta_schemas.py" -v`
Expected: PASS — including `test_schema_is_valid_meta[agent-receipt.schema.json]` (picked up automatically by the glob).

- [ ] **Step 5: Commit**

```bash
git add schemas/agent-receipt.schema.json tests/test_agent_receipt_schema.py
git commit -m "feat(schema): canonical agent-receipt schema (compact agent return contract)"
```

---

## Task 4: Receipt-contract clause — lint rule + agent files

**Files:**
- Modify: `tools/apd_gauntlet/lint_agents.py`
- Modify: the 14 dispatched-agent `.md` files (see set in File Structure)
- Test: `tests/test_lint_agents_receipt.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_lint_agents_receipt.py`:

```python
"""Every dispatched agent must declare the receipt contract; orchestrator/synthesizer exempt."""
from __future__ import annotations

import pathlib

from apd_gauntlet.lint_agents import lint_agent_file

REPO = pathlib.Path(__file__).parent.parent
AGENTS = REPO / ".claude" / "agents"

RECEIPT_MARKER = "## Final message"


def test_specialist_missing_receipt_is_flagged(tmp_path):
    agent = tmp_path / "apd-fake-specialist.md"
    agent.write_text(
        "---\nname: apd-fake-specialist\ndescription: x\n---\n\n"
        "# Fake\n\n## Output\n\nWrites foo.findings.yaml\n"
    )
    errors = lint_agent_file(agent, tmp_path)
    assert any("receipt" in e.lower() or "final message" in e.lower() for e in errors)


def test_orchestrator_is_exempt(tmp_path):
    agent = tmp_path / "apd-orchestrator.md"
    agent.write_text("---\nname: apd-orchestrator\ndescription: x\n---\n\n# Orchestrator\n")
    errors = lint_agent_file(agent, tmp_path)
    assert not any("receipt" in e.lower() or "final message" in e.lower() for e in errors)


def test_real_dispatched_agents_all_carry_receipt_contract():
    dispatched = [
        "apd-intake", "apd-code-recon", "apd-threat-model-recon",
        "apd-confidentiality", "apd-integrity", "apd-availability",
        "apd-distributed", "apd-resilient", "apd-ephemeral",
        "apd-authenticity", "apd-non-repudiation", "apd-immutability",
        "apd-attack-path-analyzer", "apd-threat-model-evaluator",
    ]
    for name in dispatched:
        text = (AGENTS / f"{name}.md").read_text()
        assert RECEIPT_MARKER in text, f"{name}.md missing receipt contract section"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_lint_agents_receipt.py -v`
Expected: FAIL — lint has no receipt rule (first test fails) and real agents lack the marker (third test fails).

- [ ] **Step 3: Add the lint rule**

In `tools/apd_gauntlet/lint_agents.py`, add a module-level constant and extend `lint_agent_file`. Add near the top after the existing patterns:

```python
RECEIPT_MARKER = "## Final message"
# Agents NOT dispatched as receipt-returning children of the run driver.
RECEIPT_EXEMPT = {"apd-orchestrator", "apd-synthesizer"}
```

Inside `lint_agent_file`, after the frontmatter `name`/`description` checks and before the Required-reading block, add:

```python
    name = meta.get("name", path.stem)
    if name not in RECEIPT_EXEMPT and RECEIPT_MARKER not in text:
        errors.append(
            f"{path}: missing receipt contract section (expected a '{RECEIPT_MARKER}' heading)"
        )
```

- [ ] **Step 4: Add the receipt section to each dispatched agent**

Append this exact block to the END of each of the 14 dispatched-agent `.md` files listed in File Structure. The wording is identical across all of them (DRY: lint checks for the stable `## Final message` marker):

```markdown
## Final message (receipt only)

Your final message back to the run driver is a **receipt, not prose**. Do NOT
restate findings, capabilities, or analysis — those live in the files you wrote.
Return only a compact object conforming to `schemas/agent-receipt.schema.json`:

```yaml
agent: <your name>
status: ok | blocked | error
outputs:
  - path: <relative path you wrote>
    schema_valid: true
counts:
  findings_by_severity: { critical: 0, high: 0, medium: 0, low: 0, informational: 0 }
  capabilities_by_maturity: { designed: 0, implemented: 0, tested: 0, operationalized: 0 }
  blocked: 0
errors: []   # populate only on status: error
```

Omit `counts` keys that do not apply to your agent (e.g. recon agents that emit
no findings). The driver retains only this receipt; keeping it small is what
keeps the run within context.
```

(Agents that emit no findings/capabilities — `apd-code-recon`, `apd-threat-model-recon` — keep the section but their `counts` may be `{}`; the schema allows it.)

- [ ] **Step 5: Run tests + lint to verify they pass**

Run: `python -m pytest tests/test_lint_agents_receipt.py tests/test_lint_agents.py -v`
Expected: PASS (all)

Run: `python -m pytest tests/test_orchestrator_topology.py -q`
Expected: PASS (the topology test still recognizes all agents)

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/lint_agents.py tests/test_lint_agents_receipt.py .claude/agents/
git commit -m "feat(agents): receipt-only final-message contract + lint enforcement"
```

---

## Task 5: Specialist output-bounding clause

**Files:**
- Modify: the 9 specialist `.md` files (confidentiality, integrity, availability, distributed, resilient, ephemeral, authenticity, non-repudiation, immutability)
- Modify: `tools/apd_gauntlet/lint_agents.py`
- Test: `tests/test_lint_agents_bounding.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_lint_agents_bounding.py`:

```python
"""The nine specialists must declare output bounding (soft cap + no-silent-truncation)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).parent.parent
AGENTS = REPO / ".claude" / "agents"
BOUNDING_MARKER = "## Output bounding"

SPECIALISTS = [
    "apd-confidentiality", "apd-integrity", "apd-availability",
    "apd-distributed", "apd-resilient", "apd-ephemeral",
    "apd-authenticity", "apd-non-repudiation", "apd-immutability",
]


def test_all_specialists_carry_output_bounding():
    for name in SPECIALISTS:
        text = (AGENTS / f"{name}.md").read_text()
        assert BOUNDING_MARKER in text, f"{name}.md missing output-bounding section"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_lint_agents_bounding.py -v`
Expected: FAIL — no specialist has the `## Output bounding` marker.

- [ ] **Step 3: Append the bounding section to each of the nine specialists**

Append this exact block to the END of each of the nine specialist `.md` files:

```markdown
## Output bounding

To stay within your own context window on a large subject:

- **Honor the relevance table.** Read only the artifacts the intake brief marks
  `primary` or `secondary` for your lens. Do not read all of `inputs/`.
- **Soft cap, never silent.** If you would emit more than ~15 findings of a single
  severity, emit the most material ones and add ONE explicit finding titled
  "Additional <lens> findings truncated" that states how many were omitted and
  recommends a re-run with a component focus hint. Silent truncation is forbidden
  by the evidence-discipline rules — an omission the reviewer cannot see is worse
  than a visible cap.
- **Write incrementally.** Prefer appending records to your output file as you
  confirm them over composing the entire file in context and writing once.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_lint_agents_bounding.py -v`
Expected: PASS

- [ ] **Step 5: (Optional) lint enforcement**

If you want the bounding clause lint-enforced like the receipt clause, in
`tools/apd_gauntlet/lint_agents.py` add:

```python
BOUNDING_MARKER = "## Output bounding"
SPECIALIST_NAMES = {
    "apd-confidentiality", "apd-integrity", "apd-availability",
    "apd-distributed", "apd-resilient", "apd-ephemeral",
    "apd-authenticity", "apd-non-repudiation", "apd-immutability",
}
```

and inside `lint_agent_file`, after the receipt check:

```python
    if name in SPECIALIST_NAMES and BOUNDING_MARKER not in text:
        errors.append(
            f"{path}: specialist missing output-bounding section "
            f"(expected a '{BOUNDING_MARKER}' heading)"
        )
```

Run: `python -m pytest tests/test_lint_agents.py tests/test_lint_agents_bounding.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/ tools/apd_gauntlet/lint_agents.py tests/test_lint_agents_bounding.py
git commit -m "feat(agents): specialist output-bounding clause (relevance table + no-silent caps)"
```

---

## Task 6: Full regression + lint/type gate

**Files:** none (verification only)

- [ ] **Step 1: Run the whole suite**

Run: `python -m pytest -q`
Expected: PASS (all green; no regressions in validate, lint, schema, or report suites)

- [ ] **Step 2: Lint + type check**

Run: `ruff check tools/ tests/ && mypy tools/apd_gauntlet`
Expected: clean (no new errors introduced)

- [ ] **Step 3: Smoke-test the new CLI surface on a real run**

Run: `apd-gauntlet validate runs/apd-20260527-authentik-identity-provider --tier 10-trustworthiness --errors-only`
Expected: exit 0 and no output (the committed run is clean for that tier), confirming the compact/scoped path works end-to-end.

- [ ] **Step 4: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "test: token-resilience Plan 1 regression gate green"
```

---

## Self-Review

**Spec coverage (vs design doc §5, §8, §9):**
- §9 `validate --errors-only` → Task 1 ✓
- §9 `validate --tier` → Task 2 ✓
- §5 receipt contract (schema) → Task 3 ✓
- §5 receipt contract (every dispatched agent declares it; driver retains only receipt) → Task 4 ✓ (lint-enforced)
- §8 specialist output bounding (relevance table + no-silent caps + incremental write) → Task 5 ✓
- Regression/lint/type gate → Task 6 ✓
- Out of Plan-1 scope (correctly deferred): `cluster-candidates`/`apply-clusters`/`rollup`/`audit-report` (Plan 2), the Workflow runner + resume + synthesizer fallback (Plan 3). The receipt schema is created here but its *consumer* (the runner) lands in Plan 3 — intentional; the schema + agent contracts must exist first.

**Placeholder scan:** No "TBD/TODO/handle edge cases". Task 5 Step 5 is explicitly marked optional, not a placeholder. The `--errors-only`/`--json` "unchanged" references point at concrete existing code shown in the design doc and the task; the full final function is given in Task 2 Step 3.

**Type/name consistency:** `RECEIPT_MARKER` (`## Final message`) is identical in lint_agents.py (Task 4 Step 3) and the test (Task 4 Step 1) and the appended agent block (Task 4 Step 4). `BOUNDING_MARKER` (`## Output bounding`) is identical across Task 5 Steps 1/3/5. `RECEIPT_EXEMPT` = {orchestrator, synthesizer} matches the dispatched-agent set (14) and the exemption test. `ValidationReport` / `Violation.render()` / `run_schema_pass` / `run_semantic_pass` / `run_cross_file_pass` signatures match the real `validate.py`. Schema `$id` matches the repo convention (`https://github.com/shoveleejoe/apd-gauntlet/schemas/<name>.schema.json`).
