# tools/apd_gauntlet/report/emit.py
"""Serialize the transformed window.APD_DATA dict, copy the precompiled bundle,
and write a per-run build manifest.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import shutil
from typing import Any


class BundleMissingError(FileNotFoundError):
    """Raised when the precompiled template bundle is absent."""


def write_data_js(data: dict[str, Any], path: pathlib.Path) -> None:
    """Write `window.APD_DATA = {...};` to path. JSON body is pretty-printed,
    Unicode preserved (ensure_ascii=False) so diffs are human-readable.
    """
    body = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False, default=str)
    path.write_text(f"window.APD_DATA = {body};\n")


def copy_bundle(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copy every file under the precompiled bundle dir into dst.

    Uses dirs_exist_ok so re-runs overwrite cleanly.
    """
    if not src.exists():
        raise BundleMissingError(
            f"precompiled bundle missing at {src}. "
            "Run `python tools/build_report_template.py` to regenerate."
        )
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
    path.write_text("\n".join(lines) + "\n")


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
