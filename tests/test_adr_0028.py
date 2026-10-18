"""Structural lint for ADR-0028 (committed calibration and frozen evaluation).

Matches the ADR format of 0020 and 0021 (numbered H1 title, Status/Date
metadata, Context/Decision/Consequences/Alternatives considered), and checks
that the load-bearing decisions are stated: the narrow exception to ADR-0017,
what is committed and what stays local, the GRAML-derived freeze protocol, and
the rejected alternatives. It also checks the cross-references in ADR-0017 and
docs/ci-gate-model.md.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
ADRS = REPO / "docs" / "adrs"
ADR = ADRS / "0028-committed-calibration-and-frozen-evaluation.md"
ADR_0017 = ADRS / "0017-local-only-accuracy-benchmark.md"
CI_GATE_MODEL = REPO / "docs" / "ci-gate-model.md"


def _section(text: str, heading: str) -> str:
    """The body under a ``## `` heading, up to the next ``## `` heading."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"missing section: ## {heading}"
    return match.group(1)


def test_adr_file_exists():
    assert ADR.exists(), f"missing {ADR}"


def test_adr_header_format():
    text = ADR.read_text()
    assert text.startswith("# ADR-0028: "), "ADR must open with '# ADR-0028: <title>'"
    assert re.search(r"^\*\*Status:\*\*\s+Accepted", text, re.MULTILINE)
    assert re.search(r"^\*\*Date:\*\*\s+\d{4}-\d{2}-\d{2}", text, re.MULTILINE)
    assert re.search(
        r"^\*\*Amends:\*\*\s+\[ADR-0017\]\(0017-local-only-accuracy-benchmark\.md\)",
        text,
        re.MULTILINE,
    )


def test_required_sections_present():
    text = ADR.read_text()
    for section in ("## Context", "## Decision", "## Consequences", "## Alternatives considered"):
        assert section in text, f"missing section: {section}"


def test_adr_is_substantively_sized():
    size = ADR.stat().st_size
    assert size >= 3000, f"ADR is only {size} bytes; expected at least 3000"


def test_load_bearing_decisions_stated():
    t = ADR.read_text().lower()
    for s in (
        "adr-0017", "thresholds.yaml", "frozen.yaml", "held-out", "eval/results", "eval/local",
        "graml",
    ):
        assert s in t


def test_what_is_committed():
    decision = _section(ADR.read_text(), "Decision")
    for s in (
        "eval/gates.yaml", "eval/frozen.yaml", "thresholds.yaml", "labels_sha256", "pinned",
        "not even a bare count", "aggregate",
    ):
        assert s in decision, f"Decision does not state {s!r}"
    for field in ("threshold", "precision", "recall", "`n`"):
        assert field in decision


def test_what_stays_local():
    decision = _section(ADR.read_text(), "Decision")
    for s in ("eval/results/", "eval/local/", "usage.yaml", "attempts.yaml", "runs/"):
        assert s in decision, f"Decision does not keep {s!r} local"


def test_protocol_stated():
    decision = _section(ADR.read_text(), "Decision").lower()
    for s in (
        "disjoint", "dev", "eval freeze", "--new-heldout-set", "calibrate", "content",
        "sha-256", "exits 2",
    ):
        assert s in decision, f"protocol does not state {s!r}"


def test_alternatives_rejected():
    alternatives = _section(ADR.read_text(), "Alternatives considered").lower()
    assert "mtime" in alternatives or "modification time" in alternatives
    assert "committing nothing" in alternatives
    assert "per run" in alternatives


def test_freeze_scope_consequence_stated():
    consequences = _section(ADR.read_text(), "Consequences")
    assert "context-params.yaml" in consequences
    assert "--new-heldout-set" in consequences


def test_adr_number_is_unique():
    existing = sorted(p.name[:4] for p in ADRS.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert existing.count("0028") == 1, "exactly one ADR-0028 file must exist"


def test_no_unresolved_placeholders():
    text = ADR.read_text()
    for bad in ("TODO", "TBD", "FIXME", "XXX", "<placeholder>"):
        assert bad not in text, f"unresolved placeholder {bad!r} in ADR"


def test_adr_0017_names_its_amendment():
    lines = ADR_0017.read_text().splitlines()
    metadata = lines[: lines.index("## Context")]
    assert (
        "**Amended by:** [ADR-0028](0028-committed-calibration-and-frozen-evaluation.md)"
        in metadata
    )


def test_ci_gate_model_states_the_exception():
    section = _section(CI_GATE_MODEL.read_text(), "What is measured locally (never committed)")
    assert "[ADR-0028](adrs/0028-committed-calibration-and-frozen-evaluation.md)" in section
    for s in ("thresholds.yaml", "eval/frozen.yaml", "eval/results/", "eval/local/"):
        assert s in section, f"'What is measured locally' does not name {s!r}"
