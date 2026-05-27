# tools/build_report_template.py
"""Contributor entry point: rebuild the precompiled HTML report bundle.

Wraps the Node-side esbuild pipeline. Skips with a clear message when Node /
npm are not available — runtime users don't need either.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
BUILD_DIR = HERE.parent / "report-template" / ".build"


def main() -> int:
    if shutil.which("node") is None or shutil.which("npm") is None:
        print(
            "build-report-template: node + npm are required. "
            "Install Node 20+ and try again.",
            file=sys.stderr,
        )
        return 2
    if not (BUILD_DIR / "node_modules").exists():
        if (BUILD_DIR / "package-lock.json").exists():
            subprocess.run(["npm", "ci"], cwd=BUILD_DIR, check=True)
        else:
            subprocess.run(["npm", "install"], cwd=BUILD_DIR, check=True)
    subprocess.run(["node", "build.mjs"], cwd=BUILD_DIR, check=True)
    print("build-report-template: bundle written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
