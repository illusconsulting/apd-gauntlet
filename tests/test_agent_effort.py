"""Every agent sets `effort`; `model` stays as it is until WS5 Task 23.

The effort values come from the cost audit's Wave 3 Effort column, with the tier-repair
row from the coordinator (WS3 plan, Global Constraints). WS3 keeps today's models and
leaves `model` absent where it is absent today; an absent `model` is `None` here.
"""
from __future__ import annotations

import pathlib
from typing import Any

import pytest
import yaml
from apd_gauntlet import lint_agents
from apd_gauntlet.lint_agents import FRONTMATTER_PATTERN, lint_agent_file

REPO = pathlib.Path(__file__).resolve().parent.parent
AGENTS = REPO / ".claude" / "agents"

# (model as WS3 leaves it, effort per Global Constraints)
LENSES = ["confidentiality", "integrity", "availability", "distributed", "resilient",
          "ephemeral", "authenticity", "non-repudiation", "immutability"]
EXPECTED = {f"apd-{lens}": (None, "medium") for lens in LENSES} | {
    "apd-cli-runner": ("haiku", "low"), "apd-tier-repair": ("sonnet", "low"),
    "apd-intake": (None, "medium"), "apd-code-recon": (None, "medium"),
    "apd-threat-model-author": ("opus", "medium"), "apd-threat-model-recon": (None, "low"),
    "apd-threat-model-evaluator": (None, "high"), "apd-attack-path-analyzer": ("opus", "medium"),
    "apd-cluster-adjudicator": ("opus", "high"), "apd-report-writer": ("opus", "medium"),
    "apd-report-auditor": ("opus", "high"), "apd-domain-auditor": ("opus", "medium"),
    "apd-synthesizer": (None, "high")}


def _frontmatter(path: pathlib.Path) -> dict[str, Any]:
    m = FRONTMATTER_PATTERN.match(path.read_text(encoding="utf-8"))
    assert m is not None, f"{path.name} has no YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert isinstance(meta, dict), path.name
    return meta


def test_every_agent_has_expected_model_and_effort():
    files = sorted(AGENTS.glob("*.md"))
    assert {f.stem for f in files} == set(EXPECTED)
    for f in files:
        meta = _frontmatter(f)
        assert (meta.get("model"), meta.get("effort")) == EXPECTED[f.stem], f.name


@pytest.mark.parametrize(("extra", "needle"), [
    ("", "missing 'effort'"),
    ("effort: extreme\n", "effort 'extreme'"),
    ("effort: low\nmodel: opsu\n", "model 'opsu'"),
])
def test_lint_effort_and_model_rules(tmp_path, extra, needle):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: x\n" + extra + "---\n\n## Final message\n")
    assert any(needle in e for e in lint_agent_file(a, tmp_path))


def test_allowed_values_are_the_claude_code_frontmatter_values():
    assert lint_agents.ALLOWED_EFFORT == ("low", "medium", "high", "xhigh", "max")
    assert lint_agents.MODEL_ALIASES == ("sonnet", "opus", "haiku", "fable", "inherit")
    assert lint_agents.FULL_MODEL_ID.pattern == r"^claude-[a-z0-9.-]+$"


def _lint(tmp_path: pathlib.Path, extra: str) -> list[str]:
    a = tmp_path / "apd-x.md"
    a.write_text("---\nname: apd-x\ndescription: x\ntools: Read\n" + extra
                 + "---\n\n## Final message\n")
    return lint_agent_file(a, tmp_path)


def test_lint_effort_and_model_error_texts(tmp_path):
    a = tmp_path / "apd-x.md"
    assert _lint(tmp_path, "") == [f"{a}: frontmatter missing 'effort'"]
    assert _lint(tmp_path, "effort: extreme\n") == [
        f"{a}: effort 'extreme' is not one of low, medium, high, xhigh, max"]
    assert _lint(tmp_path, "effort: low\nmodel: opsu\n") == [
        f"{a}: model 'opsu' is not an alias or full model id"]


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_every_allowed_effort_lints_clean(tmp_path, effort):
    assert _lint(tmp_path, f"effort: {effort}\n") == []


@pytest.mark.parametrize("model", ["sonnet", "opus", "haiku", "fable", "inherit",
                                   "claude-opus-4-1", "claude-sonnet-4-5-20250929",
                                   "claude-3.5-haiku"])
def test_model_aliases_and_full_ids_lint_clean(tmp_path, model):
    assert _lint(tmp_path, f"effort: medium\nmodel: {model}\n") == []


def test_model_stays_optional(tmp_path):
    # WS5 Task 23 makes `model` required; until then an absent `model` is clean.
    assert _lint(tmp_path, "effort: medium\n") == []


@pytest.mark.parametrize("value", ["", ' ""'], ids=["null", "empty-string"])
def test_an_empty_effort_is_missing(tmp_path, value):
    # `effort:` with no value parses to None; both count as missing, as for `description`.
    assert _lint(tmp_path, f"effort:{value}\n") == [
        f"{tmp_path / 'apd-x.md'}: frontmatter missing 'effort'"]


@pytest.mark.parametrize("extra", [
    "effort: Low\n",            # case matters: Claude Code reads the lowercase values
    "effort: [low]\n",          # not a string
    "effort: 2\n",
])
def test_effort_must_be_an_allowed_string(tmp_path, extra):
    errors = _lint(tmp_path, extra)
    assert len(errors) == 1 and "is not one of low, medium, high, xhigh, max" in errors[0]


@pytest.mark.parametrize("model", [
    "Opus",                     # case matters
    "gpt-4o",                   # not a Claude model id
    "claude-",                  # no id after the prefix
    "claude-Opus-4",            # upper case in the id
    "claude-opus 4",            # a space
    '"claude-opus-4\\n"',       # a trailing newline
    "''",                       # empty string
    "",                         # `model:` with no value
    "[opus]",                   # not a string
])
def test_model_must_be_an_alias_or_full_id(tmp_path, model):
    errors = _lint(tmp_path, f"effort: low\nmodel: {model}\n")
    assert len(errors) == 1 and "is not an alias or full model id" in errors[0], errors


def test_missing_effort_is_reported_with_the_other_frontmatter_errors(tmp_path):
    a = tmp_path / "apd-x.md"
    a.write_text("---\nother_key: value\n---\n\n## Final message\n")
    assert lint_agent_file(a, tmp_path) == [
        f"{a}: frontmatter missing 'name'",
        f"{a}: frontmatter missing 'description'",
        f"{a}: frontmatter missing 'tools'",
        f"{a}: frontmatter missing 'effort'",
    ]
