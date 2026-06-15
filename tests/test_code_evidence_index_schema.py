"""Schema tests for the code-evidence-index.yaml artifact."""
from __future__ import annotations

import json
import pathlib

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO / "schemas"
SCHEMA = json.loads((SCHEMA_DIR / "code-evidence-index.schema.json").read_text())
FIXTURES = REPO / "tests" / "fixtures"


def _build_registry() -> Registry:
    # code-evidence-index now $refs _defs.schema.json (apd_relevance); the
    # registry must carry every schema by $id so the cross-file ref resolves.
    resources = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(schema_path.read_text())
        sid = schema.get("$id")
        if sid:
            resources.append((sid, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator() -> Draft202012Validator:
    return Draft202012Validator(SCHEMA, registry=_build_registry())


def test_valid_index_passes():
    data = yaml.safe_load((FIXTURES / "valid/code-evidence-index.yaml").read_text())
    errors = list(_validator().iter_errors(data))
    assert errors == []


def test_invalid_index_flags_every_field():
    data = yaml.safe_load((FIXTURES / "invalid/code-evidence-index-malformed.yaml").read_text())
    errors = list(_validator().iter_errors(data))
    messages = " ".join(e.message for e in errors)
    # commit sha format
    assert "not-a-sha" in messages or "indexed_commit_sha" in messages
    # entry id prefix
    assert "wrong-prefix" in messages or "id" in messages
    # kind enum
    assert "not-a-real-kind" in messages or "kind" in messages
    # path traversal
    assert "../escape" in messages or "file_path" in messages
    # apd_relevance enum
    assert "made_up_lens" in messages or "apd_relevance" in messages


def test_excerpt_token_limit_enforced_by_validator_not_schema():
    """The 25-word excerpt limit lives in semantic linters, not the schema.
    The schema only requires non-empty excerpt strings."""
    data = {
        "code_evidence_index": {
            "indexed_commit_sha": "a" * 40,
            "cbm_project": "x",
            "generated_at": "2026-06-01T12:00:00Z",
            "entries": [
                {
                    "id": "cev-deadbeef",
                    "qualified_name": "x.y",
                    "kind": "function",
                    "file_path": "a.py",
                    "line_range": "L1",
                    "excerpt": "word " * 50,
                    "apd_relevance": ["confidentiality"],
                }
            ],
        }
    }
    errors = list(_validator().iter_errors(data))
    assert errors == []  # token-count check is done by linters.py later


def test_multirepo_index_with_per_entry_repo_passes():
    """Top-level repos[] provenance + per-entry repo validates."""
    data = yaml.safe_load(
        (FIXTURES / "valid/code-evidence-index-multirepo.yaml").read_text()
    )
    errors = list(_validator().iter_errors(data))
    assert errors == []
    idx = data["code_evidence_index"]
    assert len(idx["repos"]) == 2
    assert idx["entries"][0]["repo"] == "payments-api"


def test_multirepo_provenance_requires_per_entry_repo():
    """When top-level repos[] is present, every entry must carry repo (if/then)."""
    data = yaml.safe_load(
        (FIXTURES / "invalid/code-evidence-index-multirepo-missing-repo.yaml").read_text()
    )
    errors = list(_validator().iter_errors(data))
    assert errors, "entry without repo under multi-repo provenance must be rejected"
    messages = " ".join(e.message for e in errors)
    assert "repo" in messages


def test_single_repo_index_still_valid_without_repos():
    """Back-compat: the existing single-repo fixture (no repos[], no per-entry repo) stays valid."""
    data = yaml.safe_load((FIXTURES / "valid/code-evidence-index.yaml").read_text())
    errors = list(_validator().iter_errors(data))
    assert errors == []
