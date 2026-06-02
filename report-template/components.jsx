/* eslint-disable */
// Shared atoms for the APD report interface.

const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ────────────────────────────────────────────────────────────────────────
// Severity / disposition / maturity primitives
// ────────────────────────────────────────────────────────────────────────
function SeverityPill({ value }) {
  if (!value) return null;
  return <span className={`sev sev--${value}`}>{value}</span>;
}

function DispositionMark({ value }) {
  if (!value) return null;
  return (
    <span className={`disposition disposition--${value}`}>
      <span className="disposition__sigil" />
      {value}
    </span>
  );
}

function MaturityMark({ value }) {
  if (!value) return null;
  return <span className={`maturity maturity--${value}`}>{value}</span>;
}

// ────────────────────────────────────────────────────────────────────────
// Copyable ID pill
// ────────────────────────────────────────────────────────────────────────
function CopyPill({ value, label, modifier = "" }) {
  const [copied, setCopied] = useState(false);
  const onClick = (e) => {
    e.stopPropagation();
    navigator.clipboard?.writeText(value);
    setCopied(true);
    window.dispatchEvent(new CustomEvent("apd:toast", { detail: `Copied ${value}` }));
    setTimeout(() => setCopied(false), 800);
  };
  return (
    <span
      className={`pill pill--id pill--copy ${modifier}`}
      onClick={onClick}
      title={`Copy ${value}`}
    >
      {label || value} {copied ? "✓" : ""}
    </span>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Taxonomy tag with hover tooltip
// ────────────────────────────────────────────────────────────────────────
function TaxonomyTag({ id }) {
  const [hover, setHover] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const entry = window.APD_DATA.taxonomy[id];
  const ref = useRef(null);

  const onEnter = () => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    setPos({ x: r.left, y: r.bottom + 6 });
    setHover(true);
  };
  return (
    <span
      ref={ref}
      className="tag"
      onMouseEnter={onEnter}
      onMouseLeave={() => setHover(false)}
    >
      {id}
      {hover && entry && (
        <span
          className="tag-tooltip"
          style={{ left: pos.x + "px", top: pos.y + "px" }}
        >
          <span className="tag-tooltip__family">{entry.family}</span>
          {entry.title}
        </span>
      )}
    </span>
  );
}

function TagRow({ ids = [] }) {
  if (!ids.length) return <span style={{ color: "var(--ink-3)", fontSize: "var(--text-xs)" }}>—</span>;
  return (
    <div className="tagrow">
      {ids.map((id) => <TaxonomyTag key={id} id={id} />)}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
// Toast host
// ────────────────────────────────────────────────────────────────────────
function ToastHost() {
  const [toasts, setToasts] = useState([]);
  useEffect(() => {
    const onToast = (e) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((t) => [...t, { id, text: e.detail }]);
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 1600);
    };
    window.addEventListener("apd:toast", onToast);
    return () => window.removeEventListener("apd:toast", onToast);
  }, []);
  return toasts.map((t) => (
    <div key={t.id} className="copy-toast">{t.text}</div>
  ));
}

// Diagnostics banner — surfaces build-time signals the Python layer records on
// data.meta but no screen otherwise shows: empty-run, per-section build errors,
// soft warnings, and stale/empty reference catalogs. Renders nothing when clean.
function DiagnosticsBanner({ data }) {
  const meta = (data && data.meta) || {};
  const items = [];

  if (meta.is_empty_run) {
    items.push({
      kind: "empty",
      label: "Empty run",
      text: "This run produced no findings or capabilities. See advisory-report.md for the run summary.",
    });
  }

  const failed = Object.keys(meta.section_errors || {});
  if (failed.length) {
    items.push({
      kind: "error",
      label: "Section error",
      text: `Some report sections could not be built and are shown empty: ${failed.join(", ")}.`,
    });
  }

  const warnings = meta.warnings || [];
  if (warnings.length) {
    const msgs = warnings
      .map((w) => (typeof w === "string" ? w : (w && (w.message || w.detail)) || ""))
      .filter(Boolean);
    const preview = msgs.length ? `: ${msgs.slice(0, 3).join("; ")}${msgs.length > 3 ? "…" : ""}` : "";
    items.push({
      kind: "warn",
      label: "Notice",
      text: `${warnings.length} soft warning${warnings.length === 1 ? "" : "s"} during report build${preview}.`,
    });
  }

  const refs = meta.reference_db_versions || {};
  const STALE_DAYS = 180;
  const now = Date.now();
  const stale = [];
  Object.keys(refs).forEach((fam) => {
    const r = refs[fam] || {};
    if (r.count === 0) { stale.push(`${fam} (empty)`); return; }
    if (r.fetched_at) {
      const t = Date.parse(r.fetched_at);
      if (!isNaN(t) && (now - t) / 86400000 > STALE_DAYS) stale.push(`${fam} (${r.fetched_at})`);
    }
  });
  if (stale.length) {
    items.push({
      kind: "warn",
      label: "Notice",
      text: `Reference catalogs may be stale (>${STALE_DAYS}d) or empty: ${stale.join(", ")}. Re-run the refresh-* commands to update.`,
    });
  }

  if (!items.length) return null;
  return (
    <div className="diagnostics">
      {items.map((it, i) => (
        <div key={i} className={`diagnostics__item diagnostics__item--${it.kind}`}>
          <span className="diagnostics__tag">{it.label}</span>
          <span>{it.text}</span>
        </div>
      ))}
    </div>
  );
}

// Goal labels
const GOAL_LABELS = {
  confidentiality: "Confidentiality",
  integrity: "Integrity",
  availability: "Availability",
  distributed: "Distributed",
  resilient: "Resilient",
  ephemeral: "Ephemeral",
  authenticity: "Authenticity",
  non_repudiation: "Non-Repudiation",
  immutability: "Immutability",
};
const GOAL_SHORT = {
  confidentiality: "Conf",
  integrity: "Intg",
  availability: "Avail",
  distributed: "Dist",
  resilient: "Resil",
  ephemeral: "Ephem",
  authenticity: "Auth",
  non_repudiation: "NonRep",
  immutability: "Immut",
};
const TIER_LABELS = {
  trustworthiness: "Trustworthiness",
  scalability: "Scalability",
  auditability: "Auditability",
};
const TIER_GOALS = {
  trustworthiness: ["confidentiality", "integrity", "availability"],
  scalability: ["distributed", "resilient", "ephemeral"],
  auditability: ["authenticity", "non_repudiation", "immutability"],
};

Object.assign(window, {
  SeverityPill, DispositionMark, MaturityMark, CopyPill, TaxonomyTag, TagRow, ToastHost, DiagnosticsBanner,
  GOAL_LABELS, GOAL_SHORT, TIER_LABELS, TIER_GOALS,
});
