# Domain-Pack Authoring Docs Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the two domain-pack authoring guides into complete references (dissecting the `agentic-ai` pack), surgically retire the `apd-orchestrator` references and refresh the CLI reference, and add a staleness-guard test.

**Architecture:** Documentation overhaul — no application code. The deterministic "tests" are `markdownlint-cli2` (the full CI glob), a new staleness-guard pytest, and accuracy against the real `agentic-ai` pack on `main`. Author content TDD-style: write the guard test first (it fails), then make each doc change turn its assertions green while keeping markdownlint clean.

**Tech Stack:** Markdown content; `markdownlint-cli2`; one pytest guard (`pathlib` string assertions, mirroring `tests/test_doc_improving_domain_packs.py`).

---

## Sources of truth

- **Spec:** `docs/superpowers/specs/2026-05-31-domain-pack-docs-overhaul-design.md` — the section outlines, the corrected `domain`/`domains` finding, the surgical-fix list, the acceptance bar.
- **The worked-example pack (read it to dissect accurately):** `domains/agentic-ai/` — `domain.yaml` (6 crown jewels: `tool_execution_capability`, `model_provider_credentials`, `training_and_eval_data`, `agent_memory_store`, `self_improvement_loop`, `orchestration_control_plane`; 6 attacker positions; 6 trust boundaries; anchors EU AI Act / NIST AI RMF / ISO 42001 / 800-53r5), `severity-rubric.md`, the three support files, and `common-patterns/<goal>.md` (the canonical `**Pattern:**` format — read `common-patterns/integrity.md` for the R2/R3 examples).
- **Mechanics specs:** `docs/superpowers/specs/2026-05-30-multi-domain-runs-design.md` (Subsystem A — the merge engine) and `docs/superpowers/specs/2026-05-30-domain-improvement-capture-design.md` (Subsystem B — the improvement loop).
- **Schema for the enum:** `schemas/domain-improvement.schema.json` — the nine `improvement_type` values (exact strings in Task 1).
- **Doc-test to mirror:** `tests/test_doc_improving_domain_packs.py` (already pins `draft-domain-improvements` in the improving guide + the adapting→improving link; do not duplicate those).

## Conventions

- **Gate per doc task:** `npx --yes markdownlint-cli2 "<the-file>"` → `0 error(s)`, plus the relevant guard-test assertions.
- **`.markdownlint.json`:** dash bullets, blank lines around lists/headings/fences, no trailing-colon headings, single H1. `MD013` (line length) is off; `MD024` siblings-only; `MD040` (fenced-code language) off.
- **Accuracy rule:** every `agentic-ai` example in the guides must match the pack on `main` verbatim (file names, the crown-jewel/attacker-position keys above, the `**Pattern:**` format). When in doubt, read the pack file.
- **`domain` vs `domains` (verified):** the CLI flag is `--domain` (repeatable: `--domain pbm --domain api-security`); `--domains-dir` is the separate packs-directory flag; `build-domain-skill`/`validate-domain` take **positional** space-separated pack names; the run-config key is `domains:` (a list). There is no `--domain`→`--domains` rename.

## File structure

| File | Action | Task |
|------|--------|------|
| `tests/test_doc_domain_pack_authoring.py` | Create (staleness-guard) | 1 |
| `docs/architecture.md` | Modify (orchestrator row) | 2 |
| `README.md` | Modify (orchestrator invocation) | 2 |
| `docs/running-the-gauntlet.md` | Modify (orchestrator section + CLI reference + multi-domain example) | 2 |
| `docs/adapting-to-other-domains.md` | Rebuild (9-section authoring guide) | 3 |
| `docs/improving-domain-packs.md` | Rebuild (improvement loop + 9 types) | 4 |
| — | Final verification | 5 |

---

### Task 1: Staleness-guard test (write first; it must fail)

**Files:**

- Create: `tests/test_doc_domain_pack_authoring.py`

- [ ] **Step 1: Write the test**

```python
"""Staleness + completeness guards for the domain-pack authoring docs (sub-project 2)."""
from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# Top-level user-facing docs only (NOT docs/superpowers/** historical artifacts).
USER_DOCS = sorted(DOCS.glob("*.md")) + [REPO / "README.md"]

# The exact improvement_type enum from schemas/domain-improvement.schema.json.
IMPROVEMENT_TYPES = [
    "missing_severity_clause", "missing_crown_jewel", "missing_attacker_position",
    "missing_trust_boundary", "missing_consequential_action", "missing_immutability_class",
    "missing_data_class", "missing_common_pattern", "missing_regulatory_anchor",
]


def test_no_apd_orchestrator_in_user_docs():
    for doc in USER_DOCS:
        assert "apd-orchestrator" not in doc.read_text(encoding="utf-8"), (
            f"{doc.name} still references the retired apd-orchestrator"
        )


def test_running_guide_cli_reference_lists_draft_command():
    text = (DOCS / "running-the-gauntlet.md").read_text(encoding="utf-8")
    assert "draft-domain-improvements" in text, (
        "running-the-gauntlet.md CLI reference must list draft-domain-improvements"
    )


def test_adapting_guide_dissects_agentic_ai_pack():
    text = (DOCS / "adapting-to-other-domains.md").read_text(encoding="utf-8")
    assert "agentic-ai" in text, "the authoring guide must use the agentic-ai pack"


def test_improving_guide_enumerates_all_improvement_types():
    text = (DOCS / "improving-domain-packs.md").read_text(encoding="utf-8")
    missing = [t for t in IMPROVEMENT_TYPES if t not in text]
    assert not missing, f"improving guide missing improvement_types: {missing}"
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python3 -m pytest tests/test_doc_domain_pack_authoring.py -v`
Expected: `test_no_apd_orchestrator_in_user_docs` FAILS (architecture/running/README still cite it); `test_improving_guide_enumerates_all_improvement_types` likely FAILS (the thin guide doesn't list them). The other two may already pass.

- [ ] **Step 3: Confirm ruff-clean** — `ruff check tests/test_doc_domain_pack_authoring.py` → `All checks passed!`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_doc_domain_pack_authoring.py
git commit -m "test(docs): staleness + completeness guard for authoring docs"
```

---

### Task 2: Surgical fixes — retire apd-orchestrator + refresh the CLI reference

**Files:**

- Modify: `docs/architecture.md` (line ~31)
- Modify: `README.md` (line ~97)
- Modify: `docs/running-the-gauntlet.md` (intro line 3; CLI block ~20-32; "Step 2" section ~187-235; lines ~153, ~276, ~300)

**Background (verified):** `apd-orchestrator` is a retired deprecation shim. The deterministic runner is `.claude/workflows/apd-gauntlet.js` (registered as the `apd-gauntlet` workflow). It requires the run to be pre-scaffolded (`init-run` first) and phases it end-to-end: setup (build the domain skill) → intake → the nine specialists across three tiers → attack-path → decomposed synthesis → HTML report → audit → closeout. **Before writing the invocation prose, confirm the current user-facing way to launch it** (check `plugin.json` and `.claude/workflows/apd-gauntlet.js`'s header) so the replacement text is accurate — describe it as running the `apd-gauntlet` workflow runner, not the orchestrator agent.

- [ ] **Step 1: `docs/architecture.md`** — change the coordinator row (line ~31) from the `apd-orchestrator` agent to the workflow runner, e.g. `| Coordinator | \`.claude/workflows/apd-gauntlet.js\` (the \`apd-gauntlet\` runner) | Phases the run, dispatches specialists via receipts, runs the decomposed synthesis + report audit |`. Remove the word `apd-orchestrator`.

- [ ] **Step 2: `README.md`** — replace the `> Run apd-orchestrator on runs/...` invocation (line ~97) with the current workflow-runner invocation.

- [ ] **Step 3: `docs/running-the-gauntlet.md` — the orchestrator section + prose.** Rewrite "## Step 2: Invoke the orchestrator in Claude Code" (≈187-235) to "## Step 2: Run the gauntlet", describing the `apd-gauntlet` workflow runner (pre-scaffold via `init-run`; the runner phases the run end-to-end; it builds the `apd-domain` skill from the active pack(s); it runs decomposed synthesis + the gated report audit). Update every prose mention of "the orchestrator" (lines ~3, ~153, ~195, ~225, ~234, ~276, ~300) to "the runner"/"the gauntlet". Update the `"domain=saas"` scope-hint row (line ~232) to reflect that packs are chosen at `init-run` time via repeatable `--domain` (and the run-config `domains:` list), not a runtime hint. Remove every literal `apd-orchestrator`.

- [ ] **Step 4: `docs/running-the-gauntlet.md` — CLI reference refresh (≈20-32).** Update the fenced command list to current, accurate commands. Add the missing ones and the multi-pack note; keep it operator-relevant:

```text
apd-gauntlet validate <run-dir>                 # three-pass validation
apd-gauntlet init-run <run-id> --inputs DIR --domain pbm [--domain api-security] ...
apd-gauntlet build-domain-skill <pack...>       # compile one or more packs into the apd-domain skill
apd-gauntlet validate-domain <pack...>          # validate one or more domain packs
apd-gauntlet draft-domain-improvements <run-dir> # draft a pack patch from a run's captured opportunities
apd-gauntlet domain-coverage-delta <run-dir>    # deterministic pack-coverage gaps for a run
apd-gauntlet summarize <run-dir>                # finding/capability statistics
apd-gauntlet check-ids <yaml-file>              # verify deterministic record IDs
apd-gauntlet lint-agents                        # validate agent file frontmatter
apd-gauntlet refresh-mitre                      # refresh the cached MITRE crosswalk
```

(Verify each command name against `tools/apd_gauntlet/cli.py` before writing — do not invent flags. The decomposed-synthesis subcommands — `rollup`, `cluster-candidates`, `apply-clusters`, `audit-report` — are run by the workflow, not operators; mention them in one sentence rather than listing.)

- [ ] **Step 5: Multi-domain run example.** In Step 1 ("Scaffold the run"), add a short example showing pack selection for multiple domains: `apd-gauntlet init-run <id> --inputs DIR --domain pbm --domain api-security`, and the resulting `.apd-run.yaml` `domains:` block (`domains:\n  - pbm\n  - api-security`). One sentence on what multi-domain does (the run is reviewed across all selected packs; the skill merges them).

- [ ] **Step 6: Gates** — `npx --yes markdownlint-cli2 "docs/architecture.md" "docs/running-the-gauntlet.md" "README.md"` → `0 error(s)`; `python3 -m pytest tests/test_doc_domain_pack_authoring.py::test_no_apd_orchestrator_in_user_docs tests/test_doc_domain_pack_authoring.py::test_running_guide_cli_reference_lists_draft_command -v` → PASS.

- [ ] **Step 7: Commit**

```bash
git add docs/architecture.md README.md docs/running-the-gauntlet.md
git commit -m "docs: retire apd-orchestrator -> workflow runner; refresh CLI reference + multi-domain example"
```

---

### Task 3: Rebuild `docs/adapting-to-other-domains.md`

**Files:**

- Modify (full rebuild): `docs/adapting-to-other-domains.md`

Author the nine sections from the spec, using `agentic-ai` as the running dissected example (read each `domains/agentic-ai/` file to quote accurately) and retaining the PBM retention-pinning pattern. Keep the existing link to `improving-domain-packs.md` (the B doc-test pins it). Section contract:

1. **Overview — how a pack influences a run:** the pack compiles via `build-domain-skill` into the `apd-domain` skill every specialist loads; it calibrates severity, the consequential-action surface, crown jewels / attacker positions (attack-path activation), and the per-goal pattern catalogs.
2. **Anatomy — the 14 files + the full `domain.yaml` schema:** required `name` (`^[a-z][a-z0-9-]*$`), `display_name` (>=3), `version` (semver), `framework_compat` (range string), `description` (>=20), `includes` (>=1; no leading `/`, no `..`), `regulatory_anchors`; optional `crown_jewels`/`attacker_positions`/`default_trust_boundaries` as `{<pattern|position|boundary>, description (>=10)}`. Show `agentic-ai`'s `domain.yaml` as the example.
3. **Step-by-step authoring (dissecting agentic-ai):** copy a starting pack → `domain.yaml` → `severity-rubric.md` (the four agentic modifiers) → the three support files → the nine `common-patterns/<goal>.md` in the canonical `**Pattern:**` format. **State the lesson explicitly:** taxonomy mappings (CWE/ATT&CK/OWASP-LLM) are emitted in *findings* by the specialists, NOT written as bullets in the pattern markdown — the markdown carries `Severity`/`NIST`/`Related concerns`/`Detail` and grounds OWASP-LLM/ATLAS/MAESTRO in prose. → `validate-domain` → `build-domain-skill` → a sample run.
4. **Multi-domain mechanics (new):** `domains: [list]`; `build-domain-skill` merges packs — union/dedup of `crown_jewels`/`attacker_positions`/`default_trust_boundaries`, concatenated markdown under per-pack `## Domain:` provenance headers, `metadata.packs`; severity union/max/provenance. Cross-link run-time selection in `running-the-gauntlet.md`.
5. **Taxonomy & mapping discipline:** OWASP/ATT&CK/CWE/NIST guidance + the ATLAS/MAESTRO-as-prose lesson (one line that ATLAS-as-taxonomy + MAESTRO-as-methodology are possible future framework efforts).
6. **Reusable pattern: multi-regulator retention pinning** (PBM, kept).
7. **Evolving a pack from runs** (brief → link `improving-domain-packs.md`).
8. **Submitting the pack** (a concrete PR checklist: all 14 files; validate-domain + build-domain-skill clean; mappings in findings not markdown; a sample run validates).
9. **What stays the same across domains.**

- [ ] **Step 1: Read** `domains/agentic-ai/domain.yaml`, `severity-rubric.md`, `common-patterns/integrity.md`, and the two mechanics specs, so every quoted detail is accurate.
- [ ] **Step 2: Rewrite** `docs/adapting-to-other-domains.md` per the nine-section contract above.
- [ ] **Step 3: Gates** — `npx --yes markdownlint-cli2 "docs/adapting-to-other-domains.md"` → `0 error(s)`; `python3 -m pytest tests/test_doc_domain_pack_authoring.py::test_adapting_guide_dissects_agentic_ai_pack tests/test_doc_improving_domain_packs.py::test_adapting_doc_links_to_improving_guide -v` → PASS.
- [ ] **Step 4: Accuracy check** — grep the new guide for the six crown-jewel keys and confirm each matches `domains/agentic-ai/domain.yaml`: `grep -o "tool_execution_capability\|model_provider_credentials\|self_improvement_loop" docs/adapting-to-other-domains.md`. Fix any drift.
- [ ] **Step 5: Commit**

```bash
git add docs/adapting-to-other-domains.md
git commit -m "docs: rebuild adapting-to-other-domains guide (anatomy + multi-domain, dissecting agentic-ai)"
```

---

### Task 4: Rebuild `docs/improving-domain-packs.md`

**Files:**

- Modify (full rebuild): `docs/improving-domain-packs.md`

Author the four sections from the spec. Keep `draft-domain-improvements` mentioned (the B doc-test pins it). Section contract:

1. **Overview** — the capture → draft → apply loop: every run emits advisory `40-synthesis/domain-improvements.yaml` (a deterministic coverage-delta pre-pass + the `apd-domain-auditor` agent, non-blocking Phase 5h); on demand, `apd-gauntlet draft-domain-improvements <run-dir>` turns chosen opportunities into a validated, `git apply`-able patch. No auto-apply, no auto-PR.
2. **The opportunity record** — enumerate all nine `improvement_type` values verbatim: `missing_severity_clause`, `missing_crown_jewel`, `missing_attacker_position`, `missing_trust_boundary`, `missing_consequential_action`, `missing_immutability_class`, `missing_data_class`, `missing_common_pattern`, `missing_regulatory_anchor`. Document the fields: `target_pack`, `target_file`, `priority`, `source` (deterministic vs judgment), `evidence`, `draft_snippet`.
3. **`target_pack` attribution under multi-domain** — deterministic deltas key off the run's `domains`; the auditor attributes each opportunity to the specific pack it would edit.
4. **Read → Draft → Review → Apply & re-validate** — the command + its filters, the temp-copy `validate-domain` + `build-domain-skill` gate, drop-on-fail, and the minimal line-anchored diff.

- [ ] **Step 1: Read** `docs/superpowers/specs/2026-05-30-domain-improvement-capture-design.md` + `schemas/domain-improvement.schema.json` for accurate field/enum details.
- [ ] **Step 2: Rewrite** `docs/improving-domain-packs.md` per the four-section contract (all nine `improvement_type` strings must appear verbatim).
- [ ] **Step 3: Gates** — `npx --yes markdownlint-cli2 "docs/improving-domain-packs.md"` → `0 error(s)`; `python3 -m pytest tests/test_doc_domain_pack_authoring.py::test_improving_guide_enumerates_all_improvement_types tests/test_doc_improving_domain_packs.py -v` → PASS.
- [ ] **Step 4: Commit**

```bash
git add docs/improving-domain-packs.md
git commit -m "docs: rebuild improving-domain-packs guide (loop + 9 improvement_types + multi-domain attribution)"
```

---

### Task 5: Final verification

- [ ] **Step 1: Full guard suite** — `python3 -m pytest tests/test_doc_domain_pack_authoring.py tests/test_doc_improving_domain_packs.py -v` → all PASS.
- [ ] **Step 2: Full regression** — `python3 -m pytest -q` → green; `ruff check tools/ tests/` → clean; `python3 -m mypy tools/` → clean.
- [ ] **Step 3: Full CI markdownlint glob** — `npx --yes markdownlint-cli2 "docs/**/*.md" "!docs/superpowers/plans/**" ".claude/**/*.md" "domains/**/*.md" "README.md" "CONTRIBUTING.md" "CHANGELOG.md" "CODE_OF_CONDUCT.md"` → `0 error(s)`.
- [ ] **Step 4: Residual-staleness sweep** — `grep -rn "apd-orchestrator" docs/*.md README.md` → no matches; `grep -rn "^\s*domain: [a-z]" docs/*.md README.md` → no matches (run-config key stays `domains:`).
- [ ] **Step 5:** If any sweep finds a stray, fix it and re-run; commit any final touch-up with `docs: final staleness sweep for the authoring docs overhaul`.

---

## Self-review

1. **Spec coverage:** adapting rebuild (Task 3) covers spec §adapting; improving rebuild (Task 4) covers §improving; surgical fixes (Task 2) cover the three docs + CLI refresh + multi-domain example; the guard test (Task 1) + Task 5 cover the acceptance bar. The corrected `domain`/`domains` finding is encoded in Conventions so the implementer won't reintroduce a false rename.
2. **Placeholder scan:** `<pack...>`, `<run-dir>`, `<id>`, `<goal>` are CLI/template placeholders with concrete substitution; no `TBD`/`TODO`. The two guide rebuilds give a section contract + read-the-pack instructions rather than 300 lines of final prose — appropriate altitude for a docs deliverable, and each is gated by markdownlint + guard assertions + an accuracy check.
3. **Consistency:** the nine `improvement_type` strings in Task 4 match Task 1's `IMPROVEMENT_TYPES` and the schema; the six crown-jewel keys in the sources-of-truth match `domains/agentic-ai/domain.yaml`; `draft-domain-improvements` is the command name throughout.
