"""Deterministic graph generation for Graph-Boom.

Purpose:
    Generate node and edge datasets from graph-specific specs.

Data flow:
    `GraphNodeSpec` and `GraphEdgeSpec` -> streamed JSON/CSV graph artifacts ->
    manifest and validation report.

Why this layer exists:
    Graph datasets care about endpoint validity, edge cardinality, and label/type
    semantics. Those rules are different from table foreign keys and document
    object references, so Graph-Boom owns a separate generator.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

from databoom.generation import SeedManager
from databoom.graph.models import GraphEdgeSpec, GraphNodeSpec, GraphPropertySpec

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class GraphArtifact:
    """Artifact paths and generated counts for one graph export."""

    node_count: int
    edge_count: int
    graph_json_path: Path | None = None
    nodes_csv_path: Path | None = None
    edges_csv_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "graph_json_path": str(self.graph_json_path) if self.graph_json_path else None,
            "nodes_csv_path": str(self.nodes_csv_path) if self.nodes_csv_path else None,
            "edges_csv_path": str(self.edges_csv_path) if self.edges_csv_path else None,
        }


@dataclass(frozen=True)
class GraphManifest:
    """Manifest for a Graph-Boom artifact export."""

    output_dir: Path
    manifest_path: Path
    artifact: GraphArtifact
    node_labels: tuple[str, ...]
    edge_types: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "artifact": self.artifact.to_dict(),
            "node_labels": list(self.node_labels),
            "edge_types": list(self.edge_types),
        }


@dataclass(frozen=True)
class GraphGenerationResult:
    """Generated graph metadata and validation summary."""

    manifest: GraphManifest
    total_rows: int
    validation_path: Path
    validation: dict[str, Any]


class GraphGenerator:
    """Generate graph nodes and edges with deterministic IDs.

    The generator stores compact node ID lists per label because valid edges need
    endpoint lookup. It still streams CSV/JSON output as records are produced, so
    artifact writing does not need to hold full node or edge dictionaries.
    """

    flush_interval = 1_000
    preview_flush_rows = 20

    def __init__(
        self,
        *,
        nodes: tuple[GraphNodeSpec, ...],
        edges: tuple[GraphEdgeSpec, ...],
        row_counts: dict[str, int],
        seed: int | str,
        output_dir: Path,
        output_formats: tuple[str, ...] = ("json", "csv"),
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.nodes = nodes
        self.edges = edges
        self.row_counts = row_counts
        self.seed_manager = SeedManager(seed)
        self.output_dir = output_dir
        self.output_formats = output_formats
        self.progress_callback = progress_callback
        self.node_ids_by_label: dict[str, list[str]] = {}

    def generate(self) -> GraphGenerationResult:
        """Generate graph artifacts and return manifest plus validation summary."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        graph_json_path = self.output_dir / "graph.json" if "json" in self.output_formats else None
        nodes_csv_path = self.output_dir / "nodes.csv" if "csv" in self.output_formats else None
        edges_csv_path = self.output_dir / "edges.csv" if "csv" in self.output_formats else None

        with _graph_json_writer(graph_json_path) as graph_writer, _csv_writer(
            nodes_csv_path,
            ("id", "label", "properties"),
        ) as node_writer, _csv_writer(
            edges_csv_path,
            ("id", "type", "source", "target", "properties"),
        ) as edge_writer:
            node_count = self._write_nodes(graph_writer, node_writer)
            edge_count = self._write_edges(graph_writer, edge_writer, node_count)

        artifact = GraphArtifact(
            node_count=node_count,
            edge_count=edge_count,
            graph_json_path=graph_json_path,
            nodes_csv_path=nodes_csv_path,
            edges_csv_path=edges_csv_path,
        )
        manifest = GraphManifest(
            output_dir=self.output_dir,
            manifest_path=self.output_dir / "manifest.json",
            artifact=artifact,
            node_labels=tuple(node.label for node in self.nodes),
            edge_types=tuple(edge.edge_type for edge in self.edges),
        )
        manifest.manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        validation = validate_graph_artifacts(manifest)
        validation_path = self.output_dir / "validation.json"
        validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")
        return GraphGenerationResult(
            manifest=manifest,
            total_rows=node_count + edge_count,
            validation_path=validation_path,
            validation=validation,
        )

    def _write_nodes(
        self,
        graph_writer: _graph_json_writer,
        node_writer: _csv_writer,
    ) -> int:
        completed_rows = 0
        for node in self.nodes:
            count = self.row_counts.get(node.label, node.default_count)
            ids: list[str] = []
            for index in range(count):
                record = self._node_record(node, index)
                ids.append(str(record["id"]))
                graph_writer.write_node(record)
                node_writer.write(
                    (
                        record["id"],
                        record["label"],
                        json.dumps(record["properties"], separators=(",", ":"), sort_keys=True),
                    )
                )
                completed_rows += 1
                self._maybe_report_progress(completed_rows, node.label)
            self.node_ids_by_label[node.label] = ids
        self._report_progress(completed_rows, "nodes")
        return completed_rows

    def _write_edges(
        self,
        graph_writer: _graph_json_writer,
        edge_writer: _csv_writer,
        completed_before_edges: int,
    ) -> int:
        edge_count = 0
        for edge in self.edges:
            count = self.row_counts.get(edge.edge_type, edge.default_count)
            source_ids = self.node_ids_by_label.get(edge.source_label, [])
            target_ids = self.node_ids_by_label.get(edge.target_label, [])
            if not source_ids or not target_ids:
                raise ValueError(
                    f"edge {edge.edge_type} requires generated source and target labels"
                )
            for index in range(count):
                record = self._edge_record(edge, index, source_ids, target_ids)
                graph_writer.write_edge(record)
                edge_writer.write(
                    (
                        record["id"],
                        record["type"],
                        record["source"],
                        record["target"],
                        json.dumps(record["properties"], separators=(",", ":"), sort_keys=True),
                    )
                )
                edge_count += 1
                self._maybe_report_progress(completed_before_edges + edge_count, edge.edge_type)
        self._report_progress(completed_before_edges + edge_count, "edges")
        return edge_count

    def _node_record(self, node: GraphNodeSpec, index: int) -> dict[str, Any]:
        return {
            "id": _node_id(node.label, index),
            "label": node.label,
            "properties": {
                property_spec.name: self._property_value(
                    "node",
                    node.label,
                    property_spec,
                    index,
                )
                for property_spec in node.properties
            },
        }

    def _edge_record(
        self,
        edge: GraphEdgeSpec,
        index: int,
        source_ids: list[str],
        target_ids: list[str],
    ) -> dict[str, Any]:
        stream = self.seed_manager.stream("graph-edge", edge.edge_type, index)
        return {
            "id": _edge_id(edge.edge_type, index),
            "type": edge.edge_type,
            "source": source_ids[stream.randrange(len(source_ids))],
            "target": target_ids[stream.randrange(len(target_ids))],
            "properties": {
                property_spec.name: self._property_value(
                    "edge",
                    edge.edge_type,
                    property_spec,
                    index,
                )
                for property_spec in edge.properties
            },
        }

    def _property_value(
        self,
        scope: str,
        owner: str,
        property_spec: GraphPropertySpec,
        index: int,
    ) -> Any:
        stream = self.seed_manager.stream("graph", scope, owner, property_spec.name, index)
        match property_spec.kind:
            case "segment":
                return _choice(stream, ("retail", "small_business", "enterprise", "vip"))
            case "status":
                return _choice(stream, ("active", "pending", "blocked", "closed"))
            case "account_type":
                return _choice(stream, ("checking", "savings", "credit", "loan"))
            case "device_type":
                return _choice(stream, ("ios", "android", "web", "pos"))
            case "risk_score":
                return round(stream.uniform(0.01, 0.99), 3)
            case "amount":
                return round(stream.uniform(5, 5_000), 2)
            case "weight":
                return round(stream.uniform(0.1, 1.0), 3)
            case "timestamp":
                base = datetime(2024, 1, 1, tzinfo=UTC)
                return (base + timedelta(minutes=stream.randint(0, 700_000))).isoformat()
            case "country":
                return _choice(stream, ("US", "CA", "GB", "DE", "IN"))
            case _:
                return f"{property_spec.name}_{index + 1}"

    def _maybe_report_progress(self, completed_rows: int, resource_name: str) -> None:
        should_report_preview = completed_rows == self.preview_flush_rows
        should_report_interval = completed_rows % self.flush_interval == 0
        if should_report_preview or should_report_interval:
            self._report_progress(completed_rows, resource_name)

    def _report_progress(self, completed_rows: int, resource_name: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(completed_rows, resource_name)


def validate_graph_artifacts(manifest: GraphManifest) -> dict[str, Any]:
    """Validate generated graph files for counts, duplicate IDs, and edge refs."""

    artifact = manifest.artifact
    node_ids: set[str] = set()
    issues: list[dict[str, str]] = []
    node_count = 0
    edge_count = 0

    for node in _iter_nodes(artifact):
        node_count += 1
        node_id = str(node.get("id", ""))
        if not node_id:
            issues.append(
                {
                    "code": "missing_node_id",
                    "message": "node is missing an id",
                    "resource_name": "nodes",
                }
            )
            continue
        if node_id in node_ids:
            issues.append(
                {
                    "code": "duplicate_node_id",
                    "message": f"node id {node_id} appears more than once",
                    "resource_name": "nodes",
                }
            )
        node_ids.add(node_id)

    for edge in _iter_edges(artifact):
        edge_count += 1
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source not in node_ids:
            issues.append(
                {
                    "code": "dangling_edge_source",
                    "message": f"edge source {source} does not exist",
                    "resource_name": "edges",
                }
            )
        if target not in node_ids:
            issues.append(
                {
                    "code": "dangling_edge_target",
                    "message": f"edge target {target} does not exist",
                    "resource_name": "edges",
                }
            )

    if node_count != artifact.node_count:
        issues.append(
            {
                "code": "node_count_mismatch",
                "message": f"manifest expected {artifact.node_count} nodes, found {node_count}",
                "resource_name": "nodes",
            }
        )
    if edge_count != artifact.edge_count:
        issues.append(
            {
                "code": "edge_count_mismatch",
                "message": f"manifest expected {artifact.edge_count} edges, found {edge_count}",
                "resource_name": "edges",
            }
        )

    return {
        "passed": not issues,
        "checked_graph_resources": ["nodes", "edges"],
        "node_count": node_count,
        "edge_count": edge_count,
        "node_labels": list(manifest.node_labels),
        "edge_types": list(manifest.edge_types),
        "issues": issues,
    }


def _iter_nodes(artifact: GraphArtifact) -> list[dict[str, Any]]:
    if artifact.nodes_csv_path is not None and artifact.nodes_csv_path.is_file():
        with artifact.nodes_csv_path.open("r", encoding="utf-8", newline="") as handle:
            return [
                {
                    "id": row["id"],
                    "label": row["label"],
                    "properties": _json_properties(row.get("properties")),
                }
                for row in csv.DictReader(handle)
            ]
    return _graph_json_records(artifact, "nodes")


def _iter_edges(artifact: GraphArtifact) -> list[dict[str, Any]]:
    if artifact.edges_csv_path is not None and artifact.edges_csv_path.is_file():
        with artifact.edges_csv_path.open("r", encoding="utf-8", newline="") as handle:
            return [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "source": row["source"],
                    "target": row["target"],
                    "properties": _json_properties(row.get("properties")),
                }
                for row in csv.DictReader(handle)
            ]
    return _graph_json_records(artifact, "edges")


def _graph_json_records(artifact: GraphArtifact, key: str) -> list[dict[str, Any]]:
    if artifact.graph_json_path is None or not artifact.graph_json_path.is_file():
        return []
    data = json.loads(artifact.graph_json_path.read_text(encoding="utf-8"))
    records = data.get(key, [])
    if isinstance(records, list):
        return [record for record in records if isinstance(record, dict)]
    return []


def _json_properties(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return data
    return {}


class _graph_json_writer:
    """Streaming writer for a combined graph JSON artifact."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.handle: TextIO | None = None
        self.first_node = True
        self.first_edge = True
        self.in_edges = False
        self.records_written = 0

    def __enter__(self) -> _graph_json_writer:
        if self.path is not None:
            self.handle = self.path.open("w", encoding="utf-8")
            self.handle.write('{\n  "nodes": [\n')
        return self

    def __exit__(self, *args) -> None:
        if self.handle is None:
            return
        if not self.in_edges:
            self.handle.write('\n  ],\n  "edges": [\n')
        self.handle.write("\n  ]\n}\n")
        self.handle.close()

    def write_node(self, node: dict[str, Any]) -> None:
        if self.handle is None:
            return
        if not self.first_node:
            self.handle.write(",\n")
        self.first_node = False
        self.handle.write("    ")
        self.handle.write(json.dumps(node, separators=(",", ":"), sort_keys=True))
        self._flush_if_needed()

    def write_edge(self, edge: dict[str, Any]) -> None:
        if self.handle is None:
            return
        if not self.in_edges:
            self.handle.write('\n  ],\n  "edges": [\n')
            self.in_edges = True
        if not self.first_edge:
            self.handle.write(",\n")
        self.first_edge = False
        self.handle.write("    ")
        self.handle.write(json.dumps(edge, separators=(",", ":"), sort_keys=True))
        self._flush_if_needed()

    def _flush_if_needed(self) -> None:
        self.records_written += 1
        if self.handle is not None and (
            self.records_written == GraphGenerator.preview_flush_rows
            or self.records_written % GraphGenerator.flush_interval == 0
        ):
            self.handle.flush()


class _csv_writer:
    """Small CSV writer wrapper that no-ops when a format is disabled."""

    def __init__(self, path: Path | None, headers: tuple[str, ...]) -> None:
        self.path = path
        self.headers = headers
        self.handle: TextIO | None = None
        self.writer: csv.writer | None = None
        self.rows_written = 0

    def __enter__(self) -> _csv_writer:
        if self.path is not None:
            self.handle = self.path.open("w", encoding="utf-8", newline="")
            self.writer = csv.writer(self.handle)
            self.writer.writerow(self.headers)
            self.handle.flush()
        return self

    def __exit__(self, *args) -> None:
        if self.handle is not None:
            self.handle.flush()
            self.handle.close()

    def write(self, row: tuple[Any, ...]) -> None:
        if self.writer is None or self.handle is None:
            return
        self.writer.writerow(row)
        self.rows_written += 1
        if self.rows_written == GraphGenerator.preview_flush_rows:
            self.handle.flush()
        elif self.rows_written % GraphGenerator.flush_interval == 0:
            self.handle.flush()


def _node_id(label: str, index: int) -> str:
    return f"{_slug(label)}-{index + 1:08d}"


def _edge_id(edge_type: str, index: int) -> str:
    return f"{_slug(edge_type)}-{index + 1:08d}"


def _slug(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in slug.split("_") if part)


def _choice(stream, values: tuple[Any, ...]) -> Any:
    return values[stream.randrange(len(values))]
