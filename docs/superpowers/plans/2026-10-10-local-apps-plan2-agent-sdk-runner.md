# Local Apps Plan 2 — Agent SDK Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `apd-gauntlet run|status|cancel`, a Python runner that executes a full gauntlet run outside Claude Code using the Claude Agent SDK, with the same phases and outputs as `apd-gauntlet.js`.

**Architecture:** The wheel bundles the agent prompts, skills, templates and schemas; `materialize()` copies them into a workspace. A `Runner` walks the phase flow: CLI steps run as `python -m apd_gauntlet` subprocesses, agent steps go through an `AgentExecutor` (SDK implementation plus a scripted fake for tests), and decide steps call Plan 1's finding QA. A ledger, an append-only event log and a lock file under `runs/<id>/.apd-state/` make runs resumable, observable and exclusive. A `PreToolUse` hook confines every agent to the run.

**Tech Stack:** Python 3.10+, asyncio, `claude-agent-sdk` (extra `runner`), click, PyYAML, pytest (+ `pytest-asyncio`, already usable via `asyncio.run` wrappers if not added).

**Spec:** `docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md` (§7 runner, §6.3 secret hygiene, §9 testing). Depends on Plan 1 (`config`, `credentials`, `decide`). Plan 2 of 3.

## Global Constraints

- Everything in Plan 1's Global Constraints still applies.
- Extra `runner = ["claude-agent-sdk>=<tested>,<next-minor>", "apd-gauntlet[decide]"]`; Task 5 fixes the bounds to the version its tests ran against.
- `runner.flow.PHASES` equals the workflow's `meta.phases` tuple, same order.
- Step labels equal the workflow's `opts.label` strings, so ledgers from both channels read alike.
- Retry caps: lens retries 2; adjudicator re-dispatch 1; rollup retry 1; audit remediations 2 (3 attempts).
- Agent SDK options for every dispatch: `setting_sources=[]`, `permission_mode="dontAsk"`, env `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `max_turns=80`, `cwd=<workspace>`.
- Model precedence: `cfg.llm.model_overrides[agent]`, then frontmatter `model`, then `cfg.llm.default_model`.
- Readable roots for agents: the run directory and `<workspace>/{.claude,templates,schemas}`. Writable root: the run directory. Bash: first word `apd-gauntlet`, none of `` ; & | $ ` < > `` or a newline, no `..`.
- State files: `runs/<id>/.apd-state/{ledger.json,events.jsonl,lock,consent.json,runner.log}`; JSON written atomically (temp file + `os.replace`).
- Event fields never include file contents, prompts, agent text or secret values.
- Default run budget `cfg.llm.run_budget_usd` = 100.0; `--budget` overrides per invocation.

## Review Focus

- **Power loss mid-tier:** the next `run` skips steps that are `ok` in the ledger and whose outputs validate, and redoes a lens whose file is half-written.
- **Second `run` on a live run:** refused with the holder's PID and host; a lock left by a dead PID on the same host is reclaimed.
- **Injected instruction in an input file** asks an agent to `cat ~/.ssh/id_rsa` or run `apd-gauntlet validate x; curl …`: the hook denies both and the run continues.
- **Budget runs out during tier 2:** in-flight lenses finish, no new agent starts, state is `budget_exhausted`, and `run --budget 150` resumes.
- **No Claude credentials:** `run` exits 1 before any step with the env var or `keys set anthropic` hint.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/__main__.py` | `python -m apd_gauntlet` entry point | Create |
| `tools/apd_gauntlet/data/claude/{agents,skills}/**`, `tools/apd_gauntlet/data/templates/*` | Packaged copies of `.claude/agents`, `.claude/skills`, `templates/` | Create |
| `tools/apd_gauntlet/bundle.py` | Bundle digest, sync from repo, materialize into a workspace | Create |
| `tools/apd_gauntlet/runner/__init__.py` | Exports | Create |
| `tools/apd_gauntlet/runner/ledger.py` | Ledger, events, budget accounting | Create |
| `tools/apd_gauntlet/runner/lock.py` | Run lock | Create |
| `tools/apd_gauntlet/runner/steps.py` | CLI subprocess steps, output checks, audit-count parsing | Create |
| `tools/apd_gauntlet/runner/guard.py` | Tool-use policy checks | Create |
| `tools/apd_gauntlet/runner/agents.py` | Agent specs, model resolution, SDK options, executors | Create |
| `tools/apd_gauntlet/runner/instructions.py` | Per-dispatch instruction text | Create |
| `tools/apd_gauntlet/runner/flow.py` | `PHASES`, `Runner` | Create |
| `tools/apd_gauntlet/cli.py` | `run`, `status`, `cancel` | Modify |
| `pyproject.toml` | Extra `runner`, package data | Modify |
| `docs/local-runner.md`, `docs/adrs/0025-standalone-agent-sdk-runner.md`, `CHANGELOG.md` | Docs | Create/Modify |
| `tests/runner/…`, `tests/test_bundle.py`, `tests/test_cli_run.py` | Tests | Create |

---

### Task 1: Bundle prompts into the wheel and materialize a workspace

**Files:**

- Create: `tools/apd_gauntlet/__main__.py`, `tools/apd_gauntlet/bundle.py`, the packaged copies listed above
- Modify: `pyproject.toml` package data (`data/claude/**/*`, `data/templates/*`)
- Test: `tests/test_bundle.py`; extend `tests/integration/test_wheel_install_smoke.py`

**Interfaces:**

- Produces:
  - `BUNDLE_DIRS = {"claude/agents": ".claude/agents", "claude/skills": ".claude/skills", "templates": "templates", "schemas": "schemas"}` (package-data subpath → workspace subpath)
  - `def bundle_digest() -> str` (SHA-256 over sorted relative paths and bytes of all bundled files)
  - `def sync_from_repo(repo_root: Path) -> list[Path]` (maintainer helper; copies `.claude/agents`, `.claude/skills` minus `apd-domain/`, `templates/` into package data; returns changed files)
  - `def materialize(workspace: Path) -> bool` (True when files were written; writes `<workspace>/.claude/.apd-bundle` with `bundle_digest()`; never writes or deletes under `.claude/skills/apd-domain/`)
  - `python -I -m apd_gauntlet.bundle --sync` runs `sync_from_repo(Path.cwd())`

- [ ] **Step 1: Write the failing tests**

```python
def test_bundle_matches_repo():
    repo = Path(__file__).resolve().parents[1]
    for pkg_sub, repo_sub in [("claude/agents", ".claude/agents"), ("templates", "templates")]:
        for f in (repo / repo_sub).rglob("*"):
            if f.is_file():
                assert (DATA / pkg_sub / f.relative_to(repo / repo_sub)).read_bytes() == f.read_bytes(), f
    skills = [f for f in (repo / ".claude/skills").rglob("*") if f.is_file() and "apd-domain" not in f.parts]
    assert all((DATA / "claude/skills" / f.relative_to(repo / ".claude/skills")).exists() for f in skills)

def test_materialize_idempotent_and_spares_domain_skill(tmp_path):
    ws = tmp_path / "ws"; (ws / ".claude/skills/apd-domain").mkdir(parents=True)
    (ws / ".claude/skills/apd-domain/SKILL.md").write_text("generated")
    assert materialize(ws) is True and materialize(ws) is False
    assert (ws / ".claude/agents/apd-confidentiality.md").exists() and (ws / "schemas/agent-receipt.schema.json").exists()
    assert (ws / ".claude/skills/apd-domain/SKILL.md").read_text() == "generated"

def test_materialize_refreshes_on_digest_change(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; materialize(ws)
    monkeypatch.setattr(bundle, "bundle_digest", lambda: "different")
    assert materialize(ws) is True

def test_python_m_entrypoint():
    r = subprocess.run([sys.executable, "-m", "apd_gauntlet", "--version"], capture_output=True, text=True)
    assert r.returncode == 0 and "apd-gauntlet" in r.stdout
```

Extend the wheel smoke test: after install, `python -c "from apd_gauntlet.bundle import materialize; …"` into a temp dir and assert the agent file exists.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_bundle.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `bundle.py`, `__main__.py`, then sync**

Run `python -I -m apd_gauntlet.bundle --sync` to create the packaged copies. `materialize` copies `data/schemas/*.json` to `<workspace>/schemas/`. Add a line to `CONTRIBUTING.md`: edits to `.claude/` or `templates/` need `--sync` before commit.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_bundle.py -v && pytest -m wheel tests/integration/test_wheel_install_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/__main__.py tools/apd_gauntlet/bundle.py tools/apd_gauntlet/data/claude tools/apd_gauntlet/data/templates pyproject.toml CONTRIBUTING.md tests/test_bundle.py tests/integration/test_wheel_install_smoke.py
git commit -m "feat(bundle): ship agents, skills, templates in the wheel and materialize a workspace"
```

### Task 2: Ledger, events and lock

**Files:**

- Create: `tools/apd_gauntlet/runner/{__init__,ledger,lock}.py`
- Test: `tests/runner/test_ledger.py`, `tests/runner/test_lock.py`

**Interfaces:**

- Produces:
  - `RunState = Literal["idle","running","completed","failed","cancelled","budget_exhausted"]`
  - `StepStatus = Literal["pending","running","ok","skipped","error","cancelled"]`
  - `@dataclass class StepRecord: label: str; phase: str; kind: Literal["cli","agent","decide"]; status: StepStatus; attempts: int; started_at: str | None; ended_at: str | None; cost_usd: float; turns: int; error: str | None`
  - `class Ledger: def __init__(self, run_dir: Path); state: RunState; @property spent_usd: float; def step(self, label: str) -> StepRecord | None; def begin(self, label: str, phase: str, kind: str) -> None; def end(self, label: str, status: StepStatus, *, cost_usd: float = 0.0, turns: int = 0, error: str | None = None) -> None; def set_state(self, state: RunState, reason: str | None = None) -> None; def emit(self, type: str, **fields: Any) -> None; def reset_from(self, labels: Iterable[str]) -> None`
  - `EVENT_FIELDS: dict[str, frozenset[str]]` — per event type, the only keys `emit` keeps: `phase_started {phase}`, `step_started {label, phase, kind}`, `step_finished {label, status, cost_usd, turns, error}`, `tool_used {label, tool, path, decision}`, `cost {spent_usd, budget_usd}`, `warning {message}`, `error {message}`, `run_finished {state, reason}`
  - `def read_events(run_dir: Path, after_line: int = 0) -> tuple[list[dict[str, Any]], int]` (events plus the new line count)
  - `class LockHeld(Exception): holder: dict[str, Any]`; `class RunLock` (context manager; `__init__(self, run_dir: Path)`); `def lock_holder(run_dir: Path) -> dict[str, Any] | None`

- [ ] **Step 1: Write the failing tests**

```python
def test_ledger_round_trip(tmp_path):
    led = Ledger(tmp_path); led.begin("intake", "intake", "agent"); led.end("intake", "ok", cost_usd=1.25, turns=12)
    again = Ledger(tmp_path)
    assert again.step("intake").status == "ok" and again.spent_usd == 1.25

def test_emit_drops_unknown_fields(tmp_path):
    Ledger(tmp_path).emit("tool_used", label="intake", tool="Read", path="inputs/a.md", decision="allow", content="SECRET")
    events, n = read_events(tmp_path)
    assert n == 1 and "content" not in events[0] and events[0]["tool"] == "Read" and "ts" in events[0]

def test_read_events_incremental(tmp_path):
    led = Ledger(tmp_path); led.emit("warning", message="a"); _, n = read_events(tmp_path)
    led.emit("warning", message="b")
    events, n2 = read_events(tmp_path, after_line=n)
    assert [e["message"] for e in events] == ["b"] and n2 == 2

def test_atomic_write_survives_partial_tmp(tmp_path):
    led = Ledger(tmp_path); led.set_state("running")
    (tmp_path / ".apd-state/ledger.json.tmp").write_text("{partial")
    assert Ledger(tmp_path).state == "running"

def test_lock_exclusive(tmp_path):
    with RunLock(tmp_path):
        with pytest.raises(LockHeld) as e:
            with RunLock(tmp_path): pass
        assert e.value.holder["pid"] == os.getpid()
    assert lock_holder(tmp_path) is None

def test_stale_lock_reclaimed(tmp_path):
    (tmp_path / ".apd-state").mkdir()
    (tmp_path / ".apd-state/lock").write_text(json.dumps({"pid": 999_999_999, "host": socket.gethostname(), "started_at": "x"}))
    with RunLock(tmp_path): assert lock_holder(tmp_path)["pid"] == os.getpid()

def test_foreign_host_lock_not_reclaimed(tmp_path): ...  # host "other" → LockHeld even if the pid is dead locally
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/runner -v`
Expected: FAIL

- [ ] **Step 3: Implement ledger and lock**

Lock creation uses `os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)`. Liveness: `os.kill(pid, 0)`; `ProcessLookupError` means dead, `PermissionError` means alive. `events.jsonl` lines are written with a single `write` call each and `flush`.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/runner -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/runner tests/runner
git commit -m "feat(runner): add ledger, event log and run lock"
```

### Task 3: CLI step executor

**Files:**

- Create: `tools/apd_gauntlet/runner/steps.py`
- Test: `tests/runner/test_steps.py`

**Interfaces:**

- Produces:
  - `@dataclass class CliResult: cmd: str; exit_code: int; stdout_tail: str; stderr_tail: str` (tails = last 20 lines)
  - `CliRunnerFn = Callable[[list[str]], CliResult]`
  - `def run_cli(args: list[str], *, cwd: Path, timeout_s: float = 3600.0) -> CliResult` — runs `[sys.executable, "-m", "apd_gauntlet", *args]`; a timeout yields `exit_code=124`
  - `def outputs_valid(run_dir: Path, scope: Path, flags: list[str] | None = None, *, cli: CliRunnerFn) -> bool` — `validate --schema-only --errors-only <scope> [flags]` exit 0 and every expected file present (caller passes the scope)
  - `def parse_audit_counts(stdout: str) -> tuple[int, int] | None` — reads `structural_failed=<S> editorial_failed=<E>` from the `audit-report:` line
  - `def error_files(stdout: str, run_dir: Path) -> set[str]` — run-relative paths named on `ERROR` lines of `validate --errors-only`

- [ ] **Step 1: Write the failing tests**

```python
def test_run_cli_exit_and_tail(tmp_path):
    r = run_cli(["validate-run-config", str(tmp_path / "missing.yaml")], cwd=tmp_path)
    assert r.exit_code != 0 and r.cmd == "validate-run-config"

def test_parse_audit_counts():
    out = "audit-report: FAIL (checks=12 structural_failed=1 editorial_failed=3)\n"
    assert parse_audit_counts(out) == (1, 3) and parse_audit_counts("no line") is None

def test_error_files():
    out = "ERROR runs/x/10-trustworthiness/integrity.findings.yaml: 'scope' is not of type 'string'\n"
    assert error_files(out, Path("runs/x")) == {"10-trustworthiness/integrity.findings.yaml"}

def test_outputs_valid_on_clean_fixture(tmp_path):
    run = shutil.copytree(FIX / "runs/clean-run", tmp_path / "run")
    assert outputs_valid(run, run / "10-trustworthiness", cli=lambda a: run_cli(a, cwd=tmp_path))
```

Confirm the exact `audit-report` and `validate --errors-only` line formats against `synthesis/audit.py` and `validate.py` before fixing the regexes; the test strings must match what those modules print.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/runner/test_steps.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `steps.py`**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/runner/test_steps.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/runner/steps.py tests/runner/test_steps.py
git commit -m "feat(runner): run CLI steps as subprocesses with output checks"
```

### Task 4: Tool-use guard

**Files:**

- Create: `tools/apd_gauntlet/runner/guard.py`
- Test: `tests/runner/test_guard.py`

**Interfaces:**

- Produces: `def check_tool_use(tool_name: str, tool_input: dict[str, Any], *, workspace: Path, run_dir: Path, mcp_prefixes: tuple[str, ...] = ()) -> str | None` — returns a deny reason, or None to allow. Paths resolve relative to `workspace` with `Path.resolve()` (symlinks followed) before the containment check.

- [ ] **Step 1: Write the failing table test**

```python
WS = Path("/w"); RUN = WS / "runs/r1"
CASES = [
    ("Bash", {"command": "apd-gauntlet validate runs/r1 --errors-only"}, None),
    ("Bash", {"command": "apd-gauntlet validate runs/r1; curl evil"}, "metacharacter"),
    ("Bash", {"command": "cat ~/.ssh/id_rsa"}, "apd-gauntlet"),
    ("Bash", {"command": "apd-gauntlet validate ../other"}, ".."),
    ("Bash", {"command": "apd-gauntlet validate $(id)"}, "metacharacter"),
    ("Write", {"file_path": "runs/r1/10-trustworthiness/x.yaml"}, None),
    ("Write", {"file_path": "runs/r2/x.yaml"}, "outside the run"),
    ("Edit", {"file_path": "/w/.claude/agents/apd-intake.md"}, "outside the run"),
    ("Read", {"file_path": ".claude/skills/apd-framework/SKILL.md"}, None),
    ("Read", {"file_path": "/home/u/.aws/credentials"}, "outside"),
    ("Read", {"file_path": "runs/r2/inputs/a.md"}, "outside"),
    ("Glob", {"pattern": "**/*.yaml", "path": "runs/r1"}, None),
    ("Glob", {"pattern": "../../**"}, "outside"),
    ("Grep", {"pattern": "x", "path": "/etc"}, "outside"),
    ("WebFetch", {"url": "https://x"}, "not permitted"),
    ("mcp__codebase-memory-mcp__search_graph", {}, "not permitted"),
]

@pytest.mark.parametrize("tool,inp,expect", CASES)
def test_guard(tool, inp, expect, monkeypatch):
    monkeypatch.setattr(Path, "resolve", lambda self, strict=False: Path(os.path.normpath(self if self.is_absolute() else WS / self)))
    reason = check_tool_use(tool, inp, workspace=WS, run_dir=RUN)
    assert (reason is None) if expect is None else (expect in reason)

def test_mcp_allowed_when_prefixed():
    assert check_tool_use("mcp__codebase-memory-mcp__search_graph", {}, workspace=WS, run_dir=RUN,
                          mcp_prefixes=("mcp__codebase-memory-mcp__",)) is None

def test_symlink_escape(tmp_path):
    ws = tmp_path / "w"; run = ws / "runs/r1"; run.mkdir(parents=True)
    (run / "link").symlink_to(tmp_path)        # points outside
    assert "outside" in check_tool_use("Read", {"file_path": "runs/r1/link/secret"}, workspace=ws, run_dir=run)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/runner/test_guard.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `guard.py`**

Allowed tools: `Read, Glob, Grep, Write, Edit, MultiEdit, Bash` plus `mcp_prefixes`. Glob also denies a `pattern` that is absolute or contains `..`. Deny reasons are short and contain no input values beyond the tool name.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/runner/test_guard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/runner/guard.py tests/runner/test_guard.py
git commit -m "feat(runner): confine agent tool use to the run"
```

### Task 5: Agent specs and the SDK executor

**Files:**

- Create: `tools/apd_gauntlet/runner/agents.py`, `tools/apd_gauntlet/runner/instructions.py`
- Modify: `pyproject.toml` (extra `runner`; set the SDK bounds to the version installed for this task)
- Test: `tests/runner/test_agents.py`

**Interfaces:**

- Consumes: `UserConfig`, `credentials.resolve`, `check_tool_use`, `Ledger.emit`
- Produces:
  - `@dataclass(frozen=True) class AgentSpec: name: str; prompt: str; tools: tuple[str, ...]; model: str | None; effort: str | None`
  - `def load_agent_spec(workspace: Path, name: str) -> AgentSpec` (frontmatter `tools` may be a list or a comma string)
  - `def resolve_model(spec: AgentSpec, cfg: UserConfig) -> str`
  - `def sdk_env(cfg: UserConfig) -> dict[str, str]` — `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; `CLAUDE_CODE_USE_BEDROCK|VERTEX|FOUNDRY=1` per `cfg.llm.provider`; `cfg.llm.extra_env`; `ANTHROPIC_API_KEY` from the keychain or `op://` when the provider is `anthropic` and the env lacks it
  - `def claude_auth_problem(cfg: UserConfig) -> str | None` (None when usable)
  - `@dataclass class AgentOutcome: receipt: dict[str, Any] | None; text: str | None; cost_usd: float; turns: int; error: str | None`
  - `class AgentExecutor(Protocol): async def run(self, spec: AgentSpec, instruction: str, *, label: str, run_dir: Path, budget_usd: float, structured: bool = True) -> AgentOutcome`
  - `class SdkAgentExecutor: def __init__(self, cfg: UserConfig, workspace: Path, ledger: Ledger, *, query: Callable[..., AsyncIterator[Any]] | None = None)` (default `claude_agent_sdk.query`)
  - `def build_options(spec: AgentSpec, cfg: UserConfig, *, workspace: Path, run_dir: Path, budget_usd: float, structured: bool) -> Any` (returns `ClaudeAgentOptions`)
  - `instructions.py`: `INSTRUCTIONS: dict[str, str]` keyed by `"<agent>"` or `"<agent>:<variant>"` (`apd-<lens>:retry`, `apd-<lens>:repair`, `apd-cluster-adjudicator:retry`, `apd-report-writer:build-fix`, `apd-report-writer:remediate`, `apd-synthesizer:fallback`, `apd-synthesizer:rollup`, `apd-synthesizer:build`); `def instruction(key: str, **values: str) -> str` (values: `run_dir`, `tier_dir`, `lens`, `threat_model`, `errors`, `critique`). Text = the matching `llmStep`/`agent()` text in `apd-gauntlet.js`, minus the idempotency guard and the "return a receipt" line, which structured output replaces.

`build_options` sets: `system_prompt=spec.prompt`, `model=resolve_model(...)`, `effort=spec.effort` when set, `max_turns=80`, `cwd=workspace`, `setting_sources=[]`, `env=sdk_env(cfg)`, `permission_mode="dontAsk"`, `allowed_tools` = spec tools with `Bash` replaced by `Bash(apd-gauntlet *)`, `max_budget_usd=budget_usd`, `output_format={"type": "json_schema", "schema": <agent-receipt schema>}` when `structured`, a `PreToolUse` hook that calls `check_tool_use`, emits `tool_used` and denies on a reason, and `mcp_servers` with only `codebase-memory-mcp` (from `cfg.mcp_servers`) when `spec.name == "apd-code-recon"`, with the SDK's strict-MCP option set.

- [ ] **Step 1: Write the failing tests**

```python
def test_load_spec_comma_tools(materialized_ws):
    s = load_agent_spec(materialized_ws, "apd-confidentiality")
    assert s.tools == ("Read", "Glob", "Grep", "Write") and s.model is None and s.prompt.startswith("# Confidentiality")

def test_model_precedence(materialized_ws):
    cfg = UserConfig(); s = load_agent_spec(materialized_ws, "apd-threat-model-author")   # frontmatter opus
    assert resolve_model(s, cfg) == "opus"
    cfg.llm.model_overrides = {"apd-threat-model-author": "sonnet"}
    assert resolve_model(s, cfg) == "sonnet"
    assert resolve_model(load_agent_spec(materialized_ws, "apd-integrity"), UserConfig()) == "opus"

def test_options_lock_down(materialized_ws, tmp_path):
    o = build_options(load_agent_spec(materialized_ws, "apd-threat-model-recon"), UserConfig(),
                      workspace=materialized_ws, run_dir=materialized_ws / "runs/r", budget_usd=5.0, structured=True)
    assert o.setting_sources == [] and o.permission_mode == "dontAsk" and o.max_turns == 80
    assert "Bash(apd-gauntlet *)" in o.allowed_tools and "Bash" not in o.allowed_tools
    assert o.env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1" and o.max_budget_usd == 5.0
    assert set(o.output_format["schema"]["required"]) == {"agent", "status", "outputs", "counts"}

def test_no_mcp_except_code_recon(materialized_ws): ...  # apd-intake → no mcp_servers; apd-code-recon with cfg.mcp_servers → only that server

def test_executor_collects_receipt_and_cost(materialized_ws, tmp_path):
    async def fake_query(*, prompt, options):
        yield ResultMessage(subtype="success", structured_output={"agent": "apd-integrity", "status": "ok", "outputs": [], "counts": {}},
                            total_cost_usd=0.42, num_turns=7, is_error=False, result=None)
    ex = SdkAgentExecutor(UserConfig(), materialized_ws, Ledger(tmp_path), query=fake_query)
    out = asyncio.run(ex.run(load_agent_spec(materialized_ws, "apd-integrity"), "go", label="integrity",
                             run_dir=tmp_path, budget_usd=5))
    assert out.receipt["status"] == "ok" and out.cost_usd == 0.42 and out.turns == 7 and out.error is None

def test_executor_maps_max_turns_to_error(materialized_ws, tmp_path): ...  # subtype "error_max_turns" → error set, receipt None
def test_auth_problem_messages(monkeypatch, memory_keyring): ...           # anthropic, no env, no keychain → mentions ANTHROPIC_API_KEY and "keys set anthropic"
def test_instructions_cover_workflow_agents():
    js = WORKFLOW_JS.read_text()
    types = set(re.findall(r"llmStep\('(apd-[a-z-]+)'", js)) | set(re.findall(r"agentType: '(apd-[a-z-]+)'", js))
    types |= {f"apd-{l}" for l in LENSES}
    assert types <= {k.split(":")[0] for k in INSTRUCTIONS}
```

Construct `ResultMessage` with the SDK's real class; if its constructor needs more fields, supply them in a `make_result(**kw)` test helper.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/runner/test_agents.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `agents.py` and `instructions.py`**

Iterate the query to completion without `break` (the SDK warns that early exit breaks asyncio cleanup). Cost and turns come from the `ResultMessage` (`total_cost_usd`, `num_turns`); a non-success subtype or `is_error` sets `error` to the subtype. When `structured` is False, `text` is `ResultMessage.result`.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/runner/test_agents.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/runner/agents.py tools/apd_gauntlet/runner/instructions.py pyproject.toml tests/runner/test_agents.py
git commit -m "feat(runner): build locked-down Agent SDK dispatches"
```

### Task 6: Flow through the pre-synthesis gate

**Files:**

- Create: `tools/apd_gauntlet/runner/flow.py`
- Test: `tests/runner/test_flow_pre_synthesis.py`, `tests/runner/fakes.py` (`FakeExecutor`, `FakeCli`, `scenario()` helper)

**Interfaces:**

- Consumes: Tasks 2–5; Plan 1 `run_finding_qa`, `client_for`, `run_decision_model`
- Produces:
  - `PHASES: tuple[str, ...]` (copied from `meta.phases`)
  - `TIERS = (("tier-1", "10-trustworthiness", ("confidentiality","integrity","availability")), ("tier-2", "20-scalability", ("distributed","resilient","ephemeral")), ("tier-3", "30-auditability", ("authenticity","non-repudiation","immutability")))`
  - `LENS_RETRIES = 2`, `AUDIT_REMEDIATIONS = 2`
  - `class RunHalted(Exception): phase: str; reason: str`
  - `DecideFn = Callable[[str], Awaitable[None]]` (argument: tier dir)
  - `class Runner: def __init__(self, run_dir: Path, workspace: Path, cfg: UserConfig, executor: AgentExecutor, ledger: Ledger, *, cli: CliRunnerFn, decide: DecideFn | None = None, budget_usd: float | None = None, cancel: asyncio.Event | None = None); async def run(self, *, restart_from: str | None = None, stop_after: str | None = None) -> RunState` (`stop_after` ends the run after the named phase; tests use it)

Phase behavior through `validate-full-prephase5` (labels in parentheses must match the workflow):

| Phase | Steps | Conditions and failure handling |
|---|---|---|
| setup | `validate --schema-only --errors-only` (validate-scaffold); `build-domain-skill <domains>` (build-domain-skill, always runs); `validate-domain <domains>` (validate-domain) | |
| intake | agent `apd-intake` (intake); `assemble-inventory` (always); `validate --schema-only --errors-only` (intake-schema-gate) | |
| code-recon | agent `apd-code-recon` (code-recon) | Only when `code_recon` ≠ `disabled`. No `codebase-memory-mcp` in config: `auto` → write `00-context/code-recon-skipped.md` ("CBM is not configured for the local runner; code recon skipped.") and mark `skipped`; `enabled` → `RunHalted`. Agent error under `enabled` → `RunHalted` |
| threat-model-author | `author-threat-model` (author-threat-model-floor); agent (threat-model-author) | |
| tm-recon | agent `apd-threat-model-recon` (tm-recon) | Only when `threat_model` is set |
| tier-1..3 | lens agents in parallel (`<lens>`), each with up to 2 retries (`<lens>-retry-<k>`); `canonicalize` (canonicalize-`<tier>`, always); `validate <run> --tier <tier> --errors-only` (validate-`<tier>`); then `decide(tier)` (decide-finding-qa-`<tier>`) when the run enables a decision model | Lens concurrency capped by `cfg.llm.max_parallel_agents`. Tier gate failure: one `:repair` dispatch per lens named in `error_files`, with the error lines as `errors`, then canonicalize-`<tier>`-r1 and validate-`<tier>`-r1; continue either way. A `decide` failure logs a `warning` and never halts |
| tier-3 (end) | `validate --errors-only` (validate-full-prephase5) | Failure → `RunHalted("tier-3", "corpus not schema/cross-file clean")` |

Resume and budget rules for every step:

- Skip a non-always step whose ledger status is `ok` and, for steps with declared outputs, whose outputs pass `outputs_valid`.
- `restart_from` resets every step at or after that phase.
- Before each agent dispatch: `remaining = budget - ledger.spent_usd`; `≤ 0` → `set_state("budget_exhausted")` and stop starting agents; agents already running finish.
- Between steps, a set `cancel` event → `set_state("cancelled")` and return.

- [ ] **Step 1: Write the failing scenario tests**

```python
FULL = {"code_recon": "enabled", "threat_model": "inputs/tm.json", "crown_jewels": ["phi_store"]}

def test_happy_path_labels(tmp_path):
    r = scenario(tmp_path, cfg=FULL, cbm=True)
    asyncio.run(r.runner.run(stop_after="tier-3"))
    assert r.labels[:10] == ["validate-scaffold", "build-domain-skill", "validate-domain", "intake",
        "assemble-inventory", "intake-schema-gate", "code-recon", "author-threat-model-floor",
        "threat-model-author", "tm-recon"]
    assert set(r.labels[10:13]) == {"confidentiality", "integrity", "availability"}
    assert r.labels[-1] == "validate-full-prephase5"

def test_lens_retries_then_continues(tmp_path):
    r = scenario(tmp_path, agent_outcomes={"integrity": ["error", "error", "error"]})
    asyncio.run(r.runner.run(stop_after="tier-1"))
    assert ["integrity-retry-1", "integrity-retry-2"] == [l for l in r.labels if l.startswith("integrity-retry")]

def test_tier_gate_repair(tmp_path):
    r = scenario(tmp_path, cli_outcomes={"validate-10-trustworthiness": (1, "ERROR runs/r/10-trustworthiness/integrity.findings.yaml: bad")})
    asyncio.run(r.runner.run(stop_after="tier-1"))
    assert "integrity-repair" in r.labels and "validate-10-trustworthiness-r1" in r.labels
    assert "bad" in r.instructions["integrity-repair"]

def test_prephase5_gate_halts(tmp_path):
    r = scenario(tmp_path, cli_outcomes={"validate-full-prephase5": (1, "ERROR …")})
    assert asyncio.run(r.runner.run()) == "failed" and r.ledger.state == "failed"

def test_code_recon_auto_without_cbm_skips(tmp_path):
    r = scenario(tmp_path, cfg={"code_recon": "auto"}, cbm=False)
    asyncio.run(r.runner.run(stop_after="code-recon"))
    assert (r.run_dir / "00-context/code-recon-skipped.md").exists() and "code-recon" not in r.agent_labels

def test_code_recon_enabled_without_cbm_halts(tmp_path): ...    # → "failed", reason mentions codebase-memory-mcp
def test_gates_by_config(tmp_path): ...                         # code_recon disabled + no threat_model → no code-recon, no tm-recon labels
def test_decide_runs_per_tier_only_when_enabled(tmp_path): ...  # decision_model cloudflare → decide called with each tier dir; absent → never
def test_decide_failure_is_warning(tmp_path): ...               # decide raises → warning event, run continues
def test_budget_stops_new_agents(tmp_path):
    r = scenario(tmp_path, budget=3.0, agent_cost=1.0)
    assert asyncio.run(r.runner.run()) == "budget_exhausted"
    assert not any(l in r.agent_labels for l in ("distributed", "resilient", "ephemeral"))

def test_resume_skips_completed(tmp_path):
    r = scenario(tmp_path); asyncio.run(r.runner.run(stop_after="tier-1"))
    r2 = scenario(tmp_path, reuse=r); asyncio.run(r2.runner.run(stop_after="tier-2"))
    assert "intake" not in r2.agent_labels and "distributed" in r2.agent_labels

def test_cancel_between_steps(tmp_path): ...                    # set cancel after "intake" → state "cancelled", no later labels

def test_half_written_lens_redone(tmp_path):
    r = scenario(tmp_path); asyncio.run(r.runner.run(stop_after="tier-1"))
    (r.run_dir / "10-trustworthiness/integrity.findings.yaml").write_text("finding:\n  - title: [unclosed")
    r2 = scenario(tmp_path, reuse=r); asyncio.run(r2.runner.run(stop_after="tier-1"))
    assert "integrity" in r2.agent_labels and "confidentiality" not in r2.agent_labels
```

`scenario()` builds a run from `tests/fixtures/runs/clean-run`, a materialized workspace, a `FakeExecutor` that writes each agent's expected output files as minimal schema-valid YAML and returns a receipt, and a `FakeCli` that maps labels to `(exit_code, stdout)`, defaulting to `(0, "")` and delegating `outputs_valid` to file existence. `stop_after` is the keyword from the Interfaces block.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/runner/test_flow_pre_synthesis.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the flow through the pre-synthesis gate**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/runner/test_flow_pre_synthesis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/runner/flow.py tests/runner
git commit -m "feat(runner): run setup through the pre-synthesis gate"
```

### Task 7: Flow from synthesis to closeout, and parity with the workflow

**Files:**

- Modify: `tools/apd_gauntlet/runner/flow.py`
- Test: `tests/runner/test_flow_synthesis.py`, `tests/runner/test_flow_parity.py`

**Interfaces:**

- Consumes: Task 6 `Runner` internals

| Phase | Steps | Conditions and failure handling |
|---|---|---|
| synthesis-cluster | `cluster-candidates` (cluster-candidates), retry once (cluster-candidates-retry-1) | Two errors → fallback |
| synthesis-adjudicate / apply | agent `apd-cluster-adjudicator` (adjudicate); `apply-clusters` (apply-clusters) | Exit 2 → re-dispatch (adjudicate-retry-1) and re-apply (apply-clusters-retry-1); exit 2 again → fallback; other error → apply-clusters-retry-1b, error again → fallback |
| synthesis-fallback | the runner appends `{phase: synthesis, decision: synthesizer-fallback, reason: decomposed-pipeline-failed}` to `40-synthesis/run-state.yaml` itself; agent `apd-synthesizer` unstructured (synthesizer-fallback) | Only when a fallback was triggered |
| tmeval, apath | agents `apd-threat-model-evaluator` (tmeval) and `apd-attack-path-analyzer` (apath) in parallel | apath only when `crown_jewels` is non-empty |
| apath (cont.) | `assemble-c4` (always); `canonicalize` (canonicalize-tmeval, always) | |
| synthesis-rollup | `rollup` (rollup), retry once (rollup-retry-1); second error → agent `apd-synthesizer:rollup` (synthesizer-fallback-rollup) | |
| synthesis-report | agent `apd-report-writer` (report-writer-attempt-0) | |
| synthesis-build | `build-report` (build-report-attempt-0); on error and no prior fallback: writer `:build-fix` (report-writer-attempt-build-fix), rebuild (build-report-attempt-build-fix); still error → `apd-synthesizer:build` (synthesizer-fallback-build), rebuild (build-report-attempt-postfallback) | |
| synthesis-audit | for i in 0..2: `audit-report` (audit-report-attempt-i); agent `apd-report-auditor` unstructured (auditor-attempt-i). Pass when structural = 0, editorial = 0 and the auditor text matches `GATE:\s*pass`. Else, i < 2: writer `:remediate` with the critique (report-writer-attempt-i+1) and rebuild (build-report-attempt-i+1) | At i = 2: structural > 0 → `RunHalted("synthesis-audit", …)`; otherwise warning and continue |
| domain-coverage-delta, domain-improvements | `domain-coverage-delta`; agent `apd-domain-auditor` (domain-auditor); `canonicalize` (canonicalize-dimpr, always) | Advisory: errors become warnings |
| closeout | `summarize`; `validate --errors-only` (validate-final) | Final validate failure → state `failed` |

Successful completion sets state `completed` and emits `run_finished`.

- [ ] **Step 1: Write the failing tests**

```python
def test_full_happy_path_tail(tmp_path):
    r = scenario(tmp_path, cfg=FULL, cbm=True, auditor_text="GATE: pass")
    assert asyncio.run(r.runner.run()) == "completed"
    tail = r.labels[r.labels.index("validate-full-prephase5") + 1:]
    assert tail[:3] == ["cluster-candidates", "adjudicate", "apply-clusters"]
    assert set(tail[3:5]) == {"tmeval", "apath"}
    assert tail[5:] == ["assemble-c4", "canonicalize-tmeval", "rollup", "report-writer-attempt-0",
        "build-report-attempt-0", "audit-report-attempt-0", "auditor-attempt-0", "domain-coverage-delta",
        "domain-auditor", "canonicalize-dimpr", "summarize", "validate-final"]

def test_adjudication_missing_twice_falls_back(tmp_path):
    r = scenario(tmp_path, cli_outcomes={"apply-clusters": (2, ""), "apply-clusters-retry-1": (2, "")}, auditor_text="GATE: pass")
    asyncio.run(r.runner.run())
    assert "adjudicate-retry-1" in r.labels and "synthesizer-fallback" in r.labels
    assert "synthesizer-fallback" in (r.run_dir / "40-synthesis/run-state.yaml").read_text()

def test_audit_loop_remediates_then_passes(tmp_path):
    r = scenario(tmp_path, auditor_texts=["GATE: fail\n- invented-content", "GATE: pass"],
                 cli_outcomes={"audit-report-attempt-0": (0, "audit-report: PASS (structural_failed=0 editorial_failed=0)")})
    assert asyncio.run(r.runner.run()) == "completed"
    assert "report-writer-attempt-1" in r.labels and "invented-content" in r.instructions["report-writer-attempt-1"]

def test_structural_failure_blocks(tmp_path):
    out = "audit-report: FAIL (structural_failed=2 editorial_failed=0)"
    r = scenario(tmp_path, cli_outcomes={f"audit-report-attempt-{i}": (1, out) for i in range(3)})
    assert asyncio.run(r.runner.run()) == "failed" and "build-report-attempt-2" in r.labels

def test_no_apath_without_crown_jewels(tmp_path): ...       # cfg crown_jewels [] → "apath" not in agent_labels, "assemble-c4" still runs
def test_rollup_double_failure_uses_synthesizer(tmp_path): ...
def test_domain_auditor_error_is_warning(tmp_path): ...      # → state completed, warning event
```

```python
# tests/runner/test_flow_parity.py
def test_phases_match_workflow():
    js = WORKFLOW_JS.read_text()
    meta = re.search(r"phases:\s*\[(.*?)\]", js, re.DOTALL).group(1)
    assert PHASES == tuple(re.findall(r"'([^']+)'", meta))

def test_retry_caps_match_workflow():
    js = WORKFLOW_JS.read_text()
    assert re.search(r"k <= 2 && isErr\(r\)", js) and LENS_RETRIES == 2
    assert re.search(r"for \(let i = 0; i <= 2; i\+\+\)", js) and AUDIT_REMEDIATIONS == 2

def test_labels_exist_in_workflow():
    js = WORKFLOW_JS.read_text()
    for label in ["validate-scaffold", "intake-schema-gate", "author-threat-model-floor", "validate-full-prephase5",
                  "cluster-candidates-retry-1", "adjudicate-retry-1", "apply-clusters-retry-1b", "canonicalize-tmeval",
                  "rollup-retry-1", "synthesizer-fallback-rollup", "report-writer-attempt-build-fix",
                  "synthesizer-fallback-build", "build-report-attempt-postfallback", "canonicalize-dimpr", "validate-final"]:
        assert f"'{label}'" in js, label
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/runner/test_flow_synthesis.py tests/runner/test_flow_parity.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the remaining phases**

- [ ] **Step 4: Run the whole runner suite**

Run: `pytest tests/runner -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/runner/flow.py tests/runner
git commit -m "feat(runner): run synthesis through closeout in parity with the workflow"
```

### Task 8: `run`, `status` and `cancel` commands

**Files:**

- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_run.py`

**Interfaces:**

- Consumes: everything above
- Produces:
  - `def resolve_run_dir(arg: str, cfg: UserConfig) -> Path` — an existing directory path as given, else `cfg.workspace / "runs" / arg`; error when neither exists
  - `def make_runner(run_dir: Path, cfg: UserConfig, *, executor: AgentExecutor | None = None, budget_usd: float | None = None) -> Runner` (Plan 3's services call this). When `run_decision_model(run_dir)` names a provider, it passes `decide=lambda tier: run_finding_qa(run_dir, client, tier=tier)` with `client = client_for(...)`; otherwise `decide=None`
  - `apd-gauntlet run RUN [--restart-from PHASE] [--budget USD] [--detach] [--yes]`
  - `apd-gauntlet status RUN [--json]`
  - `apd-gauntlet cancel RUN`

`run` order: load config → `materialize(cfg.workspace)` → `claude_auth_problem` (exit 1 with the message) → egress consent when the run enables a decision model (`has_consent`, else `egress_notice` plus `--yes` or a TTY prompt, then `record_consent`; otherwise exit 2) → `RunLock` (exit 3 on `LockHeld`, printing holder PID and host) → build the decision client (`CredentialError` → exit 1 naming the env var), then delete the provider's env var from `os.environ` → SIGINT/SIGTERM set the cancel event → `asyncio.run(runner.run())` with a Rich live view of phase, current steps, spend and budget → exit code 0 `completed`, 1 `failed`, 4 `budget_exhausted`, 130 `cancelled`. `--detach` re-launches `[sys.executable, "-m", "apd_gauntlet", "run", RUN, "--yes"…]` with `start_new_session=True`, stdout and stderr to `.apd-state/runner.log`, and prints the PID.

`status` prints the run state, the current or failed phase, per-phase step counts, spend versus budget and the last 5 events; `--json` emits the ledger plus `lock_holder`. `cancel` sends SIGTERM to the lock holder's PID when the lock's host is this host; otherwise it exits 1 naming the host.

- [ ] **Step 1: Write the failing tests**

```python
def test_run_without_auth_fails_fast(ws_run, monkeypatch, memory_keyring):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = CliRunner().invoke(main, ["run", "r1"])
    assert r.exit_code == 1 and "keys set anthropic" in r.output and not (ws_run / ".apd-state/ledger.json").exists()

def test_run_locked(ws_run, fake_executor, auth_env):
    with RunLock(ws_run):
        r = CliRunner().invoke(main, ["run", "r1"])
    assert r.exit_code == 3 and str(os.getpid()) in r.output

def test_run_completes_with_fake_executor(ws_run, fake_executor, auth_env):
    r = CliRunner().invoke(main, ["run", "r1", "--yes"])
    assert r.exit_code == 0 and Ledger(ws_run).state == "completed"

def test_canary_key_never_written(ws_run_cf, fake_executor, auth_env, mock_transport, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "CANARY-8888")
    CliRunner().invoke(main, ["run", "r1", "--yes"])
    assert "CANARY-8888" not in grep_tree(ws_run_cf.parents[1])          # whole workspace
    assert "CLOUDFLARE_API_TOKEN" not in fake_executor.seen_env_keys     # agents never inherit it

def test_status_json(ws_run, fake_executor, auth_env): ...    # after a run: JSON has state, steps, spent_usd
def test_budget_exit_code(ws_run, fake_executor, auth_env): ...  # --budget 0.5 with agent_cost 1.0 → exit 4; then --budget 1000 → exit 0, state completed
def test_cancel_other_host(ws_run): ...                        # lock host "other" → exit 1, message names "other"
```

`fake_executor` monkeypatches `make_runner`'s default executor with Task 6's `FakeExecutor`, which records the environment it would pass to the SDK.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_cli_run.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the commands**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_cli_run.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli_run.py
git commit -m "feat(cli): add run, status and cancel for the local runner"
```

### Task 9: Docs, ADR and a manual end-to-end run

**Files:**

- Create: `docs/local-runner.md`, `docs/adrs/0025-standalone-agent-sdk-runner.md`
- Modify: `CHANGELOG.md`, `docs/running-the-gauntlet.md` (link to the local runner)

- [ ] **Step 1: Write the docs**

`docs/local-runner.md`: install (`pipx install "apd-gauntlet[runner]"`), Claude auth options and the subscription-login restriction (spec §6.2), the workspace, `run`/`status`/`cancel`, budget, resume, the enforcement hook and what it blocks, and how a run moves between the local runner and the plugin. ADR-0025 records spec §3 row 1, §7.3 and the parity tests.

- [ ] **Step 2: Lint**

Run: `npx markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**"`
Expected: 0 errors

- [ ] **Step 3: Manual end-to-end run (maintainer, needs Claude credentials)**

Run: `apd-gauntlet init-run e2e --inputs examples/apd-20260601-claim-event-bus/inputs --domain pbm --root ~/apd-gauntlet/runs && apd-gauntlet run e2e --budget 25 --yes`
Expected: state `completed`; `apd-gauntlet validate ~/apd-gauntlet/runs/e2e --errors-only` exits 0; `report-html/index.html` exists; no `tool_used` event with `decision: deny` unless an input tried something. Record spend and duration in the PR description, not in the repo (ADR-0017).

- [ ] **Step 4: Commit**

```bash
git add docs CHANGELOG.md
git commit -m "docs: document the local Agent SDK runner"
```
