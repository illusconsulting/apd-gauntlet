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
pytest                       # full test suite (1700+ tests; 85% line-coverage gate)
ruff check tools/ tests/
mypy tools/
# docs lint — mirrors the markdownlint CI job (npx fetches the tool; no local install needed)
npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "tools/apd_gauntlet/data/domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"
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

### Plugin channel

If you change anything under `.claude/` or `.claude-plugin/`, a green `pytest`
does not prove the plugin loads. Run `claude plugin validate
.claude-plugin/plugin.json` and confirm `/doctor` is clean in Claude Code.

Guardrails that protect an external contract — the Claude Code loader, a
schema, a consumer's file format — must assert that contract from its
authoritative spec, not mirror the current repo state. A test that reflects
whatever shape is already present only catches drift between two copies of the
same possibly-wrong thing (this is why the pre-PR-#8 skills test stayed green
while every skill failed to load).

## Commit messages

- Keep subject lines under 80 characters.
- Reference the relevant ADR or issue number where applicable.
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
