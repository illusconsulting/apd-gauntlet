"""Scaffold a runs/<run-id>/ directory."""
from __future__ import annotations

import pathlib
import re
import shutil

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


def scaffold_run(
    run_id: str,
    inputs_src: pathlib.Path,
    domain: str,
    root: pathlib.Path,
    taxonomies: list[str] | None = None,
    threat_model: str | None = None,
    methodology_hint: str | None = None,
) -> pathlib.Path:
    _validate_run_id(run_id)
    run_dir = root / run_id
    for sub in SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    for item in inputs_src.iterdir():
        target = run_dir / "inputs" / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    config_text = (
        f"run_id: {run_id}\n"
        f"domain: {domain}\n"
        f"framework_version: 1.1.0\n"
        f"code_recon: auto\n"
        "# code_recon: enabled  # hard-fail if CBM not reachable\n"
        "# code_recon: disabled # skip code-recon entirely\n"
        "# cbm_project: <project-name>  # optional CBM project pointer override\n"
    )
    if taxonomies:
        taxonomies_block = "taxonomies:\n" + "".join(f"  - {t}\n" for t in taxonomies)
        config_text += taxonomies_block
    if threat_model:
        config_text += f"threat_model: {threat_model}\n"
    if methodology_hint:
        config_text += f"methodology_hint: {methodology_hint}\n"
    (run_dir / ".apd-run.yaml").write_text(config_text, encoding="utf-8")
    return run_dir
