# Releasing

Two release lines are maintained at once. Each line ships through both
distribution channels (the PyPI engine and the Claude Code plugin), and inside
a line the two channels move in lockstep.

## Release lines

| Line | Branch | Versions | PyPI | Claude Code plugin |
| --- | --- | --- | --- | --- |
| Stable (1.7) | `main` | `1.7.Z` | `pip install apd-gauntlet` (the default) | `/plugin marketplace add illusconsulting/apd-gauntlet` → `apd-gauntlet@apd-security` |
| Next (2.0) | `next` | `2.0.0aN`, `2.0.0bN`, `2.0.0rcN` | `pip install --pre apd-gauntlet`, or an exact pin such as `apd-gauntlet==2.0.0a1` | `/plugin marketplace add illusconsulting/apd-gauntlet#next` → `apd-gauntlet@apd-security-next` |

`pip install apd-gauntlet` never selects a pre-release, so 2.0 alphas, betas
and release candidates reach only people who ask for them. On GitHub, the
release workflow marks them as pre-releases, and only the highest stable
version is marked **Latest**.

After 2.0.0 goes GA, `next` merges into `main`, `main` becomes the 2.x line,
and 1.7 maintenance moves to a `release/1.7` branch (see [2.0.0 GA](#200-ga)).

## Where changes land

- **A fix both lines need:** open the PR against `main`. After it merges,
  merge `main` into `next` with a merge commit (not a cherry-pick or squash),
  so git records that `next` contains it. Do this at least before every `next`
  pre-release.
- **2.0-only work:** open the PR against `next`.
- **Never merge `next` into `main` before GA.**
- When merging `main` into `next` conflicts on the version files listed below
  or on `CHANGELOG.md`, keep `next`'s values and add the `main` changelog entry
  under its own heading.

Dependabot opens its PRs against `main` (Actions and npm) and, for the 2.0-only
Python dependencies, against `next`. The merge-forward carries the `main` bumps
to `next`.

## Version lockstep

Every release updates all of these together:

1. `pyproject.toml` → `version = "…"`
2. `tools/apd_gauntlet/__init__.py` → `__version__ = "…"`
3. `.claude-plugin/plugin.json` → `"version": "…"`
4. `.claude-plugin/marketplace.json` → the `apd-gauntlet` plugin entry's `"version"`
5. `tests/test_workflow_apd_gauntlet.py` → the version-floor literal in
   `test_plugin_manifest_version_matches_pyproject`
6. `CHANGELOG.md` → a new `## vX.Y.Z — YYYY-MM-DD` section

Items 1, 2 and 5 use the canonical [PEP 440](https://peps.python.org/pep-0440/)
string. Items 3 and 4 use the same string for stable versions; for a
pre-release they use the SemVer spelling, which PEP 440 normalises to the same
version and which the tests compare through `packaging.Version`:

| PyPI / tag (`pyproject`, `__init__`) | Plugin (`plugin.json`, `marketplace.json`) |
| --- | --- |
| `1.7.1` | `1.7.1` |
| `2.0.0a1` | `2.0.0-alpha.1` |
| `2.0.0b1` | `2.0.0-beta.1` |
| `2.0.0rc1` | `2.0.0-rc.1` |
| `2.0.0` | `2.0.0` |

The tag is always `v` + the PyPI string: `v1.7.1`, `v2.0.0a1`.

Claude Code caches plugins by version, so plugin users receive an update only
when the version changes. Each drop to testers therefore needs its own
pre-release number (`a1`, `a2`, …); new commits on `next` do not reach plugin
users until the version moves.

## The release gate

`.github/workflows/release.yml` runs on every `v*` tag. Before testing,
building or publishing, it runs `tools/check_release_tag.py`, which refuses the
release unless:

- the tag is exactly `v` + the `pyproject.toml` version, and that version is in
  canonical PEP 440 form;
- `__init__.__version__`, `plugin.json` and the marketplace entry carry the
  same version;
- the tagged commit is on an allowed branch: stable versions only from `main`
  or `release/*`, and pre-releases from `main`, `next` or `release/*`.

The gate also decides how the GitHub Release is flagged: a pre-release version
is published as a GitHub pre-release, and **Latest** goes only to a stable
version at least as high as every other stable tag. A 1.7.x maintenance release
cut after 2.0.0 therefore never displaces 2.0 as Latest.

## Cutting a stable 1.7.x release (from `main`)

1. On a branch from `main`, bump the six places above to `1.7.Z`.
2. Run `pytest -q`, open a PR against `main`, and merge it.
3. Tag the merge commit and push the tag:
   `git tag v1.7.Z <merge-sha> && git push origin v1.7.Z`.
4. The release workflow publishes to PyPI as the default version and creates a
   GitHub Release marked Latest.
5. Merge `main` into `next`, keeping `next`'s version values.

## Cutting a 2.0 pre-release (from `next`)

1. On a branch from `next`, bump the six places above: `2.0.0aN` in
   `pyproject.toml`, `__init__.py` and the test literal; `2.0.0-alpha.N` in
   both plugin manifests; and a `## v2.0.0aN — YYYY-MM-DD` changelog section.
2. Run `pytest -q`, open a PR against `next`, and merge it.
3. Tag the merge commit and push the tag:
   `git tag v2.0.0aN <merge-sha> && git push origin v2.0.0aN`.
4. The release workflow publishes to PyPI as a pre-release and creates a GitHub
   pre-release that is not marked Latest.

Move through the stages in order: alphas while features are still landing,
betas once 2.0 is feature-complete, and release candidates when only fixes
remain.

## 2.0.0 GA

1. Confirm the last release candidate has been tested with both the plugin and
   the engine installed from it.
2. Preserve the 1.7 line: `git push origin main:release/1.7`. On `release/1.7`,
   rename the marketplace to `apd-security-1.7` (in `marketplace.json`, the
   README and this file), so 1.7 users can register it next to the default
   marketplace.
3. Merge `main` into `next` one last time.
4. On `next`, set every version to `2.0.0`, rename the marketplace back to
   `apd-security`, and write the `## v2.0.0` changelog section, including
   upgrade notes for 1.7 users.
5. Merge `next` into `main` with a merge commit, then tag `v2.0.0` on `main`.
   Existing plugin users on the default marketplace receive 2.0.0 at their next
   update, and `pip install apd-gauntlet` resolves to 2.0.0.
6. Housekeeping:
   - In `.github/dependabot.yml`, drop the `target-branch: next` entry. Add
     `release/1.7` entries if the 1.7 line still needs dependency updates.
   - Update the release-lines table above.
   - Either delete `next` or reset it to `main` for the 2.1 pre-releases.

After GA, 1.7.x fixes go to `release/1.7` and are tagged there. The gate allows
stable tags on `release/*` and keeps them from becoming Latest. Merge
`release/1.7` into `main` whenever a fix applies to both lines.

## Repository settings (administrators)

These live outside the repository, so the PRs that set up the release lines
cannot apply them:

- Protect `next` the way `main` is protected: require a PR and the
  `python-tests` and `validate` checks.
- Add a tag ruleset that limits who can create `v*` tags. A pushed tag
  publishes to PyPI once the gate passes.
- PyPI trusted publishing needs no change, because both lines publish from
  the same `release.yml` workflow.

## Two channels

- **PyPI** (engine): ships the deterministic CLI, the bundled
  schemas/domains/taxonomies and the prebuilt HTML report bundle.
- **Claude Code plugin** (agents/skills/workflow): **requires the
  `apd-gauntlet` PyPI package on PATH** from the same line (the workflow runner
  shells out to it). `/apd-gauntlet:run` warns when the engine's major.minor
  differs from the plugin's. Install one line's plugin at a time; both register
  the `apd-gauntlet` command namespace.

## Known follow-up

- Migrate license metadata to the modern PEP 639 form before setuptools makes it a hard error (2027-02-18): `license = "Apache-2.0"` (bare SPDX string) + `[project] license-files = ["LICENSE", "NOTICE"]`, drop the `License ::` classifier, and bump the build requirement to `setuptools>=77`.
