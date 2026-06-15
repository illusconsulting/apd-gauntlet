# Contributing to APD Gauntlet

Thanks for your interest in improving APD Gauntlet. This document describes our contribution conventions.

## Quick links

- [Design spec](docs/superpowers/specs/2026-05-24-apd-gauntlet-v1-design.md)
- [Architecture](docs/architecture.md)
- [Running the gauntlet](docs/running-the-gauntlet.md)

## Local development setup

```bash
git clone https://github.com/illusconsulting/apd-gauntlet.git
cd apd-gauntlet
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest                       # full test suite (~95 tests, ~92% coverage)
ruff check tools/ tests/
mypy tools/
# docs lint — mirrors the markdownlint CI job (npx fetches the tool; no local install needed)
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

Run all four gates (`pytest`, `ruff`, `mypy`, `markdownlint`) before pushing — CI enforces every one of them, so a green `pytest` alone is not sufficient.

## Proposing changes

For non-trivial changes, open an issue first to discuss the approach. Schema changes and new domain packs warrant especially careful review.

## Testing

Every PR must:

- Add tests for new behavior (we follow TDD discipline).
- Maintain >= 85% line coverage on `tools/apd_gauntlet/`.
- Pass `ruff check`, `mypy`, `markdownlint`, and `pytest` cleanly.
- Validate the bundled example via `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/`.

The CI workflows enforce these gates on every PR.

## Commit messages

- Keep subject lines under 80 characters.
- Reference the milestone (e.g. `M3:`) when the change is part of the v1.0 build.
- Use the imperative mood: "Add ATT&CK rationale check" not "Added".

## Sign-off

We use Developer Certificate of Origin (DCO) sign-off. Add `-s` to your commit:

```bash
git commit -s -m "Your message"
```

## Schema and breaking changes

Schema changes follow the policy in [docs/schema-evolution.md](docs/schema-evolution.md). In short: adding optional fields is a minor bump; renaming or removing fields is a major bump.

## Domain packs

To author a new domain pack, see [docs/adapting-to-other-domains.md](docs/adapting-to-other-domains.md). New packs land as PRs against `domains/<new-pack-name>/` plus a sample run under `examples/`.
