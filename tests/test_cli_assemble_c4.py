from __future__ import annotations

import pathlib
import shutil

import yaml
from click.testing import CliRunner

REPO = pathlib.Path(__file__).resolve().parent.parent
REAL_RUN = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"


def _copy_real_run(tmp_path):
    dst = tmp_path / "run"
    for sub in ("00-context", "40-synthesis"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(REAL_RUN / "00-context" / "code-evidence-index.yaml",
                dst / "00-context" / "code-evidence-index.yaml")
    shutil.copy(REAL_RUN / "00-context" / "asset-inventory.yaml",
                dst / "00-context" / "asset-inventory.yaml")
    for f in ("asset-graph.yaml", "deduped-findings.yaml", "deduped-capabilities.yaml"):
        shutil.copy(REAL_RUN / "40-synthesis" / f, dst / "40-synthesis" / f)
    (dst / ".apd-run.yaml").write_text(
        "subject: Home Assistant\nrun_id: apd-test-c4\n", encoding="utf-8"
    )
    return dst


def test_assemble_c4_cli_writes_file_and_echoes_summary(tmp_path):
    from apd_gauntlet.cli import main

    run = _copy_real_run(tmp_path)
    res = CliRunner().invoke(main, ["assemble-c4", str(run)])
    assert res.exit_code == 0, res.output
    out = run / "40-synthesis" / "c4-model.yaml"
    assert out.exists()
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["generated_by"] == "assemble_c4"
    # the echo surfaces the headline counts operators care about
    assert "assemble-c4" in res.output
    assert "23 container" in res.output
    assert "40 code" in res.output
    assert "14 not_analyzed" in res.output


def test_assemble_c4_cli_noop_without_asset_graph(tmp_path):
    from apd_gauntlet.cli import main

    run = tmp_path / "run"
    (run / "40-synthesis").mkdir(parents=True)
    res = CliRunner().invoke(main, ["assemble-c4", str(run)])
    assert res.exit_code == 0, res.output
    assert "no asset-graph.yaml" in res.output
    assert not (run / "40-synthesis" / "c4-model.yaml").exists()
