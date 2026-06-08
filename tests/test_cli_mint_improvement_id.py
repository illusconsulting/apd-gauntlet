# tests/test_cli_mint_improvement_id.py
"""FW-5: `apd-gauntlet mint-improvement-id` lets the execution-light
apd-domain-auditor mint a canonical dimpr- id that matches the validator's
recompute, instead of blocking because it cannot hand-roll sha256."""
from __future__ import annotations

from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_improvement_id
from click.testing import CliRunner


def test_mint_improvement_id_matches_canonical_function() -> None:
    args = [
        "mint-improvement-id",
        "--type", "missing_crown_jewel",
        "--target-pack", "agentic-ai",
        "--target-file", "common-patterns.md",
        "--ref", "asset-3f9a1c07",
    ]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    expected = compute_improvement_id(
        "missing_crown_jewel", "agentic-ai", "common-patterns.md", "asset-3f9a1c07"
    )
    assert result.output.strip() == expected
    assert result.output.strip().startswith("dimpr-")


def test_mint_improvement_id_is_case_insensitive_on_key() -> None:
    """The canonical key is lowercased, so case variants collide to one id."""
    lower = CliRunner().invoke(main, [
        "mint-improvement-id", "--type", "missing_common_pattern",
        "--target-pack", "api-security", "--target-file", "RUBRIC.md", "--ref", "Conf-1",
    ])
    upper = CliRunner().invoke(main, [
        "mint-improvement-id", "--type", "missing_common_pattern",
        "--target-pack", "api-security", "--target-file", "rubric.md", "--ref", "conf-1",
    ])
    assert lower.output.strip() == upper.output.strip()
