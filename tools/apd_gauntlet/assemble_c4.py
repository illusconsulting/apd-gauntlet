"""Assemble 40-synthesis/c4-model.yaml: the deterministic, grounded C4
architecture model for the apd-gauntlet HTML report.

This module is the SOLE minter of c4-/c4e- ids and the SOLE author of the
per-node FINDINGS/CAPABILITY badge rollups (ADR-0020 field-ownership: agents
emit grounded CONTENT by name; the assembler mints ids and derived counts).

Never-invent discipline: no container/component/code node or uses-edge is
emitted without an artifact or code-evidence citation. L3 components are
HARD-BLOCKED unless an artifact (c4-recon.components[]) groups symbols; the
default is to OMIT L3 and parent code nodes directly to their container.

Inputs (all under run_dir):
  00-context/c4-recon.yaml            (optional; agent-authored container/uses names)
  00-context/code-evidence-index.yaml (optional; code anchors -> L4 + repos[] -> L2)
  00-context/asset-inventory.yaml     (optional; identities/external deps -> L1)
  40-synthesis/asset-graph.yaml       (presence GATES the run)
  40-synthesis/deduped-findings.yaml  (FINDINGS badge source)
  40-synthesis/deduped-capabilities.yaml (CAPABILITY badge source)

Output:
  40-synthesis/c4-model.yaml  (assembler-minted ids + badges + build_summary)

Public entrypoint: ``assemble_c4(run_dir) -> dict`` (writes the file, returns
build_summary). Idempotent.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml


def c4_node_id(level: str, name: str, parent_name: str) -> str:
    """Deterministic C4 node id: ``c4-<sha8(level|name|parent_name)>``.

    Mirrors the attack-path/findings ``<prefix>-<sha8(seed)>`` scheme. The seed
    is the node's stable natural key: its level, its grounded NAME, and its
    parent's NAME ("" for a top-level node). Including level+parent keeps a
    same-named code symbol distinct from a same-named container and keeps a
    symbol unique across the repos it appears in.
    """
    seed = f"{level}|{name}|{parent_name}"
    return "c4-" + hashlib.sha256(seed.encode()).hexdigest()[:8]


def c4_edge_id(from_name: str, to_name: str) -> str:
    """Deterministic C4 'uses' edge id: ``c4e-<sha8("uses|"+from+"|"+to)>``.

    Directional: ``from``/``to`` order is part of the natural key, so A->B and
    B->A receive distinct ids.
    """
    seed = f"uses|{from_name}|{to_name}"
    return "c4e-" + hashlib.sha256(seed.encode()).hexdigest()[:8]


# The four code-anchor kinds that become L4 ``code`` nodes. ``edge`` entries in
# the index are cross-repo 'uses' edges, handled separately (Task 4).
_CODE_KINDS: frozenset[str] = frozenset({"function", "class", "route", "module"})


def _yaml_optional(path: Path) -> dict[str, Any] | None:
    """Load a YAML mapping, or return None when absent/empty/non-mapping."""
    if not path.exists():
        return None
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def _repo_short(repo: str) -> str:
    """Map a CBM project / repo string to the container NAME used everywhere.

    ``Users-...-home-assistant-repos-core`` -> ``core``. A bare name passes
    through unchanged, so an explicit c4-recon container name also works.
    """
    if "-repos-" in repo:
        return repo.split("-repos-")[-1]
    return repo


def _code_entries(cei: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        e for e in (cei.get("entries") or [])
        if isinstance(e, dict) and e.get("kind") in _CODE_KINDS
    ]


def _name_for_id(
    node_id: str, container_id_by_name: dict[str, str], fallback: str
) -> str:
    """The container NAME that mints ``node_id`` (inverse of
    ``container_id_by_name``), or ``fallback`` if none — used to fold the parent
    container's display name into a code node's own id seed."""
    for name, cid in container_id_by_name.items():
        if cid == node_id:
            return name
    return fallback


def build_code_nodes(
    cei: dict[str, Any],
    container_id_by_name: dict[str, str],
    component_id_by_name: dict[str, str] | None = None,
    container_id_by_repo: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """L4: one ``code`` node per code-anchor entry (function/class/route/module).

    Grounding: every node carries the entry's qualified_name (as name+locator),
    its repo (as the container), and source=code_evidence. Never invented.

    Parent resolution (the ONE coherent contract — never-invent /
    L3-block-by-default). The grounded source for code->component->container
    parenting is the PER-ENTRY ``c4_component`` / ``c4_container`` tags on the
    code-evidence-index entry, resolved against the ALREADY-MINTED component and
    container ids (never re-hashed from the entry repo when a tag applies, so the
    parent pointer is always an EMITTED id — no dangling refs). Precedence:

      1. ``c4_component`` present AND in ``component_id_by_name`` -> that
         component's minted id;
      2. elif ``c4_container`` present AND in ``container_id_by_name`` -> that
         container's minted id;
      3. elif a truthy ``repo`` -> ``container_id_by_repo[_repo_short(repo)]``,
         the minted id of the container that CLAIMS that repo. When a c4-recon
         PROCESS container declares this repo, that resolves to the display-named
         container (e.g. "Home Assistant Core"); otherwise it is the repos[]-
         derived short-name container ("core"). Always an EMITTED id;
      4. else -> None (top-level).

    The parent's NAME (component name / container name / "") is folded into this
    node's own seed so the index-only path is byte-identical: a repo-only entry
    (no c4-recon) seeds ``code|qname|<repo-short>`` exactly as before, since the
    repos[]-derived container is named by the repo short-name. A tagged entry
    seeds against the tag name; a repo claimed by a display-named c4-recon
    process container seeds against that display name. An entry with an empty
    qualified_name is skipped (no empty-name node is ever emitted), and code
    nodes are DE-DUPED by minted id so two entries sharing qualified_name+parent
    collapse to one node dict (duplicate ids crash Cytoscape and corrupt counts).
    """
    component_id_by_name = component_id_by_name or {}
    container_id_by_repo = container_id_by_repo or {}
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for e in _code_entries(cei):
        qname = str(e.get("qualified_name", "") or "").strip()
        if not qname:
            continue  # never emit an empty-name code node
        repo = e.get("repo")
        repo_short = _repo_short(str(repo)) if repo else ""
        comp_tag = str(e.get("c4_component", "") or "").strip()
        cont_tag = str(e.get("c4_container", "") or "").strip()
        if comp_tag and comp_tag in component_id_by_name:
            parent_name = comp_tag
            parent_id: str | None = component_id_by_name[comp_tag]
        elif cont_tag and cont_tag in container_id_by_name:
            parent_name = cont_tag
            parent_id = container_id_by_name[cont_tag]
        elif repo_short and repo_short in container_id_by_repo:
            # the container CLAIMING this repo: the display-named c4-recon
            # process container when one declares it, else the repos[]-derived
            # short-name container. Its NAME (display name or repo-short) is
            # folded into the seed below.
            parent_id = container_id_by_repo[repo_short]
            parent_name = _name_for_id(parent_id, container_id_by_name, repo_short)
        elif repo_short:
            # repo names a container that was not minted (e.g. only c4-recon
            # containers, no repos[] match, none claiming this repo) -> mint the
            # deterministic container id by name so the parent stays grounded to
            # the repo short-name (no dangling parent ref).
            parent_name = repo_short
            parent_id = c4_node_id("container", repo_short, "")
        else:
            # no resolvable container -> top-level, ungrouped (never invent one).
            parent_name = ""
            parent_id = None
        prov: dict[str, Any] = {
            "source": "code_evidence",
            "locator": qname,
        }
        if repo_short:
            prov["repo"] = repo_short
        node_id = c4_node_id("code", qname, parent_name)
        if node_id in seen:
            continue  # de-dup: same qualified_name+parent -> one node dict
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "level": "code",
            "parent": parent_id,
            "name": qname,
            "kind": str(e.get("kind", "")),
            "provenance": prov,
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes


def build_component_nodes(
    c4_recon: dict[str, Any] | None,
    container_id_by_name: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """L3: one ``component`` node per c4-recon ``components[]`` entry.

    HARD-BLOCK by default: if c4-recon is absent or ``components[]`` is empty,
    return ([], {}) (no L3 — code parents directly to its container). A component
    is emitted only when an artifact groups symbols, and only when its declared
    container resolves to a minted container id.

    The component node's parent is the MINTED id of its declared container, and
    its own id is folded against that container NAME. Returns the node list plus
    ``component_id_by_name = {comp.name: minted_component_id}`` so code nodes can
    parent to the EMITTED id (never re-hashing from a member entry's repo).
    De-duped by minted id (two same-name components under the same container
    collapse to one node dict).
    """
    if not isinstance(c4_recon, dict):
        return [], {}
    nodes: list[dict[str, Any]] = []
    component_id_by_name: dict[str, str] = {}
    seen: set[str] = set()
    for c in c4_recon.get("components") or []:
        name = str(c.get("name", ""))
        container_name = str(c.get("container", ""))
        parent_id = container_id_by_name.get(container_name)
        if not name or not parent_id:
            continue  # never-invent: skip an ungrounded / unparented component
        node_id = c4_node_id("component", name, container_name)
        component_id_by_name.setdefault(name, node_id)
        if node_id in seen:
            continue
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "level": "component",
            "parent": parent_id,
            "name": name,
            "kind": "component",
            "provenance": c.get("provenance") or {"source": "artifact"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes, component_id_by_name


# default container kind when neither c4-recon nor a heuristic assigns one.
_DEFAULT_CONTAINER_KIND = "service"

# The container kinds that REPRESENT a code repo (a running/built process or a
# library compiled from a repo). A c4-recon container of one of these kinds with
# a truthy ``repo`` field CLAIMS that repo, so its display name + kind ENRICH the
# repo-derived container (code nodes parent to it) instead of minting a duplicate
# short-name container. ``data_store`` and ``external_system`` do NOT represent a
# repo — any ``repo`` they carry is provenance metadata, not a containment claim.
PROCESS_KINDS: frozenset[str] = frozenset({"service", "compute", "app", "library"})


def _code_bearing_repos(cei: dict[str, Any]) -> set[str]:
    """Container NAMES (repo short-names) that have >=1 code anchor.

    Defensive: an entry with a falsy/``None``/empty ``repo`` does NOT name a
    container — including it would mint an empty-name container node, which
    violates the schema (``name`` is minLength 1). Only truthy repo strings
    become containers; repo-less entries stay ungrouped (top-level code nodes).
    """
    return {_repo_short(r) for e in _code_entries(cei) if (r := e.get("repo"))}


def _declared_repos(cei: dict[str, Any]) -> list[str]:
    """Container NAMES for every declared repo, in declared order, de-duped.

    Defensive: skip a null / non-mapping ``repos[]`` entry and any entry whose
    ``cbm_project`` is falsy/empty — neither names a container, and emitting one
    would mint an empty-name container node (schema ``name`` is minLength 1).
    """
    out: list[str] = []
    seen: set[str] = set()
    for r in cei.get("repos") or []:
        if not isinstance(r, dict):
            continue
        project = r.get("cbm_project")
        if not project:
            continue
        name = _repo_short(str(project))
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    # Defensive: a repo that appears only on entries (not in repos[]) is still a
    # real container.
    for name in sorted(_code_bearing_repos(cei)):
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def build_container_nodes(
    c4_recon: dict[str, Any] | None,
    cei: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """L2: one ``container`` node per repo/container, with repo reconciliation.

    Sources, in precedence order:
      * c4-recon ``containers[]`` (agent-authored, grounded by name+provenance),
        when present — carries kind + provenance verbatim, minted BY NAME;
      * the code-evidence-index ``repos[]`` list, for every declared repo whose
        short-name is NOT already CLAIMED by a c4-recon process container.

    Repo reconciliation. A c4-recon container whose ``kind`` is a
    :data:`PROCESS_KINDS` (service/compute/app/library) and that carries a truthy
    ``repo`` field REPRESENTS that repo: it CLAIMS ``_repo_short(repo)`` in the
    returned ``container_id_by_repo`` map, so the repos[]-derived short-name
    container is NOT also minted (no duplicate) and code nodes for that repo
    parent to the display-named container instead. ``data_store`` /
    ``external_system`` containers are minted by name but never claim a repo
    (their ``repo`` field, if any, is provenance metadata, not a containment
    claim). A repos[] repo with no claiming process container mints its own
    short-name container and claims its own short-name.

    Returns ``(nodes, container_id_by_repo)`` where ``container_id_by_repo`` maps
    each repo short-name to the minted id of the container representing it.

    Honesty rule: a container with zero code anchors renders
    ``analysis_state: not_analyzed`` (NEVER "0 findings = clean"). A container
    that c4-recon explicitly tags ``analysis_state: not_analyzed`` is honored.
    """
    code_bearing = _code_bearing_repos(cei) if cei else set()
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    container_id_by_repo: dict[str, str] = {}

    def _state(name: str, declared: str | None) -> str:
        if declared in ("analyzed", "not_analyzed"):
            return declared
        return "analyzed" if name in code_bearing else "not_analyzed"

    # 1) c4-recon containers (authored content), minted by display NAME. A
    #    process-kind container with a truthy repo CLAIMS that repo so the
    #    repos[] pass below does not mint a duplicate short-name container.
    for c in (c4_recon or {}).get("containers") or []:
        name = str(c.get("name", ""))
        if not name or name in seen:
            continue
        seen.add(name)
        node_id = c4_node_id("container", name, "")
        kind = str(c.get("kind") or _DEFAULT_CONTAINER_KIND)
        repo = c.get("repo")
        if kind in PROCESS_KINDS and repo:
            container_id_by_repo.setdefault(_repo_short(str(repo)), node_id)
        prov = c.get("provenance") or {"source": "artifact"}
        nodes.append({
            "id": node_id,
            "level": "container",
            "parent": None,
            "name": name,
            "kind": kind,
            "provenance": prov,
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": _state(name, c.get("analysis_state")),
        })

    # 2) index repos[] whose short-name is not already CLAIMED by a c4-recon
    #    process container (those reconcile to the display-named container above).
    for name in _declared_repos(cei or {}):
        if name in container_id_by_repo:
            continue  # claimed by a c4-recon process container -> no duplicate
        node_id = c4_node_id("container", name, "")
        container_id_by_repo.setdefault(name, node_id)
        if name in seen:
            continue
        seen.add(name)
        nodes.append({
            "id": node_id,
            "level": "container",
            "parent": None,
            "name": name,
            "kind": _DEFAULT_CONTAINER_KIND,
            "provenance": {"source": "code_evidence", "locator": f"repos[]:{name}"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": _state(name, None),
        })
    return nodes, container_id_by_repo


# Host-infrastructure markers: an endpoint half bearing any of these denotes
# the host (a unix socket, host daemon, /run or /var/run path) rather than a
# repo container. cev-0a000003 ("... -> /run/docker.sock (host dockerd)") would
# otherwise SUBSTRING-match the unrelated 'docker' repo container and emit a
# false supervisor->docker edge -- never-invent says drop an ungroundable
# endpoint rather than guess a wrong one.
_HOST_INFRA_MARKERS: tuple[str, ...] = (
    ".sock",
    "/run/",
    "/var/run",
    "(host ",
    "host dockerd",
)


def _is_host_infra(text: str) -> bool:
    """True when ``text`` (a qualified_name endpoint half) denotes host
    infrastructure (a socket / host daemon / host path) rather than a repo.

    Guards the substring matcher in ``_resolve_endpoint`` against the
    cev-0a000003 ("/run/docker.sock (host dockerd)") false-positive: see
    ``_HOST_INFRA_MARKERS``. Never-invent."""
    low = text.lower()
    return any(marker in low for marker in _HOST_INFRA_MARKERS)


def _resolve_endpoint(text: str, container_names: set[str], fallback: str) -> str:
    """Pick the container NAME named in ``text`` (a qualified_name half), else
    ``fallback``. Longest match wins so 'os-agent' is not shadowed by a prefix.

    Never-invent guard (cev-0a000003): a host-infrastructure half (e.g.
    ``/run/docker.sock (host dockerd)``) is NOT a repo container, so return the
    ``fallback`` verbatim instead of substring-matching it to an unrelated repo.
    For a ``to`` half the fallback is "" -> the edge is dropped; for a ``from``
    half the fallback is its attributed repo, which is preserved."""
    if _is_host_infra(text):
        return fallback
    hit = ""
    for name in container_names:
        if name and name.lower() in text.lower() and len(name) > len(hit):
            hit = name
    return hit or fallback


def build_uses_edges(
    c4_recon: dict[str, Any] | None,
    cei: dict[str, Any] | None,
    container_id_by_name: dict[str, str],
) -> list[dict[str, Any]]:
    """L2->L2 ``uses`` edges.

    Two grounded sources:
      * c4-recon ``uses_edges[]`` — authored from CROSS_* code edges or hand-read
        code evidence; carries its own ``machine_extracted`` flag + provenance;
      * the code-evidence-index ``kind: edge`` entries — cross-repo edges the
        auto-linker missed, read by hand from code (file_path). These are always
        ``machine_extracted: False``.

    Never-invent: an edge whose ``from`` or ``to`` container name cannot be
    resolved to a minted container id is DROPPED (not guessed). De-duped on the
    minted edge id so the same A->B from two sources collapses to one.
    """
    names = set(container_id_by_name)
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _emit(from_name: str, to_name: str, label: str, machine: bool,
              prov: dict[str, Any]) -> None:
        fid = container_id_by_name.get(from_name)
        tid = container_id_by_name.get(to_name)
        if not fid or not tid or fid == tid:
            return  # unresolved endpoint or self-loop -> drop, never guess
        eid = c4_edge_id(from_name, to_name)
        if eid in seen:
            return
        seen.add(eid)
        edges.append({
            "id": eid,
            "edge_type": "uses",
            "from": fid,
            "to": tid,
            "label": label,
            "machine_extracted": bool(machine),
            "provenance": prov,
        })

    # 1) c4-recon authored uses_edges (content by name).
    for u in (c4_recon or {}).get("uses_edges") or []:
        _emit(
            str(u.get("from", "")),
            str(u.get("to", "")),
            str(u.get("label", "uses")),
            bool(u.get("machine_extracted", False)),
            u.get("provenance") or {"source": "artifact"},
        )

    # 2) index kind:edge entries (hand-read cross-repo edges).
    for e in (cei or {}).get("entries") or []:
        if not isinstance(e, dict) or e.get("kind") != "edge":
            continue
        qname = str(e.get("qualified_name", ""))
        attributed = _repo_short(str(e.get("repo", "")))
        left, _, right = qname.partition(" -> ")
        from_name = _resolve_endpoint(left, names, attributed)
        to_name = _resolve_endpoint(right, names, "")
        label = str(e.get("excerpt", "") or e.get("notes", "") or "uses")[:120]
        prov = {
            "source": "code_evidence",
            "locator": f"{e.get('id', '')}:{e.get('file_path', '')}",
        }
        _emit(from_name, to_name, label, False, prov)
    return edges


# identity_type values that become L1 ``person`` nodes (human actors / external
# parties). service_account identities are NOT persons (they are machine
# principals) and are intentionally excluded from L1.
_PERSON_IDENTITY_TYPES = frozenset({"human_role", "external_party"})


def build_l1_nodes(
    inv: dict[str, Any] | None,
    subject: str,
) -> list[dict[str, Any]]:
    """L1 System Context: one synthesized ``system`` node (the run subject),
    plus ``person`` nodes (human_role / external_party identities) and
    ``external_system`` nodes (external_dependency assets).

    All grounded: persons/external systems carry the inventory entry's name +
    provenance verbatim; the single system node is the run subject (source
    run_config). Badges are zeroed here and filled by the badge join (Task 7).
    """
    inv = inv or {}
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()

    # The run-subject system node (synthesized, exactly one).
    sysname = subject or "System"
    sys_id = c4_node_id("system", sysname, "")
    seen.add(sys_id)
    nodes.append({
        "id": sys_id,
        "level": "system",
        "parent": None,
        "name": sysname,
        "kind": "software_system",
        "provenance": {"source": "run_config", "locator": "subject"},
        "finding_count": 0,
        "capability_count": 0,
        "analysis_state": "analyzed",
    })

    for i in inv.get("identities") or []:
        if i.get("identity_type") not in _PERSON_IDENTITY_TYPES:
            continue
        name = str(i.get("name", ""))
        if not name:
            continue
        node_id = c4_node_id("person", name, "")
        if node_id in seen:
            continue  # de-dup: collapse same-name person identities
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "level": "person",
            "parent": None,
            "name": name,
            "kind": str(i.get("identity_type", "person")),
            "provenance": (i.get("provenance") or {"source": "asset_inventory"})
            | {"source": "asset_inventory"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })

    for a in inv.get("assets") or []:
        if a.get("asset_type") != "external_dependency":
            continue
        name = str(a.get("name", ""))
        if not name:
            continue
        node_id = c4_node_id("external_system", name, "")
        if node_id in seen:
            continue  # de-dup: collapse same-name external systems
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "level": "external_system",
            "parent": None,
            "name": name,
            "kind": "external_dependency",
            "provenance": (a.get("provenance") or {"source": "asset_inventory"})
            | {"source": "asset_inventory"},
            "finding_count": 0,
            "capability_count": 0,
            "analysis_state": "analyzed",
        })
    return nodes


# A ``code:<qualified_name>[:Lx-Ly][@sha]`` evidence locator. Group 1 is the
# bare qualified_name (the badge-join key), stopping at the first ':' or '@'.
_CODE_LOCATOR_RE = re.compile(r"^code:([^:@]+)")


def _qname_to_container(cei: dict[str, Any]) -> dict[str, str]:
    """qualified_name -> container NAME for every code anchor."""
    return {
        str(e.get("qualified_name", "")): _repo_short(str(e.get("repo", "")))
        for e in _code_entries(cei)
    }


def _record_ids_by_qname(
    records: list[dict[str, Any]],
) -> dict[str, set[str]]:
    """qualified_name -> set of DISTINCT record ids citing it via a code: locator.

    A record that cites the same qname twice contributes its id once; a record
    that cites two qnames contributes its id to both. The set-of-ids structure
    is what makes every downstream rollup count DISTINCT ids.
    """
    out: dict[str, set[str]] = {}
    for r in records or []:
        rid = r.get("id")
        if not rid:
            continue
        for ev in r.get("evidence") or []:
            m = _CODE_LOCATOR_RE.match(str(ev.get("locator") or ""))
            if m:
                out.setdefault(m.group(1), set()).add(str(rid))
    return out


def _unlocalized_finding_count(findings: list[dict[str, Any]]) -> int:
    """DISTINCT findings with NO ``code:`` evidence locator (doc-anchored only).
    Surfaced explicitly so doc-only findings are never silently dropped."""
    count = 0
    for f in findings or []:
        if not any(
            _CODE_LOCATOR_RE.match(str(ev.get("locator") or ""))
            for ev in (f.get("evidence") or [])
        ):
            count += 1
    return count


def apply_badges(
    nodes: list[dict[str, Any]],
    cei: dict[str, Any] | None,
    findings: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
) -> dict[str, int]:
    """Compute + write ``finding_count`` / ``capability_count`` on every node in
    place (DISTINCT-id rollups), and return the global badge summary.

    Algorithm:
      1. Build qname -> {record ids} for findings and for capabilities.
      2. For each ``code`` node, attach the DISTINCT id SET for its qname (a
         multi-locator record lands once).
      3. Roll those sets UP the parent chain (code -> component -> container),
         UNIONing ids so a container holding several hit code nodes counts a
         shared finding once. ``finding_count`` is then ``len(set)``.
      4. ``unlocalized_finding_count`` = findings with no ``code:`` locator.

    L1 nodes (system/person/external_system) have no code subtree, so their
    badges stay 0 here; the asset-graph-driven L1 badge join is a later
    milestone and does not change these counts.
    """
    cei = cei or {}
    find_ids_by_qname = _record_ids_by_qname(findings)
    cap_ids_by_qname = _record_ids_by_qname(capabilities)

    by_id = {n["id"]: n for n in nodes}
    # accumulate DISTINCT id sets per node id, then roll up the parent chain.
    find_sets: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    cap_sets: dict[str, set[str]] = {n["id"]: set() for n in nodes}

    # 1+2: seed code nodes from their own qname.
    for n in nodes:
        if n.get("level") != "code":
            continue
        qname = n.get("name", "")
        find_sets[n["id"]] |= find_ids_by_qname.get(qname, set())
        cap_sets[n["id"]] |= cap_ids_by_qname.get(qname, set())

    # 3: roll up. Walk each node to the root via parent ids, unioning the leaf
    # set into every ancestor. (Depth <= 3: code -> component? -> container.)
    for n in nodes:
        if n.get("level") != "code":
            continue
        leaf_find = find_sets[n["id"]]
        leaf_cap = cap_sets[n["id"]]
        if not leaf_find and not leaf_cap:
            continue
        parent_id = n.get("parent")
        guard = 0
        while parent_id and parent_id in by_id and guard < 8:
            find_sets[parent_id] |= leaf_find
            cap_sets[parent_id] |= leaf_cap
            parent_id = by_id[parent_id].get("parent")
            guard += 1

    for n in nodes:
        find_set = find_sets[n["id"]]
        n["finding_count"] = len(find_set)
        n["capability_count"] = len(cap_sets[n["id"]])
        # Record the deterministic first contributing finding id for the
        # report's per-node finding deep-link (only when the set is non-empty).
        if find_set:
            n.setdefault("provenance", {})["first_finding_id"] = sorted(find_set)[0]

    return {"unlocalized_finding_count": _unlocalized_finding_count(findings)}


def _build_summary(nodes: list[dict[str, Any]], edges: list[dict[str, Any]],
                   badge_summary: dict[str, int]) -> dict[str, int]:
    by_level: dict[str, int] = {}
    for n in nodes:
        by_level[n["level"]] = by_level.get(n["level"], 0) + 1
    not_analyzed = sum(
        1 for n in nodes
        if n["level"] == "container" and n["analysis_state"] == "not_analyzed"
    )
    return {
        "node_count": len(nodes),
        "system_count": by_level.get("system", 0),
        "person_count": by_level.get("person", 0),
        "external_system_count": by_level.get("external_system", 0),
        "container_count": by_level.get("container", 0),
        "component_count": by_level.get("component", 0),
        "code_count": by_level.get("code", 0),
        "uses_edge_count": len(edges),
        "unlocalized_finding_count": badge_summary.get("unlocalized_finding_count", 0),
        "not_analyzed_container_count": not_analyzed,
    }


def _records(doc: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    recs = doc.get(key)
    return recs if isinstance(recs, list) else []


def assemble_c4(run_dir: Path) -> dict[str, Any]:
    """Assemble 40-synthesis/c4-model.yaml. Returns its build_summary.

    GATING: a no-op (returns {}) unless 40-synthesis/asset-graph.yaml exists —
    the C4 view is presence-gated on the same artifact as the attack-path graph.
    The code tiers (L4/L3) are populated only when
    00-context/code-evidence-index.yaml exists; otherwise only L1/L2 render.
    Idempotent: nodes/edges are id-sorted and the writer is byte-stable.
    """
    synth = run_dir / "40-synthesis"
    context = run_dir / "00-context"
    if not (synth / "asset-graph.yaml").exists():
        return {}

    cei = _yaml_optional(context / "code-evidence-index.yaml")
    cei_inner = cei.get("code_evidence_index") if isinstance(cei, dict) else None
    cei_inner = cei_inner if isinstance(cei_inner, dict) else (cei or {})

    c4_recon = _yaml_optional(context / "c4-recon.yaml")
    inv = _yaml_optional(context / "asset-inventory.yaml")
    findings = _records(_yaml_optional(synth / "deduped-findings.yaml"), "finding")
    caps = _records(_yaml_optional(synth / "deduped-capabilities.yaml"), "capability")
    subject = _subject(run_dir)

    # L2 first (containers are the parent for code + edge endpoints). The repo
    # reconciliation map resolves a code entry's repo to the container that
    # CLAIMS it (a display-named c4-recon process container, else the repos[]-
    # derived short-name container).
    containers, container_id_by_repo = build_container_nodes(
        c4_recon=c4_recon, cei=cei_inner
    )
    container_id_by_name = {n["name"]: n["id"] for n in containers}

    # L3 (blocked-by-default) then L4 (code), with component re-parenting. Code
    # nodes parent to the EMITTED component/container ids (never re-hashed), so
    # the parent pointer is always a real node id (no dangling refs).
    components, component_id_by_name = build_component_nodes(
        c4_recon=c4_recon, container_id_by_name=container_id_by_name
    )
    code = (
        build_code_nodes(
            cei_inner,
            container_id_by_name=container_id_by_name,
            component_id_by_name=component_id_by_name,
            container_id_by_repo=container_id_by_repo,
        )
        if cei_inner
        else []
    )

    # L1 system context.
    l1 = build_l1_nodes(inv, subject=subject)

    edges = build_uses_edges(
        c4_recon=c4_recon, cei=cei_inner,
        container_id_by_name=container_id_by_name,
    )

    nodes = l1 + containers + components + code
    badge_summary = apply_badges(nodes, cei=cei_inner, findings=findings, capabilities=caps)

    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: e["id"])
    build_summary = _build_summary(nodes, edges, badge_summary)

    doc = {
        "schema_version": 1,
        "generated_by": "assemble_c4",
        "nodes": nodes,
        "edges": edges,
        "build_summary": build_summary,
    }
    out = synth / "c4-model.yaml"
    tmp = out.with_suffix(".yaml.tmp")
    tmp.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096),
        encoding="utf-8",
    )
    tmp.replace(out)  # atomic on POSIX
    return build_summary


def _subject(run_dir: Path) -> str:
    cfg = _yaml_optional(run_dir / ".apd-run.yaml") or {}
    subj = cfg.get("subject")
    return str(subj) if subj else run_dir.name
