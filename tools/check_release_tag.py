"""Release gate: decide whether a pushed ``v*`` tag may publish, and how.

Run by ``.github/workflows/release.yml`` after install and before tests, build
or publish. Two release lines share this repository (see RELEASING.md):

- stable line: ``main`` (plus ``release/X.Y`` maintenance branches once a new
  major has gone GA)
- next line:   ``next`` (pre-releases of the next major)

The gate fails the release unless:

1. The tag is exactly ``v`` + the pyproject version, and that version is in
   canonical PEP 440 form, so the tag, the wheel name and PyPI all agree.
2. ``tools/apd_gauntlet/__init__.py`` carries the same version string, and the
   plugin manifest plus its marketplace entry carry an equivalent version. The
   plugin may use SemVer pre-release spelling (``2.0.0-alpha.1``) because PEP
   440 normalises it to the same version (``2.0.0a1``).
3. The tagged commit is on a branch allowed for that kind of version: stable
   versions only from ``main`` or ``release/*``; pre-releases from ``main``,
   ``next`` or ``release/*``.

It writes ``version``, ``prerelease`` and ``make_latest`` to ``$GITHUB_OUTPUT``
when that variable is set. ``make_latest`` is true only for a stable version at
least as high as every other stable tag, so a 1.x maintenance release cut after
2.0.0 never becomes the repository's "Latest" GitHub release.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import NamedTuple

from packaging.version import InvalidVersion, Version

REPO = Path(__file__).resolve().parent.parent

STABLE_BRANCHES = ("main", "release/*")
PRERELEASE_BRANCHES = ("main", "next", "release/*")


class ReleaseGateError(Exception):
    """The tag must not publish."""


class Decision(NamedTuple):
    version: str
    prerelease: bool
    make_latest: bool


def _parse(label: str, value: str) -> Version:
    try:
        return Version(value)
    except InvalidVersion as exc:
        raise ReleaseGateError(f"{label} {value!r} is not a valid PEP 440 version") from exc


def _allowed(branches: list[str], patterns: tuple[str, ...]) -> list[str]:
    return [b for b in branches if any(fnmatch(b, p) for p in patterns)]


def evaluate(
    tag: str,
    py_version: str,
    init_version: str,
    plugin_versions: dict[str, str],
    branches: list[str],
    existing_tags: list[str],
) -> Decision:
    """Pure decision function; raises ReleaseGateError when the tag must not publish."""
    if not tag.startswith("v"):
        raise ReleaseGateError(f"tag {tag!r} does not start with 'v'")
    version = _parse("pyproject version", py_version)
    if str(version) != py_version:
        raise ReleaseGateError(
            f"pyproject version {py_version!r} is not canonical PEP 440; use {str(version)!r}"
        )
    if tag != f"v{py_version}":
        raise ReleaseGateError(
            f"tag {tag!r} does not match pyproject version {py_version!r}; "
            f"expected tag 'v{py_version}'"
        )
    if init_version != py_version:
        raise ReleaseGateError(
            f"__init__.__version__ {init_version!r} != pyproject version {py_version!r}"
        )
    for label, value in plugin_versions.items():
        if _parse(label, value) != version:
            raise ReleaseGateError(
                f"{label} {value!r} is not the same version as pyproject {py_version!r}"
            )

    prerelease = version.is_prerelease
    patterns = PRERELEASE_BRANCHES if prerelease else STABLE_BRANCHES
    if not _allowed(branches, patterns):
        kind = "pre-release" if prerelease else "stable"
        on = ", ".join(sorted(branches)) or "no branch"
        raise ReleaseGateError(
            f"{kind} tag {tag!r} points at a commit on {on}; "
            f"{kind} tags must be on one of: {', '.join(patterns)}"
        )

    stable_others = []
    for t in existing_tags:
        if t == tag or not t.startswith("v"):
            continue
        try:
            v = Version(t[1:])
        except InvalidVersion:
            continue
        if not v.is_prerelease:
            stable_others.append(v)
    make_latest = not prerelease and all(version >= v for v in stable_others)
    return Decision(py_version, prerelease, make_latest)


def _git(*args: str) -> list[str]:
    out = subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def remote_branches_containing(ref: str, remote: str = "origin") -> list[str]:
    prefix = f"{remote}/"
    names = _git("branch", "-r", "--contains", f"{ref}^{{commit}}", "--format=%(refname:short)")
    return [n[len(prefix):] for n in names if n.startswith(prefix) and n != f"{prefix}HEAD"]


def read_versions(repo: Path = REPO) -> tuple[str, str, dict[str, str]]:
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    py_match = re.search(r'(?m)^version = "([^"]+)"', pyproject)
    init_text = (repo / "tools" / "apd_gauntlet" / "__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'__version__ = "([^"]+)"', init_text)
    if not py_match or not init_match:
        raise ReleaseGateError("could not read the version from pyproject.toml or __init__.py")
    plugin = json.loads((repo / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads(
        (repo / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    entry = next((p for p in market["plugins"] if p["name"] == plugin["name"]), None)
    if entry is None:
        raise ReleaseGateError(f"marketplace.json has no entry for {plugin['name']!r}")
    plugin_versions = {
        "plugin.json version": str(plugin["version"]),
        "marketplace.json entry version": str(entry["version"]),
    }
    return py_match.group(1), init_match.group(1), plugin_versions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", ""))
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args(argv)
    try:
        py_version, init_version, plugin_versions = read_versions()
        decision = evaluate(
            args.tag,
            py_version,
            init_version,
            plugin_versions,
            remote_branches_containing(args.tag, args.remote),
            _git("tag", "--list", "v*"),
        )
    except (ReleaseGateError, subprocess.CalledProcessError) as exc:
        print(f"release gate: {exc}", file=sys.stderr)
        return 1
    lines = [
        f"version={decision.version}",
        f"prerelease={str(decision.prerelease).lower()}",
        f"make_latest={str(decision.make_latest).lower()}",
    ]
    print("release gate: ok — " + ", ".join(lines))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
