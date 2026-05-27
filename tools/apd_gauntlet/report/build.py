# tools/apd_gauntlet/report/build.py
"""High-level orchestrator: load -> transform -> emit."""
from __future__ import annotations

import pathlib

import click

from . import emit
from .loader import MissingArtifactError, load_run
from .transform import build_apd_data

_PKG_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
DEFAULT_BUNDLE = _PKG_DATA / "report-template"


def build_report(
    run_dir: pathlib.Path,
    out_dir: pathlib.Path | None = None,
    *,
    bundle_src: pathlib.Path | None = None,
    quiet: bool = False,
) -> pathlib.Path:
    """Run the full HTML report build for a completed gauntlet run.

    Returns the output directory. Raises:
      - MissingArtifactError if a required input YAML is absent
      - BundleMissingError  if the precompiled template bundle is absent
    """
    bundle_src = bundle_src or DEFAULT_BUNDLE
    target = out_dir or (run_dir / "40-synthesis" / "report-html")
    target.mkdir(parents=True, exist_ok=True)

    try:
        artifacts = load_run(run_dir)
    except MissingArtifactError as exc:
        click.echo(f"build-report: cannot build — {exc}", err=True)
        raise

    if artifacts.report_data is None and not quiet:
        click.echo(
            "build-report: report-data.yaml not present; using algorithmic "
            "fallbacks for headline findings, next-steps, exec-summary, posture.",
            err=True,
        )

    data = build_apd_data(artifacts, run_dir=run_dir)

    emit.copy_bundle(bundle_src, target)
    emit.write_data_js(data, target / "data.js")
    emit.write_manifest(
        target / "build-manifest.txt",
        framework_version=artifacts.framework_version,
        source_hashes=artifacts.source_hashes,
        bundle_hash=emit.hash_dir(bundle_src),
    )
    if not quiet:
        click.echo(f"build-report: wrote {target}")
    return target
