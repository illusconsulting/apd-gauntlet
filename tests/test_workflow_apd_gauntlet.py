"""Structural contract test for the workflow runner .claude/workflows/apd-gauntlet.js.

The runner is plain JS for the Workflow primitive; it cannot run under plain
node and CI has no Node step. We pin its contract by reading it AS TEXT
(mirrors tests/test_orchestrator_topology.py): meta block + phase pins +
agentType resolution against .claude/agents/ + CLI-command resolution against
the live Click registry + RECEIPT-field fidelity against the schema + the
audit loop-cap literal + the synthesizer-fallback and typed-signal pins.
"""
from __future__ import annotations

import json
import pathlib
import re

from apd_gauntlet.cli import main as cli

REPO = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO / ".claude" / "workflows" / "apd-gauntlet.js"
AGENTS_DIR = REPO / ".claude" / "agents"
RECEIPT_SCHEMA = REPO / "schemas" / "agent-receipt.schema.json"

# Expanded §4/§7 phase pins (5a..5g surfaced). meta.phases lists every phase
# name. But the runner emits the three TIER phases DYNAMICALLY (runTier(name)
# calls phase(name) internally), so a literal `phase('tier-1')` never appears in
# the source — those three are pinned via the runTier(...) call tokens instead.
# Every OTHER phase is emitted by a direct `phase('X')` literal in the body.
EXPECTED_PHASES = [
    "setup", "intake", "code-recon", "threat-model-author", "tm-recon",
    "canonicalize",
    "tier-1", "tier-2", "tier-3",
    "synthesis-cluster", "synthesis-adjudicate", "synthesis-apply",
    "synthesis-rollup", "synthesis-fallback",
    "synthesis-report", "synthesis-build", "synthesis-audit",
    "tmeval", "apath",
    "domain-coverage-delta", "domain-improvements", "closeout",
]

# Phases emitted by a DIRECT `phase('X')` literal (checked as call literals).
DIRECT_PHASE_LITERALS = [
    "setup", "intake", "code-recon", "threat-model-author", "tm-recon",
    "synthesis-cluster", "synthesis-adjudicate", "synthesis-apply",
    "synthesis-rollup", "synthesis-fallback",
    "synthesis-report", "synthesis-build", "synthesis-audit",
    "tmeval", "apath",
    "domain-coverage-delta", "domain-improvements", "closeout",
]

# Tier phases emitted DYNAMICALLY via runTier(name){ phase(name) } — checked via
# the runTier('tier-N', ...) call tokens, NOT via a `phase('tier-N')` literal.
TIER_PHASES_VIA_RUNTIER = ["tier-1", "tier-2", "tier-3"]

# Phases that are declared in meta.phases and referenced only via opts.phase in
# pyStep (not via a direct `phase('X')` literal or a `runTier('X', ...)` call).
# 'canonicalize' is dispatched 3× inside runTier as pyStep('canonicalize',
# {phase:'canonicalize', ...}) — the phase group is advisory display only.
PYSTEP_PHASE_REFS = ["canonicalize"]


def _text() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_runner_file_exists() -> None:
    assert RUNNER.is_file(), f"missing runner at {RUNNER}"


def test_meta_block_is_pure_literal_first_export() -> None:
    text = _text()
    assert "export const meta = {" in text
    assert "name: 'apd-gauntlet'" in text
    assert "description:" in text
    assert "phases:" in text


def test_every_expected_phase_present_in_meta_phases() -> None:
    text = _text()
    # Bounded extraction of the phases:[...] array (meta is a pure literal).
    m = re.search(r"phases:\s*\[(.*?)\]", text, re.DOTALL)
    assert m, "phases:[...] array not found in meta"
    phases_blob = m.group(1)
    found = set(re.findall(r"'([^']+)'", phases_blob))
    for p in EXPECTED_PHASES:
        assert p in found, f"phase {p!r} missing from meta.phases"


def test_direct_phase_literals_invoked_in_body() -> None:
    """Every non-tier phase is emitted by a literal phase('X') call in the body."""
    text = _text()
    for p in DIRECT_PHASE_LITERALS:
        assert f"phase('{p}')" in text, f"phase('{p}') not invoked in body"


def test_tier_phases_invoked_via_runtier() -> None:
    """tier-1/2/3 are emitted dynamically by runTier(name){ phase(name) }, so they
    appear as runTier('tier-N', ...) call tokens, not as phase('tier-N') literals."""
    text = _text()
    for p in TIER_PHASES_VIA_RUNTIER:
        assert f"runTier('{p}'" in text, f"runTier('{p}', ...) call not found"
        # And confirm they are NOT (mistakenly) also emitted as direct literals,
        # which would mean the runner double-emits the phase.
        assert f"phase('{p}')" not in text, (
            f"tier phase {p} should be emitted via runTier(name), not a phase('{p}') literal"
        )


def test_every_meta_phase_is_emitted_one_way_or_the_other() -> None:
    """Union of the direct-literal set, the runTier tier set, and the pyStep
    phase-ref set == meta.phases.  'canonicalize' is in PYSTEP_PHASE_REFS because
    it is dispatched via pyStep('canonicalize', {phase:'canonicalize', ...}) inside
    runTier rather than via a direct phase() literal or a runTier() call."""
    assert (
        set(DIRECT_PHASE_LITERALS) | set(TIER_PHASES_VIA_RUNTIER) | set(PYSTEP_PHASE_REFS)
        == set(EXPECTED_PHASES)
    )


def _referenced_agent_types(text: str) -> set[str]:
    """All agentTypes the runner dispatches, from BOTH dispatch forms:
      - `llmStep('apd-foo', ...)`   — agent is the FIRST POSITIONAL arg
      - `agent(prompt, {agentType: 'apd-foo', ...})` — raw agentType opts key
    The dynamic lens dispatch is `llmStep('apd-' + lens, ...)`, which yields the
    fragment 'apd-' (a bare prefix); drop it and pin the concrete lens set
    separately so 'apd-' is never treated as a real agentType.
    """
    refs = set(re.findall(r"llmStep\('([^']+)'", text))
    refs |= set(re.findall(r"agentType:\s*'([^']+)'", text))
    refs.discard("apd-")  # the 'apd-' + lens concat fragment, not a real agent
    return refs


def test_every_agenttype_resolves_to_an_agent_file() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    # The dynamic 'apd-' + lens concat must also resolve; pin the lens set.
    lenses = ["confidentiality", "integrity", "availability",
              "distributed", "resilient", "ephemeral",
              "authenticity", "non-repudiation", "immutability"]
    referenced |= {"apd-" + lens for lens in lenses}
    for at in referenced:
        assert (AGENTS_DIR / f"{at}.md").is_file(), f"agentType {at} has no .claude/agents/{at}.md"


def test_orchestrator_is_not_an_agenttype() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    assert "apd-orchestrator" not in referenced, "orchestrator is retired; never dispatch it"


def test_expected_agent_set_is_referenced() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    # The fixed (non-lens) dispatches the runner must name. apd-intake /
    # apd-code-recon / apd-threat-model-recon / apd-cluster-adjudicator /
    # apd-report-writer / apd-threat-model-evaluator / apd-attack-path-analyzer
    # go through llmStep('apd-...'); apd-report-auditor (schema-less) and
    # apd-synthesizer (fallback) go through raw agent(..., {agentType:'...'}).
    for at in ("apd-intake", "apd-code-recon", "apd-threat-model-recon",
               "apd-cluster-adjudicator", "apd-report-writer", "apd-report-auditor",
               "apd-threat-model-evaluator", "apd-attack-path-analyzer", "apd-synthesizer"):
        assert at in referenced, f"{at} not dispatched by the runner"


def test_every_cli_command_is_registered() -> None:
    text = _text()
    registered = set(cli.commands.keys())
    # The runner executes CLI commands ONLY via pyStep('<cmd>', ...); extract
    # exactly those command tokens. We deliberately do NOT scrape the broad
    # `apd-gauntlet <word>` regex: the runner's log()/comment/instruction prose
    # contains non-command tokens ('apd-gauntlet runner: setup', 'apd-gauntlet
    # workflow') that are not subcommands, and the recon-agent prose mentions
    # commands the agents run internally (parse-threat-model, analyze-attack-paths)
    # which the runner never invokes directly. pyStep('<cmd>') is the true
    # CLI-dispatch contract.
    cmds = set(re.findall(r"pyStep\('([a-z][a-z0-9-]+)'", text))
    assert cmds, "no pyStep('<cmd>') calls found — extraction regex drifted"
    for c in cmds:
        assert c in registered, f"pyStep references unregistered command {c!r}"


def test_referenced_commands_cover_the_pipeline() -> None:
    text = _text()
    # init-run is intentionally ABSENT: per design §4 the run is scaffolded
    # before the workflow runs (args IS .apd-run.yaml), so setup VALIDATES the
    # existing scaffold via pyStep('validate', ...) rather than creating it.
    for c in ("build-domain-skill", "validate-domain", "validate",
              "cluster-candidates", "apply-clusters", "rollup", "build-report",
              "audit-report", "summarize", "assemble-c4"):
        assert f"pyStep('{c}'" in text, f"pipeline command {c} not invoked via pyStep"
    assert "pyStep('init-run'" not in text, (
        "init-run must NOT be dispatched: the run is pre-scaffolded; setup validates it"
    )


def test_receipt_constant_matches_schema_required() -> None:
    text = _text()
    schema = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    schema_required = set(schema["required"])
    # Anchor on `const RECEIPT` so we match the top-level RECEIPT required[] and
    # not some other (e.g. sub-object) required: array, regardless of ordering.
    m = re.search(r"const RECEIPT\s*=.*?required:\s*\[([^\]]*)\]", text, re.DOTALL)
    assert m, "RECEIPT required array not found"
    js_required = set(re.findall(r"'([^']+)'", m.group(1)))
    assert js_required == schema_required, (
        f"RECEIPT required {js_required} != schema required {schema_required}"
    )


def test_audit_loop_cap_literal_present() -> None:
    text = _text()
    # The cap is N=2 (3 attempts: initial + 2 remediations). Pin the literal so
    # it cannot regress silently.
    assert "i <= 2" in text, "audit loop cap (i <= 2) literal missing"


def test_typed_signals_and_fallback_pinned() -> None:
    text = _text()
    assert "/exit=2/" in text, "AdjudicationMissing (exit 2) branch missing"
    assert "synthesizer-fallback" in text, "synthesizer fallback label missing"
    assert "agentType: 'apd-synthesizer'" in text, "fallback must dispatch apd-synthesizer"


def test_skip_sentinel_convention_documented() -> None:
    text = _text()
    assert ".skipped" in text, "idempotent-skip sentinel convention missing"


# ---------------------------------------------------------------------------
# plugin.json manifest contract (Task 7)
# ---------------------------------------------------------------------------

PLUGIN_MANIFEST = REPO / ".claude-plugin" / "plugin.json"


def test_plugin_manifest_version_matches_pyproject() -> None:
    """plugin.json, pyproject.toml, and tools/apd_gauntlet/__init__ must agree (no skew)."""
    import re

    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    py_version = re.search(r'(?m)^version = "([^"]+)"', pyproject).group(1)
    init_text = (REPO / "tools" / "apd_gauntlet" / "__init__.py").read_text(encoding="utf-8")
    init_version = re.search(r'__version__ = "([^"]+)"', init_text).group(1)

    assert manifest["version"] == py_version, (
        f"plugin.json version is {manifest['version']!r}; pyproject is {py_version!r}"
    )
    assert init_version == py_version, (
        f"__init__ version is {init_version!r}; pyproject is {py_version!r}"
    )
    assert py_version == "1.7.0", (
        f"expected the 1.7.0 release version; pyproject reports {py_version!r}"
    )


def test_plugin_manifest_has_no_workflows_key() -> None:
    """plugin.json must NOT contain a 'workflows' key (M2: unverified schema key)."""
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    assert "workflows" not in manifest, (
        "plugin.json must not contain a 'workflows' key — "
        "there is no verified plugin-manifest schema for it and a strict "
        "additionalProperties:false manifest would reject it"
    )


# ---------------------------------------------------------------------------
# Gap-1 (phase ordering) + Gap-2 (asset-inventory) fix pins
# ---------------------------------------------------------------------------


def test_tier4_precedes_rollup_build_audit() -> None:
    """Gap-1 fix: tmeval/apath (tier-4) run BEFORE the coverage rollup and the
    HTML build/audit, so the rollup, report, and audit all include the apath-*/
    tmeval-* findings (the old order built + audited the report before they existed)."""
    text = _text()
    i_tmeval = text.index("phase('tmeval')")
    i_apath = text.index("phase('apath')")
    i_rollup = text.index("phase('synthesis-rollup')")
    i_build = text.index("phase('synthesis-build')")
    i_audit = text.index("phase('synthesis-audit')")
    assert i_tmeval < i_rollup, "tmeval must precede the rollup"
    assert i_apath < i_rollup, "apath must precede the rollup"
    assert i_rollup < i_build < i_audit, "order must be rollup -> build -> audit"


def test_synthesizer_fallback_defers_coverage_rollups() -> None:
    """Gap-1 fix: the synthesizer fallback writes the corpus + report-data but NOT
    the coverage rollups — the deterministic post-apath rollup owns nist/attack/matrix."""
    text = _text()
    assert "label: 'synthesizer-fallback'" in text, "synthesizer-fallback dispatch missing"
    assert "do NOT write the coverage rollups" in text, (
        "the synthesizer fallback must defer coverage rollups to the post-apath rollup"
    )


def test_intake_always_emits_asset_inventory() -> None:
    """Gap-2 fix: intake is ALWAYS instructed to emit asset-inventory.yaml (a required
    input for the rollup + build-report), no longer gated on crown_jewels."""
    text = _text()
    m = re.search(r"llmStep\('apd-intake'.*?\}\);", text, re.DOTALL)
    assert m, "intake llmStep not found"
    intake = m.group(0)
    assert "asset-inventory.yaml" in intake, "intake must emit asset-inventory.yaml"
    assert "Array.isArray(args.crown_jewels)" not in intake, (
        "intake asset-inventory emission must be unconditional (crown_jewels gate removed)"
    )


def test_runner_uses_domains_list_not_singular() -> None:
    text = _text()
    assert "args.domains" in text, "runner must read args.domains"
    assert re.search(r"args\.domain(?!s)", text) is None, \
        "runner still references singular args.domain"


def test_build_domain_skill_step_always_runs() -> None:
    """The build-domain-skill setup step must bypass the idempotent-skip guard so the
    Python command itself decides freshness (pack-set staleness fix)."""
    text = _text()
    assert re.search(r"pyStep\('build-domain-skill'[\s\S]{0,400}?alwaysRun:\s*true", text), \
        "build-domain-skill step must carry alwaysRun: true"


def test_build_domain_skill_framework_version_flag_is_guarded() -> None:
    """The --framework-version flag must be GUARDED on args.framework_version being
    present. Unconditional `'--framework-version ' + args.framework_version` produces
    the literal `--framework-version undefined` when the run-config omits the key,
    which then crashes build_domain_skill at int('undefined') in _version_in_range.
    When the key is absent the flag must be omitted so the CLI's own
    `default=__version__` applies."""
    text = _text()
    m = re.search(r"pyStep\('build-domain-skill', \{[\s\S]*?\n\}\);", text)
    assert m, "build-domain-skill pyStep block not found"
    block = m.group(0)
    # The buggy unconditional concat must be gone.
    assert "cliArgs: '--framework-version ' + args.framework_version," not in block, (
        "unconditional '--framework-version ' + args.framework_version yields "
        "'--framework-version undefined' when args.framework_version is absent"
    )
    # The flag must be emitted only behind a presence guard on args.framework_version.
    assert "args.framework_version ?" in block, (
        "build-domain-skill must guard --framework-version on args.framework_version "
        "(ternary), omitting the flag when the key is absent"
    )


def test_phase_5h_names_in_meta_and_body() -> None:
    text = _text()
    for p in ("domain-coverage-delta", "domain-improvements"):
        assert f"phase('{p}')" in text, f"phase('{p}') not invoked in body"


def test_phase_5h_is_after_audit_and_before_closeout() -> None:
    text = _text()
    i_audit = text.index("phase('synthesis-audit')")
    i_delta = text.index("phase('domain-coverage-delta')")
    i_imp = text.index("phase('domain-improvements')")
    i_closeout = text.index("phase('closeout')")
    assert i_audit < i_delta < i_imp < i_closeout


def test_domain_auditor_dispatch_is_non_blocking() -> None:
    """The apd-domain-auditor llmStep must NOT be wrapped in a HALT (throw)."""
    text = _text()
    assert "llmStep('apd-domain-auditor'" in text
    # Bound a window from the domain-improvements phase to closeout and assert no throw.
    window = text[text.index("phase('domain-improvements')"):text.index("phase('closeout')")]
    assert "throw" not in window, "Phase 5h must be advisory / non-blocking (no throw)"


def test_domain_auditor_resolves_to_agent_file() -> None:
    text = _text()
    referenced = _referenced_agent_types(text)
    assert "apd-domain-auditor" in referenced
    assert (AGENTS_DIR / "apd-domain-auditor.md").is_file()


def test_report_path_unchanged_by_5h() -> None:
    """B does not touch the report path: the 5g audit loop literal still present."""
    text = _text()
    assert "i <= 2" in text  # audit loop cap unchanged
    assert "report-data" in text  # report path still wired


# ---------------------------------------------------------------------------
# Task 9 — canonicalize-before-tier-gate wiring (C7)
# ---------------------------------------------------------------------------


def test_canonicalize_in_meta_phases() -> None:
    text = _text()
    # Use regex extraction (same approach as test_every_expected_phase_present_in_meta_phases)
    # to robustly locate the phases:[...] array in the meta block.
    m = re.search(r"phases:\s*\[(.*?)\]", text, re.DOTALL)
    assert m, "phases:[...] array not found in meta"
    phases_blob = m.group(1)
    assert "canonicalize" in phases_blob, "'canonicalize' not found in meta.phases array"


def test_canonicalize_pystep_uses_always_run() -> None:
    text = _text()
    run_tier = text.split("function runTier", 1)[1].split("\nfunction ", 1)[0]
    # locate the canonicalize pyStep block and confirm alwaysRun: true is within it
    idx = run_tier.index("pyStep('canonicalize'")
    block = run_tier[idx: run_tier.index("})", idx) + 2]
    assert "alwaysRun: true" in block, block


def test_canonicalize_precedes_tier_validate_gate() -> None:
    text = _text()
    # inside runTier, the canonicalize pyStep must appear before the tier
    # validate gate pyStep.
    run_tier = text.split("function runTier", 1)[1].split("\nfunction ", 1)[0]
    assert "pyStep('canonicalize'" in run_tier
    assert run_tier.index("pyStep('canonicalize'") < run_tier.index(
        "pyStep('validate'"
    )


# ---------------------------------------------------------------------------
# Task 10 — completeness gate: block on structural failure, semantic non-blocking
# ---------------------------------------------------------------------------


def test_completeness_gate_throws_on_structural_failure():
    src = _text()
    assert "report completeness gate" in src
    assert "throw new Error(" in src
    assert "Refusing to ship a degraded report" in src
    assert "if (!structuralOk)" in src


def test_completeness_gate_blocks_on_missing_audit_receipt():
    src = _text()
    assert "if (!audit)" in src
    # A missing audit receipt is a null receipt = an INTERRUPTED dispatch, so it now
    # halts via the interruption bail (which throws the resume error) rather than
    # shipping an unverified report. Block-on-missing behavior is preserved.
    assert "bailIfInterrupted(audit, 'synthesis-audit')" in src


def test_semantic_residual_remains_non_blocking():
    src = _text()
    assert "residual SEMANTIC discrepancies" in src
    assert "non-blocking" in src


def test_report_writer_remediation_reads_report_audit():
    src = _text()
    assert "report-audit.yaml" in src
    assert 'klass is "editorial"' in src


# ---------------------------------------------------------------------------
# F2 — the rollup last-resort fallback must (re)write metrics.yaml (the report
# loader requires it; the old last-resort wrote only nist/attack/matrix).
# ---------------------------------------------------------------------------


def test_rollup_last_resort_writes_metrics():
    src = _text()
    # Locate the synthesizer rollup last-resort dispatch and assert it lists
    # metrics.yaml among the files it writes.
    m = re.search(r"synthesizer-fallback-rollup.*?\}\)", src, re.DOTALL)
    assert m, "rollup last-resort dispatch (synthesizer-fallback-rollup) not found"
    # The prompt text precedes the label; search the whole dispatch region.
    region = src[max(0, m.start() - 800):m.end()]
    assert "metrics.yaml" in region, (
        "rollup last-resort must write metrics.yaml (load_run requires it)"
    )


# ---------------------------------------------------------------------------
# F5 — the rollup pyStep advisory `outputs` label must mention metrics.yaml
# (build_rollups writes it; the label drifted).
# ---------------------------------------------------------------------------


def test_rollup_outputs_label_includes_metrics():
    src = _text()
    m = re.search(r"pyStep\('rollup',\s*\{[^}]*?\}\)", src, re.DOTALL)
    assert m, "rollup pyStep dispatch not found"
    assert "metrics.yaml" in m.group(0), (
        "rollup pyStep outputs label must list metrics.yaml"
    )


# ---------------------------------------------------------------------------
# F3 — per-class completeness gate: the audit receipt carries structural_failed
# / editorial_failed so the workflow blocks on STRUCTURAL completeness only and
# surfaces editorial residuals non-blocking.
# ---------------------------------------------------------------------------


def test_receipt_constant_includes_report_audit():
    src = _text()
    m = re.search(r"const RECEIPT\s*=.*?^\};", src, re.DOTALL | re.MULTILINE)
    assert m, "const RECEIPT block not found"
    block = m.group(0)
    assert "report_audit" in block, "RECEIPT must carry the optional report_audit block"
    assert "structural_failed" in block and "editorial_failed" in block


def test_audit_dispatch_captures_per_class_counts():
    src = _text()
    # The audit-report dispatch must instruct the worker to populate report_audit
    # with the per-class counts the CLI prints (structural_failed / editorial_failed).
    assert "structural_failed" in src and "editorial_failed" in src
    assert "report_audit" in src


def test_completeness_gate_keys_on_structural_failed():
    src = _text()
    # structuralOk is now computed from the per-class structural_failed count
    # (not merely the command exit status), so the name is truthful and editorial
    # residuals do not hard-block.
    assert "structural_failed" in src
    assert "structuralOk" in src


def test_editorial_residual_is_non_blocking():
    src = _text()
    # The i==2 cap must NOT throw on an editorial-only residual; it logs and ships.
    assert "editorial" in src.lower()
    assert "non-blocking" in src


def test_threat_model_author_phase_in_meta_phases() -> None:
    """C5: the always-on threat-model-author phase is declared in meta.phases."""
    text = _text()
    m = re.search(r"phases:\s*\[(.*?)\]", text, re.DOTALL)
    assert m, "phases:[...] array not found in meta"
    phases_blob = m.group(1)
    found = set(re.findall(r"'([^']+)'", phases_blob))
    assert "threat-model-author" in found, "'threat-model-author' missing from meta.phases"


def test_threat_model_author_phase_dispatches_floor_then_enrich() -> None:
    """C5: the threat-model-author phase emits a phase('threat-model-author') literal,
    runs the deterministic CLI floor via pyStep('author-threat-model'), THEN dispatches
    the apd-threat-model-author agent via llmStep — floor strictly before enrich."""
    text = _text()
    assert "phase('threat-model-author')" in text, (
        "phase('threat-model-author') not invoked in body"
    )
    assert "pyStep('author-threat-model'" in text, (
        "deterministic CLI floor pyStep('author-threat-model') missing"
    )
    assert "llmStep('apd-threat-model-author'" in text, (
        "apd-threat-model-author enrich llmStep missing"
    )
    i_phase = text.index("phase('threat-model-author')")
    i_floor = text.index("pyStep('author-threat-model'", i_phase)
    i_enrich = text.index("llmStep('apd-threat-model-author'", i_phase)
    assert i_phase < i_floor < i_enrich, (
        "order must be phase -> pyStep(author-threat-model) floor -> llmStep(enrich)"
    )


def test_author_phase_precedes_tm_recon_and_tiers() -> None:
    """C5: the always-on author baseline runs after code-recon and before tm-recon
    and the tier-1 lens dispatch (specialists cite the authored baseline)."""
    text = _text()
    i_coderecon = text.index("phase('code-recon')")
    i_author = text.index("phase('threat-model-author')")
    i_tmrecon = text.index("phase('tm-recon')")
    i_tier1 = text.index("runTier('tier-1'")
    assert i_coderecon < i_author < i_tmrecon < i_tier1, (
        "order must be code-recon -> threat-model-author -> tm-recon -> tier-1"
    )


def test_tm_recon_writes_supplied_sibling_when_gated() -> None:
    """C5: recon remains gated on args.threat_model but now writes the SIBLING
    threat-model-supplied-normalized.yaml (recon's CLI --output), never the
    canonical threat-model-normalized.yaml the author owns."""
    text = _text()
    i_tmrecon = text.index("phase('tm-recon')")
    block = text[i_tmrecon:text.index("function runTier", i_tmrecon)]
    assert "if (args.threat_model)" in block, "recon must stay gated on args.threat_model"
    assert "llmStep('apd-threat-model-recon'" in block, "recon dispatch missing"
    assert "threat-model-supplied-normalized.yaml" in block, (
        "recon must write the supplied sibling threat-model-supplied-normalized.yaml"
    )
    recon_call = block[block.index("llmStep('apd-threat-model-recon'"):]
    recon_call = recon_call[:recon_call.index("});") + 3]
    assert "00-context/threat-model-normalized.yaml" not in recon_call, (
        "recon must no longer write the canonical threat-model-normalized.yaml "
        "(the author owns it); recon writes the supplied sibling"
    )
    assert "--output" in recon_call, "recon must pass --output to the sibling file"


def test_tmeval_gate_widened_to_tm_present() -> None:
    """C5: tmeval is no longer gated on args.threat_model — the authored baseline
    always exists, so the evaluator always runs. Pin that the tmeval thunk
    unconditionally dispatches apd-threat-model-evaluator (no args.threat_model
    guard) and that its instruction names BOTH the canonical authored TM and the
    supplied sibling so the comparator path is reachable."""
    text = _text()
    i_eval = text.index("llmStep('apd-threat-model-evaluator'")
    thunk_start = text.rindex("function ()", 0, i_eval)
    thunk = text[thunk_start:text.index("function ()", i_eval)]
    assert "if (args.threat_model)" not in thunk, (
        "tmeval gate must be widened: the authored baseline always exists, so the "
        "evaluator must not be gated on args.threat_model"
    )
    assert "00-context/threat-model-normalized.yaml" in thunk, (
        "tmeval must evaluate against the canonical authored baseline"
    )
    assert "threat-model-supplied-normalized.yaml" in thunk, (
        "tmeval must read the supplied sibling for the comparator path when present"
    )


def test_author_threat_model_command_registered_and_dispatched() -> None:
    """C1/C5: author-threat-model is a registered Click command dispatched via
    pyStep('author-threat-model', ...) — the deterministic skeleton floor."""
    text = _text()
    registered = set(cli.commands.keys())
    assert "author-threat-model" in registered, (
        "author-threat-model not registered in the Click CLI"
    )
    assert "pyStep('author-threat-model'" in text, (
        "author-threat-model not dispatched via pyStep in the workflow"
    )


def test_threat_model_author_agent_resolves_to_file() -> None:
    """C2/C5: the apd-threat-model-author agentType resolves to a .claude/agents file."""
    text = _text()
    referenced = _referenced_agent_types(text)
    assert "apd-threat-model-author" in referenced, (
        "apd-threat-model-author not dispatched by the runner"
    )
    assert (AGENTS_DIR / "apd-threat-model-author.md").is_file(), (
        "apd-threat-model-author agentType has no .claude/agents/apd-threat-model-author.md"
    )


# ── Shared GraphView component (Cytoscape) ───────────────────────────────────
def test_graph_view_is_shared_cytoscape_component() -> None:
    comp = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function GraphView(" in comp
    assert "window.cytoscape" in comp
    assert "dagre" in comp and "fcose" in comp           # both layouts supported
    assert "getComputedStyle" in comp                    # token-derived theming
    assert "data-theme" in comp or "MutationObserver" in comp  # re-style on theme change
    assert "GraphView" in comp.split("Object.assign(window")[1]  # exported
    assert "MermaidGraph" not in comp                    # fully replaced
    assert "window.mermaid" not in comp


def test_graph_view_kind_passthrough_is_additive_and_guarded() -> None:
    """EN2: GraphView's C4 node-kind passthrough is ADDITIVE — it only sets
    cytoscape ``data.kind`` when the node carries a ``kind`` (guarded by
    ``if (n.kind)``), so callers whose nodes have no kind (AttackPaths,
    ThreatModel) are entirely unaffected. The per-kind stylesheet rules select
    on ``node[kind=…]`` so they never match a kind-less node.

    Regression guard against a shared-component change that would alter the
    AttackPaths/ThreatModel graph behavior: those screens must not start
    emitting a ``kind`` field on their graph nodes."""
    comp = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    # Additive + guarded passthrough in buildElements.
    assert "if (n.kind) data.kind = n.kind;" in comp
    # Per-kind cytoscape styling selects on data(kind) — never fires on a
    # kind-less node, so the shared component stays behavior-neutral for callers
    # that don't set kind.
    assert 'node[kind="data_store"]' in comp
    assert 'node[kind="external_system"]' in comp
    # The non-C4 GraphView callers must NOT set a kind on their graph nodes
    # (which would change their render). They build node objects with id/label/
    # type but no kind field.
    ap = (REPO / "report-template" / "screens" / "AttackPaths.jsx").read_text(encoding="utf-8")
    tm = (REPO / "report-template" / "screens" / "ThreatModel.jsx").read_text(encoding="utf-8")
    assert "kind:" not in ap, "AttackPaths must not set a graph-node kind (EN2 is C4-only)"
    assert "kind:" not in tm, "ThreatModel must not set a graph-node kind (EN2 is C4-only)"


def test_attack_paths_uses_graphview_with_path_selection() -> None:
    ap = (REPO / "report-template" / "screens" / "AttackPaths.jsx").read_text(encoding="utf-8")
    assert "GraphView" in ap and "MermaidGraph" not in ap
    assert "ap.graph" in ap and "ap.graph_path_focused" in ap
    assert "selectedPathId" in ap and "onSelectPath" in ap
    # derives a flat paths list (id + edgeIds) for highlighting
    assert "edgeIds" in ap and "path_id" in ap


def test_attack_paths_has_findings_only_filter() -> None:
    ap = (REPO / "report-template" / "screens" / "AttackPaths.jsx").read_text(encoding="utf-8")
    # Default-ON interactive toggle state.
    assert "findingsOnly" in ap and "setFindingsOnly" in ap
    assert "useState(true)" in ap  # the toggle defaults ON
    # Predicate: a path "has findings" iff it traverses a finding-derived edge.
    assert "pathHasFindings" in ap
    # Effective filter state gates the no-findings fallback (default-ON safety).
    assert "anyFindingPaths" in ap and "effectiveOn" in ap
    # Client-side graph subsetter (JS mirror of _asset_graph_view_focused).
    assert "subsetGraph" in ap
    # The toggle is labelled.
    assert "Findings only" in ap


def test_threat_model_uses_graphview_surface_map() -> None:
    tm = (REPO / "report-template" / "screens" / "ThreatModel.jsx").read_text(encoding="utf-8")
    assert "GraphView" in tm and "MermaidGraph" not in tm
    assert "surface_graph" in tm and "surface_mermaid" not in tm
    assert "compound" in tm and 'layout="fcose"' in tm


def test_threat_model_screen_exists_and_renders_blocks() -> None:
    src = (REPO / "report-template" / "screens" / "ThreatModel.jsx").read_text(encoding="utf-8")
    assert "function ThreatModel(" in src and "window.ThreatModel = ThreatModel" in src
    # reuses the report's design language, not bespoke styling
    assert "section-eyebrow" in src and "section-title" in src
    assert "apd-matrix" in src and "matrix-cell--" in src        # block A
    assert "attack-table" in src                                  # blocks B/C
    assert "coverage-bar" in src                                  # block C
    assert "GraphView" in src                                     # block D
    assert "contradiction" in src                                 # block E
    # conditional blocks
    assert "surface_coverage" in src and "comparator_delta" in src


# ── C4 architecture scene (Cytoscape compound) ───────────────────────────────
def test_c4_screen_exists_and_renders_blocks() -> None:
    """The C4 scene renders the grounded model as a TIERED system-map
    (System → Container → Component → Code) via <C4TierGraph/>, NOT the
    Cytoscape fcose force-graph. The honest banner + drill machine stay."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # present-gate + honest banner (kept)
    assert "c4.present" in src or "c4 || !c4.present" in src
    assert "c4-banner" in src
    assert "not_analyzed" in src and "unlocalized" in src
    # NEW: the tiered renderer replaces GraphView. C4 no longer imports/uses
    # GraphView or any Cytoscape layout — those moved out of the C4 path.
    assert "C4TierGraph" in src
    assert "GraphView" not in src, "C4 must not reference the Cytoscape GraphView"
    assert 'layout="fcose"' not in src and 'layout="dagre"' not in src
    assert "compound={true}" not in src
    # the drill machine is preserved (now passed to C4TierGraph as onDrill)
    assert "selectedContainer" in src and "selectedComponent" in src
    assert "onDrill" in src
    # the model + resolved overlay membership are fed to the tiered renderer
    assert "model={" in src
    assert "overlayC4NodeIds" in src
    # the code-elements list (NodeRow) is kept beneath the scene
    assert "NodeRow" in src and "onOpenFinding" in src


def test_c4_screen_surfaces_node_kind_chip() -> None:
    """EN2: the C4 scene renders the container/code ``kind`` (service /
    data_store / external_system / function / class / route / module …) as a
    small type chip in the drill-list, and the kind-chip CSS class is styled.
    Regression guard so the C4-style typing cue can't silently drop out."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # The drill-list row references the node kind and renders the typed chip.
    assert "n.kind" in src
    assert "c4-kind-chip" in src
    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    assert ".c4-kind-chip" in css


def test_c4_overlay_join_uses_from_id_to_id() -> None:
    """The attack-path overlay's asset->C4 join MUST read the hop's from_id/to_id
    (the asset-graph node ids the transform's edges_detailed emit), NOT the bare
    h.from/h.to (which the hop objects never carry). Regression guard for the
    dead-lookup bug where the join never fired."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # The asset-endpoint lookup array uses the *_id keys.
    assert "[h.from_id, h.to_id]" in src
    # The bare-key dead fallbacks must be gone from the join + unmapped strip.
    assert "h.from," not in src and "h.to," not in src
    assert "|| h.from " not in src and "|| h.to " not in src
    # Per-node deep-link reads FX1's first_finding_id off node provenance.
    assert "provenance.first_finding_id" in src
    assert "onOpenFinding(findingId)" in src


def test_c4_screen_registered_in_bundle_entry() -> None:
    entry = (REPO / "report-template" / ".build" / "entry.jsx").read_text(encoding="utf-8")
    # The screen MUST be a side-effect import or window.C4 is never set in the bundle.
    assert 'import "../screens/C4.jsx";' in entry


def test_c4_router_helpers_present() -> None:
    """Task 5: the orthogonal connector router + short-edge-label + SVG edge
    layer ship in components.jsx (ported verbatim from the design handoff), and
    are window-exported so the C4 scene can consume them. GraphView is untouched
    (still Cytoscape) — these are additive, non-Cytoscape helpers."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    # the four pure helpers + the edge-layer component
    assert "function c4Anchors(" in comps
    assert "function c4RouteWaypoints(" in comps
    assert "function c4RoundedPath(" in comps
    assert "function c4ShortEdgeLabel(" in comps
    assert "function C4EdgeLayer(" in comps
    # window-exported via the existing Object.assign(window, {...})
    assert "c4Anchors" in comps and "c4RouteWaypoints" in comps and "c4RoundedPath" in comps
    assert "C4EdgeLayer" in comps and "c4ShortEdgeLabel" in comps
    # the router is the VERBATIM offsetParent-walk (zoom-invariant layout-box anchor)
    assert "e.offsetParent" in comps and "el.offsetWidth" in comps
    # orthogonal H-V-H / V-H-V branch (Math.abs(dx) >= Math.abs(dy))
    assert "Math.abs(dx) >= Math.abs(dy)" in comps
    # rounded elbow uses a quadratic curve at radius ~7
    assert "Q ${b.x} ${b.y}" in comps
    # the short label strips the CROSS_* machine prefix; full string kept for hover
    assert "CROSS_" in comps
    # GraphView (Cytoscape) is NOT removed — AttackPaths/ThreatModel still use it
    assert "function GraphView(" in comps and "window.cytoscape" in comps


def test_c4_global_connector_router_present() -> None:
    """The GLOBAL connector router (distinct ports per side + gutter/lane routing
    so connectors attach at distinct points, route in the clear gutters/bands, and
    never cross a non-endpoint box) ships in components.jsx and is what C4EdgeLayer
    uses. c4RouteWaypoints is RETAINED as the legality-guard fallback. The geometry
    is pinned by report-template/.build/test/c4_solve_routes.test.mjs."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    # the new pure helpers ship + are window-exported (for the node oracle)
    for fn in ("function c4Grid(", "function c4SolveRoutes(", "function c4SegHitsRect("):
        assert fn in comps, f"missing global-router helper: {fn}"
    assert "c4Grid, c4SolveRoutes, c4SegHitsRect," in comps, \
        "global-router helpers not window-exported"
    # the edge layer measures the BACKBONE box set once and routes them GLOBALLY
    # (not the old per-edge c4RouteWaypoints loop)
    assert ".l2-backbone [data-c4id]" in comps, "router must measure the backbone box set"
    assert "c4SolveRoutes(rects, edges" in comps, "C4EdgeLayer.measure must call the global solver"
    # c4RouteWaypoints kept only as the guarded fallback
    assert "c4RouteWaypoints(m.S, m.T)" in comps, "legacy router must remain the legality fallback"


def test_c4_solve_routes_node_oracle() -> None:
    """Run the committed node oracle that asserts the four routing defects
    (edge-crosses-box, shared-ports, label-over-box, label-label) are ZERO on the
    Home Assistant backbone fixture + the generality cases — the reproducible,
    pure-math form of the headless verification. Skipped only where node is absent
    (GitHub-hosted runners ship node, so this is an enforced gate there)."""
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        import pytest

        pytest.skip("node not available")
    harness = REPO / "report-template" / ".build" / "test" / "c4_solve_routes.test.mjs"
    proc = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, (
        f"c4_solve_routes node oracle failed:\n{proc.stdout}\n{proc.stderr}"
    )


def test_c4_tier_graph_present() -> None:
    """Task 6: the C4TierGraph tiered renderer (no Cytoscape) ships in
    components.jsx with the four tiers, the NodeBox in-node badge rules consuming
    the REAL c4_model names, the C4EdgeLayer overlay, and a zoom/fit toolbar."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function C4TierGraph(" in comps
    assert "function NodeBox(" in comps
    assert "C4TierGraph" in comps  # window-exported
    # the documented prop contract
    for prop in ("model", "selectedContainer", "selectedComponent",
                 "overlayC4NodeIds", "onDrill", "onOpenFinding"):
        assert prop in comps, f"C4TierGraph must accept {prop}"
    # four tiers rendered with left-gutter labels (System context / Containers / …)
    assert "System context" in comps and "Containers" in comps
    assert "Components" in comps and "Code" in comps
    assert "tier-gutter" in comps
    # consumes the REAL model field names (gap-fix 2), NOT prototype abbreviations
    assert "capability_badge" in comps and "analysis_state" in comps
    assert "provenance" in comps and "first_finding_id" in comps
    # in-node badge rules: muted ⚑0 when badge==null, sev-high clickable when >0
    assert "not analyzed" in comps
    # the prototype abbreviations must NOT leak into production. Match the bare
    # `n.cap` / `n.ff` accessors with a word boundary so they do NOT collide with
    # the REAL field names we DO consume (`n.capability_badge`, etc.).
    assert "overlay_paths" not in comps
    assert not re.search(r"\bn\.ff\b", comps) and not re.search(r"\bn\.cap\b", comps)
    # uses the Task-5 router/edge-layer (SVG, no Cytoscape) — NOT fcose
    assert "C4EdgeLayer" in comps and "c4BackboneLayout" in comps
    assert 'layout="fcose"' not in comps
    # clicking a ⚑ badge stops propagation so it deep-links without drilling
    assert "stopPropagation" in comps
    # zoom/fit toolbar
    assert "fit" in comps and "scale(" in comps

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    # the lifted tier / node-box / edge-layer rules
    for sel in (".archx-stage", ".tier", ".tier-gutter", ".nb", ".nb__badges",
                ".edge-layer", ".l2-backbone", ".shelf", ".code-grid"):
        assert sel in css, f"missing C4 tier CSS rule: {sel}"
    # not_analyzed striped/dashed treatment must be DISTINCT (never reads as clean)
    assert ".nb--na" in css
    # all colors are tokens (theme-aware) — no raw hex in the new block
    block = css[css.index(".archx-stage"):]
    assert "var(--" in block


def test_c4_edge_layer_svg_is_sized_one_to_one() -> None:
    """Regression: the C4 edge-layer SVG must map its viewBox to pixels 1:1.

    components.jsx emits the overlay as
        <svg class="edge-layer" width={scrollW} height={scrollH}
             viewBox="0 0 scrollW scrollH">
    The node boxes are absolutely positioned by the data-driven c4BackboneLayout,
    which can be WIDER than the fixed-width .archx-stage; .archx-stage-wrap then
    scrolls (overflow:auto) and stage.scrollWidth exceeds the stage's rendered
    width. If CSS forces the SVG to width:100%/height:100% (or inset:0, which
    stretches right:0/bottom:0 to the same effect), the rendered size no longer
    equals the viewBox, so the default preserveAspectRatio ("xMidYMid meet")
    UNIFORMLY SCALES + CENTERS the edge coordinate system relative to the
    (un-scaled) DOM node boxes — every connector detaches from its endpoints.
    The fix: position the SVG at the stage origin (top/left) and let its
    width/height ATTRIBUTES size it 1:1 with the viewBox. Never width:100%.
    """
    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    m = re.search(r"\.c4-scene \.edge-layer\s*\{([^}]*)\}", css)
    assert m, "missing .c4-scene .edge-layer rule"
    rule = m.group(1)
    assert "width: 100%" not in rule and "width:100%" not in rule, (
        ".edge-layer must not force width:100% — it scales the viewBox against "
        "the un-scaled boxes when the backbone overflows the fixed-width stage"
    )
    assert "height: 100%" not in rule and "height:100%" not in rule, (
        ".edge-layer must not force height:100% (same scaling defect as width)"
    )
    assert "inset:" not in rule and "inset " not in rule, (
        ".edge-layer must position at the top/left origin, not inset:0 — right:0/"
        "bottom:0 stretches the SVG to 100% and re-introduces the viewBox scaling"
    )


def test_threat_model_tab_is_conditional_and_routed() -> None:
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    # tab entry present
    assert 'id: "threat_model"' in src and 'label: "Threat model"' in src
    # gated on data.threat_model.present (omit when absent)
    assert "data.threat_model" in src and "present" in src
    # routed to the screen
    assert 'activeTab === "threat_model"' in src and "<ThreatModel" in src
    # placed after coverage, before attack_paths
    i_cov = src.index('"coverage"')
    i_tm = src.index('"threat_model"')
    i_ap = src.index('"attack_paths"')
    assert i_cov < i_tm < i_ap


def test_build_registers_cytoscape_not_mermaid() -> None:
    rg = (REPO / "report-template" / ".build" / "react-globals.js").read_text(encoding="utf-8")
    assert 'import cytoscape from "cytoscape"' in rg
    assert "cytoscape-dagre" in rg and "cytoscape-fcose" in rg
    assert "window.cytoscape = cytoscape" in rg
    assert "mermaid" not in rg
    pkg = (REPO / "report-template" / ".build" / "package.json").read_text(encoding="utf-8")
    assert "cytoscape" in pkg and "cytoscape-dagre" in pkg and "cytoscape-fcose" in pkg
    assert "mermaid" not in pkg
    build = (REPO / "report-template" / ".build" / "build.mjs").read_text(encoding="utf-8")
    assert "mermaid.min.js" not in build  # no longer vendored


def test_no_mermaid_references_remain() -> None:
    """The HTML-report renderer path carries zero Mermaid references.

    Exclusions (all out of scope for the HTML-report Cytoscape migration):
      - the precompiled bundle (tools/apd_gauntlet/data/report-template/) and
        the generated report-template/data.js are regenerated in the
        bundle-rebuild task; the mid-run source-vs-bundle mismatch is expected
        and resolved there;
      - tools/apd_gauntlet/attack_path/mermaid.py renders the attack-path
        AGENT's separate Markdown deliverable (templates/attack-path-report
        .template.md), which is Mermaid by design and has its own tested
        contract (tests/test_attack_path_templates.py).
    """
    import subprocess

    out = subprocess.run(
        [
            "git", "grep", "-il", "mermaid", "--",
            "report-template", "tools",
            ":!tools/apd_gauntlet/data/report-template",
            ":!report-template/data.js",
            ":!tools/apd_gauntlet/attack_path/mermaid.py",
        ],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    assert out.strip() == "", f"residual mermaid references:\n{out}"


def test_start_here_tab_is_first_and_routed() -> None:
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    # tab entry present, carries a sigil instead of a number
    assert 'id: "start_here"' in src and 'label: "Start here"' in src
    assert 'sigil: "✦"' in src
    # the numbering map special-cases the sigil so content tabs keep 01..N
    assert "t.sigil" in src
    # routed to the screen
    assert 'activeTab === "start_here"' in src and "<StartHere" in src
    # placed first — before Overview (compare the tab-entry literals)
    assert src.index('id: "start_here"') < src.index('id: "overview"')
    # Overview remains the default landing tab
    assert 'useState("overview")' in src


def test_start_here_sigil_excluded_from_tab_numbering() -> None:
    # Content tabs must keep 01..N: the numbering map renders the guide's sigil
    # as its `num` and increments the counter only for non-sigil tabs. A future
    # edit that renumbers content tabs (e.g. counting the guide into the index)
    # would change this shape; the bundle-freshness gate cannot catch a logic
    # regression here, so pin the map shape.
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    assert "if (t.sigil) return { ...t, num: t.sigil };" in src
    assert 'String(_tabNum).padStart(2, "0")' in src


# ── PR1: run-stopper robustness (args normalization + interruption resilience) ──

def test_args_normalized_and_validated() -> None:
    """PR1a: runner tolerates args-as-string and fails with ACTIONABLE errors
    (not `.join of undefined`) when run_id/domains are missing/malformed."""
    text = _text()
    assert re.search(r"typeof args === ['\"]string['\"]", text), "must guard the string-args case"
    assert "JSON.parse(args)" in text, "must JSON.parse string args"
    assert "args.run_id is required" in text, "must name a missing run_id"
    assert "args.domains must be a non-empty array" in text, "must name a missing domains list"


def test_interruption_helpers_present() -> None:
    """PR1b: explicit interrupted-receipt classifier + bail helper."""
    text = _text()
    assert "function isInterrupted(" in text
    assert "function bailIfInterrupted(" in text


def test_intake_bails_on_interruption() -> None:
    """PR1b: the first dispatch (intake) bails fast on interruption so an en-masse
    cancellation surfaces a clear resume message instead of cascading."""
    text = _text()
    assert "const intakeReceipt = llmStep('apd-intake'" in text
    assert "bailIfInterrupted(intakeReceipt, 'intake')" in text


def test_report_stage_interruption_distinct_from_completeness_gate() -> None:
    """PR1b: an interrupted build/audit dispatch yields the RESUME error, not the
    misleading 'completeness gate FAILED'; the genuine structural throw remains."""
    text = _text()
    assert "bailIfInterrupted(build, 'synthesis-build')" in text
    assert "bailIfInterrupted(audit, 'synthesis-audit')" in text
    assert "run interrupted at phase" in text, "distinct resume error must exist"
    assert "plan-run" in text, "resume error should point to the foreground plan-run path"
    assert "still FAILED a STRUCTURAL check" in text, "genuine structural gate must remain"


def test_assemble_c4_wired_after_apath_before_canonicalize() -> None:
    """assemble-c4 is the deterministic C4 assembler: it runs in the synthesis
    flow after the tmeval/apath parallel barrier (so asset-graph.yaml exists)
    and before the canonicalize-tmeval + rollup steps. Mirrors assemble-inventory."""
    text = _text()
    assert "pyStep('assemble-c4'" in text, "assemble-c4 must be dispatched via pyStep"
    apath_close = text.index("phase('apath')")
    c4_at = text.index("pyStep('assemble-c4'")
    # Anchor on the canonicalize-tmeval label specifically: an earlier per-tier
    # pyStep('canonicalize', ...) (label canonicalize-<tier>) precedes the apath
    # barrier, so a bare text.index("pyStep('canonicalize'") would match THAT one.
    canon_at = text.index("canonicalize-tmeval")
    rollup_at = text.index("pyStep('rollup'")
    assert apath_close < c4_at < canon_at, (
        "assemble-c4 must run after the apath barrier and before canonicalize-tmeval"
    )
    assert c4_at < rollup_at, "assemble-c4 must run before rollup"


def test_c4_tab_is_conditional_and_routed() -> None:
    src = (REPO / "report-template" / "app.jsx").read_text(encoding="utf-8")
    # tab entry present, gated on data.c4_model && data.c4_model.present (omit when absent)
    assert 'id: "c4"' in src and 'label: "Architecture"' in src
    assert "data.c4_model" in src and "data.c4_model.present" in src
    # routed to the screen, passing data + onOpenFinding
    assert 'activeTab === "c4"' in src and "<C4" in src
    assert "onOpenFinding={onOpenFinding}" in src.split('activeTab === "c4"')[1][:200]
    # placed after attack_paths, before annexes (engineering view sits late)
    i_ap = src.index('id: "attack_paths"')
    i_c4 = src.index('id: "c4"')
    i_annex = src.index('id: "annexes"')
    assert i_ap < i_c4 < i_annex
    # the conditional spread uses the SAME numbering machinery (sigil-aware map)
    assert "_tabNum" in src


def test_c4_scene_styles_present() -> None:
    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    # scene container + section headers reuse the design tokens
    assert ".c4-scene" in css and ".c4-scene__section-h" in css
    # honest banner + its warning emphasis
    assert ".c4-banner" in css and ".c4-banner__warn" in css
    # per-node list + badges
    assert ".c4-node-list" in css and ".c4-node-row" in css
    assert ".c4-badge--finding" in css and ".c4-badge--capability" in css
    # not_analyzed must be styled DISTINCTLY (muted/striped), never as clean
    assert ".c4-node-row--not-analyzed" in css and ".c4-badge--not-analyzed" in css
    # level chips for the four C4 tiers
    assert ".c4-level-chip" in css
    # all colors come from CSS custom properties (theme-aware), no hex literals
    c4_block = css[css.index(".c4-scene"):]
    assert "var(--" in c4_block


def test_bundle_contains_c4_scene() -> None:
    """The compiled bundle ships the tiered C4 scene + its deterministic
    backbone layout helper, and NOT a C4-bound fcose force-graph."""
    # ADAPTATION: the plan's `report-template/app.js` is the build tool's logical
    # name; the real esbuild OUT_DIR (report-template/.build/build.mjs) is the
    # bundled tools/apd_gauntlet/data/report-template — there is no top-level
    # report-template/app.js in this repo. Read the canonical built bundle.
    app_js = (
        REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "app.js"
    ).read_text(encoding="utf-8")
    # the tiered renderer + the deterministic backbone layout helper are bundled
    assert "C4TierGraph" in app_js
    assert "c4BackboneLayout" in app_js
    assert "c4ShortEdgeLabel" in app_js
    # an SVG edge-layer is emitted by the C4 scene (orthogonal connectors)
    assert "edge-layer" in app_js
    # GraphView still ships (AttackPaths/ThreatModel use it) but fcose is no
    # longer wired from the C4 scene — assert the C4 source has neither.
    c4 = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    assert 'layout="fcose"' not in c4
    assert "GraphView" not in c4


def _seed_load_run_required(synthesis: pathlib.Path) -> None:
    """Seed the synthesis artifacts ``load_run`` requires but the C4 fixture omits.

    The committed ``c4-home-assistant`` fixture ships *exactly the artifacts the
    C4 pipeline reads* (asset-graph, code-evidence-index, deduped findings /
    capabilities). ``load_run`` additionally requires four whole-report synthesis
    rollups. We stub them minimally so ``load_run`` -> ``build_apd_data`` succeeds
    while the assembler still consumes the real (14 zero-anchor repo) inputs, which
    keeps ``not_analyzed_count >= 1`` honest. None of these stubs feed the
    ``c4_model`` section under test. Mirrors the helper in
    tests/unit/report/test_c4_model_real_run.py.
    """
    seeds = {
        "nist-coverage.yaml": 'schema_version: 1\ngenerated_at: "2026-06-12"\ncoverage: []\n',
        "attack-exposure.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\nexposed_assets: []\n'
        ),
        "apd-coverage-matrix.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\nmatrix: []\n'
        ),
        "metrics.yaml": (
            'schema_version: 1\ngenerated_at: "2026-06-12"\n'
            "totals: {findings: 0, capabilities: 0}\n"
        ),
    }
    for name, body in seeds.items():
        target = synthesis / name
        if not target.exists():
            target.write_text(body, encoding="utf-8")


def test_built_report_renders_c4_tab_from_home_assistant_run(tmp_path: pathlib.Path) -> None:
    """End-to-end: assemble c4-model.yaml for the real Home Assistant run, build
    the report data, and assert the C4 tab is enabled (data.c4_model.present).
    runs/*/report-html is gitignored, so we assemble + build into tmp."""
    import shutil

    import yaml
    from apd_gauntlet.assemble_c4 import assemble_c4
    from apd_gauntlet.report.loader import load_run
    from apd_gauntlet.report.transform import build_apd_data

    src_run = REPO / "tests" / "fixtures" / "runs" / "c4-home-assistant"
    assert src_run.is_dir(), "ground-truth run missing"
    run = tmp_path / "run"
    shutil.copytree(src_run, run)

    # Assemble the canonical c4-model.yaml (assembler is the sole id minter).
    summary = assemble_c4(run)
    c4_path = run / "40-synthesis" / "c4-model.yaml"
    assert c4_path.is_file(), "assemble_c4 did not write 40-synthesis/c4-model.yaml"
    c4_doc = yaml.safe_load(c4_path.read_text(encoding="utf-8"))
    assert c4_doc["generated_by"] == "assemble_c4"
    # Code tiers present because this run HAS a code-evidence-index.yaml.
    assert summary["container_count"] >= 1
    assert summary["not_analyzed_container_count"] >= 1   # 14 empty repos -> some not_analyzed

    # ADAPTATION: the minimal fixture omits the four whole-report rollups that
    # load_run requires; seed them so load_run -> build_apd_data succeeds while
    # the assembler above still consumed the real C4 inputs.
    _seed_load_run_required(run / "40-synthesis")

    artifacts = load_run(run)
    assert artifacts.c4_model is not None                 # loader picked it up
    data = build_apd_data(artifacts, run_dir=run)
    assert data["c4_model"] is not None
    assert data["c4_model"]["present"] is True            # the tab will render
    # honest fields are surfaced through to the view
    assert "unlocalized_findings" in data["c4_model"]
    assert "not_analyzed_count" in data["c4_model"]
    assert data["c4_model"]["not_analyzed_count"] >= 1
    # nodes carry the level + badge contract the scene consumes
    sample = data["c4_model"]["nodes"][0]
    for key in ("id", "label", "type", "parent", "badge", "analysis_state"):
        assert key in sample, f"c4_model node missing {key}"


def test_c4_attack_path_overlay() -> None:
    """The attack-path overlay is an SVG-native highlight on the tiered scene
    (no GraphView): selecting a path resolves grounded c4 node ids via the
    deterministic asset_to_c4 + finding_to_c4 join, dims non-member node boxes,
    draws the induced member edges 'live', and keeps the 'no C4 mapping' strip
    for unmapped hops. Honest partial overlay only."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # consumes the existing enumerated paths + the DETERMINISTIC join (no client-side mapping)
    assert "data.attack_paths" in src
    assert "selectedOverlayPath" in src and "setSelectedOverlayPath" in src
    assert "asset_to_c4" in src and "finding_to_c4" in src
    # the resolved MEMBERSHIP (not a GraphView synthetic path) is handed to the renderer
    assert "overlayC4NodeIds" in src
    assert "overlayHighlight" not in src, "GraphView synthetic-path highlight is gone"
    # honest partial overlay: unmapped hops on a PARALLEL asset strip, never a C4 hop
    assert "c4-overlay-strip" in src and "no C4 mapping" in src
    assert "unmappedHops" in src

    comp = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    # C4TierGraph dims non-members + marks induced member edges live, off overlayC4NodeIds
    assert "overlayC4NodeIds" in comp
    assert "nb--dim" in comp           # non-member node boxes are dimmed
    assert "edge-layer__path--live" in comp  # induced member edges drawn live
    # induced-edge rule: both endpoints in the membership set
    assert "C4EdgeLayer" in comp

    css = (REPO / "report-template" / "screens.css").read_text(encoding="utf-8")
    assert ".c4-overlay-strip" in css and ".c4-overlay-strip__hop--unmapped" in css
    assert ".nb--dim" in css and ".edge-layer__path--live" in css


def test_c4_graph_node_tap_drives_drill() -> None:
    """A click on a tiered node box drills exactly like the NodeRow buttons,
    via the onDrill reducer passed into C4TierGraph (no GraphView onNodeTap)."""
    src = (REPO / "report-template" / "screens" / "C4.jsx").read_text(encoding="utf-8")
    # the reducer is defined and passed to C4TierGraph as onDrill
    assert "onDrill" in src
    assert "C4TierGraph" in src
    assert "setSelectedContainer" in src and "setSelectedComponent" in src
    # container -> select container; component -> select component (parent kept)
    assert 'n.type === "container"' in src
    assert 'n.type === "component"' in src
    # the drill is wired through C4TierGraph's onDrill prop, NOT GraphView
    assert "onDrill={" in src
    assert "onNodeTap=" not in src, "C4 must not pass GraphView's onNodeTap"


def test_c4_backbone_layout_helper_present() -> None:
    """Task 6: the deterministic backbone layout ships in components.jsx — layered
    BFS longest-path columns + analyzed/infra partitions + stable sorts. It is the
    data-driven replacement for the prototype's hand-curated BACKBONE position map."""
    comps = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function c4BackboneLayout(" in comps
    # window-exported alongside the other helpers
    assert "c4BackboneLayout" in comps.split("Object.assign(window")[1]
    # partitions: connected / analyzed / infra
    assert "connected" in comps and "analyzed" in comps and "infra" in comps
    # deterministic: stable sort by label, no Math.random anywhere in the helper
    assert "localeCompare" in comps
    # consumes the REAL model name — analysis_state, NOT the prototype's `state`
    assert "analysis_state" in comps
    # column geometry constants
    assert "COL_W" in comps and "ROW_H" in comps


def test_c4_short_edge_label_helper_present():
    """The deterministic short-edge-label helper is defined + window-exported in
    components.jsx (data-driven replacement for the prototype's hand-curated
    EDGE_SHORT map). The full edge.label is kept for the hover tooltip."""
    src = (REPO / "report-template" / "components.jsx").read_text(encoding="utf-8")
    assert "function c4ShortEdgeLabel(" in src
    # strips the CROSS_* machine prefix deterministically
    assert "CROSS_" in src.split("function c4ShortEdgeLabel(")[1].split("\n}")[0]
    assert "c4ShortEdgeLabel" in src.split("Object.assign(window")[1]
    bundle = (
        REPO / "tools" / "apd_gauntlet" / "data" / "report-template" / "app.js"
    ).read_text(encoding="utf-8")
    assert "c4ShortEdgeLabel" in bundle
