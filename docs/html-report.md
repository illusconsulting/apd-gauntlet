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
