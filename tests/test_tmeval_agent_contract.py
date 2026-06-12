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
