# tests/test_assemble_c4_l3.py
"""L3 (component) coherence: the ONE contract where the schema, the per-entry
c4_* index tags, and the assembler all agree.

The grounded source for code->component->container parenting is the per-entry
``c4_component`` / ``c4_container`` tag on a code-evidence-index entry; the
c4-recon ``components[]`` list DECLARES the component nodes (parented to their
declared container). A tagged code node parents to the EMITTED component id —
never re-hashed from the entry's own repo — so there is no dangling parent ref
even when the component's declared container differs from the member entry's
repo short-name.

These tests exercise the c4-recon-PRESENT path. The index-only path (the
committed c4-home-assistant fixture has no c4-recon.yaml and no c4_* tags) is
covered by tests/test_assemble_c4.py and must stay byte-identical.
"""
from __future__ import annotations

import json
import pathlib
import shutil

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"
SCHEMA_DIR = REPO / "schemas"

# A core code anchor that the real findings cite (so its container rolls up a
# real finding once tagged into the auth component).
TAGGED_QNAME = "homeassistant.auth.AuthManager.async_create_access_token"


def _registry() -> Registry:
    res = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            res.append((s["$id"], Resource.from_contents(s)))
    return Registry().with_resources(res)


def _validate(doc: dict) -> list[str]:
    schema = json.loads((SCHEMA_DIR / "c4-model.schema.json").read_text())
    errors = sorted(
        Draft202012Validator(schema, registry=_registry()).iter_errors(doc),
        key=lambda e: list(e.path),
    )
    return [e.message for e in errors]


def _copy_run(tmp_path: pathlib.Path) -> pathlib.Path:
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
    (dst / ".apd-run.yaml").write_text(
        "subject: Home Assistant\nrun_id: apd-test-c4-l3\n", encoding="utf-8"
    )
    return dst


def _write_recon(dst: pathlib.Path, components: list[dict]) -> None:
    """Drop a minimal, schema-valid c4-recon.yaml whose containers reuse the
    index repo SHORT-NAMES (so component.container references resolve against a
    minted container id)."""
    recon = {
        "schema_version": 1,
        "generated_by": "code_recon",
        "containers": [
            {
                "name": "core",
                "kind": "service",
                "repo": "Users-shoveleejoe-Documents-GitHub-home-assistant-repos-core",
                "provenance": {"source": "artifact", "locator": "brief.md#core"},
                "analysis_state": "analyzed",
            },
        ],
        "components": components,
        "uses_edges": [],
    }
    (dst / "00-context" / "c4-recon.yaml").write_text(
        yaml.safe_dump(recon, sort_keys=False), encoding="utf-8"
    )


def _tag_entry(dst: pathlib.Path, qname: str, *, c4_component: str) -> None:
    """Rewrite the tmp copy's code-evidence-index, adding a c4_component tag to
    the single entry with the given qualified_name."""
    path = dst / "00-context" / "code-evidence-index.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    inner = raw["code_evidence_index"]
    tagged = False
    for e in inner["entries"]:
        if e.get("qualified_name") == qname:
            e["c4_component"] = c4_component
            tagged = True
    assert tagged, f"no entry matched {qname}"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def test_l3_end_to_end_component_present_and_tagged(tmp_path):
    """c4-recon-present (L3): a declared component + a tagged code entry yields a
    component node parented to its container, the tagged code node parented to
    the EMITTED component id (no dangling), component_count>=1, a code->component
    ->container badge rollup, and a schema-valid document."""
    from apd_gauntlet.assemble_c4 import assemble_c4, c4_node_id

    dst = _copy_run(tmp_path)
    _write_recon(dst, [{
        "name": "auth",
        "container": "core",
        "provenance": {"source": "artifact", "locator": "brief.md#auth"},
    }])
    _tag_entry(dst, TAGGED_QNAME, c4_component="auth")

    summary = assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())
    by_id = {n["id"]: n for n in doc["nodes"]}
    id_set = set(by_id)

    # (a) a component node "auth" exists, parented to the "core" container.
    comp = next(
        (n for n in doc["nodes"] if n["level"] == "component" and n["name"] == "auth"),
        None,
    )
    assert comp is not None
    container_core_id = c4_node_id("container", "core", "")
    assert comp["parent"] == container_core_id
    assert container_core_id in id_set  # the parent container is emitted
    assert comp["id"] == c4_node_id("component", "auth", "core")

    # (b) the tagged code node parents to the EMITTED component id (no dangling).
    code = next(n for n in doc["nodes"] if n["level"] == "code" and n["name"] == TAGGED_QNAME)
    assert code["parent"] == comp["id"]
    assert code["parent"] in id_set  # the parent id is a real emitted node id

    # (c) build_summary records the component.
    assert summary["component_count"] >= 1

    # (d) badges roll code -> component -> container: the container's finding
    # count includes the tagged code node's finding(s).
    assert code["finding_count"] >= 1
    assert comp["finding_count"] >= code["finding_count"]
    assert by_id[container_core_id]["finding_count"] >= code["finding_count"]

    # (e) the document validates against the schema.
    assert _validate(doc) == []


def test_l3_member_repo_differs_from_declared_container(tmp_path):
    """Fix #1: a component DECLARED under container "core" whose tagged member
    entry lives in a DIFFERENT repo (supervisor) still parents the code node to
    the EMITTED component id — never re-hashed from the entry repo, so no
    dangling ref."""
    from apd_gauntlet.assemble_c4 import assemble_c4, c4_node_id

    dst = _copy_run(tmp_path)
    _write_recon(dst, [{
        "name": "x",
        "container": "core",
        "provenance": {"source": "artifact", "locator": "brief.md#x"},
    }])
    # Tag a SUPERVISOR entry into the core-declared component.
    sup_qname = None
    raw = yaml.safe_load((dst / "00-context" / "code-evidence-index.yaml").read_text())
    for e in raw["code_evidence_index"]["entries"]:
        if (
            e.get("kind") in ("function", "class", "route", "module")
            and "repos-supervisor" in str(e.get("repo", ""))
        ):
            sup_qname = e["qualified_name"]
            break
    assert sup_qname is not None
    _tag_entry(dst, sup_qname, c4_component="x")

    assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())
    id_set = {n["id"] for n in doc["nodes"]}

    comp_x_id = c4_node_id("component", "x", "core")
    assert comp_x_id in id_set  # the component is emitted under its declared container
    code = next(n for n in doc["nodes"] if n["level"] == "code" and n["name"] == sup_qname)
    # The code node parents to the EMITTED component id (declared-container based),
    # NOT a re-hash from its own supervisor repo.
    assert code["parent"] == comp_x_id
    assert code["parent"] in id_set  # no dangling parent ref
    assert _validate(doc) == []


def test_de_dup_no_duplicate_ids(tmp_path):
    """De-dup: two code entries with identical qualified_name+repo, and two
    identities with the same name, must NOT emit duplicate node ids or inflate
    counts."""
    from apd_gauntlet.assemble_c4 import assemble_c4

    dst = _copy_run(tmp_path)

    # Duplicate a code entry (same qualified_name + repo) in the index.
    raw = yaml.safe_load((dst / "00-context" / "code-evidence-index.yaml").read_text())
    inner = raw["code_evidence_index"]
    dup_src = next(
        e for e in inner["entries"]
        if e.get("kind") in ("function", "class", "route", "module") and e.get("repo")
    )
    dup = dict(dup_src)
    dup["id"] = "cev-deadbe01"  # distinct evidence id, SAME qualified_name + repo
    inner["entries"].append(dup)
    (dst / "00-context" / "code-evidence-index.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False), encoding="utf-8"
    )

    # Duplicate an identity (same name) in the inventory.
    inv = yaml.safe_load((dst / "00-context" / "asset-inventory.yaml").read_text())
    person = next(
        i for i in (inv.get("identities") or [])
        if i.get("identity_type") in ("human_role", "external_party")
    )
    dup_person = dict(person)
    inv["identities"].append(dup_person)  # same name, second occurrence
    (dst / "00-context" / "asset-inventory.yaml").write_text(
        yaml.safe_dump(inv, sort_keys=False), encoding="utf-8"
    )

    assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())

    ids = [n["id"] for n in doc["nodes"]]
    assert len(ids) == len(set(ids)), "duplicate node ids leaked"
    # counts are not inflated by the duplicate code entry / identity.
    assert doc["build_summary"]["code_count"] == 40
    assert doc["build_summary"]["person_count"] == 8
    assert _validate(doc) == []


def test_first_finding_id_recorded(tmp_path):
    """first_finding_id: a node whose finding_count > 0 carries
    provenance.first_finding_id equal to a real (sorted-first) finding id."""
    from apd_gauntlet.assemble_c4 import assemble_c4

    dst = _copy_run(tmp_path)
    assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())

    # the universe of real finding ids
    findings = yaml.safe_load(
        (dst / "40-synthesis" / "deduped-findings.yaml").read_text()
    )["finding"]
    real_ids = {f["id"] for f in findings}

    hit = [n for n in doc["nodes"] if n["finding_count"] > 0]
    assert hit, "expected at least one node with findings"
    for n in hit:
        ffid = n["provenance"].get("first_finding_id")
        assert ffid, f"node with findings missing first_finding_id: {n['name']}"
        assert ffid in real_ids, f"first_finding_id {ffid} is not a real finding id"

    # nodes with zero findings carry NO first_finding_id.
    for n in doc["nodes"]:
        if n["finding_count"] == 0:
            assert "first_finding_id" not in n["provenance"]

    assert _validate(doc) == []


# --- repo reconciliation (display-named c4-recon process container) -----------

# The real repo string for HA core in the committed index (its short-name "core").
CORE_REPO = "Users-shoveleejoe-Documents-GitHub-home-assistant-repos-core"


def _write_recon_containers(dst: pathlib.Path, containers: list[dict]) -> None:
    """Drop a schema-valid c4-recon.yaml with the given containers[] (and no
    components / uses_edges) so reconciliation behaviour can be exercised."""
    recon = {
        "schema_version": 1,
        "generated_by": "code_recon",
        "containers": containers,
        "components": [],
        "uses_edges": [],
    }
    (dst / "00-context" / "c4-recon.yaml").write_text(
        yaml.safe_dump(recon, sort_keys=False), encoding="utf-8"
    )


def _core_qname(dst: pathlib.Path) -> str:
    """A code entry whose repo short-name is ``core`` in the tmp index copy."""
    raw = yaml.safe_load(
        (dst / "00-context" / "code-evidence-index.yaml").read_text()
    )
    for e in raw["code_evidence_index"]["entries"]:
        if (
            e.get("kind") in ("function", "class", "route", "module")
            and str(e.get("repo", "")).endswith("repos-core")
        ):
            return str(e["qualified_name"])
    raise AssertionError("no core code entry found in index")


def test_process_container_reconciles_repo_no_duplicate(tmp_path):
    """A c4-recon PROCESS container {name:'Home Assistant Core', kind:'service',
    repo:...repos-core} claims the core repo: code entries for that repo parent to
    the DISPLAY-named container (with its kind) and NO duplicate 'core' container
    is minted."""
    from apd_gauntlet.assemble_c4 import assemble_c4, c4_node_id

    dst = _copy_run(tmp_path)
    _write_recon_containers(dst, [{
        "name": "Home Assistant Core",
        "kind": "service",
        "repo": CORE_REPO,
        "provenance": {"source": "artifact", "locator": "brief.md#core"},
        "analysis_state": "analyzed",
    }])
    qname = _core_qname(dst)

    assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())
    nodes = doc["nodes"]
    by_id = {n["id"]: n for n in nodes}

    containers = [n for n in nodes if n["level"] == "container"]
    # (a) exactly ONE container named "Home Assistant Core", and NO "core".
    named = [n for n in containers if n["name"] == "Home Assistant Core"]
    assert len(named) == 1
    assert not any(n["name"] == "core" for n in containers)
    display = named[0]
    assert display["id"] == c4_node_id("container", "Home Assistant Core", "")
    # (c) the display container carries the agent's kind.
    assert display["kind"] == "service"

    # (b) the core code node parents to the display-named container's id.
    code = next(n for n in nodes if n["level"] == "code" and n["name"] == qname)
    assert code["parent"] == display["id"]
    assert code["parent"] in by_id  # emitted, no dangling ref
    # its seed folds in the display NAME (not the repo short-name "core").
    assert code["id"] == c4_node_id("code", qname, "Home Assistant Core")

    assert _validate(doc) == []


def test_data_store_container_does_not_claim_repo(tmp_path):
    """A data_store c4-recon container that carries the same repo does NOT claim
    it (repo on a data_store is provenance metadata). A sibling PROCESS container
    claims the core repo, so core code parents to the PROCESS container, NOT the
    .storage data_store; both containers exist."""
    from apd_gauntlet.assemble_c4 import assemble_c4, c4_node_id

    dst = _copy_run(tmp_path)
    _write_recon_containers(dst, [
        {
            "name": "Home Assistant Core",
            "kind": "service",
            "repo": CORE_REPO,
            "provenance": {"source": "artifact", "locator": "brief.md#core"},
            "analysis_state": "analyzed",
        },
        {
            "name": ".storage",
            "kind": "data_store",
            "repo": CORE_REPO,
            "provenance": {"source": "artifact", "locator": "brief.md#storage"},
            "analysis_state": "analyzed",
        },
    ])
    qname = _core_qname(dst)

    assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())
    nodes = doc["nodes"]
    names = {n["name"] for n in nodes if n["level"] == "container"}

    # both authored containers exist; no short-name "core" duplicate.
    assert "Home Assistant Core" in names
    assert ".storage" in names
    assert "core" not in names

    process_id = c4_node_id("container", "Home Assistant Core", "")
    store_id = c4_node_id("container", ".storage", "")
    code = next(n for n in nodes if n["level"] == "code" and n["name"] == qname)
    # core code parents to the PROCESS container, never the data_store.
    assert code["parent"] == process_id
    assert code["parent"] != store_id

    assert _validate(doc) == []


def test_byte_identity_when_no_recon_present(tmp_path):
    """Byte-identity invariant: with NO c4-recon.yaml (the committed fixture
    shape), assemble yields the SAME 77 nodes and the exact prior repo-short
    container names (core/supervisor/...). Reconciliation is inert."""
    from apd_gauntlet.assemble_c4 import assemble_c4

    dst = _copy_run(tmp_path)
    assert not (dst / "00-context" / "c4-recon.yaml").exists()

    summary = assemble_c4(dst)
    doc = yaml.safe_load((dst / "40-synthesis" / "c4-model.yaml").read_text())

    assert summary["node_count"] == 77
    assert summary["container_count"] == 23
    assert summary["code_count"] == 40
    assert summary["component_count"] == 0
    assert summary["uses_edge_count"] == 5

    container_names = {
        n["name"] for n in doc["nodes"] if n["level"] == "container"
    }
    # the exact prior repo-short container names are unchanged (no display names).
    for name in ("core", "supervisor", "os-agent", "cli", "iOS",
                 "android", "frontend", "mobile-apps-fcm-push", "addons"):
        assert name in container_names, name
    assert "Home Assistant Core" not in container_names
