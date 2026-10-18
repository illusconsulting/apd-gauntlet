"""measure.usage: OTLP/JSON ``api_request`` events, the agent-to-phase map and ``usage.yaml``."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

import pytest
import yaml
from apd_gauntlet.measure.runs import RunLoadError, load_run
from apd_gauntlet.measure.usage import (
    AGENT_PHASES,
    PSEUDO_PHASES,
    REDACTED_AGENTS,
    USAGE_RELPATH,
    ApiRequest,
    UsageParseError,
    iter_api_requests,
    phase_for,
    summarize_decisions,
    summarize_usage,
    write_usage,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests/fixtures"
WORKFLOW_JS = REPO / ".claude/workflows/apd-gauntlet.js"
OTEL = FIXTURES / "otel/claude-code-logs.otlp.jsonl"


def test_parses_only_api_requests():
    reqs = list(iter_api_requests(OTEL))
    assert [r.agent for r in reqs] == [
        "apd-confidentiality", "apd-confidentiality", "general-purpose", "main", "custom"
    ]
    assert reqs[1].input_tokens == 500 and reqs[1].cost_usd_micros == 250_000


def test_summary_totals_and_phases():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    assert s["totals"] == {"requests": 5, "input_tokens": 1617, "output_tokens": 358,
                           "cache_read_tokens": 5000, "cache_creation_tokens": 300,
                           "cost_usd": 0.763}
    assert s["by_agent"]["apd-confidentiality"] == {
        "phase": "tier-1", "requests": 2, "input_tokens": 1500, "output_tokens": 300,
        "cache_read_tokens": 5000, "cache_creation_tokens": 300, "cost_usd": 0.75}
    assert s["by_phase"]["cli-steps"]["cost_usd"] == 0.01
    assert s["by_agent"]["main"]["phase"] == "session"


def test_redacted_agent_names_warn():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    assert s["by_agent"]["custom"]["phase"] == "unattributed"
    assert any("OTEL_LOG_TOOL_DETAILS=1" in w for w in s["warnings"])
    assert any("wf_1" in w and "wf_2" in w for w in s["warnings"])


def test_workflow_run_filter():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL, workflow_run="wf_1")
    assert s["totals"]["requests"] == 3 and s["totals"]["cost_usd"] == 0.76


def test_plugin_prefix_stripped():
    assert phase_for("apd-gauntlet:apd-report-writer") == "synthesis-report"


def test_agent_phases_cover_agents_and_workflow_phases():
    agents = {p.stem for p in (REPO / ".claude/agents").glob("apd-*.md")} - {"apd-orchestrator"}
    assert agents <= set(AGENT_PHASES)
    m = re.search(r"phases:\s*\[(.*?)\]", WORKFLOW_JS.read_text(), re.DOTALL)
    assert set(AGENT_PHASES.values()) <= set(re.findall(r"'([^']+)'", m.group(1))) | PSEUDO_PHASES


def test_tier_repair_counts_under_canonicalize():
    assert phase_for("apd-tier-repair") == "canonicalize"


# --- beyond the plan's tests -------------------------------------------------------------


def _doc(*records, resource=()):
    """One ``ExportLogsServiceRequest`` holding ``records`` under one resource and scope."""
    return {"resourceLogs": [{
        "resource": {"attributes": list(resource)},
        "scopeLogs": [{"scope": {"name": "com.anthropic.claude_code.events"},
                       "logRecords": list(records)}],
    }]}


def _attr(key, value, kind="stringValue"):
    return {"key": key, "value": {kind: value}}


def _request(*attrs, body="claude_code.api_request", event="api_request"):
    rec = {"timeUnixNano": "1760140800000000000",
           "attributes": ([_attr("event.name", event)] if event else []) + list(attrs)}
    if body is not None:
        rec["body"] = {"stringValue": body}
    return rec


def _write_jsonl(path, *docs):
    path.write_text("".join(json.dumps(d) + "\n" for d in docs), encoding="utf-8")
    return path


def test_agent_phases_is_the_planned_table():
    tiers = {
        "tier-1": ("apd-confidentiality", "apd-integrity", "apd-availability"),
        "tier-2": ("apd-distributed", "apd-resilient", "apd-ephemeral"),
        "tier-3": ("apd-authenticity", "apd-non-repudiation", "apd-immutability"),
    }
    expected = {agent: tier for tier, agents in tiers.items() for agent in agents}
    expected.update({
        "apd-intake": "intake",
        "apd-code-recon": "code-recon",
        "apd-threat-model-author": "threat-model-author",
        "apd-threat-model-recon": "tm-recon",
        "apd-cluster-adjudicator": "synthesis-adjudicate",
        "apd-synthesizer": "synthesis-fallback",
        "apd-threat-model-evaluator": "tmeval",
        "apd-attack-path-analyzer": "apath",
        "apd-report-writer": "synthesis-report",
        "apd-report-auditor": "synthesis-audit",
        "apd-domain-auditor": "domain-improvements",
        "apd-tier-repair": "canonicalize",
        "general-purpose": "cli-steps",
        "main": "session",
    })
    assert expected == AGENT_PHASES
    assert frozenset({"cli-steps", "session", "unattributed"}) == PSEUDO_PHASES
    assert frozenset({"custom", "third-party"}) == REDACTED_AGENTS


@pytest.mark.parametrize("agent", ["custom", "third-party", "Explore", "apd-orchestrator", ""])
def test_unknown_and_redacted_agents_are_unattributed(agent):
    assert phase_for(agent) == "unattributed"


def test_pseudo_phases():
    assert phase_for("general-purpose") == "cli-steps"
    assert phase_for("main") == "session"
    assert phase_for("other-plugin:custom") == "unattributed"


def test_every_request_field_is_decoded():
    reqs = list(iter_api_requests(OTEL))
    assert reqs[0] == ApiRequest(
        agent="apd-confidentiality", model="claude-sonnet-4-5", input_tokens=1000,
        output_tokens=200, cache_read_tokens=5000, cache_creation_tokens=300,
        cost_usd_micros=500_000, session_id="s1", workflow_run_id="wf_1", effort="high",
    )
    assert reqs[2].input_tokens == 100 and reqs[2].cost_usd_micros == 10_000  # JSON numbers
    assert reqs[3].workflow_run_id is None and reqs[3].effort is None
    assert [r.workflow_run_id for r in reqs] == ["wf_1", "wf_1", "wf_1", None, "wf_2"]
    assert not any(r.cost_missing for r in reqs)


def test_summary_source_filter_and_phase_counters():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    assert s["schema_version"] == 1 and s["generated_by"] == "apd-gauntlet usage"
    assert s["source"] == {
        "file": str(OTEL),
        "sha256": hashlib.sha256(OTEL.read_bytes()).hexdigest(),
        "api_requests": 5,
        "sessions": ["s1"],
        "workflow_runs": ["wf_1", "wf_2"],
    }
    assert s["filter"] == {"workflow_run": None}
    assert s["by_phase"]["tier-1"] == {
        "requests": 2, "input_tokens": 1500, "output_tokens": 300, "cache_read_tokens": 5000,
        "cache_creation_tokens": 300, "cost_usd": 0.75}
    assert set(s["by_phase"]) == {"tier-1", "cli-steps", "session", "unattributed"}
    assert s["by_phase"]["unattributed"]["requests"] == 1
    assert sum(p["requests"] for p in s["by_phase"].values()) == s["totals"]["requests"]
    assert list(s["by_agent"]) == sorted(s["by_agent"])


def test_warning_texts():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    assert s["warnings"] == [
        "agent names redacted on 1 requests ('custom'/'third-party'): set "
        "OTEL_LOG_TOOL_DETAILS=1 and use Claude Code 2.1.273 or later",
        "multiple workflow runs in this file (wf_1, wf_2): pass --workflow-run",
    ]


REDACTION_WARNING = (
    "agent names redacted on {} requests ('custom'/'third-party'): set "
    "OTEL_LOG_TOOL_DETAILS=1 and use Claude Code 2.1.273 or later"
)


def _costed(agent, *attrs):
    """An ``api_request`` from ``agent`` that carries a cost, so no missing-cost warning."""
    return _request(_attr("agent.name", agent), _attr("cost_usd_micros", "1", "intValue"), *attrs)


def test_redaction_warning_counts_only_redacted_names(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _costed("Explore"), _costed("apd-orchestrator"), _costed("custom"),
    ))
    s = summarize_usage(iter_api_requests(f), source=f)
    assert {agent: row["phase"] for agent, row in s["by_agent"].items()} == {
        "Explore": "unattributed", "apd-orchestrator": "unattributed", "custom": "unattributed"}
    assert s["warnings"] == [REDACTION_WARNING.format(1)]


def test_unknown_agent_names_alone_give_no_redaction_warning(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_costed("Explore"), _costed("apd-orchestrator")))
    s = summarize_usage(iter_api_requests(f), source=f)
    assert s["by_phase"]["unattributed"]["requests"] == 2
    assert s["warnings"] == []


def test_redaction_warning_ignores_a_plugin_prefix(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _costed("other-plugin:custom"), _costed("p:third-party"), _costed("p:Explore"),
    ))
    s = summarize_usage(iter_api_requests(f), source=f)
    assert s["warnings"] == [REDACTION_WARNING.format(2)]


def test_missing_cost_warning_counts_only_the_filtered_requests(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _costed("apd-intake", _attr("workflow.run_id", "wf_a")),
        _request(_attr("agent.name", "apd-intake"), _attr("workflow.run_id", "wf_b")),
    ))
    assert summarize_usage(iter_api_requests(f), source=f, workflow_run="wf_a")["warnings"] == []
    s = summarize_usage(iter_api_requests(f), source=f, workflow_run="wf_b")
    assert s["warnings"] == ["1 requests carried no cost attribute"]


def test_source_sessions_describe_the_whole_file(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _costed("apd-intake", _attr("workflow.run_id", "wf_a"), _attr("session.id", "s2")),
        _costed("apd-intake", _attr("workflow.run_id", "wf_b"), _attr("session.id", "s1")),
    ))
    s = summarize_usage(iter_api_requests(f), source=f, workflow_run="wf_a")
    assert s["source"]["sessions"] == ["s1", "s2"]
    assert s["source"]["workflow_runs"] == ["wf_a", "wf_b"]
    assert s["totals"]["requests"] == 1


def test_filter_to_one_run_drops_its_warnings():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL, workflow_run="wf_1")
    assert s["warnings"] == []
    assert s["filter"] == {"workflow_run": "wf_1"}
    assert s["source"]["api_requests"] == 5  # the file, not the filter
    assert set(s["by_agent"]) == {"apd-confidentiality", "general-purpose"}


def test_filter_to_an_absent_run_is_empty():
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL, workflow_run="wf_9")
    assert s["totals"]["requests"] == 0 and s["by_agent"] == {} and s["by_phase"] == {}


def test_missing_cost_is_zero_and_counted(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _request(_attr("agent.name", "apd-intake"), _attr("input_tokens", "4", "intValue")),
        _request(_attr("agent.name", "apd-intake"), _attr("cost_usd", 0.25, "doubleValue")),
    ))
    reqs = list(iter_api_requests(f))
    assert [(r.cost_usd_micros, r.cost_missing) for r in reqs] == [(0, True), (250_000, False)]
    s = summarize_usage(reqs, source=f)
    assert "1 requests carried no cost attribute" in s["warnings"]
    assert s["totals"]["cost_usd"] == 0.25


def test_cost_usd_is_rounded_to_whole_micros(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _request(_attr("cost_usd", 0.0123456789, "doubleValue")),
        _request(_attr("cost_usd", "0.9999996")),
    ))
    assert [r.cost_usd_micros for r in iter_api_requests(f)] == [12_346, 1_000_000]


def test_cost_usd_micros_wins_over_cost_usd(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(
        _attr("cost_usd", 9.0, "doubleValue"), _attr("cost_usd_micros", 1234, "intValue"),
    )))
    assert [r.cost_usd_micros for r in iter_api_requests(f)] == [1234]


def test_attribute_value_encodings(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(
        _attr("input_tokens", 3.0, "doubleValue"),
        _attr("output_tokens", 7, "intValue"),
        _attr("cache_read_tokens", "11"),
        _attr("cost_usd", "0.5"),
        _attr("model", "m-1"),
        {"key": "cache_creation_tokens", "value": {"arrayValue": {"values": []}}},
    )))
    (r,) = iter_api_requests(f)
    assert (r.input_tokens, r.output_tokens, r.cache_read_tokens) == (3, 7, 11)
    assert r.cache_creation_tokens == 0  # an unsupported value kind reads as absent
    assert r.cost_usd_micros == 500_000 and r.model == "m-1"


def test_event_name_or_body_marks_a_request(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _request(_attr("agent.name", "apd-intake"), event=None),
        _request(_attr("agent.name", "apd-integrity"), body=None),
        _request(_attr("agent.name", "apd-ephemeral"), body="claude_code.api_error",
                 event="api_error"),
    ))
    assert [r.agent for r in iter_api_requests(f)] == ["apd-intake", "apd-integrity"]


def test_record_attributes_override_resource_attributes(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(
        _request(_attr("agent.name", "apd-integrity")),
        _request(),
        resource=[_attr("agent.name", "apd-intake"), _attr("workflow.run_id", "wf_r"),
                  _attr("session.id", "s9")],
    ))
    reqs = list(iter_api_requests(f))
    assert [r.agent for r in reqs] == ["apd-integrity", "apd-intake"]
    assert {(r.workflow_run_id, r.session_id) for r in reqs} == {("wf_r", "s9")}


def test_empty_agent_name_is_main(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(_attr("agent.name", ""))))
    assert [r.agent for r in iter_api_requests(f)] == ["main"]


def test_pretty_printed_document_accepted(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps(_doc(_request(_attr("agent.name", "apd-intake"))), indent=2))
    assert [r.agent for r in iter_api_requests(f)] == ["apd-intake"]


def test_documents_without_resource_logs_are_skipped(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text(
        '{"resourceMetrics": [{"scopeMetrics": []}]}\n'
        "\n"
        '{"resourceSpans": []}\n'
        + json.dumps(_doc(_request(_attr("agent.name", "apd-intake")))) + "\n"
        + "[1, 2]\n",
        encoding="utf-8",
    )
    assert [r.agent for r in iter_api_requests(f)] == ["apd-intake"]


def test_console_export_is_not_otlp_json():
    with pytest.raises(UsageParseError) as err:
        list(iter_api_requests(FIXTURES / "otel/console-export.txt"))
    msg = str(err.value)
    assert "OTLP/JSON" in msg and "docs/measuring-changes.md" in msg
    assert "console-export.txt: line 2" in msg


def test_non_json_after_a_valid_line_names_the_line(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text(json.dumps(_doc(_request())) + "\nnot json\n", encoding="utf-8")
    with pytest.raises(UsageParseError, match=r"t\.jsonl: line 2: .*OTLP/JSON"):
        list(iter_api_requests(f))


def test_non_integer_token_value_raises(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(_attr("output_tokens", "lots"))))
    with pytest.raises(UsageParseError, match="line 1: output_tokens is not an integer: 'lots'"):
        list(iter_api_requests(f))


def test_boolean_token_value_raises(tmp_path):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(_attr("input_tokens", True, "boolValue"))))
    with pytest.raises(UsageParseError, match="input_tokens is not an integer: True"):
        list(iter_api_requests(f))


def test_integer_too_long_to_convert_raises(tmp_path):
    limit = getattr(sys, "get_int_max_str_digits", lambda: 0)()
    if not limit:
        pytest.skip("this Python has no limit on integer string conversion")
    f = tmp_path / "t.jsonl"
    f.write_text(
        json.dumps(_doc(_request())) + '\n{"resourceLogs": [], "n": ' + "9" * (limit + 1) + "}\n",
        encoding="utf-8",
    )
    with pytest.raises(UsageParseError, match=r"t\.jsonl: line 2: cannot parse a JSON value"):
        list(iter_api_requests(f))


@pytest.mark.parametrize("name", ["output_tokens", "cost_usd_micros", "cost_usd"])
def test_a_long_bad_value_is_shortened_in_the_error(tmp_path, name):
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(_attr(name, "x" * 5000))))
    with pytest.raises(UsageParseError) as err:
        list(iter_api_requests(f))
    msg = str(err.value)
    assert f"line 1: {name} is not " in msg and ": 'xxxxxxxx" in msg
    assert msg.endswith("...") and len(msg) < len(str(f)) + 150


def test_json_nested_too_deeply_raises(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text("[" * 200_000 + "\n", encoding="utf-8")
    with pytest.raises(UsageParseError, match="line 1: nested too deeply to parse"):
        list(iter_api_requests(f))


@pytest.mark.parametrize("value", [True, "NaN", "inf"])
def test_impossible_cost_raises(tmp_path, value):
    kind = "boolValue" if value is True else "stringValue"
    f = _write_jsonl(tmp_path / "t.jsonl", _doc(_request(_attr("cost_usd", value, kind))))
    with pytest.raises(UsageParseError, match="cost_usd is not a finite number"):
        list(iter_api_requests(f))


@pytest.mark.parametrize("doc, where", [
    ({"resourceLogs": {"scopeLogs": []}}, "resourceLogs is not a list"),
    ({"resourceLogs": ["x"]}, "resourceLogs[0] is not an object"),
    ({"resourceLogs": [{"scopeLogs": [{"logRecords": "x"}]}]},
     "resourceLogs[0].scopeLogs[0].logRecords is not a list"),
    ({"resourceLogs": [{"resource": {"attributes": {}}}]},
     "resourceLogs[0].resource.attributes is not a list"),
])
def test_malformed_otlp_structure_raises(tmp_path, doc, where):
    f = _write_jsonl(tmp_path / "t.jsonl", doc)
    with pytest.raises(UsageParseError) as err:
        list(iter_api_requests(f))
    assert f"line 1: {where}" in str(err.value)


def test_unreadable_or_non_utf8_file_raises(tmp_path):
    with pytest.raises(UsageParseError, match="cannot read"):
        list(iter_api_requests(tmp_path / "missing.jsonl"))
    bad = tmp_path / "bad.jsonl"
    bad.write_bytes(b'{"resourceLogs": "\xff"}\n')
    with pytest.raises(UsageParseError, match="not UTF-8"):
        list(iter_api_requests(bad))


def test_write_usage_round_trip(tmp_path):
    s = summarize_usage(iter_api_requests(OTEL), source=OTEL)
    path = write_usage(tmp_path, s)
    assert path == tmp_path / USAGE_RELPATH == tmp_path / ".apd-state/usage.yaml"
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == s
    assert list(yaml.safe_load(path.read_text(encoding="utf-8"))) == list(s)  # key order kept
    write_usage(tmp_path, {"schema_version": 1, "totals": {"requests": 1, "cost_usd": 2.0}})
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["totals"]["cost_usd"] == 2.0
    assert sorted(p.name for p in path.parent.iterdir()) == ["usage.yaml"]


def _decision(run, name, text):
    folder = run / "40-synthesis/decisions"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")


EMPTY_DECISIONS = {
    "totals": {"calls": 0, "input_tokens": 0, "cost_usd": 0.0},
    "by_task": {},
    "by_cost_basis": {},
}


def test_no_decision_records(tmp_path):
    assert summarize_decisions(tmp_path) == EMPTY_DECISIONS
    (tmp_path / "40-synthesis/decisions").mkdir(parents=True)
    assert summarize_decisions(tmp_path) == EMPTY_DECISIONS


def test_decision_records_are_totalled_by_task_and_cost_basis(tmp_path):
    _decision(tmp_path, "finding-qa.all.yaml", "task: finding-qa\nscope: all\nusage: "
              "{calls: 3, input_tokens: 4210, cost_usd: 0.00101, cost_basis: estimated}\n")
    _decision(tmp_path, "finding-qa.10-trustworthiness.yaml", "task: finding-qa\nusage: "
              "{calls: 1, input_tokens: 812, cost_usd: 0.0002, cost_basis: reported}\n")
    _decision(tmp_path, "cluster-pairs.all.yaml", "task: cluster-pairs\nusage: "
              "{calls: 2, input_tokens: null, cost_usd: null, cost_basis: unknown}\n")
    _decision(tmp_path, "notes.txt", "not a record")
    assert summarize_decisions(tmp_path) == {
        "totals": {"calls": 6, "input_tokens": 5022, "cost_usd": 0.00121},
        "by_task": {
            "cluster-pairs": {"calls": 2, "input_tokens": 0, "cost_usd": 0.0},
            "finding-qa": {"calls": 4, "input_tokens": 5022, "cost_usd": 0.00121},
        },
        "by_cost_basis": {
            "estimated": {"calls": 3, "input_tokens": 4210, "cost_usd": 0.00101},
            "reported": {"calls": 1, "input_tokens": 812, "cost_usd": 0.0002},
            "unknown": {"calls": 2, "input_tokens": 0, "cost_usd": 0.0},
        },
    }


@pytest.mark.parametrize("text, problem", [
    ("task: [unclosed\n", "invalid YAML"),
    ("- a list\n", "top level is not a mapping"),
    ("task: finding-qa\nusage: 3\n", "usage is not a mapping"),
    ("task: finding-qa\nusage: {calls: many}\n", "usage.calls is not a whole number"),
    ("task: finding-qa\nusage: {calls: 1, cost_usd: true}\n", "usage.cost_usd is not a number"),
])
def test_unusable_decision_record_raises_naming_it(tmp_path, text, problem):
    _decision(tmp_path, "finding-qa.all.yaml", text)
    with pytest.raises(UsageParseError) as err:
        summarize_decisions(tmp_path)
    assert str(err.value).startswith(str(tmp_path / "40-synthesis/decisions/finding-qa.all.yaml"))
    assert problem in str(err.value)


def test_a_long_bad_decision_value_is_shortened_in_the_error(tmp_path):
    _decision(tmp_path, "finding-qa.all.yaml",
              f"task: finding-qa\nusage: {{calls: {'z' * 5000}}}\n")
    with pytest.raises(UsageParseError) as err:
        summarize_decisions(tmp_path)
    msg = str(err.value)
    assert "usage.calls is not a whole number: 'zzzzzzzz" in msg
    assert msg.endswith("...") and len(msg) < len(str(tmp_path)) + 200


def test_decision_record_without_usage_counts_its_task_at_zero(tmp_path):
    _decision(tmp_path, "finding-qa.all.yaml", "task: finding-qa\n")
    _decision(tmp_path, "untitled.yaml", "usage: {calls: 1}\n")
    assert summarize_decisions(tmp_path) == {
        "totals": {"calls": 1, "input_tokens": 0, "cost_usd": 0.0},
        "by_task": {
            "finding-qa": {"calls": 0, "input_tokens": 0, "cost_usd": 0.0},
            "unknown": {"calls": 1, "input_tokens": 0, "cost_usd": 0.0},
        },
        "by_cost_basis": {"unknown": {"calls": 1, "input_tokens": 0, "cost_usd": 0.0}},
    }


def test_unreadable_decisions_folder_or_record_raises(tmp_path):
    (tmp_path / "40-synthesis").mkdir()
    (tmp_path / "40-synthesis/decisions").write_text("a file, not a folder", encoding="utf-8")
    with pytest.raises(UsageParseError, match="decisions: cannot read"):
        summarize_decisions(tmp_path)
    (tmp_path / "40-synthesis/decisions").unlink()
    _decision(tmp_path, "finding-qa.all.yaml", "")
    (tmp_path / "40-synthesis/decisions/finding-qa.all.yaml").write_bytes(b"task: \xff\n")
    with pytest.raises(UsageParseError, match="finding-qa.all.yaml: not UTF-8"):
        summarize_decisions(tmp_path)


def test_run_snapshot_usage_totals(make_run):
    run = make_run("r")
    assert load_run(run).usage_totals is None
    write_usage(run, {"schema_version": 1, "totals": {"requests": 1, "cost_usd": 2.0}})
    assert load_run(run).usage_totals == {"requests": 1, "cost_usd": 2.0}
    write_usage(run, {"schema_version": 1, "totals": {"requests": 5, "cost_usd": 0.763},
                      "cost_usd_all": 0.76401})
    assert load_run(run).usage_totals == {"requests": 5, "cost_usd": 0.763, "cost_usd_all": 0.76401}


@pytest.mark.parametrize("text, problem", [
    ("totals: [unclosed\n", "invalid YAML"),
    ("schema_version: 1\n", "totals is not a mapping"),
    ("totals: {requests: 1, cost_usd: lots}\n", "totals.cost_usd is not a number"),
    ("totals: {requests: true}\n", "totals.requests is not a number"),
    ("totals: {requests: 1, cost_usd: .nan}\n", "totals.cost_usd is not a number"),
    ("totals: {requests: 1}\ncost_usd_all: null\n", "cost_usd_all is not a number"),
])
def test_unusable_usage_file_fails_the_run_load(make_run, text, problem):
    run = make_run("r")
    (run / ".apd-state").mkdir()
    (run / USAGE_RELPATH).write_text(text, encoding="utf-8")
    with pytest.raises(RunLoadError) as err:
        load_run(run)
    assert str(err.value).startswith(str(run / USAGE_RELPATH))
    assert problem in str(err.value)
