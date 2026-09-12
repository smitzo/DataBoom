"""Workspace source catalog for dashboard product workspaces.

Purpose:
    Represent the databases, collections, and planned resources a user can select
    before running a product workspace.

Data flow:
    static/demo source definitions or refreshed live source metadata ->
    `WorkspaceSource` -> API responses -> dashboard resource rail -> product run.

Why this layer exists:
    Product selection and source selection are separate concerns. A user may run
    Table-Boom against multiple PostgreSQL sources; this module describes those
    sources without coupling them to generation execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from databoom.api.models import (
    DataProductKind,
    WorkspaceResourceRequest,
    WorkspaceSourceRequest,
    WorkspaceSourceStatus,
)
from databoom.schema import ColumnSchema, DatabaseSchema, ForeignKeyConstraint, TableSchema


@dataclass(frozen=True)
class WorkspaceColumn:
    """Column metadata discovered for a workspace resource."""

    name: str
    data_type: str
    type_family: str
    nullable: bool
    default: str | None = None
    is_primary_key: bool = False
    is_foreign_key: bool = False


@dataclass(frozen=True)
class WorkspaceForeignKey:
    """Foreign-key metadata discovered for a workspace resource."""

    columns: tuple[str, ...]
    referred_schema: str
    referred_table: str
    referred_columns: tuple[str, ...]
    name: str | None = None
    on_delete: str | None = None
    on_update: str | None = None


@dataclass(frozen=True)
class WorkspaceUniqueConstraint:
    """Unique constraint metadata discovered for a workspace resource."""

    columns: tuple[str, ...]
    name: str | None = None


@dataclass(frozen=True)
class WorkspaceResource:
    """One table, collection, or roadmap resource in a source."""

    name: str
    resource_type: str
    estimated_rows: int
    columns: tuple[str, ...] = ()
    schema_name: str | None = None
    primary_key: tuple[str, ...] = ()
    foreign_keys: tuple[WorkspaceForeignKey, ...] = ()
    unique_constraints: tuple[WorkspaceUniqueConstraint, ...] = ()
    column_details: tuple[WorkspaceColumn, ...] = ()


@dataclass(frozen=True)
class WorkspaceSource:
    """Database or source connection available to one product workspace.

    Refreshed relational sources may include `schema_ddl`, letting later runs use
    the live database shape instead of a baked-in demo schema.
    """

    id: str
    product_id: str
    kind: DataProductKind
    name: str
    engine: str
    host: str
    description: str
    status: WorkspaceSourceStatus
    resources: tuple[WorkspaceResource, ...]
    schema_ddl: str | None = None
    refreshed_at: datetime | None = None


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
        status=WorkspaceSourceStatus.CONNECTED,
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


def default_workspace_sources() -> tuple[WorkspaceSource, ...]:
    """Return the built-in workspace sources used to seed stores."""

    return WORKSPACE_SOURCES


def workspace_source_from_request(payload: WorkspaceSourceRequest) -> WorkspaceSource:
    """Convert an API request into the internal workspace source contract."""

    return WorkspaceSource(
        id=payload.id,
        product_id=payload.product_id,
        kind=payload.kind,
        name=payload.name,
        engine=payload.engine,
        host=payload.host,
        description=payload.description,
        status=payload.status,
        resources=tuple(_resource_from_request(resource) for resource in payload.resources),
    )


def workspace_source_from_schema(
    source: WorkspaceSource,
    database: DatabaseSchema,
    *,
    default_estimated_rows: int = 100,
) -> WorkspaceSource:
    """Return a copy of a source whose resources match an inspected database schema."""

    previous_counts = {resource.name: resource.estimated_rows for resource in source.resources}
    return WorkspaceSource(
        id=source.id,
        product_id=source.product_id,
        kind=source.kind,
        name=source.name,
        engine=source.engine,
        host=source.host,
        description=source.description,
        status=WorkspaceSourceStatus.CONNECTED,
        resources=tuple(
            _resource_from_table(table, previous_counts, default_estimated_rows)
            for table in database.tables
        ),
        schema_ddl=database_schema_to_postgres_ddl(database),
        refreshed_at=datetime.now(UTC),
    )


def database_schema_to_postgres_ddl(database: DatabaseSchema) -> str:
    """Serialize normalized schema metadata into PostgreSQL CREATE TABLE DDL."""

    statements = []
    for table in database.tables:
        definitions = [_column_definition_from_schema(column) for column in table.columns]
        if table.primary_key is not None:
            definitions.append(
                _constraint_definition(
                    table.primary_key.name,
                    "PRIMARY KEY",
                    table.primary_key.columns,
                )
            )
        for unique_constraint in table.unique_constraints:
            definitions.append(
                _constraint_definition(
                    unique_constraint.name,
                    "UNIQUE",
                    unique_constraint.columns,
                )
            )
        for foreign_key in table.foreign_keys:
            definitions.append(_foreign_key_definition(foreign_key))

        table_name = f"{_sql_identifier(table.schema_name)}.{_sql_identifier(table.name)}"
        body = ",\n    ".join(definitions)
        statements.append(f"CREATE TABLE {table_name} (\n    {body}\n);")
    return "\n\n".join(statements)


def workspace_source_to_payload(source: WorkspaceSource) -> dict[str, Any]:
    """Serialize a workspace source for durable JSON storage."""

    return {
        "id": source.id,
        "product_id": source.product_id,
        "kind": source.kind.value,
        "name": source.name,
        "engine": source.engine,
        "host": source.host,
        "description": source.description,
        "status": source.status.value,
        "schema_ddl": source.schema_ddl,
        "refreshed_at": source.refreshed_at.isoformat() if source.refreshed_at else None,
        "resources": [
            {
                "name": resource.name,
                "resource_type": resource.resource_type,
                "estimated_rows": resource.estimated_rows,
                "columns": list(resource.columns),
                "schema_name": resource.schema_name,
                "primary_key": list(resource.primary_key),
                "foreign_keys": [
                    {
                        "columns": list(foreign_key.columns),
                        "referred_schema": foreign_key.referred_schema,
                        "referred_table": foreign_key.referred_table,
                        "referred_columns": list(foreign_key.referred_columns),
                        "name": foreign_key.name,
                        "on_delete": foreign_key.on_delete,
                        "on_update": foreign_key.on_update,
                    }
                    for foreign_key in resource.foreign_keys
                ],
                "unique_constraints": [
                    {
                        "columns": list(unique_constraint.columns),
                        "name": unique_constraint.name,
                    }
                    for unique_constraint in resource.unique_constraints
                ],
                "column_details": [
                    {
                        "name": column.name,
                        "data_type": column.data_type,
                        "type_family": column.type_family,
                        "nullable": column.nullable,
                        "default": column.default,
                        "is_primary_key": column.is_primary_key,
                        "is_foreign_key": column.is_foreign_key,
                    }
                    for column in resource.column_details
                ],
            }
            for resource in source.resources
        ],
    }


def workspace_source_from_payload(payload: dict[str, Any]) -> WorkspaceSource:
    """Hydrate a workspace source from durable JSON storage."""

    return WorkspaceSource(
        id=str(payload["id"]),
        product_id=str(payload["product_id"]),
        kind=DataProductKind(str(payload["kind"])),
        name=str(payload["name"]),
        engine=str(payload["engine"]),
        host=str(payload["host"]),
        description=str(payload.get("description", "")),
        status=WorkspaceSourceStatus(str(payload.get("status", WorkspaceSourceStatus.CONNECTED))),
        resources=tuple(
            WorkspaceResource(
                name=str(resource["name"]),
                resource_type=str(resource["resource_type"]),
                estimated_rows=int(resource.get("estimated_rows", 100)),
                columns=tuple(str(column) for column in resource.get("columns", ())),
                schema_name=_optional_string(resource.get("schema_name")),
                primary_key=tuple(str(column) for column in resource.get("primary_key", ())),
                foreign_keys=tuple(
                    WorkspaceForeignKey(
                        columns=tuple(str(column) for column in foreign_key.get("columns", ())),
                        referred_schema=str(foreign_key.get("referred_schema", "public")),
                        referred_table=str(foreign_key["referred_table"]),
                        referred_columns=tuple(
                            str(column) for column in foreign_key.get("referred_columns", ())
                        ),
                        name=_optional_string(foreign_key.get("name")),
                        on_delete=_optional_string(foreign_key.get("on_delete")),
                        on_update=_optional_string(foreign_key.get("on_update")),
                    )
                    for foreign_key in resource.get("foreign_keys", ())
                ),
                unique_constraints=tuple(
                    WorkspaceUniqueConstraint(
                        columns=tuple(
                            str(column) for column in unique_constraint.get("columns", ())
                        ),
                        name=_optional_string(unique_constraint.get("name")),
                    )
                    for unique_constraint in resource.get("unique_constraints", ())
                ),
                column_details=tuple(
                    WorkspaceColumn(
                        name=str(column["name"]),
                        data_type=str(column.get("data_type", "")),
                        type_family=str(column.get("type_family", "")),
                        nullable=bool(column.get("nullable", True)),
                        default=_optional_string(column.get("default")),
                        is_primary_key=bool(column.get("is_primary_key", False)),
                        is_foreign_key=bool(column.get("is_foreign_key", False)),
                    )
                    for column in resource.get("column_details", ())
                ),
            )
            for resource in payload.get("resources", ())
        ),
        schema_ddl=_optional_string(payload.get("schema_ddl")),
        refreshed_at=_optional_datetime(payload.get("refreshed_at")),
    )


def _resource_from_request(payload: WorkspaceResourceRequest) -> WorkspaceResource:
    return WorkspaceResource(
        name=payload.name,
        resource_type=payload.resource_type,
        estimated_rows=payload.estimated_rows,
        columns=payload.columns,
    )


def _resource_from_table(
    table: TableSchema,
    previous_counts: dict[str, int],
    default_estimated_rows: int,
) -> WorkspaceResource:
    primary_key = table.primary_key.columns if table.primary_key else ()
    foreign_key_columns = {
        column_name
        for foreign_key in table.foreign_keys
        for column_name in foreign_key.columns
    }
    return WorkspaceResource(
        name=table.name,
        resource_type="table",
        estimated_rows=previous_counts.get(table.name, default_estimated_rows),
        columns=table.column_names,
        schema_name=table.schema_name,
        primary_key=primary_key,
        foreign_keys=tuple(
            WorkspaceForeignKey(
                columns=foreign_key.columns,
                referred_schema=foreign_key.referred_schema,
                referred_table=foreign_key.referred_table,
                referred_columns=foreign_key.referred_columns,
                name=foreign_key.name,
                on_delete=foreign_key.on_delete,
                on_update=foreign_key.on_update,
            )
            for foreign_key in table.foreign_keys
        ),
        unique_constraints=tuple(
            WorkspaceUniqueConstraint(
                columns=unique_constraint.columns,
                name=unique_constraint.name,
            )
            for unique_constraint in table.unique_constraints
        ),
        column_details=tuple(
            _workspace_column(column, primary_key, foreign_key_columns)
            for column in table.columns
        ),
    )


def _workspace_column(
    column: ColumnSchema,
    primary_key: tuple[str, ...],
    foreign_key_columns: set[str],
) -> WorkspaceColumn:
    return WorkspaceColumn(
        name=column.name,
        data_type=column.data_type.raw,
        type_family=column.data_type.family.value,
        nullable=column.nullable,
        default=column.default,
        is_primary_key=column.name in primary_key,
        is_foreign_key=column.name in foreign_key_columns,
    )


def _column_definition_from_schema(column: ColumnSchema) -> str:
    parts = [_sql_identifier(column.name), column.data_type.raw]
    if not column.nullable:
        parts.append("NOT NULL")
    if column.default is not None:
        parts.extend(("DEFAULT", column.default))
    return " ".join(parts)


def _constraint_definition(
    name: str | None,
    keyword: str,
    columns: tuple[str, ...],
) -> str:
    prefix = f"CONSTRAINT {_sql_identifier(name)} " if name else ""
    return f"{prefix}{keyword} ({_column_list(columns)})"


def _foreign_key_definition(foreign_key: ForeignKeyConstraint) -> str:
    prefix = f"CONSTRAINT {_sql_identifier(foreign_key.name)} " if foreign_key.name else ""
    referred_table = (
        f"{_sql_identifier(foreign_key.referred_schema)}."
        f"{_sql_identifier(foreign_key.referred_table)}"
    )
    statement = (
        f"{prefix}FOREIGN KEY ({_column_list(foreign_key.columns)}) "
        f"REFERENCES {referred_table} ({_column_list(foreign_key.referred_columns)})"
    )
    if foreign_key.on_delete:
        statement += f" ON DELETE {foreign_key.on_delete}"
    if foreign_key.on_update:
        statement += f" ON UPDATE {foreign_key.on_update}"
    return statement


def _column_list(columns: tuple[str, ...]) -> str:
    return ", ".join(_sql_identifier(column) for column in columns)


def _sql_identifier(value: str | None) -> str:
    if value is None:
        raise ValueError("SQL identifier cannot be None")
    return '"' + value.replace('"', '""') + '"'


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
