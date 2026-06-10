# Per-finding attack-path visualization (hop-strip) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed a compact, deterministic "subway-map" attack-path strip in each `apath-*` **risk** finding's detail card — showing the ordered path, the ⚠ vuln hop, and layered 💡 fix / 🛡 D3FEND-choke-point recommendation markers — plus a reverse "view full graph →" link to the Attack Paths tab.

**Architecture:** A new pure helper `_attack_path_context()` in the report transform derives the per-finding path block from the already-on-disk synthesis YAML (`asset-graph.yaml` / `attack-paths.yaml` / `defense-graph.yaml`) via the verified `id == "apath-" + sha256(path_id)[:8]` join — no `finding.schema.json` change. A new presentational `AttackPathStrip` JSX component renders it inside `FindingDetail`. No model/agent/skill runs at build or render time.

**Tech Stack:** Python 3 (transform/audit, `pytest`), React 18 JSX bundled by esbuild (`tools/build_report_template.py`), CSS custom properties. Determinism is a hard requirement (§3 of the spec) and is guarded by a test.

**Spec:** `docs/superpowers/specs/2026-06-10-attack-path-finding-visualization-design.md`

---

## File structure

| File | Responsibility | Change |
|---|---|---|
| `tools/apd_gauntlet/report/transform.py` | Build `window.APD_DATA`. | Add module-level lookup primitives + `_attack_path_context`; call it from `findings_array`. |
| `report-template/components.jsx` | Shared presentational components (window-exported). | Add `AttackPathStrip`; export it. |
| `report-template/screens/Findings.jsx` | Findings screen + `FindingDetail`. | Render `AttackPathStrip`; thread `onOpenPath`. |
| `report-template/app.jsx` | Root app, tab routing, cross-nav. | Add `onOpenPath` + `focusPathId`; pass to `Findings` and `AttackPaths`. |
| `report-template/screens/AttackPaths.jsx` | Attack Paths tab. | Accept `focusPathId`; focus/scroll the matching path. |
| `report-template/screens.css` | Screen-scoped CSS. | Add `.apath-strip__*` rules. |
| `report-template/styles.css` | Theme tokens. | Add `--rec` token (all theme blocks). |
| `tools/apd_gauntlet/data/report-template/{app.js,.source-hash,…}` | Shipped precompiled bundle (git-tracked). | Regenerated + committed (freshness gate). |
| `tools/apd_gauntlet/synthesis/audit.py` | Report completeness audit. | Add editorial check `attack_path_finding_strip_present` (testable helper). |
| `tests/unit/report/test_transform_attack_path_context.py` (new) | Transform helper unit + determinism tests. | Create. |
| `tests/unit/report/test_findings_attack_path_strip_jsx.py` (new) | Static-JSX substring tests. | Create. |
| `tests/unit/synthesis/test_attack_path_strip_check.py` (new) | Audit-helper unit test. | Create. |
| `docs/attack-path-analysis.md`, `docs/html-report.md`, `CHANGELOG.md`, `docs/adrs/0015-per-finding-attack-path-strip.md` | Docs + ADR. | Edit / create. |

**Commit discipline:** Python tasks (1–3, 9) commit individually. The report-template tasks (4–8) **must not commit individually** — every commit touching `report-template/` must include the rebuilt, git-tracked bundle or the freshness CI gate fails. Stage tasks 4–7, then **Task 8 rebuilds the bundle and makes one commit** for all of them. Per-task verification for 4–7 is the static-JSX test (which reads `.jsx` source, no bundle needed).

---

## Task 1: Transform — extract shared lookup primitives (behavior-preserving refactor)

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (`attack_paths_data`, ~lines 1319-1408; add module-level helpers above it)
- Test: `tests/unit/report/test_transform_attack_path_context.py` (create)
- Guard: `tests/unit/report/test_transform_attack_paths.py` (existing — must stay green)

- [ ] **Step 1: Write the failing test for the new primitives**

Create `tests/unit/report/test_transform_attack_path_context.py`:

```python
# tests/unit/report/test_transform_attack_path_context.py
from __future__ import annotations

from apd_gauntlet.report import transform as T


def test_normalize_edge_type_canonicalizes():
    assert T._normalize_edge_type("trusts") == "trust_boundary"
    assert T._normalize_edge_type("finding") == "compromisable_via_finding"
    assert T._normalize_edge_type("compromisable_via_finding") == "compromisable_via_finding"
    assert T._normalize_edge_type("capability") == "mitigated_by_capability"
    assert T._normalize_edge_type("network_reachable") == "network_reachable"
    assert T._normalize_edge_type("") == "trust_boundary"


def test_build_node_edge_maps_indexes_by_id():
    ag = {
        "nodes": [{"node_id": "n1", "name": "API", "node_type": "asset"}],
        "edges": [{"edge_id": "e1", "from": "n1", "to": "n2", "edge_type": "trusts"}],
    }
    nodes, edges = T._build_node_edge_maps(ag)
    assert nodes["n1"]["name"] == "API"
    assert edges["e1"]["to"] == "n2"


def test_hop_node_resolves_name_and_type_with_fallback():
    nodes = {"n1": {"name": "API", "node_type": "service"}}
    assert T._hop_node(nodes, "n1") == {"id": "n1", "name": "API", "type": "service"}
    # Missing node falls back to the id and a default type.
    assert T._hop_node(nodes, "ghost") == {"id": "ghost", "name": "ghost", "type": "asset"}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/unit/report/test_transform_attack_path_context.py -v`
Expected: FAIL with `AttributeError: module 'apd_gauntlet.report.transform' has no attribute '_normalize_edge_type'`.

- [ ] **Step 3: Add the module-level primitives**

In `tools/apd_gauntlet/report/transform.py`, add these helpers **immediately above** `def attack_paths_data(` (around line 1318). (`import hashlib` and `import re` are already present at lines 8 and 11 — no import change needed.)

```python
def _build_node_edge_maps(
    asset_graph: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Index an asset graph's nodes and edges by their ids. Shared by
    attack_paths_data and _attack_path_context so both resolve identically."""
    raw_nodes = (asset_graph or {}).get("nodes") or []
    raw_edges = (asset_graph or {}).get("edges") or []
    node_by_id = {str(n.get("node_id", "")): n for n in raw_nodes if isinstance(n, dict)}
    edge_by_id = {str(e.get("edge_id", "")): e for e in raw_edges if isinstance(e, dict)}
    return node_by_id, edge_by_id


def _normalize_edge_type(raw_type: str) -> str:
    """Collapse raw asset-graph edge_type values onto the canonical set used by
    the renderer chips. Identical to the inline mapping attack_paths_data used."""
    if raw_type == "trusts":
        return "trust_boundary"
    if raw_type in ("compromisable_via_finding", "finding"):
        return "compromisable_via_finding"
    if raw_type in ("mitigated_by_capability", "capability"):
        return "mitigated_by_capability"
    return raw_type or "trust_boundary"


def _hop_node(node_by_id: dict[str, dict[str, Any]], node_id: str) -> dict[str, Any]:
    """Resolve a node id to {id, name, type} for a hop-strip station. Falls back
    to the id and a default type when the node is missing (existing behavior)."""
    n = node_by_id.get(node_id) or {}
    return {
        "id": node_id,
        "name": str(n.get("name") or node_id),
        "type": str(n.get("node_type") or "asset"),
    }
```

- [ ] **Step 4: Refactor `attack_paths_data` to use the primitives (no output change)**

In `attack_paths_data`, replace the local map construction (lines ~1326-1333):

```python
    raw_nodes = artifacts.asset_graph.get("nodes") or []
    raw_edges = artifacts.asset_graph.get("edges") or []
    node_by_id: dict[str, dict[str, Any]] = {
        str(n.get("node_id", "")): n for n in raw_nodes if isinstance(n, dict)
    }
    edge_by_id: dict[str, dict[str, Any]] = {
        str(e.get("edge_id", "")): e for e in raw_edges if isinstance(e, dict)
    }
```

with:

```python
    raw_nodes = artifacts.asset_graph.get("nodes") or []
    raw_edges = artifacts.asset_graph.get("edges") or []
    node_by_id, edge_by_id = _build_node_edge_maps(artifacts.asset_graph)
```

(`raw_nodes`/`raw_edges` are still used later for the summary block, so keep them.)

Then inside the `_edges_detailed` closure, replace the inline normalization (lines ~1352-1360):

```python
            # Normalise edge_type to the three canonical values.
            if raw_type == "trusts":
                edge_type = "trust_boundary"
            elif raw_type in ("compromisable_via_finding", "finding"):
                edge_type = "compromisable_via_finding"
            elif raw_type in ("mitigated_by_capability", "capability"):
                edge_type = "mitigated_by_capability"
            else:
                edge_type = raw_type or "trust_boundary"
```

with:

```python
            edge_type = _normalize_edge_type(raw_type)
```

- [ ] **Step 5: Run the new + existing attack-path tests to verify green**

Run: `pytest tests/unit/report/test_transform_attack_path_context.py tests/unit/report/test_transform_attack_paths.py -v`
Expected: PASS (new primitive tests pass; existing `attack_paths_data` tests confirm the refactor preserved output).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_attack_path_context.py
git commit -m "refactor(report): extract asset-graph lookup primitives in transform"
```

---

## Task 2: Transform — `_attack_path_context` + wire into `findings_array`

**Files:**
- Modify: `tools/apd_gauntlet/report/transform.py` (add `_attack_path_context` after the Task 1 helpers; call from `findings_array` ~line 423)
- Test: `tests/unit/report/test_transform_attack_path_context.py`

- [ ] **Step 1: Write the failing tests (with a synthetic artifact factory)**

Append to `tests/unit/report/test_transform_attack_path_context.py`:

```python
import hashlib

from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import findings_array


def _apath_id(path_id: str) -> str:
    return "apath-" + hashlib.sha256(path_id.encode()).hexdigest()[:8]


def _artifacts(*, findings, asset_graph, attack_paths, defense_graph=None):
    """A RunArtifacts with only the fields the attack-path strip path reads."""
    return RunArtifacts(
        run_id="r", framework_version="1", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory={}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        asset_graph=asset_graph, attack_paths=attack_paths,
        defense_graph=defense_graph, attack_path_findings=findings,
        report_data=None, metrics={"schema_version": 1, "findings_total": 0},
    )


# A 3-hop path: internet --net--> api --compromisable(conf-1)--> worker --authz(BOTTLENECK)--> db
_ASSET_GRAPH = {
    "nodes": [
        {"node_id": "atk-1", "name": "Internet", "node_type": "attacker_position"},
        {"node_id": "svc-api", "name": "API", "node_type": "asset"},
        {"node_id": "svc-wkr", "name": "Worker", "node_type": "asset"},
        {"node_id": "db-1", "name": "Datastore", "node_type": "crown_jewel"},
    ],
    "edges": [
        {"edge_id": "edge-0000aaaa", "from": "atk-1", "to": "svc-api",
         "edge_type": "network_reachable", "confidence": "medium"},
        {"edge_id": "edge-0000bbbb", "from": "svc-api", "to": "svc-wkr",
         "edge_type": "compromisable_via_finding", "confidence": "high",
         "finding_id": "conf-11111111"},
        {"edge_id": "edge-0000cccc", "from": "svc-wkr", "to": "db-1",
         "edge_type": "authz_grants", "confidence": "high"},
    ],
}
_PATH = {
    "path_id": "path-12345678",
    "attacker_position": "atk-1",
    "crown_jewel": "db-1",
    "edges": ["edge-0000aaaa", "edge-0000bbbb", "edge-0000cccc"],
    "bottleneck_edges": ["edge-0000cccc"],
    "hop_count": 3,
    "feasibility": "medium",
    "severity_sum": 7,
    "mitigation_count": 0,
}
_DEFENSE_GRAPH = {
    "bottleneck_overlays": [
        {"edge_id": "edge-0000cccc", "paths_traversing": 6,
         "exposed_attack_techniques": ["T1190"],
         "candidate_d3fend": [], "existing_capability_backing": [],
         "net_new_d3fend": ["D3-NTA", "D3-MFA"]},
    ],
}


def _risk_finding(**over):
    f = {
        "id": _apath_id("path-12345678"), "disposition": "risk", "severity": "high",
        "confidence": "medium", "title": "t", "summary": "s", "detail": "d",
        "evidence": [{"artifact": "40-synthesis/attack-paths.yaml",
                      "locator": "path-12345678", "excerpt": "x"}],
        "recommendation": {"posture": "required", "summary": "Add a control on the highest-confidence edge"},
    }
    f.update(over)
    return f


def _get_block(findings, asset_graph=_ASSET_GRAPH, attack_paths=None, defense_graph=_DEFENSE_GRAPH):
    arts = _artifacts(findings=findings, asset_graph=asset_graph,
                      attack_paths=attack_paths or {"paths": [_PATH]},
                      defense_graph=defense_graph)
    arr = findings_array(arts, headline_supplement=None)
    return {f["id"]: f for f in arr}


def test_risk_apath_finding_gets_attack_path_block():
    f = _risk_finding()
    block = _get_block([f])[f["id"]]["attack_path"]
    assert block["path_id"] == "path-12345678"
    assert block["attacker"]["name"] == "Internet"
    assert block["crown_jewel"]["name"] == "Datastore"
    assert [h["edge_type"] for h in block["hops"]] == [
        "network_reachable", "compromisable_via_finding", "authz_grants"]
    # Vuln + fix land on the compromisable edge; it carries the on-path finding id.
    vuln = [h for h in block["hops"] if h["is_vuln"]]
    assert len(vuln) == 1 and vuln[0]["finding_id"] == "conf-11111111"
    fix = [h for h in block["hops"] if h["is_fix"]]
    assert len(fix) == 1 and fix[0]["edge_id"] == "edge-0000bbbb"
    # Choke-point overlay lands on the bottleneck edge, D3FEND sorted.
    choke = [h for h in block["hops"] if h["chokepoint"]]
    assert len(choke) == 1 and choke[0]["edge_id"] == "edge-0000cccc"
    assert choke[0]["chokepoint"]["d3fend"] == ["D3-MFA", "D3-NTA"]
    assert choke[0]["chokepoint"]["paths_traversing"] == 6


def test_non_risk_apath_finding_gets_no_block():
    f = _risk_finding(disposition="uncertainty")
    assert "attack_path" not in _get_block([f])[f["id"]]


def test_non_apath_finding_gets_no_block():
    f = _risk_finding(id="conf-22222222")
    assert "attack_path" not in _get_block([f])[f["id"]]


def test_unresolvable_apath_finding_gets_no_block():
    # Aggregate-style id that does not hash from any path_id, no usable locator.
    f = _risk_finding(id="apath-deadbeef", evidence=[])
    assert "attack_path" not in _get_block([f])[f["id"]]


def test_locator_fallback_resolves_when_hash_misses():
    # id does not hash-match, but an evidence locator names the path_id.
    f = _risk_finding(id="apath-deadbeef",
                      evidence=[{"artifact": "a", "locator": "edges (path path-12345678)", "excerpt": "x"}])
    block = _get_block([f])[f["id"]].get("attack_path")
    assert block is not None and block["path_id"] == "path-12345678"


def test_no_bottleneck_overlay_degrades_to_fix_only():
    f = _risk_finding()
    block = _get_block([f], defense_graph={"bottleneck_overlays": []})[f["id"]]["attack_path"]
    assert all(h["chokepoint"] is None for h in block["hops"])
    assert any(h["is_fix"] for h in block["hops"])
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/report/test_transform_attack_path_context.py -k "block or fallback or degrades" -v`
Expected: FAIL — `findings_array` output has no `attack_path` key (`KeyError`).

- [ ] **Step 3: Implement `_attack_path_context`**

Add to `tools/apd_gauntlet/report/transform.py` directly below `_hop_node` (from Task 1):

```python
_PATH_ID_RE = re.compile(r"path-[0-9a-f]{8}")
_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "": 0}


def _attack_path_context(
    finding: dict[str, Any], artifacts: RunArtifacts
) -> dict[str, Any] | None:
    """Derive the per-finding attack-path strip block, or None.

    Deterministic and side-effect-free: a pure function of the finding plus the
    on-disk synthesis artifacts. Attaches ONLY to apath-* findings with
    disposition == "risk" that resolve to exactly one enumerated path (via the
    id == "apath-" + sha256(path_id)[:8] join, with an evidence-locator
    fallback). No new prose is synthesized — markers surface existing fields.
    """
    fid = str(finding.get("id") or "")
    if not fid.startswith("apath-") or finding.get("disposition") != "risk":
        return None
    if artifacts.attack_paths is None or artifacts.asset_graph is None:
        return None

    raw_paths = [p for p in (artifacts.attack_paths.get("paths") or []) if isinstance(p, dict)]
    paths_by_id = {str(p.get("path_id")): p for p in raw_paths}
    apath_id_to_path = {
        "apath-" + hashlib.sha256(str(p.get("path_id")).encode()).hexdigest()[:8]: p
        for p in raw_paths
    }

    path = apath_id_to_path.get(fid)
    if path is None:  # locator fallback: scan evidence for a known path_id token
        for ev in finding.get("evidence", []) or []:
            for tok in _PATH_ID_RE.findall(str((ev or {}).get("locator", ""))):
                if tok in paths_by_id:
                    path = paths_by_id[tok]
                    break
            if path is not None:
                break
    if path is None:
        return None

    node_by_id, edge_by_id = _build_node_edge_maps(artifacts.asset_graph)
    bottleneck_ids = {str(e) for e in (path.get("bottleneck_edges") or [])}

    overlays_by_edge: dict[str, dict[str, Any]] = {}
    if artifacts.defense_graph is not None:
        for o in artifacts.defense_graph.get("bottleneck_overlays") or []:
            if isinstance(o, dict) and o.get("edge_id"):
                overlays_by_edge[str(o["edge_id"])] = o

    hops: list[dict[str, Any]] = []
    fix_edge_id: str | None = None
    fix_rank = -1
    for eid in (str(e) for e in (path.get("edges") or [])):
        e = edge_by_id.get(eid, {})
        edge_type = _normalize_edge_type(str(e.get("edge_type", "")))
        confidence = str(e.get("confidence", ""))
        is_vuln = edge_type == "compromisable_via_finding"
        if is_vuln and _CONFIDENCE_RANK.get(confidence, 0) > fix_rank:
            fix_rank = _CONFIDENCE_RANK.get(confidence, 0)
            fix_edge_id = eid
        chokepoint = None
        if eid in bottleneck_ids and eid in overlays_by_edge:
            ov = overlays_by_edge[eid]
            chokepoint = {
                "d3fend": sorted(str(d) for d in (ov.get("net_new_d3fend") or [])),
                "paths_traversing": ov.get("paths_traversing"),
            }
        hops.append({
            "edge_id": eid,
            "from": _hop_node(node_by_id, str(e.get("from", ""))),
            "to": _hop_node(node_by_id, str(e.get("to", ""))),
            "edge_type": edge_type,
            "confidence": confidence,
            "is_bottleneck": eid in bottleneck_ids,
            "is_vuln": is_vuln,
            "is_fix": False,
            "finding_id": e.get("finding_id") if is_vuln else None,
            "chokepoint": chokepoint,
        })
    for h in hops:
        if h["edge_id"] == fix_edge_id:
            h["is_fix"] = True

    rec = finding.get("recommendation") or {}
    return {
        "path_id": path.get("path_id"),
        "attacker": _hop_node(node_by_id, str(path.get("attacker_position", ""))),
        "crown_jewel": _hop_node(node_by_id, str(path.get("crown_jewel", ""))),
        "hop_count": path.get("hop_count"),
        "feasibility": path.get("feasibility"),
        "hops": hops,
        "recommendation_excerpt": rec.get("summary") or rec.get("detail") or "",
    }
```

- [ ] **Step 4: Wire it into `findings_array`**

In `findings_array`, replace the append at line ~424-427:

```python
        if fid in headline_ranks:
            entry["headline"] = True
            entry["headline_rank"] = headline_ranks[fid]
        out.append(entry)
```

with:

```python
        if fid in headline_ranks:
            entry["headline"] = True
            entry["headline_rank"] = headline_ranks[fid]
        ctx = _attack_path_context(f, artifacts)
        if ctx is not None:
            entry["attack_path"] = ctx
        out.append(entry)
```

- [ ] **Step 5: Run to verify green**

Run: `pytest tests/unit/report/test_transform_attack_path_context.py tests/unit/report/test_transform_findings.py -v`
Expected: PASS (all new tests + existing findings_array tests).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py tests/unit/report/test_transform_attack_path_context.py
git commit -m "feat(report): derive per-finding attack-path block in transform"
```

---

## Task 3: Transform — determinism guard

**Files:**
- Test: `tests/unit/report/test_transform_attack_path_context.py`

- [ ] **Step 1: Write the determinism test**

Append:

```python
def test_attack_path_block_is_deterministic():
    f = _risk_finding()
    arts = _artifacts(findings=[f], asset_graph=_ASSET_GRAPH,
                      attack_paths={"paths": [_PATH]}, defense_graph=_DEFENSE_GRAPH)
    a = findings_array(arts, headline_supplement=None)
    b = findings_array(arts, headline_supplement=None)
    assert a == b  # byte-for-byte stable across invocations
    # D3FEND lists are emitted sorted (no set-iteration order leaks).
    choke = next(h for h in a[0]["attack_path"]["hops"] if h["chokepoint"])
    assert choke["chokepoint"]["d3fend"] == sorted(choke["chokepoint"]["d3fend"])
```

- [ ] **Step 2: Run to verify it passes (implementation already deterministic)**

Run: `pytest tests/unit/report/test_transform_attack_path_context.py::test_attack_path_block_is_deterministic -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/report/test_transform_attack_path_context.py
git commit -m "test(report): guard determinism of the attack-path block"
```

---

## Task 4: JSX — `AttackPathStrip` component (no commit; staged for Task 8)

**Files:**
- Modify: `report-template/components.jsx` (add component before the final `Object.assign(window, …)` at line ~407; add `AttackPathStrip` to that export)
- Test: `tests/unit/report/test_findings_attack_path_strip_jsx.py` (create)

- [ ] **Step 1: Write the failing static-JSX test**

Create `tests/unit/report/test_findings_attack_path_strip_jsx.py`:

```python
# tests/unit/report/test_findings_attack_path_strip_jsx.py
"""Static-text regression tests for the per-finding attack-path strip
(no JS test runner in this repo — assert source invariants)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
COMPONENTS = REPO / "report-template" / "components.jsx"


def test_attack_path_strip_component_defined_and_exported():
    src = COMPONENTS.read_text(encoding="utf-8")
    assert "function AttackPathStrip(" in src
    assert "AttackPathStrip" in src.split("Object.assign(window")[1]  # in the export


def test_attack_path_strip_renders_layered_markers():
    src = COMPONENTS.read_text(encoding="utf-8")
    # vuln, fix, choke-point markers all present
    assert "h.is_vuln" in src and "h.is_fix" in src and "h.chokepoint" in src
    # reverse-nav affordance gated on onOpenPath
    assert "onOpenPath" in src and "view full graph" in src
    # D3FEND techniques surfaced on the choke-point
    assert "chokepoint.d3fend" in src
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/report/test_findings_attack_path_strip_jsx.py -v`
Expected: FAIL (`function AttackPathStrip(` not found).

- [ ] **Step 3: Add the component**

In `report-template/components.jsx`, insert immediately **before** the closing `Object.assign(window, {` (line ~407):

```jsx
// ── Per-finding attack-path strip ("subway map") ──
// Renders one enumerated path for an apath risk finding: ordered stations
// (attacker → crown jewel) with edge segments colored by type, and layered
// markers — ⚠ vuln (compromisable edge), 💡 fix-at-source (highest-confidence
// compromisable edge), 🛡 D3FEND choke-point (bottleneck edge with overlay).
// Pure presentational; consumes finding.attack_path built by the transform.
function AttackPathStrip({ attackPath, onOpenPath }) {
  const ap = attackPath;
  const hops = (ap && ap.hops) || [];
  if (!ap || hops.length === 0) return null;

  const SEG = {
    compromisable_via_finding: "var(--sev-high)",
    mitigated_by_capability: "var(--sev-low)",
  };
  const nm = (n) => (n && (n.name || n.id)) || "?";

  function Station({ node, kind }) {
    const big = kind === "attacker" || kind === "jewel";
    const bg = kind === "attacker" ? "var(--sev-high)"
      : kind === "jewel" ? "var(--accent)" : "var(--ink-3)";
    const glyph = kind === "attacker" ? "🌐 " : kind === "jewel" ? "💎 " : "";
    return (
      <div className="apath-strip__station" title={node ? `${nm(node)} (${node.type})` : ""}>
        <span className="apath-strip__dot"
          style={{ background: bg, width: big ? 16 : 11, height: big ? 16 : 11 }} />
        <span className="apath-strip__name">{glyph}{nm(node)}</span>
      </div>
    );
  }

  return (
    <div className="apath-strip">
      <div className="apath-strip__head">
        <span className="apath-strip__pid mono">{ap.path_id}</span>
        <span>{ap.hop_count} hop{ap.hop_count === 1 ? "" : "s"}</span>
        <span>feasibility {ap.feasibility}</span>
        {typeof onOpenPath === "function" && (
          <button type="button" className="apath-strip__open"
            title="Open this path in the Attack Paths tab"
            onClick={() => onOpenPath(ap.path_id)}>view full graph →</button>
        )}
      </div>
      <div className="apath-strip__rail">
        <Station node={ap.attacker} kind="attacker" />
        {hops.map((h, i) => {
          const isLast = i === hops.length - 1;
          const color = SEG[h.edge_type] || "var(--rule)";
          return (
            <React.Fragment key={h.edge_id}>
              <div className="apath-strip__seg" title={`${h.edge_type} · ${h.confidence || "?"}`}>
                <div className="apath-strip__above">
                  {h.is_vuln && (
                    <span style={{ color: "var(--sev-high)" }}>
                      ⚠ vuln{h.finding_id ? ` ${h.finding_id}` : ""}
                    </span>
                  )}
                  {h.chokepoint && (
                    <span style={{ color: "var(--rec)" }}>
                      ⛓ choke{h.chokepoint.paths_traversing ? ` ·${h.chokepoint.paths_traversing}` : ""}
                    </span>
                  )}
                </div>
                <div className="apath-strip__line"
                  style={{ background: color, height: h.is_bottleneck ? 7 : 4 }} />
                <div className="apath-strip__below">
                  {h.is_fix && <span style={{ color: "var(--rec)" }}>💡 fix here</span>}
                  {h.chokepoint && (h.chokepoint.d3fend || []).length > 0 && (
                    <span style={{ color: "var(--rec)" }}>🛡 {h.chokepoint.d3fend.join(" ")}</span>
                  )}
                </div>
              </div>
              <Station node={h.to} kind={isLast ? "jewel" : "mid"} />
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
```

Then add `AttackPathStrip` to the export object (line ~409):

```jsx
Object.assign(window, {
  SeverityPill, DispositionMark, MaturityMark, CopyPill, TaxonomyTag, TagRow, ToastHost, DiagnosticsBanner,
  GraphView, AttackPathStrip,
  GOAL_LABELS, GOAL_SHORT, TIER_LABELS, TIER_GOALS,
});
```

- [ ] **Step 4: Run the static test to verify green**

Run: `pytest tests/unit/report/test_findings_attack_path_strip_jsx.py -v`
Expected: PASS.

- [ ] **Step 5: Stage only (do NOT commit — bundle rebuild lands in Task 8)**

```bash
git add report-template/components.jsx tests/unit/report/test_findings_attack_path_strip_jsx.py
```

---

## Task 5: JSX — render in `FindingDetail` + thread `onOpenPath` (no commit; staged for Task 8)

**Files:**
- Modify: `report-template/screens/Findings.jsx` (`Findings` signature line 5; the two `FindingDetail` call sites lines 113 & 199; `FindingDetail` signature line 206; insert strip after Summary ~line 253)
- Test: `tests/unit/report/test_findings_attack_path_strip_jsx.py`

- [ ] **Step 1: Add failing static-JSX assertions**

Append to `tests/unit/report/test_findings_attack_path_strip_jsx.py`:

```python
FINDINGS = REPO / "report-template" / "screens" / "Findings.jsx"


def test_finding_detail_renders_strip_guarded_on_attack_path():
    src = FINDINGS.read_text(encoding="utf-8")
    assert "f.attack_path &&" in src
    assert "<AttackPathStrip" in src
    # FindingDetail accepts onOpenPath and forwards it to the strip
    assert "onOpenPath" in src
    # Findings passes onOpenPath into both FindingDetail call sites
    assert src.count("onOpenPath={onOpenPath}") >= 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/report/test_findings_attack_path_strip_jsx.py::test_finding_detail_renders_strip_guarded_on_attack_path -v`
Expected: FAIL.

- [ ] **Step 3: Thread `onOpenPath` through `Findings`**

Change the `Findings` signature (line 5):

```jsx
function Findings({ data, selectedId, onSelect, layout = "two-pane", initialFilter = null, onOpenPath }) {
```

Change the stacked-layout call site (line 113):

```jsx
          {filtered.map((f) => <FindingDetail key={f.id} finding={f} embedded onOpenPath={onOpenPath} />)}
```

Change the two-pane call site (line 199):

```jsx
        {selected ? <FindingDetail finding={selected} onOpenPath={onOpenPath} /> : <div className="empty-state">Select a finding</div>}
```

- [ ] **Step 4: Render the strip in `FindingDetail`**

Change the `FindingDetail` signature (line 206):

```jsx
function FindingDetail({ finding, embedded = false, onOpenPath }) {
```

Insert this block **immediately after** the Summary `</section>` (after line 253) and before the Detail block:

```jsx
        {f.attack_path && (
          <section className="finding-detail__block">
            <div className="finding-detail__block-head"><span>Attack path</span></div>
            <AttackPathStrip attackPath={f.attack_path} onOpenPath={onOpenPath} />
          </section>
        )}
```

- [ ] **Step 5: Run the static tests to verify green**

Run: `pytest tests/unit/report/test_findings_attack_path_strip_jsx.py -v`
Expected: PASS.

- [ ] **Step 6: Stage only (do NOT commit yet)**

```bash
git add report-template/screens/Findings.jsx tests/unit/report/test_findings_attack_path_strip_jsx.py
```

---

## Task 6: JSX — `onOpenPath` handler in `app.jsx` + focus in `AttackPaths.jsx` (no commit; staged for Task 8)

**Files:**
- Modify: `report-template/app.jsx` (state ~line 16; handler ~line 58; `Findings` props ~line 124; `AttackPaths` props ~line 135)
- Modify: `report-template/screens/AttackPaths.jsx` (signature line 8; add focus effect; tag path `<li>` line 156)
- Test: `tests/unit/report/test_findings_attack_path_strip_jsx.py`

- [ ] **Step 1: Add failing static-JSX assertions**

Append to `tests/unit/report/test_findings_attack_path_strip_jsx.py`:

```python
APP = REPO / "report-template" / "app.jsx"
ATTACK_PATHS = REPO / "report-template" / "screens" / "AttackPaths.jsx"


def test_app_defines_and_wires_on_open_path():
    src = APP.read_text(encoding="utf-8")
    assert "const onOpenPath" in src
    assert 'setActiveTab("attack_paths")' in src
    assert "focusPathId" in src
    assert "onOpenPath={onOpenPath}" in src  # passed to Findings


def test_attack_paths_accepts_and_applies_focus():
    src = ATTACK_PATHS.read_text(encoding="utf-8")
    assert "focusPathId" in src
    # path rows are addressable so the focus effect can scroll/open them
    assert "ap-row-${p.path_id}" in src
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/report/test_findings_attack_path_strip_jsx.py -k "on_open_path or focus" -v`
Expected: FAIL.

- [ ] **Step 3: Add state + handler in `app.jsx`**

After line 16 (`const [selectedFinding, setSelectedFinding] = useState(null);`) add:

```jsx
  const [focusPathId, setFocusPathId] = useState(null);
```

After the `onOpenFinding` handler (line 58) add:

```jsx
  const onOpenPath = (pathId) => {
    setFocusPathId(pathId);
    setActiveTab("attack_paths");
  };
```

Pass `onOpenPath` to `Findings` (line 124-131 block):

```jsx
        {activeTab === "findings" && (
          <Findings
            data={data}
            selectedId={selectedFinding}
            onSelect={setSelectedFinding}
            layout={t.findingsLayout}
            onOpenPath={onOpenPath}
          />
        )}
```

Pass `focusPathId` to `AttackPaths` (line 135-137 block):

```jsx
        {activeTab === "attack_paths" && (
          <AttackPaths data={data} onOpenFinding={onOpenFinding} focusPathId={focusPathId} />
        )}
```

- [ ] **Step 4: Apply focus in `AttackPaths.jsx`**

Change the signature (line 8):

```jsx
function AttackPaths({ data, onOpenFinding, focusPathId = null }) {
```

After the `selectedPathId` state declaration (line 12), add the focus effect:

```jsx
  React.useEffect(() => {
    if (!focusPathId) return;
    setSelectedPathId(focusPathId);
    const row = document.getElementById(`ap-row-${focusPathId}`);
    if (row) {
      const det = row.closest("details");
      if (det) det.open = true;
      row.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusPathId]);
```

Add an `id` to the path `<li>` (line 156-163). Change:

```jsx
                  <li
                    key={p.path_id}
                    className={`attack-path attack-path--${p.feasibility || "unknown"}`}
```

to:

```jsx
                  <li
                    key={p.path_id}
                    id={`ap-row-${p.path_id}`}
                    className={`attack-path attack-path--${p.feasibility || "unknown"}`}
```

- [ ] **Step 5: Run the static tests to verify green**

Run: `pytest tests/unit/report/test_findings_attack_path_strip_jsx.py -v`
Expected: PASS (all assertions across Tasks 4–6).

- [ ] **Step 6: Stage only (do NOT commit yet)**

```bash
git add report-template/app.jsx report-template/screens/AttackPaths.jsx tests/unit/report/test_findings_attack_path_strip_jsx.py
```

---

## Task 7: CSS — `.apath-strip__*` rules + `--rec` token (no commit; staged for Task 8)

**Files:**
- Modify: `report-template/styles.css` (add `--rec` to each theme token block)
- Modify: `report-template/screens.css` (append `.apath-strip` rules)

- [ ] **Step 1: Add the `--rec` token**

In `report-template/styles.css`, find each theme token block that defines `--sev-high` / `--accent` (the default `:root`/`[data-theme]` blocks; recon located severity tokens around lines 53-62). In **each** such block, add a recommendation token next to the severity tokens, e.g.:

```css
  --rec: #6b4cff;   /* recommendation / D3FEND markers — distinct from --sev-* and --accent */
```

For a dark theme block use a lighter indigo for contrast:

```css
  --rec: #9d8bff;
```

(Match the existing pattern: wherever `--sev-high` is defined for a theme, define `--rec` in the same block so it recolors with the theme. If only one `:root` defines these, one addition suffices.)

- [ ] **Step 2: Append the strip layout rules**

Append to `report-template/screens.css`:

```css
/* ── Per-finding attack-path strip ("subway map") ── */
.apath-strip { margin: 0; }
.apath-strip__head {
  display: flex; align-items: center; gap: var(--space-3);
  font-family: var(--font-mono); font-size: var(--text-xs);
  color: var(--ink-3); margin-bottom: var(--space-2); flex-wrap: wrap;
}
.apath-strip__pid {
  background: var(--paper-2); border: 1px solid var(--rule);
  border-radius: 3px; padding: 1px 5px; color: var(--ink-3);
}
.apath-strip__open {
  margin-left: auto; background: none; border: none; cursor: pointer;
  color: var(--accent); font-size: var(--text-xs); padding: 0;
  text-decoration: underline; font-family: inherit;
}
.apath-strip__rail {
  display: flex; align-items: center; overflow-x: auto;
  padding: 26px 4px 24px;          /* room for above/below marker labels */
  gap: 0; min-height: 96px;
}
.apath-strip__station {
  display: flex; flex-direction: column; align-items: center;
  gap: 5px; flex: 0 0 auto; max-width: 96px; text-align: center;
}
.apath-strip__dot { border-radius: 50%; flex: 0 0 auto; }
.apath-strip__name {
  font-size: 11px; color: var(--ink); line-height: 1.15; word-break: break-word;
}
.apath-strip__seg {
  position: relative; flex: 1 1 64px; min-width: 64px;
  display: flex; flex-direction: column; justify-content: center;
}
.apath-strip__line { border-radius: 3px; width: 100%; }
.apath-strip__above, .apath-strip__below {
  position: absolute; left: 50%; transform: translateX(-50%);
  white-space: nowrap; font-size: 10px; font-weight: 700;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
}
.apath-strip__above { bottom: calc(50% + 6px); }
.apath-strip__below { top: calc(50% + 6px); }
```

- [ ] **Step 3: Stage only (do NOT commit yet)**

```bash
git add report-template/styles.css report-template/screens.css
```

---

## Task 8: Rebuild the bundle + single commit for Tasks 4–8

**Files:**
- Generated: `tools/apd_gauntlet/data/report-template/{app.js,.source-hash,screens.css,styles.css,index.html}`

- [ ] **Step 1: Rebuild the precompiled bundle**

Run: `python tools/build_report_template.py`
Expected: exits 0 and rewrites `tools/apd_gauntlet/data/report-template/app.js` + `.source-hash` (+ copied css/index.html). If it exits 2, install Node/npm first (the script shells `node .build/build.mjs`).

- [ ] **Step 2: Verify the freshness gate passes**

Run: `python tools/check_report_template_freshness.py && echo OK`
Expected: prints `OK` (recomputed sha256 == committed `.source-hash`).

- [ ] **Step 3: Run the bundle-freshness unit test + all report JSX/transform tests**

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py tests/unit/report/test_findings_attack_path_strip_jsx.py tests/unit/report/test_transform_attack_path_context.py -v`
Expected: PASS.

- [ ] **Step 4: Stage the regenerated bundle and commit Tasks 4–8 together**

```bash
git add tools/apd_gauntlet/data/report-template/
git commit -m "feat(report): per-finding attack-path strip in the Findings card

AttackPathStrip component + FindingDetail integration + reverse onOpenPath
nav + CSS (--rec token). Regenerated precompiled bundle (freshness gate)."
```

---

## Task 9: Audit — editorial `attack_path_finding_strip_present` check

**Files:**
- Modify: `tools/apd_gauntlet/synthesis/audit.py` (add a small pure helper near `_check` ~line 68; call it inside `audit_report` after the `d3fend_overlay_present` block ~line 361)
- Test: `tests/unit/synthesis/test_attack_path_strip_check.py` (create)

- [ ] **Step 1: Write the failing helper test**

Create `tests/unit/synthesis/test_attack_path_strip_check.py`:

```python
# tests/unit/synthesis/test_attack_path_strip_check.py
from __future__ import annotations

from apd_gauntlet.synthesis.audit import _attack_path_strip_status


def test_exempt_when_no_risk_apath_findings():
    ok, detail = _attack_path_strip_status(apath_findings=[], data_findings=[])
    assert ok is True and "exempt" in detail


def test_pass_when_risk_apath_has_strip_in_data_js():
    apath = [{"id": "apath-1", "disposition": "risk"}]
    data = [{"id": "apath-1", "attack_path": {"path_id": "path-1", "hops": []}}]
    ok, _ = _attack_path_strip_status(apath_findings=apath, data_findings=data)
    assert ok is True


def test_fail_when_risk_apath_present_but_no_strip_reached_data_js():
    apath = [{"id": "apath-1", "disposition": "risk"}]
    data = [{"id": "apath-1"}]  # no attack_path block
    ok, detail = _attack_path_strip_status(apath_findings=apath, data_findings=data)
    assert ok is False and "0" in detail
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/unit/synthesis/test_attack_path_strip_check.py -v`
Expected: FAIL (`ImportError: cannot import name '_attack_path_strip_status'`).

- [ ] **Step 3: Add the helper**

In `tools/apd_gauntlet/synthesis/audit.py`, add below `_check` (line ~76):

```python
def _attack_path_strip_status(
    *, apath_findings: list[dict], data_findings: list[dict]
) -> tuple[bool, str]:
    """Editorial check: when the run produced any apath risk finding, at least
    one data.js finding should carry the derived `attack_path` strip block."""
    risk = [f for f in apath_findings if f.get("disposition") == "risk"]
    if not risk:
        return True, "exempt: no apath risk findings"
    with_strip = sum(1 for f in data_findings if isinstance(f.get("attack_path"), dict))
    return with_strip > 0, f"apath_risk={len(risk)} data_js_with_strip={with_strip}"
```

- [ ] **Step 4: Call it inside `audit_report`**

In `audit_report`, after the `d3fend_overlay_present` check block (line ~361), add:

```python
    # Completeness check — per-finding attack-path strip (editorial; non-blocking):
    # whenever apath risk findings exist, the derived strip block must reach data.js.
    strip_ok, strip_detail = _attack_path_strip_status(
        apath_findings=apath_f, data_findings=parsed.get("findings", []),
    )
    _check(result, "attack_path_finding_strip_present", strip_ok, strip_detail,
           klass="editorial")
```

- [ ] **Step 5: Run the helper test + the audit-report tests to verify green**

Run: `pytest tests/unit/synthesis/test_attack_path_strip_check.py tests/test_cli_audit_report.py tests/test_report_audit_schema.py -v`
Expected: PASS (editorial check never flips `result.status`, so existing audit tests stay green).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/synthesis/audit.py tests/unit/synthesis/test_attack_path_strip_check.py
git commit -m "feat(audit): editorial attack_path_finding_strip_present check"
```

---

## Task 10: Full test sweep + lint

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite + linters**

Run:
```bash
pytest -q
ruff check tools/ tests/
mypy tools/apd_gauntlet/report/transform.py tools/apd_gauntlet/synthesis/audit.py
python tools/check_report_template_freshness.py && echo FRESH_OK
```
Expected: all green; `FRESH_OK` printed. If `markdownlint` is part of CI, also run it over `docs/` (next task adds docs).

- [ ] **Step 2: Commit (only if any lint autofix changed files)**

```bash
git add -A && git commit -m "chore: lint fixups for attack-path strip" || echo "nothing to commit"
```

---

## Task 11: Docs + ADR + CHANGELOG

**Files:**
- Modify: `docs/attack-path-analysis.md`, `docs/html-report.md`, `CHANGELOG.md`
- Create: `docs/adrs/0015-per-finding-attack-path-strip.md`

- [ ] **Step 1: Add the ADR**

Create `docs/adrs/0015-per-finding-attack-path-strip.md`:

```markdown
# 15. Per-finding attack-path strip in the advisory report

Date: 2026-06-10

## Status

Accepted

## Context

Attack-path (`apath-*`) findings rendered as prose only in the Findings tab; a
reader could not see the path, the vuln position, or where a defense applies.
The path data already existed (asset-graph / attack-paths / defense-graph) and
was drawn on the path-centric Attack Paths tab, but was not attached to the
individual finding.

## Decision

Embed a deterministic "hop-strip" in each `apath-*` **risk** finding's detail
card, derived at report-transform time from the synthesis YAML via the
`id == "apath-" + sha256(path_id)[:8]` join (no `finding.schema.json` change,
no agent/skill/LLM at build or render time). Markers are layered: ⚠ vuln on the
`compromisable_via_finding` edge, 💡 fix on the highest-confidence such edge
(matching the risk recommendation's own wording), and 🛡 D3FEND choke-point on
bottleneck edges that carry a `defense-graph` overlay (degrading to fix-only).
Scope is strictly `disposition == "risk"`; aggregate / per-path-uncertainty /
gap findings keep prose-only rendering. A reverse "view full graph →" link
focuses the Attack Paths tab. The completeness check is editorial (non-blocking).

## Consequences

- No schema change; the linkage is recomputed deterministically and is
  byte-stable (guarded by a test), preserving the audit recompute-drift contract.
- The strip reuses the existing CSS token system (one new `--rec` token) and
  adds no runtime dependency (no Cytoscape for the per-finding view).
- Specialist (`conf-*`/`avail-*`) on-path context and an Attack-Paths-tab
  recommendation overlay are deliberately out of scope (future work).
```

- [ ] **Step 2: Update `docs/attack-path-analysis.md`**

Add a subsection (place it after the section describing the Attack Paths report tab):

```markdown
### Per-finding attack-path strip

Each `apath-*` **risk** finding renders a compact horizontal "hop-strip" in its
Findings-tab detail card: attacker → … → crown jewel, with the **⚠ vulnerable
hop** (the `compromisable_via_finding` edge), a **💡 fix-at-source** marker on
the highest-confidence compromisable edge, and a **🛡 D3FEND choke-point**
marker on any bottleneck edge that carries a `defense-graph` overlay (showing
its `net_new_d3fend` techniques). A **view full graph →** link focuses the
Attack Paths tab on that path. The strip is derived deterministically at
report-build time from `attack-paths.yaml` / `asset-graph.yaml` /
`defense-graph.yaml` — no finding-schema change and no agent in the loop.
```

- [ ] **Step 3: Update `docs/html-report.md`**

In the Findings-tab description, note: "Attack-path risk findings additionally
render a per-finding hop-strip diagram (see attack-path-analysis.md). Editing
the report JSX/CSS requires re-running `python tools/build_report_template.py`
and committing the regenerated `app.js` + `.source-hash`."

- [ ] **Step 4: Add a CHANGELOG entry**

Under the top `## [Unreleased]` (or next version) section in `CHANGELOG.md`:

```markdown
### Added
- Per-finding attack-path "hop-strip" visualization in the Findings tab for
  `apath-*` risk findings — shows the path, the vulnerable hop, and layered
  fix-at-source + D3FEND choke-point recommendation markers, with a reverse
  link to the Attack Paths tab. Derived deterministically from the synthesis
  artifacts (no finding-schema change). ADR-0015.
```

- [ ] **Step 5: Lint docs and commit**

Run: `markdownlint docs/ CHANGELOG.md` (or the repo's CI markdownlint glob) and fix any MD violations introduced.
Run: `git add docs/ CHANGELOG.md && git commit -m "docs: per-finding attack-path strip (ADR-0015 + docs + changelog)"`

---

## Self-review checklist (run before declaring done)

- [ ] **Spec coverage:** path strip (Tasks 4–7), vuln marker (Task 2 `is_vuln`), layered fix + D3FEND markers (Task 2 `is_fix`/`chokepoint`, Task 4 render), strict-risk scope (Task 2 gate), Findings-card placement (Task 5), reverse link (Tasks 4/6), determinism (Task 3), build/freshness (Task 8), editorial audit (Task 9), fixture/coverage (Task 2 in-test factory), docs/ADR (Task 11) — all present.
- [ ] **Determinism:** no `Math.random`/time/set-ordering leaks; D3FEND lists `sorted()`; `findings_array` deep-equal across calls (Task 3).
- [ ] **No schema change:** `finding.schema.json` untouched; `attack_path` is an additive data.js field; `id_coverage_findings` audit unaffected.
- [ ] **Freshness:** every commit touching `report-template/` includes the rebuilt bundle (only Task 8 commits those files).
- [ ] **Naming consistency:** transform emits `attack_path` / `hops` / `is_vuln` / `is_fix` / `chokepoint` / `recommendation_excerpt`; JSX reads the same keys; CSS classes are `.apath-strip__*`; handler is `onOpenPath`; focus prop is `focusPathId`; row id is `ap-row-${path_id}`.
