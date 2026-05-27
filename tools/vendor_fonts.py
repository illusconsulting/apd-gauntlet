# tools/vendor_fonts.py
"""Download Google Fonts .woff2 files into the precompiled bundle.

Contributor-only. Run once after a fresh `npm install` in
report-template/.build/. Idempotent: skips fonts already present.
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "tools" / "apd_gauntlet" / "data" / "report-template" / "fonts"

# Curated subset matching the template's typePairing 'editorial' default.
# Format: (filename, URL). Replace URLs by visiting fonts.google.com, selecting
# the family + weight, then copying the woff2 URL from the resulting css.
FONTS: list[tuple[str, str]] = [
    # NOTE: these are placeholders. Replace with real Google Fonts woff2 URLs
    # the first time you run this; commit the resulting fonts/*.woff2 files
    # and this list becomes the canonical record.
    ("Newsreader-Regular.woff2", "https://fonts.gstatic.com/.../newsreader.woff2"),
    ("IBMPlexSans-Regular.woff2", "https://fonts.gstatic.com/.../plexsans.woff2"),
    ("IBMPlexMono-Regular.woff2", "https://fonts.gstatic.com/.../plexmono.woff2"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in FONTS:
        target = OUT / name
        if target.exists():
            print(f"skip {name} (present)")
            continue
        print(f"fetch {name}")
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                target.write_bytes(resp.read())
        except Exception as e:
            print(f"  failed: {e}", file=sys.stderr)
            return 1
    print(f"Wrote fonts into {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
