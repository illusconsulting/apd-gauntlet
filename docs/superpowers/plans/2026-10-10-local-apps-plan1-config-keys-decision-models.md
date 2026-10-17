# Local Apps Plan 1 — Config, Keys and Decision Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an operator store a Cloudflare, TypeSafe or OpenRouter key (or none), enable a decision model per run, and run the advisory finding-QA task from the CLI and from the plugin workflow.

**Architecture:** A user config file (no secrets) plus a credential resolver (env, OS keychain, `op://`). A `decide` package holds typed System One questions and answers, a model catalog, one adapter per provider and an async `DecisionClient` that refuses oversize state, retries boundedly and enforces a spend cap. `finding-qa` is the first task; it writes a schema-validated decision record and never edits findings. The run opts in through a new `decision_model:` block in `.apd-run.yaml`.

**Tech Stack:** Python 3.10+, click, PyYAML, jsonschema (Draft 2020-12), `platformdirs` (base), `httpx` + `keyring` (extra `decide`), pytest with `httpx.MockTransport` and an in-memory keyring backend.

**Spec:** `docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md` (§5 providers, §6 credentials and config, §9 testing). This is Plan 1 of 3.

**Amended 2026-10-17** per the amendments register (A1.1, A1.2, A1.3, A1.4, A1.5, A1.6, A1.7, A1.8, A11.1, A11.2, A11.3, A11.4, A11.5, A11.6, A12.1, A12.2, A12.3, A12.7, A12.10, A12.11, A15.21, A15.27).

## Global Constraints

- Python floor `>=3.10`; `mypy --strict`, `ruff`, coverage `fail_under = 85` all stay green.
- Base dependencies gain only `platformdirs>=4`. Extra `decide = ["httpx>=0.27,<1", "keyring>=25.7,<26"]`.
- No network in CI (ADR-0017). Every provider test uses `httpx.MockTransport`.
- Secrets never appear in config files, run directories, decision records, logs or exception messages. There is no plaintext fallback.
- Credential env var names: `ANTHROPIC_API_KEY`, `CLOUDFLARE_API_TOKEN`, `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`. Keychain service name: `apd-gauntlet`.
- Default decision provider is `none`; a run without a `decision_model:` block behaves exactly as today.
- System One limits: 1–64 questions per call; question ids match `^[A-Za-z0-9_.-]{1,100}$`; ≤ 4 images, Clef models only.
- Token estimate: `ceil(len(text.encode("utf-8")) / 3)`, applied to state plus questions, plus 1,024 per image; refuse when it exceeds the model's context − 1024.
- Retries: 429 and 5xx only, max 3, exponential backoff base 1 s with full jitter, `Retry-After` honored up to 30 s.
- Finding-QA thresholds load through `decide.policy.load_threshold` from `tools/apd_gauntlet/data/decide/thresholds.yaml` (WS2 `THRESHOLDS_PATH`) under keys `finding-qa.lens_drift`, `finding-qa.unsupported` and `finding-qa.severity_delta`. LA1 appends the proposals 0.5, 0.3 and 1.0 as `{threshold, precision: null, recall: null, n: 0, labels_sha256: null, calibrated: false, provider: null, model: null}`. Every decision record copies `calibrated` (true only when all three are calibrated for the record's provider and model).
- Decision records live at `runs/<id>/40-synthesis/decisions/<task>.<scope>.yaml`.

## Review Focus

- **Headless Linux with no keychain backend:** `keys set` must exit 1 with the env-var instructions, never write a file.
- **Provider rejects the key (401/403):** one `AuthRejected` naming the provider, no retry, no key fragment in the message.
- **A finding larger than the model's context:** that item is recorded with `outcome: error`; the task continues with the rest.
- **The same key in env and keychain:** env wins and `keys show` reports `source: env`.
- **A run re-executes `decide` after a crash:** an up-to-date record (same finding ids, same schema hash) is skipped, so spend isn't doubled.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/config.py` | User config dataclasses, load/save, validation | Create |
| `tools/apd_gauntlet/data/schemas/user-config.schema.json` | User config schema | Create |
| `tools/apd_gauntlet/credentials.py` | Credential resolution, keychain store/clear, masking | Create |
| `tools/apd_gauntlet/decide/__init__.py` | Package exports | Create |
| `tools/apd_gauntlet/decide/errors.py` | Error hierarchy | Create |
| `tools/apd_gauntlet/decide/types.py` | Question and answer dataclasses, `DecisionResult`, `Usage` | Create |
| `tools/apd_gauntlet/decide/catalog.py` + `data/decision-models.json` | Model catalog | Create |
| `tools/apd_gauntlet/decide/providers.py` | Cloudflare, TypeSafe, OpenRouter adapters | Create |
| `tools/apd_gauntlet/decide/client.py` | `DecisionClient` | Create |
| `tools/apd_gauntlet/decide/factory.py` | Build a client from config + run config | Create |
| `tools/apd_gauntlet/decide/records.py` + `data/schemas/decision-record.schema.json` | Decision record writer and schema | Create |
| `tools/apd_gauntlet/decide/tasks/finding_qa.py` | Finding-QA questions, state, flags, task runner | Create |
| `tools/apd_gauntlet/data/schemas/run-config.schema.json` | Add `decision_model` | Modify |
| `tools/apd_gauntlet/validate.py` | Validate `40-synthesis/decisions/*.yaml` | Modify |
| `tools/apd_gauntlet/cli.py` | `keys` group, `decide` command | Modify |
| `tools/apd_gauntlet/plan_run.py`, `.claude/workflows/apd-gauntlet.js` | Guarded finding-QA step after each tier gate | Modify |
| `pyproject.toml` | `platformdirs`, extra `decide`, package data | Modify |
| `docs/decision-models.md`, `docs/adrs/0024-optional-decision-model-layer.md`, `CHANGELOG.md` | Docs | Create/Modify |
| `tests/decide/…`, `tests/test_config.py`, `tests/test_credentials.py`, `tests/test_cli_keys.py`, `tests/test_cli_decide.py` | Tests | Create |
| `tests/fixtures/decide/*.json` | Provider response fixtures | Create |

---

### Task 1: User config

**Files:**

- Create: `tools/apd_gauntlet/config.py`, `tools/apd_gauntlet/data/schemas/user-config.schema.json`
- Modify: `pyproject.toml` (add `platformdirs>=4` to `dependencies`)
- Test: `tests/test_config.py`

**Interfaces:**

- Produces:
  - `class ConfigError(Exception)`
  - `@dataclass class LlmConfig: provider: Literal["anthropic","bedrock","vertex","foundry"] = "anthropic"; default_model: str = "opus"; model_overrides: dict[str, str]; max_parallel_agents: int = 3; run_budget_usd: float = 100.0; extra_env: dict[str, str]`
  - `@dataclass class DecisionModelConfig: provider: Literal["none","cloudflare","typesafe","openrouter"] = "none"; model: str | None = None; cloudflare_account_id: str | None = None; timeout_s: float = 30.0; max_concurrency: int = 8; budget_usd_per_run: float = 2.0`
  - `@dataclass class DefaultsConfig: domains: list[str] = ["pbm"]; code_recon: Literal["disabled","auto","enabled"] = "auto"`
  - `@dataclass class McpServer: command: str; args: list[str]`
  - `@dataclass class UserConfig: schema_version: int = 1; workspace: Path = Path("~/apd-gauntlet").expanduser(); llm: LlmConfig; decision_model: DecisionModelConfig; defaults: DefaultsConfig; mcp_servers: dict[str, McpServer]; secret_refs: dict[str, str]`
  - `def config_path() -> Path` → `Path(platformdirs.user_config_dir("apd-gauntlet")) / "config.yaml"`; `APD_GAUNTLET_CONFIG` env var overrides.
  - `def load_config(path: Path | None = None) -> UserConfig` (missing file → defaults)
  - `def save_config(cfg: UserConfig, path: Path | None = None) -> Path` (creates parents, file mode `0o600`)
  - `EXTRA_ENV_ALLOWLIST = frozenset({"AWS_PROFILE", "AWS_REGION", "CLOUD_ML_REGION", "ANTHROPIC_VERTEX_PROJECT_ID"})`

- [ ] **Step 1: Write the failing tests**

```python
def test_missing_file_gives_defaults(tmp_path):
    cfg = load_config(tmp_path / "config.yaml")
    assert cfg.decision_model.provider == "none"
    assert cfg.llm.default_model == "opus" and cfg.llm.run_budget_usd == 100.0

def test_round_trip_and_mode(tmp_path):
    p = tmp_path / "config.yaml"
    cfg = load_config(p); cfg.decision_model.provider = "cloudflare"
    save_config(cfg, p)
    assert load_config(p).decision_model.provider == "cloudflare"
    assert stat.S_IMODE(p.stat().st_mode) == 0o600

@pytest.mark.parametrize("bad", ["api_key: x", "llm: {token: x}", "decision_model: {secret: x}"])
def test_secret_shaped_keys_rejected(tmp_path, bad):
    p = tmp_path / "config.yaml"; p.write_text("schema_version: 1\n" + bad)
    with pytest.raises(ConfigError, match="not allowed"):
        load_config(p)

def test_secret_refs_must_be_op_uris(tmp_path):
    p = tmp_path / "config.yaml"; p.write_text("schema_version: 1\nsecret_refs: {openrouter: sk-abc}")
    with pytest.raises(ConfigError, match="op://"):
        load_config(p)

def test_extra_env_allowlist(tmp_path):
    p = tmp_path / "config.yaml"; p.write_text("schema_version: 1\nllm: {extra_env: {ANTHROPIC_API_KEY: x}}")
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        load_config(p)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.config`)

- [ ] **Step 3: Implement `config.py` and the schema**

Validate with jsonschema (`additionalProperties: false` at every level, `secret_refs` values `pattern: "^op://"`) before building dataclasses. Before schema validation, walk the loaded mapping and raise `ConfigError("key '<k>' is not allowed in config.yaml; store secrets with 'apd-gauntlet keys set'")` for any key matching `(?i)(^|_)(api_?key|access_?token|token|secret|password)$` — except the literal `secret_refs`. (The unanchored `(?i)(api_?key|token|secret|password)` rejects `context_tokens`; name new numeric fields `context_window`.) `workspace` is stored as written and expanded with `expanduser()` on load.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/config.py tools/apd_gauntlet/data/schemas/user-config.schema.json pyproject.toml tests/test_config.py
git commit -m "feat(config): add user config with secret-key guard"
```

### Task 2: Credentials

**Files:**

- Create: `tools/apd_gauntlet/credentials.py`
- Modify: `pyproject.toml` (extra `decide = ["httpx>=0.27,<1", "keyring>=25.7,<26"]`)
- Test: `tests/test_credentials.py`, `tests/conftest.py` (created by WS2; LA1 adds fixture `memory_keyring` that installs a dict-backed `keyring.backend.KeyringBackend`)

**Interfaces:**

- Consumes: `UserConfig.secret_refs` (Task 1)
- Produces:
  - `CredentialName = Literal["anthropic", "cloudflare", "typesafe", "openrouter"]`
  - `ENV_VARS: dict[CredentialName, str]` (names from Global Constraints)
  - `@dataclass(frozen=True) class ResolvedSecret: value: str = field(repr=False); source: Literal["env","keychain","op"]; def masked(self) -> str` → `"…" + value[-4:]`
  - `class CredentialError(Exception)`, `class NoKeychainError(CredentialError)`
  - `def keychain_available() -> bool` (False when the active backend is `keyring.backends.fail.Keyring` or priority ≤ 0)
  - `def resolve(name: CredentialName, cfg: UserConfig) -> ResolvedSecret | None`
  - `def store(name: CredentialName, value: str) -> None`
  - `def clear(name: CredentialName) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
def test_env_beats_keychain(memory_keyring, monkeypatch):
    store("openrouter", "kc-1111"); monkeypatch.setenv("OPENROUTER_API_KEY", "env-2222")
    s = resolve("openrouter", UserConfig())
    assert s.source == "env" and s.masked() == "…2222"

def test_keychain_when_no_env(memory_keyring, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False); store("typesafe", "kc-3333")
    assert resolve("typesafe", UserConfig()).source == "keychain"

def test_op_reference(monkeypatch, memory_keyring):
    calls = []
    def fake_run(args, **kw):
        calls.append(args); return subprocess.CompletedProcess(args, 0, stdout="op-4444\n", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    cfg = UserConfig(); cfg.secret_refs = {"cloudflare": "op://Vault/CF/token"}
    s = resolve("cloudflare", cfg)
    assert calls[0] == ["op", "read", "op://Vault/CF/token"] and s.source == "op" and s.value == "op-4444"

def test_repr_never_shows_value():
    assert "secret-5555" not in repr(ResolvedSecret("secret-5555", "env"))

def test_no_backend_refuses(monkeypatch):
    monkeypatch.setattr(credentials, "keychain_available", lambda: False)
    with pytest.raises(NoKeychainError, match="OPENROUTER_API_KEY"):
        store("openrouter", "x")

def test_op_failure_hides_value(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired("op", 15)))
    cfg = UserConfig(); cfg.secret_refs = {"cloudflare": "op://V/I/f"}
    with pytest.raises(CredentialError, match="op read timed out"):
        resolve("cloudflare", cfg)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_credentials.py -v`
Expected: FAIL (module missing)

- [ ] **Step 3: Implement `credentials.py`**

Order: env, keychain (`keyring.get_password("apd-gauntlet", name)`), `op read <ref>` with `timeout=15, check=True, capture_output=True, text=True`, value `.strip()`. `NoKeychainError` message: `"No OS keychain backend is available. Set {ENV_VARS[name]} in your environment instead."` Import `keyring` lazily so the base install works without the extra; a missing `keyring` module counts as no backend.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_credentials.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/credentials.py pyproject.toml tests/test_credentials.py tests/conftest.py
git commit -m "feat(credentials): resolve keys from env, keychain or op://"
```

### Task 3: Types, catalog and provider adapters

**Files:**

- Create: `tools/apd_gauntlet/decide/{__init__,errors,types,catalog,providers}.py`, `tools/apd_gauntlet/data/decision-models.json`
- Create: `tests/fixtures/decide/{cloudflare-clef,cloudflare-error,typesafe-jev,openrouter-jev}.json` — hand-authored from the documented shapes in spec §5; Task 9 replaces them with recorded responses.
- Package data: `data/decision-models.json` is already covered by `data/*.json` in `pyproject.toml`; no change.
- Test: `tests/decide/test_providers.py`, `tests/decide/test_catalog.py`

**Interfaces:**

- Produces:
  - `errors.py`: `DecisionError`; `ProviderError(DecisionError)`; `AuthRejected(ProviderError)`; `ProviderResponseError(ProviderError)`; `StateTooLarge(DecisionError)`; `TooManyQuestions(DecisionError)`; `InvalidQuestion(DecisionError)`; `BudgetExceeded(DecisionError)`
  - `types.py`: `Noul(instructions: str, criteria: dict[str,str] | None = None)`; `Choice(instructions: str, criteria: dict[str,str])`; `Score(instructions: str, criteria: list[str])`; `Question = Noul | Choice | Score`; `def to_wire(q: Question) -> dict[str, Any]`; `NoulAnswer(p: float)`; `ChoiceAnswer(choice: str, confidence: float, probabilities: dict[str, float])`; `ScoreAnswer(score: float, confidence: float, legend: dict[str, str], probabilities: dict[str, float])`; `Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer`; `Usage(input_tokens: int | None, cost_usd: float | None, cost_basis: Literal["reported","estimated","unknown"])`; `DecisionResult(provider: str, model: str, answers: dict[str, Answer], usage: Usage, latency_ms: int)`
  - `catalog.py`: `ModelInfo(provider: str, id: str, route: str, context_tokens: int | None, images: bool, usd_per_mtok_input: float | None, default: bool)`; `def get_model(provider: str, model_id: str | None) -> ModelInfo` (None → the provider default); `def models_for(provider: str) -> list[ModelInfo]`; `UNKNOWN_CONTEXT_TOKENS = 32000`
  - `providers.py`: `class Provider(Protocol): name: str; def build_request(self, info: ModelInfo, state: str | dict[str, Any] | list[Any], questions: dict[str, Question], images: list[bytes] | None) -> httpx.Request; def parse_response(self, info: ModelInfo, resp: httpx.Response, question_ids: set[str]) -> tuple[str, dict[str, Answer], Usage]`; classes `CloudflareProvider(account_id: str, token: ResolvedSecret)`, `TypeSafeProvider(api_key: ResolvedSecret)`, `OpenRouterProvider(api_key: ResolvedSecret)`

Catalog rows (`verified_on: "2026-10-14"`):

| provider | id | route | context | images | $/M input | default |
|---|---|---|---|---|---|---|
| cloudflare | clef | `@cf/cloudflare/clef` | 65536 | yes | 0.24 | yes |
| cloudflare | clef-flash | `@cf/cloudflare/clef-flash` | 24576 | yes | 0.038 | |
| cloudflare | clef-omni | `@cf/cloudflare/clef-omni` | 64000 | yes | 0.15 | |
| typesafe | jev-latest | `/v1/systemone` | 32000 | no | 0.042 | yes |
| openrouter | typesafe/jev-1.13 | `/api/v1/systemone` | 32000 | no | 0.042 | yes |
| openrouter | ~typesafe/jev-latest | `/api/v1/systemone` | 32000 | no | 0.042 | |

- [ ] **Step 1: Write the failing tests**

```python
QS = {"urgent": Noul("Is this urgent?"), "team": Choice("Route", {"a": "A", "b": "B"})}

def test_cloudflare_clef_request():
    p = CloudflareProvider("acct123", ResolvedSecret("cf-tok", "env"))
    req = p.build_request(get_model("cloudflare", "clef"), "state", QS, None)
    assert str(req.url) == "https://api.cloudflare.com/client/v4/accounts/acct123/ai/run/@cf/cloudflare/clef"
    assert req.headers["authorization"] == "Bearer cf-tok"
    body = json.loads(req.content)
    assert body["model"] == "clef" and body["state"] == "state" and body["questions"]["urgent"]["type"] == "noul"

def test_cloudflare_envelope_unwrapped():
    model, answers, usage = CloudflareProvider("a", ResolvedSecret("t", "env")).parse_response(
        get_model("cloudflare", "clef"), httpx.Response(200, json=load_fixture("cloudflare-clef")), set(QS))
    assert isinstance(answers["urgent"], NoulAnswer) and 0 <= answers["urgent"].p <= 1
    assert usage.cost_basis == "estimated"

def test_cloudflare_success_false_raises():
    with pytest.raises(ProviderResponseError, match="cloudflare"):
        CloudflareProvider("a", ResolvedSecret("t", "env")).parse_response(
            get_model("cloudflare", "clef"), httpx.Response(200, json=load_fixture("cloudflare-error")), set(QS))

def test_typesafe_request():
    req = TypeSafeProvider(ResolvedSecret("ts-key", "env")).build_request(get_model("typesafe", None), {"x": 1}, QS, None)
    assert str(req.url) == "https://api.typesafe.ai/v1/systemone"
    assert json.loads(req.content)["model"] == "jev-latest"

def test_openrouter_reported_cost():
    _, _, usage = OpenRouterProvider(ResolvedSecret("or", "env")).parse_response(
        get_model("openrouter", None), httpx.Response(200, json=load_fixture("openrouter-jev")), set(QS))
    assert usage.cost_basis == "reported" and usage.cost_usd is not None

def test_images_rejected_for_jev():
    with pytest.raises(InvalidQuestion, match="images"):
        TypeSafeProvider(ResolvedSecret("k", "env")).build_request(get_model("typesafe", None), "s", QS, [b"png"])

def test_missing_answer_id_raises():
    payload = load_fixture("typesafe-jev"); payload["answers"].pop("team")
    with pytest.raises(ProviderResponseError, match="team"):
        TypeSafeProvider(ResolvedSecret("k", "env")).parse_response(get_model("typesafe", None), httpx.Response(200, json=payload), set(QS))
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/decide -v`
Expected: FAIL (package missing)

- [ ] **Step 3: Implement types, catalog and adapters**

Images go as `data:image/<type>;base64,…` strings under `images`. Cloudflare responses: unwrap `result`; `success: false` → `ProviderResponseError` with the first `errors[].message`. OpenRouter cost from `usage.cost`. Answer parsing follows spec §5.1; any non-finite probability or a probability outside [0, 1] → `ProviderResponseError`. Parse a `noul` answer from `answers[id]["noul"]`; `score` legends and probabilities are keyed by index strings.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/decide -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/decide tools/apd_gauntlet/data/decision-models.json tests/decide tests/fixtures/decide pyproject.toml
git commit -m "feat(decide): add System One types, catalog and provider adapters"
```

### Task 4: DecisionClient

**Files:**

- Create: `tools/apd_gauntlet/decide/client.py`
- Modify: `pyproject.toml` (`pytest-asyncio>=1.0` in the `dev` extra; `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`: pytest 9.1.1 fails bare `async def` tests with "async def functions are not natively supported")
- Test: `tests/decide/test_client.py`

**Interfaces:**

- Consumes: Task 3 types, `Provider`, `ModelInfo`
- Produces:
  - `def estimate_tokens(state: str | dict[str, Any] | list[Any], questions: dict[str, Question], images: list[bytes] | None = None) -> int` (adds 1,024 per image)
  - `class DecisionClient: def __init__(self, provider: Provider, info: ModelInfo, *, timeout_s: float = 30.0, max_concurrency: int = 8, budget_usd: float = 2.0, transport: httpx.AsyncBaseTransport | None = None, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep)`
  - `async def decide(self, state, questions, images=None) -> DecisionResult`
  - properties `spent_usd: float`, `calls: int`, `input_tokens: int`
  - `async def aclose(self) -> None`; async context manager

- [ ] **Step 1: Write the failing tests**

```python
async def test_state_too_large_never_sends(client_factory):
    calls = []
    c = client_factory(lambda req: calls.append(req) or httpx.Response(200, json=ok()), model="clef-flash")
    with pytest.raises(StateTooLarge):
        await c.decide("x" * 80_000, {"q": Noul("?")})
    assert calls == []

async def test_too_many_questions(client_factory):
    c = client_factory(lambda r: httpx.Response(200, json=ok()))
    with pytest.raises(TooManyQuestions):
        await c.decide("s", {f"q{i}": Noul("?") for i in range(65)})

async def test_invalid_question_id(client_factory):
    with pytest.raises(InvalidQuestion):
        await client_factory(lambda r: httpx.Response(200, json=ok())).decide("s", {"bad id!": Noul("?")})

async def test_retry_after_honored_then_success(client_factory):
    seq = [httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(200, json=ok())]
    sleeps = []
    c = client_factory(lambda r: seq.pop(0), sleep=lambda s: sleeps.append(s) or asyncio.sleep(0))
    await c.decide("s", {"q": Noul("?")})
    assert sleeps == [2.0]

async def test_gives_up_after_three_retries(client_factory):
    c = client_factory(lambda r: httpx.Response(503), sleep=lambda s: asyncio.sleep(0))
    with pytest.raises(ProviderError, match="503"):
        await c.decide("s", {"q": Noul("?")})
    assert c.calls == 4

async def test_auth_rejected_no_retry_no_key(client_factory):
    c = client_factory(lambda r: httpx.Response(401), secret="sk-SECRET-9999")
    with pytest.raises(AuthRejected) as e:
        await c.decide("s", {"q": Noul("?")})
    assert "9999" not in str(e.value) and c.calls == 1

async def test_budget_stops_before_call(client_factory):
    c = client_factory(lambda r: httpx.Response(200, json=ok(input_tokens=1_000_000)), budget_usd=0.30)
    await c.decide("s", {"q": Noul("?")})          # $0.24 estimated for clef
    with pytest.raises(BudgetExceeded):
        await c.decide("s", {"q": Noul("?")})

async def test_concurrency_cap(client_factory):
    live = peak = 0
    async def handler(req):
        nonlocal live, peak
        live += 1; peak = max(peak, live); await asyncio.sleep(0.01); live -= 1
        return httpx.Response(200, json=ok())
    c = client_factory(handler, max_concurrency=3)
    await asyncio.gather(*(c.decide("s", {"q": Noul("?")}) for _ in range(20)))
    assert peak == 3

async def test_possibly_truncated_escalates(client_factory): ...  # reported input_tokens ≥ context − 16 → result marked possibly_truncated; the item escalates as an error
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/decide/test_client.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `client.py`**

Pre-call checks in order: question count, id pattern, images vs `info.images`, then `estimate_tokens` vs `info.context_tokens or UNKNOWN_CONTEXT_TOKENS`. Raise `InvalidQuestion` for a choice with more than 255 options or a score outside 2–10 levels. Images: ≤ 4 per call, PNG/JPEG/WebP, ≤ 4 MiB and ≤ 16 MP each, ≤ 8 MiB decoded in total, request ≤ 13 MiB, remote URLs not accepted. `estimate_tokens` adds 1,024 per image; the client refuses above `context − 1024`. A reported `input_tokens ≥ context − 16` marks the result `possibly_truncated`; the item escalates as an error. Workers AI `rejectIfBusy` rejections are retryable. Budget check before each call uses the estimate × price (skip when price unknown and the provider reports cost; then check after the call and refuse the next one). Wrap `httpx.HTTPError` in `ProviderError`. Error messages name provider, model and HTTP status only.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/decide/test_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/decide/client.py tests/decide/test_client.py pyproject.toml
git commit -m "feat(decide): add DecisionClient with preflight, retries and spend cap"
```

### Task 5: Run-config block, decision-record schema and validation

**Files:**

- Modify: `tools/apd_gauntlet/data/schemas/run-config.schema.json`, `tools/apd_gauntlet/validate.py`
- Create: `tools/apd_gauntlet/data/schemas/decision-record.schema.json`, `tests/fixtures/valid/run-config-with-decision-model.yaml`, `tests/fixtures/invalid/run-config-decision-model-with-key.yaml`, `tests/fixtures/valid/decision-record.yaml`, `tests/fixtures/invalid/decision-record-bad-flag.yaml`
- Test: `tests/test_decision_schemas.py`

**Interfaces:**

- Produces: run-config property `decision_model: {provider: enum[none, cloudflare, typesafe, openrouter], model: string}` (`additionalProperties: false`, `provider` required). Decision record shape:

```yaml
schema_version: 1
task: finding-qa
scope: 10-trustworthiness          # or "all"
provider: cloudflare
model: clef                        # as returned by the provider
schema_sha256: <64 hex>
generated_at: 2026-10-10T00:00:00Z
thresholds: {lens_drift: 0.5, unsupported: 0.3, severity_delta: 1.0}
calibrated: false
usage: {calls: 3, input_tokens: 4210, cost_usd: 0.00101, cost_basis: estimated}
items:
  - ref: conf-1a2b3c4d
    state_sha256: <64 hex>         # over the state, question-schema hash, image digests and model (Task 6)
    outcome: flag                  # pass | flag | error
    flags: [severity_disagree]     # lens_drift | unsupported | severity_disagree
    answers: {goal: {type: choice, choice: confidentiality, confidence: 0.91, probabilities: {...}}}
    error: null
```

- `decision-record.schema.json` gains a required boolean `calibrated`.
- `validate.py`: `schema_for_run_file` (the shared lookup used by `validate` and `resume-plan`) maps `40-synthesis/decisions/*.yaml` to `decision-record.schema.json`; `run_schema_pass` validates through it. (WS6 Task 1 maps `40-synthesis/escalations/*.yaml` to `decision-escalations.schema.json` through the same lookup.)

- [ ] **Step 1: Write the failing tests**

```python
def test_run_config_accepts_decision_model():
    r = CliRunner().invoke(main, ["validate-run-config", str(FIXTURES / "valid/run-config-with-decision-model.yaml")])
    assert r.exit_code == 0, r.output

def test_run_config_rejects_key_in_block():
    r = CliRunner().invoke(main, ["validate-run-config", str(FIXTURES / "invalid/run-config-decision-model-with-key.yaml")])
    assert r.exit_code == 1 and "api_key" in r.output

def test_validate_flags_bad_decision_record(tmp_path):
    run = shutil.copytree(FIXTURES / "runs/clean-run", tmp_path / "run")
    (run / "40-synthesis/decisions").mkdir(parents=True)
    shutil.copy(FIXTURES / "invalid/decision-record-bad-flag.yaml", run / "40-synthesis/decisions/finding-qa.all.yaml")
    result = CliRunner().invoke(main, ["validate", "--schema-only", "--errors-only", str(run)])
    assert result.exit_code == 1 and "finding-qa.all.yaml" in result.output
    assert schema_errors_for_file(run, "40-synthesis/decisions/finding-qa.all.yaml")

def test_validate_accepts_good_decision_record(tmp_path): ...  # same with the valid fixture → exit 0
```

`FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"`, as in `tests/test_cli_validate_run_config.py` (the constant is `FIXTURES`, not `FIX`).

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_decision_schemas.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the schema changes and the validator glob**

- [ ] **Step 4: Run the new tests and the full validator suite**

Run: `pytest tests/test_decision_schemas.py tests/test_cli.py tests/test_cli_validate_run_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas tools/apd_gauntlet/validate.py tests/fixtures tests/test_decision_schemas.py
git commit -m "feat(schemas): add run-config decision_model and decision records"
```

### Task 6: Finding-QA task, factory and `decide` command

**Files:**

- Create: `tools/apd_gauntlet/decide/{factory,records}.py`, `tools/apd_gauntlet/decide/policy.py` (`ThresholdEntry` and `load_threshold(key: str, path: Path | None = None) -> ThresholdEntry`, using exactly WS6 Task 1's signatures; WS6 runs two milestones later), `tools/apd_gauntlet/decide/tasks/__init__.py`, `tools/apd_gauntlet/decide/tasks/finding_qa.py`
- Modify: `tools/apd_gauntlet/cli.py`, `eval/calibrate.py` (registration), `tools/apd_gauntlet/data/decide/thresholds.yaml`
- Test: `tests/decide/test_finding_qa.py`, `tests/test_cli_decide.py`

**Interfaces:**

- Consumes: `load_config`, `resolve`, `DecisionClient`, providers, catalog
- Produces:
  - `factory.py`: `def run_decision_model(run_dir: Path) -> tuple[str, str | None]` (provider, model from `.apd-run.yaml`; `("none", None)` when absent); `def client_for(provider: str, model: str | None, cfg: UserConfig, *, transport: httpx.AsyncBaseTransport | None = None) -> DecisionClient` (raises `CredentialError` naming the env var when no key); `def default_transport() -> httpx.AsyncBaseTransport | None` (tests monkeypatch this)
  - `records.py`: `def schema_sha256(questions: dict[str, Question]) -> str`; `def write_record(run_dir: Path, task: str, scope: str, client: DecisionClient, model: str, questions: dict[str, Question], thresholds: dict[str, float], items: list[dict[str, Any]]) -> Path`; `def record_is_current(path: Path, refs: set[str], schema_hash: str) -> bool` (also compares each item's `state_sha256`)
  - `finding_qa.py`: `GOALS: tuple[str, ...]` (the 9 goal ids, `non_repudiation` spelled as the schema spells `apd_goal`); `GOAL_CRITERIA: dict[str, str]`; `SEVERITIES = ("informational","low","medium","high","critical")`; `SEVERITY_LEVEL = {s: i for i, s in enumerate(SEVERITIES)}` (0–4; System One's `score` is the probability-weighted 0-based level index); `def thresholds() -> dict[str, ThresholdEntry]`; per item `delta = abs(score - SEVERITY_LEVEL[severity])`; LA1 registers `ValueSpec("finding-qa", "above", lambda item, f: item.get("delta"))` under `finding-qa.severity_delta` (WS2's plan says LA1 registers it); `def build_questions() -> dict[str, Question]`; `def rubric_digest(domains: list[str], domains_dir: Path, max_bytes: int = 6000) -> str`; `def state_for(finding: dict[str, Any], rubric: str) -> dict[str, Any]`; `def flags_for(finding: dict[str, Any], answers: dict[str, Answer]) -> list[str]`; `async def run_finding_qa(run_dir: Path, client: DecisionClient, *, tier: str | None) -> Path | None`
  - `factory.py` also: `def egress_notice(run_dir: Path) -> str | None` (None when the run has no decision model); `def has_consent(run_dir: Path, provider: str, model: str) -> bool`; `def record_consent(run_dir: Path, provider: str, model: str, method: Literal["flag","prompt","run-config"]) -> None` — reads and writes only the `decision_model` subject of `consent.json`, a JSON object keyed by subject (R6): `consent["decision_model"] = {provider, model, granted_at, method}`; other subjects such as `iac_module_fetch` are preserved; `has_consent` reads only `consent.get("decision_model")`. An existing matching record is left unchanged. Plans 2 and 3 use these three functions.
  - `factory.py` also: `def run_spend(run_dir: Path, *, exclude: Path | None = None) -> float` (sum of `usage.cost_usd` over `40-synthesis/decisions/*.yaml`)
  - CLI: `apd-gauntlet decide finding-qa RUN_DIR [--tier DIR] [--yes]`

`state_for` returns `{"lens", "title", "summary", "severity", "evidence": [{"artifact","locator","excerpt"}], "detail" (first 2,000 characters), "rubric"}`. `rubric_digest` keeps, under each `## <Severity>` heading of each pack's `severity-rubric.md`, the bold lead phrase of every bullet. With no bold lead phrase, it uses the bullet's first sentence (≤ 160 characters); it folds `### <Severity>` sub-sections into their severity (the agentic-ai rubric has no bold bullets; pbm has `###` patient-harm sub-sections). Its test covers all six bundled packs. `run_finding_qa` loads the tier's `*.findings.yaml` (all tiers when `tier` is None), skips when `record_is_current`, decides all findings with `asyncio.gather`, records a per-item `outcome: error` for `StateTooLarge` or `ProviderResponseError`, and re-raises `AuthRejected` and `BudgetExceeded` after writing what it has. Each item stores `state_sha256` over the state, the question-schema hash, image digests and the model; reuse is per item and only changed items are re-decided (finding ids hash only `title|first_locator`, so after a repair the id is unchanged and a stale decision would otherwise be reused). `decide finding-qa` builds its client with `budget = budget_usd_per_run - run_spend(exclude=<own record>)` and exits 1 with `decision budget for this run is exhausted` when ≤ 0.

- [ ] **Step 1: Write the failing tests**

```python
def test_questions_shape():
    qs = build_questions()
    assert set(qs) == {"goal", "excerpt_supports_claim", "severity"}
    assert set(qs["goal"].criteria) == set(GOALS) and len(GOALS) == 9
    assert qs["severity"].criteria == list(SEVERITIES)

def test_flags():
    f = {"apd_goal": "confidentiality", "severity": "low"}
    a = {"goal": ChoiceAnswer("authenticity", .8, {"confidentiality": .2, "authenticity": .8}),
         "excerpt_supports_claim": NoulAnswer(.1), "severity": ScoreAnswer(3.2, .7, {}, {})}
    assert flags_for(f, a) == ["lens_drift", "unsupported", "severity_disagree"]

def test_state_trims_detail():
    s = state_for({"apd_goal": "integrity", "title": "t", "summary": "s", "severity": "high",
                   "detail": "d" * 5000, "evidence": []}, rubric="r")
    assert len(s["detail"]) == 2000 and "id" not in s

def test_decide_none_is_noop(cli_run_dir):
    r = CliRunner().invoke(main, ["decide", "finding-qa", str(cli_run_dir), "--tier", "10-trustworthiness"])
    assert r.exit_code == 0 and "disabled for this run" in r.output
    assert not (cli_run_dir / "40-synthesis/decisions").exists()

def test_decide_writes_record_and_leaves_findings(cli_run_dir_with_cf, mock_transport, memory_keyring, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "CANARY-7777")
    before = digest_tree(cli_run_dir_with_cf / "10-trustworthiness")
    r = CliRunner().invoke(main, ["decide", "finding-qa", str(cli_run_dir_with_cf), "--tier", "10-trustworthiness", "--yes"])
    assert r.exit_code == 0, r.output
    rec = cli_run_dir_with_cf / "40-synthesis/decisions/finding-qa.10-trustworthiness.yaml"
    assert rec.exists() and digest_tree(cli_run_dir_with_cf / "10-trustworthiness") == before
    assert "CANARY-7777" not in grep_tree(cli_run_dir_with_cf)

def test_decide_requires_consent_when_noninteractive(cli_run_dir_with_cf, mock_transport):
    r = CliRunner().invoke(main, ["decide", "finding-qa", str(cli_run_dir_with_cf)], input="")
    assert r.exit_code == 2 and "will be sent to Cloudflare" in r.output

def test_rerun_skips_current_record(cli_run_dir_with_cf, mock_transport, monkeypatch): ...  # second invoke → "up to date", transport call count unchanged

def test_oversize_finding_recorded_as_error(cli_run_dir_with_cf, mock_transport, monkeypatch):
    add_finding(cli_run_dir_with_cf, "10-trustworthiness/integrity.findings.yaml", detail="x" * 300_000, evidence_excerpt="y" * 200_000)
    CliRunner().invoke(main, ["decide", "finding-qa", str(cli_run_dir_with_cf), "--tier", "10-trustworthiness", "--yes"])
    items = yaml.safe_load(record_path(cli_run_dir_with_cf).read_text())["items"]
    assert any(i["outcome"] == "error" for i in items) and any(i["outcome"] != "error" for i in items)
def test_missing_key_names_env_var(cli_run_dir_with_cf, memory_keyring, monkeypatch): ...   # exit 1, output contains "CLOUDFLARE_API_TOKEN"

def test_consent_preserves_other_subjects(tmp_path): ...  # consent.json holding an iac_module_fetch subject keeps it after record_consent
def test_has_consent_ignores_other_subjects(tmp_path): ...  # only an iac_module_fetch subject → has_consent is False
def test_changed_summary_redecides_one_item(cli_run_dir_with_cf, mock_transport, monkeypatch): ...  # one finding's summary edited → only that item is re-decided
def test_unchanged_run_makes_no_calls(cli_run_dir_with_cf, mock_transport, monkeypatch): ...  # second invoke on an unchanged run → transport call count unchanged
```

`cli_run_dir` and `cli_run_dir_with_cf` copy `tests/fixtures/runs/clean-run`, which has no `.apd-run.yaml`, and write a complete one (`run_id`, `domains`, `framework_version`); `cli_run_dir_with_cf` adds `decision_model: {provider: cloudflare}` to it, plus `cloudflare_account_id` in a temp config via `APD_GAUNTLET_CONFIG`. A run-config `decision_model` block counts as consent with `method: run-config` when `--yes` is passed by the workflow; without `--yes`, the CLI prompts on a TTY and exits 2 otherwise.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/decide/test_finding_qa.py tests/test_cli_decide.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the factory, records, task and CLI command**

`egress_notice` returns `"Finding titles, summaries and evidence excerpts for run {run_id} will be sent to {provider_label} ({model})."` with labels `Cloudflare Workers AI`, `TypeSafe`, `OpenRouter`; the model is the catalog default when the run names none. The excerpt field is included uncut in state, so an oversize evidence list is what triggers `StateTooLarge`. The command deletes the resolved provider's env var from `os.environ` after building the client. `client_for` accepts `CLOUDFLARE_ACCOUNT_ID` from the environment.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/decide tests/test_cli_decide.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/decide tools/apd_gauntlet/cli.py eval/calibrate.py tools/apd_gauntlet/data/decide/thresholds.yaml tests/decide tests/test_cli_decide.py
git commit -m "feat(decide): add advisory finding-qa task and decide command"
```

### Task 7: `keys` command group

**Files:**

- Modify: `tools/apd_gauntlet/cli.py`
- Test: `tests/test_cli_keys.py`

**Interfaces:**

- Consumes: `credentials.*`, `factory.client_for`, `load_config`
- Produces: `apd-gauntlet keys set NAME [--account-id ID]`, `keys show`, `keys test NAME [--model M]`, `keys clear NAME`. `NAME` ∈ the four credential names. `--account-id` saves `decision_model.cloudflare_account_id` to config.

- [ ] **Step 1: Write the failing tests**

```python
def test_set_hidden_and_masked(memory_keyring):
    r = CliRunner().invoke(main, ["keys", "set", "openrouter"], input="sk-or-12345678\n")
    assert r.exit_code == 0 and "sk-or-12345678" not in r.output and "…5678" in r.output

def test_set_without_backend(monkeypatch):
    monkeypatch.setattr(credentials, "keychain_available", lambda: False)
    r = CliRunner().invoke(main, ["keys", "set", "typesafe"], input="k\n")
    assert r.exit_code == 1 and "TYPESAFE_API_KEY" in r.output

def test_show_lists_sources(memory_keyring, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-0001"); credentials.store("openrouter", "kc-0002")
    out = CliRunner().invoke(main, ["keys", "show"]).output
    assert "typesafe" in out and "env" in out and "openrouter" in out and "keychain" in out and "not set" in out

def test_test_reports_model_and_latency(memory_keyring, mock_transport, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    r = CliRunner().invoke(main, ["keys", "test", "openrouter"])
    assert r.exit_code == 0 and "jev" in r.output and "ms" in r.output

def test_test_auth_rejected(memory_keyring, monkeypatch): ...  # transport → 401; exit 1; "rejected"
def test_clear(memory_keyring): ...                             # set then clear → "removed"; second clear → "nothing stored"
```

`keys test anthropic` prints "use 'apd-gauntlet doctor --online'" and exits 0; the Claude check belongs to Plan 3.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_cli_keys.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the group**

`set` uses `click.prompt(hide_input=True, confirmation_prompt=False)`. `test` sends one `Noul("Is this text a greeting?")` on state `"hello"` and prints provider, returned model, latency in ms and cost with its basis. On a 403, `keys test cloudflare` also prints the required token permissions ("Workers AI - Read", "Workers AI - Edit").

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_cli_keys.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_cli_keys.py
git commit -m "feat(cli): add keys set/show/test/clear"
```

### Task 8: Workflow and plan-run wiring, docs

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js` (`runTier`), `tools/apd_gauntlet/plan_run.py`, `tools/apd_gauntlet/data/schemas/run-config.schema.json` (`decision_model.tasks.finding-qa`), `CHANGELOG.md`
- Create: `docs/decision-models.md`, `docs/adrs/0024-optional-decision-model-layer.md`
- Test: `tests/test_workflow_apd_gauntlet.py` (extend), `tests/test_cli_plan_run.py` (extend)

**Interfaces:**

- Consumes: the `decide` command (Task 6)
- Produces: inside `runTier`, after `await repairTierGate(phaseName, tierDir, lenses, gate);`, when `decideMode('finding-qa') !== 'off'`, one `await pyStep('decide', {phase, label: 'decide-finding-qa-' + tierDir, noRunDir: true, positional: 'finding-qa ' + runDir, cliArgs: '--tier ' + tierDir + ' --yes', alwaysRun: true, outputs: runDir + '/40-synthesis/decisions/finding-qa.' + tierDir + '.yaml'})`. The receipt is advisory: never wrapped in `isErr` or a throw. `plan_run.build_plan` adds a `CLI` row `decide finding-qa` after each tier gate under the same condition, with the tier directory as its phase.
- Finding QA's own switch: `decision_model.tasks.finding-qa` takes `off | shadow`, default `shadow` when a provider is set; `active` is rejected. `function decideMode(task)` is added here (WS6 Task 5 replaces it with its own copy, which keeps this rule; register A12.3): `'off'` when `args.decision_model` names no provider or `none`; otherwise `args.decision_model.tasks[task]`, defaulting to `'shadow'` for `finding-qa`.
- The harness of `tests/test_workflow_runner_awaits.py` sets no `decision_model`, so `EXPECTED_GREEN_LABELS` is unchanged.

- [ ] **Step 1: Write the failing tests**

```python
def test_workflow_decide_step_guarded():
    js = _text()
    assert "'decide-finding-qa-' + tierDir" in js
    assert "decideMode('finding-qa') !== 'off'" in js

def test_plan_run_includes_decide_when_enabled(tmp_path):
    plan = _plan(tmp_path, {**FULL_CFG, "decision_model": {"provider": "cloudflare"}})
    assert sum(1 for s in plan if s["ref"].startswith("decide finding-qa")) == 3
    assert {s["phase"] for s in plan if s["ref"].startswith("decide finding-qa")} == {"10-trustworthiness", "20-scalability", "30-auditability"}

def test_plan_run_omits_decide_by_default(tmp_path):
    assert not any(s["ref"].startswith("decide") for s in _plan(tmp_path, FULL_CFG))
```

Use the existing helpers `_text()` in `tests/test_workflow_apd_gauntlet.py` (not `WORKFLOW_JS`) and `_plan` in `tests/test_cli_plan_run.py` (not `plan_json`).

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/test_cli_plan_run.py -v`
Expected: FAIL on the three new tests

- [ ] **Step 3: Implement the wiring and write the docs**

`docs/decision-models.md`: providers table and keys from spec §5.2, the run-config block, `keys` usage, what finding QA sends and records, the PHI caution from spec §12. For the plugin channel it prefers keychain or `op://` storage over environment variables, which every Bash-capable agent can read. ADR-0024 records the decisions in spec §3 rows 2–5.

- [ ] **Step 4: Run the full suite and markdownlint**

Run: `pytest -q && npx markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**"`
Expected: all pass, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tools/apd_gauntlet/plan_run.py tools/apd_gauntlet/data/schemas/run-config.schema.json docs CHANGELOG.md tests
git commit -m "feat(workflow): run finding-qa after each tier when a run enables a decision model"
```

### Task 9: Record live provider fixtures (maintainer, needs keys)

**Files:**

- Create: `tools/scripts/record_decision_fixtures.py`
- Modify: `tests/fixtures/decide/*.json`, `tools/apd_gauntlet/data/decision-models.json` (`verified_on`)

**Interfaces:**

- Consumes: `client_for`, providers

- [ ] **Step 1: Run the recorder for each configured provider**

Run: `python -I tools/scripts/record_decision_fixtures.py --out tests/fixtures/decide`
Expected: one fixture per provider and model it has a key for. The script sends one `Noul`, one `Choice` and one `Score` on the state `"hello"`, then replaces account IDs, request IDs and any `x-*` header values with `REDACTED`.

- [ ] **Step 2: Reconcile the adapters with reality**

Confirm the one open item left in spec §5.2, the Cloudflare `result`/`success` envelope, and record the ratio of the estimate to the reported `input_tokens`. Adjust the adapters if the envelope differs.

- [ ] **Step 3: Run the provider tests**

Run: `pytest tests/decide -v`
Expected: PASS against the recorded fixtures

- [ ] **Step 4: Commit**

```bash
git add tools/scripts/record_decision_fixtures.py tests/fixtures/decide tools/apd_gauntlet/data/decision-models.json tools/apd_gauntlet/decide
git commit -m "test(decide): record live provider fixtures"
```

### Task 10: Self-hosted System One provider

(Consolidated plan task N5.)

Purpose: the PHI-safe path for DEC-10. Clef weights are Apache-2.0; SGLang's `lmsysorg/sglang:dev-clef` image (SGLang 0.5.22 once released) serves `POST /v1/systemone`; vLLM serves chat only.

**Files:**

- Modify: `tools/apd_gauntlet/decide/providers.py`, `decide/catalog.py`, `decide/factory.py`, `config.py`, `credentials.py`, `data/schemas/user-config.schema.json`, `data/schemas/run-config.schema.json` (provider enum), `docs/decision-models.md`
- Create: `tests/decide/test_selfhosted_provider.py`

**Interfaces:**

- Consumes (LA1): `Provider` protocol (`build_request(self, info, state, questions, images) -> httpx.Request`; `parse_response(self, info, resp, question_ids) -> tuple[str, dict[str, Answer], Usage]`), `ModelInfo`, `ResolvedSecret`, `client_for(provider, model, cfg, *, transport=None)`, `DecisionModelConfig`.
- Produces:
  - `class SystemOneProvider` with `__init__(self, base_url: str, api_key: ResolvedSecret | None, *, name: str = "selfhosted", path: str = "/v1/systemone", ca_bundle: Path | None = None)`; `TypeSafeProvider` and `OpenRouterProvider` become thin subclasses with their fixed URLs.
  - `DecisionModelConfig` gains `base_url: str | None = None`, `context_window: int | None = None`, `images: bool = False`, `ca_bundle: Path | None = None`; provider literal gains `"selfhosted"`.
  - `catalog.selfhosted_model(cfg: DecisionModelConfig) -> ModelInfo` (`provider="selfhosted"`, `id=cfg.model or "clef"`, `route=cfg.base_url`, `context_tokens=cfg.context_window`, `images=cfg.images`, `usd_per_mtok_input=None`).
  - `CredentialName` gains `"selfhosted"` with env var `APD_DECISION_API_KEY` (optional: no key means no `Authorization` header).
  - Decision records gain `endpoint` (host only, never path or query).

- [ ] **Step 1: Write the failing tests** (`httpx.MockTransport`):
  - `test_request_goes_to_base_url_systemone` — `req.url == "https://clef.internal:8443/v1/systemone"`.
  - `test_no_auth_header_without_key` / `test_bearer_with_key` — header absent / `Bearer <key>`.
  - `test_https_required_except_loopback` — `http://10.0.0.5` raises `ConfigError`; `http://127.0.0.1:30000` and `http://localhost:30000` allowed.
  - `test_userinfo_in_url_rejected` — `https://u:p@host` raises `ConfigError` whose message contains neither `u` nor `p` credentials.
  - `test_missing_context_window_is_config_error`.
  - `test_images_refused_unless_enabled` — `InvalidQuestion` (or the client's image error) when `images=False`.
  - `test_record_carries_endpoint_host_only` — record `endpoint == "clef.internal:8443"`.
  - `test_keys_test_selfhosted` — `apd-gauntlet keys test selfhosted` (LA1 Task 7) sends one `noul` question to the mock and prints the model and latency.
- [ ] **Step 2:** `pytest tests/decide/test_selfhosted_provider.py -v`. Expected: FAIL (`ImportError: SystemOneProvider`).
- [ ] **Step 3:** Implement the interfaces above; `client_for("selfhosted", model, cfg)` (where `cfg` is the `UserConfig`) builds `SystemOneProvider(cfg.decision_model.base_url, resolve("selfhosted", cfg), ca_bundle=cfg.decision_model.ca_bundle)` with `selfhosted_model(cfg.decision_model)`; the egress notice names the host; `docs/decision-models.md` gains "Self-hosting Clef" (SGLang `dev-clef`, one H200-class GPU, no vLLM). Setup flags and the `doctor --online` check for this provider land with LA3 Task 3 (register A3.4).
- [ ] **Step 4:** Tests pass; QG. Commit: `feat(decide): self-hosted System One provider`.

### Task 11: Cloudflare AI Gateway option

(Consolidated plan task N6.)

**Files:** `decide/providers.py` (`CloudflareProvider`), `config.py`, `user-config.schema.json`, `decide/errors.py`, `docs/decision-models.md`; Create `tests/decide/test_ai_gateway.py`.

**Interfaces:** `DecisionModelConfig` gains `cloudflare_gateway_id: str | None = None`, `gateway_log_payloads: bool = False`. When a gateway id is set, `CloudflareProvider.build_request` adds `cf-aig-gateway-id: <id>` and, unless `gateway_log_payloads`, `cf-aig-collect-log-payload: false`. A 400 response carrying a `cf-aig-dlp` header raises `ProviderResponseError("blocked by AI Gateway DLP")`; the item is recorded with `outcome: error`, escalated, and the payload is never written. `usage.dlp_flags: int` counts them.

- [ ] **Step 1:** Tests: `test_gateway_headers_present`, `test_payload_logging_off_by_default`, `test_dlp_block_is_item_error_without_payload`, `test_no_gateway_no_headers`.
- [ ] **Step 2:** Run; expected FAIL.
- [ ] **Step 3:** Implement. Docs state that header routing on `/ai/run` is checked live in LA1 Task 9; if it does not route, use the gateway URL form instead and record the outcome.
- [ ] **Step 4:** Tests pass; QG. Commit: `feat(decide): optional Cloudflare AI Gateway routing with DLP handling`.
- [ ] **Step 5 (OP):** One live call through a real gateway; record whether `/ai/run` honours the header.
