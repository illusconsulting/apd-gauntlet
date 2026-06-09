"""Verify every schema under schemas/ is itself a valid JSON Schema draft 2020-12 document."""
from __future__ import annotations

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"


@pytest.mark.parametrize("schema_path", sorted(SCHEMA_DIR.glob("*.schema.json")))
def test_schema_is_valid_meta(schema_path):
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)


def test_defs_declares_mas_id_patterns():
    """_defs carries the three OWASP MAS id patterns for MASWE/MASVS (v1.7)."""
    import json
    import pathlib
    import re

    repo = pathlib.Path(__file__).resolve().parent.parent
    defs = json.loads((repo / "schemas" / "_defs.schema.json").read_text())["$defs"]

    assert defs["maswe_id"]["pattern"] == r"^MASWE-[0-9]{4}$"
    assert re.match(defs["maswe_id"]["pattern"], "MASWE-0001")
    assert not re.match(defs["maswe_id"]["pattern"], "MASWE-1")

    cat = r"^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)$"
    assert defs["masvs_category_id"]["pattern"] == cat
    assert re.match(cat, "MASVS-STORAGE")
    assert not re.match(cat, "MASVS-STORAGE-1")

    ctrl = r"^MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9][0-9]*$"
    assert defs["masvs_control_id"]["pattern"] == ctrl
    assert re.match(ctrl, "MASVS-STORAGE-1")
    assert not re.match(ctrl, "MASVS-STORAGE-0")
    assert not re.match(ctrl, "MASVS-BOGUS-1")
