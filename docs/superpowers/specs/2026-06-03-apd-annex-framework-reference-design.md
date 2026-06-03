# APD Framework Reference Annex (§11) — Design

**Goal:** Add an always-present, educational **§11 reference section** to the HTML report's **Annexes** tab that explains APD's **three pillars and nine goals** in plain language — accurate to the framework's own definitions, readable at a ~12th-grade level, useful to software engineers, information-systems & cybersecurity auditors, and risk-management professionals, and citing authoritative sources (NIST, CSA, OWASP, The Open Group, MITRE, ISO, and others) **honestly** — i.e., distinguishing what the gauntlet actually enforces from what it cites for context.

**Architecture (one sentence):** A static JSX `.annex` card numbered §11, appended to the bottom of `report-template/screens/Annexes.jsx`, that consumes the existing framework constants for pillar/goal *labels* and renders fixed explanatory prose + a Sources block using existing CSS primitives — no data-pipeline change, no new CSS, and zero completeness-gate interaction.

**Tech stack:** React/JSX report template (esbuild-precompiled), the existing report CSS design tokens, the `window.TIER_LABELS` / `GOAL_LABELS` / `TIER_GOALS` constants in `components.jsx`, Python (pytest) for the regression pin, Node toolchain for the mandatory bundle rebuild.

---

## 1. Background & source of truth

- **Canonical definitions** live in `.claude/skills/apd-framework/SKILL.md`. The render-layer constants in `report-template/components.jsx` (`GOAL_LABELS`, `TIER_LABELS`, `TIER_GOALS`, `GOAL_SHORT`) match the skill exactly. The annex consumes those constants for **labels** so the structure can never drift; the explanatory **prose** is the static content in §4 below.
- **Per-goal NIST families** are taken verbatim from `.claude/skills/apd-control-mappings/SKILL.md` (§ "NIST 800-53r5 mapping guidance").
- **Taxonomy enforcement model** is taken from `docs/taxonomy-mappings.md`: NIST 800-53r5 is required on every finding + capability; MITRE ATT&CK / CWE / D3FEND are default-on (available every run, emitted only under the high-confidence discipline); OWASP Top 10 / API / LLM and MITRE ATLAS are opt-in per run; D3FEND attaches to **capabilities**, the OWASP/CWE/ATLAS tags to **findings**.
- **"APD" is not formally expanded** anywhere in the repo. "Assure / Provide / Demonstrate" is an informal editorial gloss and must be labeled as such, never asserted as the documented expansion.

## 2. The Annexes tab today

`report-template/screens/Annexes.jsx` (Tab 06, the last tab) renders, in order:

1. **§5 Contradictions** (`data.contradictions[]`)
2. **§10 Severity disagreements** (`data.severity_disagreements[]`)
3. an **optional domain-pack caveat** (`data.domain_pack_caveat`, conditional, unnumbered)

Section numbers across the whole report run §1–§10. The new reference section takes **§11** and sits **after** all of the above (always visible).

## 3. Components / units of work

This is a small, single-plan feature. Units:

- **U1 — The §11 JSX card** in `report-template/screens/Annexes.jsx`. One self-contained block appended after the existing annex content. It:
  - renders a `.annex` card with an `.annex__head` containing `.section-eyebrow` ("§ 11 — APD FRAMEWORK") and `.section-title` ("Three pillars, nine goals");
  - renders the framework intro + acronym note in an `.empty-state--info` callout (the established pattern for explanatory prose);
  - iterates the three tiers via `window.TIER_GOALS` / `TIER_LABELS`, and the goals via `window.GOAL_LABELS`, so the **labels** come from the framework constants (no re-typed names); the per-pillar intro and per-goal prose/example/anchor are the static content from §4 keyed by goal id;
  - renders each goal's NIST family anchor as a `.pill`/`.pill--id` mono badge;
  - renders the closing "where this appears in the report" line and the **Sources** block (a list + the "What the gauntlet actually enforces" paragraph).
  - No new CSS — reuse `.annex`, `.annex__head`, `.section-eyebrow`, `.section-title`, `.empty-state--info`, `.pill`/`.pill--id`, and the standard body-prose convention (`color: var(--ink-2)`, `max-width: 72ch`, `line-height: var(--line-loose)`).
- **U2 — Bundle rebuild artifacts.** After editing U1, rebuild: `tools/apd_gauntlet/data/report-template/app.js` and `tools/apd_gauntlet/data/report-template/.source-hash` are regenerated and committed alongside the JSX.
- **U3 — Regression pin test** (pytest). A static-source/bundle assertion that the §11 section's distinctive content renders and cannot silently regress (see §6).
- **U4 — Docs note.** A short subsection in `docs/html-report.md` documenting the new §11 reference (markdownlint-clean).

**Out of scope (YAGNI):** the data-driven (`transform.py`) path; run-specific per-goal coverage numbers; a new top-level tab; any change to the completeness gate; any change to the framework definitions or the control-mappings skill.

## 4. The content (the deliverable)

The §11 section renders the following content. Pillar and goal **labels** come from the framework constants; the prose below is static. The per-goal block = the goal's lens question (taken from the framework skill — six verbatim, and three of nine lightly reworded into plain language while preserving meaning: Distributed, Authenticity, Non-Repudiation) + a 2–3 sentence plain explanation with one concrete example + the inline NIST family anchor.

### §11 — APD Framework: three pillars, nine goals

APD is a goal-based security-architecture review framework. Instead of starting from a checklist of controls, it starts from nine questions a secure system must be able to answer about itself. Those nine questions are grouped into three tiers (we call them pillars). Each pillar holds three goals — three pillars, three goals each — which gives reviewers nine distinct lenses to look through. Each goal is paired with a single lens (the one question shown below) and a defined scope (the specific properties that count as in-bounds for that lens); here we show the lens question, since that is the quickest way into each goal. The order of the pillars is deliberate and matters: a system must first be trustworthy, then able to run reliably at scale, and only then can it credibly prove what it did. The gauntlet walks the pillars in exactly that order, and later pillars are allowed to lean on the conclusions of earlier ones.

*A note on the name:* the repository does not formally expand the letters "APD." Reading "Assure / Provide / Demonstrate" out of the three pillar verbs is an informal editorial gloss, offered here only as a memory aid — it is not the framework's documented expansion.

#### Pillar 1 — Assure Trustworthiness (foundational)

*A system that cannot be trusted with its data cannot meaningfully scale or be audited, so every other pillar rests on this one.*

**Confidentiality** — *Lens: Is the data hidden from parties not authorized to see it?*
Confidentiality keeps sensitive data — health records, payment details, or secrets like passwords and API keys — readable only by the people and services allowed to read it, whether the data is moving across a network, sitting in a database, or being processed in memory. It matters because a single exposure can become a permanent, irreversible breach, and the controls that protect it (encryption, careful management of the encryption keys, data masking, narrowly scoped access) are easy to get subtly wrong — and whether a given consumer's access is scoped to the minimum necessary is something that can be reviewed against policy. For example, if a support dashboard returns a customer's full record when the agent only needed the claim status, the system has just leaked more confidential data than the task required — even though the agent was correctly logged in. `[NIST 800-53r5 · SC, AC, MP]`

**Integrity** — *Lens: Is the data what it should be, and unchanged in transit and at rest?*
Integrity ensures data is correct when it is written and stays unaltered afterward, using checks like schema validation, input validation, content hashes, and signed payloads — controls whose presence and rejection behavior can be evidenced — to catch corruption or tampering. It matters because downstream decisions — a payment, a diagnosis, a benefit eligibility ruling — are only as trustworthy as the data feeding them. For example, if a claims service accepts a malformed dollar amount because it never validated the field's type or range, a bad value can silently flow into adjudication and produce a wrong payout that no one notices until reconciliation. `[NIST 800-53r5 · SI, SC, CM]`

**Availability** — *Lens: Will the system be reachable and responsive when needed, within stated targets?*
Availability is about the system being up and answering within the response times it has promised, backed by clear uptime targets (called service-level objectives, or SLOs), spare capacity for traffic spikes, and tested disaster-recovery plans. Those plans set a recovery time objective (how fast service must come back) and a recovery point objective (how much recent data you can afford to lose) — together, RTO and RPO. It matters because a service nobody can reach is functionally the same as one that does not exist, and the cost of downtime is often measured in missed deadlines or denied care. For example, if a claim-response service promises a one-second reply but has no capacity headroom for month-end volume, it can time out exactly when load is highest — turning a paper promise into a real outage. `[NIST 800-53r5 · CP, SC, SI]`

#### Pillar 2 — Provide Scalability (operational)

*A trustworthy system that cannot be scaled, distributed, or operated under failure is fragile in production. Once a system can be trusted with data, these three goals decide whether it can actually run — spread out, survive failure, and stay clean over time — at real-world scale.*

**Distributed** — *Lens: Is the system spread across independent locations so no single failure takes it all down — and does it have a plan for when parts can't talk to each other?*
Distributed looks at the system's topology: whether it is spread across independent failure domains (multiple availability zones or regions) so that no single component takes everything down, and whether it is capable of partition tolerance — a clear, deliberate stance on what happens when parts of the network can no longer talk to each other. It matters because a system concentrated in one place has a single point of failure whose blast radius — how much goes down with it — should be a known, documented quantity. For example, if every copy of a service runs in one data center, a single power or network event in that location can take the entire service offline at once. `[NIST 800-53r5 · SC, CP, CM]`

**Resilient** — *Lens: Does the system degrade gracefully under failure and recover automatically?*
Resilient is about behavior under stress: when a dependency slows down or fails, does the system back off, retry sensibly, trip a circuit breaker (stop calling a failing service for a while), fall back to a degraded-but-useful mode, and then recover on its own — without a human paged at 3 a.m.? It matters because failures are inevitable, and the difference between a minor blip and a cascading outage is almost entirely in how the system reacts — behavior you can only trust if it has actually been exercised, not just designed. For example, if a service keeps hammering a struggling database with instant retries instead of backing off, those retries can pile on load and turn one slow dependency into a full-system collapse. `[NIST 800-53r5 · SI, CP, SC]`

**Ephemeral** — *Lens: Are credentials, infrastructure, and access short-lived by design?*
Ephemeral asks whether the things that grant power — passwords, API keys, access tokens, even the servers themselves — are intentionally short-lived, rotated automatically, and replaced rather than patched in place. It matters because anything long-lived is a standing target: the longer a credential or a server survives unchanged, the more time an attacker has to find and abuse it. For example, a service account key that was issued years ago and never rotated is a quiet liability — and an age or last-rotated date is exactly the kind of thing a review can check, because if the key ever leaked, the breach could go undetected indefinitely when nothing was ever set to expire. `[NIST 800-53r5 · IA, AC, SA]`

#### Pillar 3 — Demonstrate Auditability (accountability)

*A trustworthy, scalable system that cannot prove what it did is uninspectable and unreviewable. These three goals make a system's actions verifiable, attributable, and tamper-evident.*

**Authenticity** — *Lens: Can we actually prove — with cryptography — that a user, service, message, or piece of software is who or what it claims to be?*
Authenticity asks whether an identity can be proven with cryptography rather than merely asserted — the difference between a verified caller and a self-declared one — covering people (strong multi-factor authentication), services (mutual TLS, workload identity), messages (signed payloads), and software (proof that a program is the genuine, untampered version its publisher built, for example signed container images and supply-chain attestations using tools like Sigstore, in-toto, or SLSA). It matters because trust placed in an unverified identity is trust placed in whoever is willing to lie about it. For example, if one microservice accepts commands from another without verifying who is really calling, any process that can reach the network can impersonate a trusted caller and issue commands it should never be allowed to make. `[NIST 800-53r5 · IA, SC, SR]`

**Non-Repudiation** — *Lens: Can every important action be tied to the person or service that took it — recorded reliably enough that they can't later deny doing it?*
Non-Repudiation ensures that when something important happens, the system durably records who did it, on whose behalf, and when — with enough detail and reliability that the actor cannot later credibly deny it. It matters because accountability and most investigations depend entirely on a trustworthy record of consequential actions; if the log is missing, incomplete, or unattributed, there is no answer to "who did this?" For example, if a system lets an administrator approve a high-value payment but the audit entry omits which admin account did it, a later dispute has no way to pin the action to a person. `[NIST 800-53r5 · AU-10, IA]`

**Immutability** — *Lens: Are records that must not change protected against alteration, with detection if they are?*
Immutability protects records that must never change — audit logs, financial entries, legal-hold data — using write-once storage, hash-chained logs, and configuration-as-code so that any alteration is either prevented or at least detectable. It matters because a record an attacker (or an insider) can quietly edit is not evidence at all, no matter how complete it looked when it was written. For example, if audit logs are kept in an ordinary database that operators can update, someone covering their tracks could rewrite history with no trace — so the log proves nothing in court or in an investigation. `[NIST 800-53r5 · AU, CM, MP]`

---

*These nine goals are the backbone of the rest of this report: they drive the Findings filters, organize the Capabilities grid, and form the rows of the Coverage → APD matrix.*

#### Sources

The inline anchor on each goal points to the primary **NIST SP 800-53 Rev 5** control families for that goal. The framework also draws on the following widely adopted standards and bodies of knowledge:

- **NIST SP 800-53 Rev 5** — Security and Privacy Controls for Information Systems and Organizations
- **NIST Cybersecurity Framework (CSF) 2.0** — the Govern / Identify / Protect / Detect / Respond / Recover functions
- **NIST SP 800-160 Vol. 2 Rev. 1** — Developing Cyber-Resilient Systems
- **NIST SP 800-204** — Security Strategies for Microservices-based Application Systems
- **NIST SP 800-63B** — Digital Identity Guidelines (authenticator lifecycle and authentication assurance levels)
- **ISO/IEC 27001:2022** — information security management, including Annex A controls
- **OWASP ASVS** — Application Security Verification Standard
- **OWASP Top 10 / API Security Top 10 / LLM Top 10** — application, API, and AI-application security; **OWASP MASVS / MASTG** — the Mobile Application Security Verification Standard and Testing Guide, which inform the mobile domain pack but are not a mapped taxonomy
- **The Open Group Open FAIR** — quantitative risk analysis (useful for reasoning about RTO/RPO and availability risk)
- **CSA Cloud Controls Matrix (CCM)** — cloud-specific control framework
- **MITRE ATT&CK** — adversary tactics and techniques
- **MITRE D3FEND** — defensive countermeasures, mapped to the ATT&CK techniques they counter
- **MITRE ATLAS** — adversarial machine-learning tactics and techniques (the AI/ML counterpart to ATT&CK)
- **CWE** — Common Weakness Enumeration
- **Supply-chain attestation** — SLSA, Sigstore, in-toto; workload identity (giving each running service its own verifiable identity) via SPIFFE/SPIRE
- **IHE ATNA** — Audit Trail and Node Authentication (healthcare audit conformance)

**What the gauntlet actually enforces.** Only **NIST SP 800-53 Rev 5** is mapped on every finding and capability — it is required. **MITRE ATT&CK** is available by default but is attached only when a finding (or a capability's defense) clears a high-confidence bar — the reviewer must be able to write a specific one-sentence rationale tying the architectural detail to the technique — so an ATT&CK mapping may legitimately be absent. Two more vocabularies are available on every run under that same high-confidence discipline: **CWE** (on findings) and **MITRE D3FEND** (on capabilities, each cross-referenced to the ATT&CK technique it counters). Three more are **opt-in per run** — they apply only when declared in the run's configuration because they fit a specific surface: **OWASP Top 10 / API Top 10 / LLM Top 10** (on findings) and **MITRE ATLAS** (on findings, for adversarial-machine-learning threats). Everything in this list other than NIST 800-53r5 is a descriptive cross-reference — included so readers fluent in those vocabularies can orient themselves — **not** a statement that the gauntlet measures the system's compliance against that standard. The remaining bodies above (NIST CSF, ISO 27001, OWASP ASVS, The Open Group Open FAIR, CSA CCM, and the rest) shaped the nine goals but are not emitted as machine mappings at all.

## 5. Completeness-gate impact

**None.** The completeness gate (`tools/apd_gauntlet/synthesis/audit.py`) never inspects the Annexes tab, never enumerates section names, and never validates `parsed.keys()`. The one check that could matter — `section_errors_empty` (structural) — fires only on transform-layer exceptions; a static JSX section produces no transform output and therefore can never populate `section_errors`. No gate change and no precaution is required. (Verified by the understanding survey against `audit.py` and `docs/html-report.md`.)

## 6. Testing

- **U3 regression pin (pytest):** assert the §11 section's distinctive, static content renders and cannot silently regress. The test reads the report source (`report-template/screens/Annexes.jsx`) — and may additionally assert against the built `tools/apd_gauntlet/data/report-template/app.js` — and checks for: the section title ("Three pillars, nine goals"), the framework intro marker, the "What the gauntlet actually enforces" paragraph, and representative Sources bodies that are unique to this section (e.g., "Open FAIR", "Cloud Controls Matrix", "IHE ATNA"). It also asserts the section consumes the framework constants (references `TIER_GOALS`/`GOAL_LABELS`) so all nine goals and three pillars render from the single source of truth rather than re-typed strings. The test mirrors the project's existing static-source pin pattern (e.g., the agent/skill content tests).
- **Freshness gate:** `python tools/build_report_template.py` then `python tools/check_report_template_freshness.py` (run locally; CI runs the check). The bundle (`app.js`) and `.source-hash` must be committed with the JSX or CI fails.
- **Full regression:** `pytest -q` (whole suite), `node --check .claude/workflows/apd-gauntlet.js` (unrelated but part of the standard gate), the template-freshness check, and a shipped-run `apd-gauntlet build-report runs/<id>` to confirm the report still builds and the §11 card renders in a real run.
- **Markdownlint:** the `docs/html-report.md` note (U4) must be markdownlint-clean (MD012/MD047 etc.).

## 7. Risks & gotchas

1. **Freshness gate is mandatory and unbypassable.** Editing `Annexes.jsx` without rebuilding the bundle = red CI. The commit must bundle the JSX **plus** `tools/apd_gauntlet/data/report-template/app.js` **plus** `.source-hash`.
2. **Node toolchain required** for the rebuild; `build_report_template.py` exits 2 (graceful skip) if Node/npm are absent — but then `.source-hash` won't update and CI will catch it. Ensure Node is installed before implementing.
3. **Do not re-type framework label strings.** Consume `window.TIER_LABELS` / `GOAL_LABELS` / `TIER_GOALS` for pillar/goal names so the annex cannot drift from the framework; only the explanatory prose, examples, and NIST anchors are static (keyed by goal id).
4. **Stay accurate to the framework's own definitions.** Lens questions come from `apd-framework/SKILL.md` — six verbatim, three (Distributed, Authenticity, Non-Repudiation) lightly reworded into plain language with meaning preserved for 12th-grade readability; pillar role phrases match the skill's tier descriptions; NIST families match `apd-control-mappings/SKILL.md`; the taxonomy-enforcement nuance matches `docs/taxonomy-mappings.md`. Do **not** assert "APD = Assure/Provide/Demonstrate" as documented fact — it is an explicit gloss.
5. **Do not over-claim citation enforcement.** Only NIST 800-53r5 is required; ATT&CK/CWE/D3FEND are default-on under the high-confidence discipline; OWASP/ATLAS are per-run opt-in; everything else is educational context. The content must not imply the tool measures compliance against the educational standards.
6. **No duplicate content exists** to collide with — there is currently no glossary / "about APD" / framework reference anywhere in the report (verified across all tabs). This section is net-new.
7. **Numbering:** use **§ 11** for the eyebrow; do not renumber existing sections (the optional domain-pack caveat is unnumbered).

## 8. Acceptance criteria

- Opening any run's `report-html/index.html` → Annexes tab shows a §11 "APD Framework — three pillars, nine goals" card at the bottom, always visible, rendering all three pillars (with intros) and all nine goals (lens + plain explanation + concrete example + NIST family anchor), the closing "where this appears" line, and the Sources block including the "What the gauntlet actually enforces" paragraph.
- Content is accurate to the framework's definitions, reads at ~12th-grade level, and is honest about enforcement vs. educational citation.
- `pytest` (incl. the new pin), the template-freshness check, and a shipped-run `build-report` all pass; the committed bundle matches the JSX.
