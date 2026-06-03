"""Pure-function + CLI tests for the deterministic author-threat-model skeleton builder."""
from __future__ import annotations

from pathlib import Path

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.threat_model.author import (
    APPLICABLE_STRIDE,
    build_skeleton,
)
from apd_gauntlet.threat_model.mappings import stride_letter_to_apd_goals
from click.testing import CliRunner

FIXTURE = Path(__file__).parent / "fixtures" / "threat_model" / "author-inventory.yaml"


def _inventory() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def test_applicable_stride_matrix_per_element_type() -> None:
    # External entity (identity): Spoofing + Repudiation only.
    assert APPLICABLE_STRIDE["external_entity"] == ("S", "R")
    # Process (service/api/gateway): full STRIDE.
    assert APPLICABLE_STRIDE["process"] == ("S", "T", "R", "I", "D", "E")
    # Data store (data_store/database/queue/topic): T, R, I, D.
    assert APPLICABLE_STRIDE["data_store"] == ("T", "R", "I", "D")
    # Reconstructed data flow (agent's step, but the cell-set is fixed here): T, I, D.
    assert APPLICABLE_STRIDE["data_flow"] == ("T", "I", "D")


def test_skeleton_emits_one_entry_per_applicable_stride_cell() -> None:
    inv = _inventory()
    env = build_skeleton(inv, source_artifact="00-context/asset-inventory.yaml")

    by_asset: dict[str, list[str]] = {}
    for e in env["entries"]:
        by_asset.setdefault(e["asset"], []).append(e["framework_refs"]["stride_letter"])

    # identity (external entity) -> S, R
    assert by_asset["claims-adjudicator"] == ["S", "R"]
    # service (process) -> full STRIDE
    assert by_asset["claim-ingress-api"] == ["S", "T", "R", "I", "D", "E"]
    # data_store -> T, R, I, D
    assert by_asset["member-record-store"] == ["T", "R", "I", "D"]
    # total = 2 + 6 + 4
    assert len(env["entries"]) == 12


def test_skeleton_entries_are_low_confidence_grounded_stubs() -> None:
    env = build_skeleton(_inventory(), source_artifact="00-context/asset-inventory.yaml")
    api_s = next(
        e for e in env["entries"]
        if e["asset"] == "claim-ingress-api" and e["framework_refs"]["stride_letter"] == "S"
    )
    assert api_s["threat"] == "(S on claim-ingress-api: to be grounded)"
    assert api_s["extraction_confidence"] == "low"
    assert api_s["mitigation"] is None
    assert api_s["prerequisite_evidence"] == []
    # source_locator comes from the inventory record's provenance locator.
    assert api_s["source_locator"] == "§4 Event Bus Architecture"
    # inferred_apd_goals are inverse-mapped from the canonical table (single source).
    assert api_s["inferred_apd_goals"] == stride_letter_to_apd_goals("S")
    assert api_s["inferred_apd_goals"] == ["authenticity"]


def test_envelope_summary_counts_all_low() -> None:
    env = build_skeleton(_inventory(), source_artifact="00-context/asset-inventory.yaml")
    assert env["generated_by"] == "threat_model_author"
    assert env["methodology"] == "stride"
    assert env["extraction_summary"] == {
        "entry_count": 12,
        "high_confidence_count": 0,
        "medium_confidence_count": 0,
        "low_confidence_count": 12,
        "parser_used": "author-threat-model (deterministic skeleton)",
    }


def test_never_invents_a_surface_absent_from_inventory() -> None:
    env = build_skeleton(_inventory(), source_artifact="00-context/asset-inventory.yaml")
    surfaces = {e["asset"] for e in env["entries"]}
    # Exactly the three inventory surfaces — nothing manufactured.
    assert surfaces == {"claim-ingress-api", "member-record-store", "claims-adjudicator"}
    # A plausible-but-absent surface never leaks in.
    assert "audit-log-store" not in surfaces


def test_unknown_asset_type_produces_no_cells() -> None:
    inv = {
        "schema_version": 1,
        "generated_by": "intake",
        "assets": [
            {
                "asset_id": "asset-deadbeef",
                "name": "mystery-thing",
                "asset_type": "not_a_real_type",
                "provenance": {"source": "artifact", "locator": "x"},
                "confidence": "low",
            }
        ],
        "identities": [],
        "trust_boundaries": [],
    }
    env = build_skeleton(inv, source_artifact="00-context/asset-inventory.yaml")
    assert env["entries"] == []
    assert "mystery-thing" not in {e["asset"] for e in env["entries"]}


def test_build_skeleton_is_idempotent_and_deterministic() -> None:
    inv = _inventory()
    first = build_skeleton(inv, source_artifact="00-context/asset-inventory.yaml")
    second = build_skeleton(inv, source_artifact="00-context/asset-inventory.yaml")
    assert first == second
    # entry_ids are a pure function of (asset, threat, source_locator).
    ids = [e["entry_id"] for e in first["entries"]]
    assert ids == [e["entry_id"] for e in second["entries"]]
    assert len(ids) == len(set(ids))  # no collisions across this inventory


def test_entry_id_recomputes_from_components() -> None:
    from apd_gauntlet.threat_model.author import entry_id_for

    env = build_skeleton(_inventory(), source_artifact="00-context/asset-inventory.yaml")
    e = env["entries"][0]
    assert e["entry_id"] == entry_id_for(e["asset"], e["threat"], e["source_locator"])
    assert e["entry_id"].startswith("tm-") and len(e["entry_id"]) == 11


def _write_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    ctx = run / "00-context"
    ctx.mkdir(parents=True)
    (ctx / "asset-inventory.yaml").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return run


def test_cli_author_threat_model_exit_zero_writes_skeleton(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    result = CliRunner().invoke(main, ["author-threat-model", str(run)])
    assert result.exit_code == 0, result.output
    out = run / "00-context" / "threat-model-skeleton.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["generated_by"] == "threat_model_author"
    assert len(doc["entries"]) == 12
    assert "wrote 12 skeleton entries" in result.output


def test_cli_author_threat_model_is_idempotent_on_disk(tmp_path: Path) -> None:
    run = _write_run(tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["author-threat-model", str(run)]).exit_code == 0
    out = run / "00-context" / "threat-model-skeleton.yaml"
    first = out.read_text(encoding="utf-8")
    assert runner.invoke(main, ["author-threat-model", str(run)]).exit_code == 0
    assert out.read_text(encoding="utf-8") == first


def test_cli_author_threat_model_missing_inventory_errors(tmp_path: Path) -> None:
    run = tmp_path / "run"
    (run / "00-context").mkdir(parents=True)
    result = CliRunner().invoke(main, ["author-threat-model", str(run)])
    assert result.exit_code == 1
    assert "asset-inventory.yaml" in result.output


def test_skeleton_validates_against_normalized_schema() -> None:
    import json as _json

    from apd_gauntlet.validate import build_registry
    from jsonschema import Draft202012Validator

    repo_root = Path(__file__).resolve().parent.parent
    schema_path = repo_root / "schemas" / "threat-model-normalized.schema.json"
    schema = _json.loads(schema_path.read_text(encoding="utf-8"))
    # Pre-conditions guaranteed by the Task 1 schema-widen.
    assert "threat_model_author" in schema["properties"]["generated_by"]["enum"]
    entry_props = schema["properties"]["entries"]["items"]["properties"]
    assert entry_props["prerequisite_evidence"]["type"] == "array"
    assert entry_props["prerequisite_evidence"]["items"] == {"type": "string"}

    env = build_skeleton(_inventory(), source_artifact="00-context/asset-inventory.yaml")
    validator = Draft202012Validator(schema, registry=build_registry())
    errors = sorted(validator.iter_errors(env), key=lambda e: list(e.absolute_path))
    assert errors == [], [f"{e.message} at {list(e.absolute_path)}" for e in errors]
