"""CLI tests for `apd-gauntlet assemble-inventory`."""
from __future__ import annotations

import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner


def test_assemble_inventory_cli(tmp_path):
    inv = {
        "schema_version": 1, "generated_by": "intake",
        "assets": [{"name": "svc", "asset_type": "service",
                    "provenance": {"source": "artifact", "artifact": "t.md", "locator": "L1"},
                    "confidence": "high"}],
        "identities": [],
        "trust_boundaries": [],
    }
    d = tmp_path / "00-context"
    d.mkdir(parents=True)
    (d / "asset-inventory.yaml").write_text(yaml.safe_dump(inv, sort_keys=False), encoding="utf-8")

    result = CliRunner().invoke(main, ["assemble-inventory", str(tmp_path)])
    assert result.exit_code == 0, result.output
    out = yaml.safe_load((d / "asset-inventory.yaml").read_text())
    assert out["assets"][0]["asset_id"].startswith("asset-")
