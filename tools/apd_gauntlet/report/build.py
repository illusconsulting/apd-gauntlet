# tools/apd_gauntlet/report/build.py
"""High-level orchestrator: load -> transform -> emit."""
from __future__ import annotations

import pathlib
from typing import Any

import click

from . import emit
from .loader import MalformedArtifactError, MissingArtifactError, load_run
from .transform import build_apd_data


def _resolve_default_bundle() -> pathlib.Path:
    """Resolve the precompiled report-template bundle path.

    Prefers ``importlib.resources`` so wheel installs (where the package data
    may live in a zip / site-packages layout) work the same as editable
    installs. Falls back to walking up from ``__file__`` to find
    ``tools/apd_gauntlet/data/report-template/`` for the rare editable-install
    case where ``resources.files`` cannot produce a real filesystem path.
    """
    try:
        from importlib import resources

        candidate = resources.files("apd_gauntlet") / "data" / "report-template"
        # ``MultiplexedPath`` (namespace packages) and ``Path`` both expose
        # ``__fspath__``; coerce so callers can use ``pathlib.Path`` semantics.
        return pathlib.Path(str(candidate))
    except (ModuleNotFoundError, AttributeError, TypeError):
        # Editable-install fallback: walk up from this file looking for the
        # in-tree data dir. Stops at the filesystem root.
        here = pathlib.Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "tools" / "apd_gauntlet" / "data" / "report-template"
            if candidate.is_dir():
                return candidate
            sibling = parent / "apd_gauntlet" / "data" / "report-template"
            if sibling.is_dir():
                return sibling
        # Last-resort: the legacy relative path. Surfaces a clean error later
        # in ``copy_bundle`` if the directory truly does not exist.
        return here.parent.parent / "data" / "report-template"


DEFAULT_BUNDLE = _resolve_default_bundle()


class ReportBuildError(RuntimeError):
    """Raised when the report orchestrator cannot assemble the meta layer.

    Per-section failures are isolated by ``build_apd_data`` and recorded in
    ``data.meta.section_errors`` rather than raised. This error type is
    reserved for situations where the meta block itself cannot be assembled
    (a misconfigured run, an invalid ``RunArtifacts``), or another fatal
    orchestrator-level problem prevents the report from being emitted at all.
    """


class BundleFreshnessError(RuntimeError):
    """Raised when the precompiled bundle is stale relative to report-template/.

    Only triggered with --strict on editable installs. Default mode emits a
    stderr warning and proceeds.
    """


def _load_freshness_checker(repo_root: pathlib.Path) -> Any:
    """Return ``compute_source_hash`` from tools/check_report_template_freshness.py.

    Returns ``None`` if the module cannot be loaded (e.g. wheel install with no
    ``tools/`` directory alongside the package). Uses ``importlib.util`` to
    bypass sys.path entirely and avoid polluting it.
    """
    path = repo_root / "tools" / "check_report_template_freshness.py"
    if not path.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_apd_freshness", path,
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "compute_source_hash", None)
    except Exception:  # noqa: BLE001 — never let the gate crash the build
        return None


def build_report(
    run_dir: pathlib.Path,
    out_dir: pathlib.Path | None = None,
    *,
    bundle_src: pathlib.Path | None = None,
    quiet: bool = False,
    strict: bool = False,
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
      - BundleFreshnessError   if ``strict`` and report-template/ source differs
                               from the shipped bundle's .source-hash
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

    # Editable-install freshness gate: when report-template/ ships alongside
    # the package (i.e., user installed via `pip install -e .`), recompute
    # the source hash and compare against the shipped bundle's .source-hash.
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent
    template_src = repo_root / "report-template"
    hash_file = bundle_src / ".source-hash"
    if template_src.is_dir() and hash_file.is_file():
        compute_source_hash = _load_freshness_checker(repo_root)
        if compute_source_hash is not None:
            expected = hash_file.read_text(encoding="utf-8").strip()
            actual = compute_source_hash()
            if expected != actual:
                msg = (
                    "report-template/ source differs from the shipped bundle "
                    "(.source-hash mismatch). Run "
                    "`python tools/build_report_template.py` to refresh."
                )
                if strict:
                    raise BundleFreshnessError(msg)
                import contextlib
                with contextlib.suppress(Exception):
                    click.echo(f"warning: {msg}", err=True)

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
