# Adapting to Other Domains

The APD Gauntlet ships with one domain pack: PBM (Pharmacy Benefit Management). The framework itself is domain-neutral — only the *calibration* (severity rubric, what counts as a consequential action, which data classes must be immutable, common finding patterns) is domain-specific.

This guide describes how to author a new domain pack.

## What a domain pack contains

A pack is a directory under `domains/<name>/` with this structure:

```
domains/<name>/
├── domain.yaml                  # metadata: name, version, framework_compat, includes
├── severity-rubric.md           # critical/high/medium/low thresholds for this domain
├── consequential-actions.md     # what counts as an audit-worthy action (for Non-Repudiation)
├── immutability-classes.md      # what data classes must not change (for Immutability)
├── data-taxonomy.md             # field-level data classification with regulatory citations
└── common-patterns/
    ├── confidentiality.md
    ├── integrity.md
    ├── availability.md
    ├── distributed.md
    ├── resilient.md
    ├── ephemeral.md
    ├── authenticity.md
    ├── non-repudiation.md
    └── immutability.md
```

The validator and the build-domain-skill command consume `domain.yaml`. The runtime `apd-domain` skill is assembled from the listed `includes` files.

## Step-by-step: authoring a new pack

### 1. Copy the PBM pack as a starting point

```bash
cp -r domains/pbm domains/saas
```

### 2. Edit `domain.yaml`

Change `name`, `display_name`, `version`, `description`, and `regulatory_anchors`:

```yaml
name: saas
display_name: "Software-as-a-Service"
version: 0.1.0
framework_compat: ">=1.0.0,<2.0.0"
description: "SaaS-specialized severity rubric and pattern library. Anchored to SOC 2, ISO 27001, and GDPR."
includes:
  - severity-rubric.md
  - consequential-actions.md
  - immutability-classes.md
  - data-taxonomy.md
  - common-patterns/confidentiality.md
  - common-patterns/integrity.md
  - common-patterns/availability.md
  - common-patterns/distributed.md
  - common-patterns/resilient.md
  - common-patterns/ephemeral.md
  - common-patterns/authenticity.md
  - common-patterns/non-repudiation.md
  - common-patterns/immutability.md
regulatory_anchors:
  - "SOC 2"
  - "ISO 27001"
  - GDPR
```

The `framework_compat` field is a semver range; the validator refuses to build the skill if the active framework version is outside it.

### 3. Rewrite `severity-rubric.md`

The PBM rubric anchors to HIPAA breach-notification thresholds (>500 members = critical), CMS Part D PDE integrity, URAC accreditation, and SOC 2. A SaaS rubric would anchor differently:

- **Critical**: GDPR-relevant data exfiltration affecting >X data subjects; tenant data crossing tenant boundaries; auth bypass; total service outage exceeding SLA.
- **High**: customer data exposure beyond minimum-necessary; degraded multi-tenancy isolation short of bypass; auth weakness; sustained partial outage.
- **Medium**, **Low**, **Informational**: as the framework convention suggests.

Cite the regulatory anchors precisely. Specialists cite the matching clause in finding `detail` fields, so clauses must be specific enough to reference.

### 4. Rewrite `consequential-actions.md`

What actions in your domain are audit-worthy? For SaaS:

- Tenant data access (read, export)
- Tenant administrative changes (config, user roles, billing)
- Authentication events
- Authorization decisions granting cross-tenant or admin access
- Data export operations
- Any change to security posture (allowlists, IDP config)

### 5. Rewrite `immutability-classes.md`

What data must not change after writing? For SaaS:

- Audit log entries (SOC 2 audit trail)
- Customer billing records (financial reconcilability)
- Backups (ransomware resilience)
- Configuration history
- Customer-facing terms and consent records

### 6. Rewrite `data-taxonomy.md`

What field-level data classifications apply? For SaaS:

- PII per GDPR Article 4 (email, names, IP addresses, user IDs, etc.)
- Authentication credentials
- Payment data (PCI-DSS-relevant)
- Tenant configuration

### 7. Rewrite `common-patterns/<goal>.md` for all nine goals

Each file has two sections: "Common finding patterns" and "Common capability patterns." Adapt the PBM examples to your domain. The framework conventions (NIST mappings, severity calibration anchors, ATT&CK rationales) stay the same; only the *examples* and *severity rationales* change.

### 7a. Declare attack-path analyzer defaults (v1.4+)

The v1.4 `apd-attack-path-analyzer` (see [docs/attack-path-analysis.md](attack-path-analysis.md)) is activation-gated on three new optional fields in `domain.yaml`:

| Field | What it is | What the analyzer does with it |
|---|---|---|
| `crown_jewels` | List of `{pattern, description}` entries naming the assets or pipelines the analyzer should treat as enumeration sinks. The `pattern` is matched against asset names and data classifications in the intake's asset inventory (the analyzer strips a trailing `_pipeline` suffix when matching data classifications). | Becomes the default sink set when `.apd-run.yaml` does not override it. |
| `attacker_positions` | List of `{position, description}` entries naming the source nodes for enumeration — the "where the attacker starts" set. | Becomes the default source set when `.apd-run.yaml` does not override it. |
| `default_trust_boundaries` | Optional list of `{name, description}` entries naming trust boundaries the analyzer should expect to see in the intake's `asset-inventory.yaml`. Used by intake validation to warn when a known boundary is missing from a run. | Hints at the trust topology the domain treats as canonical (e.g., "internet edge", "PHI store boundary"). |

All three are optional. A domain pack that omits all three remains v1.4-compatible — the analyzer simply skips silently for runs in that domain unless the operator declares the values in `.apd-run.yaml`.

#### Worked example: `cms-medicare-claims-billing`

A fictional CMS Medicare Part B claims-billing domain pack would declare:

```yaml
# domains/cms-medicare-claims-billing/domain.yaml (excerpt)
name: cms-medicare-claims-billing
display_name: "CMS Medicare Part B Claims Billing"
version: 0.1.0
framework_compat: ">=1.4.0,<2.0.0"

crown_jewels:
  - pattern: beneficiary_phi_store
    description: "Medicare beneficiary PHI store — HIPAA breach-notification thresholds plus CMS data-use agreement obligations."
  - pattern: claim_submission_pipeline
    description: "Part B claim submission pipeline to CMS — submission integrity drives provider reimbursement and is regulator-anchored under 42 CFR Part 424."
  - pattern: era_reconciliation_pipeline
    description: "Electronic Remittance Advice reconciliation — payment-posting integrity material to provider revenue cycle."

attacker_positions:
  - position: external_internet
    description: "Untrusted external internet client — default external surface for any internet-facing CMS-edge endpoint."
  - position: compromised_provider_credential
    description: "Attacker holding a valid provider-submitter credential through phishing, credential stuffing, or insider abuse at a billing partner."
  - position: compromised_clearinghouse_integration
    description: "Attacker who has compromised a third-party clearinghouse's integration credentials."
  - position: insider_with_billing_role
    description: "An insider with a legitimate billing-ops role acting outside their minimum-necessary scope (e.g., bulk PHI export, cross-beneficiary claim queries)."

default_trust_boundaries:
  - name: internet_edge
    description: "External internet to provider-portal DMZ — TLS-terminating load balancer is the boundary."
  - name: phi_store_boundary
    description: "App-tier subnet to PHI persistence layer — KMS-mediated access required."
  - name: cms_integration_boundary
    description: "Outbound boundary to the CMS submission gateway — mutual-TLS pinned to CMS-issued certificates."
```

When a run under this domain pack omits `crown_jewels`/`attacker_positions` from `.apd-run.yaml`, the analyzer enumerates 3 jewels × 4 positions = 12 (attacker, jewel) pairs against the assembled partial graph. A run that wants to tighten the scope (e.g., focus only on the external-internet to beneficiary-PHI path) supplies an override in `.apd-run.yaml` that fully replaces the domain defaults.

### 8. Validate the pack

```bash
apd-gauntlet validate-domain saas
```

This validates `domain.yaml` against `schemas/domain.schema.json` and verifies all `includes` files exist.

### 9. Test by building the skill

```bash
apd-gauntlet build-domain-skill saas --framework-version 1.0.0
```

This writes `.claude/skills/apd-domain/SKILL.md` from your pack. Check that the generated skill contains all expected sections.

### 10. Author a sample run

Add a new directory under `examples/` demonstrating the new domain. Authoring is the longest task; the existing `examples/apd-20260601-claim-event-bus/` is a model. The sample run must validate cleanly:

```bash
apd-gauntlet validate examples/your-new-example/expected/
```

Wire it into `tests/test_examples.py` as an integration test.

## Submitting the pack

Open a PR with:

- `domains/<your-pack>/` complete.
- `examples/<your-sample-run>/` with curated expected outputs.
- An updated `tests/test_examples.py` referencing the new sample.
- Use the [domain_pack_proposal](.github/ISSUE_TEMPLATE/domain_pack_proposal.yml) issue template to open a discussion first.

CI runs `apd-gauntlet validate-domain <pack>` automatically on every PR touching a `domains/` directory.

## What stays the same across domains

- Lens definitions (apd-framework skill).
- Boundary calls between adjacent goals.
- Three analytical disciplines (evidence-pointer, block-on-ambiguity, stay-in-your-lens).
- Schema contracts.
- Validator behavior.

Only the calibration files in `domains/<name>/` change. The framework's analytical structure is domain-agnostic by design — that's what makes the pack model workable.
