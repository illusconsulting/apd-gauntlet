"""Graph primitives for attack-path analysis.

Defines Node, Edge, Graph dataclasses with strict construction rules:
- Node IDs must match the prefix corresponding to node_type
- compromisable_via_finding edges require finding_id
- mitigated_by_capability edges require capability_id
- Adding an edge whose endpoints don't exist in the graph raises ValueError
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

NodeType = Literal["asset", "identity", "attacker_position", "crown_jewel"]
EdgeType = Literal[
    "network_reachable", "authn_required", "authz_grants",
    "data_resides_on", "trusts",
    "compromisable_via_finding", "mitigated_by_capability",
]
Confidence = Literal["high", "medium", "low"]

_NODE_PREFIX = {
    "asset": "asset-",
    "identity": "idn-",
    "attacker_position": "atk-",
    "crown_jewel": "jewel-",
}
_NODE_ID_RE = re.compile(r"^(asset|idn|atk|jewel)-[0-9a-f]{8}$")
_EDGE_ID_RE = re.compile(r"^edge-[0-9a-f]{8}$")


def stable_id(kind: str, *components: str) -> str:
    """Deterministic sha8-based ID with kind prefix.

    kind is one of: asset, idn, atk, jewel, edge.
    components are concatenated with '|' then hashed.
    """
    payload = "|".join((kind, *components)).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:8]
    prefix = "edge-" if kind == "edge" else _NODE_PREFIX.get(kind, f"{kind}-")
    return f"{prefix}{digest}"


@dataclass(frozen=True)
class Node:
    node_id: str
    node_type: NodeType
    name: str
    provenance: dict[str, str | int]
    confidence: Confidence
    asset_type: str | None = None
    data_classifications: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _NODE_ID_RE.match(self.node_id):
            raise ValueError(f"malformed node_id: {self.node_id}")
        expected_prefix = _NODE_PREFIX[self.node_type]
        if not self.node_id.startswith(expected_prefix):
            raise ValueError(
                f"node_id prefix {self.node_id[:6]!r} does not match node_type"
                f" {self.node_type!r} (expected {expected_prefix!r})"
            )
        if "source" not in self.provenance:
            raise ValueError("provenance must include 'source'")
        if self.confidence not in ("high", "medium", "low"):
            raise ValueError(f"invalid confidence: {self.confidence}")


@dataclass(frozen=True)
class Edge:
    edge_id: str
    edge_type: EdgeType
    from_node: str
    to_node: str
    provenance: dict[str, str | int]
    confidence: Confidence
    traversal_cost: int
    finding_id: str | None = None
    capability_id: str | None = None

    def __post_init__(self) -> None:
        if not _EDGE_ID_RE.match(self.edge_id):
            raise ValueError(f"malformed edge_id: {self.edge_id}")
        if self.edge_type == "compromisable_via_finding" and not self.finding_id:
            raise ValueError("compromisable_via_finding edge requires finding_id")
        if self.edge_type == "mitigated_by_capability" and not self.capability_id:
            raise ValueError("mitigated_by_capability edge requires capability_id")
        if not 1 <= self.traversal_cost <= 100:
            raise ValueError(f"traversal_cost out of range: {self.traversal_cost}")


@dataclass
class Graph:
    """In-memory adjacency-list graph. Not thread-safe; not meant to be."""

    _nodes: dict[str, Node] = field(default_factory=dict)
    _edges: dict[str, Edge] = field(default_factory=dict)
    _adj: dict[str, list[str]] = field(default_factory=dict)  # node_id -> list[edge_id]

    def add_node(self, node: Node) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"duplicate node: {node.node_id}")
        self._nodes[node.node_id] = node
        self._adj.setdefault(node.node_id, [])

    def add_edge(self, edge: Edge) -> None:
        if edge.from_node not in self._nodes:
            raise ValueError(f"unknown node: {edge.from_node}")
        if edge.to_node not in self._nodes:
            raise ValueError(f"unknown node: {edge.to_node}")
        if edge.edge_id in self._edges:
            raise ValueError(f"duplicate edge: {edge.edge_id}")
        self._edges[edge.edge_id] = edge
        self._adj[edge.from_node].append(edge.edge_id)

    def get_node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def get_edge(self, edge_id: str) -> Edge:
        return self._edges[edge_id]

    def outgoing(self, node_id: str) -> list[Edge]:
        return [self._edges[eid] for eid in self._adj.get(node_id, [])]

    def nodes_by_type(self, node_type: NodeType) -> list[Node]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)
