"""Tests pinning the v1.4 refresh of the operator and architecture docs (Task C-26).

These tests assert that the five operator/architecture docs and the top-level
README.md have been updated to describe the v1.4 attack-path analyzer, the new
domain-pack fields (`crown_jewels`, `attacker_positions`,
`default_trust_boundaries`), the new run-config block
(`attack_path_analysis`), the new CLI subcommand (`analyze-attack-paths`),
the four new schemas, and the "activation-gated optional agent" pattern.

Paths are resolved relative to the repository root so the tests pass
regardless of the current working directory.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_architecture_doc_documents_attack_path_analyzer() -> None:
    text = (REPO_ROOT / "docs" / "architecture.md").read_text()
    assert "apd-attack-path-analyzer" in text


def test_architecture_doc_shows_agent_count() -> None:
    text = (REPO_ROOT / "docs" / "architecture.md").read_text()
    assert "20 agents" in text or "20-agent" in text


def test_running_doc_documents_new_run_config_fields() -> None:
    text = (REPO_ROOT / "docs" / "running-the-gauntlet.md").read_text()
    for field in ("crown_jewels", "attacker_positions", "attack_path_analysis"):
        assert field in text, f"Expected `{field}` in running-the-gauntlet.md"


def test_running_doc_documents_analyze_attack_paths_cli() -> None:
    text = (REPO_ROOT / "docs" / "running-the-gauntlet.md").read_text()
    assert "analyze-attack-paths" in text


def test_adapting_doc_documents_new_domain_pack_fields() -> None:
    text = (REPO_ROOT / "docs" / "adapting-to-other-domains.md").read_text()
    for field in ("crown_jewels", "attacker_positions", "default_trust_boundaries"):
        assert field in text, f"Expected `{field}` in adapting-to-other-domains.md"


def test_schema_evolution_doc_documents_v14() -> None:
    text = (REPO_ROOT / "docs" / "schema-evolution.md").read_text()
    assert "1.4.0" in text or "v1.4" in text


def test_extending_agents_doc_describes_phase_c_pattern() -> None:
    text = (REPO_ROOT / "docs" / "extending-agents.md").read_text().lower()
    assert "activation-gated" in text or "activation gated" in text
    assert "attack-path-analyzer" in text or "apd-attack-path-analyzer" in text


def test_readme_features_v14() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    assert "1.4" in text or "v1.4" in text
