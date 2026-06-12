# Deterministic Field Ownership — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a deterministic Python assembler the *sole author* of every derived field (record IDs, `schema_version`) so specialist/evaluator/intake agents emit semantic content only and never fabricate a hash they cannot reliably compute.

**Architecture:** Agents author *content* (titles, evidence, severity, the structured inputs an id is derived from). The existing `apd-gauntlet canonicalize` command is extended to be the single "assembler" that computes/overwrites all derived IDs and injects `schema_version`. Schema makes `id`/`schema_version` optional-at-emission (tooling-computed); a new presence linter is the post-assembly backstop. Four ID families are migrated off agents: finding/capability (already script-authoritative on overwrite — stop the redundant emission), `tmeval-*` (currently agent-fabricated + unverified), `dimpr-*` (currently CLI-minted-then-pasted), and the intake asset-inventory `asset-/idn-/tb-` ids (currently agent-fabricated, never recomputed).

**Tech Stack:** Python 3 (`tools/apd_gauntlet/`), JSON Schema (Draft 2020-12, `schemas/`), pytest (`tests/`, `testpaths=["tests"]`, `addopts="-ra --strict-markers"`), ruff + mypy, Claude Code agent markdown (`.claude/agents/`), the `apd-finding-schema` skill (`.claude/skills/apd-finding-schema/SKILL.md`), the workflow runner (`.claude/workflows/apd-gauntlet.js`).

---

## Locked decisions (from brainstorming)

1. **Agents emit NO id.** For findings/capabilities the agent emits zero identity field. The assembler is the sole author. (No human-readable slug — there are no within-emission id references today; `cross_references`/`merged_from`/`linked_perspectives` are synthesizer-authored post-assembly.)
2. **Full scope.** Migrate finding/capability + `tmeval-*` + `dimpr-*` + intake asset-inventory ids, plus a deterministic-task register + an ADR codifying the authored-vs-derived contract.
3. **Extend `canonicalize`, don't rename it.** The command name `canonicalize` is referenced by the workflow runner, docs, and ~tests; keep the name, broaden its remit. Conceptually it is "the assembler."
4. **Version held at 1.7.0.** This is a contract change but the framework is held at 1.7.0 with run outputs out-of-band (see the remediation program). Record the change in `docs/schema-evolution.md` under 1.7.0; do not bump `__version__`. (Flagged as a checkpoint in Phase 5.)

## Current-state register (what this plan changes)

| Field / ID family | Authored today by | After this plan |
|---|---|---|
| `apath-*` (attack-path) | Python emitter `attack_path/findings.py` | unchanged ✅ already script |
| `merged-*` (dedup) | Python `apply.py` (apply-clusters) | unchanged ✅ already script |
| finding/cap `id` (`conf-`…`immut-`) | agent best-effort → `canonicalize` overwrites | **agent emits none**; `canonicalize` sole author (Phase 1) |
| `schema_version` on finding/cap | agent emits `1` → `canonicalize` `setdefault`s | **agent emits none**; `canonicalize` injects (Phase 1) |
| `tmeval-*` (threat-model-eval) | **agent computes the sha**; never recomputed | agent emits `tmeval_key`; `canonicalize` mints (Phase 2) |
| `dimpr-*` (domain-improvement) | agent calls `mint-improvement-id` CLI, pastes | agent emits none; `canonicalize` mints (Phase 3) |
| `asset-/idn-/tb-*` (intake inventory) | **agent fabricates** "from name+locator"; never recomputed | agent emits name+provenance, references by name; `canonicalize` mints + wires refs (Phase 4) |

**Already deterministic / already script (no work, documented in Phase 5 register):** run-directory scaffolding (`init_run.scaffold_run`), `.apd-run.yaml` authoring, `control_mappings` normalization (`canonicalize._normalize_control_mappings`), `cross_references` rewrite, NIST/ATT&CK/coverage rollups (`synthesis/rollup.py`), metrics (`synthesis/metrics.py`).

## Phase independence

Each phase below is an independently-mergeable PR that produces working, tested software on its own. Phases 2–4 depend on Phase 1's assembler hooks and schema-optionality groundwork but not on each other. **Phase 4 (asset-inventory) is the highest-risk** (it rewrites an intra-inventory reference graph and must run before specialists consume inventory ids); if it grows, split it into its own plan — the rest still ship.

Recommended merge order: **Phase 1 → Phase 5a (ADR only) → Phase 2 → Phase 3 → Phase 4 → Phase 5b (register + docs)**.

---

# Phase 1 — Finding/Capability id ownership

**Outcome:** Specialist agents emit findings/capabilities with no `id` and no `schema_version`; `canonicalize` injects both; a new presence linter guarantees every in-scope record has a valid id after assembly; schema accepts id-less specialist output.

## File Structure (Phase 1)

- Modify: `schemas/finding.schema.json` — drop `id`,`schema_version` from `required`; add `readOnly` markers.
- Modify: `schemas/capability.schema.json` — same.
- Modify: `tools/apd_gauntlet/linters.py` — add `check_id_present()`.
- Modify: `tools/apd_gauntlet/validate.py` — wire `check_id_present` into the semantic pass.
- Modify: `.claude/agents/apd-confidentiality.md` + 8 sibling lens agents — stop instructing id/schema_version emission.
- Modify: `.claude/skills/apd-finding-schema/SKILL.md` — envelope example + "IDs are tooling-canonicalized" section.
- Test: `tests/test_capability_schema.py`, `tests/test_canonicalize.py`, `tests/test_validate_edge_cases.py`, new `tests/test_id_presence.py`.

> Note: `canonicalize._recompute_ids_for_file` already sets `rec["id"]` when the record has none (it reads `old_id = rec.get("id")` → `None`, guards `if old_id:` before populating `id_map`, then unconditionally assigns `rec["id"] = new_id`). So **no canonicalize code change is needed** for id injection — verify with a test, then change the contract around it.

### Task 1.1: Schema accepts id-less / schema_version-less findings & capabilities

**Files:**
- Modify: `schemas/finding.schema.json:6-9` (the `required` array) and `:13-18` (properties)
- Modify: `schemas/capability.schema.json:6-9` and `:13-18`
- Test: `tests/test_finding_schema.py`, `tests/test_capability_schema.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_capability_schema.py`:

```python
def test_capability_without_id_or_schema_version_is_valid():
    """Agents emit content only; id + schema_version are tooling-injected."""
    import copy
    rec = copy.deepcopy(_MINIMAL_VALID_CAPABILITY)  # existing helper/fixture in this module
    rec.pop("id", None)
    rec.pop("schema_version", None)
    errors = _validate_capability(rec)  # existing module helper that returns a list
    assert errors == [], errors
```

Add the mirror to `tests/test_finding_schema.py`:

```python
def test_finding_without_id_or_schema_version_is_valid():
    import copy
    rec = copy.deepcopy(_MINIMAL_VALID_FINDING)
    rec.pop("id", None)
    rec.pop("schema_version", None)
    errors = _validate_finding(rec)
    assert errors == [], errors
```

If a module lacks `_MINIMAL_VALID_*`/`_validate_*` helpers, mirror the construction already used by that file's passing tests (load a fixture from `tests/fixtures/` and call the same validator the existing tests call). Do not invent a new validation entry point.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_capability_schema.py::test_capability_without_id_or_schema_version_is_valid tests/test_finding_schema.py::test_finding_without_id_or_schema_version_is_valid -v`
Expected: FAIL — `'id' is a required property` (and `'schema_version' is a required property`).

- [ ] **Step 3: Edit the schemas**

In `schemas/finding.schema.json`, change the `required` array from:

```json
  "required": [
    "schema_version", "id", "agent", "apd_tier", "apd_goal",
    "disposition", "severity", "confidence",
    "title", "summary", "detail",
    "evidence", "control_mappings", "recommendation"
  ],
```

to (remove `schema_version` and `id`):

```json
  "required": [
    "agent", "apd_tier", "apd_goal",
    "disposition", "severity", "confidence",
    "title", "summary", "detail",
    "evidence", "control_mappings", "recommendation"
  ],
```

Then mark the two properties as tooling-authored (intent signal; jsonschema does not enforce `readOnly`, but it documents the contract and is read by `extending-agents` docs):

```json
    "schema_version": { "type": "integer", "const": 1, "readOnly": true },
    "id": {
      "readOnly": true,
      "type": "string",
      "pattern": "^(conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged|tmeval|apath)-[0-9a-f]{8}$"
    },
```

In `schemas/capability.schema.json`, change `required` from:

```json
  "required": [
    "schema_version", "id", "agent", "apd_tier", "apd_goal",
    "title", "description", "maturity", "scope",
    "evidence", "control_mappings"
  ],
```

to:

```json
  "required": [
    "agent", "apd_tier", "apd_goal",
    "title", "description", "maturity", "scope",
    "evidence", "control_mappings"
  ],
```

and add `"readOnly": true` to its `schema_version` and `id` properties exactly as above (keep the capability `id` pattern unchanged: `^((conf|intg|avail|dist|resil|ephem|auth|nonrep|immut|merged)-cap|cap-merged)-[0-9a-f]{8}$`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_capability_schema.py tests/test_finding_schema.py -v`
Expected: PASS (including all pre-existing tests — `id`/`schema_version` are still format-validated *when present*).

- [ ] **Step 5: Commit**

```bash
git add schemas/finding.schema.json schemas/capability.schema.json tests/test_finding_schema.py tests/test_capability_schema.py
git commit -m "feat(schema): make finding/capability id + schema_version tooling-authored (optional at emission)"
```

### Task 1.2: Verify canonicalize injects id + schema_version for an id-less record

**Files:**
- Test: `tests/test_canonicalize.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_canonicalize.py` (reuse the module's `_finding` helper and `tmp_path` run-dir pattern already used by neighboring tests):

```python
def test_canonicalize_injects_id_and_schema_version_when_absent(tmp_path):
    rec = _finding()                      # existing helper builds a valid finding dict
    rec.pop("id", None)
    rec.pop("schema_version", None)
    run_dir = tmp_path
    (run_dir / "10-trustworthiness").mkdir(parents=True)
    path = run_dir / "10-trustworthiness" / "confidentiality.findings.yaml"
    path.write_text(yaml.safe_dump({"finding": [rec]}, sort_keys=False), encoding="utf-8")

    from tools.apd_gauntlet.canonicalize import canonicalize_run
    canonicalize_run(run_dir)

    out = yaml.safe_load(path.read_text(encoding="utf-8"))["finding"][0]
    assert out["schema_version"] == 1
    assert out["id"].startswith("conf-") and len(out["id"]) == len("conf-") + 8
```

(Import `yaml` at the top if not already imported in this test module.)

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python -m pytest tests/test_canonicalize.py::test_canonicalize_injects_id_and_schema_version_when_absent -v`
Expected: PASS immediately (canonicalize already injects). If it FAILS, the assembler is not injecting on absent id — fix `canonicalize._recompute_ids_for_file` so `rec["id"]` is assigned even when `old_id is None` (it already is) before continuing.

- [ ] **Step 3: Commit (characterization test)**

```bash
git add tests/test_canonicalize.py
git commit -m "test(canonicalize): characterize id + schema_version injection for id-less records"
```

### Task 1.3: Add `check_id_present` presence backstop

**Files:**
- Modify: `tools/apd_gauntlet/linters.py` (add function near `check_finding_id`, ~line 130)
- Modify: `tools/apd_gauntlet/validate.py:457-510` (`run_semantic_pass`)
- Test: new `tests/test_id_presence.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_id_presence.py`:

```python
from tools.apd_gauntlet.linters import check_id_present


def _rec(**kw):
    base = {
        "agent": "confidentiality",
        "title": "KMS key rotation absent",
        "evidence": [{"artifact": "tech_plan.md", "locator": "L42", "excerpt": "no rotation"}],
    }
    base.update(kw)
    return base


def test_in_scope_record_missing_id_is_flagged():
    msgs = check_id_present(_rec())  # no 'id'
    assert msgs and "missing tooling-authored id" in msgs[0]


def test_in_scope_record_with_id_passes():
    assert check_id_present(_rec(id="conf-1a2b3c4d")) == []


def test_out_of_scope_agent_is_not_flagged():
    # attack_path / threat_model id families are minted by their own flows
    assert check_id_present(_rec(agent="attack_path_analyzer")) == []


def test_record_without_evidence_is_not_flagged():
    # no first-evidence locator => no deterministic id is computable; not our job to flag here
    assert check_id_present(_rec(evidence=[])) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_id_presence.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_id_present'`.

- [ ] **Step 3: Implement `check_id_present`**

In `tools/apd_gauntlet/linters.py`, add (after `check_capability_id`):

```python
def check_id_present(record: dict[str, Any]) -> list[str]:
    """Post-assembly backstop: every in-scope record MUST carry a tooling-authored id.

    In-scope == the nine specialist lenses (``_PREFIX_BY_AGENT``). Records with no
    first-evidence locator are skipped (no deterministic id is computable for them;
    they are caught elsewhere). attack_path / threat_model_evaluator records are
    out of scope here — their ids are minted by their own assembler passes.
    """
    agent = record.get("agent") or ""
    if agent not in _PREFIX_BY_AGENT:
        return []
    evidence = record.get("evidence") or []
    if not evidence or not evidence[0].get("locator"):
        return []
    if not record.get("id"):
        return [
            "missing tooling-authored id: run `apd-gauntlet canonicalize <run-dir>` "
            "before validate (the assembler is the sole author of id)"
        ]
    return []
```

- [ ] **Step 4: Wire into the semantic pass**

In `tools/apd_gauntlet/validate.py`, inside `run_semantic_pass`, where it already iterates records and calls `linters.check_finding_id` / `linters.check_capability_id` (~lines 481 and 496), add a presence check for both kinds. Locate the per-record loop and add, alongside the existing `for msg in linters.check_finding_id(record):` block:

```python
            for msg in linters.check_id_present(record):
                report.errors.append(Violation(path, record.get("id", "<no-id>"), msg))
```

Add the identical block in the capability branch (next to `linters.check_capability_id`). Match the exact `Violation(...)` constructor arity used by the surrounding lines in this file.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_id_presence.py tests/test_validate_edge_cases.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/linters.py tools/apd_gauntlet/validate.py tests/test_id_presence.py
git commit -m "feat(validate): add check_id_present backstop (in-scope records require assembler-authored id)"
```

### Task 1.4: Stop instructing agents to emit id / schema_version (9 lens agents + skill)

**Files:**
- Modify: `.claude/agents/apd-confidentiality.md`, `.claude/agents/apd-integrity.md`, `.claude/agents/apd-availability.md`, `.claude/agents/apd-distributed.md`, `.claude/agents/apd-resilient.md`, `.claude/agents/apd-ephemeral.md`, `.claude/agents/apd-authenticity.md`, `.claude/agents/apd-non-repudiation.md`, `.claude/agents/apd-immutability.md`
- Modify: `.claude/skills/apd-finding-schema/SKILL.md`
- Test: new `tests/test_agent_prompt_id_contract.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agent_prompt_id_contract.py`:

```python
import pathlib

AGENTS_DIR = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "agents"
LENS_AGENTS = [
    "apd-confidentiality.md", "apd-integrity.md", "apd-availability.md",
    "apd-distributed.md", "apd-resilient.md", "apd-ephemeral.md",
    "apd-authenticity.md", "apd-non-repudiation.md", "apd-immutability.md",
]


def test_lens_agents_do_not_instruct_best_effort_id():
    offenders = []
    for name in LENS_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8").lower()
        if "best-effort `id`" in text or "best-effort id" in text:
            offenders.append(name)
    assert offenders == [], f"these agents still tell the model to author an id: {offenders}"


def test_lens_agents_state_assembler_owns_id():
    missing = []
    for name in LENS_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8")
        if "do NOT emit" not in text or "id" not in text:
            missing.append(name)
    assert missing == [], f"these agents lack the do-not-emit-id contract line: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agent_prompt_id_contract.py -v`
Expected: FAIL — each lens agent currently contains "author a best-effort `id`".

- [ ] **Step 3: Edit each lens agent**

In each of the 9 files, replace the existing two-line passage (verbatim string differs only by surrounding prose — the shared sentence is):

```
are the canonical non-tech-plan source. IDs are tooling-canonicalized — author
a best-effort `id` and do not hand-tune it.
```

with:

```
are the canonical non-tech-plan source. Do NOT emit an `id` or `schema_version`
field — the assembler (`apd-gauntlet canonicalize`) is the sole author of both.
Emit each record WITHOUT them; the tooling injects them deterministically.
```

Also, where each agent's envelope text says `Each record carries `schema_version: 1`.` (e.g. `apd-confidentiality.md:38`, `apd-integrity.md:27`), replace with:

```
Each record is emitted WITHOUT `schema_version` or `id` — the assembler injects them.
```

- [ ] **Step 4: Edit the skill**

In `.claude/skills/apd-finding-schema/SKILL.md`, update the canonical envelope example (the `finding:` YAML block ~line 35) to drop `schema_version`/`id` from the emitted record and add a comment, and rewrite the "IDs are tooling-canonicalized" paragraph (~line 50). New envelope block:

```yaml
finding:                      # singular — never the plural 'findings:'
  - agent: confidentiality    # NO id, NO schema_version — the assembler injects both
    # ... rest of the record, BARE (not wrapped) ...
  - agent: confidentiality
    # ... second record ...
```

New paragraph (replacing the "**IDs are tooling-canonicalized.**" block):

```markdown
**IDs are tooling-authored.** Do **not** emit `id` or `schema_version`.
`apd-gauntlet canonicalize` is the sole author: it injects `schema_version: 1`
and computes `id` deterministically (`<shortcode>-<sha8(title|first-evidence-locator)>`,
with a `-cap-` infix for capabilities) and rewrites `cross_references` to match.
Emitting an `id` yourself is ignored (overwritten) and now flagged by lint.
```

Also update the two schema blocks further down (`id: <agent-shortcode>-<sha8>` and `id: <agent-shortcode>-cap-<sha8>`) to read `# (tooling-authored — do not emit)` on the `id` line, and the §"Validation checklist" item "ID computed correctly per the algorithm above" to "ID is **absent** in agent output (the assembler authors it)".

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_agent_prompt_id_contract.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/agents/apd-*.md .claude/skills/apd-finding-schema/SKILL.md tests/test_agent_prompt_id_contract.py
git commit -m "docs(agents): specialists emit content only — assembler authors id + schema_version"
```

### Task 1.5: Phase 1 full verification

- [ ] **Step 1: Run the whole suite + linters**

Run:
```bash
python -m pytest tests -q
ruff check tools/ tests/
mypy tools/apd_gauntlet
```
Expected: all PASS / clean. If any pre-existing specialist *fixture* under `tests/fixtures/` or `examples/` lost a required field, note it — those files are post-assembly artifacts and still carry ids, so they remain valid (id optional, not forbidden). Do not strip ids from committed example runs.

- [ ] **Step 2: Run the markdownlint glob (CI parity)**

Run: `npx markdownlint-cli docs/**/*.md .claude/**/*.md 2>/dev/null || true` (mirror the exact CI invocation in `.github/workflows/`; fix any new MD0xx the edited skill/agents introduced — wrap long lines, keep list style consistent).

- [ ] **Step 3: Commit any lint fixups**

```bash
git add -A
git commit -m "chore: phase-1 lint/format fixups"
```

---

# Phase 2 — `tmeval-*` deterministic minting

**Outcome:** The threat-model-evaluator emits a structured `tmeval_key` (flavor + the components the id is derived from) and NO `id`; `canonicalize` mints `tmeval-<sha8>` from that key; a `check_tmeval_id` linter verifies it.

## File Structure (Phase 2)

- Modify: `tools/apd_gauntlet/linters.py` — add `compute_tmeval_id()`, `check_tmeval_id()`.
- Modify: `tools/apd_gauntlet/canonicalize.py` — mint tmeval ids inside `_recompute_ids_for_file`.
- Modify: `schemas/finding.schema.json` — add optional `tmeval_key` property.
- Modify: `tools/apd_gauntlet/validate.py` — wire `check_tmeval_id` into the semantic pass.
- Modify: `.claude/agents/apd-threat-model-evaluator.md` — emit `tmeval_key`, not `id`.
- Test: new `tests/test_tmeval_id.py`; extend `tests/test_canonicalize.py`.

### Task 2.1: `compute_tmeval_id` helper + flavor canonical forms

**Files:**
- Modify: `tools/apd_gauntlet/linters.py`
- Test: new `tests/test_tmeval_id.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tmeval_id.py`:

```python
import hashlib
import pytest
from tools.apd_gauntlet.linters import compute_tmeval_id


def _sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def test_supplied_omission_form():
    key = {"flavor": "supplied_omission", "tm_entry_id": "tm-7"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("supplied_omission|tm-7")


def test_coverage_gap_form():
    key = {"flavor": "coverage_gap", "surface": "ingest-api", "goal": "confidentiality"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("coverage_gap|ingest-api|confidentiality")


def test_contradiction_form():
    key = {"flavor": "contradiction", "tm_entry_id": "tm-3", "contradicting_finding_id": "conf-aabbccdd"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("contradiction|tm-3|conf-aabbccdd")


def test_silence_form():
    key = {"flavor": "silence", "surface": "worker"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("silence|worker")


def test_blocked_form():
    key = {"flavor": "blocked", "source_artifact": "inputs/tm.md"}
    assert compute_tmeval_id(key) == "tmeval-" + _sha8("blocked|inputs/tm.md")


def test_unknown_flavor_raises():
    with pytest.raises(ValueError):
        compute_tmeval_id({"flavor": "nope"})


def test_missing_component_raises():
    with pytest.raises(ValueError):
        compute_tmeval_id({"flavor": "coverage_gap", "surface": "x"})  # missing goal
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tmeval_id.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_tmeval_id'`.

- [ ] **Step 3: Implement the helper**

In `tools/apd_gauntlet/linters.py`, add (near `compute_improvement_id`):

```python
# Per-flavor ordered component keys. The id is sha8 over
# "<flavor>|<component-1>|<component-2>..." — flavor first, uniform shape.
_TMEVAL_COMPONENTS: dict[str, tuple[str, ...]] = {
    "supplied_omission": ("tm_entry_id",),
    "coverage_gap": ("surface", "goal"),
    "contradiction": ("tm_entry_id", "contradicting_finding_id"),
    "silence": ("surface",),
    "blocked": ("source_artifact",),
}


def compute_tmeval_id(key: dict[str, Any]) -> str:
    """Deterministic tmeval- id from a structured flavor key (replaces the
    agent-computed sha). Raises ValueError on unknown flavor or a missing
    component so a malformed key fails loud instead of minting a garbage id."""
    flavor = key.get("flavor", "")
    components = _TMEVAL_COMPONENTS.get(flavor)
    if components is None:
        raise ValueError(f"unknown tmeval flavor {flavor!r}")
    parts = [flavor]
    for name in components:
        val = key.get(name)
        if not val:
            raise ValueError(f"tmeval flavor {flavor!r} requires component {name!r}")
        parts.append(str(val))
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:8]
    return f"tmeval-{digest}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tmeval_id.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/linters.py tests/test_tmeval_id.py
git commit -m "feat(linters): compute_tmeval_id — deterministic tmeval- id from structured flavor key"
```

### Task 2.2: `tmeval_key` schema property

**Files:**
- Modify: `schemas/finding.schema.json` (add property; `additionalProperties:false` requires it be declared)
- Test: `tests/test_finding_schema.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_finding_schema.py`:

```python
def test_finding_accepts_tmeval_key():
    import copy
    rec = copy.deepcopy(_MINIMAL_VALID_FINDING)
    rec.pop("id", None)
    rec["agent"] = "threat_model_evaluator"
    rec["tmeval_key"] = {"flavor": "coverage_gap", "surface": "ingest-api", "goal": "confidentiality"}
    assert _validate_finding(rec) == [], _validate_finding(rec)


def test_finding_rejects_unknown_tmeval_flavor():
    import copy
    rec = copy.deepcopy(_MINIMAL_VALID_FINDING)
    rec["tmeval_key"] = {"flavor": "bogus"}
    assert _validate_finding(rec) != []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_finding_schema.py::test_finding_accepts_tmeval_key tests/test_finding_schema.py::test_finding_rejects_unknown_tmeval_flavor -v`
Expected: FAIL — `Additional properties are not allowed ('tmeval_key' was unexpected)`.

- [ ] **Step 3: Add the property**

In `schemas/finding.schema.json`, inside `properties` (e.g. after `merged_from`), add:

```json
    "tmeval_key": {
      "type": "object",
      "additionalProperties": false,
      "required": ["flavor"],
      "properties": {
        "flavor": {
          "type": "string",
          "enum": ["supplied_omission", "coverage_gap", "contradiction", "silence", "blocked"]
        },
        "tm_entry_id": { "type": "string" },
        "surface": { "type": "string" },
        "goal": { "type": "string" },
        "contradicting_finding_id": { "type": "string" },
        "source_artifact": { "type": "string" }
      }
    },
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_finding_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/finding.schema.json tests/test_finding_schema.py
git commit -m "feat(schema): add optional tmeval_key (assembler mints tmeval- id from it)"
```

### Task 2.3: Mint tmeval ids in the assembler

**Files:**
- Modify: `tools/apd_gauntlet/canonicalize.py:127-185` (`_recompute_ids_for_file`)
- Test: `tests/test_canonicalize.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_canonicalize.py`:

```python
def test_canonicalize_mints_tmeval_id_from_key(tmp_path):
    import hashlib
    from tools.apd_gauntlet.canonicalize import canonicalize_run
    rec = {
        "agent": "threat_model_evaluator",
        "apd_tier": "trustworthiness", "apd_goal": "confidentiality",
        "disposition": "gap", "severity": "medium", "confidence": "medium",
        "title": "Threat model omits Confidentiality analysis for ingest-api",
        "summary": "s", "detail": "d",
        "tmeval_key": {"flavor": "coverage_gap", "surface": "ingest-api", "goal": "confidentiality"},
        "evidence": [{"artifact": "00-context/threat-model-normalized.yaml",
                      "locator": "entries[asset=ingest-api]", "excerpt": "x"}],
        "control_mappings": {"nist_800_53r5": ["SC-7"]},
        "recommendation": {"posture": "recommended", "summary": "s", "detail": "d"},
    }
    d = tmp_path / "40-threat-model"
    d.mkdir(parents=True)
    p = d / "threat-model.findings.yaml"
    p.write_text(yaml.safe_dump({"finding": [rec]}, sort_keys=False), encoding="utf-8")

    canonicalize_run(tmp_path)

    out = yaml.safe_load(p.read_text(encoding="utf-8"))["finding"][0]
    want = "tmeval-" + hashlib.sha256("coverage_gap|ingest-api|confidentiality".encode()).hexdigest()[:8]
    assert out["id"] == want
    assert out["schema_version"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_canonicalize.py::test_canonicalize_mints_tmeval_id_from_key -v`
Expected: FAIL — `KeyError: 'id'` (file left untouched: `threat_model_evaluator` is out of scope today).

- [ ] **Step 3: Implement minting in `_recompute_ids_for_file`**

In `tools/apd_gauntlet/canonicalize.py`, add the import:

```python
from .linters import _PREFIX_BY_AGENT, compute_capability_id, compute_id, compute_tmeval_id
```

Then in `_recompute_ids_for_file`, *before* the `prefix = _PREFIX_BY_AGENT.get(...)` line, insert a tmeval branch (so it runs for `root_key == "finding"` files holding evaluator records):

```python
        # tmeval-* ids are minted from the record's structured tmeval_key, not
        # from title|locator. Handled here because threat_model_evaluator has no
        # _PREFIX_BY_AGENT entry (the generic prefix path would skip it).
        if rec.get("agent") == "threat_model_evaluator" and root_key == "finding":
            key = rec.get("tmeval_key")
            if key:
                new_id = compute_tmeval_id(key)
                in_scope += 1
                old_id = rec.get("id")
                if new_id in seen_new_ids:
                    raise CanonicalizeCollision(
                        f"tmeval id collision on {new_id!r} in {path}"
                    )
                seen_new_ids.add(new_id)
                if old_id != new_id:
                    n_changed += 1
                if old_id:
                    id_map[old_id] = new_id
                rec["id"] = new_id
            continue  # do not fall through to the prefix path
```

(Place this immediately after the `rec.setdefault("schema_version", 1)` line so tmeval records also get `schema_version`.)

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_canonicalize.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/canonicalize.py tests/test_canonicalize.py
git commit -m "feat(canonicalize): mint tmeval- ids from tmeval_key (assembler is sole author)"
```

### Task 2.4: `check_tmeval_id` linter + wire-in

**Files:**
- Modify: `tools/apd_gauntlet/linters.py`
- Modify: `tools/apd_gauntlet/validate.py` (semantic pass)
- Test: `tests/test_tmeval_id.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_tmeval_id.py`:

```python
from tools.apd_gauntlet.linters import check_tmeval_id


def test_check_tmeval_id_passes_when_consistent():
    key = {"flavor": "silence", "surface": "worker"}
    rec = {"agent": "threat_model_evaluator", "tmeval_key": key, "id": compute_tmeval_id(key)}
    assert check_tmeval_id(rec) == []


def test_check_tmeval_id_flags_mismatch():
    key = {"flavor": "silence", "surface": "worker"}
    rec = {"agent": "threat_model_evaluator", "tmeval_key": key, "id": "tmeval-00000000"}
    assert check_tmeval_id(rec) != []


def test_check_tmeval_id_ignores_non_tmeval():
    assert check_tmeval_id({"agent": "confidentiality", "id": "conf-12345678"}) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_tmeval_id.py -k check_tmeval -v`
Expected: FAIL — `cannot import name 'check_tmeval_id'`.

- [ ] **Step 3: Implement + wire**

In `linters.py`:

```python
def check_tmeval_id(record: dict[str, Any]) -> list[str]:
    """tmeval- id must equal compute_tmeval_id(record['tmeval_key'])."""
    if record.get("agent") != "threat_model_evaluator":
        return []
    key = record.get("tmeval_key")
    if not key:
        return ["threat_model_evaluator record missing tmeval_key (assembler needs it to mint the id)"]
    try:
        expected = compute_tmeval_id(key)
    except ValueError as exc:
        return [f"invalid tmeval_key: {exc}"]
    actual = record.get("id", "")
    if actual != expected:
        return [f"id mismatch: got {actual}, expected {expected} per tmeval deterministic rule"]
    return []
```

In `validate.py` `run_semantic_pass`, in the finding branch (next to `check_finding_id`), add:

```python
            for msg in linters.check_tmeval_id(record):
                report.errors.append(Violation(path, record.get("id", "<no-id>"), msg))
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_tmeval_id.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/linters.py tools/apd_gauntlet/validate.py tests/test_tmeval_id.py
git commit -m "feat(validate): check_tmeval_id verifies assembler-minted tmeval- ids"
```

### Task 2.5: Update the evaluator agent to emit `tmeval_key`, not `id`

**Files:**
- Modify: `.claude/agents/apd-threat-model-evaluator.md`
- Test: new `tests/test_tmeval_agent_contract.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tmeval_agent_contract.py`:

```python
import pathlib
P = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "agents" / "apd-threat-model-evaluator.md"


def test_evaluator_does_not_hand_compute_sha():
    text = P.read_text(encoding="utf-8")
    assert "sha over" not in text, "evaluator must NOT instruct hand-computing the tmeval sha"


def test_evaluator_emits_tmeval_key():
    text = P.read_text(encoding="utf-8")
    assert "tmeval_key" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_tmeval_agent_contract.py -v`
Expected: FAIL — the file currently contains "sha over …" comments and no `tmeval_key`.

- [ ] **Step 3: Rewrite the 5 record templates**

In `.claude/agents/apd-threat-model-evaluator.md`, for each of the 5 flavor templates (lines ~138, 185, 226, 266, 308), replace the `id: tmeval-<sha8>   # sha over …` line with a `tmeval_key` block and remove the `id` line. Mapping:

- supplied_omission template →
  ```yaml
  tmeval_key:
    flavor: supplied_omission
    tm_entry_id: <baseline tm_entry_id>
  ```
- coverage_gap template →
  ```yaml
  tmeval_key:
    flavor: coverage_gap
    surface: <surface>
    goal: <the absent goal>
  ```
- contradiction template →
  ```yaml
  tmeval_key:
    flavor: contradiction
    tm_entry_id: <tm_entry_id>
    contradicting_finding_id: <specialist finding id>
  ```
- silence template →
  ```yaml
  tmeval_key:
    flavor: silence
    surface: <surface>
  ```
- blocked template (Step 7) →
  ```yaml
  tmeval_key:
    flavor: blocked
    source_artifact: <supplied threat-model path under inputs/>
  ```

Update the agent's prose (lines ~10, 47) from "`id: tmeval-<sha8>` (8 hex chars after the prefix)" to: "Do NOT emit `id` — emit a `tmeval_key` (flavor + components); `apd-gauntlet canonicalize` mints `tmeval-<sha8>` from it."

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_tmeval_agent_contract.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-threat-model-evaluator.md tests/test_tmeval_agent_contract.py
git commit -m "docs(evaluator): emit tmeval_key, not a hand-computed tmeval- id"
```

### Task 2.6: Phase 2 verification

- [ ] **Step 1: Full suite + linters**

Run:
```bash
python -m pytest tests -q
ruff check tools/ tests/
mypy tools/apd_gauntlet
```
Expected: clean. Confirm the workflow runner already runs `canonicalize` over the whole run before the `tmeval` phase's validate — the `tmeval` phase writes `40-threat-model/threat-model.findings.yaml`, so add a `canonicalize` invocation after the `tmeval` llmStep in `.claude/workflows/apd-gauntlet.js` (mirror the per-tier `pyStep('canonicalize', …)` block) **and** before any validate that runs `check_tmeval_id`.

- [ ] **Step 2: Wire canonicalize after the tmeval phase**

In `.claude/workflows/apd-gauntlet.js`, locate `phase('tmeval')` (the tmeval llmStep) and add immediately after it:

```js
pyStep('canonicalize', {
  phase: 'tmeval', label: 'canonicalize-tmeval',
  outputs: 'tmeval- ids minted under ' + runDir + '/40-threat-model/',
  alwaysRun: true,
});
```

- [ ] **Step 3: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js
git commit -m "feat(workflow): canonicalize after tmeval phase to mint tmeval- ids"
```

---

# Phase 3 — `dimpr-*` folding

**Outcome:** The domain-auditor emits domain-improvement records with no `id`; `canonicalize` mints `dimpr-<sha8>` from the record's own fields (the existing `compute_improvement_id` 4-tuple). The `mint-improvement-id` CLI stays for manual use; the existing validate recompute pass becomes a backstop.

## File Structure (Phase 3)

- Modify: `tools/apd_gauntlet/canonicalize.py` — add `_mint_dimpr_ids()` + call from `canonicalize_run`.
- Modify: `schemas/domain-improvement.schema.json` — drop `id` from `required` (verify it is currently required).
- Modify: `.claude/agents/apd-domain-auditor.md` — stop minting via CLI; emit content.
- Modify: `.claude/workflows/apd-gauntlet.js` — canonicalize after the domain-auditor phase.
- Test: `tests/test_canonicalize.py` (new dimpr case), `tests/test_domain_improvement_schema.py`.

### Task 3.1: Mint dimpr ids in the assembler

**Files:**
- Modify: `tools/apd_gauntlet/canonicalize.py`
- Modify: `schemas/domain-improvement.schema.json`
- Test: `tests/test_canonicalize.py`

- [ ] **Step 1: Confirm current schema requires `id`**

Run: `grep -n '"required"' schemas/domain-improvement.schema.json`
Expected: an array including `"id"`. (If `id` is not required, skip the schema edit in Step 4.)

- [ ] **Step 2: Write the failing test**

Add to `tests/test_canonicalize.py`:

```python
def test_canonicalize_mints_dimpr_id(tmp_path):
    from tools.apd_gauntlet.canonicalize import canonicalize_run
    from tools.apd_gauntlet.linters import compute_improvement_id
    rec = {
        "improvement_type": "consequential_action",
        "target_pack": "agentic-ai",
        "target_file": "domain.yaml",
        "summary": "Add tool-call audit action",
        "detail": "d",
        "draft_snippet": "x",
        "evidence": [{"ref": "conf-12345678", "note": "n"}],
    }
    d = tmp_path / "40-synthesis"
    d.mkdir(parents=True)
    p = d / "domain-improvements.yaml"
    p.write_text(yaml.safe_dump({"domain_improvement": [rec]}, sort_keys=False), encoding="utf-8")

    canonicalize_run(tmp_path)

    out = yaml.safe_load(p.read_text(encoding="utf-8"))["domain_improvement"][0]
    assert out["id"] == compute_improvement_id("consequential_action", "agentic-ai", "domain.yaml", "conf-12345678")
```

(Confirm the singular root key by reading `schemas/domain-improvements-doc.schema.json`; adjust `"domain_improvement"` to match the actual root key the doc uses.)

- [ ] **Step 3: Run to verify it fails**

Run: `python -m pytest tests/test_canonicalize.py::test_canonicalize_mints_dimpr_id -v`
Expected: FAIL — `domain-improvements.yaml` is not in `_KINDS`, so canonicalize ignores it (`KeyError: 'id'`).

- [ ] **Step 4: Implement `_mint_dimpr_ids` + call it**

In `tools/apd_gauntlet/canonicalize.py`, add the import:

```python
from .linters import (
    _PREFIX_BY_AGENT, compute_capability_id, compute_id,
    compute_improvement_id, compute_tmeval_id,
)
```

Add the function:

```python
def _mint_dimpr_ids(run_dir: Path) -> int:
    """Mint dimpr-<sha8> for every record in 40-synthesis/domain-improvements.yaml
    from its own 4-tuple (improvement_type|target_pack|target_file|evidence[0].ref).
    Idempotent; no-op when the file is absent. Returns records changed."""
    path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    if not path.exists():
        return 0
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return 0
    root_key = next(iter(doc), "domain_improvement")
    records = doc.get(root_key) or []
    changed = 0
    for rec in records:
        evidence = rec.get("evidence") or []
        primary_ref = evidence[0].get("ref", "") if evidence else ""
        new_id = compute_improvement_id(
            rec.get("improvement_type", ""), rec.get("target_pack", ""),
            rec.get("target_file", ""), primary_ref,
        )
        rec.setdefault("schema_version", 1)
        if rec.get("id") != new_id:
            changed += 1
        rec["id"] = new_id
    if changed or records:
        path.write_text(
            yaml.safe_dump({root_key: records}, sort_keys=False, allow_unicode=True, width=4096),
            encoding="utf-8",
        )
    return changed
```

Call it at the end of `canonicalize_run`, before `return CanonicalizeResult(...)`:

```python
    records_canonicalized += _mint_dimpr_ids(run_dir)
```

- [ ] **Step 5: Edit the schema (if Step 1 showed `id` required)**

In `schemas/domain-improvement.schema.json`, remove `"id"` from the `required` array; add `"readOnly": true` to the `id` property.

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/test_canonicalize.py tests/test_domain_improvement_schema.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/canonicalize.py schemas/domain-improvement.schema.json tests/test_canonicalize.py tests/test_domain_improvement_schema.py
git commit -m "feat(canonicalize): mint dimpr- ids from record fields (fold the manual mint step)"
```

### Task 3.2: Domain-auditor emits content, not a minted id

**Files:**
- Modify: `.claude/agents/apd-domain-auditor.md`
- Modify: `.claude/workflows/apd-gauntlet.js`
- Test: new `tests/test_domain_auditor_contract.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_domain_auditor_contract.py`:

```python
import pathlib
P = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "agents" / "apd-domain-auditor.md"


def test_domain_auditor_does_not_mint_id_itself():
    text = P.read_text(encoding="utf-8")
    assert "mint-improvement-id" not in text or "assembler" in text.lower(), \
        "domain-auditor should emit content; the assembler mints dimpr- ids"
    assert "do NOT emit" in text and "id" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_domain_auditor_contract.py -v`
Expected: FAIL — current text instructs computing the id via the CLI (lines ~113-121).

- [ ] **Step 3: Rewrite the id step (lines ~113-121)**

Replace the "**Compute the dimpr- id** with the deterministic CLI …" block with:

```markdown
4. **Do NOT emit or compute the `id`.** Emit each domain-improvement record with
   its content fields (`improvement_type`, `target_pack`, `target_file`,
   `evidence[].ref`, `summary`, `detail`, `draft_snippet`) and NO `id`. The
   assembler (`apd-gauntlet canonicalize`) mints the canonical `dimpr-<sha8>` from
   those fields. (`apd-gauntlet mint-improvement-id` remains available for manual
   inspection only.) Dedup identical opportunities by their (improvement_type,
   target_pack, target_file, primary ref) tuple before emitting — the assembler
   will collapse exact duplicates to the same id.
```

In `.claude/workflows/apd-gauntlet.js`, after the domain-auditor / domain-improvements phase, add a canonicalize invocation (mirror Task 2.2's block, label `canonicalize-dimpr`).

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_domain_auditor_contract.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/apd-domain-auditor.md .claude/workflows/apd-gauntlet.js tests/test_domain_auditor_contract.py
git commit -m "docs(domain-auditor): emit content; assembler mints dimpr- ids"
```

### Task 3.3: Phase 3 verification

- [ ] **Step 1:** Run `python -m pytest tests -q && ruff check tools/ tests/ && mypy tools/apd_gauntlet`. Expected: clean.
- [ ] **Step 2:** Commit any fixups: `git commit -am "chore: phase-3 fixups"`.

---

# Phase 4 — Intake asset-inventory id minting (HIGHEST RISK)

**Outcome:** Intake emits `assets`/`identities`/`trust_boundaries` with names + provenance and **no** ids, referencing `trust_boundaries.crosses` by asset **name**; a new assembler pass mints `asset-/idn-/tb-<sha8>` and rewrites `crosses` name→id. This must run in the intake phase, **before specialists** cite inventory ids in evidence.

> **Risk note:** Inventory ids are consumed downstream as evidence refs (`kind: asset_inventory`, `validate.py:646`), by attack-path `realizes_crown_jewels`, and by `trust_boundaries.crosses`. They MUST be final before specialists run. Because intake runs first, minting immediately after intake keeps them stable. If reference-rewiring grows beyond `crosses`, split this phase into its own plan.

## File Structure (Phase 4)

- Modify: `tools/apd_gauntlet/linters.py` — `compute_asset_id`, `compute_identity_id`, `compute_boundary_id`.
- Create: `tools/apd_gauntlet/assemble_inventory.py` — `assemble_inventory(run_dir)`.
- Modify: `tools/apd_gauntlet/cli.py` — register `assemble-inventory` (or fold into `canonicalize`).
- Modify: `schemas/asset-inventory.schema.json` — make `asset_id`/`identity_id`/`boundary_id` optional at emission; allow `crosses` items to be names pre-assembly (see Step decisions).
- Modify: `.claude/agents/apd-intake.md` — emit names, reference by name, no ids.
- Modify: `.claude/workflows/apd-gauntlet.js` — run the inventory assembler in the intake phase.
- Test: new `tests/test_assemble_inventory.py`; extend `tests/test_intake*`.

### Task 4.1: Inventory id minters

**Files:**
- Modify: `tools/apd_gauntlet/linters.py`
- Test: new `tests/test_assemble_inventory.py`

- [ ] **Step 1: Read provenance shape**

Run: `sed -n '1,90p' schemas/asset-inventory.schema.json`
Note the `provenance` object's fields (e.g. `artifact`, `locator`). The asset id input is `name|<provenance.locator>` — confirm the exact key name before writing the helper.

- [ ] **Step 2: Write the failing test**

Create `tests/test_assemble_inventory.py`:

```python
import hashlib
from tools.apd_gauntlet.linters import compute_asset_id, compute_identity_id, compute_boundary_id


def _sha8(s): return hashlib.sha256(s.encode()).hexdigest()[:8]


def test_asset_id_deterministic():
    assert compute_asset_id("Postgres PHI store", "tech_plan.md#L10") == "asset-" + _sha8("Postgres PHI store|tech_plan.md#L10")


def test_identity_id_deterministic():
    assert compute_identity_id("worker-sa", "iac/sa.yaml#L3") == "idn-" + _sha8("worker-sa|iac/sa.yaml#L3")


def test_boundary_id_deterministic():
    assert compute_boundary_id("dmz->app", "diagram.md#L5") == "tb-" + _sha8("dmz->app|diagram.md#L5")
```

- [ ] **Step 3: Run to verify it fails**

Run: `python -m pytest tests/test_assemble_inventory.py -v`
Expected: FAIL — import errors.

- [ ] **Step 4: Implement the minters**

In `tools/apd_gauntlet/linters.py`:

```python
def _inventory_id(prefix: str, name: str, locator: str) -> str:
    digest = hashlib.sha256(f"{name}|{locator}".encode()).hexdigest()[:8]
    return f"{prefix}-{digest}"


def compute_asset_id(name: str, locator: str) -> str:
    """Deterministic asset- id: asset-<sha8(name|provenance-locator)>."""
    return _inventory_id("asset", name, locator)


def compute_identity_id(name: str, locator: str) -> str:
    return _inventory_id("idn", name, locator)


def compute_boundary_id(name: str, locator: str) -> str:
    return _inventory_id("tb", name, locator)
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_assemble_inventory.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/linters.py tests/test_assemble_inventory.py
git commit -m "feat(linters): deterministic asset-/idn-/tb- inventory id minters"
```

### Task 4.2: `assemble_inventory` — mint ids + rewrite `crosses` by name

**Files:**
- Create: `tools/apd_gauntlet/assemble_inventory.py`
- Test: `tests/test_assemble_inventory.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_assemble_inventory.py`:

```python
import yaml
from tools.apd_gauntlet.assemble_inventory import assemble_inventory


def test_assemble_inventory_mints_ids_and_wires_crosses_by_name(tmp_path):
    inv = {
        "schema_version": 1, "generated_by": "intake",
        "assets": [
            {"name": "API gateway", "asset_type": "service",
             "provenance": {"artifact": "tech_plan.md", "locator": "L1"}, "confidence": "high"},
            {"name": "PHI DB", "asset_type": "datastore",
             "provenance": {"artifact": "tech_plan.md", "locator": "L2"}, "confidence": "high"},
        ],
        "identities": [],
        "trust_boundaries": [
            {"name": "edge", "crosses": ["API gateway", "PHI DB"],
             "provenance": {"artifact": "tech_plan.md", "locator": "L3"}},
        ],
    }
    d = tmp_path / "00-context"
    d.mkdir(parents=True)
    p = d / "asset-inventory.yaml"
    p.write_text(yaml.safe_dump(inv, sort_keys=False), encoding="utf-8")

    assemble_inventory(tmp_path)

    out = yaml.safe_load(p.read_text(encoding="utf-8"))
    ids = {a["name"]: a["asset_id"] for a in out["assets"]}
    assert all(v.startswith("asset-") for v in ids.values())
    # crosses rewritten from names to the minted asset ids
    assert out["trust_boundaries"][0]["crosses"] == [ids["API gateway"], ids["PHI DB"]]
    assert out["trust_boundaries"][0]["boundary_id"].startswith("tb-")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_assemble_inventory.py::test_assemble_inventory_mints_ids_and_wires_crosses_by_name -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the assembler**

Create `tools/apd_gauntlet/assemble_inventory.py`:

```python
"""Assemble 00-context/asset-inventory.yaml: mint deterministic asset-/idn-/tb-
ids from name+provenance and wire trust_boundaries.crosses (authored by asset
NAME) to the minted asset ids. Idempotent; no-op when the file is absent.

Runs in the intake phase, BEFORE specialists cite inventory ids in evidence, so
the ids are stable for the remainder of the run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .linters import compute_asset_id, compute_boundary_id, compute_identity_id


def _loc(rec: dict[str, Any]) -> str:
    prov = rec.get("provenance") or {}
    return str(prov.get("locator", ""))


def assemble_inventory(run_dir: Path) -> int:
    path = run_dir / "00-context" / "asset-inventory.yaml"
    if not path.exists():
        return 0
    inv = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(inv, dict):
        return 0

    name_to_asset_id: dict[str, str] = {}
    changed = 0
    for a in inv.get("assets") or []:
        new_id = compute_asset_id(a.get("name", ""), _loc(a))
        if a.get("asset_id") != new_id:
            changed += 1
        a["asset_id"] = new_id
        name_to_asset_id[a.get("name", "")] = new_id
    for i in inv.get("identities") or []:
        i["identity_id"] = compute_identity_id(i.get("name", ""), _loc(i))
    for b in inv.get("trust_boundaries") or []:
        b["boundary_id"] = compute_boundary_id(b.get("name", ""), _loc(b))
        # crosses authored by asset NAME -> rewrite to minted asset id (pass
        # through values already in asset-id form so the pass is idempotent).
        b["crosses"] = [name_to_asset_id.get(c, c) for c in (b.get("crosses") or [])]

    path.write_text(
        yaml.safe_dump(inv, sort_keys=False, allow_unicode=True, width=4096),
        encoding="utf-8",
    )
    return changed
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_assemble_inventory.py -v`
Expected: PASS.

- [ ] **Step 5: Idempotency test + commit**

Add:

```python
def test_assemble_inventory_is_idempotent(tmp_path):
    # ... build + assemble once (reuse the setup above via a helper) ...
    # second run must not change crosses (asset ids pass through unchanged)
    pass  # implement by calling assemble_inventory twice and asserting file bytes equal
```

Implement it (assemble twice; assert the file content is byte-identical after the second call). Run the module; expect PASS.

```bash
git add tools/apd_gauntlet/assemble_inventory.py tests/test_assemble_inventory.py
git commit -m "feat: assemble_inventory mints asset/idn/tb ids and wires crosses by name"
```

### Task 4.3: Schema — ids optional at emission; `crosses` accepts names pre-assembly

**Files:**
- Modify: `schemas/asset-inventory.schema.json`
- Test: `tests/test_asset_inventory_schema.py` (create if absent)

- [ ] **Step 1: Write the failing test**

```python
def test_inventory_valid_without_ids_and_with_named_crosses():
    inv = {
        "schema_version": 1, "generated_by": "intake",
        "assets": [{"name": "A", "asset_type": "service",
                    "provenance": {"artifact": "t.md", "locator": "L1"}, "confidence": "high"}],
        "identities": [],
        "trust_boundaries": [{"name": "b", "crosses": ["A"],
                              "provenance": {"artifact": "t.md", "locator": "L2"}}],
    }
    assert _validate_asset_inventory(inv) == []  # mirror the existing validator helper
```

- [ ] **Step 2: Run to verify it fails**

Expected: FAIL — `asset_id`/`boundary_id` are required and `crosses` items must match `^asset-[0-9a-f]{8}$`.

- [ ] **Step 3: Edit the schema**

In `schemas/asset-inventory.schema.json`:
- Remove `asset_id` from the asset `required`; remove `identity_id` from the identity `required`; remove `boundary_id` from the boundary `required`. Add `"readOnly": true` to each id property (keep the `^asset-…$` etc. patterns for the post-assembly form).
- Relax `trust_boundaries.crosses.items` to accept either a minted asset id or a pre-assembly name:
  ```json
  "items": { "type": "string", "minLength": 1 }
  ```
  (The post-assembly invariant — every `crosses` entry resolves to a real `asset_id` — is enforced by the existing cross-file pass in `validate.py:617-650`, which runs after `assemble_inventory`.)

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_asset_inventory_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/asset-inventory.schema.json tests/test_asset_inventory_schema.py
git commit -m "feat(schema): inventory ids tooling-authored; crosses authored by name pre-assembly"
```

### Task 4.4: CLI + workflow wiring; intake prompt

**Files:**
- Modify: `tools/apd_gauntlet/cli.py` (add `assemble-inventory` command)
- Modify: `.claude/workflows/apd-gauntlet.js` (intake phase)
- Modify: `.claude/agents/apd-intake.md`
- Test: new `tests/test_cli_assemble_inventory.py`, new `tests/test_intake_contract.py`

- [ ] **Step 1: Write the failing CLI test**

```python
def test_assemble_inventory_cli(tmp_path, ...):
    # build a minimal inventory under 00-context, invoke the click command via
    # CliRunner, assert exit 0 and that asset_id was minted. Mirror an existing
    # CliRunner-based test in tests/ (e.g. test_check_ids).
    pass
```

- [ ] **Step 2: Run → FAIL (no command).** Run: `python -m pytest tests/test_cli_assemble_inventory.py -v`.

- [ ] **Step 3: Add the click command**

In `tools/apd_gauntlet/cli.py`, mirror `canonicalize_cmd` (line ~1161):

```python
@main.command("assemble-inventory")
@click.argument("run_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def assemble_inventory_cmd(run_dir: Path) -> None:
    """Mint deterministic asset-/idn-/tb- ids and wire trust-boundary crosses."""
    from .assemble_inventory import assemble_inventory
    changed = assemble_inventory(run_dir)
    click.echo(f"assemble-inventory: {changed} asset id(s) (re)minted under {run_dir}/00-context/")
```

(Match the decorator/group name (`@main.command` vs `@cli.command`) used by the surrounding commands in this file.)

- [ ] **Step 4: Run → PASS.**

- [ ] **Step 5: Wire into the workflow intake phase**

In `.claude/workflows/apd-gauntlet.js`, after the `apd-intake` llmStep (line ~314) and its validate, add:

```js
pyStep('assemble-inventory', {
  phase: 'intake', label: 'assemble-inventory',
  outputs: runDir + '/00-context/asset-inventory.yaml (asset-/idn-/tb- ids minted)',
  validateScope: runDir + '/00-context', alwaysRun: true,
});
```

(Place it BEFORE the tier specialists run so inventory ids are stable when specialists cite them.)

- [ ] **Step 6: Update the intake agent**

In `.claude/agents/apd-intake.md` (lines ~44, 54, 60), replace the id bullets:
- `asset_id: asset-<sha8> (deterministic ID from name + locator)` → `# NO asset_id — the assembler mints asset-<sha8> from name + provenance.locator`
- `identity_id: idn-<sha8>` → `# NO identity_id — minted by the assembler`
- `boundary_id: tb-<sha8>` → `# NO boundary_id — minted by the assembler`

Add to the trust-boundary guidance: "Author `crosses` as a list of asset **names** (exactly as you wrote them in `assets[].name`); the assembler rewrites them to the minted `asset_id`s." Update the empty-inventory fallback (lines ~74, 269) — it stays `{schema_version: 1, generated_by: intake, assets: [], identities: [], trust_boundaries: []}` (no ids, already compatible).

- [ ] **Step 7: Write + run the intake contract test**

```python
def test_intake_does_not_fabricate_inventory_ids():
    import pathlib
    t = (pathlib.Path(__file__).resolve().parent.parent / ".claude/agents/apd-intake.md").read_text()
    assert "deterministic ID from name" not in t
    assert "crosses" in t and "names" in t.lower()
```

Run: `python -m pytest tests/test_intake_contract.py tests/test_cli_assemble_inventory.py -v`. Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/apd_gauntlet/cli.py .claude/workflows/apd-gauntlet.js .claude/agents/apd-intake.md tests/test_cli_assemble_inventory.py tests/test_intake_contract.py
git commit -m "feat: assemble-inventory CLI + intake-phase wiring; intake emits names not ids"
```

### Task 4.5: Phase 4 verification

- [ ] **Step 1:** `python -m pytest tests -q && ruff check tools/ tests/ && mypy tools/apd_gauntlet`. Expected: clean.
- [ ] **Step 2:** Re-run `validate` cross-file pass against a fixture run that exercises `kind: asset_inventory` evidence refs to confirm refs still resolve after minting. If a committed `examples/` run has named `crosses`, regenerate its inventory with `apd-gauntlet assemble-inventory <run>` and re-validate.
- [ ] **Step 3:** Commit fixups.

---

# Phase 5 — ADR + deterministic-task register + docs

**Outcome:** The authored-vs-derived contract is codified in an ADR (amending ADR-0005) and a standing register; user-facing docs reflect the new contract.

## File Structure (Phase 5)

- Create: `docs/adrs/0020-tooling-authored-derived-fields.md`
- Create: `docs/deterministic-field-register.md`
- Modify: `docs/adrs/0005-deterministic-finding-ids.md` (add superseded-in-part note)
- Modify: `docs/running-the-gauntlet.md`, `docs/extending-agents.md`, `docs/schema-evolution.md`, `CHANGELOG.md`
- Test: extend `tests/test_agent_prompt_id_contract.py` or add a docs-consistency test.

### Task 5.1: ADR-0020 (do this right after Phase 1 merges)

- [ ] **Step 1: Write the ADR**

Create `docs/adrs/0020-tooling-authored-derived-fields.md` following the format of `docs/adrs/0005-deterministic-finding-ids.md`. Content:
- **Status:** Accepted. **Amends:** 0005 (which established deterministic ids but kept agents authoring a best-effort id).
- **Context:** LLMs cannot reliably compute SHA-256; agent-authored ids were always fabricated-then-overwritten (findings/caps) or fabricated-and-unverified (`tmeval-`, intake inventory). Some derivation was already script-owned (`apath-`, `merged-`, scaffolding, rollups).
- **Decision:** Every *derived* field (pure function of authored content) is authored solely by the deterministic assembler (`apd-gauntlet canonicalize` + `assemble-inventory`). Agents author *content only* and reference other records by stable handles (asset **name**) where a reference is needed pre-assembly. Schema marks derived fields `readOnly`/optional-at-emission; presence/consistency linters are the post-assembly backstop.
- **Consequences:** removes the fabricated-hash error class; intermediate artifacts stop carrying fake-authoritative ids; assembler becomes a critical chokepoint (mitigated by the `test_canonicalize`/`test_assemble_inventory` suites). Run-to-run id *stability* is unchanged — it remains bounded by content (title) stability, a separate concern.

- [ ] **Step 2: Amend ADR-0005**

Add a top note to `docs/adrs/0005-deterministic-finding-ids.md`: "> **Amended by [ADR-0020]** (2026-06-12): agents no longer author a best-effort id; the assembler is the sole author. The id algorithm in this ADR is unchanged."

- [ ] **Step 3: Commit**

```bash
git add docs/adrs/0020-tooling-authored-derived-fields.md docs/adrs/0005-deterministic-finding-ids.md
git commit -m "docs(adr): ADR-0020 tooling-authored derived fields (amends 0005)"
```

### Task 5.2: Deterministic-task register

- [ ] **Step 1: Write the register**

Create `docs/deterministic-field-register.md` with a table: every derived field/id family × owner (script function) × enforcement (linter) × agent contract. Seed it from the "Current-state register" table at the top of this plan, updated to the post-implementation state. Include the already-script items (scaffolding via `init_run.scaffold_run`, `control_mappings` via `_normalize_control_mappings`, rollups, `apath-`, `merged-`).

- [ ] **Step 2: Add a guard test**

Add to `tests/test_agent_prompt_id_contract.py` (or a new `tests/test_register_consistency.py`) a test asserting the register lists every `compute_*_id` helper in `linters.py`:

```python
def test_register_mentions_every_id_helper():
    import pathlib, re
    lint = (pathlib.Path(__file__).resolve().parent.parent / "tools/apd_gauntlet/linters.py").read_text()
    helpers = set(re.findall(r"def (compute_\w*id)\(", lint))
    reg = (pathlib.Path(__file__).resolve().parent.parent / "docs/deterministic-field-register.md").read_text()
    missing = [h for h in helpers if h not in reg]
    assert missing == [], f"register omits id helpers: {missing}"
```

- [ ] **Step 3: Run → PASS; commit**

```bash
git add docs/deterministic-field-register.md tests/test_register_consistency.py
git commit -m "docs: deterministic-field register + consistency guard"
```

### Task 5.3: User-facing docs + CHANGELOG; version checkpoint

- [ ] **Step 1: Update prose docs**

- `docs/running-the-gauntlet.md`: note that `canonicalize` (and `assemble-inventory`) is the sole author of ids; agents emit content only.
- `docs/extending-agents.md`: the authored-vs-derived rule for new agents; never emit an `id`/`schema_version`; reference by handle.
- `docs/schema-evolution.md`: under a **1.7.0** entry, record: finding/cap/inventory/domain-improvement `id` + `schema_version` made optional-at-emission (`readOnly`); `tmeval_key` added; `crosses` relaxed to names pre-assembly.
- `CHANGELOG.md`: one entry summarizing the contract change.

- [ ] **Step 2: VERSION CHECKPOINT (ask the user)**

Per the locked decision the framework is held at 1.7.0. Confirm with the user whether this contract change warrants a minor bump (1.8.0) or stays 1.7.0 before finalizing `docs/schema-evolution.md` and `__version__`. Do not bump unilaterally.

- [ ] **Step 3: Markdownlint (CI parity) + commit**

Run the full CI markdownlint glob locally (`docs/**` is globbed; specs included). Fix any MD0xx. Then:

```bash
git add docs/ CHANGELOG.md
git commit -m "docs: contract change — assembler authors all derived ids/fields (1.7.0)"
```

---

## Self-Review (run against the spec before execution)

**Spec coverage:**
- "Agents generate content, script creates canonicalized objects" → Phase 1 (finding/cap), Phase 2 (tmeval), Phase 3 (dimpr), Phase 4 (inventory). ✅
- "Emit no id at all" (locked decision) → Phase 1 schema/prompt changes; no slug introduced. ✅
- "Move other deterministic tasks like scaffolding the runs directory, where appropriate" → scaffolding is **already** a script (`init_run.scaffold_run`); documented in the register (Phase 5) rather than re-implemented. The genuine remaining deterministic gaps (tmeval/dimpr/inventory ids) are migrated. ✅
- "Register + ADR" (full scope) → Phase 5. ✅

**Placeholder scan:** Task 4.2 Step 5 and Task 4.4 Step 1 leave a `pass` test body to be implemented during execution — these are explicitly flagged "implement it" with the assertion described, not silent TODOs; the assertion semantics are specified. Acceptable for an isolated-fixture test whose exact setup mirrors a sibling. All code-producing steps include full code.

**Type/name consistency:** helper names used consistently — `compute_tmeval_id`, `compute_asset_id`/`compute_identity_id`/`compute_boundary_id`, `assemble_inventory`, `_mint_dimpr_ids`, `check_id_present`, `check_tmeval_id`. The assembler entry point is `canonicalize_run` (extended) plus the new `assemble_inventory` (inventory runs separately because it must precede specialists, not after them).

**Known verification dependencies (confirm during execution, not assumed):**
1. Exact `required`-array line numbers in the two schemas (re-grep before editing — other PRs may have shifted them).
2. The singular root key of `domain-improvements.yaml` (Task 3.1 Step 2) and the `provenance.locator` key name (Task 4.1 Step 1) — read the schema first.
3. The `Violation(...)` constructor arity in `validate.py` (Tasks 1.3/2.4) — copy the surrounding call's shape exactly.
4. The click group decorator (`@main.command` vs `@cli.command`) in `cli.py` (Task 4.4).
5. The CI markdownlint invocation (Phase 1/5) — mirror `.github/workflows/` exactly.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-12-deterministic-field-ownership.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best given the 5 independently-mergeable phases (one PR each).

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
