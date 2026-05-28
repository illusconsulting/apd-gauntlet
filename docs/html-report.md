# HTML Advisory Report (v1.5)

Every gauntlet run automatically produces an interactive HTML view of the
synthesizer's outputs at:

    runs/<run_id>/40-synthesis/report-html/index.html

Open the file in any recent browser (offline — no network needed). The bundle
contains six tabs (Overview, Findings, Capabilities, Coverage, Attack paths,
Annexes) sourced from the existing `40-synthesis/*.yaml` artifacts plus the
synthesizer-emitted `report-data.yaml`.

## Manual regeneration

If you change a 40-synthesis file by hand or want to regenerate without
re-running the gauntlet:

    apd-gauntlet build-report runs/<run_id>

## When `report-data.yaml` is absent

Older runs (pre-1.5) and partial runs may lack `report-data.yaml`. The HTML
report falls back to algorithmic equivalents:

- Headline findings: top 10 by (severity desc, confidence desc, id asc).
- Next steps: empty list.
- Executive summary: placeholder paragraph naming the run id.
- Posture summary: placeholder per-tier statements.

The Findings tab, Capabilities tab, Coverage tabs, Attack paths tab, and
Annexes tab all render fully from existing YAMLs in either case.

## Empty-state interpretation

Some report tabs show zero counts without further explanation in earlier versions.
The following empty states are **accurate run outcomes**, not rendering bugs:

**Attack Paths — "0 pairs / 0 paths / 0 bottleneck edges"**
This occurs when the asset graph exists (nodes and edges are present and rendered
via Mermaid) but those edges do not form a traversable chain from any declared
attacker position to any declared crown jewel. The most common cause: specialists
reference prose documents (e.g., `tech_plan.md`) as evidence rather than specific
`asset_id` values, so the analyzer cannot synthesize graph edges from prose. The
"Enumerated paths" panel displays an informative explanation block (blue-bordered)
rather than a blank section. To enable path enumeration, enrich
`00-context/asset-inventory.yaml` with explicit trust-boundary edges connecting
attacker positions to crown jewels, or have specialists tag finding evidence with
the `asset_id` of the affected component.

**Annexes — "0 surfaced" / "0 clusters"**
Contradictions and severity disagreements are only recorded when specialists
genuinely disagree. A run where all specialists operated from a shared baseline
(same rubric, same scope) will legitimately produce zero entries in both annexes.
When the synthesizer includes a `notes:` field in `contradictions.yaml` or
`severity-disagreements.yaml` explaining the absence, those notes are surfaced
directly in the Annexes tab beneath the count pill.

If either of these tabs is blank with no explanation, that is a template
rendering bug — check that `build-report` was run against the current
`report-template/` bundle.

## Contributing template changes

The JSX source lives in `report-template/`. After editing any JSX or CSS,
rebuild the precompiled bundle and commit the result:

    python tools/build_report_template.py
    git add tools/apd_gauntlet/data/report-template/
    git commit

CI gates that the precompiled bundle matches the JSX source
(`tools/check_report_template_freshness.py`). The Node toolchain
(esbuild 0.21.5 + react 18.3.1 + mermaid 10.9.1) is contributor-only — no
runtime user needs Node.
