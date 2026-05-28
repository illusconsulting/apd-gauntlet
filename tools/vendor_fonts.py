# tools/vendor_fonts.py
"""Download Google Fonts .woff2 files into the precompiled bundle.

Contributor-only. Run once after a fresh `npm install` in
report-template/.build/. Idempotent: skips fonts already present.

URLs were resolved on 2026-05-27 via the Google Fonts CSS API with a
Chrome/120 User-Agent. Each URL is the *latin* subset of the family at
the relevant weight.  Newsreader and IBM Plex Sans are variable fonts —
a single woff2 covers the full weight axis so no separate SemiBold /
Medium file is required; the @font-face in styles.css declares a weight
range (e.g. 400 700) backed by this single file.
"""
from __future__ import annotations

import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "tools" / "apd_gauntlet" / "data" / "report-template" / "fonts"

# Google Fonts CSS API URLs used to resolve the woff2 hrefs:
#   Newsreader 400+600: https://fonts.googleapis.com/css2?family=Newsreader:wght@400;600&display=swap
#   IBM Plex Sans 400+500: https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500&display=swap
#   IBM Plex Mono 400: https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&display=swap
# (UA: Mozilla/5.0 ... Chrome/120.0.0.0 Safari/537.36 — required for woff2 vs ttf)
#
# Newsreader v26 and IBM Plex Sans v23 are variable fonts; the latin
# subset binary is the same regardless of which weight you request, so a
# single file covers the full axis range.  IBM Plex Mono v20 is a static
# font (weight 400 only, latin subset).

FONTS: list[tuple[str, str]] = [
    (
        "Newsreader-Regular.woff2",
        "https://fonts.gstatic.com/s/newsreader/v26/cY9VfjOCX1hbuyalUrK49dLac06G1ZGsZBtoBAbNJYQ5ayZC.woff2",
    ),
    (
        "IBMPlexSans-Regular.woff2",
        "https://fonts.gstatic.com/s/ibmplexsans/v23/zYXzKVElMYYaJe8bpLHnCwDKr932-G7dytD-Dmu1syxeKYbSB4Zh.woff2",
    ),
    (
        "IBMPlexMono-Regular.woff2",
        "https://fonts.gstatic.com/s/ibmplexmono/v20/-F63fjptAgt5VM-kVkqdyU8n1i8q131nj-o.woff2",
    ),
]

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in FONTS:
        target = OUT / name
        if target.exists():
            print(f"skip {name} (present)")
            continue
        print(f"fetch {name}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                target.write_bytes(resp.read())
        except Exception as e:
            print(f"  failed: {e}", file=sys.stderr)
            return 1
    print(f"Wrote fonts into {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
