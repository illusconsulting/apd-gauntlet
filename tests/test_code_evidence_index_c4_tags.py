"""Additive c4_* tags on code-evidence-index entries must (a) validate when
present and (b) NOT break the REAL multi-repo Home Assistant index that omits
them. Backward-compat is the load-bearing assertion: 14/23 repos and 46 entries
already on disk must still pass after the schema change.
"""
from __future__ import annotations

import json
import pathlib

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO / "schemas"
SCHEMA = SCHEMA_DIR / "code-evidence-index.schema.json"
HA_INDEX = (
    REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"
    / "00-context" / "code-evidence-index.yaml"
)


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
    return Draft202012Validator(json.loads(SCHEMA.read_text()), registry=_build_registry())


def _base_entry() -> dict:
    return {
        "id": "cev-abcd1234",
        "qualified_name": "homeassistant.auth.async_validate_login",
        "kind": "function",
        "file_path": "homeassistant/auth/__init__.py",
        "line_range": "L120-L150",
        "excerpt": "async def async_validate_login(self, ...):",
        "apd_relevance": ["authenticity"],
    }


def _doc(entry: dict) -> dict:
    return {
        "code_evidence_index": {
            "indexed_commit_sha": "28076bc",
            "cbm_project": "home-assistant-repos-core",
            "generated_at": "2026-06-12T00:00:00Z",
            "entries": [entry],
        }
    }


def test_entry_with_full_c4_tags_validates():
    e = _base_entry()
    e["c4_container"] = "core"
    e["c4_component"] = "auth-manager"
    e["c4_level"] = "component"
    assert list(_validator().iter_errors(_doc(e))) == []


def test_entry_with_null_c4_component_validates():
    """L3 blocked: c4_component may be explicitly null while c4_container is set."""
    e = _base_entry()
    e["c4_container"] = "core"
    e["c4_component"] = None
    e["c4_level"] = "code"
    assert list(_validator().iter_errors(_doc(e))) == []


def test_entry_without_any_c4_tags_still_validates():
    """The new fields are OPTIONAL — a tag-less entry stays valid."""
    assert list(_validator().iter_errors(_doc(_base_entry()))) == []


def test_rejects_bad_c4_level_enum():
    e = _base_entry()
    e["c4_level"] = "system"  # only container|component|code are allowed here
    assert list(_validator().iter_errors(_doc(e)))


def test_real_home_assistant_index_still_validates_after_change():
    """BACKWARD-COMPAT: the shipped 46-entry multi-repo index has NO c4_* tags
    and MUST stay valid after the additive schema change."""
    data = yaml.safe_load(HA_INDEX.read_text())
    errors = list(_validator().iter_errors(data))
    assert errors == [], [e.message for e in errors]
    assert len(data["code_evidence_index"]["entries"]) == 46
