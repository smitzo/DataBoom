"""PostgreSQL DDL ingestion.

Purpose:
    Parse PostgreSQL `CREATE TABLE` statements into DataBoom's normalized schema
    models.

Data flow:
    raw DDL string -> sqlglot AST -> `DatabaseSchema`/`TableSchema`/`ColumnSchema`
    models -> generation planner.

Why this layer exists:
    The generator should not depend on parser-specific AST nodes. DDL ingestion
    translates external SQL syntax into a stable internal contract.
"""

from __future__ import annotations

from sqlglot import exp, parse

from databoom.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeyConstraint,
    PostgresType,
    PrimaryKeyConstraint,
    TableSchema,
    UniqueConstraint,
)
from databoom.schema.models import TypeFamily


def parse_postgres_ddl(sql: str) -> DatabaseSchema:
    """Parse PostgreSQL `CREATE TABLE` DDL into a normalized schema."""

    tables: list[TableSchema] = []
    for statement in parse(sql, read="postgres"):
        if isinstance(statement, exp.Create) and statement.args.get("kind") == "TABLE":
            tables.append(_parse_create_table(statement))

    if not tables:
        raise ValueError("DDL does not contain any CREATE TABLE statements")
    return DatabaseSchema(tables=tuple(tables))


def _parse_create_table(statement: exp.Create) -> TableSchema:
    """Parse one `CREATE TABLE` AST node into a table schema."""

    schema = statement.this
    if not isinstance(schema, exp.Schema) or not isinstance(schema.this, exp.Table):
        raise ValueError("CREATE TABLE statement does not include a table schema")

    table_expression = schema.this
    table_name = _identifier_name(table_expression.this)
    schema_name = table_expression.db or "public"

    columns: list[ColumnSchema] = []
    primary_key_columns: list[str] = []
    primary_key_name: str | None = None
    foreign_keys: list[ForeignKeyConstraint] = []
    unique_constraints: list[UniqueConstraint] = []

    for expression in schema.expressions:
        if isinstance(expression, exp.ColumnDef):
            column, inline_constraints = _parse_column(expression)
            columns.append(column)
            if inline_constraints.primary_key:
                primary_key_columns.append(column.name)
            if inline_constraints.unique:
                unique_constraints.append(UniqueConstraint(columns=(column.name,)))
            if inline_constraints.foreign_key is not None:
                foreign_keys.append(inline_constraints.foreign_key)
            continue

        if isinstance(expression, exp.PrimaryKey):
            primary_key_columns = _identifier_list(expression.expressions)
            primary_key_name = None
            continue

        if isinstance(expression, exp.ForeignKey):
            foreign_keys.append(_parse_table_foreign_key(expression, None))
            continue

        if isinstance(expression, exp.Constraint):
            name = _identifier_name(expression.this) if expression.this is not None else None
            for constraint in expression.expressions:
                if isinstance(constraint, exp.ForeignKey):
                    foreign_keys.append(_parse_table_foreign_key(constraint, name))
                elif isinstance(constraint, exp.UniqueColumnConstraint):
                    unique_constraints.append(
                        UniqueConstraint(columns=_schema_columns(constraint.this), name=name)
                    )
                elif isinstance(constraint, exp.PrimaryKey):
                    primary_key_columns = _identifier_list(constraint.expressions)
                    primary_key_name = name

    primary_key = None
    if primary_key_columns:
        primary_key = PrimaryKeyConstraint(
            columns=tuple(primary_key_columns),
            name=primary_key_name,
        )

    return TableSchema(
        schema_name=schema_name,
        name=table_name,
        columns=tuple(columns),
        primary_key=primary_key,
        foreign_keys=tuple(foreign_keys),
        unique_constraints=tuple(unique_constraints),
    )


class _InlineConstraints:
    def __init__(self) -> None:
        self.primary_key = False
        self.unique = False
        self.foreign_key: ForeignKeyConstraint | None = None
        self.default: str | None = None
        self.not_null = False


def _parse_column(column_def: exp.ColumnDef) -> tuple[ColumnSchema, _InlineConstraints]:
    """Parse one column definition and its inline constraints."""

    name = _identifier_name(column_def.this)
    constraints = _InlineConstraints()

    for constraint in column_def.args.get("constraints") or []:
        kind = constraint.kind
        if isinstance(kind, exp.NotNullColumnConstraint):
            constraints.not_null = True
        elif isinstance(kind, exp.PrimaryKeyColumnConstraint):
            constraints.primary_key = True
            constraints.not_null = True
        elif isinstance(kind, exp.UniqueColumnConstraint):
            constraints.unique = True
        elif isinstance(kind, exp.DefaultColumnConstraint):
            constraints.default = kind.this.sql(dialect="postgres")
        elif isinstance(kind, exp.Reference):
            constraints.foreign_key = _parse_inline_foreign_key(name, kind)

    column = ColumnSchema(
        name=name,
        data_type=_parse_data_type(column_def.kind),
        nullable=not constraints.not_null,
        default=constraints.default,
    )
    return column, constraints


def _parse_data_type(data_type: exp.DataType) -> PostgresType:
    """Normalize a SQL type expression into broad generation families."""

    is_array = data_type.this == exp.DataType.Type.ARRAY
    effective_type = data_type.expressions[0] if is_array and data_type.expressions else data_type
    type_name = _type_name(effective_type)
    params = [_literal_int(param.this) for param in effective_type.expressions]
    params = [param for param in params if param is not None]

    return PostgresType(
        raw=data_type.sql(dialect="postgres"),
        name=type_name,
        family=_type_family(type_name),
        length=params[0] if len(params) == 1 else None,
        precision=params[0] if len(params) >= 2 else None,
        scale=params[1] if len(params) >= 2 else None,
        is_array=is_array,
    )


def _parse_inline_foreign_key(column_name: str, reference: exp.Reference) -> ForeignKeyConstraint:
    referred_schema, referred_table, referred_columns = _parse_reference(reference)
    return ForeignKeyConstraint(
        columns=(column_name,),
        referred_schema=referred_schema,
        referred_table=referred_table,
        referred_columns=referred_columns,
        on_delete=_reference_option(reference, "ON DELETE"),
        on_update=_reference_option(reference, "ON UPDATE"),
    )


def _parse_table_foreign_key(
    foreign_key: exp.ForeignKey, name: str | None
) -> ForeignKeyConstraint:
    referred_schema, referred_table, referred_columns = _parse_reference(
        foreign_key.args["reference"]
    )
    return ForeignKeyConstraint(
        name=name,
        columns=tuple(_identifier_list(foreign_key.expressions)),
        referred_schema=referred_schema,
        referred_table=referred_table,
        referred_columns=referred_columns,
    )


def _parse_reference(reference: exp.Reference) -> tuple[str, str, tuple[str, ...]]:
    reference_schema = reference.this
    if not isinstance(reference_schema, exp.Schema) or not isinstance(
        reference_schema.this, exp.Table
    ):
        raise ValueError("foreign key reference does not include a table")

    table = reference_schema.this
    return (
        table.db or "public",
        _identifier_name(table.this),
        _identifier_list(reference_schema.expressions),
    )


def _reference_option(reference: exp.Reference, prefix: str) -> str | None:
    for option in reference.args.get("options") or []:
        if isinstance(option, str) and option.startswith(prefix):
            return option.removeprefix(prefix).strip()
    return None


def _schema_columns(schema: exp.Expression | None) -> tuple[str, ...]:
    if isinstance(schema, exp.Schema):
        return tuple(_identifier_list(schema.expressions))
    return tuple()


def _identifier_list(expressions: list[exp.Expression]) -> list[str]:
    return [_identifier_name(expression) for expression in expressions]


def _identifier_name(expression: exp.Expression) -> str:
    if isinstance(expression, exp.Identifier):
        return expression.name
    return expression.sql(dialect="postgres")


def _type_name(data_type: exp.DataType) -> str:
    value = data_type.this
    if isinstance(value, exp.DataType.Type):
        return value.value.upper()
    return str(value).upper()


def _type_family(type_name: str) -> TypeFamily:
    if type_name in {"BIGINT", "DECIMAL", "DOUBLE", "FLOAT", "INT", "NUMERIC", "REAL", "SMALLINT"}:
        return TypeFamily.NUMERIC
    if type_name in {"CHAR", "TEXT", "VARCHAR"}:
        return TypeFamily.STRING
    if type_name in {"DATE", "TIME", "TIMESTAMP", "TIMESTAMPTZ"}:
        return TypeFamily.DATETIME
    if type_name in {"BOOL", "BOOLEAN"}:
        return TypeFamily.BOOLEAN
    if type_name == "UUID":
        return TypeFamily.UUID
    if type_name in {"JSON", "JSONB"}:
        return TypeFamily.JSON
    return TypeFamily.UNKNOWN


def _literal_int(expression: exp.Expression) -> int | None:
    if isinstance(expression, exp.Literal) and not expression.is_string:
        return int(expression.this)
    return None
