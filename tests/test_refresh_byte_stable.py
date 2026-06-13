"""Characterization tests: each refresher writes byte-identical data/*.json
for a fixed set of input bytes.

Written BEFORE the kb_fetch refactor (Tasks 6-8) so it pins CURRENT behavior.
After the refactor these MUST still pass byte-for-byte — that is the proof the
refactor changed only the fetch plumbing, not the projection or serialization.

Network is never touched: every test patches the refresher's fetch seam.

Refresher coverage:
  atlas        — fetch seam: patch refresh_atlas.fetch_atlas
                 projection: refresh_atlas(output_path=, fetched_at=)
                 fetched_at frozen -> byte-stable comparison
  cwe          — fetch seam: patch refresh_cwe.fetch_cwe_xml
                 projection: refresh_cwe(output_path=)
                 fetched_at is wall-clock (datetime.now) -> compare parsed JSON
                 with fetched_at field dropped
  mitre        — fetch seam: patch kb_fetch.urlopen (via fetch_mitre_bundle → fetch_pinned)
                 projection: fetch_and_project(out_path)
                 no timestamp field -> byte-stable comparison
  masvs        — fetch seam: patch refresh_mas.fetch_url
                 projection: refresh_masvs(output_path=, fetched_at=)
                 fetched_at frozen -> byte-stable comparison
  maswe        — fetch seam: patch refresh_mas.fetch_url (side_effect)
                 projection: refresh_maswe(output_path=, commit=, fetched_at=)
                 fetched_at frozen -> byte-stable comparison
  owasp        — fetch seam: patch refresh_owasp._fetch_json (side_effect)
                 projection: refresh_owasp(output_dir=)
                 fetched_at is wall-clock (datetime.now) -> compare parsed JSON
                 with fetched_at fields dropped across three files
  d3fend       — deferred to existing tests/test_refresh_d3fend.py;
                 the fixture-driven projection tests there provide the
                 byte-stability net for this refresher's logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from apd_gauntlet import refresh_atlas, refresh_cwe, refresh_mas, refresh_owasp
from apd_gauntlet.refresh_mitre import fetch_and_project

# ---------------------------------------------------------------------------
# Fixed input bytes — real-shape minimal payloads for each refresher
# ---------------------------------------------------------------------------

# --- ATLAS: minimal real-shape YAML bundle (matrices[0].techniques) --------
_ATLAS_BUNDLE_DICT = {
    "id": "ATLAS",
    "name": "MITRE ATLAS",
    "version": "5.6.0",
    "matrices": [
        {
            "id": "ATLAS",
            "name": "ATLAS Machine Learning Threat Matrix",
            "techniques": [
                {"id": "AML.T0051", "name": "LLM Prompt Injection"},
                {"id": "AML.T0051.000", "name": "Direct"},
                {"id": "AML.T0020", "name": "Poison Training Data"},
            ],
        }
    ],
}
_ATLAS_BUNDLE_BYTES: bytes = yaml.safe_dump(_ATLAS_BUNDLE_DICT).encode("utf-8")

# --- CWE: minimal real-shape XML (CWE 4.x namespace) ----------------------
_CWE_XML_BYTES: bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<Weakness_Catalog
  xmlns="http://cwe.mitre.org/cwe-7"
  Name="CWE" Version="4.14" Date="2024-02-29">
  <Weaknesses>
    <Weakness ID="79" Name="Improper Neutralization of Input During Web Page Generation"
              Abstraction="Base" Status="Stable">
      <Related_Weaknesses>
        <Related_Weakness Nature="ChildOf" CWE_ID="74" View_ID="1000"/>
      </Related_Weaknesses>
      <Demonstrative_Examples>
        <Demonstrative_Example>example</Demonstrative_Example>
      </Demonstrative_Examples>
      <Observed_Examples>
        <Observed_Example>obs</Observed_Example>
      </Observed_Examples>
    </Weakness>
    <Weakness ID="89" Name="Improper Neutralization of Special Elements used in an SQL Command"
              Abstraction="Base" Status="Stable">
      <Related_Weaknesses>
        <Related_Weakness Nature="ChildOf" CWE_ID="74" View_ID="1000"/>
      </Related_Weaknesses>
    </Weakness>
  </Weaknesses>
</Weakness_Catalog>
"""

# --- MITRE: minimal real-shape STIX bundle ---------------------------------
_MITRE_BUNDLE_DICT = {
    "created": "2026-01-01",
    "objects": [
        {
            "id": "course-of-action--1",
            "type": "course-of-action",
            "external_references": [
                {"source_name": "mitre-attack", "external_id": "M1041"}
            ],
        },
        {
            "id": "attack-pattern--1",
            "type": "attack-pattern",
            "name": "Data from Cloud Storage",
            "external_references": [
                {"source_name": "mitre-attack", "external_id": "T1530"}
            ],
        },
        {
            "type": "relationship",
            "relationship_type": "mitigates",
            "source_ref": "course-of-action--1",
            "target_ref": "attack-pattern--1",
        },
    ],
}
_MITRE_BUNDLE_BYTES: bytes = json.dumps(_MITRE_BUNDLE_DICT).encode("utf-8")

# --- MASVS: minimal real-shape OWASP_MASVS.yaml ----------------------------
_MASVS_YAML_BYTES: bytes = b"""
groups:
  - id: MASVS-STORAGE
    title: Storage
    controls:
      - id: MASVS-STORAGE-1
        statement: The app securely stores sensitive data.
      - id: MASVS-STORAGE-2
        statement: The app prevents leakage of sensitive data.
  - id: MASVS-CRYPTO
    title: Cryptography
    controls:
      - id: MASVS-CRYPTO-1
        statement: The app employs current strong cryptography.
"""

# --- MASWE: GitHub trees API response + one weakness markdown blob ---------
_MASWE_TREE_BYTES: bytes = json.dumps(
    {
        "tree": [
            {"path": "weaknesses/MASVS-STORAGE/MASWE-0001.md"},
            {"path": "docs/index.md"},  # ignored: no MASWE- in name
        ]
    }
).encode("utf-8")

_MASWE_BLOB_BYTES: bytes = b"""---
title: Insertion of Sensitive Information into Log Files
id: MASWE-0001
status: new
mappings:
  masvs-v2:
    - MASVS-STORAGE-2
  cwe:
    - 209
    - 532
---
Body prose that must be ignored.
"""

# --- OWASP: three {categories:[{id,title}]} JSON payloads ------------------
_OWASP_TOP10_PAYLOAD = {
    "categories": [
        {"id": "A03:2021", "title": "Injection"},
        {"id": "A05:2021", "title": "Security Misconfiguration"},
    ]
}
_OWASP_API_TOP10_PAYLOAD = {
    "categories": [
        {"id": "API3:2023", "title": "Broken Object Property Level Authorization"}
    ]
}
_OWASP_LLM_TOP10_PAYLOAD = {"categories": [{"id": "LLM01", "title": "Prompt Injection"}]}

# ---------------------------------------------------------------------------
# Golden-fixture helpers
# ---------------------------------------------------------------------------

_GOLDEN_DIR = Path(__file__).parent / "fixtures" / "kb_golden"
_FROZEN_DATE = "2026-06-11"


def _golden(name: str) -> bytes:
    """Read a committed golden file."""
    return (_GOLDEN_DIR / name).read_bytes()


def _strip_fetched_at(data: dict) -> dict:
    """Return a copy of data with any top-level 'fetched_at' key removed."""
    return {k: v for k, v in data.items() if k != "fetched_at"}


def _strip_fetched_at_from_owasp_dir(tmp_dir: Path) -> list[dict]:
    """Read all three OWASP output files; strip fetched_at for comparison."""
    names = ["owasp_top10.json", "owasp_api_top10.json", "owasp_llm_top10.json"]
    result = []
    for name in names:
        data = json.loads((tmp_dir / name).read_bytes())
        result.append(_strip_fetched_at(data))
    return result


# ---------------------------------------------------------------------------
# Characterization tests
# ---------------------------------------------------------------------------


def test_atlas_byte_stable(tmp_path: Path) -> None:
    """refresh_atlas writes byte-identical output for fixed input bytes."""
    out = tmp_path / "atlas-techniques.json"
    with patch("apd_gauntlet.refresh_atlas.fetch_atlas", return_value=_ATLAS_BUNDLE_BYTES):
        refresh_atlas.refresh_atlas(output_path=out, fetched_at=_FROZEN_DATE)
    assert out.read_bytes() == _golden("atlas-techniques.json")


def test_cwe_byte_stable(tmp_path: Path) -> None:
    """refresh_cwe writes structurally identical output (fetched_at stripped)."""
    out = tmp_path / "cwe.json"
    with patch("apd_gauntlet.refresh_cwe.fetch_cwe_xml", return_value=_CWE_XML_BYTES):
        refresh_cwe.refresh_cwe(output_path=out)
    actual = _strip_fetched_at(json.loads(out.read_bytes()))
    expected = _strip_fetched_at(json.loads(_golden("cwe.json")))
    assert actual == expected


def test_mitre_byte_stable(tmp_path: Path) -> None:
    """fetch_and_project writes byte-identical output for fixed input bytes."""
    out = tmp_path / "mitre-mitigations.json"

    def _mock_response(body: bytes) -> MagicMock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(body))}
        response.read.return_value = body
        return response

    with patch("apd_gauntlet.kb_fetch.urlopen") as mock_open:
        mock_open.return_value.__enter__.return_value = _mock_response(
            _MITRE_BUNDLE_BYTES
        )
        mock_open.return_value.__exit__.return_value = False
        fetch_and_project(out)
    assert out.read_bytes() == _golden("mitre-mitigations.json")


def test_masvs_byte_stable(tmp_path: Path) -> None:
    """refresh_masvs writes byte-identical output for fixed input bytes."""
    out = tmp_path / "masvs.json"
    with patch("apd_gauntlet.refresh_mas.fetch_url", return_value=_MASVS_YAML_BYTES):
        refresh_mas.refresh_masvs(output_path=out, fetched_at=_FROZEN_DATE)
    assert out.read_bytes() == _golden("masvs.json")


def test_maswe_byte_stable(tmp_path: Path) -> None:
    """refresh_maswe writes byte-identical output for fixed input bytes."""
    out = tmp_path / "maswe.json"

    def _fake_fetch(url: str) -> bytes:
        if "api.github.com" in url:
            return _MASWE_TREE_BYTES
        return _MASWE_BLOB_BYTES

    with patch("apd_gauntlet.refresh_mas.fetch_url", side_effect=_fake_fetch):
        refresh_mas.refresh_maswe(
            output_path=out,
            commit="test-commit-abc123",
            fetched_at=_FROZEN_DATE,
        )
    assert out.read_bytes() == _golden("maswe.json")


def test_owasp_byte_stable(tmp_path: Path) -> None:
    """refresh_owasp writes structurally identical output (fetched_at stripped)."""
    payloads = [
        _OWASP_TOP10_PAYLOAD,
        _OWASP_API_TOP10_PAYLOAD,
        _OWASP_LLM_TOP10_PAYLOAD,
    ]
    responses = [(json.dumps(p).encode("utf-8"), p) for p in payloads]
    calls: list[int] = [0]

    def _fake_fetch_json(url: str) -> tuple[bytes, object]:  # noqa: ARG001
        idx = calls[0]
        calls[0] += 1
        return responses[idx]

    with patch("apd_gauntlet.refresh_owasp._fetch_json", side_effect=_fake_fetch_json):
        refresh_owasp.refresh_owasp(output_dir=tmp_path)

    actual = _strip_fetched_at_from_owasp_dir(tmp_path)
    golden_dir = _GOLDEN_DIR / "owasp"
    expected = []
    for name in ["owasp_top10.json", "owasp_api_top10.json", "owasp_llm_top10.json"]:
        data = json.loads((golden_dir / name).read_bytes())
        expected.append(_strip_fetched_at(data))
    assert actual == expected
