"""Tests for the init-run command."""
from __future__ import annotations

from apd_gauntlet.cli import main
from click.testing import CliRunner


def test_init_run_creates_expected_directories(tmp_path):
    inputs = tmp_path / "src-inputs"
    inputs.mkdir()
    (inputs / "tech_plan.md").write_text("# stub")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["init-run", "test-001", "--inputs", str(inputs), "--domain", "pbm",
         "--root", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    run_dir = tmp_path / "runs" / "test-001"
    subdirs = (
        "inputs", "00-context", "10-trustworthiness",
        "20-scalability", "30-auditability", "40-synthesis",
    )
    for sub in subdirs:
        assert (run_dir / sub).is_dir()
    assert (run_dir / "inputs" / "tech_plan.md").exists()
    assert (run_dir / ".apd-run.yaml").exists()


def test_scaffold_run_writes_domains_list(tmp_path):
    from apd_gauntlet.init_run import scaffold_run
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "plan.md").write_text("x")
    run_dir = scaffold_run("r1", inputs, ["pbm", "api-security"], tmp_path / "runs")
    cfg = (run_dir / ".apd-run.yaml").read_text()
    assert "domains:\n  - pbm\n  - api-security\n" in cfg
    assert "domain: " not in cfg


def test_resolve_pack_taxonomies_unions_in_stable_order(tmp_path):
    """_resolve_pack_taxonomies reads each pack's domain.yaml taxonomies and unions
    them in declared-pack order, deduping, ignoring packs without the field."""
    from apd_gauntlet.init_run import _resolve_pack_taxonomies

    domains_dir = tmp_path / "domains"
    (domains_dir / "alpha").mkdir(parents=True)
    (domains_dir / "alpha" / "domain.yaml").write_text(
        "name: alpha\ntaxonomies:\n  - masvs\n  - maswe\n"
    )
    (domains_dir / "beta").mkdir(parents=True)
    (domains_dir / "beta" / "domain.yaml").write_text(
        "name: beta\ntaxonomies:\n  - maswe\n  - cwe\n"
    )
    (domains_dir / "gamma").mkdir(parents=True)
    (domains_dir / "gamma" / "domain.yaml").write_text("name: gamma\n")

    out = _resolve_pack_taxonomies(["alpha", "beta", "gamma"], domains_dir)
    assert out == ["masvs", "maswe", "cwe"]


def test_resolve_pack_taxonomies_missing_pack_dir_returns_empty(tmp_path):
    """A selected pack with no domain.yaml contributes nothing (no crash)."""
    from apd_gauntlet.init_run import _resolve_pack_taxonomies

    out = _resolve_pack_taxonomies(["nope"], tmp_path / "domains")
    assert out == []
