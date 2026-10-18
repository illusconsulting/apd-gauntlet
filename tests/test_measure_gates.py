"""measure.gates: the ``eval/gates.yaml`` proposal gates, their loader and their evaluation."""
from __future__ import annotations

import pathlib
import re

import pytest
from apd_gauntlet.measure.gates import (
    METRICS,
    Check,
    Gate,
    GateOutcome,
    GatesError,
    evaluate,
    load_gates,
    overall,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
GATES = REPO / "eval/gates.yaml"


def test_gate_texts_match_master_plan_verbatim():
    plan = (REPO / "docs/superpowers/plans/2026-10-10-program-master-plan.md").read_text()
    marker = "These comparison gates are proposals, recorded in `eval/gates.yaml`:"
    block = plan.split(marker)[1].split("- **Ids")[0]
    bullets = [b.strip().rstrip(";.") for b in re.findall(r"^  - (.+)$", block, re.MULTILINE)]
    assert [g.text for g in load_gates(REPO / "eval/gates.yaml")] == bullets


def test_evaluate_statuses():
    gates = load_gates(REPO / "eval/gates.yaml")
    vals = {
        "unexcused_lost_critical_high": 0,
        "severity_agreement_pct": 89.9,
        "blocked_rate_abs_delta_pts": 5.0,
        "first_pass_validator_errors_delta": None,
        "lens_retries_delta": None,
        "tier_repairs_delta": None,
        "lens_reruns_delta": None,
        "audit_iterations_delta": None,
    }
    out = evaluate(gates, vals, {"audit_iterations_delta": "no attempts file"})
    assert [o.status for o in out] == ["pass", "fail", "pass", "not_available", "not_available"]
    assert out[4].reason == "no attempts file" and overall(out) == "fail"
    assert overall([o for o in out if o.status != "fail"]) == "pass_with_gaps"


def test_unknown_metric_rejected(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text(
        "schema_version: 1\n"
        "gates: [{id: x, text: x, checks: [{metric: nope, op: le, value: 0}]}]\n"
    )
    with pytest.raises(GatesError, match="nope"):
        load_gates(p)


# --- the committed gates file ------------------------------------------------------------


def test_metrics_are_the_eight_planned_values():
    planned = {
        "unexcused_lost_critical_high",
        "severity_agreement_pct",
        "blocked_rate_abs_delta_pts",
        "first_pass_validator_errors_delta",
        "lens_retries_delta",
        "tier_repairs_delta",
        "lens_reruns_delta",
        "audit_iterations_delta",
    }
    assert isinstance(METRICS, frozenset) and planned == METRICS


def test_gates_file_ids_and_checks():
    gates = load_gates(GATES)
    assert all(isinstance(g, Gate) and isinstance(c, Check) for g in gates for c in g.checks)
    assert [(g.id, c.metric, c.op, c.value) for g in gates for c in g.checks] == [
        ("no_lost_critical_high", "unexcused_lost_critical_high", "le", 0),
        ("severity_agreement", "severity_agreement_pct", "ge", 90),
        ("blocked_rate", "blocked_rate_abs_delta_pts", "le", 5),
        ("first_pass_and_retries", "first_pass_validator_errors_delta", "le", 0),
        ("first_pass_and_retries", "lens_retries_delta", "le", 0),
        ("first_pass_and_retries", "tier_repairs_delta", "le", 0),
        ("first_pass_and_retries", "lens_reruns_delta", "le", 0),
        ("audit_iterations", "audit_iterations_delta", "le", 0),
    ]
    assert all(type(c.value) is float for g in gates for c in g.checks)
    assert isinstance(gates, tuple) and all(isinstance(g.checks, tuple) for g in gates)


def test_every_metric_is_checked_by_the_gates_file():
    assert {c.metric for g in load_gates(GATES) for c in g.checks} == METRICS


def test_gates_file_is_a_proposal_that_changes_only_by_pr():
    text = GATES.read_text(encoding="utf-8")
    assert "status: proposal" in text
    assert "Change a threshold only by PR, with the rationale in the PR description." in text


# --- evaluate and overall --------------------------------------------------------------


def _gate(*checks: tuple[str, str, float], gate_id: str = "g") -> Gate:
    return Gate(
        id=gate_id,
        text=gate_id,
        checks=tuple(Check(metric=m, op=op, value=v) for m, op, v in checks),
    )


@pytest.mark.parametrize(
    ("op", "bound", "value", "status"),
    [
        ("le", 0, 0, "pass"),
        ("le", 0, -1, "pass"),
        ("le", 0, 0.001, "fail"),
        ("ge", 90, 90, "pass"),
        ("ge", 90, 100, "pass"),
        ("ge", 90, 89.999, "fail"),
    ],
)
def test_check_bounds_are_inclusive(op, bound, value, status):
    (out,) = evaluate([_gate(("lens_retries_delta", op, bound))], {"lens_retries_delta": value}, {})
    assert out.status == status and out.reason is None


def test_a_failing_check_wins_over_a_missing_value():
    gate = _gate(("lens_retries_delta", "le", 0), ("tier_repairs_delta", "le", 0))
    (out,) = evaluate([gate], {"lens_retries_delta": None, "tier_repairs_delta": 1}, {
        "lens_retries_delta": "no attempts file",
    })
    assert out.status == "fail" and out.reason is None


def test_not_available_lists_each_distinct_reason_in_check_order():
    gate = _gate(
        ("lens_retries_delta", "le", 0),
        ("tier_repairs_delta", "le", 0),
        ("lens_reruns_delta", "le", 0),
        ("audit_iterations_delta", "le", 0),
    )
    values = {
        "lens_retries_delta": None,
        "tier_repairs_delta": 0,
        "lens_reruns_delta": None,
        "audit_iterations_delta": None,
    }
    reasons = {
        "lens_retries_delta": "b resumed",
        "lens_reruns_delta": "no attempts file",
        "audit_iterations_delta": "b resumed",
    }
    (out,) = evaluate([gate], values, reasons)
    assert out.status == "not_available"
    assert out.reason == "b resumed; no attempts file"


def test_not_available_without_a_reason_names_the_metric():
    (out,) = evaluate([_gate(("lens_retries_delta", "le", 0))], {"lens_retries_delta": None}, {})
    assert out.status == "not_available" and out.reason == "no value for lens_retries_delta"


def test_a_metric_absent_from_values_is_not_available():
    (out,) = evaluate([_gate(("lens_retries_delta", "le", 0))], {}, {"lens_retries_delta": "x"})
    assert out.status == "not_available" and out.reason == "x"
    assert out.values == {"lens_retries_delta": None}


@pytest.mark.parametrize("op", ["le", "ge"])
def test_a_nan_value_fails(op):
    gate = _gate(("lens_retries_delta", op, 0))
    (out,) = evaluate([gate], {"lens_retries_delta": float("nan")}, {})
    assert out.status == "fail"


def test_outcome_carries_its_gate_and_only_its_own_values():
    gates = load_gates(GATES)
    values = dict.fromkeys(METRICS, 0) | {"severity_agreement_pct": 100.0}
    out = evaluate(gates, values, {})
    assert all(isinstance(o, GateOutcome) for o in out)
    assert [o.gate for o in out] == list(gates)
    assert [o.status for o in out] == ["pass"] * 5 and overall(out) == "pass"
    assert out[1].values == {"severity_agreement_pct": 100.0}
    assert list(out[3].values) == [
        "first_pass_validator_errors_delta",
        "lens_retries_delta",
        "tier_repairs_delta",
        "lens_reruns_delta",
    ]
    assert all(o.reason is None for o in out)


def test_evaluate_keeps_the_gate_order():
    gates = [_gate(("lens_retries_delta", "le", 0), gate_id=i) for i in ("z", "a", "m")]
    out = evaluate(gates, {"lens_retries_delta": 0}, {})
    assert [o.gate.id for o in out] == ["z", "a", "m"]


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (["pass", "pass"], "pass"),
        (["pass", "not_available"], "pass_with_gaps"),
        (["not_available", "fail", "pass"], "fail"),
        (["fail"], "fail"),
    ],
)
def test_overall(statuses, expected):
    gate = _gate(("lens_retries_delta", "le", 0))
    outcomes = [GateOutcome(gate=gate, status=s, values={}, reason=None) for s in statuses]
    assert overall(outcomes) == expected


# --- load_gates refusals -----------------------------------------------------------------

CHECK = "{metric: lens_retries_delta, op: le, value: 0}"


def _one(gate: str) -> str:
    return f"schema_version: 1\ngates: [{gate}]\n"


@pytest.mark.parametrize(
    ("body", "problem"),
    [
        (_one("{id: x, text: x, checks: [{metric: lens_retries_delta, op: lt, value: 0}]}"),
         "gates[0].checks[0]: unknown op 'lt'"),
        (_one("{id: x, text: x, checks: [{metric: 5, op: le, value: 0}]}"),
         "gates[0].checks[0]: unknown metric 5"),
        (f"schema_version: 1\ngates: [{{id: x, text: a, checks: [{CHECK}]}}, "
         f"{{id: x, text: b, checks: [{CHECK}]}}]\n",
         "gates[1]: duplicate id 'x'"),
        (_one(f"{{text: x, checks: [{CHECK}]}}"), "gates[0]: missing key 'id'"),
        (_one(f"{{id: x, checks: [{CHECK}]}}"), "gates[0]: missing key 'text'"),
        (_one("{id: x, text: x}"), "gates[0]: missing key 'checks'"),
        (_one("{id: x, text: x, checks: [{op: le, value: 0}]}"),
         "gates[0].checks[0]: missing key 'metric'"),
        (_one("{id: x, text: x, checks: [{metric: lens_retries_delta, value: 0}]}"),
         "gates[0].checks[0]: missing key 'op'"),
        (_one("{id: x, text: x, checks: [{metric: lens_retries_delta, op: le}]}"),
         "gates[0].checks[0]: missing key 'value'"),
        (f"gates: [{{id: x, text: x, checks: [{CHECK}]}}]\n", "missing key 'schema_version'"),
        ("schema_version: 1\nstatus: proposal\n", "missing key 'gates'"),
        ("schema_version: 2\ngates: []\n", "unsupported schema_version 2"),
        ("schema_version: true\ngates: []\n", "unsupported schema_version True"),
        ("- schema_version: 1\n", "top level is not a mapping"),
        ("", "top level is not a mapping"),
        ("schema_version: 1\ngates: {}\n", "gates is not a non-empty list"),
        ("schema_version: 1\ngates: []\n", "gates is not a non-empty list"),
        (_one("x"), "gates[0] is not a mapping"),
        (_one("{id: x, text: x, checks: []}"), "gates[0]: checks is not a non-empty list"),
        (_one(f"{{id: x, text: x, checks: {CHECK}}}"), "gates[0]: checks is not a non-empty list"),
        (_one("{id: x, text: x, checks: [x]}"), "gates[0].checks[0] is not a mapping"),
        (_one(f"{{id: 5, text: x, checks: [{CHECK}]}}"), "gates[0]: id is not a non-empty string"),
        (_one(f"{{id: '', text: x, checks: [{CHECK}]}}"), "gates[0]: id is not a non-empty string"),
        (_one(f"{{id: x, text: ' ', checks: [{CHECK}]}}"),
         "gates[0]: text is not a non-empty string"),
        (_one(f"{{id: x, text: [x], checks: [{CHECK}]}}"),
         "gates[0]: text is not a non-empty string"),
        (_one(f"{{id: x, text: x, note: y, checks: [{CHECK}]}}"), "gates[0]: unknown key 'note'"),
        (_one("{id: x, text: x, checks: [{metric: lens_retries_delta, op: le, value: 0, max: 1}]}"),
         "gates[0].checks[0]: unknown key 'max'"),
    ],
)
def test_malformed_gates_files_are_refused(tmp_path, body, problem):
    p = tmp_path / "g.yaml"
    p.write_text(body, encoding="utf-8")
    with pytest.raises(GatesError) as exc:
        load_gates(p)
    assert str(exc.value) == f"{p}: {problem}"


@pytest.mark.parametrize(
    "value",
    ["true", "'0'", ".nan", ".inf", "-.inf", "1.0e+400", "1" + "0" * 400, "null", "[0]"],
    ids=["bool", "str", "nan", "inf", "-inf", "float-overflow", "int-overflow", "null", "list"],
)
def test_a_value_that_is_not_a_finite_number_is_refused(tmp_path, value):
    p = tmp_path / "g.yaml"
    check = f"{{metric: lens_retries_delta, op: le, value: {value}}}"
    p.write_text(_one(f"{{id: x, text: x, checks: [{check}]}}"), encoding="utf-8")
    with pytest.raises(GatesError, match=r"gates\[0\]\.checks\[0\]: value is not a finite number"):
        load_gates(p)


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (b"schema_version: 1\ngates: [\n", "invalid YAML"),
        (b"schema_version: 2026-02-30\n", "invalid YAML"),
        (b"[" * 5000, "invalid YAML: nested too deeply to parse"),
        (b"\xff\xfeschema_version: 1\n", "not UTF-8 text"),
    ],
    ids=["unclosed", "impossible-date", "deep-nesting", "not-utf8"],
)
def test_unparseable_gates_files_are_refused(tmp_path, content, problem):
    p = tmp_path / "g.yaml"
    p.write_bytes(content)
    with pytest.raises(GatesError) as exc:
        load_gates(p)
    assert str(exc.value).startswith(f"{p}: {problem}")


@pytest.mark.parametrize(
    "make", [lambda d: d / "missing.yaml", lambda d: d], ids=["missing", "directory"]
)
def test_unreadable_gates_files_are_refused(tmp_path, make):
    p = make(tmp_path)
    with pytest.raises(GatesError) as exc:
        load_gates(p)
    assert str(exc.value).startswith(f"{p}: cannot read: ")


def test_other_top_level_keys_are_ignored(tmp_path):
    p = tmp_path / "g.yaml"
    p.write_text(
        "schema_version: 1\nstatus: proposal\n"
        f"gates: [{{id: x, text: y, checks: [{CHECK}, {{metric: severity_agreement_pct, "
        "op: ge, value: 90.5}]}]\n"
        "catalog_gates: [{id: c, text: c, "
        "checks: [{metric: tm_recall_delta, op: ge, value: 0}]}]\n",
        encoding="utf-8",
    )
    assert load_gates(p) == (
        Gate(
            id="x",
            text="y",
            checks=(
                Check(metric="lens_retries_delta", op="le", value=0.0),
                Check(metric="severity_agreement_pct", op="ge", value=90.5),
            ),
        ),
    )
