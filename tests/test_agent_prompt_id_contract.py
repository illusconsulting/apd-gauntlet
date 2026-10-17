import pathlib
import re

AGENTS_DIR = pathlib.Path(__file__).resolve().parent.parent / ".claude" / "agents"
LENS_AGENTS = [
    "apd-confidentiality.md", "apd-integrity.md", "apd-availability.md",
    "apd-distributed.md", "apd-resilient.md", "apd-ephemeral.md",
    "apd-authenticity.md", "apd-non-repudiation.md", "apd-immutability.md",
]


def test_lens_agents_do_not_instruct_best_effort_id():
    offenders = []
    for name in LENS_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8").lower()
        if "best-effort `id`" in text or "best-effort id" in text:
            offenders.append(name)
    assert offenders == [], f"these agents still tell the model to author an id: {offenders}"


def test_lens_agents_state_assembler_owns_id():
    missing = []
    for name in LENS_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8")
        if "do NOT emit" not in text or "id" not in text:
            missing.append(name)
    assert missing == [], f"these agents lack the do-not-emit-id contract line: {missing}"


def test_lens_self_checks_never_ask_for_an_id():
    offenders = []
    for name in LENS_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8")
        section = text.split("## Self-check", 1)[1].split("\n## ", 1)[0]
        if re.search(r"(?i)\bID\b[^\n]*(computed|deterministic)", section):
            offenders.append(name)
    assert offenders == [], f"self-check asks the lens to author an id: {offenders}"


CONTEXT_AGENTS = [
    "apd-code-recon.md", "apd-threat-model-author.md", "apd-threat-model-recon.md",
]


def test_context_agents_leave_ids_to_canonicalize():
    for name in CONTEXT_AGENTS:
        text = (AGENTS_DIR / name).read_text(encoding="utf-8")
        assert re.search(r"cev-<sha8>|tm-<sha8>|sha8\(|sha256\(", text) is None, name
        assert "apd-gauntlet canonicalize" in text, name
