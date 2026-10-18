"""The freeze protocol for held-out evaluation (ADR-0028).

Tunables (decision thresholds and context parameters) are tuned on the dev set
only, then frozen with ``eval freeze``, which records the SHA-256 of every
tunables file in ``eval/frozen.yaml``. ``eval run --set heldout`` calls
``check_frozen`` first and refuses when any tunables file was added, removed or
changed since the freeze. Freshness is decided by content, never by
modification time: a git checkout resets mtimes, so an mtime rule would refuse
or accept at random.

A re-freeze after a held-out run used the frozen tunables needs a new held-out
set (IaC spec §13.2): ``freeze`` refuses unless ``new_heldout_set`` is given,
and then raises the generation by one. Every problem raises ``FreezeError``
with a message that names the file.

Tunables are found by walking the patterns in ``TUNABLE_GLOBS`` one path part
at a time, and held-out results with ``os.walk``. Unlike ``Path.glob``, both
raise for a directory they cannot list, so an unreadable directory never hides
a tunables file or a held-out result.
"""
from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

TUNABLE_GLOBS: tuple[str, ...] = (
    "tools/apd_gauntlet/data/decide/thresholds.yaml",
    "tools/apd_gauntlet/data/*/context-params.yaml",
)
FROZEN_RELPATH = Path("eval/frozen.yaml")
RESULTS_RELPATH = Path("eval/results")

_HELDOUT_PATTERN = "heldout-*.yaml"
_MAGIC = re.compile(r"[*?[]")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_HEADER = (
    "# Frozen tunables, written by 'apd-gauntlet eval freeze' (ADR-0028). Do not edit.\n"
    "# Held-out 'eval run' refuses when a tunables file differs from this record.\n"
)


class FreezeError(Exception):
    """The tunables are not frozen, changed since the freeze, or cannot be (re)frozen."""


@dataclass(frozen=True)
class Frozen:
    """The content of ``eval/frozen.yaml``."""

    frozen_at: str
    generation: int
    tunables_sha256: str
    files: dict[str, str]


def _reason(exc: OSError) -> str:
    return str(exc.strerror or exc)


def _matches(root: Path, pattern: str) -> list[Path]:
    """The paths under ``root`` that match ``pattern``, in sorted order."""
    found = [root]
    for part in PurePosixPath(pattern).parts:
        step: list[Path] = []
        for base in found:
            if _MAGIC.search(part):
                try:
                    with os.scandir(base) as entries:
                        names = sorted(e.name for e in entries if fnmatch.fnmatchcase(e.name, part))
                except (FileNotFoundError, NotADirectoryError):
                    continue
                except OSError as exc:
                    raise FreezeError(f"{base}: cannot list: {_reason(exc)}") from exc
                step.extend(base / name for name in names)
            else:
                candidate = base / part
                try:
                    candidate.lstat()
                except (FileNotFoundError, NotADirectoryError):
                    continue
                except OSError as exc:
                    raise FreezeError(f"{candidate}: cannot read: {_reason(exc)}") from exc
                step.append(candidate)
        found = step
    return found


def tunables(root: Path) -> dict[str, str]:
    """Every tunables file under ``root``: posix path relative to ``root`` → SHA-256, sorted.

    An empty mapping is valid: the thresholds file and the context parameters
    may not exist yet. A matching path that cannot be read (a directory
    included) raises ``FreezeError``.
    """
    files: dict[str, str] = {}
    for pattern in TUNABLE_GLOBS:
        for path in _matches(root, pattern):
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise FreezeError(f"{path}: cannot read: {_reason(exc)}") from exc
            files[path.relative_to(root).as_posix()] = digest
    return dict(sorted(files.items()))


def tunables_sha256(files: Mapping[str, str]) -> str:
    """SHA-256 over the sorted ``"<path>\\0<sha>\\n"`` lines of ``files``."""
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(f"{path}\0{files[path]}\n".encode())
    return digest.hexdigest()


def _load_yaml(path: Path) -> Any:
    """``path`` parsed as YAML.

    ``FileNotFoundError`` and ``NotADirectoryError`` (no such file) pass
    through; every other failure raises ``FreezeError`` naming the file.
    """
    try:
        raw = path.read_bytes()
    except (FileNotFoundError, NotADirectoryError):
        raise
    except OSError as exc:
        raise FreezeError(f"{path}: cannot read: {_reason(exc)}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FreezeError(f"{path}: not UTF-8 text: {exc}") from exc
    try:
        return yaml.safe_load(text)
    except (yaml.YAMLError, ValueError) as exc:  # ValueError: e.g. an impossible date
        raise FreezeError(f"{path}: invalid YAML: {exc}") from exc
    except RecursionError as exc:
        raise FreezeError(f"{path}: invalid YAML: nested too deeply to parse") from exc


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_frozen(path: Path, doc: Any) -> Frozen:
    def bad(problem: str) -> FreezeError:
        return FreezeError(f"{path}: invalid frozen file: {problem}")

    if not isinstance(doc, dict):
        raise bad(f"not a mapping ({type(doc).__name__})")
    for key in ("schema_version", "frozen_at", "generation", "tunables_sha256", "files"):
        if key not in doc:
            raise bad(f"{key} is missing")
    if not _is_int(doc["schema_version"]) or doc["schema_version"] != 1:
        raise bad(f"schema_version is {doc['schema_version']!r}, not 1")
    frozen_at = doc["frozen_at"]
    if not isinstance(frozen_at, str) or not frozen_at:
        raise bad(f"frozen_at is {frozen_at!r}, not a timestamp")
    generation = doc["generation"]
    if not _is_int(generation) or generation < 1:
        raise bad(f"generation is {generation!r}, not an integer of at least 1")
    sha = doc["tunables_sha256"]
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        raise bad(f"tunables_sha256 is {sha!r}, not a SHA-256")
    files = doc["files"]
    if not isinstance(files, dict):
        raise bad("files is not a mapping of path to SHA-256")
    for name, digest in files.items():
        if not isinstance(name, str) or not name:
            raise bad(f"files has the key {name!r}, not a path")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise bad(f"files[{name!r}] is {digest!r}, not a SHA-256")
    if tunables_sha256(files) != sha:
        raise bad("tunables_sha256 does not match its files")
    return Frozen(frozen_at, generation, sha, dict(sorted(files.items())))


def read_frozen(root: Path) -> Frozen | None:
    """``<root>/eval/frozen.yaml``, or ``None`` when it does not exist.

    A file that cannot be read or parsed, or whose content is invalid (its
    ``tunables_sha256`` must match its own ``files``), raises ``FreezeError``.
    """
    path = root / FROZEN_RELPATH
    try:
        doc = _load_yaml(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    return _parse_frozen(path, doc)


def check_frozen(root: Path) -> str:
    """The frozen tunables hash, when every tunables file still matches the freeze.

    Raises ``FreezeError`` when ``eval/frozen.yaml`` is missing or invalid, and
    when any tunables file was added, removed or changed since the freeze.
    """
    previous = read_frozen(root)
    if previous is None:
        raise FreezeError(
            f"{root / FROZEN_RELPATH} not found — tune on dev, then run 'apd-gauntlet eval freeze'"
        )
    current = tunables(root)
    changes: list[tuple[str, str]] = []
    for path in sorted(set(current) | set(previous.files)):
        if path not in previous.files:
            changes.append((path, "added"))
        elif path not in current:
            changes.append((path, "removed"))
        elif current[path] != previous.files[path]:
            changes.append((path, "changed"))
    if changes:
        raise FreezeError(
            "tunables changed since freeze: "
            + ", ".join(f"{kind} {path}" for path, kind in changes)
        )
    return previous.tunables_sha256


def _walk_error(exc: OSError) -> None:
    raise FreezeError(f"{exc.filename}: cannot list: {_reason(exc)}") from exc


def heldout_uses(results_dir: Path, sha: str) -> list[Path]:
    """The held-out results under ``results_dir`` (``**/heldout-*.yaml``) frozen as ``sha``.

    A result counts when it is a mapping whose ``frozen_sha256`` is ``sha``. A
    missing ``results_dir`` has none. A result that cannot be read or parsed
    raises ``FreezeError``, because it might record ``sha``. Links to
    directories are not followed.
    """
    try:
        results_dir.stat()
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise FreezeError(f"{results_dir}: cannot read: {_reason(exc)}") from exc
    uses: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(results_dir, onerror=_walk_error):
        dirnames.sort()
        for name in sorted(filenames):
            if not fnmatch.fnmatchcase(name, _HELDOUT_PATTERN):
                continue
            path = Path(dirpath) / name
            try:
                doc = _load_yaml(path)
            except (FileNotFoundError, NotADirectoryError):  # removed while walking
                continue
            if isinstance(doc, dict) and doc.get("frozen_sha256") == sha:
                uses.append(path)
    return sorted(uses)


def _write(path: Path, doc: Mapping[str, Any]) -> None:
    text = _HEADER + yaml.safe_dump(dict(doc), sort_keys=False, allow_unicode=True)
    partial = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial.write_text(text, encoding="utf-8")
        partial.replace(path)
    except OSError as exc:
        with contextlib.suppress(OSError):  # e.g. eval is a file
            partial.unlink(missing_ok=True)
        raise FreezeError(f"{path}: cannot write: {_reason(exc)}") from exc


def freeze(root: Path, *, new_heldout_set: bool = False) -> Path:
    """Record the tunables of ``root`` in ``<root>/eval/frozen.yaml``; returns its path.

    Writes nothing when the tunables hash is unchanged. The first freeze is
    generation 1. On a changed hash, a held-out result frozen as the previous
    hash (``heldout_uses``) refuses with ``FreezeError`` unless
    ``new_heldout_set``; with the flag the generation goes up by one, and
    without it the file is rewritten with the same generation.
    """
    path = root / FROZEN_RELPATH
    previous = read_frozen(root)
    files = tunables(root)
    sha = tunables_sha256(files)
    if previous is None:
        generation = 1
    elif previous.tunables_sha256 == sha:
        return path
    else:
        uses = heldout_uses(root / RESULTS_RELPATH, previous.tunables_sha256)
        if uses and not new_heldout_set:
            more = f" and {len(uses) - 1} more" if len(uses) > 1 else ""
            raise FreezeError(
                f"tunables frozen as {previous.tunables_sha256[:8]} were used on held-out data "
                f"({uses[0]}{more}); changing them needs a new held-out set (IaC spec §13.2) "
                "— pass --new-heldout-set once you have one"
            )
        generation = previous.generation + 1 if new_heldout_set else previous.generation
    _write(
        path,
        {
            "schema_version": 1,
            "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generation": generation,
            "tunables_sha256": sha,
            "files": files,
        },
    )
    return path
