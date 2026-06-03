"""Tests pinning the C9 operator-doc updates for threat-model authoring."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TM_DOC = REPO_ROOT / "docs" / "threat-modeling.md"
RUN_DOC = REPO_ROOT / "docs" / "running-the-gauntlet.md"


def test_threat_modeling_doc_describes_always_on_author() -> None:
    text = TM_DOC.read_text()
    assert "apd-threat-model-author" in text
    low = text.lower()
    assert "always-on" in low or "always on" in low
    assert "baseline" in low


def test_threat_modeling_doc_lists_authored_artifacts() -> None:
    text = TM_DOC.read_text()
    assert "00-context/threat-model-normalized.yaml" in text
    assert "00-context/threat-model-authored.md" in text
    assert "threat_model_author" in text


def test_threat_modeling_doc_describes_comparator_and_sibling() -> None:
    text = TM_DOC.read_text()
    assert "threat-model-supplied-normalized.yaml" in text
    assert "supplied-vs-authored" in text.lower() or "comparator" in text.lower()


def test_threat_modeling_doc_documents_blocked_placeholder() -> None:
    text = TM_DOC.read_text()
    assert "prerequisite_evidence" in text


def test_running_doc_lists_author_cli_verb() -> None:
    text = RUN_DOC.read_text()
    assert "author-threat-model" in text


def test_running_doc_describes_always_on_baseline() -> None:
    low = RUN_DOC.read_text().lower()
    assert "apd-threat-model-author" in RUN_DOC.read_text()
    assert "always-on" in low or "always on" in low
    assert "baseline" in low


def test_running_doc_links_threat_modeling_guide() -> None:
    assert "threat-modeling.md" in RUN_DOC.read_text()
