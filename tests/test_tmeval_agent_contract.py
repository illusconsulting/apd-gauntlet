import pathlib

AGENT = (
    pathlib.Path(__file__).resolve().parent.parent
    / ".claude" / "agents" / "apd-threat-model-evaluator.md"
)


def test_evaluator_does_not_hand_compute_sha():
    text = AGENT.read_text(encoding="utf-8")
    assert "sha over" not in text, "evaluator must NOT instruct hand-computing the tmeval sha"


def test_evaluator_emits_tmeval_key():
    text = AGENT.read_text(encoding="utf-8")
    assert "tmeval_key" in text


def test_evaluator_reads_the_deduped_corpus():
    text = AGENT.read_text(encoding="utf-8")
    assert "20-findings" not in text and "10-capabilities" not in text
    assert "40-synthesis/deduped-findings.yaml" in text
    assert "40-synthesis/deduped-capabilities.yaml" in text


def test_evaluator_writes_one_canonical_findings_file():
    text = AGENT.read_text(encoding="utf-8")
    assert "40-threat-model/threat-model.findings.yaml" in text
    assert "one file per finding" not in text and "tmeval-<sha8>.yaml" not in text


def test_canonical_dir_is_what_the_validator_accepts():
    from apd_gauntlet.validate import CANONICAL_RECORD_DIRS

    assert "40-threat-model" in CANONICAL_RECORD_DIRS


def test_threat_modeling_doc_names_the_canonical_path():
    doc = (AGENT.parents[2] / "docs" / "threat-modeling.md").read_text(encoding="utf-8")
    assert "40-threat-model/threat-model.findings.yaml" in doc and "20-findings/" not in doc
