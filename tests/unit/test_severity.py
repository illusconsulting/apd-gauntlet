"""F6: a single shared severity-token normalizer used by synthesis + report.

The finding schema's canonical token is the full word ``informational``; the
metrics block and the report template use the short token ``info``. Before this
module that mapping lived in two places (``metrics._INFORMATIONAL_TO_INFO`` and
``transform._SEVERITY_DISPLAY``). These tests pin the one canonical helper so
the two call sites can never drift.
"""
from __future__ import annotations

from apd_gauntlet.severity import (
    INFORMATIONAL_TO_INFO,
    display_severity,
    normalize_severity,
)


def test_normalize_informational_to_info() -> None:
    assert normalize_severity("informational") == "info"


def test_normalize_none_defaults_to_info() -> None:
    assert normalize_severity(None) == "info"


def test_normalize_passes_through_known_tokens() -> None:
    for token in ("critical", "high", "medium", "low", "info"):
        assert normalize_severity(token) == token


def test_display_severity_maps_informational() -> None:
    assert display_severity("informational") == "info"


def test_display_severity_defaults_to_info() -> None:
    assert display_severity(None) == "info"


def test_display_severity_passes_through_known_tokens() -> None:
    for token in ("critical", "high", "medium", "low"):
        assert display_severity(token) == token


def test_mapping_constant_is_the_single_source() -> None:
    assert INFORMATIONAL_TO_INFO == {"informational": "info"}
