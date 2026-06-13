"""Doc-presence tests for the CC cross-cutting connective-tissue deliverables.

These assert the new docs exist and carry the load-bearing tokens every other
workstream references: the CI-enforceable vs locally-measured split, the
out-of-band local-benchmark instructions, the issue crosswalk, the held-at-1.7.0
version target, and the infra reuse map.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_ci_gate_model_doc_exists_with_two_columns() -> None:
    text = (REPO_ROOT / "docs" / "ci-gate-model.md").read_text()
    assert "CI-enforceable" in text
    assert "Locally measured" in text or "Locally-measured" in text


def test_ci_gate_model_doc_names_the_committed_fixtures() -> None:
    text = (REPO_ROOT / "docs" / "ci-gate-model.md").read_text()
    assert "examples/apd-20260601-claim-event-bus/expected" in text
    assert "examples/apd-20260602-acme-mobile-banking/expected" in text
    assert "tests/fixtures/" in text


def test_ci_gate_model_doc_states_out_of_band_rule() -> None:
    text = (REPO_ROOT / "docs" / "ci-gate-model.md").read_text()
    assert "out-of-band" in text
    assert "never commit" in text.lower()


def test_running_doc_has_local_benchmark_section() -> None:
    text = (REPO_ROOT / "docs" / "running-the-gauntlet.md").read_text()
    assert "Local accuracy benchmark (out-of-band)" in text
    assert "metrics.yaml" in text
    assert "B0" in text


def test_adr_0017_exists_and_records_local_only_decision() -> None:
    text = (REPO_ROOT / "docs" / "adrs" / "0017-local-only-accuracy-benchmark.md").read_text()
    assert "ADR-0017" in text
    assert "Accepted" in text
    assert "out-of-band" in text
    assert "metrics.yaml" in text


def test_ci_gate_model_doc_states_version_held_at_1_7_0() -> None:
    text = (REPO_ROOT / "docs" / "ci-gate-model.md").read_text()
    assert "1.7.0" in text
    assert "held" in text.lower()


def test_ci_gate_model_points_to_issue_crosswalk() -> None:
    text = (REPO_ROOT / "docs" / "ci-gate-model.md").read_text()
    assert "crosswalk" in text.lower()


def test_infra_reuse_map_exists_and_lists_core_modules() -> None:
    text = (REPO_ROOT / "docs" / "infra-reuse-map.md").read_text()
    for module in (
        "validate.py",
        "canonicalize.py",
        "audit.py",
        "metrics.py",
        "kb_fetch.py",
        "test_synthesis_equivalence.py",
    ):
        assert module in text, f"reuse map must mention {module}"


def test_infra_reuse_map_has_do_not_reinvent_column() -> None:
    text = (REPO_ROOT / "docs" / "infra-reuse-map.md").read_text()
    assert "do-not-reinvent" in text.lower() or "Do not reinvent" in text
    # Each row names the workstream that extends the module.
    assert "W0" in text and "W3a" in text and "CC" in text
