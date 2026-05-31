# Multi-Domain Runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let one gauntlet run examine a solution across multiple domain packs in a single pass, by replacing the run-config `domain` string with a `domains` list and merging the selected packs into one provenance-tagged `apd-domain` skill.

**Architecture:** Hard cutover of `domain` → `domains` across schema, CLI, the Python `build_domain_skill` merge engine, the JS workflow runner, every `.apd-run.yaml` fixture, agent/skill prose, docs, and tests. `build_domain_skill` becomes the deterministic merge engine (markdown calibration concatenated per-pack under provenance headers; structured `crown_jewels`/`attacker_positions`/`default_trust_boundaries` unioned, deduped, and emitted as a generated section; `metadata.packs` frontmatter) and is made internally idempotent so the workflow can always invoke it — which fixes the pre-existing stale-skill bug.

**Tech Stack:** Python 3.11+ (Click CLI, `jsonschema` Draft 2020-12, PyYAML), pytest + `click.testing.CliRunner`, a plain-JS Workflow runner pinned by a text-contract test.

**Spec:** `docs/superpowers/specs/2026-05-30-multi-domain-runs-design.md`

**Refinement vs spec §5/§8 (read before starting):** The spec attributes the *surface union* to `build-domain-skill`. Implementation reality: today `build_domain_skill.py` only concatenates the markdown `includes`; the structured `crown_jewels`/`attacker_positions`/`default_trust_boundaries` live in `domain.yaml` and are read *by the intake and attack-path agents* (from run-config or the active pack). This plan materializes the union deterministically inside `build_domain_skill` as a generated `## Domain attack-path defaults (merged across packs)` section, and re-points the intake/analyzer/discipline prose to read that section. Run-config overrides still win.

---

## Task 1: Run-config schema cutover (`domain` → `domains`)

**Files:**
- Modify: `schemas/run-config.schema.json:6,10`
- Modify: `tests/test_run_config_schema.py` (inline dicts + new tests)
- Modify: `tests/fixtures/valid/run-config.yaml`, `tests/fixtures/valid/run-config-with-taxonomies.yaml`, `tests/fixtures/valid/run-config-with-threat-model.yaml`, `tests/fixtures/valid/run-config-with-attack-path.yaml`
- Modify: `tests/fixtures/invalid/run-config-traversal-and-bad-enum.yaml`, `tests/fixtures/invalid/run-config-with-bad-methodology-hint.yaml`, `tests/fixtures/invalid/run-config-with-invalid-taxonomy.yaml`, `tests/fixtures/invalid/run-config-with-bad-max-hop.yaml`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_run_config_schema.py`:

```python
def test_run_config_requires_domains_list():
    """domains is required and must be a non-empty array."""
    data = {"run_id": "r", "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert any("domains" in str(e.path) or "domains" in e.message for e in errors)


def test_run_config_accepts_multiple_domains():
    data = {"run_id": "r", "domains": ["pbm", "api-security"], "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors == []


def test_run_config_rejects_empty_domains():
    data = {"run_id": "r", "domains": [], "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors, "empty domains must violate minItems:1"


def test_run_config_rejects_legacy_domain_key():
    """Hard cutover: the singular `domain` key is no longer a known property."""
    data = {"run_id": "r", "domain": "pbm", "framework_version": "1.1.0"}
    errors = list(Draft202012Validator(SCHEMA).iter_errors(data))
    assert errors, "legacy singular `domain` must be rejected (additionalProperties:false)"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_run_config_schema.py -k "domains or legacy_domain" -v`
Expected: FAIL (schema still has `domain`, not `domains`).

- [ ] **Step 3: Edit the schema**

In `schemas/run-config.schema.json`, change line 6 from:

```json
  "required": ["run_id", "domain", "framework_version"],
```
to:
```json
  "required": ["run_id", "domains", "framework_version"],
```

and replace line 10:

```json
    "domain":            { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
```
with:
```json
    "domains":           { "type": "array", "minItems": 1, "items": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" }, "description": "One or more domain pack names. Each is merged into the apd-domain skill. The first is the declared-order primary for deterministic output ordering." },
```

- [ ] **Step 4: Migrate the existing inline dicts and fixtures**

In `tests/test_run_config_schema.py`, replace every inline `"domain": "pbm",` with `"domains": ["pbm"],` (4 occurrences: the two `test_all_code_recon_values_accepted`/`test_code_recon_optional...` dicts, `test_run_config_rejects_max_paths_per_pair_above_cap`, and any other).

In each `tests/fixtures/valid/*.yaml` and `tests/fixtures/invalid/*.yaml` listed above, replace the line `domain: <name>` with:
```yaml
domains:
  - <name>
```
(For `valid/run-config.yaml` that is `domains:\n  - pbm`.) Leave each invalid fixture's *intended* violation untouched — only swap the domain line so the singular key does not add a second, unintended error.

- [ ] **Step 5: Run the full schema test file**

Run: `python -m pytest tests/test_run_config_schema.py -v`
Expected: PASS (all, including the migrated `test_invalid_run_config_fails`).

- [ ] **Step 6: Commit**

```bash
git add schemas/run-config.schema.json tests/test_run_config_schema.py tests/fixtures/valid tests/fixtures/invalid
git commit -m "feat(schema): cut run-config over from domain to domains list"
```

---

## Task 2: `scaffold_run` + `init-run` CLI cutover

**Files:**
- Modify: `tools/apd_gauntlet/init_run.py:27-62`
- Modify: `tools/apd_gauntlet/cli.py:154,183-195`
- Modify: `tests/test_init_run.py`, `tests/test_init_run_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_init_run.py`:

```python
def test_scaffold_run_writes_domains_list(tmp_path):
    from apd_gauntlet.init_run import scaffold_run
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "plan.md").write_text("x")
    run_dir = scaffold_run("r1", inputs, ["pbm", "api-security"], tmp_path / "runs")
    cfg = (run_dir / ".apd-run.yaml").read_text()
    assert "domains:\n  - pbm\n  - api-security\n" in cfg
    assert "domain: " not in cfg
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_init_run.py::test_scaffold_run_writes_domains_list -v`
Expected: FAIL (`scaffold_run` still takes a `domain: str`).

- [ ] **Step 3: Change `scaffold_run`**

In `tools/apd_gauntlet/init_run.py`, change the signature parameter `domain: str,` to `domains: list[str],` and replace the `config_text` assembly (lines 46-54) with:

```python
    domains_block = "domains:\n" + "".join(f"  - {d}\n" for d in domains)
    config_text = (
        f"run_id: {run_id}\n"
        f"{domains_block}"
        f"framework_version: 1.1.0\n"
        f"code_recon: auto\n"
        "# code_recon: enabled  # hard-fail if CBM not reachable\n"
        "# code_recon: disabled # skip code-recon entirely\n"
        "# cbm_project: <project-name>  # optional CBM project pointer override\n"
    )
```

- [ ] **Step 4: Change the `init-run` CLI option**

In `tools/apd_gauntlet/cli.py`, replace line 154:

```python
@click.option("--domain", default="pbm", show_default=True)
```
with:
```python
@click.option("--domain", "domains", multiple=True, default=("pbm",), show_default=True,
              help="Domain pack for the run; repeat the flag for multiple (e.g. --domain pbm --domain api-security).")
```

Change the `init_run_cmd` signature parameter `domain` to `domains`, and the `scaffold_run(...)` call's third positional `domain,` to `list(domains),`.

- [ ] **Step 5: Migrate `test_init_run_config.py`**

In `tests/test_init_run_config.py`, update any assertion expecting `domain: pbm` in the written config to expect `domains:\n  - pbm`, and any `--domain` CLI invocation remains valid (repeatable). Update any `scaffold_run(..., "pbm", ...)` call to `scaffold_run(..., ["pbm"], ...)`.

- [ ] **Step 6: Run and commit**

Run: `python -m pytest tests/test_init_run.py tests/test_init_run_config.py -v`
Expected: PASS

```bash
git add tools/apd_gauntlet/init_run.py tools/apd_gauntlet/cli.py tests/test_init_run.py tests/test_init_run_config.py
git commit -m "feat(cli): init-run writes a domains list and accepts repeatable --domain"
```

---

## Task 3: `build_domain_skill` merge engine (markdown + `metadata.packs` + idempotency)

**Files:**
- Modify: `tools/apd_gauntlet/build_domain_skill.py`
- Create: `tests/fixtures/domains/sample2/domain.yaml`, `tests/fixtures/domains/sample2/severity-rubric.md`, `tests/fixtures/domains/sample2/common-patterns/confidentiality.md`
- Modify: `tests/test_build_domain_skill.py`

- [ ] **Step 1: Create the second test pack fixture**

Create `tests/fixtures/domains/sample2/domain.yaml`:

```yaml
name: sample2
display_name: "Second Sample Test Domain"
version: 0.2.0
framework_compat: ">=1.0.0,<2.0.0"
description: "Second minimal domain pack used only in multi-domain merge tests."
includes:
  - severity-rubric.md
  - common-patterns/confidentiality.md
regulatory_anchors: []
crown_jewels:
  - pattern: shared_audit_log
    description: "Audit log shared across sample domains."
  - pattern: sample2_secret_store
    description: "Secret store specific to the sample2 domain."
attacker_positions:
  - position: external_attacker
    description: "Untrusted external attacker reaching sample2 surfaces."
```

Create `tests/fixtures/domains/sample2/severity-rubric.md`:

```markdown
# Sample2 severity rubric

- Critical: sample2 catastrophic harm clause.
```

Create `tests/fixtures/domains/sample2/common-patterns/confidentiality.md`:

```markdown
# Confidentiality patterns (sample2)

Illustrative sample2 confidentiality pattern.
```

Also add `crown_jewels` to the existing `tests/fixtures/domains/sample/domain.yaml` so dedup-by-key is exercised — append:

```yaml
crown_jewels:
  - pattern: shared_audit_log
    description: "Audit log shared across sample domains."
  - pattern: sample_phi_store
    description: "PHI store specific to the sample domain."
```

- [ ] **Step 2: Write the failing tests**

Replace the body of `tests/test_build_domain_skill.py` with:

```python
"""Tests for the build-domain-skill command and merge engine."""
from __future__ import annotations

import pathlib

import yaml
from apd_gauntlet.build_domain_skill import build_domain_skill
from apd_gauntlet.cli import main
from click.testing import CliRunner

DOMAINS = pathlib.Path("tests/fixtures/domains")


def test_single_pack_emits_packs_frontmatter(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "name: apd-domain" in text
    assert "packs:" in text
    assert "name: sample" in text
    assert "Sample severity rubric" in text
    assert "## Domain: sample — Source: `severity-rubric.md`" in text


def test_two_packs_merge_both_rubrics_labeled(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample", "sample2"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "name: sample" in text and "name: sample2" in text
    assert "## Domain: sample — Source: `severity-rubric.md`" in text
    assert "## Domain: sample2 — Source: `severity-rubric.md`" in text
    assert "Sample severity rubric" in text and "Sample2 severity rubric" in text


def test_incompatible_framework_in_any_pack_rejected(tmp_path):
    out = tmp_path / "apd-domain"
    try:
        build_domain_skill(["sample", "sample2"], DOMAINS, out, "2.0.0")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "incompatible" in str(e).lower()


def test_idempotent_no_rewrite_when_pack_set_unchanged(tmp_path):
    out = tmp_path / "apd-domain"
    p = build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    first = p.read_text()
    p2 = build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    assert p2.read_text() == first  # byte-identical: not rewritten


def test_rebuild_when_pack_set_changes(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["sample"], DOMAINS, out, "1.0.0")
    build_domain_skill(["sample", "sample2"], DOMAINS, out, "1.0.0")
    text = (out / "SKILL.md").read_text()
    assert "name: sample2" in text  # stale single-pack skill was replaced


def test_cli_accepts_multiple_domain_names(tmp_path):
    out = tmp_path / "apd-domain"
    result = CliRunner().invoke(
        main,
        ["build-domain-skill", "sample", "sample2",
         "--domains-dir", str(DOMAINS), "--out", str(out),
         "--framework-version", "1.0.0"],
    )
    assert result.exit_code == 0, result.output
    assert "name: sample2" in (out / "SKILL.md").read_text()
```

(The CLI multi-name test depends on Task 4; it will fail until then — that is expected and re-run there.)

- [ ] **Step 3: Run to verify the non-CLI tests fail**

Run: `python -m pytest tests/test_build_domain_skill.py -k "not cli" -v`
Expected: FAIL (`build_domain_skill` still takes a single name / no `packs:` frontmatter).

- [ ] **Step 4: Rewrite `build_domain_skill.py`**

Replace `tools/apd_gauntlet/build_domain_skill.py` from the `build_domain_skill` definition onward (keep the imports, `REPO`, `DOMAIN_SCHEMA`, `_parse_semver_range`, `_version_in_range` unchanged) with:

```python
def _load_pack_meta(pack_dir: pathlib.Path, domain_name: str) -> dict:
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Domain pack '{domain_name}' not found at {pack_dir}")
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    Draft202012Validator(DOMAIN_SCHEMA).validate(meta)
    return meta


def _merge_surfaces(metas: list[tuple[str, dict]]) -> dict[str, list[dict]]:
    """Union crown_jewels/attacker_positions/default_trust_boundaries across packs,
    dedup by key in declared order, accumulate contributing-pack provenance."""
    specs = [
        ("crown_jewels", "pattern"),
        ("attacker_positions", "position"),
        ("default_trust_boundaries", "boundary"),
    ]
    merged: dict[str, list[dict]] = {}
    for field, key in specs:
        seen: dict[str, dict] = {}
        order: list[str] = []
        for name, meta in metas:
            for item in meta.get(field, []) or []:
                kv = item[key]
                if kv not in seen:
                    seen[kv] = {key: kv, "description": item["description"], "domains": [name]}
                    order.append(kv)
                else:
                    entry = seen[kv]
                    if name not in entry["domains"]:
                        entry["domains"].append(name)
                    if item["description"] != entry["description"]:
                        entry["note"] = "description varies across packs; first-declared kept"
        merged[field] = [seen[k] for k in order]
    return merged


def _render_surfaces_section(merged: dict[str, list[dict]]) -> str:
    if not any(merged.values()):
        return ""
    label = {
        "crown_jewels": "Crown jewels",
        "attacker_positions": "Attacker positions",
        "default_trust_boundaries": "Default trust boundaries",
    }
    parts = [
        "\n\n## Domain attack-path defaults (merged across packs)\n\n",
        "Unioned and deduplicated from the selected packs' `domain.yaml`. Run-config "
        "`crown_jewels` / `attacker_positions` still override these. Each entry's "
        "`domains` lists the contributing pack(s).\n",
    ]
    for field in ("crown_jewels", "attacker_positions", "default_trust_boundaries"):
        items = merged[field]
        if not items:
            continue
        block = yaml.safe_dump({field: items}, sort_keys=False).rstrip()
        parts.append(f"\n### {label[field]}\n\n```yaml\n{block}\n```\n")
    return "".join(parts)


def _existing_pack_signature(out_path: pathlib.Path):
    """Return ([(name, version), ...], framework_version) from an existing skill's
    frontmatter, or None when absent/unparseable."""
    if not out_path.exists():
        return None
    text = out_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm = yaml.safe_load(text[4:end]) or {}
    meta = fm.get("metadata", {}) or {}
    packs = [(p["name"], p["version"]) for p in meta.get("packs", []) or []]
    return (packs, meta.get("framework_version"))


def build_domain_skill(
    domain_names,
    domains_dir: pathlib.Path,
    out_dir: pathlib.Path,
    framework_version: str,
) -> pathlib.Path:
    if isinstance(domain_names, str):
        domain_names = [domain_names]
    domain_names = list(domain_names)
    if not domain_names:
        raise ValueError("build_domain_skill requires at least one domain name")

    metas: list[tuple[str, dict, pathlib.Path]] = []
    for name in domain_names:
        pack_dir = domains_dir / name
        meta = _load_pack_meta(pack_dir, name)
        if not _version_in_range(framework_version, meta["framework_compat"]):
            raise ValueError(
                f"Framework {framework_version} incompatible with pack '{name}' "
                f"framework_compat: {meta['framework_compat']}"
            )
        metas.append((name, meta, pack_dir))

    out_path = out_dir / "SKILL.md"
    requested = [(n, m["version"]) for (n, m, _) in metas]
    if _existing_pack_signature(out_path) == (requested, framework_version):
        return out_path  # idempotent: already current for this pack set

    sections: list[str] = []
    for name, meta, pack_dir in metas:
        for include_glob in meta["includes"]:
            for f in sorted(pack_dir.glob(include_glob)):
                sections.append(f"\n\n## Domain: {name} — Source: `{f.relative_to(pack_dir)}`\n\n")
                sections.append(f.read_text(encoding="utf-8").rstrip())

    surfaces = _render_surfaces_section(_merge_surfaces([(n, m) for (n, m, _) in metas]))

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    packs_yaml = "".join(f"    - name: {n}\n      version: {m['version']}\n" for (n, m, _) in metas)
    frontmatter = (
        "---\n"
        "name: apd-domain\n"
        "description: Active domain pack content — severity rubric, consequential actions,"
        " common patterns. Generated from one or more domain packs at build time;"
        " do not edit by hand.\n"
        "metadata:\n"
        "  packs:\n"
        f"{packs_yaml}"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "---\n"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(frontmatter + "".join(sections) + surfaces + "\n", encoding="utf-8")
    return out_path
```

- [ ] **Step 5: Run the non-CLI tests**

Run: `python -m pytest tests/test_build_domain_skill.py -k "not cli" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/build_domain_skill.py tests/test_build_domain_skill.py tests/fixtures/domains
git commit -m "feat(domain): merge multiple packs into one provenance-tagged apd-domain skill"
```

---

## Task 4: CLI `build-domain-skill` + `validate-domain` accept multiple packs

**Files:**
- Modify: `tools/apd_gauntlet/cli.py:125-144,199-236`
- Modify: `tests/test_validate_domain.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_validate_domain.py`:

```python
def test_validate_domain_accepts_multiple_packs():
    from apd_gauntlet.cli import main
    from click.testing import CliRunner
    result = CliRunner().invoke(
        main, ["validate-domain", "sample", "sample2", "--domains-dir", "tests/fixtures/domains"]
    )
    assert result.exit_code == 0, result.output
    assert "sample" in result.output and "sample2" in result.output
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_validate_domain.py::test_validate_domain_accepts_multiple_packs -v`
Expected: FAIL (`validate-domain` takes a single `domain_name`).

- [ ] **Step 3: Make `build-domain-skill` variadic**

In `tools/apd_gauntlet/cli.py`, replace line 126 `@click.argument("domain_name")` with:

```python
@click.argument("domain_names", nargs=-1, required=True)
```

Change the `build_domain_skill_cmd` signature `domain_name` to `domain_names`, and the call to:

```python
        path = build_domain_skill(list(domain_names), domains_dir, out, framework_version)
```

- [ ] **Step 4: Make `validate-domain` variadic**

Replace line 200 `@click.argument("domain_name")` with `@click.argument("domain_names", nargs=-1, required=True)`. Change the `validate_domain_cmd` signature `domain_name` to `domain_names` and wrap the existing per-pack body in a loop:

```python
def validate_domain_cmd(domain_names, domains_dir) -> None:  # type: ignore[no-untyped-def]
    from jsonschema import Draft202012Validator

    schema_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "domain.schema.json"
    )
    schema = _stdjson.loads(schema_path.read_text(encoding="utf-8"))
    import yaml as _yaml

    for domain_name in domain_names:
        pack_dir = domains_dir / domain_name
        meta_path = pack_dir / "domain.yaml"
        if not meta_path.exists():
            click.echo(f"Error: domain pack '{domain_name}' not found at {pack_dir}", err=True)
            raise SystemExit(1)
        meta = _yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(meta))
        if errors:
            for e in errors:
                click.echo(f"Schema error in '{domain_name}': {e.message}", err=True)
            raise SystemExit(1)
        missing = [g for g in meta.get("includes", []) if not list(pack_dir.glob(g))]
        if missing:
            for m in missing:
                click.echo(f"Missing include in '{domain_name}': {m}", err=True)
            raise SystemExit(1)
        n = len(meta.get("includes", []))
        click.echo(f"Domain pack '{domain_name}' OK: schema valid, {n} include patterns all resolved.")
```

- [ ] **Step 5: Run the CLI tests (Task 3's CLI test now passes too)**

Run: `python -m pytest tests/test_build_domain_skill.py tests/test_validate_domain.py tests/test_cli.py -v`
Expected: PASS. If `tests/test_cli.py` invokes `build-domain-skill`/`validate-domain` with a single name, that still works (variadic accepts one).

- [ ] **Step 6: Commit**

```bash
git add tools/apd_gauntlet/cli.py tests/test_validate_domain.py
git commit -m "feat(cli): build-domain-skill and validate-domain accept multiple packs"
```

---

## Task 5: Workflow runner cutover + always-rebuild staleness fix

**Files:**
- Modify: `.claude/workflows/apd-gauntlet.js:129-160,188-225` (and the setup log at line 192)
- Modify: `tests/test_workflow_apd_gauntlet.py`

- [ ] **Step 1: Write the failing pins**

Add to `tests/test_workflow_apd_gauntlet.py`:

```python
def test_runner_uses_domains_list_not_singular() -> None:
    text = _text()
    assert "args.domains" in text, "runner must read args.domains"
    assert re.search(r"args\.domain(?!s)", text) is None, "runner still references singular args.domain"


def test_build_domain_skill_step_always_runs() -> None:
    """The build-domain-skill setup step must bypass the idempotent-skip guard so the
    Python command itself decides freshness (pack-set staleness fix)."""
    text = _text()
    assert "alwaysRun" in text, "build-domain-skill must be marked alwaysRun"
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_workflow_apd_gauntlet.py -k "domains_list or always_runs" -v`
Expected: FAIL.

- [ ] **Step 3: Add `alwaysRun` support to `pyStep`**

In `.claude/workflows/apd-gauntlet.js`, inside `pyStep` (around line 140), change the first element of the `prompt` array from:

```javascript
  const prompt = [
    guard(outputs, scope, flags),
```
to:
```javascript
  const prompt = [
    opts.alwaysRun
      ? 'NO IDEMPOTENT SKIP for this setup step — always perform the WORK COMMAND below (the command is itself idempotent).'
      : guard(outputs, scope, flags),
```

- [ ] **Step 4: Cut the setup phase over to `args.domains`**

Replace the setup log (line 192):

```javascript
log('apd-gauntlet runner: setup for ' + args.run_id + ' (domain=' + args.domain + ')');
```
with:
```javascript
log('apd-gauntlet runner: setup for ' + args.run_id + ' (domains=' + args.domains.join(',') + ')');
```

Replace the `build-domain-skill` step (lines 212-218):

```javascript
pyStep('build-domain-skill', {
  phase: 'setup', label: 'build-domain-skill',
  noRunDir: true, positional: args.domains.join(' '),
  cliArgs: '--framework-version ' + args.framework_version,
  outputs: '.claude/skills/apd-domain/SKILL.md',
  validateScope: runDir, alwaysRun: true,
});
```

Replace the `validate-domain` step positional (line 222) `positional: args.domain,` with `positional: args.domains.join(' '),`.

- [ ] **Step 5: Run the workflow contract test**

Run: `python -m pytest tests/test_workflow_apd_gauntlet.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tests/test_workflow_apd_gauntlet.py
git commit -m "feat(workflow): drive setup from args.domains; always rebuild domain skill"
```

---

## Task 6: Agent + skill prose cutover (severity discipline, surface sourcing)

**Files:**
- Modify: `.claude/skills/apd-evidence-discipline/SKILL.md:90-96`
- Modify: the nine lens agents `.claude/agents/apd-{confidentiality,integrity,availability,distributed,resilient,ephemeral,authenticity,non-repudiation,immutability}.md`
- Modify: `.claude/agents/apd-intake.md`, `.claude/agents/apd-attack-path-analyzer.md`, `.claude/skills/apd-attack-path-discipline/SKILL.md`
- Modify: `.claude/agents/apd-report-writer.md`

- [ ] **Step 1: Update the severity-rubric discipline**

In `.claude/skills/apd-evidence-discipline/SKILL.md`, replace the "Severity rubric (domain-loaded)" body (lines 92-96) with:

```markdown
The severity rubrics are domain-specific and live in the active domain pack(s) at
`domains/<active>/severity-rubric.md`. They are bundled — one labeled `## Domain:
<pack> — Source: severity-rubric.md` section per selected pack — into the
`apd-domain` skill at run time by `apd-gauntlet build-domain-skill`.

You MUST cite the matching rubric clause in the finding's `detail`, naming the
**pack** it came from ("…high severity under the *api-security* rubric clause
*X*…"). When a single harm matches clauses in more than one selected pack at
different severities, take the **maximum** (the same "do not average across
impacts" rule, applied across packs) and cite the governing pack's clause. The
synthesizer relies on the cited pack+clause to reconcile severity disagreements.

If a harm matches **no** clause in **any** selected pack, record it as a
domain-improvement opportunity candidate (note it in `detail`); do not invent a
clause. If **zero** packs are loaded for a run, agents emit a single
high-severity finding "no severity rubric in scope" and halt — there is no
fallback default.
```

- [ ] **Step 2: Update the nine lens agents' required-reading line**

In each of the nine `.claude/agents/apd-<lens>.md` files, replace the string:

```
active domain's severity rubric, consequential actions, and common patterns
```
with:
```
active domain(s)' severity rubrics, consequential actions, and common patterns
```

Locate them with: `grep -rln "active domain's severity rubric" .claude/agents`. Also replace any self-check line reading `clause of the impact-to-PBM rubric` with `clause of the active domain(s)' severity rubric(s), naming the pack` (find with `grep -rln "impact-to-PBM rubric" .claude/agents`).

- [ ] **Step 3: Re-point intake + attack-path surface sourcing to the merged skill section**

In `.claude/agents/apd-intake.md`, replace the activation clause (the "OR the active domain pack declares any `crown_jewels`" wording near line 73) with:

```
OR the `## Domain attack-path defaults (merged across packs)` section of the
`.claude/skills/apd-domain/SKILL.md` skill declares any `crown_jewels`
```

In `.claude/agents/apd-attack-path-analyzer.md`, replace the two activation/input references to "the active domain pack" (lines ~30 and ~57) with "the `apd-domain` skill's merged `Domain attack-path defaults` (the union across all selected packs)". Run-config still wins on conflict — keep that sentence.

In `.claude/skills/apd-attack-path-discipline/SKILL.md`, replace the never-invent source bullet `A domain-pack `crown_jewels[]` or `attacker_positions[]` declaration` with:

```
- A `crown_jewels[]` / `attacker_positions[]` entry in the `apd-domain` skill's
  merged `Domain attack-path defaults` section (contributed by any selected pack)
```

- [ ] **Step 3b: Name the examined domains in the report (spec §9)**

In `.claude/agents/apd-report-writer.md`, add an instruction to the exec-summary
guidance: the opening paragraph must name the domain pack(s) the run examined,
read from the run's `.apd-run.yaml` `domains` list (e.g. "Reviewed across the PBM
and API-security domains."). This is free-text prose — no `report-data` schema
change. If a report-writer content test pins the old single-domain phrasing,
update it to accept the multi-domain wording.

- [ ] **Step 4: Run the agent/skill lint + contract tests**

Run: `python -m pytest tests/test_lint_agents.py tests/test_lint_agent_apd_attack_path_analyzer.py tests/test_skill_apd_attack_path_discipline.py tests/test_intake_asset_inventory_contract.py -v`
Expected: PASS. If any test pins an old string verbatim, update that test's expected string to the new wording (these are content-contract tests; the new wording is the intended contract).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills .claude/agents tests
git commit -m "docs(agents): cut severity + attack-path sourcing prose over to multi-domain"
```

---

## Task 7: Migrate run + example fixtures; regression

**Files:**
- Modify: `runs/apd-20260527-crapi-owasp-api-top10/.apd-run.yaml`, `runs/apd-20260527-authentik-identity-provider/.apd-run.yaml`, `runs/apd-20260527-caldera-adversary-emulation/.apd-run.yaml`
- Modify: `examples/apd-20260601-claim-event-bus/.apd-run.yaml`, `examples/apd-20260601-claim-event-bus/expected/.apd-run.yaml`
- Modify: `tests/fixtures/attack_path/minimal-run/.apd-run.yaml`

- [ ] **Step 1: Find every remaining singular `domain:` run-config**

Run: `grep -rln "^domain:" runs examples tests/fixtures`
Expected: the six files above (plus any missed earlier). 

- [ ] **Step 2: Migrate each**

In each file, replace the single line `domain: <name>` with:
```yaml
domains:
  - <name>
```
Leave `crown_jewels:` / `attacker_positions:` blocks untouched.

- [ ] **Step 3: Run the fixture-driven regressions**

Run: `python -m pytest tests/test_examples.py tests/test_validate_legacy_runs.py tests/test_cli_analyze_attack_paths.py tests/test_attack_path_build.py -v`
Expected: PASS. If `tests/test_validate_legacy_runs.py` asserts a run validates and it referenced the old key, the migration above fixes it; if it pins the literal `domain:` key, update the assertion to `domains:`.

- [ ] **Step 4: Commit**

```bash
git add runs examples tests/fixtures/attack_path
git commit -m "chore(fixtures): migrate run-configs from domain to domains"
```

---

## Task 8: Docs cutover + full-suite green

**Files:**
- Modify: `docs/running-the-gauntlet.md`, `docs/architecture.md`, `docs/adapting-to-other-domains.md`, `README.md` (and any other doc showing a run-config)
- Modify: `tests/test_docs_v14.py`, `tests/test_doc_attack_path_analysis.py` if they pin doc strings

- [ ] **Step 1: Enumerate doc references**

Run: `grep -rln "^domain:\|`domain`\|domain: pbm\|domain: <" docs README.md`
Expected: a handful of files.

- [ ] **Step 2: Update each reference**

Replace run-config examples that show `domain: <name>` with the `domains:` list form, and update prose that says "the run declares a single `domain`" to "the run declares one or more `domains`". (The full domain-pack authoring rewrite is a later effort; here only correct the now-wrong `domain` references.)

- [ ] **Step 3: Run the doc tests**

Run: `python -m pytest tests/test_docs_v14.py tests/test_doc_attack_path_analysis.py -v`
Expected: PASS (update any pinned literal `domain:` expectation to `domains:`).

- [ ] **Step 4: Full suite**

Run: `python -m pytest -q`
Expected: PASS (the whole suite green — this is the cutover's acceptance gate).

- [ ] **Step 5: Commit**

```bash
git add docs README.md tests
git commit -m "docs: cut run-config references over to the domains list"
```

---

## Task 9: Blended-run integration test

**Files:**
- Create: `tests/test_multi_domain_integration.py`

- [ ] **Step 1: Write the integration test**

```python
"""End-to-end-ish check that two real packs blend into one skill with both
rubrics labeled and a merged, deduped attack-path defaults section."""
from __future__ import annotations

import pathlib

from apd_gauntlet.build_domain_skill import build_domain_skill

DOMAINS = pathlib.Path("domains")


def test_pbm_plus_api_security_blend(tmp_path):
    out = tmp_path / "apd-domain"
    build_domain_skill(["pbm", "api-security"], DOMAINS, out, "1.5.0")
    text = (out / "SKILL.md").read_text()
    # both packs present in frontmatter
    assert "name: pbm" in text and "name: api-security" in text
    # both severity rubrics labeled by pack
    assert "## Domain: pbm — Source: `severity-rubric.md`" in text
    assert "## Domain: api-security — Source: `severity-rubric.md`" in text
    # merged attack-path defaults section exists with provenance
    assert "## Domain attack-path defaults (merged across packs)" in text
    assert "domains:" in text  # per-entry provenance list
    # audit_log_store is declared by both packs -> deduped to a single entry
    assert text.count("pattern: audit_log_store") == 1
```

- [ ] **Step 2: Run it**

Run: `python -m pytest tests/test_multi_domain_integration.py -v`
Expected: PASS. (If `pbm` and `api-security` use a different shared crown-jewel name than `audit_log_store`, adjust the dedup assertion to a name both declare — confirm with `grep -A2 crown_jewels domains/pbm/domain.yaml domains/api-security/domain.yaml`.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_multi_domain_integration.py
git commit -m "test: blended pbm+api-security run merges into one provenance-tagged skill"
```

---

## Self-review notes (for the implementer)

- **Spec coverage:** §2 run-config → Task 1; §3 merge → Tasks 3–4; §5 build-domain-skill → Tasks 3–4; §6 staleness → Task 5 (Python idempotency + `alwaysRun`); §7 severity → Task 6; §8 attack-path surface sourcing → Task 3 (union) + Task 6 (intake/analyzer prose); §9 validation → Task 4, report "domains examined" framing → Task 6 Step 3b; §10 cutover surface → Tasks 1,2,5,6,7,8; §11 behavioral back-compat → regression in Tasks 7–8; §12 testing → every task + Task 9.
- **Verified during planning:** the `analyze-attack-paths` Python sources crown jewels from the intake-built `asset-inventory.yaml`, NOT from `domain.yaml`, so it needs no cutover (the union reaches it via intake).
- **Deferred (not in this plan, per spec §13):** Subsystem B capture mechanism, a structured `source_domains` field, web-app/agentic pack authoring.
- **Known follow-ups surfaced during planning:** combined-skill size and surface-name dedup collisions (spec §14) are monitored, not solved here.
- **Ordering matters:** Task 3 (engine) before Task 4 (CLI) before Task 5 (workflow), because each depends on the previous signature. Tasks 6–8 are prose/fixtures and can interleave once the engine lands.
