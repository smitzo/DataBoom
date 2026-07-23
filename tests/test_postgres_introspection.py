from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String

from boom_data.ingest.postgres import inspect_postgres_schema, load_postgres_schema
from boom_data.schema.models import TypeFamily


def test_inspect_postgres_schema_builds_normalized_schema(monkeypatch) -> None:
    fake_inspector = _FakePostgresInspector()
    monkeypatch.setattr("boom_data.ingest.postgres.inspect", lambda connectable: fake_inspector)

    schema = inspect_postgres_schema(object())

    assert schema.table_names == ("public.accounts", "public.users")
    accounts = schema.get_table("accounts")
    users = schema.get_table("users")
    assert accounts.primary_key is not None
    assert accounts.primary_key.columns == ("id",)
    assert accounts.get_column("name").data_type.family == TypeFamily.STRING
    assert accounts.get_column("name").data_type.length == 120
    assert users.foreign_keys[0].columns == ("account_id",)
    assert users.foreign_keys[0].referred_table == "accounts"
    assert users.foreign_keys[0].on_delete == "CASCADE"
    assert users.unique_constraints[0].columns == ("email",)


def test_load_postgres_schema_disposes_engine(monkeypatch) -> None:
    fake_engine = _FakeEngine()
    fake_inspector = _FakePostgresInspector()
    monkeypatch.setattr("boom_data.ingest.postgres.create_engine", lambda url: fake_engine)
    monkeypatch.setattr("boom_data.ingest.postgres.inspect", lambda connectable: fake_inspector)

    schema = load_postgres_schema("postgresql+psycopg://example")

    assert fake_engine.disposed is True
    assert schema.table_names == ("public.accounts", "public.users")


class _FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True


class _FakePostgresInspector:
    def get_table_names(self, *, schema: str) -> list[str]:
        assert schema == "public"
        return ["accounts", "users"]

    def get_columns(self, table_name: str, *, schema: str) -> list[dict]:
        assert schema == "public"
        columns = {
            "accounts": [
                {"name": "id", "type": BigInteger(), "nullable": False, "identity": {}},
                {"name": "name", "type": String(length=120), "nullable": False},
                {"name": "active", "type": Boolean(), "nullable": False, "default": "true"},
            ],
            "users": [
                {"name": "id", "type": BigInteger(), "nullable": False},
                {"name": "account_id", "type": BigInteger(), "nullable": False},
                {"name": "email", "type": String(length=255), "nullable": False},
                {"name": "created_at", "type": DateTime(), "nullable": False},
                {"name": "score", "type": Numeric(precision=10, scale=2), "nullable": True},
            ],
        }
        return columns[table_name]

    def get_pk_constraint(self, table_name: str, *, schema: str) -> dict:
        assert schema == "public"
        return {
            "accounts": {"constrained_columns": ["id"], "name": "accounts_pkey"},
            "users": {"constrained_columns": ["id"], "name": "users_pkey"},
        }[table_name]

    def get_foreign_keys(self, table_name: str, *, schema: str) -> list[dict]:
        assert schema == "public"
        if table_name != "users":
            return []
        return [
            {
                "name": "users_account_id_fkey",
                "constrained_columns": ["account_id"],
                "referred_schema": "public",
                "referred_table": "accounts",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
            }
        ]

    def get_unique_constraints(self, table_name: str, *, schema: str) -> list[dict]:
        assert schema == "public"
        if table_name != "users":
            return []
        return [{"name": "users_email_key", "column_names": ["email"]}]
