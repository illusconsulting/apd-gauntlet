# Releasing

Versions are **lockstep** across both distribution channels. To cut release X.Y.Z, update ALL of these together:

1. `pyproject.toml` → `version = "X.Y.Z"`
2. `tools/apd_gauntlet/__init__.py` → `__version__ = "X.Y.Z"`
3. `.claude-plugin/plugin.json` → `"version": "X.Y.Z"`
4. `.claude-plugin/marketplace.json` → the `apd-gauntlet` plugin entry `"version": "X.Y.Z"`
5. `tests/test_workflow_apd_gauntlet.py` → the version-floor literal in `test_plugin_manifest_version_matches_pyproject`
6. `CHANGELOG.md` → a new `## vX.Y.Z` section

Then: `pytest -q`, commit, `git tag vX.Y.Z`, `git push --tags`. The `release` GitHub Actions workflow builds sdist+wheel, smoke-tests the wheel in a clean venv, validates the plugin/marketplace manifests, publishes to PyPI via Trusted Publishing (OIDC), and cuts a GitHub Release.

## Two channels

- **PyPI** (engine): `pip install apd-gauntlet`. Ships the deterministic CLI + bundled schemas/domains/taxonomies + the prebuilt HTML report bundle.
- **Claude Code plugin** (agents/skills/workflow): `/plugin marketplace add illusconsulting/apd-gauntlet` then `/plugin install apd-gauntlet@apd-security`. **Requires the `apd-gauntlet` PyPI package on PATH** (the workflow runner shells out to it). Bump the plugin `version` on every release — Claude Code caches plugins by version, so consumers only receive updates when the version changes.

## Known follow-up

- Migrate license metadata to the modern PEP 639 form before setuptools makes it a hard error (2027-02-18): `license = "Apache-2.0"` (bare SPDX string) + `[project] license-files = ["LICENSE", "NOTICE"]`, drop the `License ::` classifier, and bump the build requirement to `setuptools>=77`.
