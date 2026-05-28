# MITRE Caldera — Operators

This document scopes the operator context so reviewers do not
expect production-style operational evidence.

> **Note on terminology.** In Caldera's own vocabulary, "agent"
> refers to the deployed implant (sandcat, manx). This file
> uses **operator** to mean the human running Caldera, and
> **implant** to mean the deployed agent — consistent with the
> security-tooling pack's vocabulary.

## Who operates Caldera

The operator profile for Caldera is typically:

- **A skilled red-team practitioner** — single operator, lab /
  research use, running engagements against client environments
  with documented authorisation.
- **A detection-engineering team** — small group (2-5),
  enterprise red-team or purple-team, running Caldera to
  validate sensor coverage against ATT&CK techniques.
- **A workshop instructor** — running Caldera as the live
  target for the `training` plugin's CTF, against a small
  group of attendees.
- **A MITRE researcher / contributor** — running the latest
  master against the test plugin set.

There is **no consumer-grade or B2C operator profile.** Caldera
is not a SaaS product; every operator is responsible for their
own deployment.

## Engagement profile

- **Authorised use only.** Every engagement runs against
  targets the operator has explicit, documented authorisation
  to engage (rules-of-engagement document, signed customer
  contract, internal change-approval ticket). The platform
  does not verify this; it is operator-attested.
- **Scheduled, not always-on.** Red-team engagements are
  time-bound (typically days to weeks). Detection-validation
  runs are scheduled (e.g. monthly per ATT&CK technique
  cycle). There is no "always-on" Caldera operating role
  comparable to an SRE on-call.
- **Customer-data sensitivity is real.** Engagement results
  often contain customer-environment harvested credentials,
  internal hostnames, AD domain names, configuration
  snippets, and screenshots. The platform treats this as
  generic result data with no special handling beyond the
  optional Fernet encryption-at-rest.

## Deployment patterns

- **Per-engagement instance** — the documented production
  pattern (where it exists): stand up a fresh Caldera server
  per customer, tear it down after the engagement. Avoids
  cross-engagement data contamination.
- **Long-lived team server** — common in internal
  red-teams: one Caldera serves the team for months /
  years. Accumulates harvested data across every engagement
  the team has run.
- **Air-gapped lab** — researcher or instructor use: Caldera
  runs on an isolated network with no external connectivity;
  every implant is local.
- **Strictly network-segregated** — production engagements:
  Caldera lives behind a VPN or in an operator-controlled
  bastion network, never on the public internet.

## On-call / SLO posture

- **No on-call rotation for the platform itself.** Red-team
  engagements are scheduled work; if the platform fails
  mid-engagement, the engagement pauses.
- **No SLO commitment** to anyone using the deployed
  instance. The customer being engaged is not a Caldera
  user; they are the target.
- **No customer-visible incident channel.** Customer-side
  incidents (an out-of-scope target was engaged, harvested
  data was lost, an implant misbehaved) are handled
  off-platform via the operator-customer relationship.

## Operator capabilities (in core)

The operator role in Caldera is **deploy-and-operate**, not
**administer-and-defend**:

- Bring the stack up / tear it down.
- Create / select adversary profiles, planners, fact sources.
- Launch / monitor / close operations.
- Deploy / kill implants.
- Read every operation's results.
- Configure / enable / disable plugins.
- Edit `conf/<env>.yml` (with restart).

The operator is **not** assumed to:

- Have a hardened auth pipeline available out of the box.
- Run with structured audit shipping configured.
- Have key rotation tooling.
- Have network-policy enforcement of ROE.

## Implication for the APD review

Specialist reviewers should:

- Treat the absence of an operator-driven control (MFA, key
  rotation, audit shipping, per-engagement partition,
  signed plugins) as a **structural finding against the
  artifact**, not a procedural finding against the operator.
- Recognise that no operational-evidence artifact (paged
  runbook, on-call schedule, customer-facing SLA, incident
  postmortem) will exist; absence is the evidence.
- Calibrate severity using the security-tooling pack's
  rubric: weapons-platform misuse, ROE violations, harvested
  customer-credential exposure, CFAA exposure to the operator.

## Related documents

- `runbook.md` — what the operator does at the keyboard.
- `prior-audit.md` — the inherited posture.
- `tech_plan.md` §11–12 — known security posture +
  out-of-scope items.
