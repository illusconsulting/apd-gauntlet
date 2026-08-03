# Plugin-Channel Guardrails (PR A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guard the Claude Code plugin channel against the class of bug PR #8 fixed — assert the loader's path-form contract for every manifest array, lint all eight skills' frontmatter uniformly, add `claude plugin validate` as pinned, labeled defense-in-depth, and document the assert-the-contract discipline.

**Architecture:** The plugin manifest lives at `.claude-plugin/plugin.json` (+ `marketplace.json`). Existing tests in `tests/test_plugin_manifest.py` mirror on-disk layout (drift guards). This PR adds a filesystem-aware loader-contract check (the load-bearing guard, since `claude plugin validate` does NOT catch the file-vs-directory skills error — verified empirically), a `lint-skills` CLI mirroring `lint-agents` wired into CI, a pinned CI validate step, and docs.

**Tech Stack:** Python 3.10+, pytest, click (CLI), PyYAML, GitHub Actions, `@anthropic-ai/claude-code` CLI (CI only, pinned 2.0.76).

**Spec:** [docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md](../specs/2026-07-14-guardrail-hardening-post-pr8-design.md) — §"PR A" and §"Amendments (2026-08-02)".

**Supersedes:** the 2026-07-14 amended draft of this plan (kept uncommitted; all content folded in here).

**Base:** `illusconsulting/apd-gauntlet` `main` @ `27270d5`. This checkout is at that commit; every file/line anchor below was re-verified against it on 2026-08-02. All eight skills lint clean today, so the expected-PASS steps hold.

## Global Constraints

- Claude Code loader contract (verified against the code.claude.com plugin reference + empirically 2026-07-14; re-verified 2026-08-02 on CLI 2.0.76): `skills` entries are directories containing `SKILL.md`; `agents` entries are `.md` files; `commands` entries are `.md` files.
- `claude plugin validate` exits 0 on the file-vs-directory skills error (verified 2026-07-14; re-verified 2026-08-02) — it is defense-in-depth only, never the path-form guard.
- `mypy tools/` must stay clean — new `tools/apd_gauntlet/lint_skills.py` is fully typed.
- Follow existing patterns: mirror `tools/apd_gauntlet/lint_agents.py` and the `lint-agents` CLI command (`tools/apd_gauntlet/cli.py` — import at line 22, command at lines 318–332).
- All four gates clean before push: `pytest --cov` (`fail_under = 85` on `tools/apd_gauntlet/`, set in `pyproject.toml:78`), `ruff check tools/ tests/`, `mypy tools/`, and the markdownlint glob (exact command in Task 5; `CONTRIBUTING.md` IS linted).
- Pin CI inputs: GitHub Actions by commit SHA (`actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` v7.0.0; `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020` v7.0.0 — lightweight tag, so that IS the commit), and the CLI as `@anthropic-ai/claude-code@2.0.76` — the version the exits-0 behavior was verified on. Bumps are deliberate, never implicit.
- Branch: `feat/plugin-channel-guardrails` off `main`. Commits use `-s` (DCO).

---

### Task 1: Generalized manifest loader-contract test

**Files:**
- Modify: `tests/test_plugin_manifest.py` (append helper + tests; keep all 6 existing tests)

**Interfaces:**
- Consumes: existing helpers `_manifest()` (line 12), `_norm(p)` (line 16), and module constant `REPO` (line 7).
- Produces: `_loader_contract_errors(m: dict) -> list[str]` (test-local helper) and three tests later steps re-run by name.

- [ ] **Step 1: Write the tests** — append to `tests/test_plugin_manifest.py`:

```python
def _loader_contract_errors(m: dict) -> list[str]:
    """Assert each manifest array matches Claude Code's plugin-LOADER contract.

    Verified against https://code.claude.com/docs/en/plugins-reference and
    empirically (2026-07-14, re-verified 2026-08-02 on CLI 2.0.76):
    `claude plugin validate` exits 0 on the file-vs-directory skills error, so
    this filesystem-aware check — not the CLI — is the load-bearing guard.
    The skills branch deliberately overlaps
    test_skills_entries_are_directories_not_files above, which stays as the
    narrowly-labeled PR #8 regression guard; the new coverage here is the
    agents/commands path-form contract plus the non-vacuity fixtures.
    """
    errors: list[str] = []
    for rel in m.get("skills", []):
        d = REPO / _norm(rel)
        if not d.is_dir() or not (d / "SKILL.md").is_file():
            errors.append(f"skills entry must be a directory containing SKILL.md: {rel}")
    for rel in m.get("agents", []):
        p = REPO / _norm(rel)
        if not (rel.endswith(".md") and p.is_file()):
            errors.append(f"agents entry must be a .md file: {rel}")
    for rel in m.get("commands", []):
        p = REPO / _norm(rel)
        if not (rel.endswith(".md") and p.is_file()):
            errors.append(f"commands entry must be a .md file: {rel}")
    return errors


def test_manifest_satisfies_loader_contract() -> None:
    assert _loader_contract_errors(_manifest()) == []


def test_loader_contract_flags_file_form_skill() -> None:
    """Non-vacuous: the original PR #8 bug (skills -> SKILL.md file) is caught."""
    broken = dict(_manifest())
    broken["skills"] = ["./.claude/skills/apd-framework/SKILL.md"]
    errs = _loader_contract_errors(broken)
    assert any("directory containing SKILL.md" in e for e in errs)


def test_loader_contract_flags_directory_form_agent() -> None:
    """Non-vacuous: an agent entry pointing at a directory is caught."""
    broken = dict(_manifest())
    broken["agents"] = ["./.claude/agents"]
    errs = _loader_contract_errors(broken)
    assert any("agents entry must be a .md file" in e for e in errs)


def test_loader_contract_flags_directory_form_command() -> None:
    """Non-vacuous: a commands entry pointing at a directory is caught."""
    broken = dict(_manifest())
    broken["commands"] = ["./commands"]
    errs = _loader_contract_errors(broken)
    assert any("commands entry must be a .md file" in e for e in errs)
```

- [ ] **Step 2: Run to verify the guard is correct and non-vacuous**

Run: `pytest tests/test_plugin_manifest.py -k loader_contract -v`
Expected: all four PASS. `test_manifest_satisfies_loader_contract` confirms the real manifest is contract-clean (the manifest is already in directory form post-PR #8, so the positive test is green rather than red); the three `flags_*` tests prove the checker actually detects violations in every branch — skills, agents, AND commands — they pass only because the checker returns errors for the broken shapes, so the guard is non-vacuous.

- [ ] **Step 3: Run the full manifest test file**

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: PASS — 10 tests (6 existing + 4 new).

- [ ] **Step 4: Lint + commit**

```bash
ruff check tools/ tests/
git add tests/test_plugin_manifest.py
git commit -s -m "test: assert plugin manifest matches the Claude Code loader path-form contract"
```

---

### Task 2: Uniform skill-frontmatter linter (`lint-skills`) + CI wiring

**Files:**
- Create: `tools/apd_gauntlet/lint_skills.py`
- Modify: `tools/apd_gauntlet/cli.py` (import at line 22 block; command after `lint_agents_cmd`, which ends at line 332)
- Modify: `.github/workflows/markdown-lint.yml` (run `lint-skills` beside `lint-agents` in the `lint-agents` job)
- Test: `tests/test_lint_skills.py` (create)

**Interfaces:**
- Consumes: the `click` `main` group and `pathlib` import already present in `cli.py`; PyYAML (already a dependency).
- Produces: `lint_skill_dir(skill_dir: pathlib.Path) -> list[str]`, `lint_skills_dir(skills_dir: pathlib.Path) -> list[str]`, and CLI command `lint-skills --skill-dir` (default `.claude/skills`, output `Lint clean: N skills checked.` / errors + exit 1).

- [ ] **Step 1: Write the failing test** — create `tests/test_lint_skills.py`:

```python
"""Tests for the lint-skills command and lint_skills helpers."""
from __future__ import annotations

import pathlib

from apd_gauntlet.cli import main
from apd_gauntlet.lint_skills import lint_skill_dir, lint_skills_dir
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_lint_skills_clean_on_real_repo() -> None:
    errors = lint_skills_dir(REPO / ".claude" / "skills")
    assert errors == [], errors


def _write_skill(root: pathlib.Path, dirname: str, frontmatter: str) -> pathlib.Path:
    d = root / dirname
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\nbody\n", encoding="utf-8")
    return d


def test_lint_skills_flags_missing_skill_md(tmp_path) -> None:
    (tmp_path / "foo").mkdir()
    errors = lint_skill_dir(tmp_path / "foo")
    assert any("missing SKILL.md" in e for e in errors)


def test_lint_skills_flags_missing_description(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: foo")
    errors = lint_skill_dir(d)
    assert any("missing 'description'" in e for e in errors)


def test_lint_skills_flags_name_dir_mismatch(tmp_path) -> None:
    d = _write_skill(tmp_path, "foo", "name: bar\ndescription: x")
    errors = lint_skill_dir(d)
    assert any("!= directory" in e for e in errors)


def test_lint_skills_cli_exit_zero_on_real_repo() -> None:
    result = CliRunner().invoke(main, ["lint-skills", "--skill-dir", str(REPO / ".claude/skills")])
    assert result.exit_code == 0, result.output
    assert "Lint clean" in result.output
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_lint_skills.py -v`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'apd_gauntlet.lint_skills'`.

- [ ] **Step 3: Create the linter** — `tools/apd_gauntlet/lint_skills.py`:

```python
"""Lint skill directories for valid frontmatter and name/directory agreement."""
from __future__ import annotations

import pathlib
import re

import yaml

FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def lint_skill_dir(skill_dir: pathlib.Path) -> list[str]:
    """Lint one skill directory. Return error strings; empty list means clean."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    m = FRONTMATTER_PATTERN.match(text)
    if not m:
        return [f"{skill_md}: no YAML frontmatter (missing '---' block at top)"]
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"{skill_md}: frontmatter parse error: {e}"]
    if not isinstance(meta, dict):
        return [f"{skill_md}: frontmatter is not a mapping"]
    errors: list[str] = []
    name = meta.get("name")
    if not name:
        errors.append(f"{skill_md}: frontmatter missing 'name'")
    elif name != skill_dir.name:
        errors.append(
            f"{skill_md}: frontmatter name '{name}' != directory '{skill_dir.name}'"
        )
    if not meta.get("description"):
        errors.append(f"{skill_md}: frontmatter missing 'description'")
    return errors


def lint_skills_dir(skills_dir: pathlib.Path) -> list[str]:
    out: list[str] = []
    for path in sorted(skills_dir.iterdir()):
        if path.is_dir():
            out.extend(lint_skill_dir(path))
    return out
```

- [ ] **Step 4: Register the CLI command** — in `tools/apd_gauntlet/cli.py`, add the import beside line 22 (`from .lint_agents import lint_agents_dir`):

```python
from .lint_skills import lint_skills_dir
```

Then add, immediately after the `lint_agents_cmd` function (ends at line 332, before `@main.command("summarize")` at line 335):

```python
@main.command("lint-skills")
@click.option(
    "--skill-dir",
    type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path),
    default=pathlib.Path(".claude/skills"),
    show_default=True,
)
def lint_skills_cmd(skill_dir) -> None:  # type: ignore[no-untyped-def]
    errors = lint_skills_dir(skill_dir)
    if errors:
        for e in errors:
            click.echo(e)
        raise SystemExit(1)
    n = sum(1 for p in skill_dir.iterdir() if p.is_dir())
    click.echo(f"Lint clean: {n} skills checked.")
```

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/test_lint_skills.py -v`
Expected: PASS — all 5 tests (the real-repo tests pass because all eight skills currently have valid `name`/`description` frontmatter with `name` == directory).

- [ ] **Step 6: Wire the CLI into CI** — in `.github/workflows/markdown-lint.yml`, `lint-agents` job, add immediately after line 32 (`- run: apd-gauntlet lint-agents --agent-dir .claude/agents/`):

```yaml
      - run: apd-gauntlet lint-skills --skill-dir .claude/skills/
```

(The real-repo pytest already exercises the linter in the `python-tests` matrix; this keeps the CLI channels symmetric with `lint-agents`.)

- [ ] **Step 7: Lint + commit**

```bash
ruff check tools/ tests/
mypy tools/
git add tools/apd_gauntlet/lint_skills.py tools/apd_gauntlet/cli.py tests/test_lint_skills.py .github/workflows/markdown-lint.yml
git commit -s -m "feat: add lint-skills to validate all skill frontmatter uniformly"
```

---

### Task 3: `claude plugin validate` CI step (defense-in-depth, labeled, pinned)

**Files:**
- Modify: `.github/workflows/validate.yml` (append a `plugin-manifest` job under `jobs:`)

**Interfaces:**
- Consumes: the `@anthropic-ai/claude-code` npm package (provides the `claude` CLI), pinned to 2.0.76 per Global Constraints.
- Produces: CI job `plugin-manifest` that validates both manifests.

- [ ] **Step 1: Add the CI job** — append to `.github/workflows/validate.yml` under `jobs:`:

```yaml
  plugin-manifest:
    # Defense-in-depth: catches malformed manifest JSON / missing required
    # fields. Does NOT catch the skills file-vs-directory error (verified on
    # CLI 2.0.76: it exits 0 on that) — the load-bearing guard for the
    # path-form class is
    # tests/test_plugin_manifest.py::test_manifest_satisfies_loader_contract.
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0  # v7.0.0
      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020  # v7.0.0
        with: { node-version: "20" }
      # Pinned to the CLI version the exits-0-on-path-form behavior was
      # verified on (2026-07-14, re-verified 2026-08-02). Bump deliberately.
      - run: npm install -g @anthropic-ai/claude-code@2.0.76
      - run: claude --version
      - run: claude plugin validate .claude-plugin/plugin.json
      - run: claude plugin validate .claude-plugin/marketplace.json
```

- [ ] **Step 2: Verify the invocations locally**

Run:

```bash
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

Expected: both print `✔ Validation passed` (exit 0). The second prints `Validating marketplace manifest:` — the CLI validates a `marketplace.json` target as a marketplace manifest.

- [ ] **Step 3: Validate the workflow YAML**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/validate.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/validate.yml
git commit -s -m "ci: run claude plugin validate on the manifests (defense-in-depth, pinned)"
```

---

### Task 4: Documentation + `$schema` pointers

**Files:**
- Modify: `CONTRIBUTING.md` (insert after line 42, the sentence `The CI workflows enforce these gates on every PR.` that closes the `## Testing` list)
- Modify: `.github/PULL_REQUEST_TEMPLATE.md` (insert after line 22, the DCO checklist line)
- Modify: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (add `$schema` as the first key)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: contributor docs; editor-validated manifests.

- [ ] **Step 1: Add plugin-channel guidance to `CONTRIBUTING.md`** — insert after line 42 (`The CI workflows enforce these gates on every PR.`):

```markdown

### Plugin channel

If you change anything under `.claude/` or `.claude-plugin/`, a green `pytest`
does not prove the plugin loads. Run `claude plugin validate
.claude-plugin/plugin.json` and confirm `/doctor` is clean in Claude Code.

Guardrails that protect an external contract — the Claude Code loader, a
schema, a consumer's file format — must assert that contract from its
authoritative spec, not mirror the current repo state. A test that reflects
whatever shape is already present only catches drift between two copies of the
same possibly-wrong thing (this is why the pre-PR-#8 skills test stayed green
while every skill failed to load).
```

- [ ] **Step 2: Add a PR-template checklist line** — in `.github/PULL_REQUEST_TEMPLATE.md`, insert after line 22 (the DCO sign-off checklist line):

```markdown
- [ ] Plugin/`.claude` changes: `claude plugin validate .claude-plugin/plugin.json` clean and `/doctor` loads all skills
```

- [ ] **Step 3: Add `$schema` to the manifests** — insert as the FIRST key of `.claude-plugin/plugin.json` (before `"name"`):

```json
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
```

and as the FIRST key of `.claude-plugin/marketplace.json`:

```json
  "$schema": "https://json.schemastore.org/claude-code-marketplace.json",
```

(SchemaStore catalog names verified 2026-08-02: plugin manifest = `claude-code-plugin-manifest.json` (200), marketplace = `claude-code-marketplace.json` (200, "Claude Code Plugin Marketplace"). The `claude-code-plugin-marketplace.json` form 404s — do not use it.)

- [ ] **Step 4: Verify `$schema` does not break validation or tests**

Run:

```bash
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
pytest tests/test_plugin_manifest.py -v
```

Expected: both validations pass; all 10 manifest tests pass. If `claude plugin validate` errors or warns specifically about the `$schema` key, REMOVE both `$schema` additions (editor-only nicety; not worth a validation regression) and note it in the PR description.

- [ ] **Step 5: Run markdownlint on the touched docs**

Run:

```bash
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "tools/apd_gauntlet/data/domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: `0 error(s)`.

- [ ] **Step 6: Commit**

```bash
git add CONTRIBUTING.md .github/PULL_REQUEST_TEMPLATE.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -s -m "docs: document the plugin-channel verify step and the assert-the-contract principle"
```

---

### Task 5: PR wrap-up

**Files:** commit the design docs to the branch; no code changes.

- [ ] **Step 1: Commit the spec and this plan to the branch**

```bash
git add docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md docs/superpowers/plans/2026-08-02-plugin-channel-guardrails.md
git commit -s -m "docs: add the guardrail-hardening spec and the PR A implementation plan"
```

(The spec lints clean — verified 2026-08-02, 0 markdownlint issues — and `docs/superpowers/plans/**` is excluded from the lint glob. PR B commits the identical spec file on its own branch; identical-content adds merge without conflict. The superseded 2026-07-14 drafts stay uncommitted — commit or discard at the maintainer's discretion.)

- [ ] **Step 2: Run all four gates**

```bash
pytest --cov --cov-report=term-missing
ruff check tools/ tests/
mypy tools/
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "tools/apd_gauntlet/data/domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: all clean (coverage `fail_under = 85` enforced by `pyproject.toml`).

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin feat/plugin-channel-guardrails
gh pr create --repo illusconsulting/apd-gauntlet --base main \
  --title "Plugin-channel guardrails: loader-contract test, lint-skills, pinned validate CI" \
  --body "See docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md (PR A + Amendments)."
```
