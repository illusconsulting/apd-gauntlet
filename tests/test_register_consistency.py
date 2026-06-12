"""The deterministic-field register must list every compute_*_id helper."""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
LINTERS = REPO / "tools" / "apd_gauntlet" / "linters.py"
REGISTER = REPO / "docs" / "deterministic-field-register.md"


def test_register_mentions_every_id_helper():
    helpers = set(re.findall(r"def (compute_\w*id)\(", LINTERS.read_text(encoding="utf-8")))
    assert helpers, "expected to find compute_*_id helpers in linters.py"
    reg = REGISTER.read_text(encoding="utf-8")
    missing = sorted(h for h in helpers if h not in reg)
    assert missing == [], f"deterministic-field register omits id helpers: {missing}"
