import pytest

from boom_data.ingest import parse_postgres_ddl
from boom_data.schema import TypeFamily


def test_parse_postgres_ddl_with_inline_and_table_constraints() -> None:
    schema = parse_postgres_ddl(
        """
        CREATE TABLE public.accounts (
            id bigint PRIMARY KEY,
            name varchar(120) NOT NULL UNIQUE
        );

        CREATE TABLE public.users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id bigint NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            email varchar(255) NOT NULL,
            created_at timestamp with time zone DEFAULT now(),
            CONSTRAINT users_account_email_key UNIQUE (account_id, email),
            CONSTRAINT users_account_fk FOREIGN KEY (account_id) REFERENCES public.accounts(id)
        );
        """
    )

    users = schema.get_table("users")

    assert schema.table_names == ("public.accounts", "public.users")
    assert users.primary_key is not None
    assert users.primary_key.columns == ("id",)
    assert users.get_column("email").data_type.length == 255
    assert users.get_column("created_at").data_type.family == TypeFamily.DATETIME
    assert users.get_column("account_id").nullable is False
    assert users.get_column("id").default == "GEN_RANDOM_UUID()"
    assert users.unique_constraints[0].columns == ("account_id", "email")
    assert users.foreign_keys[0].columns == ("account_id",)
    assert users.foreign_keys[0].referred_table == "accounts"
    assert users.foreign_keys[0].on_delete == "CASCADE"
    assert users.foreign_keys[1].name == "users_account_fk"


def test_parse_postgres_ddl_with_composite_primary_key() -> None:
    schema = parse_postgres_ddl(
        """
        CREATE TABLE tenant_users (
            tenant_id bigint NOT NULL,
            user_id bigint NOT NULL,
            role text,
            PRIMARY KEY (tenant_id, user_id)
        );
        """
    )

    table = schema.get_table("tenant_users")

    assert table.primary_key is not None
    assert table.primary_key.columns == ("tenant_id", "user_id")


def test_parse_postgres_ddl_rejects_missing_tables() -> None:
    with pytest.raises(ValueError, match="does not contain any CREATE TABLE"):
        parse_postgres_ddl("CREATE INDEX users_email_idx ON users(email);")
