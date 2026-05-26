"""Parser for attack-tree threat models in three sub-formats."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from lxml import etree

_ATTACK_TECHNIQUE_KEYWORDS: dict[str, str] = {
    "phishing":              "T1566",
    "spear phishing":        "T1566.001",
    "spearphishing":         "T1566.001",
    "valid account":         "T1078",
    "credential stuffing":   "T1110.004",
    "password spray":        "T1110.003",
    "command injection":     "T1059",
    "powershell":            "T1059.001",
    "scheduled task":        "T1053",
    "registry run key":      "T1547.001",
    "sudo abuse":            "T1548.003",
    "credential dumping":    "T1003",
    "kerberoasting":         "T1558.003",
    "smb lateral":           "T1021.002",
    "rdp lateral":           "T1021.001",
    "rdp":                   "T1021.001",
    "data staging":          "T1074",
    "exfiltrate over c2":    "T1041",
    "ransomware":            "T1486",
    "data destruction":      "T1485",
}


def _map_text_to_attack_techniques(text: str) -> list[str]:
    """Case-insensitive substring search against the keyword map. Returns sorted unique matches."""
    lower = text.lower()
    matches = {tid for kw, tid in _ATTACK_TECHNIQUE_KEYWORDS.items() if kw in lower}
    return sorted(matches)


def _stable_entry_id(threat: str, position: str) -> str:
    raw = f"{threat}|{position}".encode()
    return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40]


def _build_entry(
    *,
    threat: str,
    position: str,
    is_root: bool,
    is_leaf: bool,
    gate: str | None = None,
) -> dict[str, Any]:
    confidence = "low" if (is_root or not is_leaf) else "medium"
    techniques = _map_text_to_attack_techniques(threat) if is_leaf else []
    position_label = position if gate is None else f"{position} ({gate})"
    return {
        "entry_id": _stable_entry_id(threat, position),
        "asset": "(attack-tree node)",  # attack trees don't have per-node assets
        "threat": threat,
        "mitigation": None,
        "methodology": "attack_tree",
        "source_locator": position,
        "extraction_confidence": confidence,
        "framework_refs": {
            "stride_letter": None,
            "linddun_letter": None,
            "attack_tree_position": position_label,
            "mitre_attack": techniques,
        },
        "inferred_apd_goals": [],  # leaves with ATT&CK matches get goals via the cross-ref layer
    }


# ---------- indented-prose parser ----------

_GATE_KEYWORDS: frozenset[str] = frozenset({"AND", "OR"})


def parse_indented_prose(text: str) -> list[dict[str, Any]]:
    """Parse an indented-prose attack tree (4 spaces or 1 tab per level)."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    root_node = _build_prose_tree(lines)
    return _walk_node(root_node, parent_path="", entries=[])


def _build_prose_tree(lines: list[str]) -> dict[str, Any]:
    """Build a nested dict tree from indented prose."""
    root: dict[str, Any] = {"label": "", "children": [], "gate": None}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]  # (indent, node)
    pending_gate: str | None = None
    for line in lines:
        indent_chars = len(line) - len(line.lstrip())
        # Indent level: 1 per 4 spaces (or 1 per tab)
        level = (indent_chars + (line.count("\t") * 3)) // 4
        content = line.strip()
        if content.upper() in _GATE_KEYWORDS:
            pending_gate = content.upper()
            continue
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else root
        node: dict[str, Any] = {"label": content, "children": [], "gate": pending_gate}
        pending_gate = None
        parent["children"].append(node)
        stack.append((level, node))
    return root


def _walk_node(
    node: dict[str, Any],
    parent_path: str,
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    label = node["label"]
    if not label:
        # Synthetic root with empty label; walk children directly
        for child in node["children"]:
            _walk_node(child, parent_path, entries)
        return entries
    slug = _slugify(label)
    position = f"{parent_path}/{slug}" if parent_path else "root"
    is_root = parent_path == ""
    is_leaf = not node["children"]
    # Gate is only meaningful on intermediate nodes (children of root); skip on root itself
    gate = node.get("gate") if not is_root else None
    entries.append(_build_entry(
        threat=label,
        position=position,
        is_root=is_root,
        is_leaf=is_leaf,
        gate=gate,
    ))
    for child in node["children"]:
        _walk_node(child, position, entries)
    return entries


# ---------- ADTool XML parser ----------

def parse_adtool_xml(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse ADTool XML attack tree (XXE-safe)."""
    parser = etree.XMLParser(
        recover=True,
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
    )
    try:
        root_xml = etree.fromstring(xml_bytes, parser=parser)
    except etree.XMLSyntaxError:
        return []
    if root_xml is None:
        return []
    # ADTool root is <adtree><node>...</node></adtree>; the first <node> is our root
    root_node_xml = root_xml.find("node")
    if root_node_xml is None:
        return []
    tree = _adtool_node_to_dict(root_node_xml)
    entries: list[dict[str, Any]] = []
    _walk_node({"label": "", "children": [tree], "gate": None}, parent_path="", entries=entries)
    return entries


def _adtool_node_to_dict(node_xml: etree._Element) -> dict[str, Any]:
    label_elem = node_xml.find("label")
    label = (label_elem.text or "").strip() if label_elem is not None else ""
    refinement = node_xml.get("refinement", "disjunctive")
    gate = "AND" if refinement == "conjunctive" else "OR" if refinement == "disjunctive" else None
    children = [_adtool_node_to_dict(child) for child in node_xml.findall("node")]
    return {"label": label, "children": children, "gate": gate}


# ---------- JSON parser ----------

def parse_attack_tree_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a JSON attack tree (generic {goal, gate, children[]} convention)."""
    tree = _json_node_to_dict(data)
    entries: list[dict[str, Any]] = []
    _walk_node({"label": "", "children": [tree], "gate": None}, parent_path="", entries=entries)
    return entries


def _json_node_to_dict(data: dict[str, Any]) -> dict[str, Any]:
    label = data.get("goal") or data.get("label") or ""
    gate = data.get("gate")
    children = [_json_node_to_dict(c) for c in (data.get("children") or [])]
    return {"label": label, "children": children, "gate": gate}


# ---------- dispatcher (called by Task B-17's CLI) ----------

def parse_attack_tree(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return parse_indented_prose(path.read_text(encoding="utf-8"))
    if suffix == ".xml":
        return parse_adtool_xml(path.read_bytes())
    if suffix == ".json":
        return parse_attack_tree_json(json.loads(path.read_text(encoding="utf-8")))
    raise ValueError(f"Unsupported attack-tree file extension: {suffix}")
