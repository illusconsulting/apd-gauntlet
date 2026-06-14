"""Unit tests for the attack-path overlay crosswalk producers in c4_model_view.

The overlay scene (report-template/screens/C4.jsx) CONSUMES two crosswalk maps
the transform must emit on ``data.c4_model``:

  * ``finding_to_c4`` — {finding_id -> c4 CODE-node id}, derived from each
    deduped finding's FIRST ``code:<qualified_name>`` evidence locator joined to
    the L4 code node the assembler minted for that qualified_name. This is the
    same code-locator join the C4 finding badges already use.
  * ``asset_to_c4`` — {asset-graph node_id -> c4 node id}, GROUNDED-ONLY. Only a
    deterministic, artifact-grounded link (asset provenance names a code node /
    repo container) may create an entry. NEVER name-substring matching. On the
    home-assistant fixture the asset nodes carry no repo/cev field, so this map
    is honestly empty — the disjoint-id-space limitation.

These tests assemble c4-model.yaml fresh from the committed home-assistant
fixture (mirroring test_c4_model_real_run.py) so the join runs against real
findings + a real code-evidence index.
"""
from __future__ import annotations

import pathlib
import shutil

import pytest
from apd_gauntlet.report.loader import load_run
from apd_gauntlet.report.transform import c4_model_view
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parents[3]
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"

pytestmark = pytest.mark.skipif(
    not REAL_RUN.is_dir(), reason="real home-assistant run not present"
)


def _assemble_c4_available() -> bool:
    try:
        from apd_gauntlet import assemble_c4  # noqa: F401
        from apd_gauntlet.cli import main  # noqa: F401
    except ImportError:
        return False
    from apd_gauntlet.cli import main

    return "assemble-c4" in (main.commands or {})


def _seed_load_run_required(synthesis: pathlib.Path) -> None:
    """Seed the four whole-report rollups ``load_run`` requires but the C4
    fixture omits. None of these stubs feed the ``c4_model`` section under test.
    Mirrors test_c4_model_real_run.py::_seed_load_run_required."""
    seeds = {
        "nist-coverage.yaml": 'schema_version: 1\ngenerated_at: "2026-06-12"\ncoverage: []\n',
        "attack-exposure.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\nexposed_assets: []\n'
        ),
        "apd-coverage-matrix.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\nmatrix: []\n'
        ),
        "metrics.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\n'
            "totals: {findings: 0, capabilities: 0}\n"
        ),
    }
    for name, body in seeds.items():
        target = synthesis / name
        if not target.exists():
            target.write_text(body, encoding="utf-8")


def _main_cli():
    from apd_gauntlet.cli import main

    return main


def _copy_and_assemble(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "run"
    shutil.copytree(REAL_RUN, dst)
    stale = dst / "40-synthesis" / "c4-model.yaml"
    if stale.exists():
        stale.unlink()
    runner = CliRunner()
    result = runner.invoke(_main_cli(), ["assemble-c4", str(dst)])
    assert result.exit_code == 0, result.output
    _seed_load_run_required(dst / "40-synthesis")
    return dst


def test_overlay_crosswalk_keys_present(tmp_path: pathlib.Path) -> None:
    if not _assemble_c4_available():
        pytest.skip("assemble-c4 CLI not present yet")
    run = _copy_and_assemble(tmp_path)
    view = c4_model_view(load_run(run))
    assert view["present"] is True
    assert "finding_to_c4" in view
    assert "asset_to_c4" in view


def test_finding_to_c4_grounded_and_nonempty(tmp_path: pathlib.Path) -> None:
    if not _assemble_c4_available():
        pytest.skip("assemble-c4 CLI not present yet")
    run = _copy_and_assemble(tmp_path)
    artifacts = load_run(run)
    view = c4_model_view(artifacts)

    finding_to_c4 = view["finding_to_c4"]
    assert isinstance(finding_to_c4, dict)
    # The fixture's deduped findings carry code: locators -> non-empty join.
    assert finding_to_c4, "expected at least one code-bearing finding -> code node"

    # Every value is a SINGLE id of an existing level=='code' node.
    code_node_ids = {n["id"] for n in view["nodes"] if n["type"] == "code"}
    assert code_node_ids, "fixture should mint L4 code nodes"
    for fid, cid in finding_to_c4.items():
        assert isinstance(cid, str)
        assert cid in code_node_ids, f"{fid} -> {cid} is not a code node id"

    # Every key is a real deduped finding id.
    real_finding_ids = {str(f.get("id")) for f in artifacts.deduped_findings}
    for fid in finding_to_c4:
        assert fid in real_finding_ids, f"{fid} is not a real finding id"


def test_asset_to_c4_grounded_only_no_name_matching(tmp_path: pathlib.Path) -> None:
    if not _assemble_c4_available():
        pytest.skip("assemble-c4 CLI not present yet")
    run = _copy_and_assemble(tmp_path)
    artifacts = load_run(run)
    view = c4_model_view(artifacts)

    asset_to_c4 = view["asset_to_c4"]
    assert isinstance(asset_to_c4, dict)

    # GROUNDED-ONLY: the home-assistant asset nodes carry no repo/cev field, so
    # the honest outcome is an EMPTY map. If any entry exists it must be a real
    # c4 node id AND must NOT have been minted by name-substring matching.
    c4_node_ids = {n["id"] for n in view["nodes"]}
    asset_nodes = (artifacts.asset_graph or {}).get("nodes") or []
    container_names = {
        n["label"].lower() for n in view["nodes"] if n["type"] == "container"
    }
    asset_name_by_id = {
        str(n.get("node_id")): str(n.get("name") or "") for n in asset_nodes
    }
    for aid, cid in asset_to_c4.items():
        assert cid in c4_node_ids, f"{aid} -> {cid} is not a c4 node id"
        # Never-invent guard: assert the link is NOT a fuzzy name-substring hit.
        aname = asset_name_by_id.get(aid, "").lower()
        substring_hit = any(
            cn and (cn in aname or aname in cn) for cn in container_names
        )
        assert not substring_hit, (
            f"{aid} -> {cid} looks like a name-substring match (forbidden)"
        )
