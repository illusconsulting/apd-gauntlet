"""Scaffold a runs/<run-id>/ directory."""
from __future__ import annotations
import pathlib
import shutil

SUBDIRS = ["inputs", "00-context", "10-trustworthiness", "20-scalability", "30-auditability", "40-synthesis"]


def scaffold_run(run_id: str, inputs_src: pathlib.Path, domain: str, root: pathlib.Path) -> pathlib.Path:
    run_dir = root / run_id
    for sub in SUBDIRS:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    for item in inputs_src.iterdir():
        target = run_dir / "inputs" / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    (run_dir / ".apd-run.yaml").write_text(
        f"run_id: {run_id}\ndomain: {domain}\nframework_version: 1.0.0\n"
    )
    return run_dir
