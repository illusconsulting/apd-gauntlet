# IaC Plan 1 — Resolution and Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve every Terraform, OpenTofu and Atmos component instance a run declares into a normalised, scanner-ready workspace, with nothing from the client repository executing, and record instances, unknowns, overrides and execution points in an engine-minted evidence index produced by a new `iac` phase.

**Architecture:** A shared process gateway (`apd_gauntlet.sandbox.tools.run_tool`) is the only place a subprocess starts; it enforces a per-tool argument allowlist, a scrubbed environment, a closed-port proxy and per-call isolation. A fixed pipeline in `apd_gauntlet/iac/` discovers roots, picks an engine, sanitises and resolves Atmos stacks, builds one normalised workspace per instance, fetches remote modules only with recorded consent, and writes `00-context/iac-evidence-index.yaml` plus `00-context/iac-summary.md`. `apd-gauntlet iac run <run-dir>` runs it as the `iac` phase between `setup` and `intake` in the workflow, `plan-run` and the runner.

**Tech Stack:** Python 3.10–3.12, click, PyYAML, jsonschema (Draft 2020-12), python-hcl2 7.x (extra `iac`), external tools Atmos 1.231.0, OpenTofu ≥ 1.8.0, Trivy 0.70.0, Checkov 3.3.26, ShellCheck ≥ 0.9; pytest with a fake `run_tool` and an `iac_tools` marker for real-tool tests.

**Spec:** `docs/superpowers/specs/2026-10-10-iac-terraform-opentofu-atmos-design.md` §4, §5, §6, §7.1–§7.5, §7.10 (Atmos and HCL points), §7.11, §8.1 (skeleton), §12, §13.1, §13.4, §14, §15 item 1. Master plan `docs/superpowers/plans/2026-10-10-program-master-plan.md` R1 (`iac run`, `iac consent`), R2 (`run_tool`), R3 (`iac` phase), R4, R6, R7 (`iac-evidence-index` skeleton), R8, A3. This is Plan 1 of 4; Plans 2–4 consume the Interfaces blocks below.

## Global Constraints

- Python floor `>=3.10`; `ruff check tools/ tests/`, `mypy tools/` (strict on `tools/apd_gauntlet`), `pytest`, coverage `fail_under = 85` and `markdownlint-cli2` stay green.
- **Nothing from a client repository executes.** Every external tool runs through `apd_gauntlet.sandbox.run_tool` (master plan Global Constraints); `sandbox/tools.py` is the only module that imports `subprocess` under `tools/apd_gauntlet/sandbox` and `tools/apd_gauntlet/iac`.
- `run_tool(tool: str, args: list[str], *, cwd: Path, network: bool = False, timeout_s: int) -> ToolResult`, where `ToolResult` is `(returncode: int, stdout: str, stderr: str, duration_s: float)` (R2).
- Accepted invocations (spec §7.1): `atmos describe stacks|component` (every call carries `--process-functions=false`, the gateway rejects any call without it); `tofu get`; `trivy config`; `checkov -d|-f`; `shellcheck -f json`. Version queries for `doctor` are the only additions. Anything else raises `ToolNotAllowed`.
- Scrubbed environment (spec §7.1): empty start; `PATH` to the resolved tool directory; `HOME` and `TMPDIR` to a fresh temp directory; `LANG`; `GIT_TERMINAL_PROMPT=0`; `GIT_SSH_COMMAND=false`. No cloud, Terraform, OpenTofu, Atmos, GitHub or SSH variables pass through.
- Egress: with `network=False`, `HTTP_PROXY`, `HTTPS_PROXY` and `ALL_PROXY` point at a closed local port. Only the consented fetch gets the operator's real proxy settings.
- Atmos functions are always off (`--process-functions=false`); function literals become `unknown` entries. `!terraform.output` and `!terraform.state` also become component-dependency edges; `!exec` is also an execution point.
- Minimum tool versions (spec §14): Atmos 1.231.0, OpenTofu 1.8.0, Trivy 0.70.0, Checkov 3.3.26, ShellCheck 0.9. The Terraform binary is never invoked.
- Every run-config path is relative to `inputs/` and matches `^(?!/)(?!.*\.\.).+$`.
- All work happens under `<run>/.apd-state/iac/`. `inputs/` is never modified.
- Ids are minted by the engine as `iev-` plus the first 8 hex characters of a SHA-256 over the instance, address, kind and check id. Output ordering is stable.
- Evidence excerpts are at most 25 whitespace-separated tokens (`linters.check_excerpt_length`) and at most 500 characters (`finding.schema.json` `evidence[].excerpt.maxLength`).
- `consent.json` is keyed by subject; this plan owns `"iac_module_fetch": {"sources": [...], "sources_sha256": "...", "granted_at": "...", "method": "..."}` (R6).
- New schemas `$ref` `_defs.schema.json#/$defs/apd_goal` and never inline a centralised vocabulary (`tests/test_schema_vocab_centralized.py`).
- Tests never touch the network (ADR-0017 covers tests and real runs). The `iac-tools` CI job's setup step downloads the pinned tool binaries before any test starts; the tests it then runs stay offline. Unit tests use a fake `run_tool`; real-tool tests carry `@pytest.mark.iac_tools` and skip when a tool is absent.
- Behaviour-changing tasks gate against the previous accepted state: the master plan Task 1 set run on the last accepted commit is the baseline, and `apd-gauntlet compare-runs <previous-accepted> <candidate> --gates eval/gates.yaml` must exit 0.

## Review Focus

- **A hostile Atmos repository** (`!exec`, a Go template calling `atmos.Component`, an absolute `components.terraform.command` pointing into the repo): no canary file is ever created. Pinned by Task 6 `test_template_atmos_calls_rewritten` and Task 13 `test_exec_canary_never_created`, `test_template_component_canary_never_created`.
- **An include that escapes the root** (`!include /etc/hostname`, an absolute outside path, a URL, a `..` path, an escaping symlink): rewritten to a literal and recorded as `unknown`; outside content never reaches an output and no connection is attempted. Pinned by Task 6 `test_outside_and_remote_includes_rewritten` and Task 13 `test_outside_include_content_never_in_outputs`, `test_remote_include_makes_no_connection`.
- **A module directory with both `main.tf` and `main.tofu`, a `.tofu`-only directory, or an override file:** the workspace holds exactly what OpenTofu loads, as `.tf` names, and every overridden block is recorded. Pinned by Task 9 `test_tofu_precedence_and_rename`, `test_tofu_only_dir_renamed`, `test_override_blocks_recorded`.
- **Atmos missing or older than 1.231.0:** the root is `unresolved-raw` and the phase exits 0; with `require_tools: true` it exits 1. Pinned by Task 11 `test_missing_atmos_marks_root_unresolved_raw`, `test_require_tools_fails_phase`.
- **Two consent subjects:** fetch consent is never implied by decision-model consent, writing it preserves the other subject, and a changed source list invalidates it; without consent the phase continues with remote modules recorded as unknown. Pinned by Task 8 `test_decision_consent_does_not_grant_fetch`, `test_record_preserves_other_subject`, `test_changed_sources_invalidate_consent`, and Task 11 `test_fetch_without_consent_continues`.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/sandbox/__init__.py` | Re-export `run_tool`, `register_invocation`, `ToolNotAllowed`, `ToolResult`, `ToolRunner` | Create |
| `tools/apd_gauntlet/sandbox/tools.py` | The only process gateway | Create |
| `tools/apd_gauntlet/iac/__init__.py` | Package marker; registers IaC invocations on import | Create |
| `tools/apd_gauntlet/iac/invocations.py` | Argument validators and fixed env for the five tools | Create |
| `tools/apd_gauntlet/iac/toolcheck.py` + `data/iac/tools.yaml` | Tool presence, version, minimums, install hints | Create |
| `tools/apd_gauntlet/iac/model.py` | Shared dataclasses and literal types | Create |
| `tools/apd_gauntlet/iac/config.py` | Run-config `infrastructure` loader | Create |
| `tools/apd_gauntlet/iac/hcl.py` | python-hcl2 block parser and line helpers | Create |
| `tools/apd_gauntlet/iac/discover.py` | Root discovery | Create |
| `tools/apd_gauntlet/iac/engine.py` | Engine selection and file precedence | Create |
| `tools/apd_gauntlet/iac/atmos.py` | Sanitise, resolve, provenance | Create |
| `tools/apd_gauntlet/iac/workspace.py` | Normalised workspace per instance | Create |
| `tools/apd_gauntlet/iac/consent.py` | `has_fetch_consent`, `record_fetch_consent` | Create |
| `tools/apd_gauntlet/iac/fetch.py` | Module source listing and consented fetch | Create |
| `tools/apd_gauntlet/iac/inventory.py` | Atmos and HCL execution points | Create |
| `tools/apd_gauntlet/iac/index.py` | Id minting, excerpts, index document, writer | Create |
| `tools/apd_gauntlet/iac/summary.py` | `iac-summary.md` renderer | Create |
| `tools/apd_gauntlet/iac/pipeline.py` | `run_iac`, `collect_fetch_sources`, stamp | Create |
| `tools/apd_gauntlet/iac/cli.py` | `iac run`, `iac consent` | Create |
| `tools/apd_gauntlet/iac/doctor.py` | `doctor` checks via `register_doctor_check` | Create |
| `tools/apd_gauntlet/data/schemas/iac-evidence-index.schema.json` | Index schema skeleton | Create |
| `tools/apd_gauntlet/data/schemas/run-config.schema.json:95-118` | `infrastructure` additions (R4) | Modify |
| `tools/apd_gauntlet/cli.py` | Register the `iac` group; register doctor checks | Modify |
| `tools/apd_gauntlet/plan_run.py:48-56` | `iac` step after setup | Modify |
| `.claude/workflows/apd-gauntlet.js:36-45`, `:265-313` | `iac` phase literal and step | Modify |
| `tools/apd_gauntlet/runner/flow.py` | `iac` phase and `iac-run` step | Modify |
| `pyproject.toml` | extra `iac`, dev `python-hcl2`, package data `data/iac/*.yaml`, marker `iac_tools` | Modify |
| `.github/workflows/python-tests.yml` | `iac-tools` job with pinned tools | Modify |
| `docs/iac-evaluation.md`, `docs/adrs/0027-iac-evaluation-pipeline.md`, `docs/schema-evolution.md`, `CHANGELOG.md`, `docs/running-the-gauntlet.md:359` | Docs | Create/Modify |
| `tests/iac/…`, `tests/fixtures/iac/…`, `tests/test_adr_0027.py` | Tests and fixtures | Create |
| `tests/test_workflow_apd_gauntlet.py:27-49`, `tests/test_cli_plan_run.py`, `tests/runner/test_flow_pre_synthesis.py`, `tests/test_run_config_schema.py` | Extended tests | Modify |

---

### Task 1: Process gateway `run_tool`

**Files:**

- Create: `tools/apd_gauntlet/sandbox/__init__.py`, `tools/apd_gauntlet/sandbox/tools.py`, `tests/iac/__init__.py`, `tests/iac/conftest.py`
- Modify: `pyproject.toml` (`[tool.pytest.ini_options].markers` gains `"iac_tools: needs Atmos, Trivy, Checkov or OpenTofu on PATH at pinned versions (skipped when absent)"`)
- Test: `tests/iac/test_sandbox_tools.py`

**Interfaces:**

- Produces (`apd_gauntlet.sandbox.tools`):
  - `class ToolResult(NamedTuple): returncode: int; stdout: str; stderr: str; duration_s: float`
  - `class ToolNotAllowed(Exception)`
  - `Validator = Callable[[list[str]], None]` (raises `ToolNotAllowed` with the reason)
  - `def register_invocation(tool: str, validator: Validator, *, helpers: Sequence[str] = (), env: Mapping[str, str] | None = None, allow_network: bool = False) -> None` — re-registering a tool replaces its entry
  - `def run_tool(tool: str, args: list[str], *, cwd: Path, network: bool = False, timeout_s: int) -> ToolResult`
  - `class ToolRunner(Protocol)` with the same `__call__` signature as `run_tool` (dependency injection for Plans 1–4)
  - Constants: `CLOSED_PROXY = "http://127.0.0.1:9"`, `DEFAULT_OUTPUT_CAP = 64 * 1024 * 1024`, `TIMEOUT_RETURNCODE = 124`, `OUTPUT_CAP_RETURNCODE = 125`, `NOT_FOUND_RETURNCODE = 127`, `NETWORK_ENV_PASSTHROUGH = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "no_proxy", "all_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR")`
- Produces (`tests/iac/conftest.py`): fixture `require_tools(*names)` that calls `pytest.skip` when `shutil.which(name)` is None; fixture `fake_tool(tmp_path, monkeypatch)` that writes an executable `/bin/sh` script into a temp bin dir, prepends it to `PATH`, and returns its path.

- [ ] **Step 1: Write the failing tests**

```python
ACCEPT_ALL: Validator = lambda args: None

def test_unregistered_tool_raises(tmp_path):
    with pytest.raises(ToolNotAllowed, match="not registered"):
        run_tool("nope", [], cwd=tmp_path, timeout_s=5)

def test_rejected_args_never_reach_subprocess(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(sandbox_tools.subprocess, "Popen", lambda *a, **k: calls.append(a))
    def deny(args): raise ToolNotAllowed("bad")
    register_invocation("apd-test-deny", deny)
    with pytest.raises(ToolNotAllowed, match="bad"):
        run_tool("apd-test-deny", ["x"], cwd=tmp_path, timeout_s=5)
    assert calls == []

def test_env_scrubbed_and_proxy_closed(tmp_path, fake_tool, monkeypatch):
    fake_tool("apd-test-env", "/usr/bin/env; pwd")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "CANARY-AWS"); monkeypatch.setenv("HTTPS_PROXY", "http://real:3128")
    monkeypatch.setenv("TF_VAR_x", "CANARY-TF"); monkeypatch.setenv("GITHUB_TOKEN", "CANARY-GH")
    register_invocation("apd-test-env", ACCEPT_ALL, env={"ATMOS_TELEMETRY_ENABLED": "false"})
    r = run_tool("apd-test-env", [], cwd=tmp_path, timeout_s=10)
    env = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
    assert "CANARY" not in r.stdout
    assert env["HTTPS_PROXY"] == env["HTTP_PROXY"] == env["ALL_PROXY"] == CLOSED_PROXY
    assert env["GIT_TERMINAL_PROMPT"] == "0" and env["GIT_SSH_COMMAND"] == "false"
    assert env["ATMOS_TELEMETRY_ENABLED"] == "false"
    assert len(env["PATH"].split(os.pathsep)) == 1 and not Path(env["HOME"]).exists()

def test_network_requires_registration(tmp_path, fake_tool):
    fake_tool("apd-test-net", "/usr/bin/env")
    register_invocation("apd-test-net", ACCEPT_ALL)
    with pytest.raises(ToolNotAllowed, match="network"):
        run_tool("apd-test-net", [], cwd=tmp_path, network=True, timeout_s=5)

def test_network_passes_real_proxy(tmp_path, fake_tool, monkeypatch):
    fake_tool("apd-test-net2", "/usr/bin/env")
    monkeypatch.setenv("HTTPS_PROXY", "http://real:3128")
    register_invocation("apd-test-net2", ACCEPT_ALL, allow_network=True)
    assert "HTTPS_PROXY=http://real:3128" in run_tool("apd-test-net2", [], cwd=tmp_path, network=True, timeout_s=5).stdout

def test_private_path_holds_only_tool_and_helpers(tmp_path, fake_tool):
    fake_tool("apd-test-ls", '/bin/ls "$(/usr/bin/dirname "$0")"')
    register_invocation("apd-test-ls", ACCEPT_ALL, helpers=["sh"])
    assert run_tool("apd-test-ls", [], cwd=tmp_path, timeout_s=5).stdout.split() == ["apd-test-ls", "sh"]

def test_timeout_returns_124(tmp_path, fake_tool):
    fake_tool("apd-test-sleep", "/bin/sleep 5")
    register_invocation("apd-test-sleep", ACCEPT_ALL)
    r = run_tool("apd-test-sleep", [], cwd=tmp_path, timeout_s=1)
    assert r.returncode == TIMEOUT_RETURNCODE and "timed out" in r.stderr

def test_output_cap_returns_125(tmp_path, fake_tool, monkeypatch):
    monkeypatch.setattr(sandbox_tools, "DEFAULT_OUTPUT_CAP", 1000)
    fake_tool("apd-test-big", "/usr/bin/yes | /usr/bin/head -c 5000")
    register_invocation("apd-test-big", ACCEPT_ALL)
    assert run_tool("apd-test-big", [], cwd=tmp_path, timeout_s=5).returncode == OUTPUT_CAP_RETURNCODE

def test_missing_binary_returns_127(tmp_path):
    register_invocation("apd-test-absent", ACCEPT_ALL)
    assert run_tool("apd-test-absent", [], cwd=tmp_path, timeout_s=5).returncode == NOT_FOUND_RETURNCODE
```

A fixture in `test_sandbox_tools.py` removes every `apd-test-*` key from `sandbox_tools._REGISTRY` after each test.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_sandbox_tools.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.sandbox`)

- [ ] **Step 3: Implement `run_tool` and `register_invocation` in `tools/apd_gauntlet/sandbox/tools.py`**

Order inside `run_tool`: look up `_REGISTRY[tool]` (else `ToolNotAllowed("<tool> is not registered")`); refuse `network=True` unless `allow_network`; call the validator; resolve the binary with `shutil.which(tool)` (absent → `ToolResult(127, "", "<tool>: not found on PATH", 0.0)`); create a call directory with `tempfile.mkdtemp(prefix="apd-tool-")` holding `bin/` (symlinks to the tool and each helper resolved with `shutil.which`), `home/`, `tmp/`, `out`, `err`; build the environment from `{PATH: <call>/bin, HOME, TMPDIR, LANG: "C.UTF-8", GIT_TERMINAL_PROMPT: "0", GIT_SSH_COMMAND: "false"}`, then the six proxy names (upper and lower case) set to `CLOSED_PROXY` and `NO_PROXY=""`, or, when `network=True`, the `NETWORK_ENV_PASSTHROUGH` values copied from `os.environ`; then the registration's fixed `env`. Start `subprocess.Popen([<call>/bin/<tool>, *args], cwd=cwd, env=env, stdin=DEVNULL, stdout=<out>, stderr=<err>, start_new_session=True)`; on `TimeoutExpired` kill the process group (`os.killpg`, `proc.kill()` where `os.killpg` is unavailable) and return 124. Read at most `DEFAULT_OUTPUT_CAP` bytes of each stream (decode `utf-8`, `errors="replace"`); a larger stream returns 125 with `"output exceeded cap"` appended to stderr. Remove the call directory in a `finally`.

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_sandbox_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/sandbox tests/iac pyproject.toml
git commit -m "feat(sandbox): add the run_tool process gateway"
```

### Task 2: IaC invocation allowlist and tool inventory

**Files:**

- Create: `tools/apd_gauntlet/iac/__init__.py`, `tools/apd_gauntlet/iac/invocations.py`, `tools/apd_gauntlet/iac/toolcheck.py`, `tools/apd_gauntlet/data/iac/tools.yaml`, `tests/iac/fakes.py`
- Modify: `pyproject.toml` (`[tool.setuptools.package-data]` gains `"data/iac/*.yaml"`; `[project.optional-dependencies]` gains `iac = ["python-hcl2>=7,<8"]`; `dev` gains `"python-hcl2>=7,<8"`), `tests/iac/conftest.py` (fixture `fake_runner`)
- Test: `tests/iac/test_invocations.py`, `tests/iac/test_toolcheck.py`

**Interfaces:**

- Consumes: `register_invocation`, `ToolNotAllowed`, `ToolRunner`, `ToolResult` (Task 1)
- Produces:
  - `invocations.py`: `def validate_atmos(args: list[str]) -> None`, `validate_tofu`, `validate_trivy`, `validate_checkov`, `validate_shellcheck` (same signature); `VALIDATORS: dict[str, Validator]` keyed by tool name; `ATMOS_ENV = {"ATMOS_TELEMETRY_ENABLED": "false", "ATMOS_VERSION_CHECK_ENABLED": "false"}`; `CHECKOV_ENV = {"CHECKOV_EXPERIMENTAL_TERRAFORM_MANAGED_MODULES": "True"}`; `TOFU_ENV = {"TF_INPUT": "0", "TF_IN_AUTOMATION": "1", "CHECKPOINT_DISABLE": "1", "GIT_CONFIG_NOSYSTEM": "1"}`; `def register_iac_invocations() -> None` (idempotent; `tofu` gets `helpers=("git",)` and `allow_network=True`)
  - Argument builders (the only way Plans 1–3 compose scanner calls): `def trivy_config_args(target: Path, *, plan: bool = False, tf_vars: Sequence[Path] = (), include_passed: bool = False, ignorefile: Path | None = None) -> list[str]` (`ignorefile` adds `--ignorefile <path>`; Plan 2 Task 3 passes a copy of the client's ignore file only on the run that measures what the client suppresses); `def checkov_args(target: Path, *, plan: bool = False, var_files: Sequence[Path] = ()) -> list[str]` (`-f` with `--framework terraform_plan` when `plan`, else `-d` with `--framework terraform`); `def shellcheck_args(paths: Sequence[Path]) -> list[str]`
  - `toolcheck.py`: `@dataclass(frozen=True) class ToolSpec: name: str; minimum: str; required_for: str; version_args: tuple[str, ...]; timeout_s: int; install: dict[str, str]`; `def load_tool_specs() -> dict[str, ToolSpec]`; `@dataclass(frozen=True) class ToolStatus: name: str; found: bool; version: str | None; minimum: str; ok: bool; detail: str`; `def parse_version(name: str, stdout: str) -> str | None`; `def version_at_least(found: str, minimum: str) -> bool`; `def tool_status(name: str, *, runner: ToolRunner = run_tool) -> ToolStatus`; `def install_hint(name: str, platform: str | None = None) -> str` (`platform` defaults to `sys.platform`)
  - `iac/__init__.py` calls `register_iac_invocations()`.

Exact accepted argument vectors (any other vector raises `ToolNotAllowed`; a value slot never starts with `-`; stack and component slots match `^[A-Za-z0-9_./-]+$`; path slots are absolute):

| Tool | Accepted vectors |
|---|---|
| `atmos` | `version --format json`; `describe stacks -s <stack> --format json --process-functions=false [--process-templates=false]`; `describe component <component> -s <stack> --format yaml --process-functions=false [--process-templates=false]` |
| `tofu` | `version -json`; `get` |
| `trivy` | `--version --format json`; `config --skip-check-update --disable-telemetry --skip-version-check --format json --misconfig-scanners terraform\|terraformplan-json [--quiet] [--include-non-failures] [--tf-vars <path>]… [--ignorefile <path>] <path>` (flags in any order before the final `<path>`; the builder omits `--quiet` because Trivy 0.70.0 reports HCL parse errors only on stderr, exits 0 and silently drops the file, and `--quiet` suppresses that line; `-c`/`--config` is rejected) |
| `checkov` | `--version`; `-d <dir>\|-f <file> --framework terraform\|terraform_plan -o json --skip-download --download-external-modules false --soft-fail [--var-file <path>]…` (flags in any order) |
| `shellcheck` | `--version`; `-f json --norc <path>…` |

`data/iac/tools.yaml` rows: `atmos {minimum: "1.231.0", required_for: "Atmos roots", version_args: [version, --format, json], timeout_s: 120}`, `tofu {minimum: "1.8.0", required_for: "Module fetch only", version_args: [version, -json], timeout_s: 600}`, `trivy {minimum: "0.70.0", required_for: "Baseline scanning", version_args: [--version, --format, json], timeout_s: 600}`, `checkov {minimum: "3.3.26", required_for: "Relationship checks", version_args: [--version], timeout_s: 900}`, `shellcheck {minimum: "0.9", required_for: "Script checks (optional)", version_args: [--version], timeout_s: 60}`; each with `install: {darwin, linux, win32}` commands (`brew install atmos`, `pipx install checkov`, and so on).

- [ ] **Step 1: Verify the flags this task pins**

Run each with the scratch tools and confirm the listed flags appear: `atmos describe stacks --help`, `atmos describe component --help`, `atmos version --help`, `trivy config --help`, `checkov --help`. Then record, as the first line of `invocations.py`'s module docstring, the assumptions still unverified for tools not installed here: `tofu version -json`, `tofu get`, `TF_INPUT`, `TF_IN_AUTOMATION`, `CHECKPOINT_DISABLE`, `shellcheck --norc`. Expected: every Atmos, Trivy and Checkov flag present, including Trivy's `--ignorefile string  specify .trivyignore file (default ".trivyignore")` (verified on 2026-10-11 against Atmos 1.231.0, Trivy 0.70.0, Checkov 3.3.26). If OpenTofu or ShellCheck is on PATH, run `tofu get -help` and `shellcheck --help` and correct the table before Step 2.

- [ ] **Step 2: Write the failing tests**

```python
ACCEPTED = [
    ("atmos", ["describe", "stacks", "-s", "orgs/prod", "--format", "json", "--process-functions=false"]),
    ("atmos", ["describe", "stacks", "-s", "orgs/prod", "--format", "json", "--process-functions=false", "--process-templates=false"]),
    ("atmos", ["describe", "component", "vpc", "-s", "prod", "--format", "yaml", "--process-functions=false"]),
    ("atmos", ["version", "--format", "json"]),
    ("tofu", ["get"]),
    ("trivy", ["config", "--skip-check-update", "--disable-telemetry", "--skip-version-check",
               "--format", "json", "--misconfig-scanners", "terraform", "--tf-vars", "/w/apd.auto.tfvars.json", "/w"]),
    ("trivy", ["config", "--skip-check-update", "--disable-telemetry", "--skip-version-check",
               "--format", "json", "--misconfig-scanners", "terraform", "--ignorefile", "/s/ignore/1a2b3c4d.trivyignore", "/w"]),
    ("checkov", ["-d", "/w", "--framework", "terraform", "-o", "json", "--skip-download",
                 "--download-external-modules", "false", "--soft-fail", "--var-file", "/w/a.tfvars"]),
    ("shellcheck", ["-f", "json", "--norc", "/w/x.sh"]),
]
REJECTED = [
    ("atmos", ["describe", "stacks", "-s", "prod", "--format", "json"]),                       # functions on
    ("atmos", ["describe", "stacks", "-s", "prod", "--format", "json", "--process-functions=true"]),
    ("atmos", ["terraform", "plan", "vpc", "-s", "prod"]),
    ("atmos", ["describe", "stacks", "-s", "prod", "--format", "json", "--process-functions=false", "--use-version=1.0.0"]),
    ("atmos", ["describe", "stacks", "-s", "--ai", "--format", "json", "--process-functions=false"]),
    ("tofu", ["init"]), ("tofu", ["get", "-update"]), ("tofu", ["plan"]),
    ("trivy", ["config", "--format", "json", "--misconfig-scanners", "terraform", "/w"]),       # update not skipped
    ("trivy", ["image", "alpine"]),
    ("trivy", ["config", "--skip-check-update", "--disable-telemetry", "--skip-version-check",
               "--format", "json", "--misconfig-scanners", "terraform", "--ignorefile", "rel/.trivyignore", "/w"]),  # relative path
    ("trivy", ["config", "--skip-check-update", "--disable-telemetry", "--skip-version-check",
               "--format", "json", "--misconfig-scanners", "terraform", "-c", "/w/trivy.yaml", "/w"]),            # client config
    ("checkov", ["-d", "/w", "--framework", "terraform", "-o", "json", "--soft-fail"]),        # downloads allowed
    ("checkov", ["-d", "/w", "--framework", "terraform", "-o", "json", "--skip-download",
                 "--download-external-modules", "true", "--soft-fail"]),
    ("checkov", ["-d", "/w", "--external-checks-git", "https://x", "--framework", "terraform", "-o", "json",
                 "--skip-download", "--download-external-modules", "false", "--soft-fail"]),
    ("shellcheck", ["-f", "tty", "/w/x.sh"]),
    ("terraform", ["init"]),
]

@pytest.mark.parametrize("tool,args", ACCEPTED)
def test_accepted(tool, args): VALIDATORS[tool](args)

@pytest.mark.parametrize("tool,args", REJECTED)
def test_rejected(tool, args):
    with pytest.raises((ToolNotAllowed, KeyError)):
        VALIDATORS[tool](args)

def test_only_iac_tools_registered_by_package():
    import apd_gauntlet.iac  # noqa: F401
    assert {"atmos", "tofu", "trivy", "checkov", "shellcheck"} <= set(sandbox_tools._REGISTRY)
    assert "terraform" not in sandbox_tools._REGISTRY
```

```python
def test_builders_produce_accepted_vectors(tmp_path):
    validate_trivy(trivy_config_args(tmp_path, tf_vars=[tmp_path / "a.json"], include_passed=True))
    validate_trivy(trivy_config_args(tmp_path / "plan.json", plan=True))
    validate_trivy(trivy_config_args(tmp_path, ignorefile=tmp_path / "client.trivyignore.yaml"))
    validate_checkov(checkov_args(tmp_path, var_files=[tmp_path / "a.tfvars"]))
    validate_checkov(checkov_args(tmp_path / "plan.json", plan=True))
    validate_shellcheck(shellcheck_args([tmp_path / "x.sh"]))
```

```python
def test_version_parsing():
    assert parse_version("atmos", '{"version": "1.231.0", "os": "linux"}') == "1.231.0"
    assert parse_version("trivy", '{"Version":"0.70.0"}') == "0.70.0"
    assert parse_version("checkov", "3.3.26\n") == "3.3.26"
    assert parse_version("tofu", '{"terraform_version": "1.10.6"}') == "1.10.6"
    assert parse_version("shellcheck", "ShellCheck - shell script analysis tool\nversion: 0.9.0\n") == "0.9.0"

def test_version_compare():
    assert version_at_least("1.231.0", "1.231.0") and not version_at_least("1.230.9", "1.231.0")
    assert version_at_least("0.10", "0.9")

def test_status_below_minimum_is_not_ok(fake_runner):
    fake_runner.on("atmos", ["version", "--format", "json"], stdout='{"version": "1.200.0"}')
    s = tool_status("atmos", runner=fake_runner)
    assert s.found and not s.ok and "below minimum 1.231.0" in s.detail

def test_status_missing(fake_runner):
    fake_runner.on("trivy", ["--version", "--format", "json"], returncode=127)
    assert not tool_status("trivy", runner=fake_runner).found

def test_install_hint_per_platform():
    assert "pipx install checkov" in install_hint("checkov", "linux")
```

Add `tests/iac/fakes.py` with `class FakeRunner` (conforms to `ToolRunner`; `on(tool, args_prefix, *, returncode=0, stdout="", stderr="", effect=None)` registers a response; a call is answered by the most recently registered response whose argument prefix the call's arguments start with, so a test overrides a fixture's default by registering again; `effect` is a callable run with `cwd` before returning; `calls: list[tuple[str, list[str], Path, bool]]`; an unmatched call raises `AssertionError`), a `fake_runner` fixture, and a `tools_ok` fixture that registers each tool's version response at its minimum version, in `tests/iac/conftest.py`.

- [ ] **Step 3: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_invocations.py tests/iac/test_toolcheck.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.iac`)

- [ ] **Step 4: Implement the validators, the data file and `toolcheck.py`**

Validators parse the vector against the table with an explicit flag set per form and raise `ToolNotAllowed("<tool>: <reason>")` on the first unknown flag, missing required flag or bad slot. `tool_status` runs `runner(name, list(spec.version_args), cwd=Path(tempfile.gettempdir()), timeout_s=30)`; returncode 127 → `found=False`.

- [ ] **Step 5: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/iac tools/apd_gauntlet/data/iac pyproject.toml tests/iac
git commit -m "feat(iac): add the tool argument allowlist and tool inventory"
```

### Task 3: Run-config `infrastructure` additions and the IaC config loader

**Files:**

- Modify: `tools/apd_gauntlet/data/schemas/run-config.schema.json:95-118`
- Create: `tools/apd_gauntlet/iac/model.py`, `tools/apd_gauntlet/iac/config.py`, `tests/fixtures/valid/run-config-with-iac.yaml`, `tests/fixtures/invalid/run-config-iac-bad-engine.yaml`, `tests/fixtures/invalid/run-config-iac-traversal.yaml`
- Modify: `tests/iac/conftest.py` (helpers `write_run`, `copy_fixture`, `run_with_fixture`, `load_index`, `tree_digest`, `grep_tree`)
- Test: `tests/test_run_config_schema.py` (extend), `tests/iac/test_config.py`

**Interfaces:**

- Produces (schema, R4): under `infrastructure.static`, `terraform.items` becomes `oneOf: [<the existing guarded string>, {type: object, additionalProperties: false, required: [root], properties: {root: <guarded string>, var_files: {array of guarded strings}, engine: {enum: [opentofu, terraform]}}}]`; `atmos: {array of {additionalProperties: false, required: [root], properties: {root: <guarded string>, stacks: {array of strings, minLength 1}}}}`. Under `infrastructure`: `modules: {additionalProperties: false, properties: {fetch: {type: boolean}}}`; `plans: {array of {additionalProperties: false, required: [path], properties: {path: <guarded string>, stack: string, component: string, root: <guarded string>}}}`; `require_tools: {type: boolean}`.
- Produces (`model.py`):
  - `Engine = Literal["opentofu", "terraform"]`; `FetchStatus = Literal["fetched", "local", "not_fetched", "partial"]`; `RootStatus = Literal["resolved", "partial", "unresolved-raw"]`
  - `UnknownReason = Literal["function_literal", "template_unresolved", "outside_include", "remote_include", "remote_import", "gomplate_datasource", "escaping_symlink", "multiline_rewrite", "stack_unresolved", "component_not_committed", "root_refused", "escaping_module_source", "remote_module_not_fetched", "credentials_required", "module_fetch_failed", "early_eval_unresolved", "parse_error", "tool_missing", "tool_failed", "internal_error"]`
  - `ExecutionKind = Literal["atmos_exec", "atmos_custom_command", "atmos_workflow_shell", "atmos_hook", "atmos_component_command", "local_exec", "remote_exec", "external_data", "provisioner_resource"]`
  - `@dataclass(frozen=True) class Unknown: reason: UnknownReason; file_path: str; line: int; detail: str; root: str | None = None; instance: str | None = None; address: str | None = None; key: str = ""`
  - `@dataclass(frozen=True) class ExecutionPoint: kind: ExecutionKind; file_path: str; line: int; detail: str; root: str | None = None; instance: str | None = None; address: str | None = None`
  - `@dataclass(frozen=True) class Override: instance: str; address: str; file_path: str; start: int; end: int; overrides_file: str | None`
  - `@dataclass(frozen=True) class VarOrigin: file: str; line: int | None; value: Any`
  - `@dataclass class Instance: id: str; root: str; module_path: str; engine: Engine; stack: str | None = None; component: str | None = None; vars: dict[str, Any] = field(default_factory=dict); unknown_vars: list[str] = field(default_factory=list); provenance: dict[str, VarOrigin] = field(default_factory=dict); inherited: dict[str, VarOrigin] = field(default_factory=dict); dependencies: list[str] = field(default_factory=list); settings: dict[str, Any] = field(default_factory=dict); backend: dict[str, Any] = field(default_factory=dict); backend_type: str = ""; workspace: str | None = None; fetch: FetchStatus = "local"`
- Produces (`config.py`):
  - `@dataclass(frozen=True) class TerraformRootSpec: root: str; var_files: tuple[str, ...] = (); engine: Engine | None = None`
  - `@dataclass(frozen=True) class AtmosRootSpec: root: str; stacks: tuple[str, ...] = ()`
  - `@dataclass(frozen=True) class PlanSpec: path: str; stack: str | None = None; component: str | None = None; root: str | None = None`
  - `@dataclass(frozen=True) class IacConfig: terraform_globs: tuple[str, ...]; terraform_roots: tuple[TerraformRootSpec, ...]; atmos: tuple[AtmosRootSpec, ...]; fetch: bool; plans: tuple[PlanSpec, ...]; require_tools: bool`
  - `def load_iac_config(run_dir: Path) -> IacConfig | None` (None unless `infrastructure.mode == "static"`; raises `ValueError` on a schema-invalid run-config)
  - `def resolve_input_path(inputs: Path, rel: str) -> Path` (strips one leading `inputs/` — the 1.7 fixture form `tests/fixtures/valid/run-config-with-infrastructure.yaml` writes globs that way — then joins under `inputs`; raises `ValueError` when the resolved real path leaves `inputs`)
  - `def config_sha256(cfg: IacConfig) -> str`

- [ ] **Step 1: Write the failing tests**

```python
def test_run_config_accepts_iac_block():
    data = yaml.safe_load((FIXTURES / "valid/run-config-with-iac.yaml").read_text())
    assert list(Draft202012Validator(SCHEMA).iter_errors(data)) == []

@pytest.mark.parametrize("name,needle", [("run-config-iac-bad-engine.yaml", "engine"),
                                         ("run-config-iac-traversal.yaml", "root")])
def test_run_config_rejects_bad_iac(name, needle):
    data = yaml.safe_load((FIXTURES / "invalid" / name).read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors and any(needle in "/".join(map(str, e.path)) or needle in e.message for e in errors)

def test_existing_glob_fixture_still_valid():
    data = yaml.safe_load((FIXTURES / "valid/run-config-with-infrastructure.yaml").read_text())
    assert list(Draft202012Validator(SCHEMA).iter_errors(data)) == []
```

`run-config-with-iac.yaml` sets `infrastructure: {mode: static, static: {terraform: ["infra/live/**", {root: infra/live/prod, var_files: [infra/live/prod/prod.tfvars], engine: opentofu}], atmos: [{root: platform, stacks: ["prod-*"]}]}, modules: {fetch: false}, plans: [{path: plans/prod-vpc.json, stack: prod, component: vpc}], require_tools: false}` (spec §6). The bad-engine fixture uses `engine: pulumi`; the traversal fixture uses `atmos: [{root: ../outside}]`.

```python
def test_load_none_when_not_static(tmp_path):
    run = write_run(tmp_path, {"infrastructure": {"mode": "disabled"}})
    assert load_iac_config(run) is None

def test_load_splits_globs_and_objects(tmp_path):
    run = write_run(tmp_path, IAC_BLOCK)   # same block as the valid fixture
    cfg = load_iac_config(run)
    assert cfg.terraform_globs == ("infra/live/**",)
    assert cfg.terraform_roots[0].engine == "opentofu" and cfg.atmos[0].stacks == ("prod-*",)
    assert cfg.fetch is False and cfg.plans[0].component == "vpc"

def test_resolve_input_path_accepts_legacy_prefix(tmp_path):
    (tmp_path / "inputs/terraform").mkdir(parents=True)
    assert resolve_input_path(tmp_path / "inputs", "inputs/terraform") == (tmp_path / "inputs/terraform").resolve()

def test_resolve_input_path_refuses_symlink_escape(tmp_path):
    (tmp_path / "inputs").mkdir(); (tmp_path / "inputs/link").symlink_to(tmp_path.parent)
    with pytest.raises(ValueError, match="outside inputs"):
        resolve_input_path(tmp_path / "inputs", "link")
```

Conftest helpers: `write_run(tmp_path, extra)` writes `runs/r/.apd-run.yaml` with `run_id: r, domains: [pbm], framework_version: 2.0.0` plus `extra`, creates `inputs/`, and returns the run dir; `copy_fixture(tmp_path, name)` copies `tests/fixtures/iac/<name>` to `tmp_path/inputs` and returns it, except that a single-module fixture (one whose top level holds `.tf` or `.tofu` files: `tofu-only`, `tf-and-tofu`, `override` and Plan 2's `suppressed`) lands at `tmp_path/inputs/<name>`, so its root path is `<name>`; `run_with_fixture(tmp_path, name, static, *, fetch=False, require_tools=False, plans=())` builds a run whose `inputs/` is that fixture and whose run-config sets `infrastructure: {mode: static, static: <static>, modules: {fetch: <fetch>}, require_tools: <require_tools>, plans: <plans>}`; `load_index(run)` returns the parsed `iac_evidence_index` mapping; `tree_digest(path)` hashes every file; `grep_tree(path)` concatenates every text file under `path`.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/test_run_config_schema.py tests/iac/test_config.py -v`
Expected: FAIL (the new fixtures fail validation; `apd_gauntlet.iac.config` missing)

- [ ] **Step 3: Implement the schema change, `model.py` and `config.py`**

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/test_run_config_schema.py tests/iac/test_config.py tests/test_cli_validate_run_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas/run-config.schema.json tools/apd_gauntlet/iac tests/fixtures tests/test_run_config_schema.py tests/iac
git commit -m "feat(iac): add run-config infrastructure keys and the IaC config loader"
```

### Task 4: HCL block parser

**Files:**

- Create: `tools/apd_gauntlet/iac/hcl.py`, `tests/fixtures/iac/hcl/main.tf`, `tests/fixtures/iac/hcl/json.tf.json`
- Test: `tests/iac/test_hcl.py`

**Interfaces:**

- Produces:
  - `IAC_SUFFIXES = (".tf", ".tofu", ".tf.json", ".tofu.json")`
  - `BlockKind = Literal["resource", "data", "module", "variable", "locals", "output", "provider", "terraform"]`
  - `@dataclass(frozen=True) class Block: kind: BlockKind; address: str; path: Path; start: int; end: int; body: dict[str, Any]; var_refs: frozenset[str]; refs: frozenset[str]`
  - `class HclParseError(Exception)`
  - `def parse_file(path: Path) -> list[Block]` — HCL via `hcl2.loads(text, with_meta=True)` (python-hcl2 7.x; the 8.x `serialization_options` API dropped line metadata in our probe on 2026-10-11, hence the `<8` pin); `.json` variants via `json.loads`, with each block's lines found by a text search for its label key
  - `def attribute_line(lines: Sequence[str], start: int, end: int, attr: str) -> int | None` — first line in `[start, end]` matching `^\s*<attr>\s*=`
  - `def excerpt_at(lines: Sequence[str], start: int, end: int) -> str` — first non-blank stripped line in the range
  - Addresses: resource `type.name`; data `data.type.name`; module `module.name`; variable `var.name`; output `output.name`; provider `provider.name` (with `.alias` when set); `locals` and `terraform` blocks use the literal kind name. `refs` holds every `type.name`, `data.type.name`, `module.name` and `local.name` reference found inside `${…}` strings of the body; `var_refs` holds the `var.<name>` names.

- [ ] **Step 1: Write the failing tests**

```python
def test_resource_lines_and_refs():
    blocks = {b.address: b for b in parse_file(FIX / "hcl/main.tf")}
    sg = blocks["aws_security_group.ssh"]
    assert (sg.start, sg.end) == (5, 13) and sg.var_refs == frozenset({"allowed_cidr"})
    assert "aws_security_group.ssh" in blocks["aws_instance.relay"].refs
    assert blocks["module.net"].body["source"] == "../modules/net"
    assert blocks["data.aws_ami.base"].kind == "data"

def test_attribute_line():
    lines = (FIX / "hcl/main.tf").read_text().splitlines()
    assert attribute_line(lines, 5, 13, "cidr_blocks") == 10

def test_json_syntax():
    assert "aws_s3_bucket.logs" in {b.address for b in parse_file(FIX / "hcl/json.tf.json")}

def test_parse_error(tmp_path):
    (tmp_path / "bad.tf").write_text('resource "x" {')
    with pytest.raises(HclParseError, match="bad.tf"):
        parse_file(tmp_path / "bad.tf")
```

`hcl/main.tf`: `variable "allowed_cidr" {}` (lines 1–1), blank, `data "aws_ami" "base" {}` (line 3), blank, the `aws_security_group.ssh` block of `tofu-probe/insecure.hcl` with `cidr_blocks = [var.allowed_cidr]` occupying lines 5–13 with `cidr_blocks` on line 10, then `resource "aws_instance" "relay" { vpc_security_group_ids = [aws_security_group.ssh.id] }` and `module "net" { source = "../modules/net" }`.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_hcl.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Implement `hcl.py`**

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_hcl.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/hcl.py tests/fixtures/iac/hcl tests/iac/test_hcl.py
git commit -m "feat(iac): parse HCL and JSON blocks with line ranges"
```

### Task 5: Root discovery and engine selection

**Files:**

- Create: `tools/apd_gauntlet/iac/discover.py`, `tools/apd_gauntlet/iac/engine.py`, `tests/fixtures/iac/plain/` (see below), `tests/fixtures/iac/tofu-only/main.tofu`, `tests/fixtures/iac/tf-and-tofu/{main.tf,main.tofu}`, `tests/fixtures/iac/override/{main.tf,main_override.tf}`
- Test: `tests/iac/test_discover.py`, `tests/iac/test_engine.py`

**Interfaces:**

- Consumes: `IacConfig`, `resolve_input_path` (Task 3), `parse_file` (Task 4), `Unknown`, `Engine` (Task 3)
- Produces:
  - `discover.py`: `@dataclass(frozen=True) class Root: id: str; kind: Literal["atmos", "plain"]; path: str; engine: Engine | None; var_files: tuple[str, ...] = (); stacks: tuple[str, ...] = ()` — `id` is `atmos:<path>` or `plain:<path>` (spec §8.1); `def discover_roots(inputs: Path, cfg: IacConfig) -> tuple[list[Root], list[Unknown]]`
  - `engine.py`: `@dataclass(frozen=True) class EngineChoice: engine: Engine; source: Literal["run-config", "atmos-command", "tofu-files", "default"]; nonstandard_command: str | None`; `def select_engine(module_dir: Path, *, configured: Engine | None, atmos_command: str | None, local_module_dirs: Sequence[Path] = ()) -> EngineChoice`; `def apply_precedence(names: Sequence[str], engine: Engine) -> tuple[list[str], list[str]]` (kept, excluded); `def is_override_file(name: str) -> bool`; `NOT_ANALYSED_SUFFIXES = (".tfstack.hcl", ".tfdeploy.hcl", ".tfquery.hcl")`; `IGNORED_SUFFIXES = (".tftest.hcl", ".tofutest.hcl")`

Rules:

- A glob is expanded under `inputs`; a matched file contributes its parent directory, a matched directory is walked. An **Atmos root** is a directory holding `atmos.yaml`. A **plain root** is a directory holding a file with an `IAC_SUFFIXES` suffix that no other candidate uses as a local (`./` or `../`) module source. Object-form entries are roots by declaration. Directories named `.terraform` and anything under an Atmos root's `components/` tree are never plain roots.
- Engine order (spec §7.2): the run-config `engine`; then the basename of the Atmos `components.terraform.command` (`tofu` → opentofu, `terraform` → terraform, anything else sets `nonstandard_command` and falls through); then any `.tofu` or `.tofu.json` file in the module or its local modules → opentofu; otherwise terraform.
- Precedence: opentofu keeps `X.tofu` over `X.tf` and `X.tofu.json` over `X.tf.json`; terraform excludes every `.tofu` and `.tofu.json` file. Override files are `override.tf`, `*_override.tf`, `override.tofu`, `*_override.tofu` and their `.json` forms.

`tests/fixtures/iac/plain/`: `infra/live/prod/main.tf` (calls `module "sg" { source = "../../modules/sg" }`), `infra/live/prod/prod.tfvars`, `infra/live/prod/terraform.tfvars`, `infra/live/prod/deploy.tfstack.hcl`, `infra/live/prod/main.tftest.hcl`, `infra/modules/sg/main.tf` (the `insecure.hcl` group with `cidr_blocks = [var.cidr]`). The three probe fixtures copy `tofu-probe/{only_tofu,both,override}` from spec §4 verbatim.

- [ ] **Step 1: Write the failing tests**

```python
def test_plain_root_excludes_local_module(tmp_path):
    inputs = copy_fixture(tmp_path, "plain")
    roots, unknowns = discover_roots(inputs, iac_cfg(terraform_globs=("infra/**",)))
    assert [r.id for r in roots] == ["plain:infra/live/prod"] and unknowns == []

def test_atmos_root_by_declaration(tmp_path):
    inputs = copy_fixture(tmp_path, "atmos-basic")
    roots, _ = discover_roots(inputs, iac_cfg(atmos=(AtmosRootSpec("platform"),)))
    assert roots[0].id == "atmos:platform" and roots[0].kind == "atmos"

def test_file_glob_selects_parent_dir(tmp_path):
    inputs = copy_fixture(tmp_path, "plain")
    roots, _ = discover_roots(inputs, iac_cfg(terraform_globs=("infra/live/prod/*.tf",)))
    assert [r.path for r in roots] == ["infra/live/prod"]

@pytest.mark.parametrize("names,engine,kept,excluded", [
    (["main.tf", "main.tofu", "vars.tf"], "opentofu", ["main.tofu", "vars.tf"], ["main.tf"]),
    (["a.tf.json", "a.tofu.json"], "opentofu", ["a.tofu.json"], ["a.tf.json"]),
    (["main.tf", "main.tofu"], "terraform", ["main.tf"], ["main.tofu"]),
])
def test_tofu_precedence(names, engine, kept, excluded):
    assert apply_precedence(names, engine) == (kept, excluded)

def test_engine_order(tmp_path):
    (tmp_path / "x.tofu").write_text("")
    assert select_engine(tmp_path, configured="terraform", atmos_command=None).source == "run-config"
    assert select_engine(tmp_path, configured=None, atmos_command="/usr/bin/tofu").engine == "opentofu"
    wrap = select_engine(tmp_path, configured=None, atmos_command="./bin/tf.sh")
    assert wrap.nonstandard_command == "./bin/tf.sh" and wrap.source == "tofu-files"
    assert select_engine(tmp_path / "empty", configured=None, atmos_command=None).engine == "terraform"

def test_override_names():
    assert all(is_override_file(n) for n in ["override.tf", "main_override.tf", "x_override.tofu.json"])
    assert not is_override_file("overrides.tf")
```

`iac_cfg(**kw)` (a `tests/iac/conftest.py` helper) builds an `IacConfig` with empty defaults.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_discover.py tests/iac/test_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `discover.py` and `engine.py`**

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_discover.py tests/iac/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/discover.py tools/apd_gauntlet/iac/engine.py tests/fixtures/iac tests/iac
git commit -m "feat(iac): discover roots and select the engine per root"
```

### Task 6: Atmos sanitiser

**Files:**

- Create: `tools/apd_gauntlet/iac/atmos.py` (sanitise half), `tests/fixtures/iac/atmos-basic/` (see below)
- Test: `tests/iac/test_atmos_sanitize.py`

**Interfaces:**

- Consumes: `Unknown` (Task 3), `Root` (Task 5)
- Produces:
  - `@dataclass class SanitizeResult: copy_root: Path; atmos_config: dict[str, Any]; unknowns: list[Unknown]; excluded_files: list[str]; refused: str | None`
  - `def sanitize_root(root: Root, *, inputs: Path, dst: Path) -> SanitizeResult`
  - `def load_yaml_tolerant(text: str) -> Any` — PyYAML `SafeLoader` subclass whose multi-constructor for `!` returns the tagged scalar as the string `"!<tag> <value>"`
  - `SENTINEL_COMMAND = "/nonexistent/apd-gauntlet-no-exec"`

Rewrite rules, each a single-line substitution so provenance line numbers still match the originals (spec §7.3):

| Input line pattern | Rewrite | Recorded `unknown` reason |
|---|---|---|
| `!include` or `!include.raw` whose target is a URL (`://`), a go-getter source (`git::`, `s3::`, `gcs::`, `github.com/`), an absolute path, or a path whose real path leaves the Atmos root | `"!include <target>"` (quoted literal) | `remote_include` or `outside_include` |
| An `import:` list item naming a URL or go-getter source | the item line becomes a YAML comment `# apd: removed remote import <target>` | `remote_import` |
| A Go template action `{{ … }}` containing `atmos.` (`atmos.Component`, `atmos.Store`, `atmos.GomplateDatasource`, any other) | the whole scalar becomes a quoted literal with `{{`/`}}` replaced by `{ {`/`} }` | `template_unresolved` |
| `components.terraform.command`, `components.helmfile.command`, `components.packer.command` in the copied `atmos.yaml`, and any component-level `command:` key in a stack manifest | the value becomes `SENTINEL_COMMAND` | none (the original value is kept in `atmos_config` for engine selection and Task 10's execution points) |
| `templates.settings.gomplate.datasources` and `templates.settings.sprig` in the copied `atmos.yaml` | removed; `templates.settings.gomplate.enabled: false` written | `gomplate_datasource` |

A file whose rewrite cannot stay on one line (a block-scalar include, a multi-line template action) is excluded from the copy and recorded `multiline_rewrite`; its stacks later fail to resolve and are recorded as unresolved. A symlink whose real path leaves the root is not copied (`escaping_symlink`). A root whose `base_path`, `components.terraform.base_path`, `stacks.base_path` or `workflows.base_path` is absolute or resolves outside the root is refused (`refused` set, one `root_refused` unknown, nothing copied).

The `atmos.Component` row is not in the spec: a probe on 2026-10-11 showed that with `--process-functions=false` a template `{{ (atmos.Component "peer" .stack).outputs.vpc_id }}` still ran the configured `components.terraform.command` (a script inside the repository, given by absolute path) during `atmos describe component`. Both the template rewrite and the command sentinel close that path. The coordinator accepted this trade-off on 2026-10-11: values from `atmos.*` calls become `unknown`, and every other template keeps rendering.

`tests/fixtures/iac/atmos-basic/platform/` (spec §4 probes):

- `atmos.yaml`: `base_path: "."`, `components.terraform.base_path: "components/terraform"`, `components.terraform.command: "tofu"`, `stacks.base_path: "stacks"`, `included_paths: ["orgs/**/*"]`, `excluded_paths: ["catalog/**/*"]`, `name_pattern: "{stage}"`, `templates.settings.enabled: true`.
- `stacks/catalog/vpc.yaml`: abstract `vpc/defaults` with `enable_flow_logs: true`, `map_public_ip_on_launch: false`.
- `stacks/catalog/net.json`: `{"cidr": "10.0.0.0/16"}`.
- `stacks/orgs/prod.yaml` (exactly these 11 lines; `map_public_ip_on_launch` is on line 8, as in the spec §4 probe):

  ```yaml
  import: [catalog/vpc]
  vars: { stage: prod }
  components:
    terraform:
      vpc:
        metadata: { component: vpc, inherits: [vpc/defaults] }
        vars:
          map_public_ip_on_launch: true
          net: !include stacks/catalog/net.json
          peer_vpc_id: !terraform.output peer vpc_id
          build_id: !exec "touch EXEC_RAN && echo built"
  ```

- `stacks/orgs/dev.yaml`: `stage: dev`; `vpc` inheriting `vpc/defaults` with `name: '{{ .vars.stage | nosuchfunc }}'`.
- `components/terraform/vpc/main.tf`: variables `enable_flow_logs`, `map_public_ip_on_launch`, `net`, `peer_vpc_id`, `build_id`, `name`; `resource "aws_subnet" "public_a"` using `map_public_ip_on_launch = var.map_public_ip_on_launch`; the `aws_security_group.ssh` block from `tofu-probe/insecure.hcl`.

- [ ] **Step 1: Write the failing tests**

```python
def test_local_include_kept_and_lines_preserved(tmp_path):
    res = sanitize_basic(tmp_path)
    src = (FIX / "atmos-basic/platform/stacks/orgs/prod.yaml").read_text().splitlines()
    out = (res.copy_root / "stacks/orgs/prod.yaml").read_text().splitlines()
    assert len(out) == len(src) and "!include stacks/catalog/net.json" in out[8]

def test_outside_and_remote_includes_rewritten(tmp_path):
    outside = tmp_path / "outside.txt"; outside.write_text("OUTSIDE-CANARY")
    inputs = copy_fixture(tmp_path, "atmos-basic")
    append(inputs / "platform/stacks/orgs/prod.yaml", [
        f"        host: !include /etc/hostname", f"        secret: !include {outside}",
        "        up: !include ../../../../escape.yaml", "        remote: !include https://example.invalid/x.yaml"])
    res = sanitize_root(ATMOS_ROOT, inputs=inputs, dst=tmp_path / "copy")
    text = (res.copy_root / "stacks/orgs/prod.yaml").read_text()
    assert '"!include /etc/hostname"' in text and f'"!include {outside}"' in text
    assert '"!include https://example.invalid/x.yaml"' in text
    assert sorted(u.reason for u in res.unknowns) == ["outside_include", "outside_include", "outside_include", "remote_include"]

def test_remote_import_removed(tmp_path): ...       # "import: [catalog/vpc, 'git::https://x//stacks?ref=v1']" → comment line, unknown remote_import

def test_template_atmos_calls_rewritten(tmp_path):
    inputs = copy_fixture(tmp_path, "atmos-basic")
    append(inputs / "platform/stacks/orgs/prod.yaml",
           ["        out: '{{ (atmos.Component \"peer\" .stack).outputs.vpc_id }}'"])
    res = sanitize_root(ATMOS_ROOT, inputs=inputs, dst=tmp_path / "copy")
    assert "atmos.Component" in (res.copy_root / "stacks/orgs/prod.yaml").read_text()
    assert "{{" not in (res.copy_root / "stacks/orgs/prod.yaml").read_text().splitlines()[-1]
    assert any(u.reason == "template_unresolved" for u in res.unknowns)

def test_command_neutralised_and_original_kept(tmp_path):
    res = sanitize_basic(tmp_path)
    copied = yaml.safe_load((res.copy_root / "atmos.yaml").read_text())
    assert copied["components"]["terraform"]["command"] == SENTINEL_COMMAND
    assert res.atmos_config["components"]["terraform"]["command"] == "tofu"

def test_datasources_stripped(tmp_path): ...       # gomplate.datasources present → absent in copy, enabled false, unknown gomplate_datasource
def test_escaping_symlink_not_copied(tmp_path): ...  # stacks/orgs/evil.yaml → /etc/passwd: absent in copy, unknown escaping_symlink
def test_escaping_base_path_refuses_root(tmp_path):
    inputs = copy_fixture(tmp_path, "atmos-basic")
    replace(inputs / "platform/atmos.yaml", 'base_path: "."', 'base_path: "../.."')
    res = sanitize_root(ATMOS_ROOT, inputs=inputs, dst=tmp_path / "copy")
    assert res.refused and [u.reason for u in res.unknowns] == ["root_refused"]

def test_multiline_include_excludes_file(tmp_path): ...  # "x: !include |\n  https://…" → file in excluded_files, unknown multiline_rewrite
```

`ATMOS_ROOT = Root("atmos:platform", "atmos", "platform", None)`; `sanitize_basic` copies the fixture and calls `sanitize_root`; `append` and `replace` edit fixture copies in place.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_atmos_sanitize.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `sanitize_root`**

Walk the root with `os.walk(followlinks=False)`; copy regular files byte for byte; rewrite `*.yaml`, `*.yml` and `*.yaml.tmpl` line by line with these patterns:

```python
INCLUDE_RE = re.compile(r"""(?P<pre>:\s*|-\s+)!include(?P<raw>\.raw)?\s+(?P<target>[^\s#'"]+)(?P<rest>.*)$""")
TEMPLATE_RE = re.compile(r"\{\{.*?\}\}")
REMOTE_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|git::|s3::|gcs::|github\.com/|bitbucket\.org/)")
```

A local include target resolves first against the manifest's directory, then against the Atmos root; it is kept only when the resolved real path exists inside the root.

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_atmos_sanitize.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/atmos.py tests/fixtures/iac/atmos-basic tests/iac/test_atmos_sanitize.py
git commit -m "feat(iac): sanitise Atmos roots on a scratch copy"
```

### Task 7: Atmos resolution and provenance

**Files:**

- Modify: `tools/apd_gauntlet/iac/atmos.py` (resolve half)
- Test: `tests/iac/test_atmos_resolve.py`, `tests/iac/test_atmos_resolve_live.py` (`iac_tools`)

**Interfaces:**

- Consumes: `SanitizeResult` (Task 6), `ToolRunner` (Task 1), `Instance`, `VarOrigin`, `Unknown`, `ExecutionPoint` (Task 3), `Root` (Task 5), `select_engine` (Task 5)
- Produces:
  - `def list_stack_manifests(copy_root: Path, atmos_config: dict[str, Any]) -> list[str]` — manifest names relative to `stacks.base_path`, without extension, from `included_paths` minus `excluded_paths` (`**` globs), sorted
  - `@dataclass class StackResolution: manifest: str; stack: str | None; components: dict[str, dict[str, Any]]; templates: bool; error: str | None`
  - `def resolve_manifest(copy_root: Path, manifest: str, *, runner: ToolRunner, timeout_s: int) -> StackResolution` — `atmos describe stacks -s <manifest> --format json --process-functions=false`, retried once with `--process-templates=false` on a nonzero exit; both failing → `error` holds the last 2,000 characters of stderr
  - `FUNCTION_LITERAL_RE = re.compile(r"^!(?P<fn>[a-z][a-z0-9._-]*)(?:\s|$)")`; `TEMPLATE_REMNANT_RE = re.compile(r"\{\{|\{ \{|<no value>")`
  - `def unknown_paths(value: Any, prefix: str) -> list[tuple[str, str]]` — `(path, literal)` for every string matching either pattern, depth first
  - `def instances_from_stack(res: StackResolution, root: Root, sanitize: SanitizeResult, *, inputs: Path, stack_globs: Sequence[str]) -> tuple[list[Instance], list[Unknown], list[ExecutionPoint]]`
  - `def parse_provenance(text: str) -> dict[str, tuple[str, int | None]]` — key path (`vars.map_public_ip_on_launch`) → (manifest file relative to `stacks.base_path`, line)
  - `def fetch_provenance(copy_root: Path, component: str, stack: str, *, runner: ToolRunner, timeout_s: int) -> dict[str, tuple[str, int | None]]`
  - `def locate_var_definition(copy_root: Path, stacks_base: str, component: str, var: str) -> tuple[str, int] | None` — the first manifest line `<var>:` nested under a `<component>:` key line, as a path relative to `stacks_base`
  - `def attach_provenance(instances: Sequence[Instance], copy_root: Path, root: Root, *, runner: ToolRunner, timeout_s: int) -> list[Unknown]` — fills each `Instance.provenance` (keyed by variable name, files made `inputs`-relative) from `fetch_provenance`, with at most `IAC_MAX_CONCURRENCY` calls in flight; a failed call yields a `tool_failed` unknown for that instance and leaves its provenance empty
  - `IAC_MAX_CONCURRENCY = 4`

`instances_from_stack` keeps components whose `metadata.type` is not `abstract` and whose stack name matches a `stack_globs` entry (`fnmatch`; empty means all). Each instance gets `id = "<stack>/<component>"`, `module_path` = Atmos root path joined with the component's `component_info.component_path`, `vars` minus unknown top-level keys, `unknown_vars` sorted, `inherited` from each component in `metadata.inherits` (values from the same stack output, locations from `locate_var_definition`), `settings`, `backend`, `backend_type`. Each literal yields an `Unknown(reason="function_literal" | "template_unresolved", key=<var path>)` citing the line `locate_var_definition` finds for the component, then for each component in `metadata.inherits`, else line 1 of the manifest (all `inputs`-relative); `!terraform.output` and `!terraform.state` add `"<stack>/<target component>"` to `dependencies`; `!exec` also yields `ExecutionPoint("atmos_exec")`. A component directory missing under `inputs` yields `component_not_committed`. A failed manifest yields one `stack_unresolved` unknown citing line 1 with Atmos's stderr as `detail`.

Provenance comment format (Atmos 1.231.0, verified on the probe fixture): `vars:` subtree lines end in `# ● [1] orgs/prod.yaml:8`, `# ○ [2] catalog/vpc.yaml:6` or `# ∴ …`, and a line may omit `:<line>`.

- [ ] **Step 1: Write the failing tests**

```python
PROD_JSON = {"prod": {"components": {"terraform": {
    "vpc": {"metadata": {"component": "vpc", "inherits": ["vpc/defaults"]},
            "component_info": {"component_path": "components/terraform/vpc"},
            "vars": {"map_public_ip_on_launch": True, "enable_flow_logs": True, "stage": "prod",
                     "net": {"cidr": "10.0.0.0/16"}, "peer_vpc_id": "!terraform.output peer vpc_id",
                     "build_id": "!exec touch EXEC_RAN && echo built"},
            "settings": {}, "backend": {}, "backend_type": "", "command": SENTINEL_COMMAND},
    "vpc/defaults": {"metadata": {"component": "vpc", "type": "abstract"},
                     "component_info": {"component_path": "components/terraform/vpc"},
                     "vars": {"map_public_ip_on_launch": False, "enable_flow_logs": True}}}}}}
PROV = ("vars:  # ● [1] orgs/prod.yaml:7\n"
        "  enable_flow_logs: true  # ○ [2] catalog/vpc.yaml:6\n"
        "  map_public_ip_on_launch: true  # ● [1] orgs/prod.yaml:8\n"
        "  net:  # ● [1] orgs/prod.yaml:9\n    cidr: 10.0.0.0/16  # ● [1] orgs/prod.yaml\n")

def test_parse_provenance():
    p = parse_provenance(PROV)
    assert p["vars.map_public_ip_on_launch"] == ("orgs/prod.yaml", 8)
    assert p["vars.enable_flow_logs"] == ("catalog/vpc.yaml", 6) and p["vars.net.cidr"] == ("orgs/prod.yaml", None)

def test_manifests_listed(tmp_path):
    res = sanitize_basic(tmp_path)
    assert list_stack_manifests(res.copy_root, res.atmos_config) == ["orgs/dev", "orgs/prod"]

def test_retry_without_templates(tmp_path, fake_runner):
    res = sanitize_basic(tmp_path)
    fake_runner.on("atmos", ["describe", "stacks", "-s", "orgs/dev", "--format", "json", "--process-functions=false"],
                   returncode=1, stderr='function "nosuchfunc" not defined')
    fake_runner.on("atmos", ["describe", "stacks", "-s", "orgs/dev", "--format", "json", "--process-functions=false",
                   "--process-templates=false"], stdout=json.dumps(DEV_JSON))
    sr = resolve_manifest(res.copy_root, "orgs/dev", runner=fake_runner, timeout_s=60)
    assert sr.templates is False and sr.error is None and sr.stack == "dev"

def test_both_attempts_fail_records_unresolved(tmp_path, fake_runner): ...   # two nonzero exits → error set; instances_from_stack → one stack_unresolved unknown

def test_instances_unknowns_and_execution_points(tmp_path):
    res = sanitize_basic(tmp_path)
    sr = StackResolution("orgs/prod", "prod", PROD_JSON["prod"]["components"]["terraform"], True, None)
    insts, unknowns, eps = instances_from_stack(sr, ATMOS_ROOT, res, inputs=tmp_path / "inputs", stack_globs=())
    assert [i.id for i in insts] == ["prod/vpc"]
    vpc = insts[0]
    assert vpc.module_path == "platform/components/terraform/vpc"
    assert vpc.unknown_vars == ["build_id", "peer_vpc_id"] and "build_id" not in vpc.vars
    assert vpc.dependencies == ["prod/peer"] and vpc.inherited["map_public_ip_on_launch"].value is False
    assert vpc.inherited["map_public_ip_on_launch"].file.endswith("catalog/vpc.yaml")
    assert {u.key for u in unknowns} == {"vars.build_id", "vars.peer_vpc_id"}
    assert [e.kind for e in eps] == ["atmos_exec"]

def test_stack_globs_filter(tmp_path): ...       # stack_globs=("dev*",) → no prod instances
def test_no_value_is_unknown(): assert unknown_paths({"name": "<no value>"}, "vars") == [("vars.name", "<no value>")]
```

`DEV_JSON` mirrors `PROD_JSON` for `dev` with `name: "{{ .vars.stage | nosuchfunc }}"`.

```python
@pytest.mark.iac_tools
def test_live_resolution_matches_probe(tmp_path, require_tools):
    require_tools("atmos")
    res = sanitize_basic(tmp_path)
    sr = resolve_manifest(res.copy_root, "orgs/prod", runner=run_tool, timeout_s=120)
    assert sr.components["vpc"]["vars"]["map_public_ip_on_launch"] is True
    prov = fetch_provenance(res.copy_root, "vpc", "prod", runner=run_tool, timeout_s=120)
    assert prov["vars.map_public_ip_on_launch"] == ("orgs/prod.yaml", 8)
    assert prov["vars.enable_flow_logs"] == ("catalog/vpc.yaml", 6)
```

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_atmos_resolve.py tests/iac/test_atmos_resolve_live.py -v`
Expected: FAIL (functions missing; live test fails or skips without Atmos)

- [ ] **Step 3: Implement the resolve half of `atmos.py`**

`resolve_manifest` passes `cwd=copy_root`. `parse_provenance` tracks the YAML key path by indentation and reads the trailing comment with `re.compile(r"#\s+[●○∴]\s+\[\d+\]\s+(?P<file>\S+?)(?::(?P<line>\d+))?\s*$")`.

- [ ] **Step 4: Run to verify pass**

Run: `PATH=/tmp/claude-0/-home-claude-apd-gauntlet/62f4ef46-a9fa-56b6-909b-632a30f9b40f/scratchpad/bin:$PATH /home/claude/venv-apd/bin/pytest tests/iac/test_atmos_resolve.py tests/iac/test_atmos_resolve_live.py -v`
Expected: PASS (the live test runs where Atmos 1.231.0 is on PATH and skips elsewhere)

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/atmos.py tests/iac
git commit -m "feat(iac): resolve Atmos stacks with functions off and parse provenance"
```

### Task 8: Fetch consent

**Files:**

- Create: `tools/apd_gauntlet/iac/consent.py`
- Test: `tests/iac/test_consent.py`

**Interfaces:**

- Produces:
  - `CONSENT_SUBJECT = "iac_module_fetch"`
  - `ConsentMethod = Literal["flag", "prompt", "tui", "web"]`
  - `def sources_sha256(sources: Sequence[str]) -> str` — SHA-256 of the sorted unique sources joined with `"\n"`
  - `def has_fetch_consent(run_dir: Path, sources: Sequence[str]) -> bool` (R6)
  - `def record_fetch_consent(run_dir: Path, sources: Sequence[str], method: ConsentMethod) -> None` (R6) — writes `consent.json["iac_module_fetch"] = {"sources": sorted unique, "sources_sha256", "granted_at": UTC ISO-8601 with Z, "method"}` by read-modify-write with an atomic rename, preserving every other subject

- [ ] **Step 1: Write the failing tests**

```python
SRC = ["git::https://example.com/net.git?ref=v1.2.0", "terraform-aws-modules/vpc/aws@5.1.0"]

def test_no_file_no_consent(tmp_path): assert not has_fetch_consent(tmp_path, SRC)

def test_decision_consent_does_not_grant_fetch(tmp_path):
    write_consent(tmp_path, {"decision_model": {"provider": "cloudflare", "model": "clef",
                                                "granted_at": "2026-10-10T00:00:00Z", "method": "flag"}})
    assert not has_fetch_consent(tmp_path, SRC)

def test_record_preserves_other_subject(tmp_path):
    write_consent(tmp_path, {"decision_model": {"provider": "cloudflare"}})
    record_fetch_consent(tmp_path, SRC, "flag")
    doc = read_consent(tmp_path)
    assert doc["decision_model"] == {"provider": "cloudflare"}
    assert doc["iac_module_fetch"]["sources_sha256"] == sources_sha256(SRC)
    assert has_fetch_consent(tmp_path, list(reversed(SRC)))

def test_changed_sources_invalidate_consent(tmp_path):
    record_fetch_consent(tmp_path, SRC, "prompt")
    assert not has_fetch_consent(tmp_path, SRC + ["git::https://example.com/new.git?ref=v1"])
```

`write_consent`/`read_consent` read and write `<dir>/.apd-state/consent.json`.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_consent.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `consent.py`**

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_consent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/consent.py tests/iac/test_consent.py
git commit -m "feat(iac): record module-fetch consent under its own subject"
```

### Task 9: Workspaces and consented module fetch

**Files:**

- Create: `tools/apd_gauntlet/iac/workspace.py`, `tools/apd_gauntlet/iac/fetch.py`
- Test: `tests/iac/test_workspace.py`, `tests/iac/test_fetch.py`, `tests/iac/test_fetch_live.py` (`iac_tools`)

**Interfaces:**

- Consumes: `Instance`, `Override`, `Unknown`, `Engine`, `FetchStatus` (Task 3), `parse_file`, `Block`, `IAC_SUFFIXES` (Task 4), `apply_precedence`, `is_override_file`, `NOT_ANALYSED_SUFFIXES`, `IGNORED_SUFFIXES` (Task 5), `ToolRunner` (Task 1)
- Produces:
  - `workspace.py`:
    - `SCANNER_CONFIG_FILES = frozenset({".trivyignore", ".trivyignore.yaml", "trivy.yaml", "trivy.yml", ".checkov.yaml", ".checkov.yml", ".shellcheckrc"})` — never copied at any depth: Checkov 3.3.26 reads `.checkov.yaml` from the `-d` target as well as from its working directory and `HOME`, and a `skip-check` there drops checks without a trace (verified 2026-10-11). Plan 2 Task 3 reads these files from `inputs/` and records what they would have suppressed.
    - `VARS_FILENAME = "apd.auto.tfvars.json"`
    - `@dataclass class Workspace: id: str; target: Path; tree: Path; engine: Engine; file_map: dict[str, str]; overrides: list[Override]; not_analysed: list[str]; var_files: list[Path]; unknown_vars: list[str]; blocks: list[Block]; block_vars: dict[str, frozenset[str]]; content_sha256: str; vars_sha256: str; instances: list[str]` — `file_map` maps a workspace path relative to `tree` to its original path relative to `inputs` (so a kept `main.tofu` maps from `…/main.tf`); `blocks` excludes override files
    - `def local_module_dirs(module_dir: Path, inputs: Path) -> tuple[list[Path], list[Unknown]]` — transitive `./` and `../` sources; an escaping source → `escaping_module_source`
    - `def build_workspace(instance: Instance, *, inputs: Path, ws_root: Path, var_files: Sequence[str] = ()) -> tuple[Workspace, list[Unknown]]`
    - `def dedupe_key(ws: Workspace) -> tuple[str, str, str]` → `(content_sha256, vars_sha256, engine)`
    - `def original_path(ws: Workspace, scanner_path: str) -> str | None` — maps a path a scanner reports (absolute, relative to `target`, with a leading `/`, or Trivy's `<source>/<dir>/…` module form) back to an `inputs`-relative original
  - `fetch.py`:
    - `@dataclass(frozen=True) class ModuleSource: workspace: str; module: str; source: str; version: str | None; file_path: str; line: int; remote: bool`
    - `def list_module_sources(ws: Workspace, known_vars: Mapping[str, Any]) -> tuple[list[ModuleSource], list[Unknown]]` — remote means not `./`/`../`; a source containing `var.` is resolved from `known_vars` only when the engine is opentofu (`early_eval_unresolved` otherwise)
    - `def needs_credentials(source: str) -> bool` — `git@`, `ssh://`, `git::ssh://`, `s3::`, `gcs::`, or a registry host other than `registry.terraform.io` and `registry.opentofu.org`
    - `def fetch_modules(ws: Workspace, sources: Sequence[ModuleSource], *, runner: ToolRunner, timeout_s: int) -> tuple[FetchStatus, list[Unknown]]`

Workspace layout: `tree = ws_root / "ws-<sha8>"`, `target = tree / <module_path>`; each local module directory is mirrored at its own `inputs`-relative path under `tree`. Per directory: copy the files `apply_precedence` keeps, written with `.tf`/`.tf.json` names; copy subdirectories that hold no `IAC_SUFFIXES` file (templates, policies) recursively; never copy `.terraform/`, `.git/` or `SCANNER_CONFIG_FILES`. Copies are byte-identical, so inline suppression comments (`#trivy:ignore:…`, `#checkov:skip=…`) stay in the workspace; Plan 2 Task 3 scans a separate neutralised copy. Override files are copied, and each block they define becomes an `Override` naming the non-override file that defines the same address (`overrides_file`). Each kept file is parsed with `parse_file`; an `HclParseError` yields a `parse_error` unknown citing the file's line 1, and the file is still copied so scanners see it. Variables: an Atmos instance writes `instance.vars` to `target / VARS_FILENAME`; a plain root copies its declared `var_files` plus `terraform.tfvars` and `*.auto.tfvars(.json)` and lists them in `var_files`. `unknown_vars` = the instance's unknowns plus variables declared without a default and absent from every var file. `not_analysed` lists `NOT_ANALYSED_SUFFIXES` files and the files `apply_precedence` excluded; `IGNORED_SUFFIXES` files are skipped silently. The workspace id is `"ws-" + sha256(content_sha256 + vars_sha256 + engine)[:8]`.

`fetch_modules` runs `runner("tofu", ["get"], cwd=ws.target, network=True, timeout_s=…)` only for workspaces with at least one remote source that does not need credentials; credential sources become `credentials_required` unknowns without a call. Exit 0 → `fetched` (or `partial` when some sources were skipped), else `module_fetch_failed` with stderr and `not_fetched`.

- [ ] **Step 1: Verify the OpenTofu assumptions**

With OpenTofu ≥ 1.8.0 on PATH, in a scratch copy of `tests/fixtures/iac/plain` with a registry module added: run `tofu get`, confirm `.terraform/modules/modules.json` is written and that `TF_INPUT=0` suppresses prompts; add `variable "ver" {}` with `source = "./mods/${var.ver}"`, write `apd.auto.tfvars.json`, and confirm `tofu get` reads it for the early-evaluated source. Expected: record each result in `fetch.py`'s module docstring. If `tofu get` ignores the file, `list_module_sources` records every `var.`-dependent source as `early_eval_unresolved` regardless of engine (spec §7.5 step 3) and the test `test_early_eval_resolved_for_opentofu` asserts that instead.

- [ ] **Step 2: Write the failing tests**

```python
def test_tofu_precedence_and_rename(tmp_path):
    ws, _ = build_workspace(inst("plain:tf-and-tofu", "tf-and-tofu", "opentofu"),
                            inputs=copy_fixture(tmp_path, "tf-and-tofu"), ws_root=tmp_path / "ws")
    assert sorted(p.name for p in ws.target.iterdir()) == ["main.tf"]
    assert (ws.target / "main.tf").read_text() == (FIX / "tf-and-tofu/main.tofu").read_text()
    assert ws.file_map["tf-and-tofu/main.tf"] == "tf-and-tofu/main.tofu"
    assert ws.not_analysed == ["tf-and-tofu/main.tf"]

def test_tofu_only_dir_renamed(tmp_path):
    ws, _ = build_workspace(inst("plain:tofu-only", "tofu-only", "opentofu"),
                            inputs=copy_fixture(tmp_path, "tofu-only"), ws_root=tmp_path / "ws")
    assert [p.name for p in ws.target.iterdir()] == ["main.tf"]

def test_override_blocks_recorded(tmp_path):
    ws, _ = build_workspace(inst("plain:override", "override", "terraform"),
                            inputs=copy_fixture(tmp_path, "override"), ws_root=tmp_path / "ws")
    assert [(o.address, o.file_path, o.overrides_file) for o in ws.overrides] == [
        ("aws_security_group.ssh", "override/main_override.tf", "override/main.tf")]
    assert (ws.target / "main_override.tf").exists()

def test_local_module_mirrored_and_not_analysed(tmp_path):
    ws, unknowns = build_workspace(inst("plain:infra/live/prod", "infra/live/prod", "terraform"),
                                   inputs=copy_fixture(tmp_path, "plain"), ws_root=tmp_path / "ws",
                                   var_files=["infra/live/prod/prod.tfvars"])
    assert (ws.tree / "infra/modules/sg/main.tf").exists()
    assert "infra/live/prod/deploy.tfstack.hcl" in ws.not_analysed
    assert not any(p.name == "main.tftest.hcl" for p in ws.tree.rglob("*"))
    assert [p.name for p in ws.var_files] == ["prod.tfvars", "terraform.tfvars"] and unknowns == []

def test_scanner_config_never_copied(tmp_path):
    inputs = copy_fixture(tmp_path, "plain"); (inputs / "infra/live/prod/.trivyignore").write_text("AVD-AWS-0107")
    (inputs / "infra/modules/sg/.checkov.yaml").write_text("skip-check:\n  - CKV_AWS_24\n")
    ws, _ = build_workspace(inst("plain:infra/live/prod", "infra/live/prod", "terraform"), inputs=inputs, ws_root=tmp_path / "ws")
    assert not (ws.target / ".trivyignore").exists() and not (ws.tree / "infra/modules/sg/.checkov.yaml").exists()

def test_atmos_vars_file_and_unknown_vars(tmp_path): ...   # Instance with vars {"a": 1}, unknown_vars ["b"] → apd.auto.tfvars.json == {"a": 1}; ws.unknown_vars contains "b"
def test_escaping_module_source(tmp_path): ...             # source = "../../../../etc" → unknown escaping_module_source
def test_dedupe_key_equal_for_same_content(tmp_path): ...  # two instances, same module and vars → equal dedupe_key and id
def test_original_path_forms(tmp_path): ...                # "/main.tf", "main.tf", "<abs target>/main.tf" and "git::https:/x.git?ref=v1/.terraform/modules/m/main.tf" all map back
```

```python
def test_sources_listed_and_classified(tmp_path):
    ws = ws_with(tmp_path, 'module "a" { source = "git::https://example.com/a.git?ref=v1" }\n'
                           'module "b" { source = "git@github.com:org/b.git" }\n'
                           'module "c" { source = "./c" }\n')
    srcs, _ = list_module_sources(ws, {})
    assert [(s.module, s.remote) for s in srcs] == [("a", True), ("b", True), ("c", False)]
    assert needs_credentials("git@github.com:org/b.git") and not needs_credentials(srcs[0].source)

def test_early_eval_resolved_for_opentofu(tmp_path): ...   # source "./mods/${var.ver}", known {"ver": "v1"}, engine opentofu → source "./mods/v1"; terraform → early_eval_unresolved

def test_fetch_calls_tofu_get_with_network(tmp_path, fake_runner):
    ws = ws_with(tmp_path, 'module "a" { source = "git::https://example.com/a.git?ref=v1" }\n')
    fake_runner.on("tofu", ["get"])
    status, unknowns = fetch_modules(ws, list_module_sources(ws, {})[0], runner=fake_runner, timeout_s=60)
    assert status == "fetched" and fake_runner.calls == [("tofu", ["get"], ws.target, True)]

def test_credential_sources_skipped_without_call(tmp_path, fake_runner): ...   # only git@ source → no call, status not_fetched, unknown credentials_required
```

`inst(id, module_path, engine)` builds an `Instance` with `root=id`; `ws_with(tmp_path, text)` writes a one-file module and builds its workspace.

```python
@pytest.mark.iac_tools
def test_scanners_read_fetched_modules_layout(tmp_path, require_tools):
    require_tools("trivy", "checkov")
    ws = hand_fetched_workspace(tmp_path)   # .terraform/modules/modules.json + modules/m/main.tf = insecure SG
    trivy = run_tool("trivy", trivy_config_args(ws.target), cwd=tmp_path, timeout_s=600)
    checkov = run_tool("checkov", checkov_args(ws.target), cwd=tmp_path, timeout_s=900)
    assert "module.m" in trivy.stdout and "module.m.aws_security_group.ssh" in checkov.stdout
```

This test pins spec §7.5's open item, verified on 2026-10-11: Trivy 0.70.0 resolves `.terraform/modules/modules.json` (reporting the target as `<source>/.terraform/modules/m/main.tf` and the caller as `module.m`); Checkov 3.3.26 does so only with `CHECKOV_EXPERIMENTAL_TERRAFORM_MANAGED_MODULES=True` (set by `CHECKOV_ENV`) and `--download-external-modules false`, and attempts a registry download when that flag is `true`.

- [ ] **Step 3: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_workspace.py tests/iac/test_fetch.py tests/iac/test_fetch_live.py -v`
Expected: FAIL

- [ ] **Step 4: Implement `workspace.py` and `fetch.py`**

- [ ] **Step 5: Run to verify pass**

Run: `PATH=/tmp/claude-0/-home-claude-apd-gauntlet/62f4ef46-a9fa-56b6-909b-632a30f9b40f/scratchpad/bin:/tmp/claude-0/-home-claude-apd-gauntlet/62f4ef46-a9fa-56b6-909b-632a30f9b40f/scratchpad/ckv/bin:$PATH /home/claude/venv-apd/bin/pytest tests/iac/test_workspace.py tests/iac/test_fetch.py tests/iac/test_fetch_live.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/iac/workspace.py tools/apd_gauntlet/iac/fetch.py tests/iac
git commit -m "feat(iac): build normalised workspaces and fetch modules with consent"
```

### Task 10: Execution points, index skeleton and summary

**Files:**

- Create: `tools/apd_gauntlet/iac/inventory.py`, `tools/apd_gauntlet/iac/index.py`, `tools/apd_gauntlet/iac/summary.py`, `tools/apd_gauntlet/data/schemas/iac-evidence-index.schema.json`, `tests/fixtures/iac/exec-points/` (`main.tf` with one `provisioner "local-exec"`, one `provisioner "remote-exec"`, one `data "external"`, one `terraform_data` with a provisioner)
- Test: `tests/iac/test_index.py`, `tests/iac/test_inventory.py`, `tests/test_meta_schemas.py` (picks up the new schema automatically)

**Interfaces:**

- Consumes: `Unknown`, `ExecutionPoint`, `Override` (Task 3), `Root` (Task 5), `SanitizeResult` (Task 6), `Workspace` (Task 9)
- Produces:
  - `inventory.py`: `def atmos_execution_points(root: Root, sanitize: SanitizeResult, *, inputs: Path) -> list[ExecutionPoint]` (custom `commands` in `atmos.yaml`; workflow steps with `type: shell` under `workflows.base_path`; component `hooks`; a non-standard `components.terraform.command` from `sanitize.atmos_config`); `def hcl_execution_points(ws: Workspace) -> list[ExecutionPoint]` (`provisioner "local-exec"` and `"remote-exec"`, `data "external"`, `null_resource` or `terraform_data` with a provisioner; one entry per instance in `ws.instances`)
  - `index.py`:
    - `INDEX_FILENAME = "iac-evidence-index.yaml"`; `ENTRY_ID_RE = re.compile(r"^iev-[0-9a-f]{8}$")`
    - `def mint_entry_id(instance: str | None, address: str | None, kind: str, discriminator: str) -> str` → `"iev-" + sha256("|".join([instance or "", address or "", kind, discriminator]).encode()).hexdigest()[:8]`. The discriminator is the check id for `check` and `control` entries (Plan 2), `f"{reason}:{key or file_path}"` for `unknown`, `f"{execution}:{file_path}:{line}"` for `execution_point`, and `f"override:{file_path}"` for `override`.
    - `def trim_excerpt(text: str, max_tokens: int = 25, max_chars: int = 500) -> str`
    - `def canonical_locator(entry: Mapping[str, Any]) -> str` → `f"iac:{instance or '-'}:{address or '-'}@{file_path}:{line_range}#{id}"` (spec §8.3)
    - `class IndexBuilder: def __init__(self, inputs: Path) -> None; def add_unknown(self, u: Unknown) -> str; def add_execution_point(self, e: ExecutionPoint) -> str; def add_override(self, o: Override) -> str; def add_entry(self, entry: dict[str, Any]) -> str; def entries(self) -> list[dict[str, Any]]; def document(self, *, generated_at: str, tools: dict[str, str | None], roots: list[dict[str, Any]], instances: list[dict[str, Any]], not_analysed: list[str]) -> dict[str, Any]` — excerpts are `trim_excerpt` of the cited lines read from `inputs/<file_path>`; a repeated id keeps the entry with the lowest line and lists the others under `also_at: [{file_path, line_range}]`; entries sort by `(file_path, first line, kind, id)`
    - `class IndexSchemaError(Exception)`; `def write_index(run_dir: Path, doc: dict[str, Any]) -> Path` (schema-validates first; atomic write to `00-context/iac-evidence-index.yaml`)
  - `summary.py`: `SUMMARY_FILENAME = "iac-summary.md"`; `def render_summary(doc: Mapping[str, Any]) -> str`; `def write_summary(run_dir: Path, doc: Mapping[str, Any]) -> Path`
  - Schema skeleton (R7), root key `iac_evidence_index`, `additionalProperties: false` at every level: `generated_at` (date-time), `tools` (object of string-or-null), `context_params_version` (integer, optional), `roots[] {id, kind: atmos|plain, path, engine, status: resolved|partial|unresolved-raw, reason?}`, `instances[] {id, root, stack?, component?, module_path, engine, unknown_vars[], fetch, workspace}`, `not_analysed[]`, `entries[]` with `required: [id, kind, source, file_path, line_range, excerpt, apd_relevance, confidence]` and properties `id` (`^iev-[0-9a-f]{8}$`), `kind` (`unknown | override | execution_point`), `root`, `instance`, `address` (string or null), `source` (`apd`), `file_path` (`^(?!/)(?!.*\.\.).+$`), `line_range` (`^L[0-9]+(-L[0-9]+)?$`), `excerpt` (1–500 chars), `provenance[] {key, file, line}`, `apd_relevance[]` (`$ref` `_defs.schema.json#/$defs/apd_goal`, `minItems: 0`), `confidence` (`static | uncertain`), `uncertain_reason` (null), `reason` (the `UnknownReason` values), `execution` (the `ExecutionKind` values), `overrides_file`, `detail` (≤ 2,000 chars), `also_at[]`, `dependencies[]`.

`render_summary` writes, in order: a one-line provenance note ("Engine-produced by `apd-gauntlet iac run`; cite `iac-evidence-index.yaml` entries, not this file."), a Roots table (`Root | Kind | Engine | Status | Instances | Unknowns`, with each `unresolved-raw` root marked "intake reads this root's declared files directly, as in 1.7"), Not analysed, Module fetch (counts per `fetch` value), Unknowns by reason, and Execution points by kind.

- [ ] **Step 1: Write the failing tests**

```python
def test_mint_entry_id():
    expected = "iev-" + hashlib.sha256(b"prod/vpc|aws_security_group.ssh|check|AWS-0107").hexdigest()[:8]
    assert mint_entry_id("prod/vpc", "aws_security_group.ssh", "check", "AWS-0107") == expected

def test_trim_excerpt():
    assert len(trim_excerpt(" ".join(["w"] * 40)).split()) == 25 and len(trim_excerpt("x" * 900)) == 500

def test_builder_excerpt_and_locator(tmp_path):
    inputs = copy_fixture(tmp_path, "atmos-basic"); b = IndexBuilder(inputs)
    iid = b.add_unknown(Unknown("function_literal", "platform/stacks/orgs/prod.yaml", 11, "!exec …",
                                root="atmos:platform", instance="prod/vpc", key="vars.build_id"))
    doc = b.document(generated_at="2026-10-10T12:00:00Z", tools={}, roots=[], instances=[], not_analysed=[])
    e = doc["iac_evidence_index"]["entries"][0]
    assert e["id"] == iid and e["excerpt"] == 'build_id: !exec "touch EXEC_RAN && echo built"'
    assert canonical_locator(e) == f"iac:prod/vpc:-@platform/stacks/orgs/prod.yaml:L11#{iid}"

def test_duplicate_id_collapses_to_also_at(tmp_path): ...   # same unknown key at lines 9 and 3 → one entry at L3, also_at [L9]

def test_write_index_validates(tmp_path):
    with pytest.raises(IndexSchemaError):
        write_index(tmp_path, {"iac_evidence_index": {"entries": [{"id": "bad"}]}})

def test_summary_marks_unresolved_raw():
    doc = {"iac_evidence_index": {"roots": [{"id": "atmos:platform", "kind": "atmos", "path": "platform",
           "engine": "opentofu", "status": "unresolved-raw", "reason": "tool_missing"}],
           "instances": [], "entries": [], "not_analysed": [], "tools": {}, "generated_at": "2026-10-10T12:00:00Z"}}
    assert "unresolved-raw" in render_summary(doc) and "as in 1.7" in render_summary(doc)

def test_hcl_execution_points(tmp_path):
    ws = workspace_for(tmp_path, "exec-points")
    assert sorted(e.kind for e in hcl_execution_points(ws)) == [
        "external_data", "local_exec", "provisioner_resource", "remote_exec"]

def test_atmos_execution_points(tmp_path): ...  # atmos.yaml commands + workflow shell step + component hooks + command "./bin/tf.sh" → atmos_custom_command, atmos_workflow_shell, atmos_hook, atmos_component_command
```

`workspace_for(tmp_path, name)` (conftest helper) copies a fixture and builds its plain-root workspace with `build_workspace`.

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_index.py tests/iac/test_inventory.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `inventory.py`, `index.py`, `summary.py` and the schema**

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_index.py tests/iac/test_inventory.py tests/test_meta_schemas.py tests/test_schema_vocab_centralized.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/inventory.py tools/apd_gauntlet/iac/index.py tools/apd_gauntlet/iac/summary.py tools/apd_gauntlet/data/schemas/iac-evidence-index.schema.json tests/fixtures/iac/exec-points tests/iac
git commit -m "feat(iac): add the evidence index skeleton, execution points and summary"
```

### Task 11: Pipeline and the `iac run` / `iac consent` commands

**Files:**

- Create: `tools/apd_gauntlet/iac/pipeline.py`, `tools/apd_gauntlet/iac/cli.py`, `docs/iac-evaluation.md`, `tests/fixtures/iac/plain-remote/` (the `plain` fixture plus `module "vpc" { source = "terraform-aws-modules/vpc/aws" version = "5.1.0" }` in `infra/live/prod/main.tf`)
- Modify: `tools/apd_gauntlet/cli.py` (`from .iac.cli import iac_group`; `main.add_command(iac_group)`), `docs/schema-evolution.md`, `CHANGELOG.md`, `docs/running-the-gauntlet.md:359`
- Test: `tests/iac/test_pipeline.py`, `tests/iac/test_cli_iac.py`

**Interfaces:**

- Consumes: Tasks 1–10
- Produces (`pipeline.py`):
  - `STATE_DIR = ".apd-state/iac"`; `INSTANCES_FILENAME = "instances.json"`
  - `@dataclass class IacRunResult: status: Literal["ok", "skipped", "up_to_date", "failed"]; exit_code: int; index_path: Path | None; summary_path: Path | None; messages: list[str]`
  - `@dataclass class PipelineState: run_dir: Path; inputs: Path; cfg: IacConfig; roots: list[Root]; root_status: dict[str, tuple[RootStatus, str]]; sanitized: dict[str, SanitizeResult]; instances: list[Instance]; workspaces: dict[str, Workspace]; builder: IndexBuilder; tools: dict[str, ToolStatus]; not_analysed: list[str]; messages: list[str]`
  - `Stage = Callable[[PipelineState, ToolRunner], None]`; `STAGES: list[tuple[str, Stage]]` — this plan registers `discover`, `resolve`, `workspace`, `fetch`, `inventory`; `def insert_stage(name: str, stage: Stage, *, after: str) -> None` (Plans 2 and 3 add `scan`, `checks`, `plan`, `graph`, `context`)
  - `def run_iac(run_dir: Path, *, runner: ToolRunner | None = None) -> IacRunResult` — `None` resolves `apd_gauntlet.iac.pipeline.run_tool` at call time so tests can monkeypatch it
  - `def collect_fetch_sources(run_dir: Path, *, runner: ToolRunner | None = None) -> list[str]` — runs `discover` through `workspace` and returns sorted unique `"<source>@<version>"` (or `<source>`) strings for remote sources
  - `def load_instances(run_dir: Path) -> dict[str, Instance]` (reads `.apd-state/iac/instances.json`, which `run_iac` writes with `{id: dataclasses.asdict(instance)}`, and rebuilds the `VarOrigin` values)
- Produces (`cli.py`): click group `iac_group` (name `iac`) with `run RUN_DIR` (prints `result.messages`, exits `result.exit_code`) and `consent RUN_DIR [--yes]`.

`run_iac` order and rules:

1. `load_iac_config` → None: `status="skipped"`, exit 0, writes nothing. No roots after discovery: `skipped`, message `iac: no Terraform or Atmos roots declared`.
2. Stamp: `.apd-state/iac/stamp.json` = `{inputs_sha256, config_sha256, consent_sha256, tools, engine_version}` over every file under the declared root paths and plan paths. An equal stamp with a schema-valid index → `up_to_date`, exit 0, no tool calls beyond the version checks.
3. `tool_status` for every tool in `data/iac/tools.yaml`. An Atmos root with Atmos absent or below minimum → root `unresolved-raw` with a `tool_missing` unknown; `require_tools: true` and a needed tool not ok → `failed`, exit 1, last message names the tool, the minimum and its `install_hint`.
4. Stages in `STAGES` order. An exception inside one root's or one instance's stage becomes an `internal_error` unknown for that scope, and the run continues. A root whose sanitise is refused, or whose every manifest failed, is `unresolved-raw`; one with some failed manifests is `partial`. The `resolve` stage calls `attach_provenance` per Atmos root; the `workspace` stage dedupes by `dedupe_key`.
5. Fetch: `cfg.fetch`, remote sources present and `has_fetch_consent` → `fetch_modules`. No consent → each remote source becomes `remote_module_not_fetched` with detail `run 'apd-gauntlet iac consent <run-dir>'`, the instances' `fetch` is `not_fetched`, and the message `iac: module fetch needs consent: run 'apd-gauntlet iac consent <run-dir>'` is added. `cfg.fetch` false → remote sources are `remote_module_not_fetched` with detail `infrastructure.modules.fetch is false`.
6. `write_index`, `write_summary`, then the stamp and `instances.json`. An `IndexSchemaError` → `failed`, exit 1 (an engine bug, never IaC input).

`iac consent`: computes `collect_fetch_sources`; `cfg.fetch` false → prints `module fetch is disabled for this run (infrastructure.modules.fetch: false)`, exit 0; no remote sources → prints `no remote module sources to fetch`, exit 0; otherwise prints `The following module sources will be downloaded with 'tofu get' (network access):` and one source per line, then `--yes` → `record_fetch_consent(..., "flag")`; on a TTY, `click.prompt("Type 'fetch' to allow these downloads")` equal to `fetch` → `record_fetch_consent(..., "prompt")`; anything else exits 2 with `consent not recorded`.

- [ ] **Step 1: Write the failing tests**

```python
def test_skipped_when_not_static(tmp_path, fake_runner):
    run = write_run(tmp_path, {})
    assert run_iac(run, runner=fake_runner).status == "skipped"
    assert not (run / "00-context/iac-evidence-index.yaml").exists() and fake_runner.calls == []

def test_plain_root_end_to_end(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "plain", {"terraform": ["infra/**"]})
    before = tree_digest(run / "inputs")
    r = run_iac(run, runner=fake_runner)
    idx = load_index(run)
    assert r.exit_code == 0 and [i["id"] for i in idx["instances"]] == ["plain:infra/live/prod"]
    assert idx["roots"][0]["status"] == "resolved" and "infra/live/prod/deploy.tfstack.hcl" in idx["not_analysed"]
    assert tree_digest(run / "inputs") == before and (run / "00-context/iac-summary.md").exists()

def test_missing_atmos_marks_root_unresolved_raw(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]})
    fake_runner.on("atmos", ["version"], returncode=127)
    r = run_iac(run, runner=fake_runner)
    assert r.exit_code == 0 and load_index(run)["roots"][0]["status"] == "unresolved-raw"
    assert "unresolved-raw" in (run / "00-context/iac-summary.md").read_text()

def test_require_tools_fails_phase(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]}, require_tools=True)
    fake_runner.on("atmos", ["version"], stdout='{"version": "1.200.0"}')
    r = run_iac(run, runner=fake_runner)
    assert r.exit_code == 1 and "atmos" in r.messages[-1] and "1.231.0" in r.messages[-1]

def test_fetch_without_consent_continues(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "plain-remote", {"terraform": ["infra/**"]}, fetch=True)
    r = run_iac(run, runner=fake_runner)
    assert r.exit_code == 0 and any("iac consent" in m for m in r.messages)
    assert not any(c[0] == "tofu" and c[1] == ["get"] for c in fake_runner.calls)
    assert load_index(run)["instances"][0]["fetch"] == "not_fetched"

def test_fetch_with_consent_calls_tofu_get(tmp_path, fake_runner, tools_ok): ...   # record_fetch_consent first → one ("tofu", ["get"], …, True) call, fetch "fetched"
def test_second_run_up_to_date(tmp_path, fake_runner, tools_ok): ...   # run twice → second status "up_to_date", no describe or get calls
def test_internal_error_isolated(tmp_path, fake_runner, tools_ok, monkeypatch): ...  # parse_file raises for one of two roots → internal_error unknown for it, the other resolved, exit 0
def test_instances_state_written(tmp_path, fake_runner, tools_ok): ...   # load_instances(run)["plain:infra/live/prod"].engine == "terraform"
```

```python
def test_cli_run_and_consent(tmp_path, monkeypatch, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "plain-remote", {"terraform": ["infra/**"]}, fetch=True)
    monkeypatch.setattr(pipeline, "run_tool", fake_runner)
    r = CliRunner().invoke(main, ["iac", "consent", str(run)], input="no\n")
    assert r.exit_code == 2 and "terraform-aws-modules/vpc/aws@5.1.0" in r.output
    r = CliRunner().invoke(main, ["iac", "consent", str(run), "--yes"])
    assert r.exit_code == 0 and has_fetch_consent(run, ["terraform-aws-modules/vpc/aws@5.1.0"])
    fake_runner.on("tofu", ["get"])
    assert CliRunner().invoke(main, ["iac", "run", str(run)]).exit_code == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_pipeline.py tests/iac/test_cli_iac.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `pipeline.py`, `cli.py` and the registration in `cli.py`**

- [ ] **Step 4: Write the docs**

`docs/iac-evaluation.md`: the run-config block (spec §6), what the `iac` phase does and writes, required and optional tools with minimums, the safety model (spec §12, including the `atmos.Component` template finding and the recommendation to run hostile repositories in a container with no network), consent with `iac consent`, and the `unresolved-raw` fallback. `docs/schema-evolution.md`: a `## v2.0.0 — IaC evaluation (additive)` section with a dated entry for the run-config `infrastructure` additions and the new `iac-evidence-index` schema (skeleton). `CHANGELOG.md` under ``## Unreleased — 2.0 line (`next`)`` → `### Added`: the `iac` phase, `apd-gauntlet iac run` and `iac consent`. `docs/running-the-gauntlet.md:359`: the static-infra row also names `apd-gauntlet iac run`.

- [ ] **Step 5: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac -v && /home/claude/venv-apd/bin/mypy tools/ && markdownlint-cli2 docs/iac-evaluation.md docs/schema-evolution.md CHANGELOG.md docs/running-the-gauntlet.md`
Expected: PASS, mypy clean, 0 lint errors

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/iac tools/apd_gauntlet/cli.py tests/iac tests/fixtures/iac/plain-remote docs CHANGELOG.md
git commit -m "feat(iac): add the iac pipeline and the iac run/consent commands"
```

### Task 12: The `iac` phase in the workflow, `plan-run` and the runner

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js:36-45` (`meta.phases`) and the setup/intake boundary (`:265-313`), `tools/apd_gauntlet/plan_run.py:48-56`, `tools/apd_gauntlet/runner/flow.py` (`PHASES`, phase table)
- Test: `tests/test_workflow_apd_gauntlet.py:27-49` (extend), `tests/test_cli_plan_run.py` (extend), `tests/runner/test_flow_pre_synthesis.py` (extend), `tests/test_workflow_dispatch_trace.py` (WS3 harness, extend)

**Interfaces:**

- Consumes: `apd-gauntlet iac run <run-dir>` (Task 11); LA2's `Runner`, `scenario()`, `FakeCli`; WS3's `pyStep` (dispatching `apd-cli-runner`) and its trace helpers `trace(cfg)`, `cli(t)`, `HA_SHAPED`; WS5's `build-lens-skills` setup step; WS1's `resume-plan` (`tools/apd_gauntlet/resume_plan.py` `RESUMABLE_STEPS`)
- Produces (R3):
  - `meta.phases` and `runner.flow.PHASES` gain `'iac'` immediately after `'setup'` and before `'intake'`.
  - Workflow: after the setup phase's last step (WS3's `prepare-run`, then WS5's `build-lens-skills`) and before `phase('intake')`, `phase('iac');` then, only when `args.infrastructure && args.infrastructure.mode === 'static'`, `const iacReceipt = pyStep('iac', { phase: 'iac', label: 'iac-run', positional: 'run ' + runDir, alwaysRun: true, outputs: runDir + '/00-context/iac-evidence-index.yaml, ' + runDir + '/00-context/iac-summary.md' });` followed by `bailIfInterrupted(iacReceipt, 'iac')` and, on `isErr(iacReceipt)`, `throw new Error('iac phase failed: a required IaC tool is missing (infrastructure.require_tools: true) or the evidence index failed its schema gate; see the receipt errors.')`; otherwise `log('iac: infrastructure.mode is not static — skipping.')`. `iac run` is idempotent through its stamp, so the step is always-run.
  - `plan_run.build_plan`: when `cfg.get("infrastructure", {}).get("mode") == "static"`, append `_step("iac", "CLI", f"iac run {run_dir}", "00-context/iac-evidence-index.yaml, 00-context/iac-summary.md")` after the last `setup` step.
  - Runner: phase `iac` with one CLI step label `iac-run` running `["iac", "run", str(run_dir)]` under the same condition; a nonzero exit → `RunHalted("iac", <stderr tail>)`.
  - WS1 `resume-plan` needs no entry: `RESUMABLE_STEPS` lists agent steps only, and CLI steps always run; `iac run` itself returns `up_to_date` from its stamp.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_workflow_apd_gauntlet.py — add "iac" after "setup" in EXPECTED_PHASES and DIRECT_PHASE_LITERALS
def test_iac_phase_between_setup_and_intake() -> None:
    text = _text()
    phases = re.findall(r"'([^']+)'", re.search(r"phases:\s*\[(.*?)\]", text, re.DOTALL).group(1))
    assert phases.index("iac") == phases.index("setup") + 1 == phases.index("intake") - 1
    assert text.index("phase('setup')") < text.index("phase('iac')") < text.index("phase('intake')")

def test_iac_step_gated_on_static_mode() -> None:
    text = _text()
    assert re.search(r"args\.infrastructure\.mode\s*===\s*'static'", text)
    assert "pyStep('iac'" in text and "label: 'iac-run'" in text and "positional: 'run ' + runDir" in text
```

```python
# tests/test_cli_plan_run.py
def test_plan_run_includes_iac_when_static(tmp_path):
    run_dir = _write_run(tmp_path, dict(FULL_CFG, infrastructure={"mode": "static"}))
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(run_dir)]).output)
    phases = [s["phase"] for s in plan]
    assert phases.index("iac") < phases.index("intake")
    assert next(s for s in plan if s["phase"] == "iac")["ref"] == "iac run runs/apd-test-full"

def test_plan_run_omits_iac_by_default(tmp_path):
    plan = json.loads(CliRunner().invoke(main, ["plan-run", "--json", str(_write_run(tmp_path, FULL_CFG))]).output)
    assert "iac" not in {s["phase"] for s in plan}
```

```python
# tests/runner/test_flow_pre_synthesis.py
def test_iac_step_runs_before_intake_when_static(tmp_path):
    r = scenario(tmp_path, cfg={"infrastructure": {"mode": "static"}})
    asyncio.run(r.runner.run(stop_after="intake"))
    assert r.labels.index("iac-run") == r.labels.index("intake") - 1

def test_iac_failure_halts(tmp_path):
    r = scenario(tmp_path, cfg={"infrastructure": {"mode": "static"}}, cli_outcomes={"iac-run": (1, "atmos missing")})
    assert asyncio.run(r.runner.run()) == "failed" and r.ledger.state == "failed"

def test_no_iac_step_by_default(tmp_path):
    r = scenario(tmp_path); asyncio.run(r.runner.run(stop_after="intake"))
    assert "iac-run" not in r.labels
```

```python
# tests/test_workflow_dispatch_trace.py (WS3 harness)
def test_iac_dispatch_only_when_static():
    labels = [d["label"] for d in trace({**HA_SHAPED, "infrastructure": {"mode": "static"}})]
    assert labels.index("prepare-run") < labels.index("iac-run") == labels.index("intake") - 1
    assert "iac-run" not in [d["label"] for d in trace(HA_SHAPED)]
    assert next(d for d in cli(trace({**HA_SHAPED, "infrastructure": {"mode": "static"}}))
                if d["label"] == "iac-run")["command"].startswith("apd-gauntlet iac run runs/r")
```

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py tests/runner -v`
Expected: FAIL on the new tests (and `test_flow_parity.py::test_phases_match_workflow` once only one side changes)

- [ ] **Step 3: Implement the phase in all three channels**

- [ ] **Step 4: Run to verify pass, including both parity tests**

Run: `/home/claude/venv-apd/bin/pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py tests/runner tests/test_workflow_dispatch_trace.py -v`
Expected: PASS (the trace test skips without Node), including `test_plan_run_phase_names_consistent_with_workflow` and `tests/runner/test_flow_parity.py::test_phases_match_workflow`

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tools/apd_gauntlet/plan_run.py tools/apd_gauntlet/runner/flow.py tests
git commit -m "feat(workflow): add the iac phase between setup and intake"
```

- [ ] **Step 6: Operator comparison**

Run the master plan Task 1 set on this branch, then `apd-gauntlet compare-runs <previous-accepted> <candidate> --gates eval/gates.yaml` for each run, where `<previous-accepted>` is the same run from the last accepted commit. Expected: exit 0 (none of the committed examples declares `infrastructure.mode: static`, so their outputs are unchanged).

### Task 13: Security regression suite and the `iac-tools` CI job

**Files:**

- Create: `tests/iac/test_security_regressions.py`
- Modify: `.github/workflows/python-tests.yml` (new job `iac-tools`), `tests/iac/conftest.py` (fixture `http_sentinel`, helper `add_component`)

**Interfaces:**

- Consumes: `run_iac`, `load_instances` (Task 11), `VALIDATORS` (Task 2), fixtures from Tasks 5–6
- Produces: CI job `iac-tools` (ubuntu-latest, Python 3.12). A setup step downloads Atmos 1.231.0 and Trivy 0.70.0 from their GitHub release assets with SHA-256 verification against each release's checksum file, and runs `pipx install checkov==3.3.26`; then `pip install -e ".[dev,iac]"`. Only that setup step uses the network. The test step `pytest -m iac_tools -v` runs offline: Trivy uses its bundled checks (`--skip-check-update`), Checkov never downloads (`--skip-download`, `--download-external-modules false`), and Atmos calls go through `run_tool`'s closed proxy (ADR-0017 covers tests and real runs, not tool installation).

- [ ] **Step 1: Write the failing tests**

All tests are `@pytest.mark.iac_tools`, call `require_tools("atmos")` (plus scanners where noted), and run the real `run_iac` with `run_tool`.

```python
def test_exec_canary_never_created(tmp_path, require_tools):
    require_tools("atmos")
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]})
    run_iac(run)
    assert not list(tmp_path.rglob("EXEC_RAN"))
    kinds = {(e["kind"], e.get("reason"), e.get("execution")) for e in load_index(run)["entries"]}
    assert ("unknown", "function_literal", None) in kinds and ("execution_point", None, "atmos_exec") in kinds

def test_template_component_canary_never_created(tmp_path, require_tools):
    require_tools("atmos")
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]})
    canary = tmp_path / "TEMPLATE_RAN"
    script = run / "inputs/platform/bin/tf.sh"; script.parent.mkdir()
    script.write_text(f"#!/bin/sh\ntouch {canary}\necho '{{}}'\n"); script.chmod(0o755)
    replace(run / "inputs/platform/atmos.yaml", 'command: "tofu"', f'command: "{script}"')
    add_component(run / "inputs/platform/stacks/orgs/prod.yaml", "peer",
                  vars={"out": '{{ (atmos.Component "vpc" .stack).outputs.vpc_id }}'})
    run_iac(run)
    assert not canary.exists()

def test_outside_include_content_never_in_outputs(tmp_path, require_tools):
    require_tools("atmos")
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]})
    outside = tmp_path / "outside.yaml"; outside.write_text("leak: OUTSIDE-CANARY-7f3a\n")
    append(run / "inputs/platform/stacks/orgs/prod.yaml",
           ["        host: !include /etc/hostname", f"        secret: !include {outside}"])
    run_iac(run)
    assert "OUTSIDE-CANARY-7f3a" not in grep_tree(run)
    reasons = [e.get("reason") for e in load_index(run)["entries"]]
    assert reasons.count("outside_include") == 2

def test_remote_include_makes_no_connection(tmp_path, require_tools, http_sentinel):
    require_tools("atmos")
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]})
    append(run / "inputs/platform/stacks/orgs/prod.yaml",
           [f"        remote: !include http://127.0.0.1:{http_sentinel.port}/x.yaml"])
    r = run_iac(run)
    assert r.exit_code == 0 and http_sentinel.requests == []
    assert "remote_include" in [e.get("reason") for e in load_index(run)["entries"]]

def test_provenance_points_at_prod_override(tmp_path, require_tools):
    require_tools("atmos")
    run = run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]})
    run_iac(run)
    inst = load_instances(run)["prod/vpc"]
    assert inst.provenance["map_public_ip_on_launch"].line == 8
    assert inst.inherited["map_public_ip_on_launch"].value is False

def test_only_allowlisted_vectors_reach_subprocess(tmp_path, require_tools, monkeypatch):
    require_tools("atmos")
    seen = []
    real = sandbox_tools.subprocess.Popen
    monkeypatch.setattr(sandbox_tools.subprocess, "Popen", lambda argv, **kw: seen.append(argv) or real(argv, **kw))
    run_iac(run_with_fixture(tmp_path, "atmos-basic", {"atmos": [{"root": "platform"}]}))
    for argv in seen:
        VALIDATORS[Path(argv[0]).name](list(argv[1:]))   # raises on anything off the allowlist
    assert all("--process-functions=false" in a for a in seen if Path(a[0]).name == "atmos" and "describe" in a)

def test_no_process_start_outside_gateway():
    pkg = REPO / "tools/apd_gauntlet"
    offenders = [p for d in ("iac", "context") for p in (pkg / d).rglob("*.py")
                 if re.search(r"^\s*(import|from)\s+(subprocess|pty)\b|\bos\.(system|popen|exec\w*|spawn\w*|posix_spawn\w*)\(",
                              p.read_text(), re.M)]
    assert offenders == []
```

`test_no_process_start_outside_gateway` is not `iac_tools`-marked: it runs everywhere and keeps `sandbox/tools.py` the only process gateway as `iac/` and `context/` grow.

`http_sentinel` is a fixture running `http.server` on an ephemeral port in a thread and recording each request path. `add_component(manifest, name, vars)` appends a component block under `components.terraform` in a stack manifest copy.

- [ ] **Step 2: Run the suite**

Run: `PATH=/tmp/claude-0/-home-claude-apd-gauntlet/62f4ef46-a9fa-56b6-909b-632a30f9b40f/scratchpad/bin:$PATH /home/claude/venv-apd/bin/pytest tests/iac/test_security_regressions.py -v`
Expected: PASS. These tests pin behaviour Tasks 6–11 built; a failure is a defect in the owning task, fixed there before this task commits. Without Atmos on PATH every test reports SKIPPED.

- [ ] **Step 3: Add the CI job**

- [ ] **Step 4: Run the full suite**

Run: `/home/claude/venv-apd/bin/pytest -q`
Expected: PASS, with `iac_tools` tests skipped where the tools are absent

- [ ] **Step 5: Commit**

```bash
git add tests/iac/test_security_regressions.py tests/iac/conftest.py .github/workflows/python-tests.yml
git commit -m "test(iac): pin the Atmos and include probes as security regressions"
```

### Task 14: `doctor` checks and ADR-0027

**Files:**

- Create: `tools/apd_gauntlet/iac/doctor.py`, `docs/adrs/0027-iac-evaluation-pipeline.md`, `tests/test_adr_0027.py`
- Modify: `tools/apd_gauntlet/cli.py` (call `register_iac_doctor_checks()` once at import, after the `iac` group registration)
- Test: `tests/iac/test_doctor.py`

**Interfaces:**

- Consumes (LA3, `tools/apd_gauntlet/app/services.py`): `@dataclass class Check: name: str; status: Literal["pass", "warn", "fail"]; detail: str; fix: str | None`; `doctor()`; and, from amendment A3, `register_doctor_check(name: str, fn: Callable[[UserConfig], Check]) -> None`, with `doctor()` appending registered checks after the built-ins. Also `tool_status`, `install_hint`, `load_tool_specs` (Task 2)
- Produces: `def iac_tool_check(name: str) -> Callable[[UserConfig], Check]`; `def register_iac_doctor_checks() -> None` (idempotent) registering checks `iac-atmos`, `iac-tofu`, `iac-trivy`, `iac-checkov`, `iac-shellcheck`, `iac-python-hcl2`. Status: found and at or above minimum → `pass` with the version; absent → `warn` (`fix` = `install_hint`), because IaC evaluation is optional; found below minimum → `fail` (`fix` names the minimum), because an older Atmos may not honour `--process-functions=false`. `iac-python-hcl2` warns with `pip install "apd-gauntlet[iac]"` when the import fails.

- [ ] **Step 1: Write the failing tests**

```python
def test_checks_registered_after_cli_import():
    import apd_gauntlet.cli  # noqa: F401
    names = [c.name for c in doctor(UserConfig())]
    assert {"iac-atmos", "iac-tofu", "iac-trivy", "iac-checkov", "iac-shellcheck", "iac-python-hcl2"} <= set(names)

def test_old_atmos_fails(monkeypatch):
    monkeypatch.setattr(doctor_mod, "tool_status", lambda name, **k: ToolStatus(name, True, "1.200.0", "1.231.0", False, "below minimum 1.231.0"))
    c = iac_tool_check("atmos")(UserConfig())
    assert c.status == "fail" and "1.231.0" in c.fix

def test_missing_tool_warns_with_install_hint(monkeypatch):
    monkeypatch.setattr(doctor_mod, "tool_status", lambda name, **k: ToolStatus(name, False, None, "3.3.26", False, "not found"))
    c = iac_tool_check("checkov")(UserConfig())
    assert c.status == "warn" and "pipx install checkov" in c.fix

def test_tool_at_minimum_passes_without_fix(monkeypatch):
    monkeypatch.setattr(doctor_mod, "tool_status", lambda name, **k: ToolStatus(name, True, "0.70.0", "0.70.0", True, "ok"))
    c = iac_tool_check("trivy")(UserConfig())
    assert c == Check(name="iac-trivy", status="pass", detail="trivy 0.70.0", fix=None)
```

```python
# tests/test_adr_0027.py — same shape as tests/test_adr_0021.py
def test_adr_header_and_sections():
    text = ADR.read_text()
    assert text.startswith("# ADR-0027: ") and "**Status:**" in text and "**Date:** 2026-10-10" in text
    for h in ("## Context", "## Decision", "## Consequences", "## Alternatives considered"):
        assert h in text

def test_adr_records_spec_decisions():
    t = ADR.read_text()
    for needle in ("--process-functions=false", "tofu get", "plan JSON", "Trivy", "Checkov",
                   "Terraform binary", "packets", "atmos.Component"):
        assert needle in t
```

- [ ] **Step 2: Run to verify failure**

Run: `/home/claude/venv-apd/bin/pytest tests/iac/test_doctor.py tests/test_adr_0027.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `doctor.py`, the registration call and the ADR**

ADR-0027 records the decisions in spec §3 (one row each) plus the template-function finding from Task 6 and its two mitigations.

- [ ] **Step 4: Run to verify pass**

Run: `/home/claude/venv-apd/bin/pytest tests/iac tests/test_adr_0027.py tests/test_adrs.py -v && markdownlint-cli2 docs/adrs/0027-iac-evaluation-pipeline.md`
Expected: PASS, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac/doctor.py tools/apd_gauntlet/cli.py docs/adrs/0027-iac-evaluation-pipeline.md tests/test_adr_0027.py tests/iac/test_doctor.py
git commit -m "feat(iac): add doctor checks for IaC tools and ADR-0027"
```
