"""Canonical severity-token normalization (F6).

The finding schema's canonical severity token is the full word ``informational``
(``finding.schema.json``). The metrics block (``synthesis/metrics.py``) and the
report template both use the short token ``info``. This module is the single
place that mapping lives, so the synthesis and report layers can never drift.

``normalize_severity`` is the synthesis-side helper (None/missing -> ``info``,
used when bucketing for counts). ``display_severity`` is the report-side helper
(None/missing -> ``info`` for the per-finding display payload). They share the
same one-entry mapping; both are exported so each layer reads from one source.
"""
from __future__ import annotations

from typing import Any

# The single source of truth for the schema-token -> template-token mapping.
INFORMATIONAL_TO_INFO: dict[str, str] = {"informational": "info"}


def normalize_severity(value: Any) -> str:
    """Normalize a finding severity for counting/bucketing.

    Falsy/``None`` values normalize to ``info`` (keeping the
    ``sum(bySeverity) == findings_total`` invariant intact), and the full word
    ``informational`` maps to the short token ``info``.
    """
    token = str(value or "informational")
    return INFORMATIONAL_TO_INFO.get(token, token)


def display_severity(value: Any) -> str:
    """Map a finding severity to the template's display token.

    Identical mapping to :func:`normalize_severity`; named separately because it
    is the report layer's per-finding display payload contract.
    """
    token = str(value or "informational")
    return INFORMATIONAL_TO_INFO.get(token, token)
