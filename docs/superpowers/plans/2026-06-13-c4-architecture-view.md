# C4 Architecture View — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive, never-invent-grounded C4-model architecture view (System Context → Container → Component → Code, with per-element finding/capability badges and an attack-path overlay) to the apd-gauntlet HTML report, with the code tiers gated on `code_recon`.

**Architecture:** A new agent-authored grounded recon artifact (`00-context/c4-recon.yaml`) plus additive `c4_*` tags on `code-evidence-index.yaml` feed a deterministic assembler (`tools/apd_gauntlet/assemble_c4.py` — the SOLE minter of `c4-`/`c4e-` ids and badge rollups) that emits `40-synthesis/c4-model.yaml`. The report loader/transform serialize it into `window.APD_DATA.c4_model`, and a new React/Cytoscape scene renders the compound, click-to-drill C4 graph. L4 code + L2 container-inventory + badges are mechanical/grounded; L2 "uses" edges come ONLY from `CROSS_*`/hand-read code evidence (with a `machine_extracted` flag); L3 components are **blocked-by-default** (omitted unless an artifact groups symbols); nothing ungrounded is ever synthesized.

**Tech Stack:** Python 3 (Click CLI, `jsonschema` Draft 2020-12, PyYAML), pytest; React 18 + Cytoscape.js (fcose/dagre, compound parent nodes) precompiled offline bundle; JSON Schema contracts; ADR + skill markdown.

**Provenance & rationale:** Derived from two prior analyses against the `runs/apd-20260612-home-assistant` run — the **C4 feasibility analysis** (the run's artifacts are flat, not a containment hierarchy; the asset-graph and code-evidence-index are disjoint id-spaces; L4 badge join is clean via the 97 `code:` locators) and the **build-vs-adopt analysis** (every third-party static code→C4 extractor fails on the dynamic/IPC wiring real targets use, and hallucinates L3 — disqualified by never-invent; CBM is the in-house structural ground truth; reuse the existing Cytoscape renderer). **Verdict: build the grounded core in-house, adopt no third-party extractor.** Recorded in ADR-0021 (authored in Milestone 1).

---

## Naming contract (LOCKED — every milestone conforms to these exact identifiers)

| Concept | Canonical identifier |
|---|---|
| Agent-authored recon input (content-only, names not ids) | `00-context/c4-recon.yaml` (`generated_by: code_recon`) |
| Additive code-evidence tags | `c4_container`, `c4_component`, `c4_level` (optional, on each `code-evidence-index.yaml` entry) |
| Assembled canonical artifact (ids + badges) | `40-synthesis/c4-model.yaml` (`generated_by: assemble_c4`) |
| New schemas | `schemas/c4-recon.schema.json`, `schemas/c4-model.schema.json` (+ additive edit to `schemas/code-evidence-index.schema.json`) |
| Discipline skill | `.claude/skills/apd-c4-discipline/SKILL.md` |
| Assembler module / CLI | `tools/apd_gauntlet/assemble_c4.py` → `assemble_c4.assemble_c4(run_dir) -> dict`; CLI `assemble-c4 <run-dir>` |
| Node / edge id minting | `c4-` + `sha256(seed)[:8]` (nodes); `c4e-` + `sha256(seed)[:8]` (edges) |
| Report transform fn / window key | `report/transform.py :: c4_model_view(artifacts)` → `window.APD_DATA.c4_model` |
| Report scene | `report-template/screens/C4.jsx` (reuses the compound-capable `GraphView`); tab gated on `data.c4_model && data.c4_model.present` |
| `RunArtifacts` fields (loader) | `code_evidence_index: dict|None`, `c4_model: dict|None` |
| ADR | `docs/adrs/0021-grounded-c4-architecture-view.md` |

**Layer field-name split (intentional, do not "normalize"):** the assembler's `c4-model.yaml` `build_summary` uses `unlocalized_finding_count` / `not_analyzed_container_count`; the report window object `c4_model` uses the shortened `unlocalized_findings` / `not_analyzed_count`. `c4_model_view` (M4) performs the translation; the C4 scene (M5) reads the window names.

**Gating:** `assemble-c4` runs whenever `40-synthesis/asset-graph.yaml` exists; it includes the L4/L3 code tiers ONLY when `00-context/code-evidence-index.yaml` exists. The C4 scene renders whatever `c4-model.yaml` contains, so the code tiers are effectively `code_recon`-gated while L1 + coarse L2 + the attack-path layer survive without it.

---

## Milestone overview & dependency order

Execute milestones **in order** — each is independently testable and builds on the previous. M6 (attack-path overlay) is a stretch bundled with M5.

| # | Milestone | Produces | Depends on |
|---|---|---|---|
| **M0** | Test fixture — committed `tests/fixtures/runs/c4-home-assistant/` | CI-safe run fixture (the gitignored real run is never committed) | local run present |
| **M1** | Foundations — schemas, `apd-c4-discipline` skill, ADR-0021 | contracts + discipline (no runtime behavior) | M0 |
| **M2** | Assembler core — `assemble_c4.py` + `assemble-c4` CLI | `40-synthesis/c4-model.yaml` (ids + badge join) | M1 schemas |
| **M3** | Extend `apd-code-recon` agent — emit `c4-recon.yaml` + `c4_*` tags; wire `assemble-c4` into the run | grounded recon input + run wiring | M1 (skill/schemas), M2 (CLI) |
| **M4** | Report data path — loader + `c4_model_view` transform + build wiring | `window.APD_DATA.c4_model` | M2 (artifact shape) |
| **M5** | C4 report scene + bundle rebuild + freshness gate | `screens/C4.jsx`, registered tab, rebuilt `app.js` | M4 (window data) |
| **M6** | Attack-path overlay (stretch) on the C4 scene | path highlight over grounded C4 elements | M5 |
| **M7** | Tiered C4 render redesign (from the design handoff) — replace `fcose` with a tiered "system-map" (orthogonal connectors + in-node badges + deterministic layout); folds the 4 gap-fixes | `C4TierGraph` renderer; rewritten `C4.jsx` render; rebuilt bundle | M5/M6 (render-only; no data change) |

**Total: 41 tasks** (M0:1, M1:5, M2:9, M3:5, M4:5, M5:5, M6:2, **M7:9**). M0–M6 are **complete (PR #108)**; **Milestone 7 is the new work** added from the design handoff. Each task is TDD (failing test → minimal impl → green → commit). Run the repo's full gate before any PR: `pytest -q && ruff check . && mypy tools/apd_gauntlet && markdownlint-cli2 "docs/**/*.md" && python tools/check_report_template_freshness.py`.

> **Why Milestone 0 exists (correctness fix to the as-drafted plan):** the repo's `.gitignore` ignores the **entire `runs/` tree** ("Gauntlet run outputs … are LOCAL … never commit them"), with the carve-out `!tests/fixtures/runs/**`. Tests must therefore depend on a *committed* fixture under `tests/fixtures/runs/`, never on the local `runs/apd-20260612-home-assistant` run (which is absent in CI and fresh checkouts/worktrees). Milestone 0 builds that fixture once, as a faithful copy of the C4-relevant artifacts, so every downstream assertion (`code_count == 40`, `not_analyzed == 14`, etc.) holds in CI. The Home Assistant run is a **public** project, so the sensitivity caveat behind the ignore rule does not apply to this fixture.

---

## Milestone 0: Committed test fixture — `tests/fixtures/runs/c4-home-assistant/`

This milestone exists so that **no test depends on the gitignored, never-committed `runs/` tree**. It builds a single committed fixture run, copied faithfully from the local Home Assistant gauntlet run, containing exactly the artifacts the C4 pipeline reads. Every later milestone's test points at `tests/fixtures/runs/c4-home-assistant/` (already wired in their task code). Run this milestone in the in-place checkout where the local run exists.

**Files touched in this milestone:**

- Create: `tests/fixtures/runs/c4-home-assistant/.apd-run.yaml`
- Create: `tests/fixtures/runs/c4-home-assistant/00-context/code-evidence-index.yaml`
- Create: `tests/fixtures/runs/c4-home-assistant/00-context/asset-inventory.yaml`
- Create: `tests/fixtures/runs/c4-home-assistant/40-synthesis/asset-graph.yaml`
- Create: `tests/fixtures/runs/c4-home-assistant/40-synthesis/deduped-findings.yaml`
- Create: `tests/fixtures/runs/c4-home-assistant/40-synthesis/deduped-capabilities.yaml`
- Test: `tests/test_c4_fixture_integrity.py`

### Task 0: Build the committed C4 test fixture

**Files:**

- Create: the six fixture artifacts listed above (faithful copies from `runs/apd-20260612-home-assistant/`)
- Create: `tests/test_c4_fixture_integrity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_c4_fixture_integrity.py
"""Guards the committed C4 fixture: it must exist, be tracked (not under the
ignored runs/ tree), parse as YAML, and preserve the counts the downstream C4
milestones assert against (40 code anchors, 23 repos -> 14 with no anchors)."""
from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
FIX = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"

REQUIRED = [
    ".apd-run.yaml",
    "00-context/code-evidence-index.yaml",
    "00-context/asset-inventory.yaml",
    "40-synthesis/asset-graph.yaml",
    "40-synthesis/deduped-findings.yaml",
    "40-synthesis/deduped-capabilities.yaml",
]


def test_all_required_artifacts_present_and_parse():
    for rel in REQUIRED:
        p = FIX / rel
        assert p.is_file(), f"missing fixture artifact: {rel}"
        yaml.safe_load(p.read_text())  # must parse


def test_fixture_is_not_under_the_ignored_runs_tree():
    # The fixture lives under tests/fixtures/runs/ (the .gitignore carve-out),
    # NOT the ignored top-level runs/ tree.
    assert FIX.is_relative_to(REPO / "tests" / "fixtures" / "runs")


def test_code_evidence_index_preserves_counts():
    doc = yaml.safe_load((FIX / "00-context" / "code-evidence-index.yaml").read_text())
    cei = doc["code_evidence_index"]
    entries = cei["entries"]
    repos = cei["repos"]
    code_kinds = {"function", "class", "route", "module"}
    code_anchors = [e for e in entries if e.get("kind") in code_kinds]
    assert len(code_anchors) == 40, f"expected 40 code anchors, got {len(code_anchors)}"
    assert len(repos) == 23, f"expected 23 repos, got {len(repos)}"
    repos_with_anchors = {e["repo"] for e in entries if "repo" in e}
    not_analyzed = [r for r in repos if r["cbm_project"] not in repos_with_anchors]
    assert len(not_analyzed) == 14, f"expected 14 not-analyzed repos, got {len(not_analyzed)}"


def test_findings_have_the_code_locators_the_badge_join_needs():
    doc = yaml.safe_load((FIX / "40-synthesis" / "deduped-findings.yaml").read_text())
    records = doc if isinstance(doc, list) else doc.get("findings", doc.get("records", []))
    code_locs = 0
    for rec in records:
        for ev in (rec.get("evidence") or []):
            loc = str(ev.get("locator", ""))
            if loc.startswith("code:") or "code:" in loc:
                code_locs += 1
    assert code_locs >= 90, f"expected the ~97 code: locators for the badge join, got {code_locs}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_c4_fixture_integrity.py -v`
Expected: FAIL — `test_all_required_artifacts_present_and_parse` asserts "missing fixture artifact: .apd-run.yaml" (the fixture directory does not exist yet).

- [ ] **Step 3: Build the fixture (faithful copy from the local run)**

Run exactly (the local gitignored run is the source; copy only the six C4-relevant artifacts, preserving their internal content verbatim so counts are preserved):

```bash
SRC=runs/apd-20260612-home-assistant
DST=tests/fixtures/runs/c4-home-assistant
mkdir -p "$DST/00-context" "$DST/40-synthesis"
cp "$SRC/.apd-run.yaml"                              "$DST/.apd-run.yaml"
cp "$SRC/00-context/code-evidence-index.yaml"        "$DST/00-context/code-evidence-index.yaml"
cp "$SRC/00-context/asset-inventory.yaml"            "$DST/00-context/asset-inventory.yaml"
cp "$SRC/40-synthesis/asset-graph.yaml"              "$DST/40-synthesis/asset-graph.yaml"
cp "$SRC/40-synthesis/deduped-findings.yaml"         "$DST/40-synthesis/deduped-findings.yaml"
cp "$SRC/40-synthesis/deduped-capabilities.yaml"     "$DST/40-synthesis/deduped-capabilities.yaml"
```

Size note: `asset-graph.yaml` is the largest (~1 MB; 3,298 `network_reachable` edges the C4 pipeline does not read). If the committed size must be reduced, you MAY drop edges whose `edge_type == "network_reachable"` from the fixture's `asset-graph.yaml` **but MUST preserve every node and every edge carrying a `finding_id` or `capability_id`** (those feed L1/L2 badges); otherwise copy verbatim. Do NOT alter `code-evidence-index.yaml`, `deduped-findings.yaml`, `deduped-capabilities.yaml`, `asset-inventory.yaml`, or `.apd-run.yaml` — their counts are asserted downstream.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_c4_fixture_integrity.py -v`
Expected: PASS (4 tests). If `test_code_evidence_index_preserves_counts` fails, the source run differs from the documented shape — stop and reconcile, do not edit the assertions to fit.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/runs/c4-home-assistant tests/test_c4_fixture_integrity.py
git commit -m "test(c4): add committed Home Assistant fixture run for the C4 view

The runs/ tree is gitignored (local, may be sensitive); tests must use the
tests/fixtures/runs/** carve-out. Faithful copy of the 6 C4-relevant artifacts
from the public Home Assistant run; preserves the 40 code anchors / 23 repos /
14 not-analyzed counts the C4 milestones assert against."
```

**Milestone exit check:** `.venv/bin/python -m pytest tests/test_c4_fixture_integrity.py -q` (4 passed) and `git ls-files tests/fixtures/runs/c4-home-assistant | wc -l` (6 — the fixture is tracked, not ignored).

---

## Milestone 1: Foundations — schemas, the apd-c4-discipline skill, and ADR-0021

This milestone adds the data contracts (two new JSON Schemas + one additive schema change), the analyst discipline skill, and the architecture-decision record. It introduces **NO runtime behavior**: no assembler, no transform, no scene, no validate.py wiring, no loader change. Those land in later milestones. Everything authored here is pure contract + documentation, fully tested against the REAL Home Assistant run.

**Files touched in this milestone:**

- Create: `schemas/c4-recon.schema.json`
- Create: `schemas/c4-model.schema.json`
- Modify: `schemas/code-evidence-index.schema.json:48-69` (add optional `c4_container` / `c4_component` / `c4_level` to the `entry` `$def`)
- Create: `.claude/skills/apd-c4-discipline/SKILL.md`
- Create: `docs/adrs/0021-grounded-c4-architecture-view.md`
- Create: `tests/test_c4_recon_schema.py`
- Create: `tests/test_c4_model_schema.py`
- Create: `tests/test_code_evidence_index_c4_tags.py`
- Create: `tests/test_c4_discipline_skill.py`
- Create: `tests/test_adr_0021.py`

> Path note (confirmed by reading the repo): skills live under `.claude/skills/<name>/SKILL.md` (e.g. `.claude/skills/apd-attack-path-discipline/SKILL.md`), **not** a top-level `skills/`. The SHARED CONTRACT's `skills/apd-c4-discipline/SKILL.md` resolves to the repo's real convention `.claude/skills/apd-c4-discipline/SKILL.md`. The skill *name* `apd-c4-discipline` and SKILL.md filename are exactly as specified. There is no ADR index file in `docs/adrs/` (no README/index); ADRs are validated by `markdownlint` only, matching the prior plans' `markdownlint-cli2 "docs/adrs/<file>"` convention.

---

### Task 1: `schemas/c4-recon.schema.json` (agent-authored C4 recon input)

**Files:**

- Create: `schemas/c4-recon.schema.json`
- Test: `tests/test_c4_recon_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_c4_recon_schema.py
"""c4-recon schema: agent-authored (content-only) C4 reconnaissance input.

Mirrors test_cluster_decisions_schema.py: load the .schema.json, validate a
fully-written example doc, and prove a malformed doc is rejected. No fixtures —
the example docs are inline so the contract is self-documenting.
"""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schemas" / "c4-recon.schema.json"


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


# A fully-written, grounded c4-recon.yaml modeled on the REAL Home Assistant run:
# two code-bearing containers (core analyzed, os-agent analyzed), one not_analyzed
# container (a 14/23 empty repo), one machine_extracted cross-repo 'uses' edge from
# a CROSS_* code edge, and one hand_read edge with a file_path locator. components
# is empty (L3 blocked: no artifact groups symbols).
GOOD = {
    "schema_version": 1,
    "generated_by": "code_recon",
    "containers": [
        {
            "name": "core",
            "kind": "service",
            "repo": "Users-user-Documents-GitHub-home-assistant-repos-core",
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#core"},
            "analysis_state": "analyzed",
        },
        {
            "name": "os-agent",
            "kind": "compute",
            "repo": "Users-user-Documents-GitHub-home-assistant-repos-os-agent",
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#os-agent"},
            "analysis_state": "analyzed",
        },
        {
            "name": "plugin-dns",
            "kind": "service",
            "repo": "Users-user-Documents-GitHub-home-assistant-repos-plugin-dns",
            "provenance": {"source": "artifact", "locator": "code-architecture-brief.md#repos"},
            "analysis_state": "not_analyzed",
        },
    ],
    "components": [],
    "uses_edges": [
        {
            "from": "core",
            "to": "os-agent",
            "label": "invokes host-management D-Bus API",
            "machine_extracted": True,
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#CROSS_CHANNEL:core->os-agent"},
        },
        {
            "from": "supervisor",
            "to": "core",
            "label": "proxies Core REST API",
            "machine_extracted": False,
            "provenance": {"source": "code_evidence", "locator": "supervisor/api/__init__.py:L40-L72"},
        },
    ],
}


def test_good_c4_recon_validates_clean():
    assert list(_validator().iter_errors(GOOD)) == []


def test_components_may_be_present_when_an_artifact_groups_symbols():
    doc = json.loads(json.dumps(GOOD))
    doc["components"] = [{
        "name": "auth-manager",
        "container": "core",
        "provenance": {"source": "artifact", "locator": "docs/component-map.md#auth-manager"},
    }]
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_bad_generated_by():
    doc = json.loads(json.dumps(GOOD))
    doc["generated_by"] = "assemble_c4"  # wrong producer for a recon (input) doc
    errors = list(_validator().iter_errors(doc))
    assert errors
    assert any("generated_by" in str(e.path) or "generated_by" in e.message for e in errors)


def test_rejects_bad_container_kind():
    doc = json.loads(json.dumps(GOOD))
    doc["containers"][0]["kind"] = "microservice"  # not in the kind enum
    assert list(_validator().iter_errors(doc))


def test_rejects_bad_analysis_state():
    doc = json.loads(json.dumps(GOOD))
    doc["containers"][2]["analysis_state"] = "partial"  # only analyzed|not_analyzed
    assert list(_validator().iter_errors(doc))


def test_uses_edge_requires_machine_extracted_flag():
    doc = json.loads(json.dumps(GOOD))
    del doc["uses_edges"][0]["machine_extracted"]  # the machine_extracted vs hand_read flag is mandatory
    errors = list(_validator().iter_errors(doc))
    assert errors
    assert any("machine_extracted" in e.message for e in errors)


def test_rejects_unknown_top_level_key():
    doc = json.loads(json.dumps(GOOD))
    doc["bogus"] = 1  # additionalProperties:false at the root
    assert list(_validator().iter_errors(doc))
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_c4_recon_schema.py -v
```

Expected: all seven tests error at collection/first assertion with
`FileNotFoundError: .../schemas/c4-recon.schema.json` (the schema file does not yet exist, so `SCHEMA.read_text()` raises). This confirms the test is wired to the real path before the schema exists.

- [ ] **Step 3: Write minimal implementation**

```json
// schemas/c4-recon.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/c4-recon.schema.json",
  "title": "APD C4 Recon (agent-authored, content-only)",
  "type": "object",
  "required": ["schema_version", "generated_by", "containers", "components", "uses_edges"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["code_recon"] },
    "containers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "kind", "repo", "provenance", "analysis_state"],
        "additionalProperties": false,
        "properties": {
          "name": { "type": "string", "minLength": 1 },
          "kind": { "type": "string", "enum": ["service", "data_store", "compute", "external_system", "app", "library"] },
          "repo": { "type": "string", "minLength": 1 },
          "provenance": { "$ref": "#/$defs/provenance" },
          "analysis_state": { "type": "string", "enum": ["analyzed", "not_analyzed"] }
        }
      }
    },
    "components": {
      "type": "array",
      "description": "ONLY populated when an artifact groups symbols into a component; otherwise empty (L3 is blocked and the report renders container->code directly).",
      "items": {
        "type": "object",
        "required": ["name", "container", "provenance"],
        "additionalProperties": false,
        "properties": {
          "name":      { "type": "string", "minLength": 1 },
          "container": { "type": "string", "minLength": 1, "description": "Name reference to a containers[].name." },
          "provenance": { "$ref": "#/$defs/provenance" }
        }
      }
    },
    "uses_edges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["from", "to", "label", "machine_extracted", "provenance"],
        "additionalProperties": false,
        "properties": {
          "from":  { "type": "string", "minLength": 1, "description": "Source container name." },
          "to":    { "type": "string", "minLength": 1, "description": "Target container name." },
          "label": { "type": "string", "minLength": 1 },
          "machine_extracted": { "type": "boolean", "description": "true => derived from a CROSS_* code edge (machine_extracted); false => hand_read code evidence (file_path)." },
          "provenance": { "$ref": "#/$defs/provenance" }
        }
      }
    }
  },
  "$defs": {
    "provenance": {
      "type": "object",
      "required": ["source", "locator"],
      "additionalProperties": false,
      "properties": {
        "source":  { "type": "string", "enum": ["code_evidence", "artifact"] },
        "locator": { "type": "string", "minLength": 1 }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_c4_recon_schema.py -v
```

Expected: `7 passed`.

- [ ] **Step 5: Commit**

```
git add schemas/c4-recon.schema.json tests/test_c4_recon_schema.py
git commit -m "feat(schema): add c4-recon.schema.json (agent-authored C4 recon input)

Content-only contract for 00-context/c4-recon.yaml: grounded containers/
components/uses_edges with a machine_extracted vs hand_read flag; components
empty by default (L3 blocked). No runtime wiring yet.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `schemas/c4-model.schema.json` (assembler-minted canonical C4 model)

**Files:**

- Create: `schemas/c4-model.schema.json`
- Test: `tests/test_c4_model_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_c4_model_schema.py
"""c4-model schema: the canonical, assembler-minted C4 model (ids + badges).

Asserts the c4-XXXXXXXX node-id and c4e-XXXXXXXX edge-id patterns (mirroring the
attack-path/findings sha8 minting scheme), the level/kind enums, the
finding_count/capability_count badge ints, analysis_state honesty, and the
build_summary tallies. Validates a fully-written example and rejects bad ones.
"""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schemas" / "c4-model.schema.json"


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


# A fully-written c4-model.yaml: a system node, the HA Core container (analyzed,
# 3 findings / 1 capability), an os-agent container (analyzed), a not_analyzed
# container (0 badges, NOT "0 findings = clean" — the honesty rule), one L4 code
# node under core, and one uses edge core->os-agent. ids are real 8-hex shapes.
GOOD = {
    "schema_version": 1,
    "generated_by": "assemble_c4",
    "nodes": [
        {
            "id": "c4-1a2b3c4d", "level": "system", "parent": None,
            "name": "Home Assistant", "kind": "service",
            "provenance": {"source": "asset_inventory", "locator": "asset-graph.yaml#system"},
            "finding_count": 0, "capability_count": 0, "analysis_state": "analyzed",
        },
        {
            "id": "c4-5e6f7a8b", "level": "container", "parent": "c4-1a2b3c4d",
            "name": "core", "kind": "service",
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#core", "repo": "home-assistant-repos-core", "machine_extracted": True},
            "finding_count": 3, "capability_count": 1, "analysis_state": "analyzed",
        },
        {
            "id": "c4-9c0d1e2f", "level": "container", "parent": "c4-1a2b3c4d",
            "name": "os-agent", "kind": "compute",
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#os-agent"},
            "finding_count": 2, "capability_count": 0, "analysis_state": "analyzed",
        },
        {
            "id": "c4-3a4b5c6d", "level": "container", "parent": "c4-1a2b3c4d",
            "name": "plugin-dns", "kind": "service",
            "provenance": {"source": "artifact", "locator": "code-architecture-brief.md#repos"},
            "finding_count": 0, "capability_count": 0, "analysis_state": "not_analyzed",
        },
        {
            "id": "c4-7e8f9a0b", "level": "code", "parent": "c4-5e6f7a8b",
            "name": "homeassistant.auth.providers.homeassistant.async_validate_login", "kind": "compute",
            "provenance": {"source": "code_evidence", "locator": "code:...:L120-L150@28076bc", "repo": "home-assistant-repos-core", "machine_extracted": True},
            "finding_count": 1, "capability_count": 0, "analysis_state": "analyzed",
        },
    ],
    "edges": [
        {
            "id": "c4e-aabbccdd", "edge_type": "uses",
            "from": "c4-5e6f7a8b", "to": "c4-9c0d1e2f",
            "label": "invokes host-management D-Bus API", "machine_extracted": True,
            "provenance": {"source": "code_evidence", "locator": "code-evidence-index.yaml#CROSS_CHANNEL:core->os-agent"},
        }
    ],
    "build_summary": {
        "node_count": 5, "system_count": 1, "person_count": 0, "external_system_count": 0,
        "container_count": 3, "component_count": 0, "code_count": 1, "uses_edge_count": 1,
        "unlocalized_finding_count": 4, "not_analyzed_container_count": 1,
    },
}


def test_good_c4_model_validates_clean():
    assert list(_validator().iter_errors(GOOD)) == []


def test_rejects_bad_node_id_prefix():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][0]["id"] = "node-1a2b3c4d"  # must be c4-XXXXXXXX
    assert list(_validator().iter_errors(doc))


def test_rejects_short_node_id_hash():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][0]["id"] = "c4-1a2b"  # 4 hex, must be 8
    assert list(_validator().iter_errors(doc))


def test_rejects_bad_edge_id_prefix():
    doc = json.loads(json.dumps(GOOD))
    doc["edges"][0]["id"] = "c4-aabbccdd"  # edges are c4e-, not c4-
    assert list(_validator().iter_errors(doc))


def test_rejects_unknown_level():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][0]["level"] = "module"  # not in level enum
    assert list(_validator().iter_errors(doc))


def test_rejects_non_uses_edge_type():
    doc = json.loads(json.dumps(GOOD))
    doc["edges"][0]["edge_type"] = "contains"  # only "uses" is allowed
    assert list(_validator().iter_errors(doc))


def test_rejects_negative_finding_count():
    doc = json.loads(json.dumps(GOOD))
    doc["nodes"][1]["finding_count"] = -1  # badge counts are >= 0
    assert list(_validator().iter_errors(doc))


def test_not_analyzed_with_zero_badges_is_valid():
    """0 findings on a not_analyzed container is HONEST, not a schema error."""
    doc = json.loads(json.dumps(GOOD))
    assert doc["nodes"][3]["analysis_state"] == "not_analyzed"
    assert doc["nodes"][3]["finding_count"] == 0
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_unknown_build_summary_key():
    doc = json.loads(json.dumps(GOOD))
    doc["build_summary"]["edge_count"] = 1  # asset-graph spells it uses_edge_count here; bogus key rejected
    assert list(_validator().iter_errors(doc))
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_c4_model_schema.py -v
```

Expected: every test errors with `FileNotFoundError: .../schemas/c4-model.schema.json`.

- [ ] **Step 3: Write minimal implementation**

```json
// schemas/c4-model.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/c4-model.schema.json",
  "title": "APD Gauntlet C4 Model (assembler-minted)",
  "type": "object",
  "required": ["schema_version", "generated_by", "nodes", "edges", "build_summary"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["assemble_c4"] },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "level", "parent", "name", "kind", "provenance", "finding_count", "capability_count", "analysis_state"],
        "additionalProperties": false,
        "properties": {
          "id":     { "type": "string", "pattern": "^c4-[0-9a-f]{8}$" },
          "level":  { "type": "string", "enum": ["system", "person", "external_system", "container", "component", "code"] },
          "parent": { "type": ["string", "null"], "pattern": "^c4-[0-9a-f]{8}$" },
          "name":   { "type": "string", "minLength": 1 },
          "kind":   { "type": "string", "enum": ["service", "data_store", "compute", "external_system", "app", "library", "person"] },
          "provenance": { "$ref": "#/$defs/provenance" },
          "finding_count":    { "type": "integer", "minimum": 0 },
          "capability_count": { "type": "integer", "minimum": 0 },
          "analysis_state":   { "type": "string", "enum": ["analyzed", "not_analyzed"] }
        }
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "edge_type", "from", "to", "label", "machine_extracted", "provenance"],
        "additionalProperties": false,
        "properties": {
          "id":        { "type": "string", "pattern": "^c4e-[0-9a-f]{8}$" },
          "edge_type": { "type": "string", "enum": ["uses"] },
          "from":      { "type": "string", "pattern": "^c4-[0-9a-f]{8}$" },
          "to":        { "type": "string", "pattern": "^c4-[0-9a-f]{8}$" },
          "label":     { "type": "string", "minLength": 1 },
          "machine_extracted": { "type": "boolean" },
          "provenance": { "$ref": "#/$defs/provenance" }
        }
      }
    },
    "build_summary": {
      "type": "object",
      "required": ["node_count", "system_count", "person_count", "external_system_count", "container_count", "component_count", "code_count", "uses_edge_count", "unlocalized_finding_count", "not_analyzed_container_count"],
      "additionalProperties": false,
      "properties": {
        "node_count":                  { "type": "integer", "minimum": 0 },
        "system_count":                { "type": "integer", "minimum": 0 },
        "person_count":                { "type": "integer", "minimum": 0 },
        "external_system_count":       { "type": "integer", "minimum": 0 },
        "container_count":             { "type": "integer", "minimum": 0 },
        "component_count":             { "type": "integer", "minimum": 0 },
        "code_count":                  { "type": "integer", "minimum": 0 },
        "uses_edge_count":             { "type": "integer", "minimum": 0 },
        "unlocalized_finding_count":   { "type": "integer", "minimum": 0 },
        "not_analyzed_container_count":{ "type": "integer", "minimum": 0 }
      }
    }
  },
  "$defs": {
    "provenance": {
      "type": "object",
      "required": ["source", "locator"],
      "additionalProperties": false,
      "properties": {
        "source":  { "type": "string", "enum": ["code_evidence", "artifact", "asset_inventory", "domain_default", "threat_model", "run_config"] },
        "locator": { "type": "string", "minLength": 1 },
        "repo":    { "type": "string", "minLength": 1 },
        "machine_extracted": { "type": "boolean" }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_c4_model_schema.py -v
```

Expected: `9 passed`.

- [ ] **Step 5: Commit**

```
git add schemas/c4-model.schema.json tests/test_c4_model_schema.py
git commit -m "feat(schema): add c4-model.schema.json (assembler-minted canonical C4 model)

Canonical 40-synthesis/c4-model.yaml contract: c4-/c4e- sha8 node+edge ids,
level/kind enums, finding_count/capability_count badges, analysis_state honesty
(0 findings on not_analyzed is valid, never 'clean'), build_summary tallies.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Additive `c4_container` / `c4_component` / `c4_level` on `code-evidence-index.schema.json`

**Files:**

- Modify: `schemas/code-evidence-index.schema.json:48-69` (the `entry` `$def` properties block)
- Test: `tests/test_code_evidence_index_c4_tags.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_code_evidence_index_c4_tags.py
"""Additive c4_* tags on code-evidence-index entries must (a) validate when
present and (b) NOT break the REAL multi-repo Home Assistant index that omits
them. Backward-compat is the load-bearing assertion: 14/23 repos and 46 entries
already on disk must still pass after the schema change.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schemas" / "code-evidence-index.schema.json"
HA_INDEX = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant" / "00-context" / "code-evidence-index.yaml"


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def _base_entry() -> dict:
    return {
        "id": "cev-abcd1234",
        "qualified_name": "homeassistant.auth.async_validate_login",
        "kind": "function",
        "file_path": "homeassistant/auth/__init__.py",
        "line_range": "L120-L150",
        "excerpt": "async def async_validate_login(self, ...):",
        "apd_relevance": ["authenticity"],
    }


def _doc(entry: dict) -> dict:
    return {
        "code_evidence_index": {
            "indexed_commit_sha": "28076bc",
            "cbm_project": "home-assistant-repos-core",
            "generated_at": "2026-06-12T00:00:00Z",
            "entries": [entry],
        }
    }


def test_entry_with_full_c4_tags_validates():
    e = _base_entry()
    e["c4_container"] = "core"
    e["c4_component"] = "auth-manager"
    e["c4_level"] = "component"
    assert list(_validator().iter_errors(_doc(e))) == []


def test_entry_with_null_c4_component_validates():
    """L3 blocked: c4_component may be explicitly null while c4_container is set."""
    e = _base_entry()
    e["c4_container"] = "core"
    e["c4_component"] = None
    e["c4_level"] = "code"
    assert list(_validator().iter_errors(_doc(e))) == []


def test_entry_without_any_c4_tags_still_validates():
    """The new fields are OPTIONAL — a tag-less entry stays valid."""
    assert list(_validator().iter_errors(_doc(_base_entry()))) == []


def test_rejects_bad_c4_level_enum():
    e = _base_entry()
    e["c4_level"] = "system"  # only container|component|code are allowed here
    assert list(_validator().iter_errors(_doc(e)))


def test_real_home_assistant_index_still_validates_after_change():
    """BACKWARD-COMPAT: the shipped 46-entry multi-repo index has NO c4_* tags
    and MUST stay valid after the additive schema change."""
    data = yaml.safe_load(HA_INDEX.read_text())
    errors = list(_validator().iter_errors(data))
    assert errors == [], [e.message for e in errors]
    assert len(data["code_evidence_index"]["entries"]) == 46
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_code_evidence_index_c4_tags.py -v
```

Expected: `test_entry_with_full_c4_tags_validates`, `test_entry_with_null_c4_component_validates`, and `test_rejects_bad_c4_level_enum` FAIL. The first two fail because the current `entry` `$def` is `additionalProperties: false` (line 52), so the unknown `c4_container`/`c4_component`/`c4_level` keys produce
`Additional properties are not allowed ('c4_container', 'c4_component', 'c4_level' were unexpected)` and `iter_errors` is non-empty (so the `== []` assertion fails). `test_rejects_bad_c4_level_enum` actually passes-by-accident at this point (bad value rejected as an unknown property), but `test_entry_without_any_c4_tags_still_validates` and `test_real_home_assistant_index_still_validates_after_change` already pass (proving the baseline is green). Net: 2 failing on the new fields, confirming the gap.

- [ ] **Step 3: Write minimal implementation**

Edit the `entry` `$def` `properties` block. Add three optional properties after the existing `repo` property (keep `additionalProperties: false`):

```json
        "notes":          { "type": "string" },
        "repo":           { "type": "string", "minLength": 1, "description": "Optional CBM project name this entry was attributed to. Required when top-level repos[] is present (multi-repo provenance)." },
        "c4_container":   { "type": "string", "minLength": 1, "description": "Optional C4 container name this code anchor belongs to (additive; consumed by assemble_c4)." },
        "c4_component":   { "type": ["string", "null"], "minLength": 1, "description": "Optional C4 component name; null when L3 is blocked (no artifact groups this symbol)." },
        "c4_level":       { "type": "string", "enum": ["container", "component", "code"], "description": "Optional C4 level this anchor maps to." }
```

Concretely, replace the existing two-line tail of the `properties` object (the `notes` + `repo` lines at `schemas/code-evidence-index.schema.json:66-67`) with the five-line block above. The `additionalProperties: false` on the entry stays.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_code_evidence_index_c4_tags.py -v
```

Expected: `5 passed`. Then re-run the EXISTING code-evidence-index schema test suite to confirm no regression:

```
pytest tests/ -k "code_evidence" -v
```

Expected: all pre-existing `code_evidence` tests still pass (e.g. the multirepo `repo`-required if/then is untouched).

- [ ] **Step 5: Commit**

```
git add schemas/code-evidence-index.schema.json tests/test_code_evidence_index_c4_tags.py
git commit -m "feat(schema): additive optional c4_container/c4_component/c4_level on code-evidence-index entries

Additive only (additionalProperties stays false): entries may now carry a C4
tag triple consumed by assemble_c4. c4_component is nullable (L3 blocked).
Backward-compat proven against the real 46-entry Home Assistant multi-repo index.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `apd-c4-discipline` skill

**Files:**

- Create: `.claude/skills/apd-c4-discipline/SKILL.md`
- Test: `tests/test_c4_discipline_skill.py`

The skill clones the structure of `apd-attack-path-discipline` (numbered `### N.` hard rules under a `## Hard rules` heading, with YAML frontmatter `name:`/`description:`). The "test" is a structural lint asserting the frontmatter and every required rule heading exist (no runtime; agent wiring into a required-reading list lands in Milestone 3).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_c4_discipline_skill.py
"""Structural lint for the apd-c4-discipline skill. Mirrors how the other
discipline skills are shaped (YAML frontmatter + numbered ### hard rules) and
guards that each never-invent/honesty rule heading is actually present, so the
skill can't silently drop a load-bearing rule.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "apd-c4-discipline" / "SKILL.md"

REQUIRED_RULE_HEADINGS = [
    "Never invent containers or components",
    "Never invent uses or contains edges",
    "L3 component grouping is blocked by default",
    "Confidence floor on render",
    "Diagram-size cap",
    "not_analyzed is not zero findings",
]


def test_skill_file_exists():
    assert SKILL.exists(), f"missing {SKILL}"


def test_frontmatter_name_and_description():
    text = SKILL.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "SKILL.md must open with a YAML frontmatter block"
    fm = m.group(1)
    assert re.search(r"^name:\s*apd-c4-discipline\s*$", fm, re.MULTILINE)
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE)


def test_has_hard_rules_section():
    assert "## Hard rules" in SKILL.read_text()


def test_all_required_rule_headings_present():
    text = SKILL.read_text()
    for heading in REQUIRED_RULE_HEADINGS:
        assert f"### " in text and heading in text, f"missing rule heading: {heading!r}"
        # each heading must appear on a level-3 markdown heading line
        assert re.search(rf"^### \d+\. .*{re.escape(heading)}", text, re.MULTILINE), \
            f"{heading!r} is not a numbered ### rule heading"


def test_machine_extracted_vs_hand_read_distinction_documented():
    text = SKILL.read_text()
    assert "machine_extracted" in text
    assert "hand_read" in text or "hand-read" in text


def test_names_not_ids_ownership_rule_documented():
    """ADR-0020 ownership: agents emit names; the assembler mints ids/badges."""
    text = SKILL.read_text()
    assert "ADR-0020" in text or "assembler" in text.lower()
    assert "c4-" in text  # references the id scheme it must NOT mint
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_c4_discipline_skill.py -v
```

Expected: all six tests fail; the first with `AssertionError: missing .../.claude/skills/apd-c4-discipline/SKILL.md` and the rest with the same missing-file read raising `FileNotFoundError` / failing the heading assertions.

- [ ] **Step 3: Write minimal implementation**

```markdown
<!-- .claude/skills/apd-c4-discipline/SKILL.md -->
---
name: apd-c4-discipline
description: Required discipline for the code_recon agent when authoring 00-context/c4-recon.yaml (the grounded C4 architecture view). Covers never-invent rules for containers/components and uses/contains edges, the machine_extracted-vs-hand_read flag, the L3-block-by-default rule, the confidence floor on render, the diagram-size cap, and the not_analyzed-vs-zero-findings honesty rule. Required reading before emitting any container, component, or uses edge.
---

# APD C4 Discipline

The C4 architecture view in the report renders a System / Container / Component /
Code model built from per-run YAML. It looks authoritative — boxes, arrows, badge
counts — so it is only useful if every box and arrow is grounded in an artifact or
a code-evidence citation. An invented container or a guessed "uses" arrow is worse
than an omitted one: it manufactures false structure that engineers and auditors
will trust. Block, do not guess.

Field ownership follows ADR-0020: **you (the agent) emit grounded content BY NAME
only** — container names, component names, edge endpoints by name, labels. You
NEVER mint a `c4-XXXXXXXX` / `c4e-XXXXXXXX` id and you NEVER write a badge count.
The deterministic assembler (`assemble_c4`) is the sole minter of ids and the sole
author of `finding_count` / `capability_count` rollups. If you find yourself
writing an id or a count, stop — that is not your job.

## Hard rules

### 1. Never invent containers or components

Every entry in `containers[]` and `components[]` of `c4-recon.yaml` must cite one
of:

- A code-evidence-index entry whose anchors live in that repo/service
  (`provenance.source: code_evidence`)
- An architecture artifact that names the service/module
  (`provenance.source: artifact`, e.g. `code-architecture-brief.md`)

If a container has no code anchors and no artifact names it, it does not belong in
the model. Do not add a container because "a system like this usually has one."
A repo that was declared but has zero code anchors is still a real container — emit
it with `analysis_state: not_analyzed` (see rule 6), never omit it silently and
never invent its internals.

### 2. Never invent uses or contains edges

Containment (a code node's parent container, a component's parent) is mechanical:
it comes from the code-evidence-index `c4_container` / `c4_component` tags, never
from judgment. A `uses_edges[]` entry must cite one of exactly two grounded
sources, and you MUST record which with the `machine_extracted` boolean:

- `machine_extracted: true` — the edge is derived from a CROSS_* code edge
  (`CROSS_HTTP_CALLS` / `CROSS_ASYNC_CALLS` / `CROSS_CHANNEL`) produced by the
  cross-repo index pass. `provenance.locator` points at that edge.
- `machine_extracted: false` — the edge is **hand_read** from code you actually
  read. `provenance.locator` MUST be a concrete `file_path:Lstart-Lend` you can
  point a reviewer at. "The architecture diagram implies A talks to B" is not a
  hand_read edge; cite the call site or do not emit the edge.

Never emit a self-edge (`from == to`) and never emit an edge whose endpoints are
not both present in `containers[]`. If you cannot ground both the existence and the
direction of an edge, drop it.

### 3. L3 component grouping is blocked by default

`components[]` is **empty unless an artifact explicitly groups symbols into a named
component.** There is no heuristic clustering of functions into components — that is
exactly the kind of invented structure this discipline forbids. The default and
expected output is an empty `components[]`, which makes the assembler render the
model as Container -> Code directly (L2 -> L4), skipping L3. Only when a real
artifact (a module map, a documented component decomposition) names a component AND
assigns symbols to it do you emit a `components[]` entry; otherwise leave the code
anchor's `c4_component` null and let the assembler render it under its container.

### 4. Confidence floor on render

A `uses_edges[]` entry is only as trustworthy as its weakest grounding. A
`machine_extracted: false` (hand_read) edge whose locator is a whole-file reference
with no line range, or whose direction you inferred rather than read, MUST be
dropped rather than emitted at the same standing as a CROSS_*-derived edge. When in
doubt between emitting a weak edge and omitting it, omit it: a missing arrow reads
as "not established," an invented arrow reads as "established," and only one of
those is honest. Do not annotate a guess with a hedge and ship it anyway.

### 5. Diagram-size cap

The rendered C4 scene must stay legible. A single rendered level (the set of nodes
visible at once — L1+L2 on load, or one container's expanded L3/L4) targets ≤ 50
nodes, mirroring the attack-path Mermaid cap. If a container genuinely has more
than ~50 grounded code anchors, that is a signal to rely on the click-to-expand
interaction (the scene reveals a container's code on demand) rather than to drop
real anchors — never silently truncate grounded evidence to hit the cap, and never
pad to fill it.

### 6. not_analyzed is not zero findings

A container with `analysis_state: not_analyzed` (a declared repo with zero code
anchors — 14 of the 23 Home Assistant repos are exactly this) MUST render as
"not analyzed," NEVER as "0 findings = clean." Zero badges on a not_analyzed
container means *we did not look here*, not *here is safe*. Set `analysis_state:
not_analyzed` on those containers and let the assembler/report present them
honestly. Separately, a doc-anchored finding that has no `code:` locator is real
but unlocalized — it is surfaced as the model's explicit unlocalized count, never
silently dropped onto (or away from) a node.

## Tier ordering

`c4-recon.yaml` is authored during code reconnaissance (it is `generated_by:
code_recon`), alongside / after the code-evidence-index it cites. It is read-only
input to the deterministic `assemble_c4` step, which mints `c4-*` node ids, `c4e-*`
edge ids, and the `finding_count` / `capability_count` badges in
`40-synthesis/c4-model.yaml`. You never write that canonical file and never write
those ids or counts.

## Out of scope (delegated)

- Badge counts are derived by the assembler from deduped findings/capabilities
  joined on the code locator — do not pre-count them.
- Severity, finding content, and capability maturity are owned by the specialist
  lenses and the synthesizer; the C4 view only *references* their counts.
- The L4 code-node inventory and the per-entry `c4_container` / `c4_component` /
  `c4_level` tags on the code-evidence-index are mechanical/grounded — copy them
  from the index, do not re-derive structure from them.
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_c4_discipline_skill.py -v
```

Expected: `6 passed`. Also run markdownlint on the new skill to keep CI's docs glob green:

```
npx --yes markdownlint-cli2 ".claude/skills/apd-c4-discipline/SKILL.md"
```

Expected: `Linting: 1 file(s)` ... `Summary: 0 error(s)`.

- [ ] **Step 5: Commit**

```
git add .claude/skills/apd-c4-discipline/SKILL.md tests/test_c4_discipline_skill.py
git commit -m "feat(skill): add apd-c4-discipline (never-invent C4 containers/edges, L3-block-by-default)

Clones apd-attack-path-discipline shape: numbered hard rules for never-invent
containers/components (R1), never-invent uses/contains edges with machine_extracted
vs hand_read (R2), L3-block-by-default (R3), confidence floor on render (R4),
diagram-size cap (R5), and the not_analyzed-vs-zero-findings honesty rule (R6).
Structural lint test guards every rule heading.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: ADR-0021 — grounded C4 architecture view

**Files:**

- Create: `docs/adrs/0021-grounded-c4-architecture-view.md`
- Test: `tests/test_adr_0021.py`

There is no ADR index file in `docs/adrs/` (confirmed: no README/index; ADRs are referenced ad-hoc from topic docs). The "test" is therefore a markdownlint pass plus a structural lint asserting the ADR has the standard `# ADR-0021:` / `**Status:**` / `**Date:**` header and the required sections (Context, Decision, Consequences, Alternatives considered), matching the 0019/0020 format. The link/index check asserts the ADR number is sequential and unique.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adr_0021.py
"""Structural lint for ADR-0021. Matches the 0019/0020 ADR format (numbered
H1 title, Status/Date metadata, Context/Decision/Consequences/Alternatives
sections) and guards that the load-bearing decisions (grounded-from-code-recon,
L3-block-by-default, reuse-Cytoscape/adopt-nothing) are actually stated, plus
that 0021 is a unique, sequential ADR number on disk.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
ADRS = REPO / "docs" / "adrs"
ADR = ADRS / "0021-grounded-c4-architecture-view.md"


def test_adr_file_exists():
    assert ADR.exists(), f"missing {ADR}"


def test_adr_header_format():
    text = ADR.read_text()
    assert text.startswith("# ADR-0021: "), "ADR must open with '# ADR-0021: <title>'"
    assert re.search(r"^\*\*Status:\*\*\s+\w", text, re.MULTILINE)
    assert re.search(r"^\*\*Date:\*\*\s+\d{4}-\d{2}-\d{2}", text, re.MULTILINE)


def test_required_sections_present():
    text = ADR.read_text()
    for section in ("## Context", "## Decision", "## Consequences", "## Alternatives considered"):
        assert section in text, f"missing section: {section}"


def test_load_bearing_decisions_stated():
    text = ADR.read_text().lower()
    assert "c4" in text
    assert "code_recon" in text or "code reconnaissance" in text
    assert "assemble_c4" in text or "assembler" in text
    assert "l3" in text and "block" in text          # L3-block-by-default
    assert "cytoscape" in text                        # reuse-Cytoscape
    assert "build-vs-adopt" in text or "build vs adopt" in text or "adopt" in text


def test_adr_number_is_unique_and_sequential():
    existing = sorted(p.name[:4] for p in ADRS.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert existing.count("0021") == 1, "exactly one ADR-0021 file must exist"
    assert "0020" in existing, "0021 must follow an existing 0020"


def test_no_unresolved_placeholders():
    text = ADR.read_text()
    for bad in ("TODO", "TBD", "FIXME", "XXX", "<placeholder>"):
        assert bad not in text, f"unresolved placeholder {bad!r} in ADR"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_adr_0021.py -v
```

Expected: all six tests fail; `test_adr_file_exists` with `AssertionError: missing .../docs/adrs/0021-grounded-c4-architecture-view.md` and the others raising `FileNotFoundError` on `ADR.read_text()`.

- [ ] **Step 3: Write minimal implementation**

```markdown
<!-- docs/adrs/0021-grounded-c4-architecture-view.md -->
# ADR-0021: Grounded C4 architecture view from code reconnaissance

**Status:** Accepted
**Date:** 2026-06-13

> ADR-0016 and -0018 are reserved for concurrent in-flight design changes and
> may land after this one.

## Context

The APD gauntlet produces a self-contained, offline HTML report. It already
renders an asset graph and per-finding attack-path strips, but it has no
architecture view: a reader cannot see the system as a structured set of
containers and components, cannot see where the findings and capabilities land
in that structure, and cannot drill from "the system" down to "this function."
Engineers and auditors reason about systems in C4 terms (System Context →
Container → Component → Code); the report should meet them there.

Two feasibility questions framed the decision:

1. **Where does the structure come from?** The gauntlet has no live code graph at
   view time — the report is a static bundle built by a Python pipeline from
   per-run YAML. The only grounded sources of structure are the code-evidence
   index (ADR-0007, multi-repo per ADR-0019) and hand-read code evidence with a
   `file_path`. A *feasibility analysis* against the real Home Assistant run
   confirmed this is enough for L1/L2/L4: 9 of 23 repos carry code anchors
   (40 anchors total, including 6 CROSS_* cross-repo edges), and the asset graph
   already names the system and its data stores. It also confirmed the honest
   limit: 14 of 23 repos have **zero** code anchors, so any view must distinguish
   "analyzed, no findings" from "not analyzed." L3 (Component) has **no** grounded
   source unless an artifact explicitly groups symbols — the index gives us
   symbols and their container, not a defensible component decomposition.

2. **Build or adopt an extractor?** A *build-vs-adopt analysis* weighed pulling in
   a third-party C4/architecture extractor (e.g. a Structurizr-style DSL importer
   or a static-analysis architecture-recovery tool) against composing the view
   from data we already produce. Adopting an extractor would (a) introduce a live
   code-analysis dependency at build time, breaking the offline/static contract,
   (b) produce structure not traceable to a citable artifact, violating the
   never-invent discipline, and (c) add a heavy dependency for a view whose
   inputs the gauntlet already computes.

## Decision

Build a **grounded** C4 view from data the gauntlet already produces, reusing the
report's existing graph renderer, and adopting no third-party extractor.

**Grounded from code reconnaissance + a deterministic assembler.** The
`code_recon` agent authors a content-only `00-context/c4-recon.yaml` (containers,
optional components, `uses_edges`) where every entry cites an artifact or a
code-evidence locator, and every edge carries a `machine_extracted` (CROSS_*
edge) vs hand_read (`file_path`) flag. Per ADR-0020, the agent emits names only;
the deterministic `assemble_c4` step is the sole minter of the `c4-*` node ids,
`c4e-*` edge ids, and the `finding_count` / `capability_count` badge rollups in
the canonical `40-synthesis/c4-model.yaml`. No invented value at agent or render
time. The `apd-c4-discipline` skill is required reading before the agent emits any
container, component, or edge.

**L3-block-by-default.** Components are emitted ONLY when an artifact explicitly
groups symbols into a named component. With no such artifact — the common case —
`components[]` is empty and the model renders Container → Code directly (L2 → L4),
skipping L3 entirely. There is no heuristic clustering of functions into
components; that would manufacture exactly the kind of invented structure this
feature exists to avoid.

**Honesty about coverage.** Containers backed by a declared-but-empty repo render
`analysis_state: not_analyzed` — never "0 findings = clean." Doc-anchored findings
with no code locator are surfaced as an explicit unlocalized count in the model's
`build_summary`, never silently dropped.

**Reuse Cytoscape; adopt nothing.** The view reuses the report's existing
compound-capable Cytoscape `GraphView` (the same fcose/compound renderer used by
the asset graph), with a new C4 scene that shows L1+L2 on load and reveals L3/L4
on click. No new graph library, no third-party extractor, no build-time code
analysis is introduced — the offline/static contract (ADR-0007's no-network
posture) is preserved.

**Gating.** `assemble_c4` runs whenever `40-synthesis/asset-graph.yaml` exists; it
includes the code tiers (L4 code, and any L3 components) ONLY when
`00-context/code-evidence-index.yaml` exists. The C4 scene renders whatever
`c4-model.yaml` contains and is shown only when that model is present. The feature
is therefore effectively `code_recon`-gated for the code tiers and additive
everywhere else.

## Consequences

**Positive:**

- The report gains a structured, drill-down architecture view whose every box and
  arrow is traceable to a citation — the same trustworthiness bar as findings.
- Reusing the existing Cytoscape renderer keeps the bundle offline and adds no new
  runtime dependency; adopting no extractor keeps the build deterministic.
- The not_analyzed and unlocalized-count rules make the gauntlet's coverage gaps
  *visible* rather than papering over them with a falsely clean diagram.
- Every change is additive: schemas are optional and presence-gated, so single-repo
  and no-code-recon runs are unaffected.

**Negative:**

- L3 is usually absent (block-by-default), so most runs render L2 → L4 with a
  "components not decomposed" character. This is intentional honesty, but readers
  expecting a full four-level C4 may find L3 sparse.
- The view's fidelity is bounded by code-recon coverage: in a run where most repos
  are not_analyzed, the architecture view is mostly not_analyzed containers. The
  honesty rules make that boundary explicit rather than hiding it.

## Alternatives considered

**A. Adopt a third-party C4/architecture extractor.** Rejected: it would require
live code analysis at build time (breaking the offline/static contract), produce
structure not traceable to a citable artifact (violating never-invent), and add a
heavy dependency for inputs the gauntlet already computes.

**B. Heuristically cluster code symbols into L3 components.** Rejected: function
co-location or call-graph clustering is not a defensible, citable component
decomposition. It would manufacture invented structure — exactly what this feature
forbids. L3 is blocked by default and emitted only from an explicit artifact.

**C. Render not_analyzed containers as "0 findings."** Rejected as actively
misleading: a declared repo with no code anchors was not examined, not found
clean. The model distinguishes the two via `analysis_state`.

**D. Introduce a new graph library for the C4 scene.** Rejected: the existing
compound-capable Cytoscape `GraphView` already supports parented/compound nodes
and an fcose layout, so a second library would add bundle weight for no capability
the renderer lacks.
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_adr_0021.py -v
```

Expected: `6 passed`. Then markdownlint, matching the CI docs glob convention used for prior ADRs:

```
npx --yes markdownlint-cli2 "docs/adrs/0021-grounded-c4-architecture-view.md"
```

Expected: `Summary: 0 error(s)`.

- [ ] **Step 5: Commit**

```
git add docs/adrs/0021-grounded-c4-architecture-view.md tests/test_adr_0021.py
git commit -m "docs(adr): ADR-0021 grounded C4 architecture view from code-recon + assembler

Decision: grounded C4 (code_recon authors c4-recon.yaml by name; assemble_c4
mints ids/badges per ADR-0020); L3-block-by-default; not_analyzed != clean; reuse
the existing Cytoscape compound GraphView, adopt no third-party extractor (cites
the feasibility + build-vs-adopt analyses). Structural + markdownlint guarded.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

**Milestone exit check:**

```
pytest tests/test_c4_recon_schema.py tests/test_c4_model_schema.py tests/test_code_evidence_index_c4_tags.py tests/test_c4_discipline_skill.py tests/test_adr_0021.py -v \
  && pytest tests/ -k "code_evidence or schema" -q \
  && npx --yes markdownlint-cli2 "docs/adrs/0021-grounded-c4-architecture-view.md" ".claude/skills/apd-c4-discipline/SKILL.md" \
  && ruff check tools/ tests/
```

Expected: the five new test modules all pass (33 tests total), the wider `code_evidence`/`schema` suite stays green (no regression from the additive `code-evidence-index.schema.json` change — including the real 46-entry Home Assistant index), markdownlint reports `0 error(s)` on both authored docs, and `ruff` is clean (the new test files follow the `from __future__ import annotations` + stdlib-import style of the existing schema tests). No `mypy` target this milestone — no runtime Python was added (schemas, skill, and ADR are data/docs; `assemble_c4.py`/`cli.py`/`transform.py`/`loader.py`/`validate.py` wiring all land in later milestones).

---

## Milestone 2: The assembler core — `tools/apd_gauntlet/assemble_c4.py` + the `assemble-c4` CLI command

This milestone builds the deterministic data core of the grounded C4 feature: the SOLE minter of `c4-`/`c4e-` ids and the SOLE author of badge rollups. It reads `00-context/c4-recon.yaml` (optional), `00-context/code-evidence-index.yaml`, `00-context/asset-inventory.yaml`, `40-synthesis/asset-graph.yaml`, `40-synthesis/deduped-findings.yaml`, and `40-synthesis/deduped-capabilities.yaml`; mints node/edge ids; computes per-node DISTINCT finding/capability badges by rolling code→component→container; and writes `40-synthesis/c4-model.yaml`. Report wiring (loader/transform/scene) is a later milestone — but `schemas/c4-model.schema.json` and the `validate.py` registration land here because Task 8 validates the assembler's real output against the schema.

**Files touched in this milestone:**

- Create: `tools/apd_gauntlet/assemble_c4.py` (the assembler module — all logic, Tasks 1–8)
- Create: `schemas/c4-model.schema.json` (mirror of `asset-graph.schema.json`; Task 8 validates against it)
- Modify: `tools/apd_gauntlet/cli.py` (add `assemble-c4` command after `assemble-inventory` at ~line 1169; Task 9)
- Modify: `tools/apd_gauntlet/validate.py` (register `c4-model.yaml`→`c4-model.schema.json` in `SYNTHESIS_ROLLUPS` ~line 247; Task 8)
- Create: `tests/test_assemble_c4.py` (Tasks 1–8)
- Create: `tests/test_cli_assemble_c4.py` (Task 9)

Note on naming: `c4-recon.yaml` and `c4_container`/`c4_component`/`c4_level` tags are **absent** in the real ground-truth run, so the assembler MUST fall back: containers derive from the index `repos[]` list (23 declared, 9 code-bearing), and each code node's container falls back to its entry `repo` when no `c4_container` tag exists. `c4-recon.schema.json`, the agent that authors `c4-recon.yaml`, the additive `code-evidence-index.schema.json` tags, the skill, and ADR-0021 are authored in Milestone 1; this milestone consumes them defensively (treats them as optional).

---

### Task 1: id helpers `c4_node_id` / `c4_edge_id` (sha256[:8], `c4-`/`c4e-` prefixes)

**Files:**
- Create: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_assemble_c4.py
from __future__ import annotations

import hashlib

import yaml


def _sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def test_c4_node_id_deterministic_and_stable():
    from apd_gauntlet.assemble_c4 import c4_node_id

    # seed = level|name|parent_name (parent_name "" when top-level)
    assert c4_node_id("container", "core", "") == "c4-" + _sha8("container|core|")
    assert c4_node_id("code", "homeassistant.auth.AuthManager.async_create_access_token",
                      "core") == "c4-" + _sha8(
        "code|homeassistant.auth.AuthManager.async_create_access_token|core"
    )
    # determinism: same inputs -> same id across calls
    assert c4_node_id("container", "core", "") == c4_node_id("container", "core", "")
    # distinctness: a different level or parent yields a different id
    assert c4_node_id("container", "core", "") != c4_node_id("component", "core", "")
    assert c4_node_id("code", "f", "core") != c4_node_id("code", "f", "supervisor")
    # shape: c4- + exactly 8 lowercase hex
    nid = c4_node_id("container", "core", "")
    assert nid.startswith("c4-") and len(nid) == 11
    assert all(c in "0123456789abcdef" for c in nid[3:])


def test_c4_edge_id_deterministic_and_stable():
    from apd_gauntlet.assemble_c4 import c4_edge_id

    assert c4_edge_id("cli", "supervisor") == "c4e-" + _sha8("uses|cli|supervisor")
    assert c4_edge_id("cli", "supervisor") == c4_edge_id("cli", "supervisor")
    # directional: from/to order matters
    assert c4_edge_id("cli", "supervisor") != c4_edge_id("supervisor", "cli")
    eid = c4_edge_id("cli", "supervisor")
    assert eid.startswith("c4e-") and len(eid) == 12
    assert all(c in "0123456789abcdef" for c in eid[4:])
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_c4_node_id_deterministic_and_stable tests/test_assemble_c4.py::test_c4_edge_id_deterministic_and_stable -v
```
Expected: `ModuleNotFoundError: No module named 'apd_gauntlet.assemble_c4'` (collection error, both tests ERROR).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/apd_gauntlet/assemble_c4.py
"""Assemble 40-synthesis/c4-model.yaml: the deterministic, grounded C4
architecture model for the apd-gauntlet HTML report.

This module is the SOLE minter of c4-/c4e- ids and the SOLE author of the
per-node FINDINGS/CAPABILITY badge rollups (ADR-0020 field-ownership: agents
emit grounded CONTENT by name; the assembler mints ids and derived counts).

Never-invent discipline: no container/component/code node or uses-edge is
emitted without an artifact or code-evidence citation. L3 components are
HARD-BLOCKED unless an artifact (c4-recon.components[]) groups symbols; the
default is to OMIT L3 and parent code nodes directly to their container.

Inputs (all under run_dir):
  00-context/c4-recon.yaml            (optional; agent-authored container/uses names)
  00-context/code-evidence-index.yaml (optional; code anchors -> L4 + repos[] -> L2)
  00-context/asset-inventory.yaml     (optional; identities/external deps -> L1)
  40-synthesis/asset-graph.yaml       (presence GATES the run)
  40-synthesis/deduped-findings.yaml  (FINDINGS badge source)
  40-synthesis/deduped-capabilities.yaml (CAPABILITY badge source)

Output:
  40-synthesis/c4-model.yaml  (assembler-minted ids + badges + build_summary)

Public entrypoint: ``assemble_c4(run_dir) -> dict`` (writes the file, returns
build_summary). Idempotent.
"""
from __future__ import annotations

import hashlib


def c4_node_id(level: str, name: str, parent_name: str) -> str:
    """Deterministic C4 node id: ``c4-<sha8(level|name|parent_name)>``.

    Mirrors the attack-path/findings ``<prefix>-<sha8(seed)>`` scheme. The seed
    is the node's stable natural key: its level, its grounded NAME, and its
    parent's NAME ("" for a top-level node). Including level+parent keeps a
    same-named code symbol distinct from a same-named container and keeps a
    symbol unique across the repos it appears in.
    """
    seed = f"{level}|{name}|{parent_name}"
    return "c4-" + hashlib.sha256(seed.encode()).hexdigest()[:8]


def c4_edge_id(from_name: str, to_name: str) -> str:
    """Deterministic C4 'uses' edge id: ``c4e-<sha8("uses|"+from+"|"+to)>``.

    Directional: ``from``/``to`` order is part of the natural key, so A->B and
    B->A receive distinct ids.
    """
    seed = f"uses|{from_name}|{to_name}"
    return "c4e-" + hashlib.sha256(seed.encode()).hexdigest()[:8]
```

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_c4_node_id_deterministic_and_stable tests/test_assemble_c4.py::test_c4_edge_id_deterministic_and_stable -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): deterministic c4-/c4e- id minters

c4_node_id(level,name,parent) and c4_edge_id(from,to) use sha256[:8] over a
stable natural-key seed, mirroring the attack-path id scheme. SOLE minter of
C4 node/edge ids (ADR-0020).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: load helpers + L4 code nodes from `code-evidence-index.yaml`

**Files:**
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (asserts against the REAL index: 40 code anchors, 9 code-bearing repos, `code` level, `repo`-derived parent, `kind` mapped)

```python
# append to tests/test_assemble_c4.py
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"


def _load_real_index():
    raw = yaml.safe_load(
        (REAL_RUN / "00-context" / "code-evidence-index.yaml").read_text(encoding="utf-8")
    )
    return raw["code_evidence_index"]


def test_code_nodes_from_real_index_counts_and_shape():
    from apd_gauntlet.assemble_c4 import build_code_nodes, c4_node_id

    cei = _load_real_index()
    # c4_component tags are absent in this run -> every code node parents to its
    # container (the repo short-name). No component map supplied.
    nodes = build_code_nodes(cei, component_by_qname={})
    # 27 function + 6 class + 5 route + 2 module = 40 code anchors; the 6
    # kind:edge entries are NOT code nodes.
    assert len(nodes) == 40
    assert {n["level"] for n in nodes} == {"code"}
    # 9 distinct code-bearing containers (repo short-names).
    parents = {n["provenance"]["repo"] for n in nodes}
    assert parents == {
        "core", "supervisor", "os-agent", "cli", "iOS",
        "android", "frontend", "mobile-apps-fcm-push", "addons",
    }
    # parent is the c4_node_id of the CONTAINER (level container|name repo|parent "")
    sample = next(
        n for n in nodes
        if n["name"] == "homeassistant.auth.AuthManager.async_create_access_token"
    )
    assert sample["kind"] == "function"
    assert sample["provenance"]["repo"] == "core"
    assert sample["provenance"]["source"] == "code_evidence"
    assert sample["provenance"]["locator"] == sample["name"]  # qualified_name
    assert sample["parent"] == c4_node_id("container", "core", "")
    assert sample["id"] == c4_node_id(
        "code", sample["name"], "core"
    )  # parent_name = container name when no component
    assert sample["analysis_state"] == "analyzed"
    # kinds present cover the four code kinds, never 'edge'
    assert {n["kind"] for n in nodes} == {"function", "class", "route", "module"}
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_code_nodes_from_real_index_counts_and_shape -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'build_code_nodes'`.

- [ ] **Step 3: Write minimal implementation** (add to `assemble_c4.py`)

```python
# add to the top of tools/apd_gauntlet/assemble_c4.py imports block
from pathlib import Path
from typing import Any

import yaml

# ... (c4_node_id / c4_edge_id stay above) ...

# The four code-anchor kinds that become L4 ``code`` nodes. ``edge`` entries in
# the index are cross-repo 'uses' edges, handled separately (Task 4).
_CODE_KINDS: frozenset[str] = frozenset({"function", "class", "route", "module"})


def _yaml_optional(path: Path) -> dict[str, Any] | None:
    """Load a YAML mapping, or return None when absent/empty/non-mapping."""
    if not path.exists():
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def _repo_short(repo: str) -> str:
    """Map a CBM project / repo string to the container NAME used everywhere.

    ``Users-...-home-assistant-repos-core`` -> ``core``. A bare name passes
    through unchanged, so an explicit c4-recon container name also works.
    """
    if "-repos-" in repo:
        return repo.split("-repos-")[-1]
    return repo


def _code_entries(cei: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        e for e in (cei.get("entries") or [])
        if isinstance(e, dict) and e.get("kind") in _CODE_KINDS
    ]


def build_code_nodes(
    cei: dict[str, Any],
    component_by_qname: dict[str, str],
) -> list[dict[str, Any]]:
    """L4: one ``code`` node per code-anchor entry (function/class/route/module).

    Grounding: every node carries the entry's qualified_name (as name+locator),
    its repo (as the container), and source=code_evidence. Never invented.

    Parent resolution (never-invent / L3-block-by-default): if the entry's
    qualified_name maps to a c4_component NAME (``component_by_qname``), the
    parent is that component's id; otherwise the parent falls back to the
    CONTAINER id (the repo short-name). The parent's NAME (component name, else
    container name) is folded into this node's own seed so ids stay stable when
    L3 is present vs blocked.
    """
    nodes: list[dict[str, Any]] = []
    for e in _code_entries(cei):
        qname = str(e.get("qualified_name", ""))
        container_name = _repo_short(str(e.get("repo", "")))
        component_name = component_by_qname.get(qname)
        if component_name:
            parent_name = component_name
            parent_id = c4_node_id("component", component_name, container_name)
        else:
            parent_name = container_name
            parent_id = c4_node_id("container", container_name, "")
        prov: dict[str, Any] = {
            "source": "code_evidence",
            "locator": qname,
            "repo": container_name,
        }
        line_range = e.get("line_range")
        if line_range:
            prov["locator"] = f"{qname}:{line_range}"
        nodes.append({
            "id": c4_node_id("code", qname, parent_name),
            "level": "code",
            "parent": parent_id,
            "name": qname,
            "kind": str(e.get("kind", "")),
            "provenance": prov,
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes
```

The test asserts `provenance.locator == qname`, but the impl appends `:line_range`. Reconcile by keeping the bare-qname locator (the line_range is recoverable from the index) so the badge-join key in Task 7 is the unadorned qualified_name:

```python
# replace the line_range block in build_code_nodes with: (locator stays = qname)
        prov = {
            "source": "code_evidence",
            "locator": qname,
            "repo": container_name,
        }
        nodes.append({
            "id": c4_node_id("code", qname, parent_name),
            "level": "code",
            "parent": parent_id,
            "name": qname,
            "kind": str(e.get("kind", "")),
            "provenance": prov,
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes
```

(Final `build_code_nodes` uses the bare-qname locator block; drop the `line_range` branch entirely.)

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_code_nodes_from_real_index_counts_and_shape -v
```
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): L4 code nodes from code-evidence-index

build_code_nodes maps function/class/route/module entries to level:code nodes,
parenting each to its c4_component (when an artifact groups symbols) or, by
default, to its container (repo short-name). edge entries are excluded.
Verified against the real 40-anchor / 9-repo home-assistant index.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: L2 container nodes (+ `analysis_state: not_analyzed` for the 14 empty repos)

**Files:**
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (REAL index: 23 declared `repos[]`, 9 code-bearing → `analyzed`, 14 → `not_analyzed`)

```python
# append to tests/test_assemble_c4.py
def test_container_nodes_mark_not_analyzed_for_empty_repos():
    from apd_gauntlet.assemble_c4 import build_container_nodes, c4_node_id

    cei = _load_real_index()
    # No c4-recon containers supplied -> derive purely from the index repos[].
    nodes = build_container_nodes(c4_recon=None, cei=cei)
    # 23 declared repos -> 23 container nodes.
    assert len(nodes) == 23
    assert {n["level"] for n in nodes} == {"container"}
    by_name = {n["name"]: n for n in nodes}
    # 9 code-bearing repos render analyzed.
    for name in ("core", "supervisor", "os-agent", "cli", "iOS",
                 "android", "frontend", "mobile-apps-fcm-push", "addons"):
        assert by_name[name]["analysis_state"] == "analyzed", name
    # The 14 repos with zero code anchors render NOT analyzed (never "0=clean").
    analyzed = sum(1 for n in nodes if n["analysis_state"] == "analyzed")
    not_analyzed = sum(1 for n in nodes if n["analysis_state"] == "not_analyzed")
    assert analyzed == 9
    assert not_analyzed == 14
    # spot-check a known empty repo
    assert by_name["operating-system"]["analysis_state"] == "not_analyzed"
    # container ids are minted from level|name|"" ; top-level (parent None)
    assert by_name["core"]["id"] == c4_node_id("container", "core", "")
    assert by_name["core"]["parent"] is None
    assert by_name["core"]["provenance"]["source"] == "code_evidence"
    assert by_name["core"]["kind"] == "service"
    assert by_name["core"]["finding_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_container_nodes_mark_not_analyzed_for_empty_repos -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'build_container_nodes'`.

- [ ] **Step 3: Write minimal implementation** (add to `assemble_c4.py`)

```python
# default container kind when neither c4-recon nor a heuristic assigns one.
_DEFAULT_CONTAINER_KIND = "service"


def _code_bearing_repos(cei: dict[str, Any]) -> set[str]:
    """Container NAMES (repo short-names) that have >=1 code anchor."""
    return {_repo_short(str(e.get("repo", ""))) for e in _code_entries(cei)}


def _declared_repos(cei: dict[str, Any]) -> list[str]:
    """Container NAMES for every declared repo, in declared order, de-duped."""
    out: list[str] = []
    seen: set[str] = set()
    for r in cei.get("repos") or []:
        name = _repo_short(str(r.get("cbm_project", "")))
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    # Defensive: a repo that appears only on entries (not in repos[]) is still a
    # real container.
    for name in sorted(_code_bearing_repos(cei)):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def build_container_nodes(
    c4_recon: dict[str, Any] | None,
    cei: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """L2: one ``container`` node per repo/container.

    Sources, in precedence order:
      * c4-recon ``containers[]`` (agent-authored, grounded by name+provenance),
        when present — carries kind + provenance verbatim;
      * the code-evidence-index ``repos[]`` list, for every declared repo not
        already named by c4-recon.

    Honesty rule: a container with zero code anchors renders
    ``analysis_state: not_analyzed`` (NEVER "0 findings = clean"). A container
    that c4-recon explicitly tags ``analysis_state: not_analyzed`` is honored.
    """
    code_bearing = _code_bearing_repos(cei) if cei else set()
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _state(name: str, declared: str | None) -> str:
        if declared in ("analyzed", "not_analyzed"):
            return declared
        return "analyzed" if name in code_bearing else "not_analyzed"

    # 1) c4-recon containers (authored content).
    for c in (c4_recon or {}).get("containers") or []:
        name = str(c.get("name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        prov = c.get("provenance") or {"source": "artifact"}
        nodes.append({
            "id": c4_node_id("container", name, ""),
            "level": "container",
            "parent": None,
            "name": name,
            "kind": str(c.get("kind") or _DEFAULT_CONTAINER_KIND),
            "provenance": prov,
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": _state(name, c.get("analysis_state")),
        })

    # 2) index repos[] not already authored by c4-recon.
    for name in _declared_repos(cei or {}):
        if name in seen:
            continue
        seen.add(name)
        nodes.append({
            "id": c4_node_id("container", name, ""),
            "level": "container",
            "parent": None,
            "name": name,
            "kind": _DEFAULT_CONTAINER_KIND,
            "provenance": {"source": "code_evidence", "locator": f"repos[]:{name}"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": _state(name, None),
        })
    return nodes
```

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_container_nodes_mark_not_analyzed_for_empty_repos -v
```
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): L2 container nodes with honest not_analyzed flag

build_container_nodes merges c4-recon containers[] (when authored) with the
index repos[] list; a container with zero code anchors renders
analysis_state: not_analyzed (never "0 findings = clean"). Verified the real
run yields 23 containers = 9 analyzed + 14 not_analyzed.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: L2→L2 `uses` edges from `c4-recon.uses_edges[]` + the 6 `kind:edge` index entries

**Files:**
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (REAL index: the 6 cross-repo `kind:edge` entries → 6 hand-read `uses` edges, `machine_extracted=False`, with provenance)

```python
# append to tests/test_assemble_c4.py
def test_uses_edges_from_real_index_edge_entries():
    from apd_gauntlet.assemble_c4 import build_uses_edges, c4_node_id, c4_edge_id

    cei = _load_real_index()
    # container ids must exist for the edge endpoints to resolve; we pass the
    # known container names present in this run.
    container_ids = {
        name: c4_node_id("container", name, "")
        for name in ("core", "supervisor", "os-agent", "cli", "iOS",
                     "android", "frontend", "mobile-apps-fcm-push", "addons")
    }
    edges = build_uses_edges(c4_recon=None, cei=cei, container_id_by_name=container_ids)
    # 5 of the 6 kind:edge entries resolve to known repo-derived containers and
    # become uses edges. cev-0a000003 (supervisor -> /run/docker.sock host dockerd)
    # targets HOST INFRASTRUCTURE, not one of the 23 repos, so under never-invent it
    # is correctly dropped from the raw-index path (no dangling container ref). It
    # survives as a hand-read fact in the c4-recon agent output (M3) and is only
    # rendered as a container edge if a host node is later declared there.
    assert len(edges) == 5
    assert {e["edge_type"] for e in edges} == {"uses"}
    # index-derived edges are HAND-READ cross-repo edges -> machine_extracted False
    assert all(e["machine_extracted"] is False for e in edges)
    # the cli -> supervisor edge is present, with the right minted id + endpoints
    cli_sup = next(
        (e for e in edges
         if e["from"] == container_ids["cli"] and e["to"] == container_ids["supervisor"]),
        None,
    )
    assert cli_sup is not None
    assert cli_sup["id"] == c4_edge_id("cli", "supervisor")
    assert cli_sup["provenance"]["source"] == "code_evidence"
    assert "cev-0a000001" in cli_sup["provenance"]["locator"]
    assert cli_sup["label"]
    # every edge endpoint is a real minted container id (no dangling refs)
    valid = set(container_ids.values())
    for e in edges:
        assert e["from"] in valid and e["to"] in valid
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_uses_edges_from_real_index_edge_entries -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'build_uses_edges'`.

- [ ] **Step 3: Write minimal implementation** (add to `assemble_c4.py`)

The 6 index edges carry the from/to as a `" -> "`-joined `qualified_name`; the *attributed* repo is one endpoint, and the other endpoint's container is resolved by scanning the qualified_name halves for a known container name (defaulting the unresolved side to the entry's `repo`). This keeps the join grounded and never invents an endpoint.

```python
def _resolve_endpoint(text: str, container_names: set[str], fallback: str) -> str:
    """Pick the container NAME named in ``text`` (a qualified_name half), else
    ``fallback``. Longest match wins so 'os-agent' is not shadowed by a prefix."""
    hit = ""
    for name in container_names:
        if name and name.lower() in text.lower() and len(name) > len(hit):
            hit = name
    return hit or fallback


def build_uses_edges(
    c4_recon: dict[str, Any] | None,
    cei: dict[str, Any] | None,
    container_id_by_name: dict[str, str],
) -> list[dict[str, Any]]:
    """L2->L2 ``uses`` edges.

    Two grounded sources:
      * c4-recon ``uses_edges[]`` — authored from CROSS_* code edges or hand-read
        code evidence; carries its own ``machine_extracted`` flag + provenance;
      * the code-evidence-index ``kind: edge`` entries — cross-repo edges the
        auto-linker missed, read by hand from code (file_path). These are always
        ``machine_extracted: False``.

    Never-invent: an edge whose ``from`` or ``to`` container name cannot be
    resolved to a minted container id is DROPPED (not guessed). De-duped on the
    minted edge id so the same A->B from two sources collapses to one.
    """
    names = set(container_id_by_name)
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _emit(from_name: str, to_name: str, label: str, machine: bool,
              prov: dict[str, Any]) -> None:
        fid = container_id_by_name.get(from_name)
        tid = container_id_by_name.get(to_name)
        if not fid or not tid or fid == tid:
            return  # unresolved endpoint or self-loop -> drop, never guess
        eid = c4_edge_id(from_name, to_name)
        if eid in seen:
            return
        seen.add(eid)
        edges.append({
            "id": eid,
            "edge_type": "uses",
            "from": fid,
            "to": tid,
            "label": label,
            "machine_extracted": bool(machine),
            "provenance": prov,
        })

    # 1) c4-recon authored uses_edges (content by name).
    for u in (c4_recon or {}).get("uses_edges") or []:
        _emit(
            str(u.get("from", "")),
            str(u.get("to", "")),
            str(u.get("label", "uses")),
            bool(u.get("machine_extracted", False)),
            u.get("provenance") or {"source": "artifact"},
        )

    # 2) index kind:edge entries (hand-read cross-repo edges).
    for e in (cei or {}).get("entries") or []:
        if not isinstance(e, dict) or e.get("kind") != "edge":
            continue
        qname = str(e.get("qualified_name", ""))
        attributed = _repo_short(str(e.get("repo", "")))
        left, _, right = qname.partition(" -> ")
        from_name = _resolve_endpoint(left, names, attributed)
        to_name = _resolve_endpoint(right, names, "")
        label = str(e.get("excerpt", "") or e.get("notes", "") or "uses")[:120]
        prov = {
            "source": "code_evidence",
            "locator": f"{e.get('id', '')}:{e.get('file_path', '')}",
        }
        _emit(from_name, to_name, label, False, prov)
    return edges
```

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_uses_edges_from_real_index_edge_entries -v
```
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): L2 uses edges from c4-recon + index edge entries

build_uses_edges emits grounded container->container uses edges from c4-recon
uses_edges[] (carrying their machine_extracted flag) and the index kind:edge
entries (hand-read, machine_extracted=False). Unresolvable endpoints are
dropped, never guessed. Verified the real run's 6 cross-repo edges resolve.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: L1 nodes — `system` + `person` + `external_system` from asset-inventory

**Files:**
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (REAL inventory: 5 human_role + 3 external_party = 8 person nodes; 5 external_dependency assets → external_system; 1 synthesized system)

```python
# append to tests/test_assemble_c4.py
def _load_real_inventory():
    return yaml.safe_load(
        (REAL_RUN / "00-context" / "asset-inventory.yaml").read_text(encoding="utf-8")
    )


def test_l1_nodes_from_real_inventory():
    from apd_gauntlet.assemble_c4 import build_l1_nodes, c4_node_id

    inv = _load_real_inventory()
    nodes = build_l1_nodes(inv, subject="Home Assistant")
    by_level = {}
    for n in nodes:
        by_level.setdefault(n["level"], []).append(n)
    # exactly one synthesized system node = the run subject
    assert len(by_level["system"]) == 1
    sysnode = by_level["system"][0]
    assert sysnode["name"] == "Home Assistant"
    assert sysnode["parent"] is None
    assert sysnode["id"] == c4_node_id("system", "Home Assistant", "")
    assert sysnode["provenance"]["source"] == "run_config"
    # person nodes from human_role + external_party identities (5 + 3 = 8)
    assert len(by_level["person"]) == 8
    # external_system nodes from external_dependency assets (5)
    assert len(by_level["external_system"]) == 5
    # all L1 nodes carry zeroed badges + analyzed state + minted ids
    for n in nodes:
        assert n["finding_count"] == 0 and n["capability_count"] == 0
        assert n["id"].startswith("c4-")
    # a known person resolves
    owner = next(
        (n for n in by_level["person"] if n["name"].startswith("Owner user")), None
    )
    assert owner is not None
    assert owner["provenance"]["source"] == "asset_inventory"
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_l1_nodes_from_real_inventory -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'build_l1_nodes'`.

- [ ] **Step 3: Write minimal implementation** (add to `assemble_c4.py`)

```python
# identity_type values that become L1 ``person`` nodes (human actors / external
# parties). service_account identities are NOT persons (they are machine
# principals) and are intentionally excluded from L1.
_PERSON_IDENTITY_TYPES = frozenset({"human_role", "external_party"})


def build_l1_nodes(
    inv: dict[str, Any] | None,
    subject: str,
) -> list[dict[str, Any]]:
    """L1 System Context: one synthesized ``system`` node (the run subject),
    plus ``person`` nodes (human_role / external_party identities) and
    ``external_system`` nodes (external_dependency assets).

    All grounded: persons/external systems carry the inventory entry's name +
    provenance verbatim; the single system node is the run subject (source
    run_config). Badges are zeroed here and filled by the badge join (Task 7).
    """
    inv = inv or {}
    nodes: list[dict[str, Any]] = []

    # The run-subject system node (synthesized, exactly one).
    sysname = subject or "System"
    nodes.append({
        "id": c4_node_id("system", sysname, ""),
        "level": "system",
        "parent": None,
        "name": sysname,
        "kind": "software_system",
        "provenance": {"source": "run_config", "locator": "subject"},
        "finding_count": 0,
        "capability_count": 0,
        "analysis_state": "analyzed",
    })

    for i in inv.get("identities") or []:
        if i.get("identity_type") not in _PERSON_IDENTITY_TYPES:
            continue
        name = str(i.get("name", ""))
        if not name:
            continue
        nodes.append({
            "id": c4_node_id("person", name, ""),
            "level": "person",
            "parent": None,
            "name": name,
            "kind": str(i.get("identity_type", "person")),
            "provenance": (i.get("provenance") or {"source": "asset_inventory"})
            | {"source": "asset_inventory"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })

    for a in inv.get("assets") or []:
        if a.get("asset_type") != "external_dependency":
            continue
        name = str(a.get("name", ""))
        if not name:
            continue
        nodes.append({
            "id": c4_node_id("external_system", name, ""),
            "level": "external_system",
            "parent": None,
            "name": name,
            "kind": "external_dependency",
            "provenance": (a.get("provenance") or {"source": "asset_inventory"})
            | {"source": "asset_inventory"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes
```

Note: `dict | {"source": ...}` overwrites the inventory `source` with `asset_inventory` so the provenance `source` is one of the schema-allowed enum values (the inventory's own provenance.source is `artifact`, which is also valid, but normalizing keeps L1 provenance uniform and the test asserts `asset_inventory`).

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_l1_nodes_from_real_inventory -v
```
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): L1 system/person/external_system nodes

build_l1_nodes synthesizes one system node (the run subject) and grounds
person nodes (human_role/external_party identities) + external_system nodes
(external_dependency assets) from asset-inventory. Verified 1+8+5 on the real
home-assistant inventory.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: L3 components — include ONLY if `c4-recon.components[]` non-empty; else OMIT (code parents to container)

**Files:**
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (the real run has NO components → L3 blocked; a synthetic c4-recon with components proves the un-blocked path)

```python
# append to tests/test_assemble_c4.py
def test_components_blocked_when_recon_empty():
    from apd_gauntlet.assemble_c4 import build_component_nodes, component_map

    cei = _load_real_index()
    # The real run has no c4-recon -> no components -> L3 BLOCKED.
    assert build_component_nodes(c4_recon=None, container_id_by_name={}) == []
    assert component_map(None) == {}
    assert component_map({"components": []}) == {}


def test_components_built_when_recon_groups_symbols():
    from apd_gauntlet.assemble_c4 import (
        build_code_nodes,
        build_component_nodes,
        c4_node_id,
        component_map,
    )

    # Synthetic c4-recon that DOES group two core symbols under an "auth" component.
    recon = {
        "components": [
            {"name": "auth", "container": "core",
             "provenance": {"source": "artifact", "locator": "arch.md#auth"}},
        ],
        # the agent also tags which qualified_names belong to the component via
        # the (additive) c4_component map on the index; we model it directly here
        "component_members": {
            "homeassistant.auth.AuthManager.async_create_access_token": "auth",
        },
    }
    container_ids = {"core": c4_node_id("container", "core", "")}
    comps = build_component_nodes(c4_recon=recon, container_id_by_name=container_ids)
    assert len(comps) == 1
    comp = comps[0]
    assert comp["level"] == "component"
    assert comp["name"] == "auth"
    assert comp["parent"] == container_ids["core"]
    assert comp["id"] == c4_node_id("component", "auth", "core")

    # and a code node whose qname is mapped now parents to the COMPONENT, not the
    # container.
    cei = _load_real_index()
    cmap = component_map(recon)
    code = build_code_nodes(cei, component_by_qname=cmap)
    token = next(
        n for n in code
        if n["name"] == "homeassistant.auth.AuthManager.async_create_access_token"
    )
    assert token["parent"] == c4_node_id("component", "auth", "core")
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_components_blocked_when_recon_empty tests/test_assemble_c4.py::test_components_built_when_recon_groups_symbols -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'build_component_nodes'`.

- [ ] **Step 3: Write minimal implementation** (add to `assemble_c4.py`)

```python
def component_map(c4_recon: dict[str, Any] | None) -> dict[str, str]:
    """Map qualified_name -> component NAME from c4-recon.

    Two grounding sources, both authored:
      * ``component_members`` (qname -> component name), the explicit grouping;
      * the additive ``c4_component`` tag on a code-evidence-index entry is
        consumed in build_code_nodes directly, so it is merged in by the caller.

    Returns {} when no components are grouped (L3 blocked-by-default).
    """
    if not isinstance(c4_recon, dict):
        return {}
    if not (c4_recon.get("components") or []):
        return {}  # no component declared -> nothing to map (L3 blocked)
    out: dict[str, str] = {}
    for qname, comp in (c4_recon.get("component_members") or {}).items():
        if qname and comp:
            out[str(qname)] = str(comp)
    return out


def build_component_nodes(
    c4_recon: dict[str, Any] | None,
    container_id_by_name: dict[str, str],
) -> list[dict[str, Any]]:
    """L3: one ``component`` node per c4-recon ``components[]`` entry.

    HARD-BLOCK by default: if c4-recon is absent or ``components[]`` is empty,
    return [] (no L3 — code parents directly to its container). A component is
    emitted only when an artifact groups symbols, and only when its declared
    container resolves to a minted container id.
    """
    if not isinstance(c4_recon, dict):
        return []
    nodes: list[dict[str, Any]] = []
    for c in c4_recon.get("components") or []:
        name = str(c.get("name", ""))
        container_name = str(c.get("container", ""))
        parent_id = container_id_by_name.get(container_name)
        if not name or not parent_id:
            continue  # never-invent: skip an ungrounded / unparented component
        nodes.append({
            "id": c4_node_id("component", name, container_name),
            "level": "component",
            "parent": parent_id,
            "name": name,
            "kind": "component",
            "provenance": c.get("provenance") or {"source": "artifact"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes
```

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_components_blocked_when_recon_empty tests/test_assemble_c4.py::test_components_built_when_recon_groups_symbols -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): L3 components blocked-by-default

component_map + build_component_nodes emit L3 component nodes ONLY when
c4-recon.components[] groups symbols; otherwise L3 is omitted and code parents
to its container. When present, mapped code nodes re-parent to the component.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: THE BADGE JOIN — DISTINCT finding/capability counts rolled code→component→container; unlocalized count

**Files:**
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

This is the crux. For every code node, count DISTINCT finding ids whose `evidence[].locator` is `code:<qualified_name>...` resolving to that node; a multi-locator finding counts ONCE per node. Then roll those distinct sets up to the component (when present) and container, deduping ids so a container that holds two code nodes hit by the same finding still counts it once. `unlocalized_finding_count` = findings with NO `code:` locator.

- [ ] **Step 1: Write the failing test** (REAL deduped-findings: CORE container distinct=22 vs naive locator-rows=52 → +136% inflation guard; 10 doc-only unlocalized findings)

```python
# append to tests/test_assemble_c4.py
def _load_real_findings():
    doc = yaml.safe_load(
        (REAL_RUN / "40-synthesis" / "deduped-findings.yaml").read_text(encoding="utf-8")
    )
    return doc["finding"]


def _load_real_capabilities():
    doc = yaml.safe_load(
        (REAL_RUN / "40-synthesis" / "deduped-capabilities.yaml").read_text(encoding="utf-8")
    )
    return doc["capability"]


def test_badge_join_distinct_counts_and_inflation_guard():
    from apd_gauntlet.assemble_c4 import apply_badges, build_code_nodes, build_container_nodes

    cei = _load_real_index()
    findings = _load_real_findings()
    caps = _load_real_capabilities()

    containers = build_container_nodes(c4_recon=None, cei=cei)
    code = build_code_nodes(cei, component_by_qname={})
    all_nodes = containers + code

    summary = apply_badges(all_nodes, cei=cei, findings=findings, capabilities=caps)
    by_id = {n["id"]: n for n in all_nodes}
    by_name = {n["name"]: n for n in containers}

    # CORE container DISTINCT finding badge == 22 (the real measured value).
    core = by_name["core"]
    assert core["finding_count"] == 22
    # The naive count (one per code: locator row in core's subtree) is 52.
    # DISTINCT must NOT equal naive -> the +136% inflation guard.
    naive_core = 0
    qn2container = {}
    for e in cei["entries"]:
        if e.get("kind") in ("function", "class", "route", "module"):
            qn2container[e["qualified_name"]] = e["repo"].split("-repos-")[-1]
    import re
    qn_re = re.compile(r"^code:([^:@]+)")
    for f in findings:
        for ev in (f.get("evidence") or []):
            m = qn_re.match(ev.get("locator") or "")
            if m and qn2container.get(m.group(1)) == "core":
                naive_core += 1
    assert naive_core == 52
    assert core["finding_count"] == 22 and naive_core == 52  # 22 != 52: distinct guard
    assert round((naive_core - core["finding_count"]) / core["finding_count"] * 100) == 136

    # CORE capability badge == 15 (real measured distinct value).
    assert core["capability_count"] == 15

    # a code node carries the single distinct finding(s) for its own qname,
    # never double-counting a multi-locator finding.
    token = next(
        n for n in code
        if n["name"] == "homeassistant.auth.AuthManager.async_create_access_token"
    )
    assert token["finding_count"] >= 1

    # unlocalized: 10 findings have NO code: locator (doc-anchored only).
    assert summary["unlocalized_finding_count"] == 10

    # container rollup never exceeds the global distinct (multi-repo findings
    # are counted once per container, but a container's own count is distinct).
    assert by_name["supervisor"]["finding_count"] == 6
    assert by_name["iOS"]["finding_count"] == 7
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_badge_join_distinct_counts_and_inflation_guard -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'apply_badges'`.

- [ ] **Step 3: Write minimal implementation** (add to `assemble_c4.py`)

```python
import re

# A ``code:<qualified_name>[:Lx-Ly][@sha]`` evidence locator. Group 1 is the
# bare qualified_name (the badge-join key), stopping at the first ':' or '@'.
_CODE_LOCATOR_RE = re.compile(r"^code:([^:@]+)")


def _qname_to_container(cei: dict[str, Any]) -> dict[str, str]:
    """qualified_name -> container NAME for every code anchor."""
    return {
        str(e.get("qualified_name", "")): _repo_short(str(e.get("repo", "")))
        for e in _code_entries(cei)
    }


def _record_ids_by_qname(
    records: list[dict[str, Any]],
) -> dict[str, set[str]]:
    """qualified_name -> set of DISTINCT record ids citing it via a code: locator.

    A record that cites the same qname twice contributes its id once; a record
    that cites two qnames contributes its id to both. The set-of-ids structure
    is what makes every downstream rollup count DISTINCT ids.
    """
    out: dict[str, set[str]] = {}
    for r in records or []:
        rid = r.get("id")
        if not rid:
            continue
        for ev in r.get("evidence") or []:
            m = _CODE_LOCATOR_RE.match(str(ev.get("locator") or ""))
            if m:
                out.setdefault(m.group(1), set()).add(str(rid))
    return out


def _unlocalized_finding_count(findings: list[dict[str, Any]]) -> int:
    """DISTINCT findings with NO ``code:`` evidence locator (doc-anchored only).
    Surfaced explicitly so doc-only findings are never silently dropped."""
    count = 0
    for f in findings or []:
        if not any(
            _CODE_LOCATOR_RE.match(str(ev.get("locator") or ""))
            for ev in (f.get("evidence") or [])
        ):
            count += 1
    return count


def apply_badges(
    nodes: list[dict[str, Any]],
    cei: dict[str, Any] | None,
    findings: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
) -> dict[str, int]:
    """Compute + write ``finding_count`` / ``capability_count`` on every node in
    place (DISTINCT-id rollups), and return the global badge summary.

    Algorithm:
      1. Build qname -> {record ids} for findings and for capabilities.
      2. For each ``code`` node, attach the DISTINCT id SET for its qname (a
         multi-locator record lands once).
      3. Roll those sets UP the parent chain (code -> component -> container),
         UNIONing ids so a container holding several hit code nodes counts a
         shared finding once. ``finding_count`` is then ``len(set)``.
      4. ``unlocalized_finding_count`` = findings with no ``code:`` locator.

    L1 nodes (system/person/external_system) have no code subtree, so their
    badges stay 0 here; the asset-graph-driven L1 badge join is a later
    milestone and does not change these counts.
    """
    cei = cei or {}
    find_ids_by_qname = _record_ids_by_qname(findings)
    cap_ids_by_qname = _record_ids_by_qname(capabilities)

    by_id = {n["id"]: n for n in nodes}
    # accumulate DISTINCT id sets per node id, then roll up the parent chain.
    find_sets: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    cap_sets: dict[str, set[str]] = {n["id"]: set() for n in nodes}

    # 1+2: seed code nodes from their own qname.
    for n in nodes:
        if n.get("level") != "code":
            continue
        qname = n.get("name", "")
        find_sets[n["id"]] |= find_ids_by_qname.get(qname, set())
        cap_sets[n["id"]] |= cap_ids_by_qname.get(qname, set())

    # 3: roll up. Walk each node to the root via parent ids, unioning the leaf
    # set into every ancestor. (Depth <= 3: code -> component? -> container.)
    for n in nodes:
        if n.get("level") != "code":
            continue
        leaf_find = find_sets[n["id"]]
        leaf_cap = cap_sets[n["id"]]
        if not leaf_find and not leaf_cap:
            continue
        parent_id = n.get("parent")
        guard = 0
        while parent_id and parent_id in by_id and guard < 8:
            find_sets[parent_id] |= leaf_find
            cap_sets[parent_id] |= leaf_cap
            parent_id = by_id[parent_id].get("parent")
            guard += 1

    for n in nodes:
        n["finding_count"] = len(find_sets[n["id"]])
        n["capability_count"] = len(cap_sets[n["id"]])

    return {"unlocalized_finding_count": _unlocalized_finding_count(findings)}
```

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py::test_badge_join_distinct_counts_and_inflation_guard -v
```
Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): DISTINCT-id badge join with code->container rollup

apply_badges seeds each code node with the DISTINCT set of finding/capability
ids citing its qualified_name, then unions those sets up the parent chain so a
container counts a multi-locator or multi-symbol finding exactly once. Verified
the real CORE container badge = 22 distinct vs 52 naive locator rows (+136%
inflation guard) and 10 unlocalized doc-only findings.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: write `40-synthesis/c4-model.yaml` (atomic, sorted, schema_version) + `assemble_c4(run_dir)` end-to-end; schema + validate.py registration

**Files:**
- Create: `schemas/c4-model.schema.json`
- Modify: `tools/apd_gauntlet/validate.py:234-280` (add one line to `SYNTHESIS_ROLLUPS`)
- Modify: `tools/apd_gauntlet/assemble_c4.py`
- Test: `tests/test_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (copy the REAL run to tmp_path, run the public entrypoint, assert the contract build_summary, AND validate the output against `c4-model.schema.json`)

```python
# append to tests/test_assemble_c4.py
import json
import shutil

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = REPO / "schemas"


def _registry():
    res = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            res.append((s["$id"], Resource.from_contents(s)))
    return Registry().with_resources(res)


def _copy_real_run(tmp_path):
    dst = tmp_path / "run"
    for sub in ("00-context", "40-synthesis"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(
        REAL_RUN / "00-context" / "code-evidence-index.yaml",
        dst / "00-context" / "code-evidence-index.yaml",
    )
    shutil.copy(
        REAL_RUN / "00-context" / "asset-inventory.yaml",
        dst / "00-context" / "asset-inventory.yaml",
    )
    for f in ("asset-graph.yaml", "deduped-findings.yaml", "deduped-capabilities.yaml"):
        shutil.copy(REAL_RUN / "40-synthesis" / f, dst / "40-synthesis" / f)
    # a minimal .apd-run.yaml so the subject resolves
    (dst / ".apd-run.yaml").write_text(
        "subject: Home Assistant\nrun_id: apd-test-c4\n", encoding="utf-8"
    )
    return dst


def test_assemble_c4_end_to_end_on_real_run(tmp_path):
    from apd_gauntlet.assemble_c4 import assemble_c4

    run = _copy_real_run(tmp_path)
    summary = assemble_c4(run)
    out = run / "40-synthesis" / "c4-model.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))

    assert doc["schema_version"] == 1
    assert doc["generated_by"] == "assemble_c4"
    bs = doc["build_summary"]
    assert bs == summary  # entrypoint returns the build_summary it wrote

    # 23 containers, 40 code, 0 components (L3 blocked: no c4-recon in this run)
    assert bs["container_count"] == 23
    assert bs["code_count"] == 40
    assert bs["component_count"] == 0
    # L1: 1 system + 8 persons + 5 external systems
    assert bs["system_count"] == 1
    assert bs["person_count"] == 8
    assert bs["external_system_count"] == 5
    # 5 uses edges: the fixture has no c4-recon.yaml, so edges come only from the
    # 6 kind:edge index entries, of which 5 resolve to repo-derived containers
    # (cev-0a000003's host-dockerd target is host infra, correctly excluded).
    assert bs["uses_edge_count"] >= 5
    # honesty counters
    assert bs["not_analyzed_container_count"] == 14
    assert bs["unlocalized_finding_count"] == 10
    # node_count == sum of the per-level counts
    assert bs["node_count"] == (
        bs["system_count"] + bs["person_count"] + bs["external_system_count"]
        + bs["container_count"] + bs["component_count"] + bs["code_count"]
    )

    # every node id is c4- + 8 hex; every edge id is c4e- + 8 hex; unique
    ids = [n["id"] for n in doc["nodes"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"c4-[0-9a-f]{8}", i) for i in ids)
    assert all(re.fullmatch(r"c4e-[0-9a-f]{8}", e["id"]) for e in doc["edges"])
    # nodes are sorted by id (deterministic on-disk order)
    assert ids == sorted(ids)

    # the output VALIDATES against the schema
    schema = json.loads((SCHEMA_DIR / "c4-model.schema.json").read_text())
    errors = sorted(
        Draft202012Validator(schema, registry=_registry()).iter_errors(doc),
        key=lambda e: list(e.path),
    )
    assert errors == [], [e.message for e in errors[:5]]


def test_assemble_c4_idempotent(tmp_path):
    from apd_gauntlet.assemble_c4 import assemble_c4

    run = _copy_real_run(tmp_path)
    assemble_c4(run)
    first = (run / "40-synthesis" / "c4-model.yaml").read_bytes()
    assemble_c4(run)
    second = (run / "40-synthesis" / "c4-model.yaml").read_bytes()
    assert first == second


def test_assemble_c4_noop_without_asset_graph(tmp_path):
    from apd_gauntlet.assemble_c4 import assemble_c4

    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    # no asset-graph.yaml -> gated off -> no file written, empty summary
    summary = assemble_c4(run)
    assert summary == {}
    assert not (run / "40-synthesis" / "c4-model.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_assemble_c4.py::test_assemble_c4_end_to_end_on_real_run tests/test_assemble_c4.py::test_assemble_c4_idempotent tests/test_assemble_c4.py::test_assemble_c4_noop_without_asset_graph -v
```
Expected: `AttributeError: module 'apd_gauntlet.assemble_c4' has no attribute 'assemble_c4'` (and the schema file does not yet exist, so the schema-load line would also fail).

- [ ] **Step 3: Write minimal implementation**

(a) Create `schemas/c4-model.schema.json` (mirrors `asset-graph.schema.json`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/illusconsulting/apd-gauntlet/schemas/c4-model.schema.json",
  "title": "APD Gauntlet C4 Architecture Model",
  "type": "object",
  "required": ["schema_version", "generated_by", "nodes", "edges"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "generated_by":   { "type": "string", "enum": ["assemble_c4"] },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "level", "parent", "name", "kind", "provenance", "finding_count", "capability_count", "analysis_state"],
        "additionalProperties": false,
        "properties": {
          "id":     { "type": "string", "pattern": "^c4-[0-9a-f]{8}$" },
          "level":  { "type": "string", "enum": ["system", "person", "external_system", "container", "component", "code"] },
          "parent": { "type": ["string", "null"], "pattern": "^c4-[0-9a-f]{8}$" },
          "name":   { "type": "string", "minLength": 1 },
          "kind":   { "type": "string" },
          "provenance": {
            "type": "object",
            "required": ["source"],
            "additionalProperties": false,
            "properties": {
              "source":   { "type": "string", "enum": ["artifact", "domain_default", "threat_model", "threat_model_inferred", "code_evidence", "run_config", "asset_inventory"] },
              "artifact": { "type": "string" },
              "locator":  { "type": "string" },
              "repo":     { "type": "string" },
              "machine_extracted": { "type": "boolean" }
            }
          },
          "finding_count":    { "type": "integer", "minimum": 0 },
          "capability_count": { "type": "integer", "minimum": 0 },
          "analysis_state":   { "type": "string", "enum": ["analyzed", "not_analyzed"] }
        }
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "edge_type", "from", "to", "label", "machine_extracted", "provenance"],
        "additionalProperties": false,
        "properties": {
          "id":        { "type": "string", "pattern": "^c4e-[0-9a-f]{8}$" },
          "edge_type": { "type": "string", "enum": ["uses"] },
          "from":      { "type": "string", "pattern": "^c4-[0-9a-f]{8}$" },
          "to":        { "type": "string", "pattern": "^c4-[0-9a-f]{8}$" },
          "label":     { "type": "string" },
          "machine_extracted": { "type": "boolean" },
          "provenance": { "$ref": "#/properties/nodes/items/properties/provenance" }
        }
      }
    },
    "build_summary": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "node_count":                   { "type": "integer", "minimum": 0 },
        "system_count":                 { "type": "integer", "minimum": 0 },
        "person_count":                 { "type": "integer", "minimum": 0 },
        "external_system_count":        { "type": "integer", "minimum": 0 },
        "container_count":              { "type": "integer", "minimum": 0 },
        "component_count":              { "type": "integer", "minimum": 0 },
        "code_count":                   { "type": "integer", "minimum": 0 },
        "uses_edge_count":              { "type": "integer", "minimum": 0 },
        "unlocalized_finding_count":    { "type": "integer", "minimum": 0 },
        "not_analyzed_container_count": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

(b) Register the schema in `validate.py` `SYNTHESIS_ROLLUPS` (insert directly under the `asset-graph.yaml` line at ~247):

```python
    # C-21: Phase C synthesis artifacts
    "asset-graph.yaml":            "asset-graph.schema.json",
    "c4-model.yaml":               "c4-model.schema.json",
```

(c) Add the public entrypoint + writer to `assemble_c4.py`:

```python
def _build_summary(nodes: list[dict[str, Any]], edges: list[dict[str, Any]],
                   badge_summary: dict[str, int]) -> dict[str, int]:
    by_level: dict[str, int] = {}
    for n in nodes:
        by_level[n["level"]] = by_level.get(n["level"], 0) + 1
    not_analyzed = sum(
        1 for n in nodes
        if n["level"] == "container" and n["analysis_state"] == "not_analyzed"
    )
    return {
        "node_count": len(nodes),
        "system_count": by_level.get("system", 0),
        "person_count": by_level.get("person", 0),
        "external_system_count": by_level.get("external_system", 0),
        "container_count": by_level.get("container", 0),
        "component_count": by_level.get("component", 0),
        "code_count": by_level.get("code", 0),
        "uses_edge_count": len(edges),
        "unlocalized_finding_count": badge_summary.get("unlocalized_finding_count", 0),
        "not_analyzed_container_count": not_analyzed,
    }


def _records(doc: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    recs = doc.get(key)
    return recs if isinstance(recs, list) else []


def assemble_c4(run_dir: Path) -> dict[str, Any]:
    """Assemble 40-synthesis/c4-model.yaml. Returns its build_summary.

    GATING: a no-op (returns {}) unless 40-synthesis/asset-graph.yaml exists —
    the C4 view is presence-gated on the same artifact as the attack-path graph.
    The code tiers (L4/L3) are populated only when
    00-context/code-evidence-index.yaml exists; otherwise only L1/L2 render.
    Idempotent: nodes/edges are id-sorted and the writer is byte-stable.
    """
    synth = run_dir / "40-synthesis"
    context = run_dir / "00-context"
    if not (synth / "asset-graph.yaml").exists():
        return {}

    cei = _yaml_optional(context / "code-evidence-index.yaml")
    cei_inner = cei.get("code_evidence_index") if isinstance(cei, dict) else None
    cei_inner = cei_inner if isinstance(cei_inner, dict) else (cei or {})

    c4_recon = _yaml_optional(context / "c4-recon.yaml")
    inv = _yaml_optional(context / "asset-inventory.yaml")
    findings = _records(_yaml_optional(synth / "deduped-findings.yaml"), "finding")
    caps = _records(_yaml_optional(synth / "deduped-capabilities.yaml"), "capability")
    subject = _subject(run_dir)

    # L2 first (containers are the parent for code + edge endpoints).
    containers = build_container_nodes(c4_recon=c4_recon, cei=cei_inner)
    container_id_by_name = {n["name"]: n["id"] for n in containers}

    # L3 (blocked-by-default) then L4 (code), with component re-parenting.
    components = build_component_nodes(
        c4_recon=c4_recon, container_id_by_name=container_id_by_name
    )
    cmap = component_map(c4_recon)
    code = build_code_nodes(cei_inner, component_by_qname=cmap) if cei_inner else []

    # L1 system context.
    l1 = build_l1_nodes(inv, subject=subject)

    edges = build_uses_edges(
        c4_recon=c4_recon, cei=cei_inner,
        container_id_by_name=container_id_by_name,
    )

    nodes = l1 + containers + components + code
    badge_summary = apply_badges(nodes, cei=cei_inner, findings=findings, capabilities=caps)

    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: e["id"])
    build_summary = _build_summary(nodes, edges, badge_summary)

    doc = {
        "schema_version": 1,
        "generated_by": "assemble_c4",
        "nodes": nodes,
        "edges": edges,
        "build_summary": build_summary,
    }
    out = synth / "c4-model.yaml"
    tmp = out.with_suffix(".yaml.tmp")
    tmp.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096),
        encoding="utf-8",
    )
    tmp.replace(out)  # atomic on POSIX
    return build_summary


def _subject(run_dir: Path) -> str:
    cfg = _yaml_optional(run_dir / ".apd-run.yaml") or {}
    subj = cfg.get("subject")
    return str(subj) if subj else run_dir.name
```

Add `import os` is not needed (`Path.replace` handles the atomic rename); ensure `from pathlib import Path` (already imported in Task 2).

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_assemble_c4.py -v
```
Expected: all tests pass (Tasks 1–8), including `test_assemble_c4_end_to_end_on_real_run`, `test_assemble_c4_idempotent`, `test_assemble_c4_noop_without_asset_graph`.

Then confirm the schema registration loads cleanly:

```
python3 -c "from apd_gauntlet import validate; assert validate.SYNTHESIS_ROLLUPS['c4-model.yaml'] == 'c4-model.schema.json'; print('registered')"
```
Expected: `registered`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/assemble_c4.py schemas/c4-model.schema.json tools/apd_gauntlet/validate.py tests/test_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): end-to-end assemble_c4 + c4-model schema

assemble_c4(run_dir) gates on asset-graph.yaml, assembles L1-L4 nodes + uses
edges, applies the distinct badge join, and atomically writes id-sorted
40-synthesis/c4-model.yaml, returning build_summary. Adds schemas/
c4-model.schema.json (mirrors asset-graph) and registers it in validate's
SYNTHESIS_ROLLUPS. Verified end-to-end on the real home-assistant run:
23 containers / 40 code / 0 components / >=6 uses edges / 14 not_analyzed /
10 unlocalized, output validates against the schema, byte-idempotent.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: CLI `assemble-c4 <run-dir>` command wired into `cli.py`

**Files:**
- Modify: `tools/apd_gauntlet/cli.py:1159-1169` (add `assemble-c4` directly after `assemble-inventory`)
- Test: `tests/test_cli_assemble_c4.py`

- [ ] **Step 1: Write the failing test** (CliRunner against the copied real run; asserts the file is written + the summary is echoed)

```python
# tests/test_cli_assemble_c4.py
from __future__ import annotations

import pathlib
import shutil

import yaml
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"


def _copy_real_run(tmp_path):
    dst = tmp_path / "run"
    for sub in ("00-context", "40-synthesis"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(REAL_RUN / "00-context" / "code-evidence-index.yaml",
                dst / "00-context" / "code-evidence-index.yaml")
    shutil.copy(REAL_RUN / "00-context" / "asset-inventory.yaml",
                dst / "00-context" / "asset-inventory.yaml")
    for f in ("asset-graph.yaml", "deduped-findings.yaml", "deduped-capabilities.yaml"):
        shutil.copy(REAL_RUN / "40-synthesis" / f, dst / "40-synthesis" / f)
    (dst / ".apd-run.yaml").write_text(
        "subject: Home Assistant\nrun_id: apd-test-c4\n", encoding="utf-8"
    )
    return dst


def test_assemble_c4_cli_writes_file_and_echoes_summary(tmp_path):
    from apd_gauntlet.cli import main

    run = _copy_real_run(tmp_path)
    res = CliRunner().invoke(main, ["assemble-c4", str(run)])
    assert res.exit_code == 0, res.output
    out = run / "40-synthesis" / "c4-model.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["generated_by"] == "assemble_c4"
    # the echo surfaces the headline counts operators care about
    assert "assemble-c4" in res.output
    assert "23 container" in res.output
    assert "40 code" in res.output
    assert "14 not_analyzed" in res.output


def test_assemble_c4_cli_noop_without_asset_graph(tmp_path):
    from apd_gauntlet.cli import main

    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    res = CliRunner().invoke(main, ["assemble-c4", str(run)])
    assert res.exit_code == 0, res.output
    assert "no asset-graph.yaml" in res.output
    assert not (run / "40-synthesis" / "c4-model.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```
python3 -m pytest tests/test_cli_assemble_c4.py -v
```
Expected: failure — `Error: No such command 'assemble-c4'.` (CliRunner exit_code 2, the assertions fail).

- [ ] **Step 3: Write minimal implementation** — insert the command in `cli.py` immediately after `assemble_inventory_cmd` (after line 1168):

```python
@main.command("assemble-c4")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def assemble_c4_cmd(run_dir: Path) -> None:
    """Assemble the grounded C4 architecture model -> 40-synthesis/c4-model.yaml.

    Gated on 40-synthesis/asset-graph.yaml; the code tiers (L3/L4) are populated
    only when 00-context/code-evidence-index.yaml exists. Mints all c4-/c4e- ids
    and the per-node finding/capability badges (the SOLE minter; ADR-0020).
    """
    from .assemble_c4 import assemble_c4

    summary = assemble_c4(run_dir)
    if not summary:
        click.echo(
            f"assemble-c4: no asset-graph.yaml under {run_dir}/40-synthesis/ - skipped"
        )
        return
    click.echo(
        "assemble-c4: wrote 40-synthesis/c4-model.yaml "
        f"({summary['node_count']} nodes = "
        f"{summary['system_count']} system / {summary['person_count']} person / "
        f"{summary['external_system_count']} external_system / "
        f"{summary['container_count']} container / "
        f"{summary['component_count']} component / {summary['code_count']} code; "
        f"{summary['uses_edge_count']} uses edges; "
        f"{summary['not_analyzed_container_count']} not_analyzed container(s); "
        f"{summary['unlocalized_finding_count']} unlocalized finding(s))"
    )
```

- [ ] **Step 4: Run test to verify it passes**

```
python3 -m pytest tests/test_cli_assemble_c4.py -v
```
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/cli.py tests/test_cli_assemble_c4.py
git commit -m "$(cat <<'EOF'
feat(assemble-c4): wire assemble-c4 CLI command

Adds `apd-gauntlet assemble-c4 <run-dir>` (mirrors assemble-inventory): gates on
asset-graph.yaml, writes 40-synthesis/c4-model.yaml, echoes the per-level node
counts + honesty counters. No-op with a clear message when asset-graph is absent.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

**Milestone exit check:**

```
python3 -m pytest tests/test_assemble_c4.py tests/test_cli_assemble_c4.py -v \
  && python3 -m ruff check tools/apd_gauntlet/assemble_c4.py tools/apd_gauntlet/cli.py tools/apd_gauntlet/validate.py \
  && python3 -m mypy tools/apd_gauntlet/assemble_c4.py \
  && python3 -c "import json; json.load(open('schemas/c4-model.schema.json')); print('c4-model.schema.json parses')" \
  && python3 -m pytest tests/test_assemble_inventory.py tests/ -k "validate or schema" -q
```

Expected: all new `assemble-c4` tests pass; `ruff`/`mypy` clean on the new module and the two modified files; the new schema parses; and the existing `assemble_inventory` + schema/validate test suites stay green (the `SYNTHESIS_ROLLUPS` addition is purely additive). This milestone leaves the assembler core, its schema, its `validate.py` registration, and the CLI command landed and fully covered; report wiring (`loader.py` `RunArtifacts` fields, `report/transform.py::c4_model_view`, `screens/C4.jsx`, `app.jsx` tab) is the next milestone, which consumes the `c4-model.yaml` this milestone now produces.

---

## Milestone 3: Extend the apd-code-recon agent to emit grounded C4 content (c4-recon.yaml + code-evidence-index c4_* tags), gated by the apd-c4-discipline skill

**Files touched in this milestone:**

- Modify: `.claude/agents/apd-code-recon.md` (add `apd-c4-discipline` to Required reading; add a "C4 architecture emission" section; declare the new output + `c4_*` tags)
- Create: `tests/fixtures/valid/c4-recon.yaml` (the authored home-assistant example — also the test fixture for M3 and a reusable fixture for M2's assembler test)
- Create: `tests/fixtures/invalid/c4-recon-malformed.yaml` (negative fixture)
- Create: `tests/test_c4_recon_schema.py` (validate the authored example against `schemas/c4-recon.schema.json` from M1; flag the malformed one)
- Modify: `tools/apd_gauntlet/validate.py:282-293` (register `c4-recon.yaml` → `c4-recon.schema.json` in `CONTEXT_ROLLUPS`)
- Create: `tests/test_validator_c4_recon.py` (validate-pass accepts the valid index, flags the malformed one, via the public `run_schema_pass`)
- Modify: `.claude/workflows/apd-gauntlet.js:638` (insert `pyStep('assemble-c4', ...)` immediately after the tmeval/apath `parallel([...])` barrier, before `canonicalize-tmeval`)
- Modify: `tests/test_workflow_apd_gauntlet.py:189` (add `assemble-c4` to the pipeline-coverage pin)
- Create: `tests/test_lint_agent_apd_code_recon.py` (agent-lint: the edited agent still lints clean; declares the C4 output + the new required-reading entry)

> **Cross-milestone preconditions (do not re-do here):** M1 has already created `schemas/c4-recon.schema.json` and added the additive optional `c4_container`/`c4_component`/`c4_level` keys to `schemas/code-evidence-index.schema.json`. M2 has already created `skills/apd-c4-discipline/SKILL.md`, `tools/apd_gauntlet/assemble_c4.py`, and registered the `assemble-c4` Click command in `tools/apd_gauntlet/cli.py`. The structural test `tests/test_workflow_apd_gauntlet.py::test_every_cli_command_is_registered` only passes the `pyStep('assemble-c4', ...)` added in Task 4 because M2 already registered the command in `cli.commands`. Confirm the discipline-skill path that Task 1 cites by reading `.claude/skills/apd-attack-path-discipline/SKILL.md` — the sibling lives at `.claude/skills/apd-attack-path-discipline/SKILL.md`, so the M2-created discipline skill is at `.claude/skills/apd-c4-discipline/SKILL.md`.

---

### Task 1: Add the "C4 architecture emission" section + `apd-c4-discipline` required reading to apd-code-recon.md

**Files:**
- Modify: `.claude/agents/apd-code-recon.md:29-35` (Required reading list)
- Modify: `.claude/agents/apd-code-recon.md:43-48` (Outputs declaration)
- Modify: `.claude/agents/apd-code-recon.md:152-156` (insert the new emission section after Step 6b, before Step 7)
- Test: `tests/test_lint_agent_apd_code_recon.py` (authored in Task 5; this task's gate is the structural-content test in Step 2 below)

- [ ] **Step 1: Write the failing test** — content assertions on the edited agent body (run before editing to prove they fail, then again in Task 5 for the lint gate). Create `tests/test_lint_agent_apd_code_recon.py`:

```python
"""Tests for the apd-code-recon agent file — C4 emission extension (Milestone 3).

The agent body is the source-of-truth for what code-recon emits and which
disciplines it reads. These tests pin the structural invariants the assembler
(assemble-c4) and the lint-agents command rely on after the C4 extension.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT = REPO_ROOT / ".claude" / "agents" / "apd-code-recon.md"


def _agent_frontmatter() -> dict[str, Any]:
    text = AGENT.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m is not None, "Agent file is missing YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert isinstance(meta, dict)
    return meta


def test_agent_file_exists() -> None:
    assert AGENT.exists(), f"Agent file missing: {AGENT}"


def test_agent_name_unchanged() -> None:
    assert _agent_frontmatter()["name"] == "apd-code-recon"


def test_required_reading_lists_c4_discipline() -> None:
    text = AGENT.read_text()
    rr = re.search(r"(?ms)^##+\s*Required reading.*?(?=^##|\Z)", text)
    assert rr is not None, "no Required reading section"
    assert "apd-c4-discipline" in rr.group(0), (
        "Required reading must list the apd-c4-discipline skill"
    )


def test_required_reading_c4_path_resolves() -> None:
    """The cited c4-discipline SKILL.md must exist on disk (lint enforces this)."""
    target = REPO_ROOT / ".claude" / "skills" / "apd-c4-discipline" / "SKILL.md"
    assert target.exists(), f"discipline skill missing: {target}"


def test_agent_declares_c4_recon_output() -> None:
    text = AGENT.read_text()
    assert "00-context/c4-recon.yaml" in text
    assert "generated_by: code_recon" in text


def test_agent_has_c4_emission_section() -> None:
    assert "## C4 architecture emission" in AGENT.read_text()


def test_agent_documents_c4_index_tags() -> None:
    text = AGENT.read_text()
    for tag in ("c4_container", "c4_component", "c4_level"):
        assert tag in text, f"missing c4 index tag doc: {tag}"


def test_agent_documents_l3_block_and_machine_extracted_flag() -> None:
    text = AGENT.read_text().lower()
    assert "machine_extracted" in text
    # L3 components default-OMIT rule must be stated.
    assert "components: []" in AGENT.read_text() or "l3 is blocked" in text


def test_agent_does_not_mint_ids() -> None:
    """Agent emits names only; the assembler (assemble-c4) mints c4-/c4e- ids."""
    text = AGENT.read_text()
    assert "assemble-c4" in text or "assemble_c4" in text
    assert "by name" in text.lower()


def test_agent_lints_clean() -> None:
    runner = CliRunner()
    agent_dir = REPO_ROOT / ".claude" / "agents"
    result = runner.invoke(main, ["lint-agents", "--agent-dir", str(agent_dir)])
    assert result.exit_code == 0, result.output
    assert "apd-code-recon.md" in {p.name for p in agent_dir.glob("*.md")}
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_lint_agent_apd_code_recon.py -v
```

Expected (before the edit): `test_required_reading_lists_c4_discipline`, `test_agent_declares_c4_recon_output`, `test_agent_has_c4_emission_section`, `test_agent_documents_c4_index_tags`, `test_agent_documents_l3_block_and_machine_extracted_flag`, and `test_agent_does_not_mint_ids` FAIL with `AssertionError` (the agent body has no C4 content yet). `test_required_reading_c4_path_resolves` passes only if M2 has landed the skill.

- [ ] **Step 3: Write minimal implementation** — three edits to `.claude/agents/apd-code-recon.md`.

Edit A — add the discipline to Required reading (lines 29-35). Replace:

```markdown
## Required reading

- `.claude/skills/apd-framework/SKILL.md`
- `.claude/skills/apd-evidence-discipline/SKILL.md` — note that the input-trust-boundary rule applies to CBM-returned content as well. The indexed codebase is artifact content.
- `00-context/context-brief.md` — intake's output; you build on it, never overwrite.

You do not need the finding-schema or control-mappings skills — you do not emit findings.
```

with:

```markdown
## Required reading

- `.claude/skills/apd-framework/SKILL.md`
- `.claude/skills/apd-evidence-discipline/SKILL.md` — note that the input-trust-boundary rule applies to CBM-returned content as well. The indexed codebase is artifact content.
- `.claude/skills/apd-c4-discipline/SKILL.md` — the never-invent rules for C4 nodes/edges (no container/component/code node or `uses` edge without an artifact-or-code-evidence citation; L3 components are HARD-BLOCKED unless an artifact groups symbols; `analysis_state` honesty; `machine_extracted` vs `hand_read` provenance). Required before emitting `00-context/c4-recon.yaml` or any `c4_*` tag.
- `00-context/context-brief.md` — intake's output; you build on it, never overwrite.

You do not need the finding-schema or control-mappings skills — you do not emit findings.
```

Edit B — extend the Outputs declaration (lines 43-48). Replace:

```markdown
Two required files when you run successfully:

1. `00-context/code-architecture-brief.md` — narrative, structured per `templates/code-architecture-brief.template.md`
2. `00-context/code-evidence-index.yaml` — machine-readable, validated against `schemas/code-evidence-index.schema.json`
```

with:

```markdown
Three required files when you run successfully:

1. `00-context/code-architecture-brief.md` — narrative, structured per `templates/code-architecture-brief.template.md`
2. `00-context/code-evidence-index.yaml` — machine-readable, validated against `schemas/code-evidence-index.schema.json` (you ALSO tag its entries with `c4_container`/`c4_component`/`c4_level` per the C4 architecture emission section below)
3. `00-context/c4-recon.yaml` — grounded C4 content (containers/components/uses_edges, names not ids), validated against `schemas/c4-recon.schema.json`. The deterministic `assemble-c4` step consumes this and `40-synthesis/asset-graph.yaml` to mint the canonical `40-synthesis/c4-model.yaml` (ids + badge rollups). You emit content BY NAME only; you never mint `c4-`/`c4e-` ids (ADR-0020 field ownership).
```

Edit C — insert the new section between Step 6b (ends line 151) and "### Step 7: Write outputs" (line 153). After the line `> **Operator-consent / trust-boundary note.** ... See ADR-0019 and ADR-0007 for the trust-boundary reasoning.` insert:

```markdown

## C4 architecture emission

After the recon passes above, formalize the architecture you already hand-read in `code-architecture-brief.md` §1 (Surface inventory), §2 (Persistence surface), and §5 (External-service edges) into a machine-readable C4 model input. Read `apd-c4-discipline` first. Emit `00-context/c4-recon.yaml` (content only — the assembler mints all ids) and tag the `code-evidence-index.yaml` entries you wrote so the assembler can attach badges to the right node.

### `c4-recon.yaml` shape

```yaml
schema_version: 1
generated_by: code_recon
containers:
  - name: "Core"                      # natural-key name; the assembler derives the id
    kind: service                     # service | data_store | compute | external_system | app | library
    repo: "…repos-core"               # the CBM project / repo this container maps to
    provenance: { source: "code-architecture-brief.md", locator: "§1 Surface inventory" }
    analysis_state: analyzed          # analyzed | not_analyzed
components: []                        # ONLY when an artifact groups symbols; else EMPTY (L3 blocked)
uses_edges:
  - from: "ha CLI"                    # container name ref
    to: "Supervisor API"             # container name ref
    label: "CROSS_HTTP_CALLS (runtime viper host)"
    machine_extracted: false          # false when hand-read; true only from a CBM CROSS_* edge
    provenance: { source: "code-evidence-index.yaml", locator: "cev-0a000001" }
```

### Emission discipline (never-invent)

- **Containers.** One entry per code-bearing repo you anchored, plus the surfaces/stores you grounded in §1/§2 (e.g. the REST/WS API surface, `.storage`, the Recorder DB, the Supervisor control plane, the os-agent host bridge, the mobile clients, the FCM relay). Every container carries a `provenance` citation (a brief section or a `cev-` id). A repo you indexed but did **not** deep-read (zero code anchors) is still a real container — emit it with `analysis_state: not_analyzed`. **Never** drop it and **never** imply "0 findings = clean"; the assembler renders `not_analyzed` honestly.
- **`uses_edges`.** Emit ONLY from a CBM `CROSS_*` edge (`machine_extracted: true`) or from a hand-read client/server call site in code (`machine_extracted: false`). Each edge cites the `cev-` id of the `kind: edge` index entry (from §5) or the `file_path` you read. Never emit a boundary-crossing edge you cannot cite. For Home Assistant this is exactly the six §5 edges; the auto-linker found zero, so all six are `machine_extracted: false`.
- **Components (L3) are HARD-BLOCKED.** Leave `components: []` unless a concrete artifact (a manifest, an `__init__.py` `__all__`, a package boundary doc) groups symbols into a named component. When in doubt, OMIT — the assembler then renders the container's L4 code anchors directly under the container (L2→L4), which is the default and correct behavior. Do not synthesize component groupings from intuition.
- **Field ownership.** You emit names, kinds, provenance, `machine_extracted`, and `analysis_state` — content only. The deterministic `assemble-c4` step is the SOLE minter of `c4-`/`c4e-` ids and of `finding_count`/`capability_count` badge rollups. Never put an id or a count in `c4-recon.yaml`.

### Tag the evidence index

For every entry already in `code-evidence-index.yaml`, add three additive OPTIONAL tags so the assembler can roll the entry's findings/capabilities up to the right C4 node:

- `c4_container`: the `name` of the container this anchor belongs to (must match a `c4-recon.yaml` container `name`).
- `c4_component`: the component `name` if (and only if) you emitted one for it; otherwise `null`.
- `c4_level`: `code` for a function/class/route/consumer/job/module anchor; `container` for a `kind: edge` cross-repo anchor that maps to a `uses_edge`; `component` only when the anchor is the artifact that defines a component group.

These keys are additive and optional in `schemas/code-evidence-index.schema.json` (M1); an untagged legacy index still validates. Tagging an entry with a `c4_container` that names no `c4-recon.yaml` container is the kind of inconsistency the assembler will surface — keep the names in lock-step.
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_lint_agent_apd_code_recon.py -v
```

Expected: all tests PASS (assuming M1/M2 landed so the discipline skill exists). If only `test_required_reading_c4_path_resolves` / `test_agent_lints_clean` fail, that means the M2 skill is not yet on this branch — that is the cross-milestone precondition, not a Task-1 defect.

- [ ] **Step 5: Commit**

```
git add .claude/agents/apd-code-recon.md tests/test_lint_agent_apd_code_recon.py
git commit -m "feat(code-recon): emit grounded c4-recon.yaml + c4_* index tags, read apd-c4-discipline

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Author the concrete home-assistant `c4-recon.yaml` example fixture

**Files:**
- Create: `tests/fixtures/valid/c4-recon.yaml`
- Create: `tests/fixtures/invalid/c4-recon-malformed.yaml`
- Test: `tests/test_c4_recon_schema.py` (Task is validated by this schema test)

- [ ] **Step 1: Write the failing test** — create `tests/test_c4_recon_schema.py`:

```python
"""Schema tests for the c4-recon.yaml artifact (agent-authored C4 input)."""
from __future__ import annotations

import json
import pathlib

import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((REPO / "schemas" / "c4-recon.schema.json").read_text())
FIXTURES = REPO / "tests" / "fixtures"


def test_valid_c4_recon_passes():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == [], [e.message for e in errors]


def test_home_assistant_example_has_nine_containers():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    assert len(data["containers"]) == 9


def test_home_assistant_example_has_not_analyzed_containers():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    states = {c["analysis_state"] for c in data["containers"]}
    assert "not_analyzed" in states, "honesty: at least one container is not_analyzed"
    assert "analyzed" in states


def test_home_assistant_example_has_six_uses_edges_all_hand_read():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    edges = data["uses_edges"]
    assert len(edges) == 6, "the six §5 cross-boundary edges from the brief"
    assert all(e["machine_extracted"] is False for e in edges), (
        "HA auto-linker found 0 CROSS_* edges; all six were hand-read"
    )


def test_l3_components_are_blocked_empty():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    assert data["components"] == [], "L3 is blocked: no artifact groups symbols"


def test_generated_by_is_code_recon():
    data = yaml.safe_load((FIXTURES / "valid/c4-recon.yaml").read_text())
    assert data["generated_by"] == "code_recon"
    assert data["schema_version"] == 1


def test_malformed_c4_recon_is_flagged():
    data = yaml.safe_load((FIXTURES / "invalid/c4-recon-malformed.yaml").read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    messages = " ".join(e.message for e in errors)
    # bad container kind enum
    assert "not-a-kind" in messages or "kind" in messages
    # bad analysis_state enum
    assert "maybe" in messages or "analysis_state" in messages
    # machine_extracted not a bool
    assert "yes" in messages or "machine_extracted" in messages
    # generated_by wrong const
    assert "intake" in messages or "generated_by" in messages
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_c4_recon_schema.py -v
```

Expected: collection-time `FileNotFoundError` for `tests/fixtures/valid/c4-recon.yaml` (the fixtures do not exist yet), or — if M1's `schemas/c4-recon.schema.json` is present and the fixtures are missing — every test errors with `FileNotFoundError: tests/fixtures/valid/c4-recon.yaml`.

- [ ] **Step 3: Write minimal implementation** — create the two fixtures.

`tests/fixtures/valid/c4-recon.yaml` (the authored HA example: 9 containers — core/supervisor/os-agent/cli/iOS/android/frontend/fcm-push are `analyzed` plus the addons sample manifest container; one indexed-but-not-deep-read repo `operating-system` as `not_analyzed`; the six §5 edges; `components: []`):

```yaml
schema_version: 1
generated_by: code_recon
# Grounded C4 input for apd-20260612-home-assistant. Containers + uses_edges are
# the §1/§2/§5 architecture the code-recon agent hand-read; names are natural keys
# (the assemble-c4 step mints c4-/c4e- ids and badge counts). L3 is blocked.
containers:
  - name: "Core"
    kind: service
    repo: "Users-user-Documents-GitHub-home-assistant-repos-core"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§1 Surface inventory (REST /api, WS /api/websocket, mobile_app webhook)"
    analysis_state: analyzed
  - name: "Supervisor"
    kind: service
    repo: "Users-user-Documents-GitHub-home-assistant-repos-supervisor"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§1 Supervisor privileged API + ingress; §3 SecurityMiddleware.token_validation"
    analysis_state: analyzed
  - name: "os-agent"
    kind: compute
    repo: "Users-user-Documents-GitHub-home-assistant-repos-os-agent"
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-c3000001 (system.system.AddSSHAuthKey — D-Bus host primitives)"
    analysis_state: analyzed
  - name: "ha CLI"
    kind: app
    repo: "Users-user-Documents-GitHub-home-assistant-repos-cli"
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000001 (ha CLI -> Supervisor API)"
    analysis_state: analyzed
  - name: "iOS Companion"
    kind: app
    repo: "Users-user-Documents-GitHub-home-assistant-repos-iOS"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§2 ServerManagerKeychain (default Keychain accessibility class)"
    analysis_state: analyzed
  - name: "Android Companion"
    kind: app
    repo: "Users-user-Documents-GitHub-home-assistant-repos-android"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§2 DatabaseModule.provideAppDatabase (unencrypted Room); §1 LaunchActivity"
    analysis_state: analyzed
  - name: "Frontend"
    kind: app
    repo: "Users-user-Documents-GitHub-home-assistant-repos-frontend"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§5 Mobile WebView -> Core REST/WS external-auth bridge"
    analysis_state: analyzed
  - name: "FCM push relay"
    kind: external_system
    repo: "Users-user-Documents-GitHub-home-assistant-repos-mobile-apps-fcm-push"
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-08000001 (Firebase Cloud Function POST /api/sendPushNotification)"
    analysis_state: analyzed
  - name: "Operating System"
    kind: compute
    repo: "Users-user-Documents-GitHub-home-assistant-repos-operating-system"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§7 indexed + reachable but intentionally not deep-read (thin build shell)"
    analysis_state: not_analyzed
components: []
uses_edges:
  - from: "ha CLI"
    to: "Supervisor"
    label: "CROSS_HTTP_CALLS — CLI invokes Supervisor API (runtime viper host)"
    machine_extracted: false
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000001"
  - from: "Supervisor"
    to: "Core"
    label: "CROSS_HTTP_CALLS — Supervisor calls Core /auth/token + API (runtime container IP)"
    machine_extracted: false
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000002"
  - from: "Supervisor"
    to: "os-agent"
    label: "CROSS_CHANNEL — Supervisor -> dockerd via shared /run/docker.sock"
    machine_extracted: false
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000003"
  - from: "Supervisor"
    to: "os-agent"
    label: "CROSS_CHANNEL — Supervisor -> os-agent host ops via system D-Bus IPC"
    machine_extracted: false
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000004"
  - from: "Frontend"
    to: "Core"
    label: "CROSS_HTTP_CALLS — mobile WebView -> Core REST/WS (user-entered instance URL)"
    machine_extracted: false
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000005"
  - from: "Core"
    to: "FCM push relay"
    label: "CROSS_HTTP_CALLS — Core -> FCM push relay -> APNS/FCM (external Firebase URL)"
    machine_extracted: false
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000006"
```

`tests/fixtures/invalid/c4-recon-malformed.yaml` (one deliberate violation per validated field — wrong `generated_by` const, bad container `kind` enum, bad `analysis_state` enum, non-bool `machine_extracted`):

```yaml
schema_version: 1
generated_by: intake
containers:
  - name: "Core"
    kind: not-a-kind
    repo: "repos-core"
    provenance:
      source: "code-architecture-brief.md"
      locator: "§1"
    analysis_state: maybe
components: []
uses_edges:
  - from: "Core"
    to: "Supervisor"
    label: "x"
    machine_extracted: yes-please
    provenance:
      source: "code-evidence-index.yaml"
      locator: "cev-0a000002"
```

> Note: PyYAML coerces the bare token `yes` to a boolean, which would NOT trip the schema's `boolean` check; the explicit string `yes-please` keeps `machine_extracted` a non-bool so the negative assertion holds. `not-a-kind`/`maybe`/`intake` are caught by the enum/const constraints in `schemas/c4-recon.schema.json` (M1).

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_c4_recon_schema.py -v
```

Expected: `7 passed`.

- [ ] **Step 5: Commit**

```
git add tests/fixtures/valid/c4-recon.yaml tests/fixtures/invalid/c4-recon-malformed.yaml tests/test_c4_recon_schema.py
git commit -m "test(c4): authored home-assistant c4-recon.yaml fixture + schema validation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Wire `c4-recon.yaml` into the validate.py schema map

**Files:**
- Modify: `tools/apd_gauntlet/validate.py:282-293` (`CONTEXT_ROLLUPS` map)
- Test: `tests/test_validator_c4_recon.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_validator_c4_recon.py` (mirrors `tests/test_validator_code_evidence.py`, exercising the public `run_schema_pass`):

```python
"""Validator integration tests for 00-context/c4-recon.yaml (Milestone 3)."""
from __future__ import annotations

import pathlib

from apd_gauntlet.validate import run_schema_pass

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def _make_run(tmp_path, valid: bool):
    (tmp_path / "00-context").mkdir(parents=True)
    (tmp_path / "00-context" / "context-brief.md").write_text(
        "---\n"
        "framework_version: 1.1.0\n"
        "run_id: t\n"
        "domain_pack: { name: pbm, version: 1.0.0 }\n"
        "artifacts:\n"
        "  - { filename: tech_plan.md, type: tech_plan }\n"
        "---\n"
        "# brief\n"
    )
    src = "valid/c4-recon.yaml" if valid else "invalid/c4-recon-malformed.yaml"
    (tmp_path / "00-context" / "c4-recon.yaml").write_text((FIXTURES / src).read_text())
    return tmp_path


def test_schema_pass_accepts_valid_c4_recon(tmp_path):
    run_dir = _make_run(tmp_path, valid=True)
    report = run_schema_pass(run_dir)
    errors = [v for v in report.errors if "c4-recon" in str(v.file)]
    assert errors == [], [v.message for v in errors]


def test_schema_pass_flags_malformed_c4_recon(tmp_path):
    run_dir = _make_run(tmp_path, valid=False)
    report = run_schema_pass(run_dir)
    assert any("c4-recon" in str(v.file) for v in report.errors), (
        "malformed c4-recon.yaml must be flagged by run_schema_pass"
    )


def test_absent_c4_recon_is_silent(tmp_path):
    """c4-recon.yaml is OPTIONAL: an absent file produces no validation error."""
    (tmp_path / "00-context").mkdir(parents=True)
    (tmp_path / "00-context" / "context-brief.md").write_text(
        "---\nframework_version: 1.1.0\nrun_id: t\n"
        "domain_pack: { name: pbm, version: 1.0.0 }\n"
        "artifacts:\n  - { filename: tech_plan.md, type: tech_plan }\n---\n# brief\n"
    )
    report = run_schema_pass(tmp_path)
    assert not any("c4-recon" in str(v.file) for v in report.errors)
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_validator_c4_recon.py -v
```

Expected: `test_schema_pass_flags_malformed_c4_recon` FAILS — the malformed file is not registered in `CONTEXT_ROLLUPS`, so `_validate_context_rollups` never schema-checks it and no `c4-recon` error appears (`assert any(...)` fails). The other two pass vacuously.

- [ ] **Step 3: Write minimal implementation** — register the file in `CONTEXT_ROLLUPS`. In `tools/apd_gauntlet/validate.py`, replace:

```python
    # C-21: Phase C intake artifact (emitted by the intake step).
    "asset-inventory.yaml":         "asset-inventory.schema.json",
}
```

with:

```python
    # C-21: Phase C intake artifact (emitted by the intake step).
    "asset-inventory.yaml":         "asset-inventory.schema.json",
    # C4: grounded C4 input authored by code-recon. OPTIONAL (presence-gated,
    # like asset-graph) — _validate_context_rollups silently skips it when
    # absent; the deterministic assemble-c4 step consumes it into
    # 40-synthesis/c4-model.yaml.
    "c4-recon.yaml":                "c4-recon.schema.json",
}
```

> The canonical assembled `40-synthesis/c4-model.yaml` → `c4-model.schema.json` mapping belongs to `SYNTHESIS_ROLLUPS` and lands in M2 alongside `assemble_c4.py`; this task wires only the agent-authored `c4-recon.yaml` input. Both are presence-gated and never enter the hard-required list.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_validator_c4_recon.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/validate.py tests/test_validator_c4_recon.py
git commit -m "feat(validate): register c4-recon.yaml -> c4-recon.schema.json (optional context rollup)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Wire `assemble-c4` into the synthesis flow after the apath barrier

**Files:**
- Modify: `.claude/workflows/apd-gauntlet.js:638` (insert `pyStep('assemble-c4', ...)` after the tmeval/apath `parallel([...])` close, before the `canonicalize-tmeval` pyStep)
- Modify: `tests/test_workflow_apd_gauntlet.py:189` (add `assemble-c4` to the pipeline-coverage pin)
- Test: `tests/test_workflow_apd_gauntlet.py` (extended below)

- [ ] **Step 1: Write the failing test** — add a focused structural assertion to `tests/test_workflow_apd_gauntlet.py`. Append this function at the end of the file:

```python
def test_assemble_c4_wired_after_apath_before_canonicalize() -> None:
    """assemble-c4 is the deterministic C4 assembler: it runs in the synthesis
    flow after the tmeval/apath parallel barrier (so asset-graph.yaml exists)
    and before the canonicalize-tmeval + rollup steps. Mirrors assemble-inventory."""
    text = _text()
    assert "pyStep('assemble-c4'" in text, "assemble-c4 must be dispatched via pyStep"
    apath_close = text.index("phase('apath')")
    c4_at = text.index("pyStep('assemble-c4'")
    canon_at = text.index("pyStep('canonicalize'")
    rollup_at = text.index("pyStep('rollup'")
    assert apath_close < c4_at < canon_at, (
        "assemble-c4 must run after the apath barrier and before canonicalize-tmeval"
    )
    assert c4_at < rollup_at, "assemble-c4 must run before rollup"
```

Also extend the existing `test_referenced_commands_cover_the_pipeline` pin. Replace:

```python
    for c in ("build-domain-skill", "validate-domain", "validate",
              "cluster-candidates", "apply-clusters", "rollup", "build-report",
              "audit-report", "summarize"):
        assert f"pyStep('{c}'" in text, f"pipeline command {c} not invoked via pyStep"
```

with:

```python
    for c in ("build-domain-skill", "validate-domain", "validate",
              "cluster-candidates", "apply-clusters", "rollup", "build-report",
              "audit-report", "summarize", "assemble-c4"):
        assert f"pyStep('{c}'" in text, f"pipeline command {c} not invoked via pyStep"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_workflow_apd_gauntlet.py::test_assemble_c4_wired_after_apath_before_canonicalize tests/test_workflow_apd_gauntlet.py::test_referenced_commands_cover_the_pipeline -v
```

Expected: both FAIL with `AssertionError` / `ValueError: substring not found` — `pyStep('assemble-c4'` is not yet in the runner.

- [ ] **Step 3: Write minimal implementation** — insert the step in `.claude/workflows/apd-gauntlet.js` immediately after the tmeval/apath `parallel([...]);` close (line 638), before the `// 5c.5 canonicalize` comment (line 640). Insert:

```javascript

// 5c.4 assemble-c4 (Python) — deterministic C4 model assembler. Runs HERE,
// after the tmeval/apath barrier so 40-synthesis/asset-graph.yaml exists, and
// BEFORE canonicalize/rollup. Mirrors assemble-inventory (ADR-0020 field
// ownership): the agent-authored 00-context/c4-recon.yaml + asset-graph.yaml
// are content-only; assemble-c4 is the SOLE minter of c4-/c4e- ids and the
// finding_count/capability_count badge rollups it writes to
// 40-synthesis/c4-model.yaml. It runs whenever asset-graph.yaml exists and
// includes the L4/L3 code tiers only when 00-context/code-evidence-index.yaml
// is present (the C4 scene then renders whatever c4-model.yaml contains).
pyStep('assemble-c4', {
  phase: 'apath', label: 'assemble-c4',
  outputs: runDir + '/40-synthesis/c4-model.yaml (c4-/c4e- ids minted; finding/capability badges rolled up)',
  alwaysRun: true,
});
```

> `alwaysRun: true` mirrors `assemble-inventory` and `canonicalize` (the work command is itself idempotent and presence-gates internally on `asset-graph.yaml`). The `phase: 'apath'` label keeps it inside the already-emitted apath breadcrumb, so no new `phase('…')` literal is needed and `test_every_meta_phase_is_emitted_one_way_or_the_other` is unaffected.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_workflow_apd_gauntlet.py -v
```

Expected: all tests PASS, including the new `test_assemble_c4_wired_after_apath_before_canonicalize`, the extended `test_referenced_commands_cover_the_pipeline`, and the pre-existing `test_every_cli_command_is_registered` (which passes only because M2 registered `assemble-c4` in `cli.commands`).

- [ ] **Step 5: Commit**

```
git add .claude/workflows/apd-gauntlet.js tests/test_workflow_apd_gauntlet.py
git commit -m "feat(workflow): wire assemble-c4 after apath barrier, before canonicalize/rollup

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Agent-lint gate — the edited apd-code-recon.md lints clean

**Files:**
- Test: `tests/test_lint_agent_apd_code_recon.py` (already created in Task 1; this task adds the global-lint cross-check and runs the dedicated `lint_agents` unit)

- [ ] **Step 1: Write the failing test** — extend the global lint-agents pytest to assert apd-code-recon is in scope and the c4-discipline reference resolves through the linter's Required-reading resolver. Append to `tests/test_lint_agents.py`:

```python
def test_code_recon_required_reading_resolves_c4_discipline() -> None:
    """The C4 extension adds .claude/skills/apd-c4-discipline/SKILL.md to
    code-recon's Required reading; lint_agent_file must resolve it (no
    'required reading target not found' error)."""
    from apd_gauntlet.lint_agents import lint_agent_file

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    agent = repo_root / ".claude" / "agents" / "apd-code-recon.md"
    errors = lint_agent_file(agent, repo_root)
    assert errors == [], errors
    assert "apd-c4-discipline" in agent.read_text()
```

(Confirm `import pathlib` is already present at the top of `tests/test_lint_agents.py`; it is used by the existing tests there. If not, add `import pathlib`.)

- [ ] **Step 2: Run test to verify it fails** — run BEFORE Task 1's edit is on disk (or, to demonstrate the failure mode, temporarily point the reference at a missing path):

```
pytest tests/test_lint_agents.py::test_code_recon_required_reading_resolves_c4_discipline -v
```

Expected (when the M2 skill is NOT yet present): FAIL — `lint_agent_file` returns `["…apd-code-recon.md: required reading target not found: .claude/skills/apd-c4-discipline/SKILL.md"]`, so `assert errors == []` fails. This proves the linter actively resolves the new Required-reading entry.

- [ ] **Step 3: Write minimal implementation** — no production code change is needed beyond Task 1's edits and the M2 skill; the linter already resolves `.claude/`-prefixed Required-reading paths (`tools/apd_gauntlet/lint_agents.py:61-64`). The implementation step here is to ensure the cited skill exists. Verify M2's skill is on disk:

```
test -f .claude/skills/apd-c4-discipline/SKILL.md && echo PRESENT || echo "MISSING — land M2 first"
```

If `MISSING`, the apd-c4-discipline skill is delivered in Milestone 2 and must be merged before this milestone's lint gate is green — that is the documented cross-milestone precondition, not a defect in this task.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_lint_agents.py::test_code_recon_required_reading_resolves_c4_discipline tests/test_lint_agent_apd_code_recon.py -v
```

Expected: all PASS. Also confirm the CLI lint command is clean end-to-end:

```
python -m apd_gauntlet.cli lint-agents --agent-dir .claude/agents
```

Expected stdout: a clean summary line reporting the agent count with exit code 0 (no `required reading target not found` and no `missing receipt contract section` for apd-code-recon).

- [ ] **Step 5: Commit**

```
git add tests/test_lint_agents.py
git commit -m "test(lint): assert apd-code-recon required reading resolves apd-c4-discipline

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

**Milestone exit check:**

```
pytest tests/test_lint_agent_apd_code_recon.py tests/test_c4_recon_schema.py tests/test_validator_c4_recon.py tests/test_workflow_apd_gauntlet.py tests/test_lint_agents.py tests/test_validator_code_evidence.py -v \
  && ruff check tools/apd_gauntlet/validate.py tests/test_c4_recon_schema.py tests/test_validator_c4_recon.py tests/test_lint_agent_apd_code_recon.py \
  && mypy tools/apd_gauntlet/validate.py \
  && python -m apd_gauntlet.cli lint-agents --agent-dir .claude/agents \
  && python -m apd_gauntlet.cli validate tests/fixtures/runs/c4-home-assistant --schema-only --errors-only
```

All selected pytest green; ruff/mypy clean on the touched modules; `lint-agents` exits 0 (the edited apd-code-recon.md resolves its new `apd-c4-discipline` Required-reading entry and keeps its receipt section); and the real home-assistant run still passes `validate --schema-only` (the additive `CONTEXT_ROLLUPS` entry is presence-gated, so a run with no `c4-recon.yaml` is unaffected, and a run that has one is now schema-checked). M2 (the `assemble-c4` Click command + `apd-c4-discipline` SKILL.md) must be merged before this milestone for `test_every_cli_command_is_registered` and the lint gate to be green.

---

## Milestone 4: Report data path — load c4-model.yaml + code-evidence-index.yaml into RunArtifacts and transform into window.APD_DATA.c4_model

**Files touched in this milestone:**

- `tools/apd_gauntlet/report/loader.py` — add `code_evidence_index` + `c4_model` optional fields to `RunArtifacts` (after line 117) and load them via `_yaml_optional` in `load_run` (around lines 605, 624, 654).
- `tools/apd_gauntlet/report/transform.py` — add `c4_model_view(artifacts)` (new fn, appended after `_asset_graph_view_focused`, ~line 1321) and register a `c4_model` section in `build_apd_data` (after the `attack_paths` tuple, ~line 2043).
- `tools/apd_gauntlet/validate.py` — register `c4-model.yaml -> c4-model.schema.json` in `SYNTHESIS_ROLLUPS` (~line 247) and `c4-recon.yaml -> c4-recon.schema.json` in `CONTEXT_ROLLUPS` (~line 292).
- `tests/unit/report/test_loader.py` — extend (load_run with/without files).
- `tests/unit/report/test_c4_model_view.py` — new (transform view shape + build_apd_data wiring).
- `tests/test_validate_c4_model.py` — new (schema registration, presence-gated).
- `tests/unit/report/conftest.py` — already supplies the `example_run` fixture; no change.

> Dependency note: Tasks 1–3 use a **self-contained `c4-model.yaml` fixture** (constructed in each test, conforming to the M2 `assemble_c4` contract) so the report data path is unit-isolated from M2. Task 4's schema registration requires `schemas/c4-model.schema.json` + `schemas/c4-recon.schema.json` (authored in **M1**); the Task-4 test guards on their on-disk presence. Task 5 (exit) depends on M2's `assemble-c4` having been run on a copied real run.

---

### Task 1: Add `code_evidence_index` + `c4_model` optional fields to `RunArtifacts` and load them in `load_run`

**Files:**
- Modify: `tools/apd_gauntlet/report/loader.py:117-148` (dataclass fields), `tools/apd_gauntlet/report/loader.py:604-624` (optional loads + hashes), `tools/apd_gauntlet/report/loader.py:663-665` (constructor kwargs)
- Test: `tests/unit/report/test_loader.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/report/test_loader.py`:

```python
def test_load_run_code_evidence_and_c4_absent_are_none(tmp_path: pathlib.Path) -> None:
    """A run with no code-evidence-index.yaml and no c4-model.yaml yields None
    for both new optional fields (never a guessed empty dict)."""
    src = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    dst = tmp_path / "run"
    import shutil

    shutil.copytree(src, dst)
    # The example fixture ships neither artifact; assert that precondition then load.
    assert not (dst / "00-context" / "code-evidence-index.yaml").is_file()
    assert not (dst / "40-synthesis" / "c4-model.yaml").is_file()
    artifacts = load_run(dst)
    assert artifacts.code_evidence_index is None
    assert artifacts.c4_model is None


def test_load_run_reads_code_evidence_and_c4_when_present(tmp_path: pathlib.Path) -> None:
    """When both optional artifacts exist, load_run returns parsed dicts and
    records their content hashes in source_hashes."""
    src = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    dst = tmp_path / "run"
    import shutil

    shutil.copytree(src, dst)
    (dst / "00-context" / "code-evidence-index.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: code_recon\n"
        "code_evidence_index:\n"
        "  entries:\n"
        "    - id: cev-aaaaaaaa\n"
        "      qualified_name: pkg.mod.fn\n"
        "      kind: function\n"
        "      file_path: pkg/mod.py\n"
        "      c4_container: api\n"
        "      c4_component: null\n"
        "      c4_level: code\n",
        encoding="utf-8",
    )
    (dst / "40-synthesis" / "c4-model.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: assemble_c4\n"
        "nodes:\n"
        "  - id: c4-11111111\n"
        "    level: container\n"
        "    parent: null\n"
        "    name: api\n"
        "    kind: service\n"
        "    provenance: {source: c4-recon.yaml, locator: 'containers[0]', repo: core}\n"
        "    finding_count: 3\n"
        "    capability_count: 1\n"
        "    analysis_state: analyzed\n"
        "edges: []\n"
        "build_summary: {node_count: 1, container_count: 1}\n",
        encoding="utf-8",
    )
    artifacts = load_run(dst)
    assert isinstance(artifacts.code_evidence_index, dict)
    assert artifacts.code_evidence_index["generated_by"] == "code_recon"
    assert isinstance(artifacts.c4_model, dict)
    assert artifacts.c4_model["nodes"][0]["id"] == "c4-11111111"
    assert "code-evidence-index.yaml" in artifacts.source_hashes
    assert "c4-model.yaml" in artifacts.source_hashes
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/unit/report/test_loader.py::test_load_run_code_evidence_and_c4_absent_are_none tests/unit/report/test_loader.py::test_load_run_reads_code_evidence_and_c4_when_present -v
```

Expected failure: `TypeError: __init__() got an unexpected keyword argument 'code_evidence_index'` is NOT yet raised (the fields don't exist), so the first failure is `AttributeError: 'RunArtifacts' object has no attribute 'code_evidence_index'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/apd_gauntlet/report/loader.py`, add two fields to the `RunArtifacts` dataclass. Insert immediately after the `active_taxonomies` field (after line 148):

```python
    # M4 / ADR-0021: the code-evidence-index (00-context/code-evidence-index.yaml)
    # is the grounded source for L4 code anchors + per-entry c4_* tags. Optional —
    # None on runs without code_recon. Consumed by the C4 architecture scene's
    # code tier. Loaded verbatim; the transform does not re-derive ids from it.
    code_evidence_index: dict[str, Any] | None = None
    # M4 / ADR-0021: the assembled C4 model (40-synthesis/c4-model.yaml, minted by
    # assemble_c4). Optional — None when assemble-c4 did not run (no asset-graph,
    # or pre-feature run). Consumed by transform.c4_model_view -> window.APD_DATA.
    # .c4_model. Presence-gated exactly like asset_graph.
    c4_model: dict[str, Any] | None = None
```

In `load_run`, add the two optional loads. Insert immediately after the `maswe_coverage` load (after line 605):

```python
    # M4 / ADR-0021: grounded C4 architecture inputs. The code-evidence-index is
    # the L4/code-tier source; c4-model.yaml is the assembled (id-minted) model.
    # Both optional — None on runs without code_recon / without assemble-c4.
    code_evidence_index = _yaml_optional(context / "code-evidence-index.yaml")
    c4_model = _yaml_optional(synth / "c4-model.yaml")
```

Add their hashes alongside the other optional hashes. Insert after the `maswe_coverage` hash block (after line 624):

```python
    if code_evidence_index is not None:
        source_hashes["code-evidence-index.yaml"] = _hash(
            context / "code-evidence-index.yaml"
        )
    if c4_model is not None:
        source_hashes["c4-model.yaml"] = _hash(synth / "c4-model.yaml")
```

Add the two constructor kwargs to the `return RunArtifacts(...)` call. Insert after `active_taxonomies=_extract_str_list(run_cfg, "taxonomies"),` (after line 665):

```python
        code_evidence_index=code_evidence_index,
        c4_model=c4_model,
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest tests/unit/report/test_loader.py -v
```

Expected: `test_load_run_code_evidence_and_c4_absent_are_none PASSED`, `test_load_run_reads_code_evidence_and_c4_when_present PASSED`, and all pre-existing loader tests still PASS.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/report/loader.py tests/unit/report/test_loader.py
git commit -m "feat(report): load code-evidence-index + c4-model into RunArtifacts

Add optional code_evidence_index and c4_model fields (None when absent),
loaded via _yaml_optional and hashed into source_hashes. Presence-gated
exactly like asset_graph (ADR-0021).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `transform.py :: c4_model_view(artifacts)` producing the exact window shape

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:1321` (append `c4_model_view` after `_asset_graph_view_focused`)
- Test: `tests/unit/report/test_c4_model_view.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/report/test_c4_model_view.py`:

```python
"""Unit tests for transform.c4_model_view — the window.APD_DATA.c4_model shape."""
from __future__ import annotations

import dataclasses
import pathlib

from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import c4_model_view

REPO = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _with_c4(c4_model: dict | None) -> RunArtifacts:
    """Clone the example RunArtifacts, overriding the c4_model field."""
    base = load_run(EXAMPLE)
    return dataclasses.replace(base, c4_model=c4_model)


def _fixture_c4_model() -> dict:
    """A small c4-model.yaml conforming to the M2 assemble_c4 contract."""
    return {
        "schema_version": 1,
        "generated_by": "assemble_c4",
        "nodes": [
            {
                "id": "c4-aaaaaaaa",
                "level": "system",
                "parent": None,
                "name": "Home Assistant",
                "kind": "service",
                "provenance": {"source": "c4-recon.yaml", "locator": "system"},
                "finding_count": 0,
                "capability_count": 0,
                "analysis_state": "analyzed",
            },
            {
                "id": "c4-bbbbbbbb",
                "level": "container",
                "parent": "c4-aaaaaaaa",
                "name": "core",
                "kind": "service",
                "provenance": {
                    "source": "c4-recon.yaml",
                    "locator": "containers[0]",
                    "repo": "core",
                    "machine_extracted": True,
                },
                "finding_count": 5,
                "capability_count": 2,
                "analysis_state": "analyzed",
            },
            {
                "id": "c4-cccccccc",
                "level": "container",
                "parent": "c4-aaaaaaaa",
                "name": "addons",
                "kind": "service",
                "provenance": {"source": "asset-inventory.yaml", "locator": "assets[7]"},
                "finding_count": 0,
                "capability_count": 0,
                "analysis_state": "not_analyzed",
            },
            {
                "id": "c4-dddddddd",
                "level": "code",
                "parent": "c4-bbbbbbbb",
                "name": "homeassistant.auth.AuthManager.async_create_access_token",
                "kind": "compute",
                "provenance": {
                    "source": "code-evidence-index.yaml",
                    "locator": "entries[0]",
                    "repo": "core",
                },
                "finding_count": 2,
                "capability_count": 0,
                "analysis_state": "analyzed",
            },
        ],
        "edges": [
            {
                "id": "c4e-eeeeeeee",
                "edge_type": "uses",
                "from": "c4-bbbbbbbb",
                "to": "c4-cccccccc",
                "label": "supervises",
                "machine_extracted": True,
                "provenance": {"source": "code-evidence-index.yaml", "locator": "entries[40]"},
            }
        ],
        "build_summary": {
            "node_count": 4,
            "system_count": 1,
            "container_count": 2,
            "code_count": 1,
            "uses_edge_count": 1,
            "unlocalized_finding_count": 6,
            "not_analyzed_container_count": 1,
        },
    }


def test_c4_model_view_absent_is_not_present() -> None:
    view = c4_model_view(_with_c4(None))
    assert view["present"] is False
    assert view["nodes"] == []
    assert view["edges"] == []
    assert view["unlocalized_findings"] == 0
    assert view["not_analyzed_count"] == 0
    assert view["levels_present"] == []


def test_c4_model_view_present_maps_nodes() -> None:
    view = c4_model_view(_with_c4(_fixture_c4_model()))
    assert view["present"] is True
    by_id = {n["id"]: n for n in view["nodes"]}
    assert set(by_id) == {"c4-aaaaaaaa", "c4-bbbbbbbb", "c4-cccccccc", "c4-dddddddd"}

    core = by_id["c4-bbbbbbbb"]
    # type == the C4 level; parent passes through; badge == finding_count.
    assert core["type"] == "container"
    assert core["parent"] == "c4-aaaaaaaa"
    assert core["label"] == "core"
    assert core["badge"] == 5
    assert core["capability_badge"] == 2
    assert core["analysis_state"] == "analyzed"
    assert core["provenance"]["repo"] == "core"

    # A zero-finding node carries badge == null (None), never a literal 0 chip.
    addons = by_id["c4-cccccccc"]
    assert addons["badge"] is None
    assert addons["analysis_state"] == "not_analyzed"


def test_c4_model_view_maps_edges() -> None:
    view = c4_model_view(_with_c4(_fixture_c4_model()))
    assert len(view["edges"]) == 1
    e = view["edges"][0]
    assert e["id"] == "c4e-eeeeeeee"
    assert e["source"] == "c4-bbbbbbbb"
    assert e["target"] == "c4-cccccccc"
    assert e["label"] == "supervises"
    assert e["machine_extracted"] is True


def test_c4_model_view_surfaces_rollups_and_levels() -> None:
    view = c4_model_view(_with_c4(_fixture_c4_model()))
    assert view["unlocalized_findings"] == 6
    assert view["not_analyzed_count"] == 1
    # levels_present is the distinct set of node levels, in canonical order.
    assert view["levels_present"] == ["system", "container", "code"]


def test_c4_model_view_missing_build_summary_defaults_zero() -> None:
    model = _fixture_c4_model()
    del model["build_summary"]
    view = c4_model_view(_with_c4(model))
    assert view["present"] is True
    assert view["unlocalized_findings"] == 0
    assert view["not_analyzed_count"] == 1  # derived from node analysis_state fallback
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/unit/report/test_c4_model_view.py -v
```

Expected failure: `ImportError: cannot import name 'c4_model_view' from 'apd_gauntlet.report.transform'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/apd_gauntlet/report/transform.py`, append immediately after `_asset_graph_view_focused` (after line 1320, before `_build_node_edge_maps`):

```python
# Canonical C4 level ordering (top → bottom). Drives levels_present ordering so
# the scene renders L1 System → … → L4 Code deterministically regardless of the
# node emission order in c4-model.yaml.
_C4_LEVEL_ORDER = ("system", "person", "external_system", "container", "component", "code")


def c4_model_view(artifacts: RunArtifacts) -> dict[str, Any]:
    """Structured C4-architecture view for window.APD_DATA.c4_model.

    Pure, side-effect-free transform of the assembled c4-model.yaml (already
    id-minted by assemble_c4 — this fn mints nothing). Mirrors _asset_graph_view
    in style: it shapes nodes/edges for the Cytoscape scene and passes through
    the assembler's grounded badge counts and rollups verbatim.

    Returns ``{"present": False, ...}`` (empty collections, zero rollups) when
    the run has no c4-model.yaml, so the scene is gated cleanly.

    Node shape:  {id, label, type(=level), parent, badge(=finding_count|None),
                  capability_badge, analysis_state, provenance}
      - ``badge`` is the assembler's finding_count, or None when 0 so a
        zero-finding element renders no chip (never "0 findings = clean").
    Edge shape:  {id, source, target, label, machine_extracted}
    Plus rollups: ``unlocalized_findings`` and ``not_analyzed_count`` (read off
    build_summary when present; not_analyzed_count falls back to a node scan),
    and ``levels_present`` (distinct node levels in canonical L1→L4 order).
    """
    model = artifacts.c4_model
    if not isinstance(model, dict):
        return {
            "present": False,
            "nodes": [],
            "edges": [],
            "unlocalized_findings": 0,
            "not_analyzed_count": 0,
            "levels_present": [],
        }

    nodes: list[dict[str, Any]] = []
    levels_seen: set[str] = set()
    not_analyzed_fallback = 0
    for n in model.get("nodes", []):
        if not isinstance(n, dict):
            continue
        level = str(n.get("level") or "container")
        levels_seen.add(level)
        finding_count = n.get("finding_count")
        try:
            fc = int(finding_count)
        except (TypeError, ValueError):
            fc = 0
        cap_count = n.get("capability_count")
        try:
            cc = int(cap_count)
        except (TypeError, ValueError):
            cc = 0
        analysis_state = str(n.get("analysis_state") or "analyzed")
        if level == "container" and analysis_state == "not_analyzed":
            not_analyzed_fallback += 1
        node: dict[str, Any] = {
            "id": _safe_node_id(str(n.get("id") or ""), fallback_seed="c4"),
            "label": _safe_label(str(n.get("name") or n.get("id") or "")),
            "type": level,
            "parent": (str(n["parent"]) if n.get("parent") else None),
            # Grounded badge: None (no chip) when zero — never render "0 = clean".
            "badge": (fc if fc > 0 else None),
            "capability_badge": cc,
            "analysis_state": analysis_state,
        }
        prov = n.get("provenance")
        if isinstance(prov, dict):
            node["provenance"] = {
                k: prov.get(k)
                for k in ("source", "locator", "repo", "machine_extracted")
                if prov.get(k) is not None
            }
        else:
            node["provenance"] = {}
        nodes.append(node)

    edges: list[dict[str, Any]] = []
    for e in model.get("edges", []):
        if not isinstance(e, dict):
            continue
        edges.append({
            "id": str(e.get("id") or ""),
            "source": _safe_node_id(str(e.get("from") or ""), fallback_seed="c4"),
            "target": _safe_node_id(str(e.get("to") or ""), fallback_seed="c4"),
            "label": _safe_label(str(e.get("label") or "")),
            "machine_extracted": bool(e.get("machine_extracted")),
        })

    summary = model.get("build_summary") or {}
    try:
        unlocalized = int(summary.get("unlocalized_finding_count", 0))
    except (TypeError, ValueError):
        unlocalized = 0
    not_analyzed = summary.get("not_analyzed_container_count")
    try:
        not_analyzed = int(not_analyzed)
    except (TypeError, ValueError):
        not_analyzed = not_analyzed_fallback

    levels_present = [lvl for lvl in _C4_LEVEL_ORDER if lvl in levels_seen]
    return {
        "present": True,
        "nodes": nodes,
        "edges": edges,
        "unlocalized_findings": unlocalized,
        "not_analyzed_count": not_analyzed,
        "levels_present": levels_present,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest tests/unit/report/test_c4_model_view.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_c4_model_view.py
git commit -m "feat(report): c4_model_view transform -> window.APD_DATA.c4_model

Pure transform of the assembled c4-model.yaml into the C4 scene window shape
({present, nodes, edges, unlocalized_findings, not_analyzed_count,
levels_present}). present=false when c4_model is None; node type=level;
badge=finding_count or null (never 0=clean); reuses _safe_node_id/_safe_label.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Wire `c4_model_view` into `build_apd_data` so `window.APD_DATA.c4_model` is populated

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py:2041-2043` (add the `c4_model` section tuple)
- Test: `tests/unit/report/test_c4_model_view.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/report/test_c4_model_view.py`:

```python
from apd_gauntlet.report.transform import build_apd_data


def test_build_apd_data_includes_c4_model_present() -> None:
    artifacts = _with_c4(_fixture_c4_model())
    data = build_apd_data(artifacts)
    assert "c4_model" in data
    assert data["c4_model"]["present"] is True
    assert len(data["c4_model"]["nodes"]) == 4
    assert data["c4_model"]["levels_present"] == ["system", "container", "code"]
    # The section must not have errored.
    assert "c4_model" not in data["meta"]["section_errors"]


def test_build_apd_data_c4_model_absent_present_false() -> None:
    artifacts = _with_c4(None)
    data = build_apd_data(artifacts)
    assert "c4_model" in data
    assert data["c4_model"]["present"] is False
    assert data["c4_model"]["nodes"] == []
    assert "c4_model" not in data["meta"]["section_errors"]
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/unit/report/test_c4_model_view.py::test_build_apd_data_includes_c4_model_present tests/unit/report/test_c4_model_view.py::test_build_apd_data_c4_model_absent_present_false -v
```

Expected failure: `KeyError: 'c4_model'` (the `data` dict has no `c4_model` key — the section isn't registered).

- [ ] **Step 3: Write minimal implementation**

In `tools/apd_gauntlet/report/transform.py`, inside the `sections` list in `build_apd_data`, insert a tuple immediately after the `attack_paths` tuple (after line 2043, before the `next_steps` tuple). The placeholder mirrors the `present: False` empty shape so a section fault still yields a cleanly-gated scene:

```python
        ("c4_model",
         lambda: c4_model_view(artifacts),
         {
             "present": False,
             "nodes": [],
             "edges": [],
             "unlocalized_findings": 0,
             "not_analyzed_count": 0,
             "levels_present": [],
         }),
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest tests/unit/report/test_c4_model_view.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_c4_model_view.py
git commit -m "feat(report): wire c4_model section into build_apd_data

Register c4_model_view as a build_apd_data section so window.APD_DATA.c4_model
is populated (present true/false). Per-section isolation placeholder is the
present:false empty shape so a section fault gates the scene cleanly.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Register `c4-model.yaml` + `c4-recon.yaml` in `validate.py` (optional, presence-gated)

**Files:**
- Modify: `tools/apd_gauntlet/validate.py:247` (add to `SYNTHESIS_ROLLUPS`), `tools/apd_gauntlet/validate.py:292` (add to `CONTEXT_ROLLUPS`)
- Test: `tests/test_validate_c4_model.py` (new)

> Requires `schemas/c4-model.schema.json` and `schemas/c4-recon.schema.json` (authored in M1). The test skips if either schema is absent so the milestones can be developed independently; once M1 has landed it asserts hard.

- [ ] **Step 1: Write the failing test**

Create `tests/test_validate_c4_model.py`:

```python
"""validate.py registers c4-model.yaml + c4-recon.yaml (optional, presence-gated)."""
from __future__ import annotations

import pathlib
import shutil

import pytest
from apd_gauntlet.cli import main
from apd_gauntlet.validate import CONTEXT_ROLLUPS, SCHEMAS_DIR, SYNTHESIS_ROLLUPS
from click.testing import CliRunner

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "runs"


def test_c4_model_registered_in_synthesis_rollups() -> None:
    assert SYNTHESIS_ROLLUPS.get("c4-model.yaml") == "c4-model.schema.json"


def test_c4_recon_registered_in_context_rollups() -> None:
    assert CONTEXT_ROLLUPS.get("c4-recon.yaml") == "c4-recon.schema.json"


def test_validate_passes_clean_run_without_c4_model() -> None:
    """c4-model.yaml is presence-gated: a clean run lacking it still validates."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(FIXTURES / "clean-run")])
    assert result.exit_code == 0, result.output


def test_validate_flags_malformed_c4_model(tmp_path: pathlib.Path) -> None:
    """A present-but-malformed c4-model.yaml is caught by the schema pass."""
    if not (SCHEMAS_DIR / "c4-model.schema.json").is_file():
        pytest.skip("c4-model.schema.json not authored yet (M1)")
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    # nodes must be an array per the schema; a scalar is malformed.
    (dst / "40-synthesis" / "c4-model.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: assemble_c4\n"
        "nodes: not-a-list\n"
        "edges: []\n"
        "build_summary: {}\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 1
    assert "c4-model.yaml" in result.output


def test_validate_accepts_valid_c4_model(tmp_path: pathlib.Path) -> None:
    """A present, well-formed c4-model.yaml validates cleanly (presence-gated)."""
    if not (SCHEMAS_DIR / "c4-model.schema.json").is_file():
        pytest.skip("c4-model.schema.json not authored yet (M1)")
    dst = tmp_path / "run"
    shutil.copytree(FIXTURES / "clean-run", dst)
    (dst / "40-synthesis" / "c4-model.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: assemble_c4\n"
        "nodes:\n"
        "  - id: c4-11111111\n"
        "    level: container\n"
        "    parent: null\n"
        "    name: api\n"
        "    kind: service\n"
        "    provenance: {source: c4-recon.yaml, locator: 'containers[0]'}\n"
        "    finding_count: 0\n"
        "    capability_count: 0\n"
        "    analysis_state: analyzed\n"
        "edges: []\n"
        "build_summary:\n"
        "  node_count: 1\n"
        "  system_count: 0\n"
        "  person_count: 0\n"
        "  external_system_count: 0\n"
        "  container_count: 1\n"
        "  component_count: 0\n"
        "  code_count: 0\n"
        "  uses_edge_count: 0\n"
        "  unlocalized_finding_count: 0\n"
        "  not_analyzed_container_count: 0\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(dst)])
    assert result.exit_code == 0, result.output
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/test_validate_c4_model.py::test_c4_model_registered_in_synthesis_rollups tests/test_validate_c4_model.py::test_c4_recon_registered_in_context_rollups -v
```

Expected failure: `AssertionError: assert None == 'c4-model.schema.json'` (the key is not yet in `SYNTHESIS_ROLLUPS`), and the same for `c4-recon.yaml` in `CONTEXT_ROLLUPS`.

- [ ] **Step 3: Write minimal implementation**

In `tools/apd_gauntlet/validate.py`, add the synthesis entry. Insert in the `SYNTHESIS_ROLLUPS` dict immediately after the `defense-graph.yaml` line (after line 247):

```python
    # M4 / ADR-0021: the assembled grounded C4 model. Optional / presence-gated
    # exactly like asset-graph: validated only when assemble-c4 produced it.
    "c4-model.yaml":               "c4-model.schema.json",
```

In `tools/apd_gauntlet/validate.py`, add the context entry. Insert in the `CONTEXT_ROLLUPS` dict immediately after the `asset-inventory.yaml` line (after line 292):

```python
    # M4 / ADR-0021: the agent-authored C4 recon input (code_recon output).
    # Optional; validated only when present (code_recon runs).
    "c4-recon.yaml":                "c4-recon.schema.json",
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest tests/test_validate_c4_model.py -v
```

Expected: `test_c4_model_registered_in_synthesis_rollups PASSED`, `test_c4_recon_registered_in_context_rollups PASSED`, `test_validate_passes_clean_run_without_c4_model PASSED`. The malformed/valid tests PASS once M1's `schemas/c4-model.schema.json` exists, else they SKIP.

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/validate.py tests/test_validate_c4_model.py
git commit -m "feat(validate): register c4-model.yaml + c4-recon.yaml schemas

Wire c4-model.yaml -> c4-model.schema.json (SYNTHESIS_ROLLUPS) and
c4-recon.yaml -> c4-recon.schema.json (CONTEXT_ROLLUPS). Both optional and
presence-gated like asset-graph (ADR-0021).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Milestone exit — full report build on a copied real run yields `window.APD_DATA.c4_model.present == true`

**Files:**
- Test: `tests/unit/report/test_c4_model_real_run.py` (new)

> This is the end-to-end integration check. It copies the real Home Assistant run, runs M2's `assemble-c4` CLI to produce `40-synthesis/c4-model.yaml`, then runs the full `build_apd_data` and asserts the populated `c4_model` block. The test **skips** if the `assemble-c4` CLI is not yet present (M2 not landed) so M4 stands alone; once M2 has landed it asserts hard.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/report/test_c4_model_real_run.py`:

```python
"""Milestone-4 exit: end-to-end c4_model in window.APD_DATA on the committed fixture run."""
from __future__ import annotations

import pathlib
import shutil

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import build_apd_data, c4_model_view
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"


def _assemble_c4_available() -> bool:
    try:
        from apd_gauntlet import assemble_c4  # noqa: F401
        from apd_gauntlet.cli import main  # noqa: F401
    except ImportError:
        return False
    from apd_gauntlet.cli import main

    return "assemble-c4" in (main.commands or {})


pytestmark = pytest.mark.skipif(
    not REAL_RUN.is_dir(), reason="real home-assistant run not present"
)


def _copy_and_assemble(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(REAL_RUN, dst)
    # Remove any previously-shipped c4-model so we assemble fresh from M2.
    stale = dst / "40-synthesis" / "c4-model.yaml"
    if stale.exists():
        stale.unlink()
    runner = CliRunner()
    result = runner.invoke(main_cli(), ["assemble-c4", str(dst)])
    assert result.exit_code == 0, result.output
    return dst


def main_cli():
    from apd_gauntlet.cli import main

    return main


def test_real_run_c4_model_present_with_expected_counts(tmp_path: pathlib.Path) -> None:
    if not _assemble_c4_available():
        pytest.skip("assemble-c4 CLI not present yet (M2)")
    run = _copy_and_assemble(tmp_path)
    assert (run / "40-synthesis" / "c4-model.yaml").is_file()

    artifacts = load_run(run)
    assert artifacts.c4_model is not None
    assert artifacts.code_evidence_index is not None

    view = c4_model_view(artifacts)
    assert view["present"] is True
    # Container tier (L2) is grounded from asset-graph (75 nodes) + recon; the
    # code tier (L4) is present because code-evidence-index.yaml exists (40 anchors).
    assert "container" in view["levels_present"]
    assert "code" in view["levels_present"]
    # The run has 14 zero-anchor repos -> at least one not_analyzed container.
    assert view["not_analyzed_count"] >= 1
    # Honesty: doc-anchored-but-unlocalized findings are surfaced, never dropped.
    assert view["unlocalized_findings"] >= 0

    data = build_apd_data(artifacts, run_dir=run)
    assert data["c4_model"]["present"] is True
    assert data["c4_model"]["nodes"]
    assert "c4_model" not in data["meta"]["section_errors"]
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest tests/unit/report/test_c4_model_real_run.py -v
```

Expected: before M2 lands, `test_real_run_c4_model_present_with_expected_counts SKIPPED (assemble-c4 CLI not present yet (M2))`. After M2 lands but before this milestone's Tasks 1–3, it would fail at `artifacts.c4_model is not None` / `AttributeError` — confirming the data-path wiring is what the test exercises.

- [ ] **Step 3: Write minimal implementation**

No production code is added in this task — Tasks 1–4 already implement the data path; this is the integration assertion that composes M2 (assembler/CLI) with M4 (loader + transform + build). The test file written in Step 1 is the deliverable.

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest tests/unit/report/test_c4_model_real_run.py -v
```

Expected (with M2 landed): `test_real_run_c4_model_present_with_expected_counts PASSED`. Without M2: `SKIPPED` (green run, integration deferred to M2 merge).

- [ ] **Step 5: Commit**

```
git add tests/unit/report/test_c4_model_real_run.py
git commit -m "test(report): milestone-4 exit — c4_model present on the real run

End-to-end check: copy the home-assistant run, assemble-c4 (M2), load_run +
build_apd_data, assert window.APD_DATA.c4_model.present with container+code
levels, not_analyzed_count>=1, and no section error. Skips until the
assemble-c4 CLI (M2) is present so M4 stands alone.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

**Milestone exit check:**

```
python -m pytest \
  tests/unit/report/test_loader.py \
  tests/unit/report/test_c4_model_view.py \
  tests/unit/report/test_c4_model_real_run.py \
  tests/test_validate_c4_model.py \
  -v \
&& ruff check tools/apd_gauntlet/report/loader.py tools/apd_gauntlet/report/transform.py tools/apd_gauntlet/validate.py \
&& mypy tools/apd_gauntlet/report/loader.py tools/apd_gauntlet/report/transform.py
```

Expected: all listed tests PASS (the two M2-gated tests SKIP until M2 lands, then PASS), `ruff` reports `All checks passed!`, and `mypy` reports `Success: no issues found`. Run the full suite (`python -m pytest -q`) before opening the PR to confirm no pre-existing loader/transform/validate test regressed (the new `RunArtifacts` fields default to `None`, the new section is additive, and the schema registrations are presence-gated, so the existing example/golden tests are unaffected).

---

## Milestone 5: The C4 report SCENE (React/Cytoscape) + bundle rebuild + freshness gate

This milestone builds the front-end half of the grounded C4 architecture view. It assumes Milestones 1–4 (the `c4-recon.yaml` artifact, `c4-model.schema.json`, `assemble_c4.py` assembler + `assemble-c4` CLI, the loader/validate wiring, and the `report/transform.py :: c4_model_view`) have landed and that `window.APD_DATA.c4_model` is populated for code-recon runs. M5 wires the React scene, the tab, the CSS, the bundle rebuild, and the bundle/render assertions. M6 (stretch) overlays a selected attack path onto the C4 scene.

**Files touched in this milestone:**

- Create: `report-template/screens/C4.jsx`
- Modify: `report-template/.build/entry.jsx:13-26` (register the new screen import — REQUIRED or it never bundles)
- Modify: `report-template/app.jsx:23-33` (BASE_TABS), `report-template/app.jsx:142-147` (scene routing)
- Modify: `report-template/screens.css` (append C4 scene styles)
- Modify: `tools/apd_gauntlet/data/report-template/app.js` + `tools/apd_gauntlet/data/report-template/.source-hash` (regenerated by the build, committed)
- Modify: `tools/apd_gauntlet/data/report-template/screens.css` (regenerated by the build, committed)
- Test: `tests/test_workflow_apd_gauntlet.py` (append C4 scene + tab + bundle + rendered-report assertions)

---

### Task 1: `report-template/screens/C4.jsx` — the C4 scene

**Files:**
- Create: `report-template/screens/C4.jsx`
- Modify: `report-template/.build/entry.jsx:13-26`
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_c4_screen_exists_and_renders_blocks`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workflow_apd_gauntlet.py` (after `test_threat_model_screen_exists_and_renders_blocks`, currently ending line 696):

```python
# ── C4 architecture scene (Cytoscape compound) ───────────────────────────────
def test_c4_screen_exists_and_renders_blocks() -> None:
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # component declared + exported on window (bundle registration contract)
    assert "function C4(" in src and "window.C4 = C4" in src
    # consumes the contracted window key shape
    assert "data.c4_model" in src
    # reuses the shared compound-capable Cytoscape renderer with fcose layout
    assert "GraphView" in src and "MermaidGraph" not in src
    assert "compound={true}" in src or "compound" in src
    assert 'layout="fcose"' in src
    # drill-down level state: default L1+L2, click container -> components/code
    assert "selectedContainer" in src and "selectedComponent" in src
    # honest banner: unlocalized findings + not-analyzed containers
    assert "unlocalized_findings" in src and "not_analyzed_count" in src
    # not_analyzed styling hook on nodes
    assert "analysis_state" in src and "not_analyzed" in src
    # finding-badge deep-link into the Findings tab
    assert "onOpenFinding" in src
    # reuses the report design language, not bespoke styling
    assert "section-eyebrow" in src and "section-title" in src


def test_c4_screen_registered_in_bundle_entry() -> None:
    entry = (REPO / "report-template" / ".build" / "entry.jsx").read_text(encoding="utf-8")
    # The screen MUST be a side-effect import or window.C4 is never set in the bundle.
    assert 'import "../screens/C4.jsx";' in entry
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_screen_exists_and_renders_blocks tests/test_workflow_apd_gauntlet.py::test_c4_screen_registered_in_bundle_entry -v
```

Expected: both FAIL — `FileNotFoundError: ... report-template/screens/C4.jsx` for the first, and `AssertionError: assert 'import "../screens/C4.jsx";' in entry` for the second.

- [ ] **Step 3: Write minimal implementation**

Create `report-template/screens/C4.jsx`:

```jsx
// report-template/screens/C4.jsx
/* eslint-disable */
// C4 architecture scene — grounded System/Container/Component/Code view.
//
// Levels: L1 System Context · L2 Container · L3 Component · L4 Code. On load we
// show L1 (system/person/external_system) + L2 (containers). Clicking a container
// drills to its L3 components — or straight to its L4 code when L3 was blocked
// (the never-invent default: components are OMITTED unless an artifact grouped
// symbols, so most runs render L2 -> L4). Clicking a component shows its L4 code.
//
// Every node carries a FINDINGS badge (finding_count) rendered by GraphView's
// own `[badge]` label, plus a separate CAPABILITY badge in the per-node list.
// The honest banner surfaces unlocalized doc-anchored findings (no code locator)
// and "not_analyzed" containers (repos with zero code anchors) — never rendered
// as "0 findings = clean". The interactive render + zoom toolbar live in the
// shared compound-capable GraphView (components.jsx); we feed it compound=true +
// fcose so containment (n.parent) lays out as nested boxes.

function C4({ data, onOpenFinding }) {
  const c4 = data.c4_model;

  if (!c4 || !c4.present) {
    return (
      <div className="empty-state">
        <p>No grounded C4 architecture model was assembled for this run. The
        container/code tiers require a code-evidence index
        (<code>00-context/code-evidence-index.yaml</code>) produced by
        code-recon; the system/container tiers require
        <code>40-synthesis/asset-graph.yaml</code>. Enable code_recon in the run
        config to populate this view.</p>
      </div>
    );
  }

  const allNodes = c4.nodes || [];
  const allEdges = c4.edges || [];
  const nodeById = React.useMemo(() => {
    const m = {};
    allNodes.forEach((n) => { m[n.id] = n; });
    return m;
  }, [c4]);
  const childrenOf = React.useMemo(() => {
    const m = {};
    allNodes.forEach((n) => {
      if (!n.parent) return;
      (m[n.parent] = m[n.parent] || []).push(n.id);
    });
    return m;
  }, [c4]);

  // Drill state. selectedContainer null = L1+L2 default; clicking a container
  // node selects it (revealing its components, or its code when components are
  // absent). selectedComponent narrows further to that component's L4 code.
  const [selectedContainer, setSelectedContainer] = React.useState(null);
  const [selectedComponent, setSelectedComponent] = React.useState(null);

  // Build the visible subgraph for the current drill level. Memoized so the
  // GraphView `graph` prop identity is stable across unrelated re-renders.
  const graph = React.useMemo(() => {
    const isTop = (lvl) => lvl === "system" || lvl === "person" || lvl === "external_system";
    let keep = new Set();

    if (!selectedContainer) {
      // L1 + L2: tops + every container.
      allNodes.forEach((n) => {
        if (isTop(n.type) || n.type === "container") keep.add(n.id);
      });
    } else if (!selectedComponent) {
      // Container drill: tops (for context) + the selected container + its
      // direct children (components) OR, when it has no component children,
      // its code descendants. Also keep sibling containers dimmed-in for the
      // "uses" edges to remain meaningful.
      allNodes.forEach((n) => { if (isTop(n.type) || n.type === "container") keep.add(n.id); });
      const kids = childrenOf[selectedContainer] || [];
      const compKids = kids.filter((id) => nodeById[id] && nodeById[id].type === "component");
      const codeKids = kids.filter((id) => nodeById[id] && nodeById[id].type === "code");
      (compKids.length ? compKids : codeKids).forEach((id) => keep.add(id));
      // When components exist, also pull each component's code as a 3rd tier.
      compKids.forEach((cid) => (childrenOf[cid] || []).forEach((id) => keep.add(id)));
    } else {
      // Component drill: the container, the component, and that component's code.
      allNodes.forEach((n) => { if (isTop(n.type) || n.type === "container") keep.add(n.id); });
      keep.add(selectedComponent);
      (childrenOf[selectedComponent] || []).forEach((id) => keep.add(id));
    }

    const nodes = allNodes
      .filter((n) => keep.has(n.id))
      .map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        parent: keep.has(n.parent) ? n.parent : null,
        badge: n.badge,
        hot: n.analysis_state === "not_analyzed" ? false : (n.badge ? true : false),
        provenance: n.provenance,
      }));
    const ids = new Set(nodes.map((n) => n.id));
    const edges = allEdges
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .map((e) => ({ id: e.id, source: e.source, target: e.target, type: "uses", label: e.label }));
    return { nodes, edges };
  }, [c4, selectedContainer, selectedComponent]);

  // GraphView reports the tapped node id back to us so we can drive drill-down.
  // We piggy-back on its `paths`/`onSelectPath` cross-link contract: each "path"
  // here is a single node id, so a tap resolves to that node and we branch on
  // its level. (GraphView calls onSelectPath(hit.id|null); we map id -> level.)
  const tapTargets = React.useMemo(
    () => allNodes.map((n) => ({ id: n.id, edgeIds: [] })),
    [c4]
  );
  const onNodeTap = React.useCallback((nodeId) => {
    if (!nodeId) { setSelectedContainer(null); setSelectedComponent(null); return; }
    const n = nodeById[nodeId];
    if (!n) return;
    if (n.type === "container") { setSelectedContainer(nodeId); setSelectedComponent(null); }
    else if (n.type === "component") { setSelectedContainer(n.parent || selectedContainer); setSelectedComponent(nodeId); }
    // code/system/person/external_system taps do not change the drill level.
  }, [nodeById, selectedContainer]);

  const containers = allNodes.filter((n) => n.type === "container");
  const notAnalyzed = containers.filter((n) => n.analysis_state === "not_analyzed");
  const levelsPresent = c4.levels_present || [];

  // Per-node drill-list row: name, finding badge (deep-links to Findings),
  // capability badge, and a not_analyzed marker. Mirrors the AttackPaths chip idiom.
  function NodeRow({ n }) {
    const na = n.analysis_state === "not_analyzed";
    const findingId = n.provenance && n.provenance.first_finding_id;
    return (
      <li className={`c4-node-row ${na ? "c4-node-row--not-analyzed" : ""}`}>
        <button
          type="button"
          className="c4-node-row__name"
          onClick={() => onNodeTap(n.id)}
          title={na ? "Not analyzed — no code anchors in this repo" : `Drill into ${n.label}`}
        >
          <span className={`c4-level-chip c4-level-chip--${n.type}`}>{n.type}</span>
          {n.label}
        </button>
        {na && <span className="c4-badge c4-badge--not-analyzed" title="No code anchors — analysis_state: not_analyzed (NOT '0 findings = clean')">not analyzed</span>}
        {!na && n.badge != null && n.badge > 0 && (
          <button
            type="button"
            className="c4-badge c4-badge--finding"
            title={`${n.badge} finding${n.badge === 1 ? "" : "s"} on this element — open in Findings`}
            onClick={() => findingId && onOpenFinding && onOpenFinding(findingId)}
            disabled={!findingId || !onOpenFinding}
            style={{ cursor: findingId && onOpenFinding ? "pointer" : "default" }}
          >⚑ {n.badge}</button>
        )}
        {!na && n.badge != null && n.badge === 0 && (
          <span className="c4-badge c4-badge--clean" title="Analyzed, zero findings">0</span>
        )}
        {n.capability_badge != null && n.capability_badge > 0 && (
          <span className="c4-badge c4-badge--capability" title={`${n.capability_badge} confirmed capabilit${n.capability_badge === 1 ? "y" : "ies"}`}>🛡 {n.capability_badge}</span>
        )}
      </li>
    );
  }

  const drillCrumb = !selectedContainer
    ? "L1 System context + L2 Containers"
    : !selectedComponent
      ? `Container: ${(nodeById[selectedContainer] || {}).label}`
      : `Component: ${(nodeById[selectedComponent] || {}).label}`;

  const visibleContainerChildren = selectedContainer
    ? (childrenOf[selectedContainer] || []).map((id) => nodeById[id]).filter(Boolean)
    : [];

  return (
    <div className="c4-scene">
      <div className="section-eyebrow">§ Architecture — grounded C4 model</div>
      <h2 className="section-title">
        System → Container → Component → Code · {(c4.levels_present || []).join(" · ") || "context"}
      </h2>

      {/* Honest banner — never hide doc-only findings or not-analyzed repos. */}
      <div className="c4-banner">
        <strong>Grounded view.</strong>{" "}
        {containers.length} container{containers.length === 1 ? "" : "s"}
        {notAnalyzed.length > 0 && (
          <>
            {" · "}
            <span className="c4-banner__warn">
              {notAnalyzed.length} not analyzed
            </span>{" "}
            (no code anchors — shown as <em>not_analyzed</em>, never &ldquo;0 findings = clean&rdquo;)
          </>
        )}
        {c4.unlocalized_findings > 0 && (
          <>
            {" · "}
            <span className="c4-banner__warn">
              {c4.unlocalized_findings} unlocalized finding{c4.unlocalized_findings === 1 ? "" : "s"}
            </span>{" "}
            (doc-anchored, no <code>code:</code> locator — surfaced, not dropped)
          </>
        )}
      </div>

      {/* Drill breadcrumb + reset. */}
      <div className="c4-crumbs">
        <button
          type="button"
          className={`chip ${!selectedContainer ? "chip--active" : ""}`}
          onClick={() => { setSelectedContainer(null); setSelectedComponent(null); }}
        >⌂ System</button>
        <span className="c4-crumbs__sep">/</span>
        <span className="c4-crumbs__here">{drillCrumb}</span>
        {selectedContainer && (
          <button
            type="button"
            className="chip"
            onClick={() => setSelectedComponent(null)}
            disabled={!selectedComponent}
            style={{ marginLeft: "var(--space-2)" }}
          >↑ Up one level</button>
        )}
      </div>

      <section className="c4-scene__graph">
        <h3 className="c4-scene__section-h">Architecture graph</h3>
        <GraphView
          graph={graph}
          layout="fcose"
          compound={true}
          idBase="apd-c4-graph"
          paths={tapTargets}
          selectedPathId={null}
          onSelectPath={onNodeTap}
        />
      </section>

      {selectedContainer && (
        <section className="c4-scene__drill">
          <h3 className="c4-scene__section-h">
            {visibleContainerChildren.some((c) => c.type === "component")
              ? "Components"
              : "Code elements"}
          </h3>
          {visibleContainerChildren.length === 0 ? (
            <p className="empty-state empty-state--info">
              No grounded components or code elements under this container. L3
              components are blocked by default unless an artifact groups symbols;
              this container renders L2 → L4 with no code anchors indexed.
            </p>
          ) : (
            <ul className="c4-node-list">
              {visibleContainerChildren.map((n) => <NodeRow key={n.id} n={n} />)}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

window.C4 = C4;
```

Then register the screen in the bundle entry. Modify `report-template/.build/entry.jsx`, the import block (current lines 18–25):

```jsx
import "../components.jsx";
import "../screens/StartHere.jsx";
import "../screens/Overview.jsx";
import "../screens/Findings.jsx";
import "../screens/Capabilities.jsx";
import "../screens/Coverage.jsx";
import "../screens/ThreatModel.jsx";
import "../screens/C4.jsx";
import "../screens/Annexes.jsx";
import "../screens/AttackPaths.jsx";
import "../app.jsx";
```

(The single added line is `import "../screens/C4.jsx";`, inserted before `Annexes.jsx`.)

> Note: the contract specifies `c4_model_view(...)` may add `provenance.first_finding_id` so a node's finding badge can deep-link to a real finding. M1–M4's transform must populate it; the scene degrades gracefully (badge stays non-clickable) when it's absent.

- [ ] **Step 4: Run test to verify it passes**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_screen_exists_and_renders_blocks tests/test_workflow_apd_gauntlet.py::test_c4_screen_registered_in_bundle_entry -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```
git add report-template/screens/C4.jsx report-template/.build/entry.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): C4 architecture scene (Cytoscape compound, grounded drill-down)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Register the C4 tab in `app.jsx`, gated on `data.c4_model.present`

**Files:**
- Modify: `report-template/app.jsx:23-33` (BASE_TABS), `report-template/app.jsx:142-147` (scene routing)
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_c4_tab_is_conditional_and_routed`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workflow_apd_gauntlet.py`:

```python
def test_c4_tab_is_conditional_and_routed() -> None:
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    # tab entry present, gated on data.c4_model && data.c4_model.present (omit when absent)
    assert 'id: "c4"' in src and 'label: "Architecture"' in src
    assert "data.c4_model" in src and "data.c4_model.present" in src
    # routed to the screen, passing data + onOpenFinding
    assert 'activeTab === "c4"' in src and "<C4" in src
    assert "onOpenFinding={onOpenFinding}" in src.split('activeTab === "c4"')[1][:200]
    # placed after attack_paths, before annexes (engineering view sits late)
    i_ap = src.index('id: "attack_paths"')
    i_c4 = src.index('id: "c4"')
    i_annex = src.index('id: "annexes"')
    assert i_ap < i_c4 < i_annex
    # the conditional spread uses the SAME numbering machinery (sigil-aware map)
    assert "_tabNum" in src
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_tab_is_conditional_and_routed -v
```

Expected: FAIL — `AssertionError: assert 'id: "c4"' in src`.

- [ ] **Step 3: Write minimal implementation**

Modify `report-template/app.jsx` BASE_TABS (current lines 23–33) to insert the conditional C4 tab between `attack_paths` and `annexes`:

```jsx
  const BASE_TABS = [
    { id: "start_here", label: "Start here", sigil: "✦" },
    { id: "overview", label: "Overview" },
    { id: "findings", label: "Findings" },
    { id: "capabilities", label: "Capabilities" },
    { id: "coverage", label: "Coverage" },
    ...(data.threat_model && data.threat_model.present
      ? [{ id: "threat_model", label: "Threat model" }] : []),
    { id: "attack_paths", label: "Attack paths" },
    ...(data.c4_model && data.c4_model.present
      ? [{ id: "c4", label: "Architecture" }] : []),
    { id: "annexes", label: "Annexes" },
  ];
```

(The `_tabNum`/sigil numbering map at lines 34–39 is unchanged — the new numeric tab automatically takes the next `NN` because it carries no `sigil`.)

Modify `report-template/app.jsx` scene routing — insert a route after the `attack_paths` block (current lines 142–144), before the `annexes` block (current line 145):

```jsx
        {activeTab === "attack_paths" && (
          <AttackPaths data={data} onOpenFinding={onOpenFinding} focusPathId={focusPathId} />
        )}
        {activeTab === "c4" && (
          <C4 data={data} onOpenFinding={onOpenFinding} />
        )}
        {activeTab === "annexes" && (
          <Annexes data={data} onOpenFinding={onOpenFinding} />
        )}
```

- [ ] **Step 4: Run test to verify it passes**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_tab_is_conditional_and_routed -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add report-template/app.jsx tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): register Architecture (C4) tab gated on data.c4_model.present

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: CSS additions for the C4 scene (incl. `not_analyzed` styling)

**Files:**
- Modify: `report-template/screens.css` (append C4 block)
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_c4_scene_styles_present`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workflow_apd_gauntlet.py`:

```python
def test_c4_scene_styles_present() -> None:
    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    # scene container + section headers reuse the design tokens
    assert ".c4-scene" in css and ".c4-scene__section-h" in css
    # honest banner + its warning emphasis
    assert ".c4-banner" in css and ".c4-banner__warn" in css
    # per-node list + badges
    assert ".c4-node-list" in css and ".c4-node-row" in css
    assert ".c4-badge--finding" in css and ".c4-badge--capability" in css
    # not_analyzed must be styled DISTINCTLY (muted/striped), never as clean
    assert ".c4-node-row--not-analyzed" in css and ".c4-badge--not-analyzed" in css
    # level chips for the four C4 tiers
    assert ".c4-level-chip" in css
    # all colors come from CSS custom properties (theme-aware), no hex literals
    c4_block = css[css.index(".c4-scene"):]
    assert "var(--" in c4_block
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_scene_styles_present -v
```

Expected: FAIL — `ValueError: substring not found` at `css.index(".c4-scene")` (the `.c4-scene` token is absent).

- [ ] **Step 3: Write minimal implementation**

Append to the end of `report-template/screens.css`:

```css
/* ── C4 architecture scene ────────────────────────────────────────────── */
.c4-scene {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.c4-scene__section-h {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin: var(--space-3) 0 var(--space-1);
}
.c4-banner {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  color: var(--ink-2);
  background: var(--paper-2);
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
}
.c4-banner__warn {
  color: var(--sev-high);
  font-weight: 600;
}
.c4-crumbs {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-3);
}
.c4-crumbs__sep { color: var(--rule); }
.c4-crumbs__here { color: var(--ink); font-weight: 600; }
.c4-node-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.c4-node-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--paper);
}
/* not_analyzed: distinctly muted + striped — must NOT read as a clean container */
.c4-node-row--not-analyzed {
  background: repeating-linear-gradient(
    135deg,
    var(--paper-2),
    var(--paper-2) 6px,
    var(--paper) 6px,
    var(--paper) 12px
  );
  border-style: dashed;
  border-color: var(--ink-3);
  opacity: 0.85;
}
.c4-node-row__name {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  text-align: left;
  font: inherit;
  color: var(--ink);
  cursor: pointer;
  padding: 0;
}
.c4-node-row__name:hover { color: var(--accent); }
.c4-level-chip {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--paper-2);
  color: var(--ink-3);
  border: 1px solid var(--rule);
  white-space: nowrap;
}
.c4-level-chip--container { color: var(--accent); border-color: var(--accent); }
.c4-level-chip--component { color: var(--ink-2); }
.c4-level-chip--code { color: var(--ink-3); }
.c4-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
  border: 1px solid var(--rule);
  background: var(--paper-2);
  color: var(--ink-3);
}
.c4-badge--finding {
  background: color-mix(in srgb, var(--sev-high) 15%, var(--paper));
  color: var(--sev-high);
  border-color: var(--sev-high);
  cursor: pointer;
}
.c4-badge--finding:hover { text-decoration: underline; }
.c4-badge--capability {
  background: color-mix(in srgb, var(--sev-low) 15%, var(--paper));
  color: var(--sev-low);
  border-color: var(--sev-low);
}
.c4-badge--clean { color: var(--ink-3); }
.c4-badge--not-analyzed {
  color: var(--ink-3);
  border-style: dashed;
  border-color: var(--ink-3);
  font-style: italic;
}
```

- [ ] **Step 4: Run test to verify it passes**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_scene_styles_present -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add report-template/screens.css tests/test_workflow_apd_gauntlet.py
git commit -m "style(report): C4 scene CSS incl. striped not_analyzed container styling

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Rebuild the precompiled bundle + verify the freshness gate

**Files:**
- Modify: `tools/apd_gauntlet/data/report-template/app.js` (regenerated)
- Modify: `tools/apd_gauntlet/data/report-template/screens.css` (regenerated)
- Modify: `tools/apd_gauntlet/data/report-template/.source-hash` (regenerated)

- [ ] **Step 1: Write the failing test**

The "failing test" here is the freshness gate itself — after editing `report-template/screens/C4.jsx`, `entry.jsx`, `app.jsx`, and `screens.css` in Tasks 1–3, the committed `.source-hash` no longer matches the source tree. Run the gate to confirm it is RED before the rebuild:

```
.venv/bin/python tools/check_report_template_freshness.py
```

Expected (RED): exit code 1 with
```
check_report_template_freshness: report-template/ has changed since the precompiled bundle was generated.
Run `python tools/build_report_template.py` and commit the result.
  expected=64c2da4b6ac2309b2049bc60743b4bedfb8d07fd2a9a669004807254bac51f3c
  actual  =<new-hash>
```

- [ ] **Step 2: Run test to verify it fails**

(Same command as Step 1 — `echo $?` to confirm.)

```
.venv/bin/python tools/check_report_template_freshness.py; echo "exit=$?"
```

Expected: `exit=1`.

- [ ] **Step 3: Write minimal implementation** — rebuild the bundle

```
.venv/bin/python tools/build_report_template.py
```

Expected stdout (Node 20+/npm present — confirmed `node v26.0.0`, `npm` on PATH):
```
build-report-template: bundle written.
```

This regenerates `tools/apd_gauntlet/data/report-template/app.js` (now containing the bundled `C4` component + its `GraphView`/`fcose` usage), `screens.css`, and rewrites `tools/apd_gauntlet/data/report-template/.source-hash` to the new source hash.

- [ ] **Step 4: Run test to verify it passes** — freshness gate green

```
.venv/bin/python tools/check_report_template_freshness.py; echo "exit=$?"
```

Expected (GREEN):
```
check_report_template_freshness: OK (<new-12-hex>)
exit=0
```

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/data/report-template/app.js tools/apd_gauntlet/data/report-template/screens.css tools/apd_gauntlet/data/report-template/.source-hash
git commit -m "build(report): rebuild bundle for the C4 architecture scene

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Bundle + rendered-report assertions for the C4 scene

**Files:**
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_bundle_contains_c4_scene` + `test_built_report_renders_c4_tab_from_home_assistant_run`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workflow_apd_gauntlet.py`. The first assertion follows the `test_build_registers_cytoscape_not_mermaid` idiom (read the built bundle text); the second builds a report from a COPY of the real Home Assistant run (`runs/` `report-html` is gitignored, so we assemble `data.js` fresh and assert `c4_model.present`).

```python
def test_bundle_contains_c4_scene() -> None:
    # The precompiled bundle must carry the C4 component + its compound graph use.
    app_js = (
        REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "app.js"
    ).read_text(encoding="utf-8")
    assert "window.C4" in app_js            # screen exported into the bundle
    assert "c4_model" in app_js             # consumes the contracted window key
    assert "GraphView" in app_js            # reuses the shared Cytoscape renderer
    assert "fcose" in app_js                # compound layout requested
    assert "Architecture" in app_js         # the tab label is bundled


def test_built_report_renders_c4_tab_from_home_assistant_run(tmp_path) -> None:
    """End-to-end: assemble c4-model.yaml for the real Home Assistant run, build
    the report data, and assert the C4 tab is enabled (data.c4_model.present).
    runs/*/report-html is gitignored, so we assemble + build into tmp."""
    import shutil
    import yaml
    from apd_gauntlet.assemble_c4 import assemble_c4
    from apd_gauntlet.report.loader import load_run
    from apd_gauntlet.report.transform import build_apd_data

    src_run = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"
    assert src_run.is_dir(), "ground-truth run missing"
    run = tmp_path / "run"
    shutil.copytree(src_run, run)

    # Assemble the canonical c4-model.yaml (assembler is the sole id minter).
    summary = assemble_c4(run)
    c4_path = run / "40-synthesis" / "c4-model.yaml"
    assert c4_path.is_file(), "assemble_c4 did not write 40-synthesis/c4-model.yaml"
    c4_doc = yaml.safe_load(c4_path.read_text(encoding="utf-8"))
    assert c4_doc["generated_by"] == "assemble_c4"
    # Code tiers present because this run HAS a code-evidence-index.yaml.
    assert summary["container_count"] >= 1
    assert summary["not_analyzed_container_count"] >= 1   # 14 empty repos -> some not_analyzed

    artifacts = load_run(run)
    assert artifacts.c4_model is not None                 # loader picked it up
    data = build_apd_data(artifacts, run_dir=run)
    assert data["c4_model"] is not None
    assert data["c4_model"]["present"] is True            # the tab will render
    # honest fields are surfaced through to the view
    assert "unlocalized_findings" in data["c4_model"]
    assert "not_analyzed_count" in data["c4_model"]
    assert data["c4_model"]["not_analyzed_count"] >= 1
    # nodes carry the level + badge contract the scene consumes
    sample = data["c4_model"]["nodes"][0]
    for key in ("id", "label", "type", "parent", "badge", "analysis_state"):
        assert key in sample, f"c4_model node missing {key}"
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_bundle_contains_c4_scene tests/test_workflow_apd_gauntlet.py::test_built_report_renders_c4_tab_from_home_assistant_run -v
```

Expected before Task 4's rebuild runs: `test_bundle_contains_c4_scene` FAILS (`assert "window.C4" in app_js`). After Task 4 it PASSES, so to see a clean RED on the second test in isolation, run it against the not-yet-built state, expecting `ImportError`/`AttributeError` on `assemble_c4` only if M1–M4 were absent — by this point in the milestone sequence M1–M4 have landed, so the only remaining failure is the bundle text assertion until Task 4 completes.

- [ ] **Step 3: Write minimal implementation**

No production code in this task — the implementation is the Task 4 bundle rebuild (already done) and the M1–M4 `assemble_c4`/loader/transform wiring. This task only adds the two assertions above. The render test exercises the real artifacts end-to-end against the Home Assistant run.

- [ ] **Step 4: Run test to verify it passes**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_bundle_contains_c4_scene tests/test_workflow_apd_gauntlet.py::test_built_report_renders_c4_tab_from_home_assistant_run -v
```

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```
git add tests/test_workflow_apd_gauntlet.py
git commit -m "test(report): assert C4 scene in bundle + renders from home-assistant run

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**Milestone 5 exit check:**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "c4 or C4 or graph_view or bundle" -v \
  && .venv/bin/python tools/check_report_template_freshness.py \
  && .venv/bin/ruff check tools/apd_gauntlet \
  && .venv/bin/mypy tools/apd_gauntlet/assemble_c4.py tools/apd_gauntlet/report/transform.py
```

Expected: all selected pytest cases pass, freshness `OK`, ruff `All checks passed!`, mypy `Success: no issues found`.

---

## Milestone 6: Attack-path overlay on the C4 scene (stretch)

Adds a control to the C4 scene that selects an enumerated attack path (`data.attack_paths`) and highlights the C4 elements it traverses **only where a grounded asset→C4 mapping exists** (the M2 asset→container join; code-bearing findings onto code nodes). Hops with no C4 mapping are shown on a **parallel asset strip** — never invented as a C4 hop. Reuses the AttackPaths cross-highlight pattern (`paths`/`selectedPathId`/`onSelectPath` on `GraphView`).

**Files touched in this milestone:**

- Modify: `report-template/screens/C4.jsx` (overlay control + asset-strip + mapped-hop highlight)
- Modify: `tools/apd_gauntlet/data/report-template/app.js` + `.source-hash` + `screens.css` (regenerated)
- Modify: `report-template/screens.css` (append overlay styles)
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_c4_attack_path_overlay`)

> The grounded asset→C4 mapping that this overlay consumes is produced by the assembler (M2) and exposed on `window.APD_DATA.c4_model.asset_to_c4` — a `{asset_node_id: c4_node_id}` dict for hops whose asset endpoint joins to a container (and `c4_model.finding_to_c4` for code-bearing findings onto code nodes). The overlay NEVER computes a mapping client-side; it consumes the deterministic join and labels any hop absent from it as "no C4 mapping" on the asset strip.

---

### Task 6: Attack-path overlay control + honest partial highlight

**Files:**
- Modify: `report-template/screens/C4.jsx`
- Modify: `report-template/screens.css` (append `.c4-overlay*` block)
- Test: `tests/test_workflow_apd_gauntlet.py` (append `test_c4_attack_path_overlay`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_workflow_apd_gauntlet.py`:

```python
def test_c4_attack_path_overlay() -> None:
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # consumes the existing enumerated paths (no new data source)
    assert "data.attack_paths" in src
    # a selectable overlay control + its selection state
    assert "selectedOverlayPath" in src and "setSelectedOverlayPath" in src
    # consumes the DETERMINISTIC join, never computes a mapping client-side
    assert "asset_to_c4" in src and "finding_to_c4" in src
    # reuses GraphView's cross-highlight contract (overlay path -> highlighted c4 nodes)
    assert "overlayHighlight" in src or "overlayPaths" in src
    # honest partial overlay: hops with no C4 mapping go on a PARALLEL asset strip
    assert "c4-overlay-strip" in src and "no C4 mapping" in src
    # never invent: an unmapped hop is labelled, not rendered as a C4 hop
    assert "unmappedHops" in src

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    assert ".c4-overlay-strip" in css and ".c4-overlay-strip__hop--unmapped" in css
```

- [ ] **Step 2: Run test to verify it fails**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_attack_path_overlay -v
```

Expected: FAIL — `AssertionError: assert 'selectedOverlayPath' in src`.

- [ ] **Step 3: Write minimal implementation**

In `report-template/screens/C4.jsx`, add the overlay state + derived data inside `C4(...)`, immediately after the `selectedComponent` state declaration:

```jsx
  // ── Attack-path overlay (stretch) ──────────────────────────────────────
  // Select an enumerated attack path and highlight the C4 elements it traverses
  // WHERE a grounded asset->C4 join exists. The join is the assembler's
  // deterministic c4_model.asset_to_c4 (asset node id -> c4 node id) plus
  // finding_to_c4 (code-bearing finding id -> code c4 node id). Hops with no
  // mapping are NEVER invented onto the C4 graph — they go on a parallel strip.
  const ap = data.attack_paths;
  const assetToC4 = (c4 && c4.asset_to_c4) || {};
  const findingToC4 = (c4 && c4.finding_to_c4) || {};
  const overlayPaths = React.useMemo(() => {
    const pairs = (ap && ap.pairs) || [];
    return pairs.flatMap((pair) => (pair.paths || []).map((p) => ({
      id: p.path_id,
      label: `${pair.attacker_position_name || pair.attacker_position} → ${pair.crown_jewel_name || pair.crown_jewel} · ${p.path_id}`,
      hops: p.edges_detailed || (p.edges || []).map((eid) => ({ edge_id: eid })),
    })));
  }, [ap]);
  const [selectedOverlayPath, setSelectedOverlayPath] = React.useState(null);

  // Resolve one selected path into (a) c4 node ids to highlight, and
  // (b) the unmapped hops that belong on the parallel asset strip.
  const overlay = React.useMemo(() => {
    if (!selectedOverlayPath) return { c4NodeIds: [], unmappedHops: [] };
    const sel = overlayPaths.find((p) => p.id === selectedOverlayPath);
    if (!sel) return { c4NodeIds: [], unmappedHops: [] };
    const c4NodeIds = new Set();
    const unmappedHops = [];
    sel.hops.forEach((h) => {
      let mapped = false;
      // Asset endpoints -> container join.
      [h.from, h.to].forEach((aid) => {
        if (aid && assetToC4[aid]) { c4NodeIds.add(assetToC4[aid]); mapped = true; }
      });
      // Code-bearing finding -> code node join.
      if (h.finding_id && findingToC4[h.finding_id]) {
        c4NodeIds.add(findingToC4[h.finding_id]); mapped = true;
      }
      if (!mapped) {
        unmappedHops.push({
          edge_id: h.edge_id,
          from_name: h.from_name || h.from || "?",
          to_name: h.to_name || h.to || "?",
          finding_id: h.finding_id || null,
        });
      }
    });
    return { c4NodeIds: [...c4NodeIds], unmappedHops };
  }, [selectedOverlayPath, overlayPaths, assetToC4, findingToC4]);

  // Feed the highlight into GraphView via its path-cross-link contract: a single
  // synthetic "path" whose member nodes are the mapped c4 nodes. GraphView
  // highlights edges, so we expand to the induced edges between mapped nodes.
  const overlayHighlight = React.useMemo(() => {
    if (!overlay.c4NodeIds.length) return null;
    const idset = new Set(overlay.c4NodeIds);
    const edgeIds = allEdges
      .filter((e) => idset.has(e.source) && idset.has(e.target))
      .map((e) => e.id);
    return [{ id: "__overlay__", edgeIds, nodeIds: overlay.c4NodeIds }];
  }, [overlay, c4]);
```

Then change the `GraphView` invocation in the `<section className="c4-scene__graph">` block so that, when an overlay is active, it drives the highlight (otherwise it keeps the tap-to-drill behavior):

```jsx
        <GraphView
          graph={graph}
          layout="fcose"
          compound={true}
          idBase="apd-c4-graph"
          paths={overlayHighlight || tapTargets}
          selectedPathId={overlayHighlight ? "__overlay__" : null}
          onSelectPath={overlayHighlight ? () => {} : onNodeTap}
        />
```

Insert the overlay control + parallel asset strip directly above the `<section className="c4-scene__graph">` block:

```jsx
      {/* Attack-path overlay control (stretch) — honest partial highlight. */}
      {overlayPaths.length > 0 && (
        <div className="c4-overlay">
          <label className="c4-overlay__label" htmlFor="c4-overlay-select">
            Overlay attack path:
          </label>
          <select
            id="c4-overlay-select"
            className="c4-overlay__select"
            value={selectedOverlayPath || ""}
            onChange={(e) => setSelectedOverlayPath(e.target.value || null)}
          >
            <option value="">— none —</option>
            {overlayPaths.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
          {selectedOverlayPath && (
            <button
              type="button"
              className="chip"
              onClick={() => setSelectedOverlayPath(null)}
            >clear</button>
          )}
        </div>
      )}

      {selectedOverlayPath && overlay.unmappedHops.length > 0 && (
        <div className="c4-overlay-strip">
          <div className="c4-overlay-strip__head">
            Parallel asset hops — <strong>no C4 mapping</strong> (shown here, never
            invented onto the architecture graph):
          </div>
          <ol className="c4-overlay-strip__hops">
            {overlay.unmappedHops.map((h) => (
              <li key={h.edge_id} className="c4-overlay-strip__hop c4-overlay-strip__hop--unmapped">
                <span className="mono">{h.from_name}</span>
                <span className="c4-overlay-strip__arrow">→</span>
                <span className="mono">{h.to_name}</span>
                {h.finding_id && (
                  <button
                    type="button"
                    className="c4-badge c4-badge--finding"
                    onClick={() => onOpenFinding && onOpenFinding(h.finding_id)}
                    disabled={!onOpenFinding}
                    style={{ cursor: onOpenFinding ? "pointer" : "default" }}
                  >⚑ {h.finding_id}</button>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
```

Append the overlay styles to `report-template/screens.css` (after the C4 block from Task 3):

```css
/* ── C4 attack-path overlay (stretch) ─────────────────────────────────── */
.c4-overlay {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-3);
}
.c4-overlay__label { color: var(--ink-2); }
.c4-overlay__select {
  font: inherit;
  padding: 2px 6px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--ink);
  max-width: 28rem;
}
.c4-overlay-strip {
  border: 1px dashed var(--sev-high);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--sev-high) 6%, var(--paper));
  padding: var(--space-2) var(--space-3);
}
.c4-overlay-strip__head {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--ink-2);
  margin-bottom: var(--space-2);
}
.c4-overlay-strip__hops {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.c4-overlay-strip__hop {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}
.c4-overlay-strip__hop--unmapped {
  border-left: 3px solid var(--sev-high);
  padding-left: var(--space-2);
}
.c4-overlay-strip__arrow { color: var(--ink-3); }
```

- [ ] **Step 4: Run test to verify it passes**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_attack_path_overlay -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```
git add report-template/screens/C4.jsx report-template/screens.css tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): C4 attack-path overlay with honest unmapped-hop asset strip

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Rebuild bundle + regenerate the tracked example report; confirm freshness green

**Files:**
- Modify: `tools/apd_gauntlet/data/report-template/app.js` + `screens.css` + `.source-hash` (regenerated)
- Modify: the tracked example report bundle (regenerated, if the repo tracks one — see Step 3 note)

- [ ] **Step 1: Write the failing test** — the freshness gate is RED after the M6 JSX/CSS edits

```
.venv/bin/python tools/check_report_template_freshness.py; echo "exit=$?"
```

Expected (RED): `exit=1` with the `expected=<M5-hash> actual=<M6-hash>` mismatch (the C4.jsx + screens.css overlay edits changed the source tree).

- [ ] **Step 2: Run test to verify it fails**

(Same command as Step 1.) Expected `exit=1`.

- [ ] **Step 3: Write minimal implementation** — rebuild + regenerate the example report

```
.venv/bin/python tools/build_report_template.py
```

Expected: `build-report-template: bundle written.`

Then regenerate the tracked example report so the committed example reflects the overlay. The repo ships an example report bundle alongside the template (`report-template/data.js` / `report-template/APD Gauntlet Report.html`); regenerate it from the Home Assistant run after assembling `c4-model.yaml` so the example carries the C4 tab:

```
.venv/bin/apd-gauntlet assemble-c4 tests/fixtures/runs/c4-home-assistant \
  && .venv/bin/apd-gauntlet build-report tests/fixtures/runs/c4-home-assistant \
       --out-dir report-template/.example-c4 --quiet \
  && cp "report-template/.example-c4/data.js" report-template/data.js
```

> Note: confirm the exact tracked-example path before committing — `git status` will show whether `report-template/data.js` (and/or `report-template/APD Gauntlet Report.html`) is the tracked example this repo regenerates. The freshness hash EXCLUDES dot-prefixed paths (`check_report_template_freshness.compute_source_hash` skips `rel.parts[0].startswith(".")`), so the scratch `.example-c4/` directory does not perturb the gate; only `report-template/data.js` (a non-dot file) feeds the hash, which is why the rebuild must follow the example regeneration.

- [ ] **Step 4: Run test to verify it passes** — freshness green after rebuild

Re-run the rebuild last so the `.source-hash` reflects the final `report-template/data.js`:

```
.venv/bin/python tools/build_report_template.py \
  && .venv/bin/python tools/check_report_template_freshness.py; echo "exit=$?"
```

Expected (GREEN):
```
build-report-template: bundle written.
check_report_template_freshness: OK (<hex>)
exit=0
```

- [ ] **Step 5: Commit**

```
git add tools/apd_gauntlet/data/report-template/app.js \
        tools/apd_gauntlet/data/report-template/screens.css \
        tools/apd_gauntlet/data/report-template/.source-hash \
        report-template/data.js
git commit -m "build(report): rebuild bundle + regenerate example report for C4 overlay

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**Milestone 6 exit check:**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "c4 or C4" -v \
  && .venv/bin/python tools/check_report_template_freshness.py \
  && git grep -L mermaid -- report-template/screens/C4.jsx >/dev/null \
  && .venv/bin/ruff check tools/apd_gauntlet
```

Expected: all C4-selected pytest cases pass, freshness `OK`, no Mermaid reference in `C4.jsx`, ruff clean. For the full front-end regression, also run the bundle/graph suite:

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "graph_view or attack_paths or threat_model or c4 or C4 or bundle or mermaid" -v
```

---

Notes for the implementer that are load-bearing across both milestones:

- `report-template/.build/entry.jsx` MUST gain the `import "../screens/C4.jsx";` line (Task 1) — esbuild bundles only what `entry.jsx` imports; a screen that only does `window.C4 = C4` is otherwise dropped from the bundle, and `test_bundle_contains_c4_scene` will stay red after a rebuild.
- The C4 scene reuses `GraphView`'s existing `paths`/`selectedPathId`/`onSelectPath` cross-link contract (components.jsx:289, tap handler at :346-360) for BOTH drill-down (M5, `onSelectPath={onNodeTap}`) and overlay highlight (M6, a single synthetic `__overlay__` path). No change to `GraphView` is required; `compound={true}` + `n.parent` (components.jsx:298) already render containment as nested boxes under `fcose` (layoutOpts at :311).
- `data.c4_model` is the contracted window key (loader field `c4_model`, transform `c4_model_view`) delivered by M1–M4; M5/M6 only read it. The render test in Task 5 exercises the committed fixture run `tests/fixtures/runs/c4-home-assistant` (built in Milestone 0 from the local Home Assistant run: 46 code-evidence entries across 9 code-bearing repos + 14 empty repos → ≥1 `not_analyzed` container, 27 finding-edges feeding badge counts) end-to-end, so it fails loudly if any M1–M4 piece regresses.
- `runs/*/report-html` is gitignored, so Task 5's render test copies the run into `tmp_path` and assembles/builds there — matching the established "build-report first" pattern from the report-completeness gate (#71).

---

## Milestone 7: Tiered C4 render redesign (from the design handoff)

> **Source of truth:** `docs/superpowers/design_handoff_c4_architecture_view/` (README + `prototype/`). Folds in the four gap-fixes surfaced by the handoff analysis. **Render-only** — NO change to `transform.py`, `assemble_c4.py`, or the schemas; the existing `window.APD_DATA.c4_model` is consumed verbatim using the **REAL** field names (`capability_badge`, `analysis_state`, `provenance.first_finding_id`, `machine_extracted`) — never the prototype fixture's abbreviated `cap`/`state`/`ff`/`me`.

**Why:** M5 shipped the C4 scene on Cytoscape `fcose`, but real runs are edge-sparse (Home Assistant: 82 nodes / 6 edges), so the force layout scatters the ~76 disconnected nodes into an unreadable grid. This milestone replaces it with a **tiered "system-map"** — L1 System context → L2 Container → L3 Component → L4 Code, left-gutter labels, orthogonal right-angle rounded SVG connectors (only on the grounded `edges[]`), finding (⚑) / capability (🛡) badges **inside** node boxes, and a data-driven L3 with honest empty states. `GraphView` (Cytoscape) stays untouched so AttackPaths/ThreatModel are unaffected.

**The four gap-fixes folded in** (the parts the handoff under-budgeted): **(1)** test-rewrite FIRST (Task 1) — the hard C4 tests currently assert the very Cytoscape strings being removed, so they are inverted before any impl; **(2)** data-fidelity fix (Task 2) — the prototype fixture used abbreviated/renamed keys + omitted `present`/`asset_to_c4`/`finding_to_c4`, so it is regenerated to the literal model shape + a README crosswalk; **(3)** the previously prose-only pieces made concrete — deterministic backbone layout (Task 3), deterministic short edge-label derivation (Task 4), and the SVG overlay-highlight rebuild (Task 8); **(4)** mandatory bundle rebuild + the triple-enforced freshness/audit gates + the full acceptance checklist (Task 9).

**New code** (plain React + SVG + DOM measurement — no Cytoscape, no new deps), all window-exported from `report-template/components.jsx`: pure helpers `c4BackboneLayout(nodes, edges)` + `c4ShortEdgeLabel(rawLabel)`, the router `c4Anchors`/`c4RouteWaypoints`/`c4RoundedPath`, the `C4EdgeLayer` SVG overlay, and the `C4TierGraph` component. `report-template/screens/C4.jsx` **keeps** its drill-state machine, honest banner, attack-path overlay *resolution* (`asset_to_c4`/`finding_to_c4` + unmapped-hops), `NodeRow`/badges + `onOpenFinding` deep-link, breadcrumb, and `c4-kind-chip`; it **swaps** the render from `<GraphView layout="fcose" compound>` to `<C4TierGraph/>` (removing the GraphView subgraph memo + the `overlayHighlight` synthetic-path).

**Files touched:** `report-template/screens/C4.jsx`, `report-template/components.jsx`, `report-template/screens.css`, `tests/test_workflow_apd_gauntlet.py`, the regenerated bundle (`report-template/app.js` + `tools/apd_gauntlet/data/report-template/` + `.source-hash`), and `docs/superpowers/design_handoff_c4_architecture_view/prototype/archx-data.js` (+ a README crosswalk note). The `assemble_c4.py` `level: component` (L3) modeling and the schemas are **already** in place from M1–M2 — the new L3 tier just renders them when present.

**9 tasks** — TDD, executed in order. Task 1 (the inverted tests) is the RED bar for the whole milestone; Tasks 3/4/5 are pure deterministic helpers; Tasks 6–8 are the renderer + integration + overlay; Task 9 rebuilds the bundle and closes the acceptance checklist.

---

### Task 1: Test-rewrite FIRST (TDD) — redefine the 4 hard C4 string-assertion tests for the TIERED scene

This task runs **FIRST** and stays **RED** until the Milestone-7 impl tasks (the `C4TierGraph` component + helpers in `components.jsx`, the C4.jsx render rewrite, and the bundle rebuild in Task 9) land. That is intentional and is the TDD red bar for the whole milestone. The 5 still-valid C4 tests and all shared-GraphView tests must stay GREEN throughout, because `GraphView` is untouched and the C4 data contract / banner / kind-chip / overlay-join / tab-routing are unchanged.

**Files:**

- Modify: `tests/test_workflow_apd_gauntlet.py` (rewrite 4 tests; the module globals `REPO` at line 18 and `_text()` at line 60 are reused as-is — no new imports)

**Pre-flight: pin the baseline so the red→green transition is auditable.**

- [ ] **Step 0: Record the current (Cytoscape) state of the 4 targets + the keepers — they are GREEN against the shipped PR #108 C4.jsx.**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "test_c4_screen_exists_and_renders_blocks or test_bundle_contains_c4_scene \
or test_c4_attack_path_overlay or test_c4_graph_node_tap_drives_drill" -v; echo "exit=$?"
```

Expected (baseline GREEN, `exit=0`): all 4 pass against the current Cytoscape C4.jsx. This is the "before" the rewrite inverts.

---

**The 4 rewrites.** Each block below is the exact old→new replacement for one test. Apply them verbatim. After all four, run RED (Step 5).

- [ ] **Step 1: `test_c4_screen_exists_and_renders_blocks` (line ~727).** Drop the GraphView/`compound`/`fcose` assertions; require the tiered scene + the `C4TierGraph` component + the SVG edge layer + in-node badges + the deterministic backbone helper. KEEP the unchanged contract assertions (export, `data.c4_model`, drill state, honest banner, `not_analyzed` hook, `onOpenFinding`, design-language classes).

OLD:

```python
def test_c4_screen_exists_and_renders_blocks() -> None:
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # component declared + exported on window (bundle registration contract)
    assert "function C4(" in src and "window.C4 = C4" in src
    # consumes the contracted window key shape
    assert "data.c4_model" in src
    # reuses the shared compound-capable Cytoscape renderer with fcose layout
    assert "GraphView" in src and "MermaidGraph" not in src
    assert "compound={true}" in src or "compound" in src
    assert 'layout="fcose"' in src
    # drill-down level state: default L1+L2, click container -> components/code
    assert "selectedContainer" in src and "selectedComponent" in src
    # honest banner: unlocalized findings + not-analyzed containers
    assert "unlocalized_findings" in src and "not_analyzed_count" in src
    # not_analyzed styling hook on nodes
    assert "analysis_state" in src and "not_analyzed" in src
    # finding-badge deep-link into the Findings tab
    assert "onOpenFinding" in src
    # reuses the report design language, not bespoke styling
    assert "section-eyebrow" in src and "section-title" in src
```

NEW:

```python
def test_c4_screen_exists_and_renders_blocks() -> None:
    """M7 tiered redesign: the C4 scene renders a stacked TIERED 'system-map'
    (L1 System context -> L2 Container -> L3 Component -> L4 Code) via the new
    plain-React+SVG `C4TierGraph` renderer, NOT the Cytoscape `GraphView`
    force-graph. GraphView stays in components.jsx for AttackPaths/ThreatModel
    but C4 no longer consumes it. The data contract (data.c4_model), drill-state
    machine, honest banner, not_analyzed hook, and onOpenFinding deep-link are
    UNCHANGED (render-only redesign)."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # component declared + exported on window (bundle registration contract)
    assert "function C4(" in src and "window.C4 = C4" in src
    # consumes the contracted window key shape (UNCHANGED data model)
    assert "data.c4_model" in src
    # renders the NEW tiered renderer; the Cytoscape force-graph is GONE from C4.
    assert "C4TierGraph" in src
    assert "GraphView" not in src, "C4 must no longer consume the Cytoscape GraphView"
    assert 'layout="fcose"' not in src, "the fcose force-graph is removed from C4"
    assert "compound={true}" not in src, "the compound force-layout prop is removed from C4"
    assert "MermaidGraph" not in src
    # drill-down level state: default L1+L2, click container -> components/code
    assert "selectedContainer" in src and "selectedComponent" in src
    # honest banner: unlocalized findings + not-analyzed containers (UNCHANGED)
    assert "unlocalized_findings" in src and "not_analyzed_count" in src
    # not_analyzed styling hook on nodes (UNCHANGED)
    assert "analysis_state" in src and "not_analyzed" in src
    # finding-badge deep-link into the Findings tab (UNCHANGED)
    assert "onOpenFinding" in src
    # reuses the report design language, not bespoke styling (UNCHANGED)
    assert "section-eyebrow" in src and "section-title" in src
```

- [ ] **Step 2: `test_bundle_contains_c4_scene` (line ~958).** The packaged `app.js` must carry the tiered renderer, not `GraphView`/`fcose`. KEEP `window.C4`, `c4_model`, and the `Architecture` tab label (the tab + data contract are unchanged).

OLD:

```python
def test_bundle_contains_c4_scene() -> None:
    # The precompiled bundle must carry the C4 component + its compound graph use.
    app_js = (
        REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "app.js"
    ).read_text(encoding="utf-8")
    assert "window.C4" in app_js            # screen exported into the bundle
    assert "c4_model" in app_js             # consumes the contracted window key
    assert "GraphView" in app_js            # reuses the shared Cytoscape renderer
    assert "fcose" in app_js                # compound layout requested
    assert "Architecture" in app_js         # the tab label is bundled
```

NEW:

```python
def test_bundle_contains_c4_scene() -> None:
    """M7: the precompiled bundle must carry the NEW tiered `C4TierGraph`
    renderer + the deterministic backbone-layout helper, not the Cytoscape
    force-graph wiring for C4. (GraphView/fcose still appear ELSEWHERE in app.js
    because AttackPaths/ThreatModel keep using them — so we assert C4-specific
    symbols, not the global absence of GraphView/fcose.)"""
    app_js = (
        REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "app.js"
    ).read_text(encoding="utf-8")
    assert "window.C4" in app_js            # screen exported into the bundle
    assert "c4_model" in app_js             # consumes the contracted window key
    assert "C4TierGraph" in app_js          # the new tiered renderer is bundled
    assert "c4BackboneLayout" in app_js     # the deterministic layout helper is bundled
    assert "Architecture" in app_js         # the tab label is bundled
```

> NOTE — DO NOT assert `"GraphView" not in app_js` or `"fcose" not in app_js` here: those symbols are still bundled for the AttackPaths/ThreatModel scenes, which keep the Cytoscape `GraphView`. The C4-removal of GraphView is asserted at the **source** level in `test_c4_screen_exists_and_renders_blocks` / `test_c4_graph_node_tap_drives_drill`, which read `C4.jsx` (not the shared bundle). esbuild may also minify `window.C4 = C4` to a rename; if a rebuilt bundle ever fails the literal `"window.C4"` check, relax that single assertion to `'C4=' in app_js or "window.C4" in app_js` — but the shipped esbuild config preserves the `window.C4 = C4` assignment (verified against the current bundle), so keep the literal unless the rebuild proves otherwise.

- [ ] **Step 3: `test_c4_attack_path_overlay` (line ~1047).** The overlay is REBUILT for the SVG scene: the `asset_to_c4`/`finding_to_c4` deterministic join, the `selectedOverlayPath` state, the `unmappedHops` parallel strip, and the CSS classes all stay (they are renderer-agnostic). Only the "reuses GraphView cross-highlight" clause is replaced with the new SVG overlay contract: a resolved set of C4 node ids (`overlayC4NodeIds`) handed to `C4TierGraph`, which redraws the induced edges as "live".

OLD:

```python
def test_c4_attack_path_overlay() -> None:
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # consumes the existing enumerated paths (no new data source)
    assert "data.attack_paths" in src
    # a selectable overlay control + its selection state
    assert "selectedOverlayPath" in src and "setSelectedOverlayPath" in src
    # consumes the DETERMINISTIC join, never computes a mapping client-side
    assert "asset_to_c4" in src and "finding_to_c4" in src
    # reuses GraphView's cross-highlight contract (overlay path -> highlighted c4 nodes)
    assert "overlayHighlight" in src or "overlayPaths" in src
    # honest partial overlay: hops with no C4 mapping go on a PARALLEL asset strip
    assert "c4-overlay-strip" in src and "no C4 mapping" in src
    # never invent: an unmapped hop is labelled, not rendered as a C4 hop
    assert "unmappedHops" in src

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    assert ".c4-overlay-strip" in css and ".c4-overlay-strip__hop--unmapped" in css
```

NEW:

```python
def test_c4_attack_path_overlay() -> None:
    """M7: the attack-path overlay survives the redesign but is REBUILT for the
    SVG scene. The deterministic asset_to_c4 / finding_to_c4 join, the
    selectedOverlayPath state, and the honest unmapped-hops PARALLEL strip are
    unchanged (renderer-agnostic). The only swap: instead of synthesizing a
    GraphView cross-highlight 'path', the scene resolves a SET of grounded C4
    node ids (overlayC4NodeIds) and hands it to C4TierGraph, which dims
    non-members and redraws the induced edges as 'live'."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # consumes the existing enumerated paths (no new data source) — UNCHANGED
    assert "data.attack_paths" in src
    # a selectable overlay control + its selection state — UNCHANGED
    assert "selectedOverlayPath" in src and "setSelectedOverlayPath" in src
    # consumes the DETERMINISTIC join, never computes a mapping client-side — UNCHANGED
    assert "asset_to_c4" in src and "finding_to_c4" in src
    # the resolved C4-node-id SET is passed to the tiered renderer for highlight.
    assert "overlayC4NodeIds" in src
    # the old GraphView synthetic-path cross-highlight wiring is GONE.
    assert "overlayHighlight" not in src, "the GraphView synthetic-path highlight is removed"
    assert "__overlay__" not in src, "the synthetic GraphView overlay path id is removed"
    # honest partial overlay: hops with no C4 mapping go on a PARALLEL asset strip — UNCHANGED
    assert "c4-overlay-strip" in src and "no C4 mapping" in src
    # never invent: an unmapped hop is labelled, not rendered as a C4 hop — UNCHANGED
    assert "unmappedHops" in src

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    assert ".c4-overlay-strip" in css and ".c4-overlay-strip__hop--unmapped" in css
```

- [ ] **Step 4: `test_c4_graph_node_tap_drives_drill` (line ~1066).** Drill is now driven by a DOM `onClick` on the SVG-scene node boxes calling the same `onNodeTap` reducer, passed to `C4TierGraph` as `onDrill`. The Cytoscape tap-target contract is fully removed from C4; the broken empty-`edgeIds` `tapTargets` misuse must stay gone. Also assert the badge `stopPropagation` rule (clicking a ⚑ deep-links without drilling), per the SHARED CONTRACT. The `GraphView` tap handler in `components.jsx` stays asserted (it is untouched and still used by the other scenes), so its check is KEPT but reframed: it must exist for AttackPaths/ThreatModel even though C4 no longer wires it.

OLD:

```python
def test_c4_graph_node_tap_drives_drill() -> None:
    """A graph node click must drive C4 drill-down (container -> components/code,

    component -> code), mirroring the NodeRow button. The OLD wiring abused
    GraphView's path-resolution contract with synthetic tapTargets carrying
    empty edgeIds — which ALWAYS resolved to null and confusingly reset the
    view. That misuse must be gone; the scene must pass a dedicated onNodeTap
    callback to GraphView instead.
    """
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # The C4 scene wires GraphView with a dedicated node-tap callback.
    assert "onNodeTap={onNodeTap}" in src
    # The broken empty-edgeIds tapTargets-for-drill pattern is gone.
    assert "edgeIds: []" not in src
    assert "tapTargets" not in src
    # onNodeTap is no longer (mis)used to drive onSelectPath for drilling.
    assert "onSelectPath={onNodeTap}" not in src
    assert "onSelectPath={overlayHighlight ? () => {} : onNodeTap}" not in src
    # GraphView itself accepts and honors the onNodeTap prop.
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "onNodeTap" in comps
    # The cytoscape node-tap handler reports the tapped node id when wired.
    assert "onNodeTap(ev.target.id())" in comps or "onNodeTap(node.id())" in comps
```

NEW:

```python
def test_c4_graph_node_tap_drives_drill() -> None:
    """M7: a node click in the tiered SVG scene must drive C4 drill-down
    (container -> components/code, component -> code), mirroring the NodeRow
    button. The Cytoscape path-resolution / tapTargets contract is fully removed
    from C4: drill is now a plain DOM onClick on the node box that calls the
    onNodeTap reducer, handed to C4TierGraph as `onDrill`. Clicking a ⚑ badge
    must stopPropagation so it deep-links into Findings WITHOUT drilling. The
    onNodeTap reducer state machine is unchanged (it still keys off node.type)."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # The drill reducer is handed to the tiered renderer as onDrill (DOM-click driven).
    assert "onDrill={onNodeTap}" in src
    # The reducer itself survives the redesign (state machine unchanged).
    assert "onNodeTap" in src
    # The Cytoscape tap-resolution misuse is GONE from C4.
    assert "onNodeTap={onNodeTap}" not in src, "C4 no longer wires GraphView's onNodeTap"
    assert "edgeIds: []" not in src
    assert "tapTargets" not in src
    assert "onSelectPath={onNodeTap}" not in src
    assert "onSelectPath={overlayHighlight ? () => {} : onNodeTap}" not in src
    # Clicking a ⚑ badge stops propagation so it deep-links without drilling.
    assert "stopPropagation" in src
    # GraphView's tap contract STAYS in components.jsx for the OTHER scenes
    # (AttackPaths/ThreatModel) — it is untouched, just unused by C4.
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "onNodeTap" in comps
    assert "onNodeTap(ev.target.id())" in comps or "onNodeTap(node.id())" in comps
    # The NEW tiered renderer + the deterministic backbone-layout helper exist
    # and are window-exported alongside GraphView.
    assert "function C4TierGraph(" in comps
    assert "function c4BackboneLayout(" in comps
    assert "C4TierGraph" in comps.split("Object.assign(window")[1]
    assert "c4BackboneLayout" in comps.split("Object.assign(window")[1]
```

---

- [ ] **Step 5: Run the rewritten tests — expect RED (the impl has not landed).** This is the documented TDD red bar for Milestone 7.

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "test_c4_screen_exists_and_renders_blocks or test_bundle_contains_c4_scene \
or test_c4_attack_path_overlay or test_c4_graph_node_tap_drives_drill" -v; echo "exit=$?"
```

Expected (RED, `exit=1`): all 4 FAIL — `C4TierGraph` / `c4BackboneLayout` / `onDrill` / `overlayC4NodeIds` are not yet in `C4.jsx`/`components.jsx`/`app.js`, and the removed-Cytoscape assertions trip on the still-present `layout="fcose"`/`GraphView`/`overlayHighlight` in the shipped PR #108 source. RECORD this red output in the task notes — it is the failing test that the impl tasks (C4TierGraph + helpers, C4.jsx rewrite, Task 9 rebuild) turn green.

- [ ] **Step 6: Confirm the 5 still-valid C4 tests + the shared-GraphView suite are STILL GREEN** (the rewrite must not collaterally break them — they assert the unchanged contract: kind-chip, the from_id/to_id overlay join, tab routing, bundle-entry import, CSS, and the untouched GraphView).

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "test_c4_screen_surfaces_node_kind_chip or test_c4_overlay_join_uses_from_id_to_id \
or test_c4_tab_is_conditional_and_routed or test_c4_screen_registered_in_bundle_entry \
or test_c4_scene_styles_present or graph_view or attack_paths_uses_graphview \
or threat_model_uses_graphview or kind_passthrough" -v; echo "exit=$?"
```

Expected (GREEN, `exit=0`): all pass. NONE of these reference `C4TierGraph`/`fcose`-removal, so they are insensitive to the redesign. If `test_c4_scene_styles_present` or `test_c4_overlay_join_uses_from_id_to_id` go red here, the rewrite leaked a change into the wrong test — revert and re-apply only the 4 blocks above.

> WHY this still passes while Step 5 is red: the keepers read DIFFERENT substrings (`c4-kind-chip`, `[h.from_id, h.to_id]`, `id: "c4"`, `import "../screens/C4.jsx";`, `.c4-banner`) that the redesign preserves verbatim per the SHARED CONTRACT's keep-list. The redesign removes `GraphView`/`fcose` from C4 but the shared-GraphView tests read `components.jsx` (untouched) + `AttackPaths.jsx`/`ThreatModel.jsx` (untouched), so they are green by construction.

- [ ] **Step 7: Commit the failing tests (TDD-first; impl follows).**

```
git add tests/test_workflow_apd_gauntlet.py
git commit -m "test(report): redefine C4 string-assertions for the tiered M7 scene (RED)

Rewrite the 4 hard C4 tests to assert the new plain-React+SVG C4TierGraph
tiered scene (+ deterministic c4BackboneLayout helper, SVG edge-layer,
in-node badges, onDrill DOM-click drill, overlayC4NodeIds highlight, badge
stopPropagation) and the ABSENCE of GraphView/fcose/overlayHighlight from
C4.jsx. The 5 still-valid C4 tests + the shared-GraphView suite stay green
(GraphView untouched for AttackPaths/ThreatModel). RED until the M7 impl
tasks land; this is the milestone's TDD red bar.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**Task 1 exit:** the 4 rewritten tests are RED, the 5 keepers + shared-GraphView suite are GREEN, and the failing output is recorded. The impl tasks (C4TierGraph + helpers, C4.jsx render rewrite, CSS, then Task 9 rebuild) are what flip the 4 to green; no impl is done in this task.

---

### Task 2: Data-fidelity fix — regenerate `archx-data.js` to the LITERAL `c4_model_view` field names + handoff crosswalk note

The prototype fixture `archx-data.js` was written with ABBREVIATED, fabricated
keys (`cap`/`state`/`ff`/`me`, plus an invented `overlay_paths` array) and it
DROPS the production rollups (`present`, `not_analyzed_count`, `unlocalized_findings`,
`levels_present`, `asset_to_c4`, `finding_to_c4`) and the per-node `provenance`,
`capability_badge`, `analysis_state` fields. Any React scene built against that
fixture would be coded against keys that do not exist on the real window object.

This task makes `window.C4_DATA` byte-for-byte the same SHAPE as the real
`window.APD_DATA.c4_model` slice — i.e. exactly what `c4_model_view` emits for
the home-assistant run — so the prototype and the React `C4TierGraph` consume the
SAME contract. The values are derived deterministically from the real
`runs/apd-20260612-home-assistant/40-synthesis/c4-model.yaml` (already read in this
session) passed through the documented `c4_model_view` rules: `badge = finding_count
if >0 else null`, `capability_badge = capability_count`, `type = level`,
`provenance = {source, locator, repo, first_finding_id}` (only the present keys),
edges `{id, source, target, label, machine_extracted}`. The prototype's own
backbone/short-label maps (the hard-coded `BACKBONE`/`EDGE_SHORT`/`ANALYZED_SHELF`
constants in the `.html`) are NOT in the fixture — they are renderer concerns and
Tasks 3/4 replace them with data-driven helpers.

**Files:**
- Create: `docs/superpowers/design_handoff_c4_architecture_view/prototype/check-fixture-keys.js` (node assertion harness — the fixture's "test")
- Modify: `docs/superpowers/design_handoff_c4_architecture_view/prototype/archx-data.js` (rewrite to real keys)
- Modify: `docs/superpowers/design_handoff_c4_architecture_view/README.md` (add the "Field-name crosswalk (fixture vs production)" note)

**Steps:**

- [ ] **Write the failing key-assertion harness FIRST.** Create
  `prototype/check-fixture-keys.js`. It loads the fixture, asserts the REAL keys
  are present and the abbreviation keys are ABSENT, and exits non-zero on any
  violation. Run it against the *current* (abbreviated) fixture and watch it FAIL.

  ```js
  // check-fixture-keys.js — node, no deps. Asserts archx-data.js exposes the
  // REAL window.APD_DATA.c4_model field names (from transform.py::c4_model_view)
  // and NONE of the prototype-era abbreviations (cap/state/ff/me/overlay_paths).
  // Usage: node check-fixture-keys.js  → exit 0 = pass, 1 = fail (prints diffs).
  'use strict';
  const fs = require('fs');
  const path = require('path');

  // Evaluate the fixture in a minimal window sandbox.
  const src = fs.readFileSync(path.join(__dirname, 'archx-data.js'), 'utf8');
  const window = {};
  // eslint-disable-next-line no-new-func
  new Function('window', src)(window);
  const C4 = window.C4_DATA;

  const fails = [];
  const ok = (cond, msg) => { if (!cond) fails.push(msg); };

  // ── top-level shape (the full c4_model_view return) ──────────────────────
  const TOP_REQUIRED = [
    'present', 'nodes', 'edges', 'unlocalized_findings', 'not_analyzed_count',
    'levels_present', 'asset_to_c4', 'finding_to_c4',
  ];
  TOP_REQUIRED.forEach(k => ok(k in C4, `MISSING top-level key: ${k}`));
  ok(C4.present === true, 'present must be true (this is a present run slice)');
  ok(!('overlay_paths' in C4), 'FORBIDDEN fabricated top-level key: overlay_paths');
  ok(Array.isArray(C4.nodes) && C4.nodes.length > 0, 'nodes must be a non-empty array');
  ok(Array.isArray(C4.edges) && C4.edges.length > 0, 'edges must be a non-empty array');
  ok(C4.asset_to_c4 && typeof C4.asset_to_c4 === 'object', 'asset_to_c4 must be an object');
  ok(C4.finding_to_c4 && typeof C4.finding_to_c4 === 'object', 'finding_to_c4 must be an object');

  // ── node shape ───────────────────────────────────────────────────────────
  const NODE_REQUIRED = [
    'id', 'label', 'type', 'kind', 'parent', 'badge', 'capability_badge',
    'analysis_state', 'provenance',
  ];
  const NODE_FORBIDDEN = ['cap', 'state', 'ff', 'me'];
  C4.nodes.forEach((n, i) => {
    NODE_REQUIRED.forEach(k => ok(k in n, `node[${i}] (${n.id}) MISSING key: ${k}`));
    NODE_FORBIDDEN.forEach(k => ok(!(k in n), `node[${i}] (${n.id}) FORBIDDEN abbrev key: ${k}`));
    // badge is finding_count|null (never the literal 0 'clean' lie)
    ok(n.badge === null || (typeof n.badge === 'number' && n.badge > 0),
       `node[${i}] (${n.id}) badge must be null or a positive int, got ${JSON.stringify(n.badge)}`);
    ok(typeof n.capability_badge === 'number',
       `node[${i}] (${n.id}) capability_badge must be a number`);
    ok(n.analysis_state === 'analyzed' || n.analysis_state === 'not_analyzed',
       `node[${i}] (${n.id}) analysis_state must be analyzed|not_analyzed`);
    ok(n.provenance && typeof n.provenance === 'object',
       `node[${i}] (${n.id}) provenance must be an object`);
  });

  // ── edge shape ─────────────────────────────────────────────────────────────
  const EDGE_REQUIRED = ['id', 'source', 'target', 'label', 'machine_extracted'];
  C4.edges.forEach((e, i) => {
    EDGE_REQUIRED.forEach(k => ok(k in e, `edge[${i}] (${e.id}) MISSING key: ${k}`));
    ok(!('me' in e), `edge[${i}] (${e.id}) FORBIDDEN abbrev key: me`);
    ok(typeof e.machine_extracted === 'boolean',
       `edge[${i}] (${e.id}) machine_extracted must be boolean`);
    ok(typeof e.label === 'string' && e.label.startsWith('CROSS_'),
       `edge[${i}] (${e.id}) label must be the full machine string (CROSS_*)`);
  });

  // ── spot-check the real HA values survived the regeneration ────────────────
  const core = C4.nodes.find(n => n.id === 'c4-2b33e14f');
  ok(core && core.badge === 22 && core.capability_badge === 15,
     'Core (c4-2b33e14f) must keep badge=22, capability_badge=15');
  const docker = C4.nodes.find(n => n.id === 'c4-bc1e61b2');
  ok(docker && docker.analysis_state === 'not_analyzed' && docker.badge === null,
     'docker (c4-bc1e61b2) must be not_analyzed with badge=null');

  if (fails.length) {
    console.error(`FIXTURE KEY CHECK FAILED (${fails.length}):`);
    fails.forEach(f => console.error('  - ' + f));
    process.exit(1);
  }
  console.log(`fixture key check OK: ${C4.nodes.length} nodes, ${C4.edges.length} edges, real keys present, abbreviations absent.`);
  ```

  Run it red:
  ```bash
  node "docs/superpowers/design_handoff_c4_architecture_view/prototype/check-fixture-keys.js"
  # EXPECT: FIXTURE KEY CHECK FAILED — MISSING top-level key: present / node MISSING key: kind / node FORBIDDEN abbrev key: cap … exit 1
  ```

- [ ] **Regenerate `archx-data.js` honestly.** Overwrite the file with the real
  `c4_model_view` shape for the home-assistant run. Values are the documented
  transform of `c4-model.yaml`: `type = level`, `badge = finding_count if >0 else null`,
  `capability_badge = capability_count`, `provenance` keeps only the present subset
  of `{source, locator, repo, first_finding_id}`, edges carry `{id, source, target,
  label(full string), machine_extracted}`. Top-level rollups come from
  `build_summary` (`not_analyzed_count = 15`, `unlocalized_findings = 10`,
  `levels_present` in canonical L1→L4 order = `["system","person","external_system","container","code"]`).
  `asset_to_c4`/`finding_to_c4` are the GROUNDED crosswalks — for this fixture they
  are honestly `{}` (the HA run's asset nodes carry doc-anchored provenance and
  this prototype slice does not ship the deduped-findings join), which is itself a
  faithful representation of the disjoint-id-space limitation documented in
  `c4_model_view`. (NOTE: labels are already `_safe_label`-truncated to 60 chars in
  the source values — e.g. `hash_passwor`, `ServerManagerKey` — because the fixture
  represents the POST-transform window slice; keep those truncations.)

  The full regenerated file (every node + edge from `c4-model.yaml`, real keys):

  ```js
  // archx-data.js — REGENERATED fixture (Task 2, Milestone 7).
  // window.C4_DATA is byte-identical in SHAPE to window.APD_DATA.c4_model as
  // produced by tools/apd_gauntlet/report/transform.py::c4_model_view for the
  // apd-20260612-home-assistant run (runs/.../40-synthesis/c4-model.yaml).
  // Real field names ONLY: type/kind/parent/badge/capability_badge/
  // analysis_state/provenance + machine_extracted on edges. NO cap/state/ff/me,
  // NO fabricated overlay_paths. Labels are _safe_label-truncated (60 chars),
  // matching the production transform. See README "Field-name crosswalk".
  window.C4_DATA = {
    "present": true,
    "levels_present": ["system", "person", "external_system", "container", "code"],
    "unlocalized_findings": 10,
    "not_analyzed_count": 15,
    "asset_to_c4": {},
    "finding_to_c4": {},
    "nodes": [
      {"id":"c4-00ca2e01","label":"docker-base","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:docker-base"}},
      {"id":"c4-07f5a3e6","label":"plugin-dns","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:plugin-dns"}},
      {"id":"c4-0ebbc6cf","label":"homeassistant.auth.providers.homeassistant.Data.hash_passwor","type":"code","kind":"function","parent":"c4-2b33e14f","badge":null,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.providers.homeassistant.Data.hash_password","repo":"core"}},
      {"id":"c4-10ca49c1","label":"Sources.Shared.API.ServerManagerPersistence.ServerManagerKey","type":"code","kind":"class","parent":"c4-9e5151b7","badge":2,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"Sources.Shared.API.ServerManagerPersistence.ServerManagerKeychain","repo":"iOS","first_finding_id":"conf-a30cca33"}},
      {"id":"c4-11fbf1b9","label":"system.system.AddSSHAuthKey","type":"code","kind":"function","parent":"c4-d304503a","badge":3,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"system.system.AddSSHAuthKey","repo":"os-agent","first_finding_id":"auth-6924f467"}},
      {"id":"c4-123809c8","label":"homeassistant.helpers.storage.Store._write_prepared_data","type":"code","kind":"function","parent":"c4-2b33e14f","badge":3,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.helpers.storage.Store._write_prepared_data","repo":"core","first_finding_id":"dist-69bbaf5c"}},
      {"id":"c4-13cad86b","label":"Recorder history DB","type":"container","kind":"data_store","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-a1000018 (recorder.session_scope — presence/geolocation/lock/alarm state history; brief §2)"}},
      {"id":"c4-1f375927","label":"src.external_app.external_messaging.ExternalMessaging.fireMe","type":"code","kind":"function","parent":"c4-a811b55d","badge":2,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"src.external_app.external_messaging.ExternalMessaging.fireMessage","repo":"frontend","first_finding_id":"auth-ea69d3a2"}},
      {"id":"c4-2085cc3a","label":"Long-Lived Access Token holder","type":"person","kind":"human_role","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#rest-api, line 15 (Long-Lived Access Token from /profile)"}},
      {"id":"c4-21faac85","label":"__route__POST__/api/sendPushNotification","type":"code","kind":"route","parent":"c4-fcee7bf9","badge":2,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"__route__POST__/api/sendPushNotification","repo":"mobile-apps-fcm-push","first_finding_id":"avail-a2cfd41c"}},
      {"id":"c4-22aa1f41","label":"companion.home-assistant","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:companion.home-assistant"}},
      {"id":"c4-269b85a2","label":"homeassistant.components.mobile_app.webhook.webhook_call_ser","type":"code","kind":"function","parent":"c4-2b33e14f","badge":6,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.mobile_app.webhook.webhook_call_service","repo":"core","first_finding_id":"avail-754cfc01"}},
      {"id":"c4-274b56cd","label":"Supervisor backup archive store","type":"container","kind":"data_store","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-b2000006 (Backup.set_password — full snapshots default to UNENCRYPTED; brief §2)"}},
      {"id":"c4-2b33e14f","label":"Home Assistant Core","type":"container","kind":"service","parent":null,"badge":22,"capability_badge":15,"analysis_state":"analyzed","provenance":{"source":"artifact","locator":"code-architecture-brief.md §1 Surface inventory (REST /api port 8123, WS /api/websocket handshake, bearer-less mobile_app webhook)","first_finding_id":"auth-3f2314a4"}},
      {"id":"c4-2d5eaa33","label":"homeassistant.helpers.recorder.session_scope","type":"code","kind":"function","parent":"c4-2b33e14f","badge":6,"capability_badge":1,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.helpers.recorder.session_scope","repo":"core","first_finding_id":"avail-235dacf0"}},
      {"id":"c4-3038589a","label":"functions.handlers.handleRequest","type":"code","kind":"function","parent":"c4-fcee7bf9","badge":2,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"functions.handlers.handleRequest","repo":"mobile-apps-fcm-push","first_finding_id":"auth-23048c0c"}},
      {"id":"c4-30b671c0","label":"plugin-audio","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:plugin-audio"}},
      {"id":"c4-32b40633","label":"homeassistant.auth.permissions.util.compile_policy","type":"code","kind":"function","parent":"c4-2b33e14f","badge":2,"capability_badge":3,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.permissions.util.compile_policy","repo":"core","first_finding_id":"merged-1119b0be"}},
      {"id":"c4-37c54a76","label":"IndieAuth OAuth2 client (client_id IS the redirect URL no se","type":"person","kind":"external_party","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#authenticating-the-user, lines 8-11 (IndieAuth OAuth2)"}},
      {"id":"c4-3bfb10f9","label":"Trusted-networks / command-line / legacy auth provider princ","type":"person","kind":"human_role","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#authentication-authorization-model, lines 67-69"}},
      {"id":"c4-3d5dca87","label":"Home Assistant","type":"system","kind":"software_system","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"run_config","locator":"subject"}},
      {"id":"c4-43797bde","label":"plugin-observer","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:plugin-observer"}},
      {"id":"c4-4659f23a","label":"client.helper.URLHelper","type":"code","kind":"function","parent":"c4-aa5a3a58","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"client.helper.URLHelper","repo":"cli","first_finding_id":"auth-23048c0c"}},
      {"id":"c4-4fe61adf","label":"homeassistant.auth.AuthManager.async_validate_access_token","type":"code","kind":"function","parent":"c4-2b33e14f","badge":1,"capability_badge":3,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.AuthManager.async_validate_access_token","repo":"core","first_finding_id":"ephem-f19f24f9"}},
      {"id":"c4-530843d4","label":"homeassistant.components.mobile_app.http_api.RegistrationsVi","type":"code","kind":"route","parent":"c4-2b33e14f","badge":2,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.mobile_app.http_api.RegistrationsView.post","repo":"core","first_finding_id":"auth-3f2314a4"}},
      {"id":"c4-551aad6d","label":"homeassistant.auth.models.RefreshToken","type":"code","kind":"class","parent":"c4-2b33e14f","badge":4,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.models.RefreshToken","repo":"core","first_finding_id":"ephem-9915ab91"}},
      {"id":"c4-57d74e41","label":"supervisor.docker.manager.DockerAPI.container_run_inside","type":"code","kind":"function","parent":"c4-78444877","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"supervisor.docker.manager.DockerAPI.container_run_inside","repo":"supervisor","first_finding_id":"merged-66801b1b"}},
      {"id":"c4-58b318f7","label":"homeassistant.components.api.APITemplateView.post","type":"code","kind":"route","parent":"c4-2b33e14f","badge":4,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.api.APITemplateView.post","repo":"core","first_finding_id":"avail-4be2dd70"}},
      {"id":"c4-5cb67c4d","label":"plugin-multicast","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:plugin-multicast"}},
      {"id":"c4-6068d33e","label":"homeassistant.auth.AuthManager.async_create_access_token","type":"code","kind":"function","parent":"c4-2b33e14f","badge":3,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.AuthManager.async_create_access_token","repo":"core","first_finding_id":"avail-235dacf0"}},
      {"id":"c4-640e24aa","label":"common...data.keychain.KeyStoreRepositoryImpl","type":"code","kind":"class","parent":"c4-f7d01fcf","badge":1,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"common...data.keychain.KeyStoreRepositoryImpl","repo":"android","first_finding_id":"auth-3794d338"}},
      {"id":"c4-66dae27f","label":"host-dockerd","type":"container","kind":"external_system","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-0a000003 (Supervisor <-> host Docker daemon over shared /run/docker.sock; brief §5 — host infra, outside repos[])"}},
      {"id":"c4-6877897a","label":"operating-system","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:operating-system"}},
      {"id":"c4-693638dc","label":"app...launch.LaunchActivity.LaunchActivity","type":"code","kind":"class","parent":"c4-f7d01fcf","badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"app...launch.LaunchActivity.LaunchActivity","repo":"android"}},
      {"id":"c4-69d1a517","label":"homeassistant.auth.permissions._OwnerPermissions","type":"code","kind":"class","parent":"c4-2b33e14f","badge":3,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.permissions._OwnerPermissions","repo":"core","first_finding_id":"auth-7162fd48"}},
      {"id":"c4-69f67c4e","label":"Registered mobile device (webhook_id / cloudhook holder)","type":"person","kind":"external_party","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"registration response, lines 74-79 (webhook_id, secret)"}},
      {"id":"c4-6b059adc","label":"External devices / cloud services reached by integrations (o","type":"external_system","kind":"external_dependency","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#trust-boundaries item 6 (Core integration -> external device/cloud; SSRF)"}},
      {"id":"c4-714c61de","label":"APNS / FCM push providers","type":"external_system","kind":"external_dependency","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#trust-boundaries item 7 (HA instance <-> push relay <-> APNS/FCM)"}},
      {"id":"c4-72dbaac4","label":"common...database.server.ServerSessionInfo.ServerSessionInfo","type":"code","kind":"class","parent":"c4-f7d01fcf","badge":3,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"common...database.server.ServerSessionInfo.ServerSessionInfo","repo":"android","first_finding_id":"conf-205c53a5"}},
      {"id":"c4-7637d4e7","label":"Sources.App.AppDelegate.AppDelegate.setupFirebase","type":"code","kind":"function","parent":"c4-9e5151b7","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"Sources.App.AppDelegate.AppDelegate.setupFirebase","repo":"iOS","first_finding_id":"conf-7a74a4a0"}},
      {"id":"c4-78444877","label":"Supervisor","type":"container","kind":"service","parent":null,"badge":6,"capability_badge":5,"analysis_state":"analyzed","provenance":{"source":"artifact","locator":"code-architecture-brief.md §1 Supervisor privileged API (http://supervisor/, SUPERVISOR_TOKEN + per-role URL ACL) + ingress proxy","first_finding_id":"auth-4e7d1059"}},
      {"id":"c4-7978cb3b","label":"Non-admin / low-priv user (group-scoped permission policy)","type":"person","kind":"human_role","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#permissions, lines 9-12 (group membership grants permissions)"}},
      {"id":"c4-7bf521e1","label":"Container base images (alpine/debian) wheels/npm supply chai","type":"external_system","kind":"external_dependency","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"line 1 (BUILD_FROM ghcr.io base-python image) + wheels mount lines 36-48"}},
      {"id":"c4-7f55d47c","label":"mobile-apps-fcm-push relay (Firebase Cloud Functions)","type":"external_system","kind":"external_dependency","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#mobile-apps-fcm-push, lines 1-2, 42-47 (firebase deploy, push relay)"}},
      {"id":"c4-84087d5b","label":"homeassistant.auth.permissions.filter_entity_ids_by_permissi","type":"code","kind":"function","parent":"c4-2b33e14f","badge":1,"capability_badge":1,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.permissions.filter_entity_ids_by_permission","repo":"core","first_finding_id":"merged-66801b1b"}},
      {"id":"c4-858fb41b","label":"supervisor.docker.manager.DockerAPI.__init__","type":"code","kind":"function","parent":"c4-78444877","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"supervisor.docker.manager.DockerAPI.__init__","repo":"supervisor","first_finding_id":"dist-d08ed969"}},
      {"id":"c4-85956d05","label":"home-assistant.io","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:home-assistant.io"}},
      {"id":"c4-8a7a12d5","label":"mosquitto.config.yaml","type":"code","kind":"module","parent":"c4-c4507c07","badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"mosquitto.config.yaml","repo":"addons"}},
      {"id":"c4-8bd848dd","label":"plugin-cli","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:plugin-cli"}},
      {"id":"c4-9133e640","label":"common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocket","type":"code","kind":"function","parent":"c4-f7d01fcf","badge":4,"capability_badge":1,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"common...data.TLSHelper.TLSHelper.setupOkHttpClientSSLSocketFactory","repo":"android","first_finding_id":"auth-1787eae1"}},
      {"id":"c4-975cfbd4","label":"wheels","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:wheels"}},
      {"id":"c4-9904ee7d","label":"Third-party integration / device principal (untrusted device","type":"person","kind":"external_party","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#trust-boundaries item 6 (untrusted device/cloud responses)"}},
      {"id":"c4-9a8a0efa","label":"Owner user (onboarding user all permissions)","type":"person","kind":"human_role","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#owner, lines 27-29 (always all permissions)"}},
      {"id":"c4-9e5151b7","label":"iOS Companion","type":"container","kind":"app","parent":null,"badge":7,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"artifact","locator":"code-architecture-brief.md §1/§2 iOS Companion: WebView external bus + ServerManagerKeychain (default Keychain accessibility class)","first_finding_id":"auth-ea69d3a2"}},
      {"id":"c4-9f32940b","label":"homeassistant.components.mobile_app.webhook.handle_webhook","type":"code","kind":"function","parent":"c4-2b33e14f","badge":7,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.mobile_app.webhook.handle_webhook","repo":"core","first_finding_id":"auth-3f2314a4"}},
      {"id":"c4-a697b2ea","label":"homeassistant.auth.providers.homeassistant.Data.validate_log","type":"code","kind":"function","parent":"c4-2b33e14f","badge":null,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.auth.providers.homeassistant.Data.validate_login","repo":"core"}},
      {"id":"c4-a811b55d","label":"Frontend (Lit/TS)","type":"container","kind":"app","parent":null,"badge":3,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-07000001 (src.external_app.external_messaging.ExternalMessaging._sendExternal — Lit/TS JS external-auth bridge served remotely into the WebView)","first_finding_id":"auth-ea69d3a2"}},
      {"id":"c4-aa3d3890","label":"homeassistant.components.websocket_api.auth.AuthPhase.async_","type":"code","kind":"function","parent":"c4-2b33e14f","badge":3,"capability_badge":5,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.websocket_api.auth.AuthPhase.async_handle","repo":"core","first_finding_id":"avail-4be2dd70"}},
      {"id":"c4-aa5a3a58","label":"ha CLI","type":"container","kind":"app","parent":null,"badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-d4000001 (client.helper.URLHelper — ha CLI builds the Supervisor API URL)","first_finding_id":"auth-23048c0c"}},
      {"id":"c4-ab1ad354","label":"Nabu Casa cloud relay / cloudhook (remote access cloudhook_u","type":"external_system","kind":"external_dependency","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"registration response, lines 74-79 (cloudhook_url, remote_ui_url)"}},
      {"id":"c4-ae94d359","label":"supervisor.backups.backup.Backup.set_password","type":"code","kind":"function","parent":"c4-78444877","badge":3,"capability_badge":1,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"supervisor.backups.backup.Backup.set_password","repo":"supervisor","first_finding_id":"avail-5af6fee5"}},
      {"id":"c4-bc1e61b2","label":"docker","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:docker"}},
      {"id":"c4-bddd59fe","label":"Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessa","type":"code","kind":"function","parent":"c4-9e5151b7","badge":4,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"Sources.App.Frontend.ExternalMessageBus.WebViewExternalMessageHandler.handleExternalMessage","repo":"iOS","first_finding_id":"auth-ea69d3a2"}},
      {"id":"c4-bf3dfe59","label":"supervisor.api.middleware.security.SecurityMiddleware.token_","type":"code","kind":"function","parent":"c4-78444877","badge":3,"capability_badge":3,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"supervisor.api.middleware.security.SecurityMiddleware.token_validation","repo":"supervisor","first_finding_id":"merged-1119b0be"}},
      {"id":"c4-bfb3f82b","label":"supervisor.api.middleware.security.SecurityMiddleware.ADDONS","type":"code","kind":"module","parent":"c4-78444877","badge":null,"capability_badge":1,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"supervisor.api.middleware.security.SecurityMiddleware.ADDONS_ROLE_ACCESS","repo":"supervisor"}},
      {"id":"c4-c4507c07","label":"Add-ons","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-09000001 (mosquitto.config.yaml — add-on manifest declaring auth_api role + host mounts that SecurityMiddleware enforces)"}},
      {"id":"c4-cc1569b3","label":"home-assistant-js-websocket","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:home-assistant-js-websocket"}},
      {"id":"c4-cd46fff5","label":"supervisor.api.ingress._init_header","type":"code","kind":"function","parent":"c4-78444877","badge":1,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"supervisor.api.ingress._init_header","repo":"supervisor","first_finding_id":"auth-4e7d1059"}},
      {"id":"c4-ceca8483","label":"developers.home-assistant","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:developers.home-assistant"}},
      {"id":"c4-cecf1484","label":"homeassistant.components.api.APIEntityStateView.get","type":"code","kind":"route","parent":"c4-2b33e14f","badge":2,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.api.APIEntityStateView.get","repo":"core","first_finding_id":"conf-ef49b4b0"}},
      {"id":"c4-d1ea3a05","label":".storage (plaintext JSON config/secrets/tokens)","type":"container","kind":"data_store","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-a1000017 (Store._write_prepared_data — .storage written as plaintext UTF-8 JSON, no encryption-at-rest; brief §2)"}},
      {"id":"c4-d2789629","label":"homeassistant.components.api.APIEntityStateView.post","type":"code","kind":"route","parent":"c4-2b33e14f","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.api.APIEntityStateView.post","repo":"core","first_finding_id":"merged-66801b1b"}},
      {"id":"c4-d304503a","label":"os-agent","type":"container","kind":"compute","parent":null,"badge":4,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-c3000001 (system.system.AddSSHAuthKey — D-Bus host primitive: root SSH-key write)","first_finding_id":"auth-6924f467"}},
      {"id":"c4-d3b30ed4","label":"architecture","type":"container","kind":"service","parent":null,"badge":null,"capability_badge":0,"analysis_state":"not_analyzed","provenance":{"source":"code_evidence","locator":"repos[]:architecture"}},
      {"id":"c4-d439ef43","label":"Ingress-authenticated user (X-Remote-User-Id/Name headers)","type":"person","kind":"human_role","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"asset_inventory","locator":"#authenticating-a-user-when-using-ingress, lines 40-48"}},
      {"id":"c4-dac0a1a3","label":"src.external_app.external_messaging.ExternalMessaging._sendE","type":"code","kind":"function","parent":"c4-a811b55d","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"src.external_app.external_messaging.ExternalMessaging._sendExternal","repo":"frontend","first_finding_id":"conf-3060c50e"}},
      {"id":"c4-eab86774","label":"system.system.ScheduleWipeDevice","type":"code","kind":"function","parent":"c4-d304503a","badge":4,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"system.system.ScheduleWipeDevice","repo":"os-agent","first_finding_id":"auth-6924f467"}},
      {"id":"c4-f08b7afb","label":"common...database.DatabaseModule.DatabaseModule.provideAppDa","type":"code","kind":"function","parent":"c4-f7d01fcf","badge":1,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"common...database.DatabaseModule.DatabaseModule.provideAppDatabase","repo":"android","first_finding_id":"conf-205c53a5"}},
      {"id":"c4-f7d01fcf","label":"Android Companion","type":"container","kind":"app","parent":null,"badge":6,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"artifact","locator":"code-architecture-brief.md §1/§2 Android Companion: LaunchActivity deep-link entry + DatabaseModule.provideAppDatabase (unencrypted Room) + AndroidKeyStore mTLS key","first_finding_id":"auth-1787eae1"}},
      {"id":"c4-fb9078ee","label":"Android Room AppDatabase","type":"container","kind":"data_store","parent":null,"badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-f6000003 (DatabaseModule.provideAppDatabase — unencrypted SQLite: location_history + session-token rows; brief §2)"}},
      {"id":"c4-fcee7bf9","label":"FCM push relay","type":"container","kind":"service","parent":null,"badge":4,"capability_badge":2,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"code-evidence-index.yaml#cev-08000002 (__route__POST__/api/sendPushNotification — Firebase Cloud Function push relay)","first_finding_id":"auth-23048c0c"}},
      {"id":"c4-fd561b56","label":"homeassistant.components.http.auth.async_setup_auth.auth_mid","type":"code","kind":"function","parent":"c4-2b33e14f","badge":null,"capability_badge":0,"analysis_state":"analyzed","provenance":{"source":"code_evidence","locator":"homeassistant.components.http.auth.async_setup_auth.auth_middleware","repo":"core"}}
    ],
    "edges": [
      {"id":"c4e-256f048b","source":"c4-9e5151b7","target":"c4-2b33e14f","label":"CROSS_HTTP_CALLS — iOS Companion WKWebView loads + calls the user-configured Core REST/WS instance (user-entered self-hosted URL)","machine_extracted":false},
      {"id":"c4e-381ea08b","source":"c4-78444877","target":"c4-66dae27f","label":"CROSS_CHANNEL — Supervisor controls the host Docker daemon over the shared /run/docker.sock unix socket (host-root control plane)","machine_extracted":false},
      {"id":"c4e-384bedb4","source":"c4-78444877","target":"c4-2b33e14f","label":"CROSS_HTTP_CALLS — Supervisor POSTs Core /auth/token + calls the Core API as a privileged client (runtime container IP)","machine_extracted":false},
      {"id":"c4e-60bdd445","source":"c4-78444877","target":"c4-d304503a","label":"CROSS_CHANNEL — Supervisor calls os-agent host primitives over the system D-Bus (io.hass.os; container -> host root)","machine_extracted":false},
      {"id":"c4e-9e7befef","source":"c4-2b33e14f","target":"c4-fcee7bf9","label":"CROSS_HTTP_CALLS — Core mobile_app integration pushes to the FCM relay Cloud Function, which forwards to APNS/FCM (external Firebase URL)","machine_extracted":false},
      {"id":"c4e-b1f89879","source":"c4-aa5a3a58","target":"c4-78444877","label":"CROSS_HTTP_CALLS — ha CLI invokes the Supervisor API (runtime viper endpoint host)","machine_extracted":false}
    ]
  };
  ```

  > NOTE on edge `label`: the FULL machine string is kept verbatim here (the
  > prototype's `_safe_label` 60-char truncation of edge labels is a render concern
  > and Task 4's `c4ShortEdgeLabel` re-derives the short display string from this
  > full string; the full string is also what shows in the hover tooltip).

- [ ] **Run the harness green.**
  ```bash
  node "docs/superpowers/design_handoff_c4_architecture_view/prototype/check-fixture-keys.js"
  # EXPECT: fixture key check OK: 82 nodes, 6 edges, real keys present, abbreviations absent.
  ```

- [ ] **Verify the prototype `.html` renderer no longer references abbreviation keys.**
  The prototype script reads `n.state`/`n.cap`/`n.ff`/`e.me`/`C4.overlay_paths` —
  those are now wrong against the regenerated fixture. Grep to surface every site,
  then update the prototype's `badgeHTML`/`nodeBox`/`showTip`/`overlaySet` reads to
  the real keys (`n.analysis_state`/`n.capability_badge`/`n.provenance.first_finding_id`/
  `e.machine_extracted`; drop the `overlay_paths` toggle entirely — overlays are
  rebuilt from `attack_paths` in the React scene, NOT shipped on the fixture).

  ```bash
  grep -nE '\.state\b|\.cap\b|\.ff\b|\.me\b|overlay_paths' \
    "docs/superpowers/design_handoff_c4_architecture_view/prototype/APD Gauntlet Architecture (C4).html"
  # EXPECT after edits: no matches (or only matches inside comments/strings, none in live reads)
  ```

  This keeps the prototype a faithful, self-consistent reference for the React port
  (Task 5) rather than a misleading one. (If the prototype's L3-demo synthetic
  toggle still reads `state`/`cap`, delete that toggle now — the shared contract
  forbids porting it anyway.)

- [ ] **Add the "Field-name crosswalk (fixture vs production)" note to the handoff README.**
  Insert this subsection immediately after the "Edge labels:" paragraph (README
  §259-263) and before the `---` separator at §265, so a reader who lands on the
  layout/edge sections sees the contract right there:

  ```markdown
  ### Field-name crosswalk (fixture vs production)

  The prototype's `archx-data.js` fixture (`window.C4_DATA`) is now a faithful copy
  of the **production** `window.APD_DATA.c4_model` slice that
  `tools/apd_gauntlet/report/transform.py::c4_model_view` emits. The React scene MUST
  read the production names — there are no abbreviations. Earlier drafts of this
  fixture used short keys; the table below is the historical crosswalk so reviewers
  of the prototype `.html` are not confused:

  | Production key (use this)        | Old fixture abbrev (do NOT use) | Notes |
  |----------------------------------|----------------------------------|-------|
  | `node.type` (= C4 level)         | —                                | `system\|person\|external_system\|container\|component\|code` |
  | `node.kind`                      | —                                | service/data_store/compute/app/external_system; function/class/route/module |
  | `node.badge`                     | —                                | `finding_count` when > 0, else `null` (never `0`; "0 ≠ clean") |
  | `node.capability_badge`          | `node.cap`                       | integer, `0` when none |
  | `node.analysis_state`            | `node.state`                     | `analyzed` \| `not_analyzed` |
  | `node.provenance.first_finding_id` | `node.ff`                      | per-node ⚑ deep-link key (present only when `badge` > 0) |
  | `node.provenance{source,locator,repo}` | —                          | passed through verbatim from the assembler |
  | `edge.machine_extracted`         | `edge.me`                        | boolean |
  | `edge.label`                     | —                                | FULL machine string (e.g. `CROSS_HTTP_CALLS …`); short label derived at render |
  | top: `present`, `levels_present`, `not_analyzed_count`, `unlocalized_findings`, `asset_to_c4`, `finding_to_c4` | (omitted) | rollups + overlay crosswalks; `asset_to_c4`/`finding_to_c4` are grounded-only and may be `{}` |
  | (removed) | `overlay_paths` | **fabricated** in the old fixture — attack-path overlays are rebuilt from `data.attack_paths` + `asset_to_c4`/`finding_to_c4`, never shipped on the c4 slice |

  The backbone positions and short edge labels the prototype hard-codes
  (`BACKBONE` / `EDGE_SHORT` / `ANALYZED_SHELF` constants) are **render-derived in
  production** by `c4BackboneLayout` / `c4ShortEdgeLabel` (see Layout strategy + Edge
  labels above) — they are deliberately NOT fixture fields.
  ```

- [ ] **Commit.** `git add` the regenerated fixture, the new harness, the patched
  prototype `.html`, and the README; commit
  `docs(c4): regenerate prototype fixture to real c4_model_view keys + crosswalk note`.

---

### Task 3: `c4BackboneLayout(nodes, edges)` — deterministic layered backbone + analyzed/infra shelves

The prototype hard-codes a `BACKBONE` position map and a curated `ANALYZED_SHELF`
order for the home-assistant run. Production must derive both deterministically from
the data so any run renders reproducibly. This task adds the pure helper
`c4BackboneLayout` to `components.jsx` (window-exported), implementing the README
"Layout strategy" algorithm (§267-294): partition containers into
`connected`/`analyzed`/`infra`, lay the `connected` set out in layered longest-path
columns over the edge subgraph, and emit `analyzed`/`infra` as label-sorted shelves.
It returns logical `{col,row}` / shelf-order — pixel positions and SVG routing are
the renderer's job (Task 5), which measures the rendered boxes (router ported
verbatim), so this helper has no DOM/measurement dependency and is unit-testable
with node.

**Files:**
- Modify: `report-template/components.jsx` (add `c4BackboneLayout` + window export)
- Create: `report-template/__c4_helpers_check.js` (node harness; the helpers' "test" — the report has no JS test runner)
- Modify: `tests/test_workflow_apd_gauntlet.py` (string-assert the helper exists in source + the bundle)

**Steps:**

- [ ] **Write the failing node harness FIRST** (covers Task 3 and Task 4 — extend
  it in Task 4). It extracts the helper bodies from `components.jsx` and exercises
  them; it cannot pass until the helper exists. Create
  `report-template/__c4_helpers_check.js`:

  ```js
  // __c4_helpers_check.js — node harness for the pure C4 render helpers.
  // The report has no JS test runner; this asserts determinism + the real
  // home-assistant cases for c4BackboneLayout (Task 3) and c4ShortEdgeLabel
  // (Task 4). Strategy: load components.jsx, strip JSX-bearing lines is unsafe,
  // so instead we eval ONLY the two pure helper function declarations, which we
  // locate by name and brace-match. Usage: node __c4_helpers_check.js
  'use strict';
  const fs = require('fs');
  const path = require('path');

  const src = fs.readFileSync(path.join(__dirname, 'components.jsx'), 'utf8');

  // Extract a top-level `function NAME(...) { ... }` by brace matching.
  function extractFn(name) {
    const sig = `function ${name}(`;
    const start = src.indexOf(sig);
    if (start < 0) throw new Error(`helper not found in components.jsx: ${name}`);
    let i = src.indexOf('{', start);
    let depth = 0;
    for (; i < src.length; i++) {
      if (src[i] === '{') depth++;
      else if (src[i] === '}') { depth--; if (depth === 0) { i++; break; } }
    }
    return src.slice(start, i);
  }

  // eslint-disable-next-line no-new-func
  const c4BackboneLayout = new Function(
    `${extractFn('c4BackboneLayout')}; return c4BackboneLayout;`)();
  // c4ShortEdgeLabel wired in Task 4:
  let c4ShortEdgeLabel = null;
  try {
    // eslint-disable-next-line no-new-func
    c4ShortEdgeLabel = new Function(
      `${extractFn('c4ShortEdgeLabel')}; return c4ShortEdgeLabel;`)();
  } catch (_) { /* Task 4 not landed yet */ }

  const fails = [];
  const eq = (a, b, msg) => {
    const A = JSON.stringify(a), B = JSON.stringify(b);
    if (A !== B) fails.push(`${msg}\n      got: ${A}\n      exp: ${B}`);
  };
  const ok = (c, m) => { if (!c) fails.push(m); };

  // ── c4BackboneLayout: the REAL home-assistant connected subgraph ───────────
  // 6 grounded edges + the 7 endpoints, plus 2 analyzed-no-edge + 2 infra to
  // exercise the shelves. (Subset of the real run — only containers matter.)
  const haNodes = [
    {id:'c4-9e5151b7',label:'iOS Companion',type:'container',analysis_state:'analyzed',badge:7},
    {id:'c4-2b33e14f',label:'Home Assistant Core',type:'container',analysis_state:'analyzed',badge:22},
    {id:'c4-78444877',label:'Supervisor',type:'container',analysis_state:'analyzed',badge:6},
    {id:'c4-66dae27f',label:'host-dockerd',type:'container',analysis_state:'not_analyzed',badge:null},
    {id:'c4-d304503a',label:'os-agent',type:'container',analysis_state:'analyzed',badge:4},
    {id:'c4-fcee7bf9',label:'FCM push relay',type:'container',analysis_state:'analyzed',badge:4},
    {id:'c4-aa5a3a58',label:'ha CLI',type:'container',analysis_state:'analyzed',badge:1},
    {id:'c4-a811b55d',label:'Frontend (Lit/TS)',type:'container',analysis_state:'analyzed',badge:3},
    {id:'c4-f7d01fcf',label:'Android Companion',type:'container',analysis_state:'analyzed',badge:6},
    {id:'c4-bc1e61b2',label:'docker',type:'container',analysis_state:'not_analyzed',badge:null},
    {id:'c4-07f5a3e6',label:'plugin-dns',type:'container',analysis_state:'not_analyzed',badge:null},
    // a code node + a person — must be IGNORED (containers only)
    {id:'c4-2d5eaa33',label:'session_scope',type:'code',parent:'c4-2b33e14f',analysis_state:'analyzed',badge:6},
    {id:'c4-9a8a0efa',label:'Owner user',type:'person',analysis_state:'analyzed',badge:null},
  ];
  const haEdges = [
    {source:'c4-9e5151b7',target:'c4-2b33e14f'},
    {source:'c4-78444877',target:'c4-66dae27f'},
    {source:'c4-78444877',target:'c4-2b33e14f'},
    {source:'c4-78444877',target:'c4-d304503a'},
    {source:'c4-2b33e14f',target:'c4-fcee7bf9'},
    {source:'c4-aa5a3a58',target:'c4-78444877'},
  ];

  const out = c4BackboneLayout(haNodes, haEdges);

  // Longest-path columns: ha CLI/iOS = col0; Supervisor = col1;
  // Core+host-dockerd+os-agent = col2; FCM = col3. Within a column: label asc,
  // then badge desc. (Verified by hand against the §267-294 algorithm.)
  eq(out.connected, [
    {id:'c4-aa5a3a58',col:0,row:0},   // "ha CLI"
    {id:'c4-9e5151b7',col:0,row:1},   // "iOS Companion"
    {id:'c4-78444877',col:1,row:0},   // "Supervisor"
    {id:'c4-2b33e14f',col:2,row:0},   // "Home Assistant Core"
    {id:'c4-66dae27f',col:2,row:1},   // "host-dockerd"
    {id:'c4-d304503a',col:2,row:2},   // "os-agent"
    {id:'c4-fcee7bf9',col:3,row:0},   // "FCM push relay"
  ], 'c4BackboneLayout connected (HA longest-path columns)');

  // analyzed shelf = analyzed containers NOT in any edge, label asc
  eq(out.analyzed, ['c4-f7d01fcf','c4-a811b55d'],   // "Android Companion","Frontend (Lit/TS)"
     'c4BackboneLayout analyzed shelf (label asc)');
  // infra shelf = not_analyzed containers, label asc
  eq(out.infra, ['c4-bc1e61b2','c4-07f5a3e6'],       // "docker","plugin-dns"
     'c4BackboneLayout infra shelf (label asc)');

  // Code/person nodes excluded entirely
  const allIds = [...out.connected.map(n=>n.id), ...out.analyzed, ...out.infra];
  ok(!allIds.includes('c4-2d5eaa33'), 'code node must be excluded from layout');
  ok(!allIds.includes('c4-9a8a0efa'), 'person node must be excluded from layout');

  // ── DETERMINISM: same input → byte-identical output, and INPUT-ORDER stable ─
  eq(c4BackboneLayout(haNodes, haEdges), out, 'c4BackboneLayout deterministic (re-run)');
  const shuffled = [...haNodes].reverse();
  const shufEdges = [...haEdges].reverse();
  eq(c4BackboneLayout(shuffled, shufEdges), out,
     'c4BackboneLayout stable under input reordering');

  // ── tiny synthetic fixture: a cycle (break by first-seen) + an isolated edge ─
  const cyNodes = [
    {id:'a',label:'Aye',type:'container',analysis_state:'analyzed',badge:1},
    {id:'b',label:'Bee',type:'container',analysis_state:'analyzed',badge:1},
    {id:'c',label:'Cee',type:'container',analysis_state:'analyzed',badge:1},
  ];
  const cyEdges = [
    {source:'a',target:'b'},
    {source:'b',target:'c'},
    {source:'c',target:'a'},   // cycle back to a — must NOT loop forever
  ];
  const cy = c4BackboneLayout(cyNodes, cyEdges);
  ok(cy.connected.length === 3, 'cycle: all 3 nodes placed');
  ok(cy.connected.every(n => typeof n.col === 'number' && n.col >= 0),
     'cycle: every node gets a finite non-negative column (no infinite layering)');
  eq(c4BackboneLayout(cyNodes, cyEdges), cy, 'cycle layout deterministic');

  // ── helper run on empty/degenerate input ───────────────────────────────────
  eq(c4BackboneLayout([], []), {connected:[],analyzed:[],infra:[]},
     'empty input → empty partitions');

  if (c4ShortEdgeLabel) {
    // ── Task 4 cases (filled in when c4ShortEdgeLabel lands) ─────────────────
    eq(c4ShortEdgeLabel('CROSS_HTTP_CALLS — Supervisor POSTs Core /auth/token + calls the Core API as a privileged client (runtime container IP)'),
       'Supervisor POSTs Core', 'short: Supervisor->Core /auth/token');
    eq(c4ShortEdgeLabel('CROSS_CHANNEL — Supervisor controls the host Docker daemon over the shared /run/docker.sock unix socket (host-root control plane)'),
       'Supervisor controls the', 'short: controls daemon');
    eq(c4ShortEdgeLabel('CROSS_CHANNEL — Supervisor calls os-agent host primitives over the system D-Bus (io.hass.os; container -> host root)'),
       'Supervisor calls os-agent', 'short: host primitives');
    eq(c4ShortEdgeLabel('CROSS_HTTP_CALLS — Core mobile_app integration pushes to the FCM relay Cloud Function, which forwards to APNS/FCM (external Firebase URL)'),
       'Core mobile_app integration', 'short: pushes to FCM');
    eq(c4ShortEdgeLabel('CROSS_HTTP_CALLS — ha CLI invokes the Supervisor API (runtime viper endpoint host)'),
       'ha CLI invokes', 'short: ha CLI invokes');
    eq(c4ShortEdgeLabel('CROSS_HTTP_CALLS — iOS Companion WKWebView loads + calls the user-configured Core REST/WS instance (user-entered self-hosted URL)'),
       'iOS Companion WKWebView', 'short: iOS loads/calls');
    // _safe_label may collapse the em dash → space; still strips the prefix
    eq(c4ShortEdgeLabel('CROSS_HTTP_CALLS Supervisor POSTs Core /auth/token + calls'),
       'Supervisor POSTs Core', 'short: no-dash variant');
    eq(c4ShortEdgeLabel(''), '', 'short: empty → empty');
    eq(c4ShortEdgeLabel(null), '', 'short: null → empty');
    eq(c4ShortEdgeLabel('no prefix here just plain words'),
       'no prefix here', 'short: no CROSS_ prefix → first 3 words');
    eq(c4ShortEdgeLabel('CROSS_HTTP_CALLS — Supervisor POSTs Core /auth/token + calls'),
       c4ShortEdgeLabel('CROSS_HTTP_CALLS — Supervisor POSTs Core /auth/token + calls'),
       'short: deterministic');
  }

  if (fails.length) {
    console.error(`C4 HELPERS CHECK FAILED (${fails.length}):`);
    fails.forEach(f => console.error('  - ' + f));
    process.exit(1);
  }
  console.log(`c4 helpers check OK (c4BackboneLayout${c4ShortEdgeLabel ? ' + c4ShortEdgeLabel' : ''}).`);
  ```

  Run it red:
  ```bash
  node report-template/__c4_helpers_check.js
  # EXPECT: throws "helper not found in components.jsx: c4BackboneLayout" → exit 1
  ```

- [ ] **Add the Python string-assertion (red).** Append to
  `tests/test_workflow_apd_gauntlet.py`:

  ```python
  def test_c4_backbone_layout_helper_present():
      """The deterministic backbone-layout helper is defined + window-exported in
      components.jsx (and so present in the built bundle). It is the data-driven
      replacement for the prototype's hard-coded BACKBONE map."""
      src = (REPORT_TEMPLATE_DIR / "components.jsx").read_text(encoding="utf-8")
      assert "function c4BackboneLayout(" in src
      # returns the three partitions the tier scene consumes
      assert "connected" in src and "analyzed" in src and "infra" in src
      # window-exported alongside the other helpers
      assert "c4BackboneLayout" in src.split("Object.assign(window")[1]
      bundle = (REPORT_TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")
      assert "c4BackboneLayout" in bundle
  ```

  ```bash
  .venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_backbone_layout_helper_present -q
  # EXPECT: FAIL (helper not in source/bundle yet)
  ```

- [ ] **Implement `c4BackboneLayout` (minimal, pure, deterministic).** Add to
  `report-template/components.jsx`, near the other pure top-level helpers (NOT
  inside a component). Algorithm exactly per README §267-294: partition → layered
  longest-path columns over the connected subgraph (col 0 = no incoming; relax
  `col[t] = max(col[t], col[s]+1)` to a fixed point, which assigns the LONGEST path
  and is inherently cycle-safe because columns are bounded by node count) → stable
  sort within a column (label asc, then badge desc, then id asc as the final
  tiebreak for byte-stability) → shelves sorted by label asc (then id asc).

  ```jsx
  // ── C4 tiered-scene pure helpers (no DOM; deterministic; window-exported) ───
  // c4BackboneLayout: data-driven replacement for the prototype's hard-coded
  // BACKBONE/ANALYZED_SHELF. Partitions CONTAINER nodes into connected (in any
  // edge), analyzed (no edge, analysis_state!=="not_analyzed"), infra
  // (not_analyzed); lays the connected set out in layered longest-path columns
  // over the edge subgraph and returns logical {col,row}. Pixel positions +
  // SVG routing are the renderer's job (it measures the rendered boxes), so this
  // helper is pure + node-testable. Fully deterministic / stable-sorted.
  function c4BackboneLayout(nodes, edges) {
    const containers = (nodes || []).filter(function (n) { return n && n.type === "container"; });
    const byId = {};
    containers.forEach(function (n) { byId[n.id] = n; });

    // 1. partition. connected = appears as either endpoint of an edge whose BOTH
    //    ends are containers we know.
    const sub = [];
    const endpoints = {};
    (edges || []).forEach(function (e) {
      if (e && byId[e.source] && byId[e.target]) {
        sub.push(e);
        endpoints[e.source] = true;
        endpoints[e.target] = true;
      }
    });
    const connectedIds = containers.filter(function (n) { return endpoints[n.id]; }).map(function (n) { return n.id; });
    const connSet = {};
    connectedIds.forEach(function (id) { connSet[id] = true; });
    const analyzedIds = containers.filter(function (n) {
      return !connSet[n.id] && n.analysis_state !== "not_analyzed";
    }).map(function (n) { return n.id; });
    const infraIds = containers.filter(function (n) {
      return !connSet[n.id] && n.analysis_state === "not_analyzed";
    }).map(function (n) { return n.id; });

    // 2. layered longest-path columns over the connected subgraph.
    const indeg = {};
    connectedIds.forEach(function (id) { indeg[id] = 0; });
    sub.forEach(function (e) { if (connSet[e.source] && connSet[e.target]) indeg[e.target]++; });
    const col = {};
    connectedIds.forEach(function (id) { col[id] = 0; }); // col 0 = no incoming (and default)
    // Relax to longest path. Iterate edges in a STABLE order; bounded by node
    // count (longest simple path can't exceed N-1), so cycles terminate cleanly.
    const orderedEdges = sub.filter(function (e) {
      return connSet[e.source] && connSet[e.target];
    }).slice().sort(function (a, b) {
      const ka = a.source + "|" + a.target, kb = b.source + "|" + b.target;
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });
    const maxPasses = connectedIds.length + 1;
    for (let pass = 0; pass < maxPasses; pass++) {
      let changed = false;
      for (let i = 0; i < orderedEdges.length; i++) {
        const e = orderedEdges[i];
        const want = col[e.source] + 1;
        // cap at N-1 so a cycle can't inflate columns past the bound
        if (want <= connectedIds.length - 1 && col[e.target] < want) {
          col[e.target] = want;
          changed = true;
        }
      }
      if (!changed) break;
    }

    // 3. group by column; stable-sort within column: label asc, badge desc, id asc.
    const cmpInCol = function (a, b) {
      const na = byId[a], nb = byId[b];
      const la = na.label || "", lb = nb.label || "";
      if (la !== lb) return la < lb ? -1 : 1;
      const ba = na.badge || 0, bb = nb.badge || 0;
      if (ba !== bb) return bb - ba; // foreground hot nodes
      return a < b ? -1 : a > b ? 1 : 0;
    };
    const cols = {};
    connectedIds.forEach(function (id) {
      const c = col[id];
      (cols[c] = cols[c] || []).push(id);
    });
    const connected = [];
    Object.keys(cols).map(Number).sort(function (a, b) { return a - b; }).forEach(function (c) {
      cols[c].slice().sort(cmpInCol).forEach(function (id, row) {
        connected.push({ id: id, col: c, row: row });
      });
    });

    // 4. shelves: label asc, id asc tiebreak.
    const shelfCmp = function (a, b) {
      const la = byId[a].label || "", lb = byId[b].label || "";
      if (la !== lb) return la < lb ? -1 : 1;
      return a < b ? -1 : a > b ? 1 : 0;
    };
    return {
      connected: connected,
      analyzed: analyzedIds.slice().sort(shelfCmp),
      infra: infraIds.slice().sort(shelfCmp),
    };
  }
  ```

  Add `c4BackboneLayout` to the existing `Object.assign(window, { … })` export
  block in `components.jsx` (the same block that exports `GraphView`/the other
  helpers), e.g. `Object.assign(window, { …, c4BackboneLayout, … });`.

- [ ] **Run the node harness green (Task-3 portion).**
  ```bash
  node report-template/__c4_helpers_check.js
  # EXPECT: c4 helpers check OK (c4BackboneLayout).   ← c4ShortEdgeLabel lands in Task 4
  ```

- [ ] **Rebuild the bundle, then run the Python assertion green.**
  ```bash
  .venv/bin/python tools/build_report_template.py
  .venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_backbone_layout_helper_present -q
  # EXPECT: 1 passed
  ```

- [ ] **Commit** (helper + harness + test + regenerated bundle/.source-hash):
  `feat(report): deterministic c4BackboneLayout helper (layered longest-path backbone + shelves)`.

---

### Task 4: `c4ShortEdgeLabel(rawLabel)` — deterministic short edge label (full string kept for hover)

The raw `edge.label` is a long machine string (e.g.
`"CROSS_HTTP_CALLS — Supervisor POSTs Core /auth/token + calls …"`). The prototype
hand-curates a short `EDGE_SHORT` map per run; production must derive the short
display label deterministically (README §259-263) and keep the full string for the
hover tooltip (the renderer wires the tooltip in Task 5). This task adds the pure
helper `c4ShortEdgeLabel` to `components.jsx`: strip a leading `CROSS_[A-Z_]+` token
(plus any following dash/colon separators), then take the first ~3 meaningful words.

**Files:**
- Modify: `report-template/components.jsx` (add `c4ShortEdgeLabel` + window export)
- Modify: `report-template/__c4_helpers_check.js` (already contains the Task-4 cases under the `if (c4ShortEdgeLabel)` guard from Task 3 — they now run live)
- Modify: `tests/test_workflow_apd_gauntlet.py` (string-assert helper exists in source + bundle)

**Steps:**

- [ ] **Confirm the Task-4 cases are currently dormant (red-by-absence).** The node
  harness from Task 3 already encodes every Task-4 assertion, guarded by
  `if (c4ShortEdgeLabel)`. Because the helper does not yet exist, those assertions
  are SKIPPED today (harness prints `c4 helpers check OK (c4BackboneLayout).`).
  Flip the guard to a hard requirement so the harness FAILS until the helper lands:
  in `__c4_helpers_check.js`, immediately before the final `if (fails.length)`
  block, add:

  ```js
  ok(typeof c4ShortEdgeLabel === "function",
     "c4ShortEdgeLabel must be defined in components.jsx (Task 4)");
  ```

  ```bash
  node report-template/__c4_helpers_check.js
  # EXPECT: C4 HELPERS CHECK FAILED — c4ShortEdgeLabel must be defined … exit 1
  ```

- [ ] **Add the Python string-assertion (red).** Append to
  `tests/test_workflow_apd_gauntlet.py`:

  ```python
  def test_c4_short_edge_label_helper_present():
      """The deterministic short-edge-label helper is defined + window-exported in
      components.jsx (data-driven replacement for the prototype's hand-curated
      EDGE_SHORT map). The full edge.label is kept for the hover tooltip."""
      src = (REPORT_TEMPLATE_DIR / "components.jsx").read_text(encoding="utf-8")
      assert "function c4ShortEdgeLabel(" in src
      # strips the CROSS_* machine prefix deterministically
      assert "CROSS_" in src.split("function c4ShortEdgeLabel(")[1].split("\n}")[0]
      assert "c4ShortEdgeLabel" in src.split("Object.assign(window")[1]
      bundle = (REPORT_TEMPLATE_DIR / "app.js").read_text(encoding="utf-8")
      assert "c4ShortEdgeLabel" in bundle
  ```

  ```bash
  .venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_short_edge_label_helper_present -q
  # EXPECT: FAIL
  ```

- [ ] **Implement `c4ShortEdgeLabel` (minimal, pure, deterministic).** Add to
  `report-template/components.jsx`, beside `c4BackboneLayout`:

  ```jsx
  // c4ShortEdgeLabel: deterministic short display label for a C4 edge. Strips a
  // leading CROSS_<TYPE> machine token (+ following — / - / : separators) and
  // returns the first 3 meaningful words. The FULL rawLabel is kept by the caller
  // for the hover tooltip. Replaces the prototype's hand-curated EDGE_SHORT map.
  // Pure / deterministic (no run-dependent state); empty/nullish → "".
  function c4ShortEdgeLabel(rawLabel) {
    let s = rawLabel == null ? "" : String(rawLabel);
    // strip a leading CROSS_<UPPER/_> token and any run of separator chars after it
    s = s.replace(/^\s*CROSS_[A-Z_]+\s*[—:-]*\s*/, "");
    s = s.trim();
    if (!s) return "";
    const words = s.split(/\s+/).filter(Boolean);
    return words.slice(0, 3).join(" ");
  }
  ```

  Add `c4ShortEdgeLabel` to the same `Object.assign(window, { … })` export block.

- [ ] **Run the node harness green** (Task-3 + Task-4 cases now both live, including
  every real home-assistant label):
  ```bash
  node report-template/__c4_helpers_check.js
  # EXPECT: c4 helpers check OK (c4BackboneLayout + c4ShortEdgeLabel).
  ```

- [ ] **Rebuild the bundle, then run the Python assertion green.**
  ```bash
  .venv/bin/python tools/build_report_template.py
  .venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_short_edge_label_helper_present -q
  # EXPECT: 1 passed
  ```

- [ ] **Determinism + full-suite gate.** Run the harness twice to confirm byte-stable
  output, then the Python suite + linters (JS helpers are pure; Python gates only):
  ```bash
  node report-template/__c4_helpers_check.js && node report-template/__c4_helpers_check.js
  .venv/bin/python -m pytest -q
  .venv/bin/python -m ruff check . && .venv/bin/python -m mypy tools/apd_gauntlet
  # EXPECT: identical harness output both runs; pytest green; ruff/mypy clean
  ```

- [ ] **Commit** (helper + harness guard + test + regenerated bundle/.source-hash):
  `feat(report): deterministic c4ShortEdgeLabel helper (strip CROSS_* prefix, first ~3 words)`.

### Task 5: Orthogonal connector router + `C4EdgeLayer` (pure helpers ported verbatim, SVG overlay that measures rendered boxes)

**Files:**

- Modify: `report-template/components.jsx` (add `c4ShortEdgeLabel`, `c4Anchors`, `c4RouteWaypoints`, `c4RoundedPath`, the `C4EdgeLayer` component; window-export them via the existing `Object.assign(window, {...})`)
- Create: `report-template/.build/test/c4_router.test.mjs` (node-run unit test of the pure router math — no DOM, no Cytoscape)
- Test (string-assertion): add `test_c4_router_helpers_present` to `tests/test_workflow_apd_gauntlet.py`

> Why this task is first in the milestone: the router is the one piece of the tiered scene that is *pure math* and can be unit-tested directly with `node` (the rest of the scene needs a DOM). Porting it verbatim from the handoff (README §204-249 / prototype `anchors`/`routeWaypoints`/`roundedPath`) and pinning it with a node test means Task 6 can wire it into JSX with confidence. `c4ShortEdgeLabel` (gap-fix 3: the short-edge-label derivation, previously prose-only) is the deterministic replacement for the prototype's hand-curated `EDGE_SHORT` map and is tested here too.

- [ ] **Step 1: Write the failing node unit test for the pure router math + short-label derivation**

The report bundle is plain ES — `components.jsx` is loaded as a `<script>` and assigns globals, it is not an ES module. To unit-test the pure helpers under `node` without a DOM, the test file re-declares the four pure functions inline (copied verbatim from the spec below) and asserts their contracts. This keeps the node test self-contained (no bundler, no jsdom) while the JS-source string-assertion (Step 4) guards that the *same* code actually ships in `components.jsx`. Create `report-template/.build/test/c4_router.test.mjs`:

```js
// report-template/.build/test/c4_router.test.mjs
// Pure unit tests for the C4 orthogonal connector router + short-label derivation.
// Run: node report-template/.build/test/c4_router.test.mjs  (no deps, no DOM).
// These four functions are ported VERBATIM from docs/superpowers/design_handoff_
// c4_architecture_view (README §204-249 / the prototype) and live in components.jsx;
// they are re-declared here so the math is testable under plain node.
import assert from "node:assert/strict";

// ── ported verbatim from components.jsx ──────────────────────────────────
function c4RouteWaypoints(s, t) {
  const dx = t.cx - s.cx, dy = t.cy - s.cy;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const sx = dx >= 0 ? s.x + s.w : s.x;
    const tx = dx >= 0 ? t.x : t.x + t.w;
    const midX = (sx + tx) / 2;
    return [{ x: sx, y: s.cy }, { x: midX, y: s.cy }, { x: midX, y: t.cy }, { x: tx, y: t.cy }];
  } else {
    const sy = dy >= 0 ? s.y + s.h : s.y;
    const ty = dy >= 0 ? t.y : t.y + t.h;
    const midY = (sy + ty) / 2;
    return [{ x: s.cx, y: sy }, { x: s.cx, y: midY }, { x: t.cx, y: midY }, { x: t.cx, y: ty }];
  }
}
function c4RoundedPath(pts, rad = 7) {
  const p = [];
  pts.forEach((q) => { const l = p[p.length - 1]; if (!l || Math.abs(l.x - q.x) > 0.5 || Math.abs(l.y - q.y) > 0.5) p.push(q); });
  if (p.length < 2) return "";
  let d = `M ${p[0].x} ${p[0].y}`;
  for (let i = 1; i < p.length - 1; i++) {
    const a = p[i - 1], b = p[i], c = p[i + 1];
    const l1 = Math.hypot(b.x - a.x, b.y - a.y), l2 = Math.hypot(c.x - b.x, c.y - b.y);
    const r = Math.min(rad, l1 / 2, l2 / 2);
    const u1 = { x: (a.x - b.x) / (l1 || 1), y: (a.y - b.y) / (l1 || 1) };
    const u2 = { x: (c.x - b.x) / (l2 || 1), y: (c.y - b.y) / (l2 || 1) };
    d += ` L ${(b.x + u1.x * r).toFixed(1)} ${(b.y + u1.y * r).toFixed(1)}`
       + ` Q ${b.x} ${b.y} ${(b.x + u2.x * r).toFixed(1)} ${(b.y + u2.y * r).toFixed(1)}`;
  }
  const last = p[p.length - 1];
  return d + ` L ${last.x} ${last.y}`;
}
function c4ShortEdgeLabel(rawLabel) {
  const raw = String(rawLabel == null ? "" : rawLabel).trim();
  if (!raw) return "";
  let s = raw.replace(/^CROSS_[A-Z0-9_]+\s*/, "");          // strip CROSS_* relation prefix
  const VERB = {
    HTTP_CALLS: "calls API", ASYNC_CALLS: "calls", CHANNEL: "messages",
    DBUS_CALLS: "controls daemon", IMPORTS: "imports", PUBLISHES: "publishes",
    SUBSCRIBES: "subscribes", READS: "reads", WRITES: "writes",
  };
  const m = raw.match(/^CROSS_([A-Z0-9_]+)/);
  if (m && (!s || s === raw) && VERB[m[1]]) return VERB[m[1]];  // pure-prefix edge -> verb
  const words = s.split(/\s+/).filter(Boolean).slice(0, 3);
  return words.join(" ") || (m && VERB[m[1]]) || raw.split(/\s+/).slice(0, 3).join(" ");
}
// ── /ported ──────────────────────────────────────────────────────────────

// horizontal-dominant pair: H-V-H, exits the right edge of s, enters the left edge of t
{
  const s = { x: 0, y: 0, w: 100, h: 40, cx: 50, cy: 20 };
  const t = { x: 400, y: 0, w: 100, h: 40, cx: 450, cy: 20 };
  const wp = c4RouteWaypoints(s, t);
  assert.equal(wp.length, 4);
  assert.deepEqual(wp[0], { x: 100, y: 20 });   // exits right edge of s at s.cy
  assert.deepEqual(wp[3], { x: 400, y: 20 });   // enters left edge of t at t.cy
  assert.equal(wp[1].x, wp[2].x);               // the vertical mid-run shares x (orthogonal)
}
// vertical-dominant pair: V-H-V, exits the bottom edge of s, enters the top edge of t
{
  const s = { x: 0, y: 0, w: 100, h: 40, cx: 50, cy: 20 };
  const t = { x: 0, y: 300, w: 100, h: 40, cx: 50, cy: 320 };
  const wp = c4RouteWaypoints(s, t);
  assert.deepEqual(wp[0], { x: 50, y: 40 });    // exits bottom edge of s at s.cx
  assert.deepEqual(wp[3], { x: 50, y: 300 });   // enters top edge of t at t.cx
  assert.equal(wp[1].y, wp[2].y);               // the horizontal mid-run shares y
}
// target to the LEFT: exit left edge of s, enter right edge of t
{
  const s = { x: 400, y: 0, w: 100, h: 40, cx: 450, cy: 20 };
  const t = { x: 0, y: 0, w: 100, h: 40, cx: 50, cy: 20 };
  const wp = c4RouteWaypoints(s, t);
  assert.deepEqual(wp[0], { x: 400, y: 20 });   // exits LEFT edge of s
  assert.deepEqual(wp[3], { x: 100, y: 20 });   // enters RIGHT edge of t
}
// roundedPath: only H/V segments + quadratic elbows; starts with M, no diagonal L between elbows
{
  const d = c4RoundedPath([{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 50, y: 50 }, { x: 100, y: 50 }], 7);
  assert.ok(d.startsWith("M 0 0"));
  assert.ok(d.includes("Q "), "elbow must use a quadratic curve");
  assert.ok(d.endsWith("L 100 50"));
}
// roundedPath: collinear / zero-length points are deduped so straight runs stay straight
{
  const d = c4RoundedPath([{ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 100, y: 0 }], 7);
  assert.equal(d, "M 0 0 L 100 0", "consecutive duplicate points must collapse");
}
// roundedPath: fewer than 2 distinct points -> empty string (no edge)
{
  assert.equal(c4RoundedPath([{ x: 5, y: 5 }], 7), "");
  assert.equal(c4RoundedPath([{ x: 5, y: 5 }, { x: 5, y: 5 }], 7), "");
}
// roundedPath is DETERMINISTIC (byte-stable) for the same input
{
  const pts = [{ x: 1, y: 2 }, { x: 30, y: 2 }, { x: 30, y: 80 }, { x: 60, y: 80 }];
  assert.equal(c4RoundedPath(pts, 7), c4RoundedPath(pts, 7));
}
// short-edge-label: strips the CROSS_* prefix and keeps ~3 words
{
  assert.equal(c4ShortEdgeLabel("CROSS_HTTP_CALLS Supervisor POSTs Core /auth/token now"), "Supervisor POSTs Core");
  assert.equal(c4ShortEdgeLabel("controls host daemon via socket"), "controls host daemon");
}
// short-edge-label: a bare CROSS_* relation with no trailing words maps to a verb
{
  assert.equal(c4ShortEdgeLabel("CROSS_DBUS_CALLS"), "controls daemon");
  assert.equal(c4ShortEdgeLabel("CROSS_HTTP_CALLS"), "calls API");
}
// short-edge-label: empty / null input -> empty string
{
  assert.equal(c4ShortEdgeLabel(""), "");
  assert.equal(c4ShortEdgeLabel(null), "");
}
// short-edge-label is deterministic
{
  assert.equal(c4ShortEdgeLabel("CROSS_CHANNEL a b c d"), c4ShortEdgeLabel("CROSS_CHANNEL a b c d"));
}

console.log("c4_router.test.mjs: all assertions passed");
```

- [ ] **Step 2: Run the node test to verify it fails**

Run: `node report-template/.build/test/c4_router.test.mjs`

Expected at this point: the test PASSES in isolation (the functions are declared inline in the test). This is intentional — the node test pins the *contract* of the math. The RED that drives the implementation is the JS-source string-assertion in Step 3, which proves the same functions are actually exported from `components.jsx` (not just living in the test). Run that now:

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k c4_router_helpers -v`

Expected: FAIL — `test_c4_router_helpers_present` asserts `c4RouteWaypoints` / `c4RoundedPath` / `c4Anchors` / `c4ShortEdgeLabel` / `C4EdgeLayer` strings in `components.jsx`, which do not exist yet (`AssertionError`).

Add the string-assertion test to `tests/test_workflow_apd_gauntlet.py` (place it in the C4 section, after `test_c4_screen_registered_in_bundle_entry`):

```python
def test_c4_router_helpers_present() -> None:
    """Task 5: the orthogonal connector router + short-edge-label + SVG edge
    layer ship in components.jsx (ported verbatim from the design handoff), and
    are window-exported so the C4 scene can consume them. GraphView is untouched
    (still Cytoscape) — these are additive, non-Cytoscape helpers."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    # the four pure helpers + the edge-layer component
    assert "function c4Anchors(" in comps
    assert "function c4RouteWaypoints(" in comps
    assert "function c4RoundedPath(" in comps
    assert "function c4ShortEdgeLabel(" in comps
    assert "function C4EdgeLayer(" in comps
    # window-exported via the existing Object.assign(window, {...})
    assert "c4Anchors" in comps and "c4RouteWaypoints" in comps and "c4RoundedPath" in comps
    assert "C4EdgeLayer" in comps and "c4ShortEdgeLabel" in comps
    # the router is the VERBATIM offsetParent-walk (zoom-invariant layout-box anchor)
    assert "e.offsetParent" in comps and "el.offsetWidth" in comps
    # orthogonal H-V-H / V-H-V branch (Math.abs(dx) >= Math.abs(dy))
    assert "Math.abs(dx) >= Math.abs(dy)" in comps
    # rounded elbow uses a quadratic curve at radius ~7
    assert "Q ${b.x} ${b.y}" in comps
    # the short label strips the CROSS_* machine prefix; full string kept for hover
    assert "CROSS_" in comps
    # GraphView (Cytoscape) is NOT removed — AttackPaths/ThreatModel still use it
    assert "function GraphView(" in comps and "window.cytoscape" in comps
```

- [ ] **Step 3: Implement the pure router helpers + short-edge-label + `C4EdgeLayer` in `components.jsx`**

Insert this block in `report-template/components.jsx` immediately *before* the final `Object.assign(window, {...})` (after `AttackPathStrip`). The four pure functions are the handoff algorithm verbatim; `C4EdgeLayer` is the SVG overlay that measures the rendered boxes and redraws on the lifecycle the handoff requires (mount, `fonts.ready`, `window` resize debounced, theme `MutationObserver`).

```jsx
// ── C4 orthogonal connector router (ported VERBATIM from the design handoff) ──
// docs/superpowers/design_handoff_c4_architecture_view/README.md §204-249 and the
// prototype's anchors()/routeWaypoints()/roundedPath(). Pure functions: no React,
// no Cytoscape, no DOM globals beyond the element handed in. Anchors are measured
// from the LAYOUT box model (offsetLeft/Top/Width/Height walked up to the stage)
// so they are correct regardless of the CSS `transform: scale()` zoom on the stage.

// 1. layout-space rect of an element relative to the (un-scaled) `stage` element.
function c4Anchors(srcEl, tgtEl, stage) {
  const r = (el) => {
    let x = 0, y = 0, e = el;
    while (e && e !== stage) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    return { x, y, w: el.offsetWidth, h: el.offsetHeight,
             cx: x + el.offsetWidth / 2, cy: y + el.offsetHeight / 2 };
  };
  return [r(srcEl), r(tgtEl)];
}

// 2. orthogonal waypoints: exit/enter on the side facing the target,
//    H-V-H when horizontally dominant, V-H-V otherwise.
function c4RouteWaypoints(s, t) {
  const dx = t.cx - s.cx, dy = t.cy - s.cy;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const sx = dx >= 0 ? s.x + s.w : s.x;
    const tx = dx >= 0 ? t.x : t.x + t.w;
    const midX = (sx + tx) / 2;
    return [{ x: sx, y: s.cy }, { x: midX, y: s.cy }, { x: midX, y: t.cy }, { x: tx, y: t.cy }];
  } else {
    const sy = dy >= 0 ? s.y + s.h : s.y;
    const ty = dy >= 0 ? t.y : t.y + t.h;
    const midY = (sy + ty) / 2;
    return [{ x: s.cx, y: sy }, { x: s.cx, y: midY }, { x: t.cx, y: midY }, { x: t.cx, y: ty }];
  }
}

// 3. polyline with rounded corners (radius ~7px). Dedupes collinear/zero-length
//    points so straight runs stay straight; returns "" for < 2 distinct points.
function c4RoundedPath(pts, rad = 7) {
  const p = [];
  pts.forEach((q) => { const l = p[p.length - 1]; if (!l || Math.abs(l.x - q.x) > 0.5 || Math.abs(l.y - q.y) > 0.5) p.push(q); });
  if (p.length < 2) return "";
  let d = `M ${p[0].x} ${p[0].y}`;
  for (let i = 1; i < p.length - 1; i++) {
    const a = p[i - 1], b = p[i], c = p[i + 1];
    const l1 = Math.hypot(b.x - a.x, b.y - a.y), l2 = Math.hypot(c.x - b.x, c.y - b.y);
    const r = Math.min(rad, l1 / 2, l2 / 2);
    const u1 = { x: (a.x - b.x) / (l1 || 1), y: (a.y - b.y) / (l1 || 1) };
    const u2 = { x: (c.x - b.x) / (l2 || 1), y: (c.y - b.y) / (l2 || 1) };
    d += ` L ${(b.x + u1.x * r).toFixed(1)} ${(b.y + u1.y * r).toFixed(1)}`
       + ` Q ${b.x} ${b.y} ${(b.x + u2.x * r).toFixed(1)} ${(b.y + u2.y * r).toFixed(1)}`;
  }
  const last = p[p.length - 1];
  return d + ` L ${last.x} ${last.y}`;
}

// Deterministic short edge label (gap-fix 3 — replaces the prototype's hand-curated
// EDGE_SHORT map). The raw edge.label is a long machine string like
// "CROSS_HTTP_CALLS Supervisor POSTs Core /auth/token ...". We strip the CROSS_*
// relation prefix and keep the first ~3 descriptive words; a bare CROSS_* relation
// with no trailing prose maps to a verb. The FULL raw string is kept for the hover
// title (never hand-curated per run). Pure + stable.
function c4ShortEdgeLabel(rawLabel) {
  const raw = String(rawLabel == null ? "" : rawLabel).trim();
  if (!raw) return "";
  const s = raw.replace(/^CROSS_[A-Z0-9_]+\s*/, "");
  const VERB = {
    HTTP_CALLS: "calls API", ASYNC_CALLS: "calls", CHANNEL: "messages",
    DBUS_CALLS: "controls daemon", IMPORTS: "imports", PUBLISHES: "publishes",
    SUBSCRIBES: "subscribes", READS: "reads", WRITES: "writes",
  };
  const m = raw.match(/^CROSS_([A-Z0-9_]+)/);
  if (m && (!s || s === raw) && VERB[m[1]]) return VERB[m[1]];
  const words = s.split(/\s+/).filter(Boolean).slice(0, 3);
  if (words.length) return words.join(" ");
  if (m && VERB[m[1]]) return VERB[m[1]];
  return raw.split(/\s+/).slice(0, 3).join(" ");
}

// ── C4 SVG edge overlay ──────────────────────────────────────────────────
// Plain React + SVG (no Cytoscape). Covers the stage absolutely, sized to the
// stage's scroll box, pointer-events:none, BEHIND the node boxes (z-index in
// .edge-layer CSS). For each grounded edge it draws: a rounded orthogonal path
// (marker-end arrow), a start port circle, and a short de-collided label with a
// paper-filled background rect (full relation string on hover). Edges whose BOTH
// endpoints are in `liveSet` render "live" (accent + thicker).
//
// Lifecycle (the handoff's redraw contract): measures rendered boxes via
// c4Anchors and redraws on mount, document.fonts.ready, a debounced window
// resize, and a theme MutationObserver (data-theme/data-sev on <body>). It reads
// the box positions by querying `[data-c4id]` inside the passed stage ref, so it
// is agnostic to how Task 6 positions the boxes (absolute backbone or flow).
function C4EdgeLayer({ stageRef, edges, liveSet, redrawKey }) {
  const [paths, setPaths] = React.useState([]);
  const [dims, setDims] = React.useState({ w: 0, h: 0 });
  const labelRefs = React.useRef({});
  const [labelBoxes, setLabelBoxes] = React.useState({});

  const live = liveSet || null;

  const measure = React.useCallback(() => {
    const stage = stageRef && stageRef.current;
    if (!stage) return;
    const out = [];
    (edges || []).forEach((e) => {
      const sEl = stage.querySelector(`[data-c4id="${e.source}"]`);
      const tEl = stage.querySelector(`[data-c4id="${e.target}"]`);
      if (!sEl || !tEl) return; // only draw edges whose BOTH endpoints are rendered
      const [s, t] = c4Anchors(sEl, tEl, stage);
      const wp = c4RouteWaypoints(s, t);
      // label anchor: midpoint of the last segment longer than 18px (fan-out spokes
      // separate by row instead of colliding); fall back to the final segment.
      let seg = null;
      for (let i = wp.length - 1; i >= 1; i--) {
        const a = wp[i - 1], b = wp[i];
        if (Math.hypot(b.x - a.x, b.y - a.y) > 18) { seg = [a, b]; break; }
      }
      if (!seg) seg = [wp[wp.length - 2], wp[wp.length - 1]];
      const horiz = Math.abs(seg[1].x - seg[0].x) >= Math.abs(seg[1].y - seg[0].y);
      const lx = (seg[0].x + seg[1].x) / 2;
      const ly = horiz ? (seg[0].y + seg[1].y) / 2 - 8 : (seg[0].y + seg[1].y) / 2;
      const isLive = !!(live && live.has(e.source) && live.has(e.target));
      out.push({
        id: e.id,
        d: c4RoundedPath(wp, 7),
        port: wp[0],
        live: isLive,
        label: c4ShortEdgeLabel(e.label),
        title: e.label || "",
        lx, ly, horiz,
      });
    });
    setPaths(out);
    setDims({ w: stage.scrollWidth, h: stage.scrollHeight });
  }, [stageRef, edges, live]);

  // Redraw on: mount + any data/zoom/drill change (redrawKey), fonts.ready,
  // debounced window resize, and a theme MutationObserver.
  React.useEffect(() => {
    measure();
    const raf = requestAnimationFrame(measure);     // after layout settles
    const t = setTimeout(measure, 220);             // after fonts/late shifts
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure).catch(() => {});
    let rT;
    const onResize = () => { clearTimeout(rT); rT = setTimeout(measure, 120); };
    window.addEventListener("resize", onResize);
    const obs = new MutationObserver(measure);
    obs.observe(document.body, { attributes: true, attributeFilter: ["data-theme", "data-sev"] });
    return () => {
      cancelAnimationFrame(raf); clearTimeout(t); clearTimeout(rT);
      window.removeEventListener("resize", onResize); obs.disconnect();
    };
  }, [measure, redrawKey]);

  // Size the label background rects from the rendered text bbox (after paint).
  React.useEffect(() => {
    const boxes = {};
    paths.forEach((p) => {
      const node = labelRefs.current[p.id];
      if (!node) return;
      try {
        const b = node.getBBox();
        boxes[p.id] = { x: b.x - 3, y: b.y - 1, width: b.width + 6, height: b.height + 2 };
      } catch (_) { /* getBBox throws on detached/zero-size text — skip */ }
    });
    setLabelBoxes(boxes);
  }, [paths]);

  return (
    <svg
      className="edge-layer"
      aria-hidden="true"
      width={dims.w}
      height={dims.h}
      viewBox={`0 0 ${dims.w} ${dims.h}`}
    >
      <defs>
        <marker id="c4-arw" viewBox="0 0 10 10" refX="8.5" refY="5"
          markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" />
        </marker>
      </defs>
      {paths.map((p) => (
        <g key={p.id} className="eg">
          <title>{p.title}</title>
          <path className={`edge${p.live ? " live" : ""}`} d={p.d} markerEnd="url(#c4-arw)" />
          <circle
            className="port"
            cx={p.port.x}
            cy={p.port.y}
            r="3"
            style={p.live ? undefined : { fill: "var(--rule-strong)" }}
          />
          {p.label && labelBoxes[p.id] && (
            <rect className="elabel-bg" rx="2" {...labelBoxes[p.id]} />
          )}
          {p.label && (
            <text
              ref={(el) => { labelRefs.current[p.id] = el; }}
              className="elabel"
              x={p.lx}
              y={p.ly}
              textAnchor="middle"
              dominantBaseline={p.horiz ? "auto" : "middle"}
            >{p.label}</text>
          )}
        </g>
      ))}
    </svg>
  );
}
```

Then extend the existing window export at the bottom of `components.jsx` (do **not** remove `GraphView`):

```jsx
Object.assign(window, {
  SeverityPill, DispositionMark, MaturityMark, CopyPill, TaxonomyTag, TagRow, ToastHost, DiagnosticsBanner,
  GraphView, AttackPathStrip,
  c4Anchors, c4RouteWaypoints, c4RoundedPath, c4ShortEdgeLabel, C4EdgeLayer,
  GOAL_LABELS, GOAL_SHORT, TIER_LABELS, TIER_GOALS,
});
```

- [ ] **Step 4: Run both tests to verify they pass**

Run: `node report-template/.build/test/c4_router.test.mjs`
Expected: `c4_router.test.mjs: all assertions passed`.

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k c4_router_helpers -v`
Expected: `1 passed`.

Confirm `GraphView` is untouched (the shared-renderer suite stays green):

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "graph_view or attack_paths or threat_model" -q`
Expected: all pass (no Cytoscape behavior changed; the additions are purely new exports).

- [ ] **Step 5: Commit**

```bash
git add report-template/components.jsx \
        report-template/.build/test/c4_router.test.mjs \
        tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): C4 orthogonal connector router + short-edge-label + SVG edge layer

Ports the design-handoff router VERBATIM into components.jsx as pure helpers
(c4Anchors offsetParent-walk zoom-invariant anchors, c4RouteWaypoints H-V-H/V-H-V
orthogonal waypoints, c4RoundedPath rounded elbows) plus a deterministic
c4ShortEdgeLabel (strips CROSS_* prefix / verb map / first ~3 words; full string
kept for hover) and a non-Cytoscape <C4EdgeLayer> SVG overlay that measures the
rendered boxes and redraws on mount/fonts.ready/resize/theme. GraphView untouched
(AttackPaths/ThreatModel keep it). Pure router math pinned by a node unit test.

Bundle rebuild lands with the scene render in the next task.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

> Note: no bundle rebuild yet — these helpers are exported but not consumed until Task 6 wires `C4TierGraph` into `C4.jsx` and `entry.jsx`. The `app.js` rebuild + `.source-hash` commit happens once in the bundle-rebuild task at the end of Milestone 7 (after both the renderer and the `C4.jsx` rewrite land), to avoid a half-wired intermediate bundle. The freshness gate is therefore satisfied by that single later rebuild commit; do not rebuild here.

---

### Task 6: The `C4TierGraph` tiered renderer + `NodeBox` + `c4BackboneLayout` (the tiered "system-map" scene)

**Files:**

- Modify: `report-template/components.jsx` (add the pure `c4BackboneLayout` helper, the `NodeBox` subcomponent, and the `C4TierGraph` component; window-export `c4BackboneLayout` + `C4TierGraph`)
- Modify: `report-template/screens.css` (add the `.archx-*` / `.tier` / `.tier-gutter` / `.nb` / `.nb__badges` / `.edge-layer` rule block, lifted from the prototype `<style>`, scoped under the C4 scene root; reuse existing `.c4-banner`/`.c4-crumbs`/`.c4-kind-chip`/`.chip`)
- Create: `report-template/.build/test/c4_backbone_layout.test.mjs` (node unit test of the deterministic layered-BFS layout — pure, no DOM)
- Test (string-assertion): add `test_c4_tier_graph_present` and `test_c4_backbone_layout_helper_present` to `tests/test_workflow_apd_gauntlet.py`

> This task delivers the four tiers (L1 actors/system/externals; L2 backbone via `c4BackboneLayout` + analyzed-shelf + infra-shelf; L3 data-driven with honest empty states; L4 code grid), the `NodeBox` in-node badge rules consuming the REAL `window.APD_DATA.c4_model` names (gap-fix 2 — never the prototype `cap`/`state`/`ff`/`me` abbreviations), the `C4EdgeLayer` overlay from Task 5, and a zoom/fit toolbar. `c4BackboneLayout` is the deterministic backbone-layout sub-spec made concrete (gap-fix 3). The `C4.jsx` render rewrite that *consumes* `C4TierGraph` (replacing `<GraphView layout="fcose">`) and the rewritten C4 string-assertion tests (`test_c4_screen_exists_and_renders_blocks`, `test_bundle_contains_c4_scene`, `test_c4_attack_path_overlay`, `test_c4_graph_node_tap_drives_drill`) land in the *next* task (the C4.jsx rewrite); this task builds the renderer they consume and TDD-pins the layout math + the renderer's source contract.

- [ ] **Step 1: Write the failing node unit test for the deterministic backbone layout**

The handoff's "Layout strategy" §267-294 specifies: partition containers into `connected` / `analyzed` / `infra`; assign `connected` to layered left→right columns (column 0 = no incoming edge; each next column = targets of the previous; break cycles by first-seen; longest-path layering), stable-sort within a column by label; everything fully deterministic. Create `report-template/.build/test/c4_backbone_layout.test.mjs`:

```js
// report-template/.build/test/c4_backbone_layout.test.mjs
// Pure unit test for the deterministic C4 backbone layout (layered BFS longest-path
// columns + analyzed/infra partitions + stable sorts). Run: node <thisfile>.
// c4BackboneLayout is re-declared inline (verbatim from components.jsx) so the
// placement math is testable under plain node, with no DOM and no React.
import assert from "node:assert/strict";

// ── ported verbatim from components.jsx ──────────────────────────────────
const COL_W = 360, ROW_H = 150;
function c4BackboneLayout(nodes, edges) {
  const containers = (nodes || []).filter((n) => n.type === "container");
  const byId = {};
  containers.forEach((n) => { byId[n.id] = n; });
  const endpoint = new Set();
  const adj = {}, indeg = {};
  containers.forEach((n) => { adj[n.id] = []; indeg[n.id] = 0; });
  (edges || []).forEach((e) => {
    if (!byId[e.source] || !byId[e.target] || e.source === e.target) return;
    endpoint.add(e.source); endpoint.add(e.target);
    adj[e.source].push(e.target); indeg[e.target] += 1;
  });
  const connectedIds = containers.filter((n) => endpoint.has(n.id)).map((n) => n.id);
  const connectedSet = new Set(connectedIds);
  const analyzed = containers
    .filter((n) => !connectedSet.has(n.id) && n.analysis_state !== "not_analyzed")
    .map((n) => n.id)
    .sort((a, b) => byId[a].label.localeCompare(byId[b].label));
  const infra = containers
    .filter((n) => !connectedSet.has(n.id) && n.analysis_state === "not_analyzed")
    .map((n) => n.id)
    .sort((a, b) => byId[a].label.localeCompare(byId[b].label));

  // longest-path column assignment over the connected subgraph; cycles broken by
  // first-seen (a back-edge never pushes a node further right).
  const col = {};
  connectedIds.forEach((id) => { col[id] = 0; });
  const order = connectedIds.slice().sort((a, b) => byId[a].label.localeCompare(byId[b].label));
  let changed = true, guard = 0;
  while (changed && guard < connectedIds.length + 2) {
    changed = false; guard += 1;
    order.forEach((u) => {
      adj[u].forEach((v) => {
        if (!connectedSet.has(v)) return;
        if (col[v] < col[u] + 1) { col[v] = col[u] + 1; changed = true; }
      });
    });
  }
  // group by column, stable-sort within a column by label, assign row index.
  const cols = {};
  connectedIds.forEach((id) => { (cols[col[id]] = cols[col[id]] || []).push(id); });
  const connected = [];
  Object.keys(cols).map(Number).sort((a, b) => a - b).forEach((c) => {
    cols[c].sort((a, b) => byId[a].label.localeCompare(byId[b].label));
    cols[c].forEach((id, row) => {
      connected.push({ id, col: c, row, x: c * COL_W, y: row * ROW_H });
    });
  });
  return { connected, analyzed, infra };
}
// ── /ported ──────────────────────────────────────────────────────────────

const N = (id, label, st) => ({ id, label, type: "container", analysis_state: st || "analyzed" });

// hub-and-spoke (the Home Assistant shape): cli -> supervisor -> core -> {os-agent, dockerd}
{
  const nodes = [
    N("a", "ha CLI"), N("s", "Supervisor"), N("c", "Core"),
    N("o", "os-agent"), N("d", "host-dockerd"),
    N("x", "Frontend"),                 // analyzed, no edge -> shelf
    N("z", ".storage", "not_analyzed"), // infra shelf
  ];
  const edges = [
    { source: "a", target: "s" }, { source: "s", target: "c" },
    { source: "c", target: "o" }, { source: "c", target: "d" },
  ];
  const { connected, analyzed, infra } = c4BackboneLayout(nodes, edges);
  const colOf = {}; connected.forEach((p) => { colOf[p.id] = p.col; });
  assert.equal(colOf.a, 0, "root of the chain is column 0");
  assert.equal(colOf.s, 1);
  assert.equal(colOf.c, 2);
  assert.equal(colOf.o, 3); assert.equal(colOf.d, 3, "both leaves land in the last column");
  // x/z are NOT in the backbone; they fall to the shelves
  assert.deepEqual(analyzed, ["x"]);
  assert.deepEqual(infra, ["z"]);
  // pixel positions derive from col/row deterministically
  const pa = connected.find((p) => p.id === "a");
  assert.equal(pa.x, 0); assert.equal(pa.y, 0);
}
// same column nodes stable-sort by label and get distinct rows
{
  const nodes = [N("h", "Hub"), N("b", "Beta"), N("a", "Alpha")];
  const edges = [{ source: "h", target: "b" }, { source: "h", target: "a" }];
  const { connected } = c4BackboneLayout(nodes, edges);
  const col1 = connected.filter((p) => p.col === 1).sort((p, q) => p.row - q.row);
  assert.deepEqual(col1.map((p) => p.id), ["a", "b"], "column members ordered by label");
  assert.deepEqual(col1.map((p) => p.row), [0, 1], "distinct rows within a column");
}
// a 2-cycle does not loop forever and does not push a node infinitely right
{
  const nodes = [N("p", "P"), N("q", "Q")];
  const edges = [{ source: "p", target: "q" }, { source: "q", target: "p" }];
  const { connected } = c4BackboneLayout(nodes, edges);
  assert.equal(connected.length, 2);
  connected.forEach((p) => assert.ok(p.col <= 1, "cycle broken by first-seen; bounded columns"));
}
// self-edges and edges to non-containers are ignored (never invented endpoints)
{
  const nodes = [N("a", "A"), N("b", "B")];
  const edges = [{ source: "a", target: "a" }, { source: "a", target: "ghost" }];
  const { connected, analyzed } = c4BackboneLayout(nodes, edges);
  assert.equal(connected.length, 0, "no real edge -> empty backbone");
  assert.deepEqual(analyzed, ["a", "b"]);
}
// DETERMINISM: identical input -> byte-identical output
{
  const nodes = [N("a", "A"), N("b", "B"), N("c", "C")];
  const edges = [{ source: "a", target: "b" }, { source: "b", target: "c" }];
  assert.equal(JSON.stringify(c4BackboneLayout(nodes, edges)),
               JSON.stringify(c4BackboneLayout(nodes, edges)));
}

console.log("c4_backbone_layout.test.mjs: all assertions passed");
```

- [ ] **Step 2: Run the tests to verify the RED**

Run: `node report-template/.build/test/c4_backbone_layout.test.mjs`
Expected: PASSES in isolation (the function is inline in the test — it pins the layout contract).

Add the source string-assertion tests to `tests/test_workflow_apd_gauntlet.py` (after `test_c4_router_helpers_present`):

```python
def test_c4_backbone_layout_helper_present() -> None:
    """Task 6: the deterministic backbone layout ships in components.jsx — layered
    BFS longest-path columns + analyzed/infra partitions + stable sorts. It is the
    data-driven replacement for the prototype's hand-curated BACKBONE position map."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function c4BackboneLayout(" in comps
    assert "c4BackboneLayout" in comps  # window-exported
    # partitions: connected / analyzed / infra
    assert "connected" in comps and "analyzed" in comps and "infra" in comps
    # deterministic: stable sort by label, no Math.random anywhere in the helper
    assert "localeCompare" in comps
    # consumes the REAL model name — analysis_state, NOT the prototype's `state`
    assert "analysis_state" in comps
    # column geometry constants
    assert "COL_W" in comps and "ROW_H" in comps


def test_c4_tier_graph_present() -> None:
    """Task 6: the C4TierGraph tiered renderer (no Cytoscape) ships in
    components.jsx with the four tiers, the NodeBox in-node badge rules consuming
    the REAL c4_model names, the C4EdgeLayer overlay, and a zoom/fit toolbar."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function C4TierGraph(" in comps
    assert "function NodeBox(" in comps
    assert "C4TierGraph" in comps  # window-exported
    # the documented prop contract
    for prop in ("model", "selectedContainer", "selectedComponent",
                 "overlayC4NodeIds", "onDrill", "onOpenFinding"):
        assert prop in comps, f"C4TierGraph must accept {prop}"
    # four tiers rendered with left-gutter labels (System context / Containers / …)
    assert "System context" in comps and "Containers" in comps
    assert "Components" in comps and "Code" in comps
    assert "tier-gutter" in comps
    # consumes the REAL model field names (gap-fix 2), NOT prototype abbreviations
    assert "capability_badge" in comps and "analysis_state" in comps
    assert "provenance" in comps and "first_finding_id" in comps
    # in-node badge rules: muted ⚑0 when badge==null, sev-high clickable when >0
    assert "not analyzed" in comps
    # the prototype abbreviations must NOT leak into production
    assert "overlay_paths" not in comps
    assert "n.ff" not in comps and "n.cap" not in comps
    # uses the Task-5 router/edge-layer (SVG, no Cytoscape) — NOT fcose
    assert "C4EdgeLayer" in comps and "c4BackboneLayout" in comps
    assert 'layout="fcose"' not in comps
    # clicking a ⚑ badge stops propagation so it deep-links without drilling
    assert "stopPropagation" in comps
    # zoom/fit toolbar
    assert "fit" in comps and "scale(" in comps

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    # the lifted tier / node-box / edge-layer rules
    for sel in (".archx-stage", ".tier", ".tier-gutter", ".nb", ".nb__badges",
                ".edge-layer", ".l2-backbone", ".shelf", ".code-grid"):
        assert sel in css, f"missing C4 tier CSS rule: {sel}"
    # not_analyzed striped/dashed treatment must be DISTINCT (never reads as clean)
    assert ".nb--na" in css
    # all colors are tokens (theme-aware) — no raw hex in the new block
    block = css[css.index(".archx-stage"):]
    assert "var(--" in block
```

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "c4_backbone_layout_helper or c4_tier_graph" -v`
Expected: FAIL — both assert strings (`c4BackboneLayout`, `C4TierGraph`, `.archx-stage`, …) absent from `components.jsx`/`screens.css`.

- [ ] **Step 3a: Implement `c4BackboneLayout`, `NodeBox`, and `C4TierGraph` in `components.jsx`**

Insert this block in `report-template/components.jsx` *after* `C4EdgeLayer` (from Task 5) and *before* the final `Object.assign(window, {...})`.

```jsx
// ── C4 deterministic backbone layout (gap-fix 3 — data-driven, replaces the ──
// prototype's hand-curated BACKBONE position map). Partitions containers into
// connected (in any edge) / analyzed (no edge, analyzed) / infra (not_analyzed),
// assigns the connected subgraph to layered left→right columns (longest-path
// layering; cycles broken by first-seen), and stable-sorts within a column by
// label. Fully deterministic (no randomness, stable sorts) per the framework's
// determinism contract. Pure: consumes the REAL c4_model node/edge shape.
const C4_COL_W = 360, C4_ROW_H = 150;
function c4BackboneLayout(nodes, edges) {
  const containers = (nodes || []).filter((n) => n.type === "container");
  const byId = {};
  containers.forEach((n) => { byId[n.id] = n; });
  const endpoint = new Set();
  const adj = {}, indeg = {};
  containers.forEach((n) => { adj[n.id] = []; indeg[n.id] = 0; });
  (edges || []).forEach((e) => {
    if (!byId[e.source] || !byId[e.target] || e.source === e.target) return;
    endpoint.add(e.source); endpoint.add(e.target);
    adj[e.source].push(e.target); indeg[e.target] += 1;
  });
  const connectedIds = containers.filter((n) => endpoint.has(n.id)).map((n) => n.id);
  const connectedSet = new Set(connectedIds);
  const lbl = (id) => (byId[id].label || id);
  const analyzed = containers
    .filter((n) => !connectedSet.has(n.id) && n.analysis_state !== "not_analyzed")
    .map((n) => n.id)
    .sort((a, b) => lbl(a).localeCompare(lbl(b)));
  const infra = containers
    .filter((n) => !connectedSet.has(n.id) && n.analysis_state === "not_analyzed")
    .map((n) => n.id)
    .sort((a, b) => lbl(a).localeCompare(lbl(b)));

  // longest-path column assignment (cycles broken by first-seen: a back-edge can
  // never push a node further right because we stop once nothing moves).
  const col = {};
  connectedIds.forEach((id) => { col[id] = 0; });
  const order = connectedIds.slice().sort((a, b) => lbl(a).localeCompare(lbl(b)));
  let changed = true, guard = 0;
  while (changed && guard < connectedIds.length + 2) {
    changed = false; guard += 1;
    order.forEach((u) => {
      adj[u].forEach((v) => {
        if (!connectedSet.has(v)) return;
        if (col[v] < col[u] + 1) { col[v] = col[u] + 1; changed = true; }
      });
    });
  }
  const cols = {};
  connectedIds.forEach((id) => { (cols[col[id]] = cols[col[id]] || []).push(id); });
  const connected = [];
  Object.keys(cols).map(Number).sort((a, b) => a - b).forEach((c) => {
    cols[c].sort((a, b) => lbl(a).localeCompare(lbl(b)));
    cols[c].forEach((id, row) => {
      connected.push({ id, col: c, row, x: c * C4_COL_W, y: row * C4_ROW_H });
    });
  });
  return { connected, analyzed, infra };
}

// ── C4 node box (in-node badge rules, REAL c4_model names — gap-fix 2) ────────
// Renders one node as a .nb box with the headline in-node badge row. Consumes the
// authentic window.APD_DATA.c4_model field names — NEVER the prototype-fixture
// abbreviations (cap/state/ff/me). Badge rules (mirror the handoff §174-189):
//   analysis_state === "not_analyzed" -> single dashed italic "not analyzed" pill, NO counts.
//   else:
//     badge > 0  -> "⚑ {badge}" sev-high, CLICKABLE -> onOpenFinding(provenance.first_finding_id)
//                   (static, non-link when no first_finding_id — never hidden).
//     badge == null (analyzed, 0) and container/component/code -> muted "⚑ 0".
//     capability_badge > 0 -> "🛡 {capability_badge}" sev-low.
// Drill: clicking a drillable box calls onDrill(n.id); clicking the ⚑ badge
// stops propagation so it deep-links WITHOUT drilling.
function NodeBox({ n, model, opts = {}, selected, onDrill, onOpenFinding }) {
  const childrenOf = model.__childrenOf;
  const byId = model.__byId;
  const codeOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "code");
  const compsOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "component");
  const na = n.analysis_state === "not_analyzed";
  const findingId = n.provenance && n.provenance.first_finding_id;
  const isExt = n.type === "external_system" || n.kind === "external_system";
  const drillable =
    (n.type === "container" && (compsOf(n.id).length > 0 || codeOf(n.id).length > 0)) ||
    (n.type === "component" && codeOf(n.id).length > 0);
  const isSelected = n.id === selected.container || n.id === selected.component;

  const cls = [
    "nb",
    n.kind ? `nb--${n.kind}` : "",
    n.type === "system" ? "nb--system" : "",
    isExt ? "nb--external" : "",
    !na && n.badge ? "nb--hot" : "",
    na ? "nb--na" : "",
    opts.mini ? "nb--mini" : "",
    opts.big ? "nb--big" : "",
    drillable ? "nb--clickable" : "",
    isSelected ? "nb--selected" : "",
  ].filter(Boolean).join(" ");

  const dim = opts.dim ? "1" : undefined;
  const kindTxt = (n.kind || "").replace(/_/g, " ");
  const showKind = n.kind && !opts.noKind;

  // text-only tooltip (never inject HTML from adopter data)
  const lvlName = ({ system: "L1 system", person: "L1 person", external_system: "L1 external",
    container: "L2 container", component: "L3 component", code: "L4 code" })[n.type] || n.type;
  let tip = `${n.label}\n${lvlName}${n.kind ? " · " + kindTxt : ""}`;
  if (na) tip += "\n⚠ not analyzed (no code anchors)";
  else {
    if (n.badge) tip += `\n⚑ ${n.badge} finding${n.badge === 1 ? "" : "s"}`;
    if (n.capability_badge) tip += `\n🛡 ${n.capability_badge} capabilit${n.capability_badge === 1 ? "y" : "ies"}`;
  }
  if (drillable) {
    const c = compsOf(n.id).length, k = codeOf(n.id).length;
    tip += c ? `\n↳ click to drill (${c} component${c === 1 ? "" : "s"})`
             : `\n↳ click to drill (${k} code)`;
  }

  const onClick = drillable ? (e) => { if (e.target.closest(".bdg--find")) return; onDrill(n.id); } : undefined;

  // badges
  const badges = [];
  if (na) {
    badges.push(
      <span key="na" className="bdg bdg--na"
        title="No code anchors — analysis_state: not_analyzed (not '0 = clean')">not analyzed</span>
    );
  } else {
    if (n.badge != null && n.badge > 0) {
      const canLink = findingId && typeof onOpenFinding === "function";
      badges.push(
        <span
          key="find"
          className="bdg bdg--find"
          role={canLink ? "button" : undefined}
          title={`${n.badge} finding${n.badge === 1 ? "" : "s"} on this element${canLink ? " — open in Findings" : ""}`}
          style={{ cursor: canLink ? "pointer" : "default" }}
          onClick={canLink ? (e) => { e.stopPropagation(); onOpenFinding(findingId); } : undefined}
        >⚑ {n.badge}</span>
      );
    } else if (n.type === "container" || n.type === "component" || n.type === "code") {
      badges.push(
        <span key="clean" className="bdg bdg--clean" title="Analyzed · zero findings">⚑ 0</span>
      );
    }
    if (n.capability_badge != null && n.capability_badge > 0) {
      badges.push(
        <span key="cap" className="bdg bdg--cap"
          title={`${n.capability_badge} confirmed capabilit${n.capability_badge === 1 ? "y" : "ies"}`}>🛡 {n.capability_badge}</span>
      );
    }
  }

  return (
    <div
      className={cls}
      data-c4id={n.id}
      data-dim={dim}
      title={tip}
      style={opts.style}
      onClick={onClick}
    >
      <div className="nb__head">
        {showKind && <span className="nb__kind">{kindTxt}</span>}
      </div>
      <div className="nb__name">{n.label}</div>
      {n.type === "system" && <div className="nb__sub">software system</div>}
      {!opts.noBadges && badges.length > 0 && <div className="nb__badges">{badges}</div>}
    </div>
  );
}

// ── C4 tiered "system-map" scene (the fcose force-graph replacement) ─────────
// Four stacked tiers with left-gutter labels:
//   L1 System context — Actors (person) | system (center) | External systems
//   L2 Containers      — backbone (c4BackboneLayout, absolute-positioned + the
//                        C4EdgeLayer SVG overlay) + "analyzed · no traced relation"
//                        shelf + "infrastructure · not analyzed" shelf
//   L3 Components      — data-driven; honest empty/blocked states
//   L4 Code            — the active parent's code grid
// Plus a zoom/fit toolbar (transform: scale on the stage inner). No Cytoscape.
// overlayC4NodeIds dims non-members and renders the induced backbone edges "live".
function C4TierGraph({ model, selectedContainer, selectedComponent, overlayC4NodeIds, onDrill, onOpenFinding }) {
  const nodes = (model && model.nodes) || [];
  const edges = (model && model.edges) || [];

  const byId = React.useMemo(() => {
    const m = {}; nodes.forEach((n) => { m[n.id] = n; }); return m;
  }, [model]);
  const childrenOf = React.useMemo(() => {
    const m = {};
    nodes.forEach((n) => { if (n.parent) (m[n.parent] = m[n.parent] || []).push(n.id); });
    return m;
  }, [model]);
  // hand byId/childrenOf to NodeBox without prop-drilling each lookup
  const mdl = React.useMemo(() => Object.assign({}, model, { __byId: byId, __childrenOf: childrenOf }), [model, byId, childrenOf]);

  const codeOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "code");
  const compsOf = (id) => (childrenOf[id] || []).map((c) => byId[c]).filter((x) => x && x.type === "component");

  const layout = React.useMemo(() => c4BackboneLayout(nodes, edges), [model]);

  const stageRef = React.useRef(null);
  const [zoom, setZoom] = React.useState(1);
  const selected = { container: selectedContainer, component: selectedComponent };
  const ovSet = (overlayC4NodeIds && overlayC4NodeIds.length) ? new Set(overlayC4NodeIds) : null;
  // redrawKey forces C4EdgeLayer to re-measure when the visible layout changes.
  const redrawKey = `${selectedContainer || ""}|${selectedComponent || ""}|${zoom}|${(overlayC4NodeIds || []).join(",")}`;

  const persons = nodes.filter((n) => n.type === "person");
  const exts = nodes.filter((n) => n.type === "external_system");
  const sys = nodes.find((n) => n.type === "system");
  const containers = nodes.filter((n) => n.type === "container");

  const box = (n, opts) => (
    <NodeBox key={n.id} n={n} model={mdl} opts={Object.assign({ dim: ovSet ? !ovSet.has(n.id) : false }, opts)}
      selected={selected} onDrill={onDrill} onOpenFinding={onOpenFinding} />
  );

  // backbone edges visible = grounded edges whose endpoints are both backbone nodes
  const backboneIds = new Set(layout.connected.map((p) => p.id));
  const backboneEdges = edges.filter((e) => backboneIds.has(e.source) && backboneIds.has(e.target));

  // ── L3 / L4 active-parent resolution ──
  const compsOfSel = selectedContainer ? compsOf(selectedContainer) : [];
  const activeParentId = selectedComponent
    ? selectedComponent
    : (selectedContainer && compsOfSel.length === 0 ? selectedContainer : null);

  // zoom/fit
  const zIn = () => setZoom((z) => Math.min(2, +(z + 0.15).toFixed(2)));
  const zOut = () => setZoom((z) => Math.max(0.4, +(z - 0.15).toFixed(2)));
  const fit = () => {
    const stage = stageRef.current; if (!stage) return;
    const wrap = stage.parentElement; if (!wrap) return;
    const avail = wrap.clientWidth - 4;
    setZoom(Math.min(1, +(avail / stage.scrollWidth).toFixed(3)));
  };

  return (
    <div className="archx-stage-wrap">
      <div className="archx-toolbar">
        <button type="button" onClick={zOut} title="Zoom out">−</button>
        <span className="zoom-level">{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={zIn} title="Zoom in">+</button>
        <button type="button" onClick={fit} title="Fit">fit</button>
      </div>

      <div className="archx-stage" ref={stageRef} style={{ transform: `scale(${zoom})`, transformOrigin: "0 0" }}>
        <C4EdgeLayer stageRef={stageRef} edges={backboneEdges} liveSet={ovSet} redrawKey={redrawKey} />

        {/* L1 — System context */}
        <section className="tier" data-level="system">
          <div className="tier-gutter">
            <div className="t-l1">L1</div>
            <div className="t-l2">System context</div>
            <div className="t-l3">person · system · external</div>
          </div>
          <div className="tier-body">
            <div className="l1-body">
              <div className="l1-group">
                <div className="l1-group__h">Actors · {persons.length}</div>
                <div className="l1-grid">
                  {persons.map((p) => box(p, { mini: true, noKind: true }))}
                </div>
              </div>
              <div className="l1-center">{sys && box(sys, { big: true })}</div>
              <div className="l1-group">
                <div className="l1-group__h" style={{ textAlign: "right" }}>External systems · {exts.length}</div>
                <div className="l1-grid l1-grid--ext">
                  {exts.map((x) => box(x, { mini: true, noKind: true }))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* L2 — Containers */}
        <section className="tier" data-level="container">
          <div className="tier-gutter">
            <div className="t-l1">L2</div>
            <div className="t-l2">Containers</div>
            <div className="t-l3">{containers.length} containers</div>
          </div>
          <div className="tier-body">
            <div className="l2-cap">Traced relationships</div>
            <div className="l2-backbone" style={{ minHeight: (Math.max(1, ...layout.connected.map((p) => p.row + 1)) * C4_ROW_H) + "px" }}>
              {layout.connected.map((p) => (
                <div key={p.id} className="nb-pos" style={{ position: "absolute", left: p.x + "px", top: p.y + "px" }}>
                  {byId[p.id] && box(byId[p.id])}
                </div>
              ))}
            </div>
            <div className="l2-cap">Analyzed · no traced relation</div>
            <div className="shelf">
              {layout.analyzed.map((id) => byId[id] && box(byId[id]))}
            </div>
            {layout.infra.length > 0 && <>
              <div className="l2-cap">Infrastructure · not analyzed</div>
              <div className="shelf shelf--infra">
                {layout.infra.map((id) => byId[id] && box(byId[id], { noKind: true }))}
              </div>
            </>}
          </div>
        </section>

        {/* L3 — Components (data-driven; honest empty states) */}
        <section className="tier" data-level="component">
          <div className="tier-gutter">
            <div className="t-l1">L3</div>
            <div className="t-l2">Components</div>
            <div className="t-l3">{!selectedContainer ? "—" : `${byId[selectedContainer].label} · ${compsOfSel.length || "none"}`}</div>
          </div>
          <div className="tier-body">
            {!selectedContainer ? (
              <div className="code-hint">L3 components appear here when a run grounds them via <code>c4-recon.components[]</code>. They are <b>blocked by default</b>, so most runs drill <b>L2 → L4</b>. Select a container above.</div>
            ) : compsOfSel.length === 0 ? (
              <div className="code-hint">No grounded L3 components under <b>{byId[selectedContainer].label}</b> — L3 is blocked unless an artifact groups symbols. This container renders <b>L2 → L4</b> (code parents directly to the container).</div>
            ) : (
              <div className="code-wrap">
                <div className="code-parent">{box(byId[selectedContainer])}</div>
                <div className="code-grid">{compsOfSel.map((c) => box(c))}</div>
              </div>
            )}
          </div>
        </section>

        {/* L4 — Code */}
        <section className="tier" data-level="code">
          <div className="tier-gutter">
            <div className="t-l1">L4</div>
            <div className="t-l2">Code</div>
            <div className="t-l3">{activeParentId ? `${byId[activeParentId].label} · ${codeOf(activeParentId).length}` : "select a container"}</div>
          </div>
          <div className="tier-body">
            {!selectedContainer ? (
              <div className="code-hint">Select a container (or an L3 component, when present) to expand its grounded L4 code elements — each with its own ⚑ finding and 🛡 capability counts.</div>
            ) : compsOfSel.length > 0 && !selectedComponent ? (
              <div className="code-hint">Select an L3 component above to expand its code elements.</div>
            ) : (
              <div className="code-wrap">
                <div className="code-parent">{box(byId[activeParentId])}</div>
                <div className="code-grid">{codeOf(activeParentId).map((c) => box(c))}</div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
```

Extend the window export (final `Object.assign` in `components.jsx`) to add the two new symbols:

```jsx
Object.assign(window, {
  SeverityPill, DispositionMark, MaturityMark, CopyPill, TaxonomyTag, TagRow, ToastHost, DiagnosticsBanner,
  GraphView, AttackPathStrip,
  c4Anchors, c4RouteWaypoints, c4RoundedPath, c4ShortEdgeLabel, C4EdgeLayer,
  c4BackboneLayout, NodeBox, C4TierGraph,
  GOAL_LABELS, GOAL_SHORT, TIER_LABELS, TIER_GOALS,
});
```

- [ ] **Step 3b: Add the `.archx-*` / tier / node-box / edge-layer CSS to `screens.css`**

Append this block to `report-template/screens.css` immediately after the existing C4 overlay rules (after `.c4-overlay-strip__arrow`, ~line 1431). It is lifted from the prototype `<style>` block (the `.archx` / `.tier` / `.nb` / `.edge-layer` rules), scoped under `.c4-scene` so it cannot leak into other screens, and uses only design tokens (theme-aware). The header chrome rules (`.archx-eyebrow`/`.archx-title`/`.archx-lede`/`.archx-banner`/`.archx-controls`/`.archx-crumbs`/`.chip`/`.archx-overlay`/`.archx-legend`/`.archx-tip`/`.archx-notes`/`.archx-list*`) are intentionally **omitted** — the C4 scene reuses the existing `.c4-banner`/`.c4-crumbs`/`.c4-kind-chip`/`.chip` and the kept `.c4-node-list` instead.

```css
/* ── C4 tiered scene (system-map) — lifted from the design-handoff prototype ──
   <style> block (.archx/.tier/.nb/.edge-layer), scoped under .c4-scene. Reuses
   the existing .c4-banner/.c4-crumbs/.c4-kind-chip/.chip rules above. All colors
   are tokens so light/dark/paper themes recolor live. */

.c4-scene .archx-stage-wrap {
  position: relative;
  border: 1px solid var(--rule);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 1px 1px, color-mix(in srgb, var(--ink-3) 18%, transparent) 1px, transparent 0);
  background-size: 22px 22px;
  background-color: var(--paper);
  overflow: auto;
  box-shadow: var(--shadow-md);
}
.c4-scene .archx-toolbar {
  position: absolute; top: var(--space-2); right: var(--space-2);
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 6px; background: var(--paper);
  border: 1px solid var(--rule); border-radius: 6px;
  box-shadow: var(--shadow-sm); z-index: 5;
  font-family: var(--font-mono); font-size: var(--text-xs);
}
.c4-scene .archx-toolbar button {
  appearance: none; background: transparent; border: none; color: var(--ink);
  cursor: pointer; padding: 2px 9px; border-radius: 3px; font: inherit; line-height: 1;
}
.c4-scene .archx-toolbar button:hover { background: var(--paper-2); }
.c4-scene .archx-toolbar .zoom-level { min-width: 42px; text-align: center; color: var(--ink-3); }

.c4-scene .archx-stage {
  position: relative;
  transform-origin: 0 0;
  width: 1120px;
  padding: var(--space-5) var(--space-5) var(--space-5) 0;
}

/* tiers */
.c4-scene .tier { position: relative; display: grid; grid-template-columns: 132px 1fr; }
.c4-scene .tier + .tier { margin-top: var(--space-3); }
.c4-scene .tier-gutter {
  position: relative;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-4);
  display: flex; flex-direction: column; gap: 2px; justify-content: center;
  border-right: 1px dashed var(--rule-strong);
}
.c4-scene .tier-gutter .t-l1 { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.12em; color: var(--accent); font-weight: 600; }
.c4-scene .tier-gutter .t-l2 { font-family: var(--font-display); font-size: 15px; color: var(--ink); line-height: 1.15; }
.c4-scene .tier-gutter .t-l3 { font-family: var(--font-mono); font-size: 9.5px; color: var(--ink-3); }
.c4-scene .tier-body { padding: var(--space-3) 0 var(--space-3) var(--space-4); position: relative; }

/* node boxes */
.c4-scene .nb {
  position: relative;
  box-sizing: border-box;
  background: var(--paper);
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-md);
  padding: 8px 10px 7px;
  display: flex; flex-direction: column; gap: 5px;
  box-shadow: var(--shadow-sm);
  cursor: default;
  transition: border-color .14s, box-shadow .14s, transform .14s;
}
.c4-scene .nb__head { display: flex; align-items: center; gap: 6px; }
.c4-scene .nb__head:empty { display: none; }
.c4-scene .nb__kind {
  font-family: var(--font-mono); font-size: 8.5px; letter-spacing: 0.04em;
  text-transform: uppercase; padding: 1px 5px; border-radius: 3px;
  background: var(--paper-2); color: var(--ink-3); border: 1px solid var(--rule);
  white-space: nowrap;
}
.c4-scene .nb__name {
  font-family: var(--font-body); font-weight: 600; font-size: 12.5px; color: var(--ink);
  line-height: 1.25; min-width: 0; overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.c4-scene .nb__sub { color: var(--ink-3); font-size: 10.5px; font-family: var(--font-mono); }
.c4-scene .nb__badges { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.c4-scene .bdg {
  font-family: var(--font-mono); font-size: 10px; line-height: 1.4;
  padding: 1px 6px; border-radius: 3px; white-space: nowrap;
  border: 1px solid var(--rule); background: var(--paper-2); color: var(--ink-3);
  display: inline-flex; align-items: center; gap: 3px;
}
.c4-scene .bdg--find {
  background: color-mix(in srgb, var(--sev-high) 14%, var(--paper));
  color: var(--sev-high); border-color: color-mix(in srgb, var(--sev-high) 55%, var(--rule));
}
.c4-scene .bdg--find[role="button"] { cursor: pointer; }
.c4-scene .bdg--find[role="button"]:hover { text-decoration: underline; }
.c4-scene .bdg--cap {
  background: color-mix(in srgb, var(--sev-low) 16%, var(--paper));
  color: var(--sev-low); border-color: color-mix(in srgb, var(--sev-low) 55%, var(--rule));
}
.c4-scene .bdg--clean { color: var(--ink-3); }
.c4-scene .bdg--na { color: var(--ink-3); border-style: dashed; border-color: var(--ink-3); font-style: italic; }

/* kind cues */
.c4-scene .nb--data_store { border-radius: var(--radius-md) var(--radius-md) 14px 14px; }
.c4-scene .nb--data_store .nb__kind { color: var(--accent); border-color: var(--accent); }
.c4-scene .nb--external,
.c4-scene .nb--external_dependency,
.c4-scene .nb--external_system { border-style: dashed; background: color-mix(in srgb, var(--paper-2) 60%, var(--paper)); }
.c4-scene .nb--external_party { border-style: dashed; }

.c4-scene .nb--hot { border-left: 3px solid color-mix(in srgb, var(--sev-high) 60%, var(--rule-strong)); }
.c4-scene .nb--clickable { cursor: pointer; }
.c4-scene .nb--clickable:hover { border-color: var(--accent); box-shadow: var(--shadow-md); transform: translateY(-1px); }
.c4-scene .nb--selected { border-color: var(--accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 35%, transparent), var(--shadow-md); }

/* not analyzed = striped + muted (never reads as clean) */
.c4-scene .nb--na {
  background: repeating-linear-gradient(135deg, var(--paper-2), var(--paper-2) 6px, var(--paper) 6px, var(--paper) 12px);
  border-style: dashed; border-color: var(--ink-3); opacity: 0.8; box-shadow: none;
}

/* system node (L1 centre) */
.c4-scene .nb--system { background: var(--accent); border-color: var(--accent); box-shadow: var(--shadow-md); }
.c4-scene .nb--system .nb__name { color: var(--bg); font-size: 14px; }
.c4-scene .nb--system .nb__kind { background: color-mix(in srgb, var(--bg) 20%, transparent); color: var(--bg); border-color: transparent; }
.c4-scene .nb--system .nb__sub { color: color-mix(in srgb, var(--bg) 85%, var(--accent)); }

/* L1 layout */
.c4-scene .l1-body { display: grid; grid-template-columns: 1fr auto 1fr; gap: var(--space-4); align-items: center; }
.c4-scene .l1-group { display: flex; flex-direction: column; gap: 5px; }
.c4-scene .l1-group__h { font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-3); margin-bottom: 2px; }
.c4-scene .l1-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.c4-scene .l1-grid--ext { grid-template-columns: 1fr; }
.c4-scene .nb--mini { padding: 5px 8px; gap: 2px; }
.c4-scene .nb--mini .nb__name { font-size: 11px; font-weight: 500; -webkit-line-clamp: 2; }
.c4-scene .l1-center { display: flex; justify-content: center; }
.c4-scene .nb--system.nb--big { min-width: 188px; padding: 12px 16px; text-align: left; }

/* L2 backbone canvas */
.c4-scene .l2-backbone { position: relative; }
.c4-scene .l2-backbone .nb-pos { position: absolute; }
.c4-scene .l2-backbone .nb { width: 162px; }
.c4-scene .l2-cap {
  font-family: var(--font-mono); font-size: 9px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-3); margin: var(--space-3) 0 var(--space-2);
  display: flex; align-items: center; gap: var(--space-2);
}
.c4-scene .l2-cap::after { content: ""; flex: 1; height: 1px; background: var(--rule); }

/* shelves */
.c4-scene .shelf { display: flex; flex-wrap: wrap; gap: 6px; }
.c4-scene .shelf .nb { width: auto; max-width: 220px; min-width: 132px; flex: 0 1 auto; }
.c4-scene .shelf--infra .nb { min-width: 0; }
.c4-scene .shelf .nb__name { -webkit-line-clamp: 1; }

/* L4 code tier */
.c4-scene .code-hint {
  font-family: var(--font-mono); font-size: var(--text-xs); color: var(--ink-3);
  padding: var(--space-4) var(--space-4); border: 1px dashed var(--rule-strong);
  border-radius: var(--radius-md); background: color-mix(in srgb, var(--paper-2) 50%, transparent);
}
.c4-scene .code-wrap { position: relative; }
.c4-scene .code-parent { margin-bottom: var(--space-3); }
.c4-scene .code-parent .nb { width: 220px; }
.c4-scene .code-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 7px; }
.c4-scene .code-grid .nb__name { font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; -webkit-line-clamp: 2; }

/* edges (SVG overlay) */
.c4-scene .edge-layer { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; z-index: 1; }
.c4-scene .edge-layer path.edge { fill: none; stroke: var(--rule-strong); stroke-width: 1.6; stroke-linejoin: round; stroke-linecap: round; }
.c4-scene .edge-layer path.edge.live { stroke: var(--accent); stroke-width: 2; }
.c4-scene .edge-layer .port { fill: var(--accent); }
.c4-scene .edge-layer marker path { fill: var(--accent); }
.c4-scene .edge-layer .elabel {
  font-family: var(--font-mono); font-size: 10px; font-weight: 500; fill: var(--accent);
}
.c4-scene .edge-layer .elabel-bg { fill: var(--paper); opacity: 0.92; }
.c4-scene .nb[data-dim="1"] { opacity: 0.32; }
```

- [ ] **Step 4: Run both tests to verify they pass**

Run: `node report-template/.build/test/c4_backbone_layout.test.mjs`
Expected: `c4_backbone_layout.test.mjs: all assertions passed`.

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "c4_backbone_layout_helper or c4_tier_graph or c4_router_helpers" -v`
Expected: `3 passed`.

Confirm `GraphView` / shared-renderer screens are unaffected, and the prototype demo affordance was NOT ported:

Run: `.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "graph_view or attack_paths or threat_model" -q`
Expected: all pass.

Run: `git grep -n "L3 demo\|synthetic\|buildDemoComponents\|demoOn\|toggleDemo" report-template/components.jsx`
Expected: NO matches (the prototype's "L3 demo (synthetic)" toggle is intentionally not shipped, per the acceptance checklist).

> Note: the `C4.jsx` render is still wired to `<GraphView layout="fcose">` at this point — `C4TierGraph` is built and exported but not yet consumed, so the four to-be-rewritten C4 string-assertion tests (`test_c4_screen_exists_and_renders_blocks`, `test_bundle_contains_c4_scene`, `test_c4_attack_path_overlay`, `test_c4_graph_node_tap_drives_drill`) still assert the OLD Cytoscape strings and stay green. They are rewritten in the next task (the `C4.jsx` rewrite), which also wires `C4TierGraph` in, imports it via `entry.jsx`, and triggers the single bundle rebuild + `.source-hash` commit that satisfies the freshness gate. Do not rebuild the bundle here — `components.jsx` additions are inert until consumed, and a half-wired bundle (renderer present, scene still on Cytoscape) is avoided by deferring the rebuild to the consume step.

- [ ] **Step 5: Commit**

```bash
git add report-template/components.jsx \
        report-template/screens.css \
        report-template/.build/test/c4_backbone_layout.test.mjs \
        tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): C4TierGraph tiered system-map renderer + NodeBox + c4BackboneLayout

Adds the non-Cytoscape tiered C4 scene to components.jsx: a deterministic
layered-BFS backbone layout (c4BackboneLayout — connected columns + analyzed/infra
shelves, stable-sorted, replaces the prototype's hand-curated position map), a
NodeBox with the in-node badge rules consuming the REAL c4_model field names
(badge null->muted ⚑0, badge>0->sev-high deep-link via provenance.first_finding_id,
capability_badge->🛡, analysis_state not_analyzed->dashed pill; ⚑ click
stopPropagation so it deep-links without drilling), four tiers (L1 actors/system/
externals · L2 backbone+shelves · L3 data-driven honest empty states · L4 code
grid), the Task-5 C4EdgeLayer SVG overlay (live edges for the attack-path overlay),
and a zoom/fit toolbar. Lifts the .archx/.tier/.nb/.edge-layer CSS into screens.css
scoped under .c4-scene (token-driven, theme-aware). The 'L3 demo (synthetic)'
prototype toggle is intentionally NOT shipped. Layout math pinned by a node test.

C4.jsx still consumes GraphView until the next (C4.jsx-rewrite) task wires
C4TierGraph in and rebuilds the bundle. GraphView untouched.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

These two tasks append to a new `## Milestone 7` section of `docs/superpowers/plans/2026-06-13-c4-architecture-view.md`. Notes for whoever stitches them in: Milestone 7 (the tiered-redesign) opens with the four gap-fixes (test-rewrite-first; real-name data fidelity; concrete sub-specs; bundle/freshness/audit + acceptance checklist), and its remaining tasks are Task 1 (rewrite the four hard C4 tests to assert the tiered scene before coding — the TDD-first gap-fix), Tasks 2-4 (fixture regeneration + any data-fidelity helpers), then **Task 5 + Task 6 above** (router/edge-layer, then the renderer), followed by the `C4.jsx` render-rewrite task (consumes `C4TierGraph`, removes the `GraphView` subgraph/`overlayHighlight` useMemos and the `<GraphView layout="fcose">` render, adds `import "../components.jsx"` symbols, keeps the NodeRow code-elements list) and the single bundle-rebuild task (`.venv/bin/python tools/build_report_template.py` → commit `report-template/app.js` + `.source-hash` + the packaged `tools/apd_gauntlet/data/report-template/`, satisfying the triple freshness enforcement). The bundle rebuild is deliberately deferred out of Tasks 5/6 because the added `components.jsx` symbols are inert until `C4.jsx` consumes them; rebuilding once after the consume step avoids shipping a half-wired bundle and is what flips the four rewritten tests (`test_c4_screen_exists_and_renders_blocks`, `test_bundle_contains_c4_scene`, `test_c4_attack_path_overlay`, `test_c4_graph_node_tap_drives_drill`) green.

### Task 7: Wire `C4.jsx` to the tiered renderer (`<C4TierGraph/>`), drop GraphView

**Files:**

- Modify: `report-template/screens/C4.jsx` (rewrite the render; keep the drill machine, overlay RESOLUTION useMemo, NodeRow, banner, breadcrumb, kind-chip)
- Test: `tests/test_workflow_apd_gauntlet.py` (REWRITE `test_c4_screen_exists_and_renders_blocks`, `test_bundle_contains_c4_scene`, `test_c4_graph_node_tap_drives_drill`)

- [ ] **Step 1: Rewrite the failing source-assertion tests (TDD — define the tiered scene first)**

These three tests currently assert the **Cytoscape strings being removed** (`GraphView`, `layout="fcose"`, `compound`, `onNodeTap`-to-GraphView). Rewrite them in `tests/test_workflow_apd_gauntlet.py` to assert the **tiered** scene. (Leave `test_c4_screen_surfaces_node_kind_chip`, `test_c4_overlay_join_uses_from_id_to_id`, `test_c4_tab_is_conditional_and_routed`, `test_c4_screen_registered_in_bundle_entry`, `test_c4_scene_styles_present`, and the shared-`GraphView` tests at 644–720 **as-is** — they stay green.)

Replace `test_c4_screen_exists_and_renders_blocks` (≈ line 727):

```python
def test_c4_screen_exists_and_renders_blocks() -> None:
    """The C4 scene renders the grounded model as a TIERED system-map
    (System → Container → Component → Code) via <C4TierGraph/>, NOT the
    Cytoscape fcose force-graph. The honest banner + drill machine stay."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # present-gate + honest banner (kept)
    assert "c4.present" in src or "c4 || !c4.present" in src
    assert "c4-banner" in src
    assert "not_analyzed" in src and "unlocalized" in src
    # NEW: the tiered renderer replaces GraphView. C4 no longer imports/uses
    # GraphView or any Cytoscape layout — those moved out of the C4 path.
    assert "C4TierGraph" in src
    assert "GraphView" not in src, "C4 must not reference the Cytoscape GraphView"
    assert 'layout="fcose"' not in src and 'layout="dagre"' not in src
    assert "compound={true}" not in src
    # the drill machine is preserved (now passed to C4TierGraph as onDrill)
    assert "selectedContainer" in src and "selectedComponent" in src
    assert "onDrill" in src
    # the model + resolved overlay membership are fed to the tiered renderer
    assert "model={" in src
    assert "overlayC4NodeIds" in src
    # the code-elements list (NodeRow) is kept beneath the scene
    assert "NodeRow" in src and "onOpenFinding" in src
```

Replace `test_bundle_contains_c4_scene` (≈ line 958):

```python
def test_bundle_contains_c4_scene() -> None:
    """The compiled bundle ships the tiered C4 scene + its deterministic
    backbone layout helper, and NOT a C4-bound fcose force-graph."""
    app_js = (REPO / "report-template" / "app.js").read_text(encoding="utf-8")
    # the tiered renderer + the deterministic backbone layout helper are bundled
    assert "C4TierGraph" in app_js
    assert "c4BackboneLayout" in app_js
    assert "c4ShortEdgeLabel" in app_js
    # an SVG edge-layer is emitted by the C4 scene (orthogonal connectors)
    assert "edge-layer" in app_js
    # GraphView still ships (AttackPaths/ThreatModel use it) but fcose is no
    # longer wired from the C4 scene — assert the C4 source has neither.
    c4 = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    assert 'layout="fcose"' not in c4
    assert "GraphView" not in c4
```

Replace `test_c4_graph_node_tap_drives_drill` (≈ line 1066):

```python
def test_c4_graph_node_tap_drives_drill() -> None:
    """A click on a tiered node box drills exactly like the NodeRow buttons,
    via the onDrill reducer passed into C4TierGraph (no GraphView onNodeTap)."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # the reducer is defined and passed to C4TierGraph as onDrill
    assert "onDrill" in src
    assert "C4TierGraph" in src
    assert "setSelectedContainer" in src and "setSelectedComponent" in src
    # container -> select container; component -> select component (parent kept)
    assert 'n.type === "container"' in src
    assert 'n.type === "component"' in src
    # the drill is wired through C4TierGraph's onDrill prop, NOT GraphView
    assert "onDrill={" in src
    assert "onNodeTap=" not in src, "C4 must not pass GraphView's onNodeTap"
```

- [ ] **Step 2: Run the tests to verify they fail (red)**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_screen_exists_and_renders_blocks tests/test_workflow_apd_gauntlet.py::test_bundle_contains_c4_scene tests/test_workflow_apd_gauntlet.py::test_c4_graph_node_tap_drives_drill -v
```

Expected: all three FAIL. `test_c4_screen_exists_and_renders_blocks` fails on `assert "C4TierGraph" in src` (still references `GraphView`); `test_bundle_contains_c4_scene` fails on `assert "C4TierGraph" in app_js` (bundle not yet rebuilt for the swap); `test_c4_graph_node_tap_drives_drill` fails on `assert "onNodeTap=" not in src` (the current render passes `onNodeTap={onNodeTap}` to `<GraphView>`).

- [ ] **Step 3: Rewrite the `C4.jsx` render (minimal impl — keep the machine, swap the renderer)**

**3a. Remove the two GraphView-only `useMemo`s.** Delete the `overlayHighlight` block (`C4.jsx:122-132`) and the `graph` subgraph block (`C4.jsx:134-187`) verbatim. Both existed solely to feed `GraphView`:

```jsx
  // ── DELETE: GraphView synthetic-path highlight (C4.jsx:122-132) ──
  const overlayHighlight = React.useMemo(() => {
    if (!overlay.c4NodeIds.length) return null;
    const idset = new Set(overlay.c4NodeIds);
    const edgeIds = allEdges
      .filter((e) => idset.has(e.source) && idset.has(e.target))
      .map((e) => e.id);
    return [{ id: "__overlay__", edgeIds, nodeIds: overlay.c4NodeIds }];
  }, [overlay, c4]);

  // ── DELETE: the GraphView visible-subgraph builder (C4.jsx:134-187) ──
  const graph = React.useMemo(() => {
    const isTop = (lvl) => lvl === "system" || lvl === "person" || lvl === "external_system";
    let keep = new Set();
    // … (the full keep-set + nodes/edges mapping block) …
    return { nodes, edges };
  }, [c4, selectedContainer, selectedComponent]);
```

> The induced-edge expansion that `overlayHighlight` did (filter `allEdges` to both-endpoints-in-`overlay.c4NodeIds`) is **not lost** — Task 8 moves it inside `C4EdgeLayer`, which already iterates `model.edges` to draw connectors and can mark the induced subset "live" directly from `overlayC4NodeIds`. The visible-subgraph `keep`-set logic is **superseded** by `c4BackboneLayout` + the tier partition inside `C4TierGraph` (M7 Tasks 1–6), which render every container/code node by tier and reveal drill children by `selectedContainer`/`selectedComponent` — no pre-filtered subgraph prop needed.

**3b. Rename the reducer `onNodeTap` → `onDrill`** (the contract's prop name; identical body). At `C4.jsx:194-201`:

```jsx
  // Drill reducer — a tiered node-box click drills exactly like the NodeRow
  // buttons. The c4 node id is the DOM box's data-id. Null-safe: a tap on a
  // node with no drill target (code/system/person/external_system) is a NO-OP
  // and never resets the view to nowhere. Passed to C4TierGraph as onDrill and
  // reused by NodeRow.onClick below.
  const onDrill = React.useCallback((nodeId) => {
    if (!nodeId) return;
    const n = nodeById[nodeId];
    if (!n) return;
    if (n.type === "container") { setSelectedContainer(nodeId); setSelectedComponent(null); }
    else if (n.type === "component") { setSelectedContainer(n.parent || selectedContainer); setSelectedComponent(nodeId); }
    // code/system/person/external_system taps do not change the drill level (no-op).
  }, [nodeById, selectedContainer]);
```

Then update the one in-component caller in `NodeRow` (`C4.jsx:222`) from `onClick={() => onNodeTap(n.id)}` to `onClick={() => onDrill(n.id)}`.

**3c. Replace the `<section className="c4-scene__graph">` render block** (`C4.jsx:383-394`) — the `<GraphView .../>` — with the tiered renderer. Pass the model + drill state + resolved overlay membership + the `onDrill` reducer + `onOpenFinding`:

```jsx
      <section className="c4-scene__graph">
        <h3 className="c4-scene__section-h">Architecture graph</h3>
        <C4TierGraph
          model={c4}
          selectedContainer={selectedContainer}
          selectedComponent={selectedComponent}
          overlayC4NodeIds={overlay.c4NodeIds}
          onDrill={onDrill}
          onOpenFinding={onOpenFinding}
        />
      </section>
```

> `model={c4}` passes the whole `c4_model` window slice (its `nodes`/`edges`/`asset_to_c4`/… are the REAL names; `C4TierGraph` reads `model.nodes`/`model.edges` and runs `c4BackboneLayout(model.nodes, model.edges)` itself). `overlayC4NodeIds={overlay.c4NodeIds}` is the **resolved membership array** from the kept overlay-resolution `useMemo` (`C4.jsx:91-120`) — Task 8 consumes it for the dim/live-edge highlight.

**3d. Confirm the GraphView import is gone.** `C4.jsx` references `GraphView` only via the now-replaced JSX (the bundler resolves it off `window`, there is no `import` line). After 3c there must be **zero** `GraphView` occurrences in `C4.jsx`. Grep to confirm:

```
grep -n "GraphView\|onNodeTap\|overlayHighlight\|layout=\|compound=" report-template/screens/C4.jsx
```

Expected: **no matches** (every Cytoscape-coupling string is gone). The `EN2 _c4KindLabel` helper at the top of the file (which only decorated GraphView labels) is now dead — delete it and its block comment (`C4.jsx:19-30`); `C4TierGraph` renders the `data_store`/`external_system` cues itself from `node.kind` (M7 Task 1–6) and the drill-list keeps its own `c4-kind-chip`.

- [ ] **Step 4: Run the tests to verify they pass (green)**

Rebuild the bundle first (the bundle assertion needs the regenerated `app.js`):

```
.venv/bin/python tools/build_report_template.py
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_screen_exists_and_renders_blocks tests/test_workflow_apd_gauntlet.py::test_bundle_contains_c4_scene tests/test_workflow_apd_gauntlet.py::test_c4_graph_node_tap_drives_drill tests/test_workflow_apd_gauntlet.py::test_c4_screen_surfaces_node_kind_chip tests/test_workflow_apd_gauntlet.py::test_c4_overlay_join_uses_from_id_to_id -v
```

Expected: all five PASS (the three rewritten + the two kept-green neighbors). Then run the C4-adjacent suite to confirm the shared `GraphView` tests (644–720) and the tab/registration/style tests stay green:

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "c4 or graph_view or GraphView" -v
```

Expected: all pass — AttackPaths/ThreatModel are unaffected because `GraphView` in `components.jsx` is untouched.

- [ ] **Step 5: Commit**

```
git add report-template/screens/C4.jsx report-template/app.js report-template/.source-hash \
        tools/apd_gauntlet/data/report-template tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): wire C4 scene to the tiered C4TierGraph, drop the fcose GraphView

C4.jsx render swap (data model unchanged): replaces <GraphView layout=fcose
compound> with <C4TierGraph model selectedContainer selectedComponent
overlayC4NodeIds onDrill onOpenFinding>. Drops the GraphView-only 'graph'
subgraph useMemo and the 'overlayHighlight' synthetic-path useMemo; renames the
onNodeTap reducer to onDrill (now wired to tiered node-box clicks + NodeRow).
Keeps the present-gate, honest banner, overlay RESOLUTION useMemo, NodeRow
deep-link, breadcrumb, and c4-kind-chip. GraphView (AttackPaths/ThreatModel)
untouched. Rewrites the 3 Cytoscape-asserting C4 tests to assert the tiered
scene. Bundle + .source-hash regenerated.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Overlay-highlight rebuild for SVG (dim non-members + induced "live" edges + unmapped-hops strip)

**Files:**

- Modify: `report-template/components.jsx` (`C4TierGraph` non-member dimming + `C4EdgeLayer` induced-edge "live" styling, keyed off `overlayC4NodeIds`)
- Modify: `report-template/screens/C4.jsx` (the overlay `<select>` control + the kept "parallel asset hops — no C4 mapping" strip — both already present from M6; this step only re-confirms they survive the Task 7 render swap)
- Modify: `report-template/screens.css` (append `.nb--dim` + `.edge-layer__path--live` / `.edge-layer__port--live`; the `.c4-overlay*` / `.c4-overlay-strip*` rules already exist)
- Test: `tests/test_workflow_apd_gauntlet.py` (REWRITE `test_c4_attack_path_overlay` to assert the SVG highlight + strip; line ≈ 1047)

Because `GraphView`'s synthetic-`paths` cross-highlight is gone (Task 7), `C4TierGraph` must render the highlight itself. The highlight is **set membership**: when `overlayC4NodeIds` is non-empty, dim non-member node boxes (opacity), and draw the **induced** edges between members as "live" (accent + thicker) in `C4EdgeLayer`. The "parallel asset hops — no C4 mapping" honesty strip (already in `C4.jsx` from M6, wired to the REAL `data.attack_paths → asset_to_c4/finding_to_c4` resolution) is kept beneath the scene — never invent an unmapped hop onto the tiered graph.

- [ ] **Step 1: Rewrite the failing source-assertion test (TDD)**

Replace `test_c4_attack_path_overlay` (≈ line 1047). The old version asserts "reuses GraphView cross-highlight"; the new one asserts the SVG-native highlight (member dimming + induced live edges) and the kept strip:

```python
def test_c4_attack_path_overlay() -> None:
    """The attack-path overlay is an SVG-native highlight on the tiered scene
    (no GraphView): selecting a path resolves grounded c4 node ids via the
    deterministic asset_to_c4 + finding_to_c4 join, dims non-member node boxes,
    draws the induced member edges 'live', and keeps the 'no C4 mapping' strip
    for unmapped hops. Honest partial overlay only."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # consumes the existing enumerated paths + the DETERMINISTIC join (no client-side mapping)
    assert "data.attack_paths" in src
    assert "selectedOverlayPath" in src and "setSelectedOverlayPath" in src
    assert "asset_to_c4" in src and "finding_to_c4" in src
    # the resolved MEMBERSHIP (not a GraphView synthetic path) is handed to the renderer
    assert "overlayC4NodeIds" in src
    assert "overlayHighlight" not in src, "GraphView synthetic-path highlight is gone"
    # honest partial overlay: unmapped hops on a PARALLEL asset strip, never a C4 hop
    assert "c4-overlay-strip" in src and "no C4 mapping" in src
    assert "unmappedHops" in src

    comp = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    # C4TierGraph dims non-members + marks induced member edges live, off overlayC4NodeIds
    assert "overlayC4NodeIds" in comp
    assert "nb--dim" in comp           # non-member node boxes are dimmed
    assert "edge-layer__path--live" in comp  # induced member edges drawn live
    # induced-edge rule: both endpoints in the membership set
    assert "C4EdgeLayer" in comp

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    assert ".c4-overlay-strip" in css and ".c4-overlay-strip__hop--unmapped" in css
    assert ".nb--dim" in css and ".edge-layer__path--live" in css
```

- [ ] **Step 2: Run the test to verify it fails (red)**

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_attack_path_overlay -v
```

Expected: FAIL on `assert "nb--dim" in comp` — `C4TierGraph`/`C4EdgeLayer` (from M7 Tasks 1–6) accept `overlayC4NodeIds` but do not yet draw the highlight, so the dimming/live-edge strings are absent.

- [ ] **Step 3: Implement the highlight inside `C4TierGraph` / `C4EdgeLayer` (minimal impl)**

**3a. Dim non-member node boxes in `C4TierGraph`.** Compute a membership set once and add the `nb--dim` class to any rendered `.nb` node box whose id is not in the set (only when the overlay is active). In `components.jsx`, inside `C4TierGraph({ model, selectedContainer, selectedComponent, overlayC4NodeIds, onDrill, onOpenFinding })`, derive the set and a per-box class helper:

```jsx
  // Attack-path overlay membership (Task 8). When an overlay path is selected,
  // overlayC4NodeIds is the resolved set of grounded c4 node ids it traverses
  // (asset_to_c4 + finding_to_c4 join, computed in C4.jsx — never here). Active
  // overlay => dim every node box NOT in the set, and draw the induced member
  // edges 'live'. Empty set => no dimming (normal scene).
  const overlaySet = React.useMemo(
    () => new Set(overlayC4NodeIds || []),
    [overlayC4NodeIds]
  );
  const overlayActive = overlaySet.size > 0;
  const dimClass = React.useCallback(
    (id) => (overlayActive && !overlaySet.has(id) ? " nb--dim" : ""),
    [overlayActive, overlaySet]
  );
```

Then, in the single `NodeBox` renderer that every tier uses (the backbone, both L2 shelves, the L3 component grid, and the L4 code grid — built in M7 Tasks 1–6), append `dimClass(node.id)` to its `className`. The box already carries `data-id={node.id}` for the router's DOM measurement and the `onClick={() => onDrill(node.id)}` drill (with the `⚑` badge `onClick` calling `stopPropagation()` + `onOpenFinding` per the contract):

```jsx
  function NodeBox({ node }) {
    return (
      <div
        className={`nb nb--${node.type}${node.id === selectedContainer || node.id === selectedComponent ? " nb--selected" : ""}${dimClass(node.id)}`}
        data-id={node.id}
        role="button"
        tabIndex={0}
        title={c4BoxTitle(node)}
        onClick={() => onDrill(node.id)}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onDrill(node.id); } }}
      >
        <div className="nb__name">{node.label}</div>
        <NbBadges node={node} onOpenFinding={onOpenFinding} />
      </div>
    );
  }
```

> `dimClass` is the only Task-8 change to `NodeBox`; everything else (the in-box `⚑`/`🛡` badges via `NbBadges`, the `not_analyzed` striped treatment, the selected ring) is the M7 Task 1–6 box. Keeping the dimming in `className` (not inline `opacity`) lets the CSS var-driven theme recolor live.

**3b. Draw the induced member edges "live" in `C4EdgeLayer`.** `C4EdgeLayer` already iterates `model.edges`, measures source/target boxes with `c4Anchors`, routes with `c4RouteWaypoints`, and emits a `c4RoundedPath` `<path>` + start port + short label per edge (M7 Tasks 1–6). Add the induced-edge test (both endpoints in `overlaySet`) and branch the path/port class. This **replaces** the induced-edge expansion that `C4.jsx`'s deleted `overlayHighlight` used to do — it now lives where the edges are drawn:

```jsx
function C4EdgeLayer({ model, stageRef, overlayC4NodeIds, redrawKey }) {
  const [paths, setPaths] = React.useState([]);
  const overlaySet = React.useMemo(
    () => new Set(overlayC4NodeIds || []),
    [overlayC4NodeIds]
  );
  const overlayActive = overlaySet.size > 0;

  // Measure the rendered boxes and route each grounded edge. An edge is "live"
  // (induced member edge) iff the overlay is active AND BOTH endpoints are in
  // the membership set — that is the same both-endpoints-in-set rule the old
  // GraphView overlayHighlight used, applied here at draw time. Only edges in
  // model.edges are ever drawn (never invent an edge for an unmapped hop).
  const redraw = React.useCallback(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const next = [];
    (model.edges || []).forEach((e) => {
      const srcEl = stage.querySelector(`[data-id="${e.source}"]`);
      const tgtEl = stage.querySelector(`[data-id="${e.target}"]`);
      if (!srcEl || !tgtEl) return; // endpoint not on this drill level — skip
      const [s, t] = c4Anchors(srcEl, tgtEl, stage);
      const pts = c4RouteWaypoints(s, t);
      const d = c4RoundedPath(pts, 7);
      const live = overlayActive && overlaySet.has(e.source) && overlaySet.has(e.target);
      // label at the midpoint of the last segment > 18px (de-collide hub fan-out)
      const label = c4ShortEdgeLabel(e.label);
      const lp = c4EdgeLabelPoint(pts);
      next.push({ id: e.id, d, port: pts[0], live, label, full: e.label, lp });
    });
    setPaths(next);
  }, [model, stageRef, overlayActive, overlaySet]);

  React.useEffect(redraw, [redraw, redrawKey]);
  React.useEffect(() => {
    const onResize = () => redraw();
    window.addEventListener("resize", onResize);
    window.addEventListener("load", onResize);
    if (document.fonts && document.fonts.ready) { document.fonts.ready.then(redraw); }
    const mo = new MutationObserver(redraw);
    mo.observe(document.body, { attributes: true, attributeFilter: ["data-theme", "data-sev"] });
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("load", onResize);
      mo.disconnect();
    };
  }, [redraw]);

  return (
    <svg className="edge-layer" aria-hidden="true">
      <defs>
        <marker id="c4-arrow" className="edge-layer__arrow" viewBox="0 0 10 10"
                refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" />
        </marker>
        <marker id="c4-arrow-live" className="edge-layer__arrow edge-layer__arrow--live" viewBox="0 0 10 10"
                refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" />
        </marker>
      </defs>
      {paths.map((p) => (
        <g key={p.id}>
          <path
            className={`edge-layer__path${p.live ? " edge-layer__path--live" : ""}`}
            d={p.d}
            markerEnd={p.live ? "url(#c4-arrow-live)" : "url(#c4-arrow)"}
          >
            <title>{p.full}</title>
          </path>
          <circle
            className={`edge-layer__port${p.live ? " edge-layer__port--live" : ""}`}
            cx={p.port.x} cy={p.port.y} r="3"
          />
          {p.label && p.lp && (
            <text className="edge-layer__label" x={p.lp.x} y={p.lp.y}>{p.label}</text>
          )}
        </g>
      ))}
    </svg>
  );
}
```

> `C4TierGraph` renders `<C4EdgeLayer model={model} stageRef={stageRef} overlayC4NodeIds={overlayC4NodeIds} redrawKey={`${selectedContainer}|${selectedComponent}`} />` inside its stage so the layer re-measures on every drill change. `c4EdgeLabelPoint` (midpoint of the last segment > 18px) and `c4BoxTitle`/`NbBadges` are the M7 Task 1–6 helpers; this task only adds the `live` branch + the `nb--dim` class. The `<title>` carries the **full** machine `e.label` for hover (short label shown inline) per the contract.

**3c. The overlay `<select>` control + unmapped-hops strip in `C4.jsx` are kept as-is** (they came in with M6 and survive the Task 7 render swap unchanged). Re-confirm both blocks are still present in `C4.jsx`:

- the `c4-overlay` `<select>` (`C4.jsx:330-354`) driving `selectedOverlayPath` from `overlayPaths`;
- the `c4-overlay-strip` block (`C4.jsx:356-381`) rendering `overlay.unmappedHops` with the literal `"no C4 mapping"` head, the `from_name → to_name` mono row, and the `⚑ {finding_id}` deep-link.

No change to either block; they already consume the REAL `data.attack_paths → asset_to_c4/finding_to_c4` resolution from the kept overlay-resolution `useMemo`. The select feeds `selectedOverlayPath → overlay.c4NodeIds → overlayC4NodeIds` into `C4TierGraph` (Task 7 3c), which is what Steps 3a/3b consume.

- [ ] **Step 4: Add the CSS (append to `screens.css`)**

The `.c4-overlay*` and `.c4-overlay-strip*` rules already exist (`screens.css:1382-1430`). Append only the two new highlight rules (the base `.edge-layer`, `.nb`, `.tier*`, `.archx*` rules come from M7 Task 3's CSS lift):

```css
/* Attack-path overlay highlight (Task 8) — set-membership dim + induced live edges. */
.nb--dim {
  opacity: 0.32;
  filter: saturate(0.6);
  transition: opacity 0.15s ease;
}
.edge-layer__path--live {
  stroke: var(--accent);
  stroke-width: 2.5;
}
.edge-layer__port--live { fill: var(--accent); }
.edge-layer__arrow--live path { fill: var(--accent); }
```

> Colors read from CSS vars (`--accent`) so the theme `MutationObserver` redraw (3b) recolors live — matching `_graphStylesheet`'s `getComputedStyle` approach. `.nb--dim` is class-based (not inline opacity) so it composes with the tier styles.

- [ ] **Step 5: Rebuild the bundle + run the test to verify it passes (green)**

```
.venv/bin/python tools/build_report_template.py
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py::test_c4_attack_path_overlay tests/test_workflow_apd_gauntlet.py::test_c4_scene_styles_present -v
```

Expected: both PASS. Then run the full C4 + shared-graph slice to confirm no regression:

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k "c4 or graph_view or GraphView or bundle" -v
```

Expected: all pass — the overlay highlight is now SVG-native, `GraphView` is untouched for AttackPaths/ThreatModel, and the freshness gate sees a fresh `.source-hash`.

- [ ] **Step 6: Commit**

```
git add report-template/components.jsx report-template/screens.css \
        report-template/screens/C4.jsx report-template/app.js report-template/.source-hash \
        tools/apd_gauntlet/data/report-template tests/test_workflow_apd_gauntlet.py
git commit -m "feat(report): SVG-native attack-path overlay highlight for the tiered C4 scene

Rebuilds the overlay-highlight that GraphView's synthetic-path cross-highlight
used to provide. C4TierGraph dims non-member node boxes (.nb--dim) when
overlayC4NodeIds is non-empty; C4EdgeLayer draws the INDUCED member edges
(both endpoints in the membership set) 'live' (accent + thicker, live arrow
marker) at draw time — the same both-endpoints-in-set rule the deleted
overlayHighlight useMemo applied, moved to where edges are drawn. Keeps the
'parallel asset hops — no C4 mapping' honesty strip + the overlay <select>,
both wired to the REAL data.attack_paths -> asset_to_c4/finding_to_c4
resolution. Honest partial highlight only; never invents an unmapped hop onto
the graph. Rewrites test_c4_attack_path_overlay to assert the SVG highlight +
strip. Bundle + .source-hash regenerated.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**Milestone 7 exit check (after Tasks 7–8):**

```
.venv/bin/python -m pytest -q && \
.venv/bin/python tools/check_report_template_freshness.py && \
grep -c "GraphView\|fcose\|overlayHighlight" report-template/screens/C4.jsx
```

Expected: full suite green; freshness gate green (rebuilt `.source-hash` matches); the `grep -c` returns `0` (every Cytoscape-coupling string removed from `C4.jsx`). `ruff check .` / `mypy tools/apd_gauntlet` are unaffected (JSX-only change; no Python touched).

---

**Source-path notes for the implementer (relevant absolute paths):**
- `/Users/user/Documents/GitHub/APD-sec-arch-framework/report-template/screens/C4.jsx` — rewrite target (current: GraphView render at lines 383-394; `graph` useMemo 134-187; `overlayHighlight` 122-132; `onNodeTap` reducer 194-201; overlay-resolution useMemo to KEEP at 91-120; overlay `<select>` + strip to KEEP at 330-381; `_c4KindLabel` dead-code at 19-30).
- `/Users/user/Documents/GitHub/APD-sec-arch-framework/report-template/components.jsx` — `GraphView` at line 294 (UNTOUCHED); add `C4TierGraph`/`C4EdgeLayer` highlight here (Task 8 3a/3b); window export via the existing `Object.assign(window,{...})` near line 504.
- `/Users/user/Documents/GitHub/APD-sec-arch-framework/report-template/screens.css` — existing `.c4-overlay*`/`.c4-overlay-strip*` at 1382-1430 (REUSED); append `.nb--dim`/`.edge-layer__path--live` (Task 8 4).
- `/Users/user/Documents/GitHub/APD-sec-arch-framework/docs/superpowers/design_handoff_c4_architecture_view/README.md` — overlay highlight spec at lines 310-314 (dim non-members + induced live edges + kept strip); router VERBATIM at 202-263.

### Task 9: Bundle rebuild + freshness/audit gates green + the Milestone-7 ACCEPTANCE CHECKLIST

This is the final Milestone-7 task. The triple-enforced freshness gate (`build.py` `BundleFreshnessError`, `tools/check_report_template_freshness.py`, and the report audit's `source_hash_drift` check) makes the rebuild + `.source-hash` commit MANDATORY after the M7 JSX/CSS edits. It also runs the full acceptance checklist that proves the tiered redesign meets the design handoff and that nothing else regressed.

**Files:**

- Modify: `tools/apd_gauntlet/data/report-template/app.js` (regenerated)
- Modify: `tools/apd_gauntlet/data/report-template/screens.css` (regenerated)
- Modify: `tools/apd_gauntlet/data/report-template/.source-hash` (regenerated)
- Modify: `report-template/data.js` (regenerated tracked example, if this repo tracks one — confirm via `git status`)
- Modify: `tools/apd_gauntlet/data/report-template/components.jsx` and `tools/apd_gauntlet/data/report-template/screens/C4.jsx` (the packaged source copies are regenerated by the build — `git status` will show them)

- [ ] **Step 1: Confirm the freshness gate is RED after the M7 source edits** (the prior impl tasks changed `components.jsx` + `screens/C4.jsx` + `screens.css` in `report-template/`).

```
.venv/bin/python tools/check_report_template_freshness.py; echo "exit=$?"
```

Expected (RED, `exit=1`): `report-template/ has changed since the precompiled bundle was generated` with `expected=<M6-hash> actual=<M7-hash>`. The hash covers `report-template/**` minus `.build`/`node_modules`/dot-prefixed paths (see `compute_source_hash`), so the `C4TierGraph` + helpers in `components.jsx`, the C4.jsx render rewrite, and the new `.archx-*`/`.tier`/`.nb`/`.edge-layer` rules in `screens.css` all perturb it.

- [ ] **Step 2: Run the gate to verify it fails** — same command as Step 1; confirm `exit=1`. (Also confirm the 4 Task-1 tests are STILL red here — the impl tasks made the source-level asserts pass, but `test_bundle_contains_c4_scene` reads the packaged `app.js`, which is stale until Step 3.)

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py -k test_bundle_contains_c4_scene -q; echo "exit=$?"
```

Expected (RED, `exit=1`): `app.js` lacks `C4TierGraph`/`c4BackboneLayout` until rebuilt.

- [ ] **Step 3: Rebuild the bundle** (regenerates `report-template/app.js` + `.source-hash` AND the packaged `tools/apd_gauntlet/data/report-template/`). Node v26 + the vendored esbuild are used; no `&` / background.

```
.venv/bin/python tools/build_report_template.py
```

Expected: `build-report-template: bundle written.` If it prints `node + npm are required`, install Node 20+ first — the runtime never needs Node, but the contributor rebuild does.

- [ ] **Step 4: Regenerate the tracked example report** so the committed example shows the tiered C4 scene (the example feeds the freshness hash via the non-dot `report-template/data.js`). Assemble `c4-model.yaml` for the committed fixture run first, build into a scratch (dot-prefixed, hash-excluded) dir, then copy out `data.js`.

```
.venv/bin/apd-gauntlet assemble-c4 tests/fixtures/runs/c4-home-assistant \
  && .venv/bin/apd-gauntlet build-report tests/fixtures/runs/c4-home-assistant \
       --out-dir report-template/.example-c4 --quiet \
  && cp "report-template/.example-c4/data.js" report-template/data.js
```

> Confirm the tracked-example path with `git status` before committing — if this repo tracks `report-template/APD Gauntlet Report.html` instead of / in addition to `report-template/data.js`, regenerate that too. The scratch `.example-c4/` dir is dot-prefixed so `compute_source_hash` skips it; only `report-template/data.js` (non-dot) feeds the hash, which is why the FINAL rebuild (Step 5) must follow this regeneration.

- [ ] **Step 5: Rebuild last** so `.source-hash` reflects the final `report-template/data.js`, then run the gate — expect GREEN.

```
.venv/bin/python tools/build_report_template.py \
  && .venv/bin/python tools/check_report_template_freshness.py; echo "exit=$?"
```

Expected (GREEN, `exit=0`):

```
build-report-template: bundle written.
check_report_template_freshness: OK (<hex>)
exit=0
```

- [ ] **Step 6: Turn the 4 Task-1 tests GREEN + confirm the 5 keepers + shared-GraphView suite stay green.** This is the red→green completion of the milestone's TDD bar.

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "c4 or C4 or graph_view or attack_paths or threat_model or kind_passthrough or bundle or mermaid" -v; echo "exit=$?"
```

Expected (GREEN, `exit=0`): the 4 rewritten tests now pass (C4.jsx has `C4TierGraph`/`onDrill`/`overlayC4NodeIds`/`stopPropagation` and NOT `GraphView`/`fcose`/`overlayHighlight`; `app.js` carries `C4TierGraph`+`c4BackboneLayout`), the 5 keepers pass, and AttackPaths/ThreatModel/shared-GraphView/mermaid tests pass (untouched).

- [ ] **Step 7: Full Python gates — pytest + ruff + mypy** (JSX is eslint-disabled; the gates are Python-only, and they cover the transform/assembler/loader that the example regeneration exercised).

```
.venv/bin/python -m pytest \
  && .venv/bin/python -m ruff check . \
  && .venv/bin/python -m mypy tools/apd_gauntlet; echo "exit=$?"
```

Expected (GREEN, `exit=0`): the whole suite passes, ruff clean, mypy clean. (No Python source changed in M7's render-only redesign, so a regression here means the example regeneration or a stray edit broke something — investigate before committing.)

- [ ] **Step 8: Determinism spot-check — the layout/label helpers are byte-stable.** Build the example report twice from a clean tree and diff `data.js` + the bundle; `c4BackboneLayout` (layered BFS longest-path columns, stable sorts) and `c4ShortEdgeLabel` (pure prefix-strip / verb-map) must produce identical bytes.

```
.venv/bin/apd-gauntlet assemble-c4 tests/fixtures/runs/c4-home-assistant >/dev/null \
  && .venv/bin/apd-gauntlet build-report tests/fixtures/runs/c4-home-assistant \
       --out-dir /tmp/c4-det-a --quiet \
  && .venv/bin/apd-gauntlet build-report tests/fixtures/runs/c4-home-assistant \
       --out-dir /tmp/c4-det-b --quiet \
  && diff -q /tmp/c4-det-a/data.js /tmp/c4-det-b/data.js \
  && echo "DETERMINISTIC: data.js byte-identical across two builds"
```

Expected: `DETERMINISTIC: data.js byte-identical across two builds` (no output from `diff`). The layout helper lives in `components.jsx` and runs at render in-browser, but the `data.c4_model` it consumes (nodes/edges, stable-sorted by the assembler) is what the build emits; a non-deterministic emit would diff here. (The helpers themselves are pure JS exercised by the Task-1 source asserts; their byte-stability is structural — stable sorts, no `Date`/`Math.random`.)

- [ ] **Step 9: Report-audit `source_hash_drift` green on the regenerated example run** (the third leg of the triple freshness enforcement — the audit refuses a report whose embedded source-hash doesn't match the bundle).

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "source_hash or completeness or report_audit or freshness" -q; echo "exit=$?"
```

Expected (GREEN, `exit=0`): the audit's `source_hash_drift` check and the completeness gate pass against the freshly rebuilt bundle.

- [ ] **Step 10: Commit the regenerated bundle + example.**

```
git add tools/apd_gauntlet/data/report-template/app.js \
        tools/apd_gauntlet/data/report-template/screens.css \
        tools/apd_gauntlet/data/report-template/components.jsx \
        tools/apd_gauntlet/data/report-template/screens/C4.jsx \
        tools/apd_gauntlet/data/report-template/.source-hash \
        report-template/data.js
git commit -m "build(report): rebuild bundle + regenerate example for the tiered C4 scene

Regenerate app.js/.source-hash + the packaged report-template copy for the
M7 tiered C4 redesign (C4TierGraph + c4BackboneLayout/c4ShortEdgeLabel + the
SVG edge-layer router). Regenerate the tracked example (report-template/data.js)
from the c4-home-assistant fixture so the committed example carries the tiered
Architecture scene. Triple freshness gate (BundleFreshnessError /
check_report_template_freshness / report-audit source_hash_drift) green.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 11: Run the FULL Milestone-7 ACCEPTANCE CHECKLIST.** Each item maps to the design-handoff acceptance list + the SHARED CONTRACT's four gap-fixes. Verify by inspection of the rendered example report (`open "report-template/.example-c4/index.html"` or the tracked example, with `<body data-theme="dark">`/`paper` toggled) and the cited test/source anchors. Check every box before declaring the milestone done.

  **Tiered scene & connectors**
  - [ ] C4 screen renders as stacked tiers **L1 System context → L2 Container → (L3 Component) → L4 Code** with left-gutter labels (`.tier`/`.tier-gutter` from the lifted prototype CSS; the L1 3-column actors/system/externals layout; L2 backbone + two shelves).
  - [ ] Connectors are **orthogonal (H/V only)** with **~7px rounded elbows**, accent-colored, with arrowheads + start ports, drawn in the SVG `.edge-layer` only for the **grounded `edges[]`** — **no invented edges** (no person→container / system→container connectors; containment is `parent`, not an edge). The router ports `c4Anchors`/`c4RouteWaypoints`/`c4RoundedPath` VERBATIM (offsetParent-walk, zoom-invariant; redraw on render/resize/`fonts.ready`/theme `MutationObserver`).
  - [ ] **Edge labels are short** (`c4ShortEdgeLabel`: strip `CROSS_*` prefix / relation→verb / first ~3 words), de-collided (placed on the last segment >18px), with the **full raw `edge.label` on hover**. No hand-curated per-run labels.

  **In-node badges & honesty**
  - [ ] Every node box renders a `.nb__badges` row: `badge > 0` → clickable `⚑ {badge}` (sev-high) deep-linking via `onOpenFinding(provenance.first_finding_id)`; static `⚑ {badge}` when no `first_finding_id` (never hidden); `badge == null` analyzed-zero → **muted `⚑ 0`** (never "clean"); `capability_badge > 0` → `🛡 {capability_badge}` (sev-low). Applies in the **backbone, both shelves, L3 grid, and L4 grid** — every tier.
  - [ ] **`not_analyzed` is striped/dashed** with a `not analyzed` marker and **no counts** (`.c4-node-row--not-analyzed` / `.c4-badge--not-analyzed` reused; the infra shelf uses the muted striped chip). Distinct from analyzed-zero.

  **Drill / deep-link / breadcrumb**
  - [ ] Clicking a container drills (**L3 if components exist, else L4**); clicking a component drills to its code; a **`⚑` badge `stopPropagation`s** so it deep-links to Findings WITHOUT drilling; breadcrumb (`⌂ System / Container: X [/ Component: Y]`) + "↑ up one level" work; `⌂ System` resets. The NodeRow "code elements list" beneath the diagram is kept.

  **L3 data-driven honesty**
  - [ ] L3 tier renders `type==="component"` boxes **when present** and an **honest "blocked / none"** state otherwise — the **c4-home-assistant fixture shows L2→L4** (no grounded components), with the "L3 components appear here when a run grounds them via `c4-recon.components[]`…" hint.

  **Toolbar / overlay / themes**
  - [ ] **Zoom/fit toolbar** (`−` / `100%` / `+` / `fit`; `transform: scale()` on the stage inner; `fit` solves to wrapper width; reuses the `.report-graph__toolbar` look) works.
  - [ ] **Attack-path overlay** works: selecting a path resolves grounded C4 node ids via `asset_to_c4` + `finding_to_c4` into `overlayC4NodeIds`, dims non-members (`opacity`), redraws induced edges as **live (accent, thicker)**, and keeps the **unmapped-hops parallel strip** (`.c4-overlay-strip__hop--unmapped`, "no C4 mapping"). Honest partial highlight only.
  - [ ] **Hover tooltip** is text-only (no HTML injection from adopter data): label, level, kind, counts, "↳ click to drill" hint.
  - [ ] **Light / dark / paper themes recolor live** — all colors are CSS vars read at draw time; the `data-theme`/`data-sev` `MutationObserver` re-measures + redraws edges. `test_c4_scene_styles_present` confirms the C4 CSS block is fully `var(--…)` (no hex literals).

  **Determinism & the gap-fixes**
  - [ ] **Node placement is deterministic from the data** — `c4BackboneLayout` partitions `connected`/`analyzed`/`infra`, lays out layered BFS longest-path columns with stable label/badge-desc sorts; **no curated per-run position map** (the prototype's `BACKBONE` map is NOT ported), **no randomness** (Step 8 byte-identical builds confirm).
  - [ ] **Data-fidelity (gap-fix 2):** the React scene consumes the **REAL `window.APD_DATA.c4_model` names** (`badge`/`analysis_state`/`provenance`/`capability_badge`/`asset_to_c4`/`finding_to_c4`/full `edge.label`), NOT the prototype-fixture abbreviations (`cap`/`state`/`ff`/`me`/`overlay_paths`); the dev fixture `archx-data.js` was regenerated honestly from the real slice.
  - [ ] **`GraphView` is UNTOUCHED** and **AttackPaths / ThreatModel are unaffected** — they still render the Cytoscape `GraphView` (the shared-GraphView + EN2 kind-passthrough tests stay green; `AttackPaths.jsx`/`ThreatModel.jsx` are byte-unchanged).
  - [ ] **The "L3 demo (synthetic)" affordance is NOT shipped** — `git grep -i "demo (synthetic)\|syntheticL3\|L3 demo" report-template/` returns nothing in `C4.jsx`/`components.jsx`.

  **Bundle / gates (gap-fix 4)**
  - [ ] **Bundle + `.source-hash` committed** and the **triple freshness gate is green** (`check_report_template_freshness: OK`, `build.py` `BundleFreshnessError` not raised on a fresh build, report-audit `source_hash_drift` green); the tracked example (`report-template/data.js`) reflects the tiered scene.
  - [ ] **Test-rewrite-first (gap-fix 1)** honored: the 4 Task-1 tests went RED → GREEN across this milestone; the 5 keepers + shared-GraphView suite stayed green throughout; full `pytest` + `ruff` + `mypy` green.

- [ ] **Step 12: Milestone-7 exit check** (one command — the front-end regression slice + freshness + Python gates).

```
.venv/bin/python -m pytest tests/test_workflow_apd_gauntlet.py \
  -k "c4 or C4 or graph_view or attack_paths or threat_model or bundle or mermaid or kind_passthrough" -v \
  && .venv/bin/python tools/check_report_template_freshness.py \
  && git grep -L "layout=\"fcose\"" -- report-template/screens/C4.jsx >/dev/null \
  && .venv/bin/python -m ruff check . \
  && .venv/bin/python -m mypy tools/apd_gauntlet; echo "exit=$?"
```

Expected (GREEN, `exit=0`): all C4/graph/bundle/mermaid tests pass, freshness `OK`, `C4.jsx` carries **no** `layout="fcose"` (the `git grep -L` succeeds = the pattern is absent in that file), ruff + mypy clean.

> The plan is appended under a new `## Milestone 7` section of `docs/superpowers/plans/2026-06-13-c4-architecture-view.md` (after the Milestone-6 Task-7 section ending at line ~5903). Task 1 is the FIRST task of the milestone (TDD red bar) and Task 9 is the LAST (rebuild + acceptance); the intervening impl Tasks 2–8 (the `c4BackboneLayout`/`c4ShortEdgeLabel`/router helpers + `C4TierGraph` in `components.jsx`, the C4.jsx render rewrite, the CSS lift, and the honest `archx-data.js` regeneration) are what flip Task 1's 4 tests from red to green before Task 9 rebuilds and runs acceptance.
