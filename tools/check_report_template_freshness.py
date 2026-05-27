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
        if rel.parts and rel.parts[0] in {".build", "node_modules"}:
            continue
        if rel.parts and rel.parts[0].startswith("."):
            continue
        h.update(rel.name.encode())
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
