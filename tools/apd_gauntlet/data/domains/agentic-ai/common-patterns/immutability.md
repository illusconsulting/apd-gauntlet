# Agentic AI common patterns — Immutability

These are illustrative templates, not all-inclusive. Use them to calibrate analytical style, severity assignment per the agentic-AI rubric, and NIST/ATT&CK mapping habits. The specialist agent's checklist still drives the actual analysis — this file calibrates how findings and capabilities should look once written.

## Common finding patterns

**Pattern: Per-generation lineage / provenance chain (parent->child agent, rewrite diff, scoring metric) written to a mutable store with no append-only or hash-chaining enforcement.**

- Severity: high (a self-improving loop can rewrite or drop a generation record so a poisoned/backdoored generation appears descended from a benign ancestor; once the evolution history is mutable, cross-generation incident reconstruction is impossible)
- NIST: AU-9, AU-9(2), AU-9(3), AU-10, SI-7, SR-4(3)
- Related concerns: non_repudiation (whether the lineage record exists and carries trustworthy per-agent attribution); integrity (write authorization on the lineage store — the blast-radius facet of LLM06 excessive agency)
- Detail: OWASP LLM04 (Data & Model Poisoning) and LLM03 (Supply Chain) expressed as a tampered ancestry graph, with LLM06 as the agency that reaches the store; grounds in ATLAS Backdoor ML Model and Data Poisoning, MAESTRO L3 Agent Frameworks (the generation graph) and L2 Data Operations (lineage as data). hexo-ai/sia writes the gen_n provenance under runs/run_id/gen_n/ as plain mutable files, so a later generation can back-edit or silently drop an ancestor; the immutability control is an append-only, hash-chained lineage where gen_n's head commits to gen_{n-1}'s head.

**Pattern: Runtime execution / decision trace — tool invocations, arguments, executed code, sub-agent dispatches — logged to a mutable substrate with no WORM enforcement and no externally anchored hash chain.**

- Severity: high (after a harmful consequential action the trace can be altered or truncated to erase the offending tool call; a mutable action ledger is a functionally absent ledger for autonomous-action accountability, and the irreversible blast radius of executed code makes this load-bearing)
- NIST: AU-9, AU-9(2), AU-9(3), AU-10, AU-11, SI-7
- Related concerns: non_repudiation (existence and attribution of the action ledger); integrity (tool/write-authorization on the trace path — the write-authz facet of LLM06)
- Detail: OWASP LLM06 (Excessive Agency) and LLM05 (Improper Output Handling), with LLM01 prompt injection as the originating trigger whose trace must survive; grounds in ATLAS LLM Prompt Injection and LLM Jailbreak, MAESTRO L5 Evaluation & Observability (the trace is the observability substrate) and L3 Agent Frameworks (tool-call mediation produces it). hexo-ai/sia logs the executed run to agent_execution.json, the only record of what arbitrary Python ran and which keys it touched; it must be append-only and hash-chained with the chain-head anchored outside the run directory so a self-modifying target cannot rewrite its own trace before the Feedback Agent scores it.

**Pattern: Optimization-loop metric, benchmark scores, and held-out eval outputs stored mutably and/or computed where the optimized agent can write them — no WORM substrate, no compute-time hash commit.**

- Severity: critical (a self-improving system rewarded for a higher scalar metric has a direct incentive to edit its own recorded scores, overwrite a prior generation's results to fabricate monotonic improvement, or mutate the held-out ground truth so the benchmark always passes; reward-hacking via record mutation defeats every downstream trust claim about the agent)
- NIST: AU-9, AU-9(3), SI-7, SI-7(1), AC-6, RA-5
- Related concerns: integrity (correctness of the objective store at write time, the data-sensitivity facet of LLM06); confidentiality (read-scoping data/private/ so the agent cannot read the answers); non_repudiation (attribution of who wrote each score)
- Detail: OWASP LLM04 (poisoning the eval/ground-truth), LLM09 (fabricated success metrics), and LLM06; grounds in ATLAS Data Poisoning of the evaluation set and Evade ML Model, MAESTRO L5 Evaluation & Observability (eval integrity is the core L5 concern) and L2 Data Operations (held-out ground truth as protected data). hexo-ai/sia computes a scalar metric via evaluate.py against private ground truth in data/private/; eval results per gen_n and the ground truth must live on a WORM substrate the Target Agent's executed code cannot write to, with scores hash-committed at compute time so a later generation cannot rewrite gen_{n-1} scores to invent improvement.

**Pattern: Agent prompt/policy/tool-manifest and safety guardrails not held as signed, version-historied config-as-code, with no drift detection comparing declared guardrails against the runtime-loaded set.**

- Severity: high (a prompt-injection payload, a self-modifying agent, or an operator can silently widen tool permissions or disable a guardrail at runtime while the declared policy still looks safe, or rewrite the policy-repo history to erase that a dangerous capability was ever enabled; declared-vs-actual divergence widens autonomy undetected)
- NIST: CM-2, CM-2(2), CM-3, CM-3(1), CM-6, SI-7, AC-6
- Related concerns: integrity (the permission-scope facet of LLM06 — which capabilities a generation may load); authenticity (the signing-key trust root behind signed commits/manifests); ephemeral (time-bounded validity of a granted capability)
- Detail: OWASP LLM06, LLM01 (Prompt Injection), LLM07 (System Prompt Leakage as the drift target), and LLM03 (tool-manifest provenance); grounds in ATLAS LLM Prompt Injection, LLM Jailbreak, and LLM Meta-Prompt Extraction, MAESTRO L3 Agent Frameworks (tool manifest + agent policy), L6 Security & Compliance (guardrail governance), and L4 Deployment & Infrastructure (runtime-loaded config). In hexo-ai/sia the generated target_agent.py's effective tool/permission surface (arbitrary Python, multiple provider keys) IS the runtime guardrail state; the declared manifest and the Claude Agent SDK + OpenHands sandbox config must be version-historied with signed commits and a drift check that compares declared-allowed capability against what each generated target actually loads.

**Pattern: Held-out ground truth, golden agent baselines, and run archives backed up without object-lock / vault-lock immutability — a single privileged credential or a self-modifying agent can delete or encrypt all copies.**

- Severity: critical (this destroys the only authoritative reference needed to detect that the optimization was gamed, roll back to a known-good generation, and prove what the benchmark and baselines were; a ransomware-class, anti-rollback exposure that is irreversible and specific to autonomous loops that can act on infrastructure)
- NIST: CP-9, CP-9(1), CP-9(8), MP-4, SI-7, AC-6
- Related concerns: resilient (the blast-radius facet of LLM06 — an in-loop attacker wiping live data and its backups); confidentiality (encryption-at-rest of the backed-up ground truth); availability (whether restore actually works to RTO)
- Detail: OWASP LLM04 (destroying clean reference data), LLM10 (an uncontrolled loop can also exhaust/wipe storage), and LLM06; grounds in ATLAS Data Poisoning and Erode ML Model Integrity, MAESTRO L2 Data Operations (ground-truth datastore), L4 Deployment & Infrastructure (backup substrate), and L1 Foundation Models (golden baseline checkpoints). hexo-ai/sia's data/private/ ground truth and best-scoring checkpoints under runs/ must be backed up to an object-lock (compliance-mode) / vault-lock tier no run-time credential or generated target can downgrade or delete, because target_agent.py executes arbitrary code with provider keys and could otherwise wipe both the live ground truth and its backups.

**Pattern: Persistent agent memory and shared multi-agent state (vector store, scratchpad/blackboard, episodic memory, shared queue) snapshotted without integrity sealing or version history.**

- Severity: high (one agent can silently mutate or back-date shared memory another agent relies on — memory poisoning, goal-manipulation cascades, impersonation via rewritten context records — and without immutable hash-sealed snapshots there is no point-in-time state to diff against to prove tampering or restore a clean baseline)
- NIST: SI-7, SI-7(1), AU-9, CP-9, CP-9(1), SC-28
- Related concerns: integrity (write-path validation of memory content, the data-sensitivity facet of LLM06); non_repudiation (attribution of which agent wrote each memory revision); confidentiality (encryption of the snapshot store)
- Detail: OWASP LLM04 (memory poisoning), LLM08 (Vector & Embedding Weaknesses), LLM01 (injected content persisted into memory), and LLM06; grounds in ATLAS Data Poisoning, persisted/indirect LLM Prompt Injection, and Backdoor ML Model, MAESTRO L2 Data Operations (memory/vector store), L7 Agent Ecosystem (inter-agent shared state, impersonation, goal-cascade), and L3 Agent Frameworks (memory subsystem). hexo-ai/sia is a serial generation loop, so this partially applies: the cross-generation carry-over (prior agent_execution.json, accumulated runs/ artifacts a new generation reads as memory) should be snapshot-sealed and hash-versioned so a generation cannot rewrite the state a successor trusts; full peer-to-peer shared-blackboard poisoning is n/a to SIA's current topology but dominant for general multi-agent systems.

**Pattern: Retention duration, legal-hold, and lock-mode not specified for the immutable record classes (lineage, traces, eval results, golden baselines).**

- Disposition: uncertainty or blocked
- prerequisite_evidence: "Immutability/retention policy — per-record-class WORM substrate and lock mode (compliance vs governance), retention floor with regulatory or incident-reconstruction citation, chain-head anchoring location for hash-chained logs, legal-hold override procedure, and the credential boundary that cannot downgrade or delete the locked tier"

## Common capability patterns

**Pattern: Append-only, hash-chained generation lineage where gen_n's chain-head commits to gen_{n-1}'s head, with the head anchored outside the run directory.** Maturity cue: nascent from a design note; developing once the chain is written and verified per generation; robust once an external anchor (separate account/KMS or timestamp authority) and a chain-verification gate before promotion are evidenced. Cross-cuts Non-Repudiation; mention via related_concerns.

**Pattern: WORM-locked execution/decision trace (agent_execution.json and cross-agent action ledger) on an append-only substrate with an externally anchored hash chain the executing agent cannot reach.** Maturity cue: developing when append-only is enforced on the trace store; robust when the chain-head is anchored in a separate trust domain and the self-modifying target provably has no write path to it.

**Pattern: Object-lock / vault-lock (compliance mode) on backups of held-out ground truth and golden agent baselines, with retention at or above the incident-reconstruction floor and no run-time credential able to downgrade the lock.** Scope must enumerate which buckets/vaults are confirmed, the lock mode, and the retention period; higher maturity requires evidence that no agent or pipeline credential holds the lock-downgrade or bypass-governance permission.

**Pattern: Guardrail config-as-code with signed commits, protected history, and a declared-vs-actual drift check comparing each generation's loaded capability surface against the signed policy.** Maturity ladder: designed from the tech plan; implemented once the signed manifest and per-agent roster are in the repo; operationalized once the drift-detection-and-alert loop is evidenced firing on a capability that exceeds the declared policy.
