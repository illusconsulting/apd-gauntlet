# tools/apd_gauntlet/report/emit.py
"""Serialize the transformed window.APD_DATA dict, copy the precompiled bundle,
and write a per-run build manifest.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import json
import os
import pathlib
import shutil
from typing import Any


class BundleMissingError(FileNotFoundError):
    """Raised when the precompiled template bundle is absent."""


def _normalize_for_json(value: Any, *, path: str = "$") -> Any:
    """Walk value, convert datetime/date/set to JSON-safe form, raise on
    unknown types. Replaces the lossy `default=str` shortcut.
    """
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (str, int, float)):
        return value
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(_normalize_for_json(v, path=f"{path}[set]") for v in value)
    if isinstance(value, tuple):
        return [_normalize_for_json(v, path=f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, list):
        return [_normalize_for_json(v, path=f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, dict):
        return {
            str(k): _normalize_for_json(v, path=f"{path}.{k}")
            for k, v in value.items()
        }
    raise TypeError(f"unserializable type at {path}: {type(value).__name__}")


def _atomic_write_text(path: pathlib.Path, body: str) -> None:
    """Write `body` to `path` atomically: temp file in same dir + os.replace.

    Same-directory tmp is required for POSIX rename atomicity across
    filesystems (cross-fs rename is a copy + delete).
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        # Best-effort cleanup of leftover tmp on any failure.
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()
        raise


def write_data_js(data: dict[str, Any], path: pathlib.Path) -> None:
    """Write `window.APD_DATA = {...};` to path. JSON body is pretty-printed,
    Unicode preserved (ensure_ascii=False) so diffs are human-readable.

    Hygiene (T3-A):
      - Payload is walked through `_normalize_for_json` first so unknown
        types raise loudly instead of being silently `str()`-coerced.
      - `allow_nan=False` causes NaN / +Inf / -Inf to raise rather than
        emit non-JSON `NaN`/`Infinity` tokens that browsers reject.
      - Any literal `</` in the serialized body is rewritten to `<\\/` as
        defense-in-depth against a stray `</script>` inside string values
        prematurely closing the embedded script tag.
    """
    payload = _normalize_for_json(data)
    body = json.dumps(
        payload, indent=2, ensure_ascii=False, sort_keys=False, allow_nan=False
    )
    body = body.replace("</", "<\\/")
    _atomic_write_text(path, f"window.APD_DATA = {body};\n")


# Files owned by emit.py (not the bundle source); preserve across prune.
_PROTECTED_OUTPUT_FILES = frozenset({"data.js", "build-manifest.txt"})


def copy_bundle(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copy the precompiled bundle from src into dst, pruning files that
    exist in dst but not in src so a previous bundle version cannot poison
    the new copy. data.js and build-manifest.txt are preserved because they
    are written by emit, not shipped from the source bundle.
    """
    if not src.exists():
        raise BundleMissingError(
            f"precompiled bundle missing at {src}. "
            "Run `python tools/build_report_template.py` to regenerate."
        )
    dst.mkdir(parents=True, exist_ok=True)

    # Inventory the source bundle's file list (relative paths).
    src_files: set[pathlib.Path] = set()
    for p in src.rglob("*"):
        if p.is_file():
            src_files.add(p.relative_to(src))

    # Prune files in dst not in src — except protected (emit-owned) outputs.
    for p in dst.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(dst)
        if rel.name in _PROTECTED_OUTPUT_FILES:
            continue
        if rel not in src_files:
            # Best-effort prune; surface as a hint, not a hard failure.
            with contextlib.suppress(OSError):
                p.unlink()
    # Remove now-empty subdirectories left over from pruned files.
    for p in sorted(dst.rglob("*"), key=lambda q: -len(q.parts)):
        if p.is_dir() and not any(p.iterdir()):
            with contextlib.suppress(OSError):
                p.rmdir()

    # Copy / overwrite source into dst.
    shutil.copytree(src, dst, dirs_exist_ok=True)


def write_manifest(
    path: pathlib.Path,
    *,
    framework_version: str,
    source_hashes: dict[str, str],
    bundle_hash: str,
) -> None:
    """Write a flat key=value manifest for traceability."""
    lines = [
        f"generated_at={_dt.datetime.now(_dt.timezone.utc).isoformat()}",
        f"framework_version={framework_version}",
        f"bundle_hash={bundle_hash}",
    ]
    for k, v in sorted(source_hashes.items()):
        lines.append(f"{k}={v}")
    _atomic_write_text(path, "\n".join(lines) + "\n")


def hash_dir(dir_path: pathlib.Path) -> str:
    """Hash every file under dir_path (sorted), returning a short hex digest.

    Used for bundle_hash in the manifest.
    """
    h = hashlib.sha256()
    for f in sorted(dir_path.rglob("*")):
        if f.is_file():
            h.update(f.relative_to(dir_path).as_posix().encode())
            h.update(b"\x00")
            h.update(f.read_bytes())
    return h.hexdigest()[:16]
