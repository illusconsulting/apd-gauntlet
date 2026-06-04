"""Threat-model block transform — authored baseline + supplied comparator."""
from __future__ import annotations

from apd_gauntlet.report.loader import RunArtifacts
from apd_gauntlet.report.transform import threat_model_block


def _artifacts(
    *,
    normalized: dict | None,
    supplied: dict | None,
) -> RunArtifacts:
    return RunArtifacts(
        run_id="r",
        framework_version="1.6.0",
        domain_pack_name="pbm",
        domain_pack_version="1.0.0",
        subject="s",
        date="2026-06-03",
        asset_inventory={},
        deduped_findings=[],
        deduped_capabilities=[],
        contradictions=[],
        contradictions_notes=None,
        severity_disagreements=[],
        severity_disagreements_notes=None,
        nist_coverage={},
        attack_exposure={},
        apd_coverage_matrix={},
        attack_paths=None,
        asset_graph=None,
        defense_graph=None,
        attack_path_findings=[],
        report_data=None,
        threat_model_normalized=normalized,
        threat_model_supplied=supplied,
    )


def _tm_artifacts(*, normalized=None, supplied=None, coverage=None, inventory=None):
    from apd_gauntlet.report.loader import RunArtifacts
    return RunArtifacts(
        run_id="r", framework_version="1.0.0", domain_pack_name="p",
        domain_pack_version="1", subject="s", date="2026-01-01",
        asset_inventory=inventory or {}, deduped_findings=[], deduped_capabilities=[],
        contradictions=[], contradictions_notes=None,
        severity_disagreements=[], severity_disagreements_notes=None,
        nist_coverage={}, attack_exposure={}, apd_coverage_matrix={},
        attack_paths=None, asset_graph=None, defense_graph=None,
        attack_path_findings=[], report_data=None,
        threat_model_normalized=normalized, threat_model_supplied=supplied,
        threat_model_coverage=coverage,
    )


def test_no_threat_model_returns_absent_block() -> None:
    block = threat_model_block(_artifacts(normalized=None, supplied=None))
    assert block == {
        "present": False,
        "authored": False,
        "supplied_present": False,
        "comparator": False,
        "generated_by": None,
        "methodology": None,
        "source_artifact": None,
        "entry_count": 0,
        "grounded_count": 0,
        "gap_count": 0,
        "entries": [],
        "stride_matrix": {"letters_present": [], "rows": []},
        "surface_coverage": None,
        "surface_mermaid": None,
        "comparator_delta": None,
    }


def test_threat_model_block_emits_entries_and_provenance():
    from apd_gauntlet.report.loader import RunArtifacts  # noqa: F401
    from apd_gauntlet.report.transform import threat_model_block

    normalized = {
        "generated_by": "threat_model_author",
        "methodology": "stride",
        "source_artifact": "tech_plan.md",
        "entries": [
            {"asset": "api", "threat": "cred theft", "mitigation": "MFA",
             "extraction_confidence": "high", "source_locator": "d[0]",
             "framework_refs": {"stride_letter": "S"},
             "inferred_apd_goals": ["authenticity"]},
            {"asset": "broker", "threat": "tamper", "mitigation": "",
             "extraction_confidence": "med", "source_locator": "d[1]",
             "framework_refs": {"stride_letter": "T"},
             "inferred_apd_goals": ["integrity"]},
        ],
    }
    art = _tm_artifacts(normalized=normalized)
    block = threat_model_block(art)

    assert block["present"] is True
    assert block["authored"] is True
    assert block["methodology"] == "stride"
    assert block["source_artifact"] == "tech_plan.md"
    assert block["entry_count"] == 2
    assert block["grounded_count"] == 1
    assert block["gap_count"] == 1
    assert [e["asset"] for e in block["entries"]] == ["api", "broker"]
    assert block["entries"][0]["stride_letter"] == "S"
    assert block["entries"][0]["apd_goals"] == ["authenticity"]


def test_threat_model_block_absent_is_omittable():
    from apd_gauntlet.report.transform import threat_model_block
    block = threat_model_block(_tm_artifacts(normalized=None))
    assert block["present"] is False
    assert block["entries"] == []
    assert block["stride_matrix"] == {"letters_present": [], "rows": []}
    assert block["surface_mermaid"] is None


def test_authored_baseline_recognized() -> None:
    block = threat_model_block(_artifacts(
        normalized={
            "generated_by": "threat_model_author",
            "entries": [{"entry_id": "tm-00000000"}, {"entry_id": "tm-11111111"}],
        },
        supplied=None,
    ))
    assert block["present"] is True
    assert block["authored"] is True
    assert block["supplied_present"] is False
    assert block["comparator"] is False
    assert block["entry_count"] == 2
    assert block["generated_by"] == "threat_model_author"


def test_supplied_present_enables_comparator() -> None:
    block = threat_model_block(_artifacts(
        normalized={
            "generated_by": "threat_model_author",
            "entries": [{"entry_id": "tm-00000000"}],
        },
        supplied={
            "generated_by": "threat_model_recon",
            "entries": [{"entry_id": "tm-22222222"}],
        },
    ))
    assert block["authored"] is True
    assert block["supplied_present"] is True
    assert block["comparator"] is True


def test_recon_canonical_plus_supplied_is_not_comparator() -> None:
    # Legacy/transitional: a recon-parsed canonical TM + a supplied sibling must
    # NOT be a comparator (the comparator is supplied-vs-AUTHORED only, spec C6).
    block = threat_model_block(_artifacts(
        normalized={"generated_by": "threat_model_recon", "entries": [{"entry_id": "tm-33333333"}]},
        supplied={"generated_by": "threat_model_recon", "entries": [{"entry_id": "tm-44444444"}]},
    ))
    assert block["authored"] is False
    assert block["supplied_present"] is True
    assert block["comparator"] is False


def test_recon_only_baseline_not_marked_authored() -> None:
    block = threat_model_block(_artifacts(
        normalized={"generated_by": "threat_model_recon", "entries": []},
        supplied=None,
    ))
    assert block["present"] is True
    assert block["authored"] is False
    assert block["generated_by"] == "threat_model_recon"


def test_tm_stride_matrix_cell_semantics():
    from apd_gauntlet.report.transform import _tm_stride_matrix
    entries = [
        {"asset": "api", "stride_letter": "S", "linddun_letter": None, "mitigation": "MFA"},
        {"asset": "api", "stride_letter": "I", "linddun_letter": None, "mitigation": ""},
        {"asset": "api", "stride_letter": "T", "linddun_letter": None, "mitigation": "x"},
        {"asset": "api", "stride_letter": "T", "linddun_letter": None, "mitigation": ""},
        {"asset": "broker", "stride_letter": "S", "linddun_letter": None, "mitigation": "y"},
    ]
    m = _tm_stride_matrix(entries, "stride")
    assert m["letters_present"] == ["S", "T", "I"]   # only modeled letters, STRIDE order
    rows = {r["asset"]: r["cells"] for r in m["rows"]}
    # api: S covered (mitigated), I gap (no mitigation), T partial (1 of 2 mitigated)
    assert rows["api"]["S"] == "covered"
    assert rows["api"]["I"] == "gap"
    assert rows["api"]["T"] == "partial"
    # broker: only S modeled → covered; unmodeled letters are "silent"
    assert rows["broker"]["S"] == "covered"
    assert rows["broker"]["T"] == "silent"
    # rows sorted by descending threat count: api (4) before broker (1)
    assert [r["asset"] for r in m["rows"]] == ["api", "broker"]


def test_tm_surface_coverage_parsing():
    from apd_gauntlet.report.transform import _tm_surface_coverage
    coverage = {
        "surface_coverage": [
            {"surface": "api", "categories_present": ["S", "I"],
             "categories_absent": ["R"], "tm_entry_count": 5},
        ],
        "summary": {"contradictions_emitted": 1, "silences_emitted": 1,
                    "coverage_gaps_emitted": 1, "surfaces_examined": 3},
    }
    out = _tm_surface_coverage(coverage)
    assert out["rows"][0] == {"surface": "api", "present": ["S", "I"],
                              "absent": ["R"], "entry_count": 5}
    assert out["summary"]["contradictions_emitted"] == 1


def test_tm_surface_coverage_absent_returns_none():
    from apd_gauntlet.report.transform import _tm_surface_coverage
    assert _tm_surface_coverage(None) is None
    assert _tm_surface_coverage({}) is None


def test_build_threat_surface_mermaid_clusters_and_hot():
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    entries = [
        {"asset": "api", "stride_letter": "S", "mitigation": "MFA"},
        {"asset": "api", "stride_letter": "I", "mitigation": ""},   # gap → hot
        {"asset": "broker", "stride_letter": "T", "mitigation": "x"},
    ]
    inv = {"trust_boundaries": [
        {"name": "internet", "assets": ["api"]},
        {"name": "data-plane", "assets": ["broker"]},
    ]}
    out = _build_threat_surface_mermaid(entries, inv)
    assert out.startswith("graph TD")
    assert "subgraph" in out                    # clustered by trust boundary
    assert "api [S I]" in out or 'api [S I]' in out  # node label badged with letters
    assert "classDef hot" in out and ":::hot" in out  # api has a gap → hot class
    assert "broker" in out


def test_build_threat_surface_mermaid_degrades_without_boundaries():
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    entries = [{"asset": "api", "stride_letter": "S", "mitigation": "MFA"}]
    out = _build_threat_surface_mermaid(entries, {})  # no trust boundaries
    assert out.startswith("graph TD")
    assert "subgraph" not in out                 # flat node list, no clusters
    assert "api [S]" in out


def test_build_threat_surface_mermaid_none_when_no_entries():
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    assert _build_threat_surface_mermaid([], {"trust_boundaries": []}) is None


def test_build_threat_surface_mermaid_sanitizes_adopter_labels():
    # Asset names and trust-boundary names are adopter/agent-controlled, so the
    # builder MUST route them through _safe_label (the same defense-in-depth
    # first layer used by the asset-graph Mermaid builders) before interpolation.
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    entries = [
        {"asset": 'api"]; click api callback <img src=x>',
         "stride_letter": "S", "mitigation": ""},
    ]
    inv = {"trust_boundaries": [
        {"name": "zone<script>", "assets": ['api"]; click api callback <img src=x>']},
    ]}
    out = _build_threat_surface_mermaid(entries, inv)
    # No HTML-tag payload survives into the label, and the quote/bracket
    # metacharacters that break Mermaid label quoting are gone.
    assert "<img" not in out
    assert "<script>" not in out
    assert '"];' not in out
    # HTML-tag-bearing labels are discarded entirely (defense in depth).
    assert "(unnamed)" in out


def test_build_threat_surface_mermaid_strips_bracket_metachars():
    # A benign asset name containing [ ] would break Mermaid's ["..."] quoting
    # if interpolated raw; _safe_label removes them so the graph still renders.
    from apd_gauntlet.report.transform import _build_threat_surface_mermaid
    entries = [{"asset": "queue[main]", "stride_letter": "D", "mitigation": "x"}]
    out = _build_threat_surface_mermaid(entries, {})
    assert "[main]" not in out
    assert "queue main [D]" in out


def test_tm_comparator_delta():
    from apd_gauntlet.report.transform import _tm_comparator_delta
    authored = {"entries": [
        {"asset": "api", "threat": "Credential theft"},
        {"asset": "broker", "threat": "Key rotation disabled"},
    ]}
    supplied = {"entries": [
        {"asset": "api", "threat": "credential theft"},   # corroborated (case-insensitive)
        {"asset": "edge", "threat": "DDoS"},               # supplied-only
    ]}
    d = _tm_comparator_delta(authored, supplied)
    assert [x["threat"] for x in d["authored_only"]] == ["Key rotation disabled"]
    assert [x["threat"] for x in d["supplied_only"]] == ["DDoS"]
    assert [x["threat"] for x in d["corroborated"]] == ["Credential theft"]


def test_tm_comparator_delta_block_only_when_comparator():
    # Integration: threat_model_block emits comparator_delta only when authored AND supplied.
    from apd_gauntlet.report.transform import threat_model_block
    authored = {"generated_by": "threat_model_author", "methodology": "stride",
                "entries": [{"asset": "api", "threat": "t"}]}
    supplied = {"generated_by": "threat_model_recon",
                "entries": [{"asset": "api", "threat": "t"}]}
    assert threat_model_block(_tm_artifacts(normalized=authored))["comparator_delta"] is None
    block = threat_model_block(_tm_artifacts(normalized=authored, supplied=supplied))
    assert block["comparator"] is True
    assert block["comparator_delta"] is not None
