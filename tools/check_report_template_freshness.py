"""CI gate: assert the precompiled bundle is fresh relative to the JSX source.

Computes a sha256 over the report-template/ tree the same way the Node-side
build.mjs does, and compares it to the .source-hash committed alongside the
bundle. Mismatch fails CI with a clear instruction.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "report-template"
BUNDLE = REPO / "tools" / "apd_gauntlet" / "data" / "report-template"
HASH_FILE = BUNDLE / ".source-hash"


def compute_source_hash() -> str:
    h = hashlib.sha256()
    for entry in sorted(SRC.rglob("*")):
        if not entry.is_file():
            continue
        rel = entry.relative_to(SRC)
        # Mirror report-template/.build/build.mjs walk() (line 54): skip any
        # entry whose basename is "node_modules" or starts with "." — at EVERY
        # depth, not just the top level. The old rel.parts[0]-only check diverged
        # from Node on nested dotfiles (e.g. sub/.gitkeep), turning the gate
        # falsely red on a correctly-built bundle.
        if any(part == "node_modules" or part.startswith(".") for part in rel.parts):
            continue
        # Hash the FULL relative path with NUL separator so a rename
        # invalidates the hash even when content is unchanged.
        h.update(str(rel).encode())
        h.update(b"\x00")
        h.update(entry.read_bytes())
    return h.hexdigest()


def main() -> int:
    if not HASH_FILE.exists():
        print(
            "check_report_template_freshness: bundle missing or never built. "
            "Run `python tools/build_report_template.py`.",
            file=sys.stderr,
        )
        return 1
    expected = HASH_FILE.read_text().strip()
    actual = compute_source_hash()
    if expected != actual:
        print(
            "check_report_template_freshness: report-template/ has changed "
            "since the precompiled bundle was generated.\n"
            "Run `python tools/build_report_template.py` and commit the result.",
            file=sys.stderr,
        )
        print(f"  expected={expected}\n  actual  ={actual}", file=sys.stderr)
        return 1
    print(f"check_report_template_freshness: OK ({actual[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
