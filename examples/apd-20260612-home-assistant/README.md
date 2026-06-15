# APD Gauntlet Example — Home Assistant

A real, multi-repo gauntlet run against [Home Assistant](https://www.home-assistant.io/)
(the open-source home-automation platform) and its companion apps. Unlike the
synthetic [`claim-event-bus`](../apd-20260601-claim-event-bus/) example, this is a
full assessment of a real open-source codebase — it exercises the multi-repo,
code-reconnaissance, and **C4 architecture-view** features end to end on a
non-trivial system.

> The local filesystem paths from the original run (`/Users/.../home-assistant-repos-*`)
> have been sanitized to neutral `home-assistant-repos-*` identifiers. The findings
> are the assessment's own analysis of a public open-source project.

## Files

- `.apd-run.yaml` — run config: 23-repo `repos[]`, the `api-security` +
  `mobile-applications` domain packs, `code_recon` enabled, threat-model authoring,
  and attack-path enumeration bounds.
- `inputs/` — the human-provided inputs (architecture notes, the multi-repo manifest).
- `expected/` — frozen reference outputs (the full pipeline, `00-context` →
  `40-synthesis`, including the rendered `report-html/`).

## What this run demonstrates

- **Multi-repo intake** — `repos[]` spanning core, Supervisor, os-agent, the iOS /
  Android companions, the frontend, add-ons, and the FCM push relay.
- **Code reconnaissance** — `expected/00-context/code-architecture-brief.md` +
  `code-evidence-index.yaml` (the `cev-*` anchors specialists cite).
- **The C4 architecture view** — `expected/00-context/c4-recon.yaml` (grounded,
  never-invent) → the deterministic `expected/40-synthesis/c4-model.yaml` → the
  interactive tiered "system map" in the report's **Architecture** tab (L1 system
  context, L2 containers with finding/capability badges, the attack-path overlay).
  The Supervisor → host-dockerd / os-agent host-root chains are visible as L2 edges.
- **Threat-model authoring + evaluation** — an authored STRIDE baseline
  (`expected/00-context/threat-model-authored.md`) and the evaluator's
  coverage/contradiction findings (`expected/40-threat-model/`).
- **Attack-path analysis** — `expected/40-synthesis/asset-graph.yaml` +
  `attack-paths.yaml` (attacker → crown-jewel paths) with the D3FEND overlay.
- **Both report gates GREEN** — the structural and editorial audit gates pass.

## Posture headlines (from the assessment)

Plaintext `.storage` enabling token forgery, os-agent / Docker-socket host-root
chains reachable without caller authorization, no audit log, a bearer-less webhook,
non-expiring tokens, and no certificate pinning on the mobile companions.

## Running / regenerating

Validate the frozen outputs (same check CI runs):

```bash
apd-gauntlet validate examples/apd-20260612-home-assistant/expected/
```

Rebuild the HTML report (regenerates `expected/40-synthesis/report-html/`):

```bash
apd-gauntlet build-report examples/apd-20260612-home-assistant/expected/
```

The report's `data.js` is the golden compared by
`tests/integration/report/test_example_golden.py` — if a transform intentionally
changes the output, rebuild the report and commit the updated `report-html/`.
