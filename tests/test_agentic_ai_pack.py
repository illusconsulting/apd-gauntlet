import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
PACK = REPO / "domains" / "agentic-ai"
GOALS = [
    "confidentiality", "integrity", "availability", "distributed", "resilient",
    "ephemeral", "authenticity", "non-repudiation", "immutability",
]


def test_all_14_files_present():
    assert (PACK / "domain.yaml").is_file()
    for f in ["severity-rubric.md", "consequential-actions.md",
              "immutability-classes.md", "data-taxonomy.md"]:
        assert (PACK / f).is_file(), f
    for g in GOALS:
        assert (PACK / "common-patterns" / f"{g}.md").is_file(), g


def test_includes_list_all_thirteen():
    data = yaml.safe_load((PACK / "domain.yaml").read_text())
    expected = {"severity-rubric.md", "consequential-actions.md",
                "immutability-classes.md", "data-taxonomy.md"} | {
        f"common-patterns/{g}.md" for g in GOALS}
    assert set(data["includes"]) == expected


def test_validate_domain_passes():
    r = subprocess.run(
        [sys.executable, "-m", "apd_gauntlet.cli", "validate-domain", "agentic-ai"],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout


def test_pattern_files_have_sections_and_grounding():
    for g in GOALS:
        text = (PACK / "common-patterns" / f"{g}.md").read_text()
        assert "## Common finding patterns" in text, g
        assert "## Common capability patterns" in text, g
        assert re.search(r"LLM0[1-9]|LLM10", text), f"{g}: no OWASP-LLM grounding"
