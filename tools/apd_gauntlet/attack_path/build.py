"""Graph builder for attack-path analysis.

Reads a full APD run directory and constructs a populated `Graph`:

- Asset / identity nodes from `00-context/asset-inventory.yaml`
- Attacker-position nodes from run-config or domain pack
- Crown-jewel nodes from run-config or domain pack
- `trusts` edges between assets that cross a shared trust boundary
- `compromisable_via_finding` edges from per-specialist findings whose
  text references two graph nodes
- `mitigated_by_capability` edges from per-specialist capabilities whose
  text references two graph nodes
- `network_reachable` edges from the normalized threat model and from the
  code-evidence index (when these optional artifacts are present)

`build_graph` returns a `BuildResult(graph, sources_used)` so downstream
consumers can attribute every edge back to its origin artifact.

Raises `BuilderBlocked` when crown jewels or attacker positions are
absent from both the run-config and the domain pack — attack-path
enumeration is meaningless without at least one (attacker, jewel) pair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .graph import Edge, Graph, Node, stable_id


class BuilderBlocked(Exception):
    """Raised when required inputs are absent (no crown jewels, no attacker positions)
    or when an ambiguous same-type case-insensitive node-name collision is detected."""


@dataclass(frozen=True)
class BuildResult:
    graph: Graph
    sources_used: list[str]
    orphan_crown_jewels: list[str] = field(default_factory=list)


# Generic domain suffixes stripped from a crown-jewel pattern to recover its
# semantic head (e.g. ``phi_store`` -> ``phi``, ``tool_execution_capability``
# -> ``tool_execution``). Order matters only in that the FIRST matching suffix
# is removed; patterns carry at most one such suffix in practice.
_GENERIC_JEWEL_SUFFIXES = (
    "_store",
    "_capability",
    "_credentials",
    "_secrets",
    "_keys",
    "_engine",
    "_plane",
    "_loop",
    "_pipeline",
    "_data",
)


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _jewel_candidate_tokens(pattern: str) -> set[str]:
    """Derive the set of normalized tokens a crown-jewel pattern may match
    against an asset's controlled ``data_classifications`` vocabulary.

    The candidate set is conservative and exact-match-only downstream:
      - the full normalized pattern (``pii_profile_store``);
      - the pattern with one trailing generic domain suffix stripped, recovering
        the semantic head (``pii_profile``);
      - that head split on ``_`` into its component tokens (``pii``, ``profile``).

    Because matching downstream is EXACT against a controlled enum
    (``phi``/``pii``/``pci``/``secret``/...), splitting on ``_`` cannot
    over-connect: a token like ``profile`` simply never appears in the enum, so
    only genuinely meaningful heads (``pii``, ``phi``, ``secret``) connect.
    """
    full = _normalize_token(pattern)
    candidates: set[str] = {full}
    head = full
    for suffix in _GENERIC_JEWEL_SUFFIXES:
        if head.endswith(suffix) and len(head) > len(suffix):
            head = head[: -len(suffix)]
            break
    candidates.add(head)
    candidates.update(part for part in head.split("_") if part)
    return candidates


_SEVERITY_TO_COST = {
    "critical": 1,
    "high": 2,
    "medium": 4,
    "low": 8,
    "informational": 16,
}


def build_graph(run_dir: Path) -> BuildResult:
    """Construct a populated `Graph` from the artifacts in `run_dir`.

    See module docstring for the inputs consumed and edges emitted.
    """
    run_cfg = _load_yaml(run_dir / ".apd-run.yaml")
    domain_cfg = _load_domain(run_dir, run_cfg)
    inventory = _load_yaml(run_dir / "00-context" / "asset-inventory.yaml")
    tm_norm = _load_optional(run_dir / "00-context" / "threat-model-normalized.yaml")
    code_idx = _load_optional(run_dir / "00-context" / "code-evidence-index.yaml")
    findings = _load_all_records(
        run_dir, key="finding", glob="**/*.findings.yaml"
    )
    capabilities = _load_all_records(
        run_dir, key="capability", glob="**/*.capabilities.yaml"
    )

    crown_jewel_names = _resolve_crown_jewels(run_cfg, domain_cfg)
    attacker_position_data = _resolve_attacker_positions(run_cfg, domain_cfg)

    if not crown_jewel_names:
        raise BuilderBlocked("no crown jewels declared (domain pack or run-config)")
    if not attacker_position_data:
        raise BuilderBlocked(
            "no attacker positions declared (domain pack or run-config)"
        )

    g = Graph()
    sources: list[str] = []

    _add_inventory_nodes(g, inventory)
    sources.append("asset_inventory")
    _add_attacker_positions(g, attacker_position_data, run_cfg, domain_cfg)
    _add_crown_jewels(g, crown_jewel_names, domain_cfg, inventory=inventory)
    _wire_realized_crown_jewels(g)  # link assets that realize a same-named crown jewel

    _add_inventory_trust_edges(g, inventory)
    _add_finding_edges(g, findings)
    if findings:
        sources.append("findings")
    _add_capability_edges(g, capabilities)
    if capabilities:
        sources.append("capabilities")

    if tm_norm:
        _add_threat_model_edges(g, tm_norm)
        sources.append("threat_model_normalized")

    if code_idx:
        _add_code_evidence_edges(g, code_idx)
        sources.append("code_evidence_index")

    # Re-derive the authoritative orphan set AFTER all wiring (classification
    # alias + realizes field in _add_crown_jewels, name realization in
    # _wire_realized_crown_jewels). A declared crown jewel with zero inbound
    # edges is a silent orphan sink — surfaced, never fatal.
    orphans = _orphan_crown_jewels(g)

    return BuildResult(graph=g, sources_used=sources, orphan_crown_jewels=orphans)


def _orphan_crown_jewels(g: Graph) -> list[str]:
    """Return the names of crown-jewel nodes that have ZERO inbound edges.

    Such jewels are unreachable sinks: the deterministic floor can enumerate no
    path that terminates on them. This is a diagnostic, not a blocking error.
    """
    inbound: set[str] = {e.to_node for e in g._edges.values()}
    return [
        jewel.name
        for jewel in g.nodes_by_type("crown_jewel")
        if jewel.node_id not in inbound
    ]


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_optional(path: Path) -> dict[str, Any] | None:
    return _load_yaml(path) if path.exists() else None


def _load_all_records(
    run_dir: Path, *, key: str, glob: str
) -> list[dict[str, Any]]:
    """Recursively load YAML records matching ``glob`` under ``run_dir``.

    Specialist agents emit findings/capabilities into per-goal tier directories
    (``10-trustworthiness/``, ``20-scalability/``, ``30-auditability/``), but
    older fixtures and test scaffolds may use flatter layouts. A recursive
    glob (e.g. ``**/*.findings.yaml``) handles both shapes uniformly.

    The canonical root key is singular (``finding`` / ``capability``) per
    ``validate.RECORD_KINDS``. A legacy plural form (``findings`` /
    ``capabilities``) is accepted defensively so older hand-rolled fixtures
    still load — writers always emit the singular form. Both list and scalar
    payloads under the root key are supported.

    The analyzer's own ``40-synthesis/attack-path.findings.yaml`` is skipped
    explicitly — if it weren't, every re-run would ingest its own previous
    output as a "specialist finding."
    """
    plural_alias = {
        "finding": "findings",
        "capability": "capabilities",
    }
    out: list[dict[str, Any]] = []
    if not run_dir.exists():
        return out
    for f in sorted(run_dir.glob(glob)):
        if "40-synthesis" in f.parts and f.name == "attack-path.findings.yaml":
            continue
        doc = _load_yaml(f)
        records = doc.get(key)
        if records is None and key in plural_alias:
            records = doc.get(plural_alias[key])
        if isinstance(records, list):
            out.extend(r for r in records if isinstance(r, dict))
        elif isinstance(records, dict):
            out.append(records)
    return out


def _load_domain(run_dir: Path, run_cfg: dict[str, Any]) -> dict[str, Any]:
    # Resolve the selected domain pack ids from the run-config `domains` list
    # (current multi-domain schema). When several packs are selected, union their
    # crown_jewels / attacker_positions defaults (deduped by key, in declared order).
    raw = run_cfg.get("domains")
    dom_ids = [str(d) for d in raw] if isinstance(raw, list) and raw else ["pbm"]

    merged: dict[str, Any] = {"crown_jewels": [], "attacker_positions": []}
    names: list[str] = []
    for dom_id in dom_ids:
        candidates = [
            run_dir / "domains" / f"{dom_id}.yaml",
            run_dir / "domains" / dom_id / "domain.yaml",
        ]
        loaded = next((_load_yaml(c) for c in candidates if c.exists()), None)
        if loaded is None:
            continue
        names.append(str(loaded.get("name", dom_id)))
        for fld, key in (("crown_jewels", "pattern"), ("attacker_positions", "position")):
            seen = {e[key] for e in merged[fld] if isinstance(e, dict) and key in e}
            for item in loaded.get(fld, []) or []:
                if isinstance(item, dict) and item.get(key) not in seen:
                    merged[fld].append(item)
                    seen.add(item.get(key))
    if not names:
        return {}
    merged["name"] = "+".join(names)
    return merged


# --------------------------------------------------------------------------- #
# Resolvers — crown jewels / attacker positions, run-config overrides domain
# --------------------------------------------------------------------------- #


def _resolve_crown_jewels(
    run_cfg: dict[str, Any], domain: dict[str, Any]
) -> list[str]:
    # Run-config presence (including explicit empty list) overrides domain defaults
    if "crown_jewels" in run_cfg:
        jewels = run_cfg["crown_jewels"]
        return list(jewels) if isinstance(jewels, list) else []
    return [
        j["pattern"]
        for j in domain.get("crown_jewels", [])
        if isinstance(j, dict) and "pattern" in j
    ]


def _resolve_attacker_positions(
    run_cfg: dict[str, Any], domain: dict[str, Any]
) -> list[dict[str, Any]]:
    if "attacker_positions" in run_cfg:
        names = run_cfg["attacker_positions"]
        if not isinstance(names, list):
            return []
        dom_by_name = {
            p["position"]: p
            for p in domain.get("attacker_positions", [])
            if isinstance(p, dict) and "position" in p
        }
        return [
            dom_by_name.get(
                name,
                {"position": name, "description": "(undeclared in domain pack)"},
            )
            for name in names
        ]
    return [
        p
        for p in domain.get("attacker_positions", [])
        if isinstance(p, dict) and "position" in p
    ]


# --------------------------------------------------------------------------- #
# Node emitters
# --------------------------------------------------------------------------- #


def _add_inventory_nodes(g: Graph, inv: dict[str, Any]) -> None:
    for a in inv.get("assets", []):
        g.add_node(
            Node(
                node_id=a["asset_id"],
                node_type="asset",
                name=a["name"],
                provenance=dict(a["provenance"]),
                confidence=a["confidence"],
                asset_type=a.get("asset_type"),
                data_classifications=tuple(a.get("data_classifications", [])),
            )
        )
    for i in inv.get("identities", []):
        g.add_node(
            Node(
                node_id=i["identity_id"],
                node_type="identity",
                name=i["name"],
                provenance=dict(i["provenance"]),
                confidence=i["confidence"],
            )
        )


def _add_attacker_positions(
    g: Graph,
    positions: list[dict[str, Any]],
    run_cfg: dict[str, Any],
    domain: dict[str, Any],
) -> None:
    run_override = "attacker_positions" in run_cfg
    source = "run_config" if run_override else "domain_default"
    domain_name = domain.get("name", "unknown") if isinstance(domain, dict) else "unknown"
    artifact = ".apd-run.yaml" if run_override else f"domains/{domain_name}.yaml"
    for p in positions:
        name = p["position"]
        node_id = stable_id("atk", name, source)
        g.add_node(
            Node(
                node_id=node_id,
                node_type="attacker_position",
                name=name,
                provenance={"source": source, "artifact": artifact},
                confidence="high",
            )
        )


def _asset_realizes_index(inventory: dict[str, Any]) -> dict[str, set[str]]:
    """Map asset_id -> set of normalized crown-jewel patterns the asset's
    OPTIONAL ``realizes_crown_jewels`` inventory field declares it realizes.

    Backward-compatible: the field is absent in existing inventories, yielding an
    empty map. Keyed by ``asset_id`` so it joins directly against graph nodes.
    """
    out: dict[str, set[str]] = {}
    for a in inventory.get("assets", []) or []:
        if not isinstance(a, dict):
            continue
        declared = a.get("realizes_crown_jewels")
        if not isinstance(declared, list):
            continue
        asset_id = a.get("asset_id")
        if not isinstance(asset_id, str):
            continue
        out.setdefault(asset_id, set()).update(
            _normalize_token(str(p)) for p in declared if isinstance(p, str)
        )
    return out


def _add_crown_jewels(
    g: Graph,
    jewel_names: list[str],
    domain: dict[str, Any],
    *,
    inventory: dict[str, Any] | None = None,
) -> list[str]:
    """Add crown-jewel nodes and wire ``data_resides_on`` edges from realizing
    assets. Returns the names of jewels left with ZERO inbound edges (orphans).

    Three wiring paths, all emitting the same deterministic edge_id so they
    coexist idempotently with ``_wire_realized_crown_jewels``:

    1. Classification alias: an asset whose normalized ``data_classifications``
       (a controlled enum) EXACTLY equals one of the jewel pattern's candidate
       tokens (full pattern, semantic head with a generic suffix stripped, and
       that head split on ``_``). Exact-match against a controlled vocab keeps
       this from connecting every asset to every jewel.
    2. Explicit ``realizes_crown_jewels`` inventory field naming the pattern.
    3. Legacy ``target_classification`` (naive ``_store``/``_pipeline``/
       ``_engine`` strip) — kept working for backward compatibility.
    """
    inv = inventory or {}
    realizes = _asset_realizes_index(inv)
    domain_patterns = {
        j["pattern"]
        for j in domain.get("crown_jewels", [])
        if isinstance(j, dict) and "pattern" in j
    }
    orphans: list[str] = []
    for name in jewel_names:
        jewel_id = stable_id("jewel", name)
        source = "domain_default" if name in domain_patterns else "run_config"
        g.add_node(
            Node(
                node_id=jewel_id,
                node_type="crown_jewel",
                name=name,
                provenance={"source": source},
                confidence="high",
            )
        )

        candidate_tokens = _jewel_candidate_tokens(name)
        normalized_pattern = _normalize_token(name)
        # Legacy naive head, preserved so prior behavior never regresses.
        legacy_target = (
            name.replace("_store", "").replace("_pipeline", "").replace("_engine", "")
        )
        wired = False
        for asset in g.nodes_by_type("asset"):
            asset_classes = {
                _normalize_token(c) for c in (asset.data_classifications or ())
            }
            classification_match = bool(asset_classes & candidate_tokens)
            legacy_match = legacy_target in (asset.data_classifications or ())
            explicit_match = normalized_pattern in realizes.get(asset.node_id, set())
            if (classification_match or legacy_match or explicit_match) and (
                _add_data_resides_edge(g, asset, jewel_id)
            ):
                wired = True
        if not wired:
            orphans.append(name)
    return orphans


def _add_data_resides_edge(g: Graph, asset: Node, jewel_id: str) -> bool:
    """Add a ``data_resides_on`` edge asset->jewel, idempotently.

    Returns True if an edge with the deterministic id now exists (whether this
    call created it or a prior pass did), False is unreachable here but keeps the
    caller's intent explicit. The deterministic edge_id lets this coexist with
    ``_wire_realized_crown_jewels`` without tripping add_edge's duplicate guard.
    """
    edge_id = stable_id("edge", asset.node_id, jewel_id, "data_resides_on")
    if edge_id in g._edges:
        return True
    g.add_edge(
        Edge(
            edge_id=edge_id,
            edge_type="data_resides_on",
            from_node=asset.node_id,
            to_node=jewel_id,
            provenance={"source": "asset_inventory"},
            confidence=asset.confidence,
            traversal_cost=1,
        )
    )
    return True


# --------------------------------------------------------------------------- #
# Edge emitters
# --------------------------------------------------------------------------- #


def _add_inventory_trust_edges(g: Graph, inv: dict[str, Any]) -> None:
    for tb in inv.get("trust_boundaries", []):
        crossings = tb.get("crosses", [])
        boundary_id = tb["boundary_id"]
        for i, src in enumerate(crossings):
            for dst in crossings[i + 1:]:
                for from_id, to_id in ((src, dst), (dst, src)):
                    g.add_edge(
                        Edge(
                            edge_id=stable_id(
                                "edge", from_id, to_id, "trusts", boundary_id
                            ),
                            edge_type="trusts",
                            from_node=from_id,
                            to_node=to_id,
                            provenance={
                                "source": "asset_inventory",
                                "locator": boundary_id,
                            },
                            confidence="high",
                            traversal_cost=2,
                        )
                    )


def _node_name_index(g: Graph) -> dict[str, str]:
    """Map lower-cased node name -> node_id, for text-based heuristic matching.

    A crown_jewel and an asset may legitimately share a (case-insensitive) name:
    the asset *realizes* the crown jewel (e.g. an inventory asset literally named
    ``phi_store`` realizing the ``phi_store`` crown jewel). That is the same
    concept, not an ambiguity — resolve it deterministically to the CONCRETE
    asset node so downstream text matching is unambiguous. Reserve
    ``BuilderBlocked`` for genuinely ambiguous collisions between two nodes of
    the SAME type, which downstream matching cannot disambiguate.
    """
    index: dict[str, str] = {}
    for nid in sorted(g._nodes):  # deterministic resolution order
        node = g.get_node(nid)
        name = node.name.lower()
        if name not in index:
            index[name] = nid
            continue
        existing = g.get_node(index[name])
        if {existing.node_type, node.node_type} == {"asset", "crown_jewel"}:
            # asset realizes crown jewel — prefer the concrete asset node.
            # If the asset is the one that just arrived, switch to it; otherwise
            # the existing entry is already the asset, so keep it.
            if node.node_type == "asset":
                index[name] = nid
            continue
        raise BuilderBlocked(
            f"duplicate case-insensitive node name {name!r} between two "
            f"{existing.node_type!r}/{node.node_type!r} nodes "
            f"({index[name]!r}, {nid!r}) — cannot disambiguate"
        )
    return index


def _wire_realized_crown_jewels(g: Graph) -> None:
    """When an inventory asset shares a crown jewel's (case-insensitive) name,
    the asset *realizes* that jewel. Wire a ``data_resides_on`` edge asset->jewel
    so path enumeration can traverse the realization.

    Idempotent: the edge_id is deterministic, and the explicit ``edge_id in g._edges``
    guard below skips re-adding an edge a prior pass (e.g. _add_crown_jewels via data
    classifications) already created, so this never triggers add_edge's duplicate-id error.

    Note: two crown jewels sharing a name is unreachable here — a same-type
    jewel/jewel name collision is blocked upstream by ``_node_name_index``, so
    ``jewels_by_name`` cannot silently drop a jewel.
    """
    jewels_by_name = {n.name.lower(): n for n in g.nodes_by_type("crown_jewel")}
    for asset in g.nodes_by_type("asset"):
        jewel = jewels_by_name.get(asset.name.lower())
        if jewel is None:
            continue
        edge_id = stable_id("edge", asset.node_id, jewel.node_id, "data_resides_on")
        if edge_id in g._edges:
            continue  # already wired (e.g. by _add_crown_jewels via classification)
        g.add_edge(
            Edge(
                edge_id=edge_id,
                edge_type="data_resides_on",
                from_node=asset.node_id,
                to_node=jewel.node_id,
                provenance={"source": "asset_inventory", "locator": "name_realizes_crown_jewel"},
                confidence=asset.confidence,
                traversal_cost=1,
            )
        )


def _add_finding_edges(g: Graph, findings: list[dict[str, Any]]) -> None:
    """Wire a `compromisable_via_finding` edge per finding whose detail or
    evidence excerpts name at least two graph nodes (case-insensitive).

    Findings whose text doesn't name two nodes are dropped at this layer —
    the analyzer reports them separately as "unwired" risks.
    """
    node_names = _node_name_index(g)
    for f in findings:
        text_parts = [str(f.get("detail", ""))]
        text_parts.extend(
            str(ev.get("excerpt", "")) for ev in f.get("evidence", []) if isinstance(ev, dict)
        )
        text = " ".join(text_parts).lower()
        hits: list[str] = []
        for name, nid in node_names.items():
            if name in text and nid not in hits:
                hits.append(nid)
        if len(hits) >= 2:
            cost = _SEVERITY_TO_COST.get(f.get("severity", "medium"), 4)
            g.add_edge(
                Edge(
                    edge_id=stable_id(
                        "edge",
                        hits[0],
                        hits[1],
                        "compromisable_via_finding",
                        f["id"],
                    ),
                    edge_type="compromisable_via_finding",
                    from_node=hits[0],
                    to_node=hits[1],
                    provenance={
                        "source": "artifact",
                        "artifact": "specialist findings",
                        "locator": f["id"],
                    },
                    confidence=f.get("confidence", "medium"),
                    traversal_cost=cost,
                    finding_id=f["id"],
                )
            )


def _add_capability_edges(g: Graph, capabilities: list[dict[str, Any]]) -> None:
    """Mirror of `_add_finding_edges` for capabilities."""
    node_names = _node_name_index(g)
    for c in capabilities:
        text_parts = [str(c.get("description", "")), str(c.get("scope", ""))]
        text_parts.extend(
            str(ev.get("excerpt", "")) for ev in c.get("evidence", []) if isinstance(ev, dict)
        )
        text = " ".join(text_parts).lower()
        hits: list[str] = []
        for name, nid in node_names.items():
            if name in text and nid not in hits:
                hits.append(nid)
        if len(hits) >= 2:
            g.add_edge(
                Edge(
                    edge_id=stable_id(
                        "edge",
                        hits[0],
                        hits[1],
                        "mitigated_by_capability",
                        c["id"],
                    ),
                    edge_type="mitigated_by_capability",
                    from_node=hits[0],
                    to_node=hits[1],
                    provenance={
                        "source": "artifact",
                        "artifact": "specialist capabilities",
                        "locator": c["id"],
                    },
                    confidence=c.get("confidence", "medium"),
                    traversal_cost=1,
                    capability_id=c["id"],
                )
            )


def _add_threat_model_edges(g: Graph, tm: dict[str, Any]) -> None:
    """For each TM entry whose `asset` matches an inventory asset name
    (case-insensitive), wire a `network_reachable` edge from every
    attacker_position to that asset.

    Provenance source distinguishes the TM's authority:
    - a recon-parsed, operator-supplied TM (`generated_by:
      threat_model_recon`, or the legacy default) is DECLARED coverage →
      `provenance.source = 'threat_model'`;
    - an author-agent baseline (`generated_by: threat_model_author`) is the
      gauntlet's own INFERRED reconstruction, not operator ground truth →
      `provenance.source = 'threat_model_inferred'`. Each authored entry
      keeps its own `extraction_confidence` rather than borrowing
      declared-ground-truth weight.
    """
    source = (
        "threat_model_inferred"
        if tm.get("generated_by") == "threat_model_author"
        else "threat_model"
    )
    node_names = _node_name_index(g)
    attackers = g.nodes_by_type("attacker_position")
    for entry in tm.get("entries", []):
        asset_field = entry.get("asset")
        if not isinstance(asset_field, str):
            continue
        asset_lower = asset_field.lower()
        if asset_lower not in node_names:
            continue
        asset_id = node_names[asset_lower]
        for atk in attackers:
            g.add_edge(
                Edge(
                    edge_id=stable_id(
                        "edge",
                        atk.node_id,
                        asset_id,
                        "network_reachable",
                        entry["entry_id"],
                    ),
                    edge_type="network_reachable",
                    from_node=atk.node_id,
                    to_node=asset_id,
                    provenance={
                        "source": source,
                        "locator": entry["entry_id"],
                    },
                    confidence=entry.get("extraction_confidence", "medium"),
                    traversal_cost=2,
                )
            )


def _add_code_evidence_edges(g: Graph, code: dict[str, Any]) -> None:
    """code-evidence-index entries declaring cross-service calls become
    `network_reachable` edges between the corresponding asset nodes.

    NOTE: The current code-evidence-index schema does not yet expose a
    `cross_service_calls` field — its top-level shape is
    `{code_evidence_index: {entries: [...]}}` where entries carry function /
    excerpt metadata. This helper therefore looks under the wrapper for a
    `cross_service_calls` list and is a no-op when that field is absent.
    A future task will reconcile the schema with this helper.
    """
    container = code.get("code_evidence_index") if isinstance(code, dict) else None
    if not isinstance(container, dict):
        container = code if isinstance(code, dict) else {}
    node_names = _node_name_index(g)
    for call in container.get("cross_service_calls", []):
        if not isinstance(call, dict):
            continue
        src = str(call.get("caller", "")).lower()
        dst = str(call.get("callee", "")).lower()
        if src in node_names and dst in node_names:
            locator = str(call.get("locator", ""))
            g.add_edge(
                Edge(
                    edge_id=stable_id(
                        "edge",
                        node_names[src],
                        node_names[dst],
                        "network_reachable",
                        locator,
                    ),
                    edge_type="network_reachable",
                    from_node=node_names[src],
                    to_node=node_names[dst],
                    provenance={
                        "source": "code_evidence",
                        "artifact": "00-context/code-evidence-index.yaml",
                        "locator": locator,
                    },
                    confidence="high",
                    traversal_cost=1,
                )
            )
