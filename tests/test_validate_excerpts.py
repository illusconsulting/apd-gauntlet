"""validate warns when an evidence excerpt is not verbatim in its cited input."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import apd_gauntlet.validate as validate_mod
import pytest
from apd_gauntlet.cli import main
from apd_gauntlet.validate import (
    check_excerpts_verbatim,
    excerpt_fragments,
    normalize_excerpt_text,
    run_cross_file_pass,
)
from click.testing import CliRunner

FIX = Path(__file__).parent / "fixtures"

FINDING_EX = "All Kafka topics use AES-256 at-rest encryption via broker-managed keys"
CAP_EX = "Field-level envelope encryption for PHI columns with DEKs from KMS"
PARAPHRASE = "Topics are encrypted with broker keys.\n" + CAP_EX
MESSAGE = "evidence[0].excerpt not found verbatim in artifact 'tech_plan.md'"


def _run(tmp_path, tech_plan: str | bytes | None) -> Path:
    run = shutil.copytree(FIX / "runs" / "clean-run", tmp_path / "run")
    target = run / "inputs" / "tech_plan.md"
    if isinstance(tech_plan, bytes):
        target.write_bytes(tech_plan)
    elif tech_plan is not None:
        target.write_text(tech_plan)
    return run


def _set_excerpt_from(run, old, new):
    f = run / "10-trustworthiness/confidentiality.findings.yaml"
    f.write_text(f.read_text().replace(old, new))


def _set_excerpt(run, excerpt):
    _set_excerpt_from(run, FINDING_EX, excerpt)


def _validate(run, *flags):
    return CliRunner().invoke(main, ["validate", *flags, str(run)])


def _cite_from(run, old, new):
    _set_excerpt_from(run, f"artifact: {old}", f"artifact: {new}")


def _cite(run, artifact):
    _cite_from(run, "tech_plan.md", artifact)


# --- helpers ---------------------------------------------------------------


def test_normalize_drops_inline_markers_and_collapses_whitespace():
    assert normalize_excerpt_text("  a **b**\n\t`c`   d* ") == "a b c d"


def test_fragments_split_at_ascii_and_unicode_ellipsis():
    assert excerpt_fragments("one two ... three… `four`  five") == ["one two", "three", "four five"]


def test_fragments_without_ellipsis_is_one_fragment():
    assert excerpt_fragments("  just   one\nfragment ") == ["just one fragment"]


def test_fragments_drops_empty_pieces():
    assert excerpt_fragments("... ...") == []
    assert excerpt_fragments("") == []


# --- the check through the CLI ---------------------------------------------


def test_verbatim_excerpts_are_clean(tmp_path):
    r = _validate(_run(tmp_path, f"## 4.2\n{FINDING_EX}.\n\n## 5.3\n{CAP_EX}.\n"))
    assert r.exit_code == 0 and "not found verbatim" not in r.output


def test_reflowed_whitespace_still_matches(tmp_path):
    src = "All Kafka topics use AES-256\n   at-rest encryption via\tbroker-managed keys\n" + CAP_EX
    assert "not found verbatim" not in _validate(_run(tmp_path, src)).output


def test_markdown_inline_markup_is_ignored(tmp_path):  # Review Focus 4
    src = "All **Kafka topics** use `AES-256` at-rest encryption via broker-managed keys\n" + CAP_EX
    assert "not found verbatim" not in _validate(_run(tmp_path, src)).output


def test_absence_marker_is_not_checked(tmp_path):  # Review Focus 4
    run = _run(tmp_path, CAP_EX)
    _set_excerpt(run, "(absent in supplied TM)")
    assert "not found verbatim" not in _validate(run).output


def test_partially_parenthesized_excerpt_is_still_checked(tmp_path):
    run = _run(tmp_path, CAP_EX)
    _set_excerpt(run, "(1) topics are encrypted (see §4.2)")
    assert len(check_excerpts_verbatim(run)) == 1


def test_paraphrase_warns_but_exits_zero(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE))
    assert r.exit_code == 0
    assert "WARNING" in r.output and MESSAGE in r.output


def test_strict_excerpts_makes_it_an_error(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE), "--strict-excerpts")
    assert r.exit_code == 1 and "ERROR" in r.output and "not found verbatim" in r.output
    assert "WARNING" not in r.output


def test_strict_escalates_the_warning_too(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE), "--strict")
    assert r.exit_code == 1 and "ERROR" in r.output and MESSAGE in r.output


def test_errors_only_hides_the_warning(tmp_path):
    # The workflow's gates run with --errors-only, so on 1.7.1 they never see it.
    run = _run(tmp_path, PARAPHRASE)
    r = _validate(run, "--errors-only")
    assert r.exit_code == 0 and r.output == ""
    r = _validate(run, "--errors-only", "--strict-excerpts")
    assert r.exit_code == 1 and MESSAGE in r.output


def test_missing_or_binary_artifact_is_skipped(tmp_path):
    assert check_excerpts_verbatim(_run(tmp_path / "a", None)) == []
    assert check_excerpts_verbatim(_run(tmp_path / "b", b"\xff\xfe\x00binary")) == []


def test_ellipsis_fragments_must_appear_in_order(tmp_path):  # Review Focus 4
    run = _run(tmp_path, "Topics use AES-256 at rest. Keys rotate yearly.\n" + CAP_EX)
    _set_excerpt(run, "Topics use AES-256 ... Keys rotate yearly")
    assert check_excerpts_verbatim(run) == []
    _set_excerpt_from(
        run, "Topics use AES-256 ... Keys rotate yearly", "Keys rotate yearly … Topics use AES-256"
    )
    assert len(check_excerpts_verbatim(run)) == 1


def test_each_ellipsis_fragment_is_searched_from_the_previous_match(tmp_path):
    run = _run(tmp_path, "alpha beta alpha\n" + CAP_EX)
    _set_excerpt(run, "alpha ... beta ... alpha")
    assert check_excerpts_verbatim(run) == []
    _set_excerpt_from(run, "alpha ... beta ... alpha", "beta ... alpha ... alpha")
    assert len(check_excerpts_verbatim(run)) == 1


def test_run_internal_artifacts_are_skipped(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "00-context/code-evidence-index.yaml").write_text("note: unrelated text\n")
    (run / "40-synthesis/attack-paths.yaml").write_text("note: unrelated text\n")
    (run / "inputs/other.md").write_text("unrelated text\n")
    # The control: the same unrelated text under inputs/ is read, so it would warn.
    _cite(run, "other.md")
    assert len(check_excerpts_verbatim(run)) == 1
    # The cited run-internal files exist and resolve, yet they are never read.
    _cite_from(run, "other.md", "00-context/code-evidence-index.yaml")
    assert check_excerpts_verbatim(run) == []
    _cite_from(run, "00-context/code-evidence-index.yaml", "40-synthesis/attack-paths.yaml")
    assert check_excerpts_verbatim(run) == []
    r = _validate(run)
    assert "not found verbatim" not in r.output


def test_paths_escaping_inputs_are_not_read(tmp_path):
    (tmp_path / "secret.md").write_text("unrelated text")
    run = _run(tmp_path, CAP_EX)
    _cite(run, "../secret.md")
    assert check_excerpts_verbatim(run) == []
    _cite_from(run, "../secret.md", "inputs/../00-context/context-brief.md")
    assert check_excerpts_verbatim(run) == []


def test_symlink_out_of_inputs_is_not_read(tmp_path):
    (tmp_path / "secret.md").write_text("unrelated text")
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/link.md").symlink_to(tmp_path / "secret.md")
    _cite(run, "link.md")
    assert check_excerpts_verbatim(run) == []


def test_artifact_cited_with_its_inputs_prefix_is_checked(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    _cite(run, "inputs/tech_plan.md")
    assert [v.message for v in check_excerpts_verbatim(run)] == [
        "evidence[0].excerpt not found verbatim in artifact 'inputs/tech_plan.md'"
    ]


def test_yaml_input_matches_parsed_scalars(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/kafka.yaml").write_text("note: 'it''s replicated: factor 3'\n")
    _cite(run, "kafka.yaml")
    _set_excerpt(run, "it's replicated: factor 3")
    assert check_excerpts_verbatim(run) == []


def test_json_input_matches_parsed_scalars(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/kafka.json").write_text(json.dumps({"note": 'quote " and \\ slash'}))
    _cite(run, "kafka.json")
    _set_excerpt(run, 'quote " and \\ slash')
    assert check_excerpts_verbatim(run) == []


def test_unparseable_yaml_input_falls_back_to_the_whole_text(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/kafka.yaml").write_text("key: [unclosed\n  replicated: factor 3\n")
    _cite(run, "kafka.yaml")
    _set_excerpt(run, "replicated: factor 3")
    assert check_excerpts_verbatim(run) == []


def test_tier_gate_reports_excerpt_violations(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    r = _validate(run, "--tier", "10-trustworthiness")
    assert r.exit_code == 0 and "WARNING" in r.output and "not found verbatim" in r.output
    r = _validate(run, "--tier", "10-trustworthiness", "--strict-excerpts")
    assert r.exit_code == 1 and "not found verbatim" in r.output


def test_tier_gate_json_carries_the_violation_by_severity(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    warned = json.loads(_validate(run, "--tier", "10-trustworthiness", "--json").output)
    assert warned["errors"] == [] and MESSAGE in warned["warnings"][0]["message"]
    strict = json.loads(
        _validate(run, "--tier", "10-trustworthiness", "--json", "--strict-excerpts").output
    )
    assert strict["warnings"] == [] and MESSAGE in strict["errors"][0]["message"]


def test_tier_gate_checks_only_its_own_records(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    (run / "20-scalability").mkdir(exist_ok=True)
    r = _validate(run, "--tier", "20-scalability", "--strict-excerpts")
    assert r.exit_code == 0 and "not found verbatim" not in r.output


def test_cross_file_pass_severity_follows_strict_excerpts(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    default = run_cross_file_pass(run)
    assert default.errors == [] and [v.message for v in default.warnings] == [MESSAGE]
    strict = run_cross_file_pass(run, strict_excerpts=True)
    assert strict.warnings == [] and [v.message for v in strict.errors] == [MESSAGE]


def test_schema_only_skips_the_check(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    assert "not found verbatim" not in _validate(run, "--schema-only").output
    r = _validate(run, "--schema-only", "--strict-excerpts")
    assert r.exit_code == 0 and "not found verbatim" not in r.output


# --- untrusted structured input: bounded work, never an exception ----------


def _laughs(payload: str) -> str:
    """An 8-level, 10-way alias fan-out ("billion laughs"): a few hundred bytes."""
    lines = [f"note: {json.dumps(payload)}", "l0: &l0 [" + ", ".join(['"lol"'] * 10) + "]"]
    lines += [f"l{n}: &l{n} [" + ", ".join([f"*l{n - 1}"] * 10) + "]" for n in range(1, 8)]
    return "\n".join(lines) + "\n"


def _nested(depth: int):
    return lambda payload: "[" * depth + json.dumps(payload) + "]" * depth


# Generous on purpose: a hostile input made the unfixed check hang for minutes or raise.
TIME_BOUND_S = 15

PATHOLOGICAL = {
    "recursive-anchor": ("rec.yaml", lambda p: f"note: {json.dumps(p)}\na: &a [*a]\n"),
    "deep-json-3000": ("deep.json", _nested(3_000)),
    "deep-json-100000": ("deep.json", _nested(100_000)),
    "deep-flow-yaml-3000": ("deep.yaml", _nested(3_000)),
    "alias-fan-out": ("laughs.yaml", _laughs),
}


def _run_structured(tmp_path, filename: str, body: str) -> Path:
    """A clean run whose only input, cited by the brief and both records, is ``filename``."""
    run = _run(tmp_path, None)
    for rel in (
        "00-context/context-brief.md",
        "10-trustworthiness/confidentiality.findings.yaml",
        "10-trustworthiness/confidentiality.capabilities.yaml",
    ):
        f = run / rel
        f.write_text(f.read_text().replace("tech_plan.md", filename))
    (run / "inputs" / filename).write_text(body)
    return run


@pytest.fixture
def parse_calls(monkeypatch):
    """Records each structured parse ``check_excerpts_verbatim`` starts."""
    calls: list[str] = []
    real_yaml, real_json = validate_mod.yaml.safe_load_all, validate_mod.json.loads

    def spy_yaml(*args, **kwargs):
        calls.append("yaml")
        return real_yaml(*args, **kwargs)

    def spy_json(*args, **kwargs):
        calls.append("json")
        return real_json(*args, **kwargs)

    monkeypatch.setattr(validate_mod.yaml, "safe_load_all", spy_yaml)
    monkeypatch.setattr(validate_mod.json, "loads", spy_json)
    return calls


@pytest.mark.parametrize("case", sorted(PATHOLOGICAL))
def test_pathological_input_with_a_whole_text_match_is_clean_and_never_parsed(
    tmp_path, parse_calls, case
):
    name, build = PATHOLOGICAL[case]
    run = _run_structured(tmp_path, name, build(f"{FINDING_EX} {CAP_EX}"))
    started = time.perf_counter()
    assert check_excerpts_verbatim(run) == []
    assert time.perf_counter() - started < TIME_BOUND_S
    assert parse_calls == []  # the whole-text haystack matched first; scalars are lazy


@pytest.mark.parametrize("case", sorted(PATHOLOGICAL))
def test_pathological_input_without_a_match_warns_and_never_fails_a_gate(tmp_path, case):
    name, build = PATHOLOGICAL[case]
    run = _run_structured(tmp_path, name, build("unrelated text"))
    started = time.perf_counter()
    assert len(check_excerpts_verbatim(run)) == 2
    assert time.perf_counter() - started < TIME_BOUND_S
    # The workflow's own gate commands: a warning-only check must never fail them.
    for flags in (("--errors-only",), ("--tier", "10-trustworthiness", "--errors-only")):
        r = _validate(run, *flags)
        assert r.exit_code == 0 and r.output == "", (flags, r.exception, r.output)
    r = _validate(run, "--strict-excerpts")
    assert r.exit_code == 1 and "not found verbatim" in r.output


def test_string_scalars_visits_each_container_once_and_respects_the_limit():
    loop: list = []
    loop.append(loop)
    loop.append("x")
    assert validate_mod._string_scalars(loop, 10) == ["x"]
    shared = ["s"]
    found = validate_mod._string_scalars([shared, shared, {"k": shared}], 100)
    assert sorted(found) == ["k", "s"]
    assert len(validate_mod._string_scalars([str(i) for i in range(50)], 7)) == 7


def test_structured_input_above_the_parse_cap_uses_only_the_whole_text(tmp_path, parse_calls):
    run = _run(tmp_path, CAP_EX)
    big = run / "inputs/big.yaml"
    big.write_text("note: 'it''s replicated: factor 3'\n" + "".join(
        f"k{i}: v{i}\n" for i in range(100_000)
    ))
    assert big.stat().st_size > validate_mod._MAX_STRUCTURED_PARSE_BYTES
    _cite(run, "big.yaml")
    _set_excerpt(run, "it's replicated: factor 3")  # matches a parsed scalar only
    assert len(check_excerpts_verbatim(run)) == 1
    _set_excerpt_from(run, "it's replicated: factor 3", "k99999: v99999")  # whole text
    assert check_excerpts_verbatim(run) == []
    assert parse_calls == []


def test_input_above_the_size_cap_is_skipped_without_being_read(tmp_path, monkeypatch):
    run = _run(tmp_path, CAP_EX)
    huge = run / "inputs/huge.md"
    with huge.open("wb") as f:  # sparse: no real 20 MiB written
        f.truncate(validate_mod._MAX_EXCERPT_INPUT_BYTES + 1)
    _cite(run, "huge.md")
    read: list[Path] = []
    real_read_text = Path.read_text

    def spy(self, *args, **kwargs):
        read.append(self.resolve())
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    assert check_excerpts_verbatim(run) == []  # a read would find only NULs and warn
    assert huge.resolve() not in read
