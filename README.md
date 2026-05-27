# APD Gauntlet

Multi-agent security architecture review built on the APD framework — **A**ssure Trustworthiness, **P**rovide Scalability, **D**emonstrate Auditability. Nine specialist agents plus intake, orchestrator, and synthesizer. Runs in Claude Code against a tech plan and supplementary artifacts. Produces an advisory report with confirmed capabilities, findings, contradictions, and coverage matrices.

This is **advisory input to architecture review**, not a gate. The output is structured to help an architect make better decisions, not to replace one.

```text
Trustworthiness   →  Confidentiality · Integrity · Availability
Scalability       →  Distributed · Resilient · Ephemeral
Auditability      →  Authenticity · Non-Repudiation · Immutability
```

## Quick start

```bash
pip install apd-gauntlet
apd-gauntlet --help
```

Scaffold a run:

```bash
apd-gauntlet init-run apd-$(date +%Y%m%d)-claim-event-bus \
  --inputs <path-to-artifacts> \
  --domain pbm
```

Validate it later:

```bash
apd-gauntlet validate runs/apd-20260601-claim-event-bus/
```

Then in Claude Code, invoke the `apd-orchestrator` agent against the run directory. See [docs/running-the-gauntlet.md](docs/running-the-gauntlet.md) for the full operator workflow.

## What it produces

For a tech plan plus supplementary artifacts (PRD, code, IaC, diagrams, threat models, ADRs), the gauntlet produces:

- **Findings** — gaps, risks, uncertainties, and items blocked on missing evidence.
- **Confirmed capabilities** — security properties the design or implementation positively demonstrates, with explicit scope and caveats.

Both streams are organized along the nine APD goals listed above. Every finding and capability carries NIST 800-53r5 control mappings. Findings carry MITRE ATT&CK technique mappings (and, when the run declares the relevant taxonomies, CWE / OWASP Top 10 / API / LLM mappings) when an agent has high confidence. Capabilities carry ATT&CK mitigation mappings, optional ATT&CK technique mappings (techniques the capability defends against), and optional MITRE D3FEND mappings with required ATT&CK counter-references. Severity is calibrated against an explicit domain-specific rubric (PBM ships in v1; others can be added — see [docs/adapting-to-other-domains.md](docs/adapting-to-other-domains.md)).

When a threat model is supplied (Threat Dragon JSON, Microsoft TMT, STRIDE/LINDDUN tables, attack trees), the gauntlet's threat-model evaluator surfaces coverage gaps, contradictions between TM claims and specialist findings, and surface silences as `tmeval-` findings.

When the active domain pack (or `.apd-run.yaml`) declares crown jewels and attacker positions, v1.4 adds BloodHound-style attack-path enumeration over a partial graph assembled from intake, threat-model, code-evidence, and specialist findings — with a D3FEND defensive overlay on the bottleneck edges that expose ATT&CK techniques. The analyzer emits `apath-` findings and a dedicated `attack-path-report.md`. See [docs/attack-path-analysis.md](docs/attack-path-analysis.md) for the operator guide.

The synthesizer dedups across lenses, surfaces contradictions between findings and capabilities, and produces three rollups: a NIST 800-53r5 coverage matrix, an ATT&CK exposure summary, and an APD-by-component coverage grid. The final deliverable is `40-synthesis/advisory-report.md`.

## Try the bundled example

```bash
apd-gauntlet validate examples/apd-20260601-claim-event-bus/expected/
```

A synthetic PBM claim event bus run with curated reference outputs. See [examples/apd-20260601-claim-event-bus/README.md](examples/apd-20260601-claim-event-bus/README.md).

## Documentation

- [Architecture](docs/architecture.md) — how the gauntlet works under the hood
- [Running the gauntlet](docs/running-the-gauntlet.md) — operator guide
- [Attack-path analysis (v1.4+)](docs/attack-path-analysis.md) — crown jewels, attacker positions, the D3FEND overlay, and the `apath-` finding flavors
- [Adapting to other domains](docs/adapting-to-other-domains.md) — authoring a new domain pack
- [Extending agents](docs/extending-agents.md) — contributor guide for framework changes
- [Schema evolution](docs/schema-evolution.md) — versioning policy
- [Architecture Decision Records](docs/adrs/) — design rationale

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Domain pack proposals welcome (open an issue first); see the `domain_pack_proposal` issue template.

## License

[Apache 2.0](LICENSE).
