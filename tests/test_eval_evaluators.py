"""eval.evaluators: the R2 evaluator registry and ``EvalResult``."""
from __future__ import annotations

import sys

import pytest
from apd_gauntlet.eval import evaluators
from apd_gauntlet.eval.evaluators import (
    EVALUATORS,
    EvalResult,
    get,
    load_builtin_evaluators,
    register,
)


def test_register_get_and_duplicates():
    def fn(e, labels):
        return EvalResult(e.id, {}, {})

    register("t-eval", fn)
    try:
        assert get("t-eval") is fn
        with pytest.raises(ValueError):
            register("t-eval", fn)
        with pytest.raises(KeyError, match="t-eval"):
            get("missing")
    finally:
        EVALUATORS.pop("t-eval")


# --- beyond the plan ---------------------------------------------------------


def _noop(entry, labels):
    return EvalResult(entry.id, {}, {})


@pytest.fixture
def registered():
    """Register the given names for one test and remove them afterwards."""
    names: list[str] = []

    def add(*new: str) -> None:
        for name in new:
            register(name, _noop)
            names.append(name)

    yield add
    for name in names:
        EVALUATORS.pop(name, None)


def test_duplicate_message_names_the_evaluator(registered):
    registered("t-dup")
    with pytest.raises(ValueError, match="evaluator 't-dup' is already registered"):
        register("t-dup", _noop)
    assert EVALUATORS["t-dup"] is _noop


def test_unknown_name_lists_the_registered_names_sorted(registered):
    registered("t-zeta", "t-alpha")
    with pytest.raises(KeyError) as exc:
        get("t-missing")
    message = exc.value.args[0]
    assert message.startswith("unknown evaluator 't-missing'; registered: ")
    names = message.split("registered: ")[1].split(", ")
    assert names == sorted(names) and {"t-alpha", "t-zeta"} <= set(names)


@pytest.mark.parametrize("name", ["", "Findings", "-x", "a/b", "../x", "a.b", "a b", "a_b"])
def test_names_must_be_safe_directory_names(name):
    with pytest.raises(ValueError, match="evaluator name"):
        register(name, _noop)
    assert name not in EVALUATORS


def test_eval_result_defaults_and_equality():
    def derive(counts):
        return {"m": float(counts["x"])}

    plain = EvalResult("a", {"x": 1}, {"m": 1.0})
    assert plain.notes == () and plain.derive is None
    with_derive = EvalResult("a", {"x": 1}, {"m": 1.0}, derive=derive)
    assert with_derive == plain and "derive" not in repr(with_derive)
    assert with_derive.derive is not None and with_derive.derive({"x": 3}) == {"m": 3.0}
    assert EvalResult("a", {"x": 1}, {"m": 1.0}, ("n",)) != plain


def test_load_builtin_evaluators_is_repeatable():
    load_builtin_evaluators()
    before = dict(EVALUATORS)
    load_builtin_evaluators()
    assert before == EVALUATORS


def test_unknown_name_with_nothing_registered(monkeypatch):
    monkeypatch.setattr(evaluators, "EVALUATORS", {})
    with pytest.raises(KeyError, match="unknown evaluator 'findings'; registered: none"):
        get("findings")


def test_load_builtin_evaluators_imports_each_module_once(tmp_path, monkeypatch):
    (tmp_path / "t8_builtin_probe.py").write_text(
        "from apd_gauntlet.eval.evaluators import EvalResult, register\n"
        "register('t-probe', lambda entry, labels: EvalResult(entry.id, {}, {}))\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(evaluators, "_BUILTIN_MODULES", ("t8_builtin_probe",))
    try:
        load_builtin_evaluators()
        load_builtin_evaluators()                       # cached import: no duplicate register
        assert "t-probe" in EVALUATORS
    finally:
        EVALUATORS.pop("t-probe", None)
        sys.modules.pop("t8_builtin_probe", None)
