# Golden-run framework-bug fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the APD gauntlet robust to the reality that LLM specialist agents cannot reliably produce the canonical record envelope or deterministic SHA-256 IDs — by adding a tooling-authoritative `canonicalize` step, making the validators non-vacuous, and fixing the four other defects (F1–F5) the SIA golden run surfaced.

**Architecture:** A new `canonicalize` command owns structural correctness (envelope normalization + deterministic IDs + cross-reference rewrites), reusing `linters.compute_id` / `_PREFIX_BY_AGENT` as the single source of truth for ID computation. It runs (idempotent, whole-run) before each tier's `validate` gate in the workflow. `validate` and `check-ids` are made non-vacuous (they fall back to the plural root key and unwrap per-record wrappers) AND emit a hard ERROR when a non-canonical envelope reaches them, so drift is loud instead of silent. Three smaller fixes harden the synthesis loader (F3), the attack-path builder (F5), and add a regression test for the already-applied report-data resolver fix (F4). Agent prompts and the schema skill are tightened for the parts only agents control (F2 agent-side).

**Tech Stack:** Python 3.12+, `click` (CLI), PyYAML, `jsonschema` / `referencing` (schema validation), `pytest` + `click.testing.CliRunner` (tests). Workflow runner is JavaScript (`.claude/workflows/apd-gauntlet.js`). Agent/skill definitions are Markdown with YAML frontmatter.

---

## Source spec

`docs/superpowers/specs/2026-05-31-golden-run-framework-bugs-design.md` (approved design). Defect catalog in `runs/apd-20260531-sia-self-improving-agent/RUN-NOTES-framework-findings.md`.

## Pre-flight: branch & environment

- Work on the existing branch `fix/golden-run-framework-bugs` (the F4 fix already lives there, uncommitted).
- The package is importable as `apd_gauntlet` via an editable install. If imports fail, from the repo root run: `pip install -e .`
- Run the full suite at any checkpoint with: `pytest` (repo root). Run a single file with: `pytest tests/<file>.py -v`.

## Dependency ordering (why the tasks are sequenced this way)

`canonicalize` (C1) must exist **before** `validate` is made strict (C2): the strict envelope ERROR assumes a normalizer ran ahead of it, and the workflow (C7) wires `canonicalize` before each tier gate. The shared `extract_records` helper is created in `validate.py` in Task 2 (C1 needs it) and then consumed by `_iter_records`, `check-ids`, and the loader in later tasks. Tasks 6 (C3), 7 (C5), and 8 (C6) are independent of the C1→C2→C7 chain and of each other. Task 1 (C4) is first because it commits the already-applied F4 fix and leaves the working tree clean for everything that follows.

Order: **Task 1 (C4) → Task 2 (C1 core) → Task 3 (C1 CLI) → Task 4 (C2 validate) → Task 5 (C2 check-ids) → Task 6 (C3) → Task 7 (C5) → Task 8 (C6) → Task 9 (C7) → Task 10 (integration + self-review).**

## File Structure

**Created:**
- `tools/apd_gauntlet/canonicalize.py` — the structural canonicalizer (envelope + IDs + cross-refs). One responsibility: make a run's lens records canonical without touching semantic content.
- `tests/test_canonicalize.py` — unit tests for the canonicalizer.
- `tests/test_cli_canonicalize.py` — CLI-level tests for the `canonicalize` command.
- `tests/test_cli_check_ids.py` — tests for the now-non-vacuous `check-ids` command (only if no existing file covers it; see Task 5).
- `tests/fixtures/canonicalize/` — small fixtures: a non-canonical lens file (plural + wrapped + fabricated IDs) and its expected canonical form.

**Modified:**
- `tools/apd_gauntlet/validate.py` — add `extract_records`; refactor `_iter_records` to use it (non-vacuous); add `_check_envelopes` hard-ERROR pass; (F4 fix already present).
- `tools/apd_gauntlet/cli.py` — add the `canonicalize` command; fix `check_ids_cmd` to be non-vacuous.
- `tools/apd_gauntlet/synthesis/loader.py` — add the missing-`id` skip guard to the capability branch (F3).
- `tools/apd_gauntlet/attack_path/build.py` — make `_node_name_index` resolve crown_jewel↔asset collisions; wire a `data_resides_on` edge for the realization (F5).
- `.claude/skills/apd-finding-schema/SKILL.md` — make the canonical envelope explicit; add a "common mistakes" block; note IDs are tooling-canonicalized (F2).
- `.claude/agents/apd-{confidentiality,integrity,availability,distributed,resilient,ephemeral,authenticity,non-repudiation,immutability}.md` — one shared, identical reminder in each Output section (F2).
- `.claude/workflows/apd-gauntlet.js` — `pyStep('canonicalize')` before each tier gate; add `'canonicalize'` to `meta.phases` (C7).
- `tests/test_validate_*.py` (new test functions) and `tests/test_workflow_apd_gauntlet.py` — coverage for C2 and C7.
- `tests/test_attack_path_build.py` — coverage for C5.
- `tests/test_loader.py` (or the existing loader test file) — coverage for C3.

---

### Task 1: Commit the F4 resolver fix with its regression test (C4)

The 21-line F4 fix is already applied to `tools/apd_gauntlet/validate.py` (in `_validate_report_data_cross_refs`) but uncommitted and untested. This task proves it has teeth and commits fix + test atomically.

**Files:**
- Modify (commit only, no code change): `tools/apd_gauntlet/validate.py:340-366` (the existing uncommitted hunk in `_validate_report_data_cross_refs`)
- Test: `tests/test_cli_validate_report_data.py` (existing file — add two functions)

- [ ] **Step 1: Read the existing test file to match its fixture style**

Run: `sed -n '1,40p' tests/test_cli_validate_report_data.py`
Note how it builds a run dir and invokes `validate` via `CliRunner`. Reuse that exact pattern (imports, fixture construction) in Step 2 rather than inventing a new one.

- [ ] **Step 2: Write the failing test**

Add to `tests/test_cli_validate_report_data.py`. This asserts a `report-data.yaml` that headlines a `merged-<sha8>` id present ONLY in `deduped-findings.yaml` validates clean, and that a genuinely unknown id still errors. Adjust the run-dir construction to match the helper already present in the file (e.g. a `_make_run(tmp_path)` or inline build); the body below assumes a minimal hand-built run dir.

```python
import pathlib
import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def _write(path: pathlib.Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _minimal_report_run(tmp_path: pathlib.Path, headline_id: str) -> pathlib.Path:
    run = tmp_path / "run"
    synth = run / "40-synthesis"
    # A merged finding that exists ONLY in the deduped corpus (its filename does
    # NOT match the *.findings.yaml glob, so _iter_records never sees it).
    _write(synth / "deduped-findings.yaml", {
        "finding": [{
            "schema_version": 1,
            "id": "merged-abcd1234",
            "agent": "synthesizer",
            "apd_tier": "trustworthiness",
            "apd_goal": "confidentiality",
            "disposition": "gap",
            "severity": "high",
            "confidence": "high",
            "title": "Merged PHI exposure cluster",
            "summary": "x",
            "detail": "y",
            "evidence": [{"artifact": "tech_plan.md", "locator": "§1", "excerpt": "q"}],
            "recommendation": {"posture": "required", "summary": "s", "detail": "d"},
        }],
    })
    _write(synth / "report-data.yaml", {
        "schema_version": 1,
        "headline_findings": [{"id": headline_id, "rank": 1}],
    })
    return run


def test_report_data_resolves_merged_id_from_deduped_corpus(tmp_path):
    run = _minimal_report_run(tmp_path, headline_id="merged-abcd1234")
    result = CliRunner().invoke(main, ["validate", str(run)])
    # The merged-* id resolves via the deduped union, so no "unknown finding".
    assert "unknown finding" not in result.output, result.output


def test_report_data_unknown_id_still_errors(tmp_path):
    run = _minimal_report_run(tmp_path, headline_id="merged-deadbeef")
    result = CliRunner().invoke(main, ["validate", str(run)])
    assert result.exit_code != 0, result.output
    assert "deadbeef" in result.output or "unknown" in result.output.lower(), result.output
```

- [ ] **Step 3: Run the new tests — expect PASS (fix is applied)**

Run: `pytest tests/test_cli_validate_report_data.py -v -k "merged_id or unknown_id"`
Expected: both new tests PASS (the F4 fix is in the working tree).

> If `report-data.schema.json` requires more fields on `headline_findings` entries or the doc root than shown, the schema pass will error first and mask the cross-ref check. If that happens, read `schemas/report-data.schema.json`, add only the minimal required fields to the fixture, and re-run. The cross-ref assertion (`"unknown finding" not in output`) is the behavior under test.

- [ ] **Step 4: Confirm the test has teeth (temporary RED)**

Temporarily stash ONLY the validate.py change, run the tests, confirm the merged-id test now FAILS, then restore:

```bash
git stash push tools/apd_gauntlet/validate.py
pytest tests/test_cli_validate_report_data.py -v -k "merged_id"   # expect FAIL: "unknown finding"
git stash pop
pytest tests/test_cli_validate_report_data.py -v -k "merged_id"   # expect PASS again
```

Expected: FAIL while stashed (proves the union is what makes it pass), PASS after restore.

- [ ] **Step 5: Commit fix + test together**

```bash
git add tools/apd_gauntlet/validate.py tests/test_cli_validate_report_data.py
git commit -m "fix(validate): union deduped corpus in report-data cross-ref resolver (F4)

The report-data cross-ref check built its known-id set only from _iter_records
(per-lens + apath), so a report headlining a legitimate merged-<sha8> finding
(minted by apply.py, living only in deduped-findings.yaml — whose filename does
not match the *.findings.yaml glob) failed with 'unknown finding'. Mirror the
sibling _validate_domain_improvements_cross_refs union. Adds a regression test.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `extract_records` helper + the `canonicalize` core (C1)

Build the structural canonicalizer. It is idempotent, whole-run, and structural-only: it normalizes the envelope, recomputes deterministic IDs (tooling is authoritative), and rewrites cross-references. It NEVER edits titles, excerpts, or evidence.

**Files:**
- Modify: `tools/apd_gauntlet/validate.py` (add `extract_records` near `_iter_records`, ~line 80)
- Create: `tools/apd_gauntlet/canonicalize.py`
- Create: `tests/test_canonicalize.py`

- [ ] **Step 1: Add the shared `extract_records` helper to `validate.py`**

Insert immediately above `_iter_records` (currently at `validate.py:80`):

```python
def extract_records(doc: dict[str, Any], root_key: str) -> list[dict[str, Any]]:
    """Return the bare record dicts from a findings/capabilities document.

    The single shared extraction rule used by canonicalize, ``_iter_records``,
    ``check-ids``, and the synthesis loader — so they cannot drift. Accepts:

    - the canonical singular root key (``finding`` / ``capability``) whose value
      is a list of bare records (or a single bare record), AND
    - the legacy plural root key (``findings`` / ``capabilities``), AND
    - per-record wrappers of the form ``{<root_key>: {...}}`` (unwrapped here).

    Non-dict items are dropped. This is extraction only; it does not validate.
    """
    raw = doc.get(root_key)
    if raw is None:
        raw = doc.get(root_key + "s")
    items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
    out: list[dict[str, Any]] = []
    for item in items:
        if (
            isinstance(item, dict)
            and set(item.keys()) == {root_key}
            and isinstance(item[root_key], dict)
        ):
            item = item[root_key]  # unwrap a per-record {finding: {...}} wrapper
        if isinstance(item, dict):
            out.append(item)
    return out
```

- [ ] **Step 2: Write the failing unit test for `extract_records`**

Create `tests/test_canonicalize.py` with this first test:

```python
"""Unit tests for the structural canonicalizer (C1)."""
from __future__ import annotations

from apd_gauntlet.validate import extract_records


def test_extract_records_handles_singular_plural_and_wrapped():
    # singular root, list of bare records
    assert extract_records({"finding": [{"id": "a"}, {"id": "b"}]}, "finding") == [
        {"id": "a"}, {"id": "b"},
    ]
    # singular root, single bare record
    assert extract_records({"finding": {"id": "a"}}, "finding") == [{"id": "a"}]
    # legacy plural root
    assert extract_records({"findings": [{"id": "a"}]}, "finding") == [{"id": "a"}]
    # per-record wrapper is unwrapped
    assert extract_records(
        {"finding": [{"finding": {"id": "a"}}, {"finding": {"id": "b"}}]}, "finding"
    ) == [{"id": "a"}, {"id": "b"}]
    # empty / absent
    assert extract_records({}, "finding") == []
```

- [ ] **Step 3: Run it — expect PASS (helper added in Step 1)**

Run: `pytest tests/test_canonicalize.py -v -k extract_records`
Expected: PASS.

- [ ] **Step 4: Write the `canonicalize.py` module**

Create `tools/apd_gauntlet/canonicalize.py`:

```python
"""Structural canonicalizer for specialist findings / capabilities (C1).

``apd-gauntlet canonicalize <run_dir>`` — idempotent, whole-run, structural-only.

Repairs ONLY what is derivable / structural:
  - envelope: singular root key (``finding`` / ``capability``), per-record
    unwrap, per-record ``schema_version``
  - deterministic IDs (tooling-authoritative; overwrites whatever agents wrote)
  - ``cross_references`` rewritten through the global old->new id map

Does NOT edit semantic content (titles, excerpts, evidence). A file is rewritten
only when it contains at least one IN-SCOPE record — one whose ``agent`` maps to
a known lens prefix in ``linters._PREFIX_BY_AGENT`` (the nine specialist lenses).
This deliberately leaves alone:
  - ``40-synthesis/deduped-*.yaml`` (apply.py mints ``merged-*`` ids) — excluded
    by glob anyway, since ``deduped-findings.yaml`` does not match
    ``*.findings.yaml``;
  - ``40-synthesis/attack-path.findings.yaml`` (agent ``attack_path_analyzer``)
    and ``40-threat-model/threat-model.findings.yaml`` (agent
    ``threat_model_evaluator``) — they contain no in-scope records.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .linters import _PREFIX_BY_AGENT, compute_id
from .validate import extract_records

# (singular root key, glob) per record kind. Mirrors validate.RECORD_KINDS.
_KINDS: tuple[tuple[str, str], ...] = (
    ("finding", "*.findings.yaml"),
    ("capability", "*.capabilities.yaml"),
)


class CanonicalizeCollision(Exception):
    """Two distinct in-scope records would receive the same canonical id."""


@dataclass
class CanonicalizeResult:
    records_canonicalized: int
    cross_refs_rewritten: int


def _capability_id(prefix: str, title: str, first_locator: str) -> str:
    """Capability id: ``<prefix>-cap-<sha8(title|locator)>`` — mirrors the
    expected-id computation in ``linters.check_capability_id``."""
    digest = hashlib.sha256(f"{title}|{first_locator}".encode()).hexdigest()[:8]
    return f"{prefix}-cap-{digest}"


def _first_locator(record: dict[str, Any]) -> str | None:
    evidence = record.get("evidence") or []
    if not evidence or not isinstance(evidence[0], dict):
        return None
    return evidence[0].get("locator", "")


def _recompute_ids_for_file(
    path: Path,
    root_key: str,
    id_map: dict[str, str],
    seen_new_ids: set[str],
) -> list[dict[str, Any]] | None:
    """Pass 1 for one file: load, normalize the envelope in memory, inject
    ``schema_version``, and recompute the id of every in-scope record (populating
    ``id_map`` old->new and the global ``seen_new_ids`` collision set). Returns
    the normalized record list when the file has >=1 in-scope record, else None
    (the file is left untouched on disk)."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return None
    records = extract_records(doc, root_key)
    in_scope = 0
    for rec in records:
        rec.setdefault("schema_version", 1)
        prefix = _PREFIX_BY_AGENT.get(rec.get("agent") or "", "")
        if not prefix:
            continue  # out-of-scope agent (attack_path / threat_model / etc.)
        locator = _first_locator(rec)
        if locator is None:
            continue  # cannot compute a deterministic id without a locator
        in_scope += 1
        title = rec.get("title", "")
        new_id = (
            compute_id(prefix, title, locator)
            if root_key == "finding"
            else _capability_id(prefix, title, locator)
        )
        if new_id in seen_new_ids:
            raise CanonicalizeCollision(
                f"id collision on {new_id!r} in {path}: two records share the "
                f"same (title, first-evidence-locator) under prefix {prefix!r}"
            )
        seen_new_ids.add(new_id)
        old_id = rec.get("id")
        if old_id:
            id_map[old_id] = new_id
        rec["id"] = new_id
    return records if in_scope else None


def _rewrite_cross_refs(records: list[dict[str, Any]], id_map: dict[str, str]) -> int:
    """Pass 2 for one file: rewrite every ``cross_references`` entry through the
    global id_map. Handles both the bare-string form and the defensive
    ``{"id": ...}`` dict form. Returns the count of entries actually changed."""
    changed = 0
    for rec in records:
        refs = rec.get("cross_references")
        if not isinstance(refs, list):
            continue
        for i, ref in enumerate(refs):
            if isinstance(ref, str) and ref in id_map and id_map[ref] != ref:
                refs[i] = id_map[ref]
                changed += 1
            elif isinstance(ref, dict) and isinstance(ref.get("id"), str):
                rid = ref["id"]
                if rid in id_map and id_map[rid] != rid:
                    ref["id"] = id_map[rid]
                    changed += 1
    return changed


def canonicalize_run(run_dir: Path) -> CanonicalizeResult:
    """Canonicalize every in-scope lens file under ``run_dir`` in place."""
    id_map: dict[str, str] = {}
    seen_new_ids: set[str] = set()
    pending: list[tuple[Path, str, list[dict[str, Any]]]] = []
    records_canonicalized = 0

    # Pass 1 — global: recompute ids file-by-file (deterministic file order).
    for root_key, glob in _KINDS:
        for path in sorted(run_dir.rglob(glob)):
            records = _recompute_ids_for_file(path, root_key, id_map, seen_new_ids)
            if records is None:
                continue
            pending.append((path, root_key, records))
            records_canonicalized += sum(
                1 for r in records if _PREFIX_BY_AGENT.get(r.get("agent") or "", "")
            )

    # Pass 2 — global: rewrite cross-refs, then write each file back canonically.
    cross_refs_rewritten = 0
    for path, root_key, records in pending:
        cross_refs_rewritten += _rewrite_cross_refs(records, id_map)
        doc = {root_key: records}
        path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096),
            encoding="utf-8",
        )

    return CanonicalizeResult(records_canonicalized, cross_refs_rewritten)
```

- [ ] **Step 5: Write the failing canonicalize behavior tests**

Append to `tests/test_canonicalize.py`:

```python
import pathlib
import yaml
from apd_gauntlet.canonicalize import (
    CanonicalizeCollision,
    canonicalize_run,
)
from apd_gauntlet.linters import compute_id
import pytest


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _finding(agent, title, locator, fid="fabricated-00000000", **extra):
    rec = {
        "id": fid,
        "agent": agent,
        "title": title,
        "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "q"}],
    }
    rec.update(extra)
    return rec


def test_canonicalize_normalizes_plural_root_and_unwraps(tmp_path):
    run = tmp_path / "run"
    # plural root key + per-record wrapper + fabricated id
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    canonicalize_run(run)
    doc = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )
    # singular root key, bare record, schema_version injected
    assert set(doc.keys()) == {"finding"}
    assert isinstance(doc["finding"], list)
    rec = doc["finding"][0]
    assert rec["schema_version"] == 1
    assert "finding" not in rec  # unwrapped
    # id recomputed deterministically (tooling-authoritative)
    assert rec["id"] == compute_id("conf", "PHI in topic", "§4.2")


def test_canonicalize_rewrites_cross_references(tmp_path):
    run = tmp_path / "run"
    a = _finding("confidentiality", "A", "§1")
    b = _finding("integrity", "B", "§2", fid="fab-b",
                 cross_references=["fabricated-00000000"])
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {"finding": [a]})
    _write(run / "10-trustworthiness" / "integrity.findings.yaml", {"finding": [b]})
    canonicalize_run(run)
    b_doc = yaml.safe_load(
        (run / "10-trustworthiness" / "integrity.findings.yaml").read_text()
    )
    expected_a_id = compute_id("conf", "A", "§1")
    assert b_doc["finding"][0]["cross_references"] == [expected_a_id]


def test_canonicalize_is_idempotent(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": _finding("confidentiality", "PHI in topic", "§4.2")}],
    })
    canonicalize_run(run)
    first = (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_bytes()
    canonicalize_run(run)
    second = (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_bytes()
    assert first == second  # second run is a byte-for-byte no-op


def test_canonicalize_is_structural_only(tmp_path):
    run = tmp_path / "run"
    long_title = "X" * 250  # over the 200-char limit validate enforces
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [_finding("confidentiality", long_title, "§1",
                             evidence=[{"artifact": "tech_plan.md", "locator": "§1",
                                        "excerpt": "word " * 40}])],
    })
    canonicalize_run(run)
    rec = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )["finding"][0]
    assert rec["title"] == long_title  # NOT trimmed — validate flags content, not canonicalize
    assert rec["evidence"][0]["excerpt"] == "word " * 40  # untouched


def test_canonicalize_collision_raises(tmp_path):
    run = tmp_path / "run"
    # Two distinct records with the SAME title + locator under the same agent
    # -> identical computed id -> collision.
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [
            _finding("confidentiality", "dup", "§1", fid="fab-1"),
            _finding("confidentiality", "dup", "§1", fid="fab-2"),
        ],
    })
    with pytest.raises(CanonicalizeCollision):
        canonicalize_run(run)


def test_canonicalize_leaves_out_of_scope_records_untouched(tmp_path):
    run = tmp_path / "run"
    synth = run / "40-synthesis"
    # attack-path file: agent not in _PREFIX_BY_AGENT -> file untouched
    apath = {"finding": [{"schema_version": 1, "id": "apath-deadbeef",
                          "agent": "attack_path_analyzer", "title": "t",
                          "evidence": [{"artifact": ".apd-run.yaml", "locator": "x",
                                        "excerpt": "y"}]}]}
    _write(synth / "attack-path.findings.yaml", apath)
    before = (synth / "attack-path.findings.yaml").read_bytes()
    # deduped file: filename does not match the *.findings.yaml glob at all
    _write(synth / "deduped-findings.yaml", {"finding": [{"id": "merged-abcd1234"}]})
    ded_before = (synth / "deduped-findings.yaml").read_bytes()
    canonicalize_run(run)
    assert (synth / "attack-path.findings.yaml").read_bytes() == before
    assert (synth / "deduped-findings.yaml").read_bytes() == ded_before
```

- [ ] **Step 6: Run the canonicalize tests — implement until green**

Run: `pytest tests/test_canonicalize.py -v`
Expected: all PASS. If `test_canonicalize_leaves_out_of_scope_records_untouched` fails because the attack-path file gets rewritten, confirm `_recompute_ids_for_file` returns `None` when `in_scope == 0` (no in-scope records → file skipped).

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/validate.py tools/apd_gauntlet/canonicalize.py tests/test_canonicalize.py
git commit -m "feat(canonicalize): structural canonicalizer for lens records (C1 core)

New canonicalize_run(): idempotent, whole-run, structural-only. Normalizes the
record envelope (singular root key, unwraps per-record wrappers, injects
schema_version), recomputes every deterministic id via linters.compute_id /
_PREFIX_BY_AGENT (tooling-authoritative), and rewrites cross_references through
a global old->new id map. Leaves out-of-scope records (attack_path / merged-*)
untouched. Adds the shared extract_records helper to validate.py.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Wire the `canonicalize` CLI command (C1)

**Files:**
- Modify: `tools/apd_gauntlet/cli.py` (add a command near `cluster-candidates`, ~line 956)
- Create: `tests/test_cli_canonicalize.py`

- [ ] **Step 1: Write the failing CLI test**

Create `tests/test_cli_canonicalize.py`:

```python
"""CLI tests for `apd-gauntlet canonicalize`."""
from __future__ import annotations

import pathlib
import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_id
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_canonicalize_command_normalizes_and_reports(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": {
            "id": "fabricated-00000000",
            "agent": "confidentiality",
            "title": "PHI in topic",
            "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "q"}],
        }}],
    })
    result = CliRunner().invoke(main, ["canonicalize", str(run)])
    assert result.exit_code == 0, result.output
    assert "recanonicalized" in result.output
    doc = yaml.safe_load(
        (run / "10-trustworthiness" / "confidentiality.findings.yaml").read_text()
    )
    assert doc["finding"][0]["id"] == compute_id("conf", "PHI in topic", "§4.2")


def test_canonicalize_command_exits_nonzero_on_collision(tmp_path):
    run = tmp_path / "run"
    rec = {
        "agent": "confidentiality", "title": "dup",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1", "excerpt": "q"}],
    }
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "finding": [dict(rec, id="fab-1"), dict(rec, id="fab-2")],
    })
    result = CliRunner().invoke(main, ["canonicalize", str(run)])
    assert result.exit_code == 1, result.output
    assert "collision" in result.output.lower()
```

- [ ] **Step 2: Run it — expect FAIL (no such command)**

Run: `pytest tests/test_cli_canonicalize.py -v`
Expected: FAIL — `No such command 'canonicalize'` (exit code 2 from Click).

- [ ] **Step 3: Add the command to `cli.py`**

Insert immediately before the `@main.command("cluster-candidates")` block (currently `cli.py:956`):

```python
@main.command("canonicalize")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def canonicalize_cmd(run_dir: Path) -> None:
    """Structurally canonicalize specialist findings/capabilities in place.

    Idempotent, whole-run: normalizes the record envelope (singular root key,
    unwraps per-record wrappers, injects schema_version), recomputes every
    deterministic id (tooling is authoritative), and rewrites cross_references.
    Structural only — never edits titles, excerpts, or evidence.
    """
    from .canonicalize import CanonicalizeCollision, canonicalize_run

    try:
        result = canonicalize_run(run_dir)
    except CanonicalizeCollision as exc:
        click.echo(f"canonicalize: blocked - {exc}", err=True)
        raise SystemExit(1) from None
    click.echo(
        f"canonicalize: {result.records_canonicalized} records recanonicalized, "
        f"{result.cross_refs_rewritten} cross-refs rewritten"
    )
```

- [ ] **Step 4: Run the CLI tests — expect PASS**

Run: `pytest tests/test_cli_canonicalize.py -v`
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli_canonicalize.py
git commit -m "feat(cli): add 'canonicalize' command (C1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Make `validate` non-vacuous + strict on the envelope (C2 / F1)

`validate._iter_records` reads only the singular root key, so when agents emit plural roots it matches zero records and exits 0 — vacuous. Fix: iterate via `extract_records` (non-vacuous), AND add a hard ERROR when a non-canonical envelope reaches `validate`.

**Files:**
- Modify: `tools/apd_gauntlet/validate.py` (`_iter_records` at ~line 80; add `_check_envelopes`; call it from `run_schema_pass` at ~line 267)
- Test: `tests/test_validate_envelope.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validate_envelope.py`:

```python
"""C2 / F1: validate is non-vacuous AND rejects non-canonical envelopes."""
from __future__ import annotations

import pathlib
import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _bad_excerpt_record():
    # excerpt > 25 tokens -> a per-record semantic error the lint MUST catch
    return {
        "schema_version": 1,
        "id": "conf-00000000",
        "agent": "confidentiality",
        "apd_tier": "trustworthiness",
        "apd_goal": "confidentiality",
        "disposition": "gap",
        "severity": "high",
        "confidence": "high",
        "title": "t",
        "summary": "s",
        "detail": "d",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§1",
                      "excerpt": "word " * 40}],
        "recommendation": {"posture": "required", "summary": "s", "detail": "d"},
    }


def test_plural_root_is_non_vacuously_validated(tmp_path):
    # Under the OLD bug this exited 0 (zero records matched). Now the per-record
    # excerpt lint fires AND the envelope error fires.
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"findings": [_bad_excerpt_record()]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert result.exit_code != 0, result.output


def test_plural_root_emits_envelope_error(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"findings": [_bad_excerpt_record()]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" in result.output, result.output


def test_wrapped_record_emits_envelope_error(tmp_path):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"finding": [{"finding": _bad_excerpt_record()}]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" in result.output, result.output


def test_canonical_singular_input_has_no_envelope_error(tmp_path):
    run = tmp_path / "run"
    good = _bad_excerpt_record()
    good["evidence"][0]["excerpt"] = "short quote"  # within limit
    # id must match the deterministic rule so check_finding_id passes
    from apd_gauntlet.linters import compute_id
    good["id"] = compute_id("conf", good["title"], good["evidence"][0]["locator"])
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml",
           {"finding": [good]})
    result = CliRunner().invoke(main, ["validate", str(run), "--tier",
                                       "10-trustworthiness"])
    assert "non-canonical envelope" not in result.output, result.output
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_validate_envelope.py -v`
Expected: `test_plural_root_is_non_vacuously_validated` and the two `*_envelope_error` tests FAIL (current code is vacuous and has no envelope check); `test_canonical_singular_input_has_no_envelope_error` may already pass.

- [ ] **Step 3: Refactor `_iter_records` to use `extract_records`**

Replace the body of `_iter_records` (`validate.py:80-94`) with:

```python
def _iter_records(run_dir: pathlib.Path) -> Iterable[tuple[pathlib.Path, str, dict[str, Any]]]:
    """Yield (file_path, kind, record_dict) for every YAML record in the run.

    Uses the shared ``extract_records`` extraction (singular-or-plural root key,
    per-record unwrap) so per-record checks run even on non-canonical files —
    no vacuous pass. The non-canonical envelope itself is flagged separately by
    ``_check_envelopes``.
    """
    for kind, (_schema, root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                yield path, kind, {"_parse_error": str(e)}
                continue
            if not isinstance(data, dict):
                continue
            for record in extract_records(data, root_key):
                yield path, kind, record
```

- [ ] **Step 4: Add the `_check_envelopes` pass**

Insert these two functions just below `_iter_records`:

```python
def _non_canonical_envelope_reason(doc: dict[str, Any], root_key: str) -> str | None:
    """Return a human reason if doc's envelope is non-canonical, else None."""
    plural = root_key + "s"
    if root_key not in doc and plural in doc:
        return f"plural root key '{plural}'"
    raw = doc.get(root_key)
    items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
    for item in items:
        if (
            isinstance(item, dict)
            and set(item.keys()) == {root_key}
            and isinstance(item[root_key], dict)
        ):
            return f"per-record '{root_key}:' wrapper"
    return None


def _check_envelopes(run_dir: pathlib.Path, report: "ValidationReport") -> None:
    """Hard ERROR when a lens findings/capabilities file uses a plural root key
    or wraps any record in a per-record ``{<kind>: {...}}`` wrapper. canonicalize
    is the normalizer; validate refuses to silently accept non-canonical input."""
    for _kind, (_schema, root_key, glob) in RECORD_KINDS.items():
        for path in sorted(run_dir.rglob(glob)):
            try:
                doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue  # parse errors are reported by the schema pass
            if not isinstance(doc, dict):
                continue
            reason = _non_canonical_envelope_reason(doc, root_key)
            if reason:
                report.errors.append(
                    Violation(
                        path,
                        None,
                        f"non-canonical envelope ({reason}): use singular root key "
                        f"'{root_key}' with bare records (run 'apd-gauntlet canonicalize')",
                    )
                )
```

- [ ] **Step 5: Call `_check_envelopes` from `run_schema_pass`**

In `run_schema_pass` (`validate.py:243`), add the call right after the `_iter_records` loop and the three existing `_validate_*` helpers, before `report.files_seen = ...` (currently line 270):

```python
    _validate_code_evidence_index(run_dir, report, registry)
    _validate_context_rollups(run_dir, report, registry, seen_files)
    _validate_synthesis_rollups(run_dir, report, registry, seen_files)
    _check_envelopes(run_dir, report)          # <-- add this line
    report.files_seen = len(seen_files)
    return report
```

- [ ] **Step 6: Run the envelope tests — expect PASS**

Run: `pytest tests/test_validate_envelope.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full validate suite for regressions**

Run: `pytest tests/test_validate_schema_pass.py tests/test_validate_semantic.py tests/test_validate_tier.py tests/test_validate_cross_file.py tests/test_validate_edge_cases.py -v`
Expected: all PASS. If any existing fixture used a plural root key or a wrapped record (legitimately, as a "this should still be accepted" test), the new envelope ERROR will now fire on it. That fixture encoded the bug — update it to the canonical singular/bare envelope and confirm the test's intent still holds. List any such fixtures you change in the commit body.

- [ ] **Step 8: Commit**

```bash
git add tools/apd_gauntlet/validate.py tests/test_validate_envelope.py
git commit -m "fix(validate): non-vacuous record iteration + strict envelope check (C2/F1)

_iter_records now extracts records via the shared extract_records helper
(singular-or-plural root + per-record unwrap), so per-record checks run on the
shape agents actually emit instead of matching zero records and exiting 0. A new
_check_envelopes pass emits a hard ERROR on any plural-root or wrapped-record
lens file, pointing operators at 'apd-gauntlet canonicalize'.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Make `check-ids` non-vacuous (C2 / F1)

`check_ids_cmd` (`cli.py:267-286`) has the identical singular-only bug: `data.get("finding") or data.get("capability")` misses plural roots and wrapped records.

**Files:**
- Modify: `tools/apd_gauntlet/cli.py:267-286`
- Test: `tests/test_cli_check_ids.py` (new — confirm there is no existing `test_*check_ids*` first)

- [ ] **Step 1: Confirm there is no existing check-ids test, then write the failing test**

Run: `ls tests | grep -i check_ids` (if a file exists, add the functions there instead of creating a new file).

Create `tests/test_cli_check_ids.py`:

```python
"""C2 / F1: check-ids is non-vacuous on plural-root and wrapped files."""
from __future__ import annotations

import pathlib
import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _record_with_wrong_id():
    return {
        "id": "conf-deadbeef",  # does NOT match compute_id -> a real mismatch
        "agent": "confidentiality",
        "title": "PHI in topic",
        "evidence": [{"artifact": "tech_plan.md", "locator": "§4.2", "excerpt": "q"}],
    }


def test_check_ids_catches_mismatch_under_plural_root(tmp_path):
    f = tmp_path / "confidentiality.findings.yaml"
    _write(f, {"findings": [_record_with_wrong_id()]})  # plural root
    result = CliRunner().invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 1, result.output
    assert "id mismatch" in result.output


def test_check_ids_catches_mismatch_under_wrapper(tmp_path):
    f = tmp_path / "confidentiality.findings.yaml"
    _write(f, {"finding": [{"finding": _record_with_wrong_id()}]})  # wrapped
    result = CliRunner().invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 1, result.output
    assert "id mismatch" in result.output


def test_check_ids_clean_on_canonical_correct_id(tmp_path):
    from apd_gauntlet.linters import compute_id
    rec = _record_with_wrong_id()
    rec["id"] = compute_id("conf", "PHI in topic", "§4.2")
    f = tmp_path / "confidentiality.findings.yaml"
    _write(f, {"finding": [rec]})
    result = CliRunner().invoke(main, ["check-ids", str(f)])
    assert result.exit_code == 0, result.output
    assert "IDs OK" in result.output
```

- [ ] **Step 2: Run it — expect FAILs**

Run: `pytest tests/test_cli_check_ids.py -v`
Expected: the plural-root and wrapped tests FAIL (current code matches zero records → "IDs OK" → exit 0).

- [ ] **Step 3: Rewrite `check_ids_cmd`**

Replace the body of `check_ids_cmd` (`cli.py:269-286`) with:

```python
def check_ids_cmd(yaml_file) -> None:  # type: ignore[no-untyped-def]
    import yaml as _yaml

    from .validate import extract_records

    data = _yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        click.echo(f"{yaml_file}: IDs OK.")
        return
    if "finding" in data or "findings" in data:
        kind, root_key = "finding", "finding"
    elif "capability" in data or "capabilities" in data:
        kind, root_key = "capability", "capability"
    else:
        click.echo(f"{yaml_file}: IDs OK.")
        return
    records = extract_records(data, root_key)
    found_issues = False
    for rec in records:
        msgs = check_capability_id(rec) if kind == "capability" else check_finding_id(rec)
        for msg in msgs:
            click.echo(f"{yaml_file} [{rec.get('id')}]: {msg}")
            found_issues = True
    if found_issues:
        raise SystemExit(1)
    click.echo(f"{yaml_file}: IDs OK.")
```

- [ ] **Step 4: Run the tests — expect PASS**

Run: `pytest tests/test_cli_check_ids.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli_check_ids.py
git commit -m "fix(cli): make check-ids non-vacuous on plural/wrapped envelopes (C2/F1)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Loader capability `id` skip guard (C3 / F3)

`synthesis/loader.py` `load_corpus` skips findings missing `id` (lines 54-56) but appends capabilities unconditionally (lines 63-67), so a downstream `r["id"]` in `_group_records` raises `KeyError` and `cluster-candidates` crashes.

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/loader.py:63-67`
- Test: `tests/test_loader.py` (new — confirm no existing loader test first)

- [ ] **Step 1: Confirm test home, then write the failing test**

Run: `ls tests | grep -i loader` (if a loader test file exists, add the function there).

Create `tests/test_loader.py`:

```python
"""C3 / F3: load_corpus skips id-less capability records instead of crashing."""
from __future__ import annotations

import pathlib
import yaml
from apd_gauntlet.synthesis.loader import load_corpus


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def test_load_corpus_skips_capability_missing_id(tmp_path, capsys):
    run = tmp_path / "run"
    _write(run / "10-trustworthiness" / "confidentiality.capabilities.yaml", {
        "capability": [
            {"id": "conf-cap-00000000", "agent": "confidentiality", "title": "ok"},
            {"agent": "confidentiality", "title": "missing id"},  # no id
        ],
    })
    _findings, capabilities = load_corpus(run)
    ids = [c.get("id") for c in capabilities]
    assert "conf-cap-00000000" in ids
    assert all(c.get("id") for c in capabilities)  # the id-less one was skipped
    err = capsys.readouterr().err
    assert "missing 'id'; skipping" in err
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL — the id-less capability is currently appended, so `all(c.get("id") ...)` is False (and no warning is emitted).

- [ ] **Step 3: Add the guard**

In `synthesis/loader.py`, change the capability loop (lines 63-67) to mirror the findings loop:

```python
        for idx, rec in enumerate(_records(raw)):
            if not isinstance(rec, dict):
                click.echo(f"WARNING: {f}: capability[{idx}] is not a dict; skipping", err=True)
                continue
            if "id" not in rec:
                click.echo(f"WARNING: {f}: capability[{idx}] missing 'id'; skipping", err=True)
                continue
            capabilities.append(rec)
```

- [ ] **Step 4: Run the test — expect PASS**

Run: `pytest tests/test_loader.py -v`
Expected: PASS.

- [ ] **Step 5: Run the cluster-candidates suite for regressions**

Run: `pytest tests/test_cli_cluster_candidates.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/loader.py tests/test_loader.py
git commit -m "fix(synthesis): skip id-less capability records in load_corpus (C3/F3)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Attack-path builder crown_jewel↔asset collision (C5 / F5)

`_node_name_index` raises `BuilderBlocked` on any case-insensitive name collision. When an inventory asset is named after a crown-jewel pattern string (the asset *realizes* the jewel — same concept), this blocks the whole builder. Resolve that specific pair to the concrete asset node, and emit a `data_resides_on` edge for connectivity (the edge type already exists; no schema change). Reserve `BuilderBlocked` for collisions between two nodes of the **same** type.

**Files:**
- Modify: `tools/apd_gauntlet/attack_path/build.py` (`_node_name_index` at ~line 364; add `_wire_realized_crown_jewels`; call it in `build_graph` at ~line 88)
- Test: `tests/test_attack_path_build.py` (add functions)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_attack_path_build.py`:

```python
from apd_gauntlet.attack_path.build import _node_name_index, _wire_realized_crown_jewels
from apd_gauntlet.attack_path.graph import Graph, Node, Edge, stable_id


def _g_with_jewel_asset_collision():
    g = Graph()
    g.add_node(Node(node_id=stable_id("asset", "phi_store"), node_type="asset",
                    name="phi_store", provenance={"source": "asset_inventory"},
                    confidence="high"))
    g.add_node(Node(node_id=stable_id("jewel", "phi_store"), node_type="crown_jewel",
                    name="phi_store", provenance={"source": "domain_default"},
                    confidence="high"))
    return g


def test_node_name_index_resolves_jewel_asset_collision_to_asset():
    g = _g_with_jewel_asset_collision()
    index = _node_name_index(g)  # must NOT raise
    assert index["phi_store"] == stable_id("asset", "phi_store")


def test_node_name_index_still_blocks_same_type_collision():
    import pytest
    from apd_gauntlet.attack_path.build import BuilderBlocked
    g = Graph()
    g.add_node(Node(node_id=stable_id("asset", "a"), node_type="asset", name="dup",
                    provenance={"source": "asset_inventory"}, confidence="high"))
    g.add_node(Node(node_id=stable_id("asset", "b"), node_type="asset", name="DUP",
                    provenance={"source": "asset_inventory"}, confidence="high"))
    with pytest.raises(BuilderBlocked):
        _node_name_index(g)


def test_wire_realized_crown_jewels_emits_data_resides_on_edge():
    g = _g_with_jewel_asset_collision()
    _wire_realized_crown_jewels(g)
    edges = [e for e in g._edges.values() if e.edge_type == "data_resides_on"]
    assert edges, "expected a data_resides_on edge linking the asset to its jewel"
    e = edges[0]
    assert e.from_node == stable_id("asset", "phi_store")
    assert e.to_node == stable_id("jewel", "phi_store")


def test_wire_realized_crown_jewels_is_idempotent():
    g = _g_with_jewel_asset_collision()
    _wire_realized_crown_jewels(g)
    _wire_realized_crown_jewels(g)  # second call must not raise on duplicate edge
    edges = [e for e in g._edges.values() if e.edge_type == "data_resides_on"]
    assert len(edges) == 1
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_attack_path_build.py -v -k "collision or realized"`
Expected: the resolve / realized tests FAIL (current `_node_name_index` raises on the jewel↔asset collision; `_wire_realized_crown_jewels` does not exist).

- [ ] **Step 3: Rewrite `_node_name_index`**

Replace `_node_name_index` (`build.py:364-382`) with:

```python
def _node_name_index(g: Graph) -> dict[str, str]:
    """Map lower-cased node name -> node_id, for text-based heuristic matching.

    A crown_jewel and an asset may legitimately share a (case-insensitive) name:
    the asset *realizes* the crown jewel (e.g. an inventory asset literally named
    ``phi_store`` realizing the ``phi_store`` crown jewel). That is the same
    concept, not an ambiguity — resolve it deterministically to the CONCRETE
    asset node so downstream text matching is unambiguous. Reserve
    ``BuilderBlocked`` for genuinely ambiguous collisions between two nodes of
    the SAME type, which downstream matching cannot disambiguate.
    """
    index: dict[str, str] = {}
    for nid in sorted(g._nodes):  # deterministic resolution order
        node = g.get_node(nid)
        name = node.name.lower()
        if name not in index:
            index[name] = nid
            continue
        existing = g.get_node(index[name])
        if {existing.node_type, node.node_type} == {"asset", "crown_jewel"}:
            # asset realizes crown jewel — prefer the concrete asset node.
            index[name] = nid if node.node_type == "asset" else index[name]
            continue
        raise BuilderBlocked(
            f"duplicate case-insensitive node name {name!r} between two "
            f"{existing.node_type!r}/{node.node_type!r} nodes "
            f"({index[name]!r}, {nid!r}) — cannot disambiguate"
        )
    return index
```

- [ ] **Step 4: Add `_wire_realized_crown_jewels`**

Insert just below `_node_name_index`:

```python
def _wire_realized_crown_jewels(g: Graph) -> None:
    """When an inventory asset shares a crown jewel's (case-insensitive) name,
    the asset *realizes* that jewel. Wire a ``data_resides_on`` edge asset->jewel
    so path enumeration can traverse the realization. Idempotent: the edge_id is
    deterministic and a duplicate is skipped (``Graph.add_edge`` raises on
    duplicate edge_id)."""
    jewels_by_name = {n.name.lower(): n for n in g.nodes_by_type("crown_jewel")}
    for asset in g.nodes_by_type("asset"):
        jewel = jewels_by_name.get(asset.name.lower())
        if jewel is None:
            continue
        edge_id = stable_id("edge", asset.node_id, jewel.node_id, "data_resides_on")
        if edge_id in g._edges:
            continue  # already wired (e.g. by _add_crown_jewels via classification)
        g.add_edge(
            Edge(
                edge_id=edge_id,
                edge_type="data_resides_on",
                from_node=asset.node_id,
                to_node=jewel.node_id,
                provenance={"source": "asset_inventory", "locator": "name_realizes_crown_jewel"},
                confidence=asset.confidence,
                traversal_cost=1,
            )
        )
```

- [ ] **Step 5: Call it from `build_graph`**

In `build_graph` (`build.py:54`), add the call immediately after `_add_crown_jewels(g, crown_jewel_names, domain_cfg)` (line 87) and before `_add_inventory_trust_edges` (line 89):

```python
    _add_crown_jewels(g, crown_jewel_names, domain_cfg)
    _wire_realized_crown_jewels(g)              # <-- add this line

    _add_inventory_trust_edges(g, inventory)
```

- [ ] **Step 6: Run the C5 tests + the full attack-path build suite**

Run: `pytest tests/test_attack_path_build.py -v`
Expected: all PASS (new + existing).

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/attack_path/build.py tests/test_attack_path_build.py
git commit -m "fix(attack-path): resolve crown_jewel<->asset name collision (C5/F5)

_node_name_index no longer blocks when an inventory asset shares a crown jewel's
name — the asset realizes the jewel, so it resolves deterministically to the
concrete asset node and a data_resides_on edge links the two. BuilderBlocked is
reserved for same-type ambiguous collisions. No schema change (data_resides_on
already exists).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Tighten the schema skill + specialist agent prompts (C6 / F2 agent-side)

Agents control evidence-artifact choice and length; tooling owns IDs and envelope. Make the canonical envelope explicit in the skill, add a common-mistakes block, and add one identical reminder to each of the nine specialist agents. Add a staleness test pinning the skill statement.

**Files:**
- Modify: `.claude/skills/apd-finding-schema/SKILL.md`
- Modify: `.claude/agents/apd-{confidentiality,integrity,availability,distributed,resilient,ephemeral,authenticity,non-repudiation,immutability}.md`
- Test: `tests/test_skill_apd_finding_schema_envelope.py` (new)

- [ ] **Step 1: Write the failing staleness test**

Create `tests/test_skill_apd_finding_schema_envelope.py`:

```python
"""C6: the finding-schema skill must state the canonical singular-bare envelope."""
from __future__ import annotations

import pathlib

SKILL = (
    pathlib.Path(__file__).parent.parent
    / ".claude" / "skills" / "apd-finding-schema" / "SKILL.md"
)


def test_skill_states_singular_bare_envelope():
    text = SKILL.read_text(encoding="utf-8")
    assert "Output envelope (canonical)" in text
    # explicitly forbids the two drift shapes
    assert "never the plural" in text
    assert "tooling-canonicalized" in text
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `pytest tests/test_skill_apd_finding_schema_envelope.py -v`
Expected: FAIL — those strings are not in the skill yet.

- [ ] **Step 3: Add the envelope section to the skill**

In `.claude/skills/apd-finding-schema/SKILL.md`, insert this block immediately after the "## Canonical contract" section (after line 30, before "## Finding schema"):

```markdown
## Output envelope (canonical)

Each output file uses the **singular** root key whose value is a **list of bare records**:

```yaml
finding:                      # singular — never the plural 'findings:'
  - schema_version: 1         # each record carries schema_version
    id: conf-1a2b3c4d         # best-effort; see "IDs are tooling-canonicalized" below
    agent: confidentiality
    # ... rest of the record, BARE (not wrapped) ...
  - schema_version: 1
    # ... second record ...
```

Capabilities files use the singular `capability:` root key the same way.

**IDs are tooling-canonicalized.** `apd-gauntlet canonicalize` recomputes every
`id` deterministically (`sha8(title|first-evidence-locator)`, with a `-cap-`
infix for capabilities) and rewrites `cross_references` to match. Author a
best-effort `id`, but do **not** hand-tune it — tooling is the source of truth.

### Common mistakes (rejected by `validate`)

- **Plural root key** (`findings:` / `capabilities:`) — use the singular root.
- **Per-record wrapper** — do NOT wrap each record in its own `finding:` /
  `capability:` key. Records in the list are bare maps.
- **`context-brief.md` as evidence** — evidence `artifact` values must be **input
  artifacts** (e.g. `tech_plan.md`, a `.proto`, an IaC file), never the intake
  brief.
- **Over-length** — `title` ≤ 200 characters; each evidence `excerpt` ≤ 25
  whitespace-separated tokens.
```

> Note: the `finding:`/`capability:` example blocks elsewhere in this skill show a single record under the root key for brevity. The list form above is the canonical multi-record shape; both the single-record and list forms validate, but agents should emit the list form.

- [ ] **Step 4: Run the staleness test — expect PASS**

Run: `pytest tests/test_skill_apd_finding_schema_envelope.py -v`
Expected: PASS.

- [ ] **Step 5: Add the identical reminder to each of the nine agent files**

In EACH of the nine `.claude/agents/apd-<lens>.md` files, find the `## Output` section and append this block at its end (immediately before the next `##` heading). Use the EXACT same text in all nine files:

```markdown
**Output envelope reminder.** Emit a **bare, singular** `finding:` / `capability:`
list (never the plural `findings:`/`capabilities:`, and never wrap a record in its
own `finding:`/`capability:` key). Each record carries `schema_version: 1`.
Evidence `artifact` values must be **input artifacts** (e.g. `tech_plan.md`),
never `00-context/context-brief.md`. Keep `title` ≤ 200 characters and each
evidence `excerpt` ≤ 25 tokens. IDs are tooling-canonicalized — author a
best-effort `id` and do not hand-tune it.
```

The nine files: `apd-confidentiality.md`, `apd-integrity.md`, `apd-availability.md`, `apd-distributed.md`, `apd-resilient.md`, `apd-ephemeral.md`, `apd-authenticity.md`, `apd-non-repudiation.md`, `apd-immutability.md`.

- [ ] **Step 6: Run lint-agents to confirm the edits don't break agent structure**

Run: `apd-gauntlet lint-agents`
Expected: `Lint clean: <N> agents checked.` (lint-agents checks frontmatter + required-reading paths + the `## Output bounding` marker, none of which this edit touches; if it errors, you removed or displaced the `## Output bounding` heading — restore it.)

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/apd-finding-schema/SKILL.md .claude/agents/apd-*.md tests/test_skill_apd_finding_schema_envelope.py
git commit -m "docs(agents): make canonical envelope explicit in skill + agents (C6/F2)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Wire `canonicalize` into the workflow before each tier gate (C7)

`canonicalize` must run (idempotent, whole-run) before each tier's `validate` gate so the gate sees canonical input.

**Files:**
- Modify: `.claude/workflows/apd-gauntlet.js` (`runTier` at ~line 295; `meta.phases` at ~line 36)
- Test: `tests/test_workflow_apd_gauntlet.py` (add functions)

- [ ] **Step 1: Read the existing workflow structural test to match its assertion style**

Run: `sed -n '1,60p' tests/test_workflow_apd_gauntlet.py`
Note how it loads the JS file and asserts on its text / structure. Reuse that exact approach in Step 2.

- [ ] **Step 2: Write the failing structural tests**

Add to `tests/test_workflow_apd_gauntlet.py` (adjust the file-read helper to match what the file already uses):

```python
import pathlib

WORKFLOW = (
    pathlib.Path(__file__).parent.parent
    / ".claude" / "workflows" / "apd-gauntlet.js"
)


def test_canonicalize_in_meta_phases():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "'canonicalize'" in text
    # appears inside the meta.phases array
    phases_block = text.split("phases:", 1)[1].split("]", 1)[0]
    assert "canonicalize" in phases_block


def test_canonicalize_precedes_tier_validate_gate():
    text = WORKFLOW.read_text(encoding="utf-8")
    # inside runTier, the canonicalize pyStep must appear before the tier
    # validate gate pyStep.
    run_tier = text.split("function runTier", 1)[1].split("\nfunction ", 1)[0]
    assert "pyStep('canonicalize'" in run_tier
    assert run_tier.index("pyStep('canonicalize'") < run_tier.index(
        "pyStep('validate'"
    )
```

- [ ] **Step 3: Run them — expect FAILs**

Run: `pytest tests/test_workflow_apd_gauntlet.py -v -k canonicalize`
Expected: FAIL — no canonicalize wiring yet.

- [ ] **Step 4: Add `'canonicalize'` to `meta.phases`**

In `.claude/workflows/apd-gauntlet.js`, edit the `phases` array (lines 36-44). Add `'canonicalize'` immediately before `'tier-1'`:

```javascript
  phases: [
    'setup', 'intake', 'code-recon', 'tm-recon',
    'canonicalize',
    'tier-1', 'tier-2', 'tier-3',
    'synthesis-cluster', 'synthesis-adjudicate', 'synthesis-apply',
    'synthesis-fallback', 'tmeval', 'apath', 'synthesis-rollup',
    'synthesis-report', 'synthesis-build', 'synthesis-audit',
    'domain-coverage-delta', 'domain-improvements',
    'closeout',
  ],
```

- [ ] **Step 5: Add the `canonicalize` pyStep inside `runTier`**

In `runTier` (lines 295-334), insert a canonicalize pyStep after the retry loop and BEFORE the tier validate gate (before the `pyStep('validate', {` at line 328). `canonicalize` is whole-run and idempotent, so it takes the run dir as its positional (the pyStep default):

```javascript
  // Canonicalize the whole run (idempotent, structural-only) so the tier gate
  // below sees canonical envelopes + deterministic ids. Runs before EACH tier
  // gate; because tiers run in order, later tiers read canonical earlier-tier
  // ids. Uses the shared 'canonicalize' phase group for display.
  pyStep('canonicalize', {
    phase: 'canonicalize', label: 'canonicalize-' + tierDir,
    outputs: 'canonicalized lens records under ' + runDir,
  });
  // Tier-end gate. --tier SKIPS cross-file Pass 3; the full pre-Phase-5 gate covers that.
  pyStep('validate', {
    phase: phaseName, label: 'validate-' + tierDir,
    cliArgs: '--tier ' + tierDir + ' --errors-only',
    outputs: 'tier ' + tierDir + ' records (read-only gate)',
    validateScope: runDir, validateFlags: '--tier ' + tierDir,
  });
```

- [ ] **Step 6: Run the workflow tests — expect PASS**

Run: `pytest tests/test_workflow_apd_gauntlet.py -v`
Expected: all PASS (new + existing). If an existing test pins the exact set/order of `meta.phases`, update its expected list to include `'canonicalize'`.

- [ ] **Step 7: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tests/test_workflow_apd_gauntlet.py
git commit -m "feat(workflow): canonicalize before each tier validate gate (C7)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Integration test, full suite, and self-review

Prove the end-to-end path (non-canonical specialist output → canonicalize → validate exits 0) and confirm nothing regressed.

**Files:**
- Test: `tests/integration/test_canonicalize_then_validate.py` (new)

- [ ] **Step 1: Write the integration test**

Create `tests/integration/test_canonicalize_then_validate.py`:

```python
"""Integration: non-canonical specialist output -> canonicalize -> validate clean."""
from __future__ import annotations

import pathlib
import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def _write(path: pathlib.Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _full_finding(agent, title, locator):
    return {
        "agent": agent,
        "apd_tier": "trustworthiness",
        "apd_goal": "confidentiality" if agent == "confidentiality" else "integrity",
        "disposition": "gap",
        "severity": "high",
        "confidence": "high",
        "title": title,
        "summary": "one sentence.",
        "detail": "multi paragraph technical analysis.",
        "evidence": [{"artifact": "tech_plan.md", "locator": locator, "excerpt": "short quote"}],
        "recommendation": {"posture": "required", "summary": "s", "detail": "d"},
    }


def test_canonicalize_then_tier_validate_is_clean(tmp_path):
    run = tmp_path / "run"
    # Non-canonical specialist output: plural root + per-record wrapper + fabricated id.
    _write(run / "10-trustworthiness" / "confidentiality.findings.yaml", {
        "findings": [{"finding": dict(_full_finding("confidentiality",
                                                    "PHI in topic", "§4.2"),
                                       id="fabricated-deadbeef")}],
    })
    runner = CliRunner()

    # Before canonicalize: the tier gate ERRORs on the non-canonical envelope.
    pre = runner.invoke(main, ["validate", str(run), "--tier", "10-trustworthiness"])
    assert pre.exit_code != 0
    assert "non-canonical envelope" in pre.output

    # canonicalize, then re-validate the tier.
    canon = runner.invoke(main, ["canonicalize", str(run)])
    assert canon.exit_code == 0, canon.output
    post = runner.invoke(main, ["validate", str(run), "--tier", "10-trustworthiness"])
    assert post.exit_code == 0, post.output
```

> If the tier validate still errors after canonicalize, read the ERROR lines: any remaining failure is a *content* issue canonicalize intentionally does not fix (e.g. a missing required schema field). Add the minimal required field to `_full_finding` so the record is schema-valid; the envelope/id behaviors are what this test pins.

- [ ] **Step 2: Run the integration test — expect PASS**

Run: `pytest tests/integration/test_canonicalize_then_validate.py -v`
Expected: PASS.

- [ ] **Step 3: Run the FULL test suite**

Run: `pytest`
Expected: all green. Investigate and fix any regression before proceeding — do not skip or xfail.

- [ ] **Step 4: Self-review against the spec**

Re-read `docs/superpowers/specs/2026-05-31-golden-run-framework-bugs-design.md` and confirm each component is covered:
- C1 canonicalize (envelope + ids + cross-refs, idempotent, collision guard, out-of-scope skip) → Tasks 2, 3 ✓
- C2 non-vacuous validate + envelope ERROR + non-vacuous check-ids → Tasks 4, 5 ✓
- C3 loader capability guard → Task 6 ✓
- C4 F4 regression test + commit → Task 1 ✓
- C5 builder collision + data_resides_on edge → Task 7 ✓
- C6 skill + 9 agents + staleness test → Task 8 ✓
- C7 workflow wiring + structural test → Task 9 ✓
- Testing matrix (canonicalize unit, validate/check-ids F1, loader F3, resolver F4, builder F5, workflow, agents/skill, integration) → covered across Tasks 1–10 ✓

Confirm nothing in "Out of scope" was touched: no SIA re-run, no id-algorithm change, no attack-path bridging rework beyond F5, no canonicalization of `apath-*`/`merged-*` records.

- [ ] **Step 5: Final integration commit (if any fixture tweaks were needed in Steps 1-3)**

```bash
git add -A
git commit -m "test: end-to-end canonicalize->validate integration + suite green (C1-C7)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Finish the branch**

Use the `superpowers:finishing-a-development-branch` skill to decide merge / PR / cleanup. All ten tasks complete, full suite green.

---

## Notes for the implementer

- **Single source of truth for IDs.** Never duplicate the SHA-256 hashing logic. Findings use `linters.compute_id(prefix, title, locator)`; capabilities use the `-cap-` infix rule (mirrored in `canonicalize._capability_id`, which intentionally matches `linters.check_capability_id`'s expected-id computation). If you change one, change both and re-run `tests/test_canonicalize.py`.
- **`extract_records` lives in `validate.py`** and is imported by `canonicalize.py` and `check_ids_cmd`. `validate.py` imports only `linters` (no cycle). Do not move it into `canonicalize.py` — that would make `validate` depend on the fixer.
- **Glob safety.** `deduped-findings.yaml` does NOT match `*.findings.yaml` (the char before `findings.yaml` is `-`, not `.`), so the deduped corpus is excluded from both canonicalize and the envelope check automatically. `attack-path.findings.yaml` and `threat-model.findings.yaml` DO match the glob but contain only out-of-scope agents, so canonicalize leaves them untouched and the envelope check passes (they are already singular/bare).
- **Structural-only is load-bearing.** canonicalize must never edit `title`, `excerpt`, or `evidence`. Those are agent-controlled and enforced by `validate` + tightened prompts. `tests/test_canonicalize.py::test_canonicalize_is_structural_only` guards this.
