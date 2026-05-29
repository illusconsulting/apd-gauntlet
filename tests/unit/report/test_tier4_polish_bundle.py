# tests/unit/report/test_tier4_polish_bundle.py
"""Regression tests for PR-T4-H — the four-item polish bundle.

Each test exercises one defect closure:

1. ``contradictions_section`` emits a ``capability.ids`` list (canonical) and
   retains ``capability.id`` as a back-compat joined string. The React
   template can iterate ``ids`` so anchor links don't break when a
   contradiction references multiple capabilities.
2. ``DEFAULT_BUNDLE`` resolves via ``importlib.resources`` so wheel installs
   work the same as editable installs; the fallback path covers the rare
   editable-install case where ``resources.files`` cannot produce a real
   filesystem path.
3. ``emit.hash_dir`` reads files in 1 MiB chunks (worst-case memory bounded)
   and skips symlinks / non-regular files (a bundle is a self-contained tree
   of regular files; chasing symlinks is unsafe).
4. The ``examples/apd-20260601-claim-event-bus/`` example carries the input
   scaffolding (``.apd-run.yaml``, ``00-context/asset-inventory.yaml``,
   ``inputs/README.md``) at the root so ``apd-gauntlet validate`` against
   the example root demonstrates the full directory shape.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any
from unittest import mock

import pytest
from apd_gauntlet.report.build import DEFAULT_BUNDLE, _resolve_default_bundle
from apd_gauntlet.report.emit import hash_dir
from apd_gauntlet.report.transform import contradictions_section

REPO = pathlib.Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# H1: contradictions_section emits capability.ids as a list
# ---------------------------------------------------------------------------


@dataclass
class _StubArtifacts:
    """Minimal stub that satisfies the ``contradictions`` attribute access
    pattern in ``contradictions_section``. Avoids the full RunArtifacts
    constructor (which has 20+ required fields irrelevant to this test).
    """
    contradictions: list[dict[str, Any]] = field(default_factory=list)


def test_contradictions_section_single_id_yields_list_of_one() -> None:
    """A contradiction with one ``capability_id`` must emit ``ids: [<id>]``
    plus the joined back-compat ``id`` string."""
    artifacts = _StubArtifacts(contradictions=[
        {
            "id": "contra-1",
            "finding_id": "f-1",
            "finding_assertion": "claim A",
            "capability_id": "cap-001",
            "capability_assertion": "claim B",
            "evidence_comparison": "A != B",
            "recommended_resolution": "verify",
        }
    ])
    out = contradictions_section(artifacts)  # type: ignore[arg-type]
    assert len(out) == 1
    cap = out[0]["capability"]
    assert cap["ids"] == ["cap-001"]
    # Back-compat: single id renders as itself, not a list.
    assert cap["id"] == "cap-001"
    assert cap["assertion"] == "claim B"


def test_contradictions_section_multiple_ids_yields_list_preserving_order() -> None:
    """A contradiction with ``capability_ids: [...]`` must emit the full list
    on ``ids`` (canonical) plus the joined display string on ``id``."""
    artifacts = _StubArtifacts(contradictions=[
        {
            "id": "contra-2",
            "finding_id": "f-2",
            "finding_assertion": "claim A",
            "capability_ids": ["cap-001", "cap-002", "cap-003"],
            "capability_assertion": "claim B",
            "evidence_comparison": "scopes disagree",
            "recommended_resolution": "split scopes",
        }
    ])
    out = contradictions_section(artifacts)  # type: ignore[arg-type]
    cap = out[0]["capability"]
    assert cap["ids"] == ["cap-001", "cap-002", "cap-003"]
    assert cap["id"] == "cap-001 + cap-002 + cap-003"


def test_contradictions_section_no_capability_ids_yields_empty_list() -> None:
    """A malformed contradiction (no capability id at all) must emit
    ``ids: []`` and ``id: None`` rather than raising or fabricating ids."""
    artifacts = _StubArtifacts(contradictions=[
        {
            "id": "contra-3",
            "finding_id": "f-3",
            "finding_assertion": "claim A",
            # no capability_id, no capability_ids
            "capability_assertion": "claim B",
        }
    ])
    out = contradictions_section(artifacts)  # type: ignore[arg-type]
    cap = out[0]["capability"]
    assert cap["ids"] == []
    assert cap["id"] is None


def test_contradictions_section_filters_non_string_ids() -> None:
    """Defensive: a list with a None or non-string entry must be filtered so
    the joined display string stays sane and the ``ids`` list contains only
    real string ids."""
    artifacts = _StubArtifacts(contradictions=[
        {
            "id": "contra-4",
            "capability_ids": ["cap-001", None, 42, "cap-002"],
        }
    ])
    out = contradictions_section(artifacts)  # type: ignore[arg-type]
    cap = out[0]["capability"]
    assert cap["ids"] == ["cap-001", "cap-002"]
    assert cap["id"] == "cap-001 + cap-002"


def test_contradictions_section_clean_input_round_trip_against_example() -> None:
    """Regression: the canonical example's lone contradiction renders with
    the new shape without raising — the example exercises a single
    ``capability_id`` (singular) value."""
    from apd_gauntlet.report.loader import load_run

    example = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
    artifacts = load_run(example)
    out = contradictions_section(artifacts)
    # The example fixture carries exactly one contradiction (conf-cap-89e19793
    # vs the kafka-payload finding). Both keys must be present.
    assert len(out) >= 1
    cap = out[0]["capability"]
    assert "ids" in cap
    assert isinstance(cap["ids"], list)
    assert cap["ids"], "non-empty contradiction must have at least one capability id"


# ---------------------------------------------------------------------------
# H2: DEFAULT_BUNDLE via importlib.resources + editable-install fallback
# ---------------------------------------------------------------------------


def test_default_bundle_resolves_to_existing_dir() -> None:
    """The module-level ``DEFAULT_BUNDLE`` constant must resolve to the
    shipped report-template directory under either install layout."""
    assert isinstance(DEFAULT_BUNDLE, pathlib.Path)
    assert DEFAULT_BUNDLE.is_dir(), (
        f"DEFAULT_BUNDLE {DEFAULT_BUNDLE} should be a directory under "
        "either an editable or wheel install"
    )
    # The bundle must carry the index.html the loader expects.
    assert (DEFAULT_BUNDLE / "index.html").is_file()


def test_resolve_default_bundle_uses_importlib_resources_by_default() -> None:
    """The normal resolution path runs ``importlib.resources.files`` against
    the ``apd_gauntlet`` package and returns the package-data subdirectory."""
    resolved = _resolve_default_bundle()
    assert resolved.is_dir()
    # The shipped bundle always carries .source-hash and index.html.
    assert (resolved / ".source-hash").is_file()


def test_resolve_default_bundle_falls_back_when_resources_fails() -> None:
    """When ``importlib.resources.files`` raises (simulated wheel-install
    edge case), the fallback walks up from ``__file__`` and locates the
    in-tree report-template directory."""
    import importlib

    # ``_resolve_default_bundle`` does ``from importlib import resources``
    # inside the function body. Patching ``importlib.resources.files`` to
    # raise simulates the failure mode the fallback is designed for.
    real_files = importlib.resources.files

    def _boom(*_a: Any, **_kw: Any) -> Any:
        raise ModuleNotFoundError("simulated wheel-install resource failure")

    with mock.patch.object(importlib.resources, "files", _boom):
        resolved = _resolve_default_bundle()
    # Sanity: the patch is undone.
    assert importlib.resources.files is real_files
    # Fallback must still land on a real directory in the editable tree.
    assert resolved.is_dir()
    assert (resolved / "index.html").is_file()


# ---------------------------------------------------------------------------
# H3: hash_dir streams chunked reads + skips symlinks + skips non-regular files
# ---------------------------------------------------------------------------


def test_hash_dir_matches_inline_sha256_for_regular_files(
    tmp_path: pathlib.Path,
) -> None:
    """Sanity: the streamed implementation produces the same digest as the
    naive ``read_bytes`` implementation it replaced."""
    (tmp_path / "a.txt").write_bytes(b"alpha\n")
    (tmp_path / "b.txt").write_bytes(b"beta\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_bytes(b"gamma\n")

    expected = hashlib.sha256()
    for f in sorted(tmp_path.rglob("*")):
        if f.is_file():
            expected.update(f.relative_to(tmp_path).as_posix().encode())
            expected.update(b"\x00")
            expected.update(f.read_bytes())
    assert hash_dir(tmp_path) == expected.hexdigest()[:16]


def test_hash_dir_skips_symlinks(tmp_path: pathlib.Path) -> None:
    """A symlink inside the bundle directory must not contribute to the
    hash — adding a symlink alongside the same regular files must yield the
    same digest as the regular-files-only baseline."""
    (tmp_path / "real.txt").write_bytes(b"real bytes\n")
    baseline = hash_dir(tmp_path)

    # Create a symlink pointing at the existing regular file.
    link = tmp_path / "alias.txt"
    try:
        os.symlink(tmp_path / "real.txt", link)
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"symlinks unsupported on this platform: {e}")

    with_symlink = hash_dir(tmp_path)
    assert with_symlink == baseline, (
        "hash_dir must skip symlinks so the manifest stays stable across "
        "platforms that may or may not surface a symlink"
    )


def test_hash_dir_skips_broken_symlinks_without_crashing(
    tmp_path: pathlib.Path,
) -> None:
    """A broken / dangling symlink must not crash hash_dir — the old
    implementation called ``read_bytes`` which would have raised
    FileNotFoundError."""
    (tmp_path / "real.txt").write_bytes(b"real\n")
    try:
        os.symlink(tmp_path / "does-not-exist.txt", tmp_path / "dangling.lnk")
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"symlinks unsupported on this platform: {e}")
    # Must not raise.
    digest = hash_dir(tmp_path)
    assert digest


def test_hash_dir_streams_chunked_reads(tmp_path: pathlib.Path) -> None:
    """A large file must be readable without OOM. We can't easily prove
    'streaming' without mocking, so we exercise the chunk_size kwarg
    explicitly and confirm the digest matches the naive computation.
    """
    # 4 MiB payload — large enough to exercise multiple chunks at the
    # default 1 MiB chunk size.
    payload = b"x" * (4 * 1024 * 1024)
    (tmp_path / "big.bin").write_bytes(payload)
    digest_default = hash_dir(tmp_path)
    digest_small_chunks = hash_dir(tmp_path, chunk_size=4096)
    digest_one_byte = hash_dir(tmp_path, chunk_size=1)
    assert digest_default == digest_small_chunks == digest_one_byte, (
        "digest must be chunk-size-independent"
    )


def test_hash_dir_stable_across_invocations(tmp_path: pathlib.Path) -> None:
    """Idempotence: calling hash_dir twice on the same tree returns the
    same digest."""
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "b.txt").write_bytes(b"b")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "c.txt").write_bytes(b"c")
    assert hash_dir(tmp_path) == hash_dir(tmp_path)


# ---------------------------------------------------------------------------
# H4: example scaffold files present at the example root
# ---------------------------------------------------------------------------


EXAMPLE_ROOT = REPO / "examples" / "apd-20260601-claim-event-bus"


def test_example_apd_run_yaml_exists() -> None:
    """The example's ``.apd-run.yaml`` must sit at the run root so
    ``apd-gauntlet validate`` against the example root finds the expected
    shape."""
    assert (EXAMPLE_ROOT / ".apd-run.yaml").is_file()


def test_example_asset_inventory_exists() -> None:
    """The example's ``00-context/asset-inventory.yaml`` must exist at the
    run root (scaffold pass-through from the curated ``expected/`` tree)."""
    inv = EXAMPLE_ROOT / "00-context" / "asset-inventory.yaml"
    assert inv.is_file()
    # Sanity: the file is a well-formed YAML document and at least mentions
    # one asset shape so a reader landing here understands the contract.
    import yaml
    doc = yaml.safe_load(inv.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert "assets" in doc
    assert isinstance(doc["assets"], list)
    assert doc["assets"], "scaffold inventory must carry at least one asset"


def test_example_inputs_readme_exists() -> None:
    """The example's ``inputs/README.md`` must exist to document the
    intake-artifact shape for readers exploring the repo."""
    readme = EXAMPLE_ROOT / "inputs" / "README.md"
    assert readme.is_file()
    body = readme.read_text(encoding="utf-8")
    # Should reference at least one of the input artifact filenames.
    assert "tech_plan.md" in body or "threat-model" in body
