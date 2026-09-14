"""API-facing plan construction, review, and execution mapping.

Purpose:
    Translate catalog/source metadata into provider-neutral planner contracts and
    convert an approved proposal back into the existing product-run request.

Data flow:
    product + optional workspace source + proposal request -> `PlannerRequest` ->
    stored proposal -> review transition -> `ProductRunRequest`.

Why this layer exists:
    Route handlers should own HTTP concerns, while planner metadata mapping and
    review invariants remain testable without a web server.
"""

from __future__ import annotations

from datetime import UTC, datetime

from databoom.api.models import (
    DataProductKind,
    ProductPlanProposalRequest,
    ProductRunRequest,
)
from databoom.api.products import ProductCatalogEntry
from databoom.api.workspaces import WorkspaceSource
from databoom.planning import (
    PlannerRequest,
    PlanProposal,
    PlanResourceInput,
    PlanResourceKind,
    PlanReviewStatus,
    ProductKind,
)


def planner_request_from_product(
    product: ProductCatalogEntry,
    payload: ProductPlanProposalRequest,
    *,
    source: WorkspaceSource | None = None,
) -> PlannerRequest:
    """Build normalized planner input without including source row values."""

    if product.kind == DataProductKind.MASKING:
        raise ValueError("Masker-Boom planning starts in Phase 4")

    resources = _resource_inputs(product, source)
    known_names = {resource.name for resource in resources}
    unknown_names = sorted(payload.row_counts.keys() - known_names)
    if unknown_names:
        raise ValueError(f"unknown planning resources: {', '.join(unknown_names)}")

    resources = tuple(
        resource.model_copy(
            update={"default_count": payload.row_counts.get(resource.name, resource.default_count)}
        )
        for resource in resources
    )
    output_formats = tuple(payload.output_formats or product.output_formats)
    unsupported = sorted(set(output_formats) - set(product.output_formats))
    if unsupported:
        raise ValueError(f"unsupported output formats: {', '.join(unsupported)}")

    return PlannerRequest(
        product_id=product.id,
        product_kind=ProductKind(product.kind.value),
        intent=payload.intent,
        seed=payload.seed,
        output_formats=output_formats,
        resources=resources,
    )


def review_plan(
    plan: PlanProposal,
    *,
    status: PlanReviewStatus,
    reviewer: str,
) -> PlanProposal:
    """Apply one explicit terminal review decision to a draft plan."""

    if plan.review_status != PlanReviewStatus.DRAFT:
        raise ValueError("plan has already been reviewed")
    if status == PlanReviewStatus.DRAFT:
        raise ValueError("review status must be approved or rejected")
    payload = plan.model_dump(mode="python")
    payload.update(
        review_status=status,
        reviewed_by=reviewer,
        reviewed_at=datetime.now(UTC),
    )
    return PlanProposal.model_validate(payload)


def run_request_from_approved_plan(
    plan: PlanProposal,
    *,
    source_id: str | None = None,
) -> ProductRunRequest:
    """Convert only an approved proposal into the engine's existing run contract."""

    if plan.review_status != PlanReviewStatus.APPROVED:
        raise ValueError("approve the plan before generation")
    return ProductRunRequest(
        row_counts={resource.name: resource.target_count for resource in plan.decision.resources},
        seed=plan.seed,
        output_formats=plan.output_formats,
        source_id=source_id,
        plan_id=plan.plan_id,
    )


def _resource_inputs(
    product: ProductCatalogEntry,
    source: WorkspaceSource | None,
) -> tuple[PlanResourceInput, ...]:
    if source is not None:
        return _source_resource_inputs(product, source)
    if product.kind == DataProductKind.RELATIONAL:
        return tuple(
            PlanResourceInput(
                name=name,
                kind=PlanResourceKind.TABLE,
                default_count=count,
            )
            for name, count in product.default_counts.items()
        )
    if product.kind == DataProductKind.DOCUMENT:
        return tuple(
            PlanResourceInput(
                name=collection.name,
                kind=PlanResourceKind.COLLECTION,
                default_count=collection.default_count,
                attributes=tuple(field.name for field in collection.fields),
            )
            for collection in product.document_collections
        )

    nodes = tuple(
        PlanResourceInput(
            name=node.label,
            kind=PlanResourceKind.NODE,
            default_count=node.default_count,
            attributes=tuple(prop.name for prop in node.properties),
        )
        for node in product.graph_nodes
    )
    edges = tuple(
        PlanResourceInput(
            name=edge.edge_type,
            kind=PlanResourceKind.EDGE,
            default_count=edge.default_count,
            attributes=tuple(prop.name for prop in edge.properties),
            source_resource=edge.source_label,
            target_resource=edge.target_label,
        )
        for edge in product.graph_edges
    )
    return nodes + edges


def _source_resource_inputs(
    product: ProductCatalogEntry,
    source: WorkspaceSource,
) -> tuple[PlanResourceInput, ...]:
    if product.kind != DataProductKind.GRAPH:
        kind = (
            PlanResourceKind.TABLE
            if product.kind == DataProductKind.RELATIONAL
            else PlanResourceKind.COLLECTION
        )
        return tuple(
            PlanResourceInput(
                name=resource.name,
                kind=kind,
                default_count=resource.estimated_rows,
                attributes=resource.columns,
            )
            for resource in source.resources
        )

    node_resources = tuple(
        resource for resource in source.resources if resource.resource_type.lower() == "node"
    )
    node_labels = tuple(_graph_label(resource.name) for resource in node_resources)
    if not node_labels:
        return _resource_inputs(product, None)
    source_label = node_labels[0]
    target_label = node_labels[1] if len(node_labels) > 1 else node_labels[0]
    nodes = tuple(
        PlanResourceInput(
            name=_graph_label(resource.name),
            kind=PlanResourceKind.NODE,
            default_count=resource.estimated_rows,
            attributes=tuple(column for column in resource.columns if column not in {"id", "_id"}),
        )
        for resource in node_resources
    )
    edges = tuple(
        PlanResourceInput(
            name=resource.name.upper(),
            kind=PlanResourceKind.EDGE,
            default_count=resource.estimated_rows,
            attributes=tuple(
                column
                for column in resource.columns
                if column not in {"id", "_id", "from", "to", "source", "target"}
            ),
            source_resource=source_label,
            target_resource=target_label,
        )
        for resource in source.resources
        if resource.resource_type.lower() == "edge"
    )
    return nodes + edges


def _graph_label(name: str) -> str:
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_") if part)
