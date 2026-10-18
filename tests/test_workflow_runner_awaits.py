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
import shlex
import shutil
import subprocess
from typing import Any

import jsonschema
import pytest
import yaml
from apd_gauntlet.cli import main
from click.testing import CliRunner

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
    "resume-plan", "prepare-run",
    # intake
    "intake", "assemble-inventory", "intake-schema-gate",
    # code-recon (code_recon=auto)
    "code-recon", "canonicalize-code-evidence",
    # threat-model-author (tm-recon is skipped: no threat_model)
    "author-threat-model-floor", "threat-model-author",
    "canonicalize-threat-model",
    # tier-1/2/3: the lens fan-out, then the tier gate (canonicalize, then validate)
    "confidentiality", "integrity", "availability",
    "tier-gate-10-trustworthiness",
    "distributed", "resilient", "ephemeral",
    "tier-gate-20-scalability",
    "authenticity", "non-repudiation", "immutability",
    "tier-gate-30-auditability",
    "validate-full-prephase5",
    # decomposed synthesis
    "cluster-candidates", "adjudicate", "apply-clusters",
    # tmeval (apath has no crown jewels), then post-tier4 (assemble-c4, canonicalize,
    # rollup) .. build
    "tmeval",
    "post-tier4",
    "report-writer-attempt-0", "build-report-attempt-0",
    # audit loop, cap N=2
    "audit-report-attempt-0", "auditor-attempt-0",
    "report-writer-attempt-1", "build-report-attempt-1",
    "audit-report-attempt-1", "auditor-attempt-1",
    "report-writer-attempt-2", "build-report-attempt-2",
    "audit-report-attempt-2", "auditor-attempt-2",
    # domain improvements, closeout (canonicalize, summarize, manual-audit-prompts, validate)
    "domain-coverage-delta", "domain-auditor",
    "closeout",
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
    by_label: dict[str, Any] | None = None, reject: tuple[str, ...] = ()
) -> str:
    """JS source of a responder: the answer for a dispatch's label (a receipt, or the
    schema-less auditor's critique string), else GENERIC_OK.
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
    # first one, and the tier gate must wait for the second.
    failed = {"agent": "apd-integrity", "status": "error", "outputs": [], "counts": {}}
    jsonschema.validate(failed, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    result = _run_runner(
        tmp_path, _responder({"integrity": failed, "integrity-retry-1": failed})
    )
    labels = _labels(result)
    at = labels.index("confidentiality")
    assert labels[at:at + 6] == [
        "confidentiality", "integrity", "availability",
        "integrity-retry-1", "integrity-retry-2",
        "tier-gate-10-trustworthiness",
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
    assert labels[at:at + 5] == [
        "confidentiality", "integrity", "availability",
        "integrity-retry-1",
        "tier-gate-10-trustworthiness",
    ], labels
    assert "integrity-retry-2" not in labels, labels
    assert "tier 10-trustworthiness: lens integrity failed; retry 1/2." in result["logs"]
    _assert_overlaps_within(result, LENS_GROUPS)
    outcome = result["outcome"]
    assert outcome["finished"] and outcome["returned"] and not outcome["threw"], outcome


def test_red_tier_gate_is_repaired_before_the_next_tier(tmp_path: pathlib.Path) -> None:
    red = {
        "agent": "pystep:tier-gate", "status": "error", "outputs": [], "counts": {},
        "errors": [
            {"path": "runs/r1/10-trustworthiness/confidentiality.findings.yaml",
             "message": "fnd-1 title: longer than 200 characters"},
            {"path": "runs/r1/10-trustworthiness/integrity.capabilities.yaml",
             "message": "cap-1 maturity: not one of the enum values"},
        ],
    }
    jsonschema.validate(red, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    result = _run_runner(tmp_path, _responder({"tier-gate-10-trustworthiness": red}))
    labels = _labels(result)
    at = labels.index("tier-gate-10-trustworthiness")
    assert labels[at:at + 5] == [
        "tier-gate-10-trustworthiness",
        "repair-10-trustworthiness-confidentiality.findings.yaml",
        "repair-10-trustworthiness-integrity.capabilities.yaml",
        "tier-gate-10-trustworthiness-after-repair",
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


# ---------------------------------------------------------------------------
# WS2 Task 7: the attempts the closeout step records (node). The runner counts lens
# retries, first-pass failures, skips, tier repairs and audit iterations, and the
# closeout worker is told to pass them to `closeout --record-attempts`, whose summarize
# step writes them (WS3 Task 3). These tests run the command that worker is given.
# ---------------------------------------------------------------------------

# The responder logs the closeout prompt after this mark.
CLOSEOUT_MARK = "closeout prompt:\n"
LENSES = [lens for group in LENS_GROUPS for lens in group]
FAILED_INTEGRITY: dict[str, Any] = {
    "agent": "apd-integrity", "status": "error", "outputs": [], "counts": {},
}


def _recording_responder(
    by_label: dict[str, Any] | None = None, reject: tuple[str, ...] = ()
) -> str:
    """_responder, which also logs the prompt of the dispatch labelled `closeout`."""
    return (
        "function (prompt, opts, n) {\n"
        f"  if (opts.label === 'closeout') {{ log({json.dumps(CLOSEOUT_MARK)} + prompt); }}\n"
        f"  return ({_responder(by_label, reject)})(prompt, opts, n);\n"
        "}"
    )


def _recorded_attempts(tmp_path: pathlib.Path, result: dict[str, Any]) -> dict[str, Any]:
    """Run the command the closeout prompt names, split as a shell splits it, against an
    empty run directory, and return the attempts.yaml its summarize step writes. The
    file must hold exactly the object the command passed."""
    prompts = [line for line in result["logs"] if line.startswith(CLOSEOUT_MARK)]
    assert len(prompts) == 1, result["logs"]
    # The apd-cli-runner runs the prompt's COMMAND: line (WS3 Task 1).
    commands = [line[len("COMMAND: "):] for line in prompts[0].splitlines()
                if line.startswith("COMMAND: apd-gauntlet closeout ")]
    assert len(commands) == 1, prompts[0]
    argv = shlex.split(commands[0])
    assert argv[:4] == ["apd-gauntlet", "closeout", "runs/r1", "--record-attempts"], argv
    assert len(argv) == 5, argv
    run = tmp_path / "run"
    run.mkdir()
    r = CliRunner().invoke(main, ["closeout", str(run), *argv[3:]])
    # An empty run directory has no synthesis output, so later closeout steps fail;
    # the summarize step, which records the attempts, must not.
    assert "closeout: summarize exit=0" in r.stderr.splitlines(), r.output
    written = yaml.safe_load((run / ".apd-state" / "attempts.yaml").read_text(encoding="utf-8"))
    assert written == json.loads(argv[4])
    recorded: dict[str, Any] = written
    return recorded


def _red_gate(tier_dir: str, files: list[str]) -> dict[str, Any]:
    gate = {
        "agent": "pystep:tier-gate", "status": "error", "outputs": [], "counts": {},
        "errors": [{"path": f"runs/r1/{tier_dir}/{f}", "message": "fnd-1 title: too long"}
                   for f in files],
    }
    jsonschema.validate(gate, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    return gate


def test_green_run_records_attempts_at_closeout(tmp_path: pathlib.Path) -> None:
    result = _run_runner(tmp_path, _recording_responder())
    assert result["outcome"]["returned"], result["outcome"]
    (prompt,) = [line for line in result["logs"] if line.startswith(CLOSEOUT_MARK)]
    assert "Always run this command; this step has no idempotency check and no skip." in prompt
    # The schema-less auditor never answers "GATE: pass" here, so all three audit
    # attempts run.
    assert _recorded_attempts(tmp_path, result) == {
        "schema_version": 1, "recorded_by": "workflow",
        "lens_retries": dict.fromkeys(LENSES, 0),
        "first_pass_invalid": [], "tier_gate_failures": [], "skipped": [],
        "audit_iterations": 3, "tier_repairs": {}, "lens_reruns": {},
    }


def test_attempts_count_lens_retries_and_first_pass_failures(tmp_path: pathlib.Path) -> None:
    # integrity and its first retry fail (2 retries); the distributed dispatch rejects,
    # so parallel() gives null (1 retry); confidentiality answers ok but lists an output
    # that failed schema validation (first-pass invalid, never retried).
    invalid = {
        "agent": "apd-confidentiality", "status": "ok", "counts": {},
        "outputs": [{"path": "runs/r1/10-trustworthiness/confidentiality.findings.yaml",
                     "schema_valid": False}],
    }
    jsonschema.validate(invalid, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    result = _run_runner(tmp_path, _recording_responder(
        {"integrity": FAILED_INTEGRITY, "integrity-retry-1": FAILED_INTEGRITY,
         "confidentiality": invalid},
        reject=("distributed",),
    ))
    assert result["outcome"]["returned"], result["outcome"]
    attempts = _recorded_attempts(tmp_path, result)
    assert attempts["lens_retries"] == {**dict.fromkeys(LENSES, 0), "integrity": 2,
                                        "distributed": 1}
    assert attempts["first_pass_invalid"] == ["confidentiality", "integrity", "distributed"]
    assert attempts["skipped"] == [] and attempts["tier_gate_failures"] == []


def test_resumed_lens_is_recorded_as_skipped(tmp_path: pathlib.Path) -> None:
    # resume-plan reports the confidentiality lens complete, so llmStep returns the skip
    # sentinel without dispatching it.
    resumed = {
        "agent": "pystep:resume-plan", "status": "ok", "outputs": [], "counts": {},
        "resume_plan": {"engine_version": "1.7.1", "steps": [
            {"label": "confidentiality", "complete": True, "reason": "outputs valid"},
            {"label": "integrity", "complete": False, "reason": "missing"},
        ]},
    }
    jsonschema.validate(resumed, json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8")))
    result = _run_runner(tmp_path, _recording_responder({"resume-plan": resumed}))
    assert "confidentiality" not in _labels(result)
    attempts = _recorded_attempts(tmp_path, result)
    assert attempts["skipped"] == ["confidentiality"]
    assert attempts["first_pass_invalid"] == []
    assert attempts["lens_retries"] == dict.fromkeys(LENSES, 0)


def test_attempts_count_the_tier_repair_loop(tmp_path: pathlib.Path) -> None:
    # Tier 1 stays red after the repair, so both lenses that own a red file are re-run.
    # Tier 3 is green after its one repair. Only the first gate of a tier is a failure.
    red_1 = _red_gate("10-trustworthiness",
                      ["confidentiality.findings.yaml", "integrity.capabilities.yaml"])
    red_3 = _red_gate("30-auditability", ["immutability.findings.yaml"])
    result = _run_runner(tmp_path, _recording_responder({
        "tier-gate-10-trustworthiness": red_1,
        "tier-gate-10-trustworthiness-after-repair": red_1,
        "tier-gate-30-auditability": red_3,
    }))
    labels = _labels(result)
    assert {"confidentiality-rerun", "integrity-rerun"} <= set(labels), labels
    assert result["outcome"]["returned"], result["outcome"]
    attempts = _recorded_attempts(tmp_path, result)
    assert attempts["tier_gate_failures"] == ["10-trustworthiness", "30-auditability"]
    assert attempts["tier_repairs"] == {"10-trustworthiness": 2, "30-auditability": 1}
    assert attempts["lens_reruns"] == {"confidentiality": 1, "integrity": 1}
    assert attempts["lens_retries"] == dict.fromkeys(LENSES, 0)


@pytest.mark.parametrize("passing_attempt", [0, 1])
def test_audit_iterations_stop_at_the_passing_attempt(
    tmp_path: pathlib.Path, passing_attempt: int
) -> None:
    result = _run_runner(tmp_path, _recording_responder(
        {f"auditor-attempt-{passing_attempt}": "GATE: pass"}
    ))
    labels = _labels(result)
    assert f"auditor-attempt-{passing_attempt + 1}" not in labels, labels
    assert _recorded_attempts(tmp_path, result)["audit_iterations"] == passing_attempt + 1


def test_halted_run_records_no_attempts(tmp_path: pathlib.Path) -> None:
    # A tier that is still red after the lens re-run halts the run before closeout, so
    # closeout is never dispatched and no attempts file is written.
    red = _red_gate("10-trustworthiness", ["confidentiality.findings.yaml"])
    result = _run_runner(tmp_path, _recording_responder({
        "tier-gate-10-trustworthiness": red,
        "tier-gate-10-trustworthiness-after-repair": red,
        "tier-gate-10-trustworthiness-after-rerun": red,
    }))
    assert result["outcome"]["threw"], result["outcome"]
    assert "closeout" not in _labels(result)
    assert not [line for line in result["logs"] if line.startswith(CLOSEOUT_MARK)]
