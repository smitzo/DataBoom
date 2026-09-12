import csv
import json
from pathlib import Path

from databoom.graph import (
    GraphEdgeSpec,
    GraphGenerator,
    GraphNodeSpec,
    GraphPropertySpec,
    validate_graph_artifacts,
)


def test_graph_generator_writes_json_csv_manifest_and_validation(tmp_path: Path) -> None:
    result = GraphGenerator(
        nodes=(
            GraphNodeSpec(
                "Customer",
                3,
                (GraphPropertySpec("segment", "segment"),),
            ),
            GraphNodeSpec(
                "Account",
                2,
                (GraphPropertySpec("account_type", "account_type"),),
            ),
        ),
        edges=(
            GraphEdgeSpec(
                "OWNS",
                "Customer",
                "Account",
                4,
                (GraphPropertySpec("weight", "weight"),),
            ),
        ),
        row_counts={},
        seed="graph-test",
        output_dir=tmp_path,
        output_formats=("json", "csv"),
    ).generate()

    assert result.total_rows == 9
    assert result.validation["passed"] is True
    assert result.manifest.manifest_path.exists()
    assert result.validation_path.exists()
    assert result.manifest.artifact.graph_json_path is not None
    assert result.manifest.artifact.nodes_csv_path is not None
    assert result.manifest.artifact.edges_csv_path is not None

    graph_payload = json.loads(result.manifest.artifact.graph_json_path.read_text())
    assert len(graph_payload["nodes"]) == 5
    assert len(graph_payload["edges"]) == 4
    assert graph_payload["nodes"][0]["id"] == "customer-00000001"

    with result.manifest.artifact.nodes_csv_path.open(newline="", encoding="utf-8") as handle:
        node_rows = list(csv.DictReader(handle))
    with result.manifest.artifact.edges_csv_path.open(newline="", encoding="utf-8") as handle:
        edge_rows = list(csv.DictReader(handle))

    assert len(node_rows) == 5
    assert len(edge_rows) == 4
    assert set(edge_rows[0]) == {"id", "type", "source", "target", "properties"}


def test_validate_graph_artifacts_detects_dangling_edges(tmp_path: Path) -> None:
    result = GraphGenerator(
        nodes=(GraphNodeSpec("Customer", 1), GraphNodeSpec("Account", 1)),
        edges=(GraphEdgeSpec("OWNS", "Customer", "Account", 1),),
        row_counts={},
        seed="dangling-test",
        output_dir=tmp_path,
        output_formats=("csv",),
    ).generate()
    assert result.manifest.artifact.edges_csv_path is not None

    result.manifest.artifact.edges_csv_path.write_text(
        "id,type,source,target,properties\n"
        'owns-00000001,OWNS,missing-node,account-00000001,{}\n',
        encoding="utf-8",
    )

    validation = validate_graph_artifacts(result.manifest)

    assert validation["passed"] is False
    assert {issue["code"] for issue in validation["issues"]} == {"dangling_edge_source"}
