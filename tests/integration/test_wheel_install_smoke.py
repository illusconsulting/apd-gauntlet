"""Build the wheel, install it into a clean venv with NO repo on sys.path, and
run the CLI. This is the regression test for the import-time FileNotFoundError
(schemas/domain.schema.json) that shipped in 1.7.0.

This suite pins TWO distinct wheel-packaging failures, both red at A0:
  (a) the schema-path import crash — build_domain_skill.py loads
      schemas/domain.schema.json via a __file__-relative repo path that does
      not exist inside an installed wheel (crashes ALL three tests at import);
  (b) the bundled domains/pbm pack being absent from the wheel — even once
      (a) is fixed, validate-domain pbm has no pack to validate.
The suite goes fully green only once BOTH are resolved (the schema-load fix
plus domains being bundled/defaulted) — see tasks A1-A4."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.wheel

_HAVE_UV = shutil.which("uv") is not None
_SKIP = os.environ.get("APD_SKIP_WHEEL_TESTS") == "1"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300)


@pytest.fixture(scope="session")
def venv_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if _SKIP or not _HAVE_UV:
        pytest.skip("needs uv and APD_SKIP_WHEEL_TESTS unset")
    dist = tmp_path_factory.mktemp("dist")
    venv = tmp_path_factory.mktemp("venv")
    build = _run(["uv", "build", "--wheel", "--out-dir", str(dist), str(REPO)], cwd=REPO)
    assert build.returncode == 0, build.stderr
    whl = next(dist.glob("*.whl"))
    assert _run(["uv", "venv", str(venv)], cwd=dist).returncode == 0
    py = venv / "bin" / "python"
    inst = _run(["uv", "pip", "install", "--python", str(py), str(whl)], cwd=dist)
    assert inst.returncode == 0, inst.stderr
    return venv / "bin"


def test_help_runs_without_import_error(venv_bin: Path, tmp_path: Path) -> None:
    r = _run([str(venv_bin / "apd-gauntlet"), "--help"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Traceback" not in r.stderr and "FileNotFoundError" not in r.stderr
    assert "Usage:" in r.stdout


def test_version_runs(venv_bin: Path, tmp_path: Path) -> None:
    r = _run([str(venv_bin / "apd-gauntlet"), "--version"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert re.search(r"\d+\.\d+\.\d+", r.stdout)


def test_validate_domain_pbm(venv_bin: Path, tmp_path: Path) -> None:
    # Pins BOTH wheel failures: at A0 this fails at import via the schema-path
    # crash (failure (a)); once that is fixed it will STILL fail because the
    # domains/pbm pack is not bundled into the wheel (failure (b)). Goes green
    # only when the schema-load fix AND domain bundling/defaulting both land
    # (tasks A1-A4).
    r = _run([str(venv_bin / "apd-gauntlet"), "validate-domain", "pbm"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
