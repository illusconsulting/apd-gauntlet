"""cluster-candidates: emits a schema-valid cluster-candidates.yaml.

Signals are the 3 mechanical ones only (never control-mapping overlap).
"""
from __future__ import annotations

import json
import pathlib
import shutil

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _build_registry() -> Registry:
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _copy_example(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(EXAMPLE, dst)
    return dst


def test_cluster_candidates_emits_schema_valid_doc(tmp_path):
    dst = _copy_example(tmp_path)
    result = CliRunner().invoke(main, ["cluster-candidates", str(dst)])
    assert result.exit_code == 0, result.output
    out = dst / "40-synthesis" / "cluster-candidates.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text())
    schema = json.loads((SCHEMA_DIR / "cluster-candidates.schema.json").read_text())
    validator = Draft202012Validator(schema, registry=_build_registry())
    assert list(validator.iter_errors(doc)) == [], result.output


def test_groups_are_deterministically_ordered_and_signals_valid(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["cluster-candidates", str(dst)])
    doc = yaml.safe_load((dst / "40-synthesis" / "cluster-candidates.yaml").read_text())
    valid_signals = {"evidence_locator_overlap", "title_similarity", "related_concerns"}
    for g in doc["groups"]:
        # members sorted by id
        ids = [m["id"] for m in g["members"]]
        assert ids == sorted(ids)
        # only the 3 mechanical signals (control overlap must NEVER appear)
        assert set(g["signals"]) <= valid_signals
    # group_ids are sorted
    gids = [g["group_id"] for g in doc["groups"]]
    assert gids == sorted(gids)


def test_findings_and_capabilities_cluster_separately(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["cluster-candidates", str(dst)])
    doc = yaml.safe_load((dst / "40-synthesis" / "cluster-candidates.yaml").read_text())
    for g in doc["groups"]:
        kinds = {m["id"].count("-cap-") for m in g["members"]}
        # a group is either all-finding (0 '-cap-') or all-capability (1 '-cap-')
        assert len(kinds) == 1
        assert (g["kind"] == "capability") == (kinds == {1})


def test_no_group_exceeds_cap(tmp_path):
    dst = _copy_example(tmp_path)
    CliRunner().invoke(main, ["cluster-candidates", str(dst), "--max-group-size", "8"])
    doc = yaml.safe_load((dst / "40-synthesis" / "cluster-candidates.yaml").read_text())
    for g in doc["groups"]:
        assert 2 <= len(g["members"]) <= 8


def test_oversized_cluster_splits_within_cap_no_singleton():
    from apd_gauntlet.synthesis.cluster import _group_records

    # 9 findings with identical title => one cluster of 9; with cap 8 the old
    # fold-back produced a group of 9. Even distribution must yield 2 groups, each 2..8.
    records = [
        {
            "id": f"gap-{i:04d}",
            "apd_goal": "confidentiality",
            "agent": "confidentiality",
            "severity": "low",
            "title": "identical token bypass on shared auth path",
            "summary": "x",
            "evidence": [],
            "related_concerns": [],
            "control_mappings": {},
        }
        for i in range(9)
    ]
    groups = _group_records(records, "finding", 8)
    assert groups, "expected at least one group"
    for g in groups:
        assert 2 <= len(g["members"]) <= 8, f"group size out of bounds: {len(g['members'])}"
    # all 9 ids accounted for exactly once
    seen = [m["id"] for g in groups for m in g["members"]]
    assert sorted(seen) == [f"gap-{i:04d}" for i in range(9)]
