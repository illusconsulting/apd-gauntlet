"""Tests for the refresh-d3fend command (network mocked).

Mirrors the discipline of ``test_refresh_cwe.py`` and ``test_refresh_owasp.py``:

* The standard timeout and size-cap constants are pinned.
* The :func:`apd_gauntlet.refresh_d3fend.project_d3fend_json` projection is
  exercised against a real-shape fixture (``tests/fixtures/reference_data/
  d3fend-sample.json``) that mimics the SPARQL-JSON-results envelope the live
  D3FEND API returns.
* The IRI-to-short-code parser is exercised directly against known long names.
* ``source_sha256`` is computed over the *raw upstream bytes* (matching the
  Task 9 fix that landed in ``refresh_owasp.py``).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from apd_gauntlet.refresh_d3fend import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    _iri_to_attack_id,
    _iri_to_d3fend_id,
    fetch_d3fend_json,
    project_d3fend_json,
    refresh_d3fend,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "reference_data" / "d3fend-sample.json"
)


@pytest.fixture
def sample_d3fend_json_bytes() -> bytes:
    """Fixture JSON-bytes shaped like the live D3FEND full-mappings response."""
    return FIXTURE_PATH.read_bytes()


# ---- security-hardening constants ----------------------------------------


def test_d3fend_timeout_constant_is_60s() -> None:
    assert DEFAULT_TIMEOUT_SECONDS == 60


def test_d3fend_size_cap_is_200_mib() -> None:
    assert MAX_RESPONSE_BYTES == 200 * 1024 * 1024


# ---- projection ----------------------------------------------------------


def test_project_extracts_d3fend_entries_with_counter_mappings(
    sample_d3fend_json_bytes: bytes,
) -> None:
    """Projection extracts the D3FEND short code + name + counters_attack list."""
    projected = project_d3fend_json(sample_d3fend_json_bytes)
    assert "entries" in projected
    assert "source_sha256" in projected
    assert "fetched_at" in projected
    assert "source_url" in projected

    by_id = {e["d3fend_id"]: e for e in projected["entries"]}
    assert "D3-NTF" in by_id
    ntf = by_id["D3-NTF"]
    assert ntf["name"]
    # T1078 must show up — and the duplicate T1566 row must be deduplicated.
    assert "T1078" in ntf["counters_attack"]
    assert ntf["counters_attack"].count("T1566") == 1


def test_project_dedupes_counters_within_a_technique(
    sample_d3fend_json_bytes: bytes,
) -> None:
    """SPARQL JSON-results can repeat the same (def_tech, off_tech_id) row.

    The fixture ships a duplicate ``T1566`` row for ``D3-NTF`` so this is
    explicitly exercised. Mirrors the Task 8 lesson: deduplicate list-of-things
    during projection because upstream shapes routinely repeat the same fact.
    """
    projected = project_d3fend_json(sample_d3fend_json_bytes)
    by_id = {e["d3fend_id"]: e for e in projected["entries"]}
    ntf = by_id["D3-NTF"]
    # Each counter appears at most once.
    assert len(ntf["counters_attack"]) == len(set(ntf["counters_attack"]))


def test_project_sha256_matches_raw_input(sample_d3fend_json_bytes: bytes) -> None:
    """source_sha256 is computed over the *raw* upstream bytes (Task 9 fix)."""
    projected = project_d3fend_json(sample_d3fend_json_bytes)
    assert projected["source_sha256"] == hashlib.sha256(
        sample_d3fend_json_bytes
    ).hexdigest()


def test_project_entries_sorted_by_id(sample_d3fend_json_bytes: bytes) -> None:
    """Entries are sorted by ``d3fend_id`` for deterministic diffs across refreshes."""
    projected = project_d3fend_json(sample_d3fend_json_bytes)
    ids = [e["d3fend_id"] for e in projected["entries"]]
    assert ids == sorted(ids)


def test_project_recognises_all_three_techniques(
    sample_d3fend_json_bytes: bytes,
) -> None:
    """The 3 distinct def_tech values in the fixture each produce one entry."""
    projected = project_d3fend_json(sample_d3fend_json_bytes)
    by_id = {e["d3fend_id"]: e for e in projected["entries"]}
    assert {"D3-NTF", "D3-MFA", "D3-NTSA"} <= set(by_id)


def test_project_handles_empty_results() -> None:
    """An empty SPARQL bindings list projects to zero entries (no crash)."""
    empty = json.dumps({"head": {"vars": []}, "results": {"bindings": []}}).encode()
    projected = project_d3fend_json(empty)
    assert projected["entries"] == []
    assert projected["source_sha256"] == hashlib.sha256(empty).hexdigest()


# ---- IRI parsers ---------------------------------------------------------


def test_iri_to_d3fend_id_resolves_fragment_long_name() -> None:
    """A '#NetworkTrafficFiltering' IRI fragment resolves via the seeded map."""
    iri = "http://d3fend.mitre.org/ontologies/d3fend.owl#NetworkTrafficFiltering"
    assert _iri_to_d3fend_id(iri) == "D3-NTF"


def test_iri_to_d3fend_id_resolves_known_short_codes() -> None:
    """All plan-listed long-name lookups that are in the live ontology return D3-XX."""
    cases = {
        "Multi-factorAuthentication": "D3-MFA",
        "FileAnalysis": "D3-FA",
        "FileEncryption": "D3-FE",
        "NetworkTrafficSignatureAnalysis": "D3-NTSA",
        "AuthenticationCacheInvalidation": "D3-ANCI",
    }
    for long_name, expected in cases.items():
        iri = f"http://d3fend.mitre.org/ontologies/d3fend.owl#{long_name}"
        assert _iri_to_d3fend_id(iri) == expected, long_name


def test_iri_to_d3fend_id_passes_through_d3_prefix_in_iri() -> None:
    """If the IRI already ends in 'D3-XX', use it directly."""
    iri = "http://example.invalid/d3fend.owl#D3-NTF"
    assert _iri_to_d3fend_id(iri) == "D3-NTF"


def test_iri_to_d3fend_id_returns_none_for_unknown() -> None:
    """An unknown long name returns ``None`` rather than fabricating a code."""
    iri = "http://d3fend.mitre.org/ontologies/d3fend.owl#NotARealTechnique"
    assert _iri_to_d3fend_id(iri) is None


def test_iri_to_d3fend_id_uses_explicit_node_property_first() -> None:
    """When a node carries an explicit ``d3fend:d3f-id``, that wins."""
    node = {"d3fend:d3f-id": "D3-XYZ"}
    iri = "http://d3fend.mitre.org/ontologies/d3fend.owl#NotARealTechnique"
    assert _iri_to_d3fend_id(iri, node=node) == "D3-XYZ"


def test_iri_to_attack_id_extracts_T_pattern() -> None:
    assert _iri_to_attack_id("http://example/d3fend.owl#T1078") == "T1078"
    assert _iri_to_attack_id("attack:T1110.001") == "T1110.001"


def test_iri_to_attack_id_returns_none_for_non_attack_iri() -> None:
    assert _iri_to_attack_id(None) is None
    assert _iri_to_attack_id("") is None
    assert _iri_to_attack_id("http://example/d3fend.owl#TokenBinding") is None


# ---- network hardening ---------------------------------------------------


def test_fetch_d3fend_json_passes_timeout() -> None:
    payload = (
        b'{"head":{"vars":[]},"results":{"bindings":[]}}'
    )
    with patch("apd_gauntlet.refresh_d3fend.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(len(payload))}
        response.read.return_value = payload
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        fetch_d3fend_json()
        _, kwargs = mock.call_args
        assert kwargs.get("timeout") == DEFAULT_TIMEOUT_SECONDS


def test_fetch_d3fend_json_rejects_oversize_response_content_length() -> None:
    """Content-Length pre-check rejects responses that advertise > 200 MiB."""
    with patch("apd_gauntlet.refresh_d3fend.urlopen") as mock:
        response = MagicMock()
        response.headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_d3fend_json()


def test_fetch_d3fend_json_rejects_oversize_response_post_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense in depth: even with no Content-Length, oversize body raises."""
    monkeypatch.setattr("apd_gauntlet.refresh_d3fend.MAX_RESPONSE_BYTES", 1024)
    fake_oversize = b"x" * 2048
    with patch("apd_gauntlet.refresh_d3fend.urlopen") as mock:
        response = MagicMock()
        response.headers = {}
        response.read.return_value = fake_oversize
        mock.return_value.__enter__.return_value = response
        mock.return_value.__exit__.return_value = False
        with pytest.raises(ValueError, match="exceeds maximum"):
            fetch_d3fend_json()


# ---- end-to-end write ----------------------------------------------------


def test_refresh_d3fend_writes_to_data_dir(
    tmp_path: Path, sample_d3fend_json_bytes: bytes
) -> None:
    """End-to-end: refresh_d3fend writes a valid JSON file with the raw-bytes hash."""
    with patch(
        "apd_gauntlet.refresh_d3fend.fetch_d3fend_json",
        return_value=sample_d3fend_json_bytes,
    ):
        target = tmp_path / "d3fend.json"
        refresh_d3fend(output_path=target)
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["source_sha256"] == hashlib.sha256(
        sample_d3fend_json_bytes
    ).hexdigest()
    assert data["source_url"]
    assert "entries" in data and len(data["entries"]) >= 1
