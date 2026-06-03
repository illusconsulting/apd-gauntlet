# APD Framework Reference Annex (§11) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an always-present, educational **§11 "APD Framework — three pillars, nine goals"** card to the bottom of the HTML report's Annexes tab, explaining APD's 3 pillars and 9 goals in plain language with honest citations.

**Architecture:** A static JSX section appended to `report-template/screens/Annexes.jsx`. Pillar/goal **labels** come from the existing framework constants (`TIER_LABELS`, `TIER_GOALS`, `GOAL_LABELS`, exposed as window globals by `components.jsx`); the explanatory **prose**, examples, and NIST anchors are static maps defined at the top of `Annexes.jsx`. No data-pipeline change, no new CSS, zero completeness-gate interaction. The precompiled bundle is rebuilt with `python tools/build_report_template.py` and committed alongside the source.

**Tech Stack:** React/JSX (esbuild-precompiled bundle), existing report CSS design tokens, Python/pytest for the regression pins, Node 26 + npm for the mandatory bundle rebuild.

**Authoritative content source:** the approved spec `docs/superpowers/specs/2026-06-03-apd-annex-framework-reference-design.md` §4. The prose embedded in this plan is that content verbatim — use it exactly.

---

## File Structure

- **`report-template/screens/Annexes.jsx`** (modify) — add the static content maps + the §11 `<section>` at the end of the `Annexes` function. Sole responsibility: render the Annexes tab (existing contradictions/disagreements/caveat + the new framework reference).
- **`tools/apd_gauntlet/data/report-template/app.js`** + **`.source-hash`** (regenerated build artifacts) — produced by `python tools/build_report_template.py`; committed with the JSX so the freshness gate passes.
- **`tests/unit/report/test_annex_framework_reference.py`** (create) — static-source pin asserting the §11 content + constant-driven structure can't silently regress.
- **`docs/html-report.md`** (modify) — short subsection documenting the new §11 reference.
- **`tests/unit/report/test_annex_framework_reference.py`** also carries a one-line doc-presence assertion (kept in the same module to avoid a second test file).

**Established idioms to follow (verified in the existing file):**
- Components/constants are referenced as **bare globals** (e.g. the existing code uses `CopyPill`, `SeverityPill`, `React.Fragment` bare; `components.jsx` does `Object.assign(window, { GOAL_LABELS, TIER_LABELS, TIER_GOALS, ... })`). So `TIER_LABELS`, `TIER_GOALS`, `GOAL_LABELS` are referenced bare in `Annexes.jsx`.
- Sections are `<section className="annex">` with a `<header className="annex__head">` containing a `.section-eyebrow` + an `<h3>` + a `.pill`.
- Long-form prose uses inline style `{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65 }`.
- The callout pattern for explanatory prose is `className="empty-state--info"` (defined at `report-template/screens.css:891`).
- ID-style mono badges use `className="pill pill--id"` (`report-template/styles.css:434`).
- File begins with `/* eslint-disable */` — no lint gate on the JSX.

---

## Task 1: §11 framework-reference section in Annexes.jsx (+ rebuild + pin test)

**Files:**
- Modify: `report-template/screens/Annexes.jsx`
- Regenerate + commit: `tools/apd_gauntlet/data/report-template/app.js`, `tools/apd_gauntlet/data/report-template/.source-hash`
- Test: `tests/unit/report/test_annex_framework_reference.py`

- [ ] **Step 1: Write the failing pin test**

Create `tests/unit/report/test_annex_framework_reference.py`:

```python
"""Static-source pin for the §11 APD framework-reference annex.

The §11 section is static JSX in report-template/screens/Annexes.jsx; the
bundle-freshness gate (test_tier3_bundle_freshness) separately guarantees the
shipped app.js matches this source, so pinning the source is sufficient to
prove the educational content cannot silently regress.
"""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
ANNEXES = REPO / "report-template" / "screens" / "Annexes.jsx"
HTML_DOC = REPO / "docs" / "html-report.md"


def _src() -> str:
    return ANNEXES.read_text(encoding="utf-8")


def test_section_heading_and_numbering_present() -> None:
    src = _src()
    assert "§ 11 — APD framework reference" in src
    assert "Three pillars, nine goals" in src


def test_structure_is_constant_driven() -> None:
    # Labels must come from the framework constants, not re-typed strings,
    # so the annex can never drift from the framework definition.
    src = _src()
    assert "TIER_GOALS" in src
    assert "TIER_LABELS" in src
    assert "GOAL_LABELS" in src
    assert "APD_TIER_ORDER" in src


def test_all_nine_goal_details_present() -> None:
    src = _src()
    for goal_key in (
        "confidentiality", "integrity", "availability",
        "distributed", "resilient", "ephemeral",
        "authenticity", "non_repudiation", "immutability",
    ):
        assert f"{goal_key}:" in src, f"missing goal detail entry: {goal_key}"
    # Every goal block shows its lens question.
    assert src.count("lens:") == 9


def test_per_goal_nist_family_anchors_present() -> None:
    src = _src()
    for anchor in (
        "NIST 800-53r5 · SC, AC, MP",   # confidentiality
        "NIST 800-53r5 · SI, SC, CM",   # integrity
        "NIST 800-53r5 · CP, SC, SI",   # availability
        "NIST 800-53r5 · SC, CP, CM",   # distributed
        "NIST 800-53r5 · SI, CP, SC",   # resilient
        "NIST 800-53r5 · IA, AC, SA",   # ephemeral
        "NIST 800-53r5 · IA, SC, SR",   # authenticity
        "NIST 800-53r5 · AU-10, IA",    # non-repudiation
        "NIST 800-53r5 · AU, CM, MP",   # immutability
    ):
        assert anchor in src, f"missing NIST anchor: {anchor}"


def test_acronym_caveat_present() -> None:
    # APD must NOT be asserted as a documented expansion.
    src = _src()
    assert "informal editorial gloss" in src
    assert "not the framework's documented expansion" in src


def test_sources_and_enforcement_note_present() -> None:
    src = _src()
    # Distinctive Sources bodies (the user-named bodies + a couple unique ones).
    for body in (
        "NIST Cybersecurity Framework (CSF) 2.0",
        "ISO/IEC 27001:2022",
        "OWASP ASVS",
        "The Open Group Open FAIR",
        "CSA Cloud Controls Matrix",
        "IHE ATNA",
    ):
        assert body in src, f"missing Sources body: {body}"
    # The honest enforcement note, with the default-on vs opt-in nuance.
    assert "What the gauntlet actually enforces" in src
    assert "opt-in per run" in src
    assert "not a statement that the gauntlet measures the system's compliance" in src


def test_report_cross_reference_line_present() -> None:
    src = _src()
    assert "drive the Findings filters" in src
    assert "Coverage → APD matrix" in src


def test_html_report_doc_mentions_framework_annex() -> None:
    doc = HTML_DOC.read_text(encoding="utf-8")
    assert "three pillars" in doc.lower() and "nine goals" in doc.lower()
```

- [ ] **Step 2: Run the pin test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/report/test_annex_framework_reference.py -q`
Expected: FAIL — most assertions fail because the §11 content is not yet in `Annexes.jsx` (and the doc test fails until Task 2). This confirms the test has teeth.

- [ ] **Step 3: Add the static content maps to `Annexes.jsx`**

In `report-template/screens/Annexes.jsx`, immediately after the leading comment lines (after line 2, `// Annexes screen …`) and **before** `function Annexes(...)`, insert these module-level constants verbatim:

```jsx
// §11 framework-reference content. Pillar/goal LABELS come from the framework
// constants (TIER_LABELS / TIER_GOALS / GOAL_LABELS in components.jsx); the
// prose below is the static educational content (spec §4). Verb prefixes are
// the canonical SKILL.md tier-name prefixes ("Assure Trustworthiness", …); the
// "APD" acronym itself is NOT a documented expansion (see the note rendered below).
const APD_TIER_ORDER = ["trustworthiness", "scalability", "auditability"];
const APD_PILLAR_VERB = {
  trustworthiness: "Assure",
  scalability: "Provide",
  auditability: "Demonstrate",
};
const APD_PILLAR_TAG = {
  trustworthiness: "foundational",
  scalability: "operational",
  auditability: "accountability",
};
const APD_PILLAR_INTRO = {
  trustworthiness:
    "A system that cannot be trusted with its data cannot meaningfully scale or be audited, so every other pillar rests on this one.",
  scalability:
    "A trustworthy system that cannot be scaled, distributed, or operated under failure is fragile in production. Once a system can be trusted with data, these three goals decide whether it can actually run — spread out, survive failure, and stay clean over time — at real-world scale.",
  auditability:
    "A trustworthy, scalable system that cannot prove what it did is uninspectable and unreviewable. These three goals make a system's actions verifiable, attributable, and tamper-evident.",
};
const APD_GOAL_DETAIL = {
  confidentiality: {
    lens: "Is the data hidden from parties not authorized to see it?",
    body:
      "Confidentiality keeps sensitive data — health records, payment details, or secrets like passwords and API keys — readable only by the people and services allowed to read it, whether the data is moving across a network, sitting in a database, or being processed in memory. It matters because a single exposure can become a permanent, irreversible breach, and the controls that protect it (encryption, careful management of the encryption keys, data masking, narrowly scoped access) are easy to get subtly wrong — and whether a given consumer's access is scoped to the minimum necessary is something that can be reviewed against policy. For example, if a support dashboard returns a customer's full record when the agent only needed the claim status, the system has just leaked more confidential data than the task required — even though the agent was correctly logged in.",
    nist: "NIST 800-53r5 · SC, AC, MP",
  },
  integrity: {
    lens: "Is the data what it should be, and unchanged in transit and at rest?",
    body:
      "Integrity ensures data is correct when it is written and stays unaltered afterward, using checks like schema validation, input validation, content hashes, and signed payloads — controls whose presence and rejection behavior can be evidenced — to catch corruption or tampering. It matters because downstream decisions — a payment, a diagnosis, a benefit eligibility ruling — are only as trustworthy as the data feeding them. For example, if a claims service accepts a malformed dollar amount because it never validated the field's type or range, a bad value can silently flow into adjudication and produce a wrong payout that no one notices until reconciliation.",
    nist: "NIST 800-53r5 · SI, SC, CM",
  },
  availability: {
    lens: "Will the system be reachable and responsive when needed, within stated targets?",
    body:
      "Availability is about the system being up and answering within the response times it has promised, backed by clear uptime targets (called service-level objectives, or SLOs), spare capacity for traffic spikes, and tested disaster-recovery plans. Those plans set a recovery time objective (how fast service must come back) and a recovery point objective (how much recent data you can afford to lose) — together, RTO and RPO. It matters because a service nobody can reach is functionally the same as one that does not exist, and the cost of downtime is often measured in missed deadlines or denied care. For example, if a claim-response service promises a one-second reply but has no capacity headroom for month-end volume, it can time out exactly when load is highest — turning a paper promise into a real outage.",
    nist: "NIST 800-53r5 · CP, SC, SI",
  },
  distributed: {
    lens:
      "Is the system spread across independent locations so no single failure takes it all down — and does it have a plan for when parts can't talk to each other?",
    body:
      "Distributed looks at the system's topology: whether it is spread across independent failure domains (multiple availability zones or regions) so that no single component takes everything down, and whether it is capable of partition tolerance — a clear, deliberate stance on what happens when parts of the network can no longer talk to each other. It matters because a system concentrated in one place has a single point of failure whose blast radius — how much goes down with it — should be a known, documented quantity. For example, if every copy of a service runs in one data center, a single power or network event in that location can take the entire service offline at once.",
    nist: "NIST 800-53r5 · SC, CP, CM",
  },
  resilient: {
    lens: "Does the system degrade gracefully under failure and recover automatically?",
    body:
      "Resilient is about behavior under stress: when a dependency slows down or fails, does the system back off, retry sensibly, trip a circuit breaker (stop calling a failing service for a while), fall back to a degraded-but-useful mode, and then recover on its own — without a human paged at 3 a.m.? It matters because failures are inevitable, and the difference between a minor blip and a cascading outage is almost entirely in how the system reacts — behavior you can only trust if it has actually been exercised, not just designed. For example, if a service keeps hammering a struggling database with instant retries instead of backing off, those retries can pile on load and turn one slow dependency into a full-system collapse.",
    nist: "NIST 800-53r5 · SI, CP, SC",
  },
  ephemeral: {
    lens: "Are credentials, infrastructure, and access short-lived by design?",
    body:
      "Ephemeral asks whether the things that grant power — passwords, API keys, access tokens, even the servers themselves — are intentionally short-lived, rotated automatically, and replaced rather than patched in place. It matters because anything long-lived is a standing target: the longer a credential or a server survives unchanged, the more time an attacker has to find and abuse it. For example, a service account key that was issued years ago and never rotated is a quiet liability — and an age or last-rotated date is exactly the kind of thing a review can check, because if the key ever leaked, the breach could go undetected indefinitely when nothing was ever set to expire.",
    nist: "NIST 800-53r5 · IA, AC, SA",
  },
  authenticity: {
    lens:
      "Can we actually prove — with cryptography — that a user, service, message, or piece of software is who or what it claims to be?",
    body:
      "Authenticity asks whether an identity can be proven with cryptography rather than merely asserted — the difference between a verified caller and a self-declared one — covering people (strong multi-factor authentication), services (mutual TLS, workload identity), messages (signed payloads), and software (proof that a program is the genuine, untampered version its publisher built, for example signed container images and supply-chain attestations using tools like Sigstore, in-toto, or SLSA). It matters because trust placed in an unverified identity is trust placed in whoever is willing to lie about it. For example, if one microservice accepts commands from another without verifying who is really calling, any process that can reach the network can impersonate a trusted caller and issue commands it should never be allowed to make.",
    nist: "NIST 800-53r5 · IA, SC, SR",
  },
  non_repudiation: {
    lens:
      "Can every important action be tied to the person or service that took it — recorded reliably enough that they can't later deny doing it?",
    body:
      "Non-Repudiation ensures that when something important happens, the system durably records who did it, on whose behalf, and when — with enough detail and reliability that the actor cannot later credibly deny it. It matters because accountability and most investigations depend entirely on a trustworthy record of consequential actions; if the log is missing, incomplete, or unattributed, there is no answer to \"who did this?\" For example, if a system lets an administrator approve a high-value payment but the audit entry omits which admin account did it, a later dispute has no way to pin the action to a person.",
    nist: "NIST 800-53r5 · AU-10, IA",
  },
  immutability: {
    lens: "Are records that must not change protected against alteration, with detection if they are?",
    body:
      "Immutability protects records that must never change — audit logs, financial entries, legal-hold data — using write-once storage, hash-chained logs, and configuration-as-code so that any alteration is either prevented or at least detectable. It matters because a record an attacker (or an insider) can quietly edit is not evidence at all, no matter how complete it looked when it was written. For example, if audit logs are kept in an ordinary database that operators can update, someone covering their tracks could rewrite history with no trace — so the log proves nothing in court or in an investigation.",
    nist: "NIST 800-53r5 · AU, CM, MP",
  },
};
```

- [ ] **Step 4: Render the §11 section inside `Annexes`**

In `report-template/screens/Annexes.jsx`, inside the `Annexes` function's returned `<div>`, insert the following `<section>` **immediately before the closing `</div>`** (i.e., after the `{data.domain_pack_caveat && ( … )}` block, currently around line 117):

```jsx
      {/* §11 — APD framework reference (static, always present) */}
      <section className="annex">
        <header className="annex__head">
          <div>
            <div className="section-eyebrow" style={{ margin: 0 }}>§ 11 — APD framework reference</div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>Three pillars, nine goals</h3>
          </div>
          <span className="pill">3 tiers · 9 goals</span>
        </header>

        <div className="empty-state--info" style={{ maxWidth: "72ch" }}>
          <p style={{ margin: 0, lineHeight: 1.65 }}>
            APD is a goal-based security-architecture review framework. Instead of starting from a checklist of controls, it starts from nine questions a secure system must be able to answer about itself. Those nine questions are grouped into three tiers (we call them pillars). Each pillar holds three goals — three pillars, three goals each — which gives reviewers nine distinct lenses to look through. Each goal is paired with a single lens (the one question shown below) and a defined scope (the specific properties that count as in-bounds for that lens); here we show the lens question, since that is the quickest way into each goal. The order of the pillars is deliberate and matters: a system must first be trustworthy, then able to run reliably at scale, and only then can it credibly prove what it did. The gauntlet walks the pillars in exactly that order, and later pillars are allowed to lean on the conclusions of earlier ones.
          </p>
          <p style={{ marginTop: "var(--space-3)", marginBottom: 0, fontStyle: "italic", lineHeight: 1.65 }}>
            A note on the name: the repository does not formally expand the letters "APD." Reading "Assure / Provide / Demonstrate" out of the three pillar verbs is an informal editorial gloss, offered here only as a memory aid — it is not the framework's documented expansion.
          </p>
        </div>

        {APD_TIER_ORDER.map((tier, i) => (
          <div key={tier} style={{ marginTop: "var(--space-5)" }}>
            <h4 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-lg)", marginBottom: 4 }}>
              Pillar {i + 1} — {APD_PILLAR_VERB[tier]} {TIER_LABELS[tier]}{" "}
              <span style={{ color: "var(--ink-3)", fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}>({APD_PILLAR_TAG[tier]})</span>
            </h4>
            <p style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65, fontStyle: "italic", marginBottom: "var(--space-3)" }}>
              {APD_PILLAR_INTRO[tier]}
            </p>
            {TIER_GOALS[tier].map((goal) => (
              <div key={goal} style={{ marginBottom: "var(--space-4)", maxWidth: "72ch" }}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "var(--space-2)" }}>
                  <strong style={{ fontSize: "var(--text-md)" }}>{GOAL_LABELS[goal]}</strong>
                  <span className="pill pill--id" style={{ fontSize: "var(--text-xs)", whiteSpace: "nowrap" }}>{APD_GOAL_DETAIL[goal].nist}</span>
                </div>
                <div style={{ color: "var(--ink-2)", fontStyle: "italic", margin: "2px 0" }}>
                  Lens: {APD_GOAL_DETAIL[goal].lens}
                </div>
                <p style={{ color: "var(--ink-2)", lineHeight: 1.65, margin: 0 }}>
                  {APD_GOAL_DETAIL[goal].body}
                </p>
              </div>
            ))}
          </div>
        ))}

        <p style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65, fontStyle: "italic", marginTop: "var(--space-4)" }}>
          These nine goals are the backbone of the rest of this report: they drive the Findings filters, organize the Capabilities grid, and form the rows of the Coverage → APD matrix.
        </p>

        <div style={{ marginTop: "var(--space-5)" }}>
          <h4 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-lg)", marginBottom: "var(--space-2)" }}>Sources</h4>
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65, marginTop: 0 }}>
            The inline anchor on each goal points to the primary NIST SP 800-53 Rev 5 control families for that goal. The framework also draws on the following widely adopted standards and bodies of knowledge:
          </p>
          <ul style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.6 }}>
            <li><strong>NIST SP 800-53 Rev 5</strong> — Security and Privacy Controls for Information Systems and Organizations</li>
            <li><strong>NIST Cybersecurity Framework (CSF) 2.0</strong> — the Govern / Identify / Protect / Detect / Respond / Recover functions</li>
            <li><strong>NIST SP 800-160 Vol. 2 Rev. 1</strong> — Developing Cyber-Resilient Systems</li>
            <li><strong>NIST SP 800-204</strong> — Security Strategies for Microservices-based Application Systems</li>
            <li><strong>NIST SP 800-63B</strong> — Digital Identity Guidelines (authenticator lifecycle and authentication assurance levels)</li>
            <li><strong>ISO/IEC 27001:2022</strong> — information security management, including Annex A controls</li>
            <li><strong>OWASP ASVS</strong> — Application Security Verification Standard</li>
            <li><strong>OWASP Top 10 / API Security Top 10 / LLM Top 10</strong> — application, API, and AI-application security; <strong>OWASP MASVS / MASTG</strong> — the Mobile Application Security Verification Standard and Testing Guide, which inform the mobile domain pack but are not a mapped taxonomy</li>
            <li><strong>The Open Group Open FAIR</strong> — quantitative risk analysis (useful for reasoning about RTO/RPO and availability risk)</li>
            <li><strong>CSA Cloud Controls Matrix (CCM)</strong> — cloud-specific control framework</li>
            <li><strong>MITRE ATT&amp;CK</strong> — adversary tactics and techniques</li>
            <li><strong>MITRE D3FEND</strong> — defensive countermeasures, mapped to the ATT&amp;CK techniques they counter</li>
            <li><strong>MITRE ATLAS</strong> — adversarial machine-learning tactics and techniques (the AI/ML counterpart to ATT&amp;CK)</li>
            <li><strong>CWE</strong> — Common Weakness Enumeration</li>
            <li><strong>Supply-chain attestation</strong> — SLSA, Sigstore, in-toto; workload identity (giving each running service its own verifiable identity) via SPIFFE/SPIRE</li>
            <li><strong>IHE ATNA</strong> — Audit Trail and Node Authentication (healthcare audit conformance)</li>
          </ul>
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65 }}>
            <strong>What the gauntlet actually enforces.</strong> Only NIST SP 800-53 Rev 5 is mapped on every finding and capability — it is required. MITRE ATT&amp;CK is available by default but is attached only when a finding (or a capability's defense) clears a high-confidence bar — the reviewer must be able to write a specific one-sentence rationale tying the architectural detail to the technique — so an ATT&amp;CK mapping may legitimately be absent. Two more vocabularies are available on every run under that same high-confidence discipline: CWE (on findings) and MITRE D3FEND (on capabilities, each cross-referenced to the ATT&amp;CK technique it counters). Three more are opt-in per run — they apply only when declared in the run's configuration because they fit a specific surface: OWASP Top 10 / API Top 10 / LLM Top 10 (on findings) and MITRE ATLAS (on findings, for adversarial-machine-learning threats). Everything in this list other than NIST 800-53r5 is a descriptive cross-reference — included so readers fluent in those vocabularies can orient themselves — and is not a statement that the gauntlet measures the system's compliance against that standard. The remaining bodies above (NIST CSF, ISO 27001, OWASP ASVS, The Open Group Open FAIR, CSA CCM, and the rest) shaped the nine goals but are not emitted as machine mappings at all.
          </p>
        </div>
      </section>
```

- [ ] **Step 5: Rebuild the precompiled bundle**

Run: `python tools/build_report_template.py`
Expected: it runs `node build.mjs` in `report-template/.build/` and regenerates `tools/apd_gauntlet/data/report-template/app.js` plus `.source-hash`. Confirm the bundle changed:

Run: `git status --short tools/apd_gauntlet/data/report-template/`
Expected: `app.js` and `.source-hash` show as modified (`M`).

If `node`/`npm` are missing the script prints a skip message and exits non-zero — in that case STOP and report BLOCKED (the freshness gate will fail without a fresh bundle). Node 26 + npm are expected to be present.

- [ ] **Step 6: Run the pin test + the freshness gate to verify green**

Run: `.venv/bin/python -m pytest tests/unit/report/test_annex_framework_reference.py tests/unit/report/test_tier3_bundle_freshness.py -q`
Expected: the §11 source pins PASS (the doc test still FAILS until Task 2 — that single failure is expected here), and the bundle-freshness test PASSES (bundle matches source).

> Note: `test_html_report_doc_mentions_framework_annex` will fail until Task 2 lands the doc note. That is the only acceptable failure at this step.

- [ ] **Step 7: Commit**

```bash
git add report-template/screens/Annexes.jsx \
        tools/apd_gauntlet/data/report-template/app.js \
        tools/apd_gauntlet/data/report-template/.source-hash \
        tests/unit/report/test_annex_framework_reference.py
git commit -m "$(cat <<'EOF'
feat(report): add §11 APD framework reference annex (3 pillars, 9 goals)

Static, always-present educational section at the bottom of the Annexes tab:
each of the nine goals with its lens question, a plain-language explanation and
concrete example, and its primary NIST 800-53r5 families; a consolidated Sources
list; and an honest enforcement note (NIST required / ATT&CK·CWE·D3FEND default-on
high-confidence / OWASP·ATLAS opt-in / others educational). Labels come from the
framework constants so the structure can't drift. Bundle rebuilt.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Document the §11 reference in `docs/html-report.md`

**Files:**
- Modify: `docs/html-report.md`
- Test: `tests/unit/report/test_annex_framework_reference.py` (the `test_html_report_doc_mentions_framework_annex` assertion already written in Task 1 — it goes green here)

- [ ] **Step 1: Confirm the doc assertion currently fails**

Run: `.venv/bin/python -m pytest "tests/unit/report/test_annex_framework_reference.py::test_html_report_doc_mentions_framework_annex" -q`
Expected: FAIL (the doc does not yet mention the framework annex).

- [ ] **Step 2: Add the doc subsection**

In `docs/html-report.md`, the bundle description near the top says the report "contains six tabs (Overview, Findings, Capabilities, Coverage, Attack paths, Annexes)". Find the section that describes the Annexes tab content (search for "Annexes — " or the "Empty-state interpretation" section that discusses Annexes). Add a new `##`-level subsection **after** the "Empty-state interpretation" section and **before** "Contributing template changes":

```markdown
## APD framework reference (Annexes §11)

The Annexes tab ends with a static **§11 — APD framework reference** card titled
"Three pillars, nine goals". It is always present (it does not depend on run data)
and explains the framework's **three pillars and nine goals** for readers new to
APD — software engineers, information-systems and cybersecurity auditors, and
risk-management professionals.

Each goal is shown with its lens question, a plain-language explanation and a
concrete example, and its primary NIST SP 800-53 Rev 5 control families. A
consolidated **Sources** block lists the standards the framework draws on (NIST
800-53r5, NIST CSF 2.0, NIST SP 800-160 Vol. 2, NIST SP 800-204, NIST SP 800-63B,
ISO/IEC 27001:2022, OWASP ASVS / Top 10 / API / LLM, The Open Group Open FAIR,
CSA Cloud Controls Matrix, MITRE ATT&CK / D3FEND / ATLAS, CWE, and others).

The card is deliberate about **what the gauntlet enforces versus what it cites for
context**: only NIST 800-53r5 is mapped on every finding and capability; MITRE
ATT&CK, CWE, and D3FEND are available on every run under a high-confidence
mapping discipline; OWASP Top 10 / API / LLM and MITRE ATLAS are opt-in per run;
and the remaining bodies are educational cross-references, not compliance
measurements.

The content is static JSX in `report-template/screens/Annexes.jsx` (labels are
pulled from the framework constants in `components.jsx`), so it does not interact
with the report completeness gate. As with any template change, edits require
rebuilding the bundle (`python tools/build_report_template.py`) and committing the
regenerated `app.js` and `.source-hash`.
```

- [ ] **Step 3: Verify markdownlint is clean on the doc**

Run: `npx -y markdownlint-cli2 docs/html-report.md`
Expected: `Summary: 0 error(s)`. Fix any MD012 (consecutive blank lines), MD047 (single trailing newline), MD032 (lists surrounded by blanks), or MD013 (line length, only if the repo enforces it — match the surrounding lines' width) before proceeding.

- [ ] **Step 4: Verify the doc test now passes (and the whole pin module is green)**

Run: `.venv/bin/python -m pytest tests/unit/report/test_annex_framework_reference.py -q`
Expected: ALL pass (including `test_html_report_doc_mentions_framework_annex`).

- [ ] **Step 5: Commit**

```bash
git add docs/html-report.md
git commit -m "$(cat <<'EOF'
docs(html-report): document the §11 APD framework reference annex

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Cross-cutting verification gate (no commit)

**Files:** none (verification-only).

- [ ] **Step 1: Full Python test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all tests pass — including the new `tests/unit/report/test_annex_framework_reference.py`, the bundle-freshness gate (`test_tier3_bundle_freshness.py`), and the golden/integration report tests.

- [ ] **Step 2: ruff + mypy (the test file is the only new Python)**

Run: `.venv/bin/python -m ruff check tests/unit/report/test_annex_framework_reference.py && .venv/bin/python -m mypy tools/apd_gauntlet/`
Expected: `All checks passed!` and `Success: no issues found`.

- [ ] **Step 3: Bundle freshness check (the CI gate)**

Run: `python tools/check_report_template_freshness.py`
Expected: exit 0 — the committed `.source-hash` agrees with `compute_source_hash()` over `report-template/`. (If it fails, the bundle was not rebuilt/committed in Task 1 Step 5 — go back and rebuild.)

- [ ] **Step 4: markdownlint over the touched markdown**

Run: `npx -y markdownlint-cli2 docs/html-report.md`
Expected: `Summary: 0 error(s)`.

- [ ] **Step 5: Build a real run's report and eyeball §11**

Run: `python -m apd_gauntlet.cli build-report runs/apd-20260527-crapi-owasp-api-top10`
Expected: exit 0; `runs/apd-20260527-crapi-owasp-api-top10/40-synthesis/report-html/index.html` opens with an Annexes tab whose last card is "§ 11 — APD framework reference / Three pillars, nine goals", rendering all three pillars and all nine goals plus the Sources block. (This is a manual visual confirmation; the build exiting 0 is the automated gate. Do not commit anything generated under `runs/*/report-html/` — it is gitignored.)

- [ ] **Step 6: Confirm clean tree**

Run: `git status --short`
Expected: no unexpected modifications beyond gitignored run artifacts. If anything under `tools/apd_gauntlet/data/report-template/` is modified here, the bundle drifted — rebuild and amend Task 1's commit.

---

## Self-Review

**1. Spec coverage** (against `docs/superpowers/specs/2026-06-03-apd-annex-framework-reference-design.md`):
- §3 U1 (the §11 JSX card) → Task 1 Steps 3–4. ✓
- §3 U2 (bundle rebuild artifacts) → Task 1 Step 5 + commit Step 7. ✓
- §3 U3 (regression pin) → Task 1 Step 1 test + Task 3 Step 1. ✓
- §3 U4 (docs note) → Task 2. ✓
- §4 content (3 pillar intros + 9 goal explainers with verbatim lens + plain explanation + example + NIST anchor + closing line + Sources + enforcement note) → embedded verbatim in Task 1 Steps 3–4. ✓
- §5 completeness-gate (no interaction) → confirmed by Task 3 Step 1 full suite (no gate change made). ✓
- §6 testing (pin, freshness, full regression, markdownlint, shipped-run build) → Task 1 Step 6 + Task 2 Step 3 + Task 3. ✓
- §7 risks (freshness rebuild, Node, don't re-type strings, accuracy, no over-claim, numbering §11) → handled: constants-driven structure (Step 3 comment + `test_structure_is_constant_driven`), rebuild (Step 5), §11 numbering, verbatim content from spec. ✓

**2. Placeholder scan:** No "TBD"/"add error handling"/"similar to". Every code step shows full code; every run step shows the command and expected output. ✓

**3. Type/name consistency:** Constant names (`APD_TIER_ORDER`, `APD_PILLAR_VERB`, `APD_PILLAR_TAG`, `APD_PILLAR_INTRO`, `APD_GOAL_DETAIL`) and goal keys (`confidentiality` … `non_repudiation` … `immutability`) match between the maps (Step 3), the render (Step 4), and the pin test (Step 1). The NIST anchor strings in the test match the `nist:` values in the maps exactly. Tier keys (`trustworthiness`/`scalability`/`auditability`) match `TIER_GOALS`/`TIER_LABELS` in `components.jsx`. ✓
