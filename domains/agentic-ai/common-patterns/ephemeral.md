# Agentic AI common patterns — Ephemeral

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the agentic-AI rubric, and NIST/ATT&CK mapping habits. The specialist agent's checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written. Ephemeral owns the permission-lifetime facet of excessive agency: rotation cadence, TTL, expiry, and revocation, not at-rest secret protection (Confidentiality) or identity strength (Authenticity).

## Common finding patterns

**Pattern: An agent and every sub-agent it spawns hold standing broadly-scoped tool/provider credentials instead of per-task just-in-time scoped short-TTL tokens.**

- Severity: high (high autonomy plus a permanent, over-broad grant means a hijacked turn wields the full standing permission set and the credential outlives the task — blast-radius spans every provider and tool the key reaches)
- NIST: AC-6, AC-6(1), IA-5(1), IA-5(13), SC-12(1), CM-5
- Related concerns: integrity (tool/write-authz is the agency facet on the write path); resilient (blast-radius containment of the standing grant)
- Detail: This is the permission-lifetime face of OWASP LLM06 Excessive Agency, steered by LLM01 Prompt Injection (ATLAS LLM Prompt Injection, AML.T0051; LLM Jailbreak, AML.T0054). It sits at MAESTRO L3 Agent Frameworks (the credential broker that hands tokens to the agent), L4 Deployment & Infrastructure, and L7 Agent Ecosystem (the grant spans multiple external providers). In hexo-ai/sia the Meta-Agent, Target Agent, and Feedback Agent share one set of multi-provider model API keys with no per-generation scoping or TTL, so any single generation's arbitrary-Python code-exec (target_agent.py) inherits full standing agency. The lens fix is lifecycle: mint per-run_id/gen_n narrowly-scoped tokens just-in-time and let them expire when the generation completes, so a hijacked turn cannot reach beyond the task's grant or outlive it.

**Pattern: Multi-provider model and tool API keys are issued once and never rotated, with no documented cadence and no automated rotation path.**

- Severity: high (data-sensitivity and blast-radius: agent systems leak keys through many channels, and with no rotation a single leak is permanent standing model/tool access with no automatic invalidation)
- NIST: IA-5(1), IA-5(7), SC-12, SC-28, SI-7
- Related concerns: confidentiality (key management and at-rest storage of the shared credential); resilient (unbounded-consumption blast radius once a key is live indefinitely)
- Detail: OWASP LLM02 Sensitive Information Disclosure as the leak surface, compounding into LLM10 Unbounded Consumption once a leaked key bills and runs against every provider (ATLAS LLM Meta-Prompt Extraction, AML.T0056, and ML Model Extraction/Stealing, AML.T0044, as the extraction context). MAESTRO L1 Foundation Models, L2 Data Operations, and L4 Deployment & Infrastructure carry the key material. In hexo-ai/sia the keys are static for the life of the project, and agent_execution.json plus generated target code can echo or exfiltrate them; a key surfaced in any gen_n artifact stays valid indefinitely. The lens owns rotation cadence, automation, and expiry — not how the key is protected at rest, which routes to Confidentiality.

**Pattern: A generate-and-execute (code-exec) agent runs inside a long-lived, reused, or mutable compute environment instead of a fresh ephemeral sandbox torn down after each invocation.**

- Severity: high (autonomy plus reversibility: state, installed packages, dropped files, and harvested credentials persist across executions, so one injected execution implants persistence that survives into later tasks and other agents)
- NIST: SC-7, SC-39, CM-2, CM-6, SI-7
- Related concerns: integrity (output-handling of what the code returns is the adjacent write-path concern); resilient (per-exec teardown is the blast-radius boundary)
- Detail: OWASP LLM06 Excessive Agency expressed as persistence, with LLM05 Improper Output Handling as the execution sink (ATLAS LLM Prompt Injection, AML.T0051, and Backdoor ML Model, AML.T0018). MAESTRO L4 Deployment & Infrastructure (the compute boundary) and L3 Agent Frameworks (the exec broker). In hexo-ai/sia the generated target_agent.py executes arbitrary Python each generation; if generations share a working environment (installed deps, files under runs/, env vars) rather than a per-gen disposable sandbox, a reward-hacking generation can plant artifacts or credentials that persist into gen_n+1 and across runs. The lens fix is one disposable sandbox per gen_n exec with immutable-infra teardown and no writable carry-over outside the logged artifact.

**Pattern: Spawned sub-agents or peer agents inherit or are handed the parent credential with no shorter TTL and no independent revocation handle.**

- Severity: high (autonomy and blast-radius in the multi-agent case: a compromised, impersonating, or colluding sub-agent holds a credential that cannot be revoked without killing the whole system and that outlives the sub-task)
- NIST: AC-6, AC-6(1), IA-5(13), AC-12, SC-12
- Related concerns: authenticity (proving which sub-agent is genuine routes out of lens); integrity (per-sub-agent write-scope is the agency facet)
- Detail: OWASP LLM06 Excessive Agency at the permission-lifetime facet, steered by LLM01 Prompt Injection (ATLAS LLM Prompt Injection, AML.T0051; LLM Jailbreak, AML.T0054). This is the dedicated multi-agent surface at MAESTRO L7 Agent Ecosystem, with L3 Agent Frameworks (issuance point) and L6 Security & Compliance. In hexo-ai/sia the Meta/Target/Feedback stages form a multi-stage agent set sharing the same provider keys with no per-stage TTL or revocation: a hijacked Feedback Agent (which rewrites the target across generations) holds a credential indistinguishable in lifetime from the Meta-Agent's, so you cannot revoke just one stage. The lens fix is per-sub-agent ephemeral issuance with a bounded session lifetime and a targeted revocation handle — not proving the agent is genuine (Authenticity) or auditing what it did (Non-Repudiation).

**Pattern: A self-improving / autonomous loop has no fast path to revoke the credentials a single bad generation touched and no kill-switch to expire its compute.**

- Severity: critical (low reversibility and wide blast-radius: a reward-hacked, poisoned, or injected generation keeps still-valid credentials that propagate damage into subsequent generations and outward to providers, tools, and crown-jewel data)
- NIST: AC-12, IA-5(13), CP-10, SI-4(7), SC-12, RA-5
- Related concerns: resilient (detection of the misbehavior is the upstream signal); integrity (the poisoned-generation correctness violation is the adjacent root cause)
- Detail: OWASP LLM04 Data & Model Poisoning and LLM06 Excessive Agency, with LLM10 Unbounded Consumption as the propagation amplifier (ATLAS Backdoor ML Model, AML.T0018; Data Poisoning, AML.T0020). MAESTRO L5 Evaluation & Observability, L2 Data Operations, and L4 Deployment & Infrastructure. In hexo-ai/sia, target_agent.py evolves over --max_gen generations optimizing a scalar metric against a benchmark with held-out private ground truth (data/private/, evaluate.py); a generation that reward-hacks or is poisoned keeps valid provider keys and can keep touching data/private and artifacts under runs/run_id/gen_n. The lens fix is containment-by-expiry: bind each generation's secrets to that gen, auto-expire on completion, and revoke-on-detection before the next gen starts — distinct from detecting the misbehavior (Resilient) or auditing it (Non-Repudiation).

**Pattern: Agent sessions, conversational/long-term memory, and autonomous task loops have no maximum lifetime, no turn/iteration budget, and no idle expiry.**

- Severity: medium (autonomy with deferred blast-radius: stale memory and never-expiring sessions keep injected instructions, harvested secrets, and accumulated agency alive indefinitely, and an unbounded loop is itself an agency-plus-consumption hazard)
- NIST: AC-12, AC-12(1), SC-23, SI-12, AU-11
- Related concerns: integrity (content-trust of memory entries routes out); resilient (consumption rate-limiting framed as availability)
- Detail: OWASP LLM10 Unbounded Consumption and LLM06 Excessive Agency, with LLM08 Vector & Embedding Weaknesses where stale memory persists (ATLAS LLM Prompt Injection, AML.T0051). MAESTRO L3 Agent Frameworks (loop control), L2 Data Operations (memory at rest), and L4 Deployment & Infrastructure. In hexo-ai/sia the loop is bounded by --max_gen — a partial ephemeral control — but within and after a run, agent_execution.json logs and per-gen memory/artifacts under runs/run_id/gen_n have no TTL, so secrets and injected context captured in one generation's log persist and can be re-ingested by later generations. The lens fix is a TTL on session/memory artifacts plus an explicit idle/turn budget inside each generation, not just the cross-generation cap.

**Pattern: Tech plan references provider keys or agent credentials without per-secret-class rotation cadence, TTL, automated rotation mechanism, or revocation-on-compromise procedure.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Credential-lifecycle policy — per-secret-class rotation cadence and mechanism (automated vs. manual), token/session TTL for agents and spawned sub-agents, break-glass and revocation-on-compromise procedure, generation/loop kill-switch behavior, and TTL on session/memory artifacts under the run directory"

## Common capability patterns

**Pattern: Just-in-time, per-task, narrowly-scoped tool/provider credentials minted on demand with a short TTL and automatic expiry at task or generation end.** Nascent if asserted in the tech plan only; developing once a broker/issuance mechanism is named; robust when per-run_id/gen_n token issuance and expiry are in evidence with scope confined to the step.

**Pattern: Ephemeral disposable sandbox per code-execution with immutable-infra teardown and no writable carry-over between invocations.** Maturity rises from designed (tech plan asserts per-exec sandboxing) to implemented when the per-gen sandbox lifecycle and teardown are configured in evidence.

**Pattern: Fast scoped revocation plus loop/compute kill-switch that expires a single generation's secrets and halts its compute on detection.** Robust maturity requires runbook evidence of the revocation path and a tested kill-switch; designed maturity from tech plan only; cross-cuts Resilient for the detection signal that triggers it — mention via `related_concerns`.

**Pattern: Automated provider-key rotation on a defined cadence with revocation-after-leak and no manual standing-key step.** Caveats expected on which provider keys are confirmed onboard and whether the rotation is automated end-to-end versus a documented-but-manual procedure.
