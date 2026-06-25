---
description: Run the APD security gauntlet against a prepared run directory
---

You are driving the APD gauntlet. Do this in order:

1. **Preflight the engine.** Run `apd-gauntlet --version` in the shell. If the command
   is missing, STOP and tell the user: "Install the engine first: `pip install apd-gauntlet`
   (or `pipx install apd-gauntlet`)." The plugin and CLI are released in lockstep — if the
   reported version's major.minor differs from this plugin's, warn that they should match.

2. **Confirm the run is scaffolded** — a `runs/<run-id>/` directory containing `inputs/`
   and an `.apd-run.yaml`. If it is not present, point the user to docs/running-the-gauntlet.md
   and offer to scaffold it with `apd-gauntlet init-run`.

3. **Launch the runner** via the Workflow tool, executing the script at
   `${CLAUDE_PLUGIN_ROOT}/.claude/workflows/apd-gauntlet.js`, passing the run's parsed
   `.apd-run.yaml` as `args`. Run it INTERACTIVE / FOREGROUND — never headless or in the
   background, because a background launch can interrupt the specialist subagent dispatches.
