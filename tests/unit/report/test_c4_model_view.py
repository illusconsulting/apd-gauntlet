"""Unit tests for transform.c4_model_view — the window.APD_DATA.c4_model shape."""
from __future__ import annotations

import dataclasses
import pathlib

from apd_gauntlet.report.loader import RunArtifacts, load_run
from apd_gauntlet.report.transform import build_apd_data, c4_model_view

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
                    # FX1 records the deterministic first contributing finding id
                    # on nodes whose finding_count > 0 (per assemble_c4 rollup).
                    "first_finding_id": "finding-aaaa1111",
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
                    "first_finding_id": "finding-bbbb2222",
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


def test_c4_model_view_surfaces_node_kind() -> None:
    """EN2: every window node carries the c4-model node's ``kind`` (service /
    data_store / compute / external_system / app / library for containers, or
    function / class / route / module for code) so the C4 scene can render
    C4-style typing. Additive — the existing keys are unchanged."""
    view = c4_model_view(_with_c4(_fixture_c4_model()))
    by_id = {n["id"]: n for n in view["nodes"]}

    # Container-level node carries its kind verbatim from the c4-model node.
    assert by_id["c4-bbbbbbbb"]["kind"] == "service"
    # System node kind passes through too.
    assert by_id["c4-aaaaaaaa"]["kind"] == "service"
    # L4 code node carries its kind (e.g. compute / function / class).
    assert by_id["c4-dddddddd"]["kind"] == "compute"
    # The additive key is present on every node (None when the model omits it).
    for n in view["nodes"]:
        assert "kind" in n


def test_c4_model_view_node_kind_none_when_absent() -> None:
    """When a c4-model node omits ``kind``, the window node carries ``kind: None``
    rather than raising or fabricating a value (never-invent)."""
    model = _fixture_c4_model()
    for n in model["nodes"]:
        n.pop("kind", None)
    view = c4_model_view(_with_c4(model))
    for n in view["nodes"]:
        assert n["kind"] is None


def test_c4_model_view_passes_first_finding_id_for_node_deep_link() -> None:
    """FX1 records provenance.first_finding_id on c4-model nodes whose
    finding_count > 0. The transform MUST pass it through so the C4 scene's
    per-node ⚑ badge can deep-link into the Findings tab. Zero-finding nodes
    carry no first_finding_id (the assembler omits it)."""
    view = c4_model_view(_with_c4(_fixture_c4_model()))
    by_id = {n["id"]: n for n in view["nodes"]}

    # finding_count == 5 -> first_finding_id reaches the rendered node provenance.
    core = by_id["c4-bbbbbbbb"]
    assert core["badge"] == 5
    assert core["provenance"].get("first_finding_id") == "finding-aaaa1111"

    # The L4 code node (finding_count == 2) carries its own first id too.
    code = by_id["c4-dddddddd"]
    assert code["badge"] == 2
    assert code["provenance"].get("first_finding_id") == "finding-bbbb2222"

    # A zero-finding node has no first_finding_id (so the ⚑ badge is not rendered).
    addons = by_id["c4-cccccccc"]
    assert addons["badge"] is None
    assert "first_finding_id" not in addons["provenance"]


def test_asset_to_c4_grounded_code_evidence_link_fires() -> None:
    """NON-VACUOUS positive: an asset node whose provenance DETERMINISTICALLY
    names a code-evidence anchor (source == code_evidence, locator a code:
    pointer resolving to a minted L4 code node) MUST map asset id -> code node
    id. This proves the grounded branch fires — not just the empty/disjoint
    home-assistant case. The never-invent guard (no name-substring matching)
    stays in force and is exercised by the negative asset below."""
    model = _fixture_c4_model()
    # The minted L4 code node's name IS its qualified_name (assemble_c4 contract).
    qname = "homeassistant.auth.AuthManager.async_create_access_token"
    asset_graph = {
        "schema_version": 1,
        "nodes": [
            {
                # GROUNDED: code_evidence provenance with a code: locator whose
                # qualified_name matches the minted L4 node -> link MUST fire.
                "node_id": "asset-grounded-1",
                "name": "token minter",  # deliberately NOT a container name
                "provenance": {"source": "code_evidence", "locator": f"code:{qname}"},
            },
            {
                # NEGATIVE: name equals a container label ("core") but provenance
                # is doc-sourced -> the never-invent guard must REJECT it (no
                # name-substring fallback), so it is absent from asset_to_c4.
                "node_id": "asset-docname-2",
                "name": "core",
                "provenance": {"source": "artifact", "locator": "assets[3]"},
            },
        ],
        "edges": [],
    }
    base = _with_c4(model)
    artifacts = dataclasses.replace(base, asset_graph=asset_graph)
    view = c4_model_view(artifacts)

    asset_to_c4 = view["asset_to_c4"]
    # The grounded asset resolves to the SAME rendered id as the L4 code node.
    code_node_id = next(n["id"] for n in view["nodes"] if n["type"] == "code")
    assert asset_to_c4 == {"asset-grounded-1": code_node_id}, asset_to_c4
    # Never-invent guard: the name-collision doc asset is NOT mapped.
    assert "asset-docname-2" not in asset_to_c4


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
