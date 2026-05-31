# APD Gauntlet Multi-Domain Runs Design

- **Date:** 2026-05-30
- **Status:** Approved (design); implementation plan pending
- **Author:** brainstormed with Claude Code
- **Scope:** Let a single gauntlet run examine a solution across **multiple domain
  packs at once** (e.g. PBM + API + Web App + Agentic), in one pass, with a coherent
  merged calibration context. Hard cutover of the run-config `domain` field to a
  `domains` list, with corresponding fixes across the entire codebase. Folds in the
  pre-existing domain-skill staleness fix.
- **Subsystem:** A (of the domain-system evolution). Subsystem B
  (auditor captures domain-improvement opportunities) and the documentation/skills
  overhaul are separate, sequenced efforts. This spec emits B's trigger condition
  but does not build B.

## 1. Problem / Motivation

A real solution rarely lives in exactly one domain. A pharmacy-benefit platform
that exposes a public REST API, a member web app, and an autonomous agent feature
is simultaneously in scope for the **PBM**, **API**, **web-app**, and **agentic**
domains. Today the gauntlet binds a run to exactly one pack:

- `schemas/run-config.schema.json` declares a single required `domain` string.
- `apd-gauntlet build-domain-skill <domain>` compiles exactly one pack into the
  single global `.claude/skills/apd-domain/SKILL.md`
  (`tools/apd_gauntlet/build_domain_skill.py:42-87`).
- Specialist agents read that one skill (`.claude/agents/apd-confidentiality.md:19`
  and the eight sibling lenses).

So a blended solution can only be reviewed by running the gauntlet N times against
N domains and manually reconciling N reports — which loses the highest-value
**cross-domain** findings (e.g. an attacker position contributed by the API domain
reaching a crown jewel defined by the PBM domain) and produces no single,
severity-reconciled view.

A second, pre-existing defect compounds the change: Phase 0b's idempotency guard
(`.claude/workflows/apd-gauntlet.js:98-113`) skips rebuilding the domain skill when
the output file merely *exists* and the run dir validates — it never checks *which*
pack the skill holds. A run that switches domains can silently inherit a stale
skill from a previous run. Multi-domain makes correct rebuild-on-selection-change
mandatory, so we fix this here.

## 2. Goals / Non-Goals

**Goals**

- A run declares one or more domain packs and the gauntlet examines the solution
  across all of them in a **single pass**, producing one merged, severity-reconciled
  output.
- The merged calibration context is **coherent and provenance-tagged**: every
  surface item and rubric clause records which pack contributed it.
- Cross-domain attack paths are preserved (position from pack X → jewel from pack Y),
  bounded by the run's actual asset inventory and the existing enumeration caps.
- **Hard cutover:** `domain` is removed from the run-config in favor of `domains`,
  with every reader, fixture, doc, and test migrated. No alias, no shim.
- The domain skill is rebuilt whenever the selected pack **set** changes (staleness
  fix).
- Single-domain behavior is preserved as the one-element case: a `domains` list of
  length 1 compiles to a skill equivalent to today's, and existing fixtures pass
  after mechanical migration.

**Non-Goals**

- Changing the nine APD goals, the finding/capability schema semantics, the
  NIST/ATT&CK/D3FEND mapping guidance, or the evidence-discipline rules. These stay
  domain-independent.
- Building the auditor improvement-capture mechanism (Subsystem B). This spec only
  emits B's trigger condition: a harm that matches **no** severity-rubric clause in
  **any** selected pack.
- Authoring the `web-app` or `agentic` packs. Multi-domain is the mechanism; new
  packs are authored separately. A is validated with existing packs (`pbm` +
  `api-security`).
- A machine-readable `source_domains` field on the finding/capability schema. For A,
  provenance lives in the pack-labeled skill and the cited rubric clause text; a
  structured field is deferred to B, where it is actually consumed.

## 3. Decisions (resolved during brainstorming)

| Decision | Choice |
|---|---|
| Merge model | **Per-component merge + provenance** — union surfaces, concatenate prose/patterns under per-pack headers, into one `apd-domain` skill |
| Severity across packs | **Union + max + provenance** — cite the governing pack+clause; take the max when multiple packs match; no-match-in-any-pack ⇒ B trigger |
| Attack-path scale | **Cross-domain, grounded + bounded** — dedup by name, enumerate over the run's asset-inventory, allow cross-pack paths, keep existing depth/top-N caps |
| Run-config migration | **Hard cutover** — remove `domain`, add required `domains`; fix all readers/fixtures/docs/tests |
| Staleness fix | **Folded in** — guard compares skill `metadata.packs` to `args.domains` and rebuilds on mismatch |
| No-domain rule | Generalizes — halt only if **zero** packs load |

## 4. Run-config: hard cutover `domain` → `domains`

`schemas/run-config.schema.json`:

- **Remove** the `domain` property.
- **Add** `domains`: `{ "type": "array", "items": { "type": "string", "pattern":
  "^[a-z][a-z0-9-]*$" }, "minItems": 1 }`.
- Update `required` from `["run_id", "domain", "framework_version"]` to
  `["run_id", "domains", "framework_version"]`.

`tools/apd_gauntlet/init_run.py`: write a `domains:` block (YAML list) instead of
`domain:`; the `--domain` CLI option becomes repeatable — it may be passed multiple times
(`--domain pbm --domain api-security`) — defaulting to `[pbm]`.

`.claude/workflows/apd-gauntlet.js`: `args.domain` → `args.domains` everywhere —
the setup log line, the `build-domain-skill` step, the `validate-domain` step, and
the intake crown-jewels gating. The `args = .apd-run.yaml` contract documented in
the token-resilience design (`domain` in the field list) updates to `domains`.

## 5. Compile / merge — `build-domain-skill` over a pack set

`build_domain_skill.py` signature changes from a single `domain_name` to an ordered
`domain_names: list[str]`. It still emits the single
`.claude/skills/apd-domain/SKILL.md`. Algorithm:

1. **Validate each pack** against `schemas/domain.schema.json` (as today, per pack).
2. **Compatibility gate:** `framework_compat` must hold for **every** selected pack;
   on any miss, hard-error naming the offending pack and its range (today's
   single-pack check, applied across the set).
3. **Surface union** (`crown_jewels`, `attacker_positions`,
   `default_trust_boundaries`): concatenate across packs, **dedup by key**
   (`pattern` / `position` / `boundary`). Each retained item is annotated with the
   contributing pack(s). When two packs define the same key with materially
   different descriptions, retain both, attributed.
4. **Calibration prose** (`severity-rubric.md`, `consequential-actions.md`,
   `immutability-classes.md`, `data-taxonomy.md`): emitted **per pack** under
   provenance headers — `## Domain: <pack> — Source: <file>`. All packs' rubrics,
   audit surfaces, immutability classes, and taxonomies are present and labeled.
5. **Patterns** (`common-patterns/<goal>.md`): for each of the nine goals,
   contributing packs' files are concatenated under the same provenance headers, so
   the per-goal pattern library is the union, still labeled by pack.
6. **Frontmatter:** `metadata.pack` / `metadata.pack_version` become
   `metadata.packs: [{ name, version }, …]` (order = declared order). `generated`
   stays.

Ordering is deterministic (declared `domains` order; `sorted()` within a pack's
globs, as today) so the compiled skill is byte-stable for a given pack set.

## 6. Idempotency-guard fix (staleness)

`.claude/workflows/apd-gauntlet.js` Phase 0b: the guard text currently skips when
the output file exists and `validate --schema-only <run>` exits 0. Extend the
skip condition so it **also** requires the existing skill's
`metadata.packs` (names) to equal `args.domains` (as a set). On mismatch — including
a single-pack skill left by a previous different-domain run — treat as NOT-DONE and
rebuild. This is the staleness fix identified during the prior understanding
review, now load-bearing for multi-domain switching.

## 7. Severity discipline — union + max + provenance

`.claude/skills/apd-evidence-discipline/SKILL.md` ("Severity rubric (domain-loaded)"
and "Severity calibration discipline") and the nine lens agents' required-reading
line + self-check:

- "the active domain's severity rubric" → "the active domain**(s)'** severity
  rubrics".
- Citation rule: cite the **specific pack and clause** in `detail`
  ("…high severity under the *api-security* rubric clause *X*…").
- Multi-match rule: when one harm matches clauses in more than one pack at different
  severities, take the **max** (the existing "do not average across impacts" rule,
  extended across packs) and cite the governing pack's clause.
- No-fallback rule generalizes: emit the "no severity rubric in scope" halt finding
  only when **zero** packs load.
- **B trigger:** a harm that matches no clause in any selected pack is recorded as a
  *domain-improvement opportunity* candidate. In A this is surfaced via the existing
  finding/blocked path and a note; the capture mechanism is Subsystem B.

The synthesizer's existing severity-reconciliation
(`.claude/agents/apd-synthesizer.md`) already arbitrates disagreements via cited
clauses; with pack-labeled clauses it reconciles across packs unchanged.

## 8. Attack paths — cross-domain, grounded, bounded

- `apd-intake` builds `00-context/asset-inventory.yaml` from the **unioned, deduped**
  crown jewels (and trust boundaries); activation gate is "the union is non-empty".
- `apd-attack-path-analyzer` enumerates over assets **instantiated in this run's**
  asset inventory (not the cartesian product of all packs' declarations), allows
  **cross-pack** (source from one pack, sink from another), and keeps the existing
  depth caps and top-N-by-risk bounds.
- `apd-attack-path-discipline` never-invent sourcing extends: a node may cite "a
  declaration in **any selected** pack's `crown_jewels` / `attacker_positions`".

## 9. Validation & report touch-points

- `validate-domain` accepts a set: per-pack schema + include-resolution, plus the
  framework_compat-across-all gate. Optional: warn when the same crown-jewel or
  data-class **name** carries materially divergent descriptions across packs (a
  cross-pack consistency hint, not a hard error).
- Advisory report / `report-data`: add a "domains examined" header naming the
  blended lens set. The APD 9×N coverage matrix (goal × component) is unchanged
  (domain-independent).

## 10. Cutover surface (full blast radius)

Hard cutover means migrating every reader of the field and every fixture. The
pattern is "replace single `domain` with `domains` list; merge over the set." Known
touch-points (representative, not exhaustive — the implementation plan enumerates
the rest):

- **Schema:** `schemas/run-config.schema.json`.
- **Workflow:** `.claude/workflows/apd-gauntlet.js` (`args.domain` → `args.domains`;
  multi-positional `build-domain-skill`; guard pack-set compare).
- **CLI / Python:** `tools/apd_gauntlet/cli.py` (`build-domain-skill`, `init-run`,
  `validate-domain`), `build_domain_skill.py`, `init_run.py`, and any `domain`
  read in `validate.py`.
- **Fixtures (migrate `domain: x` → `domains: [x]`):** every `.apd-run.yaml` under
  `runs/apd-20260527-crapi-owasp-api-top10/`,
  `runs/apd-20260527-authentik-identity-provider/`,
  `runs/apd-20260527-caldera-adversary-emulation/`, and
  `examples/apd-20260601-claim-event-bus/`.
- **Agents / skills prose:** the nine lens agents' required-reading line,
  `apd-evidence-discipline`, `apd-intake`, `apd-synthesizer`,
  `apd-attack-path-analyzer`, `apd-attack-path-discipline`, and the regenerated
  `apd-domain` skill frontmatter (`metadata.packs`).
- **Docs:** `docs/running-the-gauntlet.md`, `docs/architecture.md`,
  `docs/adapting-to-other-domains.md`, READMEs, and the token-resilience design's
  `args` field list — anywhere `domain:` is shown in a run-config.
- **Tests:** unit/fixture tests touching `init-run`, `build-domain-skill`,
  `validate`, `validate-domain`, and run-config schema validation.

## 11. Backward compatibility & migration

There is **no runtime back-compat** (hard cutover by decision). Compatibility is
preserved only at the *behavioral* level: a one-element `domains` list reproduces
today's single-pack skill (modulo the new `metadata.packs` frontmatter). All shipped
fixtures are migrated in the same change so the test suite stays green. A short
migration note ("`domain:` → `domains:`") is added for any external run-configs.

## 12. Testing

- **Unit (`build_domain_skill`):** surface union + dedup-by-key + provenance
  annotation; per-pack prose/pattern headers; `metadata.packs` frontmatter;
  framework_compat-across-set rejection (named offender); deterministic byte-stable
  output for a fixed pack set.
- **Unit (guard):** rebuild-on-pack-set-change; skip when set matches.
- **Schema:** `domains` required + `minItems 1`; `domain` rejected as unknown
  property (cutover proof).
- **Integration:** a blended `pbm` + `api-security` run produces a skill with both
  rubrics labeled, at least one cross-domain attack path, and a severity citing the
  governing pack's clause; an existing single-domain fixture re-runs green after
  migration (regression).

## 13. Out of scope (deferred)

- Subsystem B (auditor captures domain-improvement opportunities) — A emits only the
  no-clause-match trigger.
- Structured `source_domains` provenance field on finding/capability schemas —
  revisited in B.
- `web-app` / `agentic` pack authoring.
- Cross-pack conflict resolution beyond the optional consistency *warning* in §9.

## 14. Open questions / risks

- **Surface dedup key collisions with divergent semantics.** Two packs may use the
  same `crown_jewel` name for subtly different assets. The design keeps both
  attributed; if this proves noisy, a future pack-namespacing convention may be
  warranted. Flagged, not solved here.
- **Combined skill size.** Four packs concatenated could approach or exceed the
  ~97 KB single-pack skill several-fold. If agent context pressure results, a
  follow-up may prune per-goal patterns to the selected packs' most material
  examples. Out of scope for A; called out for monitoring.
- **Severity ergonomics.** Citing pack+clause across four rubrics raises author
  burden in `detail`. Mitigated by the pack-labeled headers making the governing
  clause unambiguous.
