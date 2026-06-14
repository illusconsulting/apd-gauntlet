# tests/test_assemble_c4_robustness.py
"""Robustness: the C4 assembler must never emit an empty-name node.

Reproduces the malformed/sparse-input shape carried by
examples/apd-20260601-claim-event-bus (top-level ``repos:`` null/absent AND
entries whose ``repo`` is null/empty). The old derivation treated ``None`` as a
repo and minted a container with ``name: ''`` (and parented the repo-less code
nodes to it), which violates c4-model.schema.json (nodes require minLength-1
``name``). The fix: ignore falsy repos, leave repo-less code nodes top-level
(parent None), and never emit an empty-name node.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO / "schemas"


def _registry() -> Registry:
    res = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        s = json.loads(p.read_text())
        if s.get("$id"):
            res.append((s["$id"], Resource.from_contents(s)))
    return Registry().with_resources(res)


def _make_sparse_run(tmp_path: pathlib.Path) -> pathlib.Path:
    """A minimal run whose code-evidence-index has null repos[] and a single
    entry with ``repo: null`` (the claim-event-bus example shape)."""
    run = tmp_path / "run"
    (run / "00-context").mkdir(parents=True)
    (run / "40-synthesis").mkdir(parents=True)

    (run / ".apd-run.yaml").write_text(
        "subject: Sparse System\nrun_id: apd-test-sparse\n", encoding="utf-8"
    )

    # >= 1 identity so L1 has a person node.
    (run / "00-context" / "asset-inventory.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "generated_by": "intake",
                "identities": [
                    {
                        "name": "operator-role",
                        "identity_type": "human_role",
                        "provenance": {"source": "asset_inventory"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # repos: null (top-level absent) AND entries with NO resolvable repo. Two
    # entries cover both falsy shapes that the old code mis-handled:
    #   * explicit ``repo: null`` (-> str() == "None", the wrong "None" name);
    #   * absent ``repo`` key      (-> str("") == "",  the empty-name violation,
    #     the exact claim-event-bus example shape).
    (run / "00-context" / "code-evidence-index.yaml").write_text(
        yaml.safe_dump(
            {
                "code_evidence_index": {
                    "indexed_commit_sha": "0" * 40,
                    "cbm_project": "sparse",
                    "generated_at": "2026-06-13T00:00:00Z",
                    "repos": None,
                    "entries": [
                        {
                            "id": "cev-deadbeef",
                            "qualified_name": "sparse.mod.func",
                            "kind": "function",
                            "repo": None,
                            "file_path": "src/sparse/mod.py",
                            "line_range": "L1-L9",
                        },
                        {
                            # NO ``repo`` key at all (claim-event-bus shape).
                            "id": "cev-cafef00d",
                            "qualified_name": "sparse.other.helper",
                            "kind": "function",
                            "file_path": "src/sparse/other.py",
                            "line_range": "L3-L7",
                        },
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # presence of asset-graph.yaml GATES the run.
    (run / "40-synthesis" / "asset-graph.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "generated_by": "attack_path_analyzer",
                "nodes": [],
                "edges": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return run


def test_assemble_c4_never_emits_empty_name_node_on_sparse_input(tmp_path):
    from apd_gauntlet.assemble_c4 import assemble_c4

    run = _make_sparse_run(tmp_path)
    assemble_c4(run)
    out = run / "40-synthesis" / "c4-model.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))

    # (a) NO node has an empty / whitespace-only name.
    for n in doc["nodes"]:
        assert n["name"] and str(n["name"]).strip(), f"empty-name node: {n!r}"

    # (b) the repo-less code nodes are present and top-level (parent None) — they
    # are not parented to a (now-skipped) empty container, and stay visible.
    code_nodes = [n for n in doc["nodes"] if n["level"] == "code"]
    assert {n["name"] for n in code_nodes} == {
        "sparse.mod.func",
        "sparse.other.helper",
    }
    for n in code_nodes:
        assert n["parent"] is None, f"repo-less code node not top-level: {n!r}"

    # no empty/None-named container leaked in (no container at all here, since
    # neither entry resolves to a real repo and there is no c4-recon).
    assert all(n["level"] != "container" for n in doc["nodes"])

    # (c) the output VALIDATES against the schema (zero errors).
    schema = json.loads((SCHEMA_DIR / "c4-model.schema.json").read_text())
    errors = list(
        Draft202012Validator(schema, registry=_registry()).iter_errors(doc)
    )
    assert errors == [], [e.message for e in errors[:5]]
