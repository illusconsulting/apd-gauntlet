# APD Gauntlet

**Multi-agent security architecture review for technical plans.** You feed it a tech plan plus supplementary artifacts (PRD, code, IaC, diagrams, threat models, ADRs); nine specialist agents — orchestrated by Claude Code — review it through nine independent lenses; a synthesizer dedups across lenses, surfaces contradictions, and emits an advisory report.

The output is **structured advisory input for an architect, not a gate**. It does not approve or block changes — it makes the human review better-informed and harder to bypass.

```text
APD framework — 3 tiers × 9 goals
─────────────────────────────────
Trustworthiness   →  Confidentiality · Integrity · Availability
Scalability       →  Distributed · Resilient · Ephemeral
Auditability      →  Authenticity · Non-Repudiation · Immutability
```

Findings carry NIST 800-53r5 + MITRE ATT&CK mappings (and CWE / OWASP Top 10 / API / LLM mappings when the run declares those taxonomies). Capabilities carry NIST + ATT&CK mitigation + optional D3FEND mappings. Severity is calibrated against an explicit, domain-specific rubric — never a free-text guess.

---

## At a glance

| You give it | It produces |
|---|---|
| A tech plan + supporting artifacts | An advisory report (`40-synthesis/advisory-report.md`) and an interactive HTML view |
| A threat model (optional — Threat Dragon, MS TMT, STRIDE, LINDDUN, attack trees) | A coverage/contradiction/silence report against your TM |
| Crown jewels + attacker positions (optional, v1.4+) | A BloodHound-style attack-path graph with a D3FEND defensive overlay on bottleneck edges |
| A domain pack (PBM ships in v1; api-security, identity-security, security-tooling, agentic-ai ship in v1.5) | Calibrated severity, consequential-action surface, immutability classes, and common-pattern hints tuned for that domain |

---

## Prerequisites

- **Python ≥ 3.10** (for the `apd-gauntlet` CLI — validator, scaffold, HTML report generator).
- **Claude Code** with agent and skill support — the gauntlet's specialist agents run as Claude Code subagents.
- **A tech plan** for the change you want reviewed. Optional but recommended: PRD, source code, IaC, architecture diagrams, threat models, ADRs, runbooks, test reports.

---

## Install

```bash
pip install apd-gauntlet
apd-gauntlet --version    # prints the installed version, confirming the CLI is on your PATH
```

That installs both the Python CLI and the Claude Code agent + skill bundle.

---

## First run (~10 minutes)

The fastest way to see what a finished report looks like is to validate one of the bundled example runs and open its HTML view. No Claude Code session required.

### 1. Validate the bundled crAPI run

```bash
git clone https://github.com/shoveleejoe/apd-gauntlet.git
cd apd-gauntlet
apd-gauntlet validate runs/apd-20260527-crapi-owasp-api-top10/
```

You should see `Validation passed` — the run is well-formed against every schema and cross-file invariant.

### 2. View the HTML report

Every completed run ships a self-contained HTML bundle at `runs/<run-id>/40-synthesis/report-html/`. Two ways to open it:

```bash
# Option A — open directly (no server)
open runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/report-html/index.html
```

```bash
# Option B — serve over HTTP (recommended; some browsers restrict
# file:// access for the Mermaid attack-graph rendering)
cd runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/report-html
python3 -m http.server 8080
# then open http://localhost:8080
```

The report has six tabs: **Overview, Findings, Capabilities, Coverage** (NIST / ATT&CK / APD-component rollups), **Attack paths** (asset graph + enumerated paths), and **Annexes** (contradictions, severity disagreements).

### 3. Scaffold your own run

```bash
apd-gauntlet init-run apd-$(date +%Y%m%d)-my-feature \
  --inputs ~/path/to/tech-plan-and-artifacts/ \
  --domain pbm
```

This creates `runs/apd-YYYYMMDD-my-feature/` with the expected subdirectory layout and copies your artifacts into `inputs/`.

### 4. Run the gauntlet

In Claude Code, from the repo root, run the `apd-gauntlet` workflow runner against the scaffolded run directory:

```text
> Run the apd-gauntlet workflow on runs/apd-YYYYMMDD-my-feature/
```

The runner (`.claude/workflows/apd-gauntlet.js`) phases the run end-to-end: it builds the `apd-domain` skill from the active pack(s), runs intake, dispatches the nine specialist agents by tier, then runs the decomposed synthesis and the gated report audit. When it finishes (~10–30 minutes depending on artifact volume), validate and view the report exactly like step 1–2 above.

For the full operator workflow including code reconnaissance, threat-model evaluation, and attack-path analysis, see **[docs/running-the-gauntlet.md](docs/running-the-gauntlet.md)**.

---

## Example runs

Three fully worked runs ship in `runs/`. Each demonstrates a different domain pack and a different review surface.

| Run | Domain pack | Subject | What it demonstrates |
|---|---|---|---|
| `apd-20260527-crapi-owasp-api-top10` | `api-security` | OWASP crAPI (deliberately vulnerable API) | OWASP API Top 10 coverage, BOLA/MFA findings, the canonical "what does a report look like" example |
| `apd-20260527-caldera-adversary-emulation` | `security-tooling` | MITRE Caldera | NIST 800-115 + ATT&CK-anchored review of a security tool, two-axis severity rubric, ROE/CFAA framing |
| `apd-20260527-authentik-identity-provider` | `identity-security` | authentik IdP | NIST 800-63B + OAuth/OIDC/SAML + GDPR coverage, attack-path enumeration |

Validate any of them:

```bash
apd-gauntlet validate runs/apd-20260527-caldera-adversary-emulation/
apd-gauntlet validate runs/apd-20260527-authentik-identity-provider/
```

The HTML report at `<run>/40-synthesis/report-html/index.html` is preloaded — open it the same way as step 2 above.

---

## Customize for your domain

The framework is domain-neutral; the **calibration** is domain-specific. Five packs ship today:

- **`pbm`** — Pharmacy Benefit Management (the reference pack)
- **`api-security`** — OWASP API Top 10 anchored
- **`identity-security`** — NIST 800-63B + OAuth/OIDC/SAML + GDPR
- **`security-tooling`** — NIST 800-115 + ATT&CK + CFAA/ROE (two-axis severity)
- **`agentic-ai`** — autonomous LLM-agent systems (OWASP LLM Top 10; ATLAS/MAESTRO grounding)

Author a new pack with `apd-gauntlet build-domain-skill <pack-name>` and the structure documented in **[docs/adapting-to-other-domains.md](docs/adapting-to-other-domains.md)**. A pack defines:

- A severity rubric (what's critical vs high vs medium for your domain)
- The consequential-action surface (what must produce audit logs)
- Immutability classes (what data must not change)
- A field-level data taxonomy with regulatory citations
- Per-goal "common patterns" the specialists use as hint catalogues

---

## CLI reference

| Command | Purpose |
|---|---|
| `apd-gauntlet init-run <id> --inputs DIR [--domain pbm]` | Scaffold a new run directory |
| `apd-gauntlet validate <run-dir>` | Run schema + semantic + cross-file validation |
| `apd-gauntlet build-report <run-dir>` | Regenerate the HTML report |
| `apd-gauntlet analyze-attack-paths <run-dir>` | (v1.4+) Build asset graph + enumerate paths |
| `apd-gauntlet parse-threat-model <file>` | Normalize a TM into the gauntlet's graph format |
| `apd-gauntlet build-domain-skill <pack>` | Assemble the `apd-domain` skill from a pack |
| `apd-gauntlet validate-domain <pack>` | Lint a domain pack for completeness |
| `apd-gauntlet summarize <run-dir>` | Finding / capability statistics |
| `apd-gauntlet lint-agents` | Check agent file frontmatter |
| `apd-gauntlet check-ids <yaml>` | Verify deterministic IDs |
| `apd-gauntlet refresh-mitre / refresh-cwe / refresh-d3fend / refresh-owasp` | Refresh cached taxonomy data |

Every command supports `--help`.

---

## Documentation

| Doc | When you need it |
|---|---|
| [Running the gauntlet](docs/running-the-gauntlet.md) | Operator guide — full workflow including code recon, TM evaluation, attack-path analysis |
| [HTML report](docs/html-report.md) | Report structure, regeneration, what `report-data.yaml` adds |
| [Attack-path analysis](docs/attack-path-analysis.md) | v1.4+ — crown jewels, attacker positions, D3FEND overlay, `apath-` finding flavors |
| [Threat modeling](docs/threat-modeling.md) | Supplying a TM, supported formats, the `tmeval-` finding flavors |
| [Adapting to other domains](docs/adapting-to-other-domains.md) | Authoring a new domain pack |
| [Architecture](docs/architecture.md) | How the gauntlet works under the hood |
| [Extending agents](docs/extending-agents.md) | Framework-level contributor guide |
| [Taxonomy mappings](docs/taxonomy-mappings.md) | NIST / ATT&CK / CWE / OWASP / D3FEND wiring |
| [Schema evolution](docs/schema-evolution.md) | Versioning policy |
| [ADRs](docs/adrs/) | Design rationale |

---

## Troubleshooting

**`apd-gauntlet: command not found`** — make sure your pip install location is on `PATH`. Verify with `pip show apd-gauntlet` and check the `Location` field's parent `bin/` directory.

**HTML report shows a blank Coverage / Attack paths tab** — the synthesizer may have emitted a YAML shape the transforms don't recognize. The transforms tolerate four shape variants today (chainguard-era, crAPI-era, caldera-era, authentik-era); if you hit a fifth, run `apd-gauntlet build-report <run-dir>` and check the console output, then open an issue with a redacted copy of the offending `40-synthesis/*.yaml` file.

**Validator fails with cross-file errors** — start with `apd-gauntlet validate <run-dir> --schema-only` to isolate schema problems from semantic ones, then re-run without the flag once the schema is clean.

**Mermaid graph labels are invisible in the report** — your browser's strict-mode CSP may be stripping `<foreignObject>` content. Either use Option B (HTTP server) instead of `file://`, or regenerate with `apd-gauntlet build-report` against v1.4.0 or newer.

---

## Contributing

Domain pack proposals welcome — open an issue first using the `domain_pack_proposal` template. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, test conventions, and the PR checklist.

## License

[Apache 2.0](LICENSE).
