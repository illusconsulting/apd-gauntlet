"""All 3 committed runs validate clean after the Plan-3 coverage regeneration."""
from __future__ import annotations

import pathlib

import pytest
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNS = [
    "apd-20260527-crapi-owasp-api-top10",
    "apd-20260527-authentik-identity-provider",
    "apd-20260527-caldera-adversary-emulation",
]


@pytest.mark.parametrize("run_id", RUNS)
def test_run_validates_clean(run_id: str) -> None:
    result = CliRunner().invoke(main, ["validate", str(REPO / "runs" / run_id), "--errors-only"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("run_id", RUNS)
def test_run_coverage_is_array_shape(run_id: str) -> None:
    """Post-regeneration, each run's coverage uses the array shape.

    (controls / techniques / components — never the legacy dict shapes.)
    """
    import yaml
    synth = REPO / "runs" / run_id / "40-synthesis"
    nist = yaml.safe_load((synth / "nist-coverage.yaml").read_text(encoding="utf-8"))
    assert isinstance(nist.get("controls"), list), \
        "nist-coverage must be array-shaped post-rollup"
    assert "coverage_by_family" not in nist
    attack = yaml.safe_load((synth / "attack-exposure.yaml").read_text(encoding="utf-8"))
    assert isinstance(attack.get("techniques"), list), \
        "attack-exposure must be array-shaped post-rollup"
    matrix = yaml.safe_load((synth / "apd-coverage-matrix.yaml").read_text(encoding="utf-8"))
    assert isinstance(matrix.get("components"), list), \
        "apd-coverage-matrix must be array-shaped post-rollup"
    assert "coverage" not in matrix
