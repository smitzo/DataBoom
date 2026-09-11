"""State storage for API sessions, subscriptions, sources, profiles, and runs.

Purpose:
    Provide a persistence boundary for the API without binding route logic to a
    specific database implementation.

Data flow:
    API handlers and async workers -> `StateStore` protocol -> in-memory store for
    tests/local fallback or SQLAlchemy-backed tables for Dockerized API runs.

Why this layer exists:
    Generation artifacts live on disk, but the dashboard also needs durable
    metadata: sessions, subscriptions, workspace sources, source profiles, and run
    summaries. A protocol keeps that storage replaceable.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from databoom.api.models import (
    AppUserResponse,
    GenerationRunResponse,
    SubscriptionResponse,
    UserRecord,
)
from databoom.api.workspaces import (
    WorkspaceSource,
    default_workspace_sources,
    workspace_source_from_payload,
    workspace_source_to_payload,
)
from databoom.core.config import Settings
from databoom.profiling import (
    SourceProfile,
    source_profile_from_payload,
    source_profile_to_payload,
)

LOGGER = logging.getLogger(__name__)

metadata = MetaData()

sessions_table = Table(
    "databoom_sessions",
    metadata,
    Column("token", String(255), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

users_table = Table(
    "databoom_users",
    metadata,
    Column("user_id", String(120), primary_key=True),
    Column("login_id", String(120), nullable=False, unique=True, index=True),
    Column("email", String(320), nullable=False, unique=True, index=True),
    Column("name", String(120), nullable=False),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

subscriptions_table = Table(
    "databoom_subscriptions",
    metadata,
    Column("subscription_id", String(255), primary_key=True),
    Column("user_email", String(320), nullable=False, index=True),
    Column("product_id", String(120), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("user_email", "product_id", name="uq_databoom_subscription_user_product"),
)

runs_table = Table(
    "databoom_runs",
    metadata,
    Column("run_id", String(64), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
)

workspace_sources_table = Table(
    "databoom_workspace_sources",
    metadata,
    Column("source_id", String(120), primary_key=True),
    Column("product_id", String(120), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

source_profiles_table = Table(
    "databoom_source_profiles",
    metadata,
    Column("source_id", String(120), primary_key=True),
    Column("payload", JSON, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False, index=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class StateStore(Protocol):
    """Persistence boundary for API state.

    The protocol is deliberately small and domain-specific. It avoids leaking
    SQLAlchemy sessions or table details into route handlers.
    """

    def save_user(self, user: UserRecord) -> None:
        """Persist an application user."""

    def get_user_by_login_id(self, login_id: str) -> UserRecord | None:
        """Return a user by login ID."""

    def get_user_by_email(self, email: str) -> UserRecord | None:
        """Return a user by email."""

    def save_session(self, token: str, user: AppUserResponse) -> None:
        """Persist an authenticated session."""

    def get_session(self, token: str) -> AppUserResponse | None:
        """Return a session user by token."""

    def save_subscription(self, subscription: SubscriptionResponse) -> None:
        """Persist or replace a subscription."""

    def list_subscriptions(self, user_email: str) -> tuple[SubscriptionResponse, ...]:
        """List subscriptions for one user."""

    def get_subscription(self, user_email: str, product_id: str) -> SubscriptionResponse | None:
        """Return one subscription by user and product."""

    def save_run(self, run: GenerationRunResponse) -> None:
        """Persist a generation run."""

    def list_runs(self) -> tuple[GenerationRunResponse, ...]:
        """List known generation runs."""

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        """Return one generation run by ID."""

    def save_workspace_source(self, source: WorkspaceSource) -> None:
        """Persist or replace a workspace source."""

    def list_workspace_sources(self, product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
        """List available workspace sources."""

    def get_workspace_source(self, source_id: str) -> WorkspaceSource | None:
        """Return one workspace source by ID."""

    def save_source_profile(self, profile: SourceProfile) -> None:
        """Persist the latest source profile snapshot."""

    def get_source_profile(self, source_id: str) -> SourceProfile | None:
        """Return the latest source profile snapshot for one source."""


class MemoryStateStore:
    """In-process state store for tests and fallback local development."""

    def __init__(self) -> None:
        self._users_by_login_id: dict[str, UserRecord] = {}
        self._users_by_email: dict[str, UserRecord] = {}
        self._sessions: dict[str, AppUserResponse] = {}
        self._subscriptions: dict[str, dict[str, SubscriptionResponse]] = {}
        self._runs: dict[str, GenerationRunResponse] = {}
        self._workspace_sources: dict[str, WorkspaceSource] = {
            source.id: source for source in default_workspace_sources()
        }
        self._source_profiles: dict[str, SourceProfile] = {}

    def save_user(self, user: UserRecord) -> None:
        self._users_by_login_id[user.login_id] = user
        self._users_by_email[user.email] = user

    def get_user_by_login_id(self, login_id: str) -> UserRecord | None:
        return self._users_by_login_id.get(login_id)

    def get_user_by_email(self, email: str) -> UserRecord | None:
        return self._users_by_email.get(email)

    def save_session(self, token: str, user: AppUserResponse) -> None:
        self._sessions[token] = user

    def get_session(self, token: str) -> AppUserResponse | None:
        return self._sessions.get(token)

    def save_subscription(self, subscription: SubscriptionResponse) -> None:
        self._subscriptions.setdefault(subscription.user_email, {})[
            subscription.product_id
        ] = subscription

    def list_subscriptions(self, user_email: str) -> tuple[SubscriptionResponse, ...]:
        return tuple(self._subscriptions.get(user_email, {}).values())

    def get_subscription(self, user_email: str, product_id: str) -> SubscriptionResponse | None:
        return self._subscriptions.get(user_email, {}).get(product_id)

    def save_run(self, run: GenerationRunResponse) -> None:
        self._runs[run.run_id] = run

    def list_runs(self) -> tuple[GenerationRunResponse, ...]:
        return tuple(self._runs.values())

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        return self._runs.get(run_id)

    def save_workspace_source(self, source: WorkspaceSource) -> None:
        self._workspace_sources[source.id] = source

    def list_workspace_sources(self, product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
        sources = tuple(self._workspace_sources.values())
        if product_id is None:
            return sources
        return tuple(source for source in sources if source.product_id == product_id)

    def get_workspace_source(self, source_id: str) -> WorkspaceSource | None:
        return self._workspace_sources.get(source_id)

    def save_source_profile(self, profile: SourceProfile) -> None:
        self._source_profiles[profile.source_id] = profile

    def get_source_profile(self, source_id: str) -> SourceProfile | None:
        return self._source_profiles.get(source_id)


class SQLAlchemyStateStore:
    """SQL-backed state store used by the Dockerized API.

    Payload columns store Pydantic/API objects as JSON. That keeps the MVP schema
    compact while the product model is still evolving.
    """

    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(
            database_url,
            pool_pre_ping=True,
            future=True,
            connect_args=_database_connect_args(database_url),
        )
        metadata.create_all(self.engine)
        # Demo workspace sources are seed data. They are inserted only when missing
        # so user-refreshed sources are not overwritten on restart.
        self._seed_workspace_sources()

    def save_user(self, user: UserRecord) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(users_table).values(
                    user_id=user.user_id,
                    login_id=user.login_id,
                    email=user.email,
                    name=user.name,
                    password_hash=user.password_hash,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                )
            )

    def get_user_by_login_id(self, login_id: str) -> UserRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(
                    users_table.c.user_id,
                    users_table.c.login_id,
                    users_table.c.email,
                    users_table.c.name,
                    users_table.c.password_hash,
                    users_table.c.created_at,
                    users_table.c.updated_at,
                ).where(users_table.c.login_id == login_id)
            ).one_or_none()
        return _parse_user_record(row) if row is not None else None

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                select(
                    users_table.c.user_id,
                    users_table.c.login_id,
                    users_table.c.email,
                    users_table.c.name,
                    users_table.c.password_hash,
                    users_table.c.created_at,
                    users_table.c.updated_at,
                ).where(users_table.c.email == email)
            ).one_or_none()
        return _parse_user_record(row) if row is not None else None

    def save_session(self, token: str, user: AppUserResponse) -> None:
        payload = user.model_dump(mode="json")
        with self.engine.begin() as connection:
            connection.execute(delete(sessions_table).where(sessions_table.c.token == token))
            connection.execute(
                insert(sessions_table).values(
                    token=token,
                    payload=payload,
                    updated_at=datetime.now(UTC),
                )
            )

    def get_session(self, token: str) -> AppUserResponse | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(sessions_table.c.payload).where(sessions_table.c.token == token)
            ).scalar_one_or_none()
        return AppUserResponse.model_validate(payload) if payload else None

    def save_subscription(self, subscription: SubscriptionResponse) -> None:
        payload = subscription.model_dump(mode="json")
        with self.engine.begin() as connection:
            connection.execute(
                delete(subscriptions_table).where(
                    subscriptions_table.c.user_email == subscription.user_email,
                    subscriptions_table.c.product_id == subscription.product_id,
                )
            )
            connection.execute(
                insert(subscriptions_table).values(
                    subscription_id=subscription.subscription_id,
                    user_email=subscription.user_email,
                    product_id=subscription.product_id,
                    payload=payload,
                    created_at=subscription.created_at,
                )
            )

    def list_subscriptions(self, user_email: str) -> tuple[SubscriptionResponse, ...]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(subscriptions_table.c.payload)
                .where(subscriptions_table.c.user_email == user_email)
                .order_by(subscriptions_table.c.created_at)
            )
            return tuple(_parse_subscriptions(row[0] for row in rows))

    def get_subscription(self, user_email: str, product_id: str) -> SubscriptionResponse | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(subscriptions_table.c.payload).where(
                    subscriptions_table.c.user_email == user_email,
                    subscriptions_table.c.product_id == product_id,
                )
            ).scalar_one_or_none()
        return SubscriptionResponse.model_validate(payload) if payload else None

    def save_run(self, run: GenerationRunResponse) -> None:
        payload = run.model_dump(mode="json")
        with self.engine.begin() as connection:
            connection.execute(delete(runs_table).where(runs_table.c.run_id == run.run_id))
            connection.execute(
                insert(runs_table).values(
                    run_id=run.run_id,
                    payload=payload,
                    created_at=run.created_at,
                )
            )

    def list_runs(self) -> tuple[GenerationRunResponse, ...]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                select(runs_table.c.payload).order_by(runs_table.c.created_at)
            )
            return tuple(_parse_runs(row[0] for row in rows))

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(runs_table.c.payload).where(runs_table.c.run_id == run_id)
            ).scalar_one_or_none()
        return GenerationRunResponse.model_validate(payload) if payload else None

    def save_workspace_source(self, source: WorkspaceSource) -> None:
        payload = workspace_source_to_payload(source)
        with self.engine.begin() as connection:
            connection.execute(
                delete(workspace_sources_table).where(
                    workspace_sources_table.c.source_id == source.id
                )
            )
            connection.execute(
                insert(workspace_sources_table).values(
                    source_id=source.id,
                    product_id=source.product_id,
                    payload=payload,
                    updated_at=datetime.now(UTC),
                )
            )

    def list_workspace_sources(self, product_id: str | None = None) -> tuple[WorkspaceSource, ...]:
        query = select(workspace_sources_table.c.payload).order_by(
            workspace_sources_table.c.product_id,
            workspace_sources_table.c.source_id,
        )
        if product_id is not None:
            query = query.where(workspace_sources_table.c.product_id == product_id)
        with self.engine.begin() as connection:
            rows = connection.execute(query)
            return tuple(workspace_source_from_payload(row[0]) for row in rows)

    def get_workspace_source(self, source_id: str) -> WorkspaceSource | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(workspace_sources_table.c.payload).where(
                    workspace_sources_table.c.source_id == source_id
                )
            ).scalar_one_or_none()
        return workspace_source_from_payload(payload) if payload else None

    def save_source_profile(self, profile: SourceProfile) -> None:
        payload = source_profile_to_payload(profile)
        with self.engine.begin() as connection:
            connection.execute(
                delete(source_profiles_table).where(
                    source_profiles_table.c.source_id == profile.source_id
                )
            )
            connection.execute(
                insert(source_profiles_table).values(
                    source_id=profile.source_id,
                    payload=payload,
                    generated_at=profile.generated_at,
                    updated_at=datetime.now(UTC),
                )
            )

    def get_source_profile(self, source_id: str) -> SourceProfile | None:
        with self.engine.begin() as connection:
            payload = connection.execute(
                select(source_profiles_table.c.payload).where(
                    source_profiles_table.c.source_id == source_id
                )
            ).scalar_one_or_none()
        return source_profile_from_payload(payload) if payload else None

    def _seed_workspace_sources(self) -> None:
        with self.engine.begin() as connection:
            existing_source_id = connection.execute(
                select(workspace_sources_table.c.source_id).limit(1)
            ).scalar_one_or_none()
            if existing_source_id is not None:
                return
            for source in default_workspace_sources():
                connection.execute(
                    insert(workspace_sources_table).values(
                        source_id=source.id,
                        product_id=source.product_id,
                        payload=workspace_source_to_payload(source),
                        updated_at=datetime.now(UTC),
                    )
                )


def create_state_store(settings: Settings) -> StateStore:
    """Create the best available state store for this runtime."""

    if settings.environment == "test":
        return MemoryStateStore()

    try:
        return SQLAlchemyStateStore(settings.database_url)
    except SQLAlchemyError:
        if settings.environment == "docker":
            raise
        LOGGER.warning("Falling back to in-memory API state store", exc_info=True)
        return MemoryStateStore()


def _parse_subscriptions(payloads: Iterable[object]) -> Iterable[SubscriptionResponse]:
    for payload in payloads:
        yield SubscriptionResponse.model_validate(payload)


def _parse_runs(payloads: Iterable[object]) -> Iterable[GenerationRunResponse]:
    for payload in payloads:
        yield GenerationRunResponse.model_validate(payload)


def _database_connect_args(database_url: str) -> dict[str, object]:
    """Return driver options for managed Postgres compatibility.

    Supabase transaction pooling does not support server-side prepared
    statements. Psycopg can disable automatic preparation with
    `prepare_threshold=None`, which keeps the SQLAlchemy state store compatible
    with the pooled URL used by Render deployments.
    """

    if database_url.startswith("postgresql+psycopg"):
        return {"prepare_threshold": None}
    return {}


def _parse_user_record(row) -> UserRecord:
    return UserRecord(
        user_id=row.user_id,
        login_id=row.login_id,
        email=row.email,
        name=row.name,
        password_hash=row.password_hash,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
