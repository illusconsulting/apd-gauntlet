"""Composite commands: run several ``apd-gauntlet`` commands in-process as one step.

``prepare-run``, ``tier-gate``, ``post-tier4`` and ``closeout`` each run a fixed list of
existing commands through :func:`invoke`, in order, whatever an earlier one returned.
After each constituent :func:`run_composite` writes ``<name>: <step> exit=<N>`` to stderr,
and at the end ``<name>: ok`` or ``<name>: failed <step>,<step>``. The runner turns each
non-zero line into one receipt error, so a failure is named by its constituent.
"""
from __future__ import annotations

import contextlib
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import click


@dataclass(frozen=True)
class SubStep:
    """One constituent: its status-line name and the argv after ``apd-gauntlet``."""

    name: str
    argv: tuple[str, ...]
    stdout_to_stderr: bool = False


Invoke = Callable[[Sequence[str]], int]


def _system_exit_code(code: object) -> int:
    """The process exit status Python gives ``SystemExit(code)``."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    click.echo(str(code), err=True)
    return 1


def invoke(argv: Sequence[str]) -> int:
    """Run ``apd-gauntlet <argv>`` in this process; return its standalone exit code.

    A ``SystemExit`` gives its code; a ``ClickException`` is shown, as the standalone
    command shows it, and gives its ``exit_code``; any other exception prints its
    traceback on stderr and gives 1.
    """
    from .cli import main  # lazy: cli registers the composite commands

    try:
        rv = main.main(args=list(argv), prog_name="apd-gauntlet", standalone_mode=False)
    except SystemExit as exc:
        return _system_exit_code(exc.code)
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except Exception:
        traceback.print_exc()
        return 1
    # Without standalone mode click returns ctx.exit(N)'s code; a command returns None.
    return rv if isinstance(rv, int) and not isinstance(rv, bool) else 0


def run_composite(
    name: str,
    steps: Sequence[SubStep],
    *,
    gate: str | None = None,
    invoke: Invoke = invoke,
) -> int:
    """Run every step in order and write one status line per step to stderr.

    Returns the code of the step named ``gate`` when it is set, otherwise the first
    non-zero code, or 0.
    """
    if gate is not None and gate not in {step.name for step in steps}:
        raise ValueError(f"{name}: gate {gate!r} names no step")
    gate_code = 0
    first_failure = 0
    failed: list[str] = []
    for step in steps:
        if step.stdout_to_stderr:
            with contextlib.redirect_stdout(sys.stderr):
                code = invoke(step.argv)
        else:
            code = invoke(step.argv)
        if step.name == gate:
            gate_code = code
        if code != 0:
            failed.append(step.name)
            first_failure = first_failure or code
        click.echo(f"{name}: {step.name} exit={code}", err=True)
    click.echo(f"{name}: failed {','.join(failed)}" if failed else f"{name}: ok", err=True)
    return gate_code if gate is not None else first_failure


def prepare_run_steps(
    run_dir: Path, domains: Sequence[str], framework_version: str | None
) -> list[SubStep]:
    """Scaffold ``validate``, then ``build-domain-skill`` and ``validate-domain``."""
    run = str(run_dir)
    version = ("--framework-version", framework_version) if framework_version is not None else ()
    return [
        SubStep("validate", ("validate", run, "--schema-only", "--errors-only")),
        SubStep("build-domain-skill", ("build-domain-skill", *domains, *version)),
        SubStep("validate-domain", ("validate-domain", *domains)),
    ]


def tier_gate_steps(run_dir: Path, tier: str, *, json_output: bool = False) -> list[SubStep]:
    """Canonicalize the whole run, then validate one tier.

    With ``json_output`` the canonicalize summary goes to stderr, so stdout carries only
    ``validate --json``'s document.
    """
    run = str(run_dir)
    return [
        SubStep("canonicalize", ("canonicalize", run), stdout_to_stderr=json_output),
        SubStep(
            "validate",
            ("validate", run, "--tier", tier, "--json" if json_output else "--errors-only"),
        ),
    ]


def post_tier4_steps(run_dir: Path) -> list[SubStep]:
    """``assemble-c4``, the tmeval ``canonicalize``, then ``rollup``."""
    run = str(run_dir)
    return [
        SubStep("assemble-c4", ("assemble-c4", run)),
        SubStep("canonicalize", ("canonicalize", run)),
        SubStep("rollup", ("rollup", run)),
    ]


def closeout_steps(run_dir: Path, record_attempts: str | None = None) -> list[SubStep]:
    """The dimpr ``canonicalize``, ``summarize``, then the final ``validate``."""
    run = str(run_dir)
    attempts = ("--record-attempts", record_attempts) if record_attempts is not None else ()
    return [
        SubStep("canonicalize", ("canonicalize", run)),
        SubStep("summarize", ("summarize", run, *attempts)),
        SubStep("validate", ("validate", run, "--errors-only")),
    ]
