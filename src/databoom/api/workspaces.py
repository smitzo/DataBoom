"""Workspace source catalog for dashboard product workspaces."""

from __future__ import annotations

from dataclasses import dataclass

from databoom.api.models import DataProductKind, WorkspaceSourceStatus


@dataclass(frozen=True)
class WorkspaceResource:
    """One table, collection, or roadmap resource in a source."""

    name: str
    resource_type: str
    estimated_rows: int
    columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkspaceSource:
    """Database or source connection available to one product workspace."""

    id: str
    product_id: str
    kind: DataProductKind
    name: str
    engine: str
    host: str
    description: str
    status: WorkspaceSourceStatus
    resources: tuple[WorkspaceResource, ...]


WORKSPACE_SOURCES: tuple[WorkspaceSource, ...] = (
    WorkspaceSource(
        id="core-banking",
        product_id="table-boom",
        kind=DataProductKind.RELATIONAL,
        name="Core Banking Sandbox",
        engine="PostgreSQL",
        host="banking-demo.internal",
        description="Accounts, customers, transactions, and payment rails.",
        status=WorkspaceSourceStatus.CONNECTED,
        resources=(
            WorkspaceResource("customers", "table", 24, ("id", "full_name", "email", "status")),
            WorkspaceResource(
                "bank_accounts",
                "table",
                36,
                ("id", "customer_id", "account_type", "balance"),
            ),
            WorkspaceResource(
                "transactions",
                "table",
                120,
                ("id", "account_id", "amount", "status", "posted_at"),
            ),
        ),
    ),
    WorkspaceSource(
        id="commerce-store",
        product_id="table-boom",
        kind=DataProductKind.RELATIONAL,
        name="Commerce Store",
        engine="PostgreSQL",
        host="commerce-demo.internal",
        description="Customer orders, products, order items, and payments.",
        status=WorkspaceSourceStatus.CONNECTED,
        resources=(
            WorkspaceResource("customers", "table", 24, ("id", "full_name", "email", "segment")),
            WorkspaceResource("products", "table", 16, ("id", "sku", "name", "price")),
            WorkspaceResource("orders", "table", 48, ("id", "customer_id", "status", "total")),
            WorkspaceResource("order_items", "table", 96, ("id", "order_id", "product_id")),
            WorkspaceResource("payments", "table", 48, ("id", "order_id", "amount", "status")),
        ),
    ),
    WorkspaceSource(
        id="patient-care",
        product_id="table-boom",
        kind=DataProductKind.RELATIONAL,
        name="Patient Care Warehouse",
        engine="PostgreSQL",
        host="health-demo.internal",
        description="Patient, encounter, claim, provider, and lab records.",
        status=WorkspaceSourceStatus.CONNECTED,
        resources=(
            WorkspaceResource("patients", "table", 40, ("id", "full_name", "dob", "status")),
            WorkspaceResource("encounters", "table", 85, ("id", "patient_id", "provider_id")),
            WorkspaceResource("claims", "table", 120, ("id", "patient_id", "amount", "status")),
            WorkspaceResource("providers", "table", 16, ("id", "full_name", "specialty")),
            WorkspaceResource("lab_results", "table", 120, ("id", "patient_id", "value")),
        ),
    ),
    WorkspaceSource(
        id="customer-events",
        product_id="docu-boom",
        kind=DataProductKind.DOCUMENT,
        name="Customer Events Cluster",
        engine="MongoDB",
        host="events-demo.internal",
        description="Nested customer documents, order events, and behavioral streams.",
        status=WorkspaceSourceStatus.CONNECTED,
        resources=(
            WorkspaceResource("customers", "collection", 40, ("_id", "email", "profile")),
            WorkspaceResource("orders", "collection", 120, ("_id", "customer_id", "items")),
            WorkspaceResource("events", "collection", 180, ("_id", "event_name", "metadata")),
        ),
    ),
    WorkspaceSource(
        id="clinical-documents",
        product_id="docu-boom",
        kind=DataProductKind.DOCUMENT,
        name="Clinical Documents",
        engine="MongoDB",
        host="clinical-docs.internal",
        description="Patient profiles, notes, claims, and nested healthcare payloads.",
        status=WorkspaceSourceStatus.CONNECTED,
        resources=(
            WorkspaceResource("patients", "collection", 50, ("_id", "profile", "coverage")),
            WorkspaceResource("clinical_notes", "collection", 140, ("_id", "patient_id", "note")),
            WorkspaceResource("claims", "collection", 160, ("_id", "patient_id", "amount")),
        ),
    ),
    WorkspaceSource(
        id="graph-roadmap",
        product_id="graph-boom",
        kind=DataProductKind.GRAPH,
        name="Relationship Graph Lab",
        engine="Neo4j",
        host="graph-demo.internal",
        description="Nodes, edges, and relationship-heavy roadmap datasets.",
        status=WorkspaceSourceStatus.PLANNED,
        resources=(
            WorkspaceResource("customers", "node", 100, ("id", "segment")),
            WorkspaceResource("accounts", "node", 150, ("id", "type")),
            WorkspaceResource("transactions", "edge", 500, ("from", "to", "amount")),
        ),
    ),
    WorkspaceSource(
        id="masking-lab",
        product_id="masker-boom",
        kind=DataProductKind.MASKING,
        name="Masking Policy Lab",
        engine="Local files",
        host="masker-demo.internal",
        description="Sensitive data classification and redaction policy testing.",
        status=WorkspaceSourceStatus.PLANNED,
        resources=(
            WorkspaceResource("pii_fields", "policy", 32, ("field", "classification")),
            WorkspaceResource("tokenized_customers", "sample", 100, ("id", "token", "status")),
            WorkspaceResource("audit_samples", "sample", 50, ("id", "policy", "result")),
        ),
    ),
)


def list_workspace_sources(product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
    """Return workspace sources, optionally scoped to one product."""

    if product_id is None:
        return WORKSPACE_SOURCES
    return tuple(source for source in WORKSPACE_SOURCES if source.product_id == product_id)


def get_workspace_source(source_id: str) -> WorkspaceSource:
    """Return one workspace source by identifier."""

    for source in WORKSPACE_SOURCES:
        if source.id == source_id:
            return source
    raise KeyError(source_id)
