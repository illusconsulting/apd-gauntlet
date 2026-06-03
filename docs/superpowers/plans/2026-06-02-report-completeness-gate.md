# HTML Report Completeness Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee that every gauntlet run ships a complete HTML report — real executive summary, accurate finding/capability counts, attack-path analysis, and D3FEND overlay — by extending the existing `audit-report` structural checker with the missing completeness checks and flipping the workflow audit loop to **block** (not warn) on an unresolved structural failure.

**Architecture:** Extend `tools/apd_gauntlet/synthesis/audit.py:audit_report` with six new/tightened `_check()`s (two `editorial`, four `structural`), each exempting legitimately-empty states. Classify every check with a `klass` field surfaced in `report-audit.yaml`. Flip the `synthesis-audit` loop in `.claude/workflows/apd-gauntlet.js` so that after the N=2 remediation cap an unresolved structural failure throws; the LLM semantic auditor's residual stays non-blocking. Enrich the committed example fixture with a real `report-data.yaml` so it passes the new editorial checks.

**Tech Stack:** Python 3.12+, `click` (CLI), PyYAML, `pytest` + `click.testing.CliRunner`. Workflow runner is JavaScript (`.claude/workflows/apd-gauntlet.js`); its tests are static-source assertions in `tests/test_workflow_apd_gauntlet.py`. JSON Schema for `report-audit.yaml`.

---

## Source spec & one refinement

Spec: `docs/superpowers/specs/2026-06-02-report-completeness-gate-design.md` (approved).

**Refinement discovered during planning (kept faithful to the spec's intent):** the workflow `RECEIPT` schema (`agent-receipt.schema.json`, `counts` is `additionalProperties: false`) plus the workflow JS having **no filesystem access** means per-class counts (`structural_failed`/`editorial_failed`) cannot reach the loop without modifying the global receipt contract. Therefore **the workflow loop branches on `audit.status` only** (robust, no schema change). `klass` still lives in `report-audit.yaml` for humans, tests, and the report-auditor; targeted editorial remediation is achieved by having the **report-writer agent read `report-audit.yaml`** (it has file access). The only thing dropped versus the spec's C2/C3 is the purely-structural short-circuit optimization — a structural failure may burn up to 2 remediation cycles before blocking (a latency cost, not a correctness one). The core guarantee — block on unresolved structural failure — is preserved.

## Pre-flight

- Branch: `feat/report-completeness-gate` (already created off `main`; the spec is committed here).
- Editable install: `pip install -e .` if `apd_gauntlet` imports fail.
- Full suite at any checkpoint: `pytest` (repo root).

## File Structure

**Modified:**
- `tools/apd_gauntlet/report/transform.py` — extract `EXEC_SUMMARY_PLACEHOLDER` module constant (Task 1).
- `tools/apd_gauntlet/synthesis/audit.py` — `_check` gains `klass`; six new checks in `audit_report` (Tasks 2, 4–8).
- `tools/apd_gauntlet/cli.py` — `audit_report_cmd` prints per-class failed counts (Task 9).
- `schemas/report-audit.schema.json` — add optional `klass` to each check item (Task 2).
- `.claude/workflows/apd-gauntlet.js` — flip the `synthesis-audit` loop terminal behavior; enrich the report-writer remediation prompt (Task 10).

**Created:**
- `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-data.yaml` — real editorial content for the fixture (Task 3).

**Test files touched:**
- `tests/test_cli_audit_report.py` — new-check unit tests + regression guard (Tasks 4–8, 11).
- `tests/test_report_audit_schema.py` — `klass` in the fixture (Task 2).
- `tests/test_workflow_apd_gauntlet.py` — flip-to-block static assertions (Task 10).

## Dependency ordering

Task 1 → Task 2 → **Task 3 (enrich fixture) MUST precede Task 4** (else the editorial checks fail the committed example and break `test_audit_passes_on_committed_example`). Tasks 5–8 are independent of 3/4 and of each other (they pass on existing fixtures). Task 9 is independent. Task 10 (workflow) is independent of the Python checks. Task 11 is last (it asserts the whole gate is green across all runs).

Order: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11.**

---

### Task 1: Extract `EXEC_SUMMARY_PLACEHOLDER` constant

The placeholder string lives as a magic literal in `build_apd_data`. Lift it to a module constant so the emitter (`transform.py`) and the checker (`audit.py`) cannot drift.

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py`
- Test: `tests/unit/report/test_exec_summary_placeholder.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/report/test_exec_summary_placeholder.py`:

```python
"""The exec-summary fallback string is a single shared constant."""
from apd_gauntlet.report import transform


def test_exec_summary_placeholder_constant_exists():
    assert transform.EXEC_SUMMARY_PLACEHOLDER == "Run summary not provided by synthesizer."


def test_build_apd_data_uses_the_constant_when_supplement_absent():
    # A RunArtifacts-like stub with no report_data supplement and one finding
    # must yield exactly [EXEC_SUMMARY_PLACEHOLDER] for exec_summary.
    from unittest.mock import MagicMock
    arts = MagicMock()
    arts.report_data = None
    arts.deduped_findings = []
    arts.deduped_capabilities = []
    arts.attack_path_findings = []
    arts.attack_paths = None
    arts.asset_graph = None
    arts.defense_graph = None
    data = transform.build_apd_data(arts)
    assert data["exec_summary"] == [transform.EXEC_SUMMARY_PLACEHOLDER]
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `pytest tests/unit/report/test_exec_summary_placeholder.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'EXEC_SUMMARY_PLACEHOLDER'`.

- [ ] **Step 3: Add the constant and reference it**

In `tools/apd_gauntlet/report/transform.py`, add near the other module-level constants (top of file, after imports):

```python
EXEC_SUMMARY_PLACEHOLDER = "Run summary not provided by synthesizer."
```

Then in `build_apd_data`, replace the `exec_summary` section tuple's two literals:

```python
        ("exec_summary",
         lambda: (supplement.get("exec_summary") or {}).get(
             "paragraphs", [EXEC_SUMMARY_PLACEHOLDER],
         ),
         [EXEC_SUMMARY_PLACEHOLDER]),
```

- [ ] **Step 4: Run it — expect PASS**

Run: `pytest tests/unit/report/test_exec_summary_placeholder.py -v`
Expected: PASS. Then `pytest tests/unit/report/ -q` to confirm no regression.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_exec_summary_placeholder.py
git commit -m "refactor(report): lift exec-summary placeholder to a shared constant

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `_check` gains `klass`; schema allows it (backwards-compatible)

Every check is classified `structural` (default) or `editorial`. `klass` is **optional** in the schema so the already-committed `report-audit.yaml` fixtures (which lack it) still validate; `_check` always emits it on freshly generated results.

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (`_check`, lines 68–71)
- Modify: `schemas/report-audit.schema.json` (checks item, lines 13–25)
- Test: `tests/test_report_audit_schema.py`, `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli_audit_report.py`:

```python
def test_every_check_carries_a_valid_klass(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    assert result.checks, "expected at least one check"
    for c in result.checks:
        assert c.get("klass") in ("structural", "editorial"), c
    # Pre-existing checks are all structural.
    sec = [c for c in result.checks if c["name"] == "section_errors_empty"]
    assert sec and sec[0]["klass"] == "structural"
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `pytest tests/test_cli_audit_report.py::test_every_check_carries_a_valid_klass -v`
Expected: FAIL — `klass` key absent (`None not in (...)`).

- [ ] **Step 3: Add `klass` to `_check`**

Replace `_check` (`tools/apd_gauntlet/synthesis/audit.py:68-71`):

```python
def _check(result: AuditResult, name: str, ok: bool, detail: str, klass: str = "structural") -> None:
    result.checks.append({
        "name": name, "status": "pass" if ok else "fail", "detail": detail, "klass": klass,
    })
    if not ok:
        result.status = "fail"
```

- [ ] **Step 4: Allow `klass` in the schema**

In `schemas/report-audit.schema.json`, the checks item `properties` (currently `name`/`status`/`detail`) gains `klass`. Keep `required` as `["name", "status", "detail"]` (klass optional — backwards-compatible with committed fixtures):

```json
        "properties": {
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["pass", "fail"] },
          "detail": { "type": "string" },
          "klass": { "type": "string", "enum": ["structural", "editorial"] }
        }
```

- [ ] **Step 5: Update the schema test fixture**

In `tests/test_report_audit_schema.py`, the minimal-pass fixture builds check dicts. Add `"klass": "structural"` to each check dict in that fixture so it mirrors real output (the schema still accepts checks without klass, but the fixture should be representative). Run:

`pytest tests/test_report_audit_schema.py -v`
Expected: PASS.

- [ ] **Step 6: Run the audit tests — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v`
Expected: all PASS (the example still passes; every check now has `klass`).

- [ ] **Step 7: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py schemas/report-audit.schema.json tests/test_report_audit_schema.py tests/test_cli_audit_report.py
git commit -m "feat(audit): classify report-audit checks with klass (structural|editorial)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Enrich the example fixture with a real `report-data.yaml`

The committed example lacks `report-data.yaml`, so its `data.js` carries the placeholder exec summary and empty `next_steps` — it would fail the editorial checks added in Task 4. Author a real `report-data.yaml` (mirroring the shape of `runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/report-data.yaml`) and rebuild `data.js`.

**Files:**
- Create: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-data.yaml`
- Regenerate: `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/data.js`
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Extract real ids for `headline_findings` and `strengths`**

Run:

```bash
python3 -c "
import yaml
EX='examples/apd-20260601-claim-event-bus/expected/40-synthesis'
f=yaml.safe_load(open(EX+'/deduped-findings.yaml')); recs=f.get('finding') or f.get('findings') or []
order={'critical':0,'high':1,'medium':2,'low':3,'info':4,'informational':4}
recs=sorted(recs,key=lambda r:(order.get(str(r.get('severity')),9),str(r.get('id'))))
print('FINDINGS:'); [print(' ',r['id'],r['severity']) for r in recs[:10]]
c=yaml.safe_load(open(EX+'/deduped-capabilities.yaml')); caps=c.get('capability') or c.get('capabilities') or []
print('CAPS:'); [print(' ',x['id']) for x in caps[:5]]
"
```

Note the printed finding ids (top 10) and capability ids (top ~3). Use them verbatim in Step 2.

- [ ] **Step 2: Author `report-data.yaml`**

Create `examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-data.yaml`. Use the real ids from Step 1 (the ids below are the known top findings for this fixture — verify against Step 1 output and adjust if the corpus changed):

```yaml
schema_version: 1

exec_summary:
  paragraphs:
    - "This APD gauntlet run reviews the claim-event-bus reference architecture under the pbm domain pack: a Kafka-based pipeline carrying PHI claim-events across a multi-AZ deployment. The 9-specialist gauntlet assessed operational consequences across all nine APD goals over the deduped corpus plus the attack-path analysis."
    - "The highest-leverage concern is the unsigned, mutably-stored audit log (merged-4dd83f6a, critical): consequential claim actions cannot be reconstructed or proven tamper-free. High-severity gaps cluster around authentication assurance (SMS MFA fallback), availability (single-region 99.95% SLO, untested DR failover), and confidentiality (PHI in the Kafka topic lacking envelope encryption; unspecified KMS DEK rotation)."

headline_findings:
  - {id: "merged-4dd83f6a", rank: 1}
  - {id: "auth-dbba3dea", rank: 2}
  - {id: "avail-4e08f6d8", rank: 3}
  - {id: "avail-ce35b2ed", rank: 4}
  - {id: "conf-7aa376c5", rank: 5}
  - {id: "conf-98a543cd", rank: 6}

strengths: []

next_steps:
  - rank: 1
    text: "Sign every audit record (HMAC or asymmetric) and move the audit store to a WORM substrate (object-lock) so consequential claim actions are tamper-evident and reconstructable."
    refs: ["merged-4dd83f6a"]
  - rank: 2
    text: "Replace SMS MFA fallback with TOTP/WebAuthn to raise authentication assurance on claim-submitter and operator surfaces."
    refs: ["auth-dbba3dea"]
  - rank: 3
    text: "Add envelope encryption for PHI fields in the Kafka claim-events topic and pin a KMS DEK rotation cadence."
    refs: ["conf-7aa376c5", "conf-98a543cd"]
  - rank: 4
    text: "Establish a tested DR failover procedure (document RTO/RPO, run a game-day) and evaluate multi-region active-active to meet the 99.95% SLO."
    refs: ["avail-ce35b2ed", "avail-4e08f6d8"]

posture_summary:
  trustworthiness: "PHI in the claim-event topic lacks envelope encryption and DEK rotation is unspecified; integrity controls exist but the audit substrate is mutable."
  scalability: "Single-region active-passive against a 99.95% SLO with untested DR failover is the dominant scalability risk."
  auditability: "The audit log is unsigned and stored in a mutable table — the single critical finding — undermining non-repudiation and tamper-evidence for every consequential claim action."
```

> If Step 1 shows different top ids, replace the `headline_findings` ids and the `refs` accordingly. `strengths: []` is valid (the schema requires the key, not non-empty content); populate it with real capability ids from Step 1 if you want the Strengths panel populated.

- [ ] **Step 3: Validate the authored file against its schema**

Run: `python3 -c "import json,yaml,jsonschema; jsonschema.validate(yaml.safe_load(open('examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-data.yaml')), json.load(open('schemas/report-data.schema.json')))" && echo "report-data.yaml VALID"`
Expected: `report-data.yaml VALID`. Fix any schema error before proceeding.

- [ ] **Step 4: Rebuild `data.js`**

Run: `apd-gauntlet build-report examples/apd-20260601-claim-event-bus/expected`
Expected: exits 0; `data.js` rewritten.

- [ ] **Step 5: Confirm the rebuild fixed the editorial signals and broke nothing**

Run:

```bash
python3 -c "
import json,pathlib
p=pathlib.Path('examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/data.js')
t=p.read_text(encoding='utf-8-sig').strip()
t=t[len('window.APD_DATA = '):] if t.startswith('window.APD_DATA = ') else t
t=t.rstrip(); t=t[:-1] if t.endswith(';') else t
d=json.loads(t.replace('<\\\\/','</'))
assert d['exec_summary']!=['Run summary not provided by synthesizer.'], 'exec still placeholder'
assert len(d['next_steps'])>0, 'next_steps empty'
assert len(d['findings'])==90, ('findings count changed', len(d['findings']))
print('OK exec_summary real; next_steps=%d; findings=%d' % (len(d['next_steps']), len(d['findings'])))
"
```

Expected: `OK exec_summary real; next_steps=4; findings=90`. Then run the existing example tests:
`pytest tests/test_cli_audit_report.py -v` → all PASS (status still pass — new checks not added yet).

- [ ] **Step 6: Commit**

```bash
git add examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-data.yaml examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-html/data.js examples/apd-20260601-claim-event-bus/expected/40-synthesis/report-audit.yaml
git commit -m "test(example): add real report-data.yaml to claim-event-bus fixture

Makes the committed example a faithful full-run output (real exec summary +
next_steps) so the report-completeness editorial checks pass on it.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Editorial checks — `exec_summary_present`, `editorial_sections_present`

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (`audit_report`; insert after the `section_errors_empty` check, before `result.counts = {`)
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli_audit_report.py`:

```python
def _mutate_data_js(dst, fn):
    """Parse the example data.js, apply fn(dict), re-emit it canonically."""
    from apd_gauntlet.report.emit import write_data_js
    p = dst / "40-synthesis" / "report-html" / "data.js"
    d = parse_data_js(p)
    fn(d)
    write_data_js(d, p)


def test_exec_summary_present_passes_on_enriched_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "exec_summary_present"]
    assert c and c[0]["status"] == "pass", c
    assert c[0]["klass"] == "editorial"


def test_exec_summary_present_fails_on_placeholder(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d.__setitem__(
        "exec_summary", ["Run summary not provided by synthesizer."]))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "exec_summary_present"]
    assert c and c[0]["status"] == "fail", c
    assert result.status == "fail"


def test_exec_summary_present_exempt_when_empty_run(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: (
        d["meta"].__setitem__("is_empty_run", True),
        d.__setitem__("exec_summary", ["Run summary not provided by synthesizer."]),
    ))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "exec_summary_present"]
    assert c and c[0]["status"] == "pass", "empty run is exempt"


def test_editorial_sections_present_fails_when_report_data_absent(tmp_path):
    dst = _copy_example(tmp_path)
    (dst / "40-synthesis" / "report-data.yaml").unlink()
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "editorial_sections_present"]
    assert c and c[0]["status"] == "fail", c
    assert c[0]["klass"] == "editorial"
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_cli_audit_report.py -v -k "exec_summary or editorial_sections"`
Expected: FAIL — these checks do not exist yet.

- [ ] **Step 3: Implement the two checks**

In `tools/apd_gauntlet/synthesis/audit.py`, update the existing import line `from ..report.transform import build_apd_data` to also import the constant:

```python
    from ..report.transform import build_apd_data, EXEC_SUMMARY_PLACEHOLDER
```

Then insert this block immediately after the `section_errors_empty` `_check(...)` call and before `result.counts = {`:

```python
    # === Report-completeness gate (report-completeness-gate) ===
    meta = parsed.get("meta") or {}
    is_empty_run = bool(meta.get("is_empty_run"))

    # Check 1 (editorial): executive summary present and not the placeholder.
    exec_summary = parsed.get("exec_summary")
    exec_summary = exec_summary if isinstance(exec_summary, list) else []
    exec_ok = is_empty_run or (
        len(exec_summary) > 0 and exec_summary != [EXEC_SUMMARY_PLACEHOLDER]
    )
    _check(result, "exec_summary_present", exec_ok,
           f"is_empty_run={is_empty_run} paragraphs={len(exec_summary)}",
           klass="editorial")

    # Check 8 (editorial): editorial blocks present in report-data.yaml.
    rd_path = synth / "report-data.yaml"
    rd_doc = yaml.safe_load(rd_path.read_text(encoding="utf-8")) if rd_path.is_file() else None
    rd_doc = rd_doc if isinstance(rd_doc, dict) else {}
    editorial_ok = is_empty_run or (
        rd_path.is_file()
        and bool((rd_doc.get("exec_summary") or {}).get("paragraphs"))
        and bool(rd_doc.get("posture_summary"))
        and bool(rd_doc.get("headline_findings"))
        and bool(rd_doc.get("next_steps"))
    )
    _check(result, "editorial_sections_present", editorial_ok,
           f"report_data={rd_path.is_file()} posture={bool(rd_doc.get('posture_summary'))} "
           f"headline={len(rd_doc.get('headline_findings') or [])} "
           f"next_steps={len(rd_doc.get('next_steps') or [])}",
           klass="editorial")
```

- [ ] **Step 4: Run them — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v -k "exec_summary or editorial_sections or passes_on_committed"`
Expected: all PASS (including `test_audit_passes_on_committed_example`, because Task 3 enriched the fixture).

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): editorial completeness checks (exec summary, editorial sections)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `attack_paths_present` check (structural)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (`audit_report`; in the completeness block)
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli_audit_report.py`:

```python
def test_attack_paths_present_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "pass", c
    assert c[0]["klass"] == "structural"


def test_attack_paths_present_fails_when_section_null_but_graph_exists(tmp_path):
    dst = _copy_example(tmp_path)  # has asset-graph.yaml
    _mutate_data_js(dst, lambda d: d.__setitem__("attack_paths", None))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "fail", c


def test_attack_paths_present_exempt_when_not_activated(tmp_path):
    dst = _copy_example(tmp_path)
    (dst / "40-synthesis" / "asset-graph.yaml").unlink()
    _mutate_data_js(dst, lambda d: d.__setitem__("attack_paths", None))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "attack_paths_present"]
    assert c and c[0]["status"] == "pass", "no asset-graph.yaml -> exempt"
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_cli_audit_report.py -v -k attack_paths_present`
Expected: FAIL — check absent.

- [ ] **Step 3: Implement the check** (append inside the completeness block, after the editorial checks)

```python
    # Check 3 (structural): attack-path analysis present when activated.
    asset_graph_path = synth / "asset-graph.yaml"
    ap = parsed.get("attack_paths")
    if not asset_graph_path.is_file():
        _check(result, "attack_paths_present", True,
               "exempt: attack-path analysis not activated (no asset-graph.yaml)",
               klass="structural")
    elif ap is None:
        _check(result, "attack_paths_present", False,
               "asset-graph.yaml present but data.attack_paths is null (build dropped the section)",
               klass="structural")
    else:
        node_count = int((ap.get("asset_graph_summary") or {}).get("node_count") or 0)
        apath_blocked = any(
            str(f.get("id", "")).startswith("apath-") and f.get("disposition") == "blocked"
            for f in apath_f
        )
        ap_ok = node_count > 0 or apath_blocked
        total_paths = (ap.get("summary") or {}).get("total_paths")
        _check(result, "attack_paths_present", ap_ok,
               f"node_count={node_count} total_paths={total_paths} apath_blocked={apath_blocked}",
               klass="structural")
```

> Note: `total_paths == 0` passes when `node_count > 0` (the graph rendered) — this is the documented valid "graph exists, no traversable chain" outcome (caldera/crapi). We never require paths > 0.

- [ ] **Step 4: Run them — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v -k attack_paths_present`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): attack_paths_present completeness check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `d3fend_overlay_present` check (structural)

D3FEND overlays are empty in all current fixtures, so this is exempt on real data today; it guards against future regressions where the defense graph has overlays but the build drops them. Tests synthesize the overlay to give the check teeth.

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (completeness block)
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli_audit_report.py`:

```python
def _overlay(edge_id="e1"):
    return {
        "edge_id": edge_id, "paths_traversing": 3,
        "exposed_attack_techniques": ["T1078"],
        "candidate_d3fend": [
            {"d3fend_id": "D3-MFA", "counters": ["T1078"],
             "rationale": "multi-factor auth counters valid-accounts abuse here"}
        ],
        "existing_capability_backing": [], "net_new_d3fend": ["D3-MFA"],
    }


def test_d3fend_overlay_exempt_when_no_overlays(tmp_path):
    dst = _copy_example(tmp_path)  # defense-graph.yaml has 0 overlays
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "pass", c


def test_d3fend_overlay_fails_when_defense_graph_overlays_dropped(tmp_path):
    dst = _copy_example(tmp_path)
    # Defense graph declares an overlay...
    dg = dst / "40-synthesis" / "defense-graph.yaml"
    doc = yaml.safe_load(dg.read_text()) or {}
    doc["bottleneck_overlays"] = [_overlay()]
    dg.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    # ...but data.js carries none (the build dropped it).
    _mutate_data_js(dst, lambda d: d["attack_paths"].__setitem__("bottleneck_overlays", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "fail", c


def test_d3fend_overlay_passes_when_counts_match(tmp_path):
    dst = _copy_example(tmp_path)
    dg = dst / "40-synthesis" / "defense-graph.yaml"
    doc = yaml.safe_load(dg.read_text()) or {}
    doc["bottleneck_overlays"] = [_overlay()]
    dg.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    _mutate_data_js(dst, lambda d: d["attack_paths"].__setitem__("bottleneck_overlays", [_overlay()]))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "d3fend_overlay_present"]
    assert c and c[0]["status"] == "pass", c
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_cli_audit_report.py -v -k d3fend_overlay`
Expected: FAIL — check absent.

- [ ] **Step 3: Implement the check** (completeness block)

```python
    # Check 4 (structural): D3FEND overlay fidelity (defense-graph -> data.js).
    defense_graph_path = synth / "defense-graph.yaml"
    dg_overlays = _yaml_records(defense_graph_path, "bottleneck_overlays")
    data_overlays = ((ap or {}).get("bottleneck_overlays") or []) if isinstance(ap, dict) else []
    if not defense_graph_path.is_file() or len(dg_overlays) == 0:
        _check(result, "d3fend_overlay_present", True,
               f"exempt: defense_graph={defense_graph_path.is_file()} overlays={len(dg_overlays)}",
               klass="structural")
    else:
        counts_match = len(data_overlays) == len(dg_overlays)
        has_d3fend = bool(data_overlays) and all(
            isinstance(o, dict) and bool(o.get("candidate_d3fend"))
            for o in data_overlays
        )
        d3_ok = counts_match and has_d3fend
        _check(result, "d3fend_overlay_present", d3_ok,
               f"defense_graph_overlays={len(dg_overlays)} data_js_overlays={len(data_overlays)} "
               f"candidate_d3fend_present={has_d3fend}",
               klass="structural")
```

- [ ] **Step 4: Run them — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v -k d3fend_overlay`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): d3fend_overlay_present completeness check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `apd_matrix_nonempty` + `coverage_rollups_nonempty` (structural)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (completeness block)
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_apd_matrix_nonempty_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "apd_matrix_nonempty"]
    assert c and c[0]["status"] == "pass", c


def test_apd_matrix_nonempty_fails_when_rows_empty_but_findings_exist(tmp_path):
    dst = _copy_example(tmp_path)
    _mutate_data_js(dst, lambda d: d["apd_matrix"].__setitem__("rows", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "apd_matrix_nonempty"]
    assert c and c[0]["status"] == "fail", c


def test_coverage_rollups_nonempty_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"]
    assert c and c[0]["status"] == "pass", c


def test_coverage_rollups_fail_when_nist_rollup_dropped(tmp_path):
    dst = _copy_example(tmp_path)  # nist-coverage.yaml has controls
    _mutate_data_js(dst, lambda d: d.__setitem__("nist_rollup", []))
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "coverage_rollups_nonempty"]
    assert c and c[0]["status"] == "fail", c
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_cli_audit_report.py -v -k "apd_matrix_nonempty or coverage_rollups"`
Expected: FAIL — checks absent.

- [ ] **Step 3: Implement the checks** (completeness block). `nist` and `attack` are already loaded near the top of `audit_report` (the `_yaml_records(... "controls")` / `"techniques"` lines):

```python
    # Check 6a (structural): APD 9xN matrix has rows whenever findings exist.
    findings_present = (len(deduped_f) + len(apath_f)) > 0
    matrix_rows = (parsed.get("apd_matrix") or {}).get("rows") or []
    matrix_ok = is_empty_run or (not findings_present) or len(matrix_rows) > 0
    _check(result, "apd_matrix_nonempty", matrix_ok,
           f"findings_present={findings_present} matrix_rows={len(matrix_rows)}",
           klass="structural")

    # Check 6b (structural): rendered rollups non-empty when the authoritative
    # coverage YAML has rows (i.e. the run cites NIST / ATT&CK at all).
    nist_rollup = parsed.get("nist_rollup") or []
    attack_exposure = parsed.get("attack_exposure") or []
    rollups_ok = is_empty_run or (
        (len(nist) == 0 or len(nist_rollup) > 0)
        and (len(attack) == 0 or len(attack_exposure) > 0)
    )
    _check(result, "coverage_rollups_nonempty", rollups_ok,
           f"nist_controls={len(nist)} nist_rollup_rows={len(nist_rollup)} "
           f"attack_techniques={len(attack)} attack_rows={len(attack_exposure)}",
           klass="structural")
```

- [ ] **Step 4: Run them — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v -k "apd_matrix_nonempty or coverage_rollups"`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): apd_matrix + coverage rollup non-empty checks

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: `taxonomy_titles_resolve` check (structural)

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (completeness block)
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_taxonomy_titles_resolve_passes_on_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "taxonomy_titles_resolve"]
    assert c and c[0]["status"] == "pass", c


def test_taxonomy_titles_resolve_fails_on_bare_id(tmp_path):
    dst = _copy_example(tmp_path)
    def _bare(d):
        # Force one taxonomy entry's title to equal its id (a bare-ID tooltip).
        k = next(iter(d["taxonomy"]))
        d["taxonomy"][k]["title"] = k
    _mutate_data_js(dst, _bare)
    result = audit_report(dst)
    c = [x for x in result.checks if x["name"] == "taxonomy_titles_resolve"]
    assert c and c[0]["status"] == "fail", c
```

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_cli_audit_report.py -v -k taxonomy_titles_resolve`
Expected: FAIL — check absent.

- [ ] **Step 3: Implement the check** (completeness block)

```python
    # Check 7 (structural): taxonomy titles resolve (no bare-ID tooltips).
    taxonomy = parsed.get("taxonomy") or {}
    bare = [
        k for k, v in taxonomy.items()
        if isinstance(v, dict) and v.get("title") in (None, "", k)
    ]
    _check(result, "taxonomy_titles_resolve", len(bare) == 0,
           f"taxonomy_entries={len(taxonomy)} bare_id={len(bare)} sample={sorted(bare)[:5]}",
           klass="structural")
```

- [ ] **Step 4: Run them — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v -k taxonomy_titles_resolve`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/test_cli_audit_report.py
git commit -m "feat(audit): taxonomy_titles_resolve completeness check

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: `audit_report_cmd` prints per-class failed counts

**Files:**
- Modify: `tools/apd_gauntlet/cli.py` (`audit_report_cmd`, lines 1184–1194)
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the failing test**

```python
def test_cli_audit_report_prints_per_class_counts(tmp_path):
    dst = _copy_example(tmp_path)
    # Break one editorial check (placeholder exec summary).
    _mutate_data_js(dst, lambda d: d.__setitem__(
        "exec_summary", ["Run summary not provided by synthesizer."]))
    result = CliRunner().invoke(main, ["audit-report", str(dst)])
    assert result.exit_code == 1, result.output
    assert "editorial_failed=" in result.output
    assert "structural_failed=" in result.output
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `pytest tests/test_cli_audit_report.py::test_cli_audit_report_prints_per_class_counts -v`
Expected: FAIL — the counts string is not printed.

- [ ] **Step 3: Update `audit_report_cmd`**

Replace the body (`tools/apd_gauntlet/cli.py:1184-1194`):

```python
def audit_report_cmd(run_dir: Path) -> None:
    """5g: structurally cross-check data.js against the authoritative YAMLs."""
    from .synthesis.audit import audit_report

    result = audit_report(run_dir)
    failed = [c for c in result.checks if c["status"] == "fail"]
    structural_failed = sum(1 for c in failed if c.get("klass", "structural") == "structural")
    editorial_failed = sum(1 for c in failed if c.get("klass") == "editorial")
    click.echo(
        f"audit-report: {result.status} ({len(result.checks)} checks, {len(failed)} failed; "
        f"structural_failed={structural_failed} editorial_failed={editorial_failed})"
    )
    for c in failed:
        click.echo(f"  FAIL [{c.get('klass', 'structural')}]: {c['name']} — {c['detail']}", err=True)
    if result.status == "fail":
        raise SystemExit(1)
```

- [ ] **Step 4: Run it — expect PASS**

Run: `pytest tests/test_cli_audit_report.py -v -k "per_class_counts or exit_code"`
Expected: PASS (the existing `test_cli_audit_report_exit_code` still passes).

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli_audit_report.py
git commit -m "feat(cli): audit-report prints per-class failed counts

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Workflow — flip the audit loop to block on structural failure

**Files:**
- Modify: `.claude/workflows/apd-gauntlet.js` (the `synthesis-audit` loop, lines ~556–585)
- Test: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing static-source tests**

Add to `tests/test_workflow_apd_gauntlet.py` (these assert against the workflow source text — match the existing helper that reads the file, e.g. `RUNNER.read_text()` / `_text()`):

```python
def test_completeness_gate_throws_on_structural_failure():
    src = _text(RUNNER)
    assert "report completeness gate" in src
    # The throw is reachable inside the post-cap branch.
    assert "throw new Error(" in src
    assert "Refusing to ship a degraded report" in src


def test_semantic_residual_remains_non_blocking():
    src = _text(RUNNER)
    assert "residual SEMANTIC discrepancies" in src
    assert "non-blocking" in src


def test_report_writer_remediation_reads_report_audit():
    src = _text(RUNNER)
    assert "report-audit.yaml" in src
    # The remediation prompt instructs addressing failed editorial checks.
    assert 'klass is "editorial"' in src
```

> If the test module exposes the workflow text via a different helper than `_text(RUNNER)`, use whatever `tests/test_workflow_apd_gauntlet.py` already uses (it reads `.claude/workflows/apd-gauntlet.js` at module top).

- [ ] **Step 2: Run them — expect FAILs**

Run: `pytest tests/test_workflow_apd_gauntlet.py -v -k "completeness_gate or semantic_residual or remediation_reads"`
Expected: FAIL — strings not present yet.

- [ ] **Step 3: Edit the audit loop**

In `.claude/workflows/apd-gauntlet.js`, replace the loop tail (currently lines 569–584, from `const structuralOk` through the closing `pyStep('build-report', ...)`):

```javascript
  const structuralOk = audit && audit.status === 'ok';
  const semanticOk = typeof auditor === 'string' && /GATE:\s*pass/i.test(auditor);
  if (structuralOk && semanticOk) { break; }
  if (i === 2) {
    // Report completeness gate: a structural failure must NEVER ship. The LLM
    // auditor's semantic residual (faithfulness judgment) stays non-blocking.
    if (!structuralOk) {
      throw new Error(
        'report completeness gate: audit-report still FAILED after 2 remediations — ' +
        'the HTML report is structurally incomplete (see ' + runDir +
        '/40-synthesis/report-audit.yaml). Refusing to ship a degraded report.');
    }
    log('report audit: residual SEMANTIC discrepancies after 2 remediations; surfacing non-blocking.');
    break;
  }
  critique = auditor;
  // Feed BOTH the structural audit (report-audit.yaml) AND the semantic critique back
  // into 5e, then rebuild 5f. The report-writer reads report-audit.yaml and fixes any
  // failed editorial completeness checks (exec_summary/posture_summary/headline/next_steps).
  llmStep('apd-report-writer',
    'Read ' + runDir + '/40-synthesis/report-audit.yaml: address EVERY failed check whose ' +
    'klass is "editorial" by regenerating 40-synthesis/report-data.yaml + advisory-report.md ' +
    '(exec_summary paragraphs, posture_summary, headline_findings, next_steps). ALSO address ' +
    'this semantic critique. CRITIQUE: ' + critique,
    { phase: 'synthesis-report', label: 'report-writer-attempt-' + (i + 1),
      outputs: runDir + '/40-synthesis/report-data.yaml' });
  pyStep('build-report', { phase: 'synthesis-build', label: 'build-report-attempt-' + (i + 1),
    outputs: runDir + '/40-synthesis/report-html/data.js' });
```

- [ ] **Step 4: Run them — expect PASS**

Run: `pytest tests/test_workflow_apd_gauntlet.py -v`
Expected: all PASS (including the pre-existing `test_audit_loop_cap_literal_present` — the `i <= 2` cap literal is unchanged).

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tests/test_workflow_apd_gauntlet.py
git commit -m "feat(workflow): block run on unresolved report-completeness failure

The synthesis-audit loop now THROWS after the N=2 cap when the structural
audit still fails, instead of surfacing non-blocking. Semantic-only residual
remains non-blocking. The report-writer remediation reads report-audit.yaml to
fix failed editorial completeness checks.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Regression guard + full integration

Prove the gate yields zero failures on every real run, and the whole suite/lint/types are clean.

**Files:**
- Test: `tests/test_cli_audit_report.py`

- [ ] **Step 1: Write the regression-guard test**

Add to `tests/test_cli_audit_report.py`:

```python
import pytest

SHIPPED_RUNS = sorted((REPO / "runs").glob("apd-20260527-*"))


@pytest.mark.parametrize("run_dir", SHIPPED_RUNS, ids=lambda p: p.name)
def test_completeness_gate_passes_on_shipped_runs(run_dir):
    result = audit_report(run_dir)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", f"{run_dir.name}: {failed}"


def test_completeness_gate_passes_on_enriched_example(tmp_path):
    dst = _copy_example(tmp_path)
    result = audit_report(dst)
    failed = [c for c in result.checks if c["status"] == "fail"]
    assert result.status == "pass", failed
    # All eight completeness checks are present.
    names = {c["name"] for c in result.checks}
    for expected in (
        "exec_summary_present", "editorial_sections_present", "attack_paths_present",
        "d3fend_overlay_present", "apd_matrix_nonempty", "coverage_rollups_nonempty",
        "taxonomy_titles_resolve", "section_errors_empty",
    ):
        assert expected in names, f"missing check {expected}"
```

- [ ] **Step 2: Run it — expect PASS (this is the false-positive guard)**

Run: `pytest tests/test_cli_audit_report.py -v -k "shipped_runs or enriched_example"`
Expected: all PASS. **If a shipped run fails a check, do not weaken the check — investigate:** either the run's `data.js` is genuinely degraded (rebuild it with `apd-gauntlet build-report runs/<run>` and confirm), or the exemption logic is too strict (re-examine that check's exemption against the spec). Record any rebuilt `data.js` in the commit.

- [ ] **Step 3: Full suite + lint + types**

Run:

```bash
pytest -q
ruff check tools/ tests/
mypy tools/
for run in runs/apd-20260527-* examples/apd-20260601-claim-event-bus/expected; do
    apd-gauntlet build-report "$run" --quiet && apd-gauntlet audit-report "$run"
done
```

Expected: pytest all-pass; ruff clean; mypy clean; every `build-report` then `audit-report` exits 0 (`audit-report: pass`).

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli_audit_report.py
git commit -m "test(audit): regression guard — completeness gate passes on all shipped runs

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage.** Every spec check maps to a task:
- Check 1 exec_summary_present → Task 4. Check 8 editorial_sections_present → Task 4.
- Check 2 counts (existing) → unchanged; covered by `id_coverage_*` / `count_parity_*` and re-asserted in Task 11.
- Check 3 attack_paths_present → Task 5. Check 4 d3fend_overlay_present → Task 6.
- Check 5 section_errors_empty (existing) → unchanged; asserted present in Task 11.
- Check 6 apd_matrix_nonempty + coverage_rollups_nonempty → Task 7. Check 7 taxonomy_titles_resolve → Task 8.
- `klass` classification → Task 2. Per-class CLI counts → Task 9. Self-heal-then-block workflow flip → Task 10. Fixture enrichment → Task 3. Regression guard → Task 11. Spec C2/C3 receipt-counts refinement documented in "Source spec & one refinement."

**Placeholder scan.** No TODO/TBD. Each code step shows complete code; each test step shows the test; each run step shows the command + expected output. The only deferred value is the `headline_findings` ids in Task 3, which Step 1 extracts deterministically and Step 2 pins (with the known ids inline as the default).

**Type/name consistency.** Check names (`exec_summary_present`, `editorial_sections_present`, `attack_paths_present`, `d3fend_overlay_present`, `apd_matrix_nonempty`, `coverage_rollups_nonempty`, `taxonomy_titles_resolve`), `klass` values (`structural`/`editorial`), `EXEC_SUMMARY_PLACEHOLDER`, and the `_mutate_data_js` test helper are used identically across tasks. `_check(..., klass=...)` signature (Task 2) matches every new call (Tasks 4–8). `nist`/`attack`/`deduped_f`/`apath_f`/`synth`/`parsed`/`ap` reuse the names already bound in `audit_report`.

**Scope.** One Python module + one CLI command + one workflow loop + one schema + one fixture + tests. No React/template changes, no new command, no global receipt-schema change, LLM auditor untouched.
