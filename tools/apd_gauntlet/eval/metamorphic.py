"""Metamorphic testing: ``apd-gauntlet metamorphic run --suite NAME``.

A suite names fixtures, behaviour-preserving transformations, an ``extract``
that turns a fixture directory into a set of result tuples, and a ``normalise``
that maps a transformed copy's results back through the transformation's
rename map. ``run_suite`` extracts each untouched fixture once, then for each
transformation writes a transformed copy, extracts and normalises it, and
compares. A case that differs is ``violated`` unless the suite's
``known_non_invariant`` allowlist lists it with a reason (``allowlisted``); an
allowlisted case that holds is ``stale_allowlist``, so the list stays honest
(IaC spec §13.3).

Suites register by name at import with ``register_suite``;
``load_builtin_suites`` imports the modules in ``BUILTIN_SUITE_MODULES``.
"""
from __future__ import annotations

import importlib
import json
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Literal

from ..measure.compare import _printable

RenameMap = dict[str, str]  # transformed name -> original name
ResultSet = frozenset[tuple[str, ...]]
Transform = Callable[[Path, Path], RenameMap]  # (source dir, empty destination dir) -> map
CaseStatus = Literal["holds", "violated", "allowlisted", "stale_allowlist"]

# Statuses that fail ``metamorphic run`` (exit 1), and the order the report counts them in.
FAILING: frozenset[str] = frozenset({"violated", "stale_allowlist"})
STATUS_ORDER: tuple[CaseStatus, ...] = ("holds", "allowlisted", "violated", "stale_allowlist")

NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
# A transform name is a directory under the workdir, so no separators and no dot names.
TRANSFORM_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

BUILTIN_SUITE_MODULES: tuple[str, ...] = ("apd_gauntlet.eval.suites.stride_table",)


class MetamorphicError(Exception):
    """A suite cannot run: a missing fixture, a tool it needs, or a malformed result."""


@dataclass(frozen=True)
class Suite:
    name: str
    fixtures: tuple[str, ...]  # directories relative to the root
    transforms: Mapping[str, Transform]
    extract: Callable[[Path], ResultSet]
    normalise: Callable[[ResultSet, RenameMap], ResultSet]
    # (transform, fixture) -> the reason the case is known not to hold
    known_non_invariant: Mapping[tuple[str, str], str] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseResult:
    fixture: str
    transform: str
    status: CaseStatus
    missing: tuple[tuple[str, ...], ...]  # in the untouched fixture's results only
    extra: tuple[tuple[str, ...], ...]  # in the transformed copy's normalised results only
    reason: str | None  # the allowlist reason (allowlisted, stale_allowlist)


SUITES: dict[str, Suite] = {}


def _fixture_dirs(suite: Suite) -> dict[str, str]:
    """Each fixture's directory name under the workdir; ``ValueError`` when they clash."""
    by_name: dict[str, str] = {}
    for fixture in suite.fixtures:
        name = PurePath(fixture).name
        if name in ("", ".", ".."):
            raise ValueError(f"suite {suite.name!r}: fixture {fixture!r} has no directory name")
        if name in by_name:
            raise ValueError(
                f"suite {suite.name!r}: fixtures {by_name[name]!r} and {fixture!r} share "
                f"the directory name {name!r}"
            )
        by_name[name] = fixture
    for transform in suite.transforms:
        if not TRANSFORM_PATTERN.fullmatch(transform):
            raise ValueError(
                f"suite {suite.name!r}: transform name {transform!r} does not match "
                f"{TRANSFORM_PATTERN.pattern}"
            )
    return {fixture: name for name, fixture in by_name.items()}


def register_suite(suite: Suite) -> None:
    """Register ``suite``; ``ValueError`` for a taken name or a suite that cannot run."""
    if not NAME_PATTERN.fullmatch(suite.name):
        raise ValueError(f"suite name {suite.name!r} does not match {NAME_PATTERN.pattern}")
    if suite.name in SUITES:
        raise ValueError(f"suite {suite.name!r} is already registered")
    for part, what in ((suite.fixtures, "fixtures"), (suite.transforms, "transforms")):
        if not part:
            raise ValueError(f"suite {suite.name!r} has no {what}, so it would hold vacuously")
    _fixture_dirs(suite)
    for key, reason in suite.known_non_invariant.items():
        transform, fixture = key
        if transform not in suite.transforms or fixture not in suite.fixtures:
            raise ValueError(f"suite {suite.name!r}: allowlist key {key!r} names no case")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"suite {suite.name!r}: allowlist key {key!r} needs a reason")
    SUITES[suite.name] = suite


def get_suite(name: str) -> Suite:
    """The suite registered as ``name``; ``KeyError`` lists the registered names."""
    try:
        return SUITES[name]
    except KeyError:
        registered = ", ".join(sorted(SUITES)) or "none"
        raise KeyError(f"unknown suite {name!r}; registered: {registered}") from None


def load_builtin_suites() -> None:
    """Import the built-in suite modules; a second call changes nothing."""
    for module in BUILTIN_SUITE_MODULES:
        importlib.import_module(module)


@contextmanager
def _case(suite: Suite, fixture: str, transform: str | None) -> Iterator[None]:
    """Turn a failed read or write into ``MetamorphicError`` naming the case."""
    try:
        yield
    except (OSError, UnicodeDecodeError) as exc:
        where = f"suite {suite.name!r}, fixture {fixture}" + (
            f", transform {transform}" if transform else ""
        )
        raise MetamorphicError(f"{where}: {exc}") from exc


def _result_set(value: object, what: str) -> ResultSet:
    if isinstance(value, (set, frozenset)):
        rows = frozenset(value)
        if all(isinstance(t, tuple) and all(isinstance(x, str) for x in t) for t in rows):
            return rows
    raise MetamorphicError(f"{what} must return a set of tuples of strings")


def _rename_map(value: object, what: str) -> RenameMap:
    if isinstance(value, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        return dict(value)
    raise MetamorphicError(f"{what} must return a rename map of strings to strings")


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:  # Python 3.12 re-raises PermissionError from the stat call
        return False


def _empty_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise MetamorphicError(f"{path}: not empty; run_suite needs an empty workdir")
    return path


def run_suite(suite: Suite, root: Path, workdir: Path) -> list[CaseResult]:
    """Run every (fixture, transform) case of ``suite``: fixtures in order, transforms by name.

    Each transformed copy goes to ``workdir/<fixture name>/<transform>/``.
    ``MetamorphicError`` when a fixture is not a directory under ``root``
    (checked before any case runs), a workdir directory is not empty, a
    transform, ``extract`` or ``normalise`` returns the wrong type, or reading
    or writing a file fails.
    """
    dirs = _fixture_dirs(suite)
    absent = [f for f in suite.fixtures if not _is_dir(root / f)]
    if absent:
        raise MetamorphicError(
            f"suite {suite.name!r}: no fixture directory {', '.join(absent)} under {root}"
        )
    cases: list[CaseResult] = []
    for fixture in suite.fixtures:
        source = root / fixture
        with _case(suite, fixture, None):
            expected = _result_set(suite.extract(source), f"suite {suite.name!r}: extract")
        for name in sorted(suite.transforms):
            what = f"suite {suite.name!r}, transform {name}"
            with _case(suite, fixture, name):
                copy = _empty_dir(workdir / dirs[fixture] / name)
                rename = _rename_map(suite.transforms[name](source, copy), what)
                got = _result_set(suite.extract(copy), f"suite {suite.name!r}: extract")
            got = _result_set(suite.normalise(got, rename), f"suite {suite.name!r}: normalise")
            lost = tuple(sorted(expected - got))
            gained = tuple(sorted(got - expected))
            reason = suite.known_non_invariant.get((name, fixture))
            status: CaseStatus
            if lost or gained:
                status = "violated" if reason is None else "allowlisted"
            else:
                status = "holds" if reason is None else "stale_allowlist"
            cases.append(CaseResult(fixture, name, status, lost, gained, reason))
    return cases


def render_text(suite: Suite, cases: Sequence[CaseResult]) -> str:
    """The text report: one line per case, what differs, and a ``RESULT:`` line.

    Control characters in each line are printed as escapes, so a result tuple
    from a fixture cannot forge a report line or reach the terminal.
    """
    lines = [
        f"suite {suite.name}: {_count(len(suite.fixtures), 'fixture')}, "
        f"{_count(len(suite.transforms), 'transform')}, {_count(len(cases), 'case')}"
    ]
    for c in cases:
        line = f"{c.status}: {c.transform} on {c.fixture}"
        if c.reason is not None:
            line += f" ({c.reason})"
        if c.status == "stale_allowlist":
            line += ": the case holds; remove its allowlist entry"
        lines.append(line)
        for label, rows in (("missing", c.missing), ("extra", c.extra)):
            lines.extend(f"  {label}: {json.dumps(list(t), ensure_ascii=False)}" for t in rows)
    counts = [
        f"{n} {status}"
        for status in STATUS_ORDER
        if (n := sum(1 for c in cases if c.status == status))
    ]
    result = "fail" if any(c.status in FAILING for c in cases) else "pass"
    lines.append(f"RESULT: {result} ({', '.join(counts) or 'no cases'})")
    return "\n".join(_printable(line) for line in lines)


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}{'' if n == 1 else 's'}"
