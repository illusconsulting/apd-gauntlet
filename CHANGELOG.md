# Changelog

All notable changes to this project will be documented in this file. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per [SemVer](https://semver.org/).

## Unreleased — 2.0 line (`next`)

The 2.0 line adds optional decision models and local CLI, TUI and web apps. The
design and implementation plans are in
`docs/superpowers/specs/2026-10-10-local-apps-and-decision-models-design.md`
and `docs/superpowers/plans/2026-10-10-local-apps-plan{1,2,3}-*.md`.

### Added

- **`summarize --record-attempts` and `.apd-state/attempts.yaml`.**
  `apd-gauntlet summarize RUN_DIR --record-attempts '<json>'` validates a
  run-attempts object against the new `run-attempts.schema.json` and writes it
  to `<run>/.apd-state/attempts.yaml` before it summarises the run. The file
  records what 1.7 runs keep only in the workflow's memory: lens retries, lenses
  that failed schema validation on the first pass, tier gates that failed before
  repair, skipped lenses, report-audit iterations, and the files and lenses the
  tier repair loop repaired or re-ran. The command exits 2 when the value is not
  JSON and 1 when it does not match the schema, and writes nothing in either
  case.
- **`usage`: tokens and cost per agent and phase from OpenTelemetry.**
  `apd-gauntlet usage RUN_DIR --otel FILE [--workflow-run ID] [--json]` reads
  Claude Code's `claude_code.api_request` events from an OTLP/JSON export (the
  OpenTelemetry Collector `file` exporter's output) and writes
  `<run>/.apd-state/usage.yaml`: totals, `by_agent` and `by_phase`, the
  decision-model spend recorded under `40-synthesis/decisions/`, and the
  combined cost `cost_usd_all`. It warns when agent names are redacted (set
  `OTEL_LOG_TOOL_DETAILS=1`, Claude Code 2.1.273 or later), when the file
  covers more than one workflow run, and when a request carries no cost. It
  exits 1 and writes nothing when no `api_request` event is left after
  filtering, and 2 when the export is not OTLP/JSON (the console exporter's
  output is refused). The new runbook,
  [docs/measuring-changes.md](docs/measuring-changes.md), covers baseline
  capture, the telemetry setup with a minimal Collector configuration, and the
  agent-to-phase map.
- **`compare-runs`: a deterministic before-and-after delta with gates.**
  `apd-gauntlet compare-runs BASELINE CANDIDATE [--json] [--gates eval/gates.yaml] [--excuse VALUE]... [--strict]`
  compares two runs, or two run sets named `<name>-r1`, `<name>-r2`, … (every
  baseline run against every candidate run). It matches findings and
  capabilities one to one (same goal, a shared derived asset, title Jaccard of
  at least 0.5), counts what went missing and what is new by severity, the
  severity and maturity shifts, the headline overlap, and each lost critical or
  high finding with its excuse. It reports the blocked rate, the attempts
  counts and the usage cost per run and as side medians. With `--gates` it
  applies the five proposal gates in the new `eval/gates.yaml` to the medians.
  The result is `pass`, `pass_with_gaps` (a gate has no data, as the attempts
  gates against 1.7 baselines) or `fail`. `--strict` makes `pass_with_gaps`
  exit 1. `--excuse <finding-id>` accepts a reviewed loss, and
  `--excuse <gate-id>:<reason>` marks a gate that failed or has no data
  `excused`. It exits 0 when no gate fails, 1 when one fails, and 2 when a side
  does not resolve, both sides share a run, a baseline run has no findings, the
  runs have different inputs, a run fails to load or the gates file cannot be
  read. The text report prints control characters from run files as escapes.
  The runbook's "Compare runs" section covers the matching, excuse and median
  rules.
- **The workflow records its retries and audit iterations.** The workflow
  writes `.apd-state/attempts.yaml` at closeout: its `summarize` step now
  passes the runner's counts to `summarize --record-attempts`, with
  `recorded_by: workflow`. The file holds the lens retries, the lenses that
  failed schema validation on the first pass, skipped lenses, the tier gates
  that failed before repair, the files and lenses the tier repair loop
  repaired or re-ran, and the report-audit iterations. The step now always
  runs. `compare-runs` can then apply gates 4 and 5 to 2.0 workflow runs. The
  counts cover one invocation of the runner: a resumed run lists its skipped
  lenses, and those gates read `not_available` for it. A foreground `plan-run`
  drive records nothing. No phase, step or dispatch label changes. The
  runbook's "Retries and audit iterations" section describes the file.
- **The `findings` evaluator and `eval label-template`.**
  `apd-gauntlet eval label-template RUN_DIR --entry ID --out FILE` writes an
  `eval-labels` file with one `unreviewed` item per finding of the run (its
  id, goal, severity, title and evidence pointers). A reviewer sets each
  verdict to `true_positive` or `false_positive`, corrects the goal or
  severity where the run got them wrong, and adds true positives the run
  missed. The command never overwrites `FILE` (exit 1), and exits 2 when `ID`
  is not a corpus entry id or the run cannot be read. The `findings`
  evaluator, registered in the evaluator registry, matches the true positives
  to the run's findings with the `compare-runs` matcher, then the false
  positives to the findings left. It reports precision, strict precision
  (findings no label judged count against it), recall and F1 per goal and in
  total, and severity agreement. It refuses labels with `unreviewed` items.

### Changed

- **Version tracks the stable line (1.7.1) until the first 2.0 pre-release.**
  The first 2.0 pre-release (`2.0.0a1`, plugin `2.0.0-alpha.1`) has not been
  cut. When it is, it publishes to PyPI as a pre-release
  (`pip install --pre apd-gauntlet`) and to the
  `apd-security-next` plugin marketplace from the `next` branch.
- **Domain packs accept framework 2.x.** All six bundled packs now declare
  `framework_compat: ">=1.0.0,<3.0.0"`. The 2.0 changes leave the pack format
  untouched. Third-party packs that declare `<2.0.0` need the same change
  before they will build against a 2.0 engine.

## v1.7.1 — 2026-10-17

### Added

- **Quickstart guide.** [docs/QUICKSTART.md](docs/QUICKSTART.md) walks a
  first-time user through installing the gauntlet and running a review by
  chatting with Claude, with example prompts for scaffolding a run, running it,
  code recon, threat models, working with the findings and rebuilding the
  report. It then covers the explicit CLI path, the commands you will actually
  type, optional add-ons and troubleshooting. The README links to it at the top.
  (#7)

### Changed

- **Two release lines.** `main` keeps shipping the stable 1.7 line; `next`
  carries the 2.0 pre-releases. A new release gate
  (`tools/check_release_tag.py`) runs first in the `release` workflow. It
  refuses a tag that does not match the package version or that sits on the
  wrong branch for its kind of version, and it flags pre-releases on GitHub so
  that only the highest stable version is marked Latest. CI now also runs on
  `next` and `release/**`. See [RELEASING.md](RELEASING.md). (#27)
- **Pre-release engines stamp a release framework version.** `init-run` and
  `build-domain-skill` now use `FRAMEWORK_VERSION`, which is the package version
  with any pre-release, dev or post suffix removed (`2.0.0a1` → `2.0.0`).
  Stamping `__version__` directly would have written a `framework_version` that
  `run-config.schema.json` rejects, and it would have crashed the
  `framework_compat` check on the first pre-release. Stable versions are
  unaffected. (#27)
- **Plugin-channel guardrails.** A loader-contract test now checks
  `.claude-plugin/plugin.json` against the Claude Code plugin loader's rules:
  every `skills` entry must be a directory that holds a `SKILL.md`, and every
  `agents` and `commands` entry a `.md` file. Fixtures prove the test catches
  each broken form, and the `commands` array must list exactly the files in
  `commands/`. A new `apd-gauntlet lint-skills` command checks each skill's
  frontmatter: `name` must match its directory, be in lowercase-hyphen form and
  be at most 64 characters, and `description` must be present and at most 1,536
  characters. CI runs it next to `lint-agents`, and a new CI job runs `claude
  plugin validate` on `plugin.json` and `marketplace.json` with a pinned Claude
  Code CLI (2.0.76). `CONTRIBUTING.md` gains a plugin-channel section. (#10)
- **The report bundle is rebuilt with newer graph and UI libraries.** The report
  template now builds with Cytoscape.js 3.34.3 (was 3.30.2), React and React DOM
  19.3.0 (was 18.3.1) and cytoscape-dagre 4.0.1 (was 2.5.0). The committed
  report bundle and its `vendor-licenses.txt` were regenerated, and after the
  React and dagre update the Home Assistant example report renders the same text
  on all nine tabs and the same dagre layouts. (#44, #45)

### Fixed

- **A resumed run decides agent skips from the new `apd-gauntlet resume-plan`
  command, and agent prompts no longer carry a resume guard they cannot run.**
  The read-only `apd-gauntlet resume-plan <run-dir> [--json]` reports, for each
  first-attempt agent step, whether its outputs are present and valid (a lens
  interrupted between its findings and capabilities files is not complete and
  re-runs). The workflow calls it once in setup and skips every complete agent
  step without dispatching it. CLI steps keep their own guard; retries and
  report-writer remediation passes always run. `resume-plan` refuses a run
  directory created by another framework major (exit 3) and the workflow halts
  before dispatching any other step. The workflow also halts, telling you to run
  `pip install --upgrade "apd-gauntlet>=1.7.1,<2"`, when the installed engine is
  older than the plugin and has no `resume-plan` command. Any other `resume-plan`
  failure is logged and the workflow runs every agent step. The `plan-run`
  checklist now starts with a `resume-plan` row. (#49)
- **Tier gates now block, and a failing tier is repaired before its lenses are
  re-run.** The per-tier validate gate used to discard its result, so a failing
  tier was caught only by the whole-run gate before synthesis, with no repair
  step. The gate now always runs and reports each failing file, including an error
  with no record id or no path, such as a YAML parse error. A failing file
  gets one repair by a repair agent, whose prompt is the new packaged template
  `tools/apd_gauntlet/data/prompts/repair.md` (read with
  `resources.read_prompt`). If the tier is still invalid, the lenses that own the
  files that are still failing are re-run once. If it is still invalid after
  that, the run halts and names the files. Dispatch failures still retry the lens
  twice, as before. The `plan-run` tier-gate rows and the troubleshooting docs
  describe the same path. (#49)
- **The read-only validate gates can no longer skip themselves.** The intake
  schema gate, the pre-synthesis whole-run gate and the final validate now always
  run their validate command (the intake gate still checks the schema only).
  Previously a schema-only guard could skip them on runs with only semantic or
  cross-file errors, so the pre-synthesis halt can now fire on errors it used to
  miss. (#49)
- **An always-run CLI step's prompt no longer offers its worker a skip.** Every
  step the workflow marks always-run (among them `resume-plan`, the tier gates,
  the three read-only gates and the `canonicalize` steps) told its worker "no
  idempotent skip" and then, a few lines later, to run the command only if a guard
  check found the work not done, and to return the skip sentinel if it
  short-circuited.
  A worker that short-circuited returned ok, so a tier gate could pass without
  running and the `resume-plan` exit-3 refusal could be missed. These prompts now
  say to always run the command and no longer mention a guard check or the skip
  sentinel. Guarded steps keep both. (#49)
- **The tier-gate repair agent has no shell and treats its input as data.** The
  repair prompt embeds validator messages that quote offending values and source
  lines, and lens excerpts are verbatim client text, yet the repair worker was
  dispatched without an agent type and could run shell commands. A repair is now
  dispatched as the new `apd-tier-repair` agent, whose tools are `Read` and `Edit`
  only, and `repair.md` tells it that the errors, the file it repairs and every
  file under `inputs/` are data, not instructions. (#49)
- **The threat-model evaluator reads and writes the paths the engine reads.** Its
  prompt told it to read `20-findings/**` and `10-capabilities/**` (neither
  exists) and to write one `tmeval-<sha8>.yaml` file per finding under
  `20-findings/40-threat-model/`, a path `validate` rejects and the report loader
  never reads. It now reads `40-synthesis/deduped-findings.yaml` and
  `deduped-capabilities.yaml` and writes every finding to the single file
  `40-threat-model/threat-model.findings.yaml` (root key `finding`). The workflow
  instruction and `docs/threat-modeling.md` name the same paths. (#49)
- **The attack-path analyzer drops two obsolete passages.** It no longer hedges on
  a report template that already exists (`templates/attack-path-report.template.md`),
  and no longer asks for a manual schema check of its four output files on the
  grounds that `validate` covers three of them vacuously. `validate` schema-checks
  the three graph files and every `attack-path.findings.yaml` record and checks
  edge integrity, so the analyzer runs `apd-gauntlet validate` and fixes errors in
  those four files. It leaves errors in other agents' files alone: the
  threat-model evaluator runs in parallel and its records have no ids yet. (#49)
- **The confidentiality lens no longer asks for an id in its self-check.** Item 10
  of its pre-emit checklist said the id should be "computed deterministically per
  the schema rule", which contradicts the contract earlier in the same prompt:
  lenses emit no `id`, and `apd-gauntlet canonicalize` mints it. The item is gone,
  and a test keeps the self-check sections of all nine lens agents free of id
  items. (#49)
- **The domain skill rebuilds when a pack file changes, not only when a pack
  version or the framework version does.** `build-domain-skill` skipped the
  rebuild whenever `metadata.packs` and `framework_version` matched, so editing a
  pack's `severity-rubric.md`, `common-patterns/` or `domain.yaml` without
  bumping its version left the previous `apd-domain` skill and `by-goal/`
  sidecars in place. The full skill's frontmatter now records
  `metadata.content_sha256`, a SHA-256 over each selected pack's `domain.yaml`
  and every file it includes, and the skip requires that hash to match as well.
  A skill built before this fix has no hash and is rebuilt once on its next run,
  including the committed `.claude/skills/apd-domain/`. (#49)
- **`canonicalize` mints the `cev-` and `tm-` ids agents were asked to compute.**
  The code-evidence-index `id` (`cev-<sha8(qualified_name|line_range)>`,
  repo-qualified when the index declares `repos`) and the normalized threat-model
  `entry_id` (`tm-<sha8(asset + threat + source_locator)>`) were hashed by LLM
  agents, which cannot do that reliably. `canonicalize` now mints each one that is
  absent, and the schemas make them optional-at-emission. It also fills an absent
  `inferred_apd_goals` from the entry's STRIDE or LINDDUN letter; that field stays
  agent-authorable, because attack-tree, MAESTRO and free-form entries and the PBM
  `N_compliance` override are set by judgement, and an authored value is never
  replaced. An id that is already present is never rewritten, so
  the hand-assigned ids in older runs and in the committed Home Assistant example,
  which findings and `c4-recon.yaml` cite, stay byte-identical. `validate` reports
  `context id missing: <file>: entries[<n>] ...` for an entry that was never
  canonicalized, and `canonicalize` reports an unparseable context file instead of
  raising. The CLI summary adds `N context ids minted` when it minted any
  ([ADR-0020](docs/adrs/0020-tooling-authored-derived-fields.md) Amendment v1.7.1). (#49)
- **The code recon and threat-model agents emit content only, and the runner mints
  their ids.** `apd-code-recon` told the model to compute a `cev-` id for every
  index entry, `apd-threat-model-author` a `tm-` `entry_id` for every
  threat-model entry and `apd-threat-model-recon` one for every free-form entry it
  extracts, and both are hashes an LLM cannot compute reliably. The three prompts
  now say not to emit them. The author also drops the `entry_id` from each cell it
  copies out of the skeleton, because that id hashes the skeleton's stub threat
  and would no longer match the grounded one. The author and the recon agent keep
  setting `inferred_apd_goals`; `canonicalize` fills it only when they leave it
  out. The workflow now runs `canonicalize` after code-recon, before the author
  reads the index, and again after the threat-model phase, before the lenses cite
  the entries; `plan-run` lists the same two steps. One prompt example was wrong
  in two ways and is fixed: the `c4-recon.yaml` example used a `provenance.source`
  the schema rejects, and told the model to cite a `cev-` id that does not exist
  yet when that file is written. Containers and edges now cite
  `file_path:Lstart-Lend` (or a `CROSS_*` edge's `<caller_qn> -> <callee_qn>`
  pair), as the `apd-c4-discipline` skill asks. The
  code recon prompt also says to keep provenance in fields such as `notes:`, not
  YAML comments, because `canonicalize` rewrites the index and drops comments.
  The code-architecture-brief and authored-threat-model templates no longer show
  ids: the brief's lens table lists `qualified_name:Lx-Ly` code anchors and the
  authored render labels entries `<letter>/<surface>`. (#49)
- **`validate` checks that an evidence excerpt appears verbatim in the input it
  cites.** A model that paraphrased instead of quoting went unnoticed, because only
  the artifact name was checked. For each excerpt that cites a file under the run's
  `inputs/` directory, `apd-gauntlet validate` now reports
  `evidence[N].excerpt not found verbatim in artifact '<file>'`, in the whole-run
  pass and at tier gates (`--tier`). It is a warning by default and an error with
  the new `--strict-excerpts` flag. Whitespace, backticks and `*` are ignored, `...`
  or `…` joins fragments that must appear in order, an excerpt wholly in parentheses
  (an absence marker such as `(absent in supplied TM)`) is skipped, and so are
  run-internal artifacts, unresolvable paths, files that are not UTF-8 and files
  over 20 MiB. A YAML or JSON input over 1 MiB, and a YAML input with aliases
  or more than 100 levels of nesting, is searched as plain text only, and a malformed or
  hostile one never makes the check fail. The workflow's gates ignore warnings, so on
  1.7.1 the warning shows in a manual `apd-gauntlet validate <run-dir>` run only. (#49)
- **`init-run` refuses input links that point outside the inputs folder.** It used
  to follow them, so a link such as `inputs/keys -> ~/.ssh` copied the files it
  pointed at into the run, where the agents read them. `init-run` now checks every
  link first, whether it points at a file, a directory or nothing. If any points
  outside the inputs folder, it exits 1, names each link and its target, and
  creates nothing. Links that stay inside are copied as links, and absolute ones
  become relative links, so the run never points back at the original folder. (#49)
- **The workflow runner now awaits every dispatch.** It was written for an older
  Workflow runtime, where `agent()` returned the agent's result. On current Claude
  Code, `agent()` and `parallel()` return Promises, and the runner awaited none of
  them. Every receipt it checked was a pending Promise, which read as success, so
  no agent ran to completion and every run failed at the report-audit gate with a
  misleading `audit-report still FAILED a STRUCTURAL check` error. The runner now
  awaits every dispatch, so each step finishes before the next one starts. Three
  kinds of group still run in parallel: a tier's lenses; a red tier's repairs, and
  then, if they did not fix it, its lens re-runs, each batch on its own; and the
  threat-model evaluator with the attack-path analyzer. A `resume-plan` refusal now
  halts the run before anything else is dispatched. (#50)
- **`validate` resolves a capability's cross-references against capability ids.**
  It resolved every `cross_references` and `merged_from` entry against finding ids, so a capability
  that cross-referenced another capability (the form `capability.schema.json`
  requires) was reported `cross_reference <id> not found`. That failed the
  whole-run check and halted the gauntlet before synthesis. `cross_references` and
  `merged_from` now resolve against the ids of the record's own kind, including
  merged capability ids (`cap-merged-*`, from
  `40-synthesis/deduped-capabilities.yaml`) after synthesis. Every id in that file
  now also resolves in the asset-graph `mitigated_by_capability` edge check and the
  `contradictions.yaml` `capability_id` check. Every whole-run check that reads
  `deduped-findings.yaml` or `deduped-capabilities.yaml` (the `cross_references` /
  `merged_from` check and the `report-data.yaml` and `domain-improvements.yaml`
  checks) now reads a malformed or unreadable one as holding no ids and reports the references
  left unresolved. Each of them used to crash on a malformed
  `deduped-findings.yaml`, and the `report-data.yaml` check on a malformed
  `deduped-capabilities.yaml` too. They all read the deduped files the same way
  now, so the `report-data.yaml` check also accepts a deduped file with a plural
  root key (`findings:`, `capabilities:`) or a single-record mapping, and the
  `domain-improvements.yaml` check does the same for `deduped-findings.yaml`. (#50)
- **The plugin's skills load.** Each `skills` entry in
  `.claude-plugin/plugin.json` named a skill's `SKILL.md` file, but Claude Code
  requires the directory that contains it and rejects a file path, so none of
  the plugin's skills loaded. Every entry now names the skill directory, and a
  manifest test fails if an entry points at a file again. (#8)
- **The report-freshness gate no longer fails a correctly built bundle.**
  `tools/check_report_template_freshness.py` hashed the report-template sources
  but skipped dotfiles and `node_modules` only at the top level, while
  `build.mjs` skips them at every depth, so a nested dotfile such as
  `sub/.gitkeep` made the two hashes differ and turned the gate red. The Python
  hash now skips them at every depth too. The Node walk moved into
  `report-template/.build/source-hash.mjs`, which `build.mjs` imports, and a new
  parity test checks that the Python and Node hashes agree on the same tree. A
  new `bundle-rebuild-diff` CI job rebuilds the bundle and fails when the
  committed bundle, new untracked files included, differs from a fresh build.
  The report template's `package-lock.json` is now committed, so `npm ci`
  installs the exact dependency tree. (#9)

## v1.7.0 — 2026-06-09

### Added

- **OWASP MASVS / MASWE as first-class mobile taxonomies** — the `mobile-applications` pack declares `taxonomies: [masvs, maswe]` in `domain.yaml`, auto-seeded into a run's `taxonomies:` at `init-run`. Specialists emit `masvs` control IDs (`MASVS-<CATEGORY>-<n>`, on findings **and** capabilities) and `maswe` weakness IDs (`MASWE-####`, findings-only) in `control_mappings`, feeding two new gated synthesis rollups (`masvs-coverage.yaml`, `maswe-coverage.yaml` + their single-file schemas) and two new Coverage sub-tabs in the HTML report. New `apd-gauntlet refresh-mas` verb + bundled `masvs.json` (v2.1.0, 24 controls) and `maswe.json` (Beta, pinned per-refresh to an upstream commit). `data.meta.active_taxonomies` now lifts the run's taxonomy scope; `audit-report` gains `id_coverage_masvs` / `id_coverage_maswe` structural checks and `coverage_rollups_nonempty` extends to the MAS rollups.
- **Optional `taxonomies` field on `domain.yaml`** — any pack can declare default taxonomies that `init-run` unions into the run config (pack -> run auto-seed). Packs that omit the field are unaffected.
- **ADR 0014** — OWASP MAS (MASVS + MASWE) as mobile finding/capability taxonomies.
- HTML report: a new "Start here" reading-guide tab (`✦`, leftmost) that orients first-time readers with an orientation map, a vocabulary glossary, a reading workflow, and per-role focus paths, reading the run's live data for contextual guidance. Overview remains the default tab.
- **Threat-model report scene** — a dedicated report tab (after Coverage, before Attack paths) detailing the threat model: STRIDE×asset matrix, entries table, coverage-by-surface, an interactive trust-boundary surface map, and a supplied-vs-authored comparator. Gracefully omitted when no threat model exists (no user-supplied TM and none authored). Renders in the existing report design language (shared interactive `GraphView`, `apd-matrix`/`coverage-bar`/`contradiction` classes).
- **HTML report — Attack-paths "Enumerated paths" link to findings.** Each enumerated path whose edges traverse a finding now shows a `⚑ N finding(s)` indicator in its header (titled with the finding ids). Clicking a finding/capability id pill copies the id to the clipboard (with a toast); clicking the red "finding" chip immediately left of the id opens that finding in the Findings view (the same `onOpenFinding` navigation Overview/Annexes already use).
- **Two-channel distribution** ([ADR-0023](docs/adrs/0023-two-channel-distribution.md)) —
  additive packaging work that will ship under **1.7.0** (currently held); the
  gauntlet now distributes via two lockstep channels:
  - **PyPI engine** (`pip install apd-gauntlet`): fixed a wheel-crash-on-import
    bug where `schemas/` and `domains/` were resolved from the repo root (absent
    in a wheel). Both trees are now relocated into the package at
    `tools/apd_gauntlet/data/{schemas,domains}` (single source of truth), with
    **repo-root symlinks** for dev/test/CI back-compat. All package reads route
    through a new `tools/apd_gauntlet/resources.py` locator
    (`importlib.resources`, wheel-safe).
  - **Claude Code plugin** (`/plugin marketplace add illusconsulting/apd-gauntlet`
    then `/plugin install apd-gauntlet@apd-security`): manifest relocated to
    `.claude-plugin/plugin.json`; new `.claude-plugin/marketplace.json` registers
    the `apd-security` marketplace namespace; new `commands/run.md` adds the
    `/apd-gauntlet:run` slash command bridging the workflow runner (foreground,
    via `${CLAUDE_PLUGIN_ROOT}`). **Requires the `apd-gauntlet` PyPI package on
    PATH** — the plugin ships agents/skills; the workflow runner shells out to the
    CLI for deterministic passes.
  - **`NOTICE` file** at repo root attributes bundled, redistributed knowledge
    bases (MITRE ATT&CK, CAPEC, D3FEND, CWE, OWASP, NIST) to their respective
    authorities and licenses.
  - **Clean-wheel-install CI smoke gate** — the `release` workflow builds the
    sdist+wheel, installs it in a fresh venv, and confirms `apd-gauntlet
    --version` exits cleanly before PyPI publish.
- **Derived cross-framework views** ([ADR-0022](docs/adrs/0022-derived-cross-framework-views.md)) —
  a second class of taxonomy artifact authored by the synthesizer (not specialists)
  from existing anchors + an authoritative crosswalk catalog. First instance: the
  **MITRE CAPEC bridge** (`40-synthesis/capec-bridge.yaml`, schema
  `capec-bridge.schema.json`). It corroborates a finding's co-tagged `cwe` +
  `mitre_attack` technique via a CAPEC attack pattern that relates both, and
  suggests the missing side when only one is tagged (sub-techniques fold to their
  parent for matching). Emitted only when both `cwe` and `mitre_attack` are
  declared and a bridge/suggestion exists; absence of a CAPEC link is silent
  (never a mismatch). New `apd-gauntlet refresh-capec` + bundled `data/capec.json`;
  CAPEC ids resolve to titles + `capec.mitre.org` URLs. Rendered as a `CAPEC bridge`
  sub-tab in the report Coverage screen. (#110)
- **ATT&CK detection overlay** (derived view, ADR-0022) — for each ATT&CK
  technique a finding exposes, the data components ATT&CK says are required to
  detect it (the telemetry side, complementing the existing mitigation mapping;
  an APD Non-Repudiation concern). Gated on the `mitre_attack` anchor; emitted
  only when an exposed technique has detection data (silence-on-absence). The
  catalog is projected from the enterprise STIX bundle's v17+
  detection-strategy → analytic → data-component chain (`refresh-mitre` now also
  writes `data/mitre-attack-detection.json`). New `detection-coverage.yaml` +
  schema; rendered as an `ATT&CK detection` Coverage sub-tab. (#110)
- **Compliance projection layer** (derived view, ADR-0022) — the run's NIST
  800-53r5 coverage projected into the **HIPAA Security Rule** and **NIST CSF 2.0**
  via a published crosswalk, carrying the NIST IR 8477 STRM relationship and an
  `exact|partial` fidelity flag. Opt-in via a new run-config `projections:` list;
  control enhancements fold to their base for matching. New
  `hipaa-coverage.yaml` / `csf2-coverage.yaml` + shared `framework-coverage.schema.json`;
  rendered as a `Compliance crosswalk` Coverage sub-tab, explicitly labeled
  *derived projection — not an audit attestation*. The crosswalk data is
  **grounded against NIST CPRT exports** by `apd-gauntlet refresh-crosswalks`:
  control-level mappings are validated to be a subset of NIST's stated 800-53
  references and titles/provenance are pulled from the exports. (CSF 2.0's CPRT
  references are family-level and HIPAA 800-66r2's are publication-level, so the
  control-level selections are curated — CSF 2.0 within NIST's family scope, HIPAA
  from 800-66r1 Appendix D — and the grounding tool drops any mapping that exceeds
  NIST's scope.)

  None of the three derived views change `finding`/`capability` `control_mappings`
  or the run-config `taxonomies` enum. (#110)
- Per-finding attack-path "hop-strip" visualization in the Findings tab for
  `apath-*` risk findings — shows the path, the vulnerable hop, and layered
  fix-at-source + D3FEND choke-point recommendation markers, with a reverse
  link to the Attack Paths tab. Derived deterministically from the synthesis
  artifacts (no finding-schema change). New editorial audit check
  `attack_path_finding_strip_present`. ADR-0015.
- **Deterministic assembler owns all derived ids** — `apd-gauntlet canonicalize`
  now mints `tmeval-*` (from a new `tmeval_key`) and `dimpr-*` ids in addition to
  finding/capability ids, and a new `apd-gauntlet assemble-inventory` pass mints
  the asset-inventory `asset-/idn-/tb-` ids and wires `trust_boundaries.crosses`
  (authored by asset name) to the minted ids. New backstop linters
  `check_id_present` / `check_tmeval_id`. ADR-0020; `docs/deterministic-field-register.md`.
- **Report-accuracy and generation-UX remediation.** A capability whose `scope`
  is a mapping, not a string, is rejected: `validate` fails it, and a capability
  merge in `apply-clusters` leaves that scope out of the merged capability's
  scope and records a `failed_validation` reject instead of writing the
  mapping's Python repr as text. A new
  `SerializationIntegrityError` check runs just before `apply-clusters` writes
  its output, and the command exits 3 if a finding's `title`, `summary` or
  `detail`, or a capability's `title`, `description` or `scope`, holds a
  non-string or repr-like value. The whole-run validate gate before synthesis
  phase 5 now halts the workflow on error; it used to be advisory. The run
  config gains an optional `infrastructure` block: `mode` is `disabled`,
  `static` or `live` (reserved for a future release), and `static` lists IaC
  globs under `inputs/` for Kubernetes, Istio or Linkerd, Terraform, Helm and
  certificate or secret managers, with no leading `/` and no `..` allowed.
  `init-run` scaffolds it as a commented skeleton. The new `apd-gauntlet
  manual-audit-prompts <run-dir>` writes `40-synthesis/manual-audit-prompts.md`,
  which lists each blocked finding with the `kubectl` or `istioctl` commands
  its title or summary matches, to run against the live system. For multi-repo
  code recon, the run config and the code-evidence index accept an optional
  `repos[]` list (an index that declares one must tag every entry with its
  `repo`), `validate` warns when a declared
  repo has zero entries, and when the run config sets neither `subject` nor
  `cbm_project` the report title uses the primary repo
  ([ADR-0019](docs/adrs/0019-multi-repo-code-recon-and-cbm-boundary.md)). The
  six knowledge-base refresh fetchers now share `kb_fetch.fetch_pinned`, which
  caps the download size and returns a `source`, `source_sha256` and
  `fetched_at` provenance block, and the new CI gate
  `tools/check_kb_cache_freshness.py` checks that the fetched `data/*.json`
  caches carry a source, a SHA-256 or commit, and a fetch date (the files
  without that provenance are listed as exempt, with reasons). (#104)

### Changed

- **Threat-model-evaluator (`tmeval-*`) findings are now first-class downstream** (data-model audit F1). The decomposed pipeline previously unioned only `apath-*` tier-4 findings into the rollups/metrics/report, silently dropping `tmeval-*` from NIST/ATT&CK/9×N coverage, the severity distribution, and the report findings list (they surfaced only as `finding_id` references and in the threat-model scene). `rollup._load_deduped` now unions both `apath-*` and `tmeval-*`; `RunArtifacts` gains a `threat_model_findings` field (loaded from `40-threat-model/threat-model.findings.yaml`); the report `findings_array`, 9×N matrix, and taxonomy sweep include them; and `audit-report`'s `id_coverage_findings` widens to `deduped ∪ apath ∪ tmeval`. Report finding counts grow accordingly (the example golden moved from 90 → 93 findings).
- **Completeness gate distinguishes structural from editorial failures** (data-model audit F3). The agent receipt gains an optional `report_audit: {structural_failed, editorial_failed}` block that the `audit-report` worker lifts from the CLI's per-class counts; the workflow's synthesis-audit loop now blocks on **structural** completeness only (or an unverifiable report) and surfaces residual **editorial** completeness gaps non-blocking after the remediation cap (matching the LLM semantic-residual policy), rather than hard-blocking on any audit failure.
- **Report graphs are now interactive (Cytoscape.js).** The Attack-paths asset graph and the Threat-model surface map render with Cytoscape (dagre/fcose layouts) instead of static Mermaid — pan/zoom/drag, hover tooltips with provenance, and click-to-highlight-paths with two-way Attack-paths list↔graph cross-highlight. Mermaid was removed from the bundle (smaller `app.js`); the report stays self-contained/offline.
- **`runs/` is now fully gitignored and no longer ships pre-built runs.** The three shipped example runs (crAPI, authentik, caldera) were removed from version control and `runs/` (the gauntlet's output directory) is ignored in its entirety, so a tool user cannot accidentally commit a sensitive security review. The single canonical fixture is now the synthetic `examples/apd-20260601-claim-event-bus/expected/` run; all tests, the report golden, and the dev-template demo data (`report-template/data.js`) were repointed to it, and the README quickstart now validates the example. The report transforms' divergent-shape regression coverage is preserved by the in-memory synthetic-shape unit tests in `test_transform_new_shapes.py` (no real-run fixtures required).
- **Specialist agent guardrails hardened** against recurring output friction seen in multi-pack runs. The `apd-finding-schema` skill now stresses the 200-character `title` cap, mandatory YAML-quoting of colon/em-dash/leading-special scalars (an unquoted colon also aborts canonicalization), and writing findings only to the canonical tier path (no invented nested directories). The `apd-control-mappings` skill now stresses that every taxonomy mapping lives under `control_mappings` (never at the finding root) with the MITRE ATLAS key spelled `atlas` (not `mitre_atlas`), and that only concrete CWEs that resolve in the bundled catalog may be cited (no pillar/category CWEs such as CWE-320).
- **Documentation: foreground-execution requirement made consistent + preflight checklist added.** `running-the-gauntlet.md` gains a "Preflight: confirm scaffolding is in place" section and lists `plan-run` in the CLI reference; its Step 2 foreground statement is now the canonical source that the README, `architecture.md`, `extending-agents.md`, the workflow `meta.description`, and the `apd-orchestrator` shim all point to (run the gauntlet in-session — a background or headless launch can interrupt the subagent dispatches and leave an empty run directory). The operator install path now recommends an isolated install (venv / `pipx`), mirroring `CONTRIBUTING.md`. Docs and descriptions only — no runtime, CLI, schema, or report-template change.
- **Agents emit content only — no `id` / `schema_version`.** The nine specialist
  lens agents, the threat-model evaluator (now emits `tmeval_key`), the
  domain-improvement auditor, and intake (emits inventory records without ids,
  authors `crosses` by name) no longer author derived fields; the assembler is the
  sole author. Finding/capability/domain-improvement/asset-inventory schemas
  relaxed accordingly (permissive — existing valid records still validate).

### Fixed

- **Attack-path analysis wires declared crown jewels to inventory assets** (#84). Run-config `crown_jewels[]` are abstract pattern tokens (`pii_profile_store`, `tool_execution_capability`); `attack_path/build.py` previously realized a jewel only when an asset's `data_classifications` contained a naive `_store`-stripped token or an asset name case-insensitively equalled the pattern, so real inventories left every declared jewel an orphan sink and the deterministic floor enumerated zero paths. `_add_crown_jewels` now also matches a jewel's classification-alias tokens (the full pattern plus its generic-suffix-stripped head, exact-matched against the controlled `data_classifications` vocabulary) and honors an optional per-asset `realizes_crown_jewels: [pattern]` inventory field; any declared jewel that still wires to zero inbound edges is surfaced as a non-fatal `orphan_crown_jewels` build diagnostic rather than silently producing no paths.
- **`asset-graph.schema.json` accepts `threat_model_inferred` edge provenance** (#85). The always-on authored-baseline threat-model path emits `provenance.source: "threat_model_inferred"`, which was absent from the schema's `source` enum and failed validation for every such edge.
- **`validate` no longer rejects tier-4 analyzers' own derived evidence** (#86). The attack-path analyzer and threat-model evaluator legitimately cite their synthesis outputs (`40-synthesis/asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`, `deduped-findings.yaml`, `deduped-capabilities.yaml`) as evidence; these are now auto-exempted from the "not in intake brief" check via `ANALYZER_DERIVED_ARTIFACTS`, the way `code-evidence-index.yaml` already is. Genuinely unknown artifacts still fail.
- **`canonicalize` is resilient to a single unparseable file.** A lone malformed YAML record (e.g. an unquoted colon-bearing scalar a specialist emitted) raised `yaml.YAMLError` and aborted the entire canonicalize pass, so no file was canonicalized and the tier gate could not run. Per-file parse failures are now caught, skipped, collected on `CanonicalizeResult.parse_errors`, and reported by the CLI, while the remaining files canonicalize normally.
- **Rollup last-resort fallback now writes `metrics.yaml`** (data-model audit F2). When the deterministic `rollup` failed twice, the synthesizer last-resort was told to write "ONLY" `nist-coverage`/`attack-exposure`/`apd-coverage-matrix` — but `load_run` requires `metrics.yaml`, so `build-report` would `MissingArtifactError` and the completeness gate would throw, making the deepest fallback unable to ship any report. The last-resort prompt now also (re)writes `metrics.yaml` and pulls the tier-4 (`apath-*`/`tmeval-*`) findings.
- **`apply-clusters` no longer folds tier-4 findings into `deduped-findings.yaml`** (data-model audit F4). It ran with `include_attack_path=True` despite executing *before* attack-path/threat-model analysis; on a corruption-recovery re-run where a stale `attack-path.findings.yaml`/`threat-model.findings.yaml` already existed, `apath-*`/`tmeval-*` could be folded into the deduped corpus and double-rendered in the report. It now loads the corpus with `include_attack_path=False`; the tier-4 findings are unioned downstream where they belong.
- **Single shared severity normalizer** (data-model audit F6). The schema-token (`informational`) → template-token (`info`) mapping lived duplicated in `synthesis/metrics.py` and `report/transform.py`; it now lives once in `apd_gauntlet.severity` and both layers import it, so they can never drift.
- **Workflow `outputs` advisory label fixed** (data-model audit F5) — the `rollup` step's idempotency-guard label now lists `metrics.yaml` (which `build_rollups` writes).
- **Workflow no longer passes `--framework-version undefined`** — the `apd-gauntlet.js` setup phase built the `build-domain-skill` flag by blind string concatenation (`'--framework-version ' + args.framework_version`); when a run's `.apd-run.yaml` omitted `framework_version`, JS stringified `undefined` into the literal arg `--framework-version undefined`, which crashed `build_domain_skill` at `int('undefined')` in `_version_in_range`. The flag is now emitted only when `args.framework_version` is present; otherwise it is omitted and the CLI's own `default=__version__` applies.
- **`scaffold_run` stamps the live framework version** — `init-run`/`scaffold_run` hardcoded `framework_version: 1.1.0` in every generated `.apd-run.yaml`, recording a stale version and risking a spurious `framework_compat` failure in `build_domain_skill` if a pack floor ever rose above `1.1.0`. It now writes the live package `__version__`.

## v1.6.0 — 2026-06-03

### Added

- **`agentic-ai` domain pack** — security-architecture calibration for autonomous LLM-agent systems (tool-use agents, multi-agent topologies, self-improving loops), grounded in the OWASP LLM Top 10, MITRE ATLAS, and CSA MAESTRO.
- **`mobile-applications` domain pack** — OWASP MASVS/MASWE/MASTG + MAS Checklist + NIST SP 800-163r1 app-vetting, calibrated for the adversary-controlled-client surface (on-device storage, keystore/TEE, pinning, WebView/JS bridges, deep-link/IPC, in-process SDKs, reverse-engineering resilience, hardware attestation), anchored to the MITRE ATT&CK Mobile matrix.
- **MITRE ATLAS as a first-class finding taxonomy** — declare `mitre_atlas` in `.apd-run.yaml`; specialists emit `atlas` technique IDs (`AML.T####[.###]`) in structured finding fields, feeding the new `atlas-coverage` synthesis rollup and the report's taxonomy tooltips. New `apd-gauntlet refresh-atlas` verb + bundled `atlas-techniques.json`.
- **CSA MAESTRO as a recognized threat-model methodology** — `methodology_hint: maestro` routes supplied threat models through the free-form envelope with an L1–L7 → APD-goal mapping in the `apd-threat-model-methodologies` skill.
- **Per-goal domain-skill sidecars** — `build-domain-skill` emits `.claude/skills/apd-domain/by-goal/<goal>.md` (calibration files + merged surfaces + only that goal's common-patterns, with a `pruned` manifest) so each lens agent loads a goal-scoped slice; the full cross-goal `SKILL.md` is retained for intake / attack-path / domain-auditor. `--full-only` suppresses sidecars.
- **Report completeness gate** (#71) — `audit-report` now enforces 8 completeness checks on the built `data.js`, each classified `klass: structural` or `klass: editorial`. Structural checks (`attack_paths_present`, `d3fend_overlay_present`, `apd_matrix_nonempty`, `coverage_rollups_nonempty`, `taxonomy_titles_resolve`, `section_errors_empty`) and editorial checks (`exec_summary_present`, `editorial_sections_present`) each exempt legitimately-empty states. The workflow's synthesis-audit phase blocks a run (throws) when a structural failure is unresolved after the two-attempt remediation cap — a degraded HTML report (placeholder exec summary, mismatched counts, empty attack-paths or D3FEND) can no longer ship silently. `report-audit.yaml` gains a per-check `klass` field; `audit-report` prints `structural_failed`/`editorial_failed` counts.
- **`refresh-cwe` `<Category>` projection** (#71) — `refresh-cwe` now also projects CWE `<Category>` entries (e.g. CWE-840 "Business Logic Errors") into the bundled reference data so cited categories resolve in report tooltips and survive a refresh.
- **ADR 0011** — Report completeness gate — block on degraded HTML reports.
- **ADR 0012** — MITRE ATLAS as a first-class finding taxonomy.

### Changed

- ATT&CK Mobile technique titles and mitigation→technique crosswalk merged additively into the bundled catalogs so Mobile-pack runs render names rather than bare IDs.
- HTML report now renders `data.meta` diagnostics and informational-severity findings that the template previously dropped.

### Fixed

- Golden-run framework defects (F1–F5): new `apd-gauntlet canonicalize`, non-vacuous record/ID validators, loader capability-id guard, deduped-union resolver, and attack-path crown-jewel↔asset name-collision handling.

## v1.5.1 — 2026-05-27

### Added

- **`api-security` domain pack** under `domains/api-security/` — 14 files (878 lines) anchored to OWASP API Top 10 (2023), PCI-DSS 4.0, GDPR, NIST 800-63B, SOC 2. Ships 8 crown jewels and 9 attacker positions covering authenticated/unauthenticated/compromised attacker scenarios common to API-style production systems. Severity rubric calibrates to API1-API10 categories + breach-notification thresholds.
- **Canonical example fixture run** at `runs/apd-20260527-crapi-owasp-api-top10/` — full APD gauntlet output against OWASP crAPI v1.1.5 (Apache-2.0, intentionally vulnerable multi-service automotive B2C demo). 63 deduped findings + 22 capabilities + complete 40-synthesis output including `report-data.yaml`. Used by Phase D HTML report integration tests as the golden fixture.

### Changed

- Phase D tests now reference `example_run` fixture (was `legacy_example_run`); pointed at the crAPI run.
- `report-template/data.js` (dev template demo data) regenerated from the crAPI run.
- `tests/fixtures/report-html/crapi-golden-data.js` replaces `legacy_example-golden-data.js` as the golden-output regression check.

### Known limitations

- 5 transform tests skip cleanly because crAPI's synthesizer-emitted YAML files use shape variants (`techniques:` dict vs `technique:` list in attack-exposure.yaml; goal-keyed vs component-keyed apd-coverage-matrix; missing family_summary in nist-coverage) that the v1.5.0 transforms don't yet normalize. Tracked as a polish item — transforms should be made tolerant of both shapes in a follow-up.

## v1.5.0 — 2026-05-27

### Added

- **Interactive HTML advisory report** at `runs/<run_id>/40-synthesis/report-html/`.
  Auto-generated by the synthesizer's trailing `apd-gauntlet build-report` step.
  Self-contained, offline-openable, no network or Node toolchain on the
  consumer side. Six tabs: Overview, Findings, Capabilities, Coverage,
  Attack paths (v1.4 enumeration + D3FEND overlay), Annexes.
- **`apd-gauntlet build-report <run_dir>`** CLI verb. Idempotent;
  re-runnable without re-running the gauntlet itself.
- **`40-synthesis/report-data.yaml`** — new optional synthesizer emission
  carrying the editorial prose blocks the HTML report cannot derive
  algorithmically (exec_summary, headline_findings, strengths caveats,
  next_steps, posture_summary). Schema-validated like the other 40-synthesis
  files; cross-file validator checks that ids resolve.

### Changed

- `apd-synthesizer` agent now emits `report-data.yaml` and invokes
  `apd-gauntlet build-report` at the end of every run.
- `tools/apd_gauntlet/data/` gains a precompiled React 18 + Mermaid bundle
  under `report-template/`. Rebuilt by contributors via
  `python tools/build_report_template.py` (Node 20+ + esbuild required).
- CI runs `tools/check_report_template_freshness.py` to ensure the
  precompiled bundle matches the JSX source under `report-template/`.

### Compatibility

This release is fully additive. v1.4 outputs (markdown, all existing YAMLs,
attack-paths, D3FEND coverage) are byte-identical. Runs without
`report-data.yaml` produce a degraded-but-complete HTML report.

## [1.4.0] - 2026-05-26

### Added

- **`apd-attack-path-analyzer` tier-4 agent** — activation-gated BloodHound-style bounded enumeration over a partial provenance-and-confidence-aware graph from declared attacker positions to declared crown jewels. Findings use `agent: attack_path_analyzer` and id prefix `apath-`.
- **Asset graph, attack-paths, defense-graph schemas** capturing nodes, edges, paths, and the D3FEND defensive overlay on bottleneck edges. Each edge carries `provenance.source` and `confidence`; the analyzer never invents nodes or edges.
- **Asset inventory** machine-readable artifact emitted by intake at `00-context/asset-inventory.yaml` when crown jewels are declared.
- **D3FEND defensive overlay** on bottleneck edges with capability-backing-vs-net-new partitioning. The D3FEND-must-counter-ATT&CK discipline rule (per `tools/apd_gauntlet/data/d3fend.json`) prevents name-similarity mappings.
- **Inline Mermaid attack-path diagrams** in the advisory report (≤50 nodes per diagram; partitioned by `attacker_position` for larger graphs).
- **Domain pack additions** for `crown_jewels[]`, `attacker_positions[]`, `default_trust_boundaries[]`. PBM domain pack ships 3 crown jewels, 5 attacker positions, and 3 default trust boundaries.
- **Run-config additions** for `crown_jewels[]` / `attacker_positions[]` overrides plus the `attack_path_analysis` tuning block (`max_hop`, `max_paths_per_pair`, `bottleneck_threshold`).
- **CLI subcommand `apd-gauntlet analyze-attack-paths <run_dir>`** for deterministic, headless graph build + path enumeration + D3FEND overlay + finding emission.
- **`apd-attack-path-discipline` skill** codifying never-invent rules for nodes and edges, confidence-floors-severity rule, bounded-enumeration discipline, and the block-on-missing-crown-jewels rule.
- **New schemas**: `asset-inventory.schema.json`, `asset-graph.schema.json`, `attack-path.schema.json`, `defense-graph.schema.json`.
- **ADR 0010** — Attack-path analysis on partial graphs.
- **`docs/attack-path-analysis.md`** — operator guide for declaring crown jewels and attacker positions, tuning enumeration bounds, reading the outputs.
- **Bundled example** `examples/apd-20260601-claim-event-bus/` exercises the full v1.4 pipeline end-to-end (3 attacker positions × 2 crown jewels yields 75 paths, 24 bottleneck edges).

### Changed

- `finding.schema.json` — `agent` enum gains `attack_path_analyzer`; `id` / `cross_references` / `merged_from` patterns accept `apath-[0-9a-f]{8}`.
- `run-config.schema.json` — new optional `crown_jewels`, `attacker_positions`, `attack_path_analysis` blocks (all additive).
- `domain.schema.json` — new optional `crown_jewels`, `attacker_positions`, `default_trust_boundaries` arrays (all additive).
- `defense-graph.schema.json` — `capability_ids` pattern corrected to accept the prefix-cap form (e.g., `auth-cap-7c2a4f91`) per `capability.schema.json`.
- `asset-graph.schema.json` — `provenance.source` enum extended to include `asset_inventory`.
- `apd-intake` — gains `00-context/asset-inventory.yaml` emission when crown jewels are declared.
- `apd-orchestrator` — topology now describes 16 agents; Phase 5.6 dispatches the analyzer.
- `apd-synthesizer` — 9×N coverage matrix scan now includes `tmeval-` and `apath-` findings from tier-4 sources.
- Validator picks up `asset-inventory.yaml`, `asset-graph.yaml`, `attack-paths.yaml`, `defense-graph.yaml`, and `attack-path.findings.yaml`; new cross-file pass checks edge endpoints reference real `nodes[].node_id`, real findings, and real capabilities.
- Finding/capability YAML root keys standardized on singular form (`finding:` / `capability:`) per the validator's `RECORD_KINDS` convention; loaders tolerate both forms for forgiveness.

### Backward compatibility

All changes additive within v1.x; `framework_compat: ">=1.0.0,<2.0.0"` continues to accept v1.4.0. A v1.1-style run with no `crown_jewels` and no `attacker_positions` produces identical output to v1.3 (analyzer skips silently and writes `40-synthesis/attack-path-analyzer-skipped.txt`).

## [1.3.0] - 2026-05-26

### Added

- **`apd-threat-model-recon` tier-0 agent** — parses user-supplied threat models into a normalized graph at `00-context/threat-model-normalized.yaml`. Activation-gated on `.apd-run.yaml` declaring `threat_model: <path>` (or intake auto-detecting a TM-like artifact).
- **`apd-threat-model-evaluator` tier-4 agent** — evaluates the normalized TM against specialist findings/capabilities; emits three finding flavors: coverage gap (`disposition: gap`), contradiction (`disposition: risk`), silence (`disposition: uncertainty`). Findings use `agent: threat_model_evaluator` and id prefix `tmeval-`.
- **Native methodology support**: STRIDE (OWASP Threat Dragon JSON, Microsoft TMT .tm7, STRIDE-per-element Markdown/CSV), LINDDUN (Markdown/CSV tables), attack trees (indented prose, ADTool XML, JSON). PASTA / VAST / Trike / free-form prose accepted with reduced extraction confidence.
- **CLI subcommand `parse-threat-model`** — standalone parser dispatcher; auto-detects format from extension or honors `--methodology-hint`.
- **CLI flags on `init-run`**: `--threat-model <path>` and `--methodology-hint <name>` pre-populate the run-config.
- **New skill `apd-threat-model-methodologies`** — canonical STRIDE/LINDDUN→APD-goal mapping tables (single source of truth shared with Python mapping module) + discipline rules.
- **New schemas**: `threat-model-normalized.schema.json`, `threat-model-coverage.schema.json`.
- **Validator extensions**: `tmeval-` findings must cite the normalized TM (or source artifact) in evidence; contradiction findings must cross-reference the contradicting specialist finding ID.
- **New dependency**: `lxml>=4.9` (used by Microsoft TMT and ADTool XML parsers with XXE-safe flags).
- **ADR 0009** — Methodology-aware threat-model evaluator.
- **`docs/threat-modeling.md`** operator guide.

### Changed

- `finding.schema.json` — `agent` enum gains `threat_model_evaluator`; `id` pattern extended to accept `tmeval-` prefix.
- `run-config.schema.json` — accepts optional `threat_model: <path>` and `methodology_hint: <name>` fields.
- **Shared `$defs` extraction** (carry-forward from Phase A): ATT&CK / D3FEND / CWE patterns now defined once in `schemas/_defs.schema.json` and `$ref`'d by record schemas. Behavior unchanged.
- **`owasp_llm_top10` pattern tightened** (carry-forward from Phase A): now `^LLM(0[1-9]|10)$` (was `^LLM[0-9]{2}$` which accepted non-existent codes).
- **`refresh_mitre.py` aligned** (carry-forward from Phase A): constants renamed to `MAX_RESPONSE_BYTES` / `DEFAULT_TIMEOUT_SECONDS` matching the v1.2 triad; Content-Length pre-check added.
- **CLI `validate` now scans coverage rollups** (carry-forward from Phase A): cwe-coverage / owasp-coverage / d3fend-coverage in `40-synthesis/` are now validated by `apd-gauntlet validate` (previously only by tests).
- **ADR 0007 reformatted** (carry-forward from Phase A): now matches the canonical 0001-0008 hyphen+colon style.

### Backward compatibility

- All schema changes additive. v1.2-format runs (and v1.1, v1.0) validate unchanged.
- Minimum-viable run with no `threat_model:` declaration produces identical output to v1.2.
- PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.3.0 with no changes.

## [1.2.0] - 2026-XX-XX

### Added

- **Multi-framework taxonomy mappings** on findings: CWE, OWASP Top 10 (web), OWASP API Top 10, OWASP LLM Top 10 (all optional, declared per run via `taxonomies:` in `.apd-run.yaml`).
- **MITRE D3FEND mappings on capabilities**, with required `counters_attack` cross-reference to ATT&CK techniques the capability defends against. Sub-technique parent matching: `T1110.001` is satisfied by `T1110` declared in `mitre_attack[]`.
- **`mitre_attack` field on capabilities** (parallel to the one on findings) — documents which ATT&CK techniques the capability defends against. Enables the D3FEND `counters_attack` cross-reference rule.
- **Per-run taxonomy scoping** via `taxonomies:` field in `.apd-run.yaml`. CWE/ATT&CK/D3FEND default-on; OWASP variants opt-in.
- **Intake `taxonomy_suggestions` block** auto-detects relevant surfaces (web routes, OpenAPI specs, LLM SDK imports) and writes advisory suggestions to the context brief.
- **Three new synthesizer coverage rollups**: `cwe-coverage.yaml`, `owasp-coverage.yaml`, `d3fend-coverage.yaml` (the last includes a `counter_coverage` view showing which exposed ATT&CK techniques have D3FEND-backed capabilities countering them).
- **Three new schemas**: `cwe-coverage.schema.json`, `owasp-coverage.schema.json`, `d3fend-coverage.schema.json`.
- **Three new CLI subcommands**: `refresh-cwe`, `refresh-owasp`, `refresh-d3fend` (each applies the v1.0 security-review hardening: 60s timeout, 200 MiB cap, `source_sha256` in projected payload).
- **Seeded reference data** at `tools/apd_gauntlet/data/`: 969 CWEs (live-fetched v4.20), 30 OWASP categories (3 lists × 10, seed-only), 149 D3FEND techniques with 3234 counter relations (live-fetched).
- **`apd-control-mappings` skill** gains per-taxonomy discipline sections (CWE, OWASP Top 10 web/API/LLM, D3FEND).
- **`apd-intake` agent** gains taxonomy auto-detection step.
- **`apd-synthesizer` agent** documents the three new rollup outputs.
- **All 9 specialist agents** reference the v1.2 taxonomy scope.
- **`init-run --taxonomies`** CLI flag pre-populates the run-config.
- **Cross-reference validation**: D3FEND `counters_attack` must intersect the capability's `mitre_attack[].technique` list (with sub-technique parent matching).
- **ADR 0008** — Multi-framework taxonomy mappings.
- **`docs/taxonomy-mappings.md`** operator guide.

### Changed

- `finding.schema.json` — `control_mappings` accepts optional `cwe`, `owasp_top10`, `owasp_api_top10`, `owasp_llm_top10` arrays.
- `capability.schema.json` — `control_mappings` accepts optional `mitre_attack` (parallel to finding's) and `d3fend` arrays.
- `run-config.schema.json` — accepts optional `taxonomies` array.
- D3FEND ID pattern widened from `^D3-[A-Z]{2,5}$` to `^D3-[A-Z]{2,7}$` (real MITRE D3FEND data contains 6- and 7-letter codes like `D3-PHDURA`, `D3-DNSTA`).
- `docs/architecture.md`, `docs/running-the-gauntlet.md`, `docs/schema-evolution.md`, `README.md` — refreshed for v1.2 additions.

### Backward compatibility

- All schema changes additive. v1.1-format runs validate unchanged against v1.2 schemas.
- Minimum-viable run with no `taxonomies:` declaration produces identical output to v1.1.
- PBM domain pack (`framework_compat: ">=1.0.0,<2.0.0"`) consumes v1.2.0 with no changes.

## [1.1.0] - 2026-05-XX

### Added

- Optional `apd-code-recon` intake-tier agent that uses the DeusData [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) graph to produce a code-grounded view of the system under review. Gated by `code_recon` setting in `.apd-run.yaml` (`enabled` / `auto` / `disabled`). See [ADR 0007](docs/adrs/0007-optional-code-reconnaissance-via-cbm.md).
- New schemas: `schemas/run-config.schema.json` (validates `.apd-run.yaml`) and `schemas/code-evidence-index.schema.json` (validates the code-evidence index).
- New template: `templates/code-architecture-brief.template.md`.
- CLI: `apd-gauntlet validate-run-config <path>` for operator parity with `validate-domain`.
- Validator now schema-validates `00-context/code-evidence-index.yaml` when present and treats it as a known artifact source for specialist evidence pointers.

### Changed

- `scaffold_run` emits `code_recon: auto` and `framework_version: 1.1.0` in the generated `.apd-run.yaml`.
- `apd-evidence-discipline` skill documents code-evidence pointer format and restates the input-trust boundary for CBM-returned content.
- `apd-orchestrator` agent gains a conditional Phase 1.5 dispatching `apd-code-recon`.

### Compatibility

- Backwards-compatible with v1.0 run directories: runs without a `.apd-run.yaml` skip Phase 1.5 entirely.
- Domain packs declaring `framework_compat: ">=1.0.0,<2.0.0"` (e.g. PBM) continue to work unchanged.

## [1.0.0] - 2026-05-XX

First public release.

### Added

- Twelve agents (orchestrator, intake, synthesizer, nine specialists) for APD security architecture reviews.
- Five skills providing framework discipline, schemas, evidence rules, control mappings, and (generated) domain content.
- JSON Schemas for finding, capability, contradiction, severity-disagreement, coverage-matrix, NIST coverage, ATT&CK exposure, and domain pack records.
- `apd-gauntlet` Python CLI with `validate`, `init-run`, `build-domain-skill`, `summarize`, `lint-agents`, `check-ids`, `validate-domain`, and `refresh-mitre` subcommands.
- Pluggable domain pack mechanism with PBM (Pharmacy Benefit Management) shipped as the first pack.
- Curated synthetic claim-event-bus example with CI-validated expected outputs.
- Claude Code plugin manifest.
- CI workflows for validation, Python tests, markdown lint, and release.
