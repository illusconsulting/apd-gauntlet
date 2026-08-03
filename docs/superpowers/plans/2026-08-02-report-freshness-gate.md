# Report-Freshness Gate Hardening (PR B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the report-template freshness gate's Python hash agree with the Node builder at every depth, prove that agreement with a real Node parity test, and add a rebuild-and-diff CI job so a stale or hand-edited bundle cannot ship.

**Architecture:** `tools/check_report_template_freshness.py` recomputes a sha256 over `report-template/` and compares it to the committed `.source-hash` that `report-template/.build/build.mjs` wrote. Two defects: the Python exclusion rule only skips dotfiles/`node_modules` at the top level while Node's `walk()` skips them at every depth (a nested dotfile turns the gate falsely red in a way a rebuild cannot fix), and nothing ever rebuilds the bundle (a hand-edited `app.js` beside a correct marker passes). Fix: align the Python rule, extract Node's walk into `source-hash.mjs` so a pytest can execute the real Node rule against a fixture, and add a CI job that rebuilds and byte-diffs — itself guarded by a source-grep test.

**Tech Stack:** Python 3.10+ (stdlib `hashlib`, `pathlib`), pytest, Node 20+ / esbuild 0.28.1 (direct-pinned; full transitive closure locked by the lockfile Task 2 commits), GitHub Actions.

**Spec:** [docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md](../specs/2026-07-14-guardrail-hardening-post-pr8-design.md) — §"PR B" and §"Amendments (2026-08-02)".

**Supersedes:** [2026-07-14-report-freshness-gate.md](2026-07-14-report-freshness-gate.md) (amended draft; all content folded in here).

**Base:** `illusconsulting/apd-gauntlet` `main` @ `27270d5`. This checkout is at that commit; every file/line anchor below was re-verified against it on 2026-08-02.

## Global Constraints

- `report-template/.build/build.mjs` is the source of truth for hash semantics. The ONLY permitted `build.mjs` edit is Task 2's extraction of its inline `walk` into `report-template/.build/source-hash.mjs` (imported back by `build.mjs`); semantics must be unchanged, proven by the emitted `.source-hash` being identical after a rebuild (`.build/` is hash-excluded at every depth, so the new file cannot perturb the hash).
- Exclusion rule to mirror (`build.mjs` line 54): skip any entry whose basename is `node_modules` or starts with `.`, at EVERY depth.
- `pytest` must pass with NO Node installed; Node-dependent tests skip with a clear reason. The `bundle-rebuild-diff` CI job provisions a pinned Node and runs the freshness test module, so the parity test is GUARANTEED to execute every CI run (the python-tests matrix runs it only incidentally, via whatever Node the runner image happens to ship).
- All four gates clean before push: `pytest --cov` (`fail_under = 85` on `tools/apd_gauntlet/`, set in `pyproject.toml:78`), `ruff check tools/ tests/`, `mypy tools/`, and the markdownlint glob (exact command in Task 4).
- Pin GitHub Actions by commit SHA: `actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` (v7.0.0), `actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405` (v6.2.0), `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020` (v7.0.0 — lightweight tag, so that IS the commit).
- No lockfile is tracked at the base commit — `report-template/.build/.gitignore` ignores `package-lock.json`, so `tools/build_report_template.py:26-30` falls back to `npm install` (floating transitives) on fresh checkouts. Task 2 un-ignores and commits the lockfile so the `npm ci` branch runs everywhere; the byte-exact CI gate (Task 4) MUST NOT land before Task 2. Byte-reproducibility was verified locally 2026-08-02 against an already-populated `node_modules`; Task 2 re-proves it from a clean `npm ci` install, and Task 5 watches the first CI run.
- Branch: `fix/report-freshness-gate` off `main`. Commits use `-s` (DCO).

---

### Task 1: Align the Python dotfile exclusion with the Node walk

**Files:**
- Modify: `tools/check_report_template_freshness.py:24-28`
- Test: `tests/unit/report/test_tier3_bundle_freshness.py` (append)

**Interfaces:**
- Consumes: `compute_source_hash()` and module attribute `SRC` from the freshness tool (both exist); the test module's existing `_load_freshness_module()` helper (line 11) and `REPO` constant (line 8).
- Produces: no new symbols — `compute_source_hash()` behavior changes so nested dotfiles / `node_modules` / `.build` no longer affect the hash at any depth.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/report/test_tier3_bundle_freshness.py`:

```python
def test_compute_source_hash_excludes_nested_dotfiles_and_node_modules(monkeypatch, tmp_path):
    """Dotfiles / node_modules / .build are excluded at EVERY depth, matching
    report-template/.build/build.mjs walk() (line 54, which skips them during
    recursive descent). Regression for the Python/Node divergence that only
    excluded at the top level (rel.parts[0])."""
    mod = _load_freshness_module()
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "app.jsx").write_text("A", encoding="utf-8")
    (src / "sub" / "child.jsx").write_text("B", encoding="utf-8")
    monkeypatch.setattr(mod, "SRC", src)
    baseline = mod.compute_source_hash()
    # Entries build.mjs excludes at nested depth (parts[0] == "sub", not excluded
    # by the old top-level-only rule):
    (src / "sub" / ".gitkeep").write_text("x", encoding="utf-8")
    (src / "sub" / "node_modules").mkdir()
    (src / "sub" / "node_modules" / "pkg.js").write_text("y", encoding="utf-8")
    (src / "sub" / ".build").mkdir()
    (src / "sub" / ".build" / "out.js").write_text("z", encoding="utf-8")
    with_excluded = mod.compute_source_hash()
    assert with_excluded == baseline, (
        "nested dotfiles / node_modules / .build must not affect the hash "
        "(they don't in build.mjs)"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py::test_compute_source_hash_excludes_nested_dotfiles_and_node_modules -v`
Expected: FAIL — `with_excluded != baseline` (the nested `.gitkeep` and `node_modules/pkg.js` are currently hashed).

- [ ] **Step 3: Apply the fix** — in `tools/check_report_template_freshness.py`, replace lines 24–28 (the `rel = ...` assignment plus the two `if rel.parts ...` blocks) with:

```python
        rel = entry.relative_to(SRC)
        # Mirror report-template/.build/build.mjs walk() (line 54): skip any
        # entry whose basename is "node_modules" or starts with "." — at EVERY
        # depth, not just the top level. The old rel.parts[0]-only check diverged
        # from Node on nested dotfiles (e.g. sub/.gitkeep), turning the gate
        # falsely red on a correctly-built bundle.
        if any(part == "node_modules" or part.startswith(".") for part in rel.parts):
            continue
```

- [ ] **Step 4: Run the module's tests to verify they pass**

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py -v`
Expected: PASS — 6 tests: the new one plus the five existing (`test_compute_source_hash_returns_64char_hex`, `_stable_across_calls`, `_includes_relative_path`, `_includes_nested_path`, `test_shipped_bundle_source_hash_matches`).

- [ ] **Step 5: Lint + commit**

```bash
ruff check tools/ tests/
mypy tools/
git add tools/check_report_template_freshness.py tests/unit/report/test_tier3_bundle_freshness.py
git commit -s -m "fix: exclude nested dotfiles/node_modules in freshness hash to match build.mjs"
```

---

### Task 2: Commit the build lockfile so `npm ci` is real

**Files:**
- Modify: `report-template/.build/.gitignore` (drop the `package-lock.json` line)
- Create: `report-template/.build/package-lock.json` (generated by npm, then committed)

**Interfaces:**
- Consumes: `report-template/.build/package.json` (six exact-pinned direct devDependencies).
- Produces: a tracked `package-lock.json` pinning the FULL transitive closure, which flips `tools/build_report_template.py:26-30` onto its `npm ci` branch on fresh checkouts. Task 4's byte-exact CI gate depends on this.

> **Why:** the build helper runs `npm ci` only `if (BUILD_DIR / "package-lock.json").exists()` — and `.gitignore` currently guarantees it never does on a fresh checkout, so CI would `npm install` with floating transitives (`cytoscape-dagre → dagre ^0.8.5`, `cytoscape-fcose → cose-base/layout-base`, `react → loose-envify`, …) that esbuild bundles straight into `app.js`. A transitive release could then flip Task 4's byte-identity diff red in a way no rebuild of the committed pins fixes. (Found by the 2026-08-02 adversarial plan review; see spec Amendments item 6.)

- [ ] **Step 1: Un-ignore the lockfile** — edit `report-template/.build/.gitignore` from:

```text
node_modules/
package-lock.json
```

to:

```text
node_modules/
```

- [ ] **Step 2: Generate the lockfile from the pinned package.json**

```bash
rm -rf report-template/.build/node_modules
(cd report-template/.build && npm install)
git status --porcelain report-template/.build/package-lock.json
```

Expected: the last command prints `?? report-template/.build/package-lock.json` (new, now trackable).

- [ ] **Step 3: Prove a clean `npm ci` install reproduces the committed bundle (GATE)**

```bash
rm -rf report-template/.build/node_modules
python tools/build_report_template.py
git status --porcelain tools/apd_gauntlet/data/report-template/
```

Expected: the build log shows `npm ci` output (the lockfile now exists, so the helper takes that branch), and the final status is EMPTY — today's freshly-resolved transitive closure rebuilds the committed bundle byte-identically.
If the bundle-dir status is NON-empty: today's transitive resolutions differ from whatever built the committed bundle. That is exactly the drift this task exists to stop — refresh once: inspect the diff, re-run `python tools/build_report_template.py`, and include the refreshed bundle files in Step 4's commit (one atomic "pin + refresh" commit). Do not proceed to Task 4 until this gate passes from a clean `node_modules`.

- [ ] **Step 4: Commit**

```bash
git add report-template/.build/.gitignore report-template/.build/package-lock.json
git add tools/apd_gauntlet/data/report-template/  # only if Step 3's refresh fallback fired
git commit -s -m "build: commit the report-template lockfile so npm ci pins the full closure"
```

---

### Task 3: Extract the Node walk and add the Python↔Node parity test

**Files:**
- Create: `report-template/.build/source-hash.mjs`
- Modify: `report-template/.build/build.mjs` (import the extracted walk; delete the inline copy at lines 50–66; trim now-unused imports)
- Test: `tests/unit/report/test_tier3_bundle_freshness.py` (append; extend the module's import block with `shutil`, `subprocess`, `pytest`)

**Interfaces:**
- Consumes: `_load_freshness_module()` and `REPO` from the test module; Task 1's every-depth exclusion (already merged).
- Produces: `computeSourceHash(rootDir)` (exported from `source-hash.mjs`) plus a CLI form — `node source-hash.mjs <dir>` prints the hex digest; pytest `test_source_hash_parity_with_node_walk`.

> **Why the extraction:** the spec's parity test must execute the REAL Node rule. Without it the test would hand-mirror the walk a third time — another copy of a possibly-wrong thing, the exact anti-pattern this design exists to kill. `.build/` is excluded from the hash at every depth, so the new file cannot change the emitted `.source-hash`; Step 5 proves it.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/report/test_tier3_bundle_freshness.py`, and add `import shutil`, `import subprocess`, `import pytest` to the module's import block (which currently holds only `importlib.util` and `pathlib`):

```python
def test_source_hash_parity_with_node_walk(monkeypatch, tmp_path):
    """Python compute_source_hash() and the Node walk (source-hash.mjs — the
    same code build.mjs runs) must agree byte-for-byte on one tree, including
    the two divergence-prone shapes: a nested dotfile, and a directory/file
    name-collision pair ("screens" dir vs "screens.css" file) that pins
    ordering agreement (Python's parts-tuple sort vs Node's per-directory
    sorted DFS). Skipped without node; the bundle-rebuild-diff CI job runs
    this module with Node present, so the skip cannot go permanently
    unnoticed."""
    if shutil.which("node") is None:
        pytest.skip("node unavailable; exercised in the bundle-rebuild-diff CI job")
    mod = _load_freshness_module()
    src = tmp_path / "src"
    (src / "screens").mkdir(parents=True)
    (src / "screens" / "A.jsx").write_text("A", encoding="utf-8")
    (src / "screens.css").write_text("C", encoding="utf-8")
    (src / "sub").mkdir()
    (src / "sub" / "child.jsx").write_text("B", encoding="utf-8")
    (src / "sub" / ".gitkeep").write_text("x", encoding="utf-8")
    monkeypatch.setattr(mod, "SRC", src)
    script = REPO / "report-template" / ".build" / "source-hash.mjs"
    proc = subprocess.run(
        ["node", str(script), str(src)], capture_output=True, text=True, check=True
    )
    assert proc.stdout.strip() == mod.compute_source_hash()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py::test_source_hash_parity_with_node_walk -v`
Expected: FAIL — `subprocess.CalledProcessError` (`source-hash.mjs` does not exist yet). Run this on a machine with Node; on a Node-less machine it skips, which does NOT satisfy the TDD gate.

- [ ] **Step 3: Create `report-template/.build/source-hash.mjs`**

```js
// report-template/.build/source-hash.mjs
// The ONE Node-side definition of the source-hash walk. build.mjs imports it;
// the pytest parity test runs it via `node source-hash.mjs <dir>`. Python's
// tools/check_report_template_freshness.py mirrors these semantics — the
// parity test is what keeps the two honest.
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

export function computeSourceHash(rootDir) {
  const hash = createHash("sha256");
  function walk(d, prefix = "") {
    for (const e of readdirSync(d).sort()) {
      if (e === ".build" || e === "node_modules" || e.startsWith(".")) continue;
      const p = join(d, e);
      const rel = prefix ? `${prefix}/${e}` : e;
      if (statSync(p).isDirectory()) walk(p, rel);
      else {
        hash.update(rel);
        hash.update(Buffer.from([0])); // NUL separator matches Python
        hash.update(readFileSync(p));
      }
    }
  }
  walk(rootDir);
  return hash.digest("hex");
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.stdout.write(computeSourceHash(process.argv[2]) + "\n");
}
```

- [ ] **Step 4: Rewire `build.mjs`** — three sub-edits:

1. Add the import below the existing imports at the top:

```js
import { computeSourceHash } from "./source-hash.mjs";
```

2. Replace the step-4 block (lines 50–66: the `// 4. Source hash ...` comment, `const hash = createHash("sha256");`, the inline `function walk(...)`, `walk(TEMPLATE_DIR);`, and the `.source-hash` `writeFileSync`) with:

```js
// 4. Source hash of report-template/ JSX + CSS sources (rule lives in source-hash.mjs).
writeFileSync(join(OUT_DIR, ".source-hash"), computeSourceHash(TEMPLATE_DIR));
```

3. Trim now-unused imports: delete `import { createHash } from "node:crypto";` (line 5) and remove `statSync, readdirSync` from the `node:fs` import (line 3) — after the extraction nothing else in `build.mjs` uses them. The `node:fs` line becomes:

```js
import { mkdirSync, copyFileSync, writeFileSync, readFileSync } from "node:fs";
```

- [ ] **Step 5: Prove the extraction changed nothing (GATE)**

Run:

```bash
python tools/build_report_template.py
git status --porcelain tools/apd_gauntlet/data/report-template/
```

Expected: empty status output — identical `.source-hash` and bundle. (The rebuild takes the `npm ci` branch via Task 2's committed lockfile.) Non-empty means the extraction altered hash semantics: STOP and fix before proceeding.

- [ ] **Step 6: Run the module's tests**

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py -v`
Expected: PASS — 7 tests: the parity test plus all six from Task 1.

- [ ] **Step 7: Lint + commit**

```bash
ruff check tools/ tests/
git add report-template/.build/source-hash.mjs report-template/.build/build.mjs tests/unit/report/test_tier3_bundle_freshness.py
git commit -s -m "test: prove Python/Node source-hash parity via an extracted source-hash.mjs"
```

---

### Task 4: Add the rebuild-and-diff CI job with a source-grep guard

**Files:**
- Modify: `.github/workflows/python-tests.yml` (append a new `bundle-rebuild-diff` job under `jobs:`)
- Test: `tests/unit/report/test_tier3_bundle_freshness.py` (append)

**Interfaces:**
- Consumes: `tools/build_report_template.py` (now takes its `npm ci` branch via Task 2's committed lockfile, then runs `node build.mjs`; writes the bundle under `tools/apd_gauntlet/data/report-template/`).
- Produces: CI job `bundle-rebuild-diff`; pytest `test_ci_has_bundle_rebuild_diff_job` (source-grep guard so the job cannot be silently dropped or renamed).

- [ ] **Step 1: Verify local byte-reproducibility (GATE — do this first)**

Run:

```bash
python tools/build_report_template.py
git status --porcelain tools/apd_gauntlet/data/report-template/
```

Expected: empty output (a fresh build reproduces the committed bundle exactly). Verified 2026-08-02 on macOS/node v26 — re-run here regardless, since the gate also covers the toolchain you execute on.
If NON-empty: STOP. The committed bundle is either stale or the build is not byte-reproducible on this toolchain. Do not add a byte-exact CI gate. Instead: (a) if stale, run the build, commit the refreshed bundle as its own step, then retry; (b) if non-reproducible across toolchains, narrow this task to diffing only `.source-hash` + a content hash of `app.js`, and record the non-reproducibility as a follow-up note in the PR description. Re-run this gate before proceeding.

- [ ] **Step 2: Prove the diff catches a stale bundle (manual non-vacuity)**

Run:

```bash
printf '/*x*/' >> tools/apd_gauntlet/data/report-template/app.js
git diff --exit-code -- tools/apd_gauntlet/data/report-template/ ; echo "exit=$?"
git checkout -- tools/apd_gauntlet/data/report-template/app.js
```

Expected: `exit=1` (the diff detects the tampered `app.js`), then the checkout restores it. This is the same assertion the CI job makes, so a stale/hand-edited bundle now fails CI.

- [ ] **Step 3: Write the failing source-grep guard** — append to `tests/unit/report/test_tier3_bundle_freshness.py`:

```python
def test_ci_has_bundle_rebuild_diff_job():
    """The rebuild-and-diff CI job is the only guard that catches a stale or
    hand-edited committed bundle (the .source-hash marker cannot). Source-grep
    guard so the job is not silently dropped or renamed."""
    wf = (REPO / ".github" / "workflows" / "python-tests.yml").read_text(encoding="utf-8")
    assert "bundle-rebuild-diff:" in wf
    assert "git diff --exit-code -- tools/apd_gauntlet/data/report-template/" in wf
```

Run: `pytest tests/unit/report/test_tier3_bundle_freshness.py::test_ci_has_bundle_rebuild_diff_job -v`
Expected: FAIL — the job does not exist in the workflow yet.

- [ ] **Step 4: Add the CI job** — append to `.github/workflows/python-tests.yml` under `jobs:`:

```yaml
  bundle-rebuild-diff:
    # Defense-in-depth for the freshness gate: check_report_template_freshness.py
    # only proves the .source-hash marker matches source; it never rebuilds the
    # bundle. This job rebuilds via build.mjs and fails if the committed bundle
    # (app.js included) is not byte-identical to a fresh build. It also runs the
    # freshness test module with an explicitly provisioned, pinned Node, so the
    # Node-parity test is guaranteed to execute every CI run (the python-tests
    # matrix only runs it incidentally, via whatever Node the runner image ships).
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0  # v7.0.0
      - uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with: { python-version: "3.12" }
      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020  # v7.0.0
        with: { node-version: "20" }
      - run: python tools/build_report_template.py
      - name: Assert committed bundle matches a fresh build
        run: git diff --exit-code -- tools/apd_gauntlet/data/report-template/
      - run: pip install -e ".[dev]"
      - name: Freshness tests with Node present (parity test executes here)
        run: pytest tests/unit/report/test_tier3_bundle_freshness.py -v
```

- [ ] **Step 5: Validate the workflow YAML and the guard**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/python-tests.yml')); print('yaml ok')"`
Expected: `yaml ok`

Then: `pytest tests/unit/report/test_tier3_bundle_freshness.py::test_ci_has_bundle_rebuild_diff_job -v`
Expected: PASS — the Step 3 guard goes green now that the job exists.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/python-tests.yml tests/unit/report/test_tier3_bundle_freshness.py
git commit -s -m "ci: rebuild the report bundle and assert it is byte-identical to source"
```

---

### Task 5: PR wrap-up

**Files:** commit the design docs to the branch; no code changes.

- [ ] **Step 1: Commit the spec and this plan to the branch**

```bash
git add docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md docs/superpowers/plans/2026-08-02-report-freshness-gate.md
git commit -s -m "docs: add the guardrail-hardening spec and the PR B implementation plan"
```

(The spec lints clean — verified 2026-08-02, 0 markdownlint issues — and `docs/superpowers/plans/**` is excluded from the lint glob. PR A commits the identical spec file on its own branch; identical-content adds merge without conflict. The superseded 2026-07-14 drafts stay uncommitted — commit or discard at the maintainer's discretion.)

- [ ] **Step 2: Run all four gates**

```bash
pytest --cov --cov-report=term-missing
ruff check tools/ tests/
mypy tools/
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "tools/apd_gauntlet/data/domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
```

Expected: all clean (coverage `fail_under = 85` enforced by `pyproject.toml`).

- [ ] **Step 3: Push and open the PR**

```bash
git push -u origin fix/report-freshness-gate
gh pr create --repo illusconsulting/apd-gauntlet --base main \
  --title "Fix report-freshness gate: Python/Node hash divergence + parity test + rebuild-diff" \
  --body "See docs/superpowers/specs/2026-07-14-guardrail-hardening-post-pr8-design.md (PR B + Amendments)."
```

- [ ] **Step 4: Watch the first `bundle-rebuild-diff` run on the CI toolchain (GATE)**

```bash
gh pr checks --watch
```

Expected: `bundle-rebuild-diff` green. This is the spec-promised re-check on the CI toolchain (ubuntu-latest / node 20) — no local run covers it. If it is RED while the local Task 3/Task 4 gates passed, treat it as cross-toolchain non-reproducibility: apply Task 4 Step 1's narrowing fallback (diff only `.source-hash` plus a content hash of `app.js`), record the non-reproducibility as a follow-up note in the PR description, and do not merge until the job is green.
