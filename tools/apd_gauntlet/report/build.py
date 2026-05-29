# tools/apd_gauntlet/report/build.py
"""High-level orchestrator: load -> transform -> emit."""
from __future__ import annotations

import pathlib
from typing import Any

import click

from . import emit
from .loader import MalformedArtifactError, MissingArtifactError, load_run
from .transform import build_apd_data

_PKG_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
DEFAULT_BUNDLE = _PKG_DATA / "report-template"


class ReportBuildError(RuntimeError):
    """Raised when the report orchestrator cannot assemble the meta layer.

    Per-section failures are isolated by ``build_apd_data`` and recorded in
    ``data.meta.section_errors`` rather than raised. This error type is
    reserved for situations where the meta block itself cannot be assembled
    (a misconfigured run, an invalid ``RunArtifacts``), or another fatal
    orchestrator-level problem prevents the report from being emitted at all.
    """


def build_report(
    run_dir: pathlib.Path,
    out_dir: pathlib.Path | None = None,
    *,
    bundle_src: pathlib.Path | None = None,
    quiet: bool = False,
) -> tuple[pathlib.Path, dict[str, Any]]:
    """Run the full HTML report build for a completed gauntlet run.

    Returns a ``(target_dir, data)`` tuple where ``data`` is the assembled
    ``window.APD_DATA`` dict. Callers can inspect ``data["meta"]["section_errors"]``
    to surface per-section failures (the CLI emits one stderr warning per entry).

    Raises:
      - MissingArtifactError   if a required input YAML is absent
      - MalformedArtifactError if a required input YAML is the wrong shape
      - BundleMissingError     if the precompiled template bundle is absent
      - ReportBuildError       if the meta layer itself cannot be assembled
    """
    bundle_src = bundle_src or DEFAULT_BUNDLE
    target = out_dir or (run_dir / "40-synthesis" / "report-html")
    target.mkdir(parents=True, exist_ok=True)

    try:
        artifacts = load_run(run_dir)
    except (MissingArtifactError, MalformedArtifactError) as exc:
        click.echo(f"build-report: cannot build — {exc}", err=True)
        raise

    if artifacts.report_data is None and not quiet:
        click.echo(
            "build-report: report-data.yaml not present; using algorithmic "
            "fallbacks for headline findings, next-steps, exec-summary, posture.",
            err=True,
        )

    try:
        data = build_apd_data(artifacts, run_dir=run_dir)
    except Exception as exc:  # noqa: BLE001 — meta-layer failures bubble up as ReportBuildError
        raise ReportBuildError(
            f"meta layer could not be assembled: {type(exc).__name__}: {exc}"
        ) from exc

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
    return target, data
