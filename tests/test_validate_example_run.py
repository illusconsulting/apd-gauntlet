"""The shipped synthetic example run validates clean and uses the canonical
array coverage shape.

The gauntlet's own output dir (runs/) is gitignored and never shipped, so the
single in-repo run is examples/apd-20260601-claim-event-bus/expected/.
"""
from __future__ import annotations

import pathlib

import yaml as _yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
EXAMPLE = REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"


def test_run_validates_clean() -> None:
    result = CliRunner().invoke(main, ["validate", str(EXAMPLE), "--errors-only"])
    assert result.exit_code == 0, result.output


def test_run_coverage_is_array_shape() -> None:
    """The example's coverage uses the array shape.

    (controls / techniques / components — never the legacy dict shapes.)
    """
    import yaml
    synth = EXAMPLE / "40-synthesis"
    nist = yaml.safe_load((synth / "nist-coverage.yaml").read_text(encoding="utf-8"))
    assert isinstance(nist.get("controls"), list), \
        "nist-coverage must be array-shaped"
    assert "coverage_by_family" not in nist
    attack = yaml.safe_load((synth / "attack-exposure.yaml").read_text(encoding="utf-8"))
    assert isinstance(attack.get("techniques"), list), \
        "attack-exposure must be array-shaped"
    matrix = yaml.safe_load((synth / "apd-coverage-matrix.yaml").read_text(encoding="utf-8"))
    assert isinstance(matrix.get("components"), list), \
        "apd-coverage-matrix must be array-shaped"
    assert "coverage" not in matrix


MOBILE = (
    pathlib.Path(__file__).resolve().parent.parent
    / "examples" / "apd-20260602-acme-mobile-banking" / "expected"
)


def test_mobile_run_config_declares_mas_taxonomies() -> None:
    cfg = _yaml.safe_load((MOBILE / ".apd-run.yaml").read_text(encoding="utf-8"))
    tax = cfg.get("taxonomies") or []
    assert "masvs" in tax, f"masvs must be declared; got {tax}"
    assert "maswe" in tax, f"maswe must be declared; got {tax}"
    # MAS taxonomy support landed in 1.7.0; the example must advertise it.
    assert cfg.get("framework_version") == "1.7.0", cfg.get("framework_version")
