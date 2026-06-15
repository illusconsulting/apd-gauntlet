# tests/unit/report/test_transform_lens_perspectives.py
"""Finding lens_perspectives render projection.

Bugfix: the report previously extracted a non-existent `source_id` from each
lens perspective (the schema is {lens: {summary, detail}}), rendering empty
pills and dropping the merged finding's per-lens reasoning entirely. The view
now emits [{lens, summary, detail}] so the report can show the real content.
"""
from __future__ import annotations

from apd_gauntlet.report.transform import _lens_perspectives_view


def test_dict_shape_emits_lens_summary_detail_in_order():
    raw = {
        "integrity": {"summary": "intg summary", "detail": "intg detail"},
        "immutability": {"summary": "immut summary", "detail": "immut detail"},
    }
    assert _lens_perspectives_view(raw) == [
        {"lens": "integrity", "summary": "intg summary", "detail": "intg detail"},
        {"lens": "immutability", "summary": "immut summary", "detail": "immut detail"},
    ]


def test_legacy_list_shape_uses_source_id_as_lens_label():
    raw = [{"source_id": "intg-4768c0f0", "summary": "a", "detail": "b"}]
    assert _lens_perspectives_view(raw) == [
        {"lens": "intg-4768c0f0", "summary": "a", "detail": "b"},
    ]


def test_list_shape_prefers_explicit_lens_over_source_id():
    raw = [{"lens": "confidentiality", "source_id": "x", "summary": "a", "detail": "b"}]
    assert _lens_perspectives_view(raw)[0]["lens"] == "confidentiality"


def test_missing_fields_degrade_to_empty_strings_not_none():
    assert _lens_perspectives_view({"auth": {}}) == [
        {"lens": "auth", "summary": "", "detail": ""},
    ]


def test_empty_or_absent_returns_empty_list():
    assert _lens_perspectives_view(None) == []
    assert _lens_perspectives_view({}) == []
    assert _lens_perspectives_view([]) == []
    assert _lens_perspectives_view("garbage") == []
