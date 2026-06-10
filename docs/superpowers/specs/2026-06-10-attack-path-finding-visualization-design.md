# Per-finding attack-path visualization (hop-strip) — design

- **Date:** 2026-06-10
- **Status:** Approved (brainstorm), pending implementation plan
- **Author:** brainstorming session (grounded in a 6-agent code recon of the attack-path data model + report renderers)
- **Affects:** report transform + HTML report renderer only. **No `finding.schema.json` change. No new agentic/skill/LLM dependency.**

## 1. Problem

Attack-path findings (`apath-*`, emitted by the `apd-attack-path-analyzer`) are rendered in the HTML report's **Findings** tab as prose only — Rubric / Summary / Detail / Evidence / Recommendation / Mappings / Lens
([Findings.jsx:206-342](../../../report-template/screens/Findings.jsx)). A reader of a single attack-path finding cannot *see*:

1. **the attack path** the finding is about,
2. **where on that path the vulnerability/threat sits**, and
3. **where on that path the recommendation(s) apply**.

The path data already exists and is already drawn on the **Attack Paths** tab
([AttackPaths.jsx](../../../report-template/screens/AttackPaths.jsx)) via the shared Cytoscape `GraphView`
([components.jsx:289-405](../../../report-template/components.jsx)), but it is path-centric (grouped by attacker→crown-jewel pair) and is not attached to the individual finding the reader is looking at.

## 2. Goals / non-goals

**Goals**

- Embed a compact, per-finding attack-path **hop-strip** ("subway map") in the finding detail card for attack-path **risk** findings.
- Mark, on that strip: the **⚠ vuln** hop, the **💡 fix-at-source** position, and the **🛡 D3FEND choke-point** position(s) — *layered* (show all that apply; degrade gracefully).
- Add a one-way **reverse link** ("view full graph →") from the finding to the Attack Paths tab focused on that path.
- Keep the whole feature **deterministic** — a pure function of the on-disk synthesis YAML, rendered by static JSX.

**Non-goals (YAGNI)**

- No strip for **specialist** findings (`conf-*`/`avail-*`) that merely lie on a path (different join key; deferred).
- No strip for **aggregate / per-path-uncertainty / gap** apath findings (only `disposition == "risk"`; see §4.1).
- No recommendation overlay added to the **Attack Paths tab** rows (that tab already shows vuln + existing-mitigation; leave it).
- No diagram for findings that do not resolve to exactly one path — they keep their current prose rendering unchanged.
- No `finding.schema.json` change. The linkage is derived at report-build time, not stored on the finding.

## 3. Determinism guarantee (hard requirement)

The feature lives entirely in the **deterministic floor**: `loader → transform → emit` + static JSX. There is **no model, agent, or skill in the loop** at report-build or render time, and **no new prose is synthesized**.

- **Join key is a pure hash.** Every per-path finding's id is `"apath-" + sha256(path_id)[:8]` ([findings.py:312](../../../tools/apd_gauntlet/attack_path/findings.py)). The aggregate finding uses a different, count-based hash input ([findings.py:230](../../../tools/apd_gauntlet/attack_path/findings.py)) and therefore never resolves to a path.
- **Marker content is existing data, surfaced verbatim.** The 💡 marker shows the finding's existing `recommendation` (authored upstream, already in the finding YAML); the 🛡 marker shows `net_new_d3fend` technique ids + `paths_traversing` from the `defense-graph` `bottleneck_overlays[edge_id]` ([findings.py:446-454](../../../tools/apd_gauntlet/attack_path/findings.py)).
- **Ordering is stable.** Hop order follows `path.edges`; any set-derived list (e.g. D3FEND techniques) is `sorted()`, mirroring the existing idiom `cross_refs = sorted({...})` ([findings.py:333](../../../tools/apd_gauntlet/attack_path/findings.py)).
- **Guarded by test.** A test asserts `build_apd_data` produces byte-identical output across two runs over the same fixture (determinism is verified, not assumed). This is the same property the audit recompute-drift check and golden fixtures already rely on.

The only agentic work — producing the `apath-*` findings, `asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml` — is the **existing upstream gauntlet** and is already on disk before the report builds. This feature adds zero new agentic step.

## 4. Architecture

```
synthesis YAML (already on disk)            report build (deterministic Python)        browser (static JSX)
─────────────────────────────────          ──────────────────────────────────        ────────────────────
attack-path.findings.yaml (apath-*)  ─┐
asset-graph.yaml  (nodes/edges)       ├──▶ loader.load_run ──▶ transform.findings_array ──▶ data.findings[i].attack_path ──▶ AttackPathStrip
attack-paths.yaml (paths/edges/bneck) │       (RunArtifacts)        + _attack_path_context()                                 (in FindingDetail)
defense-graph.yaml (overlays)        ─┘                                                                                       + "view full graph →"
                                                                                                                              └▶ onOpenPath(path_id)
                                                                                                                                 → Attack Paths tab
```

### 4.1 Scope filter (which findings get the strip)

A finding gets a strip **iff all three hold**, evaluated in `transform.findings_array`:

1. `finding["id"].startswith("apath-")`, **and**
2. `finding["disposition"] == "risk"`, **and**
3. the id hash-resolves to exactly one path (see §4.2).

Per-path *uncertainty* (low-feasibility / partial-mitigation) findings resolve to a path but are intentionally excluded by the `disposition == "risk"` filter; aggregate (`uncertainty`, count-keyed) and bottleneck (`gap`, edge-keyed) findings never resolve to a path. All excluded findings render exactly as today.

### 4.2 The linkage helper (new) — `_attack_path_context(finding, artifacts) -> dict | None`

New private helper in [transform.py](../../../tools/apd_gauntlet/report/transform.py), called from `findings_array` (which already receives `RunArtifacts`, so `asset_graph` / `attack_paths` / `defense_graph` are in scope — no new parameter).

Algorithm (pure):

1. **Resolve the path.** Build once (memoized per build) `apath_id_to_path = { "apath-" + sha256(p["path_id"])[:8] : p for p in artifacts.attack_paths["paths"] }`. Look up `finding["id"]`. **Fallback:** if the hash map misses, parse a `path-<sha8>` token out of `finding["evidence"][*]["locator"]` and match on `path_id`. If neither resolves → return `None`.
2. **Build ordered hops** by reusing the existing edge-resolution logic. Extract the shared **lookup primitives** — `node_by_id` / `edge_by_id` maps, `_node_name`, and the `edge_type` normalization (`trusts→trust_boundary`, `finding→compromisable_via_finding`, `capability→mitigated_by_capability`) — out of `attack_paths_data` ([transform.py:1335-1377](../../../tools/apd_gauntlet/report/transform.py)) into module-level helpers. **Do not change `attack_paths_data`'s output builder** — it keeps emitting its current `edges_detailed` shape verbatim (byte-identical Attack Paths tab data); only the primitives are shared. The new helper builds its own richer per-hop dict from those primitives: `{ edge_id, from:{id,name,type}, to:{id,name,type}, edge_type, confidence, is_bottleneck, finding_id, ... }`, resolving node `type` via `node_by_id[id]["node_type"]` (the `_graph_node` mapping at [transform.py:1266-1277](../../../tools/apd_gauntlet/report/transform.py)), which `edges_detailed` does not carry today.
3. **Mark vuln hops:** `is_vuln = (edge_type == "compromisable_via_finding")`. Carries the on-path `finding_id` (a specialist finding id like `conf-*`).
4. **Mark the fix hop (💡):** the **single highest-confidence** `compromisable_via_finding` edge on the path. There is no existing confidence-rank helper in `apd_gauntlet.severity`, so define a local deterministic rank `{high:3, medium:2, low:1, "":0}`; tie-break = earliest in `path.edges`. This matches the risk recommendation's own wording — *"adding capability coverage on the highest-confidence edge"* ([findings.py:377](../../../tools/apd_gauntlet/attack_path/findings.py)). The strip surfaces the finding's existing `recommendation.summary` + `posture` verbatim as the marker tooltip. If a path has no compromisable edge (shouldn't happen for a risk finding), no 💡.
5. **Mark choke-point hops (🛡):** for each hop whose `edge_id ∈ path.bottleneck_edges` **and** that has a `defense-graph` overlay `bottleneck_overlays[edge_id]`, attach `chokepoint = { d3fend: sorted(overlay["net_new_d3fend"]), paths_traversing: overlay.get("paths_traversing") }`. None match → no 🛡 (graceful degrade to fix-only).
6. **Return the `attack_path` block** (§4.3).

### 4.3 The `attack_path` block (additive field on the finding's report dict)

```yaml
attack_path:
  path_id: "path-e5d54200"
  attacker:    { id: "atk-internet", name: "Internet" }
  crown_jewel: { id: "jewel-phi",    name: "PHI store" }
  hop_count: 4
  feasibility: "medium"
  hops:                       # ordered exactly as path.edges
    - edge_id: "edge-…"
      from: { id: "atk-internet", name: "Internet",  type: "actor" }
      to:   { id: "svc-api",      name: "API",       type: "service" }
      edge_type: "network_reachable"
      confidence: "medium"
      is_bottleneck: false
      is_vuln: false
      is_fix:  false
      finding_id: null
      chokepoint: null
    - edge_id: "edge-…"
      # … the compromisable hop …
      edge_type: "compromisable_via_finding"
      is_vuln: true
      is_fix:  true            # highest-confidence compromisable edge
      finding_id: "conf-77a7fa91"
      chokepoint: null
    - edge_id: "edge-…"
      # … the bottleneck hop (may differ from the vuln hop) …
      is_bottleneck: true
      chokepoint: { d3fend: ["D3-MFA","D3-NTA"], paths_traversing: 6 }
  recommendation_excerpt: "Reduce path feasibility by adding capability coverage on the highest-confidence edge …"  # verbatim from finding.recommendation.summary
```

This is **additive** — it only adds a key to existing finding entries, so the audit `id_coverage_findings` check (which compares id *sets*) is unaffected ([audit.py:108-117](../../../tools/apd_gauntlet/synthesis/audit.py)).

### 4.4 Renderer — `AttackPathStrip` (new, presentational)

- New component in [components.jsx](../../../report-template/components.jsx), exported on `window` (it is already in the esbuild entry via `components.jsx`, so **no `.build/entry.jsx` change** and no new screen file).
- Props: `{ attackPath, onOpenPath }`. Renders the horizontal rail:
  - left **attacker pill**, ordered **station** nodes, right **💎 crown-jewel pill**;
  - each segment colored by `edge_type` (reuse the `EdgeTypeChip` palette: trust / compromisable / capability);
  - **⚠** badge above the vuln segment; **💡** badge below the fix segment (when `is_vuln && is_fix` on the same hop, merge into one combined badge to avoid stacking); **🛡 + D3FEND chips** on choke-point segments with a "breaks N paths" label;
  - horizontal-scroll on overflow (mirrors the existing `.attack-path__edges` overflow handling);
  - header affordance **"view full graph →"** calling `onOpenPath(attackPath.path_id)`.
- `FindingDetail` ([Findings.jsx](../../../report-template/screens/Findings.jsx)) renders `<AttackPathStrip>` in a bordered **"Attack path"** panel placed **immediately after Summary and before Detail**, only when `finding.attack_path` is present. The existing prose **Recommendation** section is unchanged; its 💡 intent is now also shown positionally on the strip.

### 4.5 Reverse navigation — `onOpenPath`

Today nav is one-way: `onOpenFinding(id)` jumps Attack Paths → Findings ([app.jsx:55-58](../../../report-template/app.jsx)). Add the mirror:

- New handler `onOpenPath(pathId)` in [app.jsx](../../../report-template/app.jsx): set active tab to `attack-paths` and set a `focusPathId` that is passed to `AttackPaths` as its `selectedPathId` (the tab already supports `selectedPathId` / `onSelectPath`).
- Thread `onOpenPath` into `Findings` → `FindingDetail` → `AttackPathStrip`.

### 4.6 Styling

- New `.attack-path-strip__*` rules in [screens.css](../../../report-template/screens.css), reusing existing tokens (`--sev-*`, `--accent`, `--rule`, `--ink`, `--paper`, `--font-mono`).
- Add **one** new token `--rec` (indigo/purple) for the 💡/🛡 markers, so "recommended defense" is visually distinct from **red** (vuln, `--sev-critical/high`) and the existing **green** (capability/`--success`). Define in both light and dark theme blocks.

## 5. Build / bundle / freshness

Editing `.jsx`/`.css` requires regenerating and committing the precompiled bundle (git-tracked; CI freshness gate + unit test enforce it):

1. Edit `components.jsx`, `screens/Findings.jsx`, `app.jsx`, `screens.css`, plus the transform.
2. Run `python tools/build_report_template.py` (shells `node .build/build.mjs`).
3. Commit the regenerated `tools/apd_gauntlet/data/report-template/{app.js,.source-hash,screens.css,styles.css,index.html}`.
4. CI: `tools/check_report_template_freshness.py` ([python-tests.yml:26-27](../../../.github/workflows/python-tests.yml)) + `tests/unit/report/test_tier3_bundle_freshness.py` recompute the sha256 and fail on drift.

No new runtime dependency is added (the strip is plain JSX/CSS; it does **not** instantiate Cytoscape).

## 6. Testing strategy

- **Unit — transform** (`tests/unit/report/test_transform_findings.py`):
  - a `disposition=="risk"` apath finding gets an `attack_path` block with correct ordered hops, the right `is_vuln`/`is_fix` hop, and choke-point hops when a matching overlay exists;
  - per-path *uncertainty*, *aggregate*, *gap*, and non-apath findings get **no** block;
  - helper: hash-match path, locator-fallback path, and miss → `None`;
  - graceful degrade: path with no bottleneck overlay → fix marker only, no 🛡.
- **Unit — determinism:** assert `build_apd_data(load_run(fixture))` is byte-identical across two invocations (guards §3).
- **Static JSX** (new `tests/unit/report/test_findings_jsx.py` or extend the existing pattern from `test_attack_paths_jsx.py`): assert `Findings.jsx` renders `AttackPathStrip` guarded on `attack_path`; assert `components.jsx` defines `AttackPathStrip` with the ⚠/💡/🛡 markers; assert `app.jsx` defines + wires `onOpenPath`.
- **Fixture (end-to-end coverage):** the tracked golden `tests/fixtures/report-html/claim-event-bus-golden-data.js` only has a *no-path* apath finding, so it cannot exercise the populated strip. **Add a small dedicated fixture** — a minimal run dir under `tests/fixtures/` containing one `disposition=="risk"` apath finding plus matching `asset-graph.yaml` / `attack-paths.yaml` / `defense-graph.yaml` (with a bottleneck overlay) — and assert the transform attaches a fully-populated `attack_path` block end-to-end. Leave the existing golden untouched.

## 7. Audit

Add an **editorial (non-blocking)** check `attack_path_finding_strip_present` in [audit.py](../../../tools/apd_gauntlet/synthesis/audit.py), beside `attack_paths_present` / `d3fend_overlay_present`: when ≥1 `disposition=="risk"` apath finding that resolves to a path exists in the YAML, assert ≥1 `data.js` finding carries an `attack_path` block. Editorial `klass` so it surfaces drift without ever blocking the workflow gate (conforms to `report-audit.schema.json` `{name,status,detail,klass}`).

## 8. Docs

- Update [docs/attack-path-analysis.md](../../../docs/attack-path-analysis.md) (describe the per-finding strip + marker semantics) and [docs/html-report.md](../../../docs/html-report.md) (Findings tab now shows a path strip; rebuild requirement).
- `CHANGELOG.md` entry.
- New **ADR-0015** `docs/adrs/0015-per-finding-attack-path-strip.md` (latest committed ADR is 0014, OWASP MAS): records the layered-marker decision, the strict-`risk` scope, and the "derive-at-transform, no schema change" choice.

## 9. Edge cases & graceful degradation

| Case | Behavior |
|---|---|
| apath finding doesn't resolve to a path (aggregate/gap) | No strip; prose rendering unchanged. |
| `disposition != "risk"` (per-path uncertainty) | No strip (by §4.1 filter). |
| Path has no bottleneck overlay | 💡 fix marker only; no 🛡. |
| vuln hop == fix hop (same edge) | Merge ⚠ + 💡 into one combined badge. |
| Multiple compromisable edges on one path | All are `is_vuln`; only the highest-confidence one is `is_fix`. |
| Missing/renamed node in asset-graph | `_node_name` falls back to the node id (existing behavior). |
| Path edges reference a missing edge id | Hop rendered with empty names (existing `edge_by_id.get(eid, {})` behavior); no crash. |

## 10. Open items to verify during implementation

1. Confirm `RunArtifacts` exposes `attack_paths["paths"]`, `asset_graph`, and `defense_graph["bottleneck_overlays"]` shapes exactly as assumed (recon-confirmed, re-verify against a freshly built `runs/*/40-synthesis/`).
2. Confirmed: no confidence-rank helper exists in `apd_gauntlet.severity` — define a local deterministic `{high:3,medium:2,low:1,"":0}` rank.
3. Confirm the `attacker`/`crown_jewel` node ids on a path map to nodes with `name` (they do via `_node_name`).
4. Decide final marker glyphs/labels with the existing chip styling so the strip reads cleanly at card width.

## 11. File-touch inventory

| File | Change |
|---|---|
| `tools/apd_gauntlet/report/transform.py` | New `_attack_path_context` helper; refactor `_edges_detailed`/`_node_name` to module scope; call from `findings_array`. |
| `report-template/components.jsx` | New `AttackPathStrip` component (window-exported). |
| `report-template/screens/Findings.jsx` | Render `AttackPathStrip` in FindingDetail; thread `onOpenPath`. |
| `report-template/app.jsx` | New `onOpenPath` handler + `focusPathId`; pass to Findings + AttackPaths. |
| `report-template/screens.css` | `.attack-path-strip__*` rules + `--rec` token (light+dark). |
| `tools/apd_gauntlet/data/report-template/{app.js,.source-hash,…}` | Regenerated bundle (committed). |
| `tools/apd_gauntlet/synthesis/audit.py` | New editorial check `attack_path_finding_strip_present`. |
| `tests/unit/report/test_transform_findings.py` | Transform + determinism unit tests. |
| `tests/unit/report/test_findings_jsx.py` (new) | Static-JSX substring tests. |
| `tests/fixtures/…` (new) | Minimal risk-apath fixture for end-to-end coverage. |
| `docs/attack-path-analysis.md`, `docs/html-report.md`, `CHANGELOG.md`, `docs/adrs/0015-per-finding-attack-path-strip.md` | Docs + ADR. |
