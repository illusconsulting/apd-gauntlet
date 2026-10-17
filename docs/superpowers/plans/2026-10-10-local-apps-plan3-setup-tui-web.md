# Local Apps Plan 3 — Setup, TUI and Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give operators a one-minute `apd-gauntlet setup` and three ways to create a run, run it, watch it and open the report: CLI, a Textual TUI and a loopback-only web UI.

**Architecture:** One service layer (`app.services`, `app.setup`) wraps Plans 1 and 2. The CLI, TUI and web UI call only that layer. Runs started from any interface are detached runner processes; every interface follows progress by tailing the run's `events.jsonl`, so a run started in one can be watched in another. The web UI is Starlette with Jinja2 pages, a small vanilla-JS `EventSource` client and a middleware that enforces the spec's local-only security posture.

**Tech Stack:** Python 3.10+, click, Textual (extra `tui`), Starlette + uvicorn + Jinja2 + python-multipart (extra `web`), pytest with Starlette `TestClient` and Textual `run_test()`.

**Spec:** `docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md` (§8 local interfaces, §8.5 web security, §8.6 input safety, §8.7 egress notice). Depends on Plans 1 and 2. Plan 3 of 3.

**Amended 2026-10-17** per the amendments register (A3.1, A3.2, A3.3, A3.4, A11.1, A11.5, A11.7, A11.8, A11.9).

## Global Constraints

- Everything in Plans 1 and 2's Global Constraints still applies.
- Extras: `tui = ["textual>=8.2,<9"]`; `web = ["starlette>=1.0,<2", "uvicorn>=0.30", "jinja2>=3.1", "python-multipart>=0.0.9"]`; `app = ["apd-gauntlet[decide,runner,tui,web]"]`. `tui` and `web` commands print `pip install "apd-gauntlet[app]"` and exit 1 when their extra is missing.
- Input limits for a new run, from a folder or an upload: 200 MB (209,715,200 bytes) and 2,000 files; no symlink resolving outside the input root; the run id must not already exist.
- Web server binds `127.0.0.1` only. Token: `secrets.token_urlsafe(32)`. Cookie `apd_session`: `HttpOnly`, `SameSite=Strict`, `Path=/`. CSRF via header `X-APD-CSRF` or form field `csrf`. Allowed `Host`: `127.0.0.1:<port>` and `localhost:<port>`.
- Response headers on every web response: `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`. No CORS headers.
- Every interface shows the egress notice text from Plan 1 before a run with a decision model starts and records consent in `.apd-state/consent.json`.
- The TUI stays usable at 80×24.
- Versioning: this work lands on the `next` branch, which already carries the 2.0 pre-release version (`2.0.0aN`). Plan 3 changes no version strings. Tester drops (`aN` → `bN` → `rcN`) and the 2.0.0 GA follow `RELEASING.md`.

## Review Focus

- **Old browser tab after a server restart:** the stale cookie gets a "Session expired — open the link printed in your terminal" page with status 401, not a blank 403.
- **Run started in the TUI, opened in the web UI:** both show the same phase and spend; Start in the web UI answers "already running (PID n)".
- **Setup with no keychain backend and a provider chosen:** setup finishes, stores the provider and model, stores no key, prints the env var to set, and `doctor` warns.
- **`new` with a run id that already exists:** refused before copying anything (`scaffold_run` would otherwise merge into the old run).
- **Event log being written while the web stream reads it:** a partial last line is held back until it is complete, never emitted as broken JSON.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/app/__init__.py` | Package | Create |
| `tools/apd_gauntlet/app/services.py` | Runs, inputs, start/cancel, reports, doctor | Create |
| `tools/apd_gauntlet/app/setup.py` | Setup detection and apply | Create |
| `tools/apd_gauntlet/app/web/{__init__,server,security}.py` | Starlette app, middleware, serve | Create |
| `tools/apd_gauntlet/app/web/templates/*.html`, `app/web/static/{app.css,app.js}` | Pages and client | Create |
| `tools/apd_gauntlet/app/tui/{__init__,app,screens}.py` | Textual app | Create |
| `tools/apd_gauntlet/runner/ledger.py` | `read_events` holds back a partial last line | Modify |
| `tools/apd_gauntlet/cli.py` | `setup`, `doctor`, `new`, `runs`, `report`, `tui`, `web` | Modify |
| `pyproject.toml` | Extras, package data | Modify |
| `README.md`, `docs/QUICKSTART.md`, `docs/local-apps.md`, `docs/adrs/0026-local-web-ui-security.md`, `CHANGELOG.md` | Docs | Create/Modify |
| `tests/app/…`, `tests/test_cli_setup.py`, `tests/test_cli_new_runs_report.py` | Tests | Create |

---

### Task 1: Input safety, run creation and run listing

**Files:**

- Create: `tools/apd_gauntlet/app/__init__.py`, `tools/apd_gauntlet/app/services.py`
- Test: `tests/app/test_services_runs.py`

**Interfaces:**

- Consumes: `UserConfig`, `scaffold_run`, `init_run.find_escaping_links` (N1), `Ledger`, `read_events`, `lock_holder`, `run_decision_model`
- Produces:
  - `MAX_INPUT_BYTES = 209_715_200`, `MAX_INPUT_FILES = 2000`
  - `class InputsRejected(Exception): reason: str`
  - `def check_inputs(inputs: Path) -> tuple[int, int]` (files, bytes; raises `InputsRejected`; calls `init_run.find_escaping_links(inputs)` (N1) and raises `InputsRejected` naming every escaping link)
  - `@dataclass class NewRunSpec: run_id: str; inputs: Path; domains: list[str]; code_recon: Literal["disabled","auto","enabled"] = "auto"; decision_provider: str = "none"; decision_model: str | None = None; subject: str | None = None; threat_model: str | None = None; crown_jewels: list[str] | None = None`
  - `def create_run(cfg: UserConfig, spec: NewRunSpec) -> Path` → `cfg.workspace / "runs" / spec.run_id`
  - `@dataclass class RunSummary: run_id: str; path: Path; state: str; phase: str | None; spent_usd: float; report_ready: bool; decision_provider: str; updated_at: str | None; pid: int | None`
  - `def list_runs(cfg: UserConfig) -> list[RunSummary]` (newest `updated_at` first; runs without a ledger show state `idle`)
  - `def run_summary(cfg: UserConfig, run_id: str) -> RunSummary`
  - re-exports Plan 1's `egress_notice`, `has_consent` and `record_consent` from `apd_gauntlet.decide.factory`

`create_run` order: refuse an existing run directory → `check_inputs` → `scaffold_run(spec.run_id, spec.inputs, spec.domains, cfg.workspace / "runs", threat_model=spec.threat_model)` → load `.apd-run.yaml`, set `code_recon`, `subject`, `crown_jewels` and `decision_model` (only when the provider isn't `none`) → dump with `sort_keys=False` → `validate-run-config` via the existing schema; on failure delete the new directory and raise `ValueError` with the errors. `create_run` calls the unchanged `scaffold_run`, which refuses the same links (N1), so `init-run` and `new` share one rule.

- [ ] **Step 1: Write the failing tests**

```python
def test_rejects_escaping_symlink(tmp_path):
    src = tmp_path / "in"; src.mkdir(); (src / "a.md").write_text("x")
    (src / "keys").symlink_to(tmp_path / "outside"); (tmp_path / "outside").mkdir()
    with pytest.raises(InputsRejected, match="symlink"):
        check_inputs(src)

def test_allows_internal_symlink(tmp_path):
    src = tmp_path / "in"; (src / "d").mkdir(parents=True); (src / "d/a.md").write_text("x")
    (src / "alias.md").symlink_to(src / "d/a.md")
    assert check_inputs(src) == (2, 2)

def test_rejects_too_many_files(tmp_path, monkeypatch):
    monkeypatch.setattr(services, "MAX_INPUT_FILES", 3)
    src = tmp_path / "in"; src.mkdir()
    for i in range(4): (src / f"{i}.md").write_text("x")
    with pytest.raises(InputsRejected, match="4 files"):
        check_inputs(src)

def test_create_run_writes_decision_block(cfg_ws, inputs_dir):
    run = create_run(cfg_ws, NewRunSpec("r1", inputs_dir, ["pbm"], decision_provider="cloudflare", decision_model="clef"))
    rc = yaml.safe_load((run / ".apd-run.yaml").read_text())
    assert rc["decision_model"] == {"provider": "cloudflare", "model": "clef"} and (run / "inputs").is_dir()

def test_create_run_none_omits_block(cfg_ws, inputs_dir):
    run = create_run(cfg_ws, NewRunSpec("r2", inputs_dir, ["pbm"]))
    assert "decision_model" not in yaml.safe_load((run / ".apd-run.yaml").read_text())

def test_existing_run_refused_before_copy(cfg_ws, inputs_dir):
    create_run(cfg_ws, NewRunSpec("r3", inputs_dir, ["pbm"])); (inputs_dir / "new.md").write_text("y")
    with pytest.raises(FileExistsError):
        create_run(cfg_ws, NewRunSpec("r3", inputs_dir, ["pbm"]))
    assert not (cfg_ws.workspace / "runs/r3/inputs/new.md").exists()

def test_create_run_rejects_escaping_link(cfg_ws, inputs_dir, tmp_path): ...  # inputs_dir/keys -> outside; InputsRejected names "keys"; no runs/<id> directory

def test_list_runs_states(cfg_ws, inputs_dir):
    create_run(cfg_ws, NewRunSpec("a", inputs_dir, ["pbm"]))
    run_b = create_run(cfg_ws, NewRunSpec("b", inputs_dir, ["pbm"])); Ledger(run_b).set_state("failed")
    assert [(s.run_id, s.state) for s in list_runs(cfg_ws)] == [("b", "failed"), ("a", "idle")]

def test_egress_notice_text(cfg_ws, inputs_dir):
    run = create_run(cfg_ws, NewRunSpec("e", inputs_dir, ["pbm"], decision_provider="openrouter"))
    assert egress_notice(run) == ("Finding titles, summaries and evidence excerpts for run e will be sent to "
                                  "OpenRouter (typesafe/jev-1.13).")
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app/test_services_runs.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the functions**

`check_inputs` calls `init_run.find_escaping_links(inputs)` (N1) and raises `InputsRejected` naming every escaping link; it then walks with `os.walk(followlinks=False)`, counts files and bytes as it goes and stops at the first limit exceeded.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app/test_services_runs.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app tests/app/test_services_runs.py
git commit -m "feat(app): add safe run creation and run listing"
```

### Task 2: Start, cancel, reports and the partial-line fix

**Files:**

- Modify: `tools/apd_gauntlet/app/services.py`, `tools/apd_gauntlet/runner/ledger.py`
- Test: `tests/app/test_services_lifecycle.py`, extend `tests/runner/test_ledger.py`

**Interfaces:**

- Consumes: `RunLock`, `lock_holder`, `cancel` semantics from Plan 2 Task 8, `report.build.build_report`
- Produces:
  - `class AlreadyRunning(Exception): pid: int; host: str`
  - `def start_run(cfg: UserConfig, run_id: str, *, consent: bool, budget_usd: float | None = None, restart_from: str | None = None) -> int` — raises `AlreadyRunning`; raises `PermissionError` (message = `egress_notice`) when a decision model is enabled, `consent` is False and `has_consent` is False; calls `record_consent(..., method="prompt")` when `consent` is True; spawns `[sys.executable, "-m", "apd_gauntlet", "run", run_dir, "--yes", …]` with `start_new_session=True`, output to `.apd-state/runner.log`; returns the PID
  - `def cancel_run(cfg: UserConfig, run_id: str) -> bool`
  - `def build_run_report(cfg: UserConfig, run_id: str) -> Path` (the `index.html` path)
  - `def report_index(cfg: UserConfig, run_id: str) -> Path | None`
  - `def report_metrics(cfg: UserConfig, run_id: str) -> dict[str, Any] | None` (parsed `40-synthesis/metrics.yaml`)
  - `read_events` change: a final line without `\n` is not returned and not counted

- [ ] **Step 1: Write the failing tests**

```python
def test_partial_line_held_back(tmp_path):
    Ledger(tmp_path).emit("warning", message="a")
    with open(tmp_path / ".apd-state/events.jsonl", "a") as f: f.write('{"type": "warn')
    events, n = read_events(tmp_path)
    assert [e["message"] for e in events] == ["a"] and n == 1

def test_start_requires_consent(cfg_ws, run_with_cf):
    with pytest.raises(PermissionError, match="Cloudflare"):
        start_run(cfg_ws, run_with_cf.name, consent=False)

def test_start_spawns_detached(cfg_ws, run_plain, monkeypatch):
    seen = {}
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: seen.update(args=args, kw=kw) or SimpleNamespace(pid=4242))
    assert start_run(cfg_ws, run_plain.name, consent=False) == 4242
    assert seen["args"][1:4] == ["-m", "apd_gauntlet", "run"] and seen["kw"]["start_new_session"] is True

def test_start_when_running(cfg_ws, run_plain):
    with RunLock(run_plain):
        with pytest.raises(AlreadyRunning) as e:
            start_run(cfg_ws, run_plain.name, consent=False)
    assert e.value.pid == os.getpid()

def test_report_round_trip(cfg_ws, tmp_path):
    run = copy_example_run(cfg_ws, "apd-20260601-claim-event-bus")   # copies examples/*/expected as a run
    idx = build_run_report(cfg_ws, run.name)
    assert idx.name == "index.html" and report_index(cfg_ws, run.name) == idx and report_metrics(cfg_ws, run.name)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app/test_services_lifecycle.py tests/runner/test_ledger.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app tests/runner -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app/services.py tools/apd_gauntlet/runner/ledger.py tests/app tests/runner/test_ledger.py
git commit -m "feat(app): start, cancel and report services"
```

### Task 3: Setup, doctor and the `setup`/`doctor` commands

**Files:**

- Create: `tools/apd_gauntlet/app/setup.py`
- Modify: `tools/apd_gauntlet/app/services.py` (doctor; adds `register_doctor_check`), `tools/apd_gauntlet/cli.py`
- Test: `tests/app/test_setup.py`, `tests/app/test_doctor.py`, `tests/test_cli_setup.py`

**Interfaces:**

- Consumes: `load_config`, `save_config`, `credentials`, `client_for`, `claude_auth_problem`, `materialize`, `bundle_digest`
- Produces:
  - `@dataclass class SetupAnswers: workspace: Path; llm_provider: Literal["anthropic","bedrock","vertex","foundry"]; anthropic_key: str | None; decision_provider: str; decision_model: str | None; decision_key: str | None; cloudflare_account_id: str | None; domains: list[str]; decision_base_url: str | None = None; decision_context_window: int | None = None` (the last two are for `selfhosted`)
  - `@dataclass class SetupResult: config_path: Path; stored: list[str]; test_summary: str | None; warnings: list[str]`
  - `def detect_defaults(cfg: UserConfig) -> SetupAnswers` (LLM provider from `CLAUDE_CODE_USE_BEDROCK|VERTEX|FOUNDRY`, else `anthropic`)
  - `async def apply_setup(answers: SetupAnswers, *, test_decision: bool = True, transport: httpx.AsyncBaseTransport | None = None) -> SetupResult`
  - `@dataclass class Check: name: str; status: Literal["pass","warn","fail"]; detail: str; fix: str | None`
  - `def doctor(cfg: UserConfig, *, online: bool = False, transport: httpx.AsyncBaseTransport | None = None) -> list[Check]` with check names, in order: `python`, `extras`, `workspace`, `claude`, `agent-sdk`, `keychain`, `decision-model`, `code-recon`. The `agent-sdk` check verifies the Claude Code CLI bundled in the SDK wheel (2.1.300 in 0.2.167).
  - `def register_doctor_check(name: str, fn: Callable[[UserConfig], Check]) -> None` — registered checks run after the eight built-in checks, in registration order; a duplicate or built-in name raises `ValueError`; an exception inside `fn` becomes `Check(name, "fail", <exception class and first 200 characters>, None)`; `doctor --json` lists registered checks; IAC1 and CF1 register theirs at import
  - CLI `setup [--workspace P] [--llm-provider X] [--decision-provider X] [--decision-model M] [--decision-base-url URL] [--decision-context-window N] [--cloudflare-account-id ID] [--domain D]... [--yes] [--no-test]`; `doctor [--online] [--json]` (exit 1 when any check fails)

`apply_setup`: create the workspace, `materialize`, store keys (a `NoKeychainError` adds a warning naming the env var and continues), save config (decision defaults, account id, domains, LLM provider), then, when a decision provider is set and a key resolves, send the Plan 1 `keys test` question and put `"<model> · <ms> ms · $<cost> (<basis>)"` in `test_summary`. Keys never go into `SetupResult` or the config. `setup` also names where review content goes on the Claude side, for example "Review content will be sent to Claude through Amazon Bedrock."

Interactive `setup` asks the four questions in spec §8.2 with defaults from `detect_defaults`, using `click.prompt(hide_input=True)` for keys. With `--yes`, it takes defaults and flags without prompting; a key must then come from the environment.

Self-hosted provider (consolidated plan N5, LA1 Task 10): setup's decision-model prompt gains "Self-hosted (System One endpoint)", asking for the base URL and context window; flags `--decision-base-url` and `--decision-context-window` set `decision_model.base_url` and `decision_model.context_window`; `--decision-provider` accepts `selfhosted`. `doctor --online` sends one `noul` question to the self-hosted endpoint and reports latency.

- [ ] **Step 1: Write the failing tests**

```python
def test_apply_setup_stores_and_tests(tmp_path, memory_keyring, mock_transport, cfg_path):
    a = SetupAnswers(tmp_path / "ws", "anthropic", "sk-ant-1111", "openrouter", None, "sk-or-2222", None, ["pbm"])
    res = asyncio.run(apply_setup(a, transport=mock_transport))
    assert set(res.stored) == {"anthropic", "openrouter"} and "jev" in res.test_summary
    text = cfg_path.read_text()
    assert "sk-or-2222" not in text and "openrouter" in text and (tmp_path / "ws/.claude/agents").is_dir()

def test_apply_setup_no_keychain_warns(tmp_path, monkeypatch, cfg_path):
    monkeypatch.setattr(credentials, "keychain_available", lambda: False)
    a = SetupAnswers(tmp_path / "ws", "anthropic", None, "typesafe", None, "ts-3333", None, ["pbm"])
    res = asyncio.run(apply_setup(a, test_decision=False))
    assert any("TYPESAFE_API_KEY" in w for w in res.warnings) and res.stored == []

def test_doctor_order_and_failures(cfg_ws, monkeypatch, memory_keyring):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    checks = doctor(cfg_ws)
    assert [c.name for c in checks] == ["python","extras","workspace","claude","agent-sdk","keychain","decision-model","code-recon"]
    claude = next(c for c in checks if c.name == "claude")
    assert claude.status == "fail" and "keys set anthropic" in claude.fix

def test_doctor_online_decision(cfg_ws_cf, mock_transport, monkeypatch): ...  # online=True → decision-model pass with "ms"
def test_doctor_warns_without_keychain(cfg_ws, monkeypatch): ...               # keychain_available False → keychain status "warn", fix names env vars
def test_cli_setup_noninteractive(tmp_path, memory_keyring, cfg_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    r = CliRunner().invoke(main, ["setup", "--workspace", str(tmp_path / "ws"), "--decision-provider", "none", "--yes"])
    assert r.exit_code == 0 and "apd-gauntlet new" in r.output

def test_cli_setup_interactive_hides_key(tmp_path, memory_keyring, cfg_path, mock_transport): ...  # input stream; key absent from output
def test_cli_doctor_json(cfg_ws): ...   # --json → list of {name,status,detail,fix}
def test_registered_check_runs_after_builtins(cfg_ws): ...   # register_doctor_check("sample", fn) → "sample" comes after "code-recon"; --json lists it
def test_register_duplicate_rejected(): ...                  # a second "sample", or a built-in name such as "python" → ValueError
def test_registered_check_exception_is_fail(cfg_ws): ...     # fn raises → Check("sample", "fail", <exception class and first 200 characters>, None)
def test_setup_selfhosted_flags_write_config(tmp_path, memory_keyring, cfg_path): ...  # --decision-provider selfhosted --decision-base-url --decision-context-window → decision_model.base_url and context_window in config
def test_doctor_online_uses_selfhosted(cfg_ws, mock_transport): ...  # mock transport; online=True → one noul question to the self-hosted endpoint; decision-model detail reports latency
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app/test_setup.py tests/app/test_doctor.py tests/test_cli_setup.py -v`
Expected: FAIL

- [ ] **Step 3: Implement setup, doctor and the two commands**

The closing message of `setup` prints the next three commands from spec §8.1 with the chosen workspace.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app tests/test_cli_setup.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app tools/apd_gauntlet/cli.py tests/app tests/test_cli_setup.py
git commit -m "feat(cli): add guided setup and doctor"
```

### Task 4: `new`, `runs` and `report` commands

**Files:**

- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_new_runs_report.py`

**Interfaces:**

- Consumes: Tasks 1–2 services
- Produces:
  - `new RUN_ID [--inputs DIR] [--domain D]... [--code-recon X] [--decision-provider X] [--decision-model M] [--subject S] [--threat-model PATH]` — prompts for anything missing on a TTY, defaulting from config; prints the run path and `apd-gauntlet run RUN_ID`
  - `runs [--json]` — table: run, state, phase, spend, report, decision model, updated
  - `report RUN_ID [--build/--no-build] [--open]` — builds when missing or with `--build`, prints the path, `--open` calls `webbrowser.open(index.as_uri())`

- [ ] **Step 1: Write the failing tests**

```python
def test_new_with_flags(cfg_ws_env, inputs_dir):
    r = CliRunner().invoke(main, ["new", "claims-api", "--inputs", str(inputs_dir), "--domain", "pbm", "--decision-provider", "none"])
    assert r.exit_code == 0 and "apd-gauntlet run claims-api" in r.output

def test_new_rejects_symlink_escape(cfg_ws_env, inputs_with_escape):
    r = CliRunner().invoke(main, ["new", "x", "--inputs", str(inputs_with_escape)])
    assert r.exit_code == 1 and "symlink" in r.output

def test_runs_json(cfg_ws_env, inputs_dir):
    CliRunner().invoke(main, ["new", "a", "--inputs", str(inputs_dir), "--domain", "pbm"])
    data = json.loads(CliRunner().invoke(main, ["runs", "--json"]).output)
    assert data[0]["run_id"] == "a" and data[0]["state"] == "idle"

def test_report_open(cfg_ws_env, example_run, monkeypatch):
    opened = []; monkeypatch.setattr(webbrowser, "open", opened.append)
    r = CliRunner().invoke(main, ["report", example_run.name, "--open"])
    assert r.exit_code == 0 and opened[0].endswith("report-html/index.html")
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_cli_new_runs_report.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the commands**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_cli_new_runs_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli_new_runs_report.py
git commit -m "feat(cli): add new, runs and report"
```

### Task 5: Web security middleware

**Files:**

- Create: `tools/apd_gauntlet/app/web/__init__.py`, `tools/apd_gauntlet/app/web/security.py`
- Test: `tests/app/web/test_security.py`

**Interfaces:**

- Produces:
  - `class LocalOnlyMiddleware: def __init__(self, app: ASGIApp, *, token: str, port: int)`; `request.state.csrf` holds the session's CSRF value for templates
  - `SESSION_COOKIE = "apd_session"`, `CSRF_HEADER = "X-APD-CSRF"`, `CSRF_FIELD = "csrf"`
  - Behavior, in order: `Host` not allowed → 403. `GET` with `?token=<token>` → set the session cookie (value `secrets.token_urlsafe(32)` kept in memory with its CSRF value) and 303 to the same path without `token`. No valid session cookie → 401 with the "Session expired" page. Unsafe method (`POST`, `PUT`, `PATCH`, `DELETE`) → `Origin`, when present, must be `http://127.0.0.1:<port>` or `http://localhost:<port>`, and the CSRF header or form field must equal the session's value, else 403. Add the Global Constraints headers to every response.

- [ ] **Step 1: Write the failing tests**

```python
def client(port=8765, token="T" * 43):
    app = Starlette(routes=[Route("/", lambda r: PlainTextResponse("ok")),
                            Route("/act", lambda r: PlainTextResponse("done"), methods=["POST"])])
    return TestClient(LocalOnlyMiddleware(app, token=token, port=port), base_url=f"http://127.0.0.1:{port}")

def login(c): return c.get("/?token=" + "T" * 43, follow_redirects=False)

def test_token_exchange_strips_url():
    r = login(c := client())
    assert r.status_code == 303 and r.headers["location"] == "/" and "apd_session" in r.cookies
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=strict" in r.headers["set-cookie"].lower()

def test_wrong_token_and_no_cookie():
    c = client(); assert c.get("/?token=nope").status_code == 401 and c.get("/").status_code == 401
    assert "Session expired" in c.get("/").text

def test_dns_rebinding_blocked():
    c = client(); login(c)
    assert c.get("/", headers={"host": "evil.example:8765"}).status_code == 403

def test_csrf_required():
    c = client(); login(c)
    assert c.post("/act").status_code == 403
    assert c.post("/act", headers={"X-APD-CSRF": "wrong"}).status_code == 403

def test_csrf_ok_and_origin_checked(): ...   # fetch csrf via a route that echoes request.state.csrf; correct header → 200; same header + Origin http://evil → 403
def test_security_headers():
    c = client(); login(c); r = c.get("/")
    assert r.headers["content-security-policy"] == "default-src 'self'; frame-ancestors 'none'"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "no-referrer"
    assert "access-control-allow-origin" not in r.headers
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app/web/test_security.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the middleware**

Compare tokens with `hmac.compare_digest`. Read the CSRF form field only for `application/x-www-form-urlencoded` and `multipart/form-data` bodies, and replay the consumed body to the app.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app/web/test_security.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app/web tests/app/web/test_security.py
git commit -m "feat(web): add loopback-only security middleware"
```

### Task 6: Web pages, event stream and report serving

**Files:**

- Create: `tools/apd_gauntlet/app/web/server.py`, `templates/{base,runs,setup,new_run,run,report,expired}.html`, `static/{app.css,app.js}`
- Modify: `tools/apd_gauntlet/cli.py` (`web`), `pyproject.toml` (package data for templates and static)
- Test: `tests/app/web/test_routes.py`

**Interfaces:**

- Consumes: services, setup, `LocalOnlyMiddleware`, `read_events`
- Produces:
  - `def create_app(cfg: UserConfig, *, token: str, port: int) -> ASGIApp`
  - `def serve(cfg: UserConfig, *, port: int = 0, open_browser: bool = True) -> None` — binds `127.0.0.1`; port 0 picks a free port; prints and opens `http://127.0.0.1:<port>/?token=<token>`
  - CLI `web [--port N] [--no-browser]`

| Route | Method | Behavior |
|---|---|---|
| `/` | GET | Runs table from `list_runs` |
| `/setup` | GET, POST | Setup form (provider selects, password inputs, account ID, domains) → `apply_setup`; shows `test_summary` and warnings; never renders a stored key |
| `/keys/{name}` | POST | Store a key; `/keys/{name}/test` and `/keys/{name}/clear` POST |
| `/runs/new` | GET | New-run form: id, folder path or folder upload, domains, code recon, decision model |
| `/runs` | POST | Path mode → `create_run`; upload mode → stream files into a temp dir under the workspace, enforcing both limits while streaming, then `create_run`; `InputsRejected` → form re-rendered with the reason |
| `/runs/{id}` | GET | Progress page; consent checkbox shown with the egress notice when the run has a decision model |
| `/runs/{id}/start`, `/runs/{id}/cancel` | POST | `start_run(consent=form value)` / `cancel_run`; `AlreadyRunning` → message with PID |
| `/runs/{id}/events` | GET | `text/event-stream`; `id:` = line count; honors `Last-Event-ID`; polls `read_events` every 0.5 s; closes 5 s after `run_finished` |
| `/runs/{id}/report` | POST | `build_run_report` → 303 to `/runs/{id}/report/index.html` |
| `/runs/{id}/report/{path:path}` | GET | Static file from `report-html/` after `resolve()` containment and a no-symlink check; 404 otherwise |
| `/static/{path:path}` | GET | App CSS and JS |

Run ids in paths must match the run-id pattern `init_run` enforces; anything else → 404. `app.js` is the only script: it reads the CSRF value from `<meta name="apd-csrf">`, attaches `X-APD-CSRF` to `fetch` calls, and renders events into the phase list and log. No inline scripts or styles, so the CSP holds.

- [ ] **Step 1: Write the failing tests**

```python
def test_runs_page_lists_runs(web, cfg_ws, inputs_dir):
    create_run(cfg_ws, NewRunSpec("alpha", inputs_dir, ["pbm"]))
    assert "alpha" in web.get("/").text

def test_new_run_upload_limits(web, monkeypatch):
    monkeypatch.setattr(services, "MAX_INPUT_FILES", 2)
    files = [("files", (f"d/{i}.md", b"x", "text/markdown")) for i in range(3)]
    r = web.post("/runs", data={"run_id": "u1", "mode": "upload", "csrf": web.csrf}, files=files)
    assert r.status_code == 400 and "3 files" in r.text

def test_start_requires_consent_for_decision_model(web, cfg_ws, inputs_dir):
    create_run(cfg_ws, NewRunSpec("cf", inputs_dir, ["pbm"], decision_provider="cloudflare"))
    r = web.post("/runs/cf/start", data={"csrf": web.csrf})
    assert r.status_code == 400 and "will be sent to Cloudflare Workers AI" in r.text

def test_event_stream_resumes(web, run_with_events):
    r = web.get(f"/runs/{run_with_events.name}/events", headers={"Last-Event-ID": "2"})
    assert "id: 3" in r.text and "id: 1\n" not in r.text

def test_report_path_traversal(web, example_run):
    assert web.get(f"/runs/{example_run.name}/report/../../.apd-run.yaml").status_code == 404
    assert web.get(f"/runs/{example_run.name}/report/index.html").status_code == 200

def test_setup_never_echoes_key(web, memory_keyring, mock_transport):
    r = web.post("/setup", data={"csrf": web.csrf, "decision_provider": "openrouter", "decision_key": "sk-or-9999",
                                  "llm_provider": "anthropic", "workspace": str(web.cfg.workspace), "domains": "pbm"})
    assert r.status_code == 200 and "sk-or-9999" not in r.text and "…9999" not in r.text

def test_bad_run_id_404(web): assert web.get("/runs/..%2Fx").status_code == 404
```

The `web` fixture builds `create_app` behind `TestClient`, performs the token exchange and exposes `csrf` (read from the page's meta tag) and `cfg`. The event-stream test uses a run whose events file is complete, so the stream ends after `run_finished`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app/web/test_routes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the server, templates, CSS and JS**

Keep pages plain and readable: system font stack, one accent color, light and dark via `prefers-color-scheme`, a phase list with text states (not color alone), and forms with visible labels.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app/web -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app/web tools/apd_gauntlet/cli.py pyproject.toml tests/app/web
git commit -m "feat(web): add local web UI for setup, runs and reports"
```

### Task 7: Textual TUI

**Files:**

- Create: `tools/apd_gauntlet/app/tui/{__init__,app,screens}.py`
- Modify: `tools/apd_gauntlet/cli.py` (`tui`)
- Modify: `pyproject.toml` — the async tests need `pytest-asyncio>=1.0` in the `dev` extra and `asyncio_mode = "auto"` under `[tool.pytest.ini_options]` (pytest 9.1.1 fails bare `async def` tests); LA1 Task 4 adds the same, so skip this when it is already there
- Test: `tests/app/test_tui.py`

**Interfaces:**

- Consumes: services, setup, `read_events`
- Produces: `class ApdApp(textual.app.App)` with `def __init__(self, cfg: UserConfig)`; screens `HomeScreen`, `SetupScreen`, `NewRunScreen`, `RunScreen(run_id: str)`, `ReportScreen(run_id: str)`; CLI `tui`

| Screen | Content | Keys |
|---|---|---|
| Home | `DataTable` of runs (id, state, phase, spend, report) | `n` new, `s` setup, `enter` open run, `r` refresh, `q` quit |
| Setup | Same fields as the web form; password `Input`s; result panel | `ctrl+s` apply |
| New run | id, folder (`DirectoryTree` picker), domains (`SelectionList`), code recon and decision model (`Select`) | `ctrl+s` create |
| Run | phase list with text states, current steps, elapsed, spend vs budget, `RichLog` of events; consent modal with the egress notice before start | `g` start or resume, `c` cancel, `p` report |
| Report | metrics from `report_metrics`; build and open | `b` build, `o` open in browser |

The Run screen polls `read_events` every 0.5 s with `set_interval`; a run started elsewhere shows the same progress.

- [ ] **Step 1: Write the failing tests**

```python
async def test_home_lists_runs(cfg_ws, inputs_dir):
    create_run(cfg_ws, NewRunSpec("alpha", inputs_dir, ["pbm"]))
    async with ApdApp(cfg_ws).run_test(size=(80, 24)) as pilot:
        table = pilot.app.screen.query_one(DataTable)
        assert table.row_count == 1 and "alpha" in str(table.get_row_at(0))

async def test_start_shows_consent_for_decision_model(cfg_ws, inputs_dir, monkeypatch):
    create_run(cfg_ws, NewRunSpec("cf", inputs_dir, ["pbm"], decision_provider="cloudflare"))
    started = []; monkeypatch.setattr(services, "start_run", lambda *a, **k: started.append(k) or 1)
    async with ApdApp(cfg_ws).run_test(size=(80, 24)) as pilot:
        await pilot.press("enter", "g")
        assert "will be sent to Cloudflare Workers AI" in pilot.app.screen.query_one("#consent-text").content
        await pilot.click("#consent-yes")
        assert started and started[0]["consent"] is True

async def test_run_screen_follows_events(cfg_ws, run_with_events): ...  # RunScreen shows the phase from the last phase_started event
async def test_new_run_reports_rejection(cfg_ws, inputs_with_escape): ... # error text contains "symlink"
async def test_fits_80x24(cfg_ws): ...                                   # every screen mounts at size (80, 24) without exceptions
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app/test_tui.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the app and screens**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app/test_tui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app/tui tools/apd_gauntlet/cli.py pyproject.toml tests/app/test_tui.py
git commit -m "feat(tui): add Textual interface for setup, runs and reports"
```

### Task 8: Packaging, docs and release bump

**Files:**

- Modify: `pyproject.toml`, `README.md`, `docs/QUICKSTART.md`, `CHANGELOG.md`, `tests/integration/test_wheel_install_smoke.py`
- Create: `docs/local-apps.md`, `docs/adrs/0026-local-web-ui-security.md`

- [ ] **Step 1: Extend the wheel smoke test**

Install `.[app]` into the isolated venv and assert `apd-gauntlet --help` lists `setup`, `doctor`, `new`, `runs`, `run`, `status`, `cancel`, `report`, `decide`, `keys`, `tui` and `web`, and that `importlib.resources` finds `app/web/templates/base.html`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest -m wheel tests/integration/test_wheel_install_smoke.py -v`
Expected: FAIL until the extras and package data are added

- [ ] **Step 3: Add extras and package data; write the docs**

The extras take the Global Constraints pins (`textual>=8.2,<9`, `starlette>=1.0,<2`). CI runs the app tests on Python 3.10 and 3.12 (Starlette 1.8 and platformdirs 4.13 need 3.11; 3.10 resolves older versions).

Below the 2.0 pre-release notice, the README opens with the golden path from spec §8.1. The CHANGELOG entry goes under "Unreleased — 2.0 line". `docs/QUICKSTART.md` becomes that path plus one section each for the TUI and web UI. `docs/local-apps.md` covers the screens, the web security posture and the data-egress notice. ADR-0026 records spec §8.5.

- [ ] **Step 4: Run the full suite, the wheel test and markdownlint**

Run: `pytest -q && pytest -m wheel -q && npx markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" README.md CHANGELOG.md`
Expected: all pass, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md docs CHANGELOG.md tests/integration/test_wheel_install_smoke.py
git commit -m "feat(app): extras, package data and docs for the local apps"
```
