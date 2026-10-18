"""docs/measuring-changes.md: the operator runbook for before-and-after measurement."""
from __future__ import annotations

import pathlib

from apd_gauntlet.measure.usage import AGENT_PHASES

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_runbook_covers_baseline_capture():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("CLAUDE_CODE_ENABLE_TELEMETRY=1", "OTEL_LOGS_EXPORTER=otlp",
              "OTEL_EXPORTER_OTLP_PROTOCOL=http/json", "OTEL_LOG_TOOL_DETAILS=1", "2.1.273",
              "-baseline-r1", "-baseline-r2", "apd-gauntlet usage"):
        assert s in t


# --- beyond the plan's tests -------------------------------------------------------------


def test_runbook_sections_and_collector():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for heading in ("## Why measure", "## Capture a baseline", "## Telemetry", "## Usage"):
        assert heading in t
    for s in ("OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318", "telemetry/<run-id>.otlp.jsonl",
              "apd-gauntlet validate", "ADR-0017", "--workflow-run"):
        assert s in t


def test_runbook_phase_table_matches_agent_phases():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for agent, phase in AGENT_PHASES.items():
        assert f"| `{agent}` | `{phase}` |" in t, agent


def _flat(text):
    """``text`` with every run of whitespace, line breaks included, as one space."""
    return " ".join(text.split())


def test_runbook_says_every_export_holds_the_account_details():
    t = (REPO / "docs/measuring-changes.md").read_text()
    para = _flat(next((p for p in t.split("\n\n") if "user.email" in p), ""))
    assert para.startswith("Every export holds the account e-mail address (`user.email`)")
    assert para.index("user.email") < para.index("OTEL_LOG_TOOL_DETAILS=1")
    for s in ("organization id", "`user.account_uuid`", "Bash commands", "tool input",
              "never commit it"):
        assert s in para


def test_runbook_guards_exports_from_a_commit():
    t = (REPO / "docs/measuring-changes.md").read_text()
    collector = _flat(t.split("### Collector", 1)[1].split("\n## ", 1)[0])
    assert "git check-ignore telemetry/x.otlp.jsonl" in collector
    assert ".git/info/exclude" in collector


def test_runbook_baseline_set_and_usage_details():
    t = (REPO / "docs/measuring-changes.md").read_text()
    baseline = _flat(t.split("## Capture a baseline", 1)[1].split("\n## ", 1)[0])
    assert "plus one private PBM run." in baseline
    usage = _flat(t.split("\n## Usage", 1)[1])
    assert "Stop the Collector" in usage
    assert "`1`: no `api_request` event is left after filtering, or" in usage
    assert "cannot be written" in usage


def test_runbook_covers_compare_runs():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("compare-runs", "--gates eval/gates.yaml", "pass_with_gaps", "--strict",
              "--excuse", "not_available"):
        assert s in t


def test_runbook_compare_runs_section():
    t = (REPO / "docs/measuring-changes.md").read_text()
    section = _flat(t.split("\n## Compare runs", 1)[1].split("\n## ", 1)[0])
    for s in ("-r1", "-r2", "`apd_goal`", "Jaccard", "0.5", "median", "`EXCUSED (<reason>)`",
              "`delta_only`", "`RESULT:", "1.7", "gate that passed stays `pass`",
              "printed as escapes"):
        assert s in section, s
    for code in ("- `0`:", "- `1`:", "- `2`:"):
        assert code in section, code


def test_running_guide_links_the_runbook():
    t = (REPO / "docs/running-the-gauntlet.md").read_text()
    section = t.split("## Local accuracy benchmark (out-of-band)", 1)[1].split("\n## ", 1)[0]
    assert "(measuring-changes.md)" in section


def test_runbook_covers_attempts():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in (".apd-state/attempts.yaml", "--record-attempts", "plan-run"):
        assert s in t, s


def test_runbook_attempts_section():
    t = (REPO / "docs/measuring-changes.md").read_text()
    section = _flat(t.split("\n## Retries and audit iterations", 1)[1].split("\n## ", 1)[0])
    for key in ("recorded_by", "lens_retries", "first_pass_invalid", "skipped",
                "tier_gate_failures", "tier_repairs", "lens_reruns", "audit_iterations"):
        assert f"| `{key}` |" in section, key
    for s in ("`summarize`", "--record-attempts", "run-attempts.schema.json",
              "one workflow invocation", "`resume-plan`", "`not_available`", "gates 4 and 5",
              "`plan-run`", "records no attempts", "Recorded attempts ->"):
        assert s in section, s
    assert t.index("\n## Retries and audit iterations") < t.index("\n## Compare runs")


def test_runbook_covers_eval():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("eval run", "--set heldout", "eval freeze", "--new-heldout-set", "label-template",
              "eval/local/"):
        assert s in t, s


def test_runbook_eval_section():
    t = (REPO / "docs/measuring-changes.md").read_text()
    section = _flat(t.split("\n## Evaluate against labels", 1)[1].split("\n## ", 1)[0])
    for s in ("eval/<area>/corpus.yaml", "eval/<area>/labels/", "eval/local/", "eval-corpus",
              "eval-labels", "`unreviewed`", "`true_positive`", "`false_positive`",
              "eval/frozen.yaml", "eval/results/<evaluator>/<set>-<timestamp>.yaml",
              "`frozen_sha256`", "`totals`", "ADR-0028", "--results-dir", "--json"):
        assert s in section, s
    for code in ("- `0`:", "- `1`:", "- `2`:"):
        assert code in section, code


def test_runbook_says_telemetry_is_git_ignored_and_why():
    t = (REPO / "docs/measuring-changes.md").read_text()
    para = _flat(next((p for p in t.split("\n\n") if "lists `telemetry/`" in p), ""))
    for s in ("`.gitignore`", "Bash commands", "tool input", "`user.email`", "account ids"):
        assert s in para, s


def test_runbook_covers_calibrate():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("calibrate", "--target-precision 0.98", "--min-support", "calibrated: true",
              "eval freeze"):
        assert s in t, s


def test_runbook_calibrate_section():
    t = (REPO / "docs/measuring-changes.md").read_text()
    section = _flat(t.split("\n## Calibrate a decision threshold", 1)[1].split("\n## ", 1)[0])
    for s in ("eval/local/decide/<key>.labels.yaml", "kind: decisions", "set: dev", "`gold`",
              "40-synthesis/decisions/", "apd-gauntlet calibrate <task> --labels <file> "
              "--target-precision 0.98", "`--min-support`", "10", "midpoint", "recall",
              "`set: heldout`", "mix models", "`provider`", "`model`", "`weights_revision`",
              "`labels_sha256`", "calibrated: true", "calibrated: false", "uncalibrated",
              "`--thresholds`", "apd-gauntlet eval freeze", "ADR-0028",
              "tools/apd_gauntlet/data/decide/thresholds.yaml", "ships as an empty mapping",
              "has no entry there", "(`nan` included)"):
        assert s in section, s
    for code in ("- `0`:", "- `1`:", "- `2`:"):
        assert code in section, code
    assert t.index("\n## Evaluate against labels") < t.index("\n## Calibrate a decision threshold")


def test_runbook_covers_metamorphic():
    t = (REPO / "docs/measuring-changes.md").read_text()
    for s in ("metamorphic run --suite", "register_suite", "known_non_invariant", "stride-table"):
        assert s in t, s


def test_runbook_metamorphic_section():
    t = (REPO / "docs/measuring-changes.md").read_text()
    section = _flat(t.split("\n## Behaviour-preserving transformations", 1)[1].split("\n## ", 1)[0])
    for s in ("apd-gauntlet metamorphic run --suite stride-table", "`--root`", "`--json`",
              "`fixtures`", "`transforms`", "`extract`", "`normalise`", "`known_non_invariant`",
              "`(transform, fixture)`", "rename map", "`register_suite`",
              "`BUILTIN_SUITE_MODULES`", "`holds`", "`violated`", "`allowlisted`",
              "`stale_allowlist`", "with a reason", "`rename-elements`", "`reorder-rows`",
              "`reorder-columns`", "parse-threat-model", "MetamorphicError",
              "differ only in case", "`normalise` returns the wrong type"):
        assert s in section, s
    for code in ("- `0`:", "- `1`:", "- `2`:"):
        assert code in section, code
    assert t.index("\n## Calibrate a decision threshold") < t.index(
        "\n## Behaviour-preserving transformations")
