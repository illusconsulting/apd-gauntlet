# Agentic AI common patterns — Authenticity

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the agentic-AI rubric, and NIST/ATT&CK mapping habits. The specialist agent's checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Self-produced agent code is emitted unsigned with no per-generation provenance binding it to the producing agent, model+prompt, and parent generation.**

- Severity: critical (autonomous code that rewrites itself and executes with full privilege; a poisoned generation persists across the self-improvement lineage, so the blast radius is cross-generation and the outcome is effectively irreversible)
- NIST: SR-4, SR-4(3), SR-11, SI-7, SI-7(15), CM-14
- Related concerns: immutability (tamper-evident history of the per-generation attestation chain); integrity (validation of the generated artifact's content before promotion); excessive-agency blast-radius=Resilient (what the authenticated code may do once executed)
- Detail: This is the hexo-ai/sia-class root-of-trust gap — OWASP LLM06 Excessive Agency compounded by LLM05 Improper Output Handling and LLM03 Supply Chain. ATLAS LLM Prompt Injection and Backdoor ML Model are the routes by which a smuggled rewrite masquerades as a legitimate generation; the surface lives at MAESTRO L3 Agent Frameworks and L1 Foundation Models. In hexo-ai/sia the Meta-Agent and Feedback Agent regenerate target_agent.py under runs/run_id/gen_n/ and that file executes arbitrary Python, yet SIA neither signs each generated artifact nor attests its (model, prompt-hash, parent-gen) provenance, so a prompt-injected rewrite is indistinguishable from an intended one. The control is an in-toto/Sigstore-style attestation per generation, signed with a per-run signing identity and verified before the Target Agent executes the artifact.

**Pattern: Agent and sub-agent workloads share a static pooled credential rather than a cryptographic per-workload identity (no SPIFFE-class identity).**

- Severity: high (the root of trust collapses to one shared secret; a compromised or rogue sub-agent is indistinguishable from a legitimate one and lateral movement across the agent graph is unbounded)
- NIST: IA-9, IA-3, IA-5(2), SC-23, AC-6
- Related concerns: ephemeral (credential lifetime and rotation of the pooled key); confidentiality (the shared key as an at-rest exposure); excessive-agency permission-lifetime=Ephemeral
- Detail: This is the foundational workload-identity gap that every per-agent authenticity claim depends on — OWASP LLM06 Excessive Agency with LLM02 Sensitive Information Disclosure as the amplifier, instantiating ATLAS Valid Accounts via credential reuse across agents. The trust boundary sits at MAESTRO L3 Agent Frameworks, L4 Deployment & Infrastructure, and L7 Agent Ecosystem. In hexo-ai/sia multiple model-provider API keys are shared across the Meta-Agent, Target Agent, and Feedback Agent with no per-role identity, so neither provider-side nor internal calls can be attributed to a specific agent role. The control is per-agent-role SPIFFE/SPIRE (or equivalent) workload identities, with provider keys brokered behind that identity (IA-9 service authentication) so each agent authenticates as itself, not as the pool.

**Pattern: Inter-agent messages, task delegations, and goal/state updates are unsigned and not sender-authenticated, enabling impersonation, Sybil identities, and goal-manipulation cascades.**

- Severity: high (a forged goal update or Sybil consensus vote propagates undetected through the agent graph and steers downstream generations; cascade across the multi-agent topology widens the blast radius)
- NIST: IA-9, SC-23, SC-8(1), SI-10
- Related concerns: integrity (the injected payload's content validation and downstream write authorization); confidentiality (encryption of the bus payload — Authenticity owns who is provably on the bus, not whether it is encrypted)
- Detail: This is the multi-agent authenticity core — trust between agents must be cryptographic, not positional. OWASP LLM01 Prompt Injection (agent-to-agent, indirect) and LLM06 Excessive Agency drive it, with LLM09 Misinformation as the forged-goal vector; ATLAS LLM Prompt Injection and Erode ML Model Integrity are the techniques, at MAESTRO L7 Agent Ecosystem, L3 Agent Frameworks, and L2 Data Operations. In hexo-ai/sia the Feedback Agent feeds rewrite instructions and evaluation signals into the generation step and the Target Agent logs to agent_execution.json; these handoffs are unsigned, so a tampered or forged feedback message (e.g. injected via the executed task's output) cannot be distinguished from authentic Feedback-Agent output. The control is a detached signature over message + nonce + parent-message-hash, made with the sender's per-agent workload identity and verified before any receiver acts — rejecting unsigned or Sybil senders.

**Pattern: Tools, plugins, and MCP servers are discovered and bound at runtime without verifying publisher signature or provenance.**

- Severity: high (a malicious or tampered tool loads with the agent's privileges and can both exfiltrate via tool calls and return forged tool descriptions that hijack the agent; trust-on-first-use extends the boundary to every bound capability)
- NIST: SR-4, SR-4(3), SR-11, SI-7, CM-7(5)
- Related concerns: integrity (typed/validated tool-output contracts and sanitization of forged tool descriptions); excessive-agency tool/write-authz=Integrity (what privileges the bound tool may exercise)
- Detail: The agent's effective trust boundary extends to every tool it loads, so tool authenticity is a root-of-trust concern — OWASP LLM03 Supply Chain, LLM06 Excessive Agency, and LLM01 Prompt Injection (tool-description / line-jumping injection). ATLAS ML Supply Chain Compromise is the technique, with LLM Prompt Injection via tool/plugin metadata; the surface is MAESTRO L7 Agent Ecosystem, L3 Agent Frameworks, and L4 Deployment & Infrastructure. In hexo-ai/sia the Claude Agent SDK + OpenHands runtime hosts a generated target_agent.py that can invoke arbitrary tools/Python, yet tools and OpenHands components load without signature or provenance verification, so a tampered dependency runs inside the sandbox with the agent's privileges. The control is signed tool/plugin manifests and verified MCP-server identity — publisher signature plus an allowlisted root — checked at bind-time rather than trusted on first use.

**Pattern: Model and dependency provenance is unattested — no SBOM or SLSA/in-toto build attestation over models, frameworks, and the agent runtime.**

- Severity: high (a swapped model endpoint, backdoored fine-tune, or poisoned framework dependency is undetectable and silently alters every downstream generation; for a self-improving loop the supply chain is its own outputs feeding the next iteration, so the effect persists cross-generation)
- NIST: SR-3, SR-4, SR-4(3), SR-11, SI-7, RA-3
- Related concerns: integrity (model/data poisoning as the alteration this provenance gap fails to detect); immutability (durable provenance records over the model and dependency lineage)
- Detail: The supply chain for an autonomous agent is its weights, its framework, and its tools, and none of it is attested — OWASP LLM03 Supply Chain and LLM04 Data & Model Poisoning. ATLAS ML Supply Chain Compromise, Backdoor ML Model, and Poison Training Data are the techniques, at MAESTRO L1 Foundation Models, L2 Data Operations, and L4 Deployment & Infrastructure. In hexo-ai/sia multiple foundation models are pulled via provider APIs and the system runs on the Claude Agent SDK + OpenHands with a Python dependency tree, but it emits no SBOM or provenance attestation for model versions or the framework/dep stack feeding each generation under runs/run_id/. The control is an SBOM plus SLSA-style build provenance covering models-by-version, framework, and dependencies, pinned and provenance-verified at run start and on any dependency change.

**Pattern: The human operator of the autonomous loop is authenticated below the required AAL (password-only or SMS-OTP) for the blast radius the loop commands.**

- Severity: high (compromising one operator hands an attacker the steering wheel of a system that writes and executes its own code — launch the loop, redirect provider keys, or promote a poisoned generation; raise to critical where that promotion is autonomous and irreversible)
- NIST: IA-2, IA-2(1), IA-2(2), IA-2(8), AC-6
- Related concerns: ephemeral (operator session/step-up token lifetime); non_repudiation (per-AAL attribution of who launched, reconfigured, or promoted)
- Detail: Operator AAL is an authenticity control on the loop's root of trust — OWASP LLM06 Excessive Agency with LLM02 Sensitive Information Disclosure (key access), instantiating ATLAS Valid Accounts via operator credential compromise at MAESTRO L6 Security & Compliance, L4 Deployment & Infrastructure, and L3 Agent Frameworks. An operator launches hexo-ai/sia runs (--max_gen, benchmark/private ground-truth config, provider keys) and would approve promotion of a self-improved target; a password+SMS surface means a single phish lets an attacker run the loop, redirect keys, or promote a poisoned generation. The control is phishing-resistant MFA at NIST SP 800-63B AAL2/AAL3 by blast radius, with step-up authentication for run-launch, max-gen change, key access, and artifact promotion.

**Pattern: Tech plan asserts agents are "authenticated" generically without specifying the identity mechanism, the root of trust, or what is signed and verified.**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Agent authentication specification — per-agent-role identity mechanism (SPIFFE/SPIRE workload identity, mTLS, signed JWT), the root of trust and its custody, what payloads/artifacts are signed (inter-agent messages, per-generation code, tool manifests), the signature algorithm and verifying key source, and the operator authentication AAL with its step-up boundaries"

## Common capability patterns

**Pattern: Per-agent-role workload identity via SPIFFE/SPIRE, with provider keys brokered behind that identity.** Scope must enumerate which agent roles are confirmed to hold distinct identities; maturity is nascent when a single pooled key remains in use anywhere, robust only when every role authenticates as itself and provider-key brokering is in evidence.

**Pattern: Signed inter-agent payloads — detached signature over message + nonce + parent-message-hash, verified by receivers before acting.** Developing when signing exists but receivers do not yet reject unsigned/Sybil senders; robust when sender-verification gates every consequential handoff and the parent-message-hash chain is enforced.

**Pattern: Per-generation attestation of self-produced code (in-toto/Sigstore) recording producing-agent, model+prompt-hash, and parent-gen-hash, verified before execution.** Maturity depends on whether the attestation is produced by the generation pipeline as part of CI/CD and whether the verification step actually gates the Target Agent's execution, not merely logs the artifact.

**Pattern: SBOM plus SLSA/in-toto build provenance over models-by-version, framework, and dependencies, verified at run start and on dependency change.** Higher maturity requires the provenance-verification step at the run-start or admission boundary plus phishing-resistant operator MFA (FIDO2/WebAuthn at AAL2/AAL3) on the loop-control surface; cross-cuts Ephemeral via signing-key and credential lifetime — mention via `related_concerns`.
