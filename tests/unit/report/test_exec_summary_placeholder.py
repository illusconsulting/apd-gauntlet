"""The exec-summary fallback string is a single shared constant."""
from unittest.mock import MagicMock

from apd_gauntlet.report import transform


def test_exec_summary_placeholder_constant_exists():
    assert transform.EXEC_SUMMARY_PLACEHOLDER == "Run summary not provided by synthesizer."


def test_build_apd_data_uses_the_constant_when_supplement_absent():
    # A RunArtifacts-like stub with no report_data supplement and one finding
    # must yield exactly [EXEC_SUMMARY_PLACEHOLDER] for exec_summary.
    arts = MagicMock()
    arts.report_data = None
    arts.deduped_findings = []
    arts.deduped_capabilities = []
    arts.attack_path_findings = []
    arts.threat_model_findings = []
    arts.attack_paths = None
    arts.asset_graph = None
    arts.defense_graph = None
    data = transform.build_apd_data(arts)
    assert data["exec_summary"] == [transform.EXEC_SUMMARY_PLACEHOLDER]
