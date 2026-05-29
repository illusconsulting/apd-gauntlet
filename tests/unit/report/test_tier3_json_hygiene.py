# tests/unit/report/test_tier3_json_hygiene.py
"""Regression tests for emit.py JSON serializer hygiene (T3-A).

Pins three latent hazards eliminated in PR-T3-A:
  1. `default=str` silently stringifying unknown types -> now raises.
  2. `allow_nan=True` emitting non-JSON NaN/Infinity tokens -> now raises.
  3. Raw `</` inside string values prematurely closing a host `<script>`
     tag -> now escaped to ``<\\/`` defense-in-depth.
"""
from __future__ import annotations

import datetime
import math

import pytest
from apd_gauntlet.report.emit import _normalize_for_json, write_data_js


def test_normalize_datetime_to_isoformat():
    out = _normalize_for_json({"when": datetime.datetime(2026, 5, 29, 14, 0, 0)})
    assert out == {"when": "2026-05-29T14:00:00"}


def test_normalize_date_to_isoformat():
    out = _normalize_for_json({"day": datetime.date(2026, 5, 29)})
    assert out == {"day": "2026-05-29"}


def test_normalize_set_to_sorted_list():
    out = _normalize_for_json({"tags": {"b", "a", "c"}})
    assert out == {"tags": ["a", "b", "c"]}


def test_normalize_frozenset_to_sorted_list():
    out = _normalize_for_json({"tags": frozenset(["b", "a"])})
    assert out == {"tags": ["a", "b"]}


def test_normalize_tuple_to_list():
    out = _normalize_for_json({"pair": ("a", "b")})
    assert out == {"pair": ["a", "b"]}


def test_normalize_passes_primitives_through():
    out = _normalize_for_json({"s": "x", "i": 1, "f": 1.5, "b": True, "n": None})
    assert out == {"s": "x", "i": 1, "f": 1.5, "b": True, "n": None}


def test_normalize_raises_on_unknown_type():
    class Custom:
        pass

    with pytest.raises(TypeError) as exc:
        _normalize_for_json({"obj": Custom()})
    assert "$.obj" in str(exc.value)
    assert "Custom" in str(exc.value)


def test_normalize_walks_nested_structures():
    out = _normalize_for_json({
        "list_of_dicts": [{"k": {"x", "y"}}, {"d": datetime.date(2026, 1, 1)}],
    })
    assert out == {
        "list_of_dicts": [{"k": ["x", "y"]}, {"d": "2026-01-01"}],
    }


def test_write_data_js_rejects_nan(tmp_path):
    target = tmp_path / "data.js"
    with pytest.raises(ValueError):
        write_data_js({"x": math.nan}, target)


def test_write_data_js_rejects_inf(tmp_path):
    target = tmp_path / "data.js"
    with pytest.raises(ValueError):
        write_data_js({"x": math.inf}, target)


def test_write_data_js_escapes_close_script(tmp_path):
    target = tmp_path / "data.js"
    write_data_js({"detail": "abc</script>xyz"}, target)
    body = target.read_text(encoding="utf-8")
    assert "</script>" not in body
    # The replacement </ uses a backslash to escape the forward slash.
    # The literal characters in the file should be `<\/script>` (5 chars
    # before `script`: `<`, `\`, `/`). Both spellings below produce the
    # same Python string (`<\/script>`) — kept compatible with the plan.
    assert "<\\/script>" in body


def test_write_data_js_no_default_str_coercion(tmp_path):
    """With default=str removed, an arbitrary object must raise rather than
    silently stringify."""
    class Custom:
        pass

    target = tmp_path / "data.js"
    with pytest.raises(TypeError):
        write_data_js({"obj": Custom()}, target)


def test_write_data_js_succeeds_on_clean_payload(tmp_path):
    """Smoke: realistic payload with strings + ints + lists + dicts builds OK."""
    payload = {
        "meta": {"run_id": "test", "subject": "claim-event-bus"},
        "summary": {"findings_total": 3, "bySeverity": {"high": 1, "low": 2}},
        "findings": [{"id": "f1", "severity": "high"}],
    }
    target = tmp_path / "data.js"
    write_data_js(payload, target)
    body = target.read_text(encoding="utf-8")
    assert "window.APD_DATA" in body
