"""validate flags an evidence excerpt that is not verbatim in its cited input.

On 2.0 the CLI makes it an error by default; ``--no-strict-excerpts`` makes it a warning.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import apd_gauntlet.validate as validate_mod
import pytest
from apd_gauntlet.cli import main
from apd_gauntlet.composite import closeout_steps, tier_gate_steps
from apd_gauntlet.validate import (
    ValidationReport,
    add_excerpt_violations,
    check_excerpts_verbatim,
    excerpt_fragments,
    normalize_excerpt_text,
    run_cross_file_pass,
)
from click.testing import CliRunner

FIX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).parent.parent

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
    r = _validate(_run(tmp_path, PARAPHRASE), "--no-strict-excerpts")
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
    # The workflow's gates run with --errors-only: on 2.0 they see the error, and only
    # the escape hatch for runs made before 2.0 turns it back into a hidden warning.
    run = _run(tmp_path, PARAPHRASE)
    r = _validate(run, "--errors-only", "--no-strict-excerpts")
    assert r.exit_code == 0 and r.output == ""
    for flags in ((), ("--strict-excerpts",)):
        r = _validate(run, "--errors-only", *flags)
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
    r = _validate(run, "--tier", "10-trustworthiness", "--no-strict-excerpts")
    assert r.exit_code == 0 and "WARNING" in r.output and "not found verbatim" in r.output
    for flags in ((), ("--strict-excerpts",)):
        r = _validate(run, "--tier", "10-trustworthiness", *flags)
        assert r.exit_code == 1 and "ERROR" in r.output and "not found verbatim" in r.output


def test_tier_gate_json_carries_the_violation_by_severity(tmp_path):
    run = _run(tmp_path, PARAPHRASE)
    warned = json.loads(
        _validate(run, "--tier", "10-trustworthiness", "--json", "--no-strict-excerpts").output
    )
    assert warned["errors"] == [] and MESSAGE in warned["warnings"][0]["message"]
    for flags in ((), ("--strict-excerpts",)):
        strict = json.loads(_validate(run, "--tier", "10-trustworthiness", "--json", *flags).output)
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


def _scalar_alias_fan_out(payload: str) -> str:
    """One 10 KB anchored string, aliased 20,000 times (a ~90 KB file)."""
    big = json.dumps("word " * 2_000)
    return f"note: {json.dumps(payload)}\ns: &s {big}\nl: [{', '.join(['*s'] * 20_000)}]\n"


def _merge_key_chain(payload: str) -> str:
    """3,000 anchors, each merging the previous one (PyYAML flattens these quadratically)."""
    lines = [f"note: {json.dumps(payload)}", "m0: &m0 {k0: v0}"]
    lines += [f"m{n}: &m{n} {{<<: *m{n - 1}, k{n}: v{n}}}" for n in range(1, 3_000)]
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
    "scalar-alias-fan-out": ("scalar-aliases.yaml", _scalar_alias_fan_out),
    "merge-key-chain": ("merge-chain.yaml", _merge_key_chain),
}
# The YAML cases the alias/depth scan must keep away from the constructor.
UNPARSED_YAML_CASES = (
    "recursive-anchor",
    "alias-fan-out",
    "scalar-alias-fan-out",
    "merge-key-chain",
    "deep-flow-yaml-3000",
)


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
    # The workflow's own gate commands, with the escape hatch: a warning never fails them.
    # (Strict, the YAML cases still only warn: test_unparsed_pathological_yaml_never_fails_a_
    # strict_gate. A parsed JSON miss is an error, and whether 3,000 levels parse depends
    # on the Python version.)
    for flags in (("--errors-only",), ("--tier", "10-trustworthiness", "--errors-only")):
        r = _validate(run, *flags, "--no-strict-excerpts")
        assert r.exit_code == 0 and r.output == "", (flags, r.exception, r.output)
    r = _validate(run, "--strict")
    assert r.exit_code == 1 and "not found verbatim" in r.output


def test_string_scalars_visits_each_container_once_and_respects_the_limit():
    loop: list = []
    loop.append(loop)
    loop.append("x")
    assert validate_mod._string_scalars(loop, 10) == (["x"], False)
    shared = ["s"]
    found, truncated = validate_mod._string_scalars([shared, shared, {"k": shared}], 100)
    assert sorted(found) == ["k", "s"] and not truncated
    found, truncated = validate_mod._string_scalars([str(i) for i in range(50)], 7)
    assert len(found) == 7 and truncated  # the cap stopped the walk: values left untried
    found, truncated = validate_mod._string_scalars(["a1", "b2"], 2)
    assert sorted(found) == ["a1", "b2"] and not truncated  # at the cap, nothing left


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


@pytest.mark.parametrize("case", UNPARSED_YAML_CASES)
def test_yaml_with_aliases_or_deep_nesting_is_searched_as_plain_text_only(
    tmp_path, parse_calls, case
):
    name, build = PATHOLOGICAL[case]
    run = _run_structured(tmp_path, name, build("unrelated text"))
    started = time.perf_counter()
    assert len(check_excerpts_verbatim(run)) == 2
    assert time.perf_counter() - started < TIME_BOUND_S
    assert parse_calls == []  # never constructed: aliases amplify, deep nesting is slow to scan


def test_small_aliased_yaml_matches_only_through_its_whole_text(tmp_path, parse_calls):
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/aliased.yaml").write_text('x: &x "caf\\u00e9 ok"\ny: *x\n')
    _cite(run, "aliased.yaml")
    _set_excerpt(run, "café ok")  # the parsed value; the file spells it with an escape
    assert len(check_excerpts_verbatim(run)) == 1
    _set_excerpt_from(run, "café ok", "x: &x")  # a whole-text match still works
    assert check_excerpts_verbatim(run) == []
    assert parse_calls == []


def test_anchor_free_yaml_is_still_parsed_for_scalars(parse_calls):
    body = (
        'a: "caf\\u00e9 \\"quoted\\" ok"\n'
        "b: 'it''s replicated: factor 3'\n"
        "---\n"
        "c: [x, {d: 'second ''document'''}]\n"
    )
    source = validate_mod._ExcerptInput(body, parse_as=".yaml")
    for excerpt in ('café "quoted" ok', "it's replicated: factor 3", "second 'document'"):
        assert source.contains(excerpt_fragments(excerpt)), excerpt
    assert not source.contains(excerpt_fragments("not present anywhere"))
    assert parse_calls == ["yaml"]  # parsed once, then reused


def test_string_scalars_dedupes_a_shared_string_and_caps_total_characters():
    big = "x" * 1_000
    assert validate_mod._string_scalars([big] * 500, 10_000) == ([big], False)
    distinct = [str(i) * 10 for i in range(100)]
    found, truncated = validate_mod._string_scalars(distinct, 10_000, max_chars=50)
    assert 0 < len(found) < 100 and truncated
    assert sum(map(len, found)) < 50 + max(map(len, distinct))


# --- WS3 Task 8: strict by default on 2.0 (register A9.16, DEC-18) ---------

PARAPHRASE_PLAN = "Topics are encrypted with broker keys.\n" + CAP_EX
EXAMPLES = (
    "apd-20260601-claim-event-bus",
    "apd-20260602-acme-mobile-banking",
    "apd-20260612-home-assistant",
)


def _example_with_inputs(tmp_path, example: str) -> Path:
    """A copy of the example's ``expected/`` plus its ``inputs/``, so the check has artifacts."""
    run = tmp_path / example
    shutil.copytree(REPO / "examples" / example / "expected", run)
    shutil.copytree(REPO / "examples" / example / "inputs", run / "inputs")
    return run


def test_paraphrase_is_an_error_by_default_on_2_0(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE_PLAN))
    assert r.exit_code == 1 and "ERROR" in r.output
    assert "not found verbatim in artifact 'tech_plan.md'" in r.output


def test_no_strict_excerpts_downgrades_to_warning(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE_PLAN), "--no-strict-excerpts")
    assert r.exit_code == 0 and "WARNING" in r.output and "not found verbatim" in r.output


def test_tier_validate_reports_paraphrase_as_json_error(tmp_path):
    r = _validate(_run(tmp_path, PARAPHRASE_PLAN), "--tier", "10-trustworthiness", "--json")
    errors = json.loads(r.stdout)["errors"]
    assert r.exit_code == 1
    assert errors[0]["file"].endswith("10-trustworthiness/confidentiality.findings.yaml")


def test_tier_gate_is_strict_by_default_and_honours_the_escape_hatch(tmp_path):
    run = _run(tmp_path, PARAPHRASE_PLAN)

    def gate(*flags: str) -> int:
        argv = ["tier-gate", str(run), "--tier", "10-trustworthiness", *flags]
        return CliRunner().invoke(main, argv).exit_code

    assert (gate(), gate("--no-strict-excerpts")) == (1, 0)


def test_composites_forward_the_flag():
    tier = "10-trustworthiness"
    off = "--no-strict-excerpts"
    assert tier_gate_steps(Path("r"), tier, strict_excerpts=False)[-1].argv[-1] == off
    assert closeout_steps(Path("r"), strict_excerpts=False)[-1].argv[-1] == off
    assert off not in tier_gate_steps(Path("r"), tier)[-1].argv


def test_composites_forward_the_flag_in_json_mode_and_with_attempts():
    gate = tier_gate_steps(Path("r"), "t", json_output=True, strict_excerpts=False)[-1]
    assert gate.argv == ("validate", "r", "--tier", "t", "--json", "--no-strict-excerpts")
    close = closeout_steps(Path("r"), "{}", strict_excerpts=False)
    assert close[-1].argv == ("validate", "r", "--errors-only", "--no-strict-excerpts")
    assert close[1].argv == ("summarize", "r", "--record-attempts", "{}")
    # Only the validate step carries the flag; strict (the default) adds nothing.
    for steps in (tier_gate_steps(Path("r"), "t"), closeout_steps(Path("r"), "{}")):
        assert all("strict" not in " ".join(step.argv) for step in steps)


def test_closeout_is_strict_by_default_and_honours_the_escape_hatch(tmp_path):
    run = _run(tmp_path, PARAPHRASE_PLAN)
    strict = CliRunner().invoke(main, ["closeout", str(run)])
    assert "closeout: validate exit=1" in strict.output and MESSAGE in strict.output
    loose = CliRunner().invoke(main, ["closeout", str(run), "--no-strict-excerpts"])
    assert "closeout: validate exit=0" in loose.output and MESSAGE not in loose.output


@pytest.mark.parametrize("example", EXAMPLES)
def test_committed_examples_validate_strict(example, tmp_path):
    run = _example_with_inputs(tmp_path, example)  # item (d): the check has artifacts
    r = _validate(run, "--errors-only")
    assert r.exit_code == 0, r.output
    r = _validate(run, "--errors-only", "--strict-excerpts")
    assert r.exit_code == 0, r.output
    # Item (d)'s point: the inputs are there, and the check reads them.
    assert check_excerpts_verbatim(run) == []
    assert any((run / "inputs").rglob("*.md"))


def test_committed_example_excerpts_are_checked_against_their_inputs(tmp_path):
    # A control for the test above: break one excerpt that cites an inputs/ file.
    run = _example_with_inputs(tmp_path, "apd-20260601-claim-event-bus")
    f = next(
        p for p in sorted(run.glob("10-trustworthiness/*.findings.yaml"))
        if "artifact: tech_plan.md" in p.read_text()
    )
    text = f.read_text()
    marker = "artifact: tech_plan.md"
    head, tail = text.split(marker, 1)
    line_start = tail.index("excerpt:")
    line_end = tail.index("\n", line_start)
    f.write_text(head + marker + tail[:line_start] + 'excerpt: "not in the plan"' + tail[line_end:])
    r = _validate(run, "--errors-only")
    assert r.exit_code == 1 and "not found verbatim in artifact 'tech_plan.md'" in r.output


# Item (a): the matcher folds case and drops whitespace next to punctuation.


def test_normalize_folds_case_and_drops_whitespace_beside_punctuation():
    assert normalize_excerpt_text("**The Client** SIGNS") == "the client signs"
    assert normalize_excerpt_text("f(true, {\n  token: 1\n});") == "f(true,{token:1});"
    assert normalize_excerpt_text("a - b ,c") == "a-b,c"
    assert normalize_excerpt_text("a \t  ,\n  b") == "a,b"  # a mixed run, all of it
    # Whitespace between two words still counts, as one space.
    assert normalize_excerpt_text("rate \n limit") == "rate limit"
    assert normalize_excerpt_text("rate limit") != normalize_excerpt_text("ratelimit")
    assert normalize_excerpt_text("access_token") == "access_token"  # _ is a word character


def test_case_and_bold_markup_do_not_hide_a_quote(tmp_path):  # acme conf-4149d0db
    src = "- **The client signs each API request with an HMAC** using a shared secret\n" + CAP_EX
    run = _run(tmp_path, src)
    _set_excerpt(run, "the client signs each API request with an HMAC using a shared secret")
    assert check_excerpts_verbatim(run) == []


def test_whitespace_beside_punctuation_does_not_hide_a_quote(tmp_path):  # HA conf-3060c50e
    src = (
        'window.externalAuthSetToken(true, {\n  access_token: "qwere",\n  expires_in: 1800\n});\n'
        + CAP_EX
    )
    run = _run(tmp_path, src)
    # The finding's excerpt is a double-quoted YAML scalar, hence the escaped quotes.
    _set_excerpt(
        run, 'window.externalAuthSetToken(true, {access_token: \\"qwere\\", expires_in: 1800})'
    )
    assert check_excerpts_verbatim(run) == []


def test_a_different_word_is_still_a_miss(tmp_path):
    near_miss = FINDING_EX.replace("AES-256", "AES-128")
    run = _run(tmp_path, near_miss + "\n" + CAP_EX)
    assert [v.message for v in check_excerpts_verbatim(run)] == [MESSAGE]


@pytest.mark.parametrize("example, record_id", [
    ("apd-20260602-acme-mobile-banking", "conf-4149d0db"),
    ("apd-20260612-home-assistant", "conf-3060c50e"),
])
def test_observed_false_positives_now_match(example, record_id, tmp_path):
    run = _example_with_inputs(tmp_path, example)
    assert record_id not in {v.record_id for v in check_excerpts_verbatim(run)}


# A whitespace run in an untrusted input must cost time linear in its length: every gate
# normalizes each cited input. The first item (a) pattern backtracked through a run at each
# of its positions, so one million spaces took about an hour per gate.
LONG_SPACE_RUN = " " * 1_000_000


def _long_run_in_markdown(run: Path) -> None:
    # Between two words, the costly case: no punctuation ends the backtracking early.
    (run / "inputs/tech_plan.md").write_text(FINDING_EX + LONG_SPACE_RUN + CAP_EX + "\n")


def _long_run_in_a_parsed_scalar(run: Path) -> None:
    body = f"note: 'it''s replicated: factor 3'\npad: \"a{LONG_SPACE_RUN}b\"\n"
    (run / "inputs/padded.yaml").write_text(body)
    assert len(body) <= validate_mod._MAX_STRUCTURED_PARSE_BYTES  # parsed, not whole text only
    _cite(run, "padded.yaml")
    _list_in_brief(run, "padded.yaml")
    _set_excerpt(run, "it's replicated: factor 3")  # only a parsed scalar holds it


LONG_SPACE_RUN_INPUTS = {
    "whole-text": _long_run_in_markdown,
    "parsed-scalar": _long_run_in_a_parsed_scalar,
}


@pytest.mark.parametrize("case", sorted(LONG_SPACE_RUN_INPUTS))
def test_a_long_whitespace_run_is_normalized_in_linear_time(tmp_path, case):
    run = _run(tmp_path, CAP_EX)
    LONG_SPACE_RUN_INPUTS[case](run)
    # In a child process killed at the bound, so a regression fails here instead of
    # pinning the suite (subprocess.run raises TimeoutExpired).
    argv = [sys.executable, "-m", "apd_gauntlet.cli", "validate", "--errors-only", str(run)]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=TIME_BOUND_S)
    assert p.returncode == 0 and p.stdout == "", p.stdout + p.stderr
    started = time.perf_counter()
    assert check_excerpts_verbatim(run) == []
    assert time.perf_counter() - started < TIME_BOUND_S


# Item (f): a structured input searched only as whole text stays a warning.


def _list_in_brief(run: Path, name: str) -> None:
    """Add ``name`` to the brief's artifacts, so citing it is no semantic error."""
    brief = run / "00-context/context-brief.md"
    entry = "  - { filename: tech_plan.md, type: tech_plan }\n"
    added = entry + f"  - {{ filename: {name}, type: other }}\n"
    brief.write_text(brief.read_text().replace(entry, added))


def _big_yaml(run: Path) -> str:
    big = run / "inputs/big.yaml"
    big.write_text("note: 'it''s replicated: factor 3'\n" + "".join(
        f"k{i}: v{i}\n" for i in range(100_000)
    ))
    return "big.yaml"


def _aliased_yaml(run: Path) -> str:
    (run / "inputs/aliased.yaml").write_text("x: &x 'it''s replicated: factor 3'\ny: *x\n")
    return "aliased.yaml"


def _deep_yaml(run: Path) -> str:
    depth = validate_mod._MAX_YAML_DEPTH + 1
    note = "'it''s replicated: factor 3'"
    (run / "inputs/deep.yaml").write_text("[" * depth + note + "]" * depth + "\n")
    return "deep.yaml"


def _broken_yaml(run: Path) -> str:
    body = "key: [unclosed\n  note: 'it''s replicated: factor 3'\n"
    (run / "inputs/broken.yaml").write_text(body)
    return "broken.yaml"


def _broken_json(run: Path) -> str:
    # Deep JSON is no use here: Python 3.12 parses 3,000 levels, 3.10 and 3.11 raise.
    (run / "inputs/broken.json").write_text('{"note": "it\\u0027s replicated: factor 3",}')
    return "broken.json"


def _over_the_scalar_cap_json(run: Path) -> str:
    # Parsed, but the walk stops at _MAX_SCALAR_HAYSTACKS strings before it reaches the
    # note (it takes the last values first). Distinct strings: the walk counts each object once.
    pad = [f"{i:x}" for i in range(validate_mod._MAX_SCALAR_HAYSTACKS + 20_000)]
    body = '{"note": "it\\u0027s replicated: factor 3", "pad": '
    body += json.dumps(pad, separators=(",", ":")) + "}"
    assert len(body) <= validate_mod._MAX_STRUCTURED_PARSE_BYTES
    (run / "inputs/many.json").write_text(body)
    return "many.json"


# Each input's parsed values would hold the excerpt; its whole text never does.
WHOLE_TEXT_ONLY = {
    "over-the-parse-cap": _big_yaml,
    "over-the-scalar-cap": _over_the_scalar_cap_json,
    "yaml-alias": _aliased_yaml,
    "yaml-deeper-than-the-cap": _deep_yaml,
    "unparseable-yaml": _broken_yaml,
    "unparseable-json": _broken_json,
}


@pytest.mark.parametrize("case", sorted(WHOLE_TEXT_ONLY))
def test_structured_input_searched_as_whole_text_only_stays_a_warning(tmp_path, case):
    run = _run(tmp_path, CAP_EX)
    name = WHOLE_TEXT_ONLY[case](run)
    _cite(run, name)
    _list_in_brief(run, name)
    _set_excerpt(run, "it's replicated: factor 3")  # never in the whole text
    message = f"evidence[0].excerpt not found verbatim in artifact '{name}'"
    assert [v.message for v in check_excerpts_verbatim(run)] == [message]
    for flags in ((), ("--strict-excerpts",)):
        r = _validate(run, *flags)
        assert r.exit_code == 0, (flags, r.output)
        assert "WARNING" in r.output and message in r.output and "ERROR" not in r.output
        r = _validate(run, "--errors-only", *flags)
        assert r.exit_code == 0 and r.output == "", (flags, r.output)
        tier = json.loads(_validate(run, "--tier", "10-trustworthiness", "--json", *flags).stdout)
        assert tier["errors"] == [] and [w["message"] for w in tier["warnings"]] == [message]
    # --strict still turns every warning into an error.
    assert _validate(run, "--strict").exit_code == 1


def test_parsed_structured_input_miss_is_an_error_by_default(tmp_path):
    run = _run(tmp_path, CAP_EX)
    (run / "inputs/kafka.yaml").write_text("note: 'it''s replicated: factor 5'\n")
    _cite(run, "kafka.yaml")
    _list_in_brief(run, "kafka.yaml")
    _set_excerpt(run, "it's replicated: factor 3")
    r = _validate(run, "--errors-only")
    assert r.exit_code == 1
    assert "not found verbatim in artifact 'kafka.yaml'" in r.output


# JSON-family inputs the check does not parse: JSON lines, notebooks, GeoJSON, Terraform
# state, HAR, JSON with comments and JSON5. Each holds the escaped string
# "user \"admin\" logged in"; a lens quotes what it means, so the whole text never matches.
_ESCAPED_MSG = '"msg": "user \\"admin\\" logged in"'
JSON_FAMILY_INPUTS = {
    ".jsonl": "{" + _ESCAPED_MSG + '}\n{"msg": "other"}\n',
    ".ndjson": "{" + _ESCAPED_MSG + '}\n{"msg": "other"}\n',
    ".ipynb": json.dumps({"cells": [{"cell_type": "markdown",
                                     "source": ['user "admin" logged in']}]}),
    ".geojson": '{"type": "Feature", "properties": {' + _ESCAPED_MSG + "}}",
    ".tfstate": '{"version": 4, "outputs": {' + _ESCAPED_MSG + "}}",
    ".har": '{"log": {"entries": [{' + _ESCAPED_MSG + "}]}}",
    ".jsonc": "// a comment\n{" + _ESCAPED_MSG + "}\n",
    ".json5": "{" + _ESCAPED_MSG + ",}\n",
}


@pytest.mark.parametrize("suffix", sorted(JSON_FAMILY_INPUTS))
def test_json_family_input_miss_stays_a_warning_by_default(tmp_path, suffix):
    run = _run(tmp_path, CAP_EX)
    name = f"sample{suffix}"
    (run / "inputs" / name).write_text(JSON_FAMILY_INPUTS[suffix])
    assert 'user \\"admin\\" logged in' in (run / "inputs" / name).read_text()
    _cite(run, name)
    _list_in_brief(run, name)
    _set_excerpt(run, 'user \\"admin\\" logged in')  # YAML for: user "admin" logged in
    message = f"evidence[0].excerpt not found verbatim in artifact '{name}'"
    assert [v.message for v in check_excerpts_verbatim(run)] == [message]
    tier = _validate(run, "--tier", "10-trustworthiness", "--json")  # strict by default
    assert tier.exit_code == 0, tier.output
    report = json.loads(tier.stdout)
    assert report["errors"] == [] and [w["message"] for w in report["warnings"]] == [message]
    r = _validate(run, "--errors-only")
    assert r.exit_code == 0 and r.output == "", r.output


def test_add_excerpt_violations_keeps_whole_text_only_misses_as_warnings(tmp_path):
    run = _run(tmp_path, PARAPHRASE)  # the finding misses a Markdown input: strictable
    (run / "inputs/aliased.yaml").write_text("x: &x unrelated\ny: *x\n")
    f = run / "10-trustworthiness/confidentiality.capabilities.yaml"
    f.write_text(f.read_text().replace("artifact: tech_plan.md", "artifact: aliased.yaml"))
    strict = ValidationReport()
    add_excerpt_violations(strict, run, strict_excerpts=True)
    assert [v.message for v in strict.errors] == [MESSAGE]
    assert [v.message for v in strict.warnings] == [
        "evidence[0].excerpt not found verbatim in artifact 'aliased.yaml'"
    ]
    loose = ValidationReport()
    add_excerpt_violations(loose, run)  # the library default stays a warning
    assert loose.errors == [] and len(loose.warnings) == 2


@pytest.mark.parametrize("case", UNPARSED_YAML_CASES)
def test_unparsed_pathological_yaml_never_fails_a_strict_gate(tmp_path, case):
    name, build = PATHOLOGICAL[case]
    run = _run_structured(tmp_path, name, build("unrelated text"))
    gates = (
        ("--errors-only",),
        ("--errors-only", "--strict-excerpts"),
        ("--tier", "10-trustworthiness", "--errors-only"),
    )
    for flags in gates:
        r = _validate(run, *flags)
        assert r.exit_code == 0 and r.output == "", (flags, r.exception, r.output)
    argv = ["tier-gate", str(run), "--tier", "10-trustworthiness", "--json"]
    r = CliRunner().invoke(main, argv)
    assert r.exit_code == 0 and json.loads(r.stdout)["errors"] == [], r.output
