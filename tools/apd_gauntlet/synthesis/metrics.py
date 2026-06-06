# tools/apd_gauntlet/synthesis/metrics.py
"""Canonical report summary-block metrics — the single source of truth.

compute_metrics() is the ONE implementation of the report summary block. It is
pure (takes already-loaded record lists, returns a dict) so it is trivially
unit-testable. build_rollups() calls it and persists the result as
40-synthesis/metrics.yaml; the transform reads that artifact verbatim and the
audit asserts the rendered data.js carries it faithfully.
"""
from __future__ import annotations

import collections
from typing import Any

from ..severity import normalize_severity as _norm_sev  # F6: single shared normalizer

SCHEMA_VERSION = 1


def compute_metrics(
    findings: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
    contradictions: list[dict[str, Any]],
    severity_disagreements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the canonical report summary block.

    ``findings`` MUST be the deduped-findings UNION the apath-* findings (the
    same union ``_load_deduped`` builds). Severity is normalized to ``info``
    inside, so no downstream re-normalization is needed.

    Unlike the legacy ``summary_rollup``, falsy/``None``/already-``info``
    severities normalize to ``info`` (rather than being dropped), which keeps
    the ``sum(bySeverity) == findings_total`` invariant intact.
    """
    by_sev = collections.Counter(_norm_sev(f.get("severity")) for f in findings)
    by_disp = collections.Counter(f.get("disposition") or "gap" for f in findings)
    by_tier = collections.Counter(f.get("apd_tier") or "trustworthiness" for f in findings)
    by_mat = collections.Counter(c.get("maturity", "implemented") for c in capabilities)

    cross_lens_merged = sum(
        1 for c in capabilities
        if c.get("merged") or (
            c.get("lens_perspectives") and c.get("id", "").startswith("cap-merged")
        )
    )
    linked_clusters = sum(1 for f in findings if f.get("linked_perspectives"))

    return {
        "schema_version": SCHEMA_VERSION,
        "findings_total": len(findings),
        "findings_pre_dedup": len(findings),
        "cross_lens_merged_clusters": cross_lens_merged,
        "linked_clusters": linked_clusters,
        "bySeverity": {
            "critical": by_sev.get("critical", 0),
            "high":     by_sev.get("high", 0),
            "medium":   by_sev.get("medium", 0),
            "low":      by_sev.get("low", 0),
            "info":     by_sev.get("info", 0),
        },
        "byDisposition": {
            "gap":         by_disp.get("gap", 0),
            "blocked":     by_disp.get("blocked", 0),
            "risk":        by_disp.get("risk", 0),
            "uncertainty": by_disp.get("uncertainty", 0),
            "ok":          0,
        },
        "byTier": {
            "trustworthiness": by_tier.get("trustworthiness", 0),
            "scalability":     by_tier.get("scalability", 0),
            "auditability":    by_tier.get("auditability", 0),
        },
        "capabilities_total": len(capabilities),
        "capabilities_pre_dedup": len(capabilities),
        "capabilitiesByMaturity": {
            "designed":        by_mat.get("designed", 0),
            "implemented":     by_mat.get("implemented", 0),
            "tested":          by_mat.get("tested", 0),
            "operationalized": by_mat.get("operationalized", 0),
        },
        "contradictions": len(contradictions),
        "severity_disagreements": len(severity_disagreements),
    }
