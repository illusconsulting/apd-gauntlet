/* eslint-disable */
// Annexes screen — contradictions + severity disagreements (and link back to strengths)

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

function Annexes({ data, onOpenFinding }) {
  const active = (data.meta && data.meta.active_taxonomies) || [];
  const masActive = active.includes("masvs") || active.includes("maswe");
  return (
    <div>
      <div className="section-eyebrow">§ 5 + § 10 — Annexes</div>
      <h2 className="section-title">Contradictions &amp; severity disagreements</h2>

      <section className="annex">
        <header className="annex__head">
          <div>
            <div className="section-eyebrow" style={{ margin: 0 }}>§ 5 — Contradiction annex</div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>Finding ⇄ Capability conflicts</h3>
          </div>
          <span className="pill">{data.contradictions.length} surfaced</span>
        </header>
        {data.contradictions.length > 0 && (
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
            Cases where a finding asserts a property is absent and a capability confirms it is present, or vice versa. In all three cases here, the recommended disposition is <strong>scope clarification of the capability</strong>, not capability downgrade — these indicate language that could be over-read by a reviewer outside the architectural context.
          </p>
        )}
        {data.contradictions.length === 0 && (
          <p className="empty-state">
            {data.contradictions_notes
              ? data.contradictions_notes
              : "No contradictions surfaced."}
          </p>
        )}

        {data.contradictions.map((c) => (
          <div key={c.id} className="contradiction">
            <div className="contradiction__id"><CopyPill value={c.id} /></div>
            <div className="contradiction__col">
              <div className="contradiction__label">Finding asserts</div>
              <CopyPill value={c.finding.id} />
              <div className="contradiction__assertion">"{c.finding.assertion}"</div>
            </div>
            <div className="contradiction__col">
              <div className="contradiction__label">Capability asserts</div>
              {(c.capability.ids || [c.capability.id]).map((cid) => (
                <CopyPill key={cid} value={cid} />
              ))}
              <div className="contradiction__assertion">"{c.capability.assertion}"</div>
            </div>
            <div className="contradiction__resolution">
              <div className="contradiction__label" style={{ marginBottom: 4 }}>Comparison &amp; resolution</div>
              <div>{c.comparison}</div>
              <div style={{ marginTop: "var(--space-2)", color: "var(--ink)" }}><strong>→</strong> {c.resolution}</div>
            </div>
          </div>
        ))}
      </section>

      <section className="annex">
        <header className="annex__head">
          <div>
            <div className="section-eyebrow" style={{ margin: 0 }}>§ 10 — Severity disagreement annex</div>
            <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>Within-cluster lens disagreements</h3>
          </div>
          <span className="pill">{data.severity_disagreements.length} clusters</span>
        </header>
        {data.severity_disagreements.length > 0 && (
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
            Records where two agents agreed on the concern but disagreed on severity. The merged finding takes the higher severity per the synthesis rule; the disagreement is preserved here for transparency.
          </p>
        )}
        {data.severity_disagreements.length === 0 && (
          <p className="empty-state">
            {data.severity_disagreements_notes
              ? data.severity_disagreements_notes
              : "No severity disagreements surfaced."}
          </p>
        )}

        {data.severity_disagreements.map((d) => (
          <div key={d.id} className="sev-disagreement">
            <header className="sev-disagreement__head">
              <span
                className="pill pill--id pill--clickable"
                onClick={() => onOpenFinding(d.id)}
                style={{ fontSize: "var(--text-sm)" }}
              >{d.id} →</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>
                chosen → <SeverityPill value={d.chosen} />
              </span>
            </header>
            <dl className="sev-disagreement__lenses">
              {d.agents.map((a) => (
                <React.Fragment key={a.lens}>
                  <dt>{a.lens}</dt>
                  <dd><SeverityPill value={a.severity} /></dd>
                </React.Fragment>
              ))}
            </dl>
            <div className="sev-disagreement__rationale">"{d.rationale}"</div>
          </div>
        ))}
      </section>

      {/* Domain-pack calibration caveat */}
      {data.domain_pack_caveat && (
        <section className="annex">
          <header className="annex__head">
            <div>
              <div className="section-eyebrow" style={{ margin: 0 }}>Domain-pack calibration caveat</div>
              <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", marginTop: 4 }}>{data.domain_pack_caveat.title || "Domain-pack scope"}</h3>
            </div>
            <span className="pill" style={{ borderColor: "var(--sev-medium)", color: "var(--sev-medium)" }}>
              quick-path tradeoff
            </span>
          </header>
          <p style={{ color: "var(--ink-2)", maxWidth: "72ch", lineHeight: 1.65 }}>
            {data.domain_pack_caveat.body}
          </p>
        </section>
      )}

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
            <li><strong>OWASP Top 10 / API Security Top 10 / LLM Top 10</strong> — application, API, and AI-application security; <strong>OWASP MASVS / MASWE</strong> — {masActive
              ? "the Mobile Application Security Verification Standard (MASVS) and Mobile Application Security Weakness Enumeration (MASWE), mapped on findings (and MASVS on capabilities) for this run"
              : "the Mobile Application Security Verification Standard and Testing Guide, which inform the mobile domain pack but are not a mapped taxonomy"}</li>
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
            <strong>What the gauntlet actually enforces.</strong> Only NIST SP 800-53 Rev 5 is mapped on every finding and capability — it is required. MITRE ATT&amp;CK is available by default but is attached only when a finding (or a capability's defense) clears a high-confidence bar — the reviewer must be able to write a specific one-sentence rationale tying the architectural detail to the technique — so an ATT&amp;CK mapping may legitimately be absent. Two more vocabularies are available on every run under that same high-confidence discipline: CWE (on findings) and MITRE D3FEND (on capabilities, each cross-referenced to the ATT&amp;CK technique it counters). {masActive
              ? "Five more are opt-in per run — they apply only when declared in the run's configuration because they fit a specific surface: OWASP Top 10 / API Top 10 / LLM Top 10 (on findings), MITRE ATLAS (on findings, for adversarial-machine-learning threats), OWASP MASVS (on findings and capabilities), and OWASP MASWE (on findings, for mobile-application weaknesses)."
              : "Three more are opt-in per run — they apply only when declared in the run's configuration because they fit a specific surface: OWASP Top 10 / API Top 10 / LLM Top 10 (on findings) and MITRE ATLAS (on findings, for adversarial-machine-learning threats)."}{" "}Everything in this list other than NIST 800-53r5 is a descriptive cross-reference — included so readers fluent in those vocabularies can orient themselves — and is not a statement that the gauntlet measures the system's compliance against that standard. The remaining bodies above (NIST CSF, ISO 27001, OWASP ASVS, The Open Group Open FAIR, CSA CCM, and the rest) shaped the nine goals but are not emitted as machine mappings at all.
          </p>
        </div>
      </section>
    </div>
  );
}

window.Annexes = Annexes;
