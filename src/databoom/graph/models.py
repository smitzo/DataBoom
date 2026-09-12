"""Graph generation model contracts for Graph-Boom.

Purpose:
    Describe graph datasets as node labels, edge types, and property specs.

Data flow:
    catalog/source graph specs -> `GraphGenerator` -> graph artifacts ->
    API run response and preview endpoints.

Why this layer exists:
    Graph data is relationship-first. Keeping it in graph-specific contracts
    avoids squeezing nodes and edges through relational table assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphPropertySpec:
    """Declarative property generated for a node or edge."""

    name: str
    kind: str


@dataclass(frozen=True)
class GraphNodeSpec:
    """One generated node label and its property shape."""

    label: str
    default_count: int
    properties: tuple[GraphPropertySpec, ...] = ()


@dataclass(frozen=True)
class GraphEdgeSpec:
    """One generated edge type and its endpoint labels."""

    edge_type: str
    source_label: str
    target_label: str
    default_count: int
    properties: tuple[GraphPropertySpec, ...] = ()

