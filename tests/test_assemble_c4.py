# tests/test_assemble_c4.py
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"
SCHEMA_DIR = REPO / "schemas"


def _sha8(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def _load_real_index():
    raw = yaml.safe_load(
        (REAL_RUN / "00-context" / "code-evidence-index.yaml").read_text(encoding="utf-8")
    )
    return raw["code_evidence_index"]


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


def _container_ids_for_real_index(cei):
    """Minted container ids for every code-bearing repo in the real index, so
    build_code_nodes can resolve repo-only parents to an EMITTED id."""
    from apd_gauntlet.assemble_c4 import c4_node_id

    names = {
        e["repo"].split("-repos-")[-1]
        for e in cei["entries"]
        if e.get("kind") in ("function", "class", "route", "module") and e.get("repo")
    }
    return {name: c4_node_id("container", name, "") for name in names}


def test_code_nodes_from_real_index_counts_and_shape():
    from apd_gauntlet.assemble_c4 import build_code_nodes, c4_node_id

    cei = _load_real_index()
    # c4_component / c4_container tags are absent in this run -> every code node
    # parents to its container (the repo short-name) via the minted container id.
    nodes = build_code_nodes(cei, container_id_by_name=_container_ids_for_real_index(cei))
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


def test_container_nodes_mark_not_analyzed_for_empty_repos():
    from apd_gauntlet.assemble_c4 import build_container_nodes, c4_node_id

    cei = _load_real_index()
    # No c4-recon containers supplied -> derive purely from the index repos[].
    nodes, _repo_map = build_container_nodes(c4_recon=None, cei=cei)
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


def test_uses_edges_from_real_index_edge_entries():
    from apd_gauntlet.assemble_c4 import build_uses_edges, c4_edge_id, c4_node_id

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


def test_components_blocked_when_recon_empty():
    from apd_gauntlet.assemble_c4 import build_component_nodes

    # The real run has no c4-recon -> no components -> L3 BLOCKED. The builder now
    # returns (nodes, component_id_by_name); both are empty when L3 is blocked.
    assert build_component_nodes(c4_recon=None, container_id_by_name={}) == ([], {})
    assert build_component_nodes(c4_recon={"components": []}, container_id_by_name={}) == ([], {})


def test_components_built_when_recon_groups_symbols():
    from apd_gauntlet.assemble_c4 import (
        build_code_nodes,
        build_component_nodes,
        c4_node_id,
    )

    # Synthetic c4-recon that DECLARES an "auth" component parented to core.
    recon = {
        "components": [
            {"name": "auth", "container": "core",
             "provenance": {"source": "artifact", "locator": "arch.md#auth"}},
        ],
    }
    container_ids = {"core": c4_node_id("container", "core", "")}
    comps, component_id_by_name = build_component_nodes(
        c4_recon=recon, container_id_by_name=container_ids
    )
    assert len(comps) == 1
    comp = comps[0]
    assert comp["level"] == "component"
    assert comp["name"] == "auth"
    assert comp["parent"] == container_ids["core"]
    assert comp["id"] == c4_node_id("component", "auth", "core")
    # the builder exposes name -> minted component id so code nodes parent to the
    # EMITTED id (never re-hashed from a member entry repo).
    assert component_id_by_name == {"auth": c4_node_id("component", "auth", "core")}

    # A code-evidence entry tagged c4_component:"auth" now parents to the EMITTED
    # component id (precedence #1), not the container.
    cei = _load_real_index()
    tagged = []
    for e in cei["entries"]:
        e = dict(e)
        if e.get("qualified_name") == "homeassistant.auth.AuthManager.async_create_access_token":
            e["c4_component"] = "auth"
        tagged.append(e)
    cei_tagged = {**cei, "entries": tagged}
    code = build_code_nodes(
        cei_tagged,
        container_id_by_name=container_ids,
        component_id_by_name=component_id_by_name,
    )
    token = next(
        n for n in code
        if n["name"] == "homeassistant.auth.AuthManager.async_create_access_token"
    )
    assert token["parent"] == c4_node_id("component", "auth", "core")
    # and the parent is a real emitted component id (no dangling ref)
    assert token["parent"] == comp["id"]


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

    containers, _repo_map = build_container_nodes(c4_recon=None, cei=cei)
    container_ids = {n["name"]: n["id"] for n in containers}
    code = build_code_nodes(cei, container_id_by_name=container_ids)
    all_nodes = containers + code

    summary = apply_badges(all_nodes, cei=cei, findings=findings, capabilities=caps)
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


def test_host_infra_endpoints_do_not_become_false_container_edges(tmp_path):
    # cev-0a000003 qualified_name = "supervisor.docker.manager.DockerAPI ->
    # /run/docker.sock (host dockerd)". The 'to' half names HOST infrastructure
    # (the host Docker daemon's unix socket), NOT the 'docker' repo container.
    # A bare substring matcher resolves "docker.sock"/"dockerd" to the docker
    # repo and emits a FALSE supervisor->docker uses edge. Never-invent says drop
    # an endpoint we cannot ground rather than emit a wrong one, so the whole
    # cev-0a000003 edge must be DROPPED and the 5 legitimate cross-repo edges
    # must be exactly preserved.
    from apd_gauntlet.assemble_c4 import assemble_c4

    run = _copy_real_run(tmp_path)
    build_summary = assemble_c4(run)
    doc = yaml.safe_load(
        (run / "40-synthesis" / "c4-model.yaml").read_text(encoding="utf-8")
    )

    name_by_id = {n["id"]: n["name"] for n in doc["nodes"]}
    edge_name_pairs = {
        (name_by_id.get(e["from"]), name_by_id.get(e["to"])) for e in doc["edges"]
    }

    # no false supervisor->docker edge
    assert ("supervisor", "docker") not in edge_name_pairs
    # the docker-socket edge is dropped entirely (no edge keeps its provenance)
    assert all(
        not str(e["provenance"].get("locator", "")).startswith("cev-0a000003")
        for e in doc["edges"]
    )

    # exactly the 5 legitimate cross-repo edges survive, by from->to name
    assert build_summary["uses_edge_count"] == 5
    assert edge_name_pairs == {
        ("cli", "supervisor"),
        ("supervisor", "core"),
        ("supervisor", "os-agent"),
        ("frontend", "core"),
        ("core", "mobile-apps-fcm-push"),
    }


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
