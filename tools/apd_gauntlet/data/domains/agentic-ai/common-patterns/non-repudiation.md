# Agentic AI common patterns — Non-Repudiation

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the agentic-AI rubric, and NIST/ATT&CK mapping habits. The specialist agent's checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Audit covers only the LLM request/response pair, not the full agentic action surface — tool/function calls, self-modification writes, provider-key use, sub-agent delegation, and eval-data reads go unrecorded.**

- Severity: high (every unaudited consequential-action class leaves an autonomous act that cannot be attributed or reconstructed; under the rubric, autonomy plus cross-generation persistence raises a coverage gap that defeats breach reconstruction)
- NIST: AU-2, AU-3, AU-3(1), AU-12, CM-3
- Related concerns: integrity (the side-effecting tool/write authorization facet of excessive agency that this trail must record), ephemeral (key-use events whose recording proves credential exercise)
- Detail: this is the dominant real-world non-repudiation gap on agentic systems — OWASP LLM06 Excessive Agency and LLM05 Improper Output Handling widen the act surface while LLM10 Unbounded Consumption multiplies its volume. The act that must stay reconstructable is the ATLAS LLM Prompt Injection outcome (a shelled-out command, a file write, a key use), so audit-completeness is a defender-evidence gap and emits no ATT&CK technique here. This sits at MAESTRO L3 Agent Frameworks (tool-call/orchestration surface) and L5 Evaluation & Observability (the trace plane). In hexo-ai/sia the Target Agent executes arbitrary Python and logs to agent_execution.json, but the consequential surface is broader: every tool call, each provider-API-key use, every write that produces target_agent.py, and every read under data/private/ via evaluate.py — the check enumerates that surface against runs/run_id/gen_n/ artifacts rather than trusting the task-level prompt/response log.

**Pattern: Audit entries attribute actions to a shared "system" actor or one service account — the acting principal, the delegation chain, and the generation/run context are absent.**

- Severity: high (in multi-agent and self-improving loops many distinct principals act — Meta/Target/Feedback agents, delegated sub-agents, the human operator, a specific generation — and a shared actor field defeats dispute resolution, insider-action attribution, and goal-manipulation-cascade tracing across the agent graph)
- NIST: AU-3, AU-3(1), AU-10, AC-3, IA-2
- Related concerns: authenticity (the attribution field is only as strong as the agent/sub-agent identity proofing that populates it; weak identity yields weak attribution), confidentiality (the read-scope facet of excessive agency that a per-principal trail makes attributable)
- Detail: OWASP LLM06 Excessive Agency and LLM09 Misinformation (mis-attributed agent outputs) ground the threat; the ATLAS LLM Jailbreak / Prompt Injection case where an injected instruction is executed by a sub-agent must be traceable back to the responsible principal, spanning MAESTRO L3 Agent Frameworks, L7 Agent Ecosystem (inter-agent delegation, impersonation, Sybil identities), and L6 Security & Compliance. In hexo-ai/sia each artifact under runs/run_id/gen_n/ should carry which agent role (meta/target/feedback), which generation n (from --max_gen), and which provider produced each step — "who modified the target" is generation-scoped, so the entry must name the Feedback Agent and the generation rather than just "sia," and sub-agent delegation in the OpenHands / Claude-Agent-SDK substrate must record the delegating principal.

**Pattern: Decision/action traces are neither hash-chained per stream nor entry-signed — a missing or reordered action is undetectable and an actor can plausibly deny or repudiate an entry.**

- Severity: high (without a gap-evident, attributable chain the cross-generation decision trace — the gen_0 to gen_n rewrites and the tool calls within each — cannot be proven complete or bound to its producer, so a deleted or forged self-modification leaves no trace)
- NIST: AU-10, AU-10(1), SC-12, SI-7, SI-7(1)
- Related concerns: immutability (tamper-resistance of the stored chain over time is that goal's lens; here the concern is the chain and signature existing so completeness and attribution are provable), authenticity (the signing-key trust root behind the entry signatures)
- Detail: OWASP LLM05 Improper Output Handling and LLM06 Excessive Agency ground the need; the ATLAS Erode ML Model Integrity / log-tampering-to-repudiate case is resisted by anchoring chain heads externally, at MAESTRO L5 Evaluation & Observability and L6 Security & Compliance. In hexo-ai/sia the cross-generation decision trace should be hash-chained per run with entries signed and chain heads anchored outside the runs/ tree (a separate trust domain), making "generation k's rewrite is missing or forged" detectable and binding each rewrite to the Feedback Agent that produced it.

**Pattern: Timestamps are unsynchronized local clocks — no NTP discipline, drift bounds, monotonic ordering, or behavior-on-time-source-failure across the loop and across generations.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Audit time-source specification — NTP topology and time-source authority, drift bounds, behavior on time-source failure, timestamp precision (millisecond/microsecond), and the monotonic per-run sequence anchor used to order concurrent agents and sub-agents"

**Pattern: Ordering across concurrent agents/sub-agents and across generations relies on wall-clock alone, with no monotonic logical sequence anchor — the true causal sequence of consequential actions cannot be established.**

- Severity: medium (ordering reliability is the basis for causal reconstruction; without it you cannot establish which tool call preceded which self-modification or whether a sub-agent acted before or after a delegation, materially delaying and weakening dispute resolution rather than directly enabling an irreversible act)
- NIST: AU-8, AU-8(1), AU-10, SC-45
- Related concerns: distributed (the clock/NTP topology and cross-agent ordering anchor are a topology fact this trail consumes), resilient (blast-radius isolation across concurrent agents whose actions this ordering reconstructs)
- Detail: OWASP LLM06 Excessive Agency and LLM09 Misinformation (a false ordering narrative) ground the concern; ATLAS has no specific time-source technique, so ordering reliability is a defender-evidence property that supports reconstruction of any logged technique rather than emitting an ATT&CK mapping. This spans MAESTRO L4 Deployment & Infrastructure (clock/NTP topology), L5 Evaluation & Observability, and L7 Agent Ecosystem (cross-agent ordering). In hexo-ai/sia, ordering across generations under runs/run_id/gen_n/ and across the tool calls inside a generation needs a reliable time source plus a monotonic per-run sequence number; concurrency across a multi-agent topology requires the logical ordering anchor in addition to synchronized wall-clock time.

**Pattern: The principals that run the loop — or the agents themselves, including a self-modifying Feedback Agent — can read or write their own audit logs, with no segregation of duties and no audit-of-audit-access.**

- Severity: high (when actor and auditor are the same principal, attribution can be silently curated; a self-improving agent can learn to suppress records of its own consequential actions, and an insider can identify what was observed and adjust behavior)
- NIST: AU-9, AU-9(4), AU-9(6), AC-5, AC-6
- Related concerns: integrity (the agent's own write scope over the trace plane is the side-effecting authorization facet of excessive agency), confidentiality (audit-content sensitivity inheritance drives who may read the trace), immutability (whether records can be altered once written is that goal's lens; here the concern is who is authorized to touch the stream and that those touches are themselves recorded)
- Detail: OWASP LLM06 Excessive Agency and LLM02 Sensitive Information Disclosure ground the threat; the ATLAS LLM Meta-Prompt Extraction / observability-plane-tampering case where an agent reads or curates its own traces to repudiate actions is the adversarial path, at MAESTRO L5 Evaluation & Observability, L6 Security & Compliance, and L3 Agent Frameworks. In hexo-ai/sia the Target/Feedback Agent has filesystem and code-execution reach; if its execution context can write or prune runs/run_id/gen_n/ logs or agent_execution.json there is no SoD between actor and auditor — the pattern requires audit sinks outside agent-writable scope and that any read of the trace plane is recorded independently, which is critical because a self-improving agent could otherwise optimize toward concealing its own records.

**Pattern: Audit shipping is fire-and-forget to a single broker/sink with no buffer — silent loss occurs exactly during the high-activity windows (runaway loop, unbounded-consumption episode, cascade) that most need reconstruction.**

- Severity: high (audit generated on the same host/process that executes consequential actions does not survive the agent host's failure, kill-for-budget, or reclamation; durable off-host delivery is itself the precondition for any post-incident reconstruction)
- NIST: AU-4, AU-5, AU-5(1), AU-5(2), CP-9
- Related concerns: resilient (audit-buffer behavior and back-pressure under broker outage), availability (the audit-pipeline SLO and uptime target), distributed (the broker/sink topology)
- Detail: OWASP LLM10 Unbounded Consumption and LLM06 Excessive Agency ground the threat; there is no specific ATLAS technique — reliable shipping preserves the evidence base for any logged technique, so this is a defender-evidence property — at MAESTRO L4 Deployment & Infrastructure (audit pipeline/broker topology) and L5 Evaluation & Observability. In hexo-ai/sia artifacts persist under a local runs/ tree, so if a generation crashes, is killed for exceeding budget, or the host is reclaimed, locally-buffered audit can be lost; the check is whether agent_execution.json and per-generation traces are shipped to a durable sink outside the run host with delivery acknowledgement and back-pressure handling rather than relying on the local filesystem surviving the run.

## Common capability patterns

**Pattern: Per-action audit across the full consequential surface — actor, resource, action, purpose, and outcome captured per record for each tool call, self-modification write, provider-key use, sub-agent delegation, and eval-data read.** Scope must enumerate covered action classes against the consequential-actions list; nascent when only the prompt/response pair is logged, robust when each class (including self-modification of target_agent.py) is captured per-record with caveats for any out-of-evidence surface.

**Pattern: Cryptographically signed, hash-chained decision/action traces per run, with chain heads anchored outside the run tree in a separate trust domain.** Nascent when the chain is described in a tech plan only, developing when implemented in code/IaC, robust when chain-verification at audit-read time and external anchoring of heads are evidenced — binding each generation's rewrite to its producer.

**Pattern: Per-entry attribution naming the acting principal, the delegation chain, and the generation/run context, with audit-read gated by a role separate from operational and agent roles and read events themselves audited (SoD).** Cross-cuts Authenticity for the strength of the underlying agent/sub-agent identity and Confidentiality for audit-content sensitivity; mention via related_concerns. Higher maturity requires audit sinks demonstrably outside agent-writable scope so a self-modifying agent cannot curate its own trail.

**Pattern: Time-source policy with NTP topology specified, drift bounds enforced, fallback to a secondary stratum on primary failure, and a monotonic per-run sequence anchor for cross-agent ordering.** Higher maturity requires monitoring evidence on drift and on time-source-availability events themselves being audited, plus durable off-host audit shipping with acknowledgement so the ordered record survives the run host.
