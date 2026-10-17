"""The workflow runner .claude/workflows/apd-gauntlet.js awaits every dispatch.

In the current Workflow runtime agent(prompt, opts) returns a Promise, and so does
parallel(thunks): a barrier that never rejects, where a failed thunk resolves to null.
A runner that does not await them inspects pending Promises. isErr() reads a Promise as
success, so every step "passes" at once, no agent finishes before the next is dispatched,
and the run dies at the report-audit gate with a misleading STRUCTURAL error.

Two kinds of test pin the fix:
  - node tests execute the REAL, WHOLE runner against a stub runtime whose agent()
    resolves on a later macrotask, and check what the runner dispatches, in what order,
    and which dispatches are in flight together. Each dispatch records the labels that
    were still in flight when it went out, and every such overlap must fall inside one
    of the parallel groups listed by hand below (a tier's lenses, a red tier's
    repairs). The tests also bound the maximum number in flight at once. They are
    skipped where node is absent (GitHub-hosted runners ship node, so CI enforces
    them), like _render_pystep_prompts in tests/test_workflow_apd_gauntlet.py;
  - static tests over the runner source (comments stripped, string contents blanked)
    check that every dispatch call is awaited, or is the returned expression of a
    function whose own callers await it, and that no callback is async (a
    forEach(async ...) callback is never awaited), so they hold where node is absent too.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
from typing import Any

import jsonschema
import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO / ".claude" / "workflows" / "apd-gauntlet.js"
RECEIPT_SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"

# The run-config the harness passes as `args`: no threat model and no crown jewels, so
# tm-recon is skipped and the apath thunk dispatches nothing; code_recon=auto runs it.
ARGS = {"run_id": "r1", "domains": ["pbm"], "framework_version": "1.7.1", "code_recon": "auto"}

# A success receipt that is valid for the RECEIPT shape (checked against the schema).
GENERIC_OK: dict[str, Any] = {"agent": "stub-agent", "status": "ok", "outputs": [], "counts": {}}

# What the resume-plan worker returns when `apd-gauntlet resume-plan` exits 3: the run
# directory was created by another framework major. The runner must halt on it.
RESUME_REFUSAL: dict[str, Any] = {
    "agent": "pystep:resume-plan",
    "status": "error",
    "outputs": [],
    "counts": {},
    "errors": [{
        "path": "resume-plan",
        "message": "exit=3; runs/r1 was created by framework 2.0.0; this engine is 1.7.1",
    }],
}

# Every label a green run dispatches, in the order the runner lists them, derived by hand
# from the script for ARGS and GENERIC_OK. resume-plan returns no resume_plan, so every
# agent step runs. Every gate is green, so no tier is repaired. The schema-less auditor
# answers an object, not a "GATE: pass" string, so the audit loop runs both remediations
# and ships with the non-blocking semantic residual.
EXPECTED_GREEN_LABELS = [
    # setup
    "resume-plan", "validate-scaffold", "build-domain-skill", "validate-domain",
    # intake
    "intake", "assemble-inventory", "intake-schema-gate",
    # code-recon (code_recon=auto)
    "code-recon", "canonicalize-code-evidence",
    # threat-model-author (tm-recon is skipped: no threat_model)
    "author-threat-model-floor", "threat-model-author",
    "canonicalize-threat-model",
    # tier-1/2/3: the lens fan-out, then canonicalize, then the tier gate
    "confidentiality", "integrity", "availability",
    "canonicalize-10-trustworthiness", "validate-10-trustworthiness",
    "distributed", "resilient", "ephemeral",
    "canonicalize-20-scalability", "validate-20-scalability",
    "authenticity", "non-repudiation", "immutability",
    "canonicalize-30-auditability", "validate-30-auditability",
    "validate-full-prephase5",
    # decomposed synthesis
    "cluster-candidates", "adjudicate", "apply-clusters",
    # tmeval (apath has no crown jewels), then assemble-c4 .. build
    "tmeval",
    "assemble-c4", "canonicalize-tmeval", "rollup",
    "report-writer-attempt-0", "build-report-attempt-0",
    # audit loop, cap N=2
    "audit-report-attempt-0", "auditor-attempt-0",
    "report-writer-attempt-1", "build-report-attempt-1",
    "audit-report-attempt-1", "auditor-attempt-1",
    "report-writer-attempt-2", "build-report-attempt-2",
    "audit-report-attempt-2", "auditor-attempt-2",
    # domain improvements, closeout
    "domain-coverage-delta", "domain-auditor", "canonicalize-dimpr",
    "summarize", "validate-final",
]

# The groups the runner dispatches in parallel, by label, written out by hand. Two
# dispatches may be in flight together only when both belong to one group. The
# tmeval/apath pair is not listed: apath dispatches nothing without crown jewels, so
# tmeval runs alone. A tier's lens re-runs only happen when its repairs did not help.
LENS_GROUPS = [
    ["confidentiality", "integrity", "availability"],
    ["distributed", "resilient", "ephemeral"],
    ["authenticity", "non-repudiation", "immutability"],
]
# The repairs the red-gate test drives: one per failing file, in failing-file order.
REPAIR_GROUP = [
    "repair-10-trustworthiness-confidentiality.findings.yaml",
    "repair-10-trustworthiness-integrity.capabilities.yaml",
]
# The most dispatches a run here has in flight at once: one tier's lens fan-out.
LARGEST_PARALLEL_GROUP = 3

# The stub runtime. __RESPONDER__, __ARGS__ and __BODY__ are filled in by _run_runner.
_HARNESS = r"""'use strict';
const dispatches = [];
const logs = [];
let inFlight = 0;
let maxInFlight = 0;
let resolvedCount = 0;
const respond = (__RESPONDER__);
function phase(name) {}
function log(message) { logs.push(String(message)); }
// Like the runtime: Promise.all over the thunks; a thunk that throws or rejects -> null.
function parallel(thunks) {
  return Promise.all(thunks.map(function (thunk) {
    return (async function () {
      try { return await thunk(); } catch (e) { return null; }
    })();
  }));
}
// The labels of the dispatches that are in flight, in dispatch order.
const live = [];
// Like the runtime: returns a Promise, resolved on a later macrotask. Each dispatch
// records `overlap`: the labels that were still in flight when it went out.
function agent(prompt, opts) {
  opts = opts || {};
  const n = dispatches.length;
  const label = opts.label === undefined ? null : opts.label;
  dispatches.push({
    label: label,
    agentType: opts.agentType === undefined ? null : opts.agentType,
    overlap: live.slice(),
  });
  live.push(label);
  inFlight += 1;
  if (inFlight > maxInFlight) { maxInFlight = inFlight; }
  return new Promise(function (resolve, reject) {
    setTimeout(function () {
      live.splice(live.indexOf(label), 1);
      inFlight -= 1;
      resolvedCount += 1;
      try { resolve(respond(prompt, opts, n)); } catch (e) { reject(e); }
    }, 0);
  });
}
const outcome = {
  finished: false, returned: false, threw: false, message: null, value: null,
  dispatchedAtFinish: null, resolvedAtFinish: null,
};
function settle() {
  outcome.finished = true;
  outcome.dispatchedAtFinish = dispatches.length;
  outcome.resolvedAtFinish = resolvedCount;
}
async function workflowBody(args) {
__BODY__
}
workflowBody(__ARGS__).then(
  function (value) {
    settle();
    outcome.returned = true;
    outcome.value = value === undefined ? null : value;
  },
  function (err) {
    settle();
    outcome.threw = true;
    outcome.message = String(err && err.message ? err.message : err);
  });
let reported = false;
process.on('beforeExit', function () {
  if (reported) { return; }
  reported = true;
  process.stdout.write(JSON.stringify(
    { outcome, dispatches, logs, maxInFlight, inFlight, resolvedCount }));
});
"""


def _text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def _responder(
    by_label: dict[str, dict[str, Any]] | None = None, reject: tuple[str, ...] = ()
) -> str:
    """JS source of a responder: the receipt for a dispatch's label, else GENERIC_OK.
    A label in `reject` throws instead, so that dispatch's Promise rejects.
    Every answer is a fresh copy, so the runner cannot share state between receipts."""
    return (
        "function (prompt, opts, n) {\n"
        f"  const byLabel = {json.dumps(by_label or {})};\n"
        f"  const fallback = {json.dumps(GENERIC_OK)};\n"
        f"  const reject = {json.dumps(list(reject))};\n"
        "  if (reject.indexOf(opts.label) !== -1) {\n"
        "    throw new Error('stub agent failed: ' + opts.label);\n"
        "  }\n"
        "  const has = Object.prototype.hasOwnProperty.call(byLabel, opts.label);\n"
        "  return JSON.parse(JSON.stringify(has ? byLabel[opts.label] : fallback));\n"
        "}"
    )


def _run_runner(tmp_path: pathlib.Path, responder: str) -> dict[str, Any]:
    """Execute the REAL, WHOLE runner under node against the stub runtime in _HARNESS.

    The script is read as-is; only the `export` keyword of `export const meta` is dropped,
    and the body is wrapped in an async function so its top-level await and return work.
    The runner does not call pipeline(), so the stub runtime does not define it. Returns
    the dispatches ({label, agentType, overlap}, in dispatch order, where overlap lists
    the labels still in flight when that dispatch went out), the log lines, the maximum
    number of dispatches in flight, and the outcome: whether the script finished, returned
    or threw (and the message), with the dispatch counts at the moment it finished."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    text = _text()
    assert text.count("export const meta") == 1
    body = text.replace("export const meta", "const meta", 1)
    assert not re.search(r"^\s*(?:export|import)\b", body, re.MULTILINE), (
        "the harness wraps a script body that has no other module syntax"
    )
    script = (
        _HARNESS.replace("__RESPONDER__", responder)
        .replace("__ARGS__", json.dumps(ARGS))
        .replace("__BODY__", body)
    )
    path = tmp_path / "run_runner.cjs"
    path.write_text(script, encoding="utf-8")
    proc = subprocess.run(
        [node, str(path)], capture_output=True, text=True, timeout=60, cwd=tmp_path
    )
    assert proc.returncode == 0, proc.stderr
    result: dict[str, Any] = json.loads(proc.stdout)
    return result


def _labels(result: dict[str, Any]) -> list[str]:
    return [d["label"] for d in result["dispatches"]]


def _assert_overlaps_within(result: dict[str, Any], groups: list[list[str]]) -> None:
    """Every dispatch that went out while others were in flight belongs, with all of
    them, to one of `groups`. Anything else ran alongside a step it should have waited
    for: a missing await, or an async callback that nobody awaits."""
    for d in result["dispatches"]:
        if not d["overlap"]:
            continue
        together = {d["label"], *d["overlap"]}
        assert any(together <= set(group) for group in groups), (
            f"{d['label']} was dispatched while these were still in flight: "
            + ", ".join(d["overlap"])
        )


def _overlap_of(result: dict[str, Any], label: str) -> list[str]:
    matches = [d["overlap"] for d in result["dispatches"] if d["label"] == label]
    assert len(matches) == 1, (label, len(matches))
    overlap: list[str] = matches[0]
    return overlap


def test_harness_receipts_match_the_receipt_schema() -> None:
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(GENERIC_OK, schema)
    jsonschema.validate(RESUME_REFUSAL, schema)


def test_listed_lens_groups_match_the_runner() -> None:
    """Guard the hand-written groups: they are the lens lists the runner's three
    runTier('tier-N', '<dir>', [...]) calls pass, in the same order."""
    tiers = re.findall(r"runTier\('tier-\d', '[^']+', \[([^\]]*)\]\)", _text())
    assert len(tiers) == 3, "runTier('tier-N', '<dir>', [...]) calls not found"
    assert [re.findall(r"'([^']+)'", lenses) for lenses in tiers] == LENS_GROUPS
    assert max(len(group) for group in LENS_GROUPS) == LARGEST_PARALLEL_GROUP


def test_resume_plan_refusal_halts_before_any_other_dispatch(tmp_path: pathlib.Path) -> None:
    result = _run_runner(tmp_path, _responder({"resume-plan": RESUME_REFUSAL}))
    outcome = result["outcome"]
    assert _labels(result) == ["resume-plan"], (
        "the runner dispatched past a resume-plan refusal: " + ", ".join(_labels(result)[:8])
    )
    assert outcome["finished"] and outcome["threw"], outcome
    assert "refusing to resume runs/r1" in outcome["message"], outcome["message"]
    assert "exit=3" in outcome["message"], outcome["message"]
    assert outcome["dispatchedAtFinish"] == outcome["resolvedAtFinish"] == 1, outcome


def test_green_run_dispatches_in_order_one_group_at_a_time(tmp_path: pathlib.Path) -> None:
    result = _run_runner(tmp_path, _responder())
    outcome = result["outcome"]
    labels = _labels(result)
    assert labels == EXPECTED_GREEN_LABELS, labels
    assert result["maxInFlight"] <= LARGEST_PARALLEL_GROUP, (
        f"{result['maxInFlight']} dispatches were in flight at once; the largest group the "
        f"runner runs in parallel is {LARGEST_PARALLEL_GROUP}"
    )
    _assert_overlaps_within(result, LENS_GROUPS)
    # Each tier's lens fan-out still runs concurrently: awaiting did not serialize it.
    for first, second, third in LENS_GROUPS:
        assert _overlap_of(result, third) == [first, second], result["dispatches"]
    assert result["maxInFlight"] == LARGEST_PARALLEL_GROUP, result["maxInFlight"]
    assert outcome["finished"] and outcome["returned"] and not outcome["threw"], outcome
    # Every dispatch had resolved by the time the script finished: nothing was left behind.
    assert outcome["dispatchedAtFinish"] == outcome["resolvedAtFinish"] == len(labels), outcome
    assert "apd-gauntlet runner: complete for r1." in result["logs"]


def test_failed_lens_is_retried_after_the_fan_out(tmp_path: pathlib.Path) -> None:
    # The lens and its first retry both fail, so the second retry must wait for the
    # first one, and canonicalize must wait for the second.
    failed = {"agent": "apd-integrity", "status": "error", "outputs": [], "counts": {}}
    jsonschema.validate(failed, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    result = _run_runner(
        tmp_path, _responder({"integrity": failed, "integrity-retry-1": failed})
    )
    labels = _labels(result)
    at = labels.index("confidentiality")
    assert labels[at:at + 7] == [
        "confidentiality", "integrity", "availability",
        "integrity-retry-1", "integrity-retry-2",
        "canonicalize-10-trustworthiness", "validate-10-trustworthiness",
    ], labels
    assert "integrity-retry-3" not in labels, labels
    assert result["maxInFlight"] <= LARGEST_PARALLEL_GROUP, result["maxInFlight"]
    _assert_overlaps_within(result, LENS_GROUPS)
    assert result["outcome"]["returned"], result["outcome"]


def test_rejected_lens_dispatch_becomes_null_and_is_retried(tmp_path: pathlib.Path) -> None:
    # The integrity dispatch rejects. parallel() maps it to null at its index, which
    # isErr() reads as a failure, so the lens is retried after the fan-out and the run
    # carries on instead of throwing.
    result = _run_runner(tmp_path, _responder(reject=("integrity",)))
    labels = _labels(result)
    at = labels.index("confidentiality")
    assert labels[at:at + 6] == [
        "confidentiality", "integrity", "availability",
        "integrity-retry-1",
        "canonicalize-10-trustworthiness", "validate-10-trustworthiness",
    ], labels
    assert "integrity-retry-2" not in labels, labels
    assert "tier 10-trustworthiness: lens integrity failed; retry 1/2." in result["logs"]
    _assert_overlaps_within(result, LENS_GROUPS)
    outcome = result["outcome"]
    assert outcome["finished"] and outcome["returned"] and not outcome["threw"], outcome


def test_red_tier_gate_is_repaired_before_the_next_tier(tmp_path: pathlib.Path) -> None:
    red = {
        "agent": "pystep:validate", "status": "error", "outputs": [], "counts": {},
        "errors": [
            {"path": "runs/r1/10-trustworthiness/confidentiality.findings.yaml",
             "message": "fnd-1 title: longer than 200 characters"},
            {"path": "runs/r1/10-trustworthiness/integrity.capabilities.yaml",
             "message": "cap-1 maturity: not one of the enum values"},
        ],
    }
    jsonschema.validate(red, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    result = _run_runner(tmp_path, _responder({"validate-10-trustworthiness": red}))
    labels = _labels(result)
    at = labels.index("validate-10-trustworthiness")
    assert labels[at:at + 6] == [
        "validate-10-trustworthiness",
        "repair-10-trustworthiness-confidentiality.findings.yaml",
        "repair-10-trustworthiness-integrity.capabilities.yaml",
        "canonicalize-10-trustworthiness-after-repair",
        "validate-10-trustworthiness-after-repair",
        "distributed",
    ], labels
    repairs = [d for d in result["dispatches"] if d["label"].startswith("repair-")]
    assert {d["agentType"] for d in repairs} == {"apd-tier-repair"}
    assert result["maxInFlight"] <= LARGEST_PARALLEL_GROUP, result["maxInFlight"]
    _assert_overlaps_within(result, LENS_GROUPS + [REPAIR_GROUP])
    # The repairs run in parallel with each other.
    assert _overlap_of(result, REPAIR_GROUP[1]) == [REPAIR_GROUP[0]], result["dispatches"]
    assert result["outcome"]["returned"], result["outcome"]


# ---------------------------------------------------------------------------
# Static: every dispatch call is awaited (holds where node is absent).
# ---------------------------------------------------------------------------

# The dispatch functions and the helpers that consume a dispatch result.
CALLS = ("agent", "pyStep", "llmStep", "tierGate", "regate", "repairTierGate", "runTier",
         "parallel")
# Plain functions that return agent()'s Promise (or llmStep's plain skip receipt); their
# callers await it. The node test in test_workflow_apd_gauntlet.py runs guard() and
# pyStep() with a SYNCHRONOUS stub agent(), so none of the three may await.
PASS_THROUGH = ("pyStep", "llmStep")
NO_AWAIT = ("guard", "pyStep", "llmStep")
ASYNC_HELPERS = ("tierGate", "regate", "repairTierGate", "runTier")


def _code(text: str) -> str:
    """The runner source with comments removed and string contents blanked to spaces.

    Offsets and newlines are preserved, so a position maps to the same line of the file.
    Quote characters stay; a template literal is treated as a plain string (the runner
    has none). The runner's regex literals hold no quote, '//' or '/*'."""
    out: list[str] = []
    i, n = 0, len(text)
    quote: str | None = None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and i + 1 < n:
                out.append("  " if text[i + 1] != "\n" else " \n")
                i += 2
                continue
            if c == quote:
                quote = None
                out.append(c)
            else:
                out.append("\n" if c == "\n" else " ")
            i += 1
            continue
        if c in "'\"`":
            quote = c
            out.append(c)
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    assert quote is None, "unterminated string literal: the comment stripper drifted"
    return "".join(out)


def _matching(code: str, open_at: int) -> int:
    """Index of the bracket that closes the one at open_at."""
    pairs = {"(": ")", "{": "}", "[": "]"}
    stack = [pairs[code[open_at]]]
    for i in range(open_at + 1, len(code)):
        c = code[i]
        if c in pairs:
            stack.append(pairs[c])
        elif c in ")}]":
            assert c == stack.pop(), f"unbalanced {c!r} at offset {i}"
            if not stack:
                return i
    raise AssertionError(f"no closing bracket for offset {open_at}")


def _fn_span(code: str, name: str) -> tuple[int, int]:
    """(start, end) of the body of the declaration `function name(...) { ... }`."""
    m = re.search(r"\bfunction\s+" + name + r"\s*\(", code)
    assert m, f"function {name}( not found"
    params_end = _matching(code, m.end() - 1)
    body_open = code.index("{", params_end)
    return body_open, _matching(code, body_open)


def _line(code: str, at: int) -> int:
    return code.count("\n", 0, at) + 1


def test_every_dispatch_is_awaited_or_returned_to_an_awaiting_caller() -> None:
    text = _text()
    code = _code(text)
    pass_through = [_fn_span(code, name) for name in PASS_THROUGH]
    # The argument span of every parallel(...) call: the thunks, whose results it awaits.
    thunks = [(m.end() - 1, _matching(code, m.end() - 1))
              for m in re.finditer(r"(?<![\w$.])parallel\s*\(", code)]
    assert thunks, "no parallel(...) call found"
    found = dict.fromkeys(CALLS, 0)
    offenders = []
    pattern = r"(?<![\w$.])(" + "|".join(CALLS) + r")\s*\("
    for m in re.finditer(pattern, code):
        before = code[:m.start()].rstrip()
        if re.search(r"\bfunction$", before):
            continue  # a declaration, not a call
        found[m.group(1)] += 1
        if re.search(r"\bawait$", before):
            continue
        returned = re.search(r"\breturn$", before) is not None
        inside = any(a < m.start() < b for a, b in pass_through + thunks)
        if returned and inside:
            continue
        line = _line(code, m.start())
        offenders.append(f"line {line}: {text.splitlines()[line - 1].strip()}")
    # Guard the scan: a regex that silently matched nothing would pass vacuously.
    assert all(found.values()), found
    assert sum(found.values()) >= 50, found
    assert not offenders, "dispatch calls that are not awaited:\n" + "\n".join(offenders)


def test_pass_through_functions_stay_synchronous() -> None:
    code = _code(_text())
    for name in NO_AWAIT:
        start, end = _fn_span(code, name)
        assert not re.search(r"\bawait\b", code[start:end]), f"{name}() must not await"
        assert not re.search(r"\basync\s+function\s+" + name + r"\b", code), (
            f"{name}() must stay a plain function"
        )


def test_helpers_that_consume_a_dispatch_are_async() -> None:
    code = _code(_text())
    for name in ASYNC_HELPERS:
        assert re.search(r"\basync\s+function\s+" + name + r"\s*\(", code), (
            f"{name}() reads a dispatch result, so it must be an async function"
        )


def test_no_other_function_is_async() -> None:
    """The four tier helpers are the only async functions. An async callback, such as
    forEach(async function ...) or .map(async ...), returns a Promise its caller never
    awaits, so the awaits inside it do not hold the run back: the next step goes out
    while the callback's dispatch is still in flight."""
    code = _code(_text())
    uses = list(re.finditer(r"\basync\b", code))
    names = []
    for m in uses:
        decl = re.match(r"async\s+function\s+([\w$]+)\s*\(", code[m.start():])
        if decl is None:
            line = _line(code, m.start())
            pytest.fail(f"line {line}: async callback: {_text().splitlines()[line - 1].strip()}")
        names.append(decl.group(1))
    assert sorted(names) == sorted(ASYNC_HELPERS), names
