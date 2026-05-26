# APD Gauntlet v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a production-ready v1.0 open-source release of the APD Gauntlet — a multi-agent security architecture review framework with machine-enforced schemas, a Python validator CLI, pluggable domain packs (PBM bundled), a CI-validated sample run, and a Claude Code plugin manifest.

**Architecture:** Mono-repo with a `.claude/` plugin payload (agents + skills), `schemas/` (JSON Schema draft 2020-12), `domains/<name>/` packs assembled at build time into a generated `apd-domain/SKILL.md`, a Python validator package under `tools/apd_gauntlet/` installed as the `apd-gauntlet` CLI, an `examples/` integration test, and GitHub Actions CI. Layered foundation-first build: schemas first, validator next, agents and domain pack on top, then sample run, then distribution.

**Tech Stack:** Python ≥ 3.10 (validator); `jsonschema`, `pyyaml`, `click`, `rich` (runtime); `pytest`, `pytest-cov`, `ruff`, `mypy` (dev); GitHub Actions (CI); Apache-2.0.

**Reference:** Approved design spec at `docs/superpowers/specs/2026-05-24-apd-gauntlet-v1-design.md`. Engineers should keep it open while executing — this plan is the *how*; the spec is the *why* and the contract.

---

## File Structure Map

The full v1.0 layout is documented in spec §4. Reproduced here for quick reference; each task below cites which file(s) it produces or modifies.

```
apd-gauntlet/                                 (repo root, current working dir)
├── README.md                                 # M7
├── LICENSE                                   # M1 (Apache-2.0)
├── CONTRIBUTING.md                           # M7
├── CHANGELOG.md                              # M7
├── CODE_OF_CONDUCT.md                        # M7
├── plugin.json                               # M7
├── pyproject.toml                            # M1 skeleton, M3 entry point
├── .gitignore                                # M1
├── .claude/agents/                           # M4 (moved from 9-agent-apd-framework/)
├── .claude/skills/apd-framework/SKILL.md     # M4
├── .claude/skills/apd-finding-schema/SKILL.md         # M4
├── .claude/skills/apd-evidence-discipline/SKILL.md    # M4 (PBM rubric removed)
├── .claude/skills/apd-control-mappings/SKILL.md       # M4
├── .claude/skills/apd-domain/SKILL.md        # M5 (generated)
├── domains/pbm/domain.yaml                   # M5
├── domains/pbm/severity-rubric.md            # M5 (extracted from evidence-discipline)
├── domains/pbm/consequential-actions.md      # M5
├── domains/pbm/immutability-classes.md       # M5
├── domains/pbm/data-taxonomy.md              # M5
├── domains/pbm/common-patterns/<goal>.md     # M5 × 9 files
├── schemas/*.schema.json                     # M2 × 8 files
├── templates/*.{yaml,md}                     # M1 move + M4 schema_version updates
├── tools/apd_gauntlet/{cli,validate,init_run,build_domain_skill,summary,linters}.py  # M3
├── tools/apd_gauntlet/data/mitre-mitigations.json    # M3
├── tests/test_*.py + fixtures/               # M2 fixtures, M3 tests, M6 integration
├── examples/apd-20260601-claim-event-bus/    # M6
├── docs/architecture.md + ...                # M7
├── docs/adrs/0001…0006.md                    # M7
└── .github/workflows/*.yml + templates/      # M7
```

---

## Milestone Overview

| # | Milestone | Output | Depends on |
|---|---|---|---|
| **M1** | Scaffolding | Directory layout, root files, file migration from current flat state | — |
| **M2** | Schemas | 8 JSON Schema files + positive/negative fixtures, meta-validated | M1 |
| **M3** | Validator | `apd-gauntlet` CLI installed, all 8 subcommands, pytest at ≥85% coverage | M2 |
| **M4** | Agent refactor | Agents + skills in `.claude/`, contract fixes applied, PBM content extracted | M2 |
| **M5** | Domain pack | `domains/pbm/` populated, `apd-domain/SKILL.md` build verified end-to-end | M3, M4 |
| **M6** | Sample run | Synthetic PBM run with curated expected outputs, CI integration test | M5 |
| **M7** | Plugin + CI + docs | `plugin.json`, 4 CI workflows, 6 ADRs, doc pages, README rewrite, v1.0.0 tag | M6 |

---

# M1 — Scaffolding

Goal: establish the v1.0 directory layout, root-level files, and move existing content out of the legacy flat `9-agent-apd-framework/` layout. After M1, the repo has the shape of the v1.0 spec but no schemas, validator, or refactored content yet.

### Task 1.1: Create root-level configuration files

**Files:**

- Create: `LICENSE`
- Create: `.gitignore`
- Create: `pyproject.toml` (skeleton)

- [ ] **Step 1: Fetch the Apache-2.0 license text**

Run: `curl -fsSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE`
Expected: file `LICENSE` created with Apache-2.0 boilerplate (~11 KB).

- [ ] **Step 2: Verify the LICENSE file contents**

Run: `head -3 LICENSE`
Expected: `Apache License`, `Version 2.0, January 2004`, `http://www.apache.org/licenses/`.

- [ ] **Step 3: Write `.gitignore`**

Create `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/

# Editors / OS
.DS_Store
.idea/
.vscode/
*.swp
*~

# Virtualenvs
.venv/
venv/
env/

# Run outputs (gauntlet runs)
runs/
```

- [ ] **Step 4: Write skeleton `pyproject.toml`**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "apd-gauntlet"
version = "1.0.0"
description = "APD security architecture review framework — 9 specialist agents plus intake, orchestrator, and synthesizer."
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.10"
authors = [{ name = "APD Gauntlet contributors" }]
keywords = ["security", "architecture", "review", "claude-code", "apd"]
classifiers = [
  "Development Status :: 4 - Beta",
  "License :: OSI Approved :: Apache Software License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Security",
]
dependencies = [
  "jsonschema>=4.20",
  "pyyaml>=6.0",
  "click>=8.1",
  "rich>=13.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=4.1",
  "ruff>=0.5",
  "mypy>=1.10",
  "types-PyYAML",
]

[project.scripts]
apd-gauntlet = "apd_gauntlet.cli:main"

[project.urls]
Repository = "https://github.com/shoveleejoe/apd-gauntlet"
Issues     = "https://github.com/shoveleejoe/apd-gauntlet/issues"

[tool.setuptools.packages.find]
where = ["tools"]
include = ["apd_gauntlet*"]

[tool.setuptools.package-data]
apd_gauntlet = ["data/*.json"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"

[tool.coverage.run]
source = ["tools/apd_gauntlet"]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = false
fail_under = 85

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "C4"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_unused_ignores = true
files = ["tools/apd_gauntlet"]
```

- [ ] **Step 5: Commit**

```bash
git add LICENSE .gitignore pyproject.toml
git commit -m "M1: add Apache-2.0 LICENSE, .gitignore, pyproject.toml skeleton"
```

---

### Task 1.2: Create the v1.0 directory skeleton

**Files:** Directory creation only.

- [ ] **Step 1: Create the empty directory tree**

Run:

```bash
mkdir -p \
  .claude/agents \
  .claude/skills/apd-framework \
  .claude/skills/apd-finding-schema \
  .claude/skills/apd-evidence-discipline \
  .claude/skills/apd-control-mappings \
  domains/pbm/common-patterns \
  schemas \
  templates \
  tools/apd_gauntlet/data \
  tests/fixtures/valid \
  tests/fixtures/invalid \
  examples \
  docs/adrs \
  .github/workflows \
  .github/ISSUE_TEMPLATE
```

- [ ] **Step 2: Add `.gitkeep` files so empty directories survive git**

Run:

```bash
for d in .claude/agents .claude/skills/apd-framework .claude/skills/apd-finding-schema \
  .claude/skills/apd-evidence-discipline .claude/skills/apd-control-mappings \
  domains/pbm/common-patterns schemas templates tools/apd_gauntlet/data \
  tests/fixtures/valid tests/fixtures/invalid examples docs/adrs .github/workflows .github/ISSUE_TEMPLATE; do
  touch "$d/.gitkeep"
done
```

- [ ] **Step 3: Verify the tree**

Run: `find . -type d -not -path '*/\.git/*' -not -path '*/9-agent-apd-framework/*' -not -path '*/docs/superpowers/*' | sort`
Expected: directories listed above all present.

- [ ] **Step 4: Commit**

```bash
git add .claude/ domains/ schemas/ templates/ tools/ tests/ examples/ docs/adrs/ .github/
git commit -m "M1: create v1.0 directory skeleton"
```

---

### Task 1.3: Migrate existing agents into `.claude/agents/`

**Files:**

- Move: `9-agent-apd-framework/apd-*.md` (12 files) → `.claude/agents/`

- [ ] **Step 1: Move all twelve agent files**

Run:

```bash
git mv 9-agent-apd-framework/apd-orchestrator.md  .claude/agents/apd-orchestrator.md
git mv 9-agent-apd-framework/apd-intake.md        .claude/agents/apd-intake.md
git mv 9-agent-apd-framework/apd-synthesizer.md   .claude/agents/apd-synthesizer.md
git mv 9-agent-apd-framework/apd-confidentiality.md .claude/agents/apd-confidentiality.md
git mv 9-agent-apd-framework/apd-integrity.md     .claude/agents/apd-integrity.md
git mv 9-agent-apd-framework/apd-availability.md  .claude/agents/apd-availability.md
git mv 9-agent-apd-framework/apd-distributed.md   .claude/agents/apd-distributed.md
git mv 9-agent-apd-framework/apd-resilient.md     .claude/agents/apd-resilient.md
git mv 9-agent-apd-framework/apd-ephemeral.md     .claude/agents/apd-ephemeral.md
git mv 9-agent-apd-framework/apd-authenticity.md  .claude/agents/apd-authenticity.md
git mv 9-agent-apd-framework/apd-non-repudiation.md .claude/agents/apd-non-repudiation.md
git mv 9-agent-apd-framework/apd-immutability.md  .claude/agents/apd-immutability.md
```

- [ ] **Step 2: Remove `.gitkeep` (no longer needed)**

Run: `rm .claude/agents/.gitkeep`

- [ ] **Step 3: Verify**

Run: `ls .claude/agents/ | wc -l`
Expected: `12`

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/
git commit -m "M1: move 12 agents into .claude/agents/"
```

---

### Task 1.4: Migrate existing skills into `.claude/skills/`

**Files:**

- Move: `9-agent-apd-framework/SKILL.md` → `.claude/skills/apd-framework/SKILL.md`
- Move: `9-agent-apd-framework/mnt/.../apd-evidence-discipline/SKILL.md` → `.claude/skills/apd-evidence-discipline/SKILL.md`
- Move: `9-agent-apd-framework/mnt/.../apd-finding-schema/SKILL.md` → `.claude/skills/apd-finding-schema/SKILL.md`
- Move: `9-agent-apd-framework/mnt/.../apd-control-mappings/SKILL.md` → `.claude/skills/apd-control-mappings/SKILL.md`

- [ ] **Step 1: Move skill files**

Run:

```bash
git mv 9-agent-apd-framework/SKILL.md .claude/skills/apd-framework/SKILL.md

git mv 9-agent-apd-framework/mnt/user-data/outputs/apd-gauntlet/.claude/skills/apd-evidence-discipline/SKILL.md \
       .claude/skills/apd-evidence-discipline/SKILL.md

git mv 9-agent-apd-framework/mnt/user-data/outputs/apd-gauntlet/.claude/skills/apd-finding-schema/SKILL.md \
       .claude/skills/apd-finding-schema/SKILL.md

git mv 9-agent-apd-framework/mnt/user-data/outputs/apd-gauntlet/.claude/skills/apd-control-mappings/SKILL.md \
       .claude/skills/apd-control-mappings/SKILL.md
```

- [ ] **Step 2: Remove the now-empty `mnt/` tree and `.gitkeep`s**

Run:

```bash
rm -rf 9-agent-apd-framework/mnt
rm .claude/skills/apd-framework/.gitkeep \
   .claude/skills/apd-finding-schema/.gitkeep \
   .claude/skills/apd-evidence-discipline/.gitkeep \
   .claude/skills/apd-control-mappings/.gitkeep
```

- [ ] **Step 3: Verify**

Run: `find .claude/skills -name SKILL.md | sort`
Expected: 4 paths — `apd-framework`, `apd-finding-schema`, `apd-evidence-discipline`, `apd-control-mappings`.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/ 9-agent-apd-framework/
git commit -m "M1: move 4 skills into .claude/skills/ and delete mnt/ duplicate"
```

---

### Task 1.5: Migrate templates and finalize legacy directory removal

**Files:**

- Move: `9-agent-apd-framework/*.template.{yaml,md}` (4 files) → `templates/`
- Move: `9-agent-apd-framework/README.md` → temporary path (will be rewritten in M7)
- Delete: `9-agent-apd-framework/`

- [ ] **Step 1: Move templates**

Run:

```bash
git mv 9-agent-apd-framework/finding.template.yaml      templates/finding.template.yaml
git mv 9-agent-apd-framework/capability.template.yaml   templates/capability.template.yaml
git mv 9-agent-apd-framework/context-brief.template.md  templates/context-brief.template.md
git mv 9-agent-apd-framework/advisory-report.template.md templates/advisory-report.template.md
```

- [ ] **Step 2: Stash the legacy README for reference during M7 rewrite**

Run: `git mv 9-agent-apd-framework/README.md docs/_legacy-readme.md`
(Adding the underscore prefix marks it as a transitional artifact; M7 deletes it after the new README is written.)

- [ ] **Step 3: Remove the now-empty `9-agent-apd-framework/` directory**

Run: `rmdir 9-agent-apd-framework`

- [ ] **Step 4: Remove the `templates/.gitkeep`**

Run: `rm templates/.gitkeep`

- [ ] **Step 5: Verify**

Run: `ls templates/`
Expected: `advisory-report.template.md  capability.template.yaml  context-brief.template.md  finding.template.yaml`

Run: `test ! -e 9-agent-apd-framework && echo gone`
Expected: `gone`

- [ ] **Step 6: Commit**

```bash
git add templates/ docs/ 9-agent-apd-framework
git commit -m "M1: move templates and remove 9-agent-apd-framework/ legacy directory"
```

---

### Task 1.6: Confirm M1 end state

- [ ] **Step 1: Tree sanity-check**

Run: `find . -maxdepth 2 -type d -not -path '*/\.git/*' | sort`
Expected to include: `.`, `.claude`, `.claude/agents`, `.claude/skills`, `.github`, `.github/ISSUE_TEMPLATE`, `.github/workflows`, `docs`, `docs/adrs`, `docs/superpowers`, `domains`, `domains/pbm`, `examples`, `schemas`, `templates`, `tests`, `tests/fixtures`, `tools`, `tools/apd_gauntlet`.
Should NOT include: `9-agent-apd-framework`, `mnt`.

- [ ] **Step 2: Push to origin**

Run: `git push origin main`
Expected: M1 commits visible on <https://github.com/shoveleejoe/apd-gauntlet>.

---

# M2 — Schemas

Goal: author 8 JSON Schema (draft 2020-12) files, plus positive and negative test fixtures for each, plus meta-validation that the schemas are themselves valid JSON Schema. Engineers writing findings or capabilities can hand them to `jsonschema.validate()` and get correct enforcement. Note: the `maturity ≥ implemented requires non-tech-plan evidence` rule is **not** in the schema (it needs intake context — enforced by the validator in M3). Each task in M2 follows TDD: write the negative fixture first (declares the invariant), then the schema, then verify both positive and negative cases.

### Task 2.1: Set up Python dev environment

**Files:** None (environment only).

- [ ] **Step 1: Create a virtual environment**

Run:

```bash
python3 -m venv .venv
. .venv/bin/activate
```

- [ ] **Step 2: Install the package in editable mode with dev extras**

Run: `pip install -e ".[dev]"`
Expected: installs jsonschema, pyyaml, click, rich, pytest, pytest-cov, ruff, mypy.

- [ ] **Step 3: Verify pytest discovers no tests yet (clean baseline)**

Run: `pytest`
Expected: `no tests ran` or similar with exit code 5.

---

### Task 2.2: Author the `finding.schema.json`

**Files:**

- Create: `schemas/finding.schema.json`
- Create: `tests/fixtures/valid/finding-minimal.yaml`
- Create: `tests/fixtures/valid/finding-full.yaml`
- Create: `tests/fixtures/invalid/finding-missing-id.yaml`
- Create: `tests/fixtures/invalid/finding-bad-disposition.yaml`
- Create: `tests/fixtures/invalid/finding-blocked-no-prereq.yaml`
- Create: `tests/fixtures/invalid/finding-bad-id-pattern.yaml`
- Create: `tests/fixtures/invalid/finding-strength-disposition.yaml`
- Create: `tests/test_finding_schema.py`

- [ ] **Step 1: Write the positive fixtures**

Create `tests/fixtures/valid/finding-minimal.yaml`:

```yaml
finding:
  schema_version: 1
  id: conf-1a2b3c4d
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality
  disposition: gap
  severity: high
  confidence: high
  title: "PHI fields in Kafka claim-events topic lack envelope encryption"
  summary: "Broker-level encryption only; PHI in plaintext between producers and consumers."
  detail: "Per the impact-to-PBM rubric clause 'PHI exposure beyond minimum-necessary internal audience.' Kafka broker access is a privileged role broader than minimum-necessary for any consumer."
  evidence:
    - artifact: tech_plan.md
      locator: "§4.2 paragraph 3"
      excerpt: "All Kafka topics use AES-256 at-rest encryption via broker-managed keys"
  control_mappings:
    nist_800_53r5: ["SC-8(1)", "SC-13", "SC-28(1)"]
  recommendation:
    posture: required
    summary: "Apply field-level envelope encryption to PHI fields before producer serialization."
    detail: "Replace broker-level encryption with envelope encryption applied in the producer SDK before serialization, using DEKs issued by the existing KMS hierarchy in §3.1."
```

Create `tests/fixtures/valid/finding-full.yaml` — same plus `prerequisite_evidence: []`, `control_mappings.mitre_attack: [{technique: "T1530", sub_technique: null, tactic: "TA0010", rationale: "Broker-level encryption leaves PHI in plaintext at the Kafka storage layer, enabling collection if broker filesystem access is obtained."}]`, `recommendation.references: ["internal: PHI_FIELD_CLASSIFICATION_GUIDE.md §6"]`, `related_concerns: [integrity, non_repudiation]`, `cross_references: []`.

- [ ] **Step 2: Write the negative fixtures (each tests one invariant)**

Create `tests/fixtures/invalid/finding-missing-id.yaml` — same as `valid/finding-minimal.yaml` but with the `id:` line deleted.

Create `tests/fixtures/invalid/finding-bad-disposition.yaml` — change `disposition: gap` to `disposition: weakness` (not in enum).

Create `tests/fixtures/invalid/finding-blocked-no-prereq.yaml` — change `disposition: gap` to `disposition: blocked` and omit `prerequisite_evidence`.

Create `tests/fixtures/invalid/finding-bad-id-pattern.yaml` — change `id: conf-1a2b3c4d` to `id: conf-XYZ` (not 8 hex chars).

Create `tests/fixtures/invalid/finding-strength-disposition.yaml` — change `disposition: gap` to `disposition: strength` (explicitly removed in v1 per spec §7).

- [ ] **Step 3: Write the test driver**

Create `tests/test_finding_schema.py`:

```python
"""Schema validation tests for finding records."""
from __future__ import annotations
import json
import pathlib
import pytest
import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_PATH = REPO / "schemas" / "finding.schema.json"
FIXTURES = REPO / "tests" / "fixtures"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "valid").glob("finding-*.yaml")],
)
def test_valid_finding_fixtures_pass(fixture):
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "valid" / fixture)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors == [], f"Unexpected errors: {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "fixture",
    [p.name for p in (FIXTURES / "invalid").glob("finding-*.yaml")],
)
def test_invalid_finding_fixtures_fail(fixture):
    schema = _load_schema()
    data = _load_yaml(FIXTURES / "invalid" / fixture)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data["finding"]))
    assert errors, f"Expected validation errors for {fixture}, got none"
```

- [ ] **Step 4: Run the tests and verify they fail**

Run: `pytest tests/test_finding_schema.py -v`
Expected: failure because `schemas/finding.schema.json` does not exist yet.

- [ ] **Step 5: Write the schema**

Create `schemas/finding.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/finding.schema.json",
  "title": "APD Gauntlet Finding",
  "type": "object",
  "required": [
    "schema_version", "id", "agent", "apd_tier", "apd_goal",
    "disposition", "severity", "confidence",
    "title", "summary", "detail",
    "evidence", "control_mappings", "recommendation"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "id": {
      "type": "string",
      "pattern": "^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged)-[0-9a-f]{8}$"
    },
    "agent": {
      "type": "string",
      "enum": [
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability",
        "synthesizer"
      ]
    },
    "apd_tier": { "type": "string", "enum": ["trustworthiness", "scalability", "auditability"] },
    "apd_goal": {
      "type": "string",
      "enum": [
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability"
      ]
    },
    "disposition": { "type": "string", "enum": ["gap", "risk", "uncertainty", "blocked"] },
    "severity":    { "type": "string", "enum": ["critical", "high", "medium", "low", "informational"] },
    "confidence":  { "type": "string", "enum": ["high", "medium", "low"] },
    "title":   { "type": "string", "minLength": 10, "maxLength": 200 },
    "summary": { "type": "string", "minLength": 10 },
    "detail":  { "type": "string", "minLength": 20 },
    "evidence": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["artifact", "locator", "excerpt"],
        "additionalProperties": false,
        "properties": {
          "artifact": { "type": "string", "minLength": 1 },
          "locator":  { "type": "string", "minLength": 1 },
          "excerpt":  { "type": "string", "minLength": 1, "maxLength": 500 }
        }
      }
    },
    "prerequisite_evidence": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 }
    },
    "control_mappings": {
      "type": "object",
      "required": ["nist_800_53r5"],
      "additionalProperties": false,
      "properties": {
        "nist_800_53r5": {
          "type": "array",
          "items": { "type": "string", "pattern": "^[A-Z]{2}-[0-9]+(\\([0-9]+\\))?$" }
        },
        "mitre_attack": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["technique", "tactic", "rationale"],
            "additionalProperties": false,
            "properties": {
              "technique":     { "type": "string", "pattern": "^T[0-9]{4}$" },
              "sub_technique": { "type": ["string", "null"], "pattern": "^T[0-9]{4}\\.[0-9]{3}$" },
              "tactic":        { "type": "string", "pattern": "^TA[0-9]{4}$" },
              "rationale":     { "type": "string", "minLength": 30 }
            }
          }
        }
      }
    },
    "recommendation": {
      "type": "object",
      "required": ["posture", "summary"],
      "additionalProperties": false,
      "properties": {
        "posture": { "type": "string", "enum": ["required", "recommended", "consider"] },
        "summary": { "type": "string", "minLength": 10 },
        "detail":  { "type": "string", "minLength": 20 },
        "references": { "type": "array", "items": { "type": "string" } }
      }
    },
    "related_concerns": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "confidentiality", "integrity", "availability",
          "distributed", "resilient", "ephemeral",
          "authenticity", "non_repudiation", "immutability"
        ]
      }
    },
    "cross_references": {
      "type": "array",
      "items": { "type": "string", "pattern": "^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged)-[0-9a-f]{8}$" }
    },
    "merged_from": {
      "type": "array",
      "items": { "type": "string", "pattern": "^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged)-[0-9a-f]{8}$" }
    },
    "lens_perspectives": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["summary", "detail"],
        "properties": {
          "summary": { "type": "string" },
          "detail":  { "type": "string" }
        }
      }
    }
  },
  "allOf": [
    {
      "if": { "properties": { "disposition": { "const": "blocked" } } },
      "then": {
        "required": ["prerequisite_evidence"],
        "properties": { "prerequisite_evidence": { "minItems": 1 } }
      }
    },
    {
      "if": { "properties": { "recommendation": { "required": ["posture"], "properties": { "posture": { "enum": ["required", "recommended"] } } } } },
      "then": { "properties": { "recommendation": { "required": ["posture", "summary", "detail"] } } }
    }
  ]
}
```

- [ ] **Step 6: Run the tests and verify they pass**

Run: `pytest tests/test_finding_schema.py -v`
Expected: all positive fixtures pass; all negative fixtures fail validation (i.e. the test asserting they fail passes).

- [ ] **Step 7: Commit**

```bash
git add schemas/finding.schema.json tests/fixtures/ tests/test_finding_schema.py
git commit -m "M2: add finding.schema.json with positive and negative fixtures"
```

---

### Task 2.3: Author the `capability.schema.json`

**Files:**

- Create: `schemas/capability.schema.json`
- Create: `tests/fixtures/valid/capability-designed.yaml`
- Create: `tests/fixtures/valid/capability-with-caveats.yaml`
- Create: `tests/fixtures/invalid/capability-bad-maturity.yaml`
- Create: `tests/fixtures/invalid/capability-no-scope.yaml`
- Create: `tests/fixtures/invalid/capability-bad-id.yaml`
- Create: `tests/test_capability_schema.py`

- [ ] **Step 1: Write the positive fixtures**

Create `tests/fixtures/valid/capability-designed.yaml`:

```yaml
capability:
  schema_version: 1
  id: conf-cap-7c2a4f91
  agent: confidentiality
  apd_tier: trustworthiness
  apd_goal: confidentiality
  title: "Field-level envelope encryption on PHI columns at rest"
  description: "Per tech plan §5.3, PHI columns in member_demographics and claims tables are encrypted at the field level using envelope encryption."
  maturity: designed
  scope: "Confirmed for: member_demographics table (all PHI columns), claims table (member_id, drug_ndc, prescriber_npi). Not addressed: audit_log table, Kafka event payloads."
  evidence:
    - artifact: tech_plan.md
      locator: "§5.3 paragraph 2"
      excerpt: "Field-level envelope encryption for PHI columns with DEKs from KMS"
  control_mappings:
    nist_800_53r5: ["SC-12", "SC-12(1)", "SC-13", "SC-28", "SC-28(1)"]
```

Create `tests/fixtures/valid/capability-with-caveats.yaml` — same plus `caveats: ["Key rotation cadence not specified in tech plan.", "DEK access boundary on application side unconfirmed."]` and `control_mappings.mitre_attack_mitigations: [{id: "M1041", rationale: "Field-level envelope encryption mitigates data collection from data store compromise."}]` and `related_concerns: [non_repudiation]`.

- [ ] **Step 2: Write the negative fixtures**

Create `tests/fixtures/invalid/capability-bad-maturity.yaml` — change `maturity: designed` to `maturity: production`.

Create `tests/fixtures/invalid/capability-no-scope.yaml` — delete the `scope:` field.

Create `tests/fixtures/invalid/capability-bad-id.yaml` — change ID to `conf-cap-ZZZ` (not 8 hex chars).

- [ ] **Step 3: Write the test driver**

Create `tests/test_capability_schema.py` — same shape as `test_finding_schema.py` but pointing at `capability.schema.json`, root key `capability`, and the `capability-*.yaml` fixtures.

- [ ] **Step 4: Run the tests and verify they fail**

Run: `pytest tests/test_capability_schema.py -v`
Expected: failure because schema does not exist yet.

- [ ] **Step 5: Write the schema**

Create `schemas/capability.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/shoveleejoe/apd-gauntlet/schemas/capability.schema.json",
  "title": "APD Gauntlet Capability",
  "type": "object",
  "required": [
    "schema_version", "id", "agent", "apd_tier", "apd_goal",
    "title", "description", "maturity", "scope",
    "evidence", "control_mappings"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "id": {
      "type": "string",
      "pattern": "^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged)-cap-[0-9a-f]{8}$"
    },
    "agent": { "$ref": "finding.schema.json#/properties/agent" },
    "apd_tier": { "$ref": "finding.schema.json#/properties/apd_tier" },
    "apd_goal": { "$ref": "finding.schema.json#/properties/apd_goal" },
    "title":       { "type": "string", "minLength": 10, "maxLength": 200 },
    "description": { "type": "string", "minLength": 20 },
    "maturity":    { "type": "string", "enum": ["designed", "implemented", "tested", "operationalized"] },
    "scope":       { "type": "string", "minLength": 20 },
    "evidence": { "$ref": "finding.schema.json#/properties/evidence" },
    "control_mappings": {
      "type": "object",
      "required": ["nist_800_53r5"],
      "additionalProperties": false,
      "properties": {
        "nist_800_53r5": { "$ref": "finding.schema.json#/properties/control_mappings/properties/nist_800_53r5" },
        "mitre_attack_mitigations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "rationale"],
            "additionalProperties": false,
            "properties": {
              "id":        { "type": "string", "pattern": "^M[0-9]{4}$" },
              "rationale": { "type": "string", "minLength": 30 }
            }
          }
        }
      }
    },
    "caveats": {
      "type": "array",
      "items": { "type": "string", "minLength": 5 }
    },
    "related_concerns": { "$ref": "finding.schema.json#/properties/related_concerns" }
  }
}
```

Note the `$ref` cross-file pointers — `jsonschema` resolves them via a referencing store; the test driver passes both schemas to the validator. Update `tests/test_capability_schema.py` to register both:

```python
from referencing import Registry, Resource
finding_schema  = Resource.from_contents(json.loads((REPO / "schemas/finding.schema.json").read_text()))
capability_schema = Resource.from_contents(json.loads((REPO / "schemas/capability.schema.json").read_text()))
registry = Registry().with_resources([
    ("https://github.com/shoveleejoe/apd-gauntlet/schemas/finding.schema.json", finding_schema),
    ("https://github.com/shoveleejoe/apd-gauntlet/schemas/capability.schema.json", capability_schema),
])
validator = Draft202012Validator(capability_schema.contents, registry=registry)
```

Use `from referencing import Registry, Resource` and the same pattern in any test that uses `$ref`.

- [ ] **Step 6: Run the tests and verify they pass**

Run: `pytest tests/test_capability_schema.py -v`
Expected: all positive fixtures pass, negative ones fail validation.

- [ ] **Step 7: Commit**

```bash
git add schemas/capability.schema.json tests/fixtures/ tests/test_capability_schema.py
git commit -m "M2: add capability.schema.json with positive and negative fixtures"
```

---

### Task 2.4: Author the remaining six schemas

**Files:**

- Create: `schemas/contradiction.schema.json`
- Create: `schemas/severity-disagreement.schema.json`
- Create: `schemas/coverage-matrix.schema.json`
- Create: `schemas/nist-coverage.schema.json`
- Create: `schemas/attack-exposure.schema.json`
- Create: `schemas/domain.schema.json`
- Create: per-schema fixtures under `tests/fixtures/valid/` and `tests/fixtures/invalid/`
- Create: `tests/test_other_schemas.py`

Treat this as **six mini-tasks**, all following the same TDD pattern as 2.2 and 2.3:

For each schema:

1. Write one positive fixture demonstrating a well-formed record.
2. Write at least one negative fixture (a different invariant per schema — e.g. for `severity-disagreement`, omit `agent_severities`; for `contradiction`, omit `finding_id`).
3. Write the schema using the field definitions from spec §5.
4. Verify the test in `tests/test_other_schemas.py` (parameterize over schema name and fixture file) discovers and passes.

The key required fields per schema (from spec §5):

| Schema | Required top-level fields |
|---|---|
| `contradiction` | `id`, `finding_id`, `capability_id`, `finding_assertion`, `capability_assertion`, `evidence_comparison`, `recommended_resolution` |
| `severity-disagreement` | `finding_id`, `agent_severities` (object, minProperties=2, values from severity enum), `chosen_severity`, `rationale` |
| `coverage-matrix` | Array of `component` records, each with `name` and `cells` (9 named cells: `confidentiality`, `integrity`, `availability`, `distributed`, `resilient`, `ephemeral`, `authenticity`, `non_repudiation`, `immutability`), each cell has `findings` (array of IDs), `capabilities` (array of IDs), `posture` (enum: `silent`, `covered`, `gapped`, `gapped_and_covered`) |
| `nist-coverage` | Array of `control` records, each with `id` (pattern `^[A-Z]{2}-[0-9]+(\\([0-9]+\\))?$`), `family` (2 uppercase letters), `title`, `finding_count`, `finding_ids`, `capability_count`, `capability_ids`, `posture` |
| `attack-exposure` | Array of `technique` records, each with `id` (T-pattern), `sub_technique` (T.NNN or null), `tactic` (TA-pattern), `name`, `exposure_finding_count`, `exposure_finding_ids`, `mitigated_by_capabilities` (array of `{capability_id, mitigation_id}` objects) |
| `domain` | `name` (kebab-case), `display_name`, `version` (semver), `framework_compat` (semver range string), `description`, `includes` (array of file paths), `regulatory_anchors` (array of strings) |

- [ ] **Step 1: Write `contradiction.schema.json`, fixtures, and verify**

Apply the TDD pattern. Commit:

```bash
git add schemas/contradiction.schema.json tests/fixtures/ tests/test_other_schemas.py
git commit -m "M2: add contradiction.schema.json with fixtures"
```

- [ ] **Step 2: Write `severity-disagreement.schema.json`, fixtures, and verify**

Commit individually.

- [ ] **Step 3: Write `coverage-matrix.schema.json`, fixtures, and verify**

Commit individually.

- [ ] **Step 4: Write `nist-coverage.schema.json`, fixtures, and verify**

Commit individually.

- [ ] **Step 5: Write `attack-exposure.schema.json`, fixtures, and verify**

Commit individually.

- [ ] **Step 6: Write `domain.schema.json`, fixtures, and verify**

Use a fixture that includes the PBM pack metadata from spec §8.2 as the positive case. Negative: omit `framework_compat`.

Commit:

```bash
git add schemas/domain.schema.json tests/fixtures/ tests/test_other_schemas.py
git commit -m "M2: add domain.schema.json with PBM fixture"
```

---

### Task 2.5: Meta-validate all schemas against the draft 2020-12 meta-schema

**Files:**

- Create: `tests/test_meta_schemas.py`

- [ ] **Step 1: Write the meta-validation test**

Create `tests/test_meta_schemas.py`:

```python
"""Verify every schema under schemas/ is itself a valid JSON Schema draft 2020-12 document."""
from __future__ import annotations
import json
import pathlib
import pytest
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"


@pytest.mark.parametrize("schema_path", sorted(SCHEMA_DIR.glob("*.schema.json")))
def test_schema_is_valid_meta(schema_path):
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_meta_schemas.py -v`
Expected: 8 tests pass (one per schema).

- [ ] **Step 3: Commit**

```bash
git add tests/test_meta_schemas.py
git commit -m "M2: meta-validate all 8 schemas against JSON Schema draft 2020-12"
```

---

### Task 2.6: Push M2 to origin

- [ ] **Step 1: Push**

Run: `git push origin main`
Expected: M2 commits visible on GitHub.

---

# M3 — Validator (Python CLI)

Goal: build the `apd-gauntlet` CLI with all subcommands from spec §6.1, the three validation passes from §6.2, tests at ≥85% coverage on `tools/apd_gauntlet/`, and the cached MITRE crosswalk.

### Task 3.1: Author the CLI skeleton

**Files:**

- Create: `tools/apd_gauntlet/__init__.py`
- Create: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI invocation test**

Create `tests/test_cli.py`:

```python
"""Smoke tests for the apd-gauntlet CLI entry point."""
from __future__ import annotations
from click.testing import CliRunner
from apd_gauntlet.cli import main


def test_cli_shows_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "apd-gauntlet" in result.output.lower()


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output
```

- [ ] **Step 2: Run the test (expect failure)**

Run: `pytest tests/test_cli.py -v`
Expected: `ModuleNotFoundError: No module named 'apd_gauntlet'`.

- [ ] **Step 3: Write the minimal package**

Create `tools/apd_gauntlet/__init__.py`:

```python
"""APD Gauntlet — Python validator and CLI for the APD security architecture review framework."""
__version__ = "1.0.0"
```

Create `tools/apd_gauntlet/cli.py`:

```python
"""apd-gauntlet CLI entry point."""
from __future__ import annotations
import click
from . import __version__


@click.group(help="APD Gauntlet — validator and tooling for APD security architecture reviews.")
@click.version_option(__version__, prog_name="apd-gauntlet")
def main():
    """Root command group."""


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: both tests pass.

- [ ] **Step 5: Verify the entry point installs correctly**

Run: `pip install -e ".[dev]" && apd-gauntlet --version`
Expected: `apd-gauntlet, version 1.0.0`.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/__init__.py tools/apd_gauntlet/cli.py tests/test_cli.py
git commit -m "M3: add apd-gauntlet CLI skeleton with --version and --help"
```

---

### Task 3.2: Implement the `validate` command — Pass 1 (schema validation)

**Files:**

- Create: `tools/apd_gauntlet/validate.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_validate_schema_pass.py`
- Create: `tests/fixtures/runs/clean-run/` (skeleton run directory)

- [ ] **Step 1: Write a failing test for the schema-validation pass**

Create the run-shape fixture: `tests/fixtures/runs/clean-run/` with subdirs `00-context`, `10-trustworthiness`, `20-scalability`, `30-auditability`, `40-synthesis`. Drop one valid finding YAML and one valid capability YAML into `10-trustworthiness/`.

Create `tests/test_validate_schema_pass.py`:

```python
"""Pass-1 tests: schema validation of records in a run directory."""
from __future__ import annotations
import pathlib
from click.testing import CliRunner
from apd_gauntlet.cli import main

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def test_validate_clean_run_returns_zero():
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0, result.output


def test_validate_run_with_bad_record_returns_one(tmp_path):
    # Copy a known-bad fixture into a temp run dir; assert exit 1.
    import shutil
    src = FIXTURES / "clean-run"
    dst = tmp_path / "run"
    shutil.copytree(src, dst)
    # Corrupt the finding by deleting required `severity` field.
    finding_file = dst / "10-trustworthiness" / "confidentiality.findings.yaml"
    text = finding_file.read_text()
    finding_file.write_text(text.replace("severity: high\n", ""))
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "severity" in result.output.lower()
```

- [ ] **Step 2: Run the test (expect failure — `validate` subcommand not registered)**

Run: `pytest tests/test_validate_schema_pass.py -v`
Expected: failure, "no such command 'validate'".

- [ ] **Step 3: Implement Pass 1**

Create `tools/apd_gauntlet/validate.py`:

```python
"""Validation engine — Pass 1 (schema), Pass 2 (semantic lints), Pass 3 (cross-file)."""
from __future__ import annotations
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Iterable
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = REPO / "schemas"

# Map record kind → schema file + YAML root key + filename glob
RECORD_KINDS = {
    "finding":    ("finding.schema.json",    "finding",    "*.findings.yaml"),
    "capability": ("capability.schema.json", "capability", "*.capabilities.yaml"),
}


@dataclass
class Violation:
    file: pathlib.Path
    record_id: str | None
    message: str
    path: str = ""

    def render(self) -> str:
        loc = f"{self.file}"
        if self.record_id:
            loc += f" [{self.record_id}]"
        if self.path:
            loc += f" {self.path}"
        return f"{loc}: {self.message}"


@dataclass
class ValidationReport:
    errors:   list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    files_seen: int = 0
    records_seen: int = 0

    @property
    def is_clean(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [f"Files scanned: {self.files_seen}  Records: {self.records_seen}"]
        for v in self.errors:
            lines.append(f"ERROR   {v.render()}")
        for v in self.warnings:
            lines.append(f"WARNING {v.render()}")
        return "\n".join(lines)


def _build_registry() -> Registry:
    finding    = Resource.from_contents(json.loads((SCHEMAS_DIR / "finding.schema.json").read_text()))
    capability = Resource.from_contents(json.loads((SCHEMAS_DIR / "capability.schema.json").read_text()))
    return Registry().with_resources([
        ("https://github.com/shoveleejoe/apd-gauntlet/schemas/finding.schema.json",    finding),
        ("https://github.com/shoveleejoe/apd-gauntlet/schemas/capability.schema.json", capability),
    ])


def _iter_records(run_dir: pathlib.Path) -> Iterable[tuple[pathlib.Path, str, dict[str, Any]]]:
    """Yield (file_path, kind, record_dict) for every YAML record in the run."""
    for kind, (_schema, root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            try:
                data = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError as e:
                yield path, kind, {"_parse_error": str(e)}
                continue
            # Files may contain a single record or a list under the root_key.
            payload = data.get(root_key)
            if payload is None and isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and root_key in item:
                        yield path, kind, item[root_key]
            elif isinstance(payload, list):
                for item in payload:
                    yield path, kind, item
            elif isinstance(payload, dict):
                yield path, kind, payload


def run_schema_pass(run_dir: pathlib.Path) -> ValidationReport:
    """Pass 1: validate every record against its JSON Schema."""
    registry = _build_registry()
    report = ValidationReport()
    validators = {
        kind: Draft202012Validator(
            json.loads((SCHEMAS_DIR / schema).read_text()),
            registry=registry,
        )
        for kind, (schema, _, _) in RECORD_KINDS.items()
    }
    seen_files: set[pathlib.Path] = set()
    for path, kind, record in _iter_records(run_dir):
        seen_files.add(path)
        if "_parse_error" in record:
            report.errors.append(Violation(path, None, f"YAML parse error: {record['_parse_error']}"))
            continue
        report.records_seen += 1
        validator = validators[kind]
        rid = record.get("id")
        for err in validator.iter_errors(record):
            report.errors.append(Violation(path, rid, err.message, "/".join(map(str, err.path))))
    report.files_seen = len(seen_files)
    return report
```

Modify `tools/apd_gauntlet/cli.py` — add the `validate` subcommand:

```python
import pathlib
from .validate import run_schema_pass


@main.command(help="Validate all records under a run directory.")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--schema-only", is_flag=True, help="Run schema validation only (skip semantic + cross-file passes).")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON output for CI consumption.")
def validate(run_dir, schema_only, as_json):
    report = run_schema_pass(run_dir)
    if as_json:
        import json as _json
        click.echo(_json.dumps({
            "errors":   [{"file": str(v.file), "id": v.record_id, "message": v.message, "path": v.path} for v in report.errors],
            "warnings": [{"file": str(v.file), "id": v.record_id, "message": v.message, "path": v.path} for v in report.warnings],
            "records":  report.records_seen,
        }, indent=2))
    else:
        click.echo(report.render())
    raise SystemExit(0 if report.is_clean else 1)
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `pytest tests/test_validate_schema_pass.py -v`
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tools/apd_gauntlet/cli.py \
        tests/test_validate_schema_pass.py tests/fixtures/runs/
git commit -m "M3: implement validate command — Pass 1 (schema validation)"
```

---

### Task 3.3: Implement Pass 2 — semantic lints

**Files:**

- Modify: `tools/apd_gauntlet/validate.py`
- Create: `tools/apd_gauntlet/linters.py`
- Create: `tests/test_validate_semantic.py`
- Create: `tests/fixtures/runs/long-excerpt/`, `runs/bad-id/`, `runs/hedge-rationale/`, `runs/over-tech-plan/`

Implement four semantic lints (spec §6.2 Pass 2):

1. `evidence[].excerpt` ≤ 25 whitespace-separated tokens. **Error.**
2. ID matches deterministic regeneration `sha8(title + "|" + first_evidence_locator)`. **Error.**
3. Capability `maturity ≥ implemented` ⇒ at least one evidence entry whose artifact is not in the run's tech_plan set. **Error.** (Tech plan set comes from intake brief — Pass 3 handles cross-file; this lint uses a simple "if any non-tech_plan artifact" heuristic for Pass 2 alone, then Pass 3 refines.)
4. `mitre_attack[].rationale` does not contain unjustified hedge words (`could`, `may`, `potentially`). **Warning.**

- [ ] **Step 1: Write failing tests for each lint**

Create `tests/test_validate_semantic.py` with one test per lint, each using a minimal fixture in `tests/fixtures/runs/<lint-name>/`. Pattern:

```python
def test_long_excerpt_is_caught(tmp_path):
    # Copy a clean run, then corrupt one excerpt to 30 words.
    ...
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "excerpt" in result.output.lower()
    assert "25" in result.output
```

Repeat for `test_bad_id_is_caught`, `test_hedge_word_is_warned`, `test_maturity_implemented_requires_evidence`.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_validate_semantic.py -v`
Expected: failures (lints not yet implemented).

- [ ] **Step 3: Implement the lints**

Create `tools/apd_gauntlet/linters.py`:

```python
"""Semantic lints — checks JSON Schema cannot express."""
from __future__ import annotations
import hashlib
import re
from typing import Any

HEDGE_WORDS = re.compile(r"\b(could|may|potentially)\b", re.IGNORECASE)


def compute_id(prefix: str, title: str, first_locator: str) -> str:
    """Deterministic id: first 8 hex chars of SHA-256 over title + '|' + locator."""
    payload = f"{title}|{first_locator}".encode()
    digest = hashlib.sha256(payload).hexdigest()[:8]
    return f"{prefix}-{digest}"


def check_excerpt_length(record: dict[str, Any]) -> list[str]:
    """Each excerpt must be ≤ 25 whitespace-separated tokens."""
    errors = []
    for i, ev in enumerate(record.get("evidence", [])):
        excerpt = ev.get("excerpt", "")
        n = len(excerpt.split())
        if n > 25:
            errors.append(f"evidence[{i}].excerpt has {n} tokens (max 25)")
    return errors


_PREFIX_BY_AGENT = {
    "confidentiality": "conf", "integrity": "intg", "availability": "avail",
    "distributed": "dist", "resilient": "resil", "ephemeral": "ephem",
    "authenticity": "auth", "non_repudiation": "nonrep", "immutability": "immut",
    "synthesizer": "merged",
}


def check_finding_id(record: dict[str, Any]) -> list[str]:
    """Finding ID must equal sha8(title + '|' + first_evidence_locator)."""
    agent = record.get("agent")
    prefix = _PREFIX_BY_AGENT.get(agent, "")
    if not prefix:
        return []
    title = record.get("title", "")
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    expected = compute_id(prefix, title, evidence[0].get("locator", ""))
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per deterministic rule"]
    return []


def check_capability_id(record: dict[str, Any]) -> list[str]:
    """Capability ID must equal sha8(...) with -cap- infix."""
    agent = record.get("agent")
    prefix = _PREFIX_BY_AGENT.get(agent, "")
    if not prefix:
        return []
    title = record.get("title", "")
    evidence = record.get("evidence") or []
    if not evidence:
        return []
    payload = f"{title}|{evidence[0].get('locator', '')}".encode()
    digest = hashlib.sha256(payload).hexdigest()[:8]
    expected = f"{prefix}-cap-{digest}"
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per deterministic rule"]
    return []


def check_hedge_words_in_attack_rationale(record: dict[str, Any]) -> list[str]:
    """WARNING-level: rationale shouldn't contain hedge words."""
    warnings = []
    for i, entry in enumerate(record.get("control_mappings", {}).get("mitre_attack", [])):
        rationale = entry.get("rationale", "")
        hits = HEDGE_WORDS.findall(rationale)
        if hits:
            warnings.append(f"mitre_attack[{i}].rationale uses hedge words: {sorted(set(hits))}")
    return warnings


def check_capability_maturity_evidence(record: dict[str, Any], tech_plan_artifacts: set[str]) -> list[str]:
    """Capability maturity ≥ implemented requires at least one non-tech-plan evidence entry."""
    if record.get("maturity") not in {"implemented", "tested", "operationalized"}:
        return []
    if not tech_plan_artifacts:
        return []  # nothing to compare against
    non_tech_plan = [
        ev for ev in record.get("evidence", [])
        if ev.get("artifact") not in tech_plan_artifacts
    ]
    if not non_tech_plan:
        return [f"maturity={record['maturity']} requires non-tech-plan evidence; "
                f"only tech-plan artifacts present"]
    return []
```

Modify `validate.py` — add `run_semantic_pass`:

```python
from . import linters


def run_semantic_pass(run_dir: pathlib.Path, tech_plan_artifacts: set[str] | None = None) -> ValidationReport:
    tech_plan_artifacts = tech_plan_artifacts or set()
    report = ValidationReport()
    for path, kind, record in _iter_records(run_dir):
        rid = record.get("id")
        report.records_seen += 1
        if kind == "finding":
            for msg in linters.check_excerpt_length(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_finding_id(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_hedge_words_in_attack_rationale(record):
                report.warnings.append(Violation(path, rid, msg))
        elif kind == "capability":
            for msg in linters.check_excerpt_length(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_capability_id(record):
                report.errors.append(Violation(path, rid, msg))
            for msg in linters.check_capability_maturity_evidence(record, tech_plan_artifacts):
                report.errors.append(Violation(path, rid, msg))
    return report
```

Modify the CLI `validate` command — merge schema + semantic reports:

```python
@main.command(help="Validate all records under a run directory.")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path))
@click.option("--schema-only", is_flag=True)
@click.option("--strict", is_flag=True, help="Treat warnings as errors.")
@click.option("--json", "as_json", is_flag=True)
def validate(run_dir, schema_only, strict, as_json):
    schema_rep = run_schema_pass(run_dir)
    if schema_only:
        merged = schema_rep
    else:
        semantic_rep = run_semantic_pass(run_dir)
        merged = ValidationReport(
            errors=schema_rep.errors + semantic_rep.errors,
            warnings=schema_rep.warnings + semantic_rep.warnings,
            files_seen=max(schema_rep.files_seen, semantic_rep.files_seen),
            records_seen=schema_rep.records_seen,
        )
    if strict:
        merged.errors.extend(merged.warnings)
        merged.warnings = []
    ... # emit + raise SystemExit as before
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest tests/test_validate_semantic.py -v`
Expected: all four semantic-lint tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/linters.py tools/apd_gauntlet/validate.py \
        tools/apd_gauntlet/cli.py tests/test_validate_semantic.py tests/fixtures/runs/
git commit -m "M3: implement validate Pass 2 — semantic lints (excerpt, id, hedge, maturity)"
```

---

### Task 3.4: Implement Pass 3 — cross-file resolution

**Files:**

- Modify: `tools/apd_gauntlet/validate.py`
- Create: `tests/test_validate_cross_file.py`
- Create: cross-file fixtures (run with dangling `cross_references`, etc.)

Implement four cross-file checks (spec §6.2 Pass 3):

1. `cross_references[]` IDs exist in lower-tier files.
2. `merged_from[]` IDs exist in pre-synthesis files.
3. `evidence[].artifact` appears in the intake artifact index (parsed from `00-context/context-brief.md`).
4. Contradictions in `40-synthesis/contradictions.yaml` reference real finding and capability IDs.

- [ ] **Step 1: Write failing tests**

Create `tests/test_validate_cross_file.py` with one test per cross-file check. For each, set up a fixture run with a deliberate orphan reference.

For the intake-brief check, the test fixture's `context-brief.md` should include a YAML frontmatter block:

```yaml
---
framework_version: 1.0.0
run_id: test-001
domain_pack: { name: pbm, version: 1.0.0 }
artifacts:
  - { filename: tech_plan.md, type: tech_plan }
  - { filename: claim-events.proto, type: code }
---
```

The cross-file pass parses this frontmatter to know what's a tech_plan and what artifacts are admissible.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/test_validate_cross_file.py -v`
Expected: failures (cross-file pass not implemented).

- [ ] **Step 3: Implement the cross-file pass**

Add to `validate.py`:

```python
def parse_intake_brief(brief_path: pathlib.Path) -> dict[str, Any]:
    """Extract the YAML frontmatter block from context-brief.md."""
    if not brief_path.exists():
        return {}
    text = brief_path.read_text()
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}


def run_cross_file_pass(run_dir: pathlib.Path) -> ValidationReport:
    report = ValidationReport()
    brief = parse_intake_brief(run_dir / "00-context" / "context-brief.md")
    known_artifacts: set[str] = {a["filename"] for a in brief.get("artifacts", [])}
    tech_plan_artifacts: set[str] = {a["filename"] for a in brief.get("artifacts", []) if a.get("type") == "tech_plan"}

    # Collect all finding/capability IDs by tier.
    finding_ids_by_tier: dict[str, set[str]] = {"10": set(), "20": set(), "30": set(), "40": set()}
    capability_ids: set[str] = set()
    for path, kind, record in _iter_records(run_dir):
        rid = record.get("id")
        if not rid:
            continue
        tier_dir = path.relative_to(run_dir).parts[0][:2]
        if kind == "finding":
            finding_ids_by_tier.setdefault(tier_dir, set()).add(rid)
        else:
            capability_ids.add(rid)

    all_finding_ids = set().union(*finding_ids_by_tier.values())

    # Verify cross_references and artifact references.
    for path, kind, record in _iter_records(run_dir):
        rid = record.get("id")
        # Evidence artifacts present in intake.
        for i, ev in enumerate(record.get("evidence", [])):
            art = ev.get("artifact")
            if known_artifacts and art not in known_artifacts:
                report.errors.append(Violation(path, rid, f"evidence[{i}].artifact '{art}' not in intake brief"))
        # cross_references resolve.
        for ref in record.get("cross_references", []):
            if ref not in all_finding_ids:
                report.errors.append(Violation(path, rid, f"cross_reference {ref} not found in any tier"))
        # merged_from resolve.
        for ref in record.get("merged_from", []):
            if ref not in all_finding_ids:
                report.errors.append(Violation(path, rid, f"merged_from {ref} not found"))

    # Re-run the maturity-vs-evidence lint with the real tech-plan set.
    if tech_plan_artifacts:
        sem = run_semantic_pass(run_dir, tech_plan_artifacts=tech_plan_artifacts)
        report.errors.extend(sem.errors)

    # Contradictions reference real IDs.
    contradictions_path = run_dir / "40-synthesis" / "contradictions.yaml"
    if contradictions_path.exists():
        data = yaml.safe_load(contradictions_path.read_text()) or {}
        for entry in (data.get("contradictions") or []):
            fid = entry.get("finding_id")
            cid = entry.get("capability_id")
            if fid not in all_finding_ids:
                report.errors.append(Violation(contradictions_path, entry.get("id"), f"finding_id {fid} not found"))
            if cid not in capability_ids:
                report.errors.append(Violation(contradictions_path, entry.get("id"), f"capability_id {cid} not found"))

    return report
```

Wire into the CLI: after Pass 2, if not `--schema-only`, also run `run_cross_file_pass` and merge.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest tests/test_validate_cross_file.py -v`
Expected: all cross-file tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tests/test_validate_cross_file.py tests/fixtures/
git commit -m "M3: implement validate Pass 3 — cross-file ID and artifact resolution"
```

---

### Task 3.5: Implement `init-run`

**Files:**

- Create: `tools/apd_gauntlet/init_run.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_init_run.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_init_run.py`:

```python
import pathlib
from click.testing import CliRunner
from apd_gauntlet.cli import main


def test_init_run_creates_expected_directories(tmp_path):
    inputs = tmp_path / "src-inputs"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# stub")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["init-run", "test-001", "--inputs", str(inputs), "--domain", "pbm", "--root", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0
    run_dir = tmp_path / "runs" / "test-001"
    for sub in ("inputs", "00-context", "10-trustworthiness", "20-scalability", "30-auditability", "40-synthesis"):
        assert (run_dir / sub).is_dir()
    assert (run_dir / "inputs" / "tech_plan.md").exists()
```

- [ ] **Step 2: Run test (expect failure — `init-run` not registered)**

Run: `pytest tests/test_init_run.py -v`
Expected: failure.

- [ ] **Step 3: Implement**

Create `tools/apd_gauntlet/init_run.py`:

```python
"""Scaffold a runs/<run-id>/ directory."""
from __future__ import annotations
import pathlib
import shutil

SUBDIRS = ["inputs", "00-context", "10-trustworthiness", "20-scalability", "30-auditability", "40-synthesis"]


def scaffold_run(run_id: str, inputs_src: pathlib.Path, domain: str, root: pathlib.Path) -> pathlib.Path:
    run_dir = root / run_id
    for sub in SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    # Copy inputs.
    for item in inputs_src.iterdir():
        target = run_dir / "inputs" / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    # Write a run metadata stub.
    (run_dir / ".apd-run.yaml").write_text(
        f"run_id: {run_id}\ndomain: {domain}\nframework_version: 1.0.0\n"
    )
    return run_dir
```

Modify `cli.py`:

```python
from .init_run import scaffold_run


@main.command("init-run", help="Scaffold runs/<run-id>/ with subdirectories and copy input artifacts.")
@click.argument("run_id")
@click.option("--inputs", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path), required=True)
@click.option("--domain", default="pbm", show_default=True)
@click.option("--root", type=click.Path(file_okay=False, path_type=pathlib.Path), default=pathlib.Path("runs"), show_default=True)
def init_run_cmd(run_id, inputs, domain, root):
    target = scaffold_run(run_id, inputs, domain, root)
    click.echo(f"Run scaffolded at {target}")
```

- [ ] **Step 4: Run test (verify pass)**

Run: `pytest tests/test_init_run.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/init_run.py tools/apd_gauntlet/cli.py tests/test_init_run.py
git commit -m "M3: implement init-run command"
```

---

### Task 3.6: Implement `build-domain-skill`

**Files:**

- Create: `tools/apd_gauntlet/build_domain_skill.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_build_domain_skill.py`
- Create: `tests/fixtures/domains/sample/` (minimal test domain pack)

- [ ] **Step 1: Write the test fixture**

Create `tests/fixtures/domains/sample/domain.yaml`:

```yaml
name: sample
display_name: "Sample Test Domain"
version: 0.1.0
framework_compat: ">=1.0.0,<2.0.0"
description: "Minimal domain pack used only in tests."
includes:
  - severity-rubric.md
  - common-patterns/confidentiality.md
regulatory_anchors: []
```

Create `tests/fixtures/domains/sample/severity-rubric.md`:

```markdown
# Sample severity rubric

Critical: data loss beyond test scope.
High: degraded test fidelity.
Medium: test smell.
Low: cosmetic.
```

Create `tests/fixtures/domains/sample/common-patterns/confidentiality.md`:

```markdown
# Confidentiality patterns (sample)

Just one sample pattern.
```

- [ ] **Step 2: Write failing test**

Create `tests/test_build_domain_skill.py`:

```python
import pathlib
from click.testing import CliRunner
from apd_gauntlet.cli import main


def test_build_domain_skill_emits_expected_file(tmp_path):
    runner = CliRunner()
    out = tmp_path / "apd-domain"
    result = runner.invoke(
        main,
        [
            "build-domain-skill", "sample",
            "--domains-dir", "tests/fixtures/domains",
            "--out", str(out),
            "--framework-version", "1.0.0",
        ],
    )
    assert result.exit_code == 0, result.output
    skill = out / "SKILL.md"
    assert skill.exists()
    text = skill.read_text()
    assert "name: apd-domain" in text
    assert "pack: sample" in text
    assert "Sample severity rubric" in text
    assert "Confidentiality patterns (sample)" in text


def test_build_domain_skill_rejects_incompatible_framework(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "build-domain-skill", "sample",
            "--domains-dir", "tests/fixtures/domains",
            "--out", str(tmp_path / "apd-domain"),
            "--framework-version", "2.0.0",
        ],
    )
    assert result.exit_code != 0
    assert "framework_compat" in result.output.lower() or "incompatible" in result.output.lower()
```

- [ ] **Step 3: Run test (expect failure)**

Run: `pytest tests/test_build_domain_skill.py -v`

- [ ] **Step 4: Implement**

Create `tools/apd_gauntlet/build_domain_skill.py`:

```python
"""Compose .claude/skills/apd-domain/SKILL.md from a domain pack."""
from __future__ import annotations
import datetime
import json
import pathlib
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DOMAIN_SCHEMA = json.loads((REPO / "schemas" / "domain.schema.json").read_text())


def _parse_semver_range(spec: str) -> tuple[tuple[int,int,int] | None, tuple[int,int,int] | None]:
    """Minimal '>=1.0.0,<2.0.0'-style range parser."""
    lo = hi = None
    for tok in spec.split(","):
        tok = tok.strip()
        if tok.startswith(">="):
            lo = tuple(int(x) for x in tok[2:].split("."))
        elif tok.startswith("<"):
            hi = tuple(int(x) for x in tok[1:].split("."))
    return lo, hi


def _version_in_range(version: str, spec: str) -> bool:
    v = tuple(int(x) for x in version.split("."))
    lo, hi = _parse_semver_range(spec)
    if lo and v < lo:
        return False
    if hi and v >= hi:
        return False
    return True


def build_domain_skill(
    domain_name: str,
    domains_dir: pathlib.Path,
    out_dir: pathlib.Path,
    framework_version: str,
) -> pathlib.Path:
    pack_dir = domains_dir / domain_name
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Domain pack '{domain_name}' not found at {pack_dir}")
    meta = yaml.safe_load(meta_path.read_text())
    Draft202012Validator(DOMAIN_SCHEMA).validate(meta)

    if not _version_in_range(framework_version, meta["framework_compat"]):
        raise ValueError(
            f"Framework {framework_version} incompatible with pack '{domain_name}' "
            f"framework_compat: {meta['framework_compat']}"
        )

    # Concatenate included files.
    sections: list[str] = []
    for path in meta["includes"]:
        for f in sorted(pack_dir.glob(path)):
            sections.append(f"\n\n## Source: `{f.relative_to(pack_dir)}`\n\n")
            sections.append(f.read_text())

    timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    frontmatter = (
        "---\n"
        "name: apd-domain\n"
        "description: Active domain pack content — severity rubric, consequential actions, common patterns. "
        "Generated from a domain pack at build time; do not edit by hand.\n"
        "metadata:\n"
        f"  pack: {meta['name']}\n"
        f"  pack_version: {meta['version']}\n"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "---\n"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "SKILL.md"
    out_path.write_text(frontmatter + "".join(sections))
    return out_path
```

Modify `cli.py`:

```python
from .build_domain_skill import build_domain_skill


@main.command("build-domain-skill")
@click.argument("domain_name")
@click.option("--domains-dir", type=click.Path(exists=True, file_okay=False, path_type=pathlib.Path), default=pathlib.Path("domains"))
@click.option("--out", type=click.Path(file_okay=False, path_type=pathlib.Path), default=pathlib.Path(".claude/skills/apd-domain"))
@click.option("--framework-version", default="1.0.0")
def build_domain_skill_cmd(domain_name, domains_dir, out, framework_version):
    path = build_domain_skill(domain_name, domains_dir, out, framework_version)
    click.echo(f"Wrote {path}")
```

- [ ] **Step 5: Run tests (verify pass)**

Run: `pytest tests/test_build_domain_skill.py -v`
Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/build_domain_skill.py tools/apd_gauntlet/cli.py \
        tests/test_build_domain_skill.py tests/fixtures/domains/
git commit -m "M3: implement build-domain-skill command with semver compat check"
```

---

### Task 3.7: Implement `summarize`, `lint-agents`, `check-ids`, `validate-domain`

**Files:**

- Create: `tools/apd_gauntlet/summary.py`
- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_summarize.py`, `tests/test_lint_agents.py`, `tests/test_check_ids.py`, `tests/test_validate_domain.py`

For each command, follow the TDD pattern: failing test, implement, passing test, commit. Brief specs:

- `summarize <run-dir>` — counts findings by severity, capabilities by maturity, blocked count, contradictions, severity disagreements; emits the table in spec §11 of the orchestrator's output template.
- `lint-agents [--agent-dir]` — confirms each agent file has valid YAML frontmatter with `name` and `description`; confirms "Required reading" paths resolve.
- `check-ids <yaml-file>` — for each record, regenerate the deterministic ID and report mismatches (one record per line).
- `validate-domain <name>` — validates `domains/<name>/domain.yaml` against the schema and verifies all `includes` files exist.

Each of these is roughly 15-30 lines of implementation. Commit each independently:

```bash
git commit -m "M3: implement summarize command"
git commit -m "M3: implement lint-agents command"
git commit -m "M3: implement check-ids command"
git commit -m "M3: implement validate-domain command"
```

---

### Task 3.8: Implement `refresh-mitre` and ship the cached crosswalk

**Files:**

- Create: `tools/apd_gauntlet/refresh_mitre.py`
- Create: `tools/apd_gauntlet/data/mitre-mitigations.json` (cached)
- Modify: `tools/apd_gauntlet/cli.py`
- Create: `tests/test_refresh_mitre.py`

The `refresh-mitre` subcommand fetches MITRE's enterprise STIX bundle and projects it into a compact mitigation→technique JSON the validator can use. Spec §3F notes this is a quarterly maintenance task post-v1.0; for v1.0 we ship a snapshot with the project.

- [ ] **Step 1: Author the fetch + project logic**

The MITRE source: `https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json`. Mitigations have `type: course-of-action`; relationships of `relationship_type: mitigates` connect a mitigation (`source_ref`) to a technique (`target_ref`).

Create `tools/apd_gauntlet/refresh_mitre.py`:

```python
"""Refresh the cached MITRE ATT&CK mitigation→technique crosswalk."""
from __future__ import annotations
import json
import pathlib
import urllib.request

MITRE_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"


def fetch_and_project(out_path: pathlib.Path) -> None:
    with urllib.request.urlopen(MITRE_URL) as resp:
        bundle = json.loads(resp.read().decode("utf-8"))
    mit_to_techs: dict[str, list[str]] = {}
    by_id = {obj.get("id"): obj for obj in bundle.get("objects", [])}
    for obj in bundle.get("objects", []):
        if obj.get("type") != "relationship":
            continue
        if obj.get("relationship_type") != "mitigates":
            continue
        src = by_id.get(obj.get("source_ref")) or {}
        tgt = by_id.get(obj.get("target_ref")) or {}
        mit_id = next((r["external_id"] for r in src.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)
        tech_id = next((r["external_id"] for r in tgt.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)
        if mit_id and tech_id:
            mit_to_techs.setdefault(mit_id, []).append(tech_id)
    payload = {"version": bundle.get("created", "unknown"), "mitigations": {k: sorted(set(v)) for k, v in mit_to_techs.items()}}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
```

Wire as `refresh-mitre` in `cli.py`. The CLI command writes to `tools/apd_gauntlet/data/mitre-mitigations.json` by default.

- [ ] **Step 2: Run `apd-gauntlet refresh-mitre` once locally** to produce the snapshot

Run: `apd-gauntlet refresh-mitre`
Expected: writes `tools/apd_gauntlet/data/mitre-mitigations.json` (~50-150 KB).

- [ ] **Step 3: Write the test (using a network-mocked version)**

Create `tests/test_refresh_mitre.py`:

```python
import json
import pathlib
from unittest.mock import patch
from apd_gauntlet.refresh_mitre import fetch_and_project


FAKE_BUNDLE = {
    "created": "2026-01-01",
    "objects": [
        {"id": "course-of-action--1", "type": "course-of-action",
         "external_references": [{"source_name": "mitre-attack", "external_id": "M1041"}]},
        {"id": "attack-pattern--1", "type": "attack-pattern",
         "external_references": [{"source_name": "mitre-attack", "external_id": "T1530"}]},
        {"type": "relationship", "relationship_type": "mitigates",
         "source_ref": "course-of-action--1", "target_ref": "attack-pattern--1"},
    ],
}


def test_fetch_and_project(tmp_path):
    out = tmp_path / "out.json"
    with patch("urllib.request.urlopen") as mock:
        mock.return_value.__enter__.return_value.read.return_value = json.dumps(FAKE_BUNDLE).encode()
        fetch_and_project(out)
    data = json.loads(out.read_text())
    assert data["mitigations"]["M1041"] == ["T1530"]
```

Run: `pytest tests/test_refresh_mitre.py -v`
Expected: pass.

- [ ] **Step 4: Commit the snapshot and code together**

```bash
git add tools/apd_gauntlet/refresh_mitre.py tools/apd_gauntlet/cli.py \
        tools/apd_gauntlet/data/mitre-mitigations.json tests/test_refresh_mitre.py
git commit -m "M3: implement refresh-mitre + ship initial MITRE crosswalk snapshot"
```

---

### Task 3.9: Coverage check + push

**Files:** None.

- [ ] **Step 1: Run the full test suite with coverage**

Run: `pytest --cov`
Expected: all tests pass; coverage report at end. Line coverage on `tools/apd_gauntlet/` must be ≥85%; `validate.py` should be at 100%.

- [ ] **Step 2: Run ruff and mypy**

Run: `ruff check tools/ tests/ && mypy tools/`
Expected: clean.

- [ ] **Step 3: Push**

Run: `git push origin main`

---

# M4 — Agent Refactor and Contract Fixes

Goal: apply the seven contract fixes from spec §7.1, extract PBM specialization out of agent and skill files (§7.2). Agents are content; "tests" are running `apd-gauntlet lint-agents` and ensuring schemas/templates updated consistently.

### Task 4.1: Update templates with `schema_version` and drop `strength`

**Files:**

- Modify: `templates/finding.template.yaml`
- Modify: `templates/capability.template.yaml`

- [ ] **Step 1: Add `schema_version: 1` to both templates**

Edit `templates/finding.template.yaml` — after `finding:` add `schema_version: 1` as the first child field. Same for `capability:` in the capability template.

- [ ] **Step 2: Update the finding template's `disposition:` comment**

Change the comment line near `disposition: gap` from:

```
disposition: gap   # required: gap | risk | uncertainty | strength | blocked
```

to:

```
disposition: gap   # required: gap | risk | uncertainty | blocked
```

- [ ] **Step 3: Verify**

Run: `python -c "import yaml; yaml.safe_load(open('templates/finding.template.yaml'))"` — completes without error (templates contain illustrative valid YAML).

- [ ] **Step 4: Commit**

```bash
git add templates/finding.template.yaml templates/capability.template.yaml
git commit -m "M4: add schema_version to templates; remove strength from disposition enum"
```

---

### Task 4.2: Update `apd-finding-schema/SKILL.md`

**Files:**

- Modify: `.claude/skills/apd-finding-schema/SKILL.md`

- [ ] **Step 1: Read the current file** to locate the disposition documentation.

- [ ] **Step 2: Drop `strength` from the documented `disposition` enum**

Replace:

```
disposition: gap                # gap | risk | uncertainty | strength | blocked
```

with:

```
disposition: gap                # gap | risk | uncertainty | blocked
```

Remove the `strength` row from the dispositions documentation table.

- [ ] **Step 3: Add `schema_version: 1` to the schema sample**

In the YAML sample block in §"Finding schema", insert `schema_version: 1` as the second field after `id:`.

- [ ] **Step 4: Add the canonical schema-file reference at the top**

Add a new section near the top:

```markdown
## Canonical contract

The authoritative contract for each record kind is the JSON Schema file:

- `schemas/finding.schema.json`
- `schemas/capability.schema.json`
- `schemas/contradiction.schema.json`
- `schemas/severity-disagreement.schema.json`
- `schemas/coverage-matrix.schema.json`
- `schemas/nist-coverage.schema.json`
- `schemas/attack-exposure.schema.json`
- `schemas/domain.schema.json`

This skill is the human-readable companion. When they disagree, the JSON Schema wins. Run `apd-gauntlet validate <run-dir>` to enforce.
```

- [ ] **Step 5: Expand `gap` vs `risk` differentiation**

In the field-semantics section under `disposition`, replace the brief one-liners with three worked examples per disposition (use this exact wording so the engineer doesn't have to invent):

```markdown
- `gap` — required control or property is absent.
  - Example: "Audit log is not encrypted at rest." (Property absent.)
  - Example: "No retry policy specified for the eligibility vendor call." (Control absent.)
  - Example: "MFA not required on the admin portal." (Control absent.)
- `risk` — present but inadequate, or with material weakness.
  - Example: "TLS configured but cipher suite allows 3DES." (Present but weak.)
  - Example: "Retries present but no jitter; thundering herd risk." (Present but inadequate.)
  - Example: "Audit log written but actor attribution is the system account." (Present but inadequate.)
- `uncertainty` — concern identified but evidence is incomplete; partial reasoning still possible.
  - Example: "Tech plan mentions 'TLS' without specifying version." (Partial evidence — TLS is intended.)
  - Example: "Retention is described as 'meets regulatory' without citation." (Partial.)
  - Example: "Backup encryption mentioned generally without key-management detail." (Partial.)
- `blocked` — cannot assess in this lens without prerequisite evidence. Must populate `prerequisite_evidence`.
  - Example: "No documentation of KMS hierarchy at all; cannot assess key separation."
  - Example: "Tech plan silent on vendor SLAs."
  - Example: "Audit format unspecified; cannot evaluate ATNA conformance."
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/apd-finding-schema/SKILL.md
git commit -m "M4: update finding-schema skill — drop strength, add schema_version, schema refs, gap/risk examples"
```

---

### Task 4.3: Update `apd-evidence-discipline/SKILL.md` — remove PBM rubric

**Files:**

- Modify: `.claude/skills/apd-evidence-discipline/SKILL.md`

The current file embeds the full impact-to-PBM severity rubric. M5 moves the rubric content to `domains/pbm/severity-rubric.md`. Here we *remove* the rubric from this skill and replace with a pointer.

- [ ] **Step 1: Delete the entire "Severity rubric — impact-to-PBM" section** (from heading through "Severity calibration discipline" subsection's last bullet).

- [ ] **Step 2: Replace with this domain-pointer section:**

```markdown
## Severity rubric (domain-loaded)

The severity rubric is domain-specific and lives in the active domain pack at `domains/<active>/severity-rubric.md`. It is bundled into the `apd-domain` skill at run time by `apd-gauntlet build-domain-skill`.

You MUST cite the matching rubric clause in the finding's `detail` field. The synthesizer relies on cited clauses to reconcile severity disagreements between agents.

If no domain pack is loaded for a run, agents emit a single high-severity finding "no severity rubric in scope" and halt; this is intentional — the gauntlet has no fallback default.

## Severity calibration discipline

[Keep the existing four bullets here verbatim — they're domain-neutral.]
```

- [ ] **Step 3: Update the "Self-check before emitting" list**

In bullet 4, change the wording from "Does my chosen severity match a specific clause in the rubric?" to "Does my chosen severity match a specific clause in the active domain's severity rubric, and can I cite that clause in `detail`?"

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/apd-evidence-discipline/SKILL.md
git commit -m "M4: remove PBM rubric from evidence-discipline; replace with domain-pointer section"
```

---

### Task 4.4: Update `apd-control-mappings/SKILL.md` — cite MITRE crosswalk source

**Files:**

- Modify: `.claude/skills/apd-control-mappings/SKILL.md`

- [ ] **Step 1: Add a "Crosswalk source" section under "MITRE ATT&CK mapping discipline":**

```markdown
### Crosswalk source

The mitigation→technique crosswalk is derived from MITRE's enterprise-attack STIX bundle:
`https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json`

A projected JSON snapshot ships at `tools/apd_gauntlet/data/mitre-mitigations.json`. Refresh with `apd-gauntlet refresh-mitre`. The synthesizer's ATT&CK exposure rollup uses this snapshot to correlate mitigation IDs (M-numbers) with the technique IDs (T-numbers) they mitigate.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/apd-control-mappings/SKILL.md
git commit -m "M4: cite MITRE STIX crosswalk source and shipped snapshot in control-mappings"
```

---

### Task 4.5: Update `apd-orchestrator.md` — Phase 0 domain build, tier-end validation, skip-specialist stubs

**Files:**

- Modify: `.claude/agents/apd-orchestrator.md`

- [ ] **Step 1: Insert a new sub-step in Phase 0 (after "Validate the input directory"):**

```markdown
### Phase 0 — Setup

1. Validate the input directory exists and is non-empty.
2. Determine the active domain pack (default: `pbm`; overridable via scope hint).
3. Build the domain skill: `apd-gauntlet build-domain-skill <domain> --framework-version <version>`.
   Verify `.claude/skills/apd-domain/SKILL.md` was written. Halt with a request-for-evidence finding if the pack is missing or incompatible.
4. Create the run directory structure (as before).
5. Validate the active pack against `schemas/domain.schema.json` via `apd-gauntlet validate-domain <domain>`.
```

- [ ] **Step 2: Add a "Tier-end validation" subsection between Phase 2/3/4:**

After each tier's parallel dispatch and completion, append:

```markdown
**Validation.** Run `apd-gauntlet validate <run-dir>` over the just-completed tier's outputs. If any record fails Pass 1 (schema), Pass 2 (semantic), or Pass 3 (cross-file) validation, route back to the emitting agent with the specific violations cited. Allow up to two retries per agent. After two retries, surface the failure and proceed without that record.
```

- [ ] **Step 3: Replace the "Scope hints from the user" section's `Skip <Specialist>` bullet:**

```markdown
- **"Skip <Specialist>"** — omit the named specialist from its tier dispatch and write stub files at the expected output paths so downstream tiers still find them. Stub format:
  ```yaml
  _meta:
    skipped: true
    reason: "<scope hint text>"
    emitted_by: orchestrator
  findings: []
  ```

  Same shape for capabilities. The synthesizer records the skip in run metadata; advisory report includes a "Specialists skipped" note in the executive summary.

```

- [ ] **Step 4: Add a Phase 6 line about run metadata:**

```markdown
6. **Closeout.** ... Append a `_meta` block to the advisory report's frontmatter:
   ```yaml
   ---
   framework_version: <version>
   domain_pack:
     name: <pack>
     version: <pack version>
   run_id: <id>
   specialists_skipped: [<list>]
   ---
   ```

```

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-orchestrator.md
git commit -m "M4: orchestrator — Phase 0 domain build, tier-end validation, skip-specialist stubs"
```

---

### Task 4.6: Update `apd-synthesizer.md` — rejected-records, validator invocation, frontmatter

**Files:**

- Modify: `.claude/agents/apd-synthesizer.md`

- [ ] **Step 1: Add `rejected-records.yaml` to the official "Outputs" list**

In the bulleted "Write to `40-synthesis/`:" list, insert:

```
- `rejected-records.yaml` — records that failed structural validation, with the reason per record
```

- [ ] **Step 2: Rewrite Step 1 (structural validation) to defer to the validator:**

```markdown
### Step 1: Structural validation

Invoke `apd-gauntlet validate <run-dir>`. The validator runs Pass 1 (schema), Pass 2 (semantic), and Pass 3 (cross-file) over every record. Records flagged with `errors` are written to `40-synthesis/rejected-records.yaml` with the validation message per record; they are excluded from clustering and downstream synthesis. Records flagged with `warnings` proceed but the warning is surfaced in the advisory report's executive summary.

If the validator CLI is unavailable, fall back to LLM-judged structural review using the rules in `apd-finding-schema/SKILL.md`. Note the fallback in the run metadata.
```

- [ ] **Step 3: Update Step 9 to emit YAML frontmatter on the advisory report:**

After the "Section order" list, add:

```markdown
The advisory report begins with a YAML frontmatter block:

```yaml
---
framework_version: 1.0.0
domain_pack:
  name: pbm
  version: 1.0.0
run_id: apd-20260601-claim-event-bus
synthesizer_version: 1.0.0
specialists_skipped: []
---
```

Then the human-readable section content follows.

```

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/apd-synthesizer.md
git commit -m "M4: synthesizer — add rejected-records output, validator invocation, frontmatter"
```

---

### Task 4.7: Update `apd-intake.md` — frontmatter, artifact-index for cross-file validation

**Files:**

- Modify: `.claude/agents/apd-intake.md`

- [ ] **Step 1: Add a sub-step in "Process / Step 1" requiring the intake brief to start with frontmatter:**

```markdown
The brief MUST begin with a YAML frontmatter block listing every artifact with its type, so the validator can resolve `evidence[].artifact` references and the maturity-vs-evidence rule:

```yaml
---
framework_version: 1.0.0
run_id: <run-id>
domain_pack: { name: <pack>, version: <pack-version> }
artifacts:
  - { filename: tech_plan.md,         type: tech_plan }
  - { filename: claim-events.proto,   type: code }
  - { filename: threat-model.md,      type: threat_model }
  - ...
---
```

The artifact `type` values come from the type taxonomy listed below. Specialists never write outside this index — evidence references that don't appear here are caught by `apd-gauntlet validate`.

```

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/apd-intake.md
git commit -m "M4: intake — require YAML frontmatter with typed artifact index"
```

---

### Task 4.8: Refactor each specialist agent (×9) — remove embedded patterns, add apd-domain reading

**Files:**

- Modify: `.claude/agents/apd-confidentiality.md`
- Modify: `.claude/agents/apd-integrity.md`
- Modify: `.claude/agents/apd-availability.md`
- Modify: `.claude/agents/apd-distributed.md`
- Modify: `.claude/agents/apd-resilient.md`
- Modify: `.claude/agents/apd-ephemeral.md`
- Modify: `.claude/agents/apd-authenticity.md`
- Modify: `.claude/agents/apd-non-repudiation.md`
- Modify: `.claude/agents/apd-immutability.md`

Treat this as **nine micro-tasks** with the same shape. Per file:

- [ ] **Step 1: Add `apd-domain/SKILL.md` to "Required reading"**

In the "Required reading" list (typically 5 items), insert as a new entry:

```
- `.claude/skills/apd-domain/SKILL.md` — active domain's severity rubric, consequential actions, and common patterns
```

- [ ] **Step 2: Delete the "Common finding patterns" section verbatim**

This content moves to `domains/pbm/common-patterns/<goal>.md` (Task 5.4). The agent file keeps only domain-neutral analytical content.

- [ ] **Step 3: Delete the "Common capability patterns" section verbatim**

Same — moves to the same file.

- [ ] **Step 4: Add a closing pointer paragraph in place of the removed sections:**

```markdown
## Common patterns

Pattern templates calibrated to the active domain — including severity calibration anchors and NIST/ATT&CK mapping examples — are in the `apd-domain` skill (`domains/<active>/common-patterns/<goal>.md`). Treat those as the working starting points for findings and capabilities in this lens. Patterns are *examples*, not a closed catalog; novel concerns produce novel findings.
```

- [ ] **Step 5: Commit (one per file)**

```bash
git add .claude/agents/apd-<goal>.md
git commit -m "M4: refactor apd-<goal> — drop PBM patterns, point at apd-domain skill"
```

Repeat for all nine specialists.

---

### Task 4.9: Add `schema_version` documentation to `context-brief.template.md`

**Files:**

- Modify: `templates/context-brief.template.md`

- [ ] **Step 1: Insert the YAML frontmatter block at the top of the file**

Replace the existing top line `# APD Gauntlet Context Brief — Run ...` with:

```markdown
---
framework_version: 1.0.0
run_id: <run-id>
domain_pack: { name: pbm, version: 1.0.0 }
artifacts:
  - { filename: tech_plan.md, type: tech_plan }
  - { filename: claim-events.proto, type: code }
  # ... add one row per artifact
---

# APD Gauntlet Context Brief — Run `<run-id>`
```

- [ ] **Step 2: Commit**

```bash
git add templates/context-brief.template.md
git commit -m "M4: add YAML frontmatter (framework_version, artifacts) to context-brief template"
```

---

### Task 4.10: Add frontmatter to `advisory-report.template.md`

**Files:**

- Modify: `templates/advisory-report.template.md`

- [ ] **Step 1: Insert frontmatter at top:**

```markdown
---
framework_version: 1.0.0
domain_pack: { name: pbm, version: 1.0.0 }
run_id: <run-id>
synthesizer_version: 1.0.0
specialists_skipped: []
---

# APD Gauntlet Advisory Report — Run `<run-id>`
```

- [ ] **Step 2: Commit**

```bash
git add templates/advisory-report.template.md
git commit -m "M4: add YAML frontmatter to advisory-report template"
```

---

### Task 4.11: Run `lint-agents` and push M4

- [ ] **Step 1: Lint**

Run: `apd-gauntlet lint-agents --agent-dir .claude/agents/`
Expected: all 12 agents have valid frontmatter; all "Required reading" paths resolve (note: `apd-domain/SKILL.md` will not exist yet — it's built in M5; the linter should warn but not error for this specific path until M5 finishes).

- [ ] **Step 2: Push**

Run: `git push origin main`

---

# M5 — Domain Pack (PBM)

Goal: assemble `domains/pbm/`, populate it with the PBM-specific content extracted in M4, generate `apd-domain/SKILL.md`, verify end-to-end.

### Task 5.1: Author `domains/pbm/domain.yaml`

**Files:**

- Create: `domains/pbm/domain.yaml`

- [ ] **Step 1: Write the metadata**

Create `domains/pbm/domain.yaml` (the content here is the same as spec §8.2):

```yaml
name: pbm
display_name: "Pharmacy Benefit Management"
version: 1.0.0
framework_compat: ">=1.0.0,<2.0.0"
description: "PBM-specialized severity rubric and pattern library. Anchored to HIPAA breach-notification thresholds, CMS Part D submission integrity, URAC accreditation requirements, and SOC 2."
includes:
  - severity-rubric.md
  - consequential-actions.md
  - immutability-classes.md
  - data-taxonomy.md
  - common-patterns/confidentiality.md
  - common-patterns/integrity.md
  - common-patterns/availability.md
  - common-patterns/distributed.md
  - common-patterns/resilient.md
  - common-patterns/ephemeral.md
  - common-patterns/authenticity.md
  - common-patterns/non-repudiation.md
  - common-patterns/immutability.md
regulatory_anchors:
  - HIPAA
  - "CMS Part D"
  - URAC
  - "SOC 2"
```

- [ ] **Step 2: Validate**

Run: `apd-gauntlet validate-domain pbm`
Expected: failure — referenced files don't exist yet.

- [ ] **Step 3: Commit anyway (file is correct; missing children land in next tasks)**

```bash
git add domains/pbm/domain.yaml
git commit -m "M5: add domains/pbm/domain.yaml (children land in subsequent tasks)"
```

---

### Task 5.2: Move PBM severity rubric to the pack

**Files:**

- Create: `domains/pbm/severity-rubric.md`

The content is the section "Severity rubric — impact-to-PBM" deleted from `apd-evidence-discipline/SKILL.md` in Task 4.3. Use git to recover it from history.

- [ ] **Step 1: Recover the section text**

Run:

```bash
git show HEAD~<N>:.claude/skills/apd-evidence-discipline/SKILL.md \
  | awk '/^## Severity rubric — impact-to-PBM/,/^## Severity calibration discipline/' \
  | sed '$d'
```

(Replace `<N>` with the offset to the commit before Task 4.3's removal.)

- [ ] **Step 2: Write `domains/pbm/severity-rubric.md`**

Open it in your editor and paste the recovered content. Prepend a top-level heading:

```markdown
# PBM Severity Rubric (impact-to-PBM)

Calibrated against impact-to-PBM, not against generic CVSS. Specialists cite the matching clause in finding `detail` fields.

[paste recovered content here, starting with "### Critical"]
```

Remove the original section's intro paragraph if it referred to "the agent" — replace with "The specialist agent" for clarity in the pack context.

- [ ] **Step 3: Commit**

```bash
git add domains/pbm/severity-rubric.md
git commit -m "M5: extract PBM severity rubric into domain pack"
```

---

### Task 5.3: Write the remaining three narrative files

**Files:**

- Create: `domains/pbm/consequential-actions.md`
- Create: `domains/pbm/immutability-classes.md`
- Create: `domains/pbm/data-taxonomy.md`

These extract content that was inline in the specialist agents (apd-non-repudiation, apd-immutability) and from the intake's PHI/PII taxonomy guidance.

- [ ] **Step 1: Author `consequential-actions.md`**

This is the "Consequential-action surface" section currently embedded in `apd-non-repudiation.md` (Task 4.8 keeps the analytical checklist but the *concrete PBM list* moves here).

Write `domains/pbm/consequential-actions.md`:

```markdown
# PBM consequential-action surface

For a PBM, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list.

- Any PHI access (read, export, print)
- Any adjudication decision (approve, deny, soft-deny)
- Any administrative configuration change (formulary, plan rules, prior authorization criteria, user role)
- Any authentication event (successful, failed, MFA challenge result)
- Any authorization decision that grants access to PHI or admin functions
- Any data export or report generation containing PHI
- Any vendor or partner API call carrying PHI
- Any change to system configuration affecting security posture
- Any break-glass or emergency override

This list is not exhaustive. Specialists should treat actions outside this list as candidates for the list — flagging them as evidence gaps until the operator confirms inclusion.
```

- [ ] **Step 2: Author `immutability-classes.md`**

Mirror of the "What must be immutable?" section in `apd-immutability.md`:

```markdown
# PBM required-immutable data classes

For a PBM, the following data classes must not change once written:

- Audit log entries (HIPAA 6-year retention, SOC 2 audit trail)
- Claim adjudication outcomes (regulatory and contractual reconcilability)
- Submitted CMS PDE records (CMS submission integrity)
- Backups (ransomware resilience)
- Configuration history (change traceability, RCA evidence)
- Signed agreements and consent records
- Member communications and notifications (proof of delivery)
- Prior authorization decisions
- Drug formulary historical state at point of adjudication

Specialists raise Immutability findings against any class on this list that has mutable storage or absent retention controls.
```

- [ ] **Step 3: Author `data-taxonomy.md`**

Write `domains/pbm/data-taxonomy.md`:

```markdown
# PBM PHI/PII data taxonomy

Specialist agents treat the following fields as PHI when they appear in artifacts. The intake brief's PHI/PII inventory MUST enumerate every field; missing fields become evidence gaps.

## PHI identifiers (45 CFR §164.514)

- member_id (HICN, MBI, PBM-internal)
- member_dob
- member_address (street, city, ZIP — full ZIP+4 is PHI)
- member_email
- member_phone
- SSN
- account numbers
- biometric identifiers

## PHI clinical data

- drug_ndc (National Drug Code)
- prescriber_npi
- pharmacy_id
- diagnosis codes (ICD-10)
- prior authorization criteria responses
- clinical notes

## PII (non-PHI personally identifying)

- internal user accounts (PBM employee identities)
- plan sponsor contact information

## Financial

- claim payment instructions
- copay calculations
- premium amounts

## Out of scope

- aggregate analytics with k-anonymity ≥ 5
- de-identified per Safe Harbor (45 CFR §164.514(b)(2))

This taxonomy is consulted by Confidentiality, Integrity, and Non-Repudiation specialists. The intake agent enumerates fields by reading artifacts against this list.
```

- [ ] **Step 4: Commit**

```bash
git add domains/pbm/consequential-actions.md domains/pbm/immutability-classes.md domains/pbm/data-taxonomy.md
git commit -m "M5: add PBM consequential-actions, immutability-classes, data-taxonomy"
```

---

### Task 5.4: Move PBM common-patterns content (×9 files)

**Files:**

- Create: `domains/pbm/common-patterns/confidentiality.md`
- Create: `domains/pbm/common-patterns/integrity.md`
- Create: `domains/pbm/common-patterns/availability.md`
- Create: `domains/pbm/common-patterns/distributed.md`
- Create: `domains/pbm/common-patterns/resilient.md`
- Create: `domains/pbm/common-patterns/ephemeral.md`
- Create: `domains/pbm/common-patterns/authenticity.md`
- Create: `domains/pbm/common-patterns/non-repudiation.md`
- Create: `domains/pbm/common-patterns/immutability.md`

For each goal, recover the "Common finding patterns" + "Common capability patterns" sections deleted from the specialist file in Task 4.8.

- [ ] **Step 1 (×9): Recover the section text per agent**

Run for each goal:

```bash
git show HEAD~<N>:.claude/agents/apd-<goal>.md \
  | awk '/^## Common finding patterns/,/^## Self-check before emitting/' \
  | sed '$d' > /tmp/<goal>-patterns.md
```

(Adjust `<N>` to the offset of the commit before Task 4.8's removal for that file.)

- [ ] **Step 2 (×9): Write the pack file with a top-level heading**

For each goal, create `domains/pbm/common-patterns/<goal>.md`:

```markdown
# PBM common patterns — <Goal>

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the PBM rubric, and NIST/ATT&CK mapping habits. The specialist agent's analytical checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

[paste recovered "Common finding patterns" + "Common capability patterns" content]
```

- [ ] **Step 3 (×9): Commit**

```bash
git add domains/pbm/common-patterns/<goal>.md
git commit -m "M5: add PBM common-patterns for <goal>"
```

Repeat for all nine.

---

### Task 5.5: Validate the pack and build the skill

**Files:**

- Create: `.claude/skills/apd-domain/SKILL.md` (generated)

- [ ] **Step 1: Validate the pack**

Run: `apd-gauntlet validate-domain pbm`
Expected: clean; all `includes` files resolve.

- [ ] **Step 2: Build the skill**

Run: `apd-gauntlet build-domain-skill pbm --framework-version 1.0.0`
Expected: writes `.claude/skills/apd-domain/SKILL.md` (~30-50 KB).

- [ ] **Step 3: Verify the generated skill has all 13 source sections**

Run: `grep -c '^## Source:' .claude/skills/apd-domain/SKILL.md`
Expected: `13` (4 narrative files + 9 common-pattern files).

- [ ] **Step 4: Verify the lint-agents check now resolves apd-domain references**

Run: `apd-gauntlet lint-agents --agent-dir .claude/agents/`
Expected: clean.

- [ ] **Step 5: Commit the generated skill**

```bash
git add .claude/skills/apd-domain/SKILL.md
git commit -m "M5: generate apd-domain/SKILL.md from PBM pack"
```

(Note: this is generated content but we ship it pre-built so the plugin payload is self-contained. M7's CI workflow regenerates it on tag pushes to guard against drift.)

- [ ] **Step 6: Push**

Run: `git push origin main`

---

# M6 — Sample Run

Goal: author a synthetic PBM tech plan + supplementary artifacts (`examples/apd-20260601-claim-event-bus/inputs/`) and curated expected outputs (`expected/`), wired into a CI integration test.

### Task 6.1: Scaffold the example directory

**Files:**

- Create: `examples/apd-20260601-claim-event-bus/README.md`
- Create: `examples/apd-20260601-claim-event-bus/inputs/.gitkeep`
- Create: `examples/apd-20260601-claim-event-bus/expected/.gitkeep`

- [ ] **Step 1: Create the directory and README**

Run:

```bash
mkdir -p examples/apd-20260601-claim-event-bus/inputs
mkdir -p examples/apd-20260601-claim-event-bus/expected
```

Create `examples/apd-20260601-claim-event-bus/README.md`:

```markdown
# APD Gauntlet Example — Claim Event Bus

A synthetic PBM tech plan exercising every framework feature without leaking real PHI or proprietary architecture. Used both as documentation (see what a run looks like) and as a CI integration test (the validator runs against `expected/` on every PR).

## Files

- `inputs/tech_plan.md` — Kafka-based claim event bus design
- `inputs/claim-events.proto` — protobuf schema with PHI fields
- `inputs/threat-model.md` — abbreviated STRIDE
- `inputs/adr-001-cap-positioning.md` — CAP-positioning decision
- `inputs/iac/kafka.tf` — Terraform stub (gives some capabilities `implemented` maturity)
- `expected/` — frozen reference outputs

## What this run demonstrates

- `disposition: blocked` with populated `prerequisite_evidence`
- Cross-tier references (tier 2 citing tier 1 findings)
- Synthesizer merge (Confidentiality + Non-Repudiation on the Kafka audit topic)
- Synthesizer link (Availability + Distributed on single-region SLO)
- Contradiction (capability claims at-rest encryption; finding disputes scope)
- High-confidence ATT&CK rationales

## Running the example

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

Exit code 0 means the example is consistent with the current schemas.

```

- [ ] **Step 2: Commit**

```bash
git add examples/apd-20260601-claim-event-bus/
git commit -m "M6: scaffold example directory with README"
```

---

### Task 6.2: Author the synthetic inputs

**Files:**

- Create: `examples/apd-20260601-claim-event-bus/inputs/tech_plan.md`
- Create: `examples/apd-20260601-claim-event-bus/inputs/claim-events.proto`
- Create: `examples/apd-20260601-claim-event-bus/inputs/threat-model.md`
- Create: `examples/apd-20260601-claim-event-bus/inputs/adr-001-cap-positioning.md`
- Create: `examples/apd-20260601-claim-event-bus/inputs/iac/kafka.tf`

Each file is a deliberate stand-in designed to exercise specific framework features. Treat each as a content-authoring task.

- [ ] **Step 1: Author `tech_plan.md` (~3-4 KB)**

Include sections: §1 Overview; §2 Goals; §3 KMS Hierarchy (mentions KMS but no rotation cadence — triggers Confidentiality `blocked`); §4 Event Bus Architecture (Kafka, broker-level encryption only — triggers Confidentiality finding); §5 Data at Rest (field-level envelope encryption for member_demographics and claims — populates a Confidentiality capability); §6 Audit Logging (writes to RDS table, no signing or chain — triggers Non-Repudiation + Immutability findings); §7 DR (states 4-hour RTO, no failover test — triggers Availability finding); §8 Multi-Region (single-region active-passive — triggers Distributed finding).

- [ ] **Step 2: Author `claim-events.proto`**

```protobuf
syntax = "proto3";
package pbm.claims.v1;

message ClaimEvent {
  string event_id      = 1;
  string member_id     = 2;   // PHI
  string drug_ndc      = 3;   // PHI clinical
  string prescriber_npi = 4;  // PHI clinical
  string pharmacy_id   = 5;   // PHI clinical
  int64  submitted_at  = 6;
  enum Status { PENDING = 0; APPROVED = 1; DENIED = 2; }
  Status status        = 7;
  string adjudication_notes = 8;
}
```

- [ ] **Step 3: Author `threat-model.md` (~2 KB)**

Brief STRIDE table covering the event bus. Include at least one threat that's already mitigated (gives Confidentiality a capability to confirm) and one that isn't (gives Confidentiality a finding).

- [ ] **Step 4: Author `adr-001-cap-positioning.md` (~1 KB)**

Captures the active-passive decision with a Consistency-over-Availability framing.

- [ ] **Step 5: Author `iac/kafka.tf` (~1 KB)**

Minimal Terraform module declaring the Kafka cluster. Include an encryption block but no key rotation. This makes the Confidentiality capability `implemented` (not just `designed`).

- [ ] **Step 6: Commit**

```bash
git add examples/apd-20260601-claim-event-bus/inputs/
git commit -m "M6: author synthetic input artifacts for the claim-event-bus example"
```

---

### Task 6.3: Author curated expected outputs

**Files:**

- Create: `examples/apd-20260601-claim-event-bus/expected/00-context/context-brief.md`
- Create: `examples/apd-20260601-claim-event-bus/expected/10-trustworthiness/<goal>.findings.yaml` (×3) and `.capabilities.yaml` (×3)
- Create: `examples/apd-20260601-claim-event-bus/expected/20-scalability/...` (×6)
- Create: `examples/apd-20260601-claim-event-bus/expected/30-auditability/...` (×6)
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/...` (8 files)

This is the longest task in M6. Author hand-curated YAML records — do NOT generate them with an LLM, because the example must be schema-stable and the validator's exit code is the test. Author against the templates and `domains/pbm/common-patterns/` calibration examples.

- [ ] **Step 1: Author the context brief**

Use `templates/context-brief.template.md` filled in for this run. The frontmatter `artifacts:` block must enumerate every file in `inputs/`.

- [ ] **Step 2: Author tier-1 outputs (6 files)**

For each goal (confidentiality, integrity, availability), write `<goal>.findings.yaml` and `<goal>.capabilities.yaml`. Target: 2-4 findings per goal (mix of severities, include at least one `blocked`), 1-2 capabilities per goal.

Generate finding IDs with: `apd-gauntlet check-ids --compute` (a helper subcommand the engineer may add — or compute manually with Python: `hashlib.sha256(f"{title}|{locator}".encode()).hexdigest()[:8]`).

- [ ] **Step 3: Author tier-2 outputs (6 files)**

For each goal (distributed, resilient, ephemeral). Some tier-2 findings cite tier-1 findings via `cross_references`.

- [ ] **Step 4: Author tier-3 outputs (6 files)**

For each goal (authenticity, non_repudiation, immutability). At least one merge candidate with a tier-1 finding (synthesis produces the merged record).

- [ ] **Step 5: Author synthesis outputs (8 files)**

- `deduped-findings.yaml` — all tier outputs combined, with one merged record carrying `lens_perspectives` and `merged_from`.
- `deduped-capabilities.yaml` — capabilities with one merged record.
- `contradictions.yaml` — at least one contradiction.
- `severity-disagreements.yaml` — at least one disagreement.
- `nist-coverage.yaml` — rollup populated.
- `attack-exposure.yaml` — rollup populated.
- `apd-coverage-matrix.yaml` — per-component, nine cells.
- `advisory-report.md` — composed from the YAML, ten sections per spec §3D.

- [ ] **Step 6: Validate**

Run: `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/`
Expected: exit 0. Iterate on any errors until clean.

- [ ] **Step 7: Commit**

```bash
git add examples/apd-20260601-claim-event-bus/expected/
git commit -m "M6: author curated expected outputs for the claim-event-bus example"
```

---

### Task 6.4: Wire into integration test

**Files:**

- Create: `tests/test_examples.py`

- [ ] **Step 1: Write the test**

Create `tests/test_examples.py`:

```python
"""Integration test: the bundled example must validate cleanly."""
from __future__ import annotations
import pathlib
import subprocess


def test_claim_event_bus_example_validates():
    repo = pathlib.Path(__file__).parent.parent
    example = repo / "examples" / "apd-20260601-claim-event-bus" / "expected"
    result = subprocess.run(
        ["apd-gauntlet", "validate", str(example)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Validation failed:\n{result.stdout}\n{result.stderr}"
```

- [ ] **Step 2: Run**

Run: `pytest tests/test_examples.py -v`
Expected: pass.

- [ ] **Step 3: Commit and push**

```bash
git add tests/test_examples.py
git commit -m "M6: add integration test running validator against bundled example"
git push origin main
```

---

# M7 — Plugin Manifest, CI, Documentation, Release

Goal: ship the distribution layer. `plugin.json`, four GitHub Actions workflows, six ADRs, complete docs set, README rewrite, CHANGELOG entry, v1.0.0 tag.

### Task 7.1: Check the Claude Code plugin manifest spec

**Files:** None (research step).

- [ ] **Step 1: Pull current plugin manifest docs**

Use Claude Code's `context7` (or equivalent) to fetch the current plugin manifest specification. Compare against the draft in spec §10.1. Record any field-name deltas.

- [ ] **Step 2: Author `plugin.json`** based on the verified spec (still substantially the spec §10.1 form). Verify it validates against whatever schema the Claude Code plugin tooling provides.

Create `plugin.json`:

```json
{
  "name": "apd-gauntlet",
  "version": "1.0.0",
  "description": "APD security architecture review framework — 9 specialist agents plus intake, orchestrator, and synthesizer.",
  "author": "APD Gauntlet contributors",
  "license": "Apache-2.0",
  "repository": "https://github.com/shoveleejoe/apd-gauntlet",
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/"
}
```

(Adjust field names if the verified spec differs.)

- [ ] **Step 3: Commit**

```bash
git add plugin.json
git commit -m "M7: add Claude Code plugin manifest"
```

---

### Task 7.2: Write `.github/workflows/validate.yml`

**Files:**

- Create: `.github/workflows/validate.yml`

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/validate.yml`:

```yaml
name: validate

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate-example:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install package
        run: pip install -e ".[dev]"
      - name: Validate bundled example
        run: apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
      - name: Validate domain pack
        run: apd-gauntlet validate-domain pbm
      - name: Meta-validate all schemas
        run: pytest tests/test_meta_schemas.py -v
```

- [ ] **Step 2: Commit and push, watch the workflow run**

```bash
git add .github/workflows/validate.yml
git commit -m "M7: add validate.yml workflow"
git push origin main
```

Confirm green on GitHub Actions.

---

### Task 7.3: Write `.github/workflows/python-tests.yml`

**Files:**

- Create: `.github/workflows/python-tests.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: python-tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check tools/ tests/
      - run: mypy tools/
      - run: pytest --cov --cov-report=term-missing
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/python-tests.yml
git commit -m "M7: add python-tests.yml workflow (pytest, ruff, mypy on py 3.10–3.12)"
git push origin main
```

---

### Task 7.4: Write `.github/workflows/markdown-lint.yml`

**Files:**

- Create: `.github/workflows/markdown-lint.yml`
- Create: `.markdownlint.json`

- [ ] **Step 1: Author markdownlint config**

Create `.markdownlint.json`:

```json
{
  "default": true,
  "MD013": false,
  "MD024": { "siblings_only": true },
  "MD033": false,
  "MD041": false
}
```

- [ ] **Step 2: Write the workflow**

```yaml
name: markdown-lint

on:
  pull_request:

jobs:
  markdownlint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: DavidAnson/markdownlint-cli2-action@v15
        with:
          globs: |
            docs/**/*.md
            .claude/**/*.md
            domains/**/*.md
            README.md
            CONTRIBUTING.md
            CHANGELOG.md
            CODE_OF_CONDUCT.md
  lint-agents:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: apd-gauntlet lint-agents --agent-dir .claude/agents/
```

- [ ] **Step 3: Commit and push**

```bash
git add .github/workflows/markdown-lint.yml .markdownlint.json
git commit -m "M7: add markdown-lint.yml workflow + markdownlint config"
git push origin main
```

---

### Task 7.5: Write `.github/workflows/release.yml`

**Files:**

- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write   # for PyPI trusted publishing
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]" build
      - run: pytest
      - run: apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
      - run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
      - name: GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*.whl
            dist/*.tar.gz
```

(Note: PyPI trusted publishing requires a one-time setup on PyPI to grant this repo permission to publish the `apd-gauntlet` package name. Document this in `docs/schema-evolution.md` as a v1.0 release prerequisite.)

- [ ] **Step 2: Commit and push (does not trigger — only tags do)**

```bash
git add .github/workflows/release.yml
git commit -m "M7: add release.yml workflow (build, PyPI publish, GitHub Release on tag)"
git push origin main
```

---

### Task 7.6: Author the six ADRs

**Files:**

- Create: `docs/adrs/0001-three-tier-structure.md`
- Create: `docs/adrs/0002-block-on-ambiguity-default.md`
- Create: `docs/adrs/0003-pluggable-domain-packs.md`
- Create: `docs/adrs/0004-json-schema-validation.md`
- Create: `docs/adrs/0005-deterministic-finding-ids.md`
- Create: `docs/adrs/0006-llm-driven-clustering.md`

Use the lightweight ADR format (~1-2 KB per file):

```markdown
# ADR-NNNN: <Title>

**Status:** Accepted
**Date:** 2026-05-24

## Context

(2-3 paragraphs on what problem this decision solves and why it came up.)

## Decision

(1-2 paragraphs stating the choice.)

## Consequences

(Bullet list of positive and negative consequences.)

## Alternatives considered

(Bullet list of options considered and why each was rejected.)
```

- [ ] **Step 1 (×6): Write each ADR**

For each, use the corresponding rationale from the design spec sections:

- 0001: spec §1, §2 "Why three tiers, why nine goals"
- 0002: spec §5 "Three load-bearing analytical disciplines" rule 2
- 0003: design conversation chunks 1+3
- 0004: design Chunk 2A + this plan M2
- 0005: spec §6.2 Pass 2 + apd-finding-schema rules
- 0006: spec §16 "Pure-LLM clustering" decision

- [ ] **Step 2: Commit (one per ADR or batch)**

```bash
git add docs/adrs/
git commit -m "M7: add ADRs 0001–0006"
```

---

### Task 7.7: Author the documentation pages

**Files:**

- Create: `docs/architecture.md`
- Create: `docs/running-the-gauntlet.md`
- Create: `docs/adapting-to-other-domains.md`
- Create: `docs/extending-agents.md`
- Create: `docs/schema-evolution.md`

For each, use the content guidance in spec §12 + the lifecycle text currently in `docs/_legacy-readme.md`.

- [ ] **Step 1: Write `docs/architecture.md` (~15 KB)**

Lift the lifecycle, discipline anchors, severity-rubric pointer, and maturity-ladder sections from `docs/_legacy-readme.md`. Add a "How the validator integrates" section pointing at M3's three passes. Reference the ADRs.

- [ ] **Step 2: Write `docs/running-the-gauntlet.md` (~10 KB)**

Operator-facing guide. Sections: Prerequisites, Installation, Setting up a run directory, Invoking the orchestrator, Interpreting outputs (advisory report + YAML), Scope hints, Troubleshooting (validator failures, blocked findings, contradictions).

- [ ] **Step 3: Write `docs/adapting-to-other-domains.md` (~8 KB)**

Codifies the §8.4 process. Walk through creating `domains/<new>/`, the required files, the framework_compat semantics, and the `validate-domain` + `build-domain-skill` workflow. End with an "Example: SaaS adaptation" sketch (not a full pack — just sketch).

- [ ] **Step 4: Write `docs/extending-agents.md` (~5 KB)**

For contributors: how to add a new specialist (would be a major-version change), how to modify boundary calls, how to update the schemas (with versioning implications).

- [ ] **Step 5: Write `docs/schema-evolution.md` (~3 KB)**

Codifies spec §13. Bullet what counts as breaking, who decides, the migration playbook for major bumps. Document the PyPI trusted-publishing setup as a one-time prerequisite for the release workflow.

- [ ] **Step 6: Commit**

```bash
git add docs/architecture.md docs/running-the-gauntlet.md docs/adapting-to-other-domains.md docs/extending-agents.md docs/schema-evolution.md
git commit -m "M7: add architecture, running-the-gauntlet, adapting-to-other-domains, extending-agents, schema-evolution docs"
```

---

### Task 7.8: Rewrite the top-level `README.md`

**Files:**

- Create: `README.md`
- Delete: `docs/_legacy-readme.md`

Target length: ~5 KB. Sections: badges (build status, license, PyPI version), Overview (3 paragraphs), Quick start (install + invoke), What it produces (1 paragraph + link to architecture.md), Documentation index (links to docs/*), Contributing (link), License.

- [ ] **Step 1: Write `README.md`**

Use the spec §1 "Context" as the basis of the Overview. Quick start:

```markdown
## Quick start

\`\`\`bash
pip install apd-gauntlet
\`\`\`

Set up a run:

\`\`\`bash
apd-gauntlet init-run apd-$(date +%Y%m%d)-<slug> --inputs <path-to-artifacts> --domain pbm
\`\`\`

Then in Claude Code, invoke the orchestrator agent against the new run directory. See [docs/running-the-gauntlet.md](docs/running-the-gauntlet.md).
```

- [ ] **Step 2: Delete the legacy README**

Run: `git rm docs/_legacy-readme.md`

- [ ] **Step 3: Commit**

```bash
git add README.md docs/_legacy-readme.md
git commit -m "M7: rewrite top-level README; remove legacy README"
```

---

### Task 7.9: Add `CONTRIBUTING.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`

**Files:**

- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `CODE_OF_CONDUCT.md`

- [ ] **Step 1: `CONTRIBUTING.md`**

Cover: how to propose changes (issue first for major); test expectations (pytest pass + ≥85% coverage); ruff + mypy clean; DCO sign-off (`git commit -s`); commit message convention (Conventional Commits suggested).

- [ ] **Step 2: `CHANGELOG.md`**

Keep-a-Changelog format with one entry:

```markdown
# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/).

## [1.0.0] - 2026-XX-XX

First public release.

### Added
- Twelve agents (orchestrator, intake, synthesizer, nine specialists) for APD security architecture reviews
- Five skills providing framework discipline, schemas, evidence rules, control mappings, and (generated) domain content
- JSON Schemas for finding, capability, contradiction, severity-disagreement, coverage-matrix, NIST coverage, ATT&CK exposure, and domain pack records
- `apd-gauntlet` Python CLI with `validate`, `init-run`, `build-domain-skill`, `summarize`, `lint-agents`, `check-ids`, `validate-domain`, and `refresh-mitre` subcommands
- Pluggable domain pack mechanism with PBM (Pharmacy Benefit Management) shipped as the first pack
- Curated synthetic claim-event-bus example with CI-validated expected outputs
- Claude Code plugin manifest
- CI workflows for validation, Python tests, markdown lint, and release
```

- [ ] **Step 3: `CODE_OF_CONDUCT.md`**

Copy the stock Contributor Covenant 2.1 text (<https://www.contributor-covenant.org/version/2/1/code_of_conduct/>).

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md CHANGELOG.md CODE_OF_CONDUCT.md
git commit -m "M7: add CONTRIBUTING, CHANGELOG, CODE_OF_CONDUCT"
```

---

### Task 7.10: Add issue templates and PR template

**Files:**

- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/domain_pack_proposal.yml`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: `bug_report.yml`** — standard structured bug-report form with fields: what happened, expected behavior, command(s) run, `apd-gauntlet --version` output, environment.

- [ ] **Step 2: `domain_pack_proposal.yml`** — form fields: pack name, target domain, regulatory anchors, severity rubric draft (or link), pattern coverage plan, why this domain needs a separate pack.

- [ ] **Step 3: `PULL_REQUEST_TEMPLATE.md`** — checklist: schema changes (require `schema_version` bump?), tests added, docs updated, `apd-gauntlet validate examples/...` clean, ruff + mypy clean, DCO sign-off.

- [ ] **Step 4: Commit**

```bash
git add .github/ISSUE_TEMPLATE/ .github/PULL_REQUEST_TEMPLATE.md
git commit -m "M7: add GitHub issue templates and PR template"
```

---

### Task 7.11: Final pre-tag checks and push

- [ ] **Step 1: Run the full test suite locally**

Run: `pytest --cov`
Expected: clean; coverage ≥85%.

- [ ] **Step 2: Run all lints**

Run:

```bash
ruff check tools/ tests/
mypy tools/
apd-gauntlet lint-agents --agent-dir .claude/agents/
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
apd-gauntlet validate-domain pbm
```

All expected: clean.

- [ ] **Step 3: Push and verify all four CI workflows green on `main`**

Run: `git push origin main`
Wait for the GitHub Actions checks to complete. Verify all green.

---

### Task 7.12: Tag v1.0.0 and publish

**Files:** None (tag + release only).

- [ ] **Step 1: Update `CHANGELOG.md` with the actual release date**

Replace `[1.0.0] - 2026-XX-XX` with today's date. Commit:

```bash
git add CHANGELOG.md
git commit -m "M7: set v1.0.0 release date in CHANGELOG"
git push origin main
```

- [ ] **Step 2: Make the repo public (one-time)**

If the repo is still private, make it public now via GitHub UI or:

```bash
gh repo edit shoveleejoe/apd-gauntlet --visibility public --accept-visibility-change-consequences
```

(Note: this is a manual decision moment — the user should confirm before going public.)

- [ ] **Step 3: Tag v1.0.0**

```bash
git tag -a v1.0.0 -m "v1.0.0 — first public release"
git push origin v1.0.0
```

- [ ] **Step 4: Confirm `release.yml` workflow succeeds**

Watch GitHub Actions. The `release` job builds the package, publishes to PyPI (assuming trusted-publishing setup is complete), and creates a GitHub Release with auto-generated notes.

- [ ] **Step 5: Smoke-test the published package**

In a fresh virtualenv:

```bash
pip install apd-gauntlet
apd-gauntlet --version
apd-gauntlet --help
```

Expected: 1.0.0; help output lists all subcommands.

---

## Verification — end of v1.0

At this point:

- Repo public at `github.com/shoveleejoe/apd-gauntlet`
- `apd-gauntlet` installable via `pip install apd-gauntlet`
- Claude Code plugin loadable from `.claude/`
- Synthetic example validates cleanly
- All four CI workflows green on `main` and on the v1.0.0 tag
- Documentation set complete with six ADRs

The framework is ready for a first round of real-world use. v1.1 work: second domain pack (`domains/saas/`), plugin marketplace publication, and any contract refinements that emerge from initial usage.

---

## Self-Review Notes (writer)

Spec-coverage scan: each spec section mapped to at least one task —

- §4 (layout) → M1
- §5 (schemas) → M2
- §6 (validator) → M3
- §7 (agent refactor) → M4
- §8 (domain pack) → M5
- §9 (sample run) → M6
- §10 (plugin) → 7.1
- §11 (CI) → 7.2–7.5
- §12 (docs) → 7.6–7.7
- §13 (versioning) → embedded in 7.5 (release workflow) + 7.7 (schema-evolution.md)
- §14 (phasing) → M1–M7 ordering
- §15 (risks) → addressed inline (e.g. 7.1 context7 check covers Risk #1)
- §17 (out of scope) → not implemented by design

Placeholder scan: no `TBD`/`TODO`/"implement later" remain. Where the plan says "use the content from spec §X" or "from `docs/_legacy-readme.md`," the source is real and accessible.

Type-consistency scan: function names — `compute_id`, `check_excerpt_length`, `check_finding_id`, `check_capability_id`, `run_schema_pass`, `run_semantic_pass`, `run_cross_file_pass`, `scaffold_run`, `build_domain_skill`, `fetch_and_project` — used consistently across all tasks that reference them. The `Violation` and `ValidationReport` dataclasses are introduced in 3.2 and referenced thereafter. Schema record kinds (`finding`, `capability`) and YAML root keys are consistent.
