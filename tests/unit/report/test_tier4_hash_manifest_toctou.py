"""Regression tests for PR-T4-F — hash manifest TOCTOU fix.

Covers the single-read ``_yaml_with_hash`` helper, the preserved public
signatures of ``_yaml`` and ``_hash``, and the load_run manifest hashes
that must remain byte-identical to ``sha256(file content)[:16]`` so
downstream consumers comparing against shipped hashes are unaffected.
"""
from __future__ import annotations

import hashlib
import pathlib
import textwrap

import pytest
from apd_gauntlet.report.loader import (
    MalformedArtifactError,
    _hash,
    _yaml,
    _yaml_with_hash,
    load_run,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE = REPO_ROOT / "examples" / "apd-20260601-claim-event-bus" / "expected"


def _write(tmp_path: pathlib.Path, name: str, body: str) -> pathlib.Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def test_yaml_with_hash_matches_separate_calls(tmp_path: pathlib.Path) -> None:
    """_yaml_with_hash returns the same doc as _yaml and the same hash as _hash."""
    path = _write(
        tmp_path,
        "demo.yaml",
        """
        run_id: r1
        notes: hello world
        items:
          - a
          - b
        """,
    )

    fused_doc, fused_hash = _yaml_with_hash(path)
    legacy_doc = _yaml(path)
    legacy_hash = _hash(path)

    assert fused_doc == legacy_doc
    assert fused_hash == legacy_hash


def test_yaml_with_hash_returns_empty_dict_for_none_doc(
    tmp_path: pathlib.Path,
) -> None:
    """Empty / comment-only YAML resolves to an empty dict but still produces a hash."""
    empty = _write(tmp_path, "empty.yaml", "")
    comments_only = _write(
        tmp_path,
        "comments.yaml",
        """
        # only a comment, no document body
        # another comment
        """,
    )

    doc_a, hash_a = _yaml_with_hash(empty)
    doc_b, hash_b = _yaml_with_hash(comments_only)

    assert doc_a == {}
    assert doc_b == {}
    # Hashes are still computed from the bytes and must match the legacy helper.
    assert hash_a == _hash(empty)
    assert hash_b == _hash(comments_only)


def test_yaml_with_hash_raises_on_non_dict_top_level(
    tmp_path: pathlib.Path,
) -> None:
    """A list top level must raise MalformedArtifactError, like the prior _yaml."""
    path = _write(
        tmp_path,
        "list.yaml",
        """
        - item one
        - item two
        """,
    )
    with pytest.raises(MalformedArtifactError):
        _yaml_with_hash(path)


def test_yaml_with_hash_hash_is_16_chars_hex(tmp_path: pathlib.Path) -> None:
    """Hash format is the first 16 hex chars of SHA-256."""
    path = _write(tmp_path, "shape.yaml", "k: v\n")
    _doc, hash_str = _yaml_with_hash(path)
    assert isinstance(hash_str, str)
    assert len(hash_str) == 16
    assert all(c in "0123456789abcdef" for c in hash_str)
    # And it actually equals the expected truncation.
    expected = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    assert hash_str == expected


@pytest.mark.skipif(
    not EXAMPLE.is_dir(),
    reason="requires the canonical example run fixture",
)
def test_load_run_hashes_match_file_content() -> None:
    """source_hashes recorded by load_run must equal sha256(file)[:16] verbatim."""
    run_dir = EXAMPLE
    artifacts = load_run(run_dir)

    # Path resolution for each well-known manifest entry. Required artifacts
    # always exist; optional ones only appear in the manifest when present
    # on disk, so iterate over what load_run actually recorded.
    name_to_path: dict[str, pathlib.Path] = {
        ".apd-run.yaml": run_dir / ".apd-run.yaml",
        "asset-inventory.yaml": run_dir / "00-context" / "asset-inventory.yaml",
        "deduped-findings.yaml": run_dir / "40-synthesis" / "deduped-findings.yaml",
        "deduped-capabilities.yaml": run_dir
        / "40-synthesis"
        / "deduped-capabilities.yaml",
        "nist-coverage.yaml": run_dir / "40-synthesis" / "nist-coverage.yaml",
        "attack-exposure.yaml": run_dir / "40-synthesis" / "attack-exposure.yaml",
        "apd-coverage-matrix.yaml": run_dir
        / "40-synthesis"
        / "apd-coverage-matrix.yaml",
        "attack-paths.yaml": run_dir / "40-synthesis" / "attack-paths.yaml",
        "asset-graph.yaml": run_dir / "40-synthesis" / "asset-graph.yaml",
        "defense-graph.yaml": run_dir / "40-synthesis" / "defense-graph.yaml",
        "report-data.yaml": run_dir / "40-synthesis" / "report-data.yaml",
        "metrics.yaml": run_dir / "40-synthesis" / "metrics.yaml",
        # M4 / ADR-0021 optional C4 inputs — present on this fixture (it seeds
        # a code-evidence-index.yaml) / when assemble-c4 has run.
        "code-evidence-index.yaml": run_dir
        / "00-context"
        / "code-evidence-index.yaml",
        "c4-model.yaml": run_dir / "40-synthesis" / "c4-model.yaml",
    }

    assert artifacts.source_hashes, "expected at least required-artifact hashes"
    for name, recorded in artifacts.source_hashes.items():
        path = name_to_path.get(name)
        assert path is not None, f"unexpected manifest entry: {name}"
        expected = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        assert recorded == expected, (
            f"{name}: manifest hash {recorded} != sha256(file)[:16] {expected}"
        )


def test_yaml_preserves_public_signature(tmp_path: pathlib.Path) -> None:
    """The legacy _yaml(path) -> dict signature still works for callers."""
    path = _write(
        tmp_path,
        "legacy.yaml",
        """
        alpha: 1
        beta:
          gamma: two
        """,
    )
    out = _yaml(path)
    assert out == {"alpha": 1, "beta": {"gamma": "two"}}
    # And the helper still rejects non-mapping top levels.
    bad = _write(tmp_path, "bad.yaml", "- 1\n- 2\n")
    with pytest.raises(MalformedArtifactError):
        _yaml(bad)
