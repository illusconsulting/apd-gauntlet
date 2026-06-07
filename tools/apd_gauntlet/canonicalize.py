"""Structural canonicalizer for specialist findings / capabilities (C1).

``apd-gauntlet canonicalize <run_dir>`` — idempotent, whole-run, structural-only.

Repairs ONLY what is derivable / structural:
  - envelope: singular root key (``finding`` / ``capability``), per-record
    unwrap, per-record ``schema_version``
  - deterministic IDs (tooling-authoritative; overwrites whatever agents wrote)
  - ``cross_references`` rewritten through the global old->new id map

Does NOT edit semantic content (titles, excerpts, evidence). A file is rewritten
only when it contains at least one IN-SCOPE record — one whose ``agent`` maps to
a known lens prefix in ``linters._PREFIX_BY_AGENT`` (the nine specialist lenses).
This deliberately leaves alone:
  - ``40-synthesis/deduped-*.yaml`` (apply.py mints ``merged-*`` ids) — excluded
    by glob anyway, since ``deduped-findings.yaml`` does not match
    ``*.findings.yaml``;
  - ``40-synthesis/attack-path.findings.yaml`` (agent ``attack_path_analyzer``)
    and ``40-threat-model/threat-model.findings.yaml`` (agent
    ``threat_model_evaluator``) — they contain no in-scope records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .linters import _PREFIX_BY_AGENT, compute_capability_id, compute_id
from .validate import extract_records

# (singular root key, glob) per record kind. Mirrors validate.RECORD_KINDS.
_KINDS: tuple[tuple[str, str], ...] = (
    ("finding", "*.findings.yaml"),
    ("capability", "*.capabilities.yaml"),
)

# Taxonomy sub-keys allowed UNDER ``control_mappings`` per record kind. Mirrors
# the ``control_mappings`` ``properties`` allow-sets in finding.schema.json /
# capability.schema.json (the additionalProperties:false gate). Only these keys
# are lifted from the record root into control_mappings during normalization —
# lifting a key the destination schema does not allow would merely relocate the
# schema violation, so out-of-scope keys are deliberately left at the root.
_CONTROL_MAPPING_KEYS_BY_KIND: dict[str, frozenset[str]] = {
    "finding": frozenset(
        {"nist_800_53r5", "mitre_attack", "cwe", "owasp_top10",
         "owasp_api_top10", "owasp_llm_top10", "atlas"}
    ),
    "capability": frozenset(
        {"nist_800_53r5", "mitre_attack", "mitre_attack_mitigations", "d3fend"}
    ),
}


def _normalize_control_mappings(record: dict[str, Any], kind: str = "finding") -> bool:
    """Self-heal two common specialist-output frictions on one record, in place.

    Returns ``True`` iff the record was mutated.

    (a) A root-level ``mitre_atlas`` key is the ATLAS-taxonomy data under the
        wrong name/place; move it to ``control_mappings.atlas`` (only when
        ``atlas`` is an allowed control_mappings key for ``kind``).
    (b) Each recognized taxonomy key sitting at the record ROOT — ``cwe``,
        ``atlas``, ``owasp_top10``, ``owasp_api_top10``, ``owasp_llm_top10``,
        ``mitre_attack``, ``nist_800_53r5`` — that ``kind``'s schema allows under
        ``control_mappings`` is LIFTED into ``control_mappings``.

    Loss-preventing: if the destination sub-key already holds a NON-EMPTY value,
    do NOT overwrite it; LEAVE the root key in place so the schema's
    ``additionalProperties:false`` gate still fires and a human resolves the
    conflict. (An empty/absent destination is safe to fill.) Only keys allowed
    for ``kind`` are ever touched — out-of-scope root keys are left untouched.
    """
    allowed = _CONTROL_MAPPING_KEYS_BY_KIND.get(kind, frozenset())
    mutated = False

    def _lift(root_key: str, dest_key: str) -> None:
        nonlocal mutated
        if dest_key not in allowed:
            return  # lifting would just relocate the schema violation.
        if root_key not in record:
            return
        cm = record.get("control_mappings")
        if not isinstance(cm, dict):
            cm = {}
        existing = cm.get(dest_key)
        if existing:  # non-empty destination -> loss-preventing, leave root key.
            return
        cm[dest_key] = record.pop(root_key)
        record["control_mappings"] = cm
        mutated = True

    # (a) misnamed root mitre_atlas -> control_mappings.atlas
    _lift("mitre_atlas", "atlas")

    # (b) recognized taxonomy keys lifted from the root (same-name dest).
    for key in ("cwe", "atlas", "owasp_top10", "owasp_api_top10",
                "owasp_llm_top10", "mitre_attack", "nist_800_53r5"):
        _lift(key, key)

    return mutated


class CanonicalizeCollision(Exception):
    """Two distinct in-scope records would receive the same canonical id."""


@dataclass
class CanonicalizeResult:
    records_canonicalized: int
    cross_refs_rewritten: int
    # Per-file parse failures (path, error message) for files skipped because
    # their YAML could not be loaded. A single malformed file no longer aborts
    # the whole pass; it is skipped, recorded here, and surfaced to the caller.
    parse_errors: list[tuple[str, str]] = field(default_factory=list)


def _first_locator(record: dict[str, Any]) -> str | None:
    evidence = record.get("evidence") or []
    if not evidence or not isinstance(evidence[0], dict):
        return None
    locator = evidence[0].get("locator", "")
    return locator if isinstance(locator, str) else ""


def _recompute_ids_for_file(
    path: Path,
    root_key: str,
    id_map: dict[str, str],
    seen_new_ids: set[str],
) -> tuple[list[dict[str, Any]] | None, int]:
    """Pass 1 for one file: load, normalize the envelope in memory, inject
    ``schema_version``, and recompute the id of every in-scope record (populating
    ``id_map`` old->new and the global ``seen_new_ids`` collision set). Returns
    ``(records, n_changed)`` where ``records`` is the normalized record list when
    the file has >=1 in-scope record (else None, meaning the file is left
    untouched on disk), and ``n_changed`` is the count of records whose id
    actually changed."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        return None, 0
    records = extract_records(doc, root_key)
    in_scope = 0
    n_changed = 0
    normalized = False
    for rec in records:
        # G4: deterministic control-mappings self-heal runs on EVERY record,
        # regardless of agent prefix — apath-*/tmeval-* records (whose agents are
        # out-of-scope for id recompute) must be normalized too. A file whose
        # only change is a normalization is still written back (see return).
        if _normalize_control_mappings(rec, root_key):
            normalized = True
        # schema_version is persisted only when the file is written back.
        rec.setdefault("schema_version", 1)
        prefix = _PREFIX_BY_AGENT.get(rec.get("agent") or "", "")
        if not prefix:
            continue  # out-of-scope agent (attack_path / threat_model / etc.)
        locator = _first_locator(rec)
        if locator is None:
            continue  # cannot compute a deterministic id without a locator
        in_scope += 1
        title = rec.get("title", "")
        new_id = (
            compute_id(prefix, title, locator)
            if root_key == "finding"
            else compute_capability_id(prefix, title, locator)
        )
        if new_id in seen_new_ids:
            raise CanonicalizeCollision(
                f"id collision on {new_id!r} in {path}: two records share the "
                f"same (title, first-evidence-locator) under prefix {prefix!r}"
            )
        seen_new_ids.add(new_id)
        old_id = rec.get("id")
        if old_id != new_id:
            n_changed += 1
        if old_id:
            id_map[old_id] = new_id
        rec["id"] = new_id
    # Write the file back when it has >=1 in-scope record (id recompute /
    # schema_version persistence) OR when a normalization mutated any record —
    # the latter covers files of purely out-of-scope records (e.g. attack-path,
    # threat-model) that nonetheless needed a control-mappings self-heal.
    return (records if (in_scope or normalized) else None), n_changed


def _rewrite_cross_refs(records: list[dict[str, Any]], id_map: dict[str, str]) -> int:
    """Pass 2 for one file: rewrite every ``cross_references`` entry through the
    global id_map. Handles both the bare-string form and the defensive
    ``{"id": ...}`` dict form. Returns the count of entries actually changed."""
    changed = 0
    for rec in records:
        refs = rec.get("cross_references")
        if not isinstance(refs, list):
            continue
        for i, ref in enumerate(refs):
            if isinstance(ref, str) and ref in id_map and id_map[ref] != ref:
                refs[i] = id_map[ref]
                changed += 1
            elif isinstance(ref, dict) and isinstance(ref.get("id"), str):
                rid = ref["id"]
                if rid in id_map and id_map[rid] != rid:
                    ref["id"] = id_map[rid]
                    changed += 1
    return changed


def canonicalize_run(run_dir: Path) -> CanonicalizeResult:
    """Canonicalize every in-scope lens file under ``run_dir`` in place."""
    id_map: dict[str, str] = {}
    seen_new_ids: set[str] = set()
    pending: list[tuple[Path, str, list[dict[str, Any]]]] = []
    records_canonicalized = 0
    parse_errors: list[tuple[str, str]] = []

    # Pass 1 — global: recompute ids file-by-file (deterministic file order).
    # A single unparseable/unreadable file must NOT abort the whole pass: skip
    # it (leave it untouched on disk), record the error, and keep going. A
    # CanonicalizeCollision is a real hard error and is left to propagate.
    for root_key, glob in _KINDS:
        for path in sorted(run_dir.rglob(glob)):
            try:
                records, n_changed = _recompute_ids_for_file(
                    path, root_key, id_map, seen_new_ids
                )
            except (yaml.YAMLError, OSError) as exc:
                parse_errors.append((str(path), str(exc)))
                continue
            if records is None:
                continue
            pending.append((path, root_key, records))
            records_canonicalized += n_changed

    # Pass 2 — global: rewrite cross-refs, then write each file back canonically.
    cross_refs_rewritten = 0
    for path, root_key, records in pending:
        cross_refs_rewritten += _rewrite_cross_refs(records, id_map)
        doc = {root_key: records}
        path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096),
            encoding="utf-8",
        )

    return CanonicalizeResult(records_canonicalized, cross_refs_rewritten, parse_errors)
