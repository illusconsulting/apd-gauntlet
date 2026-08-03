# Guardrail hardening (post-PR #8) — design

- **Date:** 2026-07-14
- **Status:** Approved (design), pending implementation
- **Amended:** 2026-08-02 — every claim re-verified against
  `illusconsulting/apd-gauntlet` `main` (`27270d5`), experiments re-run,
  corrections folded in; see the Amendments section at the end.
- **Origin:** Follow-up to PR #8 (plugin manifest `skills` entries pointed at
  `SKILL.md` files instead of directories; all eight skills silently failed to
  load; CI stayed green because the guarding test asserted the broken shape).

## Guiding principle

A guardrail that mirrors current repo state can only catch drift between two
copies of the same possibly-wrong thing. When a test protects an **external
contract** — Claude Code's plugin loader, a consumer's file format, a
generated-artifact match — it must assert the contract from its authoritative
spec, and where practical exercise the real consumer. The PR #8 test failed this
principle; the two PRs below apply it to the plugin channel and to the report
bundle freshness gate.

## Empirical findings (verified 2026-07-14)

- `claude plugin validate <path>` (CLI 2.0.76) exists and runs headless, but
  **does not catch the file-vs-directory `skills` error**: a fixture whose
  `skills` entry points at `./skills/foo/SKILL.md` (the exact original bug)
  passes validation with exit 0. There is no `--strict` flag in this version,
  and it exits 0 on warnings.
- Consequence: the CLI is useful only for JSON/schema hygiene (invalid JSON,
  missing required fields). The custom filesystem-aware conformance test is the
  load-bearing guard for the path-form class.
- When the target path contains `marketplace.json`, the CLI validates the
  marketplace manifest; the plugin manifest must be validated as its own target.

## Empirical findings (re-verified 2026-08-02)

All 2026-07-14 findings reproduce, on the same CLI version (2.0.76 is still the
installed CLI at re-verification time):

- The file-form `skills` fixture (`./skills/foo/SKILL.md`) still passes
  `claude plugin validate` — "✔ Validation passed with warnings", exit 0. The
  conformance test remains the load-bearing guard.
- Both real manifests pass validation as file targets, and a `marketplace.json`
  target is validated as a marketplace manifest — the per-file invocation form
  PR A uses is correct.
- `python tools/build_report_template.py` (node v26, esbuild 0.28.1) reproduces
  the committed bundle **byte-identically**:
  `git status --porcelain` over `tools/apd_gauntlet/data/report-template/` is
  empty after a fresh rebuild. PR B's byte-exact rebuild-diff gate is viable.
  (Caveat found by the 2026-08-02 adversarial plan review: that run reused an
  already-populated local `node_modules`, and `.build/.gitignore` ignores
  `package-lock.json` — no lockfile is tracked, so a fresh checkout falls back
  to `npm install` with floating transitives. PR B therefore commits the
  lockfile, and re-proves byte-identity from a clean `npm ci` install, before
  the CI gate lands; see Amendments item 6.)
- SchemaStore hosts both schemas, but the marketplace filename differs from the
  draft: `claude-code-plugin-manifest.json` resolves (200) while
  `claude-code-plugin-marketplace.json` **404s** — the correct catalog entry is
  `claude-code-marketplace.json` (200, "Claude Code Plugin Marketplace").
- The repo's workflows now pin `actions/checkout` at
  `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` (v7.0.0, dependabot PR #4). New CI
  jobs must use that pin, not the v6.0.3 pin that was current at drafting time.

## PR B — report-template freshness gate

### Problem

The freshness gate has two independent defects:

1. **Cross-language hash divergence.** `tools/check_report_template_freshness.py`
   (`compute_source_hash`) excludes dotfiles only at the top level
   (`rel.parts[0].startswith(".")`), while `report-template/.build/build.mjs`
   (`walk`) excludes them at every depth (`e.startsWith(".")`). Adding any nested
   dotfile under `report-template/` (e.g. `vendor/.gitkeep`) makes the two hashes
   diverge, turning the gate falsely red in a way a rebuild cannot fix.
2. **The gate never rebuilds the bundle.** It only compares the committed
   `.source-hash` marker against a recomputed source hash; a stale or
   hand-edited `app.js` shipped alongside a correctly-refreshed `.source-hash`
   passes.

### Fix

- Align the Python dotfile exclusion with Node's every-depth rule so the two
  implementations agree.
- Add a real rebuild-and-diff to the freshness path (approved scope): run
  `node build.mjs` and assert the freshly built bundle (`app.js` included) is
  byte-identical to the committed one.

### Tests (TDD — written first, must fail before the fix)

- A pytest that constructs a fixture source tree containing a nested dotfile and
  asserts `compute_source_hash` excludes it (reproduces the divergence).
- A parity test that runs the real Node walk over the same fixture and asserts a
  byte-identical hash; skipped with a clear reason when `node` is unavailable,
  and executed unconditionally in the rebuild-diff CI job (which has Node) so
  the skip cannot go permanently unnoticed. Requires extracting the walk into
  `source-hash.mjs` (see Files). The fixture must also include a directory/file
  name-collision pair (`screens/` vs `screens.css`) so ordering agreement —
  Python's parts-tuple sort vs Node's per-directory sorted DFS — is pinned by a
  test rather than assumed.
- The stale-bundle guard: a manual mutate-`app.js` non-vacuity check at
  implementation time, plus a source-grep pytest asserting the CI workflow
  retains the rebuild-diff job and its `git diff --exit-code` line (mutating a
  tracked bundle from inside pytest is not worth the churn).

### Files

- `tools/check_report_template_freshness.py` (the exclusion fix).
- `report-template/.build/.gitignore` + a newly committed
  `report-template/.build/package-lock.json`: un-ignore and commit the lockfile
  so `tools/build_report_template.py` takes its `npm ci` branch on fresh
  checkouts — without it the byte-exact rebuild-diff floats on transitive
  resolutions (`dagre`, `cose-base`, `layout-base`, `loose-envify`, …) that
  esbuild bundles into `app.js`.
- `report-template/.build/source-hash.mjs` (new): the walk/hash extracted from
  `build.mjs`, exported and runnable as `node source-hash.mjs <dir>` so the
  parity test exercises the real Node rule instead of a third hand-mirrored
  copy. `build.mjs` imports it; semantics must be unchanged, proven by the
  emitted `.source-hash` being byte-identical after a rebuild (`.build/` is
  hash-excluded at every depth, so the new file cannot perturb the hash).
- Tests appended to `tests/unit/report/test_tier3_bundle_freshness.py` (the
  existing freshness test module).
- A new `bundle-rebuild-diff` CI job with Node: rebuilds via `build.mjs`,
  asserts the committed bundle is byte-identical, and runs the freshness test
  module so the parity test executes in CI.

### Risks

- The rebuild-diff requires `node` in the freshness job; guard the pytest with a
  skip when `node` is absent so local runs without Node still pass.
- Non-determinism in `build.mjs` output would break byte-identical diffing;
  verify the build is reproducible before relying on it. (Verified 2026-08-02
  on macOS/node v26: a fresh rebuild reproduces the committed bundle exactly.
  The plan re-checks on the CI toolchain before the gate lands.)

## PR A — plugin-channel guardrails

### Problem

Manifest guards check filesystem correspondence, not the loader contract; the
path-form class is unguarded for `agents`/`commands` (only implicitly, via glob
set-equality) and was wrong for `skills`. Skill `SKILL.md` frontmatter is
validated for only two of eight skills. Nothing runs the real manifest
validator.

### Components

- **Generalized manifest conformance test (load-bearing).** For each manifest
  array, assert the loader contract: `skills` entries are directories containing
  `SKILL.md`; `agents` entries are `.md` files; `commands` entries are `.md`
  files. Include a comment linking the docs and stating that
  `claude plugin validate` does not catch this class. Keep the existing drift
  guards as separate, clearly-labeled tests. The `skills` branch deliberately
  overlaps `test_skills_entries_are_directories_not_files` (which stays as the
  narrowly labeled PR #8 regression guard); the genuinely new contract coverage
  is `agents`/`commands` path-form plus the non-vacuity fixtures.
- **`claude plugin validate` CI step (defense-in-depth, labeled).** Add a CI
  step that validates both `plugin.json` and `marketplace.json`, documented as
  JSON/schema hygiene only — explicitly not the path-form guard. It exits 0 on
  warnings, so it is a smoke check, not an authoritative gate.
- **Uniform skill-frontmatter linter.** Extend the `lint_agents.py` pattern to a
  `lint_skills` over every `.claude/skills/*/SKILL.md`: `SKILL.md` present, valid
  `name`/`description` frontmatter, `name` matches the directory. Wire into the
  lint test suite so all eight skills are covered uniformly, and invoke the CLI
  in CI beside `lint-agents` (`markdown-lint.yml`) so the two channels stay
  symmetric.
- **Docs.** `CONTRIBUTING.md` gains a plugin-channel verification step plus the
  guiding principle above; the PR template gains a checklist line for
  `.claude`/`.claude-plugin` changes; add an optional `$schema` pointer to the
  manifests for editor validation. (SchemaStore names verified 2026-08-02:
  plugin manifest = `claude-code-plugin-manifest.json`, marketplace =
  `claude-code-marketplace.json`. The `claude-code-plugin-marketplace.json`
  form 404s — do not use it.)

### Tests (TDD)

- Conformance test written to fail against a temporary broken (file-form)
  manifest fixture, then pass against the real (fixed) manifest.
- Skill-linter tests: a known-good skill passes; synthetic skills with a missing
  `SKILL.md`, missing `description`, and a `name`/directory mismatch each fail
  (non-vacuous detector, mirroring `test_no_external_path_resolution`).

### Files

- `tests/test_plugin_manifest.py` (generalized conformance test).
- `tools/apd_gauntlet/lint_skills.py` (new) + test module.
- `.github/workflows/validate.yml` (`claude plugin validate` step).
- `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`,
  `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (`$schema`).

### Risks

- The `claude` CLI may not be present in the CI runner; if installing it is
  heavy, make the step best-effort (documented) rather than a hard gate, since
  it is defense-in-depth only. (Amended: keep it a hard step but pin the
  install — `@anthropic-ai/claude-code@2.0.76`, the version the exits-0
  behavior was verified on — so the gate is deterministic. A hard failure then
  signals a real contract change worth investigating; version bumps are
  deliberate, never implicit.)
- `$schema` on the manifests must not break `claude plugin validate` (unknown
  top-level key); verify it is accepted before committing.

## Testing and gates

- Both PRs follow TDD: failing test first, then implementation.
- Both must pass all four CI gates locally before push: `pytest`, `ruff check`,
  `mypy`, and the full markdownlint glob (specs are linted; plans are excluded).

## Sequencing

- PR B is independent of PR #8 and can be built off `main` immediately.
- PR A is built off `main` now that PR #8 has merged (the manifest is in
  directory form, so the conformance test is green rather than red).
- The two are separate branches and separate PRs; neither depends on the other.

## Out of scope (deferred)

- R2 (`test_agents_array_matches_dir` mirror pattern) — lower severity; the new
  conformance test adds the positive contract check, so a rewrite is unnecessary.
- R4 (C4 fixture magic-number tests) — intra-repo fixture stability, defensible.
- KB refresh upstream-shape canaries and agent `tools`/`model` frontmatter
  linting — noted in the audit, not part of this hardening pass.

## Amendments (2026-08-02)

Applied after re-verifying every claim against `illusconsulting/apd-gauntlet`
`main` (`27270d5`) and re-running all experiments:

1. Marketplace `$schema` URL corrected to
   `https://json.schemastore.org/claude-code-marketplace.json` — the draft's
   `claude-code-plugin-marketplace.json` form 404s.
2. New CI jobs pin `actions/checkout` at v7.0.0 (`9c091bb…`), matching the
   post-dependabot repo convention; `actions/setup-node` is SHA-pinned (v7.0.0,
   `8207627…` — a lightweight tag, so that is the commit); the `claude` CLI
   install is version-pinned to 2.0.76.
3. PR B restores the approved parity test via a minimal extraction of the walk
   into `report-template/.build/source-hash.mjs` (imported back by
   `build.mjs`), with a fixture covering both the nested dotfile and a
   `screens`/`screens.css` name-collision pair; the stale-bundle mutation test
   is realized as a manual implementation-time gate plus a source-grep pytest
   guarding the CI job.
4. PR A wires `lint-skills` into CI beside `lint-agents`
   (`markdown-lint.yml`).
5. Both plans carry a provenance note pinning the verified base commit. The
   three documents were drafted in the `APD-sec-arch-framework` checkout (the
   clone of `illusconsulting/apd-gauntlet`) and now live in the
   `apd-gauntlet-illus` working copy as planning input for that target repo.
6. Adversarial plan verification (2026-08-02, four independent reviewers over
   the final 2026-08-02 plans) found the rebuild's "lockfile-pinned" premise
   false at the base commit: `.build/.gitignore` ignores `package-lock.json`,
   so fresh checkouts run `npm install` with floating transitives. PR B gains
   a task that un-ignores and commits the lockfile — proving a clean `npm ci`
   rebuild is byte-identical — before the CI gate lands, its
   matrix-has-no-Node wording was corrected (ubuntu-latest runners ship Node;
   the pinned job *guarantees* parity-test execution rather than enabling it),
   and a post-push step watches the first `bundle-rebuild-diff` run to honor
   the "re-checks on the CI toolchain" promise. PR A gained a
   `commands`-branch non-vacuity fixture (4 new tests, 10 total) and an
   import-order fix (ruff I001).
7. Final whole-branch review of PR B (2026-08-02) found three residual
   hardening gaps. The `bundle-rebuild-diff` job's diff step gains a
   `git add -N tools/apd_gauntlet/data/report-template/` intent-to-add prefix
   so the gate also catches brand-new untracked bundle outputs, which plain
   `git diff` is blind to (a guard test now asserts the prefix is present).
   The two comment pointers left over from Task 3's extraction — one in
   `tools/check_report_template_freshness.py`, one in the parity test's
   docstring — that still cited `build.mjs walk() (line 54)` are re-aimed at
   `report-template/.build/source-hash.mjs`, the file that now owns the walk.
   `source-hash.mjs`'s CLI entry guard is made safe for an undefined
   `argv[1]` (`process.argv[1] && ...`), matching Node's own recommended
   `main`-module check.
