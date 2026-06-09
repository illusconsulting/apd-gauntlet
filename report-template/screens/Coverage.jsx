/* eslint-disable */
// Coverage screen — NIST family rollup, ATT&CK exposure, APD component matrix.

function Coverage({ data }) {
  const [tab, setTab] = useState("nist");

  const active = (data.meta && data.meta.active_taxonomies) || [];
  const masvsRows = data.masvs_coverage || [];
  const masweRows = data.maswe_coverage || [];
  const showMasvs = active.includes("masvs") && masvsRows.length > 0;
  const showMaswe = active.includes("maswe") && masweRows.length > 0;
  // APD matrix is § 9 by default; each MAS sub-tab inserted before it bumps
  // its section number so the tab labels stay contiguous after ATT&CK (§ 8).
  let n = 9;
  const masvsSec = showMasvs ? n++ : null;
  const masweSec = showMaswe ? n++ : null;
  const apdSec = n;

  return (
    <div>
      <div className="section-eyebrow">§ 7-{apdSec} — Coverage</div>
      <h2 className="section-title">Control + technique + component coverage</h2>

      <div className="cov-tabs">
        <button className={`cov-tab ${tab === "nist" ? "cov-tab--active" : ""}`} onClick={() => setTab("nist")}>
          NIST 800-53r5 · § 7
        </button>
        <button className={`cov-tab ${tab === "attack" ? "cov-tab--active" : ""}`} onClick={() => setTab("attack")}>
          MITRE ATT&CK · § 8
        </button>
        {showMasvs && (
          <button className={`cov-tab ${tab === "masvs" ? "cov-tab--active" : ""}`} onClick={() => setTab("masvs")}>
            OWASP MASVS · § {masvsSec}
          </button>
        )}
        {showMaswe && (
          <button className={`cov-tab ${tab === "maswe" ? "cov-tab--active" : ""}`} onClick={() => setTab("maswe")}>
            OWASP MASWE · § {masweSec}
          </button>
        )}
        <button className={`cov-tab ${tab === "apd" ? "cov-tab--active" : ""}`} onClick={() => setTab("apd")}>
          APD component matrix · § {apdSec}
        </button>
      </div>

      {tab === "nist" && <NistTable rows={data.nist_rollup} />}
      {tab === "attack" && <AttackTable rows={data.attack_exposure} />}
      {tab === "masvs" && showMasvs && <MasvsTable rows={masvsRows} />}
      {tab === "maswe" && showMaswe && <MasweTable rows={masweRows} />}
      {tab === "apd" && <APDMatrix matrix={data.apd_matrix} />}
    </div>
  );
}

function NistTable({ rows }) {
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        Per-family rollup of controls touched by findings and capabilities. Highlighted rows are <strong>gapped</strong> (findings reference, no capabilities) or <strong>gapped_and_covered</strong> (both — suggesting scope mismatch). Authoritative version in <code className="mono">40-synthesis/nist-coverage.yaml</code>.
      </p>
      <table className="nist-table">
        <thead>
          <tr>
            <th>Family</th>
            <th>Title</th>
            <th className="num">Covered</th>
            <th className="num">Gapped</th>
            <th className="num">Both</th>
            <th>Coverage</th>
            <th>Notable</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const total = r.covered + r.gapped + r.both;
            return (
              <tr key={r.family}>
                <td className="mono" style={{ color: "var(--ink)" }}>{r.family}</td>
                <td>{r.title}</td>
                <td className="num">{r.covered}</td>
                <td className="num" style={{ color: r.gapped > r.covered ? "var(--sev-high)" : undefined }}>{r.gapped}</td>
                <td className="num">{r.both}</td>
                <td>
                  <div className="coverage-bar">
                    <span className="seg-covered" style={{ flex: r.covered }} />
                    <span className="seg-both" style={{ flex: r.both }} />
                    <span className="seg-gapped" style={{ flex: r.gapped }} />
                  </div>
                </td>
                <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{r.notable}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="legend">
        <span><span className="legend__swatch" style={{ background: "var(--cell-covered)" }} />covered</span>
        <span><span className="legend__swatch" style={{ background: "var(--cell-both)" }} />gapped_and_covered</span>
        <span><span className="legend__swatch" style={{ background: "var(--cell-gapped)" }} />gapped</span>
      </div>
    </div>
  );
}

function AttackTable({ rows }) {
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        Techniques mapped by findings, with any mitigating capabilities. Sorted by finding-count descending. Authoritative version in <code className="mono">40-synthesis/attack-exposure.yaml</code>.
      </p>
      <table className="attack-table">
        <thead>
          <tr>
            <th>Technique</th>
            <th>Name</th>
            <th className="num">Findings</th>
            <th>Mitigated by</th>
            <th>Coverage</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td><TaxonomyTag id={r.id} /></td>
              <td style={{ color: "var(--ink)" }}>{r.name}</td>
              <td className="num">{r.findings}</td>
              <td>
                <div className="tagrow">
                  {r.mitigations.length > 0
                    ? r.mitigations.map((m) => <CopyPill key={m} value={m} />)
                    : <span style={{ color: "var(--sev-high)", fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)" }}>— none</span>}
                </div>
              </td>
              <td>
                <span className={`cov-cell cov-cell--${r.coverage === "covered" ? "covered" : r.coverage === "uncovered" ? "gapped" : "both"}`}>
                  {r.coverage}
                </span>
              </td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{r.note || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function APDMatrix({ matrix }) {
  const labels = { both: "both", covered: "covd", gapped: "gap", silent: "—" };
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        Per-component coverage across the nine APD goals. Authoritative version in <code className="mono">40-synthesis/apd-coverage-matrix.yaml</code>.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table className="apd-matrix">
          <thead>
            <tr>
              <th>Component</th>
              {matrix.goals.map((g) => <th key={g}>{matrix.goalLabels[g]}</th>)}
            </tr>
          </thead>
          <tbody>
            {matrix.rows.map((row) => (
              <tr key={row.component}>
                <td>{row.component}</td>
                {matrix.goals.map((g) => {
                  const v = row.cells[g];
                  return (
                    <td key={g}>
                      <span className={`matrix-cell matrix-cell--${v}`}>{labels[v]}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="legend">
        <span><span className="legend__swatch" style={{ background: "var(--cell-covered)" }} />covered — capabilities, no gaps</span>
        <span><span className="legend__swatch" style={{ background: "var(--cell-both)" }} />both — review scope alignment</span>
        <span><span className="legend__swatch" style={{ background: "var(--cell-gapped)" }} />gapped — findings, no capabilities</span>
        <span><span className="legend__swatch" style={{ background: "var(--cell-silent)" }} />silent</span>
      </div>
    </div>
  );
}

function MasvsTable({ rows }) {
  const postureClass = (p) =>
    p === "satisfying" || p === "covered" ? "covered"
      : p === "exposed" || p === "gapped" ? "gapped"
      : "both";
  // Map the raw coverage enum to the friendly vocabulary used in the legend
  // prose above, so the cell text matches what the reader is told to expect.
  const postureLabel = (p) =>
    p === "covered" ? "satisfying"
      : p === "gapped" ? "exposed"
      : p === "gapped_and_covered" ? "both"
      : p;
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        OWASP MASVS controls touched by this run, with the capabilities that satisfy them and the findings that expose them. Posture is <strong>satisfying</strong> (capabilities, no findings), <strong>exposed</strong> (findings, no satisfying capability), or <strong>both</strong> (review scope alignment). Authoritative version in <code className="mono">40-synthesis/masvs-coverage.yaml</code>.
      </p>
      <table className="nist-table">
        <thead>
          <tr>
            <th>Control</th>
            <th>Category</th>
            <th>Statement</th>
            <th className="num">Satisfying</th>
            <th className="num">Exposed</th>
            <th>Surfaces</th>
            <th>Posture</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.masvs_id}>
              <td><TaxonomyTag id={r.masvs_id} /></td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{r.category_title || r.category}</td>
              <td style={{ color: "var(--ink)" }}>{r.name}</td>
              <td className="num">{r.capability_count}</td>
              <td className="num" style={{ color: r.finding_count > 0 ? "var(--sev-high)" : undefined }}>{r.finding_count}</td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{(r.surfaces || []).join(", ") || "—"}</td>
              <td><span className={`cov-cell cov-cell--${postureClass(r.posture)}`}>{postureLabel(r.posture)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MasweTable({ rows }) {
  return (
    <div>
      <p style={{ color: "var(--ink-2)", maxWidth: "72ch", marginBottom: "var(--space-4)", lineHeight: 1.6 }}>
        OWASP MASWE weaknesses exposed by findings in this run, with the MASVS control each weakness rolls up to. MASWE is a findings-only weakness taxonomy — there is no &ldquo;satisfying capability&rdquo; column. Authoritative version in <code className="mono">40-synthesis/maswe-coverage.yaml</code>.
      </p>
      <table className="attack-table">
        <thead>
          <tr>
            <th>Weakness</th>
            <th>Name</th>
            <th>Category</th>
            <th>Parent MASVS</th>
            <th className="num">Findings</th>
            <th>Surfaces</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.maswe_id}>
              <td><TaxonomyTag id={r.maswe_id} /></td>
              <td style={{ color: "var(--ink)" }}>{r.name}</td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{r.category}</td>
              <td><TagRow ids={r.parent_masvs || []} /></td>
              <td className="num" style={{ color: r.finding_count > 0 ? "var(--sev-high)" : undefined }}>{r.finding_count}</td>
              <td style={{ fontSize: "var(--text-xs)", color: "var(--ink-3)" }}>{(r.surfaces || []).join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

window.Coverage = Coverage;
