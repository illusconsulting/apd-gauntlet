"""Scaffold a runs/<run-id>/ directory."""
from __future__ import annotations

import os
import pathlib
import re
import shutil
from collections.abc import Iterator

import yaml

from . import FRAMEWORK_VERSION

SUBDIRS = [
    "inputs", "00-context", "10-trustworthiness",
    "20-scalability", "30-auditability", "40-synthesis",
]

# Run IDs must be plain identifiers so that `root / run_id` cannot escape `root`.
# Permits letters, digits, dashes, dots, and underscores; rejects path separators,
# parent-directory segments, absolute paths, and the empty string.
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _validate_run_id(run_id: str) -> None:
    if not _RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise ValueError(
            f"invalid run_id {run_id!r}: must match {_RUN_ID_RE.pattern} "
            "and contain no '..' segments"
        )


class UnsafeInputsError(ValueError):
    """The inputs folder holds links that point outside it."""


def _is_within(path: pathlib.Path, root: pathlib.Path) -> bool:
    return path == root or root in path.parents


def _links_under(top: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield every symlink under ``top`` (file, directory or dangling) without
    following any of them."""
    for dirpath, dirnames, filenames in os.walk(top, followlinks=False):
        for name in [*dirnames, *filenames]:
            path = pathlib.Path(dirpath, name)
            if path.is_symlink():
                yield path


def find_escaping_links(inputs_src: pathlib.Path) -> list[str]:
    """Return every link under ``inputs_src`` whose real target is outside it,
    as sorted POSIX paths relative to ``inputs_src``."""
    root = inputs_src.resolve()
    return sorted(
        link.relative_to(inputs_src).as_posix()
        for link in _links_under(inputs_src)
        if not _is_within(pathlib.Path(os.path.realpath(link)), root)
    )


def _relativize_links(copied: pathlib.Path, inputs_src: pathlib.Path) -> None:
    """Point every absolute link under ``copied`` at the same file inside
    ``copied``, so the run stays self-contained. Callers have already refused
    links that escape ``inputs_src``."""
    root = inputs_src.resolve()
    for link in _links_under(copied):
        if not os.path.isabs(os.readlink(link)):
            continue
        original = inputs_src / link.relative_to(copied)
        mapped = copied / pathlib.Path(os.path.realpath(original)).relative_to(root)
        link.unlink()
        link.symlink_to(os.path.relpath(mapped, link.parent))


def _resolve_pack_taxonomies(
    domains: list[str], domains_dir: pathlib.Path
) -> list[str]:
    """Union the ``taxonomies`` declared by each selected pack's ``domain.yaml``,
    in declared-pack/declared-entry order, deduped. Packs with no ``domain.yaml``
    or no ``taxonomies`` field contribute nothing."""
    seen: dict[str, None] = {}
    for name in domains:
        meta_path = domains_dir / name / "domain.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        for tax in meta.get("taxonomies", []) or []:
            seen.setdefault(tax, None)
    return list(seen)


def scaffold_run(
    run_id: str,
    inputs_src: pathlib.Path,
    domains: list[str],
    root: pathlib.Path,
    taxonomies: list[str] | None = None,
    threat_model: str | None = None,
    methodology_hint: str | None = None,
    domains_dir: pathlib.Path | None = None,
) -> pathlib.Path:
    _validate_run_id(run_id)
    escaping = find_escaping_links(inputs_src)
    if escaping:
        detail = "; ".join(f"{rel} -> {os.readlink(inputs_src / rel)}" for rel in escaping)
        raise UnsafeInputsError(
            f"inputs contain links that point outside the inputs folder: {detail}"
        )
    if domains_dir is None:
        from . import resources as _resources
        domains_dir = _resources.domains_dir()
    run_dir = root / run_id
    for sub in SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    for item in inputs_src.iterdir():
        target = run_dir / "inputs" / item.name
        if item.is_symlink():
            shutil.copy2(item, target, follow_symlinks=False)
        elif item.is_dir():
            shutil.copytree(item, target, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    _relativize_links(run_dir / "inputs", inputs_src)
    # Operator --taxonomies first (order preserved), then pack-declared taxonomies
    # not already present. Dedupe; stable order.
    merged_tax: dict[str, None] = {}
    for t in (taxonomies or []):
        merged_tax.setdefault(t, None)
    for t in _resolve_pack_taxonomies(domains, domains_dir):
        merged_tax.setdefault(t, None)
    effective_taxonomies = list(merged_tax)
    domains_block = "domains:\n" + "".join(f"  - {d}\n" for d in domains)
    config_text = (
        f"run_id: {run_id}\n"
        f"{domains_block}"
        f"framework_version: {FRAMEWORK_VERSION}\n"
        f"code_recon: auto\n"
        "# code_recon: enabled  # hard-fail if CBM not reachable\n"
        "# code_recon: disabled # skip code-recon entirely\n"
        "# cbm_project: <project-name>  # optional CBM project pointer override\n"
        "# infrastructure:           # static IaC intake (declared globs); absent == disabled\n"
        "#   mode: static            # disabled | static | live (live = future release)\n"
        "#   static:                 # globs relative to inputs/; no leading '/' or '..'\n"
        "#     k8s: []\n"
        "#     istio_linkerd: []\n"
        "#     terraform: []\n"
        "#     helm: []\n"
        "#     cert_secret_managers: []\n"
    )
    if effective_taxonomies:
        taxonomies_block = (
            "taxonomies:\n" + "".join(f"  - {t}\n" for t in effective_taxonomies)
        )
        config_text += taxonomies_block
    if threat_model:
        config_text += f"threat_model: {threat_model}\n"
    if methodology_hint:
        config_text += f"methodology_hint: {methodology_hint}\n"
    (run_dir / ".apd-run.yaml").write_text(config_text, encoding="utf-8")
    return run_dir
