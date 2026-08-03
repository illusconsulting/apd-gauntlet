## Summary

<!-- 1-3 sentences explaining what this PR does and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature (additive, no breaking changes)
- [ ] Schema change (requires schema_version bump)
- [ ] Documentation update
- [ ] CI / tooling

## Checklist

- [ ] Tests added or updated for the new behavior
- [ ] `pytest` passes locally
- [ ] `ruff check tools/ tests/` clean
- [ ] `mypy tools/` clean
- [ ] `apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/` clean
- [ ] Schema changes (if any) include a `schema_version` bump per [docs/schema-evolution.md](../docs/schema-evolution.md)
- [ ] Docs / CHANGELOG updated for user-visible changes
- [ ] DCO sign-off (`git commit -s`)
- [ ] Plugin/`.claude` changes: `claude plugin validate .claude-plugin/plugin.json` clean and `/doctor` loads all skills

## Notes for reviewers

<!-- Anything reviewers should pay particular attention to. -->
