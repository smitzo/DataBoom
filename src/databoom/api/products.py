"""Product catalog definitions for the demo dashboard API.

Purpose:
    Describe which DataBoom product modules exist, what they generate, and which
    local demo specs power the dashboard workspace.

Data flow:
    catalog entries -> `/products` API responses -> dashboard product selection ->
    product generation run.

Why this layer exists:
    Product metadata should be declarative. The execution layer can then choose the
    correct engine from `kind` instead of hardcoding product IDs across routes.
"""

from __future__ import annotations

from dataclasses import dataclass

from databoom.api.models import DataProductKind, ProductStatus
from databoom.document import DocumentCollectionSpec, DocumentFieldSpec
from databoom.generation import DomainProfile
from databoom.graph import GraphEdgeSpec, GraphNodeSpec, GraphPropertySpec


@dataclass(frozen=True)
class ProductPlan:
    """Subscription plan metadata for one product."""

    id: str
    name: str
    price: str
    description: str


@dataclass(frozen=True)
class ProductCatalogEntry:
    """Runnable product module configuration.

    `kind` is the switch that routes a product into relational, document, graph, or
    masking execution paths. This keeps use-case examples separate from engine
    architecture.
    """

    id: str
    name: str
    family: str
    module: str
    kind: DataProductKind
    status: ProductStatus
    description: str
    domain: DomainProfile
    output_formats: tuple[str, ...]
    features: tuple[str, ...]
    plans: tuple[ProductPlan, ...]
    use_cases: tuple[str, ...] = ()
    schema_ddl: str | None = None
    default_row_counts: dict[str, int] | None = None
    document_collections: tuple[DocumentCollectionSpec, ...] = ()
    graph_nodes: tuple[GraphNodeSpec, ...] = ()
    graph_edges: tuple[GraphEdgeSpec, ...] = ()

    @property
    def tables(self) -> tuple[str, ...]:
        """Return generated table names in display order."""

        return tuple(self.default_row_counts or {})

    @property
    def collections(self) -> tuple[str, ...]:
        """Return generated collection names in display order."""

        return tuple(collection.name for collection in self.document_collections)

    @property
    def default_counts(self) -> dict[str, int]:
        """Return table or collection counts by generated resource name."""

        if self.kind == DataProductKind.DOCUMENT:
            return {
                collection.name: collection.default_count
                for collection in self.document_collections
            }
        if self.kind == DataProductKind.GRAPH:
            node_counts = {node.label: node.default_count for node in self.graph_nodes}
            edge_counts = {edge.edge_type: edge.default_count for edge in self.graph_edges}
            return node_counts | edge_counts
        return dict(self.default_row_counts or {})


DEFAULT_PLANS = (
    ProductPlan(
        id="starter",
        name="Starter",
        price="$0 local",
        description="Local demo subscription for development and product validation.",
    ),
    ProductPlan(
        id="team",
        name="Team",
        price="$499/mo",
        description="Planned shared workspace with persisted runs, retention, and access controls.",
    ),
)


TABLE_BOOM_SCHEMA = """
    CREATE TABLE customers (
        id bigint PRIMARY KEY,
        full_name text NOT NULL,
        email text NOT NULL,
        phone text,
        segment text NOT NULL,
        status text NOT NULL
    );

    CREATE TABLE products (
        id bigint PRIMARY KEY,
        sku text NOT NULL,
        name text NOT NULL,
        category text,
        price numeric NOT NULL,
        status text NOT NULL
    );

    CREATE TABLE orders (
        id bigint PRIMARY KEY,
        customer_id bigint NOT NULL REFERENCES customers(id),
        status text NOT NULL,
        total_amount numeric NOT NULL,
        created_at timestamp
    );

    CREATE TABLE order_items (
        id bigint PRIMARY KEY,
        order_id bigint NOT NULL REFERENCES orders(id),
        product_id bigint NOT NULL REFERENCES products(id),
        quantity integer NOT NULL,
        amount numeric NOT NULL
    );

    CREATE TABLE payments (
        id bigint PRIMARY KEY,
        order_id bigint NOT NULL REFERENCES orders(id),
        payment_method text NOT NULL,
        payment_amount numeric NOT NULL,
        status text NOT NULL
    );
"""


DOCU_BOOM_COLLECTIONS = (
    DocumentCollectionSpec(
        name="customers",
        default_count=40,
        fields=(
            DocumentFieldSpec("_id", "object_id"),
            DocumentFieldSpec("email", "email"),
            DocumentFieldSpec("status", "status"),
            DocumentFieldSpec(
                "profile",
                "object",
                fields=(
                    DocumentFieldSpec("first_name", "first_name"),
                    DocumentFieldSpec("last_name", "last_name"),
                    DocumentFieldSpec("age", "integer"),
                    DocumentFieldSpec("loyalty_tier", "tier"),
                ),
            ),
            DocumentFieldSpec(
                "addresses",
                "array",
                item_fields=(
                    DocumentFieldSpec("city", "city"),
                    DocumentFieldSpec("country", "country"),
                    DocumentFieldSpec("postal_code", "postal_code"),
                ),
            ),
            DocumentFieldSpec("created_at", "timestamp"),
        ),
    ),
    DocumentCollectionSpec(
        name="orders",
        default_count=120,
        fields=(
            DocumentFieldSpec("_id", "object_id"),
            DocumentFieldSpec("customer_id", "reference", target_collection="customers"),
            DocumentFieldSpec("status", "order_status"),
            DocumentFieldSpec(
                "items",
                "array",
                item_fields=(
                    DocumentFieldSpec("sku", "sku"),
                    DocumentFieldSpec("name", "product_name"),
                    DocumentFieldSpec("quantity", "quantity"),
                    DocumentFieldSpec("price", "money"),
                ),
            ),
            DocumentFieldSpec("total", "money"),
            DocumentFieldSpec("created_at", "timestamp"),
        ),
    ),
    DocumentCollectionSpec(
        name="events",
        default_count=180,
        fields=(
            DocumentFieldSpec("_id", "object_id"),
            DocumentFieldSpec("customer_id", "reference", target_collection="customers"),
            DocumentFieldSpec("event_name", "event_name"),
            DocumentFieldSpec(
                "metadata",
                "object",
                fields=(
                    DocumentFieldSpec("channel", "channel"),
                    DocumentFieldSpec("campaign", "campaign"),
                    DocumentFieldSpec("score", "number"),
                ),
            ),
            DocumentFieldSpec("created_at", "timestamp"),
        ),
    ),
)


GRAPH_BOOM_NODES = (
    GraphNodeSpec(
        label="Customer",
        default_count=80,
        properties=(
            GraphPropertySpec("segment", "segment"),
            GraphPropertySpec("status", "status"),
            GraphPropertySpec("country", "country"),
        ),
    ),
    GraphNodeSpec(
        label="Account",
        default_count=120,
        properties=(
            GraphPropertySpec("account_type", "account_type"),
            GraphPropertySpec("status", "status"),
            GraphPropertySpec("risk_score", "risk_score"),
        ),
    ),
    GraphNodeSpec(
        label="Device",
        default_count=60,
        properties=(
            GraphPropertySpec("device_type", "device_type"),
            GraphPropertySpec("risk_score", "risk_score"),
            GraphPropertySpec("country", "country"),
        ),
    ),
)


GRAPH_BOOM_EDGES = (
    GraphEdgeSpec(
        edge_type="OWNS",
        source_label="Customer",
        target_label="Account",
        default_count=140,
        properties=(GraphPropertySpec("weight", "weight"),),
    ),
    GraphEdgeSpec(
        edge_type="USES_DEVICE",
        source_label="Customer",
        target_label="Device",
        default_count=180,
        properties=(GraphPropertySpec("timestamp", "timestamp"),),
    ),
    GraphEdgeSpec(
        edge_type="TRANSFERRED_TO",
        source_label="Account",
        target_label="Account",
        default_count=260,
        properties=(
            GraphPropertySpec("amount", "amount"),
            GraphPropertySpec("timestamp", "timestamp"),
            GraphPropertySpec("risk_score", "risk_score"),
        ),
    ),
)


PRODUCT_CATALOG: tuple[ProductCatalogEntry, ...] = (
    ProductCatalogEntry(
        id="table-boom",
        name="Table-Boom",
        family="DataBoom",
        module="Relational data",
        kind=DataProductKind.RELATIONAL,
        status=ProductStatus.ACTIVE,
        description="Generate relational table data with primary-key and foreign-key integrity.",
        domain=DomainProfile.FINANCIAL,
        schema_ddl=TABLE_BOOM_SCHEMA,
        default_row_counts={
            "customers": 24,
            "products": 16,
            "orders": 48,
            "order_items": 96,
            "payments": 48,
        },
        output_formats=("csv", "sql"),
        use_cases=("financial records", "healthcare records", "commerce orders", "SaaS audit data"),
        features=(
            "PostgreSQL schema-aware generation.",
            "Relationship-safe parent and child rows.",
            "CSV and SQL exports with validation reports.",
        ),
        plans=DEFAULT_PLANS,
    ),
    ProductCatalogEntry(
        id="docu-boom",
        name="Docu-Boom",
        family="DataBoom",
        module="NoSQL document data",
        kind=DataProductKind.DOCUMENT,
        status=ProductStatus.ACTIVE,
        description=(
            "Generate MongoDB-style nested JSON and NDJSON collections for document workflows."
        ),
        domain=DomainProfile.GENERAL,
        document_collections=DOCU_BOOM_COLLECTIONS,
        output_formats=("json", "ndjson"),
        use_cases=("customer profiles", "orders", "events", "catalog documents"),
        features=(
            "Nested objects and arrays for document-style records.",
            "Stable object IDs and simple cross-collection references.",
            "JSON and NDJSON exports with document previews.",
        ),
        plans=DEFAULT_PLANS,
    ),
    ProductCatalogEntry(
        id="graph-boom",
        name="Graph-Boom",
        family="DataBoom",
        module="Graph data",
        kind=DataProductKind.GRAPH,
        status=ProductStatus.ACTIVE,
        description="Generate connected node and edge datasets with labels and properties.",
        domain=DomainProfile.GENERAL,
        graph_nodes=GRAPH_BOOM_NODES,
        graph_edges=GRAPH_BOOM_EDGES,
        output_formats=("json", "csv"),
        use_cases=("fraud networks", "recommendations", "knowledge graphs"),
        features=(
            "Node and edge generation with stable IDs.",
            "Edge-reference validation for generated graph artifacts.",
            "JSON graph and CSV node/edge exports.",
        ),
        plans=DEFAULT_PLANS,
    ),
    ProductCatalogEntry(
        id="masker-boom",
        name="Masker-Boom",
        family="DataBoom",
        module="Masking and redaction",
        kind=DataProductKind.MASKING,
        status=ProductStatus.PLANNED,
        description=(
            "Redact, tokenize, hash, or replace sensitive source data while preserving useful "
            "structure."
        ),
        domain=DomainProfile.GENERAL,
        output_formats=("csv", "json"),
        use_cases=("PII redaction", "tokenized joins", "privacy audits"),
        features=(
            "Planned sensitive-field classification.",
            "Planned masking policies and privacy validation.",
            "Planned audit reports for sensitive data workflows.",
        ),
        plans=DEFAULT_PLANS,
    ),
)


def list_products() -> tuple[ProductCatalogEntry, ...]:
    """Return the product catalog."""

    return PRODUCT_CATALOG


def get_product(product_id: str) -> ProductCatalogEntry:
    """Return one product catalog entry by ID."""

    for product in PRODUCT_CATALOG:
        if product.id == product_id:
            return product
    raise KeyError(product_id)
