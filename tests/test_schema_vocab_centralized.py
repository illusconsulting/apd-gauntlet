"""Guard: the centralized vocabulary enums live ONLY in _defs.schema.json.

Every record schema must $ref `_defs.schema.json#/$defs/<name>` for the shared
vocabularies (severity, apd_goal, apd_tier, finding disposition, and the
[high, medium, low] ordinal scale) rather than inlining the enum. This test
walks every schema (except _defs, which DEFINES them, and metrics, the
report-facing rollup that intentionally enums the display token list containing
"info") and fails loudly listing any schema that still inlines a canonical set.
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).parent.parent
SCHEMA_DIR = REPO / "schemas"

# Canonical value-sets that MUST be $ref'd from _defs, never inlined.
CANONICAL_SETS: dict[str, frozenset[str]] = {
    "severity": frozenset({"critical", "high", "medium", "low", "informational"}),
    "apd_goal": frozenset({
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability",
    }),
    "apd_tier": frozenset({"trustworthiness", "scalability", "auditability"}),
    "disposition": frozenset({"gap", "risk", "uncertainty", "blocked"}),
    "ordinal_level": frozenset({"high", "medium", "low"}),
}

# These files are intentionally exempt from the guard.
#   _defs    — DEFINES the canonical $defs.
#   metrics  — report-facing rollup; enums the display token list with "info".
EXEMPT = {"_defs.schema.json", "metrics.schema.json"}


def _walk_enums(node, path):
    """Yield (json_path, enum_value_set) for every `enum` array found."""
    if isinstance(node, dict):
        enum = node.get("enum")
        if isinstance(enum, list):
            yield path, frozenset(v for v in enum if isinstance(v, str))
        for key, value in node.items():
            yield from _walk_enums(value, f"{path}/{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_enums(item, f"{path}/{i}")


def test_no_schema_inlines_centralized_vocab():
    offenders: list[str] = []
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        if schema_path.name in EXEMPT:
            continue
        schema = json.loads(schema_path.read_text())
        for json_path, value_set in _walk_enums(schema, ""):
            for def_name, canonical in CANONICAL_SETS.items():
                if value_set == canonical:
                    offenders.append(
                        f"{schema_path.name}{json_path} inlines the '{def_name}' "
                        f"vocabulary; replace with "
                        f'{{ "$ref": "_defs.schema.json#/$defs/{def_name}" }}'
                    )
    assert not offenders, (
        "Centralized vocabulary enums must be $ref'd from _defs, not inlined:\n"
        + "\n".join(offenders)
    )
